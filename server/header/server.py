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

Main header file for the client

=======================================================================
"""
from __future__ import annotations

from enum import Enum
from common.header import common as common_h
from common.header import shared

"""
#include "../../common/header/common.h"
#include "../../game/header/game.h"
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
		for i in range(shared.MAX_MODELS):
			self.models.append(shared.cmodel_t())

		self.configstrings = [] # char		[MAX_CONFIGSTRINGS][MAX_QPATH];
		for i in range(shared.MAX_CONFIGSTRINGS):
			self.configstrings.append("")
		self.baselines = [] # entity_state_t	[MAX_EDICTS];
		for i in range(shared.MAX_EDICTS):
			self.baselines.append(shared.entity_state_t())

		# the multicast buffer is used to send a message to a set of clients
		# it is only used to marshall data until SV_Multicast is called
		self.multicast = common_h.sizebuf_t() # sizebuf_t	;
		#self.multicast_buf = None # byte		[MAX_MSGLEN];

		# demo server information
		self.demofile = 0 # fileHandle_t
		self.timedemo = False # qboolean	;		// don't time sync

		self.timebase = 0 #int, msec base for SV_GiveMsec
		self.nextsignon = 0 #float
		self.signonnum = 0 #int
		self.lastframe = 0 #float

"""
#include "server.h"

"""
def EDICT_NUM(n):
	from server import sv_game	# Q2PORT: imported here; sv_game's import chain needs this header loaded first
	return sv_game.ge.edicts[n]

def CL_EDICT(cl): #define CL_EDICT(cl) EDICT_NUM(1 + ((cl) - svs.clients))
	from server import sv_init	# Q2PORT: imported here, sv_init imports this header
	return EDICT_NUM(1 + sv_init.svs.clients.index(cl))

def CLNUM_EDICT(i): return EDICT_NUM(i + 1) #define CLNUM_EDICT(i) EDICT_NUM(i + 1)

#define NUM_FOR_EDICT(e) ( ((byte *)(e)-(byte *)ge->edicts ) / ge->edict_size)
def NUM_FOR_EDICT(e):
	from server import sv_game	# Q2PORT: imported here; sv_game's import chain needs this header loaded first
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
		self.ps = shared.player_state_t()
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

		
		self.name = None #char[32];			// extracted from userinfo, high bits masked
		self.messagelevel = None #int;		// for filtering printed messages
		
		# The datagram is written to by sound calls, prints, temp ents, etc.
		# It can be harmlessly overflowed.
		
		self.datagram = common_h.sizebuf_t()

		self.download = None #byte *, file being downloaded
		self.downloadsize = 0 #int, total bytes (can't use EOF because of paks)
		self.downloadcount = 0 #int, bytes sent
		self.lastmessage = 0 #int, sv.framenum when packet was last received
		self.lastconnect = 0 #int
		self.challenge = 0 #int, challenge of this user, randomly generated
		self.frames = [client_frame_t() for _ in range(common_h.UPDATE_BACKUP)] #client_frame_t[UPDATE_BACKUP], updates can be delta'd from here

		self.netchan = common_h.netchan_t()


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

		self.adr = common_h.netadr_t() #netadr_t
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
		self.demo_multicast = common_h.sizebuf_t() # sizebuf_t
		self.demo_multicast_buf = None # byte		[MAX_MSGLEN]

"""
// sv_main.c -- server main program

#include "server.h"
"""
"""
=============================================================================

Com_Printf redirection

=============================================================================
"""
SV_OUTPUTBUF_LENGTH = common_h.MAX_MSGLEN - 16
