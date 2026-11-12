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
 * SDL backend for the GL1 renderer.
 *
 * =======================================================================
"""
from __future__ import annotations

import OpenGL.GL as GL

from backends import sdl
from common import clientserver
from common.header import common as common_h
from common.header import shared
from client.refresh.gl1 import gl1_main, gl1_buffer

"""
#include "header/local.h"

#ifdef USE_SDL3
#include <SDL3/SDL.h>
#else
#include <SDL2/SDL.h>
#endif

Q2PORT: SDL is backends/sdl.py, the SDL calls done with pyglet
"""

window = None #static SDL_Window*
context = None #static SDL_GLContext
IsHighDPIaware = False #qboolean
vsyncActive = False #static qboolean

# ----

"""
 * Swaps the buffers and shows the next frame.
"""
def RI_EndFrame(): #void

	gl1_buffer.R_ApplyGLBuffer()	# to draw buffered 2D text

	#ifdef YQ2_GL1_GLES
	# (GLES only)
	#endif

	sdl.SDL_GL_SwapWindow(window)

"""
 * Returns the adress of a GL function
"""
def RI_GetProcAddress(proc: str): #const char* (returns void *)

	# Q2PORT: PyOpenGL resolves the GL functions; this returns PyOpenGL's
	# function when the driver has it (SDL_GL_GetProcAddress)
	func = getattr(GL, proc, None)
	if func is None or not bool(func):
		return None
	return func

"""
 * Returns whether the vsync is enabled.
"""
def RI_IsVSyncActive()->bool: #void (returns qboolean)

	return vsyncActive

"""
 * This function returns the flags used at the SDL window
 * creation by GLimp_InitGraphics(). In case of error -1
 * is returned.
"""
def RI_PrepareForWindow()->int: #void (returns int)

	# Set GL context attributs bound to the window.
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_RED_SIZE, 8)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_GREEN_SIZE, 8)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_BLUE_SIZE, 8)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DEPTH_SIZE, 24)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DOUBLEBUFFER, 1)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_ACCELERATED_VISUAL, 1)

	if sdl.SDL_GL_SetAttribute(sdl.SDL_GL_STENCIL_SIZE, 8) == 0:

		gl1_main.gl_state.stencil = True

	else:

		gl1_main.gl_state.stencil = False

	#ifdef YQ2_GL1_GLES
	# (GLES only)
	#endif

	# Let's see if the driver supports MSAA.
	msaa_samples = 0

	if gl1_main.gl_msaa_samples.value:

		msaa_samples = int(gl1_main.gl_msaa_samples.value)

		if sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 1) < 0:

			clientserver.Com_Printf("MSAA is unsupported: {}\n".format(sdl.SDL_GetError()))
			gl1_main.ri.Cvar_SetValue ("r_msaa_samples", 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, 0)

		elif sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, msaa_samples) < 0:

			clientserver.Com_Printf("MSAA {}x is unsupported: {}\n".format(msaa_samples, sdl.SDL_GetError()))
			gl1_main.ri.Cvar_SetValue("r_msaa_samples", 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, 0)

	else:

		sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 0)
		sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, 0)

	return sdl.SDL_WINDOW_OPENGL

"""
 * Enables or disables the vsync.
"""
def RI_SetVsync(): #void

	global vsyncActive

	# Make sure that the user given
	# value is SDL compatible...
	vsync = 0

	if gl1_main.r_vsync.value == 1:

		vsync = 1

	elif gl1_main.r_vsync.value == 2:

		vsync = -1

	if sdl.SDL_GL_SetSwapInterval(vsync) == -1:

		if vsync == -1:

			# Not every system supports adaptive
			# vsync, fallback to normal vsync.
			clientserver.Com_Printf("Failed to set adaptive vsync, reverting to normal vsync.\n")
			sdl.SDL_GL_SetSwapInterval(1)

	vsyncActive = sdl.SDL_GL_GetSwapInterval() != 0

"""
 * Updates the gamma ramp. Only used with SDL2.
