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
from game.g_combat import (T_Damage)
from game.g_local import (AI_STAND_GROUND, DAMAGE_ENERGY, MELEE_DISTANCE, MOD_UNKNOWN, MOVETYPE_STEP, MOVETYPE_TOSS, svc_temp_entity)
from game.g_misc import (BecomeExplosion1)
from game.g_monster import (flymonster_start, monster_fire_blaster)
from game.g_utils import (G_FreeEdict, G_ProjectSource)
from game.g_weapon import (fire_hit)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_IDLE, ATTN_NORM, CHAN_VOICE, CHAN_WEAPON, EF_HYPERBLASTER, MZ2_FLOAT_BLASTER_1, multicast_t, temp_event_t, vec3_origin)
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_SPLASH = temp_event_t.TE_SPLASH.value

# m_float.h
FRAME_actvat01 = 0
FRAME_actvat02 = 1
FRAME_actvat03 = 2
FRAME_actvat04 = 3
FRAME_actvat05 = 4
FRAME_actvat06 = 5
FRAME_actvat07 = 6
FRAME_actvat08 = 7
FRAME_actvat09 = 8
FRAME_actvat10 = 9
FRAME_actvat11 = 10
FRAME_actvat12 = 11
FRAME_actvat13 = 12
FRAME_actvat14 = 13
FRAME_actvat15 = 14
FRAME_actvat16 = 15
FRAME_actvat17 = 16
FRAME_actvat18 = 17
FRAME_actvat19 = 18
FRAME_actvat20 = 19
FRAME_actvat21 = 20
FRAME_actvat22 = 21
FRAME_actvat23 = 22
FRAME_actvat24 = 23
FRAME_actvat25 = 24
FRAME_actvat26 = 25
FRAME_actvat27 = 26
FRAME_actvat28 = 27
FRAME_actvat29 = 28
FRAME_actvat30 = 29
FRAME_actvat31 = 30
FRAME_attak101 = 31
FRAME_attak102 = 32
FRAME_attak103 = 33
FRAME_attak104 = 34
FRAME_attak105 = 35
FRAME_attak106 = 36
FRAME_attak107 = 37
FRAME_attak108 = 38
FRAME_attak109 = 39
FRAME_attak110 = 40
FRAME_attak111 = 41
FRAME_attak112 = 42
FRAME_attak113 = 43
FRAME_attak114 = 44
FRAME_attak201 = 45
FRAME_attak202 = 46
FRAME_attak203 = 47
FRAME_attak204 = 48
FRAME_attak205 = 49
FRAME_attak206 = 50
FRAME_attak207 = 51
FRAME_attak208 = 52
FRAME_attak209 = 53
FRAME_attak210 = 54
FRAME_attak211 = 55
FRAME_attak212 = 56
FRAME_attak213 = 57
FRAME_attak214 = 58
FRAME_attak215 = 59
FRAME_attak216 = 60
FRAME_attak217 = 61
FRAME_attak218 = 62
FRAME_attak219 = 63
FRAME_attak220 = 64
FRAME_attak221 = 65
FRAME_attak222 = 66
FRAME_attak223 = 67
FRAME_attak224 = 68
FRAME_attak225 = 69
FRAME_attak301 = 70
FRAME_attak302 = 71
FRAME_attak303 = 72
FRAME_attak304 = 73
FRAME_attak305 = 74
FRAME_attak306 = 75
FRAME_attak307 = 76
FRAME_attak308 = 77
FRAME_attak309 = 78
FRAME_attak310 = 79
FRAME_attak311 = 80
FRAME_attak312 = 81
FRAME_attak313 = 82
FRAME_attak314 = 83
FRAME_attak315 = 84
FRAME_attak316 = 85
FRAME_attak317 = 86
FRAME_attak318 = 87
FRAME_attak319 = 88
FRAME_attak320 = 89
FRAME_attak321 = 90
FRAME_attak322 = 91
FRAME_attak323 = 92
FRAME_attak324 = 93
FRAME_attak325 = 94
FRAME_attak326 = 95
FRAME_attak327 = 96
FRAME_attak328 = 97
FRAME_attak329 = 98
FRAME_attak330 = 99
FRAME_attak331 = 100
FRAME_attak332 = 101
FRAME_attak333 = 102
FRAME_attak334 = 103
FRAME_death01 = 104
FRAME_death02 = 105
FRAME_death03 = 106
FRAME_death04 = 107
FRAME_death05 = 108
FRAME_death06 = 109
FRAME_death07 = 110
FRAME_death08 = 111
FRAME_death09 = 112
FRAME_death10 = 113
FRAME_death11 = 114
FRAME_death12 = 115
FRAME_death13 = 116
FRAME_pain101 = 117
FRAME_pain102 = 118
FRAME_pain103 = 119
FRAME_pain104 = 120
FRAME_pain105 = 121
FRAME_pain106 = 122
FRAME_pain107 = 123
FRAME_pain201 = 124
FRAME_pain202 = 125
FRAME_pain203 = 126
FRAME_pain204 = 127
FRAME_pain205 = 128
FRAME_pain206 = 129
FRAME_pain207 = 130
FRAME_pain208 = 131
FRAME_pain301 = 132
FRAME_pain302 = 133
FRAME_pain303 = 134
FRAME_pain304 = 135
FRAME_pain305 = 136
FRAME_pain306 = 137
FRAME_pain307 = 138
FRAME_pain308 = 139
FRAME_pain309 = 140
FRAME_pain310 = 141
FRAME_pain311 = 142
FRAME_pain312 = 143
FRAME_stand101 = 144
FRAME_stand102 = 145
FRAME_stand103 = 146
FRAME_stand104 = 147
FRAME_stand105 = 148
FRAME_stand106 = 149
FRAME_stand107 = 150
FRAME_stand108 = 151
FRAME_stand109 = 152
FRAME_stand110 = 153
FRAME_stand111 = 154
FRAME_stand112 = 155
FRAME_stand113 = 156
FRAME_stand114 = 157
FRAME_stand115 = 158
FRAME_stand116 = 159
FRAME_stand117 = 160
FRAME_stand118 = 161
FRAME_stand119 = 162
FRAME_stand120 = 163
FRAME_stand121 = 164
FRAME_stand122 = 165
FRAME_stand123 = 166
FRAME_stand124 = 167
FRAME_stand125 = 168
FRAME_stand126 = 169
FRAME_stand127 = 170
FRAME_stand128 = 171
FRAME_stand129 = 172
FRAME_stand130 = 173
FRAME_stand131 = 174
FRAME_stand132 = 175
FRAME_stand133 = 176
FRAME_stand134 = 177
FRAME_stand135 = 178
FRAME_stand136 = 179
FRAME_stand137 = 180
FRAME_stand138 = 181
FRAME_stand139 = 182
FRAME_stand140 = 183
FRAME_stand141 = 184
FRAME_stand142 = 185
FRAME_stand143 = 186
FRAME_stand144 = 187
FRAME_stand145 = 188
FRAME_stand146 = 189
FRAME_stand147 = 190
FRAME_stand148 = 191
FRAME_stand149 = 192
FRAME_stand150 = 193
FRAME_stand151 = 194
FRAME_stand152 = 195
FRAME_stand201 = 196
FRAME_stand202 = 197
FRAME_stand203 = 198
FRAME_stand204 = 199
FRAME_stand205 = 200
FRAME_stand206 = 201
FRAME_stand207 = 202
FRAME_stand208 = 203
FRAME_stand209 = 204
FRAME_stand210 = 205
FRAME_stand211 = 206
FRAME_stand212 = 207
FRAME_stand213 = 208
FRAME_stand214 = 209
FRAME_stand215 = 210
FRAME_stand216 = 211
FRAME_stand217 = 212
FRAME_stand218 = 213
FRAME_stand219 = 214
FRAME_stand220 = 215
FRAME_stand221 = 216
FRAME_stand222 = 217
FRAME_stand223 = 218
FRAME_stand224 = 219
FRAME_stand225 = 220
FRAME_stand226 = 221
FRAME_stand227 = 222
FRAME_stand228 = 223
FRAME_stand229 = 224
FRAME_stand230 = 225
FRAME_stand231 = 226
FRAME_stand232 = 227
FRAME_stand233 = 228
FRAME_stand234 = 229
FRAME_stand235 = 230
FRAME_stand236 = 231
FRAME_stand237 = 232
FRAME_stand238 = 233
FRAME_stand239 = 234
FRAME_stand240 = 235
FRAME_stand241 = 236
FRAME_stand242 = 237
FRAME_stand243 = 238
FRAME_stand244 = 239
FRAME_stand245 = 240
FRAME_stand246 = 241
FRAME_stand247 = 242
FRAME_stand248 = 243
FRAME_stand249 = 244
FRAME_stand250 = 245
FRAME_stand251 = 246
FRAME_stand252 = 247
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

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def floater_idle (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def floater_fire_blaster (self): #edict_t *

	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	effect;

	if (self.s.frame == FRAME_attak104) or (self.s.frame == FRAME_attak107):
		effect = EF_HYPERBLASTER
	else:
		effect = 0
	q_shared.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[MZ2_FLOAT_BLASTER_1], forward, right, start)

	q_shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	q_shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 1, 1000, MZ2_FLOAT_BLASTER_1, effect)


