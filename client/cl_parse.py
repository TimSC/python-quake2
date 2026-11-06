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

from client.input import sdl2

import copy
import numpy as np
from client import cl_main, cl_view, ref
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

from client import cl_main, cl_view, cl_cin, snd_dma
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
from client.sound import ogg
from client.vid import vid
from client import cl_effects
from client import cl_lights
from client import cl_tempentities

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
def CL_RegisterSounds(): #
	# FIXME c2py: unresolved IN_Update

	"""
	int i;
	"""

	snd_dma.S_BeginRegistration()
	cl_tempentities.CL_RegisterTEntSounds()
	for i in range(1, shared.MAX_SOUNDS):

		if not cl_main.cl.configstrings[shared.CS_SOUNDS + i]: # !cl.configstrings[CS_SOUNDS + i][0]

			break


		cl_main.cl.sound_precache[i] = snd_dma.S_RegisterSound(cl_main.cl.configstrings[shared.CS_SOUNDS + i])
		sdl2.IN_Update()


	snd_dma.S_EndRegistration()


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
		if total&(1<<i): # 1u << i
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
CL_ParseDelta_es_nullstate = shared.entity_state_t() #static const entity_state_t, in CL_ParseDelta

def CL_ParseDelta (fromEnt, toEnt, number, bits): #const entity_state_t *from, entity_state_t *to, int number, int bits

	#entity_state_t dummy;

	if fromEnt is None:

		fromEnt = CL_ParseDelta_es_nullstate


	if toEnt is None:

		toEnt = shared.entity_state_t() # to = &dummy;


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
		movemsg.MSG_ReadPos(netchan.net_message, toEnt.old_origin)

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
def CL_DeltaEntity (frame, newnum, old, bits): #frame_t *, int, const entity_state_t *, int

	#centity_t dummy, *ent;
	#entity_state_t *state;

	ent = cl_main.CL_AllocEntity(newnum)
	if not ent:

		ent = client_h.centity_t() # memset(&dummy, 0, sizeof(dummy)); ent = &dummy;

	state = cl_main.cl_parse_entities[cl_main.cl.parse_entities & (client_h.MAX_PARSE_ENTITIES-1)]
	cl_main.cl.parse_entities+=1
	frame.num_entities+=1

	CL_ParseDelta (old, state, newnum, bits)

	# some data changes will force no lerping
	if ((state.modelindex != ent.current.modelindex) or
		(state.modelindex2 != ent.current.modelindex2) or
		(state.modelindex3 != ent.current.modelindex3) or
		(state.modelindex4 != ent.current.modelindex4) or
		(state.event == shared.EV_PLAYER_TELEPORT) or
		(state.event == shared.EV_OTHER_TELEPORT) or
		(abs(int(state.origin[0] - ent.current.origin[0])) > 512) or
		(abs(int(state.origin[1] - ent.current.origin[1])) > 512) or
		(abs(int(state.origin[2] - ent.current.origin[2])) > 512)
		):
	
		ent.serverframe = -99
	

	if ent.serverframe != cl_main.cl.frame.serverframe - 1:
		# wasn't in last update, so initialize some things
		ent.trailcount = 1024		# for diminishing rocket / grenade trails
		# duplicate the current state so lerping doesn't hurt anything
		ent.prev = copy.deepcopy(state) # ent->prev = *state;

		ent.serverframe_created = cl_main.cl.frame.serverframe

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

	#unsigned int newnum;
	#unsigned bits;
	#centity_t *ent;
	#entity_state_t *oldstate = NULL;
	#int oldindex, oldnum;

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

		if newnum > client_h.MAX_CL_ENTNUM:

			clientserver.Com_Error (shared.ERR_DROP, "%s: bad entity %d > %d\n", "CL_ParsePacketEntities", newnum, client_h.MAX_CL_ENTNUM)
			return


		if netchan.net_message.readcount > netchan.net_message.cursize:

			clientserver.Com_Error (shared.ERR_DROP, "%s: end of message", "CL_ParsePacketEntities")
			return

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
				clientserver.Com_Printf ("U_REMOVE: oldnum != newnum: %d %d\n", oldnum, newnum)

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
			ent = cl_main.CL_AllocEntity(newnum)
			CL_DeltaEntity (newframe, newnum, ent.baseline if ent else None, bits)
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
		state.fov = float(movemsg.MSG_ReadByte (netchan.net_message))

	if flags & common_h.PS_RDFLAGS:
		state.rdflags = movemsg.MSG_ReadByte (netchan.net_message)

	# parse stats
	statbits = movemsg.MSG_ReadLong (netchan.net_message)
	for i in range(shared.MAX_STATS):
		if statbits & (1<<i): # 1u << i
			state.stats[i] = movemsg.MSG_ReadShort(netchan.net_message)


