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
from __future__ import annotations

import os
import time
import struct
from qcommon import cmodel, net_chan
from server import sv_init, sv_main, sv_send, sv_game, sv_user
from linux import net_udp, q_shlinux
pass
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
"""
#include "server.h"
"""
"""
/*
===============================================================================

OPERATOR CONSOLE ONLY COMMANDS

These commands can only be entered from stdin or by a remote operator datagram
===============================================================================
*/
"""
"""
/*
====================
SV_SetMaster_f

Specify a list of master servers
====================
"""
def SV_SetMaster_f ():

	#int i, slot

	# only dedicated servers send heartbeats
	if not frame.dedicated.value:
		clientserver.Com_Printf ("Only dedicated servers use masters.\n")
		return

	# make sure the server is listed public
	cvar.Cvar_Set ("public", "1")

	for i in range(1, sv_init.MAX_MASTERS):
		sv_main.master_adr[i] = common_h.netadr_t()

	slot = 1		# slot 0 will always contain the id master
	for i in range(1, cmdparser.Cmd_Argc()):
		if slot == sv_init.MAX_MASTERS:
			break

		if not net_udp.NET_StringToAdr (cmdparser.Cmd_Argv(i), sv_main.master_adr[i]):
			clientserver.Com_Printf ("Bad address: %s\n", cmdparser.Cmd_Argv(i))
			continue
		if sv_main.master_adr[slot].port == 0:
			sv_main.master_adr[slot].port = shared_c.BigShort (common_h.PORT_MASTER)

		clientserver.Com_Printf ("Master server at %s\n", net_udp.NET_AdrToString (sv_main.master_adr[slot]))

		clientserver.Com_Printf ("Sending a ping.\n")

		net_chan.Netchan_OutOfBandPrint (common_h.netsrc_t.NS_SERVER, sv_main.master_adr[slot], "ping")

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
		sv_user.sv_player = sv_main.sv_client.edict
		if sv_main.sv_client.state == sv_init.client_state_t.cs_free:
			clientserver.Com_Printf ("Client %i is not active\n", idnum)
			return False
		return True

	# check for a name match
	for i in range(int(sv_main.maxclients.value)):
		cl = sv_init.svs.clients[i]
		if cl.state == sv_init.client_state_t.cs_free:
			continue
		if cl.name == s:
			sv_main.sv_client = cl
			sv_user.sv_player = sv_main.sv_client.edict
			return True

	clientserver.Com_Printf ("Userid %s is not on the server\n", s)
	return False
"""
/*
===============================================================================

SAVEGAME FILES

===============================================================================
*/
"""
"""
/*
=====================
SV_WipeSavegame

Delete save/<XXX>/
=====================
"""
def SV_WipeSavegame (savename): #char *

	#char name[MAX_OSPATH]
	#char *s

	clientserver.Com_DPrintf("SV_WipeSaveGame({})\n".format(savename))

	name = "{}/save/{}/server.ssv".format(filesystem.FS_Gamedir(), savename)
	if os.path.exists(name):
		os.remove(name)
	name = "{}/save/{}/game.ssv".format(filesystem.FS_Gamedir(), savename)
	if os.path.exists(name):
		os.remove(name)

	name = "{}/save/{}/*.sav".format(filesystem.FS_Gamedir(), savename)
	s = q_shlinux.Sys_FindFirst(name, 0, 0)
	while s:
		os.remove(s)
		s = q_shlinux.Sys_FindNext(0, 0)
	q_shlinux.Sys_FindClose()
	name = "{}/save/{}/*.sv2".format(filesystem.FS_Gamedir(), savename)
	s = q_shlinux.Sys_FindFirst(name, 0, 0)
	while s:
		os.remove(s)
		s = q_shlinux.Sys_FindNext(0, 0)
	q_shlinux.Sys_FindClose()
"""
/*
================
CopyFile
================
*/
"""
def CopyFile (src, dst): #char *, char *

	#FILE *f1, *f2
	#int l

	clientserver.Com_DPrintf ("CopyFile ({}, {})\n".format(src, dst))

	f1 = open(src, "rb")
	if not f1:
		return
	f2 = open(dst, "wb")
	if not f2:
		f1.close()
		return

	while True:
		buffer = f1.read(65536)
		if not buffer:
			break
		f2.write(buffer)

	f1.close()
	f2.close()
