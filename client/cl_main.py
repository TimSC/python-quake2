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

This is the clients main loop as well as some miscelangelous utility
and support functions

=======================================================================
"""
from __future__ import annotations

import os
import struct
from client import snd_dma, cl_view, menu, cl_input, cl_cin, cl_parse, cl_fx, cl_tent
from linux import q_shlinux, vid_so, net_udp, cd_linux, sys_linux
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import argproc
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import frame
from common import movemsg
from common import szone
from common import collision
from common import netchan
from client import cl_console
from client import cl_download
from client import cl_input
from client import cl_keyboard
from client import cl_network
from client import cl_parse
from client import cl_prediction
from client import cl_screen
from client import cl_view
from client.header import client as client_h

"""
#include <errno.h>
#include "header/client.h"
#include "input/header/input.h"
"""

adr0, adr1, adr2, adr3, adr4, adr5, adr6, adr7, adr8 = None, None, None, None, None, None, None, None, None

cl_stereo_separation = None #cvar_t *
cl_stereo = None #cvar_t *

cl_add_blend, cl_add_lights, cl_add_particles, cl_add_entities = None, None, None, None
cl_gun, cl_footsteps, cl_noskins, cl_autoskins, cl_predict, cl_maxfps = None, None, None, None, None, None
cl_upspeed, cl_forwardspeed, cl_sidespeed, cl_yawspeed, cl_pitchspeed, cl_anglespeedkey = None, None, None, None, None, None

m_pitch, m_yaw, m_forward, m_side = None, None, None, None
cl_shownet, cl_showmiss, cl_showclamp, cl_timeout, cl_paused, cl_timedemo = None, None, None, None, None, None
rcon_client_password, rcon_address, cl_lightlevel = None, None, None
info_password, info_spectator, name, skin, rate, msg, hand, fov, gender, gender_auto, cl_vwep = None, None, None, None, None, None, None, None, None, None, None

cls = client_h.client_static_t()

cl = client_h.client_state_t()


cl_entities = []
for i in range(shared.MAX_EDICTS):
	cl_entities.append(client_h.centity_t())


cl_parse_entities = [] 
for i in range(client_h.MAX_PARSE_ENTITIES):
	cl_parse_entities.append(shared.entity_state_t())
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
"""
void
CL_ClearEntities(void)
{
	if (cl_entities)
	{
		Z_Free(cl_entities);
		cl_entities = NULL;
	}

	cl_numentities = 0;
}
"""

"""
centity_t *
CL_AllocEntity(int entnum)
{
	int nextpow2;

	if ((entnum < 0) || (entnum > MAX_CL_ENTNUM))
	{
		return NULL;
	}

	if (entnum >= cl_numentities)
	{
		nextpow2 = (cl_numentities || (entnum >= ALLOC_ENTITIES_MIN)) ?
			(int)NextPow2gt(entnum) : ALLOC_ENTITIES_MIN;

		cl_entities = Z_Realloc(cl_entities, nextpow2 * sizeof(centity_t));
		cl_numentities = nextpow2;
	}

	return &cl_entities[entnum];
}
"""

"""
/*
 * Returns max clients in the current session
 * Returns 1 if the value is bad (<= 0) or the configstring is blank
 */
int
CL_MaxClients(void)
{
	int i = 0;

	sscanf(cl.configstrings[CS_MAXCLIENTS], " %i ", &i);

	if (i > MAX_CLIENTS)
	{
		return MAX_CLIENTS;
	}

	return i <= 0 ? 1 : i;
}
"""

"""
// cl_main.c  -- client main loop

#include "client.h"
"""

def CL_WriteDemoMessage ():

	#int		len, swlen;

	# the first eight bytes are just packet sequencing stuff
	length = netchan.net_message.cursize-8
	cls.demofile.write (struct.pack("<i", length)) # swlen = LittleLong(len); fwrite (&swlen, 4, 1, cls.demofile);
	cls.demofile.write (netchan.net_message.data[8:8+length])


"""
====================
CL_Stop_f

