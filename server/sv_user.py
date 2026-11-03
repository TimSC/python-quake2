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
from server import sv_main, sv_init, sv_game
from qcommon import cvar, qcommon, common, net_chan, cmd, files
from game import q_shared
"""
// sv_user.c -- server code for moving users

#include "server.h"
"""
sv_player = None #edict_t *
"""
/*
============================================================

USER STRINGCMD EXECUTION

sv_client and sv_player will be valid.
============================================================
*/
"""
"""
==================
SV_BeginDemoServer
==================
"""
def SV_BeginDemoserver ():
	#char		name[MAX_OSPATH];

	name = "demos/{}".format(sv_init.sv.name)
	length, sv_init.sv.demofile = files.FS_FOpenFile (name)
	if sv_init.sv.demofile is None:
		common.Com_Error (qcommon.ERR_DROP, "Couldn't open %s\n", name)

"""
================
SV_New_f

Sends the first message from the server to a connected client.
This will be sent on the initial connection and upon each server load.
================
"""
def SV_New_f (): #void

	"""
	char		*gamedir;
	int			playernum;
	edict_t		*ent;
	"""

	#int playernum = 0

	common.Com_DPrintf ("New() from {}\n".format(sv_main.sv_client.name))

	if sv_main.sv_client.state != sv_init.client_state_t.cs_connected:

		common.Com_Printf ("New not valid -- already spawned\n")
		return

	# demo servers just dump the file message
	if sv_init.sv.state == sv_init.server_state_t.ss_demo:

		SV_BeginDemoserver ()
		return

	#
	# serverdata needs to go over for all types of servers
	# to make sure the protocol is right, and to set the gamedir
	#
	gamedir = cvar.Cvar_VariableString ("gamedir")

	# send the serverdata
	common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_serverdata.value)
	common.MSG_WriteLong (sv_main.sv_client.netchan.message, qcommon.PROTOCOL_VERSION)
	common.MSG_WriteLong (sv_main.sv_client.netchan.message, sv_init.svs.spawncount)
	common.MSG_WriteByte (sv_main.sv_client.netchan.message, sv_init.sv.attractloop)
	common.MSG_WriteString (sv_main.sv_client.netchan.message, gamedir)

	if sv_init.sv.state == sv_init.server_state_t.ss_cinematic or sv_init.sv.state == sv_init.server_state_t.ss_pic:
		playernum = -1
	else:
		playernum = sv_init.svs.clients.index(sv_main.sv_client)
	common.MSG_WriteShort (sv_main.sv_client.netchan.message, playernum)

	# send full levelname
	common.MSG_WriteString (sv_main.sv_client.netchan.message, sv_init.sv.configstrings[q_shared.CS_NAME])

	#
	# game server
	#
	if sv_init.sv.state == sv_init.server_state_t.ss_game:

		# set up the entity for the client
		ent = sv_init.EDICT_NUM(playernum+1)
		ent.s.number = playernum+1
		sv_main.sv_client.edict = ent
		sv_main.sv_client.lastcmd = q_shared.usercmd_t()

		# begin fetching configstrings
		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_stufftext.value)
		common.MSG_WriteString (sv_main.sv_client.netchan.message, "cmd configstrings {:d} 0\n".format(sv_init.svs.spawncount))


"""
==================
SV_Configstrings_f
==================
"""
def SV_Configstrings_f ():

	#int start

	common.Com_DPrintf ("Configstrings() from {}\n".format(sv_main.sv_client.name))

	if sv_main.sv_client.state != sv_init.client_state_t.cs_connected:

		common.Com_Printf ("configstrings not valid -- already spawned\n")
		return

	# handle the case of a level changing while a client was connecting
	if int(cmd.Cmd_Argv(1)) != sv_init.svs.spawncount:

		common.Com_Printf ("SV_Configstrings_f from different level\n")
		SV_New_f ()
		return

	start = int(cmd.Cmd_Argv(2))

	# write a packet full of data

	while sv_main.sv_client.netchan.message.cursize < qcommon.MAX_MSGLEN//2 \
		and start < q_shared.MAX_CONFIGSTRINGS:

		if sv_init.sv.configstrings[start][0]:

			common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_configstring.value)
			common.MSG_WriteShort (sv_main.sv_client.netchan.message, start)
			common.MSG_WriteString (sv_main.sv_client.netchan.message, sv_init.sv.configstrings[start])

		start+=1

	# send next command

	if start == q_shared.MAX_CONFIGSTRINGS:

		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_stufftext.value)
		common.MSG_WriteString (sv_main.sv_client.netchan.message, "cmd baselines {:d} 0\n".format(sv_init.svs.spawncount))

	else:

		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_stufftext.value)
		common.MSG_WriteString (sv_main.sv_client.netchan.message, "cmd configstrings {:d} {:d}\n".format(sv_init.svs.spawncount, start))


