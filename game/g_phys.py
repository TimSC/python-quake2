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
import math
import qcommon
from game import q_shared
from game import g_local
from game import g_main
from game import g_utils
from game import g_monster
from game import m_move
from game import game
from game.game import solid_t
SOLID_BSP = solid_t.SOLID_BSP.value
SOLID_NOT = solid_t.SOLID_NOT.value
from game.q_shared import (vec3_origin, YAW, CHAN_AUTO, MASK_SOLID,
	MASK_WATER, MASK_MONSTERSOLID, MAX_EDICTS)
from game.g_local import (FRAMETIME, MOVETYPE_PUSH, MOVETYPE_STOP,
	MOVETYPE_NONE, MOVETYPE_NOCLIP, MOVETYPE_STEP, MOVETYPE_TOSS,
	MOVETYPE_BOUNCE, MOVETYPE_FLY, MOVETYPE_FLYMISSILE, FL_TEAMSLAVE,
	FL_FLY, FL_SWIM)

"""
// g_phys.c

#include "g_local.h"
"""

STOP_EPSILON = 0.1
MAX_CLIP_PLANES = 5
sv_stopspeed = 100
sv_friction = 6
sv_waterfriction = 1


class pushed_t(object):
	def __init__(self):
		self.ent = None
		self.origin = [0, 0, 0]
		self.angles = [0, 0, 0]
		self.deltayaw = 0.0

pushed = [pushed_t() for _ in range(MAX_EDICTS)]
pushed_p = 0
obstacle = None

"""
============
SV_TestEntityPosition
============
"""
def SV_TestEntityPosition (ent):
	#trace_t trace
	#int mask
	if ent.clipmask:
		mask = ent.clipmask
	else:
		mask = MASK_SOLID
	trace = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, ent.s.origin, ent, mask)

	if trace.startsolid:
		return g_main.g_edicts[0]

	return None


"""
================
SV_CheckVelocity
================
"""
def SV_CheckVelocity (ent):
	#int i
	for i in range(3):
		if ent.velocity[i] > g_main.sv_maxvelocity.value:
			ent.velocity[i] = g_main.sv_maxvelocity.value
		elif ent.velocity[i] < -g_main.sv_maxvelocity.value:
			ent.velocity[i] = -g_main.sv_maxvelocity.value


"""
=============
SV_RunThink

Runs thinking code for this frame if necessary
=============
"""
def SV_RunThink (ent):
	#float thinktime
	thinktime = ent.nextthink
	if thinktime <= 0:
		return True
	if thinktime > g_main.level.time+0.001:
		return True

	ent.nextthink = 0
	if not ent.think:
		g_main.gi.error ("NULL ent->think")
	ent.think (ent)

	return False


"""
==================
SV_Impact

Two entities have touched, so run their touch functions
==================
"""
def SV_Impact (e1, trace):
	#edict_t *e2
	e2 = trace.ent

	if e1.touch and e1.solid != SOLID_NOT:
		e1.touch (e1, e2, trace.plane, trace.surface)

	if e2.touch and e2.solid != SOLID_NOT:
		e2.touch (e2, e1, None, None)


"""
==================
ClipVelocity

Slide off of the impacting object
returns the blocked flags (1 = floor, 2 = step / wall)
==================
"""
def ClipVelocity (in_, normal, out, overbounce):
	#float backoff, change
	#int i, blocked
	blocked = 0
	if normal[2] > 0:
		blocked |= 1		# floor
	if not normal[2]:
		blocked |= 2		# step

	backoff = q_shared.DotProduct (in_, normal) * overbounce

	for i in range(3):
		change = normal[i]*backoff
		out[i] = in_[i] - change
		if out[i] > -STOP_EPSILON and out[i] < STOP_EPSILON:
			out[i] = 0

	return blocked


