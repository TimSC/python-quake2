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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * ABI between client and refresher
 *
 * =======================================================================
"""
from __future__ import annotations

import copy
import numpy as np
from enum import Enum


MAX_DLIGHTS		= 32
MAX_ENTITIES	= 128
MAX_PARTICLES	= 4096
MAX_LIGHTSTYLES	= 256

POWERSUIT_SCALE		= 4.0

SHELL_RED_COLOR		= 0xF2
SHELL_GREEN_COLOR	= 0xD0
SHELL_BLUE_COLOR	= 0xF3
SHELL_RG_COLOR		= 0xDC
SHELL_RB_COLOR		= 0x68
SHELL_BG_COLOR		= 0x78

SHELL_DOUBLE_COLOR	= 0xDF
SHELL_HALF_DAM_COLOR	= 0x90
SHELL_CYAN_COLOR	= 0x72

SHELL_WHITE_COLOR	= 0xD7

ENTITY_FLAGS = 68


class entity_t(object):

	def __init__(self):

		self.model = None # struct model_s *, opaque type outside refresh
		self.angles = np.zeros((3,), dtype=np.float32) #float [3]

		# most recent data
		self.origin = np.zeros((3,), dtype=np.float32) #float [3], also used as RF_BEAM's "from"
		self.frame = 0 # int, also used as RF_BEAM's diameter

		# previous data for lerping
		self.oldorigin = np.zeros((3,), dtype=np.float32) #float [3], also used as RF_BEAM's "to"
		self.oldframe = 0 # int

		# misc
		self.backlerp = 0.0 # float, 0.0 = current, 1.0 = old
		self.skinnum = 0 # int, also used as RF_BEAM's palette index
		self.lightstyle = 0 # int, for flashing entities
		self.alpha = 1.0 # float, ignore if RF_TRANSLUCENT isn't set

		self.skin = None # struct image_s *, NULL for inline skin
		self.flags = 0 # int

	def copy(self):
		# struct assignment, arrays are copied but pointers (model, skin) stay shared.
		out = copy.copy(self)
		out.angles = self.angles.copy()
		out.origin = self.origin.copy()
		out.oldorigin = self.oldorigin.copy()
		return out


class dlight_t(object):

	def __init__(self):
		self.origin = np.zeros((3,), dtype=np.float32) # vec3_t
		self.color = np.zeros((3,), dtype=np.float32) # vec3_t
		self.intensity = 0.0 # float


class particle_t(object):

	def __init__(self):
		self.origin = np.zeros((3,), dtype=np.float32) # vec3_t
		self.color = 0 # int
		self.alpha = 0.0 # float


class lightstyle_t(object):

	def __init__(self):
		self.rgb = np.zeros((3,), dtype=np.float32) # float[3], 0.0 - 2.0
		self.white = 0.0 # float, r+g+b


class refdef_t(object):

	def __init__(self):

		self.x, self.y, self.width, self.height = 0, 0, 0, 0 # int, in virtual screen coordinates
		self.fov_x, self.fov_y = 0.0, 0.0 #float
		self.vieworg = np.zeros((3,), dtype=np.float32) #float [3]
		self.viewangles = np.zeros((3,), dtype=np.float32) #float [3]
		self.blend = np.zeros((4,), dtype=np.float32) #float[4], rgba 0-1 full screen blend
		self.time = 0.0 # float, time is used to auto animate
		self.rdflags = 0 # int, RDF_UNDERWATER, etc

		self.areabits = None #byte *, if not NULL, only areas with set bits will be drawn

		self.lightstyles = None #lightstyle_t *, [MAX_LIGHTSTYLES]

		self.num_entities = 0 # int
		self.entities = None #entity_t *

		self.num_dlights = 0 #int, <= 32 (MAX_DLIGHTS)
		self.dlights = None #dlight_t *

		self.num_particles = 0 #int
		self.particles = None #particle_t *

	def copy(self):
		# struct assignment, arrays are copied but pointers (entities, lightstyles...) stay shared.
		out = copy.copy(self)
		out.vieworg = self.vieworg.copy()
		out.viewangles = self.viewangles.copy()
		out.blend = self.blend.copy()
		return out


# Renderer restart type.
class ref_restart_t(Enum):
	RESTART_UNDEF = 0
	RESTART_NO = 1
	RESTART_FULL = 2
	RESTART_PARTIAL = 3


API_VERSION = 8

#
# these are the functions exported by the refresh module
#
class refexport_t(object):

	def __init__(self):

		# if api_version is different, the dll cannot be used
		self.api_version = 0 #int

		# if framework_version is different, the dll cannot be used
		# necessary because differend SDL major version cannot be mixed.
		self.framework_version = 0 #int

		# called when the library is loaded
		self.Init = None #qboolean (*) ( void )

		# called before the library is unloaded
		self.Shutdown = None #void (*) (void)

		# called by GLimp_InitGraphics() before creating window,
		# returns flags for SDL window creation, returns -1 on error
		self.PrepareForWindow = None #int (*) (void)

		# called by GLimp_InitGraphics() *after* creating window,
		# passing the SDL_Window* (void* so we don't spill SDL.h here)
		# (or SDL_Surface* for SDL1.2, another reason to use void*)
		# returns true (1) on success
		self.InitContext = None #int (*) (void *sdl_window)

		# called by GLimp_InitGraphics() *after* creating render
		# context. Returns the actual drawable size in the width
		# and height variables. This may be different from the
		# window size due to high dpi awareness.
		self.GetDrawableSize = None #void (*) (int *width, int *height)

		# shuts down rendering (OpenGL) context.
		self.ShutdownContext = None #void (*) (void)

		# returns true if vsync is active, else false
		self.IsVSyncActive = None #qboolean (*) (void)

		# All data that will be used in a level should be
		# registered before rendering any frames to prevent disk hits,
		# but they can still be registered at a later time
		# if necessary.
		#
		# EndRegistration will free any remaining data that wasn't registered.
		# Any model_s or skin_s pointers from before the BeginRegistration
		# are no longer valid after EndRegistration.
		#
		# Skins and images need to be differentiated, because skins
		# are flood filled to eliminate mip map edge errors, and pics have
		# an implicit "pics/" prepended to the name. (a pic name that starts with a
		# slash will not use the "pics/" prefix or the ".pcx" postfix)
		self.BeginRegistration = None #void (*) (const char *map)
		self.RegisterModel = None #struct model_s * (*) (const char *name)
		self.RegisterSkin = None #struct image_s * (*) (const char *name)

		self.SetSky = None #void (*) (const char *name, float rotate, vec3_t axis)
		self.EndRegistration = None #void (*) (void)

		self.RenderFrame = None #void (*) (refdef_t *fd)

		self.DrawFindPic = None #struct image_s * (*) (const char *name)

		self.DrawGetPicSize = None #void (*) (int *w, int *h, const char *name)	# will return 0 0 if not found
		self.DrawPicScaled = None #void (*) (int x, int y, const char *pic, float factor)
		self.DrawStretchPic = None #void (*) (int x, int y, int w, int h, const char *name)
		self.DrawCharScaled = None #void (*) (int x, int y, int num, float scale)
		self.DrawTileClear = None #void (*) (int x, int y, int w, int h, const char *name)
		self.DrawFill = None #void (*) (int x, int y, int w, int h, int c)
		self.DrawFadeScreen = None #void (*) (void)

		#
		# Draw images for cinematic rendering (which can have a different palette if bits equals to 8). Note that calls
		#
		self.DrawStretchRaw = None #void (*) (int x, int y, int w, int h, int cols, int rows, const byte *data, int bits)

		#
		# video mode and refresh state management entry points
		#
		self.SetPalette = None #void (*) (const unsigned char *palette)	# NULL = game palette
		self.BeginFrame = None #void (*) (float camera_separation)
		self.EndFrame = None #void (*) (void)
		self.EndWorldRenderpass = None #qboolean (*) (void), finish world rendering, apply postprocess and switch to UI render pass

		self.DrawPicScaledCol = None #void (*) (int x, int y, const char *pic, float factor, const float color[3])

		#void		(EXPORT *AppActivate)( qboolean activate );


#
# these are the functions imported by the refresh module
#
class refimport_t(object):

	def __init__(self):

		self.Sys_Error = None #void (*) (int err_level, const char *str, ...)

		self.Cmd_AddCommand = None #void (*) (const char *name, void (*cmd)(void))
		self.Cmd_RemoveCommand = None #void (*) (const char *name)
		self.Cmd_Argc = None #int (*) (void)
		self.Cmd_Argv = None #char * (*) (int i)
		self.Cmd_ExecuteText = None #void (*) (int exec_when, const char *text)

		self.Com_VPrintf = None #void (*) (int print_level, const char *fmt, va_list argptr)

		# files will be memory mapped read only
		# the returned buffer may be part of a larger pak file,
		# or a discrete file from anywhere in the quake search path
		# a -1 return means the file does not exist
		# NULL can be passed for buf to just determine existance
		self.FS_LoadFile = None #int (*) (const char *name, void **buf)
		self.FS_FreeFile = None #void (*) (void *buf)

		# gamedir will be the current directory that generated
		# files should be stored to, ie: "f:\quake\id1"
		self.FS_Gamedir = None #const char * (*) (void)

		self.Cvar_Get = None #cvar_t * (*) (const char *name, const char *value, int flags)
		self.Cvar_Set = None #cvar_t * (*) (const char *name, const char *value)
		self.Cvar_SetValue = None #void (*) (const char *name, float value)

		self.Vid_GetModeInfo = None #qboolean (*) (int *width, int *height, int mode)
		self.Vid_MenuInit = None #void (*) (void)
		# called with image data of width*height pixel which comp bytes per pixel (must be 3 or 4 for RGB or RGBA)
		# expects the pixels data to be row-wise, starting at top left
		self.Vid_WriteScreenshot = None #void (*) (int width, int height, int comp, const void *data)

		self.GLimp_InitGraphics = None #qboolean (*) (int fullscreen, int *pwidth, int *pheight)
		self.GLimp_GetDesktopMode = None #qboolean (*) (int *pwidth, int *pheight)

		self.Vid_RequestRestart = None #void (*) (ref_restart_t rs)

"""
// this is the only function actually exported at the linker level
typedef	refexport_t	(EXPORT *GetRefAPI_t) (refimport_t);
"""