"""
==================
CL_FireEntityEvents

==================
"""
def CL_FireEntityEvents(frame): #frame_t * (static)

	"""
	int pnum;
	"""

	for pnum in range(frame.num_entities):

		#entity_state_t *s1;
		#int num;
		num = (frame.parse_entities + pnum) & (client_h.MAX_PARSE_ENTITIES - 1)
		s1 = cl_main.cl_parse_entities[num]
		if s1.event:

			cl_effects.CL_EntityEvent(s1)


		if s1.effects & shared.EF_TELEPORTER:

			cl_effects.CL_TeleporterParticles(s1)
	


#================
#CL_ParseFrame
#================

def SHOWNET(s): #char *

	if cl_main.cl_shownet.value>=2:
		clientserver.Com_Printf ("{:3d}:{}\n".format(netchan.net_message.readcount-1, s))

# ====================
# CL_ParseServerMessage
# ====================
def CL_ShowNetCmd(cmd): #int (static)

	if cmd < 0:

		clientserver.Com_Error(shared.ERR_DROP, "%3i: unexpected message end", netchan.net_message.readcount - 1)
		return


	if cl_main.cl_shownet.value >= 2:

		if cmd >= len(svc_strings):

			clientserver.Com_Printf("%3i:BAD CMD %i\n", netchan.net_message.readcount - 1, cmd)
			return


		SHOWNET(svc_strings[cmd])

def CL_ParseFrame ():

	"""
	int			cmd;
	int			len;
	frame_t		*old;
	"""

	cl_main.cl.frame.clear() # memset(&cl.frame, 0, sizeof(cl.frame));

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
	CL_ShowNetCmd(cmd)

	if cmd != common_h.svc_ops_e.svc_playerinfo.value:

		clientserver.Com_Error (shared.ERR_DROP, "%s: 0x%X not playerinfo",
			"CL_ParseFrame", cmd)
		return


	CL_ParsePlayerstate (old, cl_main.cl.frame)

	# read packet entities
	cmd = movemsg.MSG_ReadByte (netchan.net_message)
	CL_ShowNetCmd(cmd)

	if cmd != common_h.svc_ops_e.svc_packetentities.value:

		clientserver.Com_Error (shared.ERR_DROP, "%s: 0x%X not packetentities",
			"CL_ParseFrame", cmd)
		return


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

			cl_main.cl.sound_prepped = True

			if cl_main.paused_at_load:

				if cl_main.cl_loadpaused.value == 1:

					cvar.Cvar_Set("paused", "0")


				cl_main.paused_at_load = False



		# fire entity events
		CL_FireEntityEvents (cl_main.cl.frame)

		if not (not cl_main.cl_predict.value or
			  (cl_main.cl.frame.playerstate.pmove.pm_flags &
			   shared.PMF_NO_PREDICTION)):

			cl_prediction.CL_CheckPredictionError()
	


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

	# Q2PORT: Yamagi's bounds check (sound.c, group 13): entities the client hasn't allocated are at the origin
	lerp_origin = cl_main.cl_entities[ent].lerp_origin if ((ent >= 0) and (ent < cl_main.cl_numentities)) else \
		shared_c.vec3_origin
	shared.VectorCopy (lerp_origin, org)

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
def CL_ParseServerData(): #void

	#extern cvar_t *fs_gamedirvar;
	"""
	char *str;
	int i;
	"""

	# Clear all key states
	sdl2.In_FlushQueue()

	clientserver.Com_DPrintf("Serverdata packet received.\n")

	# wipe the client_state_t struct
	cl_main.CL_ClearState()
	cl_main.cls.state = client_h.connstate_t.ca_connected

	# parse protocol version number
	i = movemsg.MSG_ReadLong(netchan.net_message)
	cl_main.cls.serverProtocol = i

	# another demo hack
	if clientserver.Com_ServerState() and (common_h.PROTOCOL_VERSION == 34):

		pass

	elif i != common_h.PROTOCOL_VERSION:

		clientserver.Com_Error(shared.ERR_DROP, "Server returned version %i, not %i",
				i, common_h.PROTOCOL_VERSION)
		return


	cl_main.cl.servercount = movemsg.MSG_ReadLong(netchan.net_message)
	cl_main.cl.attractloop = movemsg.MSG_ReadByte(netchan.net_message)

	# game directory
	str_ = movemsg.MSG_ReadString(netchan.net_message)
	cl_main.cl.gamedir = str_[:shared.MAX_QPATH - 1] # Q_strlcpy

	# set gamedir
	fs_gamedirvar = filesystem.fs_gamedirvar
	if ((str_ and (not fs_gamedirvar.string or not fs_gamedirvar.string[:1] or
		  fs_gamedirvar.string != str_)) or
		(not str_ and (fs_gamedirvar.string is not None and not fs_gamedirvar.string))):

		cvar.Cvar_Set("game", str_)


	# parse player entity number
	cl_main.cl.playernum = movemsg.MSG_ReadSShort(netchan.net_message)

	# get the full level name
	str_ = movemsg.MSG_ReadString(netchan.net_message)

	if cl_main.cl.playernum == -1:

		# playing a cinematic or showing a pic, not a level
		cl_cin.SCR_PlayCinematic(str_)

	else:

		# seperate the printfs so the server
		# message can have a color
		clientserver.Com_Printf("\n\n\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n\n")
		clientserver.Com_Printf("%c%s\n", 2, str_)

		# need to prep refresh at next oportunity
		cl_main.cl.refresh_prepped = False


