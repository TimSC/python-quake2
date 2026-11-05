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

Server startup.

=======================================================================
"""
from __future__ import annotations

import copy
import random
import struct
from client import cl_main, cl_scrn
from linux import net_udp
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import filesystem
from common import cmdparser
from common import cvar
from common import frame
from common import movemsg
from common import szone
from common import collision
from common import pmove
from server.header import server as server_h
from server import sv_game
from server import sv_main
from server import sv_send
from server import sv_world

"""
#include "header/server.h"
#include <limits.h>
"""

svs = server_h.server_static_t()				# persistant server info
sv = server_h.server_t()					# local server
"""
static entity_state_t *
SV_AllocBaseline(int entnum)
{
	int nextpow2;

	if ((entnum < 0) || (entnum > MAX_SV_ENTNUM))
	{
		return NULL;
	}

	if (entnum >= sv.numbaselines)
	{
		nextpow2 = (sv.numbaselines || (entnum >= ALLOC_ENTITIES_MIN)) ?
			(int)NextPow2gt(entnum) : ALLOC_ENTITIES_MIN;

		sv.baselines = Z_Realloc(sv.baselines, nextpow2 * sizeof(entity_state_t));
		sv.numbaselines = nextpow2;
	}

	return &sv.baselines[entnum];
}
"""

"""
================
SV_FindIndex

