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

This file implements all specialized client side effects.  E.g.
weapon effects, enemy effects, flash, etc.

=======================================================================
"""
from __future__ import annotations

from common.shared import rand

import numpy as np
import math
import random
from client import cl_main, ref
from client.sound import sound as sound_c
from common.header import common as common_h
from common.header import shared
from common.shared import flash
from common.shared import shared as shared_c
from common import clientserver
from common import frame
from common import movemsg
from common import netchan
from client import cl_main
from client.header import client as client_h
from client import cl_lights
from client import cl_particles
from client import cl_tempentities
from client.header import client

"""
#include "header/client.h"
"""

colortable = [2 * 8, 13 * 8, 21 * 8, 18 * 8] #static static int

# PGM
# ======================






def CL_AddMuzzleFlash(): #

	"""
	vec3_t fv, rv;
	cdlight_t *dl;
	int i, weapon;
	centity_t *pl;
	int silenced;
	float volume;
	char soundname[64];
	"""
	fv = np.zeros((3,), dtype=np.float32)
	rv = np.zeros((3,), dtype=np.float32)
	soundname = [None] * 64

	i = movemsg.MSG_ReadShort(netchan.net_message)
	if (i < 1) or (i > client_h.MAX_CL_ENTNUM):

		clientserver.Com_Error(common_h.ERR_DROP, "%s: bad entity %d > %d\n", "CL_AddMuzzleFlash", i, client_h.MAX_CL_ENTNUM)


	weapon = movemsg.MSG_ReadByte(netchan.net_message)
	silenced = weapon & shared.MZ_SILENCED
	weapon &= ~shared.MZ_SILENCED
	pl = cl_main.CL_AllocEntity(i)
	if not pl:

		return


	dl = cl_lights.CL_AllocDlight(i)
	shared.VectorCopy(pl.current.origin, dl.origin)
	shared_c.AngleVectors(pl.current.angles, fv, rv, None)
	shared_c.VectorMA(dl.origin, 18, fv, dl.origin)
	shared_c.VectorMA(dl.origin, 16, rv, dl.origin)
	if silenced:

		dl.radius = 100.0 + (rand.randk() & 31)

	else:

		dl.radius = 200.0 + (rand.randk() & 31)


	dl.minlight = 32
	dl.die = cl_main.cl.time
	if silenced:

		volume = 0.2

	else:

		volume = 1


	if weapon == shared.MZ_BLASTER:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/blastf1a.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_BLUEHYPERBLASTER:

		dl.color[0] = 0
		dl.color[1] = 0
		dl.color[2] = 1
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/hyprbf1a.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_HYPERBLASTER:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/hyprbf1a.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_MACHINEGUN:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_SHOTGUN:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/shotgf1b.wav"), volume, shared.ATTN_NORM, 0)
		sound_c.S_StartSound(None, i, shared.CHAN_AUTO, sound_c.S_RegisterSound("weapons/shotgr1b.wav"), volume, shared.ATTN_NORM, 0.1)

	elif weapon == shared.MZ_SSHOTGUN:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/sshotf1b.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_CHAINGUN1:

		dl.radius = 200.0 + (rand.randk() & 31)
		dl.color[0] = 1
		dl.color[1] = 0.25
		dl.color[2] = 0
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_CHAINGUN2:

		dl.radius = 225.0 + (rand.randk() & 31)
		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 0.1
		# long delay
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0)
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0.05)

	elif weapon == shared.MZ_CHAINGUN3:

		dl.radius = 250.0 + (rand.randk() & 31)
		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 0.1
		# long delay
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0)
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0.033)
		soundname = "weapons/machgf%db.wav" % ((rand.randk() % 5) + 1,) # Com_sprintf
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), volume, shared.ATTN_NORM, 0.066)

	elif weapon == shared.MZ_RAILGUN:

		dl.color[0] = 0.5
		dl.color[1] = 0.5
		dl.color[2] = 1.0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/railgf1a.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_ROCKET:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0.2
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/rocklf1a.wav"), volume, shared.ATTN_NORM, 0)
		sound_c.S_StartSound(None, i, shared.CHAN_AUTO, sound_c.S_RegisterSound("weapons/rocklr1b.wav"), volume, shared.ATTN_NORM, 0.1)

	elif weapon == shared.MZ_GRENADE:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/grenlf1a.wav"), volume, shared.ATTN_NORM, 0)
		sound_c.S_StartSound(None, i, shared.CHAN_AUTO, sound_c.S_RegisterSound("weapons/grenlr1b.wav"), volume, shared.ATTN_NORM, 0.1)

	elif weapon == shared.MZ_BFG:

		dl.color[0] = 0
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/bfg__f1y.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_LOGIN:

		dl.color[0] = 0
		dl.color[1] = 1
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 1
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/grenlf1a.wav"), 1, shared.ATTN_NORM, 0)
		CL_LogoutEffect(pl.current.origin, weapon)

	elif weapon == shared.MZ_LOGOUT:

		dl.color[0] = 1
		dl.color[1] = 0
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 1
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/grenlf1a.wav"), 1, shared.ATTN_NORM, 0)
		CL_LogoutEffect(pl.current.origin, weapon)

	elif weapon == shared.MZ_RESPAWN:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 1.0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/grenlf1a.wav"), 1, shared.ATTN_NORM, 0)
		CL_LogoutEffect(pl.current.origin, weapon)

	elif weapon == shared.MZ_PHALANX:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0.5
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/plasshot.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_IONRIPPER:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0.5
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/rippfire.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_ETF_RIFLE:

		dl.color[0] = 0.9
		dl.color[1] = 0.7
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/nail1.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_SHOTGUN2:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/shotg2.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_HEATBEAM:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 100

	elif weapon == shared.MZ_BLASTER2:

		dl.color[0] = 0
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/blastf1a.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_TRACKER:

		# negative flashes handled the same in gl/soft until CL_AddDLights
		dl.color[0] = -1
		dl.color[1] = -1
		dl.color[2] = -1
		sound_c.S_StartSound(None, i, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/disint2.wav"), volume, shared.ATTN_NORM, 0)

	elif weapon == shared.MZ_NUKE1:

		dl.color[0] = 1
		dl.color[1] = 0
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 100

	elif weapon == shared.MZ_NUKE2:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 100

	elif weapon == shared.MZ_NUKE4:

		dl.color[0] = 0
		dl.color[1] = 0
		dl.color[2] = 1
		dl.die = cl_main.cl.time + 100

	elif weapon == shared.MZ_NUKE8:

		dl.color[0] = 0
		dl.color[1] = 1
		dl.color[2] = 1
		dl.die = cl_main.cl.time + 100

def CL_AddMuzzleFlash2(): #

	"""
	int entnum;
	centity_t *ent;
	vec3_t origin;
	unsigned flash_number;
	cdlight_t *dl;
	vec3_t forward, right;
	char soundname[64];
	"""
	origin = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	soundname = [None] * 64

	entnum = movemsg.MSG_ReadShort(netchan.net_message)
	if (entnum < 1) or (entnum > client_h.MAX_CL_ENTNUM):

		clientserver.Com_Error(common_h.ERR_DROP, "%s: bad entity %d > %d\n", "CL_AddMuzzleFlash2", entnum, client_h.MAX_CL_ENTNUM)


	flash_number = movemsg.MSG_ReadByte(netchan.net_message)
	if flash_number > 210:

		clientserver.Com_DPrintf("%s: bad offset\n", "CL_AddMuzzleFlash2")
		return


	ent = cl_main.CL_AllocEntity(entnum)
	if not ent:

		return


	# locate the origin
	shared_c.AngleVectors(ent.current.angles, forward, right, None)
	origin[0] = ent.current.origin[0] + forward[0] * flash.monster_flash_offset[flash_number][0] + right[0] * flash.monster_flash_offset[flash_number][1]
	origin[1] = ent.current.origin[1] + forward[1] * flash.monster_flash_offset[flash_number][0] + right[1] * flash.monster_flash_offset[flash_number][1]
	origin[2] = ent.current.origin[2] + forward[2] * flash.monster_flash_offset[flash_number][0] + right[2] * flash.monster_flash_offset[flash_number][1] + flash.monster_flash_offset[flash_number][2]
	dl = cl_lights.CL_AllocDlight(entnum)
	shared.VectorCopy(origin, dl.origin)
	dl.radius = 200.0 + (rand.randk() & 31)
	dl.minlight = 32
	dl.die = cl_main.cl.time
	if flash_number == shared.MZ2_INFANTRY_MACHINEGUN_1 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_2 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_3 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_4 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_5 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_6 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_7 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_8 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_9 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_10 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_11 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_12 or flash_number == shared.MZ2_INFANTRY_MACHINEGUN_13:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("infantry/infatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_SOLDIER_MACHINEGUN_1 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_2 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_3 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_4 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_5 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_6 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_7 or flash_number == shared.MZ2_SOLDIER_MACHINEGUN_8:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("soldier/solatck3.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_GUNNER_MACHINEGUN_1 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_2 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_3 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_4 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_5 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_6 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_7 or flash_number == shared.MZ2_GUNNER_MACHINEGUN_8:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("gunner/gunatck2.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_ACTOR_MACHINEGUN_1 or flash_number == shared.MZ2_SUPERTANK_MACHINEGUN_1 or flash_number == shared.MZ2_SUPERTANK_MACHINEGUN_2 or flash_number == shared.MZ2_SUPERTANK_MACHINEGUN_3 or flash_number == shared.MZ2_SUPERTANK_MACHINEGUN_4 or flash_number == shared.MZ2_SUPERTANK_MACHINEGUN_5 or flash_number == shared.MZ2_SUPERTANK_MACHINEGUN_6 or flash_number == shared.MZ2_TURRET_MACHINEGUN:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("infantry/infatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_BOSS2_MACHINEGUN_L1 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_L2 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_L3 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_L4 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_L5 or flash_number == shared.MZ2_CARRIER_MACHINEGUN_L1 or flash_number == shared.MZ2_CARRIER_MACHINEGUN_L2:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("infantry/infatck1.wav"), 1, shared.ATTN_NONE, 0)

	elif flash_number == shared.MZ2_SOLDIER_BLASTER_1 or flash_number == shared.MZ2_SOLDIER_BLASTER_2 or flash_number == shared.MZ2_SOLDIER_BLASTER_3 or flash_number == shared.MZ2_SOLDIER_BLASTER_4 or flash_number == shared.MZ2_SOLDIER_BLASTER_5 or flash_number == shared.MZ2_SOLDIER_BLASTER_6 or flash_number == shared.MZ2_SOLDIER_BLASTER_7 or flash_number == shared.MZ2_SOLDIER_BLASTER_8 or flash_number == shared.MZ2_TURRET_BLASTER:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("soldier/solatck2.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_FLYER_BLASTER_1 or flash_number == shared.MZ2_FLYER_BLASTER_2:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("flyer/flyatck3.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_MEDIC_BLASTER_1:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("medic/medatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_HOVER_BLASTER_1:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("hover/hovatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_FLOAT_BLASTER_1:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("floater/fltatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_SOLDIER_SHOTGUN_1 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_2 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_3 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_4 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_5 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_6 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_7 or flash_number == shared.MZ2_SOLDIER_SHOTGUN_8:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("soldier/solatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_TANK_BLASTER_1 or flash_number == shared.MZ2_TANK_BLASTER_2 or flash_number == shared.MZ2_TANK_BLASTER_3:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("tank/tnkatck3.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_TANK_MACHINEGUN_1 or flash_number == shared.MZ2_TANK_MACHINEGUN_2 or flash_number == shared.MZ2_TANK_MACHINEGUN_3 or flash_number == shared.MZ2_TANK_MACHINEGUN_4 or flash_number == shared.MZ2_TANK_MACHINEGUN_5 or flash_number == shared.MZ2_TANK_MACHINEGUN_6 or flash_number == shared.MZ2_TANK_MACHINEGUN_7 or flash_number == shared.MZ2_TANK_MACHINEGUN_8 or flash_number == shared.MZ2_TANK_MACHINEGUN_9 or flash_number == shared.MZ2_TANK_MACHINEGUN_10 or flash_number == shared.MZ2_TANK_MACHINEGUN_11 or flash_number == shared.MZ2_TANK_MACHINEGUN_12 or flash_number == shared.MZ2_TANK_MACHINEGUN_13 or flash_number == shared.MZ2_TANK_MACHINEGUN_14 or flash_number == shared.MZ2_TANK_MACHINEGUN_15 or flash_number == shared.MZ2_TANK_MACHINEGUN_16 or flash_number == shared.MZ2_TANK_MACHINEGUN_17 or flash_number == shared.MZ2_TANK_MACHINEGUN_18 or flash_number == shared.MZ2_TANK_MACHINEGUN_19:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		soundname = "tank/tnkatk2%c.wav" % (97 + (rand.randk() % 5),) # Com_sprintf
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound(soundname), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_CHICK_ROCKET_1 or flash_number == shared.MZ2_TURRET_ROCKET:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0.2
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("chick/chkatck2.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_TANK_ROCKET_1 or flash_number == shared.MZ2_TANK_ROCKET_2 or flash_number == shared.MZ2_TANK_ROCKET_3:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0.2
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("tank/tnkatck1.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_SUPERTANK_ROCKET_1 or flash_number == shared.MZ2_SUPERTANK_ROCKET_2 or flash_number == shared.MZ2_SUPERTANK_ROCKET_3 or flash_number == shared.MZ2_BOSS2_ROCKET_1 or flash_number == shared.MZ2_BOSS2_ROCKET_2 or flash_number == shared.MZ2_BOSS2_ROCKET_3 or flash_number == shared.MZ2_BOSS2_ROCKET_4 or flash_number == shared.MZ2_CARRIER_ROCKET_1:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0.2
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("tank/rocket.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_GUNNER_GRENADE_1 or flash_number == shared.MZ2_GUNNER_GRENADE_2 or flash_number == shared.MZ2_GUNNER_GRENADE_3 or flash_number == shared.MZ2_GUNNER_GRENADE_4:

		dl.color[0] = 1
		dl.color[1] = 0.5
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("gunner/gunatck3.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_GLADIATOR_RAILGUN_1 or flash_number == shared.MZ2_CARRIER_RAILGUN or flash_number == shared.MZ2_WIDOW_RAIL:

		dl.color[0] = 0.5
		dl.color[1] = 0.5
		dl.color[2] = 1.0

	elif flash_number == shared.MZ2_MAKRON_BFG:

		dl.color[0] = 0.5
		dl.color[1] = 1
		dl.color[2] = 0.5

	elif flash_number == shared.MZ2_MAKRON_BLASTER_1 or flash_number == shared.MZ2_MAKRON_BLASTER_2 or flash_number == shared.MZ2_MAKRON_BLASTER_3 or flash_number == shared.MZ2_MAKRON_BLASTER_4 or flash_number == shared.MZ2_MAKRON_BLASTER_5 or flash_number == shared.MZ2_MAKRON_BLASTER_6 or flash_number == shared.MZ2_MAKRON_BLASTER_7 or flash_number == shared.MZ2_MAKRON_BLASTER_8 or flash_number == shared.MZ2_MAKRON_BLASTER_9 or flash_number == shared.MZ2_MAKRON_BLASTER_10 or flash_number == shared.MZ2_MAKRON_BLASTER_11 or flash_number == shared.MZ2_MAKRON_BLASTER_12 or flash_number == shared.MZ2_MAKRON_BLASTER_13 or flash_number == shared.MZ2_MAKRON_BLASTER_14 or flash_number == shared.MZ2_MAKRON_BLASTER_15 or flash_number == shared.MZ2_MAKRON_BLASTER_16 or flash_number == shared.MZ2_MAKRON_BLASTER_17:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("makron/blaster.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_JORG_MACHINEGUN_L1 or flash_number == shared.MZ2_JORG_MACHINEGUN_L2 or flash_number == shared.MZ2_JORG_MACHINEGUN_L3 or flash_number == shared.MZ2_JORG_MACHINEGUN_L4 or flash_number == shared.MZ2_JORG_MACHINEGUN_L5 or flash_number == shared.MZ2_JORG_MACHINEGUN_L6:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("boss3/xfire.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_JORG_MACHINEGUN_R1 or flash_number == shared.MZ2_JORG_MACHINEGUN_R2 or flash_number == shared.MZ2_JORG_MACHINEGUN_R3 or flash_number == shared.MZ2_JORG_MACHINEGUN_R4 or flash_number == shared.MZ2_JORG_MACHINEGUN_R5 or flash_number == shared.MZ2_JORG_MACHINEGUN_R6:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)

	elif flash_number == shared.MZ2_JORG_BFG_1:

		dl.color[0] = 0.5
		dl.color[1] = 1
		dl.color[2] = 0.5

	elif flash_number == shared.MZ2_BOSS2_MACHINEGUN_R1 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_R2 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_R3 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_R4 or flash_number == shared.MZ2_BOSS2_MACHINEGUN_R5 or flash_number == shared.MZ2_CARRIER_MACHINEGUN_R1 or flash_number == shared.MZ2_CARRIER_MACHINEGUN_R2:

		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		cl_particles.CL_ParticleEffect(origin, shared_c.vec3_origin, 0, 40)
		cl_tempentities.CL_SmokeAndFlash(origin)

	elif flash_number == shared.MZ2_STALKER_BLASTER or flash_number == shared.MZ2_DAEDALUS_BLASTER or flash_number == shared.MZ2_MEDIC_BLASTER_2 or flash_number == shared.MZ2_WIDOW_BLASTER or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP1 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP2 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP3 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP4 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP5 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP6 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP7 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP8 or flash_number == shared.MZ2_WIDOW_BLASTER_SWEEP9 or flash_number == shared.MZ2_WIDOW_BLASTER_100 or flash_number == shared.MZ2_WIDOW_BLASTER_90 or flash_number == shared.MZ2_WIDOW_BLASTER_80 or flash_number == shared.MZ2_WIDOW_BLASTER_70 or flash_number == shared.MZ2_WIDOW_BLASTER_60 or flash_number == shared.MZ2_WIDOW_BLASTER_50 or flash_number == shared.MZ2_WIDOW_BLASTER_40 or flash_number == shared.MZ2_WIDOW_BLASTER_30 or flash_number == shared.MZ2_WIDOW_BLASTER_20 or flash_number == shared.MZ2_WIDOW_BLASTER_10 or flash_number == shared.MZ2_WIDOW_BLASTER_0 or flash_number == shared.MZ2_WIDOW_BLASTER_10L or flash_number == shared.MZ2_WIDOW_BLASTER_20L or flash_number == shared.MZ2_WIDOW_BLASTER_30L or flash_number == shared.MZ2_WIDOW_BLASTER_40L or flash_number == shared.MZ2_WIDOW_BLASTER_50L or flash_number == shared.MZ2_WIDOW_BLASTER_60L or flash_number == shared.MZ2_WIDOW_BLASTER_70L or flash_number == shared.MZ2_WIDOW_RUN_1 or flash_number == shared.MZ2_WIDOW_RUN_2 or flash_number == shared.MZ2_WIDOW_RUN_3 or flash_number == shared.MZ2_WIDOW_RUN_4 or flash_number == shared.MZ2_WIDOW_RUN_5 or flash_number == shared.MZ2_WIDOW_RUN_6 or flash_number == shared.MZ2_WIDOW_RUN_7 or flash_number == shared.MZ2_WIDOW_RUN_8:

		dl.color[0] = 0
		dl.color[1] = 1
		dl.color[2] = 0
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("tank/tnkatck3.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_WIDOW_DISRUPTOR:

		dl.color[0] = -1
		dl.color[1] = -1
		dl.color[2] = -1
		sound_c.S_StartSound(None, entnum, shared.CHAN_WEAPON, sound_c.S_RegisterSound("weapons/disint2.wav"), 1, shared.ATTN_NORM, 0)

	elif flash_number == shared.MZ2_WIDOW_PLASMABEAM or flash_number == shared.MZ2_WIDOW2_BEAMER_1 or flash_number == shared.MZ2_WIDOW2_BEAMER_2 or flash_number == shared.MZ2_WIDOW2_BEAMER_3 or flash_number == shared.MZ2_WIDOW2_BEAMER_4 or flash_number == shared.MZ2_WIDOW2_BEAMER_5 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_1 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_2 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_3 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_4 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_5 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_6 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_7 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_8 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_9 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_10 or flash_number == shared.MZ2_WIDOW2_BEAM_SWEEP_11:

		dl.radius = 300.0 + (rand.randk() & 100)
		dl.color[0] = 1
		dl.color[1] = 1
		dl.color[2] = 0
		dl.die = cl_main.cl.time + 200

"""
===============
CL_TeleporterParticles
===============
"""
def CL_TeleporterParticles(ent): #entity_state_t *

	"""
	int i, j;
	cparticle_t *p;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(8):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = 0xdb
		for j in range(2):

			p.org[j] = ent.origin[j] - 16 + (rand.randk() & 31)
			p.vel[j] = rand.crandk() * 14


		p.org[2] = ent.origin[2] - 8 + (rand.randk() & 7)
		p.vel[2] = 80 + (rand.randk() & 7)
		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -0.5
	

