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

This file implements the game media download from the server

=======================================================================
"""
from __future__ import annotations

from client import cl_view, cl_parse
from common.header import common as common_h
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import filesystem
from common import movemsg
from common import collision
from server import sv_main
from client import cl_main
from client import cl_parse
from client import cl_view
from client.header import client as client_h

"""
#include "header/client.h"
"""

PLAYER_MULT = 5

# ENV_CNT is map load, ENV_CNT+1 is first env map
ENV_CNT = (shared.CS_PLAYERSKINS + shared.MAX_CLIENTS * PLAYER_MULT)
TEXTURE_CNT = (ENV_CNT+13)

env_suf = ["rt", "bk", "lf", "ft", "up", "dn"] #static const char *[6]

def CL_RequestNextDownload ():

	pass

	#unsigned	map_checksum;		// for detecting cheater maps
	#char fn[MAX_OSPATH];
	#dmdl_t *pheader;

	if cl_main.cls.state != client_h.connstate_t.ca_connected:
		return

	if not sv_main.allow_download.value and cl_main.precache_check < ENV_CNT:
		cl_main.precache_check = ENV_CNT

#ZOID
	if cl_main.precache_check == shared.CS_MODELS: # confirm map
		cl_main.precache_check = shared.CS_MODELS+2 # 0 isn't used
		if sv_main.allow_download_maps.value:
			if not CL_CheckOrDownloadFile(cl_main.cl.configstrings[shared.CS_MODELS+1]):
				return # started a download
	
	if cl_main.precache_check >= shared.CS_MODELS and cl_main.precache_check < shared.CS_MODELS+shared.MAX_MODELS:
		if sv_main.allow_download_models.value:
			while (cl_main.precache_check < shared.CS_MODELS+shared.MAX_MODELS and
				cl_main.cl.configstrings[cl_main.precache_check]):
				if (cl_main.cl.configstrings[cl_main.precache_check][0] == '*' or
					cl_main.cl.configstrings[cl_main.precache_check][0] == '#'):
					cl_main.precache_check += 1
					continue
				
				if cl_main.precache_model_skin == 0:
					if not CL_CheckOrDownloadFile(cl_main.cl.configstrings[cl_main.precache_check]):
						cl_main.precache_model_skin = 1
						return # started a download
					
					cl_main.precache_model_skin = 1
				
				# checking for skins in the model
				if cl_main.precache_model is None:

					length, cl_main.precache_model = filesystem.FS_LoadFile (cl_main.cl.configstrings[cl_main.precache_check])
					if cl_main.precache_model is None:
						cl_main.precache_model_skin = 0
						cl_main.precache_check += 1
						continue # couldn't load it
					
					if shared_c.LittleLong(cl_main.precache_model[:4]) != files_h.IDALIASHEADER:
						# not an alias model
						filesystem.FS_FreeFile(cl_main.precache_model)
						cl_main.precache_model = None
						cl_main.precache_model_skin = 0
						cl_main.precache_check += 1
						continue
					
					pheader = files_h.dmdl_t() # (dmdl_t *)precache_model
					pheader.load(cl_main.precache_model)
					if pheader.version != files_h.ALIAS_VERSION: # LittleLong (pheader->version)
						cl_main.precache_check += 1
						cl_main.precache_model_skin = 0
						continue # couldn't load it
					
				pheader = files_h.dmdl_t() # (dmdl_t *)precache_model
				pheader.load(cl_main.precache_model)

				while cl_main.precache_model_skin - 1 < pheader.num_skins: # LittleLong(pheader->num_skins)
					skin_ofs = pheader.ofs_skins + (cl_main.precache_model_skin - 1)*files_h.MAX_SKINNAME # (char *)precache_model + LittleLong(pheader->ofs_skins) + (precache_model_skin - 1)*MAX_SKINNAME
					skinname = bytes(cl_main.precache_model[skin_ofs:skin_ofs+files_h.MAX_SKINNAME]).split(b"\0")[0].decode('latin-1')
					if not CL_CheckOrDownloadFile(skinname):
						cl_main.precache_model_skin += 1
						return # started a download
					
					cl_main.precache_model_skin += 1
				
				if cl_main.precache_model is not None: 
					filesystem.FS_FreeFile(cl_main.precache_model)
					cl_main.precache_model = None
				
				cl_main.precache_model_skin = 0
				cl_main.precache_check += 1
			
		cl_main.precache_check = shared.CS_SOUNDS
	
	if cl_main.precache_check >= shared.CS_SOUNDS and cl_main.precache_check < shared.CS_SOUNDS+shared.MAX_SOUNDS: 
		if sv_main.allow_download_sounds.value:
			if cl_main.precache_check == shared.CS_SOUNDS:
				cl_main.precache_check += 1 # zero is blank
			while (cl_main.precache_check < shared.CS_SOUNDS+shared.MAX_SOUNDS and
				cl_main.cl.configstrings[cl_main.precache_check]):
				if cl_main.cl.configstrings[cl_main.precache_check][0] == '*':
					cl_main.precache_check += 1
					continue
				
				fn = "sound/{}".format(cl_main.cl.configstrings[cl_main.precache_check])
				cl_main.precache_check += 1
				if not CL_CheckOrDownloadFile(fn):
					return # started a download
			
		cl_main.precache_check = shared.CS_IMAGES
	
	if cl_main.precache_check >= shared.CS_IMAGES and cl_main.precache_check < shared.CS_IMAGES+shared.MAX_IMAGES:
		if cl_main.precache_check == shared.CS_IMAGES:
			cl_main.precache_check += 1 # zero is blank
		while (cl_main.precache_check < shared.CS_IMAGES+shared.MAX_IMAGES and
			cl_main.cl.configstrings[cl_main.precache_check]):
			fn = "pics/{}.pcx".format(cl_main.cl.configstrings[cl_main.precache_check])
			cl_main.precache_check += 1
			if not CL_CheckOrDownloadFile(fn):
				return # started a download
		
		cl_main.precache_check = shared.CS_PLAYERSKINS
	
	# skins are special, since a player has three things to download:
	# model, weapon model and skin
	# so precache_check is now *3
	if cl_main.precache_check >= shared.CS_PLAYERSKINS and cl_main.precache_check < shared.CS_PLAYERSKINS + shared.MAX_CLIENTS * PLAYER_MULT:
		if sv_main.allow_download_players.value:
			while cl_main.precache_check < shared.CS_PLAYERSKINS + shared.MAX_CLIENTS * PLAYER_MULT:
				#int i, n;
				#char model[MAX_QPATH], skin[MAX_QPATH], *p;

				i = (cl_main.precache_check - shared.CS_PLAYERSKINS)//PLAYER_MULT
				n = (cl_main.precache_check - shared.CS_PLAYERSKINS)%PLAYER_MULT

				if not cl_main.cl.configstrings[shared.CS_PLAYERSKINS+i]:
					cl_main.precache_check = shared.CS_PLAYERSKINS + (i + 1) * PLAYER_MULT
					continue
				
				p = cl_main.cl.configstrings[shared.CS_PLAYERSKINS+i].find('\\')
				if p != -1:
					p += 1
				else:
					p = 0
				model = cl_main.cl.configstrings[shared.CS_PLAYERSKINS+i][p:]
				p = model.find('/')
				if p == -1:
					p = model.find('\\')
				if p != -1:
					skin = model[p+1:]
					model = model[:p] # *p++ = 0;
				else:
					skin = ""

				# switch (n) with each case falling through to the next
				if n == 0: # model
					fn = "players/{}/tris.md2".format(model)
					if not CL_CheckOrDownloadFile(fn):
						cl_main.precache_check = shared.CS_PLAYERSKINS + i * PLAYER_MULT + 1
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 1: # weapon model
					fn = "players/{}/weapon.md2".format(model)
					if not CL_CheckOrDownloadFile(fn):
						cl_main.precache_check = shared.CS_PLAYERSKINS + i * PLAYER_MULT + 2
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 2: # weapon skin
					fn = "players/{}/weapon.pcx".format(model)
					if not CL_CheckOrDownloadFile(fn):
						cl_main.precache_check = shared.CS_PLAYERSKINS + i * PLAYER_MULT + 3
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 3: # skin
					fn = "players/{}/{}.pcx".format(model, skin)
					if not CL_CheckOrDownloadFile(fn):
						cl_main.precache_check = shared.CS_PLAYERSKINS + i * PLAYER_MULT + 4
						return # started a download
					
					n += 1
					#FALL THROUGH

				if n == 4: # skin_i
					fn = "players/{}/{}_i.pcx".format(model, skin)
					if not CL_CheckOrDownloadFile(fn):
						cl_main.precache_check = shared.CS_PLAYERSKINS + i * PLAYER_MULT + 5
						return # started a download
					
					# move on to next model
					cl_main.precache_check = shared.CS_PLAYERSKINS + (i + 1) * PLAYER_MULT
				
		# precache phase completed
		cl_main.precache_check = ENV_CNT
	
	if cl_main.precache_check == ENV_CNT:
		cl_main.precache_check = ENV_CNT + 1

		_, map_checksum = collision.CM_LoadMap (cl_main.cl.configstrings[shared.CS_MODELS+1], True)

		if map_checksum != (shared_c.atoi(cl_main.cl.configstrings[shared.CS_MAPCHECKSUM]) & 0xffffffff): # atoi's int is converted to unsigned for the compare
			clientserver.Com_Error (shared.ERR_DROP, "Local map version differs from server: {} != '{}'\n".format(
				map_checksum, cl_main.cl.configstrings[shared.CS_MAPCHECKSUM]))
			return
		
	if cl_main.precache_check > ENV_CNT and cl_main.precache_check < TEXTURE_CNT:
		if sv_main.allow_download.value and sv_main.allow_download_maps.value:
			while cl_main.precache_check < TEXTURE_CNT:
				n = cl_main.precache_check - ENV_CNT - 1
				cl_main.precache_check += 1

				if n & 1:
					fn = "env/{}{}.pcx".format( 
						cl_main.cl.configstrings[shared.CS_SKY], env_suf[n//2])
				else:
					fn = "env/{}{}.tga".format( 
						cl_main.cl.configstrings[shared.CS_SKY], env_suf[n//2])
				if not CL_CheckOrDownloadFile(fn):
					return # started a download
			
		cl_main.precache_check = TEXTURE_CNT
	
	if cl_main.precache_check == TEXTURE_CNT:
		cl_main.precache_check = TEXTURE_CNT+1
		cl_main.precache_tex = 0
	
	# confirm existance of textures, download any that don't exist
	if cl_main.precache_check == TEXTURE_CNT+1:
		# from qcommon/cmodel.c
		#extern int			numtexinfo;
		#extern mapsurface_t	map_surfaces[];

		if sv_main.allow_download.value and sv_main.allow_download_maps.value:
			while cl_main.precache_tex < collision.numtexinfo:
				#char fn[MAX_OSPATH];

				fn = "textures/{}.wal".format(collision.map_surfaces[cl_main.precache_tex].rname)
				cl_main.precache_tex += 1
				if not CL_CheckOrDownloadFile(fn):
					return # started a download
			
		cl_main.precache_check = TEXTURE_CNT+999
	
#ZOID
	cl_parse.CL_RegisterSounds ()
	cl_view.CL_PrepRefresh ()

	movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value)
	movemsg.MSG_WriteString (cl_main.cls.netchan.message, "begin {}\n".format(cl_main.precache_spawncount).encode('ascii') )

import os
from client import cl_main
from common.header import common as common_h
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import filesystem
from common import movemsg
from common import szone
from common import netchan
from client import cl_main
from client import cl_parse

#=====================================

def CL_DownloadFileName(fn): #char * (returns char *dest)

	if fn[:7] == "players":
		dest = "{}/{}".format(common_h.BASEDIRNAME, fn)
	else:
		dest = "{}/{}".format(filesystem.FS_Gamedir(), fn)
	return dest

r"""
/*
 * Returns true if a file is filtered and
 * should not be downloaded, false otherwise.
 */
