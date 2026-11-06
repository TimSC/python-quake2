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

Here are the client, server and game are tied together.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from enum import Enum
from enum import Enum
from common.header import shared
from game.header import local

"""
// game.h -- game dll information visible to server
"""
GAME_API_VERSION	= 3

# edict->svflags
SVF_NOCLIENT = 0x00000001	# don't send entity to clients, even if it has effects
SVF_DEADMONSTER = 0x00000002	# treat as CONTENTS_DEADMONSTER for collision
SVF_MONSTER = 0x00000004	# treat as CONTENTS_MONSTER for collision

class solid_t(Enum):
	SOLID_NOT = 0		# no interaction with other objects
	SOLID_TRIGGER = 1	# only touch when inside, after moving
	SOLID_BBOX = 2	# touch on edge
	SOLID_BSP = 3	# bsp clip, touch on edge

# module-level aliases so `game.SOLID_*` resolves to the int values
# (matches the per-module `SOLID_* = solid_t.SOLID_*.value` definitions)
SOLID_NOT = solid_t.SOLID_NOT.value
SOLID_TRIGGER = solid_t.SOLID_TRIGGER.value
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_BSP = solid_t.SOLID_BSP.value

MAX_ENT_CLUSTERS = 16


class link_t(object):

	def __init__(self):
		self.prev = None #struct link_s *
		self.next = None #struct link_s *
		self.owner = None # the object this link is embedded in (stands in for STRUCT_FROM_LINK)


"""
// edict->svflags

#define	SVF_NOCLIENT			0x00000001	// don't send entity to clients, even if it has effects
#define	SVF_DEADMONSTER			0x00000002	// treat as CONTENTS_DEADMONSTER for collision
#define	SVF_MONSTER				0x00000004	// treat as CONTENTS_MONSTER for collision

// edict->solid values

typedef enum
{
SOLID_NOT,			// no interaction with other objects
SOLID_TRIGGER,		// only touch when inside, after moving
SOLID_BBOX,			// touch on edge
SOLID_BSP			// bsp clip, touch on edge
} solid_t;

//===============================================================

// link_t is only used for entity area links now
typedef struct link_s
{
	struct link_s	*prev, *next;
} link_t;

#define	MAX_ENT_CLUSTERS	16


typedef struct edict_s edict_t;
typedef struct gclient_s gclient_t;


#ifndef GAME_INCLUDE
"""
class gclient_s(object):

	def __init__(self):

		self.clear()

	def clear(self): # memset (client, 0, sizeof(*client))

		self.ps = shared.player_state_t()		# communicated by server to clients
		self.ping: int = 0

		#================================
		# private to game (from g_local.h struct gclient_s)
		self.pers = local.client_persistant_t()
		self.resp = local.client_respawn_t()
		self.old_pmove = shared.pmove_state_t()	# for detecting out-of-pmove changes

		self.showscores = False
		self.showinventory = False
		self.showhelp = False
		self.showhelpicon = False

		self.ammo_index = 0

		self.buttons = 0
		self.oldbuttons = 0
		self.latched_buttons = 0

		self.weapon_thunk = False

		self.newweapon = None #gitem_t *

		# sum up damage over an entire frame, so
		# shotgun blasts give a single big kick
		self.damage_armor = 0
		self.damage_parmor = 0
		self.damage_blood = 0
		self.damage_knockback = 0
		self.damage_from = np.zeros((3,), dtype=np.float32)

		self.killer_yaw = 0.0					# when dead, look at killer

		self.weaponstate = local.weaponstate_t.WEAPON_READY
		self.kick_angles = np.zeros((3,), dtype=np.float32)	# weapon kicks
		self.kick_origin = np.zeros((3,), dtype=np.float32)
		self.v_dmg_roll = 0.0
		self.v_dmg_pitch = 0.0
		self.v_dmg_time = 0.0				# damage kicks
		self.fall_time = 0.0
		self.fall_value = 0.0				# for view drop on fall
		self.damage_alpha = 0.0
		self.bonus_alpha = 0.0
		self.damage_blend = np.zeros((3,), dtype=np.float32)
		self.v_angle = np.zeros((3,), dtype=np.float32)		# aiming direction
		self.bobtime = 0.0					# so off-ground doesn't change it
		self.oldviewangles = np.zeros((3,), dtype=np.float32)
		self.oldvelocity = np.zeros((3,), dtype=np.float32)

		self.next_drown_time = 0.0
		self.old_waterlevel = 0
		self.breather_sound = 0

		self.machinegun_shots = 0			# for weapon raising

		# animation vars
		self.anim_end = 0
		self.anim_priority = 0
		self.anim_duck = False
		self.anim_run = False

		# powerup timers
		self.quad_framenum = 0.0
		self.invincible_framenum = 0.0
		self.breather_framenum = 0.0
		self.enviro_framenum = 0.0

		# power armor
		self.powerarmor_type = 0 #int, 0 = none, 1 = screen, 2 = shield
		self.powerarmor_time = 0.0 #float

		self.grenade_blew_up = False
		self.grenade_time = 0.0
		self.silencer_shots = 0
		self.weapon_sound = 0

		self.pickup_msg_time = 0.0

		self.flood_locktill = 0.0			# locked from talking
		self.flood_when = [0.0 for _ in range(10)]		# when messages were said
		self.flood_whenhead = 0				# head pointer for when said

		self.respawn_time = 0.0				# can respawn when time > this

		self.chase_target = None			# player we are chasing
		self.update_chase = False			# need to update chase info?

		# flood control (PGM addition)
		self.flood_locktill = 0.0			# locked from talking
		self.flood_when = [0.0 for _ in range(10)]	# when messages were said
		self.flood_whenhead = 0			# head pointer for when said


