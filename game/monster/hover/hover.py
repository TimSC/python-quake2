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

Icarus.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_STAND_GROUND, DEAD_DEAD, FRAMETIME, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t
from game.g_misc import (BecomeExplosion1, ThrowGib, ThrowHead)
from game.g_monster import (flymonster_start, monster_fire_blaster)
from game.g_utils import G_FreeEdict, G_ProjectSource
from game.header.game import SOLID_BBOX
from common.header.shared import ATTN_NORM, CHAN_VOICE, EF_HYPERBLASTER, MZ2_HOVER_BLASTER_1
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.hover import hover_h

"""
#include "../../header/local.h"
#include "hover.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_hover.h


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
sound_death1 = 0 # static
sound_death2 = 0 # static
sound_sight = 0 # static
sound_search1 = 0 # static
sound_search2 = 0 # static


"""
==============================================================================

hover

==============================================================================
"""
def hover_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def hover_search (self): #edict_t *

	if local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_search1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_search2, 1, ATTN_NORM, 0)


def hover_reattack (self): #edict_t *

	if not self:

		return


	if self.enemy.health > 0:
		if g_ai.visible (self, self.enemy):
			if local.random() <= 0.6:
				self.monsterinfo.currentmove = hover_move_attack1
				return
	self.monsterinfo.currentmove = hover_move_end_attack


def hover_fire_blaster (self): #edict_t *

	if not self:

		return


	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	effect;

	if self.s.frame == hover_h.FRAME_attak104:
		effect = EF_HYPERBLASTER
	else:
		effect = 0

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_HOVER_BLASTER_1], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 1, 1000, MZ2_HOVER_BLASTER_1, effect)


def hover_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = hover_move_stand


def hover_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = hover_move_stand
	else:
		self.monsterinfo.currentmove = hover_move_run


def hover_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = hover_move_walk


def hover_start_attack (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = hover_move_start_attack


def hover_attack (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = hover_move_attack1


def hover_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

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


	if damage <= 25:

		if local.random() < 0.5:

			g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
			self.monsterinfo.currentmove = hover_move_pain3

		else:

			g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
			self.monsterinfo.currentmove = hover_move_pain2


	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = hover_move_pain1


def hover_deadthink (self): #edict_t *

	if not self:

		return


	if not self.groundentity and g_main.level.time < self.timestamp:
		self.nextthink = g_main.level.time + FRAMETIME
		return
	BecomeExplosion1(self)


def hover_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.think = hover_deadthink
	self.nextthink = g_main.level.time + FRAMETIME
	self.timestamp = g_main.level.time + 15
	g_main.gi.linkentity (self)


def hover_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# check for gib
	if not self:

		return


	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(0, 2):
			ThrowGib (self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)
		for n in range(0, 2):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	# regular death
	if local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_death1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_death2, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.monsterinfo.currentmove = hover_move_death1


"""QUAKED monster_hover (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_hover (self): #edict_t *

	global sound_pain1, sound_pain2, sound_death1, sound_death2, sound_sight, sound_search1, sound_search2
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("hover/hovpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("hover/hovpain2.wav")
	sound_death1 = g_main.gi.soundindex ("hover/hovdeth1.wav")
	sound_death2 = g_main.gi.soundindex ("hover/hovdeth2.wav")
	sound_sight = g_main.gi.soundindex ("hover/hovsght1.wav")
	sound_search1 = g_main.gi.soundindex ("hover/hovsrch1.wav")
	sound_search2 = g_main.gi.soundindex ("hover/hovsrch2.wav")

	g_main.gi.soundindex ("hover/hovatck1.wav")

	self.s.sound = g_main.gi.soundindex ("hover/hovidle1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/hover/tris.md2")
	shared.VectorSet (self.mins, -24, -24, -24)
	shared.VectorSet (self.maxs, 24, 24, 32)

	self.health = 240
	self.gib_health = -100
	self.mass = 150

	self.pain = hover_pain
	self.die = hover_die

	self.monsterinfo.stand = hover_stand
	self.monsterinfo.walk = hover_walk
	self.monsterinfo.run = hover_run
	# self->monsterinfo.dodge = hover_dodge;
	self.monsterinfo.attack = hover_start_attack
	self.monsterinfo.sight = hover_sight
	self.monsterinfo.search = hover_search

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = hover_move_stand
	self.monsterinfo.scale = hover_h.MODEL_SCALE

	flymonster_start (self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
hover_frames_stand = [
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
hover_move_stand = _mm(hover_h.FRAME_stand01, hover_h.FRAME_stand30, hover_frames_stand, None)

hover_frames_stop1 = [
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
hover_move_stop1 = _mm(hover_h.FRAME_stop101, hover_h.FRAME_stop109, hover_frames_stop1, None)

hover_frames_stop2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
hover_move_stop2 = _mm(hover_h.FRAME_stop201, hover_h.FRAME_stop208, hover_frames_stop2, None)

hover_frames_takeoff = [
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -9, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
]
hover_move_takeoff = _mm(hover_h.FRAME_takeof01, hover_h.FRAME_takeof30, hover_frames_takeoff, None)

hover_frames_pain3 = [
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
hover_move_pain3 = _mm(hover_h.FRAME_pain301, hover_h.FRAME_pain309, hover_frames_pain3, hover_run)

hover_frames_pain2 = [
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
hover_move_pain2 = _mm(hover_h.FRAME_pain201, hover_h.FRAME_pain212, hover_frames_pain2, hover_run)

hover_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, -8, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 7, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 4, None),
]
hover_move_pain1 = _mm(hover_h.FRAME_pain101, hover_h.FRAME_pain128, hover_frames_pain1, hover_run)

hover_frames_land = [
	_mf(ai_move, 0, None),
]
hover_move_land = _mm(hover_h.FRAME_land01, hover_h.FRAME_land01, hover_frames_land, None)

hover_frames_forward = [
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
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
hover_move_forward = _mm(hover_h.FRAME_forwrd01, hover_h.FRAME_forwrd35, hover_frames_forward, None)

hover_frames_walk = [
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
	_mf(ai_walk, 4, None),
]
hover_move_walk = _mm(hover_h.FRAME_forwrd01, hover_h.FRAME_forwrd35, hover_frames_walk, None)

hover_frames_run = [
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 10, None),
]
hover_move_run = _mm(hover_h.FRAME_forwrd01, hover_h.FRAME_forwrd35, hover_frames_run, None)

hover_frames_death1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -10, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, 4, None),
	_mf(ai_move, 7, None),
]
hover_move_death1 = _mm(hover_h.FRAME_death101, hover_h.FRAME_death111, hover_frames_death1, hover_dead)

hover_frames_backward = [
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
hover_move_backward = _mm(hover_h.FRAME_backwd01, hover_h.FRAME_backwd24, hover_frames_backward, None)

hover_frames_start_attack = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
]
hover_move_start_attack = _mm(hover_h.FRAME_attak101, hover_h.FRAME_attak103, hover_frames_start_attack, hover_attack)

hover_frames_attack1 = [
	_mf(ai_charge, -10, hover_fire_blaster),
	_mf(ai_charge, -10, hover_fire_blaster),
	_mf(ai_charge, 0, hover_reattack),
]
hover_move_attack1 = _mm(hover_h.FRAME_attak104, hover_h.FRAME_attak106, hover_frames_attack1, None)

hover_frames_end_attack = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
]
hover_move_end_attack = _mm(hover_h.FRAME_attak107, hover_h.FRAME_attak108, hover_frames_end_attack, hover_run)
