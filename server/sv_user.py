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

Server side user (player entity) moving.

=======================================================================
"""
from __future__ import annotations

from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import argproc
from common import clientserver
from common import cmdparser
from common import crc
from common import cvar
from common import filesystem
from common import movemsg
from common import szone
from common import netchan
from server.header import server as server_h
from server import sv_game
from server import sv_init
from server import sv_main

"""
#include "header/server.h"
"""

MAX_STRINGCMDS = 8

CMD_MARGIN = 40 # space in message reserved for command
SAFE_MARGIN = 24 # space reserved for more data added elsewhere

sv_player = None #edict_t *

def SV_BeginDemoserver(): #void

	#char name[MAX_OSPATH];

	name = "demos/{}".format(sv_init.sv.name)
	length, sv_init.sv.demofile = filesystem.FS_FOpenFile(name, False)

	if not sv_init.sv.demofile:

		clientserver.Com_Error(shared.ERR_DROP, "Couldn't open %s\n", name)

"""
 * Sends the first message from the server to a connected client.
 * This will be sent on the initial connection and upon each server load.
"""
def SV_New_f(): #void

	"""
	static char *gamedir;
	int playernum;
	"""

	clientserver.Com_DPrintf("New() from %s\n", sv_main.sv_client.name)

	if sv_main.sv_client.state != server_h.client_state_t.cs_connected:

		clientserver.Com_Printf("New not valid -- already spawned\n")
		return


	# demo servers just dump the file message
	if sv_init.sv.state == server_h.server_state_t.ss_demo:

		SV_BeginDemoserver()
		return


	# serverdata needs to go over for all types of servers
	# to make sure the protocol is right, and to set the gamedir
	gamedir = cvar.Cvar_VariableString("gamedir")

	# send the serverdata
	movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_serverdata.value)
	movemsg.MSG_WriteLong(sv_main.sv_client.netchan.message, common_h.PROTOCOL_VERSION)
	movemsg.MSG_WriteLong(sv_main.sv_client.netchan.message, sv_init.svs.spawncount)
	movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, 1 if sv_init.sv.attractloop else 0)
	movemsg.MSG_WriteString(sv_main.sv_client.netchan.message, gamedir)

	if (sv_init.sv.state == server_h.server_state_t.ss_cinematic) or (sv_init.sv.state == server_h.server_state_t.ss_pic):

		playernum = -1

	else:

		playernum = sv_init.svs.clients.index(sv_main.sv_client) #sv_client - svs.clients;


	movemsg.MSG_WriteShort(sv_main.sv_client.netchan.message, playernum)

	# send full levelname
	movemsg.MSG_WriteString(sv_main.sv_client.netchan.message, sv_init.sv.configstrings[shared.CS_NAME])

	# game server
	if sv_init.sv.state == server_h.server_state_t.ss_game:

		# set up the entity for the client
		server_h.CLNUM_EDICT(playernum).s.number = playernum + 1
		sv_main.sv_client.lastcmd = shared.usercmd_t() #memset(&sv_client->lastcmd, 0, sizeof(sv_client->lastcmd));

		# begin fetching configstrings
		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_stufftext.value)
		movemsg.MSG_WriteString(sv_main.sv_client.netchan.message,
				"cmd configstrings %i 0\n" % sv_init.svs.spawncount)

def _EnoughSpaceInBuffer(msg: common_h.sizebuf_t, datalen: int, is_opt: int)->bool: #const sizebuf_t *, size_t, int (returns static qboolean)

	# original check logic
	if not is_opt and (msg.cursize >= (common_h.MAX_MSGLEN // 2)):

		return False


	if (msg.cursize + datalen) > \
		(common_h.MAX_MSGLEN - (CMD_MARGIN + SAFE_MARGIN)):

		return False


	return True

def PrintOverflowConfigstrings(): #void

	"""
	int i, n;
	"""

	n = len(sv_init.sv.configstrings_overflow) #StringList_Len(&sv.configstrings_overflow);

	if not n:

		return


	clientserver.Com_Printf("Failed to load %i resources: configstrings overflowed\n", n)

	for i in range(n):

		clientserver.Com_Printf("  %s\n", sv_init.sv.configstrings_overflow[i])

# Wrote this function because the optimizer was replacing
# strlen(cs) / sizeof(sv.configstrings[i]) with 0
# which is not the correct result for the statusbar string
def _NumIndexSkips(start: int, end: int)->int: #int, int (returns static int)
	# Q2PORT: a configstring that fills its MAX_QPATH buffer (no NUL in the last byte) runs into
	# the next one, as the statusbar program does; Python strings hold the whole text in the
	# first index, so the indexes it spills into are the ones its length covers

	"""
	int i;
	"""

	i = start
	while i < (end - 1) and len(sv_init.sv.configstrings[start]) >= (shared.MAX_QPATH * (i - start + 1)):

		i += 1


	return i - start

def SV_AddBaselines(start: int, allow_zero: bool): #int, qboolean

	"""
	sizebuf_t *msg;
	int i, is_opt;
	"""

	if start < 0:

		start = 0


	msg = sv_main.sv_client.netchan.message
	is_opt = sv_main.SV_Optimizations() & server_h.OPTIMIZE_MSGUTIL

	i = start
	while i < sv_init.sv.numbaselines:

		base = sv_init.sv.baselines[i]

		if base.modelindex or base.sound or base.effects:

			if not _EnoughSpaceInBuffer(msg,
				movemsg.MSG_DeltaEntity_Size(None, base, True, True), is_opt):

				break


			movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_spawnbaseline.value)
			movemsg.MSG_WriteDeltaEntity(None, base, msg, True, True)

		i += 1


	if not allow_zero and \
		(i == start) and (i < sv_init.sv.numbaselines):

		clientserver.Com_Printf("%s: skipping index %i: too big to send\n",
			"SV_AddBaselines", i)
		i += 1


	# send next command
	if i >= sv_init.sv.numbaselines:

		movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_stufftext.value)
		movemsg.MSG_WriteString(msg,
				"precache %i\n" % sv_init.svs.spawncount)

	else:

		movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_stufftext.value)
		movemsg.MSG_WriteString(msg,
				"cmd baselines %i %i\n" % (sv_init.svs.spawncount, i))

def SV_Configstrings_f(): #void

	"""
	const char *cs;
	sizebuf_t *msg;
	int i, start;
	int opt;
	"""

	start = shared_c.atoi(cmdparser.Cmd_Argv(2)) if (cmdparser.Cmd_Argc() > 2) else 0

	clientserver.Com_DPrintf("Configstrings(%i) from %s\n", start, sv_main.sv_client.name)

	if sv_main.sv_client.state != server_h.client_state_t.cs_connected:

		clientserver.Com_Printf("configstrings not valid -- already spawned\n")
		return


	# handle the case of a level changing while a client was connecting
	if (cmdparser.Cmd_Argc() <= 1) or \
		(shared_c.atoi(cmdparser.Cmd_Argv(1)) != sv_init.svs.spawncount):

		clientserver.Com_Printf("SV_Configstrings_f from different level\n")
		SV_New_f()
		return


	if start < 0:

		start = 0


	msg = sv_main.sv_client.netchan.message
	opt = sv_main.SV_Optimizations()
	i = start

	while i < shared.MAX_CONFIGSTRINGS:

		cs = sv_init.sv.configstrings[i]

		if cs != "":

			if not _EnoughSpaceInBuffer(msg, movemsg.MSG_ConfigString_Size(cs), opt & server_h.OPTIMIZE_MSGUTIL):

				break


			movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_configstring.value)
			movemsg.MSG_WriteConfigString(msg, i, cs)


		# statusbar code is sent as one big string
		if (opt & server_h.OPTIMIZE_HUDSEND) and \
			(i >= shared.CS_STATUSBAR) and (i < shared.CS_STATUSBAR_END):

			i += 1 + _NumIndexSkips(i, shared.CS_STATUSBAR_END)

		else:

			i += 1



	if (i == start) and (i < shared.MAX_CONFIGSTRINGS):

		clientserver.Com_Printf("%s: skipping index %i: too big to send\n",
			"SV_Configstrings_f", i)

		# statusbar code is sent as one big string
		if (opt & server_h.OPTIMIZE_HUDSEND) and \
			(i >= shared.CS_STATUSBAR) and (i < shared.CS_STATUSBAR_END):

			i += 1 + _NumIndexSkips(i, shared.CS_STATUSBAR_END)

		else:

			i += 1



	# send next command
	if i >= shared.MAX_CONFIGSTRINGS:

		PrintOverflowConfigstrings()

		if opt & server_h.OPTIMIZE_CSBASE:

			# try use remainder of packet for baselines
			SV_AddBaselines(0, True)

		else:

			movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_stufftext.value)
			movemsg.MSG_WriteString(msg, "cmd baselines %i 0\n" % sv_init.svs.spawncount)


	else:

		movemsg.MSG_WriteByte(msg, common_h.svc_ops_e.svc_stufftext.value)
		movemsg.MSG_WriteString(msg,
			"cmd configstrings %i %i\n" % (sv_init.svs.spawncount, i))

def SV_Baselines_f(): #void

	start = shared_c.atoi(cmdparser.Cmd_Argv(2)) if (cmdparser.Cmd_Argc() > 2) else 0

	clientserver.Com_DPrintf("Baselines(%i) from %s\n", start, sv_main.sv_client.name)

	if sv_main.sv_client.state != server_h.client_state_t.cs_connected:

		clientserver.Com_Printf("baselines not valid -- already spawned\n")
		return


	# handle the case of a level changing while a client was connecting
	if (cmdparser.Cmd_Argc() <= 1) or \
		(shared_c.atoi(cmdparser.Cmd_Argv(1)) != sv_init.svs.spawncount):

		clientserver.Com_Printf("SV_Baselines_f from different level\n")
		SV_New_f()
		return


	SV_AddBaselines(start, False)

def SV_Begin_f(): #void

	clientserver.Com_DPrintf("Begin() from %s\n", sv_main.sv_client.name)

	# handle the case of a level changing while a client was connecting
	if shared_c.atoi(cmdparser.Cmd_Argv(1)) != sv_init.svs.spawncount:

		clientserver.Com_Printf("SV_Begin_f from different level\n")
		SV_New_f()
		return


	sv_main.sv_client.state = server_h.client_state_t.cs_spawned

	# call the game begin function
	sv_game.ge.ClientBegin(sv_player)

	cmdparser.Cbuf_InsertFromDefer()

def SV_NextDownload_f(): #void

	"""
	int r;
	int percent;
	int size;
	"""

	if not sv_main.sv_client.download:

		return


	r = sv_main.sv_client.downloadsize - sv_main.sv_client.downloadcount

	if r > 1024:

		r = 1024


	movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_download.value)
	movemsg.MSG_WriteShort(sv_main.sv_client.netchan.message, r)

	sv_main.sv_client.downloadcount += r
	size = sv_main.sv_client.downloadsize

	if not size:

		size = 1


	percent = sv_main.sv_client.downloadcount * 100 // size
	movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, percent)
	szone.SZ_Write(sv_main.sv_client.netchan.message,
			sv_main.sv_client.download[sv_main.sv_client.downloadcount - r:sv_main.sv_client.downloadcount])

	if sv_main.sv_client.downloadcount != sv_main.sv_client.downloadsize:

		return


	filesystem.FS_FreeFile(sv_main.sv_client.download)
	sv_main.sv_client.download = None

def SV_BeginDownload_f(): #void

	"""
	char *name;
	extern cvar_t *allow_download;
	extern cvar_t *allow_download_players;
	extern cvar_t *allow_download_models;
	extern cvar_t *allow_download_sounds;
	extern cvar_t *allow_download_maps;
	extern qboolean file_from_protected_pak;
	int offset = 0;
	"""
	offset = 0

	name = cmdparser.Cmd_Argv(1)

	if cmdparser.Cmd_Argc() > 2:

		offset = shared_c.atoi(cmdparser.Cmd_Argv(2)) # downloaded offset


	# hacked by zoid to allow more conrol over download
	# first off, no .. or global allow check
	if ".." in name or "\\" in name or ":" in name or not sv_main.allow_download.value \
		or (name[:1] == '.') \
		or (name[:1] == '/') \
		or ((name[:8] == "players/") and not sv_main.allow_download_players.value) \
		or ((name[:7] == "models/") and not sv_main.allow_download_models.value) \
		or ((name[:6] == "sound/") and not sv_main.allow_download_sounds.value) \
		or ((name[:5] == "maps/") and not sv_main.allow_download_maps.value) \
		or "/" not in name:
		# leading dot is no good
		# leading slash bad as well, must be in subdir
		# next up, skin check
		# now models
		# now sounds
		# now maps (note special case for maps, must not be in pak)
		# MUST be in a subdirectory

		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_download.value)
		movemsg.MSG_WriteShort(sv_main.sv_client.netchan.message, -1)
		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, 0)
		return


	if sv_main.sv_client.download:

		filesystem.FS_FreeFile(sv_main.sv_client.download)


	sv_main.sv_client.downloadsize, sv_main.sv_client.download = filesystem.FS_LoadFile(name)
	sv_main.sv_client.downloadcount = offset

	if offset > sv_main.sv_client.downloadsize:

		sv_main.sv_client.downloadcount = sv_main.sv_client.downloadsize


	if not sv_main.sv_client.download or ((name[:5] == "maps/") and filesystem.file_from_protected_pak):

		clientserver.Com_DPrintf("Couldn't download %s to %s\n", name, sv_main.sv_client.name)

		if sv_main.sv_client.download:

			filesystem.FS_FreeFile(sv_main.sv_client.download)
			sv_main.sv_client.download = None


		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, common_h.svc_ops_e.svc_download.value)
		movemsg.MSG_WriteShort(sv_main.sv_client.netchan.message, -1)
		movemsg.MSG_WriteByte(sv_main.sv_client.netchan.message, 0)
		return


	SV_NextDownload_f()
	clientserver.Com_DPrintf("Downloading %s to %s\n", name, sv_main.sv_client.name)

"""
 * The client is going to disconnect, so remove the connection immediately