def floater_stand (self): #edict_t *

	if g_local.random() <= 0.5:
		self.monsterinfo.currentmove = floater_move_stand1
	else:
		self.monsterinfo.currentmove = floater_move_stand2


def floater_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = floater_move_stand1
	else:
		self.monsterinfo.currentmove = floater_move_run


def floater_walk (self): #edict_t *

	self.monsterinfo.currentmove = floater_move_walk


def floater_wham (self): #edict_t *

	aim = np.array([MELEE_DISTANCE, 0, 0], dtype=np.float32) #static vec3_t
	g_main.gi.sound (self, CHAN_WEAPON, sound_attack3, 1, ATTN_NORM, 0)
	fire_hit (self, aim, 5 + _r.randint(0, 2147483647) % 6, -50)


def floater_zap (self): #edict_t *

	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	origin = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	offset = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, dir)

	q_shared.AngleVectors (self.s.angles, forward, right, None)
	# FIXME use a flash and replace these two lines with the commented one
	q_shared.VectorSet (offset, 18.5, -0.9, 10)
	G_ProjectSource (self.s.origin, offset, forward, right, origin)
	# G_ProjectSource (self->s.origin, monster_flash_offset[flash_number], forward, right, origin);

	g_main.gi.sound (self, CHAN_WEAPON, sound_attack2, 1, ATTN_NORM, 0)

	# FIXME use the flash, Luke
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_SPLASH)
	g_main.gi.WriteByte (32)
	g_main.gi.WritePosition (origin)
	g_main.gi.WriteDir (dir)
	g_main.gi.WriteByte (1)	# sparks
	g_main.gi.multicast (origin, MULTICAST_PVS)

	T_Damage (self.enemy, self, self, dir, self.enemy.s.origin, vec3_origin, 5 + _r.randint(0, 2147483647) % 6, -10, DAMAGE_ENERGY, MOD_UNKNOWN)


