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
from game import g_main, g_ai, g_spawn
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_ai import (FoundTarget, M_CheckAttack)
from game.header.local import AI_DUCKED, AI_GOOD_GUY, AI_HOLD_FRAME, AI_MEDIC, AI_RESURRECTING, AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t, svc_temp_entity
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_blaster, walkmonster_start)
from game.g_utils import findradius, G_FreeEdict, G_ProjectSource, vectoangles
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER, SVF_MONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_VOICE, CHAN_WEAPON, EF_BLASTER, EF_HYPERBLASTER, MASK_SHOT, MZ2_MEDIC_BLASTER_1, multicast_t, temp_event_t
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
DAMAGE_YES = damage_t.DAMAGE_YES.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_MEDIC_CABLE_ATTACK = temp_event_t.TE_MEDIC_CABLE_ATTACK.value

# m_medic.h
FRAME_walk1 = 0
FRAME_walk2 = 1
FRAME_walk3 = 2
FRAME_walk4 = 3
FRAME_walk5 = 4
FRAME_walk6 = 5
FRAME_walk7 = 6
FRAME_walk8 = 7
FRAME_walk9 = 8
FRAME_walk10 = 9
FRAME_walk11 = 10
FRAME_walk12 = 11
FRAME_wait1 = 12
FRAME_wait2 = 13
FRAME_wait3 = 14
FRAME_wait4 = 15
FRAME_wait5 = 16
FRAME_wait6 = 17
FRAME_wait7 = 18
FRAME_wait8 = 19
FRAME_wait9 = 20
FRAME_wait10 = 21
FRAME_wait11 = 22
FRAME_wait12 = 23
FRAME_wait13 = 24
FRAME_wait14 = 25
FRAME_wait15 = 26
FRAME_wait16 = 27
FRAME_wait17 = 28
FRAME_wait18 = 29
FRAME_wait19 = 30
FRAME_wait20 = 31
FRAME_wait21 = 32
FRAME_wait22 = 33
FRAME_wait23 = 34
FRAME_wait24 = 35
FRAME_wait25 = 36
FRAME_wait26 = 37
FRAME_wait27 = 38
FRAME_wait28 = 39
FRAME_wait29 = 40
FRAME_wait30 = 41
FRAME_wait31 = 42
FRAME_wait32 = 43
FRAME_wait33 = 44
FRAME_wait34 = 45
FRAME_wait35 = 46
FRAME_wait36 = 47
FRAME_wait37 = 48
FRAME_wait38 = 49
FRAME_wait39 = 50
FRAME_wait40 = 51
FRAME_wait41 = 52
FRAME_wait42 = 53
FRAME_wait43 = 54
FRAME_wait44 = 55
FRAME_wait45 = 56
FRAME_wait46 = 57
FRAME_wait47 = 58
FRAME_wait48 = 59
FRAME_wait49 = 60
FRAME_wait50 = 61
FRAME_wait51 = 62
FRAME_wait52 = 63
FRAME_wait53 = 64
FRAME_wait54 = 65
FRAME_wait55 = 66
FRAME_wait56 = 67
FRAME_wait57 = 68
FRAME_wait58 = 69
FRAME_wait59 = 70
FRAME_wait60 = 71
FRAME_wait61 = 72
FRAME_wait62 = 73
FRAME_wait63 = 74
FRAME_wait64 = 75
FRAME_wait65 = 76
FRAME_wait66 = 77
FRAME_wait67 = 78
FRAME_wait68 = 79
FRAME_wait69 = 80
FRAME_wait70 = 81
FRAME_wait71 = 82
FRAME_wait72 = 83
FRAME_wait73 = 84
FRAME_wait74 = 85
FRAME_wait75 = 86
FRAME_wait76 = 87
FRAME_wait77 = 88
FRAME_wait78 = 89
FRAME_wait79 = 90
FRAME_wait80 = 91
FRAME_wait81 = 92
FRAME_wait82 = 93
FRAME_wait83 = 94
FRAME_wait84 = 95
FRAME_wait85 = 96
FRAME_wait86 = 97
FRAME_wait87 = 98
FRAME_wait88 = 99
FRAME_wait89 = 100
FRAME_wait90 = 101
FRAME_run1 = 102
FRAME_run2 = 103
FRAME_run3 = 104
FRAME_run4 = 105
FRAME_run5 = 106
FRAME_run6 = 107
FRAME_paina1 = 108
FRAME_paina2 = 109
FRAME_paina3 = 110
FRAME_paina4 = 111
FRAME_paina5 = 112
FRAME_paina6 = 113
FRAME_paina7 = 114
FRAME_paina8 = 115
FRAME_painb1 = 116
FRAME_painb2 = 117
FRAME_painb3 = 118
FRAME_painb4 = 119
FRAME_painb5 = 120
FRAME_painb6 = 121
FRAME_painb7 = 122
FRAME_painb8 = 123
FRAME_painb9 = 124
FRAME_painb10 = 125
FRAME_painb11 = 126
FRAME_painb12 = 127
FRAME_painb13 = 128
FRAME_painb14 = 129
FRAME_painb15 = 130
FRAME_duck1 = 131
FRAME_duck2 = 132
FRAME_duck3 = 133
FRAME_duck4 = 134
FRAME_duck5 = 135
FRAME_duck6 = 136
FRAME_duck7 = 137
FRAME_duck8 = 138
FRAME_duck9 = 139
FRAME_duck10 = 140
FRAME_duck11 = 141
FRAME_duck12 = 142
FRAME_duck13 = 143
FRAME_duck14 = 144
FRAME_duck15 = 145
FRAME_duck16 = 146
FRAME_death1 = 147
FRAME_death2 = 148
FRAME_death3 = 149
FRAME_death4 = 150
FRAME_death5 = 151
FRAME_death6 = 152
FRAME_death7 = 153
FRAME_death8 = 154
FRAME_death9 = 155
FRAME_death10 = 156
FRAME_death11 = 157
FRAME_death12 = 158
FRAME_death13 = 159
FRAME_death14 = 160
FRAME_death15 = 161
FRAME_death16 = 162
FRAME_death17 = 163
FRAME_death18 = 164
FRAME_death19 = 165
FRAME_death20 = 166
FRAME_death21 = 167
FRAME_death22 = 168
FRAME_death23 = 169
FRAME_death24 = 170
FRAME_death25 = 171
FRAME_death26 = 172
FRAME_death27 = 173
FRAME_death28 = 174
FRAME_death29 = 175
FRAME_death30 = 176
FRAME_attack1 = 177
FRAME_attack2 = 178
FRAME_attack3 = 179
FRAME_attack4 = 180
FRAME_attack5 = 181
FRAME_attack6 = 182
FRAME_attack7 = 183
FRAME_attack8 = 184
FRAME_attack9 = 185
FRAME_attack10 = 186
FRAME_attack11 = 187
FRAME_attack12 = 188
FRAME_attack13 = 189
FRAME_attack14 = 190
FRAME_attack15 = 191
FRAME_attack16 = 192
FRAME_attack17 = 193
FRAME_attack18 = 194
FRAME_attack19 = 195
FRAME_attack20 = 196
FRAME_attack21 = 197
FRAME_attack22 = 198
FRAME_attack23 = 199
FRAME_attack24 = 200
FRAME_attack25 = 201
FRAME_attack26 = 202
FRAME_attack27 = 203
FRAME_attack28 = 204
FRAME_attack29 = 205
FRAME_attack30 = 206
FRAME_attack31 = 207
FRAME_attack32 = 208
FRAME_attack33 = 209
FRAME_attack34 = 210
FRAME_attack35 = 211
FRAME_attack36 = 212
FRAME_attack37 = 213
FRAME_attack38 = 214
FRAME_attack39 = 215
FRAME_attack40 = 216
FRAME_attack41 = 217
FRAME_attack42 = 218
FRAME_attack43 = 219
FRAME_attack44 = 220
FRAME_attack45 = 221
FRAME_attack46 = 222
FRAME_attack47 = 223
FRAME_attack48 = 224
FRAME_attack49 = 225
FRAME_attack50 = 226
FRAME_attack51 = 227
FRAME_attack52 = 228
FRAME_attack53 = 229
FRAME_attack54 = 230
FRAME_attack55 = 231
FRAME_attack56 = 232
FRAME_attack57 = 233
FRAME_attack58 = 234
FRAME_attack59 = 235
FRAME_attack60 = 236
MODEL_SCALE = 1.000000


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

