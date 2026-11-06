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

Item spawning.

=======================================================================
"""
from __future__ import annotations

from game import g_main, g_utils
from common.header.shared import CS_NAME, CS_SKY, CS_SKYROTATE, CS_SKYAXIS, CS_CDTRACK, CS_MAXCLIENTS, CS_STATUSBAR, CS_LIGHTS
import numpy as np
import math
from common.shared import shared as shared_c
from game.header import game as game_h
from game.header import local

"""
#include "header/local.h"
#include "savegame/tables/spawnfunc_decs.h"
#include "savegame/tables/spawnfunc_list.h"
"""

# C: extern spawn_temp_t st; -- defined in g_main.c, referenced here as g_main.st

# C: field_t fields[] -- the fields parsed out of the .map file.
# (name, type, flags).  FFL_NOSPAWN fields are save/load only and are skipped.

_ft = local.fieldtype_t
_flt = local.FFL_SPAWNTEMP
fields = [
	("classname", _ft.F_LSTRING, 0),
	("model", _ft.F_LSTRING, 0),
	("spawnflags", _ft.F_INT, 0),
	("speed", _ft.F_FLOAT, 0),
	("accel", _ft.F_FLOAT, 0),
	("decel", _ft.F_FLOAT, 0),
	("target", _ft.F_LSTRING, 0),
	("targetname", _ft.F_LSTRING, 0),
	("pathtarget", _ft.F_LSTRING, 0),
	("deathtarget", _ft.F_LSTRING, 0),
	("killtarget", _ft.F_LSTRING, 0),
	("combattarget", _ft.F_LSTRING, 0),
	("message", _ft.F_LSTRING, 0),
	("team", _ft.F_LSTRING, 0),
	("wait", _ft.F_FLOAT, 0),
	("delay", _ft.F_FLOAT, 0),
	("random", _ft.F_FLOAT, 0),
	("move_origin", _ft.F_VECTOR, 0),
	("move_angles", _ft.F_VECTOR, 0),
	("style", _ft.F_INT, 0),
	("count", _ft.F_INT, 0),
	("health", _ft.F_INT, 0),
	("sounds", _ft.F_INT, 0),
	("light", _ft.F_IGNORE, 0),
	("dmg", _ft.F_INT, 0),
	("mass", _ft.F_INT, 0),
	("volume", _ft.F_FLOAT, 0),
	("attenuation", _ft.F_FLOAT, 0),
	("map", _ft.F_LSTRING, 0),
	("origin", _ft.F_VECTOR, 0),
	("angles", _ft.F_VECTOR, 0),
	("angle", _ft.F_ANGLEHACK, 0),
	# temp spawn vars -- only valid when the spawn function is called
	("lip", _ft.F_INT, _flt),
	("distance", _ft.F_INT, _flt),
	("height", _ft.F_INT, _flt),
	("noise", _ft.F_LSTRING, _flt),
	("pausetime", _ft.F_FLOAT, _flt),
	("item", _ft.F_LSTRING, _flt),
	("gravity", _ft.F_LSTRING, _flt),
	("sky", _ft.F_LSTRING, _flt),
	("skyrotate", _ft.F_FLOAT, _flt),
	("skyaxis", _ft.F_VECTOR, _flt),
	("music", _ft.F_LSTRING, _flt),
	("minyaw", _ft.F_FLOAT, _flt),
	("maxyaw", _ft.F_FLOAT, _flt),
	("minpitch", _ft.F_FLOAT, _flt),
	("maxpitch", _ft.F_FLOAT, _flt),
	("nextmap", _ft.F_LSTRING, _flt),
]

# C: spawn_t spawns[] -- classname -> SP_ function name.
_spawns_raw = [
	("item_health", "SP_item_health"),
	("item_health_small", "SP_item_health_small"),
	("item_health_large", "SP_item_health_large"),
	("item_health_mega", "SP_item_health_mega"),
	("info_player_start", "SP_info_player_start"),
	("info_player_deathmatch", "SP_info_player_deathmatch"),
	("info_player_coop", "SP_info_player_coop"),
	("info_player_intermission", "SP_info_player_intermission"),
	("func_plat", "SP_func_plat"),
	("func_button", "SP_func_button"),
	("func_door", "SP_func_door"),
	("func_door_secret", "SP_func_door_secret"),
	("func_door_rotating", "SP_func_door_rotating"),
	("func_rotating", "SP_func_rotating"),
	("func_train", "SP_func_train"),
	("func_water", "SP_func_water"),
	("func_conveyor", "SP_func_conveyor"),
	("func_areaportal", "SP_func_areaportal"),
	("func_clock", "SP_func_clock"),
	("func_wall", "SP_func_wall"),
	("func_object", "SP_func_object"),
	("func_timer", "SP_func_timer"),
	("func_explosive", "SP_func_explosive"),
	("func_killbox", "SP_func_killbox"),
	("trigger_always", "SP_trigger_always"),
	("trigger_once", "SP_trigger_once"),
	("trigger_multiple", "SP_trigger_multiple"),
	("trigger_relay", "SP_trigger_relay"),
	("trigger_push", "SP_trigger_push"),
	("trigger_hurt", "SP_trigger_hurt"),
	("trigger_key", "SP_trigger_key"),
	("trigger_counter", "SP_trigger_counter"),
	("trigger_elevator", "SP_trigger_elevator"),
	("trigger_gravity", "SP_trigger_gravity"),
	("trigger_monsterjump", "SP_trigger_monsterjump"),
	("target_temp_entity", "SP_target_temp_entity"),
	("target_speaker", "SP_target_speaker"),
	("target_explosion", "SP_target_explosion"),
	("target_changelevel", "SP_target_changelevel"),
	("target_secret", "SP_target_secret"),
	("target_goal", "SP_target_goal"),
	("target_splash", "SP_target_splash"),
	("target_spawner", "SP_target_spawner"),
	("target_blaster", "SP_target_blaster"),
	("target_crosslevel_trigger", "SP_target_crosslevel_trigger"),
	("target_crosslevel_target", "SP_target_crosslevel_target"),
	("target_laser", "SP_target_laser"),
	("target_help", "SP_target_help"),
	("target_actor", "SP_target_actor"),
	("target_lightramp", "SP_target_lightramp"),
	("target_earthquake", "SP_target_earthquake"),
	("target_character", "SP_target_character"),
	("target_string", "SP_target_string"),
	("worldspawn", "SP_worldspawn"),
	("viewthing", "SP_viewthing"),
	("light", "SP_light"),
	("light_mine1", "SP_light_mine1"),
	("light_mine2", "SP_light_mine2"),
	("info_null", "SP_info_null"),
	("func_group", "SP_info_null"),
	("info_notnull", "SP_info_notnull"),
	("path_corner", "SP_path_corner"),
	("point_combat", "SP_point_combat"),
	("misc_explobox", "SP_misc_explobox"),
	("misc_banner", "SP_misc_banner"),
	("misc_satellite_dish", "SP_misc_satellite_dish"),
	("misc_actor", "SP_misc_actor"),
	("misc_gib_arm", "SP_misc_gib_arm"),
	("misc_gib_leg", "SP_misc_gib_leg"),
	("misc_gib_head", "SP_misc_gib_head"),
	("misc_insane", "SP_misc_insane"),
	("misc_deadsoldier", "SP_misc_deadsoldier"),
	("misc_viper", "SP_misc_viper"),
	("misc_viper_bomb", "SP_misc_viper_bomb"),
	("misc_bigviper", "SP_misc_bigviper"),
	("misc_strogg_ship", "SP_misc_strogg_ship"),
	("misc_teleporter", "SP_misc_teleporter"),
	("misc_teleporter_dest", "SP_misc_teleporter_dest"),
	("misc_blackhole", "SP_misc_blackhole"),
	("misc_eastertank", "SP_misc_eastertank"),
	("misc_easterchick", "SP_misc_easterchick"),
	("misc_easterchick2", "SP_misc_easterchick2"),
	("monster_berserk", "SP_monster_berserk"),
	("monster_gladiator", "SP_monster_gladiator"),
	("monster_gunner", "SP_monster_gunner"),
	("monster_infantry", "SP_monster_infantry"),
	("monster_soldier_light", "SP_monster_soldier_light"),
	("monster_soldier", "SP_monster_soldier"),
	("monster_soldier_ss", "SP_monster_soldier_ss"),
	("monster_tank", "SP_monster_tank"),
	("monster_tank_commander", "SP_monster_tank"),
	("monster_medic", "SP_monster_medic"),
	("monster_flipper", "SP_monster_flipper"),
	("monster_chick", "SP_monster_chick"),
	("monster_parasite", "SP_monster_parasite"),
	("monster_flyer", "SP_monster_flyer"),
	("monster_brain", "SP_monster_brain"),
	("monster_floater", "SP_monster_floater"),
	("monster_hover", "SP_monster_hover"),
	("monster_mutant", "SP_monster_mutant"),
	("monster_supertank", "SP_monster_supertank"),
	("monster_boss2", "SP_monster_boss2"),
	("monster_boss3_stand", "SP_monster_boss3_stand"),
	("monster_jorg", "SP_monster_jorg"),
	("monster_commander_body", "SP_monster_commander_body"),
	("turret_breach", "SP_turret_breach"),
	("turret_base", "SP_turret_base"),
	("turret_driver", "SP_turret_driver"),
]

_spawn_cache = None
def _find_spawn (classname):
	# resolve lazily so all the SP_ modules are fully loaded
	global _spawn_cache
	if _spawn_cache is None:
		from game import g_items
		from game import g_func
		from game import g_target
		from game import g_misc
		from game import g_turret
		from game.player import client as p_client
		from game import m_actor, m_berserk, m_boss2, m_boss3, m_boss31, m_supertank
		from game import g_trigger, m_infantry, m_soldier, m_boss32, m_gunner, m_flyer
		from game import m_brain, m_chick, m_flipper, m_float, m_gladiator, m_hover, m_insane, m_medic, m_mutant, m_parasite, m_tank
		from game import g_spawn
		srcs = (g_spawn, g_items, g_func, g_target, g_misc, p_client, g_turret,
			m_actor, m_berserk, m_boss2, m_boss3, m_boss31, m_supertank,
			g_trigger, m_infantry, m_soldier, m_boss32, m_gunner, m_flyer,
			m_brain, m_chick, m_flipper, m_float, m_gladiator, m_hover, m_insane, m_medic, m_mutant, m_parasite, m_tank)
		_spawn_cache = []
		for _cls, _spname in _spawns_raw:
			_fn = None
			for _mod in srcs:
				if hasattr(_mod, _spname):
					_fn = getattr(_mod, _spname)
					break
			if _fn is not None:
				_spawn_cache.append((_cls, _fn))
	for name, fn in _spawn_cache:
		if name == classname:
			return fn
	return None

def ED_CallSpawn (ent):
	if not ent:

		return


	from game import g_items
	#spawn_t	*s;
	#gitem_t	*item;
	#int		i;

	if not ent.classname:
		g_main.gi.dprintf ("%s: NULL classname\n", "ED_CallSpawn")
		g_utils.G_FreeEdict (ent)
		return

	# check item spawn functions
	for i in range(g_items.itemlist_len):
		item = g_items.itemlist[i]
		if not item.classname:
			continue
		if item.classname == ent.classname:	# found it
			g_items.SpawnItem (ent, item)
			return

	# check normal spawn functions
	fn = _find_spawn (ent.classname)
	if fn is not None:
		fn (ent)
		return
	g_main.gi.dprintf ("%s doesn't have a spawn function\n", ent.classname)

def ED_NewString (string):
	#char	*newb, *new_p;
	#int		i,l;

	# C copies into TAG_LEVEL memory; in Python the string is the value.
	# Only backslash-n needs translating.
	if string is None:

		return None


	out = []
	i = 0
	while i < len(string):
		if string[i] == '\\' and i < len(string)-1:
			i += 1
			if string[i] == 'n':
				out.append ('\n')
			else:
				out.append ('\\')
		else:
			out.append (string[i])
		i += 1
	return "".join(out)

def ED_ParseField (key, value, ent):
	#field_t	*f;
	if not ent or value is None or key is None:

		return


	for name, ftype, flags in fields:
		if not (flags & local.FFL_NOSPAWN) and shared_c.Q_stricmp (name, key) == 0:	# found it
			if ftype == _ft.F_LSTRING:
				v = ED_NewString (value)
			elif ftype == _ft.F_VECTOR:
				# sscanf(value, "%f %f %f", ...) != 3
				try:
					parts = value.split ()
					v = np.array([float(parts[0]), float(parts[1]), float(parts[2])], dtype=np.float32)
				except (ValueError, IndexError):
					v = np.zeros((3,), dtype=np.float32)
					g_main.gi.dprintf ("%s: entity %d: incomplete '%s' field\n", "ED_ParseField", ent.s.number, name)
			elif ftype == _ft.F_INT:
				try:
					v = int(float(value))
				except ValueError:
					v = 0
			elif ftype == _ft.F_FLOAT:
				try:
					v = float(value)
				except ValueError:
					v = 0.0
			elif ftype == _ft.F_ANGLEHACK:
				try:
					a = float(value)
				except ValueError:
					a = 0.0
				v = np.array([0.0, a, 0.0], dtype=np.float32)
			elif ftype == _ft.F_IGNORE:
				return
			else:
				return
			if name == "origin":
				ent.s.origin = v
			elif name == "angles" or name == "angle":
				ent.s.angles = v
			elif flags & local.FFL_SPAWNTEMP:
				setattr (g_main.st, name, v)
			else:
				setattr (ent, name, v)
			return
	g_main.gi.dprintf ("'%s' is not a field. Value is '%s'\n", key, value)
"""
')
"""

def ED_ParseEdict (data, ent, cursor):
	#qboolean	init;
	if not ent:

		return None


	init = False
	#memset (&st, 0, sizeof(st));
	g_main.st.__dict__.update(local.spawn_temp_t().__dict__)

	# go through all the dictionary pairs
	while 1:
		# parse key
		keyname, cursor = shared_c.COM_Parse (data, cursor)
		if keyname == '}':
			break
		if cursor is None:
			g_main.gi.error ("ED_ParseEntity: EOF without closing brace")

		# parse value
		com_token, cursor = shared_c.COM_Parse (data, cursor)
		if cursor is None:
			g_main.gi.error ("ED_ParseEntity: EOF without closing brace")

		if com_token == '}':
			g_main.gi.error ("ED_ParseEntity: closing brace without data")
		init = True

		# keynames with a leading underscore are utility comments, discarded
		if keyname[0] == '_':
			continue

		ED_ParseField (keyname, com_token, ent)

	if not init:
		ent.__dict__.update(game_h.edict_t().__dict__)

	return cursor

def G_FindTeams ():
	#edict_t	*e, *e2, *chain;
	#int		i, j;
	#int		c, c2;

	c = 0
	c2 = 0
	edicts = g_main.g_edicts
	for i in range(1, g_main.glob.num_edicts):
		e = edicts[i]
		if not e.inuse:
			continue
		if not e.team:
			continue
		if e.flags & local.FL_TEAMSLAVE:
			continue
		chain = e
		e.teammaster = e
		c += 1
		c2 += 1
		for j in range(i+1, g_main.glob.num_edicts):
			e2 = edicts[j]
			if not e2.inuse:
				continue
			if not e2.team:
				continue
			if e2.flags & local.FL_TEAMSLAVE:
				continue
			if e.team == e2.team:
				c2 += 1
				chain.teamchain = e2
				e2.teammaster = e
				chain = e2
				e2.flags |= local.FL_TEAMSLAVE

	g_main.gi.dprintf ("%i teams with %i entities.\n", c, c2)

def SpawnEntities (mapname, entities, spawnpoint):
	if mapname is None or entities is None or spawnpoint is None:

		return


	from game.player import client as p_client
	from game.player import trail as p_trail
	#edict_t		*ent;
	#int			inhibit;
	#int			i;
	#float		skill_level;

	skill_level = math.floor (g_main.skill.value)
	if skill_level < 0:
		skill_level = 0
	if skill_level > 3:
		skill_level = 3
	if g_main.skill.value != skill_level:
		g_main.gi.cvar_forceset ("skill", "%f" % skill_level)

	p_client.SaveClientData ()

	# gi.FreeTags (TAG_LEVEL);  -- Python GC handles this

	g_main.level.__dict__.update(local.level_locals_t().__dict__)
	for i in range(g_main.game.maxentities):
		g_main.g_edicts[i].__dict__.update(game_h.edict_t().__dict__)

	g_main.level.mapname = mapname
	g_main.game.spawnpoint = spawnpoint

	# set client fields on player ents
	for i in range(g_main.game.maxclients):
		g_main.g_edicts[i+1].client = g_main.game.clients[i]

	ent = None
	inhibit = 0
	cursor = 0

	# parse ents
	while 1:
		# parse the opening brace
		token, cursor = shared_c.COM_Parse (entities, cursor)
		if cursor is None:
			break
		if token[0] != '{':
			g_main.gi.error ("ED_LoadFromFile: found %s when expecting {", token)

		if not ent:
			ent = g_main.g_edicts[0]
		else:
			ent = g_utils.G_Spawn ()
		cursor = ED_ParseEdict (entities, ent, cursor)

		# yet another map hack
		if shared_c.Q_stricmp(g_main.level.mapname, "command") == 0 and shared_c.Q_stricmp(ent.classname, "trigger_once") == 0 and shared_c.Q_stricmp(ent.model, "*27") == 0:
			ent.spawnflags &= ~local.SPAWNFLAG_NOT_HARD

		# remove things (except the world) from different skill levels / deathmatch
		if ent is not g_main.g_edicts[0]:
			if g_main.deathmatch.value:
				if ( ent.spawnflags & local.SPAWNFLAG_NOT_DEATHMATCH ):
					g_utils.G_FreeEdict (ent)
					inhibit += 1
					continue
			else:
				if (
					((g_main.skill.value == local.SKILL_EASY) and (ent.spawnflags & local.SPAWNFLAG_NOT_EASY)) or
					((g_main.skill.value == local.SKILL_MEDIUM) and (ent.spawnflags & local.SPAWNFLAG_NOT_MEDIUM)) or
					(((g_main.skill.value == local.SKILL_HARD) or (g_main.skill.value == local.SKILL_HARDPLUS)) and (ent.spawnflags & local.SPAWNFLAG_NOT_HARD))
					):
					g_utils.G_FreeEdict (ent)
					inhibit += 1
					continue

			ent.spawnflags &= ~(local.SPAWNFLAG_NOT_EASY|local.SPAWNFLAG_NOT_MEDIUM|local.SPAWNFLAG_NOT_HARD|local.SPAWNFLAG_NOT_COOP|local.SPAWNFLAG_NOT_DEATHMATCH)

		ED_CallSpawn (ent)

	# in case the last entity in the entstring has spawntemp fields
	g_main.st.__init__() #memset(&st, 0, sizeof(st));

	g_main.gi.dprintf ("%i entities inhibited.\n", inhibit)

	G_FindTeams ()

	p_trail.PlayerTrail_Init ()

#
# Status bar display programs (from g_spawn.c).
#

single_statusbar = \
	"yb\t-24 " \
	"xv\t0 " \
	"hnum " \
	"xv\t50 " \
	"pic 0 " \
	"if 2 " \
	"\txv\t100 " \
	"\tanum " \
	"\txv\t150 " \
	"\tpic 2 " \
	"endif " \
	"if 4 " \
	"\txv\t200 " \
	"\trnum " \
	"\txv\t250 " \
	"\tpic 4 " \
	"endif " \
	"if 6 " \
	"\txv\t296 " \
	"\tpic 6 " \
	"endif " \
	"yb\t-50 " \
	"if 7 " \
	"\txv\t0 " \
	"\tpic 7 " \
	"\txv\t26 " \
	"\tyb\t-42 " \
	"\tstat_string 8 " \
	"\tyb\t-50 " \
	"endif " \
	"if 9 " \
	"\txv\t262 " \
	"\tnum\t2\t10 " \
	"\txv\t296 " \
	"\tpic\t9 " \
	"endif " \
	"if 11 " \
	"\txv\t148 " \
	"\tpic\t11 " \
	"endif " \
	;

dm_statusbar = \
	"yb\t-24 " \
	"xv\t0 " \
	"hnum " \
	"xv\t50 " \
	"pic 0 " \
	"if 2 " \
	"\txv\t100 " \
	"\tanum " \
	"\txv\t150 " \
	"\tpic 2 " \
	"endif " \
	"if 4 " \
	"\txv\t200 " \
	"\trnum " \
	"\txv\t250 " \
	"\tpic 4 " \
	"endif " \
	"if 6 " \
	"\txv\t296 " \
	"\tpic 6 " \
	"endif " \
	"yb\t-50 " \
	"if 7 " \
	"\txv\t0 " \
	"\tpic 7 " \
	"\txv\t26 " \
	"\tyb\t-42 " \
	"\tstat_string 8 " \
	"\tyb\t-50 " \
	"endif " \
	"if 9 " \
	"\txv\t246 " \
	"\tnum\t2\t10 " \
	"\txv\t296 " \
	"\tpic\t9 " \
	"endif " \
	"if 11 " \
	"\txv\t148 " \
	"\tpic\t11 " \
	"endif " \
	"xr\t-50 " \
	"yt 2 " \
	"num 3 14 " \
	"if 17 " \
	"  xv 0 " \
	"  yb -58 " \
	"  string2 \"SPECTATOR MODE\" " \
	"endif " \
	"if 16 " \
	"  xv 0 " \
	"  yb -68 " \
	"  string \"Chasing\" " \
	"  xv 64 " \
	"  stat_string 16 " \
	"endif " \
	;


"""
=============
SP_worldspawn

