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
from qcommon import cvar, common, cmd, files, net_chan, qcommon, cmodel
from game import q_shared
from client import console, snd_dma, cl_scrn, client, cl_view, menu, cl_input, keys, cl_cin, cl_parse, cl_fx, cl_tent, cl_pred
from linux import q_shlinux, vid_so, in_linux, net_udp, cd_linux

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


/*
====================
CL_WriteDemoMessage

Dumps the current net message, prefixed by the length
====================
*/
void CL_WriteDemoMessage (void)
{
	int		len, swlen;

	// the first eight bytes are just packet sequencing stuff
	len = net_message.cursize-8;
	swlen = LittleLong(len);
	fwrite (&swlen, 4, 1, cls.demofile);
	fwrite (net_message.data+8,	len, 1, cls.demofile);
}


/*
====================
CL_Stop_f

stop recording a demo
====================
*/
void CL_Stop_f (void)
{
	int		len;

	if (!cls.demorecording)
	{
		Com_Printf ("Not recording a demo.\n");
		return;
	}

// finish up
	len = -1;
	fwrite (&len, 4, 1, cls.demofile);
	fclose (cls.demofile);
	cls.demofile = NULL;
	cls.demorecording = false;
	Com_Printf ("Stopped demo.\n");
}

/*
====================
CL_Record_f

record <demoname>

Begins recording a demo from the current position
====================
*/
void CL_Record_f (void)
{
	char	name[MAX_OSPATH];
	char	buf_data[MAX_MSGLEN];
	sizebuf_t	buf;
	int		i;
	int		len;
	entity_state_t	*ent;
	entity_state_t	nullstate;

	if (Cmd_Argc() != 2)
	{
		Com_Printf ("record <demoname>\n");
		return;
	}

	if (cls.demorecording)
	{
		Com_Printf ("Already recording.\n");
		return;
	}

	if (cls.state != client.connstate_t.ca_active)
	{
		Com_Printf ("You must be in a level to record.\n");
		return;
	}

	//
	// open the demo file
	//
	Com_sprintf (name, sizeof(name), "%s/demos/%s.dm2", files.FS_Gamedir(), Cmd_Argv(1));

	Com_Printf ("recording to %s.\n", name);
	FS_CreatePath (name);
	cls.demofile = fopen (name, "wb");
	if (!cls.demofile)
	{
		Com_Printf ("ERROR: couldn't open.\n");
		return;
	}
	cls.demorecording = true;

	// don't start saving messages until a non-delta compressed message is received
	cls.demowaiting = true;

	//
	// write out messages to hold the startup information
	//
	SZ_Init (&buf, buf_data, sizeof(buf_data));

	// send the serverdata
	MSG_WriteByte (&buf, svc_serverdata);
	MSG_WriteLong (&buf, qcommon.PROTOCOL_VERSION);
	MSG_WriteLong (&buf, 0x10000 + cl.servercount);
	MSG_WriteByte (&buf, 1);	// demos are always attract loops
	MSG_WriteString (&buf, cl.gamedir);
	MSG_WriteShort (&buf, cl.playernum);

	MSG_WriteString (&buf, cl.configstrings[q_shared.CS_NAME]);

	// configstrings
	for (i=0 ; i<MAX_CONFIGSTRINGS ; i++)
	{
		if (cl.configstrings[i][0])
		{
			if (buf.cursize + strlen (cl.configstrings[i]) + 32 > buf.maxsize)
			{	// write it out
				len = LittleLong (buf.cursize);
				fwrite (&len, 4, 1, cls.demofile);
				fwrite (buf.data, buf.cursize, 1, cls.demofile);
				buf.cursize = 0;
			}

			MSG_WriteByte (&buf, svc_configstring);
			MSG_WriteShort (&buf, i);
			MSG_WriteString (&buf, cl.configstrings[i]);
		}

	}

	// baselines
	memset (&nullstate, 0, sizeof(nullstate));
	for (i=0; i<q_shared.MAX_EDICTS ; i++)
	{
		ent = &cl_entities[i].baseline;
		if (!ent->modelindex)
			continue;

		if (buf.cursize + 64 > buf.maxsize)
		{	// write it out
			len = LittleLong (buf.cursize);
			fwrite (&len, 4, 1, cls.demofile);
			fwrite (buf.data, buf.cursize, 1, cls.demofile);
			buf.cursize = 0;
		}

		MSG_WriteByte (&buf, svc_spawnbaseline);		
		MSG_WriteDeltaEntity (&nullstate, &cl_entities[i].baseline, &buf, true, true);
	}

	MSG_WriteByte (&buf, svc_stufftext);
	MSG_WriteString (&buf, "precache\n");

	// write it to the demo file

	len = LittleLong (buf.cursize);
	fwrite (&len, 4, 1, cls.demofile);
	fwrite (buf.data, buf.cursize, 1, cls.demofile);

	// the rest of the demo file will be individual frames
}

