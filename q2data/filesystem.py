"""A Quake II search path: loose directories and archives, searched in order."""

from __future__ import annotations

import os
from dataclasses import dataclass

from q2data.pak import Archive, PakArchive, ZipArchive

MAX_PAKS = 100

# Archive suffixes in the order Quake II (Yamagi) adds them, with the class
# that reads each one.
PACK_TYPES: tuple[tuple[str, type[PakArchive] | type[ZipArchive]], ...] = (
    ("pak", PakArchive),
    ("pk2", ZipArchive),
    ("pk3", ZipArchive),
    ("pkz", ZipArchive),
    ("zip", ZipArchive),
)


@dataclass(slots=True)
class SearchPath:
    """One entry of the search path: a directory or an archive."""

    directory: str | None = None
    archive: Archive | None = None
    # Files in protected (numbered, official) paks are never offered for download.
    protected: bool = False

    @property
    def name(self) -> str:
        return self.directory if self.directory is not None else self.archive.path


@dataclass(slots=True, frozen=True)
class FoundFile:
    """Where a name was found."""

    name: str
    search_path: SearchPath

    @property
    def in_archive(self) -> bool:
        return self.search_path.archive is not None


class FileSystem:
    """Files looked up through a search path; earlier entries win."""

    def __init__(self) -> None:
        self.search_paths: list[SearchPath] = []

    def add_directory(self, path: str | os.PathLike[str]) -> None:
        """Put a loose directory in front of the search path."""
        self.search_paths.insert(0, SearchPath(directory=os.fspath(path).rstrip("/\\")))

    def add_archive(self, archive: Archive, protected: bool = False) -> None:
        """Put an archive in front of the search path."""
        self.search_paths.insert(0, SearchPath(archive=archive, protected=protected))

    def add_game_directory(self, path: str | os.PathLike[str]) -> list[tuple[str, Exception]]:
        """Add a game directory and its archives, as Quake II does (see
        ``game_directory_archives``). Each one goes in front, so the last
        added is searched first. Returns the archives that could not be read,
        with the error, so the caller can report them.
        """
        directory = os.fspath(path).rstrip("/\\")
        self.add_directory(directory)
        failures: list[tuple[str, Exception]] = []
        for spec in game_directory_archives(directory):
            try:
                archive = spec.reader(spec.path)
            except (OSError, ValueError) as err:
                failures.append((spec.path, err))
                continue
            self.add_archive(archive, protected=spec.protected)
        return failures

    def find(self, name: str) -> FoundFile | None:
        """Find which search path entry holds ``name``."""
        for search_path in self.search_paths:
            if search_path.archive is not None:
                if name in search_path.archive:
                    return FoundFile(name, search_path)
            elif os.path.isfile(os.path.join(search_path.directory, name)):
                return FoundFile(name, search_path)
        return None

    def exists(self, name: str) -> bool:
        return self.find(name) is not None

    def read(self, name: str) -> bytes:
        """Read a whole file; raises FileNotFoundError if no entry has it."""
        found = self.find(name)
        if found is None:
            raise FileNotFoundError(name)
        return read_found(found)

    def names(self) -> set[str]:
        """Every name in the archives of the search path (not loose files)."""
        out: set[str] = set()
        for search_path in self.search_paths:
            if search_path.archive is not None:
                out.update(search_path.archive.names())
        return out


@dataclass(slots=True, frozen=True)
class ArchiveSpec:
    """An archive of a game directory, to be added to a search path."""

    path: str
    reader: type[PakArchive] | type[ZipArchive]
    protected: bool  # a numbered .pak: official data, never offered for download


def game_directory_archives(directory: str) -> list[ArchiveSpec]:
    """The archives of a game directory, in the order Quake II adds them.

    First the numbered paks (``pak0.pak`` to ``pak99.pak``, then the numbered
    zip types), then every other archive in the order the directory lists
    them. Each is put in front of the search path when added, so the last
    one is searched first.
    """
    specs: list[ArchiveSpec] = []
    for suffix, reader in PACK_TYPES:
        for number in range(MAX_PAKS):
            path = os.path.join(directory, f"pak{number}.{suffix}")
            if os.path.isfile(path):
                specs.append(ArchiveSpec(path, reader, reader is PakArchive))

    numbered = {f"pak{n}" for n in range(MAX_PAKS)}
    try:
        listing = os.listdir(directory)
    except OSError:
        listing = []
    for suffix, reader in PACK_TYPES:
        for entry in listing:
            stem, dot, ext = entry.rpartition(".")
            path = os.path.join(directory, entry)
            if dot and ext == suffix and stem.lower() not in numbered and os.path.isfile(path):
                specs.append(ArchiveSpec(path, reader, False))
    return specs


def read_found(found: FoundFile) -> bytes:
    if found.search_path.archive is not None:
        return found.search_path.archive.read(found.name)
    with open(os.path.join(found.search_path.directory, found.name), "rb") as f:
        return f.read()