"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	float		dec;
	vec3_t		right, up;
	int			i;
	float		d, c, s;
	vec3_t		dir;
	byte		clr = 0x74;

	VectorCopy (start, move);
	VectorSubtract (end, start, vec);
	len = VectorNormalize (vec);

	MakeNormalVectors (vec, right, up);

	for (i=0 ; i<len ; i++)
	{
		if (!free_particles)
			return;

		p = free_particles;
		free_particles = p->next;
		p->next = active_particles;
		active_particles = p;
		
		p->time = cl.time;
		VectorClear (p->accel);

		d = i * 0.1;
		c = cos(d);
		s = sin(d);

		VectorScale (right, c, dir);
		VectorMA (dir, s, up, dir);

		p->alpha = 1.0;
		p->alphavel = -1.0 / (1+frand()*0.2);
		p->color = clr + (rand()&7);
		for (j=0 ; j<3 ; j++)
		{
			p->org[j] = move[j] + dir[j]*3;
			p->vel[j] = dir[j]*6;
		}

		VectorAdd (move, vec, move);
	}

	dec = 0.75;
	VectorScale (vec, dec, vec);
	VectorCopy (start, move);

	while (len > 0)
	{
		len -= dec;

		if (!free_particles)
			return;
		p = free_particles;
		free_particles = p->next;
		p->next = active_particles;
		active_particles = p;

		p->time = cl.time;
		VectorClear (p->accel);

		p->alpha = 1.0;
		p->alphavel = -1.0 / (0.6+frand()*0.2);
		p->color = 0x0 + rand()&15;

		for (j=0 ; j<3 ; j++)
		{
			p->org[j] = move[j] + crand()*3;
			p->vel[j] = crand()*3;
			p->accel[j] = 0;
		}

		VectorAdd (move, vec, move);
	}
	}
