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

Baracuda Shark.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (swimmonster_start)
from game.g_utils import G_FreeEdict
from game.g_weapon import (fire_hit)
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_NORM, CHAN_VOICE, CHAN_WEAPON
from common.header import shared
from game.header import local
from game.monster.flipper import flipper_h

"""
#include "../../header/local.h"
#include "flipper.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_flipper.h


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

def flipper_idle(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_idle, 1, shared.ATTN_IDLE, 0)

sound_chomp = 0 # static
sound_attack = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_death = 0 # static
sound_idle = 0 # static
sound_search = 0 # static
sound_sight = 0 # static


"""
==============================================================================

FLIPPER

==============================================================================
"""
def flipper_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flipper_move_stand


def flipper_run_loop (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flipper_move_run_loop


def flipper_run (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flipper_move_run_start


def flipper_search(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)

def flipper_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flipper_move_walk


def flipper_start_run (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flipper_move_start_run


def flipper_bite (self): #edict_t *

	if not self:

		return


	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	shared.VectorSet (aim, MELEE_DISTANCE, 0, 0)
	fire_hit (self, aim, 5, 0)


def flipper_preattack (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_chomp, 1, ATTN_NORM, 0)


def flipper_melee (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flipper_move_attack


def flipper_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

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


	n = (rand.randk() + 1) % 2
	if n == 0:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flipper_move_pain1

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flipper_move_pain2


def flipper_dead(self): #edict_t *

	"""
	vec3_t p;
	trace_t tr;
	"""
	p = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	# original dead bbox was wrong - and make sure the bbox adjustment stays in solidity
	p[0] = self.s.origin[0]
	p[1] = self.s.origin[1]
	p[2] = self.s.origin[2] - 8
	tr = g_main.gi.trace(self.s.origin, self.mins, self.maxs, p, self, self.clipmask)
	self.mins[2] = tr.endpos[2] - self.s.origin[2]
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity(self)


def flipper_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def flipper_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

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
	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.monsterinfo.currentmove = flipper_move_death


"""QUAKED monster_flipper (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_flipper(self): #edict_t *
	global sound_attack, sound_chomp, sound_death, sound_idle, sound_pain1, sound_pain2, sound_search, sound_sight

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	sound_pain1 = g_main.gi.soundindex("flipper/flppain1.wav")
	sound_pain2 = g_main.gi.soundindex("flipper/flppain2.wav")
	sound_death = g_main.gi.soundindex("flipper/flpdeth1.wav")
	sound_chomp = g_main.gi.soundindex("flipper/flpatck1.wav")
	sound_attack = g_main.gi.soundindex("flipper/flpatck2.wav")
	sound_idle = g_main.gi.soundindex("flipper/flpidle1.wav")
	sound_search = g_main.gi.soundindex("flipper/flpsrch1.wav")
	sound_sight = g_main.gi.soundindex("flipper/flpsght1.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/flipper/tris.md2")
	shared.VectorSet(self.mins, -16, -16, 0)
	shared.VectorSet(self.maxs, 16, 16, 32)
	self.health = 50
	self.gib_health = -30
	self.mass = 100
	self.pain = flipper_pain
	self.die = flipper_die
	self.monsterinfo.stand = flipper_stand
	self.monsterinfo.walk = flipper_walk
	self.monsterinfo.run = flipper_start_run
	self.monsterinfo.melee = flipper_melee
	self.monsterinfo.sight = flipper_sight
	self.monsterinfo.idle = flipper_idle
	self.monsterinfo.search = flipper_search
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = flipper_move_stand
	self.monsterinfo.scale = flipper_h.MODEL_SCALE
	swimmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
flipper_frames_stand = [
	_mf(ai_stand, 0, None),
]
flipper_move_stand = _mm(flipper_h.FRAME_flphor01, flipper_h.FRAME_flphor01, flipper_frames_stand, None)

FLIPPER_RUN_SPEED = 24

flipper_frames_run = [
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None), _mf(ai_run, FLIPPER_RUN_SPEED, None)]
flipper_move_run_loop = _mm(flipper_h.FRAME_flpver06, flipper_h.FRAME_flpver29, flipper_frames_run, None)

flipper_frames_run_start = [
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
]
flipper_move_run_start = _mm(flipper_h.FRAME_flpver01, flipper_h.FRAME_flpver06, flipper_frames_run_start, flipper_run_loop)

flipper_frames_walk = [
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
flipper_move_walk = _mm(flipper_h.FRAME_flphor01, flipper_h.FRAME_flphor24, flipper_frames_walk, None)

flipper_frames_start_run = [
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, flipper_run),
]
flipper_move_start_run = _mm(flipper_h.FRAME_flphor01, flipper_h.FRAME_flphor05, flipper_frames_start_run, None)

flipper_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flipper_move_pain2 = _mm(flipper_h.FRAME_flppn101, flipper_h.FRAME_flppn105, flipper_frames_pain2, flipper_run)

flipper_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flipper_move_pain1 = _mm(flipper_h.FRAME_flppn201, flipper_h.FRAME_flppn205, flipper_frames_pain1, flipper_run)

flipper_frames_attack = [
	_mf(ai_charge, 0, flipper_preattack),
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
	_mf(ai_charge, 0, flipper_bite),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, flipper_bite),
	_mf(ai_charge, 0, None),
]
flipper_move_attack = _mm(flipper_h.FRAME_flpbit01, flipper_h.FRAME_flpbit20, flipper_frames_attack, flipper_run)

flipper_frames_death = [
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
flipper_move_death = _mm(flipper_h.FRAME_flpdth01, flipper_h.FRAME_flpdth56, flipper_frames_death, flipper_dead)
