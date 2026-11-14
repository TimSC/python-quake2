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

import os

from PIL import Image

from client import cl_main
from client.sound import sound as sound_c
from client import cl_keyboard
from client import cl_tempentities
from client import ref
from client.refresh import renderer
from client.vid.header import ref as ref_h
from client.vid import glimp_sdl2
from backends.generic import misc
from common import cvar
from common import clientserver
from common import cmdparser
from common import filesystem
from common.header import shared
from common.shared import shared as shared_c
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

#ifdef USE_ZLIB
#include <zlib.h>
#else
#include "../../common/unzip/miniz/miniz.h"
#endif
"""
# Q2PORT: stb_image_write (and compress_for_stbiw, its zlib hook for PNGs) is
# Pillow, which writes the same four formats

"""
 * Writes a screenshot. This function is called with raw image data of
 * width*height pixels, each pixel has comp bytes. Must be 3 or 4, for
 * RGB or RGBA. The pixels must be given row-wise, stating at the top
 * left.
"""
def VID_WriteScreenshot(width: int, height: int, comp: int, data): #int, int, int, const void *

	#char picname[80];
	#char checkname[MAX_OSPATH];
	success = 0 #int i, success = 0;
	supportedFormats = [ "tga", "bmp", "png", "jpg" ] #static const char* supportedFormats[]
	numFormats = len(supportedFormats) #static const int numFormats = ARRLEN(supportedFormats);
	format_ = 0 # 0=tga, 1=bmp, 2=png, 3=jpg
	quality = 85
	argc = cmdparser.Cmd_Argc()
	gameDir = filesystem.FS_Gamedir()

	# FS_InitFilesystem() made sure the screenshots dir exists./

	if argc > 1:

		maybeFormat = cmdparser.Cmd_Argv(1)

		for i in range(numFormats):

			if maybeFormat.lower() == supportedFormats[i]: # Q_stricmp

				format_ = i
				break


		else: # if (i == numFormats)

			clientserver.Com_Printf("the (optional) second argument to 'screenshot' is the format, one of \"tga\", \"bmp\", \"png\", \"jpg\"\n")
			return


		if argc > 2:

			q = cmdparser.Cmd_Argv(2)

			for c in q:

				if c < '0' or c > '9':

					clientserver.Com_Printf("The (optional!) third argument to 'screenshot' is jpg quality, a number between 1 and 100\n")
					clientserver.Com_Printf("  or png compression level, between 0 and 9!\n")

					return



			quality = shared_c.atoi(q)

			if format_ == 2: # png

				if quality < 0:

					quality = 0

				elif quality > 9:

					quality = 9


			elif format_ == 3: # jpg

				if quality < 1:

					quality = 1

				elif quality > 100:

					quality = 100





	# find a file name to save it to
	for i in range(10000): # for (i = 0; i <= 9999; i++)

		checkname = "{}/scrnshot/q2_{:04d}.{}".format(gameDir, i, supportedFormats[format_])

		if not os.path.exists(checkname): # f = Q_fopen(checkname, "rb"); if (!f)

			picname = "q2_{:04d}.{}".format(i, supportedFormats[format_])
			break # file doesn't exist


	else: # if (i == 10000)

		clientserver.Com_Printf("SCR_ScreenShot_f: Couldn't create a file\n")
		return


	img = Image.frombytes("RGB" if comp == 3 else "RGBA", (width, height), bytes(data))

	try: # Q2PORT: Pillow raises where stbi_write_*() returns 0

		if format_ == 0:

			img.save(checkname, "TGA", compression="tga_rle") # stbi_write_tga(), RLE by default

		elif format_ == 1:

			img.save(checkname, "BMP") # stbi_write_bmp()

		elif format_ == 2:

			img.save(checkname, "PNG", compress_level=quality if quality < 10 else 7) # stbi_write_png()

		elif format_ == 3:

			img.convert("RGB").save(checkname, "JPEG", quality=quality) # stbi_write_jpg()


		success = 1

	except (OSError, ValueError):

		success = 0


	if success:

		clientserver.Com_Printf("Wrote %s\n", picname)

	else:

		clientserver.Com_Printf("SCR_ScreenShot_f: Couldn't write %s\n", picname)


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

# The loaded renderer's entry points (client/refresh/renderer.py), None when none is loaded.
re: renderer.Renderer | None = None

# Handle / pointer the the loaded renderer DLL.
reflib_handle = None #void *, the renderer is a python module

# Is a renderer loaded and active?
ref_active = False #qboolean

# Renderer restart type requested.
restart_state = ref_h.ref_restart_t.RESTART_UNDEF #ref_restart_t

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

	# Sys_IsFile(reflib_path), Q2PORT: the port has the built in renderers (gl1, gl3)
	# as python modules, they are always available
	return renderer in ("gl1", "gl3")

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

	if restart_state == ref_h.ref_restart_t.RESTART_UNDEF:

		vid_fullscreen.modified = True
	else:

		restart_state = ref_h.ref_restart_t.RESTART_FULL

"""
 * Shuts the renderer down and unloads it.