"""
==================
SV_Baselines_f
==================
"""
def SV_Baselines_f ():

	"""
	int		start;
	entity_state_t	nullstate;
	entity_state_t	*base;
	"""
	#int start = 0

	common.Com_DPrintf ("Baselines() from {}\n".format(sv_main.sv_client.name))

	if sv_main.sv_client.state != sv_init.client_state_t.cs_connected:

		common.Com_Printf ("baselines not valid -- already spawned\n")
		return

	# handle the case of a level changing while a client was connecting
	if int(cmd.Cmd_Argv(1)) != sv_init.svs.spawncount:

		common.Com_Printf ("SV_Baselines_f from different level\n")
		SV_New_f ()
		return

	start = int(cmd.Cmd_Argv(2))

	nullstate = q_shared.entity_state_t()

	# write a packet full of data

	while sv_main.sv_client.netchan.message.cursize < qcommon.MAX_MSGLEN//2 \
		and start < q_shared.MAX_EDICTS:

		base = sv_init.sv.baselines[start]
		if base.modelindex or base.sound or base.effects:

			common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_spawnbaseline.value)
			common.MSG_WriteDeltaEntity (nullstate, base, sv_main.sv_client.netchan.message, True, True)

		start+=1

	# send next command

	if start == q_shared.MAX_EDICTS:

		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_stufftext.value)
		common.MSG_WriteString (sv_main.sv_client.netchan.message, "precache {:d}\n".format(sv_init.svs.spawncount))

	else:

		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_stufftext.value)
		common.MSG_WriteString (sv_main.sv_client.netchan.message, "cmd baselines {:d} {:d}\n".format(sv_init.svs.spawncount, start))


"""
==================
SV_Begin_f
==================
"""
def SV_Begin_f ():

	common.Com_DPrintf ("Begin() from {}\n".format(sv_main.sv_client.name))

	# handle the case of a level changing while a client was connecting
	if int(cmd.Cmd_Argv(1)) != sv_init.svs.spawncount:

		common.Com_Printf ("SV_Begin_f from different level\n")
		SV_New_f ()
		return

	sv_main.sv_client.state = sv_init.client_state_t.cs_spawned

	# call the game begin function
	sv_game.ge.ClientBegin (sv_player)

	cmd.Cbuf_InsertFromDefer ()

"""
//=============================================================================
"""
"""
==================
SV_NextDownload_f
==================
"""
def SV_NextDownload_f ():
	"""
	int		r;
	int		percent;
	int		size;
	"""
	#int r = 0, percent = 0, size = 0

	if not sv_main.sv_client.download:
		return

	r = sv_main.sv_client.downloadsize - sv_main.sv_client.downloadcount
	if r > 1024:
		r = 1024

	common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_download.value)
	common.MSG_WriteShort (sv_main.sv_client.netchan.message, r)

	sv_main.sv_client.downloadcount += r
	size = sv_main.sv_client.downloadsize
	if not size:
		size = 1
	percent = sv_main.sv_client.downloadcount*100//size
	common.MSG_WriteByte (sv_main.sv_client.netchan.message, percent)
	common.SZ_Write (sv_main.sv_client.netchan.message,
		sv_main.sv_client.download[sv_main.sv_client.downloadcount - r : sv_main.sv_client.downloadcount])

	if sv_main.sv_client.downloadcount != sv_main.sv_client.downloadsize:
		return

	files.FS_FreeFile (sv_main.sv_client.download)
	sv_main.sv_client.download = None


