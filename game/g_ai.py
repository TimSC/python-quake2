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

The basic AI functions like enemy detection, attacking and so on.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from common.shared import rand

from game import g_main
from game import g_utils
from game import g_monster
from game.header.game import SVF_MONSTER
from common.header.shared import MASK_OPAQUE, MASK_PLAYERSOLID, CONTENTS_SOLID, CONTENTS_MONSTER, CONTENTS_SLIME, CONTENTS_LAVA, CONTENTS_WINDOW, YAW
from common.shared.shared import vec3_origin
from game.header.local import FL_NOTARGET, MELEE_DISTANCE, RANGE_MELEE, RANGE_NEAR, RANGE_MID, RANGE_FAR, AI_STAND_GROUND, AI_TEMP_STAND_GROUND, AI_GOOD_GUY, AI_COMBAT_POINT, AI_SOUND_TARGET, AI_MEDIC, AI_BRUTAL, AI_LOST_SIGHT, AI_PURSUE_NEXT, AI_PURSUE_TEMP, AI_PURSUIT_LAST_SEEN, AS_MELEE, AS_MISSILE, AS_SLIDING, AS_STRAIGHT, FL_FLY
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from game.player import trail as p_trail
from game.monster.misc import move as m_move

"""
#include "header/local.h"
"""

enemy_vis = False
enemy_infront = False
enemy_range = 0
enemy_yaw = 0.0

"""
=================
AI_SetSightClient

Called once each frame to set level.sight_client to the
player to be checked for in findtarget.
=================
"""
"""
// g_ai.c

#include "g_local.h"

"""

"""
============================================================================
"""


def AI_SetSightClient ():
	#edict_t *ent
	#int start, check
	edicts = g_main.g_edicts
	if g_main.level.sight_client is None:
		start = 1
	else:
		start = edicts.index(g_main.level.sight_client) #level.sight_client - g_edicts;

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
	if not self:

		return


	m_move.M_walkmove (self, self.s.angles[YAW], dist)


"""
=============
ai_stand

Used for standing around and looking for players
==============
"""
def ai_stand(self, dist): #edict_t *, float

	"""
	vec3_t v;
	"""
	v = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	if dist:

		m_move.M_walkmove(self, self.s.angles[YAW], dist)


	if self.monsterinfo.aiflags & AI_STAND_GROUND:

		if self.enemy:

			shared.VectorSubtract(self.enemy.s.origin, self.s.origin, v)
			self.ideal_yaw = g_utils.vectoyaw(v)

			if (self.s.angles[YAW] != self.ideal_yaw) and self.monsterinfo.aiflags & AI_TEMP_STAND_GROUND:

				self.monsterinfo.aiflags &= ~(AI_STAND_GROUND | AI_TEMP_STAND_GROUND)
				self.monsterinfo.run(self)


			m_move.M_ChangeYaw(self)
			ai_checkattack(self)

		else:

			FindTarget(self)


		return


	if FindTarget(self):

		return


	if g_main.level.time > self.monsterinfo.pausetime:

		self.monsterinfo.walk(self)
		return


	if not (self.spawnflags & 1) and (self.monsterinfo.idle) and (g_main.level.time > self.monsterinfo.idle_time):

		if self.monsterinfo.idle_time:

			self.monsterinfo.idle(self)
			self.monsterinfo.idle_time = g_main.level.time + 15 + local.random() * 15

		else:

			self.monsterinfo.idle_time = g_main.level.time + local.random() * 15


"""
=============
ai_walk

The monster is walking it's beat
=============
"""
def ai_walk (self, dist):
	if not self:

		return


	m_move.M_MoveToGoal (self, dist)

	# check for noticing a player
	if FindTarget (self):
		return

	if (self.monsterinfo.search) and (g_main.level.time > self.monsterinfo.idle_time):
		if self.monsterinfo.idle_time:
			self.monsterinfo.search (self)
			self.monsterinfo.idle_time = g_main.level.time + 15 + local.random() * 15
		else:
			self.monsterinfo.idle_time = g_main.level.time + local.random() * 15


