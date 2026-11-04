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
import struct
import time

from game import g_main, q_shared, game, g_items
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

/*
============
InitGame

This will be called when the dll is first loaded, which
only happens when a new game is started or a save game
is loaded.
============
"""
def InitGame ():

	"""
	g_main.gi.dprintf ("==== InitGame ====\n");

	gun_x = g_main.gi.cvar ("gun_x", "0", 0);
	gun_y = g_main.gi.cvar ("gun_y", "0", 0);
	gun_z = g_main.gi.cvar ("gun_z", "0", 0);

	//FIXME: sv_ prefix is wrong for these
	sv_rollspeed = g_main.gi.cvar ("sv_rollspeed", "200", 0);
	sv_rollangle = g_main.gi.cvar ("sv_rollangle", "2", 0);
	sv_maxvelocity = g_main.gi.cvar ("sv_maxvelocity", "2000", 0);
	sv_gravity = g_main.gi.cvar ("sv_gravity", "800", 0);

	// noset vars
	dedicated = g_main.gi.cvar ("dedicated", "0", CVAR_NOSET);

	// latched vars
	sv_cheats = g_main.gi.cvar ("cheats", "0", q_shared.CVAR_SERVERINFO|q_shared.CVAR_LATCH);
	g_main.gi.cvar ("gamename", GAMEVERSION , q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH);
	g_main.gi.cvar ("gamedate", __DATE__ , q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH);

	maxclients = g_main.gi.cvar ("maxclients", "4", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH);
	maxspectators = g_main.gi.cvar ("maxspectators", "4", q_shared.CVAR_SERVERINFO);	
	"""
	g_main.deathmatch = g_main.gi.cvar ("deathmatch", "0", q_shared.CVAR_LATCH)
	g_main.coop = g_main.gi.cvar ("coop", "0", q_shared.CVAR_LATCH)
	g_main.skill = g_main.gi.cvar ("skill", "1", q_shared.CVAR_LATCH)
	g_main.maxclients = g_main.gi.cvar ("maxclients", "4", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)
	g_main.maxspectators = g_main.gi.cvar ("maxspectators", "4", q_shared.CVAR_SERVERINFO)
	g_main.maxentities = g_main.gi.cvar ("maxentities", "1024", q_shared.CVAR_LATCH)

	# change anytime vars
	g_main.dmflags = g_main.gi.cvar ("dmflags", "0", q_shared.CVAR_SERVERINFO)
	g_main.fraglimit = g_main.gi.cvar ("fraglimit", "0", q_shared.CVAR_SERVERINFO)
	g_main.timelimit = g_main.gi.cvar ("timelimit", "0", q_shared.CVAR_SERVERINFO)
	g_main.password = g_main.gi.cvar ("password", "", q_shared.CVAR_USERINFO)
	g_main.spectator_password = g_main.gi.cvar ("spectator_password", "", q_shared.CVAR_USERINFO)
	g_main.needpass = g_main.gi.cvar ("needpass", "0", q_shared.CVAR_SERVERINFO)
	g_main.filterban = g_main.gi.cvar ("filterban", "1", 0)

	g_main.g_select_empty = g_main.gi.cvar ("g_select_empty", "0", q_shared.CVAR_ARCHIVE)

	g_main.run_pitch = g_main.gi.cvar ("run_pitch", "0.002", 0)
	g_main.run_roll = g_main.gi.cvar ("run_roll", "0.005", 0)
	g_main.bob_up = g_main.gi.cvar ("bob_up", "0.005", 0)
	g_main.bob_pitch = g_main.gi.cvar ("bob_pitch", "0.002", 0)
	g_main.bob_roll = g_main.gi.cvar ("bob_roll", "0.002", 0)

	# gun position / sv_ movement vars
	g_main.gun_x = g_main.gi.cvar ("gun_x", "0", 0)
	g_main.gun_y = g_main.gi.cvar ("gun_y", "0", 0)
	g_main.gun_z = g_main.gi.cvar ("gun_z", "0", 0)
	g_main.sv_rollspeed = g_main.gi.cvar ("sv_rollspeed", "200", 0)
	g_main.sv_rollangle = g_main.gi.cvar ("sv_rollangle", "2", 0)
	g_main.sv_maxvelocity = g_main.gi.cvar ("sv_maxvelocity", "2000", 0)
	g_main.sv_gravity = g_main.gi.cvar ("sv_gravity", "800", 0)
	g_main.dedicated = g_main.gi.cvar ("dedicated", "0", q_shared.CVAR_NOSET)
	g_main.sv_cheats = g_main.gi.cvar ("cheats", "0", q_shared.CVAR_SERVERINFO | q_shared.CVAR_LATCH)

	# flood control
	g_main.flood_msgs = g_main.gi.cvar ("flood_msgs", "4", 0)
	g_main.flood_persecond = g_main.gi.cvar ("flood_persecond", "4", 0)
	g_main.flood_waitdelay = g_main.gi.cvar ("flood_waitdelay", "10", 0)

	# dm map list
	g_main.sv_maplist = g_main.gi.cvar ("sv_maplist", "", 0)

	# items
	g_items.InitItems ()

	g_main.game.helpmessage1 = ""
	g_main.game.helpmessage2 = ""

	# initialize all entities for this game
	g_main.game.maxentities = int(g_main.maxentities.value)
	g_main.g_edicts = [] # g_main.gi.TagMalloc (game.maxentities * sizeof(g_edicts[0]), TAG_GAME)
	for i in range(g_main.game.maxentities):
		g_main.g_edicts.append(game.edict_t())
	g_main.g_edicts[0].inuse = True
	g_main.glob.edicts = g_main.g_edicts
	g_main.glob.max_edicts = g_main.game.maxentities

	# initialize all clients for this game
	g_main.game.maxclients = int(g_main.maxclients.value)
	g_main.game.clients = [game.gclient_s() for _ in range(g_main.game.maxclients)]
	g_main.glob.num_edicts = g_main.game.maxclients + 1

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
	return struct.pack(_FMT_PMOVE,
		pm.pm_type,
		*pm.origin.tolist(),
		pm.pm_flags, pm.pm_time, pm.gravity,
		*pm.delta_angles.tolist())

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
		strdata = time.strftime("%M %h %d %I:%P", time.localtime())[:15]

	g_main.game.autosaved = autosave

	f = open(filename, "wb")
	f.write(strdata.ljust(16, b"\0"))
	f.write(_pack_game(g_main.game))
	for i in range(int(g_main.game.maxclients)):
		f.write(_pack_client(g_main.game.clients[i]))
	f.close()

#
# Save/restore of level state (level.sav) and loadgame are not
# ported yet -- they need the full edict_t field-table relocation
# (WriteEdict/ReadEdict + the fields[] tables).  These stubs keep the
# GetGameApi surface complete so the map-load path (which only calls
# WriteGame) does not crash.
#
def ReadGame (filename): #char *
	g_main.gi.dprintf ("ReadGame: not yet ported\n")

def WriteLevel (filename): #char *
	g_main.gi.dprintf ("WriteLevel: not yet ported\n")

def ReadLevel (filename): #char *
	g_main.gi.dprintf ("ReadLevel: not yet ported\n")
"""

//=========================================================

void WriteField1 (FILE *f, field_t *field, byte *base)
{
	void		*p;
	int			len;
	int			index;

	if (field->flags & FFL_SPAWNTEMP)
		return;

	p = (void *)(base + field->ofs);
	switch (field->type)
	{
	case F_INT:
	case F_FLOAT:
	case F_ANGLEHACK:
	case F_VECTOR:
	case F_IGNORE:
		break;

	case F_LSTRING:
	case F_GSTRING:
		if ( *(char **)p )
			len = strlen(*(char **)p) + 1;
		else
			len = 0;
		*(int *)p = len;
		break;
	case F_EDICT:
		if ( *(edict_t **)p == NULL)
			index = -1;
		else
			index = *(edict_t **)p - g_edicts;
		*(int *)p = index;
		break;
	case F_CLIENT:
		if ( *(gclient_t **)p == NULL)
			index = -1;
		else
			index = *(gclient_t **)p - game.clients;
		*(int *)p = index;
		break;
	case F_ITEM:
		if ( *(edict_t **)p == NULL)
			index = -1;
		else
			index = *(gitem_t **)p - itemlist;
		*(int *)p = index;
		break;

	//relative to code segment
	case F_FUNCTION:
		if (*(byte **)p == NULL)
			index = 0;
		else
			index = *(byte **)p - ((byte *)InitGame);
		*(int *)p = index;
		break;

	//relative to data segment
	case F_MMOVE:
		if (*(byte **)p == NULL)
			index = 0;
		else
			index = *(byte **)p - (byte *)&mmove_reloc;
		*(int *)p = index;
		break;

	default:
		g_main.gi.error ("WriteEdict: unknown field type");
	}
}


void WriteField2 (FILE *f, field_t *field, byte *base)
{
	int			len;
	void		*p;

	if (field->flags & FFL_SPAWNTEMP)
		return;

	p = (void *)(base + field->ofs);
	switch (field->type)
	{
	case F_LSTRING:
		if ( *(char **)p )
		{
			len = strlen(*(char **)p) + 1;
			fwrite (*(char **)p, len, 1, f);
		}
		break;
	}
}

void ReadField (FILE *f, field_t *field, byte *base)
{
	void		*p;
	int			len;
	int			index;

	if (field->flags & FFL_SPAWNTEMP)
		return;

	p = (void *)(base + field->ofs);
	switch (field->type)
	{
	case F_INT:
	case F_FLOAT:
	case F_ANGLEHACK:
	case F_VECTOR:
	case F_IGNORE:
		break;

	case F_LSTRING:
		len = *(int *)p;
		if (!len)
			*(char **)p = NULL;
		else
		{
			*(char **)p = g_main.gi.TagMalloc (len, TAG_LEVEL);
			fread (*(char **)p, len, 1, f);
		}
		break;
	case F_EDICT:
		index = *(int *)p;
		if ( index == -1 )
			*(edict_t **)p = NULL;
		else
			*(edict_t **)p = &g_edicts[index];
		break;
	case F_CLIENT:
		index = *(int *)p;
		if ( index == -1 )
			*(gclient_t **)p = NULL;
		else
			*(gclient_t **)p = &game.clients[index];
		break;
	case F_ITEM:
		index = *(int *)p;
		if ( index == -1 )
			*(gitem_t **)p = NULL;
		else
			*(gitem_t **)p = &itemlist[index];
		break;

	//relative to code segment
	case F_FUNCTION:
		index = *(int *)p;
		if ( index == 0 )
			*(byte **)p = NULL;
		else
			*(byte **)p = ((byte *)InitGame) + index;
		break;

	//relative to data segment
	case F_MMOVE:
		index = *(int *)p;
		if (index == 0)
			*(byte **)p = NULL;
		else
			*(byte **)p = (byte *)&mmove_reloc + index;
		break;

	default:
		g_main.gi.error ("ReadEdict: unknown field type");
	}
}

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
/*
============
WriteGame

This will be called whenever the game goes to a new level,
and when the user explicitly saves the game.

Game information include cross level data, like multi level
triggers, help computer info, and all client states.

A single player death will automatically restore from the
last save position.
============
*/
void WriteGame (char *filename, qboolean autosave)
{
	FILE	*f;
	int		i;
	char	str[16];

	if (!autosave)
		SaveClientData ();

	f = fopen (filename, "wb");
	if (!f)
		g_main.gi.error ("Couldn't open %s", filename);

	memset (str, 0, sizeof(str));
	strcpy (str, __DATE__);
	fwrite (str, sizeof(str), 1, f);

	game.autosaved = autosave;
	fwrite (&game, sizeof(game), 1, f);
	game.autosaved = false;

	for (i=0 ; i<game.maxclients ; i++)
		WriteClient (f, &game.clients[i]);

	fclose (f);
}

