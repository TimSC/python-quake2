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
from game.g_combat import (T_Damage)
from game.g_local import (AI_STAND_GROUND, DAMAGE_NO_KNOCKBACK, DEAD_DEAD, GIB_ORGANIC, MOD_UNKNOWN, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t, svc_temp_entity)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (walkmonster_start)
from game.g_utils import (G_FreeEdict, G_ProjectSource, vectoangles)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_VOICE, CHAN_WEAPON, MASK_SHOT, multicast_t, temp_event_t, vec3_origin)
DAMAGE_YES = damage_t.DAMAGE_YES.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_PARASITE_ATTACK = temp_event_t.TE_PARASITE_ATTACK.value

# m_parasite.h
FRAME_break01 = 0
FRAME_break02 = 1
FRAME_break03 = 2
FRAME_break04 = 3
FRAME_break05 = 4
FRAME_break06 = 5
FRAME_break07 = 6
FRAME_break08 = 7
FRAME_break09 = 8
FRAME_break10 = 9
FRAME_break11 = 10
FRAME_break12 = 11
FRAME_break13 = 12
FRAME_break14 = 13
FRAME_break15 = 14
FRAME_break16 = 15
FRAME_break17 = 16
FRAME_break18 = 17
FRAME_break19 = 18
FRAME_break20 = 19
FRAME_break21 = 20
FRAME_break22 = 21
FRAME_break23 = 22
FRAME_break24 = 23
FRAME_break25 = 24
FRAME_break26 = 25
FRAME_break27 = 26
FRAME_break28 = 27
FRAME_break29 = 28
FRAME_break30 = 29
FRAME_break31 = 30
FRAME_break32 = 31
FRAME_death101 = 32
FRAME_death102 = 33
FRAME_death103 = 34
FRAME_death104 = 35
FRAME_death105 = 36
FRAME_death106 = 37
FRAME_death107 = 38
FRAME_drain01 = 39
FRAME_drain02 = 40
FRAME_drain03 = 41
FRAME_drain04 = 42
FRAME_drain05 = 43
FRAME_drain06 = 44
FRAME_drain07 = 45
FRAME_drain08 = 46
FRAME_drain09 = 47
FRAME_drain10 = 48
FRAME_drain11 = 49
FRAME_drain12 = 50
FRAME_drain13 = 51
FRAME_drain14 = 52
FRAME_drain15 = 53
FRAME_drain16 = 54
FRAME_drain17 = 55
FRAME_drain18 = 56
FRAME_pain101 = 57
FRAME_pain102 = 58
FRAME_pain103 = 59
FRAME_pain104 = 60
FRAME_pain105 = 61
FRAME_pain106 = 62
FRAME_pain107 = 63
FRAME_pain108 = 64
FRAME_pain109 = 65
FRAME_pain110 = 66
FRAME_pain111 = 67
FRAME_run01 = 68
FRAME_run02 = 69
FRAME_run03 = 70
FRAME_run04 = 71
FRAME_run05 = 72
FRAME_run06 = 73
FRAME_run07 = 74
FRAME_run08 = 75
FRAME_run09 = 76
FRAME_run10 = 77
FRAME_run11 = 78
FRAME_run12 = 79
FRAME_run13 = 80
FRAME_run14 = 81
FRAME_run15 = 82
FRAME_stand01 = 83
FRAME_stand02 = 84
FRAME_stand03 = 85
FRAME_stand04 = 86
FRAME_stand05 = 87
FRAME_stand06 = 88
FRAME_stand07 = 89
FRAME_stand08 = 90
FRAME_stand09 = 91
FRAME_stand10 = 92
FRAME_stand11 = 93
FRAME_stand12 = 94
FRAME_stand13 = 95
FRAME_stand14 = 96
FRAME_stand15 = 97
FRAME_stand16 = 98
FRAME_stand17 = 99
FRAME_stand18 = 100
FRAME_stand19 = 101
FRAME_stand20 = 102
FRAME_stand21 = 103
FRAME_stand22 = 104
FRAME_stand23 = 105
FRAME_stand24 = 106
FRAME_stand25 = 107
FRAME_stand26 = 108
FRAME_stand27 = 109
FRAME_stand28 = 110
FRAME_stand29 = 111
FRAME_stand30 = 112
FRAME_stand31 = 113
FRAME_stand32 = 114
FRAME_stand33 = 115
FRAME_stand34 = 116
FRAME_stand35 = 117
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
sound_die = 0 # static
sound_launch = 0 # static
sound_impact = 0 # static
sound_suck = 0 # static
sound_reelin = 0 # static
sound_sight = 0 # static
sound_tap = 0 # static
sound_scratch = 0 # static
sound_search = 0 # static


"""
==============================================================================

parasite

==============================================================================
"""
def parasite_launch (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_launch, 1, ATTN_NORM, 0)


