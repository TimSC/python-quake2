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

import random as _r
from game import q_shared
from game import g_local
from game import g_main
from game import g_utils
from game import g_monster
from game import m_move
from game import p_trail
from game.game import SVF_MONSTER
from game.q_shared import (MASK_OPAQUE, MASK_PLAYERSOLID, CONTENTS_SOLID,
	CONTENTS_MONSTER, CONTENTS_SLIME, CONTENTS_LAVA, CONTENTS_WINDOW,
	vec3_origin, YAW)
from game.g_local import (FL_NOTARGET, MELEE_DISTANCE, RANGE_MELEE, RANGE_NEAR,
	RANGE_MID, RANGE_FAR, AI_STAND_GROUND, AI_TEMP_STAND_GROUND, AI_GOOD_GUY,
	AI_COMBAT_POINT, AI_SOUND_TARGET, AI_MEDIC, AI_BRUTAL, AI_LOST_SIGHT,
	AI_PURSUE_NEXT, AI_PURSUE_TEMP, AI_PURSUIT_LAST_SEEN,
	AS_MELEE, AS_MISSILE, AS_SLIDING, AS_STRAIGHT, FL_FLY)

"""
// g_ai.c

#include "g_local.h"

qboolean FindTarget (edict_t *self);
"""

enemy_vis = False
enemy_infront = False
enemy_range = 0
enemy_yaw = 0.0

"""
============================================================================
"""


"""
=================
AI_SetSightClient

Called once each frame to set level.sight_client to the
player to be checked for in findtarget.
=================
"""
def AI_SetSightClient ():
	#edict_t *ent
	#int start, check
	edicts = g_main.g_edicts
	if g_main.level.sight_client is None:
		start = 1
	else:
		start = g_main.level.sight_client.s.number

	check = start
	while True:
		check += 1
		if check > int(g_main.maxclients.value):
			check = 1
		ent = edicts[check]
		if ent.inuse and ent.health > 0 and not (ent.flags & FL_NOTARGET) :
			g_main.level.sight_client = ent
			return		# got one
		if check == start:
			g_main.level.sight_client = None
			return		# nobody to see


"""
=============
ai_move

Move the specified distance at current facing.
==============
"""
def ai_move (self, dist):
	m_move.M_walkmove (self, self.s.angles[YAW], dist)


"""
=============
ai_stand

Used for standing around and looking for players
==============
"""
def ai_stand (self, dist):
	#vec3_t v
	v = [0, 0, 0]

	if dist:
		m_move.M_walkmove (self, self.s.angles[YAW], dist)

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		if self.enemy:
			q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, v)
			self.ideal_yaw = g_utils.vectoyaw(v)
			if self.s.angles[YAW] != self.ideal_yaw and self.monsterinfo.aiflags & AI_TEMP_STAND_GROUND:
				self.monsterinfo.aiflags &= ~(AI_STAND_GROUND | AI_TEMP_STAND_GROUND)
				self.monsterinfo.run (self)
			m_move.M_ChangeYaw (self)
			ai_checkattack (self, 0)
		else:
			FindTarget (self)
		return

	if FindTarget (self):
		return

	if g_main.level.time > self.monsterinfo.pausetime:
		self.monsterinfo.walk (self)
		return

	if not (self.spawnflags & 1) and (self.monsterinfo.idle) and (g_main.level.time > self.monsterinfo.idle_time):
		if self.monsterinfo.idle_time:
			self.monsterinfo.idle (self)
			self.monsterinfo.idle_time = g_main.level.time + 15 + g_local.random() * 15
		else:
			self.monsterinfo.idle_time = g_main.level.time + g_local.random() * 15


"""
=============
ai_walk

The monster is walking it's beat
=============
"""
def ai_walk (self, dist):
	m_move.M_MoveToGoal (self, dist)

	# check for noticing a player
	if FindTarget (self):
		return

	if (self.monsterinfo.search) and (g_main.level.time > self.monsterinfo.idle_time):
		if self.monsterinfo.idle_time:
			self.monsterinfo.search (self)
			self.monsterinfo.idle_time = g_main.level.time + 15 + g_local.random() * 15
		else:
			self.monsterinfo.idle_time = g_main.level.time + g_local.random() * 15


