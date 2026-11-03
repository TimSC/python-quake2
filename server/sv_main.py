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
import random
import struct
from server import sv_ccmds, sv_send, sv_init, sv_game, sv_user
from qcommon import cvar, qcommon, common, net_chan, cmd
from game import q_shared, game
from linux import net_udp
"""
#include "server.h"
"""
master_adr = [] #netadr_t	[MAX_MASTERS], address of group servers
for i in range(sv_init.MAX_MASTERS):
	master_adr.append(qcommon.netadr_t())

sv_client = None #client_t	*, current client

sv_paused = None # cvar_t	*
sv_timedemo = None # cvar_t	*

sv_enforcetime = None # cvar_t	*

timeout = None # cvar_t	*, seconds without any message
zombietime = None # cvar_t	*, seconds to sink messages after disconnect

rcon_password = None #cvar_t	*, password for remote server commands

allow_download = None # cvar_t	*;
allow_download_players = None # cvar_t *;
allow_download_models = None # cvar_t *;
allow_download_sounds = None # cvar_t *;
allow_download_maps = None # cvar_t *;

sv_airaccelerate = None # cvar_t *;

sv_noreload = None # cvar_t	*, don't reload level state when reentering

maxclients = None #cvar_t	*, FIXME: rename sv_maxclients

sv_showclamp = None # cvar_t	*

hostname = None # cvar_t	*
public_server = None # cvar_t	*, should heartbeats be sent

sv_reconnect_limit = None # cvar_t	* minimum seconds between connect messages
"""
void Master_Shutdown (void);

//============================================================================


/*
=====================
SV_DropClient

Called when the player is totally leaving the server, either willingly
or unwillingly.  This is NOT called if the entire server is quiting
or crashing.
=====================
"""
def SV_DropClient (drop): #client_t *

	"""
	# add the disconnect
	MSG_WriteByte (&drop->netchan.message, svc_disconnect);

	if (drop->state == sv_init.server_state_t.cs_spawned)
	{
		// call the prog function for removing a client
		// this will remove the body, among other things
		ge->ClientDisconnect (drop->edict);
	}

	if (drop->download)
	{
		FS_FreeFile (drop->download);
		drop->download = NULL;
	}

	drop->state = sv_init.client_state_t.cs_zombie;		// become free in a few seconds
	drop->name[0] = 0;

	"""