//======================================================================

/*
===================
Cmd_ForwardToServer

adds the current command line as a qcommon.clc_ops_e.clc_stringcmd to the client message.
things like godmode, noclip, etc, are commands directed to the server,
so when they are typed in at the console, they will need to be forwarded.
===================
*/
void Cmd_ForwardToServer (void)
{
	char	*cmd;

	cmd = Cmd_Argv(0);
	if (cls.state <= client.connstate_t.ca_connected || *cmd == '-' || *cmd == '+')
	{
		Com_Printf ("Unknown command \"%s\"\n", cmd);
		return;
	}

	MSG_WriteByte (&cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd);
	SZ_Print (&cls.netchan.message, cmd);
	if (Cmd_Argc() > 1)
	{
		SZ_Print (&cls.netchan.message, " ");
		SZ_Print (&cls.netchan.message, Cmd_Args());
	}
}

void CL_Setenv_f( void )
{
	int argc = Cmd_Argc();

	if ( argc > 2 )
	{
		char buffer[1000];
		int i;

		strcpy( buffer, Cmd_Argv(1) );
		strcat( buffer, "=" );

		for ( i = 2; i < argc; i++ )
		{
			strcat( buffer, Cmd_Argv( i ) );
			strcat( buffer, " " );
		}

		putenv( buffer );
	}
	else if ( argc == 2 )
	{
		char *env = getenv( Cmd_Argv(1) );

		if ( env )
		{
			Com_Printf( "%s=%s\n", Cmd_Argv(1), env );
		}
		else
		{
			Com_Printf( "%s undefined\n", Cmd_Argv(1), env );
		}
	}
}


