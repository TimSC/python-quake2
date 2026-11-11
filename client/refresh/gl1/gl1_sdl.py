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

import warnings
import pygame
import OpenGL.GL as GL

from common import clientserver
from common.header import common as common_h
from common.header import shared
from client.refresh.gl1 import gl1_main, gl1_buffer

"""
#include "header/local.h"

#include <SDL2/SDL.h>
"""

# Q2PORT: the platform is pygame (SDL 2 underneath). pygame owns the window
# and makes the GL context in pygame.display.set_mode(), so the window is the
# pygame display surface and "context" only records that it exists.

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

	pygame.display.flip() # SDL_GL_SwapWindow(window)

"""
 * Returns the adress of a GL function
"""
def RI_GetProcAddress(proc): #const char* (returns void *)

	# Q2PORT: PyOpenGL resolves the GL functions; this returns PyOpenGL's
	# function when the driver has it (SDL_GL_GetProcAddress)
	func = getattr(GL, proc, None)
	if func is None or not bool(func):
		return None
	return func

"""
 * Returns whether the vsync is enabled.
"""
def RI_IsVSyncActive(): #void (returns qboolean)

	return vsyncActive

"""
 * This function returns the flags used at the SDL window
 * creation by GLimp_InitGraphics(). In case of error -1
 * is returned.
"""
def RI_PrepareForWindow(): #void (returns int)

	# Set GL context attributs bound to the window.
	pygame.display.gl_set_attribute(pygame.GL_RED_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_GREEN_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_BLUE_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
	pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
	pygame.display.gl_set_attribute(pygame.GL_ACCELERATED_VISUAL, 1)

	# Q2PORT: pygame's gl_set_attribute returns nothing; the C checks the
	# result of SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8). RI_InitContext
	# checks the bits we got.
	pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
	gl1_main.gl_state.stencil = True

	#ifdef YQ2_GL1_GLES
	# (GLES only)
	#endif

	# Let's see if the driver supports MSAA.
	msaa_samples = 0

	if gl1_main.gl_msaa_samples.value:

		msaa_samples = int(gl1_main.gl_msaa_samples.value)

		# Q2PORT: the C checks the results to detect unsupported MSAA; pygame
		# doesn't report them here (set_mode fails instead, and R_SetMode
		# then retries with r_msaa_samples 0)
		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, msaa_samples)

	else:

		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)

	return pygame.OPENGL | pygame.DOUBLEBUF # SDL_WINDOW_OPENGL, Q2PORT: pygame needs DOUBLEBUF too

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

	# Q2PORT: pygame has no SDL_GL_SetSwapInterval() / SDL_GL_GetSwapInterval();
	# it only takes vsync when the window is made (set_mode(..., vsync=1)). So
	# nothing is changed here and the state is what was asked for (as gl3_sdl).
	vsyncActive = vsync != 0

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

	# Q2PORT: pygame's set_gamma is SDL_CalculateGammaRamp + SDL_SetWindowGammaRamp
	# (it is deprecated, so its warning is silenced)
	with warnings.catch_warnings():
		warnings.simplefilter("ignore", DeprecationWarning)
		ok = pygame.display.set_gamma(gamma)

	if not ok:

		clientserver.Com_Printf("Setting gamma failed: {}\n".format(pygame.get_error()))
	#endif

"""
 * Initializes the OpenGL context. Returns true at
 * success and false at failure.
"""
def RI_InitContext(win): #void* (returns int)

	global window, context, IsHighDPIaware

	# Coders are stupid.
	if win is None:

		clientserver.Com_Error(shared.ERR_FATAL, "{} must not be called with NULL argument!".format("RI_InitContext"))

		return False

	window = win

	# Initialize GL context.
	# Q2PORT: pygame made the context in set_mode()
	context = window

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

		msaa_samples = pygame.display.gl_get_attribute(pygame.GL_MULTISAMPLESAMPLES)
		gl1_main.ri.Cvar_SetValue("r_msaa_samples", msaa_samples)

	# Enable vsync if requested.
	RI_SetVsync()

	# Check if we've got 8 stencil bits.
	stencil_bits = 0

	if gl1_main.gl_state.stencil:

		stencil_bits = pygame.display.gl_get_attribute(pygame.GL_STENCIL_SIZE)
		if stencil_bits < 8:

			gl1_main.gl_state.stencil = False

	# Initialize gamma.
	gl1_main.vid_gamma.modified = True

	# Window title - set here so we can display renderer name in it.
	#ifdef YQ2_GL1_GLES
	#else
	title = "{} {} - OpenGL 1.4".format(common_h.APPNAME, common_h.YQ2VERSION) # Q2PORT: APPNAME, the C has "Yamagi Quake II"
	#endif
	pygame.display.set_caption(title)

	# Figure out if we are high dpi aware.
	# Q2PORT: the platform never asks for SDL_WINDOW_ALLOW_HIGHDPI, so false
	IsHighDPIaware = False

	return True

"""
 * Fills the actual size of the drawable into width and height.
"""
def RI_GetDrawableSize(): #int*, int* (returns width, height)

	return pygame.display.get_surface().get_size() # SDL_GL_GetDrawableSize(window, width, height)

"""
 * Shuts the GL context down.
"""
def RI_ShutdownContext(): #void

	global context

	if window is not None:

		if context is not None:

			# Q2PORT: the context goes with the pygame window
			context = None

"""
 * Returns the SDL major version. Implemented
 * here to not polute gl1_main.c with the SDL
 * headers.
"""
def RI_GetSDLVersion(): #void (returns int)

	return pygame.get_sdl_version()[0]
