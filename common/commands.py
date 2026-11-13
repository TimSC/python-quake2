"""Console commands: the command buffer, tokenising, aliases and dispatch.

``CommandSystem`` follows Yamagi's cmdparser.c: text is queued in a buffer
(``exec`` and aliases insert at the front), split into lines at newlines and
at semicolons outside quotes, tokenised with ``$cvar`` expansion, and run as
a command, an alias, a cvar, or else sent to the server. It reaches the rest
of the engine only through the callbacks it is given.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable
from dataclasses import dataclass

from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c

BUFFER_SIZE = 32768        # the command buffer (and the deferred copy)
MAX_LINE = 1024            # one command line, as Cbuf_Execute cuts it
MAX_ALIAS_NAME = 32
ALIAS_LOOP_COUNT = 16      # aliases run per Cbuf_Execute, against runaway loops
MACRO_LOOP_COUNT = 100
WAIT_MSEC = 16             # "wait" waits about one frame at 60 fps

Command = Callable[[], None]


@dataclass(slots=True)
class Alias:
    name: str
    value: str  # the command text, ending with a newline


def tokenize_line(text: str) -> tuple[list[str], str]:
    """Split one command line into tokens (Cmd_TokenizeString without the
    macro expansion). Returns the tokens and the text after the first one."""
    argv: list[str] = []
    args = ""
    cursor = 0
    while True:
        while cursor < len(text) and text[cursor] <= " " and text[cursor] != "\n":
            cursor += 1
        if cursor >= len(text):
            return argv, args
        if text[cursor] == "\n":  # a newline separates commands in the buffer
            return argv, args
        if len(argv) == 1:
            args = text[cursor:].rstrip("".join(chr(c) for c in range(33)))
        token, cursor = shared_c.COM_Parse(text, cursor)
        if cursor is None:
            return argv, args
        if len(argv) < shared.MAX_STRING_TOKENS:
            argv.append(token)
        if cursor >= len(text):
            return argv, args


def _raise(text: str) -> None:
    raise RuntimeError(text)


class CommandSystem:
    """The commands, aliases and command buffer of an engine."""

    def __init__(self, *, print_: Callable[[str], None] = lambda text: None,
                 error: Callable[[str], None] | None = None,
                 cvar_string: Callable[[str], str] = lambda name: "",
                 cvar_command: Callable[[list[str]], bool] = lambda args: False,
                 cvar_names: Callable[[], list[str]] = lambda: [],
                 load_file: Callable[[str], bytes | None] = lambda name: None,
                 milliseconds: Callable[[], int] = lambda: 0,
                 forward_to_server: Callable[[], None] = lambda: None) -> None:
        self.print = print_
        self.error = error or _raise
        self.cvar_string = cvar_string          # a cvar's value, for $name and vstr
        self.cvar_command = cvar_command        # a cvar typed as a command
        self.cvar_names = cvar_names            # for completion
        self.load_file = load_file              # exec's script files
        self.milliseconds = milliseconds
        self.forward_to_server = forward_to_server  # an unknown command, when connected

        self.text = ""                # the command buffer
        self.deferred = ""            # Cbuf_CopyToDefer's copy
        self.wait_started = 0         # when "wait" was run (0: not waiting)
        self.alias_count = 0
        self.aliases: list[Alias] = []  # newest first
        self.functions: dict[str, Command | None] = {}  # None: forward to the server
        self._names: list[str] = []     # command names, sorted
        self.argv: list[str] = []       # the command being run
        self.args = ""                  # its text after the command name
        self.done_with_default_cfg = False

    # ---------------------------------------------------------- the buffer

    def add_text(self, text: str) -> None:
        """Queue text at the end of the buffer."""
        if len(self.text) + len(text) >= BUFFER_SIZE:
            self.print("Cbuf_AddText: overflow\n")
            return
        self.text += text

    def insert_text(self, text: str) -> None:
        """Queue text in front of what is waiting (exec, aliases, vstr)."""
        waiting, self.text = self.text, ""
        self.add_text(text)
        if len(self.text) + len(waiting) > BUFFER_SIZE:
            self.error("SZ_GetSpace: overflow without allowoverflow set")
            return
        self.text += waiting

    def copy_to_defer(self) -> None:
        self.deferred, self.text = self.text, ""

    def insert_from_defer(self) -> None:
        if self.deferred:
            self.insert_text(self.deferred)
            self.deferred = ""

    def execute_text(self, when: int, text: str) -> None:
        if when == common_h.EXEC_NOW:
            self.execute_string(text)
        elif when == common_h.EXEC_INSERT:
            self.insert_text(text)
        elif when == common_h.EXEC_APPEND:
            self.add_text(text)
        else:
            self.error("Cbuf_ExecuteText: bad exec_when")

    def execute(self) -> None:
        """Run the buffered commands (until a "wait")."""
        if self.wait_started > 0:
            if self.milliseconds() - self.wait_started <= WAIT_MSEC:
                return
            self.wait_started = 0
        self.alias_count = 0
        while self.text:
            text = self.text
            quotes = 0
            end = len(text)
            for i, c in enumerate(text):
                if c == '"':
                    quotes += 1
                if (c == ";" and not quotes & 1) or c == "\n":
                    end = i
                    break
            line = text[:min(end, MAX_LINE - 1)]
            # remove the line (and its separator) before running it: exec and
            # aliases insert at the front of the buffer
            self.text = text[end + 1:]
            self.execute_string(line)
            if self.wait_started > 0:
                break  # leave the rest for after the wait

    # ------------------------------------------------- tokenising and running

    def macro_expand(self, text: str) -> str | None:
        """Replace $name (outside quotes) with the cvar's value."""
        if len(text) >= shared.MAX_STRING_CHARS:
            self.print(f"Line exceeded {shared.MAX_STRING_CHARS} chars, discarded.\n")
            return None
        length = len(text)
        in_quote = False
        count = 0
        i = 0
        while i < len(text):
            c = text[i]
            if c == '"':
                in_quote = not in_quote
            if in_quote or c != "$":
                i += 1
                continue
            token, end = shared_c.COM_Parse(text, i + 1)
            if end is None:
                i += 1
                continue
            value = self.cvar_string(token)
            length += len(value)
            if length >= shared.MAX_STRING_CHARS:
                self.print(f"Expanded line exceeded {shared.MAX_STRING_CHARS} chars, "
                           "discarded.\n")
                return None
            text = text[:i] + value + text[end:]
            count += 1
            if count == MACRO_LOOP_COUNT:
                self.print("Macro expansion loop, discarded.\n")
                return None
            # the expanded value is scanned again from the same place
        if in_quote:
            self.print("Line has unmatched quote, discarded.\n")
            return None
        return text

    def tokenize(self, text: str, macro_expand: bool) -> None:
        """Split text into argv and args (expanding $cvars if asked)."""
        self.argv, self.args = [], ""
        expanded = self.macro_expand(text) if macro_expand else text
        if expanded:
            self.argv, self.args = tokenize_line(expanded)

    def argc(self) -> int:
        return len(self.argv)

    def arg(self, i: int) -> str:
        return self.argv[i] if i < len(self.argv) else ""

    def execute_string(self, text: str) -> None:
        """Run one command line."""
        self.tokenize(text, True)
        if not self.argv:
            return
        name = self.argv[0]
        if len(self.argv) > 1 and name.lower() == "exec" and self.argv[1].lower() == "yq2.cfg":
            # exec yq2.cfg comes right after exec default.cfg
            self.done_with_default_cfg = True

        found = self._find_command(name)
        if found is not None:
            function = self.functions[found]
            if function is None:
                self.execute_string(f"cmd {text}")  # forward to the server
            else:
                function()
            return

        for alias in self.aliases:
            if alias.name.lower() == name.lower():
                self.alias_count += 1
                if self.alias_count == ALIAS_LOOP_COUNT:
                    self.print("ALIAS_LOOP_COUNT\n")
                    return
                self.insert_text(alias.value)
                return

        if self.cvar_command(list(self.argv)):
            return
        self.forward_to_server()

    def _find_command(self, name: str) -> str | None:
        """The first command (in name order) matching name, ignoring case."""
        lowered = name.lower()
        for candidate in self._names:
            if candidate.lower() == lowered:
                return candidate
        return None

    # ------------------------------------------------------------ commands

    def add_command(self, name: str, function: Command | None) -> None:
        if self.cvar_string(name):  # a cvar of that name: the command replaces it
            self.remove_command(name)
        if name in self.functions:
            self.print(f"Cmd_AddCommand: {name} already defined\n")
            return
        self.functions[name] = function
        bisect.insort(self._names, name)

    def remove_command(self, name: str) -> None:
        if name in self.functions:
            del self.functions[name]
            self._names.remove(name)
        else:
            self.print(f"Cmd_RemoveCommand: {name} not added\n")

    def exists(self, name: str) -> bool:
        return name in self.functions

    def is_complete(self, name: str) -> bool:
        """Whether name is exactly a command, an alias or a cvar."""
        return (name in self.functions or any(a.name == name for a in self.aliases)
                or name in self.cvar_names())

    def complete(self, partial: str) -> str | None:
        """Complete a command, alias or cvar name; with several matches, print
        them and return their common prefix."""
        if not partial:
            return None
        names = [*self._names, *(a.name for a in self.aliases), *self.cvar_names()]
        if partial in names:
            return partial
        matches = [n for n in names if n.startswith(partial)]
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0][:255]
        matches.sort()
        self.print("\n\n")
        for match in matches:
            self.print(f"  {match}\n")
        prefix = ""
        for chars in zip(*matches, strict=False):
            if len(set(chars)) != 1 or len(prefix) >= 256:
                break
            prefix += chars[0]
        return prefix

    # ------------------------------------------------- the built-in commands

    def wait_command(self) -> None:
        self.wait_started = self.milliseconds()

    def exec_command(self) -> None:
        if self.argc() != 2:
            self.print("exec <filename> : execute a script file\n")
            return
        data = self.load_file(self.arg(1))
        if data is None:
            self.print(f"couldn't exec {self.arg(1)}\n")
            return
        self.print(f"execing {self.arg(1)}.\n")
        # the C treats the file as bytes; latin-1 keeps every byte
        self.insert_text(bytes(data).split(b"\0", 1)[0].decode("latin-1") + "\n")

    def vstr_command(self) -> None:
        if self.argc() != 2:
            self.print("vstr <variablename> : execute a variable command\n")
            return
        self.insert_text(f"{self.cvar_string(self.arg(1))}\n")

    def echo_command(self) -> None:
        self.print("".join(f"{arg} " for arg in self.argv[1:]) + "\n")

    def alias_command(self) -> None:
        if self.argc() == 1:
            self.print("Current alias commands:\n")
            for alias in self.aliases:
                self.print(f"{alias.name} : {alias.value}\n")
            return
        name = self.arg(1)
        if len(name) >= MAX_ALIAS_NAME:
            self.print("Alias name is too long\n")
            return
        value = (" ".join(self.argv[2:]))[:1022] + "\n"
        for alias in self.aliases:
            if alias.name == name:
                alias.value = value
                return
        self.aliases.insert(0, Alias(name, value))

    def list_command(self) -> None:
        for name in self._names:
            self.print(f"{name}\n")
        self.print(f"{len(self._names)} commands\n")

    def register_builtins(self) -> None:
        for name, function in (("cmdlist", self.list_command), ("exec", self.exec_command),
                               ("vstr", self.vstr_command), ("echo", self.echo_command),
                               ("alias", self.alias_command), ("wait", self.wait_command)):
            self.add_command(name, function)
