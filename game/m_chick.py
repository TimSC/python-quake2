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
from game.g_local import (AI_DUCKED, AI_HOLD_FRAME, AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, RANGE_MELEE, damage_t)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_rocket, walkmonster_start)
from game.g_utils import (G_FreeEdict, G_ProjectSource)
from game.g_weapon import (fire_hit)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_IDLE, ATTN_NORM, CHAN_VOICE, CHAN_WEAPON, MZ2_CHICK_ROCKET_1)
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_chick.h
FRAME_attak101 = 0
FRAME_attak102 = 1
FRAME_attak103 = 2
FRAME_attak104 = 3
FRAME_attak105 = 4
FRAME_attak106 = 5
FRAME_attak107 = 6
FRAME_attak108 = 7
FRAME_attak109 = 8
FRAME_attak110 = 9
FRAME_attak111 = 10
FRAME_attak112 = 11
FRAME_attak113 = 12
FRAME_attak114 = 13
FRAME_attak115 = 14
FRAME_attak116 = 15
FRAME_attak117 = 16
FRAME_attak118 = 17
FRAME_attak119 = 18
FRAME_attak120 = 19
FRAME_attak121 = 20
FRAME_attak122 = 21
FRAME_attak123 = 22
FRAME_attak124 = 23
FRAME_attak125 = 24
FRAME_attak126 = 25
FRAME_attak127 = 26
FRAME_attak128 = 27
FRAME_attak129 = 28
FRAME_attak130 = 29
FRAME_attak131 = 30
FRAME_attak132 = 31
FRAME_attak201 = 32
FRAME_attak202 = 33
FRAME_attak203 = 34
FRAME_attak204 = 35
FRAME_attak205 = 36
FRAME_attak206 = 37
FRAME_attak207 = 38
FRAME_attak208 = 39
FRAME_attak209 = 40
FRAME_attak210 = 41
FRAME_attak211 = 42
FRAME_attak212 = 43
FRAME_attak213 = 44
FRAME_attak214 = 45
FRAME_attak215 = 46
FRAME_attak216 = 47
FRAME_death101 = 48
FRAME_death102 = 49
FRAME_death103 = 50
FRAME_death104 = 51
FRAME_death105 = 52
FRAME_death106 = 53
FRAME_death107 = 54
FRAME_death108 = 55
FRAME_death109 = 56
FRAME_death110 = 57
FRAME_death111 = 58
FRAME_death112 = 59
FRAME_death201 = 60
FRAME_death202 = 61
FRAME_death203 = 62
FRAME_death204 = 63
FRAME_death205 = 64
FRAME_death206 = 65
FRAME_death207 = 66
FRAME_death208 = 67
FRAME_death209 = 68
FRAME_death210 = 69
FRAME_death211 = 70
FRAME_death212 = 71
FRAME_death213 = 72
FRAME_death214 = 73
FRAME_death215 = 74
FRAME_death216 = 75
FRAME_death217 = 76
FRAME_death218 = 77
FRAME_death219 = 78
FRAME_death220 = 79
FRAME_death221 = 80
FRAME_death222 = 81
FRAME_death223 = 82
FRAME_duck01 = 83
FRAME_duck02 = 84
FRAME_duck03 = 85
FRAME_duck04 = 86
FRAME_duck05 = 87
FRAME_duck06 = 88
FRAME_duck07 = 89
FRAME_pain101 = 90
FRAME_pain102 = 91
FRAME_pain103 = 92
FRAME_pain104 = 93
FRAME_pain105 = 94
FRAME_pain201 = 95
FRAME_pain202 = 96
FRAME_pain203 = 97
FRAME_pain204 = 98
FRAME_pain205 = 99
FRAME_pain301 = 100
FRAME_pain302 = 101
FRAME_pain303 = 102
FRAME_pain304 = 103
FRAME_pain305 = 104
FRAME_pain306 = 105
FRAME_pain307 = 106
FRAME_pain308 = 107
FRAME_pain309 = 108
FRAME_pain310 = 109
FRAME_pain311 = 110
FRAME_pain312 = 111
FRAME_pain313 = 112
FRAME_pain314 = 113
FRAME_pain315 = 114
FRAME_pain316 = 115
FRAME_pain317 = 116
FRAME_pain318 = 117
FRAME_pain319 = 118
FRAME_pain320 = 119
FRAME_pain321 = 120
FRAME_stand101 = 121
FRAME_stand102 = 122
FRAME_stand103 = 123
FRAME_stand104 = 124
FRAME_stand105 = 125
FRAME_stand106 = 126
FRAME_stand107 = 127
FRAME_stand108 = 128
FRAME_stand109 = 129
FRAME_stand110 = 130
FRAME_stand111 = 131
FRAME_stand112 = 132
FRAME_stand113 = 133
FRAME_stand114 = 134
FRAME_stand115 = 135
FRAME_stand116 = 136
FRAME_stand117 = 137
FRAME_stand118 = 138
FRAME_stand119 = 139
FRAME_stand120 = 140
FRAME_stand121 = 141
FRAME_stand122 = 142
FRAME_stand123 = 143
FRAME_stand124 = 144
FRAME_stand125 = 145
FRAME_stand126 = 146
FRAME_stand127 = 147
FRAME_stand128 = 148
FRAME_stand129 = 149
FRAME_stand130 = 150
FRAME_stand201 = 151
FRAME_stand202 = 152
FRAME_stand203 = 153
FRAME_stand204 = 154
FRAME_stand205 = 155
FRAME_stand206 = 156
FRAME_stand207 = 157
FRAME_stand208 = 158
FRAME_stand209 = 159
FRAME_stand210 = 160
FRAME_stand211 = 161
FRAME_stand212 = 162
FRAME_stand213 = 163
FRAME_stand214 = 164
FRAME_stand215 = 165
FRAME_stand216 = 166
FRAME_stand217 = 167
FRAME_stand218 = 168
FRAME_stand219 = 169
FRAME_stand220 = 170
FRAME_stand221 = 171
FRAME_stand222 = 172
FRAME_stand223 = 173
FRAME_stand224 = 174
FRAME_stand225 = 175
FRAME_stand226 = 176
FRAME_stand227 = 177
FRAME_stand228 = 178
FRAME_stand229 = 179
FRAME_stand230 = 180
FRAME_walk01 = 181
FRAME_walk02 = 182
FRAME_walk03 = 183
FRAME_walk04 = 184
FRAME_walk05 = 185
FRAME_walk06 = 186
FRAME_walk07 = 187
FRAME_walk08 = 188
FRAME_walk09 = 189
FRAME_walk10 = 190
FRAME_walk11 = 191
FRAME_walk12 = 192
FRAME_walk13 = 193
FRAME_walk14 = 194
FRAME_walk15 = 195
FRAME_walk16 = 196
FRAME_walk17 = 197
FRAME_walk18 = 198
FRAME_walk19 = 199
FRAME_walk20 = 200
FRAME_walk21 = 201
FRAME_walk22 = 202
FRAME_walk23 = 203
FRAME_walk24 = 204
FRAME_walk25 = 205
FRAME_walk26 = 206
FRAME_walk27 = 207
FRAME_recln201 = 208
FRAME_recln202 = 209
FRAME_recln203 = 210
FRAME_recln204 = 211
FRAME_recln205 = 212
FRAME_recln206 = 213
FRAME_recln207 = 214
FRAME_recln208 = 215
FRAME_recln209 = 216
FRAME_recln210 = 217
FRAME_recln211 = 218
FRAME_recln212 = 219
FRAME_recln213 = 220
FRAME_recln214 = 221
FRAME_recln215 = 222
FRAME_recln216 = 223
FRAME_recln217 = 224
FRAME_recln218 = 225
FRAME_recln219 = 226
FRAME_recln220 = 227
FRAME_recln221 = 228
FRAME_recln222 = 229
FRAME_recln223 = 230
FRAME_recln224 = 231
FRAME_recln225 = 232
FRAME_recln226 = 233
FRAME_recln227 = 234
FRAME_recln228 = 235
FRAME_recln229 = 236
FRAME_recln230 = 237
FRAME_recln231 = 238
FRAME_recln232 = 239
FRAME_recln233 = 240
FRAME_recln234 = 241
FRAME_recln235 = 242
FRAME_recln236 = 243
FRAME_recln237 = 244
FRAME_recln238 = 245
FRAME_recln239 = 246
FRAME_recln240 = 247
FRAME_recln101 = 248
FRAME_recln102 = 249
FRAME_recln103 = 250
FRAME_recln104 = 251
FRAME_recln105 = 252
FRAME_recln106 = 253
FRAME_recln107 = 254
FRAME_recln108 = 255
FRAME_recln109 = 256
FRAME_recln110 = 257
FRAME_recln111 = 258
FRAME_recln112 = 259
FRAME_recln113 = 260
FRAME_recln114 = 261
FRAME_recln115 = 262
FRAME_recln116 = 263
FRAME_recln117 = 264
FRAME_recln118 = 265
FRAME_recln119 = 266
FRAME_recln120 = 267
FRAME_recln121 = 268
FRAME_recln122 = 269
FRAME_recln123 = 270
FRAME_recln124 = 271
FRAME_recln125 = 272
FRAME_recln126 = 273
FRAME_recln127 = 274
FRAME_recln128 = 275
FRAME_recln129 = 276
FRAME_recln130 = 277
FRAME_recln131 = 278
FRAME_recln132 = 279
FRAME_recln133 = 280
FRAME_recln134 = 281
FRAME_recln135 = 282
FRAME_recln136 = 283
FRAME_recln137 = 284
FRAME_recln138 = 285
FRAME_recln139 = 286
FRAME_recln140 = 287
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

