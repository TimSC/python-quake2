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
import numpy as np
pass
pass
from backends.unix import system
from linux import snd_linux
from client import snd_mix, snd_loc, snd_mem, cl_main
pass
import pygame
from common.header import shared
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

num_sfx = None #int			
"""
#define		MAX_PLAYSOUNDS	128
playsound_t	s_playsounds[MAX_PLAYSOUNDS];
playsound_t	s_freeplays;
"""
s_pendingplays = [] #playsound_t (linked list)
s_beginofs = 0 #int

s_volume = None #cvar_t		*
s_testsound = None #cvar_t		*
s_loadas8bit = None #cvar_t		*
s_khz = None #cvar_t		*
s_show = None #cvar_t		*
s_mixahead = None #cvar_t		*
s_primary = None #cvar_t		*

s_rawend = 0 #int
s_rawsamples = [] #portable_samplepair_t	[MAX_RAW_SAMPLES];
for i in range(snd_loc.MAX_RAW_SAMPLES):
	s_rawsamples.append(snd_loc.portable_samplepair_t())


## ====================================================================
## User-setable variables
## ====================================================================


def S_SoundInfo_f():

	global sound_started
	pass
	"""
	if (!sound_started)
	{
		Com_Printf ("sound system not started\n");
		return;
	}
	
	Com_Printf("%5d stereo\n", dma.channels - 1);
	Com_Printf("%5d samples\n", dma.samples);
	Com_Printf("%5d samplepos\n", dma.samplepos);
	Com_Printf("%5d samplebits\n", dma.samplebits);
	Com_Printf("%5d submission_chunk\n", dma.submission_chunk);
	Com_Printf("%5d speed\n", dma.speed);
	Com_Printf("0x%x dma buffer\n", dma.buffer);

/*
================
S_Init
================
"""
def S_Init ():

	global s_volume, s_testsound, s_loadas8bit, s_khz, s_show, s_mixahead, s_primary
	global sound_started, num_sfx, soundtime, paintedtime, channels

	#cvar_t	*cv;

	clientserver.Com_Printf("\n------- sound initialization -------\n")

	cv = cvar.Cvar_Get ("s_initsound", "1", 0)
	if not cv.value:
		clientserver.Com_Printf ("not initializing.\n")
	else:
	
		s_volume = cvar.Cvar_Get ("s_volume", "0.7", shared.CVAR_ARCHIVE)
		s_khz = cvar.Cvar_Get ("s_khz", "11", shared.CVAR_ARCHIVE)
		s_loadas8bit = cvar.Cvar_Get ("s_loadas8bit", "1", shared.CVAR_ARCHIVE)
		s_mixahead = cvar.Cvar_Get ("s_mixahead", "0.2", shared.CVAR_ARCHIVE)
		s_show = cvar.Cvar_Get ("s_show", "0", 0)
		s_testsound = cvar.Cvar_Get ("s_testsound", "0", 0)
		s_primary = cvar.Cvar_Get ("s_primary", "0", shared.CVAR_ARCHIVE)	# win32 specific

		cmdparser.Cmd_AddCommand("play", S_Play)
		cmdparser.Cmd_AddCommand("stopsound", S_StopAllSounds)
		cmdparser.Cmd_AddCommand("soundlist", S_SoundList)
		cmdparser.Cmd_AddCommand("soundinfo", S_SoundInfo_f)
		
		if not snd_linux.SNDDMA_Init():
			return

		snd_mix.S_InitScaletable ()

		sound_started = 1
		num_sfx = 0

		soundtime = 0
		paintedtime = 0

		clientserver.Com_Printf ("sound sampling rate: {}\n".format(dma.speed))

		pygame.mixer.set_num_channels(snd_loc.MAX_CHANNELS)

		maxChan = min(snd_loc.MAX_CHANNELS, pygame.mixer.get_num_channels())
		for ch_idx in range(maxChan):
			channels[ch_idx].chan = pygame.mixer.Channel(ch_idx)
		
		S_StopAllSounds ()
	
	clientserver.Com_Printf("------------------------------------\n")


