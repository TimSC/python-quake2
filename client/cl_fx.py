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
import numpy as np
import math
import random
from qcommon import common, net_chan, qcommon
from game import q_shared
from client import cl_main, cl_view, ref, snd_dma
"""
// cl_fx.c -- entity effects parsing and management

#include "client.h"

void CL_LogoutEffect (vec3_t org, int type);
void CL_ItemRespawnParticles (vec3_t org);

static vec3_t avelocities [NUMVERTEXNORMALS];

extern	struct model_s	*cl_mod_smoke;
extern	struct model_s	*cl_mod_flash;

/*
==============================================================

LIGHT STYLE MANAGEMENT

==============================================================
*/
"""

class clightstyle_t(object):

	def __init__(self):
		self.length = 0
		self.value = np.ones((3,), dtype=np.float32)
		self.map = np.zeros((q_shared.MAX_QPATH,), dtype=np.float32)


cl_lightstyle = []
for _ in range(ref.MAX_LIGHTSTYLES):
	cl_lightstyle.append(clightstyle_t())
lastofs = -1

# ====================
# CL_ClearLightStyles
# ====================
def CL_ClearLightStyles ():

	global lastofs
	for ls in cl_lightstyle:
		ls.length = 0
		ls.value[:] = 0.0
		ls.map[:] = 0.0
	lastofs = -1

"""
================
CL_RunLightStyles
================
*/
void CL_RunLightStyles (void)
{
	int		ofs;
	int		i;
	clightstyle_t	*ls;

	ofs = cl.time / 100;
	if (ofs == lastofs)
		return;
	lastofs = ofs;

	for (i=0,ls=cl_lightstyle ; i<MAX_LIGHTSTYLES ; i++, ls++)
	{
		if (!ls->length)
		{
			ls->value[0] = ls->value[1] = ls->value[2] = 1.0;
			continue;
		}
		if (ls->length == 1)
			ls->value[0] = ls->value[1] = ls->value[2] = ls->map[0];
		else
			ls->value[0] = ls->value[1] = ls->value[2] = ls->map[ofs%ls->length];
	}
}

"""
def CL_RunLightStyles ():
	global lastofs

	ofs = int(cl_main.cl.time) // 100 # cl.time is int in C, FIXME it becomes float in CL_Frame
	if ofs == lastofs:
		return
	lastofs = ofs

	for ls in cl_lightstyle:
		if not ls.length:
			ls.value[0] = ls.value[1] = ls.value[2] = 1.0
			continue
		if ls.length == 1:
			val = ls.map[0]
		else:
			val = ls.map[ofs % ls.length]
		ls.value[0] = ls.value[1] = ls.value[2] = val


def CL_SetLightstyle (i: int):

	s = cl_main.cl.configstrings[i + q_shared.CS_LIGHTS]
	if s is None:
		return

	j = len(s)
	if j >= q_shared.MAX_QPATH:
		common.Com_Error(q_shared.ERR_DROP, "svc_lightstyle length=%i" % j)

	ls = cl_lightstyle[i]
	ls.length = j
	for k in range(j):
		ls.map[k] = (ord(s[k]) - ord("a")) / float(ord("m") - ord("a"))
	# C implementation omitted.
def CL_AddLightStyles ():
	for i, ls in enumerate(cl_lightstyle):
		cl_view.V_AddLightStyle(i, ls.value[0], ls.value[1], ls.value[2])


class cdlight_t(object):

	def __init__(self):
		self.key = 0
		self.color = np.zeros((3,), dtype=np.float32)
		self.origin = np.zeros((3,), dtype=np.float32)
		self.radius = 0.0
		self.die = 0.0
		self.decay = 0.0
		self.minlight = 0.0

	def clear(self):
		self.key = 0
		self.color[:] = 0.0
		self.origin[:] = 0.0
		self.radius = 0.0
		self.die = 0.0
		self.decay = 0.0
		self.minlight = 0.0


cl_dlights = []
for _ in range(ref.MAX_DLIGHTS):
	cl_dlights.append(cdlight_t())


def CL_ClearDlights ():

	for dl in cl_dlights:
		dl.clear()


"""
===============
CL_AllocDlight

===============
*/
cdlight_t *CL_AllocDlight (int key)
{
	int		i;
	cdlight_t	*dl;

// first look for an exact key match
	if (key)
	{
		dl = cl_dlights;
		for (i=0 ; i<MAX_DLIGHTS ; i++, dl++)
		{
			if (dl->key == key)
			{
				memset (dl, 0, sizeof(*dl));
				dl->key = key;
				return dl;
			}
		}
	}

// then look for anything else
	dl = cl_dlights;
	for (i=0 ; i<MAX_DLIGHTS ; i++, dl++)
	{
		if (dl->die < cl.time)
		{
			memset (dl, 0, sizeof(*dl));
			dl->key = key;
			return dl;
		}
	}

	dl = &cl_dlights[0];
	memset (dl, 0, sizeof(*dl));
	dl->key = key;
	return dl;
}

/*
===============
CL_NewDlight
===============
*/
void CL_NewDlight (int key, float x, float y, float z, float radius, float time)
{
	cdlight_t	*dl;

	dl = CL_AllocDlight (key);
	dl->origin[0] = x;
	dl->origin[1] = y;
	dl->origin[2] = z;
	dl->radius = radius;
	dl->die = cl.time + time;
}


/*
===============
CL_RunDLights

===============
*/
void CL_RunDLights (void)
{
	int			i;
	cdlight_t	*dl;

	dl = cl_dlights;
	for (i=0 ; i<MAX_DLIGHTS ; i++, dl++)
	{
		if (!dl->radius)
			continue;
		
		if (dl->die < cl.time)
		{
			dl->radius = 0;
			return;
		}
		dl->radius -= cls.frametime*dl->decay;
		if (dl->radius < 0)
			dl->radius = 0;
	}
}

/*
==============
CL_ParseMuzzleFlash
==============
"""
def CL_AllocDlight (key):
	# first look for exact key match
	if key:
		for dl in cl_dlights:
			if dl.key == key:
				dl.clear()
				dl.key = key
				return dl

	# then look for an expired one
	for dl in cl_dlights:
		if dl.die < cl_main.cl.time:
			dl.clear()
			dl.key = key
			return dl

	dl = cl_dlights[0]
	dl.clear()
	dl.key = key
	return dl


def CL_NewDlight (key, x, y, z, radius, time):
	dl = CL_AllocDlight(key)
	dl.origin[0] = x
	dl.origin[1] = y
	dl.origin[2] = z
	dl.radius = radius
	dl.die = cl_main.cl.time + time


def CL_RunDLights ():
	for dl in cl_dlights:
		if not dl.radius:
			continue
		if dl.die < cl_main.cl.time:
			dl.radius = 0.0
			continue
		dl.radius -= cl_main.cls.frametime * dl.decay
		if dl.radius < 0:
			dl.radius = 0.0


def CL_AddDLights ():
	for dl in cl_dlights:
		if not dl.radius:
			continue
		cl_view.V_AddLight(dl.origin, dl.radius, dl.color[0], dl.color[1], dl.color[2])

