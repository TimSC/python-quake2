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
"""
// m_move.c -- monster movement

#include "g_local.h"
"""

import math
import random as _r
from game import q_shared
from game import g_main
from game import g_utils
from game import g_local
from game.q_shared import (vec3_origin, CONTENTS_SOLID, MASK_MONSTERSOLID,
	MASK_WATER, anglemod, YAW)
from game.g_local import FL_PARTIALGROUND

DI_NODIR = -1
from game.g_local import FL_FLY, FL_SWIM, AI_NOSTEP

STEPSIZE = 18
c_yes = 0
c_no = 0


"""
=============
M_CheckBottom

Returns false if any part of the bottom of the entity is off an edge that
is not a staircase.
=============
"""
def M_CheckBottom (ent):
	global c_yes, c_no
	#vec3_t mins, maxs, start, stop
	#int x, y
	#float mid, bottom
	mins = [0, 0, 0]
	maxs = [0, 0, 0]
	start = [0, 0, 0]
	stop = [0, 0, 0]

	q_shared.VectorAdd (ent.s.origin, ent.mins, mins)
	q_shared.VectorAdd (ent.s.origin, ent.maxs, maxs)

	# if all of the points under the corners are solid world, don't bother
	# with the tougher checks
	# the corners must be within 16 of the midpoint
	start[2] = mins[2] - 1
	x = 0
	while x <= 1:
		y = 0
		while y <= 1:
			start[0] = maxs[0] if x else mins[0]
			start[1] = maxs[1] if y else mins[1]
			if g_main.gi.pointcontents (start) != CONTENTS_SOLID:
				c_no += 1
				# realcheck
				start[2] = mins[2]

				# the midpoint must be within 16 of the bottom
				start[0] = stop[0] = (mins[0] + maxs[0])*0.5
				start[1] = stop[1] = (mins[1] + maxs[1])*0.5
				stop[2] = start[2] - 2*STEPSIZE
				trace = g_main.gi.trace (start, vec3_origin, vec3_origin, stop, ent, MASK_MONSTERSOLID)

				if trace.fraction == 1.0:
					return False
				mid = bottom = trace.endpos[2]

				# the corners must be within 16 of the midpoint
				x = 0
				while x <= 1:
					y = 0
					while y <= 1:
						start[0] = stop[0] = maxs[0] if x else mins[0]
						start[1] = stop[1] = maxs[1] if y else mins[1]

						trace = g_main.gi.trace (start, vec3_origin, vec3_origin, stop, ent, MASK_MONSTERSOLID)

						if trace.fraction != 1.0 and trace.endpos[2] > bottom:
							bottom = trace.endpos[2]
						if trace.fraction == 1.0 or mid - trace.endpos[2] > STEPSIZE:
							return False
						y += 1
					x += 1
				c_yes += 1
				return True
			y += 1
		x += 1

	c_yes += 1
	return True