"""
/*
================
SV_CopySaveGame
================
*/
"""
def SV_CopySaveGame (src, dst): #char *, char *

	#char name[MAX_OSPATH], name2[MAX_OSPATH]
	#int l, len
	#char *found

	clientserver.Com_DPrintf("SV_CopySaveGame({}, {})\n".format(src, dst))

	SV_WipeSavegame (dst)

	# copy the savegame over
	name = "{}/save/{}/server.ssv".format(filesystem.FS_Gamedir(), src)
	name2 = "{}/save/{}/server.ssv".format(filesystem.FS_Gamedir(), dst)
	filesystem.FS_CreatePath (name2)
	CopyFile (name, name2)

	name = "{}/save/{}/game.ssv".format(filesystem.FS_Gamedir(), src)
	name2 = "{}/save/{}/game.ssv".format(filesystem.FS_Gamedir(), dst)
	CopyFile (name, name2)

	# Sys_FindFirst returns the full path
	name = "{}/save/{}/*.sav".format(filesystem.FS_Gamedir(), src)
	found = q_shlinux.Sys_FindFirst(name, 0, 0)
	while found:
		name2 = found.replace("/save/{}/".format(src), "/save/{}/".format(dst), 1)
		CopyFile (found, name2)

		# change sav to sv2
		CopyFile (found[:-3] + "sv2", name2[:-3] + "sv2")

		found = q_shlinux.Sys_FindNext(0, 0)
	q_shlinux.Sys_FindClose()
"""
/*
==============
SV_WriteLevelFile

==============
*/
"""
def SV_WriteLevelFile ():

	#char name[MAX_OSPATH]
	#FILE *f

	clientserver.Com_DPrintf("SV_WriteLevelFile()\n")

	name = "{}/save/current/{}.sv2".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	f = open(name, "wb")
	if not f:
		clientserver.Com_Printf ("Failed to open %s\n", name)
		return
	# fwrite (sv.configstrings, sizeof(sv.configstrings), 1, f);
	blob = b"".join(c.encode('latin-1').ljust(shared.MAX_QPATH, b'\0') for c in sv_init.sv.configstrings)
	f.write(blob)
	cmodel.CM_WritePortalState (f)
	f.close()

	name = "{}/save/current/{}.sav".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	sv_game.ge.WriteLevel (name)
"""
/*
==============
SV_ReadLevelFile

==============
*/
"""
def SV_ReadLevelFile ():

	#char name[MAX_OSPATH]
	#FILE *f

	clientserver.Com_DPrintf("SV_ReadLevelFile()\n")

	name = "{}/save/current/{}.sv2".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	f = open(name, "rb")
	if not f:
		clientserver.Com_Printf ("Failed to open %s\n", name)
		return
	# FS_Read (sv.configstrings, sizeof(sv.configstrings), f);
	data = f.read(len(sv_init.sv.configstrings)*shared.MAX_QPATH)
	for i in range(len(sv_init.sv.configstrings)):
		chunk = data[i*shared.MAX_QPATH:(i+1)*shared.MAX_QPATH]
		sv_init.sv.configstrings[i] = chunk.split(b'\0')[0].decode('latin-1')
	cmodel.CM_ReadPortalState (f)
	f.close()

	name = "{}/save/current/{}.sav".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	sv_game.ge.ReadLevel (name)