def floater_attack (self): #edict_t *

	self.monsterinfo.currentmove = floater_move_attack1


def floater_melee (self): #edict_t *

	if g_local.random() < 0.5:
		self.monsterinfo.currentmove = floater_move_attack3
	else:
		self.monsterinfo.currentmove = floater_move_attack2


def floater_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	#int	n;

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	n = (_r.randint(0, 2147483647) + 1) % 3
	if n == 0:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = floater_move_pain1
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = floater_move_pain2


def floater_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def floater_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	g_main.gi.sound (self, CHAN_VOICE, sound_death1, 1, ATTN_NORM, 0)
	BecomeExplosion1(self)


"""QUAKED monster_floater (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_floater (self): #edict_t *

	global sound_attack2, sound_attack3, sound_death1, sound_idle, sound_pain1, sound_pain2, sound_sight
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
	q_shared.VectorSet (self.mins, -24, -24, -24)
	q_shared.VectorSet (self.maxs, 24, 24, 32)

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

	if g_local.random() <= 0.5:
		self.monsterinfo.currentmove = floater_move_stand1
	else:
		self.monsterinfo.currentmove = floater_move_stand2

	self.monsterinfo.scale = MODEL_SCALE

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
floater_move_stand1 = _mm(FRAME_stand101, FRAME_stand152, floater_frames_stand1, None)

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
floater_move_stand2 = _mm(FRAME_stand201, FRAME_stand252, floater_frames_stand2, None)

floater_frames_activate = [
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
floater_move_activate = _mm(FRAME_actvat01, FRAME_actvat31, floater_frames_activate, None)

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
floater_move_attack1 = _mm(FRAME_attak101, FRAME_attak114, floater_frames_attack1, floater_run)

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
floater_move_attack2 = _mm(FRAME_attak201, FRAME_attak225, floater_frames_attack2, floater_run)

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
floater_move_attack3 = _mm(FRAME_attak301, FRAME_attak334, floater_frames_attack3, floater_run)

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
floater_move_death = _mm(FRAME_death01, FRAME_death13, floater_frames_death, floater_dead)

floater_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
floater_move_pain1 = _mm(FRAME_pain101, FRAME_pain107, floater_frames_pain1, floater_run)

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
floater_move_pain2 = _mm(FRAME_pain201, FRAME_pain208, floater_frames_pain2, floater_run)

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
floater_move_pain3 = _mm(FRAME_pain301, FRAME_pain312, floater_frames_pain3, floater_run)

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
floater_move_walk = _mm(FRAME_stand101, FRAME_stand152, floater_frames_walk, None)

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
floater_move_run = _mm(FRAME_stand101, FRAME_stand152, floater_frames_run, None)


