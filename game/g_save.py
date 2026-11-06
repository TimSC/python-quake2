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

import struct
import time
import numpy as np

from game import g_main, g_items
from common.header import shared
from common.header import common as common_h
from game.header import game as game_h
from game.header import local
"""
#include "g_local.h"

#define Function(f) {#f, f}

mmove_t mmove_reloc;

field_t fields[] = {
	{"classname", FOFS(classname), F_LSTRING},
	{"model", FOFS(model), F_LSTRING},
	{"spawnflags", FOFS(spawnflags), F_INT},
	{"speed", FOFS(speed), F_FLOAT},
	{"accel", FOFS(accel), F_FLOAT},
	{"decel", FOFS(decel), F_FLOAT},
	{"target", FOFS(target), F_LSTRING},
	{"targetname", FOFS(targetname), F_LSTRING},
	{"pathtarget", FOFS(pathtarget), F_LSTRING},
	{"deathtarget", FOFS(deathtarget), F_LSTRING},
	{"killtarget", FOFS(killtarget), F_LSTRING},
	{"combattarget", FOFS(combattarget), F_LSTRING},
	{"message", FOFS(message), F_LSTRING},
	{"team", FOFS(team), F_LSTRING},
	{"wait", FOFS(wait), F_FLOAT},
	{"delay", FOFS(delay), F_FLOAT},
	{"random", FOFS(random), F_FLOAT},
	{"move_origin", FOFS(move_origin), F_VECTOR},
	{"move_angles", FOFS(move_angles), F_VECTOR},
	{"style", FOFS(style), F_INT},
	{"count", FOFS(count), F_INT},
	{"health", FOFS(health), F_INT},
	{"sounds", FOFS(sounds), F_INT},
	{"light", 0, F_IGNORE},
	{"dmg", FOFS(dmg), F_INT},
	{"mass", FOFS(mass), F_INT},
	{"volume", FOFS(volume), F_FLOAT},
	{"attenuation", FOFS(attenuation), F_FLOAT},
	{"map", FOFS(map), F_LSTRING},
	{"origin", FOFS(s.origin), F_VECTOR},
	{"angles", FOFS(s.angles), F_VECTOR},
	{"angle", FOFS(s.angles), F_ANGLEHACK},

	{"goalentity", FOFS(goalentity), F_EDICT, FFL_NOSPAWN},
	{"movetarget", FOFS(movetarget), F_EDICT, FFL_NOSPAWN},
	{"enemy", FOFS(enemy), F_EDICT, FFL_NOSPAWN},
	{"oldenemy", FOFS(oldenemy), F_EDICT, FFL_NOSPAWN},
	{"activator", FOFS(activator), F_EDICT, FFL_NOSPAWN},
	{"groundentity", FOFS(groundentity), F_EDICT, FFL_NOSPAWN},
	{"teamchain", FOFS(teamchain), F_EDICT, FFL_NOSPAWN},
	{"teammaster", FOFS(teammaster), F_EDICT, FFL_NOSPAWN},
	{"owner", FOFS(owner), F_EDICT, FFL_NOSPAWN},
	{"mynoise", FOFS(mynoise), F_EDICT, FFL_NOSPAWN},
	{"mynoise2", FOFS(mynoise2), F_EDICT, FFL_NOSPAWN},
	{"target_ent", FOFS(target_ent), F_EDICT, FFL_NOSPAWN},
	{"chain", FOFS(chain), F_EDICT, FFL_NOSPAWN},

	{"prethink", FOFS(prethink), F_FUNCTION, FFL_NOSPAWN},
	{"think", FOFS(think), F_FUNCTION, FFL_NOSPAWN},
	{"blocked", FOFS(blocked), F_FUNCTION, FFL_NOSPAWN},
	{"touch", FOFS(touch), F_FUNCTION, FFL_NOSPAWN},
	{"use", FOFS(use), F_FUNCTION, FFL_NOSPAWN},
	{"pain", FOFS(pain), F_FUNCTION, FFL_NOSPAWN},
	{"die", FOFS(die), F_FUNCTION, FFL_NOSPAWN},

	{"stand", FOFS(monsterinfo.stand), F_FUNCTION, FFL_NOSPAWN},
	{"idle", FOFS(monsterinfo.idle), F_FUNCTION, FFL_NOSPAWN},
	{"search", FOFS(monsterinfo.search), F_FUNCTION, FFL_NOSPAWN},
	{"walk", FOFS(monsterinfo.walk), F_FUNCTION, FFL_NOSPAWN},
	{"run", FOFS(monsterinfo.run), F_FUNCTION, FFL_NOSPAWN},
	{"dodge", FOFS(monsterinfo.dodge), F_FUNCTION, FFL_NOSPAWN},
	{"attack", FOFS(monsterinfo.attack), F_FUNCTION, FFL_NOSPAWN},
	{"melee", FOFS(monsterinfo.melee), F_FUNCTION, FFL_NOSPAWN},
	{"sight", FOFS(monsterinfo.sight), F_FUNCTION, FFL_NOSPAWN},
	{"checkattack", FOFS(monsterinfo.checkattack), F_FUNCTION, FFL_NOSPAWN},
	{"currentmove", FOFS(monsterinfo.currentmove), F_MMOVE, FFL_NOSPAWN},

	{"endfunc", FOFS(moveinfo.endfunc), F_FUNCTION, FFL_NOSPAWN},

	// temp spawn vars -- only valid when the spawn function is called
	{"lip", STOFS(lip), F_INT, FFL_SPAWNTEMP},
	{"distance", STOFS(distance), F_INT, FFL_SPAWNTEMP},
	{"height", STOFS(height), F_INT, FFL_SPAWNTEMP},
	{"noise", STOFS(noise), F_LSTRING, FFL_SPAWNTEMP},
	{"pausetime", STOFS(pausetime), F_FLOAT, FFL_SPAWNTEMP},
	{"item", STOFS(item), F_LSTRING, FFL_SPAWNTEMP},

//need for item field in edict struct, FFL_SPAWNTEMP item will be skipped on saves
	{"item", FOFS(item), F_ITEM},

	{"gravity", STOFS(gravity), F_LSTRING, FFL_SPAWNTEMP},
	{"sky", STOFS(sky), F_LSTRING, FFL_SPAWNTEMP},
	{"skyrotate", STOFS(skyrotate), F_FLOAT, FFL_SPAWNTEMP},
	{"skyaxis", STOFS(skyaxis), F_VECTOR, FFL_SPAWNTEMP},
	{"minyaw", STOFS(minyaw), F_FLOAT, FFL_SPAWNTEMP},
	{"maxyaw", STOFS(maxyaw), F_FLOAT, FFL_SPAWNTEMP},
	{"minpitch", STOFS(minpitch), F_FLOAT, FFL_SPAWNTEMP},
	{"maxpitch", STOFS(maxpitch), F_FLOAT, FFL_SPAWNTEMP},
	{"nextmap", STOFS(nextmap), F_LSTRING, FFL_SPAWNTEMP},

	{0, 0, 0, 0}

};

field_t		levelfields[] =
{
	{"changemap", LLOFS(changemap), F_LSTRING},
                   
	{"sight_client", LLOFS(sight_client), F_EDICT},
	{"sight_entity", LLOFS(sight_entity), F_EDICT},
	{"sound_entity", LLOFS(sound_entity), F_EDICT},
	{"sound2_entity", LLOFS(sound2_entity), F_EDICT},

	{NULL, 0, F_INT}
};

field_t		clientfields[] =
{
	{"pers.weapon", CLOFS(pers.weapon), F_ITEM},
	{"pers.lastweapon", CLOFS(pers.lastweapon), F_ITEM},
	{"newweapon", CLOFS(newweapon), F_ITEM},

	{NULL, 0, F_INT}
};

"""