"""
============
SV_FlyMove

The basic solid body movement clip that slides along multiple planes
============
"""
def SV_FlyMove (ent, time, mask):
	#edict_t *hit
	#int bumpcount, numbumps
	#vec3_t dir, planes, primal_velocity, original_velocity, new_velocity, end
	#float d, time_left
	#int numplanes, blocked, i, j
	dir = [0, 0, 0]
	planes = [[0, 0, 0] for _ in range(MAX_CLIP_PLANES)]
	primal_velocity = [0, 0, 0]
	original_velocity = [0, 0, 0]
	new_velocity = [0, 0, 0]
	end = [0, 0, 0]

	numbumps = 4

	blocked = 0
	q_shared.VectorCopy (ent.velocity, original_velocity)
	q_shared.VectorCopy (ent.velocity, primal_velocity)
	numplanes = 0

	time_left = time

	ent.groundentity = None
	for bumpcount in range(numbumps):
		for i in range(3):
			end[i] = ent.s.origin[i] + time_left * ent.velocity[i]

		trace = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, end, ent, mask)

		if trace.allsolid:
			# entity is trapped in another solid
			q_shared.VectorCopy (vec3_origin, ent.velocity)
			return 3

		if trace.fraction > 0:
			# actually covered some distance
			q_shared.VectorCopy (trace.endpos, ent.s.origin)
			q_shared.VectorCopy (ent.velocity, original_velocity)
			numplanes = 0

		if trace.fraction == 1:
			 break		# moved the entire distance

		hit = trace.ent

		if trace.plane.normal[2] > 0.7:
			blocked |= 1		# floor
			if hit.solid == SOLID_BSP:
				ent.groundentity = hit
				ent.groundentity_linkcount = hit.linkcount
		if not trace.plane.normal[2]:
			blocked |= 2		# step

		#
		# run the impact function
		#
		SV_Impact (ent, trace)
		if not ent.inuse:
			break		# removed by the impact function

		time_left -= time_left * trace.fraction

		# cliped to another plane
		if numplanes >= MAX_CLIP_PLANES:
			# this shouldn't really happen
			q_shared.VectorCopy (vec3_origin, ent.velocity)
			return 3

		q_shared.VectorCopy (trace.plane.normal, planes[numplanes])
		numplanes += 1

		#
		# modify original_velocity so it parallels all of the clip planes
		#
		for i in range(numplanes):
			ClipVelocity (original_velocity, planes[i], new_velocity, 1)

			for j in range(numplanes):
				if (j != i) and not q_shared.VectorCompare (planes[i], planes[j]):
					if q_shared.DotProduct (new_velocity, planes[j]) < 0:
						break	# not ok
			if j == numplanes:
				break

		if i != numplanes:
			# go along this plane
			q_shared.VectorCopy (new_velocity, ent.velocity)
		else:
			# go along the crease
			if numplanes != 2:
				q_shared.VectorCopy (vec3_origin, ent.velocity)
				return 7
			q_shared.CrossProduct (planes[0], planes[1], dir)
			d = q_shared.DotProduct (dir, ent.velocity)
			q_shared.VectorScale (dir, d, ent.velocity)

		#
		# if original velocity is against the original velocity, stop dead
		# to avoid tiny occilations in sloping corners
		#
		if q_shared.DotProduct (ent.velocity, primal_velocity) <= 0:

			q_shared.VectorCopy (vec3_origin, ent.velocity)
			return blocked

	return blocked


"""
============
SV_AddGravity
============
"""
def SV_AddGravity (ent):
	ent.velocity[2] -= ent.gravity * g_main.sv_gravity.value * FRAMETIME


"""
===============================================================================

PUSHMOVE

===============================================================================
"""

