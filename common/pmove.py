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

Player movement code. This is the core of Quake IIs legendary physics
engine

=======================================================================
"""
from __future__ import annotations

import math
import numpy as np
from common.header import shared
from common.shared import shared as shared_c
from common.header import shared as shared_h

"""
#include "header/common.h"
#include "../client/sound/header/local.h"
#include "../client/header/client.h"
"""
# movement parameters

pm_stopspeed: float = 100.0
pm_maxspeed: float = 300.0
pm_duckspeed: float = 100.0
pm_accelerate: float = 10.0
pm_airaccelerate: float = 0.0
pm_wateraccelerate: float = 10.0
pm_friction: float = 6.0
pm_waterfriction: float = 1.0
pm_waterspeed: float = 400.0

STEPSIZE = 18
STOP_EPSILON = 0.1
MIN_STEP_NORMAL = 0.7
MAX_CLIP_PLANES = 5

pm = None


class pml_t(object):

	def __init__(self):
		self.origin = np.zeros((3,), dtype=np.float32)
		self.velocity = np.zeros((3,), dtype=np.float32)
		self.forward = np.zeros((3,), dtype=np.float32)
		self.right = np.zeros((3,), dtype=np.float32)
		self.up = np.zeros((3,), dtype=np.float32)
		self.frametime = 0.0
		self.groundsurface = None
		self.groundplane = shared.cplane_t()
		self.groundcontents = 0
		self.previous_origin = np.zeros((3,), dtype=np.float32)
		self.ladder = False

	def clear(self):
		shared.VectorClear(self.origin)
		shared.VectorClear(self.velocity)
		shared.VectorClear(self.forward)
		shared.VectorClear(self.right)
		shared.VectorClear(self.up)
		self.frametime = 0.0
		self.groundsurface = None
		self.groundplane = shared.cplane_t()
		self.groundcontents = 0
		shared.VectorClear(self.previous_origin)
		self.ladder = False


pml = pml_t()


def _pm_type_value(pm_type):
	if isinstance(pm_type, shared.pmtype_t):
		return pm_type.value
	if pm_type is None:
		return 0
	return int(pm_type)


def _pm_flags_value(pm_flags):
	if pm_flags is None:
		return 0
	return int(pm_flags)


def PM_ClipVelocity(in_vec, normal, out_vec, overbounce):
	backoff = shared.DotProduct(in_vec, normal) * overbounce

	for i in range(3):
		change = normal[i] * backoff
		out_vec[i] = in_vec[i] - change
		if -STOP_EPSILON < out_vec[i] < STOP_EPSILON:
			out_vec[i] = 0.0


def PM_StepSlideMove_():
	global pm, pml

	numbumps = 4
	primal_velocity = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(pml.velocity, primal_velocity)
	numplanes = 0
	planes = [np.zeros((3,), dtype=np.float32) for _ in range(MAX_CLIP_PLANES)]

	time_left = pml.frametime
	for _ in range(numbumps):
		end = np.zeros((3,), dtype=np.float32)
		for i in range(3):
			end[i] = pml.origin[i] + time_left * pml.velocity[i]

		trace = pm.trace(pml.origin, pm.mins, pm.maxs, end)

		if trace.allsolid:
			pml.velocity[2] = 0
			return

		if trace.fraction > 0:
			shared.VectorCopy(trace.endpos, pml.origin)
			numplanes = 0

		if trace.fraction == 1:
			break

		if pm.numtouch < shared_h.MAXTOUCH and trace.ent is not None:
			pm.touchents[pm.numtouch] = trace.ent
			pm.numtouch += 1

		time_left -= time_left * trace.fraction

		if numplanes >= MAX_CLIP_PLANES:
			shared.VectorClear(pml.velocity)
			break

		shared.VectorCopy(trace.plane.normal, planes[numplanes])
		numplanes += 1

		plane_ok = False
		for i in range(numplanes):
			PM_ClipVelocity(pml.velocity, planes[i], pml.velocity, 1.01)
			ok = True
			for j in range(numplanes):
				if j != i and shared.DotProduct(pml.velocity, planes[j]) < 0:
					ok = False
					break
			if ok:
				plane_ok = True
				break

		if not plane_ok:
			if numplanes != 2:
				shared.VectorClear(pml.velocity)
				break
			dir_vec = np.zeros((3,), dtype=np.float32)
			shared_c.CrossProduct(planes[0], planes[1], dir_vec)
			d = shared.DotProduct(dir_vec, pml.velocity)
			shared_c.VectorScale(dir_vec, d, pml.velocity)

		if shared.DotProduct(pml.velocity, primal_velocity) <= 0:
			shared.VectorClear(pml.velocity)
			break

	if pm.s.pm_time:
		shared.VectorCopy(primal_velocity, pml.velocity)


"""
==================
PM_StepSlideMove

