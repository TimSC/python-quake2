"""
 * Copyright (C) 1997-2005 Id Software, Inc.
 *           (C) 2010 skuller.net
 *           (C) 2005 Stuart Dalton (badcdev@gmail.com)
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
 * This is the OpenAL backend for the Quake II Soundsystem. Most of these
 * functions were optained from the Q2Pro project, and some are from zeq2.
 * We adapted them to work with Yamagi Quake II. The OpenAL backend is
 * split into two layers. This is the upper layer, doing the actual work.
 * The lower layer implements the interface between Q2 and the OpenAL
 * implementation. This backend is overmuch complicated due to the
 * restrictions of the frontend.
 *
 * =======================================================================
"""
from __future__ import annotations

import ctypes

import numpy as np

from common import clientserver
from common import collision
from common.header import shared
from common.shared import shared as shared_c
from client import cl_main
from client import cl_entities
from client.header import client as client_h
from client.sound import qal
from client.sound import ogg
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
from client.sound.header import qal as qal_h

#ifdef USE_OPENAL

#include <stdint.h>

#include "../header/client.h"
#include "header/local.h"
#include "header/qal.h"
#include "header/vorbis.h"

# translates from AL coordinate system to quake
def AL_UnpackVector(v)->tuple: #define AL_UnpackVector(v) - v[1], v[2], -v[0]

	return float(-v[1]), float(v[2]), float(-v[0])

def AL_CopyVector(a, b, ofs: int = 0): #define AL_CopyVector(a, b) ((b)[0] = -(a)[1], (b)[1] = (a)[2], (b)[2] = -(a)[0])

	# Q2PORT: ofs is the C's "b + 3"
	b[ofs + 0], b[ofs + 1], b[ofs + 2] = -a[1], a[2], -a[0]

# avg US male height / q2PlayerHeight = 1.764f / 56.0f = 0.0315f
# see: https://en.wikipedia.org/wiki/List_of_average_human_height_worldwide
# see: PutClientInServer(edict_t *ent) bbox
AL_METER_OF_Q2_UNIT = 0.0315

# The OpenAL implementation should support
# at least this number of sources
MIN_CHANNELS = 16

QAL_EFX_MAX = 1
QAL_REVERB_EFFECT = 0

# Globals
active_buffers = 0 #int

# Locals
streamPlaying = False #static qboolean
streamQueued = 0 # Q2PORT: buffers AL_RawSamples() queued since the last AL_StreamUpdate()
s_srcnums = (qal.ALuint * (sound_local.MAX_CHANNELS - 1))() #static ALuint [MAX_CHANNELS - 1]
streamSource = qal.ALuint() #static ALuint
s_framecount = 0 #static int
underwaterFilter = qal.ALuint() #static ALuint
occlusionFilter = qal.ALuint() #static ALuint
ReverbEffect = (qal.ALuint * QAL_EFX_MAX)() #static ALuint [QAL_EFX_MAX]
ReverbEffectSlot = (qal.ALuint * QAL_EFX_MAX)() #static ALuint [QAL_EFX_MAX]
lastreverteffect = -1 #static int, just some invalid index value
snd_is_underwater_enabled = False #static qboolean

# -----------------------------------------------------------------

"""
 * Silence / stop all OpenAL streams
"""
def AL_StreamDie(): #void (static)

	global streamPlaying, active_buffers, streamQueued

	numBuffers = qal.ALint() #int

	# openal might not be initialised yet
	if not qal.qalSourceStop:

		return

	streamPlaying = False
	qal.qalSourceStop(streamSource)

	# Un-queue any buffers, and delete them
	qal.qalGetSourcei(streamSource, qal_h.AL_BUFFERS_QUEUED, ctypes.byref(numBuffers))

	while numBuffers.value:

		numBuffers.value -= 1 # while (numBuffers--)

		buffer = qal.ALuint() #ALuint
		qal.qalSourceUnqueueBuffers(streamSource, 1, ctypes.byref(buffer))
		qal.qalDeleteBuffers(1, ctypes.byref(buffer))
		active_buffers -= 1

	streamQueued = 0 # Q2PORT

"""
 * Updates stream sources by removing all played
 * buffers and restarting playback if necessary.
"""
def AL_StreamUpdate(): #void (static)

	global streamPlaying, active_buffers, streamQueued

	numBuffers = qal.ALint() #int
	state = qal.ALint() #ALint

	qal.qalGetSourcei(streamSource, qal_h.AL_SOURCE_STATE, ctypes.byref(state))

	if state.value == qal_h.AL_STOPPED:

		streamPlaying = False

		# Q2PORT: fix, a source that ran dry (a cinematic paused by the menu or
		# console) stops with its played buffers still queued, and the
		# qalSourcePlay() below restarted them, looping the last chunk of sound.
		# Un-queue them, but keep the ones AL_RawSamples() queued since the last
		# update: a stopped source counts every buffer as processed.
		qal.qalGetSourcei(streamSource, qal_h.AL_BUFFERS_QUEUED, ctypes.byref(numBuffers))
		numBuffers.value -= streamQueued

		while numBuffers.value > 0:

			numBuffers.value -= 1

			buffer = qal.ALuint() #ALuint
			qal.qalSourceUnqueueBuffers(streamSource, 1, ctypes.byref(buffer))
			qal.qalDeleteBuffers(1, ctypes.byref(buffer))
			active_buffers -= 1

	else:

		# Un-queue any already pleyed buffers and delete them
		qal.qalGetSourcei(streamSource, qal_h.AL_BUFFERS_PROCESSED, ctypes.byref(numBuffers))

		while numBuffers.value:

			numBuffers.value -= 1 # while (numBuffers--)

			buffer = qal.ALuint() #ALuint
			qal.qalSourceUnqueueBuffers(streamSource, 1, ctypes.byref(buffer))
			qal.qalDeleteBuffers(1, ctypes.byref(buffer))
			active_buffers -= 1

	# Start the streamSource playing if necessary
	qal.qalGetSourcei(streamSource, qal_h.AL_BUFFERS_QUEUED, ctypes.byref(numBuffers))

	if not streamPlaying and numBuffers.value:

		qal.qalSourcePlay(streamSource)
		streamPlaying = True

	streamQueued = 0 # Q2PORT

