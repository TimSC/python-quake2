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
from __future__ import annotations

import struct
import numpy as np
from linux import q_shlinux
from server import sv_init, sv_main, sv_user, sv_ents
from qcommon import net_chan, cmodel
from game import game
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import filesystem
from common import frame
from common import movemsg
from common import szone
"""
// sv_main.c -- server main program

#include "server.h"
"""
"""
=============================================================================

Com_Printf redirection

=============================================================================
"""
SV_OUTPUTBUF_LENGTH = common_h.MAX_MSGLEN - 16
sv_outputbuf = "" #char [SV_OUTPUTBUF_LENGTH]

"""
==================
SV_FlushRedirect
==================
"""
def SV_FlushRedirect (sv_redirected, outputbuf): #int, char *

	if sv_redirected == clientserver.RD_PACKET:
	
		net_chan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, net_chan.net_from, "print\n{}".format(outputbuf))
	elif sv_redirected == clientserver.RD_CLIENT:
	
		movemsg.MSG_WriteByte (sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_print.value)
		movemsg.MSG_WriteByte (sv_main.sv_client.netchan.message, shared.PRINT_HIGH)
		movemsg.MSG_WriteString (sv_main.sv_client.netchan.message, outputbuf.encode('ascii'))

"""
/*
=============================================================================

EVENT MESSAGES

=============================================================================
*/
"""
"""
=================
SV_ClientPrintf

Sends text across to be displayed if the level passes
=================
"""
def SV_ClientPrintf (cl, level, fmt, *args): #client_t *, int, char *, ...

	if level < cl.messagelevel:
		return

	# va_start (argptr,fmt); vsprintf (string, fmt,argptr); va_end (argptr);
	msg = fmt % args if args else fmt

	movemsg.MSG_WriteByte (cl.netchan.message, common_h.svc_ops_e.svc_print.value)
	movemsg.MSG_WriteByte (cl.netchan.message, level)
	movemsg.MSG_WriteString (cl.netchan.message, msg.encode('ascii'))

"""
=================
SV_BroadcastPrintf

Sends text to all active clients
=================
"""
def SV_BroadcastPrintf (level, fmt, *args): #int, char *, ...

	# va_start (argptr,fmt); vsprintf (string, fmt,argptr); va_end (argptr);
	msg = fmt % args if args else fmt

	# echo to console
	if frame.dedicated.value:
		clientserver.Com_Printf ("{}".format(msg))

	for cl in sv_init.svs.clients:
	
		if level < cl.messagelevel:
			continue
		if cl.state != sv_init.client_state_t.cs_spawned:
			continue
		movemsg.MSG_WriteByte (cl.netchan.message, common_h.svc_ops_e.svc_print.value)
		movemsg.MSG_WriteByte (cl.netchan.message, level)
		movemsg.MSG_WriteString (cl.netchan.message, msg.encode('ascii'))

"""
/*
=================
SV_BroadcastCommand

Sends text to all active clients
=================
"""
def SV_BroadcastCommand (msg): #char *

	if not sv_init.sv.state:
		return

	movemsg.MSG_WriteByte(sv_init.sv.multicast, struct.pack("B", common_h.svc_ops_e.svc_stufftext.value))
	movemsg.MSG_WriteString(sv_init.sv.multicast, msg.encode('ascii'))
	SV_Multicast (None, shared.multicast_t.MULTICAST_ALL_R)


