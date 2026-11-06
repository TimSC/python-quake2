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

Quake IIs legendary physic engine.

=======================================================================
"""
from __future__ import annotations

import math
import numpy as np
from game import g_main
from game import g_utils
from game import g_monster
from game import m_move
from game.header.game import solid_t

"""
#include "header/local.h"
"""

SOLID_BSP = solid_t.SOLID_BSP.value
SOLID_NOT = solid_t.SOLID_NOT.value
from common.shared.shared import vec3_origin
from common.header.shared import EF_GIB, CHAN_AUTO, MASK_SOLID, MASK_WATER, MASK_MONSTERSOLID, MAX_EDICTS
from game.header.local import FRAMETIME, MOVETYPE_PUSH, MOVETYPE_STOP, MOVETYPE_NONE, MOVETYPE_NOCLIP, MOVETYPE_STEP, MOVETYPE_TOSS, MOVETYPE_BOUNCE, MOVETYPE_FLY, MOVETYPE_FLYMISSILE, FL_TEAMSLAVE, FL_FLY, FL_SWIM
from common.header import shared
from common.shared import shared as shared_c
from game.header import game as game_h

STOP_EPSILON = 0.1
MAX_CLIP_PLANES = 5
STOPSPEED = 100
FRICTION = 6
WATERFRICTION = 1

"""
 * pushmove objects do not obey gravity, and do not interact
 * with each other or trigger fields, but block normal movement
 * and push normal objects when they move.
 *
 * onground is set for toss objects when they come to a complete
 * rest. It is set for steping or walking objects.
 *
 * doors, plats, etc are SOLID_BSP, and MOVETYPE_PUSH
 * bonus items are SOLID_TRIGGER touch, and MOVETYPE_TOSS
 * corpses are SOLID_NOT and MOVETYPE_TOSS
 * crates are SOLID_BBOX and MOVETYPE_TOSS
 * walking monsters are SOLID_SLIDEBOX and MOVETYPE_STEP
 * flying/floating monsters are SOLID_SLIDEBOX and MOVETYPE_FLY
 *
 * solid_edge items only clip against bsp models.
"""

def SV_TestEntityPosition(ent): #edict_t * (returns static edict_t *)

	"""
	trace_t trace;
	int mask;
	"""

	if not ent:

		return None


	# dead bodies are supposed to not be solid so lets
	# ensure they only collide with BSP during pushmoves
	if ent.clipmask and not (ent.svflags & game_h.SVF_DEADMONSTER):

		mask = ent.clipmask

	else:

		mask = MASK_SOLID


	trace = g_main.gi.trace(ent.s.origin, ent.mins, ent.maxs,
			ent.s.origin, ent, mask)

	if trace.startsolid:

		return g_main.g_edicts[0]


	return None

def SV_CheckVelocity(ent): #edict_t *

	if not ent:

		return


	if shared_c.VectorLength(ent.velocity) > g_main.sv_maxvelocity.value:

		shared_c.VectorNormalize(ent.velocity)
		shared_c.VectorScale(ent.velocity, g_main.sv_maxvelocity.value, ent.velocity)

"""
 * Runs thinking code for
 * this frame if necessary
"""
def SV_RunThink(ent)->bool: #edict_t * (returns static qboolean)

	"""
	float thinktime;
	"""

	if not ent:

		return False


	thinktime = ent.nextthink

	if thinktime <= 0:

		return True


	if thinktime > g_main.level.time + 0.001:

		return True


	ent.nextthink = 0

	if ent.think:

		ent.think(ent)


	return False

"""
 * Two entities have touched, so
 * run their touch functions
"""
def SV_Impact(e1, trace): #edict_t *, trace_t *

	"""
	edict_t *e2;
	"""

	if not e1 or not trace:

		return


	e2 = trace.ent

	if e1.touch and (e1.solid != SOLID_NOT):

		e1.touch(e1, e2, trace.plane, trace.surface)


	if e2.touch and (e2.solid != SOLID_NOT):

		e2.touch(e2, e1, None, None)

"""
 * Slide off of the impacting object
 * returns the blocked flags (1 = floor,
 * 2 = step / wall)