# -----------------------------------------------------------------

def AL_GetFormat(width: int, channels: int)->int: #int, int (returns static ALenum)

	if width == 1:

		if channels == 1:

			return qal_h.AL_FORMAT_MONO8

		elif channels == 2:

			return qal_h.AL_FORMAT_STEREO8

	elif width == 2:

		if channels == 1:

			return qal_h.AL_FORMAT_MONO16

		elif channels == 2:

			return qal_h.AL_FORMAT_STEREO16

	return qal_h.AL_FORMAT_MONO8

"""
 * Uploads a sample to OpenAL and places
 * a dummy entry in the frontends cache.
 * This is not nice but necessary for the
 * frontend to work.
"""
def AL_UploadSfx(s: sound_local.sfx_t, s_info: sound_local.wavinfo_t, data, volume: int,
		begin_length: int, end_length: int,
		attack_length: int, fade_length: int)->sound_local.sfxcache_t: #sfx_t *, wavinfo_t *, byte *, short, int, int, int, int (returns sfxcache_t *)

	global active_buffers

	#sfxcache_t *sc;
	#ALsizei size;
	#ALenum format;
	name = qal.ALuint() #ALuint

	size = s_info.samples * s_info.width

	# Work out format
	format = AL_GetFormat(s_info.width, s_info.channels)

	if not size:

		return None

	qal.qalGetError()
	qal.qalGenBuffers(1, ctypes.byref(name))
	qal.qalBufferData(name, format, bytes(data[:size]), size, s_info.rate)
	active_buffers += 1

	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		return None

	# allocate placeholder sfxcache
	sc = s.cache = sound_local.sfxcache_t() # Z_TagMalloc(sizeof(*sc), 0)
	sc.length = (s_info.samples * 1000) // s_info.rate # ((uint64_t)s_info->samples * 1000) / s_info->rate
	sc.loopstart = s_info.loopstart
	sc.width = s_info.width
	sc.size = size
	sc.bufnum = name.value
	sc.stereo = s_info.channels - 1
	sc.volume = int(volume) # short
	sc.begin = int(begin_length * 1000 / s_info.rate)
	sc.end = int(end_length * 1000 / s_info.rate)
	sc.fade = int(fade_length * 1000 / s_info.rate)
	sc.attack = int(attack_length * 1000 / s_info.rate)

	return sc

"""
 * Deletes a sample from OpenALs internal
 * cache. The dummy entry in the frontends
 * cache is deleted by the frontend.
"""
def AL_DeleteSfx(s: sound_local.sfx_t): #sfx_t *

	global active_buffers

	#sfxcache_t *sc;
	#ALuint name;

	sc = s.cache

	if not sc:

		return

	name = qal.ALuint(sc.bufnum)
	qal.qalDeleteBuffers(1, ctypes.byref(name))
	active_buffers -= 1

# -----------------------------------------------------------------