"""
=================
SV_Multicast

Sends the contents of sv_init.sv.multicast to a subset of the clients,
then clears sv_init.sv.multicast.

MULTICAST_ALL	same as broadcast (origin can be NULL)
MULTICAST_PVS	send to clients potentially visible from org
MULTICAST_PHS	send to clients potentially hearable from org
=================
"""
def SV_Multicast (origin, to): #vec3_t, multicast_t

	# accept both enum members and bare int values
	if hasattr(to, "value"):
		to = to.value

	#sv_init.client_t	*client;
	#byte		*mask;
	#int			leafnum, cluster;
	#int			j;
	#qboolean	reliable;
	#int			area1, area2;

	reliable = False
	mask = None

	if to != shared.multicast_t.MULTICAST_ALL_R.value and to != shared.multicast_t.MULTICAST_ALL.value:
	
		leafnum = cmodel.CM_PointLeafnum (origin)
		area1 = cmodel.CM_LeafArea (leafnum)
	
	else:
		leafnum = 0	# just to avoid compiler warnings
		area1 = 0
	
	# if doing a serverrecord, store everything
	if sv_init.svs.demofile:
		szone.SZ_Write(sv_init.svs.demo_multicast, sv_init.sv.multicast.data)
	
	if to == shared.multicast_t.MULTICAST_ALL_R.value:
		reliable = True	# intentional fallthrough
	if to == shared.multicast_t.MULTICAST_ALL_R.value or to == shared.multicast_t.MULTICAST_ALL.value:
		leafnum = 0
		mask = None

	if to == shared.multicast_t.MULTICAST_PHS_R.value:
		reliable = True	# intentional fallthrough
	if to == shared.multicast_t.MULTICAST_PHS_R.value or to == shared.multicast_t.MULTICAST_PHS.value:
		leafnum = cmodel.CM_PointLeafnum (origin)
		cluster = cmodel.CM_LeafCluster (leafnum)
		mask = cmodel.CM_ClusterPHS (cluster)

	if to == shared.multicast_t.MULTICAST_PVS_R.value:
		reliable = True	# intentional fallthrough
	if to == shared.multicast_t.MULTICAST_PVS_R.value or to == shared.multicast_t.MULTICAST_PVS.value:
		leafnum = cmodel.CM_PointLeafnum (origin)
		cluster = cmodel.CM_LeafCluster (leafnum)
		mask = cmodel.CM_ClusterPVS (cluster)

	if to != shared.multicast_t.MULTICAST_ALL_R.value and to != shared.multicast_t.MULTICAST_ALL.value and \
		to != shared.multicast_t.MULTICAST_PHS_R.value and to != shared.multicast_t.MULTICAST_PHS.value and \
		to != shared.multicast_t.MULTICAST_PVS_R.value and to != shared.multicast_t.MULTICAST_PVS.value:

		mask = None
		clientserver.Com_Error (common_h.ERR_FATAL, "SV_Multicast: bad to:{}".format(to))

	# send the data to all relevent clients
	for client in sv_init.svs.clients:
	
		if client.state == sv_init.client_state_t.cs_free or client.state == sv_init.client_state_t.cs_zombie:
			continue
		if client.state != sv_init.client_state_t.cs_spawned and not reliable:
			continue

		if mask is not None:
	
			leafnum = cmodel.CM_PointLeafnum (client.edict.s.origin)
			cluster = cmodel.CM_LeafCluster (leafnum)
			area2 = cmodel.CM_LeafArea (leafnum)
			if not cmodel.CM_AreasConnected (area1, area2):
				continue
			if ( mask is not None and (not(mask[cluster>>3] & (1<<(cluster&7)) ) ) ):
				continue

		if reliable:
			szone.SZ_Write(client.netchan.message, sv_init.sv.multicast.data)
		else:
			szone.SZ_Write(client.datagram, sv_init.sv.multicast.data)
	
	szone.SZ_Clear(sv_init.sv.multicast)



