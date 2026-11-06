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

Gunner.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict
from game.g_monster import monster_fire_bullet, monster_fire_grenade, walkmonster_start
from game.g_misc import ThrowGib, ThrowHead
from common.header.shared import CHAN_VOICE, ATTN_NORM, ATTN_IDLE, MZ2_GUNNER_MACHINEGUN_1, MZ2_GUNNER_GRENADE_1, MZ2_GUNNER_GRENADE_2, MZ2_GUNNER_GRENADE_3, MZ2_GUNNER_GRENADE_4
from game.header.local import GIB_ORGANIC, DEAD_DEAD, MOVETYPE_TOSS, MOVETYPE_STEP, AI_STAND_GROUND, AI_HOLD_FRAME, AI_DUCKED, RANGE_MELEE, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, damage_t

"""
#include "../../header/local.h"
#include "gunner.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.gunner import gunner_h

# m_gunner.h


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

def gunner_footstep(self): #edict_t *
	global sound_step, sound_step2

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0:

		sound_step = g_main.gi.soundindex("gunner/step1.wav")
		sound_step2 = g_main.gi.soundindex("gunner/step2.wav")


	if rand.randk() % 2 == 0:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

"""
==============================================================================

GUNNER

==============================================================================
"""

sound_pain = 0 # static int
sound_pain2 = 0 # static int
sound_death = 0 # static int
sound_idle = 0 # static int
sound_open = 0 # static int
sound_search = 0 # static int
sound_sight = 0 # static int


def gunner_idlesound (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def gunner_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def gunner_search (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def gunner_fidget(self): #edict_t *

	if not self:

		return


	if self.enemy:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:

		return


	if local.random() <= 0.05:

		self.monsterinfo.currentmove = gunner_move_fidget


def gunner_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gunner_move_stand


def gunner_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gunner_move_walk


def gunner_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = gunner_move_stand
	else:
		self.monsterinfo.currentmove = gunner_move_run


def gunner_runandshoot (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gunner_move_runandshoot


def gunner_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		return


	self.pain_debounce_time = g_main.level.time + 3
	if rand.randk() & 1:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)


	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if damage <= 10:

		self.monsterinfo.currentmove = gunner_move_pain3

	elif damage <= 25:

		self.monsterinfo.currentmove = gunner_move_pain2

	else:

		self.monsterinfo.currentmove = gunner_move_pain1


def gunner_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def gunner_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	"""
	int n;
	"""

	if not self:

		return


	self.s.skinnum = 1
	# check for gib
	if self.health <= self.gib_health:

		g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(2):

			ThrowGib(self, "models/objects/gibs/bone/tris.md2", damage, GIB_ORGANIC)


		for n in range(4):

			ThrowGib(self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)


		ThrowHead(self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return


	if self.deadflag == DEAD_DEAD:

		return


	# regular death
	g_main.gi.sound(self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.monsterinfo.currentmove = gunner_move_death


def gunner_duck_down(self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_DUCKED:

		return


	self.monsterinfo.aiflags |= AI_DUCKED
	if g_main.skill.value >= local.SKILL_HARD:

		if local.random() > 0.5:

			GunnerGrenade(self)


	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity(self)


def gunner_duck_hold (self): #edict_t *

	if not self:

		return


	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME


def gunner_duck_up (self): #edict_t *

	if not self:

		return


	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)


def gunner_dodge(self, attacker, eta): #edict_t *, edict_t *, float

	if not self or not attacker:

		return


	if local.random() > 0.25:

		return


	if not self.enemy:

		self.enemy = attacker
		g_ai.FoundTarget(self)


	self.monsterinfo.currentmove = gunner_move_duck


def gunner_opengun (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_open, 1, ATTN_IDLE, 0)


def GunnerFire (self): #edict_t *

	if not self:

		return


	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	target = np.zeros((3,), dtype=np.float32) #vec3_t
	aim = np.zeros((3,), dtype=np.float32) #vec3_t
	#int		flash_number;

	flash_number = MZ2_GUNNER_MACHINEGUN_1 + (self.s.frame - gunner_h.FRAME_attak216)

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	# project enemy back a bit and target there
	shared.VectorCopy (self.enemy.s.origin, target)
	shared_c.VectorMA (target, -0.2, self.enemy.velocity, target)
	target[2] += self.enemy.viewheight

	shared.VectorSubtract (target, start, aim)
	shared_c.VectorNormalize (aim)
	monster_fire_bullet (self, start, aim, 3, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)


def GunnerGrenade (self): #edict_t *

	if not self:

		return


	start = np.zeros((3,), dtype=np.float32) #vec3_t
	forward = np.zeros((3,), dtype=np.float32) #vec3_t
	right = np.zeros((3,), dtype=np.float32) #vec3_t
	aim = np.zeros((3,), dtype=np.float32) #vec3_t
	#int		flash_number;

	if self.s.frame == gunner_h.FRAME_attak105:
		flash_number = MZ2_GUNNER_GRENADE_1
	elif self.s.frame == gunner_h.FRAME_attak108:
		flash_number = MZ2_GUNNER_GRENADE_2
	elif self.s.frame == gunner_h.FRAME_attak111:
		flash_number = MZ2_GUNNER_GRENADE_3
	else: # (self->s.frame == FRAME_attak114)
		flash_number = MZ2_GUNNER_GRENADE_4

	shared_c.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

	#FIXME : do a spread -225 -75 75 225 degrees around forward
	shared.VectorCopy (forward, aim)

	monster_fire_grenade (self, start, aim, 50, 600, flash_number)


def gunner_attack(self): #edict_t *

	if not self:

		return


	if g_ai.ai_range(self, self.enemy) == RANGE_MELEE:

		self.monsterinfo.currentmove = gunner_move_attack_chain

	else:

		if local.random() <= 0.5:

			self.monsterinfo.currentmove = gunner_move_attack_grenade

		else:

			self.monsterinfo.currentmove = gunner_move_attack_chain


def gunner_fire_chain (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = gunner_move_fire_chain


def gunner_refire_chain (self): #edict_t *

	if not self:

		return


	if self.enemy.health > 0:
		if g_ai.visible (self, self.enemy):
			if local.random() <= 0.5:
				self.monsterinfo.currentmove = gunner_move_fire_chain
				return
	self.monsterinfo.currentmove = gunner_move_endfire_chain


"""QUAKED monster_gunner (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_gunner(self): #edict_t *
	global sound_death, sound_idle, sound_open, sound_pain, sound_pain2, sound_search, sound_sight, sound_step, sound_step2

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_death = g_main.gi.soundindex("gunner/death1.wav")
	sound_pain = g_main.gi.soundindex("gunner/gunpain2.wav")
	sound_pain2 = g_main.gi.soundindex("gunner/gunpain1.wav")
	sound_idle = g_main.gi.soundindex("gunner/gunidle1.wav")
	sound_open = g_main.gi.soundindex("gunner/gunatck1.wav")
	sound_search = g_main.gi.soundindex("gunner/gunsrch1.wav")
	sound_sight = g_main.gi.soundindex("gunner/sight1.wav")
	g_main.gi.soundindex("gunner/gunatck2.wav")
	g_main.gi.soundindex("gunner/gunatck3.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/gunner/tris.md2")
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 32)
	self.health = 175
	self.gib_health = -70
	self.mass = 200
	self.pain = gunner_pain
	self.die = gunner_die
	self.monsterinfo.stand = gunner_stand
	self.monsterinfo.walk = gunner_walk
	self.monsterinfo.run = gunner_run
	self.monsterinfo.dodge = gunner_dodge
	self.monsterinfo.attack = gunner_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = gunner_sight
	self.monsterinfo.search = gunner_search
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = gunner_move_stand
	self.monsterinfo.scale = gunner_h.MODEL_SCALE
	walkmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
