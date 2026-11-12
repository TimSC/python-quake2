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
 * =======================================================================
"""
from __future__ import annotations

import ctypes
from ctypes import c_int, c_uint, c_float, c_double, c_char_p, c_void_p, c_ubyte, POINTER

from backends.unix import system
from common import clientserver
from common import cmdparser
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
handle = None #static void *

# Q2PORT: the ctypes types of the AL typedefs (al.h, alc.h)
ALboolean = c_ubyte
ALchar = ctypes.c_char
ALint = c_int
ALuint = c_uint
ALsizei = c_int
ALenum = c_int
ALfloat = c_float
ALdouble = c_double
ALvoid_p = c_void_p
ALCboolean = c_ubyte
ALCint = c_int
ALCenum = c_int
ALCsizei = c_int
ALCdevice_p = c_void_p
ALCcontext_p = c_void_p

# Q2PORT: the prototypes of the LPAL... function pointer types (al.h, alc.h, efx.h);
# name -> (return type, argument types). The string getters return a pointer, as
# alcGetString's device lists are several NUL terminated strings in a row.
_prototypes = {
	"alcCreateContext": (ALCcontext_p, [ALCdevice_p, POINTER(ALCint)]),
	"alcMakeContextCurrent": (ALCboolean, [ALCcontext_p]),
	"alcProcessContext": (None, [ALCcontext_p]),
	"alcSuspendContext": (None, [ALCcontext_p]),
	"alcDestroyContext": (None, [ALCcontext_p]),
	"alcGetCurrentContext": (ALCcontext_p, []),
	"alcGetContextsDevice": (ALCdevice_p, [ALCcontext_p]),
	"alcOpenDevice": (ALCdevice_p, [c_char_p]),
	"alcCloseDevice": (ALCboolean, [ALCdevice_p]),
	"alcGetError": (ALCenum, [ALCdevice_p]),
	"alcIsExtensionPresent": (ALCboolean, [ALCdevice_p, c_char_p]),
	"alcGetProcAddress": (c_void_p, [ALCdevice_p, c_char_p]),
	"alcGetEnumValue": (ALCenum, [ALCdevice_p, c_char_p]),
	"alcGetString": (c_void_p, [ALCdevice_p, ALCenum]),
	"alcGetIntegerv": (None, [ALCdevice_p, ALCenum, ALCsizei, POINTER(ALCint)]),
	"alcCaptureOpenDevice": (ALCdevice_p, [c_char_p, c_uint, ALCenum, ALCsizei]),
	"alcCaptureCloseDevice": (ALCboolean, [ALCdevice_p]),
	"alcCaptureStart": (None, [ALCdevice_p]),
	"alcCaptureStop": (None, [ALCdevice_p]),
	"alcCaptureSamples": (None, [ALCdevice_p, c_void_p, ALCsizei]),

	"alEnable": (None, [ALenum]),
	"alDisable": (None, [ALenum]),
	"alIsEnabled": (ALboolean, [ALenum]),
	"alGetString": (c_void_p, [ALenum]),
	"alGetBooleanv": (None, [ALenum, POINTER(ALboolean)]),
	"alGetIntegerv": (None, [ALenum, POINTER(ALint)]),
	"alGetFloatv": (None, [ALenum, POINTER(ALfloat)]),
	"alGetDoublev": (None, [ALenum, POINTER(ALdouble)]),
	"alGetBoolean": (ALboolean, [ALenum]),
	"alGetInteger": (ALint, [ALenum]),
	"alGetFloat": (ALfloat, [ALenum]),
	"alGetDouble": (ALdouble, [ALenum]),
	"alGetError": (ALenum, []),
	"alIsExtensionPresent": (ALboolean, [c_char_p]),
	"alGetProcAddress": (c_void_p, [c_char_p]),
	"alGetEnumValue": (ALenum, [c_char_p]),
	"alListenerf": (None, [ALenum, ALfloat]),
	"alListener3f": (None, [ALenum, ALfloat, ALfloat, ALfloat]),
	"alListenerfv": (None, [ALenum, POINTER(ALfloat)]),
	"alListeneri": (None, [ALenum, ALint]),
	"alListener3i": (None, [ALenum, ALint, ALint, ALint]),
	"alListeneriv": (None, [ALenum, POINTER(ALint)]),
	"alGetListenerf": (None, [ALenum, POINTER(ALfloat)]),
	"alGetListener3f": (None, [ALenum, POINTER(ALfloat), POINTER(ALfloat), POINTER(ALfloat)]),
	"alGetListenerfv": (None, [ALenum, POINTER(ALfloat)]),
	"alGetListeneri": (None, [ALenum, POINTER(ALint)]),
	"alGetListener3i": (None, [ALenum, POINTER(ALint), POINTER(ALint), POINTER(ALint)]),
	"alGetListeneriv": (None, [ALenum, POINTER(ALint)]),
	"alGenSources": (None, [ALsizei, POINTER(ALuint)]),
	"alDeleteSources": (None, [ALsizei, POINTER(ALuint)]),
	"alIsSource": (ALboolean, [ALuint]),
	"alSourcef": (None, [ALuint, ALenum, ALfloat]),
	"alSource3f": (None, [ALuint, ALenum, ALfloat, ALfloat, ALfloat]),
	"alSourcefv": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alSourcei": (None, [ALuint, ALenum, ALint]),
	"alSource3i": (None, [ALuint, ALenum, ALint, ALint, ALint]),
	"alSourceiv": (None, [ALuint, ALenum, POINTER(ALint)]),
	"alGetSourcef": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alGetSource3f": (None, [ALuint, ALenum, POINTER(ALfloat), POINTER(ALfloat), POINTER(ALfloat)]),
	"alGetSourcefv": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alGetSourcei": (None, [ALuint, ALenum, POINTER(ALint)]),
	"alGetSource3i": (None, [ALuint, ALenum, POINTER(ALint), POINTER(ALint), POINTER(ALint)]),
	"alGetSourceiv": (None, [ALuint, ALenum, POINTER(ALint)]),
	"alSourcePlayv": (None, [ALsizei, POINTER(ALuint)]),
	"alSourceStopv": (None, [ALsizei, POINTER(ALuint)]),
	"alSourceRewindv": (None, [ALsizei, POINTER(ALuint)]),
	"alSourcePausev": (None, [ALsizei, POINTER(ALuint)]),
	"alSourcePlay": (None, [ALuint]),
	"alSourceStop": (None, [ALuint]),
	"alSourceRewind": (None, [ALuint]),
	"alSourcePause": (None, [ALuint]),
	"alSourceQueueBuffers": (None, [ALuint, ALsizei, POINTER(ALuint)]),
	"alSourceUnqueueBuffers": (None, [ALuint, ALsizei, POINTER(ALuint)]),
	"alGenBuffers": (None, [ALsizei, POINTER(ALuint)]),
	"alDeleteBuffers": (None, [ALsizei, POINTER(ALuint)]),
	"alIsBuffer": (ALboolean, [ALuint]),
	"alBufferData": (None, [ALuint, ALenum, ALvoid_p, ALsizei, ALsizei]),
	"alBufferf": (None, [ALuint, ALenum, ALfloat]),
	"alBuffer3f": (None, [ALuint, ALenum, ALfloat, ALfloat, ALfloat]),
	"alBufferfv": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alBufferi": (None, [ALuint, ALenum, ALint]),
	"alBuffer3i": (None, [ALuint, ALenum, ALint, ALint, ALint]),
	"alBufferiv": (None, [ALuint, ALenum, POINTER(ALint)]),
	"alGetBufferf": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alGetBuffer3f": (None, [ALuint, ALenum, POINTER(ALfloat), POINTER(ALfloat), POINTER(ALfloat)]),
	"alGetBufferfv": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alGetBufferi": (None, [ALuint, ALenum, POINTER(ALint)]),
	"alGetBuffer3i": (None, [ALuint, ALenum, POINTER(ALint), POINTER(ALint), POINTER(ALint)]),
	"alGetBufferiv": (None, [ALuint, ALenum, POINTER(ALint)]),
	"alDopplerFactor": (None, [ALfloat]),
	"alDopplerVelocity": (None, [ALfloat]),
	"alSpeedOfSound": (None, [ALfloat]),
	"alDistanceModel": (None, [ALenum]),

	# efx.h
	"alGenFilters": (None, [ALsizei, POINTER(ALuint)]),
	"alFilteri": (None, [ALuint, ALenum, ALint]),
	"alFilterf": (None, [ALuint, ALenum, ALfloat]),
	"alDeleteFilters": (None, [ALsizei, POINTER(ALuint)]),
	"alGenEffects": (None, [ALsizei, POINTER(ALuint)]),
	"alEffectf": (None, [ALuint, ALenum, ALfloat]),
	"alEffecti": (None, [ALuint, ALenum, ALint]),
	"alEffectfv": (None, [ALuint, ALenum, POINTER(ALfloat)]),
	"alAuxiliaryEffectSloti": (None, [ALuint, ALenum, ALint]),
	"alGenAuxiliaryEffectSlots": (None, [ALsizei, POINTER(ALuint)]),
	"alDeleteAuxiliaryEffectSlots": (None, [ALsizei, POINTER(ALuint)]),
	"alDeleteEffects": (None, [ALsizei, POINTER(ALuint)]),
}

# Function pointers for OpenAL management
qalcCreateContext = None #static LPALCCREATECONTEXT
qalcMakeContextCurrent = None #static LPALCMAKECONTEXTCURRENT
qalcProcessContext = None #static LPALCPROCESSCONTEXT
qalcSuspendContext = None #static LPALCSUSPENDCONTEXT
qalcDestroyContext = None #static LPALCDESTROYCONTEXT
qalcGetCurrentContext = None #static LPALCGETCURRENTCONTEXT
qalcGetContextsDevice = None #static LPALCGETCONTEXTSDEVICE
qalcOpenDevice = None #static LPALCOPENDEVICE
qalcCloseDevice = None #static LPALCCLOSEDEVICE
qalcGetError = None #static LPALCGETERROR
qalcIsExtensionPresent = None #static LPALCISEXTENSIONPRESENT
qalcGetProcAddress = None #static LPALCGETPROCADDRESS
qalcGetEnumValue = None #static LPALCGETENUMVALUE
qalcGetString = None #static LPALCGETSTRING
qalcGetIntegerv = None #static LPALCGETINTEGERV
qalcCaptureOpenDevice = None #static LPALCCAPTUREOPENDEVICE
qalcCaptureCloseDevice = None #static LPALCCAPTURECLOSEDEVICE
qalcCaptureStart = None #static LPALCCAPTURESTART
qalcCaptureStop = None #static LPALCCAPTURESTOP
qalcCaptureSamples = None #static LPALCCAPTURESAMPLES

# Declaration of function pointers used
# to connect OpenAL to our internal API
qalEnable = None #LPALENABLE
qalDisable = None #LPALDISABLE
qalIsEnabled = None #LPALISENABLED
qalGetString = None #LPALGETSTRING
qalGetBooleanv = None #LPALGETBOOLEANV
qalGetIntegerv = None #LPALGETINTEGERV
qalGetFloatv = None #LPALGETFLOATV
qalGetDoublev = None #LPALGETDOUBLEV
qalGetBoolean = None #LPALGETBOOLEAN
qalGetInteger = None #LPALGETINTEGER
qalGetFloat = None #LPALGETFLOAT
qalGetDouble = None #LPALGETDOUBLE
qalGetError = None #LPALGETERROR
qalIsExtensionPresent = None #LPALISEXTENSIONPRESENT
qalGetProcAddress = None #LPALGETPROCADDRESS
qalGetEnumValue = None #LPALGETENUMVALUE
qalListenerf = None #LPALLISTENERF
qalListener3f = None #LPALLISTENER3F
qalListenerfv = None #LPALLISTENERFV
qalListeneri = None #LPALLISTENERI
qalListener3i = None #LPALLISTENER3I
qalListeneriv = None #LPALLISTENERIV
qalGetListenerf = None #LPALGETLISTENERF
qalGetListener3f = None #LPALGETLISTENER3F
qalGetListenerfv = None #LPALGETLISTENERFV
qalGetListeneri = None #LPALGETLISTENERI
qalGetListener3i = None #LPALGETLISTENER3I
qalGetListeneriv = None #LPALGETLISTENERIV
qalGenSources = None #LPALGENSOURCES
qalDeleteSources = None #LPALDELETESOURCES
qalIsSource = None #LPALISSOURCE
qalSourcef = None #LPALSOURCEF
qalSource3f = None #LPALSOURCE3F
qalSourcefv = None #LPALSOURCEFV
qalSourcei = None #LPALSOURCEI
qalSource3i = None #LPALSOURCE3I
qalSourceiv = None #LPALSOURCEIV
qalGetSourcef = None #LPALGETSOURCEF
qalGetSource3f = None #LPALGETSOURCE3F
qalGetSourcefv = None #LPALGETSOURCEFV
qalGetSourcei = None #LPALGETSOURCEI
qalGetSource3i = None #LPALGETSOURCE3I
qalGetSourceiv = None #LPALGETSOURCEIV
qalSourcePlayv = None #LPALSOURCEPLAYV
qalSourceStopv = None #LPALSOURCESTOPV
qalSourceRewindv = None #LPALSOURCEREWINDV
qalSourcePausev = None #LPALSOURCEPAUSEV
qalSourcePlay = None #LPALSOURCEPLAY
qalSourceStop = None #LPALSOURCESTOP
qalSourceRewind = None #LPALSOURCEREWIND
qalSourcePause = None #LPALSOURCEPAUSE
qalSourceQueueBuffers = None #LPALSOURCEQUEUEBUFFERS
qalSourceUnqueueBuffers = None #LPALSOURCEUNQUEUEBUFFERS
qalGenBuffers = None #LPALGENBUFFERS
qalDeleteBuffers = None #LPALDELETEBUFFERS
qalIsBuffer = None #LPALISBUFFER
qalBufferData = None #LPALBUFFERDATA
qalBufferf = None #LPALBUFFERF
qalBuffer3f = None #LPALBUFFER3F
qalBufferfv = None #LPALBUFFERFV
qalBufferi = None #LPALBUFFERI
qalBuffer3i = None #LPALBUFFER3I
qalBufferiv = None #LPALBUFFERIV
qalGetBufferf = None #LPALGETBUFFERF
qalGetBuffer3f = None #LPALGETBUFFER3F
qalGetBufferfv = None #LPALGETBUFFERFV
qalGetBufferi = None #LPALGETBUFFERI
qalGetBuffer3i = None #LPALGETBUFFER3I
qalGetBufferiv = None #LPALGETBUFFERIV
qalDopplerFactor = None #LPALDOPPLERFACTOR
qalDopplerVelocity = None #LPALDOPPLERVELOCITY
qalSpeedOfSound = None #LPALSPEEDOFSOUND
qalDistanceModel = None #LPALDISTANCEMODEL
qalGenFilters = None #LPALGENFILTERS
qalFilteri = None #LPALFILTERI
qalFilterf = None #LPALFILTERF
qalDeleteFilters = None #LPALDELETEFILTERS
qalGenEffects = None #LPALGENEFFECTS
qalEffectf = None #LPALEFFECTF
qalEffecti = None #LPALEFFECTI
qalEffectfv = None #LPALEFFECTFV
qalAuxiliaryEffectSloti = None #LPALAUXILIARYEFFECTSLOTI
qalGenAuxiliaryEffectSlots = None #LPALGENAUXILIARYEFFECTSLOTS
qalDeleteAuxiliaryEffectSlots = None #LPALDELETEAUXILIARYEFFECTSLOTS
qalDeleteEffects = None #LPALDELETEEFFECTS

def _string(p)->str:

	# Q2PORT: a const char * from OpenAL as a str (NULL is None)
	if not p:
		return None
	return ctypes.string_at(p).decode("utf-8", "replace")

"""
 * Gives information over the OpenAL implementation and
 * its state, showing extensions or not.
