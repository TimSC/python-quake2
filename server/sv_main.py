"""The server's frame, its clients' life cycle and the masters (Yamagi's sv_main.c).

The engine calls ``SV_Init`` once, ``SV_Frame`` every frame and
``SV_Shutdown`` when a game ends. A frame reads the clients' packets,
runs the game every 100 ms and sends the clients their frames.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import struct
import traceback

from backends.unix import network, system
from common import clientserver, cvar, errors, filesystem, frame, movemsg, netchan, szone
from common.header import common as common_h
from common.header import shared
from common.shared import rand
from common.shared import shared as shared_c
from server import context, sv_cmd, sv_conless, sv_entities, sv_game, sv_init, sv_send, sv_user
from server.header import server as server_h

CS = server_h.client_state_t
SVC = common_h.svc_ops_e

HEARTBEAT_SECONDS = 300
STATUS_SIZE = common_h.MAX_MSGLEN - 16  # the C's static char status[MAX_MSGLEN - 16]
NAME_SIZE = 32


def _clients() -> list[server_h.client_t]:
    return sv_init.svs.clients[:context.server.maxclients]


def drop_client(drop: server_h.client_t) -> None:
    """A client leaves the server (not when the whole server stops).

    It stays a zombie for a few seconds, so its last reliable message can
    still be sent again.
    """
    movemsg.MSG_WriteByte(drop.netchan.message, SVC.svc_disconnect.value)

    if drop.state == CS.cs_spawned:
        sv_game.ge.ClientDisconnect(server_h.CL_EDICT(drop))  # removes the body, among others

    if drop.download:
        filesystem.FS_FreeFile(drop.download)
        drop.download = None

    drop.state = CS.cs_zombie
    drop.name = ""


def status_string() -> str:
    """The server info and the players, for heartbeats and ``status`` replies."""
    status = (cvar.Cvar_Serverinfo() + "\n")[:STATUS_SIZE - 1]
    for cl in _clients():
        if cl.state in (CS.cs_connected, CS.cs_spawned):
            frags = server_h.CL_EDICT(cl).client.ps.stats[shared.STAT_FRAGS]
            player = f'{frags} {cl.ping} "{cl.name}"\n'
            if len(status) + len(player) >= STATUS_SIZE:
                break  # no room for more
            status += player
    return status


def accept_client(newcl: server_h.client_t, adr, qport: int, userinfo: str,
                  challenge: int) -> None:
    """Sets up a connecting client in its slot, unless the game refuses it.

    The one place a client is set up.
    """
    cvars = context.server.cvars
    context.server.client = newcl
    ent = server_h.CL_EDICT(newcl)
    newcl.challenge = challenge  # kept for the checksums

    # the game may refuse the client or change its userinfo
    if not sv_game.ge.ClientConnect(ent, userinfo):
        reason = shared_c.Info_ValueForKey(userinfo, "rejmsg")
        refusal = f"print\n{reason}\nConnection refused.\n" if reason else \
            "print\nConnection refused.\n"
        netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr, refusal)
        clientserver.Com_DPrintf("Game rejected a connection.\n")
        return

    newcl.userinfo = userinfo[:shared.MAX_INFO_STRING - 1]
    userinfo_changed(newcl)

    connect = "client_connect"
    if cvars.downloadserver.string:
        connect += f" dlserver={cvars.downloadserver.string}"
    netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr, connect)

    netchan.Netchan_Setup(common_h.netsrc_t.NS_SERVER, newcl.netchan, adr, qport)
    newcl.state = CS.cs_connected

    szone.SZ_Init(newcl.datagram, common_h.MAX_MSGLEN)
    newcl.datagram.allowoverflow = True
    newcl.lastmessage = sv_init.svs.realtime  # no timeout yet
    newcl.lastconnect = sv_init.svs.realtime


def _calc_pings() -> None:
    """Each client's ping: the average latency of its acknowledged frames."""
    for cl in _clients():
        if cl.state != CS.cs_spawned:
            continue
        latencies = [t for t in cl.frame_latency[:server_h.LATENCY_COUNTS] if t > 0]
        cl.ping = sum(latencies) // len(latencies) if latencies else 0
        server_h.CL_EDICT(cl).client.ping = cl.ping  # for the game


