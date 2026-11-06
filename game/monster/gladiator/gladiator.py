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

Gladiator.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_railgun, walkmonster_start)
from game.g_utils import G_FreeEdict, G_ProjectSource
from game.g_weapon import (fire_hit)
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_VOICE, CHAN_WEAPON, MZ2_GLADIATOR_RAILGUN_1
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.gladiator import gladiator_h

"""
#include "../../header/local.h"
#include "gladiator.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_gladiator.h


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

def gladiator_footstep(self): #edict_t *
	global sound_step, sound_step2

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0:

		sound_step = g_main.gi.soundindex("gladiator/step1.wav")
		sound_step2 = g_main.gi.soundindex("gladiator/step2.wav")


	if rand.randk() % 2 == 0:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_die = 0 # static
sound_gun = 0 # static
sound_cleaver_swing = 0 # static
sound_cleaver_hit = 0 # static
sound_cleaver_miss = 0 # static
sound_idle = 0 # static
sound_search = 0 # static
sound_sight = 0 # static


"""
==============================================================================

GLADIATOR

==============================================================================
"""
def gladiator_idle (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def gladiator_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def gladiator_search (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def gladiator_cleaver_swing (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_cleaver_swing, 1, ATTN_NORM, 0)


def gladiator_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gladiator_move_stand


def gladiator_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gladiator_move_walk


def gladiator_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = gladiator_move_stand
	else:
		self.monsterinfo.currentmove = gladiator_move_run


def GaldiatorMelee(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.mins[0], -4)
	if fire_hit(self, aim, (20 + (rand.randk() % 5)), 300):

		g_main.gi.sound(self, CHAN_AUTO, sound_cleaver_hit, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_AUTO, sound_cleaver_miss, 1, ATTN_NORM, 0)


def gladiator_melee (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gladiator_move_attack_melee


def GladiatorGun (self): #edict_t *

	if not self:

		return


	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_GLADIATOR_RAILGUN_1], forward, right, start)

	# calc direction to where we targted
	shared.VectorSubtract (self.pos1, start, dir)
	shared_c.VectorNormalize (dir)

	monster_fire_railgun (self, start, dir, 50, 100, MZ2_GLADIATOR_RAILGUN_1)


def gladiator_attack(self): #edict_t *

	"""
	float range;
	vec3_t v;
	"""
	v = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	# a small safe zone
	# but not for stand-ground ones since players can
	# abuse it by standing still inside this range
	if not (self.monsterinfo.aiflags & AI_STAND_GROUND):

		shared.VectorSubtract(self.s.origin, self.enemy.s.origin, v)
		range_ = shared_c.VectorLength(v)
		if range_ <= (MELEE_DISTANCE + 32):

			return


	# charge up the railgun
	g_main.gi.sound(self, CHAN_WEAPON, sound_gun, 1, ATTN_NORM, 0)
	shared.VectorCopy(self.enemy.s.origin, self.pos1)
	# save for aiming the shot
	self.pos1[2] += self.enemy.viewheight
	self.monsterinfo.currentmove = gladiator_move_attack_gun


def gladiator_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		if (self.velocity[2] > 100) and (self.monsterinfo.currentmove == gladiator_move_pain):

			self.monsterinfo.currentmove = gladiator_move_pain_air


		return


	self.pain_debounce_time = g_main.level.time + 3
	if local.random() < 0.5:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)


	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if self.velocity[2] > 100:

		self.monsterinfo.currentmove = gladiator_move_pain_air

	else:

		self.monsterinfo.currentmove = gladiator_move_pain


def gladiator_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def gladiator_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# check for gib
	if not self:

		return


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
	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	self.monsterinfo.currentmove = gladiator_move_death


"""QUAKED monster_gladiator (1 .5 0) (-32 -32 -24) (32 32 64) Ambush Trigger_Spawn Sight
"""
def SP_monster_gladiator(self): #edict_t *
	global sound_cleaver_hit, sound_cleaver_miss, sound_cleaver_swing, sound_die, sound_gun, sound_idle, sound_pain1, sound_pain2, sound_search, sound_sight, sound_step, sound_step2

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_pain1 = g_main.gi.soundindex("gladiator/pain.wav")
	sound_pain2 = g_main.gi.soundindex("gladiator/gldpain2.wav")
	sound_die = g_main.gi.soundindex("gladiator/glddeth2.wav")
	sound_gun = g_main.gi.soundindex("gladiator/railgun.wav")
	sound_cleaver_swing = g_main.gi.soundindex("gladiator/melee1.wav")
	sound_cleaver_hit = g_main.gi.soundindex("gladiator/melee2.wav")
	sound_cleaver_miss = g_main.gi.soundindex("gladiator/melee3.wav")
	sound_idle = g_main.gi.soundindex("gladiator/gldidle1.wav")
	sound_search = g_main.gi.soundindex("gladiator/gldsrch1.wav")
	sound_sight = g_main.gi.soundindex("gladiator/sight.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/gladiatr/tris.md2")
	shared.VectorSet(self.mins, -32, -32, -24)
	shared.VectorSet(self.maxs, 32, 32, 64)
	self.health = 400
	self.gib_health = -175
	self.mass = 400
	self.pain = gladiator_pain
	self.die = gladiator_die
	self.monsterinfo.stand = gladiator_stand
	self.monsterinfo.walk = gladiator_walk
	self.monsterinfo.run = gladiator_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = gladiator_attack
	self.monsterinfo.melee = gladiator_melee
	self.monsterinfo.sight = gladiator_sight
	self.monsterinfo.idle = gladiator_idle
	self.monsterinfo.search = gladiator_search
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = gladiator_move_stand
	self.monsterinfo.scale = gladiator_h.MODEL_SCALE
	walkmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
gladiator_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
gladiator_move_stand = _mm(gladiator_h.FRAME_stand1, gladiator_h.FRAME_stand7, gladiator_frames_stand, None)

gladiator_frames_walk = [
	_mf(ai_walk, 15, None), _mf(ai_walk, 7, None), _mf(ai_walk, 6, None),
	_mf(ai_walk, 5, None), _mf(ai_walk, 2, gladiator_footstep), _mf(ai_walk, 0, None),
	_mf(ai_walk, 2, None), _mf(ai_walk, 8, None), _mf(ai_walk, 12, None),
	_mf(ai_walk, 8, None), _mf(ai_walk, 5, None), _mf(ai_walk, 5, None),
	_mf(ai_walk, 2, gladiator_footstep), _mf(ai_walk, 2, None), _mf(ai_walk, 1, None),
	_mf(ai_walk, 8, None)]
gladiator_move_walk = _mm(gladiator_h.FRAME_walk1, gladiator_h.FRAME_walk16, gladiator_frames_walk, None)

gladiator_frames_run = [
	_mf(ai_run, 23, None), _mf(ai_run, 14, None), _mf(ai_run, 14, gladiator_footstep),
	_mf(ai_run, 21, None), _mf(ai_run, 12, None), _mf(ai_run, 13, gladiator_footstep)]
gladiator_move_run = _mm(gladiator_h.FRAME_run1, gladiator_h.FRAME_run6, gladiator_frames_run, None)

gladiator_frames_attack_melee = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, gladiator_cleaver_swing),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GaldiatorMelee),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, gladiator_cleaver_swing),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GaldiatorMelee),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
gladiator_move_attack_melee = _mm(gladiator_h.FRAME_melee1, gladiator_h.FRAME_melee17, gladiator_frames_attack_melee, gladiator_run)

gladiator_frames_attack_gun = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GladiatorGun),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
gladiator_move_attack_gun = _mm(gladiator_h.FRAME_attack1, gladiator_h.FRAME_attack9, gladiator_frames_attack_gun, gladiator_run)

gladiator_frames_pain = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
gladiator_move_pain = _mm(gladiator_h.FRAME_pain1, gladiator_h.FRAME_pain6, gladiator_frames_pain, gladiator_run)

gladiator_frames_pain_air = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
gladiator_move_pain_air = _mm(gladiator_h.FRAME_painup1, gladiator_h.FRAME_painup7, gladiator_frames_pain_air, gladiator_run)

gladiator_frames_death = [
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
gladiator_move_death = _mm(gladiator_h.FRAME_death1, gladiator_h.FRAME_death22, gladiator_frames_death, gladiator_dead)