"""

"""
===============
CL_LogoutEffect

===============
"""
def CL_LogoutEffect(org, type_): #vec3_t, int

	"""
	int i, j;
	cparticle_t *p;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(500):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		if type_ == shared.MZ_LOGIN:

			p.color = 0xd0 + (rand.randk() & 7)

		elif type_ == shared.MZ_LOGOUT:

			p.color = 0x40 + (rand.randk() & 7)

		else:

			p.color = 0xe0 + (rand.randk() & 7)


		p.org[0] = org[0] - 16 + rand.frandk() * 32
		p.org[1] = org[1] - 16 + rand.frandk() * 32
		p.org[2] = org[2] - 24 + rand.frandk() * 56
		for j in range(3):

			p.vel[j] = rand.crandk() * 20


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (1.0 + rand.frandk() * 0.3)
	

"""
===============
CL_ItemRespawnParticles

===============
"""
def CL_ItemRespawnParticles(org): #vec3_t

	"""
	int i, j;
	cparticle_t *p;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(64):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = 0xd4 + (rand.randk() & 3)
		p.org[0] = org[0] + rand.crandk() * 8
		p.org[1] = org[1] + rand.crandk() * 8
		p.org[2] = org[2] + rand.crandk() * 8
		for j in range(3):

			p.vel[j] = rand.crandk() * 8


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY * 0.2
		p.alpha = 1.0
		p.alphavel = -1.0 / (1.0 + rand.frandk() * 0.3)
	

def CL_ExplosionParticles(org): #vec3_t

	"""
	int i, j;
	cparticle_t *p;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(256):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = 0xe0 + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() % 32) - 16)
			p.vel[j] = (rand.randk() % 384) - 192


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -0.8 / (0.5 + rand.frandk() * 0.3)
def CL_BigTeleportParticles(org): #vec3_t

	"""
	int i;
	cparticle_t *p;
	float time;
	float angle, dist;
	static int colortable[4] = {2 * 8, 13 * 8, 21 * 8, 18 * 8};
	"""

	time = cl_main.cl.time
	for i in range(4096):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = colortable[rand.randk() & 3]
		angle = math.pi * 2 * (rand.randk() & 1023) / 1023.0
		dist = (rand.randk() & 31)
		p.org[0] = org[0] + math.cos(angle) * dist
		p.vel[0] = math.cos(angle) * (70 + (rand.randk() & 63))
		p.accel[0] = -math.cos(angle) * 100
		p.org[1] = org[1] + math.sin(angle) * dist
		p.vel[1] = math.sin(angle) * (70 + (rand.randk() & 63))
		p.accel[1] = -math.sin(angle) * 100
		p.org[2] = org[2] + 8 + (rand.randk() % 90)
		p.vel[2] = -100 + (rand.randk() & 31)
		p.accel[2] = client_h.PARTICLE_GRAVITY * 4
		p.alpha = 1.0
		p.alphavel = -0.3 / (0.5 + rand.frandk() * 0.3)

