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

from client.sound import sound as sound_c
from backends.unix import system
from client.vid import vid
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cvar
from common import filesystem
from common import movemsg
from common import szone
from client import cl_image
from client import cl_main
from client import cl_screen
from client.input import sdl2
from client.sound import ogg
from client.vid import vid
from client.header import client as client_h

"""
#include "header/client.h"
#include "input/header/input.h"
"""

cin_force43 = None #cvar_t *
abort_cinematic = 0 #int

class cinematics_t(object):
	def __init__(self):

		self.restart_sound=False # qboolean
		self.s_rate = None #int
		self.s_width = None #int
		self.s_channels = None #int

		self.width = None #int
		self.height = None #int
		self.color_bits = None #int

		self.pic = None #byte *
		self.pic_pending = None #byte *

		# order 1 huffman stuff
		self.hnodes1 = None #int * // [256][256][2]
		self.numhnodes1 = None #int[256]

		self.h_used = None #int[512]
		self.h_count = None #int[512]


cin = cinematics_t()


"""
//=============================================================

/*
==================
SCR_StopCinematic
==================
"""
def SCR_StopCinematic(): #void

	cl_main.cl.cinematictime = 0 # done

	if cin.pic:

		cin.pic = None # Z_Free(cin.pic);


	if cin.pic_pending:

		cin.pic_pending = None # Z_Free(cin.pic_pending);


	if cl_main.cl.cinematicpalette_active:

		vid.R_SetPalette(None)
		cl_main.cl.cinematicpalette_active = False


	if cl_main.cl.cinematic_file:

		filesystem.FS_FCloseFile(cl_main.cl.cinematic_file)
		cl_main.cl.cinematic_file = 0


	if cin.hnodes1:

		cin.hnodes1 = None # Z_Free(cin.hnodes1);


	# switch back down to 11 khz sound if necessary
	if cin.restart_sound:

		cin.restart_sound = False
		cl_main.CL_Snd_Restart_f()

	


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
def Huff1Decompress(in_: bytes, in_count: int)->bytes: #cblock_t (returns static cblock_t)

	# Q2PORT: the cblock_t is the data and its count; the result is the bytes (out.data, out.count long)

	"""
	byte *input;
	byte *out_p;
	int nodenum;
	int count;
	cblock_t out;
	int inbyte;
	int *hnodes, *hnodesbase;
	"""
	hnodes1 = cin.hnodes1
	numhnodes1 = cin.numhnodes1

	# get decompressed count
	count = in_[0] + (in_[1] << 8) + (in_[2] << 16) + (in_[3] << 24)
	input_ = 4 # input = in.data + 4;
	out = bytearray(count) # out_p = out.data = Z_Malloc(count);
	out_p = 0

	# read bits
	hnodesbase = -256 * 2 # nodes 0-255 aren't stored, hnodesbase = cin.hnodes1 - 256 * 2

	hnodes = hnodesbase
	nodenum = numhnodes1[0]

	while count:

		# Q2PORT: reading past the end of the block gives zero bits
		inbyte = in_[input_] if input_ < len(in_) else 0
		input_ += 1

		for i in range(8):

			if nodenum < 256:

				hnodes = hnodesbase + (nodenum << 9)
				out[out_p] = nodenum
				out_p += 1

				count -= 1
				if not count:

					break


				nodenum = numhnodes1[nodenum]


			nodenum = hnodes1[hnodes + nodenum * 2 + (inbyte & 1)]
			inbyte >>= 1



	if (input_ != in_count) and (input_ != in_count + 1):

		clientserver.Com_Printf("Decompression overread by %i", input_ - in_count)


	#out.count = out_p - out.data;

	return bytes(out[:out_p])



