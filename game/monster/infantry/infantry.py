from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict
from game.g_monster import monster_fire_bullet, walkmonster_start
from game.g_weapon import fire_hit
from game.g_misc import ThrowGib, ThrowHead
from common.header.shared import CHAN_VOICE, CHAN_WEAPON, CHAN_BODY, ATTN_NORM, ATTN_IDLE, MZ2_INFANTRY_MACHINEGUN_1, MZ2_INFANTRY_MACHINEGUN_2
from game.header.local import FRAMETIME, MELEE_DISTANCE, GIB_ORGANIC, DEAD_DEAD, MOVETYPE_STEP, MOVETYPE_TOSS, AI_STAND_GROUND, AI_HOLD_FRAME, AI_DUCKED, RANGE_MELEE, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, damage_t

"""
#include "../../header/local.h"
#include "infantry.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.header.game import solid_t, SVF_DEADMONSTER
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.infantry import infantry_h

SOLID_BBOX = solid_t.SOLID_BBOX.value


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

def infantry_footstep(self): #edict_t *
	global sound_step, sound_step2

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0:

		sound_step = g_main.gi.soundindex("infantry/step1.wav")
		sound_step2 = g_main.gi.soundindex("infantry/step2.wav")


	if rand.randk() % 2 == 0:

		g_main.gi.sound(self, CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

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
	if not self:

		return


	self.monsterinfo.currentmove = infantry_move_stand

def infantry_fidget (self):
	#edict_t *self
	if not self:

		return


	self.monsterinfo.currentmove = infantry_move_fidget
	g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)

def infantry_search(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)

def infantry_walk (self):
	#edict_t *self
	if not self:

		return


	self.monsterinfo.currentmove = infantry_move_walk

def infantry_run (self):
	#edict_t *self
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = infantry_move_stand
	else:
		self.monsterinfo.currentmove = infantry_move_run

def infantry_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum = 1


	if g_main.level.time < self.pain_debounce_time:

		return


	self.pain_debounce_time = g_main.level.time + 3
	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	if rand.randk() % 2 == 0:

		self.monsterinfo.currentmove = infantry_move_pain1
		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)

	else:

		self.monsterinfo.currentmove = infantry_move_pain2
		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)

def InfantryMachineGun (self):
	#edict_t *self
	global sound_gunshot
	if not self:

		return


	start = [0.0, 0.0, 0.0]
	target = [0.0, 0.0, 0.0]
	forward = [0.0, 0.0, 0.0]
	right = [0.0, 0.0, 0.0]
	vec = [0.0, 0.0, 0.0]
	flash_number = 0

	if self.s.frame == infantry_h.FRAME_attak111:
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
		flash_number = MZ2_INFANTRY_MACHINEGUN_2 + (self.s.frame - infantry_h.FRAME_death211)

		shared_c.AngleVectors (self.s.angles, forward, right, None)
		G_ProjectSource (self.s.origin, flash.monster_flash_offset[flash_number], forward, right, start)

		shared.VectorSubtract (self.s.angles, aimangles[flash_number - MZ2_INFANTRY_MACHINEGUN_2], vec)
		shared_c.AngleVectors (vec, forward, None, None)

	monster_fire_bullet (self, start, forward, 3, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_number)

def infantry_sight (self, other):
	#edict_t *self, *other
	if not self:

		return


	g_main.gi.sound (self, CHAN_BODY, sound_sight, 1, ATTN_NORM, 0)

def infantry_dead (self):
	#edict_t *self
	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	g_main.gi.linkentity (self)

	g_monster.M_FlyCheck (self)

def infantry_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	"""
	int n;
	"""

	if not self:

		return


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
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.s.skinnum = 1
	# switch to bloody skin
	n = rand.randk() % 3
	if n == 0:

		self.monsterinfo.currentmove = infantry_move_death1
		g_main.gi.sound(self, CHAN_VOICE, sound_die2, 1, ATTN_NORM, 0)

	elif n == 1:

		self.monsterinfo.currentmove = infantry_move_death2
		g_main.gi.sound(self, CHAN_VOICE, sound_die1, 1, ATTN_NORM, 0)

	else:

		self.monsterinfo.currentmove = infantry_move_death3
		g_main.gi.sound(self, CHAN_VOICE, sound_die2, 1, ATTN_NORM, 0)

def infantry_duck_down (self):
	#edict_t *self
	if not self:

		return


	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity (self)

def infantry_duck_hold (self):
	#edict_t *self
	if not self:

		return


	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME

def infantry_duck_up (self):
	#edict_t *self
	if not self:

		return


	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)

def infantry_dodge(self, attacker, eta): #edict_t *, edict_t *, float

	if not self or not attacker:

		return


	if local.random() > 0.25:

		return


	if not self.enemy:

		self.enemy = attacker
		g_ai.FoundTarget(self)


	self.monsterinfo.currentmove = infantry_move_duck

def infantry_cock_gun(self): #edict_t *

	"""
	int n;
	"""

	if not self:

		return


	g_main.gi.sound(self, CHAN_WEAPON, sound_weapon_cock, 1, ATTN_NORM, 0)
	n = (rand.randk() & 15) + 3 + 7
	self.monsterinfo.pausetime = g_main.level.time + n * FRAMETIME

def infantry_fire (self):
	#edict_t *self
	if not self:

		return


	InfantryMachineGun (self)

	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME

def infantry_swing (self):
	#edict_t *self
	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_punch_swing, 1, ATTN_NORM, 0)

def infantry_smack(self): #edict_t *

	"""
	vec3_t aim;
	"""
	aim = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	shared.VectorSet(aim, MELEE_DISTANCE, 0, 0)
	if fire_hit(self, aim, (5 + (rand.randk() % 5)), 50):

		g_main.gi.sound(self, CHAN_WEAPON, sound_punch_hit, 1, ATTN_NORM, 0)

def infantry_attack(self): #edict_t *

	if not self:

		return


	if g_ai.ai_range(self, self.enemy) == RANGE_MELEE:

		self.monsterinfo.currentmove = infantry_move_attack2

	else:

		self.monsterinfo.currentmove = infantry_move_attack1

"""
QUAKED monster_infantry (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_infantry(self): #edict_t *
	global sound_die1, sound_die2, sound_gunshot, sound_idle, sound_pain1, sound_pain2, sound_punch_hit, sound_punch_swing, sound_search, sound_sight, sound_step, sound_step2, sound_weapon_cock

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_pain1 = g_main.gi.soundindex("infantry/infpain1.wav")
	sound_pain2 = g_main.gi.soundindex("infantry/infpain2.wav")
	sound_die1 = g_main.gi.soundindex("infantry/infdeth1.wav")
	sound_die2 = g_main.gi.soundindex("infantry/infdeth2.wav")
	sound_gunshot = g_main.gi.soundindex("infantry/infatck1.wav")
	sound_weapon_cock = g_main.gi.soundindex("infantry/infatck3.wav")
	sound_punch_swing = g_main.gi.soundindex("infantry/infatck2.wav")
	sound_punch_hit = g_main.gi.soundindex("infantry/melee2.wav")
	sound_sight = g_main.gi.soundindex("infantry/infsght1.wav")
	sound_search = g_main.gi.soundindex("infantry/infsrch1.wav")
	sound_idle = g_main.gi.soundindex("infantry/infidle1.wav")
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.s.modelindex = g_main.gi.modelindex("models/monsters/infantry/tris.md2")
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 32)
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
	self.monsterinfo.search = infantry_search
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = infantry_move_stand
	self.monsterinfo.scale = infantry_h.MODEL_SCALE
	walkmonster_start(self)

