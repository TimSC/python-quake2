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

This file implements the entity and network protocol parsing

=======================================================================
"""
from __future__ import annotations

import copy
import numpy as np
from client import cl_main, cl_fx, cl_view, ref
from common.header import common as common_h
from common.header import shared
from common import clientserver
from common import movemsg
from common import netchan
from client import cl_main
from client import cl_prediction
from client import cl_screen
from client import cl_view
from client.header import client as client_h

"""
#include "header/client.h"
#include "input/header/input.h"
"""
# PGM

vidref_val = shared.VIDREF_GL # int

"""
/*
=========================================================================

FRAME PARSING

=========================================================================
*/

#if 0

typedef struct
{
	int		modelindex;
	int		num; // entity number
	int		effects;
	vec3_t	origin;
	vec3_t	oldorigin;
	vec3_t	angles;
	qboolean present;
} projectile_t;
"""
MAX_PROJECTILES = 64


class projectile_t(object):

	def __init__(self):
		self.modelindex = 0
		self.num = 0
		self.effects = 0
		self.origin = np.zeros(3, dtype=np.float32)
		self.oldorigin = np.zeros(3, dtype=np.float32)
		self.angles = np.zeros(3, dtype=np.float32)
		self.present = False


cl_projectiles = [projectile_t() for _ in range(MAX_PROJECTILES)]


def CL_ClearProjectiles():
	for proj in cl_projectiles:
		proj.present = False

"""
=====================
CL_ParseProjectiles

Flechettes are passed as efficient temporary entities
=====================
"""
def CL_ParseProjectiles():
	count = movemsg.MSG_ReadByte(netchan.net_message)
	for _ in range(count):
		bits = [movemsg.MSG_ReadByte(netchan.net_message) for _ in range(5)]

		pr_proj = projectile_t()
		pr_proj.origin[0] = ((bits[0] + ((bits[1] & 15) << 8)) << 1) - 4096
		pr_proj.origin[1] = (((bits[1] >> 4) + (bits[2] << 4)) << 1) - 4096
		pr_proj.origin[2] = ((bits[3] + ((bits[4] & 15) << 8)) << 1) - 4096
		shared.VectorCopy(pr_proj.origin, pr_proj.oldorigin)

		if bits[4] & shared.EF_BLASTER:
			pr_proj.effects = shared.EF_BLASTER
		else:
			pr_proj.effects = 0

		old = False
		if bits[4] & 128:
			old = True
			bits = [movemsg.MSG_ReadByte(netchan.net_message) for _ in range(5)]
			pr_proj.oldorigin[0] = ((bits[0] + ((bits[1] & 15) << 8)) << 1) - 4096
			pr_proj.oldorigin[1] = (((bits[1] >> 4) + (bits[2] << 4)) << 1) - 4096
			pr_proj.oldorigin[2] = ((bits[3] + ((bits[4] & 15) << 8)) << 1) - 4096

		bits = [movemsg.MSG_ReadByte(netchan.net_message) for _ in range(3)]

		pr_proj.angles[0] = 360.0 * bits[0] / 256.0
		pr_proj.angles[1] = 360.0 * bits[1] / 256.0
		pr_proj.modelindex = bits[2]

		b = movemsg.MSG_ReadByte(netchan.net_message)
		pr_proj.num = (b & 0x7f)
		if b & 128:
			pr_proj.num |= movemsg.MSG_ReadByte(netchan.net_message) << 7

		pr_proj.present = True

		lastempty = -1
		for j in range(MAX_PROJECTILES):
			slot = cl_projectiles[j]
			if slot.modelindex:
				if slot.num == pr_proj.num:
					if not old:
						shared.VectorCopy(slot.origin, pr_proj.oldorigin)
					cl_projectiles[j] = pr_proj
					break
			else:
				lastempty = j
		else:
			j = MAX_PROJECTILES

		if j == MAX_PROJECTILES and lastempty != -1:
			cl_projectiles[lastempty] = pr_proj


def CL_AddProjectiles():
	ent = ref.entity_t()
	for pr in cl_projectiles:
		if pr.modelindex < 1:
			pr.present = False
			continue
		if not pr.present:
			pr.modelindex = 0
			continue

		ent.model = cl_main.cl.model_draw[pr.modelindex]
		for i in range(3):
			ent.origin[i] = ent.oldorigin[i] = (
				pr.oldorigin[i] + cl_main.cl.lerpfrac * (pr.origin[i] - pr.oldorigin[i])
			)
		if pr.effects & shared.EF_BLASTER and hasattr(cl_fx, "CL_BlasterTrail"):
			cl_fx.CL_BlasterTrail(pr.oldorigin, ent.origin)
			cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)
		if pr.effects & shared.EF_BLASTER and not hasattr(cl_fx, "CL_BlasterTrail"):
			cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)

		shared.VectorCopy(pr.angles, ent.angles)
		cl_view.V_AddEntity(ent)

from client import cl_main, cl_view, cl_cin, cl_fx, snd_dma, cl_tent
from linux import cd_linux, sys_linux, vid_so
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import movemsg
from common import collision
from common import netchan
from client import cl_console
from client import cl_download
from client import cl_inventory
from client import cl_main
from client import cl_screen
from client import cl_view
from client.header import client as client_h

pass
pass
"""
// cl_parse.c  -- parse a message received from the server

