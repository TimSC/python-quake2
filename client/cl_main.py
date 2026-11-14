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

from client.input import sdl2

from client.sound import ogg
from client.sound.header import vorbis

import os
import struct
from client import cl_view, cl_input, cl_cin, cl_parse
from client.sound import sound as sound_c
from backends.unix import system, network
from linux import cd_linux
from client.vid import vid
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
from client import cl_effects
from client import cl_lights
from client import cl_tempentities
from client.menu import menu
from client.curl import download

"""
#include <errno.h>
#include "header/client.h"
#include "input/header/input.h"
"""

adr0, adr1, adr2, adr3, adr4, adr5, adr6, adr7, adr8 = None, None, None, None, None, None, None, None, None

cl_stereo_separation = None #cvar_t *
cl_stereo = None #cvar_t *

cl_add_blend, cl_add_lights, cl_add_particles, cl_add_entities = None, None, None, None
cl_gun, cl_footsteps, cl_noskins, cl_autoskins, cl_predict = None, None, None, None, None

cl_shownet, cl_showmiss, cl_showclamp, cl_timeout, cl_paused = None, None, None, None, None
rcon_client_password, rcon_address, cl_lightlevel = None, None, None
info_password, info_spectator, name, skin, rate, msg, hand, fov, gender, gender_auto, cl_vwep = None, None, None, None, None, None, None, None, None, None, None

cls = client_h.client_static_t()

cl = client_h.client_state_t()


# initialize the entities array to at least this many entities
ALLOC_ENTITIES_MIN = 32

cl_entities = [] #centity_t *, grown by CL_AllocEntity
cl_numentities = 0 #int


cl_parse_entities = [] #entity_state_t[MAX_PARSE_ENTITIES]
for i in range(client_h.MAX_PARSE_ENTITIES):
	cl_parse_entities.append(shared.entity_state_t())

# Evil hack against too many power screen and power
# shield impact sounds. For example if the player
# fires his shotgun onto a Brain.
num_power_sounds = 0 #int

# Used to communicate if we entered paused mode
# during server connect or if we were already in
# it.
paused_at_load = False #qboolean
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
def CL_ClearEntities(): #void

	global cl_entities, cl_numentities

	if cl_entities:

		cl_entities = [] # Z_Free(cl_entities); cl_entities = NULL;


	cl_numentities = 0


def CL_AllocEntity(entnum: int): #int (returns centity_t *)

	global cl_entities, cl_numentities

	"""
	int nextpow2;
	"""

	if (entnum < 0) or (entnum > client_h.MAX_CL_ENTNUM):

		return None


	if entnum >= cl_numentities:

		nextpow2 = int(shared_c.NextPow2gt(entnum)) if (cl_numentities or (entnum >= ALLOC_ENTITIES_MIN)) else \
			ALLOC_ENTITIES_MIN

		# cl_entities = Z_Realloc(cl_entities, nextpow2 * sizeof(centity_t));
		while len(cl_entities) < nextpow2:

			cl_entities.append(client_h.centity_t())


		cl_numentities = nextpow2


	return cl_entities[entnum]


"""
 * Returns max clients in the current session
 * Returns 1 if the value is bad (<= 0) or the configstring is blank
"""
def CL_MaxClients()->int: #void (returns int)

	"""
	int i = 0;
	"""

	i = shared_c.atoi(cl.configstrings[shared.CS_MAXCLIENTS]) # sscanf(cl.configstrings[CS_MAXCLIENTS], " %i ", &i);

	if i > shared.MAX_CLIENTS:

		return shared.MAX_CLIENTS


	return 1 if i <= 0 else i

"""
// cl_main.c  -- client main loop

#include "client.h"
"""