"""
==================
CL_ParseBaseline
==================
"""
def CL_ParseBaseline ():

	"""
	unsigned bits;
	int newnum;
	centity_t *ent;
	"""

	newnum, bits = CL_ParseEntityBits ()
	ent = cl_main.CL_AllocEntity(newnum)
	CL_ParseDelta (None, ent.baseline if ent else None, newnum, bits)

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

	ci.cinfo = s[:shared.MAX_QPATH-1] # Q_strlcpy(ci->cinfo, s, sizeof(ci->cinfo));
	s = ci.cinfo

	# isolate the player's name
	ci.name = s[:shared.MAX_QPATH-1] # Q_strlcpy(ci->name, s, sizeof(ci->name));
	t = s.find ("\\")
	if t != -1:
	
		ci.name = ci.name[:t] # ci->name[t-s] = 0;
		s = s[t+1:]
	
	if cl_main.cl_noskins.value or (len(s) == 0): # *s == 0
	
		model_filename = "players/male/tris.md2"
		weapon_filename = "players/male/weapon.md2"
		skin_filename = "players/male/grunt.pcx"
		ci.iconname = "/players/male/grunt_i.pcx"
		ci.model = vid.R_RegisterModel (model_filename)
		for i in range(client_h.MAX_CLIENTWEAPONMODELS): # memset(ci->weaponmodel, 0, sizeof(ci->weaponmodel));
			ci.weaponmodel[i] = None
		ci.weaponmodel[0] = vid.R_RegisterModel (weapon_filename)
		ci.skin = vid.R_RegisterSkin (skin_filename)
		ci.icon = vid.Draw_FindPic (ci.iconname)
	
	else:
	
		# isolate the model name
		model_name = s[:shared.MAX_QPATH-1] # Q_strlcpy(model_name, s, sizeof(model_name));
		t = model_name.find("/")
		if t == -1:
			t = model_name.find("\\")
		if t == -1:
			t = 0
		model_name = model_name[:t] # *t = 0;

		# isolate the skin name
		skin_name = s[len(model_name) + 1:][:shared.MAX_QPATH-1] # Q_strlcpy

		# model file
		model_filename = "players/{}/tris.md2".format(model_name)
		ci.model = vid.R_RegisterModel (model_filename)
		if not ci.model:
		
			model_name = "male"
			model_filename = "players/male/tris.md2"
			ci.model = vid.R_RegisterModel (model_filename)
		
		# skin file
		skin_filename = "players/{}/{}.pcx".format(model_name, skin_name)
		ci.skin = vid.R_RegisterSkin (skin_filename)

		# if we don't have the skin and the model wasn't male,
		# see if the male has it (this is for CTF's skins)
		if not ci.skin and shared_c.Q_stricmp(model_name, "male"):
		
			# change model to male
			model_name = "male"
			model_filename = "players/male/tris.md2"
			ci.model = vid.R_RegisterModel (model_filename)

			# see if the skin exists for the male model
			skin_filename = "players/{}/{}.pcx".format(model_name, skin_name)
			ci.skin = vid.R_RegisterSkin (skin_filename)
		
		# if we still don't have a skin, it means that the male model didn't have
		# it, so default to grunt
		if not ci.skin:
			# see if the skin exists for the male model
			skin_filename = "players/{}/grunt.pcx".format(model_name)
			ci.skin = vid.R_RegisterSkin (skin_filename)
		
		# weapon file
		for i in range(cl_view.num_cl_weaponmodels):
			weapon_filename = "players/{}/{}".format(model_name, cl_view.cl_weaponmodels[i])
			ci.weaponmodel[i] = vid.R_RegisterModel(weapon_filename)
			if not ci.weaponmodel[i] and model_name == "cyborg":
				# try male
				weapon_filename = "players/male/{}".format(cl_view.cl_weaponmodels[i])
				ci.weaponmodel[i] = vid.R_RegisterModel(weapon_filename)
			
			if not cl_main.cl_vwep.value:
				break # only one when vwep is off
		
		# icon file
		ci.iconname = "/players/{}/{}_i.pcx".format(model_name, skin_name)
		ci.icon = vid.Draw_FindPic (ci.iconname)
	
	# must have loaded all data types to be valid
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
def CL_ParseConfigString(): #void

	"""
	size_t length, space;
	int i, cs_changed;
	char *s, *cs;
	"""

	i = movemsg.MSG_ReadShort(netchan.net_message)
	s = movemsg.MSG_ReadString(netchan.net_message)

	if (i < 0) or (i >= shared.MAX_CONFIGSTRINGS):

		clientserver.Com_Printf("%s: bad index: %i\n", "CL_ParseConfigString", i)
		return


	cs = cl_main.cl.configstrings[i]
	cs_changed = s != cs # strcmp(s, cs) != 0

	length = len(s)

	# statusbar code covers several configstring indices
	if (i >= shared.CS_STATUSBAR) and (i < shared.CS_STATUSBAR_END):

		space = shared.CS_STATUSBAR_SPACE(i)

		if length >= space:

			clientserver.Com_Printf("%s: %i: statusbar code too long: %i > %i\n",
				"CL_ParseConfigString", i, length, space - 1)

			return


		# memcpy(cs, s, length + 1); Q2PORT: the whole string stays in
		# configstrings[i], where the C runs it on into the next indices
		cl_main.cl.configstrings[i] = s

	else:

		space = shared.MAX_QPATH # sizeof(cl.configstrings[i])

		if length >= space:

			clientserver.Com_Printf("%s: %i: string too long: %i > %i\n",
				"CL_ParseConfigString", i, length, space - 1)

			return


		cl_main.cl.configstrings[i] = s # strcpy(cs, s);


	if (i >= shared.CS_LIGHTS) and (i < shared.CS_LIGHTS + shared.MAX_LIGHTSTYLES):

		cl_lights.CL_SetLightstyle(i - shared.CS_LIGHTS)

	elif i == shared.CS_CDTRACK:

		if cl_main.cl.refresh_prepped:

			ogg.OGG_PlayTrack(cl_main.cl.configstrings[shared.CS_CDTRACK], True, True)


	elif (i >= shared.CS_MODELS) and (i < shared.CS_MODELS + shared.MAX_MODELS):

		if cl_main.cl.refresh_prepped:

			cl_main.cl.model_draw[i - shared.CS_MODELS] = vid.R_RegisterModel(cl_main.cl.configstrings[i])

			if cl_main.cl.configstrings[i][:1] == '*':

				cl_main.cl.model_clip[i - shared.CS_MODELS] = collision.CM_InlineModel(cl_main.cl.configstrings[i])


			else:

				cl_main.cl.model_clip[i - shared.CS_MODELS] = None



	elif (i >= shared.CS_SOUNDS) and (i < shared.CS_SOUNDS + shared.MAX_MODELS):

		if cl_main.cl.refresh_prepped:

			cl_main.cl.sound_precache[i - shared.CS_SOUNDS] = \
				snd_dma.S_RegisterSound(cl_main.cl.configstrings[i])


	elif (i >= shared.CS_IMAGES) and (i < shared.CS_IMAGES + shared.MAX_MODELS):

		if cl_main.cl.refresh_prepped:

			cl_main.cl.image_precache[i - shared.CS_IMAGES] = vid.Draw_FindPic(cl_main.cl.configstrings[i])


	elif (i >= shared.CS_PLAYERSKINS) and (i < shared.CS_PLAYERSKINS + shared.MAX_CLIENTS):

		if cl_main.cl.refresh_prepped and cs_changed:

			CL_ParseClientinfo(i - shared.CS_PLAYERSKINS)



