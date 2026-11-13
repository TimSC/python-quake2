"""Quake II images: PCX, WAL, Heretic II's M8 and M32, and TGA/PNG/JPG/BMP.

Paletted images keep their indices (``pixels`` is (height, width) uint8, with
the 256-colour ``palette``); true-colour images are (height, width, 4) RGBA.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field

import numpy as np
from PIL import Image as PILImage

from q2data.binary import decode_name, encode_name
from q2data.errors import FormatError

PALETTE_SIZE = 768


@dataclass(slots=True)
class Image:
    width: int
    height: int
    pixels: np.ndarray                 # (h, w) indices or (h, w, 4) RGBA, uint8
    palette: np.ndarray | None = None  # (256, 3) uint8, for indexed pixels
    warnings: list[str] = field(default_factory=list)

    @property
    def indexed(self) -> bool:
        return self.pixels.ndim == 2

    def to_rgba(self, palette: np.ndarray | None = None,
                transparent_index: int | None = None) -> np.ndarray:
        """True-colour pixels; indexed images go through ``palette``
        (or their own), with ``transparent_index`` made fully transparent."""
        if not self.indexed:
            return self.pixels
        pal = self.palette if palette is None else palette
        if pal is None:
            raise ValueError("indexed image without a palette")
        rgba = np.empty((256, 4), dtype=np.uint8)
        rgba[:, :3] = np.asarray(pal, np.uint8).reshape(256, 3)
        rgba[:, 3] = 255
        if transparent_index is not None:
            rgba[transparent_index, 3] = 0
        return rgba[self.pixels]


# --------------------------------------------------------------------------- PCX

PCX_HEADER = struct.Struct("<4B6H48s2B2H58s")


@dataclass(slots=True, frozen=True)
class PcxHeader:
    manufacturer: int
    version: int
    encoding: int
    bits_per_pixel: int
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    hres: int
    vres: int
    header_palette: bytes
    reserved: int
    color_planes: int
    bytes_per_line: int
    palette_type: int

    @property
    def width(self) -> int:
        return self.xmax - self.xmin + 1

    @property
    def height(self) -> int:
        return self.ymax - self.ymin + 1


def read_pcx_header(data: bytes) -> PcxHeader:
    if len(data) < PCX_HEADER.size:
        raise FormatError("too short to be a PCX file")
    values = PCX_HEADER.unpack_from(data)
    header = PcxHeader(*values[:15])  # the last value is the filler
    if (header.manufacturer != 0x0A or header.version != 5 or header.encoding != 1
            or header.width - 1 <= 0 or header.height - 1 <= 0
            or header.bytes_per_line <= 0 or header.color_planes <= 0
            or header.bits_per_pixel <= 0):
        raise FormatError(f"bad PCX file: version: {header.manufacturer}:{header.version}, "
                          f"encoding: {header.encoding}")
    return header


def _rle_lines(data: bytes, start: int, rows: int, line_bytes: int, buffer_size: int
               ) -> tuple[np.ndarray, bool]:
    """Decode ``rows`` run-length coded lines of ``line_bytes`` bytes each.

    As Quake II does: a run may spill past ``line_bytes`` into the line buffer
    (``buffer_size`` bytes) but never into the next line, and running out of
    data or buffer is reported as an issue rather than an error.
    """
    out = np.zeros((rows, buffer_size), dtype=np.uint8)
    issues = False
    pos, end = start, len(data)
    for y in range(rows):
        line = out[y]
        x = 0
        while x < line_bytes:
            if pos >= end:
                issues = True
                break
            value = data[pos]
            pos += 1
            if value & 0xC0 == 0xC0:
                run = value & 0x3F
                if pos >= end:
                    issues = True
                    break
                value = data[pos]
                pos += 1
            else:
                run = 1
            if x + run > buffer_size:
                line[x:] = value
                x = buffer_size
                issues = True
                break
            line[x:x + run] = value
            x += run
    return out, issues


def load_pcx(data: bytes) -> Image:
    """Decode a PCX file as Yamagi Quake II does (8-bit paletted being the
    usual case; 24/32-bit and 1/2/4-bit files are read too)."""
    header = read_pcx_header(data)
    width, height = header.width, header.height
    planes, bits, bpl = header.color_planes, header.bits_per_pixel, header.bytes_per_line
    warnings: list[str] = []

    if planes == 1 and bits == 8:
        palette = None
        if len(data) > PALETTE_SIZE:
            palette = np.frombuffer(data, np.uint8, PALETTE_SIZE,
                                    len(data) - PALETTE_SIZE).reshape(256, 3).copy()
            if data[len(data) - PALETTE_SIZE - 1] != 0x0C:
                warnings.append("has no palette marker")
        else:
            warnings.append("possible size issues")
        pixels = _pillow_pcx(data, header)
        if pixels is None:
            if bpl <= width - 1:
                warnings.append("possible size issues")
            lines, issues = _rle_lines(data, PCX_HEADER.size, height, bpl, max(bpl, width))
            pixels = np.ascontiguousarray(lines[:, :width])
            if issues and "possible size issues" not in warnings:
                warnings.append("possible size issues")
        return Image(width, height, pixels, palette, warnings)

    if planes in (3, 4) and bits == 8:
        if bpl <= width - 1:
            warnings.append("possible size issues")
        lines, issues = _rle_lines(data, PCX_HEADER.size, height, bpl * planes,
                                   max(bpl, width) * planes)
        rgba = np.full((height, width, 4), 255, dtype=np.uint8)
        for plane in range(planes):
            rgba[:, :, plane] = lines[:, plane * bpl:plane * bpl + width]
        if issues:
            warnings.append("possible size issues")
        return Image(width, height, rgba, None, _uncommon(warnings))

    header_palette = np.zeros((256, 3), dtype=np.uint8)
    header_palette.reshape(-1)[:48] = np.frombuffer(header.header_palette, np.uint8)

    if bits == 1:
        lines, issues = _rle_lines(data, PCX_HEADER.size, height, bpl * planes, bpl * planes)
        x = np.arange(width)
        pixels = np.zeros((height, width), dtype=np.uint8)
        for plane in range(planes - 1, -1, -1):
            plane_bits = (lines[:, plane * bpl + (x >> 3)] >> (7 - (x & 7))) & 1
            pixels = (pixels << 1) | plane_bits.astype(np.uint8)
        if issues:
            warnings.append("possible size issues")
        return Image(width, height, pixels, header_palette, _uncommon(warnings))

    if planes == 1 and bits in (2, 4):
        lines, issues = _rle_lines(data, PCX_HEADER.size, height, bpl, bpl)
        per_byte = 8 // bits
        x = np.arange(width)
        shift = bits * ((per_byte - 1) - x % per_byte)
        pixels = ((lines[:, x // per_byte] >> shift) & ((1 << bits) - 1)).astype(np.uint8)
        if issues:
            warnings.append("possible size issues")
        return Image(width, height, pixels, header_palette, _uncommon(warnings))

    raise FormatError(f"bad PCX file: planes: {planes}, bits: {bits}")


def _uncommon(warnings: list[str]) -> list[str]:
    return [*warnings, "has uncommon flags, could be unsupported by other engines"]


def _pillow_pcx(data: bytes, header: PcxHeader) -> np.ndarray | None:
    """Pillow's (fast, C) decoder, used only where it matches Quake II's."""
    if header.xmin or header.ymin or header.bytes_per_line != header.width:
        return None
    try:
        with PILImage.open(io.BytesIO(data)) as im:
            im.load()
            if im.mode != "P" or im.size != (header.width, header.height):
                return None
            return np.asarray(im, dtype=np.uint8).copy()
    except (OSError, ValueError, SyntaxError):
        return None


def write_pcx(pixels: np.ndarray, palette: np.ndarray) -> bytes:
    """Encode an 8-bit paletted PCX (run-length coded, 256-colour palette)."""
    pixels = np.asarray(pixels, np.uint8)
    height, width = pixels.shape
    bpl = width + (width & 1)
    header = PCX_HEADER.pack(0x0A, 5, 1, 8, 0, 0, width - 1, height - 1, 72, 72, b"\0" * 48,
                             0, 1, bpl, 1, b"\0" * 58)
    body = bytearray()
    for row in pixels:
        line = bytes(row) + b"\0" * (bpl - width)
        i = 0
        while i < len(line):
            value = line[i]
            run = 1
            while i + run < len(line) and line[i + run] == value and run < 63:
                run += 1
            if run > 1 or value & 0xC0 == 0xC0:
                body += bytes((0xC0 | run, value))
            else:
                body.append(value)
            i += run
    return header + bytes(body) + b"\x0c" + np.asarray(palette, np.uint8).tobytes()


def load_palette(data: bytes) -> np.ndarray:
    """The 256-colour palette at the end of a PCX file (e.g. ``colormap.pcx``)."""
    if len(data) < PALETTE_SIZE:
        raise FormatError("too short to hold a palette")
    return np.frombuffer(data, np.uint8, PALETTE_SIZE,
                         len(data) - PALETTE_SIZE).reshape(256, 3).copy()


# --------------------------------------------------------------------------- WAL

MIP_LEVELS = 4
WAL_HEADER = struct.Struct("<32s2I4I32s3i")


@dataclass(slots=True)
class Wal:
    """A ``.wal`` texture: its header and the four mip levels."""

    name: str
    width: int
    height: int
    anim_name: str  # next frame in the animation chain
    flags: int
    contents: int
    value: int
    mips: list[np.ndarray]  # each (h, w) uint8 palette indices; mips[0] is full size

    @property
    def pixels(self) -> np.ndarray:
        return self.mips[0]


def load_wal(data: bytes) -> Wal:
    if len(data) < WAL_HEADER.size:
        raise FormatError("small header")
    name, width, height, *offsets_and_rest = WAL_HEADER.unpack_from(data)
    offsets = offsets_and_rest[:MIP_LEVELS]
    anim_name, flags, contents, value = offsets_and_rest[MIP_LEVELS:]
    _check_body(len(data), offsets[0], width, height, 1)
    mips = []
    for level, offset in enumerate(offsets):
        w, h = max(width >> level, 1), max(height >> level, 1)
        if level and (offset <= 0 or offset + w * h > len(data)):
            break
        mips.append(np.frombuffer(data, np.uint8, w * h, offset).reshape(h, w).copy())
    return Wal(decode_name(name), width, height, decode_name(anim_name), flags, contents,
               value, mips)


def _check_body(size: int, offset: int, width: int, height: int, bytes_per_pixel: int
                ) -> None:
    if offset <= 0 or width <= 0 or height <= 0 or (size - offset) // height < width * \
            bytes_per_pixel:
        raise FormatError("small body")


def write_wal(wal: Wal) -> bytes:
    offsets = []
    body = b""
    position = WAL_HEADER.size
    for mip in wal.mips:
        offsets.append(position)
        raw = np.ascontiguousarray(mip, np.uint8).tobytes()
        body += raw
        position += len(raw)
    offsets += [0] * (MIP_LEVELS - len(offsets))
    header = WAL_HEADER.pack(encode_name(wal.name, 32), wal.width, wal.height, *offsets,
                             encode_name(wal.anim_name, 32), wal.flags, wal.contents,
                             wal.value)
    return header + body


def wal_size(data: bytes) -> tuple[int, int]:
    """The width and height of a WAL texture without decoding it."""
    if len(data) < WAL_HEADER.size:
        raise FormatError("small header")
    _, width, height, *_ = WAL_HEADER.unpack_from(data)
    return width, height


# ---------------------------------------------------------------- M8 and M32 (Heretic II)

M8_VERSION = 2
M8_MIP_LEVELS = 16
M8_HEADER = struct.Struct("<I32s16I16I16I32s768s3i")

M32_VERSION = 4
M32_MIP_LEVELS = 16
M32_HEADER = struct.Struct("<i128s128s128s128s16I16I16I3i2fi128s5f2i80s")


@dataclass(slots=True)
class MipTexture:
    """An M8 or M32 texture: the full-size level as RGBA, and its header data."""

    name: str
    width: int
    height: int
    anim_name: str
    flags: int
    contents: int
    value: int
    rgba: np.ndarray  # (h, w, 4) uint8


def load_m8(data: bytes) -> MipTexture:
    if len(data) < M8_HEADER.size:
        raise FormatError("small header")
    values = M8_HEADER.unpack_from(data)
    if values[0] != M8_VERSION:
        raise FormatError("wrong magic value")
    name = decode_name(values[1])
    width, height, offset = values[2], values[2 + M8_MIP_LEVELS], values[2 + 2 * M8_MIP_LEVELS]
    anim_name = decode_name(values[2 + 3 * M8_MIP_LEVELS])
    palette = np.frombuffer(values[3 + 3 * M8_MIP_LEVELS], np.uint8).reshape(256, 3)
    flags, contents, value = values[4 + 3 * M8_MIP_LEVELS:]
    _check_body(len(data), offset, width, height, 1)
    indices = np.frombuffer(data, np.uint8, width * height, offset).reshape(height, width)
    rgba = np.empty((height, width, 4), np.uint8)
    rgba[..., :3] = palette[indices]
    rgba[..., 3] = np.where(indices == 255, 0, 255)
    return MipTexture(name, width, height, anim_name, flags, contents, value, rgba)


def load_m32(data: bytes) -> MipTexture:
    if len(data) < M32_HEADER.size:
        raise FormatError("small header")
    values = M32_HEADER.unpack_from(data)
    if values[0] != M32_VERSION:
        raise FormatError("wrong magic value")
    name, anim_name = decode_name(values[1]), decode_name(values[3])
    width, height, offset = values[5], values[5 + M32_MIP_LEVELS], values[5 + 2 * M32_MIP_LEVELS]
    flags, contents, value = values[5 + 3 * M32_MIP_LEVELS:8 + 3 * M32_MIP_LEVELS]
    _check_body(len(data), offset, width, height, 4)
    rgba = np.frombuffer(data, np.uint8, width * height * 4, offset).reshape(height, width, 4)
    return MipTexture(name, width, height, anim_name, flags, contents, value, rgba.copy())


def mip_texture_size(data: bytes, kind: str) -> tuple[int, int]:
    """The width and height of an M8 (``"m8"``) or M32 (``"m32"``) texture."""
    header, version, first = ((M8_HEADER, M8_VERSION, 2) if kind == "m8"
                              else (M32_HEADER, M32_VERSION, 5))
    levels = M8_MIP_LEVELS if kind == "m8" else M32_MIP_LEVELS
    if len(data) < header.size:
        raise FormatError("small header")
    values = header.unpack_from(data)
    if values[0] != version:
        raise FormatError("wrong magic value")
    return values[first], values[first + levels]


# ------------------------------------------------------------- other formats (Pillow)

def load_rgba(data: bytes) -> Image:
    """Decode a TGA, PNG, JPG or BMP file into RGBA."""
    try:
        with PILImage.open(io.BytesIO(data)) as im:
            rgba = np.asarray(im.convert("RGBA"), dtype=np.uint8).copy()
    except (OSError, ValueError, SyntaxError) as err:
        raise FormatError(str(err)) from None
    height, width = rgba.shape[:2]
    return Image(width, height, rgba)


def image_size(data: bytes) -> tuple[int, int]:
    """The width and height of a TGA, PNG, JPG or BMP file, without decoding it."""
    try:
        with PILImage.open(io.BytesIO(data)) as im:
            return im.size
    except (OSError, ValueError, SyntaxError) as err:
        raise FormatError(str(err)) from None