"""
==================
SCR_ReadNextFrame
==================
"""
def SCR_ReadNextFrame(): # (returns static byte *)

	"""
	int r;
	int command;

	// the samples array is used as bytes or shorts, depending on bitrate (cin.s_width)
	// so we need to make sure to align it correctly
	YQ2_ALIGNAS_TYPE(short) byte samples[22050 / 14 * 4];

	byte compressed[0x20000];
	int size;
	byte *pic;
	cblock_t in, huf1;
	int start, end, count;
	"""

	# read the next frame
	command = filesystem.FS_FRead(4, 1, cl_main.cl.cinematic_file)
	r = len(command)

	if r == 0:

		# we'll give it one more chance
		command = filesystem.FS_FRead(4, 1, cl_main.cl.cinematic_file)
		r = len(command)


	if r != 4:

		return None


	command = shared_c.LittleLong(command)

	if command == 2:

		return None # last frame marker


	if command == 1:

		# read palette
		cl_main.cl.cinematicpalette = filesystem.FS_Read(768, # sizeof(cl.cinematicpalette)
				cl_main.cl.cinematic_file)
		cl_main.cl.cinematicpalette_active = 0


	# decompress the next frame
	size = filesystem.FS_Read(4, cl_main.cl.cinematic_file)
	size = shared_c.LittleLong(size)

	if (size > 0x20000) or (size < 1): # (size_t)size > sizeof(compressed)

		clientserver.Com_Error(shared.ERR_DROP, "Bad compressed frame size")


	compressed = filesystem.FS_Read(size, cl_main.cl.cinematic_file)

	# read sound
	start = int(cl_main.cl.cinematicframe * cin.s_rate / 14)
	end = int((cl_main.cl.cinematicframe + 1) * cin.s_rate / 14)
	count = end - start

	samples = filesystem.FS_Read(count * cin.s_width * cin.s_channels,
			cl_main.cl.cinematic_file)

	if cin.s_width == 2:

		# for (r = 0; r < count * cin.s_channels; r++)
		#	((short *)samples)[r] = LittleShort(((short *)samples)[r]);
		pass # Q2PORT: the samples stay little-endian bytes, which is what S_RawSamples takes


	sound_c.S_RawSamples(count, cin.s_rate, cin.s_width, cin.s_channels,
			samples, cvar.Cvar_VariableValue("s_volume"))

	in_data = compressed # in.data = compressed;
	in_count = size # in.count = size;

	huf1 = Huff1Decompress(in_data, in_count)

	pic = huf1 # huf1.data

	cl_main.cl.cinematicframe += 1

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
	
	frame = int((cl_main.cls.realtime - cl_main.cl.cinematictime)*14.0/1000)
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
	


def SCR_MinimalColor(): # (returns static int)

	"""
	int i, min_color, min_index;
	"""

	min_color = 255 * 3
	min_index = 0
	for i in range(255):

		#int current_color = (cl.cinematicpalette[i*3+0] + cl.cinematicpalette[i*3+1] + cl.cinematicpalette[i*3+2]);
		current_color = (cl_main.cl.cinematicpalette[i*3+0] + cl_main.cl.cinematicpalette[i*3+1] + cl_main.cl.cinematicpalette[i*3+2])
		if min_color > current_color:

			min_color = current_color
			min_index = i


	return min_index

"""
==================
SCR_DrawCinematic

Returns true if a cinematic is active, meaning the view rendering
should be skipped
==================
"""
def SCR_DrawCinematic(): # (returns qboolean)

	"""
	int x, y, w, h, color;
	"""

	if cl_main.cl.cinematictime <= 0:

		return False


	# blank screen and pause if menu is up
	if cl_main.cls.key_dest == client_h.keydest_t.key_menu:

		vid.R_SetPalette(None)
		cl_main.cl.cinematicpalette_active = False
		return True


	if not cl_main.cl.cinematicpalette_active:

		vid.R_SetPalette(cl_main.cl.cinematicpalette)
		cl_main.cl.cinematicpalette_active = True


	if not cin.pic:

		return True


	if cin_force43.value and cin.height and cin.width:

		# Try to left original aspect ratio
		w = int(vid.viddef.height * cin.width / cin.height) # C int
		if w > vid.viddef.width:

			w = vid.viddef.width


		w &= ~3
		h = int(w * cin.height / cin.width) # C int
		x = int((vid.viddef.width - w) / 2) # C int
		y = int((vid.viddef.height - h) / 2) # C int

	else:

		x = y = 0
		w = vid.viddef.width
		h = vid.viddef.height


	if not vid.vid_renderer:

		vid.vid_renderer = cvar.Cvar_Get("vid.vid_renderer", "gl1", shared.CVAR_ARCHIVE)


	if shared_c.Q_stricmp(vid.vid_renderer.string, "soft") == 0:

		color = SCR_MinimalColor()
		# Soft render requires to reset palette before show RGBA image
		if cin.color_bits == 32:

			vid.R_SetPalette(None)


	else:

		color = 0


	if x > 0:

		vid.Draw_Fill(0, 0, x, vid.viddef.height, color)


	if x + w < vid.viddef.width:

		vid.Draw_Fill(x + w, 0, vid.viddef.width - (x + w), vid.viddef.height, color)


	if y > 0:

		vid.Draw_Fill(x, 0, w, y, color)


	if y + h < vid.viddef.height:

		vid.Draw_Fill(x, y + h, w, vid.viddef.height - (y + h), color)


	vid.Draw_StretchRaw(x, y, w, h, cin.width, cin.height, cin.pic, cin.color_bits)
	return True


