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

Boss 2 aka Hornet. Found in biggun and inner hangar.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from game import g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge, infront, ai_range
from game.g_utils import G_ProjectSource, G_FreeEdict, vtos, vectoyaw
from game.g_monster import monster_fire_bullet, monster_fire_rocket, flymonster_start
from common.header.shared import CHAN_VOICE, ATTN_NONE, CONTENTS_SOLID, CONTENTS_MONSTER, CONTENTS_SLIME, CONTENTS_LAVA, MZ2_BOSS2_ROCKET_1, MZ2_BOSS2_ROCKET_2, MZ2_BOSS2_ROCKET_3, MZ2_BOSS2_ROCKET_4, MZ2_BOSS2_MACHINEGUN_R1, MZ2_BOSS2_MACHINEGUN_L1
from game.header.local import DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, FRAMETIME, MOVETYPE_STEP, MOVETYPE_TOSS, AI_STAND_GROUND, FL_FLY, FL_IMMUNE_LASER, RANGE_MELEE, RANGE_NEAR, RANGE_MID, RANGE_FAR, AS_MELEE, AS_MISSILE, AS_SLIDING, AS_STRAIGHT, DEAD_DEAD, damage_t

"""
#include "../../header/local.h"
#include "boss2.h"
"""

DAMAGE_NO = damage_t.DAMAGE_NO.value
from game.header.game import solid_t, SVF_DEADMONSTER
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.boss2 import boss2_h
from game.monster.supertank import supertank as m_supertank

SOLID_BBOX = solid_t.SOLID_BBOX.value


sound_pain1 = 0
sound_pain2 = 0
sound_pain3 = 0
sound_death = 0
sound_search1 = 0

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

boss2

==============================================================================
*/

#include "g_local.h"
#include "m_boss2.h"

void BossExplode (edict_t *self);

qboolean infront (edict_t *self, edict_t *other);

// Loop this

