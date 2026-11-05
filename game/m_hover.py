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
from game import g_main, g_local, q_shared, m_flash, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_local import (AI_STAND_GROUND, DEAD_DEAD, FRAMETIME, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t)
from game.g_misc import (BecomeExplosion1, ThrowGib, ThrowHead)
from game.g_monster import (flymonster_start, monster_fire_blaster)
from game.g_utils import (G_FreeEdict, G_ProjectSource)
from game.game import (SOLID_BBOX)
from game.q_shared import (ATTN_NORM, CHAN_VOICE, EF_HYPERBLASTER, MZ2_HOVER_BLASTER_1)
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_hover.h
FRAME_stand01 = 0
FRAME_stand02 = 1
FRAME_stand03 = 2
FRAME_stand04 = 3
FRAME_stand05 = 4
FRAME_stand06 = 5
FRAME_stand07 = 6
FRAME_stand08 = 7
FRAME_stand09 = 8
FRAME_stand10 = 9
FRAME_stand11 = 10
FRAME_stand12 = 11
FRAME_stand13 = 12
FRAME_stand14 = 13
FRAME_stand15 = 14
FRAME_stand16 = 15
FRAME_stand17 = 16
FRAME_stand18 = 17
FRAME_stand19 = 18
FRAME_stand20 = 19
FRAME_stand21 = 20
FRAME_stand22 = 21
FRAME_stand23 = 22
FRAME_stand24 = 23
FRAME_stand25 = 24
FRAME_stand26 = 25
FRAME_stand27 = 26
FRAME_stand28 = 27
FRAME_stand29 = 28
FRAME_stand30 = 29
FRAME_forwrd01 = 30
FRAME_forwrd02 = 31
FRAME_forwrd03 = 32
FRAME_forwrd04 = 33
FRAME_forwrd05 = 34
FRAME_forwrd06 = 35
FRAME_forwrd07 = 36
FRAME_forwrd08 = 37
FRAME_forwrd09 = 38
FRAME_forwrd10 = 39
FRAME_forwrd11 = 40
FRAME_forwrd12 = 41
FRAME_forwrd13 = 42
FRAME_forwrd14 = 43
FRAME_forwrd15 = 44
FRAME_forwrd16 = 45
FRAME_forwrd17 = 46
FRAME_forwrd18 = 47
FRAME_forwrd19 = 48
FRAME_forwrd20 = 49
FRAME_forwrd21 = 50
FRAME_forwrd22 = 51
FRAME_forwrd23 = 52
FRAME_forwrd24 = 53
FRAME_forwrd25 = 54
FRAME_forwrd26 = 55
FRAME_forwrd27 = 56
FRAME_forwrd28 = 57
FRAME_forwrd29 = 58
FRAME_forwrd30 = 59
FRAME_forwrd31 = 60
FRAME_forwrd32 = 61
FRAME_forwrd33 = 62
FRAME_forwrd34 = 63
FRAME_forwrd35 = 64
FRAME_stop101 = 65
FRAME_stop102 = 66
FRAME_stop103 = 67
FRAME_stop104 = 68
FRAME_stop105 = 69
FRAME_stop106 = 70
FRAME_stop107 = 71
FRAME_stop108 = 72
FRAME_stop109 = 73
FRAME_stop201 = 74
FRAME_stop202 = 75
FRAME_stop203 = 76
FRAME_stop204 = 77
FRAME_stop205 = 78
FRAME_stop206 = 79
FRAME_stop207 = 80
FRAME_stop208 = 81
FRAME_takeof01 = 82
FRAME_takeof02 = 83
FRAME_takeof03 = 84
FRAME_takeof04 = 85
FRAME_takeof05 = 86
FRAME_takeof06 = 87
FRAME_takeof07 = 88
FRAME_takeof08 = 89
FRAME_takeof09 = 90
FRAME_takeof10 = 91
FRAME_takeof11 = 92
FRAME_takeof12 = 93
FRAME_takeof13 = 94
FRAME_takeof14 = 95
FRAME_takeof15 = 96
FRAME_takeof16 = 97
FRAME_takeof17 = 98
FRAME_takeof18 = 99
FRAME_takeof19 = 100
FRAME_takeof20 = 101
FRAME_takeof21 = 102
FRAME_takeof22 = 103
FRAME_takeof23 = 104
FRAME_takeof24 = 105
FRAME_takeof25 = 106
FRAME_takeof26 = 107
FRAME_takeof27 = 108
FRAME_takeof28 = 109
FRAME_takeof29 = 110
FRAME_takeof30 = 111
FRAME_land01 = 112
FRAME_pain101 = 113
FRAME_pain102 = 114
FRAME_pain103 = 115
FRAME_pain104 = 116
FRAME_pain105 = 117
FRAME_pain106 = 118
FRAME_pain107 = 119
FRAME_pain108 = 120
FRAME_pain109 = 121
FRAME_pain110 = 122
FRAME_pain111 = 123
FRAME_pain112 = 124
FRAME_pain113 = 125
FRAME_pain114 = 126
FRAME_pain115 = 127
FRAME_pain116 = 128
FRAME_pain117 = 129
FRAME_pain118 = 130
FRAME_pain119 = 131
FRAME_pain120 = 132
FRAME_pain121 = 133
FRAME_pain122 = 134
FRAME_pain123 = 135
FRAME_pain124 = 136
FRAME_pain125 = 137
FRAME_pain126 = 138
FRAME_pain127 = 139
FRAME_pain128 = 140
FRAME_pain201 = 141
FRAME_pain202 = 142
FRAME_pain203 = 143
FRAME_pain204 = 144
FRAME_pain205 = 145
FRAME_pain206 = 146
FRAME_pain207 = 147
FRAME_pain208 = 148
FRAME_pain209 = 149
FRAME_pain210 = 150
FRAME_pain211 = 151
FRAME_pain212 = 152
FRAME_pain301 = 153
FRAME_pain302 = 154
FRAME_pain303 = 155
FRAME_pain304 = 156
FRAME_pain305 = 157
FRAME_pain306 = 158
FRAME_pain307 = 159
FRAME_pain308 = 160
FRAME_pain309 = 161
FRAME_death101 = 162
FRAME_death102 = 163
FRAME_death103 = 164
FRAME_death104 = 165
FRAME_death105 = 166
FRAME_death106 = 167
FRAME_death107 = 168
FRAME_death108 = 169
FRAME_death109 = 170
FRAME_death110 = 171
FRAME_death111 = 172
FRAME_backwd01 = 173
FRAME_backwd02 = 174
FRAME_backwd03 = 175
FRAME_backwd04 = 176
FRAME_backwd05 = 177
FRAME_backwd06 = 178
FRAME_backwd07 = 179
FRAME_backwd08 = 180
FRAME_backwd09 = 181
FRAME_backwd10 = 182
FRAME_backwd11 = 183
FRAME_backwd12 = 184
FRAME_backwd13 = 185
FRAME_backwd14 = 186
FRAME_backwd15 = 187
FRAME_backwd16 = 188
FRAME_backwd17 = 189
FRAME_backwd18 = 190
FRAME_backwd19 = 191
FRAME_backwd20 = 192
FRAME_backwd21 = 193
FRAME_backwd22 = 194
FRAME_backwd23 = 195
FRAME_backwd24 = 196
FRAME_attak101 = 197
FRAME_attak102 = 198
FRAME_attak103 = 199
FRAME_attak104 = 200
FRAME_attak105 = 201
FRAME_attak106 = 202
FRAME_attak107 = 203
FRAME_attak108 = 204
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

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def hover_search (self): #edict_t *

	if g_local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_search1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_search2, 1, ATTN_NORM, 0)


