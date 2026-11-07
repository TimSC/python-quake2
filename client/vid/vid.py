"""
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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

API between the client and renderers.

=======================================================================
"""
from __future__ import annotations

from client import cl_main, snd_dma
from client import cl_keyboard
from client import cl_tempentities
from client import ref
from client.vid import glimp_sdl2
from backends.generic import misc
from common import cvar
from common import clientserver
from common import cmdparser
from common import filesystem
from common.header import shared
"""
#include <assert.h>
#include <errno.h>

#include "../../client/header/client.h"
#include "../../client/header/keyboard.h"

# Q2PORT: the renderers are python modules (ref_gl is gl1), not libraries to dlopen
"""
"""
# Screenshots
# -----------

# Q2PORT: VID_WriteScreenshot (stb_image_write) is ported with the gl1 renderer (group 15),
# the old renderer has its own "screenshot" command (ref_gl/gl_rmisc.py)
"""

# --------

# Video mode array
# ----------------

class vidmode_t(object):

	def __init__(self, description, width, height, mode):

		self.description = description #const char *
		self.width, self.height = width, height #int
		self.mode = mode #int

# This must be the same as VID_MenuInit()->resolutions[] in videomenu.c!
vid_modes = [ #vidmode_t []
	vidmode_t("Mode  0:  320x240", 320, 240, 0),
	vidmode_t("Mode  1:  400x300", 400, 300, 1),
	vidmode_t("Mode  2:  512x384", 512, 384, 2),
	vidmode_t("Mode  3:  640x400", 640, 400, 3),
	vidmode_t("Mode  4:  640x480", 640, 480, 4),
	vidmode_t("Mode  5:  800x500", 800, 500, 5),
	vidmode_t("Mode  6:  800x600", 800, 600, 6),
	vidmode_t("Mode  7:  960x720", 960, 720, 7),
	vidmode_t("Mode  8: 1024x480", 1024, 480, 8),
	vidmode_t("Mode  9: 1024x640", 1024, 640, 9),
	vidmode_t("Mode 10: 1024x768", 1024, 768, 10),
	vidmode_t("Mode 11: 1152x768", 1152, 768, 11),
	vidmode_t("Mode 12: 1152x864", 1152, 864, 12),
	vidmode_t("Mode 13: 1280x800", 1280, 800, 13),
	vidmode_t("Mode 14: 1280x720", 1280, 720, 14),
	vidmode_t("Mode 15: 1280x960", 1280, 960, 15),
	vidmode_t("Mode 16: 1280x1024", 1280, 1024, 16),
	vidmode_t("Mode 17: 1366x768", 1366, 768, 17),
	vidmode_t("Mode 18: 1440x900", 1440, 900, 18),
	vidmode_t("Mode 19: 1600x1200", 1600, 1200, 19),
	vidmode_t("Mode 20: 1680x1050", 1680, 1050, 20),
	vidmode_t("Mode 21: 1920x1080", 1920, 1080, 21),
	vidmode_t("Mode 22: 1920x1200", 1920, 1200, 22),
	vidmode_t("Mode 23: 2048x1536", 2048, 1536, 23),
	vidmode_t("Mode 24: 2560x1080", 2560, 1080, 24),
	vidmode_t("Mode 25: 2560x1440", 2560, 1440, 25),
	vidmode_t("Mode 26: 2560x1600", 2560, 1600, 26),
	vidmode_t("Mode 27: 3440x1440", 3440, 1440, 27),
	vidmode_t("Mode 28: 3840x1600", 3840, 1600, 28),
	vidmode_t("Mode 29: 3840x2160", 3840, 2160, 29),
	vidmode_t("Mode 30: 4096x2160", 4096, 2160, 30),
	vidmode_t("Mode 31: 5120x2880", 5120, 2880, 31),
	vidmode_t("Mode 32: 1600x900", 1600, 900, 32),
]
VID_NUM_MODES = len(vid_modes) #ARRLEN(vid_modes)

"""
 * Callback function for the 'vid_listmodes' cmd.
"""
def VID_ListModes_f(): #void

	clientserver.Com_Printf("Supported video modes (r_mode):\n")

	for i in range(VID_NUM_MODES):

		clientserver.Com_Printf("  {}\n".format(vid_modes[i].description))

	clientserver.Com_Printf("  Mode -1: r_customwidth x r_customheight\n")

"""
 * Returns informations about the given mode.
 """
def VID_GetModeInfo( mode ): #int *width, int *height, int mode (returns qboolean, width, height)

	if mode < 0 or mode >= VID_NUM_MODES:
		return False, 0, 0

	width  = vid_modes[mode].width
	height = vid_modes[mode].height

	return True, width, height

