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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * Wall textures: .wal, and Heretic II's .m8 and .m32, read with q2data.images.
 *
 * =======================================================================
"""

from collections.abc import Callable

from client.refresh.files import pcx
from common import clientserver, filesystem
from q2data import FormatError
from q2data import images

# load_image(name, pixels, width, realwidth, height, realheight, data_size, type, bits)
LoadImage = Callable[..., object]


def _read(name: str) -> bytes | None:
    size, data = filesystem.FS_LoadFile(name)
    return None if data is None else bytes(data)


def LoadWal(origname: str, type_: object, load_image: LoadImage) -> object | None:  # noqa: N802
    """An 8-bit .wal texture, as an image of the renderer."""
    name = pcx.FixFileExt(origname, "wal", None)
    data = _read(name)
    if data is None:
        return None
    try:
        wal = images.load_wal(data)
    except FormatError as err:
        clientserver.Com_Printf(f"LoadWal: can't load {name}, {err}\n")
        return None
    pixels = bytearray(wal.pixels.tobytes())
    return load_image(name, pixels, wal.width, 0, wal.height, 0, len(pixels), type_, 8)


def _load_mip_texture(origname: str, ext: str, loader: Callable[[bytes], images.MipTexture],
                      type_: object, load_image: LoadImage, func: str) -> object | None:
    name = pcx.FixFileExt(origname, ext, None)
    data = _read(name)
    if data is None:
        return None
    try:
        texture = loader(data)
    except FormatError as err:
        reason = str(err)
        if reason == "wrong magic value":
            reason += "."
        clientserver.Com_Printf(f"{func}: can't load {name}, {reason}\n")
        return None
    pixels = bytearray(texture.rgba.tobytes())
    return load_image(name, pixels, texture.width, 0, texture.height, 0,
                      texture.width * texture.height, type_, 32)


def LoadM8(origname: str, type_: object, load_image: LoadImage) -> object | None:  # noqa: N802
    """A Heretic II .m8 texture (8-bit with its own palette), as RGBA."""
    return _load_mip_texture(origname, "m8", images.load_m8, type_, load_image, "LoadM8")


def LoadM32(origname: str, type_: object, load_image: LoadImage) -> object | None:  # noqa: N802
    """A Heretic II .m32 texture (RGBA)."""
    return _load_mip_texture(origname, "m32", images.load_m32, type_, load_image, "LoadM32")


def GetWalInfo(origname: str) -> tuple[int, int] | tuple[None, None]:  # noqa: N802
    """The size of a .wal texture, or (None, None)."""
    data = _read(pcx.FixFileExt(origname, "wal", None))
    if data is None:
        return None, None
    try:
        return images.wal_size(data)
    except FormatError:
        return None, None


def _mip_texture_info(origname: str, ext: str) -> tuple[int, int] | tuple[None, None]:
    data = _read(pcx.FixFileExt(origname, ext, None))
    if data is None:
        return None, None
    try:
        return images.mip_texture_size(data, ext)
    except FormatError:
        return None, None


def GetM8Info(origname: str) -> tuple[int, int] | tuple[None, None]:  # noqa: N802
    return _mip_texture_info(origname, "m8")


def GetM32Info(origname: str) -> tuple[int, int] | tuple[None, None]:  # noqa: N802
    return _mip_texture_info(origname, "m32")
