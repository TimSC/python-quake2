"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * The PcxDirect Graphics file format
 *
 * =======================================================================
"""
from __future__ import annotations

import struct
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver, filesystem
from common import md4


def COM_FileBase(in_name): #char *, char * (returns char *)
	# extract the base name (no directory, no extension)
	base = in_name
	slash = base.rfind("/")
	if slash >= 0:
		base = base[slash + 1:]
	dot = base.rfind(".")
	if dot >= 0:
		base = base[:dot]
	return base


"""
 * Add extension to file name
"""
def FixFileExt(origname, ext, filename): #const char *, const char *, char *, size_t

	# Q2PORT: this is stb.c's FixFileExt; it returns the new name instead of
	# filling filename (which callers pass as None). It used to strip the
	# directory (COM_FileBase), which LoadWal etc. can't work with.
	filename = origname

	# Add the extension
	if shared_c.COM_FileExtension(filename) != ext:

		filename += "." + ext

	return filename


# Fix Jennell Jaquays' name in the Quitscreen
# this is 98x11 pixels, each value an index
# into the standard baseq2/pak0/pics/quit.pcx colormap
quitscreenfix = bytes([ #static unsigned char quitscreenfix[]
	191,191,191,47,28,39,4,4,39,1,47,28,47,28,29,1,
	28,28,47,31,31,1,29,31,1,28,47,47,47,47,29,28,
	47,31,30,28,40,40,4,28,28,40,39,40,29,102,102,245,
	28,39,4,4,39,103,40,40,1,1,102,94,47,47,1,94,
	94,94,94,47,102,245,103,103,103,47,1,102,1,102,29,29,
	29,29,47,28,245,31,31,31,47,1,28,1,28,47,1,102, 102,102,
	191,191,142,47,4,8,8,8,8,4,47,28,1,28,29,28,
	29,29,31,1,47,245,47,47,28,28,31,47,28,1,31,1,
	1,245,47,39,8,8,8,40,39,8,8,8,39,1,1,47,
	4,8,8,8,8,4,47,29,28,31,28,28,29,28,28,28,
	29,28,31,28,47,29,1,28,31,47,1,28,1,1,29,29,
	29,47,28,1,28,28,245,28,28,28,28,47,29,28,47,102,102,103,
	191,191,142,31,29,36,8,8,36,31,40,39,40,4,1,1,
	39,40,39,40,40,31,28,40,40,4,39,40,28,47,31,40,
	39,40,4,1,36,8,8,4,47,36,8,8,39,1,1,1,
	29,36,8,8,36,4,4,39,40,4,47,1,47,40,40,39,
	39,40,28,40,40,47,45,39,40,28,4,39,40,4,39,1,
	28,4,40,28,28,4,39,28,47,40,40,39,40,39,28,28,1,103,
	1,142,29,142,28,39,8,8,36,36,8,8,8,8,36,1,
	8,8,8,8,8,36,39,8,8,8,8,8,36,40,36,8,
	8,8,8,36,40,8,8,40,1,4,8,8,40,1,1,31,
	28,39,8,8,36,8,8,8,8,8,36,31,36,8,8,8,
	8,8,36,8,8,4,40,8,8,36,8,8,8,8,8,36,
	40,8,8,40,39,8,8,40,36,8,8,8,8,8,39,29,28,29,
	103,191,142,47,28,40,8,8,40,8,8,33,33,8,8,36,
	8,8,36,36,8,8,36,8,8,36,36,8,8,36,8,8,
	33,33,8,8,36,8,8,4,47,40,8,8,39,47,28,245,
	28,40,8,8,40,40,36,36,33,8,8,36,8,8,36,36,
	8,8,36,8,8,40,40,8,8,40,4,36,36,33,8,8,
	36,8,8,39,39,8,8,36,8,8,33,36,36,39,28,1,47,28,
	103,246,1,47,1,39,8,8,40,8,8,8,8,8,8,36,
	8,8,4,40,8,8,36,8,8,40,4,8,8,36,8,8,
	8,8,8,8,36,8,8,40,29,39,8,8,39,1,1,47,
	1,39,8,8,40,36,8,8,8,8,8,36,8,8,4,40,
	8,8,36,8,8,40,39,8,8,40,36,8,8,8,8,8,
	36,8,8,39,40,8,8,40,36,8,8,8,8,36,28,1,1,29,
	103,47,40,40,4,36,8,8,36,8,8,33,36,36,36,4,
	8,8,39,4,8,8,36,8,8,4,40,8,8,36,8,8,
	33,36,36,36,36,8,8,40,31,40,8,8,40,47,40,40,
	4,36,8,8,36,8,8,33,33,8,8,36,8,8,36,36,
	8,8,36,8,8,36,36,8,8,36,8,8,33,33,8,8,
	36,8,8,36,36,8,8,4,39,36,36,33,8,8,4,40,4,31,
	191,40,8,8,8,8,8,36,29,36,8,8,8,8,8,40,
	8,8,40,4,8,8,36,8,8,40,39,8,8,39,36,8,
	8,8,8,8,39,8,8,39,45,4,8,8,40,40,8,8,
	8,8,8,36,29,36,8,8,8,8,8,40,36,8,8,8,
	8,8,40,36,8,8,8,8,8,40,36,8,8,8,8,8,
	40,36,8,8,8,8,8,36,8,8,8,8,8,36,4,8,8,4,
	47,45,40,39,40,39,39,245,246,1,40,40,40,39,4,47,
	40,4,28,29,39,40,30,39,39,1,28,40,4,28,1,40,
	40,40,39,4,29,40,39,1,1,1,4,4,47,45,40,39,
	40,39,39,245,246,29,39,40,40,40,4,47,28,39,39,36,
	8,8,4,1,39,40,4,40,40,1,29,4,39,4,40,39,
	1,39,36,36,33,8,8,4,39,4,39,4,40,47,36,8,8,40,
	1,28,47,28,28,29,1,28,47,28,31,28,28,27,47,28,
	45,246,30,28,245,29,47,47,29,30,28,47,27,1,246,47,
	47,47,1,28,47,28,47,1,47,47,1,29,29,47,47,28,
	28,29,1,47,1,47,47,28,31,47,47,31,47,47,47,4,
	8,8,39,245,1,47,28,245,28,47,31,28,47,28,28,28,
	40,8,8,8,8,8,36,47,28,1,246,47,1,40,8,8,36,1,
	47,1,102,1,102,102,47,94,94,102,47,47,102,102,102,102,
	94,1,94,47,102,1,102,47,30,30,102,27,47,102,94,1,
	102,47,1,94,102,103,1,102,103,103,47,47,47,29,1,29,
	28,28,29,28,1,47,28,31,29,1,47,29,28,1,1,47,
	4,39,1,47,47,1,28,28,28,47,1,28,45,28,47,47,
	1,40,4,4,40,4,29,28,31,45,47,28,47,47,4,40,28,28
])

def fixQuitScreen(px: bytearray): #byte* (static)

	# overwrite 11 lines, 98 pixels each, from quitscreenfix[]
	# starting at line 140, column 188
	# quitscreen is 320x240 px
	qsIdx = 0 #int r, qsIdx = 0;

	px_offset = 140*320 # go to line 140
	px_offset += 188 # to colum 188
	for r in range(11):

		px[px_offset:px_offset + 98] = quitscreenfix[qsIdx:qsIdx + 98] # memcpy(px, quitscreenfix+qsIdx, 98);
		qsIdx += 98
		px_offset += 320

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

def LoadPCX(origname): #const char *, byte **, byte **, int *, int *, int *

	# Q2PORT: returns (pic, palette, width, height, bitsPerPixel) instead of
	# filling the pointers

	"""
	char filename[256];
	byte *raw;
	int len;
	"""

	filename = FixFileExt(origname, "pcx", None)

	pic = None

	palette = None

	# load the file
	len_, raw = filesystem.FS_LoadFile(filename)
	if raw is None:

		# no such file
		return pic, palette, None, None, 8


	pic, palette, width, height, bitsPerPixel = PCX_Decode(filename, raw, len_)

	if (pic is not None and bitsPerPixel == 8 and width and height
		and width == 320 and height == 240
		and shared_c.Q_strcasecmp(filename, "pics/quit.pcx") == 0
		and md4.Com_BlockChecksum(raw, len_) == 3329419434):

		# it's the quit screen, and the baseq2 one (identified by checksum)
		# so fix it
		fixQuitScreen(pic)


	filesystem.FS_FreeFile(raw)

	return pic, palette, width, height, bitsPerPixel

def GetPCXInfo(origname): #const char *, int *, int *

	# Q2PORT: returns (width, height), (None, None) where the C leaves them

	"""
	pcx_t *pcx;
	byte *raw;
	char filename[256];
	"""

	filename = FixFileExt(origname, "pcx", None)

	len_, raw = filesystem.FS_LoadFile(filename)

	if raw is None:

		return None, None


	if len_ < PCX_HEADER_SIZE: # Q2PORT: the C reads the header past a short file

		return None, None

	pcx = files_h.pcx_t()
	pcx.Read(raw) # pcx = (pcx_t *)raw;

	width = pcx.xmax + 1
	height = pcx.ymax + 1

	filesystem.FS_FreeFile(raw)

	return width, height

"""
==============
GetPCXPalette
==============
"""
def GetPCXPalette(colormap, d_8to24table): #byte **, unsigned *

	#byte	*pal;
	#int		i, bitsPerPixel;

	# get the palette and colormap
	pic, pal, width, height, bitsPerPixel = LoadPCX("pics/colormap.pcx")
	if pic is None or pal is None or bitsPerPixel != 8:
		clientserver.Com_Error(shared.ERR_FATAL, "%s: Couldn't load pics/colormap.pcx",
			"GetPCXPalette")

	for i in range(256):
		r, g, b = struct.unpack("<BBB", pal[i * 3:i * 3 + 3])

		if i != 255:
			d_8to24table[i] = (r, g, b, 255)
		else:
			d_8to24table[i] = (r, g, b, 0) # 255 is transparent
