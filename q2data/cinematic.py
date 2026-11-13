"""Quake II cinematics (``.cin``): Huffman-coded 8-bit frames with sound.

The file is a header (frame size and sound format), 256 rows of 256 byte
counts (one Huffman tree per previous byte), then frames. Each frame is a
command word (0: frame, 1: new palette then frame, 2: end), the compressed
picture, and the sound for that frame (14 frames per second).
"""

from __future__ import annotations

import heapq
import struct
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

from q2data.errors import FormatError

FRAMES_PER_SECOND = 14
HEADER = struct.Struct("<5i")
COUNTS_SIZE = 256 * 256
MAX_COMPRESSED = 0x20000

COMMAND_FRAME = 0
COMMAND_PALETTE = 1
COMMAND_END = 2

LOOKUP_BITS = 12   # bits decoded per table lookup
LONG_CODE = -1     # table entry for a code longer than LOOKUP_BITS


@dataclass(slots=True)
class CinematicHeader:
    width: int
    height: int
    sound_rate: int
    sound_width: int     # bytes per sample
    sound_channels: int


@dataclass(slots=True)
class CinematicFrame:
    number: int
    pixels: np.ndarray            # (height, width) uint8 palette indices
    palette: np.ndarray | None    # (256, 3) uint8 when this frame changes it
    samples: bytes                # little-endian PCM for this frame
    warnings: list[str] = field(default_factory=list)


class HuffmanTables:
    """The 256 Huffman trees, one per previous byte."""

    def __init__(self, counts: np.ndarray, lookup_bits: int = LOOKUP_BITS) -> None:
        counts = np.asarray(counts, dtype=np.int64).reshape(256, 256)
        self.lookup_bits = lookup_bits
        # nodes[prev, n - 256] = (child 0, child 1) for node n >= 256
        self.nodes = np.full((256, 256, 2), -1, dtype=np.int32)
        self.roots = np.zeros(256, dtype=np.int32)
        for prev in range(256):
            self.roots[prev] = self._build(prev, counts[prev])
        self.lookup = self._lookup_table()

    def _build(self, prev: int, row: np.ndarray) -> int:
        # Quake II repeatedly takes the unused node with the smallest non-zero
        # count, the lowest-numbered one on a tie. A heap of (count, node) picks
        # the same nodes.
        heap = [(int(c), i) for i, c in enumerate(row) if c]
        heapq.heapify(heap)
        num_nodes = 256
        while num_nodes != 511:
            v1 = heapq.heappop(heap) if heap else (0, -1)
            self.nodes[prev, num_nodes - 256, 0] = v1[1]
            if v1[1] == -1:
                break
            v2 = heapq.heappop(heap) if heap else (0, -1)
            self.nodes[prev, num_nodes - 256, 1] = v2[1]
            if v2[1] == -1:
                break
            heapq.heappush(heap, (v1[0] + v2[0], num_nodes))
            num_nodes += 1
        return num_nodes - 1

    def _lookup_table(self) -> list[int]:
        """For each tree and each next LOOKUP_BITS bits (lowest bit first),
        the symbol they start with and its code length, as symbol | length << 8."""
        bits_per_lookup = self.lookup_bits
        table = np.zeros((256, 1 << bits_per_lookup), dtype=np.int32)
        for prev in range(256):
            row = table[prev]
            stack = [(int(self.roots[prev]), 0, 0)]
            while stack:
                node, bits, length = stack.pop()
                if node < 256:
                    row[bits::1 << length] = node | (length << 8)
                    continue
                if length == bits_per_lookup:
                    row[bits] = LONG_CODE
                    continue
                children = self.nodes[prev, node - 256]
                stack.append((int(children[0]), bits, length + 1))
                stack.append((int(children[1]), bits | (1 << length), length + 1))
        return table.ravel().tolist()

    def codes(self, prev: int) -> dict[int, tuple[int, int]]:
        """symbol -> (bits, length) for one tree; bits are read lowest first."""
        out: dict[int, tuple[int, int]] = {}
        stack = [(int(self.roots[prev]), 0, 0)]
        while stack:
            node, bits, length = stack.pop()
            if node < 0:
                continue
            if node < 256:
                out[node] = (bits, length)
                continue
            children = self.nodes[prev, node - 256]
            stack.append((int(children[0]), bits, length + 1))
            stack.append((int(children[1]), bits | (1 << length), length + 1))
        return out

    def decompress(self, block: bytes) -> tuple[bytes, list[str]]:
        """Decode one compressed frame (a 4-byte length, then the bits)."""
        if len(block) < 4:
            raise FormatError("compressed frame is too short")
        (count,) = struct.unpack_from("<i", block)
        lookup_bits = self.lookup_bits
        bits = np.unpackbits(np.frombuffer(block, np.uint8, offset=4), bitorder="little")
        bits = np.concatenate((bits.astype(np.int32), np.zeros(lookup_bits, np.int32)))
        windows = np.zeros(len(bits) - lookup_bits, dtype=np.int32)
        for i in range(lookup_bits):
            windows |= bits[i:i + len(windows)] << i
        window = windows.tolist()

        lookup, nodes, roots = self.lookup, self.nodes, self.roots
        out = bytearray(count)
        pos = 0        # bits read
        tree = 0       # the previous symbol's tree, << lookup_bits
        n = 0
        while n < count:
            try:
                while n < count:
                    entry = lookup[tree + window[pos]]
                    if entry == LONG_CODE:
                        prev = tree >> lookup_bits
                        node = int(roots[prev])
                        while node >= 256:
                            index = 4 + (pos >> 3)
                            byte = block[index] if index < len(block) else 0
                            node = int(nodes[prev, node - 256, (byte >> (pos & 7)) & 1])
                            pos += 1
                    else:
                        node = entry & 255
                        pos += entry >> 8
                    out[n] = node
                    n += 1
                    tree = node << lookup_bits
            except IndexError:  # reading past the end gives zero bits
                window.extend([0] * max(len(window), 64))

        warnings = []
        used = 4 + (pos >> 3) + 1 if count else 4
        if used not in (len(block), len(block) + 1):
            warnings.append(f"Decompression overread by {used - len(block)}")
        return bytes(out), warnings

    def compress(self, pixels: bytes) -> bytes:
        """Encode bytes with these trees (every symbol used must have a code)."""
        codes = [self.codes(prev) for prev in range(256)]
        bit_buffer = 0
        bit_count = 0
        out = bytearray(struct.pack("<i", len(pixels)))
        prev = 0
        for value in pixels:
            try:
                bits, length = codes[prev][value]
            except KeyError:
                raise ValueError(f"byte {value} after {prev} has no code") from None
            bit_buffer |= bits << bit_count
            bit_count += length
            while bit_count >= 8:
                out.append(bit_buffer & 0xFF)
                bit_buffer >>= 8
                bit_count -= 8
            prev = value
        if bit_count:
            out.append(bit_buffer & 0xFF)
        return bytes(out)