==================
"""
def PM_StepSlideMove():
	global pm, pml

	start_o = np.zeros((3,), dtype=np.float32)
	start_v = np.zeros((3,), dtype=np.float32)
	down_o = np.zeros((3,), dtype=np.float32)
	down_v = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(pml.origin, start_o)
	shared.VectorCopy(pml.velocity, start_v)

	PM_StepSlideMove_()

	shared.VectorCopy(pml.origin, down_o)
	shared.VectorCopy(pml.velocity, down_v)

	up = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(start_o, up)
	up[2] += STEPSIZE

	trace = pm.trace(up, pm.mins, pm.maxs, up)
	if trace.allsolid:
		return

	shared.VectorCopy(up, pml.origin)
	shared.VectorCopy(start_v, pml.velocity)

	PM_StepSlideMove_()

	down = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(pml.origin, down)
	down[2] -= STEPSIZE
	trace = pm.trace(pml.origin, pm.mins, pm.maxs, down)
	if not trace.allsolid:
		shared.VectorCopy(trace.endpos, pml.origin)

	shared.VectorCopy(pml.origin, up)
	down_dist = (down_o[0] - start_o[0]) * (down_o[0] - start_o[0]) + \
		(down_o[1] - start_o[1]) * (down_o[1] - start_o[1])
	up_dist = (up[0] - start_o[0]) * (up[0] - start_o[0]) + \
		(up[1] - start_o[1]) * (up[1] - start_o[1])

	plane_z = trace.plane.normal[2] if trace.plane is not None else 0.0
	if down_dist > up_dist or plane_z < MIN_STEP_NORMAL:
		shared.VectorCopy(down_o, pml.origin)
		shared.VectorCopy(down_v, pml.velocity)
		return

	pml.velocity[2] = down_v[2]


"""
==================
PM_Friction

Handles both ground friction and water friction
==================
"""
def PM_Friction():
	global pm, pml

	vel = pml.velocity
	speed = np.float32(math.sqrt(vel[0]*vel[0] + vel[1]*vel[1] + vel[2]*vel[2]))
	if speed < 1:
		vel[0] = 0
		vel[1] = 0
		return

	drop = 0.0

	if ((pm.groundentity is not None and pml.groundsurface is not None
		and not (pml.groundsurface.flags & shared.SURF_SLICK))
		or pml.ladder):
		friction = pm_friction
		control = pm_stopspeed if speed < pm_stopspeed else speed
		drop += control * friction * pml.frametime

	if pm.waterlevel and not pml.ladder:
		drop += speed * pm_waterfriction * pm.waterlevel * pml.frametime

	newspeed = speed - drop
	if newspeed < 0:
		newspeed = 0
	newspeed /= speed

	vel[0] *= newspeed
	vel[1] *= newspeed
	vel[2] *= newspeed


"""
/* Used for speedoomter display. */
void GetPlayerSpeed(float *speed, float *speedxy)
{
	*speedxy = sqrt(pml.velocity[0] * pml.velocity[0] + pml.velocity[1] * pml.velocity[1]);
	*speed = VectorLength(pml.velocity);
}
"""

"""
==============
PM_Accelerate