def parasite_reel_in (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_reelin, 1, ATTN_NORM, 0)


def parasite_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_sight, 1, ATTN_NORM, 0)


def parasite_tap (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_tap, 1, ATTN_IDLE, 0)


def parasite_scratch (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_scratch, 1, ATTN_IDLE, 0)


def parasite_search (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_search, 1, ATTN_IDLE, 0)


def parasite_end_fidget (self): #edict_t *

	self.monsterinfo.currentmove = parasite_move_end_fidget


def parasite_do_fidget (self): #edict_t *

	self.monsterinfo.currentmove = parasite_move_fidget


def parasite_refidget (self): #edict_t *

	if g_local.random() <= 0.8:
		self.monsterinfo.currentmove = parasite_move_fidget
	else:
		self.monsterinfo.currentmove = parasite_move_end_fidget


def parasite_idle (self): #edict_t *

	self.monsterinfo.currentmove = parasite_move_start_fidget


def parasite_stand (self): #edict_t *

	self.monsterinfo.currentmove = parasite_move_stand


def parasite_start_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = parasite_move_stand
	else:
		self.monsterinfo.currentmove = parasite_move_start_run


def parasite_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = parasite_move_stand
	else:
		self.monsterinfo.currentmove = parasite_move_run


def parasite_start_walk (self): #edict_t *

	self.monsterinfo.currentmove = parasite_move_start_walk


def parasite_walk (self): #edict_t *

	self.monsterinfo.currentmove = parasite_move_walk


def parasite_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if g_local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)

	self.monsterinfo.currentmove = parasite_move_pain1


def parasite_drain_attack_ok (start, end): #vec3_t, vec3_t

	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	angles = np.zeros((3,), dtype=np.float32) #vec3_t

	# check for max distance
	q_shared.VectorSubtract (start, end, dir)
	if q_shared.VectorLength(dir) > 256:
		return False

	# check for min/max pitch
	vectoangles (dir, angles)
	if angles[0] < -180:
		angles[0] += 360
	if abs(angles[0]) > 30:
		return False

	return True


def parasite_drain_attack (self): #edict_t *

	offset = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	f = np.zeros((3,), dtype=np.float32) #vec3_t
	r = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#trace_t	tr;
	#int	damage;

	q_shared.AngleVectors (self.s.angles, f, r, None)
	q_shared.VectorSet (offset, 24, 0, 6)
	G_ProjectSource (self.s.origin, offset, f, r, start)

	q_shared.VectorCopy (self.enemy.s.origin, end)
	if not parasite_drain_attack_ok(start, end):
		end[2] = self.enemy.s.origin[2] + self.enemy.maxs[2] - 8
		if not parasite_drain_attack_ok(start, end):
			end[2] = self.enemy.s.origin[2] + self.enemy.mins[2] + 8
			if not parasite_drain_attack_ok(start, end):
				return
	q_shared.VectorCopy (self.enemy.s.origin, end)

	tr = g_main.gi.trace (start, None, None, end, self, MASK_SHOT)
	if tr.ent != self.enemy:
		return

	if self.s.frame == FRAME_drain03:
		damage = 5
		g_main.gi.sound (self.enemy, CHAN_AUTO, sound_impact, 1, ATTN_NORM, 0)
	else:
		if self.s.frame == FRAME_drain04:
			g_main.gi.sound (self, CHAN_WEAPON, sound_suck, 1, ATTN_NORM, 0)
		damage = 2

	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_PARASITE_ATTACK)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WritePosition (start)
	g_main.gi.WritePosition (end)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)

	q_shared.VectorSubtract (start, end, dir)
	T_Damage (self.enemy, self, self, dir, self.enemy.s.origin, vec3_origin, damage, 0, DAMAGE_NO_KNOCKBACK, MOD_UNKNOWN)


def parasite_attack (self): #edict_t *

	# if (random() <= 0.2)
	# self->monsterinfo.currentmove = &parasite_move_break;
	# else
	self.monsterinfo.currentmove = parasite_move_drain


def parasite_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def parasite_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

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
	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.monsterinfo.currentmove = parasite_move_death


