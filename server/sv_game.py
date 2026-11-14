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

Interface between the server and the game module.

=======================================================================
"""
from __future__ import annotations

pass
from backends.unix import system
pass
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar
from common import movemsg
from common import szone
from common import zone
from common import collision
from common import pmove
from server.header import server as server_h
from server import sv_init
from server import sv_main
from server import sv_send
from server import sv_world
from game.header import game as game_h
from client import cl_screen

"""
#include "header/server.h"
#include <limits.h>
"""

ge = None #game.game_export_t()
"""
/*
===============
PF_Unicast

Sends the contents of the mutlicast buffer to a single client
===============
*/
"""
"""
// sv_game.c -- interface to the game dll

#include "server.h"
"""
def PF_Unicast (ent, reliable): #edict_t *, qboolean

	#int p

	if not ent:
		return

	p = server_h.NUM_FOR_EDICT (ent)
	if p < 1 or p > sv_init.server.maxclients:
		return

	client = sv_init.svs.clients[p-1]

	if reliable:
		szone.SZ_Write (client.netchan.message, bytes(sv_init.sv.multicast.data[:sv_init.sv.multicast.cursize]))
	else:
		szone.SZ_Write (client.datagram, bytes(sv_init.sv.multicast.data[:sv_init.sv.multicast.cursize]))

	szone.SZ_Clear (sv_init.sv.multicast)
"""
/*
===============
PF_dprintf

Debug print to server console
===============
*/
"""
def PF_dprintf (fmt, *args): #char *, ...

	#char msg[1024]

	if args:
		msg = fmt % args
	else:
		msg = fmt

	clientserver.Com_Printf (msg)
"""
/*
===============
PF_cprintf

Print to a single client
===============
*/
"""
def PF_cprintf (ent, level, fmt, *args): #edict_t *, int, char *, ...

	#char msg[1024]
	#int n

	n = 0
	if ent:
		n = server_h.NUM_FOR_EDICT (ent)
		if n < 1 or n > sv_init.server.maxclients:
			clientserver.Com_Error (common_h.ERR_DROP, "cprintf to a non-client")

	if args:
		msg = fmt % args
	else:
		msg = fmt

	if ent:
		sv_send.client_printf (sv_init.svs.clients[n-1], level, msg)
	else:
		clientserver.Com_Printf (msg)
"""
/*
===============
PF_centerprintf

centerprint to a single client
===============
*/
"""
def PF_centerprintf (ent, fmt, *args): #edict_t *, char *, ...

	#char msg[1024]
	#int n

	n = server_h.NUM_FOR_EDICT (ent)
	if n < 1 or n > sv_init.server.maxclients:
		return	# Com_Error (qcommon.ERR_DROP, "centerprintf to a non-client")

	if args:
		msg = fmt % args
	else:
		msg = fmt

	movemsg.MSG_WriteByte (sv_init.sv.multicast, common_h.svc_ops_e.svc_centerprint.value)
	movemsg.MSG_WriteString (sv_init.sv.multicast, msg)
	PF_Unicast (ent, True)
"""
/*
===============
PF_error

Abort the server with a game error
===============
*/
"""
def PF_error (fmt, *args): #char *, ...

	#char msg[1024]

	if args:
		msg = fmt % args
	else:
		msg = fmt

	clientserver.Com_Error (common_h.ERR_DROP, "Game Error: %s" % msg)
"""
/*
=================
PF_setmodel

Also sets mins and maxs for inline bmodels
=================
*/
"""
def PF_setmodel (ent, name): #edict_t *, char *

	#int i

	if not name:
		clientserver.Com_Error (common_h.ERR_DROP, "PF_setmodel: NULL")

	i = sv_init.SV_ModelIndex (name)

	#ent->model = name;
	ent.s.modelindex = i

	# if it is an inline model, get the size information for it
	if name[0] == '*':
		mod = collision.CM_InlineModel (name)
		shared.VectorCopy (mod.mins, ent.mins)
		shared.VectorCopy (mod.maxs, ent.maxs)
		sv_world.SV_LinkEdict (ent)
"""
/*
===============
PF_Configstring

===============
*/
"""
def PF_Configstring(index: int, val: str): #int, const char *

	"""
	size_t len, space;
	char *cs;
	"""

	if (index < 0) or (index >= shared.MAX_CONFIGSTRINGS):

		clientserver.Com_Printf("%s: bad index %i\n", "PF_Configstring", index)
		return


	if not val:

		val = ""


	length = len(val)

	# statusbar code covers several configstring indices
	if (index >= shared.CS_STATUSBAR) and (index < shared.CS_STATUSBAR_END):

		space = shared.CS_STATUSBAR_SPACE(index)

		if length >= space:

			clientserver.Com_Printf("%s: statusbar code too big: %d > %d\n",
				"PF_Configstring", length, space - 1)
			return


		sv_init.sv.configstrings[index] = val #memcpy(cs, val, len + 1);

	else:

		space = shared.MAX_QPATH #sizeof(sv.configstrings[index]);

		if length >= space:

			clientserver.Com_Printf("%s; value too big: %d > %d\n",
				"PF_Configstring", length, space - 1)
			return


		sv_init.sv.configstrings[index] = val #strcpy(cs, val);


	if sv_init.sv.state != server_h.server_state_t.ss_loading:

		# send the update to everyone
		szone.SZ_Clear(sv_init.sv.multicast)
		movemsg.MSG_WriteChar(sv_init.sv.multicast, common_h.svc_ops_e.svc_configstring.value)
		movemsg.MSG_WriteConfigString(sv_init.sv.multicast, index, val)

		sv_send.multicast(shared_c.vec3_origin, shared.multicast_t.MULTICAST_ALL_R)


def PF_WriteChar (c):
	movemsg.MSG_WriteChar (sv_init.sv.multicast, c)
def PF_WriteByte (c):
	movemsg.MSG_WriteByte (sv_init.sv.multicast, c)
def PF_WriteShort (c):
	movemsg.MSG_WriteShort (sv_init.sv.multicast, c)
def PF_WriteLong (c):
	movemsg.MSG_WriteLong (sv_init.sv.multicast, c)
def PF_WriteFloat (f):
	movemsg.MSG_WriteFloat (sv_init.sv.multicast, f)
def PF_WriteString (s):
	movemsg.MSG_WriteString (sv_init.sv.multicast, s)
def PF_WritePos (pos):
	movemsg.MSG_WritePos (sv_init.sv.multicast, pos)
def PF_WriteDir (dir):
	movemsg.MSG_WriteDir (sv_init.sv.multicast, dir)
def PF_WriteAngle (f):
	movemsg.MSG_WriteAngle (sv_init.sv.multicast, f)
"""
/*
=================
PF_inPVS

Also checks portalareas so that doors block sight
=================
*/
"""
def PF_inPVS (p1, p2): #vec3_t, vec3_t

	#int leafnum, cluster, area1, area2

	leafnum = collision.CM_PointLeafnum (p1)
	cluster = collision.CM_LeafCluster (leafnum)
	area1 = collision.CM_LeafArea (leafnum)
	mask = collision.CM_ClusterPVS (cluster)

	leafnum = collision.CM_PointLeafnum (p2)
	cluster = collision.CM_LeafCluster (leafnum)
	area2 = collision.CM_LeafArea (leafnum)
	if cluster < 0 or (not (mask[cluster>>3] & (1<<(cluster&7)))):
		return False
	if not collision.CM_AreasConnected (area1, area2):
		return False		# a door blocks sight
	return True
"""
/*
=================
PF_inPHS

Also checks portalareas so that doors block sound
=================
*/
"""
def PF_inPHS (p1, p2): #vec3_t, vec3_t

	#int leafnum, cluster, area1, area2

	leafnum = collision.CM_PointLeafnum (p1)
	cluster = collision.CM_LeafCluster (leafnum)
	area1 = collision.CM_LeafArea (leafnum)
	mask = collision.CM_ClusterPHS (cluster)

	leafnum = collision.CM_PointLeafnum (p2)
	cluster = collision.CM_LeafCluster (leafnum)
	area2 = collision.CM_LeafArea (leafnum)
	if cluster < 0 or (not (mask[cluster>>3] & (1<<(cluster&7)))):
		return False		# more than one bounce away
	if not collision.CM_AreasConnected (area1, area2):
		return False		# a door blocks hearing

	return True

def PF_StartSound (entity, channel, sound_num, volume, attenuation, timeofs): #edict_t *, int, int, float, float, float

	if not entity:
		return
	sv_send.start_sound (None, entity, channel, sound_num, volume, attenuation, timeofs)

"""
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
	system.Sys_UnloadGame ()
	ge = None

