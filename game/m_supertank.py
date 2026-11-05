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
from game.g_local import (AI_STAND_GROUND, DEAD_DEAD, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, GIB_METALLIC, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t, svc_temp_entity)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_bullet, monster_fire_rocket, walkmonster_start)
from game.g_utils import (G_FreeEdict, G_ProjectSource)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_NORM, CHAN_VOICE, MZ2_SUPERTANK_MACHINEGUN_1, MZ2_SUPERTANK_ROCKET_1, MZ2_SUPERTANK_ROCKET_2, MZ2_SUPERTANK_ROCKET_3, multicast_t, temp_event_t)
DAMAGE_NO = damage_t.DAMAGE_NO.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_EXPLOSION1 = temp_event_t.TE_EXPLOSION1.value

# m_supertank.h
FRAME_attak1_1 = 0
FRAME_attak1_2 = 1
FRAME_attak1_3 = 2
FRAME_attak1_4 = 3
FRAME_attak1_5 = 4
FRAME_attak1_6 = 5
FRAME_attak1_7 = 6
FRAME_attak1_8 = 7
FRAME_attak1_9 = 8
FRAME_attak1_10 = 9
FRAME_attak1_11 = 10
FRAME_attak1_12 = 11
FRAME_attak1_13 = 12
FRAME_attak1_14 = 13
FRAME_attak1_15 = 14
FRAME_attak1_16 = 15
FRAME_attak1_17 = 16
FRAME_attak1_18 = 17
FRAME_attak1_19 = 18
FRAME_attak1_20 = 19
FRAME_attak2_1 = 20
FRAME_attak2_2 = 21
FRAME_attak2_3 = 22
FRAME_attak2_4 = 23
FRAME_attak2_5 = 24
FRAME_attak2_6 = 25
FRAME_attak2_7 = 26
FRAME_attak2_8 = 27
FRAME_attak2_9 = 28
FRAME_attak2_10 = 29
FRAME_attak2_11 = 30
FRAME_attak2_12 = 31
FRAME_attak2_13 = 32
FRAME_attak2_14 = 33
FRAME_attak2_15 = 34
FRAME_attak2_16 = 35
FRAME_attak2_17 = 36
FRAME_attak2_18 = 37
FRAME_attak2_19 = 38
FRAME_attak2_20 = 39
FRAME_attak2_21 = 40
FRAME_attak2_22 = 41
FRAME_attak2_23 = 42
FRAME_attak2_24 = 43
FRAME_attak2_25 = 44
FRAME_attak2_26 = 45
FRAME_attak2_27 = 46
FRAME_attak3_1 = 47
FRAME_attak3_2 = 48
FRAME_attak3_3 = 49
FRAME_attak3_4 = 50
FRAME_attak3_5 = 51
FRAME_attak3_6 = 52
FRAME_attak3_7 = 53
FRAME_attak3_8 = 54
FRAME_attak3_9 = 55
FRAME_attak3_10 = 56
FRAME_attak3_11 = 57
FRAME_attak3_12 = 58
FRAME_attak3_13 = 59
FRAME_attak3_14 = 60
FRAME_attak3_15 = 61
FRAME_attak3_16 = 62
FRAME_attak3_17 = 63
FRAME_attak3_18 = 64
FRAME_attak3_19 = 65
FRAME_attak3_20 = 66
FRAME_attak3_21 = 67
FRAME_attak3_22 = 68
FRAME_attak3_23 = 69
FRAME_attak3_24 = 70
FRAME_attak3_25 = 71
FRAME_attak3_26 = 72
FRAME_attak3_27 = 73
FRAME_attak4_1 = 74
FRAME_attak4_2 = 75
FRAME_attak4_3 = 76
FRAME_attak4_4 = 77
FRAME_attak4_5 = 78
FRAME_attak4_6 = 79
FRAME_backwd_1 = 80
FRAME_backwd_2 = 81
FRAME_backwd_3 = 82
FRAME_backwd_4 = 83
FRAME_backwd_5 = 84
FRAME_backwd_6 = 85
FRAME_backwd_7 = 86
FRAME_backwd_8 = 87
FRAME_backwd_9 = 88
FRAME_backwd_10 = 89
FRAME_backwd_11 = 90
FRAME_backwd_12 = 91
FRAME_backwd_13 = 92
FRAME_backwd_14 = 93
FRAME_backwd_15 = 94
FRAME_backwd_16 = 95
FRAME_backwd_17 = 96
FRAME_backwd_18 = 97
FRAME_death_1 = 98
FRAME_death_2 = 99
FRAME_death_3 = 100
FRAME_death_4 = 101
FRAME_death_5 = 102
FRAME_death_6 = 103
FRAME_death_7 = 104
FRAME_death_8 = 105
FRAME_death_9 = 106
FRAME_death_10 = 107
FRAME_death_11 = 108
FRAME_death_12 = 109
FRAME_death_13 = 110
FRAME_death_14 = 111
FRAME_death_15 = 112
FRAME_death_16 = 113
FRAME_death_17 = 114
FRAME_death_18 = 115
FRAME_death_19 = 116
FRAME_death_20 = 117
FRAME_death_21 = 118
FRAME_death_22 = 119
FRAME_death_23 = 120
FRAME_death_24 = 121
FRAME_death_31 = 122
FRAME_death_32 = 123
FRAME_death_33 = 124
FRAME_death_45 = 125
FRAME_death_46 = 126
FRAME_death_47 = 127
FRAME_forwrd_1 = 128
FRAME_forwrd_2 = 129
FRAME_forwrd_3 = 130
FRAME_forwrd_4 = 131
FRAME_forwrd_5 = 132
FRAME_forwrd_6 = 133
FRAME_forwrd_7 = 134
FRAME_forwrd_8 = 135
FRAME_forwrd_9 = 136
FRAME_forwrd_10 = 137
FRAME_forwrd_11 = 138
FRAME_forwrd_12 = 139
FRAME_forwrd_13 = 140
FRAME_forwrd_14 = 141
FRAME_forwrd_15 = 142
FRAME_forwrd_16 = 143
FRAME_forwrd_17 = 144
FRAME_forwrd_18 = 145
FRAME_left_1 = 146
FRAME_left_2 = 147
FRAME_left_3 = 148
FRAME_left_4 = 149
FRAME_left_5 = 150
FRAME_left_6 = 151
FRAME_left_7 = 152
FRAME_left_8 = 153
FRAME_left_9 = 154
FRAME_left_10 = 155
FRAME_left_11 = 156
FRAME_left_12 = 157
FRAME_left_13 = 158
FRAME_left_14 = 159
FRAME_left_15 = 160
FRAME_left_16 = 161
FRAME_left_17 = 162
FRAME_left_18 = 163
FRAME_pain1_1 = 164
FRAME_pain1_2 = 165
FRAME_pain1_3 = 166
FRAME_pain1_4 = 167
FRAME_pain2_5 = 168
FRAME_pain2_6 = 169
FRAME_pain2_7 = 170
FRAME_pain2_8 = 171
FRAME_pain3_9 = 172
FRAME_pain3_10 = 173
FRAME_pain3_11 = 174
FRAME_pain3_12 = 175
FRAME_right_1 = 176
FRAME_right_2 = 177
FRAME_right_3 = 178
FRAME_right_4 = 179
FRAME_right_5 = 180
FRAME_right_6 = 181
FRAME_right_7 = 182
FRAME_right_8 = 183
FRAME_right_9 = 184
FRAME_right_10 = 185
FRAME_right_11 = 186
FRAME_right_12 = 187
FRAME_right_13 = 188
FRAME_right_14 = 189
FRAME_right_15 = 190
FRAME_right_16 = 191
FRAME_right_17 = 192
FRAME_right_18 = 193
FRAME_stand_1 = 194
FRAME_stand_2 = 195
FRAME_stand_3 = 196
FRAME_stand_4 = 197
FRAME_stand_5 = 198
FRAME_stand_6 = 199
FRAME_stand_7 = 200
FRAME_stand_8 = 201
FRAME_stand_9 = 202
FRAME_stand_10 = 203
FRAME_stand_11 = 204
FRAME_stand_12 = 205
FRAME_stand_13 = 206
FRAME_stand_14 = 207
FRAME_stand_15 = 208
FRAME_stand_16 = 209
FRAME_stand_17 = 210
FRAME_stand_18 = 211
FRAME_stand_19 = 212
FRAME_stand_20 = 213
FRAME_stand_21 = 214
FRAME_stand_22 = 215
FRAME_stand_23 = 216
FRAME_stand_24 = 217
FRAME_stand_25 = 218
FRAME_stand_26 = 219
FRAME_stand_27 = 220
FRAME_stand_28 = 221
FRAME_stand_29 = 222
FRAME_stand_30 = 223
FRAME_stand_31 = 224
FRAME_stand_32 = 225
FRAME_stand_33 = 226
FRAME_stand_34 = 227
FRAME_stand_35 = 228
FRAME_stand_36 = 229
FRAME_stand_37 = 230
FRAME_stand_38 = 231
FRAME_stand_39 = 232
FRAME_stand_40 = 233
FRAME_stand_41 = 234
FRAME_stand_42 = 235
FRAME_stand_43 = 236
FRAME_stand_44 = 237
FRAME_stand_45 = 238
FRAME_stand_46 = 239
FRAME_stand_47 = 240
FRAME_stand_48 = 241
FRAME_stand_49 = 242
FRAME_stand_50 = 243
FRAME_stand_51 = 244
FRAME_stand_52 = 245
FRAME_stand_53 = 246
FRAME_stand_54 = 247
FRAME_stand_55 = 248
FRAME_stand_56 = 249
FRAME_stand_57 = 250
FRAME_stand_58 = 251
FRAME_stand_59 = 252
FRAME_stand_60 = 253
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
sound_pain3 = 0 # static
sound_death = 0 # static
sound_search1 = 0 # static
sound_search2 = 0 # static
tread_sound = 0 # static


