"""
Copyright (C) 2010, 2013 Yamagi Burmeister
Copyright (C) 2005 Ryan C. Gordon

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

This file implements an interface to libvorbis for decoding
OGG/Vorbis files. Strongly spoken this file isn't part of the sound
system but part of the main client. It justs converts Vorbis streams
into normal, raw Wave stream which are injected into the backends as
if they were normal "raw" samples. At this moment only background
music playback and in theory .cin movie file playback is supported.

=======================================================================
"""
from __future__ import annotations

"""
#ifndef _WIN32
#include <sys/time.h>
#endif

#include <errno.h>

#include "../header/client.h"
#include "header/local.h"
#include "header/vorbis.h"

#define STB_VORBIS_NO_PUSHDATA_API
#include "header/stb_vorbis.h"
"""
from enum import Enum

import numpy as np

from client import cl_main
from client.sound import openal
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
from client.sound.header import stb_vorbis
from client.sound.header import vorbis
from client.header import client as client_h
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common.shared import rand
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from backends.unix import system

ogg_pausewithgame = None #cvar_t *, Pause music when the game is paused
ogg_enabled = None #cvar_t *, Backend is enabled
ogg_shuffle = None #cvar_t *, Shuffle playback
ogg_ignoretrack0 = None #cvar_t *, Toggle track 0 playing
ogg_volume = None #cvar_t *, Music volume.
ogg_curfile = 0 #int, Index of currently played file.
ogg_numbufs = 0 #int, Number of buffers for OpenAL
ogg_numsamples = 0 #int, Number of sambles read from the current file
ogg_mapcdtrack = 0 #int, Index of current map cdtrack
ogg_status = vorbis.STOP #ogg_status_t, Status indicator.
ogg_file = None #stb_vorbis *, Ogg Vorbis file.
ogg_started = False #qboolean, Initialization flag.
ogg_mutemusic = False #qboolean, Mute music

MAX_NUM_OGGTRACKS = 128 #enum
ogg_tracks = [] #char * [MAX_NUM_OGGTRACKS];
for i in range(MAX_NUM_OGGTRACKS):
	ogg_tracks.append(None)
ogg_maxfileindex = 0 #int

class GameType(Enum):

	other = 0 #incl. baseq2
	xatrix = 1
	rogue = 2

class ogg_saved_state_t(object):

	def __init__(self):

		self.saved = False #qboolean
		self.curfile = 0 #int
		self.numsamples = 0 #int

ogg_saved_state = ogg_saved_state_t()

"""
static void
OGG_TogglePlayback(void);
"""
# --------

"""
 * The GOG version of Quake2 has the music tracks in music/TrackXX.ogg
 * That music/ dir is next to baseq2/ (not in it) and contains Track02.ogg to Track21.ogg
 * There
 * - Track02 to Track11 correspond to Quake2 (baseq2) CD tracks 2-11
 * - Track12 to Track21 correspond to the Ground Zero (rogue) addon's CD tracks 2-11
 * - The "The Reckoning" (xatrix) addon also had 11 tracks, that were a mix of the ones
 *   from the main game (baseq2) and the rogue addon.
 *   See below how the CD track is mapped to GOG track numbers
 */
"""
def getMappedGOGtrack(track: int, gameType)->int: #int, enum GameType (returns int)

	if(track <= 0):
	
		return 0

	if(track == 1):
	
		return 0	# 1 is illegal (=> data track on CD), 0 means "no track"

	if(gameType == GameType.other):
	
		return track

	if(gameType == GameType.rogue):
	
		return track + 10

	# apparently it's xatrix => map the track to the corresponding TrackXX.ogg from GOG
	if track == 2: return 9  # baseq2 9
	elif track == 3: return 13  # rogue  3
	elif track == 4: return 14  # rogue  4
	elif track == 5: return 7   # baseq2 7
	elif track == 6: return 16  # rogue  6
	elif track == 7: return 2   # baseq2 2
	elif track == 8: return 15  # rogue  5
	elif track == 9: return 3   # baseq2 3
	elif track == 10: return 4  # baseq2 4
	elif track == 11: return 18 # rogue  8
	else:
		return track

