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
from game.g_local import (AI_STAND_GROUND, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t)
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (monster_fire_railgun, walkmonster_start)
from game.g_utils import (G_FreeEdict, G_ProjectSource)
from game.g_weapon import (fire_hit)
from game.game import (SOLID_BBOX, SVF_DEADMONSTER)
from game.q_shared import (ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_VOICE, CHAN_WEAPON, MZ2_GLADIATOR_RAILGUN_1)
DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_gladiator.h
FRAME_stand1 = 0
FRAME_stand2 = 1
FRAME_stand3 = 2
FRAME_stand4 = 3
FRAME_stand5 = 4
FRAME_stand6 = 5
FRAME_stand7 = 6
FRAME_walk1 = 7
FRAME_walk2 = 8
FRAME_walk3 = 9
FRAME_walk4 = 10
FRAME_walk5 = 11
FRAME_walk6 = 12
FRAME_walk7 = 13
FRAME_walk8 = 14
FRAME_walk9 = 15
FRAME_walk10 = 16
FRAME_walk11 = 17
FRAME_walk12 = 18
FRAME_walk13 = 19
FRAME_walk14 = 20
FRAME_walk15 = 21
FRAME_walk16 = 22
FRAME_run1 = 23
FRAME_run2 = 24
FRAME_run3 = 25
FRAME_run4 = 26
FRAME_run5 = 27
FRAME_run6 = 28
FRAME_melee1 = 29
FRAME_melee2 = 30
FRAME_melee3 = 31
FRAME_melee4 = 32
FRAME_melee5 = 33
FRAME_melee6 = 34
FRAME_melee7 = 35
FRAME_melee8 = 36
FRAME_melee9 = 37
FRAME_melee10 = 38
FRAME_melee11 = 39
FRAME_melee12 = 40
FRAME_melee13 = 41
FRAME_melee14 = 42
FRAME_melee15 = 43
FRAME_melee16 = 44
FRAME_melee17 = 45
FRAME_attack1 = 46
FRAME_attack2 = 47
FRAME_attack3 = 48
FRAME_attack4 = 49
FRAME_attack5 = 50
FRAME_attack6 = 51
FRAME_attack7 = 52
FRAME_attack8 = 53
FRAME_attack9 = 54
FRAME_pain1 = 55
FRAME_pain2 = 56
FRAME_pain3 = 57
FRAME_pain4 = 58
FRAME_pain5 = 59
FRAME_pain6 = 60
FRAME_death1 = 61
FRAME_death2 = 62
FRAME_death3 = 63
FRAME_death4 = 64
FRAME_death5 = 65
FRAME_death6 = 66
FRAME_death7 = 67
FRAME_death8 = 68
FRAME_death9 = 69
FRAME_death10 = 70
FRAME_death11 = 71
FRAME_death12 = 72
FRAME_death13 = 73
FRAME_death14 = 74
FRAME_death15 = 75
FRAME_death16 = 76
FRAME_death17 = 77
FRAME_death18 = 78
FRAME_death19 = 79
FRAME_death20 = 80
FRAME_death21 = 81
FRAME_death22 = 82
FRAME_painup1 = 83
FRAME_painup2 = 84
FRAME_painup3 = 85
FRAME_painup4 = 86
FRAME_painup5 = 87
FRAME_painup6 = 88
FRAME_painup7 = 89
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
sound_gun = 0 # static
sound_cleaver_swing = 0 # static
sound_cleaver_hit = 0 # static
sound_cleaver_miss = 0 # static
sound_idle = 0 # static
sound_search = 0 # static
sound_sight = 0 # static


"""
==============================================================================

GLADIATOR

==============================================================================
"""
def gladiator_idle (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def gladiator_sight (self, other): #edict_t *, edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def gladiator_search (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def gladiator_cleaver_swing (self): #edict_t *

	g_main.gi.sound (self, CHAN_WEAPON, sound_cleaver_swing, 1, ATTN_NORM, 0)


def gladiator_stand (self): #edict_t *

	self.monsterinfo.currentmove = gladiator_move_stand


def gladiator_walk (self): #edict_t *

	self.monsterinfo.currentmove = gladiator_move_walk


def gladiator_run (self): #edict_t *

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = gladiator_move_stand
	else:
		self.monsterinfo.currentmove = gladiator_move_run


def GaldiatorMelee (self): #edict_t *

	aim = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.VectorSet (aim, MELEE_DISTANCE, self.mins[0], -4)
	if fire_hit (self, aim, (20 + (_r.randint(0, 2147483647) %5)), 300):
		g_main.gi.sound (self, CHAN_AUTO, sound_cleaver_hit, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_AUTO, sound_cleaver_miss, 1, ATTN_NORM, 0)


def gladiator_melee (self): #edict_t *

	self.monsterinfo.currentmove = gladiator_move_attack_melee


def GladiatorGun (self): #edict_t *

	start = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t

	q_shared.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[MZ2_GLADIATOR_RAILGUN_1], forward, right, start)

	# calc direction to where we targted
	q_shared.VectorSubtract (self.pos1, start, dir)
	q_shared.VectorNormalize (dir)

	monster_fire_railgun (self, start, dir, 50, 100, MZ2_GLADIATOR_RAILGUN_1)