# ======================================================================
# ACTION MESSAGES
# ======================================================================

# ==================
# CL_ParseStartSoundPacket
# ==================
def CL_ParseStartSoundPacket(): # (static)

	"""
	vec3_t pos_v;
	float *pos;
	int channel, ent;
	int sound_num;
	float volume;
	float attenuation;
	int flags;
	float ofs;
	"""
	pos_v = np.zeros((3,), dtype=np.float32)

	flags = movemsg.MSG_ReadByte(netchan.net_message)
	sound_num = movemsg.MSG_ReadByte(netchan.net_message)
	if sound_num < 0:

		clientserver.Com_Error(common_h.ERR_DROP, "%s: unexpected message end", "CL_ParseStartSoundPacket")


	if flags & common_h.SND_VOLUME:

		volume = movemsg.MSG_ReadByte(netchan.net_message) / 255.0

	else:

		volume = common_h.DEFAULT_SOUND_PACKET_VOLUME


	if flags & common_h.SND_ATTENUATION:

		attenuation = movemsg.MSG_ReadByte(netchan.net_message) / 64.0

	else:

		attenuation = common_h.DEFAULT_SOUND_PACKET_ATTENUATION


	if flags & common_h.SND_OFFSET:

		ofs = movemsg.MSG_ReadByte(netchan.net_message) / 1000.0

	else:

		ofs = 0


	if flags & common_h.SND_ENT:

		# entity reletive
		channel = movemsg.MSG_ReadShort(netchan.net_message)
		ent = channel >> 3
		if ent < 0:

			clientserver.Com_Printf("%s: incorrect channel %d\n", "CL_ParseStartSoundPacket", channel)
			return


		channel &= 7

	else:

		ent = 0
		channel = 0


	if flags & common_h.SND_POS:

		# positioned in space
		movemsg.MSG_ReadPos(netchan.net_message, pos_v)
		pos = pos_v

	else:

		# use entity number
		pos = None


	if sound_num >= shared.MAX_SOUNDS:

		clientserver.Com_Printf("%s: incorrect sound id %d > MAX_SOUNDS\n", "CL_ParseStartSoundPacket", sound_num)
		return


	if not cl_main.cl.sound_precache[sound_num]:

		return


	snd_dma.S_StartSound(pos, ent, channel, cl_main.cl.sound_precache[sound_num], volume, attenuation, ofs)
	   


