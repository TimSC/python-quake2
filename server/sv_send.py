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
import struct
import numpy as np
from linux import q_shlinux
from server import sv_init, sv_main, sv_user
from qcommon import qcommon, net_chan, cmodel, common
from game import q_shared, game
"""
// sv_main.c -- server main program

#include "server.h"
"""
"""
=============================================================================

Com_Printf redirection

=============================================================================
"""
SV_OUTPUTBUF_LENGTH = qcommon.MAX_MSGLEN - 16
sv_outputbuf = "" #char [SV_OUTPUTBUF_LENGTH]

"""
==================
SV_FlushRedirect
==================
"""
def SV_FlushRedirect (sv_redirected, outputbuf): #int, char *

	if sv_redirected == common.RD_PACKET:
	
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, "print\n{}".format(outputbuf))
	elif sv_redirected == common.RD_CLIENT:
	
		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_print.value)
		common.MSG_WriteByte (sv_main.sv_client.netchan.message, q_shared.PRINT_HIGH)
		common.MSG_WriteString (sv_main.sv_client.netchan.message, outputbuf.encode('ascii'))

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
def SV_ClientPrintf (cl, level, msg): #client_t *, int, char *

	if level < cl.messagelevel:
		return

	common.MSG_WriteByte (cl.netchan.message, qcommon.svc_ops_e.svc_print.value)
	common.MSG_WriteByte (cl.netchan.message, level)
	common.MSG_WriteString (cl.netchan.message, msg.encode('ascii'))

