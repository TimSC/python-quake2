from __future__ import annotations
from common.shared import rand

import numpy as np
from game import g_main, g_utils, g_monster, g_misc, g_ai
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict, vectoangles
from game.g_monster import monster_fire_bullet, monster_fire_blaster, monster_fire_shotgun, walkmonster_start
from game.g_misc import ThrowGib, ThrowHead
from common.header.shared import CHAN_VOICE, CHAN_WEAPON, ATTN_NORM, ATTN_IDLE, EF_BLASTER, MZ2_SOLDIER_BLASTER_1, MZ2_SOLDIER_BLASTER_2, MZ2_SOLDIER_BLASTER_3, MZ2_SOLDIER_BLASTER_4, MZ2_SOLDIER_BLASTER_5, MZ2_SOLDIER_BLASTER_6, MZ2_SOLDIER_BLASTER_7, MZ2_SOLDIER_BLASTER_8, MZ2_SOLDIER_SHOTGUN_1, MZ2_SOLDIER_SHOTGUN_2, MZ2_SOLDIER_SHOTGUN_3, MZ2_SOLDIER_SHOTGUN_4, MZ2_SOLDIER_SHOTGUN_5, MZ2_SOLDIER_SHOTGUN_6, MZ2_SOLDIER_SHOTGUN_7, MZ2_SOLDIER_SHOTGUN_8, MZ2_SOLDIER_MACHINEGUN_1, MZ2_SOLDIER_MACHINEGUN_2, MZ2_SOLDIER_MACHINEGUN_3, MZ2_SOLDIER_MACHINEGUN_4, MZ2_SOLDIER_MACHINEGUN_5, MZ2_SOLDIER_MACHINEGUN_6, MZ2_SOLDIER_MACHINEGUN_7, MZ2_SOLDIER_MACHINEGUN_8
from game.header.local import FRAMETIME, GIB_ORGANIC, DEAD_DEAD, MOVETYPE_TOSS, MOVETYPE_STEP, AI_STAND_GROUND, AI_HOLD_FRAME, AI_DUCKED, RANGE_MELEE, RANGE_MID, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, crandom, damage_t

