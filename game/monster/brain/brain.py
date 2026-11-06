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

Brain.

=======================================================================
"""
from __future__ import annotations

from game import g_ai
from common.shared import rand

import numpy as np
from game import g_main
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_DUCKED, AI_HOLD_FRAME, AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, POWER_ARMOR_NONE, POWER_ARMOR_SCREEN, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (walkmonster_start)
from game.g_utils import G_FreeEdict
from game.g_weapon import (fire_hit)
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_BODY, CHAN_VOICE, CHAN_WEAPON
from common.header import shared
from game.header import local
from game.monster.brain import brain_h

"""
#include "../../header/local.h"
#include "brain.h"
"""

DAMAGE_AIM = damage_t.DAMAGE_AIM.value
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_brain.h


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

def brain_footstep(self): #edict_t *
	global sound_step, sound_step2

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0:

		sound_step = g_main.gi.soundindex("brain/step1.wav")
		sound_step2 = g_main.gi.soundindex("brain/step2.wav")


	if rand.randk() % 2 == 0:

		g_main.gi.sound(self, CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

sound_chest_open = 0 # static
sound_tentacles_extend = 0 # static
sound_tentacles_retract = 0 # static
sound_death = 0 # static
sound_idle1 = 0 # static
sound_idle2 = 0 # static
sound_idle3 = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_sight = 0 # static
sound_search = 0 # static
sound_melee1 = 0 # static
sound_melee2 = 0 # static
sound_melee3 = 0 # static


"""
==============================================================================

brain

