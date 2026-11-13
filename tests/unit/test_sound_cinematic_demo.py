import struct

import numpy as np
import pytest

from q2data import FormatError, cinematic, demo, wav
from tests.unit.builders import gradient_palette, pattern


def test_wav_round_trip():
    samples = bytes(range(200))
    data = wav.write_wav(samples, 11025, 1, 1)
    info = wav.read_wav_info(data)
    assert (info.rate, info.width, info.channels, info.loop_start) == (11025, 1, 1, -1)
    assert info.samples == 200
    assert info.sample_bytes(data) == samples


def test_wav_16_bit_counts_samples_by_width():
    data = wav.write_wav(b"\0\1" * 50, 22050, 2, 1)
    assert wav.read_wav_info(data).samples == 50


def _with_loop(loop_start: int, loop_length: int) -> bytes:
    """A WAV with a cue chunk and a LIST/mark chunk, as Quake II's sounds have."""
    data = wav.write_wav(bytes(400), 11025, 1, 1)
    cue = b"cue " + struct.pack("<i", 28) + bytes(24) + struct.pack("<i", loop_start)
    mark = b"LIST" + struct.pack("<i", 24) + bytes(16) + struct.pack("<i", loop_length) + \
        b"mark"
    body = data[12:] + cue + mark
    return b"RIFF" + struct.pack("<i", len(body) + 4) + b"WAVE" + body


def test_wav_loop_points():
    info = wav.read_wav_info(_with_loop(100, 250))
    assert info.loop_start == 100
    assert info.samples == 350


def test_wav_bad_loop_length():
    with pytest.raises(FormatError, match="bad loop length"):
        wav.read_wav_info(_with_loop(300, 250))


@pytest.mark.parametrize("data, message", [
    (b"RIFF\0\0\0\0WAVX", "RIFF/WAVE"),
    (b"RIFF\4\0\0\0WAVE", "fmt"),
])
def test_wav_errors(data, message):
    with pytest.raises(FormatError, match=message):
        wav.read_wav_info(data)


def test_wav_pcm_only():
    data = bytearray(wav.write_wav(bytes(10), 11025, 1, 1))
    data[20] = 3  # format 3, float
    with pytest.raises(FormatError, match="PCM"):
        wav.read_wav_info(bytes(data))


def _frames(count=3, width=8, height=4, rate=11025):
    header = cinematic.CinematicHeader(width, height, rate, 1, 1)
    frames = []
    for i in range(count):
        palette = gradient_palette() if i == 0 else None
        samples = bytes([i]) * cinematic.frame_sample_count(i, rate)
        frames.append((pattern(width, height, seed=i), palette, samples))
    return header, frames


def test_cinematic_round_trip():
    header, frames = _frames()
    reader = cinematic.CinematicReader(cinematic.write_cinematic(header, frames))
    assert reader.header == header
    decoded = list(reader)
    assert len(decoded) == 3
    for frame, (pixels, palette, samples) in zip(decoded, frames, strict=True):
        assert np.array_equal(frame.pixels, pixels)
        assert frame.samples == samples
        assert frame.warnings == []
        if palette is None:
            assert frame.palette is None
        else:
            assert np.array_equal(frame.palette, palette)


def test_cinematic_skewed_counts_and_long_codes():
    # Uneven counts give codes of many lengths; a 2-bit lookup forces the
    # slow tree walk for most of them.
    counts = np.ones((256, 256), np.uint8)
    counts[:, :16] = np.arange(1, 17, dtype=np.uint8) * 15
    pixels = pattern(16, 8, seed=7)
    tables = cinematic.HuffmanTables(counts)
    block = tables.compress(pixels.tobytes())
    for lookup_bits in (2, cinematic.LOOKUP_BITS):
        decoded, warnings = cinematic.HuffmanTables(counts, lookup_bits).decompress(block)
        assert decoded == pixels.tobytes()
        assert warnings == []


def test_cinematic_sound_per_frame():
    rate = 22050
    total = sum(cinematic.frame_sample_count(i, rate) for i in range(14))
    assert total == rate  # 14 frames make one second


def test_cinematic_bad_frame_size():
    header, frames = _frames(count=1)
    data = bytearray(cinematic.write_cinematic(header, frames))
    size_pos = cinematic.HEADER.size + cinematic.COUNTS_SIZE + 4 + 768
    struct.pack_into("<i", data, size_pos, 0)
    with pytest.raises(FormatError, match="Bad compressed frame size"):
        list(cinematic.CinematicReader(bytes(data)))


def test_demo_round_trip():
    blocks = [b"\x01\x02", b"", bytes(1400)]
    assert list(demo.iter_demo_blocks(demo.write_demo(blocks))) == blocks


def test_demo_errors():
    with pytest.raises(FormatError, match="truncated"):
        list(demo.iter_demo_blocks(struct.pack("<i", 10) + b"abc"))
    with pytest.raises(FormatError, match="length"):
        list(demo.iter_demo_blocks(struct.pack("<i", 1401) + bytes(1401)))
