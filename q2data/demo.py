"""Quake II demos (``.dm2``): the server messages a client received, in order.

Each block is a little-endian int32 length followed by that many bytes of
server message; a length of -1 ends the demo.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator

from q2data.errors import FormatError

END_OF_DEMO = -1
MAX_MESSAGE = 1400  # MAX_MSGLEN: the server refuses longer demo blocks


def iter_demo_blocks(data: bytes) -> Iterator[bytes]:
    """The message blocks of a demo, up to the end marker."""
    pos = 0
    while pos + 4 <= len(data):
        (length,) = struct.unpack_from("<i", data, pos)
        pos += 4
        if length == END_OF_DEMO:
            return
        if length < 0 or length > MAX_MESSAGE:
            raise FormatError(f"bad demo message length {length}")
        if pos + length > len(data):
            raise FormatError("demo is truncated")
        yield data[pos:pos + length]
        pos += length


def write_demo(blocks: list[bytes]) -> bytes:
    out = bytearray()
    for block in blocks:
        out += struct.pack("<i", len(block)) + block
    out += struct.pack("<i", END_OF_DEMO)
    return bytes(out)
