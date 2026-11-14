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

Server main function and correspondig stuff

=======================================================================
"""
from __future__ import annotations

import struct
import traceback
from backends.unix import network, system
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import errors
from common import clientserver
from common import cvar
from common import filesystem
from common import frame
from common import movemsg
from common import szone
from common import netchan
from common.shared import rand
from server.header import server as server_h
from server import sv_cmd
from server import sv_conless
from server import sv_game
from server import sv_init
from server import sv_send
from server import sv_user
from server import sv_entities

"""
#include "header/server.h"
"""

HEARTBEAT_SECONDS = 300

master_adr = [common_h.netadr_t() for i in range(server_h.MAX_MASTERS)] #netadr_t [MAX_MASTERS], address of group servers


sv_optimize_sp_loadtime = None #static cvar_t *
sv_optimize_mp_loadtime = None #static cvar_t *

sv_paused = None #cvar_t *
sv_timedemo = None #cvar_t *
sv_enforcetime = None #cvar_t *
timeout = None #cvar_t *, seconds without any message
zombietime = None #cvar_t *, seconds to sink messages after disconnect
rcon_password = None #cvar_t *, password for remote server commands
allow_download = None #cvar_t *
allow_download_players = None #cvar_t *
allow_download_models = None #cvar_t *
allow_download_sounds = None #cvar_t *
allow_download_maps = None #cvar_t *
sv_airaccelerate = None #cvar_t *
sv_noreload = None #cvar_t *, don't reload level state when reentering
maxclients = None #cvar_t *, rename sv_maxclients
sv_showclamp = None #cvar_t *
hostname = None #cvar_t *
public_server = None #cvar_t *, should heartbeats be sent
sv_entfile = None #cvar_t *, External entity files.
sv_downloadserver = None #cvar_t *, Download server.

#void SV_ConnectionlessPacket(void);

"""
 * Called when the player is totally leaving the server, either willingly
 * or unwillingly.  This is NOT called if the entire server is quiting
 * or crashing.
"""
def SV_DropClient(drop: server_h.client_t): #client_t *

	# add the disconnect
	movemsg.MSG_WriteByte(drop.netchan.message, common_h.svc_ops_e.svc_disconnect.value)

	if drop.state == server_h.client_state_t.cs_spawned:

		# call the prog function for removing a client
		# this will remove the body, among other things
		sv_game.ge.ClientDisconnect(server_h.CL_EDICT(drop))


	if drop.download:

		filesystem.FS_FreeFile(drop.download)
		drop.download = None


	drop.state = server_h.client_state_t.cs_zombie # become free in a few seconds
	drop.name = ""

"""
 * Builds the string that is sent as heartbeats and status replies
"""
def SV_StatusString()->str: #(returns char *)

	"""
	char player[1024];
	static char status[MAX_MSGLEN - 16];
	int i;
	client_t *cl;
	int statusLength;
	int playerLength;
	"""

	status = (cvar.Cvar_Serverinfo() + "\n")[:common_h.MAX_MSGLEN - 16 - 1]
	statusLength = len(status)

	for i in range(int(maxclients.value)):

		cl = sv_init.svs.clients[i]

		if (cl.state == server_h.client_state_t.cs_connected) or (cl.state == server_h.client_state_t.cs_spawned):

			player = "%i %i \"%s\"\n" % (
					server_h.CL_EDICT(cl).client.ps.stats[shared.STAT_FRAGS], cl.ping, cl.name)
			playerLength = len(player)

			if statusLength + playerLength >= common_h.MAX_MSGLEN - 16:

				break # can't hold any more


			status += player
			statusLength += playerLength



	return status

def SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge):
	# Q2PORT: the code after the gotnewcl label of SVC_DirectConnect (sv_conless.c)

	# build a new connection
	# accept the new client
	# this is the only place a client_t is ever initialized
	#*newcl = temp;
	sv_init.server.client = newcl
	ent = server_h.CL_EDICT(newcl)
	newcl.challenge = challenge # save challenge for checksumming

	# get the game a chance to reject this connection or modify the userinfo
	if not sv_game.ge.ClientConnect(ent, userinfo):

		if shared_c.Info_ValueForKey(userinfo, "rejmsg"):

			netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr,
					"print\n%s\nConnection refused.\n",
					shared_c.Info_ValueForKey(userinfo, "rejmsg"))

		else:

			netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr,
					"print\nConnection refused.\n")


		clientserver.Com_DPrintf("Game rejected a connection.\n")
		return


	# parse some info from the info strings
	newcl.userinfo = userinfo[:shared.MAX_INFO_STRING - 1]
	SV_UserinfoChanged(newcl)

	# send the connect packet to the client
	if sv_downloadserver.string:

		netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr, "client_connect dlserver=%s", sv_downloadserver.string)

	else:

		netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, adr, "client_connect")


	netchan.Netchan_Setup(common_h.netsrc_t.NS_SERVER, newcl.netchan, adr, qport)

	newcl.state = server_h.client_state_t.cs_connected

	szone.SZ_Init(newcl.datagram, common_h.MAX_MSGLEN) #SZ_Init(&newcl->datagram, newcl->datagram_buf, sizeof(newcl->datagram_buf));
	newcl.datagram.allowoverflow = True
	newcl.lastmessage = sv_init.svs.realtime  # don't timeout
	newcl.lastconnect = sv_init.svs.realtime

"""
 * Updates the cl->ping variables
