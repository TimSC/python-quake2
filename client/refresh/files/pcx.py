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

from q2data import FormatError
from q2data import images as q2images
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

"""
==============
LoadPCX
==============
"""
def LoadPCX(origname): #char * (returns pic, palette, width, height)

	# The name may come with or without ".pcx". The pixels are 8 bit palette
	# indices (q2data.images.load_pcx); true colour PCX files aren't used by
	# the renderers' callers, so they are refused as before.
	filename = FixFileExt(origname, "pcx", None)

	length, raw = filesystem.FS_LoadFile(filename)
	if raw is None:
		clientserver.Com_Printf("Bad pcx file {}\n".format(filename))
		return None, None, None, None

	raw = bytes(raw)
	try:
		image = q2images.load_pcx(raw)
	except FormatError as err:
		clientserver.Com_Printf("{}: {} {}\n".format("PCX_Decode", filename, err))
		return None, None, None, None

	for warning in image.warnings:

		if warning == "possible size issues":
			clientserver.Com_Printf("{}: {} file has {}.\n".format("PCX_Decode", filename, warning))
		else:
			clientserver.Com_DPrintf("{}: {} {}\n".format("PCX_Decode", filename, warning))

	if not image.indexed or image.palette is None:
		clientserver.Com_Printf("Bad pcx file {}\n".format(filename))
		return None, None, None, None

	pic = bytearray(image.pixels.tobytes())
	width, height = image.width, image.height

	if width == 320 and height == 240 \
		and filename.lower() == "pics/quit.pcx" \
		and md4.Com_BlockChecksum(raw, len(raw)) == 3329419434:

		# it's the quit screen, and the baseq2 one (identified by checksum)
		# so fix it
		fixQuitScreen(pic)

	return pic, image.palette.tobytes(), width, height

"""
==============
GetPCXInfo
==============
"""
def GetPCXInfo(filename): #char * (returns width, height, or None, None)

	length, raw = filesystem.FS_LoadFile(filename)
	if raw is None:
		return None, None

	try:
		header = q2images.read_pcx_header(bytes(raw))
	except FormatError:
		return None, None

	return header.width, header.height

"""
==============
GetPCXPalette
==============
"""
def GetPCXPalette(colormap, d_8to24table): #byte **, unsigned *

	#byte	*pic, *pal;
	#int		width, height;

	pic, pal, width, height = LoadPCX("pics/colormap.pcx")
	if pal is None:
		clientserver.Com_Error(shared.ERR_FATAL, "Couldn't load pics/colormap.pcx")

	for i in range(256):
		r, g, b = struct.unpack("<BBB", pal[i * 3:i * 3 + 3])

		if i != 255:
			d_8to24table[i] = (r, g, b, 255)
		else:
			d_8to24table[i] = (r, g, b, 0) # 255 is transparent