Handles user intended acceleration
==============
"""
def PM_Accelerate(wishdir, wishspeed, accel):
	global pml

	currentspeed = shared.DotProduct(pml.velocity, wishdir)
	addspeed = wishspeed - currentspeed
	if addspeed <= 0:
		return
	accelspeed = accel * pml.frametime * wishspeed
	if accelspeed > addspeed:
		accelspeed = addspeed

	for i in range(3):
		pml.velocity[i] += accelspeed * wishdir[i]


def PM_AirAccelerate(wishdir, wishspeed, accel):
	global pml

	wishspd = wishspeed
	if wishspd > 30:
		wishspd = 30
	currentspeed = shared.DotProduct(pml.velocity, wishdir)
	addspeed = wishspd - currentspeed
	if addspeed <= 0:
		return
	accelspeed = accel * wishspeed * pml.frametime
	if accelspeed > addspeed:
		accelspeed = addspeed

	for i in range(3):
		pml.velocity[i] += accelspeed * wishdir[i]


"""
=============
PM_AddCurrents
=============
"""
def PM_AddCurrents(wishvel):
	global pm, pml

	if pml.ladder and abs(pml.velocity[2]) <= 200:
		if (pm.viewangles[shared.PITCH] <= -15) and (pm.cmd.forwardmove > 0):
			wishvel[2] = 200
		elif (pm.viewangles[shared.PITCH] >= 15) and (pm.cmd.forwardmove > 0):
			wishvel[2] = -200
		elif pm.cmd.upmove > 0:
			wishvel[2] = 200
		elif pm.cmd.upmove < 0:
			wishvel[2] = -200
		else:
			wishvel[2] = 0

		if wishvel[0] < -25:
			wishvel[0] = -25
		elif wishvel[0] > 25:
			wishvel[0] = 25

		if wishvel[1] < -25:
			wishvel[1] = -25
		elif wishvel[1] > 25:
			wishvel[1] = 25

	if pm.watertype & shared.MASK_CURRENT:
		v = np.zeros((3,), dtype=np.float32)

		if pm.watertype & shared.CONTENTS_CURRENT_0:
			v[0] += 1
		if pm.watertype & shared.CONTENTS_CURRENT_90:
			v[1] += 1
		if pm.watertype & shared.CONTENTS_CURRENT_180:
			v[0] -= 1
		if pm.watertype & shared.CONTENTS_CURRENT_270:
			v[1] -= 1
		if pm.watertype & shared.CONTENTS_CURRENT_UP:
			v[2] += 1
		if pm.watertype & shared.CONTENTS_CURRENT_DOWN:
			v[2] -= 1

		s = pm_waterspeed
		if (pm.waterlevel == 1) and (pm.groundentity is not None):
			s /= 2

		shared_c.VectorMA(wishvel, s, v, wishvel)

	if pm.groundentity is not None:
		v = np.zeros((3,), dtype=np.float32)

		if pml.groundcontents & shared.CONTENTS_CURRENT_0:
			v[0] += 1
		if pml.groundcontents & shared.CONTENTS_CURRENT_90:
			v[1] += 1
		if pml.groundcontents & shared.CONTENTS_CURRENT_180:
			v[0] -= 1
		if pml.groundcontents & shared.CONTENTS_CURRENT_270:
			v[1] -= 1
		if pml.groundcontents & shared.CONTENTS_CURRENT_UP:
			v[2] += 1
		if pml.groundcontents & shared.CONTENTS_CURRENT_DOWN:
			v[2] -= 1

		shared_c.VectorMA(wishvel, 100, v, wishvel)


"""
===================
PM_WaterMove

===================
"""
def PM_WaterMove():
	global pm, pml

	wishvel = np.zeros((3,), dtype=np.float32)
	for i in range(3):
		wishvel[i] = pml.forward[i] * pm.cmd.forwardmove + pml.right[i] * pm.cmd.sidemove

	if not pm.cmd.forwardmove and not pm.cmd.sidemove and not pm.cmd.upmove:
		wishvel[2] -= 60
	else:
		wishvel[2] += pm.cmd.upmove

	PM_AddCurrents(wishvel)

	wishdir = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(wishvel, wishdir)
	wishspeed = shared_c.VectorNormalize(wishdir)

	if wishspeed > pm_maxspeed:
		shared_c.VectorScale(wishvel, pm_maxspeed / wishspeed, wishvel)
		wishspeed = pm_maxspeed
	wishspeed *= 0.5

	PM_Accelerate(wishdir, wishspeed, pm_wateraccelerate)
	PM_StepSlideMove()


"""
===================
PM_AirMove

