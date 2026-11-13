"""Quake II maps (``.bsp``, ``IBSP`` version 38).

Every lump is loaded as-is into a numpy record array (or bytes / str), so one
loader serves collision, the renderers and tools. Building engine structures
(collision trees, GPU buffers) from these arrays is up to the caller.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field, fields
from enum import IntEnum, IntFlag

import numpy as np

from q2data.binary import ENCODING, read_records
from q2data.errors import FormatError

BSP_IDENT = b"IBSP"
BSP_VERSION = 38

MAX_LIGHTMAPS = 4  # light styles per face

# Upper design bounds of the format (the map compiler's and the engine's limits).
MAX_MAP_MODELS = 1024
MAX_MAP_BRUSHES = 8192
MAX_MAP_ENTITIES = 2048
MAX_MAP_ENTSTRING = 0x40000
MAX_MAP_TEXINFO = 8192
MAX_MAP_AREAS = 256
MAX_MAP_AREAPORTALS = 1024
MAX_MAP_PLANES = 65536
MAX_MAP_NODES = 65536
MAX_MAP_BRUSHSIDES = 65536
MAX_MAP_LEAFS = 65536
MAX_MAP_VERTS = 65536
MAX_MAP_FACES = 65536
MAX_MAP_LEAFFACES = 65536
MAX_MAP_LEAFBRUSHES = 65536
MAX_MAP_PORTALS = 65536
MAX_MAP_EDGES = 128000
MAX_MAP_SURFEDGES = 256000
MAX_MAP_LIGHTING = 0x200000
MAX_MAP_VISIBILITY = 0x100000


class Lump(IntEnum):
    ENTITIES = 0
    PLANES = 1
    VERTICES = 2
    VISIBILITY = 3
    NODES = 4
    TEXINFO = 5
    FACES = 6
    LIGHTING = 7
    LEAFS = 8
    LEAF_FACES = 9
    LEAF_BRUSHES = 10
    EDGES = 11
    SURF_EDGES = 12
    MODELS = 13
    BRUSHES = 14
    BRUSH_SIDES = 15
    POP = 16
    AREAS = 17
    AREA_PORTALS = 18


HEADER = struct.Struct("<4si" + "ii" * len(Lump))


class Contents(IntFlag):
    SOLID = 0x1
    WINDOW = 0x2
    AUX = 0x4
    LAVA = 0x8
    SLIME = 0x10
    WATER = 0x20
    MIST = 0x40
    AREAPORTAL = 0x8000
    PLAYERCLIP = 0x10000
    MONSTERCLIP = 0x20000
    CURRENT_0 = 0x40000
    CURRENT_90 = 0x80000
    CURRENT_180 = 0x100000
    CURRENT_270 = 0x200000
    CURRENT_UP = 0x400000
    CURRENT_DOWN = 0x800000
    ORIGIN = 0x1000000
    MONSTER = 0x2000000
    DEADMONSTER = 0x4000000
    DETAIL = 0x8000000
    TRANSLUCENT = 0x10000000
    LADDER = 0x20000000


class SurfaceFlags(IntFlag):
    LIGHT = 0x1
    SLICK = 0x2
    SKY = 0x4
    WARP = 0x8
    TRANS33 = 0x10
    TRANS66 = 0x20
    FLOWING = 0x40
    NODRAW = 0x80


class PlaneType(IntEnum):
    X = 0
    Y = 1
    Z = 2
    ANY_X = 3
    ANY_Y = 4
    ANY_Z = 5


PLANE = np.dtype([("normal", "<f4", 3), ("dist", "<f4"), ("type", "<i4")])
VERTEX = np.dtype([("point", "<f4", 3)])
# children: negative numbers are -(leaf + 1)
NODE = np.dtype([("plane", "<i4"), ("children", "<i4", 2), ("mins", "<i2", 3),
                 ("maxs", "<i2", 3), ("first_face", "<u2"), ("num_faces", "<u2")])
TEXINFO = np.dtype([("vecs", "<f4", (2, 4)), ("flags", "<i4"), ("value", "<i4"),
                    ("texture", "S32"), ("next_texinfo", "<i4")])
FACE = np.dtype([("plane", "<u2"), ("side", "<i2"), ("first_edge", "<i4"),
                 ("num_edges", "<i2"), ("texinfo", "<i2"), ("styles", "u1", MAX_LIGHTMAPS),
                 ("light_offset", "<i4")])
LEAF = np.dtype([("contents", "<i4"), ("cluster", "<i2"), ("area", "<i2"),
                 ("mins", "<i2", 3), ("maxs", "<i2", 3), ("first_leaf_face", "<u2"),
                 ("num_leaf_faces", "<u2"), ("first_leaf_brush", "<u2"),
                 ("num_leaf_brushes", "<u2")])
EDGE = np.dtype([("v", "<u2", 2)])
MODEL = np.dtype([("mins", "<f4", 3), ("maxs", "<f4", 3), ("origin", "<f4", 3),
                  ("head_node", "<i4"), ("first_face", "<i4"), ("num_faces", "<i4")])
BRUSH = np.dtype([("first_side", "<i4"), ("num_sides", "<i4"), ("contents", "<i4")])
BRUSH_SIDE = np.dtype([("plane", "<u2"), ("texinfo", "<i2")])
AREA = np.dtype([("num_area_portals", "<i4"), ("first_area_portal", "<i4")])
AREA_PORTAL = np.dtype([("portal", "<i4"), ("other_area", "<i4")])

# Lumps that are arrays of fixed-size records.
RECORD_LUMPS: dict[Lump, np.dtype] = {
    Lump.PLANES: PLANE,
    Lump.VERTICES: VERTEX,
    Lump.NODES: NODE,
    Lump.TEXINFO: TEXINFO,
    Lump.FACES: FACE,
    Lump.LEAFS: LEAF,
    Lump.LEAF_FACES: np.dtype("<u2"),
    Lump.LEAF_BRUSHES: np.dtype("<u2"),
    Lump.EDGES: EDGE,
    Lump.SURF_EDGES: np.dtype("<i4"),
    Lump.MODELS: MODEL,
    Lump.BRUSHES: BRUSH,
    Lump.BRUSH_SIDES: BRUSH_SIDE,
    Lump.AREAS: AREA,
    Lump.AREA_PORTALS: AREA_PORTAL,
}


class VisType(IntEnum):
    PVS = 0
    PHS = 1


@dataclass(slots=True)
class Visibility:
    """The visibility lump: per cluster, offsets of its compressed PVS and PHS.

    ``offsets[cluster, VisType.PVS]`` is a byte offset into ``data`` (the whole
    lump, header included), as Quake II uses it.
    """

    data: bytes
    offsets: np.ndarray  # (num_clusters, 2) int32

    @property
    def num_clusters(self) -> int:
        return len(self.offsets)

    @classmethod
    def from_bytes(cls, data: bytes) -> Visibility:
        if not data:
            return cls(b"", np.zeros((0, 2), dtype=np.int32))
        if len(data) < 4:
            raise FormatError("visibility lump is too short")
        (num_clusters,) = struct.unpack_from("<i", data)
        offsets = read_records(data, 4, num_clusters * 2, np.dtype("<i4"), "visibility offsets")
        return cls(data, offsets.reshape(num_clusters, 2))

    def cluster_vis(self, cluster: int, kind: VisType = VisType.PVS, num_clusters:
                    int | None = None) -> np.ndarray:
        """Decompress one cluster's PVS or PHS into a bool array per cluster."""
        count = self.num_clusters if num_clusters is None else num_clusters
        row_bytes = (count + 7) >> 3
        out = bytearray()
        pos = int(self.offsets[cluster, kind])
        data = self.data
        while len(out) < row_bytes:
            if pos >= len(data):
                break
            byte = data[pos]
            if byte:
                out.append(byte)
                pos += 1
                continue
            run = data[pos + 1] if pos + 1 < len(data) else 0
            out.extend(b"\0" * run)
            pos += 2
        bits = np.unpackbits(np.frombuffer(bytes(out[:row_bytes]).ljust(row_bytes, b"\0"),
                                           dtype=np.uint8), bitorder="little")
        return bits[:count].astype(bool)


