"""Quake II archives: ``.pak`` files, and zip-based ``.pk3`` (``.pk2``, ``.pkz``, ``.zip``)."""

from __future__ import annotations

import io
import os
import struct
import zipfile
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from q2data.binary import decode_name, encode_name, read_records
from q2data.errors import FormatError

PAK_IDENT = b"PACK"
PAK_NAME_SIZE = 56
MAX_FILES_IN_PACK = 4096

PAK_HEADER = struct.Struct("<4sii")
PAK_ENTRY = np.dtype([("name", "S56"), ("offset", "<i4"), ("length", "<i4")])


class Archive(Protocol):
    """A collection of named files, looked up without regard to case."""

    path: str

    def names(self) -> list[str]: ...

    def __contains__(self, name: str) -> bool: ...

    def size(self, name: str) -> int: ...

    def read(self, name: str) -> bytes: ...


@dataclass(slots=True, frozen=True)
class PakEntry:
    name: str
    offset: int
    length: int


class PakArchive:
    """A ``.pak`` file: a header, the file contents, and a directory."""

    def __init__(self, source: str | os.PathLike[str] | bytes) -> None:
        if isinstance(source, bytes):
            self.path = "<memory>"
            self._data: bytes | None = source
            directory = _read_pak_directory(source, len(source))
        else:
            self.path = os.fspath(source)
            self._data = None
            with open(self.path, "rb") as f:
                size = os.fstat(f.fileno()).st_size
                header = f.read(PAK_HEADER.size)
                ident, dir_offset, dir_length = _check_pak_header(header, size)
                f.seek(dir_offset)
                raw = f.read(dir_length)
            directory = _parse_directory(raw, dir_length)

        self.entries = [PakEntry(decode_name(bytes(e["name"])), int(e["offset"]),
                                 int(e["length"])) for e in directory]
        # Quake II sorts a pack's names case-insensitively and binary-searches
        # them; with duplicate names it finds one of them. Keep the first.
        self._index: dict[str, PakEntry] = {}
        for entry in self.entries:
            self._index.setdefault(entry.name.lower(), entry)

    def __len__(self) -> int:
        return len(self.entries)

    def names(self) -> list[str]:
        return [entry.name for entry in self.entries]

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._index

    def entry(self, name: str) -> PakEntry:
        try:
            return self._index[name.lower()]
        except KeyError:
            raise FileNotFoundError(f"{name} is not in {self.path}") from None

    def size(self, name: str) -> int:
        return self.entry(name).length

    def read(self, name: str) -> bytes:
        entry = self.entry(name)
        if self._data is not None:
            data = self._data[entry.offset:entry.offset + entry.length]
        else:
            with open(self.path, "rb") as f:
                f.seek(entry.offset)
                data = f.read(entry.length)
        if len(data) != entry.length:
            raise FormatError(f"{name} in {self.path} is truncated")
        return data


def _check_pak_header(header: bytes, size: int) -> tuple[bytes, int, int]:
    if len(header) < PAK_HEADER.size:
        raise FormatError("too short to be a pack file")
    ident, dir_offset, dir_length = PAK_HEADER.unpack(header)
    if ident != PAK_IDENT:
        raise FormatError("not a pack file")
    if dir_length // PAK_ENTRY.itemsize == 0 or dir_length < 0 or dir_offset < 0:
        raise FormatError("pack file is too short")
    if dir_offset + dir_length > size:
        raise FormatError("pack directory lies outside the file")
    return ident, dir_offset, dir_length


def _read_pak_directory(data: bytes, size: int) -> np.ndarray:
    _, dir_offset, dir_length = _check_pak_header(data[:PAK_HEADER.size], size)
    return _parse_directory(data[dir_offset:dir_offset + dir_length], dir_length)


def _parse_directory(raw: bytes, dir_length: int) -> np.ndarray:
    count = dir_length // PAK_ENTRY.itemsize
    return read_records(raw, 0, count, PAK_ENTRY, "pack directory")


def write_pak(files: dict[str, bytes]) -> bytes:
    """Build a ``.pak`` file holding ``files`` (name -> contents), in order."""
    body = io.BytesIO()
    body.write(b"\0" * PAK_HEADER.size)
    directory = np.zeros(len(files), dtype=PAK_ENTRY)
    for i, (name, contents) in enumerate(files.items()):
        directory[i] = (encode_name(name, PAK_NAME_SIZE), body.tell(), len(contents))
        body.write(contents)
    dir_offset = body.tell()
    body.write(directory.tobytes())
    out = body.getbuffer()
    out[:PAK_HEADER.size] = PAK_HEADER.pack(PAK_IDENT, dir_offset, directory.nbytes)
    return bytes(out)


class ZipArchive:
    """A zip-based pack (``.pk3`` and friends)."""

    def __init__(self, source: str | os.PathLike[str] | bytes) -> None:
        if isinstance(source, bytes):
            self.path = "<memory>"
            fileobj: io.BytesIO | str = io.BytesIO(source)
        else:
            self.path = os.fspath(source)
            fileobj = self.path
        try:
            self._zip = zipfile.ZipFile(fileobj)
        except zipfile.BadZipFile as err:
            raise FormatError(f"not a zip file: {err}") from None
        self._index: dict[str, zipfile.ZipInfo] = {}
        for info in self._zip.infolist():
            if not info.is_dir():
                self._index.setdefault(info.filename.lower(), info)

    def __len__(self) -> int:
        return len(self._index)

    def names(self) -> list[str]:
        return [info.filename for info in self._index.values()]

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._index

    def size(self, name: str) -> int:
        try:
            return self._index[name.lower()].file_size
        except KeyError:
            raise FileNotFoundError(f"{name} is not in {self.path}") from None

    def read(self, name: str) -> bytes:
        try:
            info = self._index[name.lower()]
        except KeyError:
            raise FileNotFoundError(f"{name} is not in {self.path}") from None
        try:
            return self._zip.read(info)
        except (zipfile.BadZipFile, OSError) as err:
            raise FormatError(f"{name} in {self.path}: {err}") from None

    def close(self) -> None:
        self._zip.close()


def write_zip(files: dict[str, bytes]) -> bytes:
    """Build a zip-based pack holding ``files``."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, contents in files.items():
            z.writestr(name, contents)
    return out.getvalue()
