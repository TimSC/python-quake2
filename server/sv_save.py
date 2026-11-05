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
from linux import q_shlinux
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

from linux import q_shlinux
from common import clientserver
from common import filesystem
from server import sv_save

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

	sv_save.SV_WipeSavegame (dst)

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
	collision.CM_WritePortalState (f)
	f.close()

	name = "{}/save/current/{}.sav".format(filesystem.FS_Gamedir(), sv_init.sv.name)
	sv_game.ge.WriteLevel (name)
r"""
static void
SV_ReadConfigStrings(fileHandle_t f)
{
	int i;

	FS_Read(sv.configstrings, sizeof(sv.configstrings), f);

	/* ensure the configstrings are null terminated */
	for (i = 0; i < MAX_CONFIGSTRINGS; i++)
	{
		/* only null terminate the last index of the statusbar code section */
		if ((i < CS_STATUSBAR) || (i >= (CS_STATUSBAR_END - 1)))
		{
			sv.configstrings[i][sizeof(sv.configstrings[i]) - 1] = '\0';
		}
	}
}
"""

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
	collision.CM_ReadPortalState (f)
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
	sv_init.sv.state = server_h.server_state_t.ss_dead		# don't save current level when changing
	sv_init.SV_Map (False, sv_init.svs.mapcmd, True)

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

	if int(sv_main.maxclients.value) == 1 and server_h.CL_EDICT(sv_init.svs.clients[0]).client.ps.stats[shared.STAT_HEALTH] <= 0:
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

