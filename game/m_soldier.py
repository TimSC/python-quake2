#
# Copyright (C) 1997-2001 Id Software, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
from __future__ import annotations

import random as _r
import numpy as np
from game import q_shared, g_local, g_main, g_utils, g_monster, g_misc, g_ai, m_flash
from game.g_ai import ai_stand, ai_walk, ai_run, ai_move, ai_charge
from game.g_utils import G_ProjectSource, G_FreeEdict, vectoangles
from game.g_monster import monster_fire_bullet, monster_fire_blaster, monster_fire_shotgun, walkmonster_start
from game.g_misc import ThrowGib, ThrowHead
from game.q_shared import (CHAN_VOICE, CHAN_WEAPON, ATTN_NORM, ATTN_IDLE, EF_BLASTER,
	MZ2_SOLDIER_BLASTER_1, MZ2_SOLDIER_BLASTER_2, MZ2_SOLDIER_BLASTER_3, MZ2_SOLDIER_BLASTER_4,
	MZ2_SOLDIER_BLASTER_5, MZ2_SOLDIER_BLASTER_6, MZ2_SOLDIER_BLASTER_7, MZ2_SOLDIER_BLASTER_8,
	MZ2_SOLDIER_SHOTGUN_1, MZ2_SOLDIER_SHOTGUN_2, MZ2_SOLDIER_SHOTGUN_3, MZ2_SOLDIER_SHOTGUN_4,
	MZ2_SOLDIER_SHOTGUN_5, MZ2_SOLDIER_SHOTGUN_6, MZ2_SOLDIER_SHOTGUN_7, MZ2_SOLDIER_SHOTGUN_8,
	MZ2_SOLDIER_MACHINEGUN_1, MZ2_SOLDIER_MACHINEGUN_2, MZ2_SOLDIER_MACHINEGUN_3, MZ2_SOLDIER_MACHINEGUN_4,
	MZ2_SOLDIER_MACHINEGUN_5, MZ2_SOLDIER_MACHINEGUN_6, MZ2_SOLDIER_MACHINEGUN_7, MZ2_SOLDIER_MACHINEGUN_8)
from game.g_local import (FRAMETIME, GIB_ORGANIC, DEAD_DEAD, MOVETYPE_TOSS,
	MOVETYPE_STEP, AI_STAND_GROUND, AI_HOLD_FRAME, AI_DUCKED, RANGE_MELEE, RANGE_MID,
	DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, crandom, damage_t)
DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.game import solid_t, SVF_DEADMONSTER

SOLID_BBOX = solid_t.SOLID_BBOX.value

# from g_local.h (not yet in g_local.py)
DEFAULT_SHOTGUN_HSPREAD = 1000
DEFAULT_SHOTGUN_VSPREAD = 500
DEFAULT_SHOTGUN_COUNT = 12

MODEL_SCALE = 1.000000

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

blaster_flash = [MZ2_SOLDIER_BLASTER_1, MZ2_SOLDIER_BLASTER_2, MZ2_SOLDIER_BLASTER_3, MZ2_SOLDIER_BLASTER_4, MZ2_SOLDIER_BLASTER_5, MZ2_SOLDIER_BLASTER_6, MZ2_SOLDIER_BLASTER_7, MZ2_SOLDIER_BLASTER_8]
shotgun_flash = [MZ2_SOLDIER_SHOTGUN_1, MZ2_SOLDIER_SHOTGUN_2, MZ2_SOLDIER_SHOTGUN_3, MZ2_SOLDIER_SHOTGUN_4, MZ2_SOLDIER_SHOTGUN_5, MZ2_SOLDIER_SHOTGUN_6, MZ2_SOLDIER_SHOTGUN_7, MZ2_SOLDIER_SHOTGUN_8]
machinegun_flash = [MZ2_SOLDIER_MACHINEGUN_1, MZ2_SOLDIER_MACHINEGUN_2, MZ2_SOLDIER_MACHINEGUN_3, MZ2_SOLDIER_MACHINEGUN_4, MZ2_SOLDIER_MACHINEGUN_5, MZ2_SOLDIER_MACHINEGUN_6, MZ2_SOLDIER_MACHINEGUN_7, MZ2_SOLDIER_MACHINEGUN_8]

FRAME_attak101 = 0
FRAME_attak102 = 1
FRAME_attak110 = 9
FRAME_attak112 = 11
FRAME_attak201 = 12
FRAME_attak204 = 15
FRAME_attak216 = 27
FRAME_attak218 = 29
FRAME_attak301 = 30
FRAME_attak303 = 32
FRAME_attak309 = 38
FRAME_attak401 = 39
FRAME_attak406 = 44
FRAME_duck01 = 45
FRAME_duck05 = 49
FRAME_pain101 = 50
FRAME_pain105 = 54
FRAME_pain201 = 55
FRAME_pain207 = 61
FRAME_pain301 = 62
FRAME_pain318 = 79
FRAME_pain401 = 80
FRAME_pain417 = 96
FRAME_run01 = 97
FRAME_run02 = 98
FRAME_run03 = 99
FRAME_run08 = 104
FRAME_runs01 = 109
FRAME_runs03 = 111
FRAME_runs14 = 122
FRAME_stand101 = 146
FRAME_stand130 = 175
FRAME_stand301 = 176
FRAME_stand339 = 214
FRAME_walk101 = 215
FRAME_walk133 = 247
FRAME_walk209 = 256
FRAME_walk218 = 265
FRAME_death101 = 272
FRAME_death136 = 307
FRAME_death201 = 308
FRAME_death235 = 342
FRAME_death301 = 343
FRAME_death345 = 387
FRAME_death401 = 388
FRAME_death453 = 440
FRAME_death501 = 441
FRAME_death524 = 464
FRAME_death601 = 465
FRAME_death610 = 474
FRAME_stand322 = 197
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

SOLDIER

==============================================================================
*/

#include "g_local.h"
#include "m_soldier.h"


static int	sound_idle;
static int	sound_sight1;
static int	sound_sight2;
static int	sound_pain_light;
static int	sound_pain;
static int	sound_pain_ss;
static int	sound_death_light;
static int	sound_death;
static int	sound_death_ss;
static int	sound_cock;


void soldier_idle (edict_t *self)
{
	if (random() > 0.8)
		gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0);
}

void soldier_cock (edict_t *self)
{
	if (self->s.frame == FRAME_stand322)
		gi.sound (self, CHAN_WEAPON, sound_cock, 1, ATTN_IDLE, 0);
	else
		gi.sound (self, CHAN_WEAPON, sound_cock, 1, ATTN_NORM, 0);
}


// STAND

void soldier_stand (edict_t *self);