class edict_t(object):

	def __init__(self):


		"""
		entity_state_t	s;
		"""
		self.s = shared.entity_state_t()
		self.client = None # struct gclient_s *, NULL until a client slot is assigned
		"""
		qboolean	inuse;
		int			linkcount;

		# FIXME: move these fields to a server private sv_entity_t
		link_t		area;				// linked to a division node or leaf
		
		int			num_clusters;		// if -1, use headnode instead
		int			clusternums[MAX_ENT_CLUSTERS];
		int			headnode;			// unused if num_clusters != -1
		int			areanum, areanum2;

		#================================

		int			svflags;			// SVF_NOCLIENT, SVF_DEADMONSTER, SVF_MONSTER, etc
		vec3_t		mins, maxs;
		vec3_t		absmin, absmax, size;
		solid_t		solid;
		int			clipmask;
		edict_t		*owner;

		# the game dll can add anything it wants after
		# this point in the structure
		"""
		self.inuse = False
		self.linkcount = 0
		self.area = link_t() # FIXME: move these fields to a server private sv_entity_t
		self.num_clusters = 0
		self.clusternums = [0 for _ in range(MAX_ENT_CLUSTERS)]
		self.headnode = 0
		self.areanum = 0
		self.areanum2 = 0
		self.svflags = 0
		self.mins = np.zeros((3,), dtype=np.float32)
		self.maxs = np.zeros((3,), dtype=np.float32)
		self.absmin = np.zeros((3,), dtype=np.float32)
		self.absmax = np.zeros((3,), dtype=np.float32)
		self.size = np.zeros((3,), dtype=np.float32)
		self.solid = SOLID_NOT #solid_t, 0 as after memset
		self.clipmask = 0
		self.owner = None

		#================================
		# DO NOT MODIFY ANYTHING ABOVE THIS, THE SERVER
		# EXPECTS THE FIELDS IN THAT ORDER!
		# (game-local fields from g_local.h struct edict_s)
		self.movetype = 0
		self.flags = 0

		self.model = None
		self.freetime = 0.0				# sv.time when the object was freed

		# only used locally in game, not by server
		self.message = None
		self.classname = None
		self.spawnflags = 0

		self.timestamp = 0.0

		self.angle = 0.0				# set in qe3, -1 = up, -2 = down
		self.target = None
		self.targetname = None
		self.killtarget = None
		self.team = None
		self.pathtarget = None
		self.deathtarget = None
		self.combattarget = None
		self.target_ent = None

		self.speed = 0.0
		self.accel = 0.0
		self.decel = 0.0
		self.movedir = np.zeros((3,), dtype=np.float32)
		self.pos1 = np.zeros((3,), dtype=np.float32)
		self.pos2 = np.zeros((3,), dtype=np.float32)

		self.velocity = np.zeros((3,), dtype=np.float32)
		self.avelocity = np.zeros((3,), dtype=np.float32)
		self.mass = 0
		self.air_finished = 0.0
		self.gravity = 1.0				# per entity gravity multiplier (1.0 is normal)

		self.goalentity = None
		self.movetarget = None
		self.yaw_speed = 0.0
		self.ideal_yaw = 0.0

		self.nextthink = 0.0
		self.prethink = None
		self.think = None
		self.blocked = None
		self.touch = None
		self.use = None
		self.pain = None
		self.die = None

		self.touch_debounce_time = 0.0
		self.pain_debounce_time = 0.0
		self.damage_debounce_time = 0.0
		self.fly_sound_debounce_time = 0.0
		self.last_move_time = 0.0

		self.health = 0
		self.max_health = 0
		self.gib_health = 0
		self.deadflag = local.DEAD_NO
		self.show_hostile = False

		self.powerarmor_time = 0.0

		self.map = None				# target_changelevel

		self.viewheight = 0				# height above origin where eyesight is determined
		self.takedamage = 0
		self.dmg = 0
		self.radius_dmg = 0
		self.dmg_radius = 0.0
		self.sounds = 0
		self.count = 0

		self.chain = None
		self.enemy = None
		self.oldenemy = None
		self.activator = None
		self.groundentity = None
		self.groundentity_linkcount = 0
		self.teamchain = None
		self.teammaster = None

		self.mynoise = None			# can go in client only
		self.mynoise2 = None

		self.noise_index = 0
		self.noise_index2 = 0
		self.volume = 0.0
		self.attenuation = 0.0

		# timing variables
		self.wait = 0.0
		self.delay = 0.0				# before firing targets
		self.random = 0.0

		self.last_sound_time = 0.0 #float

		self.watertype = 0
		self.waterlevel = 0

		self.move_origin = np.zeros((3,), dtype=np.float32)
		self.move_angles = np.zeros((3,), dtype=np.float32)

		# move this to clientinfo?
		self.light_level = 0

		self.style = 0				# also used as areaportal number

		self.item = None			# for bonus items

		# common data blocks
		self.moveinfo = local.moveinfo_t()
		self.monsterinfo = local.monsterinfo_t()
