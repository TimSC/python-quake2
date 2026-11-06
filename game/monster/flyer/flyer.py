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

Flyer.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict
from game.g_weapon import fire_hit
from game.g_monster import monster_fire_blaster, flymonster_start
from game.g_misc import BecomeExplosion1
from common.header.shared import CHAN_VOICE, CHAN_WEAPON, ATTN_NORM, ATTN_IDLE, EF_HYPERBLASTER, MZ2_FLYER_BLASTER_1, MZ2_FLYER_BLASTER_2
from game.header.local import MELEE_DISTANCE, MOVETYPE_STEP, AI_STAND_GROUND, RANGE_MELEE
from game.header.game import SOLID_BBOX
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.flyer import flyer_h

"""
#include "../../header/local.h"
#include "flyer.h"
"""

# m_flyer.h

ACTION_nothing = 0
ACTION_attack1 = 1
ACTION_attack2 = 2
ACTION_run = 3
ACTION_walk = 4


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

"""
==============================================================================

flyer

==============================================================================
"""

nextmove = 0 # static int, Used for start/stop frames

sound_sight = 0 # static int
sound_idle = 0 # static int
sound_pain1 = 0 # static int
sound_pain2 = 0 # static int
sound_slash = 0 # static int
sound_sproing = 0 # static int
sound_die = 0 # static int


