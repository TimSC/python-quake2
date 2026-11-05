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
import copy
import random
import struct
from enum import Enum
from server import sv_main, sv_send, sv_game, sv_world, sv_game
from client import cl_main, cl_scrn
from qcommon import cvar, common, cmd, qcommon, cmodel, pmove
from game import q_shared
from linux import net_udp
"""
#include "server.h"

"""
MAX_MASTERS	= 8				# max recipients for heartbeat packets

class server_state_t(Enum):
	ss_dead = 0			# no map loaded
	ss_loading = 1			# spawning level edicts
	ss_game = 2			# actively running
	ss_cinematic = 3
	ss_demo = 4
	ss_pic = 5

# some qc commands are only valid before the server has finished
# initializing (precache commands, static sounds / objects, etc)

class server_t(object):

	def __init__(self):

		self.clear()

	def clear(self):

		self.state = server_state_t.ss_dead #server_state_t, precache commands are only valid during load

		self.attractloop = False # qboolean	;		// running cinematics and demos for the local system only
		self.loadgame = False # qboolean	;			// client begins should reuse existing entity

		self.time = 0 # unsigned	;				// always sv.framenum * 100 msec
		self.framenum = 0 # int			;

		self.name = None # char		[MAX_QPATH];			// map name, or cinematic name
		self.models = [] # struct cmodel_s		*[q_shared.MAX_MODELS];
		for i in range(q_shared.MAX_MODELS):
			self.models.append(q_shared.cmodel_t())

		self.configstrings = [] # char		[MAX_CONFIGSTRINGS][MAX_QPATH];
		for i in range(q_shared.MAX_CONFIGSTRINGS):
			self.configstrings.append("")
		self.baselines = [] # entity_state_t	[MAX_EDICTS];
		for i in range(q_shared.MAX_EDICTS):
			self.baselines.append(q_shared.entity_state_t())

		# the multicast buffer is used to send a message to a set of clients
		# it is only used to marshall data until SV_Multicast is called
		self.multicast = qcommon.sizebuf_t() # sizebuf_t	;
		#self.multicast_buf = None # byte		[MAX_MSGLEN];

		# demo server information
		self.demofile = None # FILE		*;
		self.timedemo = False # qboolean	;		// don't time sync

		self.timebase = 0 #int, msec base for SV_GiveMsec
		self.nextsignon = 0 #float
		self.signonnum = 0 #int
		self.lastframe = 0 #float

def EDICT_NUM(n):
	return sv_game.ge.edicts[n]

#define NUM_FOR_EDICT(e) ( ((byte *)(e)-(byte *)ge->edicts ) / ge->edict_size)
def NUM_FOR_EDICT(e):
	return sv_game.ge.edicts.index(e)

class client_state_t(Enum):

	cs_free = 0			# can be reused for a new connection
	cs_zombie = 1		# client has been disconnected, but don't reuse
						# connection for a couple seconds
	cs_connected = 2	# has been assigned to a client_t, but not in game yet
	cs_spawned = 3		# client is fully in game

"""
typedef struct
{
	int					areabytes;
	byte				areabits[MAX_MAP_AREAS/8];		// portalarea visibility bits
	player_state_t		ps;
	int					num_entities;
	int					first_entity;		// into the circular sv_packet_entities[]
	int					senttime;			// for ping calculations
} client_frame_t;

#define	LATENCY_COUNTS	16
#define	RATE_MESSAGES	10
"""
LATENCY_COUNTS	= 16
RATE_MESSAGES	= 10

#typedef struct
#{
#	int				areabytes;
#	byte			areabits[MAX_MAP_AREAS/8];		// portalarea visibility bits
#	player_state_t	ps;
#	int				num_entities;
#	int				first_entity;		// into the circular sv_packet_entities[]
#	int				senttime;			// for ping calculations
#} client_frame_t;
class client_frame_t(object):

	def __init__(self):
		self.areabytes = 0 #int
		self.areabits = bytearray(32) #byte[MAX_MAP_AREAS/8], portalarea visibility bits
		self.ps = q_shared.player_state_t()
		self.num_entities = 0 #int
		self.first_entity = 0 #int, into the circular sv_packet_entities[]
		self.senttime = 0 #int, for ping calculations

