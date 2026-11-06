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

Iron Maiden.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_DUCKED, AI_HOLD_FRAME, AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, RANGE_MELEE, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_rocket, walkmonster_start)
from game.g_utils import G_FreeEdict, G_ProjectSource
from game.g_weapon import (fire_hit)
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_VOICE, CHAN_WEAPON, MZ2_CHICK_ROCKET_1
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.chick import chick_h

"""
#include "../../header/local.h"
#include "chick.h"
"""

DAMAGE_AIM = damage_t.DAMAGE_AIM.value
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_chick.h


sound_step = 0 #static int
sound_step2 = 0 #static int

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

def chick_footstep(self): #edict_t *
	global sound_step, sound_step2

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0:

		sound_step = g_main.gi.soundindex("bitch/step1.wav")
		sound_step2 = g_main.gi.soundindex("bitch/step2.wav")


	if rand.randk() % 2 == 0:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

sound_missile_prelaunch = 0 # static
sound_missile_launch = 0 # static
sound_melee_swing = 0 # static
sound_melee_hit = 0 # static
sound_missile_reload = 0 # static
sound_death1 = 0 # static
sound_death2 = 0 # static
sound_fall_down = 0 # static
sound_idle1 = 0 # static
sound_idle2 = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_pain3 = 0 # static
sound_sight = 0 # static
sound_search = 0 # static


"""
==============================================================================

chick

==============================================================================
"""
def ChickMoan (self): #edict_t *

	if not self:

		return


	if local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_idle1, 1, ATTN_IDLE, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_idle2, 1, ATTN_IDLE, 0)


def chick_fidget (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		return
	if local.random() <= 0.3:
		self.monsterinfo.currentmove = chick_move_fidget


def chick_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = chick_move_stand


def chick_search(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)

def chick_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = chick_move_walk


def chick_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = chick_move_stand
		return

	if self.monsterinfo.currentmove == chick_move_walk or self.monsterinfo.currentmove == chick_move_start_run:
		self.monsterinfo.currentmove = chick_move_run
	else:
		self.monsterinfo.currentmove = chick_move_start_run


def chick_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	"""
	float r;
	"""

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		return


	self.pain_debounce_time = g_main.level.time + 3
	r = local.random()
	if r < 0.33:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)

	elif r < 0.66:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain3, 1, ATTN_NORM, 0)


	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if damage <= 10:

		self.monsterinfo.currentmove = chick_move_pain1

	elif damage <= 25:

		self.monsterinfo.currentmove = chick_move_pain2

	else:

		self.monsterinfo.currentmove = chick_move_pain3


def chick_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, 0)
	shared.VectorSet (self.maxs, 16, 16, 16)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def chick_fall_down(self): #edict_t * (static)

	if not self:

		return


	# CHAN_VOICE so gibbing the body cancels this sound
	g_main.gi.sound(self, CHAN_VOICE, sound_fall_down, 1, ATTN_NORM, 0)

def chick_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	"""
	int n;
	"""

	if not self:

		return


	# check for gib
	if self.health <= self.gib_health:

		g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(2):

			ThrowGib(self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)


		for n in range(4):

			ThrowGib(self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)


		ThrowHead(self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return


	if self.deadflag == DEAD_DEAD:

		return


	# regular death
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	if rand.randk() % 2 == 0:

		self.monsterinfo.currentmove = chick_move_death1
		g_main.gi.sound(self, CHAN_VOICE, sound_death1, 1, ATTN_NORM, 0)

	else:

		self.monsterinfo.currentmove = chick_move_death2
		g_main.gi.sound(self, CHAN_VOICE, sound_death2, 1, ATTN_NORM, 0)


def chick_duck_down (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity (self)


def chick_duck_hold (self): #edict_t *

	if not self:

		return


	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME


def chick_duck_up (self): #edict_t *

	if not self:

		return


	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)


def chick_dodge(self, attacker, eta): #edict_t *, edict_t *, float

	if not self or not attacker:

		return


	if local.random() > 0.25:

		return


	if not self.enemy:

		self.enemy = attacker
		g_ai.FoundTarget(self)


	self.monsterinfo.currentmove = chick_move_duck


def ChickSlash(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.mins[0], 10)
	g_main.gi.sound(self, CHAN_WEAPON, sound_melee_swing, 1, ATTN_NORM, 0)
	fire_hit(self, aim, (10 + (rand.randk() % 6)), 100)


def ChickRocket (self): #edict_t *

	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_CHICK_ROCKET_1], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)

	monster_fire_rocket (self, start, dir, 50, 500, MZ2_CHICK_ROCKET_1)


def Chick_PreAttack1 (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_missile_prelaunch, 1, ATTN_NORM, 0)


def ChickReload (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_missile_reload, 1, ATTN_NORM, 0)


def chick_rerocket(self): #edict_t *

	if not self:

		return


	if self.enemy.health > 0:

		if g_ai.ai_range(self, self.enemy) > RANGE_MELEE:

			if g_ai.visible(self, self.enemy):

				if local.random() <= 0.6:

					self.monsterinfo.currentmove = chick_move_attack1
					return


	self.monsterinfo.currentmove = chick_move_end_attack1