"""
==============================================================================

CONNECTIONLESS COMMANDS

==============================================================================
*/
"""
"""
/*
===============
SV_StatusString

Builds the string that is sent as heartbeats and status replies
===============
*/
char	*SV_StatusString (void)
{
	char	player[1024];
	static char	status[MAX_MSGLEN - 16];
	int		i;
	client_t	*cl;
	int		statusLength;
	int		playerLength;

	strcpy (status, Cvar_Serverinfo());
	strcat (status, "\n");
	statusLength = strlen(status);

	for (i=0 ; i<maxclients->value ; i++)
	{
		cl = &sv_init.svs.clients[i];
		if (cl.state == sv_init.client_state_t.cs_connected || cl.state == sv_init.server_state_t.cs_spawned )
		{
			Com_sprintf (player, sizeof(player), "%i %i \"%s\"\n", 
				cl.edict->client->ps.stats[STAT_FRAGS], cl.ping, cl.name);
			playerLength = strlen(player);
			if (statusLength + playerLength >= sizeof(status) )
				break;		// can't hold any more
			strcpy (status + statusLength, player);
			statusLength += playerLength;
		}
	}

	return status;
}
"""
"""
/*
================
SVC_Status

Responds with all the info that qplug or qspy can see
================
*/
void SVC_Status (void)
{
	net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, "print\n%s", SV_StatusString());
#if 0
	Com_BeginRedirect (RD_PACKET, sv_outputbuf, SV_OUTPUTBUF_LENGTH, SV_FlushRedirect);
	Com_Printf (SV_StatusString());
	Com_EndRedirect ();
#endif
}
"""
"""
/*
================
SVC_Ack

================
*/
void SVC_Ack (void)
{
	Com_Printf ("Ping acknowledge from %s\n", net_udp.NET_AdrToString(net_chan.net_from));
}
"""
"""
/*
================
SVC_Info

Responds with short info for broadcast scans
The second parameter should be the current protocol version number.
================
*/
void SVC_Info (void)
{
	char	string[64];
	int		i, count;
	int		version;

	if (maxclients->value == 1)
		return;		// ignore in single player

	version = atoi (Cmd_Argv(1));

	if (version != PROTOCOL_VERSION)
		Com_sprintf (string, sizeof(string), "%s: wrong version\n", hostname->string, sizeof(string));
	else
	{
		count = 0;
		for (i=0 ; i<maxclients->value ; i++)
			if (sv_init.svs.clients[i].state >= sv_init.client_state_t.cs_connected)
				count++;

		Com_sprintf (string, sizeof(string), "%16s %8s %2i/%2i\n", hostname->string, sv_init.sv.name, count, (int)maxclients->value);
	}

	net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, "info\n%s", string);
}
"""
"""
/*
================
SVC_Ping

Just responds with an acknowledgement
================
*/
void SVC_Ping (void)
{
	net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, "ack");
}
"""
"""
/*
=================
SVC_GetChallenge

Returns a challenge number that can be used
in a subsequent client_connect command.
We do this to prevent denial of service attacks that
flood the server with invalid connection IPs.  With a
challenge, they must give a valid IP address.
=================
*/
void SVC_GetChallenge (void)
{
	int		i;
	int		oldest;
	int		oldestTime;

	oldest = 0;
	oldestTime = 0x7fffffff;

	// see if we already have a challenge for this ip
	for (i = 0 ; i < MAX_CHALLENGES ; i++)
	{
		if (net_udp.NET_CompareBaseAdr (net_chan.net_from, sv_init.svs.challenges[i].adr))
			break;
		if (sv_init.svs.challenges[i].time < oldestTime)
		{
			oldestTime = sv_init.svs.challenges[i].time;
			oldest = i;
		}
	}

	if (i == MAX_CHALLENGES)
	{
		// overwrite the oldest
		sv_init.svs.challenges[oldest].challenge = rand() & 0x7fff;
		sv_init.svs.challenges[oldest].adr = net_chan.net_from;
		sv_init.svs.challenges[oldest].time = curtime;
		i = oldest;
	}

	// send it back
	net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, "challenge %i", sv_init.svs.challenges[i].challenge);
}
"""
"""
/*
==================
SVC_DirectConnect

A connection request that did not come from the master
==================
"""
def SVC_DirectConnect ():

	#char		userinfo[MAX_INFO_STRING];
	#netadr_t	adr;
	#int			i;
	#client_t	*cl, *newcl;
	#client_t	temp;
	#edict_t		*ent;
	#int			edictnum;
	#int			version;
	#int			qport;
	#int			challenge;

	adr = net_chan.net_from

	common.Com_DPrintf ("SVC_DirectConnect ()\n")

	try:
		version = int(cmd.Cmd_Argv(1))
	except ValueError:
		version = None
	if version != qcommon.PROTOCOL_VERSION:
	
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, "print\nServer is version {:4.2f}.\n".format(VERSION))
		common.Com_DPrintf ("    rejected connect from version {}\n".format(version))
		return
	
	try:
		qport = int(cmd.Cmd_Argv(2))
		challenge = int(cmd.Cmd_Argv(3))
	except ValueError:
		qport = None
		challenge = None

	userinfo = cmd.Cmd_Argv(4)

	# force the IP key/value pair so the game can filter based on ip
	userinfo = q_shared.Info_RemoveKey(userinfo, "ip")
	userinfo += q_shared.Info_SetValueForKey ("ip", net_udp.NET_AdrToString(net_chan.net_from))

	# attractloop servers are ONLY for local clients
	if sv_init.sv.attractloop:
	
		if not net_udp.NET_IsLocalAddress (adr):
		
			common.Com_Printf ("Remote connect in attract loop.  Ignored.\n")
			net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, "print\nConnection refused.\n")
			return

	# see if the challenge is valid
	if not net_udp.NET_IsLocalAddress (adr):
		
		pass
		"""
		for (i=0 ; i<MAX_CHALLENGES ; i++)
		{
			if (net_udp.NET_CompareBaseAdr (net_chan.net_from, sv_init.svs.challenges[i].adr))
			{
				if (challenge == sv_init.svs.challenges[i].challenge)
					break;		// good
				net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, "print\nBad challenge.\n");
				return;
			}
		}
		if (i == MAX_CHALLENGES)
		{
			net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, "print\nNo challenge for address.\n");
			return;
		}
		"""

	newcl = sv_init.client_t()

	# if there is already a slot for this ip, reuse it
	for cl in sv_init.svs.clients:
	
		if cl.state == sv_init.client_state_t.cs_free:
			continue
		if net_udp.NET_CompareBaseAdr (adr, cl.netchan.remote_address) \
			and ( cl.netchan.qport == qport \
			or adr.port == cl.netchan.remote_address.port ):
		
			if not net_udp.NET_IsLocalAddress (adr) and (sv_init.svs.realtime - cl.lastconnect) < int(sv_reconnect_limit.value * 1000):
			
				common.Com_DPrintf ("{}:reconnect rejected : too soon\n".format(net_udp.NET_AdrToString (adr)))
				return
			
			common.Com_Printf ("{}:reconnect\n".format(net_udp.NET_AdrToString (adr)))
			newcl = cl
			SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge)
			return
	
	# find a client slot
	newcl = None
	for client in sv_init.svs.clients:
	
		if cl.state == sv_init.client_state_t.cs_free:
		
			newcl = cl
			break
		
	if newcl is None:
	
		Netchan_OutOfBandPrint (NS_SERVER, adr, "print\nServer is full.\n");
		Com_DPrintf ("Rejected a connection.\n");
		return;
	
	SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge)


def SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge):
	
	# build a new connection
	# accept the new client
	# this is the only place a client_t is ever initialized
	#*newcl = temp
	sv_client = newcl
	edictnum = sv_init.svs.clients.index(newcl)
	ent = sv_init.EDICT_NUM(edictnum)
	newcl.edict = ent
	newcl.challenge = challenge # save challenge for checksumming

	# get the game a chance to reject this connection or modify the userinfo
	if not sv_game.ge.ClientConnect (ent, userinfo):
	
		if q_shared.Info_ValueForKey (userinfo, "rejmsg"):
			net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, "print\n{}\nConnection refused.\n".format(  
				q_shared.Info_ValueForKey (userinfo, "rejmsg")))
		else:
			net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, "print\nConnection refused.\n" )
		common.Com_DPrintf ("Game rejected a connection.\n")
		return
	
	# parse some info from the info strings
	newcl.userinfo = userinfo
	SV_UserinfoChanged (newcl)

	# send the connect packet to the client
	net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, adr, b"client_connect")

	net_chan.Netchan_Setup (qcommon.netsrc_t.NS_SERVER, newcl.netchan, adr, qport)

	newcl.state = sv_init.client_state_t.cs_connected
	
	common.SZ_Init(newcl.datagram, qcommon.MAX_MSGLEN)
	newcl.datagram.allowoverflow = True
	newcl.lastmessage = sv_init.svs.realtime	# don't timeout
	newcl.lastconnect = sv_init.svs.realtime

