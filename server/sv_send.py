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

Message sending and multiplexing.

=======================================================================
"""
from __future__ import annotations

import struct
import numpy as np
from backends.unix import system
pass
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import filesystem
from common import frame
from common import movemsg
from common import szone
from common import collision
from common import netchan
from server.header import server as server_h
from server import sv_entities
from server import sv_init
from server import sv_main
from server import sv_user
from game.header import game as game_h

"""
#include "header/server.h"
"""

# entnum and channel are sent in the same signed 16-bit value
# 3 bits for channel, 13 for entnum, so limit is 4096
SND_MAX_ENTNUM = 4095

sv_outputbuf = "" #char [SV_OUTPUTBUF_LENGTH]

def SV_FlushRedirect(sv_redirected: int, outputbuf: str): #int, char *

	if sv_redirected == server_h.redirect_t.RD_PACKET.value:

		netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, netchan.net_from, "print\n%s", outputbuf)

	elif sv_redirected == server_h.redirect_t.RD_CLIENT.value:

		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_print.value)
		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, shared.PRINT_HIGH)
		movemsg.MSG_WriteString(sv_main.sv_client.netchan.message, outputbuf)

"""
 * Sends text across to be displayed if the level passes
"""
def SV_ClientPrintf(cl: server_h.client_t, level: int, fmt: str, *args): #client_t *, int, const char *, ...

	"""
	va_list argptr;
	char string[1024];
	"""

	string = ((fmt % args) if args else fmt)[:1023] #vsnprintf(string, sizeof(string), fmt, argptr);

	movemsg.MSG_WriteByte(cl.netchan.message, common_h.svc_ops_e.svc_print.value)
	movemsg.MSG_WriteByte(cl.netchan.message, level)
	movemsg.MSG_WriteString(cl.netchan.message, string)

"""
 * Sends text to all active clients
"""
def SV_BroadcastPrintf(level: int, fmt: str, *args): #int, const char *, ...

	"""
	va_list argptr;
	char string[2048];
	client_t *cl;
	int i;
	"""

	string = ((fmt % args) if args else fmt)[:2047] #vsnprintf(string, sizeof(string), fmt, argptr);

	# echo to console
	if frame.dedicated.value:

		#char copy[1024];

		# mask off high bits
		copy = "".join(chr(ord(c) & 127) for c in string[:1023])
		clientserver.Com_Printf("%s", copy)


	for i in range(int(sv_main.maxclients.value)):

		cl = sv_init.svs.clients[i]

		if cl.state != server_h.client_state_t.cs_spawned:

			continue


		movemsg.MSG_WriteByte(cl.netchan.message, common_h.svc_ops_e.svc_print.value)
		movemsg.MSG_WriteByte(cl.netchan.message, level)
		movemsg.MSG_WriteString(cl.netchan.message, string)

"""
 * Sends text to all active clients
"""
def SV_BroadcastCommand(fmt: str, *args): #const char *, ...

	"""
	va_list argptr;
	char string[1024];
	"""

	if not sv_init.sv.state.value:

		return


	string = ((fmt % args) if args else fmt)[:1023] #vsnprintf(string, sizeof(string), fmt, argptr);

	movemsg.MSG_WriteByte(sv_init.sv.multicast, common_h.svc_ops_e.svc_stufftext.value)
	movemsg.MSG_WriteString(sv_init.sv.multicast, string)
	SV_Multicast(None, shared.multicast_t.MULTICAST_ALL_R)

"""
 * Sends the contents of sv.multicast to a subset of the clients,
 * then clears sv.multicast.
 *
 * MULTICAST_ALL	same as broadcast (origin can be NULL)
 * MULTICAST_PVS	send to clients potentially visible from org
 * MULTICAST_PHS	send to clients potentially hearable from org
