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

Connectionless server commands.

=======================================================================
"""
from __future__ import annotations

import random
from backends.unix import network, system
from common.header import common as common_h
from common.shared import shared as shared_c
from common.shared import rand
from common import clientserver
from common import frame
from common import cmdparser
from common import movemsg
from common import netchan
from server.header import server as server_h
from server import sv_init
from server import sv_main
from server import sv_send

"""
#include "header/server.h"
"""

def SVC_Status ():

	netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, netchan.net_from, "print\n{}".format(sv_main.SV_StatusString()))
"""
================
SVC_Ack

================
"""
def SVC_Ack ():

	clientserver.Com_Printf ("Ping acknowledge from {}\n".format(network.NET_AdrToString(netchan.net_from)))
"""
================
SVC_Info

Responds with short info for broadcast scans
The second parameter should be the current protocol version number.
================
"""
def SVC_Info ():

	string = "" #char[64]

	if sv_main.maxclients.value == 1:
		return		# ignore in single player

	try:
		version = int(cmdparser.Cmd_Argv(1))
	except ValueError:
		version = None

	if version != common_h.PROTOCOL_VERSION:
		string = "{}: wrong version\n".format(sv_main.hostname.string)
	else:
		count = 0
		for i in range(int(sv_main.maxclients.value)):
			if sv_init.svs.clients[i].state >= server_h.client_state_t.cs_connected:
				count += 1

		string = "{:16s} {:8s} {}/{}\n".format(sv_main.hostname.string, sv_init.sv.name, count, int(sv_main.maxclients.value))

	netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, netchan.net_from, "info\n{}".format(string))
"""
================
SVC_Ping

Just responds with an acknowledgement
================
"""
def SVC_Ping ():

	netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, netchan.net_from, "ack")
"""
=================
SVC_GetChallenge

Returns a challenge number that can be used
in a subsequent client_connect command.
We do this to prevent denial of service attacks that
flood the server with invalid connection IPs.  With a
challenge, they must give a valid IP address.
=================
"""
def SVC_GetChallenge ():

	oldest = 0
	oldestTime = 0x7fffffff
	i = None

	# see if we already have a challenge for this ip
	for k in range(server_h.MAX_CHALLENGES):
		if network.NET_CompareBaseAdr (netchan.net_from, sv_init.svs.challenges[k].adr):
			i = k
			break
		if sv_init.svs.challenges[k].time < oldestTime:
			oldestTime = sv_init.svs.challenges[k].time
			oldest = k

	if i is None:
		# overwrite the oldest
		sv_init.svs.challenges[oldest].challenge = rand.randk() & 0x7fff
		sv_init.svs.challenges[oldest].adr = netchan.net_from
		sv_init.svs.challenges[oldest].time = frame.curtime
		i = oldest

	# send it back
	netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, netchan.net_from, "challenge %i p=34", sv_init.svs.challenges[i].challenge)
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

	adr = netchan.net_from

	clientserver.Com_DPrintf ("SVC_DirectConnect ()\n")

	try:
		version = int(cmdparser.Cmd_Argv(1))
	except ValueError:
		version = None
	if version != common_h.PROTOCOL_VERSION:
	
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, adr, "print\nServer is protocol version 34.\n")
		clientserver.Com_DPrintf ("    rejected connect from version {}\n".format(version))
		return
	
	try:
		qport = int(cmdparser.Cmd_Argv(2))
		challenge = int(cmdparser.Cmd_Argv(3))
	except ValueError:
		qport = None
		challenge = None

	userinfo = cmdparser.Cmd_Argv(4)

	# force the IP key/value pair so the game can filter based on ip
	userinfo = shared_c.Info_SetValueForKey (userinfo, "ip", network.NET_AdrToString(netchan.net_from))

	# attractloop servers are ONLY for local clients
	if sv_init.sv.attractloop:
	
		if not network.NET_IsLocalAddress (adr):
		
			clientserver.Com_Printf ("Remote connect in attract loop.  Ignored.\n")
			netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, adr, "print\nConnection refused.\n")
			return

	# see if the challenge is valid
	if not network.NET_IsLocalAddress (adr):
		
		pass
		found = False
		for i in range(server_h.MAX_CHALLENGES):
			if network.NET_CompareBaseAdr (netchan.net_from, sv_init.svs.challenges[i].adr):
				found = True
				if challenge == sv_init.svs.challenges[i].challenge:
					break		# good
				netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, adr, "print\nBad challenge.\n")
				return
		if not found:
			netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, adr, "print\nNo challenge for address.\n")
			return

	newcl = server_h.client_t()

	# if there is already a slot for this ip, reuse it
	for cl in sv_init.svs.clients:
	
		if cl.state.value < server_h.client_state_t.cs_connected.value:
			continue
		if network.NET_CompareBaseAdr (adr, cl.netchan.remote_address) \
			and ( cl.netchan.qport == qport \
			or adr.port == cl.netchan.remote_address.port ):
		
			if not network.NET_IsLocalAddress (adr):
			
				clientserver.Com_DPrintf ("{}:reconnect rejected : too soon\n".format(network.NET_AdrToString (adr)))
				return
			
			clientserver.Com_Printf ("{}:reconnect\n".format(network.NET_AdrToString (adr)))
			newcl = cl
			sv_main.SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge)
			return
	
	# find a client slot
	newcl = None
	for i in range(int(sv_main.maxclients.value)):
	
		cl = sv_init.svs.clients[i]
		if cl.state == server_h.client_state_t.cs_free:
		
			newcl = cl
			break
		
	if newcl is None:
	
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, adr, "print\nServer is full.\n")
		clientserver.Com_DPrintf ("Rejected a connection.\n")
		return;
	
	sv_main.SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge)

"""
================
Rcon_Validate

