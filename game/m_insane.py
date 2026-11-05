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
from game import g_main, g_local
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_local import (AI_GOOD_GUY, AI_STAND_GROUND, DEAD_DEAD, FL_FLY, FL_NO_KNOCKBACK, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (flymonster_start, walkmonster_start)
from game.g_utils import (G_FreeEdict)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from common.header.shared import ATTN_IDLE, CHAN_VOICE
from common.header import shared
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_insane.h
FRAME_stand1 = 0
FRAME_stand2 = 1
FRAME_stand3 = 2
FRAME_stand4 = 3
FRAME_stand5 = 4
FRAME_stand6 = 5
FRAME_stand7 = 6
FRAME_stand8 = 7
FRAME_stand9 = 8
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
FRAME_stand31 = 30
FRAME_stand32 = 31
FRAME_stand33 = 32
FRAME_stand34 = 33
FRAME_stand35 = 34
FRAME_stand36 = 35
FRAME_stand37 = 36
FRAME_stand38 = 37
FRAME_stand39 = 38
FRAME_stand40 = 39
FRAME_stand41 = 40
FRAME_stand42 = 41
FRAME_stand43 = 42
FRAME_stand44 = 43
FRAME_stand45 = 44
FRAME_stand46 = 45
FRAME_stand47 = 46
FRAME_stand48 = 47
FRAME_stand49 = 48
FRAME_stand50 = 49
FRAME_stand51 = 50
FRAME_stand52 = 51
FRAME_stand53 = 52
FRAME_stand54 = 53
FRAME_stand55 = 54
FRAME_stand56 = 55
FRAME_stand57 = 56
FRAME_stand58 = 57
FRAME_stand59 = 58
FRAME_stand60 = 59
FRAME_stand61 = 60
FRAME_stand62 = 61
FRAME_stand63 = 62
FRAME_stand64 = 63
FRAME_stand65 = 64
FRAME_stand66 = 65
FRAME_stand67 = 66
FRAME_stand68 = 67
FRAME_stand69 = 68
FRAME_stand70 = 69
FRAME_stand71 = 70
FRAME_stand72 = 71
FRAME_stand73 = 72
FRAME_stand74 = 73
FRAME_stand75 = 74
FRAME_stand76 = 75
FRAME_stand77 = 76
FRAME_stand78 = 77
FRAME_stand79 = 78
FRAME_stand80 = 79
FRAME_stand81 = 80
FRAME_stand82 = 81
FRAME_stand83 = 82
FRAME_stand84 = 83
FRAME_stand85 = 84
FRAME_stand86 = 85
FRAME_stand87 = 86
FRAME_stand88 = 87
FRAME_stand89 = 88
FRAME_stand90 = 89
FRAME_stand91 = 90
FRAME_stand92 = 91
FRAME_stand93 = 92
FRAME_stand94 = 93
FRAME_stand95 = 94
FRAME_stand96 = 95
FRAME_stand97 = 96
FRAME_stand98 = 97
FRAME_stand99 = 98
FRAME_stand100 = 99
FRAME_stand101 = 100
FRAME_stand102 = 101
FRAME_stand103 = 102
FRAME_stand104 = 103
FRAME_stand105 = 104
FRAME_stand106 = 105
FRAME_stand107 = 106
FRAME_stand108 = 107
FRAME_stand109 = 108
FRAME_stand110 = 109
FRAME_stand111 = 110
FRAME_stand112 = 111
FRAME_stand113 = 112
FRAME_stand114 = 113
FRAME_stand115 = 114
FRAME_stand116 = 115
FRAME_stand117 = 116
FRAME_stand118 = 117
FRAME_stand119 = 118
FRAME_stand120 = 119
FRAME_stand121 = 120
FRAME_stand122 = 121
FRAME_stand123 = 122
FRAME_stand124 = 123
FRAME_stand125 = 124
FRAME_stand126 = 125
FRAME_stand127 = 126
FRAME_stand128 = 127
FRAME_stand129 = 128
FRAME_stand130 = 129
FRAME_stand131 = 130
FRAME_stand132 = 131
FRAME_stand133 = 132
FRAME_stand134 = 133
FRAME_stand135 = 134
FRAME_stand136 = 135
FRAME_stand137 = 136
FRAME_stand138 = 137
FRAME_stand139 = 138
FRAME_stand140 = 139
FRAME_stand141 = 140
FRAME_stand142 = 141
FRAME_stand143 = 142
FRAME_stand144 = 143
FRAME_stand145 = 144
FRAME_stand146 = 145
FRAME_stand147 = 146
FRAME_stand148 = 147
FRAME_stand149 = 148
FRAME_stand150 = 149
FRAME_stand151 = 150
FRAME_stand152 = 151
FRAME_stand153 = 152
FRAME_stand154 = 153
FRAME_stand155 = 154
FRAME_stand156 = 155
FRAME_stand157 = 156
FRAME_stand158 = 157
FRAME_stand159 = 158
FRAME_stand160 = 159
FRAME_walk27 = 160
FRAME_walk28 = 161
FRAME_walk29 = 162
FRAME_walk30 = 163
FRAME_walk31 = 164
FRAME_walk32 = 165
FRAME_walk33 = 166
FRAME_walk34 = 167
FRAME_walk35 = 168
FRAME_walk36 = 169
FRAME_walk37 = 170
FRAME_walk38 = 171
FRAME_walk39 = 172
FRAME_walk1 = 173
FRAME_walk2 = 174
FRAME_walk3 = 175
FRAME_walk4 = 176
FRAME_walk5 = 177
FRAME_walk6 = 178
FRAME_walk7 = 179
FRAME_walk8 = 180
FRAME_walk9 = 181
FRAME_walk10 = 182
FRAME_walk11 = 183
FRAME_walk12 = 184
FRAME_walk13 = 185
FRAME_walk14 = 186
FRAME_walk15 = 187
FRAME_walk16 = 188
FRAME_walk17 = 189
FRAME_walk18 = 190
FRAME_walk19 = 191
FRAME_walk20 = 192
FRAME_walk21 = 193
FRAME_walk22 = 194
FRAME_walk23 = 195
FRAME_walk24 = 196
FRAME_walk25 = 197
FRAME_walk26 = 198
FRAME_st_pain2 = 199
FRAME_st_pain3 = 200
FRAME_st_pain4 = 201
FRAME_st_pain5 = 202
FRAME_st_pain6 = 203
FRAME_st_pain7 = 204
FRAME_st_pain8 = 205
FRAME_st_pain9 = 206
FRAME_st_pain10 = 207
FRAME_st_pain11 = 208
FRAME_st_pain12 = 209
FRAME_st_death2 = 210
FRAME_st_death3 = 211
FRAME_st_death4 = 212
FRAME_st_death5 = 213
FRAME_st_death6 = 214
FRAME_st_death7 = 215
FRAME_st_death8 = 216
FRAME_st_death9 = 217
FRAME_st_death10 = 218
FRAME_st_death11 = 219
FRAME_st_death12 = 220
FRAME_st_death13 = 221
FRAME_st_death14 = 222
FRAME_st_death15 = 223
FRAME_st_death16 = 224
FRAME_st_death17 = 225
FRAME_st_death18 = 226
FRAME_crawl1 = 227
FRAME_crawl2 = 228
FRAME_crawl3 = 229
FRAME_crawl4 = 230
FRAME_crawl5 = 231
FRAME_crawl6 = 232
FRAME_crawl7 = 233
FRAME_crawl8 = 234
FRAME_crawl9 = 235
FRAME_cr_pain2 = 236
FRAME_cr_pain3 = 237
FRAME_cr_pain4 = 238
FRAME_cr_pain5 = 239
FRAME_cr_pain6 = 240
FRAME_cr_pain7 = 241
FRAME_cr_pain8 = 242
FRAME_cr_pain9 = 243
FRAME_cr_pain10 = 244
FRAME_cr_death10 = 245
FRAME_cr_death11 = 246
FRAME_cr_death12 = 247
FRAME_cr_death13 = 248
FRAME_cr_death14 = 249
FRAME_cr_death15 = 250
FRAME_cr_death16 = 251
FRAME_cross1 = 252
FRAME_cross2 = 253
FRAME_cross3 = 254
FRAME_cross4 = 255
FRAME_cross5 = 256
FRAME_cross6 = 257
FRAME_cross7 = 258
FRAME_cross8 = 259
FRAME_cross9 = 260
FRAME_cross10 = 261
FRAME_cross11 = 262
FRAME_cross12 = 263
FRAME_cross13 = 264
FRAME_cross14 = 265
FRAME_cross15 = 266
FRAME_cross16 = 267
FRAME_cross17 = 268
FRAME_cross18 = 269
FRAME_cross19 = 270
FRAME_cross20 = 271
FRAME_cross21 = 272
FRAME_cross22 = 273
FRAME_cross23 = 274
FRAME_cross24 = 275
FRAME_cross25 = 276
FRAME_cross26 = 277
FRAME_cross27 = 278
FRAME_cross28 = 279
FRAME_cross29 = 280
FRAME_cross30 = 281
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

	g_main.gi.sound (self, CHAN_VOICE, sound_fist, 1, ATTN_IDLE, 0)


def insane_shake (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_shake, 1, ATTN_IDLE, 0)


def insane_moan (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_moan, 1, ATTN_IDLE, 0)


def insane_scream (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_scream[_r.randint(0, 2147483647)%8], 1, ATTN_IDLE, 0)


def insane_cross (self): #edict_t *

	if g_local.random() < 0.8:
		self.monsterinfo.currentmove = insane_move_cross
	else:
		self.monsterinfo.currentmove = insane_move_struggle_cross


def insane_walk (self): #edict_t *

	if self.spawnflags & 16:
		# Hold Ground?
		if self.s.frame == FRAME_cr_pain10:
			self.monsterinfo.currentmove = insane_move_down
			return
	if self.spawnflags & 4:
		self.monsterinfo.currentmove = insane_move_crawl
	elif g_local.random() <= 0.5:
		self.monsterinfo.currentmove = insane_move_walk_normal
	else:
		self.monsterinfo.currentmove = insane_move_walk_insane


def insane_run (self): #edict_t *

	if self.spawnflags & 16:
		# Hold Ground?
		if self.s.frame == FRAME_cr_pain10:
			self.monsterinfo.currentmove = insane_move_down
			return
	if self.spawnflags & 4:
		# Crawling?
		self.monsterinfo.currentmove = insane_move_runcrawl
	elif g_local.random() <= 0.5:
		# Else, mix it up
		self.monsterinfo.currentmove = insane_move_run_normal
	else:
		self.monsterinfo.currentmove = insane_move_run_insane


def insane_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	#int	l;
	#int	r;

	# if (self->health < (self->max_health / 2))
	# self->s.skinnum = 1;

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	r = 1 + (_r.randint(0, 2147483647)&1)
	if self.health < 25:
		l = 25
	elif self.health < 50:
		l = 50
	elif self.health < 75:
		l = 75
	else:
		l = 100
	g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("player/male/pain%i_%i.wav" % (l, r)), 1, ATTN_IDLE, 0)

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	# Don't go into pain frames if crucified.
	if self.spawnflags & 8:
		self.monsterinfo.currentmove = insane_move_struggle_cross
		return

	if ((self.s.frame >= FRAME_crawl1) and (self.s.frame <= FRAME_crawl9)) or ((self.s.frame >= FRAME_stand99) and (self.s.frame <= FRAME_stand160)):
		self.monsterinfo.currentmove = insane_move_crawl_pain
	else:
		self.monsterinfo.currentmove = insane_move_stand_pain


