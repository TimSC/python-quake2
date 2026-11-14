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

Serverside savegame code.

=======================================================================
"""
from __future__ import annotations

import os
import time
from backends.unix import system
from common.header import shared
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import collision
from server.header import server as server_h
from server import sv_cmd
from server import sv_game
from server import sv_init
from server import sv_main

"""
#include "header/server.h"
"""

"""
#include "header/server.h"
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
	s = system.Sys_FindFirst(name, 0, 0)
	while s:
		os.remove(s)
		s = system.Sys_FindNext(0, 0)
	system.Sys_FindClose()
	name = "{}/save/{}/*.sv2".format(filesystem.FS_Gamedir(), savename)
	s = system.Sys_FindFirst(name, 0, 0)
	while s:
		os.remove(s)
		s = system.Sys_FindNext(0, 0)
	system.Sys_FindClose()


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
	found = system.Sys_FindFirst(name, 0, 0)
	while found:
		name2 = found.replace("/save/{}/".format(src), "/save/{}/".format(dst), 1)
		CopyFile (found, name2)

		# change sav to sv2
		CopyFile (found[:-3] + "sv2", name2[:-3] + "sv2")

		found = system.Sys_FindNext(0, 0)
	system.Sys_FindClose()
"""
/*
==============
SV_WriteLevelFile

==============
*/
"""
def SV_ConfigStringsBlob()->bytes: #(returns the bytes of sv.configstrings)
	# Q2PORT: sv.configstrings is char[MAX_CONFIGSTRINGS][MAX_QPATH] in C, written with one fwrite;
	# the statusbar program is longer than one slot and runs on into the following ones

	blob = bytearray(shared.MAX_CONFIGSTRINGS * shared.MAX_QPATH)

	for i in range(shared.MAX_CONFIGSTRINGS):

		s = sv_init.sv.configstrings[i]
		if s:

			data = s.encode('latin-1')
			blob[i * shared.MAX_QPATH:i * shared.MAX_QPATH + len(data)] = data
			blob[i * shared.MAX_QPATH + len(data)] = 0



	return bytes(blob)

def SV_WriteLevelFile(): #void

	"""
	char name[MAX_OSPATH];
	char workdir[MAX_OSPATH];
	FILE *f;
	"""

	clientserver.Com_DPrintf("SV_WriteLevelFile()\n")

	name = "{}/save/current/{}.sv2".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	f = filesystem.Q_fopen(name, "wb")

	if f is None:

		clientserver.Com_Printf("Failed to open %s\n", name)
		return


	f.write(SV_ConfigStringsBlob()) #fwrite(sv.configstrings, sizeof(sv.configstrings), 1, f);
	collision.CM_WritePortalState(f)
	f.close()

	# Q2PORT: Yamagi changes the working directory to save/current and passes the
	# game a relative name; the port passes the full path and leaves the working directory
	name = "{}/save/current".format(filesystem.FS_Gamedir())
	system.Sys_Mkdir(name)

	name = "{}/save/current/{}.sav".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	sv_game.ge.WriteLevel(name)

def SV_ReadConfigStrings(f): #fileHandle_t

	"""
	int i;
	"""

	data = filesystem.FS_Read(shared.MAX_CONFIGSTRINGS * shared.MAX_QPATH, f) #FS_Read(sv.configstrings, sizeof(sv.configstrings), f);
	data = bytearray(data.ljust(shared.MAX_CONFIGSTRINGS * shared.MAX_QPATH, b'\0'))

	# ensure the configstrings are null terminated
	for i in range(shared.MAX_CONFIGSTRINGS):

		# only null terminate the last index of the statusbar code section
		if (i < shared.CS_STATUSBAR) or (i >= (shared.CS_STATUSBAR_END - 1)):

			data[i * shared.MAX_QPATH + shared.MAX_QPATH - 1] = 0



	# Q2PORT: the C strings in the array; a string that runs on into the following slots
	# (the statusbar program) is held whole at its first index
	i = 0
	while i < shared.MAX_CONFIGSTRINGS:

		start = i * shared.MAX_QPATH
		end = data.index(0, start)
		sv_init.sv.configstrings[i] = data[start:end].decode('latin-1')
		spill = (end - start) // shared.MAX_QPATH
		for k in range(1, spill + 1):
			if i + k < shared.MAX_CONFIGSTRINGS:
				sv_init.sv.configstrings[i + k] = ""
		i += 1 + spill

"""
/*
==============
SV_ReadLevelFile

==============
*/
"""
def SV_ReadLevelFile(): #void

	"""
	char name[MAX_OSPATH];
	char workdir[MAX_OSPATH];
	fileHandle_t f;
	"""

	clientserver.Com_DPrintf("SV_ReadLevelFile()\n")

	name = "save/current/{}.sv2".format(sv_init.sv.name)
	length, f = filesystem.FS_FOpenFile(name, True)

	if not f:

		clientserver.Com_Printf("Failed to open %s\n", name)
		return


	SV_ReadConfigStrings(f)
	collision.CM_ReadPortalState(f)
	filesystem.FS_FCloseFile(f)

	# Q2PORT: the full path, not a change of working directory (see SV_WriteLevelFile)
	name = "{}/save/current/{}.sav".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	sv_game.ge.ReadLevel(name)

