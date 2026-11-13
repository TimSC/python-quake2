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
from common import net_channel
from common.header import common as common_h
from q2data import bsp as q2bsp
from common.header import shared

"""
#include "../../common/header/common.h"
#include "../../game/header/game.h"
"""

MAX_MASTERS = 8
LATENCY_COUNTS = 16
RATE_MESSAGES = 10

# MAX_CHALLENGES is made large to prevent a denial
# of service attack that could cycle all of them
# out before legitimate users connected
MAX_CHALLENGES = 1024

# MAX_TOKEN_CHARS was 128. YQ2 bumped it to 1024, since we
# need to support some very long cvars like gl_nolerp_list.
# Keep structs used in savegames at 128, otherwise older
# savegames would be broken.
MAX_SAVE_TOKEN_CHARS = 128


SV_OUTPUTBUF_LENGTH = (common_h.MAX_MSGLEN - 16)

def EDICT_NUM(n): #define EDICT_NUM(n) ((edict_t *)((byte *)ge->edicts + ge->edict_size * (n)))
	from server import sv_game	# Q2PORT: imported here; sv_game's import chain needs this header loaded first
	return sv_game.ge.edicts[n]

def CL_EDICT(cl): #define CL_EDICT(cl) EDICT_NUM(1 + ((cl) - svs.clients))
	from server import sv_init	# Q2PORT: imported here, sv_init imports this header
	return EDICT_NUM(1 + sv_init.svs.clients.index(cl))

def CLNUM_EDICT(i): return EDICT_NUM(i + 1) #define CLNUM_EDICT(i) EDICT_NUM(i + 1)

def NUM_FOR_EDICT(e): #define NUM_FOR_EDICT(e) (((byte *)(e) - (byte *)ge->edicts) / ge->edict_size)
	from server import sv_game	# Q2PORT: imported here; sv_game's import chain needs this header loaded first
	return sv_game.ge.edicts.index(e)

class server_state_t(Enum):

	ss_dead = 0            # no map loaded
	ss_loading = 1         # spawning level edicts
	ss_game = 2            # actively running
	ss_cinematic = 3
	ss_demo = 4
	ss_pic = 5

class server_t(object):

	def __init__(self):

		self.clear()

	def clear(self):	# Q2PORT: memset(&sv, 0, sizeof(sv))

		self.state = server_state_t.ss_dead #server_state_t, precache commands are only valid during load

		self.attractloop = False #qboolean, running cinematics and demos for the local system only
		self.loadgame = False #qboolean, client begins should reuse existing entity

		self.time = 0 #unsigned, always sv.framenum * 100 msec
		self.framenum = 0 #int

		self.name = "" #char [MAX_QPATH], map name, or cinematic name
		self.models = [] #struct cmodel_s *[MAX_MODELS]
		for i in range(shared.MAX_MODELS):
			self.models.append(shared.cmodel_t())

		self.configstrings_overflow = [] #stringlist_t, Q2PORT: a Python list
		self.configstrings = [] #char [MAX_CONFIGSTRINGS][MAX_QPATH]
		for i in range(shared.MAX_CONFIGSTRINGS):
			self.configstrings.append("")
		self.baselines = [] #entity_state_t *, grown by SV_BaselineForEntity
		self.numbaselines = 0 #int

		# the multicast buffer is used to send a message to a set of clients
		# it is only used to marshall data until SV_Multicast is called
		self.multicast = common_h.sizebuf_t() #sizebuf_t
		#byte multicast_buf[MAX_MSGLEN];

		# demo server information
		self.demofile = 0 #fileHandle_t
		self.timedemo = False #qboolean, don't time sync

class client_state_t(Enum):

	cs_free = 0        # can be reused for a new connection
	cs_zombie = 1      # client has been disconnected, but don't reuse
	                   # connection for a couple seconds
	cs_connected = 2   # has been assigned to a client_t, but not in game yet
	cs_spawned = 3     # client is fully in game

