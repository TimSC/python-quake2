#
# Copyright (C) 1997-2001 Id Software, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
from __future__ import annotations

import random as _r
import numpy as np
from game import g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict
from game.g_monster import monster_fire_bullet, walkmonster_start
from game.g_weapon import fire_hit
from game.g_misc import ThrowGib, ThrowHead
from common.header.shared import CHAN_VOICE, CHAN_WEAPON, CHAN_BODY, ATTN_NORM, ATTN_IDLE, MZ2_INFANTRY_MACHINEGUN_1, MZ2_INFANTRY_MACHINEGUN_2
from game.header.local import FRAMETIME, MELEE_DISTANCE, GIB_ORGANIC, DEAD_DEAD, MOVETYPE_STEP, MOVETYPE_TOSS, AI_STAND_GROUND, AI_HOLD_FRAME, AI_DUCKED, RANGE_MELEE, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, damage_t
DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.header.game import solid_t, SVF_DEADMONSTER
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local

SOLID_BBOX = solid_t.SOLID_BBOX.value

MODEL_SCALE = 1.000000

sound_pain1 = 0
sound_pain2 = 0
sound_die1 = 0
sound_die2 = 0
sound_gunshot = 0
sound_weapon_cock = 0
sound_punch_swing = 0
sound_punch_hit = 0
sound_sight = 0
sound_search = 0
sound_idle = 0

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

FRAME_stand50      = 50
FRAME_stand71      = 71
FRAME_stand01      = 1
FRAME_stand49      = 49
FRAME_walk03       = 74
FRAME_walk14       = 85
FRAME_run01        = 92
FRAME_run08        = 99
FRAME_pain101      = 100
FRAME_pain110      = 109
FRAME_pain201      = 110
FRAME_pain210      = 119
FRAME_duck01       = 120
FRAME_duck05       = 124
FRAME_death101     = 125
FRAME_death120     = 144
FRAME_death201     = 145
FRAME_death211     = 155
FRAME_death225     = 169
FRAME_death301     = 170
FRAME_death309     = 178
FRAME_attak101     = 184
FRAME_attak111     = 194
FRAME_attak115     = 198
FRAME_attak201     = 199
FRAME_attak208     = 206
"""
/*
==============================================================================

INFANTRY

==============================================================================
*/

#include "g_local.h"
#include "m_infantry.h"

vec3_t	aimangles[] =
{
	0.0, 5.0, 0.0,
	10.0, 15.0, 0.0,
	20.0, 25.0, 0.0,
	25.0, 35.0, 0.0,
	30.0, 40.0, 0.0,
	30.0, 45.0, 0.0,
	25.0, 50.0, 0.0,
	20.0, 40.0, 0.0,
	15.0, 35.0, 0.0,
	40.0, 35.0, 0.0,
	70.0, 35.0, 0.0,
	90.0, 35.0, 0.0
};

"""

aimangles = [
	[0.0, 5.0, 0.0],
	[10.0, 15.0, 0.0],
	[20.0, 25.0, 0.0],
	[25.0, 35.0, 0.0],
	[30.0, 40.0, 0.0],
	[30.0, 45.0, 0.0],
	[25.0, 50.0, 0.0],
	[20.0, 40.0, 0.0],
	[15.0, 35.0, 0.0],
	[40.0, 35.0, 0.0],
	[70.0, 35.0, 0.0],
	[90.0, 35.0, 0.0],
]

def infantry_stand (self):
	#edict_t *self
	self.monsterinfo.currentmove = infantry_move_stand

def infantry_fidget (self):
	#edict_t *self
	self.monsterinfo.currentmove = infantry_move_fidget
	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)

def infantry_walk (self):
	#edict_t *self
	self.monsterinfo.currentmove = infantry_move_walk

def infantry_run (self):
	#edict_t *self
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = infantry_move_stand
	else:
		self.monsterinfo.currentmove = infantry_move_run

def infantry_pain (self, other, kick, damage):
	#edict_t *self, *other; float kick; int damage
	n = 0

	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3

	if g_main.skill.value == 3:
		return  # no pain anims in nightmare

	n = _r.randint(0, 2147483647) % 2
	if n == 0:
		self.monsterinfo.currentmove = infantry_move_pain1
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
	else:
		self.monsterinfo.currentmove = infantry_move_pain2
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)

