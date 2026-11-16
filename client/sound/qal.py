"""
 * Copyright (C) 2012 Yamagi Burmeister
 * Copyright (C) 2010 skuller.net
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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * Low level, platform depended "qal" API implementation. This files
 * provides functions to load, initialize, shutdown und unload the
 * OpenAL library and connects the "qal" funtion pointers to the
 * OpenAL functions. It shopuld work on Windows and unixoid Systems,
 * other platforms may need an own implementation. This source file
 * was taken from Q2Pro and modified by the YQ2 authors.
 *
 * Q2PORT: openal-py's AudioEngine owns static sounds and voices. The
 * QAL entry points still own device/context startup, shutdown and recovery;
 * OpenAL parameters and EFX use the library's public object API.
 *
 * =======================================================================
"""
from __future__ import annotations

import typing

import openal_py

from common import clientserver
from common import cvar
from common.header import shared
from common.shared import shared as shared_c
from client.sound.header import local as sound_local

#ifdef USE_OPENAL

#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>

#include "../../common/header/common.h"
#include "../../client/sound/header/local.h"
#include "header/qal.h"

# DEFAULT_OPENAL_DRIVER is defined at compile time via the compiler
DEFAULT_OPENAL_DRIVER = "libopenal.so.1"

context: openal_py.Context | None = None #static ALCcontext *
device: openal_py.Device | None = None #static ALCdevice *
al_device = None #static cvar_t *
al_driver = None #static cvar_t *
hasAlcExtDisconnect = False #static qboolean

class QALAudioEngine(openal_py.AudioEngine):

	# Q2PORT: AudioEngine's hook configures attenuation and EFX before play().
	configure_voice: typing.Callable[[openal_py.Voice], None] | None = None

	def _create_voice(self, sound: openal_py.Sound, source: openal_py.Source)->openal_py.Voice:

		voice = super()._create_voice(sound, source)
		if self.configure_voice is not None:
			self.configure_voice(voice)
		return voice


audio: QALAudioEngine | None = None

"""
 * Gives information over the OpenAL implementation and
 * its state, showing extensions or not.
"""
def QAL_SoundInfo(show_ext: bool): #qboolean

	Printf_Ext = clientserver.Com_Printf if show_ext else clientserver.Com_DPrintf #void (*)(const char *msg, ...)

	clientserver.Com_Printf("OpenAL features:\n")
	clientserver.Com_Printf("AL_VENDOR: {}\n".format(context.vendor))
	clientserver.Com_Printf("AL_RENDERER: {}\n".format(context.renderer))
	clientserver.Com_Printf("AL_VERSION: {}\n".format(context.version))
	Printf_Ext("AL_EXTENSIONS: {}\n".format(" ".join(sorted(context.extensions))))
	clientserver.Com_Printf("AL_EXTENSIONS number: {}\n".format(shared_c.Word_Count(" ".join(sorted(context.extensions)))))

	if device.supports("ALC_ENUMERATE_ALL_EXT"):

		devs = openal_py.enumerate_devices() #const char *

		clientserver.Com_Printf("\nAvailable OpenAL devices:\n")

		if not devs:

			clientserver.Com_Printf("- No devices found. Depending on your\n")
			clientserver.Com_Printf("  platform this may be expected and\n")
			clientserver.Com_Printf("  doesn't indicate a problem!\n")

		else:

			for dev in devs:

				if not dev:
					continue

				clientserver.Com_Printf("- {}\n".format(dev))

	if device.supports("ALC_ENUMERATE_ALL_EXT"):

		devs = device.spec #const char *

		clientserver.Com_Printf("\nCurrent OpenAL device:\n")

		if not devs:

			clientserver.Com_Printf("- No OpenAL device in use\n")

		else:

			clientserver.Com_Printf("- {}\n".format(devs))

