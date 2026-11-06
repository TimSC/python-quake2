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

*/
"""
from __future__ import annotations

import math
import random
import numpy as np
from enum import Enum
pass
pass
from client import cl_fx, cl_newfx, snd_dma, ref, cl_main, cl_view
from linux import vid_so
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
"""
// cl_tent.c -- client side temporary entities

#include "client.h"
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

	def clear(self): # memset to 0
		self.typeval = exptype_t.ex_free #exptype_t type
		self.ent = ref.entity_t() #entity_t

		self.frames = 0 # int			
		self.light = 0.0 # float		
		self.lightcolor = np.zeros((3,), dtype=np.float32) # vec3_t		
		self.start = 0.0 # float
		self.baseframe = 0 # int



MAX_EXPLOSIONS = 32
cl_explosions = [] #explosion_t[MAX_EXPLOSIONS]
for ex in range(MAX_EXPLOSIONS):
	cl_explosions.append(explosion_t())


MAX_BEAMS = 32
class beam_t(object):

	def __init__(self):
		self.clear()

	def clear(self): # memset to 0
		self.entity = 0 #int
		self.dest_entity = 0 #int
		self.model = None #struct model_s	*
		self.endtime = 0 #int
		self.offset = np.zeros((3,), dtype=np.float32) #vec3_t
		self.start = np.zeros((3,), dtype=np.float32) #vec3_t
		self.end = np.zeros((3,), dtype=np.float32) #vec3_t

cl_beams = [beam_t() for _ in range(MAX_BEAMS)] #beam_t[MAX_BEAMS]
#PMM - added this for player-linked beams.  Currently only used by the plasma beam
cl_playerbeams = [beam_t() for _ in range(MAX_BEAMS)] #beam_t[MAX_BEAMS]


MAX_LASERS = 32
class laser_t(object):

	def __init__(self):
		self.clear()

	def clear(self): # memset to 0
		self.ent = ref.entity_t() #entity_t
		self.endtime = 0 #int

cl_lasers = [laser_t() for _ in range(MAX_LASERS)] #laser_t[MAX_LASERS]

#ROGUE
cl_sustains = [client_h.cl_sustain_t() for _ in range(client_h.MAX_SUSTAINS)] #cl_sustain_t[MAX_SUSTAINS]
#ROGUE
"""
//PGM
extern void CL_TeleportParticles (vec3_t org);
//PGM

void CL_BlasterParticles (vec3_t org, vec3_t dir);
void CL_ExplosionParticles (vec3_t org);
void CL_BFGExplosionParticles (vec3_t org);
// RAFAEL
void CL_BlueBlasterParticles (vec3_t org, vec3_t dir);
"""
cl_sfx_ric1 = None #struct sfx_s	*
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
# RAFAEL
cl_sfx_plasexp = None 
cl_sfx_footsteps = [None, None, None, None] # struct sfx_s	*[4]

cl_mod_explode = None #struct model_s	*
cl_mod_smoke = None
cl_mod_flash = None
cl_mod_parasite_segment = None
cl_mod_grapple_cable = None
cl_mod_parasite_tip = None
cl_mod_explo4 = None
cl_mod_bfg_explo = None
cl_mod_powerscreen = None
# RAFAEL
cl_mod_plasmaexplo = None

#ROGUE
cl_sfx_lightning = None #struct sfx_s	*
cl_sfx_disrexp = None
cl_mod_lightning = None #struct model_s	*
cl_mod_heatbeam = None
cl_mod_monster_heatbeam = None
cl_mod_explo4_big = None

#ROGUE
"""
=================
CL_RegisterTEntSounds
=================
"""
def CL_RegisterTEntSounds ():

	global cl_sfx_ric1, cl_sfx_ric2, cl_sfx_ric3
	global cl_sfx_lashit
	global cl_sfx_spark5, cl_sfx_spark6, cl_sfx_spark7
	global cl_sfx_railg, cl_sfx_rockexp, cl_sfx_grenexp, cl_sfx_watrexp
	global cl_sfx_footsteps, cl_sfx_lightning, cl_sfx_disrexp

	"""
	int		i;
	char	name[MAX_QPATH];

	// PMM - version stuff
//	Com_Printf ("%s\n", ROGUE_VERSION_STRING);
	// PMM
	"""
	cl_sfx_ric1 = snd_dma.S_RegisterSound ("world/ric1.wav")
	cl_sfx_ric2 = snd_dma.S_RegisterSound ("world/ric2.wav")
	cl_sfx_ric3 = snd_dma.S_RegisterSound ("world/ric3.wav")
	cl_sfx_lashit = snd_dma.S_RegisterSound("weapons/lashit.wav")
	cl_sfx_spark5 = snd_dma.S_RegisterSound ("world/spark5.wav")
	cl_sfx_spark6 = snd_dma.S_RegisterSound ("world/spark6.wav")
	cl_sfx_spark7 = snd_dma.S_RegisterSound ("world/spark7.wav")
	cl_sfx_railg = snd_dma.S_RegisterSound ("weapons/railgf1a.wav")
	cl_sfx_rockexp = snd_dma.S_RegisterSound ("weapons/rocklx1a.wav")
	cl_sfx_grenexp = snd_dma.S_RegisterSound ("weapons/grenlx1a.wav")
	cl_sfx_watrexp = snd_dma.S_RegisterSound ("weapons/xpld_wat.wav")
	# RAFAEL
	# cl_sfx_plasexp = S_RegisterSound ("weapons/plasexpl.wav");
	snd_dma.S_RegisterSound ("player/land1.wav")

	snd_dma.S_RegisterSound ("player/fall2.wav")
	snd_dma.S_RegisterSound ("player/fall1.wav")

	for i in range(4):
	
		name = "player/step{}.wav".format(i+1)
		cl_sfx_footsteps[i] = snd_dma.S_RegisterSound (name)
	

