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

import os
import struct
from client import cl_main, cl_scrn, cl_view, client, cl_cin, cl_ents, cl_fx, snd_dma, cl_tent, console, cl_inv
pass
from qcommon import net_chan, cmodel
from linux import cd_linux, sys_linux, vid_so
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import movemsg
from common import szone
"""
// cl_parse.c  -- parse a message received from the server

#include "client.h"
"""
svc_strings = \
[
	"svc_bad",

	"svc_muzzleflash",
	"svc_muzzlflash2",
	"svc_temp_entity",
	"svc_layout",
	"svc_inventory",

	"svc_nop",
	"svc_disconnect",
	"svc_reconnect",
	"svc_sound",
	"svc_print",
	"svc_stufftext",
	"svc_serverdata",
	"svc_configstring",
	"svc_spawnbaseline",	
	"svc_centerprint",
	"svc_download",
	"svc_playerinfo",
	"svc_packetentities",
	"svc_deltapacketentities",
	"svc_frame"]

while len(svc_strings) < 256:
	svc_strings.append(None)

#=====================================

def CL_DownloadFileName(fn): #char * (returns char *dest)

	if fn[:7] == "players":
		dest = "{}/{}".format(common_h.BASEDIRNAME, fn)
	else:
		dest = "{}/{}".format(filesystem.FS_Gamedir(), fn)
	return dest

"""
===============
CL_CheckOrDownloadFile

Returns true if the file exists, otherwise it attempts
to start a download from the server.
===============
"""
def CL_CheckOrDownloadFile (filename): #char * (returns qboolean)

	#FILE *fp;
	#char	name[MAX_OSPATH];

	if ".." in filename:
	
		clientserver.Com_Printf ("Refusing to download a path with ..\n")
		return True
	
	if filesystem.FS_LoadFile (filename)[0] != -1:
		# it exists, no need to download
		return True
	
	cl_main.cls.downloadname = filename

	# download to a temp name, and only rename
	# to the real name when done, so if interrupted
	# a runt file wont be left
	cl_main.cls.downloadtempname = shared_c.COM_StripExtension (cl_main.cls.downloadname)
	cl_main.cls.downloadtempname += ".tmp"

#ZOID
	# check to see if we already have a tmp for this file, if so, try to resume
	# open the file if not opened yet
	name = CL_DownloadFileName(cl_main.cls.downloadtempname)

#	FS_CreatePath (name);

	try:
		fp = open (name, "r+b")
	except OSError:
		fp = None
	if fp is not None: # it exists
		#int len;
		fp.seek(0, os.SEEK_END)
		length = fp.tell()

		cl_main.cls.download = fp

		# give the server an offset to start the download
		clientserver.Com_Printf ("Resuming {}\n".format(cl_main.cls.downloadname))
		movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
		movemsg.MSG_WriteString (cl_main.cls.netchan.message,
			"download {} {}".format(cl_main.cls.downloadname, length).encode('ascii'))
	else:
		clientserver.Com_Printf ("Downloading {}\n".format(cl_main.cls.downloadname))
		movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
		movemsg.MSG_WriteString (cl_main.cls.netchan.message,
			"download {}".format(cl_main.cls.downloadname).encode('ascii'))
	
	cl_main.cls.downloadnumber += 1

	return False

"""
===============
CL_Download_f

Request a download from the server
===============
"""
def CL_Download_f ():

	#char filename[MAX_OSPATH];

	if cmdparser.Cmd_Argc() != 2:
		clientserver.Com_Printf("Usage: download <filename>\n")
		return
	
	filename = cmdparser.Cmd_Argv(1)

	if ".." in filename:
	
		clientserver.Com_Printf ("Refusing to download a path with ..\n")
		return
	
	if filesystem.FS_LoadFile (filename)[0] != -1:
		# it exists, no need to download
		clientserver.Com_Printf("File already exists.\n")
		return
	
	cl_main.cls.downloadname = filename
	clientserver.Com_Printf ("Downloading {}\n".format(cl_main.cls.downloadname))

	# download to a temp name, and only rename
	# to the real name when done, so if interrupted
	# a runt file wont be left
	cl_main.cls.downloadtempname = shared_c.COM_StripExtension (cl_main.cls.downloadname)
	cl_main.cls.downloadtempname += ".tmp"

	movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
	movemsg.MSG_WriteString (cl_main.cls.netchan.message,
		"download {}".format(cl_main.cls.downloadname).encode('ascii'))

	cl_main.cls.downloadnumber += 1

