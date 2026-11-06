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

Mutant.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_combat import (T_Damage)
from game.header.local import AI_DUCKED, AI_STAND_GROUND, AS_MELEE, AS_MISSILE, DEAD_DEAD, GIB_ORGANIC, MELEE_DISTANCE, MOD_UNKNOWN, MOVETYPE_STEP, MOVETYPE_TOSS, RANGE_MELEE, damage_t
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (M_FlyCheck, walkmonster_start)
from game.g_utils import G_FreeEdict
from game.g_weapon import (fire_hit)
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from game.monster.misc.move import M_CheckBottom
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_VOICE, CHAN_WEAPON
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from game.monster.mutant import mutant_h

"""
#include "../../header/local.h"
#include "mutant.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value

# m_mutant.h


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

sound_swing = 0 # static
sound_hit = 0 # static
sound_hit2 = 0 # static
sound_death = 0 # static
sound_idle = 0 # static
sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_sight = 0 # static
sound_search = 0 # static
sound_step1 = 0 # static
sound_step2 = 0 # static
sound_step3 = 0 # static
sound_thud = 0 # static


"""
==============================================================================

mutant

==============================================================================
"""
def mutant_step(self): #edict_t *

	"""
	int n;
	"""

	if not self:

		return


	n = (rand.randk() + 1) % 3
	if n == 0:

		g_main.gi.sound(self, CHAN_VOICE, sound_step1, 1, ATTN_NORM, 0)

	elif n == 1:

		g_main.gi.sound(self, CHAN_VOICE, sound_step2, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_step3, 1, ATTN_NORM, 0)


def mutant_sight (self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def mutant_search (self): #edict_t *

	g_main.gi.sound (self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def mutant_swing (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_VOICE, sound_swing, 1, ATTN_NORM, 0)


def mutant_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = mutant_move_stand


def mutant_idle_loop (self): #edict_t *

	if not self:

		return


	if local.random() < 0.75:
		self.monsterinfo.nextframe = mutant_h.FRAME_stand155


def mutant_idle (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = mutant_move_idle
	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)


def mutant_walk_loop (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = mutant_move_walk


def mutant_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = mutant_move_start_walk


def mutant_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = mutant_move_stand
	else:
		self.monsterinfo.currentmove = mutant_move_run


def mutant_hit_left(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.mins[0], 8)
	if fire_hit(self, aim, (10 + (rand.randk() % 5)), 100):

		g_main.gi.sound(self, CHAN_WEAPON, sound_hit, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_WEAPON, sound_swing, 1, ATTN_NORM, 0)


def mutant_hit_right(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, self.maxs[0], 8)
	if fire_hit(self, aim, (10 + (rand.randk() % 5)), 100):

		g_main.gi.sound(self, CHAN_WEAPON, sound_hit2, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_WEAPON, sound_swing, 1, ATTN_NORM, 0)


def mutant_check_refire(self): #edict_t *

	if not self:

		return


	if not self.enemy or not self.enemy.inuse or (self.enemy.health <= 0):

		return


	if ((g_main.skill.value == local.SKILL_HARDPLUS) and (local.random() < 0.5)) or (g_ai.ai_range(self, self.enemy) == RANGE_MELEE):

		self.monsterinfo.nextframe = mutant_h.FRAME_attack09


def mutant_melee (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = mutant_move_attack


def mutant_jump_touch (self, other, plane, surf): #edict_t *, edict_t *, cplane_t *, csurface_t *

	if not self:

		return


	if self.health <= 0:
		self.touch = None
		return

	if other.takedamage:
		if shared_c.VectorLength(self.velocity) > 400:
			point = np.zeros((3,), dtype=np.float32) #vec3_t
			normal = np.zeros((3,), dtype=np.float32) #vec3_t
			#int	damage;

			shared.VectorCopy (self.velocity, normal)
			shared_c.VectorNormalize(normal)
			shared_c.VectorMA (self.s.origin, self.maxs[0], normal, point)
			damage = 40 + 10 * local.random()
			T_Damage (other, self, self, self.velocity, point, normal, damage, damage, 0, MOD_UNKNOWN)

	if not M_CheckBottom (self):
		if self.groundentity:
			self.monsterinfo.nextframe = mutant_h.FRAME_attack02
			self.touch = None
		return

	self.touch = None


def mutant_jump_takeoff (self): #edict_t *

	if not self:

		return


	forward = np.zeros((3,), dtype=np.float32) #vec3_t

	g_main.gi.sound (self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)
	shared_c.AngleVectors (self.s.angles, forward, None, None)
	self.s.origin[2] += 1
	shared_c.VectorScale (forward, 600, self.velocity)
	self.velocity[2] = 250
	self.groundentity = None
	self.monsterinfo.aiflags |= AI_DUCKED
	self.monsterinfo.attack_finished = g_main.level.time + 3
	self.touch = mutant_jump_touch


def mutant_check_landing (self): #edict_t *

	if not self:

		return


	if self.groundentity:
		g_main.gi.sound (self, CHAN_WEAPON, sound_thud, 1, ATTN_NORM, 0)
		self.monsterinfo.attack_finished = 0
		self.monsterinfo.aiflags &= ~AI_DUCKED
		return

	if g_main.level.time > self.monsterinfo.attack_finished:
		self.monsterinfo.nextframe = mutant_h.FRAME_attack02
	else:
		self.monsterinfo.nextframe = mutant_h.FRAME_attack05


def mutant_jump (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = mutant_move_jump


def mutant_check_melee(self): #edict_t * (returns qboolean)

	if not self:

		return False


	if g_ai.ai_range(self, self.enemy) == RANGE_MELEE:

		return True


	return False


def mutant_check_jump (self): #edict_t *

	if not self:

		return False


	v = np.zeros((3,), dtype=np.float32) #vec3_t
	#float	distance;

	if self.absmin[2] > (self.enemy.absmin[2] + 0.75 * self.enemy.size[2]):
		return False

	if self.absmax[2] < (self.enemy.absmin[2] + 0.25 * self.enemy.size[2]):
		return False

	v[0] = self.s.origin[0] - self.enemy.s.origin[0]
	v[1] = self.s.origin[1] - self.enemy.s.origin[1]
	v[2] = 0
	distance = shared_c.VectorLength(v)

	if distance < 100:
		return False
	if distance > 100:
		if local.random() < 0.9:
			return False

	return True


def mutant_checkattack (self): #edict_t *

	if not self:

		return False


	if not self.enemy or self.enemy.health <= 0:
		return False

	if mutant_check_melee(self):
		self.monsterinfo.attack_state = AS_MELEE
		return True

	if mutant_check_jump(self):
		self.monsterinfo.attack_state = AS_MISSILE
		# FIXME play a jump sound here
		return True

	return False


def mutant_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	"""
	float r;
	"""

	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		return


	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	r = local.random()
	if r < 0.33:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = mutant_move_pain1

	elif r < 0.66:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = mutant_move_pain2

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)
		self.monsterinfo.currentmove = mutant_move_pain3


def mutant_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	g_main.gi.linkentity (self)

	M_FlyCheck (self)


def mutant_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	if not self:

		return


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

	g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.s.skinnum = 1

	if local.random() < 0.5:
		self.monsterinfo.currentmove = mutant_move_death1
	else:
		self.monsterinfo.currentmove = mutant_move_death2


"""QUAKED monster_mutant (1 .5 0) (-32 -32 -24) (32 32 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_mutant (self): #edict_t *

	global sound_swing, sound_hit, sound_hit2, sound_death, sound_idle, sound_pain1, sound_pain2, sound_sight, sound_search, sound_step1, sound_step2, sound_step3, sound_thud
	if not self:

		return


	if g_main.deathmatch.value:
		G_FreeEdict (self)
		return

	sound_swing = g_main.gi.soundindex ("mutant/mutatck1.wav")
	sound_hit = g_main.gi.soundindex ("mutant/mutatck2.wav")
	sound_hit2 = g_main.gi.soundindex ("mutant/mutatck3.wav")
	sound_death = g_main.gi.soundindex ("mutant/mutdeth1.wav")
	sound_idle = g_main.gi.soundindex ("mutant/mutidle1.wav")
	sound_pain1 = g_main.gi.soundindex ("mutant/mutpain1.wav")
	sound_pain2 = g_main.gi.soundindex ("mutant/mutpain2.wav")
	sound_sight = g_main.gi.soundindex ("mutant/mutsght1.wav")
	sound_search = g_main.gi.soundindex ("mutant/mutsrch1.wav")
	sound_step1 = g_main.gi.soundindex ("mutant/step1.wav")
	sound_step2 = g_main.gi.soundindex ("mutant/step2.wav")
	sound_step3 = g_main.gi.soundindex ("mutant/step3.wav")
	sound_thud = g_main.gi.soundindex ("mutant/thud1.wav")

	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex ("models/monsters/mutant/tris.md2")
	shared.VectorSet (self.mins, -32, -32, -24)
	shared.VectorSet (self.maxs, 32, 32, 48)

	self.health = 300
	self.gib_health = -120
	self.mass = 300

	self.pain = mutant_pain
	self.die = mutant_die

	self.monsterinfo.stand = mutant_stand
	self.monsterinfo.walk = mutant_walk
	self.monsterinfo.run = mutant_run
	self.monsterinfo.dodge = None
	self.monsterinfo.attack = mutant_jump
	self.monsterinfo.melee = mutant_melee
	self.monsterinfo.sight = mutant_sight
	self.monsterinfo.search = mutant_search
	self.monsterinfo.idle = mutant_idle
	self.monsterinfo.checkattack = mutant_checkattack

	g_main.gi.linkentity (self)

	self.monsterinfo.currentmove = mutant_move_stand

	self.monsterinfo.scale = mutant_h.MODEL_SCALE
	walkmonster_start (self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
mutant_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),	# 10
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),	# 20
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),	# 30
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),	# 40
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),	# 50
	_mf(ai_stand, 0, None),
]
mutant_move_stand = _mm(mutant_h.FRAME_stand101, mutant_h.FRAME_stand151, mutant_frames_stand, None)

