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

import builtins
import io
import math
import struct
import numpy as np
pass
pass
from backends.unix import system
from linux import snd_linux
from client import snd_mix, snd_loc, snd_mem, cl_main
pass
import pygame
from common.header import shared
from common.header import common as common_h
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from client import cl_main
from client import cl_parse
from client.sound import ogg
from client.header import client as client_h
"""
// snd_dma.c -- main control for any streaming sound output device

#include "client.h"
#include "snd_loc.h"

// =======================================================================
// Internal sound data & structures
// =======================================================================

"""
# only begin attenuating sound volumes when outside the FULLVOLUME range
SOUND_FULLVOLUME	= 80

SOUND_LOOPATTENUATE	= 0.003

s_registration_sequence = 0 #int
channels = [] #channel_t[]
for i in range(snd_loc.MAX_CHANNELS):
	channels.append(snd_loc.channel_t())

snd_initialized = False #qboolean
snd_is_underwater = False #qboolean, set by pmove (Yamagi)
sound_started = False #int

dma = snd_loc.dma_t()

listener_origin = np.zeros((3,), dtype=np.float32) #vec3_t
listener_forward = np.zeros((3,), dtype=np.float32) #vec3_t
listener_right = np.zeros((3,), dtype=np.float32) #vec3_t
listener_up = np.zeros((3,), dtype=np.float32) #vec3_t

s_registering = False #qboolean

soundtime = None	# int, sample PAIRS
paintedtime = None 	# int, sample PAIRS

# during registration it is possible to have more sounds
# than could actually be referenced during gameplay,
# because we don't want to free anything until we are
# sure we won't need it.
MAX_SFX = (shared.MAX_SOUNDS*2)
known_sfx = [] #sfx_t [MAX_SFX];
for i in range(MAX_SFX):
	known_sfx.append(snd_loc.sfx_t())

num_sfx = 0 #int			
sound_max = 0 #static int
"""
#define		MAX_PLAYSOUNDS	128
playsound_t	s_playsounds[MAX_PLAYSOUNDS];
playsound_t	s_freeplays;
"""
MAX_PLAYSOUNDS = 128 #int Q2PORT: the C's #define
s_playsounds = None #playsound_t[MAX_PLAYSOUNDS]
s_freeplays = None #playsound_t *
s_pendingplays = [] #playsound_t (linked list)
s_beginofs = 0 #int

s_volume = None #cvar_t		*
s_testsound = None #cvar_t		*
s_loadas8bit = None #cvar_t		*
s_khz = None #cvar_t		*
s_show = None #cvar_t		*
s_mixahead = None #cvar_t		*
s_primary = None #cvar_t		*
s_ambient = None #cvar_t		*
s_underwater = None #cvar_t		*
s_underwater_gain_hf = None #cvar_t		*
s_doppler = None #cvar_t		*
s_ps_sorting = None #cvar_t		*
s_reverb_preset = None #cvar_t		*
s_occlusion_strength = None #cvar_t		*
s_feedback_kind = None #cvar_t		*
s_bsp_soundpos = None #cvar_t		*
cl_paused = None #cvar_t		*

s_rawend = 0 #int
s_rawsamples = [] #portable_samplepair_t	[MAX_RAW_SAMPLES];
for i in range(snd_loc.MAX_RAW_SAMPLES):
	s_rawsamples.append(snd_loc.portable_samplepair_t())


## ====================================================================
## User-setable variables
## ====================================================================


def S_SoundInfo_f():

	if not sound_started:
	
		clientserver.Com_Printf("Sound system not started\n")
		return

	# Q2PORT: the C's USE_OPENAL / QAL_SoundInfo branch is not ported
	snd_linux.SDL_SoundInfo()

"""
================
S_Init
================
"""
def S_Init ():

	global s_volume, s_testsound, s_loadas8bit, s_khz, s_show, s_mixahead
	global sound_started, num_sfx, soundtime, paintedtime
	global cl_paused, s_ambient, s_underwater, s_underwater_gain_hf, s_doppler
	global s_ps_sorting, s_reverb_preset, s_occlusion_strength, s_feedback_kind

	#cvar_t	*cv;
	global s_numchannels, s_active, s_playsounds, s_freeplays, sound_max

	clientserver.Com_Printf("\n------- sound initialization -------\n")

	cv = cvar.Cvar_Get ("s_initsound", "1", 0)

	if not cv.value:
	
		clientserver.Com_Printf ("Not initializing.\n")
		clientserver.Com_Printf("------------------------------------\n\n")
		return

	s_volume = cvar.Cvar_Get ("s_volume", "0.7", shared.CVAR_ARCHIVE)
	s_khz = cvar.Cvar_Get ("s_khz", "44", shared.CVAR_ARCHIVE)
	s_loadas8bit = cvar.Cvar_Get ("s_loadas8bit", "0", shared.CVAR_ARCHIVE)
	s_mixahead = cvar.Cvar_Get ("s_mixahead", "0.14", shared.CVAR_ARCHIVE)
	s_show = cvar.Cvar_Get ("s_show", "0", 0)
	s_testsound = cvar.Cvar_Get ("s_testsound", "0", 0)
	s_ambient = cvar.Cvar_Get ("s_ambient", "1", 0)
	s_underwater = cvar.Cvar_Get ("s_underwater", "1", shared.CVAR_ARCHIVE)
	s_underwater_gain_hf = cvar.Cvar_Get ("s_underwater_gain_hf", "0.25", shared.CVAR_ARCHIVE)
	s_doppler = cvar.Cvar_Get ("s_doppler", "0", shared.CVAR_ARCHIVE)
	s_ps_sorting = cvar.Cvar_Get ("s_ps_sorting", "1", shared.CVAR_ARCHIVE)
	# Reverb and occlusion is fully disabled by default
	# Q2PORT: OpenAL only, registered so saved configs load unchanged
	s_reverb_preset = cvar.Cvar_Get ("s_reverb_preset", "-1", shared.CVAR_ARCHIVE)
	s_occlusion_strength = cvar.Cvar_Get ("s_occlusion_strength", "0", shared.CVAR_ARCHIVE)
	# Feedback kind: 0 - rumble, 1 - haptic
	s_feedback_kind = cvar.Cvar_Get ("s_feedback_kind", "0", shared.CVAR_ARCHIVE)

	cmdparser.Cmd_AddCommand("play", S_Play)
	cmdparser.Cmd_AddCommand("stopsound", S_StopAllSounds)
	cmdparser.Cmd_AddCommand("soundlist", S_SoundList)
	cmdparser.Cmd_AddCommand("soundinfo", S_SoundInfo_f)

	# Q2PORT: the C's USE_OPENAL / s_openal branch (AL_Init) is not ported

	if snd_linux.SNDDMA_Init(): # Q2PORT: the C's SDL_BackendInit
	
		# Q2PORT: the rest of the pygame backend setup (the C does it in SDL_BackendInit)
		pygame.mixer.set_num_channels(snd_loc.MAX_CHANNELS)
		# the C sets s_numchannels = MAX_CHANNELS; the port keeps the pygame mixer channel count
		s_numchannels = min(snd_loc.MAX_CHANNELS, pygame.mixer.get_num_channels())

		for ch_idx in range(s_numchannels):
			channels[ch_idx].chan = pygame.mixer.Channel(ch_idx)

		snd_mix.S_InitScaletable ()
		soundtime = 0

		sound_started = 1 # SS_SDL
	
	else:
	
		sound_started = 0 # SS_NOT
		return

	# Q2PORT: the C's static s_playsounds[MAX_PLAYSOUNDS] array, linked by S_StopAllSounds
	s_playsounds = [snd_loc.playsound_t() for _ in range(MAX_PLAYSOUNDS)]

	num_sfx = 0
	paintedtime = 0
	sound_max = 0
	s_active = True

	ogg.OGG_Init()

	clientserver.Com_Printf("Sound sampling rate: {}\n".format(dma.speed))
	S_StopAllSounds()

	clientserver.Com_Printf("------------------------------------\n\n")