"""
======================
CL_RegisterSounds
======================
"""
def CL_RegisterSounds ():

	#int		i;

	snd_dma.S_BeginRegistration ()
	cl_tent.CL_RegisterTEntSounds ()
	for i in range(1, shared.MAX_SOUNDS):
	
		if cl_main.cl.configstrings[shared.CS_SOUNDS+i] is None:
			break
		cl_main.cl.sound_precache[i] = snd_dma.S_RegisterSound (cl_main.cl.configstrings[shared.CS_SOUNDS+i])
		sys_linux.Sys_SendKeyEvents ()	# pump message loop
	
	snd_dma.S_EndRegistration ()



"""
=====================
CL_ParseDownload

A download message has been received from the server
=====================
"""
def CL_ParseDownload ():

	#int		size, percent;
	#char	name[MAX_OSPATH];
	#int		r;

	# read the data
	size = movemsg.MSG_ReadShort (net_chan.net_message)
	percent = movemsg.MSG_ReadByte (net_chan.net_message)
	if size == -1:
	
		clientserver.Com_Printf ("Server does not have this file.\n")
		if cl_main.cls.download is not None:
		
			# if here, we tried to resume a file but the server said no
			cl_main.cls.download.close ()
			cl_main.cls.download = None
		
		cl_main.CL_RequestNextDownload ()
		return
	
	# open the file if not opened yet
	if cl_main.cls.download is None:
	
		name = CL_DownloadFileName(cl_main.cls.downloadtempname)

		filesystem.FS_CreatePath (name)

		try:
			cl_main.cls.download = open (name, "wb")
		except OSError:
			cl_main.cls.download = None
		if cl_main.cls.download is None:
		
			net_chan.net_message.readcount += size
			clientserver.Com_Printf ("Failed to open {}\n".format(cl_main.cls.downloadtempname))
			cl_main.CL_RequestNextDownload ()
			return
		
	cl_main.cls.download.write (net_chan.net_message.data[net_chan.net_message.readcount:net_chan.net_message.readcount + size])
	net_chan.net_message.readcount += size

	if percent != 100:
	
		# request next block
		"""
// change display routines by zoid
#if 0
		Com_Printf (".");
		if (10*(percent/10) != cls.downloadpercent)
		{
			cls.downloadpercent = 10*(percent/10);
			Com_Printf ("%i%%", cls.downloadpercent);
		}
#endif
		"""
		cl_main.cls.downloadpercent = percent

		movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
		szone.SZ_Print (cl_main.cls.netchan.message, "nextdl")
	
	else:
	
		#char	oldn[MAX_OSPATH];
		#char	newn[MAX_OSPATH];

#		Com_Printf ("100%%\n");

		cl_main.cls.download.close ()

		# rename the temp file to it's final name
		oldn = CL_DownloadFileName(cl_main.cls.downloadtempname)
		newn = CL_DownloadFileName(cl_main.cls.downloadname)
		try:
			os.rename (oldn, newn)
			r = 0
		except OSError:
			r = -1
		if r:
			clientserver.Com_Printf ("failed to rename.\n")

		cl_main.cls.download = None
		cl_main.cls.downloadpercent = 0

		# get another file if needed

		cl_main.CL_RequestNextDownload ()


"""
=====================================================================

  SERVER CONNECTING MESSAGES

=====================================================================
"""

