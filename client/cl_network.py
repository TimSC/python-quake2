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

This file implements generic network functions

=======================================================================
"""
from __future__ import annotations

import struct
from client import snd_dma, menu, cl_cin, cl_parse
from linux import q_shlinux, vid_so, net_udp, sys_linux
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar
from common import movemsg
from common import szone
from common import netchan
from server import sv_main
from client import cl_main
from client import cl_parse
from client import cl_screen
from client.header import client as client_h

"""
#include "header/client.h"
#include "../client/sound/header/local.h"
"""

def Cmd_ForwardToServer ():

	#char	*cmd;

	cmd_name = cmdparser.Cmd_Argv(0)
	if cl_main.cls.state.value <= client_h.connstate_t.ca_connected.value or cmd_name[:1] == '-' or cmd_name[:1] == '+':
	
		clientserver.Com_Printf ("Unknown command \"{}\"\n".format(cmd_name))
		return
	
	movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
	szone.SZ_Print (cl_main.cls.netchan.message, cmd_name)
	if cmdparser.Cmd_Argc() > 1:
	
		szone.SZ_Print (cl_main.cls.netchan.message, " ")
		szone.SZ_Print (cl_main.cls.netchan.message, cmdparser.Cmd_Args())

		

"""
==================
CL_ForwardToServer_f
==================
"""
def CL_ForwardToServer_f ():

	if cl_main.cls.state != client_h.connstate_t.ca_connected and cl_main.cls.state != client_h.connstate_t.ca_active:
	
		clientserver.Com_Printf ("Can't \"{}\", not connected\n".format(cmdparser.Cmd_Argv(0)))
		return
	
	# don't forward the first argument
	if cmdparser.Cmd_Argc() > 1:
	
		movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
		szone.SZ_Print (cl_main.cls.netchan.message, cmdparser.Cmd_Args())


"""
================
CL_Drop

Called after an q_shared.ERR_DROP was thrown
================
"""
def CL_Drop ():
	if cl_main.cls.state == client_h.connstate_t.ca_uninitialized:
		return
	if cl_main.cls.state == client_h.connstate_t.ca_disconnected:
		return

	CL_Disconnect()

	# drop loading plaque unless this is the initial game start
	if cl_main.cls.disable_servercount != -1:
		cl_screen.SCR_EndLoadingPlaque()


# =======================
# CL_SendConnectPacket
#
# We have gotten a challenge from the server, so try and
# connect.
# ======================
def CL_SendConnectPacket ():

	#netadr_t	adr;
	#int		port;

	adr = net_udp.NET_StringToAdr (cl_main.cls.servername)
	if adr is None:
	
		clientserver.Com_Printf ("Bad server address\n")
		cl_main.cls.connect_time = 0
		return
	
	if not adr.port:
		adr.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)

	port = int(cvar.Cvar_VariableValue ("qport"))
	cvar.userinfo_modified = False

	netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_CLIENT, adr, "connect {:d} {:d} {:d} \"{}\"\n".format(
		common_h.PROTOCOL_VERSION, port, cl_main.cls.challenge, cvar.Cvar_Userinfo()).encode('ascii') )


"""
=================
CL_CheckForResend

Resend a connect message if the last one has timed out
=================
"""
def CL_CheckForResend ():

	#netadr_t	adr;

	# if the local server is running and we aren't
	# then connect
	if cl_main.cls.state == client_h.connstate_t.ca_disconnected and clientserver.Com_ServerState():
	
		cl_main.cls.state = client_h.connstate_t.ca_connecting
		cl_main.cls.servername = "localhost"
		# we don't need a challenge on the localhost
		CL_SendConnectPacket ()
		return
		##cls.connect_time = -99999;	// CL_CheckForResend() will fire immediately

	# resend if we haven't gotten a reply yet
	if cl_main.cls.state != client_h.connstate_t.ca_connecting:
		return

	if cl_main.cls.realtime - cl_main.cls.connect_time < 3000:
		return

	adr = net_udp.NET_StringToAdr(cl_main.cls.servername)
	if adr is None:
		clientserver.Com_Printf("Bad server address\n")
		cl_main.cls.state = client_h.connstate_t.ca_disconnected
		return

	if not adr.port:
		adr.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)

	cl_main.cls.connect_time = cl_main.cls.realtime

	clientserver.Com_Printf("Connecting to {}...\n".format(cl_main.cls.servername))

	netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_CLIENT, adr, b"getchallenge\n")


"""
================
CL_Connect_f