mframe_t soldier_frames_stand1 [] =
{
	ai_stand, 0, soldier_idle,
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
mmove_t soldier_move_stand1 = {FRAME_stand101, FRAME_stand130, soldier_frames_stand1, soldier_stand};

mframe_t soldier_frames_stand3 [] =
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
	ai_stand, 0, NULL,

	ai_stand, 0, NULL,
	ai_stand, 0, soldier_cock,
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
mmove_t soldier_move_stand3 = {FRAME_stand301, FRAME_stand339, soldier_frames_stand3, soldier_stand};

#if 0
mframe_t soldier_frames_stand4 [] =
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
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,

	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 0, NULL,
	ai_stand, 4, NULL,
	ai_stand, 1, NULL,
	ai_stand, -1, NULL,
	ai_stand, -2, NULL,

	ai_stand, 0, NULL,
	ai_stand, 0, NULL
};
mmove_t soldier_move_stand4 = {FRAME_stand401, FRAME_stand452, soldier_frames_stand4, NULL};
#endif

void soldier_stand (edict_t *self)
{
	if ((self->monsterinfo.currentmove == &soldier_move_stand3) || (random() < 0.8))
		self->monsterinfo.currentmove = &soldier_move_stand1;
	else
		self->monsterinfo.currentmove = &soldier_move_stand3;
}


//
// WALK
//

void soldier_walk1_random (edict_t *self)
{
	if (random() > 0.1)
		self->monsterinfo.nextframe = FRAME_walk101;
}

mframe_t soldier_frames_walk1 [] =
{
	ai_walk, 3,  NULL,
	ai_walk, 6,  NULL,
	ai_walk, 2,  NULL,
	ai_walk, 2,  NULL,
	ai_walk, 2,  NULL,
	ai_walk, 1,  NULL,
	ai_walk, 6,  NULL,
	ai_walk, 5,  NULL,
	ai_walk, 3,  NULL,
	ai_walk, -1, soldier_walk1_random,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL,
	ai_walk, 0,  NULL
};
mmove_t soldier_move_walk1 = {FRAME_walk101, FRAME_walk133, soldier_frames_walk1, NULL};

mframe_t soldier_frames_walk2 [] =
{
	ai_walk, 4,  NULL,
	ai_walk, 4,  NULL,
	ai_walk, 9,  NULL,
	ai_walk, 8,  NULL,
	ai_walk, 5,  NULL,
	ai_walk, 1,  NULL,
	ai_walk, 3,  NULL,
	ai_walk, 7,  NULL,
	ai_walk, 6,  NULL,
	ai_walk, 7,  NULL
};
mmove_t soldier_move_walk2 = {FRAME_walk209, FRAME_walk218, soldier_frames_walk2, NULL};

void soldier_walk (edict_t *self)
{
	if (random() < 0.5)
		self->monsterinfo.currentmove = &soldier_move_walk1;
	else
		self->monsterinfo.currentmove = &soldier_move_walk2;
}


//
// RUN
//

void soldier_run (edict_t *self);

mframe_t soldier_frames_start_run [] =
{
	ai_run, 7,  NULL,
	ai_run, 5,  NULL
};
mmove_t soldier_move_start_run = {FRAME_run01, FRAME_run02, soldier_frames_start_run, soldier_run};

mframe_t soldier_frames_run [] =
{
	ai_run, 10, NULL,
	ai_run, 11, NULL,
	ai_run, 11, NULL,
	ai_run, 16, NULL,
	ai_run, 10, NULL,
	ai_run, 15, NULL
};
mmove_t soldier_move_run = {FRAME_run03, FRAME_run08, soldier_frames_run, NULL};

void soldier_run (edict_t *self)
{
	if (self->monsterinfo.aiflags & AI_STAND_GROUND)
	{
		self->monsterinfo.currentmove = &soldier_move_stand1;
		return;
	}

	if (self->monsterinfo.currentmove == &soldier_move_walk1 ||
		self->monsterinfo.currentmove == &soldier_move_walk2 ||
		self->monsterinfo.currentmove == &soldier_move_start_run)
	{
		self->monsterinfo.currentmove = &soldier_move_run;
	}
	else
	{
		self->monsterinfo.currentmove = &soldier_move_start_run;
	}
}


//
// PAIN
//

mframe_t soldier_frames_pain1 [] =
{
	ai_move, -3, NULL,
	ai_move, 4,  NULL,
	ai_move, 1,  NULL,
	ai_move, 1,  NULL,
	ai_move, 0,  NULL
};
mmove_t soldier_move_pain1 = {FRAME_pain101, FRAME_pain105, soldier_frames_pain1, soldier_run};

mframe_t soldier_frames_pain2 [] =
{
	ai_move, -13, NULL,
	ai_move, -1,  NULL,
	ai_move, 2,   NULL,
	ai_move, 4,   NULL,
	ai_move, 2,   NULL,
	ai_move, 3,   NULL,
	ai_move, 2,   NULL
};
mmove_t soldier_move_pain2 = {FRAME_pain201, FRAME_pain207, soldier_frames_pain2, soldier_run};

mframe_t soldier_frames_pain3 [] =
{
	ai_move, -8, NULL,
	ai_move, 10, NULL,
	ai_move, -4, NULL,
	ai_move, -1, NULL,
	ai_move, -3, NULL,
	ai_move, 0,  NULL,
	ai_move, 3,  NULL,
	ai_move, 0,  NULL,
	ai_move, 0,  NULL,
	ai_move, 0,  NULL,
	ai_move, 0,  NULL,
	ai_move, 1,  NULL,
	ai_move, 0,  NULL,
	ai_move, 1,  NULL,
	ai_move, 2,  NULL,
	ai_move, 4,  NULL,
	ai_move, 3,  NULL,
	ai_move, 2,  NULL
};
mmove_t soldier_move_pain3 = {FRAME_pain301, FRAME_pain318, soldier_frames_pain3, soldier_run};

mframe_t soldier_frames_pain4 [] =
{
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, -10, NULL,
	ai_move, -6,  NULL,
	ai_move, 8,   NULL,
	ai_move, 4,   NULL,
	ai_move, 1,   NULL,
	ai_move, 0,   NULL,
	ai_move, 2,   NULL,
	ai_move, 5,   NULL,
	ai_move, 2,   NULL,
	ai_move, -1,  NULL,
	ai_move, -1,  NULL,
	ai_move, 3,   NULL,
	ai_move, 2,   NULL,
	ai_move, 0,   NULL
};
mmove_t soldier_move_pain4 = {FRAME_pain401, FRAME_pain417, soldier_frames_pain4, soldier_run};


void soldier_pain (edict_t *self, edict_t *other, float kick, int damage)
{
	float	r;
	int		n;

	if (self->health < (self->max_health / 2))
			self->s.skinnum |= 1;

	if (level.time < self->pain_debounce_time)
	{
		if ((self->velocity[2] > 100) && ( (self->monsterinfo.currentmove == &soldier_move_pain1) || (self->monsterinfo.currentmove == &soldier_move_pain2) || (self->monsterinfo.currentmove == &soldier_move_pain3)))
			self->monsterinfo.currentmove = &soldier_move_pain4;
		return;
	}

	self->pain_debounce_time = level.time + 3;

	n = self->s.skinnum | 1;
	if (n == 1)
		gi.sound (self, CHAN_VOICE, sound_pain_light, 1, ATTN_NORM, 0);
	else if (n == 3)
		gi.sound (self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0);
	else
		gi.sound (self, CHAN_VOICE, sound_pain_ss, 1, ATTN_NORM, 0);

	if (self->velocity[2] > 100)
	{
		self->monsterinfo.currentmove = &soldier_move_pain4;
		return;
	}

	if (skill->value == 3)
		return;		// no pain anims in nightmare

	r = random();

	if (r < 0.33)
		self->monsterinfo.currentmove = &soldier_move_pain1;
	else if (r < 0.66)
		self->monsterinfo.currentmove = &soldier_move_pain2;
	else
		self->monsterinfo.currentmove = &soldier_move_pain3;
}


