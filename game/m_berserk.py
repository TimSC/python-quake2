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
from game import q_shared, g_local, g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_FreeEdict
from game.g_weapon import fire_hit
from game.g_monster import walkmonster_start
from game.g_misc import ThrowGib, ThrowHead
from game.q_shared import CHAN_VOICE, CHAN_WEAPON, ATTN_NORM, ATTN_IDLE, YAW
from game.g_local import (MELEE_DISTANCE, GIB_ORGANIC, DEAD_DEAD, MOVETYPE_TOSS,
	MOVETYPE_STEP, AI_STAND_GROUND, damage_t)
DAMAGE_YES = damage_t.DAMAGE_YES.value
from game.game import solid_t, SVF_DEADMONSTER

SOLID_BBOX = solid_t.SOLID_BBOX.value

MODEL_SCALE = 1.000000

sound_pain = 0
sound_die = 0
sound_idle = 0
sound_punch = 0
sound_sight = 0
sound_search = 0

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

FRAME_stand1     = 0
FRAME_stand5     = 4
FRAME_standb1    = 5
FRAME_standb20   = 24
FRAME_walkc1     = 25
FRAME_walkc11    = 35
FRAME_run1       = 36
FRAME_run6       = 41
FRAME_att_c1     = 76
FRAME_att_c8     = 83
FRAME_att_c9     = 84
FRAME_att_c20    = 95
FRAME_att_c21    = 96
FRAME_att_c34    = 109
FRAME_painc1     = 199
FRAME_painc4     = 202
FRAME_painb1     = 203
FRAME_painb20    = 222
FRAME_death1     = 223
FRAME_death13    = 235
FRAME_deathc1    = 236
FRAME_deathc8    = 243
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


static int sound_pain;
static int sound_die;
static int sound_idle;
static int sound_punch;
static int sound_sight;
static int sound_search;




void berserk_fidget (edict_t *self);
mframe_t berserk_frames_stand [] =
{
	ai_stand, 0, berserk_fidget,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL
};
mmove_t berserk_move_stand = {FRAME_stand1, FRAME_stand5, berserk_frames_stand, NULL};


mframe_t berserk_frames_stand_fidget [] =
{
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL
};
mmove_t berserk_move_stand_fidget = {FRAME_standb1, FRAME_standb20, berserk_frames_stand_fidget, berserk_stand};



mframe_t berserk_frames_walk [] =
{
	ai_walk, 9.1, NULL,
	ai_walk, 6.3, NULL,
	ai_walk, 4.9, NULL,
	ai_walk, 6.7, NULL,
	ai_walk, 6.0, NULL,
	ai_walk, 8.2, NULL,
	ai_walk, 7.2, NULL,
	ai_walk, 6.1, NULL,
	ai_walk, 4.9, NULL,
	ai_walk, 4.7, NULL,
	ai_walk, 4.7, NULL,
	ai_walk, 4.8, NULL
};
mmove_t berserk_move_walk = {FRAME_walkc1, FRAME_walkc11, berserk_frames_walk, NULL};


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


mframe_t berserk_frames_run1 [] =
{
	ai_run, 21, NULL,
	ai_run, 11, NULL,
	ai_run, 21, NULL,
	ai_run, 25, NULL,
	ai_run, 18, NULL,
	ai_run, 19, NULL
};
mmove_t berserk_move_run1 = {FRAME_run1, FRAME_run6, berserk_frames_run1, NULL};






mframe_t berserk_frames_attack_spike [] =
{
		ai_charge, 0, NULL,
		ai_charge, 0, NULL,
		ai_charge, 0, berserk_swing,
		ai_charge, 0, berserk_attack_spike,
		ai_charge, 0, NULL,
		ai_charge, 0, NULL,
		ai_charge, 0, NULL,
		ai_charge, 0, NULL
};
mmove_t berserk_move_attack_spike = {FRAME_att_c1, FRAME_att_c8, berserk_frames_attack_spike, berserk_run};



mframe_t berserk_frames_attack_club [] =
{	
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, berserk_swing,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, berserk_attack_club,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL
};
mmove_t berserk_move_attack_club = {FRAME_att_c9, FRAME_att_c20, berserk_frames_attack_club, berserk_run};




mframe_t berserk_frames_attack_strike [] =
{
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, berserk_swing,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, berserk_strike,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 9.7, NULL,
	ai_move, 13.6, NULL
};
	