#PGM
	cl_sfx_lightning = snd_dma.S_RegisterSound ("weapons/tesla.wav")
	cl_sfx_disrexp = snd_dma.S_RegisterSound ("weapons/disrupthit.wav")
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
def CL_RegisterTEntModels ():

	global cl_mod_explode, cl_mod_smoke, cl_mod_flash
	global cl_mod_parasite_segment, cl_mod_grapple_cable, cl_mod_parasite_tip
	global cl_mod_explo4, cl_mod_bfg_explo,cl_mod_powerscreen
	global cl_mod_explo4_big, cl_mod_lightning, cl_mod_heatbeam, cl_mod_monster_heatbeam

	cl_mod_explode = vid_so.re.RegisterModel ("models/objects/explode/tris.md2")
	cl_mod_smoke = vid_so.re.RegisterModel ("models/objects/smoke/tris.md2")
	cl_mod_flash = vid_so.re.RegisterModel ("models/objects/flash/tris.md2")
	cl_mod_parasite_segment = vid_so.re.RegisterModel ("models/monsters/parasite/segment/tris.md2")
	cl_mod_grapple_cable = vid_so.re.RegisterModel ("models/ctf/segment/tris.md2")
	cl_mod_parasite_tip = vid_so.re.RegisterModel ("models/monsters/parasite/tip/tris.md2")
	cl_mod_explo4 = vid_so.re.RegisterModel ("models/objects/r_explode/tris.md2")
	cl_mod_bfg_explo = vid_so.re.RegisterModel ("sprites/s_bfg2.sp2")
	cl_mod_powerscreen = vid_so.re.RegisterModel ("models/items/armor/effect/tris.md2")

	vid_so.re.RegisterModel ("models/objects/laser/tris.md2")
	vid_so.re.RegisterModel ("models/objects/grenade2/tris.md2")
	vid_so.re.RegisterModel ("models/weapons/v_machn/tris.md2")
	vid_so.re.RegisterModel ("models/weapons/v_handgr/tris.md2")
	vid_so.re.RegisterModel ("models/weapons/v_shotg2/tris.md2")
	vid_so.re.RegisterModel ("models/objects/gibs/bone/tris.md2")
	vid_so.re.RegisterModel ("models/objects/gibs/sm_meat/tris.md2")
	vid_so.re.RegisterModel ("models/objects/gibs/bone2/tris.md2")
	# RAFAEL
	# vid_so.re.RegisterModel ("models/objects/blaser/tris.md2");

	vid_so.re.RegisterPic ("w_machinegun")
	vid_so.re.RegisterPic ("a_bullets")
	vid_so.re.RegisterPic ("i_health")
	vid_so.re.RegisterPic ("a_grenades")

#ROGUE
	cl_mod_explo4_big = vid_so.re.RegisterModel ("models/objects/r_explode2/tris.md2")
	cl_mod_lightning = vid_so.re.RegisterModel ("models/proj/lightning/tris.md2")
	cl_mod_heatbeam = vid_so.re.RegisterModel ("models/proj/beam/tris.md2")
	cl_mod_monster_heatbeam = vid_so.re.RegisterModel ("models/proj/widowbeam/tris.md2")
#ROGUE
	

"""
=================
CL_ClearTEnts
=================
"""
def CL_ClearTEnts ():

	for b in cl_beams: # memset (cl_beams, 0, sizeof(cl_beams));
		b.clear()
	for ex in cl_explosions: # memset (cl_explosions, 0, sizeof(cl_explosions));
		ex.clear()
	for l in cl_lasers: # memset (cl_lasers, 0, sizeof(cl_lasers));
		l.clear()

#ROGUE
	for b in cl_playerbeams: # memset (cl_playerbeams, 0, sizeof(cl_playerbeams));
		b.clear()
	for s in cl_sustains: # memset (cl_sustains, 0, sizeof(cl_sustains));
		s.clear()
#ROGUE

"""
=================
CL_AllocExplosion
=================
"""
def CL_AllocExplosion (): #(returns explosion_t *)

	"""
	int		i;
	int		time;
	int		index;
	"""
	
	for ex in cl_explosions:
	
		if ex.typeval == exptype_t.ex_free:
		
			ex.clear()
			return ex
		
# find the oldest explosion
	time = cl_main.cl.time
	index = 0

	for i in range(MAX_EXPLOSIONS):
		if cl_explosions[i].start < time:
		
			time = cl_explosions[i].start
			index = i
		
	cl_explosions[index].clear()
	return cl_explosions[index]

"""
=================
CL_SmokeAndFlash
=================
"""
def CL_SmokeAndFlash(origin): #vec3_t

	#explosion_t	*ex;

	ex = CL_AllocExplosion ()
	shared.VectorCopy (origin, ex.ent.origin)
	ex.typeval = exptype_t.ex_misc
	ex.frames = 4
	ex.ent.flags = shared.RF_TRANSLUCENT
	ex.start = cl_main.cl.frame.servertime - 100
	ex.ent.model = cl_mod_smoke

	ex = CL_AllocExplosion ()
	shared.VectorCopy (origin, ex.ent.origin)
	ex.typeval = exptype_t.ex_flash
	ex.ent.flags = shared.RF_FULLBRIGHT
	ex.frames = 2
	ex.start = cl_main.cl.frame.servertime - 100
	ex.ent.model = cl_mod_flash

"""
=================
CL_ParseParticles
=================
"""
def CL_ParseParticles ():

	#int		color, count;
	#vec3_t	pos, dir;

	pos = movemsg.MSG_ReadPos (netchan.net_message)
	dir = movemsg.MSG_ReadDir (netchan.net_message)

	color = movemsg.MSG_ReadByte (netchan.net_message)

	count = movemsg.MSG_ReadByte (netchan.net_message)

	cl_fx.CL_ParticleEffect (pos, dir, color, count)

"""
=================
CL_ParseBeam
=================
"""
def CL_ParseBeam (model): #struct model_s * (returns int)

	"""
	int		ent;
	vec3_t	start, end;
	beam_t	*b;
	int		i;
	"""
	
	ent = movemsg.MSG_ReadShort (netchan.net_message)
	
	start = movemsg.MSG_ReadPos (netchan.net_message)
	end = movemsg.MSG_ReadPos (netchan.net_message)

# override any beam with the same entity
	for b in cl_beams:
		if b.entity == ent:
		
			b.entity = ent
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorClear (b.offset)
			return ent
		
# find a free beam
	for b in cl_beams:
	
		if not b.model or b.endtime < cl_main.cl.time:
		
			b.entity = ent
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorClear (b.offset)
			return ent
		
	clientserver.Com_Printf ("beam list overflow!\n")	
	return ent

"""
=================
CL_ParseBeam2
=================
"""
def CL_ParseBeam2 (model): #struct model_s * (returns int)

	"""
	int		ent;
	vec3_t	start, end, offset;
	beam_t	*b;
	int		i;
	"""
	
	ent = movemsg.MSG_ReadShort (netchan.net_message)
	
	start = movemsg.MSG_ReadPos (netchan.net_message)
	end = movemsg.MSG_ReadPos (netchan.net_message)
	offset = movemsg.MSG_ReadPos (netchan.net_message)

#	Com_Printf ("end- %f %f %f\n", end[0], end[1], end[2]);

# override any beam with the same entity

	for b in cl_beams:
		if b.entity == ent:
		
			b.entity = ent
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorCopy (offset, b.offset)
			return ent
		