"""
def SV_WereConnected(cluster: int, area2: int, origin, mask, area1: int)->bool: #int, int, vec3_t, const byte *, int (returns static qboolean)

	# cluster can be -1 if we're in the void (or sometimes just at a wall)
	# and using a negative index into mask[] would be invalid
	if cluster >= 0 and (mask[cluster >> 3] & (1 << (cluster & 7))):

		if collision.CM_AreasConnected(area1, area2):

			return True



	# if the client is currently in water, do a second check
	if collision.CM_PointContents(origin, 0) & shared.MASK_WATER:

		"""
		vec3_t origin2;
		int leafnum2, cluster2;
		"""

		# if the client is half-submerged in opaque water so its origin
		# is below the water, but the head/camera is still above the water
		# and thus should be able to see/hear explosions or similar
		# that are above the water.
		# so try again at a slightly higher position
		# FIXME: OTOH, we have a similar problem if we're over water and shoot under water (near water level) => can't see explosion

		origin2 = np.array(origin, dtype=np.float32) #VectorCopy(origin, origin2);
		origin2[2] += np.float32(32.0)

		leafnum2 = collision.CM_PointLeafnum(origin2)
		cluster2 = collision.CM_LeafCluster(leafnum2)

		if cluster2 >= 0 and (mask[cluster2 >> 3] & (1 << (cluster2 & 7))):

			if collision.CM_AreasConnected(area1, collision.CM_LeafArea(leafnum2)):

				return True




	return False

def SV_GetClientLeafCache(client: server_h.client_t): #client_t *, int *, int *
	# Q2PORT: returns area, cluster

	e = server_h.CL_EDICT(client)

	if client.cached_framenum != sv_init.sv.framenum or \
	    not shared_c.VectorCompare(client.cached_origin, e.s.origin):

		client.cached_origin = [e.s.origin[0], e.s.origin[1], e.s.origin[2]] #VectorCopy(e->s.origin, client->cached_origin);
		client.cached_leafnum = collision.CM_PointLeafnum(e.s.origin)
		client.cached_area = collision.CM_LeafArea(client.cached_leafnum)
		client.cached_cluster = collision.CM_LeafCluster(client.cached_leafnum)
		client.cached_framenum = sv_init.sv.framenum


	return client.cached_area, client.cached_cluster

def SV_Multicast(origin, to): #const vec3_t, multicast_t

	"""
	int leafnum, cluster, area1 = 0, j;
	qboolean reliable;
	client_t *client;
	byte *mask;
	"""
	area1 = 0

	if not isinstance(to, shared.multicast_t):	# Q2PORT: the game passes the enum's integer
		to = shared.multicast_t(to)

	reliable = False

	if (to != shared.multicast_t.MULTICAST_ALL_R) and (to != shared.multicast_t.MULTICAST_ALL):

		leafnum = collision.CM_PointLeafnum(origin)
		area1 = collision.CM_LeafArea(leafnum)


	# if doing a serverrecord, store everything
	if sv_init.svs.demofile:

		szone.SZ_Write(sv_init.svs.demo_multicast, bytes(sv_init.sv.multicast.data[:sv_init.sv.multicast.cursize]))


	if to == shared.multicast_t.MULTICAST_ALL_R or to == shared.multicast_t.MULTICAST_ALL:

		reliable = (to == shared.multicast_t.MULTICAST_ALL_R) # intentional fallthrough
		mask = None

	elif to == shared.multicast_t.MULTICAST_PHS_R or to == shared.multicast_t.MULTICAST_PHS:

		reliable = (to == shared.multicast_t.MULTICAST_PHS_R) # intentional fallthrough
		leafnum = collision.CM_PointLeafnum(origin)
		cluster = collision.CM_LeafCluster(leafnum)
		mask = collision.CM_ClusterPHS(cluster)

	elif to == shared.multicast_t.MULTICAST_PVS_R or to == shared.multicast_t.MULTICAST_PVS:

		reliable = (to == shared.multicast_t.MULTICAST_PVS_R) # intentional fallthrough
		leafnum = collision.CM_PointLeafnum(origin)
		cluster = collision.CM_LeafCluster(leafnum)
		mask = collision.CM_ClusterPVS(cluster)

	else:

		mask = None
		clientserver.Com_Error(shared.ERR_FATAL, "%s: bad to:%i", "SV_Multicast", to.value)


	# send the data to all relevent clients
	for j in range(int(sv_main.maxclients.value)):

		client = sv_init.svs.clients[j]

		if (client.state == server_h.client_state_t.cs_free) or (client.state == server_h.client_state_t.cs_zombie):

			continue


		if (client.state != server_h.client_state_t.cs_spawned) and not reliable:

			continue


		if mask is not None:

			#int area2, cluster2;
			area2, cluster2 = SV_GetClientLeafCache(client)

			if not SV_WereConnected(cluster2, area2, server_h.CL_EDICT(client).s.origin, mask, area1):

				continue



		szone.SZ_Write(client.netchan.message if reliable else client.datagram,
				bytes(sv_init.sv.multicast.data[:sv_init.sv.multicast.cursize]))


	szone.SZ_Clear(sv_init.sv.multicast)

"""
 * Each entity can have eight independant sound sources, like voice,
 * weapon, feet, etc.
 *
 * If cahnnel & 8, the sound will be sent to everyone, not just
 * things in the PHS.
 *
 * Channel 0 is an auto-allocate channel, the others override anything
 * already running on that entity/channel pair.
 *
 * An attenuation of 0 will play full volume everywhere in the level.
 * Larger attenuations will drop off.  (max 4 attenuation)
 *
 * Timeofs can range from 0.0 to 0.1 to cause sounds to be started
 * later in the frame than they normally would.
 *
 * If origin is NULL, the origin is determined from the entity origin
 * or the midpoint of the entity box for bmodels.