"""
def SV_CalcPings(): #void

	"""
	int i, j;
	client_t *cl;
	int total, count;
	"""

	for i in range(int(maxclients.value)):

		cl = sv_init.svs.clients[i]

		if cl.state != server_h.client_state_t.cs_spawned:

			continue


		total = 0
		count = 0

		for j in range(server_h.LATENCY_COUNTS):

			if cl.frame_latency[j] > 0:

				count += 1
				total += cl.frame_latency[j]



		cl.ping = 0 if (not count) else (total // count)

		# let the game dll know about the ping
		server_h.CL_EDICT(cl).client.ping = cl.ping

"""
 * Every few frames, gives all clients an allotment of milliseconds
 * for their command moves. If they exceed it, assume cheating.
"""
def SV_GiveMsec(): #void

	"""
	int i;
	client_t *cl;
	"""

	if sv_init.sv.framenum & 15:

		return


	for i in range(int(maxclients.value)):

		cl = sv_init.svs.clients[i]

		if cl.state == server_h.client_state_t.cs_free:

			continue


		cl.commandMsec = 1800 # 1600 + some slop

def SV_ReadPackets(): #void

	"""
	int i;
	client_t *cl;
	int qport;
	"""

	while True:

		rx, netchan.net_from = network.NET_GetPacket(common_h.netsrc_t.NS_SERVER, netchan.net_from, netchan.net_message)
		if not rx:
			break

		# check for connectionless packet (0xffffffff) first
		# Q2PORT: and the packet has those 4 bytes; net_message.data is only as
		# long as the packet (the C reads its fixed size buffer)
		if netchan.net_message.cursize >= 4 and \
			struct.unpack_from("<i", netchan.net_message.data, 0)[0] == -1: #*(int *)net_message.data == -1

			try: # Q2PORT: see SV_UntrustedDataError()

				sv_conless.SV_ConnectionlessPacket()

			except errors.DropError:

				raise

			except Exception as err:

				SV_UntrustedDataError(err, "connectionless packet")

			continue


		# read the qport out of the message so we can fix up
		# stupid address translating routers
		movemsg.MSG_BeginReading(netchan.net_message)
		movemsg.MSG_ReadLong(netchan.net_message) # sequence number
		movemsg.MSG_ReadLong(netchan.net_message) # sequence number
		qport = movemsg.MSG_ReadShort(netchan.net_message) & 0xffff

		# check for packets from connected clients
		i = 0
		while i < maxclients.value:

			cl = sv_init.svs.clients[i]

			if cl.state == server_h.client_state_t.cs_free:

				i += 1
				continue


			if not network.NET_CompareBaseAdr(netchan.net_from, cl.netchan.remote_address):

				i += 1
				continue


			if cl.netchan.qport != qport:

				i += 1
				continue


			if cl.netchan.remote_address.port != netchan.net_from.port:

				clientserver.Com_Printf("%s: fixing up a translated port\n", "SV_ReadPackets")
				cl.netchan.remote_address.port = netchan.net_from.port


			if netchan.Netchan_Process(cl.netchan, netchan.net_message):

				# this is a valid, sequenced packet, so process it
				if cl.state != server_h.client_state_t.cs_zombie:

					cl.lastmessage = sv_init.svs.realtime # don't timeout

					if not (sv_init.sv.demofile and (sv_init.sv.state == server_h.server_state_t.ss_demo)):

						try: # Q2PORT: see SV_UntrustedDataError()

							sv_user.SV_ExecuteClientMessage(cl)

						except errors.DropError:

							raise

						except Exception as err:

							SV_UntrustedDataError(err, "message from {}".format(cl.name))
							SV_DropClient(cl)




			break


		if i != maxclients.value:

			continue

def SV_UntrustedDataError(err: Exception, what: str): # Q2PORT: Exception, char *

	# Q2PORT: not in the C. A packet from the network is untrusted data, and a
	# python exception while handling it (a bug the bad data reached, where the
	# C would read garbage or drop the client) would otherwise end the whole
	# server. SV_ReadPackets() catches it instead: a connectionless packet is
	# ignored and a client's message drops that client. The exception is
	# reported here, with the traceback for developer 1.
	clientserver.Com_Printf("{}: {} in {} from {}, ignored\n".format("SV_ReadPackets",
		type(err).__name__, what, network.NET_AdrToString(netchan.net_from)))
	clientserver.Com_DPrintf("{}".format("".join(traceback.format_exception(err))))

"""
 * If a packet has not been received from a client for timeout->value
 * seconds, drop the conneciton.  Server frames are used instead of
 * realtime to avoid dropping the local client while debugging.
 *
 * When a client is normally dropped, the client_t goes into a zombie state
 * for a few seconds to make sure any final reliable message gets resent
 * if necessary
