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
from game import g_main, g_local, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_local import (AI_BRUTAL, AI_STAND_GROUND, DEAD_DEAD, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, GIB_METALLIC, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_blaster, monster_fire_bullet, monster_fire_rocket, walkmonster_start)
from game.g_utils import (G_FreeEdict, G_ProjectSource, vectoangles)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_BODY, CHAN_VOICE, CHAN_WEAPON, EF_BLASTER, MZ2_TANK_BLASTER_1, MZ2_TANK_BLASTER_2, MZ2_TANK_BLASTER_3, MZ2_TANK_MACHINEGUN_1, MZ2_TANK_ROCKET_1, MZ2_TANK_ROCKET_2, MZ2_TANK_ROCKET_3
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_tank.h
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
FRAME_walk01 = 30
FRAME_walk02 = 31
FRAME_walk03 = 32
FRAME_walk04 = 33
FRAME_walk05 = 34
FRAME_walk06 = 35
FRAME_walk07 = 36
FRAME_walk08 = 37
FRAME_walk09 = 38
FRAME_walk10 = 39
FRAME_walk11 = 40
FRAME_walk12 = 41
FRAME_walk13 = 42
FRAME_walk14 = 43
FRAME_walk15 = 44
FRAME_walk16 = 45
FRAME_walk17 = 46
FRAME_walk18 = 47
FRAME_walk19 = 48
FRAME_walk20 = 49
FRAME_walk21 = 50
FRAME_walk22 = 51
FRAME_walk23 = 52
FRAME_walk24 = 53
FRAME_walk25 = 54
FRAME_attak101 = 55
FRAME_attak102 = 56
FRAME_attak103 = 57
FRAME_attak104 = 58
FRAME_attak105 = 59
FRAME_attak106 = 60
FRAME_attak107 = 61
FRAME_attak108 = 62
FRAME_attak109 = 63
FRAME_attak110 = 64
FRAME_attak111 = 65
FRAME_attak112 = 66
FRAME_attak113 = 67
FRAME_attak114 = 68
FRAME_attak115 = 69
FRAME_attak116 = 70
FRAME_attak117 = 71
FRAME_attak118 = 72
FRAME_attak119 = 73
FRAME_attak120 = 74
FRAME_attak121 = 75
FRAME_attak122 = 76
FRAME_attak201 = 77
FRAME_attak202 = 78
FRAME_attak203 = 79
FRAME_attak204 = 80
FRAME_attak205 = 81
FRAME_attak206 = 82
FRAME_attak207 = 83
FRAME_attak208 = 84
FRAME_attak209 = 85
FRAME_attak210 = 86
FRAME_attak211 = 87
FRAME_attak212 = 88
FRAME_attak213 = 89
FRAME_attak214 = 90
FRAME_attak215 = 91
FRAME_attak216 = 92
FRAME_attak217 = 93
FRAME_attak218 = 94
FRAME_attak219 = 95
FRAME_attak220 = 96
FRAME_attak221 = 97
FRAME_attak222 = 98
FRAME_attak223 = 99
FRAME_attak224 = 100
FRAME_attak225 = 101
FRAME_attak226 = 102
FRAME_attak227 = 103
FRAME_attak228 = 104
FRAME_attak229 = 105
FRAME_attak230 = 106
FRAME_attak231 = 107
FRAME_attak232 = 108
FRAME_attak233 = 109
FRAME_attak234 = 110
FRAME_attak235 = 111
FRAME_attak236 = 112
FRAME_attak237 = 113
FRAME_attak238 = 114
FRAME_attak301 = 115
FRAME_attak302 = 116
FRAME_attak303 = 117
FRAME_attak304 = 118
FRAME_attak305 = 119
FRAME_attak306 = 120
FRAME_attak307 = 121
FRAME_attak308 = 122
FRAME_attak309 = 123
FRAME_attak310 = 124
FRAME_attak311 = 125
FRAME_attak312 = 126
FRAME_attak313 = 127
FRAME_attak314 = 128
FRAME_attak315 = 129
FRAME_attak316 = 130
FRAME_attak317 = 131
FRAME_attak318 = 132
FRAME_attak319 = 133
FRAME_attak320 = 134
FRAME_attak321 = 135
FRAME_attak322 = 136
FRAME_attak323 = 137
FRAME_attak324 = 138
FRAME_attak325 = 139
FRAME_attak326 = 140
FRAME_attak327 = 141
FRAME_attak328 = 142
FRAME_attak329 = 143
FRAME_attak330 = 144
FRAME_attak331 = 145
FRAME_attak332 = 146
FRAME_attak333 = 147
FRAME_attak334 = 148
FRAME_attak335 = 149
FRAME_attak336 = 150
FRAME_attak337 = 151
FRAME_attak338 = 152
FRAME_attak339 = 153
FRAME_attak340 = 154
FRAME_attak341 = 155
FRAME_attak342 = 156
FRAME_attak343 = 157
FRAME_attak344 = 158
FRAME_attak345 = 159
FRAME_attak346 = 160
FRAME_attak347 = 161
FRAME_attak348 = 162
FRAME_attak349 = 163
FRAME_attak350 = 164
FRAME_attak351 = 165
FRAME_attak352 = 166
FRAME_attak353 = 167
FRAME_attak401 = 168
FRAME_attak402 = 169
FRAME_attak403 = 170
FRAME_attak404 = 171
FRAME_attak405 = 172
FRAME_attak406 = 173
FRAME_attak407 = 174
FRAME_attak408 = 175
FRAME_attak409 = 176
FRAME_attak410 = 177
FRAME_attak411 = 178
FRAME_attak412 = 179
FRAME_attak413 = 180
FRAME_attak414 = 181
FRAME_attak415 = 182
FRAME_attak416 = 183
FRAME_attak417 = 184
FRAME_attak418 = 185
FRAME_attak419 = 186
FRAME_attak420 = 187
FRAME_attak421 = 188
FRAME_attak422 = 189
FRAME_attak423 = 190
FRAME_attak424 = 191
FRAME_attak425 = 192
FRAME_attak426 = 193
FRAME_attak427 = 194
FRAME_attak428 = 195
FRAME_attak429 = 196
FRAME_pain101 = 197
FRAME_pain102 = 198
FRAME_pain103 = 199
FRAME_pain104 = 200
FRAME_pain201 = 201
FRAME_pain202 = 202
FRAME_pain203 = 203
FRAME_pain204 = 204
FRAME_pain205 = 205
FRAME_pain301 = 206
FRAME_pain302 = 207
FRAME_pain303 = 208
FRAME_pain304 = 209
FRAME_pain305 = 210
FRAME_pain306 = 211
FRAME_pain307 = 212
FRAME_pain308 = 213
FRAME_pain309 = 214
FRAME_pain310 = 215
FRAME_pain311 = 216
FRAME_pain312 = 217
FRAME_pain313 = 218
FRAME_pain314 = 219
FRAME_pain315 = 220
FRAME_pain316 = 221
FRAME_death101 = 222
FRAME_death102 = 223
FRAME_death103 = 224
FRAME_death104 = 225
FRAME_death105 = 226
FRAME_death106 = 227
FRAME_death107 = 228
FRAME_death108 = 229
FRAME_death109 = 230
FRAME_death110 = 231
FRAME_death111 = 232
FRAME_death112 = 233
FRAME_death113 = 234
FRAME_death114 = 235
FRAME_death115 = 236
FRAME_death116 = 237
FRAME_death117 = 238
FRAME_death118 = 239
FRAME_death119 = 240
FRAME_death120 = 241
FRAME_death121 = 242
FRAME_death122 = 243
FRAME_death123 = 244
FRAME_death124 = 245
FRAME_death125 = 246
FRAME_death126 = 247
FRAME_death127 = 248
FRAME_death128 = 249
FRAME_death129 = 250
FRAME_death130 = 251
FRAME_death131 = 252
FRAME_death132 = 253
FRAME_recln101 = 254
FRAME_recln102 = 255
FRAME_recln103 = 256
FRAME_recln104 = 257
FRAME_recln105 = 258
FRAME_recln106 = 259
FRAME_recln107 = 260
FRAME_recln108 = 261
FRAME_recln109 = 262
FRAME_recln110 = 263
FRAME_recln111 = 264
FRAME_recln112 = 265
FRAME_recln113 = 266
FRAME_recln114 = 267
FRAME_recln115 = 268
FRAME_recln116 = 269
FRAME_recln117 = 270
FRAME_recln118 = 271
FRAME_recln119 = 272
FRAME_recln120 = 273
FRAME_recln121 = 274
FRAME_recln122 = 275
FRAME_recln123 = 276
FRAME_recln124 = 277
FRAME_recln125 = 278
FRAME_recln126 = 279
FRAME_recln127 = 280
FRAME_recln128 = 281
FRAME_recln129 = 282
FRAME_recln130 = 283
FRAME_recln131 = 284
FRAME_recln132 = 285
FRAME_recln133 = 286
FRAME_recln134 = 287
FRAME_recln135 = 288
FRAME_recln136 = 289
FRAME_recln137 = 290
FRAME_recln138 = 291
FRAME_recln139 = 292
FRAME_recln140 = 293
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

