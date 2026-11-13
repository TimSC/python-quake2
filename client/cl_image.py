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

from q2data import FormatError
from q2data import images as q2images
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

def PCX_Decode(name: str, raw: bytes, len_: int):
	#const char *, const byte *, int (returns pic, palette, width, height, bitsPerPixel)

	# Decoded by q2data.images.load_pcx: 8 bit files give palette indices and
	# their palette, 24/32 bit files RGBA (bitsPerPixel 32, no palette).
	try:
		image = q2images.load_pcx(bytes(raw[:len_]))
	except FormatError as err:
		clientserver.Com_Printf("%s: %s %s\n", "PCX_Decode", name, str(err))
		return None, None, None, None, 8

	for warning in image.warnings:

		if warning == "possible size issues":
			clientserver.Com_Printf("%s: %s file has possible size issues.\n", "PCX_Decode", name)
		else:
			clientserver.Com_DPrintf("%s: %s %s\n", "PCX_Decode", name, warning)

	if image.indexed:
		palette = image.palette.tobytes() if image.palette is not None else None
		return bytearray(image.pixels.tobytes()), palette, image.width, image.height, 8

	return bytearray(image.pixels.tobytes()), None, image.width, image.height, 32

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

		# stbi_load_from_memory(raw, len, width, height, &sourcebitsPerPixel,
		#	STBI_rgb_alpha) is q2data.images.load_rgba
		pic, width, height = None, None, None
		try:

			img = q2images.load_rgba(bytes(raw[:len_]))
			width, height = img.width, img.height
			pic = bytearray(img.pixels.tobytes())

		except FormatError as e: # it can't be read

			clientserver.Com_DPrintf("%s couldn't load data from %s: %s!\n",
				"SCR_LoadImageWithPalette", filename, str(e))


		bitsPerPixel = 32


	#FS_FreeFile(raw);

	return pic, palette, width, height, bitsPerPixel
