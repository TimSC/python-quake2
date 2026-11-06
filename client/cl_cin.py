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

This file implements the .cin video codec and the corresponding .pcx
bitmap decoder. .cin files are just a bunch of .pcx images.

=======================================================================
"""
from __future__ import annotations

import os
import struct
from client import cl_main, snd_dma
from linux import q_shlinux, vid_so, cd_linux
from common.header import common as common_h
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cvar
from common import filesystem
from common import movemsg
from common import szone
from client import cl_main
from client import cl_screen
from client.header import client as client_h

"""
#include "header/client.h"
#include "input/header/input.h"
"""

class cinematics_t(object):
	def __init__(self):

		self.restart_sound=False # qboolean
		self.s_rate = None #int
		self.s_width = None #int
		self.s_channels = None #int

		self.width = None #int
		self.height = None #int

		self.pic = None #byte *
		self.pic_pending = None #byte *

		# order 1 huffman stuff
		self.hnodes1 = None #int * // [256][256][2]
		self.numhnodes1 = None #int[256]

		self.h_used = None #int[512]
		self.h_count = None #int[512]


cin = cinematics_t()

"""
=================================================================

PCX LOADING

=================================================================
"""


"""
==============
SCR_LoadPCX
==============
"""
def SCR_LoadPCX (filename): # char * (byte **pic, byte **palette, int *width, int *height)

	"""
	byte	*raw;
	pcx_t	*pcx;
	int		x, y;
	int		len;
	int		dataByte, runLength;
	byte	*out, *pix;
	"""

	pic = None

	#
	# load the file
	#
	length, raw = filesystem.FS_LoadFile (filename)
	if raw is None:
		return None, None, None, None	# Com_Printf ("Bad pcx file %s\n", filename);

	#
	# parse the PCX file
	#
	pcx = files_h.pcx_t()
	pcx.Read(raw) # pcx = (pcx_t *)raw;
	data = pcx.data # raw = &pcx->data;
	r = 0 # index into data

	if (pcx.manufacturer != 0x0a
		or pcx.version != 5
		or pcx.encoding != 1
		or pcx.bits_per_pixel != 8
		or pcx.xmax >= 640
		or pcx.ymax >= 480):
	
		clientserver.Com_Printf ("Bad pcx file {}\n".format(filename))
		return None, None, None, None
	
	out = bytearray ( (pcx.ymax+1) * (pcx.xmax+1) )

	pic = out

	pix = 0 # index into out

	palette = bytes(raw[length - 768:length]) # memcpy (*palette, (byte *)pcx + len - 768, 768);
	
	width = pcx.xmax+1
	height = pcx.ymax+1

	for y in range(pcx.ymax+1):
	
		x = 0
		while x<=pcx.xmax:
		
			dataByte = data[r]
			r += 1

			if (dataByte & 0xC0) == 0xC0:
			
				runLength = dataByte & 0x3F
				dataByte = data[r]
				r += 1
			
			else:
				runLength = 1

			while runLength > 0:
				runLength -= 1
				out[pix + x] = dataByte
				x += 1
		
		pix += pcx.xmax+1

	if r + 128 > length: # raw - (byte *)pcx > len
	
		clientserver.Com_Printf ("PCX file {} was malformed".format(filename))
		pic = None
	
	return pic, palette, width, height

"""
//=============================================================

