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
from game import g_main, g_local, q_shared, m_flash
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_local import (AI_DUCKED, AI_HOLD_FRAME, AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, POWER_ARMOR_NONE, POWER_ARMOR_SCREEN, damage_t)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (walkmonster_start)
from game.g_utils import (G_FreeEdict)
from game.g_weapon import (fire_hit)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_BODY, CHAN_VOICE, CHAN_WEAPON)
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_brain.h
FRAME_walk101 = 0
FRAME_walk102 = 1
FRAME_walk103 = 2
FRAME_walk104 = 3
FRAME_walk105 = 4
FRAME_walk106 = 5
FRAME_walk107 = 6
FRAME_walk108 = 7
FRAME_walk109 = 8
FRAME_walk110 = 9
FRAME_walk111 = 10
FRAME_walk112 = 11
FRAME_walk113 = 12
FRAME_walk201 = 13
FRAME_walk202 = 14
FRAME_walk203 = 15
FRAME_walk204 = 16
FRAME_walk205 = 17
FRAME_walk206 = 18
FRAME_walk207 = 19
FRAME_walk208 = 20
FRAME_walk209 = 21
FRAME_walk210 = 22
FRAME_walk211 = 23
FRAME_walk212 = 24
FRAME_walk213 = 25
FRAME_walk214 = 26
FRAME_walk215 = 27
FRAME_walk216 = 28
FRAME_walk217 = 29
FRAME_walk218 = 30
FRAME_walk219 = 31
FRAME_walk220 = 32
FRAME_walk221 = 33
FRAME_walk222 = 34
FRAME_walk223 = 35
FRAME_walk224 = 36
FRAME_walk225 = 37
FRAME_walk226 = 38
FRAME_walk227 = 39
FRAME_walk228 = 40
FRAME_walk229 = 41
FRAME_walk230 = 42
FRAME_walk231 = 43
FRAME_walk232 = 44
FRAME_walk233 = 45
FRAME_walk234 = 46
FRAME_walk235 = 47
FRAME_walk236 = 48
FRAME_walk237 = 49
FRAME_walk238 = 50
FRAME_walk239 = 51
FRAME_walk240 = 52
FRAME_attak101 = 53
FRAME_attak102 = 54
FRAME_attak103 = 55
FRAME_attak104 = 56
FRAME_attak105 = 57
FRAME_attak106 = 58
FRAME_attak107 = 59
FRAME_attak108 = 60
FRAME_attak109 = 61
FRAME_attak110 = 62
FRAME_attak111 = 63
FRAME_attak112 = 64
FRAME_attak113 = 65
FRAME_attak114 = 66
FRAME_attak115 = 67
FRAME_attak116 = 68
FRAME_attak117 = 69
FRAME_attak118 = 70
FRAME_attak201 = 71
FRAME_attak202 = 72
FRAME_attak203 = 73
FRAME_attak204 = 74
FRAME_attak205 = 75
FRAME_attak206 = 76
FRAME_attak207 = 77
FRAME_attak208 = 78
FRAME_attak209 = 79
FRAME_attak210 = 80
FRAME_attak211 = 81
FRAME_attak212 = 82
FRAME_attak213 = 83
FRAME_attak214 = 84
FRAME_attak215 = 85
FRAME_attak216 = 86
FRAME_attak217 = 87
FRAME_pain101 = 88
FRAME_pain102 = 89
FRAME_pain103 = 90
FRAME_pain104 = 91
FRAME_pain105 = 92
FRAME_pain106 = 93
FRAME_pain107 = 94
FRAME_pain108 = 95
FRAME_pain109 = 96
FRAME_pain110 = 97
FRAME_pain111 = 98
FRAME_pain112 = 99
FRAME_pain113 = 100
FRAME_pain114 = 101
FRAME_pain115 = 102
FRAME_pain116 = 103
FRAME_pain117 = 104
FRAME_pain118 = 105
FRAME_pain119 = 106
FRAME_pain120 = 107
FRAME_pain121 = 108
FRAME_pain201 = 109
FRAME_pain202 = 110
FRAME_pain203 = 111
FRAME_pain204 = 112
FRAME_pain205 = 113
FRAME_pain206 = 114
FRAME_pain207 = 115
FRAME_pain208 = 116
FRAME_pain301 = 117
FRAME_pain302 = 118
FRAME_pain303 = 119
FRAME_pain304 = 120
FRAME_pain305 = 121
FRAME_pain306 = 122
FRAME_death101 = 123
FRAME_death102 = 124
FRAME_death103 = 125
FRAME_death104 = 126
FRAME_death105 = 127
FRAME_death106 = 128
FRAME_death107 = 129
FRAME_death108 = 130
FRAME_death109 = 131
FRAME_death110 = 132
FRAME_death111 = 133
FRAME_death112 = 134
FRAME_death113 = 135
FRAME_death114 = 136
FRAME_death115 = 137
FRAME_death116 = 138
FRAME_death117 = 139
FRAME_death118 = 140
FRAME_death201 = 141
FRAME_death202 = 142
FRAME_death203 = 143
FRAME_death204 = 144
FRAME_death205 = 145
FRAME_duck01 = 146
FRAME_duck02 = 147
FRAME_duck03 = 148
FRAME_duck04 = 149
FRAME_duck05 = 150
FRAME_duck06 = 151
FRAME_duck07 = 152
FRAME_duck08 = 153
FRAME_defens01 = 154
FRAME_defens02 = 155
FRAME_defens03 = 156
FRAME_defens04 = 157
FRAME_defens05 = 158
FRAME_defens06 = 159
FRAME_defens07 = 160
FRAME_defens08 = 161
FRAME_stand01 = 162
FRAME_stand02 = 163
FRAME_stand03 = 164
FRAME_stand04 = 165
FRAME_stand05 = 166
FRAME_stand06 = 167
FRAME_stand07 = 168
FRAME_stand08 = 169
FRAME_stand09 = 170
FRAME_stand10 = 171
FRAME_stand11 = 172
FRAME_stand12 = 173
FRAME_stand13 = 174
FRAME_stand14 = 175
FRAME_stand15 = 176
FRAME_stand16 = 177
FRAME_stand17 = 178
FRAME_stand18 = 179
FRAME_stand19 = 180
FRAME_stand20 = 181
FRAME_stand21 = 182
FRAME_stand22 = 183
FRAME_stand23 = 184
FRAME_stand24 = 185
FRAME_stand25 = 186
FRAME_stand26 = 187
FRAME_stand27 = 188
FRAME_stand28 = 189
FRAME_stand29 = 190
FRAME_stand30 = 191
FRAME_stand31 = 192
FRAME_stand32 = 193
FRAME_stand33 = 194
FRAME_stand34 = 195
FRAME_stand35 = 196
FRAME_stand36 = 197
FRAME_stand37 = 198
FRAME_stand38 = 199
FRAME_stand39 = 200
FRAME_stand40 = 201
FRAME_stand41 = 202
FRAME_stand42 = 203
FRAME_stand43 = 204
FRAME_stand44 = 205
FRAME_stand45 = 206
FRAME_stand46 = 207
FRAME_stand47 = 208
FRAME_stand48 = 209
FRAME_stand49 = 210
FRAME_stand50 = 211
FRAME_stand51 = 212
FRAME_stand52 = 213
FRAME_stand53 = 214
FRAME_stand54 = 215
FRAME_stand55 = 216
FRAME_stand56 = 217
FRAME_stand57 = 218
FRAME_stand58 = 219
FRAME_stand59 = 220
FRAME_stand60 = 221
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