"""
 * Allocate the edicts and clients arrays.
"""
def InitAllocations(): #void (static)

	#int num_c = maxclients->value;
	#int num_e = maxentities->value;
	num_c = int(g_main.maxclients.value)
	num_e = int(g_main.maxentities.value)

	if num_c < 1:

		num_c = 1
		g_main.gi.cvar_forceset("maxclients", "1")


	if num_e < (num_c + 1):

		num_e = num_c + 1
		g_main.gi.cvar_forceset("maxentities", "%d" % (num_c + 1))


	g_main.g_edicts = [game_h.edict_t() for _ in range(num_e)] # gi.TagMalloc (num_e * sizeof(g_edicts[0]), TAG_GAME)
	g_main.game.maxentities = num_e

	g_main.glob.edicts = g_main.g_edicts
	g_main.glob.num_edicts = num_c + 1
	g_main.glob.max_edicts = num_e

	g_main.game.clients = [game_h.gclient_s() for _ in range(num_c)] # gi.TagMalloc (num_c * sizeof(game.clients[0]), TAG_GAME)
	g_main.game.maxclients = num_c

"""
 * This will be called when the dll is first loaded,
 * which only happens when a new game is started or
 * a save game is loaded.
"""
def InitGame(): #void

	g_main.gi.dprintf("Game is starting up.\n")
	g_main.gi.dprintf("Game is %s built on %s.\n", local.GAMEVERSION, common_h.BUILD_DATE)

	g_main.gun_x = g_main.gi.cvar("gun_x", "0", 0)
	g_main.gun_y = g_main.gi.cvar("gun_y", "0", 0)
	g_main.gun_z = g_main.gi.cvar("gun_z", "0", 0)
	g_main.sv_rollspeed = g_main.gi.cvar("sv_rollspeed", "200", 0)
	g_main.sv_rollangle = g_main.gi.cvar("sv_rollangle", "2", 0)
	g_main.sv_maxvelocity = g_main.gi.cvar("sv_maxvelocity", "2000", 0)
	g_main.sv_gravity = g_main.gi.cvar("sv_gravity", "800", 0)

	# noset vars
	g_main.dedicated = g_main.gi.cvar("dedicated", "0", shared.CVAR_NOSET)

	# latched vars
	g_main.sv_cheats = g_main.gi.cvar("cheats", "0", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.gi.cvar("gamename", local.GAMEVERSION, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.gi.cvar("gamedate", common_h.BUILD_DATE, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.maxclients = g_main.gi.cvar("maxclients", "4", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.maxspectators = g_main.gi.cvar("maxspectators", "4", shared.CVAR_SERVERINFO)
	g_main.deathmatch = g_main.gi.cvar("deathmatch", "0", shared.CVAR_LATCH)
	g_main.coop = g_main.gi.cvar("coop", "0", shared.CVAR_LATCH)
	g_main.coop_pickup_weapons = g_main.gi.cvar("coop_pickup_weapons", "1", shared.CVAR_ARCHIVE)
	g_main.coop_elevator_delay = g_main.gi.cvar("coop_elevator_delay", "1.0", shared.CVAR_ARCHIVE)
	g_main.skill = g_main.gi.cvar("skill", "1", shared.CVAR_LATCH)
	g_main.maxentities = g_main.gi.cvar("maxentities", "1024", shared.CVAR_LATCH)
	g_main.g_footsteps = g_main.gi.cvar("g_footsteps", "1", shared.CVAR_ARCHIVE)
	g_main.g_monsterfootsteps = g_main.gi.cvar("g_monsterfootsteps", "0", shared.CVAR_ARCHIVE)
	g_main.g_fix_triggered = g_main.gi.cvar ("g_fix_triggered", "0", 0)
	g_main.g_commanderbody_nogod = g_main.gi.cvar("g_commanderbody_nogod", "0", shared.CVAR_ARCHIVE)

	# change anytime vars
	g_main.dmflags = g_main.gi.cvar("dmflags", "0", shared.CVAR_SERVERINFO)
	g_main.fraglimit = g_main.gi.cvar("fraglimit", "0", shared.CVAR_SERVERINFO)
	g_main.timelimit = g_main.gi.cvar("timelimit", "0", shared.CVAR_SERVERINFO)
	g_main.password = g_main.gi.cvar("password", "", shared.CVAR_USERINFO)
	g_main.spectator_password = g_main.gi.cvar("spectator_password", "", shared.CVAR_USERINFO)
	g_main.needpass = g_main.gi.cvar("needpass", "0", shared.CVAR_SERVERINFO)
	g_main.filterban = g_main.gi.cvar("filterban", "1", 0)
	g_main.g_select_empty = g_main.gi.cvar("g_select_empty", "0", shared.CVAR_ARCHIVE)
	g_main.run_pitch = g_main.gi.cvar("run_pitch", "0.002", 0)
	g_main.run_roll = g_main.gi.cvar("run_roll", "0.005", 0)
	g_main.bob_up = g_main.gi.cvar("bob_up", "0.005", 0)
	g_main.bob_pitch = g_main.gi.cvar("bob_pitch", "0.002", 0)
	g_main.bob_roll = g_main.gi.cvar("bob_roll", "0.002", 0)

	# flood control
	g_main.flood_msgs = g_main.gi.cvar("flood_msgs", "4", 0)
	g_main.flood_persecond = g_main.gi.cvar("flood_persecond", "4", 0)
	g_main.flood_waitdelay = g_main.gi.cvar("flood_waitdelay", "10", 0)

	# dm map list
	g_main.sv_maplist = g_main.gi.cvar("sv_maplist", "", 0)

	# others
	g_main.aimfix = g_main.gi.cvar("aimfix", "0", shared.CVAR_ARCHIVE)
	g_main.g_machinegun_norecoil = g_main.gi.cvar("g_machinegun_norecoil", "0", shared.CVAR_ARCHIVE)
	g_main.g_quick_weap = g_main.gi.cvar("g_quick_weap", "1", shared.CVAR_ARCHIVE)
	g_main.g_swap_speed = g_main.gi.cvar("g_swap_speed", "1", shared.CVAR_ARCHIVE)

	g_main.game.__init__() #memset(&game, 0, sizeof(game));

	g_items.InitItems()

	# initialize entities and clients arrays
	InitAllocations()

#
# C-compatible savegame binary layout (32-bit Quake2).
# The format strings reproduce the exact struct layouts from
# q_shared.h and g_local.h so .ssv/.sav files match the original.
#
_FMT_PMOVE  = "<i3hbbh3h"                    # pmove_state_t        = 20
_FMT_PLAYER = "<i3hbbh3h" + "3f3f3f3f3f" + "ii" + "4f" + "f" + "i" + "32h"  # player_state_t = 176
_FMT_CLIENT = _FMT_PLAYER + "i"              # gclient_s            = 180
_FMT_GAME   = "<512s512sii512s5i"            # game_locals_t        = 1556

def _pack_pmove(pm):
	# origin/velocity/delta_angles may be float32 arrays at runtime, so cast
	# each field to int explicitly (struct shorts/bytes require integers).
	return struct.pack(_FMT_PMOVE,
		int(pm.pm_type),
		int(pm.origin[0]), int(pm.origin[1]), int(pm.origin[2]),
		int(pm.pm_flags), int(pm.pm_time), int(pm.gravity),
		int(pm.delta_angles[0]), int(pm.delta_angles[1]), int(pm.delta_angles[2]))

def _pack_player(ps):
	data = _pack_pmove(ps.pmove)
	data += struct.pack("15f",
		*ps.viewangles.tolist(), *ps.viewoffset.tolist(),
		*ps.kick_angles.tolist(), *ps.gunangles.tolist(),
		*ps.gunoffset.tolist())
	data += struct.pack("ii", int(ps.gunindex or 0), int(ps.gunframe or 0))
	data += struct.pack("4f", *ps.blend.tolist())
	data += struct.pack("f", float(ps.fov))
	data += struct.pack("i", int(ps.rdflags))
	data += struct.pack("32h", *ps.stats)
	return data

def _pack_client(cl):
	return _pack_player(cl.ps) + struct.pack("i", int(cl.ping))

def _pack_game(gm):
	def s512(x):
		b = (x or "").encode("latin-1")[:512]
		return b.ljust(512, b"\0")
	return struct.pack(_FMT_GAME,
		s512(gm.helpmessage1), s512(gm.helpmessage2),
		int(gm.helpchanged),
		0,  # clients pointer (overwritten on read)
		s512(gm.spawnpoint),
		int(gm.maxclients), int(gm.maxentities),
		int(gm.serverflags), int(gm.num_items),
		1 if gm.autosaved else 0)

#=========================================================
# Field tables (port of fields[]/levelfields[]/clientfields[]).
# In the C, field->ofs is a byte offset; here it is the Python
# attribute path (e.g. "s.origin", "monsterinfo.stand") resolved
# via getattr/setattr.
#
_ft = local.fieldtype_t


def _fk (name, ofs, type, flags=0):
	f = local.field_t()
	f.name = name
	f.ofs = ofs
	f.type = type
	f.flags = flags
	return f


_fields_nospawn = local.FFL_NOSPAWN

fields = [
	_fk("classname", "classname", _ft.F_LSTRING),
	_fk("model", "model", _ft.F_LSTRING),
	_fk("spawnflags", "spawnflags", _ft.F_INT),
	_fk("speed", "speed", _ft.F_FLOAT),
	_fk("accel", "accel", _ft.F_FLOAT),
	_fk("decel", "decel", _ft.F_FLOAT),
	_fk("target", "target", _ft.F_LSTRING),
	_fk("targetname", "targetname", _ft.F_LSTRING),
	_fk("pathtarget", "pathtarget", _ft.F_LSTRING),
	_fk("deathtarget", "deathtarget", _ft.F_LSTRING),
	_fk("killtarget", "killtarget", _ft.F_LSTRING),
	_fk("combattarget", "combattarget", _ft.F_LSTRING),
	_fk("message", "message", _ft.F_LSTRING),
	_fk("team", "team", _ft.F_LSTRING),
	_fk("wait", "wait", _ft.F_FLOAT),
	_fk("delay", "delay", _ft.F_FLOAT),
	_fk("random", "random", _ft.F_FLOAT),
	_fk("move_origin", "move_origin", _ft.F_VECTOR),
	_fk("move_angles", "move_angles", _ft.F_VECTOR),
	_fk("style", "style", _ft.F_INT),
	_fk("count", "count", _ft.F_INT),
	_fk("health", "health", _ft.F_INT),
	_fk("sounds", "sounds", _ft.F_INT),
	_fk("light", None, _ft.F_IGNORE),
	_fk("dmg", "dmg", _ft.F_INT),
	_fk("mass", "mass", _ft.F_INT),
	_fk("volume", "volume", _ft.F_FLOAT),
	_fk("attenuation", "attenuation", _ft.F_FLOAT),
	_fk("map", "map", _ft.F_LSTRING),
	_fk("origin", "s.origin", _ft.F_VECTOR),
	_fk("angles", "s.angles", _ft.F_VECTOR),
	_fk("angle", "s.angles", _ft.F_ANGLEHACK),

	_fk("goalentity", "goalentity", _ft.F_EDICT, _fields_nospawn),
	_fk("movetarget", "movetarget", _ft.F_EDICT, _fields_nospawn),
	_fk("enemy", "enemy", _ft.F_EDICT, _fields_nospawn),
	_fk("oldenemy", "oldenemy", _ft.F_EDICT, _fields_nospawn),
	_fk("activator", "activator", _ft.F_EDICT, _fields_nospawn),
	_fk("groundentity", "groundentity", _ft.F_EDICT, _fields_nospawn),
	_fk("teamchain", "teamchain", _ft.F_EDICT, _fields_nospawn),
	_fk("teammaster", "teammaster", _ft.F_EDICT, _fields_nospawn),
	_fk("owner", "owner", _ft.F_EDICT, _fields_nospawn),
	_fk("mynoise", "mynoise", _ft.F_EDICT, _fields_nospawn),
	_fk("mynoise2", "mynoise2", _ft.F_EDICT, _fields_nospawn),
	_fk("target_ent", "target_ent", _ft.F_EDICT, _fields_nospawn),
	_fk("chain", "chain", _ft.F_EDICT, _fields_nospawn),

	_fk("prethink", "prethink", _ft.F_FUNCTION, _fields_nospawn),
	_fk("think", "think", _ft.F_FUNCTION, _fields_nospawn),
	_fk("blocked", "blocked", _ft.F_FUNCTION, _fields_nospawn),
	_fk("touch", "touch", _ft.F_FUNCTION, _fields_nospawn),
	_fk("use", "use", _ft.F_FUNCTION, _fields_nospawn),
	_fk("pain", "pain", _ft.F_FUNCTION, _fields_nospawn),
	_fk("die", "die", _ft.F_FUNCTION, _fields_nospawn),

	_fk("stand", "monsterinfo.stand", _ft.F_FUNCTION, _fields_nospawn),
	_fk("idle", "monsterinfo.idle", _ft.F_FUNCTION, _fields_nospawn),
	_fk("search", "monsterinfo.search", _ft.F_FUNCTION, _fields_nospawn),
	_fk("walk", "monsterinfo.walk", _ft.F_FUNCTION, _fields_nospawn),
	_fk("run", "monsterinfo.run", _ft.F_FUNCTION, _fields_nospawn),
	_fk("dodge", "monsterinfo.dodge", _ft.F_FUNCTION, _fields_nospawn),
	_fk("attack", "monsterinfo.attack", _ft.F_FUNCTION, _fields_nospawn),
	_fk("melee", "monsterinfo.melee", _ft.F_FUNCTION, _fields_nospawn),
	_fk("sight", "monsterinfo.sight", _ft.F_FUNCTION, _fields_nospawn),
	_fk("checkattack", "monsterinfo.checkattack", _ft.F_FUNCTION, _fields_nospawn),
	_fk("currentmove", "monsterinfo.currentmove", _ft.F_MMOVE, _fields_nospawn),

	_fk("endfunc", "moveinfo.endfunc", _ft.F_FUNCTION, _fields_nospawn),

	# temp spawn vars -- only valid when the spawn function is called
	_fk("lip", "st.lip", _ft.F_INT, local.FFL_SPAWNTEMP),
	_fk("distance", "st.distance", _ft.F_INT, local.FFL_SPAWNTEMP),
	_fk("height", "st.height", _ft.F_INT, local.FFL_SPAWNTEMP),
	_fk("noise", "st.noise", _ft.F_LSTRING, local.FFL_SPAWNTEMP),
	_fk("pausetime", "st.pausetime", _ft.F_FLOAT, local.FFL_SPAWNTEMP),
	_fk("item", "st.item", _ft.F_LSTRING, local.FFL_SPAWNTEMP),

	# need for item field in edict struct, FFL_SPAWNTEMP item will be skipped on saves
	_fk("item", "item", _ft.F_ITEM),

	_fk("gravity", "st.gravity", _ft.F_LSTRING, local.FFL_SPAWNTEMP),
	_fk("sky", "st.sky", _ft.F_LSTRING, local.FFL_SPAWNTEMP),
	_fk("skyrotate", "st.skyrotate", _ft.F_FLOAT, local.FFL_SPAWNTEMP),
	_fk("skyaxis", "st.skyaxis", _ft.F_VECTOR, local.FFL_SPAWNTEMP),
	_fk("minyaw", "st.minyaw", _ft.F_FLOAT, local.FFL_SPAWNTEMP),
	_fk("maxyaw", "st.maxyaw", _ft.F_FLOAT, local.FFL_SPAWNTEMP),
	_fk("minpitch", "st.minpitch", _ft.F_FLOAT, local.FFL_SPAWNTEMP),
	_fk("maxpitch", "st.maxpitch", _ft.F_FLOAT, local.FFL_SPAWNTEMP),
	_fk("nextmap", "st.nextmap", _ft.F_LSTRING, local.FFL_SPAWNTEMP),
]

levelfields = [
	_fk("changemap", "changemap", _ft.F_LSTRING),
	_fk("sight_client", "sight_client", _ft.F_EDICT),
	_fk("sight_entity", "sight_entity", _ft.F_EDICT),
	_fk("sound_entity", "sound_entity", _ft.F_EDICT),
	_fk("sound2_entity", "sound2_entity", _ft.F_EDICT),
]

clientfields = [
	_fk("pers.weapon", "pers.weapon", _ft.F_ITEM),
	_fk("pers.lastweapon", "pers.lastweapon", _ft.F_ITEM),
	_fk("newweapon", "newweapon", _ft.F_ITEM),
]


def _fld_get (obj, path):
	o = obj
	for part in path.split("."):
		o = getattr(o, part)
	return o


def _fld_set (obj, path, val):
	parts = path.split(".")
	o = obj
	for part in parts[:-1]:
		o = getattr(o, part)
	setattr(o, parts[-1], val)


def _safe_index (lst, obj):
	if obj is None:
		return -1
	try:
		return lst.index(obj)
	except ValueError:
		return -1


# function / mmove pointer relocation tables (port of the C code/data-segment offsets)
_func_table = []
_mmove_table = []


def _func_index (fn):
	if fn is None:
		return -1
	if fn in _func_table:
		return _func_table.index(fn)
	_func_table.append(fn)
	return len(_func_table) - 1


def _mmove_index (mv):
	if mv is None:
		return -1
	if mv in _mmove_table:
		return _mmove_table.index(mv)
	_mmove_table.append(mv)
	return len(_mmove_table) - 1


def WriteField1 (f, field, base):
	if field.flags & local.FFL_SPAWNTEMP:
		return

	t = field.type
	if t == _ft.F_INT:
		f.write(struct.pack("i", int(_fld_get(base, field.ofs))))
	elif t == _ft.F_FLOAT:
		f.write(struct.pack("f", float(_fld_get(base, field.ofs))))
	elif t == _ft.F_ANGLEHACK:
		pass	# aliased by the F_VECTOR "angles" field
	elif t == _ft.F_VECTOR:
		v = _fld_get(base, field.ofs)
		f.write(struct.pack("3f", float(v[0]), float(v[1]), float(v[2])))
	elif t == _ft.F_IGNORE:
		pass
	elif t == _ft.F_LSTRING:
		s = _fld_get(base, field.ofs)
		b = (s or "").encode("latin-1")
		f.write(struct.pack("i", len(b)))
	elif t == _ft.F_GSTRING:
		f.write(struct.pack("i", 0))
	elif t == _ft.F_EDICT:
		f.write(struct.pack("i", _safe_index(g_main.g_edicts, _fld_get(base, field.ofs))))
	elif t == _ft.F_CLIENT:
		f.write(struct.pack("i", _safe_index(g_main.game.clients, _fld_get(base, field.ofs))))
	elif t == _ft.F_ITEM:
		f.write(struct.pack("i", _safe_index(g_items.itemlist, _fld_get(base, field.ofs))))
	elif t == _ft.F_FUNCTION:
		f.write(struct.pack("i", _func_index(_fld_get(base, field.ofs))))
	elif t == _ft.F_MMOVE:
		f.write(struct.pack("i", _mmove_index(_fld_get(base, field.ofs))))
	else:
		g_main.gi.error ("WriteEdict: unknown field type")


def WriteField2 (f, field, base):
	if field.flags & local.FFL_SPAWNTEMP:
		return
	if field.type == _ft.F_LSTRING:
		s = _fld_get(base, field.ofs)
		if s:
			f.write(s.encode("latin-1"))


def ReadField (f, field, base):
	if field.flags & local.FFL_SPAWNTEMP:
		return

	t = field.type
	if t == _ft.F_INT:
		_fld_set(base, field.ofs, struct.unpack("i", f.read(4))[0])
	elif t == _ft.F_FLOAT:
		_fld_set(base, field.ofs, struct.unpack("f", f.read(4))[0])
	elif t == _ft.F_ANGLEHACK:
		pass	# aliased by the F_VECTOR "angles" field
	elif t == _ft.F_VECTOR:
		v = struct.unpack("3f", f.read(12))
		cur = _fld_get(base, field.ofs)
		cur[0], cur[1], cur[2] = v
	elif t == _ft.F_IGNORE:
		pass
	elif t == _ft.F_LSTRING:
		length = struct.unpack("i", f.read(4))[0]
		if length == 0:
			_fld_set(base, field.ofs, None)
		else:
			_fld_set(base, field.ofs, f.read(length).decode("latin-1"))
	elif t == _ft.F_GSTRING:
		f.read(4)
	elif t == _ft.F_EDICT:
		idx = struct.unpack("i", f.read(4))[0]
		_fld_set(base, field.ofs, None if idx == -1 else g_main.g_edicts[idx])
	elif t == _ft.F_CLIENT:
		idx = struct.unpack("i", f.read(4))[0]
		_fld_set(base, field.ofs, None if idx == -1 else g_main.game.clients[idx])
	elif t == _ft.F_ITEM:
		idx = struct.unpack("i", f.read(4))[0]
		_fld_set(base, field.ofs, None if idx == -1 else g_items.itemlist[idx])
	elif t == _ft.F_FUNCTION:
		idx = struct.unpack("i", f.read(4))[0]
		_fld_set(base, field.ofs, None if idx < 0 else _func_table[idx])
	elif t == _ft.F_MMOVE:
		idx = struct.unpack("i", f.read(4))[0]
		_fld_set(base, field.ofs, None if idx < 0 else _mmove_table[idx])
	else:
		g_main.gi.error ("ReadEdict: unknown field type")


#=================
# WriteClient
#
# All pointer variables (except function pointers) must be
# handled specially.
#=================
def WriteClient (f, client):
	for field in clientfields:
		WriteField1 (f, field, client)
	for field in clientfields:
		WriteField2 (f, field, client)


#=================
# ReadClient
#
# All pointer variables (except function pointers) must be
# handled specially.
#=================
def ReadClient (f, client):
	for field in clientfields:
		ReadField (f, field, client)


# unpacking helpers for the struct-based game.ssv written by WriteGame

def _unpack_game (f):
	gm = g_main.game
	data = f.read(struct.calcsize(_FMT_GAME))
	(hm1, hm2, helpchanged, clients_ptr, spawnpoint,
	 maxclients, maxentities, serverflags, num_items, autosaved) = struct.unpack(_FMT_GAME, data)
	gm.helpmessage1 = hm1.decode("latin-1").rstrip("\x00")
	gm.helpmessage2 = hm2.decode("latin-1").rstrip("\x00")
	gm.helpchanged = helpchanged
	gm.spawnpoint = spawnpoint.decode("latin-1").rstrip("\x00")
	gm.maxclients = maxclients
	gm.maxentities = maxentities
	gm.serverflags = serverflags
	gm.num_items = num_items
	gm.autosaved = bool(autosaved)


def _unpack_player (f, ps):
	data = f.read(struct.calcsize(_FMT_PLAYER))
	(pm_type, ox, oy, oz, pm_flags, pm_time, gravity, dx, dy, dz) = struct.unpack(_FMT_PMOVE, data[:20])
	pm = ps.pmove
	pm.pm_type = pm_type
	pm.origin = np.array((ox, oy, oz), dtype=np.float32)
	pm.pm_flags = pm_flags
	pm.pm_time = pm_time
	pm.gravity = gravity
	pm.delta_angles = np.array((dx, dy, dz), dtype=np.float32)
	fl = struct.unpack("15f", data[20:80])
	ps.viewangles = np.array(fl[0:3], dtype=np.float32)
	ps.viewoffset = np.array(fl[3:6], dtype=np.float32)
	ps.kick_angles = np.array(fl[6:9], dtype=np.float32)
	ps.gunangles = np.array(fl[9:12], dtype=np.float32)
	ps.gunoffset = np.array(fl[12:15], dtype=np.float32)
	ps.gunindex, ps.gunframe = struct.unpack("ii", data[80:88])
	ps.blend = np.array(struct.unpack("4f", data[88:104]), dtype=np.float32)
	ps.fov = struct.unpack("f", data[104:108])[0]
	ps.rdflags = struct.unpack("i", data[108:112])[0]
	ps.stats = list(struct.unpack("32h", data[112:176]))


def _unpack_client (f, cl):
	_unpack_player (f, cl.ps)
	cl.ping = struct.unpack("i", f.read(4))[0]

"""
=========================================================
WriteGame

This is called when the server writes out the game.ssv
file.  It stores the persistant cross-level state: the
whole game_locals_t struct followed by each client's
gclient_t (player_state_t + ping).
=========================================================
"""
def WriteGame (filename, autosave): #char *, qboolean
	g_main.gi.dprintf ("Writing %s\n", filename)

	# the date string
	if autosave:
		strdata = b"Autosave"
	else:
		strdata = time.strftime("%M %h %d %I:%P", time.localtime())[:15].encode("latin-1")	# Q2PORT: bytes, as the autosave branch; group 9 ports this file

	g_main.game.autosaved = autosave

	f = open(filename, "wb")
	f.write(strdata.ljust(16, b"\0"))
	f.write(_pack_game(g_main.game))
	g_main.game.autosaved = False
	for i in range(int(g_main.game.maxclients)):
		f.write(_pack_client(g_main.game.clients[i]))
	f.close()

def ReadGame (filename): #char *
	g_main.gi.dprintf ("Reading game %s\n", filename)

	f = open(filename, "rb")
	if not f:
		g_main.gi.error ("Couldn't open %s", filename)

	strdata = f.read(16)

	# re-allocate the edicts
	g_main.g_edicts = [game_h.edict_t() for _ in range(int(g_main.game.maxentities))]
	g_main.glob.edicts = g_main.g_edicts
	g_main.glob.max_edicts = int(g_main.game.maxentities)

	# read the game locals
	_unpack_game (f)

	# read the clients
	for i in range(int(g_main.game.maxclients)):
		_unpack_client (f, g_main.game.clients[i])

	f.close()


#=================
# WriteEdict
#
# All pointer variables (except function pointers) must be
# handled specially.
#=================
def WriteEdict (f, ent):
	for field in fields:
		if field.name:
			WriteField1 (f, field, ent)
			WriteField2 (f, field, ent)


#=================
# WriteLevelLocals
#
# All pointer variables (except function pointers) must be
# handled specially.
#=================
def WriteLevelLocals (f):
	level = g_main.level
	for field in levelfields:
		if field.name:
			WriteField1 (f, field, level)
			WriteField2 (f, field, level)


#=================
# ReadEdict
#
# All pointer variables (except function pointers) must be
# handled specially.
#=================
def ReadEdict (f, ent):
	for field in fields:
		if field.name:
			ReadField (f, field, ent)


#=================
# ReadLevelLocals
#
# All pointer variables (except function pointers) must be
# handled specially.
#=================
def ReadLevelLocals (f):
	level = g_main.level
	for field in levelfields:
		if field.name:
			ReadField (f, field, level)


#=================
# WriteLevel
#=================
"""
=================
WriteLevel

=================
"""
def WriteLevel (filename): #char *
	g_main.gi.dprintf ("Writing level %s\n", filename)

	f = open(filename, "wb")
	if not f:
		g_main.gi.error ("Couldn't open %s", filename)

	# write out edict size and a function pointer base for checking
	f.write(struct.pack("ii", 1, 0))

	# write out level_locals_t
	WriteLevelLocals (f)

	# write out all the entities
	for i in range(g_main.glob.num_edicts):
		ent = g_main.g_edicts[i]
		if not ent.inuse:
			continue
		f.write(struct.pack("i", i))
		WriteEdict (f, ent)
	f.write(struct.pack("i", -1))

	f.close()


#=================
# ReadLevel
#
# SpawnEntities will already have been called on the level the
# same way it was when the level was saved.  That is necessary to
# get the baselines set up identically.  The server will have
# cleared all of the world links before calling ReadLevel.  No
# clients are connected yet.
#=================
"""
=================
ReadLevel

SpawnEntities will allready have been called on the
level the same way it was when the level was saved.

That is necessary to get the baselines
set up identically.

The server will have cleared all of the world links before
calling ReadLevel.

No clients are connected yet.
=================
"""
def ReadLevel (filename): #char *
	g_main.gi.dprintf ("Reading level %s\n", filename)

	f = open(filename, "rb")
	if not f:
		g_main.gi.error ("Couldn't open %s", filename)

	# wipe all the entities
	#memset(g_edicts, 0, game.maxentities * sizeof(g_edicts[0]));
	for i in range(len(g_main.g_edicts)):
		g_main.g_edicts[i].__init__()	# Q2PORT: cleared in place, so pointers to the edicts stay valid
	g_main.g_edicts[0].inuse = True
	g_main.glob.num_edicts = int(g_main.maxclients.value) + 1

	# check edict size and function pointer base address
	edict_size, base = struct.unpack("ii", f.read(8))
	g_main.gi.dprintf ("Function offsets %d\n", base)

	# load the level locals
	ReadLevelLocals (f)

	# load all the entities
	while True:
		data = f.read(4)
		if not data:
			f.close()
			g_main.gi.error ("ReadLevel: failed to read entnum")
		entnum = struct.unpack("i", data)[0]
		if entnum == -1:
			break
		if entnum >= g_main.glob.num_edicts:
			g_main.glob.num_edicts = entnum + 1

		ent = g_main.g_edicts[entnum]
		ReadEdict (f, ent)

		# let the server rebuild world links for this ent
		ent.area = game_h.link_t()
		g_main.gi.linkentity (ent)

	f.close()

	# mark all clients as unconnected
	for i in range(int(g_main.maxclients.value)):
		ent = g_main.g_edicts[i + 1]
		ent.client = g_main.game.clients[i]
		ent.client.pers.connected = False

	# do any load time things at this point
	for i in range(g_main.glob.num_edicts):
		ent = g_main.g_edicts[i]

		if not ent.inuse:
			continue

		# fire any cross-level triggers
		if ent.classname:
			if ent.classname == "target_crosslevel_target":
				ent.nextthink = g_main.level.time + ent.delay
"""

//=========================================================

//=========================================================
"""
"""
/*
==============
WriteClient

All pointer variables (except function pointers) must be handled specially.
==============
*/
void WriteClient (FILE *f, gclient_t *client)
{
	field_t		*field;
	gclient_t	temp;
	
	// all of the ints, floats, and vectors stay as they are
	temp = *client;

	// change the pointers to lengths or indexes
	for (field=clientfields ; field->name ; field++)
	{
		WriteField1 (f, field, (byte *)&temp);
	}

	// write the block
	fwrite (&temp, sizeof(temp), 1, f);

	// now write any allocated data following the edict
	for (field=clientfields ; field->name ; field++)
	{
		WriteField2 (f, field, (byte *)client);
	}
}
"""
"""
/*
==============
ReadClient

All pointer variables (except function pointers) must be handled specially.
==============
*/
void ReadClient (FILE *f, gclient_t *client)
{
	field_t		*field;

	fread (client, sizeof(*client), 1, f);

	for (field=clientfields ; field->name ; field++)
	{
		ReadField (f, field, (byte *)client);
	}
}
"""
"""

//==========================================================
"""
"""
/*
==============
WriteEdict

All pointer variables (except function pointers) must be handled specially.
==============
*/
void WriteEdict (FILE *f, edict_t *ent)
{
	field_t		*field;
	edict_t		temp;

	// all of the ints, floats, and vectors stay as they are
	temp = *ent;

	// change the pointers to lengths or indexes
	for (field=fields ; field->name ; field++)
	{
		WriteField1 (f, field, (byte *)&temp);
	}

	// write the block
	fwrite (&temp, sizeof(temp), 1, f);

	// now write any allocated data following the edict
	for (field=fields ; field->name ; field++)
	{
		WriteField2 (f, field, (byte *)ent);
	}

}
"""
"""
/*
==============
WriteLevelLocals

All pointer variables (except function pointers) must be handled specially.
==============
*/
void WriteLevelLocals (FILE *f)
{
	field_t		*field;
	level_locals_t		temp;

	// all of the ints, floats, and vectors stay as they are
	temp = level;

	// change the pointers to lengths or indexes
	for (field=levelfields ; field->name ; field++)
	{
		WriteField1 (f, field, (byte *)&temp);
	}

	// write the block
	fwrite (&temp, sizeof(temp), 1, f);

	// now write any allocated data following the edict
	for (field=levelfields ; field->name ; field++)
	{
		WriteField2 (f, field, (byte *)&level);
	}
}
"""
"""
/*
==============
ReadEdict

All pointer variables (except function pointers) must be handled specially.
==============
*/
void ReadEdict (FILE *f, edict_t *ent)
{
	field_t		*field;

	fread (ent, sizeof(*ent), 1, f);

	for (field=fields ; field->name ; field++)
	{
		ReadField (f, field, (byte *)ent);
	}
}
"""
"""
/*
==============
ReadLevelLocals

All pointer variables (except function pointers) must be handled specially.
==============
*/
void ReadLevelLocals (FILE *f)
{
	field_t		*field;

	fread (&level, sizeof(level), 1, f);

	for (field=levelfields ; field->name ; field++)
	{
		ReadField (f, field, (byte *)&level);
	}
}
"""