# ===============
# CL_BlasterParticles
#
# Wall impact puffs
# ===============
def CL_BlasterParticles(org, dir): #vec3_t, vec3_t

	"""
	int i, j;
	cparticle_t *p;
	float d;
	int count;
	float time;
	"""

	time = cl_main.cl.time
	count = 40
	for i in range(count):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = 0xe0 + (rand.randk() & 7)
		d = rand.randk() & 15
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() & 7) - 4) + d * dir[j]
			p.vel[j] = dir[j] * 30 + rand.crandk() * 40


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)
"""
===============
CL_BlasterTrail

===============
"""
def CL_BlasterTrail(start, end): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.3 + rand.frandk() * 0.2)
		p.color = 0xe0
		for j in range(3):

			p.org[j] = move[j] + rand.crandk()
			p.vel[j] = rand.crandk() * 5
			p.accel[j] = 0


		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_QuadTrail

===============
"""
def CL_QuadTrail(start, end): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.8 + rand.frandk() * 0.2)
		p.color = 115
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 16
			p.vel[j] = rand.crandk() * 5
			p.accel[j] = 0


		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_FlagTrail

===============
"""
def CL_FlagTrail(start, end, color): #vec3_t, vec3_t, int

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.8 + rand.frandk() * 0.2)
		p.color = color
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 16
			p.vel[j] = rand.crandk() * 5
			p.accel[j] = 0


		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_DiminishingTrail

===============
"""
def CL_DiminishingTrail(start, end, old, flags): #vec3_t, vec3_t, centity_t *, int

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	float dec;
	float orgscale;
	float velscale;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = int(shared_c.VectorNormalize(vec)) # int len
	dec = 0.5
	shared_c.VectorScale(vec, dec, vec)
	if old.trailcount > 900:

		orgscale = 4
		velscale = 15

	elif old.trailcount > 800:

		orgscale = 2
		velscale = 10

	else:

		orgscale = 1
		velscale = 5


	while len_ > 0:

		len_ = int(len_ - dec) # int len -= float dec
		if not cl_particles.free_particles:

			return


		# drop less particles as it flies
		if (rand.randk() & 1023) < old.trailcount:

			p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
			cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
			shared.VectorClear(p.accel)
			p.time = time
			if flags & shared.EF_GIB:

				p.alpha = 1.0
				p.alphavel = -1.0 / (1 + rand.frandk() * 0.4)
				p.color = 0xe8 + (rand.randk() & 7)
				for j in range(3):

					p.org[j] = move[j] + rand.crandk() * orgscale
					p.vel[j] = rand.crandk() * velscale
					p.accel[j] = 0


				p.vel[2] -= client_h.PARTICLE_GRAVITY

			elif flags & shared.EF_GREENGIB:

				p.alpha = 1.0
				p.alphavel = -1.0 / (1 + rand.frandk() * 0.4)
				p.color = 0xdb + (rand.randk() & 7)
				for j in range(3):

					p.org[j] = move[j] + rand.crandk() * orgscale
					p.vel[j] = rand.crandk() * velscale
					p.accel[j] = 0


				p.vel[2] -= client_h.PARTICLE_GRAVITY

			else:

				p.alpha = 1.0
				p.alphavel = -1.0 / (1 + rand.frandk() * 0.2)
				p.color = 4 + (rand.randk() & 7)
				for j in range(3):

					p.org[j] = move[j] + rand.crandk() * orgscale
					p.vel[j] = rand.crandk() * velscale


				p.accel[2] = 20


		old.trailcount -= 5
		if old.trailcount < 100:

			old.trailcount = 100


		shared.VectorAdd(move, vec, move)
	

def MakeNormalVectors (forward, right, up): #vec3_t, vec3_t, vec3_t

	#float		d;

	# this rotate and negat guarantees a vector
	# not colinear with the original
	right[1] = -forward[0]
	right[2] = forward[1]
	right[0] = forward[2]

	d = shared.DotProduct (right, forward)
	shared_c.VectorMA (right, -d, forward, right)
	shared_c.VectorNormalize (right)
	shared_c.CrossProduct (right, forward, up)


"""
===============
CL_RocketTrail