sound_missile_prelaunch = 0 # static
sound_missile_launch = 0 # static
sound_melee_swing = 0 # static
sound_melee_hit = 0 # static
sound_missile_reload = 0 # static
sound_death1 = 0 # static
sound_death2 = 0 # static
sound_fall_down = 0 # static
sound_idle1 = 0 # static
sound_idle2 = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_pain3 = 0 # static
sound_sight = 0 # static
sound_search = 0 # static


"""
==============================================================================

chick

==============================================================================
"""
def ChickMoan (self): #edict_t *

	if g_local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_idle1, 1, ATTN_IDLE, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_idle2, 1, ATTN_IDLE, 0)


def chick_fidget (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		return
	if g_local.random() <= 0.3:
		self.monsterinfo.currentmove = chick_move_fidget


def chick_stand (self): #edict_t *

	self.monsterinfo.currentmove = chick_move_stand


def chick_walk (self): #edict_t *

	self.monsterinfo.currentmove = chick_move_walk


def chick_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = chick_move_stand
		return

	if self.monsterinfo.currentmove == chick_move_walk or self.monsterinfo.currentmove == chick_move_start_run:
		self.monsterinfo.currentmove = chick_move_run
	else:
		self.monsterinfo.currentmove = chick_move_start_run


def chick_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	#float	r;

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	r = g_local.random()
	if r < 0.33:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
	elif r < 0.66:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain3, 1, ATTN_NORM, 0)

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if damage <= 10:
		self.monsterinfo.currentmove = chick_move_pain1
	elif damage <= 25:
		self.monsterinfo.currentmove = chick_move_pain2
	else:
		self.monsterinfo.currentmove = chick_move_pain3