sound_thud = 0 # static
sound_pain = 0 # static
sound_idle = 0 # static
sound_die = 0 # static
sound_step = 0 # static
sound_sight = 0 # static
sound_windup = 0 # static
sound_strike = 0 # static


"""
==============================================================================

TANK

==============================================================================
"""
def tank_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def tank_footstep (self): #edict_t *

	g_main.gi.sound (self, CHAN_BODY, sound_step, 1, ATTN_NORM, 0)


def tank_thud (self): #edict_t *

	g_main.gi.sound (self, CHAN_BODY, sound_thud, 1, ATTN_NORM, 0)


def tank_windup (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_windup, 1, ATTN_NORM, 0)


def tank_idle (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def tank_stand (self): #edict_t *

	self.monsterinfo.currentmove = tank_move_stand


def tank_walk (self): #edict_t *

	self.monsterinfo.currentmove = tank_move_walk


def tank_run (self): #edict_t *

	if self.enemy and self.enemy.client:
		self.monsterinfo.aiflags |= AI_BRUTAL
	else:
		self.monsterinfo.aiflags &= ~AI_BRUTAL

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = tank_move_stand
		return

	if self.monsterinfo.currentmove == tank_move_walk or self.monsterinfo.currentmove == tank_move_start_run:
		self.monsterinfo.currentmove = tank_move_run
	else:
		self.monsterinfo.currentmove = tank_move_start_run


def tank_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	if self.health < (self.max_health // 2):
		self.s.skinnum |= 1

	if damage <= 10:
		return

	if g_main.level.time < self.pain_debounce_time:
		return

	if damage <= 30:
		if g_local.random() > 0.2:
			return

	# If hard or nightmare, don't go into pain while attacking
	if g_main.skill.value >= 2:
		if (self.s.frame >= FRAME_attak301) and (self.s.frame <= FRAME_attak330):
			return
		if (self.s.frame >= FRAME_attak101) and (self.s.frame <= FRAME_attak116):
			return

	self.pain_debounce_time = g_main.level.time + 3
	g_main.gi.sound (self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if damage <= 30:
		self.monsterinfo.currentmove = tank_move_pain1
	elif damage <= 60:
		self.monsterinfo.currentmove = tank_move_pain2
	else:
		self.monsterinfo.currentmove = tank_move_pain3


def TankBlaster (self): #edict_t *

	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	if self.s.frame == FRAME_attak110:
		flash_number = MZ2_TANK_BLASTER_1
	elif self.s.frame == FRAME_attak113:
		flash_number = MZ2_TANK_BLASTER_2
	else:
		# (self->s.frame == FRAME_attak116)
		flash_number = MZ2_TANK_BLASTER_3

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 30, 800, flash_number, EF_BLASTER)


def TankStrike (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_strike, 1, ATTN_NORM, 0)


def TankRocket (self): #edict_t *

	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	if self.s.frame == FRAME_attak324:
		flash_number = MZ2_TANK_ROCKET_1
	elif self.s.frame == FRAME_attak327:
		flash_number = MZ2_TANK_ROCKET_2
	else:
		# (self->s.frame == FRAME_attak330)
		flash_number = MZ2_TANK_ROCKET_3

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)

	monster_fire_rocket (self, start, dir, 50, 550, flash_number)


def TankMachineGun (self): #edict_t *

	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	flash_number = MZ2_TANK_MACHINEGUN_1 + (self.s.frame - FRAME_attak406)

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	if self.enemy:
		shared.VectorCopy (self.enemy.s.origin, vec)
		vec[2] += self.enemy.viewheight
		shared.VectorSubtract (vec, start, vec)
		vectoangles (vec, vec)
		dir[0] = vec[0]
	else:
		dir[0] = 0
	if self.s.frame <= FRAME_attak415:
		dir[1] = self.s.angles[1] - 8 * (self.s.frame - FRAME_attak411)
	else:
		dir[1] = self.s.angles[1] + 8 * (self.s.frame - FRAME_attak419)
	dir[2] = 0

	shared_c.AngleVectors (dir, forward, None, None)

	monster_fire_bullet (self, start, forward, 20, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)


def tank_reattack_blaster (self): #edict_t *

	if g_main.skill.value >= 2:
		if g_ai.visible (self, self.enemy):
			if self.enemy.health > 0:
				if g_local.random() <= 0.6:
					self.monsterinfo.currentmove = tank_move_reattack_blast
					return
	self.monsterinfo.currentmove = tank_move_attack_post_blast


def tank_poststrike (self): #edict_t *

	self.enemy = None
	tank_run (self)


def tank_refire_rocket (self): #edict_t *

	# Only on hard or nightmare
	if g_main.skill.value >= 2:
		if self.enemy.health > 0:
			if g_ai.visible(self, self.enemy):
				if g_local.random() <= 0.4:
					self.monsterinfo.currentmove = tank_move_attack_fire_rocket
					return
	self.monsterinfo.currentmove = tank_move_attack_post_rocket


def tank_doattack_rocket (self): #edict_t *

	self.monsterinfo.currentmove = tank_move_attack_fire_rocket


def tank_attack (self): #edict_t *

	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#float	range;
	#float	r;

	if self.enemy.health < 0:
		self.monsterinfo.currentmove = tank_move_attack_strike
		self.monsterinfo.aiflags &= ~AI_BRUTAL
		return

	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range = shared_c.VectorLength (vec)

	r = g_local.random()

	if range <= 125:
		if r < 0.4:
			self.monsterinfo.currentmove = tank_move_attack_chain
		else:
			self.monsterinfo.currentmove = tank_move_attack_blast
	elif range <= 250:
		if r < 0.5:
			self.monsterinfo.currentmove = tank_move_attack_chain
		else:
			self.monsterinfo.currentmove = tank_move_attack_blast
	else:
		if r < 0.33:
			self.monsterinfo.currentmove = tank_move_attack_chain
		elif r < 0.66:
			self.monsterinfo.currentmove = tank_move_attack_pre_rocket
			self.pain_debounce_time = g_main.level.time + 5.0	# no pain for a while
		else:
			self.monsterinfo.currentmove = tank_move_attack_blast


def tank_dead (self): #edict_t *

	shared.VectorSet (self.mins, -16, -16, -16)
	shared.VectorSet (self.maxs, 16, 16, -0)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def tank_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# check for gib
	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(0, 1):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		for n in range(0, 4):
			ThrowGib (self, "models/objects/gibs/sm_metal/tris.md2", damage, GIB_METALLIC)
		ThrowGib (self, "models/objects/gibs/chest/tris.md2", damage, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/gear/tris.md2", damage, GIB_METALLIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	# regular death
	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	self.monsterinfo.currentmove = tank_move_death


"""QUAKED monster_tank (1 .5 0) (-32 -32 -16) (32 32 72) Ambush Trigger_Spawn Sight
"""
"""QUAKED monster_tank_commander (1 .5 0) (-32 -32 -16) (32 32 72) Ambush Trigger_Spawn Sight
"""
def SP_monster_tank (self): #edict_t *

	global sound_thud, sound_pain, sound_idle, sound_die, sound_step, sound_sight, sound_windup, sound_strike
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	self.s.modelindex = g_main.gi.modelindex ("models/monsters/tank/tris.md2")
	shared.VectorSet (self.mins, -32, -32, -16)
	shared.VectorSet (self.maxs, 32, 32, 72)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX

	sound_pain = g_main.gi.soundindex ("tank/tnkpain2.wav")
	sound_thud = g_main.gi.soundindex ("tank/tnkdeth2.wav")
	sound_idle = g_main.gi.soundindex ("tank/tnkidle1.wav")
	sound_die = g_main.gi.soundindex ("tank/death.wav")
	sound_step = g_main.gi.soundindex ("tank/step.wav")
	sound_windup = g_main.gi.soundindex ("tank/tnkatck4.wav")
	sound_strike = g_main.gi.soundindex ("tank/tnkatck5.wav")
	sound_sight = g_main.gi.soundindex ("tank/sight1.wav")

	g_main.gi.soundindex ("tank/tnkatck1.wav")
	g_main.gi.soundindex ("tank/tnkatk2a.wav")
	g_main.gi.soundindex ("tank/tnkatk2b.wav")
	g_main.gi.soundindex ("tank/tnkatk2c.wav")
	g_main.gi.soundindex ("tank/tnkatk2d.wav")
	g_main.gi.soundindex ("tank/tnkatk2e.wav")
	g_main.gi.soundindex ("tank/tnkatck3.wav")

	if (self.classname == "monster_tank_commander"):
		self.health = 1000
		self.gib_health = -225
	else:
		self.health = 750
		self.gib_health = -200

	self.mass = 500

	self.pain = tank_pain
	self.die = tank_die
	self.monsterinfo.stand = tank_stand
	self.monsterinfo.walk = tank_walk
	self.monsterinfo.run = tank_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = tank_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = tank_sight
	self.monsterinfo.idle = tank_idle

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = tank_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start(self)

	if (self.classname == "monster_tank_commander"):
		self.s.skinnum = 2



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
tank_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
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
tank_move_stand = _mm(FRAME_stand01, FRAME_stand30, tank_frames_stand, None)

tank_frames_start_walk = [
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 11, tank_footstep),
]
tank_move_start_walk = _mm(FRAME_walk01, FRAME_walk04, tank_frames_start_walk, tank_walk)

tank_frames_walk = [
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 4, tank_footstep),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 6, tank_footstep),
]
tank_move_walk = _mm(FRAME_walk05, FRAME_walk20, tank_frames_walk, None)