void ReadGame (char *filename)
{
	FILE	*f;
	int		i;
	char	str[16];

	g_main.gi.FreeTags (TAG_GAME);

	f = fopen (filename, "rb");
	if (!f)
		g_main.gi.error ("Couldn't open %s", filename);

	fread (str, sizeof(str), 1, f);
	if (strcmp (str, __DATE__))
	{
		fclose (f);
		g_main.gi.error ("Savegame from an older version.\n");
	}

	g_edicts =  g_main.gi.TagMalloc (game.maxentities * sizeof(g_edicts[0]), TAG_GAME);
	globals.edicts = g_edicts;

	fread (&game, sizeof(game), 1, f);
	game.clients = g_main.gi.TagMalloc (game.maxclients * sizeof(game.clients[0]), TAG_GAME);
	for (i=0 ; i<game.maxclients ; i++)
		ReadClient (f, &game.clients[i]);

	fclose (f);
}

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
"""
/*
=================
WriteLevel

=================
*/
void WriteLevel (char *filename)
{
	int		i;
	edict_t	*ent;
	FILE	*f;
	void	*base;

	f = fopen (filename, "wb");
	if (!f)
		g_main.gi.error ("Couldn't open %s", filename);

	// write out edict size for checking
	i = sizeof(edict_t);
	fwrite (&i, sizeof(i), 1, f);

	// write out a function pointer for checking
	base = (void *)InitGame;
	fwrite (&base, sizeof(base), 1, f);

	// write out level_locals_t
	WriteLevelLocals (f);

	// write out all the entities
	for (i=0 ; i<globals.num_edicts ; i++)
	{
		ent = &g_edicts[i];
		if (!ent->inuse)
			continue;
		fwrite (&i, sizeof(i), 1, f);
		WriteEdict (f, ent);
	}
	i = -1;
	fwrite (&i, sizeof(i), 1, f);

	fclose (f);
}
"""
"""
/*
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
*/
void ReadLevel (char *filename)
{
	int		entnum;
	FILE	*f;
	int		i;
	void	*base;
	edict_t	*ent;

	f = fopen (filename, "rb");
	if (!f)
		g_main.gi.error ("Couldn't open %s", filename);

	// free any dynamic memory allocated by loading the level
	// base state
	g_main.gi.FreeTags (TAG_LEVEL);

	// wipe all the entities
	memset (g_edicts, 0, game.maxentities*sizeof(g_edicts[0]));
	globals.num_edicts = maxclients->value+1;

	// check edict size
	fread (&i, sizeof(i), 1, f);
	if (i != sizeof(edict_t))
	{
		fclose (f);
		g_main.gi.error ("ReadLevel: mismatched edict size");
	}

	// check function pointer base address
	fread (&base, sizeof(base), 1, f);
#ifdef _WIN32
	if (base != (void *)InitGame)
	{
		fclose (f);
		g_main.gi.error ("ReadLevel: function pointers have moved");
	}
#else
	g_main.gi.dprintf("Function offsets %d\n", ((byte *)base) - ((byte *)InitGame));
#endif

	// load the level locals
	ReadLevelLocals (f);

	// load all the entities
	while (1)
	{
		if (fread (&entnum, sizeof(entnum), 1, f) != 1)
		{
			fclose (f);
			g_main.gi.error ("ReadLevel: failed to read entnum");
		}
		if (entnum == -1)
			break;
		if (entnum >= globals.num_edicts)
			globals.num_edicts = entnum+1;

		ent = &g_edicts[entnum];
		ReadEdict (f, ent);

		// let the server rebuild world links for this ent
		memset (&ent->area, 0, sizeof(ent->area));
		g_main.gi.linkentity (ent);
	}

	fclose (f);

	// mark all clients as unconnected
	for (i=0 ; i<maxclients->value ; i++)
	{
		ent = &g_edicts[i+1];
		ent->client = game.clients + i;
		ent->client->pers.connected = false;
	}

	// do any load time things at this point
	for (i=0 ; i<globals.num_edicts ; i++)
	{
		ent = &g_edicts[i];

		if (!ent->inuse)
			continue;

		// fire any cross-level triggers
		if (ent->classname)
			if (strcmp(ent->classname, "target_crosslevel_target") == 0)
				ent->nextthink = level.time + ent->delay;
	}
}
"""