def chick_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, 0)
	q_shared.VectorSet (self.maxs, 16, 16, 16)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def chick_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# check for gib
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
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	n = _r.randint(0, 2147483647) % 2
	if n == 0:
		self.monsterinfo.currentmove = chick_move_death1
		g_main.gi.sound (self, CHAN_VOICE, sound_death1, 1, ATTN_NORM, 0)
	else:
		self.monsterinfo.currentmove = chick_move_death2
		g_main.gi.sound (self, CHAN_VOICE, sound_death2, 1, ATTN_NORM, 0)


def chick_duck_down (self): #edict_t *

	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity (self)


def chick_duck_hold (self): #edict_t *

	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME


def chick_duck_up (self): #edict_t *

	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)


def chick_dodge (self, attacker, eta): #edict_t *, edict_t *, float

	if g_local.random() > 0.25:
		return

	if not self.enemy:
		self.enemy = attacker

	self.monsterinfo.currentmove = chick_move_duck


def ChickSlash (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSet (aim, MELEE_DISTANCE, self.mins[0], 10)
	g_main.gi.sound (self, CHAN_WEAPON, sound_melee_swing, 1, ATTN_NORM, 0)
	fire_hit (self, aim, (10 + (_r.randint(0, 2147483647) %6)), 100)


def ChickRocket (self): #edict_t *

	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[MZ2_CHICK_ROCKET_1], forward, right, start)

	q_shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	q_shared.VectorSubtract (vec, start, dir)
	q_shared.VectorNormalize (dir)

	monster_fire_rocket (self, start, dir, 50, 500, MZ2_CHICK_ROCKET_1)