"""
============
SV_PushEntity

Does not change the entities velocity at all
============
"""
def SV_PushEntity (ent, push):
	#trace_t trace
	#vec3_t start, end
	#int mask
	start = [0, 0, 0]
	end = [0, 0, 0]

	q_shared.VectorCopy (ent.s.origin, start)
	q_shared.VectorAdd (start, push, end)

	while True:
		if ent.clipmask:
			mask = ent.clipmask
		else:
			mask = MASK_SOLID

		trace = g_main.gi.trace (start, ent.mins, ent.maxs, end, ent, mask)

		q_shared.VectorCopy (trace.endpos, ent.s.origin)
		g_main.gi.linkentity (ent)

		if trace.fraction != 1.0:
			SV_Impact (ent, trace)

			# if the pushed entity went away and the pusher is still there
			if not trace.ent.inuse and ent.inuse:
				# move the pusher back and try again
				q_shared.VectorCopy (start, ent.s.origin)
				g_main.gi.linkentity (ent)
				continue
		break

	if ent.inuse:
		g_utils.G_TouchTriggers (ent)

	return trace


"""
============
SV_Push

Objects need to be moved back on a failed push
============
"""
def SV_Push (pusher, move, amove):
	#int i, e
	#edict_t *check, *block
	#vec3_t mins, maxs, org, org2, move2, forward, right, up
	#pushed_t *p
	mins = [0, 0, 0]
	maxs = [0, 0, 0]
	org = [0, 0, 0]
	org2 = [0, 0, 0]
	move2 = [0, 0, 0]
	forward = [0, 0, 0]
	right = [0, 0, 0]
	up = [0, 0, 0]

	global pushed_p

	# clamp the move to 1/8 units, so the position will
	# be accurate for client side prediction
	for i in range(3):
		temp = move[i]*8.0
		if temp > 0.0:
			temp += 0.5
		else:
			temp -= 0.5
		move[i] = 0.125 * int(temp)

	# find the bounding box
	for i in range(3):
		mins[i] = pusher.absmin[i] + move[i]
		maxs[i] = pusher.absmax[i] + move[i]

	# we need this for pushing things later
	q_shared.VectorSubtract (vec3_origin, amove, org)
	q_shared.AngleVectors (org, forward, right, up)

	# save the pusher's original position
	pushed[pushed_p].ent = pusher
	q_shared.VectorCopy (pusher.s.origin, pushed[pushed_p].origin)
	q_shared.VectorCopy (pusher.s.angles, pushed[pushed_p].angles)
	if pusher.client:
		pushed[pushed_p].deltayaw = pusher.client.ps.pmove.delta_angles[YAW]
	pushed_p += 1

	# move the pusher to it's final position
	q_shared.VectorAdd (pusher.s.origin, move, pusher.s.origin)
	q_shared.VectorAdd (pusher.s.angles, amove, pusher.s.angles)
	g_main.gi.linkentity (pusher)

	# see if any solid entities are inside the final position
	#check = g_edicts+1;
	for e in range(1, g_main.glob.num_edicts): # for (e = 1; e < globals.num_edicts; e++, check++)
		check = g_main.g_edicts[e]
		if not check.inuse:
			continue
		if (check.movetype == MOVETYPE_PUSH
		or check.movetype == MOVETYPE_STOP
		or check.movetype == MOVETYPE_NONE
		or check.movetype == MOVETYPE_NOCLIP):
			continue

		if not check.area.prev:
			continue		# not linked in anywhere

		# if the entity is standing on the pusher, it will definitely be moved
		if check.groundentity != pusher:
			# see if the ent needs to be tested
			if (check.absmin[0] >= maxs[0]
			or check.absmin[1] >= maxs[1]
			or check.absmin[2] >= maxs[2]
			or check.absmax[0] <= mins[0]
			or check.absmax[1] <= mins[1]
			or check.absmax[2] <= mins[2]):
				continue

			# see if the ent's bbox is inside the pusher's final position
			if not SV_TestEntityPosition (check):
				continue

		if (pusher.movetype == MOVETYPE_PUSH) or (check.groundentity == pusher):
			# move this entity
			pushed[pushed_p].ent = check
			q_shared.VectorCopy (check.s.origin, pushed[pushed_p].origin)
			q_shared.VectorCopy (check.s.angles, pushed[pushed_p].angles)
			pushed_p += 1

			# try moving the contacted entity
			q_shared.VectorAdd (check.s.origin, move, check.s.origin)
			if check.client:
				# FIXME: doesn't rotate monsters?
				check.client.ps.pmove.delta_angles[YAW] += amove[YAW]

			# figure movement due to the pusher's amove
			q_shared.VectorSubtract (check.s.origin, pusher.s.origin, org)
			org2[0] = q_shared.DotProduct (org, forward)
			org2[1] = -q_shared.DotProduct (org, right)
			org2[2] = q_shared.DotProduct (org, up)
			q_shared.VectorSubtract (org2, org, move2)
			q_shared.VectorAdd (check.s.origin, move2, check.s.origin)

			# may have pushed them off an edge
			if check.groundentity != pusher:
				check.groundentity = None

			block = SV_TestEntityPosition (check)
			if not block:
				# pushed ok
				g_main.gi.linkentity (check)
				# impact?
				continue

			# if it is ok to leave in the old position, do it
			# this is only relevent for riding entities, not pushed
			# FIXME: this doesn't acount for rotation
			q_shared.VectorSubtract (check.s.origin, move, check.s.origin)
			block = SV_TestEntityPosition (check)
			if not block:
				pushed_p -= 1
				continue

		# save off the obstacle so we can call the block function
		global obstacle
		obstacle = check

		# move back any entities we already moved
		# go backwards, so if the same entity was pushed
		# twice, it goes back to the original position
		for p in range(pushed_p-1, -1, -1):
			q_shared.VectorCopy (pushed[p].origin, pushed[p].ent.s.origin)
			q_shared.VectorCopy (pushed[p].angles, pushed[p].ent.s.angles)
			if pushed[p].ent.client:
				pushed[p].ent.client.ps.pmove.delta_angles[YAW] = pushed[p].deltayaw
			g_main.gi.linkentity (pushed[p].ent)
		return False

	# see if anything we moved has touched a trigger
	for p in range(pushed_p-1, -1, -1):
		g_utils.G_TouchTriggers (pushed[p].ent)

	return True