"""
def QAL_SoundInfo(show_ext: bool): #qboolean

	Printf_Ext = clientserver.Com_Printf if show_ext else clientserver.Com_DPrintf #void (*)(const char *msg, ...)

	clientserver.Com_Printf("OpenAL features:\n")
	clientserver.Com_Printf("AL_VENDOR: {}\n".format(_string(qalGetString(qal_h.AL_VENDOR))))
	clientserver.Com_Printf("AL_RENDERER: {}\n".format(_string(qalGetString(qal_h.AL_RENDERER))))
	clientserver.Com_Printf("AL_VERSION: {}\n".format(_string(qalGetString(qal_h.AL_VERSION))))
	Printf_Ext("AL_EXTENSIONS: {}\n".format(_string(qalGetString(qal_h.AL_EXTENSIONS))))
	clientserver.Com_Printf("AL_EXTENSIONS number: {}\n".format(shared_c.Word_Count(_string(qalGetString(qal_h.AL_EXTENSIONS)))))

	if qalcIsExtensionPresent(None, b"ALC_ENUMERATE_ALL_EXT"):

		devs = qalcGetString(None, qal_h.ALC_ALL_DEVICES_SPECIFIER) #const char *

		clientserver.Com_Printf("\nAvailable OpenAL devices:\n")

		if devs is None:

			clientserver.Com_Printf("- No devices found. Depending on your\n")
			clientserver.Com_Printf("  platform this may be expected and\n")
			clientserver.Com_Printf("  doesn't indicate a problem!\n")

		else:

			while devs and ctypes.string_at(devs, 1) != b"\0": # while (devs && *devs)

				dev = ctypes.string_at(devs)
				clientserver.Com_Printf("- {}\n".format(dev.decode("utf-8", "replace")))
				devs += len(dev) + 1

	if qalcIsExtensionPresent(None, b"ALC_ENUMERATE_ALL_EXT"):

		devs = _string(qalcGetString(device, qal_h.ALC_DEVICE_SPECIFIER)) #const char *

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

		connected = ALCint() #ALCint
		qalcGetIntegerv(device, qal_h.ALC_CONNECTED, 1, ctypes.byref(connected))

		if not connected.value:

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

			cmdparser.Cbuf_AddText("snd_restart\n")
			discoCount = 0
			return False

_management = ["CreateContext", "MakeContextCurrent", "ProcessContext", "SuspendContext",
	"DestroyContext", "GetCurrentContext", "GetContextsDevice", "OpenDevice", "CloseDevice",
	"GetError", "IsExtensionPresent", "GetProcAddress", "GetEnumValue", "GetString",
	"GetIntegerv", "CaptureOpenDevice", "CaptureCloseDevice", "CaptureStart", "CaptureStop",
	"CaptureSamples"] # Q2PORT: the qalc* names, in the C's order

_api = ["Enable", "Disable", "IsEnabled", "GetString", "GetBooleanv", "GetIntegerv",
	"GetFloatv", "GetDoublev", "GetBoolean", "GetInteger", "GetFloat", "GetDouble", "GetError",
	"IsExtensionPresent", "GetProcAddress", "GetEnumValue", "Listenerf", "Listener3f",
	"Listenerfv", "Listeneri", "Listener3i", "Listeneriv", "GetListenerf", "GetListener3f",
	"GetListenerfv", "GetListeneri", "GetListener3i", "GetListeneriv", "GenSources",
	"DeleteSources", "IsSource", "Sourcef", "Source3f", "Sourcefv", "Sourcei", "Source3i",
	"Sourceiv", "GetSourcef", "GetSource3f", "GetSourcefv", "GetSourcei", "GetSource3i",
	"GetSourceiv", "SourcePlayv", "SourceStopv", "SourceRewindv", "SourcePausev", "SourcePlay",
	"SourceStop", "SourceRewind", "SourcePause", "SourceQueueBuffers", "SourceUnqueueBuffers",
	"GenBuffers", "DeleteBuffers", "IsBuffer", "BufferData", "Bufferf", "Buffer3f", "Bufferfv",
	"Bufferi", "Buffer3i", "Bufferiv", "GetBufferf", "GetBuffer3f", "GetBufferfv", "GetBufferi",
	"GetBuffer3i", "GetBufferiv", "DopplerFactor", "DopplerVelocity", "SpeedOfSound",
	"DistanceModel"] # Q2PORT: the qal* names, in the C's order

_efx = ["GenFilters", "Filteri", "Filterf", "DeleteFilters", "AuxiliaryEffectSloti",
	"GenEffects", "GenAuxiliaryEffectSlots", "Effectf", "Effecti", "Effectfv",
	"DeleteAuxiliaryEffectSlots", "DeleteEffects"] # Q2PORT: the EFX qal* names, in the C's order

"""
 * Shuts OpenAL down, frees all context and
 * device handles and unloads the shared lib.
