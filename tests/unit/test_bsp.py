import struct

import numpy as np
import pytest

from q2data import FormatError, bsp
from q2data.entities import parse_entities
from tests.unit.builders import ROOM_HALF, TEXTURE, box_room


@pytest.fixture
def room_bytes():
    return bsp.write_bsp(box_room())


def test_round_trip(room_bytes):
    original = box_room()
    loaded = bsp.load_bsp(room_bytes)
    for name in bsp.LUMP_FIELDS:
        a, b = getattr(original, name), getattr(loaded, name)
        if isinstance(a, np.ndarray):
            assert a.dtype == b.dtype and np.array_equal(a, b), name
        elif isinstance(a, bsp.Visibility):
            assert a.data == b.data and np.array_equal(a.offsets, b.offsets)
        else:
            assert a == b, name
    assert bsp.write_bsp(loaded) == room_bytes


def test_record_sizes_match_the_file_format():
    sizes = {bsp.PLANE: 20, bsp.VERTEX: 12, bsp.NODE: 28, bsp.TEXINFO: 76, bsp.FACE: 20,
             bsp.LEAF: 28, bsp.EDGE: 4, bsp.MODEL: 48, bsp.BRUSH: 12, bsp.BRUSH_SIDE: 4,
             bsp.AREA: 8, bsp.AREA_PORTAL: 8}
    for dtype, size in sizes.items():
        assert dtype.itemsize == size


def test_lumps_are_aligned(room_bytes):
    for info in bsp.read_header(room_bytes):
        assert info.offset % 4 == 0


def test_room_contents(room_bytes):
    room = bsp.load_bsp(room_bytes)
    assert room.texture_names() == [TEXTURE] * 6
    assert room.leafs["contents"][0] == bsp.Contents.SOLID  # leaf 0 must be solid
    assert len(room.models) == 1 and room.models[0]["head_node"] == 0
    assert room.vertices["point"].max() == ROOM_HALF
    entities = parse_entities(room.entities)
    assert [e.classname for e in entities] == ["worldspawn", "info_player_start"]


def test_bad_ident_and_version(room_bytes):
    with pytest.raises(FormatError, match="ident"):
        bsp.load_bsp(b"XBSP" + room_bytes[4:])
    wrong_version = room_bytes[:4] + struct.pack("<i", 37) + room_bytes[8:]
    with pytest.raises(FormatError, match="version"):
        bsp.load_bsp(wrong_version)
    with pytest.raises(FormatError):
        bsp.load_bsp(room_bytes[:10])


def test_funny_lump_size(room_bytes):
    data = bytearray(room_bytes)
    # shorten the planes lump by one byte
    offset_pos = 8 + 8 * bsp.Lump.PLANES
    length = struct.unpack_from("<i", data, offset_pos + 4)[0]
    struct.pack_into("<i", data, offset_pos + 4, length - 1)
    with pytest.raises(FormatError, match="funny lump size in planes"):
        bsp.load_bsp(bytes(data))


def test_lump_outside_file(room_bytes):
    with pytest.raises(FormatError, match="outside"):
        bsp.load_bsp(room_bytes[:-8])


def test_visibility_round_trip():
    rows = [[0, 1], [1, 2, 9], [], list(range(10))]
    vis = bsp.build_visibility(rows + [[]] * 6)
    loaded = bsp.Visibility.from_bytes(vis.data)
    assert loaded.num_clusters == 10
    for cluster, row in enumerate(rows):
        expected = np.zeros(10, bool)
        expected[row] = True
        assert np.array_equal(loaded.cluster_vis(cluster), expected)
        assert np.array_equal(loaded.cluster_vis(cluster, bsp.VisType.PHS), expected)


def test_visibility_zero_runs_are_compressed():
    vis = bsp.build_visibility([[0]] + [[]] * 99)
    # 100 clusters is 13 bytes a row: one data byte, then a run of 12 zeros.
    row = vis.data[vis.offsets[0, 0]:vis.offsets[1, 0]]
    assert row == bytes((1, 0, 12))


def test_empty_visibility():
    vis = bsp.Visibility.from_bytes(b"")
    assert vis.num_clusters == 0
