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
from game import g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge, infront, range, visible
from game.g_utils import G_ProjectSource, G_FreeEdict, vectoyaw, vectoangles
from game.g_monster import monster_fire_bullet, monster_fire_bfg, monster_fire_railgun, monster_fire_blaster, walkmonster_start
from game.g_misc import ThrowGib, ThrowHead
from common.header.shared import CHAN_AUTO, CHAN_VOICE, CHAN_BODY, CHAN_WEAPON, ATTN_NONE, ATTN_NORM, CONTENTS_SOLID, CONTENTS_MONSTER, CONTENTS_SLIME, CONTENTS_LAVA, MZ2_MAKRON_BFG, MZ2_MAKRON_RAILGUN_1, MZ2_MAKRON_BLASTER_1, EF_BLASTER
from game.header.local import FRAMETIME, MOVETYPE_NONE, MOVETYPE_STEP, MOVETYPE_TOSS, AI_STAND_GROUND, FL_FLY, RANGE_MELEE, RANGE_NEAR, RANGE_MID, RANGE_FAR, AS_MELEE, AS_MISSILE, AS_SLIDING, AS_STRAIGHT, DEAD_DEAD, GIB_ORGANIC, GIB_METALLIC, damage_t
DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_NO = damage_t.DAMAGE_NO.value
from game.header.game import solid_t, SVF_DEADMONSTER
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value

MODEL_SCALE = 1.000000

sound_pain4 = 0
sound_pain5 = 0
sound_pain6 = 0
sound_death = 0
sound_step_left = 0
sound_step_right = 0
sound_attack_bfg = 0
sound_brainsplorch = 0
sound_prerailgun = 0
sound_popup = 0
sound_taunt1 = 0
sound_taunt2 = 0
sound_taunt3 = 0
sound_hit = 0

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

FRAME_stand201     = 414
FRAME_stand260     = 473
FRAME_active01     = 188
FRAME_active13     = 200
FRAME_attak301     = 201
FRAME_attak308     = 208
FRAME_attak401     = 209
FRAME_attak405     = 213
FRAME_attak413     = 221
FRAME_attak421     = 229
FRAME_attak426     = 234
FRAME_attak501     = 235
FRAME_attak516     = 250
FRAME_death201     = 251
FRAME_death295     = 345
FRAME_death301     = 346
FRAME_death320     = 365
FRAME_pain401      = 379
FRAME_pain404      = 382
FRAME_pain501      = 383
FRAME_pain504      = 386
FRAME_pain601      = 387
FRAME_pain627      = 413
FRAME_walk204      = 477
FRAME_walk213      = 486
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
"""
"""
/*
==============================================================================

Makron -- Final Boss

==============================================================================
*/

#include "g_local.h"
#include "m_boss32.h"

qboolean visible (edict_t *self, edict_t *other);

//
// stand
//

	

// FIXME: He's not firing from the proper Z

// FIXME: This is all wrong. He's not firing at the proper angles.

/*
---
Makron Torso. This needs to be spawned in
---
*/

//
// death
//

//
// monster_makron
//

/*QUAKED monster_makron (1 .5 0) (-30 -30 0) (30 30 90) Ambush Trigger_Spawn Sight
*/
"""
"""
/*
=================
MakronSpawn

=================
*/
"""
"""
/*
=================
MakronToss

Jorg is just about dead, so set up to launch Makron out
=================
*/
"""

def makron_taunt (self):
	r = local.random()
	if r <= 0.3:
		g_main.gi.sound (self, CHAN_AUTO, sound_taunt1, 1, ATTN_NONE, 0)
	elif r <= 0.6:
		g_main.gi.sound (self, CHAN_AUTO, sound_taunt2, 1, ATTN_NONE, 0)
	else:
		g_main.gi.sound (self, CHAN_AUTO, sound_taunt3, 1, ATTN_NONE, 0)

def makron_stand (self):
	self.monsterinfo.currentmove = makron_move_stand

def makron_hit (self):
	g_main.gi.sound (self, CHAN_AUTO, sound_hit, 1, ATTN_NONE, 0)

def makron_popup (self):
	g_main.gi.sound (self, CHAN_BODY, sound_popup, 1, ATTN_NONE, 0)

def makron_step_left (self):
	g_main.gi.sound (self, CHAN_BODY, sound_step_left, 1, ATTN_NORM, 0)

def makron_step_right (self):
	g_main.gi.sound (self, CHAN_BODY, sound_step_right, 1, ATTN_NORM, 0)

def makron_brainsplorch (self):
	g_main.gi.sound (self, CHAN_VOICE, sound_brainsplorch, 1, ATTN_NORM, 0)

def makron_prerailgun (self):
	g_main.gi.sound (self, CHAN_WEAPON, sound_prerailgun, 1, ATTN_NORM, 0)

def makron_walk (self):
	self.monsterinfo.currentmove = makron_move_walk

def makron_run (self):
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = makron_move_stand
	else:
		self.monsterinfo.currentmove = makron_move_run

def makronBFG (self):
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_MAKRON_BFG], forward, right, start)

	shared.VectorCopy (self.enemy.s.origin, vec)
	vec[2] += self.enemy.viewheight
	shared.VectorSubtract (vec, start, dir)
	shared_c.VectorNormalize (dir)
	g_main.gi.sound (self, CHAN_VOICE, sound_attack_bfg, 1, ATTN_NORM, 0)
	monster_fire_bfg (self, start, dir, 50, 300, 100, 300, MZ2_MAKRON_BFG)

def MakronSaveloc (self):
	shared.VectorCopy (self.enemy.s.origin, self.pos1)	# save for aiming the shot
	self.pos1[2] += self.enemy.viewheight
	"""
