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
from server import sv_init, sv_main, sv_game
from qcommon import qcommon, common, cmodel
from game import q_shared, game
"""
#include "server.h"

/*
=============================================================================

Encode a client frame onto the network channel

=============================================================================
*/
"""

"""
byte		fatpvs[65536/8];	// 32767 is MAX_MAP_LEAFS
"""
fatpvs = bytearray(65536 // 8)


"""
=============
SV_EmitPacketEntities

Writes a delta update of an entity_state_t list to the message.
=============
"""
def SV_EmitPacketEntities (frm, to, msg): #client_frame_t *, client_frame_t *, sizebuf_t *

	"""
	entity_state_t	*oldent, *newent;
	int		oldindex, newindex;
	int		oldnum, newnum;
	int		from_num_entities;
	int		bits;
	"""
	oldent = None
	newent = None
	oldindex = 0
	newindex = 0
	oldnum = 0
	newnum = 0
	bits = 0

	common.MSG_WriteByte (msg, qcommon.svc_ops_e.svc_packetentities.value)

	if not frm:
		from_num_entities = 0
	else:
		from_num_entities = frm.num_entities

	newindex = 0
	oldindex = 0
	while newindex < to.num_entities or oldindex < from_num_entities:
		if newindex >= to.num_entities:
			newnum = 9999
		else:
			newent = sv_init.svs.client_entities[(to.first_entity+newindex)%sv_init.svs.num_client_entities]
			newnum = newent.number

		if oldindex >= from_num_entities:
			oldnum = 9999
		else:
			oldent = sv_init.svs.client_entities[(frm.first_entity+oldindex)%sv_init.svs.num_client_entities]
			oldnum = oldent.number

		if newnum == oldnum:
			# delta update from old position
			# because the force parm is false, this will not result
			# in any bytes being emited if the entity has not changed at all
			# note that players are always 'newentities', this updates their oldorigin always
			# and prevents warping
			common.MSG_WriteDeltaEntity (oldent, newent, msg, False, newent.number <= int(sv_main.maxclients.value))
			oldindex += 1
			newindex += 1
			continue

		if newnum < oldnum:
			# this is a new entity, send it from the baseline
			common.MSG_WriteDeltaEntity (sv_init.sv.baselines[newnum], newent, msg, True, True)
			newindex += 1
			continue

		if newnum > oldnum:
			# the old entity isn't present in the new message
			bits = qcommon.U_REMOVE
			if oldnum >= 256:
				bits |= qcommon.U_NUMBER16 | qcommon.U_MOREBITS1

			common.MSG_WriteByte (msg, bits&255)
			if bits & 0x0000ff00:
				common.MSG_WriteByte (msg, (bits>>8)&255)

			if bits & qcommon.U_NUMBER16:
				common.MSG_WriteShort (msg, oldnum)
			else:
				common.MSG_WriteByte (msg, oldnum)

			oldindex += 1
			continue

	common.MSG_WriteShort (msg, 0)	# end of packetentities


"""
=============
SV_WritePlayerstateToClient

=============
"""
def SV_WritePlayerstateToClient (frm, to, msg): #client_frame_t *, client_frame_t *, sizebuf_t *

	"""
	int				i;
	int				pflags;
	player_state_t	*ps, *ops;
	player_state_t	dummy;
	int				statbits;
	"""
	#int i, pflags, statbits

	ps = to.ps
	if not frm:
		dummy = q_shared.player_state_t()
		ops = dummy
	else:
		ops = frm.ps

	#
	# determine what needs to be sent
	#
	pflags = 0

	if ps.pmove.pm_type != ops.pmove.pm_type:
		pflags |= qcommon.PS_M_TYPE

	if (ps.pmove.origin[0] != ops.pmove.origin[0]
		or ps.pmove.origin[1] != ops.pmove.origin[1]
		or ps.pmove.origin[2] != ops.pmove.origin[2]):
		pflags |= qcommon.PS_M_ORIGIN

	if (ps.pmove.velocity[0] != ops.pmove.velocity[0]
		or ps.pmove.velocity[1] != ops.pmove.velocity[1]
		or ps.pmove.velocity[2] != ops.pmove.velocity[2]):
		pflags |= qcommon.PS_M_VELOCITY

	if ps.pmove.pm_time != ops.pmove.pm_time:
		pflags |= qcommon.PS_M_TIME

	if ps.pmove.pm_flags != ops.pmove.pm_flags:
		pflags |= qcommon.PS_M_FLAGS

	if ps.pmove.gravity != ops.pmove.gravity:
		pflags |= qcommon.PS_M_GRAVITY

	if (ps.pmove.delta_angles[0] != ops.pmove.delta_angles[0]
		or ps.pmove.delta_angles[1] != ops.pmove.delta_angles[1]
		or ps.pmove.delta_angles[2] != ops.pmove.delta_angles[2]):
		pflags |= qcommon.PS_M_DELTA_ANGLES

	if (ps.viewoffset[0] != ops.viewoffset[0]
		or ps.viewoffset[1] != ops.viewoffset[1]
		or ps.viewoffset[2] != ops.viewoffset[2]):
		pflags |= qcommon.PS_VIEWOFFSET

	if (ps.viewangles[0] != ops.viewangles[0]
		or ps.viewangles[1] != ops.viewangles[1]
		or ps.viewangles[2] != ops.viewangles[2]):
		pflags |= qcommon.PS_VIEWANGLES

	if (ps.kick_angles[0] != ops.kick_angles[0]
		or ps.kick_angles[1] != ops.kick_angles[1]
		or ps.kick_angles[2] != ops.kick_angles[2]):
		pflags |= qcommon.PS_KICKANGLES

	if (ps.blend[0] != ops.blend[0]
		or ps.blend[1] != ops.blend[1]
		or ps.blend[2] != ops.blend[2]
		or ps.blend[3] != ops.blend[3]):
		pflags |= qcommon.PS_BLEND

	if ps.fov != ops.fov:
		pflags |= qcommon.PS_FOV

	if ps.rdflags != ops.rdflags:
		pflags |= qcommon.PS_RDFLAGS

	if ps.gunframe != ops.gunframe:
		pflags |= qcommon.PS_WEAPONFRAME

	pflags |= qcommon.PS_WEAPONINDEX

	#
	# write it
	#
	common.MSG_WriteByte (msg, qcommon.svc_ops_e.svc_playerinfo.value)
	common.MSG_WriteShort (msg, pflags)

	#
	# write the pmove_state_t
	#
	if pflags & qcommon.PS_M_TYPE:
		common.MSG_WriteByte (msg, ps.pmove.pm_type)

	if pflags & qcommon.PS_M_ORIGIN:
		common.MSG_WriteShort (msg, int(ps.pmove.origin[0]))
		common.MSG_WriteShort (msg, int(ps.pmove.origin[1]))
		common.MSG_WriteShort (msg, int(ps.pmove.origin[2]))

	if pflags & qcommon.PS_M_VELOCITY:
		common.MSG_WriteShort (msg, int(ps.pmove.velocity[0]))
		common.MSG_WriteShort (msg, int(ps.pmove.velocity[1]))
		common.MSG_WriteShort (msg, int(ps.pmove.velocity[2]))

	if pflags & qcommon.PS_M_TIME:
		common.MSG_WriteByte (msg, ps.pmove.pm_time)

	if pflags & qcommon.PS_M_FLAGS:
		common.MSG_WriteByte (msg, ps.pmove.pm_flags)

	if pflags & qcommon.PS_M_GRAVITY:
		common.MSG_WriteShort (msg, int(ps.pmove.gravity))

	if pflags & qcommon.PS_M_DELTA_ANGLES:
		common.MSG_WriteShort (msg, int(ps.pmove.delta_angles[0]))
		common.MSG_WriteShort (msg, int(ps.pmove.delta_angles[1]))
		common.MSG_WriteShort (msg, int(ps.pmove.delta_angles[2]))

	#
	# write the rest of the player_state_t
	#
	if pflags & qcommon.PS_VIEWOFFSET:
		common.MSG_WriteChar (msg, int(ps.viewoffset[0]*4))
		common.MSG_WriteChar (msg, int(ps.viewoffset[1]*4))
		common.MSG_WriteChar (msg, int(ps.viewoffset[2]*4))

	if pflags & qcommon.PS_VIEWANGLES:
		common.MSG_WriteAngle16 (msg, ps.viewangles[0])
		common.MSG_WriteAngle16 (msg, ps.viewangles[1])
		common.MSG_WriteAngle16 (msg, ps.viewangles[2])

	if pflags & qcommon.PS_KICKANGLES:
		common.MSG_WriteChar (msg, int(ps.kick_angles[0]*4))
		common.MSG_WriteChar (msg, int(ps.kick_angles[1]*4))
		common.MSG_WriteChar (msg, int(ps.kick_angles[2]*4))

	if pflags & qcommon.PS_WEAPONINDEX:
		common.MSG_WriteByte (msg, ps.gunindex)

	if pflags & qcommon.PS_WEAPONFRAME:
		common.MSG_WriteByte (msg, ps.gunframe)
		common.MSG_WriteChar (msg, int(ps.gunoffset[0]*4))
		common.MSG_WriteChar (msg, int(ps.gunoffset[1]*4))
		common.MSG_WriteChar (msg, int(ps.gunoffset[2]*4))
		common.MSG_WriteChar (msg, int(ps.gunangles[0]*4))
		common.MSG_WriteChar (msg, int(ps.gunangles[1]*4))
		common.MSG_WriteChar (msg, int(ps.gunangles[2]*4))

	if pflags & qcommon.PS_BLEND:
		common.MSG_WriteByte (msg, int(ps.blend[0]*255))
		common.MSG_WriteByte (msg, int(ps.blend[1]*255))
		common.MSG_WriteByte (msg, int(ps.blend[2]*255))
		common.MSG_WriteByte (msg, int(ps.blend[3]*255))
	if pflags & qcommon.PS_FOV:
		common.MSG_WriteByte (msg, int(ps.fov))
	if pflags & qcommon.PS_RDFLAGS:
		common.MSG_WriteByte (msg, ps.rdflags)

	# send stats
	statbits = 0
	for i in range(q_shared.MAX_STATS):
		if ps.stats[i] != ops.stats[i]:
			statbits |= 1<<i
	common.MSG_WriteLong (msg, statbits)
	for i in range(q_shared.MAX_STATS):
		if statbits & (1<<i):
			common.MSG_WriteShort (msg, ps.stats[i])


"""
==================
SV_WriteFrameToClient
==================
"""
def SV_WriteFrameToClient (client, msg): #client_t *, sizebuf_t *

	"""
	client_frame_t		*frame, *oldframe;
	int					lastframe;
	"""
	#client_frame_t *frame, *oldframe
	#int lastframe

	# this is the frame we are creating
	frame = client.frames[sv_init.sv.framenum & qcommon.UPDATE_MASK]

	if client.lastframe <= 0:
		# client is asking for a retransmit
		oldframe = None
		lastframe = -1
	elif sv_init.sv.framenum - client.lastframe >= (qcommon.UPDATE_BACKUP - 3):
		# client hasn't gotten a good message through in a long time
		oldframe = None
		lastframe = -1
	else:
		# we have a valid message to delta from
		oldframe = client.frames[client.lastframe & qcommon.UPDATE_MASK]
		lastframe = client.lastframe

	common.MSG_WriteByte (msg, qcommon.svc_ops_e.svc_frame.value)
	common.MSG_WriteLong (msg, sv_init.sv.framenum)
	common.MSG_WriteLong (msg, lastframe)	# what we are delta'ing from
	common.MSG_WriteByte (msg, client.surpressCount)	# rate dropped packets
	client.surpressCount = 0

	# send over the areabits
	common.MSG_WriteByte (msg, frame.areabytes)
	common.SZ_Write (msg, bytes(frame.areabits[:frame.areabytes]))

	# delta encode the playerstate
	SV_WritePlayerstateToClient (oldframe, frame, msg)

	# delta encode the entities
	SV_EmitPacketEntities (oldframe, frame, msg)


"""
============
SV_FatPVS

The client will interpolate the view position,
so we can't use a single PVS point
===========
"""
def SV_FatPVS (org): #vec3_t

	"""
	int		leafs[64];
	int		i, j, count;
	int		longs;
	byte	*src;
	vec3_t	mins, maxs;
	"""
	#int i, j, count, longs
	leafs = [0]*64
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)

	for i in range(3):
		mins[i] = org[i] - 8
		maxs[i] = org[i] + 8

	topnode = [0]
	count = cmodel.CM_BoxLeafnums (mins, maxs, leafs, 64, topnode)
	if count < 1:
		common.Com_Error (qcommon.ERR_FATAL, "SV_FatPVS: count < 1")
	longs = (cmodel.CM_NumClusters()+31)>>5
	n = longs<<2

	# convert leafs to clusters
	for i in range(count):
		leafs[i] = cmodel.CM_LeafCluster(leafs[i])

	src = cmodel.CM_ClusterPVS(leafs[0])
	for j in range(n):
		fatpvs[j] = src[j]
	# or in all the other leaf bits
	for i in range(1, count):
		for j in range(i):
			if leafs[i] == leafs[j]:
				break
		if j != i:
			continue		# already have the cluster we want
		src = cmodel.CM_ClusterPVS(leafs[i])
		for j in range(n):
			fatpvs[j] |= src[j]