"""
def QAL_Shutdown(): #void

	global context, device, handle

	if context:

		qalcMakeContextCurrent( None )
		qalcDestroyContext( context )
		context = None

	if device:

		qalcCloseDevice( device )
		device = None

	# Disconnect function pointers used
	# for OpenAL management calls
	# Q2PORT: qalcCreateContext = NULL; ... for each of them
	for name in _management:
		globals()["qalc" + name] = None

	# Disconnect OpenAL
	# function pointers
	# Q2PORT: qalEnable = NULL; ... for each of them, and the C's four filter ones
	for name in _api + ["GenFilters", "Filteri", "Filterf", "DeleteFilters"]:
		globals()["qal" + name] = None

	if handle:

		# Unload the shared lib
		system.Sys_FreeLibrary(handle)
		handle = None

def ALSYMBOL(handle, sym: str):

	# #define ALSYMBOL(handle, sym) Sys_GetProcAddress(handle, #sym)
	func = system.Sys_GetProcAddress(handle, sym)
	if func is not None:
		func.restype, func.argtypes = _prototypes[sym] # Q2PORT: the LPAL... type the C assigns it to
	return func

def _qalGetProcAddress(name: str):

	# (LPAL...)qalGetProcAddress(name), Q2PORT: the pointer as a ctypes function
	address = qalGetProcAddress(name.encode("ascii"))
	if not address:
		return None
	restype, argtypes = _prototypes[name]
	return ctypes.CFUNCTYPE(restype, *argtypes)(address)

"""
 * Loads the OpenAL shared lib, creates
 * a context and device handle.