===================
"""
def PM_AirMove():
	global pm, pml

	fmove = pm.cmd.forwardmove
	smove = pm.cmd.sidemove

	wishvel = np.zeros((3,), dtype=np.float32)
	for i in range(2):
		wishvel[i] = pml.forward[i] * fmove + pml.right[i] * smove
	wishvel[2] = 0

	PM_AddCurrents(wishvel)

	wishdir = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(wishvel, wishdir)
	wishspeed = shared_c.VectorNormalize(wishdir)

	maxspeed = pm_duckspeed if (pm.s.pm_flags & shared.PMF_DUCKED) else pm_maxspeed
	if wishspeed > maxspeed:
		shared_c.VectorScale(wishvel, maxspeed / wishspeed, wishvel)
		wishspeed = maxspeed

	if pml.ladder:
		PM_Accelerate(wishdir, wishspeed, pm_accelerate)
		if not wishvel[2]:
			if pml.velocity[2] > 0:
				pml.velocity[2] -= pm.s.gravity * pml.frametime
				if pml.velocity[2] < 0:
					pml.velocity[2] = 0
			else:
				pml.velocity[2] += pm.s.gravity * pml.frametime
				if pml.velocity[2] > 0:
					pml.velocity[2] = 0
		PM_StepSlideMove()
	elif pm.groundentity is not None:
		pml.velocity[2] = 0
		PM_Accelerate(wishdir, wishspeed, pm_accelerate)
		if pm.s.gravity > 0:
			pml.velocity[2] = 0
		else:
			pml.velocity[2] -= pm.s.gravity * pml.frametime
		if not pml.velocity[0] and not pml.velocity[1]:
			return
		PM_StepSlideMove()
	else:
		if pm_airaccelerate:
			PM_AirAccelerate(wishdir, wishspeed, pm_accelerate)
		else:
			PM_Accelerate(wishdir, wishspeed, 1)
		pml.velocity[2] -= pm.s.gravity * pml.frametime
		PM_StepSlideMove()


"""
=============
PM_CatagorizePosition
=============
"""
def PM_CatagorizePosition():
	global pm, pml

	point = np.zeros((3,), dtype=np.float32)
	point[0] = pml.origin[0]
	point[1] = pml.origin[1]
	point[2] = pml.origin[2] - 0.25
	if pml.velocity[2] > 180:
		pm.s.pm_flags &= ~shared.PMF_ON_GROUND
		pm.groundentity = None
	else:
		trace = pm.trace(pml.origin, pm.mins, pm.maxs, point)
		pml.groundplane = trace.plane
		pml.groundsurface = trace.surface
		pml.groundcontents = trace.contents

		if (trace.ent is None) or (trace.plane.normal[2] < 0.7 and not trace.startsolid):
			pm.groundentity = None
			pm.s.pm_flags &= ~shared.PMF_ON_GROUND
		else:
			pm.groundentity = trace.ent
			if pm.s.pm_flags & shared.PMF_TIME_WATERJUMP:
				pm.s.pm_flags &= ~(shared.PMF_TIME_WATERJUMP | shared.PMF_TIME_LAND | shared.PMF_TIME_TELEPORT)
				pm.s.pm_time = 0

			if not (pm.s.pm_flags & shared.PMF_ON_GROUND):
				pm.s.pm_flags |= shared.PMF_ON_GROUND
				if pml.velocity[2] < -200:
					pm.s.pm_flags |= shared.PMF_TIME_LAND
					if pml.velocity[2] < -400:
						pm.s.pm_time = 25
					else:
						pm.s.pm_time = 18

		if pm.numtouch < shared_h.MAXTOUCH and trace.ent is not None:
			pm.touchents[pm.numtouch] = trace.ent
			pm.numtouch += 1

	pm.waterlevel = 0
	pm.watertype = 0

	sample2 = np.float32(pm.viewheight - pm.mins[2]) # float
	sample1 = sample2 / 2 # float

	point[2] = pml.origin[2] + pm.mins[2] + 1
	cont = pm.pointcontents(point)

	if cont & shared.MASK_WATER:
		pm.watertype = cont
		pm.waterlevel = 1
		point[2] = pml.origin[2] + pm.mins[2] + sample1
		cont = pm.pointcontents(point)
		if cont & shared.MASK_WATER:
			pm.waterlevel = 2
			point[2] = pml.origin[2] + pm.mins[2] + sample2
			cont = pm.pointcontents(point)
			if cont & shared.MASK_WATER:
				pm.waterlevel = 3


"""
=============
PM_CheckJump
=============
"""
def PM_CheckJump():
	global pm, pml

	if pm.s.pm_flags & shared.PMF_TIME_LAND:
		return

	if pm.cmd.upmove < 10:
		pm.s.pm_flags &= ~shared.PMF_JUMP_HELD
		return

	if pm.s.pm_flags & shared.PMF_JUMP_HELD:
		return

	if _pm_type_value(pm.s.pm_type) == shared.pmtype_t.PM_DEAD.value:
		return

	if pm.waterlevel >= 2:
		pm.groundentity = None
		if pml.velocity[2] <= -300:
			return

		if pm.watertype == shared.CONTENTS_WATER:
			pml.velocity[2] = 100
		elif pm.watertype == shared.CONTENTS_SLIME:
			pml.velocity[2] = 80
		else:
			pml.velocity[2] = 50
		return

	if pm.groundentity is None:
		return

	pm.s.pm_flags |= shared.PMF_JUMP_HELD
	pm.groundentity = None
	pml.velocity[2] += 270
	if pml.velocity[2] < 270:
		pml.velocity[2] = 270


"""
=============
PM_CheckSpecialMovement
=============
"""
def PM_CheckSpecialMovement():
	global pm, pml

	if pm.s.pm_time:
		return

	pml.ladder = False

	flatforward = np.zeros((3,), dtype=np.float32)
	flatforward[0] = pml.forward[0]
	flatforward[1] = pml.forward[1]
	flatforward[2] = 0
	shared_c.VectorNormalize(flatforward)

	spot = np.zeros((3,), dtype=np.float32)
	shared_c.VectorMA(pml.origin, 1, flatforward, spot)
	trace = pm.trace(pml.origin, pm.mins, pm.maxs, spot)
	if trace.fraction < 1 and (trace.contents & shared.CONTENTS_LADDER):
		pml.ladder = True

	if pm.waterlevel != 2:
		return

	shared_c.VectorMA(pml.origin, 30, flatforward, spot)
	spot[2] += 4
	cont = pm.pointcontents(spot)
	if not (cont & shared.CONTENTS_SOLID):
		return

	spot[2] += 16
	cont = pm.pointcontents(spot)
	if cont:
		return

	shared_c.VectorScale(flatforward, 50, pml.velocity)
	pml.velocity[2] = 350

	pm.s.pm_flags |= shared.PMF_TIME_WATERJUMP
	pm.s.pm_time = 255


"""
===============
PM_FlyMove
===============
"""
def PM_FlyMove(doclip):
	global pm, pml

	pm.viewheight = 22

	speed = shared_c.VectorLength(pml.velocity)
	if speed < 1:
		shared.VectorClear(pml.velocity)
	else:
		drop = 0.0
		friction = pm_friction * 1.5
		control = pm_stopspeed if speed < pm_stopspeed else speed
		drop += control * friction * pml.frametime

		newspeed = speed - drop
		if newspeed < 0:
			newspeed = 0
		newspeed /= speed

		shared_c.VectorScale(pml.velocity, newspeed, pml.velocity)

	fmove = pm.cmd.forwardmove
	smove = pm.cmd.sidemove

	shared_c.VectorNormalize(pml.forward)
	shared_c.VectorNormalize(pml.right)

	wishvel = np.zeros((3,), dtype=np.float32)
	for i in range(3):
		wishvel[i] = pml.forward[i] * fmove + pml.right[i] * smove
	wishvel[2] += pm.cmd.upmove

	wishdir = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy(wishvel, wishdir)
	wishspeed = shared_c.VectorNormalize(wishdir)

	if wishspeed > pm_maxspeed:
		shared_c.VectorScale(wishvel, pm_maxspeed / wishspeed, wishvel)
		wishspeed = pm_maxspeed

	currentspeed = shared.DotProduct(pml.velocity, wishdir)
	addspeed = wishspeed - currentspeed
	if addspeed <= 0:
		return
	accelspeed = pm_accelerate * pml.frametime * wishspeed
	if accelspeed > addspeed:
		accelspeed = addspeed

	for i in range(3):
		pml.velocity[i] += accelspeed * wishdir[i]

	if doclip:
		end = np.zeros((3,), dtype=np.float32)
		for i in range(3):
			end[i] = pml.origin[i] + pml.frametime * pml.velocity[i]
		trace = pm.trace(pml.origin, pm.mins, pm.maxs, end)
		shared.VectorCopy(trace.endpos, pml.origin)
	else:
		shared_c.VectorMA(pml.origin, pml.frametime, pml.velocity, pml.origin)


"""
==============
PM_CheckDuck