"""
// =======================================================================
// Shutdown sound engine
// =======================================================================
"""
def S_Shutdown():

	#int		i;
	#sfx_t	*sfx;
	global sound_started, known_sfx, num_sfx

	if not sound_started:
		return;

	snd_linux.SNDDMA_Shutdown()

	sound_started = 0

	cmdparser.Cmd_RemoveCommand("play")
	cmdparser.Cmd_RemoveCommand("stopsound")
	cmdparser.Cmd_RemoveCommand("soundlist")
	cmdparser.Cmd_RemoveCommand("soundinfo")

	# free all sounds
	total = 0
	for i in range(num_sfx):
	
		sfx=known_sfx[i]
		sfx.clear()

	num_sfx = 0

"""
// =======================================================================
// Load a sound
// =======================================================================

/*
==================
S_FindName

==================
"""
def S_FindName (name, create): #char *, qboolean (returns sfx_t *)

	global num_sfx, known_sfx
	#int		i;
	#sfx_t	*sfx;

	if name is None:
		clientserver.Com_Error (shared.ERR_FATAL, "S_FindName: NULL\n")
	if len(name) == 0:
		clientserver.Com_Error (shared.ERR_FATAL, "S_FindName: empty name\n")

	if len(name) >= shared.MAX_QPATH:
		clientserver.Com_Error (shared.ERR_FATAL, "Sound name too long: {}".format(name))

	# see if already loaded
	for i in range(num_sfx):
		if known_sfx[i].name == name:
			return known_sfx[i]
		
	if not create:
		return None

	# find a free sfx
	i = 0
	while i < num_sfx:
		if known_sfx[i].name is None:
			##registration_sequence < s_registration_sequence)
			break;
		i+=1

	if i == num_sfx:
	
		if num_sfx == MAX_SFX:
			clientserver.Com_Error (shared.ERR_FATAL, "S_FindName: out of sfx_t")
		num_sfx+=1
	
	sfx = known_sfx[i]
	sfx.name = name
	sfx.registration_sequence = s_registration_sequence
	sfx.cache = None
	sfx.truename = None
	
	return sfx;

"""

"""
"""
==================
S_AliasName

==================
"""
def S_AliasName (aliasname, truename): #char *, char * (returns sfx_t *)

	global num_sfx

	#sfx_t	*sfx;
	#char	*s;
	#int		i;

	s = truename # s = Z_Malloc (MAX_QPATH); strcpy (s, truename);

	# find a free sfx
	i = 0
	while i < num_sfx:
		if known_sfx[i].name is None: # !known_sfx[i].name[0]
			break
		i += 1

	if i == num_sfx:
	
		if num_sfx == MAX_SFX:
			clientserver.Com_Error (shared.ERR_FATAL, "S_FindName: out of sfx_t")
		num_sfx+=1
	
	sfx = known_sfx[i]
	sfx.clear() # memset (sfx, 0, sizeof(*sfx));
	sfx.name = aliasname
	sfx.registration_sequence = s_registration_sequence
	sfx.truename = s

	return sfx

"""


/*
=====================
S_BeginRegistration

=====================
"""
def S_BeginRegistration ():

	global s_registration_sequence, s_registering

	s_registration_sequence+=1
	s_registering = True

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

	sfx = S_FindName (name, True)
	sfx.registration_sequence = s_registration_sequence

	if not s_registering:
		snd_mem.S_LoadSound (sfx)

	return sfx


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

	# free any sounds not from this registration sequence
	for i in range(num_sfx):
	
		sfx = known_sfx[i]
		if sfx.name is None: # !sfx->name[0]
			continue
		if sfx.registration_sequence != s_registration_sequence:
			# don't need this sound
			sfx.clear() # Z_Free (sfx->cache); memset (sfx, 0, sizeof(*sfx));
		
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