"""
def ClipVelocity(inp, normal, out, overbounce: float)->int: #vec3_t, vec3_t, vec3_t, float (returns static int)

	"""
	float backoff;
	float change;
	int i, blocked;
	"""

	blocked = 0

	if normal[2] > 0:

		blocked |= 1 # floor


	if not normal[2]:

		blocked |= 2 # step


	backoff = shared.DotProduct(inp, normal) * overbounce

	for i in range(3):

		change = normal[i] * backoff
		out[i] = inp[i] - change

		if (out[i] > -STOP_EPSILON) and (out[i] < STOP_EPSILON):

			out[i] = 0



	return blocked

"""
 * The basic solid body movement clip
 * that slides along multiple planes
 * Returns the clipflags if the velocity
 * was modified (hit something solid)
 *
 * 1 = floor
 * 2 = wall / step
 * 4 = dead stop
"""
def SV_FlyMove(ent, time: float, mask: int)->int: #edict_t *, float, int (returns static int)

	"""
	edict_t *hit;
	int bumpcount, numbumps;
	vec3_t dir;
	float d;
	int numplanes;
	vec3_t planes[MAX_CLIP_PLANES];
	vec3_t primal_velocity, original_velocity, new_velocity;
	int i, j;
	trace_t trace;
	vec3_t end;
	float time_left;
	int blocked;
	"""

	if not ent:

		return 0


	dir = np.zeros((3,), dtype=np.float32)
	planes = [np.zeros((3,), dtype=np.float32) for _ in range(MAX_CLIP_PLANES)]
	primal_velocity = np.zeros((3,), dtype=np.float32)
	original_velocity = np.zeros((3,), dtype=np.float32)
	new_velocity = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	numbumps = 4

	blocked = 0
	shared.VectorCopy(ent.velocity, original_velocity)
	shared.VectorCopy(ent.velocity, primal_velocity)
	numplanes = 0

	time_left = time

	ent.groundentity = None

	for bumpcount in range(numbumps):

		for i in range(3):

			end[i] = ent.s.origin[i] + time_left * ent.velocity[i]


		trace = g_main.gi.trace(ent.s.origin, ent.mins, ent.maxs, end, ent, mask)

		if trace.allsolid:

			# entity is trapped in another solid
			shared.VectorCopy(vec3_origin, ent.velocity)
			return 3


		if trace.fraction > 0:

			# actually covered some distance
			shared.VectorCopy(trace.endpos, ent.s.origin)
			shared.VectorCopy(ent.velocity, original_velocity)
			numplanes = 0


		if trace.fraction == 1:

			break # moved the entire distance


		hit = trace.ent

		if trace.plane.normal[2] > 0.7:

			blocked |= 1 # floor

			if hit.solid == SOLID_BSP:

				ent.groundentity = hit
				ent.groundentity_linkcount = hit.linkcount



		if not trace.plane.normal[2]:

			blocked |= 2 # step


		# run the impact function
		SV_Impact(ent, trace)

		if not ent.inuse:

			break # removed by the impact function


		time_left -= time_left * trace.fraction

		# cliped to another plane
		if numplanes >= MAX_CLIP_PLANES:

			# this shouldn't really happen
			shared.VectorCopy(vec3_origin, ent.velocity)
			return 3


		shared.VectorCopy(trace.plane.normal, planes[numplanes])
		numplanes += 1

		# modify original_velocity so it
		# parallels all of the clip planes
		i = 0
		while i < numplanes:

			ClipVelocity(original_velocity, planes[i], new_velocity, 1)

			j = 0
			while j < numplanes:

				if (j != i) and not shared_c.VectorCompare(planes[i], planes[j]):

					if shared.DotProduct(new_velocity, planes[j]) < 0:

						break # not ok


				j += 1


			if j == numplanes:

				break

			i += 1


		if i != numplanes:

			# go along this plane
			shared.VectorCopy(new_velocity, ent.velocity)

		else:

			# go along the crease
			if numplanes != 2:

				shared.VectorCopy(vec3_origin, ent.velocity)
				return 7


			shared_c.CrossProduct(planes[0], planes[1], dir)
			d = shared.DotProduct(dir, ent.velocity)
			shared_c.VectorScale(dir, d, ent.velocity)


		# if original velocity is against the original
		# velocity, stop dead to avoid tiny occilations
		# in sloping corners
		if shared.DotProduct(ent.velocity, primal_velocity) <= 0:

			shared.VectorCopy(vec3_origin, ent.velocity)
			return blocked



	return blocked

def SV_AddGravity(ent): #edict_t *

	if not ent:

		return


	ent.velocity[2] -= ent.gravity * g_main.sv_gravity.value * FRAMETIME

"""
 * Returns the actual bounding box of a bmodel.
 * This is a big improvement over what q2 normally
 * does with rotating bmodels - q2 sets absmin,
 * absmax to a cube that will completely contain
 * the bmodel at *any* rotation on *any* axis, whether
 * the bmodel can actually rotate to that angle or not.
 * This leads to a lot of false block tests in SV_Push
 * if another bmodel is in the vicinity.
