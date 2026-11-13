"""Small helpers for fixed-size binary records."""

from __future__ import annotations

import numpy as np

from q2data.errors import FormatError

# Quake II stores names as NUL-padded bytes; latin-1 maps every byte to one
# character, so names round-trip unchanged.
ENCODING = "latin-1"


def decode_name(raw: bytes) -> str:
    """Decode a NUL-terminated, NUL-padded name."""
    return raw.split(b"\0", 1)[0].decode(ENCODING)


def encode_name(name: str, size: int) -> bytes:
    """Encode a name into a NUL-padded field of ``size`` bytes."""
    raw = name.encode(ENCODING)
    if len(raw) >= size:
        raise FormatError(f"name {name!r} is longer than {size - 1} bytes")
    return raw.ljust(size, b"\0")


def read_records(data: bytes | memoryview, offset: int, count: int, dtype: np.dtype,
                 what: str) -> np.ndarray:
    """Copy ``count`` records of ``dtype`` starting at ``offset``."""
    end = offset + count * dtype.itemsize
    if offset < 0 or count < 0 or end > len(data):
        raise FormatError(f"{what} lies outside the file")
    return np.frombuffer(data, dtype=dtype, count=count, offset=offset).copy()


def strings_field(array: np.ndarray, field: str) -> list[str]:
    """Decode a fixed-size bytes field of a record array into strings."""
    return [decode_name(bytes(value)) for value in array[field]]