"""
================
SV_Physics_Pusher

Bmodel objects don't interact with each other, but
push all box objects
================
"""
def SV_Physics_Pusher (ent):
	#vec3_t move, amove
	#edict_t *part, *mv
	move = [0, 0, 0]
	amove = [0, 0, 0]

	global pushed_p

	# if not a team captain, so movement will be handled elsewhere
	if ent.flags & FL_TEAMSLAVE:
		return

	# make sure all team slaves can move before commiting
	# any moves or calling any think functions
	# if the move is blocked, all moved objects will be backed out
	pushed_p = 0
	part = ent
	while part:
		if (part.velocity[0] or part.velocity[1] or part.velocity[2] or
			part.avelocity[0] or part.avelocity[1] or part.avelocity[2]):
			# object is moving
			q_shared.VectorScale (part.velocity, FRAMETIME, move)
			q_shared.VectorScale (part.avelocity, FRAMETIME, amove)

			if not SV_Push (part, move, amove):
				break	# move was blocked
		part = part.teamchain

	if pushed_p > MAX_EDICTS:
		g_main.gi.error (qcommon.ERR_FATAL, "pushed_p > &pushed[MAX_EDICTS], memory corrupted")

	if part:
		# the move failed, bump all nextthink times and back out moves
		mv = ent
		while mv:
			if mv.nextthink > 0:
				mv.nextthink += FRAMETIME
			mv = mv.teamchain

		# if the pusher has a "blocked" function, call it
		# otherwise, just stay in place until the obstacle is gone
		if part.blocked:
			part.blocked (part, obstacle)
	else:
		# the move succeeded, so call all think functions
		part = ent
		while part:
			SV_RunThink (part)
			part = part.teamchain


"""
===============================================================================
"""
def SV_Physics_None (ent):
	# regular thinking
	SV_RunThink (ent)