# find a free beam
	for b in cl_beams:
	
		if not b.model or b.endtime < cl_main.cl.time:
		
			b.entity = ent
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorCopy (offset, b.offset)
			return ent
		
	clientserver.Com_Printf ("beam list overflow!\n")	
	return ent

# ROGUE
"""
=================
CL_ParsePlayerBeam
  - adds to the cl_playerbeam array instead of the cl_beams array
=================
"""
def CL_ParsePlayerBeam (model): #struct model_s * (returns int)

	"""
	int		ent;
	vec3_t	start, end, offset;
	beam_t	*b;
	int		i;
	"""
	offset = np.zeros((3,), dtype=np.float32)
	
	ent = movemsg.MSG_ReadShort (netchan.net_message)
	
	start = movemsg.MSG_ReadPos (netchan.net_message)
	end = movemsg.MSG_ReadPos (netchan.net_message)
	# PMM - network optimization
	if model is cl_mod_heatbeam:
		shared.VectorSet(offset, 2, 7, -3)
	elif model is cl_mod_monster_heatbeam:
	
		model = cl_mod_heatbeam
		shared.VectorSet(offset, 0, 0, 0)
	
	else:
		offset = movemsg.MSG_ReadPos (netchan.net_message)

#	Com_Printf ("end- %f %f %f\n", end[0], end[1], end[2]);

# override any beam with the same entity
# PMM - For player beams, we only want one per player (entity) so..
	for b in cl_playerbeams:
	
		if b.entity == ent:
		
			b.entity = ent
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorCopy (offset, b.offset)
			return ent
		
# find a free beam
	for b in cl_playerbeams:
	
		if not b.model or b.endtime < cl_main.cl.time:
		
			b.entity = ent
			b.model = model
			b.endtime = cl_main.cl.time + 100		# PMM - this needs to be 100 to prevent multiple heatbeams
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorCopy (offset, b.offset)
			return ent
		
	clientserver.Com_Printf ("beam list overflow!\n")	
	return ent

#rogue

"""
=================
CL_ParseLightning
=================
"""
def CL_ParseLightning (model): #struct model_s * (returns int)

	"""
	int		srcEnt, destEnt;
	vec3_t	start, end;
	beam_t	*b;
	int		i;
	"""
	
	srcEnt = movemsg.MSG_ReadShort (netchan.net_message)
	destEnt = movemsg.MSG_ReadShort (netchan.net_message)

	start = movemsg.MSG_ReadPos (netchan.net_message)
	end = movemsg.MSG_ReadPos (netchan.net_message)

# override any beam with the same source AND destination entities
	for b in cl_beams:
		if b.entity == srcEnt and b.dest_entity == destEnt:
		
#			Com_Printf("%d: OVERRIDE  %d -> %d\n", cl.time, srcEnt, destEnt);
			b.entity = srcEnt
			b.dest_entity = destEnt
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorClear (b.offset)
			return srcEnt
		
# find a free beam
	for b in cl_beams:
	
		if not b.model or b.endtime < cl_main.cl.time:
		
#			Com_Printf("%d: NORMAL  %d -> %d\n", cl.time, srcEnt, destEnt);
			b.entity = srcEnt
			b.dest_entity = destEnt
			b.model = model
			b.endtime = cl_main.cl.time + 200
			shared.VectorCopy (start, b.start)
			shared.VectorCopy (end, b.end)
			shared.VectorClear (b.offset)
			return srcEnt
		
	clientserver.Com_Printf ("beam list overflow!\n")	
	return srcEnt

"""
=================
CL_ParseLaser
=================
"""
def CL_ParseLaser (colors): #int

	"""
	vec3_t	start;
	vec3_t	end;
	laser_t	*l;
	int		i;
	"""

	start = movemsg.MSG_ReadPos (netchan.net_message)
	end = movemsg.MSG_ReadPos (netchan.net_message)

	for l in cl_lasers:
	
		if l.endtime < cl_main.cl.time:
		
			l.ent.flags = shared.RF_TRANSLUCENT | shared.RF_BEAM
			shared.VectorCopy (start, l.ent.origin)
			shared.VectorCopy (end, l.ent.oldorigin)
			l.ent.alpha = 0.30
			l.ent.skinnum = (colors >> ((random.getrandbits(15) % 4)*8)) & 0xff
			l.ent.model = None
			l.ent.frame = 4
			l.endtime = cl_main.cl.time + 100
			return
		

#=============
#ROGUE
def CL_ParseSteam ():

	"""
	vec3_t	pos, dir;
	int		id, i;
	int		r;
	int		cnt;
	int		color;
	int		magnitude;
	cl_sustain_t	*s, *free_sustain;
	"""

	id = movemsg.MSG_ReadShort (netchan.net_message)		# an id of -1 is an instant effect
	if id != -1: # sustains
	
#			Com_Printf ("Sustain effect id %d\n", id);
		free_sustain = None
		for s in cl_sustains:
		
			if s.id == 0:
			
				free_sustain = s
				break
			
		if free_sustain:
		
			s = free_sustain
			s.id = id
			s.count = movemsg.MSG_ReadByte (netchan.net_message)
			s.org[:] = movemsg.MSG_ReadPos (netchan.net_message)
			s.dir[:] = movemsg.MSG_ReadDir (netchan.net_message)
			r = movemsg.MSG_ReadByte (netchan.net_message)
			s.color = r & 0xff
			s.magnitude = movemsg.MSG_ReadShort (netchan.net_message)
			s.endtime = cl_main.cl.time + movemsg.MSG_ReadLong (netchan.net_message)
			s.think = cl_newfx.CL_ParticleSteamEffect2
			s.thinkinterval = 100
			s.nextthink = cl_main.cl.time
		
		else:
		
#				Com_Printf ("No free sustains!\n");
			# FIXME - read the stuff anyway
			cnt = movemsg.MSG_ReadByte (netchan.net_message)
			pos = movemsg.MSG_ReadPos (netchan.net_message)
			dir = movemsg.MSG_ReadDir (netchan.net_message)
			r = movemsg.MSG_ReadByte (netchan.net_message)
			magnitude = movemsg.MSG_ReadShort (netchan.net_message)
			magnitude = movemsg.MSG_ReadLong (netchan.net_message) # really interval
		
	else: # instant
	
		cnt = movemsg.MSG_ReadByte (netchan.net_message)
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		r = movemsg.MSG_ReadByte (netchan.net_message)
		magnitude = movemsg.MSG_ReadShort (netchan.net_message)
		color = r & 0xff
		cl_newfx.CL_ParticleSteamEffect (pos, dir, color, cnt, magnitude)
#		S_StartSound (pos,  0, 0, cl_sfx_lashit, 1, ATTN_NORM, 0);
	