"""
def SV_CheckTimeouts(): #void

	"""
	int i;
	client_t *cl;
	int droppoint;
	int zombiepoint;
	"""

	droppoint = int(sv_init.svs.realtime - 1000 * timeout.value)
	zombiepoint = int(sv_init.svs.realtime - 1000 * zombietime.value)

	for i in range(int(maxclients.value)):

		cl = sv_init.svs.clients[i]

		# message times may be wrong across a changelevel
		if cl.lastmessage > sv_init.svs.realtime:

			cl.lastmessage = sv_init.svs.realtime


		if (cl.state == server_h.client_state_t.cs_zombie) and \
			(cl.lastmessage < zombiepoint):

			cl.state = server_h.client_state_t.cs_free # can now be reused
			continue


		if ((cl.state == server_h.client_state_t.cs_connected) or (cl.state == server_h.client_state_t.cs_spawned)) and \
			(cl.lastmessage < droppoint):

			sv_send.broadcast_printf(shared.PRINT_HIGH, "%s timed out\n", cl.name)
			SV_DropClient(cl)
			cl.state = server_h.client_state_t.cs_free # don't bother with zombie state

"""
 * This has to be done before the world logic, because
 * player processing happens outside RunWorldFrame
"""
def SV_PrepWorldFrame(): #void

	"""
	edict_t *ent;
	int i;
	"""

	for i in range(sv_game.ge.num_edicts):

		ent = server_h.EDICT_NUM(i)

		# events only last for a single message
		ent.s.event = 0

def SV_RunGameFrame(): #void

	#ifndef DEDICATED_ONLY
	if frame.host_speeds.value:

		frame.time_before_game = system.Sys_Milliseconds()

	#endif

	# we always need to bump framenum, even if we
	# don't run the world, otherwise the delta
	# compression can get confused when a client
	# has the "current" frame
	sv_init.sv.framenum += 1
	sv_init.sv.time = sv_init.sv.framenum * 100

	# don't run if paused
	if not sv_paused.value or (maxclients.value > 1):

		sv_game.ge.RunFrame()

		# never get more than one tic behind
		if sv_init.sv.time < sv_init.svs.realtime:

			if sv_showclamp.value:

				clientserver.Com_Printf("sv highclamp\n")


			sv_init.svs.realtime = sv_init.sv.time



	#ifndef DEDICATED_ONLY
	if frame.host_speeds.value:

		frame.time_after_game = system.Sys_Milliseconds()

	#endif

def SV_Optimizations()->int: #(returns int)

	"""
	cvar_t *cv;
	"""

	if sv_init.svs.gamemode <= 0 or sv_init.svs.gamemode > 3:

		return 0


	cv = sv_optimize_sp_loadtime if (sv_init.svs.gamemode == server_h.GAMEMODE_SP) else \
		sv_optimize_mp_loadtime

	return (int(cv.value) & server_h.OPTIMIZE_MASK_ALL) if cv is not None else 0

def SV_Frame(usec: int): #int

	"""
	int opt_sendrate;
	"""

	#ifndef DEDICATED_ONLY
	frame.time_before_game = frame.time_after_game = 0
	#endif

	# if server is not active, do nothing
	if not sv_init.svs.initialized:

		return


	sv_init.svs.realtime += usec // 1000

	# keep the random time dependent
	rand.randk()

	# check timeouts
	SV_CheckTimeouts()

	# get packets from clients
	SV_ReadPackets()

	# send messages more often to new clients getting ready for spawning in
	# speeds up the process of sending configstrings, entty deltas, etc.
	opt_sendrate = SV_Optimizations() & server_h.OPTIMIZE_SENDRATE

	if opt_sendrate:

		sv_send.send_prep_client_messages()


	# move autonomous things around if enough time has passed
	if not sv_timedemo.value and (sv_init.svs.realtime < sv_init.sv.time):

		# never let the time get too far off
		if sv_init.sv.time - sv_init.svs.realtime > 100:

			if sv_showclamp.value:

				clientserver.Com_Printf("sv lowclamp\n")


			sv_init.svs.realtime = sv_init.sv.time - 100


		network.NET_Sleep(sv_init.sv.time - sv_init.svs.realtime)
		return


	# update ping based on the last known frame from all clients
	SV_CalcPings()

	# give the clients some timeslices
	SV_GiveMsec()

	# let everything in the world think and move
	SV_RunGameFrame()

	# send messages back to the clients that had packets read this frame
	sv_send.send_client_messages()

	# if not optimizing, send all messages here
	if not opt_sendrate:

		sv_send.send_prep_client_messages()


	# save the entire world state if recording a serverdemo
	sv_entities.record_demo_message()

	# send a heartbeat to the master if needed
	Master_Heartbeat()

	# clear teleport flags, etc for next frame
	SV_PrepWorldFrame()

"""
 * Send a message to the master every few minutes to
 * let it know we are alive, and log information
