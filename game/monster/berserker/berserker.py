"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

The berserker.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_FreeEdict
from game.g_weapon import fire_hit
from game.g_monster import walkmonster_start
from game.g_misc import ThrowGib, ThrowHead
from common.header.shared import CHAN_VOICE, CHAN_WEAPON, ATTN_NORM, ATTN_IDLE, YAW
from game.header.local import MELEE_DISTANCE, GIB_ORGANIC, DEAD_DEAD, MOVETYPE_TOSS, MOVETYPE_STEP, AI_STAND_GROUND, damage_t

"""
#include "../../header/local.h"
#include "berserker.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value
from game.header.game import solid_t, SVF_DEADMONSTER
from common.header import shared
from game.header import local
from game.monster.berserker import berserker_h

SOLID_BBOX = solid_t.SOLID_BBOX.value


sound_pain = 0
sound_die = 0
sound_idle = 0
sound_punch = 0
sound_sight = 0
sound_search = 0

sound_step = 0 #static int
sound_step2 = 0 #static int

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

def berserk_footstep(self): #edict_t *
	global sound_step, sound_step2

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0:

		sound_step = g_main.gi.soundindex("berserk/step1.wav")
		sound_step2 = g_main.gi.soundindex("berserk/step2.wav")


	if rand.randk() % 2 == 0:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

"""
/*
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

*/
/*
==============================================================================

BERSERK

==============================================================================
*/

#include "g_local.h"
#include "m_berserk.h"

/*

  *****************************
  SKIPPED THIS FOR NOW!
  *****************************

   Running -> Arm raised in air

void()	berserk_runb1	=[	$r_att1 ,	berserk_runb2	] {ai_run(21);};
void()	berserk_runb2	=[	$r_att2 ,	berserk_runb3	] {ai_run(11);};
void()	berserk_runb3	=[	$r_att3 ,	berserk_runb4	] {ai_run(21);};
void()	berserk_runb4	=[	$r_att4 ,	berserk_runb5	] {ai_run(25);};
void()	berserk_runb5	=[	$r_att5 ,	berserk_runb6	] {ai_run(18);};
void()	berserk_runb6	=[	$r_att6 ,	berserk_runb7	] {ai_run(19);};
// running with arm in air : start loop
void()	berserk_runb7	=[	$r_att7 ,	berserk_runb8	] {ai_run(21);};
void()	berserk_runb8	=[	$r_att8 ,	berserk_runb9	] {ai_run(11);};
void()	berserk_runb9	=[	$r_att9 ,	berserk_runb10	] {ai_run(21);};
void()	berserk_runb10	=[	$r_att10 ,	berserk_runb11	] {ai_run(25);};
void()	berserk_runb11	=[	$r_att11 ,	berserk_runb12	] {ai_run(18);};
void()	berserk_runb12	=[	$r_att12 ,	berserk_runb7	] {ai_run(19);};
// running with arm in air : end loop
*/

	

/*
void() 	berserk_atke1	=[	$r_attb1,	berserk_atke2	] {ai_run(9);};
void() 	berserk_atke2	=[	$r_attb2,	berserk_atke3	] {ai_run(6);};
void() 	berserk_atke3	=[	$r_attb3,	berserk_atke4	] {ai_run(18.4);};
void() 	berserk_atke4	=[	$r_attb4,	berserk_atke5	] {ai_run(25);};
void() 	berserk_atke5	=[	$r_attb5,	berserk_atke6	] {ai_run(14);};
void() 	berserk_atke6	=[	$r_attb6,	berserk_atke7	] {ai_run(20);};
void() 	berserk_atke7	=[	$r_attb7,	berserk_atke8	] {ai_run(8.5);};
void() 	berserk_atke8	=[	$r_attb8,	berserk_atke9	] {ai_run(3);};
void() 	berserk_atke9	=[	$r_attb9,	berserk_atke10	] {ai_run(17.5);};
void() 	berserk_atke10	=[	$r_attb10,	berserk_atke11	] {ai_run(17);};
void() 	berserk_atke11	=[	$r_attb11,	berserk_atke12	] {ai_run(9);};
void() 	berserk_atke12	=[	$r_attb12,	berserk_atke13	] {ai_run(25);};
void() 	berserk_atke13	=[	$r_attb13,	berserk_atke14	] {ai_run(3.7);};
void() 	berserk_atke14	=[	$r_attb14,	berserk_atke15	] {ai_run(2.6);};
void() 	berserk_atke15	=[	$r_attb15,	berserk_atke16	] {ai_run(19);};
void() 	berserk_atke16	=[	$r_attb16,	berserk_atke17	] {ai_run(25);};
void() 	berserk_atke17	=[	$r_attb17,	berserk_atke18	] {ai_run(19.6);};
void() 	berserk_atke18	=[	$r_attb18,	berserk_run1	] {ai_run(7.8);};
*/