"""
=============
ai_charge

Turns towards target and advances
==============
"""
def ai_charge(self, dist): #edict_t *, float

	"""
	vec3_t v;
	"""
	v = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	if self.enemy:

		shared.VectorSubtract(self.enemy.s.origin, self.s.origin, v)


	self.ideal_yaw = g_utils.vectoyaw(v)
	m_move.M_ChangeYaw(self)

	if dist:

		m_move.M_walkmove(self, self.s.angles[YAW], dist)


"""
=============
ai_turn

don't move, but turn towards ideal_yaw
=============
"""
def ai_turn (self, dist):
	if not self:

		return


	if dist:
		m_move.M_walkmove (self, self.s.angles[YAW], dist)

	if FindTarget (self):
		return

	m_move.M_ChangeYaw (self)


"""
 ============================================================================
"""
def ai_range(self, other): #edict_t *, edict_t * (returns int)

	"""
	vec3_t v;
	float len;
	"""
	v = np.zeros((3,), dtype=np.float32)

	if not self or not other:

		return 0


	shared.VectorSubtract(self.s.origin, other.s.origin, v)
	len_ = shared_c.VectorLength(v)

	if len_ < MELEE_DISTANCE:

		return RANGE_MELEE


	if len_ < 500:

		return RANGE_NEAR


	if len_ < 1000:

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
	if not self or not other:

		return False


	spot1 = [0, 0, 0]
	spot2 = [0, 0, 0]

	shared.VectorCopy (self.s.origin, spot1)
	spot1[2] += self.viewheight
	shared.VectorCopy (other.s.origin, spot2)
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
	if not self or not other:

		return False


	vec = [0, 0, 0]
	forward = [0, 0, 0]

	shared_c.AngleVectors (self.s.angles, forward, None, None)
	shared.VectorSubtract (other.s.origin, self.s.origin, vec)
	shared_c.VectorNormalize (vec)
	dot = shared.DotProduct (vec, forward)

	if dot > 0.3:
		return True
	return False


def HuntTarget(self): #edict_t * (static)

	"""
	vec3_t vec;
	"""
	vec = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	self.goalentity = self.enemy

	if self.monsterinfo.aiflags & AI_STAND_GROUND:

		self.monsterinfo.stand(self)

	else:

		self.monsterinfo.run(self)


	if visible(self, self.enemy):

		shared.VectorSubtract(self.enemy.s.origin, self.s.origin, vec)

	else:

		shared.VectorClear(vec)


	self.ideal_yaw = g_utils.vectoyaw(vec)

	# wait a while before first attack
	if not (self.monsterinfo.aiflags & AI_STAND_GROUND):

		g_monster.AttackFinished(self, 1)


def FoundTarget(self): #edict_t *

	"""
	edict_t *combatpoint;
	vec3_t v;
	"""
	v = np.zeros((3,), dtype=np.float32)

	if not self or not self.enemy or not self.enemy.inuse:

		return


	# let other monsters see this monster for a while
	if self.enemy.client:

		g_main.level.sight_entity = self
		g_main.level.sight_entity_framenum = g_main.level.framenum
		g_main.level.sight_entity.light_level = 128


	self.show_hostile = g_main.level.time + 1

	shared.VectorCopy(self.enemy.s.origin, self.monsterinfo.last_sighting)
	self.monsterinfo.trail_time = g_main.level.time

	if not self.combattarget:

		HuntTarget(self)
		return


	combatpoint = g_utils.G_PickTarget(self.combattarget)

	if not combatpoint:

		g_main.gi.dprintf("%s at %s, combattarget %s not found\n", self.classname, g_utils.vtos(self.s.origin), self.combattarget)

		HuntTarget(self)
		return


	shared.VectorSubtract(combatpoint.s.origin, self.s.origin, v)
	self.ideal_yaw = g_utils.vectoyaw(v)

	# clear out our combattarget, these are a one shot deal
	self.combattarget = None
	self.monsterinfo.aiflags |= AI_COMBAT_POINT
	self.monsterinfo.pausetime = 0

	# clear the targetname, that point is ours!
	combatpoint.targetname = None
	self.goalentity = self.movetarget = combatpoint

	# run for it
	self.monsterinfo.run(self)