"""
int Rcon_Validate (void)
{
	if (!strlen (rcon_password->string))
		return 0;

	if (strcmp (Cmd_Argv(1), rcon_password->string) )
		return 0;

	return 1;
}

/*
===============
SVC_RemoteCommand

A client issued an rcon command.
Shift down the remaining args
Redirect all printfs
===============
"""
def SVC_RemoteCommand ():

	"""
	int		i;
	char	remaining[1024];

	i = Rcon_Validate ();

	if (i == 0)
		Com_Printf ("Bad rcon from %s:\n%s\n", net_udp.NET_AdrToString (net_chan.net_from), net_message.data+4);
	else
		Com_Printf ("Rcon from %s:\n%s\n", net_udp.NET_AdrToString (net_chan.net_from), net_message.data+4);

	Com_BeginRedirect (RD_PACKET, sv_outputbuf, SV_OUTPUTBUF_LENGTH, SV_FlushRedirect);

	if (!Rcon_Validate ())
	{
		Com_Printf ("Bad rcon_password.\n");
	}
	else
	{
		remaining[0] = 0;

		for (i=2 ; i<Cmd_Argc() ; i++)
		{
			strcat (remaining, Cmd_Argv(i) );
			strcat (remaining, " ");
		}

		Cmd_ExecuteString (remaining);
	}

	Com_EndRedirect ();
}

/*
=================
SV_ConnectionlessPacket

A connectionless packet has four leading 0xff
characters to distinguish it from a game channel.
Clients that are in the game can still send
connectionless packets.
=================
"""
def SV_ConnectionlessPacket ():

	#char	*s;
	#char	*c;

	common.MSG_BeginReading (net_chan.net_message)
	common.MSG_ReadLong (net_chan.net_message)		# skip the -1 marker

	s = common.MSG_ReadStringLine (net_chan.net_message)

	cmd.Cmd_TokenizeString (s, False)

	c = cmd.Cmd_Argv(0)
	common.Com_DPrintf ("Packet {} : {}\n".format(net_udp.NET_AdrToString(net_chan.net_from), c))

	if c == "ping":
		SVC_Ping ()
	elif c == "ack":
		SVC_Ack ()
	elif c == "status":
		SVC_Status ()
	elif c == "info":
		SVC_Info ()
	elif c == "getchallenge":
		SVC_GetChallenge ()
	elif c == "connect":
		SVC_DirectConnect ()
	elif c == "rcon":
		SVC_RemoteCommand ()
	else:
		common.Com_Printf ("bad connectionless packet from {}:\n{}\n".format(
			net_udp.NET_AdrToString (net_chan.net_from), s))


