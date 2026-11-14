"""What the server sends to its clients (Yamagi's sv_send.c).

Prints, stuffed commands, multicasts (to everyone, or to the clients that
can see or hear a point) and sounds, which collect in ``sv.multicast`` and
then go into each chosen client's reliable message or datagram; and, every
frame, each client's datagram (its frame, then the multicasts) within its
rate.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import struct

import numpy as np

from common import clientserver, collision, filesystem, frame, movemsg, netchan, szone
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from game.header import game as game_h
from server import sv_entities, sv_init, sv_main, sv_user
from server.header import server as server_h

M = shared.multicast_t
CS = server_h.client_state_t
SS = server_h.server_state_t

# the entity number and channel share a signed 16 bit value: 13 bits for the
# entity, 3 for the channel
SND_MAX_ENTNUM = 4095

# what rcon and a client's redirected commands print collects here (see
# Com_BeginRedirect)
output_buffer = ""

# (reliable?, the mask to check the clients against) of each multicast
_MULTICASTS = {
    M.MULTICAST_ALL: (False, None), M.MULTICAST_ALL_R: (True, None),
    M.MULTICAST_PHS: (False, "phs"), M.MULTICAST_PHS_R: (True, "phs"),
    M.MULTICAST_PVS: (False, "pvs"), M.MULTICAST_PVS_R: (True, "pvs"),
}


def _clients() -> list[server_h.client_t]:
    return sv_init.svs.clients[:int(sv_main.maxclients.value)]


def _write_print(msg: common_h.sizebuf_t, level: int, text: str) -> None:
    movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_print.value)
    movemsg.MSG_WriteByte(msg, level)
    movemsg.MSG_WriteString(msg, text)


def flush_redirect(target: int, text: str) -> None:
    """Sends redirected console output to the rcon sender or the client."""
    if target == server_h.redirect_t.RD_PACKET.value:
        netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, netchan.net_from,
                                       "print\n" + text)
    elif target == server_h.redirect_t.RD_CLIENT.value:
        _write_print(sv_init.server.client.netchan.message, shared.PRINT_HIGH, text)


def client_printf(cl: server_h.client_t, level: int, fmt: str, *args) -> None:
    """Prints text on one client (it shows if its msg level lets it)."""
    _write_print(cl.netchan.message, level, ((fmt % args) if args else fmt)[:1023])


def broadcast_printf(level: int, fmt: str, *args) -> None:
    """Prints text on every client in the game (and a dedicated server's console)."""
    text = ((fmt % args) if args else fmt)[:2047]

    if frame.dedicated.value:
        # without the high (coloured) bit
        clientserver.Com_Printf("%s", "".join(chr(ord(c) & 127) for c in text[:1023]))

    for cl in _clients():
        if cl.state == CS.cs_spawned:
            _write_print(cl.netchan.message, level, text)


def broadcast_command(fmt: str, *args) -> None:
    """Runs a command on every client (e.g. ``changing``, ``reconnect``)."""
    if not sv_init.sv.state.value:
        return
    text = ((fmt % args) if args else fmt)[:1023]
    movemsg.MSG_WriteByte(sv_init.sv.multicast, common_h.svc_ops_e.svc_stufftext.value)
    movemsg.MSG_WriteString(sv_init.sv.multicast, text)
    multicast(None, M.MULTICAST_ALL_R)


def _in_mask(mask, cluster: int) -> bool:
    # the cluster is -1 in the void (or sometimes at a wall)
    return cluster >= 0 and bool(mask[cluster >> 3] & (1 << (cluster & 7)))


def _reaches(cluster: int, area: int, origin, mask, from_area: int) -> bool:
    """Whether a client (in cluster and area, at origin) is in the multicast's mask."""
    if _in_mask(mask, cluster) and collision.CM_AreasConnected(from_area, area):
        return True

    # A client half in opaque water has its origin below the surface but its
    # view above it, where it should see and hear things: try again higher up.
    # (Shooting under water from just above it has the same problem.)
    if collision.CM_PointContents(origin, 0) & shared.MASK_WATER:
        higher = np.array(origin, dtype=np.float32)
        higher[2] += np.float32(32.0)
        leafnum = collision.CM_PointLeafnum(higher)
        if (_in_mask(mask, collision.CM_LeafCluster(leafnum))
                and collision.CM_AreasConnected(from_area, collision.CM_LeafArea(leafnum))):
            return True
    return False


def _client_leaf(client: server_h.client_t) -> tuple[int, int]:
    """The client's (area, cluster), worked out once a frame while it doesn't move."""
    e = server_h.CL_EDICT(client)
    if (client.cached_framenum != sv_init.sv.framenum
            or not shared_c.VectorCompare(client.cached_origin, e.s.origin)):
        client.cached_origin = [e.s.origin[0], e.s.origin[1], e.s.origin[2]]
        client.cached_leafnum = collision.CM_PointLeafnum(e.s.origin)
        client.cached_area = collision.CM_LeafArea(client.cached_leafnum)
        client.cached_cluster = collision.CM_LeafCluster(client.cached_leafnum)
        client.cached_framenum = sv_init.sv.framenum
    return client.cached_area, client.cached_cluster


def multicast(origin, to) -> None:
    """Sends sv.multicast to the clients it is for, then clears it.

    ``MULTICAST_ALL`` goes to everyone (origin can be None), ``PVS`` to the
    clients that may see origin, ``PHS`` to those that may hear it. The
    ``_R`` kinds are reliable and also reach clients not yet in the game.
    """
    to = M(to)  # the game passes the enum's integer
    if to not in _MULTICASTS:
        clientserver.Com_Error(shared.ERR_FATAL, "%s: bad to:%i", "SV_Multicast", to.value)
    reliable, which = _MULTICASTS[to]

    sv = sv_init.sv
    from_area = 0
    mask = None
    if which is not None:
        leafnum = collision.CM_PointLeafnum(origin)
        from_area = collision.CM_LeafArea(leafnum)
        cluster = collision.CM_LeafCluster(leafnum)
        mask = (collision.CM_ClusterPHS if which == "phs" else collision.CM_ClusterPVS)(cluster)

    data = bytes(sv.multicast.data[:sv.multicast.cursize])
    if sv_init.svs.demofile:
        szone.SZ_Write(sv_init.svs.demo_multicast, data)  # serverrecord keeps everything

    for client in _clients():
        if client.state in (CS.cs_free, CS.cs_zombie):
            continue
        if client.state != CS.cs_spawned and not reliable:
            continue
        if mask is not None:
            area, cluster = _client_leaf(client)
            if not _reaches(cluster, area, server_h.CL_EDICT(client).s.origin, mask, from_area):
                continue
        szone.SZ_Write(client.netchan.message if reliable else client.datagram, data)

    szone.SZ_Clear(sv.multicast)


def _sound_origin(entity) -> np.ndarray:
    """Where an entity's sound comes from: its origin, or a brush model's centre."""
    if entity.solid == game_h.SOLID_BSP:
        return (entity.s.origin + np.float32(0.5) * (entity.mins + entity.maxs)).astype(np.float32)
    return np.array(entity.s.origin, dtype=np.float32)


def start_sound(origin, entity, channel: int, soundindex: int,
                volume: float, attenuation: float, timeofs: float) -> None:
    """Plays a sound on an entity's channel, for the clients that can hear it.

    An entity has eight channels (voice, weapon, feet...); channel 0 picks a
    free one, the others replace what plays on them. Channel bit 8 sends
    the sound to everyone, not only the PHS; an attenuation of 0 plays at
    full volume everywhere (up to 4 fades fastest). timeofs (0 to 0.255 s)
    starts the sound later in the frame. Without an origin the sound comes
    from the entity (the centre of a brush model).
    """
    if volume < 0.0 or volume > 1.0:
        clientserver.Com_DPrintf("%s: volume out of bounds [0-1]: %f\n", "SV_StartSound", volume)
        volume = 1.0
    if attenuation < 0.0 or attenuation > 4.0:
        clientserver.Com_DPrintf("%s: attenuation out of bounds [0-4]: %f\n",
                                 "SV_StartSound", attenuation)
        attenuation = 0.0
    if timeofs < 0.0 or timeofs > 0.255:
        clientserver.Com_DPrintf("%s: timeofs out of bounds [0-0.255]: %f\n",
                                 "SV_StartSound", timeofs)
        timeofs = 0.0

    ent = server_h.NUM_FOR_EDICT(entity)
    if ent > SND_MAX_ENTNUM:
        return

    flags = common_h.SND_ENT  # always the entity number, for the channel overrides
    if volume != common_h.DEFAULT_SOUND_PACKET_VOLUME:
        flags |= common_h.SND_VOLUME
    if attenuation != common_h.DEFAULT_SOUND_PACKET_ATTENUATION:
        flags |= common_h.SND_ATTENUATION
    # the client doesn't know brush models' odd origins, and an origin can
    # be given
    if (entity.svflags & game_h.SVF_NOCLIENT or entity.solid == game_h.SOLID_BSP
            or origin is not None):
        flags |= common_h.SND_POS
    if timeofs:
        flags |= common_h.SND_OFFSET

    if origin is None:
        origin = _sound_origin(entity)

    msg = sv_init.sv.multicast
    movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_sound.value)
    movemsg.MSG_WriteByte(msg, flags)
    movemsg.MSG_WriteByte(msg, soundindex)
    if flags & common_h.SND_VOLUME:
        movemsg.MSG_WriteByte(msg, int(volume * 255))
    if flags & common_h.SND_ATTENUATION:
        movemsg.MSG_WriteByte(msg, int(attenuation * 64))
    if flags & common_h.SND_OFFSET:
        movemsg.MSG_WriteByte(msg, int(timeofs * 1000))
    movemsg.MSG_WriteShort(msg, (ent << 3) | (channel & 7))
    if flags & common_h.SND_POS:
        movemsg.MSG_WritePos(msg, origin)

    # a sound that doesn't fade (radio chatter, voice-overs) goes to everyone
    use_phs = not (channel & shared.CHAN_NO_PHS_ADD) and attenuation != shared.ATTN_NONE
    if channel & shared.CHAN_RELIABLE:
        to = M.MULTICAST_PHS_R if use_phs else M.MULTICAST_ALL_R
    else:
        to = M.MULTICAST_PHS if use_phs else M.MULTICAST_ALL
    multicast(origin, to)


