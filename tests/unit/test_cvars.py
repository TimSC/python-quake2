import pytest

from common.cvars import CvarRegistry, format_value, is_float
from common.header import shared


class Engine:
    """The callbacks a registry needs, recording what happened."""

    def __init__(self, server_running: bool = False) -> None:
        self.output: list[str] = []
        self.running = server_running
        self.games: list[str] = []
        self.user_games: list[str] = []

    def registry(self) -> CvarRegistry:
        return CvarRegistry(print_=self.output.append, server_running=lambda: self.running,
                            game_changed=self.games.append,
                            user_game_changed=self.user_games.append)


@pytest.fixture
def engine() -> Engine:
    return Engine()


@pytest.fixture
def cvars(engine: Engine) -> CvarRegistry:
    return engine.registry()


def test_get_creates_once_and_merges_flags(cvars):
    a = cvars.get("skill", "1", shared.CVAR_LATCH)
    assert (a.string, a.value, a.default_string, a.modified) == ("1", 1.0, "1", True)
    b = cvars.get("skill", "2", shared.CVAR_ARCHIVE)
    assert b is a
    assert a.string == "1"  # an existing cvar keeps its value
    assert a.default_string == "2"
    assert a.flags == shared.CVAR_LATCH | shared.CVAR_ARCHIVE


def test_sorted_by_name(cvars):
    for name in ("zz", "aa", "mm"):
        cvars.get(name, "0", 0)
    assert [v.name for v in cvars.vars] == ["aa", "mm", "zz"]


def test_value_parses_like_strtod(cvars):
    cvars.get("fov", "90.5abc", 0)
    assert cvars.value("fov") == 90.5
    assert cvars.value("missing") == 0
    assert cvars.string("missing") == ""


def test_deprecated_names(engine, cvars):
    var = cvars.get("gl_mode", "3", 0)
    assert var.name == "r_mode"
    assert "cvar gl_mode is deprecated, use r_mode instead\n" in engine.output
    assert cvars.value("gl_mode") == 3


def test_info_values_are_validated(engine, cvars):
    assert cvars.get("name", 'bad"name', shared.CVAR_USERINFO) is None
    assert "invalid info cvar value\n" in engine.output
    var = cvars.get("name", "player", shared.CVAR_USERINFO)
    cvars.set("name", "a;b")
    assert var.string == "player"


def test_userinfo_change_is_flagged(cvars):
    cvars.get("name", "player", shared.CVAR_USERINFO)
    cvars.userinfo_modified = False
    cvars.set("name", "other")
    assert cvars.userinfo_modified


def test_write_protected(engine, cvars):
    var = cvars.get("version", "1.0", shared.CVAR_NOSET)
    cvars.set("version", "2.0")
    assert var.string == "1.0"
    assert "version is write protected.\n" in engine.output
    cvars.set("version", "2.0", force=True)
    assert var.string == "2.0"


def test_latched_while_a_server_runs(engine, cvars):
    var = cvars.get("maxclients", "1", shared.CVAR_LATCH)
    engine.running = True
    cvars.set("maxclients", "8")
    assert (var.string, var.latched_string) == ("1", "8")
    assert "maxclients will be changed for next game.\n" in engine.output
    cvars.apply_latched()
    assert (var.string, var.value, var.latched_string) == ("8", 8.0, None)


def test_latched_without_a_server_changes_now(engine, cvars):
    var = cvars.get("game", "", shared.CVAR_LATCH)
    cvars.set("game", "ctf")
    assert var.string == "ctf"
    assert engine.games == ["ctf"]


def test_base_game_is_empty(cvars):
    var = cvars.get("game", "baseq2", 0)
    assert var.string == ""
    cvars.set("game", "baseq2")
    assert var.string == ""


def test_set_value_formats(cvars):
    cvars.set_value("a", 3.0)
    cvars.set_value("b", 0.5)
    assert cvars.string("a") == "3" and cvars.string("b") == "0.500000"
    assert format_value(-2.0) == "-2"


def test_full_set_replaces_flags(cvars):
    var = cvars.get("x", "1", shared.CVAR_ARCHIVE)
    cvars.full_set("x", "2", shared.CVAR_SERVERINFO)
    assert (var.string, var.flags) == ("2", shared.CVAR_SERVERINFO)