;
	"""

def MakronRailgun (self):
	start = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[MZ2_MAKRON_RAILGUN_1], forward, right, start)

	# calc direction to where we targted
	shared.VectorSubtract (self.pos1, start, dir)
	shared_c.VectorNormalize (dir)

	monster_fire_railgun (self, start, dir, 50, 100, MZ2_MAKRON_RAILGUN_1)

def MakronHyperblaster (self):
	dir = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)

	flash_number = MZ2_MAKRON_BLASTER_1 + (self.s.frame - FRAME_attak405)

	shared_c.AngleVectors (self.s.angles, forward, right, up)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	if self.enemy:
		shared.VectorCopy (self.enemy.s.origin, vec)
		vec[2] += self.enemy.viewheight
		shared.VectorSubtract (vec, start, vec)
		vectoangles (vec, vec)
		dir[0] = vec[0]
	else:
		dir[0] = 0
	if self.s.frame <= FRAME_attak413:
		dir[1] = self.s.angles[1] - 10 * (self.s.frame - FRAME_attak413)
	else:
		dir[1] = self.s.angles[1] + 10 * (self.s.frame - FRAME_attak421)
	dir[2] = 0

	shared_c.AngleVectors (dir, forward, None, None)

	monster_fire_blaster (self, start, forward, 15, 1000, MZ2_MAKRON_BLASTER_1, EF_BLASTER)

def makron_pain (self, other, kick, damage):
	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum = 1

	if g_main.level.time < self.pain_debounce_time:
		return

	# Lessen the chance of him going into his pain frames
	if damage <= 25:
		if local.random() < 0.2:
			return

	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == 3:
		return		# no pain anims in nightmare

	if damage <= 40:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain4, 1, ATTN_NONE, 0)
		self.monsterinfo.currentmove = makron_move_pain4
	elif damage <= 110:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain5, 1, ATTN_NONE, 0)
		self.monsterinfo.currentmove = makron_move_pain5
	else:
		if damage <= 150:
			if local.random() <= 0.45:
				g_main.gi.sound (self, CHAN_VOICE, sound_pain6, 1, ATTN_NONE, 0)
				self.monsterinfo.currentmove = makron_move_pain6
		else:
			if local.random() <= 0.35:
				g_main.gi.sound (self, CHAN_VOICE, sound_pain6, 1, ATTN_NONE, 0)
				self.monsterinfo.currentmove = makron_move_pain6
	"""
;
	"""

def makron_sight (self, other):
	self.monsterinfo.currentmove = makron_move_sight
	"""
