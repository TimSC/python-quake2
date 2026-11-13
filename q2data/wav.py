"""WAV sound files, read the way Quake II reads them (PCM only, with loop points)."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from q2data.errors import FormatError


@dataclass(slots=True)
class WavInfo:
    rate: int
    width: int        # bytes per sample
    channels: int
    loop_start: int   # -1 when the sound doesn't loop
    samples: int      # data bytes / width, as Quake II counts them (not per channel)
    data_offset: int  # where the samples start in the file

    def sample_bytes(self, data: bytes) -> bytes:
        """The raw sample data."""
        size = self.samples * self.width
        return data[self.data_offset:self.data_offset + size]


class _Chunks:
    """Quake II's RIFF chunk search, including its quirks (a chunk's length
    word may be read just past the end, and odd lengths are padded)."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.start = 0
        self.last = 0

    def find(self, name: bytes) -> int | None:
        self.last = self.start
        return self.find_next(name)

    def find_next(self, name: bytes) -> int | None:
        data = self.data
        while True:
            pos = self.last + 4
            if pos >= len(data) or pos + 4 > len(data):
                return None
            (length,) = struct.unpack_from("<i", data, pos)
            if length < 0:
                return None
            chunk = self.last
            self.last = chunk + 8 + ((length + 1) & ~1)
            if data[chunk:chunk + 4] == name:
                return chunk


def _short(data: bytes, pos: int) -> int:
    if pos + 2 > len(data):
        raise FormatError("truncated header")
    return struct.unpack_from("<h", data, pos)[0]


def _long(data: bytes, pos: int) -> int:
    if pos + 4 > len(data):
        raise FormatError("truncated header")
    return struct.unpack_from("<i", data, pos)[0]


def read_wav_info(data: bytes) -> WavInfo:
    """Parse the header chunks of a WAV file."""
    chunks = _Chunks(data)
    riff = chunks.find(b"RIFF")
    if riff is None or data[riff + 8:riff + 12] != b"WAVE":
        raise FormatError("Missing RIFF/WAVE chunks")
    chunks.start = riff + 12

    fmt = chunks.find(b"fmt ")
    if fmt is None:
        raise FormatError("Missing fmt chunk")
    pos = fmt + 8
    if _short(data, pos) != 1:
        raise FormatError("Microsoft PCM format only")
    channels = _short(data, pos + 2)
    rate = _long(data, pos + 4)
    width = _short(data, pos + 14) // 8
    if width <= 0:
        raise FormatError("Invalid bits per sample")

    loop_start = -1
    loop_samples = 0
    cue = chunks.find(b"cue ")
    if cue is not None:
        loop_start = _long(data, cue + 32)
        listing = chunks.find_next(b"LIST")
        if listing is not None and listing + 32 <= len(data) and \
                data[listing + 28:listing + 32] == b"mark":
            loop_samples = loop_start + _long(data, listing + 24)

    data_chunk = chunks.find(b"data")
    if data_chunk is None:
        raise FormatError("Missing data chunk")
    samples = _long(data, data_chunk + 4) // width
    if loop_samples:
        if samples < loop_samples:
            raise FormatError("has a bad loop length")
        samples = loop_samples
    return WavInfo(rate, width, channels, loop_start, samples, data_chunk + 8)


def write_wav(samples: bytes, rate: int, width: int, channels: int) -> bytes:
    """A plain PCM WAV file."""
    fmt = struct.pack("<hhiihh", 1, channels, rate, rate * width * channels,
                      width * channels, width * 8)
    body = b"WAVE" + b"fmt " + struct.pack("<i", len(fmt)) + fmt
    body += b"data" + struct.pack("<i", len(samples)) + samples
    if len(samples) & 1:
        body += b"\0"
    return b"RIFF" + struct.pack("<i", len(body)) + body