"""
===========
FindTarget

Self is currently not attacking anything, so try to find a target
===========
"""
def FindTarget(self): #edict_t * (returns qboolean)

	"""
	edict_t *client;
	qboolean heardit;
	int r;
	"""

	if not self:

		return False


	if self.monsterinfo.aiflags & AI_GOOD_GUY:

		return False


	# if we're going to a combat point, just proceed
	if self.monsterinfo.aiflags & AI_COMBAT_POINT:

		return False


	# if the first spawnflag bit is set, the monster
	# will only wake up on really seeing the player,
	# not another monster getting angry or hearing
	# something

	heardit = False

	if (g_main.level.sight_entity_framenum >= (g_main.level.framenum - 1)) and not (self.spawnflags & 1):

		client = g_main.level.sight_entity

		if client.enemy == self.enemy:

			return False


	elif g_main.level.sound_entity_framenum >= (g_main.level.framenum - 1):

		client = g_main.level.sound_entity
		heardit = True

	elif not (self.enemy) and (g_main.level.sound2_entity_framenum >= (g_main.level.framenum - 1)) and not (self.spawnflags & 1):

		client = g_main.level.sound2_entity
		heardit = True

	else:

		client = g_main.level.sight_client


	# if the entity went away, forget it
	if not client or not client.inuse or (client.client and g_main.level.intermissiontime):

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

		r = ai_range(self, client)

		if r == RANGE_FAR:

			return False


		# is client in an spot too dark to be seen?
		if client.light_level <= 5:

			return False


		if not visible(self, client):

			return False


		if r == RANGE_NEAR:

			if (client.show_hostile < g_main.level.time) and not infront(self, client):

				return False


		elif r == RANGE_MID:

			if not infront(self, client):

				return False



		self.enemy = client

		if (self.enemy.classname != "player_noise"):

			self.monsterinfo.aiflags &= ~AI_SOUND_TARGET

			if not self.enemy.client:

				self.enemy = self.enemy.enemy

				if not self.enemy.client:

					self.enemy = None
					return False




	else:

		#vec3_t temp;
		temp = np.zeros((3,), dtype=np.float32)

		if self.spawnflags & 1:

			if not visible(self, client):

				return False


		else:

			if not g_main.gi.inPHS(self.s.origin, client.s.origin):

				return False



		shared.VectorSubtract(client.s.origin, self.s.origin, temp)

		if shared_c.VectorLength(temp) > 1000:

			return False


		# check area portals - if they are different
		# and not connected then we can't hear it
		if client.areanum != self.areanum:

			if not g_main.gi.AreasConnected(self.areanum, client.areanum):

				return False



		self.ideal_yaw = g_utils.vectoyaw(temp)
		m_move.M_ChangeYaw(self)

		# hunt the sound for a bit; hopefully find the real player
		self.monsterinfo.aiflags |= AI_SOUND_TARGET
		self.enemy = client


	FoundTarget(self)

	if not (self.monsterinfo.aiflags & AI_SOUND_TARGET) and (self.monsterinfo.sight):

		self.monsterinfo.sight(self, self.enemy)


	return True


"""
=============================================================================
"""
def FacingIdeal(self):
	#float delta
	if not self:

		return False


	delta = shared_c.anglemod(self.s.angles[YAW] - self.ideal_yaw)
	if delta > 45 and delta < 315:
		return False
	return True