def GI_TagMalloc(size: int, tag: int): #int, int (returns static void *)

	if size < 0:

		clientserver.Com_Error(shared.ERR_FATAL, "%s: size < 0: %i\n",
			"GI_TagMalloc", size)
		return None


	if (tag > 65535) or (tag < 0): #USHRT_MAX

		clientserver.Com_Printf("%s: tag outside [0, 65535]: %i\n",
			"GI_TagMalloc", tag)

		tag = 0


	return zone.Z_TagMalloc(size, tag)

def GI_FreeTags(tag: int): #int

	if (tag > 65535) or (tag <= 0): #USHRT_MAX

		clientserver.Com_Printf("%s: tag outside [1, 65535]: %i\n",
			"GI_FreeTags", tag)

		return


	zone.Z_FreeTags(tag)

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

	gimport = game_h.game_import_t()

	# unload anything we have now
	if ge is not None:
		SV_ShutdownGameProgs ()

	clientserver.Com_Printf("-------- game initialization -------\n")

	# load a new game dll
	gimport.multicast = sv_send.multicast
	gimport.unicast = PF_Unicast
	gimport.bprintf = sv_send.broadcast_printf
	gimport.dprintf = PF_dprintf
	gimport.cprintf = PF_cprintf
	gimport.centerprintf = PF_centerprintf
	gimport.error = PF_error

	gimport.linkentity = sv_world.SV_LinkEdict
	gimport.unlinkentity = sv_world.SV_UnlinkEdict
	gimport.BoxEdicts = sv_world.SV_AreaEdicts
	gimport.trace = sv_world.SV_Trace
	gimport.pointcontents = sv_world.SV_PointContents
	gimport.setmodel = PF_setmodel
	gimport.inPVS = PF_inPVS
	gimport.inPHS = PF_inPHS
	gimport.Pmove = pmove.Pmove

	gimport.modelindex = sv_init.SV_ModelIndex
	gimport.soundindex = sv_init.SV_SoundIndex
	gimport.imageindex = sv_init.SV_ImageIndex

	gimport.configstring = PF_Configstring
	gimport.sound = PF_StartSound
	gimport.positioned_sound = sv_send.start_sound

	gimport.WriteChar = PF_WriteChar
	gimport.WriteByte = PF_WriteByte
	gimport.WriteShort = PF_WriteShort
	gimport.WriteLong = PF_WriteLong
	gimport.WriteFloat = PF_WriteFloat
	gimport.WriteString = PF_WriteString
	gimport.WritePosition = PF_WritePos
	gimport.WriteDir = PF_WriteDir
	gimport.WriteAngle = PF_WriteAngle

	gimport.TagMalloc = GI_TagMalloc
	gimport.TagFree = zone.Z_Free
	gimport.FreeTags = GI_FreeTags

	gimport.cvar = cvar.Cvar_Get
	gimport.cvar_set = cvar.Cvar_Set
	gimport.cvar_forceset = cvar.Cvar_ForceSet

	gimport.argc = cmdparser.Cmd_Argc
	gimport.argv = cmdparser.Cmd_Argv
	gimport.args = cmdparser.Cmd_Args
	gimport.AddCommandString = cmdparser.Cbuf_AddText

	gimport.DebugGraph = cl_screen.SCR_DebugGraph
	gimport.SetAreaPortalState = collision.CM_SetAreaPortalState
	gimport.AreasConnected = collision.CM_AreasConnected

	ge = system.Sys_GetGameAPI (gimport)

	#if (!ge)
	#	Com_Error (qcommon.ERR_DROP, "failed to load game DLL")

	if ge.apiversion != game_h.GAME_API_VERSION:
		clientserver.Com_Error (common_h.ERR_DROP, "game is version {:d}, not {:d}".format(ge.apiversion, game_h.GAME_API_VERSION))

	ge.Init ()

	clientserver.Com_Printf("------------------------------------\n\n")