"""
/*
==============
SV_WriteServerFile

==============
*/
"""
def SV_WriteServerFile (autosave): #qboolean

	#FILE *f
	#cvar_t *var
	#char name[MAX_OSPATH], string[128]
	#char comment[32]
	#time_t aclock

	clientserver.Com_DPrintf("SV_WriteServerFile({})\n".format("true" if autosave else "false"))

	name = "{}/save/current/server.ssv".format(filesystem.FS_Gamedir())
	f = open(name, "wb")
	if not f:
		clientserver.Com_Printf ("Couldn't write %s\n", name)
		return
	# write the comment field
	if not autosave:
		newtime = time.localtime()
		comment = "{:2d}:{}{} {:2d}/{:2d}  ".format(newtime.tm_hour
			, newtime.tm_min//10, newtime.tm_min%10,
			newtime.tm_mon+1, newtime.tm_mday)
		comment = (comment + sv_init.sv.configstrings[shared.CS_NAME])[:31]
	else:
		# autosaved
		comment = ("ENTERING {}".format(sv_init.sv.configstrings[shared.CS_NAME]))[:31]

	f.write(comment.encode('latin-1').ljust(32, b'\0'))

	# write the mapcmd
	mapcmd = (sv_init.svs.mapcmd or "")
	f.write(mapcmd.encode('latin-1').ljust(shared.MAX_TOKEN_CHARS, b'\0'))

	# write all CVAR_LATCH cvars
	# these will be things like coop, skill, deathmatch, etc
	for var in cvar.cvar_vars:
		if not (var.flags & shared.CVAR_LATCH):
			continue
		if len(var.name) >= shared.MAX_OSPATH-1 or len(var.string) >= 127:
			clientserver.Com_Printf ("Cvar too long: %s = %s\n", var.name, var.string)
			continue
		f.write(var.name.encode('latin-1').ljust(shared.MAX_OSPATH, b'\0'))
		f.write(var.string.encode('latin-1').ljust(128, b'\0'))

	f.close()

	# write game state
	name = "{}/save/current/game.ssv".format(filesystem.FS_Gamedir())
	sv_game.ge.WriteGame (name, autosave)
"""
/*
==============
SV_ReadServerFile

==============
*/
"""
def SV_ReadServerFile ():

	#FILE *f
	#char name[MAX_OSPATH], string[128]
	#char comment[32]
	#char mapcmd[MAX_TOKEN_CHARS]

	clientserver.Com_DPrintf("SV_ReadServerFile()\n")

	name = "{}/save/current/server.ssv".format(filesystem.FS_Gamedir())
	f = open(name, "rb")
	if not f:
		clientserver.Com_Printf ("Couldn't read %s\n", name)
		return
	# read the comment field
	f.read(32)

	# read the mapcmd
	mapcmd = f.read(shared.MAX_TOKEN_CHARS).split(b'\0')[0].decode('latin-1')

	# read all CVAR_LATCH cvars
	# these will be things like coop, skill, deathmatch, etc
	while True:
		namebuf = f.read(shared.MAX_OSPATH)
		if not namebuf:
			break
		stringbuf = f.read(128)
		cname = namebuf.split(b'\0')[0].decode('latin-1')
		cstring = stringbuf.split(b'\0')[0].decode('latin-1')
		clientserver.Com_DPrintf ("Set {} = {}\n".format(cname, cstring))
		cvar.Cvar_ForceSet (cname, cstring)

	f.close()

	# start a new game fresh with new cvars
	sv_init.SV_InitGame ()

	sv_init.svs.mapcmd = mapcmd

	# read game state
	name = "{}/save/current/game.ssv".format(filesystem.FS_Gamedir())
	sv_game.ge.ReadGame (name)


"""
//=========================================================
/*
==================
SV_DemoMap_f

Puts the server in demo mode on a specific map/cinematic
==================
"""
def SV_DemoMap_f ():
	
	sv_init.SV_Map (True, cmdparser.Cmd_Argv(1), False )

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
def SV_GameMap_f ():

	#char		*map;
	#int			i;
	#client_t	*cl;
	#qboolean	*savedInuse;

	if cmdparser.Cmd_Argc() != 2:
	
		clientserver.Com_Printf ("USAGE: gamemap <map>\n");
		return
	
	clientserver.Com_DPrintf("SV_GameMap({})\n".format(cmdparser.Cmd_Argv(1)))
	filesystem.FS_CreatePath("{}/save/current/".format(filesystem.FS_Gamedir()))
	
	# check for clearing the current savegame
	map = cmdparser.Cmd_Argv(1)
	if len(map) > 0 and map[0] == '*':  # C: empty string has map[0]=='\0'
		# wipe all the *.sav files
		SV_WipeSavegame ("current")
	else:
		# save the map just exited
		if sv_init.sv.state == sv_init.server_state_t.ss_game:
			# clear all the client inuse flags before saving so that
			# when the level is re-entered, the clients will spawn
			# at spawn points instead of occupying body shells
			savedInuse = []
			for i in range(int(sv_main.maxclients.value)):
				cl = sv_init.svs.clients[i]
				savedInuse.append(cl.edict.inuse)
				cl.edict.inuse = False

			SV_WriteLevelFile ()

			# we must restore these for clients to transfer over correctly
			for i in range(int(sv_main.maxclients.value)):
				sv_init.svs.clients[i].edict.inuse = savedInuse[i]

	# start up the next map
	sv_init.SV_Map (False, cmdparser.Cmd_Argv(1), False)

	# archive server state
	sv_init.svs.mapcmd = map

	# copy off the level to the autosave slot
	if not frame.dedicated.value:
		SV_WriteServerFile (True)
		SV_CopySaveGame ("current", "save0")

