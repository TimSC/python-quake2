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
import os
import struct
from qcommon import cvar, common, cmd, files, net_chan, qcommon, cmodel, qfiles
from game import q_shared
from client import console, snd_dma, cl_scrn, client, cl_view, menu, cl_input, keys, cl_cin, cl_parse, cl_fx, cl_tent, cl_pred
from linux import q_shlinux, vid_so, in_linux, net_udp, cd_linux, sys_linux
from server import sv_main

"""
// cl_main.c  -- client main loop

#include "client.h"
"""

adr0, adr1, adr2, adr3, adr4, adr5, adr6, adr7, adr8 = None, None, None, None, None, None, None, None, None

cl_stereo_separation = None #cvar_t *
cl_stereo = None #cvar_t *

cl_add_blend, cl_add_lights, cl_add_particles, cl_add_entities = None, None, None, None
cl_gun, cl_footsteps, cl_noskins, cl_autoskins, cl_predict, cl_maxfps = None, None, None, None, None, None
cl_upspeed, cl_forwardspeed, cl_sidespeed, cl_yawspeed, cl_pitchspeed, cl_anglespeedkey = None, None, None, None, None, None
cl_run, freelook, lookspring, lookstrafe, sensitivity = None, None, None, None, None
m_pitch, m_yaw, m_forward, m_side = None, None, None, None
cl_shownet, cl_showmiss, cl_showclamp, cl_timeout, cl_paused, cl_timedemo = None, None, None, None, None, None
rcon_client_password, rcon_address, cl_lightlevel = None, None, None
info_password, info_spectator, name, skin, rate, msg, hand, fov, gender, gender_auto, cl_vwep = None, None, None, None, None, None, None, None, None, None, None

cls = client.client_static_t()

cl = client.client_state_t()


cl_entities = []
for i in range(q_shared.MAX_EDICTS):
	cl_entities.append(client.centity_t())


cl_parse_entities = [] 
for i in range(client.MAX_PARSE_ENTITIES):
	cl_parse_entities.append(q_shared.entity_state_t())
"""
extern	cvar_t *allow_download;
extern	cvar_t *allow_download_players;
extern	cvar_t *allow_download_models;
extern	cvar_t *allow_download_sounds;
extern	cvar_t *allow_download_maps;

//======================================================================


"""
"""
====================
CL_WriteDemoMessage

Dumps the current net message, prefixed by the length
====================
"""
def CL_WriteDemoMessage ():

	#int		len, swlen;

	# the first eight bytes are just packet sequencing stuff
	length = net_chan.net_message.cursize-8
	cls.demofile.write (struct.pack("<i", length)) # swlen = LittleLong(len); fwrite (&swlen, 4, 1, cls.demofile);
	cls.demofile.write (net_chan.net_message.data[8:8+length])


"""
====================
CL_Stop_f

stop recording a demo
====================
"""
def CL_Stop_f ():

	#int		len;

	if not cls.demorecording:
	
		common.Com_Printf ("Not recording a demo.\n")
		return
	
	# finish up
	length = -1
	cls.demofile.write (struct.pack("<i", length))
	cls.demofile.close ()
	cls.demofile = None
	cls.demorecording = False
	common.Com_Printf ("Stopped demo.\n")

"""
====================
CL_Record_f

record <demoname>

Begins recording a demo from the current position
====================
"""
def CL_Record_f ():

	"""
	char	name[MAX_OSPATH];
	char	buf_data[MAX_MSGLEN];
	sizebuf_t	buf;
	int		i;
	int		len;
	entity_state_t	*ent;
	entity_state_t	nullstate;
	"""
	buf = qcommon.sizebuf_t()

	if cmd.Cmd_Argc() != 2:
	
		common.Com_Printf ("record <demoname>\n")
		return
	
	if cls.demorecording:
	
		common.Com_Printf ("Already recording.\n")
		return
	
	if cls.state != client.connstate_t.ca_active:
	
		common.Com_Printf ("You must be in a level to record.\n")
		return
	
	#
	# open the demo file
	#
	name = "{}/demos/{}.dm2".format(files.FS_Gamedir(), cmd.Cmd_Argv(1))

	common.Com_Printf ("recording to {}.\n".format(name))
	files.FS_CreatePath (name)
	try:
		cls.demofile = open (name, "wb")
	except OSError:
		cls.demofile = None
	if cls.demofile is None:
	
		common.Com_Printf ("ERROR: couldn't open.\n")
		return
	
	cls.demorecording = True

	# don't start saving messages until a non-delta compressed message is received
	cls.demowaiting = True

	#
	# write out messages to hold the startup information
	#
	common.SZ_Init (buf, qcommon.MAX_MSGLEN)

	# send the serverdata
	common.MSG_WriteByte (buf, qcommon.svc_ops_e.svc_serverdata.value)
	common.MSG_WriteLong (buf, qcommon.PROTOCOL_VERSION)
	common.MSG_WriteLong (buf, 0x10000 + cl.servercount)
	common.MSG_WriteByte (buf, 1)	# demos are always attract loops
	common.MSG_WriteString (buf, cl.gamedir.encode('ascii'))
	common.MSG_WriteShort (buf, cl.playernum)

	common.MSG_WriteString (buf, cl.configstrings[q_shared.CS_NAME].encode('ascii'))

	# configstrings
	for i in range(q_shared.MAX_CONFIGSTRINGS):
	
		if cl.configstrings[i]:
		
			if buf.cursize + len (cl.configstrings[i]) + 32 > buf.maxsize:
				# write it out
				cls.demofile.write (struct.pack("<i", buf.cursize)) # len = LittleLong (buf.cursize); fwrite (&len, 4, 1, cls.demofile);
				cls.demofile.write (buf.data[:buf.cursize])
				buf.cursize = 0
			
			common.MSG_WriteByte (buf, qcommon.svc_ops_e.svc_configstring.value)
			common.MSG_WriteShort (buf, i)
			common.MSG_WriteString (buf, cl.configstrings[i].encode('ascii'))
		
	# baselines
	nullstate = q_shared.entity_state_t() # memset (&nullstate, 0, sizeof(nullstate));
	for i in range(q_shared.MAX_EDICTS):
	
		ent = cl_entities[i].baseline
		if not ent.modelindex:
			continue

		if buf.cursize + 64 > buf.maxsize:
			# write it out
			cls.demofile.write (struct.pack("<i", buf.cursize))
			cls.demofile.write (buf.data[:buf.cursize])
			buf.cursize = 0
		
		common.MSG_WriteByte (buf, qcommon.svc_ops_e.svc_spawnbaseline.value)		
		common.MSG_WriteDeltaEntity (nullstate, cl_entities[i].baseline, buf, True, True)
	
	common.MSG_WriteByte (buf, qcommon.svc_ops_e.svc_stufftext.value)
	common.MSG_WriteString (buf, b"precache\n")

	# write it to the demo file

	cls.demofile.write (struct.pack("<i", buf.cursize))
	cls.demofile.write (buf.data[:buf.cursize])

	# the rest of the demo file will be individual frames