"""
==============================================================================

SUPERTANK

==============================================================================
"""
def TreadSound (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, tread_sound, 1, ATTN_NORM, 0)


def supertank_search (self): #edict_t *

	if g_local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_search1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_search2, 1, ATTN_NORM, 0)


def supertank_stand (self): #edict_t *

	self.monsterinfo.currentmove = supertank_move_stand


def supertank_forward (self): #edict_t *

	self.monsterinfo.currentmove = supertank_move_forward


def supertank_walk (self): #edict_t *

	self.monsterinfo.currentmove = supertank_move_forward


def supertank_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = supertank_move_stand
	else:
		self.monsterinfo.currentmove = supertank_move_run


def supertank_reattack1 (self): #edict_t *

	if g_ai.visible(self, self.enemy):
		if g_local.random() < 0.9:
			self.monsterinfo.currentmove = supertank_move_attack1
		else:
			self.monsterinfo.currentmove = supertank_move_end_attack1
	else:
		self.monsterinfo.currentmove = supertank_move_end_attack1


def supertank_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	# Lessen the chance of him going into his pain frames
	if damage <=25:
		if g_local.random()<0.2:
			return

	# Don't go into pain if he's firing his rockets
	if g_main.skill.value >= 2:
		if (self.s.frame >= FRAME_attak2_1) and (self.s.frame <= FRAME_attak2_14):
			return

	self.pain_debounce_time = g_main.level.time + 3

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if damage <= 10:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM,0)
		self.monsterinfo.currentmove = supertank_move_pain1
	elif damage <= 25:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain3, 1, ATTN_NORM,0)
		self.monsterinfo.currentmove = supertank_move_pain2
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM,0)
		self.monsterinfo.currentmove = supertank_move_pain3


