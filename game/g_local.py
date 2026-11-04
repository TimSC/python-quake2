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
from enum import Enum
import math
import numpy as np
from game import q_shared, game

"""
// g_local.h -- local definitions for game module

#include "q_shared.h"

// define GAME_INCLUDE so that game.h does not define the
// short, server-visible gclient_t and edict_t structures,
// because we define the full size ones in this file
#define	GAME_INCLUDE
#include "game.h"

// the "gameversion" client command will print this plus compile date
#define	GAMEVERSION	"baseq2"

// protocol bytes that can be directly added to messages
#define	svc_muzzleflash		1
#define	svc_muzzleflash2	2
#define	svc_temp_entity		3
#define	svc_layout			4
#define	svc_inventory		5
#define	svc_stufftext		11

//==================================================================

// view pitching times
#define DAMAGE_TIME		0.5
#define	FALL_TIME		0.3


// edict->spawnflags
// these are set with checkboxes on each entity in the map editor
#define	SPAWNFLAG_NOT_EASY			0x00000100
#define	SPAWNFLAG_NOT_MEDIUM		0x00000200
#define	SPAWNFLAG_NOT_HARD			0x00000400
#define	SPAWNFLAG_NOT_DEATHMATCH	0x00000800
#define	SPAWNFLAG_NOT_COOP			0x00001000

// edict->flags
#define	FL_FLY					0x00000001
#define	FL_SWIM					0x00000002	// implied immunity to drowining
#define FL_IMMUNE_LASER			0x00000004
#define	FL_INWATER				0x00000008
#define	FL_GODMODE				0x00000010
#define	FL_NOTARGET				0x00000020
#define FL_IMMUNE_SLIME			0x00000040
#define FL_IMMUNE_LAVA			0x00000080
#define	FL_PARTIALGROUND		0x00000100	// not all corners are valid
#define	FL_WATERJUMP			0x00000200	// player jumping out of water
#define	FL_TEAMSLAVE			0x00000400	// not the first on the team
#define FL_NO_KNOCKBACK			0x00000800
#define FL_POWER_ARMOR			0x00001000	// power armor (if any) is active
#define FL_RESPAWN				0x80000000	// used for item respawning


#define	FRAMETIME		0.1

// memory tags to allow dynamic memory to be cleaned up
#define	TAG_GAME	765		// clear when unloading the dll
#define	TAG_LEVEL	766		// clear when loading a new level


#define MELEE_DISTANCE	80

#define BODY_QUEUE_SIZE		8

"""
GAMEVERSION = "baseq2"

# protocol bytes that can be directly added to messages
svc_muzzleflash   = 1
svc_muzzleflash2  = 2
svc_temp_entity   = 3
svc_layout        = 4
svc_inventory     = 5
svc_stufftext     = 11

# view pitching times
DAMAGE_TIME = 0.5
FALL_TIME   = 0.3

# edict->spawnflags
SPAWNFLAG_NOT_EASY       = 0x00000100
SPAWNFLAG_NOT_MEDIUM     = 0x00000200
SPAWNFLAG_NOT_HARD       = 0x00000400
SPAWNFLAG_NOT_DEATHMATCH = 0x00000800
SPAWNFLAG_NOT_COOP       = 0x00001000

# edict->flags
FL_FLY           = 0x00000001
FL_SWIM          = 0x00000002
FL_IMMUNE_LASER  = 0x00000004
FL_INWATER       = 0x00000008
FL_GODMODE       = 0x00000010
FL_NOTARGET      = 0x00000020
FL_IMMUNE_SLIME  = 0x00000040
FL_IMMUNE_LAVA   = 0x00000080
FL_PARTIALGROUND = 0x00000100
FL_WATERJUMP     = 0x00000200
FL_TEAMSLAVE     = 0x00000400
FL_NO_KNOCKBACK  = 0x00000800
FL_POWER_ARMOR   = 0x00001000
FL_RESPAWN       = 0x80000000

