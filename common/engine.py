"""The engine object: the subsystems an engine owns, wired together.

It holds the cvars and the console commands so far; more subsystems move in
as they are reworked (see docs/pythonic_plan.md, step 3). The old modules
reach it through ``common.engine.engine`` until their callers are given the
engine directly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from common.commands import CommandSystem
from common.cvars import CvarRegistry


@dataclass(slots=True)
class EngineHooks:
    """What the engine's subsystems need from the parts not yet reworked."""

    print_: Callable[[str], None]
    fatal_error: Callable[[str], None]
    server_running: Callable[[], bool]
    game_changed: Callable[[str], None]
    user_game_changed: Callable[[str], None]
    load_file: Callable[[str], bytes | None]
    milliseconds: Callable[[], int]
    forward_to_server: Callable[[], None]


class Engine:
    """An engine's cvars and commands."""

    def __init__(self, hooks: EngineHooks) -> None:
        self.hooks = hooks
        self.cvars = CvarRegistry(print_=hooks.print_, server_running=hooks.server_running,
                                  game_changed=hooks.game_changed,
                                  user_game_changed=hooks.user_game_changed)
        cvars = self.cvars
        self.commands = CommandSystem(
            print_=hooks.print_, error=hooks.fatal_error,
            cvar_string=cvars.string, cvar_command=cvars.command,
            cvar_names=lambda: [var.name for var in cvars.vars],
            load_file=hooks.load_file, milliseconds=hooks.milliseconds,
            forward_to_server=hooks.forward_to_server)


def _hooks() -> EngineHooks:
    # The parts of the engine not yet reworked, imported when called: they
    # import the modules that use this one.
    def print_(text: str) -> None:
        from common import clientserver
        clientserver.Com_Printf(text)

    def fatal_error(text: str) -> None:
        from common import clientserver
        from common.header import shared
        clientserver.Com_Error(shared.ERR_FATAL, text)

    def server_running() -> bool:
        from common import clientserver
        return bool(clientserver.Com_ServerState())

    def game_changed(game: str) -> None:
        from common import filesystem
        filesystem.FS_BuildGameSpecificSearchPath(game)

    def user_game_changed(game: str) -> None:
        from common import frame
        frame.userGivenGame = game

    def load_file(name: str) -> bytes | None:
        from common import filesystem
        length, data = filesystem.FS_LoadFile(name)
        return None if data is None else bytes(data[:length])

    def milliseconds() -> int:
        from backends.unix import system
        return system.Sys_Milliseconds()

    def forward_to_server() -> None:
        from client import cl_network
        cl_network.Cmd_ForwardToServer()

    return EngineHooks(print_, fatal_error, server_running, game_changed, user_game_changed,
                       load_file, milliseconds, forward_to_server)


# The process's engine (a single one until the server and client take it as a
# parameter).
engine = Engine(_hooks())