"""
def RealBoundingBox(ent, mins, maxs): #edict_t *, vec3_t, vec3_t

	"""
	vec3_t forward, left, up, f1, l1, u1;
	vec3_t p[8];
	int i, j, k, j2, k4;
	"""

	if not ent:

		return


	forward = np.zeros((3,), dtype=np.float32)
	left = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	f1 = np.zeros((3,), dtype=np.float32)
	l1 = np.zeros((3,), dtype=np.float32)
	u1 = np.zeros((3,), dtype=np.float32)
	p = [np.zeros((3,), dtype=np.float32) for _ in range(8)]

	for k in range(2):

		k4 = k * 4

		if k:

			p[k4][2] = ent.maxs[2]

		else:

			p[k4][2] = ent.mins[2]


		p[k4 + 1][2] = p[k4][2]
		p[k4 + 2][2] = p[k4][2]
		p[k4 + 3][2] = p[k4][2]

		for j in range(2):

			j2 = j * 2

			if j:

				p[j2 + k4][1] = ent.maxs[1]

			else:

				p[j2 + k4][1] = ent.mins[1]


			p[j2 + k4 + 1][1] = p[j2 + k4][1]

			for i in range(2):

				if i:

					p[i + j2 + k4][0] = ent.maxs[0]

				else:

					p[i + j2 + k4][0] = ent.mins[0]





	shared_c.AngleVectors(ent.s.angles, forward, left, up)

	for i in range(8):

		shared_c.VectorScale(forward, p[i][0], f1)
		shared_c.VectorScale(left, -p[i][1], l1)
		shared_c.VectorScale(up, p[i][2], u1)
		shared.VectorAdd(ent.s.origin, f1, p[i])
		shared.VectorAdd(p[i], l1, p[i])
		shared.VectorAdd(p[i], u1, p[i])


	shared.VectorCopy(p[0], mins)
	shared.VectorCopy(p[0], maxs)

	for i in range(1, 8):

		if mins[0] > p[i][0]:

			mins[0] = p[i][0]


		if mins[1] > p[i][1]:

			mins[1] = p[i][1]


		if mins[2] > p[i][2]:

			mins[2] = p[i][2]


		if maxs[0] < p[i][0]:

			maxs[0] = p[i][0]


		if maxs[1] < p[i][1]:

			maxs[1] = p[i][1]


		if maxs[2] < p[i][2]:

			maxs[2] = p[i][2]

# ==================================================================

# PUSHMOVE

"""
 * Does not change the entities velocity at all
"""
def SV_PushEntity(ent, push): #edict_t *, vec3_t (returns static trace_t)

	"""
	trace_t trace;
	vec3_t start;
	vec3_t end;
	int mask;
	"""

	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	shared.VectorCopy(ent.s.origin, start)
	shared.VectorAdd(start, push, end)

	while True: #retry:

		if ent.clipmask:

			mask = ent.clipmask

		else:

			mask = MASK_SOLID


		trace = g_main.gi.trace(start, ent.mins, ent.maxs, end, ent, mask)

		# startsolid treats different-content volumes
		# as continuous, like the bbox of a monster/player
		# and the floor of an elevator. So do another trace
		# that only collides with BSP so that we make a best
		# effort to keep these entities inside non-solid space
		if trace.startsolid and (mask & ~MASK_SOLID):

			trace = g_main.gi.trace(start, ent.mins, ent.maxs, end, ent, MASK_SOLID)


		shared.VectorCopy(trace.endpos, ent.s.origin)
		g_main.gi.linkentity(ent)

		# Push slightly away from non-horizontal surfaces,
		# prevent origin stuck in the plane which causes
		# the entity to be rendered in full black.
		if trace.plane.type != 2:

			# Limit the fix to gibs, debris and dead monsters.
			# Everything else may break existing maps. Items
			# may slide to unreachable locations, monsters may
			# get stuck, etc.
			if ((ent.classname[:8] == "monster_") and ent.health < 1) or \
					(ent.classname == "debris") or (ent.s.effects & EF_GIB):

				shared.VectorAdd(ent.s.origin, trace.plane.normal, ent.s.origin)



		if trace.fraction != 1.0:

			SV_Impact(ent, trace)

			# if the pushed entity went away
			# and the pusher is still there
			if not trace.ent.inuse and ent.inuse:

				# move the pusher back and try again
				shared.VectorCopy(start, ent.s.origin)
				g_main.gi.linkentity(ent)
				continue #goto retry;



		break


	if ent.inuse:

		g_utils.G_TouchTriggers(ent)


	return trace

"""
 * Pushed API