FRAMETIME = 0.1
DEFAULT_BULLET_HSPREAD = 300
DEFAULT_BULLET_VSPREAD = 500

# memory tags to allow dynamic memory to be cleaned up
TAG_GAME  = 765
TAG_LEVEL = 766

MELEE_DISTANCE  = 80
BODY_QUEUE_SIZE = 8


"""
typedef enum
{
	DAMAGE_NO,
	DAMAGE_YES,			// will take damage if hit
	DAMAGE_AIM			// auto targeting recognizes this
} damage_t;

typedef enum
{
	WEAPON_READY,
	WEAPON_ACTIVATING,
	WEAPON_DROPPING,
	WEAPON_FIRING
} weaponstate_t;

typedef enum
{
	AMMO_BULLETS,
	AMMO_SHELLS,
	AMMO_ROCKETS,
	AMMO_GRENADES,
	AMMO_CELLS,
	AMMO_SLUGS
} ammo_t;


//deadflag
#define DEAD_NO					0
#define DEAD_DYING				1
#define DEAD_DEAD				2
#define DEAD_RESPAWNABLE		3

//range
#define RANGE_MELEE				0
#define RANGE_NEAR				1
#define RANGE_MID				2
#define RANGE_FAR				3

//gib types
#define GIB_ORGANIC				0
#define GIB_METALLIC			1

//monster ai flags
#define AI_STAND_GROUND			0x00000001
#define AI_TEMP_STAND_GROUND	0x00000002
#define AI_SOUND_TARGET			0x00000004
#define AI_LOST_SIGHT			0x00000008
#define AI_PURSUIT_LAST_SEEN	0x00000010
#define AI_PURSUE_NEXT			0x00000020
#define AI_PURSUE_TEMP			0x00000040
#define AI_HOLD_FRAME			0x00000080
#define AI_GOOD_GUY				0x00000100
#define AI_BRUTAL				0x00000200
#define AI_NOSTEP				0x00000400
#define AI_DUCKED				0x00000800
#define AI_COMBAT_POINT			0x00001000
#define AI_MEDIC				0x00002000
#define AI_RESURRECTING			0x00004000

//monster attack state
#define AS_STRAIGHT				1
#define AS_SLIDING				2
#define	AS_MELEE				3
#define	AS_MISSILE				4

// armor types
#define ARMOR_NONE				0
#define ARMOR_JACKET			1
#define ARMOR_COMBAT			2
#define ARMOR_BODY				3
#define ARMOR_SHARD				4

// power armor types
#define POWER_ARMOR_NONE		0
#define POWER_ARMOR_SCREEN		1
#define POWER_ARMOR_SHIELD		2

// handedness values
#define RIGHT_HANDED			0
#define LEFT_HANDED				1
#define CENTER_HANDED			2


// game.serverflags values
#define SFL_CROSS_TRIGGER_1		0x00000001
#define SFL_CROSS_TRIGGER_2		0x00000002
#define SFL_CROSS_TRIGGER_3		0x00000004
#define SFL_CROSS_TRIGGER_4		0x00000008
#define SFL_CROSS_TRIGGER_5		0x00000010
#define SFL_CROSS_TRIGGER_6		0x00000020
#define SFL_CROSS_TRIGGER_7		0x00000040
#define SFL_CROSS_TRIGGER_8		0x00000080
#define SFL_CROSS_TRIGGER_MASK	0x000000ff


// noise types for PlayerNoise
#define PNOISE_SELF				0
#define PNOISE_WEAPON			1
#define PNOISE_IMPACT			2


// edict->movetype values
typedef enum
{
MOVETYPE_NONE,			// never moves
MOVETYPE_NOCLIP,		// origin and angles change with no interaction
MOVETYPE_PUSH,			// no clip to world, push on box contact
MOVETYPE_STOP,			// no clip to world, stops on box contact

MOVETYPE_WALK,			// gravity
MOVETYPE_STEP,			// gravity, special edge handling
MOVETYPE_FLY,
MOVETYPE_TOSS,			// gravity
MOVETYPE_FLYMISSILE,	// extra size to monsters
MOVETYPE_BOUNCE
} movetype_t;
"""
class damage_t(Enum):
	DAMAGE_NO  = 0
	DAMAGE_YES = 1
	DAMAGE_AIM = 2