/*
==================
CL_ForwardToServer_f
==================
"""
def CL_ForwardToServer_f ():

	print ("CL_ForwardToServer_f")

	"""
	if (cls.state != client.connstate_t.ca_connected && cls.state != client.connstate_t.ca_active)
	{
		Com_Printf ("Can't \"%s\", not connected\n", Cmd_Argv(0));
		return;
	}
	
	// don't forward the first argument
	if (Cmd_Argc() > 1)
	{
		MSG_WriteByte (&cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd);
		SZ_Print (&cls.netchan.message, Cmd_Args());
	}
}


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
	
	if adr.port == 0 or adr.port is None:
		adr.port = struct.pack(">H", qcommon.PORT_SERVER)

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

	if adr.port == 0 or adr.port is None:
		adr.port = struct.pack(">H", qcommon.PORT_SERVER)

	cls.connect_time = cls.realtime

	common.Com_Printf("Connecting to {}...\n".format(cls.servername))

	net_chan.Netchan_OutOfBandPrint(qcommon.netsrc_t.NS_CLIENT, adr, b"getchallenge\n")



# ================
# CL_Connect_f
# ================
def CL_Connect_f ():

	print ("CL_Connect_f")
	"""
	char	*server;

	if (Cmd_Argc() != 2)
	{
		Com_Printf ("usage: connect <server>\n");
		return;	
	}
	
	if (Com_ServerState ())
	{	// if running a local server, kill it and reissue
		SV_Shutdown (va("Server quit\n", msg), false);
	}
	else
	{
		CL_Disconnect ();
	}

	server = Cmd_Argv (1);

	net_udp.NET_Config (true);		// allow remote

	CL_Disconnect ();

	cls.state = client.connstate_t.ca_connecting;
	strncpy (cls.servername, server, sizeof(cls.servername)-1);
	cls.connect_time = -99999;	// CL_CheckForResend() will fire immediately
}
	"""


"""
/*
=====================
CL_Rcon_f

  Send the rest of the command line over as
  an unconnected command.
=====================
*/
void CL_Rcon_f (void)
{
	char	message[1024];
	int		i;
	netadr_t	to;

	if (!rcon_client_password->string)
	{
		Com_Printf ("You must set 'rcon_password' before\n"
					"issuing an rcon command.\n");
		return;
	}

	message[0] = (char)255;
	message[1] = (char)255;
	message[2] = (char)255;
	message[3] = (char)255;
	message[4] = 0;

	net_udp.NET_Config (true);		// allow remote

	strcat (message, "rcon ");

	strcat (message, rcon_client_password->string);
	strcat (message, " ");

	for (i=1 ; i<Cmd_Argc() ; i++)
	{
		strcat (message, Cmd_Argv(i));
		strcat (message, " ");
	}

	if (cls.state >= client.connstate_t.ca_connected)
		to = cls.netchan.remote_address;
	else
	{
		if (!strlen(rcon_address->string))
		{
			Com_Printf ("You must either be connected,\n"
						"or set the 'rcon_address' cvar\n"
						"to issue rcon commands\n");

			return;
		}
		NET_StringToAdr (rcon_address->string, &to);
		if (to.port == 0)
			to.port = BigShort (qcommon.PORT_SERVER);
	}
	
	NET_SendPacket (qcommon.netsrc_t.NS_CLIENT, strlen(message)+1, message, to);
}
"""


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

	if cmds.Cmd_Argc() != 3:
	
		common.Com_Printf ("packet <destination> <contents>\n")
		return
	
	
	"""
	net_udp.NET_Config (true);		// allow remote

	if (!NET_StringToAdr (Cmd_Argv(1), &adr))
	{
		Com_Printf ("Bad address\n");
		return;
	}
	if (!adr.port)
		adr.port = BigShort (qcommon.PORT_SERVER);

	in = Cmd_Argv(2);
	out = send+4;
	send[0] = send[1] = send[2] = send[3] = (char)0xff;

	l = strlen (in);
	for (i=0 ; i<l ; i++)
	{
		if (in[i] == '\\' && in[i+1] == 'n')
		{
			*out++ = '\n';
			i++;
		}
		else
			*out++ = in[i];
	}
	*out = 0;

	NET_SendPacket (qcommon.netsrc_t.NS_CLIENT, out-send, send, adr);


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
*/
void CL_ParseStatusMessage (void)
{
	char	*s;

	s = MSG_ReadString(&net_message);

	Com_Printf ("%s\n", s);
	M_AddToServerList (net_chan.net_from, s);
}


/*
=================
CL_PingServers_f
=================
*/
void CL_PingServers_f (void)
{
	int			i;
	netadr_t	adr;
	char		name[32];
	char		*adrstring;
	cvar_t		*noudp;
	cvar_t		*noipx;

	net_udp.NET_Config (true);		// allow remote

	// send a broadcast packet
	Com_Printf ("pinging broadcast...\n");

	noudp = Cvar_Get ("noudp", "0", CVAR_NOSET);
	if (!noudp->value)
	{
		adr.type = NA_BROADCAST;
		adr.port = BigShort(qcommon.PORT_SERVER);
		Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, va("info %i", qcommon.PROTOCOL_VERSION));
	}

	noipx = Cvar_Get ("noipx", "0", CVAR_NOSET);
	if (!noipx->value)
	{
		adr.type = NA_BROADCAST_IPX;
		adr.port = BigShort(qcommon.PORT_SERVER);
		Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, va("info %i", qcommon.PROTOCOL_VERSION));
	}

	// send a packet to each address book entry
	for (i=0 ; i<16 ; i++)
	{
		Com_sprintf (name, sizeof(name), "adr%i", i);
		adrstring = Cvar_VariableString (name);
		if (!adrstring || !adrstring[0])
			continue;

		Com_Printf ("pinging %s...\n", adrstring);
		if (!NET_StringToAdr (adrstring, &adr))
		{
			Com_Printf ("Bad address: %s\n", adrstring);
			continue;
		}
		if (!adr.port)
			adr.port = BigShort(qcommon.PORT_SERVER);
		Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, adr, va("info %i", qcommon.PROTOCOL_VERSION));
	}
}


