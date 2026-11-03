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
from game import game
from linux import sys_linux
from qcommon import cvar
"""
// sv_game.c -- interface to the game dll

#include "server.h"
"""
ge = None #game.game_export_t()
"""

/*
===============
PF_Unicast

Sends the contents of the mutlicast buffer to a single client
===============
*/
void PF_Unicast (edict_t *ent, qboolean reliable)
{
	int		p;
	client_t	*client;

	if (!ent)
		return;

	p = NUM_FOR_EDICT(ent);
	if (p < 1 || p > maxclients->value)
		return;

	client = svs.clients + (p-1);

	if (reliable)
		SZ_Write (&client->netchan.message, sv.multicast.data, sv.multicast.cursize);
	else
		SZ_Write (&client->datagram, sv.multicast.data, sv.multicast.cursize);

	SZ_Clear (&sv.multicast);
}


/*
===============
PF_dprintf

Debug print to server console
===============
*/
void PF_dprintf (char *fmt, ...)
{
	char		msg[1024];
	va_list		argptr;
	
	va_start (argptr,fmt);
	vsprintf (msg, fmt, argptr);
	va_end (argptr);

	Com_Printf ("%s", msg);
}


/*
===============
PF_cprintf

Print to a single client
===============
*/
void PF_cprintf (edict_t *ent, int level, char *fmt, ...)
{
	char		msg[1024];
	va_list		argptr;
	int			n;

	if (ent)
	{
		n = NUM_FOR_EDICT(ent);
		if (n < 1 || n > maxclients->value)
			Com_Error (qcommon.ERR_DROP, "cprintf to a non-client");
	}

	va_start (argptr,fmt);
	vsprintf (msg, fmt, argptr);
	va_end (argptr);

	if (ent)
		SV_ClientPrintf (svs.clients+(n-1), level, "%s", msg);
	else
		Com_Printf ("%s", msg);
}


/*
===============
PF_centerprintf

centerprint to a single client
===============
*/
void PF_centerprintf (edict_t *ent, char *fmt, ...)
{
	char		msg[1024];
	va_list		argptr;
	int			n;
	
	n = NUM_FOR_EDICT(ent);
	if (n < 1 || n > maxclients->value)
		return;	// Com_Error (qcommon.ERR_DROP, "centerprintf to a non-client");

	va_start (argptr,fmt);
	vsprintf (msg, fmt, argptr);
	va_end (argptr);

	MSG_WriteByte (&sv.multicast,svc_centerprint);
	MSG_WriteString (&sv.multicast,msg);
	PF_Unicast (ent, true);
}


/*
===============
PF_error

Abort the server with a game error
===============
*/
void PF_error (char *fmt, ...)
{
	char		msg[1024];
	va_list		argptr;
	
	va_start (argptr,fmt);
	vsprintf (msg, fmt, argptr);
	va_end (argptr);

	Com_Error (qcommon.ERR_DROP, "Game Error: %s", msg);
}


/*
=================
PF_setmodel

Also sets mins and maxs for inline bmodels
=================
*/
void PF_setmodel (edict_t *ent, char *name)
{
	int		i;
	cmodel_t	*mod;

	if (!name)
		Com_Error (qcommon.ERR_DROP, "PF_setmodel: NULL");

	i = SV_ModelIndex (name);
		
//	ent->model = name;
	ent->s.modelindex = i;

// if it is an inline model, get the size information for it
	if (name[0] == '*')
	{
		mod = CM_InlineModel (name);
		q_shared.VectorCopy (mod->mins, ent->mins);
		q_shared.VectorCopy (mod->maxs, ent->maxs);
		SV_LinkEdict (ent);
	}

}

/*
===============
PF_Configstring

===============
*/
void PF_Configstring (int index, char *val)
{
	if (index < 0 || index >= MAX_CONFIGSTRINGS)
		Com_Error (qcommon.ERR_DROP, "configstring: bad index %i\n", index);

	if (!val)
		val = "";

	// change the string in sv
	strcpy (sv.configstrings[index], val);

	
	if (sv.state != ss_loading)
	{	// send the update to everyone
		SZ_Clear (&sv.multicast);
		MSG_WriteChar (&sv.multicast, svc_configstring);
		MSG_WriteShort (&sv.multicast, index);
		MSG_WriteString (&sv.multicast, val);

		SV_Multicast (vec3_origin, MULTICAST_ALL_R);
	}
}



void PF_WriteChar (int c) {MSG_WriteChar (&sv.multicast, c);}
void PF_WriteByte (int c) {MSG_WriteByte (&sv.multicast, c);}
void PF_WriteShort (int c) {MSG_WriteShort (&sv.multicast, c);}
void PF_WriteLong (int c) {MSG_WriteLong (&sv.multicast, c);}
void PF_WriteFloat (float f) {MSG_WriteFloat (&sv.multicast, f);}
void PF_WriteString (char *s) {MSG_WriteString (&sv.multicast, s);}
void PF_WritePos (vec3_t pos) {MSG_WritePos (&sv.multicast, pos);}
void PF_WriteDir (vec3_t dir) {MSG_WriteDir (&sv.multicast, dir);}
void PF_WriteAngle (float f) {MSG_WriteAngle (&sv.multicast, f);}


/*
=================
PF_inPVS

Also checks portalareas so that doors block sight
=================
*/
qboolean PF_inPVS (vec3_t p1, vec3_t p2)
{
	int		leafnum;
	int		cluster;
	int		area1, area2;
	byte	*mask;

	leafnum = CM_PointLeafnum (p1);
	cluster = CM_LeafCluster (leafnum);
	area1 = CM_LeafArea (leafnum);
	mask = CM_ClusterPVS (cluster);

	leafnum = CM_PointLeafnum (p2);
	cluster = CM_LeafCluster (leafnum);
	area2 = CM_LeafArea (leafnum);
	if ( mask && (!(mask[cluster>>3] & (1<<(cluster&7)) ) ) )
		return false;
	if (!CM_AreasConnected (area1, area2))
		return false;		// a door blocks sight
	return true;
}


/*
=================
PF_inPHS

Also checks portalareas so that doors block sound
=================
*/
qboolean PF_inPHS (vec3_t p1, vec3_t p2)
{
	int		leafnum;
	int		cluster;
	int		area1, area2;
	byte	*mask;

	leafnum = CM_PointLeafnum (p1);
	cluster = CM_LeafCluster (leafnum);
	area1 = CM_LeafArea (leafnum);
	mask = CM_ClusterPHS (cluster);

	leafnum = CM_PointLeafnum (p2);
	cluster = CM_LeafCluster (leafnum);
	area2 = CM_LeafArea (leafnum);
	if ( mask && (!(mask[cluster>>3] & (1<<(cluster&7)) ) ) )
		return false;		// more than one bounce away
	if (!CM_AreasConnected (area1, area2))
		return false;		// a door blocks hearing

	return true;
}

void PF_StartSound (edict_t *entity, int channel, int sound_num, float volume,
    float attenuation, float timeofs)
{
	if (!entity)
		return;
	SV_StartSound (NULL, entity, channel, sound_num, volume, attenuation, timeofs);
}

//==============================================

/*
===============
SV_ShutdownGameProgs

Called when either the entire server is being killed, or
it is changing to a different game directory.
===============
"""
def SV_ShutdownGameProgs ():

	global ge

	if ge is None:
		return
	ge.Shutdown ()
	sys_linux.Sys_UnloadGame ()
	ge = None

