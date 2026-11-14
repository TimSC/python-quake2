"""The entities each client sees (Yamagi's sv_entities.c).

Every server frame, ``build_client_frame`` picks the entities a client can
see or hear and stores their states (and the player state and the visible
areas) as the client's frame. ``write_frame_to_client`` then sends that
frame as a delta from the last frame the client acknowledged.
``record_demo_message`` writes a whole frame for ``serverrecord``.

The frames' entity states live in one ring shared by all clients,
``svs.client_entities``.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import copy
import struct
from collections.abc import Sequence

import numpy as np

from common import clientserver, collision, entity_delta, movemsg, player_delta, szone
from common.header import common as common_h
from common.header import shared
from game.header import game as game_h
from server import sv_game, sv_init, sv_main
from server.header import server as server_h

NO_ENTITY = 99999  # past the last entity number, ends the merge in write_packet_entities()
SOUND_RANGE = 400.0  # sounds of entities without a model are sent within this distance
DEMO_MESSAGE_SIZE = 32768

# the PVS around the view position (see fat_pvs())
_fat_pvs = bytearray(65536 // 8)


def frame_entities(frame: server_h.client_frame_t | None) -> list[shared.entity_state_t]:
    """A client frame's entity states, in entity number order."""
    if frame is None:
        return []
    ring = sv_init.svs.client_entities
    size = sv_init.svs.num_client_entities
    return [ring[(frame.first_entity + i) % size] for i in range(frame.num_entities)]


def write_remove(msg: common_h.sizebuf_t, number: int) -> None:
    """Tells the client an entity is no longer in its frame."""
    bits = common_h.U_REMOVE
    if number >= 256:
        bits |= common_h.U_NUMBER16 | common_h.U_MOREBITS1
    movemsg.MSG_WriteByte(msg, bits & 255)
    if bits & 0xff00:
        movemsg.MSG_WriteByte(msg, (bits >> 8) & 255)
    if bits & common_h.U_NUMBER16:
        movemsg.MSG_WriteShort(msg, number)
    else:
        movemsg.MSG_WriteByte(msg, number)


def write_packet_entities(old: Sequence[shared.entity_state_t],
                          new: Sequence[shared.entity_state_t],
                          msg: common_h.sizebuf_t,
                          baselines: Sequence[shared.entity_state_t], maxclients: int) -> None:
    """Writes the entities of a frame as a delta from an older frame.

    Both lists are in entity number order. An entity in both gets a delta
    (no bytes if it didn't change; players always get one, which keeps
    their old origin and stops them warping), a new one a delta from its
    baseline, and one that's gone a remove. The list stops early when the
    message gets near full.
    """
    movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_packetentities.value)

    oldindex = newindex = 0
    while newindex < len(new) or oldindex < len(old):
        if msg.cursize > common_h.MAX_MSGLEN - 150:
            break

        newent = new[newindex] if newindex < len(new) else None
        oldent = old[oldindex] if oldindex < len(old) else None
        newnum = newent.number if newent is not None else NO_ENTITY
        oldnum = oldent.number if oldent is not None else NO_ENTITY

        if newnum == oldnum:
            entity_delta.write_delta(oldent, newent, msg, False, newnum <= maxclients)
            oldindex += 1
            newindex += 1
        elif newnum < oldnum:
            baseline = baselines[newnum] if newnum < len(baselines) else None
            entity_delta.write_delta(baseline, newent, msg, True, True)
            newindex += 1
        else:
            write_remove(msg, oldnum)
            oldindex += 1

    movemsg.MSG_WriteShort(msg, 0)  # end of packetentities


def write_frame_to_client(client: server_h.client_t, msg: common_h.sizebuf_t) -> None:
    """Writes the client's frame for this server frame."""
    sv = sv_init.sv
    frame = client.frames[sv.framenum & common_h.UPDATE_MASK]

    if client.lastframe <= 0 or sv.framenum - client.lastframe >= common_h.UPDATE_BACKUP - 3:
        # the client asks for a full frame, or hasn't got one through in a
        # long time: no delta
        oldframe = None
        lastframe = -1
    else:
        oldframe = client.frames[client.lastframe & common_h.UPDATE_MASK]
        lastframe = client.lastframe

    movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_frame.value)
    movemsg.MSG_WriteLong(msg, sv.framenum)
    movemsg.MSG_WriteLong(msg, lastframe)  # what the delta is from
    movemsg.MSG_WriteByte(msg, client.surpressCount)  # packets dropped for the rate
    client.surpressCount = 0

    movemsg.MSG_WriteByte(msg, frame.areabytes)
    szone.SZ_Write(msg, bytes(frame.areabits[:frame.areabytes]))

    movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_playerinfo.value)
    player_delta.write_delta(oldframe.ps if oldframe else None, frame.ps, msg)

    baselines = sv.baselines[:sv.numbaselines]
    write_packet_entities(frame_entities(oldframe), frame_entities(frame), msg,
                          baselines, sv_init.server.maxclients)