sound_chest_open = 0 # static
sound_tentacles_extend = 0 # static
sound_tentacles_retract = 0 # static
sound_death = 0 # static
sound_idle1 = 0 # static
sound_idle2 = 0 # static
sound_idle3 = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_sight = 0 # static
sound_search = 0 # static
sound_melee1 = 0 # static
sound_melee2 = 0 # static
sound_melee3 = 0 # static


"""
==============================================================================

brain

==============================================================================
"""
def brain_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def brain_search (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def brain_stand (self): #edict_t *

	self.monsterinfo.currentmove = brain_move_stand


def brain_idle (self): #edict_t *

	g_main.gi.sound (self, CHAN_AUTO, sound_idle3, 1, ATTN_IDLE, 0)
	self.monsterinfo.currentmove = brain_move_idle


def brain_walk (self): #edict_t *

	# if (random() <= 0.5)
	self.monsterinfo.currentmove = brain_move_walk1
	# else
	# self->monsterinfo.currentmove = &brain_move_walk2;


def brain_duck_down (self): #edict_t *

	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	g_main.gi.linkentity (self)


def brain_duck_hold (self): #edict_t *

	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME


def brain_duck_up (self): #edict_t *

	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)


def brain_dodge (self, attacker, eta): #edict_t *, edict_t *, float

	if g_local.random() > 0.25:
		return

	if not self.enemy:
		self.enemy = attacker

	self.monsterinfo.pausetime = g_main.level.time + eta + 0.5
	self.monsterinfo.currentmove = brain_move_duck


def brain_swing_right (self): #edict_t *

	g_main.gi.sound (self, CHAN_BODY, sound_melee1, 1, ATTN_NORM, 0)