"""
def Master_Heartbeat(): #void

	"""
	char *string;
	int i;
	"""

	if frame.dedicated is None or not frame.dedicated.value:

		return # only dedicated servers send heartbeats


	if public_server is None or not public_server.value:

		return # a private dedicated game


	# check for time wraparound
	if sv_init.svs.last_heartbeat > sv_init.svs.realtime:

		sv_init.svs.last_heartbeat = sv_init.svs.realtime


	if sv_init.svs.realtime - sv_init.svs.last_heartbeat < HEARTBEAT_SECONDS * 1000:

		return # not time to send yet


	sv_init.svs.last_heartbeat = sv_init.svs.realtime

	# send the same string that we would give for a status OOB command
	string = SV_StatusString()

	# send to group master
	for i in range(server_h.MAX_MASTERS):

		if master_adr[i].port:

			clientserver.Com_Printf("Sending heartbeat to %s\n",
					network.NET_AdrToString(master_adr[i]))
			netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, master_adr[i],
					"heartbeat\n%s", string)

"""
 * Informs all masters that this server is going down
"""
def Master_Shutdown(): #void

	"""
	int i;
	"""

	if frame.dedicated is None or not frame.dedicated.value:

		return # only dedicated servers send heartbeats


	if public_server is None or not public_server.value:

		return # a private dedicated game


	# send to group master
	for i in range(server_h.MAX_MASTERS):

		if master_adr[i].port:

			if i > 0:

				clientserver.Com_Printf("Sending heartbeat to %s\n",
						network.NET_AdrToString(master_adr[i]))


			netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, master_adr[i], "shutdown")

"""
 * Pull specific info from a newly changed userinfo string
 * into a more C freindly form.
