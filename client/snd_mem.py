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

import io
pass
from client import snd_loc, snd_dma
pass
import pygame
from common.header import shared
from common import clientserver
from common import filesystem
"""
// snd_mem.c: sound caching

#include "client.h"
#include "snd_loc.h"

int			cache_full_cycle;

byte *S_Alloc (int size);
"""
"""
/*
================
ResampleSfx
================
*/
void ResampleSfx (sfx_t *sfx, int inrate, int inwidth, byte *data)
{
	int		outcount;
	int		srcsample;
	float	stepscale;
	int		i;
	int		sample, samplefrac, fracstep;
	sfxcache_t	*sc;
	
	sc = sfx->cache;
	if (!sc)
		return;

	stepscale = (float)inrate / dma.speed;	// this is usually 0.5, 1, or 2

	outcount = sc->length / stepscale;
	sc->length = outcount;
	if (sc->loopstart != -1)
		sc->loopstart = sc->loopstart / stepscale;

	sc->speed = dma.speed;
	if (s_loadas8bit->value)
		sc->width = 1;
	else
		sc->width = inwidth;
	sc->stereo = 0;

// resample / decimate to the current source rate

	if (stepscale == 1 && inwidth == 1 && sc->width == 1)
	{
// fast special case
		for (i=0 ; i<outcount ; i++)
			((signed char *)sc->data)[i]
			= (int)( (unsigned char)(data[i]) - 128);
	}
	else
	{
// general case
		samplefrac = 0;
		fracstep = stepscale*256;
		for (i=0 ; i<outcount ; i++)
		{
			srcsample = samplefrac >> 8;
			samplefrac += fracstep;
			if (inwidth == 2)
				sample = LittleShort ( ((short *)data)[srcsample] );
			else
				sample = (int)( (unsigned char)(data[srcsample]) - 128) << 8;
			if (sc->width == 2)
				((short *)sc->data)[i] = sample;
			else
				((signed char *)sc->data)[i] = sample >> 8;
		}
	}
}

//=============================================================================
"""
"""
/*
==============
S_LoadSound
==============
"""
def S_LoadSound (s): #sfx_t * (returns sfxcache_t *)

	"""
	char namebuffer[MAX_QPATH];
	byte *data = NULL;
	wavinfo_t info;
	sfxcache_t *sc;
	double sound_volume = 0;
	int begin_length = 0;
	int end_length = 0;
	int attack_length = 0;
	int fade_length = 0;
	char *name;
	"""

	if s.name[0] == '*':
		return None

	# see if still in memory
	sc = s.cache

	if sc is not None:
		return sc

	# load it
	if s.truename is not None:
		name = s.truename
	else:
		name = s.name

	if name[0] == '#':
		namebuffer = name[1:]
	else:
		namebuffer = "sound/{}".format(name)

	# Q2PORT: the C's S_LoadVorbis (static, sound.c) falls back to a .ogg when the
	# .wav is missing; here it also builds the cache directly (see snd_dma.S_LoadVorbis)
	sc = snd_dma.S_LoadVorbis(s, namebuffer)
	if sc is not None:
		s.cache = sc
		return sc

	# can't load ogg file
	size, data = filesystem.FS_LoadFile (namebuffer)

	if data is None:
	
		s.cache = None
		clientserver.Com_DPrintf ("Couldn't load {}\n".format(namebuffer))
		return None

	info = GetWavinfo (s.name, data, size)

	if info.channels < 1 or info.channels > 2:
	
		clientserver.Com_Printf ("{} has an invalid number of channels\n".format(s.name))
		filesystem.FS_FreeFile(data)
		return None

	if snd_dma.S_IsSilencedMuzzleFlash(info, data, namebuffer):
		s.is_silenced_muzzle_flash = True

	sound_volume = snd_dma.S_GetVolume(data[info.dataofs:info.dataofs + info.samples * info.width], info.samples, info.width)

	begin_length, end_length, attack_length, fade_length = snd_dma.S_GetStatistics(
		data[info.dataofs:info.dataofs + info.samples * info.width], info.samples,
		info.width, info.channels, sound_volume)

	stepscale = info.rate / snd_dma.dma.speed

	sc = snd_loc.sfxcache_t()
	# Pass a file object so pygame parses the wav header and converts the mono
	# data to the mixer format. Raw bytes are treated as samples already in the
	# mixer format (stereo), which played everything at double speed.
	sc.data = pygame.mixer.Sound(file=io.BytesIO(data))

	filesystem.FS_FreeFile(data)

	sc.length = int(sc.data.get_length() * snd_dma.dma.speed) # in samples, like paintedtime
	sc.loopstart = info.loopstart
	sc.speed = info.rate
	sc.width = info.width
	sc.stereo = info.channels
	sc.begin = begin_length
	sc.end = end_length
	sc.attack = attack_length
	sc.fade = fade_length
	sc.volume = int(sound_volume)

	# pygame resamples the data, so only the loopstart scaling from ResampleSfx is applied
	if sc.loopstart != -1:
		sc.loopstart = int(sc.loopstart / stepscale)
	sc.speed = snd_dma.dma.speed

	s.cache = sc

	return sc