"""
=================
S_Shutdown
=================
"""
def S_Shutdown():

	#int		i;
	#sfx_t	*sfx;
	global sound_started, known_sfx, num_sfx, s_numchannels

	if not sound_started:
		return

	S_StopAllSounds()
	ogg.OGG_Shutdown()
	s_numchannels = 0
	"""
	// reset the sound buffer
	if (dma.name)
	{
		memset(dma.name, 0, sizeof(dma.name));
		memset(dma.buffer, 0, dma.dmaarea);
	}
	"""
	snd_linux.SNDDMA_Shutdown() # Q2PORT: the C's SNDDMA_Shutdown is id's; the port keeps the legacy hook

	sound_started = 0

	cmdparser.Cmd_RemoveCommand("soundlist")
	cmdparser.Cmd_RemoveCommand("soundinfo")
	cmdparser.Cmd_RemoveCommand("play")
	cmdparser.Cmd_RemoveCommand("stopsound")

	# free all sounds
	for i in range(num_sfx):
	
		sfx=known_sfx[i]
		if not sfx.name:
			continue
		sfx.clear()

	num_sfx = 0

"""
=================
S_Activate

Activate or deactivate sound backend
=================
"""
def S_Activate (active): #qboolean

	global s_active

	s_active = active

	if active == False:
		S_StopAllSounds()



"""
// =======================================================================
// Load a sound
// =======================================================================

==================
S_GetSfxByName

Returns the sfx with the specified name, NULL if none exists
==================
"""
def S_GetSfxByName (name): #char * (returns sfx_t *)

	"""
	int i;
	"""

	for i in range(num_sfx):
		if known_sfx[i].name is not None and known_sfx[i].name == name:
			return known_sfx[i]

	return None

"""
==================
S_NextFreeSfx

Finds the next free sfx slot
==================
"""
def S_NextFreeSfx (): #void (returns sfx_t *)

	global num_sfx

	"""
	sfx_t	*sfx;
	"""

	# look for an existing free slot
	for i in range(num_sfx):
		if not known_sfx[i].name:
			return known_sfx[i]

	# allocate a new one
	if num_sfx >= MAX_SFX:
		return None

	sfx = known_sfx[num_sfx]
	num_sfx += 1 # the C returns &known_sfx[num_sfx++]
	return sfx

"""
==================
S_FindOrCreateSfx

Finds the sfx with the specified name, creating it if necessary
==================
"""
def S_FindOrCreateSfx (name): #char * (returns sfx_t *)

	global num_sfx
	#sfx_t	*sfx;

	if not name:
		clientserver.Com_Printf ("S_FindOrCreateSfx: blank name\n")
		return None

	sfx = S_GetSfxByName(name)

	if sfx is not None:
		return sfx

	if len(name) >= shared.MAX_QPATH:
		clientserver.Com_Printf ("S_FindOrCreateSfx: name is too long: {}\n".format(name))
		return None

	sfx = S_NextFreeSfx()

	if sfx is None:
		clientserver.Com_Printf ("S_FindOrCreateSfx: out of sfx for: {}\n".format(name))
		return None

	sfx.truename = None
	sfx.name = name
	sfx.registration_sequence = s_registration_sequence
	sfx.is_silenced_muzzle_flash = False

	return sfx



"""
=================
S_AliasName

Registers an alias name for a sound
=================
"""
def S_AliasName (aliasname, truename): #char *, char * (returns sfx_t *)

	#sfx_t	*sfx;

	if len(aliasname) >= shared.MAX_QPATH:
		clientserver.Com_Printf ("S_AliasName: name is too long: {}\n".format(aliasname))
		return None

	sfx = S_NextFreeSfx()

	if sfx is None:
		clientserver.Com_Printf ("S_AliasName: out of sfx for: {}\n".format(aliasname))
		return None

	sfx.cache = None
	sfx.name = aliasname
	sfx.registration_sequence = s_registration_sequence
	sfx.truename = truename # Q2PORT: the C does strdup(truename); the port shares the string

	return sfx


def S_BeginRegistration ():

	global s_registration_sequence, s_registering

	s_registration_sequence+=1
	s_registering = True

"""
==================
S_RegisterSound

==================
"""

"""
==================
S_RegisterSound

==================
"""
def S_RegisterSound (name): #char * (returns sfx_t *)

	global sound_started
	#sfx_t	*sfx;

	if not sound_started:
		return None

	sfx = S_FindOrCreateSfx(name)

	if sfx is None:
		return None

	sfx.registration_sequence = s_registration_sequence

	if not s_registering:
		snd_mem.S_LoadSound (sfx)

	return sfx