"""
def SV_Disconnect_f(): #void

	sv_main.SV_DropClient(sv_main.sv_client)

"""
 * Dumps the serverinfo info string
"""
def SV_ShowServerinfo_f(): #void

	argproc.Info_Print(cvar.Cvar_Serverinfo())

def SV_Nextserver(): #void

	"""
	const char *v;
	"""

	if (sv_init.sv.state == server_h.server_state_t.ss_game) or \
		((sv_init.sv.state == server_h.server_state_t.ss_pic) and
		 not cvar.Cvar_VariableValue("coop")):

		return # can't nextserver while playing a normal game


	sv_init.svs.spawncount += 1 # make sure another doesn't sneak in
	v = cvar.Cvar_VariableString("nextserver")

	if not v:

		cmdparser.Cbuf_AddText("killserver\n")

	else:

		cmdparser.Cbuf_AddText(v)
		cmdparser.Cbuf_AddText("\n")


	cvar.Cvar_Set("nextserver", "")

"""
 * A cinematic has completed or been aborted by a client, so move
 * to the next server,
"""
def SV_Nextserver_f(): #void

	if shared_c.atoi(cmdparser.Cmd_Argv(1)) != sv_init.svs.spawncount:

		clientserver.Com_DPrintf("Nextserver() from wrong level, from %s\n", sv_main.sv_client.name)
		return # leftover from last server


	clientserver.Com_DPrintf("Nextserver() from %s\n", sv_main.sv_client.name)

	SV_Nextserver()

class ucmd_t(object):

	def __init__(self, name, func):

		self.name = name #char *
		self.func = func #void (*func)(void);

ucmds = [
	# auto issued
	ucmd_t("new", SV_New_f),
	ucmd_t("configstrings", SV_Configstrings_f),
	ucmd_t("baselines", SV_Baselines_f),
	ucmd_t("begin", SV_Begin_f),
	ucmd_t("nextserver", SV_Nextserver_f),
	ucmd_t("disconnect", SV_Disconnect_f),

	# issued by hand at client consoles
	ucmd_t("info", SV_ShowServerinfo_f),

	ucmd_t("download", SV_BeginDownload_f),
	ucmd_t("nextdl", SV_NextDownload_f),

	#{NULL, NULL}
]

def SV_ExecuteUserCommand(s: str): #char *

	global sv_player

	"""
	ucmd_t *u;
	"""

	# Security Fix... This is being set to false so that client's can't
	# macro expand variables on the server.  It seems unlikely that a
	# client ever ought to need to be able to do this...
	cmdparser.Cmd_TokenizeString(s, False)
	sv_player = server_h.CL_EDICT(sv_main.sv_client)

	found = None
	for u in ucmds:

		if cmdparser.Cmd_Argv(0) == u.name:

			u.func()
			found = u
			break



	if found is None and (sv_init.sv.state == server_h.server_state_t.ss_game):

		sv_game.ge.ClientCommand(sv_player)

def SV_ClientThink(cl: server_h.client_t, cmd: shared.usercmd_t): #client_t *, usercmd_t *

	cl.commandMsec -= cmd.msec

	if (cl.commandMsec < 0) and sv_main.sv_enforcetime.value:

		clientserver.Com_DPrintf("commandMsec underflow from %s\n", cl.name)
		return


	sv_game.ge.ClientThink(server_h.CL_EDICT(cl), cmd)

"""
 * The current net_message is parsed for the given client