"""
class pushed_t(object):

	def __init__(self):

		self.ent = None #edict_t *
		self.origin = np.zeros((3,), dtype=np.float32) #vec3_t
		self.angles = np.zeros((3,), dtype=np.float32) #vec3_t

pushed = [pushed_t() for _ in range(MAX_EDICTS)] #static pushed_t [MAX_EDICTS]
pushed_p = 0 #static pushed_t *, Q2PORT: an index into pushed

def Pushed_Init(): #void

	global pushed_p

	pushed_p = 0

def Pushed_Append(e)->bool: #edict_t * (returns static qboolean)

	global pushed_p

	if pushed_p >= len(pushed): #ARREND(pushed)

		return False


	pushed[pushed_p].ent = e
	shared.VectorCopy(e.s.origin, pushed[pushed_p].origin)
	shared.VectorCopy(e.s.angles, pushed[pushed_p].angles)

	pushed_p += 1

	return True

def Pushed_Pop(): #void

	global pushed_p

	if pushed_p > 0:

		pushed_p -= 1

def Pushed_Undo(): #void

	global pushed_p

	"""
	pushed_t *p;
	"""

	# go backwards, so if the same entity was pushed
	# twice, it goes back to the original position
	for k in range(pushed_p - 1, -1, -1):

		p = pushed[k]
		shared.VectorCopy(p.origin, p.ent.s.origin)
		shared.VectorCopy(p.angles, p.ent.s.angles)

		g_main.gi.linkentity(p.ent)


	pushed_p = 0

def Pushed_TouchTriggers(): #void

	"""
	pushed_t *p;
	"""

	for k in range(pushed_p - 1, -1, -1):

		g_utils.G_TouchTriggers(pushed[k].ent)

"""
 * Objects need to be moved back on a failed push,
 * otherwise riders would continue to slide.
"""
def SV_Push(pusher, move, amove): #edict_t *, vec3_t, vec3_t (returns static edict_t *)

	"""
	int i;
	edict_t *check;
	vec3_t org, forward, right, up;
	vec3_t realmins, realmaxs;
	"""

	if not pusher:

		return None


	org = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	realmins = np.zeros((3,), dtype=np.float32)
	realmaxs = np.zeros((3,), dtype=np.float32)

	# clamp the move to 1/8 units, so the position will
	# be accurate for client side prediction
	for i in range(3):

		#float temp;
		temp = move[i] * 8.0

		if temp > 0.0:

			temp += 0.5

		else:

			temp -= 0.5


		move[i] = 0.125 * int(temp)


	# we need this for pushing things later
	shared.VectorSubtract(vec3_origin, amove, org)
	shared_c.AngleVectors(org, forward, right, up)

	if not Pushed_Append(pusher):

		return None


	shared.VectorAdd(pusher.s.origin, move, pusher.s.origin)
	shared.VectorAdd(pusher.s.angles, amove, pusher.s.angles)
	g_main.gi.linkentity(pusher)

	# Create a real bounding box for
	# rotating brush models.
	RealBoundingBox(pusher, realmins, realmaxs)

	# see if any solid entities
	# are inside the final position
	for e in range(1, g_main.glob.num_edicts):

		check = g_main.g_edicts[e]

		if not check.inuse:

			continue


		if (check.movetype == MOVETYPE_PUSH) or \
			(check.movetype == MOVETYPE_STOP) or \
			(check.movetype == MOVETYPE_NONE) or \
			(check.movetype == MOVETYPE_NOCLIP):

			continue


		if not check.area.prev:

			continue # not linked in anywhere


		# if the entity is standing on the pusher,
		# it will definitely be moved
		if check.groundentity != pusher:

			# see if the ent needs to be tested
			if (check.absmin[0] >= realmaxs[0]) or \
				(check.absmin[1] >= realmaxs[1]) or \
				(check.absmin[2] >= realmaxs[2]) or \
				(check.absmax[0] <= realmins[0]) or \
				(check.absmax[1] <= realmins[1]) or \
				(check.absmax[2] <= realmins[2]):

				continue


			# see if the ent's bbox is inside
			# the pusher's final position
			if not SV_TestEntityPosition(check):

				continue



		if (pusher.movetype == MOVETYPE_PUSH) or \
			(check.groundentity == pusher):

			#vec3_t org2, move2;
			org2 = np.zeros((3,), dtype=np.float32)
			move2 = np.zeros((3,), dtype=np.float32)

			if not Pushed_Append(check):

				continue


			# try moving the contacted entity
			shared.VectorAdd(check.s.origin, move, check.s.origin)

			# figure movement due to the pusher's amove
			shared.VectorSubtract(check.s.origin, pusher.s.origin, org)
			org2[0] = shared.DotProduct(org, forward)
			org2[1] = -shared.DotProduct(org, right)
			org2[2] = shared.DotProduct(org, up)
			shared.VectorSubtract(org2, org, move2)
			shared.VectorAdd(check.s.origin, move2, check.s.origin)

			# may have pushed them off an edge
			if check.groundentity != pusher:

				check.groundentity = None


			if not SV_TestEntityPosition(check):

				g_main.gi.linkentity(check)
				continue


			# if it is ok to leave in the old position, do it
			# this is only relevent for riding entities, not
			# pushed
			shared.VectorSubtract(check.s.origin, move, check.s.origin)

			if not SV_TestEntityPosition(check):

				Pushed_Pop()
				continue



		Pushed_Undo()

		return check


	Pushed_TouchTriggers()

	return None

"""
 * Bmodel objects don't interact with each
 * other, but push all box objects