Returns true if the current net_from is allowed
to issue remote commands.
================
"""
def Rcon_Validate (): #int

	ri = sv_main.rcon_password
	if ri.value < 3:
		return True
	if ri.value == 3:
		adr = network.NET_AdrToString(netchan.net_from)
		if ri.string[0] == '*' and ri.string[1:].lower() == adr.lower():
			return True
		if ri.string[0] == '*':
			return False

	return ri.string.lower() == network.NET_AdrToString(netchan.net_from).lower()
def SVC_RemoteCommand ():

	#char		remaining[1024];

	i = Rcon_Validate ()

	if i == 0:
		clientserver.Com_Printf ("Bad rcon from {}:\n{}\n".format(network.NET_AdrToString (netchan.net_from), netchan.net_message.data[4:].decode('ascii')))
	else:
		clientserver.Com_Printf ("Rcon from {}:\n{}\n".format(network.NET_AdrToString (netchan.net_from), netchan.net_message.data[4:].decode('ascii')))

	clientserver.Com_BeginRedirect (server_h.redirect_t.RD_PACKET.value, sv_send.sv_outputbuf, server_h.SV_OUTPUTBUF_LENGTH, sv_send.SV_FlushRedirect)

	if not Rcon_Validate ():
		clientserver.Com_Printf ("Bad rcon_password.\n")
	else:
		remaining = ""
		for i in range(2, cmdparser.Cmd_Argc()):
			remaining += cmdparser.Cmd_Argv(i) + " "

		cmdparser.Cmd_ExecuteString (remaining)

	clientserver.Com_EndRedirect ()

"""
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

	movemsg.MSG_BeginReading (netchan.net_message)
	movemsg.MSG_ReadLong (netchan.net_message)		# skip the -1 marker

	s = movemsg.MSG_ReadStringLine (netchan.net_message)

	cmdparser.Cmd_TokenizeString (s, False)

	c = cmdparser.Cmd_Argv(0)
	clientserver.Com_DPrintf ("Packet {} : {}\n".format(network.NET_AdrToString(netchan.net_from), c))

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
		clientserver.Com_Printf ("bad connectionless packet from {}:\n{}\n".format(
			network.NET_AdrToString (netchan.net_from), s))