"""
 * Extracts the model name from a player configstring
 """
def GetModelName (cs, n): #const char *, size_t (returns char *model)

	#char *end;

	if not cs:
		return ''

	p = cs.find('\\')

	if p == -1:
		return ''

	p += 1

	if len(cs) - p >= n: # strlen(p) >= n
		return ''

	model = cs[p:] # Q_strlcpy(model, p, n);

	end = model.find('/')

	if end != -1:
		model = model[:end]

	return model

"""
 * Checks that the sfx list has free space
 """
def S_HasFreeSpace(): #void (returns qboolean)

	#int		i, used;

	used = 0

	# check used slots
	for i in range(num_sfx):
	
		sfx = known_sfx[i]
		if sfx.name is None:
			continue
		if sfx.registration_sequence == s_registration_sequence:
			used += 1

	global sound_max
	if sound_max < used:
		sound_max = used

	# should same size of free slots as currently used
	return (num_sfx + used) < MAX_SFX



"""
=====================
S_EndRegistration

=====================
"""
def S_EndRegistration ():
	
	global s_registering

	#int		i;
	#sfx_t	*sfx;
	#int		size;

	if not S_HasFreeSpace():
	
		# free any sounds not from this registration sequence
		for i in range(num_sfx):
		
			sfx = known_sfx[i]
			if sfx.name is None: # !sfx->name[0]
				continue
			if sfx.registration_sequence != s_registration_sequence:
				# don't need this sound
				sfx.clear() # Z_Free (sfx->cache); memset (sfx, 0, sizeof(*sfx));
				# Z_Free (sfx->truename)
				
			else:
				# make sure it is paged in
				pass # Com_PageInMemory is not needed in python
	
	# load everything in
	for i in range(num_sfx):
	
		sfx = known_sfx[i]
		if sfx.name is None:
			continue
		snd_mem.S_LoadSound (sfx)
	
	s_registering = False


"""
=================
S_PickChannel
=================
"""
def S_PickChannel(entnum, entchannel): #int, int (returns channel_t *)

	"""
	int			ch_idx;
	int			first_to_die;
	int			life_left;
	channel_t	*ch;
	"""
	global channels

	if entchannel < 0:
		clientserver.Com_Error (shared.ERR_DROP, "S_PickChannel: entchannel<0")

	# Check for replacement sound, or find the best one to replace
	first_to_die = -1
	life_left = 2147483647 # 0x7fffffff

	plnum = cl_main.cl.playernum + 1

	for ch_idx in range(s_numchannels):
	
		ch = channels[ch_idx]

		# channel 0 never overrides
		if (entchannel != 0) and \
			(ch.entnum == entnum) and \
			(ch.entchannel == entchannel):
			
			# always override sound from same entity
			first_to_die = ch_idx
			break
		
		# don't let monster sounds override player sounds
		if (ch.entnum == plnum) and (entnum != plnum) and ch.sfx:
			continue

		if ch.end - paintedtime < life_left:
			
			life_left = ch.end - paintedtime
			first_to_die = ch_idx
		
	if first_to_die == -1:
		return None

	ch = channels[first_to_die]

	ch.clear()
	ch.chan.stop() # Q2PORT: the C's SDL memset leaves the channel dead; a pygame channel keeps playing until stopped
	ch.loop_sfx = None # Q2PORT: whatever the pygame channel plays next replaces the loop

	return ch

"""
=================
S_AllocPlaysound
=================
"""
def S_AllocPlaysound (): #void (returns playsound_t *)

	global s_freeplays

	if not s_freeplays:
		# no free playsounds, this results in stuttering and cracking
		return None

	# unlink from freelist
	return s_freeplays.pop()

"""
=================
S_FreePlaysound
=================
"""
def S_FreePlaysound (ps): #playsound_t *

	global s_freeplays

	# add to free list
	s_freeplays.append(ps)


def S_SpatializeOrigin (origin, master_vol, dist_mult): #vec3_t, float, float (returns int *left_vol, int *right_vol)
	
	"""
	vec_t		dot;
	vec_t		dist;
	vec_t		lscale, rscale, scale;
	vec3_t		source_vec;
	"""
	source_vec = np.zeros((3,), dtype=np.float32)

	if cl_main.cls.state != client_h.connstate_t.ca_active:
	
		left_vol = right_vol = 255
		return left_vol, right_vol
	
	# calculate stereo seperation and distance attenuation
	shared.VectorSubtract(origin, listener_origin, source_vec)

	dist = shared_c.VectorNormalize(source_vec)
	dist -= SOUND_FULLVOLUME
	if dist < 0:
		dist = 0			# close enough to be at full volume
	dist *= dist_mult		# different attenuation levels
	
	dot = shared.DotProduct(listener_right, source_vec)

	if dma.channels == 1 or not dist_mult:
		# no attenuation = no spatialization
		rscale = 1.0
		lscale = 1.0
	
	else:
	
		rscale = 0.5 * (1.0 + dot)
		lscale = 0.5*(1.0 - dot)
	
	# add in distance effect
	scale = (1.0 - dist) * rscale
	right_vol = int (master_vol * scale)
	if right_vol < 0:
		right_vol = 0

	scale = (1.0 - dist) * lscale
	left_vol = int (master_vol * scale)
	if left_vol < 0:
		left_vol = 0

	return left_vol, right_vol

"""
=================
S_Spatialize
=================
"""
def S_Spatialize(ch): #channel_t *

	origin = np.zeros((3,), dtype=np.float32)

	# anything coming from the view entity will always be full volume
	if (ch.entnum == -1) or (ch.entnum == cl_main.cl.playernum+1):
	
		ch.leftvol = ch.master_vol
		ch.rightvol = ch.master_vol
		return
	

	if ch.fixed_origin:									
		shared.VectorCopy(ch.origin, origin)

	else:
		origin = GetEntitySoundOrigin (ch.entnum)

	ch.leftvol, ch.rightvol = S_SpatializeOrigin (origin, ch.master_vol, ch.dist_mult)