/*QUAKED monster_boss2 (1 .5 0) (-56 -56 0) (56 56 80) Ambush Trigger_Spawn Sight
*/
"""

def boss2_search (self):
	if not self:

		return


	if local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_search1, 1, ATTN_NONE, 0)

def Boss2Rocket (self):
	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)

	# 1
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_BOSS2_ROCKET_1], forward, right, start)
	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)
	monster_fire_rocket (self, start, dir, 50, 500, MZ2_BOSS2_ROCKET_1)

	# 2
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_BOSS2_ROCKET_2], forward, right, start)
	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)
	monster_fire_rocket (self, start, dir, 50, 500, MZ2_BOSS2_ROCKET_2)

	# 3
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_BOSS2_ROCKET_3], forward, right, start)
	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)
	monster_fire_rocket (self, start, dir, 50, 500, MZ2_BOSS2_ROCKET_3)

	# 4
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_BOSS2_ROCKET_4], forward, right, start)
	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)
	monster_fire_rocket (self, start, dir, 50, 500, MZ2_BOSS2_ROCKET_4)

def boss2_firebullet_right (self):
	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	target = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_BOSS2_MACHINEGUN_R1], forward, right, start)

	shared_c.VectorMA (self.enemy.s.origin, -0.2, self.enemy.velocity, target)
	target[2] += self.enemy.viewheight
	shared.VectorSubtract (target, start, forward)
	shared_c.VectorNormalize (forward)

	monster_fire_bullet (self, start, forward, 6, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MZ2_BOSS2_MACHINEGUN_R1)

def boss2_firebullet_left (self):
	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	target = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_BOSS2_MACHINEGUN_L1], forward, right, start)

	shared_c.VectorMA (self.enemy.s.origin, -0.2, self.enemy.velocity, target)

	target[2] += self.enemy.viewheight
	shared.VectorSubtract (target, start, forward)
	shared_c.VectorNormalize (forward)

	monster_fire_bullet (self, start, forward, 6, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MZ2_BOSS2_MACHINEGUN_L1)

def Boss2MachineGun (self):
	# original code fired a single flash-based bullet; the active version calls both guns
	if not self:

		return


	boss2_firebullet_left(self)
	boss2_firebullet_right(self)

def boss2_stand (self):
	if not self:

		return


	self.monsterinfo.currentmove = boss2_move_stand

def boss2_run (self):
	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = boss2_move_stand
	else:
		self.monsterinfo.currentmove = boss2_move_run

def boss2_walk (self):
	if not self:

		return


	self.monsterinfo.currentmove = boss2_move_walk

def boss2_attack (self):
	if not self:

		return


	vec = np.zeros((3,), dtype=np.float32)
	range_ = 0.0

	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range_ = shared_c.VectorLength (vec)

	if range_ <= 125:
		self.monsterinfo.currentmove = boss2_move_attack_pre_mg
	else:
		if local.random() <= 0.6:
			self.monsterinfo.currentmove = boss2_move_attack_pre_mg
		else:
			self.monsterinfo.currentmove = boss2_move_attack_rocket

def boss2_attack_mg (self):
	if not self:

		return


	self.monsterinfo.currentmove = boss2_move_attack_mg

def boss2_reattack_mg (self):
	if not self:

		return


	if infront(self, self.enemy):
		if local.random() <= 0.7:
			self.monsterinfo.currentmove = boss2_move_attack_mg
		else:
			self.monsterinfo.currentmove = boss2_move_attack_post_mg
	else:
		self.monsterinfo.currentmove = boss2_move_attack_post_mg

def boss2_pain (self, other, kick, damage):
	if not self:

		return


	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	self.pain_debounce_time = g_main.level.time + 3
	# American wanted these at no attenuation
	if damage < 10:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain3, 1, ATTN_NONE, 0)
		self.monsterinfo.currentmove = boss2_move_pain_light
	elif damage < 30:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain1, 1, ATTN_NONE, 0)
		self.monsterinfo.currentmove = boss2_move_pain_light
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain2, 1, ATTN_NONE, 0)
		self.monsterinfo.currentmove = boss2_move_pain_heavy

def boss2_dead (self):
	if not self:

		return


	shared.VectorSet (self.mins, -56, -56, 0)
	shared.VectorSet (self.maxs, 56, 56, 80)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)

def boss2_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_death, 1, ATTN_NONE, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_NO
	self.count = 0
	self.monsterinfo.currentmove = boss2_move_death

def Boss2_CheckAttack(self): #edict_t * (returns qboolean)

	"""
	vec3_t spot1, spot2;
	vec3_t temp;
	float chance;
	trace_t tr;
	int enemy_range;
	float enemy_yaw;
	"""
	spot1 = np.zeros((3,), dtype=np.float32)
	spot2 = np.zeros((3,), dtype=np.float32)
	temp = np.zeros((3,), dtype=np.float32)

	if not self:

		return False


	if self.enemy.health > 0:

		# see if any entities are in the way of the shot
		shared.VectorCopy(self.s.origin, spot1)
		spot1[2] += self.viewheight
		shared.VectorCopy(self.enemy.s.origin, spot2)
		spot2[2] += self.enemy.viewheight
		tr = g_main.gi.trace(spot1, None, None, spot2, self, CONTENTS_SOLID | CONTENTS_MONSTER | CONTENTS_SLIME | CONTENTS_LAVA)
		# do we have a clear shot?
		if tr.ent != self.enemy:

			return False


	enemy_range = ai_range(self, self.enemy)
	shared.VectorSubtract(self.enemy.s.origin, self.s.origin, temp)
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

	elif enemy_range == RANGE_NEAR:

		chance = 0.8

	elif enemy_range == RANGE_MID:

		chance = 0.8

	else:

		return False


	if local.random() < chance:

		self.monsterinfo.attack_state = AS_MISSILE
		self.monsterinfo.attack_finished = g_main.level.time + 2 * local.random()
		return True


	if self.flags & FL_FLY:

		if local.random() < 0.3:

			self.monsterinfo.attack_state = AS_SLIDING

		else:

			self.monsterinfo.attack_state = AS_STRAIGHT


	return False

def SP_monster_boss2 (self):
	global sound_pain1, sound_pain2, sound_pain3, sound_death, sound_search1
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_pain1 = g_main.gi.soundindex ("bosshovr/bhvpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("bosshovr/bhvpain2.wav")
	sound_pain3 = g_main.gi.soundindex ("bosshovr/bhvpain3.wav")
	sound_death = g_main.gi.soundindex ("bosshovr/bhvdeth1.wav")
	sound_search1 = g_main.gi.soundindex ("bosshovr/bhvunqv1.wav")

	self.s.sound = g_main.gi.soundindex ("bosshovr/bhvengn1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/boss2/tris.md2")
	shared.VectorSet (self.mins, -56, -56, 0)
	shared.VectorSet (self.maxs, 56, 56, 80)

	self.health = 2000
	self.gib_health = -200
	self.mass = 1000

	self.flags |= FL_IMMUNE_LASER

	self.pain = boss2_pain
	self.die = boss2_die

	self.monsterinfo.stand = boss2_stand
	self.monsterinfo.walk = boss2_walk
	self.monsterinfo.run = boss2_run
	self.monsterinfo.attack = boss2_attack
	self.monsterinfo.search = boss2_search
	self.monsterinfo.checkattack = Boss2_CheckAttack
	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = boss2_move_stand
	self.monsterinfo.scale = boss2_h.MODEL_SCALE

	flymonster_start (self)

# ----------------------------------------------------------------------------
# Animation move tables (defined after the functions they reference)
# ----------------------------------------------------------------------------
boss2_frames_stand = [_mf(ai_stand, 0, None)] * 21
boss2_move_stand = _mm(boss2_h.FRAME_stand30, boss2_h.FRAME_stand50, boss2_frames_stand, None)

boss2_frames_fidget = [_mf(ai_stand, 0, None)] * 30
boss2_move_fidget = _mm(boss2_h.FRAME_stand1, boss2_h.FRAME_stand30, boss2_frames_fidget, None)

boss2_frames_walk = [_mf(ai_walk, 8, None)] * 20
boss2_move_walk = _mm(boss2_h.FRAME_walk1, boss2_h.FRAME_walk20, boss2_frames_walk, None)

boss2_frames_run = [_mf(ai_run, 8, None)] * 20
boss2_move_run = _mm(boss2_h.FRAME_walk1, boss2_h.FRAME_walk20, boss2_frames_run, None)

boss2_frames_attack_pre_mg = [_mf(ai_charge, 1, None)] * 8 + [_mf(ai_charge, 1, boss2_attack_mg)]
boss2_move_attack_pre_mg = _mm(boss2_h.FRAME_attack1, boss2_h.FRAME_attack9, boss2_frames_attack_pre_mg, None)

boss2_frames_attack_mg = [_mf(ai_charge, 1, Boss2MachineGun)] * 5 + [_mf(ai_charge, 1, boss2_reattack_mg)]
boss2_move_attack_mg = _mm(boss2_h.FRAME_attack10, boss2_h.FRAME_attack15, boss2_frames_attack_mg, None)

boss2_frames_attack_post_mg = [_mf(ai_charge, 1, None)] * 4
boss2_move_attack_post_mg = _mm(boss2_h.FRAME_attack16, boss2_h.FRAME_attack19, boss2_frames_attack_post_mg, boss2_run)

boss2_frames_attack_rocket = [_mf(ai_charge, 1, None)] * 12 + [_mf(ai_move, -20, Boss2Rocket)] + [_mf(ai_charge, 1, None)] * 8
boss2_move_attack_rocket = _mm(boss2_h.FRAME_attack20, boss2_h.FRAME_attack40, boss2_frames_attack_rocket, boss2_run)

boss2_frames_pain_heavy = [_mf(ai_move, 0, None)] * 18
boss2_move_pain_heavy = _mm(boss2_h.FRAME_pain2, boss2_h.FRAME_pain19, boss2_frames_pain_heavy, boss2_run)

boss2_frames_pain_light = [_mf(ai_move, 0, None)] * 4
boss2_move_pain_light = _mm(boss2_h.FRAME_pain20, boss2_h.FRAME_pain23, boss2_frames_pain_light, boss2_run)

boss2_frames_death = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, m_supertank.BossExplode)]
boss2_move_death = _mm(boss2_h.FRAME_death2, boss2_h.FRAME_death50, boss2_frames_death, boss2_dead)