"""
=============
ai_charge

Turns towards target and advances
==============
"""
def ai_charge (self, dist):
	#vec3_t v
	v = [0, 0, 0]

	q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, v)
	self.ideal_yaw = g_utils.vectoyaw(v)
	m_move.M_ChangeYaw (self)

	if dist:
		m_move.M_walkmove (self, self.s.angles[YAW], dist)


"""
=============
ai_turn

don't move, but turn towards ideal_yaw
=============
"""
def ai_turn (self, dist):
	if dist:
		m_move.M_walkmove (self, self.s.angles[YAW], dist)

	if FindTarget (self):
		return

	m_move.M_ChangeYaw (self)


"""
=============
range

returns the range catagorization of an entity reletive to self
=============
"""
def range (self, other):
	#vec3_t v
	#float len
	v = [0, 0, 0]

	q_shared.VectorSubtract (self.s.origin, other.s.origin, v)
	length = q_shared.VectorLength (v)
	if length < MELEE_DISTANCE:
		return RANGE_MELEE
	if length < 500:
		return RANGE_NEAR
	if length < 1000:
		return RANGE_MID
	return RANGE_FAR


"""
=============
visible

returns 1 if the entity is visible to self, even if not infront ()
=============
"""
def visible (self, other):
	#vec3_t spot1, spot2
	spot1 = [0, 0, 0]
	spot2 = [0, 0, 0]

	q_shared.VectorCopy (self.s.origin, spot1)
	spot1[2] += self.viewheight
	q_shared.VectorCopy (other.s.origin, spot2)
	spot2[2] += other.viewheight
	trace = g_main.gi.trace (spot1, vec3_origin, vec3_origin, spot2, self, MASK_OPAQUE)

	if trace.fraction == 1.0:
		return True
	return False


"""
=============
infront

returns 1 if the entity is in front (in sight) of self
=============
"""
def infront (self, other):
	#vec3_t vec, forward
	#float dot
	vec = [0, 0, 0]
	forward = [0, 0, 0]

	q_shared.AngleVectors (self.s.angles, forward, None, None)
	q_shared.VectorSubtract (other.s.origin, self.s.origin, vec)
	q_shared.VectorNormalize (vec)
	dot = q_shared.DotProduct (vec, forward)

	if dot > 0.3:
		return True
	return False


def HuntTarget (self):
	#vec3_t vec
	vec = [0, 0, 0]

	self.goalentity = self.enemy
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.stand (self)
	else:
		self.monsterinfo.run (self)
	q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	self.ideal_yaw = g_utils.vectoyaw(vec)
	# wait a while before first attack
	if not (self.monsterinfo.aiflags & AI_STAND_GROUND):
		g_monster.AttackFinished (self, 1)


def FoundTarget (self):
	# let other monsters see this monster for a while
	if self.enemy.client:
		g_main.level.sight_entity = self
		g_main.level.sight_entity_framenum = g_main.level.framenum
		g_main.level.sight_entity.light_level = 128

	self.show_hostile = g_main.level.time + 1		# wake up other monsters

	q_shared.VectorCopy(self.enemy.s.origin, self.monsterinfo.last_sighting)
	self.monsterinfo.trail_time = g_main.level.time

	if not self.combattarget:
		HuntTarget (self)
		return

	self.goalentity = self.movetarget = g_utils.G_PickTarget(self.combattarget)
	if not self.movetarget:
		self.goalentity = self.movetarget = self.enemy
		HuntTarget (self)
		g_main.gi.dprintf("%s at %s, combattarget %s not found\n", self.classname, g_utils.vtos(self.s.origin), self.combattarget)
		return

	# clear out our combattarget, these are a one shot deal
	self.combattarget = None
	self.monsterinfo.aiflags |= AI_COMBAT_POINT

	# clear the targetname, that point is ours!
	self.movetarget.targetname = None
	self.monsterinfo.pausetime = 0

	# run for it
	self.monsterinfo.run (self)