# T_Damage dflags (from g_local.h)
DAMAGE_RADIUS = 1			# damage was indirect (from a nearby explosion)
DAMAGE_NO_ARMOR = 2			# armor does not protect from this damage
DAMAGE_ENERGY = 4			# damage is from an energy based weapon
DAMAGE_NO_KNOCKBACK = 8		# do not affect velocity, just view angles
DAMAGE_BULLET = 16			# damage is from a bullet (used for ricochets)
DAMAGE_NO_PROTECTION = 32	# kills godmode, armor, everything


class weaponstate_t(Enum):
	WEAPON_READY      = 0
	WEAPON_ACTIVATING = 1
	WEAPON_DROPPING   = 2
	WEAPON_FIRING     = 3


class ammo_t(Enum):
	AMMO_BULLETS  = 0
	AMMO_SHELLS   = 1
	AMMO_ROCKETS  = 2
	AMMO_GRENADES = 3
	AMMO_CELLS    = 4
	AMMO_SLUGS    = 5


# deadflag
DEAD_NO          = 0
DEAD_DYING       = 1
DEAD_DEAD        = 2
DEAD_RESPAWNABLE = 3

# range
RANGE_MELEE = 0
RANGE_NEAR  = 1
RANGE_MID   = 2
RANGE_FAR   = 3

# gib types
GIB_ORGANIC  = 0
GIB_METALLIC = 1

# monster ai flags
AI_STAND_GROUND      = 0x00000001
AI_TEMP_STAND_GROUND = 0x00000002
AI_SOUND_TARGET      = 0x00000004
AI_LOST_SIGHT        = 0x00000008
AI_PURSUIT_LAST_SEEN = 0x00000010
AI_PURSUE_NEXT       = 0x00000020
AI_PURSUE_TEMP       = 0x00000040
AI_HOLD_FRAME        = 0x00000080
AI_GOOD_GUY          = 0x00000100
AI_BRUTAL            = 0x00000200
AI_NOSTEP            = 0x00000400
AI_DUCKED            = 0x00000800
AI_COMBAT_POINT      = 0x00001000
AI_MEDIC             = 0x00002000
AI_RESURRECTING      = 0x00004000

# monster attack state
AS_STRAIGHT = 1
AS_SLIDING  = 2
AS_MELEE    = 3
AS_MISSILE  = 4

# armor types
ARMOR_NONE   = 0
ARMOR_JACKET = 1
ARMOR_COMBAT = 2
ARMOR_BODY   = 3
ARMOR_SHARD  = 4

# power armor types
POWER_ARMOR_NONE   = 0
POWER_ARMOR_SCREEN = 1
POWER_ARMOR_SHIELD = 2

# handedness values
RIGHT_HANDED  = 0
LEFT_HANDED   = 1
CENTER_HANDED = 2

# game.serverflags values
SFL_CROSS_TRIGGER_1  = 0x00000001
SFL_CROSS_TRIGGER_2  = 0x00000002
SFL_CROSS_TRIGGER_3  = 0x00000004
SFL_CROSS_TRIGGER_4  = 0x00000008
SFL_CROSS_TRIGGER_5  = 0x00000010
SFL_CROSS_TRIGGER_6  = 0x00000020
SFL_CROSS_TRIGGER_7  = 0x00000040
SFL_CROSS_TRIGGER_8  = 0x00000080
SFL_CROSS_TRIGGER_MASK = 0x000000ff

# noise types for PlayerNoise
PNOISE_SELF   = 0
PNOISE_WEAPON = 1
PNOISE_IMPACT = 2