"""
=============
SV_BuildClientFrame

Decides which entities are going to be visible to the client, and
copies off the playerstat and areabits.
=============
"""
def SV_BuildClientFrame (client): #client_t *

	"""
	int		e, i;
	vec3_t	org;
	edict_t	*ent;
	edict_t	*clent;
	client_frame_t	*frame;
	entity_state_t	*state;
	int		l;
	int		clientarea, clientcluster;
	int		leafnum;
	int		c_fullsend;
	byte	*clientphs;
	byte	*bitvector;
	"""
	#int e, i, l, clientarea, clientcluster, leafnum, c_fullsend

	clent = client.edict
	if not clent.client:
		return		# not in game yet

	# this is the frame we are creating
	frame = client.frames[sv_init.sv.framenum & qcommon.UPDATE_MASK]

	frame.senttime = sv_init.svs.realtime # save it for ping calc later

	# find the client's PVS
	org = np.zeros((3,), dtype=np.float32)
	for i in range(3):
		org[i] = clent.client.ps.pmove.origin[i]*0.125 + clent.client.ps.viewoffset[i]

	leafnum = cmodel.CM_PointLeafnum (org)
	clientarea = cmodel.CM_LeafArea (leafnum)
	clientcluster = cmodel.CM_LeafCluster (leafnum)

	# calculate the visible areas
	frame.areabytes = cmodel.CM_WriteAreaBits (frame.areabits, clientarea)

	# grab the current player_state_t
	frame.ps = clent.client.ps

	SV_FatPVS (org)
	clientphs = cmodel.CM_ClusterPHS (clientcluster)

	# build up the list of visible entities
	frame.num_entities = 0
	frame.first_entity = sv_init.svs.next_client_entities

	c_fullsend = 0

	for e in range(1, sv_game.ge.num_edicts):
		ent = sv_init.EDICT_NUM(e)

		# ignore ents without visible models
		if ent.svflags & game.SVF_NOCLIENT:
			continue

		# ignore ents without visible models unless they have an effect
		if not ent.s.modelindex and not ent.s.effects and not ent.s.sound \
			and not ent.s.event:
			continue

		# ignore if not touching a PV leaf
		if ent is not clent:
			# check area
			if not cmodel.CM_AreasConnected (clientarea, ent.areanum):
				# doors can legally straddle two areas, so
				# we may need to check another one
				if not ent.areanum2 \
					or not cmodel.CM_AreasConnected (clientarea, ent.areanum2):
					continue		# blocked by a door

			# beams just check one point for PHS
			if ent.s.renderfx & q_shared.RF_BEAM:
				l = ent.clusternums[0]
				if not (clientphs[l>>3] & (1<<(l&7))):
					continue
			else:
				# FIXME: if an ent has a model and a sound, but isn't
				# in the PVS, only the PHS, clear the model
				if ent.s.sound:
					bitvector = fatpvs	#clientphs;
				else:
					bitvector = fatpvs

				if ent.num_clusters == -1:
					# too many leafs for individual check, go by headnode
					if not cmodel.CM_HeadnodeVisible (ent.headnode, bitvector):
						continue
					c_fullsend += 1
				else:
					# check individual leafs
					for i in range(ent.num_clusters):
						l = ent.clusternums[i]
						if bitvector[l>>3] & (1<<(l&7)):
							break
					if i == ent.num_clusters:
						continue		# not visible

				if not ent.s.modelindex:
					# don't send sounds if they will be attenuated away
					delta = np.zeros((3,), dtype=np.float32)
					q_shared.VectorSubtract (org, ent.s.origin, delta)
					length = q_shared.VectorLength (delta)
					if length > 400:
						continue

		# add it to the circular client_entities array
		state = sv_init.svs.client_entities[sv_init.svs.next_client_entities%sv_init.svs.num_client_entities]
		if ent.s.number != e:
			common.Com_DPrintf ("FIXING ENT->S.NUMBER!!!\n")
			ent.s.number = e
		state.copy (ent.s)

		# don't mark players missiles as solid
		if ent.owner is client.edict:
			state.solid = 0

		sv_init.svs.next_client_entities += 1
		frame.num_entities += 1


