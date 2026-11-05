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

import numpy as np
from game import g_local, g_main, g_utils, g_monster, g_misc, g_ai, m_boss32, m_supertank
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge, infront, range, visible
from game.g_utils import G_ProjectSource, G_FreeEdict, vectoyaw
from game.g_monster import monster_fire_bullet, monster_fire_bfg, walkmonster_start
from common.header.shared import CHAN_VOICE, CHAN_BODY, ATTN_NORM, CONTENTS_SOLID, CONTENTS_MONSTER, CONTENTS_SLIME, CONTENTS_LAVA, MZ2_JORG_BFG_1, MZ2_JORG_MACHINEGUN_R1, MZ2_JORG_MACHINEGUN_L1
from game.g_local import (DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, FRAMETIME,
	MOVETYPE_STEP, AI_STAND_GROUND, FL_FLY,
	RANGE_MELEE, RANGE_NEAR, RANGE_MID, RANGE_FAR, AS_MELEE, AS_MISSILE, AS_SLIDING,
	AS_STRAIGHT, DEAD_DEAD, damage_t)
DAMAGE_NO = damage_t.DAMAGE_NO.value
from game.game import solid_t
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c

SOLID_BBOX = solid_t.SOLID_BBOX.value

MODEL_SCALE = 1.000000

sound_pain1 = 0
sound_pain2 = 0
sound_pain3 = 0
sound_idle = 0
sound_death = 0
sound_search1 = 0
sound_search2 = 0
sound_search3 = 0
sound_attack1 = 0
sound_attack2 = 0
sound_firegun = 0
sound_step_left = 0
sound_step_right = 0
sound_death_hit = 0

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

FRAME_attak101     = 0
FRAME_attak108     = 7
FRAME_attak109     = 8
FRAME_attak114     = 13
FRAME_attak115     = 14
FRAME_attak118     = 17
FRAME_attak201     = 18
FRAME_attak208     = 25
FRAME_attak213     = 30
FRAME_death01      = 31
FRAME_death50      = 80
FRAME_pain101      = 81
FRAME_pain103      = 83
FRAME_pain201      = 84
FRAME_pain203      = 86
FRAME_pain301      = 87
FRAME_pain325      = 111
FRAME_stand01      = 112
FRAME_stand51      = 162
FRAME_walk01       = 163
FRAME_walk05       = 167
FRAME_walk06       = 168
FRAME_walk19       = 181
FRAME_walk20       = 182
FRAME_walk25       = 187
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

jorg

==============================================================================
*/

#include "g_local.h"
#include "m_boss31.h"

extern SP_monster_makron (edict_t *self);
qboolean visible (edict_t *self, edict_t *other);

void BossExplode (edict_t *self);
void MakronToss (edict_t *self);

void jorg_dead (edict_t *self);
void jorgMachineGun (edict_t *self);

//
// stand
//

//
// walk
//

void MakronPrecache (void);

/*QUAKED monster_jorg (1 .5 0) (-80 -80 0) (90 90 140) Ambush Trigger_Spawn Sight
*/
"""

def jorg_search (self):
	r = g_local.random()

	if r <= 0.3:
		g_main.gi.sound (self, CHAN_VOICE, sound_search1, 1, ATTN_NORM, 0)
	elif r <= 0.6:
		g_main.gi.sound (self, CHAN_VOICE, sound_search2, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_search3, 1, ATTN_NORM, 0)

def jorg_idle (self):
	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_NORM, 0)

def jorg_death_hit (self):
	g_main.gi.sound (self, CHAN_BODY, sound_death_hit, 1, ATTN_NORM, 0)

def jorg_step_left (self):
	g_main.gi.sound (self, CHAN_BODY, sound_step_left, 1, ATTN_NORM, 0)

def jorg_step_right (self):
	g_main.gi.sound (self, CHAN_BODY, sound_step_right, 1, ATTN_NORM, 0)

def jorg_stand (self):
	self.monsterinfo.currentmove = jorg_move_stand

def jorg_walk (self):
	self.monsterinfo.currentmove = jorg_move_walk

def jorg_run (self):
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = jorg_move_stand
	else:
		self.monsterinfo.currentmove = jorg_move_run

def jorg_reattack1 (self):
	if visible(self, self.enemy):
		if g_local.random() < 0.9:
			self.monsterinfo.currentmove = jorg_move_attack1
		else:
			self.s.sound = 0
			self.monsterinfo.currentmove = jorg_move_end_attack1
	else:
		self.s.sound = 0
		self.monsterinfo.currentmove = jorg_move_end_attack1

def jorg_attack1 (self):
	self.monsterinfo.currentmove = jorg_move_attack1

def jorg_pain (self, other, kick, damage):
	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum = 1

	self.s.sound = 0

	if g_main.level.time < self.pain_debounce_time:
		return

	# Lessen the chance of him going into his pain frames if he takes little damage
	if damage <= 40:
		if g_local.random() <= 0.6:
			return

	if (self.s.frame >= FRAME_attak101) and (self.s.frame <= FRAME_attak108):
		if g_local.random() <= 0.005:
			return

	if (self.s.frame >= FRAME_attak109) and (self.s.frame <= FRAME_attak114):
		if g_local.random() <= 0.00005:
			return

	if (self.s.frame >= FRAME_attak201) and (self.s.frame <= FRAME_attak208):
		if g_local.random() <= 0.005:
			return

	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == 3:
		return		# no pain anims in nightmare

	if damage <= 50:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = jorg_move_pain1
	elif damage <= 100:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = jorg_move_pain2
	else:
		if g_local.random() <= 0.3:
			g_main.gi.sound (self, CHAN_VOICE, sound_pain3, 1, ATTN_NORM, 0)
			self.monsterinfo.currentmove = jorg_move_pain3
	"""