# edict->movetype values
class movetype_t(Enum):
	MOVETYPE_NONE      = 0
	MOVETYPE_NOCLIP    = 1
	MOVETYPE_PUSH      = 2
	MOVETYPE_STOP      = 3
	MOVETYPE_WALK      = 4
	MOVETYPE_STEP      = 5
	MOVETYPE_FLY       = 6
	MOVETYPE_TOSS      = 7
	MOVETYPE_FLYMISSILE = 8
	MOVETYPE_BOUNCE    = 9

# module-level (matching C usage)
MOVETYPE_NONE = 0
MOVETYPE_NOCLIP = 1
MOVETYPE_PUSH = 2
MOVETYPE_STOP = 3
MOVETYPE_WALK = 4
MOVETYPE_STEP = 5
MOVETYPE_FLY = 6
MOVETYPE_TOSS = 7
MOVETYPE_FLYMISSILE = 8
MOVETYPE_BOUNCE = 9


"""
typedef struct
{
	int		base_count;
	int		max_count;
	float	normal_protection;
	float	energy_protection;
	int		armor;
} gitem_armor_t;
"""
class gitem_armor_t(object):

	def __init__(self):
		self.base_count = 0
		self.max_count = 0
		self.normal_protection = 0.0
		self.energy_protection = 0.0
		self.armor = 0


"""
// gitem_t->flags
#define	IT_WEAPON		1		// use makes active weapon
#define	IT_AMMO			2
#define IT_ARMOR		4
#define IT_STAY_COOP	8
#define IT_KEY			16
#define IT_POWERUP		32

// gitem_t->weapmodel for weapons indicates model index
#define WEAP_BLASTER			1
#define WEAP_SHOTGUN			2
#define WEAP_SUPERSHOTGUN		3
#define WEAP_MACHINEGUN			4
#define WEAP_CHAINGUN			5
#define WEAP_GRENADES			6
#define WEAP_GRENADELAUNCHER	7
#define WEAP_ROCKETLAUNCHER		8
#define WEAP_HYPERBLASTER		9
#define WEAP_RAILGUN			10
#define WEAP_BFG				11
"""
IT_WEAPON    = 1
IT_AMMO      = 2
IT_ARMOR     = 4
IT_STAY_COOP = 8
IT_KEY       = 16
IT_POWERUP   = 32

# item spawnflags
ITEM_TRIGGER_SPAWN = 0x00000001
ITEM_NO_TOUCH      = 0x00000002
DROPPED_ITEM       = 0x00010000
DROPPED_PLAYER_ITEM= 0x00020000
ITEM_TARGETS_USED  = 0x00040000

WEAP_BLASTER        = 1
WEAP_SHOTGUN        = 2
WEAP_SUPERSHOTGUN   = 3
WEAP_MACHINEGUN     = 4
WEAP_CHAINGUN       = 5
WEAP_GRENADES       = 6
WEAP_GRENADELAUNCHER = 7
WEAP_ROCKETLAUNCHER = 8
WEAP_HYPERBLASTER   = 9
WEAP_RAILGUN        = 10
WEAP_BFG            = 11


"""
typedef struct gitem_s
{
	char		*classname;	// spawning name
	qboolean	(*pickup)(struct edict_s *ent, struct edict_s *other);
	void		(*use)(struct edict_s *ent, struct gitem_s *item);
	void		(*drop)(struct edict_s *ent, struct gitem_s *item);
	void		(*weaponthink)(struct edict_s *ent);
	char		*pickup_sound;
	char		*world_model;
	int			world_model_flags;
	char		*view_model;

	// client side info
	char		*icon;
	char		*pickup_name;	// for printing on pickup
	int			count_width;		// number of digits to display by icon

	int			quantity;		// for ammo how much, for weapons how much is used per shot
	char		*ammo;			// for weapons
	int			flags;			// IT_* flags

	int			weapmodel;		// weapon model index (for weapons)

	void		*info;
	int			tag;

	char		*precaches;		// string of all models, sounds, and images this item will use
} gitem_t;
"""
class gitem_t(object):

	def __init__(self):
		self.classname = None
		self.pickup = None
		self.use = None
		self.drop = None
		self.weaponthink = None
		self.pickup_sound = None
		self.world_model = None
		self.world_model_flags = 0
		self.view_model = None
		self.icon = None
		self.pickup_name = None
		self.count_width = 0
		self.quantity = 0
		self.ammo = None
		self.flags = 0
		self.weapmodel = 0
		self.info = None
		self.tag = 0
		self.precaches = None