def InfantryMachineGun (self):
	#edict_t *self
	global sound_gunshot
	start = [0.0, 0.0, 0.0]
	target = [0.0, 0.0, 0.0]
	forward = [0.0, 0.0, 0.0]
	right = [0.0, 0.0, 0.0]
	vec = [0.0, 0.0, 0.0]
	flash_number = 0

	if self.s.frame == FRAME_attak111:
		flash_number = MZ2_INFANTRY_MACHINEGUN_1
		shared_c.AngleVectors (self.s.angles, forward, right, None)
		G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

		if self.enemy:
			shared_c.VectorMA (self.enemy.s.origin, -0.2, self.enemy.velocity, target)
			target[2] += self.enemy.viewheight
			shared.VectorSubtract (target, start, forward)
			shared_c.VectorNormalize (forward)
		else:
			shared_c.AngleVectors (self.s.angles, forward, right, None)
	else:
		flash_number = MZ2_INFANTRY_MACHINEGUN_2 + (self.s.frame - FRAME_death211)

		shared_c.AngleVectors (self.s.angles, forward, right, None)
		G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

		shared.VectorSubtract (self.s.angles, aimangles[flash_number - MZ2_INFANTRY_MACHINEGUN_2], vec)
		shared_c.AngleVectors (vec, forward, None, None)

	monster_fire_bullet (self, start, forward, 3, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)

def infantry_sight (self, other):
	#edict_t *self, *other
	g_main.gi.sound (self, CHAN_BODY, sound_sight, 1, ATTN_NORM, 0)

def infantry_dead (self):
	#edict_t *self
	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	g_main.gi.linkentity (self)

	g_monster.M_FlyCheck (self)

def infantry_die (self, inflictor, attacker, damage, point):
	#edict_t *self, *inflictor, *attacker; int damage; vec3_t point
	n = 0

	# check for gib
	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(2):
			ThrowGib (self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)
		for n in range(4):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	# regular death
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	n = _r.randint(0, 2147483647) % 3
	if n == 0:
		self.monsterinfo.currentmove = infantry_move_death1
		g_main.gi.sound (self, CHAN_VOICE, sound_die2, 1, ATTN_NORM, 0)
	elif n == 1:
		self.monsterinfo.currentmove = infantry_move_death2
		g_main.gi.sound (self, CHAN_VOICE, sound_die1, 1, ATTN_NORM, 0)
	else:
		self.monsterinfo.currentmove = infantry_move_death3
		g_main.gi.sound (self, CHAN_VOICE, sound_die2, 1, ATTN_NORM, 0)

def infantry_duck_down (self):
	#edict_t *self
	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity (self)

def infantry_duck_hold (self):
	#edict_t *self
	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME

def infantry_duck_up (self):
	#edict_t *self
	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)

def infantry_dodge (self, attacker, eta):
	#edict_t *self, *attacker; float eta
	if local.random() > 0.25:
		return

	if not self.enemy:
		self.enemy = attacker

	self.monsterinfo.currentmove = infantry_move_duck

def infantry_cock_gun (self):
	#edict_t *self
	global sound_weapon_cock
	n = 0

	g_main.gi.sound (self, CHAN_WEAPON, sound_weapon_cock, 1, ATTN_NORM, 0)
	n = (_r.randint(0, 2147483647) & 15) + 3 + 7
	self.monsterinfo.pausetime = g_main.level.time + n * FRAMETIME

def infantry_fire (self):
	#edict_t *self
	InfantryMachineGun (self)

	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME

def infantry_swing (self):
	#edict_t *self
	g_main.gi.sound (self, CHAN_WEAPON, sound_punch_swing, 1, ATTN_NORM, 0)

def infantry_smack (self):
	#edict_t *self
	global sound_punch_hit
	aim = [0.0, 0.0, 0.0]

	shared.VectorSet (aim, MELEE_DISTANCE, 0, 0)
	if fire_hit (self, aim, (5 + (_r.randint(0, 2147483647) % 5)), 50):
		g_main.gi.sound (self, CHAN_WEAPON, sound_punch_hit, 1, ATTN_NORM, 0)

def infantry_attack (self):
	#edict_t *self
	if g_ai.range (self, self.enemy) == RANGE_MELEE:
		self.monsterinfo.currentmove = infantry_move_attack2
	else:
		self.monsterinfo.currentmove = infantry_move_attack1