ReverbPresets = [ #static EFXEAXREVERBPROPERTIES []
	qal_h.EFX_REVERB_PRESET_GENERIC,
	qal_h.EFX_REVERB_PRESET_PADDEDCELL,
	qal_h.EFX_REVERB_PRESET_ROOM,
	qal_h.EFX_REVERB_PRESET_BATHROOM,
	qal_h.EFX_REVERB_PRESET_LIVINGROOM,
	qal_h.EFX_REVERB_PRESET_STONEROOM,
	qal_h.EFX_REVERB_PRESET_AUDITORIUM,
	qal_h.EFX_REVERB_PRESET_CONCERTHALL,
	qal_h.EFX_REVERB_PRESET_CAVE,
	qal_h.EFX_REVERB_PRESET_ARENA,
	qal_h.EFX_REVERB_PRESET_HANGAR,
	qal_h.EFX_REVERB_PRESET_CARPETEDHALLWAY,
	qal_h.EFX_REVERB_PRESET_HALLWAY,
	qal_h.EFX_REVERB_PRESET_STONECORRIDOR,
	qal_h.EFX_REVERB_PRESET_ALLEY,
	qal_h.EFX_REVERB_PRESET_FOREST,
	qal_h.EFX_REVERB_PRESET_CITY,
	qal_h.EFX_REVERB_PRESET_MOUNTAINS,
	qal_h.EFX_REVERB_PRESET_QUARRY,
	qal_h.EFX_REVERB_PRESET_PLAIN,
	qal_h.EFX_REVERB_PRESET_PARKINGLOT,
	qal_h.EFX_REVERB_PRESET_SEWERPIPE,
	qal_h.EFX_REVERB_PRESET_UNDERWATER,
	qal_h.EFX_REVERB_PRESET_DRUGGED,
	qal_h.EFX_REVERB_PRESET_DIZZY,
	qal_h.EFX_REVERB_PRESET_PSYCHOTIC,
	qal_h.EFX_REVERB_PRESET_CASTLE_SMALLROOM,
	qal_h.EFX_REVERB_PRESET_CASTLE_SHORTPASSAGE,
	qal_h.EFX_REVERB_PRESET_CASTLE_MEDIUMROOM,
	qal_h.EFX_REVERB_PRESET_CASTLE_LARGEROOM,
	qal_h.EFX_REVERB_PRESET_CASTLE_LONGPASSAGE,
	qal_h.EFX_REVERB_PRESET_CASTLE_HALL,
	qal_h.EFX_REVERB_PRESET_CASTLE_CUPBOARD,
	qal_h.EFX_REVERB_PRESET_CASTLE_COURTYARD,
	qal_h.EFX_REVERB_PRESET_CASTLE_ALCOVE,
	qal_h.EFX_REVERB_PRESET_FACTORY_SMALLROOM,
	qal_h.EFX_REVERB_PRESET_FACTORY_SHORTPASSAGE,
	qal_h.EFX_REVERB_PRESET_FACTORY_MEDIUMROOM,
	qal_h.EFX_REVERB_PRESET_FACTORY_LARGEROOM,
	qal_h.EFX_REVERB_PRESET_FACTORY_LONGPASSAGE,
	qal_h.EFX_REVERB_PRESET_FACTORY_HALL,
	qal_h.EFX_REVERB_PRESET_FACTORY_CUPBOARD,
	qal_h.EFX_REVERB_PRESET_FACTORY_COURTYARD,
	qal_h.EFX_REVERB_PRESET_FACTORY_ALCOVE,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_SMALLROOM,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_SHORTPASSAGE,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_MEDIUMROOM,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_LARGEROOM,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_LONGPASSAGE,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_HALL,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_CUPBOARD,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_COURTYARD,
	qal_h.EFX_REVERB_PRESET_ICEPALACE_ALCOVE,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_SMALLROOM,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_SHORTPASSAGE,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_MEDIUMROOM,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_LARGEROOM,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_LONGPASSAGE,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_HALL,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_CUPBOARD,
	qal_h.EFX_REVERB_PRESET_SPACESTATION_ALCOVE,
	qal_h.EFX_REVERB_PRESET_WOODEN_SMALLROOM,
	qal_h.EFX_REVERB_PRESET_WOODEN_SHORTPASSAGE,
	qal_h.EFX_REVERB_PRESET_WOODEN_MEDIUMROOM,
	qal_h.EFX_REVERB_PRESET_WOODEN_LARGEROOM,
	qal_h.EFX_REVERB_PRESET_WOODEN_LONGPASSAGE,
	qal_h.EFX_REVERB_PRESET_WOODEN_HALL,
	qal_h.EFX_REVERB_PRESET_WOODEN_CUPBOARD,
	qal_h.EFX_REVERB_PRESET_WOODEN_COURTYARD,
	qal_h.EFX_REVERB_PRESET_WOODEN_ALCOVE,
	qal_h.EFX_REVERB_PRESET_SPORT_EMPTYSTADIUM,
	qal_h.EFX_REVERB_PRESET_SPORT_SQUASHCOURT,
	qal_h.EFX_REVERB_PRESET_SPORT_SMALLSWIMMINGPOOL,
	qal_h.EFX_REVERB_PRESET_SPORT_LARGESWIMMINGPOOL,
	qal_h.EFX_REVERB_PRESET_SPORT_GYMNASIUM,
	qal_h.EFX_REVERB_PRESET_SPORT_FULLSTADIUM,
	qal_h.EFX_REVERB_PRESET_SPORT_STADIUMTANNOY,
	qal_h.EFX_REVERB_PRESET_PREFAB_WORKSHOP,
	qal_h.EFX_REVERB_PRESET_PREFAB_SCHOOLROOM,
	qal_h.EFX_REVERB_PRESET_PREFAB_PRACTISEROOM,
	qal_h.EFX_REVERB_PRESET_PREFAB_OUTHOUSE,
	qal_h.EFX_REVERB_PRESET_PREFAB_CARAVAN,
	qal_h.EFX_REVERB_PRESET_DOME_TOMB,
	qal_h.EFX_REVERB_PRESET_PIPE_SMALL,
	qal_h.EFX_REVERB_PRESET_DOME_SAINTPAULS,
	qal_h.EFX_REVERB_PRESET_PIPE_LONGTHIN,
	qal_h.EFX_REVERB_PRESET_PIPE_LARGE,
	qal_h.EFX_REVERB_PRESET_PIPE_RESONANT,
	qal_h.EFX_REVERB_PRESET_OUTDOORS_BACKYARD,
	qal_h.EFX_REVERB_PRESET_OUTDOORS_ROLLINGPLAINS,
	qal_h.EFX_REVERB_PRESET_OUTDOORS_DEEPCANYON,
	qal_h.EFX_REVERB_PRESET_OUTDOORS_CREEK,
	qal_h.EFX_REVERB_PRESET_OUTDOORS_VALLEY,
	qal_h.EFX_REVERB_PRESET_MOOD_HEAVEN,
	qal_h.EFX_REVERB_PRESET_MOOD_HELL,
	qal_h.EFX_REVERB_PRESET_MOOD_MEMORY,
	qal_h.EFX_REVERB_PRESET_DRIVING_COMMENTATOR,
	qal_h.EFX_REVERB_PRESET_DRIVING_PITGARAGE,
	qal_h.EFX_REVERB_PRESET_DRIVING_INCAR_RACER,
	qal_h.EFX_REVERB_PRESET_DRIVING_INCAR_SPORTS,
	qal_h.EFX_REVERB_PRESET_DRIVING_INCAR_LUXURY,
	qal_h.EFX_REVERB_PRESET_DRIVING_FULLGRANDSTAND,
	qal_h.EFX_REVERB_PRESET_DRIVING_EMPTYGRANDSTAND,
	qal_h.EFX_REVERB_PRESET_DRIVING_TUNNEL,
	qal_h.EFX_REVERB_PRESET_CITY_STREETS,
	qal_h.EFX_REVERB_PRESET_CITY_SUBWAY,
	qal_h.EFX_REVERB_PRESET_CITY_MUSEUM,
	qal_h.EFX_REVERB_PRESET_CITY_LIBRARY,
	qal_h.EFX_REVERB_PRESET_CITY_UNDERPASS,
	qal_h.EFX_REVERB_PRESET_CITY_ABANDONED,
	qal_h.EFX_REVERB_PRESET_DUSTYROOM,
	qal_h.EFX_REVERB_PRESET_CHAPEL,
	qal_h.EFX_REVERB_PRESET_SMALLWATERROOM,
]

EFX_REVERB_SIZE = len(ReverbPresets) # ARRLEN(ReverbPresets)