"""
=============
SV_movestep

Called by monster program code.
The move will be adjusted for slopes and stairs, but if the move isn't
possible, no move is done, false is returned, and
pr_global_struct->trace_normal is set to the normal of the blocking wall
=============
"""
def SV_movestep (ent, move, relink):
	#vec3_t move; qboolean relink
	dz = 0.0
	oldorg = [0.0, 0.0, 0.0]
	neworg = [0.0, 0.0, 0.0]
	end = [0.0, 0.0, 0.0]
	test = [0.0, 0.0, 0.0]
	trace = None
	i = 0
	stepsize = 0.0
	contents = 0

	# try the move
	q_shared.VectorCopy (ent.s.origin, oldorg)
	q_shared.VectorAdd (ent.s.origin, move, neworg)

	# flying monsters don't step up
	if ent.flags & (FL_SWIM | FL_FLY):
		# try one move with vertical motion, then one without
		i = 0
		while i < 2:
			q_shared.VectorAdd (ent.s.origin, move, neworg)
			if i == 0 and ent.enemy:
				if not ent.goalentity:
					ent.goalentity = ent.enemy
				dz = ent.s.origin[2] - ent.goalentity.s.origin[2]
				if ent.goalentity.client:
					if dz > 40:
						neworg[2] -= 8
					if not ((ent.flags & FL_SWIM) and (ent.waterlevel < 2)):
						if dz < 30:
							neworg[2] += 8
				else:
					if dz > 8:
						neworg[2] -= 8
					elif dz > 0:
						neworg[2] -= dz
					elif dz < -8:
						neworg[2] += 8
					else:
						neworg[2] += dz
			trace = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, neworg, ent, MASK_MONSTERSOLID)

			# fly monsters don't enter water voluntarily
			if ent.flags & FL_FLY:
				if not ent.waterlevel:
					test[0] = trace.endpos[0]
					test[1] = trace.endpos[1]
					test[2] = trace.endpos[2] + ent.mins[2] + 1
					contents = g_main.gi.pointcontents (test)
					if contents & MASK_WATER:
						return False

			# swim monsters don't exit water voluntarily
			if ent.flags & FL_SWIM:
				if ent.waterlevel < 2:
					test[0] = trace.endpos[0]
					test[1] = trace.endpos[1]
					test[2] = trace.endpos[2] + ent.mins[2] + 1
					contents = g_main.gi.pointcontents (test)
					if not (contents & MASK_WATER):
						return False

			if trace.fraction == 1:
				q_shared.VectorCopy (trace.endpos, ent.s.origin)
				if relink:
					g_main.gi.linkentity (ent)
					g_utils.G_TouchTriggers (ent)
				return True

			if not ent.enemy:
				break
			i += 1

		return False

	# push down from a step height above the wished position
	if not (ent.monsterinfo.aiflags & AI_NOSTEP):
		stepsize = STEPSIZE
	else:
		stepsize = 1

	neworg[2] += stepsize
	q_shared.VectorCopy (neworg, end)
	end[2] -= stepsize * 2

	trace = g_main.gi.trace (neworg, ent.mins, ent.maxs, end, ent, MASK_MONSTERSOLID)

	if trace.allsolid:
		return False

	if trace.startsolid:
		neworg[2] -= stepsize
		trace = g_main.gi.trace (neworg, ent.mins, ent.maxs, end, ent, MASK_MONSTERSOLID)
		if trace.allsolid or trace.startsolid:
			return False

	# don't go in to water
	if ent.waterlevel == 0:
		test[0] = trace.endpos[0]
		test[1] = trace.endpos[1]
		test[2] = trace.endpos[2] + ent.mins[2] + 1
		contents = g_main.gi.pointcontents (test)

		if contents & MASK_WATER:
			return False

	if trace.fraction == 1:
		# if monster had the ground pulled out, go ahead and fall
		if ent.flags & g_local.FL_PARTIALGROUND:
			q_shared.VectorAdd (ent.s.origin, move, ent.s.origin)
			if relink:
				g_main.gi.linkentity (ent)
				g_utils.G_TouchTriggers (ent)
			ent.groundentity = None
			return True

		return False  # walked off an edge

	# check point traces down for dangling corners
	q_shared.VectorCopy (trace.endpos, ent.s.origin)

	if not M_CheckBottom (ent):
		if ent.flags & g_local.FL_PARTIALGROUND:
			# entity had floor mostly pulled out from underneath it
			# and is trying to correct
			if relink:
				g_main.gi.linkentity (ent)
				g_utils.G_TouchTriggers (ent)
			return True
		q_shared.VectorCopy (oldorg, ent.s.origin)
		return False

	if ent.flags & g_local.FL_PARTIALGROUND:
		ent.flags &= ~g_local.FL_PARTIALGROUND

	ent.groundentity = trace.ent
	ent.groundentity_linkcount = trace.ent.linkcount

	# the move is ok
	if relink:
		g_main.gi.linkentity (ent)
		g_utils.G_TouchTriggers (ent)
	return True


"""
=============
M_walkmove

returns false if the move is blocked by a wall
=============
"""
def M_walkmove (ent, yaw, dist):
	#vec3_t move
	move = [0.0, 0.0, 0.0]

	if not ent.groundentity and not (ent.flags & (FL_FLY | FL_SWIM)):
		return False

	yaw = yaw * math.pi * 2 / 360

	move[0] = math.cos (yaw) * dist
	move[1] = math.sin (yaw) * dist
	move[2] = 0

	return SV_movestep (ent, move, True)


"""
===============
M_ChangeYaw

===============
"""
def M_ChangeYaw (ent):
	#edict_t *ent
	ideal = 0.0
	current = 0.0
	move = 0.0
	speed = 0.0

	current = anglemod (ent.s.angles[YAW])
	ideal = ent.ideal_yaw

	if current == ideal:
		return

	move = ideal - current
	speed = ent.yaw_speed
	if ideal > current:
		if move >= 180:
			move = move - 360
	else:
		if move <= -180:
			move = move + 360
	if move > 0:
		if move > speed:
			move = speed
	else:
		if move < -speed:
			move = -speed

	ent.s.angles[YAW] = anglemod (current + move)


