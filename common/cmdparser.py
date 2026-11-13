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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
USA.

=======================================================================

The engine's console commands, and the old Cbuf_* / Cmd_* functions the rest
of the engine still calls. The command processor is common/commands.py's
CommandSystem; these functions are a thin layer over the engine's one
CommandSystem, kept until the callers use it directly. The command line
(+set and + commands) and map name completion are here too.

=======================================================================
"""

from common import argproc, clientserver, filesystem
from common.engine import engine
from common.shared import shared as shared_c

commands = engine.commands  # the engine's commands


# ------------------------------------------------------------- the buffer

def Cbuf_Init() -> None:  # noqa: N802
    commands.text = ""


def Cbuf_AddText(text: str) -> None:  # noqa: N802
    commands.add_text(text)


def Cbuf_InsertText(text: str) -> None:  # noqa: N802
    commands.insert_text(text)


def Cbuf_CopyToDefer() -> None:  # noqa: N802
    commands.copy_to_defer()


def Cbuf_InsertFromDefer() -> None:  # noqa: N802
    commands.insert_from_defer()


def Cbuf_ExecuteText(exec_when: int, text: str) -> None:  # noqa: N802
    commands.execute_text(exec_when, text)


def Cbuf_Execute() -> None:  # noqa: N802
    commands.execute()


def Cbuf_AddEarlyCommands(clear: bool) -> None:  # noqa: N802
    """Queue the command line's "+set name value" (before the client and
    server start), removing them from the arguments if clear."""
    i = 0
    while i < argproc.COM_Argc():
        if argproc.COM_Argv(i) != "+set":
            i += 1
            continue
        commands.add_text(f"set {argproc.COM_Argv(i + 1)} {argproc.COM_Argv(i + 2)}\n")
        if clear:
            for j in range(i, i + 3):
                argproc.COM_ClearArgv(j)
        i += 3


def Cbuf_AddLateCommands() -> bool:  # noqa: N802
    """Queue the command line's other + commands (e.g. +map base1); each runs
    to the next + or " -". Returns whether there were any."""
    text = " ".join(argproc.COM_Argv(i) for i in range(1, argproc.COM_Argc()))
    if not text:
        return False
    found = False
    i = 0
    while i < len(text) - 1:
        if text[i] == "+":
            i += 1
            j = i
            while j < len(text) and text[j] != "+" and not (text[j] == "-" and text[j - 1] == " "):
                j += 1
            commands.add_text(text[i:j] + "\n")
            found = True
            i = j - 1
        i += 1
    return found


# ----------------------------------------------------------- the commands

def Cmd_Argc() -> int:  # noqa: N802
    return commands.argc()


def Cmd_Argv(arg: int) -> str:  # noqa: N802
    return commands.arg(arg)


def Cmd_Args() -> str:  # noqa: N802
    return commands.args


def Cmd_TokenizeString(text: str, macro_expand: bool) -> None:  # noqa: N802
    commands.tokenize(text, macro_expand)


def Cmd_ExecuteString(text: str) -> None:  # noqa: N802
    commands.execute_string(text)


def Cmd_AddCommand(cmd_name: str, function) -> None:  # noqa: N802
    commands.add_command(cmd_name, function)


def Cmd_RemoveCommand(cmd_name: str) -> None:  # noqa: N802
    commands.remove_command(cmd_name)


def Cmd_Exists(cmd_name: str) -> bool:  # noqa: N802
    return commands.exists(cmd_name)


def Cmd_IsComplete(command: str) -> bool:  # noqa: N802
    return commands.is_complete(command)


def Cmd_CompleteCommand(partial: str) -> str | None:  # noqa: N802
    return commands.complete(partial)


def Cmd_CompleteMapCommand(partial: str) -> str:  # noqa: N802
    """Complete a map name; with several matches, print them and return
    their common prefix (ignoring case)."""
    names = filesystem.FS_ListFiles2("maps/*.bsp", 0, 0)
    result = ""
    if not names.num:
        return result
    matches = []
    for i in range(names.num):
        name = names.data[i].rsplit("/", 1)[-1].split(".")[0]
        if not shared_c.Q_strcasecmp(partial, name):
            result = partial[:255]
        elif partial.lower() == name[:len(partial)].lower():
            matches.append(name)
    if len(matches) == 1:
        return matches[0][:255]
    if len(matches) > 1:
        clientserver.Com_Printf("\n=================\n\n")
        matches.sort()
        for name in matches:
            clientserver.Com_Printf(f"{name}\n")
        for j, c in enumerate(matches[0]):
            if any(j >= len(m) or m[j].lower() != c.lower() for m in matches[1:]):
                break
            result = result[:j] + c
    return result


def Cmd_Init() -> None:  # noqa: N802
    commands.register_builtins()
