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

import struct
import pygame
from linux import snd_linux
from client import snd_dma, snd_loc
from common import cvar
"""
// snd_mix.c -- portable code to mix sounds for snd_dma.c

#include "client.h"
#include "snd_loc.h"
"""
PAINTBUFFER_SIZE = 2048
paintbuffer = []
for i in range(PAINTBUFFER_SIZE):
	paintbuffer.append(snd_loc.portable_samplepair_t())

raw_buff = bytearray()

def S_PaintChannels(endtime): #int

	global paintbuffer, PAINTBUFFER_SIZE
	global raw_buff

	"""
	int 	i;
	int 	end;
	channel_t *ch;
	sfxcache_t	*sc;
	int		ltime, count;
	playsound_t	*ps;
	"""

	#print (snd_dma.paintedtime, endtime, snd_dma.s_pendingplays)

	# the C's SDL_BackendPaintChannel checks each channel as it paints:
	# a finished sound clears ch->sfx. Q2PORT: a per-frame pass over the channels
	# does the same (the C's per-sample fade in/out is not applied, see snd_dma).
	# loop channels are left alone: S_AddLoopSounds / S_Update manage their lifetime
	for i in range(snd_dma.s_numchannels):
		ch = snd_dma.channels[i]
		if ch.chan is None or ch.loop_sfx is not None:
			continue
		if ch.sfx is not None:
			sc = ch.sfx.cache
			if sc is not None and (snd_dma.paintedtime - ch.pos) >= sc.length:
				ch.clear()
				ch.chan.stop() # Q2PORT: the C's SDL leaves the painted channel dead; a pygame channel keeps playing until stopped
				ch.loop_sfx = None # Q2PORT: the loop bookkeeping is not in the C's channel_t

	snd_vol = snd_dma.s_volume.value*256

	##Com_Printf ("%i to %i\n", snd_dma.paintedtime, endtime);
	while snd_dma.paintedtime < endtime:

		# if paintbuffer is smaller than DMA buffer
		end = endtime
		if endtime - snd_dma.paintedtime > PAINTBUFFER_SIZE:
			end = snd_dma.paintedtime + PAINTBUFFER_SIZE

		# start any playsounds
		
		while len(snd_dma.s_pendingplays) > 0:
		
			ps = snd_dma.s_pendingplays[0]

			if ps.begin <= snd_dma.paintedtime:
				
				ps = snd_dma.s_pendingplays.pop(0)
				snd_dma.S_IssuePlaysound (ps)
				continue
			
			#if ps.begin < end:
			#	end = ps.begin		# stop here
			break
		

		# clear the paint buffer
		if snd_dma.s_rawend < snd_dma.paintedtime:
		
			## Com_Printf ("clear\n");
			#memset(paintbuffer, 0, (end - paintedtime) * sizeof(portable_samplepair_t))
			for i in range(snd_dma.paintedtime, end):
				paintbuffer[i-snd_dma.paintedtime].clear()
		
		else:
			# copy from the streaming sound source
			#int		s;
			#int		stop;

			if end < snd_dma.s_rawend:
				stop = end
			else:
				stop = snd_dma.s_rawend

			for i in range(snd_dma.paintedtime, stop):
			
				s = i&(snd_loc.MAX_RAW_SAMPLES-1)
				paintbuffer[i-snd_dma.paintedtime].left = snd_dma.s_rawsamples[s].left # Q2PORT: the C copies the struct
				paintbuffer[i-snd_dma.paintedtime].right = snd_dma.s_rawsamples[s].right

##		if (i != end)
##			Com_Printf ("partial stream\n");
##		else
##			Com_Printf ("full stream\n");
			for i in range(stop, end):
				# Buffer underrun, so pad paint buffer with zeros
				paintbuffer[i-snd_dma.paintedtime].left = 0
				paintbuffer[i-snd_dma.paintedtime].right = 0

		# Q2PORT: the C mixer that painted each channel into paintbuffer is not ported;
		# channels are played and mixed by pygame (see snd_dma).

		#if test is None:
		#	test = wave.open("test.wav", "w")
		#	test.setnchannels(2)
		#	test.setsampwidth(2)
		#	test.setframerate(44100//2)

		startrange = None
		endrange = None
		
		for i in range(snd_dma.paintedtime, end):
			s = i-snd_dma.paintedtime
			samp = paintbuffer[s]
			# Q2PORT: the C's SDL_TransferPaintBuffer, 16 bit stereo case
			val = samp.left >> 8
			if val > 0x7fff:
				val = 0x7fff
			elif val < -32768:
				val = -32768
			val2 = samp.right >> 8
			if val2 > 0x7fff:
				val2 = 0x7fff
			elif val2 < -32768:
				val2 = -32768
			raw_buff += struct.pack("<hh", val, val2)
			#test.writeframes(struct.pack("<hh", samp.left, samp.right))

			if startrange is None: startrange = s
			endrange = s

		if snd_linux.dma_channel.get_queue() is None:

			# transfer out according to DMA format
			raw_snd = pygame.mixer.Sound(buffer=raw_buff)
			snd_linux.dma_channel.queue(raw_snd)
			raw_buff = bytearray()

		snd_dma.paintedtime = end

def S_InitScaletable ():

	# Q2PORT: Yamagi's SDL_UpdateScaletable; the scale table itself is only
	# used by the unported mixer, so only the s_volume clamp is ported

	if snd_dma.s_volume.value > 2.0:
		cvar.Cvar_Set("s_volume", "2")
	elif snd_dma.s_volume.value < 0:
		cvar.Cvar_Set("s_volume", "0")

	snd_dma.s_volume.modified = False
