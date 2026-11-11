"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 * Copyright (C) 2016-2017 Daniel Gibson
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
 * SDL backend for the GL3 renderer. Everything that needs to be on the
 * renderer side of thing. Also all glad (or whatever OpenGL loader I
 * end up using) specific things.
 *
 * =======================================================================
"""

from __future__ import annotations

import pygame
import OpenGL.GL as GL

from common import clientserver
from common.header import common as common_h
from common.header import shared
from client.refresh.gl3 import gl3_main

#include "header/local.h"

# Q2PORT: the platform is pygame (SDL 2 underneath). pygame owns the window
# and makes the GL context in pygame.display.set_mode(), so the window is the
# pygame display surface and "context" only records that it exists.

window = None #static SDL_Window*
context = None #static SDL_GLContext
vsyncActive = False #static qboolean
IsHighDPIaware = False #qboolean

# --------

# Not all GL.h header know about GL_DEBUG_SEVERITY_NOTIFICATION_*.
# DG: yes, it's the same value in GLES3.2
QGL_DEBUG_SEVERITY_NOTIFICATION = 0x826B

"""
 * Callback function for debug output.
static void APIENTRY
DebugCallback(GLenum source, GLenum type, GLuint id, GLenum severity, GLsizei length,
              const GLchar *message, const void *userParam)
{
	(not ported: gl3_debugcontext needs glDebugMessageCallbackARB with a ctypes
	 callback)
}
"""

# ---------

def GL3_SwapWindow(): #void

	pygame.display.flip() # SDL_GL_SwapWindow(window)

"""
 * Returns whether the vsync is enabled.
"""
def GL3_IsVsyncActive(): #void (returns qboolean)

	return vsyncActive

"""
 * Enables or disables the vsync.
"""
def GL3_SetVsync(): #void

	global vsyncActive

	# Make sure that the user given
	# value is SDL compatible...
	vsync = 0

	if gl3_main.r_vsync.value == 1:

		vsync = 1

	elif gl3_main.r_vsync.value == 2:

		vsync = -1

	# Q2PORT: pygame has no SDL_GL_SetSwapInterval(); it only takes vsync when
	# the window is made (set_mode(..., vsync=1)). So nothing is changed here
	# and the state is what was asked for.
	vsyncActive = vsync != 0

"""
 * This function returns the flags used at the SDL window
 * creation by GLimp_InitGraphics(). In case of error -1
 * is returned.
"""
def GL3_PrepareForWindow(): #void (returns int)

	# Mkay, let's try to load the libGL,
	# Q2PORT: SDL_GL_LoadLibrary is done by pygame; gl3_libgl is registered
	# but not used
	gl3_libgl = gl3_main.ri.Cvar_Get("gl3_libgl", "", shared.CVAR_ARCHIVE)

	# Set GL context attributs bound to the window.
	pygame.display.gl_set_attribute(pygame.GL_RED_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_GREEN_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_BLUE_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
	pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)

	# Q2PORT: pygame's gl_set_attribute returns nothing; the C checks the
	# result of SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8)
	pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
	gl3_main.gl3config.stencil = True

	# Desktop GL
	pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
	pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 2)
	pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

	# Set GL context flags.
	contextFlags = 0

	# Desktop GL (at least RPi4 doesn't like this for GLES3)
	contextFlags |= pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG

	if gl3_main.gl3_debugcontext is not None and gl3_main.gl3_debugcontext.value:

		contextFlags |= pygame.GL_CONTEXT_DEBUG_FLAG

	if contextFlags != 0:

		pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FLAGS, contextFlags)

	# Let's see if the driver supports MSAA.
	msaa_samples = 0

	if gl3_main.gl_msaa_samples.value:

		msaa_samples = int(gl3_main.gl_msaa_samples.value)

		# Q2PORT: the C checks the results to detect unsupported MSAA; pygame
		# doesn't report them here (set_mode fails instead)
		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, msaa_samples)

	else:

		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
		pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)

	return pygame.OPENGL | pygame.DOUBLEBUF # SDL_WINDOW_OPENGL, Q2PORT: pygame needs DOUBLEBUF too

"""
 * Initializes the OpenGL context. Returns true at
 * success and false at failure.