==============================================================================
"""
def brain_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def brain_search (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def brain_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = brain_move_stand


def brain_idle(self): #edict_t *

	"""
	int n;
	"""

	if not self:

		return


	n = rand.randk() & 3
	if n <= 1:

		self.monsterinfo.currentmove = brain_move_idle
		g_main.gi.sound(self, CHAN_AUTO, sound_idle3, 1, ATTN_IDLE, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE,(sound_idle1 if (n == 2) else sound_idle2), 1, ATTN_IDLE, 0)


def brain_walk (self): #edict_t *

	# if (random() <= 0.5)
	if not self:

		return


	self.monsterinfo.currentmove = brain_move_walk1
	# else
	# self->monsterinfo.currentmove = &brain_move_walk2;


def brain_duck_down (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	g_main.gi.linkentity (self)


def brain_duck_hold (self): #edict_t *

	if not self:

		return


	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME


def brain_duck_up (self): #edict_t *

	if not self:

		return


	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)


def brain_dodge(self, attacker, eta): #edict_t *, edict_t *, float

	if not self or not attacker:

		return


	if local.random() > 0.25:

		return


	if not self.enemy:

		self.enemy = attacker
		g_ai.FoundTarget(self)


	self.monsterinfo.pausetime = g_main.level.time + eta + 0.5
	self.monsterinfo.currentmove = brain_move_duck


def brain_swing_right (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_BODY, sound_melee1, 1, ATTN_NORM, 0)


def brain_hit_right(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.maxs[0], 8)
	if fire_hit(self, aim, (15 + (rand.randk() % 5)), 40):

		g_main.gi.sound(self, CHAN_WEAPON, sound_melee3, 1, ATTN_NORM, 0)


def brain_swing_left (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_BODY, sound_melee2, 1, ATTN_NORM, 0)


def brain_hit_left(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.mins[0], 8)
	if fire_hit(self, aim, (15 + (rand.randk() % 5)), 40):

		g_main.gi.sound(self, CHAN_WEAPON, sound_melee3, 1, ATTN_NORM, 0)


def brain_chest_open (self): #edict_t *

	if not self:

		return


	self.spawnflags &= ~65536
	self.monsterinfo.power_armor_type = POWER_ARMOR_NONE
	g_main.gi.sound (self, CHAN_BODY, sound_chest_open, 1, ATTN_NORM, 0)


def brain_tentacle_attack(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, 0, 8)
	if fire_hit(self, aim, (10 + (rand.randk() % 5)), -600) and (g_main.skill.value > local.SKILL_EASY):

		self.spawnflags |= 65536


	g_main.gi.sound(self, CHAN_WEAPON, sound_tentacles_retract, 1, ATTN_NORM, 0)


def brain_chest_closed (self): #edict_t *

	if not self:

		return


	self.monsterinfo.power_armor_type = POWER_ARMOR_SCREEN
	if self.spawnflags & 65536:
		self.spawnflags &= ~65536
		self.monsterinfo.currentmove = brain_move_attack1


def brain_melee (self): #edict_t *

	if not self:

		return


	if local.random() <= 0.5:
		self.monsterinfo.currentmove = brain_move_attack1
	else:
		self.monsterinfo.currentmove = brain_move_attack2


def brain_run (self): #edict_t *

	if not self:

		return


	self.monsterinfo.power_armor_type = POWER_ARMOR_SCREEN
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = brain_move_stand
	else:
		self.monsterinfo.currentmove = brain_move_run


def brain_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

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
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	r = local.random()
	if r < 0.33:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = brain_move_pain1

	elif r < 0.66:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = brain_move_pain2

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = brain_move_pain3


def brain_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def brain_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	if not self:

		return


	self.s.effects = 0
	self.monsterinfo.power_armor_type = POWER_ARMOR_NONE

	# check for gib
	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(0, 2):
			ThrowGib (self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)
		for n in range(0, 4):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	# regular death
	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	if local.random() <= 0.5:
		self.monsterinfo.currentmove = brain_move_death1
	else:
		self.monsterinfo.currentmove = brain_move_death2


"""QUAKED monster_brain (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_brain(self): #edict_t *
	global sound_chest_open, sound_death, sound_idle1, sound_idle2, sound_idle3, sound_melee1, sound_melee2, sound_melee3, sound_pain1, sound_pain2, sound_search, sound_sight, sound_step, sound_step2, sound_tentacles_extend, sound_tentacles_retract

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_chest_open = g_main.gi.soundindex("brain/brnatck1.wav")
	sound_tentacles_extend = g_main.gi.soundindex("brain/brnatck2.wav")
	sound_tentacles_retract = g_main.gi.soundindex("brain/brnatck3.wav")
	sound_death = g_main.gi.soundindex("brain/brndeth1.wav")
	sound_idle1 = g_main.gi.soundindex("brain/brnidle1.wav")
	sound_idle2 = g_main.gi.soundindex("brain/brnidle2.wav")
	sound_idle3 = g_main.gi.soundindex("brain/brnlens1.wav")
	sound_pain1 = g_main.gi.soundindex("brain/brnpain1.wav")
	sound_pain2 = g_main.gi.soundindex("brain/brnpain2.wav")
	sound_sight = g_main.gi.soundindex("brain/brnsght1.wav")
	sound_search = g_main.gi.soundindex("brain/brnsrch1.wav")
	sound_melee1 = g_main.gi.soundindex("brain/melee1.wav")
	sound_melee2 = g_main.gi.soundindex("brain/melee2.wav")
	sound_melee3 = g_main.gi.soundindex("brain/melee3.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/brain/tris.md2")
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 32)
	self.health = 300
	self.gib_health = -150
	self.mass = 400
	self.pain = brain_pain
	self.die = brain_die
	self.monsterinfo.stand = brain_stand
	self.monsterinfo.walk = brain_walk
	self.monsterinfo.run = brain_run
	self.monsterinfo.dodge = brain_dodge
	self.monsterinfo.melee = brain_melee
	self.monsterinfo.sight = brain_sight
	self.monsterinfo.search = brain_search
	self.monsterinfo.idle = brain_idle
	self.monsterinfo.power_armor_type = POWER_ARMOR_SCREEN
	self.monsterinfo.power_armor_power = 100
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = brain_move_stand
	self.monsterinfo.scale = brain_h.MODEL_SCALE
	walkmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