"""
====================
GetBSPEntitySoundOrigin

BSP model entities (doors, elevators...) use origin as an
offset added to mins/maxs
====================
"""
def GetBSPEntitySoundOrigin (ent, listener_org, org): #int, vec3_t, vec3_t (returns qboolean)

	global s_bsp_soundpos
	#centity_t	*old;
	#cmodel_t	*cm;
	#vec3_t		amin, amax;
	#int			mi;

	if (ent < 0) or (ent >= cl_main.cl_numentities):
		return False

	old = cl_main.cl_entities[ent]

	mi = old.current.modelindex
	cm = cl_main.cl.model_clip[mi] if (mi > 0 and mi < shared.MAX_MODELS) else None

	if cm is None:
		return False

	if s_bsp_soundpos is None:
		s_bsp_soundpos = cvar.Cvar_Get("s_bsp_soundpos", "1", shared.CVAR_ARCHIVE)
		if s_bsp_soundpos is None:
			return False

	if not s_bsp_soundpos.value:
		return False

	if listener_org is None or s_bsp_soundpos.value < 2.0:
		shared.VectorAdd(cm.mins, cm.maxs, org)
		shared_c.VectorScale(org, 0.5, org)
		shared.VectorAdd(org, old.lerp_origin, org)
	else:
		amin = np.zeros((3,), dtype=np.float32)
		amax = np.zeros((3,), dtype=np.float32)
		shared.VectorCopy(cm.mins, amin)
		shared.VectorAdd(amin, old.lerp_origin, amin)
		shared.VectorCopy(cm.maxs, amax)
		shared.VectorAdd(amax, old.lerp_origin, amax)
		shared_c.ClosestPointOnBounds(listener_org, amin, amax, org)

	return True

"""
====================
GetEntitySoundOrigin

Returns the origin of the specified entity
====================
"""
def GetEntitySoundOrigin (ent): #int (returns vec3_t)

	org = np.zeros((3,), dtype=np.float32)

	if not GetBSPEntitySoundOrigin(ent, listener_origin, org):
		if (ent >= 0) and (ent < cl_main.cl_numentities):
			shared.VectorCopy(cl_main.cl_entities[ent].lerp_origin, org)
		# else: org stays vec3_origin

	return org

"""
=================
S_IssuePlaysound

Take the next playsound and begin it on the channel
This is never called directly by S_Play*, but only
by the update loop.
=================
"""
def S_IssuePlaysound (ps): #playsound_t *

	"""
	channel_t	*ch;
	sfxcache_t	*sc;
	"""

	if not ps:
		return

	if s_show.value:
		clientserver.Com_Printf ("Issue {}\n".format(ps.begin))

	if s_ps_sorting.value == 3 and ps.sfx.is_silenced_muzzle_flash:
		S_FreePlaysound(ps)
		return

	# pick a channel to play on
	ch = S_PickChannel(ps.entnum, ps.entchannel)
	if ch is None:
		S_FreePlaysound(ps)
		return

	sc = snd_mem.S_LoadSound (ps.sfx)
	if sc is None:
		clientserver.Com_Printf ("S_IssuePlaysound: couldn't load {}\n".format(ps.sfx.name))
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

	ch.master_vol = int(ps.volume)

	S_Spatialize(ch)

	ch.pos = paintedtime # Q2PORT: the C mixer advances ch->pos as it paints; pygame plays it, so the lifecycle pass uses the start time
	ch.end = paintedtime + sc.length

	# free the playsound
	S_FreePlaysound(ps)

	# Q2PORT: the C mixer scales by ch->leftvol and s_volume (snd_vol, snd_scaletable) as it paints
	ch.chan.set_volume(ch.leftvol/255 * s_volume.value, ch.rightvol/255 * s_volume.value)
	ch.chan.play(sc.data)



"""
=====================
S_RegisterSexedSound

=====================
"""
def S_RegisterSexedSound (entnum, base): #int, char * (returns struct sfx_s *)

	"""
	sfx_t		*sfx;
	char		model[MAX_QPATH];
	char		sexedFilename[MAX_QPATH];
	char		*cs;
	"""

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
	sexedFilename = "#players/{}/{}".format(model, base[1:])

	sfx = S_GetSfxByName(sexedFilename)

	if sfx is None:
		
		# no, so see if it exists
		if common_h.FS_FileExists(sexedFilename[1:]):
			
			# yes, close the file and register it
			sfx = S_RegisterSound (sexedFilename)
		
		else:
			
			# no, revert to the male sound in the pak0.pak
			maleFilename = "player/male/{}".format(base[1:])

			sfx = S_AliasName (sexedFilename, maleFilename)
	
	return sfx



"""
====================
SDL_DriftBeginofs

Calculates when a sound must be started. The C has this in the SDL backend;
Q2PORT: it is inline here because the pygame backend is inline here too
====================
"""
def SDL_DriftBeginofs(timeofs): #float (returns int)

	global s_beginofs

	start = int(cl_main.cl.frame.servertime * 0.001 * dma.speed + s_beginofs)

	if start < paintedtime:
	
		start = paintedtime
		s_beginofs = int(start - (cl_main.cl.frame.servertime * 0.001 * dma.speed))
	
	elif start > paintedtime + 0.3 * dma.speed:
	
		start = int(paintedtime + 0.1 * dma.speed)
		s_beginofs = int(start - (cl_main.cl.frame.servertime * 0.001 * dma.speed))
	
	else:
	
		s_beginofs -= 10

	if timeofs == 0.0:
		return paintedtime
	return int(start + timeofs * dma.speed) # the C returns int