"""
===========
FindTarget

Self is currently not attacking anything, so try to find a target
===========
"""
def FindTarget (self):
	#edict_t *client
	#qboolean heardit
	#int r
	heardit = False

	if self.monsterinfo.aiflags & AI_GOOD_GUY:
		if self.goalentity and self.goalentity.inuse and self.goalentity.classname:
			if self.goalentity.classname == "target_actor":
				return False

		return False

	# if we're going to a combat point, just proceed
	if self.monsterinfo.aiflags & AI_COMBAT_POINT:
		return False

	heardit = False
	if (g_main.level.sight_entity_framenum >= (g_main.level.framenum - 1)) and not (self.spawnflags & 1) :
		client = g_main.level.sight_entity
		if client.enemy == self.enemy:
			return False
	elif g_main.level.sound_entity_framenum >= (g_main.level.framenum - 1):
		client = g_main.level.sound_entity
		heardit = True
	elif not (self.enemy) and (g_main.level.sound2_entity_framenum >= (g_main.level.framenum - 1)) and not (self.spawnflags & 1) :
		client = g_main.level.sound2_entity
		heardit = True
	else:
		client = g_main.level.sight_client
		if not client:
			return False	# no clients to get mad at

	# if the entity went away, forget it
	if not client.inuse:
		return False

	if client == self.enemy:
		return True

	if client.client:
		if client.flags & FL_NOTARGET:
			return False
	elif client.svflags & SVF_MONSTER:
		if not client.enemy:
			return False
		if client.enemy.flags & FL_NOTARGET:
			return False
	elif heardit:
		if client.owner.flags & FL_NOTARGET:
			return False
	else:
		return False

	if not heardit:
		r = range (self, client)

		if r == RANGE_FAR:
			return False

		# is client in an spot too dark to be seen?
		if client.light_level <= 5:
			return False

		if not visible (self, client):
			return False

		if r == RANGE_NEAR:
			if client.show_hostile < g_main.level.time and not infront (self, client):
				return False
		elif r == RANGE_MID:
			if not infront (self, client):
				return False

		self.enemy = client

		if self.enemy.classname != "player_noise":
			self.monsterinfo.aiflags &= ~AI_SOUND_TARGET

			if not self.enemy.client:
				self.enemy = self.enemy.enemy
				if not self.enemy.client:
					self.enemy = None
					return False
	else:	# heardit
		#vec3_t temp
		temp = [0, 0, 0]

		if self.spawnflags & 1:
			if not visible (self, client):
				return False
		else:
			if not g_main.gi.inPHS(self.s.origin, client.s.origin):
				return False

		q_shared.VectorSubtract (client.s.origin, self.s.origin, temp)

		if q_shared.VectorLength(temp) > 1000:	# too far to hear
			return False

		# check area portals
		if client.areanum != self.areanum:
			if not g_main.gi.AreasConnected(self.areanum, client.areanum):
				return False

		self.ideal_yaw = g_utils.vectoyaw(temp)
		m_move.M_ChangeYaw (self)

		# hunt the sound for a bit; hopefully find the real player
		self.monsterinfo.aiflags |= AI_SOUND_TARGET
		self.enemy = client

	#
	# got one
	#
	FoundTarget (self)

	if not (self.monsterinfo.aiflags & AI_SOUND_TARGET) and (self.monsterinfo.sight):
		self.monsterinfo.sight (self, self.enemy)

	return True


"""
=============================================================================
"""
def FacingIdeal(self):
	#float delta
	delta = q_shared.anglemod(self.s.angles[YAW] - self.ideal_yaw)
	if delta > 45 and delta < 315:
		return False
	return True


