"""The server operator's console commands (Yamagi's sv_cmd.c).

``SV_InitOperatorCommands`` adds them: maps (``map``, ``gamemap``,
``demomap``, ``listmaps``), clients (``kick``, ``status``, ``dumpuser``,
the dedicated console's ``say``), the server info, masters and heartbeats,
the server demo (``serverrecord``, ``serverstop``), saves, ``killserver``,
``gamemode``, and ``sv`` for the game's own commands.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import struct

from backends.unix import network
from common import (
    argproc,
    clientserver,
    cmdparser,
    cvar,
    filesystem,
    frame,
    movemsg,
    netchan,
    szone,
)
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from server import sv_game, sv_init, sv_main, sv_save, sv_send
from server.header import server as server_h

CS = server_h.client_state_t
SVC = common_h.svc_ops_e

SAY_SIZE = 1024  # the C's char text[1024]
DEMO_MULTICAST_SIZE = 65536  # the C's is MAX_MSGLEN, which a busy frame overflows
SIGNON_SIZE = 32768


def _no_server() -> bool:
    if not sv_init.svs.initialized:
        clientserver.Com_Printf("No server running.\n")
        return True
    return False


def _set_master() -> None:
    """``setmaster <address>...``: the master servers to send heartbeats to."""
    if not frame.dedicated.value:
        clientserver.Com_Printf("Only dedicated servers use masters.\n")
        return

    cvar.Cvar_Set("public", "1")  # listed in the masters

    masters = sv_init.server.masters
    for i in range(1, server_h.MAX_MASTERS):
        masters[i] = common_h.netadr_t()

    slot = 1  # slot 0 is always the id master
    for i in range(1, cmdparser.Cmd_Argc()):
        if slot == server_h.MAX_MASTERS:
            break
        # into the slot it goes to (the C parses into slot i, which leaves
        # a gap after a bad address)
        if not network.NET_StringToAdr(cmdparser.Cmd_Argv(i), masters[slot]):
            clientserver.Com_Printf("Bad address: %s\n", cmdparser.Cmd_Argv(i))
            continue
        if masters[slot].port == 0:
            masters[slot].port = shared_c.BigShort(common_h.PORT_MASTER)

        clientserver.Com_Printf("Master server at %s\n", network.NET_AdrToString(masters[slot]))
        clientserver.Com_Printf("Sending a ping.\n")
        netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, masters[slot], "ping")
        slot += 1

    sv_init.svs.last_heartbeat = -9999999


def find_client(who: str, clients: list) -> server_h.client_t | str:
    """The client a command names, by slot number or name; else why not.

    A name starting with a digit is a slot number, read as the C's strtol
    (so "1abc" is slot 1).
    """
    if who[:1].isdigit():
        slot = shared_c.atoi(who)
        if slot >= len(clients):
            return f"Bad client slot: {slot}\n"
        if clients[slot].state == CS.cs_free:
            return f"Client {slot} is not active\n"
        return clients[slot]

    for cl in clients:
        if cl.state != CS.cs_free and cl.name == who:
            return cl
    return f"Userid {who} is not on the server\n"


def _set_player() -> bool:
    """Makes the client that argument 1 names the current one."""
    if cmdparser.Cmd_Argc() < 2:
        return False
    who = cmdparser.Cmd_Argv(1)
    clients = sv_init.svs.clients[:sv_init.server.maxclients]
    found = find_client(who, clients)

    if who[:1].isdigit():
        # the C makes a slot current even when it isn't active
        slot = shared_c.atoi(who)
        if slot < len(clients):
            sv_init.server.set_client(clients[slot])
    if isinstance(found, str):
        clientserver.Com_Printf("%s", found)
        return False
    sv_init.server.set_client(found)
    return True


def _demo_map() -> None:
    """``demomap <demo.dm2>``: plays a demo (or a cinematic) on the server."""
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("USAGE: demomap <demoname.dm2>\n")
        return
    sv_init.SV_Map(True, cmdparser.Cmd_Argv(1), False, False)


def _save_level_for_return() -> None:
    """Saves the level being left, with no clients in it.

    So the clients spawn at spawn points when the level is entered again,
    instead of in the bodies they left.
    """
    maxclients = sv_init.server.maxclients
    was_in_use = []
    for i in range(maxclients):
        clent = server_h.CLNUM_EDICT(i)
        was_in_use.append(bool(clent.inuse))
        clent.inuse = False

    sv_save.SV_WriteLevelFile()

    for i in range(maxclients):
        server_h.CLNUM_EDICT(i).inuse = was_in_use[i]  # for the clients to move over


def _map_name_as_file(name: str) -> str:
    """The map name in the case of its file (e.g. "BASE1" for maps/base1.bsp).

    A save made under the wrong case would not be found when coming back
    to the map. (Forms like base2$base1 aren't handled.)
    """
    star = name[:1] == "*"
    size, f = filesystem.FS_FOpenFile(f"maps/{name[1:] if star else name}.bsp", False)
    if size < 0:
        return name
    path = filesystem.FS_GetFilenameForHandle(f)[:shared.MAX_QPATH - 1]
    filesystem.FS_FCloseFile(f)

    fixed = path[4:]  # without "maps", keeping the '/'
    fixed = "*" + fixed[1:] if star else fixed[1:]
    return fixed[:-4]  # without ".bsp"


def _game_map() -> None:
    """``gamemap <map>``: saves the level being left and goes to a new one.

    A map starting with '*' begins a new unit, which clears the current
    save's levels; ``*inter.cin+jail`` clears them, plays inter.cin and
    goes to jail.bsp.
    """
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("USAGE: gamemap <map>\n")
        return
    name = cmdparser.Cmd_Argv(1)
    if len(name) >= shared.MAX_QPATH:
        clientserver.Com_Printf("gamemap is too long\n")
        return

    clientserver.Com_DPrintf("%s(%s)\n", "SV_GameMap_f", name)
    filesystem.FS_CreatePath(f"{filesystem.FS_Gamedir()}/save/current/")

    if name[:1] == "*":
        sv_save.SV_WipeSavegame("current")
    elif sv_init.sv.state == server_h.server_state_t.ss_game:
        _save_level_for_return()

    name = _map_name_as_file(name)
    sv_init.SV_Map(False, name, False, False)
    sv_init.svs.mapcmd = name[:shared.MAX_TOKEN_CHARS - 1]  # the server state for saves

    if not frame.dedicated.value:
        # the autosave
        sv_save.SV_WriteServerFile(True)
        sv_save.SV_CopySaveGame("current", "save0")


def _map() -> None:
    """``map <map>``: goes to a map, with no save of the level being left."""
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("USAGE: map <mapname>\n")
        return

    # a level (not a picture, demo or cinematic) has to exist
    name = cmdparser.Cmd_Argv(1)
    if "." not in name and "$" not in name and name[:1] != "*":
        expanded = f"maps/{name}.bsp"
        if filesystem.FS_LoadFile2(expanded, 0)[0] < 0:
            clientserver.Com_Printf("Can't find %s\n", expanded)
            return

    sv_init.sv.state = server_h.server_state_t.ss_dead  # don't save the level being left
    sv_save.SV_WipeSavegame("current")
    _game_map()


def _list_maps() -> None:
    clientserver.Com_Printf("\n")
    found = filesystem.FS_ListFiles2("maps/*.bsp", 0, 0)
    for path in found.data[:found.num]:
        clientserver.Com_Printf("%s\n", path.rsplit("/", 1)[-1].split(".")[0])


def _kick() -> None:
    """``kick <slot or name>``."""
    if _no_server():
        return
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("Usage: kick <userid>\n")
        return
    if not _set_player():
        return

    cl = sv_init.server.client
    if cl.state == CS.cs_spawned and cl.name:
        sv_send.broadcast_printf(shared.PRINT_HIGH, "%s was kicked\n", cl.name)
    # to the client itself too: once dropped it doesn't get the broadcast
    sv_send.client_printf(cl, shared.PRINT_HIGH, "You were kicked from the game\n")
    sv_main.drop_client(cl)
    cl.lastmessage = sv_init.svs.realtime  # in case there is a funny zombie


STATUS_HEADER = (
    "num score ping name            lastmsg address               qport \n"
    "--- ----- ---- --------------- ------- --------------------- ------\n")


def status_line(slot: int, frags: int, cl: server_h.client_t, idle: int, address: str) -> str:
    """A client's line of ``status``."""
    if cl.state == CS.cs_connected:
        ping = "CNCT"
    elif cl.state == CS.cs_zombie:
        ping = "ZMBI"
    else:
        ping = f"{min(cl.ping, 9999):4}"
    return (f"{slot:2} {frags:5} {ping} {cl.name:<16}{idle:7} {address:<22}"
            f"{cl.netchan.qport:5}\n")


def _status() -> None:
    if not sv_init.svs.clients:
        clientserver.Com_Printf("No server running.\n")
        return

    clientserver.Com_Printf("map              : %s\n", sv_init.sv.name)
    clientserver.Com_Printf(STATUS_HEADER)
    for i, cl in enumerate(sv_init.svs.clients[:sv_init.server.maxclients]):
        if cl.state == CS.cs_free:
            continue
        frags = server_h.CL_EDICT(cl).client.ps.stats[shared.STAT_FRAGS]
        clientserver.Com_Printf("%s", status_line(
            i, frags, cl, sv_init.svs.realtime - cl.lastmessage,
            network.NET_AdrToString(cl.netchan.remote_address)))
    clientserver.Com_Printf("\n")


def _console_say() -> None:
    """``say`` on a dedicated server's console."""
    if cmdparser.Cmd_Argc() < 2:
        return
    if _no_server():
        return

    text = cmdparser.Cmd_Args()
    if text[:1] == '"':
        text = text[1:-1]
    text = f"console: {text}"[:SAY_SIZE - 1]

    for client in sv_init.svs.clients[:sv_init.server.maxclients]:
        if client.state == CS.cs_spawned:
            sv_send.client_printf(client, shared.PRINT_CHAT, "%s\n", text)


def _heartbeat() -> None:
    sv_init.svs.last_heartbeat = -9999999


def _serverinfo() -> None:
    clientserver.Com_Printf("Server info settings:\n")
    argproc.Info_Print(cvar.Cvar_Serverinfo())


def _dump_user() -> None:
    """``dumpuser <slot or name>``: a client's info strings."""
    if _no_server():
        return
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("Usage: dumpuser <userid>\n")
        return
    if not _set_player():
        return
    clientserver.Com_Printf("userinfo\n")
    clientserver.Com_Printf("--------\n")
    argproc.Info_Print(sv_init.server.client.userinfo)


def _signon_message() -> common_h.sizebuf_t | None:
    """A server demo's first message: the serverdata and the configstrings."""
    sv = sv_init.sv
    buf = common_h.sizebuf_t()
    szone.SZ_Init(buf, SIGNON_SIZE)

    movemsg.MSG_WriteByte(buf, SVC.svc_serverdata.value)
    movemsg.MSG_WriteLong(buf, common_h.PROTOCOL_VERSION)
    movemsg.MSG_WriteLong(buf, sv_init.svs.spawncount)
    movemsg.MSG_WriteByte(buf, 2)  # 2: a server demo (demos are always attract loops)
    movemsg.MSG_WriteString(buf, cvar.Cvar_VariableString("gamedir"))
    movemsg.MSG_WriteShort(buf, -1)
    movemsg.MSG_WriteString(buf, sv.configstrings[shared.CS_NAME])  # the full level name

    for i, cs in enumerate(sv.configstrings[:shared.MAX_CONFIGSTRINGS]):
        if cs:
            movemsg.MSG_WriteByte(buf, SVC.svc_configstring.value)
            movemsg.MSG_WriteConfigString(buf, i, cs)
            if buf.cursize + 67 >= buf.maxsize:
                clientserver.Com_Printf("not enough buffer space available.\n")
                return None
    return buf


def _server_record() -> None:
    """``serverrecord <name>``: records every entity and message, without player info.

    For merging into demos.
    """
    svs = sv_init.svs
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("serverrecord <demoname>\n")
        return
    if svs.demofile:
        clientserver.Com_Printf("Already recording.\n")
        return
    if sv_init.sv.state != server_h.server_state_t.ss_game:
        clientserver.Com_Printf("You must be in a level to record.\n")
        return
    name = cmdparser.Cmd_Argv(1)
    if ".." in name or "/" in name or "\\" in name:
        clientserver.Com_Printf("Illegal filename.\n")
        return

    path = f"{filesystem.FS_Gamedir()}/demos/{name}.dm2"
    clientserver.Com_Printf("recording to %s.\n", path)
    filesystem.FS_CreatePath(path)
    svs.demofile = filesystem.Q_fopen(path, "wb")
    if not svs.demofile:
        clientserver.Com_Printf("ERROR: couldn't open.\n")
        return

    szone.SZ_Init(svs.demo_multicast, DEMO_MULTICAST_SIZE)  # catches every multicast

    buf = _signon_message()
    if buf is None:
        svs.demofile.close()
        svs.demofile = None
        return

    clientserver.Com_DPrintf("signon message length: %i\n", buf.cursize)
    svs.demofile.write(struct.pack("<i", buf.cursize))
    svs.demofile.write(bytes(buf.data[:buf.cursize]))
    # then one message a frame (sv_entities.record_demo_message)


def _server_stop() -> None:
    if not sv_init.svs.demofile:
        clientserver.Com_Printf("Not doing a serverrecord.\n")
        return
    sv_init.svs.demofile.close()
    sv_init.svs.demofile = None
    clientserver.Com_Printf("Recording completed.\n")


def _kill_server() -> None:
    """Drops everyone, perhaps for a new game."""
    if not sv_init.svs.initialized:
        return
    sv_main.SV_Shutdown("Server was killed.\n", False)
    network.NET_Config(False)  # closes the sockets


def _server_command() -> None:
    """``sv ...``: a command for the game."""
    if not sv_game.ge:
        clientserver.Com_Printf("No game loaded.\n")
        return
    sv_game.ge.ServerCommand()


GAMEMODES = {  # (deathmatch, coop, singleplayer)
    "dm": ("1", "0", "0"),
    "coop": ("0", "1", "0"),
    "sp": ("0", "0", "1"),
}


def _gamemode() -> None:
    """``gamemode dm|coop|sp``, or ``gamemode ?`` for the current one."""
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("gamemode dm, coop or sp\ngamemode ? to print current info\n")
        return

    arg = cmdparser.Cmd_Argv(1)
    if arg[:1] == "?":
        modes = [mode for mode, name in (("dm", "deathmatch"), ("coop", "coop"),
                                         ("sp", "singleplayer"))
                 if cvar.Cvar_VariableValue(name)]
        clientserver.Com_Printf("%s\n", " ".join(modes) + " " if modes else "none")
        return

    if arg not in GAMEMODES:
        clientserver.Com_Printf("unknown gamemode: '%s'\nspecify dm, coop or sp\n", arg)
        return
    for name, value in zip(("deathmatch", "coop", "singleplayer"), GAMEMODES[arg], strict=True):
        cvar.Cvar_Set(name, value)


def SV_InitOperatorCommands() -> None:  # noqa: N802
    commands = [
        ("gamemode", _gamemode),
        ("heartbeat", _heartbeat),
        ("kick", _kick),
        ("status", _status),
        ("serverinfo", _serverinfo),
        ("dumpuser", _dump_user),
        ("map", _map),
        ("listmaps", _list_maps),
        ("demomap", _demo_map),
        ("gamemap", _game_map),
        ("setmaster", _set_master),
    ]
    if frame.dedicated.value:
        commands.append(("say", _console_say))
    commands += [
        ("serverrecord", _server_record),
        ("serverstop", _server_stop),
        ("save", sv_save.SV_Savegame_f),
        ("load", sv_save.SV_Loadgame_f),
        ("killserver", _kill_server),
        ("sv", _server_command),
    ]
    for name, function in commands:
        cmdparser.Cmd_AddCommand(name, function)
