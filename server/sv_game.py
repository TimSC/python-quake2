"""The server's side of the game interface (Yamagi's sv_game.c).

``init_game`` builds the table of server functions the game calls (its
``gi``: prints, configstrings, the multicast writers, linking and traces,
sounds, cvars and commands), loads the game with it, and keeps the game's
exports as ``server.game``. The table's field names are the game's
interface and keep their C names.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

from backends.unix import system
from client import cl_screen
from common import clientserver, cmdparser, collision, cvar, movemsg, pmove, szone, zone
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from game.header import game as game_h
from server import context, sv_init, sv_send, sv_world
from server.header import server as server_h

USHRT_MAX = 65535


def _client_number(ent) -> int | None:
    """The client slot + 1 of a player's edict, or None for other edicts."""
    n = server_h.NUM_FOR_EDICT(ent)
    return n if 1 <= n <= context.server.maxclients else None


def _format(fmt: str, args: tuple) -> str:
    return (fmt % args) if args else fmt


def unicast(ent, reliable: bool) -> None:
    """Sends the multicast buffer to one client (gi.unicast)."""
    if not ent:
        return
    n = _client_number(ent)
    if n is None:
        return
    client = sv_init.svs.clients[n - 1]
    multicast = sv_init.sv.multicast
    szone.SZ_Write(client.netchan.message if reliable else client.datagram,
                   bytes(multicast.data[:multicast.cursize]))
    szone.SZ_Clear(multicast)


def dprintf(fmt: str, *args) -> None:
    """A debug print to the server console (gi.dprintf)."""
    clientserver.Com_Printf(_format(fmt, args))


def cprintf(ent, level: int, fmt: str, *args) -> None:
    """A print to one client, or the console for no edict (gi.cprintf)."""
    n = None
    if ent:
        n = _client_number(ent)
        if n is None:
            clientserver.Com_Error(common_h.ERR_DROP, "cprintf to a non-client")
    msg = _format(fmt, args)
    if ent:
        sv_send.client_printf(sv_init.svs.clients[n - 1], level, msg)
    else:
        clientserver.Com_Printf(msg)


def centerprintf(ent, fmt: str, *args) -> None:
    """A centre-screen print to one client (gi.centerprintf)."""
    if _client_number(ent) is None:
        return
    movemsg.MSG_WriteByte(sv_init.sv.multicast, common_h.svc_ops_e.svc_centerprint.value)
    movemsg.MSG_WriteString(sv_init.sv.multicast, _format(fmt, args))
    unicast(ent, True)


def error(fmt: str, *args) -> None:
    """Ends the game with a game error (gi.error)."""
    clientserver.Com_Error(common_h.ERR_DROP, "Game Error: %s", _format(fmt, args))


def setmodel(ent, name: str) -> None:
    """Sets an entity's model; a brush model ("*n") also sets its size and links it."""
    if not name:
        clientserver.Com_Error(common_h.ERR_DROP, "PF_setmodel: NULL")

    ent.s.modelindex = sv_init.model_index(name)
    if name[0] == "*":
        model = collision.CM_InlineModel(name)
        shared.VectorCopy(model.mins, ent.mins)
        shared.VectorCopy(model.maxs, ent.maxs)
        sv_world.link_edict(ent)


def configstring(index: int, val: str) -> None:
    """Sets a configstring, and sends it to everyone outside of loading."""
    if index < 0 or index >= shared.MAX_CONFIGSTRINGS:
        clientserver.Com_Printf("%s: bad index %i\n", "PF_Configstring", index)
        return
    val = val or ""

    # the statusbar program covers several configstrings
    if shared.CS_STATUSBAR <= index < shared.CS_STATUSBAR_END:
        space = shared.CS_STATUSBAR_SPACE(index)
        if len(val) >= space:
            clientserver.Com_Printf("%s: statusbar code too big: %d > %d\n",
                                    "PF_Configstring", len(val), space - 1)
            return
    elif len(val) >= shared.MAX_QPATH:
        clientserver.Com_Printf("%s; value too big: %d > %d\n",
                                "PF_Configstring", len(val), shared.MAX_QPATH - 1)
        return

    sv_init.sv.configstrings[index] = val

    if sv_init.sv.state != server_h.server_state_t.ss_loading:
        multicast = sv_init.sv.multicast
        szone.SZ_Clear(multicast)
        movemsg.MSG_WriteChar(multicast, common_h.svc_ops_e.svc_configstring.value)
        movemsg.MSG_WriteConfigString(multicast, index, val)
        sv_send.multicast(shared_c.vec3_origin, shared.multicast_t.MULTICAST_ALL_R)


def _multicast_writer(write):
    """A gi.Write* function: writes its value into the multicast buffer."""
    return lambda value: write(sv_init.sv.multicast, value)


