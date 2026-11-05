"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""
from __future__ import annotations

import copy
import numpy as np
from qcommon import cmodel, pmove
pass
from client import cl_main, client
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver

def _copy_trace(src: shared.trace_t, dest: shared.trace_t):
    dest.allsolid = src.allsolid
    dest.startsolid = src.startsolid
    dest.fraction = src.fraction
    shared.VectorCopy(src.endpos, dest.endpos)
    dest.plane = src.plane
    dest.surface = src.surface
    dest.contents = src.contents
    dest.ent = src.ent

"""
===================
CL_CheckPredictionError
===================
"""
def CL_CheckPredictionError():
    if not cl_main.cl_predict or not cl_main.cl_predict.value:
        return
    pm_flags = cl_main.cl.frame.playerstate.pmove.pm_flags
    if pm_flags is None:
        pm_flags = 0
    if pm_flags & shared.PMF_NO_PREDICTION:
        return

    frame = cl_main.cls.netchan.incoming_acknowledged & (client.CMD_BACKUP - 1)

    delta = np.zeros((3,), dtype=np.float32)
    predicted_origin = cl_main.cl.predicted_origins[frame]
    if predicted_origin is None:
        predicted_origin = np.zeros((3,), dtype=np.float32)
        cl_main.cl.predicted_origins[frame] = predicted_origin

    shared.VectorSubtract(cl_main.cl.frame.playerstate.pmove.origin, predicted_origin, delta)

    length = abs(delta[0]) + abs(delta[1]) + abs(delta[2])
    if length > 640:
        shared.VectorClear(cl_main.cl.prediction_error)
    else:
        if (delta[0] or delta[1] or delta[2]) and cl_main.cl_showmiss and cl_main.cl_showmiss.value:
            clientserver.Com_Printf(
                "prediction miss on %i: %i\n"
                % (cl_main.cl.frame.serverframe, int(delta[0] + delta[1] + delta[2]))
            )
        shared.VectorCopy(cl_main.cl.frame.playerstate.pmove.origin, predicted_origin)
        for i in range(3):
            cl_main.cl.prediction_error[i] = delta[i] * 0.125

"""
====================
CL_ClipMoveToEntities

Checks collisions against solid entities for movement tracing.
====================
"""
def CL_ClipMoveToEntities(start, mins, maxs, end, tr):
    bmins = np.zeros((3,), dtype=np.float32)
    bmaxs = np.zeros((3,), dtype=np.float32)

    for i in range(cl_main.cl.frame.num_entities):
        num = (cl_main.cl.frame.parse_entities + i) & (client.MAX_PARSE_ENTITIES - 1)
        ent = cl_main.cl_parse_entities[num]
        solid = ent.solid or 0
        if not solid:
            continue

        if ent.number == cl_main.cl.playernum + 1:
            continue

        if solid == 31:
            cmodel_obj = cl_main.cl.model_clip[ent.modelindex]
            if not cmodel_obj:
                continue
            headnode = cmodel_obj.headnode
            angles = ent.angles
        else:
            x = 8 * (solid & 31)
            zd = 8 * ((solid >> 5) & 31)
            zu = 8 * ((solid >> 10) & 63) - 32

            bmins[0] = bmins[1] = -x
            bmaxs[0] = bmaxs[1] = x
            bmins[2] = -zd
            bmaxs[2] = zu

            headnode = cmodel.CM_HeadnodeForBox(bmins, bmaxs)
            angles = shared_c.vec3_origin

        if tr.allsolid:
            return

        trace = cmodel.CM_TransformedBoxTrace(
            start,
            end,
            mins,
            maxs,
            headnode,
            shared.MASK_PLAYERSOLID,
            ent.origin,
            angles,
        )

        if trace.allsolid or trace.startsolid or trace.fraction < tr.fraction:
            trace.ent = ent
            if tr.startsolid:
                _copy_trace(trace, tr)
                tr.startsolid = True
            else:
                _copy_trace(trace, tr)
        elif trace.startsolid:
            tr.startsolid = True