"""
 * Load list of Ogg Vorbis files in "music/".
 */
"""
def OGG_InitTrackList(): #void

	global ogg_maxfileindex

	"""
	const char* potMusicDirs[3];
	char gameMusicDir[MAX_QPATH]; // e.g. "xatrix/music"
	cvar_t* gameCvar;
	enum GameType gameType;
	"""

	for i in range(MAX_NUM_OGGTRACKS):
		# Q2PORT: no free() in Python
		ogg_tracks[i] = None

	ogg_maxfileindex = 0

	gameCvar = cvar.Cvar_Get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)

	if gameCvar.string == '' or common_h.BASEDIRNAME == gameCvar.string:
		# baseq2 => only 2 dirs in searchPath
		potMusicDirs = [common_h.BASEDIRNAME + "/music/", "music/"] # baseq2/music/, global music dir (GOG)
	else:
		# some other mod/addon
		gameMusicDir = "{}{}".format(gameCvar.string, "/music/") # $mod/music/
		potMusicDirs = [gameMusicDir, "music/", common_h.BASEDIRNAME + "/music/"] # $mod/music/, global music dir (GOG), baseq2/music/

	gameType = GameType.other

	if "xatrix" == gameCvar.string:
		gameType = GameType.xatrix
	elif "rogue" == gameCvar.string:
		gameType = GameType.rogue

	for musicDir in potMusicDirs:
	
		rawPath = filesystem.FS_GetNextRawPath(None)
		while rawPath is not None:
		
			fullMusicPath = "{}/{}".format(rawPath, musicDir)
			
			if not system.Sys_IsDir(fullMusicPath):
				rawPath = filesystem.FS_GetNextRawPath(rawPath)
				continue
			
			testFileName = fullMusicPath + "02.ogg"
			
			# the simple case (like before: $mod/music/02.ogg - 11.ogg or whatever)
			if system.Sys_IsFile(testFileName):
			
				ogg_tracks[2] = testFileName
				
				i = 3
				while i < MAX_NUM_OGGTRACKS:
				
					testFileName = "{}{:02d}.ogg".format(fullMusicPath, i)
					
					if system.Sys_IsFile(testFileName):
						ogg_tracks[i] = testFileName
						ogg_maxfileindex = i
					i += 1
				
				return
			
			# the GOG case: music/Track02.ogg to Track21.ogg
			testFileName = "{}Track{:02d}.ogg".format(fullMusicPath, getMappedGOGtrack(8, gameType))
			
			if system.Sys_IsFile(testFileName):
			
				i = 2
				while i < MAX_NUM_OGGTRACKS:
				
					gogTrack = getMappedGOGtrack(i, gameType)
					
					testFileName = "{}Track{:02d}.ogg".format(fullMusicPath, gogTrack)
					
					if system.Sys_IsFile(testFileName):
						ogg_tracks[i] = testFileName
						ogg_maxfileindex = i
					i += 1
				
				return
			
			# the ReRelease case: music/track02.ogg to track79.ogg
			testFileName = "{}track{:02d}.ogg".format(fullMusicPath, getMappedGOGtrack(8, gameType))
			
			if system.Sys_IsFile(testFileName):
			
				i = 2
				while i < MAX_NUM_OGGTRACKS:
				
					gogTrack = getMappedGOGtrack(i, gameType)
					
					testFileName = "{}track{:02d}.ogg".format(fullMusicPath, gogTrack)
					
					if system.Sys_IsFile(testFileName):
						ogg_tracks[i] = testFileName
						ogg_maxfileindex = i
					i += 1
				
				return
			
			rawPath = filesystem.FS_GetNextRawPath(rawPath)

	# if tracks have been found above, we would've returned there
	clientserver.Com_Printf("No Ogg Vorbis music tracks have been found, so there will be no music.\n")

# --------

"""
 * Play a portion of the currently opened file.
"""
def OGG_Read(): #void (static)

	global ogg_numsamples, ogg_status, ogg_numbufs

	samples = np.zeros((4096,), dtype=np.int16) #short [4096]
	volume = 0.0 if (ogg_mutemusic == True) else ogg_volume.value #float

	read_samples = stb_vorbis.stb_vorbis_get_samples_short_interleaved(ogg_file, ogg_file.channels, samples,
		len(samples)) #int

	if read_samples > 0:

		ogg_numsamples += read_samples

		sound_c.S_RawSamples(read_samples, ogg_file.sample_rate, 2, ogg_file.channels, # sizeof(short)
			samples.tobytes(), volume) # (byte *)samples

	else:

		# We cannot call OGG_Stop() here. It flushes the OpenAL sample
		# queue, thus about 12 seconds of music are lost. Instead we
		# just set the OGG state to stop and open a new file. The new
		# files content is added to the sample queue after the remaining
		# samples from the old file.
		stb_vorbis.stb_vorbis_close(ogg_file)
		ogg_status = vorbis.STOP
		ogg_numbufs = 0
		ogg_numsamples = 0

		OGG_PlayTrack("{}".format(ogg_curfile), False, False)

