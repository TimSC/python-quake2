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


"""
==============
LoadPCX
==============
"""
def LoadPCX(origname): #char *, byte **, byte **, int *, int * (returns qboolean)

	# Q2PORT: Yamagi's LoadPCX takes the name without extension (it is
	# FixFileExt'ed, so a name with ".pcx" works too) and also returns
	# bitsPerPixel; the port only reads 8 bit PCX, so that is always 8.
	filename = FixFileExt(origname, "pcx", None)

	#
	# load the file
	#
	length, raw = filesystem.FS_LoadFile(filename)
	if raw is None:
		clientserver.Com_Printf("Bad pcx file {}\n".format(filename))
		return None, None, None, None

	pcx = files_h.pcx_t()

	try:
		pic, palette, width, height = pcx.Decompress(raw)
	except IndexError:
		pic = None
		clientserver.Com_Printf("PCX file {} was malformed".format(filename))

	if pic is None:
		clientserver.Com_Printf("Bad pcx file {}\n".format(filename))
		return None, None, None, None

	return pic, palette, width, height

"""
==============
GetPCXInfo
==============
"""
def GetPCXInfo(filename): #char *, int *, int * (returns qboolean)

	length, raw = filesystem.FS_LoadFile(filename)
	if raw is None:
		return None, None

	pcx = files_h.pcx_t()
	if not pcx.Read(raw):
		return None, None

	return pcx.xmax + 1, pcx.ymax + 1

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
