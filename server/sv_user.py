"""What clients send the server (Yamagi's sv_user.c).

``execute_client_message`` reads a client's packet: user info, its moves
(checksummed, and replayed for dropped packets) and string commands. The
string commands the server knows are the ``USER_COMMANDS``: the sign-on
sequence (``new``, ``configstrings``, ``baselines``, ``begin``),
downloads, ``nextserver``, ``disconnect`` and ``info``; the game gets the
others.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

from collections.abc import Callable

from common import (
    argproc,
    clientserver,
    cmdparser,
    crc,
    cvar,
    entity_delta,
    filesystem,
    movemsg,
    netchan,
    szone,
    usercmd_delta,
)
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from server import sv_game, sv_init, sv_main
from server.header import server as server_h

CS = server_h.client_state_t
SS = server_h.server_state_t
SVC = common_h.svc_ops_e
CLC = common_h.clc_ops_e

MAX_STRINGCMDS = 8  # string commands a packet may run

CMD_MARGIN = 40  # message space kept for a command
SAFE_MARGIN = 24  # message space kept for more data added elsewhere

DOWNLOAD_CHUNK = 1024


def _stufftext(msg: common_h.sizebuf_t, text: str) -> None:
    movemsg.MSG_WriteByte(msg, SVC.svc_stufftext.value)
    movemsg.MSG_WriteString(msg, text)


def _arg_int(i: int) -> int:
    return shared_c.atoi(cmdparser.Cmd_Argv(i))


def _same_level() -> bool:
    """Whether the command's spawn count is this level's (not one changed while connecting)."""
    return cmdparser.Cmd_Argc() > 1 and _arg_int(1) == sv_init.svs.spawncount


def _start_arg() -> int:
    return max(_arg_int(2), 0) if cmdparser.Cmd_Argc() > 2 else 0


def _begin_demo_server() -> None:
    name = f"demos/{sv_init.sv.name}"
    _, sv_init.sv.demofile = filesystem.FS_FOpenFile(name, False)
    if not sv_init.sv.demofile:
        clientserver.Com_Error(shared.ERR_DROP, "Couldn't open %s\n", name)


def _new(cl: server_h.client_t) -> None:
    """The server's first message to a client, on connecting and on each level."""
    clientserver.Com_DPrintf("New() from %s\n", cl.name)
    if cl.state != CS.cs_connected:
        clientserver.Com_Printf("New not valid -- already spawned\n")
        return

    sv = sv_init.sv
    if sv.state == SS.ss_demo:
        _begin_demo_server()  # demo servers just send the file
        return

    # the serverdata, for every kind of server: the protocol and the game directory
    msg = cl.netchan.message
    movemsg.MSG_WriteByte(msg, SVC.svc_serverdata.value)
    movemsg.MSG_WriteLong(msg, common_h.PROTOCOL_VERSION)
    movemsg.MSG_WriteLong(msg, sv_init.svs.spawncount)
    movemsg.MSG_WriteByte(msg, 1 if sv.attractloop else 0)
    movemsg.MSG_WriteString(msg, cvar.Cvar_VariableString("gamedir"))

    playernum = -1 if sv.state in (SS.ss_cinematic, SS.ss_pic) else cl.slot
    movemsg.MSG_WriteShort(msg, playernum)
    movemsg.MSG_WriteString(msg, sv.configstrings[shared.CS_NAME])  # the full level name

    if sv.state == SS.ss_game:
        server_h.CLNUM_EDICT(playernum).s.number = playernum + 1
        cl.lastcmd = shared.usercmd_t()
        _stufftext(msg, f"cmd configstrings {sv_init.svs.spawncount} 0\n")


def _enough_space(msg: common_h.sizebuf_t, size: int, optimized: int) -> bool:
    """Whether size more bytes fit in a sign-on message."""
    if not optimized and msg.cursize >= common_h.MAX_MSGLEN // 2:
        return False
    return msg.cursize + size <= common_h.MAX_MSGLEN - (CMD_MARGIN + SAFE_MARGIN)


def _print_overflowed_configstrings() -> None:
    overflow = sv_init.sv.configstrings_overflow
    if not overflow:
        return
    clientserver.Com_Printf("Failed to load %i resources: configstrings overflowed\n",
                            len(overflow))
    for name in overflow:
        clientserver.Com_Printf("  %s\n", name)


