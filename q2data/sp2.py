"""Quake II sprites (``.sp2``, ``IDS2`` version 2)."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from q2data.binary import decode_name, encode_name
from q2data.errors import FormatError

SP2_IDENT = b"IDS2"
SP2_VERSION = 2
NAME_SIZE = 64

HEADER = struct.Struct("<4s2i")
FRAME = struct.Struct("<4i64s")


@dataclass(slots=True)
class SpriteFrame:
    width: int
    height: int
    origin_x: int  # raster coordinates inside the picture
    origin_y: int
    name: str      # the picture file


@dataclass(slots=True)
class Sprite:
    frames: list[SpriteFrame] = field(default_factory=list)


def load_sp2(data: bytes) -> Sprite:
    if len(data) < HEADER.size:
        raise FormatError("too short to be a sprite")
    ident, version, num_frames = HEADER.unpack_from(data)
    if ident != SP2_IDENT:
        raise FormatError("not a sprite")
    if version != SP2_VERSION:
        raise FormatError(f"has wrong version number ({version} should be {SP2_VERSION})")
    if num_frames < 0 or HEADER.size + num_frames * FRAME.size > len(data):
        raise FormatError("frames lie outside the file")
    frames = []
    for i in range(num_frames):
        w, h, x, y, name = FRAME.unpack_from(data, HEADER.size + i * FRAME.size)
        frames.append(SpriteFrame(w, h, x, y, decode_name(name)))
    return Sprite(frames)


def write_sp2(sprite: Sprite) -> bytes:
    out = HEADER.pack(SP2_IDENT, SP2_VERSION, len(sprite.frames))
    for f in sprite.frames:
        out += FRAME.pack(f.width, f.height, f.origin_x, f.origin_y,
                          encode_name(f.name, NAME_SIZE))
    return out