def _give_msec() -> None:
    """Every 16 frames, the time the clients' moves may take (more is cheating)."""
    if sv_init.sv.framenum & 15:
        return
    for cl in _clients():
        if cl.state != CS.cs_free:
            cl.commandMsec = 1800  # 1600 and some slop


def _untrusted_data_error(err: Exception, what: str) -> None:
    """Reports an exception while handling a packet (not in the C).

    Packets are untrusted data, and an exception a bad one causes (where
    the C would read garbage or drop the client) would otherwise end the
    whole server: a connectionless packet is ignored instead, and a
    client's message drops that client. The traceback shows with
    developer 1.
    """
    clientserver.Com_Printf("{}: {} in {} from {}, ignored\n".format(
        "SV_ReadPackets", type(err).__name__, what, network.NET_AdrToString(netchan.net_from)))
    clientserver.Com_DPrintf("{}".format("".join(traceback.format_exception(err))))


def _client_for_packet(qport: int) -> server_h.client_t | None:
    for cl in _clients():
        if (cl.state != CS.cs_free
                and network.NET_CompareBaseAdr(netchan.net_from, cl.netchan.remote_address)
                and cl.netchan.qport == qport):
            return cl
    return None


def _read_packets() -> None:
    msg = netchan.net_message
    while True:
        rx, netchan.net_from = network.NET_GetPacket(common_h.netsrc_t.NS_SERVER,
                                                     netchan.net_from, msg)
        if not rx:
            break

        # a connectionless packet starts with 0xffffffff
        if msg.cursize >= 4 and struct.unpack_from("<i", msg.data, 0)[0] == -1:
            try:
                sv_conless.SV_ConnectionlessPacket()
            except errors.DropError:
                raise
            except Exception as err:
                _untrusted_data_error(err, "connectionless packet")
            continue

        # the qport, to fix up routers that translate addresses
        movemsg.MSG_BeginReading(msg)
        movemsg.MSG_ReadLong(msg)  # sequence number
        movemsg.MSG_ReadLong(msg)  # acknowledged sequence number
        qport = movemsg.MSG_ReadShort(msg) & 0xffff

        cl = _client_for_packet(qport)
        if cl is None:
            continue

        if cl.netchan.remote_address.port != netchan.net_from.port:
            clientserver.Com_Printf("%s: fixing up a translated port\n", "SV_ReadPackets")
            cl.netchan.remote_address.port = netchan.net_from.port

        if not netchan.Netchan_Process(cl.netchan, msg) or cl.state == CS.cs_zombie:
            continue  # not a valid, sequenced packet
        cl.lastmessage = sv_init.svs.realtime  # no timeout
        if sv_init.sv.demofile and sv_init.sv.state == server_h.server_state_t.ss_demo:
            continue
        try:
            sv_user.execute_client_message(cl)
        except errors.DropError:
            raise
        except Exception as err:
            _untrusted_data_error(err, f"message from {cl.name}")
            drop_client(cl)


def _check_timeouts() -> None:
    """Drops the clients silent for ``timeout`` seconds, and frees the old zombies.

    Server time, not real time, so a debugger doesn't drop the local client.
    """
    cvars = context.server.cvars
    realtime = sv_init.svs.realtime
    droppoint = int(realtime - 1000 * cvars.timeout.value)
    zombiepoint = int(realtime - 1000 * cvars.zombietime.value)

    for cl in _clients():
        if cl.lastmessage > realtime:
            cl.lastmessage = realtime  # message times can be wrong across a level change

        if cl.state == CS.cs_zombie and cl.lastmessage < zombiepoint:
            cl.state = CS.cs_free  # can be used again
            continue

        if cl.state in (CS.cs_connected, CS.cs_spawned) and cl.lastmessage < droppoint:
            sv_send.broadcast_printf(shared.PRINT_HIGH, "%s timed out\n", cl.name)
            drop_client(cl)
            cl.state = CS.cs_free  # no zombie


def _prep_world_frame() -> None:
    """Clears the entities' events: they last one message.

    Before the world logic, as the players are handled outside RunFrame.
    """
    for i in range(sv_game.ge.num_edicts):
        server_h.EDICT_NUM(i).s.event = 0


