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
import random as _r
import numpy as np
from game import g_main, g_local, q_shared, m_flash
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_local import (DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (swimmonster_start)
from game.g_utils import (G_FreeEdict)
from game.g_weapon import (fire_hit)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_NORM, CHAN_VOICE, CHAN_WEAPON)
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_flipper.h
FRAME_flpbit01 = 0
FRAME_flpbit02 = 1
FRAME_flpbit03 = 2
FRAME_flpbit04 = 3
FRAME_flpbit05 = 4
FRAME_flpbit06 = 5
FRAME_flpbit07 = 6
FRAME_flpbit08 = 7
FRAME_flpbit09 = 8
FRAME_flpbit10 = 9
FRAME_flpbit11 = 10
FRAME_flpbit12 = 11
FRAME_flpbit13 = 12
FRAME_flpbit14 = 13
FRAME_flpbit15 = 14
FRAME_flpbit16 = 15
FRAME_flpbit17 = 16
FRAME_flpbit18 = 17
FRAME_flpbit19 = 18
FRAME_flpbit20 = 19
FRAME_flptal01 = 20
FRAME_flptal02 = 21
FRAME_flptal03 = 22
FRAME_flptal04 = 23
FRAME_flptal05 = 24
FRAME_flptal06 = 25
FRAME_flptal07 = 26
FRAME_flptal08 = 27
FRAME_flptal09 = 28
FRAME_flptal10 = 29
FRAME_flptal11 = 30
FRAME_flptal12 = 31
FRAME_flptal13 = 32
FRAME_flptal14 = 33
FRAME_flptal15 = 34
FRAME_flptal16 = 35
FRAME_flptal17 = 36
FRAME_flptal18 = 37
FRAME_flptal19 = 38
FRAME_flptal20 = 39
FRAME_flptal21 = 40
FRAME_flphor01 = 41
FRAME_flphor02 = 42
FRAME_flphor03 = 43
FRAME_flphor04 = 44
FRAME_flphor05 = 45
FRAME_flphor06 = 46
FRAME_flphor07 = 47
FRAME_flphor08 = 48
FRAME_flphor09 = 49
FRAME_flphor10 = 50
FRAME_flphor11 = 51
FRAME_flphor12 = 52
FRAME_flphor13 = 53
FRAME_flphor14 = 54
FRAME_flphor15 = 55
FRAME_flphor16 = 56
FRAME_flphor17 = 57
FRAME_flphor18 = 58
FRAME_flphor19 = 59
FRAME_flphor20 = 60
FRAME_flphor21 = 61
FRAME_flphor22 = 62
FRAME_flphor23 = 63
FRAME_flphor24 = 64
FRAME_flpver01 = 65
FRAME_flpver02 = 66
FRAME_flpver03 = 67
FRAME_flpver04 = 68
FRAME_flpver05 = 69
FRAME_flpver06 = 70
FRAME_flpver07 = 71
FRAME_flpver08 = 72
FRAME_flpver09 = 73
FRAME_flpver10 = 74
FRAME_flpver11 = 75
FRAME_flpver12 = 76
FRAME_flpver13 = 77
FRAME_flpver14 = 78
FRAME_flpver15 = 79
FRAME_flpver16 = 80
FRAME_flpver17 = 81
FRAME_flpver18 = 82
FRAME_flpver19 = 83
FRAME_flpver20 = 84
FRAME_flpver21 = 85
FRAME_flpver22 = 86
FRAME_flpver23 = 87
FRAME_flpver24 = 88
FRAME_flpver25 = 89
FRAME_flpver26 = 90
FRAME_flpver27 = 91
FRAME_flpver28 = 92
FRAME_flpver29 = 93
FRAME_flppn101 = 94
FRAME_flppn102 = 95
FRAME_flppn103 = 96
FRAME_flppn104 = 97
FRAME_flppn105 = 98
FRAME_flppn201 = 99
FRAME_flppn202 = 100
FRAME_flppn203 = 101
FRAME_flppn204 = 102
FRAME_flppn205 = 103
FRAME_flpdth01 = 104
FRAME_flpdth02 = 105
FRAME_flpdth03 = 106
FRAME_flpdth04 = 107
FRAME_flpdth05 = 108
FRAME_flpdth06 = 109
FRAME_flpdth07 = 110
FRAME_flpdth08 = 111
FRAME_flpdth09 = 112
FRAME_flpdth10 = 113
FRAME_flpdth11 = 114
FRAME_flpdth12 = 115
FRAME_flpdth13 = 116
FRAME_flpdth14 = 117
FRAME_flpdth15 = 118
FRAME_flpdth16 = 119
FRAME_flpdth17 = 120
FRAME_flpdth18 = 121
FRAME_flpdth19 = 122
FRAME_flpdth20 = 123
FRAME_flpdth21 = 124
FRAME_flpdth22 = 125
FRAME_flpdth23 = 126
FRAME_flpdth24 = 127
FRAME_flpdth25 = 128
FRAME_flpdth26 = 129
FRAME_flpdth27 = 130
FRAME_flpdth28 = 131
FRAME_flpdth29 = 132
FRAME_flpdth30 = 133
FRAME_flpdth31 = 134
FRAME_flpdth32 = 135
FRAME_flpdth33 = 136
FRAME_flpdth34 = 137
FRAME_flpdth35 = 138
FRAME_flpdth36 = 139
FRAME_flpdth37 = 140
FRAME_flpdth38 = 141
FRAME_flpdth39 = 142
FRAME_flpdth40 = 143
FRAME_flpdth41 = 144
FRAME_flpdth42 = 145
FRAME_flpdth43 = 146
FRAME_flpdth44 = 147
FRAME_flpdth45 = 148
FRAME_flpdth46 = 149
FRAME_flpdth47 = 150
FRAME_flpdth48 = 151
FRAME_flpdth49 = 152
FRAME_flpdth50 = 153
FRAME_flpdth51 = 154
FRAME_flpdth52 = 155
FRAME_flpdth53 = 156
FRAME_flpdth54 = 157
FRAME_flpdth55 = 158
FRAME_flpdth56 = 159
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

	self.monsterinfo.currentmove = flipper_move_stand