"""
 * Checks if the output device is still connected. Returns true
 * if it is, false otherwise. Should be called every frame, if
 * disconnected a 'snd_restart' is injected after waiting for 2.5
 * seconds.
 *
 * This is mostly a work around for broken Sound driver. For
 * example the _good_ Intel display driver for Windows 10
 * destroys the DisplayPort sound device when the display
 * resolution changes and recreates it after an unspecified
 * amount of time...
"""
discoCount = 0 #static int, QAL_RecoverLostDevice

def QAL_RecoverLostDevice()->bool: #void (returns qboolean)

	global discoCount

	if not hasAlcExtDisconnect:

		return True

	if discoCount == 0:

		connected = device.get_parameter("ALC_CONNECTED") #ALCint

		if not connected:

			discoCount += 1
			return False

		else:

			return True

	else:

		# Wait for about 2.5 seconds
		# before trying to reconnect.
		if discoCount < int(cvar.Cvar_VariableValue("cl_maxfps") * 2.5):

			discoCount += 1
			return False

		else:

			# Q2PORT: the C's Cbuf_AddText("snd_restart\n")
			from common import cmdparser
			cmdparser.Cbuf_AddText("snd_restart\n")
			discoCount = 0
			return False

"""
 * Shuts OpenAL down, frees all context and
 * device handles.
"""
def QAL_Shutdown(): #void

	global audio, context, device, hasAlcExtDisconnect, discoCount

	if audio is not None:

		audio.close()
		audio = None
		context = None

	if device is not None:

		device.close()
		device = None

	hasAlcExtDisconnect = False
	discoCount = 0

"""
 * Loads the OpenAL library, creates
 * a context and device handle.
"""
def QAL_Init()->bool: #void (returns qboolean)

	global al_device, al_driver, device, context, audio, hasAlcExtDisconnect

	al_device = cvar.Cvar_Get("al_device", "", shared.CVAR_ARCHIVE)

	# DEFAULT_OPENAL_DRIVER is defined at compile time via the compiler
	al_driver = cvar.Cvar_Get("al_driver", DEFAULT_OPENAL_DRIVER, shared.CVAR_ARCHIVE)

	if ".." in al_driver.string or ':' in al_driver.string or '/' in al_driver.string or '\\' in al_driver.string:

		clientserver.Com_Printf("al_driver must not contain '..', ':', '/' or '\\': {}\n".format(al_driver.string))
		return False

	# Q2PORT: the library is the one bundled with the openal-py package;
	# al_driver is kept for compatibility.
	clientserver.Com_Printf("OpenAL library: {}\n".format(openal_py.library_path()))

	# Open the OpenAL device
	clientserver.Com_Printf("...opening OpenAL device: ")

	try:

		device = openal_py.Device.open(al_device.string or None)

	except (openal_py.OpenALError, openal_py.LifecycleError):

		clientserver.Com_DPrintf("failed\n")
		return False

	clientserver.Com_Printf("ok\n")

	# Create the OpenAL context
	clientserver.Com_Printf("...creating OpenAL context: ")

	try:

		audio = QALAudioEngine(device=device, max_voices=sound_local.MAX_CHANNELS - 1)
		context = audio.context

	except (openal_py.OpenALError, openal_py.LifecycleError):

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	clientserver.Com_Printf("ok\n")

	# Set the created context as current context
	clientserver.Com_Printf("...making context current: ")

	try:

		# Q2PORT: the frame thread owns playback. Pyglet only decodes music
		# and uses its silent driver, so it cannot replace this context.
		context.make_current()

	except (openal_py.OpenALError, openal_py.LifecycleError):

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	clientserver.Com_Printf("ok\n")

	# Print OpenAL information
	clientserver.Com_Printf("\n")
	QAL_SoundInfo(False)
	clientserver.Com_Printf("\n")

	#  Check extensions
	hasAlcExtDisconnect = device.supports("ALC_EXT_disconnect")

	return True

#endif /* USE_OPENAL */