"""
def SV_UserinfoChanged(cl: server_h.client_t): #client_t *

	"""
	char *val;
	int i;
	"""

	# call prog code to allow overrides
	sv_game.ge.ClientUserinfoChanged(server_h.CL_EDICT(cl), cl.userinfo)

	# name for C code
	cl.name = shared_c.Info_ValueForKey(cl.userinfo, "name")[:32 - 1] #Q_strlcpy(cl->name, ..., sizeof(cl->name));

	# mask off high bit
	cl.name = "".join(chr(ord(c) & 127) for c in cl.name) #for (i = 0; i < sizeof(cl->name); i++) cl->name[i] &= 127;

	# rate command
	val = shared_c.Info_ValueForKey(cl.userinfo, "rate")

	if len(val):

		i = shared_c.atoi(val) #(int)strtol(val, (char **)NULL, 10);
		cl.rate = i

		if cl.rate < 100:

			cl.rate = 100


		if cl.rate > 15000:

			cl.rate = 15000


	else:

		cl.rate = 5000

"""
 * Only called at quake2.exe startup, not for each game
"""
def SV_Init(): #void

	global sv_optimize_sp_loadtime, sv_optimize_mp_loadtime
	global rcon_password, maxclients, hostname, timeout, zombietime
	global sv_showclamp, sv_paused, sv_timedemo, sv_enforcetime
	global allow_download, allow_download_players, allow_download_models, allow_download_sounds, allow_download_maps
	global sv_downloadserver, sv_noreload, sv_airaccelerate, public_server, sv_entfile

	sv_cmd.SV_InitOperatorCommands()

	sv_optimize_sp_loadtime = cvar.Cvar_Get("sv_optimize_sp_loadtime", "31", 0)
	sv_optimize_mp_loadtime = cvar.Cvar_Get("sv_optimize_mp_loadtime", "7", 0)

	rcon_password = cvar.Cvar_Get("rcon_password", "", 0)
	cvar.Cvar_Get("skill", "1", 0)
	cvar.Cvar_Get("singleplayer", "0", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	cvar.Cvar_Get("deathmatch", "0", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	cvar.Cvar_Get("coop", "0", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	cvar.Cvar_Get("dmflags", "%i" % shared.DF_INSTANT_ITEMS, shared.CVAR_SERVERINFO)
	cvar.Cvar_Get("fraglimit", "0", shared.CVAR_SERVERINFO)
	cvar.Cvar_Get("timelimit", "0", shared.CVAR_SERVERINFO)
	cvar.Cvar_Get("cheats", "0", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	cvar.Cvar_Get("protocol", "%i" % common_h.PROTOCOL_VERSION, shared.CVAR_SERVERINFO | shared.CVAR_NOSET)
	maxclients = cvar.Cvar_Get("maxclients", "1", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	hostname = cvar.Cvar_Get("hostname", "noname", shared.CVAR_SERVERINFO | shared.CVAR_ARCHIVE)
	timeout = cvar.Cvar_Get("timeout", "125", 0)
	zombietime = cvar.Cvar_Get("zombietime", "2", 0)
	sv_showclamp = cvar.Cvar_Get("showclamp", "0", 0)
	sv_paused = cvar.Cvar_Get("paused", "0", 0)
	sv_timedemo = cvar.Cvar_Get("timedemo", "0", 0)
	sv_enforcetime = cvar.Cvar_Get("sv_enforcetime", "0", 0)
	allow_download = cvar.Cvar_Get("allow_download", "1", shared.CVAR_ARCHIVE)
	allow_download_players = cvar.Cvar_Get("allow_download_players", "0", shared.CVAR_ARCHIVE)
	allow_download_models = cvar.Cvar_Get("allow_download_models", "1", shared.CVAR_ARCHIVE)
	allow_download_sounds = cvar.Cvar_Get("allow_download_sounds", "1", shared.CVAR_ARCHIVE)
	allow_download_maps = cvar.Cvar_Get("allow_download_maps", "1", shared.CVAR_ARCHIVE)
	sv_downloadserver = cvar.Cvar_Get("sv_downloadserver", "", 0)

	sv_noreload = cvar.Cvar_Get("sv_noreload", "0", 0)

	sv_airaccelerate = cvar.Cvar_Get("sv_airaccelerate", "0", shared.CVAR_LATCH)

	public_server = cvar.Cvar_Get("public", "0", 0)

	sv_entfile = cvar.Cvar_Get("sv_entfile", "1", shared.CVAR_ARCHIVE)

	szone.SZ_Init(netchan.net_message, common_h.MAX_MSGLEN) #SZ_Init(&net_message, net_message_buffer, sizeof(net_message_buffer));

"""
 * Used by SV_Shutdown to send a final message to all
 * connected clients before the server goes down. The
 * messages are sent immediately, not just stuck on the
 * outgoing message list, because the server is going
 * to totally exit after returning from this function.