#include "client.h"
"""
svc_strings = \
[
	"svc_bad",

	"svc_muzzleflash",
	"svc_muzzlflash2",
	"svc_temp_entity",
	"svc_layout",
	"svc_inventory",

	"svc_nop",
	"svc_disconnect",
	"svc_reconnect",
	"svc_sound",
	"svc_print",
	"svc_stufftext",
	"svc_serverdata",
	"svc_configstring",
	"svc_spawnbaseline",	
	"svc_centerprint",
	"svc_download",
	"svc_playerinfo",
	"svc_packetentities",
	"svc_deltapacketentities",
	"svc_frame"]

while len(svc_strings) < 256:
	svc_strings.append(None)

"""
======================
CL_RegisterSounds
======================
"""
def CL_RegisterSounds ():

	#int		i;

	snd_dma.S_BeginRegistration ()
	cl_tent.CL_RegisterTEntSounds ()
	for i in range(1, shared.MAX_SOUNDS):
	
		if cl_main.cl.configstrings[shared.CS_SOUNDS+i] is None:
			break
		cl_main.cl.sound_precache[i] = snd_dma.S_RegisterSound (cl_main.cl.configstrings[shared.CS_SOUNDS+i])
		sys_linux.Sys_SendKeyEvents ()	# pump message loop
	
	snd_dma.S_EndRegistration ()


bitcounts = [] #int[32], just for protocol profilingf
for i in range(32):
	bitcounts.append(0)

def CL_ParseEntityBits (): # (unsigned *bits)

	# unsigned	b, total;
	# int			i;
	# int			number;

	total = movemsg.MSG_ReadByte (netchan.net_message)
	if total & common_h.U_MOREBITS1:
	
		b = movemsg.MSG_ReadByte (netchan.net_message)
		total |= b<<8
	
	if total & common_h.U_MOREBITS2:
	
		b = movemsg.MSG_ReadByte (netchan.net_message)
		total |= b<<16
	
	if total & common_h.U_MOREBITS3:
	
		b = movemsg.MSG_ReadByte (netchan.net_message)
		total |= b<<24
	

	# count the bits for net profiling
	for i in range(32):
		if total&(1<<i):
			bitcounts[i]+=1

	if total & common_h.U_NUMBER16:
		number = movemsg.MSG_ReadShort (netchan.net_message)
	else:
		number = movemsg.MSG_ReadByte (netchan.net_message)

	return number, total


	# ==================
	# CL_ParseDelta
	#
	# Can go from either a baseline or a previous packet_entity
	# ==================
def CL_ParseDelta (fromEnt, toEnt, number, bits): #entity_state_t *from, entity_state_t *to, int number, int bits

	# set everything to the state we are delta'ing from
	
	toEnt.copy(fromEnt)

	shared.VectorCopy (fromEnt.origin, toEnt.old_origin)
	toEnt.number = number

	if bits & common_h.U_MODEL:
		toEnt.modelindex = movemsg.MSG_ReadByte (netchan.net_message)
	if bits & common_h.U_MODEL2:
		toEnt.modelindex2 = movemsg.MSG_ReadByte (netchan.net_message)
	if bits & common_h.U_MODEL3:
		toEnt.modelindex3 = movemsg.MSG_ReadByte (netchan.net_message)
	if bits & common_h.U_MODEL4:
		toEnt.modelindex4 = movemsg.MSG_ReadByte (netchan.net_message)
		
	if bits & common_h.U_FRAME8:
		toEnt.frame = movemsg.MSG_ReadByte (netchan.net_message)
	if bits & common_h.U_FRAME16:
		toEnt.frame = movemsg.MSG_ReadShort (netchan.net_message)

	if (bits & common_h.U_SKIN8) and (bits & common_h.U_SKIN16):		# used for laser colors
		toEnt.skinnum = movemsg.MSG_ReadLong(netchan.net_message)
	elif bits & common_h.U_SKIN8:
		toEnt.skinnum = movemsg.MSG_ReadByte(netchan.net_message)
	elif bits & common_h.U_SKIN16:
		toEnt.skinnum = movemsg.MSG_ReadShort(netchan.net_message)

	if (bits & (common_h.U_EFFECTS8|common_h.U_EFFECTS16)) == (common_h.U_EFFECTS8|common_h.U_EFFECTS16):
		toEnt.effects = movemsg.MSG_ReadLong(netchan.net_message)
	elif bits & common_h.U_EFFECTS8:
		toEnt.effects = movemsg.MSG_ReadByte(netchan.net_message)
	elif bits & common_h.U_EFFECTS16:
		toEnt.effects = movemsg.MSG_ReadShort(netchan.net_message)

	if (bits & (common_h.U_RENDERFX8|common_h.U_RENDERFX16)) == (common_h.U_RENDERFX8|common_h.U_RENDERFX16):
		toEnt.renderfx = movemsg.MSG_ReadLong(netchan.net_message)
	elif bits & common_h.U_RENDERFX8:
		toEnt.renderfx = movemsg.MSG_ReadByte(netchan.net_message)
	elif bits & common_h.U_RENDERFX16:
		toEnt.renderfx = movemsg.MSG_ReadShort(netchan.net_message)

	if bits & common_h.U_ORIGIN1:
		toEnt.origin[0] = movemsg.MSG_ReadCoord (netchan.net_message)
	if bits & common_h.U_ORIGIN2:
		toEnt.origin[1] = movemsg.MSG_ReadCoord (netchan.net_message)
	if bits & common_h.U_ORIGIN3:
		toEnt.origin[2] = movemsg.MSG_ReadCoord (netchan.net_message)
		
	if bits & common_h.U_ANGLE1:
		toEnt.angles[0] = movemsg.MSG_ReadAngle(netchan.net_message)
	if bits & common_h.U_ANGLE2:
		toEnt.angles[1] = movemsg.MSG_ReadAngle(netchan.net_message)
	if bits & common_h.U_ANGLE3:
		toEnt.angles[2] = movemsg.MSG_ReadAngle(netchan.net_message)

	if bits & common_h.U_OLDORIGIN:
		toEnt.old_origin = movemsg.MSG_ReadPos (netchan.net_message)

	if bits & common_h.U_SOUND:
		toEnt.sound = movemsg.MSG_ReadByte (netchan.net_message)

	if bits & common_h.U_EVENT:
		toEnt.event = movemsg.MSG_ReadByte (netchan.net_message)
	else:
		toEnt.event = 0

	if bits & common_h.U_SOLID:
		toEnt.solid = movemsg.MSG_ReadShort (netchan.net_message)


	# ==================
	# CL_DeltaEntity
	#
	# Parses deltas from the given base and adds the resulting entity
	# to the current frame
	# ==================
def CL_DeltaEntity (frame, newnum, old, bits): #frame_t *, int, entity_state_t *, int

		# centity_t	*ent;
		# entity_state_t	*state;

	ent = cl_main.cl_entities[newnum]

	state = cl_main.cl_parse_entities[cl_main.cl.parse_entities & (client_h.MAX_PARSE_ENTITIES-1)]
	cl_main.cl.parse_entities+=1
	frame.num_entities+=1

	CL_ParseDelta (old, state, newnum, bits)

	# some data changes will force no lerping
	if (state.modelindex != ent.current.modelindex
		or state.modelindex2 != ent.current.modelindex2
		or state.modelindex3 != ent.current.modelindex3
		or state.modelindex4 != ent.current.modelindex4
		or abs(state.origin[0] - ent.current.origin[0]) > 512
		or abs(state.origin[1] - ent.current.origin[1]) > 512
		or abs(state.origin[2] - ent.current.origin[2]) > 512
		or state.event == shared.EV_PLAYER_TELEPORT
		or state.event == shared.EV_OTHER_TELEPORT
		):
	
		ent.serverframe = -99
	

	if ent.serverframe != cl_main.cl.frame.serverframe - 1:
		# wasn't in last update, so initialize some things
		ent.trailcount = 1024		# for diminishing rocket / grenade trails
		# duplicate the current state so lerping doesn't hurt anything
		ent.prev = copy.deepcopy(state) # ent->prev = *state;
		if state.event == shared.EV_OTHER_TELEPORT:
		
			shared.VectorCopy (state.origin, ent.prev.origin)
			shared.VectorCopy (state.origin, ent.lerp_origin)
		
		else:
		
			shared.VectorCopy (state.old_origin, ent.prev.origin)
			shared.VectorCopy (state.old_origin, ent.lerp_origin)
		
	
	else:
		# shuffle the last state to previous
		ent.prev = ent.current
	

	ent.serverframe = cl_main.cl.frame.serverframe
	ent.current = copy.deepcopy(state) # ent->current = *state;


	# ==================
	# CL_ParsePacketEntities
	#
	# An svc_packetentities has just been parsed, deal with the
	# rest of the data stream.
	# ==================
def CL_ParsePacketEntities (oldframe, newframe): #frame_t *, frame_t *

	# int			newnum;
	# int			bits;
	# entity_state_t	*oldstate;
	# int			oldindex, oldnum;

	newframe.parse_entities = cl_main.cl.parse_entities
	newframe.num_entities = 0

	# delta from the entities present in oldframe
	oldindex = 0
	oldnum = 0
	oldstate = None
	if oldframe is None:
		oldnum = 99999
	else:
	
		if oldindex >= oldframe.num_entities:
			oldnum = 99999
		else:
			oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client_h.MAX_PARSE_ENTITIES-1)]
			oldnum = oldstate.number

	while 1:

		newnum, bits = CL_ParseEntityBits ()

		if newnum >= shared.MAX_EDICTS:
			clientserver.Com_Error (shared.ERR_DROP,"CL_ParsePacketEntities: bad number:{}".format(newnum))

		if netchan.net_message.readcount > netchan.net_message.cursize:
			clientserver.Com_Error (shared.ERR_DROP,"CL_ParsePacketEntities: end of message")

		if newnum==0:
			break

		while oldnum < newnum:

			# one or more entities from the old packet are unchanged
			if cl_main.cl_shownet.value == 3:
				clientserver.Com_Printf ("   unchanged: {}\n".format(oldnum))

			CL_DeltaEntity (newframe, oldnum, oldstate, 0)
			
			oldindex+=1

			if oldindex >= oldframe.num_entities:
				oldnum = 99999
			else:
			
				oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client_h.MAX_PARSE_ENTITIES-1)]
				oldnum = oldstate.number
		

		if bits & common_h.U_REMOVE:
			# the entity present in oldframe is not in the current frame
			if cl_main.cl_shownet.value == 3:
				clientserver.Com_Printf ("   remove: {}\n".format(newnum))

			if oldnum != newnum:
				clientserver.Com_Printf ("U_REMOVE: oldnum != newnum\n")

			oldindex+=1

			if oldindex >= oldframe.num_entities:
				oldnum = 99999
			else:
			
				oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client_h.MAX_PARSE_ENTITIES-1)]
				oldnum = oldstate.number
			
			continue
		

		if oldnum == newnum:
			# delta from previous state
			if cl_main.cl_shownet.value == 3:
				clientserver.Com_Printf ("   delta: {}\n".format(newnum))

			CL_DeltaEntity (newframe, newnum, oldstate, bits)

			oldindex+=1

			if oldindex >= oldframe.num_entities:
				oldnum = 99999
			else:
			
				oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client_h.MAX_PARSE_ENTITIES-1)]
				oldnum = oldstate.number
			
			continue;
		

		if oldnum > newnum:
			# delta from baseline
			if cl_main.cl_shownet.value == 3:
				clientserver.Com_Printf ("   baseline: {}\n".format(newnum))
			CL_DeltaEntity (newframe, newnum, cl_main.cl_entities[newnum].baseline, bits)
			continue

	# any remaining entities in the old frame are copied over
	while oldnum != 99999:

		# one or more entities from the old packet are unchanged
		if cl_main.cl_shownet.value == 3:
			clientserver.Com_Printf ("   unchanged: {}\n".format(oldnum))

		CL_DeltaEntity (newframe, oldnum, oldstate, 0)
		
		oldindex+=1

		if oldindex >= oldframe.num_entities:
			oldnum = 99999
		else:
		
			oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client_h.MAX_PARSE_ENTITIES-1)]
			oldnum = oldstate.number
		


# ===================
# CL_ParsePlayerstate
# ===================
def CL_ParsePlayerstate (oldframe, newframe): #frame_t *, frame_t *

	# int			flags;
	# player_state_t	*state;
	# int			i;
	# int			statbits;

	# clear to old value before delta parsing
	if oldframe:
		newframe.playerstate = copy.deepcopy(oldframe.playerstate) # *state = oldframe->playerstate
	else:
		newframe.playerstate.clear()

	state = newframe.playerstate

	flags = movemsg.MSG_ReadShort (netchan.net_message)

	#
	# parse the pmove_state_t
	#
	if flags & common_h.PS_M_TYPE:
		state.pmove.pm_type = movemsg.MSG_ReadByte (netchan.net_message)


	if flags & common_h.PS_M_ORIGIN:

		state.pmove.origin[0] = movemsg.MSG_ReadShort (netchan.net_message)
		state.pmove.origin[1] = movemsg.MSG_ReadShort (netchan.net_message)
		state.pmove.origin[2] = movemsg.MSG_ReadShort (netchan.net_message)


	if flags & common_h.PS_M_VELOCITY:

		state.pmove.velocity[0] = movemsg.MSG_ReadShort (netchan.net_message)
		state.pmove.velocity[1] = movemsg.MSG_ReadShort (netchan.net_message)
		state.pmove.velocity[2] = movemsg.MSG_ReadShort (netchan.net_message)


	if flags & common_h.PS_M_TIME:
		state.pmove.pm_time = movemsg.MSG_ReadByte (netchan.net_message)

	if flags & common_h.PS_M_FLAGS:
		state.pmove.pm_flags = movemsg.MSG_ReadByte (netchan.net_message)

	if flags & common_h.PS_M_GRAVITY:
		state.pmove.gravity = movemsg.MSG_ReadShort (netchan.net_message)

	if flags & common_h.PS_M_DELTA_ANGLES:

		state.pmove.delta_angles[0] = movemsg.MSG_ReadShort (netchan.net_message)
		state.pmove.delta_angles[1] = movemsg.MSG_ReadShort (netchan.net_message)
		state.pmove.delta_angles[2] = movemsg.MSG_ReadShort (netchan.net_message)


	if cl_main.cl.attractloop:
		state.pmove.pm_type = shared.pmtype_t.PM_FREEZE.value		# demo playback

	#
	# parse the rest of the player_state_t
	#
	if flags & common_h.PS_VIEWOFFSET:

		state.viewoffset[0] = movemsg.MSG_ReadChar (netchan.net_message) * 0.25
		state.viewoffset[1] = movemsg.MSG_ReadChar (netchan.net_message) * 0.25
		state.viewoffset[2] = movemsg.MSG_ReadChar (netchan.net_message) * 0.25


	if flags & common_h.PS_VIEWANGLES:

		state.viewangles[0] = movemsg.MSG_ReadAngle16 (netchan.net_message)
		state.viewangles[1] = movemsg.MSG_ReadAngle16 (netchan.net_message)
		state.viewangles[2] = movemsg.MSG_ReadAngle16 (netchan.net_message)


	if flags & common_h.PS_KICKANGLES:

		state.kick_angles[0] = movemsg.MSG_ReadChar (netchan.net_message) * 0.25
		state.kick_angles[1] = movemsg.MSG_ReadChar (netchan.net_message) * 0.25
		state.kick_angles[2] = movemsg.MSG_ReadChar (netchan.net_message) * 0.25


	if flags & common_h.PS_WEAPONINDEX:

		state.gunindex = movemsg.MSG_ReadByte (netchan.net_message)


	if flags & common_h.PS_WEAPONFRAME:

		state.gunframe = movemsg.MSG_ReadByte (netchan.net_message)
		state.gunoffset[0] = movemsg.MSG_ReadChar (netchan.net_message)*0.25
		state.gunoffset[1] = movemsg.MSG_ReadChar (netchan.net_message)*0.25
		state.gunoffset[2] = movemsg.MSG_ReadChar (netchan.net_message)*0.25
		state.gunangles[0] = movemsg.MSG_ReadChar (netchan.net_message)*0.25
		state.gunangles[1] = movemsg.MSG_ReadChar (netchan.net_message)*0.25
		state.gunangles[2] = movemsg.MSG_ReadChar (netchan.net_message)*0.25


	if flags & common_h.PS_BLEND:

		state.blend[0] = movemsg.MSG_ReadByte (netchan.net_message)/255.0
		state.blend[1] = movemsg.MSG_ReadByte (netchan.net_message)/255.0
		state.blend[2] = movemsg.MSG_ReadByte (netchan.net_message)/255.0
		state.blend[3] = movemsg.MSG_ReadByte (netchan.net_message)/255.0


	if flags & common_h.PS_FOV:
		state.fov = movemsg.MSG_ReadByte (netchan.net_message)

	if flags & common_h.PS_RDFLAGS:
		state.rdflags = movemsg.MSG_ReadByte (netchan.net_message)

	# parse stats
	statbits = movemsg.MSG_ReadLong (netchan.net_message)
	for i in range(shared.MAX_STATS):
		if statbits & (1<<i):
			state.stats[i] = movemsg.MSG_ReadShort(netchan.net_message)


"""
==================
CL_FireEntityEvents