cl_showfps = None #cvar_t *
cl_showspeed = None #cvar_t *
cl_kickangles = None #cvar_t *
cl_laseralpha = None #cvar_t *
cl_nodownload_list = None #cvar_t *
cl_loadpaused = None #cvar_t *
cl_audiopaused = None #cvar_t *
cl_unpaused_scvis = None #cvar_t *
cl_r1q2_lightstyle = None #cvar_t *
cl_limitsparksounds = None #cvar_t *
horplus = None #cvar_t *
windowed_mouse = None #cvar_t *
gl1_stereo = None #cvar_t *
gl1_stereo_separation = None #cvar_t *
gl1_stereo_convergence = None #cvar_t *

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
	char name[MAX_OSPATH];
	byte buf_data[MAX_MSGLEN];
	sizebuf_t buf;
	int i;
	int len;
	entity_state_t *ent;
	"""
	buf = common_h.sizebuf_t()

	if cmdparser.Cmd_Argc() != 2:
	
		clientserver.Com_Printf ("record <demoname>\n")
		return
	
	if cls.demorecording:
	
		clientserver.Com_Printf ("Already recording.\n")
		return

	# Q2PORT: fix, the name could leave the game directory (a server can stuff
	# this command)
	if ".." in cmdparser.Cmd_Argv(1):

		clientserver.Com_Printf ("Refusing to record to a path with ..\n")
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
		cls.demofile = open (name, "wb") # Q_fopen (name, "wb")
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
	movemsg.MSG_WriteString (buf, cl.gamedir.encode('latin-1', 'replace')) # Q2PORT: latin-1, the C's strings are bytes (ascii failed on others)
	movemsg.MSG_WriteShort (buf, cl.playernum)

	movemsg.MSG_WriteString (buf, cl.configstrings[shared.CS_NAME].encode('latin-1', 'replace')) # Q2PORT: latin-1, the C's strings are bytes (ascii failed on others)

	# configstrings
	for i in range(shared.MAX_CONFIGSTRINGS):
	
		if cl.configstrings[i]:
		
			if buf.cursize + len (cl.configstrings[i]) + 32 > buf.maxsize:
				# write it out
				cls.demofile.write (struct.pack("<i", buf.cursize)) # len = LittleLong (buf.cursize); fwrite (&len, 4, 1, cls.demofile);
				cls.demofile.write (buf.data[:buf.cursize])
				buf.cursize = 0
			
			movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_configstring.value)
			movemsg.MSG_WriteConfigString (buf, i, cl.configstrings[i])
		
	# baselines
	for i in range(cl_numentities):
	
		ent = cl_entities[i].baseline
		if not ent.modelindex:
			continue

		if buf.cursize + 64 > buf.maxsize:
			# write it out
			cls.demofile.write (struct.pack("<i", buf.cursize))
			cls.demofile.write (buf.data[:buf.cursize])
			buf.cursize = 0
		
		movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_spawnbaseline.value)		
		movemsg.MSG_WriteDeltaEntity (None, cl_entities[i].baseline, buf, True, True)
	
	movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_stufftext.value)
	movemsg.MSG_WriteString (buf, b"precache\n")

	# write it to the demo file

	cls.demofile.write (struct.pack("<i", buf.cursize))
	cls.demofile.write (buf.data[:buf.cursize])

	

def CL_Setenv_f(): # (static)

	"""
	int argc = Cmd_Argc();
	"""
	argc = cmdparser.Cmd_Argc()

	if argc > 2:

		#char buffer[1000];
		buffer = [None] * 1000
		#int i;
		buffer = cmdparser.Cmd_Argv(1) # Q_strlcpy
		buffer += "=" # Q_strlcat
		for i in range(2, argc):

			buffer += cmdparser.Cmd_Argv(i) # Q_strlcat
			buffer += " " # Q_strlcat


		if os.putenv(buffer):

			clientserver.Com_Printf("%s: putenv is failed: %s\n", "CL_Setenv_f", os.strerror(network.errno))


	elif argc == 2:

		#char *env = getenv(Cmd_Argv(1));
		env = os.getenv(cmdparser.Cmd_Argv(1))
		if env:

			clientserver.Com_Printf("%s=%s\n", cmdparser.Cmd_Argv(1), env)

		else:

			clientserver.Com_Printf("%s undefined\n", cmdparser.Cmd_Argv(1))

	


"""
/*
==================
CL_Pause_f
==================
"""
def CL_Pause_f(): # (static)

	# never pause in multiplayer
	if (cvar.Cvar_VariableValue("maxclients") > 1) or not clientserver.Com_ServerState():

		cvar.Cvar_SetValue("paused", 0)
		return


	cvar.Cvar_SetValue("paused", not cl_paused.value)
	if cvar.Cvar_VariableValue("ogg_pausewithgame") == 1 and ogg.OGG_Status() == vorbis.PAUSE and cl_paused.value == 0:

		# play music
		cmdparser.Cbuf_AddText("ogg toggle\n")

	elif cvar.Cvar_VariableValue("ogg_pausewithgame") == 1 and ogg.OGG_Status() == vorbis.PLAY and cl_paused.value == 1:

		# pause music
		cmdparser.Cbuf_AddText("ogg toggle\n")


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
def CL_ClearState(): #void

	global cl

	sound_c.S_StopAllSounds()
	cl_effects.CL_ClearEffects()
	cl_tempentities.CL_ClearTEnts()

	# wipe the entire cl structure
	cl.reset() # memset(&cl, 0, sizeof(cl));
	CL_ClearEntities()

	szone.SZ_Clear(cls.netchan.message)



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
def CL_Skins_f(): # (static)

	"""
	int i;
	"""

	for i in range(shared.MAX_CLIENTS):

		if not cl.configstrings[shared.CS_PLAYERSKINS + i]: # !cl.configstrings[CS_PLAYERSKINS + i][0]

			continue


		clientserver.Com_Printf("client %i: %s\n", i, cl.configstrings[shared.CS_PLAYERSKINS + i])
		cl_screen.SCR_UpdateScreen()
		sdl2.IN_Update()
		# pump message loop
		cl_parse.CL_ParseClientinfo(i)


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
		rx, netchan.net_from = network.NET_GetPacket (common_h.netsrc_t.NS_CLIENT, netchan.net_from, netchan.net_message)
		if not rx:
			break
	
		clientserver.Com_Printf ("dumnping a packet\n")

def CL_FixUpGender(): #void

	"""
	char *p;
	char sk[80];
	"""

	if gender_auto.value:

		if gender.modified:

			# was set directly, don't override the user
			gender.modified = False
			return


		sk = skin.string[:79] # Q_strlcpy(sk, skin->string, sizeof(sk));

		p = sk.find('/')
		if p >= 0: # (p = strchr(sk, '/')) != NULL

			sk = sk[:p] # *p = 0;


		if (shared_c.Q_stricmp(sk, "male") == 0) or (shared_c.Q_stricmp(sk, "cyborg") == 0):

			cvar.Cvar_Set("gender", "male")

		elif (shared_c.Q_stricmp(sk, "female") == 0) or (shared_c.Q_stricmp(sk, "crackhor") == 0):

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
def CL_Snd_Restart_f(): #

	ogg.OGG_SaveState()
	sound_c.S_Shutdown()
	sound_c.S_Init()
	cl_parse.CL_RegisterSounds()
	ogg.OGG_InitTrackList()
	ogg.OGG_RecoverState()


def CL_ResetPrecacheCheck(): #void

	global precache_check, precache_model, precache_model_skin

	precache_check = shared.CS_MODELS
	precache_model = None
	precache_model_skin = 0


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
def CL_Precache_f(): #void

	global precache_check, precache_spawncount, precache_model, precache_model_skin

	# Yet another hack to let old demos work
	if cmdparser.Cmd_Argc() < 2:

		"""
		unsigned map_checksum;    /* for detecting cheater maps */
		"""

		_, map_checksum = collision.CM_LoadMap(cl.configstrings[shared.CS_MODELS + 1], True)
		cl_parse.CL_RegisterSounds()
		cl_view.CL_PrepRefresh()
		return


	precache_check = shared.CS_MODELS

	precache_spawncount = shared_c.atoi(cmdparser.Cmd_Argv(1)) # (int)strtol(Cmd_Argv(1), (char **)NULL, 10)
	precache_model = None
	precache_model_skin = 0

	cl_download.CL_RequestNextDownload()



def CL_CurrentMap_f(): # (static)

	clientserver.Com_Printf("%s\n", cl.configstrings[shared.CS_MODELS + 1])

"""
=================
CL_InitLocal
=================
"""
def CL_InitLocal(): # (static)
	global cl_add_blend, cl_add_entities, cl_add_lights, cl_add_particles, cl_audiopaused, cl_footsteps, cl_gun, cl_kickangles, cl_laseralpha, cl_lightlevel, cl_limitsparksounds, cl_loadpaused, cl_nodownload_list, cl_noskins, cl_paused, cl_predict, cl_r1q2_lightstyle, cl_showclamp, cl_showfps, cl_showmiss, cl_shownet, cl_showspeed, cl_timeout, cl_unpaused_scvis, cl_vwep, fov, gender, gender_auto, gl1_stereo, gl1_stereo_convergence, gl1_stereo_separation, hand, horplus, name, rate, rcon_address, rcon_client_password, skin, windowed_mouse

	cls.state = client_h.connstate_t.ca_disconnected
	cls.realtime = system.Sys_Milliseconds()
	cl_input.CL_InitInput()
	# register our variables
	cl_cin.cin_force43 = cvar.Cvar_Get("cin_force43", "1", shared.CVAR_ARCHIVE)
	cl_add_blend = cvar.Cvar_Get("cl_blend", "1", 0)
	cl_add_lights = cvar.Cvar_Get("cl_lights", "1", 0)
	cl_add_particles = cvar.Cvar_Get("cl_particles", "1", 0)
	cl_add_entities = cvar.Cvar_Get("cl_entities", "1", 0)
	cl_kickangles = cvar.Cvar_Get("cl_kickangles", "1", 0)
	cl_gun = cvar.Cvar_Get("cl_gun", "2", shared.CVAR_ARCHIVE)
	cl_footsteps = cvar.Cvar_Get("cl_footsteps", "1", 0)
	cl_noskins = cvar.Cvar_Get("cl_noskins", "0", 0)
	cl_predict = cvar.Cvar_Get("cl_predict", "1", 0)
	cl_showfps = cvar.Cvar_Get("cl_showfps", "0", shared.CVAR_ARCHIVE)
	cl_showspeed = cvar.Cvar_Get("cl_showspeed", "0", shared.CVAR_ARCHIVE)
	cl_laseralpha = cvar.Cvar_Get("cl_laseralpha", "0.3", 0)
	cl_nodownload_list = cvar.Cvar_Get("cl_nodownload_list", "", shared.CVAR_ARCHIVE)
	cl_input.cl_upspeed = cvar.Cvar_Get("cl_upspeed", "200", 0)
	cl_input.cl_forwardspeed = cvar.Cvar_Get("cl_forwardspeed", "200", 0)
	cl_input.cl_sidespeed = cvar.Cvar_Get("cl_sidespeed", "200", 0)
	cl_input.cl_yawspeed = cvar.Cvar_Get("cl_yawspeed", "140", 0)
	cl_input.cl_pitchspeed = cvar.Cvar_Get("cl_pitchspeed", "150", 0)
	cl_input.cl_anglespeedkey = cvar.Cvar_Get("cl_anglespeedkey", "1.5", 0)
	cl_input.cl_run = cvar.Cvar_Get("cl_run", "0", shared.CVAR_ARCHIVE)
	cl_shownet = cvar.Cvar_Get("cl_shownet", "0", 0)
	cl_showmiss = cvar.Cvar_Get("cl_showmiss", "0", 0)
	cl_showclamp = cvar.Cvar_Get("showclamp", "0", 0)
	cl_timeout = cvar.Cvar_Get("cl_timeout", "120", 0)
	cl_paused = cvar.Cvar_Get("paused", "0", 0)
	cl_loadpaused = cvar.Cvar_Get("cl_loadpaused", "1", shared.CVAR_ARCHIVE)
	cl_audiopaused = cvar.Cvar_Get("cl_audiopaused", "1", shared.CVAR_ARCHIVE)
	cl_unpaused_scvis = cvar.Cvar_Get("cl_unpaused_scvis", "1", shared.CVAR_ARCHIVE)
	gl1_stereo = cvar.Cvar_Get("gl1_stereo", "0", shared.CVAR_ARCHIVE)
	gl1_stereo_separation = cvar.Cvar_Get("gl1_stereo_separation", "1", shared.CVAR_ARCHIVE)
	gl1_stereo_convergence = cvar.Cvar_Get("gl1_stereo_convergence", "1.4", shared.CVAR_ARCHIVE)
	rcon_client_password = cvar.Cvar_Get("rcon_password", "", 0)
	rcon_address = cvar.Cvar_Get("rcon_address", "", 0)
	cl_lightlevel = cvar.Cvar_Get("r_lightlevel", "0", 0)
	cl_r1q2_lightstyle = cvar.Cvar_Get("cl_r1q2_lightstyle", "1", shared.CVAR_ARCHIVE)
	cl_limitsparksounds = cvar.Cvar_Get("cl_limitsparksounds", "0", shared.CVAR_ARCHIVE)
	# userinfo
	name = cvar.Cvar_Get("name", "unnamed", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	skin = cvar.Cvar_Get("skin", "male/grunt", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	rate = cvar.Cvar_Get("rate", "8000", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	hand = cvar.Cvar_Get("hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	fov = cvar.Cvar_Get("fov", "90", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	horplus = cvar.Cvar_Get("horplus", "1", shared.CVAR_ARCHIVE)
	windowed_mouse = cvar.Cvar_Get("windowed_mouse", "1", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	gender = cvar.Cvar_Get("gender", "male", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	gender_auto = cvar.Cvar_Get("gender_auto", "1", shared.CVAR_ARCHIVE)
	gender.modified = False
	# USERINFO cvars are special, they just need to be registered
	cvar.Cvar_Get("password", "", shared.CVAR_USERINFO)
	cvar.Cvar_Get("spectator", "0", shared.CVAR_USERINFO)
	cl_vwep = cvar.Cvar_Get("cl_vwep", "1", shared.CVAR_ARCHIVE)
	# #ifdef USE_CURL
	download.cl_http_verifypeer = cvar.Cvar_Get("cl_http_verifypeer", "1", shared.CVAR_ARCHIVE)
	download.cl_http_proxy = cvar.Cvar_Get("cl_http_proxy", "", shared.CVAR_ARCHIVE)
	download.cl_http_filelists = cvar.Cvar_Get("cl_http_filelists", "1", 0)
	download.cl_http_downloads = cvar.Cvar_Get("cl_http_downloads", "1", shared.CVAR_ARCHIVE)
	download.cl_http_max_connections = cvar.Cvar_Get("cl_http_max_connections", "4", 0)
	download.cl_http_show_dw_progress = cvar.Cvar_Get("cl_http_show_dw_progress", "0", 0)
	download.cl_http_bw_limit_rate = cvar.Cvar_Get("cl_http_bw_limit_rate", "0", 0)
	download.cl_http_bw_limit_tmout = cvar.Cvar_Get("cl_http_bw_limit_tmout", "0", 0)
	# #endif
	# register our commands
	cmdparser.Cmd_AddCommand("cmd", cl_network.CL_ForwardToServer_f)
	cmdparser.Cmd_AddCommand("pause", CL_Pause_f)
	cmdparser.Cmd_AddCommand("pingservers", cl_network.CL_PingServers_f)
	cmdparser.Cmd_AddCommand("skins", CL_Skins_f)
	cmdparser.Cmd_AddCommand("userinfo", CL_Userinfo_f)
	cmdparser.Cmd_AddCommand("snd_restart", CL_Snd_Restart_f)
	cmdparser.Cmd_AddCommand("changing", cl_network.CL_Changing_f)
	cmdparser.Cmd_AddCommand("disconnect", cl_network.CL_Disconnect_f)
	cmdparser.Cmd_AddCommand("record", CL_Record_f)
	cmdparser.Cmd_AddCommand("stop", CL_Stop_f)
	cmdparser.Cmd_AddCommand("quit", CL_Quit_f)
	cmdparser.Cmd_AddCommand("connect", cl_network.CL_Connect_f)
	cmdparser.Cmd_AddCommand("reconnect", cl_network.CL_Reconnect_f)
	cmdparser.Cmd_AddCommand("rcon", cl_network.CL_Rcon_f)
	cmdparser.Cmd_AddCommand("packet", cl_network.CL_Packet_f)
	cmdparser.Cmd_AddCommand("setenv", CL_Setenv_f)
	cmdparser.Cmd_AddCommand("precache", CL_Precache_f)
	cmdparser.Cmd_AddCommand("download", cl_download.CL_Download_f)
	cmdparser.Cmd_AddCommand("currentmap", CL_CurrentMap_f)
	# forward to server commands
	# the only thing this does is allow command completion
	# to work -- all unknown commands are automatically
	# forwarded to the server
	cmdparser.Cmd_AddCommand("wave", None)
	cmdparser.Cmd_AddCommand("inven", None)
	cmdparser.Cmd_AddCommand("kill", None)
	cmdparser.Cmd_AddCommand("use", None)
	cmdparser.Cmd_AddCommand("drop", None)
	cmdparser.Cmd_AddCommand("say", None)
	cmdparser.Cmd_AddCommand("say_team", None)
	cmdparser.Cmd_AddCommand("info", None)
	cmdparser.Cmd_AddCommand("prog", None)
	cmdparser.Cmd_AddCommand("give", None)
	cmdparser.Cmd_AddCommand("god", None)
	cmdparser.Cmd_AddCommand("notarget", None)
	cmdparser.Cmd_AddCommand("noclip", None)
	cmdparser.Cmd_AddCommand("invuse", None)
	cmdparser.Cmd_AddCommand("invprev", None)
	cmdparser.Cmd_AddCommand("invnext", None)
	cmdparser.Cmd_AddCommand("invdrop", None)
	cmdparser.Cmd_AddCommand("weapnext", None)
	cmdparser.Cmd_AddCommand("weapprev", None)
	cmdparser.Cmd_AddCommand("listentities", None)
	cmdparser.Cmd_AddCommand("teleport", None)
	cmdparser.Cmd_AddCommand("spawnentity", None)
	cmdparser.Cmd_AddCommand("spawnonstart", None)
	cmdparser.Cmd_AddCommand("cycleweap", None)


"""
===============
CL_WriteConfiguration

