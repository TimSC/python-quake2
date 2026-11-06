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
import struct
from client import cl_main
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
from common.shared import rand
from server.header import server as server_h
from server import sv_game
from server import sv_main
from server import sv_send
from server import sv_world
from server import sv_save
from client import cl_network
from client import cl_screen

"""
#include "header/server.h"
#include <limits.h>
"""

# initialize the entities array to at least this many entities
ALLOC_ENTITIES_MIN = 32
MAX_SV_ENTNUM = 32767 #SHRT_MAX

svs = server_h.server_static_t() # persistant server info
sv = server_h.server_t() # local server

def SV_AllocBaseline(entnum: int)->shared.entity_state_t: #int (returns static entity_state_t *)

	"""
	int nextpow2;
	"""

	if (entnum < 0) or (entnum > MAX_SV_ENTNUM):

		return None


	if entnum >= sv.numbaselines:

		nextpow2 = shared_c.NextPow2gt(entnum) if (sv.numbaselines or (entnum >= ALLOC_ENTITIES_MIN)) else \
			ALLOC_ENTITIES_MIN

		#sv.baselines = Z_Realloc(sv.baselines, nextpow2 * sizeof(entity_state_t));
		while len(sv.baselines) < nextpow2:
			sv.baselines.append(shared.entity_state_t())
		sv.numbaselines = nextpow2


	return sv.baselines[entnum]

def SV_FindIndex(name: str, start: int, max: int, create: bool)->int: #const char *, int, int, qboolean (returns static int)

	"""
	size_t len, space;
	int i;
	"""

	if name is None or not name:

		return 0


	i = 1
	while i < max and sv.configstrings[start + i]:

		if sv.configstrings[start + i] == name:

			return i

		i += 1


	if not create:

		return 0


	if i == max:

		if name not in sv.configstrings_overflow:

			if sv.state != server_h.server_state_t.ss_loading:

				clientserver.Com_Printf("Failed to load %s: configstrings overflowed\n", name)


			sv.configstrings_overflow.append(name)


		return 0


	space = shared.MAX_QPATH #sizeof(sv.configstrings[start + i]);
	length = len(name) #len = Q_strlcpy(sv.configstrings[start + i], name, space);

	if length >= space:

		sv.configstrings[start + i] = ""

		if name not in sv.configstrings_overflow:

			if sv.state != server_h.server_state_t.ss_loading:

				clientserver.Com_Printf("Failed to load %s: configstring too long: %d > %d\n",
					name, length, space - 1)


			sv.configstrings_overflow.append(name)


		return 0


	sv.configstrings[start + i] = name

	if sv.state != server_h.server_state_t.ss_loading:

		# send the update to everyone
		movemsg.MSG_WriteChar(sv.multicast, common_h.svc_ops_e.svc_configstring.value)
		movemsg.MSG_WriteConfigString(sv.multicast, start + i, name)
		sv_send.SV_Multicast(shared_c.vec3_origin, shared.multicast_t.MULTICAST_ALL_R)


	return i

def SV_ModelIndex(name: str)->int: #const char * (returns int)

	return SV_FindIndex(name, shared.CS_MODELS, shared.MAX_MODELS, True)

def SV_SoundIndex(name: str)->int: #const char * (returns int)

	return SV_FindIndex(name, shared.CS_SOUNDS, shared.MAX_SOUNDS, True)

def SV_ImageIndex(name: str)->int: #const char * (returns int)

	return SV_FindIndex(name, shared.CS_IMAGES, shared.MAX_IMAGES, True)

"""
 * Entity baselines are used to compress the update messages
 * to the clients -- only the fields that differ from the
 * baseline will be transmitted
"""
def SV_CreateBaseline(): #void

	"""
	entity_state_t *es;
	edict_t *svent;
	int entnum;
	"""

	for entnum in range(1, sv_game.ge.num_edicts):

		svent = server_h.EDICT_NUM(entnum)

		if not svent.inuse:

			continue


		if not svent.s.modelindex and not svent.s.sound and not svent.s.effects:

			continue


		svent.s.number = entnum

		# take current state as baseline
		shared.VectorCopy(svent.s.origin, svent.s.old_origin)

		es = SV_AllocBaseline(entnum)
		if es is not None:

			sv.baselines[entnum] = copy.deepcopy(svent.s) #*es = svent->s;