def _in_set(p1, p2, cluster_set) -> bool:
    """Whether p2 is in p1's PVS or PHS, and a door doesn't close it off."""
    leafnum = collision.CM_PointLeafnum(p1)
    area1 = collision.CM_LeafArea(leafnum)
    mask = cluster_set(collision.CM_LeafCluster(leafnum))

    leafnum = collision.CM_PointLeafnum(p2)
    cluster = collision.CM_LeafCluster(leafnum)
    area2 = collision.CM_LeafArea(leafnum)
    if cluster < 0 or not (mask[cluster >> 3] & (1 << (cluster & 7))):
        return False
    return bool(collision.CM_AreasConnected(area1, area2))


def in_pvs(p1, p2) -> bool:
    """Whether p2 may be visible from p1 (gi.inPVS)."""
    return _in_set(p1, p2, collision.CM_ClusterPVS)


def in_phs(p1, p2) -> bool:
    """Whether p2 may be heard from p1: at most one bounce away (gi.inPHS)."""
    return _in_set(p1, p2, collision.CM_ClusterPHS)


def start_sound(entity, channel: int, sound_num: int, volume: float, attenuation: float,
                timeofs: float) -> None:
    """A sound from an entity (gi.sound)."""
    if entity:
        sv_send.start_sound(None, entity, channel, sound_num, volume, attenuation, timeofs)


def tag_malloc(size: int, tag: int):
    if size < 0:
        clientserver.Com_Error(shared.ERR_FATAL, "%s: size < 0: %i\n", "GI_TagMalloc", size)
        return None
    if tag > USHRT_MAX or tag < 0:
        clientserver.Com_Printf("%s: tag outside [0, 65535]: %i\n", "GI_TagMalloc", tag)
        tag = 0
    return zone.Z_TagMalloc(size, tag)


def free_tags(tag: int) -> None:
    if tag > USHRT_MAX or tag <= 0:
        clientserver.Com_Printf("%s: tag outside [1, 65535]: %i\n", "GI_FreeTags", tag)
        return
    zone.Z_FreeTags(tag)


def shutdown_game() -> None:
    """Shuts the game down (the server stops, or changes game directory)."""
    game = context.server.game
    if game is None:
        return
    game.Shutdown()
    system.Sys_UnloadGame()
    context.server.game = None


def _game_imports() -> game_h.game_import_t:
    gi = game_h.game_import_t()
    write = movemsg
    for name, function in {
        "multicast": sv_send.multicast,
        "unicast": unicast,
        "bprintf": sv_send.broadcast_printf,
        "dprintf": dprintf,
        "cprintf": cprintf,
        "centerprintf": centerprintf,
        "error": error,
        "linkentity": sv_world.link_edict,
        "unlinkentity": sv_world.unlink_edict,
        "BoxEdicts": sv_world.area_edicts,
        "trace": sv_world.trace,
        "pointcontents": sv_world.point_contents,
        "setmodel": setmodel,
        "inPVS": in_pvs,
        "inPHS": in_phs,
        "Pmove": pmove.Pmove,
        "modelindex": sv_init.model_index,
        "soundindex": sv_init.sound_index,
        "imageindex": sv_init.image_index,
        "configstring": configstring,
        "sound": start_sound,
        "positioned_sound": sv_send.start_sound,
        "WriteChar": _multicast_writer(write.MSG_WriteChar),
        "WriteByte": _multicast_writer(write.MSG_WriteByte),
        "WriteShort": _multicast_writer(write.MSG_WriteShort),
        "WriteLong": _multicast_writer(write.MSG_WriteLong),
        "WriteFloat": _multicast_writer(write.MSG_WriteFloat),
        "WriteString": _multicast_writer(write.MSG_WriteString),
        "WritePosition": _multicast_writer(write.MSG_WritePos),
        "WriteDir": _multicast_writer(write.MSG_WriteDir),
        "WriteAngle": _multicast_writer(write.MSG_WriteAngle),
        "TagMalloc": tag_malloc,
        "TagFree": zone.Z_Free,
        "FreeTags": free_tags,
        "cvar": cvar.Cvar_Get,
        "cvar_set": cvar.Cvar_Set,
        "cvar_forceset": cvar.Cvar_ForceSet,
        "argc": cmdparser.Cmd_Argc,
        "argv": cmdparser.Cmd_Argv,
        "args": cmdparser.Cmd_Args,
        "AddCommandString": cmdparser.Cbuf_AddText,
        "DebugGraph": cl_screen.SCR_DebugGraph,
        "SetAreaPortalState": collision.CM_SetAreaPortalState,
        "AreasConnected": collision.CM_AreasConnected,
    }.items():
        setattr(gi, name, function)
    return gi


def init_game() -> None:
    """Loads the game for a new map (unloading the one before)."""
    if context.server.game is not None:
        shutdown_game()

    clientserver.Com_Printf("-------- game initialization -------\n")

    game = context.server.game = system.Sys_GetGameAPI(_game_imports())
    if game.apiversion != game_h.GAME_API_VERSION:
        clientserver.Com_Error(common_h.ERR_DROP, "game is version %d, not %d",
                               game.apiversion, game_h.GAME_API_VERSION)
    game.Init()

    clientserver.Com_Printf("------------------------------------\n\n")
