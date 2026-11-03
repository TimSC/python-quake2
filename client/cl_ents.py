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
import copy
import random
import numpy as np
from qcommon import common, net_chan, qcommon
from game import q_shared
import math
from qcommon import files
from client import cl_main, cl_parse, client, cl_pred, cl_scrn, cl_tent, cl_fx, cl_newfx, cl_view, ref
from linux import vid_so
"""
// cl_ents.c -- entity parsing and management

#include "client.h"


extern	struct model_s	*cl_mod_powerscreen;

# PGM
vidref_val = q_shared.VIDREF_GL
cl_mod_powerscreen = None

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
	count = common.MSG_ReadByte(net_chan.net_message)
	for _ in range(count):
		bits = [common.MSG_ReadByte(net_chan.net_message) for _ in range(5)]

		pr_proj = projectile_t()
		pr_proj.origin[0] = ((bits[0] + ((bits[1] & 15) << 8)) << 1) - 4096
		pr_proj.origin[1] = (((bits[1] >> 4) + (bits[2] << 4)) << 1) - 4096
		pr_proj.origin[2] = ((bits[3] + ((bits[4] & 15) << 8)) << 1) - 4096
		q_shared.VectorCopy(pr_proj.origin, pr_proj.oldorigin)

		if bits[4] & q_shared.EF_BLASTER:
			pr_proj.effects = q_shared.EF_BLASTER
		else:
			pr_proj.effects = 0

		old = False
		if bits[4] & 128:
			old = True
			bits = [common.MSG_ReadByte(net_chan.net_message) for _ in range(5)]
			pr_proj.oldorigin[0] = ((bits[0] + ((bits[1] & 15) << 8)) << 1) - 4096
			pr_proj.oldorigin[1] = (((bits[1] >> 4) + (bits[2] << 4)) << 1) - 4096
			pr_proj.oldorigin[2] = ((bits[3] + ((bits[4] & 15) << 8)) << 1) - 4096

		bits = [common.MSG_ReadByte(net_chan.net_message) for _ in range(3)]

		pr_proj.angles[0] = 360.0 * bits[0] / 256.0
		pr_proj.angles[1] = 360.0 * bits[1] / 256.0
		pr_proj.modelindex = bits[2]

		b = common.MSG_ReadByte(net_chan.net_message)
		pr_proj.num = (b & 0x7f)
		if b & 128:
			pr_proj.num |= common.MSG_ReadByte(net_chan.net_message) << 7

		pr_proj.present = True

		lastempty = -1
		for j in range(MAX_PROJECTILES):
			slot = cl_projectiles[j]
			if slot.modelindex:
				if slot.num == pr_proj.num:
					if not old:
						q_shared.VectorCopy(slot.origin, pr_proj.oldorigin)
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
		if pr.effects & q_shared.EF_BLASTER and hasattr(cl_fx, "CL_BlasterTrail"):
			cl_fx.CL_BlasterTrail(pr.oldorigin, ent.origin)
			cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)
		if pr.effects & q_shared.EF_BLASTER and not hasattr(cl_fx, "CL_BlasterTrail"):
			cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)

		q_shared.VectorCopy(pr.angles, ent.angles)
		cl_view.V_AddEntity(ent)

bitcounts = [] #int[32], just for protocol profilingf
for i in range(32):
	bitcounts.append(0)

def CL_ParseEntityBits (): # (unsigned *bits)

	# unsigned	b, total;
	# int			i;
	# int			number;

	total = common.MSG_ReadByte (net_chan.net_message)
	if total & qcommon.U_MOREBITS1:
	
		b = common.MSG_ReadByte (net_chan.net_message)
		total |= b<<8
	
	if total & qcommon.U_MOREBITS2:
	
		b = common.MSG_ReadByte (net_chan.net_message)
		total |= b<<16
	
	if total & qcommon.U_MOREBITS3:
	
		b = common.MSG_ReadByte (net_chan.net_message)
		total |= b<<24
	

	# count the bits for net profiling
	for i in range(32):
		if total&(1<<i):
			bitcounts[i]+=1

	if total & qcommon.U_NUMBER16:
		number = common.MSG_ReadShort (net_chan.net_message)
	else:
		number = common.MSG_ReadByte (net_chan.net_message)

	return number, total


	# ==================
	# CL_ParseDelta
	#
	# Can go from either a baseline or a previous packet_entity
	# ==================
def CL_ParseDelta (fromEnt, toEnt, number, bits): #entity_state_t *from, entity_state_t *to, int number, int bits

	# set everything to the state we are delta'ing from
	
	toEnt.copy(fromEnt)

	q_shared.VectorCopy (fromEnt.origin, toEnt.old_origin)
	toEnt.number = number

	if bits & qcommon.U_MODEL:
		toEnt.modelindex = common.MSG_ReadByte (net_chan.net_message)
	if bits & qcommon.U_MODEL2:
		toEnt.modelindex2 = common.MSG_ReadByte (net_chan.net_message)
	if bits & qcommon.U_MODEL3:
		toEnt.modelindex3 = common.MSG_ReadByte (net_chan.net_message)
	if bits & qcommon.U_MODEL4:
		toEnt.modelindex4 = common.MSG_ReadByte (net_chan.net_message)
		
	if bits & qcommon.U_FRAME8:
		toEnt.frame = common.MSG_ReadByte (net_chan.net_message)
	if bits & qcommon.U_FRAME16:
		toEnt.frame = common.MSG_ReadShort (net_chan.net_message)

	if (bits & qcommon.U_SKIN8) and (bits & qcommon.U_SKIN16):		# used for laser colors
		toEnt.skinnum = common.MSG_ReadLong(net_chan.net_message)
	elif bits & qcommon.U_SKIN8:
		toEnt.skinnum = common.MSG_ReadByte(net_chan.net_message)
	elif bits & qcommon.U_SKIN16:
		toEnt.skinnum = common.MSG_ReadShort(net_chan.net_message)

	if (bits & (qcommon.U_EFFECTS8|qcommon.U_EFFECTS16)) == (qcommon.U_EFFECTS8|qcommon.U_EFFECTS16):
		toEnt.effects = common.MSG_ReadLong(net_chan.net_message)
	elif bits & qcommon.U_EFFECTS8:
		toEnt.effects = common.MSG_ReadByte(net_chan.net_message)
	elif bits & qcommon.U_EFFECTS16:
		toEnt.effects = common.MSG_ReadShort(net_chan.net_message)

	if (bits & (qcommon.U_RENDERFX8|qcommon.U_RENDERFX16)) == (qcommon.U_RENDERFX8|qcommon.U_RENDERFX16):
		toEnt.renderfx = common.MSG_ReadLong(net_chan.net_message)
	elif bits & qcommon.U_RENDERFX8:
		toEnt.renderfx = common.MSG_ReadByte(net_chan.net_message)
	elif bits & qcommon.U_RENDERFX16:
		toEnt.renderfx = common.MSG_ReadShort(net_chan.net_message)

	if bits & qcommon.U_ORIGIN1:
		toEnt.origin[0] = common.MSG_ReadCoord (net_chan.net_message)
	if bits & qcommon.U_ORIGIN2:
		toEnt.origin[1] = common.MSG_ReadCoord (net_chan.net_message)
	if bits & qcommon.U_ORIGIN3:
		toEnt.origin[2] = common.MSG_ReadCoord (net_chan.net_message)
		
	if bits & qcommon.U_ANGLE1:
		toEnt.angles[0] = common.MSG_ReadAngle(net_chan.net_message)
	if bits & qcommon.U_ANGLE2:
		toEnt.angles[1] = common.MSG_ReadAngle(net_chan.net_message)
	if bits & qcommon.U_ANGLE3:
		toEnt.angles[2] = common.MSG_ReadAngle(net_chan.net_message)

	if bits & qcommon.U_OLDORIGIN:
		toEnt.old_origin = common.MSG_ReadPos (net_chan.net_message)

	if bits & qcommon.U_SOUND:
		toEnt.sound = common.MSG_ReadByte (net_chan.net_message)

	if bits & qcommon.U_EVENT:
		toEnt.event = common.MSG_ReadByte (net_chan.net_message)
	else:
		toEnt.event = 0

	if bits & qcommon.U_SOLID:
		toEnt.solid = common.MSG_ReadShort (net_chan.net_message)


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

	state = cl_main.cl_parse_entities[cl_main.cl.parse_entities & (client.MAX_PARSE_ENTITIES-1)]
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
		or state.event == q_shared.entity_event_t.EV_PLAYER_TELEPORT
		or state.event == q_shared.entity_event_t.EV_OTHER_TELEPORT
		):
	
		ent.serverframe = -99
	

	if ent.serverframe != cl_main.cl.frame.serverframe - 1:
		# wasn't in last update, so initialize some things
		ent.trailcount = 1024		# for diminishing rocket / grenade trails
		# duplicate the current state so lerping doesn't hurt anything
		ent.prev = copy.deepcopy(state) # ent->prev = *state;
		if state.event == q_shared.entity_event_t.EV_OTHER_TELEPORT:
		
			q_shared.VectorCopy (state.origin, ent.prev.origin)
			q_shared.VectorCopy (state.origin, ent.lerp_origin)
		
		else:
		
			q_shared.VectorCopy (state.old_origin, ent.prev.origin)
			q_shared.VectorCopy (state.old_origin, ent.lerp_origin)
		
	
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
			oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client.MAX_PARSE_ENTITIES-1)]
			oldnum = oldstate.number

	while 1:

		newnum, bits = CL_ParseEntityBits ()

		if newnum >= q_shared.MAX_EDICTS:
			common.Com_Error (q_shared.ERR_DROP,"CL_ParsePacketEntities: bad number:{}".format(newnum))

		if net_chan.net_message.readcount > net_chan.net_message.cursize:
			common.Com_Error (q_shared.ERR_DROP,"CL_ParsePacketEntities: end of message")

		if newnum==0:
			break

		while oldnum < newnum:

			# one or more entities from the old packet are unchanged
			if cl_main.cl_shownet.value == 3:
				common.Com_Printf ("   unchanged: {}\n".format(oldnum))

			CL_DeltaEntity (newframe, oldnum, oldstate, 0)
			
			oldindex+=1

			if oldindex >= oldframe.num_entities:
				oldnum = 99999
			else:
			
				oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client.MAX_PARSE_ENTITIES-1)]
				oldnum = oldstate.number
		

		if bits & qcommon.U_REMOVE:
			# the entity present in oldframe is not in the current frame
			if cl_main.cl_shownet.value == 3:
				common.Com_Printf ("   remove: {}\n".format(newnum))

			if oldnum != newnum:
				common.Com_Printf ("U_REMOVE: oldnum != newnum\n")

			oldindex+=1

			if oldindex >= oldframe.num_entities:
				oldnum = 99999
			else:
			
				oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client.MAX_PARSE_ENTITIES-1)]
				oldnum = oldstate.number
			
			continue
		

		if oldnum == newnum:
			# delta from previous state
			if cl_main.cl_shownet.value == 3:
				common.Com_Printf ("   delta: {}\n".format(newnum))

			CL_DeltaEntity (newframe, newnum, oldstate, bits)

			oldindex+=1

			if oldindex >= oldframe.num_entities:
				oldnum = 99999
			else:
			
				oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client.MAX_PARSE_ENTITIES-1)]
				oldnum = oldstate.number
			
			continue;
		

		if oldnum > newnum:
			# delta from baseline
			if cl_main.cl_shownet.value == 3:
				common.Com_Printf ("   baseline: {}\n".format(newnum))
			CL_DeltaEntity (newframe, newnum, cl_main.cl_entities[newnum].baseline, bits)
			continue

	# any remaining entities in the old frame are copied over
	while oldnum != 99999:

		# one or more entities from the old packet are unchanged
		if cl_main.cl_shownet.value == 3:
			common.Com_Printf ("   unchanged: {}\n".format(oldnum))

		CL_DeltaEntity (newframe, oldnum, oldstate, 0)
		
		oldindex+=1

		if oldindex >= oldframe.num_entities:
			oldnum = 99999
		else:
		
			oldstate = cl_main.cl_parse_entities[(oldframe.parse_entities+oldindex) & (client.MAX_PARSE_ENTITIES-1)]
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

	flags = common.MSG_ReadShort (net_chan.net_message)

	#
	# parse the pmove_state_t
	#
	if flags & qcommon.PS_M_TYPE:
		state.pmove.pm_type = common.MSG_ReadByte (net_chan.net_message)


	if flags & qcommon.PS_M_ORIGIN:

		state.pmove.origin[0] = common.MSG_ReadShort (net_chan.net_message)
		state.pmove.origin[1] = common.MSG_ReadShort (net_chan.net_message)
		state.pmove.origin[2] = common.MSG_ReadShort (net_chan.net_message)


	if flags & qcommon.PS_M_VELOCITY:

		state.pmove.velocity[0] = common.MSG_ReadShort (net_chan.net_message)
		state.pmove.velocity[1] = common.MSG_ReadShort (net_chan.net_message)
		state.pmove.velocity[2] = common.MSG_ReadShort (net_chan.net_message)


	if flags & qcommon.PS_M_TIME:
		state.pmove.pm_time = common.MSG_ReadByte (net_chan.net_message)

	if flags & qcommon.PS_M_FLAGS:
		state.pmove.pm_flags = common.MSG_ReadByte (net_chan.net_message)

	if flags & qcommon.PS_M_GRAVITY:
		state.pmove.gravity = common.MSG_ReadShort (net_chan.net_message)

	if flags & qcommon.PS_M_DELTA_ANGLES:

		state.pmove.delta_angles[0] = common.MSG_ReadShort (net_chan.net_message)
		state.pmove.delta_angles[1] = common.MSG_ReadShort (net_chan.net_message)
		state.pmove.delta_angles[2] = common.MSG_ReadShort (net_chan.net_message)


	if cl_main.cl.attractloop:
		state.pmove.pm_type = q_shared.pmtype_t.PM_FREEZE.value		# demo playback

	#
	# parse the rest of the player_state_t
	#
	if flags & qcommon.PS_VIEWOFFSET:

		state.viewoffset[0] = common.MSG_ReadChar (net_chan.net_message) * 0.25
		state.viewoffset[1] = common.MSG_ReadChar (net_chan.net_message) * 0.25
		state.viewoffset[2] = common.MSG_ReadChar (net_chan.net_message) * 0.25


	if flags & qcommon.PS_VIEWANGLES:

		state.viewangles[0] = common.MSG_ReadAngle16 (net_chan.net_message)
		state.viewangles[1] = common.MSG_ReadAngle16 (net_chan.net_message)
		state.viewangles[2] = common.MSG_ReadAngle16 (net_chan.net_message)


	if flags & qcommon.PS_KICKANGLES:

		state.kick_angles[0] = common.MSG_ReadChar (net_chan.net_message) * 0.25
		state.kick_angles[1] = common.MSG_ReadChar (net_chan.net_message) * 0.25
		state.kick_angles[2] = common.MSG_ReadChar (net_chan.net_message) * 0.25


	if flags & qcommon.PS_WEAPONINDEX:

		state.gunindex = common.MSG_ReadByte (net_chan.net_message)


	if flags & qcommon.PS_WEAPONFRAME:

		state.gunframe = common.MSG_ReadByte (net_chan.net_message)
		state.gunoffset[0] = common.MSG_ReadChar (net_chan.net_message)*0.25
		state.gunoffset[1] = common.MSG_ReadChar (net_chan.net_message)*0.25
		state.gunoffset[2] = common.MSG_ReadChar (net_chan.net_message)*0.25
		state.gunangles[0] = common.MSG_ReadChar (net_chan.net_message)*0.25
		state.gunangles[1] = common.MSG_ReadChar (net_chan.net_message)*0.25
		state.gunangles[2] = common.MSG_ReadChar (net_chan.net_message)*0.25


	if flags & qcommon.PS_BLEND:

		state.blend[0] = common.MSG_ReadByte (net_chan.net_message)/255.0
		state.blend[1] = common.MSG_ReadByte (net_chan.net_message)/255.0
		state.blend[2] = common.MSG_ReadByte (net_chan.net_message)/255.0
		state.blend[3] = common.MSG_ReadByte (net_chan.net_message)/255.0


	if flags & qcommon.PS_FOV:
		state.fov = common.MSG_ReadByte (net_chan.net_message)

	if flags & qcommon.PS_RDFLAGS:
		state.rdflags = common.MSG_ReadByte (net_chan.net_message)

	# parse stats
	statbits = common.MSG_ReadLong (net_chan.net_message)
	for i in range(q_shared.MAX_STATS):
		if statbits & (1<<i):
			state.stats[i] = common.MSG_ReadShort(net_chan.net_message)



def CL_FireEntityEvents (frame):
	for pnum in range(frame.num_entities):
		num = (frame.parse_entities + pnum) & (client.MAX_PARSE_ENTITIES - 1)
		s1 = cl_main.cl_parse_entities[num]
		if s1.event and hasattr(cl_fx, "CL_EntityEvent"):
			cl_fx.CL_EntityEvent(s1)
		effects = s1.effects or 0
		if effects & q_shared.EF_TELEPORTER and hasattr(cl_fx, "CL_TeleporterParticles"):
			cl_fx.CL_TeleporterParticles(s1)


#================
#CL_ParseFrame
#================

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

	cl_main.cl.frame.serverframe = common.MSG_ReadSLong (net_chan.net_message)
	cl_main.cl.frame.deltaframe = common.MSG_ReadSLong (net_chan.net_message)
	cl_main.cl.frame.servertime = cl_main.cl.frame.serverframe*100

	# BIG HACK to let old demos continue to work
	if cl_main.cls.serverProtocol != 26:
		cl_main.cl.surpressCount = common.MSG_ReadByte (net_chan.net_message)

	if cl_main.cl_shownet.value == 3:
		common.Com_Printf ("   frame:{}  delta:{}\n".format(cl_main.cl.frame.serverframe,
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
		old = cl_main.cl.frames[cl_main.cl.frame.deltaframe & qcommon.UPDATE_MASK]

		if not old.valid:
			# should never happen
			common.Com_Printf ("Delta from invalid frame (not supposed to happen!).\n");
		
		if old.serverframe != cl_main.cl.frame.deltaframe:
			# The frame that the server did the delta from
			# is too old, so we can't reconstruct it properly.
			common.Com_Printf ("Delta frame too old.\n")
		
		elif cl_main.cl.parse_entities - old.parse_entities > client.MAX_PARSE_ENTITIES-128:
		
			common.Com_Printf ("Delta parse_entities too old.\n")
		
		else:
			cl_main.cl.frame.valid = True	# valid delta parse
	
	
	# clamp time 
	if cl_main.cl.time > cl_main.cl.frame.servertime:
		cl_main.cl.time = cl_main.cl.frame.servertime
	elif cl_main.cl.time < cl_main.cl.frame.servertime - 100:
		cl_main.cl.time = cl_main.cl.frame.servertime - 100

	# read areabits
	length = common.MSG_ReadByte (net_chan.net_message)
	cl_main.cl.frame.areabits = common.MSG_ReadData (net_chan.net_message, length)

	# read playerinfo
	cmd = common.MSG_ReadByte (net_chan.net_message)
	cl_parse.SHOWNET(cl_parse.svc_strings[cmd])
	if cmd != qcommon.svc_ops_e.svc_playerinfo.value:
		common.Com_Error (q_shared.ERR_DROP, "CL_ParseFrame: not playerinfo")
	CL_ParsePlayerstate (old, cl_main.cl.frame)

	# read packet entities
	cmd = common.MSG_ReadByte (net_chan.net_message)
	cl_parse.SHOWNET(cl_parse.svc_strings[cmd])
	if cmd != qcommon.svc_ops_e.svc_packetentities.value:
		common.Com_Error (q_shared.ERR_DROP, "CL_ParseFrame: not packetentities")
	CL_ParsePacketEntities (old, cl_main.cl.frame)

	# save the frame off in the backup array for later delta comparisons
	cl_main.cl.frames[cl_main.cl.frame.serverframe & qcommon.UPDATE_MASK] = copy.copy(cl_main.cl.frame)

	if cl_main.cl.frame.valid:
	
		# getting a valid frame message ends the connection process
		if cl_main.cls.state != client.connstate_t.ca_active:
		
			cl_main.cls.state = client.connstate_t.ca_active
			cl_main.cl.force_refdef = True
			cl_main.cl.predicted_origin[0] = cl_main.cl.frame.playerstate.pmove.origin[0]*0.125
			cl_main.cl.predicted_origin[1] = cl_main.cl.frame.playerstate.pmove.origin[1]*0.125
			cl_main.cl.predicted_origin[2] = cl_main.cl.frame.playerstate.pmove.origin[2]*0.125
			q_shared.VectorCopy (cl_main.cl.frame.playerstate.viewangles, cl_main.cl.predicted_angles)
			if cl_main.cls.disable_servercount != cl_main.cl.servercount \
				and cl_main.cl.refresh_prepped:
				cl_scrn.SCR_EndLoadingPlaque ()	# get rid of loading plaque
		
		cl_main.cl.sound_prepped = True	# can start mixing ambient sounds
	
		# fire entity events
		CL_FireEntityEvents (cl_main.cl.frame)
		cl_pred.CL_CheckPredictionError ()
	


"""
==========================================================================