Sets mins, maxs, and pm->viewheight
==============
"""
def PM_CheckDuck():
	global pm, pml

	pm.mins[0] = -16
	pm.mins[1] = -16

	pm.maxs[0] = 16
	pm.maxs[1] = 16

	if _pm_type_value(pm.s.pm_type) == shared.pmtype_t.PM_GIB.value:
		pm.mins[2] = 0
		pm.maxs[2] = 16
		pm.viewheight = 8
		return

	pm.mins[2] = -24

	if _pm_type_value(pm.s.pm_type) == shared.pmtype_t.PM_DEAD.value:
		pm.s.pm_flags |= shared.PMF_DUCKED
	elif pm.cmd.upmove < 0 and (pm.s.pm_flags & shared.PMF_ON_GROUND):
		pm.s.pm_flags |= shared.PMF_DUCKED
	else:
		if pm.s.pm_flags & shared.PMF_DUCKED:
			pm.maxs[2] = 32
			trace = pm.trace(pml.origin, pm.mins, pm.maxs, pml.origin)
			if not trace.allsolid:
				pm.s.pm_flags &= ~shared.PMF_DUCKED

	if pm.s.pm_flags & shared.PMF_DUCKED:
		pm.maxs[2] = 4
		pm.viewheight = -2
	else:
		pm.maxs[2] = 32
		pm.viewheight = 22


"""
==============
PM_DeadMove
==============
"""
def PM_DeadMove():
	global pm, pml

	if pm.groundentity is None:
		return

	forward = shared_c.VectorLength(pml.velocity)
	forward -= 20
	if forward <= 0:
		shared.VectorClear(pml.velocity)
	else:
		shared_c.VectorNormalize(pml.velocity)
		shared_c.VectorScale(pml.velocity, forward, pml.velocity)


def PM_GoodPosition():
	global pm

	if _pm_type_value(pm.s.pm_type) == shared.pmtype_t.PM_SPECTATOR.value:
		return True

	origin = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)
	for i in range(3):
		origin[i] = end[i] = pm.s.origin[i] * 0.125
	trace = pm.trace(origin, pm.mins, pm.maxs, end)

	return not trace.allsolid


"""
================
PM_SnapPosition