def _index_skips(start: int, end: int) -> int:
    """The configstrings after start that its text runs into.

    A configstring that fills its MAX_QPATH buffer runs into the next ones,
    as the statusbar program does. Here the whole text is in the first
    index, and the ones its length covers are skipped.
    """
    length = len(sv_init.sv.configstrings[start])
    i = start
    while i < end - 1 and length >= shared.MAX_QPATH * (i - start + 1):
        i += 1
    return i - start


def _next_configstring(i: int, opt: int) -> int:
    # the statusbar program goes as one string
    if opt & server_h.OPTIMIZE_HUDSEND and shared.CS_STATUSBAR <= i < shared.CS_STATUSBAR_END:
        return i + 1 + _index_skips(i, shared.CS_STATUSBAR_END)
    return i + 1


def _add_baselines(cl: server_h.client_t, start: int, allow_zero: bool) -> None:
    """Sends the entity baselines from start that fit, and the next command."""
    sv = sv_init.sv
    msg = cl.netchan.message
    optimized = sv_main.optimizations() & server_h.OPTIMIZE_MSGUTIL
    start = max(start, 0)

    i = start
    while i < sv.numbaselines:
        base = sv.baselines[i]
        if base.modelindex or base.sound or base.effects:
            if not _enough_space(msg, entity_delta.delta_size(None, base, True, True), optimized):
                break
            movemsg.MSG_WriteByte(msg, SVC.svc_spawnbaseline.value)
            entity_delta.write_delta(None, base, msg, True, True)
        i += 1

    if not allow_zero and i == start and i < sv.numbaselines:
        clientserver.Com_Printf("%s: skipping index %i: too big to send\n", "SV_AddBaselines", i)
        i += 1

    if i >= sv.numbaselines:
        _stufftext(msg, f"precache {sv_init.svs.spawncount}\n")
    else:
        _stufftext(msg, f"cmd baselines {sv_init.svs.spawncount} {i}\n")


def _configstrings(cl: server_h.client_t) -> None:
    """Sends the configstrings from the given index that fit, and the next command."""
    start = _start_arg()
    clientserver.Com_DPrintf("Configstrings(%i) from %s\n", start, cl.name)
    if cl.state != CS.cs_connected:
        clientserver.Com_Printf("configstrings not valid -- already spawned\n")
        return
    if not _same_level():
        clientserver.Com_Printf("SV_Configstrings_f from different level\n")
        _new(cl)
        return

    msg = cl.netchan.message
    opt = sv_main.optimizations()
    i = start
    while i < shared.MAX_CONFIGSTRINGS:
        cs = sv_init.sv.configstrings[i]
        if cs != "":
            if not _enough_space(msg, movemsg.MSG_ConfigString_Size(cs),
                                 opt & server_h.OPTIMIZE_MSGUTIL):
                break
            movemsg.MSG_WriteByte(msg, SVC.svc_configstring.value)
            movemsg.MSG_WriteConfigString(msg, i, cs)
        i = _next_configstring(i, opt)

    if i == start and i < shared.MAX_CONFIGSTRINGS:
        clientserver.Com_Printf("%s: skipping index %i: too big to send\n",
                                "SV_Configstrings_f", i)
        i = _next_configstring(i, opt)

    if i < shared.MAX_CONFIGSTRINGS:
        _stufftext(msg, f"cmd configstrings {sv_init.svs.spawncount} {i}\n")
        return

    _print_overflowed_configstrings()
    if opt & server_h.OPTIMIZE_CSBASE:
        _add_baselines(cl, 0, True)  # the rest of the packet for baselines
    else:
        _stufftext(msg, f"cmd baselines {sv_init.svs.spawncount} 0\n")


def _baselines(cl: server_h.client_t) -> None:
    start = _start_arg()
    clientserver.Com_DPrintf("Baselines(%i) from %s\n", start, cl.name)
    if cl.state != CS.cs_connected:
        clientserver.Com_Printf("baselines not valid -- already spawned\n")
        return
    if not _same_level():
        clientserver.Com_Printf("SV_Baselines_f from different level\n")
        _new(cl)
        return
    _add_baselines(cl, start, False)


def _begin(cl: server_h.client_t) -> None:
    """The client has everything: it enters the game."""
    clientserver.Com_DPrintf("Begin() from %s\n", cl.name)
    if _arg_int(1) != sv_init.svs.spawncount:
        clientserver.Com_Printf("SV_Begin_f from different level\n")
        _new(cl)
        return

    cl.state = CS.cs_spawned
    sv_game.ge.ClientBegin(sv_init.server.player)
    cmdparser.Cbuf_InsertFromDefer()


