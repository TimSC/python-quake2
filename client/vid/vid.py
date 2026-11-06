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

from linux import vid_so

"""
#include <assert.h>
#include <errno.h>

#include "../../client/header/client.h"
"""

# Q2PORT: only the renderer wrappers of vid.c are ported so far (the client
# needs them); the rest of vid.c is group 14. Until then the renderer is
# id's: re and ref_active are linux/vid_so.py's re and reflib_active, and
# where Yamagi's refexport_t differs from id's the wrapper says so.

vid_renderer = None #cvar_t *, Q2PORT: registered in linux/vid_so.py's VID_Init until group 14

# ----

# Wrappers for the functions provided by the renderer libs.
# =========================================================

def R_BeginRegistration(map_: str): #const char *

	if vid_so.reflib_active:

		vid_so.re.BeginRegistration(map_)

def R_RegisterModel(name: str): #const char * (returns struct model_s*)

	if vid_so.reflib_active:

		return vid_so.re.RegisterModel(name)


	return None

def R_RegisterSkin(name: str): #const char * (returns struct image_s*)

	if vid_so.reflib_active:

		return vid_so.re.RegisterSkin(name)


	return None

def R_SetSky(name: str, rotate: float, axis): #const char *, float, vec3_t

	if vid_so.reflib_active:

		vid_so.re.SetSky(name, rotate, axis)

def R_EndRegistration(): #void

	if vid_so.reflib_active:

		vid_so.re.EndRegistration()

def R_RenderFrame(fd): #refdef_t *

	if vid_so.reflib_active:

		vid_so.re.RenderFrame(fd)

def Draw_FindPic(name: str): #const char * (returns struct image_s*)

	if vid_so.reflib_active:

		return vid_so.re.DrawFindPic(name)


	return None

def Draw_GetPicSize(name: str): #int *, int *, const char *

	# Q2PORT: returns (w, h) instead of filling w and h; (0, 0) if the renderer isn't up

	if vid_so.reflib_active:

		return vid_so.re.DrawGetPicSize(name)


	return 0, 0

def Draw_StretchPic(x: int, y: int, w: int, h: int, name: str): #int, int, int, int, const char *

	if vid_so.reflib_active:

		vid_so.re.DrawStretchPic(x, y, w, h, name)

def Draw_PicScaled(x: int, y: int, pic: str, factor: float): #int, int, const char *, float

	if vid_so.reflib_active:

		vid_so.re.DrawPicScaled(x, y, pic, factor)

def Draw_PicScaledCol(x: int, y: int, pic: str, factor: float, color): #int, int, const char *, float, const float[3]

	if vid_so.reflib_active:

		if vid_so.re.DrawPicScaledCol:

			vid_so.re.DrawPicScaledCol(x, y, pic, factor, color)

		else:

			vid_so.re.DrawPicScaled(x, y, pic, factor)

def Draw_CharScaled(x: int, y: int, num: int, scale: float): #int, int, int, float

	if vid_so.reflib_active:

		vid_so.re.DrawCharScaled(x, y, num, scale)

def Draw_TileClear(x: int, y: int, w: int, h: int, name: str): #int, int, int, int, const char *

	if vid_so.reflib_active:

		vid_so.re.DrawTileClear(x, y, w, h, name)

def Draw_Fill(x: int, y: int, w: int, h: int, c: int): #int, int, int, int, int

	if vid_so.reflib_active:

		vid_so.re.DrawFill(x, y, w, h, c)

def Draw_FadeScreen(): #void

	if vid_so.reflib_active:

		vid_so.re.DrawFadeScreen()

def Draw_StretchRaw(x: int, y: int, w: int, h: int, cols: int, rows: int, data, bits: int): #int, int, int, int, int, int, const byte *, int

	if vid_so.reflib_active:

		vid_so.re.DrawStretchRaw(x, y, w, h, cols, rows, data) # Q2PORT: id's renderer takes 8-bit data only (no bits)

def R_SetPalette(palette): #const unsigned char *

	if vid_so.reflib_active:

		vid_so.re.CinematicSetPalette(palette) # Q2PORT: id's name for SetPalette

def R_BeginFrame(camera_separation: float): #float

	if vid_so.reflib_active:

		vid_so.re.BeginFrame(camera_separation)

def R_EndWorldRenderpass()->bool: #void (returns qboolean)

	if vid_so.reflib_active:

		return True # Q2PORT: re.EndWorldRenderpass(); id's renderer has no render passes


	return False

def R_EndFrame(): #void

	if vid_so.reflib_active:

		vid_so.re.EndFrame()

def R_IsVSyncActive()->bool: #void (returns qboolean)

	if vid_so.reflib_active:

		return False # Q2PORT: re.IsVSyncActive(); id's renderer doesn't report it


	return False

def GLimp_GetRefreshRate()->float: #void (returns float)

	# Q2PORT: from glimp_sdl2.c (group 14). Only called while R_IsVSyncActive(),
	# which id's renderer never is
	return 60.0

def VID_HasRenderer(renderer: str)->bool: #const char * (returns qboolean)

	# Q2PORT: the C looks for the renderer's library (ref_<name>.so); the port
	# has one renderer built in, id's, which stands for gl1 (group 14)
	return renderer == "gl1"