On exit, the origin will have a value that is pre-quantized to the 0.125
precision of the network channel and in a valid position.
================
"""
def PM_SnapPosition():
	global pm, pml

	sign = [0, 0, 0]
	jitterbits = [0, 4, 1, 2, 3, 5, 6, 7]

	for i in range(3):
		pm.s.velocity[i] = int(pml.velocity[i] * 8)

	for i in range(3):
		if pml.origin[i] >= 0:
			sign[i] = 1
		else:
			sign[i] = -1
		pm.s.origin[i] = int(pml.origin[i] * 8)
		if pm.s.origin[i] * 0.125 == pml.origin[i]:
			sign[i] = 0

	base = pm.s.origin.copy()

	for bits in jitterbits:
		pm.s.origin[:] = base
		for i in range(3):
			if bits & (1 << i):
				pm.s.origin[i] += sign[i]
		if PM_GoodPosition():
			return

	pm.s.origin[:] = pml.previous_origin


"""
================
PM_InitialSnapPosition

================
"""
def PM_InitialSnapPosition():
	global pm, pml

	base = pm.s.origin.copy()
	offset = [0, -1, 1]

	for z in range(3):
		pm.s.origin[2] = base[2] + offset[z]
		for y in range(3):
			pm.s.origin[1] = base[1] + offset[y]
			for x in range(3):
				pm.s.origin[0] = base[0] + offset[x]
				if PM_GoodPosition():
					pml.origin[0] = pm.s.origin[0] * 0.125
					pml.origin[1] = pm.s.origin[1] * 0.125
					pml.origin[2] = pm.s.origin[2] * 0.125
					shared.VectorCopy(pm.s.origin, pml.previous_origin)
					return


"""
================
PM_ClampAngles