def CL_ParseWidow ():

	"""
	vec3_t	pos;
	int		id, i;
	cl_sustain_t	*s, *free_sustain;
	"""

	id = movemsg.MSG_ReadShort (netchan.net_message)

	free_sustain = None
	for s in cl_sustains:
	
		if s.id == 0:
		
			free_sustain = s
			break
		
	if free_sustain:
	
		s = free_sustain
		s.id = id
		s.org[:] = movemsg.MSG_ReadPos (netchan.net_message)
		s.endtime = cl_main.cl.time + 2100
		s.think = cl_newfx.CL_Widowbeamout
		s.thinkinterval = 1
		s.nextthink = cl_main.cl.time
	
	else: # no free sustains
	
		# FIXME - read the stuff anyway
		pos = movemsg.MSG_ReadPos (netchan.net_message)
	

def CL_ParseNuke ():

	"""
	vec3_t	pos;
	int		i;
	cl_sustain_t	*s, *free_sustain;
	"""

	free_sustain = None
	for s in cl_sustains:
	
		if s.id == 0:
		
			free_sustain = s
			break
		
	if free_sustain:
	
		s = free_sustain
		s.id = 21000
		s.org[:] = movemsg.MSG_ReadPos (netchan.net_message)
		s.endtime = cl_main.cl.time + 1000
		s.think = cl_newfx.CL_Nukeblast
		s.thinkinterval = 1
		s.nextthink = cl_main.cl.time
	
	else: # no free sustains
	
		# FIXME - read the stuff anyway
		pos = movemsg.MSG_ReadPos (netchan.net_message)
	

#ROGUE
#=============


"""
=================
CL_ParseTEnt
=================
"""
splash_color = [0x00, 0xe0, 0xb0, 0x50, 0xd0, 0xe0, 0xe8] #static byte[]