def insane_onground (self): #edict_t *

	self.monsterinfo.currentmove = insane_move_down


def insane_checkdown (self): #edict_t *

	# if ( (self->s.frame == FRAME_stand94) || (self->s.frame == FRAME_stand65) )
	if self.spawnflags & 32:
		# Always stand
		return
	if g_local.random() < 0.3:
		if g_local.random() < 0.5:
			self.monsterinfo.currentmove = insane_move_uptodown
		else:
			self.monsterinfo.currentmove = insane_move_jumpdown


def insane_checkup (self): #edict_t *

	# If Hold_Ground and Crawl are set
	if (self.spawnflags & 4) and (self.spawnflags & 16):
		return
	if g_local.random() < 0.5:
		self.monsterinfo.currentmove = insane_move_downtoup


def insane_stand (self): #edict_t *

	if self.spawnflags & 8:
		# If crucified
		self.monsterinfo.currentmove = insane_move_cross
		self.monsterinfo.aiflags |= AI_STAND_GROUND
	# If Hold_Ground and Crawl are set
	elif (self.spawnflags & 4) and (self.spawnflags & 16):
		self.monsterinfo.currentmove = insane_move_down
	elif g_local.random() < 0.5:
		self.monsterinfo.currentmove = insane_move_stand_normal
	else:
		self.monsterinfo.currentmove = insane_move_stand_insane