"""
=================
SV_BroadcastPrintf

Sends text to all active clients
=================
"""
def SV_BroadcastPrintf (level, msg): #int, char *

	# echo to console
	if common.dedicated.value:
		common.Com_Printf ("{}".format(msg))

	for cl in sv_init.svs.clients:
	
		if level < cl.messagelevel:
			continue
		if cl.state != sv_init.client_state_t.cs_spawned:
			continue
		common.MSG_WriteByte (cl.netchan.message, qcommon.svc_ops_e.svc_print.value)
		common.MSG_WriteByte (cl.netchan.message, level)
		common.MSG_WriteString (cl.netchan.message, msg.encode('ascii'))

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

	common.MSG_WriteByte(sv_init.sv.multicast, struct.pack("B", qcommon.svc_ops_e.svc_stufftext.value))
	common.MSG_WriteString(sv_init.sv.multicast, msg.encode('ascii'))
	SV_Multicast (None, q_shared.multicast_t.MULTICAST_ALL_R)


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

	if to != q_shared.multicast_t.MULTICAST_ALL_R.value and to != q_shared.multicast_t.MULTICAST_ALL.value:
	
		leafnum = cmodel.CM_PointLeafnum (origin)
		area1 = cmodel.CM_LeafArea (leafnum)
	
	else:
		leafnum = 0	# just to avoid compiler warnings
		area1 = 0
	
	# if doing a serverrecord, store everything
	if sv_init.svs.demofile:
		common.SZ_Write(sv_init.svs.demo_multicast, sv_init.sv.multicast.data)
	
	if to == q_shared.multicast_t.MULTICAST_ALL_R.value:
		reliable = True	# intentional fallthrough
	if to == q_shared.multicast_t.MULTICAST_ALL_R.value or to == q_shared.multicast_t.MULTICAST_ALL.value:
		leafnum = 0
		mask = None

	if to == q_shared.multicast_t.MULTICAST_PHS_R.value:
		reliable = True	# intentional fallthrough
	if to == q_shared.multicast_t.MULTICAST_PHS_R.value or to == q_shared.multicast_t.MULTICAST_PHS.value:
		leafnum = cmodel.CM_PointLeafnum (origin)
		cluster = cmodel.CM_LeafCluster (leafnum)
		mask = cmodel.CM_ClusterPHS (cluster)

	if to == q_shared.multicast_t.MULTICAST_PVS_R.value:
		reliable = True	# intentional fallthrough
	if to == q_shared.multicast_t.MULTICAST_PVS_R.value or to == q_shared.multicast_t.MULTICAST_PVS.value:
		leafnum = cmodel.CM_PointLeafnum (origin)
		cluster = cmodel.CM_LeafCluster (leafnum)
		mask = cmodel.CM_ClusterPVS (cluster)

	if to != q_shared.multicast_t.MULTICAST_ALL_R.value and to != q_shared.multicast_t.MULTICAST_ALL.value and \
		to != q_shared.multicast_t.MULTICAST_PHS_R.value and to != q_shared.multicast_t.MULTICAST_PHS.value and \
		to != q_shared.multicast_t.MULTICAST_PVS_R.value and to != q_shared.multicast_t.MULTICAST_PVS.value:

		mask = None
		common.Com_Error (qcommon.ERR_FATAL, "SV_Multicast: bad to:{}".format(to))

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
			common.SZ_Write(client.netchan.message, sv_init.sv.multicast.data)
		else:
			common.SZ_Write(client.datagram, sv_init.sv.multicast.data)
	
	common.SZ_Clear(sv_init.sv.multicast)



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
		common.Com_Error (qcommon.ERR_FATAL, "SV_StartSound: volume = %f", volume)

	if attenuation < 0 or attenuation > 4:
		common.Com_Error (qcommon.ERR_FATAL, "SV_StartSound: attenuation = %f", attenuation)

	#if channel < 0 or channel > 15
	#	Com_Error (ERR_FATAL, "SV_StartSound: channel = %i", channel)

	if timeofs < 0 or timeofs > 0.255:
		common.Com_Error (qcommon.ERR_FATAL, "SV_StartSound: timeofs = %f", timeofs)

	ent = sv_init.NUM_FOR_EDICT(entity)

	if channel & 8:	# no PHS flag
		use_phs = False
		channel &= 7
	else:
		use_phs = True

	sendchan = (ent<<3) | (channel&7)

	flags = 0
	if volume != qcommon.DEFAULT_SOUND_PACKET_VOLUME:
		flags |= qcommon.SND_VOLUME
	if attenuation != qcommon.DEFAULT_SOUND_PACKET_ATTENUATION:
		flags |= qcommon.SND_ATTENUATION

	# the client doesn't know that bmodels have weird origins
	# the origin can also be explicitly set
	if (entity.svflags & game.SVF_NOCLIENT) \
		or entity.solid == game.SOLID_BSP \
		or origin is not None:
		flags |= qcommon.SND_POS

	# always send the entity number for channel overrides
	flags |= qcommon.SND_ENT

	if timeofs:
		flags |= qcommon.SND_OFFSET

	# use the entity origin unless it is a bmodel or explicitly specified
	origin_v = np.zeros((3,), dtype=np.float32)
	if origin is None:
		if entity.solid == game.SOLID_BSP:
			for i in range(3):
				origin_v[i] = entity.s.origin[i]+0.5*(entity.mins[i]+entity.maxs[i])
		else:
			q_shared.VectorCopy (entity.s.origin, origin_v)
		origin = origin_v

	common.MSG_WriteByte (sv_init.sv.multicast, qcommon.svc_ops_e.svc_sound.value)
	common.MSG_WriteByte (sv_init.sv.multicast, flags)
	common.MSG_WriteByte (sv_init.sv.multicast, soundindex)

	if flags & qcommon.SND_VOLUME:
		common.MSG_WriteByte (sv_init.sv.multicast, volume*255)
	if flags & qcommon.SND_ATTENUATION:
		common.MSG_WriteByte (sv_init.sv.multicast, attenuation*64)
	if flags & qcommon.SND_OFFSET:
		common.MSG_WriteByte (sv_init.sv.multicast, timeofs*1000)

	if flags & qcommon.SND_ENT:
		common.MSG_WriteShort (sv_init.sv.multicast, sendchan)

	if flags & qcommon.SND_POS:
		common.MSG_WritePos (sv_init.sv.multicast, origin)

	# if the sound doesn't attenuate, send it to everyone
	# (global radio chatter, voiceovers, etc)
	if attenuation == q_shared.ATTN_NONE:
		use_phs = False

	if channel & q_shared.CHAN_RELIABLE:
		if use_phs:
			SV_Multicast (origin, q_shared.multicast_t.MULTICAST_PHS_R)
		else:
			SV_Multicast (origin, q_shared.multicast_t.MULTICAST_ALL_R)
	else:
		if use_phs:
			SV_Multicast (origin, q_shared.multicast_t.MULTICAST_PHS)
		else:
			SV_Multicast (origin, q_shared.multicast_t.MULTICAST_ALL)

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

	"""
	byte		msg_buf[qcommon.MAX_MSGLEN];
	sizebuf_t	msg;

	SV_BuildClientFrame (client);

	SZ_Init (&msg, msg_buf, sizeof(msg_buf));
	msg.allowoverflow = true;

	// send over all the relevant entity_state_t
	// and the player_state_t
	SV_WriteFrameToClient (client, &msg);

	// copy the accumulated multicast datagram
	// for this client out to the message
	// it is necessary for this to be after the WriteEntities
	// so that entity references will be current
	if (client->datagram.overflowed)
		Com_Printf ("WARNING: datagram overflowed for %s\n", client->name);
	else
		SZ_Write (&msg, client->datagram.data, client->datagram.cursize);
	SZ_Clear (&client->datagram);

	if (msg.overflowed)
	{	// must have room left for the packet header
		Com_Printf ("WARNING: msg overflowed for %s\n", client->name);
		SZ_Clear (&msg);
	}

	// send the datagram
	net_chan.Netchan_Transmit (&client->netchan, msg.cursize, msg.data);

	// record the size for rate estimation
	client->message_size[sv_init.sv.framenum % RATE_MESSAGES] = msg.cursize;

	return true;
}


/*
==================
SV_DemoCompleted
==================
"""
def SV_DemoCompleted ():

	if sv_init.sv.demofile:
	
		sv_init.sv.demofile.close()
		sv_init.sv.demofile = None
	
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
	if sv_init.sv.state == sv_init.server_state_t.ss_demo and sv_init.sv.demofile is not None:
	
		if sv_main.sv_paused.value != 0:
			msglen = 0
		else:
			# get the next message
			data = sv_init.sv.demofile.read(4)
			r = 1 if len(data) == 4 else 0 # r = fread (&msglen, 4, 1, sv.demofile);
			if r != 1:
			
				SV_DemoCompleted ()
				return
			
			msglen = q_shared.LittleSLong (data)
			if msglen == -1:
			
				SV_DemoCompleted ()
				return
			
			if msglen > qcommon.MAX_MSGLEN:
				common.Com_Error (q_shared.ERR_DROP, "SV_SendClientMessages: msglen > MAX_MSGLEN")
			msgbuf = sv_init.sv.demofile.read(msglen)
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
		
			c.netchan.message.data = None
			c.datagram = None
			SV_BroadcastPrintf (q_shared.PRINT_HIGH, "{} overflowed\n".format(c.name))
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
		
	