def CL_ParseTEnt ():

	"""
	int		type;
	vec3_t	pos, pos2, dir;
	explosion_t	*ex;
	int		cnt;
	int		color;
	int		r;
	int		ent;
	int		magnitude;
	"""
	dir = np.zeros((3,), dtype=np.float32)

	type = shared.temp_event_t(movemsg.MSG_ReadByte (netchan.net_message))

	#switch (type)
	if type == shared.temp_event_t.TE_BLOOD:			# bullet hitting flesh
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		cl_fx.CL_ParticleEffect (pos, dir, 0xe8, 60)
	
	elif type in (shared.temp_event_t.TE_GUNSHOT, shared.temp_event_t.TE_SPARKS, shared.temp_event_t.TE_BULLET_SPARKS):			# bullet hitting wall
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		if type == shared.temp_event_t.TE_GUNSHOT:
			cl_fx.CL_ParticleEffect (pos, dir, 0, 40)
		else:
			cl_fx.CL_ParticleEffect (pos, dir, 0xe0, 6)

		if type != shared.temp_event_t.TE_SPARKS:
		
			CL_SmokeAndFlash(pos)
			
			# impact sound
			cnt = random.getrandbits(15)&15
			if cnt == 1:
				snd_dma.S_StartSound (pos, 0, 0, cl_sfx_ric1, 1, shared.ATTN_NORM, 0)
			elif cnt == 2:
				snd_dma.S_StartSound (pos, 0, 0, cl_sfx_ric2, 1, shared.ATTN_NORM, 0)
			elif cnt == 3:
				snd_dma.S_StartSound (pos, 0, 0, cl_sfx_ric3, 1, shared.ATTN_NORM, 0)
		
	elif type in (shared.temp_event_t.TE_SCREEN_SPARKS, shared.temp_event_t.TE_SHIELD_SPARKS):
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		if type == shared.temp_event_t.TE_SCREEN_SPARKS:
			cl_fx.CL_ParticleEffect (pos, dir, 0xd0, 40)
		else:
			cl_fx.CL_ParticleEffect (pos, dir, 0xb0, 40)
		#FIXME : replace or remove this sound
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)
		
	elif type == shared.temp_event_t.TE_SHOTGUN:			# bullet hitting wall
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		cl_fx.CL_ParticleEffect (pos, dir, 0, 20)
		CL_SmokeAndFlash(pos)

	elif type == shared.temp_event_t.TE_SPLASH:			# bullet hitting water
		cnt = movemsg.MSG_ReadByte (netchan.net_message)
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		r = movemsg.MSG_ReadByte (netchan.net_message)
		if r > 6:
			color = 0x00
		else:
			color = splash_color[r]
		cl_fx.CL_ParticleEffect (pos, dir, color, cnt)

		if r == shared.SPLASH_SPARKS:
		
			r = random.getrandbits(15) & 3
			if r == 0:
				snd_dma.S_StartSound (pos, 0, 0, cl_sfx_spark5, 1, shared.ATTN_STATIC, 0)
			elif r == 1:
				snd_dma.S_StartSound (pos, 0, 0, cl_sfx_spark6, 1, shared.ATTN_STATIC, 0)
			else:
				snd_dma.S_StartSound (pos, 0, 0, cl_sfx_spark7, 1, shared.ATTN_STATIC, 0)
		
	elif type == shared.temp_event_t.TE_LASER_SPARKS:
		cnt = movemsg.MSG_ReadByte (netchan.net_message)
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		color = movemsg.MSG_ReadByte (netchan.net_message)
		cl_fx.CL_ParticleEffect2 (pos, dir, color, cnt)

	# RAFAEL
	elif type == shared.temp_event_t.TE_BLUEHYPERBLASTER:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadPos (netchan.net_message)
		cl_fx.CL_BlasterParticles (pos, dir)

	elif type == shared.temp_event_t.TE_BLASTER:			# blaster hitting wall
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		cl_fx.CL_BlasterParticles (pos, dir)

		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.ent.angles[0] = math.acos(dir[2])/math.pi*180
	# PMM - fixed to correct for pitch of 0
		if dir[0]:
			ex.ent.angles[1] = math.atan2(dir[1], dir[0])/math.pi*180
		elif dir[1] > 0:
			ex.ent.angles[1] = 90
		elif dir[1] < 0:
			ex.ent.angles[1] = 270
		else:
			ex.ent.angles[1] = 0

		ex.typeval = exptype_t.ex_misc
		ex.ent.flags = shared.RF_FULLBRIGHT|shared.RF_TRANSLUCENT
		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 150
		ex.lightcolor[0] = 1
		ex.lightcolor[1] = 1
		ex.ent.model = cl_mod_explode
		ex.frames = 4
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)
		
	elif type == shared.temp_event_t.TE_RAILTRAIL:			# railgun effect
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		pos2 = movemsg.MSG_ReadPos (netchan.net_message)
		cl_fx.CL_RailTrail (pos, pos2)
		snd_dma.S_StartSound (pos2, 0, 0, cl_sfx_railg, 1, shared.ATTN_NORM, 0)

	elif type in (shared.temp_event_t.TE_EXPLOSION2, shared.temp_event_t.TE_GRENADE_EXPLOSION, shared.temp_event_t.TE_GRENADE_EXPLOSION_WATER):
		pos = movemsg.MSG_ReadPos (netchan.net_message)

		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.typeval = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT
		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 350
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.model = cl_mod_explo4
		ex.frames = 19
		ex.baseframe = 30
		ex.ent.angles[1] = random.getrandbits(15) % 360
		cl_fx.CL_ExplosionParticles (pos)
		if type == shared.temp_event_t.TE_GRENADE_EXPLOSION_WATER:
			snd_dma.S_StartSound (pos, 0, 0, cl_sfx_watrexp, 1, shared.ATTN_NORM, 0)
		else:
			snd_dma.S_StartSound (pos, 0, 0, cl_sfx_grenexp, 1, shared.ATTN_NORM, 0)

	# RAFAEL
	elif type == shared.temp_event_t.TE_PLASMA_EXPLOSION:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.typeval = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT
		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 350
		ex.lightcolor[0] = 1.0 
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.angles[1] = random.getrandbits(15) % 360
		ex.ent.model = cl_mod_explo4
		if frame.frand() < 0.5:
			ex.baseframe = 15
		ex.frames = 15
		cl_fx.CL_ExplosionParticles (pos)
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_rockexp, 1, shared.ATTN_NORM, 0)
	
	elif type in (shared.temp_event_t.TE_EXPLOSION1, shared.temp_event_t.TE_EXPLOSION1_BIG, shared.temp_event_t.TE_ROCKET_EXPLOSION, shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER, shared.temp_event_t.TE_EXPLOSION1_NP): # PMM
		pos = movemsg.MSG_ReadPos (netchan.net_message)

		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.typeval = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT
		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 350
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.angles[1] = random.getrandbits(15) % 360
		if type != shared.temp_event_t.TE_EXPLOSION1_BIG:				# PMM
			ex.ent.model = cl_mod_explo4			# PMM
		else:
			ex.ent.model = cl_mod_explo4_big
		if frame.frand() < 0.5:
			ex.baseframe = 15
		ex.frames = 15
		if (type != shared.temp_event_t.TE_EXPLOSION1_BIG) and (type != shared.temp_event_t.TE_EXPLOSION1_NP):		# PMM
			cl_fx.CL_ExplosionParticles (pos)									# PMM
		if type == shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER:
			snd_dma.S_StartSound (pos, 0, 0, cl_sfx_watrexp, 1, shared.ATTN_NORM, 0)
		else:
			snd_dma.S_StartSound (pos, 0, 0, cl_sfx_rockexp, 1, shared.ATTN_NORM, 0)

	elif type == shared.temp_event_t.TE_BFG_EXPLOSION:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.typeval = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT
		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 350
		ex.lightcolor[0] = 0.0
		ex.lightcolor[1] = 1.0
		ex.lightcolor[2] = 0.0
		ex.ent.model = cl_mod_bfg_explo
		ex.ent.flags |= shared.RF_TRANSLUCENT
		ex.ent.alpha = 0.30
		ex.frames = 4

	elif type == shared.temp_event_t.TE_BFG_BIGEXPLOSION:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		cl_fx.CL_BFGExplosionParticles (pos)

	elif type == shared.temp_event_t.TE_BFG_LASER:
		CL_ParseLaser (0xd0d1d2d3)

	elif type == shared.temp_event_t.TE_BUBBLETRAIL:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		pos2 = movemsg.MSG_ReadPos (netchan.net_message)
		cl_fx.CL_BubbleTrail (pos, pos2)

	elif type in (shared.temp_event_t.TE_PARASITE_ATTACK, shared.temp_event_t.TE_MEDIC_CABLE_ATTACK):
		ent = CL_ParseBeam (cl_mod_parasite_segment)

	elif type == shared.temp_event_t.TE_BOSSTPORT:			# boss teleporting to station
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		cl_fx.CL_BigTeleportParticles (pos)
		snd_dma.S_StartSound (pos, 0, 0, snd_dma.S_RegisterSound ("misc/bigtele.wav"), 1, shared.ATTN_NONE, 0)

	elif type == shared.temp_event_t.TE_GRAPPLE_CABLE:
		ent = CL_ParseBeam2 (cl_mod_grapple_cable)

	# RAFAEL
	elif type == shared.temp_event_t.TE_WELDING_SPARKS:
		cnt = movemsg.MSG_ReadByte (netchan.net_message)
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		color = movemsg.MSG_ReadByte (netchan.net_message)
		cl_fx.CL_ParticleEffect2 (pos, dir, color, cnt)

		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.typeval = exptype_t.ex_flash
		# note to self
		# we need a better no draw flag
		ex.ent.flags = shared.RF_BEAM
		ex.start = cl_main.cl.frame.servertime - 0.1
		ex.light = 100 + (random.getrandbits(15)%75)
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 1.0
		ex.lightcolor[2] = 0.3
		ex.ent.model = cl_mod_flash
		ex.frames = 2

	elif type == shared.temp_event_t.TE_GREENBLOOD:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		cl_fx.CL_ParticleEffect2 (pos, dir, 0xdf, 30)

	# RAFAEL
	elif type == shared.temp_event_t.TE_TUNNEL_SPARKS:
		cnt = movemsg.MSG_ReadByte (netchan.net_message)
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		color = movemsg.MSG_ReadByte (netchan.net_message)
		cl_fx.CL_ParticleEffect3 (pos, dir, color, cnt)