"""
==================
CL_ParseServerData
==================
"""
def CL_ParseServerData ():

	clientserver.Com_DPrintf ("Serverdata packet received.\n")

	cl_main.CL_ClearState ()
	cl_main.cls.state = client.connstate_t.ca_connected

	protocol = movemsg.MSG_ReadLong (net_chan.net_message)
	cl_main.cls.serverProtocol = protocol

	if not (clientserver.Com_ServerState() and common_h.PROTOCOL_VERSION == 34):
		if protocol != common_h.PROTOCOL_VERSION:
			clientserver.Com_Error (common_h.ERR_DROP, "Server returned version {}, not {}".format(protocol, common_h.PROTOCOL_VERSION))

	cl_main.cl.servercount = movemsg.MSG_ReadLong (net_chan.net_message)
	cl_main.cl.attractloop = movemsg.MSG_ReadByte (net_chan.net_message)

	gamedir = movemsg.MSG_ReadString (net_chan.net_message)
	cl_main.cl.gamedir = gamedir[:shared.MAX_QPATH]

	fsvar = filesystem.fs_gamedirvar
	if gamedir:
		if not fsvar or not fsvar.string or fsvar.string != gamedir:
			cvar.Cvar_Set ("game", gamedir)
	elif fsvar and fsvar.string:
		cvar.Cvar_Set ("game", gamedir)

	cl_main.cl.playernum = movemsg.MSG_ReadSShort (net_chan.net_message)

	level_name = movemsg.MSG_ReadString (net_chan.net_message)

	if cl_main.cl.playernum == -1:
		cl_cin.SCR_PlayCinematic (level_name)
	else:
		clientserver.Com_Printf ("\n\n\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n\n")
		clientserver.Com_Printf ("{}{}\n".format(chr(2), level_name))
		cl_main.cl.refresh_prepped = False
	


"""
==================
CL_ParseBaseline
==================
"""
def CL_ParseBaseline ():

	"""
	entity_state_t	*es;
	int				bits;
	int				newnum;
	entity_state_t	nullstate;
	"""

	nullstate = shared.entity_state_t()

	newnum, bits = cl_ents.CL_ParseEntityBits ()
	es = cl_main.cl_entities[newnum].baseline
	cl_ents.CL_ParseDelta (nullstate, es, newnum, bits)

