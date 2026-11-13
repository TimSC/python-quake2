import pytest

from q2data import FormatError
from q2data.pak import PakArchive, ZipArchive, write_pak, write_zip

FILES = {"maps/test.bsp": b"map data", "pics/Colormap.pcx": b"\x0a" * 10, "empty.txt": b""}


@pytest.mark.parametrize("from_file", [False, True])
def test_pak_round_trip(tmp_path, from_file):
    data = write_pak(FILES)
    if from_file:
        path = tmp_path / "pak0.pak"
        path.write_bytes(data)
        pak = PakArchive(path)
    else:
        pak = PakArchive(data)
    assert pak.names() == list(FILES)
    for name, contents in FILES.items():
        assert pak.read(name) == contents


def test_pak_lookup_ignores_case():
    pak = PakArchive(write_pak(FILES))
    assert "PICS/colormap.PCX" in pak
    assert pak.read("pics/colormap.pcx") == FILES["pics/Colormap.pcx"]


def test_pak_missing_file():
    pak = PakArchive(write_pak(FILES))
    assert "nothere" not in pak
    with pytest.raises(FileNotFoundError):
        pak.read("nothere")


def test_pak_rejects_bad_files():
    with pytest.raises(FormatError):
        PakArchive(b"PACX" + bytes(8))
    with pytest.raises(FormatError):
        PakArchive(b"PACK")
    empty = write_pak({})
    with pytest.raises(FormatError, match="too short"):
        PakArchive(empty)
    truncated = write_pak(FILES)[:-10]
    with pytest.raises(FormatError):
        PakArchive(truncated)


def test_pak_name_too_long():
    with pytest.raises(FormatError):
        write_pak({"x" * 56: b""})


def test_zip_round_trip_and_case():
    archive = ZipArchive(write_zip(FILES))
    assert sorted(archive.names()) == sorted(FILES)
    assert archive.read("MAPS/TEST.BSP") == b"map data"
    with pytest.raises(FileNotFoundError):
        archive.read("nothere")


def test_zip_rejects_non_zip():
    with pytest.raises(FormatError):
        ZipArchive(b"not a zip file")