def hover_reattack (self): #edict_t *

	if self.enemy.health > 0:
		if g_ai.visible (self, self.enemy):
			if g_local.random() <= 0.6:
				self.monsterinfo.currentmove = hover_move_attack1
				return
	self.monsterinfo.currentmove = hover_move_end_attack


def hover_fire_blaster (self): #edict_t *

	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	effect;

	if self.s.frame == FRAME_attak104:
		effect = EF_HYPERBLASTER
	else:
		effect = 0

	q_shared.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[MZ2_HOVER_BLASTER_1], forward, right, start)

	q_shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	q_shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 1, 1000, MZ2_HOVER_BLASTER_1, effect)


def hover_stand (self): #edict_t *

	self.monsterinfo.currentmove = hover_move_stand


def hover_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = hover_move_stand
	else:
		self.monsterinfo.currentmove = hover_move_run


def hover_walk (self): #edict_t *

	self.monsterinfo.currentmove = hover_move_walk


def hover_start_attack (self): #edict_t *

	self.monsterinfo.currentmove = hover_move_start_attack


def hover_attack (self): #edict_t *

	self.monsterinfo.currentmove = hover_move_attack1


def hover_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if damage <= 25:
		if g_local.random() < 0.5:
			g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
			self.monsterinfo.currentmove = hover_move_pain3
		else:
			g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
			self.monsterinfo.currentmove = hover_move_pain2
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = hover_move_pain1