ReverbPresetsNames = [ #static char [][32]
	"Generic",
	"Padded Cell",
	"Room",
	"Bathroom",
	"LivingRoom",
	"StoneRoom",
	"Auditorium",
	"ConcertHall",
	"Cave",
	"Arena",
	"Hangar",
	"Carpeted Hallway",
	"Hallway",
	"Stone Corridor",
	"Alley",
	"Forest",
	"City",
	"Mountains",
	"Quarry",
	"Plain",
	"Parking Lot",
	"Sewer Pipe",
	"Underwater",
	"Drugged",
	"Dizzy",
	"Psychotic",
	"Castle Small Room",
	"Castle Short Passage",
	"Castle Medium Room",
	"Castle Large Room",
	"Castle Long Passage",
	"Castle Hall",
	"Castle Cupboard",
	"Castle Courtyard",
	"Castle Alcove",
	"Factory Small Room",
	"Factory Short Passage",
	"Factory Medium Room",
	"Factory Large Room",
	"Factory Long Passage",
	"Factory Hall",
	"Factory Cupboard",
	"Factory Courtyard",
	"Factory Alcove",
	"Icepalace Small Room",
	"Icepalace Short Passage",
	"Icepalace Medium Room",
	"Icepalace Large Room",
	"Icepalace Long Passage",
	"Icepalace Hall",
	"Icepalace Cupboard",
	"Icepalace Courtyard",
	"Icepalace Alcove",
	"Spacestation Small Room",
	"Spacestation Short Passage",
	"Spacestation Medium Room",
	"Spacestation Large Room",
	"Spacestation Long Passage",
	"Spacestation Hall",
	"Spacestation Cupboard",
	"Spacestation Alcove",
	"Wooden Small Room",
	"Wooden Short Passage",
	"Wooden Medium Room",
	"Wooden Large Room",
	"Wooden Long Passage",
	"Wooden Hall",
	"Wooden Cupboard",
	"Wooden CourtYard",
	"Wooden Alcove",
	"Sport Empty Stadium",
	"Sport Squash Court",
	"Sport Small Swimming Pool",
	"Sport Large Swimming Pool",
	"Sport Gymnasium",
	"Sport Full Stadium",
	"Sport Stadium Tannoy",
	"Prefab Workshop",
	"Prefab School Room",
	"Prefab Practise Room",
	"Prefab Outhouse",
	"Prefab Caravan",
	"Dome Tomb",
	"Pipe Small",
	"Dome Saintpauls",
	"Pipe Longthin",
	"Pipe Large",
	"Pipe Resonant",
	"Outdoors Backyard",
	"Outdoors Rolling Plains",
	"Outdoors Deep Canyon",
	"Outdoors Creek",
	"Outdoors Valley",
	"Mood Heaven",
	"Mood Hell",
	"Mood Memory",
	"Driving Commentator",
	"Driving Pit Garage",
	"Driving Incar Racer",
	"Driving Incar Sports",
	"Driving Incar Luxury",
	"Driving Full Grandstand",
	"Driving Empty Grandstand",
	"Driving Tunnel",
	"City Streets",
	"City Subway",
	"City Museum",
	"City Library",
	"City Underpass",
	"City Abandoned",
	"Dusty Room",
	"Chapel",
	"Smallwater Room",
]

"""
 * Update reverb setting without apply
"""
def AL_SetReverb(reverb_effect: int): #int (static)

	global lastreverteffect

	#EFXEAXREVERBPROPERTIES reverb;

	if (reverb_effect == lastreverteffect or
		reverb_effect < 0 or
		reverb_effect >= EFX_REVERB_SIZE):

		return

	reverb = ReverbPresets[reverb_effect]
	lastreverteffect = reverb_effect

	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_DENSITY, reverb.flDensity)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_DIFFUSION, reverb.flDiffusion)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_GAIN, reverb.flGain)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_GAINHF, reverb.flGainHF)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_DECAY_TIME, reverb.flDecayTime)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_DECAY_HFRATIO, reverb.flDecayHFRatio)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_REFLECTIONS_GAIN, reverb.flReflectionsGain)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_REFLECTIONS_DELAY, reverb.flReflectionsDelay)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_LATE_REVERB_GAIN, reverb.flLateReverbGain)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_LATE_REVERB_DELAY, reverb.flLateReverbDelay)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_AIR_ABSORPTION_GAINHF, reverb.flAirAbsorptionGainHF)
	qal.qalEffectf(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_ROOM_ROLLOFF_FACTOR, reverb.flRoomRolloffFactor)
	qal.qalEffecti(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_REVERB_DECAY_HFLIMIT, reverb.iDecayHFLimit)

	qal.qalAuxiliaryEffectSloti(ReverbEffectSlot[QAL_REVERB_EFFECT],
		qal_h.AL_EFFECTSLOT_EFFECT, ReverbEffect[QAL_REVERB_EFFECT])

"""
 * Apply Reverb effect
"""
def AL_ApplyReverb(): #void (static)

	mins = np.zeros((3,), dtype=np.float32) #vec3_t
	maxs = np.zeros((3,), dtype=np.float32) #vec3_t
	direction = np.array([ #vec3_t [6]
		[1000000, 0, 0], # forward
		[-1000000, 0, 0], # backward
		[0, 1000000, 0], # left
		[0, -1000000, 0], # right
		[ 0, 0, 1000000 ], # up
		[ 0, 0, -1000000 ], # down
	], dtype=np.float32)
	average = 0.0 #float
	#int i;

	if ReverbEffect[QAL_REVERB_EFFECT] == 0:
		return

	for i in range(6):

		#trace_t trace;
		length = np.zeros((3,), dtype=np.float32) #vec3_t

		trace = collision.CM_BoxTrace(sound_c.listener_origin, direction[i], mins, maxs, 0, shared.MASK_DEADSOLID)
		shared.VectorSubtract(trace.endpos, sound_c.listener_origin, length)
		average += shared_c.VectorLength(length)

	# Use five as down is near to us
	average /= 5

	if average < 100:

		AL_SetReverb(41)

	if average >= 100 and average < 200:

		AL_SetReverb(26)

	if average >= 200 and average < 330:

		AL_SetReverb(5)

	if average >= 330 and average < 450:

		AL_SetReverb(12)

	if average >= 450 and average < 650:

		AL_SetReverb(18)

	if average >= 650:

		AL_SetReverb(17)