def frame_sample_count(frame: int, rate: int) -> int:
    """How many sound samples go with a frame."""
    return int((frame + 1) * rate / FRAMES_PER_SECOND) - int(frame * rate / FRAMES_PER_SECOND)


class CinematicReader:
    """Reads a cinematic frame by frame from bytes."""

    def __init__(self, data: bytes) -> None:
        if len(data) < HEADER.size + COUNTS_SIZE:
            raise FormatError("too short to be a cinematic")
        self.data = data
        self.header = CinematicHeader(*HEADER.unpack_from(data))
        counts = np.frombuffer(data, np.uint8, COUNTS_SIZE, HEADER.size)
        self.tables = HuffmanTables(counts)
        self.pos = HEADER.size + COUNTS_SIZE
        self.frame = 0

    def _read(self, size: int) -> bytes:
        chunk = self.data[self.pos:self.pos + size]
        self.pos += len(chunk)
        return chunk

    def next_frame(self) -> CinematicFrame | None:
        """The next frame, or None at the end."""
        command = self._read(4)
        if len(command) != 4:
            return None
        (command_value,) = struct.unpack("<i", command)
        if command_value == COMMAND_END:
            return None
        palette = None
        if command_value == COMMAND_PALETTE:
            raw = self._read(768)
            palette = np.frombuffer(raw.ljust(768, b"\0"), np.uint8).reshape(256, 3).copy()
        size_raw = self._read(4)
        if len(size_raw) != 4:
            return None
        (size,) = struct.unpack("<i", size_raw)
        if size > MAX_COMPRESSED or size < 1:
            raise FormatError("Bad compressed frame size")
        compressed = self._read(size)
        header = self.header
        count = frame_sample_count(self.frame, header.sound_rate)
        samples = self._read(count * header.sound_width * header.sound_channels)
        pixels, warnings = self.tables.decompress(compressed)
        needed = header.width * header.height
        picture = np.frombuffer(pixels[:needed].ljust(needed, b"\0"), np.uint8)
        frame = CinematicFrame(self.frame, picture.reshape(header.height, header.width).copy(),
                               palette, samples, warnings)
        self.frame += 1
        return frame

    def __iter__(self) -> Iterator[CinematicFrame]:
        while (frame := self.next_frame()) is not None:
            yield frame


def write_cinematic(header: CinematicHeader, frames: list[tuple[np.ndarray, np.ndarray | None,
                                                                 bytes]],
                    counts: np.ndarray | None = None) -> bytes:
    """Build a cinematic from (pixels, palette or None, samples) per frame.

    Without ``counts`` every byte pair counts once, which gives every symbol an
    8-bit code.
    """
    if counts is None:
        counts = np.ones((256, 256), dtype=np.uint8)
    tables = HuffmanTables(counts)
    out = bytearray(HEADER.pack(header.width, header.height, header.sound_rate,
                                header.sound_width, header.sound_channels))
    out += np.asarray(counts, np.uint8).tobytes()
    for pixels, palette, samples in frames:
        if palette is None:
            out += struct.pack("<i", COMMAND_FRAME)
        else:
            out += struct.pack("<i", COMMAND_PALETTE) + np.asarray(palette, np.uint8).tobytes()
        block = tables.compress(np.asarray(pixels, np.uint8).tobytes())
        out += struct.pack("<i", len(block)) + block + samples
    out += struct.pack("<i", COMMAND_END)
    return bytes(out)