================
"""
def CL_Connect_f ():

	#char	*server;

	if cmdparser.Cmd_Argc() != 2:
	
		clientserver.Com_Printf ("usage: connect <server>\n")
		return	
	
	if clientserver.Com_ServerState ():
		# if running a local server, kill it and reissue
		sv_main.SV_Shutdown ("Server quit\n", False)
	
	else:
	
		CL_Disconnect ()
	
	server = cmdparser.Cmd_Argv (1)

	net_udp.NET_Config (True)		# allow remote

	CL_Disconnect ()

	cl_main.cls.state = client_h.connstate_t.ca_connecting
	cl_main.cls.servername = server[:shared.MAX_OSPATH-1] # strncpy (cls.servername, server, sizeof(cls.servername)-1);
	cl_main.cls.connect_time = -99999	# CL_CheckForResend() will fire immediately


"""
=====================
CL_Rcon_f

  Send the rest of the command line over as
  an unconnected command.
=====================
"""
def CL_Rcon_f ():

	#char	message[1024];
	#int		i;
	#netadr_t	to;

	if cl_main.rcon_client_password.string is None:
	
		clientserver.Com_Printf ("You must set 'rcon_password' before\n"
					"issuing an rcon command.\n")
		return
	
	message = bytearray(b"\xff\xff\xff\xff") # message[0..3] = (char)255; message[4] = 0;

	net_udp.NET_Config (True)		# allow remote

	message += b"rcon "

	message += cl_main.rcon_client_password.string.encode('ascii')
	message += b" "

	for i in range(1, cmdparser.Cmd_Argc()):
	
		message += cmdparser.Cmd_Argv(i).encode('ascii')
		message += b" "
	
	if cl_main.cls.state.value >= client_h.connstate_t.ca_connected.value:
		to = cl_main.cls.netchan.remote_address
	else:
	
		if not len(cl_main.rcon_address.string):
		
			clientserver.Com_Printf ("You must either be connected,\n"
						"or set the 'rcon_address' cvar\n"
						"to issue rcon commands\n")

			return
		
		to = net_udp.NET_StringToAdr (cl_main.rcon_address.string)
		if to is None: # C ignores the failure and sends to an empty address
			to = common_h.netadr_t()
		if to.port == 0:
			to.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)
	
	message += b"\0"
	net_udp.NET_SendPacket (common_h.netsrc_t.NS_CLIENT, bytes(message), to) # strlen(message)+1


"""
=====================
CL_Disconnect

Goes from a connected state to full screen console state
Sends a disconnect message to the server
This is also called on Com_Error, so it shouldn't cause any errors
=====================
"""
def CL_Disconnect ():


	"""
	byte	final[32];
	"""

	if cl_main.cls.state == client_h.connstate_t.ca_disconnected:
		return

	if cl_main.cl_timedemo is not None and int(cl_main.cl_timedemo.value):
	
		#int	time;
		
		time = q_shlinux.Sys_Milliseconds () - cl_main.cl.timedemo_start
		if time > 0:
			clientserver.Com_Printf ("{} frames, {:3.1f} seconds: {:3.1f} fps\n".format(cl_main.cl.timedemo_frames,
			time/1000.0, cl_main.cl.timedemo_frames*1000.0 / time))
	
	shared.VectorClear (cl_main.cl.refdef.blend)
	vid_so.re.CinematicSetPalette(None)

	menu.M_ForceMenuOff ()

	cl_main.cls.connect_time = 0

	cl_cin.SCR_StopCinematic ()

	if cl_main.cls.demorecording:
		cl_main.CL_Stop_f ()

	# send a disconnect message to the server
	final = bytearray()
	final += struct.pack("B", common_h.clc_ops_e.clc_stringcmd.value)
	final += b"disconnect"
	netchan.Netchan_Transmit (cl_main.cls.netchan, final)
	netchan.Netchan_Transmit (cl_main.cls.netchan, final)
	netchan.Netchan_Transmit (cl_main.cls.netchan, final)

	cl_main.CL_ClearState ()

	# stop download
	if cl_main.cls.download is not None:
		cl_main.cls.download.close()
		cl_main.cls.download = None
	
	cl_main.cls.state = client_h.connstate_t.ca_disconnected


def CL_Disconnect_f ():

	clientserver.Com_Error (shared.ERR_DROP, "Disconnected from server");


"""
====================
CL_Packet_f

packet <destination> <contents>