gunner_frames_fidget = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, gunner_idlesound),
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
gunner_move_fidget = _mm(gunner_h.FRAME_stand31, gunner_h.FRAME_stand70, gunner_frames_fidget, gunner_stand)

gunner_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, gunner_fidget),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, gunner_fidget),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, gunner_fidget),
]
gunner_move_stand = _mm(gunner_h.FRAME_stand01, gunner_h.FRAME_stand30, gunner_frames_stand, None)

gunner_frames_walk = [
	_mf(ai_walk, 0, gunner_footstep), _mf(ai_walk, 3, None), _mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None), _mf(ai_walk, 7, None), _mf(ai_walk, 2, gunner_footstep),
	_mf(ai_walk, 6, None), _mf(ai_walk, 4, None), _mf(ai_walk, 2, None),
	_mf(ai_walk, 7, None), _mf(ai_walk, 5, None), _mf(ai_walk, 7, None),
	_mf(ai_walk, 4, gunner_footstep)]
gunner_move_walk = _mm(gunner_h.FRAME_walk07, gunner_h.FRAME_walk19, gunner_frames_walk, None)

gunner_frames_run = [
	_mf(ai_run, 26, None), _mf(ai_run, 9, gunner_footstep), _mf(ai_run, 9, None),
	_mf(ai_run, 9, None), _mf(ai_run, 15, None), _mf(ai_run, 10, gunner_footstep),
	_mf(ai_run, 13, None), _mf(ai_run, 6, None)]