def M_CheckAttack(self): #edict_t * (returns qboolean)

	"""
	vec3_t spot1, spot2;
	float chance;
	trace_t tr;
	"""
	spot1 = np.zeros((3,), dtype=np.float32)
	spot2 = np.zeros((3,), dtype=np.float32)

	if not self or not self.enemy or not self.enemy.inuse:

		return False


	if self.enemy.health > 0:

		# see if any entities are in the way of the shot
		shared.VectorCopy(self.s.origin, spot1)
		spot1[2] += self.viewheight
		shared.VectorCopy(self.enemy.s.origin, spot2)
		spot2[2] += self.enemy.viewheight

		tr = g_main.gi.trace(spot1, None, None, spot2, self, CONTENTS_SOLID | CONTENTS_MONSTER | CONTENTS_SLIME | CONTENTS_LAVA | CONTENTS_WINDOW)

		# do we have a clear shot?
		if tr.ent != self.enemy:

			return False



	# melee attack
	if enemy_range == RANGE_MELEE:

		# don't always melee in easy mode
		if (g_main.skill.value == local.SKILL_EASY) and (rand.randk() & 3):

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

	elif enemy_range == RANGE_NEAR:

		chance = 0.1

	elif enemy_range == RANGE_MID:

		chance = 0.02

	else:

		return False


	if g_main.skill.value == local.SKILL_EASY:

		chance *= 0.5

	elif g_main.skill.value >= local.SKILL_HARD:

		chance *= 2


	if local.random() < chance:

		self.monsterinfo.attack_state = AS_MISSILE
		self.monsterinfo.attack_finished = g_main.level.time + 2 * local.random()
		return True


	if self.flags & FL_FLY:

		if local.random() < 0.3:

			self.monsterinfo.attack_state = AS_SLIDING

		else:

			self.monsterinfo.attack_state = AS_STRAIGHT



	return False


"""
=============
ai_run_melee
=============
"""
def ai_run_melee(self): #edict_t *

	if not self:

		return


	self.ideal_yaw = enemy_yaw
	m_move.M_ChangeYaw(self)

	if FacingIdeal(self):

		if self.monsterinfo.melee:
			self.monsterinfo.melee(self)
			self.monsterinfo.attack_state = AS_STRAIGHT


"""
=============
ai_run_missile
=============
"""
def ai_run_missile(self): #edict_t *

	if not self:

		return


	self.ideal_yaw = enemy_yaw
	m_move.M_ChangeYaw(self)

	if FacingIdeal(self):

		if self.monsterinfo.attack:
			self.monsterinfo.attack(self)
			self.monsterinfo.attack_state = AS_STRAIGHT


"""
=============
ai_run_slide

Strafe sideways, but stay at aproximately the same range
=============
"""
def ai_run_slide(self, distance):
	#float ofs
	if not self:

		return


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
 * Decides if we're going to attack
 * or do something else used by
 * ai_run and ai_stand

"""
def hesDeadJim(self): #const edict_t * (returns static qboolean)

	"""
	const edict_t *enemy = self->enemy;
	"""
	enemy = self.enemy

	if not enemy or not enemy.inuse:

		return True


	if self.monsterinfo.aiflags & AI_MEDIC:

		return (enemy.health > 0)


	if enemy.client and g_main.level.intermissiontime:

		return True


	if self.monsterinfo.aiflags & AI_BRUTAL:

		return (enemy.health <= -80)


	return (enemy.health <= 0)

"""
=============
ai_checkattack