//=============================================================================

/*
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

	if entchannel<0:
		clientserver.Com_Error (shared.ERR_DROP, "S_PickChannel: entchannel<0")

	# Check for replacement sound, or find the best one to replace
	first_to_die = -1
	life_left = None

	for ch_idx in range(snd_loc.MAX_CHANNELS):
	
		ch = channels[ch_idx]
		if ch.chan is None: continue
	
		if (entchannel != 0		# channel 0 never overrides
			and ch.entnum == entnum
			and ch.entchannel == entchannel):
		
			# always override sound from same entity
			first_to_die = ch_idx
			break
			
		# don't let monster sounds override player sounds
		if ch.entnum == cl_main.cl.playernum+1 and entnum != cl_main.cl.playernum+1 and ch.sfx:
			continue

		if life_left is None or ch.end - paintedtime < life_left:
		
			life_left = ch.end - paintedtime
			first_to_die = ch_idx
   
	if first_to_die == -1:
		return None

	ch = channels[first_to_die]
	ch.clear()
	ch.loop_sfx = None # Q2PORT: whatever the pygame channel plays next replaces the loop

	return ch

"""
=================
S_SpatializeOrigin

Used for spatializing channels and autosounds
=================
"""
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
	if ch.entnum == cl_main.cl.playernum+1:
	
		ch.leftvol = ch.master_vol
		ch.rightvol = ch.master_vol
		return
	

	if ch.fixed_origin:	
		shared.VectorCopy(ch.origin, origin)

	else:
		origin = cl_parse.CL_GetEntitySoundOrigin (ch.entnum)

	ch.leftvol, ch.rightvol = S_SpatializeOrigin (origin, ch.master_vol, ch.dist_mult)


"""
=================
S_AllocPlaysound
=================
*/
playsound_t *S_AllocPlaysound (void)
{
	playsound_t	*ps;

	ps = s_freeplays.next;
	if (ps == &s_freeplays)
		return NULL;		// no free playsounds

	// unlink from freelist
	ps->prev->next = ps->next;
	ps->next->prev = ps->prev;
	
	return ps;
}
"""
"""
/*
=================
S_FreePlaysound
=================
*/
void S_FreePlaysound (playsound_t *ps)
{
	// unlink from channel
	ps->prev->next = ps->next;
	ps->next->prev = ps->prev;

	// add to free list
	ps->next = s_freeplays.next;
	s_freeplays.next->prev = ps;
	ps->prev = &s_freeplays;
	s_freeplays.next = ps;
}
"""
"""
/*
===============
S_IssuePlaysound

Take the next playsound and begin it on the channel
This is never called directly by S_Play*, but only
by the update loop.
===============
"""
def S_IssuePlaysound (ps): #playsound_t *

	"""
	channel_t	*ch;
	sfxcache_t	*sc;
	"""

	if s_show.value:
		clientserver.Com_Printf ("Issue {}\n".format(ps.begin))
	# pick a channel to play on
	ch = S_PickChannel(ps.entnum, ps.entchannel)
	if ch is None:
	
		#S_FreePlaysound (ps)
		return;

	# spatialize
	if ps.attenuation == shared.ATTN_STATIC:
		ch.dist_mult = ps.attenuation * 0.001
	else:
		ch.dist_mult = ps.attenuation * 0.0005
	ch.master_vol = ps.volume
	ch.entnum = ps.entnum
	ch.entchannel = ps.entchannel
	ch.sfx = ps.sfx
	ps.origin = ch.origin
	ch.fixed_origin = ps.fixed_origin

	S_Spatialize(ch)
	
	ch.pos = 0;
	sc = snd_mem.S_LoadSound (ch.sfx)
	ch.end = paintedtime + sc.length

	# Q2PORT: the C mixer scales by ch->leftvol and s_volume (snd_vol, snd_scaletable) as it paints
	ch.chan.set_volume(ch.leftvol/255 * s_volume.value, ch.rightvol/255 * s_volume.value)
	ch.chan.play(sc.data)

"""
"""
def S_RegisterSexedSound (ent, base): #entity_state_t *, char * (returns struct sfx_s *)

	"""
	int				n;
	char			*p;
	struct sfx_s	*sfx;
	FILE			*f;
	char			model[MAX_QPATH];
	char			sexedFilename[MAX_QPATH];
	char			maleFilename[MAX_QPATH];
	"""

	# determine what model the client is using
	model = ""
	n = shared.CS_PLAYERSKINS + ent.number - 1
	if cl_main.cl.configstrings[n]:
	
		p = cl_main.cl.configstrings[n].find('\\')
		if p != -1:
		
			p += 1
			model = cl_main.cl.configstrings[n][p:]
			p = model.find('/')
			if p != -1:
				model = model[:p]
			
	# if we can't figure it out, they're male
	if not model:
		model = "male"

	# see if we already know of the model specific sound
	sexedFilename = "#players/{}/{}".format(model, base[1:])
	sfx = S_FindName (sexedFilename, False)

	if sfx is None:
	
		# no, so see if it exists
		length, f = filesystem.FS_FOpenFile (sexedFilename[1:])
		if f is not None:
		
			# yes, close the file and register it
			filesystem.FS_FCloseFile (f)
			sfx = S_RegisterSound (sexedFilename)
		
		else:
		
			# no, revert to the male sound in the pak0.pak
			maleFilename = "player/{}/{}".format("male", base[1:])
			sfx = S_AliasName (sexedFilename, maleFilename)
		
	return sfx

"""


// =======================================================================
// Start a sound effect
// =======================================================================

/*
====================
S_StartSound

Validates the parms and ques the sound up
if pos is NULL, the sound will be dynamically sourced from the entity
Entchannel 0 will never override a playing sound
====================
"""
def S_StartSound(origin, entnum, entchannel, sfx, fvol, attenuation, timeofs): #vec3_t, int, int, sfx_t *, float, float, float

	global s_beginofs, sound_started
	#common.Com_Printf("S_StartSound {}\n".format(sfx.name))

	"""
	sfxcache_t	*sc;
	int			vol;
	playsound_t	*ps, *sort;
	int			start;
	"""

	if not sound_started:
		return

	if sfx is None:
		return

	if sfx.name[0] == '*':
		ent = cl_main.CL_AllocEntity(entnum) # Q2PORT: until sound.c (group 13), which passes entnum
		sfx = S_RegisterSexedSound(ent.current if ent else shared.entity_state_t(), sfx.name)

	# make sure the sound is loaded
	sc = snd_mem.S_LoadSound (sfx)

	if sc is None:
		return		# couldn't load the sound's data

	vol = fvol*255

	# make the playsound_t
	ps = snd_loc.playsound_t ()
	if ps is None:
		return

	if origin is not None:
		ps.origin = origin
		ps.fixed_origin = True
	else:
		ps.origin = None
		ps.fixed_origin = False

	ps.entnum = entnum
	ps.entchannel = entchannel
	ps.attenuation = attenuation
	ps.volume = vol
	ps.sfx = sfx

	# drift s_beginofs
	start = int(cl_main.cl.frame.servertime * 0.001 * dma.speed + s_beginofs)
	if start < paintedtime:

		start = paintedtime
		s_beginofs = int(start - (cl_main.cl.frame.servertime * 0.001 * dma.speed))

	elif start > paintedtime + 0.3 * dma.speed:

		start = int(paintedtime + 0.1 * dma.speed)
		s_beginofs = int(start - (cl_main.cl.frame.servertime * 0.001 * dma.speed))

	else:

		s_beginofs-=10

	if timeofs == 0.0:
		ps.begin = paintedtime
	else:
		ps.begin = int(start + timeofs * dma.speed)

	# sort into the pending sound list
	s_pendingplays.append(ps)
	s_pendingplays.sort(key = lambda x: x.begin)

"""
==================
S_StartLocalSound
==================
"""

def S_StartLocalSound (sound): #char *

	#sfx_t	*sfx;

	if not sound_started:
		return
	
	sfx = S_RegisterSound (sound)
	if sfx is None:
	
		clientserver.Com_Printf ("S_StartLocalSound: can't cache {}\n".format(sound))
		return
	
	S_StartSound (None, cl_main.cl.playernum+1, 0, sfx, 1, 1, 0.0)

"""
==================
S_ClearBuffer
==================
"""
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
def S_StopAllSounds():
	
	#int		i;

	global sound_started, s_pendingplays

	if not sound_started:
		return;
	"""
	# clear all the playsounds
	memset(s_playsounds, 0, sizeof(s_playsounds));
	s_freeplays.next = s_freeplays.prev = &s_freeplays;
	s_pendingplays.next = s_pendingplays.prev = &s_pendingplays;
	"""
	s_pendingplays = []
	"""
	for (i=0 ; i<MAX_PLAYSOUNDS ; i++)
	{
		s_playsounds[i].prev = &s_freeplays;
		s_playsounds[i].next = s_freeplays.next;
		s_playsounds[i].prev->next = &s_playsounds[i];
		s_playsounds[i].next->prev = &s_playsounds[i];
	}
	"""

	# clear all the channels
	"""
	for ch_idx in range(snd_loc.MAX_CHANNELS):
	
		ch = channels[ch_idx]
		if ch.chan is None: continue
		ch.chan.stop()
	"""	

	#memset(channels, 0, sizeof(channels));

	S_ClearBuffer ()

"""
==================
S_AddLoopSounds

Entities with a ->sound field will generated looped sounds
that are automatically started, stopped, and merged together
as the entities are sent to the client
==================
*/
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
	"""
	sounds = [0] * shared.MAX_EDICTS

	if cl_main.cl_paused.value:
		return

	if cl_main.cls.state != client_h.connstate_t.ca_active:
		return

	if not cl_main.cl.sound_prepped:
		return

	for i in range(cl_main.cl.frame.num_entities):
	
		num = (cl_main.cl.frame.parse_entities + i)&(client_h.MAX_PARSE_ENTITIES-1)
		ent = cl_main.cl_parse_entities[num]
		sounds[i] = ent.sound
	
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

		# find the total contribution of all sounds of this type
		left_total, right_total = S_SpatializeOrigin (ent.origin, 255.0, SOUND_LOOPATTENUATE)
		for j in range(i+1, cl_main.cl.frame.num_entities):
		
			if sounds[j] != sounds[i]:
				continue
			sounds[j] = 0	# don't check this again later

			num = (cl_main.cl.frame.parse_entities + j)&(client_h.MAX_PARSE_ENTITIES-1)
			ent = cl_main.cl_parse_entities[num]

			left, right = S_SpatializeOrigin (ent.origin, 255.0, SOUND_LOOPATTENUATE)
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
		ch.pos = paintedtime % sc.length
		ch.end = paintedtime + sc.length - ch.pos

		# Q2PORT: the C mixer would now paint the loop; start it on pygame if it is not already playing
		if ch.loop_sfx is not sfx:
			ch.chan.play(sc.data, loops=-1)
			ch.loop_sfx = sfx
		ch.chan.set_volume(ch.leftvol/255 * s_volume.value, ch.rightvol/255 * s_volume.value)
	
"""

