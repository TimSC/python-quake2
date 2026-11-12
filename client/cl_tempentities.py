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

This file implements all temporary (dynamic created) entities

=======================================================================
"""
from __future__ import annotations

from common.shared import rand
from client.vid import vid

import math
import random
import numpy as np
from enum import Enum
from client import ref, cl_main, cl_view
from client.sound import sound as sound_c
from client.vid import vid
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import frame
from common import movemsg
from common import netchan
from client import cl_main
from client import cl_view
from client.header import client as client_h
from client import cl_effects
from client import cl_particles

"""
#include "header/client.h"
#include "sound/header/local.h"
"""

class exptype_t(Enum):

	ex_free = 0
	ex_explosion = 1
	ex_misc = 2
	ex_flash = 3
	ex_mflash = 4
	ex_poly = 5
	ex_poly2 = 6

class explosion_t(object):

	def __init__(self):

		self.clear()

	def clear(self): # Q2PORT: memset(ex, 0, sizeof(*ex))

		self.type = exptype_t.ex_free #exptype_t
		self.ent = ref.entity_t() #entity_t
		self.frames = 0 #int
		self.light = 0.0 #float
		self.lightcolor = np.zeros((3,), dtype=np.float32) #vec3_t
		self.start = 0.0 #float
		self.baseframe = 0 #int

MAX_EXPLOSIONS	= 64
MAX_BEAMS	= 64
MAX_LASERS	= 64

cl_explosions = [] #static explosion_t[MAX_EXPLOSIONS]
for i in range(MAX_EXPLOSIONS):
	cl_explosions.append(explosion_t())

class beam_t(object):

	def __init__(self):

		self.clear()

	def clear(self): # Q2PORT: memset(b, 0, sizeof(*b))

		self.entity = 0 #int
		self.dest_entity = 0 #int
		self.model = None #struct model_s *
		self.endtime = 0 #int
		self.offset = np.zeros((3,), dtype=np.float32) #vec3_t
		self.start = np.zeros((3,), dtype=np.float32) #vec3_t
		self.end = np.zeros((3,), dtype=np.float32) #vec3_t

cl_beams = [beam_t() for i in range(MAX_BEAMS)] #static beam_t[MAX_BEAMS]
cl_heatbeams = [beam_t() for i in range(MAX_BEAMS)] #static beam_t[MAX_BEAMS]

class laser_t(object):

	def __init__(self):

		self.clear()

	def clear(self): # Q2PORT: memset(l, 0, sizeof(*l))

		self.ent = ref.entity_t() #entity_t
		self.endtime = 0 #int

cl_lasers = [laser_t() for i in range(MAX_LASERS)] #static laser_t[MAX_LASERS]
cl_sustains = [client_h.cl_sustain_t() for i in range(client_h.MAX_SUSTAINS)] #static cl_sustain_t[MAX_SUSTAINS]

"""
extern void CL_TeleportParticles(vec3_t org);
void CL_BlasterParticles(vec3_t org, vec3_t dir);
void CL_BFGExplosionParticles(vec3_t org);
void CL_BlueBlasterParticles(vec3_t org, vec3_t dir);
void CL_ExplosionParticles(vec3_t org);
void CL_Explosion_Particle(vec3_t org, float size,
		qboolean large, qboolean rocket);

extern cvar_t *hand;
"""

def EXPLOSION_PARTICLES(x): cl_effects.CL_ExplosionParticles((x)) #define EXPLOSION_PARTICLES(x)

NUM_FOOTSTEP_SFX	= 4

# sounds
cl_sfx_ric1 = None #static struct sfx_s *
cl_sfx_ric2 = None #static struct sfx_s *
cl_sfx_ric3 = None #static struct sfx_s *
cl_sfx_lashit = None #static struct sfx_s *
cl_sfx_spark5 = None #static struct sfx_s *
cl_sfx_spark6 = None #static struct sfx_s *
cl_sfx_spark7 = None #static struct sfx_s *
cl_sfx_railg = None #static struct sfx_s *
cl_sfx_rockexp = None #static struct sfx_s *
cl_sfx_grenexp = None #static struct sfx_s *
cl_sfx_watrexp = None #static struct sfx_s *
cl_sfx_footsteps = [None] * NUM_FOOTSTEP_SFX #static struct sfx_s *[NUM_FOOTSTEP_SFX]
cl_sfx_lightning = None #static struct sfx_s *
cl_sfx_disrexp = None #static struct sfx_s *

# models
cl_mod_explode = None #static struct model_s *
cl_mod_smoke = None #static struct model_s *
cl_mod_flash = None #static struct model_s *
cl_mod_parasite_segment = None #static struct model_s *
cl_mod_grapple_cable = None #static struct model_s *
cl_mod_parasite_tip = None #static struct model_s *
cl_mod_explo4 = None #static struct model_s *
cl_mod_bfg_explo = None #static struct model_s *
cl_mod_powerscreen = None #static struct model_s *
cl_mod_plasmaexplo = None #static struct model_s *
cl_mod_lightning = None #static struct model_s *
cl_mod_heatbeam = None #static struct model_s *
cl_mod_explo4_big = None #static struct model_s *

"""
 * Utility functions
"""
def CL_Beams_NextFree(list_: list): #const beam_t * (returns static beam_t *)

	"""
	const beam_t *b;
	"""

	for b in list_[:MAX_BEAMS]: # for (b = list; b < &list[MAX_BEAMS]; b++)

		if not b.model or (b.endtime < cl_main.cl.time):
			return b # (beam_t *)b


	return None

def CL_Beams_SameEnt(list_: list, src: int, dest: int): #const beam_t *, int, int (returns static beam_t *)

	"""
	const beam_t *b;
	"""

	for b in list_[:MAX_BEAMS]: # for (b = list; b < &list[MAX_BEAMS]; b++)

		if ((src < 0 or b.entity == src) and
			(dest < 0 or b.dest_entity == dest)):

			return b # (beam_t *)b



	return None


def CL_Beams_Set(b, src, dest, model, start, end, ofs, tm): #beam_t *, int, int, struct model_s *, const vec3_t, const vec3_t, const vec3_t, int (static)

	b.entity = src
	b.dest_entity = dest
	b.model = model
	shared.VectorCopy(start, b.start)
	shared.VectorCopy(end, b.end)
	if ofs is not None: # if (ofs), a pointer test

		shared.VectorCopy(ofs, b.offset)

	else:

		shared.VectorClear(b.offset)


	b.endtime = cl_main.cl.time + tm

def CL_NextFreeSustain(): # (returns static cl_sustain_t *)

	"""
	cl_sustain_t *s;
	"""

	for s in cl_sustains[:client_h.MAX_SUSTAINS]: # for (s = cl_sustains; s < &cl_sustains[MAX_SUSTAINS]; s++)

		if s.id == 0:

			return s


	return None

"""
=================
CL_AllocExplosion
=================
"""
def CL_AllocExplosion(): # (returns static explosion_t *)

	"""
	int i;
	float time;
	int index;
	"""

	for i in range(MAX_EXPLOSIONS):

		if cl_explosions[i].type == exptype_t.ex_free:

			cl_explosions[i].clear() # memset(&cl_explosions[i], 0, sizeof(cl_explosions[i]));
			return cl_explosions[i]


	# find the oldest explosion
	time = cl_main.cl.time
	index = 0
	for i in range(MAX_EXPLOSIONS):

		if cl_explosions[i].start < time:

			time = cl_explosions[i].start
			index = i


	cl_explosions[index].clear() # memset(&cl_explosions[index], 0, sizeof(cl_explosions[index]));
	return cl_explosions[index]

"""
// cl_tent.c -- client side temporary entities