def _run_game_frame() -> None:
    cvars = context.server.cvars
    sv = sv_init.sv
    if frame.host_speeds.value:
        frame.time_before_game = system.Sys_Milliseconds()

    # the frame number moves on even when paused, or the delta compression
    # gets confused when a client has the "current" frame
    sv.framenum += 1
    sv.time = sv.framenum * 100

    if not cvars.paused.value or cvars.maxclients.value > 1:
        sv_game.ge.RunFrame()

        # never more than one frame behind
        if sv.time < sv_init.svs.realtime:
            if cvars.showclamp.value:
                clientserver.Com_Printf("sv highclamp\n")
            sv_init.svs.realtime = sv.time

    if frame.host_speeds.value:
        frame.time_after_game = system.Sys_Milliseconds()


def optimizations() -> int:
    """The sv_optimize_*_loadtime flags of this game mode."""
    gamemode = sv_init.svs.gamemode
    if gamemode <= 0 or gamemode > 3:
        return 0
    cvars = context.server.cvars
    cv = cvars.optimize_sp_loadtime if gamemode == server_h.GAMEMODE_SP else \
        cvars.optimize_mp_loadtime
    return int(cv.value) & server_h.OPTIMIZE_MASK_ALL


def SV_Frame(usec: int) -> None:  # noqa: N802
    cvars = context.server.cvars
    sv = sv_init.sv
    svs = sv_init.svs
    frame.time_before_game = frame.time_after_game = 0

    if not svs.initialized:
        return

    svs.realtime += usec // 1000
    rand.randk()  # keeps the random numbers time dependent

    _check_timeouts()
    _read_packets()

    # clients getting ready to spawn get their sign-on faster
    fast_signon = optimizations() & server_h.OPTIMIZE_SENDRATE
    if fast_signon:
        sv_send.send_prep_client_messages()

    # the world moves on once enough time has passed
    if not cvars.timedemo.value and svs.realtime < sv.time:
        if sv.time - svs.realtime > 100:
            # never let the time get too far off
            if cvars.showclamp.value:
                clientserver.Com_Printf("sv lowclamp\n")
            svs.realtime = sv.time - 100
        network.NET_Sleep(sv.time - svs.realtime)
        return

    _calc_pings()
    _give_msec()
    _run_game_frame()

    sv_send.send_client_messages()
    if not fast_signon:
        sv_send.send_prep_client_messages()

    sv_entities.record_demo_message()  # serverrecord
    _master_heartbeat()
    _prep_world_frame()  # clears the events for the next frame


def _public_dedicated() -> bool:
    cvars = context.server.cvars
    # only public dedicated servers talk to masters
    return (frame.dedicated is not None and bool(frame.dedicated.value)
            and cvars is not None and bool(cvars.public.value))


def _master_heartbeat() -> None:
    """Tells the masters every few minutes that the server is up, and its status."""
    if not _public_dedicated():
        return

    svs = sv_init.svs
    if svs.last_heartbeat > svs.realtime:
        svs.last_heartbeat = svs.realtime  # the time wrapped around
    if svs.realtime - svs.last_heartbeat < HEARTBEAT_SECONDS * 1000:
        return
    svs.last_heartbeat = svs.realtime

    status = status_string()  # as for a status packet
    for adr in context.server.masters:
        if adr.port:
            clientserver.Com_Printf("Sending heartbeat to %s\n", network.NET_AdrToString(adr))
            netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr,
                                           "heartbeat\n" + status)


def _master_shutdown() -> None:
    """Tells the masters the server is going down."""
    if not _public_dedicated():
        return
    for i, adr in enumerate(context.server.masters):
        if adr.port:
            if i > 0:
                clientserver.Com_Printf("Sending heartbeat to %s\n", network.NET_AdrToString(adr))
            netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr, "shutdown")


def userinfo_changed(cl: server_h.client_t) -> None:
    """Takes the name and the rate from a client's new userinfo."""
    sv_game.ge.ClientUserinfoChanged(server_h.CL_EDICT(cl), cl.userinfo)  # the game may change it

    name = shared_c.Info_ValueForKey(cl.userinfo, "name")[:NAME_SIZE - 1]
    cl.name = "".join(chr(ord(c) & 127) for c in name)  # without the high bit

    rate = shared_c.Info_ValueForKey(cl.userinfo, "rate")
    cl.rate = min(max(shared_c.atoi(rate), 100), 15000) if rate else 5000


