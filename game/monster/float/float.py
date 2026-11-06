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

Mechanic.

=======================================================================
"""
from __future__ import annotations

from game import g_ai
from common.shared import rand

import numpy as np
from game import g_main
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_combat import (T_Damage)
from game.header.local import AI_STAND_GROUND, DAMAGE_ENERGY, MELEE_DISTANCE, MOD_UNKNOWN, MOVETYPE_STEP, MOVETYPE_TOSS, svc_temp_entity
from game.g_misc import (BecomeExplosion1)
from game.g_monster import (flymonster_start, monster_fire_blaster)
from game.g_utils import G_FreeEdict, G_ProjectSource
from game.g_weapon import (fire_hit)
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_VOICE, CHAN_WEAPON, EF_HYPERBLASTER, MZ2_FLOAT_BLASTER_1, multicast_t, temp_event_t
from common.shared.shared import vec3_origin
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.float import float_h

"""
#include "../../header/local.h"
#include "float.h"
"""

MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_SPLASH = temp_event_t.TE_SPLASH.value

# m_float.h


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

sound_attack2 = 0 # static
sound_attack3 = 0 # static
sound_death1 = 0 # static
sound_idle = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_sight = 0 # static


"""
==============================================================================

floater

==============================================================================
"""
def floater_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def floater_idle (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def floater_fire_blaster (self): #edict_t *

	if not self:

		return


	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	effect;

	if (self.s.frame == float_h.FRAME_attak104) or (self.s.frame == float_h.FRAME_attak107):
		effect = EF_HYPERBLASTER
	else:
		effect = 0
	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_FLOAT_BLASTER_1], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 1, 1000, MZ2_FLOAT_BLASTER_1, effect)


def floater_stand (self): #edict_t *

	if not self:

		return


	if local.random() <= 0.5:
		self.monsterinfo.currentmove = floater_move_stand1
	else:
		self.monsterinfo.currentmove = floater_move_stand2


def floater_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = floater_move_stand1
	else:
		self.monsterinfo.currentmove = floater_move_run


def floater_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = floater_move_walk


def floater_wham(self): #edict_t *

	"""
	static vec3_t aim = {MELEE_DISTANCE, 0, 0};
	"""
	aim = np.array([MELEE_DISTANCE, 0, 0], dtype=np.float32)

	g_main.gi.sound(self, CHAN_WEAPON, sound_attack3, 1, ATTN_NORM, 0)
	fire_hit(self, aim, 5 + rand.randk() % 6, -50)


def floater_zap(self): #edict_t *

	"""
	vec3_t forward, right;
	vec3_t origin;
	vec3_t dir;
	vec3_t offset;
	"""
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	origin = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSubtract(self.enemy.s.origin, self.s.origin, dir)
	shared_c.AngleVectors(self.s.angles, forward, right, None)
	shared.VectorSet(offset, 18.5, -0.9, 10)
	G_ProjectSource(self.s.origin, offset, forward, right, origin)
	g_main.gi.sound(self, CHAN_WEAPON, sound_attack2, 1, ATTN_NORM, 0)
	g_main.gi.WriteByte(svc_temp_entity)
	g_main.gi.WriteByte(TE_SPLASH)
	g_main.gi.WriteByte(32)
	g_main.gi.WritePosition(origin)
	g_main.gi.WriteDir(dir)
	g_main.gi.WriteByte(1)
	# sparks
	g_main.gi.multicast(origin, MULTICAST_PVS)
	if g_ai.ai_range(self, self.enemy) == local.RANGE_MELEE and g_ai.infront(self, self.enemy) and g_ai.visible(self, self.enemy):

		T_Damage(self.enemy, self, self, dir, self.enemy.s.origin, vec3_origin, 5 + rand.randk() % 6, -10, DAMAGE_ENERGY, MOD_UNKNOWN)


def floater_attack (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = floater_move_attack1


def floater_melee (self): #edict_t *

	if not self:

		return


	if local.random() < 0.5:
		self.monsterinfo.currentmove = floater_move_attack3
	else:
		self.monsterinfo.currentmove = floater_move_attack2


def floater_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	"""
	int n;
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


	n = (rand.randk() + 1) % 3
	if n == 0:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = floater_move_pain1

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = floater_move_pain2


def floater_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def floater_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_death1, 1, ATTN_NORM, 0)
	BecomeExplosion1(self)