def supertankRocket (self): #edict_t *

	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	if self.s.frame == FRAME_attak2_8:
		flash_number = MZ2_SUPERTANK_ROCKET_1
	elif self.s.frame == FRAME_attak2_11:
		flash_number = MZ2_SUPERTANK_ROCKET_2
	else:
		# (self->s.frame == FRAME_attak2_14)
		flash_number = MZ2_SUPERTANK_ROCKET_3

	q_shared.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[flash_number], forward, right, start)

	q_shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	q_shared.VectorSubtract (vec, start, dir)
	q_shared.VectorNormalize (dir)

	monster_fire_rocket (self, start, dir, 50, 500, flash_number)


def supertankMachineGun (self): #edict_t *

	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	flash_number;

	flash_number = MZ2_SUPERTANK_MACHINEGUN_1 + (self.s.frame - FRAME_attak1_1)

	# FIXME!!!
	dir[0] = 0
	dir[1] = self.s.angles[1]
	dir[2] = 0

	q_shared.AngleVectors (dir, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[flash_number], forward, right, start)

	if self.enemy:
		q_shared.VectorCopy (self.enemy.s.origin, vec)
		q_shared.VectorMA (vec, 0, self.enemy.velocity, vec)
		vec[2] += self.enemy.viewheight
		q_shared.VectorSubtract (vec, start, forward)
		q_shared.VectorNormalize (forward)

	monster_fire_bullet (self, start, forward, 6, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)