class client_t(object):

	def __init__(self):

		self.state = client_state_t.cs_free

		self.userinfo = "" #char[MAX_INFO_STRING], name, etc
		self.lastframe = -1 #int, for delta compression
		self.lastcmd = None #usercmd_t, for filling in big drops
		self.commandMsec = 0 #int, every seconds this is reset, if user commands exhaust it, assume time cheating
		self.frame_latency = [] #int[LATENCY_COUNTS]
		for i in range(LATENCY_COUNTS):
			self.frame_latency.append(0)
		self.ping = 0 #int
		self.message_size = [] #int[RATE_MESSAGES], used to rate drop packets
		for i in range(RATE_MESSAGES):
			self.message_size.append(0)
		self.rate = 5000 #int
		self.surpressCount = 0 #int, number of messages rate supressed

		self.edict = None #edict_t*, EDICT_NUM(clientnum+1)
		
		self.name = None #char[32];			// extracted from userinfo, high bits masked
		self.messagelevel = None #int;		// for filtering printed messages
		
		# The datagram is written to by sound calls, prints, temp ents, etc.
		# It can be harmlessly overflowed.
		
		self.datagram = qcommon.sizebuf_t()

		self.download = None #byte *, file being downloaded
		self.downloadsize = 0 #int, total bytes (can't use EOF because of paks)
		self.downloadcount = 0 #int, bytes sent
		self.lastmessage = 0 #int, sv.framenum when packet was last received
		self.lastconnect = 0 #int
		self.challenge = 0 #int, challenge of this user, randomly generated
		self.frames = [client_frame_t() for _ in range(qcommon.UPDATE_BACKUP)] #client_frame_t[UPDATE_BACKUP], updates can be delta'd from here

		self.netchan = qcommon.netchan_t()


"""
// a client can leave the server in one of four ways:
// dropping properly by quiting or disconnecting
// timing out if no valid messages are received for timeout.value seconds
// getting kicked off by the server operator
// a program error, like an overflowed reliable buffer

//=============================================================================

// MAX_CHALLENGES is made large to prevent a denial
// of service attack that could cycle all of them
// out before legitimate users connected
#define	MAX_CHALLENGES	1024

typedef struct
{
	netadr_t	adr;
	int			challenge;
	int			time;
} challenge_t;

"""
MAX_CHALLENGES	= 1024

class challenge_t(object):

	def __init__(self):

		self.adr = qcommon.netadr_t() #netadr_t
		self.challenge = 0 #int
		self.time = 0 #int

class server_static_t(object):

	def __init__(self):

		self.clear()

	def clear(self): # memset (&svs, 0, sizeof(svs))

		self.initialized = False # qboolean, sv_init has completed
		self.realtime = 0 # int, always increasing, no clamping, etc

		self.mapcmd = None # char [MAX_TOKEN_CHARS], ie: *intro.cin+base 

		self.spawncount = 0 # int, incremented each server start
												# used to check late spawns

		self.clients = [] 					# client_t	*, [maxclients->value];
		self.num_client_entities = 0 		# int, maxclients->value*UPDATE_BACKUP*MAX_PACKET_ENTITIES
		self.next_client_entities = 0 		# int, next client_entity to use
		self.client_entities = [] 			# entity_state_t	*, [num_client_entities]

		self.last_heartbeat = 0 # int

		self.challenges = [] # challenge_t	[MAX_CHALLENGES], to prevent invalid IPs from connecting
		for i in range(MAX_CHALLENGES):
			self.challenges.append(challenge_t())

		# serverrecord values
		self.demofile = None # FILE		*
		self.demo_multicast = qcommon.sizebuf_t() # sizebuf_t
		self.demo_multicast_buf = None # byte		[MAX_MSGLEN]



svs = server_static_t()				# persistant server info
sv = server_t()					# local server
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
		common.Com_Error (q_shared.ERR_DROP, "*Index: overflow")

	sv.configstrings[start+i] = name[:q_shared.MAX_QPATH] # strncpy (sv.configstrings[start+i], name, sizeof(sv.configstrings[i]));

	if sv.state != server_state_t.ss_loading:
		# send the update to everyone
		common.SZ_Clear (sv.multicast)
		common.MSG_WriteChar (sv.multicast, struct.pack("b", qcommon.svc_ops_e.svc_configstring.value))
		common.MSG_WriteShort (sv.multicast, start+i)
		common.MSG_WriteString (sv.multicast, name.encode('ascii'))
		sv_send.SV_Multicast (q_shared.vec3_origin, q_shared.multicast_t.MULTICAST_ALL_R)
	
	return i


def SV_ModelIndex (name): #char *

	return SV_FindIndex (name, q_shared.CS_MODELS, q_shared.MAX_MODELS, True)