"""
================
CL_PMTrace
================
"""
def CL_PMTrace(start, mins, maxs, end):
    trace = cmodel.CM_BoxTrace(start, end, mins, maxs, 0, shared.MASK_PLAYERSOLID)
    if trace.fraction < 1.0:
        trace.ent = 1
    CL_ClipMoveToEntities(start, mins, maxs, end, trace)
    return trace

"""
====================
CL_PMpointcontents
====================
"""
def CL_PMpointcontents(point):
    contents = cmodel.CM_PointContents(point, 0)
    for i in range(cl_main.cl.frame.num_entities):
        num = (cl_main.cl.frame.parse_entities + i) & (client.MAX_PARSE_ENTITIES - 1)
        ent = cl_main.cl_parse_entities[num]

        if (ent.solid or 0) != 31:
            continue

        cmodel_obj = cl_main.cl.model_clip[ent.modelindex]
        if not cmodel_obj:
            continue

        contents |= cmodel.CM_TransformedPointContents(
            point, cmodel_obj.headnode, ent.origin, ent.angles
        )

    return contents

"""
=================
CL_PredictMovement

Sets cl.predicted_origin and cl.predicted_angles
=================
"""
def CL_PredictMovement():
    if cl_main.cls.state != client.connstate_t.ca_active:
        return
    if cl_main.cl_paused and cl_main.cl_paused.value:
        return

    pm_state = cl_main.cl.frame.playerstate.pmove
    pm_flags = pm_state.pm_flags if pm_state.pm_flags is not None else 0
    if (
        not cl_main.cl_predict
        or not cl_main.cl_predict.value
        or pm_flags & shared.PMF_NO_PREDICTION
    ):
        for i in range(3):
            cl_main.cl.predicted_angles[i] = (
                cl_main.cl.viewangles[i]
                + shared.SHORT2ANGLE(pm_state.delta_angles[i])
            )
        return

    ack = cl_main.cls.netchan.incoming_acknowledged
    current = cl_main.cls.netchan.outgoing_sequence

    if current - ack >= client.CMD_BACKUP:
        if cl_main.cl_showmiss and cl_main.cl_showmiss.value:
            clientserver.Com_Printf("exceeded CMD_BACKUP\n")
        return

    pm = pmove.pmove_t()
    pm.trace = CL_PMTrace
    pm.pointcontents = CL_PMpointcontents

    airaccel = cl_main.cl.configstrings[shared.CS_AIRACCEL]
    pmove.pm_airaccelerate = float(airaccel) if airaccel else 0.0

    pm.s = copy.deepcopy(pm_state)

    frame_index = 0
    while ack + 1 < current:
        ack += 1
        frame_index = ack & (client.CMD_BACKUP - 1)
        pm.cmd = copy.deepcopy(cl_main.cl.cmds[frame_index])
        pmove.Pmove(pm)

        if cl_main.cl.predicted_origins[frame_index] is None:
            cl_main.cl.predicted_origins[frame_index] = np.zeros(
                (3,), dtype=np.float32
            )
        shared.VectorCopy(
            pm.s.origin, cl_main.cl.predicted_origins[frame_index]
        )

    oldframe = (ack - 2) & (client.CMD_BACKUP - 1)
    old_origin = cl_main.cl.predicted_origins[oldframe]
    oldz = old_origin[2] if old_origin is not None else 0

    step = pm.s.origin[2] - oldz
    if step > 63 and step < 160 and (pm.s.pm_flags & shared.PMF_ON_GROUND):
        cl_main.cl.predicted_step = step * 0.125
        cl_main.cl.predicted_step_time = (
            cl_main.cls.realtime - cl_main.cls.frametime * 500
        )

    for i in range(3):
        cl_main.cl.predicted_origin[i] = pm.s.origin[i] * 0.125

    shared.VectorCopy(pm.viewangles, cl_main.cl.predicted_angles)