"""
// means of death
#define MOD_UNKNOWN			0
...
#define MOD_FRIENDLY_FIRE	0x8000000
"""
MOD_UNKNOWN        = 0
MOD_BLASTER        = 1
MOD_SHOTGUN        = 2
MOD_SSHOTGUN       = 3
MOD_MACHINEGUN     = 4
MOD_CHAINGUN       = 5
MOD_GRENADE        = 6
MOD_G_SPLASH       = 7
MOD_ROCKET         = 8
MOD_R_SPLASH       = 9
MOD_HYPERBLASTER   = 10
MOD_RAILGUN        = 11
MOD_BFG_LASER      = 12
MOD_BFG_BLAST      = 13
MOD_BFG_EFFECT     = 14
MOD_HANDGRENADE    = 15
MOD_HG_SPLASH      = 16
MOD_WATER          = 17
MOD_SLIME          = 18
MOD_LAVA           = 19
MOD_CRUSH          = 20
MOD_TELEFRAG       = 21
MOD_FALLING        = 22
MOD_SUICIDE        = 23
MOD_HELD_GRENADE   = 24
MOD_EXPLOSIVE      = 25
MOD_BARREL         = 26
MOD_BOMB           = 27
MOD_EXIT           = 28
MOD_SPLASH         = 29
MOD_TARGET_LASER   = 30
MOD_TRIGGER_HURT   = 31
MOD_HIT            = 32
MOD_TARGET_BLASTER = 33
MOD_FRIENDLY_FIRE  = 0x8000000


"""
//
// fields are needed for spawning from the entity string
// and saving / loading games
//
#define FFL_SPAWNTEMP		1
#define FFL_NOSPAWN			2

typedef enum {
	F_INT,
	F_FLOAT,
	F_LSTRING,			// string on disk, pointer in memory, TAG_LEVEL
	F_GSTRING,			// string on disk, pointer in memory, TAG_GAME
	F_VECTOR,
	F_ANGLEHACK,
	F_EDICT,			// index on disk, pointer in memory
	F_ITEM,				// index on disk, pointer in memory
	F_CLIENT,			// index on disk, pointer in memory
	F_FUNCTION,
	F_MMOVE,
	F_IGNORE
} fieldtype_t;

typedef struct
{
	char	*name;
	int		ofs;
	fieldtype_t	type;
	int		flags;
} field_t;
"""
FFL_SPAWNTEMP = 1
FFL_NOSPAWN   = 2


class fieldtype_t(Enum):
	F_INT       = 0
	F_FLOAT     = 1
	F_LSTRING   = 2
	F_GSTRING   = 3
	F_VECTOR    = 4
	F_ANGLEHACK = 5
	F_EDICT     = 6
	F_ITEM      = 7
	F_CLIENT    = 8
	F_FUNCTION  = 9
	F_MMOVE     = 10
	F_IGNORE    = 11


class field_t(object):

	def __init__(self):
		self.name = None
		self.ofs = 0
		self.type = None
		self.flags = 0