brain_frames_stand = [
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
brain_move_stand = _mm(brain_h.FRAME_stand01, brain_h.FRAME_stand30, brain_frames_stand, None)

brain_frames_idle = [
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
brain_move_idle = _mm(brain_h.FRAME_stand31, brain_h.FRAME_stand60, brain_frames_idle, brain_stand)

brain_frames_walk1 = [
	_mf(ai_walk, 7, None), _mf(ai_walk, 2, None), _mf(ai_walk, 3, None),
	_mf(ai_walk, 3, brain_footstep), _mf(ai_walk, 1, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 9, None), _mf(ai_walk, -4, None),
	_mf(ai_walk, -1, brain_footstep), _mf(ai_walk, 2, None)]
brain_move_walk1 = _mm(brain_h.FRAME_walk101, brain_h.FRAME_walk111, brain_frames_walk1, None)

brain_frames_defense = [
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
brain_move_defense = _mm(brain_h.FRAME_defens01, brain_h.FRAME_defens08, brain_frames_defense, None)

brain_frames_pain3 = [
	_mf(ai_move, -2, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -4, None),
]
brain_move_pain3 = _mm(brain_h.FRAME_pain301, brain_h.FRAME_pain306, brain_frames_pain3, brain_run)

brain_frames_pain2 = [
	_mf(ai_move, -2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, -2, None),
]
brain_move_pain2 = _mm(brain_h.FRAME_pain201, brain_h.FRAME_pain208, brain_frames_pain2, brain_run)

brain_frames_pain1 = [
	_mf(ai_move, -6, None), _mf(ai_move, -2, None), _mf(ai_move, -6, brain_footstep),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 2, None), _mf(ai_move, 0, None),
	_mf(ai_move, 2, None), _mf(ai_move, 1, None), _mf(ai_move, 7, None),
	_mf(ai_move, 0, None), _mf(ai_move, 3, brain_footstep), _mf(ai_move, -1, None)]
brain_move_pain1 = _mm(brain_h.FRAME_pain101, brain_h.FRAME_pain121, brain_frames_pain1, brain_run)

brain_frames_duck = [
	_mf(ai_move, 0, None), _mf(ai_move, -2, brain_duck_down), _mf(ai_move, 17, brain_duck_hold),
	_mf(ai_move, -3, brain_footstep), _mf(ai_move, -1, brain_duck_up), _mf(ai_move, -5, None),
	_mf(ai_move, -6, None), _mf(ai_move, -6, brain_footstep)]
brain_move_duck = _mm(brain_h.FRAME_duck01, brain_h.FRAME_duck08, brain_frames_duck, brain_run)

brain_frames_death2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 9, None),
	_mf(ai_move, 0, None),
]
brain_move_death2 = _mm(brain_h.FRAME_death201, brain_h.FRAME_death205, brain_frames_death2, brain_dead)

brain_frames_death1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 9, None),
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
brain_move_death1 = _mm(brain_h.FRAME_death101, brain_h.FRAME_death118, brain_frames_death1, brain_dead)

brain_frames_attack1 = [
	_mf(ai_charge, 8, None), _mf(ai_charge, 3, None), _mf(ai_charge, 5, None),
	_mf(ai_charge, 0, brain_footstep), _mf(ai_charge, -3, brain_swing_right), _mf(ai_charge, 0, None),
	_mf(ai_charge, -5, None), _mf(ai_charge, -7, brain_hit_right), _mf(ai_charge, 0, None),
	_mf(ai_charge, 6, brain_swing_left), _mf(ai_charge, 1, None), _mf(ai_charge, 2, brain_hit_left),
	_mf(ai_charge, -3, None), _mf(ai_charge, 6, None), _mf(ai_charge, -1, None),
	_mf(ai_charge, -3, None), _mf(ai_charge, 2, None), _mf(ai_charge, -11, brain_footstep)]
brain_move_attack1 = _mm(brain_h.FRAME_attak101, brain_h.FRAME_attak118, brain_frames_attack1, brain_run)

brain_frames_attack2 = [
	_mf(ai_charge, 5, None),
	_mf(ai_charge, -4, None),
	_mf(ai_charge, -4, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 0, brain_chest_open),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 13, brain_tentacle_attack),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -9, brain_chest_closed),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, -6, None),
]
brain_move_attack2 = _mm(brain_h.FRAME_attak201, brain_h.FRAME_attak217, brain_frames_attack2, brain_run)

brain_frames_run = [
	_mf(ai_run, 9, None), _mf(ai_run, 2, None), _mf(ai_run, 3, None),
	_mf(ai_run, 3, brain_footstep), _mf(ai_run, 1, None), _mf(ai_run, 0, None),
	_mf(ai_run, 0, None), _mf(ai_run, 10, None), _mf(ai_run, -4, None),
	_mf(ai_run, -1, brain_footstep), _mf(ai_run, 2, None)]
brain_move_run = _mm(brain_h.FRAME_walk101, brain_h.FRAME_walk111, brain_frames_run, None)