===============
"""
def CL_RocketTrail(start, end, old): #vec3_t, vec3_t, centity_t *

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	# smoke
	CL_DiminishingTrail(start, end, old, shared.EF_ROCKET)
	# fire
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 1
	shared_c.VectorScale(vec, dec, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		if (rand.randk() & 7) == 0:

			p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
			cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
			shared.VectorClear(p.accel)
			p.time = time
			p.alpha = 1.0
			p.alphavel = -1.0 / (1 + rand.frandk() * 0.2)
			p.color = 0xdc + (rand.randk() & 3)
			for j in range(3):

				p.org[j] = move[j] + rand.crandk() * 5
				p.vel[j] = rand.crandk() * 20


			p.accel[2] = -client_h.PARTICLE_GRAVITY


		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_RailTrail

===============
"""
def CL_RailTrail(start, end): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	float dec;
	vec3_t right, up;
	int i;
	float d, c, s;
	vec3_t dir;
	byte clr = 0x74;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	clr = 0x74

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = int(shared_c.VectorNormalize(vec)) # int len
	MakeNormalVectors(vec, right, up)
	for i in range(len_):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		shared.VectorClear(p.accel)
		d = i * 0.1
		c = math.cos(d)
		s = math.sin(d)
		shared_c.VectorScale(right, c, dir)
		shared_c.VectorMA(dir, s, up, dir)
		p.alpha = 1.0
		p.alphavel = -1.0 / (1 + rand.frandk() * 0.2)
		p.color = clr + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = move[j] + dir[j] * 3
			p.vel[j] = dir[j] * 6


		shared.VectorAdd(move, vec, move)


	dec = 0.75
	shared_c.VectorScale(vec, dec, vec)
	shared.VectorCopy(start, move)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		shared.VectorClear(p.accel)
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.6 + rand.frandk() * 0.2)
		p.color = 0x0 + (rand.randk() & 15)
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 3
			p.vel[j] = rand.crandk() * 3
			p.accel[j] = 0


		shared.VectorAdd(move, vec, move)
	

# RAFAEL
"""
===============
CL_IonripperTrail
===============
"""
def CL_IonripperTrail(start, ent): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int j;
	cparticle_t *p;
	int dec;
	int left = 0;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	left = 0

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(ent, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 0.5
		p.alphavel = -1.0 / (0.3 + rand.frandk() * 0.2)
		p.color = 0xe4 + (rand.randk() & 3)
		for j in range(3):

			p.org[j] = move[j]
			p.accel[j] = 0


		if left:

			left = 0
			p.vel[0] = 10

		else:

			left = 1
			p.vel[0] = -10


		p.vel[1] = 0
		p.vel[2] = 0
		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_BubbleTrail

===============
"""
def CL_BubbleTrail(start, end): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	int len;
	int i, j;
	cparticle_t *p;
	float dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = int(shared_c.VectorNormalize(vec)) # int len
	dec = 32
	shared_c.VectorScale(vec, dec, vec)
	for i in range(0, len_, 32):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (1 + rand.frandk() * 0.2)
		p.color = 4 + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 2
			p.vel[j] = rand.crandk() * 5


		p.vel[2] += 6
		shared.VectorAdd(move, vec, move)

avelocities = np.zeros((common_h.NUMVERTEXNORMALS, 3), dtype=np.float32) #static vec3_t [NUMVERTEXNORMALS]

def CL_FlyParticles(origin, count): #vec3_t, int

	"""
	int i;
	cparticle_t *p;
	float angle;
	float sp, sy, cp, cy;
	vec3_t forward;
	float dist = 64;
	float ltime;
	float time;
	"""
	forward = np.zeros((3,), dtype=np.float32)
	dist = 64

	time = cl_main.cl.time
	if count > common_h.NUMVERTEXNORMALS:

		count = common_h.NUMVERTEXNORMALS


	if not avelocities[0][0]:

		for i in range(common_h.NUMVERTEXNORMALS):

			avelocities[i][0] = (rand.randk() & 255) * 0.01
			avelocities[i][1] = (rand.randk() & 255) * 0.01
			avelocities[i][2] = (rand.randk() & 255) * 0.01


	ltime = time / 1000.0
	for i in range(0, count, 2):

		angle = ltime * avelocities[i][0]
		sy = math.sin(angle)
		cy = math.cos(angle)
		angle = ltime * avelocities[i][1]
		sp = math.sin(angle)
		cp = math.cos(angle)
		forward[0] = cp * cy
		forward[1] = cp * sy
		forward[2] = -sp
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		dist = math.sin(ltime + i) * 64
		p.org[0] = origin[0] + movemsg.bytedirs[i][0] * dist + forward[0] * 16
		p.org[1] = origin[1] + movemsg.bytedirs[i][1] * dist + forward[1] * 16
		p.org[2] = origin[2] + movemsg.bytedirs[i][2] * dist + forward[2] * 16
		shared.VectorClear(p.vel)
		shared.VectorClear(p.accel)
		p.color = 0
		p.colorvel = 0
		p.alpha = 1
		p.alphavel = -100


def CL_FlyEffect(ent, origin): #centity_t *, vec3_t

	"""
	int n;
	int count;
	int starttime;
	"""

	if ent.fly_stoptime < cl_main.cl.time:

		starttime = cl_main.cl.time
		ent.fly_stoptime = cl_main.cl.time + 60000

	else:

		starttime = ent.fly_stoptime - 60000


	n = cl_main.cl.time - starttime
	if n < 20000:

		count = int(n * 162 / 20000.0) # C int

	else:

		n = ent.fly_stoptime - cl_main.cl.time
		if n < 20000:

			count = int(n * 162 / 20000.0) # C int

		else:

			count = 162


	CL_FlyParticles(origin, count)


"""
===============
CL_BfgParticles
===============
"""
def CL_BfgParticles(ent): #entity_t *

	"""
	int i;
	cparticle_t *p;
	float angle;
	float sp, sy, cp, cy;
	vec3_t forward;
	float dist = 64;
	vec3_t v;
	float ltime;
	float time;
	"""
	forward = np.zeros((3,), dtype=np.float32)
	dist = 64
	v = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	if not avelocities[0][0]:

		for i in range(common_h.NUMVERTEXNORMALS):

			avelocities[i][0] = (rand.randk() & 255) * 0.01
			avelocities[i][1] = (rand.randk() & 255) * 0.01
			avelocities[i][2] = (rand.randk() & 255) * 0.01


	ltime = time / 1000.0
	for i in range(common_h.NUMVERTEXNORMALS):

		angle = ltime * avelocities[i][0]
		sy = math.sin(angle)
		cy = math.cos(angle)
		angle = ltime * avelocities[i][1]
		sp = math.sin(angle)
		cp = math.cos(angle)
		forward[0] = cp * cy
		forward[1] = cp * sy
		forward[2] = -sp
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		dist = math.sin(ltime + i) * 64
		p.org[0] = ent.origin[0] + movemsg.bytedirs[i][0] * dist + forward[0] * 16
		p.org[1] = ent.origin[1] + movemsg.bytedirs[i][1] * dist + forward[1] * 16
		p.org[2] = ent.origin[2] + movemsg.bytedirs[i][2] * dist + forward[2] * 16
		shared.VectorClear(p.vel)
		shared.VectorClear(p.accel)
		shared.VectorSubtract(p.org, ent.origin, v)
		dist = shared_c.VectorLength(v) / 90.0
		p.color = math.floor(0xd0 + dist * 7)
		p.colorvel = 0
		p.alpha = 1.0 - dist
		p.alphavel = -100
	


"""
===============
CL_TrapParticles
===============
"""
# RAFAEL
def CL_TrapParticles(ent): #entity_t *

	"""
	vec3_t move;
	vec3_t vec;
	vec3_t start, end;
	int len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	int i, j, k;
	cparticle_t *p;
	float vel;
	vec3_t dir;
	vec3_t org;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	org = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	ent.origin[2] -= 14
	shared.VectorCopy(ent.origin, start)
	shared.VectorCopy(ent.origin, end)
	end[2] += 64
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.3 + rand.frandk() * 0.2)
		p.color = 0xe0
		for j in range(3):

			p.org[j] = move[j] + rand.crandk()
			p.vel[j] = rand.crandk() * 15
			p.accel[j] = 0


		p.accel[2] = client_h.PARTICLE_GRAVITY
		shared.VectorAdd(move, vec, move)


	ent.origin[2] += 14
	shared.VectorCopy(ent.origin, org)
	for i in range(-2, 2 + 1, 4):

		for j in range(-2, 2 + 1, 4):

			for k in range(-2, 4 + 1, 4):

				if not cl_particles.free_particles:

					return


				p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
				cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
				p.time = time
				p.color = 0xe0 + (rand.randk() & 3)
				p.alpha = 1.0
				p.alphavel = -1.0 / (0.3 + (rand.randk() & 7) * 0.02)
				p.org[0] = org[0] + i + ((rand.randk() & 23) * rand.crandk())
				p.org[1] = org[1] + j + ((rand.randk() & 23) * rand.crandk())
				p.org[2] = org[2] + k + ((rand.randk() & 23) * rand.crandk())
				dir[0] = j * 8.0
				dir[1] = i * 8.0
				dir[2] = k * 8.0
				shared_c.VectorNormalize(dir)
				vel = (50 + (rand.randk() & 63))
				shared_c.VectorScale(dir, vel, p.vel)
				p.accel[0] = p.accel[1] = 0
				p.accel[2] = -client_h.PARTICLE_GRAVITY
			