def CL_ParseMuzzleFlash ():
	
	"""
	vec3_t		fv, rv;
	cdlight_t	*dl;
	int			i, weapon;
	centity_t	*pl;
	int			silenced;
	float		volume;
	char		soundname[64];
	"""

	i = common.MSG_ReadShort (net_chan.net_message)
	if i < 1 or i >= q_shared.MAX_EDICTS:
		Com_Error (q_shared.ERR_DROP, "CL_ParseMuzzleFlash: bad entity")

	weapon = common.MSG_ReadByte (net_chan.net_message)
	silenced = weapon & q_shared.MZ_SILENCED
	weapon &= ~q_shared.MZ_SILENCED

	pl = cl_main.cl_entities[i]
	"""
	dl = CL_AllocDlight (i);
	VectorCopy (pl->current.origin,  dl->origin);
	AngleVectors (pl->current.angles, fv, rv, NULL);
	VectorMA (dl->origin, 18, fv, dl->origin);
	VectorMA (dl->origin, 16, rv, dl->origin);
	if (silenced)
		dl->radius = 100 + (rand()&31);
	else
		dl->radius = 200 + (rand()&31);
	dl->minlight = 32;
	dl->die = cl.time; // + 0.1;

	if (silenced)
		volume = 0.2;
	else
		volume = 1;

	switch (weapon)
	{
	case MZ_BLASTER:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/blastf1a.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_BLUEHYPERBLASTER:
		dl->color[0] = 0;dl->color[1] = 0;dl->color[2] = 1;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/hyprbf1a.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_HYPERBLASTER:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/hyprbf1a.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_MACHINEGUN:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0);
		break;
	case MZ_SHOTGUN:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/shotgf1b.wav"), volume, ATTN_NORM, 0);
		S_StartSound (NULL, i, CHAN_AUTO,   S_RegisterSound("weapons/shotgr1b.wav"), volume, ATTN_NORM, 0.1);
		break;
	case MZ_SSHOTGUN:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/sshotf1b.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_CHAINGUN1:
		dl->radius = 200 + (rand()&31);
		dl->color[0] = 1;dl->color[1] = 0.25;dl->color[2] = 0;
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0);
		break;
	case MZ_CHAINGUN2:
		dl->radius = 225 + (rand()&31);
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0;
		dl->die = cl.time  + 0.1;	// long delay
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0);
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0.05);
		break;
	case MZ_CHAINGUN3:
		dl->radius = 250 + (rand()&31);
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		dl->die = cl.time  + 0.1;	// long delay
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0);
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0.033);
		Com_sprintf(soundname, sizeof(soundname), "weapons/machgf%ib.wav", (rand() % 5) + 1);
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound(soundname), volume, ATTN_NORM, 0.066);
		break;
	case MZ_RAILGUN:
		dl->color[0] = 0.5;dl->color[1] = 0.5;dl->color[2] = 1.0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/railgf1a.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_ROCKET:
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0.2;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/rocklf1a.wav"), volume, ATTN_NORM, 0);
		S_StartSound (NULL, i, CHAN_AUTO,   S_RegisterSound("weapons/rocklr1b.wav"), volume, ATTN_NORM, 0.1);
		break;
	case MZ_GRENADE:
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/grenlf1a.wav"), volume, ATTN_NORM, 0);
		S_StartSound (NULL, i, CHAN_AUTO,   S_RegisterSound("weapons/grenlr1b.wav"), volume, ATTN_NORM, 0.1);
		break;
	case MZ_BFG:
		dl->color[0] = 0;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/bfg__f1y.wav"), volume, ATTN_NORM, 0);
		break;

	case MZ_LOGIN:
		dl->color[0] = 0;dl->color[1] = 1; dl->color[2] = 0;
		dl->die = cl.time + 1.0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/grenlf1a.wav"), 1, ATTN_NORM, 0);
		CL_LogoutEffect (pl->current.origin, weapon);
		break;
	case MZ_LOGOUT:
		dl->color[0] = 1;dl->color[1] = 0; dl->color[2] = 0;
		dl->die = cl.time + 1.0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/grenlf1a.wav"), 1, ATTN_NORM, 0);
		CL_LogoutEffect (pl->current.origin, weapon);
		break;
	case MZ_RESPAWN:
		dl->color[0] = 1;dl->color[1] = 1; dl->color[2] = 0;
		dl->die = cl.time + 1.0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/grenlf1a.wav"), 1, ATTN_NORM, 0);
		CL_LogoutEffect (pl->current.origin, weapon);
		break;
	// RAFAEL
	case MZ_PHALANX:
		dl->color[0] = 1;dl->color[1] = 0.5; dl->color[2] = 0.5;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/plasshot.wav"), volume, ATTN_NORM, 0);
		break;
	// RAFAEL
	case MZ_IONRIPPER:	
		dl->color[0] = 1;dl->color[1] = 0.5; dl->color[2] = 0.5;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/rippfire.wav"), volume, ATTN_NORM, 0);
		break;

// ======================
// PGM
	case MZ_ETF_RIFLE:
		dl->color[0] = 0.9;dl->color[1] = 0.7;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/nail1.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_SHOTGUN2:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/shotg2.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_HEATBEAM:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		dl->die = cl.time + 100;
//		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/bfg__l1a.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_BLASTER2:
		dl->color[0] = 0;dl->color[1] = 1;dl->color[2] = 0;
		// FIXME - different sound for blaster2 ??
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/blastf1a.wav"), volume, ATTN_NORM, 0);
		break;
	case MZ_TRACKER:
		// negative flashes handled the same in gl/soft until CL_AddDLights
		dl->color[0] = -1;dl->color[1] = -1;dl->color[2] = -1;
		S_StartSound (NULL, i, CHAN_WEAPON, S_RegisterSound("weapons/disint2.wav"), volume, ATTN_NORM, 0);
		break;		
	case MZ_NUKE1:
		dl->color[0] = 1;dl->color[1] = 0;dl->color[2] = 0;
		dl->die = cl.time + 100;
		break;
	case MZ_NUKE2:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		dl->die = cl.time + 100;
		break;
	case MZ_NUKE4:
		dl->color[0] = 0;dl->color[1] = 0;dl->color[2] = 1;
		dl->die = cl.time + 100;
		break;
	case MZ_NUKE8:
		dl->color[0] = 0;dl->color[1] = 1;dl->color[2] = 1;
		dl->die = cl.time + 100;
		break;
// PGM
// ======================
	}
}


/*
==============
CL_ParseMuzzleFlash2
==============
"""
def CL_ParseMuzzleFlash2 ():

	print ("CL_ParseMuzzleFlash2")

	ent = common.MSG_ReadShort (net_chan.net_message)
	if ent < 1 or ent >= q_shared.MAX_EDICTS:
		common.Com_Error (q_shared.ERR_DROP, "CL_ParseMuzzleFlash2: bad entity")

	flash_number = common.MSG_ReadByte (net_chan.net_message)

	"""
	// locate the origin
	AngleVectors (cl_main.cl_entities[ent].current.angles, forward, right, NULL);
	origin[0] = cl_main.cl_entities[ent].current.origin[0] + forward[0] * monster_flash_offset[flash_number][0] + right[0] * monster_flash_offset[flash_number][1];
	origin[1] = cl_main.cl_entities[ent].current.origin[1] + forward[1] * monster_flash_offset[flash_number][0] + right[1] * monster_flash_offset[flash_number][1];
	origin[2] = cl_main.cl_entities[ent].current.origin[2] + forward[2] * monster_flash_offset[flash_number][0] + right[2] * monster_flash_offset[flash_number][1] + monster_flash_offset[flash_number][2];

	dl = CL_AllocDlight (ent);
	VectorCopy (origin,  dl->origin);
	dl->radius = 200 + (rand()&31);
	dl->minlight = 32;
	dl->die = cl.time;	// + 0.1;

	switch (flash_number)
	{
	case MZ2_INFANTRY_MACHINEGUN_1:
	case MZ2_INFANTRY_MACHINEGUN_2:
	case MZ2_INFANTRY_MACHINEGUN_3:
	case MZ2_INFANTRY_MACHINEGUN_4:
	case MZ2_INFANTRY_MACHINEGUN_5:
	case MZ2_INFANTRY_MACHINEGUN_6:
	case MZ2_INFANTRY_MACHINEGUN_7:
	case MZ2_INFANTRY_MACHINEGUN_8:
	case MZ2_INFANTRY_MACHINEGUN_9:
	case MZ2_INFANTRY_MACHINEGUN_10:
	case MZ2_INFANTRY_MACHINEGUN_11:
	case MZ2_INFANTRY_MACHINEGUN_12:
	case MZ2_INFANTRY_MACHINEGUN_13:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("infantry/infatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_SOLDIER_MACHINEGUN_1:
	case MZ2_SOLDIER_MACHINEGUN_2:
	case MZ2_SOLDIER_MACHINEGUN_3:
	case MZ2_SOLDIER_MACHINEGUN_4:
	case MZ2_SOLDIER_MACHINEGUN_5:
	case MZ2_SOLDIER_MACHINEGUN_6:
	case MZ2_SOLDIER_MACHINEGUN_7:
	case MZ2_SOLDIER_MACHINEGUN_8:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("soldier/solatck3.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_GUNNER_MACHINEGUN_1:
	case MZ2_GUNNER_MACHINEGUN_2:
	case MZ2_GUNNER_MACHINEGUN_3:
	case MZ2_GUNNER_MACHINEGUN_4:
	case MZ2_GUNNER_MACHINEGUN_5:
	case MZ2_GUNNER_MACHINEGUN_6:
	case MZ2_GUNNER_MACHINEGUN_7:
	case MZ2_GUNNER_MACHINEGUN_8:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("gunner/gunatck2.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_ACTOR_MACHINEGUN_1:
	case MZ2_SUPERTANK_MACHINEGUN_1:
	case MZ2_SUPERTANK_MACHINEGUN_2:
	case MZ2_SUPERTANK_MACHINEGUN_3:
	case MZ2_SUPERTANK_MACHINEGUN_4:
	case MZ2_SUPERTANK_MACHINEGUN_5:
	case MZ2_SUPERTANK_MACHINEGUN_6:
	case MZ2_TURRET_MACHINEGUN:			// PGM
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;

		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("infantry/infatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_BOSS2_MACHINEGUN_L1:
	case MZ2_BOSS2_MACHINEGUN_L2:
	case MZ2_BOSS2_MACHINEGUN_L3:
	case MZ2_BOSS2_MACHINEGUN_L4:
	case MZ2_BOSS2_MACHINEGUN_L5:
	case MZ2_CARRIER_MACHINEGUN_L1:		// PMM
	case MZ2_CARRIER_MACHINEGUN_L2:		// PMM
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;

		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("infantry/infatck1.wav"), 1, ATTN_NONE, 0);
		break;

	case MZ2_SOLDIER_BLASTER_1:
	case MZ2_SOLDIER_BLASTER_2:
	case MZ2_SOLDIER_BLASTER_3:
	case MZ2_SOLDIER_BLASTER_4:
	case MZ2_SOLDIER_BLASTER_5:
	case MZ2_SOLDIER_BLASTER_6:
	case MZ2_SOLDIER_BLASTER_7:
	case MZ2_SOLDIER_BLASTER_8:
	case MZ2_TURRET_BLASTER:			// PGM
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("soldier/solatck2.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_FLYER_BLASTER_1:
	case MZ2_FLYER_BLASTER_2:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("flyer/flyatck3.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_MEDIC_BLASTER_1:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("medic/medatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_HOVER_BLASTER_1:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("hover/hovatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_FLOAT_BLASTER_1:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("floater/fltatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_SOLDIER_SHOTGUN_1:
	case MZ2_SOLDIER_SHOTGUN_2:
	case MZ2_SOLDIER_SHOTGUN_3:
	case MZ2_SOLDIER_SHOTGUN_4:
	case MZ2_SOLDIER_SHOTGUN_5:
	case MZ2_SOLDIER_SHOTGUN_6:
	case MZ2_SOLDIER_SHOTGUN_7:
	case MZ2_SOLDIER_SHOTGUN_8:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("soldier/solatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_TANK_BLASTER_1:
	case MZ2_TANK_BLASTER_2:
	case MZ2_TANK_BLASTER_3:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("tank/tnkatck3.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_TANK_MACHINEGUN_1:
	case MZ2_TANK_MACHINEGUN_2:
	case MZ2_TANK_MACHINEGUN_3:
	case MZ2_TANK_MACHINEGUN_4:
	case MZ2_TANK_MACHINEGUN_5:
	case MZ2_TANK_MACHINEGUN_6:
	case MZ2_TANK_MACHINEGUN_7:
	case MZ2_TANK_MACHINEGUN_8:
	case MZ2_TANK_MACHINEGUN_9:
	case MZ2_TANK_MACHINEGUN_10:
	case MZ2_TANK_MACHINEGUN_11:
	case MZ2_TANK_MACHINEGUN_12:
	case MZ2_TANK_MACHINEGUN_13:
	case MZ2_TANK_MACHINEGUN_14:
	case MZ2_TANK_MACHINEGUN_15:
	case MZ2_TANK_MACHINEGUN_16:
	case MZ2_TANK_MACHINEGUN_17:
	case MZ2_TANK_MACHINEGUN_18:
	case MZ2_TANK_MACHINEGUN_19:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		Com_sprintf(soundname, sizeof(soundname), "tank/tnkatk2%c.wav", 'a' + rand() % 5);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound(soundname), 1, ATTN_NORM, 0);
		break;

	case MZ2_CHICK_ROCKET_1:
	case MZ2_TURRET_ROCKET:			// PGM
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0.2;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("chick/chkatck2.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_TANK_ROCKET_1:
	case MZ2_TANK_ROCKET_2:
	case MZ2_TANK_ROCKET_3:
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0.2;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("tank/tnkatck1.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_SUPERTANK_ROCKET_1:
	case MZ2_SUPERTANK_ROCKET_2:
	case MZ2_SUPERTANK_ROCKET_3:
	case MZ2_BOSS2_ROCKET_1:
	case MZ2_BOSS2_ROCKET_2:
	case MZ2_BOSS2_ROCKET_3:
	case MZ2_BOSS2_ROCKET_4:
	case MZ2_CARRIER_ROCKET_1:
//	case MZ2_CARRIER_ROCKET_2:
//	case MZ2_CARRIER_ROCKET_3:
//	case MZ2_CARRIER_ROCKET_4:
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0.2;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("tank/rocket.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_GUNNER_GRENADE_1:
	case MZ2_GUNNER_GRENADE_2:
	case MZ2_GUNNER_GRENADE_3:
	case MZ2_GUNNER_GRENADE_4:
		dl->color[0] = 1;dl->color[1] = 0.5;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("gunner/gunatck3.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_GLADIATOR_RAILGUN_1:
	// PMM
	case MZ2_CARRIER_RAILGUN:
	case MZ2_WIDOW_RAIL:
	// pmm
		dl->color[0] = 0.5;dl->color[1] = 0.5;dl->color[2] = 1.0;
		break;

// --- Xian's shit starts ---
	case MZ2_MAKRON_BFG:
		dl->color[0] = 0.5;dl->color[1] = 1 ;dl->color[2] = 0.5;
		//S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("makron/bfg_fire.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_MAKRON_BLASTER_1:
	case MZ2_MAKRON_BLASTER_2:
	case MZ2_MAKRON_BLASTER_3:
	case MZ2_MAKRON_BLASTER_4:
	case MZ2_MAKRON_BLASTER_5:
	case MZ2_MAKRON_BLASTER_6:
	case MZ2_MAKRON_BLASTER_7:
	case MZ2_MAKRON_BLASTER_8:
	case MZ2_MAKRON_BLASTER_9:
	case MZ2_MAKRON_BLASTER_10:
	case MZ2_MAKRON_BLASTER_11:
	case MZ2_MAKRON_BLASTER_12:
	case MZ2_MAKRON_BLASTER_13:
	case MZ2_MAKRON_BLASTER_14:
	case MZ2_MAKRON_BLASTER_15:
	case MZ2_MAKRON_BLASTER_16:
	case MZ2_MAKRON_BLASTER_17:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("makron/blaster.wav"), 1, ATTN_NORM, 0);
		break;
	
	case MZ2_JORG_MACHINEGUN_L1:
	case MZ2_JORG_MACHINEGUN_L2:
	case MZ2_JORG_MACHINEGUN_L3:
	case MZ2_JORG_MACHINEGUN_L4:
	case MZ2_JORG_MACHINEGUN_L5:
	case MZ2_JORG_MACHINEGUN_L6:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("boss3/xfire.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_JORG_MACHINEGUN_R1:
	case MZ2_JORG_MACHINEGUN_R2:
	case MZ2_JORG_MACHINEGUN_R3:
	case MZ2_JORG_MACHINEGUN_R4:
	case MZ2_JORG_MACHINEGUN_R5:
	case MZ2_JORG_MACHINEGUN_R6:
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		break;

	case MZ2_JORG_BFG_1:
		dl->color[0] = 0.5;dl->color[1] = 1 ;dl->color[2] = 0.5;
		break;

	case MZ2_BOSS2_MACHINEGUN_R1:
	case MZ2_BOSS2_MACHINEGUN_R2:
	case MZ2_BOSS2_MACHINEGUN_R3:
	case MZ2_BOSS2_MACHINEGUN_R4:
	case MZ2_BOSS2_MACHINEGUN_R5:
	case MZ2_CARRIER_MACHINEGUN_R1:			// PMM
	case MZ2_CARRIER_MACHINEGUN_R2:			// PMM

		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;

		CL_ParticleEffect (origin, vec3_origin, 0, 40);
		CL_SmokeAndFlash(origin);
		break;

// ======
// ROGUE
	case MZ2_STALKER_BLASTER:
	case MZ2_DAEDALUS_BLASTER:
	case MZ2_MEDIC_BLASTER_2:
	case MZ2_WIDOW_BLASTER:
	case MZ2_WIDOW_BLASTER_SWEEP1:
	case MZ2_WIDOW_BLASTER_SWEEP2:
	case MZ2_WIDOW_BLASTER_SWEEP3:
	case MZ2_WIDOW_BLASTER_SWEEP4:
	case MZ2_WIDOW_BLASTER_SWEEP5:
	case MZ2_WIDOW_BLASTER_SWEEP6:
	case MZ2_WIDOW_BLASTER_SWEEP7:
	case MZ2_WIDOW_BLASTER_SWEEP8:
	case MZ2_WIDOW_BLASTER_SWEEP9:
	case MZ2_WIDOW_BLASTER_100:
	case MZ2_WIDOW_BLASTER_90:
	case MZ2_WIDOW_BLASTER_80:
	case MZ2_WIDOW_BLASTER_70:
	case MZ2_WIDOW_BLASTER_60:
	case MZ2_WIDOW_BLASTER_50:
	case MZ2_WIDOW_BLASTER_40:
	case MZ2_WIDOW_BLASTER_30:
	case MZ2_WIDOW_BLASTER_20:
	case MZ2_WIDOW_BLASTER_10:
	case MZ2_WIDOW_BLASTER_0:
	case MZ2_WIDOW_BLASTER_10L:
	case MZ2_WIDOW_BLASTER_20L:
	case MZ2_WIDOW_BLASTER_30L:
	case MZ2_WIDOW_BLASTER_40L:
	case MZ2_WIDOW_BLASTER_50L:
	case MZ2_WIDOW_BLASTER_60L:
	case MZ2_WIDOW_BLASTER_70L:
	case MZ2_WIDOW_RUN_1:
	case MZ2_WIDOW_RUN_2:
	case MZ2_WIDOW_RUN_3:
	case MZ2_WIDOW_RUN_4:
	case MZ2_WIDOW_RUN_5:
	case MZ2_WIDOW_RUN_6:
	case MZ2_WIDOW_RUN_7:
	case MZ2_WIDOW_RUN_8:
		dl->color[0] = 0;dl->color[1] = 1;dl->color[2] = 0;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("tank/tnkatck3.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_WIDOW_DISRUPTOR:
		dl->color[0] = -1;dl->color[1] = -1;dl->color[2] = -1;
		S_StartSound (NULL, ent, CHAN_WEAPON, S_RegisterSound("weapons/disint2.wav"), 1, ATTN_NORM, 0);
		break;

	case MZ2_WIDOW_PLASMABEAM:
	case MZ2_WIDOW2_BEAMER_1:
	case MZ2_WIDOW2_BEAMER_2:
	case MZ2_WIDOW2_BEAMER_3:
	case MZ2_WIDOW2_BEAMER_4:
	case MZ2_WIDOW2_BEAMER_5:
	case MZ2_WIDOW2_BEAM_SWEEP_1:
	case MZ2_WIDOW2_BEAM_SWEEP_2:
	case MZ2_WIDOW2_BEAM_SWEEP_3:
	case MZ2_WIDOW2_BEAM_SWEEP_4:
	case MZ2_WIDOW2_BEAM_SWEEP_5:
	case MZ2_WIDOW2_BEAM_SWEEP_6:
	case MZ2_WIDOW2_BEAM_SWEEP_7:
	case MZ2_WIDOW2_BEAM_SWEEP_8:
	case MZ2_WIDOW2_BEAM_SWEEP_9:
	case MZ2_WIDOW2_BEAM_SWEEP_10:
	case MZ2_WIDOW2_BEAM_SWEEP_11:
		dl->radius = 300 + (rand()&100);
		dl->color[0] = 1;dl->color[1] = 1;dl->color[2] = 0;
		dl->die = cl.time + 200;
		break;
// ROGUE
// ======

// --- Xian's shit ends ---

	}
}


/*
===============
CL_AddDLights

===============
*/
void CL_AddDLights (void)
{
	int			i;
	cdlight_t	*dl;

	dl = cl_dlights;

//=====
//PGM
	if(vidref_val == VIDREF_GL)
	{
		for (i=0 ; i<MAX_DLIGHTS ; i++, dl++)
		{
			if (!dl->radius)
				continue;
			V_AddLight (dl->origin, dl->radius,
				dl->color[0], dl->color[1], dl->color[2]);
		}
	}
	else
	{
		for (i=0 ; i<MAX_DLIGHTS ; i++, dl++)
		{
			if (!dl->radius)
				continue;

			// negative light in software. only black allowed
			if ((dl->color[0] < 0) || (dl->color[1] < 0) || (dl->color[2] < 0))
			{
				dl->radius = -(dl->radius);
				dl->color[0] = 1;
				dl->color[1] = 1;
				dl->color[2] = 1;
			}
			V_AddLight (dl->origin, dl->radius,
				dl->color[0], dl->color[1], dl->color[2]);
		}
	}
//PGM
//=====
}



/*
==============================================================

PARTICLE MANAGEMENT

==============================================================
*/

/*
// THIS HAS BEEN RELOCATED TO CLIENT.H
typedef struct particle_s
{
	struct particle_s	*next;

	float		time;

	vec3_t		org;
	vec3_t		vel;
	vec3_t		accel;
	float		color;
	float		colorvel;
	float		alpha;
	float		alphavel;
} cparticle_t;


#define	PARTICLE_GRAVITY	40
*/

cparticle_t	*active_particles, *free_particles;

cparticle_t	particles[MAX_PARTICLES];
int			cl_numparticles = MAX_PARTICLES;


/*
===============
CL_ClearParticles
===============
"""
class cparticle_t(object):

	def __init__(self):
		self.time = 0.0
		self.org = np.zeros((3,), dtype=np.float32)
		self.vel = np.zeros((3,), dtype=np.float32)
		self.accel = np.zeros((3,), dtype=np.float32)
		self.color = 0
		self.colorvel = 0.0
		self.alpha = 0.0
		self.alphavel = 0.0