"""
// =======================================================================
// Start a sound effect
// =======================================================================

====================
S_StartSound

Validates the parms and queues the sound up
If pos is NULL, the sound will be dynamically sourced from the entity
Entchannel 0 will never override a playing sound
====================
"""
def S_StartSound(origin, entnum, entchannel, sfx, fvol, attenuation, timeofs): #vec3_t, int, int, sfx_t *, float, float, float

	global sound_started
	#common.Com_Printf("S_StartSound {}".format(sfx.name))

	"""
	sfxcache_t	*sc;
	playsound_t	*ps, *sort;
	"""

	if not sound_started:
		return

	# A hack to prevent temporary entities generating sounds when the sound
	# backend is not active and the game is not paused
	if s_active == False:
	    return

	if sfx is None:
		return

	# -1 means localized (menu sounds, etc.)
	if (entnum < -1) or (entnum >= cl_main.cl_numentities):
		return

	if sfx.name[0] == '*':
		sfx = S_RegisterSexedSound(entnum, sfx.name)

		if sfx is None:
			return

	# make sure the sound is loaded
	sc = snd_mem.S_LoadSound (sfx)

	if sc is None:
		return		# couldn't load the sound's data

	# make the playsound_t
	ps = S_AllocPlaysound()

	if ps is None:
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
		vec3_t orientation, direction;
		vec_t distance_direction;
		int dir_x, dir_y, dir_z;
		int effect_volume = -1;
		...
		Haptic_Feedback(
			sfx->name, effect_volume,
			effect_duration,
			sfx->cache->begin, sfx->cache->attack, sfx->cache->fade,
			dir_x, dir_y, dir_z, distance_direction);
	}
	else if (sfx->name[0] && s_feedback_kind->value == 0)
	{
		vec3_t direction = {0};
		unsigned int effect_duration = 0;
		unsigned short int effect_volume = 0;
		...
		Controller_Rumble(sfx->name, direction, !ps->fixed_origin,
			effect_duration, effect_volume);
	}
	"""
	# Q2PORT: controller rumble/haptics use SDL controllers (Controller_Rumble /
	# Haptic_Feedback in the C's keyboard.c), which pygame has no equivalent for

	ps.entnum = entnum
	ps.entchannel = entchannel
	ps.attenuation = attenuation
	ps.sfx = sfx

	# the C's SDL backend
	ps.begin = SDL_DriftBeginofs(timeofs)
	ps.volume = fvol * 255

	game = cvar.Cvar_Get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)

	is_mission_pack = \
		game.string == "" or \
		game.string == "rogue" or \
		game.string == "xatrix"

	if (s_ps_sorting.value == 1 and is_mission_pack) or \
			s_ps_sorting.value == 2 or \
			s_ps_sorting.value == 3:
		# Q2PORT: the C's s_pendingplays is a linked list, sorted by begin
		idx = 0
		while idx < len(s_pendingplays) and s_pendingplays[idx].begin <= ps.begin:
			idx += 1
		s_pendingplays.insert(idx, ps)
	elif not is_mission_pack and s_ps_sorting.value == 1:
		idx = 0
		while idx < len(s_pendingplays) and s_pendingplays[idx].begin < ps.begin:
			idx += 1
		s_pendingplays.insert(idx, ps)
	else:
		# No sorting. Just append at the end.
		s_pendingplays.append(ps)


"""
=================
S_StartLocalSound
=================
"""
def S_StartLocalSound (sound): #char *

	#sfx_t	*sfx;

	if not sound_started:
		return

	sfx = S_RegisterSound (sound)

	if sfx is None:
	
		clientserver.Com_Printf ("S_StartLocalSound: can't cache {}\n".format(sound))
		return
	
	S_StartSound (None, -1, 0, sfx, 1, 1, 0)


def S_ClearBuffer ():

	global s_rawend
	#int		clear;
		
	global sound_started

	if not sound_started:
		return;

	s_rawend = 0
	"""
	if (dma.samplebits == 8)
		clear = 0x80;
	else
		clear = 0;

	SNDDMA_BeginPainting ();
	if (dma.buffer)
		memset(dma.buffer, clear, dma.samples * dma.samplebits/8);
	SNDDMA_Submit ();
	"""

"""
==================
S_StopAllSounds
==================
"""

"""
==================
S_StopAllSounds
==================
"""
def S_StopAllSounds():
	
	#int		i;

	global sound_started, s_pendingplays, s_freeplays, channels

	if not sound_started:
		return
	"""
	# clear all the playsounds
	memset(s_playsounds, 0, sizeof(s_playsounds));
	s_freeplays.next = s_freeplays.prev = &s_freeplays;
	s_pendingplays.next = s_pendingplays.prev = &s_pendingplays;

	for (i=0 ; i<MAX_PLAYSOUNDS ; i++)
	{
		s_playsounds[i].prev = &s_freeplays;
		s_playsounds[i].next = s_freeplays.next;
		s_playsounds[i].prev->next = &s_playsounds[i];
		s_playsounds[i].next->prev = &s_playsounds[i];
	}
	"""
	# Q2PORT: the C's free list rebuild is just "all MAX_PLAYSOUNDS are free"
	s_freeplays = list(s_playsounds)
	s_pendingplays = []

	# clear all the channels
	"""
	memset(channels, 0, sizeof(channels));
	"""
	for ch in channels:
	
		if ch.chan is not None:
			ch.chan.stop() # Q2PORT: the C's SDL memset leaves the channels dead; pygame channels keep playing until stopped
		ch.clear()
		ch.loop_sfx = None # Q2PORT: the loop bookkeeping is not in the C's channel_t

	S_ClearBuffer ()



"""
==================
S_BuildSoundList
==================
"""
def S_BuildSoundList(): #void (returns int *)

	"""
	int		i;
	"""
	ambient = s_ambient.value
	#const int plnum = cl.playernum + 1
	sounds = [0] * shared.MAX_EDICTS

	for i in range(cl_main.cl.frame.num_entities):
		if i > client_h.MAX_CL_ENTNUM:
			break
		num = (cl_main.cl.frame.parse_entities + i) & (client_h.MAX_PARSE_ENTITIES - 1)
		ent = cl_main.cl_parse_entities[num]

		if (ambient == 2) and not ent.modelindex:
			sounds[i] = 0
		elif (ambient == 3) and (ent.number != cl_main.cl.playernum + 1):
			sounds[i] = 0
		else:
			sounds[i] = ent.sound

	return sounds # Q2PORT: the C fills the caller's array

"""
==================
S_AddLoopSounds

