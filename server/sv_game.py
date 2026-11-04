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
from game import game, q_shared
from linux import sys_linux
from qcommon import cvar, common, cmd, qcommon, cmodel, pmove
from server import sv_main, sv_send, sv_ents, sv_world, sv_init
from client import cl_scrn
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
"""
def PF_Unicast (ent, reliable): #edict_t *, qboolean

	#int p

	if not ent:
		return

	p = sv_init.NUM_FOR_EDICT (ent)
	if p < 1 or p > int(sv_main.maxclients.value):
		return

	client = sv_init.svs.clients[p-1]

	if reliable:
		common.SZ_Write (client.netchan.message, bytes(sv_init.sv.multicast.data[:sv_init.sv.multicast.cursize]))
	else:
		common.SZ_Write (client.datagram, bytes(sv_init.sv.multicast.data[:sv_init.sv.multicast.cursize]))

	common.SZ_Clear (sv_init.sv.multicast)
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

	common.Com_Printf ("%s", msg)
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
		n = sv_init.NUM_FOR_EDICT (ent)
		if n < 1 or n > int(sv_main.maxclients.value):
			common.Com_Error (qcommon.ERR_DROP, "cprintf to a non-client")

	if args:
		msg = fmt % args
	else:
		msg = fmt

	if ent:
		sv_send.SV_ClientPrintf (sv_init.svs.clients[n-1], level, msg)
	else:
		common.Com_Printf ("%s", msg)
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

	n = sv_init.NUM_FOR_EDICT (ent)
	if n < 1 or n > int(sv_main.maxclients.value):
		return	# Com_Error (qcommon.ERR_DROP, "centerprintf to a non-client")

	if args:
		msg = fmt % args
	else:
		msg = fmt

	common.MSG_WriteByte (sv_init.sv.multicast, qcommon.svc_ops_e.svc_centerprint.value)
	common.MSG_WriteString (sv_init.sv.multicast, msg)
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

	common.Com_Error (qcommon.ERR_DROP, "Game Error: %s", msg)
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
		common.Com_Error (qcommon.ERR_DROP, "PF_setmodel: NULL")

	i = sv_init.SV_ModelIndex (name)

	#ent->model = name;
	ent.s.modelindex = i

	# if it is an inline model, get the size information for it
	if name[0] == '*':
		mod = cmodel.CM_InlineModel (name)
		q_shared.VectorCopy (mod.mins, ent.mins)
		q_shared.VectorCopy (mod.maxs, ent.maxs)
		sv_world.SV_LinkEdict (ent)
"""
/*
===============
PF_Configstring

===============
*/
"""
def PF_Configstring (index, val): #int, char *

	if index < 0 or index >= q_shared.MAX_CONFIGSTRINGS:
		common.Com_Error (qcommon.ERR_DROP, "configstring: bad index %i\n", index)

	if not val:
		val = ""

	# change the string in sv
	sv_init.sv.configstrings[index] = val

	if sv_init.sv.state != sv_init.server_state_t.ss_loading:
		# send the update to everyone
		common.SZ_Clear (sv_init.sv.multicast)
		common.MSG_WriteChar (sv_init.sv.multicast, qcommon.svc_ops_e.svc_configstring.value)
		common.MSG_WriteShort (sv_init.sv.multicast, index)
		common.MSG_WriteString (sv_init.sv.multicast, val)

		sv_send.SV_Multicast (q_shared.vec3_origin, q_shared.multicast_t.MULTICAST_ALL_R)


def PF_WriteChar (c):
	common.MSG_WriteChar (sv_init.sv.multicast, c)
def PF_WriteByte (c):
	common.MSG_WriteByte (sv_init.sv.multicast, c)
def PF_WriteShort (c):
	common.MSG_WriteShort (sv_init.sv.multicast, c)
def PF_WriteLong (c):
	common.MSG_WriteLong (sv_init.sv.multicast, c)
def PF_WriteFloat (f):
	common.MSG_WriteFloat (sv_init.sv.multicast, f)
def PF_WriteString (s):
	common.MSG_WriteString (sv_init.sv.multicast, s)
def PF_WritePos (pos):
	common.MSG_WritePos (sv_init.sv.multicast, pos)
def PF_WriteDir (dir):
	common.MSG_WriteDir (sv_init.sv.multicast, dir)
def PF_WriteAngle (f):
	common.MSG_WriteAngle (sv_init.sv.multicast, f)
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

	leafnum = cmodel.CM_PointLeafnum (p1)
	cluster = cmodel.CM_LeafCluster (leafnum)
	area1 = cmodel.CM_LeafArea (leafnum)
	mask = cmodel.CM_ClusterPVS (cluster)

	leafnum = cmodel.CM_PointLeafnum (p2)
	cluster = cmodel.CM_LeafCluster (leafnum)
	area2 = cmodel.CM_LeafArea (leafnum)
	if mask and not (mask[cluster>>3] & (1<<(cluster&7))):
		return False
	if not cmodel.CM_AreasConnected (area1, area2):
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

	leafnum = cmodel.CM_PointLeafnum (p1)
	cluster = cmodel.CM_LeafCluster (leafnum)
	area1 = cmodel.CM_LeafArea (leafnum)
	mask = cmodel.CM_ClusterPHS (cluster)

	leafnum = cmodel.CM_PointLeafnum (p2)
	cluster = cmodel.CM_LeafCluster (leafnum)
	area2 = cmodel.CM_LeafArea (leafnum)
	if mask and not (mask[cluster>>3] & (1<<(cluster&7))):
		return False		# more than one bounce away
	if not cmodel.CM_AreasConnected (area1, area2):
		return False		# a door blocks hearing

	return True

def PF_StartSound (entity, channel, sound_num, volume, attenuation, timeofs): #edict_t *, int, int, float, float, float

	if not entity:
		return
	sv_send.SV_StartSound (None, entity, channel, sound_num, volume, attenuation, timeofs)

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

	# load a new game dll
	gimport.multicast = sv_send.SV_Multicast
	gimport.unicast = PF_Unicast
	gimport.bprintf = sv_send.SV_BroadcastPrintf
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
	gimport.positioned_sound = sv_send.SV_StartSound

	gimport.WriteChar = PF_WriteChar
	gimport.WriteByte = PF_WriteByte
	gimport.WriteShort = PF_WriteShort
	gimport.WriteLong = PF_WriteLong
	gimport.WriteFloat = PF_WriteFloat
	gimport.WriteString = PF_WriteString
	gimport.WritePosition = PF_WritePos
	gimport.WriteDir = PF_WriteDir
	gimport.WriteAngle = PF_WriteAngle

	gimport.TagMalloc = common.Z_TagMalloc
	gimport.TagFree = common.Z_Free
	gimport.FreeTags = common.Z_FreeTags

	gimport.cvar = cvar.Cvar_Get
	gimport.cvar_set = cvar.Cvar_Set
	gimport.cvar_forceset = cvar.Cvar_ForceSet

	gimport.argc = cmd.Cmd_Argc
	gimport.argv = cmd.Cmd_Argv
	gimport.args = cmd.Cmd_Args
	gimport.AddCommandString = cmd.Cbuf_AddText

	gimport.DebugGraph = cl_scrn.SCR_DebugGraph
	gimport.SetAreaPortalState = cmodel.CM_SetAreaPortalState
	gimport.AreasConnected = cmodel.CM_AreasConnected

	ge = sys_linux.Sys_GetGameAPI (gimport)

	#if (!ge)
	#	Com_Error (qcommon.ERR_DROP, "failed to load game DLL")

	if ge.apiversion != game.GAME_API_VERSION:
		common.Com_Error (qcommon.ERR_DROP, "game is version {:d}, not {:d}".format(ge.apiversion, game.GAME_API_VERSION))

	ge.Init ()
