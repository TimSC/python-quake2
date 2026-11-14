"""
Copyright (C) 2010 Yamagi Burmeister
Copyright (C) 1997-2001 Id Software, Inc.

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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""
from __future__ import annotations

from backends import sdl
from common import cvar
from common import clientserver
from common.header import common as common_h
from common.header import shared
from client.vid import vid
from client.vid.icon import q2icon64 as q2icon64_h
# Q2PORT: the C glimp calls the active renderer via the re.* / ri.* globals, not a fixed
# module. The port resolves the active renderer (gl1 or gl3) lazily, per vid_renderer.
def _renderer():

	from client.refresh import ref_dispatch
	return ref_dispatch.get_renderer()
"""
#include "../../common/header/common.h"
#include "header/ref.h"

#include <SDL2/SDL.h>
#include <SDL2/SDL_video.h>

Q2PORT: SDL is backends/sdl.py, the SDL calls done with pyglet
"""
glimp_refreshRate = -1.0 #float

# glw_linux.h; used by qgl_linux's gl logging
class glwstate_t(object):

	def __init__(self):

		self.OpenGLLib = None # void *, instance of OpenGL library
		self.log_fp = None # FILE *

glw_state = glwstate_t()

vid_displayrefreshrate = None #static cvar_t *
vid_displayindex = None #static cvar_t *
vid_highdpiaware = None #static cvar_t *
vid_rate = None #static cvar_t *

last_flags = 0 #static int
last_display = 0 #static int
last_position_x = sdl.SDL_WINDOWPOS_UNDEFINED #static int
last_position_y = sdl.SDL_WINDOWPOS_UNDEFINED #static int
window = None #static SDL_Window*
initSuccessful = False #static qboolean
displayindices = None #static char **
num_displays = 0 #static int

"""
 * Resets the display index Cvar if out of bounds