def SV_SoundIndex (name): #char *

	return SV_FindIndex (name, q_shared.CS_SOUNDS, q_shared.MAX_SOUNDS, True)


def SV_ImageIndex (name): #char *

	return SV_FindIndex (name, q_shared.CS_IMAGES, q_shared.MAX_IMAGES, True)


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
			num_edicts = q_shared.MAX_EDICTS

	for entnum in range(1, num_edicts):
		svent = EDICT_NUM(entnum)
		if not svent.inuse:
			continue
		if not svent.s.modelindex and not svent.s.sound and not svent.s.effects:
			continue
		svent.s.number = entnum

		# take current state as baseline
		q_shared.VectorCopy(svent.s.origin, svent.s.old_origin)
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

	common.Com_Printf ("------- Server Initialization -------\n")

	common.Com_DPrintf ("SpawnServer: {}\n".format(server))

	if sv.demofile is not None:
		sv.demofile = None

	svs.spawncount+=1		# any partially connected client will be
							# restarted
	sv.state = server_state_t.ss_dead
	common.Com_SetServerState (sv.state.value)

	# wipe the entire per-level structure
	#memset (&sv, 0, sizeof(sv));
	sv.clear()
	svs.realtime = 0
	sv.loadgame = loadgame
	sv.attractloop = attractloop

	
	# save name for levels that don't set message
	sv.configstrings[q_shared.CS_NAME] = server
	if cvar.Cvar_VariableValue ("deathmatch"):
	
		sv.configstrings[q_shared.CS_AIRACCEL] = str(int(sv_main.sv_airaccelerate.value))
		pmove.pm_airaccelerate = sv_main.sv_airaccelerate.value
	
	else:
	
		sv.configstrings[q_shared.CS_AIRACCEL] = "0"
		pmove.pm_airaccelerate = 0
	
	common.SZ_Init (sv.multicast, qcommon.MAX_MSGLEN)

	sv.name = server

	# leave slots at start for clients only
	for client in svs.clients: 
	
		# needs to reconnect
		if client.state.value > client_state_t.cs_connected.value:
			client.state = client_state_t.cs_connected
		client.lastframe = -1

	sv.time = 1000;
	
	sv.name = server
	sv.configstrings[q_shared.CS_NAME] = server
	
	if serverstate != server_state_t.ss_game:

		while len(sv.models) < 2: sv.models.append(None)
		sv.models[1], checksum = cmodel.CM_LoadMap ("", False)	# no real map
	
	else:
		sv.configstrings[q_shared.CS_MODELS+1] = "maps/{}.bsp".format(server)
		while len(sv.models) < 2: sv.models.append(None)
		sv.models[1], checksum = cmodel.CM_LoadMap (sv.configstrings[q_shared.CS_MODELS+1], False)
	
	sv.configstrings[q_shared.CS_MAPCHECKSUM] = "{:d}".format(checksum)

	#
	# clear physics interaction links
	#
	sv_world.SV_ClearWorld ()
	"""
	for (i=1 ; i< CM_NumInlineModels() ; i++)
	{
		Com_sprintf (sv.configstrings[CS_MODELS+1+i], sizeof(sv.configstrings[CS_MODELS+1+i]),
			"*%i", i);
		sv.models[i+1] = CM_InlineModel (sv.configstrings[CS_MODELS+1+i]);
	}
	"""
	#
	# spawn the rest of the entities on the map
	#	

	# precache and static commands can be issued during
	# map initialization
	sv.state = server_state_t.ss_loading
	common.Com_SetServerState (sv.state.value)

	# load and spawn all other entities
	sv_game.ge.SpawnEntities (sv.name, cmodel.CM_EntityString(), spawnpoint)

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
	common.Com_SetServerState (sv.state.value)
	
	# create a baseline for more efficient communications
	SV_CreateBaseline ()

	# check for a savegame
	SV_CheckForSavegame ()
	
	# set serverinfo variable
	cvar.Cvar_FullSet ("mapname", sv.name, q_shared.CVAR_SERVERINFO | q_shared.CVAR_NOSET)

	common.Com_Printf ("-------------------------------------\n")


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
		sv_main.SV_Shutdown ("Server restarted\n", true);
	
	else:
	
		# make sure the client is down
		cl_main.CL_Drop ()
		cl_scrn.SCR_BeginLoadingPlaque ()

	# Hack different from standard quake 2. Why?	
	common.SZ_Init (sv.multicast, qcommon.MAX_MSGLEN)

	# get any latched variable changes (maxclients, etc)
	cvar.Cvar_GetLatchedVars ()

	svs.initialized = True

	if cvar.Cvar_VariableValue ("coop") and cvar.Cvar_VariableValue ("deathmatch"):
	
		common.Com_Printf("Deathmatch and Coop both set, disabling Coop\n");
		cvar.Cvar_FullSet ("coop", "0",  CVAR_SERVERINFO | CVAR_LATCH);
	

	# dedicated servers are can't be single player and are usually DM
	# so unless they explicity set coop, force it to deathmatch
	if common.dedicated.value:
	
		if cvar.Cvar_VariableValue ("coop") != 0:
			cvar.Cvar_FullSet ("deathmatch", "1",  q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH);
	
	# init clients
	if cvar.Cvar_VariableValue ("deathmatch"):
	
		if sv_main.maxclients.value <= 1:
			cvar.Cvar_FullSet ("maxclients", "8", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)
		elif sv_main.maxclients.value > MAX_CLIENTS:
			cvar.Cvar_FullSet ("maxclients", va("%i", MAX_CLIENTS), q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)
	
	elif cvar.Cvar_VariableValue ("coop"):
	
		if sv_main.maxclients.value <= 1 or sv_main.maxclients.value > 4:
			cvar.Cvar_FullSet ("maxclients", "4", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)
		#ifdef COPYPROTECT
		#if (!sv.attractloop && !common.dedicated->value)
		#	Sys_CopyProtect ();
		#endif
	
	else:	# non-deathmatch, non-coop is one player
	
		cvar.Cvar_FullSet ("maxclients", "1", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)
		#ifdef COPYPROTECT
		#if (!sv.attractloop)
		#	Sys_CopyProtect ();
		#endif
	
	svs.spawncount = random.randint(0, 1 << 32)
	svs.clients = []
	for i in range(int(sv_main.maxclients.value)):
		svs.clients.append(client_t())
	svs.num_client_entities = int(sv_main.maxclients.value*qcommon.UPDATE_BACKUP*64)
	svs.client_entities = []
	for i in range(svs.num_client_entities):
		svs.client_entities.append(q_shared.entity_state_t())

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
		svs.clients[i].edict = ent;
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
def SV_Map ( attractloop, levelstring, loadgame): #qboolean, char *, qboolean

	#char	level[MAX_QPATH];
	#char	*ch;
	#int		l;
	#char	spawnpoint[MAX_QPATH];
	spawnpoint = ""
	
	sv.loadgame = loadgame
	sv.attractloop = attractloop

	if sv.state == server_state_t.ss_dead and not sv.loadgame:
		SV_InitGame ()	# the game is just starting

	level = levelstring

	# if there is a + in the map, set nextserver to the remainder
	ch = level.find("+")
	if ch != -1:
	
		level = level[:ch]
		cvar.Cvar_Set ("nextserver", "gamemap \"{}\"".format(level[ch+1:]))
	
	else:
		cvar.Cvar_Set ("nextserver", "");

	#ZOID special hack for end game screen in coop mode
	if cvar.Cvar_VariableValue ("coop") and not q_shared.Q_stricmp(level, "victory.pcx"):
		cvar.Cvar_Set ("nextserver", "gamemap \"*base1\"")

	# if there is a $, use the remainder as a spawnpoint
	ch = level.find("$")
	if ch != -1:

		spawnpoint = level[ch+1:]
		level = level[:ch]
	
	else:
		spawnpoint = ""

	# skip the end-of-unit flag if necessary
	if level[0] == '*':
		level = level[1:]

	l = len(level)
	if l > 4 and level[-4:] == ".cin":

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		SV_SpawnServer (level, spawnpoint, server_state_t.ss_cinematic, attractloop, loadgame)
	
	elif l > 4 and level[-4:] == ".dm2":

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		SV_SpawnServer (level, spawnpoint, server_state_t.ss_demo, attractloop, loadgame)
	
	elif l > 4 and level[-4:] == ".pcx":

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		SV_SpawnServer (level, spawnpoint, server_state_t.ss_pic, attractloop, loadgame)
	
	else:

		cl_scrn.SCR_BeginLoadingPlaque ()			# for local system
		sv_send.SV_BroadcastCommand ("changing\n")
		sv_send.SV_SendClientMessages ()
		SV_SpawnServer (level, spawnpoint, server_state_t.ss_game, attractloop, loadgame)
		cmd.Cbuf_CopyToDefer ()
	
	sv_send.SV_BroadcastCommand ("reconnect\n")