def _empty(dtype: np.dtype) -> np.ndarray:
    return np.zeros(0, dtype=dtype)


@dataclass(slots=True)
class Bsp:
    """All lumps of a map, in file order."""

    entities: str = ""
    planes: np.ndarray = field(default_factory=lambda: _empty(PLANE))
    vertices: np.ndarray = field(default_factory=lambda: _empty(VERTEX))
    visibility: Visibility = field(default_factory=lambda: Visibility.from_bytes(b""))
    nodes: np.ndarray = field(default_factory=lambda: _empty(NODE))
    texinfo: np.ndarray = field(default_factory=lambda: _empty(TEXINFO))
    faces: np.ndarray = field(default_factory=lambda: _empty(FACE))
    lighting: bytes = b""
    leafs: np.ndarray = field(default_factory=lambda: _empty(LEAF))
    leaf_faces: np.ndarray = field(default_factory=lambda: _empty(np.dtype("<u2")))
    leaf_brushes: np.ndarray = field(default_factory=lambda: _empty(np.dtype("<u2")))
    edges: np.ndarray = field(default_factory=lambda: _empty(EDGE))
    surf_edges: np.ndarray = field(default_factory=lambda: _empty(np.dtype("<i4")))
    models: np.ndarray = field(default_factory=lambda: _empty(MODEL))
    brushes: np.ndarray = field(default_factory=lambda: _empty(BRUSH))
    brush_sides: np.ndarray = field(default_factory=lambda: _empty(BRUSH_SIDE))
    pop: bytes = b""
    areas: np.ndarray = field(default_factory=lambda: _empty(AREA))
    area_portals: np.ndarray = field(default_factory=lambda: _empty(AREA_PORTAL))

    def texture_names(self) -> list[str]:
        return [name.decode(ENCODING) for name in
                (bytes(t).split(b"\0", 1)[0] for t in self.texinfo["texture"])]