"""
def ClampDisplayIndexCvar(): #void

	if not vid_displayindex:

		# uninitialized render?
		return

	if vid_displayindex.value < 0 or vid_displayindex.value >= num_displays:

		cvar.Cvar_SetValue("vid_displayindex", 0)

def ClearDisplayIndices(): #void

	global displayindices

	if displayindices:

		# python frees the strings
		displayindices = None

def CreateSDLWindow(flags: int, w: int, h: int)->bool: #int, int, int (returns qboolean)

	global window, last_display, last_position_x, last_position_y

	if sdl.SDL_WINDOWPOS_ISUNDEFINED(last_position_x) or sdl.SDL_WINDOWPOS_ISUNDEFINED(last_position_y) or last_position_x < 0 or last_position_y < 24:

		last_position_x = last_position_y = sdl.SDL_WINDOWPOS_UNDEFINED_DISPLAY(int(vid_displayindex.value))

	# Force the window to minimize when focus is lost. This was the
	# default behavior until SDL 2.0.12 and changed with 2.0.14.
	# The windows staying maximized has some odd implications for
	# window ordering under Windows and some X11 window managers
	# like kwin. See:
	#  * https://github.com/libsdl-org/SDL/issues/4039
	#  * https://github.com/libsdl-org/SDL/issues/3656
	sdl.SDL_SetHint(sdl.SDL_HINT_VIDEO_MINIMIZE_ON_FOCUS_LOSS, "1")

	window = sdl.SDL_CreateWindow("{}".format(common_h.APPNAME), last_position_x, last_position_y, w, h, flags) # Q2PORT: APPNAME, the C has "Yamagi Quake II"

	if window:

		# save current display as default
		last_display = sdl.SDL_GetWindowDisplayIndex(window)
		last_position_x, last_position_y = sdl.SDL_GetWindowPosition(window)

		# Check if we're really in the requested diplay mode. There is
		# (or was) an SDL bug were SDL switched into the wrong mode
		# without giving an error code. See the bug report for details:
		# https://bugzilla.libsdl.org/show_bug.cgi?id=4700
		real_mode = None #SDL_DisplayMode

		if (flags & (sdl.SDL_WINDOW_FULLSCREEN | sdl.SDL_WINDOW_FULLSCREEN_DESKTOP)) == sdl.SDL_WINDOW_FULLSCREEN:

			ret, real_mode = sdl.SDL_GetWindowDisplayMode(window)
			if ret != 0:

				sdl.SDL_DestroyWindow(window)
				window = None

				clientserver.Com_Printf("Can't get display mode: {}\n".format(sdl.SDL_GetError()))

				return False

		# SDL_WINDOW_FULLSCREEN_DESKTOP implies SDL_WINDOW_FULLSCREEN!
		if (((flags & (sdl.SDL_WINDOW_FULLSCREEN | sdl.SDL_WINDOW_FULLSCREEN_DESKTOP)) == sdl.SDL_WINDOW_FULLSCREEN)
				and ((real_mode.w != w) or (real_mode.h != h))):

			clientserver.Com_Printf("Current display mode isn't requested display mode\n")
			clientserver.Com_Printf("Likely SDL bug #4700, trying to work around it\n")

			# Mkay, try to hack around that.
			wanted_mode = sdl.SDL_DisplayMode()

			wanted_mode.w = w
			wanted_mode.h = h

			if sdl.SDL_SetWindowDisplayMode(window, wanted_mode) != 0:

				sdl.SDL_DestroyWindow(window)
				window = None

				clientserver.Com_Printf("Can't force resolution to {}x{}: {}\n".format(w, h, sdl.SDL_GetError()))

				return False

			# The SDL doku says, that SDL_SetWindowSize() shouldn't be
			# used on fullscreen windows. But at least in my test with
			# SDL 2.0.9 the subsequent SDL_GetWindowDisplayMode() fails
			# if I don't call it.
			sdl.SDL_SetWindowSize(window, wanted_mode.w, wanted_mode.h)

			ret, real_mode = sdl.SDL_GetWindowDisplayMode(window)
			if ret != 0:

				sdl.SDL_DestroyWindow(window)
				window = None

				clientserver.Com_Printf("Can't get display mode: {}\n".format(sdl.SDL_GetError()))

				return False

			if (real_mode.w != w) or (real_mode.h != h):

				sdl.SDL_DestroyWindow(window)
				window = None

				clientserver.Com_Printf("Still in wrong display mode: {}x{} instead of {}x{}\n".format(real_mode.w, real_mode.h, w, h))

				return False

		# Normally SDL stays at desktop refresh rate or chooses something
		# sane. Some player may want to override that.
		#
		# Reminder: SDL_WINDOW_FULLSCREEN_DESKTOP implies SDL_WINDOW_FULLSCREEN!
		if (flags & (sdl.SDL_WINDOW_FULLSCREEN | sdl.SDL_WINDOW_FULLSCREEN_DESKTOP)) == sdl.SDL_WINDOW_FULLSCREEN:

			if vid_rate.value > 0:

				#SDL_DisplayMode closest_mode;
				requested_mode = sdl.SDL_DisplayMode(real_mode.w, real_mode.h, real_mode.refresh_rate)

				requested_mode.refresh_rate = int(vid_rate.value)

				closest_mode = sdl.SDL_GetClosestDisplayMode(last_display, requested_mode)
				if closest_mode is None:

					clientserver.Com_Printf("SDL was unable to find a mode close to {}x{}@{}\n".format(w, h, requested_mode.refresh_rate))
					cvar.Cvar_SetValue("vid_rate", -1)

				else:

					clientserver.Com_Printf("User requested {}x{}@{}, setting closest mode {}x{}@{}\n".format(
							w, h, requested_mode.refresh_rate, w, h, closest_mode.refresh_rate))

					if sdl.SDL_SetWindowDisplayMode(window, closest_mode) != 0:

						clientserver.Com_Printf("Couldn't switch to mode {}x{}@{}, staying at current mode\n".format(
								w, h, closest_mode.refresh_rate))
						cvar.Cvar_SetValue("vid_rate", -1)

					else:

						cvar.Cvar_SetValue("vid_rate", closest_mode.refresh_rate)

	else:

		clientserver.Com_Printf("Creating window failed: {}\n".format(sdl.SDL_GetError()))
		return False

	return True

def GetFullscreenType()->int: #void (returns int)

	if sdl.SDL_GetWindowFlags(window) & sdl.SDL_WINDOW_FULLSCREEN_DESKTOP:

		return 2

	elif sdl.SDL_GetWindowFlags(window) & sdl.SDL_WINDOW_FULLSCREEN:

		return 1

	else:

		return 0

def GetWindowSize()->tuple: #int*, int* (returns qboolean, *w, *h)

	if window is None:

		return False, 0, 0

	ret, m = sdl.SDL_GetWindowDisplayMode(window)
	if ret != 0:

		clientserver.Com_Printf("Can't get Displaymode: {}\n".format(sdl.SDL_GetError()))

		return False, 0, 0

	return True, m.w, m.h

def InitDisplayIndices(): #void

	global displayindices

	displayindices = [] # malloc((num_displays + 1) * sizeof(char *))

	for i in range(num_displays):

		# There are a maximum of 12 digits in 32 bit int + 1 for the NULL terminator.
		displayindices.append("{}".format(i))

	# The last entry is NULL to indicate the list of strings ends.
	displayindices.append(None)

"""
 * Lists all available display modes.
