import struct

import numpy as np
import pytest

from q2data import FormatError, md2, sp2
from tests.unit.builders import cube_model


def test_md2_round_trip():
    model = cube_model(frames=3)
    data = md2.write_md2(model)
    loaded = md2.load_md2(data)
    assert loaded.skins == model.skins
    assert (loaded.skin_width, loaded.skin_height) == (64, 64)
    assert np.array_equal(loaded.st, model.st)
    assert np.array_equal(loaded.triangles, model.triangles)
    assert np.array_equal(loaded.glcmds, model.glcmds)
    assert [f.name for f in loaded.frames] == ["frame0", "frame1", "frame2"]
    for a, b in zip(loaded.frames, model.frames, strict=True):
        assert np.array_equal(a.verts, b.verts)
        assert np.allclose(a.scale, b.scale) and np.allclose(a.translate, b.translate)
    assert md2.write_md2(loaded) == data


def test_md2_positions():
    frame = cube_model().frames[0]
    positions = frame.positions()
    assert positions.shape == (8, 3)
    assert np.allclose(positions.min(axis=0), -8.0)
    assert np.allclose(positions.max(axis=0), -8.0 + 16.0)


def test_md2_header_checks():
    data = md2.write_md2(cube_model())
    with pytest.raises(FormatError, match="not an MD2"):
        md2.load_md2(b"XXXX" + data[4:])
    with pytest.raises(FormatError, match="wrong version"):
        md2.load_md2(data[:4] + struct.pack("<i", 7) + data[8:])
    with pytest.raises(FormatError, match="too small"):
        md2.load_md2(data[:-4])


def test_md2_header_fields():
    header = md2.read_header(md2.write_md2(cube_model(frames=2)))
    assert (header.num_xyz, header.num_st, header.num_tris, header.num_frames) == (8, 8, 12, 2)
    assert header.frame_size == 40 + 8 * 4


def test_sp2_round_trip():
    sprite = sp2.Sprite([sp2.SpriteFrame(32, 32, 16, 16, "sprites/s_bubble.pcx"),
                         sp2.SpriteFrame(64, 48, 0, 0, "sprites/s_bubble2.pcx")])
    loaded = sp2.load_sp2(sp2.write_sp2(sprite))
    assert loaded == sprite


def test_sp2_errors():
    data = sp2.write_sp2(sp2.Sprite([sp2.SpriteFrame(1, 1, 0, 0, "a.pcx")]))
    with pytest.raises(FormatError, match="wrong version"):
        sp2.load_sp2(data[:4] + struct.pack("<i", 1) + data[8:])
    with pytest.raises(FormatError, match="outside"):
        sp2.load_sp2(data[:-1])