"""
================
CL_LoadClientinfo

================
"""
def CL_LoadClientinfo (ci, s): #clientinfo_t *, char *

	"""
	int i;
	char		*t;
	char		model_name[MAX_QPATH];
	char		skin_name[MAX_QPATH];
	char		model_filename[MAX_QPATH];
	char		skin_filename[MAX_QPATH];
	char		weapon_filename[MAX_QPATH];
	"""

	if s is None: # unset configstrings are None rather than ""
		s = ""

	ci.cinfo = s[:shared.MAX_QPATH-1] # strncpy(ci->cinfo, s, sizeof(ci->cinfo)); ci->cinfo[sizeof(ci->cinfo)-1] = 0;

	# isolate the player's name
	ci.name = s[:shared.MAX_QPATH-1]
	t = s.find ("\\")
	if t != -1:
	
		ci.name = ci.name[:t] # ci->name[t-s] = 0;
		s = s[t+1:]
	
	if cl_main.cl_noskins.value or len(s) == 0:
	
		model_filename = "players/male/tris.md2"
		weapon_filename = "players/male/weapon.md2"
		skin_filename = "players/male/grunt.pcx"
		ci.iconname = "/players/male/grunt_i.pcx"
		ci.model = vid_so.re.RegisterModel (model_filename)
		for i in range(client.MAX_CLIENTWEAPONMODELS): # memset(ci->weaponmodel, 0, sizeof(ci->weaponmodel));
			ci.weaponmodel[i] = None
		ci.weaponmodel[0] = vid_so.re.RegisterModel (weapon_filename)
		ci.skin = vid_so.re.RegisterSkin (skin_filename)
		ci.icon = vid_so.re.RegisterPic (ci.iconname)
	
	else:
	
		# isolate the model name
		model_name = s
		t = model_name.find("/")
		if t == -1:
			t = model_name.find("\\")
		if t == -1:
			t = 0
		model_name = model_name[:t] # *t = 0;

		# isolate the skin name
		skin_name = s[len(model_name) + 1:]

		# model file
		model_filename = "players/{}/tris.md2".format(model_name)
		ci.model = vid_so.re.RegisterModel (model_filename)
		if not ci.model:
		
			model_name = "male"
			model_filename = "players/male/tris.md2"
			ci.model = vid_so.re.RegisterModel (model_filename)
		
		# skin file
		skin_filename = "players/{}/{}.pcx".format(model_name, skin_name)
		ci.skin = vid_so.re.RegisterSkin (skin_filename)

		# if we don't have the skin and the model wasn't male,
		# see if the male has it (this is for CTF's skins)
		if not ci.skin and shared_c.Q_stricmp(model_name, "male"):
		
			# change model to male
			model_name = "male"
			model_filename = "players/male/tris.md2"
			ci.model = vid_so.re.RegisterModel (model_filename)

			# see if the skin exists for the male model
			skin_filename = "players/{}/{}.pcx".format(model_name, skin_name)
			ci.skin = vid_so.re.RegisterSkin (skin_filename)
		
		# if we still don't have a skin, it means that the male model didn't have
		# it, so default to grunt
		if not ci.skin:
			# see if the skin exists for the male model
			skin_filename = "players/{}/grunt.pcx".format(model_name)
			ci.skin = vid_so.re.RegisterSkin (skin_filename)
		
		# weapon file
		for i in range(cl_view.num_cl_weaponmodels):
			weapon_filename = "players/{}/{}".format(model_name, cl_view.cl_weaponmodels[i])
			ci.weaponmodel[i] = vid_so.re.RegisterModel(weapon_filename)
			if not ci.weaponmodel[i] and model_name == "cyborg":
				# try male
				weapon_filename = "players/male/{}".format(cl_view.cl_weaponmodels[i])
				ci.weaponmodel[i] = vid_so.re.RegisterModel(weapon_filename)
			
			if not cl_main.cl_vwep.value:
				break # only one when vwep is off
		
		# icon file
		ci.iconname = "/players/{}/{}_i.pcx".format(model_name, skin_name)
		ci.icon = vid_so.re.RegisterPic (ci.iconname)
	
	# must have loaded all data types to be valud
	if not ci.skin or not ci.icon or not ci.model or not ci.weaponmodel[0]:
	
		ci.skin = None
		ci.icon = None
		ci.model = None
		ci.weaponmodel[0] = None
		return
	

"""
================
CL_ParseClientinfo

Load the skin, icon, and model for a client
================
"""
def CL_ParseClientinfo (player): #int

	#char			*s;
	#clientinfo_t	*ci;

	s = cl_main.cl.configstrings[player+shared.CS_PLAYERSKINS]

	ci = cl_main.cl.clientinfo[player]

	CL_LoadClientinfo (ci, s)

# =================
# CL_ParseConfigString
# =================
def CL_ParseConfigString ():

		# int		i;
		# char	*s;
		# char	olds[MAX_QPATH];


	i = movemsg.MSG_ReadShort (net_chan.net_message)
	if i < 0 or i >= shared.MAX_CONFIGSTRINGS:
		clientserver.Com_Error (common_h.ERR_DROP, "configstring > MAX_CONFIGSTRINGS")
	s = movemsg.MSG_ReadString (net_chan.net_message)

	olds = cl_main.cl.configstrings[i] or ""
	cl_main.cl.configstrings[i] = s

	if i >= shared.CS_LIGHTS and i < shared.CS_LIGHTS + shared.MAX_LIGHTSTYLES:
		cl_fx.CL_SetLightstyle (i - shared.CS_LIGHTS)

	elif i == shared.CS_CDTRACK:
		if cl_main.cl.refresh_prepped:
			track = 0
			try:
				track = int (cl_main.cl.configstrings[shared.CS_CDTRACK] or "")
			except ValueError:
				pass
			cd_linux.CDAudio_Play (track, True)

	elif i >= shared.CS_MODELS and i < shared.CS_MODELS + shared.MAX_MODELS:
		if cl_main.cl.refresh_prepped:
			model_name = cl_main.cl.configstrings[i]
			if model_name:
				cl_main.cl.model_draw[i - shared.CS_MODELS] = vid_so.re.RegisterModel (model_name)
				if model_name[0] == '*':
					cl_main.cl.model_clip[i - shared.CS_MODELS] = cmodel.CM_InlineModel (model_name)
				else:
					cl_main.cl.model_clip[i - shared.CS_MODELS] = None

	elif i >= shared.CS_SOUNDS and i < shared.CS_SOUNDS + shared.MAX_SOUNDS:
		if cl_main.cl.refresh_prepped:
			sound_name = cl_main.cl.configstrings[i]
			if sound_name:
				cl_main.cl.sound_precache[i - shared.CS_SOUNDS] = snd_dma.S_RegisterSound (sound_name)

	elif i >= shared.CS_IMAGES and i < shared.CS_IMAGES + shared.MAX_IMAGES:
		if cl_main.cl.refresh_prepped:
			image_name = cl_main.cl.configstrings[i]
			if image_name:
				cl_main.cl.image_precache[i - shared.CS_IMAGES] = vid_so.re.RegisterPic (image_name)

	elif i >= shared.CS_PLAYERSKINS and i < shared.CS_PLAYERSKINS + shared.MAX_CLIENTS:
		if cl_main.cl.refresh_prepped and olds != s:
			CL_ParseClientinfo (i - shared.CS_PLAYERSKINS)
	