"""
def SV_ExecuteClientMessage(cl: server_h.client_t): #client_t *

	global sv_player

	"""
	int c;
	char *s;

	usercmd_t nullcmd;
	usercmd_t oldest, oldcmd, newcmd;
	int net_drop;
	int stringCmdCount;
	int checksum, calculatedChecksum;
	int checksumIndex;
	qboolean move_issued;
	int lastframe;
	"""

	sv_main.sv_client = cl
	sv_player = server_h.CL_EDICT(sv_main.sv_client)

	# only allow one move command
	move_issued = False
	stringCmdCount = 0

	while 1:

		if netchan.net_message.readcount > netchan.net_message.cursize:

			clientserver.Com_Printf("SV_ReadClientMessage: badread\n")
			sv_main.SV_DropClient(cl)
			return


		c = movemsg.MSG_ReadByte(netchan.net_message)

		if c == -1:

			break


		# Q2PORT: the switch; a C 'break' out of a case falls to the end of the if chain
		if c == common_h.clc_ops_e.clc_nop.value:
			pass

		elif c == common_h.clc_ops_e.clc_userinfo.value:
			cl.userinfo = movemsg.MSG_ReadString(netchan.net_message)[:shared.MAX_INFO_STRING - 1]
			sv_main.SV_UserinfoChanged(cl)

		elif c == common_h.clc_ops_e.clc_move.value:

			if move_issued:

				return # someone is trying to cheat...


			move_issued = True
			checksumIndex = netchan.net_message.readcount
			checksum = movemsg.MSG_ReadByte(netchan.net_message)
			lastframe = movemsg.MSG_ReadLong(netchan.net_message)

			if lastframe != cl.lastframe:

				cl.lastframe = lastframe

				if cl.lastframe > 0:

					cl.frame_latency[cl.lastframe & (server_h.LATENCY_COUNTS - 1)] = \
						sv_init.svs.realtime - cl.frames[cl.lastframe & common_h.UPDATE_MASK].senttime



			nullcmd = shared.usercmd_t() #memset(&nullcmd, 0, sizeof(nullcmd));
			oldest = shared.usercmd_t()
			oldcmd = shared.usercmd_t()
			newcmd = shared.usercmd_t()
			movemsg.MSG_ReadDeltaUsercmd(netchan.net_message, nullcmd, oldest)
			movemsg.MSG_ReadDeltaUsercmd(netchan.net_message, oldest, oldcmd)
			movemsg.MSG_ReadDeltaUsercmd(netchan.net_message, oldcmd, newcmd)

			if cl.state != server_h.client_state_t.cs_spawned:

				cl.lastframe = -1
				continue	# break;


			# if the checksum fails, ignore the rest of the packet
			calculatedChecksum = crc.COM_BlockSequenceCRCByte(
				netchan.net_message.data, checksumIndex + 1,
				netchan.net_message.readcount - checksumIndex - 1,
				cl.netchan.incoming_sequence)[0]

			if calculatedChecksum != checksum:

				clientserver.Com_DPrintf("Failed command checksum for %s (%d != %d)/%d\n",
						cl.name, calculatedChecksum, checksum,
						cl.netchan.incoming_sequence)
				return


			if not sv_main.sv_paused.value:

				net_drop = cl.netchan.dropped

				if net_drop < 20:

					while net_drop > 2:

						SV_ClientThink(cl, cl.lastcmd)

						net_drop -= 1


					if net_drop > 1:

						SV_ClientThink(cl, oldest)


					if net_drop > 0:

						SV_ClientThink(cl, oldcmd)



				SV_ClientThink(cl, newcmd)


			cl.lastcmd = newcmd

		elif c == common_h.clc_ops_e.clc_stringcmd.value:
			s = movemsg.MSG_ReadString(netchan.net_message)

			# malicious users may try using too many string commands
			stringCmdCount += 1
			if stringCmdCount < MAX_STRINGCMDS:

				SV_ExecuteUserCommand(s)


			if cl.state == server_h.client_state_t.cs_zombie:

				return # disconnect command

		else:
			clientserver.Com_Printf("SV_ReadClientMessage: unknown command char\n")
			sv_main.SV_DropClient(cl)
			return