"""
def PrintDisplayModes(): #void

	curdisplay = sdl.SDL_GetWindowDisplayIndex(window) if window else 0

	# On X11 (at least for me)
	# curdisplay is always -1.
	# DG: probably because window was NULL?
	if curdisplay < 0:
		curdisplay = 0

	nummodes = sdl.SDL_GetNumDisplayModes(curdisplay)

	if nummodes < 1:

		clientserver.Com_Printf("Can't get display modes: {}\n".format(sdl.SDL_GetError()))
		return

	for i in range(nummodes):

		ret, mode = sdl.SDL_GetDisplayMode(curdisplay, i)
		if ret != 0:

			clientserver.Com_Printf("Can't get display mode: {}\n".format(sdl.SDL_GetError()))
			return

		clientserver.Com_Printf(" - Mode {:2}: {}x{}@{}\n".format(i, mode.w, mode.h, mode.refresh_rate))

"""
 * Sets the window icon
"""
def SetSDLIcon(): #void

	#include "icon/q2icon64.h" // 64x64 32 Bit
	q2icon64 = q2icon64_h.q2icon64

	# these masks are needed to tell SDL_CreateRGBSurface(From)
	# to assume the data it gets is byte-wise RGB(A) data
	#Uint32 rmask, gmask, bmask, amask;

	if sdl.SDL_BYTEORDER == sdl.SDL_BIG_ENDIAN:

		shift = 8 if q2icon64.bytes_per_pixel == 3 else 0
		rmask = 0xff000000 >> shift
		gmask = 0x00ff0000 >> shift
		bmask = 0x0000ff00 >> shift
		amask = 0x000000ff >> shift

	else: # little endian, like x86

		rmask = 0x000000ff
		gmask = 0x0000ff00
		bmask = 0x00ff0000
		amask = 0 if q2icon64.bytes_per_pixel == 3 else 0xff000000

	icon = sdl.SDL_CreateRGBSurfaceFrom(q2icon64.pixel_data, q2icon64.width,
		q2icon64.height, q2icon64.bytes_per_pixel*8, q2icon64.bytes_per_pixel*q2icon64.width,
		rmask, gmask, bmask, amask) #SDL_Surface*
	sdl.SDL_SetWindowIcon(window, icon)
	sdl.SDL_FreeSurface(icon)

"""
// FIXME: We need a header for this.
// Maybe we could put it in vid.h.
void GLimp_GrabInput(qboolean grab);
"""

"""
 * Shuts the SDL render backend down
"""
def ShutdownGraphics(): #void

	global window, last_display, last_position_x, last_position_y, glimp_refreshRate, initSuccessful

	ClampDisplayIndexCvar()

	if window:

		# save current display as default
		last_display = sdl.SDL_GetWindowDisplayIndex(window)

		# or if current display isn't the desired default
		if last_display != vid_displayindex.value:
			last_position_x = last_position_y = sdl.SDL_WINDOWPOS_UNDEFINED
			last_display = int(vid_displayindex.value)
		else:
			last_position_x, last_position_y = sdl.SDL_GetWindowPosition(window)

		# cleanly ungrab input (needs window)
		GLimp_GrabInput(False)
		sdl.SDL_DestroyWindow(window)

		window = None

	# make sure that after vid_restart the refreshrate will be queried from SDL2 again.
	glimp_refreshRate = -1

	initSuccessful = False # not initialized anymore
# --------

"""
 * Initializes the SDL video subsystem. Must
 * be called before anything else.