#=============
#PGM
		# PMM -following code integrated for flechette (different color)
	elif type in (shared.temp_event_t.TE_BLASTER2, shared.temp_event_t.TE_FLECHETTE):			# green blaster hitting wall / flechette
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		
		# PMM
		if type == shared.temp_event_t.TE_BLASTER2:
			cl_newfx.CL_BlasterParticles2 (pos, dir, 0xd0)
		else:
			cl_newfx.CL_BlasterParticles2 (pos, dir, 0x6f) # 75

		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.ent.angles[0] = math.acos(dir[2])/math.pi*180
	# PMM - fixed to correct for pitch of 0
		if dir[0]:
			ex.ent.angles[1] = math.atan2(dir[1], dir[0])/math.pi*180
		elif dir[1] > 0:
			ex.ent.angles[1] = 90
		elif dir[1] < 0:
			ex.ent.angles[1] = 270
		else:
			ex.ent.angles[1] = 0

		ex.typeval = exptype_t.ex_misc
		ex.ent.flags = shared.RF_FULLBRIGHT|shared.RF_TRANSLUCENT

		# PMM
		if type == shared.temp_event_t.TE_BLASTER2:
			ex.ent.skinnum = 1
		else: # flechette
			ex.ent.skinnum = 2

		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 150
		# PMM
		if type == shared.temp_event_t.TE_BLASTER2:
			ex.lightcolor[1] = 1
		else: # flechette
		
			ex.lightcolor[0] = 0.19
			ex.lightcolor[1] = 0.41
			ex.lightcolor[2] = 0.75
		
		ex.ent.model = cl_mod_explode
		ex.frames = 4
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)


	elif type == shared.temp_event_t.TE_LIGHTNING:
		ent = CL_ParseLightning (cl_mod_lightning)
		snd_dma.S_StartSound (None, ent, shared.CHAN_WEAPON, cl_sfx_lightning, 1, shared.ATTN_NORM, 0)

	elif type == shared.temp_event_t.TE_DEBUGTRAIL:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		pos2 = movemsg.MSG_ReadPos (netchan.net_message)
		cl_newfx.CL_DebugTrail (pos, pos2)

	elif type == shared.temp_event_t.TE_PLAIN_EXPLOSION:
		pos = movemsg.MSG_ReadPos (netchan.net_message)

		ex = CL_AllocExplosion ()
		shared.VectorCopy (pos, ex.ent.origin)
		ex.typeval = exptype_t.ex_poly
		ex.ent.flags = shared.RF_FULLBRIGHT
		ex.start = cl_main.cl.frame.servertime - 100
		ex.light = 350
		ex.lightcolor[0] = 1.0
		ex.lightcolor[1] = 0.5
		ex.lightcolor[2] = 0.5
		ex.ent.angles[1] = random.getrandbits(15) % 360
		ex.ent.model = cl_mod_explo4
		if frame.frand() < 0.5:
			ex.baseframe = 15
		ex.frames = 15
		if type == shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER:
			snd_dma.S_StartSound (pos, 0, 0, cl_sfx_watrexp, 1, shared.ATTN_NORM, 0)
		else:
			snd_dma.S_StartSound (pos, 0, 0, cl_sfx_rockexp, 1, shared.ATTN_NORM, 0)

	elif type == shared.temp_event_t.TE_FLASHLIGHT:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		ent = movemsg.MSG_ReadShort (netchan.net_message)
		cl_newfx.CL_Flashlight(ent, pos)

	elif type == shared.temp_event_t.TE_FORCEWALL:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		pos2 = movemsg.MSG_ReadPos (netchan.net_message)
		color = movemsg.MSG_ReadByte (netchan.net_message)
		cl_newfx.CL_ForceWall(pos, pos2, color)

	elif type == shared.temp_event_t.TE_HEATBEAM:
		ent = CL_ParsePlayerBeam (cl_mod_heatbeam)

	elif type == shared.temp_event_t.TE_MONSTER_HEATBEAM:
		ent = CL_ParsePlayerBeam (cl_mod_monster_heatbeam)

	elif type == shared.temp_event_t.TE_HEATBEAM_SPARKS:
#		cnt = MSG_ReadByte (&net_message);
		cnt = 50
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
#		r = MSG_ReadByte (&net_message);
#		magnitude = MSG_ReadShort (&net_message);
		r = 8
		magnitude = 60
		color = r & 0xff
		cl_newfx.CL_ParticleSteamEffect (pos, dir, color, cnt, magnitude)
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)
	
	elif type == shared.temp_event_t.TE_HEATBEAM_STEAM:
#		cnt = MSG_ReadByte (&net_message);
		cnt = 20
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
#		r = MSG_ReadByte (&net_message);
#		magnitude = MSG_ReadShort (&net_message);
#		color = r & 0xff;
		color = 0xe0
		magnitude = 60
		cl_newfx.CL_ParticleSteamEffect (pos, dir, color, cnt, magnitude)
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type == shared.temp_event_t.TE_STEAM:
		CL_ParseSteam()

	elif type == shared.temp_event_t.TE_BUBBLETRAIL2:
#		cnt = MSG_ReadByte (&net_message);
		cnt = 8
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		pos2 = movemsg.MSG_ReadPos (netchan.net_message)
		cl_newfx.CL_BubbleTrail2 (pos, pos2, cnt)
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type == shared.temp_event_t.TE_MOREBLOOD:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
		cl_fx.CL_ParticleEffect (pos, dir, 0xe8, 250)

	elif type == shared.temp_event_t.TE_CHAINFIST_SMOKE:
		dir[0]=0; dir[1]=0; dir[2]=1
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		cl_newfx.CL_ParticleSmokeEffect (pos, dir, 0, 20, 20)

	elif type == shared.temp_event_t.TE_ELECTRIC_SPARKS:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		dir = movemsg.MSG_ReadDir (netchan.net_message)
#		CL_ParticleEffect (pos, dir, 109, 40);
		cl_fx.CL_ParticleEffect (pos, dir, 0x75, 40)
		#FIXME : replace or remove this sound
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_lashit, 1, shared.ATTN_NORM, 0)

	elif type == shared.temp_event_t.TE_TRACKER_EXPLOSION:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		cl_newfx.CL_ColorFlash (pos, 0, 150, -1, -1, -1)
		cl_newfx.CL_ColorExplosionParticles (pos, 0, 1)
#		CL_Tracker_Explode (pos);
		snd_dma.S_StartSound (pos, 0, 0, cl_sfx_disrexp, 1, shared.ATTN_NORM, 0)

	elif type in (shared.temp_event_t.TE_TELEPORT_EFFECT, shared.temp_event_t.TE_DBALL_GOAL):
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		cl_fx.CL_TeleportParticles (pos)

	elif type == shared.temp_event_t.TE_WIDOWBEAMOUT:
		CL_ParseWidow ()

	elif type == shared.temp_event_t.TE_NUKEBLAST:
		CL_ParseNuke ()

	elif type == shared.temp_event_t.TE_WIDOWSPLASH:
		pos = movemsg.MSG_ReadPos (netchan.net_message)
		cl_newfx.CL_WidowSplash (pos)
#PGM
#==============

	else:
		clientserver.Com_Error (shared.ERR_DROP, "CL_ParseTEnt: bad type")
	

"""
=================
CL_AddBeams
=================
"""
def CL_AddBeams ():

	"""
	int			i,j;
	beam_t		*b;
	vec3_t		dist, org;
	float		d;
	entity_t	ent;
	float		yaw, pitch;
	float		forward;
	float		len, steps;
	float		model_length;
	"""
	dist = np.zeros((3,), dtype=np.float32)
	org = np.zeros((3,), dtype=np.float32)
	cl = cl_main.cl
	
