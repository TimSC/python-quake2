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
import numpy as np
try:
	import cl_cin_extras
except ModuleNotFoundError:
	from client import cl_cin_extras
from client import cl_main, cl_scrn, client, snd_dma
from qcommon import files, cvar, common, qcommon, qfiles
from game import q_shared
from linux import q_shlinux, vid_so, cd_linux
"""
#include "client.h"

typedef struct
{
	byte	*data;
	int		count;
} cblock_t;
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
		self.hnodes1tree = None

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
	length, raw = files.FS_LoadFile (filename)
	if raw is None:
		return None, None, None, None	# Com_Printf ("Bad pcx file %s\n", filename);

	#
	# parse the PCX file
	#
	pcx = qfiles.pcx_t()
	pcx.Read(raw) # pcx = (pcx_t *)raw;
	data = pcx.data # raw = &pcx->data;
	r = 0 # index into data

	if (pcx.manufacturer != 0x0a
		or pcx.version != 5
		or pcx.encoding != 1
		or pcx.bits_per_pixel != 8
		or pcx.xmax >= 640
		or pcx.ymax >= 480):
	
		common.Com_Printf ("Bad pcx file {}\n".format(filename))
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
	
		common.Com_Printf ("PCX file {} was malformed".format(filename))
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
	
	if cl_main.cl.cinematic_file is not None:
		cl_main.cl.cinematic_file = None

	if cin.hnodes1 is not None:
	
		cin.hnodes1 = None
		cin.hnodes1tree = None
		cin.hnodes1vals = None
		cin.hnodes1leaf = None
		cin.numhnodes1 = None

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
	common.MSG_WriteByte (cl_main.cls.netchan.message, qcommon.clc_ops_e.clc_stringcmd.value.to_bytes(1, 'big'))
	common.SZ_Print (cl_main.cls.netchan.message, "nextserver {}\n".format(cl_main.cl.servercount))


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

	cin.hnodes1 = [0] * (256*256*2*4)
	cin.numhnodes1 = np.zeros((256,), dtype=np.int16) #int[256] Mapping from previous pixel to specalized huff tree


	for prev in range(256):
	
		cin.h_count = [0]*512
		cin.h_used = [0]*512

		# read a row of counts
		counts = files.FS_Read (256, cl_main.cl.cinematic_file)
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

	#Convert to higher level (cython friendly) representation
	cin.hnodes1tree = np.empty((256, 256, 2), dtype=np.uint8) # Node tree
	cin.hnodes1vals = np.zeros((256, 256, 2), dtype=np.uint8) # Leaf node values
	cin.hnodes1leaf = np.zeros((256, 256, 2), dtype=np.uint8) # Indicates if node is a leaf node

	for prevpixel in range(256):

		for nodenum in range(256):
			leftRightNextNode = [cin.hnodes1[prevpixel * 512 + nodenum * 2 + 0],
				cin.hnodes1[prevpixel * 512 + nodenum * 2 + 1]]

			if leftRightNextNode[0] < 0:
				leftRightNextNode[0] = 0
			elif leftRightNextNode[0] < 256:
				cin.hnodes1vals[prevpixel][nodenum][0] = leftRightNextNode[0]
				leftRightNextNode[0] = 0
				cin.hnodes1leaf[prevpixel][nodenum][0] = 1
			else:
				leftRightNextNode[0] -= 256

			if leftRightNextNode[1] < 0:
				leftRightNextNode[1] = 0
			elif leftRightNextNode[1] < 256:
				cin.hnodes1vals[prevpixel][nodenum][1] = leftRightNextNode[1]
				leftRightNextNode[1] = 0
				cin.hnodes1leaf[prevpixel][nodenum][1] = 1
			else:
				leftRightNextNode[1] -= 256

			cin.hnodes1tree[prevpixel][nodenum][:] = leftRightNextNode

	cin.numhnodes1 -= 256
	cin.numhnodes1 = np.array(cin.numhnodes1, dtype=np.uint8)


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
		command = cl_main.cl.cinematic_file.read(4)
	except:
		try:
			# we'll give it one more chance
			command = cl_main.cl.cinematic_file.read(4)
		except:
			return None

	command = q_shared.LittleLong(command)
	if command == 2:
		return None	# last frame marker

	if command == 1:
		# read palette
		cl_main.cl.cinematicpalette = files.FS_Read (768, cl_main.cl.cinematic_file)
		cl_main.cl.cinematicpalette_active=False	# dubious....  exposes an edge case
	

	# decompress the next frame
	size = files.FS_Read (4, cl_main.cl.cinematic_file)
	size = q_shared.LittleLong(size)
	if size > 0x20000 or size < 1:
		common.Com_Error (ERR_DROP, "Bad compressed frame size")
	compressed = files.FS_Read (size, cl_main.cl.cinematic_file)

	# read sound
	start = cl_main.cl.cinematicframe*cin.s_rate//14
	end = (cl_main.cl.cinematicframe+1)*cin.s_rate//14
	count = end - start

	samples = files.FS_Read (count*cin.s_width*cin.s_channels, cl_main.cl.cinematic_file)

	snd_dma.S_RawSamples (count, cin.s_rate, cin.s_width, cin.s_channels, samples)

	in_blk = bytes(compressed)

	huf1 = cl_cin_extras.Huff1Decompress (in_blk, cin.hnodes1tree, cin.hnodes1vals, cin.hnodes1leaf, cin.numhnodes1)

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

	if cl_main.cls.key_dest != client.keydest_t.key_game:
		# pause if menu or console is up
		cl_main.cl.cinematictime = cl_main.cls.realtime - cl_main.cl.cinematicframe*1000//14
		return
	
	frame = (cl_main.cls.realtime - cl_main.cl.cinematictime)*14.0/1000
	if frame <= cl_main.cl.cinematicframe:
		return
	if frame > cl_main.cl.cinematicframe+1:
	
		common.Com_Printf ("Dropped frame: {} > {}\n".format(frame, cl_main.cl.cinematicframe+1))
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
		cl_scrn.SCR_BeginLoadingPlaque ()
		cl_main.cl.cinematictime = 0
		return
	


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
	

	if cl_main.cls.key_dest == client.keydest_t.key_menu:
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
		cl_scrn.SCR_EndLoadingPlaque ()
		cl_main.cls.state = client.connstate_t.ca_active
		if cin.pic is None:
		
			common.Com_Printf ("{} not found.\n".format(name))
			cl_main.cl.cinematictime = 0
		
		else:
			cl_main.cl.cinematicpalette = palette
			
		return

	name = "video/{}".format(arg)
	file_length, cl_main.cl.cinematic_file = files.FS_FOpenFile (name)
	if cl_main.cl.cinematic_file is None:
	
#		Com_Error (ERR_DROP, "Cinematic %s not found.\n", name);
		SCR_FinishCinematic ()
		cl_main.cl.cinematictime = 0	# done
		return
	
	cl_scrn.SCR_EndLoadingPlaque ()

	cl_main.cls.state = client.connstate_t.ca_active

	width = files.FS_Read (4, cl_main.cl.cinematic_file)
	height = files.FS_Read (4, cl_main.cl.cinematic_file)
	cin.width = q_shared.LittleLong(width)
	cin.height = q_shared.LittleLong(height)

	cin.s_rate = files.FS_Read (4, cl_main.cl.cinematic_file)
	cin.s_rate = q_shared.LittleLong(cin.s_rate)
	cin.s_width = files.FS_Read (4, cl_main.cl.cinematic_file)
	cin.s_width = q_shared.LittleLong(cin.s_width)
	cin.s_channels = files.FS_Read (4, cl_main.cl.cinematic_file)
	cin.s_channels = q_shared.LittleLong(cin.s_channels)

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