static qboolean
CL_DownloadFilter(const char *filename)
{
	size_t i;
	static const char *extensions[] = {
		".dll",
		".dylib",
		".lib",
		".so",
		".a",
		NULL,
	};

	if ((*filename == '.') || (*filename == '/') || strchr(filename, ':') || strstr(filename, ".."))
	{
		Com_Printf("Refusing to download a path containing '..' or ':' or starting with '.' or '/': %s\n", filename);
		return true;
	}

	for (i = 0; extensions[i]; i++)
	{
		if (strstr(filename, extensions[i]))
		{
			Com_Printf("Refusing to download a path containing '%s': %s\n", extensions[i], filename);
			return true;
		}
	}

	char *nodownload = strdup(cl_nodownload_list->string);
	char *nodownload_token = strtok(nodownload, " ");
	while (nodownload_token != NULL)
	{
		Com_Printf("Token: %s\n", nodownload_token);
		if (Q_strcasestr(filename, nodownload_token))
		{
			Com_Printf("Filename is filtered by cl_nodownload_list: %s\n", filename);
			free(nodownload);
			return true;
		}
		nodownload_token = strtok(NULL, " ");
	}
	free(nodownload);

	if (FS_FileExists(filename))
	{
		/* it exists, no need to download */
		return true;
	}

	return false;
}
"""

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
	size = movemsg.MSG_ReadShort (netchan.net_message)
	percent = movemsg.MSG_ReadByte (netchan.net_message)
	if size == -1:
	
		clientserver.Com_Printf ("Server does not have this file.\n")
		if cl_main.cls.download is not None:
		
			# if here, we tried to resume a file but the server said no
			cl_main.cls.download.close ()
			cl_main.cls.download = None
		
		CL_RequestNextDownload ()
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
		
			netchan.net_message.readcount += size
			clientserver.Com_Printf ("Failed to open {}\n".format(cl_main.cls.downloadtempname))
			CL_RequestNextDownload ()
			return
		
	cl_main.cls.download.write (netchan.net_message.data[netchan.net_message.readcount:netchan.net_message.readcount + size])
	netchan.net_message.readcount += size

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

		CL_RequestNextDownload ()