;
	"""

def jorgBFG (self):
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_JORG_BFG_1], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)
	g_main.gi.sound (self, CHAN_VOICE, sound_attack2, 1, ATTN_NORM, 0)
	monster_fire_bfg (self, start, dir, 50, 300, 100, 200, MZ2_JORG_BFG_1)

def jorg_firebullet_right (self):
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	target = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_JORG_MACHINEGUN_R1], forward, right, start)

	shared_c.VectorMA (self.enemy.s.origin, -0.2, self.enemy.velocity, target)
	target[2] += self.enemy.viewheight
	shared.VectorSubtract (target, start, forward)
	shared_c.VectorNormalize (forward)

	monster_fire_bullet (self, start, forward, 6, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MZ2_JORG_MACHINEGUN_R1)

def jorg_firebullet_left (self):
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	target = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_JORG_MACHINEGUN_L1], forward, right, start)

	shared_c.VectorMA (self.enemy.s.origin, -0.2, self.enemy.velocity, target)
	target[2] += self.enemy.viewheight
	shared.VectorSubtract (target, start, forward)
	shared_c.VectorNormalize (forward)

	monster_fire_bullet (self, start, forward, 6, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MZ2_JORG_MACHINEGUN_L1)

def jorg_firebullet (self):
	jorg_firebullet_left(self)
	jorg_firebullet_right(self)
	"""