def _send_client_datagram(client: server_h.client_t) -> None:
    """Sends the client its frame and the multicasts collected for it."""
    sv_entities.build_client_frame(client)

    msg = common_h.sizebuf_t()
    szone.SZ_Init(msg, common_h.MAX_MSGLEN)
    msg.allowoverflow = True

    sv_entities.write_frame_to_client(client, msg)

    # the multicasts after the entities, so their entity references are current
    if client.datagram.overflowed:
        clientserver.Com_DPrintf("WARNING: datagram overflowed for %s\n", client.name)
    else:
        szone.SZ_Write(msg, bytes(client.datagram.data[:client.datagram.cursize]))
    szone.SZ_Clear(client.datagram)

    if msg.overflowed:
        # it must leave room for the packet header
        clientserver.Com_DPrintf("WARNING: msg overflowed for %s\n", client.name)
        szone.SZ_Clear(msg)

    netchan.Netchan_Transmit(client.netchan, bytes(msg.data[:msg.cursize]))
    client.message_size[sv_init.sv.framenum % server_h.RATE_MESSAGES] = msg.cursize  # for the rate


def _demo_completed() -> None:
    if sv_init.sv.demofile:
        filesystem.FS_FCloseFile(sv_init.sv.demofile)
        sv_init.sv.demofile = 0
    sv_user.SV_Nextserver()