Decides if we're going to attack or do something else
=============
"""
def ai_checkattack(self): #edict_t * (returns qboolean)
	global enemy_infront, enemy_range, enemy_vis, enemy_yaw

	"""
	vec3_t temp;
	"""
	temp = np.zeros((3,), dtype=np.float32)

	if not self:

		enemy_vis = False

		return False


	# this causes monsters to run blindly
	# to the combat point w/o firing
	if self.goalentity:

		if self.monsterinfo.aiflags & AI_COMBAT_POINT:

			return False


		if (self.monsterinfo.aiflags & AI_SOUND_TARGET) and not visible(self, self.goalentity):

			if (g_main.level.time - self.enemy.last_sound_time) > 5.0:

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
	if hesDeadJim(self):

		self.enemy = None
		self.monsterinfo.aiflags &= ~AI_MEDIC

		if self.oldenemy and (self.oldenemy.health > 0):

			self.enemy = self.oldenemy
			self.oldenemy = None
			HuntTarget(self)

		else:

			if self.movetarget:

				self.goalentity = self.movetarget
				self.monsterinfo.walk(self)

			else:

				# we need the pausetime otherwise the stand code
				# will just revert to walking with no target and
				# the monsters will wonder around aimlessly trying
				# to hunt the world entity
				self.monsterinfo.pausetime = g_main.level.time + 100000000
				self.monsterinfo.stand(self)


			return True



	# wake up other monsters
	self.show_hostile = g_main.level.time + 1

	# check knowledge of enemy
	enemy_vis = visible(self, self.enemy)

	if enemy_vis:

		self.monsterinfo.search_time = g_main.level.time + 5
		shared.VectorCopy(self.enemy.s.origin, self.monsterinfo.last_sighting)


	# look for other coop players here
	if g_main.coop.value and (self.monsterinfo.search_time < g_main.level.time):

		if FindTarget(self):

			return True



	if self.enemy:

		enemy_infront = infront(self, self.enemy)
		enemy_range = ai_range(self, self.enemy)
		shared.VectorSubtract(self.enemy.s.origin, self.s.origin, temp)
		enemy_yaw = g_utils.vectoyaw(temp)


	if self.monsterinfo.attack_state == AS_MISSILE:

		ai_run_missile(self)
		return True


	if self.monsterinfo.attack_state == AS_MELEE:

		ai_run_melee(self)
		return True


	# if enemy is not currently visible,
	# we will never attack
	if not enemy_vis:

		return False


	return self.monsterinfo.checkattack(self)


"""
=============
ai_run