"""
typedef struct
{
	// fixed data
	vec3_t		start_origin;
	vec3_t		start_angles;
	vec3_t		end_origin;
	vec3_t		end_angles;

	int			sound_start;
	int			sound_middle;
	int			sound_end;

	float		accel;
	float		speed;
	float		decel;
	float		distance;

	float		wait;

	// state data
	int			state;
	vec3_t		dir;
	float		current_speed;
	float		move_speed;
	float		next_speed;
	float		remaining_distance;
	float		decel_distance;
	void		(*endfunc)(edict_t *);
} moveinfo_t;
"""
class moveinfo_t(object):

	def __init__(self):
		self.start_origin = np.zeros((3,), dtype=np.float32)
		self.start_angles = np.zeros((3,), dtype=np.float32)
		self.end_origin = np.zeros((3,), dtype=np.float32)
		self.end_angles = np.zeros((3,), dtype=np.float32)
		self.sound_start = 0
		self.sound_middle = 0
		self.sound_end = 0
		self.accel = 0.0
		self.speed = 0.0
		self.decel = 0.0
		self.distance = 0.0
		self.wait = 0.0
		self.state = 0
		self.dir = np.zeros((3,), dtype=np.float32)
		self.current_speed = 0.0
		self.move_speed = 0.0
		self.next_speed = 0.0
		self.remaining_distance = 0.0
		self.decel_distance = 0.0
		self.endfunc = None


"""
typedef struct
{
	void	(*aifunc)(edict_t *self, float dist);
	float	dist;
	void	(*thinkfunc)(edict_t *self);
} mframe_t;

typedef struct
{
	int			firstframe;
	int			lastframe;
	mframe_t	*frame;
	void		(*endfunc)(edict_t *self);
} mmove_t;
"""
class mframe_t(object):

	def __init__(self):
		self.aifunc = None
		self.dist = 0.0
		self.thinkfunc = None


class mmove_t(object):

	def __init__(self):
		self.firstframe = 0
		self.lastframe = 0
		self.frame = None
		self.endfunc = None


"""
typedef struct
{
	mmove_t		*currentmove;
	int			aiflags;
	int			nextframe;
	float		scale;

	void		(*stand)(edict_t *self);
	void		(*idle)(edict_t *self);
	void		(*search)(edict_t *self);
	void		(*walk)(edict_t *self);
	void		(*run)(edict_t *self);
	void		(*dodge)(edict_t *self, edict_t *other, float eta);
	void		(*attack)(edict_t *self);
	void		(*melee)(edict_t *self);
	void		(*sight)(edict_t *self, edict_t *other);
	qboolean	(*checkattack)(edict_t *self);

	float		pausetime;
	float		attack_finished;

	vec3_t		saved_goal;
	float		search_time;
	float		trail_time;
	vec3_t		last_sighting;
	int			attack_state;
	int			lefty;
	float		idle_time;
	int			linkcount;

	int			power_armor_type;
	int			power_armor_power;
} monsterinfo_t;
"""
class monsterinfo_t(object):

	def __init__(self):
		self.currentmove = None
		self.aiflags = 0
		self.nextframe = 0
		self.scale = 0.0
		self.stand = None
		self.idle = None
		self.search = None
		self.walk = None
		self.run = None
		self.dodge = None
		self.attack = None
		self.melee = None
		self.sight = None
		self.checkattack = None
		self.pausetime = 0.0
		self.attack_finished = 0.0
		self.saved_goal = np.zeros((3,), dtype=np.float32)
		self.search_time = 0.0
		self.trail_time = 0.0
		self.last_sighting = np.zeros((3,), dtype=np.float32)
		self.attack_state = 0
		self.lefty = 0
		self.idle_time = 0.0
		self.linkcount = 0
		self.power_armor_type = 0
		self.power_armor_power = 0


"""
#define random()	((rand () & 0x7fff) / ((float)0x7fff))
#define crandom()	(2.0 * (random() - 0.5))
"""
import random as _pyrandom


def random():
	# (rand() & 0x7fff) / 0x7fff
	return (_pyrandom.randint(0, 0x7fff)) / 0x7fff


def crandom():
	return 2.0 * (random() - 0.5)


"""
// client_t->anim_priority
#define	ANIM_BASIC		0		// stand / run
#define	ANIM_WAVE		1
#define	ANIM_JUMP		2
#define	ANIM_PAIN		3
#define	ANIM_ATTACK		4
#define	ANIM_DEATH		5
#define	ANIM_REVERSE	6
"""
ANIM_BASIC   = 0
ANIM_WAVE    = 1
ANIM_JUMP    = 2
ANIM_PAIN    = 3
ANIM_ATTACK  = 4