sound_idle1 = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_die = 0 # static
sound_sight = 0 # static
sound_search = 0 # static
sound_hook_launch = 0 # static
sound_hook_hit = 0 # static
sound_hook_heal = 0 # static
sound_hook_retract = 0 # static


"""
==============================================================================

MEDIC

==============================================================================
"""
def medic_FindDeadMonster (self): #edict_t *

	ent = None #edict_t	*
	best = None #edict_t	*

	# while ((ent = findradius(ent, self->s.origin, 1024)) != NULL)
	while True:
		ent = findradius(ent, self.s.origin, 1024)
		if ent is None:
			break
		if ent == self:
			continue
		if not (ent.svflags & SVF_MONSTER):
			continue
		if ent.monsterinfo.aiflags & AI_GOOD_GUY:
			continue
		if ent.owner:
			continue
		if ent.health > 0:
			continue
		if ent.nextthink:
			continue
		if not g_ai.visible(self, ent):
			continue
		if not best:
			best = ent
			continue
		if ent.max_health <= best.max_health:
			continue
		best = ent

	return best


def medic_idle (self): #edict_t *

	#edict_t	*	ent;

	g_main.gi.sound (self, CHAN_VOICE, sound_idle1, 1, ATTN_IDLE, 0)

	ent = medic_FindDeadMonster(self)
	if ent:
		self.enemy = ent
		self.enemy.owner = self
		self.monsterinfo.aiflags |= AI_MEDIC
		FoundTarget (self)