# ======================================================================
# ACTION MESSAGES
# ======================================================================

# ==================
# CL_ParseStartSoundPacket
# ==================
def CL_ParseStartSoundPacket():

	# vec3_t  pos_v;
	# float	*pos;
	# int 	channel, ent;
	# int 	sound_num;
	# float 	volume;
	# float 	attenuation;
	# int		flags;
	# float	ofs;


	flags = movemsg.MSG_ReadByte (net_chan.net_message)
	sound_num = movemsg.MSG_ReadByte (net_chan.net_message)

	if flags & common_h.SND_VOLUME:
		volume = movemsg.MSG_ReadByte (net_chan.net_message) / 255.0
	else:
		volume = common_h.DEFAULT_SOUND_PACKET_VOLUME
	
	if flags & common_h.SND_ATTENUATION:
		attenuation = movemsg.MSG_ReadByte (net_chan.net_message) / 64.0
	else:
		attenuation = common_h.DEFAULT_SOUND_PACKET_ATTENUATION

	if flags & common_h.SND_OFFSET:
		ofs = movemsg.MSG_ReadByte (net_chan.net_message) / 1000.0
	else:
		ofs = 0

	if flags & common_h.SND_ENT:
		# entity reletive
		channel = movemsg.MSG_ReadShort(net_chan.net_message)
		ent = channel>>3
		if ent > shared.MAX_EDICTS:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseStartSoundPacket: ent = {}".format(ent))

		channel &= 7
	
	else:
	
		ent = 0
		channel = 0
	

	if flags & common_h.SND_POS:
		# positioned in space
		pos_v = movemsg.MSG_ReadPos (net_chan.net_message)
 
		pos = pos_v
	
	else:	# use entity number
		pos = None

	if sound_num < 0 or sound_num >= len (cl_main.cl.sound_precache):
		return

	if not cl_main.cl.sound_precache[sound_num]:
		return

	snd_dma.S_StartSound (pos, ent, channel, cl_main.cl.sound_precache[sound_num], volume, attenuation, ofs)
	   


def SHOWNET(s): #char *

	if cl_main.cl_shownet.value>=2:
		clientserver.Com_Printf ("{:3d}:{}\n".format(net_chan.net_message.readcount-1, s))