;
	"""

def makron_attack (self):
	vec = np.zeros((3,), dtype=np.float32)
	range_ = 0.0
	r = local.random()

	shared.VectorSubtract (self.enemy.s.origin, self.s.origin, vec)
	range_ = shared_c.VectorLength (vec)

	if r <= 0.3:
		self.monsterinfo.currentmove = makron_move_attack3
	elif r <= 0.6:
		self.monsterinfo.currentmove = makron_move_attack4
	else:
		self.monsterinfo.currentmove = makron_move_attack5

def makron_torso_think (self):
	self.s.frame += 1
	if self.s.frame < 365:
		self.nextthink = g_main.level.time + FRAMETIME
	else:
		self.s.frame = 346
		self.nextthink = g_main.level.time + FRAMETIME

def makron_torso (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_NOT
	shared.VectorSet (ent.mins, -8, -8, 0)
	shared.VectorSet (ent.maxs, 8, 8, 8)
	ent.s.frame = 346
	ent.s.modelindex = g_main.gi.modelindex ("models/monsters/boss3/rider/tris.md2")
	ent.think = makron_torso_think
	ent.nextthink = g_main.level.time + 2 * FRAMETIME
	ent.s.sound = g_main.gi.soundindex ("makron/spine.wav")
	g_main.gi.linkentity (ent)

def makron_dead (self):
	shared.VectorSet (self.mins, -60, -60, 0)
	shared.VectorSet (self.maxs, 60, 60, 72)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)

def makron_die (self, inflictor, attacker, damage, point):
	tempent = None
	n = 0

	self.s.sound = 0

	# check for gib
	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(1):	# 4 in original, reduced to 1
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		for n in range(4):
			ThrowGib (self, "models/objects/gibs/sm_metal/tris.md2", damage, GIB_METALLIC)
		ThrowHead (self, "models/objects/gibs/gear/tris.md2", damage, GIB_METALLIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	# regular death
	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NONE, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES

	tempent = g_utils.G_Spawn()
	shared.VectorCopy (self.s.origin, tempent.s.origin)
	shared.VectorCopy (self.s.angles, tempent.s.angles)
	tempent.s.origin[1] -= 84
	makron_torso (tempent)

	self.monsterinfo.currentmove = makron_move_death2

def Makron_CheckAttack (self):
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

	if local.random() < chance:
		self.monsterinfo.attack_state = AS_MISSILE
		self.monsterinfo.attack_finished = g_main.level.time + 2*local.random()
		return True

	if self.flags & FL_FLY:
		if local.random() < 0.3:
			self.monsterinfo.attack_state = AS_SLIDING
		else:
			self.monsterinfo.attack_state = AS_STRAIGHT

	return False

def MakronPrecache ():
	global sound_pain4, sound_pain5, sound_pain6, sound_death, sound_step_left, sound_step_right, sound_attack_bfg, sound_brainsplorch, sound_prerailgun, sound_popup, sound_taunt1, sound_taunt2, sound_taunt3, sound_hit
	sound_pain4 = g_main.gi.soundindex ("makron/pain3.wav")
	sound_pain5 = g_main.gi.soundindex ("makron/pain2.wav")
	sound_pain6 = g_main.gi.soundindex ("makron/pain1.wav")
	sound_death = g_main.gi.soundindex ("makron/death.wav")
	sound_step_left = g_main.gi.soundindex ("makron/step1.wav")
	sound_step_right = g_main.gi.soundindex ("makron/step2.wav")
	sound_attack_bfg = g_main.gi.soundindex ("makron/bfg_fire.wav")
	sound_brainsplorch = g_main.gi.soundindex ("makron/brain1.wav")
	sound_prerailgun = g_main.gi.soundindex ("makron/rail_up.wav")
	sound_popup = g_main.gi.soundindex ("makron/popup.wav")
	sound_taunt1 = g_main.gi.soundindex ("makron/voice4.wav")
	sound_taunt2 = g_main.gi.soundindex ("makron/voice3.wav")
	sound_taunt3 = g_main.gi.soundindex ("makron/voice.wav")
	sound_hit = g_main.gi.soundindex ("makron/bhit.wav")

	g_main.gi.modelindex ("models/monsters/boss3/rider/tris.md2")

def SP_monster_makron (self):
	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	MakronPrecache ()

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/boss3/rider/tris.md2")
	shared.VectorSet (self.mins, -30, -30, 0)
	shared.VectorSet (self.maxs, 30, 30, 90)

	self.health = 3000
	self.gib_health = -2000
	self.mass = 500

	self.pain = makron_pain
	self.die = makron_die
	self.monsterinfo.stand = makron_stand
	self.monsterinfo.walk = makron_walk
	self.monsterinfo.run = makron_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = makron_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = makron_sight
	self.monsterinfo.checkattack = Makron_CheckAttack

	g_main.gi.linkentity (self)

	# self.monsterinfo.currentmove = makron_move_stand
	self.monsterinfo.currentmove = makron_move_sight
	self.monsterinfo.scale = MODEL_SCALE

	walkmonster_start(self)

def MakronSpawn (self):
	vec = np.zeros((3,), dtype=np.float32)
	player = None

	SP_monster_makron (self)

	# jump at player
	player = g_main.level.sight_client
	if not player:
		return

	shared.VectorSubtract (player.s.origin, self.s.origin, vec)
	self.s.angles[1] = vectoyaw(vec)
	shared_c.VectorNormalize (vec)
	shared_c.VectorMA (shared_c.vec3_origin, 400, vec, self.velocity)
	self.velocity[2] = 200
	self.groundentity = None

def MakronToss (self):
	ent = g_utils.G_Spawn ()
	ent.nextthink = g_main.level.time + 0.8
	ent.think = MakronSpawn
	ent.target = self.target
	shared.VectorCopy (self.s.origin, ent.s.origin)

# ----------------------------------------------------------------------------
# Animation move tables (defined after the functions they reference)
# ----------------------------------------------------------------------------
makron_frames_stand = [
  _mf(ai_stand, 0, None)] * 60
makron_move_stand = _mm(FRAME_stand201, FRAME_stand260, makron_frames_stand, None)

makron_frames_run = [
  _mf(ai_run, 3, makron_step_left), _mf(ai_run, 12, None), _mf(ai_run, 8, None),
  _mf(ai_run, 8, None), _mf(ai_run, 8, makron_step_right), _mf(ai_run, 6, None),
  _mf(ai_run, 12, None), _mf(ai_run, 9, None), _mf(ai_run, 6, None),
  _mf(ai_run, 12, None)]
makron_move_run = _mm(FRAME_walk204, FRAME_walk213, makron_frames_run, None)

makron_frames_walk = [
  _mf(ai_walk, 3, makron_step_left), _mf(ai_walk, 12, None), _mf(ai_walk, 8, None),
  _mf(ai_walk, 8, None), _mf(ai_walk, 8, makron_step_right), _mf(ai_walk, 6, None),
  _mf(ai_walk, 12, None), _mf(ai_walk, 9, None), _mf(ai_walk, 6, None),
  _mf(ai_walk, 12, None)]
# C quirk: makron_move_walk references makron_frames_run
makron_move_walk = _mm(FRAME_walk204, FRAME_walk213, makron_frames_run, None)

makron_frames_pain6 = [_mf(ai_move, 0, None)] * 15 + [_mf(ai_move, 0, makron_popup)] + [_mf(ai_move, 0, None)] * 7 + [_mf(ai_move, 0, makron_taunt)] + [_mf(ai_move, 0, None)] * 3
makron_move_pain6 = _mm(FRAME_pain601, FRAME_pain627, makron_frames_pain6, makron_run)

makron_frames_pain5 = [_mf(ai_move, 0, None)] * 4
makron_move_pain5 = _mm(FRAME_pain501, FRAME_pain504, makron_frames_pain5, makron_run)

makron_frames_pain4 = [_mf(ai_move, 0, None)] * 4
makron_move_pain4 = _mm(FRAME_pain401, FRAME_pain404, makron_frames_pain4, makron_run)

makron_frames_death2 = [
  _mf(ai_move, -15, None), _mf(ai_move, 3, None), _mf(ai_move, -12, None), _mf(ai_move, 0, makron_step_left), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 11, None), _mf(ai_move, 12, None), _mf(ai_move, 11, makron_step_right),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 5, None), _mf(ai_move, 7, None), _mf(ai_move, 6, makron_step_left),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -1, None), _mf(ai_move, 2, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -6, None),
  _mf(ai_move, -4, None), _mf(ai_move, -6, makron_step_right), _mf(ai_move, -4, None), _mf(ai_move, -4, makron_step_left), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -2, None), _mf(ai_move, -5, None), _mf(ai_move, -3, makron_step_right), _mf(ai_move, -8, None),
  _mf(ai_move, -3, makron_step_left), _mf(ai_move, -7, None), _mf(ai_move, -4, None), _mf(ai_move, -4, makron_step_right), _mf(ai_move, -6, None), _mf(ai_move, -7, None),
  _mf(ai_move, 0, makron_step_left), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
  _mf(ai_move, 0, None), _mf(ai_move, -2, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 2, None), _mf(ai_move, 0, None),
  _mf(ai_move, 27, makron_hit), _mf(ai_move, 26, None), _mf(ai_move, 0, makron_brainsplorch), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
makron_move_death2 = _mm(FRAME_death201, FRAME_death295, makron_frames_death2, makron_dead)

makron_frames_death3 = [_mf(ai_move, 0, None)] * 20
makron_move_death3 = _mm(FRAME_death301, FRAME_death320, makron_frames_death3, None)

makron_frames_sight = [_mf(ai_move, 0, None)] * 13
makron_move_sight = _mm(FRAME_active01, FRAME_active13, makron_frames_sight, makron_run)

makron_frames_attack3 = [_mf(ai_charge, 0, None)] * 3 + [_mf(ai_charge, 0, makronBFG)] + [_mf(ai_move, 0, None)] * 4
makron_move_attack3 = _mm(FRAME_attak301, FRAME_attak308, makron_frames_attack3, makron_run)

makron_frames_attack4 = [_mf(ai_charge, 0, None)] * 4 + [_mf(ai_move, 0, MakronHyperblaster)] * 20 + [_mf(ai_move, 0, None)] * 2
makron_move_attack4 = _mm(FRAME_attak401, FRAME_attak426, makron_frames_attack4, makron_run)

makron_frames_attack5 = [_mf(ai_charge, 0, makron_prerailgun), _mf(ai_charge, 0, None)] * 1 + [_mf(ai_charge, 0, None)] * 5 + [_mf(ai_charge, 0, MakronSaveloc)] + [_mf(ai_move, 0, MakronRailgun)] + [_mf(ai_move, 0, None)] * 7
makron_move_attack5 = _mm(FRAME_attak501, FRAME_attak516, makron_frames_attack5, makron_run)