PARTICLE_GRAVITY = 40.0
INSTANT_PARTICLE = 10000.0

cl_numparticles = ref.MAX_PARTICLES
particles = []
for _ in range(cl_numparticles):
	particles.append(cparticle_t())
active_particles = []
free_particles = particles[:]


def _alloc_particle():
	if not free_particles:
		return None
	return free_particles.pop()


def _free_particle(p):
	free_particles.append(p)


def CL_ClearParticles ():

	active_particles.clear()
	free_particles.clear()
	free_particles.extend(particles)
	"""
	int		i;
	
	free_particles = &particles[0];
	active_particles = NULL;

	for (i=0 ;i<cl_numparticles ; i++)
		particles[i].next = &particles[i+1];
	particles[cl_numparticles-1].next = NULL;
	"""


"""
===============
CL_ParticleEffect

Wall impact puffs
===============
"""
def CL_ParticleEffect (org, dirIn, color, count): #vec3_t org, vec3_t dir, int color, int count

	for _ in range(count):
		p = _alloc_particle()
		if p is None:
			return
		p.time = cl_main.cl.time
		p.color = color + (random.randint(0, 7))
		d = random.randint(0, 31)
		for j in range(3):
			p.org[j] = org[j] + (random.randint(0, 7) - 4) + d * dirIn[j]
			p.vel[j] = (random.random() * 2.0 - 1.0) * 20.0
		p.accel[0] = 0.0
		p.accel[1] = 0.0
		p.accel[2] = -PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + random.random() * 0.3)
		active_particles.append(p)