//
// ATTACK
//

static int blaster_flash [] = {MZ2_SOLDIER_BLASTER_1, MZ2_SOLDIER_BLASTER_2, MZ2_SOLDIER_BLASTER_3, MZ2_SOLDIER_BLASTER_4, MZ2_SOLDIER_BLASTER_5, MZ2_SOLDIER_BLASTER_6, MZ2_SOLDIER_BLASTER_7, MZ2_SOLDIER_BLASTER_8};
static int shotgun_flash [] = {MZ2_SOLDIER_SHOTGUN_1, MZ2_SOLDIER_SHOTGUN_2, MZ2_SOLDIER_SHOTGUN_3, MZ2_SOLDIER_SHOTGUN_4, MZ2_SOLDIER_SHOTGUN_5, MZ2_SOLDIER_SHOTGUN_6, MZ2_SOLDIER_SHOTGUN_7, MZ2_SOLDIER_SHOTGUN_8};
static int machinegun_flash [] = {MZ2_SOLDIER_MACHINEGUN_1, MZ2_SOLDIER_MACHINEGUN_2, MZ2_SOLDIER_MACHINEGUN_3, MZ2_SOLDIER_MACHINEGUN_4, MZ2_SOLDIER_MACHINEGUN_5, MZ2_SOLDIER_MACHINEGUN_6, MZ2_SOLDIER_MACHINEGUN_7, MZ2_SOLDIER_MACHINEGUN_8};

void soldier_fire (edict_t *self, int flash_number)
{
	vec3_t	start;
	vec3_t	forward, right, up;
	vec3_t	aim;
	vec3_t	dir;
	vec3_t	end;
	float	r, u;
	int		flash_index;

	if (self->s.skinnum < 2)
		flash_index = blaster_flash[flash_number];
	else if (self->s.skinnum < 4)
		flash_index = shotgun_flash[flash_number];
	else
		flash_index = machinegun_flash[flash_number];

	AngleVectors (self->s.angles, forward, right, NULL);
	G_ProjectSource (self->s.origin, monster_flash_offset[flash_index], forward, right, start);

	if (flash_number == 5 || flash_number == 6)
	{
		VectorCopy (forward, aim);
	}
	else
	{
		VectorCopy (self->enemy->s.origin, end);
		end[2] += self->enemy->viewheight;
		VectorSubtract (end, start, aim);
		vectoangles (aim, dir);
		AngleVectors (dir, forward, right, up);

		r = crandom()*1000;
		u = crandom()*500;
		VectorMA (start, 8192, forward, end);
		VectorMA (end, r, right, end);
		VectorMA (end, u, up, end);

		VectorSubtract (end, start, aim);
		VectorNormalize (aim);
	}

	if (self->s.skinnum <= 1)
	{
		monster_fire_blaster (self, start, aim, 5, 600, flash_index, EF_BLASTER);
	}
	else if (self->s.skinnum <= 3)
	{
		monster_fire_shotgun (self, start, aim, 2, 1, DEFAULT_SHOTGUN_HSPREAD, DEFAULT_SHOTGUN_VSPREAD, DEFAULT_SHOTGUN_COUNT, flash_index);
	}
	else
	{
		if (!(self->monsterinfo.aiflags & AI_HOLD_FRAME))
			self->monsterinfo.pausetime = level.time + (3 + rand() % 8) * FRAMETIME;

		monster_fire_bullet (self, start, aim, 2, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_index);

		if (level.time >= self->monsterinfo.pausetime)
			self->monsterinfo.aiflags &= ~AI_HOLD_FRAME;
		else
			self->monsterinfo.aiflags |= AI_HOLD_FRAME;
	}
}

// ATTACK1 (blaster/shotgun)

void soldier_fire1 (edict_t *self)
{
	soldier_fire (self, 0);
}

void soldier_attack1_refire1 (edict_t *self)
{
	if (self->s.skinnum > 1)
		return;

	if (self->enemy->health <= 0)
		return;

	if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
		self->monsterinfo.nextframe = FRAME_attak102;
	else
		self->monsterinfo.nextframe = FRAME_attak110;
}

void soldier_attack1_refire2 (edict_t *self)
{
	if (self->s.skinnum < 2)
		return;

	if (self->enemy->health <= 0)
		return;

	if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
		self->monsterinfo.nextframe = FRAME_attak102;
}

mframe_t soldier_frames_attack1 [] =
{
	ai_charge, 0,  NULL,
	ai_charge, 0,  NULL,
	ai_charge, 0,  soldier_fire1,
	ai_charge, 0,  NULL,
	ai_charge, 0,  NULL,
	ai_charge, 0,  soldier_attack1_refire1,
	ai_charge, 0,  NULL,
	ai_charge, 0,  soldier_cock,
	ai_charge, 0,  soldier_attack1_refire2,
	ai_charge, 0,  NULL,
	ai_charge, 0,  NULL,
	ai_charge, 0,  NULL
};
mmove_t soldier_move_attack1 = {FRAME_attak101, FRAME_attak112, soldier_frames_attack1, soldier_run};

// ATTACK2 (blaster/shotgun)

void soldier_fire2 (edict_t *self)
{
	soldier_fire (self, 1);
}

void soldier_attack2_refire1 (edict_t *self)
{
	if (self->s.skinnum > 1)
		return;

	if (self->enemy->health <= 0)
		return;

	if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
		self->monsterinfo.nextframe = FRAME_attak204;
	else
		self->monsterinfo.nextframe = FRAME_attak216;
}

void soldier_attack2_refire2 (edict_t *self)
{
	if (self->s.skinnum < 2)
		return;

	if (self->enemy->health <= 0)
		return;

	if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
		self->monsterinfo.nextframe = FRAME_attak204;
}

mframe_t soldier_frames_attack2 [] =
{
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_fire2,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_attack2_refire1,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_cock,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_attack2_refire2,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL
};
mmove_t soldier_move_attack2 = {FRAME_attak201, FRAME_attak218, soldier_frames_attack2, soldier_run};

// ATTACK3 (duck and shoot)

void soldier_duck_down (edict_t *self)
{
	if (self->monsterinfo.aiflags & AI_DUCKED)
		return;
	self->monsterinfo.aiflags |= AI_DUCKED;
	self->maxs[2] -= 32;
	self->takedamage = DAMAGE_YES;
	self->monsterinfo.pausetime = level.time + 1;
	gi.linkentity (self);
}

void soldier_duck_up (edict_t *self)
{
	self->monsterinfo.aiflags &= ~AI_DUCKED;
	self->maxs[2] += 32;
	self->takedamage = DAMAGE_AIM;
	gi.linkentity (self);
}