def insane_dead (self): #edict_t *

	if self.spawnflags & 8:
		self.flags |= FL_FLY
	else:
		shared.VectorSet (self.mins, -16, -16, -24)
		shared.VectorSet (self.maxs, 16, 16, -8)
		self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def insane_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_IDLE, 0)
		for n in range(0, 2):
			ThrowGib (self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)
		for n in range(0, 4):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex("player/male/death%i.wav" % ((_r.randint(0, 2147483647)%4)+1)), 1, ATTN_IDLE, 0)

	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	if self.spawnflags & 8:
		insane_dead (self)
	else:
		if ((self.s.frame >= FRAME_crawl1) and (self.s.frame <= FRAME_crawl9)) or ((self.s.frame >= FRAME_stand99) and (self.s.frame <= FRAME_stand160)):
			self.monsterinfo.currentmove = insane_move_crawl_death
		else:
			self.monsterinfo.currentmove = insane_move_stand_death


"""QUAKED misc_insane (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn CRAWL CRUCIFIED STAND_GROUND ALWAYS_STAND
"""
def SP_misc_insane (self): #edict_t *

	global sound_fist, sound_shake, sound_moan
	# static int skin = 0;	//@@

	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_fist = g_main.gi.soundindex ("insane/insane11.wav")
	sound_shake = g_main.gi.soundindex ("insane/insane5.wav")
	sound_moan = g_main.gi.soundindex ("insane/insane7.wav")
	sound_scream[0] = g_main.gi.soundindex ("insane/insane1.wav")
	sound_scream[1] = g_main.gi.soundindex ("insane/insane2.wav")
	sound_scream[2] = g_main.gi.soundindex ("insane/insane3.wav")
	sound_scream[3] = g_main.gi.soundindex ("insane/insane4.wav")
	sound_scream[4] = g_main.gi.soundindex ("insane/insane6.wav")
	sound_scream[5] = g_main.gi.soundindex ("insane/insane8.wav")
	sound_scream[6] = g_main.gi.soundindex ("insane/insane9.wav")
	sound_scream[7] = g_main.gi.soundindex ("insane/insane10.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/insane/tris.md2")

	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, 32)

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

	# @@
	# self->s.skinnum = skin;
	# skin++;
	# if (skin > 12)
	# skin = 0;

	g_main.gi.linkentity (self)

	if self.spawnflags & 16:
		# Stand Ground
		self.monsterinfo.aiflags |= AI_STAND_GROUND

	self.monsterinfo.currentmove = insane_move_stand_normal

	self.monsterinfo.scale = MODEL_SCALE

	if self.spawnflags & 8:
		# Crucified ?
		shared.VectorSet (self.mins, -16, 0, 0)
		shared.VectorSet (self.maxs, 16, 8, 32)
		self.flags |= FL_NO_KNOCKBACK
		flymonster_start (self)
	else:
		walkmonster_start (self)
		self.s.skinnum = _r.randint(0, 2147483647)%3



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
insane_move_stand_normal = _mm(FRAME_stand60, FRAME_stand65, insane_frames_stand_normal, insane_stand)

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
insane_move_stand_insane = _mm(FRAME_stand65, FRAME_stand94, insane_frames_stand_insane, insane_stand)

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
insane_move_uptodown = _mm(FRAME_stand1, FRAME_stand40, insane_frames_uptodown, insane_onground)

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
insane_move_downtoup = _mm(FRAME_stand41, FRAME_stand59, insane_frames_downtoup, insane_stand)