def supertank_attack (self): #edict_t *

	vec = np.zeros((3,), dtype=np.float32) #vec3_t
	#float	range;
	# float	r;

	q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range = q_shared.VectorLength (vec)

	# r = random();

	# Attack 1 == Chaingun
	# Attack 2 == Rocket Launcher

	if range <= 160:
		self.monsterinfo.currentmove = supertank_move_attack1
	else:
		# fire rockets more often at distance
		if g_local.random() < 0.3:
			self.monsterinfo.currentmove = supertank_move_attack1
		else:
			self.monsterinfo.currentmove = supertank_move_attack2


def supertank_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -60, -60, 0)
	q_shared.VectorSet (self.maxs, 60, 60, 72)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def BossExplode (self):
	org = np.zeros((3,), dtype=np.float32)

	self.think = BossExplode
	q_shared.VectorCopy (self.s.origin, org)
	org[2] += 24 + (_r.randint(0, 2147483647) & 15)
	switch = self.count
	self.count += 1
	if switch == 0:
		org[0] -= 24
		org[1] -= 24
	elif switch == 1:
		org[0] += 24
		org[1] += 24
	elif switch == 2:
		org[0] += 24
		org[1] -= 24
	elif switch == 3:
		org[0] -= 24
		org[1] += 24
	elif switch == 4:
		org[0] -= 48
		org[1] -= 48
	elif switch == 5:
		org[0] += 48
		org[1] += 48
	elif switch == 6:
		org[0] -= 48
		org[1] += 48
	elif switch == 7:
		org[0] += 48
		org[1] -= 48
	elif switch == 8:
		self.s.sound = 0
		for n in range(4):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", 500, GIB_ORGANIC)
		for n in range(8):
			ThrowGib (self, "models/objects/gibs/sm_metal/tris.md2", 500, GIB_METALLIC)
		ThrowGib (self, "models/objects/gibs/chest/tris.md2", 500, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/gear/tris.md2", 500, GIB_METALLIC)
		self.deadflag = DEAD_DEAD
		return

	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_EXPLOSION1)
	g_main.gi.WritePosition (org)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)

	self.nextthink = g_main.level.time + 0.1


def supertank_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_NO
	self.count = 0
	self.monsterinfo.currentmove = supertank_move_death