"""
 * Stream music.
"""
def OGG_Stream(): #void

	global ogg_numbufs, ogg_mapcdtrack

	if not ogg_started:

		return

	# OGG playback was disabled since the last package frame.
	# Shutdown the backend to stop all playing tracks and to
	# prevend OGG_PLayTrack() from starting new ones.
	if ogg_enabled.value != 1:

		OGG_Shutdown()
		return

	if ogg_pausewithgame.modified:

		if ((ogg_pausewithgame.value == 0 and ogg_status == vorbis.PAUSE) or
		    (ogg_pausewithgame.value == 1 and ogg_status == vorbis.PLAY)):

			OGG_TogglePlayback()

		ogg_pausewithgame.modified = False

	if ogg_status == vorbis.PLAY:

		# the music is streamed through OpenAL (client/sound/backend.py)
		if sound_c.sound_started == sound_local.SS_OAL:

			# Calculate the number of buffers used
			# for storing decoded OGG/Vorbis data.
			# We take the number of active buffers
			# and add 256. 256 are about 12 seconds
			# worth of sound, more than enough to
			# be resilent against underruns.
			if ogg_numbufs == 0 or openal.active_buffers < ogg_numbufs - 256:

				ogg_numbufs = openal.active_buffers + 256

			# active_buffers are all active OpenAL buffers,
			# buffering normal sfx _and_ ogg/vorbis samples.
			while openal.active_buffers <= ogg_numbufs:

				OGG_Read()


	if ogg_status == vorbis.PLAY and ogg_shuffle.modified:

		# Shuffle was modified before last track finished.
		ogg_shuffle.modified = False

	elif ogg_status == vorbis.STOP and ogg_shuffle.modified:

		# If fullscreen console, clear the map cdtrack.
		if cl_main.cls.state == client_h.connstate_t.ca_disconnected:

			ogg_mapcdtrack = 0 # Track 0 means "stop music".

		# Ogg playback has stopped and shuffle was modified, play the map cdtrack.
		ogg_shuffle.modified = False
		OGG_PlayTrack("{}".format(ogg_mapcdtrack), True, True)

# --------