==================
"""
def CL_FireEntityEvents (frame): #frame_t *

	#entity_state_t		*s1;
	#int					pnum, num;

	for pnum in range(frame.num_entities):
	
		num = (frame.parse_entities + pnum)&(client_h.MAX_PARSE_ENTITIES-1)
		s1 = cl_main.cl_parse_entities[num]
		if s1.event:
			cl_fx.CL_EntityEvent (s1)

		# EF_TELEPORTER acts like an event, but is not cleared each frame
		if s1.effects & shared.EF_TELEPORTER:
			cl_fx.CL_TeleporterParticles (s1)
	


#================
#CL_ParseFrame
#================

def SHOWNET(s): #char *

	if cl_main.cl_shownet.value>=2:
		clientserver.Com_Printf ("{:3d}:{}\n".format(netchan.net_message.readcount-1, s))

# ====================
# CL_ParseServerMessage
# ====================
r"""
static void
CL_ShowNetCmd(int cmd)
{
	if (cmd < 0)
	{
		Com_Error(ERR_DROP, "%3i: unexpected message end",
			net_message.readcount - 1);
		return;
	}

	if (cl_shownet->value >= 2)
	{
		if (cmd >= ARRLEN(svc_strings))
		{
			Com_Printf("%3i:BAD CMD %i\n", net_message.readcount - 1, cmd);
			return;
		}

		SHOWNET(svc_strings[cmd]);
	}
}
"""

def CL_ParseFrame ():

	"""
	int			cmd;
	int			len;
	frame_t		*old;
	"""

	cl_main.cl.frame.clear()

#if 0
#	CL_ClearProjectiles(); // clear projectiles for new frame
#endif

	cl_main.cl.frame.serverframe = movemsg.MSG_ReadSLong (netchan.net_message)
	cl_main.cl.frame.deltaframe = movemsg.MSG_ReadSLong (netchan.net_message)
	cl_main.cl.frame.servertime = cl_main.cl.frame.serverframe*100

	# BIG HACK to let old demos continue to work
	if cl_main.cls.serverProtocol != 26:
		cl_main.cl.surpressCount = movemsg.MSG_ReadByte (netchan.net_message)

	if cl_main.cl_shownet.value == 3:
		clientserver.Com_Printf ("   frame:{}  delta:{}\n".format(cl_main.cl.frame.serverframe,
			cl_main.cl.frame.deltaframe))

	# If the frame is delta compressed from data that we
	# no longer have available, we must suck up the rest of
	# the frame, but not use it, then ask for a non-compressed
	# message 
	if cl_main.cl.frame.deltaframe <= 0:
	
		cl_main.cl.frame.valid = True		# uncompressed frame
		old = None
		cl_main.cls.demowaiting = False	# we can start recording now
	
	else:
		old = cl_main.cl.frames[cl_main.cl.frame.deltaframe & common_h.UPDATE_MASK]

		if not old.valid:
			# should never happen
			clientserver.Com_Printf ("Delta from invalid frame (not supposed to happen!).\n");
		
		if old.serverframe != cl_main.cl.frame.deltaframe:
			# The frame that the server did the delta from
			# is too old, so we can't reconstruct it properly.
			clientserver.Com_Printf ("Delta frame too old.\n")
		
		elif cl_main.cl.parse_entities - old.parse_entities > client_h.MAX_PARSE_ENTITIES-128:
		
			clientserver.Com_Printf ("Delta parse_entities too old.\n")
		
		else:
			cl_main.cl.frame.valid = True	# valid delta parse
	
	
	# clamp time 
	if cl_main.cl.time > cl_main.cl.frame.servertime:
		cl_main.cl.time = cl_main.cl.frame.servertime
	elif cl_main.cl.time < cl_main.cl.frame.servertime - 100:
		cl_main.cl.time = cl_main.cl.frame.servertime - 100

	# read areabits
	length = movemsg.MSG_ReadByte (netchan.net_message)
	cl_main.cl.frame.areabits = movemsg.MSG_ReadData (netchan.net_message, length)

	# read playerinfo
	cmd = movemsg.MSG_ReadByte (netchan.net_message)
	SHOWNET(svc_strings[cmd])
	if cmd != common_h.svc_ops_e.svc_playerinfo.value:
		clientserver.Com_Error (shared.ERR_DROP, "CL_ParseFrame: not playerinfo")
	CL_ParsePlayerstate (old, cl_main.cl.frame)

	# read packet entities
	cmd = movemsg.MSG_ReadByte (netchan.net_message)
	SHOWNET(svc_strings[cmd])
	if cmd != common_h.svc_ops_e.svc_packetentities.value:
		clientserver.Com_Error (shared.ERR_DROP, "CL_ParseFrame: not packetentities")
	CL_ParsePacketEntities (old, cl_main.cl.frame)

	# save the frame off in the backup array for later delta comparisons
	cl_main.cl.frames[cl_main.cl.frame.serverframe & common_h.UPDATE_MASK] = copy.copy(cl_main.cl.frame)

	if cl_main.cl.frame.valid:
	
		# getting a valid frame message ends the connection process
		if cl_main.cls.state != client_h.connstate_t.ca_active:
		
			cl_main.cls.state = client_h.connstate_t.ca_active
			cl_main.cl.force_refdef = True
			cl_main.cl.predicted_origin[0] = cl_main.cl.frame.playerstate.pmove.origin[0]*0.125
			cl_main.cl.predicted_origin[1] = cl_main.cl.frame.playerstate.pmove.origin[1]*0.125
			cl_main.cl.predicted_origin[2] = cl_main.cl.frame.playerstate.pmove.origin[2]*0.125
			shared.VectorCopy (cl_main.cl.frame.playerstate.viewangles, cl_main.cl.predicted_angles)
			if cl_main.cls.disable_servercount != cl_main.cl.servercount \
				and cl_main.cl.refresh_prepped:
				cl_screen.SCR_EndLoadingPlaque ()	# get rid of loading plaque
		
		cl_main.cl.sound_prepped = True	# can start mixing ambient sounds
	
		# fire entity events
		CL_FireEntityEvents (cl_main.cl.frame)
		cl_prediction.CL_CheckPredictionError ()
	


"""
==========================================================================