def SV_CheckForSavegame(isautosave: bool): #qboolean

	"""
	char name[MAX_OSPATH];
	FILE *f;
	int i;
	"""

	if sv_main.sv_noreload.value:

		return


	if cvar.Cvar_VariableValue("deathmatch"):

		return


	name = "{}/save/current/{}.sav".format(filesystem.FS_Gamedir(), sv.name)
	f = filesystem.Q_fopen(name, "rb")

	if f is None:

		return # no savegame


	f.close()

	sv_world.SV_ClearWorld()

	# get configstrings and areaportals
	sv_save.SV_ReadLevelFile()

	if not sv.loadgame or (sv.loadgame and isautosave):

		# coming back to a level after being in a different
		# level, so run it for ten seconds
		#server_state_t previousState;

		previousState = sv.state
		sv.state = server_h.server_state_t.ss_loading

		for i in range(100):

			sv_game.ge.RunFrame()


		sv.state = previousState

"""
 * Change the server to a new map, taking all connected
 * clients along with it.
"""
def SV_SpawnServer(server: str, spawnpoint: str, serverstate: server_h.server_state_t,
		attractloop: bool, loadgame: bool, isautosave: bool): #char *, char *, server_state_t, qboolean, qboolean, qboolean

	"""
	int i;
	unsigned checksum;
	"""

	if attractloop:

		cvar.Cvar_Set("paused", "0")


	clientserver.Com_Printf("------- server initialization ------\n")
	clientserver.Com_DPrintf("SpawnServer: %s\n", server)

	if sv.demofile:

		filesystem.FS_FCloseFile(sv.demofile)


	svs.spawncount += 1 # any partially connected client will be restarted
	sv.state = server_h.server_state_t.ss_dead
	clientserver.Com_SetServerState(sv.state.value)

	# wipe the entire per-level structure
	sv_main.SV_ClearBaselines()
	sv.clear() #memset(&sv, 0, sizeof(sv));
	svs.realtime = 0
	sv.loadgame = loadgame
	sv.attractloop = attractloop

	# save name for levels that don't set message
	sv.configstrings[shared.CS_NAME] = server

	if cvar.Cvar_VariableValue("deathmatch"):

		sv.configstrings[shared.CS_AIRACCEL] = "%g" % sv_main.sv_airaccelerate.value
		pmove.pm_airaccelerate = sv_main.sv_airaccelerate.value

	else:

		sv.configstrings[shared.CS_AIRACCEL] = "0"
		pmove.pm_airaccelerate = 0


	szone.SZ_Init(sv.multicast, common_h.MAX_MSGLEN) #SZ_Init(&sv.multicast, sv.multicast_buf, sizeof(sv.multicast_buf));

	sv.name = server

	# leave slots at start for clients only
	for i in range(int(sv_main.maxclients.value)):

		# needs to reconnect
		if svs.clients[i].state.value > server_h.client_state_t.cs_connected.value:

			svs.clients[i].state = server_h.client_state_t.cs_connected


		svs.clients[i].lastframe = -1


	sv.time = 1000

	sv.name = server
	sv.configstrings[shared.CS_NAME] = server

	if serverstate != server_h.server_state_t.ss_game:

		sv.models[1], checksum = collision.CM_LoadMap("", False) # no real map

	else:

		sv.configstrings[shared.CS_MODELS + 1] = "maps/{}.bsp".format(server)[:shared.MAX_QPATH - 1]
		sv.models[1], checksum = collision.CM_LoadMap(sv.configstrings[shared.CS_MODELS + 1],
				False)


	sv.configstrings[shared.CS_MAPCHECKSUM] = "%i" % checksum

	# clear physics interaction links
	sv_world.SV_ClearWorld()

	for i in range(1, collision.CM_NumInlineModels()):

		sv.configstrings[shared.CS_MODELS + 1 + i] = "*%i" % i
		sv.models[i + 1] = collision.CM_InlineModel(sv.configstrings[shared.CS_MODELS + 1 + i])


	# spawn the rest of the entities on the map
	sv.state = server_h.server_state_t.ss_loading
	clientserver.Com_SetServerState(sv.state.value)

	# load and spawn all other entities
	sv_game.ge.SpawnEntities(sv.name, collision.CM_EntityString(), spawnpoint)

	# run two frames to allow everything to settle
	sv_game.ge.RunFrame()
	sv_game.ge.RunFrame()

	# verify game didn't clobber important stuff
	if checksum != \
		shared_c.atoi(sv.configstrings[shared.CS_MAPCHECKSUM]):

		clientserver.Com_Error(shared.ERR_DROP, "Game DLL corrupted server configstrings")


	# all precaches are complete
	sv.state = serverstate
	clientserver.Com_SetServerState(sv.state.value)

	# create a baseline for more efficient communications
	SV_CreateBaseline()

	# check for a savegame
	SV_CheckForSavegame(isautosave)

	# set serverinfo variable
	cvar.Cvar_FullSet("mapname", sv.name, shared.CVAR_SERVERINFO | shared.CVAR_NOSET)

	clientserver.Com_Printf("------------------------------------\n\n")

