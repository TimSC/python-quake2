"""Quake II alias models (``.md2``, ``IDP2`` version 8)."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np

from q2data.binary import decode_name, encode_name, read_records
from q2data.errors import FormatError

MD2_IDENT = b"IDP2"
MD2_VERSION = 8
SKIN_NAME_SIZE = 64

# The engine's limits for alias models.
MAX_TRIANGLES = 4096
MAX_VERTS = 2048
MAX_FRAMES = 512
MAX_SKINS = 32
FRAME_NAME_SIZE = 16

HEADER = struct.Struct("<4s16i")
FRAME_HEADER = struct.Struct("<3f3f16s")

ST_VERT = np.dtype([("s", "<i2"), ("t", "<i2")])
TRIANGLE = np.dtype([("index_xyz", "<i2", 3), ("index_st", "<i2", 3)])
# v: position scaled into the frame's box; normal: index into the normal table
TRI_VERTEX = np.dtype([("v", "u1", 3), ("normal", "u1")])


@dataclass(slots=True)
class Md2Frame:
    name: str
    scale: np.ndarray       # (3,) float32: multiply the byte positions by this
    translate: np.ndarray   # (3,) float32: then add this
    verts: np.ndarray       # (num_xyz,) TRI_VERTEX

    def positions(self) -> np.ndarray:
        """Vertex positions in model space, (num_xyz, 3) float32."""
        return self.verts["v"].astype(np.float32) * self.scale + self.translate


@dataclass(slots=True)
class Md2:
    skin_width: int
    skin_height: int
    skins: list[str] = field(default_factory=list)
    st: np.ndarray = field(default_factory=lambda: np.zeros(0, ST_VERT))
    triangles: np.ndarray = field(default_factory=lambda: np.zeros(0, TRIANGLE))
    frames: list[Md2Frame] = field(default_factory=list)
    # The GL command list as int32 words: a count (positive for a strip,
    # negative for a fan, 0 to end), then count * (s float, t float, index).
    glcmds: np.ndarray = field(default_factory=lambda: np.zeros(1, np.int32))

    @property
    def num_xyz(self) -> int:
        return len(self.frames[0].verts) if self.frames else 0


@dataclass(slots=True, frozen=True)
class Md2Header:
    skin_width: int
    skin_height: int
    frame_size: int
    num_skins: int
    num_xyz: int
    num_st: int
    num_tris: int
    num_glcmds: int
    num_frames: int
    ofs_skins: int
    ofs_st: int
    ofs_tris: int
    ofs_frames: int
    ofs_glcmds: int
    ofs_end: int


def read_header(data: bytes) -> Md2Header:
    if len(data) < HEADER.size:
        raise FormatError("too short to be a model")
    ident, version, *values = HEADER.unpack_from(data)
    if ident != MD2_IDENT:
        raise FormatError("not an MD2 model")
    if version != MD2_VERSION:
        raise FormatError(f"has wrong version number ({version} should be {MD2_VERSION})")
    header = Md2Header(*values)
    if len(data) < header.ofs_end:
        raise FormatError(f"file size({len(data)}) too small, should be {header.ofs_end}")
    return header


def load_md2(data: bytes) -> Md2:
    header = read_header(data)
    skins = [decode_name(data[header.ofs_skins + i * SKIN_NAME_SIZE:
                              header.ofs_skins + (i + 1) * SKIN_NAME_SIZE])
             for i in range(max(header.num_skins, 0))]
    if header.ofs_skins + max(header.num_skins, 0) * SKIN_NAME_SIZE > len(data):
        raise FormatError("skins lie outside the file")
    st = read_records(data, header.ofs_st, header.num_st, ST_VERT, "st vertices")
    triangles = read_records(data, header.ofs_tris, header.num_tris, TRIANGLE, "triangles")
    glcmds = read_records(data, header.ofs_glcmds, header.num_glcmds, np.dtype("<i4"),
                          "gl commands")

    frames: list[Md2Frame] = []
    vert_bytes = header.num_xyz * TRI_VERTEX.itemsize
    if header.num_frames > 0 and header.frame_size < FRAME_HEADER.size + vert_bytes:
        raise FormatError("frame size is too small for its vertices")
    for i in range(max(header.num_frames, 0)):
        start = header.ofs_frames + i * header.frame_size
        if start + FRAME_HEADER.size > len(data):
            raise FormatError("frames lie outside the file")
        values = FRAME_HEADER.unpack_from(data, start)
        verts = read_records(data, start + FRAME_HEADER.size, header.num_xyz, TRI_VERTEX,
                             "frame vertices")
        frames.append(Md2Frame(decode_name(values[6]), np.array(values[0:3], np.float32),
                               np.array(values[3:6], np.float32), verts))

    return Md2(header.skin_width, header.skin_height, skins, st, triangles, frames,
               glcmds.astype(np.int32))


def write_md2(model: Md2) -> bytes:
    num_xyz = model.num_xyz
    frame_size = FRAME_HEADER.size + num_xyz * TRI_VERTEX.itemsize
    skins = b"".join(encode_name(s, SKIN_NAME_SIZE) for s in model.skins)
    frames = b"".join(
        FRAME_HEADER.pack(*map(float, f.scale), *map(float, f.translate),
                          encode_name(f.name, FRAME_NAME_SIZE))
        + np.ascontiguousarray(f.verts, TRI_VERTEX).tobytes()
        for f in model.frames)
    st = np.ascontiguousarray(model.st, ST_VERT).tobytes()
    tris = np.ascontiguousarray(model.triangles, TRIANGLE).tobytes()
    glcmds = np.asarray(model.glcmds, "<i4").tobytes()

    ofs_skins = HEADER.size
    ofs_st = ofs_skins + len(skins)
    ofs_tris = ofs_st + len(st)
    ofs_frames = ofs_tris + len(tris)
    ofs_glcmds = ofs_frames + len(frames)
    ofs_end = ofs_glcmds + len(glcmds)
    header = HEADER.pack(MD2_IDENT, MD2_VERSION, model.skin_width, model.skin_height,
                         frame_size, len(model.skins), num_xyz, len(model.st),
                         len(model.triangles), len(glcmds) // 4, len(model.frames),
                         ofs_skins, ofs_st, ofs_tris, ofs_frames, ofs_glcmds, ofs_end)
    return header + skins + st + tris + frames + glcmds
