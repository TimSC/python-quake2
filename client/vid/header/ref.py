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
# refexport_t is client/refresh/renderer.py's Renderer
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
