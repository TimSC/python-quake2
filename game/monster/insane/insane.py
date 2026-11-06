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

The insane earth soldiers.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.header.local import AI_GOOD_GUY, AI_STAND_GROUND, DEAD_DEAD, FL_FLY, FL_NO_KNOCKBACK, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (flymonster_start, walkmonster_start)
from game.g_utils import G_FreeEdict
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, CHAN_VOICE
from common.header import shared
from game.header import local
from game.monster.insane import insane_h

"""
#include "../../header/local.h"
#include "insane.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_insane.h


sound_step = 0 #static int
sound_step2 = 0 #static int
sound_step3 = 0 #static int
sound_step4 = 0 #static int

SPAWNFLAG_CRUSIFIED = 8

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

def insane_footstep(self): #edict_t *
	global sound_step, sound_step2, sound_step3, sound_step4

	"""
	int i;
	"""

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0 or sound_step3 == 0 or sound_step4 == 0:

		sound_step = g_main.gi.soundindex("player/step1.wav")
		sound_step2 = g_main.gi.soundindex("player/step2.wav")
		sound_step3 = g_main.gi.soundindex("player/step3.wav")
		sound_step4 = g_main.gi.soundindex("player/step4.wav")


	i = rand.randk() % 4
	if i == 0:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step, 0.7, shared.ATTN_NORM, 0)

	elif i == 1:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step2, 0.7, shared.ATTN_NORM, 0)

	elif i == 2:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step3, 0.7, shared.ATTN_NORM, 0)

	elif i == 3:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step4, 0.7, shared.ATTN_NORM, 0)

sound_fist = 0 # static
sound_shake = 0 # static
sound_moan = 0 # static
sound_scream = [0] * 8 # static int [8]


"""
==============================================================================

insane

