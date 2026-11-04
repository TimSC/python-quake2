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
from game import game as _gamemod, g_save, p_client
from game import g_local
from game import p_view, p_hud, g_utils, g_ai, g_monster, g_phys, q_shared
from game import g_spawn, g_cmds, g_svcmds
from game.q_shared import Q_stricmp, DF_SAME_LEVEL, PRINT_HIGH
"""

#include "g_local.h"

game_locals_t	game;
level_locals_t	level;
"""
gi = _gamemod.game_import_t()
glob = _gamemod.game_export_t() # Called global in the original C code
"""
spawn_temp_t	st;

int	sm_meat_index;
int	snd_fry;
int meansOfDeath;
"""
g_edicts = None #edict_t *
game = g_local.game_locals_t()
level = g_local.level_locals_t()
st = g_local.spawn_temp_t()

sm_meat_index = 0
snd_fry = 0
meansOfDeath = 0


# cvars (cvar_t *), assigned in g_save.InitGame via gi.cvar(...)
deathmatch = None #cvar_t	*
coop = None #cvar_t	*
dmflags = None # cvar_t	*
skill = None # cvar_t	*
fraglimit = None # cvar_t	*
timelimit = None # cvar_t	*
password = None # cvar_t	*
spectator_password = None # cvar_t	*
needpass = None # cvar_t	*
maxclients = None # cvar_t	*
maxspectators = None # cvar_t	*
maxentities = None # cvar_t	*
g_select_empty = None # cvar_t	*
dedicated = None # cvar_t	*

filterban = None # cvar_t	*

sv_maxvelocity = None # cvar_t	*
sv_gravity = None # cvar_t	*

sv_rollspeed = None # cvar_t	*
sv_rollangle = None # cvar_t	*
gun_x = None # cvar_t	*
gun_y = None # cvar_t	*
gun_z = None # cvar_t	*

run_pitch = None # cvar_t	*
run_roll = None # cvar_t	*
bob_up = None # cvar_t	*
bob_pitch = None # cvar_t	*
bob_roll = None # cvar_t	*

sv_cheats = None # cvar_t	*

flood_msgs = None # cvar_t	*
flood_persecond = None # cvar_t	*
flood_waitdelay = None # cvar_t	*

sv_maplist = None # cvar_t	*

"""
void SpawnEntities (char *mapname, char *entities, char *spawnpoint);
void ClientThink (edict_t *ent, usercmd_t *cmd);
qboolean ClientConnect (edict_t *ent, char *userinfo);
void ClientUserinfoChanged (edict_t *ent, char *userinfo);
void ClientDisconnect (edict_t *ent);
void ClientBegin (edict_t *ent);
void ClientCommand (edict_t *ent);
void RunEntity (edict_t *ent);
void WriteGame (char *filename, qboolean autosave);
void ReadGame (char *filename);
void WriteLevel (char *filename);
void ReadLevel (char *filename);
void InitGame (void);
void G_RunFrame (void);


//===================================================================

"""
def ShutdownGame ():
	gi.dprintf ("==== ShutdownGame ====\n")
	gi.FreeTags (g_local.TAG_LEVEL)
	gi.FreeTags (g_local.TAG_GAME)
	"""
	gi.dprintf ("==== ShutdownGame ====\n")

	gi.FreeTags (TAG_LEVEL)
	gi.FreeTags (TAG_GAME)
	"""


"""
=================
GetGameAPI

Returns a pointer to the structure with all entry points
and global variables
=================
"""
def GetGameAPI (gimport): #game_import_t * (returns game_export_t *)

	global gi, glob

	gi = gimport

	glob.apiversion = _gamemod.GAME_API_VERSION

	glob.Init = g_save.InitGame
	glob.Shutdown = ShutdownGame
	glob.SpawnEntities = g_spawn.SpawnEntities
	glob.WriteGame = g_save.WriteGame
	glob.ReadGame = g_save.ReadGame
	glob.WriteLevel = g_save.WriteLevel
	glob.ReadLevel = g_save.ReadLevel
	glob.ClientThink = p_client.ClientThink
	glob.ClientConnect = p_client.ClientConnect
	glob.ClientUserinfoChanged = p_client.ClientUserinfoChanged
	glob.ClientDisconnect = p_client.ClientDisconnect
	glob.ClientBegin = p_client.ClientBegin
	glob.ClientCommand = g_cmds.ClientCommand
	glob.RunFrame = G_RunFrame
	glob.ServerCommand = g_svcmds.ServerCommand

	#glob.edict_size = sizeof(edict_t)

	return glob

