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
 * Q2PORT: the OpenAL library is the one bundled with the openal-py
 * package (openal_py._core, a typed layer over libopenal), so loading
 * and dlsym'ing it with ctypes/Sys_LoadLibrary is gone. The qal* /
 * qalc* names stay, as thin adapters, so openal.py reads like the C.
 * The C's "qalGetError(); ...; if qalGetError() != 0" pattern is kept
 * by recording the _core ALLError code in _last_error.
 *
 * =======================================================================
"""
from __future__ import annotations

import openal_py
from openal_py import _core

from common import clientserver
from common import cvar
from common.header import shared
from common.shared import shared as shared_c
from client.sound.header import qal as qal_h

#ifdef USE_OPENAL

#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>

#include "../../common/header/common.h"
#include "../../client/sound/header/local.h"
#include "header/qal.h"

# DEFAULT_OPENAL_DRIVER is defined at compile time via the compiler
DEFAULT_OPENAL_DRIVER = "libopenal.so.1"

context = None #static ALCcontext *
device = None #static ALCdevice *
al_device = None #static cvar_t *
al_driver = None #static cvar_t *
hasAlcExtDisconnect = False #static qboolean

# Q2PORT: the AL error code qalGetError() returns. The _core calls raise
# an ALLError on failure and each qal* adapter records the code here.
_last_error = 0 #int

# Q2PORT: the EFX qal* names, in the C's order
_efx = ["GenFilters", "Filteri", "Filterf", "DeleteFilters", "AuxiliaryEffectSloti",
	"GenEffects", "GenAuxiliaryEffectSlots", "Effectf", "Effecti", "Effectfv",
	"DeleteAuxiliaryEffectSlots", "DeleteEffects"]

def _qal(f):

	# Q2PORT: wraps a _core call: on failure record the AL error code
	# (instead of raising) so the C's qalGetError() polling still works
	def wrapper(*args):

		global _last_error

		try:

			return f(*args)

		except openal_py.ALLError as e:

			_last_error = e.code
			return None

	return wrapper

def qalGetError()->int: # (returns ALenum)

	global _last_error

	e = _last_error
	_last_error = 0
	return e

# Q2PORT: the qal* function pointers of the C are thin adapters over
# openal_py._core, keeping the C names and argument order. (The C
# pointers nobody here calls, like qalGetBooleanv, are left out.)

@_qal
def qalIsExtensionPresent(name): #const char * (returns ALboolean)

	return _core.is_extension_present(name.decode("ascii") if isinstance(name, bytes) else name)

@_qal
def qalListenerf(pname, value): #ALenum, ALfloat

	_core.listener_set(pname, float(value))

@_qal
def qalListener3f(pname, x, y, z): #ALenum, ALfloat, ALfloat, ALfloat

	_core.listener_set(pname, (x, y, z))

@_qal
def qalListenerfv(pname, values): #ALenum, ALfloat *

	_core.listener_set(pname, list(values))

@_qal
def qalListeneri(pname, value): #ALenum, ALint

	_core.listener_set(pname, int(value))

@_qal
def qalListener3i(pname, x, y, z): #ALenum, ALint, ALint, ALint

	_core.listener_set(pname, (int(x), int(y), int(z)))

@_qal
def qalGenSources(n): #ALsizei (returns ALuint *)

	return _core.gen_sources(n)

@_qal
def qalDeleteSources(n, sources): #ALsizei, ALuint *

	_core.delete_sources(list(sources))

@_qal
def qalIsSource(source): #ALuint (returns ALboolean)

	return _core.is_source(source)

@_qal
def qalSourcef(source, pname, value): #ALuint, ALenum, ALfloat

	_core.source_set(source, pname, float(value))

@_qal
def qalSource3f(source, pname, x, y, z): #ALuint, ALenum, ALfloat, ALfloat, ALfloat

	_core.source_set(source, pname, (float(x), float(y), float(z)))

@_qal
def qalSourcei(source, pname, value): #ALuint, ALenum, ALint

	_core.source_set(source, pname, int(value))

@_qal
def qalSource3i(source, pname, x, y, z): #ALuint, ALenum, ALint, ALint, ALint

	_core.source_set(source, pname, (int(x), int(y), int(z)))

@_qal
def qalSourcePlay(source): #ALuint

	_core.source_play(source)

@_qal
def qalSourceStop(source): #ALuint

	_core.source_stop(source)

@_qal
def qalSourcePause(source): #ALuint

	_core.source_pause(source)

@_qal
def qalGetSourcef(source, pname): #ALuint, ALenum (returns ALfloat)

	return _core.source_get(source, pname)

@_qal
def qalGetSource3f(source, pname): #ALuint, ALenum (returns ALfloat *)

	return _core.source_get(source, pname, 3)

@_qal
def qalGetSourcei(source, pname): #ALuint, ALenum (returns ALint)

	return _core.source_geti(source, pname)

@_qal
def qalSourceQueueBuffers(source, n, buffers): #ALuint, ALsizei, ALuint *

	_core.source_queue_buffers(source, list(buffers))

@_qal
def qalSourceUnqueueBuffers(source, n): #ALuint, ALsizei (returns ALuint *)

	return _core.source_unqueue_buffers(source, n)

@_qal
def qalGenBuffers(n): #ALsizei (returns ALuint *)

	return _core.gen_buffers(n)

@_qal
def qalDeleteBuffers(n, buffers): #ALsizei, ALuint *

	_core.delete_buffers(list(buffers))

@_qal
def qalIsBuffer(buffer): #ALuint (returns ALboolean)

	return _core.is_buffer(buffer)

@_qal
def qalBufferData(buffer, format, data, size, freq): #ALuint, ALenum, const ALvoid *, ALsizei, ALsizei

	_core.buffer_data(buffer, format, data, freq)

@_qal
def qalDopplerFactor(value): #ALfloat

	_core.doppler_factor(value)

@_qal
def qalDopplerVelocity(value): #ALfloat

	_core.doppler_velocity(value)

@_qal
def qalDistanceModel(model): #ALenum

	_core.distance_model(model)

# EFX (AL_EXT_EFX), the C fetches them via qalGetProcAddress or keeps
# them NULL
@_qal
def qalGenFilters(n): #ALsizei (returns ALuint *)

	return _core.gen_filters(n)

@_qal
def qalFilteri(f, pname, value): #ALuint, ALenum, ALint

	_core.filter_set(f, pname, int(value))

@_qal
def qalFilterf(f, pname, value): #ALuint, ALenum, ALfloat

	_core.filter_set(f, pname, float(value))

@_qal
def qalDeleteFilters(n, filters): #ALsizei, ALuint *

	_core.delete_filters(list(filters))

@_qal
def qalGenEffects(n): #ALsizei (returns ALuint *)

	return _core.gen_effects(n)

@_qal
def qalEffectf(e, pname, value): #ALuint, ALenum, ALfloat

	_core.effect_set(e, pname, float(value))

@_qal
def qalEffecti(e, pname, value): #ALuint, ALenum, ALint

	_core.effect_set(e, pname, int(value))

@_qal
def qalEffectfv(e, pname, values): #ALuint, ALenum, ALfloat *

	_core.effect_set(e, pname, list(values))

@_qal
def qalAuxiliaryEffectSloti(slot, pname, value): #ALuint, ALenum, ALint

	_core.auxiliary_effect_slot_set(slot, pname, int(value))

@_qal
def qalGenAuxiliaryEffectSlots(n): #ALsizei (returns ALuint *)

	return _core.gen_auxiliary_effect_slots(n)

@_qal
def qalDeleteAuxiliaryEffectSlots(n, slots): #ALsizei, ALuint *

	_core.delete_auxiliary_effect_slots(list(slots))

@_qal
def qalDeleteEffects(n, effects): #ALsizei, ALuint *

	_core.delete_effects(list(effects))

"""
 * Gives information over the OpenAL implementation and
 * its state, showing extensions or not.