"""
def SV_Physics_Pusher(ent): #edict_t *

	"""
	edict_t *part, *obstacle;
	"""

	if not ent:

		return


	# if not a team captain, so movement
	# will be handled elsewhere
	if ent.flags & FL_TEAMSLAVE:

		return


	Pushed_Init()
	obstacle = None

	move = np.zeros((3,), dtype=np.float32)
	amove = np.zeros((3,), dtype=np.float32)

	# make sure all team slaves can move before commiting
	# any moves or calling any think functions if the move
	# is blocked, all moved objects will be backed out
	part = ent
	while part:

		#vec3_t move, amove;

		if shared_c.VectorCompare(part.velocity, vec3_origin) and \
			shared_c.VectorCompare(part.avelocity, vec3_origin):

			part = part.teamchain
			continue


		shared_c.VectorScale(part.velocity, FRAMETIME, move)
		shared_c.VectorScale(part.avelocity, FRAMETIME, amove)

		obstacle = SV_Push(part, move, amove)
		if obstacle:

			break

		part = part.teamchain


	if part: # move failed

		#edict_t *mv;

		mv = ent
		while mv:

			if mv.nextthink > 0:

				mv.nextthink += FRAMETIME

			mv = mv.teamchain


		if part.blocked:

			part.blocked(part, obstacle)


	else:

		part = ent
		while part:

			SV_RunThink(part)
			part = part.teamchain

# ==================================================================

"""
 * Non moving objects can only think
"""
def SV_Physics_None(ent): #edict_t *

	if not ent:

		return


	SV_RunThink(ent)

"""
 * A moving object that doesn't obey physics
"""
def SV_Physics_Noclip(ent): #edict_t *

	if not ent:

		return


	if not SV_RunThink(ent):

		return


	shared_c.VectorMA(ent.s.angles, FRAMETIME, ent.avelocity, ent.s.angles)
	shared_c.VectorMA(ent.s.origin, FRAMETIME, ent.velocity, ent.s.origin)

	g_main.gi.linkentity(ent)

# ==================================================================

# TOSS / BOUNCE

"""
 * Toss, bounce, and fly movement.
 * When onground, do nothing.