Entities with a ->sound field will generated looped sounds
that are automatically started, stopped, and merged together
as the entities are sent to the client
==================
"""
def S_AddLoopSounds ():

	"""
	int			i, j;
	int			sounds[MAX_EDICTS];
	int			left, right, left_total, right_total;
	channel_t	*ch;
	sfx_t		*sfx;
	sfxcache_t	*sc;
	int			num;
	entity_state_t	*ent;
	vec3_t		org;
	"""
	org = np.zeros((3,), dtype=np.float32)

	if cl_main.cls.state != client_h.connstate_t.ca_active:
		return

	if cl_main.cl_paused.value and cl_main.cl_audiopaused.value:
		return

	if not cl_main.cl.sound_prepped:
		return

	if not s_ambient.value:
		return

	sounds = S_BuildSoundList()

	for i in range(cl_main.cl.frame.num_entities):
	
		if not sounds[i]:
			continue

		sfx = cl_main.cl.sound_precache[sounds[i]]
		if sfx is None:
			continue		# bad sound effect
		sc = sfx.cache
		if sc is None:
			continue

		num = (cl_main.cl.frame.parse_entities + i)&(client_h.MAX_PARSE_ENTITIES-1)
		ent = cl_main.cl_parse_entities[num]

		if not GetBSPEntitySoundOrigin(ent.number, listener_origin, org):
			shared.VectorCopy(ent.origin, org)

		# find the total contribution of all sounds of this type
		left_total, right_total = S_SpatializeOrigin (org, 255.0, SOUND_LOOPATTENUATE)
		for j in range(i+1, cl_main.cl.frame.num_entities):
		
			if sounds[j] != sounds[i]:
				continue
			sounds[j] = 0	# don't check this again later

			num = (cl_main.cl.frame.parse_entities + j)&(client_h.MAX_PARSE_ENTITIES-1)
			ent = cl_main.cl_parse_entities[num]

			if not GetBSPEntitySoundOrigin(ent.number, listener_origin, org):
				shared.VectorCopy(ent.origin, org)

			left, right = S_SpatializeOrigin (org, 255.0, SOUND_LOOPATTENUATE)
			left_total += left
			right_total += right
		
		if left_total == 0 and right_total == 0:
			continue		# not audible

		# allocate a channel
		# Q2PORT: prefer the channel that played this loop last frame, so pygame keeps playing it
		ch = None
		for c in channels:
			if c.chan is not None and c.sfx is None and c.loop_sfx is sfx:
				ch = c
				break
		if ch is None:
			ch = S_PickChannel(0, 0)
		if ch is None:
			return

		if left_total > 255:
			left_total = 255
		if right_total > 255:
			right_total = 255
		ch.leftvol = left_total
		ch.rightvol = right_total
		ch.autosound = True	# remove next frame
		ch.sfx = sfx

		# Sometimes, the sc->length argument can become 0, and in that case
		# the modulo operation below would fail. The workaround checks for
		# this situation and sets the pos and end parameters to 0.
		if sc.length == 0:
			ch.pos = 0
			ch.end = 0
		else:
			ch.pos = paintedtime % sc.length
			ch.end = paintedtime + sc.length - ch.pos

		# Q2PORT: the C mixer would now paint the loop; start it on pygame if it is not already playing
		if ch.loop_sfx is not sfx:
			ch.chan.play(sc.data, loops=-1)
			ch.loop_sfx = sfx
		ch.chan.set_volume(ch.leftvol/255 * s_volume.value, ch.rightvol/255 * s_volume.value)
	

S_MAX_LEN_TO_TEST_FOR_SILENCE_S = 2
S_MIN_LEN_TO_TREAT_AS_SILENCE_MS = 3
S_MIN_ABS_AMP_8_TO_TREAT_AS_SILENCE = 1
S_MIN_ABS_AMP_16_TO_TREAT_AS_SILENCE = 2

"""
====================
S_IsShortSilence

Returns true if the sound is short enough to be treated as silence
====================
"""
def S_IsShortSilence (info, raw_data): #wavinfo_t *, byte * (returns qboolean)

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
		sample_count = info.samples * info.width
		samples = np.frombuffer(raw_data, dtype=np.uint8, count=min(sample_count, len(raw_data)))
		amp = np.abs(samples.astype(np.int32) - 0x80)
		return bool(np.all(amp <= S_MIN_ABS_AMP_8_TO_TREAT_AS_SILENCE))
	
	if info.width == 2:
	
		# Signed 16-bit audio data.
		# Q2PORT: like the C, raw_data is the start of the file (not data + dataofs)
		# and the count is samples * width; the read is limited to the buffer
		sample_count = info.samples * info.width
		samples = np.frombuffer(raw_data, dtype="<i2", count=min(sample_count, len(raw_data) // 2)) # LittleShort
		amp = np.abs(samples.astype(np.int32))
		return bool(np.all(amp <= S_MIN_ABS_AMP_16_TO_TREAT_AS_SILENCE))
	
	# Unsupported bit depth.
	return False

"""
====================
S_IsSilencedMuzzleFlash

Returns true if the sound is a silenced muzzle flash
====================
"""
def S_IsSilencedMuzzleFlash (info, raw_data, name): #wavinfo_t *, byte *, char * (returns qboolean)

	# Skip the prefix.
	base_sound_string_length = 6 #strlen("sound/")
	base_name = name[base_sound_string_length:]

	# Match to well-known muzzle flash sound names.
	is_name_matched = base_name in (
		"weapons/bfg__f1y.wav",
		"weapons/blastf1a.wav",
		"weapons/disint2.wav",
		"weapons/grenlf1a.wav",
		"weapons/grenlr1b.wav",
		"weapons/hyprbf1a.wav",
		"weapons/machgf1b.wav",
		"weapons/machgf2b.wav",
		"weapons/machgf3b.wav",
		"weapons/machgf4b.wav",
		"weapons/machgf5b.wav",
		"weapons/nail1.wav",
		"weapons/plasshot.wav",
		"weapons/railgf1a.wav",
		"weapons/rippfire.wav",
		"weapons/rocklf1a.wav",
		"weapons/rocklr1b.wav",
		"weapons/shotg2.wav",
		"weapons/shotgf1b.wav",
		"weapons/shotgr1b.wav",
		"weapons/sshotf1b.wav")

	if not is_name_matched:
		return False

	# Now check for silence.
	if not S_IsShortSilence(info, raw_data):
		return False

	return True

"""
====================
S_GetVolume