def chick_attack1 (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = chick_move_attack1


def chick_reslash(self): #edict_t *

	if not self:

		return


	if self.enemy.health > 0:

		if g_ai.ai_range(self, self.enemy) == RANGE_MELEE:

			if local.random() <= 0.9:

				self.monsterinfo.currentmove = chick_move_slash
				return

			else:

				self.monsterinfo.currentmove = chick_move_end_slash
				return


	self.monsterinfo.currentmove = chick_move_end_slash


def chick_slash (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = chick_move_slash


def chick_melee (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = chick_move_start_slash


def chick_attack (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = chick_move_start_attack1


def chick_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


"""QUAKED monster_chick (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_chick(self): #edict_t *
	global sound_death1, sound_death2, sound_fall_down, sound_idle1, sound_idle2, sound_melee_hit, sound_melee_swing, sound_missile_launch, sound_missile_prelaunch, sound_missile_reload, sound_pain1, sound_pain2, sound_pain3, sound_search, sound_sight, sound_step, sound_step2

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_missile_prelaunch = g_main.gi.soundindex("chick/chkatck1.wav")
	sound_missile_launch = g_main.gi.soundindex("chick/chkatck2.wav")
	sound_melee_swing = g_main.gi.soundindex("chick/chkatck3.wav")
	sound_melee_hit = g_main.gi.soundindex("chick/chkatck4.wav")
	sound_missile_reload = g_main.gi.soundindex("chick/chkatck5.wav")
	sound_death1 = g_main.gi.soundindex("chick/chkdeth1.wav")
	sound_death2 = g_main.gi.soundindex("chick/chkdeth2.wav")
	sound_fall_down = g_main.gi.soundindex("chick/chkfall1.wav")
	sound_idle1 = g_main.gi.soundindex("chick/chkidle1.wav")
	sound_idle2 = g_main.gi.soundindex("chick/chkidle2.wav")
	sound_pain1 = g_main.gi.soundindex("chick/chkpain1.wav")
	sound_pain2 = g_main.gi.soundindex("chick/chkpain2.wav")
	sound_pain3 = g_main.gi.soundindex("chick/chkpain3.wav")
	sound_sight = g_main.gi.soundindex("chick/chksght1.wav")
	sound_search = g_main.gi.soundindex("chick/chksrch1.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/bitch/tris.md2")
	shared.VectorSet(self.mins, -16, -16, 0)
	shared.VectorSet(self.maxs, 16, 16, 56)
	self.health = 175
	self.gib_health = -70
	self.mass = 200
	self.pain = chick_pain
	self.die = chick_die
	self.monsterinfo.stand = chick_stand
	self.monsterinfo.walk = chick_walk
	self.monsterinfo.run = chick_run
	self.monsterinfo.dodge = chick_dodge
	self.monsterinfo.attack = chick_attack
	self.monsterinfo.melee = chick_melee
	self.monsterinfo.sight = chick_sight
	self.monsterinfo.search = chick_search
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = chick_move_stand
	self.monsterinfo.scale = chick_h.MODEL_SCALE
	walkmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
chick_frames_fidget = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, ChickMoan),
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
chick_move_fidget = _mm(chick_h.FRAME_stand201, chick_h.FRAME_stand230, chick_frames_fidget, chick_stand)

chick_frames_stand = [
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
	_mf(ai_stand, 0, chick_fidget),
]
chick_move_stand = _mm(chick_h.FRAME_stand101, chick_h.FRAME_stand130, chick_frames_stand, None)

chick_frames_start_run = [
	_mf(ai_run, 1, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, -1, None),
	_mf(ai_run, -1, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 1, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 3, None),
]
chick_move_start_run = _mm(chick_h.FRAME_walk01, chick_h.FRAME_walk10, chick_frames_start_run, chick_run)

chick_frames_run = [
	_mf(ai_run, 6, None), _mf(ai_run, 8, chick_footstep), _mf(ai_run, 13, None),
	_mf(ai_run, 5, None), _mf(ai_run, 7, None), _mf(ai_run, 4, None),
	_mf(ai_run, 11, chick_footstep), _mf(ai_run, 5, None), _mf(ai_run, 9, None),
	_mf(ai_run, 7, None)]
chick_move_run = _mm(chick_h.FRAME_walk11, chick_h.FRAME_walk20, chick_frames_run, None)

chick_frames_walk = [
	_mf(ai_walk, 6, None), _mf(ai_walk, 8, chick_footstep), _mf(ai_walk, 13, None),
	_mf(ai_walk, 5, None), _mf(ai_walk, 7, None), _mf(ai_walk, 4, None),
	_mf(ai_walk, 11, chick_footstep), _mf(ai_walk, 5, None), _mf(ai_walk, 9, None),
	_mf(ai_walk, 7, None)]
chick_move_walk = _mm(chick_h.FRAME_walk11, chick_h.FRAME_walk20, chick_frames_walk, None)

chick_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
chick_move_pain1 = _mm(chick_h.FRAME_pain101, chick_h.FRAME_pain105, chick_frames_pain1, chick_run)

chick_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
chick_move_pain2 = _mm(chick_h.FRAME_pain201, chick_h.FRAME_pain205, chick_frames_pain2, chick_run)

chick_frames_pain3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 11, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 4, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, 7, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -8, None),
	_mf(ai_move, 2, None),
]
chick_move_pain3 = _mm(chick_h.FRAME_pain301, chick_h.FRAME_pain321, chick_frames_pain3, chick_run)

chick_frames_death2 = [
	_mf(ai_move, -6, None), _mf(ai_move, 0, None), _mf(ai_move, -1, None),
	_mf(ai_move, -5, chick_footstep), _mf(ai_move, 0, None), _mf(ai_move, -1, None),
	_mf(ai_move, -2, None), _mf(ai_move, 1, None), _mf(ai_move, 10, None),
	_mf(ai_move, 2, None), _mf(ai_move, 3, chick_footstep), _mf(ai_move, 1, None),
	_mf(ai_move, 2, None), _mf(ai_move, 0, None), _mf(ai_move, 3, None),
	_mf(ai_move, 3, None), _mf(ai_move, 1, chick_footstep), _mf(ai_move, -3, None),
	_mf(ai_move, -5, None), _mf(ai_move, 4, None), _mf(ai_move, 15, None),
	_mf(ai_move, 14, chick_fall_down), _mf(ai_move, 1, None)]
chick_move_death2 = _mm(chick_h.FRAME_death201, chick_h.FRAME_death223, chick_frames_death2, chick_dead)

chick_frames_death1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, 4, None),
	_mf(ai_move, 11, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
chick_move_death1 = _mm(chick_h.FRAME_death101, chick_h.FRAME_death112, chick_frames_death1, chick_dead)

chick_frames_duck = [
	_mf(ai_move, 0, chick_duck_down),
	_mf(ai_move, 1, None),
	_mf(ai_move, 4, chick_duck_hold),
	_mf(ai_move, -4, None),
	_mf(ai_move, -5, chick_duck_up),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
]
chick_move_duck = _mm(chick_h.FRAME_duck01, chick_h.FRAME_duck07, chick_frames_duck, chick_run)

chick_frames_start_attack1 = [
	_mf(ai_charge, 0, Chick_PreAttack1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 4, None), _mf(ai_charge, 0, None), _mf(ai_charge, -3, None),
	_mf(ai_charge, 3, None), _mf(ai_charge, 5, None), _mf(ai_charge, 7, chick_footstep),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, chick_attack1)]
chick_move_start_attack1 = _mm(chick_h.FRAME_attak101, chick_h.FRAME_attak113, chick_frames_start_attack1, None)

chick_frames_attack1 = [
	_mf(ai_charge, 19, ChickRocket), _mf(ai_charge, -6, None), _mf(ai_charge, -5, chick_footstep),
	_mf(ai_charge, -2, None), _mf(ai_charge, -7, chick_footstep), _mf(ai_charge, 0, None),
	_mf(ai_charge, 1, None), _mf(ai_charge, 10, ChickReload), _mf(ai_charge, 4, None),
	_mf(ai_charge, 5, chick_footstep), _mf(ai_charge, 6, None), _mf(ai_charge, 6, None),
	_mf(ai_charge, 4, chick_footstep), _mf(ai_charge, 3, chick_rerocket)]
chick_move_attack1 = _mm(chick_h.FRAME_attak114, chick_h.FRAME_attak127, chick_frames_attack1, None)

chick_frames_end_attack1 = [
	_mf(ai_charge, -3, None), _mf(ai_charge, 0, None), _mf(ai_charge, -6, None),
	_mf(ai_charge, -4, None), _mf(ai_charge, -2, chick_footstep)]
chick_move_end_attack1 = _mm(chick_h.FRAME_attak128, chick_h.FRAME_attak132, chick_frames_end_attack1, chick_run)

chick_frames_slash = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 7, ChickSlash),
	_mf(ai_charge, -7, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, -2, chick_reslash),
]
chick_move_slash = _mm(chick_h.FRAME_attak204, chick_h.FRAME_attak212, chick_frames_slash, None)

chick_frames_end_slash = [
	_mf(ai_charge, -6, None), _mf(ai_charge, -1, None), _mf(ai_charge, -6, None),
	_mf(ai_charge, 0, chick_footstep)]
chick_move_end_slash = _mm(chick_h.FRAME_attak213, chick_h.FRAME_attak216, chick_frames_end_slash, chick_run)

chick_frames_start_slash = [
	_mf(ai_charge, 1, None), _mf(ai_charge, 8, None), _mf(ai_charge, 3, chick_footstep)]
chick_move_start_slash = _mm(chick_h.FRAME_attak201, chick_h.FRAME_attak203, chick_frames_start_slash, chick_slash)