"""
#endif		// GAME_INCLUDE

//===============================================================
"""
#
# functions provided by the main engine
#
class game_import_t(object):

	def __init__(self):

		"""
		// special messages
		void	(*bprintf) (int printlevel, char *fmt, ...);
		void	(*dprintf) (char *fmt, ...);
		void	(*cprintf) (edict_t *ent, int printlevel, char *fmt, ...);
		void	(*centerprintf) (edict_t *ent, char *fmt, ...);
		void	(*sound) (edict_t *ent, int channel, int soundindex, float volume, float attenuation, float timeofs);
		void	(*positioned_sound) (vec3_t origin, edict_t *ent, int channel, int soundinedex, float volume, float attenuation, float timeofs);

		// config strings hold all the index strings, the lightstyles,
		// and misc data like the sky definition and cdtrack.
		// All of the current configstrings are sent to clients when
		// they connect, and changes are sent to all connected clients.
		void	(*configstring) (int num, char *string);

		void	(*error) (char *fmt, ...);

		// the *index functions create configstrings and some internal server state
		int		(*modelindex) (char *name);
		int		(*soundindex) (char *name);
		int		(*imageindex) (char *name);

		void	(*setmodel) (edict_t *ent, char *name);

		// collision detection
		trace_t	(*trace) (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, edict_t *passent, int contentmask);
		int		(*pointcontents) (vec3_t point);
		qboolean	(*inPVS) (vec3_t p1, vec3_t p2);
		qboolean	(*inPHS) (vec3_t p1, vec3_t p2);
		void		(*SetAreaPortalState) (int portalnum, qboolean open);
		qboolean	(*AreasConnected) (int area1, int area2);

		// an entity will never be sent to a client or used for collision
		// if it is not passed to linkentity.  If the size, position, or
		// solidity changes, it must be relinked.
		void	(*linkentity) (edict_t *ent);
		void	(*unlinkentity) (edict_t *ent);		// call before removing an interactive edict
		int		(*BoxEdicts) (vec3_t mins, vec3_t maxs, edict_t **list,	int maxcount, int areatype);
		void	(*Pmove) (pmove_t *pmove);		// player movement code common with client prediction

		// network messaging
		void	(*multicast) (vec3_t origin, multicast_t to);
		void	(*unicast) (edict_t *ent, qboolean reliable);
		void	(*WriteChar) (int c);
		void	(*WriteByte) (int c);
		void	(*WriteShort) (int c);
		void	(*WriteLong) (int c);
		void	(*WriteFloat) (float f);
		void	(*WriteString) (char *s);
		void	(*WritePosition) (vec3_t pos);	// some fractional bits
		void	(*WriteDir) (vec3_t pos);		// single byte encoded, very coarse
		void	(*WriteAngle) (float f);

		// managed memory allocation
		void	*(*TagMalloc) (int size, int tag);
		void	(*TagFree) (void *block);
		void	(*FreeTags) (int tag);

		// console variable interaction
		"""
		self.cvar = None # cvar_t, *(*cvar) (char *var_name, char *value, int flags);
		"""
		cvar_t	*(*cvar_set) (char *var_name, char *value);
		cvar_t	*(*cvar_forceset) (char *var_name, char *value);

		// ClientCommand and ServerCommand parameter access
		int		(*argc) (void);
		char	*(*argv) (int n);
		char	*(*args) (void);	// concatenation of all argv >= 1

		// add commands to the server console as if they were typed in
		// for map changing, etc
		void	(*AddCommandString) (char *text);

		void	(*DebugGraph) (float value, int color);
		"""