Returns the average volume of the sound
====================
"""
def S_GetVolume (data, sound_length, width): #byte *, int, int (returns double)

	if width == 2:
		sound_data = np.frombuffer(data, dtype=np.uint16)
		sound_data = np.frombuffer(sound_data.tobytes(), dtype=np.int16).astype(np.float64) # the C's LittleShort
		vol = float(np.sum(sound_data * sound_data))
	elif width == 1:
		sound_data = np.frombuffer(data, dtype=np.uint8).astype(np.int32)
		# normilize to 16bit sound;
		sound_data = (sound_data << 8).astype(np.int16).astype(np.float64) # the C's short sound_sample = *sound_data << 8
		vol = float(np.sum(sound_data * sound_data))
	else:
		vol = 0.0

	if sound_length != 0:
		vol /= sound_length
		vol = math.sqrt(vol)

	return vol

"""
====================
S_GetStatistics

Returns the begin, end, attack and fade lengths of the sound
====================
"""
def S_GetStatistics (data, sound_length, width, channels, sound_volume): #byte *, int, int, int, double (returns int *begin_length, int *end_length, int *attack_length, int *fade_length)

	# Q2PORT: the C's short arithmetic, wrapped to 16 bits
	def short(x): return ((int(x) + 32768) & 0xFFFF) - 32768

	if width == 2:
		sound_samples = np.frombuffer(data, dtype="<i2", count=min(sound_length, builtins.len(data) // 2)).tolist() # LittleShort
	elif width == 1:
		# normilize to 16bit sound;
		sound_samples = (np.frombuffer(data, dtype=np.uint8, count=min(sound_length, builtins.len(data))).astype(np.int32) << 8).astype(np.int16).tolist()
	else:
		return 0, 0, 0, 0
	sound_samples += [0] * (sound_length - builtins.len(sound_samples)) # Q2PORT: a truncated file reads as silence

	# attack length
	sound_max = 0 # short
	# calculate max value
	for sound_sample in sound_samples:
		if sound_max < abs(sound_sample):
			sound_max = short(abs(sound_sample))

	# use something in middle
	sound_max = short((sound_max + sound_volume) / 2)

	# calculate attack/fade length
	# Q2PORT: the C's pointers become indices. The do/while loops read one sample past
	# the ends of a (near) empty sound; the zero appended here stands in for those
	# reads (index sound_length, and -1)
	sound_samples.append(0)
	sound_data = 0
	delay_data = sound_data
	fade_data = sound_data
	sound_end = sound_data + sound_length
	sound_sample = 0
	sound_treshold = short(int(sound_max / 2))

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
====================
S_LoadVorbis

Load a vorbis file into a sfxcache_t
====================
"""
def S_LoadVorbis(path): #const char *, (returns wavinfo_t *info, void **buffer)

	"""
	const char ogg_ext[] = ".ogg";
	char filename[MAX_QPATH];
	const char* ext;
	int	len;
	"""

	# Q2PORT: the C fills info and buffer through pointers; the port returns
	# (info, buffer, the pygame Sound decoded from the file) or (None, None, None)

	if path is None:
		return None, None, None

	ext = shared_c.COM_FileExtension(path)
	if not ext:
		# file has no extension
		return None, None, None

	# Remove the extension
	len = (builtins.len(path) - builtins.len(ext)) - 1 # (ext - path) - 1
	if (len < 1) or (len > shared.MAX_QPATH - 5):
	
		clientserver.Com_DPrintf("{}: Bad filename {}\n".format("S_LoadVorbis", path))
		return None, None, None

	# copy base path
	# Add the extension
	filename = path[:len] + ".ogg" #const char ogg_ext[] = ".ogg"

	return ogg.OGG_LoadAsWav(filename)

"""
============
S_RawSamples

Cinematic streaming and voice over network
============
"""
def S_RawSamples (samples: int, rate: int, width: int, channels: int, data, volume): # byte *, float

	global sound_started, s_rawend, s_rawsamples, paintedtime

	"""
	float scale;
	int dst;
	int i;
	int src;
	int intVolume;
	"""

	if not sound_started:
		return

	if s_rawend < paintedtime:
		s_rawend = paintedtime

	# Q2PORT: the body of the C's SDL_RawSamples (sdl.c), the only backend ported
	scale = rate / dma.speed
	intVolume = int(256 * volume)

	if channels == 2 and width == 2:
	
		i = 0
		while True:
		
			src = int(i * scale)

			if src >= samples:
				break

			dst = s_rawend & (snd_loc.MAX_RAW_SAMPLES - 1)
			s_rawend += 1
			s_rawsamples[dst].left = shared_c.LittleSShort(data[src*4:src*4+2]) * intVolume # ((short *)data)[src * 2]
			s_rawsamples[dst].right = shared_c.LittleSShort(data[src*4+2:src*4+4]) * intVolume # ((short *)data)[src * 2 + 1]
			i += 1

	elif channels == 1 and width == 2:
	
		i = 0
		while True:
		
			src = int(i * scale)

			if src >= samples:
				break

			dst = s_rawend & (snd_loc.MAX_RAW_SAMPLES - 1)
			s_rawend += 1
			s_rawsamples[dst].left = shared_c.LittleSShort(data[src*2:src*2+2]) * intVolume # ((short *)data)[src]
			s_rawsamples[dst].right = shared_c.LittleSShort(data[src*2:src*2+2]) * intVolume
			i += 1

	elif channels == 2 and width == 1:
	
		intVolume *= 256

		i = 0
		while True:
		
			src = int(i * scale)

			if src >= samples:
				break

			dst = s_rawend & (snd_loc.MAX_RAW_SAMPLES - 1)
			s_rawend += 1
			s_rawsamples[dst].left = \
				(data[src * 2] - 128) * intVolume
			s_rawsamples[dst].right = \
				(data[src * 2 + 1] - 128) * intVolume
			i += 1

	elif channels == 1 and width == 1:
	
		intVolume *= 256

		i = 0
		while True:
		
			src = int(i * scale)

			if src >= samples:
				break

			dst = s_rawend & (snd_loc.MAX_RAW_SAMPLES - 1)
			s_rawend += 1
			s_rawsamples[dst].left = (data[src] - 128) * intVolume
			s_rawsamples[dst].right = (data[src] - 128) * intVolume
			i += 1