tank_frames_stop_walk = [
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 4, tank_footstep),
]
tank_move_stop_walk = _mm(FRAME_walk21, FRAME_walk25, tank_frames_stop_walk, tank_stand)

tank_frames_start_run = [
	_mf(ai_run, 0, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 11, tank_footstep),
]
tank_move_start_run = _mm(FRAME_walk01, FRAME_walk04, tank_frames_start_run, tank_run)

tank_frames_run = [
	_mf(ai_run, 4, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 4, None),
	_mf(ai_run, 4, tank_footstep),
	_mf(ai_run, 3, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 4, None),
	_mf(ai_run, 5, None),
	_mf(ai_run, 7, None),
	_mf(ai_run, 7, None),
	_mf(ai_run, 6, None),
	_mf(ai_run, 6, tank_footstep),
]
tank_move_run = _mm(FRAME_walk05, FRAME_walk20, tank_frames_run, None)

tank_frames_stop_run = [
	_mf(ai_run, 3, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 4, tank_footstep),
]
tank_move_stop_run = _mm(FRAME_walk21, FRAME_walk25, tank_frames_stop_run, tank_walk)

tank_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
tank_move_pain1 = _mm(FRAME_pain101, FRAME_pain104, tank_frames_pain1, tank_run)

tank_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
tank_move_pain2 = _mm(FRAME_pain201, FRAME_pain205, tank_frames_pain2, tank_run)

