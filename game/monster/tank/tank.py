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

Tank and Tank Commander.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_BRUTAL, AI_STAND_GROUND, DEAD_DEAD, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, GIB_METALLIC, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_blaster, monster_fire_bullet, monster_fire_rocket, walkmonster_start)
from game.g_utils import G_FreeEdict, G_ProjectSource, vectoangles
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_BODY, CHAN_VOICE, CHAN_WEAPON, EF_BLASTER, MZ2_TANK_BLASTER_1, MZ2_TANK_BLASTER_2, MZ2_TANK_BLASTER_3, MZ2_TANK_MACHINEGUN_1, MZ2_TANK_ROCKET_1, MZ2_TANK_ROCKET_2, MZ2_TANK_ROCKET_3
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.tank import tank_h

"""
#include "../../header/local.h"
#include "tank.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_tank.h


def _mf(aifunc, dist, thinkfunc):
	f = local.mframe_t()
	f.aifunc = aifunc
	f.dist = dist
	f.thinkfunc = thinkfunc
	return f

def _mm(first, last, frames, endfunc):
	m = local.mmove_t()
	m.firstframe = first
	m.lastframe = last
	m.frame = frames
	m.endfunc = endfunc
	return m

sound_thud = 0 # static
sound_pain = 0 # static
sound_idle = 0 # static
sound_die = 0 # static
sound_step = 0 # static
sound_sight = 0 # static
sound_windup = 0 # static
sound_strike = 0 # static


"""
==============================================================================

TANK