# Lump number -> Bsp attribute, in lump order.
LUMP_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(Bsp))
assert len(LUMP_FIELDS) == len(Lump)


@dataclass(slots=True, frozen=True)
class LumpInfo:
    offset: int
    length: int


def read_header(data: bytes) -> list[LumpInfo]:
    """Check the header and return where each lump is."""
    if len(data) < HEADER.size:
        raise FormatError("too short to be a map")
    values = HEADER.unpack_from(data)
    ident, version = values[0], values[1]
    if ident != BSP_IDENT:
        raise FormatError("not a Quake II map (bad ident)")
    if version != BSP_VERSION:
        raise FormatError(f"wrong version number ({version} should be {BSP_VERSION})")
    lumps = [LumpInfo(values[2 + 2 * i], values[3 + 2 * i]) for i in range(len(Lump))]
    for lump, info in zip(Lump, lumps, strict=True):
        if info.offset < 0 or info.length < 0 or info.offset + info.length > len(data):
            raise FormatError(f"lump {lump.name.lower()} lies outside the file")
    return lumps


def lump_records(data: bytes, info: LumpInfo, lump: Lump) -> np.ndarray:
    """Read one record lump; its size must be a whole number of records."""
    dtype = RECORD_LUMPS[lump]
    if info.length % dtype.itemsize:
        raise FormatError(f"funny lump size in {lump.name.lower()}")
    return read_records(data, info.offset, info.length // dtype.itemsize, dtype,
                        lump.name.lower())


def load_bsp(data: bytes) -> Bsp:
    """Parse a whole map file."""
    lumps = read_header(data)
    values: dict[str, object] = {}
    for lump, info in zip(Lump, lumps, strict=True):
        raw = data[info.offset:info.offset + info.length]
        name = LUMP_FIELDS[lump]
        if lump in RECORD_LUMPS:
            values[name] = lump_records(data, info, lump)
        elif lump is Lump.ENTITIES:
            values[name] = raw.split(b"\0", 1)[0].decode(ENCODING)
        elif lump is Lump.VISIBILITY:
            values[name] = Visibility.from_bytes(raw)
        else:
            values[name] = raw
    return Bsp(**values)


def write_bsp(bsp: Bsp) -> bytes:
    """Serialise a map; lumps are written in order, 4-byte aligned."""
    chunks: list[bytes] = []
    for name in LUMP_FIELDS:
        value = getattr(bsp, name)
        if isinstance(value, np.ndarray):
            chunks.append(value.tobytes())
        elif isinstance(value, Visibility):
            chunks.append(value.data)
        elif isinstance(value, str):
            chunks.append(value.encode(ENCODING) + b"\0")
        else:
            chunks.append(bytes(value))

    offset = HEADER.size
    header_values: list[object] = [BSP_IDENT, BSP_VERSION]
    body = bytearray()
    for chunk in chunks:
        header_values += [offset, len(chunk)]
        body += chunk
        padding = -len(chunk) % 4
        body += b"\0" * padding
        offset += len(chunk) + padding
    return HEADER.pack(*header_values) + bytes(body)


def build_visibility(rows: list[list[int]], phs_rows: list[list[int]] | None = None
                     ) -> Visibility:
    """Make a visibility lump from per-cluster lists of visible clusters.

    Rows are stored uncompressed except for runs of zero bytes, as the map
    compiler writes them. Without ``phs_rows`` the PHS repeats the PVS.
    """
    count = len(rows)
    phs = rows if phs_rows is None else phs_rows
    header_size = 4 + 8 * count
    body = bytearray()
    offsets = np.zeros((count, 2), dtype=np.int32)
    for kind, table in ((VisType.PVS, rows), (VisType.PHS, phs)):
        for cluster, visible in enumerate(table):
            offsets[cluster, kind] = header_size + len(body)
            body += _compress_row(visible, count)
    data = struct.pack("<i", count) + offsets.astype("<i4").tobytes() + bytes(body)
    return Visibility(data, offsets)


def _compress_row(visible: list[int], count: int) -> bytes:
    bits = np.zeros((count + 7) >> 3 << 3, dtype=np.uint8)
    bits[list(visible)] = 1
    row = np.packbits(bits, bitorder="little").tobytes()
    out = bytearray()
    i = 0
    while i < len(row):
        if row[i]:
            out.append(row[i])
            i += 1
            continue
        run = 0
        while i < len(row) and row[i] == 0 and run < 255:
            run += 1
            i += 1
        out += bytes((0, run))
    return bytes(out)