tank_frames_pain3 = [
	_mf(ai_move, -7, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, tank_footstep),
]
tank_move_pain3 = _mm(FRAME_pain301, FRAME_pain316, tank_frames_pain3, tank_run)

tank_frames_attack_blast = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),	# 10
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),	# 16
]
tank_move_attack_blast = _mm(FRAME_attak101, FRAME_attak116, tank_frames_attack_blast, tank_reattack_blaster)

tank_frames_reattack_blast = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankBlaster),	# 16
]
tank_move_reattack_blast = _mm(FRAME_attak111, FRAME_attak116, tank_frames_reattack_blast, tank_reattack_blaster)

tank_frames_attack_post_blast = [
	_mf(ai_move, 0, None),	# 17
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, -2, tank_footstep),	# 22
]
tank_move_attack_post_blast = _mm(FRAME_attak117, FRAME_attak122, tank_frames_attack_post_blast, tank_run)

tank_frames_attack_strike = [
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 7, None),
	_mf(ai_move, 9, tank_footstep),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 2, tank_footstep),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 0, tank_windup),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, TankStrike),
	_mf(ai_move, 0, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -10, None),
	_mf(ai_move, -10, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -2, tank_footstep),
]
tank_move_attack_strike = _mm(FRAME_attak201, FRAME_attak238, tank_frames_attack_strike, tank_poststrike)