"""
 * Performance stereo spatialization
 * of a channel in the frontends
 * sense.
"""
def AL_Spatialize(ch: sound_local.channel_t): #channel_t * (static)

	origin = np.zeros((3,), dtype=np.float32) #vec3_t
	velocity = np.zeros((3,), dtype=np.float32) #vec3_t

	if (ch.entnum == -1) or (ch.entnum == cl_main.cl.playernum + 1) or not ch.dist_mult:

		# from view entity (player) => nothing to do,
		# position is still (0,0,0) and relative,
		# as set in AL_PlayChannel()

		return

	elif ch.fixed_origin:

		shared.VectorCopy(ch.origin, origin)
		qal.qalSource3f(ch.srcnum, qal_h.AL_POSITION, *AL_UnpackVector(origin))
		return

	else:

		source_occluded = False #qboolean
		reverb_enabled = False #qboolean

		sound_c.GetEntitySoundOrigin(ch.entnum, sound_c.listener_origin, origin)
		qal.qalSource3f(ch.srcnum, qal_h.AL_POSITION, *AL_UnpackVector(origin))

		if sound_c.s_doppler.value:

			cl_entities.CL_GetEntitySoundVelocity(ch.entnum, velocity)
			shared_c.VectorScale(velocity, AL_METER_OF_Q2_UNIT, velocity)
			qal.qalSource3f(ch.srcnum, qal_h.AL_VELOCITY, *AL_UnpackVector(velocity))

		if (not sound_c.snd_is_underwater and
			sound_c.s_occlusion_strength.value and
			occlusionFilter.value != 0):

			#trace_t trace;
			mins = np.zeros((3,), dtype=np.float32) #vec3_t
			maxs = np.zeros((3,), dtype=np.float32) #vec3_t

			trace = collision.CM_BoxTrace(origin, sound_c.listener_origin, mins, maxs, 0, shared.MASK_PLAYERSOLID)
			if (trace.fraction < 1.0 and
				not (ch.entnum == -1 or ch.entnum == cl_main.cl.playernum + 1 or not ch.dist_mult)
			):

				distance = np.zeros((3,), dtype=np.float32) #vec3_t
				#float dist;
				#float final;
				#float gain_hf;

				shared.VectorSubtract(origin, sound_c.listener_origin, distance)
				dist = shared_c.VectorLength(distance)

				final = 1.0 - ((dist / 1000) * (1.0 - sound_c.s_occlusion_strength.value))

				qal.qalSourcef(ch.srcnum, qal_h.AL_GAIN, shared.Q_min(shared.Q_max(final, 0), 1))

				# Scale high-frequency attenuation with distance.
				# Preserve enough HF content for HRTF spatial cues
				gain_hf = 1.0 - (0.5 * sound_c.s_occlusion_strength.value *
					shared.Q_min(dist / 1000.0, 1.0))
				gain_hf = shared.Q_min(shared.Q_max(gain_hf, qal_h.AL_LOWPASS_MIN_GAINHF),
					qal_h.AL_LOWPASS_MAX_GAINHF)
				qal.qalFilterf(occlusionFilter, qal_h.AL_LOWPASS_GAINHF, gain_hf)

				qal.qalSourcei(ch.srcnum, qal_h.AL_DIRECT_FILTER, occlusionFilter.value)

				source_occluded = True

		if not source_occluded:

			# Remove filter
			if not sound_c.snd_is_underwater:
				qal.qalSourcei(ch.srcnum, qal_h.AL_DIRECT_FILTER, 0)

			if sound_c.s_reverb_preset.value != -1: # Non Disabled reverb

				# Apply reverb effect
				qal.qalSource3i(ch.srcnum, qal_h.AL_AUXILIARY_SEND_FILTER,
					ReverbEffectSlot[QAL_REVERB_EFFECT], 0, qal_h.AL_FILTER_NULL)
				reverb_enabled = True

		if not reverb_enabled:

			# Disable filtering
			qal.qalSource3i(ch.srcnum, qal_h.AL_AUXILIARY_SEND_FILTER,
				0, 0, qal_h.AL_FILTER_NULL)

		return

"""
 * Plays a channel (in the frontends
 * sense) with OpenAL.
"""
def AL_PlayChannel(ch: sound_local.channel_t): #channel_t *

	#sfxcache_t *sc;
	#float vol;

	# Debug
	if sound_c.s_show.value > 1:

		clientserver.Com_Printf("{}: {}\n".format("AL_PlayChannel", ch.sfx.name))

	# Clamp volume
	vol = ch.oal_vol

	if vol > 1.0:

		vol = 1.0

	sc = ch.sfx.cache
	ch.srcnum = s_srcnums[sound_c.channels.index(ch)] # s_srcnums[ch - channels]

	qal.qalGetError()
	qal.qalSourcef(ch.srcnum, qal_h.AL_REFERENCE_DISTANCE, sound_local.SOUND_FULLVOLUME)
	qal.qalSourcef(ch.srcnum, qal_h.AL_MAX_DISTANCE, 8192)
	qal.qalSourcef(ch.srcnum, qal_h.AL_ROLLOFF_FACTOR, ch.dist_mult * (8192 - sound_local.SOUND_FULLVOLUME))
	qal.qalSourcef(ch.srcnum, qal_h.AL_GAIN, vol)
	qal.qalSourcei(ch.srcnum, qal_h.AL_BUFFER, sc.bufnum)
	qal.qalSourcei(ch.srcnum, qal_h.AL_LOOPING, qal_h.AL_TRUE if ch.autosound else qal_h.AL_FALSE)

	if (ch.entnum == -1) or (ch.entnum == cl_main.cl.playernum + 1) or not ch.dist_mult:

		# anything coming from the view entity will always
		# be full volume and at the listeners position
		qal.qalSource3f(ch.srcnum, qal_h.AL_POSITION, 0.0, 0.0, 0.0)
		qal.qalSourcei(ch.srcnum, qal_h.AL_SOURCE_RELATIVE, qal_h.AL_TRUE)

	else:

		# all other sources are *not* relative
		qal.qalSourcei(ch.srcnum, qal_h.AL_SOURCE_RELATIVE, qal_h.AL_FALSE)

	# Spatialize it
	AL_Spatialize(ch)

	# Play it
	qal.qalSourcePlay(ch.srcnum)

	# Do not play broken channels
	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		AL_StopChannel(ch)