"""
//============================================================================
"""
"""
/*
===================
SV_CalcPings

Updates the cl.ping variables
===================
*/
void SV_CalcPings (void)
{
	int			i, j;
	client_t	*cl;
	int			total, count;

	for (i=0 ; i<maxclients->value ; i++)
	{
		cl = &sv_init.svs.clients[i];
		if (cl.state != sv_init.server_state_t.cs_spawned )
			continue;

#if 0
		if (cl.lastframe > 0)
			cl.frame_latency[sv_init.sv.framenum&(LATENCY_COUNTS-1)] = sv_init.sv.framenum - cl.lastframe + 1;
		else
			cl.frame_latency[sv_init.sv.framenum&(LATENCY_COUNTS-1)] = 0;
#endif

		total = 0;
		count = 0;
		for (j=0 ; j<LATENCY_COUNTS ; j++)
		{
			if (cl.frame_latency[j] > 0)
			{
				count++;
				total += cl.frame_latency[j];
			}
		}
		if (!count)
			cl.ping = 0;
		else
#if 0
			cl.ping = total*100/count - 100;
#else
			cl.ping = total / count;
#endif

		// let the game dll know about the ping
		cl.edict->client->ping = cl.ping;
	}
}
"""
"""
/*
===================
SV_GiveMsec

Every few frames, gives all clients an allotment of milliseconds
for their command moves.  If they exceed it, assume cheating.
===================
"""
def SV_GiveMsec ():

	pass
	"""
	int			i;
	client_t	*cl;

	if (sv_init.sv.framenum & 15)
		return;

	for (i=0 ; i<maxclients->value ; i++)
	{
		cl = &sv_init.svs.clients[i];
		if (cl.state == sv_init.client_state_t.cs_free )
			continue;
		
		cl.commandMsec = 1800;		// 1600 + some slop
	}
}


/*
=================
SV_ReadPackets
=================
"""
def SV_ReadPackets ():

	#int			i;
	#client_t	*cl;
	#int			qport;

	rx, net_chan.net_from = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, net_chan.net_message)

	while rx:
		try:
			# check for connectionless packet (0xffffffff) first
			header = struct.unpack("<l", net_chan.net_message.data[:4]) # *(int *)net_message.data
			if header[0] == -1:
			
				SV_ConnectionlessPacket ()
				continue
			
			# read the qport out of the message so we can fix up
			# stupid address translating routers
			common.MSG_BeginReading (net_chan.net_message)
			common.MSG_ReadLong (net_chan.net_message)		# sequence number
			common.MSG_ReadLong (net_chan.net_message)		# sequence number
			qport = common.MSG_ReadShort (net_chan.net_message) & 0xffff

			# check for packets from connected clients
			i = 0
			while i<maxclients.value:

				try:
					cl=sv_init.svs.clients[i]
					if cl.state == sv_init.client_state_t.cs_free:
						continue
					if not net_udp.NET_CompareBaseAdr (net_chan.net_from, cl.netchan.remote_address):
						continue
					if cl.netchan.qport != qport:
						continue
					if cl.netchan.remote_address.port != net_chan.net_from.port:
					
						common.Com_Printf ("SV_ReadPackets: fixing up a translated port\n")
						cl.netchan.remote_address.port = net_chan.net_from.port
					
					if net_chan.Netchan_Process(cl.netchan, net_chan.net_message):
						# this is a valid, sequenced packet, so process it
						if cl.state != sv_init.client_state_t.cs_zombie:
						
							cl.lastmessage = sv_init.svs.realtime	# don't timeout
							sv_user.SV_ExecuteClientMessage (cl)
						
					break

				finally:
					i+=1
			
			if i != maxclients.value:
				continue

		finally:
			rx, net_chan.net_from = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_SERVER, net_chan.net_from, net_chan.net_message)

"""
==================
SV_CheckTimeouts

If a packet has not been received from a client for timeout->value
seconds, drop the conneciton.  Server frames are used instead of
realtime to avoid dropping the local client while debugging.

When a client is normally dropped, the client_t goes into a zombie state
for a few seconds to make sure any final reliable message gets resent
if necessary
==================
"""
def SV_CheckTimeouts ():

	pass
	"""

	int		i;
	client_t	*cl;
	int			droppoint;
	int			zombiepoint;

	droppoint = sv_init.svs.realtime - 1000*timeout->value;
	zombiepoint = sv_init.svs.realtime - 1000*zombietime->value;

	for (i=0,cl=sv_init.svs.clients ; i<maxclients->value ; i++,cl++)
	{
		// message times may be wrong across a changelevel
		if (cl.lastmessage > sv_init.svs.realtime)
			cl.lastmessage = sv_init.svs.realtime;

		if (cl.state == sv_init.client_state_t.cs_zombie
		&& cl.lastmessage < zombiepoint)
		{
			cl.state = sv_init.client_state_t.cs_free;	// can now be reused
			continue;
		}
		if ( (cl.state == sv_init.client_state_t.cs_connected || cl.state == sv_init.server_state_t.cs_spawned) 
			&& cl.lastmessage < droppoint)
		{
			SV_BroadcastPrintf (PRINT_HIGH, "%s timed out\n", cl.name);
			SV_DropClient (cl); 
			cl.state = sv_init.client_state_t.cs_free;	// don't bother with zombie state
		}
	}
}

/*
================
SV_PrepWorldFrame

This has to be done before the world logic, because
player processing happens outside RunWorldFrame
================
"""
def SV_PrepWorldFrame ():

	pass
	"""
	edict_t	*ent;
	int		i;

	for (i=0 ; i<ge->num_edicts ; i++, ent++)
	{
		ent = EDICT_NUM(i);
		// events only last for a single message
		ent->s.event = 0;
	}

}


/*
=================
SV_RunGameFrame
=================
"""
def SV_RunGameFrame ():
	

	if int(common.host_speeds.value):
		time_before_game = q_shlinux.Sys_Milliseconds ()

	# we always need to bump framenum, even if we
	# don't run the world, otherwise the delta
	# compression can get confused when a client
	# has the "current" frame
	sv_init.sv.framenum+=1
	sv_init.sv.time = sv_init.sv.framenum*100

	# don't run if paused
	if not int(sv_paused.value) or int(maxclients.value) > 1:
	
		sv_game.ge.RunFrame ()

		# never get more than one tic behind
		if sv_init.sv.time < sv_init.svs.realtime:
		
			if int(sv_showclamp.value):
				common.Com_Printf ("sv highclamp\n")
			sv_init.svs.realtime = sv_init.sv.time

	if int(common.host_speeds.value):
		time_after_game = q_shlinux.Sys_Milliseconds ()