"""
 * A brand new game has been started
"""
def SV_ClearGamemodeCvar(name: str, msg: list, flags: int): #char *, char *, int
	# Q2PORT: msg is a list the names are appended to

	cvar.Cvar_FullSet(name, "0", flags)

	msg.append(name)
	msg.append(" ")

def SV_ChooseGamemode()->int: #(returns static int)

	"""
	char msg[32], *choice;
	int gamemode;
	"""

	msg = []

	if cvar.Cvar_VariableValue("deathmatch"):

		if cvar.Cvar_VariableValue("coop"):

			SV_ClearGamemodeCvar("coop", msg, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)


		if cvar.Cvar_VariableValue("singleplayer"):

			SV_ClearGamemodeCvar("singleplayer", msg, 0)


		choice = "deathmatch"
		gamemode = server_h.GAMEMODE_DM

	elif cvar.Cvar_VariableValue("coop"):

		if cvar.Cvar_VariableValue("singleplayer"):

			SV_ClearGamemodeCvar("singleplayer", msg, 0)


		choice = "coop"
		gamemode = server_h.GAMEMODE_COOP

	else:

		if frame.dedicated.value and not cvar.Cvar_VariableValue("singleplayer"):

			cvar.Cvar_FullSet("deathmatch", "1", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)

			choice = "deathmatch"
			gamemode = server_h.GAMEMODE_DM

		else:

			cvar.Cvar_FullSet("singleplayer", "1", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)

			choice = "singleplayer"
			gamemode = server_h.GAMEMODE_SP



	if msg:

		clientserver.Com_Printf("Gamemode ambiguity: Chose: %s, ignored: %s\n", choice, "".join(msg))


	return gamemode

def SV_InitGame(): #void

	"""
	int i, gamemode;
	char idmaster[32];
	"""

	if svs.initialized:

		# cause any connected clients to reconnect
		sv_main.SV_Shutdown("Server restarted\n", True)

	#ifndef DEDICATED_ONLY
	else:

		# make sure the client is down
		cl_network.CL_Drop()
		cl_screen.SCR_BeginLoadingPlaque()

	#endif

	# get any latched variable changes (maxclients, etc)
	cvar.Cvar_GetLatchedVars()

	svs.initialized = True

	gamemode = SV_ChooseGamemode()

	# init clients
	if gamemode == server_h.GAMEMODE_DM:

		if sv_main.maxclients.value <= 1:

			cvar.Cvar_FullSet("maxclients", "8", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)

		elif sv_main.maxclients.value > shared.MAX_CLIENTS:

			cvar.Cvar_FullSet("maxclients", "%i" % shared.MAX_CLIENTS, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)


	elif gamemode == server_h.GAMEMODE_COOP:

		if (sv_main.maxclients.value <= 1) or (sv_main.maxclients.value > 4):

			cvar.Cvar_FullSet("maxclients", "4", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)


	else: # non-deathmatch, non-coop is one player

		cvar.Cvar_FullSet("maxclients", "1", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)


	svs.gamemode = gamemode
	svs.spawncount = rand.randk()
	svs.clients = [server_h.client_t() for i in range(int(sv_main.maxclients.value))] #Z_Malloc(sizeof(client_t) * maxclients->value);
	svs.num_client_entities = int(sv_main.maxclients.value * common_h.UPDATE_BACKUP * 64)
	svs.client_entities = [shared.entity_state_t() for i in range(svs.num_client_entities)]

	# init network stuff
	if frame.dedicated.value:

		if gamemode == server_h.GAMEMODE_SP:

			net_udp.NET_Config(True)

		else:

			net_udp.NET_Config((sv_main.maxclients.value > 1))


	else:

		net_udp.NET_Config((sv_main.maxclients.value > 1))


	# heartbeats will always be sent to the id master
	svs.last_heartbeat = -99999 # send immediately
	idmaster = "192.246.40.37:%i" % common_h.PORT_MASTER
	adr = net_udp.NET_StringToAdr(idmaster)
	if adr is not None:
		sv_main.master_adr[0] = adr

	# init game
	sv_game.SV_InitGameProgs()

	for i in range(int(sv_main.maxclients.value)):

		server_h.CLNUM_EDICT(i).s.number = i + 1
		svs.clients[i].lastcmd = shared.usercmd_t() #memset(&svs.clients[i].lastcmd, 0, sizeof(svs.clients[i].lastcmd));