"""
 * Stops playback of a "channel"
 * in the frontends sense.
"""
def AL_StopChannel(ch: sound_local.channel_t): #channel_t *

	# Debug output
	if sound_c.s_show.value > 1:

		clientserver.Com_Printf("{}: {}\n".format("AL_StopChannel", ch.sfx.name))

	# stop it
	qal.qalSourceStop(ch.srcnum)
	qal.qalSourcei(ch.srcnum, qal_h.AL_BUFFER, qal_h.AL_NONE)
	ch.clear() # memset(ch, 0, sizeof(*ch));

"""
 * Stops playback of all channels.
"""
def AL_StopAllChannels(): #void

	#int i;
	#channel_t *ch;

	# It doesn't matter if a channel
	# is active or not.
	for i in range(sound_c.s_numchannels):

		ch = sound_c.channels[i]
		if not ch.sfx:

			continue

		AL_StopChannel(ch)

	sound_c.s_rawend = 0

	# Remove all pending samples
	AL_StreamDie()

# -----------------------------------------------------------------

"""
 * Returns the channel which contains
 * the looping sound for the entity
 * "entnum".
"""
def AL_FindLoopingSound(entnum: int, sfx: sound_local.sfx_t)->sound_local.channel_t: #int, sfx_t * (returns static channel_t *)

	#int i;
	#channel_t *ch;

	for i in range(sound_c.s_numchannels):

		ch = sound_c.channels[i]
		if not ch.sfx:

			continue

		if not ch.autosound:

			continue

		if ch.entnum != entnum:

			continue

		if ch.sfx is not sfx:

			continue

		return ch

	return None

"""
 * Plays an looping sound with OpenAL
"""
def AL_AddLoopSounds(): #void (static)

	#int i;
	#int sounds[MAX_EDICTS];

	if ((cl_main.cls.state != client_h.connstate_t.ca_active) or (cl_main.cl_paused.value and cl_main.cl_audiopaused.value) or
		not sound_c.s_ambient.value):

		return

	sounds = [0] * shared.MAX_EDICTS # memset(&sounds, 0, sizeof(int) * MAX_EDICTS);
	sound_c.S_BuildSoundList(sounds)

	for i in range(cl_main.cl.frame.num_entities):

		#channel_t *ch;
		#sfx_t *sfx;
		#sfxcache_t *sc;
		#int num;
		#entity_state_t *ent;

		if not sounds[i]:

			continue

		sfx = cl_main.cl.sound_precache[sounds[i]]

		if not sfx:

			continue # bad sound effect

		sc = sfx.cache

		if not sc:

			continue

		num = (cl_main.cl.frame.parse_entities + i) & (client_h.MAX_PARSE_ENTITIES - 1)
		ent = cl_main.cl_parse_entities[num]

		ch = AL_FindLoopingSound(ent.number, sfx)

		if ch:

			ch.autoframe = s_framecount
			ch.end = sound_c.paintedtime + sc.length
			continue

		# allocate a channel
		ch = sound_c.S_PickChannel(0, 0)

		if not ch:

			continue

		ch.autosound = True # remove next frame
		ch.autoframe = s_framecount
		ch.sfx = sfx
		ch.entnum = ent.number
		ch.master_vol = 1
		ch.dist_mult = sound_local.SOUND_LOOPATTENUATE
		ch.end = sound_c.paintedtime + sc.length

		# it seems like looped sounds are always played at full volume
		# see SDL_AddLoopSounds() which calls SDL_SpatializeOrigin() with volume 255.0f
		# so set it to full volume (1.0 * s_volume).
		ch.oal_vol = sound_c.s_volume.value

		AL_PlayChannel(ch)

"""
 * Starts all pending playsounds.
"""
def AL_IssuePlaysounds(): #void (static)

	#playsound_t *ps;

	# start any playsounds
	while True:

		if not sound_c.s_pendingplays: # ps == &s_pendingplays

			break # no more pending sounds

		ps = sound_c.s_pendingplays[0] # s_pendingplays.next

		if ps.begin > sound_c.paintedtime:

			break

		sound_c.S_IssuePlaysound(ps)

"""
 * Queues raw samples for playback. Used
 * by the background music an cinematics.
"""
def AL_RawSamples(samples: int, rate: int, width: int, channels: int,
		data, volume: float): #int, int, int, int, const byte *, float

	global active_buffers, streamQueued

	buffer = qal.ALuint() #ALuint
	format = 0 #ALuint

	# Work out format
	format = AL_GetFormat(width, channels)

	# Create a buffer, and stuff the data into it
	qal.qalGenBuffers(1, ctypes.byref(buffer))
	qal.qalBufferData(buffer, format, bytes(data),
			(samples * width * channels), rate)
	active_buffers += 1

	# set volume
	if volume > 1.0:

		volume = 1.0

	qal.qalSourcef(streamSource, qal_h.AL_GAIN, volume)

	# Shove the data onto the streamSource
	qal.qalSourceQueueBuffers(streamSource, 1, ctypes.byref(buffer))
	streamQueued += 1 # Q2PORT

	# emulate behavior of S_RawSamples for s_rawend
	sound_c.s_rawend += samples

"""
 * Kills all raw samples still in flight.
 * This is used to stop music playback
 * when silence is triggered.
"""
def AL_UnqueueRawSamples(): #void

	AL_StreamDie()

def AL_UpdateReverb(): #void (static)

	#int reverb_effect;

	if not sound_c.s_reverb_preset.modified:

		return

	sound_c.s_reverb_preset.modified = False

	reverb_effect = int(sound_c.s_reverb_preset.value)

	if reverb_effect == -2:

		clientserver.Com_Printf("Reverb set to: AUTO\n")
		return

	elif reverb_effect == -1:

		clientserver.Com_Printf("Reverb set to: Disabled\n")
		return

	# We have only EFX_REVERB_SIZE(113) effects
	elif reverb_effect >= 0 and reverb_effect < EFX_REVERB_SIZE:

		clientserver.Com_Printf("Reverb set to: {}\n".format(ReverbPresetsNames[reverb_effect]))

		AL_SetReverb(reverb_effect)

	else:

		#int i;
		clientserver.Com_Printf("Uknown reverb effect, supported:\n-2: Auto\n-1: Disabled\n")
		for i in range(EFX_REVERB_SIZE):

			clientserver.Com_Printf("{}: {}\n".format(i, ReverbPresetsNames[i]))

