"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 * Copyright (C) 2010, 2013 Yamagi Burmeister
 * Copyright (C) 2005 Ryan C. Gordon
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * SDL sound backend. Since SDL is just an API for sound playback, we
 * must caculate everything in software: mixing, resampling, stereo
 * spartializations, etc. Therefor this file is rather complex. :)
 * Samples are read from the cache (see the upper layer of the sound
 * system), manipulated and written into sound.buffer. sound.buffer is
 * passed to SDL (in fact requested by SDL via the callback) and played
 * with a platform dependend SDL driver. Parts of this file are based
 * on ioQuake3s snd_sdl.c.
 *
 * =======================================================================
"""
from __future__ import annotations

from common import clientserver

# Q2PORT: the SDL backend is not ported. It is SDL's audio device and the C
# software mixer (paint buffer, resampling, spatialization), and the port has
# neither: sound is played by the OpenAL backend (client/sound/openal.py).
# SDL_BackendInit() fails, so sound.c's S_Init() never starts it (SS_SDL), and
# the other SDL_* functions sound.c names are never reached.

"""
static void lpf_initialize(LpfContext* lpf_context, float gain_hf, int target_frequency)
static void lpf_update_samples(LpfContext* lpf_context,int sample_count, portable_samplepair_t* samples)
static void SDL_TransferPaintBuffer(int endtime)
static void SDL_PaintChannels(int endtime)
static void SDL_SpatializeOrigin(vec3_t origin, float master_vol, float dist_mult, int *left_vol, int *right_vol)
static void SDL_AddLoopSounds(void)
static void SDL_UpdateSoundtime(void)
static void SDL_UpdateScaletable(void)
static void SDL_Callback(void *data, Uint8 *stream, int length)
(not ported, see above)
"""

# Q2PORT: the functions sound.c calls in its SS_SDL branches; they are never
# reached, as SDL_BackendInit() fails
def SDL_DriftBeginofs(timeofs: float)->int: #float (returns int)

	raise NotImplementedError()

def SDL_Spatialize(ch): #channel_t *

	raise NotImplementedError()

def SDL_ClearBuffer(): #void

	raise NotImplementedError()

def SDL_Cache(sfx, info, data, volume: int, begin_length: int, end_length: int,
	attack_length: int, fade_length: int)->bool: #sfx_t *, wavinfo_t *, byte *, short, int, int, int, int (returns qboolean)

	raise NotImplementedError()

def SDL_RawSamples(samples: int, rate: int, width: int, channels: int, data, volume: float): #int, int, int, int, const byte *, float

	raise NotImplementedError()

def SDL_Update(): #void

	raise NotImplementedError()

def SDL_SoundInfo(): #void

	raise NotImplementedError()

def SDL_BackendShutdown(): #void

	raise NotImplementedError()

"""
 * Initializes the SDL sound
 * backend and sets up SDL.
"""
def SDL_BackendInit()->bool: #void (returns qboolean)

	clientserver.Com_Printf("SDL audio backend is not available, there is no software mixer.\n") # Q2PORT
	return False