#=================
# move tables
#=================
infantry_frames_stand = [_mf(ai_stand, 0, None)] * 22
infantry_move_stand = _mm(infantry_h.FRAME_stand50, infantry_h.FRAME_stand71, infantry_frames_stand, None)

infantry_frames_fidget = [
	_mf(ai_stand, 1, None), _mf(ai_stand, 0, None), _mf(ai_stand, 1, None),
	_mf(ai_stand, 3, None), _mf(ai_stand, 6, None), _mf(ai_stand, 3, infantry_footstep),
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
	_mf(ai_stand, -2, None), _mf(ai_stand, -3, None), _mf(ai_stand, -3, infantry_footstep),
	_mf(ai_stand, -2, None)]
infantry_move_fidget = _mm(infantry_h.FRAME_stand01, infantry_h.FRAME_stand49, infantry_frames_fidget, infantry_stand)

infantry_frames_walk = [
	_mf(ai_walk, 5, infantry_footstep), _mf(ai_walk, 4, None), _mf(ai_walk, 4, None),
	_mf(ai_walk, 5, None), _mf(ai_walk, 4, None), _mf(ai_walk, 5, None),
	_mf(ai_walk, 6, infantry_footstep), _mf(ai_walk, 4, None), _mf(ai_walk, 4, None),
	_mf(ai_walk, 4, None), _mf(ai_walk, 4, None), _mf(ai_walk, 5, None)]
infantry_move_walk = _mm(infantry_h.FRAME_walk03, infantry_h.FRAME_walk14, infantry_frames_walk, None)

infantry_frames_run = [
	_mf(ai_run, 10, None), _mf(ai_run, 20, infantry_footstep), _mf(ai_run, 5, None),
	_mf(ai_run, 7, None), _mf(ai_run, 30, None), _mf(ai_run, 35, infantry_footstep),
	_mf(ai_run, 2, None), _mf(ai_run, 6, None)]
infantry_move_run = _mm(infantry_h.FRAME_run01, infantry_h.FRAME_run08, infantry_frames_run, None)

infantry_frames_pain1 = [
	_mf(ai_move, -3, None), _mf(ai_move, -2, None), _mf(ai_move, -1, None),
	_mf(ai_move, -2, None), _mf(ai_move, -1, infantry_footstep), _mf(ai_move, 1, None),
	_mf(ai_move, -1, None), _mf(ai_move, 1, None), _mf(ai_move, 6, None),
	_mf(ai_move, 2, infantry_footstep)]