"""
==================
SV_Frame

==================
"""
def SV_Frame (msec): #int
 
	common.time_before_game = 0
	common.time_after_game = 0
	
	# if server is not active, do nothing
	if not sv_init.svs.initialized:
		return
	
	sv_init.svs.realtime += msec

	# keep the random time dependent
	random.randint(0, 1 << 32)

	# check timeouts
	SV_CheckTimeouts ()

	# get packets from clients
	SV_ReadPackets ()

	# move autonomous things around if enough time has passed
	if not int(sv_timedemo.value) and sv_init.svs.realtime < sv_init.sv.time:

		# never let the time get too far off
		if sv_init.sv.time - sv_init.svs.realtime > 100:
		
			if int(sv_showclamp.value):
				Com_Printf ("sv lowclamp\n");
			sv_init.svs.realtime = sv_init.sv.time - 100
		
		net_udp.NET_Sleep(sv_init.sv.time - sv_init.svs.realtime)
		return
	
	"""
	# update ping based on the last known frame from all clients
	SV_CalcPings ()
	"""
	# give the clients some timeslices
	SV_GiveMsec ()

	# let everything in the world think and move
	SV_RunGameFrame ()

	# send messages back to the clients that had packets read this frame
	sv_send.SV_SendClientMessages ()
	"""
	# save the entire world state if recording a serverdemo
	SV_RecordDemoMessage ();

	# send a heartbeat to the master if needed
	Master_Heartbeat ()
	"""
	# clear teleport flags, etc for next frame
	SV_PrepWorldFrame ()

"""
//============================================================================
"""
"""
/*
================
Master_Heartbeat

Send a message to the master every few minutes to
let it know we are alive, and log information
================
*/
#define	HEARTBEAT_SECONDS	300
void Master_Heartbeat (void)
{
	char		*string;
	int			i;

	// pgm post3.19 change, cvar pointer not validated before dereferencing
	if (!dedicated || !dedicated->value)
		return;		// only dedicated servers send heartbeats

	// pgm post3.19 change, cvar pointer not validated before dereferencing
	if (!public_server || !public_server->value)
		return;		// a private dedicated game

	// check for time wraparound
	if (sv_init.svs.last_heartbeat > sv_init.svs.realtime)
		sv_init.svs.last_heartbeat = sv_init.svs.realtime;

	if (sv_init.svs.realtime - sv_init.svs.last_heartbeat < HEARTBEAT_SECONDS*1000)
		return;		// not time to send yet

	sv_init.svs.last_heartbeat = sv_init.svs.realtime;

	// send the same string that we would give for a status OOB command
	string = SV_StatusString();

	// send to group master
	for (i=0 ; i<MAX_MASTERS ; i++)
		if (master_adr[i].port)
		{
			Com_Printf ("Sending heartbeat to %s\n", net_udp.NET_AdrToString (master_adr[i]));
			net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, master_adr[i], "heartbeat\n%s", string);
		}
}
"""
"""
/*
=================
Master_Shutdown

Informs all masters that this server is going down
=================
"""
def Master_Shutdown ():

	#int			i;

	# pgm post3.19 change, cvar pointer not validated before dereferencing
	if common.dedicated is None or not common.dedicated.value:
		return		# only dedicated servers send heartbeats

	# pgm post3.19 change, cvar pointer not validated before dereferencing
	if public_server is None or not public_server.value:
		return		# a private dedicated game

	# send to group master
	for i in range(sv_init.MAX_MASTERS):
		if master_adr[i].port:
		
			if i > 0:
				common.Com_Printf ("Sending heartbeat to {}\n".format(net_udp.NET_AdrToString (master_adr[i])))
			net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_SERVER, master_adr[i], b"shutdown")
		