"""QUAKED monster_parasite (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_parasite (self): #edict_t *

	global sound_pain1, sound_pain2, sound_die, sound_launch, sound_impact, sound_suck, sound_reelin, sound_sight, sound_tap, sound_scratch, sound_search
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("parasite/parpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("parasite/parpain2.wav")
	sound_die = g_main.gi.soundindex ("parasite/pardeth1.wav")
	sound_launch = g_main.gi.soundindex("parasite/paratck1.wav")
	sound_impact = g_main.gi.soundindex("parasite/paratck2.wav")
	sound_suck = g_main.gi.soundindex("parasite/paratck3.wav")
	sound_reelin = g_main.gi.soundindex("parasite/paratck4.wav")
	sound_sight = g_main.gi.soundindex("parasite/parsght1.wav")
	sound_tap = g_main.gi.soundindex("parasite/paridle1.wav")
	sound_scratch = g_main.gi.soundindex("parasite/paridle2.wav")
	sound_search = g_main.gi.soundindex("parasite/parsrch1.wav")

	self.s.modelindex = g_main.gi.modelindex ("models/monsters/parasite/tris.md2")
	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, 24)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX

	self.health = 175
	self.gib_health = -50
	self.mass = 250

	self.pain = parasite_pain
	self.die = parasite_die

	self.monsterinfo.stand = parasite_stand
	self.monsterinfo.walk = parasite_start_walk
	self.monsterinfo.run = parasite_start_run
	self.monsterinfo.attack = parasite_attack
	self.monsterinfo.sight = parasite_sight
	self.monsterinfo.idle = parasite_idle

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = parasite_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start (self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
parasite_frames_start_fidget = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
parasite_move_start_fidget = _mm(FRAME_stand18, FRAME_stand21, parasite_frames_start_fidget, parasite_do_fidget)

parasite_frames_fidget = [
	_mf(ai_stand, 0, parasite_scratch),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_scratch),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
parasite_move_fidget = _mm(FRAME_stand22, FRAME_stand27, parasite_frames_fidget, parasite_refidget)

parasite_frames_end_fidget = [
	_mf(ai_stand, 0, parasite_scratch),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
parasite_move_end_fidget = _mm(FRAME_stand28, FRAME_stand35, parasite_frames_end_fidget, parasite_stand)

parasite_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
]
parasite_move_stand = _mm(FRAME_stand01, FRAME_stand17, parasite_frames_stand, parasite_stand)

parasite_frames_run = [
	_mf(ai_run, 30, None),
	_mf(ai_run, 30, None),
	_mf(ai_run, 22, None),
	_mf(ai_run, 19, None),
	_mf(ai_run, 24, None),
	_mf(ai_run, 28, None),
	_mf(ai_run, 25, None),
]
parasite_move_run = _mm(FRAME_run03, FRAME_run09, parasite_frames_run, None)

parasite_frames_start_run = [
	_mf(ai_run, 0, None),
	_mf(ai_run, 30, None),
]
parasite_move_start_run = _mm(FRAME_run01, FRAME_run02, parasite_frames_start_run, parasite_run)

parasite_frames_stop_run = [
	_mf(ai_run, 20, None),
	_mf(ai_run, 20, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 10, None),
	_mf(ai_run, 0, None),
	_mf(ai_run, 0, None),
]
parasite_move_stop_run = _mm(FRAME_run10, FRAME_run15, parasite_frames_stop_run, None)

parasite_frames_walk = [
	_mf(ai_walk, 30, None),
	_mf(ai_walk, 30, None),
	_mf(ai_walk, 22, None),
	_mf(ai_walk, 19, None),
	_mf(ai_walk, 24, None),
	_mf(ai_walk, 28, None),
	_mf(ai_walk, 25, None),
]
parasite_move_walk = _mm(FRAME_run03, FRAME_run09, parasite_frames_walk, parasite_walk)

parasite_frames_start_walk = [
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 30, parasite_walk),
]
parasite_move_start_walk = _mm(FRAME_run01, FRAME_run02, parasite_frames_start_walk, None)

parasite_frames_stop_walk = [
	_mf(ai_walk, 20, None),
	_mf(ai_walk, 20, None),
	_mf(ai_walk, 12, None),
	_mf(ai_walk, 10, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None),
]
parasite_move_stop_walk = _mm(FRAME_run10, FRAME_run15, parasite_frames_stop_walk, None)

parasite_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 16, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, 0, None),
]
parasite_move_pain1 = _mm(FRAME_pain101, FRAME_pain111, parasite_frames_pain1, parasite_start_run)

parasite_frames_drain = [
	_mf(ai_charge, 0, parasite_launch),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 15, parasite_drain_attack),	# Target hits
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, -2, parasite_drain_attack),	# drain
	_mf(ai_charge, -2, parasite_drain_attack),	# drain
	_mf(ai_charge, -3, parasite_drain_attack),	# drain
	_mf(ai_charge, -2, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, -1, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_reel_in),	# let go
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 0, None),
]
parasite_move_drain = _mm(FRAME_drain01, FRAME_drain18, parasite_frames_drain, parasite_start_run)

parasite_frames_break = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -18, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 9, None),
	_mf(ai_charge, 6, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -18, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 8, None),
	_mf(ai_charge, 9, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -18, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# airborne
	_mf(ai_charge, 0, None),	# airborne
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 11, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -5, None),
	_mf(ai_charge, 1, None),
]
parasite_move_break = _mm(FRAME_break01, FRAME_break32, parasite_frames_break, parasite_start_run)

parasite_frames_death = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
parasite_move_death = _mm(FRAME_death101, FRAME_death107, parasite_frames_death, parasite_dead)