# --------

# Renderer load, restart and shutdown
# -----------------------------------

# Global console variables.
vid_gamma = None #cvar_t *
vid_fullscreen = None #cvar_t *
vid_renderer = None #cvar_t *

# Global video state, used throughout the client.
class viddef_t(object):

	def __init__(self):

		self.width, self.height = 0, 0 #unsigned, coordinates from main game

viddef = viddef_t() # global video state; used by other modules

# Struct with the pointers exported by the renderer.
re = ref.refexport_t()

# Handle / pointer the the loaded renderer DLL.
reflib_handle = None #void *, the renderer is a python module

# Is a renderer loaded and active?
ref_active = False #qboolean

# Renderer restart type requested.
restart_state = 0 #ref_restart_t, RESTART_UNDEF

# Renderer lib extension.
lib_ext = "so" #const char *

"""
 * Returns platform specific path to a renderer lib.
"""
def VID_GetRendererLibPath(renderer: str): #const char *, char *, size_t (returns void, path)

	# Q2PORT: returns the path
	return "{}ref_{}.{}".format(misc.Sys_GetBinaryDir(), renderer, lib_ext)

"""
 * Checks if a renderer DLL is available.
"""
def VID_HasRenderer(renderer: str)->bool: #const char * (returns qboolean)

	reflib_path = VID_GetRendererLibPath(renderer)

	# Sys_IsFile(reflib_path), Q2PORT: the port has one built in renderer (ref_gl, gl1),
	# it is always available
	return renderer == "gl1"

"""
 * Called by the renderer to request a restart.
"""
def VID_RequestRestart(rs): #ref_restart_t

	global restart_state

	restart_state = rs

"""
 * Restarts the renderer.
"""
def VID_Restart_f(): #void

	global restart_state

	if restart_state == 0: # RESTART_UNDEF

		vid_fullscreen.modified = True
	else:

		restart_state = 2 # RESTART_FULL

"""
 * Shuts the renderer down and unloads it.
"""
def VID_ShutdownRenderer(): #void

	global re, reflib_handle, ref_active

	if ref_active:

		# shut down the renderer
		re.Shutdown()
		glimp_sdl2.GLimp_ShutdownGraphics()
		# Sys_FreeLibrary(reflib_handle); the renderer is a python module
		reflib_handle = None
		re = ref.refexport_t() # memset (&re, 0, sizeof(re));

		cl_tempentities.CL_ClearTEntModels()

	# declare the refresher as inactive
	ref_active = False

"""
 * Loads and initializes a renderer.
"""
def VID_LoadRenderer(): #void (returns qboolean)

	global re, reflib_handle, ref_active

	#ri = ref.refimport_t()
	#GetRefAPI

	#char reflib_name[64];
	#char reflib_path[MAX_OSPATH];
	reflib_name = None
	reflib_path = None

	# if the refresher is already active we need
	# to shut it down before loading a new one
	VID_ShutdownRenderer()

	# log what we're doing.
	clientserver.Com_Printf("----- refresher initialization -----\n")

	reflib_name = "ref_{}.{}".format(vid_renderer.string, lib_ext)
	reflib_path = VID_GetRendererLibPath(vid_renderer.string)
	clientserver.Com_Printf("Loading library: {}\n".format(reflib_name))

	# check if the renderer libs exists.
	if not VID_HasRenderer(vid_renderer.string):

		clientserver.Com_Printf("Library {} cannot be found!\n".format(reflib_name))

		return False

	# mkay, let's load the requested renderer.
	# Q2PORT: the renderer is a python module, imported directly in place of Sys_LoadLibrary
	from ref_gl import gl_rmain

	# fill in the struct exported to the renderer.
	# FIXME: Do we really need all these?
	ri = ref.refimport_t()
	ri.Cmd_AddCommand = cmdparser.Cmd_AddCommand
	ri.Cmd_Argc = cmdparser.Cmd_Argc
	ri.Cmd_Argv = cmdparser.Cmd_Argv
	ri.Cmd_ExecuteText = cmdparser.Cbuf_ExecuteText
	ri.Cmd_RemoveCommand = cmdparser.Cmd_RemoveCommand
	ri.Cvar_Get = cvar.Cvar_Get
	ri.Cvar_Set = cvar.Cvar_Set
	ri.Cvar_SetValue = cvar.Cvar_SetValue
	ri.FS_FreeFile = filesystem.FS_FreeFile
	ri.FS_Gamedir = filesystem.FS_Gamedir
	ri.FS_LoadFile = filesystem.FS_LoadFile
	ri.Sys_Error = clientserver.Com_Error
	ri.Vid_GetModeInfo = VID_GetModeInfo
	from client.menu import videomenu as vid_menu # imported here, vid_menu needs client.menu fully loaded
	ri.Vid_MenuInit = vid_menu.VID_MenuInit
	# Q2PORT: id's refimport fields, the old renderer (ref_gl) reads them
	def VID_Printf (print_level, msg):

		if print_level == shared.PRINT_ALL:
			clientserver.Com_Printf (str(msg))
		else:
			clientserver.Com_DPrintf (str(msg))

	def VID_Error (err_level, msg):

		clientserver.Com_Error (err_level, str(msg))

	ri.Com_VPrintf = clientserver.Com_VPrintf
	ri.Con_Printf = VID_Printf
	ri.Vid_NewWindow = VID_NewWindow

	# exchange our export struct with the renderers import struct.
	re = gl_rmain.GetRefAPI(ri)

	# declare the refresher as active.
	ref_active = True

	# let's check if we've got a compatible renderer.
	if re.api_version is not None and re.api_version != ref.API_VERSION: # API_VERSION

		clientserver.Com_Printf("{} has incompatible api_version {}!\n".format(reflib_name, re.api_version))

		VID_ShutdownRenderer()

		return False
	elif False: # re.framework_version != GLimp_GetFrameworkVersion(), the old renderer has no framework_version

		clientserver.Com_Printf("{} has incompatible sdl_version {}!\n".format(reflib_name, re.framework_version))

		VID_ShutdownRenderer()

		return False

	# everything seems okay, initialize it.
	# Q2PORT: id's re.Init(0, 0)
	if re.Init( 0, 0 ) == -1:

		VID_ShutdownRenderer()

		clientserver.Com_Printf("ERROR: Loading {} as rendering backend failed.\n".format(reflib_name))
		clientserver.Com_Printf("------------------------------------\n\n")

		return False

	# ensure that all key states are cleared
	cl_keyboard.Key_MarkAllUp()

	clientserver.Com_Printf("Successfully loaded {} as rendering backend.\n".format(reflib_name))
	clientserver.Com_Printf("------------------------------------\n\n")

	return True