#
# functions exported by the game subsystem
#
class game_export_t(object):

	def __init__(self):

		"""
		int			apiversion;

		// the init function will only be called when a game starts,
		// not each time a level is loaded.  Persistant data for clients
		// and the server can be allocated in init
		"""
		self.Init = None # void (*) (void)
		self.Shutdown = None # void (*) (void)
		self.helpchanged = 0 #int
		"""

		// each new level entered will cause a call to SpawnEntities
		void		(*SpawnEntities) (char *mapname, char *entstring, char *spawnpoint);

		// Read/Write Game is for storing persistant cross level information
		// about the world state and the clients.
		// WriteGame is called every time a level is exited.
		// ReadGame is called on a loadgame.
		void		(*WriteGame) (char *filename, qboolean autosave);
		void		(*ReadGame) (char *filename);

		// ReadLevel is called after the default map information has been
		// loaded with SpawnEntities
		void		(*WriteLevel) (char *filename);
		void		(*ReadLevel) (char *filename);

		qboolean	(*ClientConnect) (edict_t *ent, char *userinfo);
		void		(*ClientBegin) (edict_t *ent);
		void		(*ClientUserinfoChanged) (edict_t *ent, char *userinfo);
		void		(*ClientDisconnect) (edict_t *ent);
		void		(*ClientCommand) (edict_t *ent);
		void		(*ClientThink) (edict_t *ent, usercmd_t *cmd);

		void		(*RunFrame) (void);

		// ServerCommand will be called when an "sv <command>" command is issued on the
		// server console.
		// The game can issue gi.argc() / gi.argv() commands to get the rest
		// of the parameters
		void		(*ServerCommand) (void);

		//
		// global variables shared between game and server
		//

		// The edict array is allocated in the game dll so it
		// can vary in size from one game to another.
		// 
		// The size will be fixed when ge->Init() is called
		"""
		self.edicts = None
		self.edict_size = 0 #int
		self.num_edicts = 0 #int, current number, <= max_edicts
		self.max_edicts = 0 #int

#game_export_t *GetGameApi (game_import_t *import);