================
"""
def PM_ClampAngles():
	global pm, pml

	if pm.s.pm_flags & shared.PMF_TIME_TELEPORT:
		pm.viewangles[shared.YAW] = shared.SHORT2ANGLE(
			int(pm.cmd.angles[shared.YAW]) + int(pm.s.delta_angles[shared.YAW]) # the C adds these as ints
		)
		pm.viewangles[shared.PITCH] = 0
		pm.viewangles[shared.ROLL] = 0
	else:
		# circularly clamp the angles with deltas
		for i in range(3):
			temp = int(pm.cmd.angles[i]) + int(pm.s.delta_angles[i])
			temp = ((temp + 0x8000) & 0xffff) - 0x8000 # short	temp;
			pm.viewangles[i] = shared.SHORT2ANGLE(temp)

		if pm.viewangles[shared.PITCH] > 89 and pm.viewangles[shared.PITCH] < 180:
			pm.viewangles[shared.PITCH] = 89
		elif pm.viewangles[shared.PITCH] < 271 and pm.viewangles[shared.PITCH] >= 180:
			pm.viewangles[shared.PITCH] = 271

	shared_c.AngleVectors(pm.viewangles, pml.forward, pml.right, pml.up)


def PM_CalculateViewHeightForDemo(): #void

	if pm.s.pm_type == shared.pmtype_t.PM_GIB.value:
		pm.viewheight = 8
	else:
		if (pm.s.pm_flags & shared.PMF_DUCKED) != 0:
			pm.viewheight = -2
		else:
			pm.viewheight = 22

def PM_CalculateWaterLevelForDemo(): #void

	"""
	vec3_t point;
	int cont;
	"""
	point = np.zeros((3,), dtype=np.float32)

	point[0] = pml.origin[0]
	point[1] = pml.origin[1]
	point[2] = pml.origin[2] + pm.viewheight

	pm.waterlevel = 0
	pm.watertype = 0

	cont = pm.pointcontents(point)

	if (cont & shared.MASK_WATER) != 0:
		pm.waterlevel = 3
		pm.watertype = cont

_underwater = 0 #static int, in PM_UpdateUnderwaterSfx

def PM_UpdateUnderwaterSfx(): #void

	global _underwater

	from client import snd_dma	# Q2PORT: imported here; snd_is_underwater is in the client's sound code

	#static int underwater;

	if (pm.waterlevel == 3) and not _underwater:

		_underwater = 1
		snd_dma.snd_is_underwater = True

		#ifdef USE_OPENAL
		#AL_Underwater();
		#endif


	if (pm.waterlevel < 3) and _underwater:

		_underwater = 0
		snd_dma.snd_is_underwater = False

		#ifdef USE_OPENAL
		#AL_Overwater();
		#endif

"""
================
Pmove