"""
===============
CL_BFGExplosionParticles
===============
"""
#FIXME combined with CL_ExplosionParticles
def CL_BFGExplosionParticles(org): #vec3_t

	"""
	int i, j;
	cparticle_t *p;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(256):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = 0xd0 + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() % 32) - 16)
			p.vel[j] = (rand.randk() % 384) - 192


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -0.8 / (0.5 + rand.frandk() * 0.3)
	

"""
===============
CL_TeleportParticles

===============
"""
def CL_TeleportParticles(org): #vec3_t

	"""
	int i, j, k;
	cparticle_t *p;
	float vel;
	vec3_t dir;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	for i in range(-16, 16 + 1, 4):

		for j in range(-16, 16 + 1, 4):

			for k in range(-16, 32 + 1, 4):

				if not cl_particles.free_particles:

					return


				p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
				cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
				p.time = time
				p.color = 7 + (rand.randk() & 7)
				p.alpha = 1.0
				p.alphavel = -1.0 / (0.3 + (rand.randk() & 7) * 0.02)
				p.org[0] = org[0] + i + (rand.randk() & 3)
				p.org[1] = org[1] + j + (rand.randk() & 3)
				p.org[2] = org[2] + k + (rand.randk() & 3)
				dir[0] = j * 8.0
				dir[1] = i * 8.0
				dir[2] = k * 8.0
				shared_c.VectorNormalize(dir)
				vel = (50 + (rand.randk() & 63))
				shared_c.VectorScale(dir, vel, p.vel)
				p.accel[0] = p.accel[1] = 0
				p.accel[2] = -client_h.PARTICLE_GRAVITY


"""
/*
==============
CL_EntityEvent

An entity has just been parsed that has an event value

the female events are there for backwards compatability
==============
*/
extern struct sfx_s	*cl_sfx_footsteps[4];

"""
def CL_EntityEvent(ent): #entity_state_t *

	if ent.event == shared.entity_event_t.EV_ITEM_RESPAWN.value:

		sound_c.S_StartSound(None, ent.number, shared.CHAN_WEAPON, sound_c.S_RegisterSound("items/respawn1.wav"), 1, shared.ATTN_IDLE, 0)
		CL_ItemRespawnParticles(ent.origin)

	elif ent.event == shared.entity_event_t.EV_PLAYER_TELEPORT.value:

		sound_c.S_StartSound(None, ent.number, shared.CHAN_WEAPON, sound_c.S_RegisterSound("misc/tele1.wav"), 1, shared.ATTN_IDLE, 0)
		CL_TeleportParticles(ent.origin)

	elif ent.event == shared.entity_event_t.EV_FOOTSTEP.value:

		if cl_main.cl_footsteps.value:

			sound_c.S_StartSound(None, ent.number, shared.CHAN_BODY, cl_tempentities.CL_RandomFootstepSfx(), 1, shared.ATTN_NORM, 0)


	elif ent.event == shared.entity_event_t.EV_FALLSHORT.value:

		sound_c.S_StartSound(None, ent.number, shared.CHAN_AUTO, sound_c.S_RegisterSound("player/land1.wav"), 1, shared.ATTN_NORM, 0)

	elif ent.event == shared.entity_event_t.EV_FALL.value:

		sound_c.S_StartSound(None, ent.number, shared.CHAN_AUTO, sound_c.S_RegisterSound("*fall2.wav"), 1, shared.ATTN_NORM, 0)

	elif ent.event == shared.entity_event_t.EV_FALLFAR.value:

		sound_c.S_StartSound(None, ent.number, shared.CHAN_AUTO, sound_c.S_RegisterSound("*fall1.wav"), 1, shared.ATTN_NORM, 0)


# ==============
# CL_ClearEffects
# ==============
def CL_ClearEffects ():

	cl_particles.CL_ClearParticles ()
	cl_lights.CL_ClearDlights ()
	cl_lights.CL_ClearLightStyles ()

import math
import random
import numpy as np
from client import cl_main
from common.header import shared
from common.shared import shared as shared_c
from common import frame
from client import cl_main
from client import cl_parse
from client.header import client as client_h
from client import cl_lights
from client import cl_particles

pass
pass



#=============
#=============
def CL_Flashlight (ent, pos): #int, vec3_t

	#cdlight_t	*dl;

	dl = cl_lights.CL_AllocDlight (ent)
	shared.VectorCopy (pos,  dl.origin)
	dl.radius = 400
	dl.minlight = 250
	dl.die = cl_main.cl.time + 100
	dl.color[0] = 1
	dl.color[1] = 1
	dl.color[2] = 1

"""
======
CL_ColorFlash - flash of light
======
"""
def CL_ColorFlash(pos, ent, intensity, r, g, b): #vec3_t, int, float, float, float, float

	"""
	cdlight_t *dl;
	"""

	dl = cl_lights.CL_AllocDlight(ent)
	shared.VectorCopy(pos, dl.origin)
	dl.radius = intensity
	dl.minlight = 250
	dl.die = cl_main.cl.time + 100
	dl.color[0] = r
	dl.color[1] = g
	dl.color[2] = b


"""
======
CL_DebugTrail
======
"""
def CL_DebugTrail(start, end): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	float len;
	cparticle_t *p;
	float dec;
	vec3_t right, up;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)

	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	MakeNormalVectors(vec, right, up)
	dec = 3
	shared_c.VectorScale(vec, dec, vec)
	shared.VectorCopy(start, move)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = cl_main.cl.time
		shared.VectorClear(p.accel)
		shared.VectorClear(p.vel)
		p.alpha = 1.0
		p.alphavel = -0.1
		p.color = 0x74 + (rand.randk() & 7)
		shared.VectorCopy(move, p.org)
		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_SmokeTrail