gunner_move_run = _mm(gunner_h.FRAME_run01, gunner_h.FRAME_run08, gunner_frames_run, None)

gunner_frames_runandshoot = [
	_mf(ai_run, 32, None), _mf(ai_run, 15, gunner_footstep), _mf(ai_run, 10, None),
	_mf(ai_run, 18, None), _mf(ai_run, 8, gunner_footstep), _mf(ai_run, 20, None)]
gunner_move_runandshoot = _mm(gunner_h.FRAME_runs01, gunner_h.FRAME_runs06, gunner_frames_runandshoot, None)

gunner_frames_pain3 = [
	_mf(ai_move, -3, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 1, None),
]
gunner_move_pain3 = _mm(gunner_h.FRAME_pain301, gunner_h.FRAME_pain305, gunner_frames_pain3, gunner_run)

gunner_frames_pain2 = [
	_mf(ai_move, -2, None), _mf(ai_move, 11, None), _mf(ai_move, 6, gunner_footstep),
	_mf(ai_move, 2, None), _mf(ai_move, -1, None), _mf(ai_move, -7, None),
	_mf(ai_move, -2, None), _mf(ai_move, -7, gunner_footstep)]
gunner_move_pain2 = _mm(gunner_h.FRAME_pain201, gunner_h.FRAME_pain208, gunner_frames_pain2, gunner_run)

gunner_frames_pain1 = [
	_mf(ai_move, 2, None), _mf(ai_move, 0, None), _mf(ai_move, -5, gunner_footstep),
	_mf(ai_move, 3, None), _mf(ai_move, -1, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 1, None), _mf(ai_move, 1, None), _mf(ai_move, 2, None),
	_mf(ai_move, 1, gunner_footstep), _mf(ai_move, 0, None), _mf(ai_move, -2, None),
	_mf(ai_move, -2, None), _mf(ai_move, 0, gunner_footstep), _mf(ai_move, 0, None)]
gunner_move_pain1 = _mm(gunner_h.FRAME_pain101, gunner_h.FRAME_pain118, gunner_frames_pain1, gunner_run)

gunner_frames_death = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -5, None),
	_mf(ai_move, 8, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
gunner_move_death = _mm(gunner_h.FRAME_death01, gunner_h.FRAME_death11, gunner_frames_death, gunner_dead)

gunner_frames_duck = [
	_mf(ai_move, 1, gunner_duck_down),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, gunner_duck_hold),
	_mf(ai_move, 0, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, -1, None),
	_mf(ai_move, 0, gunner_duck_up),
	_mf(ai_move, -1, None),
]
gunner_move_duck = _mm(gunner_h.FRAME_duck01, gunner_h.FRAME_duck08, gunner_frames_duck, gunner_run)

gunner_frames_attack_chain = [
	_mf(ai_charge, 0, gunner_opengun), _mf(ai_charge, 0, gunner_footstep), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None)]
gunner_move_attack_chain = _mm(gunner_h.FRAME_attak209, gunner_h.FRAME_attak215, gunner_frames_attack_chain, gunner_fire_chain)

gunner_frames_fire_chain = [
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
	_mf(ai_charge, 0, GunnerFire),
]
gunner_move_fire_chain = _mm(gunner_h.FRAME_attak216, gunner_h.FRAME_attak223, gunner_frames_fire_chain, gunner_refire_chain)

gunner_frames_endfire_chain = [
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None),
	_mf(ai_charge, 0, gunner_footstep)]
gunner_move_endfire_chain = _mm(gunner_h.FRAME_attak224, gunner_h.FRAME_attak230, gunner_frames_endfire_chain, gunner_run)

gunner_frames_attack_grenade = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GunnerGrenade),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GunnerGrenade),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GunnerGrenade),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, GunnerGrenade),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
]
gunner_move_attack_grenade = _mm(gunner_h.FRAME_attak101, gunner_h.FRAME_attak121, gunner_frames_attack_grenade, gunner_run)