"""
def QAL_SoundInfo(show_ext: bool): #qboolean

	Printf_Ext = clientserver.Com_Printf if show_ext else clientserver.Com_DPrintf #void (*)(const char *msg, ...)

	clientserver.Com_Printf("OpenAL features:\n")
	clientserver.Com_Printf("AL_VENDOR: {}\n".format(_core.get_string(qal_h.AL_VENDOR)))
	clientserver.Com_Printf("AL_RENDERER: {}\n".format(_core.get_string(qal_h.AL_RENDERER)))
	clientserver.Com_Printf("AL_VERSION: {}\n".format(_core.get_string(qal_h.AL_VERSION)))
	Printf_Ext("AL_EXTENSIONS: {}\n".format(_core.get_string(qal_h.AL_EXTENSIONS)))
	clientserver.Com_Printf("AL_EXTENSIONS number: {}\n".format(shared_c.Word_Count(_core.get_string(qal_h.AL_EXTENSIONS))))

	if _core.is_alc_extension_present("ALC_ENUMERATE_ALL_EXT", None):

		devs = _core.alc_get_string(None, qal_h.ALC_ALL_DEVICES_SPECIFIER) #const char *

		clientserver.Com_Printf("\nAvailable OpenAL devices:\n")

		if devs is None:

			clientserver.Com_Printf("- No devices found. Depending on your\n")
			clientserver.Com_Printf("  platform this may be expected and\n")
			clientserver.Com_Printf("  doesn't indicate a problem!\n")

		else:

			for dev in devs.split("\x00"): # Q2PORT: the C walks the NUL separated list

				if not dev:
					continue

				clientserver.Com_Printf("- {}\n".format(dev))

	if _core.is_alc_extension_present("ALC_ENUMERATE_ALL_EXT", None):

		devs = _core.get_device_spec(device) #const char *

		clientserver.Com_Printf("\nCurrent OpenAL device:\n")

		if devs is None:

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

		connected = _core.get_integer(device, qal_h.ALC_CONNECTED) #ALCint

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

	global context, device

	if context:

		_core.make_context_current(None)
		_core.destroy_context(context)
		context = None

	if device:

		_core.close_device(device)
		device = None

	# Disconnect the EFX function pointers
	# Q2PORT: the C sets qalc* / qal* to NULL, here the EFX adapters to None
	for name in _efx:
		globals()["qal" + name] = None

"""
 * Loads the OpenAL library, creates
 * a context and device handle.
