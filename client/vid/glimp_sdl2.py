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

import pygame
from common import cvar
from common import clientserver
from common.header import common as common_h
from common.header import shared
from client.vid import vid
from client.refresh.gl1 import gl1_main as gl_rmain
"""
#include "../../common/header/common.h"
#include "header/ref.h"

#include <SDL2/SDL.h>
#include <SDL2/SDL_video.h>

# Q2PORT: the platform layer is pygame; the SDL window functions are done with the
# pygame.display functions, marked as they are
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
last_position_x = None #static int, SDL_WINDOWPOS_UNDEFINED
last_position_y = None #static int, SDL_WINDOWPOS_UNDEFINED
window = None #static SDL_Window *
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

	if displayindices:

		# python frees the strings
		displayindices.clear()

"""
 * Q2PORT: the C's CreateSDLWindow; pygame creates the window and GL context in place of
 * SDL_CreateWindow, and switches the screen mode for fullscreen in place of the
 * SDL display mode functions
"""
def CreateSDLWindow(flags: int, w: int, h: int)->bool: #int, int, int (returns qboolean)

	global window, last_display, last_position_x, last_position_y

	# the C checks the last window position and display index here; the port has one
	# display and lets the window manager place the window
	if (last_position_x is None) or (last_position_y is None):

		last_position_x = last_position_y = None # SDL_WINDOWPOS_UNDEFINED_DISPLAY(vid_displayindex->value)

	# SDL_SetHint(SDL_HINT_VIDEO_MINIMIZE_ON_FOCUS_LOSS, "1") - the window manager does this

	window = None
	pyflags = pygame.OPENGL | pygame.DOUBLEBUF
	if flags & 0x10000: # SDL_WINDOW_FULLSCREEN
		pyflags |= pygame.FULLSCREEN

	try:
		window = pygame.display.set_mode((w, h), pyflags, position=(last_position_x, last_position_y) if last_position_x is not None else None)
	except pygame.error as err:

		clientserver.Com_Printf("Creating window failed: {}\n".format(err))
		return False

	if window:

		# save current display as default
		last_display = 0 # SDL_GetWindowDisplayIndex(window)
		last_position_x, last_position_y = (0, 0) # SDL_GetWindowPosition(window, ...)

		# SDL bug #4700 work around: the port's fullscreen always lands in the
		# requested mode, so there is nothing to check here

		# normally SDL stays at desktop refresh rate; the vid_rate cvar
		# (SDL_GetClosestDisplayMode and SDL_SetWindowDisplayMode) is not done, Q2PORT
		if flags & 0x10000: # SDL_WINDOW_FULLSCREEN

			if vid_rate.value > 0:

				clientserver.Com_Printf("User requested {}x{}@{}, staying at the desktop refresh rate\n".format(w, h, int(vid_rate.value)))
				cvar.Cvar_SetValue("vid_rate", -1)

	return True

def GetFullscreenType(): #void (returns int)

	if window is None:
		return 0

	return pygame.display.get_surface().get_flags() & pygame.FULLSCREEN and 2 or 0 # SDL_WINDOW_FULLSCREEN_DESKTOP implies SDL_WINDOW_FULLSCREEN

def GetWindowSize(): #int *, int * (returns qboolean, *w, *h)

	if window is None:
		return False, 0, 0

	# SDL_GetWindowDisplayMode
	info = pygame.display.Info()
	return True, info.current_w, info.current_h

def InitDisplayIndices(): #void

	global displayindices

	displayindices = [] # malloc((num_displays + 1) * sizeof(char *)), NULL terminated in the C

	for i in range(num_displays):

		# there are a maximum of 12 digits in 32 bit int
		displayindices.append("{}" .format(i))

"""
 * Lists all available display modes.
 """
def PrintDisplayModes(): #void

	curdisplay = last_display if window else 0

	# SDL_GetNumDisplayModes / SDL_GetDisplayMode
	for i, mode in enumerate(pygame.display.list_modes() or []):

		clientserver.Com_Printf(" - Mode {:2}: {}x{}@{}\n".format(i, mode[0], mode[1], 60))

"""
 * Sets the window icon
