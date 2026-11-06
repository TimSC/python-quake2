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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

This file implements interpolation between two frames. This is used
to smooth down network play

=======================================================================
"""
from __future__ import annotations

import copy

import numpy as np

from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import collision
from common import pmove
from client import cl_main
from client.header import client as client_h

"""
#include "header/client.h"
"""

def CL_CheckPredictionError(): #void

	"""
	int frame;
	int delta[3];
	int i;
	int len;
	"""
	delta = [0, 0, 0]

	if (not cl_main.cl_predict.value or
		(cl_main.cl.frame.playerstate.pmove.pm_flags & shared.PMF_NO_PREDICTION)):

		return


	# calculate the last usercmd_t we sent that the server has processed
	frame = cl_main.cls.netchan.incoming_acknowledged
	frame &= (client_h.CMD_BACKUP - 1)

	# compare what the server returned with what we had predicted it to be
	for i in range(3): # VectorSubtract(cl.frame.playerstate.pmove.origin, cl.predicted_origins[frame], delta); (ints)
		delta[i] = int(cl_main.cl.frame.playerstate.pmove.origin[i]) - int(cl_main.cl.predicted_origins[frame][i])

	# save the prediction error for interpolation
	len_ = abs(delta[0]) + abs(delta[1]) + abs(delta[2])

	# 80 world units
	if len_ > 640:

		# a teleport or something
		shared.VectorClear(cl_main.cl.prediction_error)

	else:

		if cl_main.cl_showmiss.value and (delta[0] or delta[1] or delta[2]):

			clientserver.Com_Printf("prediction miss on %i: %i\n", cl_main.cl.frame.serverframe,
					delta[0] + delta[1] + delta[2])


		shared.VectorCopy(cl_main.cl.frame.playerstate.pmove.origin,
				cl_main.cl.predicted_origins[frame])

		# save for error itnerpolation
		for i in range(3):

			cl_main.cl.prediction_error[i] = delta[i] * 0.125

def _trace_assign(tr: shared.trace_t, trace: shared.trace_t): # Q2PORT: *tr = trace;, tr is the caller's trace_t

	t = trace.copy()
	tr.allsolid = t.allsolid
	tr.startsolid = t.startsolid
	tr.fraction = t.fraction
	tr.endpos = t.endpos
	tr.plane = t.plane
	tr.surface = t.surface
	tr.contents = t.contents
	tr.ent = t.ent

def CL_ClipMoveToEntities(start, mins, maxs, end, tr: shared.trace_t):
	#vec3_t, vec3_t, vec3_t, vec3_t, trace_t * (static)

	"""
	int i, x, zd, zu;
	trace_t trace;
	int headnode;
	float *angles;
	entity_state_t *ent;
	int num;
	cmodel_t *cmodel;
	vec3_t bmins, bmaxs;
	"""
	bmins = np.zeros((3,), dtype=np.float32)
	bmaxs = np.zeros((3,), dtype=np.float32)

	for i in range(cl_main.cl.frame.num_entities):

		num = (cl_main.cl.frame.parse_entities + i) & (client_h.MAX_PARSE_ENTITIES - 1)
		ent = cl_main.cl_parse_entities[num]

		if not ent.solid:

			continue


		if ent.number == cl_main.cl.playernum + 1:

			continue


		if ent.solid == 31:

			# special value for bmodel
			cmodel = cl_main.cl.model_clip[ent.modelindex]

			if not cmodel:

				continue


			headnode = cmodel.headnode
			angles = ent.angles

		else:

			# encoded bbox
			x = 8 * (ent.solid & 31)
			zd = 8 * ((ent.solid >> 5) & 31)
			zu = 8 * ((ent.solid >> 10) & 63) - 32

			bmins[0] = bmins[1] = -float(x)
			bmaxs[0] = bmaxs[1] = float(x)
			bmins[2] = -float(zd)
			bmaxs[2] = float(zu)

			headnode = collision.CM_HeadnodeForBox(bmins, bmaxs)
			angles = shared_c.vec3_origin # boxes don't rotate


		if tr.allsolid:

			return


		trace = collision.CM_TransformedBoxTrace(start, end,
				mins, maxs, headnode, shared.MASK_PLAYERSOLID,
				ent.origin, angles)

		if (trace.allsolid or trace.startsolid or
			(trace.fraction < tr.fraction)):

			trace.ent = ent # (struct edict_s *)ent

			if tr.startsolid:

				_trace_assign(tr, trace) # *tr = trace;
				tr.startsolid = True

			else:

				_trace_assign(tr, trace) # *tr = trace;

def CL_PMTrace(start, mins, maxs, end)->shared.trace_t: #vec3_t, vec3_t, vec3_t, vec3_t (returns trace_t)

	"""
	trace_t t;
	"""

	# check against world
	t = collision.CM_BoxTrace(start, end, mins, maxs, 0, shared.MASK_PLAYERSOLID)

	if t.fraction < 1.0:

		t.ent = 1 # (struct edict_s *)1


	# check all other solid models
	CL_ClipMoveToEntities(start, mins, maxs, end, t)

	return t

def CL_PMpointcontents(point)->int: #const vec3_t (returns int)

	"""
	int i;
	entity_state_t *ent;
	int num;
	cmodel_t *cmodel;
	int contents;
	"""

	contents = collision.CM_PointContents(point, 0)

	for i in range(cl_main.cl.frame.num_entities):

		num = (cl_main.cl.frame.parse_entities + i) & (client_h.MAX_PARSE_ENTITIES - 1)
		ent = cl_main.cl_parse_entities[num]

		if ent.solid != 31: # special value for bmodel

			continue


		cmodel = cl_main.cl.model_clip[ent.modelindex]

		if not cmodel:

			continue


		contents |= collision.CM_TransformedPointContents(point, cmodel.headnode,
				ent.origin, ent.angles)


	return contents

"""
 * Sets cl.predicted_origin and cl.predicted_angles