mmove_t berserk_move_attack_strike = {FRAME_att_c21, FRAME_att_c34, berserk_frames_attack_strike, berserk_run};




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


mframe_t berserk_frames_pain1 [] =
{
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL
};
mmove_t berserk_move_pain1 = {FRAME_painc1, FRAME_painc4, berserk_frames_pain1, berserk_run};


mframe_t berserk_frames_pain2 [] =
{
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL
};
mmove_t berserk_move_pain2 = {FRAME_painb1, FRAME_painb20, berserk_frames_pain2, berserk_run};





mframe_t berserk_frames_death1 [] =
{
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL
	
};
mmove_t berserk_move_death1 = {FRAME_death1, FRAME_death13, berserk_frames_death1, berserk_dead};


mframe_t berserk_frames_death2 [] =
{
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL,
	ai_move, 0, NULL
};
mmove_t berserk_move_death2 = {FRAME_deathc1, FRAME_deathc8, berserk_frames_death2, berserk_dead};




/*QUAKED monster_berserk (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
*/
"""

def berserk_sight (self, other):
	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)
	"""
	void berserk_sight (edict_t *self, edict_t *other)
	{
		gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0);
	}
	"""

def berserk_search (self):
	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)
	"""
	void berserk_search (edict_t *self)
	{
		gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0);
	}
	"""

def berserk_stand (self):
	self.monsterinfo.currentmove = berserk_move_stand
	"""
	void berserk_stand (edict_t *self)
	{
		self->monsterinfo.currentmove = &berserk_move_stand;
	}
	"""

def berserk_fidget (self):
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		return
	if g_local.random() > 0.15:
		return

	self.monsterinfo.currentmove = berserk_move_stand_fidget
	g_main.gi.sound (self, CHAN_WEAPON, sound_idle, 1, ATTN_IDLE, 0)
	"""
	void berserk_fidget (edict_t *self)
	{
		if (self->monsterinfo.aiflags & AI_STAND_GROUND)
			return;
		if (random() > 0.15)
			return;
	
		self->monsterinfo.currentmove = &berserk_move_stand_fidget;
		gi.sound (self, CHAN_WEAPON, sound_idle, 1, ATTN_IDLE, 0);
	}
	"""

def berserk_walk (self):
	self.monsterinfo.currentmove = berserk_move_walk
	"""
	void berserk_walk (edict_t *self)
	{
		self->monsterinfo.currentmove = &berserk_move_walk;
	}
	"""

def berserk_run (self):
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = berserk_move_stand
	else:
		self.monsterinfo.currentmove = berserk_move_run1
	"""
	void berserk_run (edict_t *self)
	{
		if (self->monsterinfo.aiflags & AI_STAND_GROUND)
			self->monsterinfo.currentmove = &berserk_move_stand;
		else
			self->monsterinfo.currentmove = &berserk_move_run1;
	}
	"""

def berserk_attack_spike (self):
	aim = np.array([MELEE_DISTANCE, 0, -24], dtype=np.float32)
	fire_hit (self, aim, (15 + (_r.randint(0, 2147483647) % 6)), 400)		# Faster attack -- upwards and backwards
	"""
	void berserk_attack_spike (edict_t *self)
	{
		static	vec3_t	aim = {MELEE_DISTANCE, 0, -24};
		fire_hit (self, aim, (15 + (rand() % 6)), 400);		//	Faster attack -- upwards and backwards
	}
	"""

def berserk_swing (self):
	g_main.gi.sound (self, CHAN_WEAPON, sound_punch, 1, ATTN_NORM, 0)
	"""
	void berserk_swing (edict_t *self)
	{
		gi.sound (self, CHAN_WEAPON, sound_punch, 1, ATTN_NORM, 0);
	}
	"""

def berserk_attack_club (self):
	aim = np.zeros((3,), dtype=np.float32)

	q_shared.VectorSet (aim, MELEE_DISTANCE, self.mins[0], -4)
	fire_hit (self, aim, (5 + (_r.randint(0, 2147483647) % 6)), 400)		# Slower attack
	"""
	void berserk_attack_club (edict_t *self)
	{
		vec3_t	aim;
	
		VectorSet (aim, MELEE_DISTANCE, self->mins[0], -4);
		fire_hit (self, aim, (5 + (rand() % 6)), 400);		// Slower attack
	}
	"""

def berserk_strike (self):
	pass	#FIXME play impact sound
	"""
	void berserk_strike (edict_t *self)
	{
		//FIXME play impact sound
	}
	"""

def berserk_melee (self):
	if ((_r.randint(0, 2147483647) % 2) == 0):
		self.monsterinfo.currentmove = berserk_move_attack_spike
	else:
		self.monsterinfo.currentmove = berserk_move_attack_club
	"""
	void berserk_melee (edict_t *self)
	{
		if ((rand() % 2) == 0)
			self->monsterinfo.currentmove = &berserk_move_attack_spike;
		else
			self->monsterinfo.currentmove = &berserk_move_attack_club;
	}
	"""

def berserk_pain (self, other, kick, damage):
	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3
	g_main.gi.sound (self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)

	if g_main.skill.value == 3:
		return		# no pain anims in nightmare

	if ((damage < 20) or (g_local.random() < 0.5)):
		self.monsterinfo.currentmove = berserk_move_pain1
	else:
		self.monsterinfo.currentmove = berserk_move_pain2
	"""
	void berserk_pain (edict_t *self, edict_t *other, float kick, int damage)
	{
		if (self->health < (self->max_health / 2))
			self->s.skinnum = 1;
	
		if (level.time < self->pain_debounce_time)
			return;
	
		self->pain_debounce_time = level.time + 3;
		gi.sound (self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0);
	
		if (skill->value == 3)
			return;		// no pain anims in nightmare
	
		if ((damage < 20) || (random() < 0.5))
			self->monsterinfo.currentmove = &berserk_move_pain1;
		else
			self->monsterinfo.currentmove = &berserk_move_pain2;
	}
	"""

def berserk_dead (self):
	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)
	"""
	void berserk_dead (edict_t *self)
	{
		VectorSet (self->mins, -16, -16, -24);
		VectorSet (self->maxs, 16, 16, -8);
		self->movetype = MOVETYPE_TOSS;
		self->svflags |= SVF_DEADMONSTER;
		self->nextthink = 0;
		gi.linkentity (self);
	}
	"""

def berserk_die (self, inflictor, attacker, damage, point):
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
	"""
	void berserk_die (edict_t *self, edict_t *inflictor, edict_t *attacker, int damage, vec3_t point)
	{
		int		n;
	
		if (self->health <= self->gib_health)
		{
			gi.sound (self, CHAN_VOICE, gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0);
			for (n= 0; n < 2; n++)
				ThrowGib (self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC);
			for (n= 0; n < 4; n++)
				ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC);
			ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC);
			self->deadflag = DEAD_DEAD;
			return;
		}
	
		if (self->deadflag == DEAD_DEAD)
			return;
	
		gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0);
		self->deadflag = DEAD_DEAD;
		self->takedamage = DAMAGE_YES;
	
		if (damage >= 50)
			self->monsterinfo.currentmove = &berserk_move_death1;
		else
			self->monsterinfo.currentmove = &berserk_move_death2;
	}
	"""

def SP_monster_berserk (self):
	global sound_pain, sound_die, sound_idle, sound_punch, sound_sight, sound_search
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	# pre-caches
	sound_pain  = g_main.gi.soundindex ("berserk/berpain2.wav")
	sound_die   = g_main.gi.soundindex ("berserk/berdeth2.wav")
	sound_idle  = g_main.gi.soundindex ("berserk/beridle1.wav")
	sound_punch = g_main.gi.soundindex ("berserk/attack.wav")
	sound_search = g_main.gi.soundindex ("berserk/bersrch1.wav")
	sound_sight = g_main.gi.soundindex ("berserk/sight.wav")

	self.s.modelindex = g_main.gi.modelindex("models/monsters/berserk/tris.md2")
	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, 32)
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
	self.monsterinfo.scale = MODEL_SCALE

	g_main.gi.linkentity (self)

	walkmonster_start (self)
	"""
	void SP_monster_berserk (edict_t *self)
	{
		if (deathmatch->value)
		{
			G_FreeEdict (self);
			return;
		}
	
		// pre-caches
		sound_pain  = gi.soundindex ("berserk/berpain2.wav");
		sound_die   = gi.soundindex ("berserk/berdeth2.wav");
		sound_idle  = gi.soundindex ("berserk/beridle1.wav");
		sound_punch = gi.soundindex ("berserk/attack.wav");
		sound_search = gi.soundindex ("berserk/bersrch1.wav");
		sound_sight = gi.soundindex ("berserk/sight.wav");
	
		self->s.modelindex = gi.modelindex("models/monsters/berserk/tris.md2");
		VectorSet (self->mins, -16, -16, -24);
		VectorSet (self->maxs, 16, 16, 32);
		self->movetype = MOVETYPE_STEP;
		self->solid = SOLID_BBOX;
	
		self->health = 240;
		self->gib_health = -60;
		self->mass = 250;
	
		self->pain = berserk_pain;
		self->die = berserk_die;
	
		self->monsterinfo.stand = berserk_stand;
		self->monsterinfo.walk = berserk_walk;
		self->monsterinfo.run = berserk_run;
		self->monsterinfo.dodge = NULL;
		self->monsterinfo.attack = NULL;
		self->monsterinfo.melee = berserk_melee;
		self->monsterinfo.sight = berserk_sight;
		self->monsterinfo.search = berserk_search;
	
		self->monsterinfo.currentmove = &berserk_move_stand;
		self->monsterinfo.scale = MODEL_SCALE;
	
		gi.linkentity (self);
	
		walkmonster_start (self);
	}
	"""

# ----------------------------------------------------------------------------
# Animation move tables (defined after the functions they reference)
# ----------------------------------------------------------------------------
berserk_frames_stand = [
	_mf(ai_stand, 0, berserk_fidget), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None), _mf(ai_stand, 0, None)]
berserk_move_stand = _mm(FRAME_stand1, FRAME_stand5, berserk_frames_stand, None)

berserk_frames_stand_fidget = [_mf(ai_stand, 0, None)] * 20
berserk_move_stand_fidget = _mm(FRAME_standb1, FRAME_standb20, berserk_frames_stand_fidget, berserk_stand)

berserk_frames_walk = [
	_mf(ai_walk, 9.1, None), _mf(ai_walk, 6.3, None), _mf(ai_walk, 4.9, None),
	_mf(ai_walk, 6.7, None), _mf(ai_walk, 6.0, None), _mf(ai_walk, 8.2, None),
	_mf(ai_walk, 7.2, None), _mf(ai_walk, 6.1, None), _mf(ai_walk, 4.9, None),
	_mf(ai_walk, 4.7, None), _mf(ai_walk, 4.7, None), _mf(ai_walk, 4.8, None)]
berserk_move_walk = _mm(FRAME_walkc1, FRAME_walkc11, berserk_frames_walk, None)

berserk_frames_run1 = [
	_mf(ai_run, 21, None), _mf(ai_run, 11, None), _mf(ai_run, 21, None),
	_mf(ai_run, 25, None), _mf(ai_run, 18, None), _mf(ai_run, 19, None)]
berserk_move_run1 = _mm(FRAME_run1, FRAME_run6, berserk_frames_run1, None)

berserk_frames_attack_spike = [
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_swing),
	_mf(ai_charge, 0, berserk_attack_spike), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
berserk_move_attack_spike = _mm(FRAME_att_c1, FRAME_att_c8, berserk_frames_attack_spike, berserk_run)

berserk_frames_attack_club = [
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_swing), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, berserk_attack_club),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
berserk_move_attack_club = _mm(FRAME_att_c9, FRAME_att_c20, berserk_frames_attack_club, berserk_run)

berserk_frames_attack_strike = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, berserk_swing), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, berserk_strike), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 9.7, None), _mf(ai_move, 13.6, None)]
berserk_move_attack_strike = _mm(FRAME_att_c21, FRAME_att_c34, berserk_frames_attack_strike, berserk_run)

berserk_frames_pain1 = [_mf(ai_move, 0, None)] * 4
berserk_move_pain1 = _mm(FRAME_painc1, FRAME_painc4, berserk_frames_pain1, berserk_run)

berserk_frames_pain2 = [_mf(ai_move, 0, None)] * 20
berserk_move_pain2 = _mm(FRAME_painb1, FRAME_painb20, berserk_frames_pain2, berserk_run)

berserk_frames_death1 = [_mf(ai_move, 0, None)] * 13
berserk_move_death1 = _mm(FRAME_death1, FRAME_death13, berserk_frames_death1, berserk_dead)

berserk_frames_death2 = [_mf(ai_move, 0, None)] * 8
berserk_move_death2 = _mm(FRAME_deathc1, FRAME_deathc8, berserk_frames_death2, berserk_dead)