================
"""
def SV_FindIndex (name, start, max, create): #char *, int, int, qboolean

	#int		i;
	
	if name is None or not name:
		return 0

	i = 1
	while i<max and sv.configstrings[start+i]:
		if sv.configstrings[start+i] == name:
			return i
		i += 1

	if not create:
		return 0

	if i == max:
		clientserver.Com_Error (shared.ERR_DROP, "*Index: overflow")

	sv.configstrings[start+i] = name[:shared.MAX_QPATH] # strncpy (sv.configstrings[start+i], name, sizeof(sv.configstrings[i]));

	if sv.state != server_h.server_state_t.ss_loading:
		# send the update to everyone
		szone.SZ_Clear (sv.multicast)
		movemsg.MSG_WriteChar (sv.multicast, struct.pack("b", common_h.svc_ops_e.svc_configstring.value))
		movemsg.MSG_WriteShort (sv.multicast, start+i)
		movemsg.MSG_WriteString (sv.multicast, name.encode('ascii'))
		sv_send.SV_Multicast (shared_c.vec3_origin, shared.multicast_t.MULTICAST_ALL_R)
	
	return i


def SV_ModelIndex (name): #char *

	return SV_FindIndex (name, shared.CS_MODELS, shared.MAX_MODELS, True)


def SV_SoundIndex (name): #char *

	return SV_FindIndex (name, shared.CS_SOUNDS, shared.MAX_SOUNDS, True)


def SV_ImageIndex (name): #char *

	return SV_FindIndex (name, shared.CS_IMAGES, shared.MAX_IMAGES, True)


"""
/*
================
SV_CreateBaseline

Entity baselines are used to compress the update messages
to the clients -- only the fields that differ from the
baseline will be transmitted
================
"""
def SV_CreateBaseline ():

	num_edicts = getattr(sv_game.ge, "num_edicts", None)
	if num_edicts is None:
		if getattr(sv_game.ge, "edicts", None) is not None:
			num_edicts = len(sv_game.ge.edicts)
		else:
			num_edicts = shared.MAX_EDICTS

	for entnum in range(1, num_edicts):
		svent = server_h.EDICT_NUM(entnum)
		if not svent.inuse:
			continue
		if not svent.s.modelindex and not svent.s.sound and not svent.s.effects:
			continue
		svent.s.number = entnum

		# take current state as baseline
		shared.VectorCopy(svent.s.origin, svent.s.old_origin)
		if entnum >= len(sv.baselines):
			sv.baselines.extend([None] * (entnum + 1 - len(sv.baselines)))
		sv.baselines[entnum] = copy.deepcopy(svent.s)


# =================
# SV_CheckForSavegame
# =================
def SV_CheckForSavegame ():

	pass
	"""
	char		name[MAX_OSPATH];
	FILE		*f;
	int			i;

	if (sv_noreload->value)
		return;

	if (Cvar_VariableValue ("deathmatch"))
		return;

	Com_sprintf (name, sizeof(name), "%s/save/current/%s.sav", FS_Gamedir(), sv.name);
	f = fopen (name, "rb");
	if (!f)
		return;		// no savegame

	fclose (f);

	SV_ClearWorld ();

	// get configstrings and areaportals
	SV_ReadLevelFile ();

	if (!sv.loadgame)
	{	// coming back to a level after being in a different
		// level, so run it for ten seconds

		// rlava2 was sending too many lightstyles, and overflowing the
		// reliable data. temporarily changing the server state to loading
		// prevents these from being passed down.
		server_state_t		previousState;		// PGM

		previousState = sv.state;				// PGM
		sv.state = ss_loading;					// PGM
		for (i=0 ; i<100 ; i++)
			ge->RunFrame ();

		sv.state = previousState;				// PGM
	}
	"""


# =================
# SV_SpawnServer
#
# Change the server to a new map, taking all connected
# clients along with it.
#
# =================
def SV_SpawnServer (server, spawnpoint, serverstate, attractloop, loadgame): #char *, char *, server_state_t, qboolean, qboolean

	#int			i;
	#unsigned	checksum;

	if attractloop:
		cvar.Cvar_Set ("paused", "0")

	clientserver.Com_Printf ("------- Server Initialization -------\n")

	clientserver.Com_DPrintf ("SpawnServer: {}\n".format(server))

	if sv.demofile:
		filesystem.FS_FCloseFile (sv.demofile)
		sv.demofile = 0

	svs.spawncount+=1		# any partially connected client will be
							# restarted
	sv.state = server_h.server_state_t.ss_dead
	clientserver.Com_SetServerState (sv.state.value)

	# wipe the entire per-level structure
	#memset (&sv, 0, sizeof(sv));
	sv.clear()
	svs.realtime = 0
	sv.loadgame = loadgame
	sv.attractloop = attractloop

	
	# save name for levels that don't set message
	sv.configstrings[shared.CS_NAME] = server
	if cvar.Cvar_VariableValue ("deathmatch"):
	
		sv.configstrings[shared.CS_AIRACCEL] = str(int(sv_main.sv_airaccelerate.value))
		pmove.pm_airaccelerate = sv_main.sv_airaccelerate.value
	
	else:
	
		sv.configstrings[shared.CS_AIRACCEL] = "0"
		pmove.pm_airaccelerate = 0
	
	szone.SZ_Init (sv.multicast, common_h.MAX_MSGLEN)

	sv.name = server

	# leave slots at start for clients only
	for client in svs.clients: 
	
		# needs to reconnect
		if client.state.value > server_h.client_state_t.cs_connected.value:
			client.state = server_h.client_state_t.cs_connected
		client.lastframe = -1

	sv.time = 1000;
	
	sv.name = server
	sv.configstrings[shared.CS_NAME] = server
	
	if serverstate != server_h.server_state_t.ss_game:

		while len(sv.models) < 2: sv.models.append(None)
		sv.models[1], checksum = collision.CM_LoadMap ("", False)	# no real map
	
	else:
		sv.configstrings[shared.CS_MODELS+1] = "maps/{}.bsp".format(server)
		while len(sv.models) < 2: sv.models.append(None)
		sv.models[1], checksum = collision.CM_LoadMap (sv.configstrings[shared.CS_MODELS+1], False)
	
	sv.configstrings[shared.CS_MAPCHECKSUM] = "{:d}".format(checksum)

	#
	# clear physics interaction links
	#
	sv_world.SV_ClearWorld ()
	
	for i in range(1, collision.CM_NumInlineModels()):
	
		sv.configstrings[shared.CS_MODELS+1+i] = "*%i" % i
		sv.models[i+1] = collision.CM_InlineModel (sv.configstrings[shared.CS_MODELS+1+i])
	
	#
	# spawn the rest of the entities on the map
	#	

	# precache and static commands can be issued during
	# map initialization
	sv.state = server_h.server_state_t.ss_loading
	clientserver.Com_SetServerState (sv.state.value)

	# load and spawn all other entities
	sv_game.ge.SpawnEntities (sv.name, collision.CM_EntityString(), spawnpoint)

	# run two frames to allow everything to settle
	sv_game.ge.RunFrame ()
	sv_game.ge.RunFrame ()

	"""
	# load and spawn all other entities
	ge->SpawnEntities ( sv.name, CM_EntityString(), spawnpoint )

	# run two frames to allow everything to settle
	ge->RunFrame ()
	ge->RunFrame ()
	"""
	# all precaches are complete
	sv.state = serverstate
	clientserver.Com_SetServerState (sv.state.value)
	
	# create a baseline for more efficient communications
	SV_CreateBaseline ()

	# check for a savegame
	SV_CheckForSavegame ()
	
	# set serverinfo variable
	cvar.Cvar_FullSet ("mapname", sv.name, shared.CVAR_SERVERINFO | shared.CVAR_NOSET)

	clientserver.Com_Printf ("-------------------------------------\n")


"""
/*
 * A brand new game has been started
 */