INTERPOLATE BETWEEN FRAMES TO GET RENDERING PARMS

==========================================================================

"""

def S_RegisterSexedModel (ent, base):
	model = ""
	n = shared.CS_PLAYERSKINS + ent.number - 1
	if 0 <= n < len(cl_main.cl.configstrings):
		config = cl_main.cl.configstrings[n]
		if config:
			idx = config.find('\\')
			if idx != -1:
				model_name = config[idx + 1:]
				end = model_name.find('/')
				if end != -1:
					model = model_name[:end]
	if not model:
		model = "male"

	base_name = base[1:] if base and len(base) > 1 else (base or "")
	re_interface = getattr(cl_main.vid_so, 're', None)
	if not re_interface:
		return None

	path = f"players/{model}/{base_name}"
	mdl = re_interface.RegisterModel(path)
	if not mdl:
		path = f"players/{model}/weapon.md2"
		mdl = re_interface.RegisterModel(path)
		if not mdl:
			path = f"players/male/{base_name}"
			mdl = re_interface.RegisterModel(path)
			if not mdl:
				mdl = re_interface.RegisterModel("players/male/weapon.md2")
	return mdl

bfg_lightramp = [300, 400, 600, 300, 150, 75] #static int [6]


"""
===============
CL_GetEntitySoundOrigin