"""
#include "../../header/local.h"
#include "soldier.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.header.game import solid_t, SVF_DEADMONSTER
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from game.header import local
from game.monster.soldier import soldier_h

SOLID_BBOX = solid_t.SOLID_BBOX.value



sound_idle = 0
sound_sight1 = 0
sound_sight2 = 0
sound_pain_light = 0
sound_pain = 0
sound_pain_ss = 0
sound_death_light = 0
sound_death = 0
sound_death_ss = 0
sound_cock = 0

sound_step = 0 #static int
sound_step2 = 0 #static int
sound_step3 = 0 #static int
sound_step4 = 0 #static int

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

def soldier_footstep(self): #edict_t *
	global sound_step, sound_step2, sound_step3, sound_step4

	"""
	int i;
	"""

	if not g_main.g_monsterfootsteps.value:

		return


	# Lazy loading for savegame compatibility.
	if sound_step == 0 or sound_step2 == 0 or sound_step3 == 0 or sound_step4 == 0:

		sound_step = g_main.gi.soundindex("player/step1.wav")
		sound_step2 = g_main.gi.soundindex("player/step2.wav")
		sound_step3 = g_main.gi.soundindex("player/step3.wav")
		sound_step4 = g_main.gi.soundindex("player/step4.wav")


	i = rand.randk() % 4
	if i == 0:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step, 1, ATTN_NORM, 0)

	elif i == 1:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step2, 1, ATTN_NORM, 0)

	elif i == 2:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step3, 1, ATTN_NORM, 0)

	elif i == 3:

		g_main.gi.sound(self, shared.CHAN_BODY, sound_step4, 1, ATTN_NORM, 0)

blaster_flash = [MZ2_SOLDIER_BLASTER_1, MZ2_SOLDIER_BLASTER_2, MZ2_SOLDIER_BLASTER_3, MZ2_SOLDIER_BLASTER_4, MZ2_SOLDIER_BLASTER_5, MZ2_SOLDIER_BLASTER_6, MZ2_SOLDIER_BLASTER_7, MZ2_SOLDIER_BLASTER_8]
shotgun_flash = [MZ2_SOLDIER_SHOTGUN_1, MZ2_SOLDIER_SHOTGUN_2, MZ2_SOLDIER_SHOTGUN_3, MZ2_SOLDIER_SHOTGUN_4, MZ2_SOLDIER_SHOTGUN_5, MZ2_SOLDIER_SHOTGUN_6, MZ2_SOLDIER_SHOTGUN_7, MZ2_SOLDIER_SHOTGUN_8]
machinegun_flash = [MZ2_SOLDIER_MACHINEGUN_1, MZ2_SOLDIER_MACHINEGUN_2, MZ2_SOLDIER_MACHINEGUN_3, MZ2_SOLDIER_MACHINEGUN_4, MZ2_SOLDIER_MACHINEGUN_5, MZ2_SOLDIER_MACHINEGUN_6, MZ2_SOLDIER_MACHINEGUN_7, MZ2_SOLDIER_MACHINEGUN_8]

def soldier_idle (self):
	#edict_t *self
	if not self:

		return


	if local.random() > 0.8:
		g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)

def soldier_cock (self):
	#edict_t *self
	global sound_cock
	if not self:

		return


	if self.s.frame == soldier_h.FRAME_stand322:
		g_main.gi.sound (self, CHAN_WEAPON, sound_cock, 1, ATTN_IDLE, 0)
	else:
		g_main.gi.sound (self, CHAN_WEAPON, sound_cock, 1, ATTN_NORM, 0)

def soldier_stand (self):
	#edict_t *self
	if not self:

		return


	if (self.monsterinfo.currentmove == soldier_move_stand3) or (local.random() < 0.8):
		self.monsterinfo.currentmove = soldier_move_stand1
	else:
		self.monsterinfo.currentmove = soldier_move_stand3

def soldier_walk1_random (self):
	#edict_t *self
	if not self:

		return


	if local.random() > 0.1:
		self.monsterinfo.nextframe = soldier_h.FRAME_walk101

def soldier_walk (self):
	#edict_t *self
	if not self:

		return


	if local.random() < 0.5:
		self.monsterinfo.currentmove = soldier_move_walk1
	else:
		self.monsterinfo.currentmove = soldier_move_walk2

def soldier_run (self):
	#edict_t *self
	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = soldier_move_stand1
		return

	if self.monsterinfo.currentmove == soldier_move_walk1 or \
		self.monsterinfo.currentmove == soldier_move_walk2 or \
		self.monsterinfo.currentmove == soldier_move_start_run:
		self.monsterinfo.currentmove = soldier_move_run
	else:
		self.monsterinfo.currentmove = soldier_move_start_run

def soldier_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

	"""
	float r;
	int n;
	"""

	if not self:

		return


	if self.health < (self.max_health / 2):

		self.s.skinnum |= 1


	if g_main.level.time < self.pain_debounce_time:

		if (self.velocity[2] > 100) and ((self.monsterinfo.currentmove == soldier_move_pain1) or (self.monsterinfo.currentmove == soldier_move_pain2) or (self.monsterinfo.currentmove == soldier_move_pain3)):

			self.monsterinfo.currentmove = soldier_move_pain4


		return


	self.pain_debounce_time = g_main.level.time + 3
	n = self.s.skinnum | 1
	if n == 1:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain_light, 1, ATTN_NORM, 0)

	elif n == 3:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain_ss, 1, ATTN_NORM, 0)


	if self.velocity[2] > 100:

		self.monsterinfo.currentmove = soldier_move_pain4
		return


	if g_main.skill.value == local.SKILL_HARDPLUS:

		return
		# no pain anims in nightmare


	r = local.random()
	if r < 0.33:

		self.monsterinfo.currentmove = soldier_move_pain1

	elif r < 0.66:

		self.monsterinfo.currentmove = soldier_move_pain2

	else:

		self.monsterinfo.currentmove = soldier_move_pain3

def soldier_fire(self, flash_number): #edict_t *, int

	"""
	vec3_t start;
	vec3_t forward, right, up;
	vec3_t aim;
	vec3_t dir;
	vec3_t end;
	float r, u;
	int flash_index;
	"""
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	aim = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	if not self:

		return


	if self.s.skinnum < 2:

		flash_index = blaster_flash[flash_number]

	elif self.s.skinnum < 4:

		flash_index = shotgun_flash[flash_number]

	else:

		flash_index = machinegun_flash[flash_number]


	shared_c.AngleVectors(self.s.angles, forward, right, None)
	G_ProjectSource(self.s.origin, flash.monster_flash_offset[flash_index], forward, right, start)
	if (flash_number == 5) or (flash_number == 6):

		shared.VectorCopy(forward, aim)

	else:

		shared.VectorCopy(self.enemy.s.origin, end)
		end[2] += self.enemy.viewheight
		shared.VectorSubtract(end, start, aim)
		vectoangles(aim, dir)
		shared_c.AngleVectors(dir, forward, right, up)
		r = crandom() * 1000
		u = crandom() * 500
		shared_c.VectorMA(start, 8192, forward, end)
		shared_c.VectorMA(end, r, right, end)
		shared_c.VectorMA(end, u, up, end)
		shared.VectorSubtract(end, start, aim)
		shared_c.VectorNormalize(aim)


	if self.s.skinnum <= 1:

		monster_fire_blaster(self, start, aim, 5, 600, flash_index, EF_BLASTER)

	elif self.s.skinnum <= 3:

		monster_fire_shotgun(self, start, aim, 2, 1, local.DEFAULT_SHOTGUN_HSPREAD, local.DEFAULT_SHOTGUN_VSPREAD, local.DEFAULT_SHOTGUN_COUNT, flash_index)

	else:

		if not (self.monsterinfo.aiflags & AI_HOLD_FRAME):

			self.monsterinfo.pausetime = g_main.level.time + (3 + rand.randk() % 8) * FRAMETIME


		monster_fire_bullet(self, start, aim, 2, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_index)
		if g_main.level.time >= self.monsterinfo.pausetime:

			self.monsterinfo.aiflags &= ~AI_HOLD_FRAME

		else:

			self.monsterinfo.aiflags |= AI_HOLD_FRAME

def soldier_fire1 (self):
	#edict_t *self
	if not self:

		return


	soldier_fire (self, 0)

def soldier_attack1_refire1(self): #edict_t *

	if not self:

		return


	if self.s.skinnum > 1:

		return


	if self.enemy.health <= 0:

		return


	if ((g_main.skill.value == local.SKILL_HARDPLUS) and (local.random() < 0.5)) or (g_ai.ai_range(self, self.enemy) == RANGE_MELEE):

		self.monsterinfo.nextframe = soldier_h.FRAME_attak102

	else:

		self.monsterinfo.nextframe = soldier_h.FRAME_attak110

def soldier_attack1_refire2(self): #edict_t *

	if not self:

		return


	if self.s.skinnum < 2:

		return


	if self.enemy.health <= 0:

		return


	if ((g_main.skill.value == local.SKILL_HARDPLUS) and (local.random() < 0.5)) or (g_ai.ai_range(self, self.enemy) == RANGE_MELEE):

		self.monsterinfo.nextframe = soldier_h.FRAME_attak102

def soldier_fire2 (self):
	#edict_t *self
	if not self:

		return


	soldier_fire (self, 1)

def soldier_attack2_refire1(self): #edict_t *

	if not self:

		return


	if self.s.skinnum > 1:

		return


	if self.enemy.health <= 0:

		return


	if ((g_main.skill.value == local.SKILL_HARDPLUS) and (local.random() < 0.5)) or (g_ai.ai_range(self, self.enemy) == RANGE_MELEE):

		self.monsterinfo.nextframe = soldier_h.FRAME_attak204

	else:

		self.monsterinfo.nextframe = soldier_h.FRAME_attak216

def soldier_attack2_refire2(self): #edict_t *

	if not self:

		return


	if self.s.skinnum < 2:

		return


	if self.enemy.health <= 0:

		return


	if ((g_main.skill.value == local.SKILL_HARDPLUS) and (local.random() < 0.5)) or (g_ai.ai_range(self, self.enemy) == RANGE_MELEE):

		self.monsterinfo.nextframe = soldier_h.FRAME_attak204

def soldier_duck_down (self):
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

def soldier_duck_up (self):
	#edict_t *self
	if not self:

		return


	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)

def soldier_fire3 (self):
	#edict_t *self
	if not self:

		return


	soldier_duck_down (self)
	soldier_fire (self, 2)

def soldier_attack3_refire (self):
	#edict_t *self
	if not self:

		return


	if (g_main.level.time + 0.4) < self.monsterinfo.pausetime:
		self.monsterinfo.nextframe = soldier_h.FRAME_attak303

def soldier_fire4 (self):
	#edict_t *self
	if not self:

		return


	soldier_fire (self, 3)
	#
	# if (self->enemy->health <= 0)
	# 	return
	#
	# if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
	# 	self->monsterinfo.nextframe = FRAME_attak402

def soldier_fire8 (self):
	#edict_t *self
	if not self:

		return


	soldier_fire (self, 7)

def soldier_attack6_refire(self): #edict_t *

	if not self:

		return


	if self.enemy.health <= 0:

		return


	if g_ai.ai_range(self, self.enemy) < RANGE_MID:

		return


	if g_main.skill.value == local.SKILL_HARDPLUS:

		self.monsterinfo.nextframe = soldier_h.FRAME_runs03

def soldier_attack (self):
	#edict_t *self
	if not self:

		return


	if self.s.skinnum < 4:
		if local.random() < 0.5:
			self.monsterinfo.currentmove = soldier_move_attack1
		else:
			self.monsterinfo.currentmove = soldier_move_attack2
	else:
		self.monsterinfo.currentmove = soldier_move_attack4

def soldier_sight(self, other): #edict_t *, edict_t *

	if not self:

		return


	if local.random() < 0.5:

		g_main.gi.sound(self, CHAN_VOICE, sound_sight1, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_sight2, 1, ATTN_NORM, 0)


	if (g_main.skill.value > local.SKILL_EASY) and (g_ai.ai_range(self, self.enemy) >= RANGE_MID):

		if local.random() > 0.5:

			self.monsterinfo.currentmove = soldier_move_attack6

def soldier_duck_hold (self):
	#edict_t *self
	if not self:

		return


	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME

def soldier_dodge(self, attacker, eta): #edict_t *, edict_t *, float

	"""
	float r;
	"""

	if not self or not attacker:

		return


	r = local.random()
	if r > 0.25:

		return


	if not self.enemy:

		self.enemy = attacker
		g_ai.FoundTarget(self)


	if g_main.skill.value == local.SKILL_EASY:

		self.monsterinfo.currentmove = soldier_move_duck
		return


	self.monsterinfo.pausetime = g_main.level.time + eta + 0.3
	r = local.random()
	if g_main.skill.value == local.SKILL_MEDIUM:

		if r > 0.33:

			self.monsterinfo.currentmove = soldier_move_duck

		else:

			self.monsterinfo.currentmove = soldier_move_attack3


		return


	if g_main.skill.value >= local.SKILL_HARD:

		if r > 0.66:

			self.monsterinfo.currentmove = soldier_move_duck

		else:

			self.monsterinfo.currentmove = soldier_move_attack3


		return


	self.monsterinfo.currentmove = soldier_move_attack3

def soldier_fire6 (self):
	#edict_t *self
	if not self:

		return


	soldier_fire (self, 5)

def soldier_fire7 (self):
	#edict_t *self
	if not self:

		return


	soldier_fire (self, 6)

def soldier_dead (self):
	#edict_t *self
	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)

def soldier_die(self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, const vec3_t

	"""
	int n;
	"""

	# check for gib
	if self.health <= self.gib_health:

		g_main.gi.sound(self, CHAN_VOICE, g_main.gi.soundindex("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(3):

			ThrowGib(self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)


		ThrowGib(self, "models/objects/gibs/chest/tris.md2", damage, GIB_ORGANIC)
		ThrowHead(self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return


	if self.deadflag == DEAD_DEAD:

		return


	# regular death
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.s.skinnum |= 1
	if self.s.skinnum == 1:

		g_main.gi.sound(self, CHAN_VOICE, sound_death_light, 1, ATTN_NORM, 0)

	elif self.s.skinnum == 3:

		g_main.gi.sound(self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_death_ss, 1, ATTN_NORM, 0)


	if abs((self.s.origin[2] + self.viewheight) - point[2]) <= 4:

		# head shot
		self.monsterinfo.currentmove = soldier_move_death3
		return


	n = rand.randk() % 5
	if n == 0:

		self.monsterinfo.currentmove = soldier_move_death1

	elif n == 1:

		self.monsterinfo.currentmove = soldier_move_death2

	elif n == 2:

		self.monsterinfo.currentmove = soldier_move_death4

	elif n == 3:

		self.monsterinfo.currentmove = soldier_move_death5

	else:

		self.monsterinfo.currentmove = soldier_move_death6

def SP_monster_soldier_x(self): #edict_t *
	global sound_cock, sound_idle, sound_sight1, sound_sight2, sound_step, sound_step2, sound_step3, sound_step4

	if not self:

		return


	# Force recaching at next footstep to ensure
	# that the sound indices are correct.
	sound_step = 0
	sound_step2 = 0
	sound_step3 = 0
	sound_step4 = 0
	self.s.modelindex = g_main.gi.modelindex("models/monsters/soldier/tris.md2")
	self.monsterinfo.scale = soldier_h.MODEL_SCALE
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 32)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	sound_idle = g_main.gi.soundindex("soldier/solidle1.wav")
	sound_sight1 = g_main.gi.soundindex("soldier/solsght1.wav")
	sound_sight2 = g_main.gi.soundindex("soldier/solsrch1.wav")
	sound_cock = g_main.gi.soundindex("infantry/infatck3.wav")
	self.mass = 100
	self.pain = soldier_pain
	self.die = soldier_die
	self.monsterinfo.stand = soldier_stand
	self.monsterinfo.walk = soldier_walk
	self.monsterinfo.run = soldier_run
	self.monsterinfo.dodge = soldier_dodge
	self.monsterinfo.attack = soldier_attack
	self.monsterinfo.melee = None
	self.monsterinfo.sight = soldier_sight
	g_main.gi.linkentity(self)
	self.monsterinfo.stand(self)
	walkmonster_start(self)


"""QUAKED monster_soldier_light (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_soldier_light(self): #edict_t *
	global sound_death_light, sound_pain_light, sound_step, sound_step2, sound_step3, sound_step4

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	self.health = 20
	self.gib_health = -30
	SP_monster_soldier_x(self)
	sound_pain_light = g_main.gi.soundindex("soldier/solpain2.wav")
	sound_death_light = g_main.gi.soundindex("soldier/soldeth2.wav")
	sound_step = g_main.gi.soundindex("player/step1.wav")
	sound_step2 = g_main.gi.soundindex("player/step2.wav")
	sound_step3 = g_main.gi.soundindex("player/step3.wav")
	sound_step4 = g_main.gi.soundindex("player/step4.wav")
	g_main.gi.modelindex("models/objects/laser/tris.md2")
	g_main.gi.soundindex("misc/lasfly.wav")
	g_main.gi.soundindex("soldier/solatck2.wav")
	self.s.skinnum = 0


"""QUAKED monster_soldier (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_soldier(self): #edict_t *
	global sound_death, sound_pain, sound_step, sound_step2, sound_step3, sound_step4

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	self.health = 30
	self.gib_health = -30
	SP_monster_soldier_x(self)
	sound_pain = g_main.gi.soundindex("soldier/solpain1.wav")
	sound_death = g_main.gi.soundindex("soldier/soldeth1.wav")
	sound_step = g_main.gi.soundindex("player/step1.wav")
	sound_step2 = g_main.gi.soundindex("player/step2.wav")
	sound_step3 = g_main.gi.soundindex("player/step3.wav")
	sound_step4 = g_main.gi.soundindex("player/step4.wav")
	g_main.gi.soundindex("soldier/solatck1.wav")
	self.s.skinnum = 2


"""QUAKED monster_soldier_ss (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_soldier_ss(self): #edict_t *
	global sound_death_ss, sound_pain_ss, sound_step, sound_step2, sound_step3, sound_step4

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	self.health = 40
	self.gib_health = -30
	SP_monster_soldier_x(self)
	sound_pain_ss = g_main.gi.soundindex("soldier/solpain3.wav")
	sound_death_ss = g_main.gi.soundindex("soldier/soldeth3.wav")
	sound_step = g_main.gi.soundindex("player/step1.wav")
	sound_step2 = g_main.gi.soundindex("player/step2.wav")
	sound_step3 = g_main.gi.soundindex("player/step3.wav")
	sound_step4 = g_main.gi.soundindex("player/step4.wav")
	g_main.gi.soundindex("soldier/solatck3.wav")
	self.s.skinnum = 4


#=================
# move tables
#=================
soldier_frames_stand1 = [_mf(ai_stand, 0, soldier_idle), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None)]
soldier_frames_stand3 = [_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, soldier_cock), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None)]
soldier_frames_walk1 = [
	_mf(ai_walk, 3, None), _mf(ai_walk, 6, None), _mf(ai_walk, 2, None),
	_mf(ai_walk, 2, soldier_footstep), _mf(ai_walk, 2, None), _mf(ai_walk, 1, None),
	_mf(ai_walk, 6, None), _mf(ai_walk, 5, None), _mf(ai_walk, 3, soldier_footstep),
	_mf(ai_walk, -1, soldier_walk1_random), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None),
	_mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None)]
