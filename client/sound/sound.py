"""
 * Copyright (C) 1997-2001 Id Software, Inc.
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
 * The upper layer of the Quake II sound system. This is merely more
 * than an interface between the client and a backend. Currently only
 * two backends are supported:
 * - OpenAL, renders sound with OpenAL.
 * - SDL, has the same features than the original sound system.
 *
 * =======================================================================
"""
from __future__ import annotations

import builtins
import math

import numpy as np

from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from client import cl_main
from client.header import client as client_h
from client.sound import ogg
from client.sound import openal
from client.sound import qal
from client.sound import sdl as sound_sdl
from client.sound import wave
from client.sound.header import local as sound_local

#include "../header/client.h"
#include "header/local.h"
#include "header/qal.h"
#include "header/vorbis.h"

# During registration it is possible to have more sounds
# than could actually be referenced during gameplay,
# because we don't want to free anything until we are
# sure we won't need it.
MAX_SFX = (shared.MAX_SOUNDS * 2)
MAX_PLAYSOUNDS = 128

# Maximum length (seconds) of audio data to test for silence.
S_MAX_LEN_TO_TEST_FOR_SILENCE_S = (2)

# Minimum length (milliseconds) of audio data to treat as silence.
S_MIN_LEN_TO_TREAT_AS_SILENCE_MS = (3)

# Minimum amplitude absolute value of unsigned 8-bit audio data to treat as silence.
S_MIN_ABS_AMP_8_TO_TREAT_AS_SILENCE = (1)

# Minimum amplitude absolute value of signed 16-bit audio data to treat as silence.
S_MIN_ABS_AMP_16_TO_TREAT_AS_SILENCE = (2)


listener_origin = np.zeros((3,), dtype=np.float32) #vec3_t
listener_forward = np.zeros((3,), dtype=np.float32) #vec3_t
listener_right = np.zeros((3,), dtype=np.float32) #vec3_t
listener_up = np.zeros((3,), dtype=np.float32) #vec3_t

s_playsounds = [] #static playsound_t [MAX_PLAYSOUNDS]
for i in range(MAX_PLAYSOUNDS):
	s_playsounds.append(sound_local.playsound_t())
s_freeplays = [] #static playsound_t, Q2PORT: the linked list as a list
s_pendingplays = [] #playsound_t, Q2PORT: the linked list as a list, in order

s_volume = None #cvar_t *
s_testsound = None #cvar_t *
s_loadas8bit = None #cvar_t *
s_khz = None #cvar_t *
s_mixahead = None #cvar_t *
s_show = None #cvar_t *
s_ambient = None #cvar_t *
s_underwater = None #cvar_t*
s_underwater_gain_hf = None #cvar_t*
s_doppler = None #cvar_t*
s_occlusion_strength = None #cvar_t*
s_reverb_preset = None #cvar_t*
s_ps_sorting = None #static cvar_t*
s_feedback_kind = None #static cvar_t*

channels = [] #channel_t [MAX_CHANNELS]
for i in range(sound_local.MAX_CHANNELS):
	channels.append(sound_local.channel_t())
num_sfx = 0 #static int
sound_max = 0 #static int
paintedtime = 0 #int
s_numchannels = 0 #int
s_rawend = 0 #int
s_registration_sequence = 0 #static int
s_rawsamples = [] #portable_samplepair_t [MAX_RAW_SAMPLES]
for i in range(sound_local.MAX_RAW_SAMPLES):
	s_rawsamples.append(sound_local.portable_samplepair_t())
known_sfx = [] #static sfx_t [MAX_SFX]
for i in range(MAX_SFX):
	known_sfx.append(sound_local.sfx_t())
sound_started = sound_local.SS_NOT #sndstarted_t
sound = sound_local.sound_t() #sound_t
s_registering = False #static qboolean
s_active = False #qboolean

snd_is_underwater = False #qboolean
# -----------------------------------------------------------------