void soldier_fire3 (edict_t *self)
{
	soldier_duck_down (self);
	soldier_fire (self, 2);
}

void soldier_attack3_refire (edict_t *self)
{
	if ((level.time + 0.4) < self->monsterinfo.pausetime)
		self->monsterinfo.nextframe = FRAME_attak303;
}

mframe_t soldier_frames_attack3 [] =
{
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_fire3,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_attack3_refire,
	ai_charge, 0, soldier_duck_up,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL
};
mmove_t soldier_move_attack3 = {FRAME_attak301, FRAME_attak309, soldier_frames_attack3, soldier_run};

// ATTACK4 (machinegun)

void soldier_fire4 (edict_t *self)
{
	soldier_fire (self, 3);
//
//	if (self->enemy->health <= 0)
//		return;
//
//	if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
//		self->monsterinfo.nextframe = FRAME_attak402;
}

mframe_t soldier_frames_attack4 [] =
{
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_fire4,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL
};
mmove_t soldier_move_attack4 = {FRAME_attak401, FRAME_attak406, soldier_frames_attack4, soldier_run};

#if 0
// ATTACK5 (prone)

void soldier_fire5 (edict_t *self)
{
	soldier_fire (self, 4);
}

void soldier_attack5_refire (edict_t *self)
{
	if (self->enemy->health <= 0)
		return;

	if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
		self->monsterinfo.nextframe = FRAME_attak505;
}

mframe_t soldier_frames_attack5 [] =
{
	ai_charge, 8, NULL,
	ai_charge, 8, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_fire5,
	ai_charge, 0, NULL,
	ai_charge, 0, NULL,
	ai_charge, 0, soldier_attack5_refire
};
mmove_t soldier_move_attack5 = {FRAME_attak501, FRAME_attak508, soldier_frames_attack5, soldier_run};
#endif

// ATTACK6 (run & shoot)

void soldier_fire8 (edict_t *self)
{
	soldier_fire (self, 7);
}

void soldier_attack6_refire (edict_t *self)
{
	if (self->enemy->health <= 0)
		return;

	if (range(self, self->enemy) < RANGE_MID)
		return;

	if (skill->value == 3)
		self->monsterinfo.nextframe = FRAME_runs03;
}

mframe_t soldier_frames_attack6 [] =
{
	ai_charge, 10, NULL,
	ai_charge,  4, NULL,
	ai_charge, 12, NULL,
	ai_charge, 11, soldier_fire8,
	ai_charge, 13, NULL,
	ai_charge, 18, NULL,
	ai_charge, 15, NULL,
	ai_charge, 14, NULL,
	ai_charge, 11, NULL,
	ai_charge,  8, NULL,
	ai_charge, 11, NULL,
	ai_charge, 12, NULL,
	ai_charge, 12, NULL,
	ai_charge, 17, soldier_attack6_refire
};
mmove_t soldier_move_attack6 = {FRAME_runs01, FRAME_runs14, soldier_frames_attack6, soldier_run};

void soldier_attack(edict_t *self)
{
	if (self->s.skinnum < 4)
	{
		if (random() < 0.5)
			self->monsterinfo.currentmove = &soldier_move_attack1;
		else
			self->monsterinfo.currentmove = &soldier_move_attack2;
	}
	else
	{
		self->monsterinfo.currentmove = &soldier_move_attack4;
	}
}


//
// SIGHT
//

void soldier_sight(edict_t *self, edict_t *other)
{
	if (random() < 0.5)
		gi.sound (self, CHAN_VOICE, sound_sight1, 1, ATTN_NORM, 0);
	else
		gi.sound (self, CHAN_VOICE, sound_sight2, 1, ATTN_NORM, 0);

	if ((skill->value > 0) && (range(self, self->enemy) >= RANGE_MID))
	{
		if (random() > 0.5)
			self->monsterinfo.currentmove = &soldier_move_attack6;
	}
}

//
// DUCK
//

void soldier_duck_hold (edict_t *self)
{
	if (level.time >= self->monsterinfo.pausetime)
		self->monsterinfo.aiflags &= ~AI_HOLD_FRAME;
	else
		self->monsterinfo.aiflags |= AI_HOLD_FRAME;
}

mframe_t soldier_frames_duck [] =
{
	ai_move, 5, soldier_duck_down,
	ai_move, -1, soldier_duck_hold,
	ai_move, 1,  NULL,
	ai_move, 0,  soldier_duck_up,
	ai_move, 5,  NULL
};
mmove_t soldier_move_duck = {FRAME_duck01, FRAME_duck05, soldier_frames_duck, soldier_run};

void soldier_dodge (edict_t *self, edict_t *attacker, float eta)
{
	float	r;

	r = random();
	if (r > 0.25)
		return;

	if (!self->enemy)
		self->enemy = attacker;

	if (skill->value == 0)
	{
		self->monsterinfo.currentmove = &soldier_move_duck;
		return;
	}

	self->monsterinfo.pausetime = level.time + eta + 0.3;
	r = random();

	if (skill->value == 1)
	{
		if (r > 0.33)
			self->monsterinfo.currentmove = &soldier_move_duck;
		else
			self->monsterinfo.currentmove = &soldier_move_attack3;
		return;
	}

	if (skill->value >= 2)
	{
		if (r > 0.66)
			self->monsterinfo.currentmove = &soldier_move_duck;
		else
			self->monsterinfo.currentmove = &soldier_move_attack3;
		return;
	}

	self->monsterinfo.currentmove = &soldier_move_attack3;
}


//
// DEATH
//

void soldier_fire6 (edict_t *self)
{
	soldier_fire (self, 5);
}

void soldier_fire7 (edict_t *self)
{
	soldier_fire (self, 6);
}

void soldier_dead (edict_t *self)
{
	VectorSet (self->mins, -16, -16, -24);
	VectorSet (self->maxs, 16, 16, -8);
	self->movetype = MOVETYPE_TOSS;
	self->svflags |= SVF_DEADMONSTER;
	self->nextthink = 0;
	gi.linkentity (self);
}

mframe_t soldier_frames_death1 [] =
{
	ai_move, 0,   NULL,
	ai_move, -10, NULL,
	ai_move, -10, NULL,
	ai_move, -10, NULL,
	ai_move, -5,  NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   soldier_fire6,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   soldier_fire7,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL
};
mmove_t soldier_move_death1 = {FRAME_death101, FRAME_death136, soldier_frames_death1, soldier_dead};

mframe_t soldier_frames_death2 [] =
{
	ai_move, -5,  NULL,
	ai_move, -5,  NULL,
	ai_move, -5,  NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL
};
mmove_t soldier_move_death2 = {FRAME_death201, FRAME_death235, soldier_frames_death2, soldier_dead};

mframe_t soldier_frames_death3 [] =
{
	ai_move, -5,  NULL,
	ai_move, -5,  NULL,
	ai_move, -5,  NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
};
mmove_t soldier_move_death3 = {FRAME_death301, FRAME_death345, soldier_frames_death3, soldier_dead};