;
	"""

def jorg_attack (self):
	vec = np.zeros((3,), dtype=np.float32)
	range_ = 0.0

	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range_ = shared_c.VectorLength (vec)

	if g_local.random() <= 0.75:
		g_main.gi.sound (self, CHAN_VOICE, sound_attack1, 1, ATTN_NORM, 0)
		self.s.sound = g_main.gi.soundindex ("boss3/w_loop.wav")
		self.monsterinfo.currentmove = jorg_move_start_attack1
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_attack2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = jorg_move_attack2

def jorg_dead (self):
	pass	# original body is #if 0 (disabled): Jorg is on modelindex2, do not clear
	"""
	void jorg_dead (edict_t *self)
	{
	#if 0
		edict_t	*tempent;
		/*
		VectorSet (self->mins, -16, -16, -24);
		VectorSet (self->maxs, 16, 16, -8);
		*/
		
		// Jorg is on modelindex2. Do not clear him.
		VectorSet (self->mins, -60, -60, 0);
		VectorSet (self->maxs, 60, 60, 72);
		self->movetype = MOVETYPE_TOSS;
		self->nextthink = 0;
		gi.linkentity (self);
	
		tempent = G_Spawn();
		VectorCopy (self->s.origin, tempent->s.origin);
		VectorCopy (self->s.angles, tempent->s.angles);
		tempent->killtarget = self->killtarget;
		tempent->target = self->target;
		tempent->activator = self->enemy;
		self->killtarget = 0;
		self->target = 0;
		SP_monster_makron (tempent);
	#endif
	}
	"""

def jorg_die (self, inflictor, attacker, damage, point):
	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_NO
	self.s.sound = 0
	self.count = 0
	self.monsterinfo.currentmove = jorg_move_death

def Jorg_CheckAttack (self):
	spot1 = np.zeros((3,), dtype=np.float32)
	spot2 = np.zeros((3,), dtype=np.float32)
	temp = np.zeros((3,), dtype=np.float32)
	chance = 0.0
	tr = None
	enemy_infront = False
	enemy_range = 0
	enemy_yaw = 0.0

	if self.enemy.health > 0:
		# see if any entities are in the way of the shot
		shared.VectorCopy (self.s.origin, spot1)
		spot1[2] += self.viewheight
		shared.VectorCopy (self.enemy.s.origin, spot2)
		spot2[2] += self.enemy.viewheight

		tr = g_main.gi.trace (spot1, None, None, spot2, self, CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_SLIME|CONTENTS_LAVA)

		# do we have a clear shot?
		if tr.ent != self.enemy:
			return False

	enemy_infront = infront(self, self.enemy)
	enemy_range = range(self, self.enemy)
	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, temp)
	enemy_yaw = vectoyaw(temp)

	self.ideal_yaw = enemy_yaw

	# melee attack
	if enemy_range == RANGE_MELEE:
		if self.monsterinfo.melee:
			self.monsterinfo.attack_state = AS_MELEE
		else:
			self.monsterinfo.attack_state = AS_MISSILE
		return True

	# missile attack
	if not self.monsterinfo.attack:
		return False

	if g_main.level.time < self.monsterinfo.attack_finished:
		return False

	if enemy_range == RANGE_FAR:
		return False

	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		chance = 0.4
	elif enemy_range == RANGE_MELEE:
		chance = 0.8
	elif enemy_range == RANGE_NEAR:
		chance = 0.4
	elif enemy_range == RANGE_MID:
		chance = 0.2
	else:
		return False

	if g_local.random() < chance:
		self.monsterinfo.attack_state = AS_MISSILE
		self.monsterinfo.attack_finished = g_main.level.time + 2*g_local.random()
		return True

	if self.flags & FL_FLY:
		if g_local.random() < 0.3:
			self.monsterinfo.attack_state = AS_SLIDING
		else:
			self.monsterinfo.attack_state = AS_STRAIGHT

	return False

def SP_monster_jorg (self):
	global sound_pain1, sound_pain2, sound_pain3, sound_idle, sound_death, sound_search1, sound_search2, sound_search3, sound_attack1, sound_attack2, sound_firegun, sound_step_left, sound_step_right, sound_death_hit
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("boss3/bs3pain1.wav")
	sound_pain2 = g_main.gi.soundindex ("boss3/bs3pain2.wav")
	sound_pain3 = g_main.gi.soundindex ("boss3/bs3pain3.wav")
	sound_death = g_main.gi.soundindex ("boss3/bs3deth1.wav")
	sound_attack1 = g_main.gi.soundindex ("boss3/bs3atck1.wav")
	sound_attack2 = g_main.gi.soundindex ("boss3/bs3atck2.wav")
	sound_search1 = g_main.gi.soundindex ("boss3/bs3srch1.wav")
	sound_search2 = g_main.gi.soundindex ("boss3/bs3srch2.wav")
	sound_search3 = g_main.gi.soundindex ("boss3/bs3srch3.wav")
	sound_idle = g_main.gi.soundindex ("boss3/bs3idle1.wav")
	sound_step_left = g_main.gi.soundindex ("boss3/step1.wav")
	sound_step_right = g_main.gi.soundindex ("boss3/step2.wav")
	sound_firegun = g_main.gi.soundindex ("boss3/xfire.wav")
	sound_death_hit = g_main.gi.soundindex ("boss3/d_hit.wav")

	m_boss32.MakronPrecache ()

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/boss3/rider/tris.md2")
	self.s.modelindex2 = g_main.gi.modelindex ("models/monsters/boss3/jorg/tris.md2")
	shared.VectorSet (self.mins, -80, -80, 0)
	shared.VectorSet (self.maxs, 80, 80, 140)

	self.health = 3000
	self.gib_health = -2000
	self.mass = 1000

	self.pain = jorg_pain
	self.die = jorg_die
	self.monsterinfo.stand = jorg_stand
	self.monsterinfo.walk = jorg_walk
	self.monsterinfo.run = jorg_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = jorg_attack
	self.monsterinfo.search = jorg_search
	self.monsterinfo.melee = None
	self.monsterinfo.sight = None
	self.monsterinfo.checkattack = Jorg_CheckAttack
	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = jorg_move_stand
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start(self)

# ----------------------------------------------------------------------------
# Animation move tables (defined after the functions they reference)
# ----------------------------------------------------------------------------
jorg_frames_stand = [_mf(ai_stand, 0, jorg_idle)] + [_mf(ai_stand, 0, None)] * 33 + [
  _mf(ai_stand, 19, None),
  _mf(ai_stand, 11, jorg_step_left),
  _mf(ai_stand, 0, None), _mf(ai_stand, 0, None),
  _mf(ai_stand, 6, None),
  _mf(ai_stand, 9, jorg_step_right),
] + [_mf(ai_stand, 0, None)] * 6 + [
  _mf(ai_stand, -2, None),
  _mf(ai_stand, -17, jorg_step_left),
  _mf(ai_stand, 0, None),
  _mf(ai_stand, -12, None),
  _mf(ai_stand, -14, jorg_step_right)]
jorg_move_stand = _mm(FRAME_stand01, FRAME_stand51, jorg_frames_stand, None)

jorg_frames_run = [
  _mf(ai_run, 17, jorg_step_left), _mf(ai_run, 0, None), _mf(ai_run, 0, None),
  _mf(ai_run, 0, None), _mf(ai_run, 12, None), _mf(ai_run, 8, None),
  _mf(ai_run, 10, None), _mf(ai_run, 33, jorg_step_right), _mf(ai_run, 0, None),
  _mf(ai_run, 0, None), _mf(ai_run, 0, None), _mf(ai_run, 9, None),
  _mf(ai_run, 9, None), _mf(ai_run, 9, None)]
jorg_move_run = _mm(FRAME_walk06, FRAME_walk19, jorg_frames_run, None)

jorg_frames_start_walk = [
  _mf(ai_walk, 5, None), _mf(ai_walk, 6, None), _mf(ai_walk, 7, None),
  _mf(ai_walk, 9, None), _mf(ai_walk, 15, None)]
jorg_move_start_walk = _mm(FRAME_walk01, FRAME_walk05, jorg_frames_start_walk, None)

jorg_frames_walk = [
  _mf(ai_walk, 17, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
  _mf(ai_walk, 0, None), _mf(ai_walk, 12, None), _mf(ai_walk, 8, None),
  _mf(ai_walk, 10, None), _mf(ai_walk, 33, None), _mf(ai_walk, 0, None),
  _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 9, None),
  _mf(ai_walk, 9, None), _mf(ai_walk, 9, None)]
jorg_move_walk = _mm(FRAME_walk06, FRAME_walk19, jorg_frames_walk, None)

jorg_frames_end_walk = [
  _mf(ai_walk, 11, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
  _mf(ai_walk, 0, None), _mf(ai_walk, 8, None), _mf(ai_walk, -8, None)]
jorg_move_end_walk = _mm(FRAME_walk20, FRAME_walk25, jorg_frames_end_walk, None)

jorg_frames_pain3 = [
  _mf(ai_move, -28, None), _mf(ai_move, -6, None), _mf(ai_move, -3, jorg_step_left),
  _mf(ai_move, -9, None), _mf(ai_move, 0, jorg_step_right), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -7, None),
  _mf(ai_move, 1, None), _mf(ai_move, -11, None), _mf(ai_move, -4, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 10, None),
  _mf(ai_move, 11, None), _mf(ai_move, 0, None), _mf(ai_move, 10, None),
  _mf(ai_move, 3, None), _mf(ai_move, 10, None), _mf(ai_move, 7, jorg_step_left),
  _mf(ai_move, 17, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, jorg_step_right)]
jorg_move_pain3 = _mm(FRAME_pain301, FRAME_pain325, jorg_frames_pain3, jorg_run)

jorg_frames_pain2 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
jorg_move_pain2 = _mm(FRAME_pain201, FRAME_pain203, jorg_frames_pain2, jorg_run)

jorg_frames_pain1 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
jorg_move_pain1 = _mm(FRAME_pain101, FRAME_pain103, jorg_frames_pain1, jorg_run)

jorg_frames_death1 = [_mf(ai_move, 0, None)] * 48 + [_mf(ai_move, 0, m_boss32.MakronToss), _mf(ai_move, 0, m_supertank.BossExplode)]
jorg_move_death = _mm(FRAME_death01, FRAME_death50, jorg_frames_death1, jorg_dead)

jorg_frames_attack2 = [_mf(ai_charge, 0, None)] * 6 + [_mf(ai_charge, 0, jorgBFG)] + [_mf(ai_move, 0, None)] * 6
jorg_move_attack2 = _mm(FRAME_attak201, FRAME_attak213, jorg_frames_attack2, jorg_run)

jorg_frames_start_attack1 = [_mf(ai_charge, 0, None)] * 8
jorg_move_start_attack1 = _mm(FRAME_attak101, FRAME_attak108, jorg_frames_start_attack1, jorg_attack1)

jorg_frames_attack1 = [_mf(ai_charge, 0, jorg_firebullet)] * 6
jorg_move_attack1 = _mm(FRAME_attak109, FRAME_attak114, jorg_frames_attack1, jorg_reattack1)

jorg_frames_end_attack1 = [_mf(ai_move, 0, None)] * 4
jorg_move_end_attack1 = _mm(FRAME_attak115, FRAME_attak118, jorg_frames_end_attack1, jorg_run)
