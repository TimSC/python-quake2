import pytest

from common.commands import BUFFER_SIZE, CommandSystem, tokenize_line
from common.header import common as common_h


class Engine:
    """The callbacks a CommandSystem needs, recording what happened."""

    def __init__(self) -> None:
        self.output: list[str] = []
        self.cvars: dict[str, str] = {}
        self.files: dict[str, bytes] = {}
        self.forwarded: list[list[str]] = []
        self.now = 1000
        self.system = CommandSystem(
            print_=self.output.append,
            cvar_string=lambda name: self.cvars.get(name, ""),
            cvar_command=self.cvar_command,
            cvar_names=lambda: sorted(self.cvars),
            load_file=self.files.get,
            milliseconds=lambda: self.now,
            forward_to_server=lambda: self.forwarded.append(list(self.system.argv)))
        self.system.register_builtins()
        self.ran: list[list[str]] = []
        self.system.add_command("say", lambda: self.ran.append(list(self.system.argv)))

    def cvar_command(self, args: list[str]) -> bool:
        if args[0] not in self.cvars:
            return False
        if len(args) > 1:
            self.cvars[args[0]] = args[1]
        return True


@pytest.fixture
def engine() -> Engine:
    return Engine()


def test_tokenize():
    argv, args = tokenize_line('say "hello there"  world  ')
    assert argv == ["say", "hello there", "world"]
    assert args == '"hello there"  world'


def test_tokenize_stops_at_newline():
    assert tokenize_line("a b\nc d")[0] == ["a", "b"]


def test_lines_split_at_semicolons_outside_quotes(engine):
    engine.system.add_text('say a; say "b;c"\nsay d\n')
    engine.system.execute()
    assert engine.ran == [["say", "a"], ["say", "b;c"], ["say", "d"]]
    assert engine.system.text == ""


def test_commands_ignore_case(engine):
    engine.system.execute_string("SAY hi")
    assert engine.ran == [["SAY", "hi"]]


def test_macro_expansion(engine):
    engine.cvars["name"] = "Player"
    engine.system.execute_string('say $name "$name"')
    assert engine.ran == [["say", "Player", "$name"]]


def test_macro_errors(engine):
    engine.cvars["loop"] = "$loop"
    assert engine.system.macro_expand("say $loop") is None
    assert engine.output[-1] == "Macro expansion loop, discarded.\n"
    assert engine.system.macro_expand('say "open') is None
    assert engine.output[-1] == "Line has unmatched quote, discarded.\n"


def test_alias(engine):
    engine.system.execute_string("alias greet say hello ; say again")
    assert engine.system.aliases[0].value == "say hello ; say again\n"
    engine.system.add_text("GREET\n")
    engine.system.execute()
    assert engine.ran == [["say", "hello"], ["say", "again"]]


def test_newest_alias_listed_first(engine):
    engine.system.execute_string("alias a say 1")
    engine.system.execute_string("alias b say 2")
    engine.system.execute_string("alias a say 3")  # reused, keeps its place
    assert [a.name for a in engine.system.aliases] == ["b", "a"]
    assert engine.system.aliases[1].value == "say 3\n"


def test_alias_loop_is_stopped(engine):
    engine.system.execute_string("alias loop loop")
    engine.system.add_text("loop\n")
    engine.system.execute()
    assert "ALIAS_LOOP_COUNT\n" in engine.output


def test_cvars_then_server(engine):
    engine.cvars["fov"] = "90"
    engine.system.execute_string("fov 110")
    assert engine.cvars["fov"] == "110"
    engine.system.execute_string("kill now")
    assert engine.forwarded == [["kill", "now"]]


def test_command_forwarded_when_it_has_no_function(engine):
    engine.system.add_command("score", None)
    engine.system.execute_string("score")
    assert engine.forwarded == [["cmd", "score"]]


def test_wait_delays_the_rest(engine):
    engine.system.add_text("say 1; wait; say 2\n")
    engine.system.execute()
    assert engine.ran == [["say", "1"]]
    engine.now += 10
    engine.system.execute()
    assert engine.ran == [["say", "1"]]  # under one 60 fps frame
    engine.now += 10
    engine.system.execute()
    assert engine.ran == [["say", "1"], ["say", "2"]]


def test_exec(engine):
    engine.files["test.cfg"] = b"say from file\nsay \xe9t\xe9"
    engine.system.add_text("exec test.cfg\nsay after\n")
    engine.system.execute()
    assert engine.ran == [["say", "from", "file"], ["say", "\xe9t\xe9"], ["say", "after"]]
    assert "execing test.cfg.\n" in engine.output
    engine.system.execute_string("exec missing.cfg")
    assert engine.output[-1] == "couldn't exec missing.cfg\n"


def test_yq2_cfg_marks_default_cfg_done(engine):
    engine.system.execute_string("exec yq2.cfg")
    assert engine.system.done_with_default_cfg


def test_insert_goes_first(engine):
    engine.system.add_text("say last\n")
    engine.system.insert_text("say first\n")
    engine.system.execute()
    assert engine.ran == [["say", "first"], ["say", "last"]]


def test_buffer_overflow(engine):
    engine.system.add_text("x" * (BUFFER_SIZE - 1))
    engine.system.add_text("more")
    assert engine.output[-1] == "Cbuf_AddText: overflow\n"


def test_defer(engine):
    engine.system.add_text("say later\n")
    engine.system.copy_to_defer()
    assert engine.system.text == ""
    engine.system.insert_from_defer()
    engine.system.execute()
    assert engine.ran == [["say", "later"]]


def test_execute_text(engine):
    engine.system.execute_text(common_h.EXEC_NOW, "say now")
    engine.system.execute_text(common_h.EXEC_APPEND, "say append\n")
    engine.system.execute_text(common_h.EXEC_INSERT, "say insert\n")
    engine.system.execute()
    assert engine.ran == [["say", "now"], ["say", "insert"], ["say", "append"]]


def test_add_and_remove(engine):
    engine.system.add_command("say", lambda: None)
    assert engine.output[-1] == "Cmd_AddCommand: say already defined\n"
    engine.system.remove_command("say")
    assert not engine.system.exists("say")
    engine.system.remove_command("say")
    assert engine.output[-1] == "Cmd_RemoveCommand: say not added\n"


def test_echo_and_vstr(engine):
    engine.cvars["v"] = "say from vstr"
    engine.system.add_text("echo a b\nvstr v\n")
    engine.system.execute()
    assert "a b \n" in engine.output
    assert engine.ran == [["say", "from", "vstr"]]


def test_complete(engine):
    engine.cvars["sensitivity"] = "3"
    engine.system.execute_string("alias sayall say all")
    assert engine.system.complete("sens") == "sensitivity"
    assert engine.system.complete("say") == "say"
    assert engine.system.complete("sa") == "say"  # say, sayall: their common prefix
    assert "  sayall\n" in engine.output
    assert engine.system.complete("zz") is None
    assert engine.system.is_complete("sayall")