INTERPOLATE BETWEEN FRAMES TO GET RENDERING PARMS

==========================================================================

"""

def S_RegisterSexedModel (ent, base):
	model = ""
	n = q_shared.CS_PLAYERSKINS + ent.number - 1
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

def CL_AddPacketEntities (frame): #frame_t *

	"""
	entity_t			ent;
	entity_state_t		*s1;
	float				autorotate;
	int					i;
	int					pnum;
	centity_t			*cent;
	int					autoanim;
	clientinfo_t		*ci;
	unsigned int		effects, renderfx;
	"""
	cl = cl_main.cl

	# bonus items rotate at a fixed rate
	autorotate = q_shared.anglemod(cl.time/10)

	# brush models can auto animate their frames
	autoanim = int(2*cl.time/1000)

	ent = ref.entity_t() # memset (&ent, 0, sizeof(ent)); it is reused for every entity, as in the C

	for pnum in range(frame.num_entities):
	
		s1 = cl_main.cl_parse_entities[(frame.parse_entities+pnum)&(client.MAX_PARSE_ENTITIES-1)]

		cent = cl_main.cl_entities[s1.number]

		effects = s1.effects
		renderfx = s1.renderfx

			# set frame
		if effects & q_shared.EF_ANIM01:
			ent.frame = autoanim & 1
		elif effects & q_shared.EF_ANIM23:
			ent.frame = 2 + (autoanim & 1)
		elif effects & q_shared.EF_ANIM_ALL:
			ent.frame = autoanim
		elif effects & q_shared.EF_ANIM_ALLFAST:
			ent.frame = int(cl.time) // 100 # cl.time is int in C
		else:
			ent.frame = s1.frame

		# quad and pent can do different things on client
		if effects & q_shared.EF_PENT:
		
			effects &= ~q_shared.EF_PENT
			effects |= q_shared.EF_COLOR_SHELL
			renderfx |= q_shared.RF_SHELL_RED
		
		if effects & q_shared.EF_QUAD:
		
			effects &= ~q_shared.EF_QUAD
			effects |= q_shared.EF_COLOR_SHELL
			renderfx |= q_shared.RF_SHELL_BLUE
		
#======
# PMM
		if effects & q_shared.EF_DOUBLE:
		
			effects &= ~q_shared.EF_DOUBLE
			effects |= q_shared.EF_COLOR_SHELL
			renderfx |= q_shared.RF_SHELL_DOUBLE
		
		if effects & q_shared.EF_HALF_DAMAGE:
		
			effects &= ~q_shared.EF_HALF_DAMAGE
			effects |= q_shared.EF_COLOR_SHELL
			renderfx |= q_shared.RF_SHELL_HALF_DAM
		
# pmm
#======
		ent.oldframe = cent.prev.frame
		ent.backlerp = 1.0 - cl.lerpfrac

		if renderfx & (q_shared.RF_FRAMELERP|q_shared.RF_BEAM):
			# step origin discretely, because the frames
			# do the animation properly
			q_shared.VectorCopy (cent.current.origin, ent.origin)
			q_shared.VectorCopy (cent.current.old_origin, ent.oldorigin)
		
		else:
			# interpolate origin
			for i in range(3):
			
				ent.origin[i] = ent.oldorigin[i] = cent.prev.origin[i] + cl.lerpfrac * \
					(cent.current.origin[i] - cent.prev.origin[i])
			
		# create a new entity
	
		# tweak the color of beams
		if renderfx & q_shared.RF_BEAM:
			# the four beam colors are encoded in 32 bits of skinnum (hack)
			ent.alpha = 0.30
			ent.skinnum = (s1.skinnum >> ((random.getrandbits(15) % 4)*8)) & 0xff
			ent.model = None
		
		else:
		
			# set skin
			if s1.modelindex == 255:
				# use custom player skin
				ent.skinnum = 0
				ci = cl.clientinfo[s1.skinnum & 0xff]
				ent.skin = ci.skin
				ent.model = ci.model
				if not ent.skin or not ent.model:
				
					ent.skin = cl.baseclientinfo.skin
					ent.model = cl.baseclientinfo.model
				
#============
#PGM
				if renderfx & q_shared.RF_USE_DISGUISE:
				
					# strncmp((char *)ent.skin, ...) compares the image name, the first field of image_t
					skinname = ent.skin.name if ent.skin is not None else ""
					if skinname[:12] == "players/male":
					
						ent.skin = vid_so.re.RegisterSkin ("players/male/disguise.pcx")
						ent.model = vid_so.re.RegisterModel ("players/male/tris.md2")
					
					elif skinname[:14] == "players/female":
					
						ent.skin = vid_so.re.RegisterSkin ("players/female/disguise.pcx")
						ent.model = vid_so.re.RegisterModel ("players/female/tris.md2")
					
					elif skinname[:14] == "players/cyborg":
					
						ent.skin = vid_so.re.RegisterSkin ("players/cyborg/disguise.pcx")
						ent.model = vid_so.re.RegisterModel ("players/cyborg/tris.md2")
					
#PGM
#============
			
			else:
			
				ent.skinnum = s1.skinnum
				ent.skin = None
				ent.model = cl.model_draw[s1.modelindex]
			
		# only used for black hole model right now, FIXME: do better
		if renderfx == q_shared.RF_TRANSLUCENT:
			ent.alpha = 0.70

		# render effects (fullbright, translucent, etc)
		if effects & q_shared.EF_COLOR_SHELL:
			ent.flags = 0	# renderfx go on color shell entity
		else:
			ent.flags = renderfx

		# calculate angles
		if effects & q_shared.EF_ROTATE:
			# some bonus items auto-rotate
			ent.angles[0] = 0
			ent.angles[1] = autorotate
			ent.angles[2] = 0
		
		# RAFAEL
		elif effects & q_shared.EF_SPINNINGLIGHTS:
		
			ent.angles[0] = 0
			ent.angles[1] = q_shared.anglemod(cl.time/2) + s1.angles[1]
			ent.angles[2] = 180
			
			#vec3_t forward;
			#vec3_t start;
			forward = np.zeros((3,), dtype=np.float32)
			start = np.zeros((3,), dtype=np.float32)

			q_shared.AngleVectors (ent.angles, forward, None, None)
			q_shared.VectorMA (ent.origin, 64, forward, start)
			cl_view.V_AddLight (start, 100, 1, 0, 0)
			
		else:
			# interpolate angles
			#float	a1, a2;

			for i in range(3):
			
				a1 = cent.current.angles[i]
				a2 = cent.prev.angles[i]
				ent.angles[i] = q_shared.LerpAngle (a2, a1, cl.lerpfrac)
			
		if s1.number == cl.playernum+1:
		
			ent.flags |= q_shared.RF_VIEWERMODEL	# only draw from mirrors
			# FIXME: still pass to refresh

			if effects & q_shared.EF_FLAG1:
				cl_view.V_AddLight (ent.origin, 225, 1.0, 0.1, 0.1)
			elif effects & q_shared.EF_FLAG2:
				cl_view.V_AddLight (ent.origin, 225, 0.1, 0.1, 1.0)
			elif effects & q_shared.EF_TAGTRAIL:						#PGM
				cl_view.V_AddLight (ent.origin, 225, 1.0, 1.0, 0.0)	#PGM
			elif effects & q_shared.EF_TRACKERTRAIL:					#PGM
				cl_view.V_AddLight (ent.origin, 225, -1.0, -1.0, -1.0)	#PGM

			continue
		
		# if set to invisible, skip
		if not s1.modelindex:
			continue

		if effects & q_shared.EF_BFG:
		
			ent.flags |= q_shared.RF_TRANSLUCENT
			ent.alpha = 0.30
		
		# RAFAEL
		if effects & q_shared.EF_PLASMA:
		
			ent.flags |= q_shared.RF_TRANSLUCENT
			ent.alpha = 0.6
		
		if effects & q_shared.EF_SPHERETRANS:
		
			ent.flags |= q_shared.RF_TRANSLUCENT
			# PMM - *sigh*  yet more EF overloading
			if effects & q_shared.EF_TRACKERTRAIL:
				ent.alpha = 0.6
			else:
				ent.alpha = 0.3
		
#pmm

		# add to refresh list
		cl_view.V_AddEntity (ent)


		# color shells generate a seperate entity for the main model
		if effects & q_shared.EF_COLOR_SHELL:
		
			# PMM - at this point, all of the shells have been handled
			# if we're in the rogue pack, set up the custom mixing, otherwise just
			# keep going
#			if(Developer_searchpath(2) == 2)
#			{
				# all of the solo colors are fine.  we need to catch any of the combinations that look bad
				# (double & half) and turn them into the appropriate color, and make double/quad something special
			if renderfx & q_shared.RF_SHELL_HALF_DAM:
			
				if files.Developer_searchpath(2) == 2:
				
					# ditch the half damage shell if any of red, blue, or double are on
					if renderfx & (q_shared.RF_SHELL_RED|q_shared.RF_SHELL_BLUE|q_shared.RF_SHELL_DOUBLE):
						renderfx &= ~q_shared.RF_SHELL_HALF_DAM
				
			if renderfx & q_shared.RF_SHELL_DOUBLE:
			
				if files.Developer_searchpath(2) == 2:
				
					# lose the yellow shell if we have a red, blue, or green shell
					if renderfx & (q_shared.RF_SHELL_RED|q_shared.RF_SHELL_BLUE|q_shared.RF_SHELL_GREEN):
						renderfx &= ~q_shared.RF_SHELL_DOUBLE
					# if we have a red shell, turn it to purple by adding blue
					if renderfx & q_shared.RF_SHELL_RED:
						renderfx |= q_shared.RF_SHELL_BLUE
					# if we have a blue shell (and not a red shell), turn it to cyan by adding green
					elif renderfx & q_shared.RF_SHELL_BLUE:
						# go to green if it's on already, otherwise do cyan (flash green)
						if renderfx & q_shared.RF_SHELL_GREEN:
							renderfx &= ~q_shared.RF_SHELL_BLUE
						else:
							renderfx |= q_shared.RF_SHELL_GREEN
				
#			}
			# pmm
			ent.flags = renderfx | q_shared.RF_TRANSLUCENT
			ent.alpha = 0.30
			cl_view.V_AddEntity (ent)
		
		ent.skin = None		# never use a custom skin on others
		ent.skinnum = 0
		ent.flags = 0
		ent.alpha = 0

		# duplicate for linked models
		if s1.modelindex2:
		
			if s1.modelindex2 == 255:
				# custom weapon
				ci = cl.clientinfo[s1.skinnum & 0xff]
				i = (s1.skinnum >> 8) # 0 is default weapon model
				if not cl_main.cl_vwep.value or i > client.MAX_CLIENTWEAPONMODELS - 1:
					i = 0
				ent.model = ci.weaponmodel[i]
				if not ent.model:
					if i != 0:
						ent.model = ci.weaponmodel[0]
					if not ent.model:
						ent.model = cl.baseclientinfo.weaponmodel[0]
				
			else:
				ent.model = cl.model_draw[s1.modelindex2]

			# PMM - check for the defender sphere shell .. make it translucent
			# replaces the previous version which used the high bit on modelindex2 to determine transparency
			if not q_shared.Q_strcasecmp (cl.configstrings[q_shared.CS_MODELS+(s1.modelindex2)] or "", "models/items/shell/tris.md2"):
			
				ent.alpha = 0.32
				ent.flags = q_shared.RF_TRANSLUCENT
			
			# pmm

			cl_view.V_AddEntity (ent)

			#PGM - make sure these get reset.
			ent.flags = 0
			ent.alpha = 0
			#PGM
		
		if s1.modelindex3:
		
			ent.model = cl.model_draw[s1.modelindex3]
			cl_view.V_AddEntity (ent)
		
		if s1.modelindex4:
		
			ent.model = cl.model_draw[s1.modelindex4]
			cl_view.V_AddEntity (ent)
		
		if effects & q_shared.EF_POWERSCREEN:
		
			ent.model = cl_tent.cl_mod_powerscreen
			ent.oldframe = 0
			ent.frame = 0
			ent.flags |= (q_shared.RF_TRANSLUCENT | q_shared.RF_SHELL_GREEN)
			ent.alpha = 0.30
			cl_view.V_AddEntity (ent)
		
		# add automatic particle trails
		if effects&~q_shared.EF_ROTATE:
		
			if effects & q_shared.EF_ROCKET:
			
				cl_fx.CL_RocketTrail (cent.lerp_origin, ent.origin, cent)
				cl_view.V_AddLight (ent.origin, 200, 1, 1, 0)
			
			# PGM - Do not reorder EF_BLASTER and EF_HYPERBLASTER. 
			# EF_BLASTER | EF_TRACKER is a special case for EF_BLASTER2... Cheese!
			elif effects & q_shared.EF_BLASTER:
			
#				CL_BlasterTrail (cent->lerp_origin, ent.origin);
#PGM
				if effects & q_shared.EF_TRACKER:	# lame... problematic?
				
					cl_newfx.CL_BlasterTrail2 (cent.lerp_origin, ent.origin)
					cl_view.V_AddLight (ent.origin, 200, 0, 1, 0)		
				
				else:
				
					cl_fx.CL_BlasterTrail (cent.lerp_origin, ent.origin)
					cl_view.V_AddLight (ent.origin, 200, 1, 1, 0)
				
#PGM
			
			elif effects & q_shared.EF_HYPERBLASTER:
			
				if effects & q_shared.EF_TRACKER:						# PGM	overloaded for blaster2.
					cl_view.V_AddLight (ent.origin, 200, 0, 1, 0)		# PGM
				else:											# PGM
					cl_view.V_AddLight (ent.origin, 200, 1, 1, 0)
			
			elif effects & q_shared.EF_GIB:
			
				cl_fx.CL_DiminishingTrail (cent.lerp_origin, ent.origin, cent, effects)
			
			elif effects & q_shared.EF_GRENADE:
			
				cl_fx.CL_DiminishingTrail (cent.lerp_origin, ent.origin, cent, effects)
			
			elif effects & q_shared.EF_FLIES:
			
				cl_fx.CL_FlyEffect (cent, ent.origin)
			
			elif effects & q_shared.EF_BFG:
			
				#static int bfg_lightramp[6] = {300, 400, 600, 300, 150, 75};

				if effects & q_shared.EF_ANIM_ALLFAST:
				
					cl_fx.CL_BfgParticles (ent)
					i = 200
				
				else:
				
					i = bfg_lightramp[s1.frame]
				
				cl_view.V_AddLight (ent.origin, i, 0, 1, 0)
			
			# RAFAEL
			elif effects & q_shared.EF_TRAP:
			
				ent.origin[2] += 32
				cl_fx.CL_TrapParticles (ent)
				i = (random.getrandbits(15)%100) + 100
				cl_view.V_AddLight (ent.origin, i, 1, 0.8, 0.1)
			
			elif effects & q_shared.EF_FLAG1:
			
				cl_fx.CL_FlagTrail (cent.lerp_origin, ent.origin, 242)
				cl_view.V_AddLight (ent.origin, 225, 1, 0.1, 0.1)
			
			elif effects & q_shared.EF_FLAG2:
			
				cl_fx.CL_FlagTrail (cent.lerp_origin, ent.origin, 115)
				cl_view.V_AddLight (ent.origin, 225, 0.1, 0.1, 1)
			
#======
#ROGUE
			elif effects & q_shared.EF_TAGTRAIL:
			
				cl_newfx.CL_TagTrail (cent.lerp_origin, ent.origin, 220)
				cl_view.V_AddLight (ent.origin, 225, 1.0, 1.0, 0.0)
			
			elif effects & q_shared.EF_TRACKERTRAIL:
			
				if effects & q_shared.EF_TRACKER:
				
					#float intensity;

					intensity = 50 + (500 * (math.sin(cl.time/500.0) + 1.0))
					# FIXME - check out this effect in rendition
					if vidref_val == q_shared.VIDREF_GL:
						cl_view.V_AddLight (ent.origin, intensity, -1.0, -1.0, -1.0)
					else:
						cl_view.V_AddLight (ent.origin, -1.0 * intensity, 1.0, 1.0, 1.0)
					
				else:
				
					cl_newfx.CL_Tracker_Shell (cent.lerp_origin)
					cl_view.V_AddLight (ent.origin, 155, -1.0, -1.0, -1.0)
				
			elif effects & q_shared.EF_TRACKER:
			
				cl_newfx.CL_TrackerTrail (cent.lerp_origin, ent.origin, 0)
				# FIXME - check out this effect in rendition
				if vidref_val == q_shared.VIDREF_GL:
					cl_view.V_AddLight (ent.origin, 200, -1, -1, -1)
				else:
					cl_view.V_AddLight (ent.origin, -200, 1, 1, 1)
			
#ROGUE
#======
			# RAFAEL
			elif effects & q_shared.EF_GREENGIB:
			
				cl_fx.CL_DiminishingTrail (cent.lerp_origin, ent.origin, cent, effects)				
			
			# RAFAEL
			elif effects & q_shared.EF_IONRIPPER:
			
				cl_fx.CL_IonripperTrail (cent.lerp_origin, ent.origin)
				cl_view.V_AddLight (ent.origin, 100, 1, 0.5, 0.5)
			
			# RAFAEL
			elif effects & q_shared.EF_BLUEHYPERBLASTER:
			
				cl_view.V_AddLight (ent.origin, 200, 0, 0, 1)
			
			# RAFAEL
			elif effects & q_shared.EF_PLASMA:
			
				if effects & q_shared.EF_ANIM_ALLFAST:
				
					cl_fx.CL_BlasterTrail (cent.lerp_origin, ent.origin)
				
				cl_view.V_AddLight (ent.origin, 130, 1, 0.5, 0.5)
			
		q_shared.VectorCopy (ent.origin, cent.lerp_origin)
	


def CL_AddViewWeapon (ps, ops):
	if not cl_main.cl_gun.value:
		return
	if ps.fov > 90:
		return

	if ps.gunindex is None:
		return

	gun_index = ps.gunindex
	if gun_index < 0 or gun_index >= len(cl_main.cl.model_draw):
		return

	gun = ref.entity_t()
	gun.model = cl_main.cl.model_draw[gun_index]
	if gun.model is None:
		return

	for i in range(3):
		gun.origin[i] = cl_main.cl.refdef.vieworg[i] + ops.gunoffset[i] + \
			cl_main.cl.lerpfrac * (ps.gunoffset[i] - ops.gunoffset[i])
		gun.angles[i] = cl_main.cl.refdef.viewangles[i] + q_shared.LerpAngle(
			ops.gunangles[i], ps.gunangles[i], cl_main.cl.lerpfrac
		)

	gun.frame = ps.gunframe
	if gun.frame == 0:
		gun.oldframe = 0
	else:
		gun.oldframe = ops.gunframe

	gun.flags = q_shared.RF_MINLIGHT | q_shared.RF_DEPTHHACK | q_shared.RF_WEAPONMODEL
	gun.backlerp = 1.0 - cl_main.cl.lerpfrac
	q_shared.VectorCopy(gun.origin, gun.oldorigin)
	cl_view.V_AddEntity(gun)


"""
===============
CL_CalcViewValues

