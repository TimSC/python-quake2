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

Supertank aka "Boss1".

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_STAND_GROUND, DEAD_DEAD, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, GIB_METALLIC, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t, svc_temp_entity
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_bullet, monster_fire_rocket, walkmonster_start)
from game.g_utils import G_FreeEdict, G_ProjectSource
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_NORM, CHAN_VOICE, MZ2_SUPERTANK_MACHINEGUN_1, MZ2_SUPERTANK_ROCKET_1, MZ2_SUPERTANK_ROCKET_2, MZ2_SUPERTANK_ROCKET_3, multicast_t, temp_event_t
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.supertank import supertank_h

"""
#include "../../header/local.h"
#include "supertank.h"
"""

DAMAGE_NO = damage_t.DAMAGE_NO.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_EXPLOSION1 = temp_event_t.TE_EXPLOSION1.value

# m_supertank.h


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

sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_pain3 = 0 # static
sound_death = 0 # static
sound_search1 = 0 # static
sound_search2 = 0 # static
tread_sound = 0 # static


"""
==============================================================================

SUPERTANK

==============================================================================
"""
def TreadSound (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, tread_sound, 1, ATTN_NORM, 0)


def supertank_search (self): #edict_t *

	if not self:

		return


	if local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_search1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_search2, 1, ATTN_NORM, 0)


def supertank_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = supertank_move_stand


def supertank_forward (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = supertank_move_forward


def supertank_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = supertank_move_forward


def supertank_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = supertank_move_stand
	else:
		self.monsterinfo.currentmove = supertank_move_run


def supertank_reattack1 (self): #edict_t *

	if not self:

		return


	if g_ai.visible(self, self.enemy):
		if local.random() < 0.9:
			self.monsterinfo.currentmove = supertank_move_attack1
		else:
			self.monsterinfo.currentmove = supertank_move_end_attack1
	else:
		self.monsterinfo.currentmove = supertank_move_end_attack1


def supertank_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		return


	# Lessen the chance of him going into his pain frames
	if damage <= 25:

		if local.random() < 0.2:

			return


	# Don't go into pain if he's firing his rockets
	if g_main.skill.value >= local.SKILL_HARD:

		if (self.s.frame >= supertank_h.FRAME_attak2_1) and (self.s.frame <= supertank_h.FRAME_attak2_14):

			return


	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if damage <= 10:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = supertank_move_pain1

	elif damage <= 25:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain3, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = supertank_move_pain2

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = supertank_move_pain3


def supertankRocket (self): #edict_t *

	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	if self.s.frame == supertank_h.FRAME_attak2_8:
		flash_number = MZ2_SUPERTANK_ROCKET_1
	elif self.s.frame == supertank_h.FRAME_attak2_11:
		flash_number = MZ2_SUPERTANK_ROCKET_2
	else:
		# (self->s.frame == FRAME_attak2_14)
		flash_number = MZ2_SUPERTANK_ROCKET_3

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)

	monster_fire_rocket (self, start, dir, 50, 500, flash_number)


def supertankMachineGun (self): #edict_t *

	if not self:

		return


	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	flash_number = MZ2_SUPERTANK_MACHINEGUN_1 + (self.s.frame - supertank_h.FRAME_attak1_1)

	# FIXME!!!
	dir[0] = 0
	dir[1] = self.s.angles[1]
	dir[2] = 0

	shared_c.AngleVectors (dir, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	if self.enemy:
		shared.VectorCopy (self.enemy.s.origin, vec)
		shared_c.VectorMA (vec, 0, self.enemy.velocity, vec)
		vec[2] += self.enemy.viewheight
		shared.VectorSubtract (vec, start, forward)
		shared_c.VectorNormalize (forward)

	monster_fire_bullet (self, start, forward, 6, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)


def supertank_attack (self): #edict_t *

	if not self:

		return


	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#float	range;
	# float	r;

	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range = shared_c.VectorLength (vec)

	# r = random();

	# Attack 1 == Chaingun
	# Attack 2 == Rocket Launcher

	if range <= 160:
		self.monsterinfo.currentmove = supertank_move_attack1
	else:
		# fire rockets more often at distance
		if local.random() < 0.3:
			self.monsterinfo.currentmove = supertank_move_attack1
		else:
			self.monsterinfo.currentmove = supertank_move_attack2


def supertank_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -60, -60, 0)
	shared.VectorSet (self.maxs, 60, 60, 72)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def BossExplode(self): #edict_t *

	"""
	vec3_t org;
	int n;
	"""
	org = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	self.think = BossExplode
	shared.VectorCopy(self.s.origin, org)
	org[2] += 24 + (rand.randk() & 15)
	_switch = self.count
	self.count += 1
	if _switch == 0:

		org[0] -= 24
		org[1] -= 24

	elif _switch == 1:

		org[0] += 24
		org[1] += 24

	elif _switch == 2:

		org[0] += 24
		org[1] -= 24

	elif _switch == 3:

		org[0] -= 24
		org[1] += 24

	elif _switch == 4:

		org[0] -= 48
		org[1] -= 48

	elif _switch == 5:

		org[0] += 48
		org[1] += 48

	elif _switch == 6:

		org[0] -= 48
		org[1] += 48

	elif _switch == 7:

		org[0] += 48
		org[1] -= 48

	elif _switch == 8:

		self.s.sound = 0
		for n in range(4):

			ThrowGib(self, "models/objects/gibs/sm_meat/tris.md2", 500, GIB_ORGANIC)


		for n in range(8):

			ThrowGib(self, "models/objects/gibs/sm_metal/tris.md2", 500, GIB_METALLIC)


		ThrowGib(self, "models/objects/gibs/chest/tris.md2", 500, GIB_ORGANIC)
		ThrowHead(self, "models/objects/gibs/gear/tris.md2", 500, GIB_METALLIC)
		self.deadflag = DEAD_DEAD
		return


	g_main.gi.WriteByte(svc_temp_entity)
	g_main.gi.WriteByte(TE_EXPLOSION1)
	g_main.gi.WritePosition(org)
	g_main.gi.multicast(self.s.origin, MULTICAST_PVS)
	self.nextthink = g_main.level.time + 0.1