def medic_search (self): #edict_t *

	#edict_t	*	ent;

	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_IDLE, 0)

	if not self.oldenemy:
		ent = medic_FindDeadMonster(self)
		if ent:
			self.oldenemy = self.enemy
			self.enemy = ent
			self.enemy.owner = self
			self.monsterinfo.aiflags |= AI_MEDIC
			FoundTarget (self)


def medic_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def medic_stand (self): #edict_t *

	self.monsterinfo.currentmove = medic_move_stand


def medic_walk (self): #edict_t *

	self.monsterinfo.currentmove = medic_move_walk


def medic_run (self): #edict_t *

	if not (self.monsterinfo.aiflags & AI_MEDIC):
		#edict_t	*	ent;

		ent = medic_FindDeadMonster(self)
		if ent:
			self.oldenemy = self.enemy
			self.enemy = ent
			self.enemy.owner = self
			self.monsterinfo.aiflags |= AI_MEDIC
			FoundTarget (self)
			return

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = medic_move_stand
	else:
		self.monsterinfo.currentmove = medic_move_run


def medic_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if local.random() < 0.5:
		self.monsterinfo.currentmove = medic_move_pain1
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
	else:
		self.monsterinfo.currentmove = medic_move_pain2
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)


def medic_fire_blaster (self): #edict_t *

	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#int	effect;

	if (self.s.frame == FRAME_attack9) or (self.s.frame == FRAME_attack12):
		effect = EF_BLASTER
	elif (self.s.frame == FRAME_attack19) or (self.s.frame == FRAME_attack22) or (self.s.frame == FRAME_attack25) or (self.s.frame == FRAME_attack28):
		effect = EF_HYPERBLASTER
	else:
		effect = 0

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_MEDIC_BLASTER_1], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] += self.enemy.viewheight
	shared.VectorSubtract (end, start, dir)

	monster_fire_blaster (self, start, dir, 2, 1000, MZ2_MEDIC_BLASTER_1, effect)


def medic_dead (self): #edict_t *

	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def medic_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# if we had a pending patient, free him up for another medic
	if (self.enemy) and (self.enemy.owner == self):
		self.enemy.owner = None

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
	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	self.monsterinfo.currentmove = medic_move_death


def medic_duck_down (self): #edict_t *

	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity (self)


def medic_duck_hold (self): #edict_t *

	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME


def medic_duck_up (self): #edict_t *

	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)


def medic_dodge (self, attacker, eta): #edict_t *, edict_t *, float

	if local.random() > 0.25:
		return

	if not self.enemy:
		self.enemy = attacker

	self.monsterinfo.currentmove = medic_move_duck


def medic_continue (self): #edict_t *

	if g_ai.visible (self, self.enemy):
		if local.random() <= 0.95:
			self.monsterinfo.currentmove = medic_move_attackHyperBlaster


def medic_hook_launch (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_hook_launch, 1, ATTN_NORM, 0)