"""
 * play the ogg file that corresponds to the CD track with the given number
 */
"""
def OGG_PlayTrack(track: str, cdtrack: bool, immediate: bool): #const char *, qboolean, qboolean

	"""
	const char *path = NULL;
	char name[MAX_OSPATH];
	int trackNo;
	"""

	global ogg_curfile, ogg_numsamples, ogg_status, ogg_mapcdtrack, ogg_file

	if sound_c.sound_started == sound_local.SS_NOT:
		return	# sound is not initialized

	if ogg_started is False:
		return

	path = None
	while True:
	
		path = filesystem.FS_NextPath(path)
		if path is None:
			break
		
		res = [0] #int
		#FILE* f;

		name = "{}/music/{}".format(path, track)

		# Open ogg vorbis file.
		f = filesystem.Q_fopen(name, "rb")
		if f is None:
			continue

		# Check running music.
		if ogg_status == vorbis.PLAY:
			OGG_Stop()

		# fclose is not required on error with close_on_free=true
		ogg_file = stb_vorbis.stb_vorbis_open_file(f, True, res, None)

		if res[0] != 0:
			clientserver.Com_Printf("{}: '{}' is not a valid Ogg Vorbis file (error {}).\n".format(
				"OGG_PlayTrack", name, res[0]))
			return

		# Play file.
		ogg_curfile = 0
		ogg_numsamples = 0
		ogg_status = vorbis.PLAY

		return

	# Q2PORT: the C's strtol stops at the first non-digit and returns 0 on failure
	try:
		trackNo = int(track)
	except ValueError:
		trackNo = 0

	# Track 0 means "stop music".
	if trackNo == 0:
		if(ogg_ignoretrack0.value == 0):
			OGG_Stop()
			return
		
		# Special case: If ogg_ignoretrack0 is 0 we stopped the music (see above)
		# and ogg_curfile is still holding the last track played (track >1). So
		# this triggers and we return. If ogg_ignoretrack is 1 we didn't stop the
		# music, as soon as the tracks ends OGG_Read() starts it over. Until here
		# everything's okay.
		# But if ogg_ignoretrack0 is 1, the game was just restarted and a save game
		# load send us trackNo 0, we would end up without music. Since we have no
		# way to get the last track before trackNo 0 was set just fall through and
		# shuffle a random track (see below).
		if ogg_curfile > 0:
			return

	if cdtrack == True:			# the map cdtrack.
		ogg_mapcdtrack = trackNo

	playback = ogg_shuffle.value
	curtrack = 0

	# If loading a map, restarting sound or video, the ogg backend or console issued
	# a playtrack or no tracks have been played, apply shuffle parameters to the next
	# track.
	if (immediate == False and (cl_main.cls.state == client_h.connstate_t.ca_connecting or cl_main.cls.state == client_h.connstate_t.ca_connected)) or \
		immediate == True or ogg_curfile == -1:
		curtrack = trackNo
		playback = 0
	else:
		curtrack = ogg_curfile

	newtrack = 0

	# These must match those in menu.c - Options_MenuInit().
	if playback == 0:				# default
		newtrack = curtrack
	elif playback == 1:			# play once
		return
	elif playback == 2:			# sequential
		newtrack = (curtrack + 1) if ((curtrack + 1) % (ogg_maxfileindex + 1) != 0) else 2
	elif playback == 3:			# random
		newtrack = (rand.randk() % (ogg_maxfileindex - 1) + 2)
		newtrack = (newtrack + 1) if (newtrack == curtrack) else newtrack
		newtrack = 2 if (newtrack > ogg_maxfileindex) else newtrack

	trackNo = newtrack

	if ogg_maxfileindex == -1:
		return	# no ogg files at all, ignore this silently instead of printing warnings all the time

	if (trackNo < 2) or (trackNo > ogg_maxfileindex):
		clientserver.Com_Printf("OGG_PlayTrack: %d out of range.\n", trackNo)
		return

	if ogg_tracks[trackNo] is None:
		clientserver.Com_Printf("OGG_PlayTrack: Don't have a .ogg file for track %d\n", trackNo)

	# Check running music.
	if ogg_status == vorbis.PLAY:
		if ogg_curfile == trackNo:
			return
		else:
			OGG_Stop()

	if ogg_tracks[trackNo] is None:
		clientserver.Com_Printf("OGG_PlayTrack: I don't have a file for track %d!\n", trackNo)
		return

	# Open ogg vorbis file.
	f = filesystem.Q_fopen(ogg_tracks[trackNo], "rb") #FILE*

	if f is None:
		clientserver.Com_Printf("%s: could not open file %s for track %d: %s.\n",
			"OGG_PlayTrack", ogg_tracks[trackNo], trackNo, "No such file or directory") # strerror(errno)
		ogg_tracks[trackNo] = None

		return

	res = [0] #int

	# fclose is not required on error with close_on_free=true
	ogg_file = stb_vorbis.stb_vorbis_open_file(f, True, res, None)

	if res[0] != 0:
		clientserver.Com_Printf("%s: '%s' is not a valid Ogg Vorbis file (error %i).\n",
			"OGG_PlayTrack", ogg_tracks[trackNo], res[0])

		return

	# Play file.
	ogg_curfile = trackNo
	ogg_numsamples = 0
	ogg_status = vorbis.PLAY

# ----

"""
 * List Ogg Vorbis files and print current playback state.
 */
"""
def OGG_Info(): #void (static)

	clientserver.Com_Printf("Tracks:\n")

	for i in range(2, ogg_maxfileindex + 1):
		if ogg_tracks[i]:
			clientserver.Com_Printf(" - %02d %s\n", i, ogg_tracks[i])
		else:
			clientserver.Com_Printf(" - %02d <none>\n", i)

	clientserver.Com_Printf("Total: %d Ogg/Vorbis files.\n", ogg_maxfileindex + 1)

	if ogg_status == vorbis.PLAY:
		clientserver.Com_Printf("State: Playing file %d (%s) at %i samples.\n",
			ogg_curfile, ogg_tracks[ogg_curfile], stb_vorbis.stb_vorbis_get_sample_offset(ogg_file))
	elif ogg_status == vorbis.PAUSE:
		clientserver.Com_Printf("State: Paused file %d (%s) at %i samples.\n",
			ogg_curfile, ogg_tracks[ogg_curfile], stb_vorbis.stb_vorbis_get_sample_offset(ogg_file))
	elif ogg_status == vorbis.STOP:
		if ogg_curfile == -1:
			clientserver.Com_Printf("State: Stopped.\n")
		else:
			clientserver.Com_Printf("State: Stopped file %d (%s).\n", ogg_curfile, ogg_tracks[ogg_curfile])

