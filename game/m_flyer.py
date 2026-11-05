"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""
from __future__ import annotations

import random as _r
import numpy as np
from game import g_local, g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict
from game.g_weapon import fire_hit
from game.g_monster import monster_fire_blaster, flymonster_start
from game.g_misc import BecomeExplosion1
from common.header.shared import CHAN_VOICE, CHAN_WEAPON, ATTN_NORM, ATTN_IDLE, EF_HYPERBLASTER, MZ2_FLYER_BLASTER_1, MZ2_FLYER_BLASTER_2
from game.g_local import (MELEE_DISTANCE, MOVETYPE_STEP, AI_STAND_GROUND, RANGE_MELEE)
from game.game import SOLID_BBOX
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c

# m_flyer.h
ACTION_nothing = 0
ACTION_attack1 = 1
ACTION_attack2 = 2
ACTION_run = 3
ACTION_walk = 4
FRAME_start01 = 0
FRAME_start02 = 1
FRAME_start03 = 2
FRAME_start04 = 3
FRAME_start05 = 4
FRAME_start06 = 5
FRAME_stop01 = 6
FRAME_stop02 = 7
FRAME_stop03 = 8
FRAME_stop04 = 9
FRAME_stop05 = 10
FRAME_stop06 = 11
FRAME_stop07 = 12
FRAME_stand01 = 13
FRAME_stand02 = 14
FRAME_stand03 = 15
FRAME_stand04 = 16
FRAME_stand05 = 17
FRAME_stand06 = 18
FRAME_stand07 = 19
FRAME_stand08 = 20
FRAME_stand09 = 21
FRAME_stand10 = 22
FRAME_stand11 = 23
FRAME_stand12 = 24
FRAME_stand13 = 25
FRAME_stand14 = 26
FRAME_stand15 = 27
FRAME_stand16 = 28
FRAME_stand17 = 29
FRAME_stand18 = 30
FRAME_stand19 = 31
FRAME_stand20 = 32
FRAME_stand21 = 33
FRAME_stand22 = 34
FRAME_stand23 = 35
FRAME_stand24 = 36
FRAME_stand25 = 37
FRAME_stand26 = 38
FRAME_stand27 = 39
FRAME_stand28 = 40
FRAME_stand29 = 41
FRAME_stand30 = 42
FRAME_stand31 = 43
FRAME_stand32 = 44
FRAME_stand33 = 45
FRAME_stand34 = 46
FRAME_stand35 = 47
FRAME_stand36 = 48
FRAME_stand37 = 49
FRAME_stand38 = 50
FRAME_stand39 = 51
FRAME_stand40 = 52
FRAME_stand41 = 53
FRAME_stand42 = 54
FRAME_stand43 = 55
FRAME_stand44 = 56
FRAME_stand45 = 57
FRAME_attak101 = 58
FRAME_attak102 = 59
FRAME_attak103 = 60
FRAME_attak104 = 61
FRAME_attak105 = 62
FRAME_attak106 = 63
FRAME_attak107 = 64
FRAME_attak108 = 65
FRAME_attak109 = 66
FRAME_attak110 = 67
FRAME_attak111 = 68
FRAME_attak112 = 69
FRAME_attak113 = 70
FRAME_attak114 = 71
FRAME_attak115 = 72
FRAME_attak116 = 73
FRAME_attak117 = 74
FRAME_attak118 = 75
FRAME_attak119 = 76
FRAME_attak120 = 77
FRAME_attak121 = 78
FRAME_attak201 = 79
FRAME_attak202 = 80
FRAME_attak203 = 81
FRAME_attak204 = 82
FRAME_attak205 = 83
FRAME_attak206 = 84
FRAME_attak207 = 85
FRAME_attak208 = 86
FRAME_attak209 = 87
FRAME_attak210 = 88
FRAME_attak211 = 89
FRAME_attak212 = 90
FRAME_attak213 = 91
FRAME_attak214 = 92
FRAME_attak215 = 93
FRAME_attak216 = 94
FRAME_attak217 = 95
FRAME_bankl01 = 96
FRAME_bankl02 = 97
FRAME_bankl03 = 98
FRAME_bankl04 = 99
FRAME_bankl05 = 100
FRAME_bankl06 = 101
FRAME_bankl07 = 102
FRAME_bankr01 = 103
FRAME_bankr02 = 104
FRAME_bankr03 = 105
FRAME_bankr04 = 106
FRAME_bankr05 = 107
FRAME_bankr06 = 108
FRAME_bankr07 = 109
FRAME_rollf01 = 110
FRAME_rollf02 = 111
FRAME_rollf03 = 112
FRAME_rollf04 = 113
FRAME_rollf05 = 114
FRAME_rollf06 = 115
FRAME_rollf07 = 116
FRAME_rollf08 = 117
FRAME_rollf09 = 118
FRAME_rollr01 = 119
FRAME_rollr02 = 120
FRAME_rollr03 = 121
FRAME_rollr04 = 122
FRAME_rollr05 = 123
FRAME_rollr06 = 124
FRAME_rollr07 = 125
FRAME_rollr08 = 126
FRAME_rollr09 = 127
FRAME_defens01 = 128
FRAME_defens02 = 129
FRAME_defens03 = 130
FRAME_defens04 = 131
FRAME_defens05 = 132
FRAME_defens06 = 133
FRAME_pain101 = 134
FRAME_pain102 = 135
FRAME_pain103 = 136
FRAME_pain104 = 137
FRAME_pain105 = 138
FRAME_pain106 = 139
FRAME_pain107 = 140
FRAME_pain108 = 141
FRAME_pain109 = 142
FRAME_pain201 = 143
FRAME_pain202 = 144
FRAME_pain203 = 145
FRAME_pain204 = 146
FRAME_pain301 = 147
FRAME_pain302 = 148
FRAME_pain303 = 149
FRAME_pain304 = 150
MODEL_SCALE = 1.000000