def flipper_run_loop (self): #edict_t *

	self.monsterinfo.currentmove = flipper_move_run_loop


def flipper_run (self): #edict_t *

	self.monsterinfo.currentmove = flipper_move_run_start


def flipper_walk (self): #edict_t *

	self.monsterinfo.currentmove = flipper_move_walk


def flipper_start_run (self): #edict_t *

	self.monsterinfo.currentmove = flipper_move_start_run


def flipper_bite (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSet (aim, MELEE_DISTANCE, 0, 0)
	fire_hit (self, aim, 5, 0)


def flipper_preattack (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_chomp, 1, ATTN_NORM, 0)


def flipper_melee (self): #edict_t *

	self.monsterinfo.currentmove = flipper_move_attack


def flipper_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	#int	n;

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	n = (_r.randint(0, 2147483647) + 1) % 2
	if n == 0:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flipper_move_pain1
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = flipper_move_pain2


def flipper_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def flipper_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def flipper_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# check for gib
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
def SP_monster_flipper (self): #edict_t *

	global sound_chomp, sound_attack, sound_pain1, sound_pain2, sound_death, sound_idle, sound_search, sound_sight
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("flipper/flppain1.wav")
	sound_pain2 = g_main.gi.soundindex ("flipper/flppain2.wav")
	sound_death = g_main.gi.soundindex ("flipper/flpdeth1.wav")
	sound_chomp = g_main.gi.soundindex ("flipper/flpatck1.wav")
	sound_attack = g_main.gi.soundindex ("flipper/flpatck2.wav")
	sound_idle = g_main.gi.soundindex ("flipper/flpidle1.wav")
	sound_search = g_main.gi.soundindex ("flipper/flpsrch1.wav")
	sound_sight = g_main.gi.soundindex ("flipper/flpsght1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/flipper/tris.md2")
	q_shared.VectorSet (self.mins, -16, -16, 0)
	q_shared.VectorSet (self.maxs, 16, 16, 32)

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

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = flipper_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	swimmonster_start (self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
flipper_frames_stand = [
	_mf(ai_stand, 0, None),
]
flipper_move_stand = _mm(FRAME_flphor01, FRAME_flphor01, flipper_frames_stand, None)

FLIPPER_RUN_SPEED = 24

flipper_frames_run = [
	_mf(ai_run, FLIPPER_RUN_SPEED, None),	# 6
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),	# 10
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),	# 20
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),
	_mf(ai_run, FLIPPER_RUN_SPEED, None),	# 29
]
flipper_move_run_loop = _mm(FRAME_flpver06, FRAME_flpver29, flipper_frames_run, None)

flipper_frames_run_start = [
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
]
flipper_move_run_start = _mm(FRAME_flpver01, FRAME_flpver06, flipper_frames_run_start, flipper_run_loop)

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
flipper_move_walk = _mm(FRAME_flphor01, FRAME_flphor24, flipper_frames_walk, None)

flipper_frames_start_run = [
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 8, flipper_run),
]
flipper_move_start_run = _mm(FRAME_flphor01, FRAME_flphor05, flipper_frames_start_run, None)

flipper_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flipper_move_pain2 = _mm(FRAME_flppn101, FRAME_flppn105, flipper_frames_pain2, flipper_run)

flipper_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
flipper_move_pain1 = _mm(FRAME_flppn201, FRAME_flppn205, flipper_frames_pain1, flipper_run)

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
flipper_move_attack = _mm(FRAME_flpbit01, FRAME_flpbit20, flipper_frames_attack, flipper_run)

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
flipper_move_death = _mm(FRAME_flpdth01, FRAME_flpdth56, flipper_frames_death, flipper_dead)