mutant_frames_idle = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),	# scratch loop start
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, mutant_idle_loop),	# scratch loop end
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
mutant_move_idle = _mm(mutant_h.FRAME_stand152, mutant_h.FRAME_stand164, mutant_frames_idle, mutant_stand)

mutant_frames_walk = [
	_mf(ai_walk, 3, mutant_step), _mf(ai_walk, 1, None), _mf(ai_walk, 5, mutant_step),
	_mf(ai_walk, 10, None), _mf(ai_walk, 13, None), _mf(ai_walk, 10, None),
	_mf(ai_walk, 0, mutant_step), _mf(ai_walk, 5, None), _mf(ai_walk, 6, None),
	_mf(ai_walk, 16, None), _mf(ai_walk, 15, None), _mf(ai_walk, 6, None)]
mutant_move_walk = _mm(mutant_h.FRAME_walk05, mutant_h.FRAME_walk16, mutant_frames_walk, None)

mutant_frames_start_walk = [
	_mf(ai_walk, 5, None), _mf(ai_walk, 5, None), _mf(ai_walk, -2, mutant_step),
	_mf(ai_walk, 1, None)]
mutant_move_start_walk = _mm(mutant_h.FRAME_walk01, mutant_h.FRAME_walk04, mutant_frames_start_walk, mutant_walk_loop)