#include "client.h"
"""
"""
=================
CL_RegisterTEntSounds
=================
"""
def CL_RegisterTEntSounds(): #

	global cl_sfx_disrexp, cl_sfx_grenexp, cl_sfx_lashit, cl_sfx_lightning, cl_sfx_railg, cl_sfx_ric1, cl_sfx_ric2, cl_sfx_ric3, cl_sfx_rockexp, cl_sfx_spark5, cl_sfx_spark6, cl_sfx_spark7, cl_sfx_watrexp

	"""
	int i;
	char name[MAX_QPATH];
	"""
	name = [None] * shared.MAX_QPATH

	cl_sfx_ric1 = sound_c.S_RegisterSound("world/ric1.wav")
	cl_sfx_ric2 = sound_c.S_RegisterSound("world/ric2.wav")
	cl_sfx_ric3 = sound_c.S_RegisterSound("world/ric3.wav")
	cl_sfx_lashit = sound_c.S_RegisterSound("weapons/lashit.wav")
	cl_sfx_spark5 = sound_c.S_RegisterSound("world/spark5.wav")
	cl_sfx_spark6 = sound_c.S_RegisterSound("world/spark6.wav")
	cl_sfx_spark7 = sound_c.S_RegisterSound("world/spark7.wav")
	cl_sfx_railg = sound_c.S_RegisterSound("weapons/railgf1a.wav")
	cl_sfx_rockexp = sound_c.S_RegisterSound("weapons/rocklx1a.wav")
	cl_sfx_grenexp = sound_c.S_RegisterSound("weapons/grenlx1a.wav")
	cl_sfx_watrexp = sound_c.S_RegisterSound("weapons/xpld_wat.wav")
	sound_c.S_RegisterSound("player/land1.wav")
	sound_c.S_RegisterSound("player/fall2.wav")
	sound_c.S_RegisterSound("player/fall1.wav")
	for i in range(NUM_FOOTSTEP_SFX):

		name = "player/step%i.wav" % (i + 1,) # Com_sprintf
		cl_sfx_footsteps[i] = sound_c.S_RegisterSound(name)


	cl_sfx_lightning = sound_c.S_RegisterSound("weapons/tesla.wav")
	cl_sfx_disrexp = sound_c.S_RegisterSound("weapons/disrupthit.wav")
	# version stuff
#	sprintf (name, "weapons/sound%d.wav", ROGUE_VERSION_ID);
#	if (name[0] == 'w')
#		name[0] = 'W';
#PGM
	

"""
=================
CL_RegisterTEntModels
=================
"""
def CL_RegisterTEntModels(): #

	global cl_mod_bfg_explo, cl_mod_explo4, cl_mod_explo4_big, cl_mod_explode, cl_mod_flash, cl_mod_grapple_cable, cl_mod_heatbeam, cl_mod_lightning, cl_mod_parasite_segment, cl_mod_parasite_tip, cl_mod_powerscreen, cl_mod_smoke

	cl_mod_explode = vid.R_RegisterModel("models/objects/explode/tris.md2")
	cl_mod_smoke = vid.R_RegisterModel("models/objects/smoke/tris.md2")
	cl_mod_flash = vid.R_RegisterModel("models/objects/flash/tris.md2")
	cl_mod_parasite_segment = vid.R_RegisterModel("models/monsters/parasite/segment/tris.md2")
	cl_mod_grapple_cable = vid.R_RegisterModel("models/ctf/segment/tris.md2")
	cl_mod_parasite_tip = vid.R_RegisterModel("models/monsters/parasite/tip/tris.md2")
	cl_mod_explo4 = vid.R_RegisterModel("models/objects/r_explode/tris.md2")
	cl_mod_bfg_explo = vid.R_RegisterModel("sprites/s_bfg2.sp2")
	cl_mod_powerscreen = vid.R_RegisterModel("models/items/armor/effect/tris.md2")
	vid.R_RegisterModel("models/objects/laser/tris.md2")
	vid.R_RegisterModel("models/objects/grenade2/tris.md2")
	vid.R_RegisterModel("models/weapons/v_machn/tris.md2")
	vid.R_RegisterModel("models/weapons/v_handgr/tris.md2")
	vid.R_RegisterModel("models/weapons/v_shotg2/tris.md2")
	vid.R_RegisterModel("models/objects/gibs/bone/tris.md2")
	vid.R_RegisterModel("models/objects/gibs/sm_meat/tris.md2")
	vid.R_RegisterModel("models/objects/gibs/bone2/tris.md2")
	vid.Draw_FindPic("w_machinegun")
	vid.Draw_FindPic("a_bullets")
	vid.Draw_FindPic("i_health")
	vid.Draw_FindPic("a_grenades")
	cl_mod_explo4_big = vid.R_RegisterModel("models/objects/r_explode2/tris.md2")
	cl_mod_lightning = vid.R_RegisterModel("models/proj/lightning/tris.md2")
	cl_mod_heatbeam = vid.R_RegisterModel("models/proj/beam/tris.md2")
#ROGUE
	

"""
 * Clear temp entity state

