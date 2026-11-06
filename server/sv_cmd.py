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

Server commands received by clients. There are only two ways on which
those can be received. Typed via stdin into the server console or via
a network / internal communication datagram.

=======================================================================
"""
from __future__ import annotations

import struct
from linux import net_udp
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
from common import netchan
from server.header import server as server_h
from server import sv_game
from server import sv_init
from server import sv_main
from server import sv_save
from server import sv_send
from server import sv_user
from server import sv_save as server_sv_save

"""
#include "header/server.h"
"""

"""
#include "header/server.h"
"""

def SV_SetMaster_f ():

	#int i, slot

	# only dedicated servers send heartbeats
	if not frame.dedicated.value:
		clientserver.Com_Printf ("Only dedicated servers use masters.\n")
		return

	# make sure the server is listed public
	cvar.Cvar_Set ("public", "1")

	for i in range(1, server_h.MAX_MASTERS):
		sv_main.master_adr[i] = common_h.netadr_t()

	slot = 1		# slot 0 will always contain the id master
	for i in range(1, cmdparser.Cmd_Argc()):
		if slot == server_h.MAX_MASTERS:
			break

		if not net_udp.NET_StringToAdr (cmdparser.Cmd_Argv(i), sv_main.master_adr[i]):
			clientserver.Com_Printf ("Bad address: %s\n", cmdparser.Cmd_Argv(i))
			continue
		if sv_main.master_adr[slot].port == 0:
			sv_main.master_adr[slot].port = shared_c.BigShort (common_h.PORT_MASTER)

		clientserver.Com_Printf ("Master server at %s\n", net_udp.NET_AdrToString (sv_main.master_adr[slot]))

		clientserver.Com_Printf ("Sending a ping.\n")

		netchan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, sv_main.master_adr[slot], "ping")

		slot += 1

	sv_init.svs.last_heartbeat = -9999999
"""
/*
==================
SV_SetPlayer

Sets sv_client and sv_player to the player with idnum Cmd_Argv(1)
==================
*/
"""
def SV_SetPlayer ():

	#client_t *cl
	#int i, idnum
	#char *s

	if cmdparser.Cmd_Argc() < 2:
		return False

	s = cmdparser.Cmd_Argv(1)

	# numeric values are just slot numbers
	if s[0] >= '0' and s[0] <= '9':
		idnum = int(s)
		if idnum < 0 or idnum >= int(sv_main.maxclients.value):
			clientserver.Com_Printf ("Bad client slot: %i\n", idnum)
			return False

		sv_main.sv_client = sv_init.svs.clients[idnum]
		sv_user.sv_player = server_h.CL_EDICT(sv_main.sv_client)
		if sv_main.sv_client.state == server_h.client_state_t.cs_free:
			clientserver.Com_Printf ("Client %i is not active\n", idnum)
			return False
		return True

	# check for a name match
	for i in range(int(sv_main.maxclients.value)):
		cl = sv_init.svs.clients[i]
		if cl.state == server_h.client_state_t.cs_free:
			continue
		if cl.name == s:
			sv_main.sv_client = cl
			sv_user.sv_player = server_h.CL_EDICT(sv_main.sv_client)
			return True

	clientserver.Com_Printf ("Userid %s is not on the server\n", s)
	return False


"""
//=========================================================
/*
==================
SV_DemoMap_f

Puts the server in demo mode on a specific map/cinematic
==================
"""
def SV_DemoMap_f(): #void

	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("USAGE: demomap <demoname.dm2>\n")
		return


	sv_init.SV_Map(True, cmdparser.Cmd_Argv(1), False, False)

"""
==================
SV_GameMap_f

Saves the state of the map just being exited and goes to a new map.

If the initial character of the map string is '*', the next map is
in a new unit, so the current savegame directory is cleared of
map files.

Example:

*inter.cin+jail

Clears the archived maps, plays the inter.cin cinematic, then
goes to map jail.bsp.
==================
"""
def SV_GameMap_f(): #void

	"""
	char *map, mapvalue[MAX_QPATH];
	int i;
	edict_t *clent;
	"""

	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("USAGE: gamemap <map>\n")
		return


	if len(cmdparser.Cmd_Argv(1)) >= shared.MAX_QPATH:

		clientserver.Com_Printf("gamemap is too long\n")
		return


	clientserver.Com_DPrintf("%s(%s)\n", "SV_GameMap_f", cmdparser.Cmd_Argv(1))

	filesystem.FS_CreatePath("{}/save/current/".format(filesystem.FS_Gamedir()))

	# check for clearing the current savegame
	mapvalue = cmdparser.Cmd_Argv(1)
	map = mapvalue

	if map[:1] == '*':

		# wipe all the *.sav files
		sv_save.SV_WipeSavegame("current")

	else:

		# save the map just exited
		if sv_init.sv.state == server_h.server_state_t.ss_game:

			#bitlist_t savedInuse[BITLIST_SIZE(MAX_CLIENTS)];
			savedInuse = [False] * shared.MAX_CLIENTS

			# clear all the client inuse flags before saving so that
			# when the level is re-entered, the clients will spawn
			# at spawn points instead of occupying body shells
			for i in range(int(sv_main.maxclients.value)):

				clent = server_h.CLNUM_EDICT(i)

				if clent.inuse:

					savedInuse[i] = True


				clent.inuse = False


			sv_save.SV_WriteLevelFile()

			# we must restore these for clients to transfer over correctly
			for i in range(int(sv_main.maxclients.value)):

				server_h.CLNUM_EDICT(i).inuse = \
					True if savedInuse[i] else False




	# it's possible to start a map with the wrong case, e.g. "/map BASE1"
	# (even though the mapfile is maps/base1.bsp)
	# however, that will screw up the corresponding savegame (for going back to last map)
	# which will then be called baseq2/save/bla/BASE1.sav - because when going back to the
	# map from base2 it will look for .../base1.sav
	# so try to fix the mapname here
	# NOTE: does not properly handle all variations like base2$base1 and whatever else we forgot
	#       but so far we haven't run into problems with that anyway
	#char mapPath[MAX_QPATH];
	haveStar = (map[:1] == '*')
	mapPath = "maps/{}.bsp".format(map[1:] if haveStar else map)

	size, f = filesystem.FS_FOpenFile(mapPath, False)
	if size >= 0:

		realMapPath = filesystem.FS_GetFilenameForHandle(f)
		# now mapPath contains the fixed path
		mapPath = realMapPath[:shared.MAX_QPATH - 1]
		filesystem.FS_FCloseFile(f)

		map = mapPath[4:] # skip "maps"
		if haveStar:
			map = '*' + map[1:] # restore it (=> replace '/' by '*')
		else:
			map = map[1:] # skip '/'

		map = map[:-4] # cut off ".bsp"


	# start up the next map
	sv_init.SV_Map(False, map, False, False)

	# archive server state
	sv_init.svs.mapcmd = map[:shared.MAX_TOKEN_CHARS - 1]

	# copy off the level to the autosave slot
	if not frame.dedicated.value:

		sv_save.SV_WriteServerFile(True)
		sv_save.SV_CopySaveGame("current", "save0")

"""
==================
sv_init.SV_Map_f

Goes directly to a given map without any savegame archiving.
For development work
==================
"""
def SV_Map_f(): #void

	"""
	char *map;
	char expanded[MAX_QPATH];
	"""

	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("USAGE: map <mapname>\n")
		return


	# if not a pcx, demo, or cinematic, check to make sure the level exists
	map = cmdparser.Cmd_Argv(1)

	if "." not in map and "$" not in map and (map[:1] != '*'):

		expanded = "maps/{}.bsp".format(map)

		if not (filesystem.FS_LoadFile2(expanded, 0)[0] >= 0): #if (!FS_FileExists(expanded))

			clientserver.Com_Printf("Can't find %s\n", expanded)
			return



	sv_init.sv.state = server_h.server_state_t.ss_dead # don't save current level when changing
	sv_save.SV_WipeSavegame("current")
	SV_GameMap_f()

def SV_ListMaps_f(): #void

	"""
	strlist_t userMapNames;
	int i;
	char* mapName, *lastsep;
	"""

	clientserver.Com_Printf("\n")

	userMapNames = filesystem.FS_ListFiles2("maps/*.bsp", 0, 0)

	for i in range(len(userMapNames)):

		lastsep = userMapNames[i].rfind('/')
		if lastsep != -1:

			mapName = userMapNames[i][lastsep + 1:]

		else:

			mapName = userMapNames[i]


		mapName = mapName.split(".")[0] #strtok(mapName, ".");

		clientserver.Com_Printf("%s\n", mapName)


	#StrList_Free(&userMapNames);

"""
//===============================================================

/*
==================
SV_Kick_f

Kick a user off of the server
==================
"""
def SV_Kick_f(): #void

	if not sv_init.svs.initialized:

		clientserver.Com_Printf("No server running.\n")
		return


	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("Usage: kick <userid>\n")
		return


	if not SV_SetPlayer():

		return


	if (sv_main.sv_client.state == server_h.client_state_t.cs_spawned) and sv_main.sv_client.name:

		sv_send.SV_BroadcastPrintf(shared.PRINT_HIGH, "%s was kicked\n", sv_main.sv_client.name)


	# print directly, because the dropped client
	# won't get the SV_BroadcastPrintf message
	sv_send.SV_ClientPrintf(sv_main.sv_client, shared.PRINT_HIGH, "You were kicked from the game\n")
	sv_main.SV_DropClient(sv_main.sv_client)
	sv_main.sv_client.lastmessage = sv_init.svs.realtime # min case there is a funny zombie

"""
================
SV_Status_f
================
"""
def SV_Status_f ():

	#int i, j, l
	#client_t *cl
	#char *s
	#int ping
	if not sv_init.svs.clients:
		clientserver.Com_Printf ("No server running.\n")
		return
	clientserver.Com_Printf ("map              : %s\n", sv_init.sv.name)

	clientserver.Com_Printf ("num score ping name            lastmsg address               qport \n")
	clientserver.Com_Printf ("--- ----- ---- --------------- ------- --------------------- ------\n")
	for i in range(int(sv_main.maxclients.value)):
		cl = sv_init.svs.clients[i]
		if cl.state == server_h.client_state_t.cs_free:
			continue
		clientserver.Com_Printf ("%2i ", i)
		clientserver.Com_Printf ("%5i ", server_h.CL_EDICT(cl).client.ps.stats[shared.STAT_FRAGS])

		if cl.state == server_h.client_state_t.cs_connected:
			clientserver.Com_Printf ("CNCT ")
		elif cl.state == server_h.client_state_t.cs_zombie:
			clientserver.Com_Printf ("ZMBI ")
		else:
			ping = cl.ping if cl.ping < 9999 else 9999
			clientserver.Com_Printf ("%4i ", ping)

		clientserver.Com_Printf ("%s", cl.name)
		l = 16 - len(cl.name)
		for j in range(l):
			clientserver.Com_Printf (" ")

		clientserver.Com_Printf ("%7i ", sv_init.svs.realtime - cl.lastmessage)

		s = net_udp.NET_AdrToString (cl.netchan.remote_address)
		clientserver.Com_Printf ("%s", s)
		l = 22 - len(s)
		for j in range(l):
			clientserver.Com_Printf (" ")
		
		clientserver.Com_Printf ("%5i", cl.netchan.qport)

		clientserver.Com_Printf ("\n")
	clientserver.Com_Printf ("\n")

"""
/*
==================
SV_ConSay_f
==================
"""
def SV_ConSay_f():

	#client_t *client
	#int j
	#char *p
	#char text[1024]

	if cmdparser.Cmd_Argc() < 2:
		return

	if not sv_init.svs.initialized:

		clientserver.Com_Printf("No server running.\n")
		return


	text = "console: "
	p = cmdparser.Cmd_Args()

	if p[0] == '"':
		p = p[1:]
		p = p[:-1]

	text = text + p

	for j in range(int(sv_main.maxclients.value)):
		client = sv_init.svs.clients[j]
		if client.state != server_h.client_state_t.cs_spawned:
			continue
		sv_send.SV_ClientPrintf (client, shared.PRINT_CHAT, "{}\n".format(text))


"""
/*
==================
SV_Heartbeat_f
==================
"""
def SV_Heartbeat_f ():

	sv_init.svs.last_heartbeat = -9999999

"""
===========
SV_Serverinfo_f

  Examine or change the serverinfo string
===========
"""
def SV_Serverinfo_f ():

	clientserver.Com_Printf ("Server info settings:\n");
	argproc.Info_Print (cvar.Cvar_Serverinfo())

"""
/*
===========
SV_DumpUser_f

Examine all a users info strings
===========
"""
def SV_DumpUser_f(): #void

	if not sv_init.svs.initialized:

		clientserver.Com_Printf("No server running.\n")
		return


	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("Usage: dumpuser <userid>\n")
		return


	if not SV_SetPlayer():

		return


	clientserver.Com_Printf("userinfo\n")
	clientserver.Com_Printf("--------\n")
	argproc.Info_Print(sv_main.sv_client.userinfo)

"""
/*
==============
SV_ServerRecord_f

Begins server demo recording.  Every entity and every message will be
recorded, but no playerinfo will be stored.  Primarily for demo merging.
==============
"""
def SV_ServerRecord_f ():

	#char name[MAX_OSPATH]
	#sizebuf_t buf
	#int len, i

	if cmdparser.Cmd_Argc() != 2:
		clientserver.Com_Printf ("serverrecord <demoname>\n")
		return

	if sv_init.svs.demofile:
		clientserver.Com_Printf ("Already recording.\n")
		return

	if sv_init.sv.state != server_h.server_state_t.ss_game:
		clientserver.Com_Printf ("You must be in a level to record.\n")
		return

	if ".." in cmdparser.Cmd_Argv(1) or "/" in cmdparser.Cmd_Argv(1) or "\\" in cmdparser.Cmd_Argv(1):

		clientserver.Com_Printf("Illegal filename.\n")
		return

	#
	# open the demo file
	#
	name = "{}/demos/{}.dm2".format(filesystem.FS_Gamedir(), cmdparser.Cmd_Argv(1))

	clientserver.Com_Printf ("recording to %s.\n", name)
	filesystem.FS_CreatePath (name)
	sv_init.svs.demofile = filesystem.Q_fopen(name, "wb")
	if not sv_init.svs.demofile:
		clientserver.Com_Printf ("ERROR: couldn't open.\n")
		return

	# setup a buffer to catch all multicasts
	szone.SZ_Init (sv_init.svs.demo_multicast, 65536)

	#
	# write a single giant fake message with all the startup info
	#
	buf = common_h.sizebuf_t()
	szone.SZ_Init (buf, 32768)

	#
	# serverdata needs to go over for all types of servers
	# to make sure the protocol is right, and to set the gamedir
	#
	# send the serverdata
	movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_serverdata.value)
	movemsg.MSG_WriteLong (buf, common_h.PROTOCOL_VERSION)
	movemsg.MSG_WriteLong (buf, sv_init.svs.spawncount)
	# 2 means server demo
	movemsg.MSG_WriteByte (buf, 2)	# demos are always attract loops
	movemsg.MSG_WriteString (buf, cvar.Cvar_VariableString ("gamedir"))
	movemsg.MSG_WriteShort (buf, -1)
	# send full levelname
	movemsg.MSG_WriteString (buf, sv_init.sv.configstrings[shared.CS_NAME])

	for i in range(shared.MAX_CONFIGSTRINGS):
		if sv_init.sv.configstrings[i]:  # C: empty string has [0]=='\0'
			movemsg.MSG_WriteByte (buf, common_h.svc_ops_e.svc_configstring.value)
			movemsg.MSG_WriteConfigString (buf, i, sv_init.sv.configstrings[i])

			if buf.cursize + 67 >= buf.maxsize:

				clientserver.Com_Printf("not enough buffer space available.\n")
				sv_init.svs.demofile.close()
				sv_init.svs.demofile = None
				return

	# write it to the demo file
	clientserver.Com_DPrintf ("signon message length: %i\n", buf.cursize)
	sv_init.svs.demofile.write(struct.pack('<i', buf.cursize))
	sv_init.svs.demofile.write(bytes(buf.data[:buf.cursize]))

	# the rest of the demo file will be individual frames


"""
/*
==============
SV_ServerStop_f

Ends server demo recording
==============
"""
def SV_ServerStop_f ():

	if not sv_init.svs.demofile:
		clientserver.Com_Printf ("Not doing a serverrecord.\n")
		return
	sv_init.svs.demofile.close()
	sv_init.svs.demofile = None
	clientserver.Com_Printf ("Recording completed.\n")


"""
/*
===============
SV_KillServer_f

Kick everyone off, possibly in preparation for a new game

===============
"""
def SV_KillServer_f ():

	if not sv_init.svs.initialized:
		return
	sv_main.SV_Shutdown ("Server was killed.\n", False)
	net_udp.NET_Config ( False )	# close network sockets

"""
/*
===============
SV_ServerCommand_f

Let the game dll handle a command
===============
"""
def SV_ServerCommand_f ():

	if not sv_game.ge:
		clientserver.Com_Printf ("No game loaded.\n")
		return

	sv_game.ge.ServerCommand()

def SV_Gamemode_f(): #void

	"""
	int none;
	char *arg;
	"""

	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("gamemode dm, coop or sp\ngamemode ? to print current info\n")
		return


	arg = cmdparser.Cmd_Argv(1)

	if arg[:1] == '?':

		none = 1

		if cvar.Cvar_VariableValue("deathmatch"):

			clientserver.Com_Printf("dm ")
			none = 0


		if cvar.Cvar_VariableValue("coop"):

			clientserver.Com_Printf("coop ")
			none = 0


		if cvar.Cvar_VariableValue("singleplayer"):

			clientserver.Com_Printf("sp ")
			none = 0


		if none:

			clientserver.Com_Printf("none\n")

		else:

			clientserver.Com_Printf("\n")


		return


	if arg == "dm":

		cvar.Cvar_Set("deathmatch", "1")
		cvar.Cvar_Set("coop", "0")
		cvar.Cvar_Set("singleplayer", "0")

	elif arg == "coop":

		cvar.Cvar_Set("deathmatch", "0")
		cvar.Cvar_Set("coop", "1")
		cvar.Cvar_Set("singleplayer", "0")

	elif arg == "sp":

		cvar.Cvar_Set("deathmatch", "0")
		cvar.Cvar_Set("coop", "0")
		cvar.Cvar_Set("singleplayer", "1")

	else:

		clientserver.Com_Printf("unknown gamemode: '%s'\nspecify dm, coop or sp\n", arg)

"""
//===========================================================

/*
==================
SV_InitOperatorCommands
==================
"""
def SV_InitOperatorCommands(): #void

	cmdparser.Cmd_AddCommand("gamemode", SV_Gamemode_f)

	cmdparser.Cmd_AddCommand("heartbeat", SV_Heartbeat_f)
	cmdparser.Cmd_AddCommand("kick", SV_Kick_f)
	cmdparser.Cmd_AddCommand("status", SV_Status_f)
	cmdparser.Cmd_AddCommand("serverinfo", SV_Serverinfo_f)
	cmdparser.Cmd_AddCommand("dumpuser", SV_DumpUser_f)

	cmdparser.Cmd_AddCommand("map", SV_Map_f)
	cmdparser.Cmd_AddCommand("listmaps", SV_ListMaps_f)
	cmdparser.Cmd_AddCommand("demomap", SV_DemoMap_f)
	cmdparser.Cmd_AddCommand("gamemap", SV_GameMap_f)
	cmdparser.Cmd_AddCommand("setmaster", SV_SetMaster_f)

	if frame.dedicated.value:

		cmdparser.Cmd_AddCommand("say", SV_ConSay_f)


	cmdparser.Cmd_AddCommand("serverrecord", SV_ServerRecord_f)
	cmdparser.Cmd_AddCommand("serverstop", SV_ServerStop_f)

	cmdparser.Cmd_AddCommand("save", sv_save.SV_Savegame_f)
	cmdparser.Cmd_AddCommand("load", sv_save.SV_Loadgame_f)

	cmdparser.Cmd_AddCommand("killserver", SV_KillServer_f)

	cmdparser.Cmd_AddCommand("sv", SV_ServerCommand_f)