soldier_frames_walk2 = [
	_mf(ai_walk, 4, soldier_footstep), _mf(ai_walk, 4, None), _mf(ai_walk, 9, None),
	_mf(ai_walk, 8, None), _mf(ai_walk, 5, soldier_footstep), _mf(ai_walk, 1, None),
	_mf(ai_walk, 3, None), _mf(ai_walk, 7, None), _mf(ai_walk, 6, None),
	_mf(ai_walk, 7, None)]
soldier_frames_start_run = [_mf(ai_run, 7, None), _mf(ai_run, 5, None)]
soldier_frames_run = [
	_mf(ai_run, 10, None), _mf(ai_run, 11, soldier_footstep), _mf(ai_run, 11, None),
	_mf(ai_run, 16, None), _mf(ai_run, 10, soldier_footstep), _mf(ai_run, 15, None)]
soldier_frames_pain1 = [_mf(ai_move, -3, None), _mf(ai_move, 4, None), _mf(ai_move, 1, None), _mf(ai_move, 1, None), _mf(ai_move, 0, None)]
soldier_frames_pain2 = [_mf(ai_move, -13, None), _mf(ai_move, -1, None), _mf(ai_move, 2, None), _mf(ai_move, 4, None), _mf(ai_move, 2, None), _mf(ai_move, 3, None), _mf(ai_move, 2, None)]
soldier_frames_pain3 = [
	_mf(ai_move, -8, None), _mf(ai_move, 10, None), _mf(ai_move, -4, soldier_footstep),
	_mf(ai_move, -1, None), _mf(ai_move, -3, None), _mf(ai_move, 0, None),
	_mf(ai_move, 3, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None),
	_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 1, None),
	_mf(ai_move, 0, None), _mf(ai_move, 1, None), _mf(ai_move, 2, None),
	_mf(ai_move, 4, None), _mf(ai_move, 3, None), _mf(ai_move, 2, soldier_footstep)]