def SCR_LoadHiColor(namewe: str, ext: str, width: int, height: int, palette, bitsPerPixel: int):
	#const char*, const char *, int *, int *, byte **, int * (returns static byte *)

	# Q2PORT: width, height, palette and bitsPerPixel are passed in and returned
	# with the result: pic, width, height, palette, bitsPerPixel

	"""
	byte *pic, *data = NULL, *palette_in = NULL;
	char filename[256];
	"""

	filename = namewe[:255] # Q_strlcpy(filename, namewe, sizeof(filename));
	filename = (filename + ".")[:255] # Q_strlcat
	filename = (filename + ext)[:255] # Q_strlcat

	data, palette_in, w, h, bits = cl_image.SCR_LoadImageWithPalette(filename)
	if w is not None: width, height = w, h # SCR_LoadImageWithPalette sets them only when it gets that far
	if bits is not None: bitsPerPixel = bits
	if data is None:

		return None, width, height, palette, bitsPerPixel


	if palette_in:

		# pcx file could have palette
		palette = bytes(palette_in[:768]) # *palette = Z_Malloc(768); memcpy(*palette, palette_in, 768);
		#free(palette_in);


	# Q2PORT: the C copies cin.height * cin.width pixels; width and height point at those
	pic = bytes(data[:height * width * bitsPerPixel // 8]) # pic = Z_Malloc(...); memcpy(pic, data, ...);
	#free(data);

	return pic, width, height, palette, bitsPerPixel


"""
==================
SCR_PlayCinematic

==================
"""
def SCR_PlayCinematic(arg: str): #char *

	"""
	int width, height;
	byte *palette = NULL;
	char name[MAX_OSPATH], *dot;
	"""
	global abort_cinematic

	palette = None

	sdl2.In_FlushQueue()
	abort_cinematic = 2147483647 # INT_MAX

	# make sure background music is not playing
	ogg.OGG_Stop()

	cl_main.cl.cinematicframe = 0
	dot = arg.find(".") # strstr(arg, ".")
	dot = arg[dot:] if dot >= 0 else None

	# static pcx image
	if dot and (dot == ".pcx" or
				dot == ".tga" or
				dot == ".jpg" or
				dot == ".png"):

		"""
		cvar_t	*r_retexturing;
		char namewe[256];
		"""

		name = "pics/{}".format(arg)[:shared.MAX_OSPATH - 1] # Com_sprintf
		r_retexturing = cvar.Cvar_Get("r_retexturing", "1", shared.CVAR_ARCHIVE)

		# Remove the extension
		namewe = name[:len(name) - len(dot)] # memset(namewe, 0, 256); memcpy(namewe, name, strlen(name) - strlen(dot));

		if r_retexturing.value:

			cin.color_bits = 32

			cin.pic, cin.width, cin.height, palette, cin.color_bits = SCR_LoadHiColor(namewe, "tga", cin.width, cin.height,
				palette, cin.color_bits)

			if not cin.pic:

				cin.pic, cin.width, cin.height, palette, cin.color_bits = SCR_LoadHiColor(namewe, "png", cin.width, cin.height,
				palette, cin.color_bits)


			if not cin.pic:

				cin.pic, cin.width, cin.height, palette, cin.color_bits = SCR_LoadHiColor(namewe, "jpg", cin.width, cin.height,
				palette, cin.color_bits)



		if not cin.pic:

			cin.pic, cin.width, cin.height, palette, cin.color_bits = SCR_LoadHiColor(namewe, dot[1:], cin.width, cin.height,
				palette, cin.color_bits)


		cl_main.cl.cinematicframe = -1
		cl_main.cl.cinematictime = 1
		cl_screen.SCR_EndLoadingPlaque()

		cl_main.cls.state = client_h.connstate_t.ca_active

		if not cin.pic:

			clientserver.Com_Printf("%s not found.\n", name)
			cl_main.cl.cinematictime = 0

		elif palette:

			cl_main.cl.cinematicpalette = bytes(palette[:768]) # memcpy(cl.cinematicpalette, palette, sizeof(cl.cinematicpalette));
			#Z_Free(palette);


		return


	name = "video/{}".format(arg)[:shared.MAX_OSPATH - 1] # Com_sprintf
	file_length, cl_main.cl.cinematic_file = filesystem.FS_FOpenFile(name, False)

	if not cl_main.cl.cinematic_file:

		SCR_FinishCinematic()
		cl_main.cl.cinematictime = 0 # done
		return


	cl_screen.SCR_EndLoadingPlaque()

	cin.color_bits = 8
	cl_main.cls.state = client_h.connstate_t.ca_active

	width = filesystem.FS_Read(4, cl_main.cl.cinematic_file)
	height = filesystem.FS_Read(4, cl_main.cl.cinematic_file)
	cin.width = shared_c.LittleLong(width)
	cin.height = shared_c.LittleLong(height)

	cin.s_rate = filesystem.FS_Read(4, cl_main.cl.cinematic_file)
	cin.s_rate = shared_c.LittleLong(cin.s_rate)
	cin.s_width = filesystem.FS_Read(4, cl_main.cl.cinematic_file)
	cin.s_width = shared_c.LittleLong(cin.s_width)
	cin.s_channels = filesystem.FS_Read(4, cl_main.cl.cinematic_file)
	cin.s_channels = shared_c.LittleLong(cin.s_channels)

	Huff1TableInit()

	cl_main.cl.cinematicframe = 0
	cin.pic = SCR_ReadNextFrame()
	cl_main.cl.cinematictime = system.Sys_Milliseconds()