static void
SV_ClearGamemodeCvar(char *name, char *msg, int flags)
{
	Cvar_FullSet(name, "0", flags);

	strcat(msg, name);
	strcat(msg, " ");
}
"""

r"""
static int
SV_ChooseGamemode(void)
{
	char msg[32], *choice;
	int gamemode;

	*msg = 0;

	if (Cvar_VariableValue("deathmatch"))
	{
		if (Cvar_VariableValue("coop"))
		{
			SV_ClearGamemodeCvar("coop", msg, CVAR_SERVERINFO | CVAR_LATCH);
		}

		if (Cvar_VariableValue("singleplayer"))
		{
			SV_ClearGamemodeCvar("singleplayer", msg, 0);
		}

		choice = "deathmatch";
		gamemode = GAMEMODE_DM;
	}
	else if (Cvar_VariableValue("coop"))
	{
		if (Cvar_VariableValue("singleplayer"))
		{
			SV_ClearGamemodeCvar("singleplayer", msg, 0);
		}

		choice = "coop";
		gamemode = GAMEMODE_COOP;
	}
	else
	{
		if (dedicated->value && !Cvar_VariableValue("singleplayer"))
		{
			Cvar_FullSet("deathmatch", "1", CVAR_SERVERINFO | CVAR_LATCH);

			choice = "deathmatch";
			gamemode = GAMEMODE_DM;
		}
		else
		{
			Cvar_FullSet("singleplayer", "1", CVAR_SERVERINFO | CVAR_LATCH);

			choice = "singleplayer";
			gamemode = GAMEMODE_SP;
		}
	}

	if (*msg)
	{
		Com_Printf("Gamemode ambiguity: Chose: %s, ignored: %s\n", choice, msg);
	}

	return gamemode;
}
"""

"""
==============
SV_InitGame

A brand new game has been started
==============
"""
def SV_InitGame ():

	#int		i;
	#edict_t	*ent;
	#char	idmaster[32];

	if svs.initialized:
	
		# cause any connected clients to reconnect
		sv_main.SV_Shutdown ("Server restarted\n", True)
	
	else:
	
		# make sure the client is down
		cl_main.CL_Drop ()
		cl_scrn.SCR_BeginLoadingPlaque ()

	# Hack different from standard quake 2. Why?	
	szone.SZ_Init (sv.multicast, common_h.MAX_MSGLEN)

	# get any latched variable changes (maxclients, etc)
	cvar.Cvar_GetLatchedVars ()

	svs.initialized = True

	if cvar.Cvar_VariableValue ("coop") and cvar.Cvar_VariableValue ("deathmatch"):
	
		clientserver.Com_Printf("Deathmatch and Coop both set, disabling Coop\n");
		cvar.Cvar_FullSet ("coop", "0",  shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	

	# dedicated servers are can't be single player and are usually DM
	# so unless they explicity set coop, force it to deathmatch
	if frame.dedicated.value:
	
		if cvar.Cvar_VariableValue ("coop") != 0:
			cvar.Cvar_FullSet ("deathmatch", "1",  shared.CVAR_SERVERINFO | shared.CVAR_LATCH);
	
	# init clients
	if cvar.Cvar_VariableValue ("deathmatch"):
	
		if sv_main.maxclients.value <= 1:
			cvar.Cvar_FullSet ("maxclients", "8", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
		elif sv_main.maxclients.value > shared.MAX_CLIENTS:
			cvar.Cvar_FullSet ("maxclients", "%i" % shared.MAX_CLIENTS, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	
	elif cvar.Cvar_VariableValue ("coop"):
	
		if sv_main.maxclients.value <= 1 or sv_main.maxclients.value > 4:
			cvar.Cvar_FullSet ("maxclients", "4", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
		#ifdef COPYPROTECT
		#if (!sv.attractloop && !common.dedicated->value)
		#	Sys_CopyProtect ();
		#endif
	
	else:	# non-deathmatch, non-coop is one player
	
		cvar.Cvar_FullSet ("maxclients", "1", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
		#ifdef COPYPROTECT
		#if (!sv.attractloop)
		#	Sys_CopyProtect ();
		#endif
	
	svs.spawncount = random.randint(0, 1 << 32)
	svs.clients = []
	for i in range(int(sv_main.maxclients.value)):
		svs.clients.append(server_h.client_t())
	svs.num_client_entities = int(sv_main.maxclients.value*common_h.UPDATE_BACKUP*64)
	svs.client_entities = []
	for i in range(svs.num_client_entities):
		svs.client_entities.append(shared.entity_state_t())

	# init network stuff
	net_udp.NET_Config (sv_main.maxclients.value > 1)
	"""
	# heartbeats will always be sent to the id master
	svs.last_heartbeat = -99999;		// send immediately
	Com_sprintf(idmaster, sizeof(idmaster), "192.246.40.37:%i", PORT_MASTER);
	NET_StringToAdr (idmaster, &master_adr[0]);
	"""
	# init game
	sv_game.SV_InitGameProgs ()
	"""
	for (i=0 ; i<sv_main.maxclients.value ; i++)
	{
		ent = EDICT_NUM(i+1);
		ent->s.number = i+1;
		memset (&svs.clients[i].lastcmd, 0, sizeof(svs.clients[i].lastcmd));
	}