"""
/*
==============
SV_WriteServerFile

==============
*/
"""
def SV_WriteServerFile(autosave: bool): #qboolean

	"""
	FILE *f;
	cvar_t *var;
	char name[MAX_OSPATH], string[128];
	char workdir[MAX_OSPATH];
	char comment[32];
	time_t aclock;
	struct tm *newtime;
	"""

	clientserver.Com_DPrintf("SV_WriteServerFile(%s)\n", "true" if autosave else "false")

	name = "{}/save/current/server.ssv".format(filesystem.FS_Gamedir())
	f = filesystem.Q_fopen(name, "wb")

	if f is None:

		clientserver.Com_Printf("Couldn't write %s\n", name)
		return


	# write the comment field
	#memset(comment, 0, sizeof(comment));

	if not autosave:

		newtime = time.localtime()
		comment = "%2i:%i%i %2i/%2i  " % (newtime.tm_hour,
				newtime.tm_min // 10, newtime.tm_min % 10,
				newtime.tm_mon + 1, newtime.tm_mday)
		comment = (comment + sv_init.sv.configstrings[shared.CS_NAME])[:32 - 1] #Q_strlcat(comment, sv.configstrings[CS_NAME], sizeof(comment));

	else:

		# autosaved
		comment = "ENTERING {}".format(sv_init.sv.configstrings[shared.CS_NAME])[:32 - 1]


	f.write(comment.encode('latin-1').ljust(32, b'\0'))

	# write the mapcmd
	f.write(sv_init.svs.mapcmd.encode('latin-1')[:server_h.MAX_SAVE_TOKEN_CHARS - 1].ljust(server_h.MAX_SAVE_TOKEN_CHARS, b'\0'))

	# write all CVAR_LATCH cvars
	# these will be things like coop, skill, deathmatch, etc
	for var in cvar.cvar_vars:

		#char cvarname[LATCH_CVAR_SAVELENGTH] = {0};

		if not (var.flags & shared.CVAR_LATCH):

			continue


		if (len(var.name) >= shared.LATCH_CVAR_SAVELENGTH - 1) or \
			(len(var.string) >= 128 - 1):

			clientserver.Com_Printf("Cvar too long: %s = %s\n", var.name, var.string)
			continue


		f.write(var.name.encode('latin-1').ljust(shared.LATCH_CVAR_SAVELENGTH, b'\0'))
		f.write(var.string.encode('latin-1').ljust(128, b'\0'))


	f.close()

	# write game state
	# Q2PORT: the full path, not a change of working directory (see SV_WriteLevelFile)
	name = "{}/save/current".format(filesystem.FS_Gamedir())
	system.Sys_Mkdir(name)

	sv_game.ge.WriteGame("{}/game.ssv".format(name), autosave)

"""
/*
==============
SV_ReadServerFile

==============
*/
"""
def SV_ReadServerFile(): #void

	"""
	fileHandle_t f;
	char name[MAX_OSPATH], string[128];
	char workdir[MAX_OSPATH];
	char comment[32];
	char mapcmd[MAX_SAVE_TOKEN_CHARS];
	"""

	clientserver.Com_DPrintf("SV_ReadServerFile()\n")

	name = "save/current/server.ssv"
	length, f = filesystem.FS_FOpenFile(name, True)

	if not f:

		clientserver.Com_Printf("Couldn't read %s\n", name)
		return


	# read the comment field
	comment = filesystem.FS_Read(32, f)

	# read the mapcmd
	mapcmd = filesystem.FS_Read(server_h.MAX_SAVE_TOKEN_CHARS, f).split(b'\0')[0].decode('latin-1')

	# read all CVAR_LATCH cvars
	# these will be things like coop, skill, deathmatch, etc
	while 1:

		#char cvarname[LATCH_CVAR_SAVELENGTH] = {0};

		data = filesystem.FS_FRead(1, shared.LATCH_CVAR_SAVELENGTH, f)
		if not data:

			break


		cvarname = data.split(b'\0')[0].decode('latin-1')
		string = filesystem.FS_Read(128, f).split(b'\0')[0].decode('latin-1')
		clientserver.Com_DPrintf("Set %s = %s\n", cvarname, string)
		cvar.Cvar_ForceSet(cvarname, string)


	filesystem.FS_FCloseFile(f)

	# start a new game fresh with new cvars
	sv_init.SV_InitGame()

	sv_init.svs.mapcmd = mapcmd

	# read game state
	# Q2PORT: the full path, not a change of working directory (see SV_WriteLevelFile)
	name = "{}/save/current".format(filesystem.FS_Gamedir())
	sv_game.ge.ReadGame("{}/game.ssv".format(name))

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


	clientserver.Com_Printf("Savegame: %s\n", cmdparser.Cmd_Argv(1))

	if cmdparser.Cmd_Argv(1) == "save0" or cmdparser.Cmd_Argv(1) == "current":

		isautosave = True

	else:

		isautosave = False


	SV_CopySaveGame (cmdparser.Cmd_Argv(1), "current")
	SV_ReadServerFile ()

	# go to the map
	sv_init.sv.state = server_h.server_state_t.ss_dead		# don't save current level when changing
	sv_init.SV_Map (False, sv_init.svs.mapcmd, True, isautosave)

"""
==============
SV_Savegame_f

==============
"""
def SV_Savegame_f ():

	#char *dir

	if sv_init.sv.state != server_h.server_state_t.ss_game:
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

	if sv_init.server.maxclients == 1 and server_h.CL_EDICT(sv_init.svs.clients[0]).client.ps.stats[shared.STAT_HEALTH] <= 0:
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