Writes key bindings and archived cvars to config.cfg
===============
"""
def CL_WriteConfiguration(): #void

	"""
	FILE *f;
	char path[MAX_OSPATH];
	"""

	if cls.state == client_h.connstate_t.ca_uninitialized:

		return


	path = "{}/config.cfg".format(filesystem.FS_Gamedir())[:shared.MAX_OSPATH - 1] # Com_sprintf

	try:

		f = open(path, "w") # Q_fopen(path, "w")

	except OSError:

		clientserver.Com_Printf("Couldn't write config.cfg.\n")
		return


	f.write("// generated by quake, do not modify\n") # fprintf

	cl_keyboard.Key_WriteBindings(f)

	f.flush()
	f.close()

	cvar.Cvar_WriteVariables(path)



class cheatvar_t(object):

	def __init__(self, name=None, value=None):

		self.name = name #char *
		self.value = value #char *
		self.var = None #cvar_t *

cheatvars = [ #cheatvar_t []
	cheatvar_t("timescale", "1"),
	cheatvar_t("timedemo", "0"),
	cheatvar_t("r_drawworld", "1"),
	cheatvar_t("cl_testlights", "0"),
	cheatvar_t("r_fullbright", "0"),
	cheatvar_t("gl_drawflat", "0"),
	cheatvar_t("paused", "0"),
	cheatvar_t("fixedtime", "0"),
	cheatvar_t("sw_draworder", "0"),
	cheatvar_t("r_lightmap", "0"),
	cheatvar_t("gl_saturatelighting", "0"),
	cheatvar_t("cl_kickangles", "1"),
	cheatvar_t("g_footsteps", "1"),
	cheatvar_t("g_machinegun_norecoil", "0"),
	cheatvar_t("g_swap_speed", "1"),
	cheatvar_t(None, None)
]

numcheatvars = 0 #static int

def CL_FixCvarCheats(): # (static)

	"""
	int i;
	cheatvar_t *var;
	"""
	global numcheatvars

	if (cl.configstrings[shared.CS_MAXCLIENTS] == "1" or
		not cl.configstrings[shared.CS_MAXCLIENTS]):

		return # single player can cheat


	# find all the cvars if we haven't done it yet
	if not numcheatvars:

		while cheatvars[numcheatvars].name:

			cheatvars[numcheatvars].var = cvar.Cvar_Get(cheatvars[numcheatvars].name,
					cheatvars[numcheatvars].value, 0)
			numcheatvars += 1



	# make sure they are all set to the proper values
	for i in range(numcheatvars):

		var = cheatvars[i]
		if var.var.string != var.value:

			cvar.Cvar_Set(var.name, var.value)




def CL_UpdateWindowedMouse(): # (static)

	if cls.disable_screen:

		return


	if cls.key_dest == client_h.keydest_t.key_menu or cls.key_dest == client_h.keydest_t.key_console or (cls.key_dest == client_h.keydest_t.key_game and (cls.state != client_h.connstate_t.ca_active or not cl.refresh_prepped)):

		if windowed_mouse.value:

			cvar.Cvar_SetValue("windowed_mouse", 0)


	else:

		if not windowed_mouse.value:

			cvar.Cvar_SetValue("windowed_mouse", 1)

lasttimecalled = 0 #static int, in CL_Frame

def CL_Frame(packetdelta: int, renderdelta: int, timedelta: int, packetframe: bool, renderframe: bool):
	#int, int, int, qboolean, qboolean

	global lasttimecalled, num_power_sounds

	#static int lasttimecalled;

	# Dedicated?
	if frame.dedicated.value:

		return


	# Calculate simulation time.
	cls.nframetime = packetdelta / 1000000.0
	cls.rframetime = renderdelta / 1000000.0
	cls.realtime = frame.curtime
	cl.time += int(timedelta / 1000)

	# Don't extrapolate too far ahead.
	if cls.nframetime > 0.5:

		cls.nframetime = 0.5


	if cls.rframetime > 0.5:

		cls.rframetime = 0.5


	# if in the debugger last frame, don't timeout.
	if timedelta > 5000000:

		cls.netchan.last_received = system.Sys_Milliseconds()


	# Reset power shield / power screen sound counter.
	num_power_sounds = 0

	if not frame.cl_timedemo.value:

		# Don't throttle too much when connecting / loading.
		if (cls.state == client_h.connstate_t.ca_connected) and (packetdelta > 100000):

			packetframe = True



	# Run HTTP downloads more often while connecting.
	# #ifdef USE_CURL
	if cls.state == client_h.connstate_t.ca_connected:

		download.CL_RunHTTPDownloads()

	# #endif

	# Update input stuff.
	if packetframe or renderframe:

		cl_network.CL_ReadPackets()
		CL_UpdateWindowedMouse()
		sdl2.IN_Update()
		cmdparser.Cbuf_Execute()
		CL_FixCvarCheats()

		if cls.state.value > client_h.connstate_t.ca_connecting.value:

			cl_input.CL_RefreshCmd()

		else:

			cl_input.CL_RefreshMove()



	if cls.forcePacket or cvar.userinfo_modified:

		packetframe = True
		cls.forcePacket = False


	if packetframe:

		cl_input.CL_SendCmd()
		cl_network.CL_CheckForResend()

		# Run HTTP downloads during game.
		# #ifdef USE_CURL
		download.CL_RunHTTPDownloads()
		# #endif


	if renderframe:

		vid.VID_CheckChanges()
		cl_prediction.CL_PredictMovement()

		if not cl.refresh_prepped and (cls.state == client_h.connstate_t.ca_active):

			cl_view.CL_PrepRefresh()


		# update the screen
		if frame.host_speeds.value:

			frame.time_before_ref = system.Sys_Milliseconds()


		cl_screen.SCR_UpdateScreen()

		if frame.host_speeds.value:

			frame.time_after_ref = system.Sys_Milliseconds()


		# update audio
		sound_c.S_Update(cl.refdef.vieworg, cl.v_forward, cl.v_right, cl.v_up)

		# advance local effects for next frame
		cl_lights.CL_RunDLights()
		cl_lights.CL_RunLightStyles()
		cl_cin.SCR_RunCinematic()
		cl_screen.SCR_RunConsole()

		# Update framecounter
		cls.framecount += 1

		if frame.log_stats.value:

			if cls.state == client_h.connstate_t.ca_active:

				if not lasttimecalled:

					lasttimecalled = system.Sys_Milliseconds()

					if frame.log_stats_file:

						frame.log_stats_file.write("0\n")



				else:

					now = system.Sys_Milliseconds()

					if frame.log_stats_file:

						frame.log_stats_file.write("{}\n".format(now - lasttimecalled))


					lasttimecalled = now


def CL_Init(): #void

	if frame.dedicated.value:

		return # nothing running on the client


	# all archived variables will now be loaded
	cl_console.Con_Init()

	sound_c.S_Init()

	cl_screen.SCR_Init()

	vid.VID_Init()

	sdl2.IN_Init()

	cl_view.V_Init()

	szone.SZ_Init(netchan.net_message, common_h.MAX_MSGLEN) # net_message.data = net_message_buffer;

	#net_message.maxsize = sizeof(net_message_buffer);

	menu.M_Init()

	# #ifdef USE_CURL
	download.CL_InitHTTPDownloads()
	# #endif

	cls.disable_screen = True # don't draw yet

	CL_InitLocal()

	cmdparser.Cbuf_Execute()

	cl_keyboard.Key_ReadConsoleHistory()



isdown = False #static qboolean, in CL_Shutdown

def CL_Shutdown(): #void

	global isdown

	#static qboolean isdown = false;

	if isdown:

		print("recursive shutdown")
		return


	isdown = True

	# #ifdef USE_CURL
	download.CL_HTTP_Cleanup(True)
	# #endif

	CL_WriteConfiguration()

	cl_keyboard.Key_WriteConsoleHistory()

	ogg.OGG_Stop()

	sound_c.S_Shutdown()
	sdl2.IN_Shutdown()
	vid.VID_Shutdown()

	CL_ClearEntities()