"""
def SetSDLIcon(): #void

	# Q2PORT: no window icon until one is loaded
	pass

"""
// FIXME: We need a header for this.
// Maybe we could put it in vid.h.
void GLimp_GrabInput(qboolean grab);
"""
def ShutdownGraphics(): #void

	global window, last_display, last_position_x, last_position_y, glimp_refreshRate, initSuccessful

	ClampDisplayIndexCvar()

	if window:

		# save current display as default
		last_display = 0 # SDL_GetWindowDisplayIndex(window)

		# or if current display isn't the desired default
		if last_display != vid_displayindex.value:
			last_position_x = last_position_y = None # SDL_WINDOWPOS_UNDEFINED
			last_display = int(vid_displayindex.value)
		else:
			last_position_x, last_position_y = (0, 0) # SDL_GetWindowPosition(window, ...)

		# cleanly ungrab input (needs window)
		GLimp_GrabInput(False)
		pygame.display.quit()

		window = None # SDL_DestroyWindow(window)

	# make sure that after vid_restart the refreshrate will be queried from SDL2 again.
	glimp_refreshRate = -1

	initSuccessful = False # not initialized anymore

"""
 * Initializes the SDL video subsystem. Must
 * be called before anything else.
"""
def GLimp_Init( hinstance=None, wndproc=None ): #void *, void * (returns qboolean)

	# id's GLimp_Init(hinstance, wndproc) signature is tolerated; the window itself is created by GLimp_InitGraphics from GLimp_SetMode

	global vid_displayrefreshrate, vid_displayindex, vid_highdpiaware, vid_rate
	global num_displays

	vid_displayrefreshrate = cvar.Cvar_Get("vid_displayrefreshrate", "-1", shared.CVAR_ARCHIVE)
	vid_displayindex = cvar.Cvar_Get("vid_displayindex", "0", shared.CVAR_ARCHIVE)
	vid_highdpiaware = cvar.Cvar_Get("vid_highdpiaware", "0", shared.CVAR_ARCHIVE)
	vid_rate = cvar.Cvar_Get("vid_rate", "-1", shared.CVAR_ARCHIVE)

	if not pygame.display.get_init():

		# SDL_Init(SDL_INIT_VIDEO)
		try:
			pygame.display.init()
		except pygame.error as err:
			clientserver.Com_Printf("Couldn't init the video: {}.\n".format(err))
			return False

		clientserver.Com_Printf("-------- vid initialization --------\n")
		clientserver.Com_Printf("pygame version is: {}\n".format(pygame.version.ver))
		clientserver.Com_Printf("SDL version is: {}\n".format(pygame.get_sdl_version()[1:]))
		clientserver.Com_Printf("SDL video driver is \"pygame\".\n")

		num_displays = 1 # SDL_GetNumVideoDisplays, Q2PORT: the port uses one display
		InitDisplayIndices()
		ClampDisplayIndexCvar()
		clientserver.Com_Printf("display modes:\n")

		PrintDisplayModes()
		clientserver.Com_Printf("------------------------------------\n\n")

	return True

"""
 * Shuts the SDL video subsystem down. Must
 * be called after evrything's finished and
 * clean up.
"""
def GLimp_Shutdown(): #void

	# the C does SDL_Quit here, but id's R_Shutdown calls GLimp_Shutdown on a renderer
	# restart, and pygame.quit() would kill the mixer (the C's id gl_glx.c only
	# destroyed the display); the process exits anyway, so no pygame.quit()
	ShutdownGraphics()
	ClearDisplayIndices()

"""
 * Determine if we want to be high dpi aware. If
 * we are we must scale ourself. If we are not the
 * compositor might scale us.