def S_IsShortSilence(info: sound_local.wavinfo_t, raw_data)->bool: #const wavinfo_t*, const void* (returns static qboolean)

	# Test only mono-audio data.
	if info.channels != 1:

		return False

	# Treat it as silence if sample count too small.
	if ((info.samples * 1000) // info.rate) <= S_MIN_LEN_TO_TREAT_AS_SILENCE_MS:

		return True

	# Test only several second's of audio data.
	if info.samples > (info.rate * S_MAX_LEN_TO_TEST_FOR_SILENCE_S):

		return False

	if info.width == 1:

		# Unsigned 8-bit audio data.

		# Q2PORT: like the C, raw_data is the start of the file (not data + dataofs);
		# the read is limited to the buffer
		sample_count = info.samples * info.width #const int
		samples = np.frombuffer(raw_data, dtype=np.uint8, count=min(sample_count, builtins.len(raw_data))) #const unsigned char*
		sample = samples.astype(np.int32) - 0x80

		if np.any(np.abs(sample) > S_MIN_ABS_AMP_8_TO_TREAT_AS_SILENCE):

			return False

	elif info.width == 2:

		# Signed 16-bit audio data.

		# Q2PORT: like the C, raw_data is the start of the file (not data + dataofs)
		# and the count is samples * width; the read is limited to the buffer
		sample_count = info.samples * info.width #const int
		samples = np.frombuffer(raw_data, dtype="<i2", count=min(sample_count, builtins.len(raw_data) // 2)) # LittleShort

		if np.any(np.abs(samples.astype(np.int32)) > S_MIN_ABS_AMP_16_TO_TREAT_AS_SILENCE):

			return False

	else:

		# Unsupported bit depth.
		return False

	return True

def S_IsSilencedMuzzleFlash(info: sound_local.wavinfo_t, raw_data, name: str)->bool: #const wavinfo_t*, const void*, const char* (returns static qboolean)

	# Skip the prefix.
	base_sound_string_length = 6 #static const size_t, strlen("sound/")
	base_name = name[base_sound_string_length:] #const char*

	# Match to well-known muzzle flash sound names.
	is_name_matched = (
		base_name == "weapons/bfg__f1y.wav" or
		base_name == "weapons/blastf1a.wav" or
		base_name == "weapons/disint2.wav" or
		base_name == "weapons/grenlf1a.wav" or
		base_name == "weapons/grenlr1b.wav" or
		base_name == "weapons/hyprbf1a.wav" or
		base_name == "weapons/machgf1b.wav" or
		base_name == "weapons/machgf2b.wav" or
		base_name == "weapons/machgf3b.wav" or
		base_name == "weapons/machgf4b.wav" or
		base_name == "weapons/machgf5b.wav" or
		base_name == "weapons/nail1.wav" or
		base_name == "weapons/plasshot.wav" or
		base_name == "weapons/railgf1a.wav" or
		base_name == "weapons/rippfire.wav" or
		base_name == "weapons/rocklf1a.wav" or
		base_name == "weapons/rocklr1b.wav" or
		base_name == "weapons/shotg2.wav" or
		base_name == "weapons/shotgf1b.wav" or
		base_name == "weapons/shotgr1b.wav" or
		base_name == "weapons/sshotf1b.wav" or
		False
	) #const qboolean

	if not is_name_matched:

		return False

	# Now check for silence.
	if not S_IsShortSilence(info, raw_data):

		return False

	return True

def S_LoadVorbis(path: str)->tuple: #const char *, wavinfo_t *, void ** (returns static void; Q2PORT: info, buffer)

	ogg_ext = ".ogg" #const char []
	#char filename[MAX_QPATH];
	#const char* ext;
	#int	len;

	if not path:

		return None, None

	ext = shared_c.COM_FileExtension(path)
	if not ext:

		# file has no extension
		return None, None

	# Remove the extension
	len = (builtins.len(path) - builtins.len(ext)) - 1 # (ext - path) - 1
	if (len < 1) or (len > shared.MAX_QPATH - 5): # sizeof(filename) - 5

		clientserver.Com_DPrintf("{}: Bad filename {}\n".format("S_LoadVorbis", path))
		return None, None

	# copy base path
	filename = path[:len] # memcpy(filename, path, len);

	# Add the extension
	filename += ogg_ext

	return ogg.OGG_LoadAsWav(filename)

def S_GetVolume(data, sound_length: int, width: int)->float: #const byte *, int, int, double * (returns static void; Q2PORT: sound_volume)

	# update sound volume
	sound_volume = 0.0
	if width == 2:

		sound_data = np.frombuffer(data, dtype="<i2", count=min(sound_length, builtins.len(data) // 2)) # LittleShort
		sound_sample = sound_data.astype(np.float64)
		sound_volume += float(np.sum(sound_sample * sound_sample))

	elif width == 1:

		# normilize to 16bit sound;
		sound_data = np.frombuffer(data, dtype=np.uint8, count=min(sound_length, builtins.len(data)))
		sound_sample = (sound_data.astype(np.int32) << 8).astype(np.int16).astype(np.float64) # short sound_sample = *sound_data << 8
		sound_volume += float(np.sum(sound_sample * sound_sample))

	if sound_length != 0:

		sound_volume /= sound_length
		sound_volume = float(np.sqrt(np.float32(sound_volume))) # sqrtf

	return sound_volume

def S_GetStatistics(data, sound_length: int, width: int, channels: int,
	sound_volume: float)->tuple: #const byte *, int, int, int, double, int *, int *, int *, int * (returns static void; Q2PORT: begin_length, end_length, attack_length, fade_length)

	# Q2PORT: the C's short arithmetic, wrapped to 16 bits
	def short(x): return ((int(x) + 32768) & 0xFFFF) - 32768

	begin_length = end_length = attack_length = fade_length = 0

	# Q2PORT: both widths as a list of shorts (the width 1 samples << 8, as the
	# C normalizes them); the pointers become indices
	if width == 2:
		sound_samples = np.frombuffer(data, dtype="<i2", count=min(sound_length, builtins.len(data) // 2)).tolist() # LittleShort
	elif width == 1:
		sound_samples = (np.frombuffer(data, dtype=np.uint8, count=min(sound_length, builtins.len(data))).astype(np.int32) << 8).astype(np.int16).tolist()
	else:
		return begin_length, end_length, attack_length, fade_length
	sound_samples += [0] * (sound_length - builtins.len(sound_samples)) # Q2PORT: a truncated file reads as silence

	# attack length
	sound_max = 0 #short
	# calculate max value
	for sound_sample in sound_samples:

		if sound_max < abs(sound_sample):

			sound_max = short(abs(sound_sample))

	# use something in middle
	sound_max = short((sound_max + sound_volume) / 2)

	# calculate attack/fade length
	# Q2PORT: the do/while loops read one sample past the ends of a (near) empty
	# sound; the zero appended here stands in for those reads (index sound_length, and -1)
	sound_samples.append(0)
	sound_data = 0
	delay_data = sound_data
	fade_data = sound_data
	sound_end = sound_data + sound_length
	sound_sample = 0 #short
	sound_treshold = short(int(sound_max / 2)) #short

	# delay calculate
	while True:

		sound_sample = sound_samples[sound_data]
		sound_data += 1

		if not (sound_data < sound_end and abs(sound_sample) < sound_treshold):
			break

	# delay_data == (short *)(data + info.dataofs)
	begin_length = int((sound_data - delay_data) / channels)
	delay_data = sound_data
	fade_data = sound_data

	# attack calculate
	while True:

		sound_sample = sound_samples[sound_data]
		sound_data += 1

		if not (sound_data < sound_end and abs(sound_sample) < sound_max):
			break

	# fade_data == delay_data
	attack_length = int((sound_data - delay_data) / channels)
	fade_data = sound_data

	# end calculate
	sound_data = sound_end
	while True:

		sound_data -= 1
		sound_sample = sound_samples[sound_data]

		if not (sound_data > fade_data and abs(sound_sample) < sound_treshold):
			break

	end_length = int((sound_end - sound_data) / channels)
	sound_end = sound_data

	# fade calculate
	while True:

		sound_data -= 1
		sound_sample = sound_samples[sound_data]

		if not (sound_data > fade_data and abs(sound_sample) < sound_max):
			break

	fade_length = int((sound_end - sound_data) / channels)

	return begin_length, end_length, attack_length, fade_length

"""
 * Loads one sample into memory
"""
def S_LoadSound(s: sound_local.sfx_t)->sound_local.sfxcache_t: #sfx_t * (returns sfxcache_t *)

	#char namebuffer[MAX_QPATH];
	data = None #byte *
	info = None #wavinfo_t
	#sfxcache_t *sc;
	sound_volume = 0 #double
	begin_length = 0 #int
	attack_length = 0 #int
	fade_length = 0 #int
	end_length = 0 #int
	#char *name;

	if s.name[0] == '*':

		return None

	# see if still in memory
	sc = s.cache

	if sc:

		return sc

	# load it
	if s.truename:

		name = s.truename

	else:

		name = s.name

	if name[0] == '#':

		namebuffer = name[1:][:shared.MAX_QPATH - 1] # Q_strlcpy(namebuffer, &name[1], sizeof(namebuffer));

	else:

		namebuffer = "sound/{}".format(name)[:shared.MAX_QPATH - 1] # Com_sprintf(namebuffer, sizeof(namebuffer), "sound/%s", name);

	info, data = S_LoadVorbis(namebuffer)

	# can't load ogg file
	if not data:

		size, data = filesystem.FS_LoadFile(namebuffer)

		if data:

			info = wave.GetWavinfo(s.name, data, size)

	if not data:

		s.cache = None
		clientserver.Com_DPrintf("Couldn't load {}\n".format(namebuffer))
		return None

	#Com_Printf("%s: rate:%d\n\twidth:%d\n\tchannels:%d\n\tloopstart:%d\n\tsamples:%d\n\tdataofs:%d\n",
	#	s->name, info.rate, info.width, info.channels, info.loopstart, info.samples, info.dataofs);

	if info.channels < 1 or info.channels > 2:

		clientserver.Com_Printf("{} has an invalid number of channels\n".format(s.name))
		filesystem.FS_FreeFile(data)
		return None

	if S_IsSilencedMuzzleFlash(info, data, namebuffer):

		s.is_silenced_muzzle_flash = True

	sound_volume = S_GetVolume(data[info.dataofs:], info.samples,
		info.width)

	begin_length, end_length, attack_length, fade_length = S_GetStatistics(data[info.dataofs:], info.samples,
		info.width, info.channels, sound_volume)

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		sc = openal.AL_UploadSfx(s, info, data[info.dataofs:], sound_volume,
						  begin_length, end_length,
						  attack_length, fade_length)

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			if not sound_sdl.SDL_Cache(s, info, data[info.dataofs:], sound_volume,
						  begin_length, end_length,
						  attack_length, fade_length):

				clientserver.Com_Printf("Pansen!\n")
				filesystem.FS_FreeFile(data)
				return None

	filesystem.FS_FreeFile(data)
	return sc

"""
 * Returns the sfx with the specified name, NULL if none exists
"""
def S_GetSfxByName(name: str)->sound_local.sfx_t: #const char * (returns static sfx_t *)

	#int i;

	for i in range(num_sfx):

		if known_sfx[i].name == name:

			return known_sfx[i]

	return None

def S_NextFreeSfx()->sound_local.sfx_t: #void (returns static sfx_t *)

	global num_sfx

	#int i;

	for i in range(num_sfx):

		if not known_sfx[i].name:

			return known_sfx[i]

	if num_sfx >= MAX_SFX:

		return None

	num_sfx += 1
	return known_sfx[num_sfx - 1] # &known_sfx[num_sfx++]

def S_FindOrCreateSfx(name: str)->sound_local.sfx_t: #const char * (returns static sfx_t *)

	#sfx_t *sfx;

	if not name:

		clientserver.Com_Printf("{}: blank name\n".format("S_FindOrCreateSfx"))
		return None

	# see if already loaded
	sfx = S_GetSfxByName(name)

	if sfx:

		return sfx

	if builtins.len(name) >= shared.MAX_QPATH:

		clientserver.Com_Printf("{}: name is too long: {}\n".format("S_FindOrCreateSfx", name))
		return None

	sfx = S_NextFreeSfx()

	if not sfx:

		clientserver.Com_Printf("{}: out of sfx for: {}\n".format("S_FindOrCreateSfx", name))
		return None

	sfx.truename = None
	sfx.name = name
	sfx.registration_sequence = s_registration_sequence
	sfx.is_silenced_muzzle_flash = False

	return sfx

"""
 * Registers an alias name
 * for a sound
"""
def S_AliasName(aliasname: str, truename: str)->sound_local.sfx_t: #const char *, const char * (returns static sfx_t *)

	#sfx_t *sfx;

	if builtins.len(aliasname) >= shared.MAX_QPATH:

		clientserver.Com_Printf("{}: name is too long: {}\n".format("S_AliasName", aliasname))
		return None

	sfx = S_NextFreeSfx()

	if not sfx:

		clientserver.Com_Printf("{}: out of sfx for: {}\n".format("S_AliasName", aliasname))
		return None

	sfx.cache = None
	sfx.name = aliasname[:shared.MAX_QPATH - 1] # Q_strlcpy(sfx->name, aliasname, sizeof(sfx->name));
	sfx.registration_sequence = s_registration_sequence
	sfx.truename = truename # Z_Malloc(strlen(truename) + 1); strcpy(sfx->truename, truename);

	return sfx

"""
 * Called before registering
 * of sound starts
"""
def S_BeginRegistration(): #void

	global s_registration_sequence, s_registering

	s_registration_sequence += 1
	s_registering = True

"""
 * Registers a sound
"""
def S_RegisterSound(name: str)->sound_local.sfx_t: #const char * (returns struct sfx_s *)

	#sfx_t *sfx;

	if sound_started == sound_local.SS_NOT:

		return None

	sfx = S_FindOrCreateSfx(name)

	if not sfx:

		return None

	sfx.registration_sequence = s_registration_sequence

	if not s_registering:

		S_LoadSound(sfx)

	return sfx

def GetModelName(cs: str, n: int)->str: #const char *, char *, size_t (returns static void; Q2PORT: model)

	#const char *p;
	#char *end;

	model = "" # *model = '\0';

	if not cs:

		return model

	p = cs.find('\\')

	if p == -1:

		return model

	p += 1

	if builtins.len(cs) - p >= n: # strlen(p) >= n

		return model

	model = cs[p:] # Q_strlcpy(model, p, n);

	end = model.find('/')

	if end != -1:

		model = model[:end] # *end = '\0';

	return model

def S_RegisterSexedSound(entnum: int, base: str)->sound_local.sfx_t: #int, const char * (returns static sfx_t *)

	#sfx_t *sfx;
	#char model[MAX_QPATH];
	#char sexedFilename[MAX_QPATH];
	#char *cs;

	# determine what model the client is using
	if entnum > 0 and entnum <= cl_main.CL_MaxClients():

		cs = cl_main.cl.configstrings[shared.CS_PLAYERSKINS + entnum - 1]

	else:

		cs = None

	model = GetModelName(cs, shared.MAX_QPATH) # sizeof(model)

	# if we can't figure it out, they're male
	if not model:

		model = "male"

	# see if we already know of the model specific sound
	sexedFilename = "#players/{}/{}".format(model, base[1:])[:shared.MAX_QPATH - 1]

	sfx = S_GetSfxByName(sexedFilename)

	if not sfx:

		# no, so see if it exists
		if common_h.FS_FileExists(sexedFilename[1:]):

			# yes, close the file and register it
			sfx = S_RegisterSound(sexedFilename)

		else:

			#char maleFilename[MAX_QPATH];

			# no, revert to the male sound in the pak0.pak
			maleFilename = "player/male/{}".format(base[1:])[:shared.MAX_QPATH - 1]

			sfx = S_AliasName(sexedFilename, maleFilename)

	return sfx

def S_HasFreeSpace()->bool: #void (returns static qboolean)

	global sound_max

	#sfx_t *sfx;
	#int i, used;

	used = 0

	# check used slots
	for i in range(num_sfx):

		sfx = known_sfx[i]
		if not sfx.name:

			continue

		if sfx.registration_sequence == s_registration_sequence:

			used += 1

	if sound_max < used:

		sound_max = used

	# should same size of free slots as currently used
	return (num_sfx + used) < MAX_SFX

"""
 * Called after registering of
 * sound has ended
"""
def S_EndRegistration(): #void

	global s_registering

	#int i;
	#sfx_t *sfx;

	if not S_HasFreeSpace():

		# free any sounds not from this registration sequence
		for i in range(num_sfx):

			sfx = known_sfx[i]
			if not sfx.name:

				continue

			if sfx.registration_sequence != s_registration_sequence:

				# it is possible to have a leftover
				#if (sfx->cache) Z_Free(sfx->cache); /* from a server that didn't finish loading */
				#if (sfx->truename) Z_Free(sfx->truename);

				sfx.cache = None
				sfx.name = "" # sfx->name[0] = 0;

	# load everything in
	for i in range(num_sfx):

		sfx = known_sfx[i]
		if not sfx.name:

			continue

		S_LoadSound(sfx)

	s_registering = False

# -----------------------------------------------------------------

"""
 * Picks a free channel
"""
def S_PickChannel(entnum: int, entchannel: int)->sound_local.channel_t: #int, int (returns channel_t *)

	#int ch_idx;
	#int first_to_die;
	#int life_left;
	#channel_t *ch;
	plnum = cl_main.cl.playernum + 1 #const int

	if entchannel < 0:

		clientserver.Com_Error(shared.ERR_DROP, "{}: entchannel<0".format("S_PickChannel"))

	# Check for replacement sound, or find the best one to replace
	first_to_die = -1
	life_left = 0x7fffffff

	for ch_idx in range(s_numchannels):

		# channel 0 never overrides
		if ((entchannel != 0) and
			(channels[ch_idx].entnum == entnum) and
			(channels[ch_idx].entchannel == entchannel)):

			# always override sound from same entity
			first_to_die = ch_idx
			break

		# don't let monster sounds override player sounds
		if ((channels[ch_idx].entnum == plnum) and
			(entnum != plnum) and channels[ch_idx].sfx):

			continue

		if channels[ch_idx].end - paintedtime < life_left:

			life_left = channels[ch_idx].end - paintedtime
			first_to_die = ch_idx

	if first_to_die == -1:

		return None

	ch = channels[first_to_die]

	#if USE_OPENAL
	if (sound_started == sound_local.SS_OAL) and ch.sfx:

		# Make sure the channel is dead
		openal.AL_StopChannel(ch)
	#endif

	ch.clear() # memset(ch, 0, sizeof(*ch));
	return ch

"""
 * Picks a free playsound
"""
def S_AllocPlaysound()->sound_local.playsound_t: #void (returns static playsound_t *)

	#playsound_t *ps;

	if not s_freeplays: # ps == &s_freeplays

		# no free playsounds, this results
		# in stuttering an cracking
		return None

	# unlink from freelist
	ps = s_freeplays.pop(0) # s_freeplays.next

	return ps

"""
 * Frees a playsound
"""
def S_FreePlaysound(ps: sound_local.playsound_t): #playsound_t * (static)

	# unlink from channel
	if ps in s_pendingplays:
		s_pendingplays.remove(ps)

	# add to free list
	s_freeplays.insert(0, ps)

"""
 * Take the next playsound and begin it on the channel
 * This is never called directly by S_Play*, but only
 * by the update loop.
"""
def S_IssuePlaysound(ps: sound_local.playsound_t): #playsound_t *

	#channel_t *ch;
	#sfxcache_t *sc;

	if not ps:

		return

	if s_show.value:

		clientserver.Com_Printf("Issue {}\n".format(ps.begin))

	if s_ps_sorting.value == 3 and ps.sfx.is_silenced_muzzle_flash:

		S_FreePlaysound(ps)
		return

	# pick a channel to play on
	ch = S_PickChannel(ps.entnum, ps.entchannel)

	if not ch:

		S_FreePlaysound(ps)
		return

	sc = S_LoadSound(ps.sfx)

	if not sc:

		clientserver.Com_Printf("S_IssuePlaysound: couldn't load {}\n".format(ps.sfx.name))
		S_FreePlaysound(ps)
		return

	# spatialize
	if ps.attenuation == shared.ATTN_STATIC:

		ch.dist_mult = ps.attenuation * 0.001

	else:

		ch.dist_mult = ps.attenuation * 0.0005

	ch.entnum = ps.entnum
	ch.entchannel = ps.entchannel
	ch.sfx = ps.sfx
	shared.VectorCopy(ps.origin, ch.origin)
	ch.fixed_origin = ps.fixed_origin

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		# This is clamped to 1.0 in AL_PlayChannel()
		ch.oal_vol = ps.volume * (s_volume.value)
		openal.AL_PlayChannel(ch)

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			ch.master_vol = int(ps.volume)
			sound_sdl.SDL_Spatialize(ch)

	ch.pos = 0
	ch.end = paintedtime + sc.length

	# free the playsound
	S_FreePlaysound(ps)

_game = None #static const cvar_t *, S_StartSound

"""
 * Validates the parms and queues the sound up.
 * If pos is NULL, the sound will be dynamically
 * sourced from the entity. Entchannel 0 will never
 * override a playing sound.
"""
def S_StartSound(origin, entnum: int, entchannel: int, sfx: sound_local.sfx_t,
		fvol: float, attenuation: float, timeofs: float): #vec3_t, int, int, sfx_t *, float, float, float

	global _game

	#sfxcache_t *sc;
	#playsound_t *ps, *sort;

	if sound_started == sound_local.SS_NOT:

		return

	# A hack to prevent temporary entities generating sounds when the sound
	# backend is not active and the game is not paused
	if s_active == False:

		return

	if not sfx:

		return

	# -1 means localized (menu sounds, etc.)
	if (entnum < -1) or (entnum >= cl_main.cl_numentities):

		return

	if sfx.name[0] == '*':

		sfx = S_RegisterSexedSound(entnum, sfx.name)

		if not sfx:

			return

	# make sure the sound is loaded
	sc = S_LoadSound(sfx)

	if not sc:

		# couldn't load the sound's data
		return

	# make the playsound_t
	ps = S_AllocPlaysound()

	if not ps:

		return

	if origin is not None:

		if not GetBSPEntitySoundOrigin(entnum, listener_origin, ps.origin):

			shared.VectorCopy(origin, ps.origin)

		ps.fixed_origin = True

	else:

		ps.fixed_origin = False

	"""
	if (sfx->name[0] && s_feedback_kind->value == 1)
	{
		...
		Haptic_Feedback(
			sfx->name, effect_volume,
			effect_duration,
			sfx->cache->begin, sfx->cache->attack, sfx->cache->fade,
			dir_x, dir_y, dir_z, distance_direction);
	}
	else if (sfx->name[0] && s_feedback_kind->value == 0)
	{
		...
		Controller_Rumble(sfx->name, direction, !ps->fixed_origin,
			effect_duration, effect_volume);
	}
	"""
	# Q2PORT: the haptic and rumble feedback goes to the game controllers
	# (input/sdl2.c), which are not ported (group 14)

	ps.entnum = entnum
	ps.entchannel = entchannel
	ps.attenuation = attenuation
	ps.sfx = sfx

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		ps.begin = int(paintedtime + timeofs * 1000) # unsigned
		ps.volume = fvol

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			ps.begin = sound_sdl.SDL_DriftBeginofs(timeofs)
			ps.volume = fvol * 255

	if _game is None:

		_game = cvar.Cvar_Get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)

	is_mission_pack = (
		(_game.string == "") or
		(_game.string == "rogue") or
		(_game.string == "xatrix")) #const qboolean

	# Q2PORT: sort is an index into s_pendingplays, len(s_pendingplays) for the
	# list head (&s_pendingplays); ps is put in front of it
	if ((s_ps_sorting.value == 1 and is_mission_pack) or
			s_ps_sorting.value == 2 or
			s_ps_sorting.value == 3):

		sort = 0 # s_pendingplays.next
		while sort != builtins.len(s_pendingplays) and s_pendingplays[sort].begin <= ps.begin:

			sort += 1

	elif not is_mission_pack and s_ps_sorting.value == 1:

		sort = 0 # s_pendingplays.next
		while sort != builtins.len(s_pendingplays) and s_pendingplays[sort].begin < ps.begin:

			sort += 1

	else:

		# No sorting. Just append at the end.
		# Q2PORT: as the C, this is in front of the last one (s_pendingplays.prev)
		sort = builtins.len(s_pendingplays) - 1 if s_pendingplays else 0

	# ps->next = sort; ps->prev = sort->prev; ps->next->prev = ps; ps->prev->next = ps;
	s_pendingplays.insert(sort, ps)

"""
 * Plays a sound when we're not
 * in a level. Used by the menu
 * system.
"""
def S_StartLocalSound(sound: str): #const char *

	#sfx_t *sfx;

	if sound_started == sound_local.SS_NOT:

		return

	sfx = S_RegisterSound(sound)

	if not sfx:

		clientserver.Com_Printf("{}: can't cache {}\n".format("S_StartLocalSound", sound))
		return

	S_StartSound(None, -1, 0, sfx, 1, 1, 0)

"""
 * Stops all sounds
"""
def S_StopAllSounds(): #void

	global s_freeplays, s_pendingplays

	#int i;

	if sound_started == sound_local.SS_NOT:

		return

	# clear all the playsounds
	for ps in s_playsounds:
		ps.clear() # memset(s_playsounds, 0, sizeof(s_playsounds));
	s_freeplays = [] # s_freeplays.next = s_freeplays.prev = &s_freeplays;
	s_pendingplays = [] # s_pendingplays.next = s_pendingplays.prev = &s_pendingplays;

	for i in range(MAX_PLAYSOUNDS):

		s_freeplays.insert(0, s_playsounds[i]) # linked in after &s_freeplays

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		openal.AL_StopAllChannels()

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			sound_sdl.SDL_ClearBuffer()

	# clear all the channels
	for ch in channels:
		ch.clear() # memset(channels, 0, sizeof(channels));

"""
 * Builds a list of all sounds
"""
def S_BuildSoundList(sounds: list): #int *

	#int i;
	ambient = s_ambient.value #const float
	plnum = cl_main.cl.playernum + 1 #const int

	i = 0
	while i < cl_main.cl.frame.num_entities and i <= client_h.MAX_CL_ENTNUM:

		#int num;
		#entity_state_t *ent;

		num = (cl_main.cl.frame.parse_entities + i) & (client_h.MAX_PARSE_ENTITIES - 1)
		ent = cl_main.cl_parse_entities[num]

		if (ambient == 2) and not ent.modelindex:

			sounds[i] = 0

		elif (ambient == 3) and (ent.number != plnum):

			sounds[i] = 0

		else:

			sounds[i] = ent.sound

		i += 1

"""
 * Cinematic streaming and voice over network.
 * This could be used for chat over network, but
 * that would be terrible slow.
"""
def S_RawSamples(samples: int, rate: int, width: int,
		channels: int, data, volume: float): #int, int, int, int, const byte *, float

	global s_rawend

	if sound_started == sound_local.SS_NOT:

		return

	if s_rawend < paintedtime:

		s_rawend = paintedtime

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		openal.AL_RawSamples(samples, rate, width, channels, data, volume)

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			sound_sdl.SDL_RawSamples(samples, rate, width, channels, data, volume)

"""
 * Calls the update functions of the
 * backend. Those perform their
 * calculations and fill their buffers.
"""
def S_Update(origin, forward, right, up): #vec3_t, vec3_t, vec3_t, vec3_t

	if sound_started == sound_local.SS_NOT:

		return

	if s_active == False:

		return

	shared.VectorCopy(origin, listener_origin)
	shared.VectorCopy(forward, listener_forward)
	shared.VectorCopy(right, listener_right)
	shared.VectorCopy(up, listener_up)

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		openal.AL_Update()

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			sound_sdl.SDL_Update()

"""
 * Plays one sample. Called
 * by the "play" cmd.
"""
def S_Play(): #void (static)

	#int i;

	i = 1

	while i < cmdparser.Cmd_Argc():

		#char name[256];
		#sfx_t *sfx;

		if '.' not in cmdparser.Cmd_Argv(i): # !strrchr(Cmd_Argv(i), '.')

			name = cmdparser.Cmd_Argv(i)[:256 - 4 - 1] # Q_strlcpy(name, Cmd_Argv(i), sizeof(name) - 4);
			name += ".wav"

		else:

			name = cmdparser.Cmd_Argv(i)[:256 - 1]

		if ".." in name or (name[0] == '/') or (name[0] == '\\'):

			clientserver.Com_Printf("Bad filename {}\n".format(name))
			return

		sfx = S_RegisterSound(name)
		S_StartSound(None, cl_main.cl.playernum + 1, 0, sfx, 1.0, 1.0, 0)
		i += 1

"""
 * List all loaded sounds
"""
def S_SoundList(): #void (static)

	#int i;
	#sfx_t *sfx;
	#sfxcache_t *sc;
	#int size, total, used;
	#int numsounds;
	#qboolean freeup;

	total = 0
	used = 0
	numsounds = 0

	for i in range(num_sfx):

		sfx = known_sfx[i]
		if not sfx.name:

			continue

		if sfx.registration_sequence == s_registration_sequence:

			used += 1

		sc = sfx.cache

		if sc:

			size = sc.length * sc.width * (sc.stereo + 1)
			total += size
			# Q2PORT: log10 of 0 is -inf in C, a ValueError in Python
			db = 10 * math.log10(sc.volume / (2 << 15)) if sc.volume > 0 else float("-inf")
			clientserver.Com_Printf("{}({:2d}b) {:8d}({} ch) {} {:2.1f} dB {:.1f}s:{:.1f}..{:.1f}..{:.1f}..{:.1f}\n".format(
					"L" if sc.loopstart != -1 else " ",
					sc.width * 8, size,
					(sc.stereo + 1), sfx.name,
					db,
					sc.length / 1000 / (sc.stereo + 1),
					sc.begin / 1000,
					sc.attack / 1000,
					sc.fade / 1000,
					sc.end / 1000))

		else:

			if sfx.name[0] == '*':

				clientserver.Com_Printf("    placeholder : {}\n".format(sfx.name))

			else:

				clientserver.Com_Printf("    not loaded  : {}\n".format(sfx.name))

		numsounds += 1

	clientserver.Com_Printf("Total resident: {} bytes ({:.2f} MB) in {} sounds\n".format(total,
			total / 1024 / 1024, numsounds))
	freeup = S_HasFreeSpace()
	clientserver.Com_Printf("Used {} of {} sounds{}.\n".format(used, sound_max, ", has free space" if freeup else ""))

# -----------------------------------------------------------------

"""
 * Prints information about the
 * active sound backend
"""
def S_SoundInfo_f(): #void (static)

	if sound_started == sound_local.SS_NOT:

		clientserver.Com_Printf("Sound system not started\n")
		return

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		qal.QAL_SoundInfo(True)

	else:
	#endif

		sound_sdl.SDL_SoundInfo()

"""
 * Activate or deactivate sound backend
"""
def S_Activate(active: bool): #qboolean

	global s_active

	s_active = active

	if active == False:

		S_StopAllSounds()

"""
 * Initializes the sound system
 * and it's requested backend
"""
def S_Init(): #void

	global s_volume, s_khz, s_loadas8bit, s_mixahead, s_show, s_testsound, s_ambient
	global s_underwater, s_underwater_gain_hf, s_doppler, s_ps_sorting, s_reverb_preset
	global s_occlusion_strength, s_feedback_kind
	global sound_started, num_sfx, paintedtime, sound_max, s_active

	#cvar_t *cv;

	clientserver.Com_Printf("\n------- sound initialization -------\n")

	cv = cvar.Cvar_Get("s_initsound", "1", 0)

	if not cv.value:

		clientserver.Com_Printf("Not initializing.\n")
		clientserver.Com_Printf("------------------------------------\n\n")
		return

	s_volume = cvar.Cvar_Get("s_volume", "0.7", shared.CVAR_ARCHIVE)
	s_khz = cvar.Cvar_Get("s_khz", "44", shared.CVAR_ARCHIVE)
	s_loadas8bit = cvar.Cvar_Get("s_loadas8bit", "0", shared.CVAR_ARCHIVE)
	s_mixahead = cvar.Cvar_Get("s_mixahead", "0.14", shared.CVAR_ARCHIVE)
	s_show = cvar.Cvar_Get("s_show", "0", 0)
	s_testsound = cvar.Cvar_Get("s_testsound", "0", 0)
	s_ambient = cvar.Cvar_Get("s_ambient", "1", 0)
	s_underwater = cvar.Cvar_Get("s_underwater", "1", shared.CVAR_ARCHIVE)
	s_underwater_gain_hf = cvar.Cvar_Get("s_underwater_gain_hf", "0.25", shared.CVAR_ARCHIVE)
	s_doppler = cvar.Cvar_Get("s_doppler", "0", shared.CVAR_ARCHIVE)
	s_ps_sorting = cvar.Cvar_Get("s_ps_sorting", "1", shared.CVAR_ARCHIVE)
	# Reverb and occlusion is fully disabled by default
	s_reverb_preset = cvar.Cvar_Get("s_reverb_preset", "-1", shared.CVAR_ARCHIVE)
	s_occlusion_strength = cvar.Cvar_Get("s_occlusion_strength", "0", shared.CVAR_ARCHIVE)
	# Feedback kind: 0 - rumble, 1 - haptic
	s_feedback_kind = cvar.Cvar_Get("s_feedback_kind", "0", shared.CVAR_ARCHIVE)

	cmdparser.Cmd_AddCommand("play", S_Play)
	cmdparser.Cmd_AddCommand("stopsound", S_StopAllSounds)
	cmdparser.Cmd_AddCommand("soundlist", S_SoundList)
	cmdparser.Cmd_AddCommand("soundinfo", S_SoundInfo_f)

	#if USE_OPENAL
	cv = cvar.Cvar_Get("s_openal", "1", shared.CVAR_ARCHIVE)

	if cv.value and openal.AL_Init():

		sound_started = sound_local.SS_OAL

	else:
	#endif

		if sound_sdl.SDL_BackendInit():

			sound_started = sound_local.SS_SDL

		else:

			sound_started = sound_local.SS_NOT
			return

	num_sfx = 0
	paintedtime = 0
	sound_max = 0
	s_active = True

	ogg.OGG_Init()

	clientserver.Com_Printf("Sound sampling rate: {}\n".format(sound.speed))
	S_StopAllSounds()

	clientserver.Com_Printf("------------------------------------\n\n")

"""
 * Shutdown the sound system
 * and it's backend
"""
def S_Shutdown(): #void

	global num_sfx, sound_started, s_numchannels

	#int i;
	#sfx_t *sfx;

	if sound_started == sound_local.SS_NOT:

		return

	S_StopAllSounds()
	ogg.OGG_Shutdown()

	# free all sounds
	for i in range(num_sfx):

		sfx = known_sfx[i]
		if not sfx.name:

			continue

		#if USE_OPENAL
		if sound_started == sound_local.SS_OAL:

			openal.AL_DeleteSfx(sfx)
		#endif

		#if (sfx->cache) Z_Free(sfx->cache);
		#if (sfx->truename) Z_Free(sfx->truename);

	for sfx in known_sfx:
		sfx.clear() # memset(known_sfx, 0, sizeof(known_sfx));
	num_sfx = 0

	#if USE_OPENAL
	if sound_started == sound_local.SS_OAL:

		openal.AL_Shutdown()

	else:
	#endif

		if sound_started == sound_local.SS_SDL:

			sound_sdl.SDL_BackendShutdown()

	sound_started = sound_local.SS_NOT
	s_numchannels = 0

	cmdparser.Cmd_RemoveCommand("soundlist")
	cmdparser.Cmd_RemoveCommand("soundinfo")
	cmdparser.Cmd_RemoveCommand("play")
	cmdparser.Cmd_RemoveCommand("stopsound")

"""
 * Called to get the sound spatialization origin
"""

_soundpos = None #static const cvar_t *, GetBSPEntitySoundOrigin

"""
BSP model entities (doors, elevators...)
use origin as an offset added to mins/maxs
"""
def GetBSPEntitySoundOrigin(ent: int, listener_org, org)->bool: #int, const vec3_t, vec3_t (returns qboolean)

	global _soundpos

	#centity_t *old;
	#cmodel_t *cm;
	amin = np.zeros((3,), dtype=np.float32) #vec3_t
	amax = np.zeros((3,), dtype=np.float32) #vec3_t
	#int mi;

	if (ent < 0) or (ent >= cl_main.cl_numentities):

		return False

	old = cl_main.cl_entities[ent]

	mi = old.current.modelindex
	cm = cl_main.cl.model_clip[mi] if (mi > 0 and mi < shared.MAX_MODELS) else None

	if not cm:

		return False

	if not _soundpos:

		_soundpos = cvar.Cvar_Get("s_bsp_soundpos", "1", shared.CVAR_ARCHIVE)

		if not _soundpos:

			return False

	if not _soundpos.value:

		return False

	if listener_org is None or _soundpos.value < 2.0:

		shared.VectorAdd(cm.mins, cm.maxs, org)
		shared_c.VectorScale(org, 0.5, org)
		shared.VectorAdd(org, old.lerp_origin, org)

	else:

		shared.VectorCopy(cm.mins, amin)
		shared.VectorAdd(amin, old.lerp_origin, amin)

		shared.VectorCopy(cm.maxs, amax)
		shared.VectorAdd(amax, old.lerp_origin, amax)

		shared_c.ClosestPointOnBounds(listener_org, amin, amax, org)

	return True

def GetEntitySoundOrigin(ent: int, listener_org, org): #int, const vec3_t, vec3_t

	#vec_t *lerp_origin;

	if not GetBSPEntitySoundOrigin(ent, listener_org, org):

		lerp_origin = cl_main.cl_entities[ent].lerp_origin if ((ent >= 0) and (ent < cl_main.cl_numentities)) else shared_c.vec3_origin

		shared.VectorCopy(lerp_origin, org)