Sets cl_main.cl.refdef view values
===============
"""
def CL_CalcViewValues ():

	"""
	Interpolate entity states and account for prediction to update the view definition.
	"""

	ps = cl_main.cl.frame.playerstate
	frame_index = (cl_main.cl.frame.serverframe - 1) & qcommon.UPDATE_MASK
	oldframe = cl_main.cl.frames[frame_index]
	if oldframe.serverframe != cl_main.cl.frame.serverframe - 1 or not oldframe.valid:
		oldframe = cl_main.cl.frame
	ops = oldframe.playerstate

	if abs(ops.pmove.origin[0] - ps.pmove.origin[0]) > 256 * 8 \
		or abs(ops.pmove.origin[1] - ps.pmove.origin[1]) > 256 * 8 \
		or abs(ops.pmove.origin[2] - ps.pmove.origin[2]) > 256 * 8:
		ops = ps

	ent = cl_main.cl_entities[cl_main.cl.playernum + 1]
	lerp = cl_main.cl.lerpfrac

	prediction_allowed = (
		cl_main.cl_predict
		and cl_main.cl_predict.value
		and not (cl_main.cl.frame.playerstate.pmove.pm_flags & q_shared.PMF_NO_PREDICTION)
	)

	if prediction_allowed:
		backlerp = 1.0 - lerp
		for i in range(3):
			cl_main.cl.refdef.vieworg[i] = (
				cl_main.cl.predicted_origin[i]
				+ ops.viewoffset[i]
				+ cl_main.cl.lerpfrac * (ps.viewoffset[i] - ops.viewoffset[i])
				- backlerp * cl_main.cl.prediction_error[i]
			)

		step_time = cl_main.cl.predicted_step_time or 0
		delta = cl_main.cls.realtime - step_time
		if delta < 100:
			predicted_step = (
				cl_main.cl.predicted_step
				if cl_main.cl.predicted_step is not None
				else 0.0
			)
			cl_main.cl.refdef.vieworg[2] -= predicted_step * (100 - delta) * 0.01
	else:
		for i in range(3):
			cl_main.cl.refdef.vieworg[i] = (
				ops.pmove.origin[i] * 0.125
				+ ops.viewoffset[i]
				+ lerp
				* (
					ps.pmove.origin[i] * 0.125
					+ ps.viewoffset[i]
					- (ops.pmove.origin[i] * 0.125 + ops.viewoffset[i])
				)
			)

	if cl_main.cl.frame.playerstate.pmove.pm_type < q_shared.pmtype_t.PM_DEAD.value:
		for i in range(3):
			cl_main.cl.refdef.viewangles[i] = cl_main.cl.predicted_angles[i]
	else:
		for i in range(3):
			cl_main.cl.refdef.viewangles[i] = q_shared.LerpAngle(
				ops.viewangles[i], ps.viewangles[i], lerp
			)

	for i in range(3):
		cl_main.cl.refdef.viewangles[i] += q_shared.LerpAngle(
			ops.kick_angles[i], ps.kick_angles[i], lerp
		)

	if cl_main.cl.v_forward is None:
		cl_main.cl.v_forward = np.zeros((3,), dtype=np.float32)
	if cl_main.cl.v_right is None:
		cl_main.cl.v_right = np.zeros((3,), dtype=np.float32)
	if cl_main.cl.v_up is None:
		cl_main.cl.v_up = np.zeros((3,), dtype=np.float32)

	q_shared.AngleVectors(
		cl_main.cl.refdef.viewangles,
		cl_main.cl.v_forward,
		cl_main.cl.v_right,
		cl_main.cl.v_up,
	)

	cl_main.cl.refdef.fov_x = ops.fov + lerp * (ps.fov - ops.fov)
	cl_main.cl.refdef.blend[:] = ps.blend

	CL_AddViewWeapon (ps, ops)

"""
===============
CL_AddEntities

