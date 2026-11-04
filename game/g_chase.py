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
import numpy as np
from game import q_shared, g_main
from game.q_shared import pmtype_t
from game.q_shared import (PMF_NO_PREDICTION, MASK_SOLID, ANGLE2SHORT, PITCH,
	YAW, ROLL, vec3_origin, VectorCopy, VectorMA, VectorNormalize, AngleVectors)
"""
/*
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

*/
#include "g_local.h"





"""

def UpdateChaseCam (ent):
	ownerv = np.zeros((3,), dtype=np.float32)
	oldgoal = np.zeros((3,), dtype=np.float32)
	angles = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	o = np.zeros((3,), dtype=np.float32)
	goal = np.zeros((3,), dtype=np.float32)

	# is our chase target gone?
	if (not ent.client.chase_target.inuse \
		or ent.client.chase_target.client.resp.spectator):
		old = ent.client.chase_target
		ChaseNext(ent)
		if ent.client.chase_target is old:
			ent.client.chase_target = None
			ent.client.ps.pmove.pm_flags &= ~PMF_NO_PREDICTION
			return

	targ = ent.client.chase_target

	VectorCopy(targ.s.origin, ownerv)
	VectorCopy(ent.s.origin, oldgoal)

	ownerv[2] += targ.viewheight

	VectorCopy(targ.client.v_angle, angles)
	if angles[PITCH] > 56:
		angles[PITCH] = 56
	AngleVectors (angles, forward, right, None)
	VectorNormalize(forward)
	VectorMA(ownerv, -30, forward, o)

	if o[2] < targ.s.origin[2] + 20:
		o[2] = targ.s.origin[2] + 20

	# jump animation lifts
	if not targ.groundentity:
		o[2] += 16

	trace = g_main.gi.trace(ownerv, vec3_origin, vec3_origin, o, targ, MASK_SOLID)

	VectorCopy(trace.endpos, goal)

	VectorMA(goal, 2, forward, goal)

	# pad for floors and ceilings
	VectorCopy(goal, o)
	o[2] += 6
	trace = g_main.gi.trace(goal, vec3_origin, vec3_origin, o, targ, MASK_SOLID)
	if trace.fraction < 1:
		VectorCopy(trace.endpos, goal)
		goal[2] -= 6

	VectorCopy(goal, o)
	o[2] -= 6
	trace = g_main.gi.trace(goal, vec3_origin, vec3_origin, o, targ, MASK_SOLID)
	if trace.fraction < 1:
		VectorCopy(trace.endpos, goal)
		goal[2] += 6

	if targ.deadflag:
		ent.client.ps.pmove.pm_type = pmtype_t.PM_DEAD.value
	else:
		ent.client.ps.pmove.pm_type = pmtype_t.PM_FREEZE.value

	VectorCopy(goal, ent.s.origin)
	for i in range(3):
		ent.client.ps.pmove.delta_angles[i] = ANGLE2SHORT(targ.client.v_angle[i] - ent.client.resp.cmd_angles[i])

	if targ.deadflag:
		ent.client.ps.viewangles[ROLL] = 40
		ent.client.ps.viewangles[PITCH] = -15
		ent.client.ps.viewangles[YAW] = targ.client.killer_yaw
	else:
		VectorCopy(targ.client.v_angle, ent.client.ps.viewangles)
		VectorCopy(targ.client.v_angle, ent.client.v_angle)

	ent.viewheight = 0
	ent.client.ps.pmove.pm_flags |= PMF_NO_PREDICTION
	g_main.gi.linkentity(ent)
	"""
	void UpdateChaseCam(edict_t *ent)
	{
		vec3_t o, ownerv, goal;
		edict_t *targ;
		vec3_t forward, right;
		trace_t trace;
		int i;
		vec3_t oldgoal;
		vec3_t angles;
	
		// is our chase target gone?
		if (!ent->client->chase_target->inuse
			|| ent->client->chase_target->client->resp.spectator) {
			edict_t *old = ent->client->chase_target;
			ChaseNext(ent);
			if (ent->client->chase_target == old) {
				ent->client->chase_target = NULL;
				ent->client->ps.pmove.pm_flags &= ~PMF_NO_PREDICTION;
				return;
			}
		}
	
		targ = ent->client->chase_target;
	
		VectorCopy(targ->s.origin, ownerv);
		VectorCopy(ent->s.origin, oldgoal);
	
		ownerv[2] += targ->viewheight;
	
		VectorCopy(targ->client->v_angle, angles);
		if (angles[PITCH] > 56)
			angles[PITCH] = 56;
		AngleVectors (angles, forward, right, NULL);
		VectorNormalize(forward);
		VectorMA(ownerv, -30, forward, o);
	
		if (o[2] < targ->s.origin[2] + 20)
			o[2] = targ->s.origin[2] + 20;
	
		// jump animation lifts
		if (!targ->groundentity)
			o[2] += 16;
	
		trace = gi.trace(ownerv, vec3_origin, vec3_origin, o, targ, MASK_SOLID);
	
		VectorCopy(trace.endpos, goal);
	
		VectorMA(goal, 2, forward, goal);
	
		// pad for floors and ceilings
		VectorCopy(goal, o);
		o[2] += 6;
		trace = gi.trace(goal, vec3_origin, vec3_origin, o, targ, MASK_SOLID);
		if (trace.fraction < 1) {
			VectorCopy(trace.endpos, goal);
			goal[2] -= 6;
		}
	
		VectorCopy(goal, o);
		o[2] -= 6;
		trace = gi.trace(goal, vec3_origin, vec3_origin, o, targ, MASK_SOLID);
		if (trace.fraction < 1) {
			VectorCopy(trace.endpos, goal);
			goal[2] += 6;
		}
	
		if (targ->deadflag)
			ent->client->ps.pmove.pm_type = PM_DEAD;
		else
			ent->client->ps.pmove.pm_type = PM_FREEZE;
	
		VectorCopy(goal, ent->s.origin);
		for (i=0 ; i<3 ; i++)
			ent->client->ps.pmove.delta_angles[i] = ANGLE2SHORT(targ->client->v_angle[i] - ent->client->resp.cmd_angles[i]);
	
		if (targ->deadflag) {
			ent->client->ps.viewangles[ROLL] = 40;
			ent->client->ps.viewangles[PITCH] = -15;
			ent->client->ps.viewangles[YAW] = targ->client->killer_yaw;
		} else {
			VectorCopy(targ->client->v_angle, ent->client->ps.viewangles);
			VectorCopy(targ->client->v_angle, ent->client->v_angle);
		}
	
		ent->viewheight = 0;
		ent->client->ps.pmove.pm_flags |= PMF_NO_PREDICTION;
		gi.linkentity(ent);
	}
	"""