def Chick_PreAttack1 (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_missile_prelaunch, 1, ATTN_NORM, 0)


def ChickReload (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_missile_reload, 1, ATTN_NORM, 0)


def chick_rerocket (self): #edict_t *

	if self.enemy.health > 0:
		if g_ai.range (self, self.enemy) > RANGE_MELEE:
			if g_ai.visible (self, self.enemy):
				if g_local.random() <= 0.6:
					self.monsterinfo.currentmove = chick_move_attack1
					return
	self.monsterinfo.currentmove = chick_move_end_attack1


def chick_attack1 (self): #edict_t *

	self.monsterinfo.currentmove = chick_move_attack1


def chick_reslash (self): #edict_t *

	if self.enemy.health > 0:
		if g_ai.range (self, self.enemy) == RANGE_MELEE:
			if g_local.random() <= 0.9:
				self.monsterinfo.currentmove = chick_move_slash
				return
			else:
				self.monsterinfo.currentmove = chick_move_end_slash
				return
	self.monsterinfo.currentmove = chick_move_end_slash


def chick_slash (self): #edict_t *

	self.monsterinfo.currentmove = chick_move_slash


def chick_melee (self): #edict_t *

	self.monsterinfo.currentmove = chick_move_start_slash


def chick_attack (self): #edict_t *

	self.monsterinfo.currentmove = chick_move_start_attack1


def chick_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