# update beams
	for b in cl_beams:
	
		if not b.model or b.endtime < cl.time:
			continue

		# if coming from the player, update the start position
		if b.entity == cl.playernum+1:	# entity 0 is the world
		
			shared.VectorCopy (cl.refdef.vieworg, b.start)
			b.start[2] -= 22	# adjust for view height
		
		shared.VectorAdd (b.start, b.offset, org)

	# calculate pitch and yaw
		shared.VectorSubtract (b.end, org, dist)

		if dist[1] == 0 and dist[0] == 0:
		
			yaw = 0
			if dist[2] > 0:
				pitch = 90
			else:
				pitch = 270
		
		else:
		
	# PMM - fixed to correct for pitch of 0
			if dist[0]:
				yaw = (math.atan2(dist[1], dist[0]) * 180 / math.pi)
			elif dist[1] > 0:
				yaw = 90
			else:
				yaw = 270
			if yaw < 0:
				yaw += 360
	
			forward = math.sqrt (dist[0]*dist[0] + dist[1]*dist[1])
			pitch = (math.atan2(dist[2], forward) * -180.0 / math.pi)
			if pitch < 0:
				pitch += 360.0
		

	# add new entities for the beams
		d = shared_c.VectorNormalize(dist)

		ent = ref.entity_t() # memset (&ent, 0, sizeof(ent));
		if b.model is cl_mod_lightning:
		
			model_length = 35.0
			d-= 20.0  # correction so it doesn't end in middle of tesla
		
		else:
		
			model_length = 30.0
		
		steps = math.ceil(d/model_length)
		length = (d-model_length)/(steps-1) if steps != 1 else 0.0 # C divides by zero (inf) here, but it is unused when only one step is drawn

		# PMM - special case for lightning model .. if the real length is shorter than the model,
		# flip it around & draw it from the end to the start.  This prevents the model from going
		# through the tesla mine (instead it goes through the target)
		if (b.model is cl_mod_lightning) and (d <= model_length):
		
#			Com_Printf ("special case\n");
			shared.VectorCopy (b.end, ent.origin)
			# offset to push beam outside of tesla model (negative because dist is from end to start
			# for this beam)
#			for (j=0 ; j<3 ; j++)
#				ent.origin[j] -= dist[j]*10.0;
			ent.model = b.model
			ent.flags = shared.RF_FULLBRIGHT
			ent.angles[0] = pitch
			ent.angles[1] = yaw
			ent.angles[2] = random.getrandbits(15)%360
			cl_view.V_AddEntity (ent)			
			return
		
		while d > 0:
		
			shared.VectorCopy (org, ent.origin)
			ent.model = b.model
			if b.model is cl_mod_lightning:
			
				ent.flags = shared.RF_FULLBRIGHT
				ent.angles[0] = -pitch
				ent.angles[1] = yaw + 180.0
				ent.angles[2] = random.getrandbits(15)%360
			
			else:
			
				ent.angles[0] = pitch
				ent.angles[1] = yaw
				ent.angles[2] = random.getrandbits(15)%360
			
#			Com_Printf("B: %d -> %d\n", b->entity, b->dest_entity);
			cl_view.V_AddEntity (ent)

			for j in range(3):
				org[j] += dist[j]*length
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

"""
=================
ROGUE - draw player locked beams
CL_AddPlayerBeams
=================
"""
def CL_AddPlayerBeams ():

	"""
	int			i,j;
	beam_t		*b;
	vec3_t		dist, org;
	float		d;
	entity_t	ent;
	float		yaw, pitch;
	float		forward;
	float		len, steps;
	int			framenum;
	float		model_length;
	
	float		hand_multiplier;
	frame_t		*oldframe;
	player_state_t	*ps, *ops;
	"""
	dist = np.zeros((3,), dtype=np.float32)
	org = np.zeros((3,), dtype=np.float32)
	ent = ref.entity_t()
	framenum = 0
	cl = cl_main.cl
	hand = cl_main.hand

#PMM
	if hand:
	
		if hand.value == 2:
			hand_multiplier = 0
		elif hand.value == 1:
			hand_multiplier = -1
		else:
			hand_multiplier = 1
	
	else:
	
		hand_multiplier = 1
	
#PMM

# update beams
	for b in cl_playerbeams:
	
		#vec3_t		f,r,u;
		f = np.zeros((3,), dtype=np.float32)
		r = np.zeros((3,), dtype=np.float32)
		u = np.zeros((3,), dtype=np.float32)
		if not b.model or b.endtime < cl.time:
			continue

		if cl_mod_heatbeam and (b.model is cl_mod_heatbeam):
		
			# if coming from the player, update the start position
			if b.entity == cl.playernum+1:	# entity 0 is the world
				
				# set up gun position
				# code straight out of CL_AddViewWeapon
				ps = cl.frame.playerstate
				j = (cl.frame.serverframe - 1) & common_h.UPDATE_MASK
				oldframe = cl.frames[j]
				if oldframe.serverframe != cl.frame.serverframe-1 or not oldframe.valid:
					oldframe = cl.frame		# previous frame was dropped or involid
				ops = oldframe.playerstate
				for j in range(3):
				
					b.start[j] = cl.refdef.vieworg[j] + ops.gunoffset[j] \
						+ cl.lerpfrac * (ps.gunoffset[j] - ops.gunoffset[j])
				
				shared_c.VectorMA (b.start, (hand_multiplier * b.offset[0]), cl.v_right, org)
				shared_c.VectorMA (     org, b.offset[1], cl.v_forward, org)
				shared_c.VectorMA (     org, b.offset[2], cl.v_up, org)
				if hand and hand.value == 2:
					shared_c.VectorMA (org, -1, cl.v_up, org)
				
				# FIXME - take these out when final
				shared.VectorCopy (cl.v_right, r)
				shared.VectorCopy (cl.v_forward, f)
				shared.VectorCopy (cl.v_up, u)

			
			else:
				shared.VectorCopy (b.start, org)
		
		else:
		
			# if coming from the player, update the start position
			if b.entity == cl.playernum+1:	# entity 0 is the world
			
				shared.VectorCopy (cl.refdef.vieworg, b.start)
				b.start[2] -= 22	# adjust for view height
			
			shared.VectorAdd (b.start, b.offset, org)
		
	# calculate pitch and yaw
		shared.VectorSubtract (b.end, org, dist)