/*
======================
SV_Map

  the full syntax is:

  map [*]<map>$<startspot>+<nextserver>

command from the console or progs.
Map can also be a.cin, .pcx, or .dm2 file
Nextserver is used to allow a cinematic to play, then proceed to
another level:

	map tram.cin+jail_e3
======================
"""
def SV_Map ( attractloop, levelstring, loadgame, isautosave=False): #qboolean, char *, qboolean, qboolean

	#char	level[MAX_QPATH];
	#char	*ch;
	#int		l;
	#char	spawnpoint[MAX_QPATH];
	spawnpoint = ""
	
	sv.loadgame = loadgame
	sv.attractloop = attractloop

	if sv.state == server_h.server_state_t.ss_dead and not sv.loadgame:
		SV_InitGame ()	# the game is just starting

	level = levelstring

	# if there is a + in the map, set nextserver to the remainder
	ch = level.find("+")
	if ch != -1:
	
		cvar.Cvar_Set ("nextserver", "gamemap \"{}\"".format(level[ch+1:]))
		level = level[:ch]
	
	else:
		cvar.Cvar_Set ("nextserver", "");

	#ZOID special hack for end game screen in coop mode
	if cvar.Cvar_VariableValue ("coop") and not shared_c.Q_stricmp(level, "victory.pcx"):
		cvar.Cvar_Set ("nextserver", "gamemap \"*base1\"")

	# if there is a $, use the remainder as a spawnpoint
	ch = level.find("$")
	if ch != -1:

		spawnpoint = level[ch+1:]
		level = level[:ch]
	
	else:
		spawnpoint = ""

	# skip the end-of-unit flag if necessary
	if len(level) > 0 and level[0] == '*':
		level = level[1:]

	l = len(level)
	if l > 4 and level[-4:] == ".cin":

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		SV_SpawnServer (level, spawnpoint, server_h.server_state_t.ss_cinematic, attractloop, loadgame)
	
	elif l > 4 and level[-4:] == ".dm2":

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		SV_SpawnServer (level, spawnpoint, server_h.server_state_t.ss_demo, attractloop, loadgame)
	
	elif l > 4 and level[-4:] == ".pcx":

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		SV_SpawnServer (level, spawnpoint, server_h.server_state_t.ss_pic, attractloop, loadgame)
	
	else:

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		sv_send.SV_SendClientMessages ()
		SV_SpawnServer (level, spawnpoint, server_h.server_state_t.ss_game, attractloop, loadgame)
		cmdparser.Cbuf_CopyToDefer ()
	
	sv_send.SV_BroadcastCommand ("reconnect\n")