/*QUAKED monster_berserk (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
*/
"""

def berserk_sight (self, other):
	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)

def berserk_search (self):
	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)

def berserk_stand (self):
	if not self:

		return


	self.monsterinfo.currentmove = berserk_move_stand

def berserk_fidget(self): #edict_t *

	if not self:

		return


	if self.enemy:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:

		return


	if local.random() > 0.15:

		return


	self.monsterinfo.currentmove = berserk_move_stand_fidget
	g_main.gi.sound(self, CHAN_WEAPON, sound_idle, 1, ATTN_IDLE, 0)

def berserk_walk (self):
	if not self:

		return


	self.monsterinfo.currentmove = berserk_move_walk

def berserk_run (self):
	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = berserk_move_stand
	else:
		self.monsterinfo.currentmove = berserk_move_run1

def berserk_attack_spike(self): #edict_t *

	"""
	static vec3_t aim = {MELEE_DISTANCE, 0, -24};
	"""
	aim = np.array([MELEE_DISTANCE, 0, -24], dtype=np.float32)

	if not self:

		return


	fire_hit(self, aim, (15 + (rand.randk() % 6)), 400)
	# Faster attack -- upwards and backwards

def berserk_swing (self):
	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_punch, 1, ATTN_NORM, 0)

def berserk_attack_club(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.mins[0], -4)
	fire_hit(self, aim, (5 + (rand.randk() % 6)), 400)
	# Slower attack

def berserk_strike (self):
	pass	#FIXME play impact sound
	"""
	void berserk_strike (edict_t *self)
	{
		//FIXME play impact sound
	}
	"""

def berserk_melee(self): #edict_t *

	if not self:

		return


	if (rand.randk() % 2) == 0:

		self.monsterinfo.currentmove = berserk_move_attack_spike

	else:

		self.monsterinfo.currentmove = berserk_move_attack_club

def berserk_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		return


	self.pain_debounce_time = g_main.level.time + 3
	g_main.gi.sound(self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if (damage < 20) or (local.random() < 0.5):

		self.monsterinfo.currentmove = berserk_move_pain1

	else:

		self.monsterinfo.currentmove = berserk_move_pain2

def berserk_dead (self):
	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)

def berserk_die (self, inflictor, attacker, damage, point):
	if not self:

		return


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

	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	if damage >= 50:
		self.monsterinfo.currentmove = berserk_move_death1
	else:
		self.monsterinfo.currentmove = berserk_move_death2

def SP_monster_berserk(self): #edict_t *
	global sound_die, sound_idle, sound_pain, sound_punch, sound_search, sound_sight, sound_step, sound_step2

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	# pre-caches
	sound_pain = g_main.gi.soundindex("berserk/berpain2.wav")
	sound_die = g_main.gi.soundindex("berserk/berdeth2.wav")
	sound_idle = g_main.gi.soundindex("berserk/beridle1.wav")
	sound_punch = g_main.gi.soundindex("berserk/attack.wav")
	sound_search = g_main.gi.soundindex("berserk/bersrch1.wav")
	sound_sight = g_main.gi.soundindex("berserk/sight.wav")
	self.s.modelindex = g_main.gi.modelindex("models/monsters/berserk/tris.md2")
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 32)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.health = 240
	self.gib_health = -60
	self.mass = 250
	self.pain = berserk_pain
	self.die = berserk_die
	self.monsterinfo.stand = berserk_stand
	self.monsterinfo.walk = berserk_walk
	self.monsterinfo.run = berserk_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = None
	self.monsterinfo.melee = berserk_melee
	self.monsterinfo.sight = berserk_sight
	self.monsterinfo.search = berserk_search
	self.monsterinfo.currentmove = berserk_move_stand
	self.monsterinfo.scale = berserker_h.MODEL_SCALE
	g_main.gi.linkentity(self)
	walkmonster_start(self)

# ----------------------------------------------------------------------------
# Animation move tables (defined after the functions they reference)
# ----------------------------------------------------------------------------
berserk_frames_stand = [
	_mf(ai_stand, 0, berserk_fidget), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None)]
berserk_move_stand = _mm(berserker_h.FRAME_stand1, berserker_h.FRAME_stand5, berserk_frames_stand, None)

berserk_frames_stand_fidget = [_mf(ai_stand, 0, None)] * 20
berserk_move_stand_fidget = _mm(berserker_h.FRAME_standb1, berserker_h.FRAME_standb20, berserk_frames_stand_fidget, berserk_stand)

berserk_frames_walk = [
	_mf(ai_walk, 9.1, None), _mf(ai_walk, 6.3, None), _mf(ai_walk, 4.9, None),
	_mf(ai_walk, 6.7, berserk_footstep), _mf(ai_walk, 6, None), _mf(ai_walk, 8.2, None),
	_mf(ai_walk, 7.2, None), _mf(ai_walk, 6.1, None), _mf(ai_walk, 4.9, berserk_footstep),
	_mf(ai_walk, 4.7, None), _mf(ai_walk, 4.7, None), _mf(ai_walk, 4.8, None)]
berserk_move_walk = _mm(berserker_h.FRAME_walkc1, berserker_h.FRAME_walkc11, berserk_frames_walk, None)

berserk_frames_run1 = [
	_mf(ai_run, 21, None), _mf(ai_run, 11, berserk_footstep), _mf(ai_run, 21, None),
	_mf(ai_run, 25, None), _mf(ai_run, 18, berserk_footstep), _mf(ai_run, 19, None)]
berserk_move_run1 = _mm(berserker_h.FRAME_run1, berserker_h.FRAME_run6, berserk_frames_run1, None)

berserk_frames_attack_spike = [
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_swing),
	_mf(ai_charge, 0, berserk_attack_spike), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
berserk_move_attack_spike = _mm(berserker_h.FRAME_att_c1, berserker_h.FRAME_att_c8, berserk_frames_attack_spike, berserk_run)

berserk_frames_attack_club = [
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_footstep),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_swing), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_attack_club),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
berserk_move_attack_club = _mm(berserker_h.FRAME_att_c9, berserker_h.FRAME_att_c20, berserk_frames_attack_club, berserk_run)

berserk_frames_attack_strike = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, berserk_footstep),
	_mf(ai_move, 0, berserk_swing), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, berserk_strike), _mf(ai_move, 0, berserk_footstep),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 9.7, None), _mf(ai_move, 13.6, berserk_footstep)]
berserk_move_attack_strike = _mm(berserker_h.FRAME_att_c21, berserker_h.FRAME_att_c34, berserk_frames_attack_strike, berserk_run)

berserk_frames_pain1 = [_mf(ai_move, 0, None)] * 4
berserk_move_pain1 = _mm(berserker_h.FRAME_painc1, berserker_h.FRAME_painc4, berserk_frames_pain1, berserk_run)

berserk_frames_pain2 = [_mf(ai_move, 0, None)] * 20
berserk_move_pain2 = _mm(berserker_h.FRAME_painb1, berserker_h.FRAME_painb20, berserk_frames_pain2, berserk_run)

berserk_frames_death1 = [_mf(ai_move, 0, None)] * 13
berserk_move_death1 = _mm(berserker_h.FRAME_death1, berserker_h.FRAME_death13, berserk_frames_death1, berserk_dead)

berserk_frames_death2 = [_mf(ai_move, 0, None)] * 8
berserk_move_death2 = _mm(berserker_h.FRAME_deathc1, berserker_h.FRAME_deathc8, berserk_frames_death2, berserk_dead)