===============
"""
def CL_SmokeTrail(start, end, colorStart, colorRun, spacing): #vec3_t, vec3_t, int, int, int

	"""
	vec3_t move;
	vec3_t vec;
	float len, time;
	int j;
	cparticle_t *p;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	shared_c.VectorScale(vec, spacing, vec)
	time = cl_main.cl.time
	while len_ > 0:

		len_ -= spacing
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (1 + rand.frandk() * 0.5)
		p.color = colorStart + (rand.randk() % colorRun)
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 3
			p.accel[j] = 0


		p.vel[2] = 20 + rand.crandk() * 5
		shared.VectorAdd(move, vec, move)
	

def CL_ForceWall(start, end, color8): #vec3_t, vec3_t, int

	"""
	vec3_t move;
	vec3_t vec;
	int j;
	cparticle_t *p;
	float len, time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	shared_c.VectorScale(vec, 4, vec)
	time = cl_main.cl.time
	while len_ > 0:

		len_ -= 4
		if not cl_particles.free_particles:

			return


		if rand.frandk() > 0.3:

			p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
			cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
			shared.VectorClear(p.accel)
			p.time = time
			p.alpha = 1.0
			p.alphavel = -1.0 / (3.0 + rand.frandk() * 0.5)
			p.color = color8
			for j in range(3):

				p.org[j] = move[j] + rand.crandk() * 3
				p.accel[j] = 0


			p.vel[0] = 0
			p.vel[1] = 0
			p.vel[2] = -40 - (rand.crandk() * 10)


		shared.VectorAdd(move, vec, move)
	


#		p->alphavel = alphavel;
	

"""
===============
CL_BubbleTrail2 (lets you control the # of bubbles by setting the distance between the spawns)

===============
"""
def CL_BubbleTrail2(start, end, dist): #vec3_t, vec3_t, int

	"""
	vec3_t move;
	vec3_t vec;
	float len, time;
	int i;
	int j;
	cparticle_t *p;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	shared_c.VectorScale(vec, dist, vec)
	for i in range(0, math.ceil(len_), dist): # for (i = 0; i < len; i += dist), int i, float len

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (1 + rand.frandk() * 0.1)
		p.color = 4 + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 2
			p.vel[j] = rand.crandk() * 10


		p.org[2] -= 4
		p.vel[2] += 20
		shared.VectorAdd(move, vec, move)
	

#define CORKSCREW		1
#define DOUBLE_SCREW	1
RINGS = 1
#define	SPRAY		1

def CL_Heatbeam(start, forward): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	float len;
	int j;
	cparticle_t *p;
	vec3_t right, up;
	float i;
	float c, s;
	vec3_t dir;
	float ltime;
	float step = 32.0, rstep;
	float start_pt;
	float rot;
	float variance;
	float time;
	vec3_t end;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	step = 32.0
	end = np.zeros((3,), dtype=np.float32)

	shared_c.VectorMA(start, 4096, forward, end)
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	shared.VectorCopy(cl_main.cl.v_right, right)
	shared.VectorCopy(cl_main.cl.v_up, up)
	shared_c.VectorMA(move, -0.5, right, move)
	shared_c.VectorMA(move, -0.5, up, move)
	time = cl_main.cl.time
	ltime = cl_main.cl.time / 1000.0
	start_pt = math.fmod(ltime * 96.0, step)
	shared_c.VectorMA(move, start_pt, vec, move)
	shared_c.VectorScale(vec, step, vec)
	rstep = math.pi / 10.0
	i = start_pt
	while i < len_: # for (i = start_pt; i < len; i += step)

		if i > step * 5:

			# don't bother after the 5th ring
			break


		rot = 0
		while rot < math.pi * 2: # for (rot = 0; rot < M_PI * 2; rot += rstep)

			if not cl_particles.free_particles:

				return


			p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
			cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
			p.time = time
			shared.VectorClear(p.accel)
			variance = 0.5
			c = math.cos(rot) * variance
			s = math.sin(rot) * variance
			# trim it so it looks like it's starting at the origin
			if i < 10:

				shared_c.VectorScale(right, c * (i / 10.0), dir)
				shared_c.VectorMA(dir, s * (i / 10.0), up, dir)

			else:

				shared_c.VectorScale(right, c, dir)
				shared_c.VectorMA(dir, s, up, dir)


			p.alpha = 0.5
			p.alphavel = -1000.0
			p.color = 223 - (rand.randk() & 7)
			for j in range(3):

				p.org[j] = move[j] + dir[j] * 3
				p.vel[j] = 0


			rot += rstep

		shared.VectorAdd(move, vec, move)
		i += step
	
#endif
def CL_ParticleSteamEffect(org, dir, color, count, magnitude): #vec3_t, vec3_t, int, int, int

	"""
	int i, j;
	cparticle_t *p;
	float d, time;
	vec3_t r, u;
	"""
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	MakeNormalVectors(dir, r, u)
	for i in range(count):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = color + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = org[j] + magnitude * 0.1 * rand.crandk()


		shared_c.VectorScale(dir, magnitude, p.vel)
		d = rand.crandk() * magnitude / 3
		shared_c.VectorMA(p.vel, d, r, p.vel)
		d = rand.crandk() * magnitude / 3
		shared_c.VectorMA(p.vel, d, u, p.vel)
		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY / 2
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)
	

def CL_ParticleSteamEffect2(self): #cl_sustain_t *

	"""
	int i, j;
	cparticle_t *p;
	float d;
	vec3_t r, u;
	vec3_t dir;
	"""
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	shared.VectorCopy(self.dir, dir)
	MakeNormalVectors(dir, r, u)
	for i in range(self.count):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = cl_main.cl.time
		p.color = self.color + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = self.org[j] + self.magnitude * 0.1 * rand.crandk()


		shared_c.VectorScale(dir, self.magnitude, p.vel)
		d = rand.crandk() * self.magnitude / 3
		shared_c.VectorMA(p.vel, d, r, p.vel)
		d = rand.crandk() * self.magnitude / 3
		shared_c.VectorMA(p.vel, d, u, p.vel)
		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY / 2
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)


	self.nextthink += self.thinkinterval

"""
===============
CL_TrackerTrail
===============
"""
def CL_TrackerTrail(start, end, particleColor): #vec3_t, vec3_t, int

	"""
	vec3_t move;
	vec3_t vec;
	vec3_t forward, right, up, angle_dir;
	float len;
	int j;
	cparticle_t *p;
	int dec;
	float dist;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	angle_dir = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	shared.VectorCopy(vec, forward)
	shared_c.AngleVectors2(forward, angle_dir)
	shared_c.AngleVectors(angle_dir, forward, right, up)
	dec = 3
	shared_c.VectorScale(vec, 3, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -2.0
		p.color = particleColor
		dist = shared.DotProduct(move, forward)
		shared_c.VectorMA(move, 8 * math.cos(dist), up, p.org)
		for j in range(3):

			p.vel[j] = 0
			p.accel[j] = 0


		p.vel[2] = 5
		shared.VectorAdd(move, vec, move)
	

def CL_Tracker_Shell(origin): #vec3_t

	"""
	vec3_t dir;
	int i;
	cparticle_t *p;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	for i in range(300):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = client_h.INSTANT_PARTICLE
		p.color = 0
		dir[0] = rand.crandk()
		dir[1] = rand.crandk()
		dir[2] = rand.crandk()
		shared_c.VectorNormalize(dir)
		shared_c.VectorMA(origin, 40, dir, p.org)
	