def SV_Physics_Noclip (ent):
	# regular thinking
	if not SV_RunThink (ent):
		return

	q_shared.VectorMA (ent.s.angles, FRAMETIME, ent.avelocity, ent.s.angles)
	q_shared.VectorMA (ent.s.origin, FRAMETIME, ent.velocity, ent.s.origin)

	g_main.gi.linkentity (ent)


"""
==============================================================================

TOSS / BOUNCE

==============================================================================
"""
def SV_Physics_Toss (ent):
	#trace_t trace
	#vec3_t move, old_origin
	#float backoff
	#edict_t *slave
	#qboolean wasinwater, isinwater
	move = [0, 0, 0]
	old_origin = [0, 0, 0]

	# regular thinking
	SV_RunThink (ent)

	# if not a team captain, so movement will be handled elsewhere
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

	q_shared.VectorCopy (ent.s.origin, old_origin)

	SV_CheckVelocity (ent)

	# add gravity
	if ent.movetype != MOVETYPE_FLY and ent.movetype != MOVETYPE_FLYMISSILE:
		SV_AddGravity (ent)

	# move angles
	q_shared.VectorMA (ent.s.angles, FRAMETIME, ent.avelocity, ent.s.angles)

	# move origin
	q_shared.VectorScale (ent.velocity, FRAMETIME, move)
	trace = SV_PushEntity (ent, move)
	if not ent.inuse:
		return

	if trace.fraction < 1:
		if ent.movetype == MOVETYPE_BOUNCE:
			backoff = 1.5
		else:
			backoff = 1

		ClipVelocity (ent.velocity, trace.plane.normal, ent.velocity, backoff)

		# stop if on ground
		if trace.plane.normal[2] > 0.7:
			if ent.velocity[2] < 60 or ent.movetype != MOVETYPE_BOUNCE:
				ent.groundentity = trace.ent
				ent.groundentity_linkcount = trace.ent.linkcount
				q_shared.VectorCopy (vec3_origin, ent.velocity)
				q_shared.VectorCopy (vec3_origin, ent.avelocity)

	# check for water transition
	wasinwater = (ent.watertype & MASK_WATER)
	ent.watertype = g_main.gi.pointcontents (ent.s.origin)
	isinwater = ent.watertype & MASK_WATER

	if isinwater:
		ent.waterlevel = 1
	else:
		ent.waterlevel = 0

	if not wasinwater and isinwater:
		g_main.gi.positioned_sound (old_origin, g_main.g_edicts[0], CHAN_AUTO, g_main.gi.soundindex("misc/h2ohit1.wav"), 1, 1, 0)
	elif wasinwater and not isinwater:
		g_main.gi.positioned_sound (ent.s.origin, g_main.g_edicts[0], CHAN_AUTO, g_main.gi.soundindex("misc/h2ohit1.wav"), 1, 1, 0)

	# move teamslaves
	slave = ent.teamchain
	while slave:
		q_shared.VectorCopy (ent.s.origin, slave.s.origin)
		g_main.gi.linkentity (slave)
		slave = slave.teamchain


"""
===============================================================================

STEPPING MOVEMENT

===============================================================================
"""
def SV_AddRotationalFriction (ent):
	#int n
	#float adjustment
	q_shared.VectorMA (ent.s.angles, FRAMETIME, ent.avelocity, ent.s.angles)
	adjustment = FRAMETIME * sv_stopspeed * sv_friction
	for n in range(3):
		if ent.avelocity[n] > 0:
			ent.avelocity[n] -= adjustment
			if ent.avelocity[n] < 0:
				ent.avelocity[n] = 0
		else:
			ent.avelocity[n] += adjustment
			if ent.avelocity[n] > 0:
				ent.avelocity[n] = 0