infantry_move_pain1 = _mm(infantry_h.FRAME_pain101, infantry_h.FRAME_pain110, infantry_frames_pain1, infantry_run)

infantry_frames_pain2 = [
	_mf(ai_move, -3, None), _mf(ai_move, -3, None), _mf(ai_move, 0, None),
	_mf(ai_move, -1, None), _mf(ai_move, -2, infantry_footstep), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 2, None), _mf(ai_move, 5, None),
	_mf(ai_move, 2, infantry_footstep)]
infantry_move_pain2 = _mm(infantry_h.FRAME_pain201, infantry_h.FRAME_pain210, infantry_frames_pain2, infantry_run)

infantry_frames_death1 = [
	_mf(ai_move, -4, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, -1, None), _mf(ai_move, -4, infantry_footstep), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -1, infantry_footstep),
	_mf(ai_move, 3, None), _mf(ai_move, 1, None), _mf(ai_move, 1, None),
	_mf(ai_move, -2, None), _mf(ai_move, 2, None), _mf(ai_move, 2, None),
	_mf(ai_move, 9, None), _mf(ai_move, 9, None), _mf(ai_move, 5, None),
	_mf(ai_move, -3, None), _mf(ai_move, -3, None)]
infantry_move_death1 = _mm(infantry_h.FRAME_death101, infantry_h.FRAME_death120, infantry_frames_death1, infantry_dead)

infantry_frames_death2 = [
	_mf(ai_move, 0, None), _mf(ai_move, 1, None), _mf(ai_move, 5, None),
	_mf(ai_move, -1, None), _mf(ai_move, 0, None), _mf(ai_move, 1, infantry_footstep),
	_mf(ai_move, 1, infantry_footstep), _mf(ai_move, 4, None), _mf(ai_move, 3, None),
	_mf(ai_move, 0, None), _mf(ai_move, -2, InfantryMachineGun), _mf(ai_move, -2, InfantryMachineGun),
	_mf(ai_move, -3, InfantryMachineGun), _mf(ai_move, -1, InfantryMachineGun), _mf(ai_move, -2, InfantryMachineGun),
	_mf(ai_move, 0, InfantryMachineGun), _mf(ai_move, 2, InfantryMachineGun), _mf(ai_move, 2, InfantryMachineGun),
	_mf(ai_move, 3, InfantryMachineGun), _mf(ai_move, -10, InfantryMachineGun), _mf(ai_move, -7, InfantryMachineGun),
	_mf(ai_move, -8, InfantryMachineGun), _mf(ai_move, -6, None), _mf(ai_move, 4, None),
	_mf(ai_move, 0, None)]
infantry_move_death2 = _mm(infantry_h.FRAME_death201, infantry_h.FRAME_death225, infantry_frames_death2, infantry_dead)

infantry_frames_death3 = [
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, -6, None), _mf(ai_move, -11, None), _mf(ai_move, -3, None),
	_mf(ai_move, -11, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
infantry_move_death3 = _mm(infantry_h.FRAME_death301, infantry_h.FRAME_death309, infantry_frames_death3, infantry_dead)

infantry_frames_duck = [
	_mf(ai_move, -2, infantry_duck_down), _mf(ai_move, -5, infantry_duck_hold), _mf(ai_move, 3, None),
	_mf(ai_move, 4, infantry_duck_up), _mf(ai_move, 0, infantry_footstep)]
infantry_move_duck = _mm(infantry_h.FRAME_duck01, infantry_h.FRAME_duck05, infantry_frames_duck, infantry_run)

infantry_frames_attack1 = [
	_mf(ai_charge, 4, None), _mf(ai_charge, -1, None), _mf(ai_charge, -1, None),
	_mf(ai_charge, 0, infantry_cock_gun), _mf(ai_charge, -1, None),
	_mf(ai_charge, 1, None), _mf(ai_charge, 1, None), _mf(ai_charge, 2, None),
	_mf(ai_charge, -2, None), _mf(ai_charge, -3, None), _mf(ai_charge, 1, infantry_fire),
	_mf(ai_charge, 5, None), _mf(ai_charge, -1, None), _mf(ai_charge, -2, None),
	_mf(ai_charge, -3, None)]
infantry_move_attack1 = _mm(infantry_h.FRAME_attak101, infantry_h.FRAME_attak115, infantry_frames_attack1, infantry_run)

infantry_frames_attack2 = [
	_mf(ai_charge, 3, None), _mf(ai_charge, 6, None), _mf(ai_charge, 0, infantry_swing),
	_mf(ai_charge, 8, infantry_footstep), _mf(ai_charge, 5, None), _mf(ai_charge, 8, infantry_smack),
	_mf(ai_charge, 6, None), _mf(ai_charge, 3, None)]
infantry_move_attack2 = _mm(infantry_h.FRAME_attak201, infantry_h.FRAME_attak208, infantry_frames_attack2, infantry_run)