"""
def SV_FinalMessage(message: str, reconnect: bool): #char *, qboolean

	"""
	int i;
	client_t *cl;
	"""

	szone.SZ_Clear(netchan.net_message)
	movemsg.MSG_WriteByte(netchan.net_message, common_h.svc_ops_e.svc_print.value)
	movemsg.MSG_WriteByte(netchan.net_message, shared.PRINT_HIGH)
	movemsg.MSG_WriteString(netchan.net_message, message)

	if reconnect:

		movemsg.MSG_WriteByte(netchan.net_message, common_h.svc_ops_e.svc_reconnect.value)

	else:

		movemsg.MSG_WriteByte(netchan.net_message, common_h.svc_ops_e.svc_disconnect.value)


	# stagger the packets to crutch operating system limited buffers
	# DG: we can't just use the maxclients cvar here for the number of clients,
	#     because this is called by SV_Shutdown() and the shut down server might have
	#     a different number of clients (e.g. 1 if it's single player), when maxclients
	#     has already been set to a higher value for multiplayer (e.g. 4 for coop)
	#     Luckily, svs.num_client_entities = maxclients->value * UPDATE_BACKUP * 64;
	#     with the maxclients value from when the current server was started (see SV_InitGame())
	#     so we can just calculate the right number of clients from that
	numClients = sv_init.svs.num_client_entities // (common_h.UPDATE_BACKUP * 64)
	for i in range(numClients):

		cl = sv_init.svs.clients[i]
		if cl.state.value >= server_h.client_state_t.cs_connected.value:

			netchan.Netchan_Transmit(cl.netchan, netchan.net_message.data[:netchan.net_message.cursize])



	for i in range(numClients):

		cl = sv_init.svs.clients[i]
		if cl.state.value >= server_h.client_state_t.cs_connected.value:

			netchan.Netchan_Transmit(cl.netchan, netchan.net_message.data[:netchan.net_message.cursize])

# Also called in SpawnServer just in case
def SV_ClearBaselines(): #void

	if sv_init.sv.baselines:

		sv_init.sv.baselines = [] #Z_Free(sv.baselines); sv.baselines = NULL;


	sv_init.sv.numbaselines = 0

"""
 * Called when each game quits,
 * before Sys_Quit or Sys_Error
"""
def SV_Shutdown(finalmsg: str, reconnect: bool): #char *, qboolean

	if sv_init.svs.clients:

		SV_FinalMessage(finalmsg, reconnect)


	Master_Shutdown()
	sv_game.SV_ShutdownGameProgs()

	# free current level
	if sv_init.sv.demofile:

		filesystem.FS_FCloseFile(sv_init.sv.demofile)


	sv_init.sv.configstrings_overflow = [] #StringList_Free(&sv.configstrings_overflow);
	SV_ClearBaselines()
	sv_init.sv.clear() #memset(&sv, 0, sizeof(sv));
	clientserver.Com_SetServerState(sv_init.sv.state.value)

	# free server static data
	#Z_Free(svs.clients); Z_Free(svs.client_entities);

	if sv_init.svs.demofile is not None:

		sv_init.svs.demofile.close()


	sv_init.svs.clear() #memset(&svs, 0, sizeof(svs));