def hover_deadthink (self): #edict_t *

	if not self.groundentity and g_main.level.time < self.timestamp:
		self.nextthink = g_main.level.time + FRAMETIME
		return
	BecomeExplosion1(self)


def hover_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.think = hover_deadthink
	self.nextthink = g_main.level.time + FRAMETIME
	self.timestamp = g_main.level.time + 15
	g_main.gi.linkentity (self)


def hover_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

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
	if g_local.random() < 0.5:
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
	q_shared.VectorSet (self.mins, -24, -24, -24)
	q_shared.VectorSet (self.maxs, 24, 24, 32)

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
	self.monsterinfo.scale = MODEL_SCALE

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
hover_move_stand = _mm(FRAME_stand01, FRAME_stand30, hover_frames_stand, None)

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
hover_move_stop1 = _mm(FRAME_stop101, FRAME_stop109, hover_frames_stop1, None)

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
hover_move_stop2 = _mm(FRAME_stop201, FRAME_stop208, hover_frames_stop2, None)

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
hover_move_takeoff = _mm(FRAME_takeof01, FRAME_takeof30, hover_frames_takeoff, None)

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
hover_move_pain3 = _mm(FRAME_pain301, FRAME_pain309, hover_frames_pain3, hover_run)

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
hover_move_pain2 = _mm(FRAME_pain201, FRAME_pain212, hover_frames_pain2, hover_run)

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
hover_move_pain1 = _mm(FRAME_pain101, FRAME_pain128, hover_frames_pain1, hover_run)

hover_frames_land = [
	_mf(ai_move, 0, None),
]
hover_move_land = _mm(FRAME_land01, FRAME_land01, hover_frames_land, None)

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
hover_move_forward = _mm(FRAME_forwrd01, FRAME_forwrd35, hover_frames_forward, None)

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
hover_move_walk = _mm(FRAME_forwrd01, FRAME_forwrd35, hover_frames_walk, None)

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
hover_move_run = _mm(FRAME_forwrd01, FRAME_forwrd35, hover_frames_run, None)

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
hover_move_death1 = _mm(FRAME_death101, FRAME_death111, hover_frames_death1, hover_dead)

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
hover_move_backward = _mm(FRAME_backwd01, FRAME_backwd24, hover_frames_backward, None)

hover_frames_start_attack = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
]
hover_move_start_attack = _mm(FRAME_attak101, FRAME_attak103, hover_frames_start_attack, hover_attack)

hover_frames_attack1 = [
	_mf(ai_charge, -10, hover_fire_blaster),
	_mf(ai_charge, -10, hover_fire_blaster),
	_mf(ai_charge, 0, hover_reattack),
]
hover_move_attack1 = _mm(FRAME_attak104, FRAME_attak106, hover_frames_attack1, None)

hover_frames_end_attack = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
]
hover_move_end_attack = _mm(FRAME_attak107, FRAME_attak108, hover_frames_end_attack, hover_run)