"""
==================
SV_StartSound

Each entity can have eight independant sound sources, like voice,
weapon, feet, etc.

If cahnnel & 8, the sound will be sent to everyone, not just
things in the PHS.

FIXME: if entity isn't in PHS, they must be forced to be sent or
have the origin explicitly sent.

Channel 0 is an auto-allocate channel, the others override anything
already running on that entity/channel pair.

An attenuation of 0 will play full volume everywhere in the level.
Larger attenuations will drop off.  (max 4 attenuation)

Timeofs can range from 0.0 to 0.1 to cause sounds to be started
later in the frame than they normally would.

If origin is NULL, the origin is determined from the entity origin
or the midpoint of the entity box for bmodels.
==================
*/  
"""
def SV_StartSound (origin, entity, channel, soundindex, volume, attenuation, timeofs): #vec3_t, edict_t *, int, int, float, float, float

	#int sendchan, flags, i, ent
	#qboolean use_phs
	#vec3_t origin_v

	if volume < 0 or volume > 1.0:
		clientserver.Com_Error (common_h.ERR_FATAL, "SV_StartSound: volume = %f", volume)

	if attenuation < 0 or attenuation > 4:
		clientserver.Com_Error (common_h.ERR_FATAL, "SV_StartSound: attenuation = %f", attenuation)

	#if channel < 0 or channel > 15
	#	Com_Error (ERR_FATAL, "SV_StartSound: channel = %i", channel)

	if timeofs < 0 or timeofs > 0.255:
		clientserver.Com_Error (common_h.ERR_FATAL, "SV_StartSound: timeofs = %f", timeofs)

	ent = sv_init.NUM_FOR_EDICT(entity)

	if channel & 8:	# no PHS flag
		use_phs = False
		channel &= 7
	else:
		use_phs = True

	sendchan = (ent<<3) | (channel&7)

	flags = 0
	if volume != common_h.DEFAULT_SOUND_PACKET_VOLUME:
		flags |= common_h.SND_VOLUME
	if attenuation != common_h.DEFAULT_SOUND_PACKET_ATTENUATION:
		flags |= common_h.SND_ATTENUATION

	# the client doesn't know that bmodels have weird origins
	# the origin can also be explicitly set
	if (entity.svflags & game.SVF_NOCLIENT) \
		or entity.solid == game.SOLID_BSP \
		or origin is not None:
		flags |= common_h.SND_POS

	# always send the entity number for channel overrides
	flags |= common_h.SND_ENT

	if timeofs:
		flags |= common_h.SND_OFFSET

	# use the entity origin unless it is a bmodel or explicitly specified
	origin_v = np.zeros((3,), dtype=np.float32)
	if origin is None:
		if entity.solid == game.SOLID_BSP:
			for i in range(3):
				origin_v[i] = entity.s.origin[i]+0.5*(entity.mins[i]+entity.maxs[i])
		else:
			shared.VectorCopy (entity.s.origin, origin_v)
		origin = origin_v

	movemsg.MSG_WriteByte (sv_init.sv.multicast, common_h.svc_ops_e.svc_sound.value)
	movemsg.MSG_WriteByte (sv_init.sv.multicast, flags)
	movemsg.MSG_WriteByte (sv_init.sv.multicast, soundindex)

	if flags & common_h.SND_VOLUME:
		movemsg.MSG_WriteByte (sv_init.sv.multicast, volume*255)
	if flags & common_h.SND_ATTENUATION:
		movemsg.MSG_WriteByte (sv_init.sv.multicast, attenuation*64)
	if flags & common_h.SND_OFFSET:
		movemsg.MSG_WriteByte (sv_init.sv.multicast, timeofs*1000)

	if flags & common_h.SND_ENT:
		movemsg.MSG_WriteShort (sv_init.sv.multicast, sendchan)

	if flags & common_h.SND_POS:
		movemsg.MSG_WritePos (sv_init.sv.multicast, origin)

	# if the sound doesn't attenuate, send it to everyone
	# (global radio chatter, voiceovers, etc)
	if attenuation == shared.ATTN_NONE:
		use_phs = False

	if channel & shared.CHAN_RELIABLE:
		if use_phs:
			SV_Multicast (origin, shared.multicast_t.MULTICAST_PHS_R)
		else:
			SV_Multicast (origin, shared.multicast_t.MULTICAST_ALL_R)
	else:
		if use_phs:
			SV_Multicast (origin, shared.multicast_t.MULTICAST_PHS)
		else:
			SV_Multicast (origin, shared.multicast_t.MULTICAST_ALL)

"""
/*
===============================================================================

FRAME UPDATES

===============================================================================
*/
"""
"""
/*
=======================
SV_SendClientDatagram
=======================
"""
def SV_SendClientDatagram (client)-> bool: #sv_init.client_t

	#byte		msg_buf[qcommon.MAX_MSGLEN];
	#sizebuf_t	msg;
	msg = common_h.sizebuf_t()

	sv_ents.SV_BuildClientFrame (client)

	szone.SZ_Init (msg, common_h.MAX_MSGLEN)
	msg.allowoverflow = True

	# send over all the relevant entity_state_t
	# and the player_state_t
	sv_ents.SV_WriteFrameToClient (client, msg)

	# copy the accumulated multicast datagram
	# for this client out to the message
	# it is necessary for this to be after the WriteEntities
	# so that entity references will be current
	if client.datagram.overflowed:
		clientserver.Com_Printf ("WARNING: datagram overflowed for {}\n".format(client.name))
	else:
		szone.SZ_Write (msg, bytes(client.datagram.data[:client.datagram.cursize]))
	szone.SZ_Clear (client.datagram)

	if msg.overflowed:
		# must have room left for the packet header
		clientserver.Com_Printf ("WARNING: msg overflowed for {}\n".format(client.name))
		szone.SZ_Clear (msg)

	# send the datagram
	net_chan.Netchan_Transmit (client.netchan, bytes(msg.data[:msg.cursize]))

	# record the size for rate estimation
	client.message_size[sv_init.sv.framenum % sv_init.RATE_MESSAGES] = msg.cursize

	return True