"""
==================
SV_RecordDemoMessage

Save everything in the world out without deltas.
Used for recording footage for merged or assembled demos
==================
"""
def SV_RecordDemoMessage ():

	"""
	int			e;
	edict_t		*ent;
	entity_state_t	nostate;
	sizebuf_t	buf;
	byte		buf_data[32768];
	int			len;
	"""
	#int e, len

	if not sv_init.svs.demofile:
		return

	nostate = q_shared.entity_state_t()
	buf = qcommon.sizebuf_t()
	common.SZ_Init (buf, 32768)

	# write a frame message that doesn't contain a player_state_t
	common.MSG_WriteByte (buf, qcommon.svc_ops_e.svc_frame.value)
	common.MSG_WriteLong (buf, sv_init.sv.framenum)

	common.MSG_WriteByte (buf, qcommon.svc_ops_e.svc_packetentities.value)

	e = 1
	ent = sv_init.EDICT_NUM(e)
	while e < sv_game.ge.num_edicts:
		# ignore ents without visible models unless they have an effect
		if ent.inuse \
			and ent.s.number \
			and (ent.s.modelindex or ent.s.effects or ent.s.sound or ent.s.event) \
			and not (ent.svflags & game.SVF_NOCLIENT):
			common.MSG_WriteDeltaEntity (nostate, ent.s, buf, False, True)

		e += 1
		ent = sv_init.EDICT_NUM(e)

	common.MSG_WriteShort (buf, 0)		# end of packetentities

	# now add the accumulated multicast information
	common.SZ_Write (buf, bytes(sv_init.svs.demo_multicast.data[:sv_init.svs.demo_multicast.cursize]))
	common.SZ_Clear (sv_init.svs.demo_multicast)

	# now write the entire message to the file, prefixed by the length
	length = q_shared.LittleLong (buf.cursize)
	sv_init.svs.demofile.write(length.to_bytes(4, 'little'))
	sv_init.svs.demofile.write(bytes(buf.data[:buf.cursize]))