"""
def CL_ClearTEntSoundVars(): # (static)

	global cl_sfx_disrexp, cl_sfx_grenexp, cl_sfx_lashit, cl_sfx_lightning, cl_sfx_railg, cl_sfx_ric1, cl_sfx_ric2, cl_sfx_ric3, cl_sfx_rockexp, cl_sfx_spark5, cl_sfx_spark6, cl_sfx_spark7, cl_sfx_watrexp

	"""
	int i;
	"""

	cl_sfx_ric1 = None
	cl_sfx_ric2 = None
	cl_sfx_ric3 = None
	cl_sfx_lashit = None
	cl_sfx_spark5 = None
	cl_sfx_spark6 = None
	cl_sfx_spark7 = None
	cl_sfx_railg = None
	cl_sfx_rockexp = None
	cl_sfx_grenexp = None
	cl_sfx_watrexp = None
	for i in range(NUM_FOOTSTEP_SFX):

		cl_sfx_footsteps[i] = None


	cl_sfx_lightning = None
	cl_sfx_disrexp = None

def CL_ClearTEntModelVars(): # (static)

	global cl_mod_bfg_explo, cl_mod_explo4, cl_mod_explo4_big, cl_mod_explode, cl_mod_flash, cl_mod_grapple_cable, cl_mod_heatbeam, cl_mod_lightning, cl_mod_parasite_segment, cl_mod_parasite_tip, cl_mod_plasmaexplo, cl_mod_powerscreen, cl_mod_smoke

	cl_mod_explode = None
	cl_mod_smoke = None
	cl_mod_flash = None
	cl_mod_parasite_segment = None
	cl_mod_grapple_cable = None
	cl_mod_parasite_tip = None
	cl_mod_explo4 = None
	cl_mod_bfg_explo = None
	cl_mod_powerscreen = None
	cl_mod_plasmaexplo = None
	cl_mod_lightning = None
	cl_mod_heatbeam = None
	cl_mod_explo4_big = None

"""
=================
CL_ClearTEnts
=================
"""
def CL_ClearTEnts(): #

	for x in cl_beams: x.clear() # memset(cl_beams, 0, sizeof(cl_beams));
	for x in cl_explosions: x.clear() # memset(cl_explosions, 0, sizeof(cl_explosions));
	for x in cl_lasers: x.clear() # memset(cl_lasers, 0, sizeof(cl_lasers));
	for x in cl_heatbeams: x.clear() # memset(cl_heatbeams, 0, sizeof(cl_heatbeams));
	for x in cl_sustains: x.clear() # memset(cl_sustains, 0, sizeof(cl_sustains));
	CL_ClearTEntModelVars()
	CL_ClearTEntSoundVars()
#ROGUE

def CL_ClearTEntModels(): #

	for x in cl_explosions: x.clear() # memset(cl_explosions, 0, sizeof(cl_explosions));
	for x in cl_beams: x.clear() # memset(cl_beams, 0, sizeof(cl_beams));
	for x in cl_heatbeams: x.clear() # memset(cl_heatbeams, 0, sizeof(cl_heatbeams));
	CL_ClearTEntModelVars()

"""
=================
CL_SmokeAndFlash
=================
"""
def CL_SmokeAndFlash(origin): #vec3_t

	"""
	explosion_t *ex;
	"""

	ex = CL_AllocExplosion()
	shared.VectorCopy(origin, ex.ent.origin)
	ex.type = exptype_t.ex_misc
	ex.frames = 4
	ex.ent.flags = shared.RF_TRANSLUCENT
	ex.start = cl_main.cl.frame.servertime - 100.0
	ex.ent.model = cl_mod_smoke
	ex = CL_AllocExplosion()
	shared.VectorCopy(origin, ex.ent.origin)
	ex.type = exptype_t.ex_flash
	ex.ent.flags = shared.RF_FULLBRIGHT
	ex.frames = 2
	ex.start = cl_main.cl.frame.servertime - 100.0
	ex.ent.model = cl_mod_flash

"""
=================
CL_ParseParticles
=================
"""
def CL_ParseParticles(): #

	"""
	int color, count;
	vec3_t pos, dir;
	"""
	pos = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	movemsg.MSG_ReadPos(netchan.net_message, pos)
	movemsg.MSG_ReadDir(netchan.net_message, dir)
	color = movemsg.MSG_ReadByte(netchan.net_message)
	count = movemsg.MSG_ReadByte(netchan.net_message)
	cl_particles.CL_ParticleEffect(pos, dir, color, count)

"""
=================
CL_ParseBeam
=================
"""
def CL_ParseBeam(model, with_offset): #struct model_s *, qboolean (static)

	"""
	int ent;
	vec3_t start, end, ofs;
	beam_t *b;
	"""
	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)
	ofs = np.zeros((3,), dtype=np.float32)

	ent = movemsg.MSG_ReadShort(netchan.net_message)
	movemsg.MSG_ReadPos(netchan.net_message, start)
	movemsg.MSG_ReadPos(netchan.net_message, end)
	if with_offset:

		movemsg.MSG_ReadPos(netchan.net_message, ofs)

	else:

		shared.VectorClear(ofs)


	if not model:

		return


	# override any beam with the same entity
	b = CL_Beams_SameEnt(cl_beams, ent, -1)
	if not b:

		b = CL_Beams_NextFree(cl_beams)
		if not b:

			clientserver.Com_Printf("beam list overflow!\n")
			return


	CL_Beams_Set(b, ent, 0, model, start, end, ofs, 200)


# ROGUE

#rogue

"""
 * adds to the cl_playerbeam array instead of the cl_beams array