def fat_pvs(org: np.ndarray) -> bytearray:
    """The PVS of all the leafs within 8 units of org.

    The client interpolates its view position, so one point's PVS isn't
    enough.
    """
    mins = org - 8
    maxs = org + 8
    leafs = [0] * 64
    count = collision.CM_BoxLeafnums(mins, maxs, leafs, 64, [0])
    if count < 1:
        clientserver.Com_Error(common_h.ERR_FATAL, "SV_FatPVS: count < 1")
    size = ((collision.CM_NumClusters() + 31) >> 5) << 2

    clusters = []
    for leaf in leafs[:count]:
        cluster = collision.CM_LeafCluster(leaf)
        if cluster not in clusters:
            clusters.append(cluster)

    pvs = np.frombuffer(bytes(collision.CM_ClusterPVS(clusters[0])[:size]), dtype=np.uint8)
    for cluster in clusters[1:]:
        pvs = pvs | np.frombuffer(bytes(collision.CM_ClusterPVS(cluster)[:size]),
                                  dtype=np.uint8)
    _fat_pvs[:size] = pvs.tobytes()
    return _fat_pvs


def _has_bit(bits, n: int) -> bool:
    return bool(bits[n >> 3] & (1 << (n & 7)))


def _sendable(ent) -> bool:
    """Entities without a model are sent only for an effect, a sound or an event."""
    if ent.svflags & game_h.SVF_NOCLIENT:
        return False
    s = ent.s
    return bool(s.modelindex or s.effects or s.sound or s.event)


def _visible(ent, org: np.ndarray, clientarea: int, phs, pvs) -> bool:
    """Whether a client at org (in clientarea) sees or hears ent."""
    if not collision.CM_AreasConnected(clientarea, ent.areanum):
        # doors can straddle two areas
        if not ent.areanum2 or not collision.CM_AreasConnected(clientarea, ent.areanum2):
            return False  # blocked by a door

    if ent.s.renderfx & shared.RF_BEAM:
        return _has_bit(phs, ent.clusternums[0])  # beams check one point, in the PHS

    if ent.num_clusters == -1:
        # in too many leafs to list: go by the head node
        if not collision.CM_HeadnodeVisible(ent.headnode, pvs):
            return False
    elif not any(_has_bit(pvs, c) for c in ent.clusternums[:ent.num_clusters]):
        return False

    if not ent.s.modelindex:
        # a sound that would be attenuated away
        delta = org - ent.s.origin
        if float(np.dot(delta, delta)) > SOUND_RANGE * SOUND_RANGE:
            return False
    return True


def build_client_frame(client: server_h.client_t) -> None:
    """Builds the client's frame: its player state, areas and visible entities."""
    clent = server_h.CL_EDICT(client)
    if not clent.client:
        return  # not in the game yet

    svs = sv_init.svs
    frame = client.frames[sv_init.sv.framenum & common_h.UPDATE_MASK]
    frame.senttime = svs.realtime  # for the ping

    ps = clent.client.ps
    org = (np.asarray(ps.pmove.origin, dtype=np.float32) * np.float32(0.125)
           + ps.viewoffset).astype(np.float32)

    leafnum = collision.CM_PointLeafnum(org)
    clientarea = collision.CM_LeafArea(leafnum)
    clientcluster = collision.CM_LeafCluster(leafnum)

    frame.areabytes = collision.CM_WriteAreaBits(frame.areabits, clientarea)
    frame.ps = copy.deepcopy(ps)

    pvs = fat_pvs(org)
    phs = collision.CM_ClusterPHS(clientcluster)

    frame.num_entities = 0
    frame.first_entity = svs.next_client_entities

    for e in range(1, sv_game.ge.num_edicts):
        ent = server_h.EDICT_NUM(e)
        if not _sendable(ent):
            continue
        if ent is not clent and not _visible(ent, org, clientarea, phs, pvs):
            continue

        if ent.s.number != e:
            clientserver.Com_DPrintf("FIXING ENT->S.NUMBER!!!\n")
            ent.s.number = e

        state = svs.client_entities[svs.next_client_entities % svs.num_client_entities]
        state.copy(ent.s)
        if ent.owner is clent:
            state.solid = 0  # the player's own missiles aren't solid to them

        svs.next_client_entities += 1
        frame.num_entities += 1


def record_demo_message() -> None:
    """Writes the whole world, without deltas, to the server demo.

    For footage to merge or assemble into demos (``serverrecord``).
    """
    svs = sv_init.svs
    if not svs.demofile:
        return

    buf = common_h.sizebuf_t()
    szone.SZ_Init(buf, DEMO_MESSAGE_SIZE)

    # a frame message without a player state
    movemsg.MSG_WriteByte(buf, common_h.svc_ops_e.svc_frame.value)
    movemsg.MSG_WriteLong(buf, sv_init.sv.framenum)
    movemsg.MSG_WriteByte(buf, common_h.svc_ops_e.svc_packetentities.value)

    nostate = shared.entity_state_t()
    for e in range(1, sv_game.ge.num_edicts):
        ent = server_h.EDICT_NUM(e)
        if ent.inuse and ent.s.number and _sendable(ent):
            entity_delta.write_delta(nostate, ent.s, buf, False, True)

    movemsg.MSG_WriteShort(buf, 0)  # end of packetentities

    # and the multicasts since the last frame
    szone.SZ_Write(buf, bytes(svs.demo_multicast.data[:svs.demo_multicast.cursize]))
    szone.SZ_Clear(svs.demo_multicast)

    svs.demofile.write(struct.pack("<i", buf.cursize))
    svs.demofile.write(bytes(buf.data[:buf.cursize]))