"""
==================
sv_init.SV_Map_f

Goes directly to a given map without any savegame archiving.
For development work
==================
"""
def SV_Map_f ():

	#char	*map;

	# if not a pcx, demo, or cinematic, check to make sure the level exists
	mapName = cmdparser.Cmd_Argv(1)
	if mapName.find(".") == -1:
	
		expanded = "maps/{}.bsp".format(mapName)
		length, handle = filesystem.FS_LoadFile (expanded)
		if handle is None:
		
			clientserver.Com_Printf ("Can't find {}\n".format(expanded))
			return
		
	sv_init.sv.state = sv_init.server_state_t.ss_dead		# don't save current level when changing
	SV_WipeSavegame("current")
	SV_GameMap_f ()

"""
=====================================================================

  SAVEGAMES

=====================================================================
*/


"""
"""
/*
==============
SV_Loadgame_f

==============
"""
def SV_Loadgame_f ():
	#char name[MAX_OSPATH]
	#FILE *f
	#char *dir

	if cmdparser.Cmd_Argc() != 2:
		clientserver.Com_Printf ("USAGE: loadgame <directory>\n")
		return

	clientserver.Com_Printf ("Loading game...\n")

	dir = cmdparser.Cmd_Argv(1)
	if (".." in dir) or ("/" in dir) or ("\\" in dir):
		clientserver.Com_Printf ("Bad savedir.\n")

	# make sure the server.ssv file exists
	name = "{}/save/{}/server.ssv".format(filesystem.FS_Gamedir(), cmdparser.Cmd_Argv(1))
	if not os.path.exists(name):
		clientserver.Com_Printf ("No such savegame: %s\n", name)
		return

	SV_CopySaveGame (cmdparser.Cmd_Argv(1), "current")

	SV_ReadServerFile ()

	# go to the map
	sv_init.sv.state = sv_init.server_state_t.ss_dead		# don't save current level when changing
	sv_init.SV_Map (False, sv_init.svs.mapcmd, True)

"""
==============
SV_Savegame_f

==============
"""
def SV_Savegame_f ():

	#char *dir

	if sv_init.sv.state != sv_init.server_state_t.ss_game:
		clientserver.Com_Printf ("You must be in a game to save.\n")
		return

	if cmdparser.Cmd_Argc() != 2:
		clientserver.Com_Printf ("USAGE: savegame <directory>\n")
		return

	if cvar.Cvar_VariableValue("deathmatch"):
		clientserver.Com_Printf ("Can't savegame in a deathmatch\n")
		return

	if cmdparser.Cmd_Argv(1) == "current":
		clientserver.Com_Printf ("Can't save to 'current'\n")
		return

	if int(sv_main.maxclients.value) == 1 and sv_init.svs.clients[0].edict.client.ps.stats[shared.STAT_HEALTH] <= 0:
		clientserver.Com_Printf ("\nCan't savegame while dead!\n")
		return

	dir = cmdparser.Cmd_Argv(1)
	if (".." in dir) or ("/" in dir) or ("\\" in dir):
		clientserver.Com_Printf ("Bad savedir.\n")

	clientserver.Com_Printf ("Saving game...\n")

	# archive current level, including all client edicts.
	# when the level is reloaded, they will be shells awaiting
	# a connecting client
	SV_WriteLevelFile ()

	# save server state
	SV_WriteServerFile (False)

	# copy it off
	SV_CopySaveGame ("current", dir)

	clientserver.Com_Printf ("Done.\n")