//=============================================================================

============
S_LoadVorbis
============

"""
def S_LoadVorbis(s, namebuffer): #sfx_t *, char * (returns sfxcache_t *)

	"""
	const char ogg_ext[] = ".ogg";
	char filename[MAX_QPATH];
	const char* ext;
	int	len;
	"""

	# Q2PORT: the C decodes the vorbis into a raw wav buffer via OGG_LoadAsWav and
	# S_LoadSound builds the cache from it; pygame.mixer.Sound decodes the ogg directly,
	# so the cache is built here.

	ext = namebuffer.rfind(".")
	if ext < 0:
		return None

	len = ext
	if (len < 1):
		clientserver.Com_DPrintf("S_LoadVorbis: Bad filename {}\n".format(namebuffer))
		return None

	filename = namebuffer[:len] + ".ogg" #const char ogg_ext[] = ".ogg"

	size, data = filesystem.FS_LoadFile(filename)
	if data is None:
		return None

	sc = snd_loc.sfxcache_t()
	sc.data = pygame.mixer.Sound(file=io.BytesIO(data))
	# Q2PORT: the C rejects stereo samples (info.channels != 1); pygame already converts
	# the file to the (stereo) mixer format, so the source channel count is not available

	# The OGG_LoadAsWav info
	sc.length = int(sc.data.get_length() * dma.speed) #in samples, like paintedtime
	sc.loopstart = -1
	sc.speed = dma.speed
	sc.width = 2
	sc.stereo = 1

	return sc


"""
============
S_RawSamples