==============================================================================
"""
def insane_fist (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_fist, 1, ATTN_IDLE, 0)


def insane_shake (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_shake, 1, ATTN_IDLE, 0)


def insane_moan(self): #edict_t *

	if not self:

		return


	# suppress screaming so pain sound can play
	if self.fly_sound_debounce_time > g_main.level.time:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_moan, 1, ATTN_IDLE, 0)


def insane_scream(self): #edict_t *

	if not self:

		return


	# suppress screaming so pain sound can play
	if self.fly_sound_debounce_time > g_main.level.time:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_scream[rand.randk() % 8], 1, ATTN_IDLE, 0)


def insane_cross (self): #edict_t *

	if not self:

		return


	if local.random() < 0.8:
		self.monsterinfo.currentmove = insane_move_cross
	else:
		self.monsterinfo.currentmove = insane_move_struggle_cross


def insane_walk (self): #edict_t *

	if not self:

		return


	if self.spawnflags & 16:
		# Hold Ground?
		if self.s.frame == insane_h.FRAME_cr_pain10:
			self.monsterinfo.currentmove = insane_move_down
			return
	if self.spawnflags & 4:
		self.monsterinfo.currentmove = insane_move_crawl
	elif local.random() <= 0.5:
		self.monsterinfo.currentmove = insane_move_walk_normal
	else:
		self.monsterinfo.currentmove = insane_move_walk_insane


def insane_run(self): #edict_t *

	if not self:

		return


	if self.spawnflags & 16:

		if self.s.frame == insane_h.FRAME_cr_pain10:

			self.monsterinfo.currentmove = insane_move_down
			return


	if self.spawnflags & 4:

		self.monsterinfo.currentmove = insane_move_runcrawl

	elif rand.frandk() <= 0.5:

		# Else, mix it up
		self.monsterinfo.currentmove = insane_move_run_normal

	else:

		self.monsterinfo.currentmove = insane_move_run_insane


def insane_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	"""
	int l, r;
	"""

	if not self:

		return


	if g_main.level.time < self.pain_debounce_time:

		return


	self.pain_debounce_time = g_main.level.time + 3
	r = 1 + (rand.randk() & 1)
	if self.health < 25:

		l = 25

	elif self.health < 50:

		l = 50

	elif self.health < 75:

		l = 75

	else:

		l = 100


	g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex(("player/male/pain%i_%i.wav" % (l, r,))), 1, ATTN_IDLE, 0)
	# suppress screaming and moaning for 1 second so pain sound plays
	self.fly_sound_debounce_time = g_main.level.time + 1
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	# Don't go into pain frames if crucified.
	if self.spawnflags & SPAWNFLAG_CRUSIFIED:

		self.monsterinfo.currentmove = insane_move_struggle_cross
		return


	if ((self.s.frame >= insane_h.FRAME_crawl1) and (self.s.frame <= insane_h.FRAME_crawl9)) or ((self.s.frame >= insane_h.FRAME_stand99) and (self.s.frame <= insane_h.FRAME_stand160)):

		self.monsterinfo.currentmove = insane_move_crawl_pain

	else:

		self.monsterinfo.currentmove = insane_move_stand_pain


def insane_onground (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = insane_move_down


def insane_checkdown (self): #edict_t *

	# if ( (self->s.frame == FRAME_stand94) || (self->s.frame == FRAME_stand65) )
	if not self:

		return


	if self.spawnflags & 32:
		# Always stand
		return
	if local.random() < 0.3:
		if local.random() < 0.5:
			self.monsterinfo.currentmove = insane_move_uptodown
		else:
			self.monsterinfo.currentmove = insane_move_jumpdown


def insane_checkup (self): #edict_t *

	# If Hold_Ground and Crawl are set
	if not self:

		return


	if (self.spawnflags & 4) and (self.spawnflags & 16):
		return
	if local.random() < 0.5:
		self.monsterinfo.currentmove = insane_move_downtoup


def insane_stand(self): #edict_t *

	if not self:

		return


	if self.spawnflags & SPAWNFLAG_CRUSIFIED:

		# If crucified
		self.monsterinfo.currentmove = insane_move_cross
		self.monsterinfo.aiflags |= AI_STAND_GROUND

	elif (self.spawnflags & 4) and (self.spawnflags & 16):

		self.monsterinfo.currentmove = insane_move_down

	elif local.random() < 0.5:

		self.monsterinfo.currentmove = insane_move_stand_normal

	else:

		self.monsterinfo.currentmove = insane_move_stand_insane


def insane_dead(self): #edict_t *

	if not self:

		return


	if self.spawnflags & SPAWNFLAG_CRUSIFIED:

		self.flags |= FL_FLY

	else:

		shared.VectorSet(self.mins, -16, -16, -24)
		shared.VectorSet(self.maxs, 16, 16, -8)
		self.movetype = MOVETYPE_TOSS


	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity(self)


def insane_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	"""
	int n;
	"""

	if not self:

		return


	if self.health <= self.gib_health:

		g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex("misc/udeath.wav"), 1, ATTN_IDLE, 0)
		for n in range(2):

			ThrowGib(self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)


		for n in range(4):

			ThrowGib(self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)


		ThrowHead(self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return


	if self.deadflag == DEAD_DEAD:

		return


	g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex(("player/male/death%i.wav" % ((rand.randk() % 4) + 1,))), 1, ATTN_IDLE, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	if self.spawnflags & SPAWNFLAG_CRUSIFIED:

		insane_dead(self)

	else:

		if ((self.s.frame >= insane_h.FRAME_crawl1) and (self.s.frame <= insane_h.FRAME_crawl9)) or ((self.s.frame >= insane_h.FRAME_stand99) and (self.s.frame <= insane_h.FRAME_stand160)):

			self.monsterinfo.currentmove = insane_move_crawl_death

		else:

			self.monsterinfo.currentmove = insane_move_stand_death


"""QUAKED misc_insane (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn CRAWL CRUCIFIED STAND_GROUND ALWAYS_STAND
"""
def SP_misc_insane(self): #edict_t *
	global sound_fist, sound_moan, sound_shake, sound_step, sound_step2, sound_step3, sound_step4

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_step3 = 0
	sound_step4 = 0
	sound_fist = g_main.gi.soundindex("insane/insane11.wav")
	sound_shake = g_main.gi.soundindex("insane/insane5.wav")
	sound_moan = g_main.gi.soundindex("insane/insane7.wav")
	sound_scream[0] = g_main.gi.soundindex("insane/insane1.wav")
	sound_scream[1] = g_main.gi.soundindex("insane/insane2.wav")
	sound_scream[2] = g_main.gi.soundindex("insane/insane3.wav")
	sound_scream[3] = g_main.gi.soundindex("insane/insane4.wav")
	sound_scream[4] = g_main.gi.soundindex("insane/insane6.wav")
	sound_scream[5] = g_main.gi.soundindex("insane/insane8.wav")
	sound_scream[6] = g_main.gi.soundindex("insane/insane9.wav")
	sound_scream[7] = g_main.gi.soundindex("insane/insane10.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/insane/tris.md2")
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 32)
	self.health = 100
	self.gib_health = -50
	self.mass = 300
	self.pain = insane_pain
	self.die = insane_die
	self.monsterinfo.stand = insane_stand
	self.monsterinfo.walk = insane_walk
	self.monsterinfo.run = insane_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = None
	self.monsterinfo.melee = None
	self.monsterinfo.sight = None
	self.monsterinfo.aiflags |= AI_GOOD_GUY
	g_main.gi.linkentity(self)
	if self.spawnflags & 16:

		# Stand Ground
		self.monsterinfo.aiflags |= AI_STAND_GROUND


	self.monsterinfo.currentmove = insane_move_stand_normal
	self.monsterinfo.scale = insane_h.MODEL_SCALE
	if self.spawnflags & SPAWNFLAG_CRUSIFIED:

		# Crucified ?
		shared.VectorSet(self.mins, -16, 0, 0)
		shared.VectorSet(self.maxs, 16, 8, 32)
		self.flags |= FL_NO_KNOCKBACK
		flymonster_start(self)

	else:

		walkmonster_start(self)
		self.s.skinnum = rand.randk() % 3


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
insane_frames_stand_normal = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, insane_checkdown),
]
insane_move_stand_normal = _mm(insane_h.FRAME_stand60, insane_h.FRAME_stand65, insane_frames_stand_normal, insane_stand)

insane_frames_stand_insane = [
	_mf(ai_stand, 0, insane_shake),
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
	_mf(ai_stand, 0, insane_checkdown),
]
insane_move_stand_insane = _mm(insane_h.FRAME_stand65, insane_h.FRAME_stand94, insane_frames_stand_insane, insane_stand)

insane_frames_uptodown = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, insane_moan),
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
	_mf(ai_move, 2.7, None),
	_mf(ai_move, 4.1, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 7.6, None),
	_mf(ai_move, 3.6, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, insane_fist),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, insane_fist),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
insane_move_uptodown = _mm(insane_h.FRAME_stand1, insane_h.FRAME_stand40, insane_frames_uptodown, insane_onground)

insane_frames_downtoup = [
	_mf(ai_move, -0.7, None),	# 41
	_mf(ai_move, -1.2, None),	# 42
	_mf(ai_move, -1.5, None),	# 43
	_mf(ai_move, -4.5, None),	# 44
	_mf(ai_move, -3.5, None),	# 45
	_mf(ai_move, -0.2, None),	# 46
	_mf(ai_move, 0, None),	# 47
	_mf(ai_move, -1.3, None),	# 48
	_mf(ai_move, -3, None),	# 49
	_mf(ai_move, -2, None),	# 50
	_mf(ai_move, 0, None),	# 51
	_mf(ai_move, 0, None),	# 52
	_mf(ai_move, 0, None),	# 53
	_mf(ai_move, -3.3, None),	# 54
	_mf(ai_move, -1.6, None),	# 55
	_mf(ai_move, -0.3, None),	# 56
	_mf(ai_move, 0, None),	# 57
	_mf(ai_move, 0, None),	# 58
	_mf(ai_move, 0, None),	# 59
]
insane_move_downtoup = _mm(insane_h.FRAME_stand41, insane_h.FRAME_stand59, insane_frames_downtoup, insane_stand)

insane_frames_jumpdown = [
	_mf(ai_move, 0.2, None),
	_mf(ai_move, 11.5, None),
	_mf(ai_move, 5.1, None),
	_mf(ai_move, 7.1, None),
	_mf(ai_move, 0, None),
]
insane_move_jumpdown = _mm(insane_h.FRAME_stand96, insane_h.FRAME_stand100, insane_frames_jumpdown, insane_onground)

insane_frames_down = [
	_mf(ai_move, 0, None),	# 100
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),	# 110
	_mf(ai_move, -1.7, None),
	_mf(ai_move, -1.6, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, insane_fist),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),	# 120
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),	# 130
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, insane_moan),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),	# 140
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),	# 150
	_mf(ai_move, 0.5, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -0.2, insane_scream),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0.2, None),
	_mf(ai_move, 0.4, None),
	_mf(ai_move, 0.6, None),
	_mf(ai_move, 0.8, None),
	_mf(ai_move, 0.7, None),
	_mf(ai_move, 0, insane_checkup),	# 160
]
insane_move_down = _mm(insane_h.FRAME_stand100, insane_h.FRAME_stand160, insane_frames_down, insane_onground)

insane_frames_walk_normal = [
	_mf(ai_walk, 0, insane_scream), _mf(ai_walk, 2.5, None), _mf(ai_walk, 3.5, None),
	_mf(ai_walk, 1.7, None), _mf(ai_walk, 2.3, None), _mf(ai_walk, 2.4, None),
	_mf(ai_walk, 2.2, insane_footstep), _mf(ai_walk, 4.2, None), _mf(ai_walk, 5.6, None),
	_mf(ai_walk, 3.3, None), _mf(ai_walk, 2.4, None), _mf(ai_walk, 0.9, None),
	_mf(ai_walk, 0, insane_footstep)]
insane_move_walk_normal = _mm(insane_h.FRAME_walk27, insane_h.FRAME_walk39, insane_frames_walk_normal, insane_walk)

insane_move_run_normal = _mm(insane_h.FRAME_walk27, insane_h.FRAME_walk39, insane_frames_walk_normal, insane_run)

insane_frames_walk_insane = [
	_mf(ai_walk, 0, insane_scream), _mf(ai_walk, 3.4, None), _mf(ai_walk, 3.6, None),
	_mf(ai_walk, 2.9, None), _mf(ai_walk, 2.2, None), _mf(ai_walk, 2.6, None),
	_mf(ai_walk, 0, insane_footstep), _mf(ai_walk, 0.7, None), _mf(ai_walk, 4.8, None),
	_mf(ai_walk, 5.3, None), _mf(ai_walk, 1.1, None), _mf(ai_walk, 2, insane_footstep),
	_mf(ai_walk, 0.5, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 4.9, None), _mf(ai_walk, 6.7, None), _mf(ai_walk, 3.8, None),
	_mf(ai_walk, 2, insane_footstep), _mf(ai_walk, 0.2, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 3.4, None), _mf(ai_walk, 6.4, None), _mf(ai_walk, 5, None),
	_mf(ai_walk, 1.8, insane_footstep), _mf(ai_walk, 0, None)]
insane_move_walk_insane = _mm(insane_h.FRAME_walk1, insane_h.FRAME_walk26, insane_frames_walk_insane, insane_walk)

insane_move_run_insane = _mm(insane_h.FRAME_walk1, insane_h.FRAME_walk26, insane_frames_walk_insane, insane_run)

insane_frames_stand_pain = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, insane_footstep), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None)]
insane_move_stand_pain = _mm(insane_h.FRAME_st_pain2, insane_h.FRAME_st_pain12, insane_frames_stand_pain, insane_run)

insane_frames_stand_death = [
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
insane_move_stand_death = _mm(insane_h.FRAME_st_death2, insane_h.FRAME_st_death18, insane_frames_stand_death, insane_dead)

insane_frames_crawl = [
	_mf(ai_walk, 0, insane_scream),
	_mf(ai_walk, 1.5, None),
	_mf(ai_walk, 2.1, None),
	_mf(ai_walk, 3.6, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 0.9, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 3.4, None),
	_mf(ai_walk, 2.4, None),
]
insane_move_crawl = _mm(insane_h.FRAME_crawl1, insane_h.FRAME_crawl9, insane_frames_crawl, None)

insane_move_runcrawl = _mm(insane_h.FRAME_crawl1, insane_h.FRAME_crawl9, insane_frames_crawl, None)

insane_frames_crawl_pain = [
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
insane_move_crawl_pain = _mm(insane_h.FRAME_cr_pain2, insane_h.FRAME_cr_pain10, insane_frames_crawl_pain, insane_run)

insane_frames_crawl_death = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
insane_move_crawl_death = _mm(insane_h.FRAME_cr_death10, insane_h.FRAME_cr_death16, insane_frames_crawl_death, insane_dead)

insane_frames_cross = [
	_mf(ai_move, 0, insane_moan),
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
insane_move_cross = _mm(insane_h.FRAME_cross1, insane_h.FRAME_cross15, insane_frames_cross, insane_cross)

insane_frames_struggle_cross = [
	_mf(ai_move, 0, insane_scream),
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
insane_move_struggle_cross = _mm(insane_h.FRAME_cross16, insane_h.FRAME_cross30, insane_frames_struggle_cross, insane_cross)