def CL_ExplosionParticles (org):

	for _ in range(256):
		p = _alloc_particle()
		if p is None:
			return
		p.time = cl_main.cl.time
		p.color = 0xe0 + random.randint(0, 7)

		for j in range(3):
			p.org[j] = org[j] + random.randint(0, 31) - 16
			p.vel[j] = random.randint(0, 383) - 192

		p.accel[0] = p.accel[1] = 0.0
		p.accel[2] = -PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -0.8 / (0.5 + random.random() * 0.3)
		active_particles.append(p)
def CL_BigTeleportParticles(org):
	color_table = [2 * 8, 13 * 8, 21 * 8, 18 * 8]
	for _ in range(4096):
		p = _alloc_particle()
		if p is None:
			return
		p.time = cl_main.cl.time
		p.color = color_table[random.randint(0, 3)]

		angle = math.pi * 2.0 * random.randint(0, 1023) / 1023.0
		dist = random.randint(0, 31)
		cos_a = math.cos(angle)
		sin_a = math.sin(angle)

		p.org[0] = org[0] + cos_a * dist
		p.vel[0] = cos_a * (70 + random.randint(0, 63))
		p.accel[0] = -cos_a * 100.0

		p.org[1] = org[1] + sin_a * dist
		p.vel[1] = sin_a * (70 + random.randint(0, 63))
		p.accel[1] = -sin_a * 100.0

		p.org[2] = org[2] + 8 + random.randint(0, 89)
		p.vel[2] = -100 + random.randint(0, 31)
		p.accel[2] = PARTICLE_GRAVITY * 4.0
		p.alpha = 1.0
		p.alphavel = -0.3 / (0.5 + random.random() * 0.3)
		active_particles.append(p)