Cinematic streaming and voice over network
============
"""
def S_RawSamples (samples: int, rate: int, width: int, channels: int, data): # byte *

	global sound_started, s_rawend, s_rawsamples, paintedtime

	"""
	int		i;
	int		src, dst;
	float	scale;
	"""

	if not sound_started:
		return

	if s_rawend < paintedtime:
		s_rawend = paintedtime
	scale = rate / dma.speed

#Com_Printf ("%i < %i < %i\n", soundtime, paintedtime, s_rawend);
	if channels == 2 and width == 2:
	
		if rate == dma.speed:
			# optimized case
			rangestart = None
			rangeend = None

			for i in range(samples):
			
				dst = s_rawend&(snd_loc.MAX_RAW_SAMPLES-1)
				s_rawend+=1
				s_rawsamples[dst].left = \
					shared_c.LittleSShort(data[i*4:i*4+2] )
				s_rawsamples[dst].right = \
					shared_c.LittleSShort(data[i*4+2:i*4+4] )

				#print ("a", dst, s_rawsamples[dst].left, s_rawsamples[dst].right)
				if rangestart is None:
					rangestart = dst
				rangeend = dst

		else:
			i = 0
			while True:
			
				src = int(i*scale)
				if src >= samples:
					break
				dst = s_rawend&(snd_loc.MAX_RAW_SAMPLES-1)
				s_rawend+=1

				s_rawsamples[dst].left = \
					shared_c.LittleSShort(data[src*2:src*2+2] )
				s_rawsamples[dst].right = \
					shared_c.LittleSShort(data[src*2+2:src*2+4] )
				i += 1
			
	elif channels == 1 and width == 2:
	
		pass
		"""
		for (i=0 ; ; i++)
		{
			src = i*scale;
			if (src >= samples)
				break;
			dst = s_rawend&(snd_loc.MAX_RAW_SAMPLES-1);
			s_rawend++;
			s_rawsamples[dst].left =
				LittleShort(((short *)data)[src]) << 8;
			s_rawsamples[dst].right =
				LittleShort(((short *)data)[src]) << 8;
		}
		"""
	
	elif channels == 2 and width == 1:
	
		pass
		"""
		for (i=0 ; ; i++)
		{
			src = i*scale;
			if (src >= samples)
				break;
			dst = s_rawend&(MAX_RAW_SAMPLES-1);
			s_rawend++;
			s_rawsamples[dst].left =
				((char *)data)[src*2] << 16;
			s_rawsamples[dst].right =
				((char *)data)[src*2+1] << 16;
		}
		"""
	
	elif channels == 1 and width == 1:
		
		pass
		"""
		for (i=0 ; ; i++)
		{
			src = i*scale;
			if (src >= samples)
				break;
			dst = s_rawend&(MAX_RAW_SAMPLES-1);
			s_rawend++;
			s_rawsamples[dst].left =
				(((byte *)data)[src]-128) << 16;
			s_rawsamples[dst].right = (((byte *)data)[src]-128) << 16;
		}
		"""

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


	# if the laoding plaque is up, clear everything
	# out to make sure we aren't looping a dirty
	# dma buffer while loading
	if cl_main.cls.disable_screen:
	
		S_ClearBuffer ()
		return
	
	"""
	// rebuild scale tables if volume is modified
	if (s_volume->modified)
		S_InitScaletable ();
	"""

	shared.VectorCopy(origin, listener_origin)
	shared.VectorCopy(forward, listener_forward)
	shared.VectorCopy(right, listener_right)
	shared.VectorCopy(up, listener_up)

	combine = None

	# update spatialization for dynamic sounds	
	for i in range(snd_loc.MAX_CHANNELS):
	
		ch = channels[i]
		if ch.sfx is None:
			continue
		if ch.autosound:
			# autosounds are regenerated fresh each frame
			ch.clear() # memset (ch, 0, sizeof(*ch)); loop_sfx is kept, see S_AddLoopSounds
			continue
		
		S_Spatialize(ch)		 # respatialize channel
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

	"""

	#
	# debugging output
	#
	if (s_show->value)
	{
		total = 0;
		ch = channels;
		for (i=0 ; i<MAX_CHANNELS; i++, ch++)
			if (ch->sfx && (ch->leftvol || ch->rightvol) )
			{
				Com_Printf ("%3i %3i %s\n", ch->leftvol, ch->rightvol, ch->sfx->name);
				total++;
			}
		
		Com_Printf ("----(%i)---- painted: %i\n", total, paintedtime);
	}