The monster has an enemy it is trying to kill
=============
"""
def ai_run(self, dist): #edict_t *, float

	"""
	vec3_t v;
	edict_t *tempgoal;
	edict_t *save;
	qboolean new;
	edict_t *marker;
	float d1, d2;
	trace_t tr;
	vec3_t v_forward, v_right;
	float left, center, right;
	vec3_t left_target, right_target;
	"""
	v = np.zeros((3,), dtype=np.float32)
	v_forward = np.zeros((3,), dtype=np.float32)
	v_right = np.zeros((3,), dtype=np.float32)
	left_target = np.zeros((3,), dtype=np.float32)
	right_target = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	# if we're going to a combat point, just proceed
	if self.monsterinfo.aiflags & AI_COMBAT_POINT:

		m_move.M_MoveToGoal(self, dist)
		return


	if self.monsterinfo.aiflags & AI_SOUND_TARGET:

		# Special case: Some projectiles like grenades or rockets are
		# classified as an enemy. When they explode they generate a
		# sound entity, triggering this code path. Since they're gone
		# after the explosion their entity pointer is NULL. Therefor
		# self->enemy is also NULL and we're crashing. Work around
		# this by predending that the enemy is still there, and move
		# to it.
		if self.enemy:

			shared.VectorSubtract(self.s.origin, self.enemy.s.origin, v)

			if shared_c.VectorLength(v) < 64:

				self.monsterinfo.aiflags |= (AI_STAND_GROUND | AI_TEMP_STAND_GROUND)
				self.monsterinfo.stand(self)
				return



		m_move.M_MoveToGoal(self, dist)

		if not FindTarget(self):

			return



	if ai_checkattack(self):

		return


	if self.monsterinfo.attack_state == AS_SLIDING:

		ai_run_slide(self, dist)
		return


	if enemy_vis:

		m_move.M_MoveToGoal(self, dist)
		self.monsterinfo.aiflags &= ~AI_LOST_SIGHT
		shared.VectorCopy(self.enemy.s.origin, self.monsterinfo.last_sighting)
		self.monsterinfo.trail_time = g_main.level.time
		return


	if (self.monsterinfo.search_time) and (g_main.level.time > (self.monsterinfo.search_time + 20)):

		m_move.M_MoveToGoal(self, dist)
		self.monsterinfo.search_time = 0
		return


	tempgoal = g_utils.G_SpawnOptional()

	if not tempgoal:

		m_move.M_MoveToGoal(self, dist)
		return


	save = self.goalentity
	self.goalentity = tempgoal

	new = False

	if not (self.monsterinfo.aiflags & AI_LOST_SIGHT):

		# just lost sight of the player, decide where to go first
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
			shared.VectorCopy(self.monsterinfo.saved_goal, self.monsterinfo.last_sighting)
			new = True

		elif self.monsterinfo.aiflags & AI_PURSUIT_LAST_SEEN:

			self.monsterinfo.aiflags &= ~AI_PURSUIT_LAST_SEEN
			marker = p_trail.PlayerTrail_PickFirst(self)

		else:

			marker = p_trail.PlayerTrail_PickNext(self)


		if marker:

			shared.VectorCopy(marker.s.origin, self.monsterinfo.last_sighting)
			self.monsterinfo.trail_time = marker.timestamp
			self.s.angles[YAW] = self.ideal_yaw = marker.s.angles[YAW]
			new = True



	shared.VectorSubtract(self.s.origin, self.monsterinfo.last_sighting, v)
	d1 = shared_c.VectorLength(v)

	if d1 <= dist:

		self.monsterinfo.aiflags |= AI_PURSUE_NEXT
		dist = d1


	shared.VectorCopy(self.monsterinfo.last_sighting, self.goalentity.s.origin)

	if new:

		tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, self.monsterinfo.last_sighting, self, MASK_PLAYERSOLID)

		if tr.fraction < 1:

			shared.VectorSubtract(self.goalentity.s.origin, self.s.origin, v)
			d1 = shared_c.VectorLength(v)
			center = tr.fraction
			d2 = d1 * ((center + 1) / 2)
			self.s.angles[YAW] = self.ideal_yaw = g_utils.vectoyaw(v)
			shared_c.AngleVectors(self.s.angles, v_forward, v_right, None)

			shared.VectorSet(v, d2, -16, 0)
			g_utils.G_ProjectSource(self.s.origin, v, v_forward, v_right, left_target)
			tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, left_target, self, MASK_PLAYERSOLID)
			left = tr.fraction

			shared.VectorSet(v, d2, 16, 0)
			g_utils.G_ProjectSource(self.s.origin, v, v_forward, v_right, right_target)
			tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, right_target, self, MASK_PLAYERSOLID)
			right = tr.fraction

			center = (d1 * center) / d2

			if (left >= center) and (left > right):

				if left < 1:

					shared.VectorSet(v, d2 * left * 0.5, -16, 0)
					g_utils.G_ProjectSource(self.s.origin, v, v_forward, v_right, left_target)


				shared.VectorCopy(self.monsterinfo.last_sighting, self.monsterinfo.saved_goal)
				self.monsterinfo.aiflags |= AI_PURSUE_TEMP
				shared.VectorCopy(left_target, self.goalentity.s.origin)
				shared.VectorCopy(left_target, self.monsterinfo.last_sighting)
				shared.VectorSubtract(self.goalentity.s.origin, self.s.origin, v)
				self.s.angles[YAW] = self.ideal_yaw = g_utils.vectoyaw(v)

			elif (right >= center) and (right > left):

				if right < 1:

					shared.VectorSet(v, d2 * right * 0.5, 16, 0)
					g_utils.G_ProjectSource(self.s.origin, v, v_forward, v_right, right_target)


				shared.VectorCopy(self.monsterinfo.last_sighting, self.monsterinfo.saved_goal)
				self.monsterinfo.aiflags |= AI_PURSUE_TEMP
				shared.VectorCopy(right_target, self.goalentity.s.origin)
				shared.VectorCopy(right_target, self.monsterinfo.last_sighting)
				shared.VectorSubtract(self.goalentity.s.origin, self.s.origin, v)
				self.s.angles[YAW] = self.ideal_yaw = g_utils.vectoyaw(v)




	m_move.M_MoveToGoal(self, dist)

	g_utils.G_FreeEdict(tempgoal)

	self.goalentity = save