"""QUAKED monster_floater (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_floater (self): #edict_t *

	global sound_attack2, sound_attack3, sound_death1, sound_idle, sound_pain1, sound_pain2, sound_sight
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_attack2 = g_main.gi.soundindex ("floater/fltatck2.wav")
	sound_attack3 = g_main.gi.soundindex ("floater/fltatck3.wav")
	sound_death1 = g_main.gi.soundindex ("floater/fltdeth1.wav")
	sound_idle = g_main.gi.soundindex ("floater/fltidle1.wav")
	sound_pain1 = g_main.gi.soundindex ("floater/fltpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("floater/fltpain2.wav")
	sound_sight = g_main.gi.soundindex ("floater/fltsght1.wav")

	g_main.gi.soundindex ("floater/fltatck1.wav")

	self.s.sound = g_main.gi.soundindex ("floater/fltsrch1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/float/tris.md2")
	shared.VectorSet (self.mins, -24, -24, -24)
	shared.VectorSet (self.maxs, 24, 24, 32)

	self.health = 200
	self.gib_health = -80
	self.mass = 300

	self.pain = floater_pain
	self.die = floater_die

	self.monsterinfo.stand = floater_stand
	self.monsterinfo.walk = floater_walk
	self.monsterinfo.run = floater_run
	# self->monsterinfo.dodge = floater_dodge;
	self.monsterinfo.attack = floater_attack
	self.monsterinfo.melee = floater_melee
	self.monsterinfo.sight = floater_sight
	self.monsterinfo.idle = floater_idle

	g_main.gi.linkentity (self)

	if local.random() <= 0.5:
		self.monsterinfo.currentmove = floater_move_stand1
	else:
		self.monsterinfo.currentmove = floater_move_stand2

	self.monsterinfo.scale = float_h.MODEL_SCALE

	flymonster_start (self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
floater_frames_stand1 = [
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
floater_move_stand1 = _mm(float_h.FRAME_stand101, float_h.FRAME_stand152, floater_frames_stand1, None)

floater_frames_stand2 = [
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
floater_move_stand2 = _mm(float_h.FRAME_stand201, float_h.FRAME_stand252, floater_frames_stand2, None)

floater_frames_activate = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None)]
floater_move_activate = _mm(float_h.FRAME_actvat01, float_h.FRAME_actvat31, floater_frames_activate, None)

floater_frames_attack1 = [
	_mf(ai_charge, 0, None),	# Blaster attack
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, floater_fire_blaster),	# BOOM (0, -25.8, 32.5)	-- LOOP Starts
	_mf(ai_charge, 0, floater_fire_blaster),
	_mf(ai_charge, 0, floater_fire_blaster),
	_mf(ai_charge, 0, floater_fire_blaster),
	_mf(ai_charge, 0, floater_fire_blaster),
	_mf(ai_charge, 0, floater_fire_blaster),
	_mf(ai_charge, 0, floater_fire_blaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# -- LOOP Ends
]
floater_move_attack1 = _mm(float_h.FRAME_attak101, float_h.FRAME_attak114, floater_frames_attack1, floater_run)

floater_frames_attack2 = [
	_mf(ai_charge, 0, None),	# Claws
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, floater_wham),	# WHAM (0, -45, 29.6)		-- LOOP Starts
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# -- LOOP Ends
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
floater_move_attack2 = _mm(float_h.FRAME_attak201, float_h.FRAME_attak225, floater_frames_attack2, floater_run)

floater_frames_attack3 = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, floater_zap),	# -- LOOP Starts
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# -- LOOP Ends
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
floater_move_attack3 = _mm(float_h.FRAME_attak301, float_h.FRAME_attak334, floater_frames_attack3, floater_run)

floater_frames_death = [
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
floater_move_death = _mm(float_h.FRAME_death01, float_h.FRAME_death13, floater_frames_death, floater_dead)

floater_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
floater_move_pain1 = _mm(float_h.FRAME_pain101, float_h.FRAME_pain107, floater_frames_pain1, floater_run)

floater_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
floater_move_pain2 = _mm(float_h.FRAME_pain201, float_h.FRAME_pain208, floater_frames_pain2, floater_run)

floater_frames_pain3 = [
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
floater_move_pain3 = _mm(float_h.FRAME_pain301, float_h.FRAME_pain312, floater_frames_pain3, floater_run)

floater_frames_walk = [
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
]
floater_move_walk = _mm(float_h.FRAME_stand101, float_h.FRAME_stand152, floater_frames_walk, None)

floater_frames_run = [
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 13, None),
]
floater_move_run = _mm(float_h.FRAME_stand101, float_h.FRAME_stand152, floater_frames_run, None)