def M_CheckAttack (self):
	#vec3_t spot1, spot2
	#float chance
	spot1 = [0, 0, 0]
	spot2 = [0, 0, 0]

	if self.enemy.health > 0:
		# see if any entities are in the way of the shot
		q_shared.VectorCopy (self.s.origin, spot1)
		spot1[2] += self.viewheight
		q_shared.VectorCopy (self.enemy.s.origin, spot2)
		spot2[2] += self.enemy.viewheight

		tr = g_main.gi.trace (spot1, None, None, spot2, self, CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_SLIME|CONTENTS_LAVA|CONTENTS_WINDOW)

		# do we have a clear shot?
		if tr.ent != self.enemy:
			return False

	# melee attack
	if enemy_range == RANGE_MELEE:
		# don't always melee in easy mode
		if g_main.skill.value == 0 and (_r.randint(0, 2147483647) & 3) :
			return False
		if self.monsterinfo.melee:
			self.monsterinfo.attack_state = AS_MELEE
		else:
			self.monsterinfo.attack_state = AS_MISSILE
		return True

	# missile attack
	if not self.monsterinfo.attack:
		return False

	if g_main.level.time < self.monsterinfo.attack_finished:
		return False

	if enemy_range == RANGE_FAR:
		return False

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		chance = 0.4
	elif enemy_range == RANGE_MELEE:
		chance = 0.2
	elif enemy_range == RANGE_NEAR:
		chance = 0.1
	elif enemy_range == RANGE_MID:
		chance = 0.02
	else:
		return False

	if g_main.skill.value == 0:
		chance *= 0.5
	elif g_main.skill.value >= 2:
		chance *= 2

	if g_local.random () < chance:
		self.monsterinfo.attack_state = AS_MISSILE
		self.monsterinfo.attack_finished = g_main.level.time + 2*g_local.random()
		return True

	if self.flags & FL_FLY:
		if g_local.random() < 0.3:
			self.monsterinfo.attack_state = AS_SLIDING
		else:
			self.monsterinfo.attack_state = AS_STRAIGHT

	return False


"""
=============
ai_run_melee
=============
"""
def ai_run_melee(self):
	self.ideal_yaw = enemy_yaw
	m_move.M_ChangeYaw (self)

	if FacingIdeal(self):
		self.monsterinfo.melee (self)
		self.monsterinfo.attack_state = AS_STRAIGHT


"""
=============
ai_run_missile
=============
"""
def ai_run_missile(self):
	self.ideal_yaw = enemy_yaw
	m_move.M_ChangeYaw (self)

	if FacingIdeal(self):
		self.monsterinfo.attack (self)
		self.monsterinfo.attack_state = AS_STRAIGHT


"""
=============
ai_run_slide

Strafe sideways, but stay at aproximately the same range
=============
"""
def ai_run_slide(self, distance):
	#float ofs
	if self.monsterinfo.lefty:
		ofs = 90
	else:
		ofs = -90

	self.ideal_yaw = enemy_yaw
	m_move.M_ChangeYaw (self)

	if m_move.M_walkmove (self, self.ideal_yaw + ofs, distance):
		return

	self.monsterinfo.lefty = 1 - self.monsterinfo.lefty
	m_move.M_walkmove (self, self.ideal_yaw - ofs, distance)