stop recording a demo
====================
"""
def CL_Stop_f ():

	#int		len;

	if not cls.demorecording:
	
		clientserver.Com_Printf ("Not recording a demo.\n")
		return
	
	# finish up
	length = -1
	cls.demofile.write (struct.pack("<i", length))
	cls.demofile.close ()
	cls.demofile = None
	cls.demorecording = False
	clientserver.Com_Printf ("Stopped demo.\n")

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
	buf = common_h.sizebuf_t()

	if cmdparser.Cmd_Argc() != 2:
	
		clientserver.Com_Printf ("record <demoname>\n")
		return
	
	if cls.demorecording:
	
		clientserver.Com_Printf ("Already recording.\n")
		return
	
	if cls.state != client_h.connstate_t.ca_active:
	
		clientserver.Com_Printf ("You must be in a level to record.\n")
		return
	
	#
	# open the demo file
	#
	name = "{}/demos/{}.dm2".format(filesystem.FS_Gamedir(), cmdparser.Cmd_Argv(1))

	clientserver.Com_Printf ("recording to {}.\n".format(name))
	filesystem.FS_CreatePath (name)
	try:
		cls.demofile = open (name, "wb")
	except OSError:
		cls.demofile = None
	if cls.demofile is None:
	
		clientserver.Com_Printf ("ERROR: couldn't open.\n")
		return
	
	cls.demorecording = True

	# don't start saving messages until a non-delta compressed message is received
	cls.demowaiting = True

	#
	# write out messages to hold the startup information
	#
	szone.SZ_Init (buf, common_h.MAX_MSGLEN)

	# send the serverdata
	movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_serverdata.value)
	movemsg.MSG_WriteLong (buf, common_h.PROTOCOL_VERSION)
	movemsg.MSG_WriteLong (buf, 0x10000 + cl.servercount)
	movemsg.MSG_WriteByte (buf, 1)	# demos are always attract loops
	movemsg.MSG_WriteString (buf, cl.gamedir.encode('ascii'))
	movemsg.MSG_WriteShort (buf, cl.playernum)

	movemsg.MSG_WriteString (buf, cl.configstrings[shared.CS_NAME].encode('ascii'))

	# configstrings
	for i in range(shared.MAX_CONFIGSTRINGS):
	
		if cl.configstrings[i]:
		
			if buf.cursize + len (cl.configstrings[i]) + 32 > buf.maxsize:
				# write it out
				cls.demofile.write (struct.pack("<i", buf.cursize)) # len = LittleLong (buf.cursize); fwrite (&len, 4, 1, cls.demofile);
				cls.demofile.write (buf.data[:buf.cursize])
				buf.cursize = 0
			
			movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_configstring.value)
			movemsg.MSG_WriteShort (buf, i)
			movemsg.MSG_WriteString (buf, cl.configstrings[i].encode('ascii'))
		
	# baselines
	nullstate = shared.entity_state_t() # memset (&nullstate, 0, sizeof(nullstate));
	for i in range(shared.MAX_EDICTS):
	
		ent = cl_entities[i].baseline
		if not ent.modelindex:
			continue

		if buf.cursize + 64 > buf.maxsize:
			# write it out
			cls.demofile.write (struct.pack("<i", buf.cursize))
			cls.demofile.write (buf.data[:buf.cursize])
			buf.cursize = 0
		
		movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_spawnbaseline.value)		
		movemsg.MSG_WriteDeltaEntity (nullstate, cl_entities[i].baseline, buf, True, True)
	
	movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_stufftext.value)
	movemsg.MSG_WriteString (buf, b"precache\n")

	# write it to the demo file

	cls.demofile.write (struct.pack("<i", buf.cursize))
	cls.demofile.write (buf.data[:buf.cursize])

	

def CL_Setenv_f():

	argc = cmdparser.Cmd_Argc()

	if argc > 2:
	
		#char buffer[1000];
		#int i;

		name = cmdparser.Cmd_Argv(1)
		buffer = ""

		for i in range(2, argc):
		
			buffer += cmdparser.Cmd_Argv( i )
			buffer += " "
		
		os.environ[name] = buffer # strcpy( buffer, Cmd_Argv(1) ); strcat( buffer, "=" ); ... putenv( buffer );
	
	elif argc == 2:
	
		env = os.environ.get( cmdparser.Cmd_Argv(1) ) # getenv returns NULL when unset

		if env is not None:
		
			clientserver.Com_Printf( "{}={}\n".format(cmdparser.Cmd_Argv(1), env) )
		
		else:
		
			clientserver.Com_Printf( "{} undefined\n".format(cmdparser.Cmd_Argv(1)) )

	


"""
/*
==================
CL_Pause_f
==================
"""
def CL_Pause_f ():

	# never pause in multiplayer
	if cvar.Cvar_VariableValue ("maxclients") > 1 or not clientserver.Com_ServerState ():
	
		cvar.Cvar_SetValue ("paused", 0)
		return
	
	cvar.Cvar_SetValue ("paused", cl_paused.value == 0.0)


"""
==================
CL_Quit_f
==================
"""
def CL_Quit_f ():

	cl_network.CL_Disconnect ()
	clientserver.Com_Quit ()


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

	szone.SZ_Clear (cls.netchan.message)


"""
=================
CL_ParseStatusMessage

Handle a reply from a ping
=================
"""
def CL_ParseStatusMessage ():

	#char	*s;

	s = movemsg.MSG_ReadString(netchan.net_message)

	clientserver.Com_Printf ("{}\n".format(s))
	menu.M_AddToServerList (netchan.net_from, s)

	

"""


/*
=================
CL_Skins_f

Load or download any custom player skins and models
=================
"""
def CL_Skins_f ():

	#int		i;

	for i in range(shared.MAX_CLIENTS):
	
		if not cl.configstrings[shared.CS_PLAYERSKINS+i]:
			continue
		clientserver.Com_Printf ("client {}: {}\n".format(i, cl.configstrings[shared.CS_PLAYERSKINS+i])) 
		cl_screen.SCR_UpdateScreen ()
		sys_linux.Sys_SendKeyEvents ()	# pump message loop
		cl_parse.CL_ParseClientinfo (i)


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
		rx, netchan.net_from = net_udp.NET_GetPacket (common_h.netsrc_t.NS_CLIENT, netchan.net_from, netchan.net_message)
		if not rx:
			break
	
		clientserver.Com_Printf ("dumnping a packet\n")

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

	if shared_c.Q_stricmp(skin_dir, "male") == 0 or shared_c.Q_stricmp(skin_dir, "cyborg") == 0:
		cvar.Cvar_Set("gender", "male")
	elif shared_c.Q_stricmp(skin_dir, "female") == 0 or shared_c.Q_stricmp(skin_dir, "crackhor") == 0:
		cvar.Cvar_Set("gender", "female")
	else:
		cvar.Cvar_Set("gender", "none")
	gender.modified = False


# ==============
# CL_Userinfo_f
# ==============
def CL_Userinfo_f ():

	clientserver.Com_Printf ("User info settings:\n")
	argproc.Info_Print (cvar.Cvar_Userinfo())


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


"""
void CL_ResetPrecacheCheck (void)
{
	precache_check = CS_MODELS;
	precache_model = 0;
	precache_model_skin = 0;
}
"""

precache_check: int = 0 # for autodownload of precache items
precache_spawncount: int = 0
precache_tex: int = 0
precache_model_skin: int = 0
precache_model = None #byte *, used for skin checking in alias models

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
	if cmdparser.Cmd_Argc() < 2:
		#unsigned	map_checksum;		// for detecting cheater maps

		map_checksum = collision.CM_LoadMap (cl.configstrings[shared.CS_MODELS+1], True)
		cl_parse.CL_RegisterSounds ()
		cl_view.CL_PrepRefresh ()
		return
	

	precache_check = shared.CS_MODELS
	precache_spawncount = int(cmdparser.Cmd_Argv(1))
	precache_model = None
	precache_model_skin = 0

	cl_download.CL_RequestNextDownload()


r"""
static void
CL_CurrentMap_f(void)
{
	Com_Printf("%s\n", cl.configstrings[CS_MODELS + 1]);
}
"""

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
	global freelook, lookspring, lookstrafe, sensitivity
	global m_pitch, m_yaw, m_forward, m_side
	global cl_shownet, cl_showmiss, cl_showclamp, cl_timeout, cl_paused, cl_timedemo
	global rcon_client_password, rcon_address, cl_lightlevel
	global info_password, info_spectator, name, skin, rate, msg, hand, fov, gender, gender_auto, cl_vwep

	cls.state = client_h.connstate_t.ca_disconnected
	cls.realtime = q_shlinux.Sys_Milliseconds ()

	cl_input.CL_InitInput ()

	adr0 = cvar.Cvar_Get( "adr0", "", shared.CVAR_ARCHIVE )
	adr1 = cvar.Cvar_Get( "adr1", "", shared.CVAR_ARCHIVE )
	adr2 = cvar.Cvar_Get( "adr2", "", shared.CVAR_ARCHIVE )
	adr3 = cvar.Cvar_Get( "adr3", "", shared.CVAR_ARCHIVE )
	adr4 = cvar.Cvar_Get( "adr4", "", shared.CVAR_ARCHIVE )
	adr5 = cvar.Cvar_Get( "adr5", "", shared.CVAR_ARCHIVE )
	adr6 = cvar.Cvar_Get( "adr6", "", shared.CVAR_ARCHIVE )
	adr7 = cvar.Cvar_Get( "adr7", "", shared.CVAR_ARCHIVE )
	adr8 = cvar.Cvar_Get( "adr8", "", shared.CVAR_ARCHIVE )

	#
	# register our variables
	#
	cl_stereo_separation = cvar.Cvar_Get( "cl_stereo_separation", "0.4", shared.CVAR_ARCHIVE )
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

	cl_input.cl_run = cvar.Cvar_Get ("cl_run", "0", shared.CVAR_ARCHIVE)
	freelook = cvar.Cvar_Get( "freelook", "0", shared.CVAR_ARCHIVE )
	lookspring = cvar.Cvar_Get ("lookspring", "0", shared.CVAR_ARCHIVE)
	lookstrafe = cvar.Cvar_Get ("lookstrafe", "0", shared.CVAR_ARCHIVE)
	sensitivity = cvar.Cvar_Get ("sensitivity", "3", shared.CVAR_ARCHIVE)
	
	m_pitch = cvar.Cvar_Get ("m_pitch", "0.022", shared.CVAR_ARCHIVE)
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
	info_password = cvar.Cvar_Get ("password", "", shared.CVAR_USERINFO)
	info_spectator = cvar.Cvar_Get ("spectator", "0", shared.CVAR_USERINFO)
	name = cvar.Cvar_Get ("name", "unnamed", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	skin = cvar.Cvar_Get ("skin", "male/grunt", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	rate = cvar.Cvar_Get ("rate", "25000", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE);	# FIXME
	msg = cvar.Cvar_Get ("msg", "1", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	hand = cvar.Cvar_Get ("hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	fov = cvar.Cvar_Get ("fov", "90", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	gender = cvar.Cvar_Get ("gender", "male", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	gender_auto = cvar.Cvar_Get ("gender_auto", "1", shared.CVAR_ARCHIVE)
	gender.modified = False # clear this so we know when user sets it manually

	cl_vwep = cvar.Cvar_Get ("cl_vwep", "1", shared.CVAR_ARCHIVE)

	"""
	//
	// register our commands
	//
	"""
	cmdparser.Cmd_AddCommand ("cmd", cl_network.CL_ForwardToServer_f)
	cmdparser.Cmd_AddCommand ("pause", CL_Pause_f)
	cmdparser.Cmd_AddCommand ("pingservers", cl_network.CL_PingServers_f)
	cmdparser.Cmd_AddCommand ("skins", CL_Skins_f)
	cmdparser.Cmd_AddCommand ("userinfo", CL_Userinfo_f);
	cmdparser.Cmd_AddCommand ("snd_restart", CL_Snd_Restart_f);

	cmdparser.Cmd_AddCommand ("changing", cl_network.CL_Changing_f)
	cmdparser.Cmd_AddCommand ("disconnect", cl_network.CL_Disconnect_f)
	cmdparser.Cmd_AddCommand ("record", CL_Record_f)
	cmdparser.Cmd_AddCommand ("stop", CL_Stop_f)
	cmdparser.Cmd_AddCommand ("quit", CL_Quit_f)
	
	cmdparser.Cmd_AddCommand ("connect", cl_network.CL_Connect_f)
	cmdparser.Cmd_AddCommand ("reconnect", cl_network.CL_Reconnect_f)

	cmdparser.Cmd_AddCommand ("rcon", cl_network.CL_Rcon_f)

 	## Cmd_AddCommand ("packet", CL_Packet_f); # this is dangerous to leave in

	cmdparser.Cmd_AddCommand ("setenv", CL_Setenv_f )

	cmdparser.Cmd_AddCommand ("precache", CL_Precache_f)

	cmdparser.Cmd_AddCommand ("download", cl_download.CL_Download_f)
	#
	# forward to server commands
	#
	# the only thing this does is allow command completion
	# to work -- all unknown commands are automatically
	# forwarded to the server
	cmdparser.Cmd_AddCommand ("wave", None)
	cmdparser.Cmd_AddCommand ("inven", None)
	cmdparser.Cmd_AddCommand ("kill", None)
	cmdparser.Cmd_AddCommand ("use", None)
	cmdparser.Cmd_AddCommand ("drop", None)
	cmdparser.Cmd_AddCommand ("say", None)
	cmdparser.Cmd_AddCommand ("say_team", None)
	cmdparser.Cmd_AddCommand ("info", None)
	cmdparser.Cmd_AddCommand ("prog", None)
	cmdparser.Cmd_AddCommand ("give", None)
	cmdparser.Cmd_AddCommand ("god", None)
	cmdparser.Cmd_AddCommand ("notarget", None)
	cmdparser.Cmd_AddCommand ("noclip", None)
	cmdparser.Cmd_AddCommand ("invuse", None)
	cmdparser.Cmd_AddCommand ("invprev", None)
	cmdparser.Cmd_AddCommand ("invnext", None)
	cmdparser.Cmd_AddCommand ("invdrop", None)
	cmdparser.Cmd_AddCommand ("weapnext", None)
	cmdparser.Cmd_AddCommand ("weapprev", None)


"""
===============
CL_WriteConfiguration

Writes key bindings and archived cvars to config.cfg
===============
"""
def CL_WriteConfiguration ():

	#FILE	*f;
	#char	path[MAX_QPATH];

	if cls.state == client_h.connstate_t.ca_uninitialized:
		return

	path = os.path.join(filesystem.FS_Gamedir(), "config.cfg")

	try:
		f = open (path, "w")
	except:
		clientserver.Com_Printf ("Couldn't write config.cfg.\n")
		return
	
	f.write("// generated by quake, do not modify\n")
	cl_keyboard.Key_WriteBindings (f)
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

	maxclients = cl.configstrings[shared.CS_MAXCLIENTS]
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
	
	# get new key events
	sys_linux.Sys_SendKeyEvents ()

	# allow mice or other external controllers to add commands
	vid_so.IN_Commands ()

	# process console commands
	cmdparser.Cbuf_Execute ()

	# fix any cheating cvars
	CL_FixCvarCheats ()

	# send intentions now
	cl_input.CL_SendCmd ()

	# resend a connection request if necessary
	cl_network.CL_CheckForResend ()


"""
static void
CL_UpdateWindowedMouse(void)
{
	if (cls.disable_screen)
	{
		return;
	}

	if (cls.key_dest == key_menu || cls.key_dest == key_console ||
		(cls.key_dest == key_game && (cls.state != ca_active || !cl.refresh_prepped)))
	{
		if (windowed_mouse->value)
		{
			Cvar_SetValue("windowed_mouse", 0);
		}
	}
	else
	{
		if (!windowed_mouse->value)
		{
			Cvar_SetValue("windowed_mouse", 1);
		}
	}
}
"""

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

	if frame.dedicated.value != 0:
		return

	extratime += msec
	
	if not int(cl_timedemo.value):
	
		if cls.state == client_h.connstate_t.ca_connected and extratime < 100:
			return			# don't flood packets out while connecting
		if extratime < 1000.0/int(cl_maxfps.value):
			return			# framerate is too high
	
	# let the mouse activate or deactivate
	vid_so.IN_Frame ()

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
	cl_network.CL_ReadPackets ()

	# send a new command message to the server
	CL_SendCommand ()

	# predict all unacknowledged movements
	cl_prediction.CL_PredictMovement ()

	# allow rendering DLL change
	vid_so.VID_CheckChanges ()
	
	if not cl.refresh_prepped and cls.state == client_h.connstate_t.ca_active:
		cl_view.CL_PrepRefresh ()

	# update the screen
	if frame.host_speeds.value:
		frame.time_before_ref = q_shlinux.Sys_Milliseconds ()
	cl_screen.SCR_UpdateScreen ()
	if frame.host_speeds.value:
		frame.time_after_ref = q_shlinux.Sys_Milliseconds ()

	# update audio
	snd_dma.S_Update (cl.refdef.vieworg, cl.v_forward, cl.v_right, cl.v_up)

	cd_linux.CDAudio_Update()

	# advance local effects for next frame
	cl_fx.CL_RunDLights ()
	cl_fx.CL_RunLightStyles ()
	cl_cin.SCR_RunCinematic ()
	cl_screen.SCR_RunConsole ()

	cls.framecount+=1


	# =============================================================================
# CL_Init
# =============================================================================
def CL_Init ():

	if frame.dedicated.value:
		return		# nothing running on the client

	# all archived variables will now be loaded

	cl_console.Con_Init ()

	#if defined __linux__ || defined __sgi
	snd_dma.S_Init ()
	vid_so.VID_Init ()
	#else
	#VID_Init ();
	#S_Init ();	// sound must be initialized after window is created
	#endif

	cl_view.V_Init ()
	szone.SZ_Init(netchan.net_message, common_h.MAX_MSGLEN)
	menu.M_Init ()

	cl_screen.SCR_Init ()
	cls.disable_screen = True	# don't draw yet
	
	#CDAudio_Init ();
	CL_InitLocal ()
	vid_so.IN_Init ()

	## Cbuf_AddText ("exec autoexec.cfg\n");	# Q2PORT: Yamagi execs autoexec.cfg in Qcommon_ExecConfigs
	cmdparser.Cbuf_Execute ()


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
	vid_so.IN_Shutdown ()
	vid_so.VID_Shutdown()