def AL_UpdateUnderwater(): #void (static)

	global snd_is_underwater_enabled

	#int i;
	#float gain_hf;
	update = False #qboolean
	#ALuint filter;

	if underwaterFilter.value == 0:
		return

	if sound_c.s_underwater.modified:
		update = True
		sound_c.s_underwater.modified = False
		snd_is_underwater_enabled = (int(sound_c.s_underwater.value) != 0)

	if sound_c.s_underwater_gain_hf.modified:
		update = True
		sound_c.s_underwater_gain_hf.modified = False

	if not update:
		return

	gain_hf = sound_c.s_underwater_gain_hf.value

	if gain_hf < qal_h.AL_LOWPASS_MIN_GAINHF:
		gain_hf = qal_h.AL_LOWPASS_MIN_GAINHF

	if gain_hf > qal_h.AL_LOWPASS_MAX_GAINHF:
		gain_hf = qal_h.AL_LOWPASS_MAX_GAINHF

	qal.qalFilterf(underwaterFilter, qal_h.AL_LOWPASS_GAINHF, gain_hf)

	if snd_is_underwater_enabled and sound_c.snd_is_underwater:
		filter = underwaterFilter.value
	else:
		filter = 0

	for i in range(sound_c.s_numchannels):
		qal.qalSourcei(s_srcnums[i], qal_h.AL_DIRECT_FILTER, filter)

"""
 * Main update function. Called every frame,
 * performes all necessary calculations.
"""
def AL_Update(): #void

	global s_framecount

	#int i;
	#channel_t *ch;
	orientation = (qal.ALfloat * 6)() #vec_t [6]
	listener_velocity = np.zeros((3,), dtype=np.float32) #vec3_t

	sound_c.paintedtime = cl_main.cls.realtime

	# Do nothing if we aren't connected to a output device.
	# This is called after increasing paintedtime, because
	# the sound for the current frame needs to be skipped.
	# Otherwise sound and game will become asynchronous and
	# the paint buffer may overflow.
	if not qal.QAL_RecoverLostDevice():
		return

	# set listener (player) parameters
	AL_CopyVector(sound_c.listener_forward, orientation)
	AL_CopyVector(sound_c.listener_up, orientation, 3) # orientation + 3
	qal.qalListener3f(qal_h.AL_POSITION, *AL_UnpackVector(sound_c.listener_origin))
	qal.qalListenerfv(qal_h.AL_ORIENTATION, orientation)

	if sound_c.s_reverb_preset.value == -2:

		AL_ApplyReverb()

	elif sound_c.s_reverb_preset.value >= 0:

		AL_SetReverb(int(sound_c.s_reverb_preset.value))

	if sound_c.s_doppler.value:
		cl_entities.CL_GetViewVelocity(listener_velocity)
		shared_c.VectorScale(listener_velocity, AL_METER_OF_Q2_UNIT, listener_velocity)
		qal.qalListener3f(qal_h.AL_VELOCITY, *AL_UnpackVector(listener_velocity))

	# update spatialization for dynamic sounds
	for i in range(sound_c.s_numchannels):

		ch = sound_c.channels[i]
		if not ch.sfx:

			continue

		if ch.autosound:

			# autosounds are regenerated fresh each frame
			if ch.autoframe != s_framecount:

				AL_StopChannel(ch)
				continue

		else:

			state = qal.ALint() #ALenum

			qal.qalGetError()
			qal.qalGetSourcei(ch.srcnum, qal_h.AL_SOURCE_STATE, ctypes.byref(state))

			if (qal.qalGetError() != qal_h.AL_NO_ERROR) or (state.value == qal_h.AL_STOPPED):

				AL_StopChannel(ch)
				continue

		if sound_c.s_show.value:

			clientserver.Com_Printf("{:3} {}\n".format(ch.master_vol, ch.sfx.name))

		# respatialize channel
		AL_Spatialize(ch)

	s_framecount += 1

	# add loopsounds
	AL_AddLoopSounds()

	# add music
	ogg.OGG_Stream()

	AL_StreamUpdate()
	AL_IssuePlaysounds()

	AL_UpdateUnderwater()
	AL_UpdateReverb()

# -----------------------------------------------------------------

"""
 * Enables underwater effect
"""
def AL_Underwater(): #void

	#int i;

	if sound_c.sound_started != sound_local.SS_OAL or not snd_is_underwater_enabled:

		return

	if underwaterFilter.value == 0:
		return

	# Apply to all sources
	for i in range(sound_c.s_numchannels):

		qal.qalSourcei(s_srcnums[i], qal_h.AL_DIRECT_FILTER, underwaterFilter.value)

	AL_SetReverb(22)

"""
 * Disables the underwater effect
"""
def AL_Overwater(): #void

	#int i;

	if sound_c.sound_started != sound_local.SS_OAL or not snd_is_underwater_enabled:

		return

	if underwaterFilter.value == 0:

		return

	# Apply to all sources
	for i in range(sound_c.s_numchannels):

		qal.qalSourcei(s_srcnums[i], qal_h.AL_DIRECT_FILTER, qal_h.AL_FILTER_NULL)

	AL_SetReverb(int(sound_c.s_reverb_preset.value))

# -----------------------------------------------------------------

"""
 * Set up the stream sources
"""
def AL_InitStreamSource(): #void (static)

	qal.qalSource3f(streamSource, qal_h.AL_POSITION, 0.0, 0.0, 0.0)
	qal.qalSource3f(streamSource, qal_h.AL_VELOCITY, 0.0, 0.0, 0.0)
	qal.qalSource3f(streamSource, qal_h.AL_DIRECTION, 0.0, 0.0, 0.0)
	qal.qalSourcef(streamSource, qal_h.AL_ROLLOFF_FACTOR, 0.0)
	qal.qalSourcei(streamSource, qal_h.AL_BUFFER, 0)
	qal.qalSourcei(streamSource, qal_h.AL_LOOPING, qal_h.AL_FALSE)
	qal.qalSourcei(streamSource, qal_h.AL_SOURCE_RELATIVE, qal_h.AL_TRUE)