"""
def SV_Physics_Toss(ent): #edict_t *

	"""
	trace_t trace;
	vec3_t move;
	float backoff;
	edict_t *slave;
	qboolean wasinwater;
	qboolean isinwater;
	vec3_t old_origin;
	"""

	if not ent:

		return


	move = np.zeros((3,), dtype=np.float32)
	old_origin = np.zeros((3,), dtype=np.float32)

	SV_RunThink(ent)

	# entities are very often freed during thinking
	if not ent.inuse:

		return


	# if not a team captain, so movement
	# will be handled elsewhere
	if ent.flags & FL_TEAMSLAVE:

		return


	if ent.velocity[2] > 0:

		ent.groundentity = None


	# check for the groundentity going away
	if ent.groundentity:

		if not ent.groundentity.inuse:

			ent.groundentity = None



	# if onground, return without moving
	if ent.groundentity:

		return


	shared.VectorCopy(ent.s.origin, old_origin)

	SV_CheckVelocity(ent)

	# add gravity
	if (ent.movetype != MOVETYPE_FLY) and \
		(ent.movetype != MOVETYPE_FLYMISSILE):

		SV_AddGravity(ent)


	# move angles
	shared_c.VectorMA(ent.s.angles, FRAMETIME, ent.avelocity, ent.s.angles)

	# move origin
	shared_c.VectorScale(ent.velocity, FRAMETIME, move)
	trace = SV_PushEntity(ent, move)

	if not ent.inuse:

		return


	if trace.fraction < 1:

		if ent.movetype == MOVETYPE_BOUNCE:

			backoff = 1.5

		else:

			backoff = 1


		ClipVelocity(ent.velocity, trace.plane.normal, ent.velocity, backoff)

		# stop if on ground
		if trace.plane.normal[2] > 0.7:

			if (ent.velocity[2] < 60) or (ent.movetype != MOVETYPE_BOUNCE):

				ent.groundentity = trace.ent
				ent.groundentity_linkcount = trace.ent.linkcount
				shared.VectorCopy(vec3_origin, ent.velocity)
				shared.VectorCopy(vec3_origin, ent.avelocity)




	# check for water transition
	wasinwater = (ent.watertype & MASK_WATER)
	ent.watertype = g_main.gi.pointcontents(ent.s.origin)
	isinwater = ent.watertype & MASK_WATER

	if isinwater:

		ent.waterlevel = 1

	else:

		ent.waterlevel = 0


	if not wasinwater and isinwater:

		# don't play splash sound for entities already in water on level start
		if g_main.level.framenum > 3:

			g_main.gi.positioned_sound(old_origin, g_main.g_edicts[0], CHAN_AUTO,
					g_main.gi.soundindex("misc/h2ohit1.wav"), 1, 1, 0)


	elif wasinwater and not isinwater:

		g_main.gi.positioned_sound(ent.s.origin, g_main.g_edicts[0], CHAN_AUTO,
				g_main.gi.soundindex("misc/h2ohit1.wav"), 1, 1, 0)


	# move teamslaves
	slave = ent.teamchain
	while slave:

		shared.VectorCopy(ent.s.origin, slave.s.origin)
		g_main.gi.linkentity(slave)
		slave = slave.teamchain

# ==================================================================

# STEPPING MOVEMENT

"""
 * Monsters freefall when they don't have a ground
 * entity, otherwise all movement is done with
 * discrete steps.
 *
 * This is also used for objects that have become
 * still on the ground, but  will fall if the floor
 * is pulled out from under them.