def _mf(aifunc, dist, thinkfunc):
	f = g_local.mframe_t()
	f.aifunc = aifunc
	f.dist = dist
	f.thinkfunc = thinkfunc
	return f

def _mm(first, last, frames, endfunc):
	m = g_local.mmove_t()
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

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def flyer_idle (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def flyer_pop_blades (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sproing, 1, ATTN_NORM, 0)


def flyer_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = flyer_move_stand
	else:
		self.monsterinfo.currentmove = flyer_move_run


def flyer_walk (self): #edict_t *

	self.monsterinfo.currentmove = flyer_move_walk


def flyer_stand (self): #edict_t *

	self.monsterinfo.currentmove = flyer_move_stand


def flyer_stop (self): #edict_t *

	self.monsterinfo.currentmove = flyer_move_stop


def flyer_start (self): #edict_t *

	self.monsterinfo.currentmove = flyer_move_start


def flyer_fire (self, flash_number): #edict_t *, int

	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int		effect;

	if (self.s.frame == FRAME_attak204) or (self.s.frame == FRAME_attak207) or (self.s.frame == FRAME_attak210):
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

	flyer_fire (self, MZ2_FLYER_BLASTER_1)


def flyer_fireright (self): #edict_t *

	flyer_fire (self, MZ2_FLYER_BLASTER_2)


def flyer_slash_left (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	shared.VectorSet (aim, MELEE_DISTANCE, self.mins[0], 0)
	fire_hit (self, aim, 5, 0)
	g_main.gi.sound (self, CHAN_WEAPON, sound_slash, 1, ATTN_NORM, 0)


def flyer_slash_right (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	shared.VectorSet (aim, MELEE_DISTANCE, self.maxs[0], 0)
	fire_hit (self, aim, 5, 0)
	g_main.gi.sound (self, CHAN_WEAPON, sound_slash, 1, ATTN_NORM, 0)


def flyer_loop_melee (self): #edict_t *

	#	if (random() <= 0.5)
	#		self->monsterinfo.currentmove = &flyer_move_attack1;
	#	else
	self.monsterinfo.currentmove = flyer_move_loop_melee


def flyer_attack (self): #edict_t *

	#	if (random() <= 0.5)
	#		self->monsterinfo.currentmove = &flyer_move_attack1;
	#	else
	self.monsterinfo.currentmove = flyer_move_attack2


def flyer_setstart (self): #edict_t *

	global nextmove

	nextmove = ACTION_run
	self.monsterinfo.currentmove = flyer_move_start


def flyer_nextmove (self): #edict_t *

	if nextmove == ACTION_attack1:
		self.monsterinfo.currentmove = flyer_move_start_melee
	elif nextmove == ACTION_attack2:
		self.monsterinfo.currentmove = flyer_move_attack2
	elif nextmove == ACTION_run:
		self.monsterinfo.currentmove = flyer_move_run


def flyer_melee (self): #edict_t *

	#	flyer.nextmove = ACTION_attack1;
	#	self->monsterinfo.currentmove = &flyer_move_stop;
	self.monsterinfo.currentmove = flyer_move_start_melee


def flyer_check_melee (self): #edict_t *

	if g_ai.range (self, self.enemy) == RANGE_MELEE:
		if g_local.random() <= 0.8:
			self.monsterinfo.currentmove = flyer_move_loop_melee
		else:
			self.monsterinfo.currentmove = flyer_move_end_melee
	else:
		self.monsterinfo.currentmove = flyer_move_end_melee


def flyer_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	#int		n;

	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == 3:
		return		# no pain anims in nightmare

	n = _r.randint(0, 2147483647) % 3
	if n == 0:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flyer_move_pain1
	elif n == 1:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flyer_move_pain2
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flyer_move_pain3


def flyer_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	BecomeExplosion1(self)


"""QUAKED monster_flyer (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_flyer (self): #edict_t *

	global sound_sight, sound_idle, sound_pain1, sound_pain2, sound_slash, sound_sproing, sound_die

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
	self.monsterinfo.scale = MODEL_SCALE

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
flyer_move_stand = _mm(FRAME_stand01, FRAME_stand45, flyer_frames_stand, None)

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
flyer_move_walk = _mm(FRAME_stand01, FRAME_stand45, flyer_frames_walk, None)

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
flyer_move_run = _mm(FRAME_stand01, FRAME_stand45, flyer_frames_run, None)

flyer_frames_start = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, flyer_nextmove),
]
flyer_move_start = _mm(FRAME_start01, FRAME_start06, flyer_frames_start, None)

flyer_frames_stop = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, flyer_nextmove),
]
flyer_move_stop = _mm(FRAME_stop01, FRAME_stop07, flyer_frames_stop, None)

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
flyer_move_rollright = _mm(FRAME_rollr01, FRAME_rollr09, flyer_frames_rollright, None)

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
flyer_move_rollleft = _mm(FRAME_rollf01, FRAME_rollf09, flyer_frames_rollleft, None)

flyer_frames_pain3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_pain3 = _mm(FRAME_pain301, FRAME_pain304, flyer_frames_pain3, flyer_run)

flyer_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_pain2 = _mm(FRAME_pain201, FRAME_pain204, flyer_frames_pain2, flyer_run)

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
flyer_move_pain1 = _mm(FRAME_pain101, FRAME_pain109, flyer_frames_pain1, flyer_run)

flyer_frames_defense = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),		# Hold this frame
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_defense = _mm(FRAME_defens01, FRAME_defens06, flyer_frames_defense, None)

flyer_frames_bankright = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_bankright = _mm(FRAME_bankr01, FRAME_bankr07, flyer_frames_bankright, None)

flyer_frames_bankleft = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flyer_move_bankleft = _mm(FRAME_bankl01, FRAME_bankl07, flyer_frames_bankleft, None)

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
flyer_move_attack2 = _mm(FRAME_attak201, FRAME_attak217, flyer_frames_attack2, flyer_run)

flyer_frames_start_melee = [
	_mf(ai_charge, 0, flyer_pop_blades),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
flyer_move_start_melee = _mm(FRAME_attak101, FRAME_attak106, flyer_frames_start_melee, flyer_loop_melee)

flyer_frames_end_melee = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
flyer_move_end_melee = _mm(FRAME_attak119, FRAME_attak121, flyer_frames_end_melee, flyer_run)

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
flyer_move_loop_melee = _mm(FRAME_attak107, FRAME_attak118, flyer_frames_loop_melee, flyer_check_melee)


