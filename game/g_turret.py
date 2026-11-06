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

Turrets aka big cannons with a driver.

=======================================================================
"""
from __future__ import annotations

import math
import numpy as np
from game import g_main, g_utils, g_monster, g_misc, g_ai, g_items
from game.g_ai import FindTarget, visible
from game.g_utils import G_PickTarget, G_FreeEdict, vtos, vectoangles
from game.g_combat import T_Damage
from game.g_weapon import fire_rocket
from game.g_monster import monster_use
from game.g_items import FindItemByClassname
from common.header.shared import PITCH, YAW, CHAN_WEAPON, ATTN_NORM, RF_FRAMELERP, MASK_MONSTERSOLID
from common.shared.shared import vec3_origin
from game.header.local import FRAMETIME, MOD_CRUSH, FL_TEAMSLAVE, FL_NO_KNOCKBACK, AI_LOST_SIGHT, AI_STAND_GROUND, AI_DUCKED, MOVETYPE_PUSH, MOVETYPE_STEP, damage_t

"""
#include "header/local.h"
"""

DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.header.game import solid_t, SVF_MONSTER
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from game.monster.infantry import infantry as m_infantry

SOLID_BSP = solid_t.SOLID_BSP.value
SOLID_BBOX = solid_t.SOLID_BBOX.value
M_PI = math.pi
"""
// g_turret.c