"""

//======================================================================

"""
"""
===================
Cmd_ForwardToServer

adds the current command line as a clc_stringcmd to the client message.
things like godmode, noclip, etc, are commands directed to the server,
so when they are typed in at the console, they will need to be forwarded.
===================
"""
def Cmd_ForwardToServer ():

	#char	*cmd;

	cmd_name = cmd.Cmd_Argv(0)
	if cls.state.value <= client.connstate_t.ca_connected.value or cmd_name[:1] == '-' or cmd_name[:1] == '+':
	
		common.Com_Printf ("Unknown command \"{}\"\n".format(cmd_name))
		return
	
	common.MSG_WriteByte (cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd.value)
	common.SZ_Print (cls.netchan.message, cmd_name)
	if cmd.Cmd_Argc() > 1:
	
		common.SZ_Print (cls.netchan.message, " ")
		common.SZ_Print (cls.netchan.message, cmd.Cmd_Args())
	

def CL_Setenv_f():

	argc = cmd.Cmd_Argc()

	if argc > 2:
	
		#char buffer[1000];
		#int i;

		name = cmd.Cmd_Argv(1)
		buffer = ""

		for i in range(2, argc):
		
			buffer += cmd.Cmd_Argv( i )
			buffer += " "
		
		os.environ[name] = buffer # strcpy( buffer, Cmd_Argv(1) ); strcat( buffer, "=" ); ... putenv( buffer );
	
	elif argc == 2:
	
		env = os.environ.get( cmd.Cmd_Argv(1) ) # getenv returns NULL when unset

		if env is not None:
		
			common.Com_Printf( "{}={}\n".format(cmd.Cmd_Argv(1), env) )
		
		else:
		
			common.Com_Printf( "{} undefined\n".format(cmd.Cmd_Argv(1)) )
		

"""
==================
CL_ForwardToServer_f
==================
"""
def CL_ForwardToServer_f ():

	if cls.state != client.connstate_t.ca_connected and cls.state != client.connstate_t.ca_active:
	
		common.Com_Printf ("Can't \"{}\", not connected\n".format(cmd.Cmd_Argv(0)))
		return
	
	# don't forward the first argument
	if cmd.Cmd_Argc() > 1:
	
		common.MSG_WriteByte (cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd.value)
		common.SZ_Print (cls.netchan.message, cmd.Cmd_Args())
	


"""
/*
==================
CL_Pause_f
==================
"""
def CL_Pause_f ():

	# never pause in multiplayer
	if cvar.Cvar_VariableValue ("maxclients") > 1 or not common.Com_ServerState ():
	
		cvar.Cvar_SetValue ("paused", 0)
		return
	
	cvar.Cvar_SetValue ("paused", cl_paused.value == 0.0)


"""
==================
CL_Quit_f
==================
"""
def CL_Quit_f ():

	CL_Disconnect ()
	common.Com_Quit ()


"""
================
CL_Drop

Called after an q_shared.ERR_DROP was thrown
================
"""
def CL_Drop ():
	if cls.state == client.connstate_t.ca_uninitialized:
		return
	if cls.state == client.connstate_t.ca_disconnected:
		return

	CL_Disconnect()

	# drop loading plaque unless this is the initial game start
	if cls.disable_servercount != -1:
		cl_scrn.SCR_EndLoadingPlaque()


# =======================
# CL_SendConnectPacket
#
# We have gotten a challenge from the server, so try and
# connect.
# ======================
def CL_SendConnectPacket ():

	#netadr_t	adr;
	#int		port;

	adr = net_udp.NET_StringToAdr (cls.servername)
	if adr is None:
	
		common.Com_Printf ("Bad server address\n")
		cls.connect_time = 0
		return
	
	if not adr.port:
		adr.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)

	port = int(cvar.Cvar_VariableValue ("qport"))
	cvar.userinfo_modified = False

	net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, "connect {:d} {:d} {:d} \"{}\"\n".format(
		qcommon.PROTOCOL_VERSION, port, cls.challenge, cvar.Cvar_Userinfo()).encode('ascii') )


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
	if cls.state == client.connstate_t.ca_disconnected and common.Com_ServerState():
	
		cls.state = client.connstate_t.ca_connecting
		cls.servername = "localhost"
		# we don't need a challenge on the localhost
		CL_SendConnectPacket ()
		return
		##cls.connect_time = -99999;	// CL_CheckForResend() will fire immediately

	# resend if we haven't gotten a reply yet
	if cls.state != client.connstate_t.ca_connecting:
		return

	if cls.realtime - cls.connect_time < 3000:
		return

	adr = net_udp.NET_StringToAdr(cls.servername)
	if adr is None:
		common.Com_Printf("Bad server address\n")
		cls.state = client.connstate_t.ca_disconnected
		return

	if not adr.port:
		adr.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)

	cls.connect_time = cls.realtime

	common.Com_Printf("Connecting to {}...\n".format(cls.servername))

	net_chan.Netchan_OutOfBandPrint(qcommon.netsrc_t.NS_CLIENT, adr, b"getchallenge\n")



"""
================
CL_Connect_f

================
"""
def CL_Connect_f ():

	#char	*server;

	if cmd.Cmd_Argc() != 2:
	
		common.Com_Printf ("usage: connect <server>\n")
		return	
	
	if common.Com_ServerState ():
		# if running a local server, kill it and reissue
		sv_main.SV_Shutdown ("Server quit\n", False)
	
	else:
	
		CL_Disconnect ()
	
	server = cmd.Cmd_Argv (1)

	net_udp.NET_Config (True)		# allow remote

	CL_Disconnect ()

	cls.state = client.connstate_t.ca_connecting
	cls.servername = server[:q_shared.MAX_OSPATH-1] # strncpy (cls.servername, server, sizeof(cls.servername)-1);
	cls.connect_time = -99999	# CL_CheckForResend() will fire immediately


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

	if rcon_client_password.string is None:
	
		common.Com_Printf ("You must set 'rcon_password' before\n"
					"issuing an rcon command.\n")
		return
	
	message = bytearray(b"\xff\xff\xff\xff") # message[0..3] = (char)255; message[4] = 0;

	net_udp.NET_Config (True)		# allow remote

	message += b"rcon "

	message += rcon_client_password.string.encode('ascii')
	message += b" "

	for i in range(1, cmd.Cmd_Argc()):
	
		message += cmd.Cmd_Argv(i).encode('ascii')
		message += b" "
	
	if cls.state.value >= client.connstate_t.ca_connected.value:
		to = cls.netchan.remote_address
	else:
	
		if not len(rcon_address.string):
		
			common.Com_Printf ("You must either be connected,\n"
						"or set the 'rcon_address' cvar\n"
						"to issue rcon commands\n")

			return
		
		to = net_udp.NET_StringToAdr (rcon_address.string)
		if to is None: # C ignores the failure and sends to an empty address
			to = qcommon.netadr_t()
		if to.port == 0:
			to.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)
	
	message += b"\0"
	net_udp.NET_SendPacket (qcommon.netsrc_t.NS_CLIENT, bytes(message), to) # strlen(message)+1