mutant_frames_run = [
	_mf(ai_run, 40, None),
	_mf(ai_run, 40, mutant_step),
	_mf(ai_run, 24, None),
	_mf(ai_run, 5, mutant_step),
	_mf(ai_run, 17, None),
	_mf(ai_run, 10, None),
]
mutant_move_run = _mm(mutant_h.FRAME_run03, mutant_h.FRAME_run08, mutant_frames_run, None)

mutant_frames_attack = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, mutant_hit_left),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, mutant_hit_right),
	_mf(ai_charge, 0, mutant_check_refire),
]
mutant_move_attack = _mm(mutant_h.FRAME_attack09, mutant_h.FRAME_attack15, mutant_frames_attack, mutant_run)

mutant_frames_jump = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 17, None),
	_mf(ai_charge, 15, mutant_jump_takeoff),
	_mf(ai_charge, 15, None),
	_mf(ai_charge, 15, mutant_check_landing),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 0, None),
]
mutant_move_jump = _mm(mutant_h.FRAME_attack01, mutant_h.FRAME_attack08, mutant_frames_jump, mutant_run)

mutant_frames_pain1 = [
	_mf(ai_move, 4, None),
	_mf(ai_move, -3, None),
	_mf(ai_move, -8, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 5, None),
]
mutant_move_pain1 = _mm(mutant_h.FRAME_pain101, mutant_h.FRAME_pain105, mutant_frames_pain1, mutant_run)

mutant_frames_pain2 = [
	_mf(ai_move, -24, None),
	_mf(ai_move, 11, None),
	_mf(ai_move, 5, None),
	_mf(ai_move, -2, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 4, None),
]
mutant_move_pain2 = _mm(mutant_h.FRAME_pain201, mutant_h.FRAME_pain206, mutant_frames_pain2, mutant_run)

mutant_frames_pain3 = [
	_mf(ai_move, -22, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 1, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 3, None),
	_mf(ai_move, 2, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 1, None),
]
mutant_move_pain3 = _mm(mutant_h.FRAME_pain301, mutant_h.FRAME_pain311, mutant_frames_pain3, mutant_run)

mutant_frames_death1 = [
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
mutant_move_death1 = _mm(mutant_h.FRAME_death101, mutant_h.FRAME_death109, mutant_frames_death1, mutant_dead)

mutant_frames_death2 = [
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
mutant_move_death2 = _mm(mutant_h.FRAME_death201, mutant_h.FRAME_death210, mutant_frames_death2, mutant_dead)