"""
def QAL_Init()->bool: #void (returns qboolean)

	global al_device, al_driver, device, context, hasAlcExtDisconnect

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

		device = _core.open_device(al_device.string if al_device.string else None)

	except openal_py.ALLError:

		clientserver.Com_DPrintf("failed\n")
		return False

	clientserver.Com_Printf("ok\n")

	# Create the OpenAL context
	clientserver.Com_Printf("...creating OpenAL context: ")

	try:

		context = _core.create_context(device, None)

	except openal_py.ALLError:

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	clientserver.Com_Printf("ok\n")

	# Set the created context as current context
	clientserver.Com_Printf("...making context current: ")

	if not _core.make_context_current(context):

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	# Connect the EFX function pointers, or keep them None
	# Q2PORT: the C dlsyms them on ALC_EXT_EFX, else sets them to NULL
	if _core.is_alc_extension_present("ALC_EXT_EFX", device):

		pass

	else:

		for name in _efx:
			globals()["qal" + name] = None

	clientserver.Com_Printf("ok\n")

	# Print OpenAL information
	clientserver.Com_Printf("\n")
	QAL_SoundInfo(False)
	clientserver.Com_Printf("\n")

	#  Check extensions
	hasAlcExtDisconnect = _core.is_alc_extension_present("ALC_EXT_disconnect", device)

	return True

#endif /* USE_OPENAL */