# ===============
# CL_BlasterParticles
#
# Wall impact puffs
# ===============
def CL_BlasterParticles (org, readdir): # vec3_t, vec3_t

	dirIn = readdir
	for _ in range(40):
		p = _alloc_particle()
		if p is None:
			return
		p.time = cl_main.cl.time
		p.color = 0xE0 + random.randint(0, 7)

		d = random.randint(0, 15)
		for j in range(3):
			p.org[j] = org[j] + (random.randint(0, 7) - 4) + d * dirIn[j]
			p.vel[j] = dirIn[j] * 30.0 + (random.random() * 2.0 - 1.0) * 40.0

		p.accel[0] = 0.0
		p.accel[1] = 0.0
		p.accel[2] = -PARTICLE_GRAVITY
		p.alpha = 1.0
	p.alphavel = -1.0 / (0.5 + random.random() * 0.3)
	active_particles.append(p)
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
CL_TeleporterParticles
===============
"""
def CL_TeleporterParticles (ent): #entity_state_t *

	#int			i, j;
	#cparticle_t	*p;

	for i in range(8):
	
		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = 0xdb

		for j in range(2):
		
			p.org[j] = ent.origin[j] - 16 + (random.getrandbits(15)&31)
			p.vel[j] = common.crand()*14
		
		p.org[2] = ent.origin[2] - 8 + (random.getrandbits(15)&7)
		p.vel[2] = 80 + (random.getrandbits(15)&7)

		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -PARTICLE_GRAVITY
		p.alpha = 1.0

		p.alphavel = -0.5
	

"""
===============
CL_BlasterTrail