"""
//===============================================================

/*
==================
SV_Kick_f

Kick a user off of the server
==================
"""
def SV_Kick_f ():

	if not sv_init.svs.initialized:
		clientserver.Com_Printf ("No server running.\n")
		return

	if cmdparser.Cmd_Argc() != 2:
		clientserver.Com_Printf ("Usage: kick <userid>\n")
		return

	if not SV_SetPlayer ():
		return

	# print directly, because the dropped client won't get the
	# SV_BroadcastPrintf message
	sv_send.SV_BroadcastPrintf (shared.PRINT_HIGH, "{} was kicked\n".format(sv_main.sv_client.name))
	sv_send.SV_ClientPrintf (sv_main.sv_client, shared.PRINT_HIGH, "You were kicked from the game\n")
	sv_main.SV_DropClient (sv_main.sv_client)
	sv_main.sv_client.lastmessage = sv_init.svs.realtime	# min case there is a funny zombie

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
		if cl.state == sv_init.client_state_t.cs_free:
			continue
		clientserver.Com_Printf ("%3i ", i)
		clientserver.Com_Printf ("%5i ", cl.edict.client.ps.stats[shared.STAT_FRAGS])

		if cl.state == sv_init.client_state_t.cs_connected:
			clientserver.Com_Printf ("CNCT ")
		elif cl.state == sv_init.client_state_t.cs_zombie:
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

	text = "console: "
	p = cmdparser.Cmd_Args()

	if p[0] == '"':
		p = p[1:]
		p = p[:-1]

	text = text + p

	for j in range(int(sv_main.maxclients.value)):
		client = sv_init.svs.clients[j]
		if client.state != sv_init.client_state_t.cs_spawned:
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
def SV_DumpUser_f ():

	if cmdparser.Cmd_Argc() != 2:
		clientserver.Com_Printf ("Usage: info <userid>\n")
		return

	if not SV_SetPlayer ():
		return

	clientserver.Com_Printf ("userinfo\n")
	clientserver.Com_Printf ("--------\n")
	argproc.Info_Print (sv_main.sv_client.userinfo)

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

	if sv_init.sv.state != sv_init.server_state_t.ss_game:
		clientserver.Com_Printf ("You must be in a level to record.\n")
		return

	#
	# open the demo file
	#
	name = "{}/demos/{}.dm2".format(filesystem.FS_Gamedir(), cmdparser.Cmd_Argv(1))

	clientserver.Com_Printf ("recording to %s.\n", name)
	filesystem.FS_CreatePath (name)
	sv_init.svs.demofile = open(name, "wb")
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
			movemsg.MSG_WriteShort (buf, i)
			movemsg.MSG_WriteString (buf, sv_init.sv.configstrings[i])

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

"""
//===========================================================

/*
==================
SV_InitOperatorCommands
==================
"""
def SV_InitOperatorCommands ():

	cmdparser.Cmd_AddCommand ("heartbeat", SV_Heartbeat_f)
	cmdparser.Cmd_AddCommand ("kick", SV_Kick_f)
	cmdparser.Cmd_AddCommand ("status", SV_Status_f)
	cmdparser.Cmd_AddCommand ("serverinfo", SV_Serverinfo_f)
	cmdparser.Cmd_AddCommand ("dumpuser", SV_DumpUser_f)

	cmdparser.Cmd_AddCommand ("map", SV_Map_f)
	cmdparser.Cmd_AddCommand ("demomap", SV_DemoMap_f)
	cmdparser.Cmd_AddCommand ("gamemap", SV_GameMap_f)
	cmdparser.Cmd_AddCommand ("setmaster", SV_SetMaster_f)

	if frame.dedicated.value:
		cmdparser.Cmd_AddCommand ("say", SV_ConSay_f)

	cmdparser.Cmd_AddCommand ("serverrecord", SV_ServerRecord_f)
	cmdparser.Cmd_AddCommand ("serverstop", SV_ServerStop_f)

	cmdparser.Cmd_AddCommand ("save", SV_Savegame_f)
	cmdparser.Cmd_AddCommand ("load", SV_Loadgame_f)

	cmdparser.Cmd_AddCommand ("killserver", SV_KillServer_f)

	cmdparser.Cmd_AddCommand ("sv", SV_ServerCommand_f)