"""
plofs = np.array([2, 7, -3], dtype=np.float32) #static const vec3_t, in CL_ParseHeatBeam

def CL_ParseHeatBeam(is_monster): #qboolean (static)

	"""
	static const vec3_t plofs = {2, 7, -3};
	const vec_t *ofs;
	int ent;
	vec3_t start, end;
	beam_t *b;
	int tm;
	"""
	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	ent = movemsg.MSG_ReadShort(netchan.net_message)
	movemsg.MSG_ReadPos(netchan.net_message, start)
	movemsg.MSG_ReadPos(netchan.net_message, end)
	if not cl_mod_heatbeam:

		return


	ofs = (plofs if (not is_monster) else shared_c.vec3_origin)
	tm = 200
	# Override any beam with the same entity
	# For player beams, we only want one per
	# player (entity) so...
	b = CL_Beams_SameEnt(cl_heatbeams, ent, -1)
	if not b:

		b = CL_Beams_NextFree(cl_heatbeams)
		if not b:

			clientserver.Com_Printf("beam list overflow!\n")
			return


		# this needs to be 100 to
		# prevent multiple heatbeams
		tm = 100


	CL_Beams_Set(b, ent, 0, cl_mod_heatbeam, start, end, ofs, tm)

"""
=================
CL_ParseLightning
=================
"""
def CL_ParseLightning(model): #struct model_s * (returns static unsigned)

	"""
	int srcEnt, destEnt;
	vec3_t start, end;
	beam_t *b;
	"""
	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	srcEnt = movemsg.MSG_ReadShort(netchan.net_message)
	if srcEnt < 0:

		clientserver.Com_Error(common_h.ERR_DROP, "%s: unexpected message end", "CL_ParseLightning")
		return 0


	destEnt = movemsg.MSG_ReadShort(netchan.net_message)
	if destEnt < 0:

		clientserver.Com_Error(common_h.ERR_DROP, "%s: unexpected message end", "CL_ParseLightning")
		return 0


	movemsg.MSG_ReadPos(netchan.net_message, start)
	movemsg.MSG_ReadPos(netchan.net_message, end)
	if not model:

		return srcEnt


	# override any beam with the same
	# source AND destination entities
	b = CL_Beams_SameEnt(cl_beams, srcEnt, destEnt)
	if not b:

		b = CL_Beams_NextFree(cl_beams)
		if not b:

			clientserver.Com_Printf("beam list overflow!\n")
			return srcEnt


	CL_Beams_Set(b, srcEnt, destEnt, model, start, end, None, 200)
	return srcEnt

"""
=================
CL_ParseLaser
=================
"""
def CL_ParseLaser(colors: int): #int (static)

	"""
	vec3_t start;
	vec3_t end;
	laser_t *l;
	int i;
	"""
	start = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)

	movemsg.MSG_ReadPos(netchan.net_message, start)
	movemsg.MSG_ReadPos(netchan.net_message, end)

	for i in range(MAX_LASERS):

		l = cl_lasers[i]
		if l.endtime < cl_main.cl.time:

			alpha = cl_main.cl_laseralpha.value
			if alpha < 0.0:

				alpha = 0.0

			elif alpha > 1.0:

				alpha = 1.0


			l.ent.flags = shared.RF_TRANSLUCENT | shared.RF_BEAM
			shared.VectorCopy(start, l.ent.origin)
			shared.VectorCopy(end, l.ent.oldorigin)
			l.ent.alpha = alpha
			l.ent.skinnum = (colors >> ((rand.randk() % 4) * 8)) & 0xff
			l.ent.model = None
			l.ent.frame = 4
			l.endtime = cl_main.cl.time + 100
			return

		

#=============
#ROGUE
def CL_ParseSteam(): # (static)

	"""
	vec3_t pos, dir;
	int id;
	int r;
	int cnt;
	int color;
	int magnitude;
	cl_sustain_t *s, dummy;
	"""
	pos = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	id_ = movemsg.MSG_ReadShort(netchan.net_message)
	# an id of -1 is an instant effect
	if id_ == -1:

		# instant
		# instant
		cnt = movemsg.MSG_ReadByte(netchan.net_message)
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		r = movemsg.MSG_ReadByte(netchan.net_message)
		magnitude = movemsg.MSG_ReadShort(netchan.net_message)
		color = r & 0xff
		cl_effects.CL_ParticleSteamEffect(pos, dir, color, cnt, magnitude)
		return


	s = CL_NextFreeSustain()
	if not s:

		s = client_h.cl_sustain_t() # s = &dummy;


	s.id = id_
	s.count = movemsg.MSG_ReadByte(netchan.net_message)
	movemsg.MSG_ReadPos(netchan.net_message, s.org)
	movemsg.MSG_ReadDir(netchan.net_message, s.dir)
	r = movemsg.MSG_ReadByte(netchan.net_message)
	s.color = r & 0xff
	s.magnitude = movemsg.MSG_ReadShort(netchan.net_message)
	s.endtime = cl_main.cl.time + movemsg.MSG_ReadLong(netchan.net_message)
	s.think = cl_effects.CL_ParticleSteamEffect2
	s.thinkinterval = 100
	s.nextthink = cl_main.cl.time
#		S_StartSound (pos,  0, 0, cl_sfx_lashit, 1, ATTN_NORM, 0);
	

def CL_ParseWidow(): # (static)

	"""
	int id;
	cl_sustain_t *s, dummy;
	"""

	id_ = movemsg.MSG_ReadShort(netchan.net_message)
	s = CL_NextFreeSustain()
	if not s:

		s = client_h.cl_sustain_t() # s = &dummy;


	s.id = id_
	movemsg.MSG_ReadPos(netchan.net_message, s.org)
	s.endtime = cl_main.cl.time + 2100
	s.think = cl_effects.CL_Widowbeamout
	s.thinkinterval = 1
	s.nextthink = cl_main.cl.time
	

def CL_ParseNuke(): # (static)

	"""
	cl_sustain_t *s, dummy;
	"""

	s = CL_NextFreeSustain()
	if not s:

		s = client_h.cl_sustain_t() # s = &dummy;


	s.id = 21000
	movemsg.MSG_ReadPos(netchan.net_message, s.org)
	s.endtime = cl_main.cl.time + 1000
	s.think = cl_effects.CL_Nukeblast
	s.thinkinterval = 1
	s.nextthink = cl_main.cl.time
	

#ROGUE
#=============


"""
=================
CL_ParseTEnt
=================
"""
splash_color = [0x00, 0xe0, 0xb0, 0x50, 0xd0, 0xe0, 0xe8] #static byte[]

def CL_ParseTEnt(): #

	"""
	int type;
	vec3_t pos, pos2, dir;
	explosion_t *ex;
	int cnt;
	int color;
	int r;
	int ent;
	int magnitude;
	"""
	pos = np.zeros((3,), dtype=np.float32)
	pos2 = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	type_ = movemsg.MSG_ReadByte(netchan.net_message)
	if type_ == shared.temp_event_t.TE_BLOOD.value:

		# bullet hitting flesh
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		cl_particles.CL_ParticleEffect(pos, dir, 0xe8, 60)

	elif type_ == shared.temp_event_t.TE_GUNSHOT.value or type_ == shared.temp_event_t.TE_SPARKS.value or type_ == shared.temp_event_t.TE_BULLET_SPARKS.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		if type_ == shared.temp_event_t.TE_GUNSHOT.value:

			cl_particles.CL_ParticleEffect(pos, dir, 0, 40)

		else:

			cl_particles.CL_ParticleEffect(pos, dir, 0xe0, 6)


		if type_ != shared.temp_event_t.TE_SPARKS.value:

			CL_SmokeAndFlash(pos)
			# impact sound
			if rand.randk() & 15 == 1:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_ric1, 1, shared.ATTN_NORM, 0)

			elif rand.randk() & 15 == 2:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_ric2, 1, shared.ATTN_NORM, 0)

			elif rand.randk() & 15 == 3:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_ric3, 1, shared.ATTN_NORM, 0)


	elif type_ == shared.temp_event_t.TE_SCREEN_SPARKS.value or type_ == shared.temp_event_t.TE_SHIELD_SPARKS.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		if type_ == shared.temp_event_t.TE_SCREEN_SPARKS.value:

			cl_particles.CL_ParticleEffect(pos, dir, 0xd0, 40)

		else:

			cl_particles.CL_ParticleEffect(pos, dir, 0xb0, 40)


		if cl_main.cl_limitsparksounds.value:

			cl_main.num_power_sounds += 1
			# If too many of these sounds are started in one frame
			# (for example if the player shoots with the super
			# shotgun into the power screen of a Brain) things get
			# too loud and OpenAL is forced to scale the volume of
			# several other sounds and the background music down.
			# That leads to a noticable and annoying drop in the
			# overall volume.
			# Work around that by limiting the number of sounds
			# started.
			# 16 was choosen by empirical testing.
			# This was fixed in openal-soft 0.19.0. We're keeping
			# the work around hidden behind a cvar and no longer
			# limited to OpenAL because a) some Linux distros may
			# still ship older openal-soft versions and b) some
			# player may like the changed behavior.
			if cl_main.num_power_sounds < 16:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)


		else:

			sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)


	elif type_ == shared.temp_event_t.TE_SHOTGUN.value:

		# bullet hitting wall
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		cl_particles.CL_ParticleEffect(pos, dir, 0, 20)
		CL_SmokeAndFlash(pos)

	elif type_ == shared.temp_event_t.TE_SPLASH.value:

		# bullet hitting water
		cnt = movemsg.MSG_ReadByte(netchan.net_message)
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		r = movemsg.MSG_ReadByte(netchan.net_message)
		if r > 6 or r < 0:

			color = 0x00

		else:

			color = splash_color[r]


		cl_particles.CL_ParticleEffect(pos, dir, color, cnt)
		if r == shared.SPLASH_SPARKS:

			if rand.randk() & 3 == 0:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_spark5, 1, shared.ATTN_STATIC, 0)

			elif rand.randk() & 3 == 1:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_spark6, 1, shared.ATTN_STATIC, 0)

			else:

				sound_c.S_StartSound(pos, 0, 0, cl_sfx_spark7, 1, shared.ATTN_STATIC, 0)


	elif type_ == shared.temp_event_t.TE_LASER_SPARKS.value:

		cnt = movemsg.MSG_ReadByte(netchan.net_message)
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		color = movemsg.MSG_ReadByte(netchan.net_message)
		cl_particles.CL_ParticleEffect2(pos, dir, color, cnt)

	elif type_ == shared.temp_event_t.TE_BLUEHYPERBLASTER.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadPos(netchan.net_message, dir)
		cl_effects.CL_BlasterParticles(pos, dir)

	elif type_ == shared.temp_event_t.TE_BLASTER.value:

		# blaster hitting wall
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		cl_effects.CL_BlasterParticles(pos, dir)
		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.ent.angles[0] = math.acos(dir[2]) / math.pi * 180
		if dir[0]:

			ex.ent.angles[1] = math.atan2(dir[1], dir[0]) / math.pi * 180

		elif dir[1] > 0:

			ex.ent.angles[1] = 90

		elif dir[1] < 0:

			ex.ent.angles[1] = 270

		else:

			ex.ent.angles[1] = 0


		ex.type = exptype_t.ex_misc
		ex.ent.flags = 0
		ex.start = cl_main.cl.frame.servertime - 100.0
		ex.light = 150
		ex.lightcolor[0] = 1
		ex.lightcolor[1] = 1
		ex.ent.model = cl_mod_explode
		ex.frames = 4
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_RAILTRAIL.value:

		# railgun effect
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadPos(netchan.net_message, pos2)
		cl_effects.CL_RailTrail(pos, pos2)
		sound_c.S_StartSound(pos2, 0, 0, cl_sfx_railg, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_EXPLOSION2.value or type_ == shared.temp_event_t.TE_GRENADE_EXPLOSION.value or type_ == shared.temp_event_t.TE_GRENADE_EXPLOSION_WATER.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.type = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT | shared.RF_NOSHADOW
		ex.start = cl_main.cl.frame.servertime - 100.0
		ex.light = 350
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.model = cl_mod_explo4
		ex.frames = 19
		ex.baseframe = 30
		ex.ent.angles[1] = (rand.randk() % 360)
		EXPLOSION_PARTICLES(pos)
		if type_ == shared.temp_event_t.TE_GRENADE_EXPLOSION_WATER.value:

			sound_c.S_StartSound(pos, 0, 0, cl_sfx_watrexp, 1, shared.ATTN_NORM, 0)

		else:

			sound_c.S_StartSound(pos, 0, 0, cl_sfx_grenexp, 1, shared.ATTN_NORM, 0)


	elif type_ == shared.temp_event_t.TE_EXPLOSION1_BIG.value or type_ == shared.temp_event_t.TE_EXPLOSION1_NP.value or type_ == shared.temp_event_t.TE_EXPLOSION1.value or type_ == shared.temp_event_t.TE_ROCKET_EXPLOSION.value or type_ == shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER.value or type_ == shared.temp_event_t.TE_PLASMA_EXPLOSION.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.type = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT | shared.RF_NOSHADOW
		ex.start = cl_main.cl.frame.servertime - 100.0
		ex.light = 350
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.angles[1] = (rand.randk() % 360)
		if type_ != shared.temp_event_t.TE_EXPLOSION1_BIG.value:

			ex.ent.model = cl_mod_explo4

		else:

			ex.ent.model = cl_mod_explo4_big


		if rand.frandk() < 0.5:

			ex.baseframe = 15


		ex.frames = 15
		if (type_ != shared.temp_event_t.TE_EXPLOSION1_BIG.value) and (type_ != shared.temp_event_t.TE_EXPLOSION1_NP.value):

			EXPLOSION_PARTICLES(pos)


		if type_ == shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER.value:

			sound_c.S_StartSound(pos, 0, 0, cl_sfx_watrexp, 1, shared.ATTN_NORM, 0)

		else:

			sound_c.S_StartSound(pos, 0, 0, cl_sfx_rockexp, 1, shared.ATTN_NORM, 0)


	elif type_ == shared.temp_event_t.TE_BFG_EXPLOSION.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.type = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT | shared.RF_NOSHADOW
		ex.start = cl_main.cl.frame.servertime - 100.0
		ex.light = 350
		ex.lightcolor[0] = 0.0
		ex.lightcolor[1] = 1.0
		ex.lightcolor[2] = 0.0
		ex.ent.model = cl_mod_bfg_explo
		ex.ent.flags |= shared.RF_TRANSLUCENT
		ex.ent.alpha = 0.30
		ex.frames = 4

	elif type_ == shared.temp_event_t.TE_BFG_BIGEXPLOSION.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		cl_effects.CL_BFGExplosionParticles(pos)

	elif type_ == shared.temp_event_t.TE_BFG_LASER.value:

		CL_ParseLaser(0xd0d1d2d3)

	elif type_ == shared.temp_event_t.TE_BUBBLETRAIL.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadPos(netchan.net_message, pos2)
		cl_effects.CL_BubbleTrail(pos, pos2)

	elif type_ == shared.temp_event_t.TE_PARASITE_ATTACK.value or type_ == shared.temp_event_t.TE_MEDIC_CABLE_ATTACK.value:

		CL_ParseBeam(cl_mod_parasite_segment, False)

	elif type_ == shared.temp_event_t.TE_BOSSTPORT.value:

		# boss teleporting to station
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		cl_effects.CL_BigTeleportParticles(pos)
		sound_c.S_StartSound(pos, 0, 0, sound_c.S_RegisterSound("misc/bigtele.wav"), 1, shared.ATTN_NONE, 0)

	elif type_ == shared.temp_event_t.TE_GRAPPLE_CABLE.value:

		CL_ParseBeam(cl_mod_grapple_cable, True)

	elif type_ == shared.temp_event_t.TE_WELDING_SPARKS.value:

		cnt = movemsg.MSG_ReadByte(netchan.net_message)
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		color = movemsg.MSG_ReadByte(netchan.net_message)
		cl_particles.CL_ParticleEffect2(pos, dir, color, cnt)
		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.type = exptype_t.ex_flash
		ex.ent.flags = shared.RF_BEAM
		ex.start = cl_main.cl.frame.servertime - 0.1
		ex.light = 100 + (rand.randk() % 75)
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 1.0
		ex.lightcolor[2] = 0.3
		ex.ent.model = cl_mod_flash
		ex.frames = 2

	elif type_ == shared.temp_event_t.TE_GREENBLOOD.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		cl_particles.CL_ParticleEffect2(pos, dir, 0xdf, 30)

	elif type_ == shared.temp_event_t.TE_TUNNEL_SPARKS.value:

		cnt = movemsg.MSG_ReadByte(netchan.net_message)
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		color = movemsg.MSG_ReadByte(netchan.net_message)
		cl_particles.CL_ParticleEffect3(pos, dir, color, cnt)

	elif type_ == shared.temp_event_t.TE_BLASTER2.value or type_ == shared.temp_event_t.TE_FLECHETTE.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		if type_ == shared.temp_event_t.TE_BLASTER2.value:

			cl_effects.CL_BlasterParticles2(pos, dir, 0xd0)

		else:

			cl_effects.CL_BlasterParticles2(pos, dir, 0x6)


		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.ent.angles[0] = math.acos(dir[2]) / math.pi * 180
		if dir[0]:

			ex.ent.angles[1] = math.atan2(dir[1], dir[0]) / math.pi * 180

		elif dir[1] > 0:

			ex.ent.angles[1] = 90

		elif dir[1] < 0:

			ex.ent.angles[1] = 270

		else:

			ex.ent.angles[1] = 0


		ex.type = exptype_t.ex_misc
		ex.ent.flags = shared.RF_FULLBRIGHT | shared.RF_TRANSLUCENT
		if type_ == shared.temp_event_t.TE_BLASTER2.value:

			ex.ent.skinnum = 1

		else:

			# flechette
			ex.ent.skinnum = 2


		ex.start = cl_main.cl.frame.servertime - 100.0
		ex.light = 150
		if type_ == shared.temp_event_t.TE_BLASTER2.value:

			ex.lightcolor[1] = 1

		else:

			# flechette
			ex.lightcolor[0] = 0.19
			ex.lightcolor[1] = 0.41
			ex.lightcolor[2] = 0.75


		ex.ent.model = cl_mod_explode
		ex.frames = 4
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_LIGHTNING.value:

		ent = CL_ParseLightning(cl_mod_lightning)
		sound_c.S_StartSound(None, ent, shared.CHAN_WEAPON, cl_sfx_lightning, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_DEBUGTRAIL.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadPos(netchan.net_message, pos2)
		cl_effects.CL_DebugTrail(pos, pos2)

	elif type_ == shared.temp_event_t.TE_PLAIN_EXPLOSION.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		ex = CL_AllocExplosion()
		shared.VectorCopy(pos, ex.ent.origin)
		ex.type = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT | shared.RF_NOSHADOW
		ex.start = cl_main.cl.frame.servertime - 100.0
		ex.light = 350
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.angles[1] = rand.randk() % 360
		ex.ent.model = cl_mod_explo4
		if rand.frandk() < 0.5:

			ex.baseframe = 15


		ex.frames = 15
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_rockexp, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_FLASHLIGHT.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		ent = movemsg.MSG_ReadShort(netchan.net_message)
		cl_effects.CL_Flashlight(ent, pos)

	elif type_ == shared.temp_event_t.TE_FORCEWALL.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadPos(netchan.net_message, pos2)
		color = movemsg.MSG_ReadByte(netchan.net_message)
		cl_effects.CL_ForceWall(pos, pos2, color)

	elif type_ == shared.temp_event_t.TE_HEATBEAM.value:

		CL_ParseHeatBeam(False)

	elif type_ == shared.temp_event_t.TE_MONSTER_HEATBEAM.value:

		CL_ParseHeatBeam(True)

	elif type_ == shared.temp_event_t.TE_HEATBEAM_SPARKS.value:

		cnt = 50
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		r = 8
		magnitude = 60
		color = r & 0xff
		cl_effects.CL_ParticleSteamEffect(pos, dir, color, cnt, magnitude)
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_HEATBEAM_STEAM.value:

		cnt = 20
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		color = 0xe0
		magnitude = 60
		cl_effects.CL_ParticleSteamEffect(pos, dir, color, cnt, magnitude)
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_STEAM.value:

		CL_ParseSteam()

	elif type_ == shared.temp_event_t.TE_BUBBLETRAIL2.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadPos(netchan.net_message, pos2)
		cl_effects.CL_BubbleTrail2(pos, pos2, 8)
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_MOREBLOOD.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		cl_particles.CL_ParticleEffect(pos, dir, 0xe8, 250)

	elif type_ == shared.temp_event_t.TE_CHAINFIST_SMOKE.value:

		dir[0] = 0
		dir[1] = 0
		dir[2] = 1
		movemsg.MSG_ReadPos(netchan.net_message, pos)
		cl_effects.CL_ParticleSmokeEffect(pos, dir, 0, 20, 20)

	elif type_ == shared.temp_event_t.TE_ELECTRIC_SPARKS.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		movemsg.MSG_ReadDir(netchan.net_message, dir)
		cl_particles.CL_ParticleEffect(pos, dir, 0x75, 40)
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_TRACKER_EXPLOSION.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		cl_effects.CL_ColorFlash(pos, 0, 150, -1, -1, -1)
		cl_effects.CL_ColorExplosionParticles(pos, 0, 1)
		sound_c.S_StartSound(pos, 0, 0, cl_sfx_disrexp, 1, shared.ATTN_NORM, 0)

	elif type_ == shared.temp_event_t.TE_TELEPORT_EFFECT.value or type_ == shared.temp_event_t.TE_DBALL_GOAL.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		cl_effects.CL_TeleportParticles(pos)

	elif type_ == shared.temp_event_t.TE_WIDOWBEAMOUT.value:

		CL_ParseWidow()

	elif type_ == shared.temp_event_t.TE_NUKEBLAST.value:

		CL_ParseNuke()

	elif type_ == shared.temp_event_t.TE_WIDOWSPLASH.value:

		movemsg.MSG_ReadPos(netchan.net_message, pos)
		cl_effects.CL_WidowSplash(pos)

	else:

		clientserver.Com_Error(common_h.ERR_DROP, "CL_ParseTEnt: bad type")
	

def CalculatePitchYaw(dir_): #const vec3_t, float *, float * (static)

	# Q2PORT: returns (pitch, yaw) instead of filling *pitch and *yaw

	"""
	float forward;
	float p, y;
	"""

	if (dir_[1] == 0) and (dir_[0] == 0):

		y = 0

		if dir_[2] > 0:

			p = 90

		else:

			p = 270


	else:

		if dir_[0]:

			y = (float(math.atan2(dir_[1], dir_[0])) * 180 / math.pi)

		elif dir_[1] > 0:

			y = 90

		else:

			y = 270


		if y < 0:

			y += 360


		forward = math.sqrt(dir_[0] * dir_[0] + dir_[1] * dir_[1])
		p = (float(math.atan2(dir_[2], forward)) * -180.0 / math.pi)

		if p < 0:

			p += 360



	return p, y # *pitch = p; *yaw = y;


"""
=================
CL_AddBeams
=================
"""
def CL_AddBeams(): # (static)

	"""
	const beam_t *b;
	vec3_t dist, org;
	float d;
	entity_t ent;
	float yaw, pitch;
	float len, steps;
	float model_length;
	"""
	dist = np.zeros((3,), dtype=np.float32)
	org = np.zeros((3,), dtype=np.float32)

	for b in cl_beams[:MAX_BEAMS]: # for (b = cl_beams; b < &cl_beams[MAX_BEAMS]; b++)

		if not b.model or (b.endtime < cl_main.cl.time):

			continue


		# if coming from the player, update the start position
		if b.entity == cl_main.cl.playernum + 1:

			# entity 0 is the world
			shared.VectorCopy(cl_main.cl.refdef.vieworg, org)
			org[2] -= 22
			# adjust for view height
			shared.VectorAdd(org, b.offset, org)

		else:

			shared.VectorAdd(b.start, b.offset, org)


		# calculate pitch and yaw
		shared.VectorSubtract(b.end, org, dist)
		pitch, yaw = CalculatePitchYaw(dist)
		# add new entities for the beams
		d = shared_c.VectorNormalize(dist)
		if b.model == cl_mod_lightning:

			model_length = 35.0
			d -= 20.0
			# correction so it doesn't end in middle of tesla

		else:

			model_length = 30.0


		steps = math.ceil(d / model_length)
		# Q2PORT: with one step the C divides by zero; its result only moves org
		# after the last segment is drawn, so 0 does the same here
		len_ = (d - model_length) / (steps - 1) if steps != 1 else 0.0
		ent = ref.entity_t() # memset(&ent, 0, sizeof(ent));
		# special case for lightning model .. if the real length
		# is shorter than the model, flip it around & draw it
		# from the end to the start. This prevents the model from
		# going through the tesla mine (instead it goes through
		# the target)
		if (b.model == cl_mod_lightning) and (d <= model_length):

			shared.VectorCopy(b.end, ent.origin)
			ent.model = b.model
			ent.flags = shared.RF_FULLBRIGHT
			ent.angles[0] = pitch
			ent.angles[1] = yaw
			ent.angles[2] = (rand.randk() % 360)
			cl_view.V_AddEntity(ent)
			continue


		while d > 0:

			shared.VectorCopy(org, ent.origin)
			ent.model = b.model
			if b.model == cl_mod_lightning:

				ent.angles[0] = -pitch
				ent.angles[1] = yaw + 180.0

			else:

				ent.angles[0] = pitch
				ent.angles[1] = yaw


			ent.angles[2] = (rand.randk() % 360)
			cl_view.V_AddEntity(ent)
			shared_c.VectorMA(org, len_, dist, org)
			d -= model_length
		
"""
//				Com_Printf ("Endpoint:  %f %f %f\n", b->end[0], b->end[1], b->end[2]);
//				Com_Printf ("Pred View Angles:  %f %f %f\n", cl.predicted_angles[0], cl.predicted_angles[1], cl.predicted_angles[2]);
//				Com_Printf ("Act View Angles: %f %f %f\n", cl.refdef.viewangles[0], cl.refdef.viewangles[1], cl.refdef.viewangles[2]);
//				VectorCopy (cl.predicted_origin, b->start);
//				b->start[2] += 22;	// adjust for view height
//				if (fabs(cl.refdef.vieworg[2] - b->start[2]) >= 10) {
//					b->start[2] = cl.refdef.vieworg[2];
//				}

