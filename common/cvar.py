"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

The engine's cvars, and the old Cvar_* functions the rest of the engine
still calls. The cvars themselves are in common/cvars.py's CvarRegistry;
these functions are a thin layer over the engine's one registry, kept until
the callers use it directly.

=======================================================================
"""

from common import cmdparser
from common.cvars import to_number
from common.engine import engine
from common.header import shared

registry = engine.cvars  # the engine's cvars
cvar_vars = registry.vars  # every cvar, sorted by name


def _args() -> list[str]:
    return [cmdparser.Cmd_Argv(i) for i in range(cmdparser.Cmd_Argc())]


def Cvar_Get(var_name: str, var_value: str | None, flags: int) -> shared.cvar_t | None:  # noqa: N802
    return registry.get(var_name, var_value, flags)


def Cvar_Set(var_name: str, value: str) -> shared.cvar_t | None:  # noqa: N802
    return registry.set(var_name, value)


def Cvar_ForceSet(var_name: str, value: str) -> shared.cvar_t | None:  # noqa: N802
    return registry.set(var_name, value, force=True)


def Cvar_FullSet(var_name: str, value: str, flags: int) -> shared.cvar_t | None:  # noqa: N802
    return registry.full_set(var_name, value, flags)


def Cvar_SetValue(var_name: str, value: float) -> None:  # noqa: N802
    registry.set_value(var_name, value)


def Cvar_VariableValue(var_name: str) -> float:  # noqa: N802
    return registry.value(var_name)


def Cvar_VariableString(var_name: str) -> str:  # noqa: N802
    return registry.string(var_name)


def Cvar_CompleteVariable(partial: str) -> str | None:  # noqa: N802
    return registry.complete(partial)


def Cvar_GetLatchedVars() -> None:  # noqa: N802
    registry.apply_latched()


def Cvar_Command() -> bool:  # noqa: N802
    """A cvar name at the console (the command's arguments)."""
    return registry.command(_args())


def Cvar_WriteVariables(path: str) -> None:  # noqa: N802
    registry.write_archived(path)


def Cvar_Userinfo() -> str:  # noqa: N802
    return registry.info_string(shared.CVAR_USERINFO)


def Cvar_Serverinfo() -> str:  # noqa: N802
    return registry.info_string(shared.CVAR_SERVERINFO)


def strtod(s: str) -> float:
    return to_number(s)


def Cvar_Init() -> None:  # noqa: N802
    registry.clear()
    for name, command in registry.commands().items():
        cmdparser.Cmd_AddCommand(name, lambda command=command: command(_args()))


def Cvar_Fini() -> None:  # noqa: N802
    registry.clear()
    for name in registry.commands():
        cmdparser.Cmd_RemoveCommand(name)