tank_frames_attack_pre_rocket = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 10
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 7, None),
	_mf(ai_charge, 7, None),
	_mf(ai_charge, 7, tank_footstep),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 20
	_mf(ai_charge, -3, None),
]
tank_move_attack_pre_rocket = _mm(FRAME_attak301, FRAME_attak321, tank_frames_attack_pre_rocket, tank_doattack_rocket)

tank_frames_attack_fire_rocket = [
	_mf(ai_charge, -3, None),	# Loop Start	22
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankRocket),	# 24
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, TankRocket),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -1, TankRocket),	# 30	Loop End
]
tank_move_attack_fire_rocket = _mm(FRAME_attak322, FRAME_attak330, tank_frames_attack_fire_rocket, tank_refire_rocket)

tank_frames_attack_post_rocket = [
	_mf(ai_charge, 0, None),	# 31
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 40
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -9, None),
	_mf(ai_charge, -8, None),
	_mf(ai_charge, -7, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -1, tank_footstep),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# 50
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
tank_move_attack_post_rocket = _mm(FRAME_attak331, FRAME_attak353, tank_frames_attack_post_rocket, tank_run)

tank_frames_attack_chain = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(None, 0, TankMachineGun),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
tank_move_attack_chain = _mm(FRAME_attak401, FRAME_attak429, tank_frames_attack_chain, tank_run)

tank_frames_death1 = [
	_mf(ai_move, -7, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -4, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, -15, tank_thud),
	_mf(ai_move, -5, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
tank_move_death = _mm(FRAME_death101, FRAME_death132, tank_frames_death1, tank_dead)