def SV_Physics_Step (ent):
	#qboolean wasonground, hitsound
	#float speed, newspeed, control, friction
	#edict_t *groundentity
	#int mask
	hitsound = False

	# airborn monsters should always check for ground
	if not ent.groundentity:
		g_monster.M_CheckGround (ent)

	groundentity = ent.groundentity

	SV_CheckVelocity (ent)

	if groundentity:
		wasonground = True
	else:
		wasonground = False

	if ent.avelocity[0] or ent.avelocity[1] or ent.avelocity[2]:
		SV_AddRotationalFriction (ent)

	# add gravity except:
	#   flying monsters
	#   swimming monsters who are in the water
	if not wasonground:
		if not (ent.flags & FL_FLY):
			if not ((ent.flags & FL_SWIM) and (ent.waterlevel > 2)):
				if ent.velocity[2] < g_main.sv_gravity.value*-0.1:
					hitsound = True
				if ent.waterlevel == 0:
					SV_AddGravity (ent)

	# friction for flying monsters that have been given vertical velocity
	if (ent.flags & FL_FLY) and (ent.velocity[2] != 0):
		speed = abs(ent.velocity[2])
		control = sv_stopspeed if speed < sv_stopspeed else speed
		friction = sv_friction/3
		newspeed = speed - (FRAMETIME * control * friction)
		if newspeed < 0:
			newspeed = 0
		newspeed /= speed
		ent.velocity[2] *= newspeed

	# friction for flying monsters that have been given vertical velocity
	if (ent.flags & FL_SWIM) and (ent.velocity[2] != 0):
		speed = abs(ent.velocity[2])
		control = sv_stopspeed if speed < sv_stopspeed else speed
		newspeed = speed - (FRAMETIME * control * sv_waterfriction * ent.waterlevel)
		if newspeed < 0:
			newspeed = 0
		newspeed /= speed
		ent.velocity[2] *= newspeed

	if ent.velocity[2] or ent.velocity[1] or ent.velocity[0]:
		# apply friction
		# let dead monsters who aren't completely onground slide
		if wasonground or (ent.flags & (FL_SWIM|FL_FLY)):
			if not (ent.health <= 0.0 and not m_move.M_CheckBottom(ent)):
				vel = ent.velocity
				speed = math.sqrt(vel[0]*vel[0] +vel[1]*vel[1])
				if speed:
					friction = sv_friction

					control = sv_stopspeed if speed < sv_stopspeed else speed
					newspeed = speed - FRAMETIME*control*friction

					if newspeed < 0:
						newspeed = 0
					newspeed /= speed

					vel[0] *= newspeed
					vel[1] *= newspeed

		if ent.svflags & game.SVF_MONSTER:
			mask = MASK_MONSTERSOLID
		else:
			mask = MASK_SOLID
		SV_FlyMove (ent, FRAMETIME, mask)

		g_main.gi.linkentity (ent)
		g_utils.G_TouchTriggers (ent)
		if not ent.inuse:
			return

		if ent.groundentity:
			if not wasonground:
				if hitsound:
					g_main.gi.sound (ent, 0, g_main.gi.soundindex("world/land.wav"), 1, 1, 0)

	# regular thinking
	SV_RunThink (ent)


"""
============================================================================
"""
def G_RunEntity (ent):
	if ent.prethink:
		ent.prethink (ent)

	mt = int(ent.movetype)
	if mt in (MOVETYPE_PUSH, MOVETYPE_STOP):
		SV_Physics_Pusher (ent)
	elif mt == MOVETYPE_NONE:
		SV_Physics_None (ent)
	elif mt == MOVETYPE_NOCLIP:
		SV_Physics_Noclip (ent)
	elif mt == MOVETYPE_STEP:
		SV_Physics_Step (ent)
	elif mt in (MOVETYPE_TOSS, MOVETYPE_BOUNCE, MOVETYPE_FLY, MOVETYPE_FLYMISSILE):
		SV_Physics_Toss (ent)
	else:
		g_main.gi.error ("SV_Physics: bad movetype %i", mt)