Called to get the sound spatialization origin
===============
"""
def CL_GetEntitySoundOrigin (ent: int): # vec3_t

	org = np.zeros((3,), dtype=np.float32)
	#centity_t	*old;

	if ent < 0 or ent >= shared.MAX_EDICTS:
		clientserver.Com_Error (shared.ERR_DROP, "CL_GetEntitySoundOrigin: bad ent")
	old = cl_main.cl_entities[ent]
	shared.VectorCopy (old.lerp_origin, org)

	# FIXME: bmodel issues...

	return org

"""
=====================================================================

  SERVER CONNECTING MESSAGES

=====================================================================
"""

"""
==================
CL_ParseServerData
==================
"""
def CL_ParseServerData ():

	clientserver.Com_DPrintf ("Serverdata packet received.\n")

	cl_main.CL_ClearState ()
	cl_main.cls.state = client_h.connstate_t.ca_connected

	protocol = movemsg.MSG_ReadLong (netchan.net_message)
	cl_main.cls.serverProtocol = protocol

	if not (clientserver.Com_ServerState() and common_h.PROTOCOL_VERSION == 34):
		if protocol != common_h.PROTOCOL_VERSION:
			clientserver.Com_Error (common_h.ERR_DROP, "Server returned version {}, not {}".format(protocol, common_h.PROTOCOL_VERSION))

	cl_main.cl.servercount = movemsg.MSG_ReadLong (netchan.net_message)
	cl_main.cl.attractloop = movemsg.MSG_ReadByte (netchan.net_message)

	gamedir = movemsg.MSG_ReadString (netchan.net_message)
	cl_main.cl.gamedir = gamedir[:shared.MAX_QPATH]

	fsvar = filesystem.fs_gamedirvar
	if gamedir:
		if not fsvar or not fsvar.string or fsvar.string != gamedir:
			cvar.Cvar_Set ("game", gamedir)
	elif fsvar and fsvar.string:
		cvar.Cvar_Set ("game", gamedir)

	cl_main.cl.playernum = movemsg.MSG_ReadSShort (netchan.net_message)

	level_name = movemsg.MSG_ReadString (netchan.net_message)

	if cl_main.cl.playernum == -1:
		cl_cin.SCR_PlayCinematic (level_name)
	else:
		clientserver.Com_Printf ("\n\n\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n\n")
		clientserver.Com_Printf ("{}{}\n".format(chr(2), level_name))
		cl_main.cl.refresh_prepped = False
	


"""
==================
CL_ParseBaseline
==================
"""
def CL_ParseBaseline ():

	"""
	entity_state_t	*es;
	int				bits;
	int				newnum;
	entity_state_t	nullstate;
	"""

	nullstate = shared.entity_state_t()

	newnum, bits = CL_ParseEntityBits ()
	es = cl_main.cl_entities[newnum].baseline
	CL_ParseDelta (nullstate, es, newnum, bits)

"""
================
CL_LoadClientinfo