/*
=================
CL_Skins_f

Load or download any custom player skins and models
=================
*/
void CL_Skins_f (void)
{
	int		i;

	for (i=0 ; i<MAX_CLIENTS ; i++)
	{
		if (!cl.configstrings[q_shared.CS_PLAYERSKINS+i][0])
			continue;
		Com_Printf ("client %i: %s\n", i, cl.configstrings[q_shared.CS_PLAYERSKINS+i]); 
		SCR_UpdateScreen ();
		Sys_SendKeyEvents ();	// pump message loop
		CL_ParseClientinfo (i);
	}
}


/*
=================
CL_ConnectionlessPacket

Responses to broadcasts, etc
=================
"""
def CL_ConnectionlessPacket ():

	#char	*s;
	#char	*c;
	
	#MSG_BeginReading (&net_message);
	#MSG_ReadLong (&net_message);	// skip the -1

	s = net_chan.net_message.data[4:].decode("ascii")

	cmd.Cmd_TokenizeString (s, False)

	c = cmd.Cmd_Argv(0)

	common.Com_Printf ("{}: {}\n".format(net_udp.NET_AdrToString (net_chan.net_from), c))
	print ("CL_ConnectionlessPacket", c)

	# server connection
	if c == "client_connect":
	
		if cls.state == client.connstate_t.ca_connected:
		
			common.Com_Printf ("Dup connect received.  Ignored.\n")
			return

		net_chan.Netchan_Setup (qcommon.netsrc_t.NS_CLIENT, cls.netchan, net_chan.net_from, cls.quakePort)
		common.MSG_WriteChar(cls.netchan.message, struct.pack("B", qcommon.clc_ops_e.clc_stringcmd.value))
		common.MSG_WriteString(cls.netchan.message, b"new")
		cls.state = client.connstate_t.ca_connected
		return
	
	# server responding to a status broadcast
	elif c == "info":
	
		CL_ParseStatusMessage ()
		return
	
	# remote command from gui front end
	elif c == "cmd":
	
		if not NET_IsLocalAddress(net_chan.net_from):
		
			Com_Printf ("Command packet from remote host.  Ignored.\n")
			return
		
		Sys_AppActivate ()
		s = MSG_ReadString (net_chan.net_message)
		Cbuf_AddText (s)
		Cbuf_AddText ("\n")
		return
	
	# print command from somewhere
	elif c == "print":
	
		s = MSG_ReadString (net_chan.net_message)
		common.Com_Printf ("%s", s)
		return
	

	# ping from somewhere
	elif c == "ping":
	
		Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, "ack")
		return
	

	# challenge from the server we are connecting to
	elif c == "challenge":
	
		cls.challenge = atoi(Cmd_Argv(1))
		CL_SendConnectPacket ()
		return
	

	# echo request from server
	elif c == "echo":
	
		Netchan_OutOfBandPrint (qcommon.netsrc_t.NS_CLIENT, net_chan.net_from, "%s", Cmd_Argv(1) )
		return
	

	common.Com_Printf ("Unknown command.\n")


"""
=================
CL_DumpPackets

A vain attempt to help bad TCP stacks that cause problems
when they overflow
=================
*/
void CL_DumpPackets (void)
{
	while (NET_GetPacket (qcommon.netsrc_t.NS_CLIENT, &net_chan.net_from, &net_message))
	{
		Com_Printf ("dumnping a packet\n");
	}
}