Contents allows \n escape character
====================
"""
def CL_Packet_f ():

	#char	send[2048];
	#int		i, l;
	#char	*in, *out;
	#netadr_t	adr;

	if cmdparser.Cmd_Argc() != 3:
	
		clientserver.Com_Printf ("packet <destination> <contents>\n")
		return
	
	net_udp.NET_Config (True)		# allow remote

	adr = net_udp.NET_StringToAdr (cmdparser.Cmd_Argv(1))
	if adr is None:
	
		clientserver.Com_Printf ("Bad address\n")
		return
	
	if not adr.port:
		adr.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)

	in_str = cmdparser.Cmd_Argv(2)
	send = bytearray(b"\xff\xff\xff\xff") # send[0] = send[1] = send[2] = send[3] = (char)0xff;

	l = len (in_str)
	i = 0
	while i < l:
	
		if in_str[i] == '\\' and in_str[i+1:i+2] == 'n':
		
			send += b"\n"
			i += 1
		
		else:
			send += in_str[i].encode('latin-1')
		i += 1
	
	# *out = 0;

	net_udp.NET_SendPacket (common_h.netsrc_t.NS_CLIENT, bytes(send), adr) # out-send, excludes the terminator


"""
/*
=================
CL_Changing_f

Just sent as a hint to the client that they should
drop to full console
=================
"""
def CL_Changing_f ():

	#ZOID
	#if we are downloading, we don't change!  This so we don't suddenly stop downloading a map
	if cl_main.cls.download is not None:
		return

	cl_screen.SCR_BeginLoadingPlaque ()
	cl_main.cls.state = client_h.connstate_t.ca_connected # not active anymore, but not disconnected
	clientserver.Com_Printf ("\nChanging map...\n")

"""
=================
CL_Reconnect_f

The server is changing levels
=================
"""
def CL_Reconnect_f ():

	#ZOID
	#if we are downloading, we don't change!  This so we don't suddenly stop downloading a map
	if cl_main.cls.download is not None:
		return

	snd_dma.S_StopAllSounds ()
	if cl_main.cls.state == client_h.connstate_t.ca_connected:
		clientserver.Com_Printf ("reconnecting...\n")
		cl_main.cls.state = client_h.connstate_t.ca_connected
		movemsg.MSG_WriteChar (cl_main.cls.netchan.message, struct.pack("B", common_h.clc_ops_e.clc_stringcmd.value))
		movemsg.MSG_WriteString (cl_main.cls.netchan.message, b"new")
		return

	if cl_main.cls.servername:
		if cl_main.cls.state.value >= client_h.connstate_t.ca_connected.value:
			CL_Disconnect()
			cl_main.cls.connect_time = cl_main.cls.realtime - 1500
		else:
			cl_main.cls.connect_time = -99999 # fire immediately

		cl_main.cls.state = client_h.connstate_t.ca_connecting
		clientserver.Com_Printf ("reconnecting...\n")


"""
=================
CL_PingServers_f
=================
"""
def CL_PingServers_f ():

	"""
	int			i;
	netadr_t	adr;
	char		name[32];
	char		*adrstring;
	cvar_t		*noudp;
	cvar_t		*noipx;
	"""
	adr = common_h.netadr_t()

	net_udp.NET_Config (True)		# allow remote

	# send a broadcast packet
	clientserver.Com_Printf ("pinging broadcast...\n")

	noudp = cvar.Cvar_Get ("noudp", "0", shared.CVAR_NOSET)
	if not noudp.value:
	
		adr.type = common_h.netadrtype_t.NA_BROADCAST
		adr.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_CLIENT, adr, "info {}".format(common_h.PROTOCOL_VERSION).encode("ascii"))
	
	noipx = cvar.Cvar_Get ("noipx", "0", shared.CVAR_NOSET)
	if not noipx.value:
	
		adr.type = common_h.netadrtype_t.NA_BROADCAST_IPX
		adr.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_CLIENT, adr, "info {}".format(common_h.PROTOCOL_VERSION).encode("ascii"))
	
	# send a packet to each address book entry
	for i in range(16):
	
		name = "adr{}".format(i)
		adrstring = cvar.Cvar_VariableString (name)
		if not adrstring:
			continue

		clientserver.Com_Printf ("pinging {}...\n".format(adrstring))
		adr = net_udp.NET_StringToAdr (adrstring)
		if adr is None:
		
			clientserver.Com_Printf ("Bad address: {}\n".format(adrstring))
			continue
		
		if not adr.port:
			adr.port = shared_c.BigShort (struct.pack("=H", common_h.PORT_SERVER)) # BigShort (PORT_SERVER)
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_CLIENT, adr, "info {}".format(common_h.PROTOCOL_VERSION).encode("ascii"))

	
"""


/*
=================
CL_ConnectionlessPacket

Responses to broadcasts, etc
=================
"""
def CL_ConnectionlessPacket ():

	#char	*s;
	#char	*c;
	
	movemsg.MSG_BeginReading (netchan.net_message)
	movemsg.MSG_ReadLong (netchan.net_message)	# skip the -1

	s = movemsg.MSG_ReadStringLine (netchan.net_message)

	cmdparser.Cmd_TokenizeString (s, False)

	c = cmdparser.Cmd_Argv(0)

	clientserver.Com_Printf ("{}: {}\n".format(net_udp.NET_AdrToString (netchan.net_from), c))

	# server connection
	if c == "client_connect":
	
		if cl_main.cls.state == client_h.connstate_t.ca_connected:
		
			clientserver.Com_Printf ("Dup connect received.  Ignored.\n")
			return
		
		netchan.Netchan_Setup (common_h.netsrc_t.NS_CLIENT, cl_main.cls.netchan, netchan.net_from, cl_main.cls.quakePort)
		movemsg.MSG_WriteChar (cl_main.cls.netchan.message, struct.pack("B", common_h.clc_ops_e.clc_stringcmd.value))
		movemsg.MSG_WriteString (cl_main.cls.netchan.message, b"new")	
		cl_main.cls.state = client_h.connstate_t.ca_connected
		return
	
	# server responding to a status broadcast
	if c == "info":
	
		cl_main.CL_ParseStatusMessage ()
		return
	
	# remote command from gui front end
	if c == "cmd":
	
		if not net_udp.NET_IsLocalAddress(netchan.net_from):
		
			clientserver.Com_Printf ("Command packet from remote host.  Ignored.\n")
			return
		
		sys_linux.Sys_AppActivate ()
		s = movemsg.MSG_ReadString (netchan.net_message)
		cmdparser.Cbuf_AddText (s)
		cmdparser.Cbuf_AddText ("\n")
		return
	
	# print command from somewhere
	if c == "print":
	
		s = movemsg.MSG_ReadString (netchan.net_message)
		clientserver.Com_Printf ("{}".format(s))
		return
	
	# ping from somewhere
	if c == "ping":
	
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_CLIENT, netchan.net_from, b"ack")
		return
	
	# challenge from the server we are connecting to
	if c == "challenge":
	
		cl_main.cls.challenge = shared_c.atoi(cmdparser.Cmd_Argv(1))
		CL_SendConnectPacket ()
		return
	
	# echo request from server
	if c == "echo":
	
		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_CLIENT, netchan.net_from, "{}".format(cmdparser.Cmd_Argv(1)).encode('ascii') )
		return
	
	clientserver.Com_Printf ("Unknown command.\n")

	

"""
=================
CL_ReadPackets
=================
"""
def CL_ReadPackets ():

	rx, netchan.net_from = net_udp.NET_GetPacket (common_h.netsrc_t.NS_CLIENT, netchan.net_from, netchan.net_message)

	while rx:
		try:
			##Com_Printf ("packet\n");
			#
			# remote command packet
			#

			header = struct.unpack("<l", netchan.net_message.data[:4])[0] # *(int *)net_message.data
			if header == -1:
				CL_ConnectionlessPacket ()
				continue
			

			if cl_main.cls.state == client_h.connstate_t.ca_disconnected or cl_main.cls.state == client_h.connstate_t.ca_connecting:
				continue		# dump it if not connected

			if netchan.net_message.cursize < 8:
			
				clientserver.Com_Printf ("{}: Runt packet\n".format(net_udp.NET_AdrToString(netchan.net_from)))
				continue
			

			#
			# packet from server
			#
			if not net_udp.NET_CompareAdr (netchan.net_from, cl_main.cls.netchan.remote_address):
			
				clientserver.Com_DPrintf ("{}:sequenced packet without connection\n".format(
					net_udp.NET_AdrToString(netchan.net_from)))
				continue
			
			if not netchan.Netchan_Process(cl_main.cls.netchan, netchan.net_message):
				continue		# wasn't accepted for some reason
			cl_parse.CL_ParseServerMessage ()

		finally:
			rx, netchan.net_from = net_udp.NET_GetPacket (common_h.netsrc_t.NS_CLIENT, netchan.net_from, netchan.net_message)

	#
	# check timeout
	#
	if ( cl_main.cls.state.value >= client_h.connstate_t.ca_connected.value
	 and cl_main.cls.realtime - cl_main.cls.netchan.last_received > cl_main.cl_timeout.value*1000 ):
	
		cl_main.cl.timeoutcount += 1
		if cl_main.cl.timeoutcount > 5:	# timeoutcount saves debugger
		
			clientserver.Com_Printf ("\nServer connection timed out.\n")
			CL_Disconnect ()
			return
		
	else:
		cl_main.cl.timeoutcount = 0
	
	"""


//=============================================================================

/*
==============
CL_FixUpGender_f
==============
"""