"""
def SV_StartSound(origin, entity, channel: int, soundindex: int,
		volume: float, attenuation: float, timeofs: float): #const vec3_t, const edict_t *, int, int, float, float, float

	"""
	int flags;
	int ent;
	vec3_t origin_v;
	qboolean use_phs;
	multicast_t to;
	"""

	if (volume < 0.0) or (volume > 1.0):

		clientserver.Com_DPrintf("%s: volume out of bounds [0-1]: %f\n", "SV_StartSound", volume)
		volume = 1.0


	if (attenuation < 0.0) or (attenuation > 4.0):

		clientserver.Com_DPrintf("%s: attenuation out of bounds [0-4]: %f\n", "SV_StartSound", attenuation)
		attenuation = 0.0


	if (timeofs < 0.0) or (timeofs > 0.255):

		clientserver.Com_DPrintf("%s: timeofs out of bounds [0-0.255]: %f\n", "SV_StartSound", timeofs)
		timeofs = 0.0


	ent = server_h.NUM_FOR_EDICT(entity)

	if ent > SND_MAX_ENTNUM:

		return


	flags = 0

	if volume != common_h.DEFAULT_SOUND_PACKET_VOLUME:

		flags |= common_h.SND_VOLUME


	if attenuation != common_h.DEFAULT_SOUND_PACKET_ATTENUATION:

		flags |= common_h.SND_ATTENUATION


	# the client doesn't know that bmodels have
	# weird origins the origin can also be
	# explicitly set
	if (entity.svflags & game_h.SVF_NOCLIENT) or \
		(entity.solid == game_h.SOLID_BSP) or \
		origin is not None:

		flags |= common_h.SND_POS


	# always send the entity number for channel overrides
	flags |= common_h.SND_ENT

	if timeofs:

		flags |= common_h.SND_OFFSET


	# use the entity origin unless it is a bmodel or explicitly specified
	if origin is None:

		origin_v = np.zeros((3,), dtype=np.float32)
		origin = origin_v

		if entity.solid == game_h.SOLID_BSP:

			for i in range(3):

				origin_v[i] = entity.s.origin[i] + np.float32(0.5) * \
							  (entity.mins[i] + entity.maxs[i])


		else:

			shared.VectorCopy(entity.s.origin, origin_v)



	movemsg.MSG_WriteByte(sv_init.sv.multicast, common_h.svc_ops_e.svc_sound.value)
	movemsg.MSG_WriteByte(sv_init.sv.multicast, flags)
	movemsg.MSG_WriteByte(sv_init.sv.multicast, soundindex)

	if flags & common_h.SND_VOLUME:

		movemsg.MSG_WriteByte(sv_init.sv.multicast, int(volume * 255))


	if flags & common_h.SND_ATTENUATION:

		movemsg.MSG_WriteByte(sv_init.sv.multicast, int(attenuation * 64))


	if flags & common_h.SND_OFFSET:

		movemsg.MSG_WriteByte(sv_init.sv.multicast, int(timeofs * 1000))


	if flags & common_h.SND_ENT:

		sendchan = (ent << 3) | (channel & 7)
		movemsg.MSG_WriteShort(sv_init.sv.multicast, sendchan)


	if flags & common_h.SND_POS:

		movemsg.MSG_WritePos(sv_init.sv.multicast, origin)


	use_phs = False if (channel & shared.CHAN_NO_PHS_ADD) else True

	# if the sound doesn't attenuate,send it to everyone
	# (global radio chatter, voiceovers, etc)
	if attenuation == shared.ATTN_NONE:

		use_phs = False


	if channel & shared.CHAN_RELIABLE:

		to = shared.multicast_t.MULTICAST_PHS_R if use_phs else shared.multicast_t.MULTICAST_ALL_R

	else:

		to = shared.multicast_t.MULTICAST_PHS if use_phs else shared.multicast_t.MULTICAST_ALL


	SV_Multicast(origin, to)

def SV_SendClientDatagram(client: server_h.client_t)->bool: #client_t * (returns static qboolean)

	"""
	byte msg_buf[MAX_MSGLEN];
	sizebuf_t msg;
	"""
	msg = common_h.sizebuf_t()

	sv_entities.SV_BuildClientFrame(client)

	szone.SZ_Init(msg, common_h.MAX_MSGLEN)
	msg.allowoverflow = True

	# send over all the relevant entity_state_t
	# and the player_state_t
	sv_entities.SV_WriteFrameToClient(client, msg)

	# copy the accumulated multicast datagram
	# for this client out to the message
	# it is necessary for this to be after the WriteEntities
	# so that entity references will be current
	if client.datagram.overflowed:

		clientserver.Com_DPrintf("WARNING: datagram overflowed for %s\n", client.name)

	else:

		szone.SZ_Write(msg, bytes(client.datagram.data[:client.datagram.cursize]))


	szone.SZ_Clear(client.datagram)

	if msg.overflowed:

		# must have room left for the packet header
		clientserver.Com_DPrintf("WARNING: msg overflowed for %s\n", client.name)
		szone.SZ_Clear(msg)


	# send the datagram
	netchan.Netchan_Transmit(client.netchan, bytes(msg.data[:msg.cursize]))

	# record the size for rate estimation
	client.message_size[sv_init.sv.framenum % server_h.RATE_MESSAGES] = msg.cursize

	return True

def SV_DemoCompleted(): #void

	if sv_init.sv.demofile:

		filesystem.FS_FCloseFile(sv_init.sv.demofile)
		sv_init.sv.demofile = 0


	sv_user.SV_Nextserver()

"""
 * Returns true if the client is over its current
 * bandwidth estimation and should not be sent another packet