"""
def SV_AddRotationalFriction(ent): #edict_t *

	"""
	int n;
	float adjustment;
	"""

	if not ent:

		return


	shared_c.VectorMA(ent.s.angles, FRAMETIME, ent.avelocity, ent.s.angles)
	adjustment = FRAMETIME * STOPSPEED * FRICTION

	for n in range(3):

		if ent.avelocity[n] > 0:

			ent.avelocity[n] -= adjustment

			if ent.avelocity[n] < 0:

				ent.avelocity[n] = 0


		else:

			ent.avelocity[n] += adjustment

			if ent.avelocity[n] > 0:

				ent.avelocity[n] = 0

def SV_Physics_Step(ent): #edict_t *

	"""
	qboolean wasonground;
	qboolean hitsound = false;
	float *vel;
	float speed, newspeed, control;
	float friction;
	edict_t *groundentity;
	int mask;
	vec3_t oldorig;
	trace_t tr;
	"""
	hitsound = False

	if not ent:

		return


	oldorig = np.zeros((3,), dtype=np.float32)

	# airborn monsters should always check for ground
	if not ent.groundentity:

		g_monster.M_CheckGround(ent)


	groundentity = ent.groundentity

	SV_CheckVelocity(ent)

	if groundentity:

		wasonground = True

	else:

		wasonground = False


	if ent.avelocity[0] or ent.avelocity[1] or ent.avelocity[2]:

		SV_AddRotationalFriction(ent)


	# add gravity except:
	#   flying monsters
	#   swimming monsters who are in the water
	if not wasonground:

		if not (ent.flags & FL_FLY):

			if not ((ent.flags & FL_SWIM) and (ent.waterlevel > 2)):

				if ent.velocity[2] < g_main.sv_gravity.value * -0.1:

					hitsound = True


				if ent.waterlevel == 0:

					SV_AddGravity(ent)





	# friction for flying monsters that have been given vertical velocity
	if (ent.flags & FL_FLY) and (ent.velocity[2] != 0):

		speed = abs(ent.velocity[2])
		control = STOPSPEED if speed < STOPSPEED else speed
		friction = FRICTION / 3
		newspeed = speed - (FRAMETIME * control * friction)

		if newspeed < 0:

			newspeed = 0


		newspeed /= speed
		ent.velocity[2] *= newspeed


	# friction for flying monsters that have been given vertical velocity
	if (ent.flags & FL_SWIM) and (ent.velocity[2] != 0):

		speed = abs(ent.velocity[2])
		control = STOPSPEED if speed < STOPSPEED else speed
		newspeed = speed - (FRAMETIME * control * WATERFRICTION * ent.waterlevel)

		if newspeed < 0:

			newspeed = 0


		newspeed /= speed
		ent.velocity[2] *= newspeed


	if ent.velocity[2] or ent.velocity[1] or ent.velocity[0]:

		# apply friction: let dead monsters who
		# aren't completely onground slide
		if (wasonground) or (ent.flags & (FL_SWIM | FL_FLY)):

			if not ((ent.health <= 0.0) and not m_move.M_CheckBottom(ent)):

				vel = ent.velocity
				speed = math.sqrt(vel[0] * vel[0] + vel[1] * vel[1])

				if speed:

					friction = FRICTION

					control = STOPSPEED if speed < STOPSPEED else speed
					newspeed = speed - FRAMETIME * control * friction

					if newspeed < 0:

						newspeed = 0


					newspeed /= speed

					vel[0] *= newspeed
					vel[1] *= newspeed




		if ent.svflags & game_h.SVF_MONSTER:

			mask = MASK_MONSTERSOLID

		else:

			mask = MASK_SOLID


		shared.VectorCopy(ent.s.origin, oldorig)
		SV_FlyMove(ent, FRAMETIME, mask)

		# Evil hack to work around dead parasites (and maybe other monster)
		# falling through the worldmodel into the void. We copy the current
		# origin (see above) and after the SV_FlyMove() was performend we
		# checl if we're stuck in the world model. If yes we're undoing the
		# move.
		if not shared_c.VectorCompare(ent.s.origin, oldorig):

			tr = g_main.gi.trace(ent.s.origin, ent.mins, ent.maxs, ent.s.origin, ent, mask)

			if tr.startsolid:

				shared.VectorCopy(oldorig, ent.s.origin)



		g_main.gi.linkentity(ent)
		g_utils.G_TouchTriggers(ent)

		if not ent.inuse:

			return


		if ent.groundentity:

			if not wasonground:

				if hitsound:

					g_main.gi.sound(ent, 0, g_main.gi.soundindex("world/land.wav"), 1, 1, 0)





	SV_RunThink(ent)

# ==================================================================

def G_RunEntity(ent): #edict_t *

	if not ent:

		return


	if ent.prethink:

		ent.prethink(ent)


	movetype = int(ent.movetype)
	if movetype == MOVETYPE_PUSH or movetype == MOVETYPE_STOP:
		SV_Physics_Pusher(ent)
	elif movetype == MOVETYPE_NONE:
		SV_Physics_None(ent)
	elif movetype == MOVETYPE_NOCLIP:
		SV_Physics_Noclip(ent)
	elif movetype == MOVETYPE_STEP:
		SV_Physics_Step(ent)
	elif movetype == MOVETYPE_TOSS or \
		movetype == MOVETYPE_BOUNCE or \
		movetype == MOVETYPE_FLY or \
		movetype == MOVETYPE_FLYMISSILE:
		SV_Physics_Toss(ent)
	else:
		g_main.gi.dprintf("%s:%d has bad movetype: %d\n",
			ent.classname, ent.s.number, ent.movetype)
		ent.movetype = MOVETYPE_NONE
		SV_Physics_None(ent)