mframe_t soldier_frames_death4 [] =
{
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL
};
mmove_t soldier_move_death4 = {FRAME_death401, FRAME_death453, soldier_frames_death4, soldier_dead};

mframe_t soldier_frames_death5 [] =
{
	ai_move, -5,  NULL,
	ai_move, -5,  NULL,
	ai_move, -5,  NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,

	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL
};
mmove_t soldier_move_death5 = {FRAME_death501, FRAME_death524, soldier_frames_death5, soldier_dead};

mframe_t soldier_frames_death6 [] =
{
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL,
	ai_move, 0,   NULL
};
mmove_t soldier_move_death6 = {FRAME_death601, FRAME_death610, soldier_frames_death6, soldier_dead};

void soldier_die (edict_t *self, edict_t *inflictor, edict_t *attacker, int damage, vec3_t point)
{
	int		n;

// check for gib
	if (self->health <= self->gib_health)
	{
		gi.sound (self, CHAN_VOICE, gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0);
		for (n= 0; n < 3; n++)
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC);
		ThrowGib (self, "models/objects/gibs/chest/tris.md2", damage, GIB_ORGANIC);
		ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC);
		self->deadflag = DEAD_DEAD;
		return;
	}

	if (self->deadflag == DEAD_DEAD)
		return;

// regular death
	self->deadflag = DEAD_DEAD;
	self->takedamage = DAMAGE_YES;
	self->s.skinnum |= 1;

	if (self->s.skinnum == 1)
		gi.sound (self, CHAN_VOICE, sound_death_light, 1, ATTN_NORM, 0);
	else if (self->s.skinnum == 3)
		gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0);
	else // (self->s.skinnum == 5)
		gi.sound (self, CHAN_VOICE, sound_death_ss, 1, ATTN_NORM, 0);

	if (fabs((self->s.origin[2] + self->viewheight) - point[2]) <= 4)
	{
		// head shot
		self->monsterinfo.currentmove = &soldier_move_death3;
		return;
	}

	n = rand() % 5;
	if (n == 0)
		self->monsterinfo.currentmove = &soldier_move_death1;
	else if (n == 1)
		self->monsterinfo.currentmove = &soldier_move_death2;
	else if (n == 2)
		self->monsterinfo.currentmove = &soldier_move_death4;
	else if (n == 3)
		self->monsterinfo.currentmove = &soldier_move_death5;
	else
		self->monsterinfo.currentmove = &soldier_move_death6;
}


//
// SPAWN
//

void SP_monster_soldier_x (edict_t *self)
{

	self->s.modelindex = gi.modelindex ("models/monsters/soldier/tris.md2");
	self->monsterinfo.scale = MODEL_SCALE;
	VectorSet (self->mins, -16, -16, -24);
	VectorSet (self->maxs, 16, 16, 32);
	self->movetype = MOVETYPE_STEP;
	self->solid = SOLID_BBOX;

	sound_idle =	gi.soundindex ("soldier/solidle1.wav");
	sound_sight1 =	gi.soundindex ("soldier/solsght1.wav");
	sound_sight2 =	gi.soundindex ("soldier/solsrch1.wav");
	sound_cock =	gi.soundindex ("infantry/infatck3.wav");

	self->mass = 100;

	self->pain = soldier_pain;
	self->die = soldier_die;

	self->monsterinfo.stand = soldier_stand;
	self->monsterinfo.walk = soldier_walk;
	self->monsterinfo.run = soldier_run;
	self->monsterinfo.dodge = soldier_dodge;
	self->monsterinfo.attack = soldier_attack;
	self->monsterinfo.melee = NULL;
	self->monsterinfo.sight = soldier_sight;

	gi.linkentity (self);

	self->monsterinfo.stand (self);

	walkmonster_start (self);
}


/*QUAKED monster_soldier_light (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
*/
void SP_monster_soldier_light (edict_t *self)
{
	if (deathmatch->value)
	{
		G_FreeEdict (self);
		return;
	}

	SP_monster_soldier_x (self);

	sound_pain_light = gi.soundindex ("soldier/solpain2.wav");
	sound_death_light =	gi.soundindex ("soldier/soldeth2.wav");
	gi.modelindex ("models/objects/laser/tris.md2");
	gi.soundindex ("misc/lasfly.wav");
	gi.soundindex ("soldier/solatck2.wav");

	self->s.skinnum = 0;
	self->health = 20;
	self->gib_health = -30;
}

/*QUAKED monster_soldier (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
*/
void SP_monster_soldier (edict_t *self)
{
	if (deathmatch->value)
	{
		G_FreeEdict (self);
		return;
	}

	SP_monster_soldier_x (self);

	sound_pain = gi.soundindex ("soldier/solpain1.wav");
	sound_death = gi.soundindex ("soldier/soldeth1.wav");
	gi.soundindex ("soldier/solatck1.wav");

	self->s.skinnum = 2;
	self->health = 30;
	self->gib_health = -30;
}