def _write_download_refusal(msg: common_h.sizebuf_t) -> None:
    movemsg.MSG_WriteByte(msg, SVC.svc_download.value)
    movemsg.MSG_WriteShort(msg, -1)
    movemsg.MSG_WriteByte(msg, 0)


def _next_download(cl: server_h.client_t) -> None:
    """Sends the next chunk of the client's download."""
    if not cl.download:
        return

    n = min(cl.downloadsize - cl.downloadcount, DOWNLOAD_CHUNK)
    msg = cl.netchan.message
    movemsg.MSG_WriteByte(msg, SVC.svc_download.value)
    movemsg.MSG_WriteShort(msg, n)

    cl.downloadcount += n
    movemsg.MSG_WriteByte(msg, cl.downloadcount * 100 // (cl.downloadsize or 1))  # percent
    szone.SZ_Write(msg, cl.download[cl.downloadcount - n:cl.downloadcount])

    if cl.downloadcount == cl.downloadsize:
        filesystem.FS_FreeFile(cl.download)
        cl.download = None


def download_allowed(name: str) -> bool:
    """Whether the allow_download cvars let a client download a file (zoid's rules)."""
    if ".." in name or "\\" in name or ":" in name or not sv_init.server.cvars.allow_download.value:
        return False
    if name[:1] in (".", "/"):
        return False  # no leading dot, and it must be relative
    for prefix, allowed in (("players/", sv_init.server.cvars.allow_download_players),
                            ("models/", sv_init.server.cvars.allow_download_models),
                            ("sound/", sv_init.server.cvars.allow_download_sounds),
                            ("maps/", sv_init.server.cvars.allow_download_maps)):
        if name.startswith(prefix) and not allowed.value:
            return False
    return "/" in name  # it must be in a directory


def _begin_download(cl: server_h.client_t) -> None:
    """Starts a download (from an offset, to resume one)."""
    name = cmdparser.Cmd_Argv(1)
    offset = max(_arg_int(2), 0) if cmdparser.Cmd_Argc() > 2 else 0

    if not download_allowed(name):
        _write_download_refusal(cl.netchan.message)
        return

    if cl.download:
        filesystem.FS_FreeFile(cl.download)

    cl.downloadsize, cl.download = filesystem.FS_LoadFile(name)
    cl.downloadcount = min(offset, cl.downloadsize)

    # maps from the game's own paks can't be downloaded
    if not cl.download or (name.startswith("maps/") and filesystem.file_from_protected_pak):
        clientserver.Com_DPrintf("Couldn't download %s to %s\n", name, cl.name)
        if cl.download:
            filesystem.FS_FreeFile(cl.download)
            cl.download = None
        _write_download_refusal(cl.netchan.message)
        return

    _next_download(cl)
    clientserver.Com_DPrintf("Downloading %s to %s\n", name, cl.name)


def _disconnect(cl: server_h.client_t) -> None:
    sv_main.drop_client(cl)


def _show_serverinfo(cl: server_h.client_t) -> None:
    argproc.Info_Print(cvar.Cvar_Serverinfo())


def SV_Nextserver() -> None:  # noqa: N802
    """Goes on to the nextserver cvar's command (after a cinematic, demo or end picture)."""
    sv = sv_init.sv
    if sv.state == SS.ss_game or (sv.state == SS.ss_pic and not cvar.Cvar_VariableValue("coop")):
        return  # not while playing a normal game

    sv_init.svs.spawncount += 1  # so another doesn't sneak in
    v = cvar.Cvar_VariableString("nextserver")
    cmdparser.Cbuf_AddText(f"{v}\n" if v else "killserver\n")
    cvar.Cvar_Set("nextserver", "")


def _nextserver(cl: server_h.client_t) -> None:
    """A client finished or skipped a cinematic."""
    if _arg_int(1) != sv_init.svs.spawncount:
        clientserver.Com_DPrintf("Nextserver() from wrong level, from %s\n", cl.name)
        return  # left over from the last server
    clientserver.Com_DPrintf("Nextserver() from %s\n", cl.name)
    SV_Nextserver()


USER_COMMANDS: dict[str, Callable[[server_h.client_t], None]] = {
    # sent by the client itself
    "new": _new,
    "configstrings": _configstrings,
    "baselines": _baselines,
    "begin": _begin,
    "nextserver": _nextserver,
    "disconnect": _disconnect,
    # typed at the client's console
    "info": _show_serverinfo,
    "download": _begin_download,
    "nextdl": _next_download,
}


def execute_user_command(cl: server_h.client_t, text: str) -> None:
    """Runs a client's string command, or hands it to the game."""
    # no $cvar expansion: clients mustn't read the server's cvars
    cmdparser.Cmd_TokenizeString(text, False)
    sv_init.server.set_client(cl)

    handler = USER_COMMANDS.get(cmdparser.Cmd_Argv(0))
    if handler is not None:
        handler(cl)
    elif sv_init.sv.state == SS.ss_game:
        sv_game.ge.ClientCommand(sv_init.server.player)


def _client_think(cl: server_h.client_t, cmd: shared.usercmd_t) -> None:
    cl.commandMsec -= cmd.msec
    if cl.commandMsec < 0 and sv_init.server.cvars.enforcetime.value:
        clientserver.Com_DPrintf("commandMsec underflow from %s\n", cl.name)
        return
    sv_game.ge.ClientThink(server_h.CL_EDICT(cl), cmd)


def _read_move(cl: server_h.client_t, msg: common_h.sizebuf_t) -> bool:
    """Reads a move and runs it (and the ones lost with dropped packets).

    False when the rest of the packet is to be ignored (a bad checksum).
    """
    checksum_index = msg.readcount
    checksum = movemsg.MSG_ReadByte(msg)
    lastframe = movemsg.MSG_ReadSLong(msg)  # signed: -1 is no frame yet

    if lastframe != cl.lastframe:
        cl.lastframe = lastframe
        if cl.lastframe > 0:
            cl.frame_latency[cl.lastframe & (server_h.LATENCY_COUNTS - 1)] = \
                sv_init.svs.realtime - cl.frames[cl.lastframe & common_h.UPDATE_MASK].senttime

    oldest = shared.usercmd_t()
    oldcmd = shared.usercmd_t()
    newcmd = shared.usercmd_t()
    usercmd_delta.read_delta(msg, shared.usercmd_t(), oldest)
    usercmd_delta.read_delta(msg, oldest, oldcmd)
    usercmd_delta.read_delta(msg, oldcmd, newcmd)

    if cl.state != CS.cs_spawned:
        cl.lastframe = -1
        return True

    if msg.readcount > msg.cursize:
        # cut short by the end of the packet (the C checksums what lies
        # past it in its buffer, which fails)
        clientserver.Com_DPrintf("Failed command checksum for %s (truncated move)\n", cl.name)
        return False

    calculated = crc.COM_BlockSequenceCRCByte(msg.data, checksum_index + 1,
                                              msg.readcount - checksum_index - 1,
                                              cl.netchan.incoming_sequence)[0]
    if calculated != checksum:
        clientserver.Com_DPrintf("Failed command checksum for %s (%d != %d)/%d\n",
                                 cl.name, calculated, checksum, cl.netchan.incoming_sequence)
        return False

    if not sv_init.server.cvars.paused.value:
        dropped = cl.netchan.dropped
        if dropped < 20:
            # replay what the dropped packets carried
            for _ in range(dropped - 2):
                _client_think(cl, cl.lastcmd)
            if dropped > 1:
                _client_think(cl, oldest)
            if dropped > 0:
                _client_think(cl, oldcmd)
        _client_think(cl, newcmd)

    cl.lastcmd = newcmd
    return True


def execute_client_message(cl: server_h.client_t) -> None:
    """Reads the client's packet in net_message."""
    sv_init.server.set_client(cl)
    msg = netchan.net_message

    move_issued = False  # one move a packet
    string_commands = 0

    while True:
        if msg.readcount > msg.cursize:
            clientserver.Com_Printf("SV_ReadClientMessage: badread\n")
            sv_main.drop_client(cl)
            return

        c = movemsg.MSG_ReadByte(msg)
        if c == -1:
            break

        if c == CLC.clc_nop.value:
            pass

        elif c == CLC.clc_userinfo.value:
            cl.userinfo = movemsg.MSG_ReadString(msg)[:shared.MAX_INFO_STRING - 1]
            sv_main.userinfo_changed(cl)

        elif c == CLC.clc_move.value:
            if move_issued:
                return  # someone is trying to cheat
            move_issued = True
            if not _read_move(cl, msg):
                return

        elif c == CLC.clc_stringcmd.value:
            text = movemsg.MSG_ReadString(msg)
            # against floods of string commands
            string_commands += 1
            if string_commands < MAX_STRINGCMDS:
                execute_user_command(cl, text)
            if cl.state == CS.cs_zombie:
                return  # it disconnected

        else:
            clientserver.Com_Printf("SV_ReadClientMessage: unknown command char\n")
            sv_main.drop_client(cl)
            return