/*
=================
CL_ReadPackets
=================
"""
def CL_ReadPackets ():

	rx, net_chan.net_from, net_chan.net_message = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_CLIENT)

	while rx:
		try:
			##Com_Printf ("packet\n");
			#
			# remote command packet
			#

			header = struct.unpack(">l", net_chan.net_message.data[:4])[0]
			if header == -1:
				CL_ConnectionlessPacket ()
				continue
			

			if cls.state == client.connstate_t.ca_disconnected or cls.state == client.connstate_t.ca_connecting:
				continue		# dump it if not connected

			if len(net_chan.net_message.data) < 8:
			
				common.Com_Printf ("{}: Runt packet\n".format(net_udp.net_udp.NET_AdrToString(net_chan.net_from)))
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
			rx, net_chan.net_from, net_chan.net_message = net_udp.NET_GetPacket (qcommon.netsrc_t.NS_CLIENT)

	"""
	//
	// check timeout
	//
	if (cls.state >= client.connstate_t.ca_connected
	 && cls.realtime - cls.netchan.last_received > cl_timeout->value*1000)
	{
		if (++cl.timeoutcount > 5)	// timeoutcount saves debugger
		{
			Com_Printf ("\nServer connection timed out.\n");
			CL_Disconnect ();
			return;
		}
	}
	else
		cl.timeoutcount = 0;
	



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
"""
byte *precache_model; // used for skin checking in alias models

#define PLAYER_MULT 5

// ENV_CNT is map load, ENV_CNT+1 is first env map
#define ENV_CNT (q_shared.CS_PLAYERSKINS + MAX_CLIENTS * PLAYER_MULT)
#define TEXTURE_CNT (ENV_CNT+13)

static const char *env_suf[6] = {"rt", "bk", "lf", "ft", "up", "dn"};

void CL_RequestNextDownload (void)
{
	unsigned	map_checksum;		// for detecting cheater maps
	char fn[MAX_OSPATH];
	dmdl_t *pheader;

	if (cls.state != client.connstate_t.ca_connected)
		return;

	if (!allow_download->value && precache_check < ENV_CNT)
		precache_check = ENV_CNT;

//ZOID
	if (precache_check == q_shared.CS_MODELS) { // confirm map
		precache_check = q_shared.CS_MODELS+2; // 0 isn't used
		if (allow_download_maps->value)
			if (!CL_CheckOrDownloadFile(cl.configstrings[q_shared.CS_MODELS+1]))
				return; // started a download
	}
	if (precache_check >= q_shared.CS_MODELS && precache_check < q_shared.CS_MODELS+MAX_MODELS) {
		if (allow_download_models->value) {
			while (precache_check < q_shared.CS_MODELS+MAX_MODELS &&
				cl.configstrings[precache_check][0]) {
				if (cl.configstrings[precache_check][0] == '*' ||
					cl.configstrings[precache_check][0] == '#') {
					precache_check++;
					continue;
				}
				if (precache_model_skin == 0) {
					if (!CL_CheckOrDownloadFile(cl.configstrings[precache_check])) {
						precache_model_skin = 1;
						return; // started a download
					}
					precache_model_skin = 1;
				}

				// checking for skins in the model
				if (!precache_model) {

					FS_LoadFile (cl.configstrings[precache_check], (void **)&precache_model);
					if (!precache_model) {
						precache_model_skin = 0;
						precache_check++;
						continue; // couldn't load it
					}
					if (LittleLong(*(unsigned *)precache_model) != IDALIASHEADER) {
						// not an alias model
						FS_FreeFile(precache_model);
						precache_model = 0;
						precache_model_skin = 0;
						precache_check++;
						continue;
					}
					pheader = (dmdl_t *)precache_model;
					if (LittleLong (pheader->version) != ALIAS_VERSION) {
						precache_check++;
						precache_model_skin = 0;
						continue; // couldn't load it
					}
				}

				pheader = (dmdl_t *)precache_model;

				while (precache_model_skin - 1 < LittleLong(pheader->num_skins)) {
					if (!CL_CheckOrDownloadFile((char *)precache_model +
						LittleLong(pheader->ofs_skins) + 
						(precache_model_skin - 1)*MAX_SKINNAME)) {
						precache_model_skin++;
						return; // started a download
					}
					precache_model_skin++;
				}
				if (precache_model) { 
					FS_FreeFile(precache_model);
					precache_model = 0;
				}
				precache_model_skin = 0;
				precache_check++;
			}
		}
		precache_check = q_shared.CS_SOUNDS;
	}
	if (precache_check >= q_shared.CS_SOUNDS && precache_check < q_shared.CS_SOUNDS+MAX_SOUNDS) { 
		if (allow_download_sounds->value) {
			if (precache_check == q_shared.CS_SOUNDS)
				precache_check++; // zero is blank
			while (precache_check < q_shared.CS_SOUNDS+MAX_SOUNDS &&
				cl.configstrings[precache_check][0]) {
				if (cl.configstrings[precache_check][0] == '*') {
					precache_check++;
					continue;
				}
				Com_sprintf(fn, sizeof(fn), "sound/%s", cl.configstrings[precache_check++]);
				if (!CL_CheckOrDownloadFile(fn))
					return; // started a download
			}
		}
		precache_check = q_shared.CS_IMAGES;
	}
	if (precache_check >= q_shared.CS_IMAGES && precache_check < q_shared.CS_IMAGES+MAX_IMAGES) {
		if (precache_check == q_shared.CS_IMAGES)
			precache_check++; // zero is blank
		while (precache_check < q_shared.CS_IMAGES+MAX_IMAGES &&
			cl.configstrings[precache_check][0]) {
			Com_sprintf(fn, sizeof(fn), "pics/%s.pcx", cl.configstrings[precache_check++]);
			if (!CL_CheckOrDownloadFile(fn))
				return; // started a download
		}
		precache_check = q_shared.CS_PLAYERSKINS;
	}
	// skins are special, since a player has three things to download:
	// model, weapon model and skin
	// so precache_check is now *3
	if (precache_check >= q_shared.CS_PLAYERSKINS && precache_check < q_shared.CS_PLAYERSKINS + MAX_CLIENTS * PLAYER_MULT) {
		if (allow_download_players->value) {
			while (precache_check < q_shared.CS_PLAYERSKINS + MAX_CLIENTS * PLAYER_MULT) {
				int i, n;
				char model[MAX_QPATH], skin[MAX_QPATH], *p;

				i = (precache_check - q_shared.CS_PLAYERSKINS)/PLAYER_MULT;
				n = (precache_check - q_shared.CS_PLAYERSKINS)%PLAYER_MULT;

				if (!cl.configstrings[q_shared.CS_PLAYERSKINS+i][0]) {
					precache_check = q_shared.CS_PLAYERSKINS + (i + 1) * PLAYER_MULT;
					continue;
				}

				if ((p = strchr(cl.configstrings[q_shared.CS_PLAYERSKINS+i], '\\')) != NULL)
					p++;
				else
					p = cl.configstrings[q_shared.CS_PLAYERSKINS+i];
				strcpy(model, p);
				p = strchr(model, '/');
				if (!p)
					p = strchr(model, '\\');
				if (p) {
					*p++ = 0;
					strcpy(skin, p);
				} else
					*skin = 0;

				switch (n) {
				case 0: // model
					Com_sprintf(fn, sizeof(fn), "players/%s/tris.md2", model);
					if (!CL_CheckOrDownloadFile(fn)) {
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 1;
						return; // started a download
					}
					n++;
					/*FALL THROUGH*/

				case 1: // weapon model
					Com_sprintf(fn, sizeof(fn), "players/%s/weapon.md2", model);
					if (!CL_CheckOrDownloadFile(fn)) {
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 2;
						return; // started a download
					}
					n++;
					/*FALL THROUGH*/

				case 2: // weapon skin
					Com_sprintf(fn, sizeof(fn), "players/%s/weapon.pcx", model);
					if (!CL_CheckOrDownloadFile(fn)) {
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 3;
						return; // started a download
					}
					n++;
					/*FALL THROUGH*/

				case 3: // skin
					Com_sprintf(fn, sizeof(fn), "players/%s/%s.pcx", model, skin);
					if (!CL_CheckOrDownloadFile(fn)) {
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 4;
						return; // started a download
					}
					n++;
					/*FALL THROUGH*/

				case 4: // skin_i
					Com_sprintf(fn, sizeof(fn), "players/%s/%s_i.pcx", model, skin);
					if (!CL_CheckOrDownloadFile(fn)) {
						precache_check = q_shared.CS_PLAYERSKINS + i * PLAYER_MULT + 5;
						return; // started a download
					}
					// move on to next model
					precache_check = q_shared.CS_PLAYERSKINS + (i + 1) * PLAYER_MULT;
				}
			}
		}
		// precache phase completed
		precache_check = ENV_CNT;
	}

	if (precache_check == ENV_CNT) {
		precache_check = ENV_CNT + 1;

		CM_LoadMap (cl.configstrings[q_shared.CS_MODELS+1], true, &map_checksum);

		if (map_checksum != atoi(cl.configstrings[q_shared.CS_MAPCHECKSUM])) {
			Com_Error (q_shared.ERR_DROP, "Local map version differs from server: %i != '%s'\n",
				map_checksum, cl.configstrings[q_shared.CS_MAPCHECKSUM]);
			return;
		}
	}

	if (precache_check > ENV_CNT && precache_check < TEXTURE_CNT) {
		if (allow_download->value && allow_download_maps->value) {
			while (precache_check < TEXTURE_CNT) {
				int n = precache_check++ - ENV_CNT - 1;

				if (n & 1)
					Com_sprintf(fn, sizeof(fn), "env/%s%s.pcx", 
						cl.configstrings[q_shared.CS_SKY], env_suf[n/2]);
				else
					Com_sprintf(fn, sizeof(fn), "env/%s%s.tga", 
						cl.configstrings[q_shared.CS_SKY], env_suf[n/2]);
				if (!CL_CheckOrDownloadFile(fn))
					return; // started a download
			}
		}
		precache_check = TEXTURE_CNT;
	}

	if (precache_check == TEXTURE_CNT) {
		precache_check = TEXTURE_CNT+1;
		precache_tex = 0;
	}

	// confirm existance of textures, download any that don't exist
	if (precache_check == TEXTURE_CNT+1) {
		// from qcommon/cmodel.c
		extern int			numtexinfo;
		extern mapsurface_t	map_surfaces[];

		if (allow_download->value && allow_download_maps->value) {
			while (precache_tex < numtexinfo) {
				char fn[MAX_OSPATH];

				sprintf(fn, "textures/%s.wal", map_surfaces[precache_tex++].rname);
				if (!CL_CheckOrDownloadFile(fn))
					return; // started a download
			}
		}
		precache_check = TEXTURE_CNT+999;
	}