insane_frames_jumpdown = [
	_mf(ai_move, 0.2, None),
	_mf(ai_move, 11.5, None),
	_mf(ai_move, 5.1, None),
	_mf(ai_move, 7.1, None),
	_mf(ai_move, 0, None),
]
insane_move_jumpdown = _mm(FRAME_stand96, FRAME_stand100, insane_frames_jumpdown, insane_onground)

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
insane_move_down = _mm(FRAME_stand100, FRAME_stand160, insane_frames_down, insane_onground)

insane_frames_walk_normal = [
	_mf(ai_walk, 0, insane_scream),
	_mf(ai_walk, 2.5, None),
	_mf(ai_walk, 3.5, None),
	_mf(ai_walk, 1.7, None),
	_mf(ai_walk, 2.3, None),
	_mf(ai_walk, 2.4, None),
	_mf(ai_walk, 2.2, None),
	_mf(ai_walk, 4.2, None),
	_mf(ai_walk, 5.6, None),
	_mf(ai_walk, 3.3, None),
	_mf(ai_walk, 2.4, None),
	_mf(ai_walk, 0.9, None),
	_mf(ai_walk, 0, None),
]
insane_move_walk_normal = _mm(FRAME_walk27, FRAME_walk39, insane_frames_walk_normal, insane_walk)