===============
"""
def CL_BlasterTrail (start, end): #vec3_t, vec3_t

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	int			dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 5
	q_shared.VectorScale (vec, 5, vec)

	# FIXME: this is a really silly way to have a loop
	while length > 0:
	
		length -= dec

		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (0.3+common.frand()*0.2)
		p.color = 0xe0
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()
			p.vel[j] = common.crand()*5
			p.accel[j] = 0
		
		q_shared.VectorAdd (move, vec, move)
	

"""
===============
CL_DiminishingTrail

===============
"""
def CL_DiminishingTrail (start, end, old, flags): #vec3_t, vec3_t, centity_t *, int

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	float		dec;
	float		orgscale;
	float		velscale;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 0.5
	q_shared.VectorScale (vec, dec, vec)

	if old.trailcount > 900:
	
		orgscale = 4
		velscale = 15
	
	elif old.trailcount > 800:
	
		orgscale = 2
		velscale = 10
	
	else:
	
		orgscale = 1
		velscale = 5
	
	while length > 0:
	
		length -= dec

		if not free_particles:
			return

		# drop less particles as it flies
		if (random.getrandbits(15)&1023) < old.trailcount:
		
			p = _alloc_particle()
			active_particles.append(p)
			q_shared.VectorClear (p.accel)
		
			p.time = cl_main.cl.time

			if flags & q_shared.EF_GIB:
			
				p.alpha = 1.0
				p.alphavel = -1.0 / (1+common.frand()*0.4)
				p.color = 0xe8 + (random.getrandbits(15)&7)
				for j in range(3):
				
					p.org[j] = move[j] + common.crand()*orgscale
					p.vel[j] = common.crand()*velscale
					p.accel[j] = 0
				
				p.vel[2] -= PARTICLE_GRAVITY
			
			elif flags & q_shared.EF_GREENGIB:
			
				p.alpha = 1.0
				p.alphavel = -1.0 / (1+common.frand()*0.4)
				p.color = 0xdb + (random.getrandbits(15)&7)
				for j in range(3):
				
					p.org[j] = move[j] + common.crand()*orgscale
					p.vel[j] = common.crand()*velscale
					p.accel[j] = 0
				
				p.vel[2] -= PARTICLE_GRAVITY
			
			else:
			
				p.alpha = 1.0
				p.alphavel = -1.0 / (1+common.frand()*0.2)
				p.color = 4 + (random.getrandbits(15)&7)
				for j in range(3):
				
					p.org[j] = move[j] + common.crand()*orgscale
					p.vel[j] = common.crand()*velscale
				
				p.accel[2] = 20
			
		old.trailcount -= 5
		if old.trailcount < 100:
			old.trailcount = 100
		q_shared.VectorAdd (move, vec, move)
	

def MakeNormalVectors (forward, right, up): #vec3_t, vec3_t, vec3_t

	#float		d;

	# this rotate and negat guarantees a vector
	# not colinear with the original
	right[1] = -forward[0]
	right[2] = forward[1]
	right[0] = forward[2]

	d = q_shared.DotProduct (right, forward)
	q_shared.VectorMA (right, -d, forward, right)
	q_shared.VectorNormalize (right)
	q_shared.CrossProduct (right, forward, up)


"""
===============
CL_RocketTrail

===============
"""
def CL_RocketTrail (start, end, old): #vec3_t, vec3_t, centity_t *

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	float		dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	# smoke
	CL_DiminishingTrail (start, end, old, q_shared.EF_ROCKET)

	# fire
	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 1
	q_shared.VectorScale (vec, dec, vec)

	while length > 0:
	
		length -= dec

		if not free_particles:
			return

		if (random.getrandbits(15)&7) == 0:
		
			p = _alloc_particle()
			active_particles.append(p)
			
			q_shared.VectorClear (p.accel)
			p.time = cl_main.cl.time

			p.alpha = 1.0
			p.alphavel = -1.0 / (1+common.frand()*0.2)
			p.color = 0xdc + (random.getrandbits(15)&3)
			for j in range(3):
			
				p.org[j] = move[j] + common.crand()*5
				p.vel[j] = common.crand()*20
			
			p.accel[2] = -PARTICLE_GRAVITY
		
		q_shared.VectorAdd (move, vec, move)
	

"""
===============
CL_RailTrail

===============
"""
def CL_RailTrail (start, end): #vec3_t, vec3_t

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
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	clr = 0x74

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	MakeNormalVectors (vec, right, up)

	i = 0
	while i < length:
	
		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)
		
		p.time = cl_main.cl.time
		q_shared.VectorClear (p.accel)

		d = i * 0.1
		c = math.cos(d)
		s = math.sin(d)

		q_shared.VectorScale (right, c, dir)
		q_shared.VectorMA (dir, s, up, dir)

		p.alpha = 1.0
		p.alphavel = -1.0 / (1+common.frand()*0.2)
		p.color = clr + (random.getrandbits(15)&7)
		for j in range(3):
		
			p.org[j] = move[j] + dir[j]*3
			p.vel[j] = dir[j]*6
		
		q_shared.VectorAdd (move, vec, move)
		i += 1
	
	dec = 0.75
	q_shared.VectorScale (vec, dec, vec)
	q_shared.VectorCopy (start, move)

	while length > 0:
	
		length -= dec

		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)

		p.time = cl_main.cl.time
		q_shared.VectorClear (p.accel)

		p.alpha = 1.0
		p.alphavel = -1.0 / (0.6+common.frand()*0.2)
		p.color = (0x0 + random.getrandbits(15))&15 # 0x0 + rand()&15

		for j in range(3):
		
			p.org[j] = move[j] + common.crand()*3
			p.vel[j] = common.crand()*3
			p.accel[j] = 0
		
		q_shared.VectorAdd (move, vec, move)
	

# RAFAEL
"""
===============
CL_IonripperTrail
===============
"""
def CL_IonripperTrail (start, ent): #vec3_t, vec3_t

	"""
	vec3_t	move;
	vec3_t	vec;
	float	len;
	int		j;
	cparticle_t *p;
	int		dec;
	int     left = 0;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	left = 0

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (ent, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 5
	q_shared.VectorScale (vec, 5, vec)

	while length > 0:
	
		length -= dec

		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)
		q_shared.VectorClear (p.accel)

		p.time = cl_main.cl.time
		p.alpha = 0.5
		p.alphavel = -1.0 / (0.3 + common.frand() * 0.2)
		p.color = 0xe4 + (random.getrandbits(15)&3)

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

		q_shared.VectorAdd (move, vec, move)
	

