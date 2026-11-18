"""Save games: the server's half (Yamagi's sv_save.c).

A save directory (``save/<name>/`` in the game directory) holds:

- ``server.ssv``: a 32 byte comment, the map command, and the latched
  cvars (skill, coop, deathmatch...) as name/value pairs;
- ``game.ssv``: the game's state (written by the game);
- per level visited, ``<map>.sv2`` (the configstrings and the area portal
  state) and ``<map>.sav`` (the level's entities, written by the game).

``current`` is the save of the game being played; ``save`` and ``load``
copy it to and from a named save, and ``save0`` is the autosave.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import glob
import os
import shutil
import time

from backends.unix import system
from common import clientserver, cmdparser, collision, cvar, filesystem
from common.header import shared
from server import context, sv_init
from server.header import server as server_h

COMMENT_SIZE = 32
CVAR_VALUE_SIZE = 128
CONFIGSTRINGS_SIZE = shared.MAX_CONFIGSTRINGS * shared.MAX_QPATH
AUTOSAVES = ("save0", "current")


def _save_dir(name: str) -> str:
    return f"{filesystem.FS_Gamedir()}/save/{name}"


def _bad_save_name(name: str) -> bool:
    """A name that would leave the save directory.

    Yamagi only prints "Bad savedir." and carries on with the name; here it
    is refused.
    """
    if ".." in name or "/" in name or "\\" in name:
        clientserver.Com_Printf("Bad savedir.\n")
        return True
    return False


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def wipe_savegame(name: str) -> None:
    """Deletes a save's files."""
    clientserver.Com_DPrintf(f"SV_WipeSaveGame({name})\n")
    directory = _save_dir(name)
    _remove(f"{directory}/server.ssv")
    _remove(f"{directory}/game.ssv")
    for pattern in ("*.sav", "*.sv2"):
        for path in glob.glob(f"{glob.escape(directory)}/{pattern}"):
            _remove(path)


def _copy_file(src: str, dst: str) -> None:
    clientserver.Com_DPrintf(f"CopyFile ({src}, {dst})\n")
    try:
        shutil.copyfile(src, dst)
    except OSError:
        pass  # as the C, a file that can't be opened is skipped


def copy_savegame(src: str, dst: str) -> None:
    """Replaces save dst with a copy of save src."""
    clientserver.Com_DPrintf(f"SV_CopySaveGame({src}, {dst})\n")
    wipe_savegame(dst)

    src_dir, dst_dir = _save_dir(src), _save_dir(dst)
    filesystem.FS_CreatePath(f"{dst_dir}/server.ssv")
    _copy_file(f"{src_dir}/server.ssv", f"{dst_dir}/server.ssv")
    _copy_file(f"{src_dir}/game.ssv", f"{dst_dir}/game.ssv")

    for level in glob.glob(f"{glob.escape(src_dir)}/*.sav"):
        target = f"{dst_dir}/{os.path.basename(level)}"
        _copy_file(level, target)
        _copy_file(level[:-3] + "sv2", target[:-3] + "sv2")  # and its .sv2


def configstrings_blob() -> bytes:
    """The configstrings as the C's char[MAX_CONFIGSTRINGS][MAX_QPATH].

    The statusbar program is longer than one slot and runs on into the
    following ones, as in the C's array.
    """
    blob = bytearray(CONFIGSTRINGS_SIZE)
    for i, text in enumerate(sv_init.sv.configstrings[:shared.MAX_CONFIGSTRINGS]):
        if text:
            data = text.encode("latin-1")
            start = i * shared.MAX_QPATH
            blob[start:start + len(data)] = data
            blob[start + len(data)] = 0
    return bytes(blob)


def parse_configstrings(data: bytes) -> list[str]:
    """The configstrings from configstrings_blob()'s layout.

    Every slot is NUL terminated, except inside the statusbar program; a
    string that runs on into the following slots is held whole at its first
    index, and the slots it covers are empty.
    """
    data = bytearray(data.ljust(CONFIGSTRINGS_SIZE, b"\0"))
    for i in range(shared.MAX_CONFIGSTRINGS):
        if i < shared.CS_STATUSBAR or i >= shared.CS_STATUSBAR_END - 1:
            data[i * shared.MAX_QPATH + shared.MAX_QPATH - 1] = 0

    strings = [""] * shared.MAX_CONFIGSTRINGS
    i = 0
    while i < shared.MAX_CONFIGSTRINGS:
        start = i * shared.MAX_QPATH
        end = data.index(0, start)
        strings[i] = data[start:end].decode("latin-1")
        i += 1 + (end - start) // shared.MAX_QPATH
    return strings


def write_level_file() -> None:
    """Saves the level being played into the current save (.sv2 and .sav)."""
    clientserver.Com_DPrintf("SV_WriteLevelFile()\n")
    current = _save_dir("current")
    name = f"{current}/{sv_init.sv.name}.sv2"
    f = filesystem.Q_fopen(name, "wb")
    if f is None:
        clientserver.Com_Printf("Failed to open %s\n", name)
        return
    f.write(configstrings_blob())
    collision.CM_WritePortalState(f)
    f.close()

    # Yamagi changes the working directory and passes a relative name; the
    # full path does the same
    system.Sys_Mkdir(current)
    context.server.game.WriteLevel(f"{current}/{sv_init.sv.name}.sav")


