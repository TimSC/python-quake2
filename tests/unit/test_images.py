import io
import struct

import numpy as np
import pytest
from PIL import Image as PILImage

from q2data import FormatError, images
from tests.unit.builders import gradient_palette, pattern


@pytest.mark.parametrize("width, height", [(16, 8), (15, 9), (1 + 1, 3), (320, 240)])
def test_pcx_round_trip(width, height):
    pixels = pattern(width, height)
    palette = gradient_palette()
    image = images.load_pcx(images.write_pcx(pixels, palette))
    assert (image.width, image.height) == (width, height)
    assert np.array_equal(image.pixels, pixels)
    assert np.array_equal(image.palette, palette)
    assert image.warnings == []


def test_pcx_pillow_and_manual_decoders_agree():
    pixels = pattern(32, 16, seed=3)
    data = images.write_pcx(pixels, gradient_palette())
    header = images.read_pcx_header(data)
    assert header.bytes_per_line == 32  # Pillow takes this one
    fast = images.load_pcx(data).pixels
    manual, _ = images._rle_lines(data, images.PCX_HEADER.size, 16, 32, 32)
    assert np.array_equal(fast, manual)


def test_pcx_truncated_data_is_an_issue_not_an_error():
    data = images.write_pcx(pattern(15, 9), gradient_palette())
    # drop the palette and some of the picture
    image = images.load_pcx(data[:200])
    assert image.width == 15
    assert "possible size issues" in image.warnings


def test_pcx_missing_palette_marker():
    data = bytearray(images.write_pcx(pattern(15, 9), gradient_palette()))
    data[-769] = 0
    assert "has no palette marker" in images.load_pcx(bytes(data)).warnings


def test_pcx_bad_header():
    data = images.write_pcx(pattern(4, 4), gradient_palette())
    with pytest.raises(FormatError, match="bad PCX"):
        images.load_pcx(b"\x0b" + data[1:])
    with pytest.raises(FormatError):
        images.load_pcx(data[:50])


def _rle(raw: bytes) -> bytes:
    """Encode bytes as PCX runs (no run crosses the end of the input)."""
    out = bytearray()
    for value in raw:
        out += bytes((0xC1, value))
    return bytes(out)


def test_pcx_24_bit():
    width, height = 3, 2
    rgb = np.arange(width * height * 3, dtype=np.uint8).reshape(height, width, 3)
    body = b"".join(_rle(bytes(rgb[y, :, plane])) for y in range(height) for plane in range(3))
    header = images.PCX_HEADER.pack(0x0A, 5, 1, 8, 0, 0, width - 1, height - 1, 72, 72,
                                    b"\0" * 48, 0, 3, width, 1, b"\0" * 58)
    image = images.load_pcx(header + body)
    assert image.pixels.shape == (height, width, 4)
    assert np.array_equal(image.pixels[..., :3], rgb)
    assert (image.pixels[..., 3] == 255).all()


def test_pcx_1_bit():
    width, height = 10, 2
    header_palette = bytes([0, 0, 0, 255, 255, 255]) + b"\0" * 42
    header = images.PCX_HEADER.pack(0x0A, 5, 1, 1, 0, 0, width - 1, height - 1, 72, 72,
                                    header_palette, 0, 1, 2, 1, b"\0" * 58)
    rows = bytes([0b10100000, 0b01000000, 0b11111111, 0b11000000])
    image = images.load_pcx(header + _rle(rows))
    assert image.pixels.tolist() == [[1, 0, 1, 0, 0, 0, 0, 0, 0, 1], [1] * 10]
    assert image.palette[1].tolist() == [255, 255, 255]


def test_pcx_one_pixel_high_is_rejected():
    # Quake II refuses PCX files whose ymax - ymin is 0
    with pytest.raises(FormatError, match="bad PCX"):
        images.load_pcx(images.write_pcx(pattern(4, 1), gradient_palette()))