def CL_ParseServerMessage(): #void

	"""
	int cmd;
	char *s;
	int i;
	"""

	# if recording demos, copy the message out
	if cl_main.cl_shownet.value == 1:

		clientserver.Com_Printf("%i ", netchan.net_message.cursize)


	elif cl_main.cl_shownet.value >= 2:

		clientserver.Com_Printf("------------------\n")


	# parse the message
	while 1:

		if netchan.net_message.readcount > netchan.net_message.cursize:

			clientserver.Com_Error(shared.ERR_DROP, "%s: Bad server message", "CL_ParseServerMessage")
			return


		cmd = movemsg.MSG_ReadByte(netchan.net_message)

		if cmd == -1:

			SHOWNET("END OF MESSAGE")
			break


		CL_ShowNetCmd(cmd)

		# other commands
		if cmd == common_h.svc_ops_e.svc_nop.value:

			pass

		elif cmd == common_h.svc_ops_e.svc_disconnect.value:

			clientserver.Com_Error(shared.ERR_DISCONNECT, "Server disconnected\n")
			return

		elif cmd == common_h.svc_ops_e.svc_reconnect.value:

			clientserver.Com_Printf("Server disconnected, reconnecting\n")

			if cl_main.cls.download:

				# close download
				cl_main.cls.download.close() # fclose(cls.download);
				cl_main.cls.download = None


			cl_main.cls.state = client_h.connstate_t.ca_connecting
			cl_main.cls.connect_time = -99999 # CL_CheckForResend() will fire immediately

		elif cmd == common_h.svc_ops_e.svc_print.value:

			i = movemsg.MSG_ReadByte(netchan.net_message)
			if i < 0:

				SHOWNET("END OF MESSAGE")

			else: # break; leaves the switch

				if i == shared.PRINT_CHAT:

					snd_dma.S_StartLocalSound("misc/talk.wav")
					cl_console.con.ormask = 128


				clientserver.Com_Printf("%s", movemsg.MSG_ReadString(netchan.net_message))
				cl_console.con.ormask = 0

		elif cmd == common_h.svc_ops_e.svc_centerprint.value:

			cl_screen.SCR_CenterPrint(movemsg.MSG_ReadString(netchan.net_message))

		elif cmd == common_h.svc_ops_e.svc_stufftext.value:

			s = movemsg.MSG_ReadString(netchan.net_message)
			clientserver.Com_DPrintf("stufftext: %s\n", s)
			cmdparser.Cbuf_AddText(s)

		elif cmd == common_h.svc_ops_e.svc_serverdata.value:

			cmdparser.Cbuf_Execute() # make sure any stuffed commands are done
			CL_ParseServerData()

		elif cmd == common_h.svc_ops_e.svc_configstring.value:

			CL_ParseConfigString()

		elif cmd == common_h.svc_ops_e.svc_sound.value:

			CL_ParseStartSoundPacket()

		elif cmd == common_h.svc_ops_e.svc_spawnbaseline.value:

			CL_ParseBaseline()

		elif cmd == common_h.svc_ops_e.svc_temp_entity.value:

			cl_tempentities.CL_ParseTEnt()

		elif cmd == common_h.svc_ops_e.svc_muzzleflash.value:

			cl_effects.CL_AddMuzzleFlash()

		elif cmd == common_h.svc_ops_e.svc_muzzleflash2.value:

			cl_effects.CL_AddMuzzleFlash2()

		elif cmd == common_h.svc_ops_e.svc_download.value:

			cl_download.CL_ParseDownload()

		elif cmd == common_h.svc_ops_e.svc_frame.value:

			CL_ParseFrame()

		elif cmd == common_h.svc_ops_e.svc_inventory.value:

			cl_inventory.CL_ParseInventory()

		elif cmd == common_h.svc_ops_e.svc_layout.value:

			s = movemsg.MSG_ReadString(netchan.net_message)
			cl_main.cl.layout = s[:1023] # Q_strlcpy(cl.layout, s, sizeof(cl.layout));

		elif cmd in (common_h.svc_ops_e.svc_playerinfo.value, common_h.svc_ops_e.svc_packetentities.value,
				common_h.svc_ops_e.svc_deltapacketentities.value):

			clientserver.Com_Error(shared.ERR_DROP, "Out of place frame data")
			return

		else:

			clientserver.Com_Error(shared.ERR_DROP, "%s: Illegible server message\n",
				"CL_ParseServerMessage")
			return



	cl_screen.CL_AddNetgraph()

	# we don't know if it is ok to save a demo message
	# until after we have parsed the frame
	if cl_main.cls.demorecording and not cl_main.cls.demowaiting:

		cl_main.CL_WriteDemoMessage()