def supertank_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_NO
	self.count = 0
	self.monsterinfo.currentmove = supertank_move_death


"""QUAKED monster_supertank (1 .5 0) (-64 -64 0) (64 64 72) Ambush Trigger_Spawn Sight
"""
def SP_monster_supertank (self): #edict_t *

	global sound_pain1, sound_pain2, sound_pain3, sound_death, sound_search1, sound_search2, tread_sound
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("bosstank/btkpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("bosstank/btkpain2.wav")
	sound_pain3 = g_main.gi.soundindex ("bosstank/btkpain3.wav")
	sound_death = g_main.gi.soundindex ("bosstank/btkdeth1.wav")
	sound_search1 = g_main.gi.soundindex ("bosstank/btkunqv1.wav")
	sound_search2 = g_main.gi.soundindex ("bosstank/btkunqv2.wav")

	# self->s.sound = gi.soundindex ("bosstank/btkengn1.wav");
	tread_sound = g_main.gi.soundindex ("bosstank/btkengn1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/boss1/tris.md2")
	shared.VectorSet (self.mins, -64, -64, 0)
	shared.VectorSet (self.maxs, 64, 64, 112)

	self.health = 1500
	self.gib_health = -500
	self.mass = 800

	self.pain = supertank_pain
	self.die = supertank_die
	self.monsterinfo.stand = supertank_stand
	self.monsterinfo.walk = supertank_walk
	self.monsterinfo.run = supertank_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = supertank_attack
	self.monsterinfo.search = supertank_search
	self.monsterinfo.melee = None
	self.monsterinfo.sight = None

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = supertank_move_stand
	self.monsterinfo.scale = supertank_h.MODEL_SCALE

	walkmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
supertank_frames_stand = [
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
supertank_move_stand = _mm(supertank_h.FRAME_stand_1, supertank_h.FRAME_stand_60, supertank_frames_stand, None)

supertank_frames_run = [
	_mf(ai_run, 12, TreadSound),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
]
supertank_move_run = _mm(supertank_h.FRAME_forwrd_1, supertank_h.FRAME_forwrd_18, supertank_frames_run, None)

supertank_frames_forward = [
	_mf(ai_walk, 4, TreadSound),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None),
]
supertank_move_forward = _mm(supertank_h.FRAME_forwrd_1, supertank_h.FRAME_forwrd_18, supertank_frames_forward, None)

supertank_frames_turn_right = [
	_mf(ai_move, 0, TreadSound),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_turn_right = _mm(supertank_h.FRAME_right_1, supertank_h.FRAME_right_18, supertank_frames_turn_right, supertank_run)

supertank_frames_turn_left = [
	_mf(ai_move, 0, TreadSound),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_turn_left = _mm(supertank_h.FRAME_left_1, supertank_h.FRAME_left_18, supertank_frames_turn_left, supertank_run)

supertank_frames_pain3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_pain3 = _mm(supertank_h.FRAME_pain3_9, supertank_h.FRAME_pain3_12, supertank_frames_pain3, supertank_run)

supertank_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_pain2 = _mm(supertank_h.FRAME_pain2_5, supertank_h.FRAME_pain2_8, supertank_frames_pain2, supertank_run)

supertank_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_pain1 = _mm(supertank_h.FRAME_pain1_1, supertank_h.FRAME_pain1_4, supertank_frames_pain1, supertank_run)

supertank_frames_death1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, BossExplode),
]
supertank_move_death = _mm(supertank_h.FRAME_death_1, supertank_h.FRAME_death_24, supertank_frames_death1, supertank_dead)

supertank_frames_backward = [
	_mf(ai_walk, 0, TreadSound),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
]
supertank_move_backward = _mm(supertank_h.FRAME_backwd_1, supertank_h.FRAME_backwd_18, supertank_frames_backward, None)

supertank_frames_attack4 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_attack4 = _mm(supertank_h.FRAME_attak4_1, supertank_h.FRAME_attak4_6, supertank_frames_attack4, supertank_run)

supertank_frames_attack3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_attack3 = _mm(supertank_h.FRAME_attak3_1, supertank_h.FRAME_attak3_27, supertank_frames_attack3, supertank_run)

supertank_frames_attack2 = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, supertankRocket),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, supertankRocket),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, supertankRocket),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_attack2 = _mm(supertank_h.FRAME_attak2_1, supertank_h.FRAME_attak2_27, supertank_frames_attack2, supertank_run)

supertank_frames_attack1 = [
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
]
supertank_move_attack1 = _mm(supertank_h.FRAME_attak1_1, supertank_h.FRAME_attak1_6, supertank_frames_attack1, supertank_reattack1)

supertank_frames_end_attack1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_end_attack1 = _mm(supertank_h.FRAME_attak1_7, supertank_h.FRAME_attak1_20, supertank_frames_end_attack1, supertank_run)