# =====================
# CL_ClearState
# =====================
def CL_ClearState ():

	snd_dma.S_StopAllSounds ()

	cl_fx.CL_ClearEffects ()
	cl_tent.CL_ClearTEnts ()

# wipe the entire cl structure
	cl.reset()
	for ent in cl_entities:
		ent.clear()

	common.SZ_Clear (cls.netchan.message)



"""
=====================
CL_Disconnect

Goes from a connected state to full screen console state
Sends a disconnect message to the server
This is also called on Com_Error, so it shouldn't cause any errors
=====================
"""
def CL_Disconnect ():

	print ("CL_Disconnect")

	"""
	byte	final[32];
	"""

	if cls.state == client.connstate_t.ca_disconnected:
		return

	if cl_timedemo is not None and int(cl_timedemo.value):
	
		#int	time;
		
		time = q_shlinux.Sys_Milliseconds () - cl.timedemo_start
		if time > 0:
			common.Com_Printf ("{} frames, {:3.1f} seconds: {:3.1f} fps\n".format(cl.timedemo_frames,
			time/1000.0, cl.timedemo_frames*1000.0 / time))
	
	q_shared.VectorClear (cl.refdef.blend)
	vid_so.re.CinematicSetPalette(None)

	menu.M_ForceMenuOff ()

	cls.connect_time = 0

	cl_cin.SCR_StopCinematic ()

	if cls.demorecording:
		CL_Stop_f ()

	# send a disconnect message to the server
	final = bytearray()
	final += struct.pack("B", qcommon.clc_ops_e.clc_stringcmd.value)
	final += b"disconnect"
	net_chan.Netchan_Transmit (cls.netchan, final)
	net_chan.Netchan_Transmit (cls.netchan, final)
	net_chan.Netchan_Transmit (cls.netchan, final)

	CL_ClearState ()

	# stop download
	if cls.download is not None:
		cls.download.close()
		cls.download = None
	
	cls.state = client.connstate_t.ca_disconnected


def CL_Disconnect_f ():

	common.Com_Error (q_shared.ERR_DROP, "Disconnected from server");



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

	if cmd.Cmd_Argc() != 3:
	
		common.Com_Printf ("packet <destination> <contents>\n")
		return
	
	net_udp.NET_Config (True)		# allow remote

	adr = net_udp.NET_StringToAdr (cmd.Cmd_Argv(1))
	if adr is None:
	
		common.Com_Printf ("Bad address\n")
		return
	
	if not adr.port:
		adr.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)

	in_str = cmd.Cmd_Argv(2)
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

	net_udp.NET_SendPacket (qcommon.netsrc_t.NS_CLIENT, bytes(send), adr) # out-send, excludes the terminator



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
	if cls.download is not None:
		return

	cl_scrn.SCR_BeginLoadingPlaque ()
	cls.state = client.connstate_t.ca_connected # not active anymore, but not disconnected
	common.Com_Printf ("\nChanging map...\n")

"""
=================
CL_Reconnect_f

The server is changing levels
=================
"""
def CL_Reconnect_f ():

	#ZOID
	#if we are downloading, we don't change!  This so we don't suddenly stop downloading a map
	if cls.download is not None:
		return

	snd_dma.S_StopAllSounds ()
	if cls.state == client.connstate_t.ca_connected:
		common.Com_Printf ("reconnecting...\n")
		cls.state = client.connstate_t.ca_connected
		common.MSG_WriteChar (cls.netchan.message, struct.pack("B", qcommon.clc_ops_e.clc_stringcmd.value))
		common.MSG_WriteString (cls.netchan.message, b"new")
		return

	if cls.servername:
		if cls.state.value >= client.connstate_t.ca_connected.value:
			CL_Disconnect()
			cls.connect_time = cls.realtime - 1500
		else:
			cls.connect_time = -99999 # fire immediately

		cls.state = client.connstate_t.ca_connecting
		common.Com_Printf ("reconnecting...\n")


"""
=================
CL_ParseStatusMessage

Handle a reply from a ping
=================
"""
def CL_ParseStatusMessage ():

	#char	*s;

	s = common.MSG_ReadString(net_chan.net_message)

	common.Com_Printf ("{}\n".format(s))
	menu.M_AddToServerList (net_chan.net_from, s)


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
	adr = qcommon.netadr_t()

	net_udp.NET_Config (True)		# allow remote

	# send a broadcast packet
	common.Com_Printf ("pinging broadcast...\n")

	noudp = cvar.Cvar_Get ("noudp", "0", q_shared.CVAR_NOSET)
	if not noudp.value:
	
		adr.type = qcommon.netadrtype_t.NA_BROADCAST
		adr.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, "info {}".format(qcommon.PROTOCOL_VERSION).encode("ascii"))
	
	noipx = cvar.Cvar_Get ("noipx", "0", q_shared.CVAR_NOSET)
	if not noipx.value:
	
		adr.type = qcommon.netadrtype_t.NA_BROADCAST_IPX
		adr.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, "info {}".format(qcommon.PROTOCOL_VERSION).encode("ascii"))
	
	# send a packet to each address book entry
	for i in range(16):
	
		name = "adr{}".format(i)
		adrstring = cvar.Cvar_VariableString (name)
		if not adrstring:
			continue

		common.Com_Printf ("pinging {}...\n".format(adrstring))
		adr = net_udp.NET_StringToAdr (adrstring)
		if adr is None:
		
			common.Com_Printf ("Bad address: {}\n".format(adrstring))
			continue
		
		if not adr.port:
			adr.port = q_shared.BigShort (struct.pack("=H", qcommon.PORT_SERVER)) # BigShort (PORT_SERVER)
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, "info {}".format(qcommon.PROTOCOL_VERSION).encode("ascii"))
	