/*QUAKED monster_soldier_ss (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
*/
void SP_monster_soldier_ss (edict_t *self)
{
	if (deathmatch->value)
	{
		G_FreeEdict (self);
		return;
	}

	SP_monster_soldier_x (self);

	sound_pain_ss = gi.soundindex ("soldier/solpain3.wav");
	sound_death_ss = gi.soundindex ("soldier/soldeth3.wav");
	gi.soundindex ("soldier/solatck3.wav");

	self->s.skinnum = 4;
	self->health = 40;
	self->gib_health = -30;
}
"""

def soldier_idle (self):
	#edict_t *self
	if g_local.random() > 0.8:
		g_main.gi.sound (self, CHAN_VOICE, sound_idle, 1, ATTN_IDLE, 0)

def soldier_cock (self):
	#edict_t *self
	global sound_cock
	if self.s.frame == FRAME_stand322:
		g_main.gi.sound (self, CHAN_WEAPON, sound_cock, 1, ATTN_IDLE, 0)
	else:
		g_main.gi.sound (self, CHAN_WEAPON, sound_cock, 1, ATTN_NORM, 0)

def soldier_stand (self):
	#edict_t *self
	if (self.monsterinfo.currentmove == soldier_move_stand3) or (g_local.random() < 0.8):
		self.monsterinfo.currentmove = soldier_move_stand1
	else:
		self.monsterinfo.currentmove = soldier_move_stand3

def soldier_walk1_random (self):
	#edict_t *self
	if g_local.random() > 0.1:
		self.monsterinfo.nextframe = FRAME_walk101

def soldier_walk (self):
	#edict_t *self
	if g_local.random() < 0.5:
		self.monsterinfo.currentmove = soldier_move_walk1
	else:
		self.monsterinfo.currentmove = soldier_move_walk2

def soldier_run (self):
	#edict_t *self
	if self.monsterinfo.aiflags & AI_STAND_GROUND:
		self.monsterinfo.currentmove = soldier_move_stand1
		return

	if self.monsterinfo.currentmove == soldier_move_walk1 or \
		self.monsterinfo.currentmove == soldier_move_walk2 or \
		self.monsterinfo.currentmove == soldier_move_start_run:
		self.monsterinfo.currentmove = soldier_move_run
	else:
		self.monsterinfo.currentmove = soldier_move_start_run

def soldier_pain (self, other, kick, damage):
	#edict_t *self, *other; float kick; int damage
	r = 0.0
	n = 0

	if self.health < (self.max_health // 2):	# int division
		self.s.skinnum |= 1

	if g_main.level.time < self.pain_debounce_time:
		if (self.velocity[2] > 100) and ((self.monsterinfo.currentmove == soldier_move_pain1) or (self.monsterinfo.currentmove == soldier_move_pain2) or (self.monsterinfo.currentmove == soldier_move_pain3)):
			self.monsterinfo.currentmove = soldier_move_pain4
		return

	self.pain_debounce_time = g_main.level.time + 3

	n = self.s.skinnum | 1
	if n == 1:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain_light, 1, ATTN_NORM, 0)
	elif n == 3:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_pain_ss, 1, ATTN_NORM, 0)

	if self.velocity[2] > 100:
		self.monsterinfo.currentmove = soldier_move_pain4
		return

	if g_main.skill.value == 3:
		return  # no pain anims in nightmare

	r = g_local.random()

	if r < 0.33:
		self.monsterinfo.currentmove = soldier_move_pain1
	elif r < 0.66:
		self.monsterinfo.currentmove = soldier_move_pain2
	else:
		self.monsterinfo.currentmove = soldier_move_pain3

def soldier_fire (self, flash_number):
	#edict_t *self; int flash_number
	global sound_cock
	start = [0.0, 0.0, 0.0]
	forward = [0.0, 0.0, 0.0]
	right = [0.0, 0.0, 0.0]
	up = [0.0, 0.0, 0.0]
	aim = [0.0, 0.0, 0.0]
	dir = [0.0, 0.0, 0.0]
	end = [0.0, 0.0, 0.0]
	r = 0.0
	u = 0.0
	flash_index = 0

	if self.s.skinnum < 2:
		flash_index = blaster_flash[flash_number]
	elif self.s.skinnum < 4:
		flash_index = shotgun_flash[flash_number]
	else:
		flash_index = machinegun_flash[flash_number]

	q_shared.AngleVectors (self.s.angles, forward, right, None)
	G_ProjectSource (self.s.origin, m_flash.monster_flash_offset[flash_index], forward, right, start)

	if flash_number == 5 or flash_number == 6:
		q_shared.VectorCopy (forward, aim)
	else:
		q_shared.VectorCopy (self.enemy.s.origin, end)
		end[2] += self.enemy.viewheight
		q_shared.VectorSubtract (end, start, aim)
		g_utils.vectoangles (aim, dir)
		q_shared.AngleVectors (dir, forward, right, up)

		r = g_local.crandom() * 1000
		u = g_local.crandom() * 500
		q_shared.VectorMA (start, 8192, forward, end)
		q_shared.VectorMA (end, r, right, end)
		q_shared.VectorMA (end, u, up, end)

		q_shared.VectorSubtract (end, start, aim)
		q_shared.VectorNormalize (aim)

	if self.s.skinnum <= 1:
		monster_fire_blaster (self, start, aim, 5, 600, flash_index, EF_BLASTER)
	elif self.s.skinnum <= 3:
		monster_fire_shotgun (self, start, aim, 2, 1, DEFAULT_SHOTGUN_HSPREAD, DEFAULT_SHOTGUN_VSPREAD, DEFAULT_SHOTGUN_COUNT, flash_index)
	else:
		if not (self.monsterinfo.aiflags & AI_HOLD_FRAME):
			self.monsterinfo.pausetime = g_main.level.time + (3 + _r.randint(0, 2147483647) % 8) * FRAMETIME

		monster_fire_bullet (self, start, aim, 2, 4, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, flash_index)

		if g_main.level.time >= self.monsterinfo.pausetime:
			self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
		else:
			self.monsterinfo.aiflags |= AI_HOLD_FRAME

def soldier_fire1 (self):
	#edict_t *self
	soldier_fire (self, 0)

def soldier_attack1_refire1 (self):
	#edict_t *self
	if self.s.skinnum > 1:
		return

	if self.enemy.health <= 0:
		return

	if ((g_main.skill.value == 3) and (g_local.random() < 0.5)) or (g_ai.range (self, self.enemy) == RANGE_MELEE):
		self.monsterinfo.nextframe = FRAME_attak102
	else:
		self.monsterinfo.nextframe = FRAME_attak110

def soldier_attack1_refire2 (self):
	#edict_t *self
	if self.s.skinnum < 2:
		return

	if self.enemy.health <= 0:
		return

	if ((g_main.skill.value == 3) and (g_local.random() < 0.5)) or (g_ai.range (self, self.enemy) == RANGE_MELEE):
		self.monsterinfo.nextframe = FRAME_attak102

def soldier_fire2 (self):
	#edict_t *self
	soldier_fire (self, 1)

def soldier_attack2_refire1 (self):
	#edict_t *self
	if self.s.skinnum > 1:
		return

	if self.enemy.health <= 0:
		return

	if ((g_main.skill.value == 3) and (g_local.random() < 0.5)) or (g_ai.range (self, self.enemy) == RANGE_MELEE):
		self.monsterinfo.nextframe = FRAME_attak204
	else:
		self.monsterinfo.nextframe = FRAME_attak216

def soldier_attack2_refire2 (self):
	#edict_t *self
	if self.s.skinnum < 2:
		return

	if self.enemy.health <= 0:
		return

	if ((g_main.skill.value == 3) and (g_local.random() < 0.5)) or (g_ai.range (self, self.enemy) == RANGE_MELEE):
		self.monsterinfo.nextframe = FRAME_attak204

def soldier_duck_down (self):
	#edict_t *self
	if self.monsterinfo.aiflags & AI_DUCKED:
		return
	self.monsterinfo.aiflags |= AI_DUCKED
	self.maxs[2] -= 32
	self.takedamage = DAMAGE_YES
	self.monsterinfo.pausetime = g_main.level.time + 1
	g_main.gi.linkentity (self)

def soldier_duck_up (self):
	#edict_t *self
	self.monsterinfo.aiflags &= ~AI_DUCKED
	self.maxs[2] += 32
	self.takedamage = DAMAGE_AIM
	g_main.gi.linkentity (self)

def soldier_fire3 (self):
	#edict_t *self
	soldier_duck_down (self)
	soldier_fire (self, 2)

def soldier_attack3_refire (self):
	#edict_t *self
	if (g_main.level.time + 0.4) < self.monsterinfo.pausetime:
		self.monsterinfo.nextframe = FRAME_attak303

def soldier_fire4 (self):
	#edict_t *self
	soldier_fire (self, 3)
	#
	# if (self->enemy->health <= 0)
	# 	return
	#
	# if ( ((skill->value == 3) && (random() < 0.5)) || (range(self, self->enemy) == RANGE_MELEE) )
	# 	self->monsterinfo.nextframe = FRAME_attak402

def soldier_fire8 (self):
	#edict_t *self
	soldier_fire (self, 7)

def soldier_attack6_refire (self):
	#edict_t *self
	if self.enemy.health <= 0:
		return

	if g_ai.range (self, self.enemy) < RANGE_MID:
		return

	if g_main.skill.value == 3:
		self.monsterinfo.nextframe = FRAME_runs03

def soldier_attack (self):
	#edict_t *self
	if self.s.skinnum < 4:
		if g_local.random() < 0.5:
			self.monsterinfo.currentmove = soldier_move_attack1
		else:
			self.monsterinfo.currentmove = soldier_move_attack2
	else:
		self.monsterinfo.currentmove = soldier_move_attack4

def soldier_sight (self, other):
	#edict_t *self, *other
	if g_local.random() < 0.5:
		g_main.gi.sound (self, CHAN_VOICE, sound_sight1, 1, ATTN_NORM, 0)
	else:
		g_main.gi.sound (self, CHAN_VOICE, sound_sight2, 1, ATTN_NORM, 0)

	if (g_main.skill.value > 0) and (g_ai.range (self, self.enemy) >= RANGE_MID):
		if g_local.random() > 0.5:
			self.monsterinfo.currentmove = soldier_move_attack6

def soldier_duck_hold (self):
	#edict_t *self
	if g_main.level.time >= self.monsterinfo.pausetime:
		self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
	else:
		self.monsterinfo.aiflags |= AI_HOLD_FRAME

def soldier_dodge (self, attacker, eta):
	#edict_t *self, *attacker; float eta
	r = 0.0

	r = g_local.random()
	if r > 0.25:
		return

	if not self.enemy:
		self.enemy = attacker

	if g_main.skill.value == 0:
		self.monsterinfo.currentmove = soldier_move_duck
		return

	self.monsterinfo.pausetime = g_main.level.time + eta + 0.3
	r = g_local.random()

	if g_main.skill.value == 1:
		if r > 0.33:
			self.monsterinfo.currentmove = soldier_move_duck
		else:
			self.monsterinfo.currentmove = soldier_move_attack3
		return

	if g_main.skill.value >= 2:
		if r > 0.66:
			self.monsterinfo.currentmove = soldier_move_duck
		else:
			self.monsterinfo.currentmove = soldier_move_attack3
		return

	self.monsterinfo.currentmove = soldier_move_attack3

def soldier_fire6 (self):
	#edict_t *self
	soldier_fire (self, 5)

def soldier_fire7 (self):
	#edict_t *self
	soldier_fire (self, 6)

def soldier_dead (self):
	#edict_t *self
	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, -8)
	self.movetype = MOVETYPE_TOSS
	self.svflags |= SVF_DEADMONSTER
	self.nextthink = 0
	g_main.gi.linkentity (self)

def soldier_die (self, inflictor, attacker, damage, point):
	#edict_t *self, *inflictor, *attacker; int damage; vec3_t point
	n = 0

	# check for gib
	if self.health <= self.gib_health:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(3):
			ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		ThrowGib (self, "models/objects/gibs/chest/tris.md2", damage, GIB_ORGANIC)
		ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)
		self.deadflag = DEAD_DEAD
		return

	if self.deadflag == DEAD_DEAD:
		return

	# regular death
	self.deadflag = DEAD_DEAD
	self.takedamage = DAMAGE_YES
	self.s.skinnum |= 1

	if self.s.skinnum == 1:
		g_main.gi.sound (self, CHAN_VOICE, sound_death_light, 1, ATTN_NORM, 0)
	elif self.s.skinnum == 3:
		g_main.gi.sound (self, CHAN_VOICE, sound_death, 1, ATTN_NORM, 0)
	else:  # (self->s.skinnum == 5)
		g_main.gi.sound (self, CHAN_VOICE, sound_death_ss, 1, ATTN_NORM, 0)

	if abs((self.s.origin[2] + self.viewheight) - point[2]) <= 4:
		# head shot
		self.monsterinfo.currentmove = soldier_move_death3
		return

	n = _r.randint(0, 2147483647) % 5
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

def SP_monster_soldier_x (self): #edict_t *

	global sound_idle, sound_sight1, sound_sight2, sound_cock

	self.s.modelindex = g_main.gi.modelindex ("models/monsters/soldier/tris.md2")
	self.monsterinfo.scale = MODEL_SCALE
	q_shared.VectorSet (self.mins, -16, -16, -24)
	q_shared.VectorSet (self.maxs, 16, 16, 32)
	self.movetype = MOVETYPE_STEP
	self.solid = SOLID_BBOX

	sound_idle =	g_main.gi.soundindex ("soldier/solidle1.wav")
	sound_sight1 =	g_main.gi.soundindex ("soldier/solsght1.wav")
	sound_sight2 =	g_main.gi.soundindex ("soldier/solsrch1.wav")
	sound_cock =	g_main.gi.soundindex ("infantry/infatck3.wav")

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

	g_main.gi.linkentity (self)

	self.monsterinfo.stand (self)

	walkmonster_start (self)


"""QUAKED monster_soldier_light (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_soldier_light (self): #edict_t *

	global sound_pain_light, sound_death_light

	if g_main.deathmatch.value:
	
		G_FreeEdict (self)
		return
	

	SP_monster_soldier_x (self)

	sound_pain_light = g_main.gi.soundindex ("soldier/solpain2.wav")
	sound_death_light =	g_main.gi.soundindex ("soldier/soldeth2.wav")
	g_main.gi.modelindex ("models/objects/laser/tris.md2")
	g_main.gi.soundindex ("misc/lasfly.wav")
	g_main.gi.soundindex ("soldier/solatck2.wav")

	self.s.skinnum = 0
	self.health = 20
	self.gib_health = -30


"""QUAKED monster_soldier (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_soldier (self): #edict_t *

	global sound_pain, sound_death

	if g_main.deathmatch.value:
	
		G_FreeEdict (self)
		return
	

	SP_monster_soldier_x (self)

	sound_pain = g_main.gi.soundindex ("soldier/solpain1.wav")
	sound_death = g_main.gi.soundindex ("soldier/soldeth1.wav")
	g_main.gi.soundindex ("soldier/solatck1.wav")

	self.s.skinnum = 2
	self.health = 30
	self.gib_health = -30


"""QUAKED monster_soldier_ss (1 .5 0) (-16 -16 -24) (16 16 32) Ambush Trigger_Spawn Sight
"""
def SP_monster_soldier_ss (self): #edict_t *

	global sound_pain_ss, sound_death_ss

	if g_main.deathmatch.value:
	
		G_FreeEdict (self)
		return
	

	SP_monster_soldier_x (self)

	sound_pain_ss = g_main.gi.soundindex ("soldier/solpain3.wav")
	sound_death_ss = g_main.gi.soundindex ("soldier/soldeth3.wav")
	g_main.gi.soundindex ("soldier/solatck3.wav")

	self.s.skinnum = 4
	self.health = 40
	self.gib_health = -30


#=================
# move tables
#=================
soldier_frames_stand1 = [_mf(ai_stand, 0, soldier_idle), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None)]
soldier_frames_stand3 = [_mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, soldier_cock), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None), _mf(ai_stand, 0, None)]
soldier_frames_walk1 = [_mf(ai_walk, 3, None), _mf(ai_walk, 6, None), _mf(ai_walk, 2, None), _mf(ai_walk, 2, None), _mf(ai_walk, 2, None), _mf(ai_walk, 1, None), _mf(ai_walk, 6, None), _mf(ai_walk, 5, None), _mf(ai_walk, 3, None), _mf(ai_walk, -1, soldier_walk1_random), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None), _mf(ai_walk, 0, None)]
soldier_frames_walk2 = [_mf(ai_walk, 4, None), _mf(ai_walk, 4, None), _mf(ai_walk, 9, None), _mf(ai_walk, 8, None), _mf(ai_walk, 5, None), _mf(ai_walk, 1, None), _mf(ai_walk, 3, None), _mf(ai_walk, 7, None), _mf(ai_walk, 6, None), _mf(ai_walk, 7, None)]
soldier_frames_start_run = [_mf(ai_run, 7, None), _mf(ai_run, 5, None)]
soldier_frames_run = [_mf(ai_run, 10, None), _mf(ai_run, 11, None), _mf(ai_run, 11, None), _mf(ai_run, 16, None), _mf(ai_run, 10, None), _mf(ai_run, 15, None)]
soldier_frames_pain1 = [_mf(ai_move, -3, None), _mf(ai_move, 4, None), _mf(ai_move, 1, None), _mf(ai_move, 1, None), _mf(ai_move, 0, None)]
soldier_frames_pain2 = [_mf(ai_move, -13, None), _mf(ai_move, -1, None), _mf(ai_move, 2, None), _mf(ai_move, 4, None), _mf(ai_move, 2, None), _mf(ai_move, 3, None), _mf(ai_move, 2, None)]
soldier_frames_pain3 = [_mf(ai_move, -8, None), _mf(ai_move, 10, None), _mf(ai_move, -4, None), _mf(ai_move, -1, None), _mf(ai_move, -3, None), _mf(ai_move, 0, None), _mf(ai_move, 3, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 1, None), _mf(ai_move, 0, None), _mf(ai_move, 1, None), _mf(ai_move, 2, None), _mf(ai_move, 4, None), _mf(ai_move, 3, None), _mf(ai_move, 2, None)]
soldier_frames_pain4 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, -10, None), _mf(ai_move, -6, None), _mf(ai_move, 8, None), _mf(ai_move, 4, None), _mf(ai_move, 1, None), _mf(ai_move, 0, None), _mf(ai_move, 2, None), _mf(ai_move, 5, None), _mf(ai_move, 2, None), _mf(ai_move, -1, None), _mf(ai_move, -1, None), _mf(ai_move, 3, None), _mf(ai_move, 2, None), _mf(ai_move, 0, None)]
soldier_frames_attack1 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack1_refire1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_cock), _mf(ai_charge, 0, soldier_attack1_refire2), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack2 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire2), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack2_refire1), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_cock), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack2_refire2), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack3 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire3), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_attack3_refire), _mf(ai_charge, 0, soldier_duck_up), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack4 = [_mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, soldier_fire4), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None), _mf(ai_charge, 0, None)]
soldier_frames_attack6 = [_mf(ai_charge, 10, None), _mf(ai_charge, 4, None), _mf(ai_charge, 12, None), _mf(ai_charge, 11, soldier_fire8), _mf(ai_charge, 13, None), _mf(ai_charge, 18, None), _mf(ai_charge, 15, None), _mf(ai_charge, 14, None), _mf(ai_charge, 11, None), _mf(ai_charge, 8, None), _mf(ai_charge, 11, None), _mf(ai_charge, 12, None), _mf(ai_charge, 12, None), _mf(ai_charge, 17, soldier_attack6_refire)]
soldier_frames_duck = [_mf(ai_move, 5, soldier_duck_down), _mf(ai_move, -1, soldier_duck_hold), _mf(ai_move, 1, None), _mf(ai_move, 0, soldier_duck_up), _mf(ai_move, 5, None)]
soldier_frames_death1 = [_mf(ai_move, 0, None), _mf(ai_move, -10, None), _mf(ai_move, -10, None), _mf(ai_move, -10, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, soldier_fire6), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, soldier_fire7), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death2 = [_mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death3 = [_mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death4 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death5 = [_mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, -5, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_frames_death6 = [_mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None), _mf(ai_move, 0, None)]
soldier_move_stand1 = _mm(FRAME_stand101, FRAME_stand130, soldier_frames_stand1, soldier_stand)
soldier_move_stand3 = _mm(FRAME_stand301, FRAME_stand339, soldier_frames_stand3, soldier_stand)
soldier_move_walk1 = _mm(FRAME_walk101, FRAME_walk133, soldier_frames_walk1, None)
soldier_move_walk2 = _mm(FRAME_walk209, FRAME_walk218, soldier_frames_walk2, None)
soldier_move_start_run = _mm(FRAME_run01, FRAME_run02, soldier_frames_start_run, soldier_run)
soldier_move_run = _mm(FRAME_run03, FRAME_run08, soldier_frames_run, None)
soldier_move_pain1 = _mm(FRAME_pain101, FRAME_pain105, soldier_frames_pain1, soldier_run)
soldier_move_pain2 = _mm(FRAME_pain201, FRAME_pain207, soldier_frames_pain2, soldier_run)
soldier_move_pain3 = _mm(FRAME_pain301, FRAME_pain318, soldier_frames_pain3, soldier_run)
soldier_move_pain4 = _mm(FRAME_pain401, FRAME_pain417, soldier_frames_pain4, soldier_run)
soldier_move_attack1 = _mm(FRAME_attak101, FRAME_attak112, soldier_frames_attack1, soldier_run)
soldier_move_attack2 = _mm(FRAME_attak201, FRAME_attak218, soldier_frames_attack2, soldier_run)
soldier_move_attack3 = _mm(FRAME_attak301, FRAME_attak309, soldier_frames_attack3, soldier_run)
soldier_move_attack4 = _mm(FRAME_attak401, FRAME_attak406, soldier_frames_attack4, soldier_run)
soldier_move_attack6 = _mm(FRAME_runs01, FRAME_runs14, soldier_frames_attack6, soldier_run)
soldier_move_duck = _mm(FRAME_duck01, FRAME_duck05, soldier_frames_duck, soldier_run)
soldier_move_death1 = _mm(FRAME_death101, FRAME_death136, soldier_frames_death1, soldier_dead)
soldier_move_death2 = _mm(FRAME_death201, FRAME_death235, soldier_frames_death2, soldier_dead)
soldier_move_death3 = _mm(FRAME_death301, FRAME_death345, soldier_frames_death3, soldier_dead)
soldier_move_death4 = _mm(FRAME_death401, FRAME_death453, soldier_frames_death4, soldier_dead)
soldier_move_death5 = _mm(FRAME_death501, FRAME_death524, soldier_frames_death5, soldier_dead)
soldier_move_death6 = _mm(FRAME_death601, FRAME_death610, soldier_frames_death6, soldier_dead)