"""
//=============================================================================

/*
============
S_Update

Called once each time through the main loop
============
"""
def S_Update(origin, forward, right, up): #vec3_t, vec3_t, vec3_t, vec3_t

	"""
	int			i;
	int			total;
	channel_t	*ch;
	channel_t	*combine;
	"""

	global sound_started

	if not sound_started:
		return

	if s_active == False:
		return

	shared.VectorCopy(origin, listener_origin)
	shared.VectorCopy(forward, listener_forward)
	shared.VectorCopy(right, listener_right)
	shared.VectorCopy(up, listener_up)

	# Q2PORT: the C's USE_OPENAL / AL_Update branch is not ported; the rest is
	# the C's SDL_Update (sdl.c)

	# Q2PORT: the s_underwater / s_underwater_gain_hf low-pass filter (lpf_*) is
	# part of the C mixer, which is not ported (pygame mixes the channels)

	# if the loading plaque is up, clear everything
	# out to make sure we aren't looping a dirty
	# SDL buffer while loading
	if cl_main.cls.disable_screen:
	
		S_ClearBuffer ()
		return

	# rebuild scale tables if
	# volume is modified
	if s_volume.modified:
		snd_mix.S_InitScaletable ()

	# update spatialization
	# for dynamic sounds
	for i in range(s_numchannels):
	
		ch = channels[i]
		if ch.sfx is None:
			continue

		if ch.autosound:
		
			# autosounds are regenerated
			# fresh each frame
			ch.clear() # memset (ch, 0, sizeof(*ch)); loop_sfx is kept, see S_AddLoopSounds
			continue

		# respatialize channel
		S_Spatialize(ch)

		if not ch.leftvol and not ch.rightvol:
		
			ch.clear() # memset (ch, 0, sizeof(*ch));
			if ch.chan is not None:
				ch.chan.stop() # Q2PORT: the C mixer stops painting a cleared channel
			continue
		
		if ch.chan is not None:
			ch.chan.set_volume(ch.leftvol/255 * s_volume.value, ch.rightvol/255 * s_volume.value) # Q2PORT: the C mixer reads leftvol, rightvol and s_volume each paint
	
	# add loopsounds
	S_AddLoopSounds ()

	# Q2PORT: stop the pygame loops of autosound channels that were not regenerated
	for ch in channels:
		if ch.loop_sfx is not None and ch.sfx is None:
			ch.chan.stop()
			ch.loop_sfx = None

	# debugging output
	if s_show.value:
	
		total = 0

		for i in range(s_numchannels):
		
			ch = channels[i]
			if ch.sfx is not None and (ch.leftvol or ch.rightvol):
			
				clientserver.Com_Printf("{:3d} {:3d} {}\n".format(ch.leftvol,
						ch.rightvol, ch.sfx.name))
				total += 1

		clientserver.Com_Printf("----({})---- painted: {}\n".format(total, paintedtime))

	# stream music
	# Q2PORT: the music is streamed inside pygame.mixer.music (see client/sound/ogg.py)
	ogg.OGG_Stream()

	# Mix the samples
	S_Update_()


def GetSoundtime():

	global soundtime
	"""
	int		samplepos;
	static	int		buffers;
	static	int		oldsamplepos;
	int		fullsamples;
	"""
	
	"""
	fullsamples = dma.samples / dma.channels;

// it is possible to miscount buffers if it has wrapped twice between
// calls to S_Update.  Oh well.
	samplepos = SNDDMA_GetDMAPos();

	if (samplepos < oldsamplepos)
	{
		buffers++;					// buffer wrapped
		
		if (paintedtime > 0x40000000)
		{	// time to chop things off to avoid 32 bit limits
			buffers = 0;
			paintedtime = fullsamples;
			S_StopAllSounds ();
		}
	}
	oldsamplepos = samplepos;

	soundtime = buffers*fullsamples + samplepos/dma.channels;
	"""
	soundtime = system.Sys_Milliseconds() * dma.speed // 1000


def S_Update_():

	"""
	unsigned		endtime;
	int				samps;
	"""

	global sound_started, paintedtime, soundtime, s_pendingplays

	if not sound_started:
		return
	"""
	SNDDMA_BeginPainting ();

	if (!dma.buffer)
		return;
"""
	# Updates DMA time
	GetSoundtime()

	if not soundtime:
		return

	# check to make sure that we haven't overshot
	if paintedtime < soundtime:
	
		clientserver.Com_DPrintf("{}: overflow\n".format("SDL_Update"))
		paintedtime = soundtime

	# mix ahead of current position
	endtime = int(soundtime + s_mixahead.value * dma.speed)

	# mix to an even submission block size
	endtime = (endtime + dma.submission_chunk - 1) & ~(dma.submission_chunk - 1)
	samps = dma.samples >> (dma.channels - 1)

	# start any pending playsounds (Q2PORT: the C's SDL backend does this in its paint loop)
	while s_pendingplays:
	
		ps = s_pendingplays[0]
		if ps.begin <= paintedtime:
			s_pendingplays.pop(0)
			S_IssuePlaysound(ps)
			continue
		if ps.begin < endtime:
			endtime = ps.begin # stop here
		break
	if endtime - soundtime > samps:
		endtime = soundtime + samps
	
	snd_mix.S_PaintChannels (endtime)

	#SNDDMA_Submit ()

"""
===============================================================================

console functions

===============================================================================
"""

def S_Play():

	"""
	int 	i;
	char name[256];
	sfx_t	*sfx;
	"""
	i = 1
	while i<cmdparser.Cmd_Argc():
	
		if cmdparser.Cmd_Argv(i).find('.') == -1:
		
			name = "{}.wav".format(cmdparser.Cmd_Argv(i))
		
		else:
			name = cmdparser.Cmd_Argv(i)

		if ".." in name or name[0] == '/' or name[0] == '\\':
		
			clientserver.Com_Printf("Bad filename {}\n".format(name))
			return

		sfx = S_RegisterSound(name)
		S_StartSound(None, cl_main.cl.playernum+1, 0, sfx, 1.0, 1.0, 0.0)
		i+=1

def S_SoundList():
	
	"""
	int i;
	sfx_t *sfx;
	sfxcache_t *sc;
	int size, total, used;
	int numsounds;
	qboolean freeup;
	"""

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

		if sc is not None:
		
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