"""
==================
SV_BeginDownload_f
==================
"""
def SV_BeginDownload_f():
	"""
	char	*name;
	extern	cvar_t *allow_download;
	extern	cvar_t *allow_download_players;
	extern	cvar_t *allow_download_models;
	extern	cvar_t *allow_download_sounds;
	extern	cvar_t *allow_download_maps;
	extern	int		file_from_pak; // ZOID did file come from pak?
	int offset = 0;
	"""
	#char *name
	#int offset = 0

	name = cmd.Cmd_Argv(1)

	if cmd.Cmd_Argc() > 2:
		offset = int(cmd.Cmd_Argv(2)) # downloaded offset

	# hacked by zoid to allow more conrol over download
	# first off, no .. or global allow check
	if (
		(".." in name)
		or not sv_main.allow_download.value
		# leading dot is no good
		or name[0] == '.'
		# leading slash bad as well, must be in subdir
		or name[0] == '/'
		# next up, skin check
		or (name.startswith('players/') and not sv_main.allow_download_players.value)
		# now models
		or (name.startswith('models/') and not sv_main.allow_download_models.value)
		# now sounds
		or (name.startswith('sound/') and not sv_main.allow_download_sounds.value)
		# now maps (note special case for maps, must not be in pak)
		or (name.startswith('maps/') and not sv_main.allow_download_maps.value)
		# MUST be in a subdirectory
		or (('/' not in name))
	):

		# don't allow anything with .. path
		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_download.value)
		common.MSG_WriteShort (sv_main.sv_client.netchan.message, -1)
		common.MSG_WriteByte (sv_main.sv_client.netchan.message, 0)
		return


	if sv_main.sv_client.download:
		files.FS_FreeFile (sv_main.sv_client.download)

	sv_main.sv_client.downloadsize, sv_main.sv_client.download = files.FS_LoadFile (name)
	sv_main.sv_client.downloadcount = offset

	if offset > sv_main.sv_client.downloadsize:
		sv_main.sv_client.downloadcount = sv_main.sv_client.downloadsize

	if (
		(not sv_main.sv_client.download)
		# special check for maps, if it came from a pak file, don't allow download ZOID
		or (name.startswith('maps/') and files.file_from_pak)
	):
		common.Com_DPrintf ("Couldn't download %s to %s\n" % (name, sv_main.sv_client.name))
		if sv_main.sv_client.download:
			files.FS_FreeFile (sv_main.sv_client.download)
			sv_main.sv_client.download = None

		common.MSG_WriteByte (sv_main.sv_client.netchan.message, qcommon.svc_ops_e.svc_download.value)
		common.MSG_WriteShort (sv_main.sv_client.netchan.message, -1)
		common.MSG_WriteByte (sv_main.sv_client.netchan.message, 0)
		return

	SV_NextDownload_f ()
	common.Com_DPrintf ("Downloading %s to %s\n" % (name, sv_main.sv_client.name))

"""
//============================================================================
"""
"""
=================
SV_Disconnect_f

The client is going to disconnect, so remove the connection immediately
=================
"""
def SV_Disconnect_f ():

#	SV_EndRedirect ();
	sv_main.SV_DropClient (sv_main.sv_client)


"""
==================
SV_ShowServerinfo_f

Dumps the serverinfo info string
==================
"""
def SV_ShowServerinfo_f ():

	common.Info_Print (cvar.Cvar_Serverinfo())


"""
"""
def SV_Nextserver ():

	#char *v

	#ZOID, ss_pic can be nextserver'd in coop mode
	if sv_init.sv.state == sv_init.server_state_t.ss_game \
		or (sv_init.sv.state == sv_init.server_state_t.ss_pic and not cvar.Cvar_VariableValue("coop")):
		return		# can't nextserver while playing a normal game

	sv_init.svs.spawncount+=1	# make sure another doesn't sneak in
	v = cvar.Cvar_VariableString ("nextserver")
	if len(v) == 0:
		cmd.Cbuf_AddText ("killserver\n")
	else:
		cmd.Cbuf_AddText (v)
		cmd.Cbuf_AddText ("\n")

	cvar.Cvar_Set ("nextserver","")


"""
==================
SV_Nextserver_f

A cinematic has completed or been aborted by a client, so move
to the next server,
==================
"""
def SV_Nextserver_f ():

	if int(cmd.Cmd_Argv(1)) != sv_init.svs.spawncount :
		common.Com_DPrintf ("Nextserver() from wrong level, from {}\n".format(sv_main.sv_client.name))
		return		# leftover from last server

	common.Com_DPrintf ("Nextserver() from {}\n".format(sv_main.sv_client.name))

	SV_Nextserver ()


"""
typedef struct
{
	char	*name;
	void	(*func) (void);
} ucmd_t;
"""
ucmds = {
	# auto issued
	"new": SV_New_f,
	"configstrings": SV_Configstrings_f,
	"baselines": SV_Baselines_f,
	"begin": SV_Begin_f,

	"nextserver": SV_Nextserver_f,

	"disconnect": SV_Disconnect_f,

	# issued by hand at client consoles
	"info": SV_ShowServerinfo_f,

	"download": SV_BeginDownload_f,
	"nextdl": SV_NextDownload_f,
}

"""
==================
SV_ExecuteUserCommand
==================
"""
def SV_ExecuteUserCommand (s): #char *

	global sv_player

	cmd.Cmd_TokenizeString (s, True)
	sv_player = sv_main.sv_client.edict

#	SV_BeginRedirect (RD_CLIENT)

	if cmd.Cmd_Argv(0) in ucmds:
		ucmds[cmd.Cmd_Argv(0)]()
	elif sv_init.sv.state == sv_init.server_state_t.ss_game:
		sv_game.ge.ClientCommand (sv_player)

#	SV_EndRedirect ()