"""


/*
=================
CL_Skins_f

Load or download any custom player skins and models
=================
"""
def CL_Skins_f ():

	#int		i;

	for i in range(q_shared.MAX_CLIENTS):
	
		if not cl.configstrings[q_shared.CS_PLAYERSKINS+i]:
			continue
		common.Com_Printf ("client {}: {}\n".format(i, cl.configstrings[q_shared.CS_PLAYERSKINS+i])) 
		cl_scrn.SCR_UpdateScreen ()
		sys_linux.Sys_SendKeyEvents ()	# pump message loop
		cl_parse.CL_ParseClientinfo (i)
	
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
	
	common.MSG_BeginReading (net_chan.net_message)
	common.MSG_ReadLong (net_chan.net_message)	# skip the -1

	s = common.MSG_ReadStringLine (net_chan.net_message)

	cmd.Cmd_TokenizeString (s, False)

	c = cmd.Cmd_Argv(0)

	common.Com_Printf ("{}: {}\n".format(net_udp.NET_AdrToString (net_chan.net_from), c))

	# server connection
	if c == "client_connect":
	
		if cls.state == client.connstate_t.ca_connected:
		
			common.Com_Printf ("Dup connect received.  Ignored.\n")
			return
		
		net_chan.Netchan_Setup (qcommon.netsrc_t.NS_CLIENT, cls.netchan, net_chan.net_from, cls.quakePort)
		common.MSG_WriteChar (cls.netchan.message, struct.pack("B", qcommon.clc_ops_e.clc_stringcmd.value))
		common.MSG_WriteString (cls.netchan.message, b"new")	
		cls.state = client.connstate_t.ca_connected
		return
	
	# server responding to a status broadcast
	if c == "info":
	
		CL_ParseStatusMessage ()
		return
	
	# remote command from gui front end
	if c == "cmd":
	
		if not net_udp.NET_IsLocalAddress(net_chan.net_from):
		
			common.Com_Printf ("Command packet from remote host.  Ignored.\n")
			return
		
		sys_linux.Sys_AppActivate ()
		s = common.MSG_ReadString (net_chan.net_message)
		cmd.Cbuf_AddText (s)
		cmd.Cbuf_AddText ("\n")
		return
	
	# print command from somewhere
	if c == "print":
	
		s = common.MSG_ReadString (net_chan.net_message)
		common.Com_Printf ("{}".format(s))
		return
	
	# ping from somewhere
	if c == "ping":
	
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, b"ack")
		return
	
	# challenge from the server we are connecting to
	if c == "challenge":
	
		cls.challenge = q_shared.atoi(cmd.Cmd_Argv(1))
		CL_SendConnectPacket ()
		return
	
	# echo request from server
	if c == "echo":
	
		net_chan.Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, "{}".format(cmd.Cmd_Argv(1)).encode('ascii') )
		return
	
	common.Com_Printf ("Unknown command.\n")


"""
=================
CL_DumpPackets

A vain attempt to help bad TCP stacks that cause problems
when they overflow
=================
*/
"""
def CL_DumpPackets ():

	while True:
		rx, net_chan.net_from = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, net_chan.net_message)
		if not rx:
			break
	
		common.Com_Printf ("dumnping a packet\n")
	

"""
=================
CL_ReadPackets
=================
"""
def CL_ReadPackets ():

	rx, net_chan.net_from = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, net_chan.net_message)

	while rx:
		try:
			##Com_Printf ("packet\n");
			#
			# remote command packet
			#

			header = struct.unpack("<l", net_chan.net_message.data[:4])[0] # *(int *)net_message.data
			if header == -1:
				CL_ConnectionlessPacket ()
				continue
			

			if cls.state == client.connstate_t.ca_disconnected or cls.state == client.connstate_t.ca_connecting:
				continue		# dump it if not connected

			if net_chan.net_message.cursize < 8:
			
				common.Com_Printf ("{}: Runt packet\n".format(net_udp.NET_AdrToString(net_chan.net_from)))
				continue
			

			#
			# packet from server
			#
			if not net_udp.NET_CompareAdr (net_chan.net_from, cls.netchan.remote_address):
			
				common.Com_DPrintf ("{}:sequenced packet without connection\n".format(
					net_udp.NET_AdrToString(net_chan.net_from)))
				continue
			
			if not net_chan.Netchan_Process(cls.netchan, net_chan.net_message):
				continue		# wasn't accepted for some reason
			cl_parse.CL_ParseServerMessage ()

		finally:
			rx, net_chan.net_from = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, net_chan.net_message)

	#
	# check timeout
	#
	if ( cls.state.value >= client.connstate_t.ca_connected.value
	 and cls.realtime - cls.netchan.last_received > cl_timeout.value*1000 ):
	
		cl.timeoutcount += 1
		if cl.timeoutcount > 5:	# timeoutcount saves debugger
		
			common.Com_Printf ("\nServer connection timed out.\n")
			CL_Disconnect ()
			return
		
	else:
		cl.timeoutcount = 0
	
	"""



//=============================================================================

/*
==============
CL_FixUpGender_f
==============
"""
def CL_FixUpGender():

	if not gender_auto.value:
		return

	if gender.modified:
		# was set directly, don't override the user
		gender.modified = False
		return

	skin_name = skin.string
	if "/" in skin_name:
		skin_dir = skin_name.split("/", 1)[0]
	elif "\\" in skin_name:
		skin_dir = skin_name.split("\\", 1)[0]
	else:
		skin_dir = skin_name

	if q_shared.Q_stricmp(skin_dir, "male") == 0 or q_shared.Q_stricmp(skin_dir, "cyborg") == 0:
		cvar.Cvar_Set("gender", "male")
	elif q_shared.Q_stricmp(skin_dir, "female") == 0 or q_shared.Q_stricmp(skin_dir, "crackhor") == 0:
		cvar.Cvar_Set("gender", "female")
	else:
		cvar.Cvar_Set("gender", "none")
	gender.modified = False


# ==============
# CL_Userinfo_f
# ==============
def CL_Userinfo_f ():

	common.Com_Printf ("User info settings:\n")
	Info_Print (Cvar_Userinfo())


"""
=================
CL_Snd_Restart_f

Restart the sound subsystem so it can pick up
new parameters and flush all sounds
=================
"""
def CL_Snd_Restart_f ():

	snd_dma.S_Shutdown()
	snd_dma.S_Init()
	cl_parse.CL_RegisterSounds ()


precache_check: int = 0 # for autodownload of precache items
precache_spawncount: int = 0
precache_tex: int = 0
precache_model_skin: int = 0
precache_model = None #byte *, used for skin checking in alias models

PLAYER_MULT = 5

# ENV_CNT is map load, ENV_CNT+1 is first env map
ENV_CNT = (q_shared.CS_PLAYERSKINS + q_shared.MAX_CLIENTS * PLAYER_MULT)
TEXTURE_CNT = (ENV_CNT+13)

env_suf = ["rt", "bk", "lf", "ft", "up", "dn"] #static const char *[6]

def CL_RequestNextDownload ():

	global precache_check, precache_model, precache_model_skin, precache_tex

	#unsigned	map_checksum;		// for detecting cheater maps
	#char fn[MAX_OSPATH];
	#dmdl_t *pheader;

	if cls.state != client.connstate_t.ca_connected:
		return

	if not sv_main.allow_download.value and precache_check < ENV_CNT:
		precache_check = ENV_CNT