#include "g_local.h"
"""


def AnglesNormalize (vec): #vec3_t
	while vec[0] > 360:
		vec[0] -= 360
	while vec[0] < 0:
		vec[0] += 360
	while vec[1] > 360:
		vec[1] -= 360
	while vec[1] < 0:
		vec[1] += 360


def SnapToEights (x): #float
	x *= 8.0
	if x > 0.0:
		x += 0.5
	else:
		x -= 0.5
	return 0.125 * int(x)


def turret_blocked (self, other): #edict_t *, edict_t *
	if not self or not other:

		return


	attacker = None

	if other.takedamage:
		if self.teammaster.owner:
			attacker = self.teammaster.owner
		else:
			attacker = self.teammaster
		T_Damage (other, self, attacker, vec3_origin, other.s.origin, vec3_origin, self.teammaster.dmg, 10, 0, MOD_CRUSH)


def turret_breach_fire (self): #edict_t *
	if not self:

		return


	f = np.zeros((3,), dtype=np.float32)
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	damage = 0
	speed = 0

	shared_c.AngleVectors (self.s.angles, f, r, u)
	shared_c.VectorMA (self.s.origin, self.move_origin[0], f, start)
	shared_c.VectorMA (start, self.move_origin[1], r, start)
	shared_c.VectorMA (start, self.move_origin[2], u, start)

	damage = 100 + local.random() * 50
	speed = 550 + 50 * g_main.skill.value
	fire_rocket (self.teammaster.owner, start, f, damage, speed, 150, damage)
	g_main.gi.positioned_sound (start, self, CHAN_WEAPON, g_main.gi.soundindex("weapons/rocklf1a.wav"), 1, ATTN_NORM, 0)


def turret_breach_think (self): #edict_t *
	if not self:

		return


	ent = None
	current_angles = np.zeros((3,), dtype=np.float32)
	delta = np.zeros((3,), dtype=np.float32)
	dmin = 0.0
	dmax = 0.0
	angle = 0.0
	target_z = 0.0
	diff = 0.0
	target = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	shared.VectorCopy (self.s.angles, current_angles)
	AnglesNormalize(current_angles)

	AnglesNormalize(self.move_angles)
	if self.move_angles[PITCH] > 180:
		self.move_angles[PITCH] -= 360

	# clamp angles to mins & maxs
	if self.move_angles[PITCH] > self.pos1[PITCH]:
		self.move_angles[PITCH] = self.pos1[PITCH]
	elif self.move_angles[PITCH] < self.pos2[PITCH]:
		self.move_angles[PITCH] = self.pos2[PITCH]

	if (self.move_angles[YAW] < self.pos1[YAW]) or (self.move_angles[YAW] > self.pos2[YAW]):
		dmin = abs(self.pos1[YAW] - self.move_angles[YAW])
		if dmin < -180:
			dmin += 360
		elif dmin > 180:
			dmin -= 360
		dmax = abs(self.pos2[YAW] - self.move_angles[YAW])
		if dmax < -180:
			dmax += 360
		elif dmax > 180:
			dmax -= 360
		if abs(dmin) < abs(dmax):
			self.move_angles[YAW] = self.pos1[YAW]
		else:
			self.move_angles[YAW] = self.pos2[YAW]

	shared.VectorSubtract (self.move_angles, current_angles, delta)
	if delta[0] < -180:
		delta[0] += 360
	elif delta[0] > 180:
		delta[0] -= 360
	if delta[1] < -180:
		delta[1] += 360
	elif delta[1] > 180:
		delta[1] -= 360
	delta[2] = 0

	if delta[0] > self.speed * FRAMETIME:
		delta[0] = self.speed * FRAMETIME
	if delta[0] < -1 * self.speed * FRAMETIME:
		delta[0] = -1 * self.speed * FRAMETIME
	if delta[1] > self.speed * FRAMETIME:
		delta[1] = self.speed * FRAMETIME
	if delta[1] < -1 * self.speed * FRAMETIME:
		delta[1] = -1 * self.speed * FRAMETIME

	shared_c.VectorScale (delta, 1.0/FRAMETIME, self.avelocity)

	self.nextthink = g_main.level.time + FRAMETIME

	ent = self.teammaster
	while ent:
		ent.avelocity[1] = self.avelocity[1]
		ent = ent.teamchain

	# if we have a driver, adjust his velocities
	if self.owner:
		# angular is easy, just copy ours
		self.owner.avelocity[0] = self.avelocity[0]
		self.owner.avelocity[1] = self.avelocity[1]

		# x & y
		angle = self.s.angles[1] + self.owner.move_origin[1]
		angle *= (M_PI*2 / 360)
		target[0] = SnapToEights(self.s.origin[0] + math.cos(angle) * self.owner.move_origin[0])
		target[1] = SnapToEights(self.s.origin[1] + math.sin(angle) * self.owner.move_origin[0])
		target[2] = self.owner.s.origin[2]

		shared.VectorSubtract (target, self.owner.s.origin, dir)
		self.owner.velocity[0] = dir[0] * 1.0 / FRAMETIME
		self.owner.velocity[1] = dir[1] * 1.0 / FRAMETIME

		# z
		angle = self.s.angles[PITCH] * (M_PI*2 / 360)
		target_z = SnapToEights(self.s.origin[2] + self.owner.move_origin[0] * math.tan(angle) + self.owner.move_origin[2])

		diff = target_z - self.owner.s.origin[2]
		self.owner.velocity[2] = diff * 1.0 / FRAMETIME

		if self.spawnflags & 65536:
			turret_breach_fire (self)
			self.spawnflags &= ~65536


def turret_breach_finish_init (self): #edict_t *
	# get and save info for muzzle location
	if not self:

		return


	if not self.target:
		g_main.gi.dprintf("%s at %s needs a target\n" % (self.classname, vtos(self.s.origin)))
	else:
		self.target_ent = G_PickTarget (self.target)
		shared.VectorSubtract (self.target_ent.s.origin, self.s.origin, self.move_origin)
		G_FreeEdict(self.target_ent)

	self.teammaster.dmg = self.dmg
	self.think = turret_breach_think
	self.think (self)


def SP_turret_breach (self): #edict_t *
	if not self:

		return


	self.solid = SOLID_BSP
	self.movetype = MOVETYPE_PUSH
	g_main.gi.setmodel (self, self.model)

	if not self.speed:
		self.speed = 50
	if not self.dmg:
		self.dmg = 10

	if not g_main.st.minpitch:
		g_main.st.minpitch = -30
	if not g_main.st.maxpitch:
		g_main.st.maxpitch = 30
	if not g_main.st.maxyaw:
		g_main.st.maxyaw = 360

	self.pos1[PITCH] = -1 * g_main.st.minpitch
	self.pos1[YAW]   = g_main.st.minyaw
	self.pos2[PITCH] = -1 * g_main.st.maxpitch
	self.pos2[YAW]   = g_main.st.maxyaw

	self.ideal_yaw = self.s.angles[YAW]
	self.move_angles[YAW] = self.ideal_yaw

	self.blocked = turret_blocked

	self.think = turret_breach_finish_init
	self.nextthink = g_main.level.time + FRAMETIME
	g_main.gi.linkentity (self)


def SP_turret_base (self): #edict_t *
	if not self:

		return


	self.solid = SOLID_BSP
	self.movetype = MOVETYPE_PUSH
	g_main.gi.setmodel (self, self.model)
	self.blocked = turret_blocked
	g_main.gi.linkentity (self)


def turret_driver_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t
	if not self or not inflictor or not attacker:

		return


	ent = None

	# level the gun
	self.target_ent.move_angles[0] = 0

	# remove the driver from the end of the team chain
	ent = self.target_ent.teammaster
	while ent.teamchain != self:
		ent = ent.teamchain
	ent.teamchain = None
	self.teammaster = None
	self.flags &= ~FL_TEAMSLAVE

	self.target_ent.owner = None
	self.target_ent.teammaster.owner = None

	m_infantry.infantry_die (self, inflictor, attacker, damage, point)


def turret_driver_think (self): #edict_t *
	if not self:

		return


	target = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	reaction_time = 0.0

	self.nextthink = g_main.level.time + FRAMETIME

	if self.enemy and (not self.enemy.inuse or self.enemy.health <= 0):
		self.enemy = None

	if not self.enemy:
		if not FindTarget (self):
			return
		self.monsterinfo.trail_time = g_main.level.time
		self.monsterinfo.aiflags &= ~AI_LOST_SIGHT
	else:
		if visible (self, self.enemy):
			if self.monsterinfo.aiflags & AI_LOST_SIGHT:
				self.monsterinfo.trail_time = g_main.level.time
				self.monsterinfo.aiflags &= ~AI_LOST_SIGHT
		else:
			self.monsterinfo.aiflags |= AI_LOST_SIGHT
			return

	# let the turret know where we want it to aim
	shared.VectorCopy (self.enemy.s.origin, target)
	target[2] += self.enemy.viewheight
	shared.VectorSubtract (target, self.target_ent.s.origin, dir)
	vectoangles (dir, self.target_ent.move_angles)

	# decide if we should shoot
	if g_main.level.time < self.monsterinfo.attack_finished:
		return

	reaction_time = (3 - g_main.skill.value) * 1.0
	if ((g_main.level.time - self.monsterinfo.trail_time) < reaction_time):
		return

	self.monsterinfo.attack_finished = g_main.level.time + reaction_time + 1.0
	#FIXME how do we really want to pass this along?
	self.target_ent.spawnflags |= 65536


def turret_driver_link (self): #edict_t *
	if not self:

		return


	vec = np.zeros((3,), dtype=np.float32)
	ent = None

	self.think = turret_driver_think
	self.nextthink = g_main.level.time + FRAMETIME

	self.target_ent = G_PickTarget (self.target)
	self.target_ent.owner = self
	self.target_ent.teammaster.owner = self
	shared.VectorCopy (self.target_ent.s.angles, self.s.angles)

	vec[0] = self.target_ent.s.origin[0] - self.s.origin[0]
	vec[1] = self.target_ent.s.origin[1] - self.s.origin[1]
	vec[2] = 0
	self.move_origin[0] = shared_c.VectorLength(vec)

	shared.VectorSubtract (self.s.origin, self.target_ent.s.origin, vec)
	vectoangles (vec, vec)
	AnglesNormalize(vec)
	self.move_origin[1] = vec[1]

	self.move_origin[2] = self.s.origin[2] - self.target_ent.s.origin[2]

	# add the driver to the end of the team chain
	ent = self.target_ent.teammaster
	while ent.teamchain:
		ent = ent.teamchain
	ent.teamchain = self
	self.teammaster = self.target_ent.teammaster
	self.flags |= FL_TEAMSLAVE


def SP_turret_driver (self): #edict_t *
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	self.movetype = MOVETYPE_PUSH
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/infantry/tris.md2")
	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, 32)

	self.health = 100
	self.gib_health = 0
	self.mass = 200
	self.viewheight = 24

	self.die = turret_driver_die
	self.monsterinfo.stand = m_infantry.infantry_stand

	self.flags |= FL_NO_KNOCKBACK

	g_main.level.total_monsters += 1

	self.svflags |= SVF_MONSTER
	self.s.renderfx |= RF_FRAMELERP
	self.takedamage = DAMAGE_AIM
	self.use = monster_use
	self.clipmask = MASK_MONSTERSOLID
	shared.VectorCopy (self.s.origin, self.s.old_origin)
	self.monsterinfo.aiflags |= AI_STAND_GROUND|AI_DUCKED

	if g_main.st.item:
		self.item = FindItemByClassname (g_main.st.item)
		if not self.item:
			g_main.gi.dprintf("%s at %s has bad item: %s\n" % (self.classname, vtos(self.s.origin), g_main.st.item))

	self.think = turret_driver_link
	self.nextthink = g_main.level.time + FRAMETIME

	g_main.gi.linkentity (self)