"""QUAKED monster_supertank (1 .5 0) (-64 -64 0) (64 64 72) Ambush Trigger_Spawn Sight
"""
def SP_monster_supertank (self): #edict_t *

	global sound_pain1, sound_pain2, sound_pain3, sound_death, sound_search1, sound_search2, tread_sound
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("bosstank/btkpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("bosstank/btkpain2.wav")
	sound_pain3 = g_main.gi.soundindex ("bosstank/btkpain3.wav")
	sound_death = g_main.gi.soundindex ("bosstank/btkdeth1.wav")
	sound_search1 = g_main.gi.soundindex ("bosstank/btkunqv1.wav")
	sound_search2 = g_main.gi.soundindex ("bosstank/btkunqv2.wav")

	# self->s.sound = gi.soundindex ("bosstank/btkengn1.wav");
	tread_sound = g_main.gi.soundindex ("bosstank/btkengn1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/boss1/tris.md2")
	q_shared.VectorSet (self.mins, -64, -64, 0)
	q_shared.VectorSet (self.maxs, 64, 64, 112)

	self.health = 1500
	self.gib_health = -500
	self.mass = 800

	self.pain = supertank_pain
	self.die = supertank_die
	self.monsterinfo.stand = supertank_stand
	self.monsterinfo.walk = supertank_walk
	self.monsterinfo.run = supertank_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = supertank_attack
	self.monsterinfo.search = supertank_search
	self.monsterinfo.melee = None
	self.monsterinfo.sight = None

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = supertank_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start(self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
supertank_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
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
supertank_move_stand = _mm(FRAME_stand_1, FRAME_stand_60, supertank_frames_stand, None)

supertank_frames_run = [
	_mf(ai_run, 12, TreadSound),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 12, None),
]
supertank_move_run = _mm(FRAME_forwrd_1, FRAME_forwrd_18, supertank_frames_run, None)

supertank_frames_forward = [
	_mf(ai_walk, 4, TreadSound),
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
supertank_move_forward = _mm(FRAME_forwrd_1, FRAME_forwrd_18, supertank_frames_forward, None)

supertank_frames_turn_right = [
	_mf(ai_move, 0, TreadSound),
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
supertank_move_turn_right = _mm(FRAME_right_1, FRAME_right_18, supertank_frames_turn_right, supertank_run)

supertank_frames_turn_left = [
	_mf(ai_move, 0, TreadSound),
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
supertank_move_turn_left = _mm(FRAME_left_1, FRAME_left_18, supertank_frames_turn_left, supertank_run)

supertank_frames_pain3 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_pain3 = _mm(FRAME_pain3_9, FRAME_pain3_12, supertank_frames_pain3, supertank_run)

supertank_frames_pain2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_pain2 = _mm(FRAME_pain2_5, FRAME_pain2_8, supertank_frames_pain2, supertank_run)

supertank_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_pain1 = _mm(FRAME_pain1_1, FRAME_pain1_4, supertank_frames_pain1, supertank_run)

supertank_frames_death1 = [
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
	_mf(ai_move, 0, BossExplode),
]
supertank_move_death = _mm(FRAME_death_1, FRAME_death_24, supertank_frames_death1, supertank_dead)

supertank_frames_backward = [
	_mf(ai_walk, 0, TreadSound),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
]
supertank_move_backward = _mm(FRAME_backwd_1, FRAME_backwd_18, supertank_frames_backward, None)

supertank_frames_attack4 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
supertank_move_attack4 = _mm(FRAME_attak4_1, FRAME_attak4_6, supertank_frames_attack4, supertank_run)

supertank_frames_attack3 = [
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
supertank_move_attack3 = _mm(FRAME_attak3_1, FRAME_attak3_27, supertank_frames_attack3, supertank_run)

supertank_frames_attack2 = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, supertankRocket),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, supertankRocket),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, supertankRocket),
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
supertank_move_attack2 = _mm(FRAME_attak2_1, FRAME_attak2_27, supertank_frames_attack2, supertank_run)

supertank_frames_attack1 = [
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
	_mf(ai_charge, 0, supertankMachineGun),
]
supertank_move_attack1 = _mm(FRAME_attak1_1, FRAME_attak1_6, supertank_frames_attack1, supertank_reattack1)

supertank_frames_end_attack1 = [
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
supertank_move_end_attack1 = _mm(FRAME_attak1_7, FRAME_attak1_20, supertank_frames_end_attack1, supertank_run)