soldier_frames_pain4 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -10, None), _mf(ai_move, -6, None), _mf(ai_move, 8, None), _mf(ai_move, 4, None), _mf(ai_move, 1, None), _mf(ai_move, 0, None), _mf(ai_move, 2, None), _mf(ai_move, 5, None), _mf(ai_move, 2, None), _mf(ai_move, -1, None), _mf(ai_move, -1, None), _mf(ai_move, 3, None), _mf(ai_move, 2, None), _mf(ai_move, 0, None)]
soldier_frames_attack1 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack1_refire1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_cock), _mf(ai_charge, 0, soldier_attack1_refire2), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack2 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire2), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack2_refire1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_cock), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack2_refire2), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack3 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire3), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack3_refire), _mf(ai_charge, 0, soldier_duck_up), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack4 = [
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_footstep), _mf(ai_charge, 0, soldier_fire4),
	_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_footstep)]
soldier_frames_attack6 = [
	_mf(ai_charge, 10, None), _mf(ai_charge, 4, None), _mf(ai_charge, 12, soldier_footstep),
	_mf(ai_charge, 11, soldier_fire8), _mf(ai_charge, 13, None), _mf(ai_charge, 18, None),
	_mf(ai_charge, 15, soldier_footstep), _mf(ai_charge, 14, None), _mf(ai_charge, 11, None),
	_mf(ai_charge, 8, soldier_footstep), _mf(ai_charge, 11, None), _mf(ai_charge, 12, None),
	_mf(ai_charge, 12, soldier_footstep), _mf(ai_charge, 17, soldier_attack6_refire)]