def gladiator_attack (self): #edict_t *

	#float	range;
	v = np.zeros((3,), dtype=np.float32) #vec3_t

	# a small safe zone
	q_shared.VectorSubtract (self.s.origin, self.enemy.s.origin, v)
	range = q_shared.VectorLength(v)
	if range <= (MELEE_DISTANCE + 32):
		return

	# charge up the railgun
	g_main.gi.sound (self, CHAN_WEAPON, sound_gun, 1, ATTN_NORM, 0)
	q_shared.VectorCopy (self.enemy.s.origin, self.pos1)	# save for aiming the shot
	self.pos1[2] += self.enemy.viewheight
	self.monsterinfo.currentmove = gladiator_move_attack_gun


def gladiator_pain (self, other, kick, damage): #edict_t *, edict_t *, float, int

	if self.health < (self.max_health // 2):
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		if (self.velocity[2] > 100) and (self.monsterinfo.currentmove == gladiator_move_pain):
			self.monsterinfo.currentmove = gladiator_move_pain_air
		return

	self.pain_debounce_time = g_main.level.time + 3

	if g_local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)

	if g_main.skill.value == 3:
		return	# no pain anims in nightmare

	if self.velocity[2] > 100:
		self.monsterinfo.currentmove = gladiator_move_pain_air
	else:
		self.monsterinfo.currentmove = gladiator_move_pain


def gladiator_dead (self): #edict_t *

	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def gladiator_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

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

	self.monsterinfo.currentmove = gladiator_move_death


"""QUAKED monster_gladiator (1 .5 0) (-32 -32 -24) (32 32 64) Ambush Trigger_Spawn Sight
"""
def SP_monster_gladiator (self): #edict_t *

	global sound_pain1, sound_pain2, sound_die, sound_gun, sound_cleaver_swing, sound_cleaver_hit, sound_cleaver_miss, sound_idle, sound_search, sound_sight
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("gladiator/pain.wav")
	sound_pain2 = g_main.gi.soundindex ("gladiator/gldpain2.wav")
	sound_die = g_main.gi.soundindex ("gladiator/glddeth2.wav")
	sound_gun = g_main.gi.soundindex ("gladiator/railgun.wav")
	sound_cleaver_swing = g_main.gi.soundindex ("gladiator/melee1.wav")
	sound_cleaver_hit = g_main.gi.soundindex ("gladiator/melee2.wav")
	sound_cleaver_miss = g_main.gi.soundindex ("gladiator/melee3.wav")
	sound_idle = g_main.gi.soundindex ("gladiator/gldidle1.wav")
	sound_search = g_main.gi.soundindex ("gladiator/gldsrch1.wav")
	sound_sight = g_main.gi.soundindex ("gladiator/sight.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/gladiatr/tris.md2")
	q_shared.VectorSet (self.mins, -32, -32, -24)
	q_shared.VectorSet (self.maxs, 32, 32, 64)

	self.health = 400
	self.gib_health = -175
	self.mass = 400

	self.pain = gladiator_pain
	self.die = gladiator_die

	self.monsterinfo.stand = gladiator_stand
	self.monsterinfo.walk = gladiator_walk
	self.monsterinfo.run = gladiator_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = gladiator_attack
	self.monsterinfo.melee = gladiator_melee
	self.monsterinfo.sight = gladiator_sight
	self.monsterinfo.idle = gladiator_idle
	self.monsterinfo.search = gladiator_search

	g_main.gi.linkentity (self)
	self.monsterinfo.currentmove = gladiator_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start (self)



# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
gladiator_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
gladiator_move_stand = _mm(FRAME_stand1, FRAME_stand7, gladiator_frames_stand, None)

gladiator_frames_walk = [
	_mf(ai_walk, 15, None),
	_mf(ai_walk, 7, None),
	_mf(ai_walk, 6, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 8, None),
	_mf(ai_walk, 12, None),
	_mf(ai_walk, 8, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 5, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 2, None),
	_mf(ai_walk, 1, None),
	_mf(ai_walk, 8, None),
]
gladiator_move_walk = _mm(FRAME_walk1, FRAME_walk16, gladiator_frames_walk, None)

gladiator_frames_run = [
	_mf(ai_run, 23, None),
	_mf(ai_run, 14, None),
	_mf(ai_run, 14, None),
	_mf(ai_run, 21, None),
	_mf(ai_run, 12, None),
	_mf(ai_run, 13, None),
]
gladiator_move_run = _mm(FRAME_run1, FRAME_run6, gladiator_frames_run, None)

gladiator_frames_attack_melee = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, gladiator_cleaver_swing),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GaldiatorMelee),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, gladiator_cleaver_swing),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GaldiatorMelee),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
gladiator_move_attack_melee = _mm(FRAME_melee1, FRAME_melee17, gladiator_frames_attack_melee, gladiator_run)

gladiator_frames_attack_gun = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GladiatorGun),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
gladiator_move_attack_gun = _mm(FRAME_attack1, FRAME_attack9, gladiator_frames_attack_gun, gladiator_run)

gladiator_frames_pain = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
gladiator_move_pain = _mm(FRAME_pain1, FRAME_pain6, gladiator_frames_pain, gladiator_run)

gladiator_frames_pain_air = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
gladiator_move_pain_air = _mm(FRAME_painup1, FRAME_painup7, gladiator_frames_pain_air, gladiator_run)

gladiator_frames_death = [
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
gladiator_move_death = _mm(FRAME_death1, FRAME_death22, gladiator_frames_death, gladiator_dead)