"""
def VID_ShutdownRenderer(): #void

	global re, reflib_handle, ref_active

	if ref_active:

		# shut down the renderer
		re.shutdown()
		glimp_sdl2.GLimp_ShutdownGraphics()
		# Sys_FreeLibrary(reflib_handle); the renderer is a python module
		reflib_handle = None
		re = None

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
	# Q2PORT: the renderer is a python module, imported in place of Sys_LoadLibrary
	from client.refresh import ref_dispatch
	gl_rmain = ref_dispatch.get_renderer()

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
	ri.Vid_WriteScreenshot = VID_WriteScreenshot
	ri.Vid_RequestRestart = VID_RequestRestart
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
	ri.GLimp_InitGraphics = glimp_sdl2.GLimp_InitGraphics # Q2PORT: Yamagi's refimport, for gl3
	ri.GLimp_GetDesktopMode = glimp_sdl2.GLimp_GetDesktopMode

	# exchange our export struct with the renderers import struct.
	re = gl_rmain.GetRefAPI(ri)

	# declare the refresher as active.
	ref_active = True

	# let's check if we've got a compatible renderer.
	if re.api_version != renderer.API_VERSION:

		clientserver.Com_Printf("{} has incompatible api_version {}!\n".format(reflib_name, re.api_version))

		VID_ShutdownRenderer()

		return False

	# everything seems okay, initialize it.
	if not re.init():

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

	if restart_state == ref_h.ref_restart_t.RESTART_UNDEF:

		if vid_fullscreen.modified:

			rs = ref_h.ref_restart_t.RESTART_FULL
			vid_fullscreen.modified = False
		else:

			rs = ref_h.ref_restart_t.RESTART_NO
	else:

		rs = restart_state
		restart_state = ref_h.ref_restart_t.RESTART_NO

	if rs == ref_h.ref_restart_t.RESTART_FULL:

		# stop sound, because the clients blocks while
		# we're reloading the renderer. The sound system
		# would screw up its internal timings.
		sound_c.S_StopAllSounds()

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

	elif rs == ref_h.ref_restart_t.RESTART_PARTIAL:

		cl_main.cl.refresh_prepped = False

"""
 * Initializes the video stuff.