def flyer_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def flyer_idle (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def flyer_pop_blades (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sproing, 1, ATTN_NORM, 0)


def flyer_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = flyer_move_stand
	else:
		self.monsterinfo.currentmove = flyer_move_run


def flyer_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_walk


def flyer_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_stand


def flyer_stop (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_stop


def flyer_start (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_start


def flyer_fire (self, flash_number): #edict_t *, int

	if not self or not self.enemy:

		return


	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int		effect;

	if (self.s.frame == flyer_h.FRAME_attak204) or (self.s.frame == flyer_h.FRAME_attak207) or (self.s.frame == flyer_h.FRAME_attak210):
		effect = EF_HYPERBLASTER
	else:
		effect = 0
	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 1, 1000, flash_number, effect)


def flyer_fireleft (self): #edict_t *

	if not self:

		return


	flyer_fire (self, MZ2_FLYER_BLASTER_1)


def flyer_fireright (self): #edict_t *

	if not self:

		return


	flyer_fire (self, MZ2_FLYER_BLASTER_2)


def flyer_slash_left (self): #edict_t *

	if not self:

		return


	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	shared.VectorSet (aim, MELEE_DISTANCE, self.mins[0], 0)
	fire_hit (self, aim, 5, 0)
	g_main.gi.sound (self, CHAN_WEAPON, sound_slash, 1, ATTN_NORM, 0)


def flyer_slash_right (self): #edict_t *

	if not self:

		return


	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	shared.VectorSet (aim, MELEE_DISTANCE, self.maxs[0], 0)
	fire_hit (self, aim, 5, 0)
	g_main.gi.sound (self, CHAN_WEAPON, sound_slash, 1, ATTN_NORM, 0)


def flyer_loop_melee (self): #edict_t *

	#	if (random() <= 0.5)
	#		self->monsterinfo.currentmove = &flyer_move_attack1;
	#	else
	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_loop_melee


def flyer_attack (self): #edict_t *

	#	if (random() <= 0.5)
	#		self->monsterinfo.currentmove = &flyer_move_attack1;
	#	else
	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_attack2


def flyer_setstart (self): #edict_t *

	global nextmove

	if not self:

		return


	nextmove = ACTION_run
	self.monsterinfo.currentmove = flyer_move_start


def flyer_nextmove (self): #edict_t *

	if not self:

		return


	if nextmove == ACTION_attack1:
		self.monsterinfo.currentmove = flyer_move_start_melee
	elif nextmove == ACTION_attack2:
		self.monsterinfo.currentmove = flyer_move_attack2
	elif nextmove == ACTION_run:
		self.monsterinfo.currentmove = flyer_move_run


def flyer_melee (self): #edict_t *

	#	flyer.nextmove = ACTION_attack1;
	#	self->monsterinfo.currentmove = &flyer_move_stop;
	if not self:

		return


	self.monsterinfo.currentmove = flyer_move_start_melee


def flyer_check_melee(self): #edict_t *

	if not self:

		return


	if g_ai.ai_range(self, self.enemy) == RANGE_MELEE:

		if local.random() <= 0.8:

			self.monsterinfo.currentmove = flyer_move_loop_melee

		else:

			self.monsterinfo.currentmove = flyer_move_end_melee


	else:

		self.monsterinfo.currentmove = flyer_move_end_melee


def flyer_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

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


	n = rand.randk() % 3
	if n == 0:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flyer_move_pain1

	elif n == 1:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flyer_move_pain2

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flyer_move_pain3


def flyer_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	BecomeExplosion1(self)


"""QUAKED monster_flyer (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_flyer (self): #edict_t *

	global sound_sight, sound_idle, sound_pain1, sound_pain2, sound_slash, sound_sproing, sound_die

	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	# fix a map bug in jail5.bsp
	if not shared_c.Q_stricmp(g_main.level.mapname, "jail5") and (self.s.origin[2] == -104):
		self.targetname = self.target
		self.target = None

	sound_sight = g_main.gi.soundindex ("flyer/flysght1.wav")
	sound_idle = g_main.gi.soundindex ("flyer/flysrch1.wav")
	sound_pain1 = g_main.gi.soundindex ("flyer/flypain1.wav")
	sound_pain2 = g_main.gi.soundindex ("flyer/flypain2.wav")
	sound_slash = g_main.gi.soundindex ("flyer/flyatck2.wav")
	sound_sproing = g_main.gi.soundindex ("flyer/flyatck1.wav")
	sound_die = g_main.gi.soundindex ("flyer/flydeth1.wav")

	g_main.gi.soundindex ("flyer/flyatck3.wav")

	self.s.modelindex = g_main.gi.modelindex ("models/monsters/flyer/tris.md2")
	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, 32)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX

	self.s.sound = g_main.gi.soundindex ("flyer/flyidle1.wav")

	self.health = 50
	self.mass = 50

	self.pain = flyer_pain
	self.die = flyer_die

	self.monsterinfo.stand = flyer_stand
	self.monsterinfo.walk = flyer_walk
	self.monsterinfo.run = flyer_run
	self.monsterinfo.attack = flyer_attack
	self.monsterinfo.melee = flyer_melee
	self.monsterinfo.sight = flyer_sight
	self.monsterinfo.idle = flyer_idle

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = flyer_move_stand
	self.monsterinfo.scale = flyer_h.MODEL_SCALE

	flymonster_start (self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
flyer_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
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
flyer_move_stand = _mm(flyer_h.FRAME_stand01, flyer_h.FRAME_stand45, flyer_frames_stand, None)

flyer_frames_walk = [
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
flyer_move_walk = _mm(flyer_h.FRAME_stand01, flyer_h.FRAME_stand45, flyer_frames_walk, None)

flyer_frames_run = [
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
flyer_move_run = _mm(flyer_h.FRAME_stand01, flyer_h.FRAME_stand45, flyer_frames_run, None)

flyer_frames_start = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, flyer_nextmove),
]
flyer_move_start = _mm(flyer_h.FRAME_start01, flyer_h.FRAME_start06, flyer_frames_start, None)

flyer_frames_stop = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, flyer_nextmove),
]
flyer_move_stop = _mm(flyer_h.FRAME_stop01, flyer_h.FRAME_stop07, flyer_frames_stop, None)

flyer_frames_rollright = [
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
flyer_move_rollright = _mm(flyer_h.FRAME_rollr01, flyer_h.FRAME_rollr09, flyer_frames_rollright, None)

flyer_frames_rollleft = [
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
flyer_move_rollleft = _mm(flyer_h.FRAME_rollf01, flyer_h.FRAME_rollf09, flyer_frames_rollleft, None)

flyer_frames_pain3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_pain3 = _mm(flyer_h.FRAME_pain301, flyer_h.FRAME_pain304, flyer_frames_pain3, flyer_run)

flyer_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_pain2 = _mm(flyer_h.FRAME_pain201, flyer_h.FRAME_pain204, flyer_frames_pain2, flyer_run)

flyer_frames_pain1 = [
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
flyer_move_pain1 = _mm(flyer_h.FRAME_pain101, flyer_h.FRAME_pain109, flyer_frames_pain1, flyer_run)

flyer_frames_defense = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),		# Hold this frame
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_defense = _mm(flyer_h.FRAME_defens01, flyer_h.FRAME_defens06, flyer_frames_defense, None)

flyer_frames_bankright = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_bankright = _mm(flyer_h.FRAME_bankr01, flyer_h.FRAME_bankr07, flyer_frames_bankright, None)

flyer_frames_bankleft = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_bankleft = _mm(flyer_h.FRAME_bankl01, flyer_h.FRAME_bankl07, flyer_frames_bankleft, None)

flyer_frames_attack2 = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -10, flyer_fireleft),		# left gun
	_mf(ai_charge, -10, flyer_fireright),		# right gun
	_mf(ai_charge, -10, flyer_fireleft),		# left gun
	_mf(ai_charge, -10, flyer_fireright),		# right gun
	_mf(ai_charge, -10, flyer_fireleft),		# left gun
	_mf(ai_charge, -10, flyer_fireright),		# right gun
	_mf(ai_charge, -10, flyer_fireleft),		# left gun
	_mf(ai_charge, -10, flyer_fireright),		# right gun
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
flyer_move_attack2 = _mm(flyer_h.FRAME_attak201, flyer_h.FRAME_attak217, flyer_frames_attack2, flyer_run)

flyer_frames_start_melee = [
	_mf(ai_charge, 0, flyer_pop_blades),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
flyer_move_start_melee = _mm(flyer_h.FRAME_attak101, flyer_h.FRAME_attak106, flyer_frames_start_melee, flyer_loop_melee)

flyer_frames_end_melee = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
flyer_move_end_melee = _mm(flyer_h.FRAME_attak119, flyer_h.FRAME_attak121, flyer_frames_end_melee, flyer_run)

flyer_frames_loop_melee = [
	_mf(ai_charge, 0, None),		# Loop Start
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, flyer_slash_left),		# Left Wing Strike
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, flyer_slash_right),		# Right Wing Strike
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),		# Loop Ends
]
flyer_move_loop_melee = _mm(flyer_h.FRAME_attak107, flyer_h.FRAME_attak118, flyer_frames_loop_melee, flyer_check_melee)
