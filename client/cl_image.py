"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

This file implements .pcx bitmap decoder.

=======================================================================
"""
from __future__ import annotations

import io

from PIL import Image

from common.header import files as files_h
from common.shared import shared as shared_c
from common import clientserver
from common import filesystem

"""
#include "header/client.h"
"""

PCX_IDENT	= ((0x05 << 8) + 0x0a)

# don't need HDR stuff
#define STBI_NO_LINEAR
#define STBI_NO_HDR
# make sure STB_image uses standard malloc(), as we'll use standard free() to deallocate
#define STBI_MALLOC(sz)    malloc(sz)
#define STBI_REALLOC(p,sz) realloc(p,sz)
#define STBI_FREE(p)       free(p)
# Switch of the thread local stuff. Breaks mingw under Windows.
#define STBI_NO_THREAD_LOCALS
# include implementation part of stb_image into this file
#define STB_IMAGE_IMPLEMENTATION
#include "refresh/files/stb_image.h"
# Q2PORT: there is no stb_image; Pillow loads the other formats (see SCR_LoadImageWithPalette)

PCX_HEADER_SIZE	= 128 # Q2PORT: the offset of pcx_t's data, (const byte *)&pcx->data - raw

def PCX_RLE_Decode(pix: bytearray, pix_ofs: int, pix_max: int, raw: bytes, raw_ofs: int, raw_max: int,
	bytes_per_line: int): #byte *, byte *, const byte *, const byte *, int, qboolean * (returns static const byte *)

	# Q2PORT: the pointers are offsets into pix and raw; returns (raw offset, image_issues),
	# image_issues True where the C sets *image_issues = true

	"""
	int x;
	"""

	x = 0
	while x < bytes_per_line:

		"""
		int runLength;
		byte dataByte;
		"""

		if raw_ofs >= raw_max:

			# no place for read
			return raw_ofs, True

		dataByte = raw[raw_ofs]
		raw_ofs += 1

		if (dataByte & 0xC0) == 0xC0:

			runLength = dataByte & 0x3F
			if raw_ofs >= raw_max:

				# no place for read
				return raw_ofs, True

			dataByte = raw[raw_ofs]
			raw_ofs += 1

		else:

			runLength = 1


		while runLength > 0:

			runLength -= 1
			if pix_max <= (pix_ofs + x):

				# no place for write
				return raw_ofs, True

			else:

				pix[pix_ofs + x] = dataByte
				x += 1

	return raw_ofs, False

def PCX_Decode(name: str, raw: bytes, len_: int):
	#const char *, const byte *, int, byte **, byte **, int *, int *, int * (static)

	# Q2PORT: returns (pic, palette, width, height, bitsPerPixel) instead of
	# filling the pointers; width and height are None where the C leaves them

	"""
	const pcx_t *pcx;
	int full_size;
	int pcx_width, pcx_height, bytes_per_line;
	qboolean image_issues = false;
	byte *out, *pix;
	const byte *data;
	"""
	image_issues = False

	pic = None
	bitsPerPixel = 8

	palette = None
	width, height = None, None

	if len_ < PCX_HEADER_SIZE: # sizeof(pcx_t)

		return pic, palette, width, height, bitsPerPixel


	# parse the PCX file
	pcx = files_h.pcx_t()
	pcx.Read(raw) # pcx = (const pcx_t *)raw;

	data = PCX_HEADER_SIZE # data = &pcx->data;

	bytes_per_line = pcx.bytes_per_line # LittleShort(pcx->bytes_per_line)
	pcx_width = pcx.xmax - pcx.xmin
	pcx_height = pcx.ymax - pcx.ymin

	if ((pcx.manufacturer != 0x0a) or
		(pcx.version != 5) or
		(pcx.encoding != 1) or
		(pcx_width <= 0) or
		(pcx_height <= 0) or
		(bytes_per_line <= 0) or
		(pcx.color_planes <= 0) or
		(pcx.bits_per_pixel <= 0)):

		clientserver.Com_Printf("%s: Bad pcx file %s: version: %d:%d, encoding: %d\n",
			"PCX_Decode", name, pcx.manufacturer, pcx.version, pcx.encoding)
		return pic, palette, width, height, bitsPerPixel


	full_size = (pcx_height + 1) * (pcx_width + 1)
	if ((pcx.color_planes == 3 or pcx.color_planes == 4)
		and pcx.bits_per_pixel == 8):

		full_size *= 4
		bitsPerPixel = 32


	out = bytearray(full_size) # malloc(full_size)

	pic = out

	pix = 0 # pix = out;

	width = pcx_width + 1

	height = pcx_height + 1

	if ((pcx.color_planes == 3 or pcx.color_planes == 4)
		and pcx.bits_per_pixel == 8):

		"""
		int x, y, linesize;
		byte *line;
		"""

		if bytes_per_line <= pcx_width:

			image_issues = True


		# clean image alpha
		out[:] = b'\xff' * full_size # memset(pix, 255, full_size);

		linesize = max(bytes_per_line, pcx_width + 1) * pcx.color_planes
		line = bytearray(linesize)

		for y in range(pcx_height + 1):

			data, issues = PCX_RLE_Decode(line, 0, linesize,
				raw, data, len_,
				bytes_per_line * pcx.color_planes)
			image_issues = image_issues or issues

			for x in range(pcx_width + 1):

				"""
				int j;
				"""

				for j in range(pcx.color_planes):

					out[pix + 4 * x + j] = line[x + bytes_per_line * j]

			pix += (pcx_width + 1) * 4

		#free(line);

	elif pcx.bits_per_pixel == 1:

		"""
		byte *line;
		int y;
		"""

		palette = bytes(pcx.palette) # memcpy(*palette, pcx->palette, sizeof(pcx->palette)); (48 bytes in a 768 byte buffer)
		palette += bytes(768 - len(palette))

		line = bytearray(bytes_per_line * pcx.color_planes)

		for y in range(pcx_height + 1):

			"""
			int x;
			"""

			data, issues = PCX_RLE_Decode(line, 0, bytes_per_line * pcx.color_planes,
				raw, data, len_,
				bytes_per_line * pcx.color_planes)
			image_issues = image_issues or issues

			for x in range(pcx_width + 1):

				"""
				int m, i, v;
				"""

				m = 0x80 >> (x & 7)
				v = 0

				for i in range(pcx.color_planes - 1, -1, -1):
					v <<= 1
					v += 1 if (line[i * bytes_per_line + (x >> 3)] & m) else 0

				out[pix + x] = v & 0xff

			pix += pcx_width + 1

		#free(line);

	elif pcx.color_planes == 1 and pcx.bits_per_pixel == 8:

		"""
		int y, linesize;
		byte *line;
		"""

		palette = bytes(768) # malloc(768)

		if len_ > 768:

			palette = bytes(raw[len_ - 768:len_]) # memcpy(*palette, (byte *)pcx + len - 768, 768);

			if raw[len_ - 769] != 0x0C:

				clientserver.Com_DPrintf("%s: %s has no palette marker\n",
					"PCX_Decode", name)

		else:

			image_issues = True


		if bytes_per_line <= pcx_width:

			image_issues = True


		linesize = max(bytes_per_line, pcx_width + 1)
		line = bytearray(linesize)
		for y in range(pcx_height + 1):

			data, issues = PCX_RLE_Decode(line, 0, linesize,
				raw, data, len_,
				bytes_per_line)
			image_issues = image_issues or issues
			# copy only visible part
			out[pix:pix + pcx_width + 1] = line[:pcx_width + 1]

			pix += pcx_width + 1

		#free(line);

	elif (pcx.color_planes == 1 and
		(pcx.bits_per_pixel == 2 or pcx.bits_per_pixel == 4)):

		"""
		int y;

		byte *line;
		"""

		palette = bytes(pcx.palette) # memcpy(*palette, pcx->palette, sizeof(pcx->palette));
		palette += bytes(768 - len(palette))

		line = bytearray(bytes_per_line)

		for y in range(pcx_height + 1):

			"""
			int x, mask, div;
			"""

			data, issues = PCX_RLE_Decode(line, 0, bytes_per_line,
				raw, data, len_,
				bytes_per_line)
			image_issues = image_issues or issues

			mask = (1 << pcx.bits_per_pixel) - 1
			div = 8 // pcx.bits_per_pixel

			for x in range(pcx_width + 1):

				"""
				unsigned v, shift;
				"""

				v = line[x // div] & 0xFF
				# for 2 bits:
				# 0 -> 6
				# 1 -> 4
				# 3 -> 2
				# 4 -> 0
				shift = pcx.bits_per_pixel * ((div - 1) - x % div)
				out[pix + x] = (v >> shift) & mask

			pix += pcx_width + 1

		#free(line);

	else:

		clientserver.Com_Printf("%s: Bad pcx file %s: planes: %d, bits: %d\n",
			"PCX_Decode", name, pcx.color_planes, pcx.bits_per_pixel)
		pic = None # free(*pic);


	if pcx.color_planes != 1 or pcx.bits_per_pixel != 8:

		clientserver.Com_DPrintf("%s: %s has uncommon flags, "
			"could be unsupported by other engines\n",
			"PCX_Decode", name)


	if data > len_: # data - (byte *)pcx > len

		clientserver.Com_DPrintf("%s: %s file was malformed\n", "PCX_Decode", name)
		pic = None # free(*pic);


	if image_issues:

		clientserver.Com_Printf("%s: %s file has possible size issues.\n", "PCX_Decode", name)

	return pic, palette, width, height, bitsPerPixel

def SCR_LoadImageWithPalette(filename: str):
	#char *, byte **, byte **, int *, int *, int *

	# Q2PORT: returns (pic, palette, width, height, bitsPerPixel) instead of
	# filling the pointers; width, height and bitsPerPixel are None where the C
	# leaves them

	"""
	const char* ext;
	int len, ident;
	byte *raw;
	"""

	ext = shared_c.COM_FileExtension(filename)
	pic = None

	# load the file
	len_, raw = filesystem.FS_LoadFile(filename)

	if not raw or len_ <= 0:

		return None, None, None, None, None


	if len_ <= 4: # sizeof(int)

		#FS_FreeFile(raw);
		return None, None, None, None, None


	ident = shared_c.LittleSShort(raw[0:2]) # LittleShort(*((short*)raw))
	if ext == "pcx" and (ident == PCX_IDENT):

		pic, palette, width, height, bitsPerPixel = PCX_Decode(filename, raw, len_)

	else:

		# other formats does not have palette directly
		palette = None

		# Q2PORT: *pic = stbi_load_from_memory(raw, len, width, height,
		#	&sourcebitsPerPixel, STBI_rgb_alpha); Pillow's image loader instead
		pic, width, height = None, None, None
		try:

			img = Image.open(io.BytesIO(bytes(raw[:len_]))).convert("RGBA")
			width, height = img.size
			pic = bytearray(img.tobytes())

		except (OSError, ValueError) as e: # Pillow can't read it

			clientserver.Com_DPrintf("%s couldn't load data from %s: %s!\n",
				"SCR_LoadImageWithPalette", filename, str(e))


		bitsPerPixel = 32


	#FS_FreeFile(raw);

	return pic, palette, width, height, bitsPerPixel