def ChaseNext (ent):
	if not ent.client.chase_target:
		return

	i = g_main.g_edicts.index(ent.client.chase_target)
	while True:
		i += 1
		if i > int(g_main.maxclients.value):
			i = 1
		e = g_main.g_edicts[i]
		if not e.inuse:
			continue
		if not e.client.resp.spectator:
			break
		if e is ent.client.chase_target:
			break

	ent.client.chase_target = e
	ent.client.update_chase = True
	"""
	void ChaseNext(edict_t *ent)
	{
		int i;
		edict_t *e;
	
		if (!ent->client->chase_target)
			return;
	
		i = ent->client->chase_target - g_edicts;
		do {
			i++;
			if (i > maxclients->value)
				i = 1;
			e = g_edicts + i;
			if (!e->inuse)
				continue;
			if (!e->client->resp.spectator)
				break;
		} while (e != ent->client->chase_target);
	
		ent->client->chase_target = e;
		ent->client->update_chase = true;
	}
	"""

def ChasePrev (ent):
	if not ent.client.chase_target:
		return

	i = g_main.g_edicts.index(ent.client.chase_target)
	while True:
		i -= 1
		if i < 1:
			i = int(g_main.maxclients.value)
		e = g_main.g_edicts[i]
		if not e.inuse:
			continue
		if not e.client.resp.spectator:
			break
		if e is ent.client.chase_target:
			break

	ent.client.chase_target = e
	ent.client.update_chase = True
	"""
	void ChasePrev(edict_t *ent)
	{
		int i;
		edict_t *e;
	
		if (!ent->client->chase_target)
			return;
	
		i = ent->client->chase_target - g_edicts;
		do {
			i--;
			if (i < 1)
				i = maxclients->value;
			e = g_edicts + i;
			if (!e->inuse)
				continue;
			if (!e->client->resp.spectator)
				break;
		} while (e != ent->client->chase_target);
	
		ent->client->chase_target = e;
		ent->client->update_chase = true;
	}
	"""

def GetChaseTarget (ent):
	for i in range(1, int(g_main.maxclients.value)+1):
		other = g_main.g_edicts[i]
		if other.inuse and not other.client.resp.spectator:
			ent.client.chase_target = other
			ent.client.update_chase = True
			UpdateChaseCam(ent)
			return
	g_main.gi.centerprintf(ent, "No other players to chase.")
	"""
	void GetChaseTarget(edict_t *ent)
	{
		int i;
		edict_t *other;
	
		for (i = 1; i <= maxclients->value; i++) {
			other = g_edicts + i;
			if (other->inuse && !other->client->resp.spectator) {
				ent->client->chase_target = other;
				ent->client->update_chase = true;
				UpdateChaseCam(ent);
				return;
			}
		}
		gi.centerprintf(ent, "No other players to chase.");
	}
	"""