def CL_MonsterPlasma_Shell(origin): #vec3_t

	"""
	vec3_t dir;
	int i;
	cparticle_t *p;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	for i in range(40):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = client_h.INSTANT_PARTICLE
		p.color = 0xe0
		dir[0] = rand.crandk()
		dir[1] = rand.crandk()
		dir[2] = rand.crandk()
		shared_c.VectorNormalize(dir)
		shared_c.VectorMA(origin, 10, dir, p.org)
#		VectorMA(origin, 10*(((rand () & 0x7fff) / ((float)0x7fff))), dir, p->org);
	

widowbeamout_colortable = [2*8,13*8,21*8,18*8] #static int colortable[4]

def CL_Widowbeamout(self): #cl_sustain_t *

	"""
	vec3_t dir;
	int i;
	cparticle_t *p;
	static int colortable[4] = {2 * 8, 13 * 8, 21 * 8, 18 * 8};
	float ratio;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	ratio = 1.0 - ((self.endtime - cl_main.cl.time) / 2100.0)
	time = cl_main.cl.time
	for i in range(300):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = client_h.INSTANT_PARTICLE
		p.color = colortable[rand.randk() & 3]
		dir[0] = rand.crandk()
		dir[1] = rand.crandk()
		dir[2] = rand.crandk()
		shared_c.VectorNormalize(dir)
		shared_c.VectorMA(self.org, (45.0 * ratio), dir, p.org)
#		VectorMA(origin, 10*(((rand () & 0x7fff) / ((float)0x7fff))), dir, p->org);
	

nukeblast_colortable = [110, 112, 114, 116] #static int colortable[4]

def CL_Nukeblast(self): #cl_sustain_t *

	"""
	vec3_t dir;
	int i;
	cparticle_t *p;
	static int colortable[4] = {110, 112, 114, 116};
	float ratio;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	ratio = 1.0 - ((self.endtime - cl_main.cl.time) / 1000.0)
	time = cl_main.cl.time
	for i in range(700):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = client_h.INSTANT_PARTICLE
		p.color = colortable[rand.randk() & 3]
		dir[0] = rand.crandk()
		dir[1] = rand.crandk()
		dir[2] = rand.crandk()
		shared_c.VectorNormalize(dir)
		shared_c.VectorMA(self.org, (200.0 * ratio), dir, p.org)
#		VectorMA(origin, 10*(((rand () & 0x7fff) / ((float)0x7fff))), dir, p->org);
	

widowsplash_colortable = [2*8,13*8,21*8,18*8] #static int colortable[4]

def CL_WidowSplash(org): #vec3_t

	"""
	static int colortable[4] = {2 * 8, 13 * 8, 21 * 8, 18 * 8};
	int i;
	cparticle_t *p;
	vec3_t dir;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	for i in range(256):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = colortable[rand.randk() & 3]
		dir[0] = rand.crandk()
		dir[1] = rand.crandk()
		dir[2] = rand.crandk()
		shared_c.VectorNormalize(dir)
		shared_c.VectorMA(org, 45.0, dir, p.org)
		shared_c.VectorMA(shared_c.vec3_origin, 40.0, dir, p.vel)
		p.accel[0] = p.accel[1] = 0
		p.alpha = 1.0
		p.alphavel = -0.8 / (0.5 + rand.frandk() * 0.3)
	


def CL_Tracker_Explode(origin): #vec3_t

	"""
	vec3_t dir, backdir;
	int i;
	cparticle_t *p;
	float time;
	"""
	dir = np.zeros((3,), dtype=np.float32)
	backdir = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	for i in range(300):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0
		p.color = 0
		dir[0] = rand.crandk()
		dir[1] = rand.crandk()
		dir[2] = rand.crandk()
		shared_c.VectorNormalize(dir)
		shared_c.VectorScale(dir, -1, backdir)
		shared_c.VectorMA(origin, 64, dir, p.org)
		shared_c.VectorScale(backdir, 64, p.vel)
	

"""
===============
CL_TagTrail

===============
"""
def CL_TagTrail(start, end, color): #vec3_t, vec3_t, int

	"""
	vec3_t move;
	vec3_t vec;
	float len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ >= 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.8 + rand.frandk() * 0.2)
		p.color = color
		for j in range(3):

			p.org[j] = move[j] + rand.crandk() * 16
			p.vel[j] = rand.crandk() * 5
			p.accel[j] = 0


		shared.VectorAdd(move, vec, move)
	

"""
===============
CL_ColorExplosionParticles
===============
"""
def CL_ColorExplosionParticles(org, color, run): #vec3_t, int, int

	"""
	int i;
	int j;
	cparticle_t *p;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(128):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = color + (rand.randk() % run)
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() % 32) - 16)
			p.vel[j] = (rand.randk() % 256) - 128


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -0.4 / (0.6 + rand.frandk() * 0.2)
	

"""
===============
CL_ParticleSmokeEffect - like the steam effect, but unaffected by gravity
===============
"""
def CL_ParticleSmokeEffect(org, dir, color, count, magnitude): #vec3_t, vec3_t, int, int, int

	"""
	int i, j;
	cparticle_t *p;
	float d;
	vec3_t r, u;
	float time;
	"""
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	MakeNormalVectors(dir, r, u)
	for i in range(count):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = color + (rand.randk() & 7)
		for j in range(3):

			p.org[j] = org[j] + magnitude * 0.1 * rand.crandk()


		shared_c.VectorScale(dir, magnitude, p.vel)
		d = rand.crandk() * magnitude / 3
		shared_c.VectorMA(p.vel, d, r, p.vel)
		d = rand.crandk() * magnitude / 3
		shared_c.VectorMA(p.vel, d, u, p.vel)
		p.accel[0] = p.accel[1] = p.accel[2] = 0
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)
	

"""
===============
CL_BlasterParticles2

Wall impact puffs (Green)
===============
"""
def CL_BlasterParticles2(org, dir, color): #vec3_t, vec3_t, unsigned int

	"""
	int i, j;
	cparticle_t *p;
	float d;
	int count;
	float time;
	"""

	time = cl_main.cl.time
	count = 40
	for i in range(count):

		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = color + (rand.randk() & 7)
		d = (rand.randk() & 15)
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() & 7) - 4) + d * dir[j]
			p.vel[j] = dir[j] * 30 + rand.crandk() * 40


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)
	

"""
===============
CL_BlasterTrail2

Green!
===============
"""
def CL_BlasterTrail2(start, end): #vec3_t, vec3_t

	"""
	vec3_t move;
	vec3_t vec;
	float len;
	int j;
	cparticle_t *p;
	int dec;
	float time;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	time = cl_main.cl.time
	shared.VectorCopy(start, move)
	shared.VectorSubtract(end, start, vec)
	len_ = shared_c.VectorNormalize(vec)
	dec = 5
	shared_c.VectorScale(vec, 5, vec)
	while len_ > 0:

		len_ -= dec
		if not cl_particles.free_particles:

			return


		p = cl_particles.free_particles.pop() # p = free_particles; free_particles = p->next;
		cl_particles.active_particles.append(p) # p->next = active_particles; active_particles = p;
		shared.VectorClear(p.accel)
		p.time = time
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.3 + rand.frandk() * 0.2)
		for j in range(3):

			p.org[j] = move[j] + rand.crandk()
			p.vel[j] = rand.crandk() * 5
			p.accel[j] = 0


		shared.VectorAdd(move, vec, move)