"""
def GL3_InitContext(win): #void* (returns int)

	global window, context

	# Coders are stupid.
	if win is None:

		clientserver.Com_Error(shared.ERR_FATAL, "R_InitContext() must not be called with NULL argument!")

		return False

	window = win

	# Initialize GL context.
	# Q2PORT: pygame made the context in set_mode()
	context = window

	# Check if we've got the requested MSAA.
	msaa_samples = 0

	if gl3_main.gl_msaa_samples.value:

		msaa_samples = pygame.display.gl_get_attribute(pygame.GL_MULTISAMPLESAMPLES)
		gl3_main.ri.Cvar_SetValue("r_msaa_samples", msaa_samples)

	# Check if we've got at least 8 stencil bits
	stencil_bits = 0

	if gl3_main.gl3config.stencil:

		stencil_bits = pygame.display.gl_get_attribute(pygame.GL_STENCIL_SIZE)
		if stencil_bits < 8:

			gl3_main.gl3config.stencil = False

	# Enable vsync if requested.
	GL3_SetVsync()

	# Load GL pointers through GLAD and check context.
	# Q2PORT: PyOpenGL loads the pointers; this checks the version the same way
	major = GL.glGetIntegerv(GL.GL_MAJOR_VERSION)
	minor = GL.glGetIntegerv(GL.GL_MINOR_VERSION)
	if major < 3 or (major == 3 and minor < 2):

		clientserver.Com_Printf("GL3_InitContext(): ERROR: glad only got GL version {}.{}!\n".format(major, minor))

		return False

	else:

		clientserver.Com_Printf("Successfully loaded OpenGL function pointers using glad, got version {}.{}!\n".format(major, minor))

	# Q2PORT: GLAD_GL_* are whether the extension is in the context's list
	numExtensions = GL.glGetIntegerv(GL.GL_NUM_EXTENSIONS)
	extensions = set(GL.glGetStringi(GL.GL_EXTENSIONS, i).decode("ascii") for i in range(numExtensions))
	gl3_main.gl3config.debug_output = "GL_ARB_debug_output" in extensions
	gl3_main.gl3config.anisotropic = "GL_EXT_texture_filter_anisotropic" in extensions

	gl3_main.gl3config.major_version = major
	gl3_main.gl3config.minor_version = minor

	# Debug context setup.
	if gl3_main.gl3_debugcontext is not None and gl3_main.gl3_debugcontext.value and gl3_main.gl3config.debug_output:

		# Q2PORT: glDebugMessageCallbackARB(DebugCallback, NULL) is not ported
		pass

	# Window title - set here so we can display renderer name in it.
	title = "{} {} - OpenGL 3.2".format(common_h.APPNAME, common_h.YQ2VERSION) # Q2PORT: APPNAME, the C has "Yamagi Quake II"
	pygame.display.set_caption(title)

	# Figure out if we are high dpi aware.
	# Q2PORT: the platform never asks for SDL_WINDOW_ALLOW_HIGHDPI, so false

	return True

"""
 * Fills the actual size of the drawable into width and height.
"""
def GL3_GetDrawableSize(): #int*, int* (returns width, height)

	return pygame.display.get_surface().get_size() # SDL_GL_GetDrawableSize(window, width, height)

"""
 * Shuts the GL context down.
"""
def GL3_ShutdownContext(): #void

	global context

	if window is not None:

		if context is not None:

			# Q2PORT: the context goes with the pygame window
			context = None

"""
 * Returns the SDL major version. Implemented
 * here to not polute gl3_main.c with the SDL
 * headers.
"""
def GL3_GetSDLVersion(): #void (returns int)

	return pygame.get_sdl_version()[0]