"""
def Glimp_DetermineHighDPISupport(flags: int)->int: #int (returns int)

	# SDL 2.26 SDL_WINDOW_ALLOW_HIGHDPI, Q2PORT: pygame does the scaling
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
	fs_flag = 0

	if fullscreen == 1:

		fs_flag = 0x10000 # SDL_WINDOW_FULLSCREEN
	elif fullscreen == 2:

		fs_flag = 0x20000 # SDL_WINDOW_FULLSCREEN_DESKTOP

	# only do this if we already have a working window and a fully
	# initialized rendering backend GLimp_InitGraphics() is also
	# called when recovering if creating GL context fails or the
	# one we got is unusable.
	if initSuccessful:

		ok, curWidth, curHeight = GetWindowSize()

		if ok and curWidth == width and curHeight == height:

			# if we want fullscreen, but aren't
			if GetFullscreenType():

				# SDL_SetWindowFullscreen(window, fs_flag)
				pass
			cvar.Cvar_SetValue("vid_fullscreen", fullscreen)

			# are we now?
			if GetFullscreenType():

				return True

	# is the surface used?
	if window:

		# re.ShutdownContext(); the old renderer has no ShutdownContext, Q2PORT
		ShutdownGraphics()

		window = None

	# SDL_GL_ResetAttributes when (last_flags & SDL_WINDOW_OPENGL), Q2PORT: nothing to reset

	# let the renderer prepare things (set OpenGL attributes); the C calls re.PrepareForWindow()
	# which the old renderer doesn't have, so the flags are the port's pygame flags
	flags = pygame.OPENGL | pygame.DOUBLEBUF

	if fs_flag:

		flags |= fs_flag

	# check for high dpi support.
	flags = Glimp_DetermineHighDPISupport(flags)

	# mkay, now the hard work. Let's create the window.
	gl_msaa_samples = cvar.Cvar_Get("r_msaa_samples", "0", shared.CVAR_ARCHIVE)

	while True:

		if not CreateSDLWindow(flags, width, height):

			if width != 640 or height != 480 or fs_flag:

				clientserver.Com_Printf("SetVideoMode failed\n")
				clientserver.Com_Printf("Reverting to windowed r_mode 4 (640x480).\n")

				# try to recover
				cvar.Cvar_SetValue("r_mode", 4)
				cvar.Cvar_SetValue("vid_fullscreen", 0)
				cvar.Cvar_SetValue("vid_rate", -1)

				fullscreen = 0
				width = 640
				height = 480
				flags &= ~fs_flag

			else:

				clientserver.Com_Printf("Failed to revert to r_mode 4. Will try another render backend...\n")
				return False

		else:

			break

	last_flags = flags

	# now that we've got a working window print its mode.
	# SDL_GetCurrentDisplayMode
	info = pygame.display.Info()
	clientserver.Com_Printf("Real display mode: {}x{}@{}\n".format(info.current_w, info.current_h, info.refresh_rate))

	# initialize rendering context.
	# re.InitContext(window); the old renderer makes the context in set_mode, Q2PORT

	# we need the actual drawable size for things like the
	# console, the menus, etc. This might be different to
	# the resolution due to high dpi awareness.
	# SDL_WINDOW_ALLOW_HIGHDPI is never set, Q2PORT
	vid.viddef.width = width
	vid.viddef.height = height

	clientserver.Com_Printf("Drawable size: {}x{}\n".format(vid.viddef.width, vid.viddef.height))

	# set the window icon - For SDL2, this must be done after creating the window
	SetSDLIcon()

	# no cursor
	pygame.mouse.set_visible(False) # SDL_ShowCursor(0)

	initSuccessful = True

	# let the sound and input subsystems know about the new window
	gl_rmain.ri.Vid_NewWindow (width, height)

	return True

"""
 * Shuts the window down.
"""
def GLimp_ShutdownGraphics(): #void

	# SDL_GL_ResetAttributes
	ShutdownGraphics()

"""
 * (Un)grab Input
"""
def GLimp_GrabInput(grab: bool): #qboolean

	global window

	seen_error = False #static qboolean
	if window is not None:

		# SDL_SetWindowGrab(window, grab)
		pass

	# SDL_SetRelativeMouseMode(grab)
	try:
		pygame.event.set_grab(bool(grab))
	except pygame.error as err:

		if not seen_error:

			seen_error = True
			clientserver.Com_Printf("WARNING: Setting Relative Mousemode failed, reason: {}\n".format(err))

"""
 * Returns the current display refresh rate.
"""
def GLimp_GetRefreshRate(): #void (returns float)

	global glimp_refreshRate

	if vid_displayrefreshrate.value > -1 or \
			vid_displayrefreshrate.modified:

		glimp_refreshRate = vid_displayrefreshrate.value
		vid_displayrefreshrate.modified = False
	elif glimp_refreshRate == -1:

		# SDL_GetCurrentDisplayMode
		info = pygame.display.Info()
		glimp_refreshRate = float(info.refresh_rate)

		# something went wrong, use default.
		if glimp_refreshRate <= 0:

			glimp_refreshRate = 60

	return glimp_refreshRate

"""
 * Detect current desktop mode