"""
QUAKED monster_infantry (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_infantry (self):
	#edict_t *self
	global sound_pain1, sound_pain2, sound_die1, sound_die2
	global sound_gunshot, sound_weapon_cock, sound_punch_swing, sound_punch_hit
	global sound_sight, sound_search, sound_idle

	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("infantry/infpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("infantry/infpain2.wav")
	sound_die1 = g_main.gi.soundindex ("infantry/infdeth1.wav")
	sound_die2 = g_main.gi.soundindex ("infantry/infdeth2.wav")

	sound_gunshot = g_main.gi.soundindex ("infantry/infatck1.wav")
	sound_weapon_cock = g_main.gi.soundindex ("infantry/infatck3.wav")
	sound_punch_swing = g_main.gi.soundindex ("infantry/infatck2.wav")
	sound_punch_hit = g_main.gi.soundindex ("infantry/melee2.wav")

	sound_sight = g_main.gi.soundindex ("infantry/infsght1.wav")
	sound_search = g_main.gi.soundindex ("infantry/infsrch1.wav")
	sound_idle = g_main.gi.soundindex ("infantry/infidle1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/infantry/tris.md2")
	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, 32)

	self.health = 100
	self.gib_health = -40
	self.mass = 200

	self.pain = infantry_pain
	self.die = infantry_die

	self.monsterinfo.stand = infantry_stand
	self.monsterinfo.walk = infantry_walk
	self.monsterinfo.run = infantry_run
	self.monsterinfo.dodge = infantry_dodge
	self.monsterinfo.attack = infantry_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = infantry_sight
	self.monsterinfo.idle = infantry_fidget

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = infantry_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start (self)

#=================
# move tables
#=================
infantry_frames_stand = [_mf(ai_stand, 0, None)] * 22
infantry_move_stand = _mm(FRAME_stand50, FRAME_stand71, infantry_frames_stand, None)

infantry_frames_fidget = [
	_mf(ai_stand, 1, None), _mf(ai_stand, 0, None), _mf(ai_stand, 1, None),
	_mf(ai_stand, 3, None), _mf(ai_stand, 6, None), _mf(ai_stand, 3, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 1, None), _mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None),
	_mf(ai_stand, 1, None), _mf(ai_stand, 0, None), _mf(ai_stand, -1, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 1, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, -2, None), _mf(ai_stand, 1, None),
	_mf(ai_stand, 1, None), _mf(ai_stand, 1, None), _mf(ai_stand, -1, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, -1, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, -1, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 1, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, -1, None),
	_mf(ai_stand, -1, None), _mf(ai_stand, 0, None), _mf(ai_stand, -3, None),
	_mf(ai_stand, -2, None), _mf(ai_stand, -3, None), _mf(ai_stand, -3, None),
	_mf(ai_stand, -2, None)]
infantry_move_fidget = _mm(FRAME_stand01, FRAME_stand49, infantry_frames_fidget, infantry_stand)

infantry_frames_walk = [
	_mf(ai_walk, 5, None), _mf(ai_walk, 4, None), _mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None), _mf(ai_walk, 4, None), _mf(ai_walk, 5, None),
	_mf(ai_walk, 6, None), _mf(ai_walk, 4, None), _mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None), _mf(ai_walk, 4, None), _mf(ai_walk, 5, None)]
infantry_move_walk = _mm(FRAME_walk03, FRAME_walk14, infantry_frames_walk, None)

infantry_frames_run = [
	_mf(ai_run, 10, None), _mf(ai_run, 20, None), _mf(ai_run, 5, None),
	_mf(ai_run, 7, None), _mf(ai_run, 30, None), _mf(ai_run, 35, None),
	_mf(ai_run, 2, None), _mf(ai_run, 6, None)]
infantry_move_run = _mm(FRAME_run01, FRAME_run08, infantry_frames_run, None)

infantry_frames_pain1 = [
	_mf(ai_move, -3, None), _mf(ai_move, -2, None), _mf(ai_move, -1, None),
	_mf(ai_move, -2, None), _mf(ai_move, -1, None), _mf(ai_move, 1, None),
	_mf(ai_move, -1, None), _mf(ai_move, 1, None), _mf(ai_move, 6, None),
	_mf(ai_move, 2, None)]
infantry_move_pain1 = _mm(FRAME_pain101, FRAME_pain110, infantry_frames_pain1, infantry_run)

infantry_frames_pain2 = [
	_mf(ai_move, -3, None), _mf(ai_move, -3, None), _mf(ai_move, 0, None),
	_mf(ai_move, -1, None), _mf(ai_move, -2, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 2, None), _mf(ai_move, 5, None),
	_mf(ai_move, 2, None)]
infantry_move_pain2 = _mm(FRAME_pain201, FRAME_pain210, infantry_frames_pain2, infantry_run)

infantry_frames_death1 = [
	_mf(ai_move, -4, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, -1, None), _mf(ai_move, -4, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -1, None),
	_mf(ai_move, 3, None), _mf(ai_move, 1, None), _mf(ai_move, 1, None),
	_mf(ai_move, -2, None), _mf(ai_move, 2, None), _mf(ai_move, 2, None),
	_mf(ai_move, 9, None), _mf(ai_move, 9, None), _mf(ai_move, 5, None),
	_mf(ai_move, -3, None), _mf(ai_move, -3, None)]
infantry_move_death1 = _mm(FRAME_death101, FRAME_death120, infantry_frames_death1, infantry_dead)

infantry_frames_death2 = [
	_mf(ai_move, 0, None), _mf(ai_move, 1, None), _mf(ai_move, 5, None),
	_mf(ai_move, -1, None), _mf(ai_move, 0, None), _mf(ai_move, 1, None),
	_mf(ai_move, 1, None), _mf(ai_move, 4, None), _mf(ai_move, 3, None),
	_mf(ai_move, 0, None), _mf(ai_move, -2, InfantryMachineGun),
	_mf(ai_move, -2, InfantryMachineGun), _mf(ai_move, -3, InfantryMachineGun),
	_mf(ai_move, -1, InfantryMachineGun), _mf(ai_move, -2, InfantryMachineGun),
	_mf(ai_move, 0, InfantryMachineGun), _mf(ai_move, 2, InfantryMachineGun),
	_mf(ai_move, 2, InfantryMachineGun), _mf(ai_move, 3, InfantryMachineGun),
	_mf(ai_move, -10, InfantryMachineGun), _mf(ai_move, -7, InfantryMachineGun),
	_mf(ai_move, -8, InfantryMachineGun), _mf(ai_move, -6, None),
	_mf(ai_move, 4, None), _mf(ai_move, 0, None)]
infantry_move_death2 = _mm(FRAME_death201, FRAME_death225, infantry_frames_death2, infantry_dead)

infantry_frames_death3 = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, -6, None), _mf(ai_move, -11, None), _mf(ai_move, -3, None),
	_mf(ai_move, -11, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
infantry_move_death3 = _mm(FRAME_death301, FRAME_death309, infantry_frames_death3, infantry_dead)

infantry_frames_duck = [
	_mf(ai_move, -2, infantry_duck_down), _mf(ai_move, -5, infantry_duck_hold),
	_mf(ai_move, 3, None), _mf(ai_move, 4, infantry_duck_up),
	_mf(ai_move, 0, None)]
infantry_move_duck = _mm(FRAME_duck01, FRAME_duck05, infantry_frames_duck, infantry_run)

infantry_frames_attack1 = [
	_mf(ai_charge, 4, None), _mf(ai_charge, -1, None), _mf(ai_charge, -1, None),
	_mf(ai_charge, 0, infantry_cock_gun), _mf(ai_charge, -1, None),
	_mf(ai_charge, 1, None), _mf(ai_charge, 1, None), _mf(ai_charge, 2, None),
	_mf(ai_charge, -2, None), _mf(ai_charge, -3, None), _mf(ai_charge, 1, infantry_fire),
	_mf(ai_charge, 5, None), _mf(ai_charge, -1, None), _mf(ai_charge, -2, None),
	_mf(ai_charge, -3, None)]
infantry_move_attack1 = _mm(FRAME_attak101, FRAME_attak115, infantry_frames_attack1, infantry_run)

infantry_frames_attack2 = [
	_mf(ai_charge, 3, None), _mf(ai_charge, 6, None), _mf(ai_charge, 0, infantry_swing),
	_mf(ai_charge, 8, None), _mf(ai_charge, 5, None), _mf(ai_charge, 8, infantry_smack),
	_mf(ai_charge, 6, None), _mf(ai_charge, 3, None)]
infantry_move_attack2 = _mm(FRAME_attak201, FRAME_attak208, infantry_frames_attack2, infantry_run)