/*
==================
SCR_StopCinematic
==================
"""
def SCR_StopCinematic ():
	
	global cin
	
	cl_main.cl.cinematictime = 0	# done
	
	if cin.pic is not None:
		cin.pic = None
	
	if cin.pic_pending is not None:
		cin.pic_pending = None
	
	if cl_main.cl.cinematicpalette_active:
	
		vid_so.re.CinematicSetPalette(None)
		cl_main.cl.cinematicpalette_active = False
	
	if cl_main.cl.cinematic_file:
		filesystem.FS_FCloseFile (cl_main.cl.cinematic_file)
		cl_main.cl.cinematic_file = 0

	if cin.hnodes1 is not None:
	
		cin.hnodes1 = None	# Z_Free (cin.hnodes1);

	# switch back down to 11 khz sound if necessary
	if cin.restart_sound:
	
		cin.restart_sound = False
		cl_main.CL_Snd_Restart_f ()
	


"""
====================
SCR_FinishCinematic

Called when either the cinematic completes, or it is aborted
====================
"""
def SCR_FinishCinematic ():

	# tell the server to advance to the next map / cinematic
	movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_stringcmd.value.to_bytes(1, 'big'))
	szone.SZ_Print (cl_main.cls.netchan.message, "nextserver {}\n".format(cl_main.cl.servercount))


"""
//==========================================================================

/*
==================
SmallestNode1
==================
"""
def	SmallestNode1 (numhnodes): #int

	#int		i;
	#int		best, bestnode;

	best = 99999999
	bestnode = -1
	for i in range(numhnodes):
	
		if cin.h_used[i]:
			continue
		if not cin.h_count[i]:
			continue
		if cin.h_count[i] < best:
		
			best = cin.h_count[i]
			bestnode = i

	if bestnode == -1:
		return -1

	cin.h_used[bestnode] = True
	return bestnode


"""
==================
Huff1TableInit

Reads the 64k counts table and initializes the node trees
==================
"""
def Huff1TableInit ():

	global cin
	"""
	int		prev;
	int		j;
	int		*node, *nodebase;
	byte	counts[256];
	int		numhnodes;
	"""

	cin.hnodes1 = [0] * (256*256*2) # Z_Malloc (256*256*2*4); memset (cin.hnodes1, 0, 256*256*2*4);
	cin.numhnodes1 = [0] * 256 #int[256]


	for prev in range(256):
	
		cin.h_count = [0]*512
		cin.h_used = [0]*512

		# read a row of counts
		counts = filesystem.FS_Read (256, cl_main.cl.cinematic_file)
		for j in range(256):
			cin.h_count[j] = counts[j]

		# build the nodes
		numhnodes = 256
		nodebase = prev * 256 * 2

		while numhnodes != 511:
		
			node = nodebase + (numhnodes - 256) * 2

			# pick two lowest counts
			v1 = SmallestNode1(numhnodes)
			cin.hnodes1[node+0] = v1
			if v1 == -1:
				break	# no more

			v2 = SmallestNode1(numhnodes)
			cin.hnodes1[node+1] = v2
			if v2 == -1:
				break

			cin.h_count[numhnodes] = cin.h_count[v1] + cin.h_count[v2]
			numhnodes+=1
		

		cin.numhnodes1[prev] = numhnodes-1


"""
==================
Huff1Decompress
==================
"""
def Huff1Decompress (in_data): #cblock_t (returns cblock_t)

	"""
	byte		*input;
	byte		*out_p;
	int			nodenum;
	int			count;
	cblock_t	out;
	int			inbyte;
	int			*hnodes, *hnodesbase;
	"""
	hnodes1 = cin.hnodes1
	numhnodes1 = cin.numhnodes1

	# get decompressed count
	count = in_data[0] + (in_data[1]<<8) + (in_data[2]<<16) + (in_data[3]<<24)
	input_p = 4
	out = bytearray(count) # out_p = out.data = Z_Malloc (count);
	out_p = 0

	# read bits

	hnodesbase = -256*2	# nodes 0-255 aren't stored

	hnodes = hnodesbase
	nodenum = numhnodes1[0]
	while count:
	
		# Q2PORT: reading past the end of the block gives zero bits
		inbyte = in_data[input_p] if input_p < len(in_data) else 0
		input_p += 1
		# Q2PORT: the C repeats this block once per bit, 8 times
		for bit in range(8):
			#-----------
			if nodenum < 256:
			
				hnodes = hnodesbase + (nodenum<<9)
				out[out_p] = nodenum
				out_p += 1
				count -= 1
				if not count:
					break
				nodenum = numhnodes1[nodenum]
			
			nodenum = hnodes1[hnodes + nodenum*2 + (inbyte&1)]
			inbyte >>=1
	

	if input_p != len(in_data) and input_p != len(in_data)+1:
	
		clientserver.Com_Printf ("Decompression overread by %i", input_p - len(in_data))
	
	#out.count = out_p - out.data;

	return bytes(out[:out_p])


"""
==================
SCR_ReadNextFrame
==================
"""
def SCR_ReadNextFrame (): #byte *

	"""
	int		r;
	int		command;
	byte	samples[22050/14*4];
	byte	compressed[0x20000];
	int		size;
	byte	*pic;
	cblock_t	in_blk, huf1;
	int		start, end, count;
	"""

	# read the next frame
	try:
		command = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	except:
		try:
			# we'll give it one more chance
			command = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
		except:
			return None

	command = shared_c.LittleLong(command)
	if command == 2:
		return None	# last frame marker

	if command == 1:
		# read palette
		cl_main.cl.cinematicpalette = filesystem.FS_Read (768, cl_main.cl.cinematic_file)
		cl_main.cl.cinematicpalette_active=False	# dubious....  exposes an edge case
	

	# decompress the next frame
	size = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	size = shared_c.LittleLong(size)
	if size > 0x20000 or size < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Bad compressed frame size")
	compressed = filesystem.FS_Read (size, cl_main.cl.cinematic_file)

	# read sound
	start = cl_main.cl.cinematicframe*cin.s_rate//14
	end = (cl_main.cl.cinematicframe+1)*cin.s_rate//14
	count = end - start

	samples = filesystem.FS_Read (count*cin.s_width*cin.s_channels, cl_main.cl.cinematic_file)

	snd_dma.S_RawSamples (count, cin.s_rate, cin.s_width, cin.s_channels, samples)

	in_blk = bytes(compressed)

	huf1 = Huff1Decompress (in_blk)

	pic = huf1

	cl_main.cl.cinematicframe+=1

	return pic


"""
==================
SCR_RunCinematic

==================
"""
def SCR_RunCinematic ():

	global cin
	#int		frame;

	if cl_main.cl.cinematictime <= 0:
	
		SCR_StopCinematic ()
		return
	
	if cl_main.cl.cinematicframe == -1:
		return		# static image

	if cl_main.cls.key_dest != client_h.keydest_t.key_game:
		# pause if menu or console is up
		cl_main.cl.cinematictime = cl_main.cls.realtime - cl_main.cl.cinematicframe*1000//14
		return
	
	frame = (cl_main.cls.realtime - cl_main.cl.cinematictime)*14.0/1000
	if frame <= cl_main.cl.cinematicframe:
		return
	if frame > cl_main.cl.cinematicframe+1:
	
		clientserver.Com_Printf ("Dropped frame: {} > {}\n".format(frame, cl_main.cl.cinematicframe+1))
		cl_main.cl.cinematictime = cl_main.cls.realtime - cl_main.cl.cinematicframe*1000//14
	
	if cin.pic is not None:
		cin.pic = None
	
	cin.pic = cin.pic_pending
	cin.pic_pending = None
	cin.pic_pending = SCR_ReadNextFrame ()

	if not cin.pic_pending:
	
		SCR_StopCinematic ()
		SCR_FinishCinematic ()
		cl_main.cl.cinematictime = 1	# hack to get the black screen behind loading
		cl_screen.SCR_BeginLoadingPlaque ()
		cl_main.cl.cinematictime = 0
		return
	


"""
static int
SCR_MinimalColor(void)
{
	int i, min_color, min_index;

	min_color = 255 * 3;
	min_index = 0;

	for(i=0; i<255; i++)
	{
		int current_color = (cl.cinematicpalette[i*3+0] +
				     cl.cinematicpalette[i*3+1] +
				     cl.cinematicpalette[i*3+2]);

		if (min_color > current_color)
		{
			min_color = current_color;
			min_index = i;
		}
	}

	return min_index;
}
"""

"""
==================
SCR_DrawCinematic

Returns true if a cinematic is active, meaning the view rendering
should be skipped
==================
"""
def SCR_DrawCinematic (): #(qboolean)

	
	if cl_main.cl.cinematictime <= 0:
	
		return False
	

	if cl_main.cls.key_dest == client_h.keydest_t.key_menu:
		# blank screen and pause if menu is up
		vid_so.re.CinematicSetPalette(None)
		cl_main.cl.cinematicpalette_active = False
		return True
	

	if not cl_main.cl.cinematicpalette_active:
	
		vid_so.re.CinematicSetPalette(cl_main.cl.cinematicpalette)
		cl_main.cl.cinematicpalette_active = True
	

	if cin.pic is None:
		return True

	vid_so.re.DrawStretchRaw (0, 0, vid_so.viddef.width, vid_so.viddef.height,
		cin.width, cin.height, cin.pic)

	return True


"""
static byte *
SCR_LoadHiColor(const char* namewe, const char *ext, int *width, int *height,
	byte **palette, int *bitsPerPixel)
{
	byte *pic, *data = NULL, *palette_in = NULL;
	char filename[256];

	Q_strlcpy(filename, namewe, sizeof(filename));
	Q_strlcat(filename, ".", sizeof(filename));
	Q_strlcat(filename, ext, sizeof(filename));

	SCR_LoadImageWithPalette(filename, &data, &palette_in,
		width, height, bitsPerPixel);
	if (data == NULL)
	{
		return NULL;
	}

	if (palette_in)
	{
		/* pcx file could have palette */
		*palette = Z_Malloc(768);
		memcpy(*palette, palette_in, 768);
		free(palette_in);
	}

	pic = Z_Malloc(cin.height * cin.width * (*bitsPerPixel) / 8);
	memcpy(pic, data, cin.height * cin.width * (*bitsPerPixel) / 8);
	free(data);

	return pic;
}
"""

"""
==================
SCR_PlayCinematic