"""
def CL_PredictMovement(): #void

	"""
	int ack, current;
	int frame;
	usercmd_t *cmd;
	pmove_t pm;
	int i;
	int step;
	vec3_t tmp;
	"""
	tmp = np.zeros((3,), dtype=np.float32)

	if cl_main.cls.state != client_h.connstate_t.ca_active:

		return


	if cl_main.cl_paused.value:

		return


	if (not cl_main.cl_predict.value or
		(cl_main.cl.frame.playerstate.pmove.pm_flags & shared.PMF_NO_PREDICTION)):

		# just set angles
		for i in range(3):

			cl_main.cl.predicted_angles[i] = cl_main.cl.viewangles[i] + shared.SHORT2ANGLE(
					cl_main.cl.frame.playerstate.pmove.delta_angles[i])


		return


	ack = cl_main.cls.netchan.incoming_acknowledged
	current = cl_main.cls.netchan.outgoing_sequence

	# if we are too far out of date, just freeze
	if current - ack >= client_h.CMD_BACKUP:

		if cl_main.cl_showmiss.value:

			clientserver.Com_Printf("exceeded CMD_BACKUP\n")


		return


	# copy current state to pmove
	pm = shared.pmove_t() # memset (&pm, 0, sizeof(pm));
	pm.trace = CL_PMTrace
	pm.pointcontents = CL_PMpointcontents
	pmove.pm_airaccelerate = shared_c.atof(cl_main.cl.configstrings[shared.CS_AIRACCEL])
	pm.s = copy.deepcopy(cl_main.cl.frame.playerstate.pmove) # pm.s = cl.frame.playerstate.pmove;

	# run frames
	ack += 1
	while ack <= current: # while (++ack <= current)

		frame = ack & (client_h.CMD_BACKUP - 1)
		cmd = cl_main.cl.cmds[frame]
		ack += 1

		# Ignore null entries
		if not cmd.msec:

			continue


		pm.cmd = copy.deepcopy(cmd) # pm.cmd = *cmd;
		pmove.Pmove(pm)

		# save for debug checking
		shared.VectorCopy(pm.s.origin, cl_main.cl.predicted_origins[frame])


	# step is used for movement prediction on stairs
	# (so moving up/down stairs is smooth)
	step = int(pm.s.origin[2]) - int(cl_main.cl.predicted_origin[2] * 8)
	shared.VectorCopy(pm.s.velocity, tmp)

	if (((step > 62 and step < 66) or (step > 94 and step < 98) or (step > 126 and step < 130))
		and not shared_c.VectorCompare(tmp, shared_c.vec3_origin)
		and (pm.s.pm_flags & shared.PMF_ON_GROUND)):

		cl_main.cl.predicted_step = step * 0.125
		cl_main.cl.predicted_step_time = cl_main.cls.realtime - int(cl_main.cls.nframetime * 500)


	# copy results out for rendering
	cl_main.cl.predicted_origin[0] = pm.s.origin[0] * 0.125
	cl_main.cl.predicted_origin[1] = pm.s.origin[1] * 0.125
	cl_main.cl.predicted_origin[2] = pm.s.origin[2] * 0.125

	shared.VectorCopy(pm.viewangles, cl_main.cl.predicted_angles)
