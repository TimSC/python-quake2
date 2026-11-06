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

Parasite.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from game import g_main
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_combat import (T_Damage)
from game.header.local import AI_STAND_GROUND, DAMAGE_NO_KNOCKBACK, DEAD_DEAD, GIB_ORGANIC, MOD_UNKNOWN, MOVETYPE_STEP, MOVETYPE_TOSS, damage_t, svc_temp_entity
from game.g_misc import (ThrowGib, ThrowHead)
from game.g_monster import (walkmonster_start)
from game.g_utils import G_FreeEdict, G_ProjectSource, vectoangles
from game.header.game import SOLID_BBOX, SVF_DEADMONSTER
from common.header.shared import ATTN_IDLE, ATTN_NORM, CHAN_AUTO, CHAN_VOICE, CHAN_WEAPON, MASK_SHOT, multicast_t, temp_event_t
from common.shared.shared import vec3_origin
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from game.monster.parasite import parasite_h

"""
#include "../../header/local.h"
#include "parasite.h"
"""

DAMAGE_YES = damage_t.DAMAGE_YES.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
TE_PARASITE_ATTACK = temp_event_t.TE_PARASITE_ATTACK.value

# m_parasite.h


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

sound_pain1 = 0 # static
sound_pain2 = 0 # static
sound_die = 0 # static
sound_launch = 0 # static
sound_impact = 0 # static
sound_suck = 0 # static
sound_reelin = 0 # static
sound_sight = 0 # static
sound_tap = 0 # static
sound_scratch = 0 # static
sound_search = 0 # static


"""
==============================================================================

parasite

==============================================================================
"""
def parasite_launch (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_launch, 1, ATTN_NORM, 0)


def parasite_reel_in (self): #edict_t *

	if not self:

		return


	g_main.gi.sound (self, CHAN_WEAPON, sound_reelin, 1, ATTN_NORM, 0)


def parasite_sight(self, other): #edict_t *, edict_t *

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_sight, 1, ATTN_NORM, 0)


def parasite_tap(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, shared.CHAN_BODY, sound_tap, 1, ATTN_IDLE, 0)


def parasite_footstep(self): #edict_t *

	if g_main.g_monsterfootsteps.value:

		parasite_tap(self)

def parasite_scratch(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, shared.CHAN_BODY, sound_scratch, 1, ATTN_IDLE, 0)


def parasite_search(self): #edict_t *

	if not self:

		return


	g_main.gi.sound(self, CHAN_VOICE, sound_search, 1, ATTN_NORM, 0)


def parasite_end_fidget (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_end_fidget


def parasite_do_fidget (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_fidget


def parasite_refidget (self): #edict_t *

	if not self:

		return


	if local.random() <= 0.8:
		self.monsterinfo.currentmove = parasite_move_fidget
	else:
		self.monsterinfo.currentmove = parasite_move_end_fidget


def parasite_idle (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_start_fidget


def parasite_stand (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_stand


def parasite_start_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = parasite_move_stand
	else:
		self.monsterinfo.currentmove = parasite_move_start_run


def parasite_run (self): #edict_t *

	if not self:

		return


	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = parasite_move_stand
	else:
		self.monsterinfo.currentmove = parasite_move_run


def parasite_start_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_start_walk


def parasite_walk (self): #edict_t *

	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_walk


def parasite_pain(self, other, kick, damage): #edict_t *, edict_t *, float, int

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


	if local.random() < 0.5:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain1, 1, ATTN_NORM, 0)

	else:

		g_main.gi.sound(self, CHAN_VOICE, sound_pain2, 1, ATTN_NORM, 0)


	self.monsterinfo.currentmove = parasite_move_pain1


def parasite_drain_attack_ok (start, end): #vec3_t, vec3_t

	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	angles = np.zeros((3,), dtype=np.float32) #vec3_t

	# check for max distance
	shared.VectorSubtract (start, end, dir)
	if shared_c.VectorLength(dir) > 256:
		return False

	# check for min/max pitch
	vectoangles (dir, angles)
	if angles[0] < -180:
		angles[0] += 360
	if abs(angles[0]) > 30:
		return False

	return True


def parasite_drain_attack (self): #edict_t *

	if not self:

		return


	offset = np.zeros((3,), dtype=np.float32) #vec3_t
	start = np.zeros((3,), dtype=np.float32) #vec3_t
	f = np.zeros((3,), dtype=np.float32) #vec3_t
	r = np.zeros((3,), dtype=np.float32) #vec3_t
	end = np.zeros((3,), dtype=np.float32) #vec3_t
	dir = np.zeros((3,), dtype=np.float32) #vec3_t
	#trace_t	tr;
	#int	damage;

	shared_c.AngleVectors (self.s.angles, f, r, None)
	shared.VectorSet (offset, 24, 0, 6)
	G_ProjectSource (self.s.origin, offset, f, r, start)

	shared.VectorCopy (self.enemy.s.origin, end)
	if not parasite_drain_attack_ok(start, end):
		end[2] = self.enemy.s.origin[2] + self.enemy.maxs[2] - 8
		if not parasite_drain_attack_ok(start, end):
			end[2] = self.enemy.s.origin[2] + self.enemy.mins[2] + 8
			if not parasite_drain_attack_ok(start, end):
				return
	shared.VectorCopy (self.enemy.s.origin, end)

	tr = g_main.gi.trace (start, None, None, end, self, MASK_SHOT)
	if tr.ent != self.enemy:
		return

	if self.s.frame == parasite_h.FRAME_drain03:
		damage = 5
		g_main.gi.sound (self.enemy, CHAN_AUTO, sound_impact, 1, ATTN_NORM, 0)
	else:
		if self.s.frame == parasite_h.FRAME_drain04:
			g_main.gi.sound (self, CHAN_WEAPON, sound_suck, 1, ATTN_NORM, 0)
		damage = 2

	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_PARASITE_ATTACK)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WritePosition (start)
	g_main.gi.WritePosition (end)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)

	shared.VectorSubtract (start, end, dir)
	T_Damage (self.enemy, self, self, dir, self.enemy.s.origin, vec3_origin, damage, 0, DAMAGE_NO_KNOCKBACK, MOD_UNKNOWN)


def parasite_attack (self): #edict_t *

	# if (random() <= 0.2)
	# self->monsterinfo.currentmove = &parasite_move_break;
	# else
	if not self:

		return


	self.monsterinfo.currentmove = parasite_move_drain


def parasite_dead (self): #edict_t *

	if not self:

		return


	shared.VectorSet (self.mins, -16, -16, -24)
	shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)