"""
======================
SV_StepDirection

Turns to the movement direction, and walks the current distance if
facing it.

======================
"""
def SV_StepDirection (ent, yaw, dist):
	#vec3_t move, oldorigin; float delta
	move = [0.0, 0.0, 0.0]
	oldorigin = [0.0, 0.0, 0.0]
	delta = 0.0

	ent.ideal_yaw = yaw
	M_ChangeYaw (ent)

	yaw = yaw * math.pi * 2 / 360
	move[0] = math.cos (yaw) * dist
	move[1] = math.sin (yaw) * dist
	move[2] = 0

	q_shared.VectorCopy (ent.s.origin, oldorigin)
	if SV_movestep (ent, move, False):
		delta = ent.s.angles[YAW] - ent.ideal_yaw
		if delta > 45 and delta < 315:
			# not turned far enough, so don't take the step
			q_shared.VectorCopy (oldorigin, ent.s.origin)
		g_main.gi.linkentity (ent)
		g_utils.G_TouchTriggers (ent)
		return True
	g_main.gi.linkentity (ent)
	g_utils.G_TouchTriggers (ent)
	return False


"""
======================
SV_FixCheckBottom

======================
"""
def SV_FixCheckBottom (ent):
	#edict_t *ent
	ent.flags |= FL_PARTIALGROUND


"""
================
SV_NewChaseDir

================
"""
def SV_NewChaseDir (actor, enemy, dist):
	#edict_t *actor, *enemy; float dist
	deltax = 0.0
	deltay = 0.0
	d = [0.0, 0.0, 0.0]
	tdir = 0.0
	olddir = 0.0
	turnaround = 0.0

	# FIXME: how did we get here with no enemy
	if not enemy:
		return

	olddir = anglemod ((int)(actor.ideal_yaw / 45) * 45)
	turnaround = anglemod (olddir - 180)

	deltax = enemy.s.origin[0] - actor.s.origin[0]
	deltay = enemy.s.origin[1] - actor.s.origin[1]
	if deltax > 10:
		d[1] = 0
	elif deltax < -10:
		d[1] = 180
	else:
		d[1] = DI_NODIR
	if deltay < -10:
		d[2] = 270
	elif deltay > 10:
		d[2] = 90
	else:
		d[2] = DI_NODIR

	# try direct route
	if d[1] != DI_NODIR and d[2] != DI_NODIR:
		if d[1] == 0:
			tdir = 45 if d[2] == 90 else 315
		else:
			tdir = 135 if d[2] == 90 else 215

		if tdir != turnaround and SV_StepDirection (actor, tdir, dist):
			return

	# try other directions
	if ((_r.randint(0, 2147483647) & 3) & 1) or abs(deltay) > abs(deltax):
		tdir = d[1]
		d[1] = d[2]
		d[2] = tdir

	if d[1] != DI_NODIR and d[1] != turnaround \
	and SV_StepDirection (actor, d[1], dist):
		return

	if d[2] != DI_NODIR and d[2] != turnaround \
	and SV_StepDirection (actor, d[2], dist):
		return

	# there is no direct path to the player, so pick another direction

	if olddir != DI_NODIR and SV_StepDirection (actor, olddir, dist):
		return

	if _r.randint(0, 2147483647) & 1:  # randomly determine direction of search
		tdir = 0
		while tdir <= 315:
			if tdir != turnaround and SV_StepDirection (actor, tdir, dist):
				return
			tdir += 45
	else:
		tdir = 315
		while tdir >= 0:
			if tdir != turnaround and SV_StepDirection (actor, tdir, dist):
				return
			tdir -= 45

	if turnaround != DI_NODIR and SV_StepDirection (actor, turnaround, dist):
		return

	actor.ideal_yaw = olddir  # can't move

	# if a bridge was pulled out from underneath a monster, it may not have
	# a valid standing position at all

	if not M_CheckBottom (actor):
		SV_FixCheckBottom (actor)


"""
======================
SV_CloseEnough

======================
"""
def SV_CloseEnough (ent, goal, dist):
	#edict_t *ent, *goal; float dist
	i = 0

	while i < 3:
		if goal.absmin[i] > ent.absmax[i] + dist:
			return False
		if goal.absmax[i] < ent.absmin[i] - dist:
			return False
		i += 1
	return True


"""
======================
M_MoveToGoal

======================
"""
def M_MoveToGoal (ent, dist):
	#edict_t *ent; float dist
	goal = None

	goal = ent.goalentity

	if not ent.groundentity and not (ent.flags & (FL_FLY | FL_SWIM)):
		return

	# if the next step hits the enemy, return immediately
	if ent.enemy and SV_CloseEnough (ent, ent.enemy, dist):
		return

	# bump around...
	if (_r.randint(0, 2147483647) & 3) == 1 or not SV_StepDirection (ent, ent.ideal_yaw, dist):
		if ent.inuse:
			SV_NewChaseDir (ent, goal, dist)