"""
 * Checks if a renderer changes was requested and executes it.
 * Inclusive fallback through all renderers. :)
"""
def VID_CheckChanges(): #void

	global restart_state
	#static const char *r_order[] = {
	r_order = [
		"gl3",
		"gles3",
		"gl1",
		"gles1",
		"soft"
	]
	r_order_len = len(r_order) #ARRLEN(r_order)

	# hack around renderers that still abuse vid_fullscreen
	# to communicate restart requests to the client.
	#ref_restart_t rs;
	rs = 0

	if restart_state == 0: # RESTART_UNDEF

		if vid_fullscreen.modified:

			rs = 2 # RESTART_FULL
			vid_fullscreen.modified = False
		else:

			rs = 0 # RESTART_NO
	else:

		rs = restart_state
		restart_state = 0 # RESTART_NO

	if rs == 2: # RESTART_FULL

		# stop sound, because the clients blocks while
		# we're reloading the renderer. The sound system
		# would screw up its internal timings.
		snd_dma.S_StopAllSounds()

		# reset the client side of the renderer state.
		cl_main.cl.refresh_prepped = False
		cl_main.cl.cinematicpalette_active = False

		# more or less blocks the client.
		cl_main.cls.disable_screen = True

		# mkay, let's try our luck.
		while not VID_LoadRenderer():

			next_test = 0

			for i in range(r_order_len):

				if vid_renderer.string == r_order[i]:

					next_test = i + 1
					break

			if next_test == r_order_len:

				clientserver.Com_Error(shared.ERR_FATAL, "No usable renderer found!\n")
				return

			clientserver.Com_Printf("Retrying with {}...\n".format(r_order[next_test]))
			cvar.Cvar_Set("vid_renderer", r_order[next_test])

		# unblock the client.
		cl_main.cls.disable_screen = False

	elif rs == 1: # RESTART_PARTIAL

		cl_main.cl.refresh_prepped = False

"""
 * Initializes the video stuff.
"""
def VID_Init(): #void

	global vid_gamma, vid_fullscreen, vid_renderer

	# console variables
	vid_gamma = cvar.Cvar_Get( "vid_gamma", "1", shared.CVAR_ARCHIVE )
	vid_fullscreen = cvar.Cvar_Get( "vid_fullscreen", "0", shared.CVAR_ARCHIVE )
	# Q2PORT: the port has one renderer, gl1
	vid_renderer = cvar.Cvar_Get( "vid_renderer", "gl1", shared.CVAR_ARCHIVE )

	# commands
	cmdparser.Cmd_AddCommand ("vid_restart", VID_Restart_f)
	cmdparser.Cmd_AddCommand ("vid_listmodes", VID_ListModes_f)
	cmdparser.Cmd_AddCommand ("r_listmodes", VID_ListModes_f) # more consistent with r_mode

	# initializes the video backend. This is NOT the renderer
	# itself, just the client side support stuff!
	if not glimp_sdl2.GLimp_Init():

		clientserver.Com_Error(shared.ERR_FATAL, "Couldn't initialize the graphics subsystem!\n")

	# load the renderer and get things going.
	VID_CheckChanges()

