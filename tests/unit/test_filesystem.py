import pytest

from q2data.filesystem import FileSystem
from q2data.pak import write_pak, write_zip


@pytest.fixture
def game_dir(tmp_path):
    """A game directory where every source has its own version of shared.txt."""
    d = tmp_path / "baseq2"
    d.mkdir()
    (d / "shared.txt").write_bytes(b"loose")
    (d / "loose_only.txt").write_bytes(b"loose only")
    (d / "pak0.pak").write_bytes(write_pak({"shared.txt": b"pak0", "pak0_only.txt": b"0"}))
    (d / "pak1.pak").write_bytes(write_pak({"shared.txt": b"pak1"}))
    (d / "pak0.pk3").write_bytes(write_zip({"shared.txt": b"pk3"}))
    (d / "mymod.pak").write_bytes(write_pak({"shared.txt": b"mymod", "mod_only.txt": b"m"}))
    (d / "notes.txt").write_bytes(b"not an archive")
    return d


def test_search_order(game_dir):
    fs = FileSystem()
    assert fs.add_game_directory(game_dir) == []
    names = [p.name.rsplit("/", 1)[-1] for p in fs.search_paths]
    # Each source goes in front, so the order is the reverse of adding:
    # the directory, numbered paks, numbered zips, then other archives.
    assert names == ["mymod.pak", "pak0.pk3", "pak1.pak", "pak0.pak", "baseq2"]
    assert fs.read("shared.txt") == b"mymod"
    assert fs.read("pak0_only.txt") == b"0"
    assert fs.read("loose_only.txt") == b"loose only"
    assert fs.read("mod_only.txt") == b"m"


def test_protected_paks(game_dir):
    fs = FileSystem()
    fs.add_game_directory(game_dir)
    protected = {p.name.rsplit("/", 1)[-1]: p.protected for p in fs.search_paths}
    assert protected == {"mymod.pak": False, "pak0.pk3": False, "pak1.pak": True,
                         "pak0.pak": True, "baseq2": False}


def test_find_and_missing(game_dir):
    fs = FileSystem()
    fs.add_game_directory(game_dir)
    found = fs.find("pak0_only.txt")
    assert found is not None and found.in_archive
    assert fs.find("loose_only.txt").in_archive is False
    assert not fs.exists("missing.txt")
    with pytest.raises(FileNotFoundError):
        fs.read("missing.txt")


def test_broken_archive_is_reported(game_dir):
    (game_dir / "pak2.pak").write_bytes(b"garbage")
    fs = FileSystem()
    failures = fs.add_game_directory(game_dir)
    assert [path.rsplit("/", 1)[-1] for path, _ in failures] == ["pak2.pak"]
    assert fs.read("shared.txt") == b"mymod"


def test_mod_directory_overrides_base(tmp_path, game_dir):
    mod = tmp_path / "mod"
    mod.mkdir()
    (mod / "shared.txt").write_bytes(b"mod dir")
    fs = FileSystem()
    fs.add_game_directory(game_dir)
    fs.add_game_directory(mod)
    assert fs.read("shared.txt") == b"mod dir"
    assert fs.read("pak0_only.txt") == b"0"