"""
def VID_Init(): #void

	global vid_gamma, vid_fullscreen, vid_renderer

	# console variables
	vid_gamma = cvar.Cvar_Get( "vid_gamma", "1", shared.CVAR_ARCHIVE )
	vid_fullscreen = cvar.Cvar_Get( "vid_fullscreen", "0", shared.CVAR_ARCHIVE )
	# Q2PORT: the port has two built in renderers, gl1 (default, verified) and gl3 (group 16).
	# The C default is gl3 (vid.c), but the port ships gl1 as the default. Q2_RENDERER is a
	# test hook that forces a specific renderer; it must Cvar_Set because other modules
	# (videomenu, cl_cin) register the cvar with the gl1 default before VID_Init.
	import os
	_env_renderer = os.environ.get ("Q2_RENDERER", "")
	vid_renderer = cvar.Cvar_Get( "vid_renderer", "gl1", shared.CVAR_ARCHIVE )
	if _env_renderer:
		cvar.Cvar_Set( "vid_renderer", _env_renderer )

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

		re.begin_registration(map_)

def R_RegisterModel(name: str): #const char * (returns struct model_s*)

	if ref_active:

		return re.register_model(name)


	return None

def R_RegisterSkin(name: str): #const char * (returns struct image_s*)

	if ref_active:

		return re.register_skin(name)


	return None

def R_SetSky(name: str, rotate: float, axis): #const char *, float, vec3_t

	if ref_active:

		re.set_sky(name, rotate, axis)

def R_EndRegistration(): #void

	if ref_active:

		re.end_registration()

def R_RenderFrame(fd): #refdef_t *

	if ref_active:

		re.render_frame(fd)

def Draw_FindPic(name: str): #const char * (returns struct image_s*)

	if ref_active:

		return re.find_pic(name)


	return None

def Draw_GetPicSize(name: str): #int *, int *, const char *

	# Q2PORT: returns (w, h) instead of filling w and h; (0, 0) if the renderer isn't up

	if ref_active:

		return re.pic_size(name)


	return 0, 0

def Draw_StretchPic(x: int, y: int, w: int, h: int, name: str): #int, int, int, int, const char *

	if ref_active:

		re.draw_stretch_pic(x, y, w, h, name)

def Draw_PicScaled(x: int, y: int, pic: str, factor: float): #int, int, const char *, float

	if ref_active:

		re.draw_pic_scaled(x, y, pic, factor)

def Draw_PicScaledCol(x: int, y: int, pic: str, factor: float, color): #int, int, const char *, float, const float[3]

	if ref_active:

		re.draw_pic_scaled_col(x, y, pic, factor, color)

def Draw_CharScaled(x: int, y: int, num: int, scale: float): #int, int, int, float

	if ref_active:

		re.draw_char_scaled(x, y, num, scale)

def Draw_TileClear(x: int, y: int, w: int, h: int, name: str): #int, int, int, int, const char *

	if ref_active:

		re.draw_tile_clear(x, y, w, h, name)

def Draw_Fill(x: int, y: int, w: int, h: int, c: int): #int, int, int, int

	if ref_active:

		re.draw_fill(x, y, w, h, c)

def Draw_FadeScreen(): #void

	if ref_active:

		re.draw_fade_screen()

def Draw_StretchRaw(x: int, y: int, w: int, h: int, cols: int, rows: int, data, bits: int): #int, int, int, int, int, int, const byte *, int

	if ref_active:

		re.draw_stretch_raw(x, y, w, h, cols, rows, data) # the cinematics are 8-bit

def R_SetPalette(palette): #const unsigned char *

	if ref_active:

		re.set_palette(palette)

def R_BeginFrame(camera_separation: float): #float

	if ref_active:

		re.begin_frame(camera_separation)

def R_EndWorldRenderpass()->bool: #void (returns qboolean)

	if ref_active:

		return re.end_world_renderpass()


	return False

def R_EndFrame(): #void

	if ref_active:

		re.end_frame()

def R_IsVSyncActive()->bool: #void (returns qboolean)

	if ref_active:

		return re.is_vsync_active()


	return False

def GLimp_GetRefreshRate()->float: #void (returns float)

	# Q2PORT: from glimp_sdl2.c. Only called while R_IsVSyncActive(),
	# which id's renderer never is
	return glimp_sdl2.GLimp_GetRefreshRate()