"""
===========================================================================

USER CMD EXECUTION

===========================================================================
"""
"""
"""
def SV_ClientThink (cl, cmd_): #client_t *, usercmd_t *

	cl.commandMsec -= cmd_.msec

	if cl.commandMsec < 0 and sv_main.sv_enforcetime.value:
		common.Com_DPrintf ("commandMsec underflow from %s\n" % cl.name)
		return

	sv_game.ge.ClientThink (cl.edict, cmd_)


"""
#define	MAX_STRINGCMDS	8
"""
MAX_STRINGCMDS = 8

"""
===================
SV_ExecuteClientMessage

The current net_message is parsed for the given client
===================
"""
def SV_ExecuteClientMessage (cl): #client_t *

	global sv_player
	"""
	int		c;
	char	*s;

	usercmd_t	nullcmd;
	usercmd_t	oldest, oldcmd, newcmd;
	int		net_drop;
	int		stringCmdCount;
	int		checksum, calculatedChecksum;
	int		checksumIndex;
	qboolean	move_issued;
	int		lastframe;
	"""
	#int c = 0
	#int net_drop = 0, stringCmdCount = 0
	#int checksum = 0, calculatedChecksum = 0, checksumIndex = 0, lastframe = 0

	sv_main.sv_client = cl
	sv_player = sv_main.sv_client.edict

	# only allow one move command
	move_issued = False
	stringCmdCount = 0

	while True:

		if net_chan.net_message.readcount > net_chan.net_message.cursize:

			common.Com_Printf ("SV_ReadClientMessage: badread\n")
			sv_main.SV_DropClient (cl)
			return

		c = common.MSG_ReadByte (net_chan.net_message)
		if c == -1:
			break # nothing to read

		if c == qcommon.clc_ops_e.clc_nop.value:
			pass

		elif c == qcommon.clc_ops_e.clc_userinfo.value:
			cl.userinfo = common.MSG_ReadString (net_chan.net_message)
			sv_main.SV_UserinfoChanged (cl)
			break

		elif c == qcommon.clc_ops_e.clc_move.value:

			if move_issued:
				return		# someone is trying to cheat...

			move_issued = True
			checksumIndex = net_chan.net_message.readcount
			checksum = common.MSG_ReadByte (net_chan.net_message)
			lastframe = common.MSG_ReadLong (net_chan.net_message)
			if lastframe != cl.lastframe:
				cl.lastframe = lastframe
				if cl.lastframe > 0:
					cl.frame_latency[cl.lastframe & (sv_init.LATENCY_COUNTS-1)] = \
						sv_init.svs.realtime - cl.frames[cl.lastframe & qcommon.UPDATE_MASK].senttime

			nullcmd = q_shared.usercmd_t()
			oldest = q_shared.usercmd_t()
			oldcmd = q_shared.usercmd_t()
			newcmd = q_shared.usercmd_t()

			common.MSG_ReadDeltaUsercmd (net_chan.net_message, nullcmd, oldest)
			common.MSG_ReadDeltaUsercmd (net_chan.net_message, oldest, oldcmd)
			common.MSG_ReadDeltaUsercmd (net_chan.net_message, oldcmd, newcmd)

			if cl.state != sv_init.client_state_t.cs_spawned:
				cl.lastframe = -1
				break

			# if the checksum fails, ignore the rest of the packet
			calculatedChecksum = common.COM_BlockSequenceCRCByte (
				net_chan.net_message.data,
				checksumIndex + 1,
				net_chan.net_message.readcount - checksumIndex - 1,
				cl.netchan.incoming_sequence)

			if calculatedChecksum[0] != checksum:
				common.Com_DPrintf ("Failed command checksum for %s (%d != %d)/%d\n" % (
					cl.name, calculatedChecksum[0], checksum, cl.netchan.incoming_sequence))
				return

			if not sv_main.sv_paused.value:
				net_drop = cl.netchan.dropped
				if net_drop < 20:
					while net_drop > 2:
						SV_ClientThink (cl, cl.lastcmd)
						net_drop-=1
					if net_drop > 1:
						SV_ClientThink (cl, oldest)
					if net_drop > 0:
						SV_ClientThink (cl, oldcmd)
				SV_ClientThink (cl, newcmd)

			cl.lastcmd = newcmd
			break

		elif c == qcommon.clc_ops_e.clc_stringcmd.value:

			s = common.MSG_ReadString (net_chan.net_message)

			# malicious users may try using too many string commands
			stringCmdCount += 1
			if stringCmdCount < MAX_STRINGCMDS:
				SV_ExecuteUserCommand (s)

			if cl.state == sv_init.client_state_t.cs_zombie:
				return	# disconnect command

		else:

			common.Com_Printf ("SV_ReadClientMessage: unknown command char\n")
			sv_main.SV_DropClient (cl)
			return