"""

//============================================================================



=================
SV_UserinfoChanged

Pull specific info from a newly changed userinfo string
into a more C freindly form.
=================
"""
def SV_UserinfoChanged (cl): #client_t *

	pass
	"""
	char	*val;
	int		i;

	// call prog code to allow overrides
	ge->ClientUserinfoChanged (cl.edict, cl.userinfo);
	
	// name for C code
	strncpy (cl.name, q_shared.Info_ValueForKey (cl.userinfo, "name"), sizeof(cl.name)-1);
	// mask off high bit
	for (i=0 ; i<sizeof(cl.name) ; i++)
		cl.name[i] &= 127;

	// rate command
	val = q_shared.Info_ValueForKey (cl.userinfo, "rate");
	if (strlen(val))
	{
		i = atoi(val);
		cl.rate = i;
		if (cl.rate < 100)
			cl.rate = 100;
		if (cl.rate > 15000)
			cl.rate = 15000;
	}
	else
		cl.rate = 5000;

	// msg command
	val = q_shared.Info_ValueForKey (cl.userinfo, "msg");
	if (strlen(val))
	{
		cl.messagelevel = atoi(val);
	}

}


//============================================================================

/*
===============
SV_Init

Only called at quake2.exe startup, not for each game
===============
"""
def SV_Init ():

	global rcon_password, maxclients, hostname, timeout, zombietime
	global sv_showclamp, sv_paused, sv_timedemo, sv_enforcetime
	global allow_download, allow_download_players, allow_download_models, allow_download_sounds, allow_download_maps
	global sv_noreload, sv_airaccelerate, public_server, sv_reconnect_limit

	sv_ccmds.SV_InitOperatorCommands()
	
	rcon_password = cvar.Cvar_Get ("rcon_password", "", 0)
	cvar.Cvar_Get ("skill", "1", 0)
	cvar.Cvar_Get ("deathmatch", "0", q_shared.CVAR_LATCH)
	cvar.Cvar_Get ("coop", "0", q_shared.CVAR_LATCH)
	cvar.Cvar_Get ("dmflags", "".format(q_shared.DF_INSTANT_ITEMS), q_shared.CVAR_SERVERINFO)
	cvar.Cvar_Get ("fraglimit", "0", q_shared.CVAR_SERVERINFO)
	cvar.Cvar_Get ("timelimit", "0", q_shared.CVAR_SERVERINFO)
	cvar.Cvar_Get ("cheats", "0", q_shared.CVAR_SERVERINFO|q_shared.CVAR_LATCH)
	cvar.Cvar_Get ("protocol", "{}".format(qcommon.PROTOCOL_VERSION), q_shared.CVAR_SERVERINFO|q_shared.CVAR_NOSET)
	maxclients = cvar.Cvar_Get ("maxclients", "1", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)
	hostname = cvar.Cvar_Get ("hostname", "noname", q_shared.CVAR_SERVERINFO | q_shared.CVAR_ARCHIVE)
	timeout = cvar.Cvar_Get ("timeout", "125", 0)
	zombietime = cvar.Cvar_Get ("zombietime", "2", 0)
	sv_showclamp = cvar.Cvar_Get ("showclamp", "0", 0)
	sv_paused = cvar.Cvar_Get ("paused", "0", 0)
	sv_timedemo = cvar.Cvar_Get ("timedemo", "0", 0)
	sv_enforcetime = cvar.Cvar_Get ("sv_enforcetime", "0", 0)
	allow_download = cvar.Cvar_Get ("allow_download", "1", q_shared.CVAR_ARCHIVE)
	allow_download_players  = cvar.Cvar_Get ("allow_download_players", "0", q_shared.CVAR_ARCHIVE)
	allow_download_models = cvar.Cvar_Get ("allow_download_models", "1", q_shared.CVAR_ARCHIVE)
	allow_download_sounds = cvar.Cvar_Get ("allow_download_sounds", "1", q_shared.CVAR_ARCHIVE)
	allow_download_maps	  = cvar.Cvar_Get ("allow_download_maps", "1", q_shared.CVAR_ARCHIVE)

	sv_noreload = cvar.Cvar_Get ("sv_noreload", "0", 0)

	sv_airaccelerate = cvar.Cvar_Get("sv_airaccelerate", "0", q_shared.CVAR_LATCH)

	public_server = cvar.Cvar_Get ("public", "0", 0)

	sv_reconnect_limit = cvar.Cvar_Get ("sv_reconnect_limit", "3", q_shared.CVAR_ARCHIVE)

	#net_chan.net_message = ""

