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

import ctypes

import OpenGL.GL as GL
from OpenGL.GL.ARB import debug_output

from backends import sdl
from common import clientserver
from common.header import common as common_h
from common.header import shared
from client.refresh.gl3 import gl3_main

#include "header/local.h"
# Q2PORT: SDL is backends/sdl.py, the SDL calls done with pyglet

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
"""
def DebugCallback(source, type_, id_, severity, length, message, userParam): #GLenum, GLenum, GLuint, GLenum, GLsizei, const GLchar *, const void *

	sourceStr = "Source: Unknown" #const char*
	typeStr = "Type: Unknown" #const char*
	severityStr = "Severity: Unknown" #const char*

	#ifdef YQ2_GL3_GLES ... #else // Desktop GL
	#define SVRCASE(X, STR)  case GL_DEBUG_SEVERITY_ ## X ## _ARB : severityStr = STR; break;
	if severity == QGL_DEBUG_SEVERITY_NOTIFICATION: return
	elif severity == debug_output.GL_DEBUG_SEVERITY_HIGH_ARB: severityStr = "Severity: High"
	elif severity == debug_output.GL_DEBUG_SEVERITY_MEDIUM_ARB: severityStr = "Severity: Medium"
	elif severity == debug_output.GL_DEBUG_SEVERITY_LOW_ARB: severityStr = "Severity: Low"

	#define SRCCASE(X)  case GL_DEBUG_SOURCE_ ## X ## _ARB: sourceStr = "Source: " #X; break;
	for X in ("API", "WINDOW_SYSTEM", "SHADER_COMPILER", "THIRD_PARTY", "APPLICATION", "OTHER"):

		if source == getattr(debug_output, "GL_DEBUG_SOURCE_" + X + "_ARB"):

			sourceStr = "Source: " + X
			break

	#define TYPECASE(X)  case GL_DEBUG_TYPE_ ## X ## _ARB: typeStr = "Type: " #X; break;
	for X in ("ERROR", "DEPRECATED_BEHAVIOR", "UNDEFINED_BEHAVIOR", "PORTABILITY", "PERFORMANCE", "OTHER"):

		if type_ == getattr(debug_output, "GL_DEBUG_TYPE_" + X + "_ARB"):

			typeStr = "Type: " + X
			break

	# Q2PORT: ctypes gives the message as a pointer
	message = ctypes.string_at(message, length).decode("latin-1")

	# use PRINT_ALL - this is only called with gl3_debugcontext != 0 anyway.
	clientserver.Com_Printf("GLDBG {} {} {}: {}\n".format(sourceStr, typeStr, severityStr, message))

# Q2PORT: the ctypes function pointer to DebugCallback given to the driver;
# kept here so it isn't garbage collected while the driver can call it
DebugCallbackPtr = None #GLDEBUGPROCARB

# ---------

def GL3_SwapWindow(): #void

	sdl.SDL_GL_SwapWindow(window)

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

	if sdl.SDL_GL_SetSwapInterval(vsync) == -1:

		if vsync == -1:

			# Not every system supports adaptive
			# vsync, fallback to normal vsync.
			clientserver.Com_Printf("Failed to set adaptive vsync, reverting to normal vsync.\n")
			sdl.SDL_GL_SetSwapInterval(1)

	vsyncActive = sdl.SDL_GL_GetSwapInterval() != 0

"""
 * This function returns the flags used at the SDL window
 * creation by GLimp_InitGraphics(). In case of error -1
 * is returned.