"""
 * the full syntax is:
 *
 * map [*]<map>$<startspot>+<nextserver>
 *
 * command from the console or progs.
 * Map can also be a.cin, .pcx, or .dm2 file
 * Nextserver is used to allow a cinematic to play, then proceed to
 * another level:
 *
 *  map tram.cin+jail_e3
"""
def SV_Map(attractloop: bool, levelstring: str, loadgame: bool, isautosave: bool = False): #qboolean, char *, qboolean, qboolean

	"""
	char level[MAX_QPATH];
	char *ch;
	size_t l;
	char spawnpoint[MAX_QPATH];
	const char *ext;
	"""

	sv.loadgame = loadgame
	sv.attractloop = attractloop

	if (sv.state == server_h.server_state_t.ss_dead) and not sv.loadgame:

		SV_InitGame() # the game is just starting


	level = levelstring

	# if there is a + in the map, set nextserver to the remainder
	ch = level.find("+")

	if ch != -1:

		cvar.Cvar_Set("nextserver", "gamemap \"{}\"".format(level[ch + 1:]))
		level = level[:ch]

	else:

		# use next demo command if list of map commands as empty
		cvar.Cvar_Set("nextserver", cvar.Cvar_VariableString("nextdemo"))
		# and cleanup nextdemo
		cvar.Cvar_Set("nextdemo", "")


	# hack for end game screen in coop mode
	if cvar.Cvar_VariableValue("coop") and not shared_c.Q_stricmp(level, "victory.pcx"):

		cvar.Cvar_Set("nextserver", "gamemap \"*base1\"")


	# if there is a $, use the remainder as a spawnpoint
	ch = level.find("$")

	if ch != -1:

		spawnpoint = level[ch + 1:]
		level = level[:ch]

	else:

		spawnpoint = ""


	# skip the end-of-unit flag if necessary
	l = len(level)

	if level[:1] == '*':

		level = level[1:]
		l -= 1


	ext = None if (l <= 4) else level[l - 4:]

	if ext is not None and ext == ".cin":

		#ifndef DEDICATED_ONLY
		cl_screen.SCR_BeginLoadingPlaque() # for local system
		#endif
		sv_send.SV_BroadcastCommand("changing\n")
		SV_SpawnServer(level, spawnpoint, server_h.server_state_t.ss_cinematic, attractloop, loadgame, isautosave)

	elif ext is not None and ext == ".dm2":

		#ifndef DEDICATED_ONLY
		cl_screen.SCR_BeginLoadingPlaque() # for local system
		#endif
		sv_send.SV_BroadcastCommand("changing\n")
		SV_SpawnServer(level, spawnpoint, server_h.server_state_t.ss_demo, attractloop, loadgame, isautosave)

	elif ext is not None and (ext == ".pcx" or
					ext == ".tga" or
					ext == ".jpg" or
					ext == ".png"):

		#ifndef DEDICATED_ONLY
		cl_screen.SCR_BeginLoadingPlaque() # for local system
		#endif
		sv_send.SV_BroadcastCommand("changing\n")
		SV_SpawnServer(level, spawnpoint, server_h.server_state_t.ss_pic, attractloop, loadgame, isautosave)

	else:

		#ifndef DEDICATED_ONLY
		cl_screen.SCR_BeginLoadingPlaque() # for local system
		#endif
		sv_send.SV_BroadcastCommand("changing\n")

		# for some reason calling send messages here causes a lengthy reconnect delay
		if not (sv_main.SV_Optimizations() & server_h.OPTIMIZE_RECONNECT):

			sv_send.SV_SendClientMessages()
			sv_send.SV_SendPrepClientMessages()


		SV_SpawnServer(level, spawnpoint, server_h.server_state_t.ss_game, attractloop, loadgame, isautosave)
		cmdparser.Cbuf_CopyToDefer()


	sv_send.SV_BroadcastCommand("reconnect\n")