"""
===============
CL_BubbleTrail

===============
"""
def CL_BubbleTrail (start, end): #vec3_t, vec3_t

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			i, j;
	cparticle_t	*p;
	float		dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 32
	q_shared.VectorScale (vec, dec, vec)

	i = 0
	while i < length:
	
		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)

		q_shared.VectorClear (p.accel)
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (1+common.frand()*0.2)
		p.color = 4 + (random.getrandbits(15)&7)
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()*2
			p.vel[j] = common.crand()*5
		
		p.vel[2] += 6

		q_shared.VectorAdd (move, vec, move)
		i += dec
	


"""
===============
CL_FlyParticles
===============
"""
BEAMLENGTH = 16

avelocities = np.zeros((qcommon.NUMVERTEXNORMALS, 3), dtype=np.float32) #static vec3_t [NUMVERTEXNORMALS]

def CL_FlyParticles (origin, count): #vec3_t, int

	"""
	int			i;
	cparticle_t	*p;
	float		angle;
	float		sr, sp, sy, cr, cp, cy;
	vec3_t		forward;
	float		dist = 64;
	float		ltime;
	"""
	forward = np.zeros((3,), dtype=np.float32)

	if count > qcommon.NUMVERTEXNORMALS:
		count = qcommon.NUMVERTEXNORMALS

	if not avelocities[0][0]:
		for i in range(qcommon.NUMVERTEXNORMALS*3):
			avelocities.flat[i] = (random.randint(0, 255)) * 0.01

	ltime = float(cl_main.cl.time) / 1000.0
	for i in range(0, count, 2):

		angle = ltime * avelocities[i][0]
		sy = math.sin(angle)
		cy = math.cos(angle)
		angle = ltime * avelocities[i][1]
		sp = math.sin(angle)
		cp = math.cos(angle)
		angle = ltime * avelocities[i][2]
		sr = math.sin(angle)
		cr = math.cos(angle)

		forward[0] = cp*cy
		forward[1] = cp*sy
		forward[2] = -sp

		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)

		p.time = cl_main.cl.time

		dist = math.sin(ltime + i)*64
		p.org[0] = origin[0] + common.bytedirs[i][0]*dist + forward[0]*BEAMLENGTH
		p.org[1] = origin[1] + common.bytedirs[i][1]*dist + forward[1]*BEAMLENGTH
		p.org[2] = origin[2] + common.bytedirs[i][2]*dist + forward[2]*BEAMLENGTH

		q_shared.VectorClear (p.vel)
		q_shared.VectorClear (p.accel)

		p.color = 0
		p.colorvel = 0

		p.alpha = 1
		p.alphavel = -100


def CL_FlyEffect (ent, origin): #centity_t *, vec3_t

	#int		n;
	#int		count;
	#int		starttime;

	if ent.fly_stoptime < cl_main.cl.time:

		starttime = cl_main.cl.time
		ent.fly_stoptime = cl_main.cl.time + 60000

	else:

		starttime = ent.fly_stoptime - 60000

	n = cl_main.cl.time - starttime
	if n < 20000:
		count = int(n * 162 / 20000.0)
	else:

		n = ent.fly_stoptime - cl_main.cl.time
		if n < 20000:
			count = int(n * 162 / 20000.0)
		else:
			count = 162

	CL_FlyParticles (origin, count)


"""
===============
CL_BfgParticles
===============
"""
def CL_BfgParticles (ent): #entity_t *

	"""
	int			i;
	cparticle_t	*p;
	float		angle;
	float		sr, sp, sy, cr, cp, cy;
	vec3_t		forward;
	float		dist = 64;
	vec3_t		v;
	float		ltime;
	"""
	forward = np.zeros((3,), dtype=np.float32)
	v = np.zeros((3,), dtype=np.float32)
	
	if not avelocities[0][0]:
	
		for i in range(qcommon.NUMVERTEXNORMALS*3):
			avelocities.flat[i] = (random.getrandbits(15)&255) * 0.01
	
	ltime = float(cl_main.cl.time) / 1000.0
	for i in range(qcommon.NUMVERTEXNORMALS):
	
		angle = ltime * avelocities[i][0]
		sy = math.sin(angle)
		cy = math.cos(angle)
		angle = ltime * avelocities[i][1]
		sp = math.sin(angle)
		cp = math.cos(angle)
		angle = ltime * avelocities[i][2]
		sr = math.sin(angle)
		cr = math.cos(angle)
	
		forward[0] = cp*cy
		forward[1] = cp*sy
		forward[2] = -sp

		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)

		p.time = cl_main.cl.time

		dist = math.sin(ltime + i)*64
		p.org[0] = ent.origin[0] + common.bytedirs[i][0]*dist + forward[0]*BEAMLENGTH
		p.org[1] = ent.origin[1] + common.bytedirs[i][1]*dist + forward[1]*BEAMLENGTH
		p.org[2] = ent.origin[2] + common.bytedirs[i][2]*dist + forward[2]*BEAMLENGTH

		q_shared.VectorClear (p.vel)
		q_shared.VectorClear (p.accel)

		q_shared.VectorSubtract (p.org, ent.origin, v)
		dist = q_shared.VectorLength(v) / 90.0
		p.color = math.floor (0xd0 + dist * 7)
		p.colorvel = 0

		p.alpha = 1.0 - dist
		p.alphavel = -100
	