#PMM
		if cl_mod_heatbeam and (b.model is cl_mod_heatbeam) and (b.entity == cl.playernum+1):
		
			#vec_t len;

			length = shared_c.VectorLength (dist)
			shared_c.VectorScale (f, length, dist)
			shared_c.VectorMA (dist, (hand_multiplier * b.offset[0]), r, dist)
			shared_c.VectorMA (dist, b.offset[1], f, dist)
			shared_c.VectorMA (dist, b.offset[2], u, dist)
			if hand and hand.value == 2:
				shared_c.VectorMA (org, -1, cl.v_up, org)
			
#PMM

		if dist[1] == 0 and dist[0] == 0:
		
			yaw = 0
			if dist[2] > 0:
				pitch = 90
			else:
				pitch = 270
		
		else:
		
	# PMM - fixed to correct for pitch of 0
			if dist[0]:
				yaw = (math.atan2(dist[1], dist[0]) * 180 / math.pi)
			elif dist[1] > 0:
				yaw = 90
			else:
				yaw = 270
			if yaw < 0:
				yaw += 360
	
			forward = math.sqrt (dist[0]*dist[0] + dist[1]*dist[1])
			pitch = (math.atan2(dist[2], forward) * -180.0 / math.pi)
			if pitch < 0:
				pitch += 360.0
		
		
		if cl_mod_heatbeam and (b.model is cl_mod_heatbeam):
		
			if b.entity != cl.playernum+1:
			
				framenum = 2
#				Com_Printf ("Third person\n");
				ent.angles[0] = -pitch
				ent.angles[1] = yaw + 180.0
				ent.angles[2] = 0
#				Com_Printf ("%f %f - %f %f %f\n", -pitch, yaw+180.0, b->offset[0], b->offset[1], b->offset[2]);
				shared_c.AngleVectors(ent.angles, f, r, u)
					
				# if it's a non-origin offset, it's a player, so use the hardcoded player offset
				if not shared_c.VectorCompare (b.offset, shared_c.vec3_origin):
				
					shared_c.VectorMA (org, -(b.offset[0])+1, r, org)
					shared_c.VectorMA (org, -(b.offset[1]), f, org)
					shared_c.VectorMA (org, -(b.offset[2])-10, u, org)
				
				else:
				
					# if it's a monster, do the particle effect
					cl_newfx.CL_MonsterPlasma_Shell(b.start)
				
			else:
			
				framenum = 1
			
		# if it's the heatbeam, draw the particle effect
		if (cl_mod_heatbeam and (b.model is cl_mod_heatbeam) and (b.entity == cl.playernum+1)):
		
			cl_newfx.CL_Heatbeam (org, dist)
		
	# add new entities for the beams
		d = shared_c.VectorNormalize(dist)

		ent = ref.entity_t() # memset (&ent, 0, sizeof(ent));
		if b.model is cl_mod_heatbeam:
		
			model_length = 32.0
		
		elif b.model is cl_mod_lightning:
		
			model_length = 35.0
			d-= 20.0  # correction so it doesn't end in middle of tesla
		
		else:
		
			model_length = 30.0
		
		steps = math.ceil(d/model_length)
		length = (d-model_length)/(steps-1) if steps != 1 else 0.0 # C divides by zero (inf) here, but it is unused when only one step is drawn

		# PMM - special case for lightning model .. if the real length is shorter than the model,
		# flip it around & draw it from the end to the start.  This prevents the model from going
		# through the tesla mine (instead it goes through the target)
		if (b.model is cl_mod_lightning) and (d <= model_length):
		
#			Com_Printf ("special case\n");
			shared.VectorCopy (b.end, ent.origin)
			# offset to push beam outside of tesla model (negative because dist is from end to start
			# for this beam)
#			for (j=0 ; j<3 ; j++)
#				ent.origin[j] -= dist[j]*10.0;
			ent.model = b.model
			ent.flags = shared.RF_FULLBRIGHT
			ent.angles[0] = pitch
			ent.angles[1] = yaw
			ent.angles[2] = random.getrandbits(15)%360
			cl_view.V_AddEntity (ent)			
			return
		
		while d > 0:
		
			shared.VectorCopy (org, ent.origin)
			ent.model = b.model
			if cl_mod_heatbeam and (b.model is cl_mod_heatbeam):
			
#				ent.flags = RF_FULLBRIGHT|RF_TRANSLUCENT;
#				ent.alpha = 0.3;
				ent.flags = shared.RF_FULLBRIGHT
				ent.angles[0] = -pitch
				ent.angles[1] = yaw + 180.0
				ent.angles[2] = (int(cl.time)) % 360
#				ent.angles[2] = rand()%360;
				ent.frame = framenum
			
			elif b.model is cl_mod_lightning:
			
				ent.flags = shared.RF_FULLBRIGHT
				ent.angles[0] = -pitch
				ent.angles[1] = yaw + 180.0
				ent.angles[2] = random.getrandbits(15)%360
			
			else:
			
				ent.angles[0] = pitch
				ent.angles[1] = yaw
				ent.angles[2] = random.getrandbits(15)%360
			
#			Com_Printf("B: %d -> %d\n", b->entity, b->dest_entity);
			cl_view.V_AddEntity (ent)

			for j in range(3):
				org[j] += dist[j]*length
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
	
		if ex.typeval == exptype_t.ex_free:
			continue
		frac = (cl.time - ex.start)/100.0
		f = math.floor(frac)

		ent = ex.ent

		#switch (ex->type)
		if ex.typeval == exptype_t.ex_mflash:
			if f >= ex.frames-1:
				ex.typeval = exptype_t.ex_free
			
		elif ex.typeval == exptype_t.ex_misc:
			if f >= ex.frames-1:
			
				ex.typeval = exptype_t.ex_free
			
			else:
				ent.alpha = 1.0 - frac/(ex.frames-1)
			
		elif ex.typeval == exptype_t.ex_flash:
			if f >= 1:
			
				ex.typeval = exptype_t.ex_free
			
			else:
				ent.alpha = 1.0
			
		elif ex.typeval == exptype_t.ex_poly:
			if f >= ex.frames-1:
			
				ex.typeval = exptype_t.ex_free
			
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
				
		elif ex.typeval == exptype_t.ex_poly2:
			if f >= ex.frames-1:
			
				ex.typeval = exptype_t.ex_free
			
			else:

				ent.alpha = (5.0 - float(f))/5.0
				ent.skinnum = 0
				ent.flags |= shared.RF_TRANSLUCENT
			
		if ex.typeval == exptype_t.ex_free:
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
def CL_AddTEnts ():

	CL_AddBeams ()
	# PMM - draw plasma beams
	CL_AddPlayerBeams ()
	CL_AddExplosions ()
	CL_AddLasers ()
	# PMM - set up sustain
	CL_ProcessSustain()

def CL_PowerScreenModel(): # (returns struct model_s *), Q2PORT: Yamagi's cl_tempentities.c (group 11)

	return cl_mod_powerscreen