"""QUAKED monster_chick (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_chick (self): #edict_t *

	global sound_missile_prelaunch, sound_missile_launch, sound_melee_swing, sound_melee_hit, sound_missile_reload, sound_death1, sound_death2, sound_fall_down, sound_idle1, sound_idle2, sound_pain1, sound_pain2, sound_pain3, sound_sight, sound_search
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_missile_prelaunch = g_main.gi.soundindex ("chick/chkatck1.wav")
	sound_missile_launch = g_main.gi.soundindex ("chick/chkatck2.wav")
	sound_melee_swing = g_main.gi.soundindex ("chick/chkatck3.wav")
	sound_melee_hit = g_main.gi.soundindex ("chick/chkatck4.wav")
	sound_missile_reload = g_main.gi.soundindex ("chick/chkatck5.wav")
	sound_death1 = g_main.gi.soundindex ("chick/chkdeth1.wav")
	sound_death2 = g_main.gi.soundindex ("chick/chkdeth2.wav")
	sound_fall_down = g_main.gi.soundindex ("chick/chkfall1.wav")
	sound_idle1 = g_main.gi.soundindex ("chick/chkidle1.wav")
	sound_idle2 = g_main.gi.soundindex ("chick/chkidle2.wav")
	sound_pain1 = g_main.gi.soundindex ("chick/chkpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("chick/chkpain2.wav")
	sound_pain3 = g_main.gi.soundindex ("chick/chkpain3.wav")
	sound_sight = g_main.gi.soundindex ("chick/chksght1.wav")
	sound_search = g_main.gi.soundindex ("chick/chksrch1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/bitch/tris.md2")
	q_shared.VectorSet (self.mins, -16, -16, 0)
	q_shared.VectorSet (self.maxs, 16, 16, 56)

	self.health = 175
	self.gib_health = -70
	self.mass = 200

	self.pain = chick_pain
	self.die = chick_die

	self.monsterinfo.stand = chick_stand
	self.monsterinfo.walk = chick_walk
	self.monsterinfo.run = chick_run
	self.monsterinfo.dodge = chick_dodge
	self.monsterinfo.attack = chick_attack
	self.monsterinfo.melee = chick_melee
	self.monsterinfo.sight = chick_sight

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = chick_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start (self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
chick_frames_fidget = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, ChickMoan),
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
chick_move_fidget = _mm(FRAME_stand201, FRAME_stand230, chick_frames_fidget, chick_stand)

chick_frames_stand = [
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
	_mf(ai_stand, 0, chick_fidget),
]
chick_move_stand = _mm(FRAME_stand101, FRAME_stand130, chick_frames_stand, None)

chick_frames_start_run = [
	_mf(ai_run, 1, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, -1, None),
	_mf(ai_run, -1, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 1, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 3, None),
]
chick_move_start_run = _mm(FRAME_walk01, FRAME_walk10, chick_frames_start_run, chick_run)

chick_frames_run = [
	_mf(ai_run, 6, None),
	_mf(ai_run, 8, None),
	_mf(ai_run, 13, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 7, None),
	_mf(ai_run, 4, None),
	_mf(ai_run, 11, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 9, None),
	_mf(ai_run, 7, None),
]
chick_move_run = _mm(FRAME_walk11, FRAME_walk20, chick_frames_run, None)

chick_frames_walk = [
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 8, None),
	_mf(ai_walk, 13, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 11, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 9, None),
	_mf(ai_walk, 7, None),
]
chick_move_walk = _mm(FRAME_walk11, FRAME_walk20, chick_frames_walk, None)

chick_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
chick_move_pain1 = _mm(FRAME_pain101, FRAME_pain105, chick_frames_pain1, chick_run)

chick_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
chick_move_pain2 = _mm(FRAME_pain201, FRAME_pain205, chick_frames_pain2, chick_run)

chick_frames_pain3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 11, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 4, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, 7, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -8, None),
	_mf(ai_move, 2, None),
]
chick_move_pain3 = _mm(FRAME_pain301, FRAME_pain321, chick_frames_pain3, chick_run)

chick_frames_death2 = [
	_mf(ai_move, -6, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 10, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, 4, None),
	_mf(ai_move, 15, None),
	_mf(ai_move, 14, None),
	_mf(ai_move, 1, None),
]
chick_move_death2 = _mm(FRAME_death201, FRAME_death223, chick_frames_death2, chick_dead)

chick_frames_death1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, 4, None),
	_mf(ai_move, 11, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
chick_move_death1 = _mm(FRAME_death101, FRAME_death112, chick_frames_death1, chick_dead)

chick_frames_duck = [
	_mf(ai_move, 0, chick_duck_down),
	_mf(ai_move, 1, None),
	_mf(ai_move, 4, chick_duck_hold),
	_mf(ai_move, -4, None),
	_mf(ai_move, -5, chick_duck_up),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
]
chick_move_duck = _mm(FRAME_duck01, FRAME_duck07, chick_frames_duck, chick_run)

chick_frames_start_attack1 = [
	_mf(ai_charge, 0, Chick_PreAttack1),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 5, None),
	_mf(ai_charge, 7, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, chick_attack1),
]
chick_move_start_attack1 = _mm(FRAME_attak101, FRAME_attak113, chick_frames_start_attack1, None)

chick_frames_attack1 = [
	_mf(ai_charge, 19, ChickRocket),
	_mf(ai_charge, -6, None),
	_mf(ai_charge, -5, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -7, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 10, ChickReload),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 5, None),
	_mf(ai_charge, 6, None),
	_mf(ai_charge, 6, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 3, chick_rerocket),
]
chick_move_attack1 = _mm(FRAME_attak114, FRAME_attak127, chick_frames_attack1, None)

chick_frames_end_attack1 = [
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -6, None),
	_mf(ai_charge, -4, None),
	_mf(ai_charge, -2, None),
]
chick_move_end_attack1 = _mm(FRAME_attak128, FRAME_attak132, chick_frames_end_attack1, chick_run)

chick_frames_slash = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 7, ChickSlash),
	_mf(ai_charge, -7, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, -2, chick_reslash),
]
chick_move_slash = _mm(FRAME_attak204, FRAME_attak212, chick_frames_slash, None)

chick_frames_end_slash = [
	_mf(ai_charge, -6, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -6, None),
	_mf(ai_charge, 0, None),
]
chick_move_end_slash = _mm(FRAME_attak213, FRAME_attak216, chick_frames_end_slash, chick_run)

chick_frames_start_slash = [
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 8, None),
	_mf(ai_charge, 3, None),
]
chick_move_start_slash = _mm(FRAME_attak201, FRAME_attak203, chick_frames_start_slash, chick_slash)