"""
 * Stop playing the current file.
 */
"""
def OGG_Stop(): #void

	global ogg_status, ogg_numbufs

	if ogg_status == vorbis.STOP:
		return

	if sound_c.backend is not None:
		sound_c.backend.unqueue_raw_samples()

	stb_vorbis.stb_vorbis_close(ogg_file)
	ogg_status = vorbis.STOP
	ogg_numbufs = 0

"""
 * Pause or resume playback.
 */
"""
def OGG_TogglePlayback(): #void (static)

	global ogg_status, ogg_numbufs

	if ogg_status == vorbis.PLAY:
		ogg_status = vorbis.PAUSE
		ogg_numbufs = 0

		if sound_c.backend is not None:
			sound_c.backend.unqueue_raw_samples()

	elif ogg_status == vorbis.PAUSE:
		ogg_status = vorbis.PLAY

"""
 * Prints a help message for the 'ogg' cmd.
 */
"""
def OGG_HelpMsg(): #void (static)

	clientserver.Com_Printf("Unknown sub command %s\n\n", cmdparser.Cmd_Argv(1))
	clientserver.Com_Printf("Commands:\n")
	clientserver.Com_Printf(" - info: Print information about playback state and tracks\n")
	clientserver.Com_Printf(" - play <track>: Play track number <track>\n")
	clientserver.Com_Printf(" - stop: Stop playback\n")
	clientserver.Com_Printf(" - toggle: Toggle pause\n")
	clientserver.Com_Printf(" - mute: Mute playback\n")

"""
 * The 'ogg' cmd. Gives some control and information about the playback state.
 */
"""
def OGG_Cmd(): #void (static)

	global ogg_mutemusic

	if cmdparser.Cmd_Argc() < 2:
		OGG_HelpMsg()
		return

	if shared_c.Q_stricmp(cmdparser.Cmd_Argv(1), "info") == 0:
		OGG_Info()
	elif shared_c.Q_stricmp(cmdparser.Cmd_Argv(1), "mute") == 0:
		ogg_mutemusic = not ogg_mutemusic
	elif shared_c.Q_stricmp(cmdparser.Cmd_Argv(1), "play") == 0:
		if cmdparser.Cmd_Argc() != 3:
			clientserver.Com_Printf("ogg play <track> : Play <track>")
			return
		
		OGG_PlayTrack(cmdparser.Cmd_Argv(2), False, True)
	elif shared_c.Q_stricmp(cmdparser.Cmd_Argv(1), "skip") == 0:
		curtrack = "{}".format(ogg_curfile)
		OGG_Stop()
		OGG_PlayTrack(curtrack, False, False)
	elif shared_c.Q_stricmp(cmdparser.Cmd_Argv(1), "stop") == 0:
		OGG_Stop()
	elif shared_c.Q_stricmp(cmdparser.Cmd_Argv(1), "toggle") == 0:
		OGG_TogglePlayback()
	else:
		OGG_HelpMsg()

"""
 * Saves the current state of the subsystem.
 */
"""
def OGG_SaveState(): #void

	# Q2PORT: fix, ogg_enabled is NULL when OGG_Init() never ran (s_initsound 0
	# or no sound backend), and the C dereferences it here
	if ogg_enabled is None or ogg_enabled.value != 1 or ogg_status != vorbis.PLAY:
		ogg_saved_state.saved = False
		return

	ogg_saved_state.saved = True
	ogg_saved_state.curfile = ogg_curfile
	ogg_saved_state.numsamples = ogg_numsamples

"""
 * Recover the previously saved state.
 */
"""
def OGG_RecoverState(): #void

	global ogg_numsamples

	# Q2PORT: fix, ogg_enabled is NULL when OGG_Init() never ran (see OGG_SaveState())
	if ogg_enabled is None or ogg_enabled.value != 1 or ogg_saved_state.saved is not True:
		return

	# Mkay, ultra evil hack to recover the state in case of
	# shuffled playback. OGG_PlayTrack() does the shuffeling,
	# so switch it of before and enable after state recovery.
	shuffle_state = ogg_shuffle.value
	cvar.Cvar_SetValue("ogg_shuffle", 0)

	OGG_PlayTrack("{}".format(ogg_saved_state.curfile), False, True)
	stb_vorbis.stb_vorbis_seek_frame(ogg_file, ogg_saved_state.numsamples)
	ogg_numsamples = ogg_saved_state.numsamples

	cvar.Cvar_SetValue("ogg_shuffle", shuffle_state)