#ZOID
	if precache_check == q_shared.CS_MODELS: # confirm map
		precache_check = q_shared.CS_MODELS+2 # 0 isn't used
		if sv_main.allow_download_maps.value:
			if not cl_parse.CL_CheckOrDownloadFile(cl.configstrings[q_shared.CS_MODELS+1]):
				return # started a download
	
	if precache_check >= q_shared.CS_MODELS and precache_check < q_shared.CS_MODELS+q_shared.MAX_MODELS:
		if sv_main.allow_download_models.value:
			while (precache_check < q_shared.CS_MODELS+q_shared.MAX_MODELS and
				cl.configstrings[precache_check]):
				if (cl.configstrings[precache_check][0] == '*' or
					cl.configstrings[precache_check][0] == '#'):
					precache_check += 1
					continue
				
				if precache_model_skin == 0:
					if not cl_parse.CL_CheckOrDownloadFile(cl.configstrings[precache_check]):
						precache_model_skin = 1
						return # started a download
					
					precache_model_skin = 1
				
				# checking for skins in the model
				if precache_model is None:

					length, precache_model = files.FS_LoadFile (cl.configstrings[precache_check])
					if precache_model is None:
						precache_model_skin = 0
						precache_check += 1
						continue # couldn't load it
					
					if q_shared.LittleLong(precache_model[:4]) != qfiles.IDALIASHEADER:
						# not an alias model
						files.FS_FreeFile(precache_model)
						precache_model = None
						precache_model_skin = 0
						precache_check += 1
						continue
					
					pheader = qfiles.dmdl_t() # (dmdl_t *)precache_model
					pheader.load(precache_model)
					if pheader.version != qfiles.ALIAS_VERSION: # LittleLong (pheader->version)
						precache_check += 1
						precache_model_skin = 0
						continue # couldn't load it
					
				pheader = qfiles.dmdl_t() # (dmdl_t *)precache_model
				pheader.load(precache_model)

				while precache_model_skin - 1 < pheader.num_skins: # LittleLong(pheader->num_skins)
					skin_ofs = pheader.ofs_skins + (precache_model_skin - 1)*qfiles.MAX_SKINNAME # (char *)precache_model + LittleLong(pheader->ofs_skins) + (precache_model_skin - 1)*MAX_SKINNAME
					skinname = bytes(precache_model[skin_ofs:skin_ofs+qfiles.MAX_SKINNAME]).split(b"\0")[0].decode('latin-1')
					if not cl_parse.CL_CheckOrDownloadFile(skinname):
						precache_model_skin += 1
						return # started a download
					
					precache_model_skin += 1
				
				if precache_model is not None: 
					files.FS_FreeFile(precache_model)
					precache_model = None
				
				precache_model_skin = 0
				precache_check += 1
			
		precache_check = q_shared.CS_SOUNDS
	
	if precache_check >= q_shared.CS_SOUNDS and precache_check < q_shared.CS_SOUNDS+q_shared.MAX_SOUNDS: 
		if sv_main.allow_download_sounds.value:
			if precache_check == q_shared.CS_SOUNDS:
				precache_check += 1 # zero is blank
			while (precache_check < q_shared.CS_SOUNDS+q_shared.MAX_SOUNDS and
				cl.configstrings[precache_check]):
				if cl.configstrings[precache_check][0] == '*':
					precache_check += 1
					continue
				
				fn = "sound/{}".format(cl.configstrings[precache_check])
				precache_check += 1
				if not cl_parse.CL_CheckOrDownloadFile(fn):
					return # started a download
			
		precache_check = q_shared.CS_IMAGES
	
	if precache_check >= q_shared.CS_IMAGES and precache_check < q_shared.CS_IMAGES+q_shared.MAX_IMAGES:
		if precache_check == q_shared.CS_IMAGES:
			precache_check += 1 # zero is blank
		while (precache_check < q_shared.CS_IMAGES+q_shared.MAX_IMAGES and
			cl.configstrings[precache_check]):
			fn = "pics/{}.pcx".format(cl.configstrings[precache_check])
			precache_check += 1
			if not cl_parse.CL_CheckOrDownloadFile(fn):
				return # started a download
		
		precache_check = q_shared.CS_PLAYERSKINS
	
	# skins are special, since a player has three things to download:
	# model, weapon model and skin
	# so precache_check is now *3
	if precache_check >= q_shared.CS_PLAYERSKINS and precache_check < q_shared.CS_PLAYERSKINS + q_shared.MAX_CLIENTS * PLAYER_MULT:
		if sv_main.allow_download_players.value:
			while precache_check < q_shared.CS_PLAYERSKINS + q_shared.MAX_CLIENTS * PLAYER_MULT:
				#int i, n;
				#char model[MAX_QPATH], skin[MAX_QPATH], *p;

				i = (precache_check - q_shared.CS_PLAYERSKINS)//PLAYER_MULT
				n = (precache_check - q_shared.CS_PLAYERSKINS)%PLAYER_MULT

				if not cl.configstrings[q_shared.CS_PLAYERSKINS+i]:
					precache_check = q_shared.CS_PLAYERSKINS + (i + 1) * PLAYER_MULT
					continue
				
				p = cl.configstrings[q_shared.CS_PLAYERSKINS+i].find('\\')
				if p != -1:
					p += 1
				else:
					p = 0
				model = cl.configstrings[q_shared.CS_PLAYERSKINS+i][p:]
				p = model.find('/')
				if p == -1:
					p = model.find('\\')
				if p != -1:
					skin = model[p+1:]
					model = model[:p] # *p++ = 0;
				else:
					skin = ""

				# switch (n) with each case falling through to the next
				if n == 0: # model
					fn = "players/{}/tris.md2".format(model)
					if not cl_parse.CL_CheckOrDownloadFile(fn):
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 1
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 1: # weapon model
					fn = "players/{}/weapon.md2".format(model)
					if not cl_parse.CL_CheckOrDownloadFile(fn):
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 2
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 2: # weapon skin
					fn = "players/{}/weapon.pcx".format(model)
					if not cl_parse.CL_CheckOrDownloadFile(fn):
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 3
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 3: # skin
					fn = "players/{}/{}.pcx".format(model, skin)
					if not cl_parse.CL_CheckOrDownloadFile(fn):
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 4
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 4: # skin_i
					fn = "players/{}/{}_i.pcx".format(model, skin)
					if not cl_parse.CL_CheckOrDownloadFile(fn):
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 5
						return # started a download
					
					# move on to next model
					precache_check = q_shared.CS_PLAYERSKINS + (i + 1) * PLAYER_MULT
				
		# precache phase completed
		precache_check = ENV_CNT
	
	if precache_check == ENV_CNT:
		precache_check = ENV_CNT + 1

		_, map_checksum = cmodel.CM_LoadMap (cl.configstrings[q_shared.CS_MODELS+1], True)

		if map_checksum != (q_shared.atoi(cl.configstrings[q_shared.CS_MAPCHECKSUM]) & 0xffffffff): # atoi's int is converted to unsigned for the compare
			common.Com_Error (q_shared.ERR_DROP, "Local map version differs from server: {} != '{}'\n".format(
				map_checksum, cl.configstrings[q_shared.CS_MAPCHECKSUM]))
			return
		
	if precache_check > ENV_CNT and precache_check < TEXTURE_CNT:
		if sv_main.allow_download.value and sv_main.allow_download_maps.value:
			while precache_check < TEXTURE_CNT:
				n = precache_check - ENV_CNT - 1
				precache_check += 1

				if n & 1:
					fn = "env/{}{}.pcx".format( 
						cl.configstrings[q_shared.CS_SKY], env_suf[n//2])
				else:
					fn = "env/{}{}.tga".format( 
						cl.configstrings[q_shared.CS_SKY], env_suf[n//2])
				if not cl_parse.CL_CheckOrDownloadFile(fn):
					return # started a download
			
		precache_check = TEXTURE_CNT
	
	if precache_check == TEXTURE_CNT:
		precache_check = TEXTURE_CNT+1
		precache_tex = 0
	
	# confirm existance of textures, download any that don't exist
	if precache_check == TEXTURE_CNT+1:
		# from qcommon/cmodel.c
		#extern int			numtexinfo;
		#extern mapsurface_t	map_surfaces[];

		if sv_main.allow_download.value and sv_main.allow_download_maps.value:
			while precache_tex < cmodel.numtexinfo:
				#char fn[MAX_OSPATH];

				fn = "textures/{}.wal".format(cmodel.map_surfaces[precache_tex].rname)
				precache_tex += 1
				if not cl_parse.CL_CheckOrDownloadFile(fn):
					return # started a download
			
		precache_check = TEXTURE_CNT+999
	
#ZOID
	cl_parse.CL_RegisterSounds ()
	cl_view.CL_PrepRefresh ()

	common.MSG_WriteByte (cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd.value)
	common.MSG_WriteString (cls.netchan.message, "begin {}\n".format(precache_spawncount).encode('ascii') )

"""

/*
=================
CL_Precache_f

The server will send this command right
before allowing the client into the server
=================
"""
def CL_Precache_f ():

	global precache_check, precache_spawncount, precache_tex, precache_model_skin, precache_model
	
	# Yet another hack to let old demos work
	# the old precache sequence
	if cmd.Cmd_Argc() < 2:
		#unsigned	map_checksum;		// for detecting cheater maps

		map_checksum = cmodel.CM_LoadMap (cl.configstrings[q_shared.CS_MODELS+1], True)
		cl_parse.CL_RegisterSounds ()
		cl_view.CL_PrepRefresh ()
		return
	

	precache_check = q_shared.CS_MODELS
	precache_spawncount = int(cmd.Cmd_Argv(1))
	precache_model = None
	precache_model_skin = 0

	CL_RequestNextDownload()



"""
=================
CL_InitLocal
=================
"""
def CL_InitLocal ():

	global adr0, adr1, adr2, adr3, adr4, adr5, adr6, adr7, adr8
	global cl_stereo_separation, cl_stereo, cls
	global cl_add_blend, cl_add_lights, cl_add_particles, cl_add_entities
	global cl_gun, cl_footsteps, cl_noskins, cl_autoskins, cl_predict, cl_maxfps
	global cl_upspeed, cl_forwardspeed, cl_sidespeed, cl_yawspeed, cl_pitchspeed, cl_anglespeedkey
	global cl_run, freelook, lookspring, lookstrafe, sensitivity
	global m_pitch, m_yaw, m_forward, m_side
	global cl_shownet, cl_showmiss, cl_showclamp, cl_timeout, cl_paused, cl_timedemo
	global rcon_client_password, rcon_address, cl_lightlevel
	global info_password, info_spectator, name, skin, rate, msg, hand, fov, gender, gender_auto, cl_vwep

	cls.state = client.connstate_t.ca_disconnected
	cls.realtime = q_shlinux.Sys_Milliseconds ()

	cl_input.CL_InitInput ()

	adr0 = cvar.Cvar_Get( "adr0", "", q_shared.CVAR_ARCHIVE )
	adr1 = cvar.Cvar_Get( "adr1", "", q_shared.CVAR_ARCHIVE )
	adr2 = cvar.Cvar_Get( "adr2", "", q_shared.CVAR_ARCHIVE )
	adr3 = cvar.Cvar_Get( "adr3", "", q_shared.CVAR_ARCHIVE )
	adr4 = cvar.Cvar_Get( "adr4", "", q_shared.CVAR_ARCHIVE )
	adr5 = cvar.Cvar_Get( "adr5", "", q_shared.CVAR_ARCHIVE )
	adr6 = cvar.Cvar_Get( "adr6", "", q_shared.CVAR_ARCHIVE )
	adr7 = cvar.Cvar_Get( "adr7", "", q_shared.CVAR_ARCHIVE )
	adr8 = cvar.Cvar_Get( "adr8", "", q_shared.CVAR_ARCHIVE )

	#
	# register our variables
	#
	cl_stereo_separation = cvar.Cvar_Get( "cl_stereo_separation", "0.4", q_shared.CVAR_ARCHIVE )
	cl_stereo = cvar.Cvar_Get( "cl_stereo", "0", 0 )

	cl_add_blend = cvar.Cvar_Get ("cl_blend", "1", 0)
	cl_add_lights = cvar.Cvar_Get ("cl_lights", "1", 0)
	cl_add_particles = cvar.Cvar_Get ("cl_particles", "1", 0)
	cl_add_entities = cvar.Cvar_Get ("cl_entities", "1", 0)
	cl_gun = cvar.Cvar_Get ("cl_gun", "1", 0)
	cl_footsteps = cvar.Cvar_Get ("cl_footsteps", "1", 0)
	cl_noskins = cvar.Cvar_Get ("cl_noskins", "0", 0)
	cl_autoskins = cvar.Cvar_Get ("cl_autoskins", "0", 0)
	cl_predict = cvar.Cvar_Get ("cl_predict", "1", 0)
	## cl_minfps = cvar.Cvar_Get ("cl_minfps", "5", 0)
	cl_maxfps = cvar.Cvar_Get ("cl_maxfps", "90", 0)

	cl_upspeed = cvar.Cvar_Get ("cl_upspeed", "200", 0)
	cl_forwardspeed = cvar.Cvar_Get ("cl_forwardspeed", "200", 0)
	cl_sidespeed = cvar.Cvar_Get ("cl_sidespeed", "200", 0)
	cl_yawspeed = cvar.Cvar_Get ("cl_yawspeed", "140", 0)
	cl_pitchspeed = cvar.Cvar_Get ("cl_pitchspeed", "150", 0)
	cl_anglespeedkey = cvar.Cvar_Get ("cl_anglespeedkey", "1.5", 0)

	cl_run = cvar.Cvar_Get ("cl_run", "0", q_shared.CVAR_ARCHIVE)
	freelook = cvar.Cvar_Get( "freelook", "0", q_shared.CVAR_ARCHIVE )
	lookspring = cvar.Cvar_Get ("lookspring", "0", q_shared.CVAR_ARCHIVE)
	lookstrafe = cvar.Cvar_Get ("lookstrafe", "0", q_shared.CVAR_ARCHIVE)
	sensitivity = cvar.Cvar_Get ("sensitivity", "3", q_shared.CVAR_ARCHIVE)
	
	m_pitch = cvar.Cvar_Get ("m_pitch", "0.022", q_shared.CVAR_ARCHIVE)
	m_yaw = cvar.Cvar_Get ("m_yaw", "0.022", 0)
	m_forward = cvar.Cvar_Get ("m_forward", "1", 0)
	m_side = cvar.Cvar_Get ("m_side", "1", 0)

	cl_shownet = cvar.Cvar_Get ("cl_shownet", "0", 0)
	cl_showmiss = cvar.Cvar_Get ("cl_showmiss", "0", 0)
	cl_showclamp = cvar.Cvar_Get ("showclamp", "0", 0)
	cl_timeout = cvar.Cvar_Get ("cl_timeout", "120", 0)
	cl_paused = cvar.Cvar_Get ("paused", "0", 0)
	cl_timedemo = cvar.Cvar_Get ("timedemo", "0", 0)

	rcon_client_password = cvar.Cvar_Get ("rcon_password", "", 0)
	rcon_address = cvar.Cvar_Get ("rcon_address", "", 0)

	cl_lightlevel = cvar.Cvar_Get ("r_lightlevel", "0", 0)

	#
	# userinfo
	#
	info_password = cvar.Cvar_Get ("password", "", q_shared.CVAR_USERINFO)
	info_spectator = cvar.Cvar_Get ("spectator", "0", q_shared.CVAR_USERINFO)
	name = cvar.Cvar_Get ("name", "unnamed", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE)
	skin = cvar.Cvar_Get ("skin", "male/grunt", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE)
	rate = cvar.Cvar_Get ("rate", "25000", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE);	# FIXME
	msg = cvar.Cvar_Get ("msg", "1", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE)
	hand = cvar.Cvar_Get ("hand", "0", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE)
	fov = cvar.Cvar_Get ("fov", "90", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE)
	gender = cvar.Cvar_Get ("gender", "male", q_shared.CVAR_USERINFO | q_shared.CVAR_ARCHIVE)
	gender_auto = cvar.Cvar_Get ("gender_auto", "1", q_shared.CVAR_ARCHIVE)
	gender.modified = False # clear this so we know when user sets it manually

	cl_vwep = cvar.Cvar_Get ("cl_vwep", "1", q_shared.CVAR_ARCHIVE)

	"""
	//
	// register our commands
	//
	"""
	cmd.Cmd_AddCommand ("cmd", CL_ForwardToServer_f)
	cmd.Cmd_AddCommand ("pause", CL_Pause_f)
	cmd.Cmd_AddCommand ("pingservers", CL_PingServers_f)
	cmd.Cmd_AddCommand ("skins", CL_Skins_f)
	cmd.Cmd_AddCommand ("userinfo", CL_Userinfo_f);
	cmd.Cmd_AddCommand ("snd_restart", CL_Snd_Restart_f);

	cmd.Cmd_AddCommand ("changing", CL_Changing_f)
	cmd.Cmd_AddCommand ("disconnect", CL_Disconnect_f)
	cmd.Cmd_AddCommand ("record", CL_Record_f)
	cmd.Cmd_AddCommand ("stop", CL_Stop_f)
	cmd.Cmd_AddCommand ("quit", CL_Quit_f)
	
	cmd.Cmd_AddCommand ("connect", CL_Connect_f)
	cmd.Cmd_AddCommand ("reconnect", CL_Reconnect_f)

	cmd.Cmd_AddCommand ("rcon", CL_Rcon_f)

 	## Cmd_AddCommand ("packet", CL_Packet_f); # this is dangerous to leave in

	cmd.Cmd_AddCommand ("setenv", CL_Setenv_f )

	cmd.Cmd_AddCommand ("precache", CL_Precache_f)

	cmd.Cmd_AddCommand ("download", cl_parse.CL_Download_f)
	#
	# forward to server commands
	#
	# the only thing this does is allow command completion
	# to work -- all unknown commands are automatically
	# forwarded to the server
	cmd.Cmd_AddCommand ("wave", None)
	cmd.Cmd_AddCommand ("inven", None)
	cmd.Cmd_AddCommand ("kill", None)
	cmd.Cmd_AddCommand ("use", None)
	cmd.Cmd_AddCommand ("drop", None)
	cmd.Cmd_AddCommand ("say", None)
	cmd.Cmd_AddCommand ("say_team", None)
	cmd.Cmd_AddCommand ("info", None)
	cmd.Cmd_AddCommand ("prog", None)
	cmd.Cmd_AddCommand ("give", None)
	cmd.Cmd_AddCommand ("god", None)
	cmd.Cmd_AddCommand ("notarget", None)
	cmd.Cmd_AddCommand ("noclip", None)
	cmd.Cmd_AddCommand ("invuse", None)
	cmd.Cmd_AddCommand ("invprev", None)
	cmd.Cmd_AddCommand ("invnext", None)
	cmd.Cmd_AddCommand ("invdrop", None)
	cmd.Cmd_AddCommand ("weapnext", None)
	cmd.Cmd_AddCommand ("weapprev", None)


"""
===============
CL_WriteConfiguration

Writes key bindings and archived cvars to config.cfg
===============
"""
def CL_WriteConfiguration ():

	#FILE	*f;
	#char	path[MAX_QPATH];

	if cls.state == client.connstate_t.ca_uninitialized:
		return

	path = os.path.join(files.FS_Gamedir(), "config.cfg")

	try:
		f = open (path, "w")
	except:
		common.Com_Printf ("Couldn't write config.cfg.\n")
		return
	
	f.write("// generated by quake, do not modify\n")
	keys.Key_WriteBindings (f)
	f.close()

	cvar.Cvar_WriteVariables (path)



"""
==================
CL_FixCvarCheats

==================
*/

typedef struct
{
	char	*name;
	char	*value;
	cvar_t	*var;
} cheatvar_t;

cheatvar_t	cheatvars[] = {
	{"timescale", "1"},
	{"timedemo", "0"},
	{"r_drawworld", "1"},
	{"cl_testlights", "0"},
	{"r_fullbright", "0"},
	{"r_drawflat", "0"},
	{"paused", "0"},
	{"fixedtime", "0"},
	{"sw_draworder", "0"},
	{"gl_lightmap", "0"},
	{"gl_saturatelighting", "0"},
	{NULL, NULL}
};

int		numcheatvars;
"""
cheatvars = [
	{"name": "timescale", "value": "1", "var": None},
	{"name": "timedemo", "value": "0", "var": None},
	{"name": "r_drawworld", "value": "1", "var": None},
	{"name": "cl_testlights", "value": "0", "var": None},
	{"name": "r_fullbright", "value": "0", "var": None},
	{"name": "r_drawflat", "value": "0", "var": None},
	{"name": "paused", "value": "0", "var": None},
	{"name": "fixedtime", "value": "0", "var": None},
	{"name": "sw_draworder", "value": "0", "var": None},
	{"name": "gl_lightmap", "value": "0", "var": None},
	{"name": "gl_saturatelighting", "value": "0", "var": None},
]

numcheatvars = 0

def CL_FixCvarCheats ():

	maxclients = cl.configstrings[q_shared.CS_MAXCLIENTS]
	if not maxclients or maxclients == "1":
		return

	global numcheatvars
	if numcheatvars == 0:
		for cheat in cheatvars:
			cheat["var"] = cvar.Cvar_Get(cheat["name"], cheat["value"], 0)
			numcheatvars += 1

	for cheat in cheatvars:
		if cheat["var"] is None:
			continue
		if cheat["var"].string != cheat["value"]:
			cvar.Cvar_Set(cheat["name"], cheat["value"])

# =============================================================================

# ==================
# CL_SendCommand
# ==================
def CL_SendCommand ():
	
	"""
	// get new key events
	Sys_SendKeyEvents ();

	// allow mice or other external controllers to add commands
	IN_Commands ();
	"""
	# process console commands
	cmd.Cbuf_Execute ()

	# fix any cheating cvars
	CL_FixCvarCheats ()

	# send intentions now
	cl_input.CL_SendCmd ()

	# resend a connection request if necessary
	CL_CheckForResend ()



"""
==================
CL_Frame

==================
"""
extratime = 0
lasttimecalled = 0

def CL_Frame (msec): #int

	global extratime, lasttimecalled
	#static int	extratime;
	#static int  lasttimecalled;

	if common.dedicated.value != 0:
		return

	extratime += msec
	
	if not int(cl_timedemo.value):
	
		if cls.state == client.connstate_t.ca_connected and extratime < 100:
			return			# don't flood packets out while connecting
		if extratime < 1000.0/int(cl_maxfps.value):
			return			# framerate is too high
	
	"""
# let the mouse activate or deactivate
	IN_Frame ();
	"""

	# decide the simulation time
	cls.frametime = extratime/1000.0
	cl.time += extratime

	cls.realtime = q_shlinux.curtime

	extratime = 0
	#if 0
	##if (cls.frametime > (1.0 / cl_minfps->value))
	##	cls.frametime = (1.0 / cl_minfps->value);
	#else
	if cls.frametime > (1.0 / 5.0):
		cls.frametime = (1.0 / 5.0)
	#endif

	# if in the debugger last frame, don't timeout
	if msec > 5000:
		cls.netchan.last_received = q_shlinux.Sys_Milliseconds ()

	# fetch results from server
	CL_ReadPackets ()

	# send a new command message to the server
	CL_SendCommand ()

	# predict all unacknowledged movements
	cl_pred.CL_PredictMovement ()

	# allow rendering DLL change
	vid_so.VID_CheckChanges ()
	
	if not cl.refresh_prepped and cls.state == client.connstate_t.ca_active:
		cl_view.CL_PrepRefresh ()

	# update the screen
	if common.host_speeds.value:
		common.time_before_ref = q_shlinux.Sys_Milliseconds ()
	cl_scrn.SCR_UpdateScreen ()
	if common.host_speeds.value:
		common.time_after_ref = q_shlinux.Sys_Milliseconds ()

	# update audio
	#S_Update (cl.refdef.vieworg, cl.v_forward, cl.v_right, cl.v_up)
	snd_dma.S_Update (None, cl.v_forward, cl.v_right, cl.v_up) #FIXME Simplified while porting

	cd_linux.CDAudio_Update()

	# advance local effects for next frame
	cl_fx.CL_RunDLights ()
	cl_fx.CL_RunLightStyles ()
	cl_cin.SCR_RunCinematic ()
	cl_scrn.SCR_RunConsole ()

	cls.framecount+=1
	"""
		if ( log_stats->value )
		{
			if ( cls.state == client.connstate_t.ca_active )
		{
			if ( !lasttimecalled )
			{
				lasttimecalled = q_shlinux.Sys_Milliseconds();
				if ( log_stats_file )
					fprintf( log_stats_file, "0\n" );
			}
			else
			{
				int now = q_shlinux.Sys_Milliseconds();

				if ( log_stats_file )
					fprintf( log_stats_file, "%d\n", now - lasttimecalled );
				lasttimecalled = now;
			}
			}
		}
		"""



	# =============================================================================
# CL_Init
# =============================================================================
def CL_Init ():

	if common.dedicated.value:
		return		# nothing running on the client

	# all archived variables will now be loaded

	console.Con_Init ()

	#if defined __linux__ || defined __sgi
	snd_dma.S_Init ()
	vid_so.VID_Init ()
	#else
	#VID_Init ();
	#S_Init ();	// sound must be initialized after window is created
	#endif

	cl_view.V_Init ()
	common.SZ_Init(net_chan.net_message, qcommon.MAX_MSGLEN)
	menu.M_Init ()

	cl_scrn.SCR_Init ()
	cls.disable_screen = True	# don't draw yet
	
	#CDAudio_Init ();
	CL_InitLocal ()
	in_linux.IN_Init ()

	## Cbuf_AddText ("exec autoexec.cfg\n");
	files.FS_ExecAutoexec ()
	cmd.Cbuf_Execute ()


# ===============
# CL_Shutdown
#
# FIXME: this is a callback from Sys_Quit and Com_Error.  It would be better
# to run quit through here before the final handoff to the sys code.
# ===============
isdown = False

def CL_Shutdown():

	global isdown
	#static qboolean isdown = false;
	if isdown:
	
		print ("recursive shutdown\n")
		return
	
	isdown = True

	CL_WriteConfiguration ()

	#CDAudio_Shutdown ()

	snd_dma.S_Shutdown()
	"""
	IN_Shutdown ();
	VID_Shutdown();
	"""