# player anim frames (from m_player.h) used by Cmd_Wave_f
FRAME_flip01     = 72
FRAME_flip12     = 83
FRAME_salute01   = 84
FRAME_salute11   = 94
FRAME_taunt01    = 95
FRAME_taunt17    = 111
FRAME_wave01     = 112
FRAME_wave11     = 122
FRAME_point01    = 123
FRAME_point12    = 134

# player death anim frames (from m_player.h) used by player_die
FRAME_crdeath1   = 173
FRAME_crdeath5   = 177
FRAME_death101   = 178
FRAME_death106   = 183
FRAME_death201   = 184
FRAME_death206   = 189
FRAME_death301   = 190
FRAME_death308   = 197

# player walk/jump/pain anim frames (from m_player.h) used by p_view
FRAME_stand01    = 0
FRAME_stand40    = 39
FRAME_run1       = 40
FRAME_run6       = 45
FRAME_pain101    = 54
FRAME_pain104    = 57
FRAME_pain201    = 58
FRAME_pain204    = 61
FRAME_pain301    = 62
FRAME_pain304    = 65
FRAME_jump1      = 66
FRAME_jump2      = 67
FRAME_jump3      = 68
FRAME_jump6      = 71
FRAME_crstnd01   = 135
FRAME_crstnd19   = 153
FRAME_crwalk1    = 154
FRAME_crwalk6    = 159
FRAME_crpain1    = 169
FRAME_crpain4    = 172
ANIM_DEATH   = 5
ANIM_REVERSE = 6


"""
// client data that stays across multiple level loads
typedef struct
{
	char		userinfo[MAX_INFO_STRING];
	char		netname[16];
	int			hand;

	qboolean	connected;

	// values saved and restored from edicts when changing levels
	int			health;
	int			max_health;
	int			savedFlags;

	int			selected_item;
	int			inventory[MAX_ITEMS];

	// ammo capacities
	int			max_bullets;
	int			max_shells;
	int			max_rockets;
	int			max_grenades;
	int			max_cells;
	int			max_slugs;

	gitem_t		*weapon;
	gitem_t		*lastweapon;

	int			power_cubes;	// used for tracking the cubes in coop games
	int			score;			// for calculating total unit score in coop games

	int			game_helpchanged;
	int			helpchanged;

	qboolean	spectator;			// client is a spectator
} client_persistant_t;
"""
class client_persistant_t(object):

	def __init__(self):
		self.userinfo = ""
		self.netname = ""
		self.hand = 0
		self.connected = False
		self.health = 0
		self.max_health = 0
		self.savedFlags = 0
		self.selected_item = 0
		self.inventory = [0 for _ in range(q_shared.MAX_ITEMS)]
		self.max_bullets = 0
		self.max_shells = 0
		self.max_rockets = 0
		self.max_grenades = 0
		self.max_cells = 0
		self.max_slugs = 0
		self.weapon = None
		self.lastweapon = None
		self.power_cubes = 0
		self.score = 0
		self.game_helpchanged = 0
		self.helpchanged = 0
		self.spectator = False


"""
// client data that stays across deathmatch respawns
typedef struct
{
	client_persistant_t	coop_respawn;	// what to set client->pers to on a respawn
	int			enterframe;			// level.framenum the client entered the game
	int			score;				// frags, etc
	vec3_t		cmd_angles;			// angles sent over in the last command

	qboolean	spectator;			// client is a spectator
} client_respawn_t;
"""
class client_respawn_t(object):

	def __init__(self):
		self.coop_respawn = client_persistant_t()
		self.enterframe = 0
		self.score = 0
		self.cmd_angles = np.zeros((3,), dtype=np.float32)
		self.spectator = False