"""
def GLimp_GetDesktopMode(): #int *, int * (returns qboolean, *pwidth, *pheight)

	global last_display, last_position_x, last_position_y

	if window:

		# save current display as default
		last_display = 0 # SDL_GetWindowDisplayIndex(window)
		last_position_x, last_position_y = (0, 0) # SDL_GetWindowPosition(window, ...)

	if last_display < 0:

		# in case of error...
		clientserver.Com_Printf("Can't detect current desktop.\n")
		last_display = 0

	# SDL_GetCurrentDisplayMode
	info = pygame.display.Info()
	return True, info.current_w, info.current_h

def GLimp_GetDisplayIndices(): #void (returns const char **)

	return displayindices

def GLimp_GetNumVideoDisplays(): #void (returns int)

	return num_displays

def GLimp_GetWindowDisplayIndex(): #void (returns int)

	return last_display

def GLimp_GetFrameworkVersion(): #void (returns int)

	# SDL_GetVersion
	return 2 # Q2PORT: the framework is pygame on top of SDL2

"""
// =======================================================================
// Q2PORT: id's GLimp functions (linux/gl_glx.c, id's ref_gl talks to them), until
// the gl1 renderer (group 15) replaces the old ref_gl
// =======================================================================
"""
#
# GLimp_BeginFrame
#
def GLimp_BeginFrame( camera_seperation ): #float
	pass

"""
/*
** GLimp_EndFrame
** 
** Responsible for doing a swapbuffers and possibly for other stuff
** as yet to be determined.  Probably better not to make this a GLimp
** function and instead do a call to GLimp_SwapBuffers.
*/
"""
def GLimp_EndFrame ():

	#qglFlush();
	#qglXSwapBuffers(dpy, win);
	pygame.display.flip()

"""
/*
** GLimp_AppActivate
*/
"""
def GLimp_AppActivate( active ): #qboolean
	pass

"""
/*
** GLimp_SetMode
**
** This function is responsible for setting a new video mode.
*/
"""
def GLimp_SetMode( pwidth, pheight, mode, fullscreen ): # int *, int *, int, qboolean (returns rserr_t, *pwidth, *pheight)

	global initSuccessful
	# Q2PORT: id's GLimp_SetMode in place of the C's GLimp_InitGraphics; the old
	# renderer asks for a mode from vid_modes and a fullscreen flag, not a size

	#int width, height;
	width = None
	height = None

	gl_rmain.ri.Con_Printf( shared.PRINT_ALL, "Initializing OpenGL display\n")
	
	mode = int(mode)

	if fullscreen:
		gl_rmain.ri.Con_Printf (shared.PRINT_ALL, "...setting fullscreen mode {}:".format(mode) )
	else:
		gl_rmain.ri.Con_Printf (shared.PRINT_ALL, "...setting mode {}:".format(mode) )

	ok, width, height = vid.VID_GetModeInfo( mode )
	if not ok:
	
		gl_rmain.ri.Con_Printf( shared.PRINT_ALL, " invalid mode\n" )
		return gl_rmain.rserr_t.rserr_invalid_mode, pwidth, pheight
	
	gl_rmain.ri.Con_Printf( shared.PRINT_ALL, " {} {}\n".format(width, height) )
	
	# destroy the existing window
	# ShutdownGraphics() only, not GLimp_Shutdown(): the C's GLimp_Shutdown quits SDL
	# (and pygame.quit() would kill the mixer and invalidate snd_linux.dma_channel)
	ShutdownGraphics()

	flags = pygame.OPENGL | pygame.DOUBLEBUF
	if fullscreen:
		flags |= pygame.FULLSCREEN
	try:
		pygame.display.set_mode((width, height), flags)
	except pygame.error as err:
		gl_rmain.ri.Con_Printf( shared.PRINT_ALL, "Error couldn't set the video mode: {}\n".format(err) )
		if fullscreen:
			return gl_rmain.rserr_t.rserr_invalid_fullscreen, pwidth, pheight
		return gl_rmain.rserr_t.rserr_invalid_mode, pwidth, pheight

	window = pygame.display.get_surface()
	width, height = pygame.display.get_window_size()

	pwidth = width
	pheight = height

	initSuccessful = True

	# let the sound and input subsystems know about the new window
	gl_rmain.ri.Vid_NewWindow (width, height)

	return gl_rmain.rserr_t.rserr_ok, pwidth, pheight