"""
	# mix some sound
	S_Update_();

	# Q2PORT: the C's SDL backend calls OGG_Stream() from its S_Update; the music is
	# streamed inside pygame.mixer.music (see client/sound/ogg.py)
	ogg.OGG_Stream()


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

	global sound_started, paintedtime, soundtime

	if not sound_started:
		return
	"""
	SNDDMA_BeginPainting ();

	if (!dma.buffer)
		return;
"""
	# Updates DMA time
	GetSoundtime()

	# check to make sure that we haven't overshot
	if paintedtime < soundtime:
	
	#	common.Com_DPrintf ("S_Update_ : overflow\n")
		paintedtime = soundtime
	
	
	# mix ahead of current position
	endtime = int(soundtime + s_mixahead.value * dma.speed)
	##endtime = (soundtime + 4096) & ~4095;

	# mix to an even submission block size
	#endtime = (endtime + dma.submission_chunk-1) \
	#	& ~(dma.submission_chunk-1)
	#samps = dma.samples >> (dma.channels-1)
	#if endtime - soundtime > samps:
	#	endtime = soundtime + samps
	
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
		sfx = S_RegisterSound(name)
		S_StartSound(None, cl_main.cl.playernum+1, 0, sfx, 1.0, 1.0, 0.0)
		i+=1

def S_SoundList():
	
	"""
	int		i;
	sfx_t	*sfx;
	sfxcache_t	*sc;
	int		size, total;
	"""
	global known_sfx, num_sfx

	total = 0
	for i in range(num_sfx):
	
		sfx=known_sfx[i]
		if not sfx.registration_sequence:
			continue
		sc = sfx.cache

		if sc is not None:
		
			size = len(sc.data.get_raw())
			total += size;
			if sc.loopstart >= 0:
				clientserver.Com_Printf ("L")
			else:
				clientserver.Com_Printf (" ")
			clientserver.Com_Printf("  {}\n", sfx.name)
		
		else:
		
			if sfx.name[0] == '*':
				clientserver.Com_Printf("  placeholder : {}\n".format(sfx.name))
			else:
				clientserver.Com_Printf("  not loaded  : {}\n".format(sfx.name))
		
	clientserver.Com_Printf ("Total resident: {}\n".format(total))