Only used for the world.
"sky"		environment map name
"skyaxis"	vector axis for rotating sky
"skyrotate"	speed of rotation in degrees/second
"sounds"	music cd track number
"gravity"	800 is default gravity
"message"	text to print at user logon
=============
"""
def SP_worldspawn (self):
	if not self:

		return


	from game import g_items
	from game.player import client as p_client
	#edict_t *ent
	gi = g_main.gi

	self.movetype = local.MOVETYPE_PUSH
	self.solid = game_h.SOLID_BSP
	self.inuse = True  # since the world doesn't use G_Spawn()
	self.s.modelindex = 1  # world model is always index 1

	#---------------

	# reserve some spots for dead player bodies for coop / deathmatch
	p_client.InitBodyQue ()

	# set configstrings for items
	g_items.SetItemNames ()

	if g_main.st.nextmap:
		g_main.level.nextmap = g_main.st.nextmap

	# make some data visible to the server

	if self.message and self.message[0]:
		gi.configstring (CS_NAME, self.message)
		g_main.level.level_name = self.message
	else:
		g_main.level.level_name = g_main.level.mapname

	if g_main.st.sky and g_main.st.sky[0]:
		gi.configstring (CS_SKY, g_main.st.sky)
	else:
		gi.configstring (CS_SKY, "unit1_")

	gi.configstring (CS_SKYROTATE, "%f" % g_main.st.skyrotate)

	gi.configstring (CS_SKYAXIS, "%f %f %f" % (
		g_main.st.skyaxis[0], g_main.st.skyaxis[1], g_main.st.skyaxis[2]) )

	if g_main.st.music:

		gi.configstring (CS_CDTRACK, g_main.st.music)

	else:

		gi.configstring (CS_CDTRACK, "%i" % self.sounds)


	gi.configstring (CS_MAXCLIENTS, "%i" % int(g_main.maxclients.value) )

	# status bar program
	if g_main.deathmatch.value:
		gi.configstring (CS_STATUSBAR, dm_statusbar)
	else:
		gi.configstring (CS_STATUSBAR, single_statusbar)

	#---------------


	# help icon for statusbar
	gi.imageindex ("i_help")
	g_main.level.pic_health = gi.imageindex ("i_health")
	gi.imageindex ("help")
	gi.imageindex ("field_3")

	if not g_main.st.gravity:
		gi.cvar_set("sv_gravity", "800")
	else:
		gi.cvar_set("sv_gravity", str(g_main.st.gravity))

	g_main.snd_fry = gi.soundindex ("player/fry.wav")  # standing in lava / slime

	g_items.PrecacheItem (g_items.FindItem ("Blaster"))

	gi.soundindex ("player/lava1.wav")
	gi.soundindex ("player/lava2.wav")

	gi.soundindex ("misc/pc_up.wav")
	gi.soundindex ("misc/talk1.wav")

	gi.soundindex ("misc/udeath.wav")

	# gibs
	gi.soundindex ("items/respawn1.wav")

	# sexed sounds
	gi.soundindex ("*death1.wav")
	gi.soundindex ("*death2.wav")
	gi.soundindex ("*death3.wav")
	gi.soundindex ("*death4.wav")
	gi.soundindex ("*fall1.wav")
	gi.soundindex ("*fall2.wav")
	gi.soundindex ("*gurp1.wav")  # drowning damage
	gi.soundindex ("*gurp2.wav")
	gi.soundindex ("*jump1.wav")  # player jump
	gi.soundindex ("*pain25_1.wav")
	gi.soundindex ("*pain25_2.wav")
	gi.soundindex ("*pain50_1.wav")
	gi.soundindex ("*pain50_2.wav")
	gi.soundindex ("*pain75_1.wav")
	gi.soundindex ("*pain75_2.wav")
	gi.soundindex ("*pain100_1.wav")
	gi.soundindex ("*pain100_2.wav")

	# sexed models
	# THIS ORDER MUST MATCH THE DEFINES IN g_local.h
	# you can add more, max 15
	if g_main.coop.value or g_main.deathmatch.value:

		gi.modelindex ("#w_blaster.md2")

	gi.modelindex ("#w_shotgun.md2")
	gi.modelindex ("#w_sshotgun.md2")
	gi.modelindex ("#w_machinegun.md2")
	gi.modelindex ("#w_chaingun.md2")
	gi.modelindex ("#a_grenades.md2")
	gi.modelindex ("#w_glauncher.md2")
	gi.modelindex ("#w_rlauncher.md2")
	gi.modelindex ("#w_hyperblaster.md2")
	gi.modelindex ("#w_railgun.md2")
	gi.modelindex ("#w_bfg.md2")

	#-------------------

	gi.soundindex ("player/gasp1.wav")  # gasping for air
	gi.soundindex ("player/gasp2.wav")  # head breaking surface, not gasping

	gi.soundindex ("player/watr_in.wav")  # feet hitting water
	gi.soundindex ("player/watr_out.wav")  # feet leaving water

	gi.soundindex ("player/watr_un.wav")  # head going underwater

	gi.soundindex ("player/u_breath1.wav")
	gi.soundindex ("player/u_breath2.wav")

	gi.soundindex ("items/pkup.wav")  # bonus item pickup
	gi.soundindex ("world/land.wav")  # landing thud
	gi.soundindex ("misc/h2ohit1.wav")  # landing splash

	gi.soundindex ("items/damage.wav")
	gi.soundindex ("items/protect.wav")
	gi.soundindex ("items/protect4.wav")
	gi.soundindex ("weapons/noammo.wav")

	gi.soundindex ("infantry/inflies1.wav")

	g_main.sm_meat_index = gi.modelindex ("models/objects/gibs/sm_meat/tris.md2")
	gi.modelindex ("models/objects/gibs/arm/tris.md2")
	gi.modelindex ("models/objects/gibs/bone/tris.md2")
	gi.modelindex ("models/objects/gibs/bone2/tris.md2")
	gi.modelindex ("models/objects/gibs/chest/tris.md2")
	gi.modelindex ("models/objects/gibs/skull/tris.md2")
	gi.modelindex ("models/objects/gibs/head2/tris.md2")

	#
	# Setup light animation tables. 'a' is total darkness, 'z' is doublebright.
	#

	# 0 normal
	gi.configstring(CS_LIGHTS+0, "m")

	# 1 FLICKER (first variety)
	gi.configstring(CS_LIGHTS+1, "mmnmmommommnonmmonqnmmo")

	# 2 SLOW STRONG PULSE
	gi.configstring(CS_LIGHTS+2, "abcdefghijklmnopqrstuvwxyzyxwvutsrqponmlkjihgfedcba")

	# 3 CANDLE (first variety)
	gi.configstring(CS_LIGHTS+3, "mmmmmaaaaammmmmaaaaaabcdefgabcdefg")

	# 4 FAST STROBE
	gi.configstring(CS_LIGHTS+4, "mamamamamama")

	# 5 GENTLE PULSE 1
	gi.configstring(CS_LIGHTS+5, "jklmnopqrstuvwxyzyxwvutsrqponmlkj")

	# 6 FLICKER (second variety)
	gi.configstring(CS_LIGHTS+6, "nmonqnmomnmomomno")

	# 7 CANDLE (second variety)
	gi.configstring(CS_LIGHTS+7, "mmmaaaabcdefgmmmmaaaammmaamm")

	# 8 CANDLE (third variety)
	gi.configstring(CS_LIGHTS+8, "mmmaaammmaaammmabcdefaaaammmmabcdefmmmaaaa")

	# 9 SLOW STROBE (fourth variety)
	gi.configstring(CS_LIGHTS+9, "aaaaaaaazzzzzzzz")

	# 10 FLUORESCENT FLICKER
	gi.configstring(CS_LIGHTS+10, "mmamammmmammamamaaamammma")

	# 11 SLOW PULSE NOT FADE TO BLACK
	gi.configstring(CS_LIGHTS+11, "abcdefghijklmnopqrrqponmlkjihgfedcba")

	# styles 32-62 are assigned by the light program for switchable lights

	# 63 testing
	gi.configstring(CS_LIGHTS+63, "a")