"""
==================
SV_FinalMessage

Used by SV_Shutdown to send a final message to all
connected clients before the server goes down.  The messages are sent immediately,
not just stuck on the outgoing message list, because the server is going
to totally exit after returning from this function.
==================
*/
"""
def SV_FinalMessage (message, reconnect): #char *, qboolean

	#int			i;
	#client_t	*cl;
	
	common.SZ_Clear (net_chan.net_message)
	common.MSG_WriteByte (net_chan.net_message, qcommon.svc_ops_e.svc_print.value)
	common.MSG_WriteByte (net_chan.net_message, q_shared.PRINT_HIGH)
	common.MSG_WriteString (net_chan.net_message, message.encode('ascii'))

	if reconnect:
		common.MSG_WriteByte (net_chan.net_message, qcommon.svc_ops_e.svc_reconnect.value)
	else:
		common.MSG_WriteByte (net_chan.net_message, qcommon.svc_ops_e.svc_disconnect.value)

	# send it twice
	# stagger the packets to crutch operating system limited buffers

	for i in range(int(maxclients.value)):
		cl = sv_init.svs.clients[i]
		if cl.state.value >= sv_init.client_state_t.cs_connected.value:
			net_chan.Netchan_Transmit (cl.netchan, net_chan.net_message.data[:net_chan.net_message.cursize])

	for i in range(int(maxclients.value)):
		cl = sv_init.svs.clients[i]
		if cl.state.value >= sv_init.client_state_t.cs_connected.value:
			net_chan.Netchan_Transmit (cl.netchan, net_chan.net_message.data[:net_chan.net_message.cursize])



"""
================
SV_Shutdown

Called when each game quits,
before Sys_Quit or Sys_Error
================
"""
def SV_Shutdown (finalmsg, reconnect): #char *, qboolean

	if sv_init.svs.clients:
		SV_FinalMessage (finalmsg, reconnect)

	Master_Shutdown ()
	sv_game.SV_ShutdownGameProgs ()

	# free current level
	if sv_init.sv.demofile is not None:
		sv_init.sv.demofile.close ()
	sv_init.sv.clear () # memset (&sv, 0, sizeof(sv));
	common.Com_SetServerState (sv_init.sv.state.value)

	# free server static data
	# Z_Free (svs.clients); Z_Free (svs.client_entities);
	if sv_init.svs.demofile is not None:
		sv_init.svs.demofile.close ()
	sv_init.svs.clear () # memset (&svs, 0, sizeof(svs));