"""
def GL3_PrepareForWindow(): #void (returns int)

	# Mkay, let's try to load the libGL,
	# Q2PORT: pyglet loads libGL (SDL_GL_LoadLibrary); gl3_libgl is registered
	# but not used
	gl3_libgl = gl3_main.ri.Cvar_Get("gl3_libgl", "", shared.CVAR_ARCHIVE)

	# Set GL context attributs bound to the window.
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_RED_SIZE, 8)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_GREEN_SIZE, 8)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_BLUE_SIZE, 8)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DEPTH_SIZE, 24)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DOUBLEBUFFER, 1)

	if sdl.SDL_GL_SetAttribute(sdl.SDL_GL_STENCIL_SIZE, 8) == 0:

		gl3_main.gl3config.stencil = True

	else:

		gl3_main.gl3config.stencil = False

	#ifdef YQ2_GL3_GLES3
	#else // Desktop GL
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_MINOR_VERSION, 2)
	sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_PROFILE_MASK, sdl.SDL_GL_CONTEXT_PROFILE_CORE)
	#endif

	# Set GL context flags.
	contextFlags = 0

	#ifndef YQ2_GL3_GLES // Desktop GL (at least RPi4 doesn't like this for GLES3)
	contextFlags |= sdl.SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG
	#endif

	if gl3_main.gl3_debugcontext is not None and gl3_main.gl3_debugcontext.value:

		contextFlags |= sdl.SDL_GL_CONTEXT_DEBUG_FLAG

	if contextFlags != 0:

		sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_FLAGS, contextFlags)

	# Let's see if the driver supports MSAA.
	msaa_samples = 0

	if gl3_main.gl_msaa_samples.value:

		msaa_samples = int(gl3_main.gl_msaa_samples.value)

		if sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 1) < 0:

			clientserver.Com_Printf("MSAA is unsupported: {}\n".format(sdl.SDL_GetError()))
			gl3_main.ri.Cvar_SetValue ("r_msaa_samples", 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, 0)

		elif sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, msaa_samples) < 0:

			clientserver.Com_Printf("MSAA {}x is unsupported: {}\n".format(msaa_samples, sdl.SDL_GetError()))
			gl3_main.ri.Cvar_SetValue("r_msaa_samples", 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 0)
			sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, 0)

	else:

		sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLEBUFFERS, 0)
		sdl.SDL_GL_SetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES, 0)

	return sdl.SDL_WINDOW_OPENGL

"""
 * Initializes the OpenGL context. Returns true at
 * success and false at failure.
"""
def GL3_InitContext(win): #void* (returns int)

	global window, context, IsHighDPIaware, DebugCallbackPtr

	# Coders are stupid.
	if win is None:

		clientserver.Com_Error(shared.ERR_FATAL, "R_InitContext() must not be called with NULL argument!")

		return False

	window = win

	# Initialize GL context.
	context = sdl.SDL_GL_CreateContext(window)

	if context is None:

		clientserver.Com_Printf("GL3_InitContext(): Creating OpenGL Context failed: {}\n".format(sdl.SDL_GetError()))

		window = None

		return False

	# Check if we've got the requested MSAA.
	msaa_samples = 0

	if gl3_main.gl_msaa_samples.value:

		ret, msaa_samples = sdl.SDL_GL_GetAttribute(sdl.SDL_GL_MULTISAMPLESAMPLES)
		if ret == 0:

			gl3_main.ri.Cvar_SetValue("r_msaa_samples", msaa_samples)

	# Check if we've got at least 8 stencil bits
	stencil_bits = 0

	if gl3_main.gl3config.stencil:

		ret, stencil_bits = sdl.SDL_GL_GetAttribute(sdl.SDL_GL_STENCIL_SIZE)
		if ret < 0 or stencil_bits < 8:

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

		#ifdef YQ2_GL3_GLES ... #else // Desktop GL
		DebugCallbackPtr = debug_output.GLDEBUGPROCARB(DebugCallback)
		debug_output.glDebugMessageCallbackARB(DebugCallbackPtr, None)
		GL.glEnable(debug_output.GL_DEBUG_OUTPUT_SYNCHRONOUS_ARB)
		#endif

	# Window title - set here so we can display renderer name in it.
	title = "{} {} - OpenGL 3.2".format(common_h.APPNAME, common_h.YQ2VERSION) # Q2PORT: APPNAME, the C has "Yamagi Quake II"
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
def GL3_GetDrawableSize(): #int*, int* (returns width, height)

	return sdl.SDL_GL_GetDrawableSize(window)

"""
 * Shuts the GL context down.
"""
def GL3_ShutdownContext(): #void

	global context

	if window is not None:

		if context is not None:

			sdl.SDL_GL_DeleteContext(context)
			context = None

"""
 * Returns the SDL major version. Implemented
 * here to not polute gl3_main.c with the SDL
 * headers.
"""
def GL3_GetSDLVersion(): #void (returns int)

	#SDL_version ver;
	#SDL_VERSION(&ver);
	return sdl.SDL_MAJOR_VERSION