"""
def RI_UpdateGamma(): #void

	# Hardware gamma / gamma ramps are no longer supported with SDL3.
	# There's no replacement and sdl2-compat won't support it either.
	# See https://github.com/libsdl-org/SDL/pull/6617 for the rational.
	# Gamma works with a lookup table when using SDL3 (or GLES1).
	#ifndef GL1_GAMMATABLE
	gamma = gl1_main.vid_gamma.value
	ramp = [0] * 256 #Uint16 [256]

	sdl.SDL_CalculateGammaRamp(gamma, ramp)
	if sdl.SDL_SetWindowGammaRamp(window, ramp, ramp, ramp) != 0:

		clientserver.Com_Printf("Setting gamma failed: {}\n".format(sdl.SDL_GetError()))
	#endif

"""
 * Initializes the OpenGL context. Returns true at
 * success and false at failure.
"""
def RI_InitContext(win)->bool: #void* (returns int)

	global window, context, IsHighDPIaware

	# Coders are stupid.
	if win is None:

		clientserver.Com_Error(shared.ERR_FATAL, "{} must not be called with NULL argument!".format("RI_InitContext"))

		return False

	window = win

	# Initialize GL context.
	context = sdl.SDL_GL_CreateContext(window)

	if context is None:

		clientserver.Com_Printf("{}: Creating OpenGL Context failed: {}\n".format("RI_InitContext", sdl.SDL_GetError()))

		window = None

		return False

	#ifdef YQ2_GL1_GLES
	# (GLES only)
	#else

	# Check if it's really OpenGL 1.4.
	glver = GL.glGetString(GL.GL_VERSION).decode("ascii", "ignore")
	try:
		major, minor = (int(x) for x in glver.split(" ")[0].split(".")[:2]) # sscanf(glver, "%d.%d", ...)
	except ValueError:
		major, minor = 0, 0
	gl1_main.gl_config.major_version, gl1_main.gl_config.minor_version = major, minor

	if gl1_main.gl_config.major_version < 1 or (gl1_main.gl_config.major_version == 1 and gl1_main.gl_config.minor_version < 4):

		clientserver.Com_Printf("{}: Got an OpenGL version {}.{} context - need (at least) 1.4!\n".format("RI_InitContext", gl1_main.gl_config.major_version, gl1_main.gl_config.minor_version))

		return False

	#endif

	# Check if we've got the requested MSAA.
	msaa_samples = 0

	if gl1_main.gl_msaa_samples.value:

		ret, msaa_samples = sdl.SDL_GL_GetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES)
		if ret == 0:

			gl1_main.ri.Cvar_SetValue("r_msaa_samples", msaa_samples)

	# Enable vsync if requested.
	RI_SetVsync()

	# Check if we've got 8 stencil bits.
	stencil_bits = 0

	if gl1_main.gl_state.stencil:

		ret, stencil_bits = sdl.SDL_GL_GetAttribute(sdl.SDL_GL_STENCIL_SIZE)
		if ret < 0 or stencil_bits < 8:

			gl1_main.gl_state.stencil = False

	# Initialize gamma.
	gl1_main.vid_gamma.modified = True

	# Window title - set here so we can display renderer name in it.
	#ifdef YQ2_GL1_GLES
	#else
	title = "{} {} - OpenGL 1.4".format(common_h.APPNAME, common_h.YQ2VERSION) # Q2PORT: APPNAME, the C has "Yamagi Quake II"
	#endif
	sdl.SDL_SetWindowTitle(window, title)

	#if SDL_VERSION_ATLEAST(2, 26, 0)
	# Figure out if we are high dpi aware.
	flags = sdl.SDL_GetWindowFlags(win)
	IsHighDPIaware = True if (flags & sdl.SDL_WINDOW_ALLOW_HIGHDPI) else False
	#endif

	return True

"""
 * Fills the actual size of the drawable into width and height.
"""
def RI_GetDrawableSize()->tuple: #int*, int* (returns width, height)

	return sdl.SDL_GL_GetDrawableSize(window)

"""
 * Shuts the GL context down.
"""
def RI_ShutdownContext(): #void

	global context

	if window:

		if context:

			sdl.SDL_GL_DeleteContext(context)
			context = None

"""
 * Returns the SDL major version. Implemented
 * here to not polute gl1_main.c with the SDL
 * headers.
"""
def RI_GetSDLVersion()->int: #void (returns int)

	#SDL_version ver;
	#SDL_VERSION(&ver);
	return sdl.SDL_MAJOR_VERSION