medic_cable_offsets = [ # static vec3_t []
	np.array([45.0,  -9.2, 15.5], dtype=np.float32),
	np.array([48.4,  -9.7, 15.2], dtype=np.float32),
	np.array([47.8,  -9.8, 15.8], dtype=np.float32),
	np.array([47.3,  -9.3, 14.3], dtype=np.float32),
	np.array([45.4, -10.1, 13.1], dtype=np.float32),
	np.array([41.9, -12.7, 12.0], dtype=np.float32),
	np.array([37.8, -15.8, 11.2], dtype=np.float32),
	np.array([34.3, -18.4, 10.7], dtype=np.float32),
	np.array([32.7, -19.7, 10.4], dtype=np.float32),
	np.array([32.7, -19.7, 10.4], dtype=np.float32)
]

def medic_cable_attack (self): #edict_t *

	offset = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	f = np.zeros((3,), dtype=np.float32) #vec3_t
	r = np.zeros((3,), dtype=np.float32) #vec3_t
	#trace_t	tr;
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	angles = np.zeros((3,), dtype=np.float32) #vec3_t
	#float	distance;

	if not self.enemy.inuse:
		return

	shared_c.AngleVectors (self.s.angles, f, r, None)
	shared.VectorCopy (medic_cable_offsets[self.s.frame - FRAME_attack42], offset)
	G_ProjectSource (self.s.origin, offset, f, r, start)

	# check for max distance
	shared.VectorSubtract (start, self.enemy.s.origin, dir)
	distance = shared_c.VectorLength(dir)
	if distance > 256:
		return

	# check for min/max pitch
	vectoangles (dir, angles)
	if angles[0] < -180:
		angles[0] += 360
	if abs(angles[0]) > 45:
		return

	tr = g_main.gi.trace (start, None, None, self.enemy.s.origin, self, MASK_SHOT)
	if tr.fraction != 1.0 and tr.ent != self.enemy:
		return

	if self.s.frame == FRAME_attack43:
		g_main.gi.sound (self.enemy, CHAN_AUTO, sound_hook_hit, 1, ATTN_NORM, 0)
		self.enemy.monsterinfo.aiflags |= AI_RESURRECTING
	elif self.s.frame == FRAME_attack50:
		self.enemy.spawnflags = 0
		self.enemy.monsterinfo.aiflags = 0
		self.enemy.target = None
		self.enemy.targetname = None
		self.enemy.combattarget = None
		self.enemy.deathtarget = None
		self.enemy.owner = self
		g_spawn.ED_CallSpawn (self.enemy)
		self.enemy.owner = None
		if self.enemy.think:
			self.enemy.nextthink = g_main.level.time
			self.enemy.think (self.enemy)
		self.enemy.monsterinfo.aiflags |= AI_RESURRECTING
		if self.oldenemy and self.oldenemy.client:
			self.enemy.enemy = self.oldenemy
			FoundTarget (self.enemy)
	else:
		if self.s.frame == FRAME_attack44:
			g_main.gi.sound (self, CHAN_WEAPON, sound_hook_heal, 1, ATTN_NORM, 0)

	# adjust start for beam origin being in middle of a segment
	shared_c.VectorMA (start, 8, f, start)

	# adjust end z for end spot since the monster is currently dead
	shared.VectorCopy (self.enemy.s.origin, end)
	end[2] = self.enemy.absmin[2] + self.enemy.size[2] / 2

	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_MEDIC_CABLE_ATTACK)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WritePosition (start)
	g_main.gi.WritePosition (end)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)


def medic_hook_retract (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_hook_retract, 1, ATTN_NORM, 0)
	self.enemy.monsterinfo.aiflags &= ~AI_RESURRECTING


def medic_attack (self): #edict_t *

	if self.monsterinfo.aiflags & AI_MEDIC:
		self.monsterinfo.currentmove = medic_move_attackCable
	else:
		self.monsterinfo.currentmove = medic_move_attackBlaster


def medic_checkattack (self): #edict_t *

	if self.monsterinfo.aiflags & AI_MEDIC:
		medic_attack(self)
		return True

	return M_CheckAttack (self)