"""
/*
==================
SV_DemoCompleted
==================
"""
def SV_DemoCompleted ():

	if sv_init.sv.demofile:
	
		filesystem.FS_FCloseFile (sv_init.sv.demofile)
		sv_init.sv.demofile = 0
	
	sv_user.SV_Nextserver ()

"""
=======================
SV_RateDrop

Returns true if the client is over its current
bandwidth estimation and should not be sent another packet
=======================
"""
def SV_RateDrop (c)->bool:#sv_init.client_t*

	return False
	"""
	int		total;
	int		i;

	// never drop over the loopback
	if (c->netchan.remote_address.type == NA_LOOPBACK)
		return false;

	total = 0;

	for (i = 0 ; i < RATE_MESSAGES ; i++)
	{
		total += c->message_size[i];
	}

	if (total > c->rate)
	{
		c->surpressCount++;
		c->message_size[sv_init.sv.framenum % RATE_MESSAGES] = 0;
		return true;
	}

	return false;
}

/*
=======================
SV_SendClientMessages
=======================
"""
def SV_SendClientMessages ():

	#int			i;
	#sv_init.client_t	*c;
	#int			r;
	msgbuf = b"" # byte[qcommon.MAX_MSGLEN]
	msglen = 0 # int

	# read the next demo message if needed
	if sv_init.sv.state == sv_init.server_state_t.ss_demo and sv_init.sv.demofile:
	
		if sv_main.sv_paused.value != 0:
			msglen = 0
		else:
			# get the next message
			data = filesystem.FS_FRead (4, 1, sv_init.sv.demofile)
			r = 1 if len(data) == 4 else 0 # r = fread (&msglen, 4, 1, sv.demofile);
			if r != 1:
			
				SV_DemoCompleted ()
				return
			
			msglen = shared_c.LittleSLong (data)
			if msglen == -1:
			
				SV_DemoCompleted ()
				return
			
			if msglen > common_h.MAX_MSGLEN:
				clientserver.Com_Error (shared.ERR_DROP, "SV_SendClientMessages: msglen > MAX_MSGLEN")
			msgbuf = filesystem.FS_FRead (msglen, 1, sv_init.sv.demofile)
			r = 1 if len(msgbuf) == msglen else 0 # r = fread (msgbuf, msglen, 1, sv.demofile);
			if r != 1:
			
				SV_DemoCompleted ()
				return
			
		


	# send a message to each connected client
	for c in sv_init.svs.clients:
	
		if not c.state:
			continue

		# if the reliable message overflowed,
		# drop the client
		if c.netchan.message.overflowed:
		
			szone.SZ_Clear (c.netchan.message)
			szone.SZ_Clear (c.datagram)
			SV_BroadcastPrintf (shared.PRINT_HIGH, "%s overflowed\n", c.name)
			sv_main.SV_DropClient (c)
		
		if (sv_init.sv.state == sv_init.server_state_t.ss_cinematic 
			or sv_init.sv.state == sv_init.server_state_t.ss_demo 
			or sv_init.sv.state == sv_init.server_state_t.ss_pic):

			net_chan.Netchan_Transmit (c.netchan, msgbuf)

		elif c.state == sv_init.client_state_t.cs_spawned:
		
			# don't overrun bandwidth
			if SV_RateDrop (c):
				continue

			SV_SendClientDatagram (c)
		
		else:
		
			# just update reliableif needed
			if c.netchan.message.data is not None or q_shlinux.curtime - c.netchan.last_sent > 1000:
				net_chan.Netchan_Transmit (c.netchan, b"")
		
	