"""
=============
ai_checkattack

Decides if we're going to attack or do something else
=============
"""
def ai_checkattack (self, dist):
	#vec3_t temp
	#qboolean hesDeadJim
	temp = [0, 0, 0]
	hesDeadJim = False

	# this causes monsters to run blindly to the combat point w/o firing
	if self.goalentity:
		if self.monsterinfo.aiflags & AI_COMBAT_POINT:
			return False

		if self.monsterinfo.aiflags & AI_SOUND_TARGET:
			if (g_main.level.time - self.enemy.teleport_time) > 5.0:
				if self.goalentity == self.enemy:
					if self.movetarget:
						self.goalentity = self.movetarget
					else:
						self.goalentity = None
				self.monsterinfo.aiflags &= ~AI_SOUND_TARGET
				if self.monsterinfo.aiflags & AI_TEMP_STAND_GROUND:
					self.monsterinfo.aiflags &= ~(AI_STAND_GROUND | AI_TEMP_STAND_GROUND)
			else:
				self.show_hostile = g_main.level.time + 1
				return False

	enemy_vis = False

	# see if the enemy is dead
	hesDeadJim = False
	if (not self.enemy) or (not self.enemy.inuse):
		hesDeadJim = True
	elif self.monsterinfo.aiflags & AI_MEDIC:
		if self.enemy.health > 0:
			hesDeadJim = True
			self.monsterinfo.aiflags &= ~AI_MEDIC
	elif self.monsterinfo.aiflags & AI_BRUTAL:
		if self.enemy.health <= -80:
			hesDeadJim = True
	else:
		if self.enemy.health <= 0:
			hesDeadJim = True

	if hesDeadJim:
		self.enemy = None
		# FIXME: look all around for other targets
		if self.oldenemy and self.oldenemy.health > 0:
			self.enemy = self.oldenemy
			self.oldenemy = None
			HuntTarget (self)
		else:
			if self.movetarget:
				self.goalentity = self.movetarget
				self.monsterinfo.walk (self)
			else:
				# we need the pausetime otherwise the stand code
				# will just revert to walking with no target
				self.monsterinfo.pausetime = g_main.level.time + 100000000
				self.monsterinfo.stand (self)
			return True

	self.show_hostile = g_main.level.time + 1		# wake up other monsters

	# check knowledge of enemy
	enemy_vis = visible(self, self.enemy)
	if enemy_vis:
		self.monsterinfo.search_time = g_main.level.time + 5
		q_shared.VectorCopy (self.enemy.s.origin, self.monsterinfo.last_sighting)

	enemy_infront = infront(self, self.enemy)
	enemy_range = range(self, self.enemy)
	q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, temp)
	enemy_yaw = g_utils.vectoyaw(temp)

	if self.monsterinfo.attack_state == AS_MISSILE:
		ai_run_missile (self)
		return True
	if self.monsterinfo.attack_state == AS_MELEE:
		ai_run_melee (self)
		return True

	# if enemy is not currently visible, we will never attack
	if not enemy_vis:
		return False

	return self.monsterinfo.checkattack (self)