//ZOID
	CL_RegisterSounds ();
	cl_view.CL_PrepRefresh ();

	MSG_WriteByte (&cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd);
	MSG_WriteString (&cls.netchan.message, va("begin %i\n", precache_spawncount) );
}

/*
=================
CL_Precache_f

The server will send this command right
before allowing the client into the server
=================
"""
def CL_Precache_f ():

	global precache_check, precache_spawncount, precache_tex, precache_model_skin
	
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
	precache_model = 0
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
	"""
	Cmd_AddCommand ("pingservers", CL_PingServers_f);
	Cmd_AddCommand ("skins", CL_Skins_f);
	"""
	cmd.Cmd_AddCommand ("userinfo", CL_Userinfo_f);
	cmd.Cmd_AddCommand ("snd_restart", CL_Snd_Restart_f);

	cmd.Cmd_AddCommand ("changing", CL_Changing_f)
	cmd.Cmd_AddCommand ("disconnect", CL_Disconnect_f)
	"""
	Cmd_AddCommand ("record", CL_Record_f);
	Cmd_AddCommand ("stop", CL_Stop_f);
	"""
	cmd.Cmd_AddCommand ("quit", CL_Quit_f)
	
	cmd.Cmd_AddCommand ("connect", CL_Connect_f)
	cmd.Cmd_AddCommand ("reconnect", CL_Reconnect_f)
	"""
	Cmd_AddCommand ("rcon", CL_Rcon_f);

 	## Cmd_AddCommand ("packet", CL_Packet_f); # this is dangerous to leave in

	Cmd_AddCommand ("setenv", CL_Setenv_f );

	"""
	cmd.Cmd_AddCommand ("precache", CL_Precache_f)
	"""

	Cmd_AddCommand ("download", CL_Download_f);
	"""
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