# ====================
# CL_ParseServerMessage
# ====================
def CL_ParseServerMessage ():

	#int			cmd;
	#char		*s;
	#int			i;

	#
	# if recording demos, copy the message out
	#
	if cl_main.cl_shownet.value == 1:
		clientserver.Com_Printf ("{:d} ".format(net_chan.net_message.cursize))
	elif cl_main.cl_shownet.value >= 2:
		clientserver.Com_Printf ("------------------\n")

	#
	# parse the message
	#
	while True:
		if net_chan.net_message.readcount > net_chan.net_message.cursize:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseServerMessage: Bad server message")
			break

		cmd_raw = movemsg.MSG_ReadByte (net_chan.net_message)
		if cmd_raw == -1:
			SHOWNET("END OF MESSAGE")
			break

		if cl_main.cl_shownet.value>=2:

			if not svc_strings[cmd_raw]:
				clientserver.Com_Printf ("{:3d}:BAD CMD {:d}".format(net_chan.net_message.readcount-1,cmd_raw))
			else:
				SHOWNET(svc_strings[cmd_raw])

		try:
			cmdval = common_h.svc_ops_e (cmd_raw)
		except ValueError:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseServerMessage: Illegible server message")
			break

		if cmdval == common_h.svc_ops_e.svc_nop:
			pass
		elif cmdval == common_h.svc_ops_e.svc_disconnect:
			clientserver.Com_Error (shared.ERR_DISCONNECT,"Server disconnected\n")
		elif cmdval == common_h.svc_ops_e.svc_reconnect:
			clientserver.Com_Printf ("Server disconnected, reconnecting\n")
			if cl_main.cls.download:
				cl_main.cls.download.close ()
				cl_main.cls.download = None

			cl_main.cls.state = client.connstate_t.ca_connecting
			cl_main.cls.connect_time = -99999
		elif cmdval == common_h.svc_ops_e.svc_print:
			i = movemsg.MSG_ReadByte (net_chan.net_message)
			if i == shared.PRINT_CHAT:
				snd_dma.S_StartLocalSound ("misc/talk.wav")
				console.con.ormask = 128

			clientserver.Com_Printf (movemsg.MSG_ReadString(net_chan.net_message))
			console.con.ormask = 0
		elif cmdval == common_h.svc_ops_e.svc_centerprint:
			cl_scrn.SCR_CenterPrint (movemsg.MSG_ReadString(net_chan.net_message))
		elif cmdval == common_h.svc_ops_e.svc_stufftext:
			s = movemsg.MSG_ReadString(net_chan.net_message)
			clientserver.Com_DPrintf ("stufftext: {}\n".format(s))
			cmdparser.Cbuf_AddText (s)
		elif cmdval == common_h.svc_ops_e.svc_serverdata:
			cmdparser.Cbuf_Execute ()
			CL_ParseServerData ()
		elif cmdval == common_h.svc_ops_e.svc_configstring:
			CL_ParseConfigString ()
		elif cmdval == common_h.svc_ops_e.svc_sound:
			CL_ParseStartSoundPacket()
		elif cmdval == common_h.svc_ops_e.svc_spawnbaseline:
			CL_ParseBaseline ()
		elif cmdval == common_h.svc_ops_e.svc_temp_entity:
			cl_tent.CL_ParseTEnt ()
		elif cmdval == common_h.svc_ops_e.svc_muzzleflash:
			cl_fx.CL_ParseMuzzleFlash ()
		elif cmdval == common_h.svc_ops_e.svc_muzzleflash2:
			cl_fx.CL_ParseMuzzleFlash2 ()
		elif cmdval == common_h.svc_ops_e.svc_download:
			CL_ParseDownload ()
		elif cmdval == common_h.svc_ops_e.svc_frame:
			cl_ents.CL_ParseFrame ()
		elif cmdval == common_h.svc_ops_e.svc_inventory:
			cl_inv.CL_ParseInventory ()
		elif cmdval == common_h.svc_ops_e.svc_layout:
			s = movemsg.MSG_ReadString(net_chan.net_message)
			cl_main.cl.layout = s
		elif cmdval in [common_h.svc_ops_e.svc_playerinfo, common_h.svc_ops_e.svc_packetentities, common_h.svc_ops_e.svc_deltapacketentities]:
			clientserver.Com_Error (common_h.ERR_DROP, "Out of place frame data")
		else:
			clientserver.Com_Error (common_h.ERR_DROP,"CL_ParseServerMessage: Illegible server message\n")
	cl_scrn.CL_AddNetgraph ()

	#
	# we don't know if it is ok to save a demo message until
	# after we have parsed the frame
	#
	if cl_main.cls.demorecording and not cl_main.cls.demowaiting:
		cl_main.CL_WriteDemoMessage ()