"""
def GLimp_Init()->bool: #void (returns qboolean)

	global vid_displayrefreshrate, vid_displayindex, vid_highdpiaware, vid_rate
	global num_displays

	vid_displayrefreshrate = cvar.Cvar_Get("vid_displayrefreshrate", "-1", shared.CVAR_ARCHIVE)
	vid_displayindex = cvar.Cvar_Get("vid_displayindex", "0", shared.CVAR_ARCHIVE)
	vid_highdpiaware = cvar.Cvar_Get("vid_highdpiaware", "0", shared.CVAR_ARCHIVE)
	vid_rate = cvar.Cvar_Get("vid_rate", "-1", shared.CVAR_ARCHIVE)

	if not sdl.SDL_WasInit(sdl.SDL_INIT_VIDEO):

		if sdl.SDL_Init(sdl.SDL_INIT_VIDEO) == -1:

			clientserver.Com_Printf("Couldn't init SDL video: {}.\n".format(sdl.SDL_GetError()))

			return False

		version = sdl.SDL_GetVersion()
		clientserver.Com_Printf("-------- vid initialization --------\n")
		clientserver.Com_Printf("pyglet version is: {}.{}.{}\n".format(*version)) # Q2PORT: pyglet stands in for SDL
		clientserver.Com_Printf("SDL video driver is \"{}\".\n".format(sdl.SDL_GetCurrentVideoDriver()))

		num_displays = sdl.SDL_GetNumVideoDisplays()
		InitDisplayIndices()
		ClampDisplayIndexCvar()
		clientserver.Com_Printf("SDL display modes:\n")

		PrintDisplayModes()
		clientserver.Com_Printf("------------------------------------\n\n")

	return True

"""
 * Shuts the SDL video subsystem down. Must
 * be called after evrything's finished and
 * clean up.
"""
def GLimp_Shutdown(): #void

	ShutdownGraphics()

	# SDL_INIT_VIDEO implies SDL_INIT_EVENTS
	subsystems = sdl.SDL_INIT_VIDEO | sdl.SDL_INIT_EVENTS #const Uint32
	if sdl.SDL_WasInit(sdl.SDL_INIT_EVERYTHING) == subsystems:

		sdl.SDL_Quit()

	else:

		sdl.SDL_QuitSubSystem(sdl.SDL_INIT_VIDEO)

	ClearDisplayIndices()

"""
 * Determine if we want to be high dpi aware. If
 * we are we must scale ourself. If we are not the
 * compositor might scale us.
"""
def Glimp_DetermineHighDPISupport(flags: int)->int: #int (returns int)

	#if SDL_VERSION_ATLEAST(2, 26, 0)
	# Make sure that high dpi is never set when we don't want it.
	flags &= ~sdl.SDL_WINDOW_ALLOW_HIGHDPI

	if vid_highdpiaware.value == 0:

		return flags

	# Handle high dpi awareness based on the render backend.
	# SDL doesn't support high dpi awareness for all backends
	# and the quality and behavior differs between them.
	if sdl.SDL_GetCurrentVideoDriver() == "wayland":

		flags |= sdl.SDL_WINDOW_ALLOW_HIGHDPI
	#endif

	return flags

"""
 * (Re)initializes the actual window.