==============================================================================
"""
def tank_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def tank_footstep (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_BODY, sound_step, 1, ATTN_NORM, 0)


def tank_thud (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_BODY, sound_thud, 1, ATTN_NORM, 0)


def tank_windup (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_windup, 1, ATTN_NORM, 0)


def tank_idle (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def tank_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = tank_move_stand


def tank_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = tank_move_walk


def tank_run (self): #edict_t *

	if not self:

		return


	if self.enemy and self.enemy.client:
		self.monsterinfo.aiflags |= AI_BRUTAL
	else:
		self.monsterinfo.aiflags &= ~AI_BRUTAL

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = tank_move_stand
		return

	if self.monsterinfo.currentmove == tank_move_walk or self.monsterinfo.currentmove == tank_move_start_run:
		self.monsterinfo.currentmove = tank_move_run
	else:
		self.monsterinfo.currentmove = tank_move_start_run


def tank_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum |= 1


	if damage <= 10:

		return


	if g_main.level.time < self.pain_debounce_time:

		return


	if damage <= 30:

		if local.random() > 0.2:

			return


	# If hard or nightmare, don't go into pain while attacking
	if g_main.skill.value >= local.SKILL_HARD:

		if (self.s.frame >= tank_h.FRAME_attak301) and (self.s.frame <= tank_h.FRAME_attak330):

			return


		if (self.s.frame >= tank_h.FRAME_attak101) and (self.s.frame <= tank_h.FRAME_attak116):

			return


	self.pain_debounce_time = g_main.level.time + 3
	g_main.gi.sound(self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if damage <= 30:

		self.monsterinfo.currentmove = tank_move_pain1

	elif damage <= 60:

		self.monsterinfo.currentmove = tank_move_pain2

	else:

		self.monsterinfo.currentmove = tank_move_pain3


def TankBlaster (self): #edict_t *

	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	if self.s.frame == tank_h.FRAME_attak110:
		flash_number = MZ2_TANK_BLASTER_1
	elif self.s.frame == tank_h.FRAME_attak113:
		flash_number = MZ2_TANK_BLASTER_2
	else:
		# (self->s.frame == FRAME_attak116)
		flash_number = MZ2_TANK_BLASTER_3

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 30, 800, flash_number, EF_BLASTER)


def TankStrike (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_strike, 1, ATTN_NORM, 0)


def TankRocket (self): #edict_t *

	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	if self.s.frame == tank_h.FRAME_attak324:
		flash_number = MZ2_TANK_ROCKET_1
	elif self.s.frame == tank_h.FRAME_attak327:
		flash_number = MZ2_TANK_ROCKET_2
	else:
		# (self->s.frame == FRAME_attak330)
		flash_number = MZ2_TANK_ROCKET_3

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)

	monster_fire_rocket (self, start, dir, 50, 550, flash_number)


def TankMachineGun (self): #edict_t *

	if not self:

		return


	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	flash_number = MZ2_TANK_MACHINEGUN_1 + (self.s.frame - tank_h.FRAME_attak406)

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	if self.enemy:
		shared.VectorCopy (self.enemy.s.origin, vec)
		vec[2] += self.enemy.viewheight
		shared.VectorSubtract (vec, start, vec)
		vectoangles (vec, vec)
		dir[0] = vec[0]
	else:
		dir[0] = 0
	if self.s.frame <= tank_h.FRAME_attak415:
		dir[1] = self.s.angles[1] - 8 * (self.s.frame - tank_h.FRAME_attak411)
	else:
		dir[1] = self.s.angles[1] + 8 * (self.s.frame - tank_h.FRAME_attak419)
	dir[2] = 0

	shared_c.AngleVectors (dir, forward, None, None)

	monster_fire_bullet (self, start, forward, 20, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)


def tank_reattack_blaster(self): #edict_t *

	if not self:

		return


	if g_main.skill.value >= local.SKILL_HARD:

		if g_ai.visible(self, self.enemy):

			if self.enemy.health > 0:

				if local.random() <= 0.6:

					self.monsterinfo.currentmove = tank_move_reattack_blast
					return


	self.monsterinfo.currentmove = tank_move_attack_post_blast


def tank_poststrike (self): #edict_t *

	if not self:

		return


	self.enemy = None
	tank_run (self)


def tank_refire_rocket(self): #edict_t *

	if not self:

		return


	# Only on hard or nightmare
	if g_main.skill.value >= local.SKILL_HARD:

		if self.enemy.health > 0:

			if g_ai.visible(self, self.enemy):

				if local.random() <= 0.4:

					self.monsterinfo.currentmove = tank_move_attack_fire_rocket
					return


	self.monsterinfo.currentmove = tank_move_attack_post_rocket


def tank_doattack_rocket (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = tank_move_attack_fire_rocket


def tank_attack (self): #edict_t *

	if not self:

		return


	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#float	range;
	#float	r;

	if self.enemy.health < 0:
		self.monsterinfo.currentmove = tank_move_attack_strike
		self.monsterinfo.aiflags &= ~AI_BRUTAL
		return

	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range = shared_c.VectorLength (vec)

	r = local.random()

	if range <= 125:
		if r < 0.4:
			self.monsterinfo.currentmove = tank_move_attack_chain
		else:
			self.monsterinfo.currentmove = tank_move_attack_blast
	elif range <= 250:
		if r < 0.5:
			self.monsterinfo.currentmove = tank_move_attack_chain
		else:
			self.monsterinfo.currentmove = tank_move_attack_blast
	else:
		if r < 0.33:
			self.monsterinfo.currentmove = tank_move_attack_chain
		elif r < 0.66:
			self.monsterinfo.currentmove = tank_move_attack_pre_rocket
			self.pain_debounce_time = g_main.level.time + 5.0	# no pain for a while
		else:
			self.monsterinfo.currentmove = tank_move_attack_blast


def tank_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -16)
	shared.VectorSet (self.maxs, 16, 16, -0)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def tank_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	"""
	int n;
	"""

	if not self:

		return


	# check for gib
	if self.health <= self.gib_health:

		g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex("misc/udeath.wav"), 1, ATTN_NORM, 0)
		ThrowGib(self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		for n in range(4):

			ThrowGib(self, "models/objects/gibs/sm_metal/tris.md2", damage, GIB_METALLIC)


		ThrowGib(self, "models/objects/gibs/chest/tris.md2", damage, GIB_ORGANIC)
		ThrowHead(self, "models/objects/gibs/gear/tris.md2", damage, GIB_METALLIC)
		self.deadflag = DEAD_DEAD
		return


	if self.deadflag == DEAD_DEAD:

		return


	# regular death
	g_main.gi.sound(self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.monsterinfo.currentmove = tank_move_death


"""QUAKED monster_tank (1 .5 0) (-32 -32 -16) (32 32 72) Ambush Trigger_Spawn Sight
"""
"""QUAKED monster_tank_commander (1 .5 0) (-32 -32 -16) (32 32 72) Ambush Trigger_Spawn Sight
"""
def SP_monster_tank (self): #edict_t *

	global sound_thud, sound_pain, sound_idle, sound_die, sound_step, sound_sight, sound_windup, sound_strike
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	self.s.modelindex = g_main.gi.modelindex ("models/monsters/tank/tris.md2")
	shared.VectorSet (self.mins, -32, -32, -16)
	shared.VectorSet (self.maxs, 32, 32, 72)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX

	sound_pain = g_main.gi.soundindex ("tank/tnkpain2.wav")
	sound_thud = g_main.gi.soundindex ("tank/tnkdeth2.wav")
	sound_idle = g_main.gi.soundindex ("tank/tnkidle1.wav")
	sound_die = g_main.gi.soundindex ("tank/death.wav")
	sound_step = g_main.gi.soundindex ("tank/step.wav")
	sound_windup = g_main.gi.soundindex ("tank/tnkatck4.wav")
	sound_strike = g_main.gi.soundindex ("tank/tnkatck5.wav")
	sound_sight = g_main.gi.soundindex ("tank/sight1.wav")

	g_main.gi.soundindex ("tank/tnkatck1.wav")
	g_main.gi.soundindex ("tank/tnkatk2a.wav")
	g_main.gi.soundindex ("tank/tnkatk2b.wav")
	g_main.gi.soundindex ("tank/tnkatk2c.wav")
	g_main.gi.soundindex ("tank/tnkatk2d.wav")
	g_main.gi.soundindex ("tank/tnkatk2e.wav")
	g_main.gi.soundindex ("tank/tnkatck3.wav")

	if (self.classname == "monster_tank_commander"):
		self.health = 1000
		self.gib_health = -225
	else:
		self.health = 750
		self.gib_health = -200

	self.mass = 500

	self.pain = tank_pain
	self.die = tank_die
	self.monsterinfo.stand = tank_stand
	self.monsterinfo.walk = tank_walk
	self.monsterinfo.run = tank_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = tank_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = tank_sight
	self.monsterinfo.idle = tank_idle

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = tank_move_stand
	self.monsterinfo.scale = tank_h.MODEL_SCALE

	walkmonster_start(self)

	if (self.classname == "monster_tank_commander"):
		self.s.skinnum = 2


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
tank_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
tank_move_stand = _mm(tank_h.FRAME_stand01, tank_h.FRAME_stand30, tank_frames_stand, None)

tank_frames_start_walk = [
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 11, tank_footstep),
]
tank_move_start_walk = _mm(tank_h.FRAME_walk01, tank_h.FRAME_walk04, tank_frames_start_walk, tank_walk)

tank_frames_walk = [
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, tank_footstep),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 6, tank_footstep),
]
tank_move_walk = _mm(tank_h.FRAME_walk05, tank_h.FRAME_walk20, tank_frames_walk, None)

tank_frames_stop_walk = [
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 4, tank_footstep),
]
tank_move_stop_walk = _mm(tank_h.FRAME_walk21, tank_h.FRAME_walk25, tank_frames_stop_walk, tank_stand)

tank_frames_start_run = [
	_mf(ai_run, 0, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 11, tank_footstep),
]
tank_move_start_run = _mm(tank_h.FRAME_walk01, tank_h.FRAME_walk04, tank_frames_start_run, tank_run)

tank_frames_run = [
	_mf(ai_run, 4, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 4, None),
	_mf(ai_run, 4, tank_footstep),
	_mf(ai_run, 3, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 4, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 7, None),
	_mf(ai_run, 7, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 6, tank_footstep),
]
tank_move_run = _mm(tank_h.FRAME_walk05, tank_h.FRAME_walk20, tank_frames_run, None)

tank_frames_stop_run = [
	_mf(ai_run, 3, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 4, tank_footstep),
]
tank_move_stop_run = _mm(tank_h.FRAME_walk21, tank_h.FRAME_walk25, tank_frames_stop_run, tank_walk)

tank_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
tank_move_pain1 = _mm(tank_h.FRAME_pain101, tank_h.FRAME_pain104, tank_frames_pain1, tank_run)

tank_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
tank_move_pain2 = _mm(tank_h.FRAME_pain201, tank_h.FRAME_pain205, tank_frames_pain2, tank_run)

tank_frames_pain3 = [
	_mf(ai_move, -7, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, tank_footstep),
]
tank_move_pain3 = _mm(tank_h.FRAME_pain301, tank_h.FRAME_pain316, tank_frames_pain3, tank_run)

tank_frames_attack_blast = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),	# 10
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),	# 16
]
tank_move_attack_blast = _mm(tank_h.FRAME_attak101, tank_h.FRAME_attak116, tank_frames_attack_blast, tank_reattack_blaster)

tank_frames_reattack_blast = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),	# 16
]
tank_move_reattack_blast = _mm(tank_h.FRAME_attak111, tank_h.FRAME_attak116, tank_frames_reattack_blast, tank_reattack_blaster)

tank_frames_attack_post_blast = [
	_mf(ai_move, 0, None),	# 17
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, -2, tank_footstep),	# 22
]
tank_move_attack_post_blast = _mm(tank_h.FRAME_attak117, tank_h.FRAME_attak122, tank_frames_attack_post_blast, tank_run)

tank_frames_attack_strike = [
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 7, None),
	_mf(ai_move, 9, tank_footstep),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 2, tank_footstep),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 0, tank_windup),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, TankStrike),
	_mf(ai_move, 0, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -10, None),
	_mf(ai_move, -10, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -2, tank_footstep),
]
tank_move_attack_strike = _mm(tank_h.FRAME_attak201, tank_h.FRAME_attak238, tank_frames_attack_strike, tank_poststrike)

tank_frames_attack_pre_rocket = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 10
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 7, None),
	_mf(ai_charge, 7, None),
	_mf(ai_charge, 7, tank_footstep),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 20
	_mf(ai_charge, -3, None),
]
tank_move_attack_pre_rocket = _mm(tank_h.FRAME_attak301, tank_h.FRAME_attak321, tank_frames_attack_pre_rocket, tank_doattack_rocket)

tank_frames_attack_fire_rocket = [
	_mf(ai_charge, -3, None),	# Loop Start	22
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankRocket),	# 24
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankRocket),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -1, TankRocket),	# 30	Loop End
]
tank_move_attack_fire_rocket = _mm(tank_h.FRAME_attak322, tank_h.FRAME_attak330, tank_frames_attack_fire_rocket, tank_refire_rocket)

tank_frames_attack_post_rocket = [
	_mf(ai_charge, 0, None),	# 31
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 40
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -9, None),
	_mf(ai_charge, -8, None),
	_mf(ai_charge, -7, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -1, tank_footstep),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 50
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
tank_move_attack_post_rocket = _mm(tank_h.FRAME_attak331, tank_h.FRAME_attak353, tank_frames_attack_post_rocket, tank_run)

tank_frames_attack_chain = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
tank_move_attack_chain = _mm(tank_h.FRAME_attak401, tank_h.FRAME_attak429, tank_frames_attack_chain, tank_run)

tank_frames_death1 = [
	_mf(ai_move, -7, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, -15, tank_thud),
	_mf(ai_move, -5, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
tank_move_death = _mm(tank_h.FRAME_death101, tank_h.FRAME_death132, tank_frames_death1, tank_dead)