def test_to_rgba_with_transparency():
    image = images.Image(2, 1, np.array([[0, 255]], np.uint8), gradient_palette())
    rgba = image.to_rgba(transparent_index=255)
    assert rgba[0, 0].tolist() == [0, 255, 0, 255]
    assert rgba[0, 1].tolist() == [255, 0, 127, 0]


def test_load_palette():
    data = images.write_pcx(pattern(4, 4), gradient_palette())
    assert np.array_equal(images.load_palette(data), gradient_palette())


def _wal(width=16, height=8):
    mips = [pattern(max(width >> i, 1), max(height >> i, 1), seed=i) for i in range(4)]
    return images.Wal("e1u1/test", width, height, "e1u1/test2", 1, 2, 3, mips)


def test_wal_round_trip():
    wal = _wal()
    loaded = images.load_wal(images.write_wal(wal))
    assert (loaded.name, loaded.anim_name, loaded.flags, loaded.contents, loaded.value) == \
        ("e1u1/test", "e1u1/test2", 1, 2, 3)
    assert len(loaded.mips) == 4
    for a, b in zip(loaded.mips, wal.mips, strict=True):
        assert np.array_equal(a, b)
    assert images.wal_size(images.write_wal(wal)) == (16, 8)


def test_wal_errors():
    data = images.write_wal(_wal())
    with pytest.raises(FormatError, match="small header"):
        images.load_wal(data[:50])
    with pytest.raises(FormatError, match="small body"):
        images.load_wal(data[:images.WAL_HEADER.size + 100])


def test_m8():
    palette = gradient_palette()
    width, height = 4, 2
    indices = np.array([[0, 1, 2, 255], [3, 4, 5, 6]], np.uint8)
    offset = images.M8_HEADER.size
    header = images.M8_HEADER.pack(images.M8_VERSION, b"name", width, *[0] * 15, height,
                                   *[0] * 15, offset, *[0] * 15, b"anim", palette.tobytes(),
                                   7, 8, 9)
    texture = images.load_m8(header + indices.tobytes())
    assert (texture.width, texture.height, texture.flags) == (4, 2, 7)
    assert texture.rgba[0, 1].tolist() == [1, 254, 0, 255]
    assert texture.rgba[0, 3, 3] == 0  # index 255 is transparent
    assert images.mip_texture_size(header + indices.tobytes(), "m8") == (4, 2)
    with pytest.raises(FormatError, match="magic"):
        images.load_m8(struct.pack("<I", 1) + header[4:] + indices.tobytes())


def test_m32():
    width, height = 2, 2
    rgba = np.arange(16, dtype=np.uint8).reshape(2, 2, 4)
    offset = images.M32_HEADER.size
    header = images.M32_HEADER.pack(images.M32_VERSION, b"n", b"", b"a", b"",
                                    width, *[0] * 15, height, *[0] * 15, offset, *[0] * 15,
                                    1, 2, 3, 1.0, 1.0, 0, b"", 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0,
                                    b"")
    texture = images.load_m32(header + rgba.tobytes())
    assert np.array_equal(texture.rgba, rgba)
    with pytest.raises(FormatError, match="small body"):
        images.load_m32(header + rgba.tobytes()[:8])


@pytest.mark.parametrize("fmt", ["PNG", "TGA", "BMP"])
def test_load_rgba(fmt):
    rgba = np.zeros((3, 5, 4), np.uint8)
    rgba[..., 0] = 200
    rgba[..., 3] = 255
    rgba[1, 2] = (1, 2, 3, 255)
    buffer = io.BytesIO()
    PILImage.fromarray(rgba).save(buffer, fmt)
    image = images.load_rgba(buffer.getvalue())
    assert (image.width, image.height) == (5, 3)
    assert image.pixels[1, 2].tolist() == [1, 2, 3, 255]
    assert images.image_size(buffer.getvalue()) == (5, 3)


def test_load_rgba_rejects_garbage():
    with pytest.raises(FormatError):
        images.load_rgba(b"not an image")