def SV_Init() -> None:  # noqa: N802
    """Sets the server up, once at start-up (not for each game)."""
    sv_cmd.SV_InitOperatorCommands()

    get = cvar.Cvar_Get
    info_latch = shared.CVAR_SERVERINFO | shared.CVAR_LATCH
    optimize_sp = get("sv_optimize_sp_loadtime", "31", 0)
    optimize_mp = get("sv_optimize_mp_loadtime", "7", 0)
    rcon_password = get("rcon_password", "", 0)
    get("skill", "1", 0)
    get("singleplayer", "0", info_latch)
    get("deathmatch", "0", info_latch)
    get("coop", "0", info_latch)
    get("dmflags", str(shared.DF_INSTANT_ITEMS), shared.CVAR_SERVERINFO)
    get("fraglimit", "0", shared.CVAR_SERVERINFO)
    get("timelimit", "0", shared.CVAR_SERVERINFO)
    get("cheats", "0", info_latch)
    get("protocol", str(common_h.PROTOCOL_VERSION), shared.CVAR_SERVERINFO | shared.CVAR_NOSET)

    context.server.cvars = context.ServerCvars(
        optimize_sp_loadtime=optimize_sp,
        optimize_mp_loadtime=optimize_mp,
        rcon_password=rcon_password,
        maxclients=get("maxclients", "1", info_latch),
        hostname=get("hostname", "noname", shared.CVAR_SERVERINFO | shared.CVAR_ARCHIVE),
        timeout=get("timeout", "125", 0),
        zombietime=get("zombietime", "2", 0),
        showclamp=get("showclamp", "0", 0),
        paused=get("paused", "0", 0),
        timedemo=get("timedemo", "0", 0),
        enforcetime=get("sv_enforcetime", "0", 0),
        allow_download=get("allow_download", "1", shared.CVAR_ARCHIVE),
        allow_download_players=get("allow_download_players", "0", shared.CVAR_ARCHIVE),
        allow_download_models=get("allow_download_models", "1", shared.CVAR_ARCHIVE),
        allow_download_sounds=get("allow_download_sounds", "1", shared.CVAR_ARCHIVE),
        allow_download_maps=get("allow_download_maps", "1", shared.CVAR_ARCHIVE),
        downloadserver=get("sv_downloadserver", "", 0),
        noreload=get("sv_noreload", "0", 0),
        airaccelerate=get("sv_airaccelerate", "0", shared.CVAR_LATCH),
        public=get("public", "0", 0),
        entfile=get("sv_entfile", "1", shared.CVAR_ARCHIVE),
    )

    szone.SZ_Init(netchan.net_message, common_h.MAX_MSGLEN)


def _final_message(message: str, reconnect: bool) -> None:
    """Sends every client a last message, at once (the server is about to stop)."""
    msg = netchan.net_message
    szone.SZ_Clear(msg)
    movemsg.MSG_WriteByte(msg, SVC.svc_print.value)
    movemsg.MSG_WriteByte(msg, shared.PRINT_HIGH)
    movemsg.MSG_WriteString(msg, message)
    movemsg.MSG_WriteByte(msg, (SVC.svc_reconnect if reconnect else SVC.svc_disconnect).value)

    # The clients of the server being stopped, not maxclients: that may
    # already be set for the next game (4 for coop after single player).
    # num_client_entities is maxclients * UPDATE_BACKUP * 64 of this server.
    count = sv_init.svs.num_client_entities // (common_h.UPDATE_BACKUP * 64)
    connected = [cl for cl in sv_init.svs.clients[:count]
                 if cl.state.value >= CS.cs_connected.value]
    for _ in range(2):  # twice, against OS buffers that are too small
        for cl in connected:
            netchan.Netchan_Transmit(cl.netchan, msg.data[:msg.cursize])


def clear_baselines() -> None:
    sv_init.sv.baselines = []
    sv_init.sv.numbaselines = 0


def SV_Shutdown(finalmsg: str, reconnect: bool) -> None:  # noqa: N802
    """Stops the server, when a game ends (and before quitting or a fatal error)."""
    if sv_init.svs.clients:
        _final_message(finalmsg, reconnect)

    _master_shutdown()
    sv_game.SV_ShutdownGameProgs()

    sv = sv_init.sv
    if sv.demofile:
        filesystem.FS_FCloseFile(sv.demofile)
    sv.configstrings_overflow = []
    clear_baselines()
    sv.clear()
    clientserver.Com_SetServerState(sv.state.value)

    if sv_init.svs.demofile is not None:
        sv_init.svs.demofile.close()
    sv_init.svs.clear()