================
"""
def CL_LoadClientinfo (ci, s): #clientinfo_t *, char *

	"""
	int i;
	char		*t;
	char		model_name[MAX_QPATH];
	char		skin_name[MAX_QPATH];
	char		model_filename[MAX_QPATH];
	char		skin_filename[MAX_QPATH];
	char		weapon_filename[MAX_QPATH];
	"""

	if s is None: # unset configstrings are None rather than ""
		s = ""

	ci.cinfo = s[:shared.MAX_QPATH-1] # strncpy(ci->cinfo, s, sizeof(ci->cinfo)); ci->cinfo[sizeof(ci->cinfo)-1] = 0;

	# isolate the player's name
	ci.name = s[:shared.MAX_QPATH-1]
	t = s.find ("\\")
	if t != -1:
	
		ci.name = ci.name[:t] # ci->name[t-s] = 0;
		s = s[t+1:]
	
	if cl_main.cl_noskins.value or len(s) == 0:
	
		model_filename = "players/male/tris.md2"
		weapon_filename = "players/male/weapon.md2"
		skin_filename = "players/male/grunt.pcx"
		ci.iconname = "/players/male/grunt_i.pcx"
		ci.model = vid_so.re.RegisterModel (model_filename)
		for i in range(client_h.MAX_CLIENTWEAPONMODELS): # memset(ci->weaponmodel, 0, sizeof(ci->weaponmodel));
			ci.weaponmodel[i] = None
		ci.weaponmodel[0] = vid_so.re.RegisterModel (weapon_filename)
		ci.skin = vid_so.re.RegisterSkin (skin_filename)
		ci.icon = vid_so.re.RegisterPic (ci.iconname)
	
	else:
	
		# isolate the model name
		model_name = s
		t = model_name.find("/")
		if t == -1:
			t = model_name.find("\\")
		if t == -1:
			t = 0
		model_name = model_name[:t] # *t = 0;

		# isolate the skin name
		skin_name = s[len(model_name) + 1:]

		# model file
		model_filename = "players/{}/tris.md2".format(model_name)
		ci.model = vid_so.re.RegisterModel (model_filename)
		if not ci.model:
		
			model_name = "male"
			model_filename = "players/male/tris.md2"
			ci.model = vid_so.re.RegisterModel (model_filename)
		
		# skin file
		skin_filename = "players/{}/{}.pcx".format(model_name, skin_name)
		ci.skin = vid_so.re.RegisterSkin (skin_filename)

		# if we don't have the skin and the model wasn't male,
		# see if the male has it (this is for CTF's skins)
		if not ci.skin and shared_c.Q_stricmp(model_name, "male"):
		
			# change model to male
			model_name = "male"
			model_filename = "players/male/tris.md2"
			ci.model = vid_so.re.RegisterModel (model_filename)

			# see if the skin exists for the male model
			skin_filename = "players/{}/{}.pcx".format(model_name, skin_name)
			ci.skin = vid_so.re.RegisterSkin (skin_filename)
		
		# if we still don't have a skin, it means that the male model didn't have
		# it, so default to grunt
		if not ci.skin:
			# see if the skin exists for the male model
			skin_filename = "players/{}/grunt.pcx".format(model_name)
			ci.skin = vid_so.re.RegisterSkin (skin_filename)
		
		# weapon file
		for i in range(cl_view.num_cl_weaponmodels):
			weapon_filename = "players/{}/{}".format(model_name, cl_view.cl_weaponmodels[i])
			ci.weaponmodel[i] = vid_so.re.RegisterModel(weapon_filename)
			if not ci.weaponmodel[i] and model_name == "cyborg":
				# try male
				weapon_filename = "players/male/{}".format(cl_view.cl_weaponmodels[i])
				ci.weaponmodel[i] = vid_so.re.RegisterModel(weapon_filename)
			
			if not cl_main.cl_vwep.value:
				break # only one when vwep is off
		
		# icon file
		ci.iconname = "/players/{}/{}_i.pcx".format(model_name, skin_name)
		ci.icon = vid_so.re.RegisterPic (ci.iconname)
	
	# must have loaded all data types to be valud
	if not ci.skin or not ci.icon or not ci.model or not ci.weaponmodel[0]:
	
		ci.skin = None
		ci.icon = None
		ci.model = None
		ci.weaponmodel[0] = None
		return
	

"""
================
CL_ParseClientinfo