def brain_hit_right (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSet (aim, MELEE_DISTANCE, self.maxs[0], 8)
	if fire_hit (self, aim, (15 + (_r.randint(0, 2147483647) %5)), 40):
		g_main.gi.sound (self, CHAN_WEAPON, sound_melee3, 1, ATTN_NORM, 0)


def brain_swing_left (self): #edict_t *

	g_main.gi.sound (self, CHAN_BODY, sound_melee2, 1, ATTN_NORM, 0)


def brain_hit_left (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSet (aim, MELEE_DISTANCE, self.mins[0], 8)
	if fire_hit (self, aim, (15 + (_r.randint(0, 2147483647) %5)), 40):
		g_main.gi.sound (self, CHAN_WEAPON, sound_melee3, 1, ATTN_NORM, 0)


def brain_chest_open (self): #edict_t *

	self.spawnflags &= ~65536
	self.monsterinfo.power_armor_type = POWER_ARMOR_NONE
	g_main.gi.sound (self, CHAN_BODY, sound_chest_open, 1, ATTN_NORM, 0)


def brain_tentacle_attack (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSet (aim, MELEE_DISTANCE, 0, 8)
	if fire_hit (self, aim, (10 + (_r.randint(0, 2147483647) %5)), -600) and g_main.skill.value > 0:
		self.spawnflags |= 65536
	g_main.gi.sound (self, CHAN_WEAPON, sound_tentacles_retract, 1, ATTN_NORM, 0)


def brain_chest_closed (self): #edict_t *

	self.monsterinfo.power_armor_type = POWER_ARMOR_SCREEN
	if self.spawnflags & 65536:
		self.spawnflags &= ~65536
		self.monsterinfo.currentmove = brain_move_attack1


def brain_melee (self): #edict_t *

	if g_local.random() <= 0.5:
		self.monsterinfo.currentmove = brain_move_attack1
	else:
		self.monsterinfo.currentmove = brain_move_attack2


def brain_run (self): #edict_t *

	self.monsterinfo.power_armor_type = POWER_ARMOR_SCREEN
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = brain_move_stand
	else:
		self.monsterinfo.currentmove = brain_move_run


def brain_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	#float	r;

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	r = g_local.random()
	if r < 0.33:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = brain_move_pain1
	elif r < 0.66:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = brain_move_pain2
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = brain_move_pain3


def brain_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def brain_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	self.s.effects = 0
	self.monsterinfo.power_armor_type = POWER_ARMOR_NONE

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
	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	if g_local.random() <= 0.5:
		self.monsterinfo.currentmove = brain_move_death1
	else:
		self.monsterinfo.currentmove = brain_move_death2


"""QUAKED monster_brain (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_brain (self): #edict_t *

	global sound_chest_open, sound_tentacles_extend, sound_tentacles_retract, sound_death, sound_idle1, sound_idle2, sound_idle3, sound_pain1, sound_pain2, sound_sight, sound_search, sound_melee1, sound_melee2, sound_melee3
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_chest_open = g_main.gi.soundindex ("brain/brnatck1.wav")
	sound_tentacles_extend = g_main.gi.soundindex ("brain/brnatck2.wav")
	sound_tentacles_retract = g_main.gi.soundindex ("brain/brnatck3.wav")
	sound_death = g_main.gi.soundindex ("brain/brndeth1.wav")
	sound_idle1 = g_main.gi.soundindex ("brain/brnidle1.wav")
	sound_idle2 = g_main.gi.soundindex ("brain/brnidle2.wav")
	sound_idle3 = g_main.gi.soundindex ("brain/brnlens1.wav")
	sound_pain1 = g_main.gi.soundindex ("brain/brnpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("brain/brnpain2.wav")
	sound_sight = g_main.gi.soundindex ("brain/brnsght1.wav")
	sound_search = g_main.gi.soundindex ("brain/brnsrch1.wav")
	sound_melee1 = g_main.gi.soundindex ("brain/melee1.wav")
	sound_melee2 = g_main.gi.soundindex ("brain/melee2.wav")
	sound_melee3 = g_main.gi.soundindex ("brain/melee3.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/brain/tris.md2")
	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, 32)

	self.health = 300
	self.gib_health = -150
	self.mass = 400

	self.pain = brain_pain
	self.die = brain_die

	self.monsterinfo.stand = brain_stand
	self.monsterinfo.walk = brain_walk
	self.monsterinfo.run = brain_run
	self.monsterinfo.dodge = brain_dodge
	# self->monsterinfo.attack = brain_attack;
	self.monsterinfo.melee = brain_melee
	self.monsterinfo.sight = brain_sight
	self.monsterinfo.search = brain_search
	self.monsterinfo.idle = brain_idle

	self.monsterinfo.power_armor_type = POWER_ARMOR_SCREEN
	self.monsterinfo.power_armor_power = 100

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = brain_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start (self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
brain_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
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
brain_move_stand = _mm(FRAME_stand01, FRAME_stand30, brain_frames_stand, None)

brain_frames_idle = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
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
brain_move_idle = _mm(FRAME_stand31, FRAME_stand60, brain_frames_idle, brain_stand)

brain_frames_walk1 = [
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 3, None),
	_mf(ai_walk, 1, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 9, None),
	_mf(ai_walk, -4, None),
	_mf(ai_walk, -1, None),
	_mf(ai_walk, 2, None),
]
brain_move_walk1 = _mm(FRAME_walk101, FRAME_walk111, brain_frames_walk1, None)

"""
#if 0
void brain_walk2_cycle (edict_t *self)
{
	if (random() > 0.1)
		self->monsterinfo.nextframe = FRAME_walk220;
}

mframe_t brain_frames_walk2 [] =
{
	ai_walk,	3,	NULL,
	ai_walk,	-2,	NULL,
	ai_walk,	-4,	NULL,
	ai_walk,	-3,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	1,	NULL,
	ai_walk,	12,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	-3,	NULL,
	ai_walk,	0,	NULL,

	ai_walk,	-2,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	1,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	10,	NULL,		

	ai_walk,	-1,	NULL,
	ai_walk,	7,	NULL,
	ai_walk,	0,	NULL,
	ai_walk,	3,	NULL,
	ai_walk,	-3,	NULL,
	ai_walk,	2,	NULL,
	ai_walk,	4,	NULL,
	ai_walk,	-3,	NULL,
	ai_walk,	2,	NULL,
	ai_walk,	0,	NULL,

	ai_walk,	4,	brain_walk2_cycle,
	ai_walk,	-1,	NULL,
	ai_walk,	-1,	NULL,
	ai_walk,	-8,	NULL,		
	ai_walk,	0,	NULL,
	ai_walk,	1,	NULL,
	ai_walk,	5,	NULL,
	ai_walk,	2,	NULL,
	ai_walk,	-1,	NULL,
	ai_walk,	-5,	NULL
};
mmove_t brain_move_walk2 = {FRAME_walk201, FRAME_walk240, brain_frames_walk2, NULL};
#endif
"""
brain_frames_defense = [
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
brain_move_defense = _mm(FRAME_defens01, FRAME_defens08, brain_frames_defense, None)

brain_frames_pain3 = [
	_mf(ai_move, -2, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -4, None),
]
brain_move_pain3 = _mm(FRAME_pain301, FRAME_pain306, brain_frames_pain3, brain_run)

brain_frames_pain2 = [
	_mf(ai_move, -2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, -2, None),
]
brain_move_pain2 = _mm(FRAME_pain201, FRAME_pain208, brain_frames_pain2, brain_run)

brain_frames_pain1 = [
	_mf(ai_move, -6, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, -6, None),
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
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 7, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, -1, None),
]
brain_move_pain1 = _mm(FRAME_pain101, FRAME_pain121, brain_frames_pain1, brain_run)

brain_frames_duck = [
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, brain_duck_down),
	_mf(ai_move, 17, brain_duck_hold),
	_mf(ai_move, -3, None),
	_mf(ai_move, -1, brain_duck_up),
	_mf(ai_move, -5, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -6, None),
]
brain_move_duck = _mm(FRAME_duck01, FRAME_duck08, brain_frames_duck, brain_run)

brain_frames_death2 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 9, None),
	_mf(ai_move, 0, None),
]
brain_move_death2 = _mm(FRAME_death201, FRAME_death205, brain_frames_death2, brain_dead)

brain_frames_death1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 9, None),
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
brain_move_death1 = _mm(FRAME_death101, FRAME_death118, brain_frames_death1, brain_dead)

brain_frames_attack1 = [
	_mf(ai_charge, 8, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 5, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -3, brain_swing_right),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -5, None),
	_mf(ai_charge, -7, brain_hit_right),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 6, brain_swing_left),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 2, brain_hit_left),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 6, None),
	_mf(ai_charge, -1, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, -11, None),
]
brain_move_attack1 = _mm(FRAME_attak101, FRAME_attak118, brain_frames_attack1, brain_run)

brain_frames_attack2 = [
	_mf(ai_charge, 5, None),
	_mf(ai_charge, -4, None),
	_mf(ai_charge, -4, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 0, brain_chest_open),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 13, brain_tentacle_attack),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -9, brain_chest_closed),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, -6, None),
]
brain_move_attack2 = _mm(FRAME_attak201, FRAME_attak217, brain_frames_attack2, brain_run)

brain_frames_run = [
	_mf(ai_run, 9, None),
	_mf(ai_run, 2, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 3, None),
	_mf(ai_run, 1, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, -4, None),
	_mf(ai_run, -1, None),
	_mf(ai_run, 2, None),
]
brain_move_run = _mm(FRAME_walk101, FRAME_walk111, brain_frames_run, None)