"""QUAKED monster_medic (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_medic (self): #edict_t *

	global sound_idle1, sound_pain1, sound_pain2, sound_die, sound_sight, sound_search, sound_hook_launch, sound_hook_hit, sound_hook_heal, sound_hook_retract
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_idle1 = g_main.gi.soundindex ("medic/idle.wav")
	sound_pain1 = g_main.gi.soundindex ("medic/medpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("medic/medpain2.wav")
	sound_die = g_main.gi.soundindex ("medic/meddeth1.wav")
	sound_sight = g_main.gi.soundindex ("medic/medsght1.wav")
	sound_search = g_main.gi.soundindex ("medic/medsrch1.wav")
	sound_hook_launch = g_main.gi.soundindex ("medic/medatck2.wav")
	sound_hook_hit = g_main.gi.soundindex ("medic/medatck3.wav")
	sound_hook_heal = g_main.gi.soundindex ("medic/medatck4.wav")
	sound_hook_retract = g_main.gi.soundindex ("medic/medatck5.wav")

	g_main.gi.soundindex ("medic/medatck1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/medic/tris.md2")
	shared.VectorSet (self.mins, -24, -24, -24)
	shared.VectorSet (self.maxs, 24, 24, 32)

	self.health = 300
	self.gib_health = -130
	self.mass = 400

	self.pain = medic_pain
	self.die = medic_die

	self.monsterinfo.stand = medic_stand
	self.monsterinfo.walk = medic_walk
	self.monsterinfo.run = medic_run
	self.monsterinfo.dodge = medic_dodge
	self.monsterinfo.attack = medic_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = medic_sight
	self.monsterinfo.idle = medic_idle
	self.monsterinfo.search = medic_search
	self.monsterinfo.checkattack = medic_checkattack

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = medic_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start (self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
medic_frames_stand = [
	_mf(ai_stand, 0, medic_idle),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
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
medic_move_stand = _mm(FRAME_wait1, FRAME_wait90, medic_frames_stand, None)

medic_frames_walk = [
	_mf(ai_walk, 6.2, None),
	_mf(ai_walk, 18.1, None),
	_mf(ai_walk, 1, None),
	_mf(ai_walk, 9, None),
	_mf(ai_walk, 10, None),
	_mf(ai_walk, 9, None),
	_mf(ai_walk, 11, None),
	_mf(ai_walk, 11.6, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 9.9, None),
	_mf(ai_walk, 14, None),
	_mf(ai_walk, 9.3, None),
]
medic_move_walk = _mm(FRAME_walk1, FRAME_walk12, medic_frames_walk, None)

medic_frames_run = [
	_mf(ai_run, 18, None),
	_mf(ai_run, 22.5, None),
	_mf(ai_run, 25.4, None),
	_mf(ai_run, 23.4, None),
	_mf(ai_run, 24, None),
	_mf(ai_run, 35.6, None),
]
medic_move_run = _mm(FRAME_run1, FRAME_run6, medic_frames_run, None)

medic_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
medic_move_pain1 = _mm(FRAME_paina1, FRAME_paina8, medic_frames_pain1, medic_run)

medic_frames_pain2 = [
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
medic_move_pain2 = _mm(FRAME_painb1, FRAME_painb15, medic_frames_pain2, medic_run)

medic_frames_death = [
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
medic_move_death = _mm(FRAME_death1, FRAME_death30, medic_frames_death, medic_dead)

medic_frames_duck = [
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, medic_duck_down),
	_mf(ai_move, -1, medic_duck_hold),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, medic_duck_up),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
]
medic_move_duck = _mm(FRAME_duck1, FRAME_duck16, medic_frames_duck, medic_run)

medic_frames_attackHyperBlaster = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, medic_fire_blaster),
]
medic_move_attackHyperBlaster = _mm(FRAME_attack15, FRAME_attack30, medic_frames_attackHyperBlaster, medic_run)

medic_frames_attackBlaster = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 5, None),
	_mf(ai_charge, 5, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, medic_fire_blaster),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, medic_continue),	# Change to medic_continue... Else, go to frame 32
]
medic_move_attackBlaster = _mm(FRAME_attack1, FRAME_attack14, medic_frames_attackBlaster, medic_run)

medic_frames_attackCable = [
	_mf(ai_move, 2, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, 4.4, None),
	_mf(ai_charge, 4.7, None),
	_mf(ai_charge, 5, None),
	_mf(ai_charge, 6, None),
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 0, None),
	_mf(ai_move, 0, medic_hook_launch),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, 0, medic_cable_attack),
	_mf(ai_move, -15, medic_hook_retract),
	_mf(ai_move, -1.5, None),
	_mf(ai_move, -1.2, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 0.3, None),
	_mf(ai_move, 0.7, None),
	_mf(ai_move, 1.2, None),
	_mf(ai_move, 1.3, None),
]
medic_move_attackCable = _mm(FRAME_attack33, FRAME_attack60, medic_frames_attackCable, medic_run)