"""

/*
===============================================================================

WAV loading

===============================================================================
*/


"""

data_p = None #byte	*, index into iff_buf, None for NULL
iff_end = None #byte 	*
last_chunk = None #byte 	*
iff_data = None #byte 	*
iff_chunk_len = None #int
iff_buf = None # the wav buffer the pointers above index into


def GetLittleShort():

	global data_p

	val = 0
	val = iff_buf[data_p]
	val = val + (iff_buf[data_p+1]<<8)
	data_p += 2
	if val >= 0x8000: # short
		val -= 0x10000
	return val


def GetLittleLong():

	global data_p

	val = 0
	val = iff_buf[data_p]
	val = val + (iff_buf[data_p+1]<<8)
	val = val + (iff_buf[data_p+2]<<16)
	val = val + (iff_buf[data_p+3]<<24)
	data_p += 4
	if val >= 0x80000000: # int
		val -= 0x100000000
	return val


def FindNextChunk(name): #char *

	global data_p, iff_chunk_len, last_chunk

	while True:
	
		data_p=last_chunk

		if data_p >= iff_end:
			# didn't find the chunk
			data_p = None
			return
		
		data_p += 4
		iff_chunk_len = GetLittleLong()
		if iff_chunk_len < 0:
		
			data_p = None
			return
		
#		if (iff_chunk_len > 1024*1024)
#			Sys_Error ("FindNextChunk: %i length is past the 1 meg sanity limit", iff_chunk_len);
		data_p -= 8
		last_chunk = data_p + 8 + ( (iff_chunk_len + 1) & ~1 )
		if iff_buf[data_p:data_p+4] == name:
			return
	

def FindChunk(name): #char *

	global last_chunk

	last_chunk = iff_data
	FindNextChunk (name)


def DumpChunks():

	global data_p, iff_chunk_len

	#char	str[5];
	
	data_p=iff_data
	while True:
	
		st = iff_buf[data_p:data_p+4].decode('ascii', 'replace')
		data_p += 4
		iff_chunk_len = GetLittleLong()
		clientserver.Com_Printf ("0x{:x} : {} ({:d})\n".format(data_p - 4, st, iff_chunk_len))
		data_p += (iff_chunk_len + 1) & ~1
		if not (data_p < iff_end):
			break
	
"""
============
GetWavinfo
============
"""
def GetWavinfo (name, wav, wavlength): #char *, byte *, int (returns wavinfo_t)

	global data_p, iff_data, iff_end, iff_buf

	"""
	wavinfo_t	info;
	int     i;
	int     format;
	int		samples;
	"""

	info = snd_loc.wavinfo_t() # memset (&info, 0, sizeof(info));

	if wav is None:
		return info
		
	iff_buf = wav
	iff_data = 0
	iff_end = wavlength

	# find "RIFF" chunk
	FindChunk(b"RIFF")
	if not (data_p is not None and iff_buf[data_p+8:data_p+12] == b"WAVE"):
	
		clientserver.Com_Printf("Missing RIFF/WAVE chunks\n")
		return info
	
	# get "fmt " chunk
	iff_data = data_p + 12
	# DumpChunks ();

	FindChunk(b"fmt ")
	if data_p is None:
	
		clientserver.Com_Printf("Missing fmt chunk\n")
		return info
	
	data_p += 8
	format = GetLittleShort()
	if format != 1:
	
		clientserver.Com_Printf("Microsoft PCM format only\n")
		return info
	
	info.channels = GetLittleShort()
	info.rate = GetLittleLong()
	data_p += 4+2
	info.width = GetLittleShort() // 8

	# get cue chunk
	FindChunk(b"cue ")
	if data_p is not None:
	
		data_p += 32
		info.loopstart = GetLittleLong()
#		Com_Printf("loopstart=%d\n", sfx->loopstart);

		# if the next chunk is a LIST chunk, look for a cue length marker
		FindNextChunk (b"LIST")
		if data_p is not None:
		
			if iff_buf[data_p + 28:data_p + 32] == b"mark":
				# this is not a proper parse, but it works with cooledit...
				data_p += 24
				i = GetLittleLong ()	# samples in loop
				info.samples = info.loopstart + i
#				Com_Printf("looped length: %i\n", i);
			
	else:
		info.loopstart = -1

	# find data chunk
	FindChunk(b"data")
	if data_p is None:
	
		clientserver.Com_Printf("Missing data chunk\n")
		return info
	
	data_p += 4
	samples = int(GetLittleLong () / info.width)

	if info.samples:
	
		if samples < info.samples:
			clientserver.Com_Error (shared.ERR_DROP, "Sound {} has a bad loop length".format(name))
	
	else:
		info.samples = samples

	info.dataofs = data_p # data_p - wav
	
	return info