Load the skin, icon, and model for a client
================
"""
def CL_ParseClientinfo (player): #int

	#char			*s;
	#clientinfo_t	*ci;

	s = cl_main.cl.configstrings[player+shared.CS_PLAYERSKINS]

	ci = cl_main.cl.clientinfo[player]

	CL_LoadClientinfo (ci, s)

# =================
# CL_ParseConfigString
# =================
def CL_ParseConfigString ():

		# int		i;
		# char	*s;
		# char	olds[MAX_QPATH];


	i = movemsg.MSG_ReadShort (netchan.net_message)
	if i < 0 or i >= shared.MAX_CONFIGSTRINGS:
		clientserver.Com_Error (common_h.ERR_DROP, "configstring > MAX_CONFIGSTRINGS")
	s = movemsg.MSG_ReadString (netchan.net_message)

	olds = cl_main.cl.configstrings[i] or ""
	cl_main.cl.configstrings[i] = s

	if i >= shared.CS_LIGHTS and i < shared.CS_LIGHTS + shared.MAX_LIGHTSTYLES:
		cl_fx.CL_SetLightstyle (i - shared.CS_LIGHTS)

	elif i == shared.CS_CDTRACK:
		if cl_main.cl.refresh_prepped:
			track = 0
			try:
				track = int (cl_main.cl.configstrings[shared.CS_CDTRACK] or "")
			except ValueError:
				pass
			cd_linux.CDAudio_Play (track, True)

	elif i >= shared.CS_MODELS and i < shared.CS_MODELS + shared.MAX_MODELS:
		if cl_main.cl.refresh_prepped:
			model_name = cl_main.cl.configstrings[i]
			if model_name:
				cl_main.cl.model_draw[i - shared.CS_MODELS] = vid_so.re.RegisterModel (model_name)
				if model_name[0] == '*':
					cl_main.cl.model_clip[i - shared.CS_MODELS] = collision.CM_InlineModel (model_name)
				else:
					cl_main.cl.model_clip[i - shared.CS_MODELS] = None

	elif i >= shared.CS_SOUNDS and i < shared.CS_SOUNDS + shared.MAX_SOUNDS:
		if cl_main.cl.refresh_prepped:
			sound_name = cl_main.cl.configstrings[i]
			if sound_name:
				cl_main.cl.sound_precache[i - shared.CS_SOUNDS] = snd_dma.S_RegisterSound (sound_name)

	elif i >= shared.CS_IMAGES and i < shared.CS_IMAGES + shared.MAX_IMAGES:
		if cl_main.cl.refresh_prepped:
			image_name = cl_main.cl.configstrings[i]
			if image_name:
				cl_main.cl.image_precache[i - shared.CS_IMAGES] = vid_so.re.RegisterPic (image_name)

	elif i >= shared.CS_PLAYERSKINS and i < shared.CS_PLAYERSKINS + shared.MAX_CLIENTS:
		if cl_main.cl.refresh_prepped and olds != s:
			CL_ParseClientinfo (i - shared.CS_PLAYERSKINS)
	


# ======================================================================
# ACTION MESSAGES
# ======================================================================

# ==================
# CL_ParseStartSoundPacket
# ==================
def CL_ParseStartSoundPacket():

	# vec3_t  pos_v;
	# float	*pos;
	# int 	channel, ent;
	# int 	sound_num;
	# float 	volume;
	# float 	attenuation;
	# int		flags;
	# float	ofs;


	flags = movemsg.MSG_ReadByte (netchan.net_message)
	sound_num = movemsg.MSG_ReadByte (netchan.net_message)

	if flags & common_h.SND_VOLUME:
		volume = movemsg.MSG_ReadByte (netchan.net_message) / 255.0
	else:
		volume = common_h.DEFAULT_SOUND_PACKET_VOLUME
	
	if flags & common_h.SND_ATTENUATION:
		attenuation = movemsg.MSG_ReadByte (netchan.net_message) / 64.0
	else:
		attenuation = common_h.DEFAULT_SOUND_PACKET_ATTENUATION

	if flags & common_h.SND_OFFSET:
		ofs = movemsg.MSG_ReadByte (netchan.net_message) / 1000.0
	else:
		ofs = 0

	if flags & common_h.SND_ENT:
		# entity reletive
		channel = movemsg.MSG_ReadShort(netchan.net_message)
		ent = channel>>3
		if ent > shared.MAX_EDICTS:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseStartSoundPacket: ent = {}".format(ent))

		channel &= 7
	
	else:
	
		ent = 0
		channel = 0
	

	if flags & common_h.SND_POS:
		# positioned in space
		pos_v = movemsg.MSG_ReadPos (netchan.net_message)
 
		pos = pos_v
	
	else:	# use entity number
		pos = None

	if sound_num < 0 or sound_num >= len (cl_main.cl.sound_precache):
		return

	if not cl_main.cl.sound_precache[sound_num]:
		return

	snd_dma.S_StartSound (pos, ent, channel, cl_main.cl.sound_precache[sound_num], volume, attenuation, ofs)
	   


def CL_ParseServerMessage ():

	#int			cmd;
	#char		*s;
	#int			i;

	#
	# if recording demos, copy the message out
	#
	if cl_main.cl_shownet.value == 1:
		clientserver.Com_Printf ("{:d} ".format(netchan.net_message.cursize))
	elif cl_main.cl_shownet.value >= 2:
		clientserver.Com_Printf ("------------------\n")

	#
	# parse the message
	#
	while True:
		if netchan.net_message.readcount > netchan.net_message.cursize:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseServerMessage: Bad server message")
			break

		cmd_raw = movemsg.MSG_ReadByte (netchan.net_message)
		if cmd_raw == -1:
			SHOWNET("END OF MESSAGE")
			break

		if cl_main.cl_shownet.value>=2:

			if not svc_strings[cmd_raw]:
				clientserver.Com_Printf ("{:3d}:BAD CMD {:d}".format(netchan.net_message.readcount-1,cmd_raw))
			else:
				SHOWNET(svc_strings[cmd_raw])

		try:
			cmdval = common_h.svc_ops_e (cmd_raw)
		except ValueError:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseServerMessage: Illegible server message")
			break

		if cmdval == common_h.svc_ops_e.svc_nop:
			pass
		elif cmdval == common_h.svc_ops_e.svc_disconnect:
			clientserver.Com_Error (shared.ERR_DISCONNECT,"Server disconnected\n")
		elif cmdval == common_h.svc_ops_e.svc_reconnect:
			clientserver.Com_Printf ("Server disconnected, reconnecting\n")
			if cl_main.cls.download:
				cl_main.cls.download.close ()
				cl_main.cls.download = None

			cl_main.cls.state = client_h.connstate_t.ca_connecting
			cl_main.cls.connect_time = -99999
		elif cmdval == common_h.svc_ops_e.svc_print:
			i = movemsg.MSG_ReadByte (netchan.net_message)
			if i == shared.PRINT_CHAT:
				snd_dma.S_StartLocalSound ("misc/talk.wav")
				cl_console.con.ormask = 128

			clientserver.Com_Printf (movemsg.MSG_ReadString(netchan.net_message))
			cl_console.con.ormask = 0
		elif cmdval == common_h.svc_ops_e.svc_centerprint:
			cl_screen.SCR_CenterPrint (movemsg.MSG_ReadString(netchan.net_message))
		elif cmdval == common_h.svc_ops_e.svc_stufftext:
			s = movemsg.MSG_ReadString(netchan.net_message)
			clientserver.Com_DPrintf ("stufftext: {}\n".format(s))
			cmdparser.Cbuf_AddText (s)
		elif cmdval == common_h.svc_ops_e.svc_serverdata:
			cmdparser.Cbuf_Execute ()
			CL_ParseServerData ()
		elif cmdval == common_h.svc_ops_e.svc_configstring:
			CL_ParseConfigString ()
		elif cmdval == common_h.svc_ops_e.svc_sound:
			CL_ParseStartSoundPacket()
		elif cmdval == common_h.svc_ops_e.svc_spawnbaseline:
			CL_ParseBaseline ()
		elif cmdval == common_h.svc_ops_e.svc_temp_entity:
			cl_tent.CL_ParseTEnt ()
		elif cmdval == common_h.svc_ops_e.svc_muzzleflash:
			cl_fx.CL_ParseMuzzleFlash ()
		elif cmdval == common_h.svc_ops_e.svc_muzzleflash2:
			cl_fx.CL_ParseMuzzleFlash2 ()
		elif cmdval == common_h.svc_ops_e.svc_download:
			cl_download.CL_ParseDownload ()
		elif cmdval == common_h.svc_ops_e.svc_frame:
			CL_ParseFrame ()
		elif cmdval == common_h.svc_ops_e.svc_inventory:
			cl_inventory.CL_ParseInventory ()
		elif cmdval == common_h.svc_ops_e.svc_layout:
			s = movemsg.MSG_ReadString(netchan.net_message)
			cl_main.cl.layout = s
		elif cmdval in [common_h.svc_ops_e.svc_playerinfo, common_h.svc_ops_e.svc_packetentities, common_h.svc_ops_e.svc_deltapacketentities]:
			clientserver.Com_Error (common_h.ERR_DROP, "Out of place frame data")
		else:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseServerMessage: Illegible server message\n")
	cl_screen.CL_AddNetgraph ()

	#
	# we don't know if it is ok to save a demo message until
	# after we have parsed the frame
	#
	if cl_main.cls.demorecording and not cl_main.cls.demowaiting:
		cl_main.CL_WriteDemoMessage ()