"""
def GLimp_InitGraphics(fullscreen: int, pwidth: int, pheight: int)->bool: #int, int *, int * (returns qboolean)

	global window, last_flags, initSuccessful

	"""
	int flags;
	int curWidth, curHeight;
	"""
	width = pwidth
	height = pheight
	fs_flag = 0 #unsigned int

	if fullscreen == 1:

		fs_flag = sdl.SDL_WINDOW_FULLSCREEN

	elif fullscreen == 2:

		fs_flag = sdl.SDL_WINDOW_FULLSCREEN_DESKTOP

	# Only do this if we already have a working window and a fully
	# initialized rendering backend GLimp_InitGraphics() is also
	# called when recovering if creating GL context fails or the
	# one we got is unusable.
	if initSuccessful:

		ok, curWidth, curHeight = GetWindowSize()

		if ok and (curWidth == width) and (curHeight == height):

			# If we want fullscreen, but aren't
			if GetFullscreenType():

				sdl.SDL_SetWindowFullscreen(window, fs_flag)
				cvar.Cvar_SetValue("vid_fullscreen", fullscreen)

			# Are we now?
			if GetFullscreenType():

				return True

	# Is the surface used?
	if window:

		vid.re.shutdown_context()
		ShutdownGraphics()

		window = None

	if last_flags != -1 and (last_flags & sdl.SDL_WINDOW_OPENGL):

		# Reset SDL.
		sdl.SDL_GL_ResetAttributes()

	# Let renderer prepare things (set OpenGL attributes).
	# FIXME: This is no longer necessary, the renderer
	# could and should pass the flags when calling this
	# function.
	flags = vid.re.prepare_for_window()

	if flags == -1:

		# It's PrepareForWindow() job to log an error
		return False

	if fs_flag:

		flags |= fs_flag

	# Check for high dpi support.
	flags = Glimp_DetermineHighDPISupport(flags)

	# Mkay, now the hard work. Let's create the window.
	gl_msaa_samples = cvar.Cvar_Get("r_msaa_samples", "0", shared.CVAR_ARCHIVE)

	while True:

		if not CreateSDLWindow(flags, width, height):

			if (flags & sdl.SDL_WINDOW_OPENGL) and gl_msaa_samples.value:

				msaa_samples = int(gl_msaa_samples.value)

				if msaa_samples > 0:

					msaa_samples //= 2

				clientserver.Com_Printf("SDL SetVideoMode failed: {}\n".format(sdl.SDL_GetError()))
				clientserver.Com_Printf("Reverting to {} r_mode {} ({}x{}) with {}x MSAA.\n".format(
					        "fullscreen" if (flags & fs_flag) else "windowed",
					        int(cvar.Cvar_VariableValue("r_mode")), width, height,
					        msaa_samples))

				# Try to recover
				cvar.Cvar_SetValue("r_msaa_samples", msaa_samples)

				sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS,
					1 if msaa_samples > 0 else 0)
				sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES,
					msaa_samples)

			elif width != 640 or height != 480 or (flags & fs_flag):

				clientserver.Com_Printf("SDL SetVideoMode failed: {}\n".format(sdl.SDL_GetError()))
				clientserver.Com_Printf("Reverting to windowed r_mode 4 (640x480).\n")

				# Try to recover
				cvar.Cvar_SetValue("r_mode", 4)
				cvar.Cvar_SetValue("vid_fullscreen", 0)
				cvar.Cvar_SetValue("vid_rate", -1)

				fullscreen = 0
				pwidth = width = 640
				pheight = height = 480
				flags &= ~fs_flag

			else:

				clientserver.Com_Printf("Failed to revert to r_mode 4. Will try another render backend...\n")
				return False

		else:

			break

	last_flags = flags

	# Now that we've got a working window print its mode.
	curdisplay = sdl.SDL_GetWindowDisplayIndex(window)

	if curdisplay < 0:
		curdisplay = 0

	ret, mode = sdl.SDL_GetCurrentDisplayMode(curdisplay)
	if ret != 0:

		clientserver.Com_Printf("Can't get current display mode: {}\n".format(sdl.SDL_GetError()))

	else:

		clientserver.Com_Printf("Real display mode: {}x{}@{}\n".format(mode.w, mode.h, mode.refresh_rate))

	# Initialize rendering context.
	if not vid.re.init_context(window):

		# InitContext() should have logged an error.
		return False

	# We need the actual drawable size for things like the
	# console, the menus, etc. This might be different to
	# the resolution due to high dpi awareness.
	#
	# The fullscreen window is special. We want it to fill
	# the screen when native resolution is requestes, all
	# other cases should look broken.
	if flags & sdl.SDL_WINDOW_ALLOW_HIGHDPI:

		if fullscreen != 2:

			vid.viddef.width, vid.viddef.height = vid.re.get_drawable_size()

		else:

			r_mode = cvar.Cvar_Get("r_mode", "4", 0)

			if r_mode.value == -2:

				vid.viddef.width, vid.viddef.height = vid.re.get_drawable_size()

			else:

				# User likes it broken.
				vid.viddef.width = pwidth
				vid.viddef.height = pheight

	else:

		# Another bug or design failure in SDL: When we are
		# not high dpi aware the drawable size returned by
		# SDL may be too small. It seems like the window
		# decoration are taken into account when they shouldn't.
		# It can be seen when creating a fullscreen window.
		#
		# Work around that by always using the resolution and
		# not the drawable size when we are not high dpi aware.
		vid.viddef.width = pwidth
		vid.viddef.height = pheight

	clientserver.Com_Printf("Drawable size: {}x{}\n".format(vid.viddef.width, vid.viddef.height))

	# Set the window icon - For SDL2, this must be done after creating the window
	SetSDLIcon()

	# No cursor
	sdl.SDL_ShowCursor(0)

	initSuccessful = True

	# Q2PORT: let the sound and input subsystems know about the new window
	_renderer().ri.Vid_NewWindow (width, height)

	return True

"""
 * Shuts the window down.
