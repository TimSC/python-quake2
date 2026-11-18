"""Entities in the world: linking them into areas, and traces (Yamagi's sv_world.c).

The world is split into a tree of area nodes (``AREA_DEPTH`` levels,
halving the longer side each time). An entity is linked into the lowest
node its box fits in, in the node's triggers or solids. ``area_edicts``
finds the entities whose boxes touch a box, ``trace`` moves a box through
the world and the solid entities, and ``point_contents`` gives the
contents at a point.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from common import clientserver, collision
from common.header import shared
from common.shared import shared as shared_c
from game.header import game as game_h
from server import sv_init
from server.header import server as server_h

AREA_DEPTH = 4
AREA_NODES = 32
MAX_TOTAL_ENT_LEAFS = 128


@dataclass(slots=True)
class AreaNode:
    axis: int = -1  # -1: a leaf
    dist: float = 0.0
    children: tuple[AreaNode, AreaNode] | None = None
    # the entities linked here, oldest first (as the C's lists)
    triggers: list = field(default_factory=list)
    solids: list = field(default_factory=list)


_root: AreaNode | None = None


def _create_area_node(depth: int, mins: np.ndarray, maxs: np.ndarray) -> AreaNode:
    """A uniformly subdivided tree for the given world size."""
    node = AreaNode()
    if depth == AREA_DEPTH:
        return node

    size = maxs - mins
    node.axis = 0 if size[0] > size[1] else 1
    node.dist = 0.5 * (maxs[node.axis] + mins[node.axis])

    maxs1 = np.array(maxs, dtype=np.float32)
    mins2 = np.array(mins, dtype=np.float32)
    maxs1[node.axis] = node.dist
    mins2[node.axis] = node.dist
    front = _create_area_node(depth + 1, mins2, np.array(maxs, dtype=np.float32))
    back = _create_area_node(depth + 1, np.array(mins, dtype=np.float32), maxs1)
    node.children = (front, back)
    return node


def clear_world() -> None:
    """A new area tree for the world model (no entities linked)."""
    global _root
    world = sv_init.sv.models[1]
    _root = _create_area_node(0, world.mins, world.maxs) if world else None


def unlink_edict(ent) -> None:
    """Takes an entity out of its area (if it's in one)."""
    linked_in = ent.area.prev
    if not linked_in:
        return
    for i, other in enumerate(linked_in):
        if other is ent:
            del linked_in[i]
            break
    ent.area.prev = ent.area.next = None


def _solid_encoding(ent) -> int:
    """The size of an entity's box as the clients predict it (entity_state_t.solid)."""
    if ent.solid == game_h.SOLID_BBOX and not (ent.svflags & game_h.SVF_DEADMONSTER):
        xy = min(max(int(ent.maxs[0] / 8), 1), 31)  # x and y taken as equal and symmetric
        down = min(max(int(-ent.mins[2] / 8), 1), 31)  # z isn't symmetric
        up = min(max(int((ent.maxs[2] + 32) / 8), 1), 63)  # and its maxs can be negative
        return (up << 10) | (down << 5) | xy
    if ent.solid == game_h.SOLID_BSP:
        return 31  # a SOLID_BBOX never makes this value
    return 0


def _set_abs_box(ent) -> None:
    if ent.solid == game_h.SOLID_BSP and (ent.s.angles[0] or ent.s.angles[1] or ent.s.angles[2]):
        # room to rotate
        radius = max(max(abs(float(v)) for v in ent.mins), max(abs(float(v)) for v in ent.maxs),
                     0)
        for i in range(3):
            ent.absmin[i] = ent.s.origin[i] - radius
            ent.absmax[i] = ent.s.origin[i] + radius
    else:
        shared.VectorAdd(ent.s.origin, ent.mins, ent.absmin)
        shared.VectorAdd(ent.s.origin, ent.maxs, ent.absmax)

    # moves are clipped an epsilon from an edge, so boxes that nearly touch
    # are checked too
    ent.absmin -= 1
    ent.absmax += 1


def _set_areas_and_clusters(ent) -> None:
    """The areas (two at most, for doors) and PVS clusters the entity's box is in."""
    leafs = [0] * MAX_TOTAL_ENT_LEAFS
    topnode = [0]
    ent.num_clusters = 0
    ent.areanum = 0
    ent.areanum2 = 0

    num_leafs = collision.CM_BoxLeafnums(ent.absmin, ent.absmax, leafs, MAX_TOTAL_ENT_LEAFS,
                                         topnode)
    clusters = []
    for leaf in leafs[:num_leafs]:
        clusters.append(collision.CM_LeafCluster(leaf))
        area = collision.CM_LeafArea(leaf)
        if not area:
            continue
        if ent.areanum and ent.areanum != area:
            # doors may straddle two areas, nothing should need more
            if (ent.areanum2 and ent.areanum2 != area
                    and sv_init.sv.state == server_h.server_state_t.ss_loading):
                clientserver.Com_DPrintf("Object touching 3 areas at %f %f %f\n",
                                         ent.absmin[0], ent.absmin[1], ent.absmin[2])
            ent.areanum2 = area
        else:
            ent.areanum = area

    if num_leafs >= MAX_TOTAL_ENT_LEAFS:
        # leafs may be missing: go by the head node
        ent.num_clusters = -1
        ent.headnode = topnode[0]
        return

    seen = []
    for cluster in clusters:
        if cluster == -1 or cluster in seen:
            continue  # not a visible leaf, or listed already
        if ent.num_clusters == game_h.MAX_ENT_CLUSTERS:
            ent.num_clusters = -1  # too many: go by the head node
            ent.headnode = topnode[0]
            return
        seen.append(cluster)
        ent.clusternums[ent.num_clusters] = cluster
        ent.num_clusters += 1


def link_edict(ent) -> None:
    """(Re)links an entity after it moved or changed: its box, PVS clusters and area."""
    if ent.area.prev:
        unlink_edict(ent)  # from where it was

    if ent is sv_init.server.game.edicts[0]:
        return  # not the world (the C's test; the port compared with the edict list)
    if not ent.inuse:
        return

    shared.VectorSubtract(ent.maxs, ent.mins, ent.size)
    ent.s.solid = _solid_encoding(ent)  # for the clients' prediction
    _set_abs_box(ent)
    _set_areas_and_clusters(ent)

    if not ent.linkcount:
        shared.VectorCopy(ent.s.origin, ent.s.old_origin)  # the first time: a valid old origin
    ent.linkcount += 1

    if ent.solid == game_h.SOLID_NOT:
        return

    # the first node the box crosses
    node = _root
    while node.axis != -1:
        if ent.absmin[node.axis] > node.dist:
            node = node.children[0]
        elif ent.absmax[node.axis] < node.dist:
            node = node.children[1]
        else:
            break

    linked_in = node.triggers if ent.solid == game_h.SOLID_TRIGGER else node.solids
    linked_in.append(ent)
    ent.area.prev = linked_in  # where it is; also the game's "linked" test
    ent.area.owner = ent


def _touches(check, mins, maxs) -> bool:
    return not (check.absmin[0] > maxs[0] or check.absmin[1] > maxs[1]
                or check.absmin[2] > maxs[2] or check.absmax[0] < mins[0]
                or check.absmax[1] < mins[1] or check.absmax[2] < mins[2])


def _collect(mins, maxs, triggers: bool, found: list, maxcount: int) -> None:
    stack = [_root]
    # the C recurses into the front child first, then the back: a stack
    # of (front last pushed) keeps that order
    while stack:
        node = stack.pop()
        for check in (node.triggers if triggers else node.solids):
            if check.solid == game_h.SOLID_NOT:
                continue  # deactivated
            if not _touches(check, mins, maxs):
                continue
            if len(found) == maxcount:
                clientserver.Com_Printf("SV_AreaEdicts: MAXCOUNT\n")
                return
            found.append(check)

        if node.axis == -1:
            continue
        back = mins[node.axis] < node.dist
        if back:
            stack.append(node.children[1])
        if maxs[node.axis] > node.dist:
            stack.append(node.children[0])


def find_area_edicts(mins, maxs, maxcount: int, areatype: int) -> list:
    """The entities (triggers or solids) whose boxes touch mins/maxs."""
    found: list = []
    _collect(mins, maxs, areatype != shared.AREA_SOLID, found, maxcount)
    return found


def area_edicts(mins, maxs, out: list, maxcount: int, areatype: int) -> int:
    """The game's BoxEdicts: fills out with the entities touching the box."""
    found = find_area_edicts(mins, maxs, maxcount, areatype)
    out[:len(found)] = found
    return len(found)


def _hull_for_entity(ent) -> int:
    """The head node to clip against an entity: its BSP model, or a box of its size."""
    if ent.solid == game_h.SOLID_BSP:
        mi = ent.s.modelindex
        model = sv_init.sv.models[mi] if 0 <= mi < shared.MAX_MODELS else None
        return model.headnode if model else 0
    return collision.CM_HeadnodeForBox(ent.mins, ent.maxs)


def point_contents(p) -> int:
    """The contents at p: the world's and every solid entity's there."""
    contents = collision.CM_PointContents(p, sv_init.sv.models[1].headnode)
    for hit in find_area_edicts(p, p, shared.MAX_EDICTS, shared.AREA_SOLID):
        # as the C: the entity's angles, even for boxes (which don't rotate)
        contents |= collision.CM_TransformedPointContents(p, _hull_for_entity(hit),
                                                         hit.s.origin, hit.s.angles)
    return contents


@dataclass(slots=True)
class _MoveClip:
    start: np.ndarray
    end: np.ndarray
    mins: np.ndarray  # the moving box
    maxs: np.ndarray
    mins2: np.ndarray  # the box for clipping against monsters (a copy, as in the C)
    maxs2: np.ndarray
    passedict: object
    contentmask: int
    trace: shared.trace_t
    boxmins: np.ndarray = field(default_factory=lambda: np.zeros((3,), dtype=np.float32))
    boxmaxs: np.ndarray = field(default_factory=lambda: np.zeros((3,), dtype=np.float32))


def _clip_move_to_entities(clip: _MoveClip) -> None:
    # an entity in the list can be removed (killtargeted) before it is reached
    for touch in find_area_edicts(clip.boxmins, clip.boxmaxs, shared.MAX_EDICTS,
                                  shared.AREA_SOLID):
        if touch.solid == game_h.SOLID_NOT or touch is clip.passedict:
            continue
        if clip.trace.allsolid:
            return
        if clip.passedict:
            if touch.owner is clip.passedict:
                continue  # not one's own missiles
            if clip.passedict.owner is touch:
                continue  # not one's owner
        if (not (clip.contentmask & shared.CONTENTS_DEADMONSTER)
                and touch.svflags & game_h.SVF_DEADMONSTER):
            continue

        angles = touch.s.angles if touch.solid == game_h.SOLID_BSP else shared_c.vec3_origin
        monster = touch.svflags & game_h.SVF_MONSTER
        trace = collision.CM_TransformedBoxTrace(clip.start, clip.end,
                                                 clip.mins2 if monster else clip.mins,
                                                 clip.maxs2 if monster else clip.maxs,
                                                 _hull_for_entity(touch), clip.contentmask,
                                                 touch.s.origin, angles)

        if trace.allsolid or trace.startsolid or trace.fraction < clip.trace.fraction:
            trace.ent = touch
            if clip.trace.startsolid:
                clip.trace = trace
                clip.trace.startsolid = True
            else:
                clip.trace = trace


def _trace_bounds(start, mins, maxs, end, boxmins, boxmaxs) -> None:
    """The box around the whole move."""
    for i in range(3):
        if end[i] > start[i]:
            boxmins[i] = start[i] + mins[i] - 1
            boxmaxs[i] = end[i] + maxs[i] + 1
        else:
            boxmins[i] = end[i] + mins[i] - 1
            boxmaxs[i] = start[i] + maxs[i] + 1


def trace(start, mins, maxs, end, passedict, contentmask: int) -> shared.trace_t:
    """Moves a box (mins/maxs, None for a point) through the world from start to end.

    passedict, and the entities it owns, are not checked.
    """
    if mins is None:
        mins = shared_c.vec3_origin
    if maxs is None:
        maxs = shared_c.vec3_origin

    world_trace = collision.CM_BoxTrace(start, end, mins, maxs, 0, contentmask)
    world_trace.ent = sv_init.server.game.edicts[0]
    if world_trace.fraction == 0:
        return world_trace  # blocked by the world

    clip = _MoveClip(start, end, mins, maxs, np.array(mins, dtype=np.float32),
                     np.array(maxs, dtype=np.float32), passedict, contentmask, world_trace)
    _trace_bounds(start, clip.mins2, clip.maxs2, end, clip.boxmins, clip.boxmaxs)
    _clip_move_to_entities(clip)
    return clip.trace