"""
=============
ai_run

The monster has an enemy it is trying to kill
=============
"""
def ai_run (self, dist):
	#vec3_t v
	#edict_t *tempgoal, *save, *marker
	#qboolean new
	#float d1, d2, left, center, right
	v = [0, 0, 0]
	new = False

	# if we're going to a combat point, just proceed
	if self.monsterinfo.aiflags & AI_COMBAT_POINT:
		m_move.M_MoveToGoal (self, dist)
		return

	if self.monsterinfo.aiflags & AI_SOUND_TARGET:
		q_shared.VectorSubtract (self.s.origin, self.enemy.s.origin, v)
		if q_shared.VectorLength(v) < 64:
			self.monsterinfo.aiflags |= (AI_STAND_GROUND | AI_TEMP_STAND_GROUND)
			self.monsterinfo.stand (self)
			return

		m_move.M_MoveToGoal (self, dist)

		if not FindTarget (self):
			return

	if ai_checkattack (self, dist):
		return

	if self.monsterinfo.attack_state == AS_SLIDING:
		ai_run_slide (self, dist)
		return

	if enemy_vis:
		m_move.M_MoveToGoal (self, dist)
		self.monsterinfo.aiflags &= ~AI_LOST_SIGHT
		q_shared.VectorCopy (self.enemy.s.origin, self.monsterinfo.last_sighting)
		self.monsterinfo.trail_time = g_main.level.time
		return

	# coop will change to another enemy if visible
	if g_main.coop.value:
		if FindTarget (self):
			return

	if (self.monsterinfo.search_time) and (g_main.level.time > (self.monsterinfo.search_time + 20)):
		m_move.M_MoveToGoal (self, dist)
		self.monsterinfo.search_time = 0
		return

	save = self.goalentity
	tempgoal = g_utils.G_Spawn()
	self.goalentity = tempgoal

	new = False

	if not (self.monsterinfo.aiflags & AI_LOST_SIGHT):
		self.monsterinfo.aiflags |= (AI_LOST_SIGHT | AI_PURSUIT_LAST_SEEN)
		self.monsterinfo.aiflags &= ~(AI_PURSUE_NEXT | AI_PURSUE_TEMP)
		new = True

	if self.monsterinfo.aiflags & AI_PURSUE_NEXT:
		self.monsterinfo.aiflags &= ~AI_PURSUE_NEXT

		# give ourself more time since we got this far
		self.monsterinfo.search_time = g_main.level.time + 5

		if self.monsterinfo.aiflags & AI_PURSUE_TEMP:
			self.monsterinfo.aiflags &= ~AI_PURSUE_TEMP
			marker = None
			q_shared.VectorCopy (self.monsterinfo.saved_goal, self.monsterinfo.last_sighting)
			new = True
		elif self.monsterinfo.aiflags & AI_PURSUIT_LAST_SEEN:
			self.monsterinfo.aiflags &= ~AI_PURSUIT_LAST_SEEN
			marker = p_trail.PlayerTrail_PickFirst (self)
		else:
			marker = p_trail.PlayerTrail_PickNext (self)

		if marker:
			q_shared.VectorCopy (marker.s.origin, self.monsterinfo.last_sighting)
			self.monsterinfo.trail_time = marker.timestamp
			self.s.angles[YAW] = self.ideal_yaw = marker.s.angles[YAW]
			new = True

	q_shared.VectorSubtract (self.s.origin, self.monsterinfo.last_sighting, v)
	d1 = q_shared.VectorLength(v)
	if d1 <= dist:
		self.monsterinfo.aiflags |= AI_PURSUE_NEXT
		dist = d1

	q_shared.VectorCopy (self.monsterinfo.last_sighting, self.goalentity.s.origin)

	if new:
		#vec3_t v_forward, v_right, left_target, right_target
		v_forward = [0, 0, 0]
		v_right = [0, 0, 0]
		left_target = [0, 0, 0]
		right_target = [0, 0, 0]

		tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, self.monsterinfo.last_sighting, self, MASK_PLAYERSOLID)
		if tr.fraction < 1:
			q_shared.VectorSubtract (self.goalentity.s.origin, self.s.origin, v)
			d1 = q_shared.VectorLength(v)
			center = tr.fraction
			d2 = d1 * ((center+1)/2)
			self.s.angles[YAW] = self.ideal_yaw = g_utils.vectoyaw(v)
			q_shared.AngleVectors(self.s.angles, v_forward, v_right, None)

			q_shared.VectorSet(v, d2, -16, 0)
			g_utils.G_ProjectSource (self.s.origin, v, v_forward, v_right, left_target)
			tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, left_target, self, MASK_PLAYERSOLID)
			left = tr.fraction

			q_shared.VectorSet(v, d2, 16, 0)
			g_utils.G_ProjectSource (self.s.origin, v, v_forward, v_right, right_target)
			tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, right_target, self, MASK_PLAYERSOLID)
			right = tr.fraction

			center = (d1*center)/d2
			if (left >= center and left > right):
				if left < 1:
					q_shared.VectorSet(v, d2 * left * 0.5, -16, 0)
					g_utils.G_ProjectSource (self.s.origin, v, v_forward, v_right, left_target)
				q_shared.VectorCopy (self.monsterinfo.last_sighting, self.monsterinfo.saved_goal)
				self.monsterinfo.aiflags |= AI_PURSUE_TEMP
				q_shared.VectorCopy (left_target, self.goalentity.s.origin)
				q_shared.VectorCopy (left_target, self.monsterinfo.last_sighting)
				q_shared.VectorSubtract (self.goalentity.s.origin, self.s.origin, v)
				self.s.angles[YAW] = self.ideal_yaw = g_utils.vectoyaw(v)
			elif (right >= center and right > left):
				if right < 1:
					q_shared.VectorSet(v, d2 * right * 0.5, 16, 0)
					g_utils.G_ProjectSource (self.s.origin, v, v_forward, v_right, right_target)
				q_shared.VectorCopy (self.monsterinfo.last_sighting, self.monsterinfo.saved_goal)
				self.monsterinfo.aiflags |= AI_PURSUE_TEMP
				q_shared.VectorCopy (right_target, self.goalentity.s.origin)
				q_shared.VectorCopy (right_target, self.monsterinfo.last_sighting)
				q_shared.VectorSubtract (self.goalentity.s.origin, self.s.origin, v)
				self.s.angles[YAW] = self.ideal_yaw = g_utils.vectoyaw(v)

	m_move.M_MoveToGoal (self, dist)

	g_utils.G_FreeEdict(tempgoal)

	if self:
		self.goalentity = save