class client_frame_t(object):

	def __init__(self):

		self.areabytes = 0 #int
		self.areabits = bytearray(q2bsp.MAX_MAP_AREAS // 8) #byte [MAX_MAP_AREAS / 8], portalarea visibility bits
		self.ps = shared.player_state_t() #player_state_t
		self.num_entities = 0 #int
		self.first_entity = 0 #int, into the circular sv_packet_entities[]
		self.senttime = 0 #int, for ping calculations

class client_t(object):

	def __init__(self):

		self.state = client_state_t.cs_free #client_state_t

		self.userinfo = "" #char [MAX_INFO_STRING], name, etc

		self.lastframe = -1 #int, for delta compression
		self.lastcmd = None #usercmd_t, for filling in big drops

		self.commandMsec = 0 #int, every seconds this is reset, if user
		                     # commands exhaust it, assume time cheating

		self.frame_latency = [0] * LATENCY_COUNTS #int [LATENCY_COUNTS]
		self.ping = 0 #int

		self.message_size = [0] * RATE_MESSAGES #int [RATE_MESSAGES], used to rate drop packets
		self.rate = 5000 #int
		self.surpressCount = 0 #int, number of messages rate supressed

		self.name = "" #char [32], extracted from userinfo, high bits masked

		# The datagram is written to by sound calls, prints,
		# temp ents, etc. It can be harmlessly overflowed.
		self.datagram = common_h.sizebuf_t() #sizebuf_t
		#byte datagram_buf[MAX_MSGLEN];

		self.frames = [client_frame_t() for _ in range(common_h.UPDATE_BACKUP)] #client_frame_t [UPDATE_BACKUP], updates can be delta'd from here

		self.download = None #byte *, file being downloaded
		self.downloadsize = 0 #int, total bytes (can't use EOF because of paks)
		self.downloadcount = 0 #int, bytes sent

		self.lastmessage = 0 #int, sv.framenum when packet was last received
		self.lastconnect = 0 #int

		self.challenge = 0 #int, challenge of this user, randomly generated

		self.netchan = net_channel.NetChannel() #netchan_t

		# per-frame caches for SV_Multicast fanout
		self.cached_origin = [0.0, 0.0, 0.0] #vec3_t
		self.cached_leafnum = 0 #int
		self.cached_area = 0 #int
		self.cached_cluster = 0 #int
		self.cached_framenum = 0 #int

class challenge_t(object):

	def __init__(self):

		self.adr = common_h.netadr_t() #netadr_t
		self.challenge = 0 #int
		self.time = 0 #int

class server_static_t(object):

	def __init__(self):

		self.clear()

	def clear(self):	# Q2PORT: memset(&svs, 0, sizeof(svs))

		self.initialized = False #qboolean, sv_init has completed
		self.realtime = 0 #int, always increasing, no clamping, etc

		self.mapcmd = "" #char [MAX_SAVE_TOKEN_CHARS], ie: *intro.cin+base

		self.spawncount = 0 #int, incremented each server start
		                    # used to check late spawns

		self.clients = [] #client_t *, [maxclients->value];
		self.num_client_entities = 0 #int, maxclients->value*UPDATE_BACKUP*MAX_PACKET_ENTITIES
		self.next_client_entities = 0 #int, next client_entity to use
		self.client_entities = [] #entity_state_t *, [num_client_entities]

		self.last_heartbeat = 0 #int

		self.challenges = [challenge_t() for _ in range(MAX_CHALLENGES)] #challenge_t [MAX_CHALLENGES], to prevent invalid IPs from connecting

		# serverrecord values
		self.demofile = None #FILE *
		self.demo_multicast = common_h.sizebuf_t() #sizebuf_t
		#byte demo_multicast_buf[MAX_MSGLEN];

		self.gamemode = 0 #int

GAMEMODE_SP = 1
GAMEMODE_COOP = 2
GAMEMODE_DM = 3

class redirect_t(Enum):	#typedef enum {RD_NONE, RD_CLIENT, RD_PACKET} redirect_t;
	RD_NONE = 0
	RD_CLIENT = 1
	RD_PACKET = 2

# loadtime optimizations

OPTIMIZE_MSGUTIL = 1
OPTIMIZE_SENDRATE = 2
OPTIMIZE_RECONNECT = 4
OPTIMIZE_HUDSEND = 8
OPTIMIZE_CSBASE = 16
OPTIMIZE_MASK_ALL = 31