"""
 * Returns ogg status.
 */
"""
def OGG_Status()->int: #void (returns int)

	return ogg_status

# --------

"""
 * Initialize the Ogg Vorbis subsystem.
 */
"""
def OGG_Init(): #void

	global ogg_pausewithgame, ogg_enabled, ogg_shuffle, ogg_ignoretrack0, ogg_volume
	global ogg_curfile, ogg_numsamples, ogg_status, ogg_mapcdtrack, ogg_mutemusic, ogg_started

	# Cvars
	ogg_pausewithgame = cvar.Cvar_Get("ogg_pausewithgame", "0", shared.CVAR_ARCHIVE)
	ogg_shuffle = cvar.Cvar_Get("ogg_shuffle", "0", shared.CVAR_ARCHIVE)
	ogg_ignoretrack0 = cvar.Cvar_Get("ogg_ignoretrack0", "0", shared.CVAR_ARCHIVE)
	ogg_volume = cvar.Cvar_Get("ogg_volume", "0.7", shared.CVAR_ARCHIVE)
	ogg_enabled = cvar.Cvar_Get("ogg_enable", "1", shared.CVAR_ARCHIVE)

	if ogg_enabled.value != 1:
		return

	# Commands
	cmdparser.Cmd_AddCommand("ogg", OGG_Cmd)

	# Global variables
	ogg_curfile = -1
	ogg_numsamples = 0
	ogg_status = vorbis.STOP

	ogg_mapcdtrack = 0

	ogg_mutemusic = False
	ogg_started = True

"""
 * Shutdown the Ogg Vorbis subsystem.
 */
"""
def OGG_Shutdown(): #void

	global ogg_started, ogg_maxfileindex

	if not ogg_started:
		return

	# Music must be stopped.
	OGG_Stop()

	# Free file list.
	for i in range(MAX_NUM_OGGTRACKS):
		ogg_tracks[i] = None	# Q2PORT: no free() in Python

	ogg_maxfileindex = 0

	# Remove console commands
	cmdparser.Cmd_RemoveCommand("ogg")

	ogg_started = False

def OGG_LoadAsWav(filename: str)->tuple: #char *, wavinfo_t *, void ** (Q2PORT: returns info, buffer)

	info = None #wavinfo_t *
	buffer = None #void *
	temp_buffer = None #void *
	size, temp_buffer = filesystem.FS_LoadFile(filename) #int
	final_buffer = None #short *
	ogg2wav_file = None #stb_vorbis *
	res = [0] #int

	if temp_buffer is None:

		# no such file
		return info, buffer

	# load vorbis file from memory
	ogg2wav_file = stb_vorbis.stb_vorbis_open_memory(temp_buffer, size, res, None)
	if not res[0] and ogg2wav_file.channels > 0:

		read_samples = 0 #int

		# fill in wav structure
		info = sound_local.wavinfo_t()
		info.rate = ogg2wav_file.sample_rate
		info.width = 2
		info.channels = ogg2wav_file.channels
		info.loopstart = -1
		# return length * channels
		info.samples = stb_vorbis.stb_vorbis_stream_length_in_samples(ogg2wav_file) * info.channels
		info.dataofs = 0

		# alloc memory for uncompressed wav
		final_buffer = np.zeros((info.samples,), dtype=np.int16) # Z_Malloc(info->samples * sizeof(short))

		# load sampleas to buffer
		read_samples = stb_vorbis.stb_vorbis_get_samples_short_interleaved(
			ogg2wav_file, info.channels, final_buffer,
			info.samples)

		if read_samples > 0:

			# fix sample list size
			if (read_samples * info.channels) != info.samples:

				clientserver.Com_DPrintf("%s: incorrect size: %d != %d\n",
					filename, info.samples, read_samples * info.channels)

				info.samples = read_samples * info.channels

			# copy to final result
			buffer = final_buffer[:info.samples].tobytes()

		else:

			# something is going wrong
			final_buffer = None

	if ogg2wav_file:

		stb_vorbis.stb_vorbis_close(ogg2wav_file)

	filesystem.FS_FreeFile(temp_buffer)

	return info, buffer