"""
===============
CL_TrapParticles
===============
"""
# RAFAEL
def CL_TrapParticles (ent): #entity_t *

	"""
	vec3_t		move;
	vec3_t		vec;
	vec3_t		start, end;
	float		len;
	int			j;
	cparticle_t	*p;
	int			dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	ent.origin[2]-=14
	q_shared.VectorCopy (ent.origin, start)
	q_shared.VectorCopy (ent.origin, end)
	end[2]+=64

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 5
	q_shared.VectorScale (vec, 5, vec)

	# FIXME: this is a really silly way to have a loop
	while length > 0:
	
		length -= dec

		p = _alloc_particle()
		if p is None:
			return
		active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (0.3+common.frand()*0.2)
		p.color = 0xe0
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()
			p.vel[j] = common.crand()*15
			p.accel[j] = 0
		
		p.accel[2] = PARTICLE_GRAVITY

		q_shared.VectorAdd (move, vec, move)
	
	"""
	int			i, j, k;
	cparticle_t	*p;
	float		vel;
	vec3_t		dir;
	vec3_t		org;
	"""
	dir = np.zeros((3,), dtype=np.float32)
	org = np.zeros((3,), dtype=np.float32)

	ent.origin[2]+=14
	q_shared.VectorCopy (ent.origin, org)

	for i in range(-2, 3, 4):
		for j in range(-2, 3, 4):
			for k in range(-2, 5, 4):
			
				p = _alloc_particle()
				if p is None:
					return
				active_particles.append(p)

				p.time = cl_main.cl.time
				p.color = 0xe0 + (random.getrandbits(15)&3)

				p.alpha = 1.0
				p.alphavel = -1.0 / (0.3 + (random.getrandbits(15)&7) * 0.02)
				
				p.org[0] = org[0] + i + ((random.getrandbits(15)&23) * common.crand())
				p.org[1] = org[1] + j + ((random.getrandbits(15)&23) * common.crand())
				p.org[2] = org[2] + k + ((random.getrandbits(15)&23) * common.crand())
	
				dir[0] = j * 8
				dir[1] = i * 8
				dir[2] = k * 8
	
				q_shared.VectorNormalize (dir)
				vel = (50 + random.getrandbits(15))&63 # 50 + rand()&63
				q_shared.VectorScale (dir, vel, p.vel)

				p.accel[0] = p.accel[1] = 0
				p.accel[2] = -PARTICLE_GRAVITY
			

def CL_AddParticles ():
	active = []
	for p in list(active_particles):
		if p.alphavel == INSTANT_PARTICLE:
			alpha = p.alpha
			time = 0.0
		else:
			time = (cl_main.cl.time - p.time) * 0.001
			alpha = p.alpha + time * p.alphavel
		if alpha <= 0:
			active_particles.remove(p)
			_free_particle(p)
			continue

		if alpha > 1.0:
			alpha = 1.0

		time2 = time * time
		org = np.zeros((3,), dtype=np.float32)
		org[0] = p.org[0] + p.vel[0] * time + p.accel[0] * time2
		org[1] = p.org[1] + p.vel[1] * time + p.accel[1] * time2
		org[2] = p.org[2] + p.vel[2] * time + p.accel[2] * time2

		cl_view.V_AddParticle(org, p.color, alpha)
		if p.alphavel == INSTANT_PARTICLE:
			p.alphavel = 0.0
			p.alpha = 0.0
		active.append(p)

	active_particles[:] = active


"""
/*
==============
CL_EntityEvent

An entity has just been parsed that has an event value

the female events are there for backwards compatability
==============
*/
extern struct sfx_s	*cl_sfx_footsteps[4];

void CL_EntityEvent (entity_state_t *ent)
{
	switch (ent->event)
	{
	case EV_ITEM_RESPAWN:
		S_StartSound (NULL, ent->number, CHAN_WEAPON, S_RegisterSound("items/respawn1.wav"), 1, ATTN_IDLE, 0);
		CL_ItemRespawnParticles (ent->origin);
		break;
	case EV_PLAYER_TELEPORT:
		S_StartSound (NULL, ent->number, CHAN_WEAPON, S_RegisterSound("misc/tele1.wav"), 1, ATTN_IDLE, 0);
		CL_TeleportParticles (ent->origin);
		break;
	case EV_FOOTSTEP:
		if (cl_footsteps->value)
			S_StartSound (NULL, ent->number, CHAN_BODY, cl_sfx_footsteps[rand()&3], 1, ATTN_NORM, 0);
		break;
	case EV_FALLSHORT:
		S_StartSound (NULL, ent->number, CHAN_AUTO, S_RegisterSound ("player/land1.wav"), 1, ATTN_NORM, 0);
		break;
	case EV_FALL:
		S_StartSound (NULL, ent->number, CHAN_AUTO, S_RegisterSound ("*fall2.wav"), 1, ATTN_NORM, 0);
		break;
	case EV_FALLFAR:
		S_StartSound (NULL, ent->number, CHAN_AUTO, S_RegisterSound ("*fall1.wav"), 1, ATTN_NORM, 0);
		break;
	}
}

"""
def CL_EntityEvent(ent):
	if ent.event == q_shared.EV_ITEM_RESPAWN:
		snd_dma.S_StartSound(
			None,
			ent.number,
			q_shared.CHAN_WEAPON,
			snd_dma.S_RegisterSound("items/respawn1.wav"),
			1,
			q_shared.ATTN_IDLE,
			0,
		)
		CL_ItemRespawnParticles(ent.origin)
		return

	if ent.event == q_shared.EV_PLAYER_TELEPORT:
		snd_dma.S_StartSound(
			None,
			ent.number,
			q_shared.CHAN_WEAPON,
			snd_dma.S_RegisterSound("misc/tele1.wav"),
			1,
			q_shared.ATTN_IDLE,
			0,
		)
		CL_TeleportParticles(ent.origin)
		return

	if ent.event == q_shared.EV_FOOTSTEP:
		if cl_main.cl_footsteps and cl_main.cl_footsteps.value:
			from client import cl_tent
			sfx = cl_tent.cl_sfx_footsteps[random.randint(0, 3)]
			if sfx is not None:
				snd_dma.S_StartSound(
					None,
					ent.number,
					q_shared.CHAN_BODY,
					sfx,
					1,
					q_shared.ATTN_NORM,
					0,
				)
		return

	if ent.event == q_shared.EV_FALLSHORT:
		snd_dma.S_StartSound(
			None,
			ent.number,
			q_shared.CHAN_AUTO,
			snd_dma.S_RegisterSound("player/land1.wav"),
			1,
			q_shared.ATTN_NORM,
			0,
		)
		return

	if ent.event == q_shared.EV_FALL:
		snd_dma.S_StartSound(
			None,
			ent.number,
			q_shared.CHAN_AUTO,
			snd_dma.S_RegisterSound("*fall2.wav"),
			1,
			q_shared.ATTN_NORM,
			0,
		)
		return

	if ent.event == q_shared.EV_FALLFAR:
		snd_dma.S_StartSound(
			None,
			ent.number,
			q_shared.CHAN_AUTO,
			snd_dma.S_RegisterSound("*fall1.wav"),
			1,
			q_shared.ATTN_NORM,
			0,
		)
		return


def CL_ParticleEffect2 (org, dirIn, color, count):
	for _ in range(count):
		p = _alloc_particle()
		if p is None:
			return
		p.time = cl_main.cl.time
		p.color = color
		d = random.randint(0, 7)
		for j in range(3):
			p.org[j] = org[j] + (random.randint(0, 7) - 4) + d * dirIn[j]
			p.vel[j] = (random.random() * 2.0 - 1.0) * 20.0
		p.accel[0] = 0.0
		p.accel[1] = 0.0
		p.accel[2] = -PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + random.random() * 0.3)
		active_particles.append(p)


def CL_ParticleEffect3 (org, dirIn, color, count):
	for _ in range(count):
		p = _alloc_particle()
		if p is None:
			return
		p.time = cl_main.cl.time
		p.color = color
		d = random.randint(0, 7)
		for j in range(3):
			p.org[j] = org[j] + (random.randint(0, 7) - 4) + d * dirIn[j]
			p.vel[j] = (random.random() * 2.0 - 1.0) * 20.0
		p.accel[0] = 0.0
		p.accel[1] = 0.0
		p.accel[2] = PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + random.random() * 0.3)
		active_particles.append(p)


# ==============
# CL_ClearEffects
# ==============
def CL_ClearEffects ():

	CL_ClearParticles ()
	CL_ClearDlights ()
	CL_ClearLightStyles ()