//				Com_Printf ("Time:  %d %d %f\n", cl.time, cls.realtime, cls.frametime);

extern cvar_t *hand;
"""

		

def HandMul(): # (returns static float)

	if not cl_main.hand:

		return 1.0


	if cl_main.hand.value == 1:

		return -1.0

	elif cl_main.hand.value == 2:

		return 0.0

	else:

		return 1.0

def ApplyBeamOffset(ofs, hand_mul, out): #const vec3_t, float, vec3_t (static)

	shared_c.VectorMA(out, hand_mul * ofs[0], cl_main.cl.v_right, out)
	shared_c.VectorMA(out, ofs[1], cl_main.cl.v_forward, out)
	shared_c.VectorMA(out, ofs[2], cl_main.cl.v_up, out)
	if hand_mul == 0.0:

		shared_c.VectorMA(out, -1, cl_main.cl.v_up, out)

def AdjustToWeapon(ofs, hand_mul, out): #const vec3_t, float, vec3_t (static)

	"""
	int i;
	frame_t *oldframe;
	player_state_t *ps, *ops;
	"""

	# set up gun position
	ps = cl_main.cl.frame.playerstate
	i = (cl_main.cl.frame.serverframe - 1) & common_h.UPDATE_MASK
	oldframe = cl_main.cl.frames[i]
	if (oldframe.serverframe != cl_main.cl.frame.serverframe - 1) or not oldframe.valid:

		oldframe = cl_main.cl.frame
		# previous frame was dropped or invalid


	ops = oldframe.playerstate
	for i in range(3):

		out[i] = cl_main.cl.refdef.vieworg[i] + ops.gunoffset[i] + cl_main.cl.lerpfrac * (ps.gunoffset[i] - ops.gunoffset[i])


	ApplyBeamOffset(ofs, hand_mul, out)

def CL_AddHeatBeams(): # (static)

	"""
	const beam_t *b;
	vec3_t dist, org;
	float d;
	entity_t ent;
	float yaw, pitch;
	float len, steps;
	int framenum;
	float model_length;
	int by_us;
	float hand_mul;
	"""
	dist = np.zeros((3,), dtype=np.float32)
	org = np.zeros((3,), dtype=np.float32)

	hand_mul = HandMul()
	for b in cl_heatbeams[:MAX_BEAMS]: # for (b = cl_heatbeams; b < &cl_heatbeams[MAX_BEAMS]; b++)

		if not b.model or (b.endtime < cl_main.cl.time):

			continue


		by_us = (b.entity == cl_main.cl.playernum + 1)
		if by_us:

			AdjustToWeapon(b.offset, hand_mul, org)

		else:

			shared.VectorCopy(b.start, org)


		# calculate pitch and yaw
		shared.VectorSubtract(b.end, org, dist)
		if by_us:

			len_ = shared_c.VectorLength(dist)
			shared_c.VectorScale(cl_main.cl.v_forward, len_, dist)
			ApplyBeamOffset(b.offset, hand_mul, dist)


		pitch, yaw = CalculatePitchYaw(dist)
		if by_us:

			framenum = 1
			# add the rings
			cl_effects.CL_Heatbeam(org, dist)

		else:

			framenum = 2
			cl_effects.CL_MonsterPlasma_Shell(org)


		# hack for left-handed weapon
		# RF_WEAPONMODEL will mirror the beam start pos
		# so put the start pos to the right
		# that way the renderer mirrors it to the left
		if by_us and hand_mul == -1.0:

			AdjustToWeapon(b.offset, 1.0, org)
			shared.VectorSubtract(b.end, org, dist)
			len_ = shared_c.VectorLength(dist)
			shared_c.VectorScale(cl_main.cl.v_forward, len_, dist)
			ApplyBeamOffset(b.offset, 1.0, dist)
			pitch, yaw = CalculatePitchYaw(dist)


		# add new entities for the beams
		d = shared_c.VectorNormalize(dist)
		model_length = 32.0
		steps = math.ceil(d / model_length)
		# Q2PORT: with one step the C divides by zero; its result only moves org
		# after the last segment is drawn, so 0 does the same here
		len_ = (d - model_length) / (steps - 1) if steps != 1 else 0.0
		ent = ref.entity_t() # memset(&ent, 0, sizeof(ent));
		ent.model = b.model
		ent.flags = shared.RF_FULLBRIGHT
		# DG: fix rogue heatbeam high FOV rendering
		if by_us and hand_mul != 0.0:

			ent.flags |= shared.RF_WEAPONMODEL


		ent.angles[0] = -pitch
		ent.angles[1] = yaw + 180.0
		ent.angles[2] = ((cl_main.cl.time) % 360)
		ent.frame = framenum
		while d > 0:

			shared.VectorCopy(org, ent.origin)
			cl_view.V_AddEntity(ent)
			shared_c.VectorMA(org, len_, dist, org)
			d -= model_length

"""
=================
CL_AddExplosions
=================
"""
def CL_AddExplosions ():

	"""
	entity_t	*ent;
	int			i;
	explosion_t	*ex;
	float		frac;
	int			f;
	"""
	cl = cl_main.cl

	for ex in cl_explosions:
	
		if ex.type == exptype_t.ex_free:
			continue
		frac = (cl.time - ex.start)/100.0
		f = math.floor(frac)

		ent = ex.ent

		#switch (ex->type)
		if ex.type == exptype_t.ex_mflash:
			if f >= ex.frames-1:
				ex.type = exptype_t.ex_free
			
		elif ex.type == exptype_t.ex_misc:
			if f >= ex.frames-1:
			
				ex.type = exptype_t.ex_free
			
			else:
				ent.alpha = 1.0 - frac/(ex.frames-1)
			
		elif ex.type == exptype_t.ex_flash:
			if f >= 1:
			
				ex.type = exptype_t.ex_free
			
			else:
				ent.alpha = 1.0
			
		elif ex.type == exptype_t.ex_poly:
			if f >= ex.frames-1:
			
				ex.type = exptype_t.ex_free
			
			else:

				ent.alpha = (16.0 - float(f))/16.0

				if f < 10:
				
					ent.skinnum = (f>>1)
					if ent.skinnum < 0:
						ent.skinnum = 0
				
				else:
				
					ent.flags |= shared.RF_TRANSLUCENT
					if f < 13:
						ent.skinnum = 5
					else:
						ent.skinnum = 6
				
		elif ex.type == exptype_t.ex_poly2:
			if f >= ex.frames-1:
			
				ex.type = exptype_t.ex_free
			
			else:

				ent.alpha = (5.0 - float(f))/5.0
				ent.skinnum = 0
				ent.flags |= shared.RF_TRANSLUCENT
			
		if ex.type == exptype_t.ex_free:
			continue
		if ex.light:
		
			cl_view.V_AddLight (ent.origin, ex.light*ent.alpha,
				ex.lightcolor[0], ex.lightcolor[1], ex.lightcolor[2])
		
		shared.VectorCopy (ent.origin, ent.oldorigin)

		if f < 0:
			f = 0
		ent.frame = ex.baseframe + f + 1
		ent.oldframe = ex.baseframe + f
		ent.backlerp = 1.0 - cl.lerpfrac

		cl_view.V_AddEntity (ent)
	


"""
=================
CL_AddLasers
=================
"""
def CL_AddLasers ():

	#laser_t		*l;
	#int			i;

	for l in cl_lasers:
	
		if l.endtime >= cl_main.cl.time:
			cl_view.V_AddEntity (l.ent)
	

# PMM - CL_Sustains
def CL_ProcessSustain ():

	#cl_sustain_t	*s;
	#int				i;

	for s in cl_sustains:
	
		if s.id:
			if (s.endtime >= cl_main.cl.time) and (cl_main.cl.time >= s.nextthink):
			
#				Com_Printf ("think %d %d %d\n", cl.time, s->nextthink, s->thinkinterval);
				s.think (s)
			
			elif s.endtime < cl_main.cl.time:
				s.id = 0
	

"""
=================
CL_AddTEnts
=================
"""
def CL_AddTEnts(): #

	CL_AddBeams()
	CL_AddHeatBeams()
	CL_AddExplosions()
	CL_AddLasers()
	CL_ProcessSustain()

def CL_RandomFootstepSfx(): # (returns struct sfx_s *)

	return cl_sfx_footsteps[rand.randk() % NUM_FOOTSTEP_SFX]

def CL_PowerScreenModel(): # (returns struct model_s *)

	return cl_mod_powerscreen