"""
//
// this structure is left intact through an entire game
// it should be initialized at dll load time, and read/written to
// the server.ssv file for savegames
//
typedef struct
{
	char		helpmessage1[512];
	char		helpmessage2[512];
	int			helpchanged;	// flash F1 icon if non 0, play sound
								// and increment only if 1, 2, or 3

	gclient_t	*clients;		// [maxclients]

	// can't store spawnpoint in level, because
	// it would get overwritten by the savegame restore
	char		spawnpoint[512];	// needed for coop respawns

	// store latched cvars here that we want to get at often
	int			maxclients;
	int			maxentities;

	// cross level triggers
	int			serverflags;

	// items
	int			num_items;

	qboolean	autosaved;
} game_locals_t;
"""
class game_locals_t(object):

	def __init__(self):
		self.helpmessage1 = ""
		self.helpmessage2 = ""
		self.helpchanged = 0
		self.clients = None			# [maxclients]
		self.spawnpoint = ""
		self.maxclients = 0
		self.maxentities = 0
		self.serverflags = 0
		self.num_items = 0
		self.autosaved = False


"""
//
// this structure is cleared as each map is entered
// it is read/written to the level.sav file for savegames
//
typedef struct
{
	int			framenum;
	float		time;

	char		level_name[MAX_QPATH];	// the descriptive name (Outer Base, etc)
	char		mapname[MAX_QPATH];		// the server name (base1, etc)
	char		nextmap[MAX_QPATH];		// go here when fraglimit is hit

	// intermission state
	float		intermissiontime;		// time the intermission was started
	char		*changemap;
	int			exitintermission;
	vec3_t		intermission_origin;
	vec3_t		intermission_angle;

	edict_t		*sight_client;	// changed once each frame for coop games

	edict_t		*sight_entity;
	int			sight_entity_framenum;
	edict_t		*sound_entity;
	int			sound_entity_framenum;
	edict_t		*sound2_entity;
	int			sound2_entity_framenum;

	int			pic_health;

	int			total_secrets;
	int			found_secrets;

	int			total_goals;
	int			found_goals;

	int			total_monsters;
	int			killed_monsters;

	edict_t		*current_entity;	// entity running from G_RunFrame
	int			body_que;			// dead bodies

	int			power_cubes;		// ugly necessity for coop
} level_locals_t;
"""
class level_locals_t(object):

	def __init__(self):
		self.framenum = 0
		self.time = 0.0
		self.level_name = ""
		self.mapname = ""
		self.nextmap = ""
		self.intermissiontime = 0.0
		self.changemap = None
		self.exitintermission = 0
		self.intermission_origin = np.zeros((3,), dtype=np.float32)
		self.intermission_angle = np.zeros((3,), dtype=np.float32)
		self.sight_client = None
		self.sight_entity = None
		self.sight_entity_framenum = 0
		self.sound_entity = None
		self.sound_entity_framenum = 0
		self.sound2_entity = None
		self.sound2_entity_framenum = 0
		self.pic_health = 0
		self.total_secrets = 0
		self.found_secrets = 0
		self.total_goals = 0
		self.found_goals = 0
		self.total_monsters = 0
		self.killed_monsters = 0
		self.current_entity = None
		self.body_que = 0
		self.power_cubes = 0


"""
// spawn_temp_t is only used to hold entity field values that
// can be set from the editor, but aren't actualy present
// in edict_t during gameplay
typedef struct
{
	// world vars
	char		*sky;
	float		skyrotate;
	vec3_t		skyaxis;
	char		*nextmap;

	int			lip;
	int			distance;
	int			height;
	char		*noise;
	float		pausetime;
	char		*item;
	char		*gravity;

	float		minyaw;
	float		maxyaw;
	float		minpitch;
	float		maxpitch;
} spawn_temp_t;
"""
class spawn_temp_t(object):

	def __init__(self):
		self.sky = None
		self.skyrotate = 0.0
		self.skyaxis = np.zeros((3,), dtype=np.float32)
		self.nextmap = None
		self.lip = 0
		self.distance = 0
		self.height = 0
		self.noise = None
		self.pausetime = 0.0
		self.item = None
		self.gravity = None
		self.minyaw = 0.0
		self.maxyaw = 0.0
		self.minpitch = 0.0
		self.maxpitch = 0.0