def test_info_string(cvars):
    cvars.get("name", "player", shared.CVAR_USERINFO)
    cvars.get("skin", "male/grunt", shared.CVAR_USERINFO)
    cvars.get("hostname", "server", shared.CVAR_SERVERINFO)
    info = cvars.info_string(shared.CVAR_USERINFO)
    assert "\\name\\player" in info and "\\skin\\male/grunt" in info
    assert "hostname" not in info


def test_write_archived(tmp_path, cvars):
    cvars.get("b", "2", shared.CVAR_ARCHIVE)
    cvars.get("a", "1", shared.CVAR_ARCHIVE)
    cvars.get("c", "3", 0)
    path = tmp_path / "config.cfg"
    cvars.write_archived(str(path))
    assert path.read_text() == 'set a "1"\nset b "2"\n'


def test_console_print_and_set(engine, cvars):
    cvars.get("fov", "90", 0)
    assert cvars.command(["fov"])
    assert engine.output[-1] == '"fov" is "90"\n'
    assert cvars.command(["fov", "110"])
    assert cvars.string("fov") == "110"
    assert not cvars.command(["notacvar", "1"])


def test_console_game_sets_the_user_game(engine, cvars):
    cvars.get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)
    cvars.command(["game", "rogue"])
    assert engine.user_games == ["rogue"]


@pytest.mark.parametrize("args, name, value, flags", [
    (["set", "a", "1"], "a", "1", 0),
    (["set", "a", "1", "a"], "a", "1", shared.CVAR_ARCHIVE),
    (["set", "a", "1", "u"], "a", "1", shared.CVAR_USERINFO),
    (["set", "a", "1", "s"], "a", "1", shared.CVAR_SERVERINFO),
])
def test_set_command(cvars, args, name, value, flags):
    cvars.set_command(args)
    var = cvars.find(name)
    assert (var.string, var.flags) == (value, flags)


def test_set_command_errors(engine, cvars):
    cvars.set_command(["set", "a"])
    cvars.set_command(["set", "a", "1", "x"])
    assert engine.output == ["usage: set <variable> <value> [u / s]\n",
                             "flags can only be 'a', 'u' or 's'\n"]
    assert cvars.find("a") is None


def test_inc_and_dec(engine, cvars):
    cvars.get("v", "1", 0)
    cvars.inc_command(["inc", "v"])
    assert cvars.value("v") == 2
    cvars.inc_command(["dec", "v", "0.5"])
    assert cvars.value("v") == 1.5
    cvars.get("s", "abc", 0)
    cvars.inc_command(["inc", "s"])
    assert engine.output[-1] == "\"s\" is \"abc\", can't inc\n"


def test_toggle_and_cycle(cvars):
    cvars.get("t", "0", 0)
    cvars.toggle_command(["toggle", "t"])
    assert cvars.string("t") == "1"
    cvars.toggle_command(["toggle", "t"])
    assert cvars.string("t") == "0"
    cvars.set("t", "B")
    cvars.toggle_command(["toggle", "t", "a", "b", "c"])  # case-insensitive match
    assert cvars.string("t") == "c"
    cvars.toggle_command(["toggle", "t", "a", "b", "c"])
    assert cvars.string("t") == "a"


def test_reset_and_reset_all(cvars):
    cvars.get("a", "1", 0)
    cvars.get("b", "2", shared.CVAR_NOSET)
    cvars.get("game", "", 0)
    cvars.set("a", "5")
    cvars.set("game", "ctf")
    cvars.reset_command(["reset", "a"])
    assert cvars.string("a") == "1"
    cvars.set("a", "5")
    cvars.reset_all_command(["resetall"])
    assert cvars.string("a") == "1" and cvars.string("game") == "ctf"


def test_complete(cvars):
    for name in ("cl_run", "cl_maxfps", "fov"):
        cvars.get(name, "0", 0)
    assert cvars.complete("fov") == "fov"
    assert cvars.complete("cl_m") == "cl_maxfps"
    assert cvars.complete("zz") is None


@pytest.mark.parametrize("text, expected", [
    ("1", True), ("-1.5", True), (".5", True), ("1.2.3", False), ("-", False), ("", False),
    ("1e5", False), ("abc", False),
])
def test_is_float(text, expected):
    assert is_float(text) is expected


def test_list_command(engine, cvars):
    cvars.get("a", "1", shared.CVAR_ARCHIVE | shared.CVAR_LATCH)
    cvars.list_command(["cvarlist"])
    assert "".join(engine.output) == '*  L a "1"\n1 cvars\n'