def AL_Efx_Enabled()->bool: #void (returns static qboolean)

	if (qal.qalAuxiliaryEffectSloti and
		qal.qalDeleteAuxiliaryEffectSlots and
		qal.qalDeleteEffects and
		qal.qalDeleteFilters and
		qal.qalEffectf and
		qal.qalEffecti and
		qal.qalFilterf and
		qal.qalFilteri and
		qal.qalGenAuxiliaryEffectSlots and
		qal.qalGenEffects and
		qal.qalGenFilters):
		return True
	return False

"""
 * Set up the underwater filter
"""
def AL_InitUnderwaterFilter(): #void (static)

	underwaterFilter.value = 0

	if not AL_Efx_Enabled():
		return

	# Generate a filter
	qal.qalGenFilters(1, ctypes.byref(underwaterFilter))

	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("Couldn't generate an OpenAL filter!\n")
		return

	# Low pass filter for underwater effect
	qal.qalFilteri(underwaterFilter, qal_h.AL_FILTER_TYPE, qal_h.AL_FILTER_LOWPASS)

	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("Low pass filter is not supported!\n")
		return

	qal.qalFilterf(underwaterFilter, qal_h.AL_LOWPASS_GAIN, qal_h.AL_LOWPASS_DEFAULT_GAIN)

	sound_c.s_underwater.modified = True
	sound_c.s_underwater_gain_hf.modified = True

"""
 * Set up the occlusion filter (separate from underwater)
"""
def AL_InitOcclusionFilter(): #void (static)

	occlusionFilter.value = 0

	if not AL_Efx_Enabled():
		return

	qal.qalGenFilters(1, ctypes.byref(occlusionFilter))

	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("Couldn't generate occlusion filter!\n")
		return

	qal.qalFilteri(occlusionFilter, qal_h.AL_FILTER_TYPE, qal_h.AL_FILTER_LOWPASS)

	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("Low pass filter is not supported!\n")
		occlusionFilter.value = 0
		return

	qal.qalFilterf(occlusionFilter, qal_h.AL_LOWPASS_GAIN, qal_h.AL_LOWPASS_DEFAULT_GAIN)
	qal.qalFilterf(occlusionFilter, qal_h.AL_LOWPASS_GAINHF, qal_h.AL_LOWPASS_DEFAULT_GAINHF)

def AL_InitReverbEffect(): #void (static)

	if not AL_Efx_Enabled():
		return

	qal.qalGenEffects(QAL_EFX_MAX, ReverbEffect)
	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("Couldn't generate an OpenAL effect!\n")
		return

	qal.qalGenAuxiliaryEffectSlots(QAL_EFX_MAX, ReverbEffectSlot)
	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("Couldn't generate an OpenAL auxiliary effect slot!\n")
		return

	qal.qalEffecti(ReverbEffect[QAL_REVERB_EFFECT], qal_h.AL_EFFECT_TYPE, qal_h.AL_EFFECT_REVERB)
	AL_SetReverb(int(sound_c.s_reverb_preset.value))

"""
 * Initializes the OpenAL backend
"""
def AL_Init()->bool: #void (returns qboolean)

	#int i;

	if not qal.QAL_Init():

		clientserver.Com_Printf("ERROR: OpenAL failed to initialize.\n")
		return False

	# check for linear distance extension
	if not qal.qalIsExtensionPresent(b"AL_EXT_LINEAR_DISTANCE"):

		clientserver.Com_Printf("ERROR: Required AL_EXT_LINEAR_DISTANCE extension is missing.\n")
		qal.QAL_Shutdown()
		return False

	# generate source names
	qal.qalGetError()
	qal.qalGenSources(1, ctypes.byref(streamSource))

	if qal.qalGetError() != qal_h.AL_NO_ERROR:

		clientserver.Com_Printf("ERROR: Couldn't get a single Source.\n")
		qal.QAL_Shutdown()
		return False

	else:

		# -1 because we already got one channel for streaming
		i = 0
		while i < sound_local.MAX_CHANNELS - 1:

			source = qal.ALuint()
			qal.qalGenSources(1, ctypes.byref(source)) # &s_srcnums[i]
			s_srcnums[i] = source.value

			if qal.qalGetError() != qal_h.AL_NO_ERROR:

				break

			i += 1

		if i < MIN_CHANNELS - 1:

			clientserver.Com_Printf("ERROR: Required at least {} sources, but got {}.\n".format(
					MIN_CHANNELS, i + 1))
			qal.QAL_Shutdown()
			return False

	sound_c.s_numchannels = i
	AL_InitStreamSource()
	AL_InitUnderwaterFilter()
	AL_InitOcclusionFilter()
	AL_InitReverbEffect()

	clientserver.Com_Printf("Number of OpenAL sources: {}\n\n".format(sound_c.s_numchannels))

	# exaggerate 2x because realistic is barely noticeable
	if sound_c.s_doppler.value:
		qal.qalDopplerFactor(2.0)

	qal.qalDistanceModel(qal_h.AL_LINEAR_DISTANCE_CLAMPED)

	return True

"""
 * Shuts the OpenAL backend down
"""
def AL_Shutdown(): #void

	clientserver.Com_Printf("Shutting down OpenAL.\n")

	AL_StopAllChannels()

	qal.qalDeleteSources(1, ctypes.byref(streamSource))
	if qal.qalDeleteFilters: # Q2PORT: NULL without ALC_EXT_EFX, the C would crash
		qal.qalDeleteFilters(1, ctypes.byref(underwaterFilter))
		qal.qalDeleteFilters(1, ctypes.byref(occlusionFilter))
		qal.qalDeleteAuxiliaryEffectSlots(QAL_EFX_MAX, ReverbEffectSlot)
		qal.qalDeleteEffects(QAL_EFX_MAX, ReverbEffect)

	if sound_c.s_numchannels:

		# delete source names
		qal.qalDeleteSources(sound_c.s_numchannels, s_srcnums)
		ctypes.memset(s_srcnums, 0, ctypes.sizeof(s_srcnums))
		sound_c.s_numchannels = 0

	qal.QAL_Shutdown()

#endif /* USE_OPENAL */