"""
#ifndef GAME_HARD_LINKED
// this is only here so the functions in q_shared.c and q_shwin.c can link
void Sys_Error (char *error, ...)
{
	va_list		argptr;
	char		text[1024];

	va_start (argptr, error);
	vsprintf (text, error, argptr);
	va_end (argptr);

	gi.error (ERR_FATAL, "%s", text);
}

void Com_Printf (char *msg, ...)
{
	va_list		argptr;
	char		text[1024];

	va_start (argptr, msg);
	vsprintf (text, msg, argptr);
	va_end (argptr);

	gi.dprintf ("%s", text);
}

#endif

//======================================================================
"""
def ClientEndServerFrames ():
	i = 0
	ent = None

	# calc the player views now that all pushing
	# and damage has been added
	for i in range(int(maxclients.value)):
		ent = g_edicts[1 + i]
		if not ent.inuse or not ent.client:
			continue
		p_view.ClientEndServerFrame (ent)
	"""
/*
=================
ClientEndServerFrames
=================
*/
void ClientEndServerFrames (void)
{
	int		i;
	edict_t	*ent;

	// calc the player views now that all pushing
	// and damage has been added
	for (i=0 ; i<maxclients->value ; i++)
	{
		ent = g_edicts + 1 + i;
		if (!ent->inuse || !ent->client)
			continue;
		ClientEndServerFrame (ent);
	}

}
"""
def CreateTargetChangeLevel (map):
	ent = g_utils.G_Spawn ()
	ent.classname = "target_changelevel"
	level.nextmap = map
	ent.map = level.nextmap
	return ent
	"""
/*
=================
CreateTargetChangeLevel

Returns the created target changelevel
=================
*/
edict_t *CreateTargetChangeLevel(char *map)
{
	edict_t *ent;

	ent = G_Spawn ();
	ent->classname = "target_changelevel";
	Com_sprintf(level.nextmap, sizeof(level.nextmap), "%s", map);
	ent->map = level.nextmap;
	return ent;
}
"""
def EndDMLevel ():
	ent = None
	f = None
	tokens = []
	i = 0

	# stay on same level flag
	if int(dmflags.value) & DF_SAME_LEVEL:
		p_hud.BeginIntermission (CreateTargetChangeLevel (level.mapname))
		return

	# see if it's in the map list
	if sv_maplist.string:
		tokens = sv_maplist.string.replace(',', ' ').split()
		f = None
		i = 0
		while i < len(tokens):
			t = tokens[i]
			if Q_stricmp(t, level.mapname) == 0:
				# it's in the list, go to the next one
				i += 1
				if i >= len(tokens):	# end of list, go to first one
					if f is None:	# there isn't a first one, same level
						p_hud.BeginIntermission (CreateTargetChangeLevel (level.mapname))
					else:
						p_hud.BeginIntermission (CreateTargetChangeLevel (f))
				else:
					p_hud.BeginIntermission (CreateTargetChangeLevel (tokens[i]))
				return
			if f is None:
				f = t
			i += 1

	if level.nextmap:	# go to a specific map
		p_hud.BeginIntermission (CreateTargetChangeLevel (level.nextmap))
	else:	# search for a changelevel
		ent = g_utils.G_Find (None, "classname", "target_changelevel")
		if not ent:
			#	# the map designer didn't include a changelevel,
			#	# so create a fake ent that goes back to the same level
			p_hud.BeginIntermission (CreateTargetChangeLevel (level.mapname))
			return
		p_hud.BeginIntermission (ent)
	"""
/*
=================
EndDMLevel

The timelimit or fraglimit has been exceeded
=================
*/
void EndDMLevel (void)
{
	edict_t		*ent;
	char *s, *t, *f;
	static const char *seps = " ,\n\r";

	// stay on same level flag
	if ((int)dmflags->value & DF_SAME_LEVEL)
	{
		BeginIntermission (CreateTargetChangeLevel (level.mapname) );
		return;
	}

	// see if it's in the map list
	if (*sv_maplist->string) {
		s = strdup(sv_maplist->string);
		f = NULL;
		t = strtok(s, seps);
		while (t != NULL) {
			if (Q_stricmp(t, level.mapname) == 0) {
				// it's in the list, go to the next one
				t = strtok(NULL, seps);
				if (t == NULL) { // end of list, go to first one
					if (f == NULL) // there isn't a first one, same level
						BeginIntermission (CreateTargetChangeLevel (level.mapname) );
					else
						BeginIntermission (CreateTargetChangeLevel (f) );
				} else
					BeginIntermission (CreateTargetChangeLevel (t) );
				free(s);
				return;
			}
			if (!f)
				f = t;
			t = strtok(NULL, seps);
		}
		free(s);
	}

	if (level.nextmap[0]) // go to a specific map
		BeginIntermission (CreateTargetChangeLevel (level.nextmap) );
	else {	// search for a changelevel
		ent = G_Find (NULL, FOFS(classname), "target_changelevel");
		if (!ent)
		{	// the map designer didn't include a changelevel,
			// so create a fake ent that goes back to the same level
			BeginIntermission (CreateTargetChangeLevel (level.mapname) );
			return;
		}
		BeginIntermission (ent);
	}
}
"""
def CheckNeedPass ():
	need = 0

	# if password or spectator_password has changed, update needpass
	# as needed
	if password.modified or spectator_password.modified:
		password.modified = spectator_password.modified = False

		need = 0

		if password.string and Q_stricmp(password.string, "none") != 0:
			need |= 1
		if spectator_password.string and Q_stricmp(spectator_password.string, "none") != 0:
			need |= 2

		gi.cvar_set("needpass", "%d" % need)
	"""
/*
=================
CheckNeedPass
=================
*/
void CheckNeedPass (void)
{
	int need;

	// if password or spectator_password has changed, update needpass
	// as needed
	if (password->modified || spectator_password->modified) 
	{
		password->modified = spectator_password->modified = false;

		need = 0;

		if (*password->string && Q_stricmp(password->string, "none"))
			need |= 1;
		if (*spectator_password->string && Q_stricmp(spectator_password->string, "none"))
			need |= 2;

		gi.cvar_set("needpass", va("%d", need));
	}
}
"""
def CheckDMRules ():
	i = 0
	cl = None

	if level.intermissiontime:
		return

	if not deathmatch.value:
		return

	if timelimit.value:
		if level.time >= timelimit.value*60:
			gi.bprintf (PRINT_HIGH, "Timelimit hit.\n")
			EndDMLevel ()
			return

	if fraglimit.value:
		for i in range(int(maxclients.value)):
			cl = game.clients[i]
			if not g_edicts[i+1].inuse:
				continue

			if cl.resp.score >= fraglimit.value:
				gi.bprintf (PRINT_HIGH, "Fraglimit hit.\n")
				EndDMLevel ()
				return
	"""
/*
=================
CheckDMRules
=================
*/
void CheckDMRules (void)
{
	int			i;
	gclient_t	*cl;

	if (level.intermissiontime)
		return;

	if (!deathmatch->value)
		return;

	if (timelimit->value)
	{
		if (level.time >= timelimit->value*60)
		{
			gi.bprintf (PRINT_HIGH, "Timelimit hit.\n");
			EndDMLevel ();
			return;
		}
	}

	if (fraglimit->value)
	{
		for (i=0 ; i<maxclients->value ; i++)
		{
			cl = game.clients + i;
			if (!g_edicts[i+1].inuse)
				continue;

			if (cl->resp.score >= fraglimit->value)
			{
				gi.bprintf (PRINT_HIGH, "Fraglimit hit.\n");
				EndDMLevel ();
				return;
			}
		}
	}
}
"""
def ExitLevel ():
	i = 0
	ent = None
	command = ""

	command = "gamemap \"%s\"\n" % level.changemap
	gi.AddCommandString (command)
	level.changemap = None
	level.exitintermission = 0
	level.intermissiontime = 0
	ClientEndServerFrames ()

	# clear some things before going to next level
	for i in range(int(maxclients.value)):
		ent = g_edicts[1 + i]
		if not ent.inuse:
			continue
		if ent.health > ent.client.pers.max_health:
			ent.health = ent.client.pers.max_health
	"""
/*
=============
ExitLevel
=============
*/
void ExitLevel (void)
{
	int		i;
	edict_t	*ent;
	char	command [256];

	Com_sprintf (command, sizeof(command), "gamemap \"%s\"\n", level.changemap);
	gi.AddCommandString (command);
	level.changemap = NULL;
	level.exitintermission = 0;
	level.intermissiontime = 0;
	ClientEndServerFrames ();

	// clear some things before going to next level
	for (i=0 ; i<maxclients->value ; i++)
	{
		ent = g_edicts + 1 + i;
		if (!ent->inuse)
			continue;
		if (ent->health > ent->client->pers.max_health)
			ent->health = ent->client->pers.max_health;
	}

}
"""
"""
/*
================
G_RunFrame

Advances the world by 0.1 seconds
================
"""
def G_RunFrame ():
	i = 0
	ent = None

	level.framenum += 1
	level.time = level.framenum*g_local.FRAMETIME

	# choose a client for monsters to target this frame
	g_ai.AI_SetSightClient ()

	# exit intermissions
	if level.exitintermission:
		ExitLevel ()
		return

	#
	# treat each object in turn
	# even the world gets a chance to think
	#
	for i in range(glob.num_edicts):
		ent = g_edicts[i]
		if not ent.inuse:
			continue

		level.current_entity = ent

		q_shared.VectorCopy (ent.s.origin, ent.s.old_origin)

		# if the ground entity moved, make sure we are still on it
		if ent.groundentity and ent.groundentity.linkcount != ent.groundentity_linkcount:
			ent.groundentity = None
			if not (ent.flags & (g_local.FL_SWIM|g_local.FL_FLY)) and (ent.svflags & _gamemod.SVF_MONSTER):
				g_monster.M_CheckGround (ent)

		if i > 0 and i <= int(maxclients.value):
			p_client.ClientBeginServerFrame (ent)
			continue

		g_phys.G_RunEntity (ent)

	# see if it is time to end a deathmatch
	CheckDMRules ()

	# see if needpass needs updated
	CheckNeedPass ()

	# build the playerstate_t structures for all players
	ClientEndServerFrames ()
	"""
	int		i;
	edict_t	*ent;

	level.framenum++;
	level.time = level.framenum*FRAMETIME;

	// choose a client for monsters to target this frame
	AI_SetSightClient ();

	// exit intermissions

	if (level.exitintermission)
	{
		ExitLevel ();
		return;
	}

	//
	// treat each object in turn
	// even the world gets a chance to think
	//
	ent = &g_edicts[0];
	for (i=0 ; i<globals.num_edicts ; i++, ent++)
	{
		if (!ent->inuse)
			continue;

		level.current_entity = ent;

		q_shared.VectorCopy (ent->s.origin, ent->s.old_origin);

		// if the ground entity moved, make sure we are still on it
		if ((ent->groundentity) && (ent->groundentity->linkcount != ent->groundentity_linkcount))
		{
			ent->groundentity = NULL;
			if ( !(ent->flags & (FL_SWIM|FL_FLY)) && (ent->svflags & SVF_MONSTER) )
			{
				M_CheckGround (ent);
			}
		}

		if (i > 0 && i <= maxclients->value)
		{
			ClientBeginServerFrame (ent);
			continue;
		}

		G_RunEntity (ent);
	}

	// see if it is time to end a deathmatch
	CheckDMRules ();

	// see if needpass needs updated
	CheckNeedPass ();

	// build the playerstate_t structures for all players
	ClientEndServerFrames ();
}
"""