"""
def SV_RateDrop(c: server_h.client_t)->bool: #client_t * (returns static qboolean)

	"""
	int total;
	int i;
	"""

	# never drop over the loopback
	if c.netchan.remote_address.type == common_h.netadrtype_t.NA_LOOPBACK:

		return False


	total = 0

	for i in range(server_h.RATE_MESSAGES):

		total += c.message_size[i]


	if total > c.rate:

		c.surpressCount += 1
		c.message_size[sv_init.sv.framenum % server_h.RATE_MESSAGES] = 0
		return True


	return False

def SV_NextDemoChunk(): #byte * (returns static int)
	# Q2PORT: returns the length and the message: n, msgbuf = SV_NextDemoChunk()

	"""
	size_t r;
	int n;
	"""

	if sv_main.sv_paused.value:

		return 0, b""


	data = filesystem.FS_FRead(4, 1, sv_init.sv.demofile)
	r = len(data)

	if r != 4:

		return -1, b""


	n = struct.unpack("<i", data)[0] #n = LittleLong(n);

	if n == -1:

		return -1, b""


	if n > common_h.MAX_MSGLEN:

		clientserver.Com_Error(shared.ERR_DROP,
				"SV_SendClientMessages: msglen > MAX_MSGLEN")


	msgbuf = filesystem.FS_FRead(n, 1, sv_init.sv.demofile)
	r = len(msgbuf)

	return (n, msgbuf) if (r == n) else (-1, b"")

# if the reliable message
# overflowed, drop the
# client
def SV_SendDisconnect(c: server_h.client_t): #client_t *

	szone.SZ_Clear(c.netchan.message)
	szone.SZ_Clear(c.datagram)

	SV_BroadcastPrintf(shared.PRINT_HIGH, "%s overflowed\n", c.name)
	sv_main.SV_DropClient(c)

	netchan.Netchan_Transmit(c.netchan, b"")

def SV_SendClientMessages(): #void

	"""
	int i;
	client_t *c;
	int msglen;
	byte msgbuf[MAX_MSGLEN];
	"""

	# read the next demo message if needed
	if sv_init.sv.demofile and (sv_init.sv.state == server_h.server_state_t.ss_demo):

		msglen, msgbuf = SV_NextDemoChunk()

		if msglen < 0:

			SV_DemoCompleted()
			return


	else:

		msglen = 0
		msgbuf = b""


	# send a message to each spawned client
	for i in range(int(sv_main.maxclients.value)):

		c = sv_init.svs.clients[i]

		if c.state == server_h.client_state_t.cs_free:

			continue


		if c.netchan.message.overflowed:

			SV_SendDisconnect(c)
			continue


		if (sv_init.sv.state == server_h.server_state_t.ss_cinematic) or \
			(sv_init.sv.state == server_h.server_state_t.ss_demo) or \
			(sv_init.sv.state == server_h.server_state_t.ss_pic):

			netchan.Netchan_Transmit(c.netchan, msgbuf[:msglen])

		elif c.state == server_h.client_state_t.cs_spawned:

			# don't overrun bandwidth
			if SV_RateDrop(c):

				continue


			SV_SendClientDatagram(c)


		# messages to non-spawned clients are sent by SendPrepClientMessages

def SV_SendPrepClientMessages(): #void

	"""
	client_t *c;
	int i;
	"""

	if (sv_init.sv.state == server_h.server_state_t.ss_cinematic) or \
		(sv_init.sv.state == server_h.server_state_t.ss_demo) or \
		(sv_init.sv.state == server_h.server_state_t.ss_pic):

		return


	# send a message to each inactive client if needed
	for i in range(int(sv_main.maxclients.value)):

		c = sv_init.svs.clients[i]

		if (c.state == server_h.client_state_t.cs_free) or (c.state == server_h.client_state_t.cs_spawned):

			continue


		if c.netchan.message.overflowed:

			SV_SendDisconnect(c)
			continue


		# just update reliable	if needed
		if c.netchan.message.cursize or \
			(frame.curtime - c.netchan.last_sent > 1000):

			netchan.Netchan_Transmit(c.netchan, b"")