def parasite_die (self, inflictor, attacker, damage, point): #edict_t *, edict_t *, edict_t *, int, vec3_t

	#int	n;

	# check for gib
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

	# regular death
	g_main.gi.sound (self, CHAN_VOICE, sound_die, 1, ATTN_NORM, 0)
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.monsterinfo.currentmove = parasite_move_death


"""QUAKED monster_parasite (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_parasite(self): #edict_t *
	global sound_die, sound_impact, sound_launch, sound_pain1, sound_pain2, sound_reelin, sound_scratch, sound_search, sound_sight, sound_suck, sound_tap

	if not self:

		return


	if g_main.deathmatch.value:

		G_FreeEdict(self)
		return


	sound_pain1 = g_main.gi.soundindex("parasite/parpain1.wav")
	sound_pain2 = g_main.gi.soundindex("parasite/parpain2.wav")
	sound_die = g_main.gi.soundindex("parasite/pardeth1.wav")
	sound_launch = g_main.gi.soundindex("parasite/paratck1.wav")
	sound_impact = g_main.gi.soundindex("parasite/paratck2.wav")
	sound_suck = g_main.gi.soundindex("parasite/paratck3.wav")
	sound_reelin = g_main.gi.soundindex("parasite/paratck4.wav")
	sound_sight = g_main.gi.soundindex("parasite/parsght1.wav")
	sound_tap = g_main.gi.soundindex("parasite/paridle1.wav")
	sound_scratch = g_main.gi.soundindex("parasite/paridle2.wav")
	sound_search = g_main.gi.soundindex("parasite/parsrch1.wav")
	self.s.modelindex = g_main.gi.modelindex("models/monsters/parasite/tris.md2")
	shared.VectorSet(self.mins, -16, -16, -24)
	shared.VectorSet(self.maxs, 16, 16, 24)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX
	self.health = 175
	self.gib_health = -50
	self.mass = 250
	self.viewheight = 16
	self.pain = parasite_pain
	self.die = parasite_die
	self.monsterinfo.stand = parasite_stand
	self.monsterinfo.walk = parasite_start_walk
	self.monsterinfo.run = parasite_start_run
	self.monsterinfo.attack = parasite_attack
	self.monsterinfo.sight = parasite_sight
	self.monsterinfo.idle = parasite_idle
	self.monsterinfo.search = parasite_search
	g_main.gi.linkentity(self)
	self.monsterinfo.currentmove = parasite_move_stand
	self.monsterinfo.scale = parasite_h.MODEL_SCALE
	walkmonster_start(self)


# ----------------------------------------------------------------------------
# Animation move tables (Q2PORT: defined after the functions they reference)
# ----------------------------------------------------------------------------
parasite_frames_start_fidget = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
parasite_move_start_fidget = _mm(parasite_h.FRAME_stand18, parasite_h.FRAME_stand21, parasite_frames_start_fidget, parasite_do_fidget)

parasite_frames_fidget = [
	_mf(ai_stand, 0, parasite_scratch),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_scratch),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
parasite_move_fidget = _mm(parasite_h.FRAME_stand22, parasite_h.FRAME_stand27, parasite_frames_fidget, parasite_refidget)

parasite_frames_end_fidget = [
	_mf(ai_stand, 0, parasite_scratch),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
]
parasite_move_end_fidget = _mm(parasite_h.FRAME_stand28, parasite_h.FRAME_stand35, parasite_frames_end_fidget, parasite_stand)

parasite_frames_stand = [
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
	_mf(ai_stand, 0, None),
	_mf(ai_stand, 0, parasite_tap),
]
parasite_move_stand = _mm(parasite_h.FRAME_stand01, parasite_h.FRAME_stand17, parasite_frames_stand, parasite_stand)

parasite_frames_run = [
	_mf(ai_run, 30, None), _mf(ai_run, 30, None), _mf(ai_run, 22, parasite_footstep),
	_mf(ai_run, 19, parasite_footstep), _mf(ai_run, 24, None), _mf(ai_run, 28, parasite_footstep),
	_mf(ai_run, 25, None)]
parasite_move_run = _mm(parasite_h.FRAME_run03, parasite_h.FRAME_run09, parasite_frames_run, None)

parasite_frames_start_run = [
	_mf(ai_run, 0, None),
	_mf(ai_run, 30, None),
]
parasite_move_start_run = _mm(parasite_h.FRAME_run01, parasite_h.FRAME_run02, parasite_frames_start_run, parasite_run)

parasite_frames_stop_run = [
	_mf(ai_run, 20, None), _mf(ai_run, 20, None), _mf(ai_run, 12, parasite_footstep),
	_mf(ai_run, 10, None), _mf(ai_run, 0, None), _mf(ai_run, 0, None)]
parasite_move_stop_run = _mm(parasite_h.FRAME_run10, parasite_h.FRAME_run15, parasite_frames_stop_run, None)

parasite_frames_walk = [
	_mf(ai_walk, 30, None), _mf(ai_walk, 30, None), _mf(ai_walk, 22, parasite_footstep),
	_mf(ai_walk, 19, None), _mf(ai_walk, 24, parasite_footstep), _mf(ai_walk, 28, parasite_footstep),
	_mf(ai_walk, 25, None)]
parasite_move_walk = _mm(parasite_h.FRAME_run03, parasite_h.FRAME_run09, parasite_frames_walk, parasite_walk)

parasite_frames_start_walk = [
	_mf(ai_walk, 0, None),
	_mf(ai_walk, 30, parasite_walk),
]
parasite_move_start_walk = _mm(parasite_h.FRAME_run01, parasite_h.FRAME_run02, parasite_frames_start_walk, None)

parasite_frames_stop_walk = [
	_mf(ai_walk, 20, None), _mf(ai_walk, 20, None), _mf(ai_walk, 12, parasite_footstep),
	_mf(ai_walk, 10, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None)]
parasite_move_stop_walk = _mm(parasite_h.FRAME_run10, parasite_h.FRAME_run15, parasite_frames_stop_walk, None)

parasite_frames_pain1 = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 6, None),
	_mf(ai_move, 16, None),
	_mf(ai_move, -6, None),
	_mf(ai_move, -7, None),
	_mf(ai_move, 0, None),
]
parasite_move_pain1 = _mm(parasite_h.FRAME_pain101, parasite_h.FRAME_pain111, parasite_frames_pain1, parasite_start_run)

parasite_frames_drain = [
	_mf(ai_charge, 0, parasite_launch),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 15, parasite_drain_attack),	# Target hits
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, -2, parasite_drain_attack),	# drain
	_mf(ai_charge, -2, parasite_drain_attack),	# drain
	_mf(ai_charge, -3, parasite_drain_attack),	# drain
	_mf(ai_charge, -2, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_drain_attack),	# drain
	_mf(ai_charge, -1, parasite_drain_attack),	# drain
	_mf(ai_charge, 0, parasite_reel_in),	# let go
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 0, None),
]
parasite_move_drain = _mm(parasite_h.FRAME_drain01, parasite_h.FRAME_drain18, parasite_frames_drain, parasite_start_run)

parasite_frames_break = [
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 2, None),
	_mf(ai_charge, -3, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 1, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -18, None),
	_mf(ai_charge, 3, None),
	_mf(ai_charge, 9, None),
	_mf(ai_charge, 6, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -18, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 8, None),
	_mf(ai_charge, 9, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, -18, None),
	_mf(ai_charge, 0, None),
	_mf(ai_charge, 0, None),	# airborne
	_mf(ai_charge, 0, None),	# airborne
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 0, None),	# slides
	_mf(ai_charge, 4, None),
	_mf(ai_charge, 11, None),
	_mf(ai_charge, -2, None),
	_mf(ai_charge, -5, None),
	_mf(ai_charge, 1, None),
]
parasite_move_break = _mm(parasite_h.FRAME_break01, parasite_h.FRAME_break32, parasite_frames_break, parasite_start_run)

parasite_frames_death = [
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
	_mf(ai_move, 0, None),
]
parasite_move_death = _mm(parasite_h.FRAME_death101, parasite_h.FRAME_death107, parasite_frames_death, parasite_dead)