"""
def GLimp_ShutdownGraphics(): #void

	sdl.SDL_GL_ResetAttributes()
	ShutdownGraphics()

"""
 * (Un)grab Input
"""
seen_error = False #static qboolean, GLimp_GrabInput

def GLimp_GrabInput(grab: bool): #qboolean

	global seen_error

	if window is not None:

		sdl.SDL_SetWindowGrab(window, True if grab else False)

	if sdl.SDL_SetRelativeMouseMode(True if grab else False) < 0 and not seen_error:

		seen_error = True
		clientserver.Com_Printf("WARNING: Setting Relative Mousemode failed, reason: {}\n".format(sdl.SDL_GetError()))
		clientserver.Com_Printf("         You should probably update to SDL 2.0.3 or newer!\n")

"""
 * Returns the current display refresh rate.
"""
def GLimp_GetRefreshRate()->float: #void (returns float)

	global glimp_refreshRate

	if vid_displayrefreshrate.value > -1 or \
			vid_displayrefreshrate.modified:

		glimp_refreshRate = vid_displayrefreshrate.value
		vid_displayrefreshrate.modified = False

	elif glimp_refreshRate == -1:

		#SDL_DisplayMode mode;

		i = sdl.SDL_GetWindowDisplayIndex(window) if window else -1 # Q2PORT: SDL returns -1 for a NULL window

		if i >= 0:

			ret, mode = sdl.SDL_GetCurrentDisplayMode(i)
			if ret == 0:

				glimp_refreshRate = mode.refresh_rate

		# Something went wrong, use default.
		if glimp_refreshRate <= 0:

			glimp_refreshRate = 60

	return glimp_refreshRate

"""
 * Detect current desktop mode
"""
def GLimp_GetDesktopMode()->tuple: #int *, int * (returns qboolean, *pwidth, *pheight)

	global last_display, last_position_x, last_position_y

	# Declare display mode structure to be filled in.
	#SDL_DisplayMode mode;

	if window:

		# save current display as default
		last_display = sdl.SDL_GetWindowDisplayIndex(window)
		last_position_x, last_position_y = sdl.SDL_GetWindowPosition(window)

	if last_display < 0:

		# In case of error...
		clientserver.Com_Printf("Can't detect current desktop.\n")
		last_display = 0

	# We can't get desktop where we start, so use first desktop
	ret, mode = sdl.SDL_GetCurrentDisplayMode(last_display)
	if ret != 0:

		# In case of error...
		clientserver.Com_Printf("Can't detect default desktop mode: {}\n".format(
				sdl.SDL_GetError()))
		return False, 0, 0

	return True, mode.w, mode.h

def GLimp_GetDisplayIndices(): #void (returns const char**)

	return displayindices

def GLimp_GetNumVideoDisplays()->int: #void (returns int)

	return num_displays

def GLimp_GetWindowDisplayIndex()->int: #void (returns int)

	return last_display

def GLimp_GetFrameworkVersion()->int: #void (returns int)

	#SDL_version ver;
	#SDL_VERSION(&ver);

	return sdl.SDL_MAJOR_VERSION