Can be called by either the server or the client
================
"""
def Pmove(pmove):
	global pm, pml

	pm = pmove

	pm.numtouch = 0
	shared.VectorClear(pm.viewangles)
	pm.viewheight = 0
	pm.groundentity = None
	pm.watertype = 0
	pm.waterlevel = 0

	pml.clear()

	if pm.s.pm_flags is None:
		pm.s.pm_flags = 0
	if pm.s.pm_time is None:
		pm.s.pm_time = 0
	if pm.s.gravity is None:
		pm.s.gravity = 0

	pml.origin[0] = pm.s.origin[0] * 0.125
	pml.origin[1] = pm.s.origin[1] * 0.125
	pml.origin[2] = pm.s.origin[2] * 0.125

	pml.velocity[0] = pm.s.velocity[0] * 0.125
	pml.velocity[1] = pm.s.velocity[1] * 0.125
	pml.velocity[2] = pm.s.velocity[2] * 0.125

	shared.VectorCopy(pm.s.origin, pml.previous_origin)

	pml.frametime = pm.cmd.msec * np.float32(0.001)	# Q2PORT: float arithmetic, as msec * 0.001f

	PM_ClampAngles()

	pm_type = _pm_type_value(pm.s.pm_type)
	if pm_type == shared.pmtype_t.PM_SPECTATOR.value:
		PM_FlyMove(False)
		PM_SnapPosition()
		return

	if pm_type >= shared.pmtype_t.PM_DEAD.value:
		pm.cmd.forwardmove = 0
		pm.cmd.sidemove = 0
		pm.cmd.upmove = 0

	if pm_type == shared.pmtype_t.PM_FREEZE.value:

		#if !defined(DEDICATED_ONLY)
		from client import cl_main	# Q2PORT: imported here, the client imports pmove
		if cl_main.cl.attractloop:
			PM_CalculateViewHeightForDemo()
			PM_CalculateWaterLevelForDemo()
			PM_UpdateUnderwaterSfx()
		#endif

		return # no movement at all

	PM_CheckDuck()

	if pm.snapinitial:
		PM_InitialSnapPosition()

	PM_CatagorizePosition()

	if pm_type == shared.pmtype_t.PM_DEAD.value:
		PM_DeadMove()

	PM_CheckSpecialMovement()

	if pm.s.pm_time:
		msec = pm.cmd.msec >> 3
		if not msec:
			msec = 1
		if msec >= pm.s.pm_time:
			pm.s.pm_flags &= ~(shared.PMF_TIME_WATERJUMP | shared.PMF_TIME_LAND | shared.PMF_TIME_TELEPORT)
			pm.s.pm_time = 0
		else:
			pm.s.pm_time -= msec

	if pm.s.pm_flags & shared.PMF_TIME_TELEPORT:
		pass
	elif pm.s.pm_flags & shared.PMF_TIME_WATERJUMP:
		pml.velocity[2] -= pm.s.gravity * pml.frametime
		if pml.velocity[2] < 0:
			pm.s.pm_flags &= ~(shared.PMF_TIME_WATERJUMP | shared.PMF_TIME_LAND | shared.PMF_TIME_TELEPORT)
			pm.s.pm_time = 0

		PM_StepSlideMove()
	else:
		PM_CheckJump()
		PM_Friction()

		if pm.waterlevel >= 2:
			PM_WaterMove()
		else:
			angles = np.zeros((3,), dtype=np.float32)
			shared.VectorCopy(pm.viewangles, angles)
			if angles[shared.PITCH] > 180:
				angles[shared.PITCH] -= 360
			angles[shared.PITCH] /= 3

			shared_c.AngleVectors(angles, pml.forward, pml.right, pml.up)
			PM_AirMove()

	# set groundentity, watertype, and waterlevel for final spot
	PM_CatagorizePosition()

	#if !defined(DEDICATED_ONLY)
	PM_UpdateUnderwaterSfx()
	#endif

	PM_SnapPosition()
"""
/*

  walking up a step should kill some velocity

*/
"""
"""
/*
==================
PM_StepSlideMove

Each intersection will try to step over the obstruction instead of
sliding along it.

Returns a new origin, velocity, and contact entity
Does not modify any world state?
==================
*/
#define	MIN_STEP_NORMAL	0.7		// can't step up onto very steep slopes
#define	MAX_CLIP_PLANES	5

"""
"""

#if 0
//NO LONGER USED
"""
"""

#else
"""
"""

#endif
"""