"""
def QAL_Init()->bool: #void (returns qboolean)

	global al_device, al_driver, handle, device, context, hasAlcExtDisconnect

	al_device = cvar.Cvar_Get("al_device", "", shared.CVAR_ARCHIVE)

	# DEFAULT_OPENAL_DRIVER is defined at compile time via the compiler
	al_driver = cvar.Cvar_Get("al_driver", DEFAULT_OPENAL_DRIVER, shared.CVAR_ARCHIVE)

	if ".." in al_driver.string or ':' in al_driver.string or '/' in al_driver.string or '\\' in al_driver.string:

		clientserver.Com_Printf("al_driver must not contain '..', ':', '/' or '\\': {}\n".format(al_driver.string))
		return False

	# Load the library
	clientserver.Com_Printf("Loading library: {}\n".format(al_driver.string))

	_entry, handle = system.Sys_LoadLibrary(al_driver.string, None)

	if not handle:

		clientserver.Com_Printf("Loading {} failed! Disabling OpenAL.\n".format(al_driver.string))
		return False

	# Connect function pointers to management functions
	# Q2PORT: qalcCreateContext = ALSYMBOL(handle, alcCreateContext); ... for each of them
	for name in _management:
		globals()["qalc" + name] = ALSYMBOL(handle, "alc" + name)

	# Connect function pointers to
	# to OpenAL API functions
	# Q2PORT: qalEnable = ALSYMBOL(handle, alEnable); ... for each of them
	for name in _api:
		globals()["qal" + name] = ALSYMBOL(handle, "al" + name)

	# Open the OpenAL device
	clientserver.Com_Printf("...opening OpenAL device: ")

	device = qalcOpenDevice(al_device.string.encode("utf-8") if al_device.string else None)

	if not device:

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	clientserver.Com_Printf("ok\n")

	# Create the OpenAL context
	clientserver.Com_Printf("...creating OpenAL context: ")

	context = qalcCreateContext(device, None)
	if not context:

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	clientserver.Com_Printf("ok\n")

	# Set the created context as current context
	clientserver.Com_Printf("...making context current: ")

	if not qalcMakeContextCurrent(context):

		clientserver.Com_DPrintf("failed\n")
		QAL_Shutdown()
		return False

	if qalcIsExtensionPresent(device, b"ALC_EXT_EFX") != qal_h.AL_FALSE:

		# Q2PORT: qalGenFilters = (LPALGENFILTERS)qalGetProcAddress("alGenFilters"); ... for each of them
		for name in _efx:
			globals()["qal" + name] = _qalGetProcAddress("al" + name)

	else:

		# Q2PORT: qalGenFilters = NULL; ... for each of them
		for name in _efx:
			globals()["qal" + name] = None

	clientserver.Com_Printf("ok\n")

	# Print OpenAL information
	clientserver.Com_Printf("\n")
	QAL_SoundInfo(False)
	clientserver.Com_Printf("\n")

	#  Check extensions
	if qalcIsExtensionPresent(device, b"ALC_EXT_disconnect") != qal_h.AL_FALSE:

		hasAlcExtDisconnect = True

	return True

#endif /* USE_OPENAL */