def read_level_file() -> None:
    """Loads the level being entered from the current save."""
    clientserver.Com_DPrintf("SV_ReadLevelFile()\n")
    name = f"save/current/{sv_init.sv.name}.sv2"
    _, f = filesystem.FS_FOpenFile(name, True)
    if not f:
        clientserver.Com_Printf("Failed to open %s\n", name)
        return

    strings = parse_configstrings(filesystem.FS_Read(CONFIGSTRINGS_SIZE, f))
    sv_init.sv.configstrings[:shared.MAX_CONFIGSTRINGS] = strings
    collision.CM_ReadPortalState(f)
    filesystem.FS_FCloseFile(f)

    context.server.game.ReadLevel(f"{_save_dir('current')}/{sv_init.sv.name}.sav")


def save_comment(autosave: bool, levelname: str, now: time.struct_time) -> str:
    """The comment the load menu shows: the time and date, or ENTERING for an autosave."""
    if autosave:
        comment = f"ENTERING {levelname}"
    else:
        # as the C's "%2i:%i%i %2i/%2i  " (struct_time's months count from 1)
        comment = (f"{now.tm_hour:2}:{now.tm_min // 10}{now.tm_min % 10} "
                   f"{now.tm_mon:2}/{now.tm_mday:2}  {levelname}")
    return comment[:COMMENT_SIZE - 1]


def _padded(text: str, size: int) -> bytes:
    return text.encode("latin-1")[:size].ljust(size, b"\0")


def write_server_file(autosave: bool) -> None:
    """Writes server.ssv and the game state into the current save."""
    clientserver.Com_DPrintf("SV_WriteServerFile(%s)\n", "true" if autosave else "false")
    current = _save_dir("current")
    name = f"{current}/server.ssv"
    f = filesystem.Q_fopen(name, "wb")
    if f is None:
        clientserver.Com_Printf("Couldn't write %s\n", name)
        return

    comment = save_comment(autosave, sv_init.sv.configstrings[shared.CS_NAME], time.localtime())
    f.write(_padded(comment, COMMENT_SIZE))
    f.write(_padded(sv_init.svs.mapcmd[:server_h.MAX_SAVE_TOKEN_CHARS - 1],
                    server_h.MAX_SAVE_TOKEN_CHARS))

    # the latched cvars: coop, skill, deathmatch...
    for var in cvar.cvar_vars:
        if not var.flags & shared.CVAR_LATCH:
            continue
        if (len(var.name) >= shared.LATCH_CVAR_SAVELENGTH - 1
                or len(var.string) >= CVAR_VALUE_SIZE - 1):
            clientserver.Com_Printf("Cvar too long: %s = %s\n", var.name, var.string)
            continue
        f.write(_padded(var.name, shared.LATCH_CVAR_SAVELENGTH))
        f.write(_padded(var.string, CVAR_VALUE_SIZE))
    f.close()

    system.Sys_Mkdir(current)
    context.server.game.WriteGame(f"{current}/game.ssv", autosave)


def _c_string(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("latin-1")


def read_server_file() -> None:
    """Restarts the server with the current save's cvars, and reads the game state."""
    clientserver.Com_DPrintf("SV_ReadServerFile()\n")
    name = "save/current/server.ssv"
    _, f = filesystem.FS_FOpenFile(name, True)
    if not f:
        clientserver.Com_Printf("Couldn't read %s\n", name)
        return

    filesystem.FS_Read(COMMENT_SIZE, f)
    mapcmd = _c_string(filesystem.FS_Read(server_h.MAX_SAVE_TOKEN_CHARS, f))

    # the latched cvars, until the end of the file
    while True:
        data = filesystem.FS_FRead(1, shared.LATCH_CVAR_SAVELENGTH, f)
        if not data:
            break
        name, value = _c_string(data), _c_string(filesystem.FS_Read(CVAR_VALUE_SIZE, f))
        clientserver.Com_DPrintf("Set %s = %s\n", name, value)
        cvar.Cvar_ForceSet(name, value)
    filesystem.FS_FCloseFile(f)

    sv_init.new_game()  # a fresh game, with these cvars
    sv_init.svs.mapcmd = mapcmd
    context.server.game.ReadGame(f"{_save_dir('current')}/game.ssv")


def loadgame_command() -> None:
    """``load <name>``."""
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("USAGE: loadgame <directory>\n")
        return

    clientserver.Com_Printf("Loading game...\n")
    name = cmdparser.Cmd_Argv(1)
    if _bad_save_name(name):
        return

    path = f"{_save_dir(name)}/server.ssv"
    if not os.path.exists(path):
        clientserver.Com_Printf("No such savegame: %s\n", path)
        return
    clientserver.Com_Printf("Savegame: %s\n", name)

    copy_savegame(name, "current")
    read_server_file()

    sv_init.sv.state = server_h.server_state_t.ss_dead  # don't save the level being left
    sv_init.start_map(False, sv_init.svs.mapcmd, True, name in AUTOSAVES)


def savegame_command() -> None:
    """``save <name>``."""
    if sv_init.sv.state != server_h.server_state_t.ss_game:
        clientserver.Com_Printf("You must be in a game to save.\n")
        return
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("USAGE: savegame <directory>\n")
        return
    if cvar.Cvar_VariableValue("deathmatch"):
        clientserver.Com_Printf("Can't savegame in a deathmatch\n")
        return
    name = cmdparser.Cmd_Argv(1)
    if name == "current":
        clientserver.Com_Printf("Can't save to 'current'\n")
        return
    player = server_h.CL_EDICT(sv_init.svs.clients[0])
    if context.server.maxclients == 1 and player.client.ps.stats[shared.STAT_HEALTH] <= 0:
        clientserver.Com_Printf("\nCan't savegame while dead!\n")
        return
    if _bad_save_name(name):
        return

    clientserver.Com_Printf("Saving game...\n")
    # the level, with all the client edicts: when it is loaded they are
    # shells waiting for their clients
    write_level_file()
    write_server_file(False)
    copy_savegame("current", name)
    clientserver.Com_Printf("Done.\n")