Emits all entities, particles, and lights to the refresh
===============
"""
def CL_AddEntities ():

	cl = cl_main.cl

	if cl_main.cls.state != client.connstate_t.ca_active:
		return

	if cl.time > cl.frame.servertime:
	
		if cl_main.cl_showclamp.value:
			common.Com_Printf ("high clamp {}\n".format(cl.time - cl.frame.servertime))
		cl.time = cl.frame.servertime
		cl.lerpfrac = 1.0
	
	elif cl.time < cl.frame.servertime - 100:
	
		if cl_main.cl_showclamp.value:
			common.Com_Printf ("low clamp {}\n".format(cl.frame.servertime-100 - cl.time))
		cl.time = cl.frame.servertime - 100
		cl.lerpfrac = 0
	
	else:
		cl.lerpfrac = 1.0 - (cl.frame.servertime - cl.time) * 0.01

	if cl_main.cl_timedemo.value:
		cl.lerpfrac = 1.0

#	CL_AddPacketEntities (&cl.frame);
#	CL_AddTEnts ();
#	CL_AddParticles ();
#	CL_AddDLights ();
#	CL_AddLightStyles ();

	CL_CalcViewValues ()
	# PMM - moved this here so the heat beam has the right values for the vieworg, and can lock the beam to the gun
	CL_AddPacketEntities (cl.frame)
#if 0
#	CL_AddProjectiles ();
#endif
	cl_tent.CL_AddTEnts ()
	cl_fx.CL_AddParticles ()
	cl_fx.CL_AddDLights ()
	cl_fx.CL_AddLightStyles ()



"""
===============
CL_GetEntitySoundOrigin

Called to get the sound spatialization origin
===============
"""
def CL_GetEntitySoundOrigin (ent: int): # vec3_t

	org = np.zeros((3,), dtype=np.float32)
	#centity_t	*old;

	if ent < 0 or ent >= q_shared.MAX_EDICTS:
		common.Com_Error (q_shared.ERR_DROP, "CL_GetEntitySoundOrigin: bad ent")
	old = cl_main.cl_entities[ent]
	q_shared.VectorCopy (old.lerp_origin, org)

	# FIXME: bmodel issues...

	return org