"""
/*
===============
SV_InitGameProgs

Init the game subsystem for a new map
===============
*/
void SCR_DebugGraph (float value, int color);
"""
def SV_InitGameProgs ():

	global ge

	gimport = game.game_import_t()

	# unload anything we have now
	if ge is not None:
		SV_ShutdownGameProgs ()
	"""
	// load a new game dll
	gimport.multicast = SV_Multicast;
	gimport.unicast = PF_Unicast;
	gimport.bprintf = SV_BroadcastPrintf;
	gimport.dprintf = PF_dprintf;
	gimport.cprintf = PF_cprintf;
	gimport.centerprintf = PF_centerprintf;
	gimport.error = PF_error;

	gimport.linkentity = SV_LinkEdict;
	gimport.unlinkentity = SV_UnlinkEdict;
	gimport.BoxEdicts = SV_AreaEdicts;
	gimport.trace = SV_Trace;
	gimport.pointcontents = SV_PointContents;
	gimport.setmodel = PF_setmodel;
	gimport.inPVS = PF_inPVS;
	gimport.inPHS = PF_inPHS;
	gimport.Pmove = Pmove;

	gimport.modelindex = SV_ModelIndex;
	gimport.soundindex = SV_SoundIndex;
	gimport.imageindex = SV_ImageIndex;

	gimport.configstring = PF_Configstring;
	gimport.sound = PF_StartSound;
	gimport.positioned_sound = SV_StartSound;

	gimport.WriteChar = PF_WriteChar;
	gimport.WriteByte = PF_WriteByte;
	gimport.WriteShort = PF_WriteShort;
	gimport.WriteLong = PF_WriteLong;
	gimport.WriteFloat = PF_WriteFloat;
	gimport.WriteString = PF_WriteString;
	gimport.WritePosition = PF_WritePos;
	gimport.WriteDir = PF_WriteDir;
	gimport.WriteAngle = PF_WriteAngle;

	gimport.TagMalloc = Z_TagMalloc;
	gimport.TagFree = Z_Free;
	gimport.FreeTags = Z_FreeTags;

	"""
	gimport.cvar = cvar.Cvar_Get
	"""
	gimport.cvar_set = Cvar_Set;
	gimport.cvar_forceset = Cvar_ForceSet;

	gimport.argc = Cmd_Argc;
	gimport.argv = Cmd_Argv;
	gimport.args = Cmd_Args;
	gimport.AddCommandString = Cbuf_AddText;

	gimport.DebugGraph = SCR_DebugGraph;
	gimport.SetAreaPortalState = CM_SetAreaPortalState;
	gimport.AreasConnected = CM_AreasConnected;
	"""
	ge = sys_linux.Sys_GetGameAPI (gimport)

	"""
	if (!ge)
		Com_Error (qcommon.ERR_DROP, "failed to load game DLL");
	"""
	if ge.apiversion != game.GAME_API_VERSION:
		common.Com_Error (qcommon.ERR_DROP, "game is version {:d}, not {:d}".format(ge.apiversion, game.GAME_API_VERSION))

	ge.Init ()