"""
 * Shuts the video stuff down.
"""
def VID_Shutdown(): #void

	VID_ShutdownRenderer()
	glimp_sdl2.GLimp_Shutdown()

"""
** VID_NewWindow
"""
def VID_NewWindow ( width, height): #int, int

	viddef.width  = width
	viddef.height = height

# ----

# Wrappers for the functions provided by the renderer libs.
# =========================================================

def R_BeginRegistration(map_: str): #const char *

	if ref_active:

		re.BeginRegistration(map_)

def R_RegisterModel(name: str): #const char * (returns struct model_s*)

	if ref_active:

		return re.RegisterModel(name)


	return None

def R_RegisterSkin(name: str): #const char * (returns struct image_s*)

	if ref_active:

		return re.RegisterSkin(name)


	return None

def R_SetSky(name: str, rotate: float, axis): #const char *, float, vec3_t

	if ref_active:

		re.SetSky(name, rotate, axis)

def R_EndRegistration(): #void

	if ref_active:

		re.EndRegistration()

def R_RenderFrame(fd): #refdef_t *

	if ref_active:

		re.RenderFrame(fd)

def Draw_FindPic(name: str): #const char * (returns struct image_s*)

	if ref_active:

		return re.DrawFindPic(name)


	return None

def Draw_GetPicSize(name: str): #int *, int *, const char *

	# Q2PORT: returns (w, h) instead of filling w and h; (0, 0) if the renderer isn't up

	if ref_active:

		return re.DrawGetPicSize(name)


	return 0, 0

def Draw_StretchPic(x: int, y: int, w: int, h: int, name: str): #int, int, int, int, const char *

	if ref_active:

		re.DrawStretchPic(x, y, w, h, name)

def Draw_PicScaled(x: int, y: int, pic: str, factor: float): #int, int, const char *, float

	if ref_active:

		re.DrawPicScaled(x, y, pic, factor)

def Draw_PicScaledCol(x: int, y: int, pic: str, factor: float, color): #int, int, const char *, float, const float[3]

	if ref_active:

		if re.DrawPicScaledCol:

			re.DrawPicScaledCol(x, y, pic, factor, color)

		else:

			re.DrawPicScaled(x, y, pic, factor)

def Draw_CharScaled(x: int, y: int, num: int, scale: float): #int, int, int, float

	if ref_active:

		re.DrawCharScaled(x, y, num, scale)

def Draw_TileClear(x: int, y: int, w: int, h: int, name: str): #int, int, int, int, const char *

	if ref_active:

		re.DrawTileClear(x, y, w, h, name)

def Draw_Fill(x: int, y: int, w: int, h: int, c: int): #int, int, int, int

	if ref_active:

		re.DrawFill(x, y, w, h, c)

def Draw_FadeScreen(): #void

	if ref_active:

		re.DrawFadeScreen()

def Draw_StretchRaw(x: int, y: int, w: int, h: int, cols: int, rows: int, data, bits: int): #int, int, int, int, int, int, const byte *, int

	if ref_active:

		re.DrawStretchRaw(x, y, w, h, cols, rows, data) # Q2PORT: id's renderer takes 8-bit data only (no bits)

def R_SetPalette(palette): #const unsigned char *

	if ref_active:

		re.CinematicSetPalette(palette) # Q2PORT: id's name for SetPalette

def R_BeginFrame(camera_separation: float): #float

	if ref_active:

		re.BeginFrame(camera_separation)

def R_EndWorldRenderpass()->bool: #void (returns qboolean)

	if ref_active:

		return True # Q2PORT: re.EndWorldRenderpass(); id's renderer has no render passes


	return False

def R_EndFrame(): #void

	if ref_active:

		re.EndFrame()

def R_IsVSyncActive()->bool: #void (returns qboolean)

	if ref_active:

		return False # Q2PORT: re.IsVSyncActive(); id's renderer doesn't report it


	return False

def GLimp_GetRefreshRate()->float: #void (returns float)

	# Q2PORT: from glimp_sdl2.c. Only called while R_IsVSyncActive(),
	# which id's renderer never is
	return glimp_sdl2.GLimp_GetRefreshRate()