insane_move_run_normal = _mm(FRAME_walk27, FRAME_walk39, insane_frames_walk_normal, insane_run)

insane_frames_walk_insane = [
	_mf(ai_walk, 0, insane_scream),	# walk 1
	_mf(ai_walk, 3.4, None),	# walk 2
	_mf(ai_walk, 3.6, None),	# 3
	_mf(ai_walk, 2.9, None),	# 4
	_mf(ai_walk, 2.2, None),	# 5
	_mf(ai_walk, 2.6, None),	# 6
	_mf(ai_walk, 0, None),	# 7
	_mf(ai_walk, 0.7, None),	# 8
	_mf(ai_walk, 4.8, None),	# 9
	_mf(ai_walk, 5.3, None),	# 10
	_mf(ai_walk, 1.1, None),	# 11
	_mf(ai_walk, 2, None),	# 12
	_mf(ai_walk, 0.5, None),	# 13
	_mf(ai_walk, 0, None),	# 14
	_mf(ai_walk, 0, None),	# 15
	_mf(ai_walk, 4.9, None),	# 16
	_mf(ai_walk, 6.7, None),	# 17
	_mf(ai_walk, 3.8, None),	# 18
	_mf(ai_walk, 2, None),	# 19
	_mf(ai_walk, 0.2, None),	# 20
	_mf(ai_walk, 0, None),	# 21
	_mf(ai_walk, 3.4, None),	# 22
	_mf(ai_walk, 6.4, None),	# 23
	_mf(ai_walk, 5, None),	# 24
	_mf(ai_walk, 1.8, None),	# 25
	_mf(ai_walk, 0, None),	# 26
]
insane_move_walk_insane = _mm(FRAME_walk1, FRAME_walk26, insane_frames_walk_insane, insane_walk)

insane_move_run_insane = _mm(FRAME_walk1, FRAME_walk26, insane_frames_walk_insane, insane_run)

insane_frames_stand_pain = [
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
insane_move_stand_pain = _mm(FRAME_st_pain2, FRAME_st_pain12, insane_frames_stand_pain, insane_run)

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
insane_move_stand_death = _mm(FRAME_st_death2, FRAME_st_death18, insane_frames_stand_death, insane_dead)

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
insane_move_crawl = _mm(FRAME_crawl1, FRAME_crawl9, insane_frames_crawl, None)

insane_move_runcrawl = _mm(FRAME_crawl1, FRAME_crawl9, insane_frames_crawl, None)

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
insane_move_crawl_pain = _mm(FRAME_cr_pain2, FRAME_cr_pain10, insane_frames_crawl_pain, insane_run)

insane_frames_crawl_death = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
insane_move_crawl_death = _mm(FRAME_cr_death10, FRAME_cr_death16, insane_frames_crawl_death, insane_dead)

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
insane_move_cross = _mm(FRAME_cross1, FRAME_cross15, insane_frames_cross, insane_cross)

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
insane_move_struggle_cross = _mm(FRAME_cross16, FRAME_cross30, insane_frames_struggle_cross, insane_cross)