==================
"""
def SCR_PlayCinematic (arg): # char *

	global cin
	"""
	int		width, height;
	byte	*palette;
	char	name[MAX_OSPATH], *dot;
	int		old_khz;
	"""
	# make sure CD isn't playing music
	cd_linux.CDAudio_Stop()

	cl_main.cl.cinematicframe = 0
	#dot = strstr (arg, ".")
	arg_split = os.path.splitext(arg)
	if len(arg_split) >= 2:
		dot = arg_split[1]
	else:
		dot = None

	
	if dot == ".pcx":
		
		# static pcx image
		name = "pics/{}".format(arg)
		cin.pic, palette, cin.width, cin.height = SCR_LoadPCX (name)
		cl_main.cl.cinematicframe = -1
		cl_main.cl.cinematictime = 1
		cl_screen.SCR_EndLoadingPlaque ()
		cl_main.cls.state = client_h.connstate_t.ca_active
		if cin.pic is None:
		
			clientserver.Com_Printf ("{} not found.\n".format(name))
			cl_main.cl.cinematictime = 0
		
		else:
			cl_main.cl.cinematicpalette = palette
			
		return

	name = "video/{}".format(arg)
	file_length, cl_main.cl.cinematic_file = filesystem.FS_FOpenFile (name)
	if not cl_main.cl.cinematic_file:
	
#		Com_Error (ERR_DROP, "Cinematic %s not found.\n", name);
		SCR_FinishCinematic ()
		cl_main.cl.cinematictime = 0	# done
		return
	
	cl_screen.SCR_EndLoadingPlaque ()

	cl_main.cls.state = client_h.connstate_t.ca_active

	width = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	height = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	cin.width = shared_c.LittleLong(width)
	cin.height = shared_c.LittleLong(height)

	cin.s_rate = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	cin.s_rate = shared_c.LittleLong(cin.s_rate)
	cin.s_width = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	cin.s_width = shared_c.LittleLong(cin.s_width)
	cin.s_channels = filesystem.FS_Read (4, cl_main.cl.cinematic_file)
	cin.s_channels = shared_c.LittleLong(cin.s_channels)

	Huff1TableInit ()

	# switch up to 22 khz sound if necessary
	old_khz = cvar.Cvar_VariableValue ("s_khz")
	if old_khz != cin.s_rate//1000:
	
		cin.restart_sound = True
		cvar.Cvar_SetValue ("s_khz", cin.s_rate//1000)
		cl_main.CL_Snd_Restart_f ()
		cvar.Cvar_SetValue ("s_khz", old_khz)
	

	cl_main.cl.cinematicframe = 0
	cin.pic = SCR_ReadNextFrame ()
	cl_main.cl.cinematictime = q_shlinux.Sys_Milliseconds ()