def _rate_drop(c: server_h.client_t) -> bool:
    """Whether the client is over its rate and gets no packet this frame."""
    if c.netchan.remote_address.type == common_h.netadrtype_t.NA_LOOPBACK:
        return False  # never over the loopback
    if sum(c.message_size) > c.rate:
        c.surpressCount += 1
        c.message_size[sv_init.sv.framenum % server_h.RATE_MESSAGES] = 0
        return True
    return False


def _next_demo_chunk() -> bytes | None:
    """The next message of the demo the server plays; None at its end."""
    if sv_main.sv_paused.value:
        return b""

    data = filesystem.FS_FRead(4, 1, sv_init.sv.demofile)
    if len(data) != 4:
        return None
    n = struct.unpack("<i", data)[0]
    if n == -1:
        return None
    if n > common_h.MAX_MSGLEN:
        clientserver.Com_Error(shared.ERR_DROP, "SV_SendClientMessages: msglen > MAX_MSGLEN")

    msg = filesystem.FS_FRead(n, 1, sv_init.sv.demofile)
    return msg if len(msg) == n else None


def _send_disconnect(c: server_h.client_t) -> None:
    """Drops a client whose reliable message overflowed."""
    szone.SZ_Clear(c.netchan.message)
    szone.SZ_Clear(c.datagram)
    broadcast_printf(shared.PRINT_HIGH, "%s overflowed\n", c.name)
    sv_main.SV_DropClient(c)
    netchan.Netchan_Transmit(c.netchan, b"")


def _playing_media() -> bool:
    return sv_init.sv.state in (SS.ss_cinematic, SS.ss_demo, SS.ss_pic)


def send_client_messages() -> None:
    """Sends this frame's packet to every client in the game.

    A demo server sends each client the demo's next message instead.
    """
    if sv_init.sv.demofile and sv_init.sv.state == SS.ss_demo:
        demo_msg = _next_demo_chunk()
        if demo_msg is None:
            _demo_completed()
            return
    else:
        demo_msg = b""

    for c in _clients():
        if c.state == CS.cs_free:
            continue
        if c.netchan.message.overflowed:
            _send_disconnect(c)
            continue
        if _playing_media():
            netchan.Netchan_Transmit(c.netchan, demo_msg)
        elif c.state == CS.cs_spawned:
            if not _rate_drop(c):
                _send_client_datagram(c)
        # the clients not yet in the game get send_prep_client_messages()


def send_prep_client_messages() -> None:
    """Sends the reliable messages of the clients still connecting."""
    if _playing_media():
        return
    for c in _clients():
        if c.state in (CS.cs_free, CS.cs_spawned):
            continue
        if c.netchan.message.overflowed:
            _send_disconnect(c)
            continue
        if c.netchan.message.cursize or frame.curtime - c.netchan.last_sent > 1000:
            netchan.Netchan_Transmit(c.netchan, b"")  # the reliable part, if any
