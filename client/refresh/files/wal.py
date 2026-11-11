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
 * The Wal image format
 *
 * =======================================================================
"""
from __future__ import annotations

from common.header import files as files_h
# Q2PORT: LittleLong() is done by the files_h structs' load()
from common import clientserver, filesystem
from client.refresh.files import pcx


def LoadWal(origname, type, load_image): #const char *, imagetype_t, loadimage_t (returns struct image_s *)

	name = pcx.FixFileExt(origname, "wal", None)

	size, mt = filesystem.FS_LoadFile(name)

	if mt is None:
		return None

	if size < files_h.miptex_t.packed_size():
		clientserver.Com_Printf("{}: can't load {}, small header\n".format("LoadWal", name))
		filesystem.FS_FreeFile(mt)
		return None

	img_header = files_h.miptex_t()
	img_header.load(mt)

	width = img_header.width
	height = img_header.height
	ofs = img_header.offsets[0]

	if (ofs <= 0) or (width <= 0) or (height <= 0) or (((size - ofs) // height) < width):
		clientserver.Com_Printf("{}: can't load {}, small body\n".format("LoadWal", name))
		filesystem.FS_FreeFile(mt)
		return None

	image = load_image(name, mt[ofs:],
		width, 0,
		height, 0,
		(size - ofs), type, 8)

	filesystem.FS_FreeFile(mt)

	return image


def LoadM8(origname, type, load_image): #const char *, imagetype_t, loadimage_t (returns struct image_s *)

	name = pcx.FixFileExt(origname, "m8", None)

	size, mt = filesystem.FS_LoadFile(name)

	if mt is None:
		return None

	if size < files_h.m8tex_t.packed_size():
		clientserver.Com_Printf("{}: can't load {}, small header\n".format("LoadM8", name))
		filesystem.FS_FreeFile(mt)
		return None

	mt_obj = files_h.m8tex_t()
	mt_obj.load(mt)

	if mt_obj.version != files_h.M8_VERSION:
		clientserver.Com_Printf("{}: can't load {}, wrong magic value.\n".format("LoadM8", name))
		filesystem.FS_FreeFile(mt)
		return None

	width = mt_obj.width[0]
	height = mt_obj.height[0]
	ofs = mt_obj.offsets[0]

	if (ofs <= 0) or (width <= 0) or (height <= 0) or (((size - ofs) // height) < width):
		clientserver.Com_Printf("{}: can't load {}, small body\n".format("LoadM8", name))
		filesystem.FS_FreeFile(mt)
		return None

	image_buffer = bytearray((size - ofs) * 4)
	for i in range(size - ofs):
		value = mt[ofs + i]
		image_buffer[i * 4 + 0] = mt_obj.palette[value].r
		image_buffer[i * 4 + 1] = mt_obj.palette[value].g
		image_buffer[i * 4 + 2] = mt_obj.palette[value].b
		image_buffer[i * 4 + 3] = 0 if value == 255 else 255

	image = load_image(name, image_buffer,
		width, 0,
		height, 0,
		(size - ofs), type, 32)

	filesystem.FS_FreeFile(mt)

	return image


def LoadM32(origname, type, load_image): #const char *, imagetype_t, loadimage_t (returns struct image_s *)

	name = pcx.FixFileExt(origname, "m32", None)

	size, mt = filesystem.FS_LoadFile(name)

	if mt is None:
		return None

	if size < files_h.m32tex_t.packed_size():
		clientserver.Com_Printf("{}: can't load {}, small header\n".format("LoadM32", name))
		filesystem.FS_FreeFile(mt)
		return None

	mt_obj = files_h.m32tex_t()
	mt_obj.load(mt)

	if mt_obj.version != files_h.M32_VERSION:
		clientserver.Com_Printf("{}: can't load {}, wrong magic value.\n".format("LoadM32", name))
		filesystem.FS_FreeFile(mt)
		return None

	width = mt_obj.width[0]
	height = mt_obj.height[0]
	ofs = mt_obj.offsets[0]

	if (ofs <= 0) or (width <= 0) or (height <= 0) or (((size - ofs) // height) < (width * 4)):
		clientserver.Com_Printf("{}: can't load {}, small body\n".format("LoadM32", name))
		filesystem.FS_FreeFile(mt)
		return None

	image = load_image(name, mt[ofs:],
		width, 0,
		height, 0,
		(size - ofs) // 4, type, 32)
	filesystem.FS_FreeFile(mt)

	return image


def GetWalInfo(origname, width, height): #const char *, int *, int *

	name = pcx.FixFileExt(origname, "wal", None)

	size, mt = filesystem.FS_LoadFile(name)

	if mt is None:
		return None, None

	if size < files_h.miptex_t.packed_size():
		filesystem.FS_FreeFile(mt)
		return None, None

	img_header = files_h.miptex_t()
	img_header.load(mt)

	width[0] = img_header.width
	height[0] = img_header.height

	filesystem.FS_FreeFile(mt)

	return width[0], height[0]


def GetM8Info(origname, width, height): #const char *, int *, int *

	name = pcx.FixFileExt(origname, "m8", None)

	size, mt = filesystem.FS_LoadFile(name)

	if mt is None:
		return None, None

	if size < files_h.m8tex_t.packed_size():
		filesystem.FS_FreeFile(mt)
		return None, None

	mt_obj = files_h.m8tex_t()
	mt_obj.load(mt)
	if mt_obj.version != files_h.M8_VERSION:
		filesystem.FS_FreeFile(mt)
		return None, None
	width[0] = mt_obj.width[0]
	height[0] = mt_obj.height[0]

	filesystem.FS_FreeFile(mt)

	return width[0], height[0]


def GetM32Info(origname, width, height): #const char *, int *, int *

	name = pcx.FixFileExt(origname, "m32", None)

	size, mt = filesystem.FS_LoadFile(name)

	if mt is None:
		return None, None

	if size < files_h.m32tex_t.packed_size():
		filesystem.FS_FreeFile(mt)
		return None, None

	mt_obj = files_h.m32tex_t()
	mt_obj.load(mt)
	if mt_obj.version != files_h.M32_VERSION:
		filesystem.FS_FreeFile(mt)
		return None, None

	width[0] = mt_obj.width[0]
	height[0] = mt_obj.height[0]

	filesystem.FS_FreeFile(mt)

	return width[0], height[0]