soldier_frames_duck = [_mf(ai_move, 5, soldier_duck_down), _mf(ai_move, -1, soldier_duck_hold), _mf(ai_move, 1, None), _mf(ai_move, 0, soldier_duck_up), _mf(ai_move, 5, None)]
soldier_frames_death1 = [_mf(ai_move, 0, None), _mf(ai_move, -10, None), _mf(ai_move, -10, None), _mf(ai_move, -10, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, soldier_fire6), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, soldier_fire7), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death2 = [_mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death3 = [_mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death4 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death5 = [_mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death6 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_move_stand1 = _mm(soldier_h.FRAME_stand101, soldier_h.FRAME_stand130, soldier_frames_stand1, soldier_stand)
soldier_move_stand3 = _mm(soldier_h.FRAME_stand301, soldier_h.FRAME_stand339, soldier_frames_stand3, soldier_stand)
soldier_move_walk1 = _mm(soldier_h.FRAME_walk101, soldier_h.FRAME_walk133, soldier_frames_walk1, None)
soldier_move_walk2 = _mm(soldier_h.FRAME_walk209, soldier_h.FRAME_walk218, soldier_frames_walk2, None)
soldier_move_start_run = _mm(soldier_h.FRAME_run01, soldier_h.FRAME_run02, soldier_frames_start_run, soldier_run)
soldier_move_run = _mm(soldier_h.FRAME_run03, soldier_h.FRAME_run08, soldier_frames_run, None)
soldier_move_pain1 = _mm(soldier_h.FRAME_pain101, soldier_h.FRAME_pain105, soldier_frames_pain1, soldier_run)
soldier_move_pain2 = _mm(soldier_h.FRAME_pain201, soldier_h.FRAME_pain207, soldier_frames_pain2, soldier_run)
soldier_move_pain3 = _mm(soldier_h.FRAME_pain301, soldier_h.FRAME_pain318, soldier_frames_pain3, soldier_run)
soldier_move_pain4 = _mm(soldier_h.FRAME_pain401, soldier_h.FRAME_pain417, soldier_frames_pain4, soldier_run)
soldier_move_attack1 = _mm(soldier_h.FRAME_attak101, soldier_h.FRAME_attak112, soldier_frames_attack1, soldier_run)
soldier_move_attack2 = _mm(soldier_h.FRAME_attak201, soldier_h.FRAME_attak218, soldier_frames_attack2, soldier_run)
soldier_move_attack3 = _mm(soldier_h.FRAME_attak301, soldier_h.FRAME_attak309, soldier_frames_attack3, soldier_run)
soldier_move_attack4 = _mm(soldier_h.FRAME_attak401, soldier_h.FRAME_attak406, soldier_frames_attack4, soldier_run)
soldier_move_attack6 = _mm(soldier_h.FRAME_runs01, soldier_h.FRAME_runs14, soldier_frames_attack6, soldier_run)
soldier_move_duck = _mm(soldier_h.FRAME_duck01, soldier_h.FRAME_duck05, soldier_frames_duck, soldier_run)
soldier_move_death1 = _mm(soldier_h.FRAME_death101, soldier_h.FRAME_death136, soldier_frames_death1, soldier_dead)
soldier_move_death2 = _mm(soldier_h.FRAME_death201, soldier_h.FRAME_death235, soldier_frames_death2, soldier_dead)
soldier_move_death3 = _mm(soldier_h.FRAME_death301, soldier_h.FRAME_death345, soldier_frames_death3, soldier_dead)
soldier_move_death4 = _mm(soldier_h.FRAME_death401, soldier_h.FRAME_death453, soldier_frames_death4, soldier_dead)
soldier_move_death5 = _mm(soldier_h.FRAME_death501, soldier_h.FRAME_death524, soldier_frames_death5, soldier_dead)
soldier_move_death6 = _mm(soldier_h.FRAME_death601, soldier_h.FRAME_death610, soldier_frames_death6, soldier_dead)
