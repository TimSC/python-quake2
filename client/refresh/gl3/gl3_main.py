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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * Refresher setup and main part of the frame generation, for OpenGL3
 *
 * =======================================================================
"""

from __future__ import annotations

import copy
import ctypes
import math

import numpy as np
import OpenGL.GL as GL
from OpenGL.GL.EXT.texture_filter_anisotropic import GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT

from common import clientserver
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from client import ref
from client.refresh import ref_shared
from client.refresh.files import pcx as files_pcx
from client.refresh.files import models as files_models
from client.refresh.files import surf as files_surf
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model
from client.refresh.gl3.header import hmm
from client.refresh.gl3 import gl3_draw, gl3_image, gl3_light, gl3_mesh, gl3_misc, gl3_model, gl3_sdl, gl3_shaders, gl3_surf, gl3_warp

#include "../ref_shared.h"
#include "header/local.h"

#define HANDMADE_MATH_IMPLEMENTATION
#include "header/HandmadeMath.h"

#define DG_DYNARR_IMPLEMENTATION
#include "header/DG_dynarr.h"

REF_VERSION = "Yamagi Quake II OpenGL3 Refresher"

ri = None #refimport_t

gl3config = local.gl3config_t() #gl3config_t
gl3state = local.gl3state_t() #gl3state_t

# unsigned gl3_rawpalette[256]; Q2PORT: a uint32 numpy array, RGBA bytes in memory order
gl3_rawpalette = np.zeros(256, dtype=np.uint32)

gl3_worldmodel = None #gl3model_t *

gl3depthmin, gl3depthmax = 0.0, 1.0 #float

frustum = [] #cplane_t [4]
for i in range(4):
	frustum.append(shared.cplane_t())

# view origin
vup = np.zeros((3,), dtype=np.float32) #vec3_t
vpn = np.zeros((3,), dtype=np.float32) #vec3_t
vright = np.zeros((3,), dtype=np.float32) #vec3_t
gl3_origin = np.zeros((3,), dtype=np.float32) #vec3_t

gl3_visframecount = 0 #int, bumped when going to a new PVS
gl3_framecount = 0 #int, used for dlight push checking

c_brush_polys, c_alias_polys = 0, 0 #int

v_blend = [0.0, 0.0, 0.0, 0.0] #static float [4], final blending color

gl3_viewcluster, gl3_viewcluster2, gl3_oldviewcluster, gl3_oldviewcluster2 = 0, 0, 0, 0 #int

gl3_identityMat4 = local.gl3_identityMat4 #const hmm_mat4

gl_msaa_samples = None #cvar_t *
r_vsync = None #cvar_t *
r_retexturing = None #cvar_t *
r_scale8bittextures = None #cvar_t *
vid_fullscreen = None #cvar_t *
r_mode = None #cvar_t *
r_customwidth = None #cvar_t *
r_customheight = None #cvar_t *
vid_gamma = None #cvar_t *
gl_anisotropic = None #cvar_t *
gl_texturemode = None #cvar_t *
gl_drawbuffer = None #cvar_t *
r_clear = None #cvar_t *
gl3_particle_size = None #cvar_t *
gl3_particle_fade_factor = None #cvar_t *
gl3_particle_square = None #cvar_t *
gl3_colorlight = None #cvar_t *
gl_polyblend = None #cvar_t *

gl_lefthand = None #cvar_t *
r_gunfov = None #cvar_t *
r_farsee = None #cvar_t *

gl3_intensity = None #cvar_t *
gl3_intensity_2D = None #cvar_t *
r_lightlevel = None #cvar_t *
gl3_overbrightbits = None #cvar_t *

r_norefresh = None #cvar_t *
r_drawentities = None #cvar_t *
r_drawworld = None #cvar_t *
gl_nolerp_list = None #cvar_t *
r_lerp_list = None #cvar_t *
r_2D_unfiltered = None #cvar_t *
r_videos_unfiltered = None #cvar_t *
gl_nobind = None #cvar_t *
gl_showtris = None #cvar_t *
r_lockpvs = None #cvar_t *
r_novis = None #cvar_t *
r_speeds = None #cvar_t *
gl_finish = None #cvar_t *

r_cull = None #cvar_t *
gl_zfix = None #cvar_t *
r_fullbright = None #cvar_t *
r_modulate = None #cvar_t *
gl_lightmap = None #cvar_t *
gl_shadows = None #cvar_t *
gl3_debugcontext = None #cvar_t *
r_fixsurfsky = None #cvar_t *
r_palettedtexture = None #cvar_t *
r_validation = None #cvar_t *
gl3_usefbo = None #cvar_t *

gl3_show_draw_stats = None #cvar_t *

gl_znear = None #static cvar_t *

# DA_TYPEDEF(gl3_3D_vtx_t, Vtx3DArray_t);
# DA_TYPEDEF(GLushort, UShortArray_t);
# DA_TYPEDEF(gl3drawCmd_t, DrawCommandArray_t);
# DA_TYPEDEF(hmm_mat4, Mat4Array_t);
# dynamic arrays to batch all consecutive 3D draws (with gl3_3D_vtx_t) with same texture to reduce drawcalls
# Q2PORT: vtxBuf is a list of gl3_3D_vtx_t numpy arrays (vtxBufCount vertices
# in all), joined when the batch is drawn; idxBuf is a list of ints
vtxBuf = [] #static Vtx3DArray_t
vtxBufCount = 0
idxBuf = [] #static UShortArray_t
drawCmds = [] #static DrawCommandArray_t
transModelMats = [] #static Mat4Array_t

UINT16_MAX = 65535

# the 2D/3D state of the C's vid (ref_shared.h: viddef_t vid)
class viddef_t(object):

	def __init__(self):

		self.width, self.height = 0, 0 #int, coordinates from main game

vid = viddef_t() #viddef_t

r_newrefdef = ref.refdef_t() #refdef_t

"""
 Yaw-Pitch-Roll
 equivalent to R_z * R_y * R_x where R_x is the trans matrix for rotating around X axis for aroundXdeg
"""
def rotAroundAxisZYX(aroundZdeg, aroundYdeg, aroundXdeg): #float, float, float (returns hmm_mat4)

	# Naming of variables is consistent with http://planning.cs.uiuc.edu/node102.html
	# and https://de.wikipedia.org/wiki/Roll-Nick-Gier-Winkel#.E2.80.9EZY.E2.80.B2X.E2.80.B3-Konvention.E2.80.9C
	alpha = hmm.HMM_ToRadians(aroundZdeg)
	beta = hmm.HMM_ToRadians(aroundYdeg)
	gamma = hmm.HMM_ToRadians(aroundXdeg)

	sinA = hmm.HMM_SinF(alpha)
	cosA = hmm.HMM_CosF(alpha)
	# TODO: or sincosf(alpha, &sinA, &cosA); ?? (not a standard function)
	sinB = hmm.HMM_SinF(beta)
	cosB = hmm.HMM_CosF(beta)
	sinG = hmm.HMM_SinF(gamma)
	cosG = hmm.HMM_CosF(gamma)

	ret = np.array([
		[ cosA*cosB,                  sinA*cosB,                   -sinB,    0 ], # first *column*
		[ cosA*sinB*sinG - sinA*cosG, sinA*sinB*sinG + cosA*cosG, cosB*sinG, 0 ],
		[ cosA*sinB*cosG + sinA*sinG, sinA*sinB*cosG - cosA*sinG, cosB*cosG, 0 ],
		[  0,                          0,                          0,        1 ]
	], dtype=np.float32)

	return ret

def GL3_RotateUni3DforEntity(e): #entity_t *

	# angles: pitch (around y), yaw (around z), roll (around x)
	# rot matrices to be multiplied in order Z, Y, X (yaw, pitch, roll)
	transMat = rotAroundAxisZYX(e.angles[1], -e.angles[0], -e.angles[2])

	for i in range(3):

		transMat[3][i] = e.origin[i] # set translation

	modelMat = gl3state.uni3DData[local.UNI3D_MODEL:local.UNI3D_MODEL + 16].reshape(4, 4)
	gl3state.uni3DData[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = hmm.HMM_MultiplyMat4(modelMat, transMat).flatten()

	gl3_shaders.GL3_UpdateUBO3D()

"""
 if replaceTransModelMat is true, the existing value of drawCmd->transModelMat
 is ignored and it's replaced with the one calculated here (otherwise they're multiplied)
"""
def GL3_RotateForEntity(e, drawCmd): #entity_t *, gl3drawCmd_t*

	# TODO: shortcut for "not rotated at all"?

	# angles: pitch (around y), yaw (around z), roll (around x)
	# rot matrices to be multiplied in order Z, Y, X (yaw, pitch, roll)
	transMat = rotAroundAxisZYX(e.angles[1], -e.angles[0], -e.angles[2])

	for i in range(3):

		transMat[3][i] = e.origin[i] # set translation

	GL3_SetDrawCmdTransMatrix(drawCmd, transMat)

def GL3_Strings(show_ext): #qboolean

	Printf_Ext = clientserver.Com_Printf if show_ext else clientserver.Com_DPrintf
	#GLint i, numExtensions;

	clientserver.Com_Printf("GL_VENDOR: {}\n".format(gl3config.vendor_string))
	clientserver.Com_Printf("GL_RENDERER: {}\n".format(gl3config.renderer_string))
	clientserver.Com_Printf("GL_VERSION: {}\n".format(gl3config.version_string))
	clientserver.Com_Printf("GL_SHADING_LANGUAGE_VERSION: {}\n".format(gl3config.glsl_version_string))

	numExtensions = GL.glGetIntegerv(GL.GL_NUM_EXTENSIONS)

	Printf_Ext("GL_EXTENSIONS:")
	for i in range(numExtensions):

		Printf_Ext(" {}".format(GL.glGetStringi(GL.GL_EXTENSIONS, i).decode("ascii")))

	Printf_Ext("\n")

	clientserver.Com_Printf("GL_NUM_EXTENSIONS: {}\n".format(numExtensions))

def GL3_Strings_f(): #void

	GL3_Strings(True)

def GL3_Register(): #void

	global gl_lefthand, r_gunfov, r_farsee, gl_drawbuffer, r_vsync, gl_msaa_samples, r_retexturing, \
		r_scale8bittextures, gl3_debugcontext, r_mode, r_customwidth, r_customheight, gl3_particle_size, \
		gl3_particle_fade_factor, gl3_particle_square, gl3_colorlight, gl_polyblend, r_norefresh, \
		r_drawentities, r_drawworld, r_fullbright, r_fixsurfsky, r_palettedtexture, r_validation, \
		gl_nolerp_list, r_lerp_list, r_2D_unfiltered, r_videos_unfiltered, gl_nobind, gl_showtris, \
		gl_texturemode, gl_anisotropic, vid_fullscreen, vid_gamma, gl3_intensity, gl3_intensity_2D, \
		r_lightlevel, gl3_overbrightbits, gl_lightmap, gl_shadows, r_modulate, gl_zfix, r_clear, r_cull, \
		r_lockpvs, r_novis, r_speeds, gl_finish, gl_znear, gl3_usefbo, gl3_show_draw_stats

	gl_lefthand = ri.Cvar_Get("hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	r_gunfov = ri.Cvar_Get("r_gunfov", "80", shared.CVAR_ARCHIVE)
	r_farsee = ri.Cvar_Get("r_farsee", "0", shared.CVAR_LATCH | shared.CVAR_ARCHIVE)

	gl_drawbuffer = ri.Cvar_Get("gl_drawbuffer", "GL_BACK", 0)
	r_vsync = ri.Cvar_Get("r_vsync", "1", shared.CVAR_ARCHIVE)
	gl_msaa_samples = ri.Cvar_Get ( "r_msaa_samples", "0", shared.CVAR_ARCHIVE )
	r_retexturing = ri.Cvar_Get("r_retexturing", "1", shared.CVAR_ARCHIVE)
	r_scale8bittextures = ri.Cvar_Get("r_scale8bittextures", "0", shared.CVAR_ARCHIVE)
	gl3_debugcontext = ri.Cvar_Get("gl3_debugcontext", "0", 0)
	r_mode = ri.Cvar_Get("r_mode", "4", shared.CVAR_ARCHIVE)
	r_customwidth = ri.Cvar_Get("r_customwidth", "1024", shared.CVAR_ARCHIVE)
	r_customheight = ri.Cvar_Get("r_customheight", "768", shared.CVAR_ARCHIVE)
	gl3_particle_size = ri.Cvar_Get("gl3_particle_size", "40", shared.CVAR_ARCHIVE)
	gl3_particle_fade_factor = ri.Cvar_Get("gl3_particle_fade_factor", "1.2", shared.CVAR_ARCHIVE)
	gl3_particle_square = ri.Cvar_Get("gl3_particle_square", "0", shared.CVAR_ARCHIVE)
	# if set to 0, lights (from lightmaps, dynamic lights and on models) are white instead of colored
	gl3_colorlight = ri.Cvar_Get("gl3_colorlight", "1", shared.CVAR_ARCHIVE)
	gl_polyblend = ri.Cvar_Get("gl_polyblend", "1", shared.CVAR_ARCHIVE)

	r_norefresh = ri.Cvar_Get("r_norefresh", "0", 0)
	r_drawentities = ri.Cvar_Get("r_drawentities", "1", 0)
	r_drawworld = ri.Cvar_Get("r_drawworld", "1", 0)
	r_fullbright = ri.Cvar_Get("r_fullbright", "0", 0)
	r_fixsurfsky = ri.Cvar_Get("r_fixsurfsky", "0", shared.CVAR_ARCHIVE)
	r_palettedtexture = ri.Cvar_Get("r_palettedtexture", "0", 0)
	r_validation = ri.Cvar_Get("r_validation", "0", shared.CVAR_ARCHIVE)

	# don't bilerp characters and crosshairs
	gl_nolerp_list = ri.Cvar_Get("r_nolerp_list", "pics/conchars.pcx pics/ch1.pcx pics/ch2.pcx pics/ch3.pcx", shared.CVAR_ARCHIVE)
	# textures that should always be filtered, even if r_2D_unfiltered or an unfiltered gl mode is used
	r_lerp_list = ri.Cvar_Get("r_lerp_list", "", shared.CVAR_ARCHIVE)
	# don't bilerp any 2D elements
	r_2D_unfiltered = ri.Cvar_Get("r_2D_unfiltered", "0", shared.CVAR_ARCHIVE)
	# don't bilerp videos
	r_videos_unfiltered = ri.Cvar_Get("r_videos_unfiltered", "0", shared.CVAR_ARCHIVE)
	gl_nobind = ri.Cvar_Get("gl_nobind", "0", 0)
	gl_showtris = ri.Cvar_Get("gl_showtris", "0", 0)

	gl_texturemode = ri.Cvar_Get("gl_texturemode", "GL_LINEAR_MIPMAP_NEAREST", shared.CVAR_ARCHIVE)
	gl_anisotropic = ri.Cvar_Get("r_anisotropic", "0", shared.CVAR_ARCHIVE)

	vid_fullscreen = ri.Cvar_Get("vid_fullscreen", "0", shared.CVAR_ARCHIVE)
	vid_gamma = ri.Cvar_Get("vid_gamma", "1.2", shared.CVAR_ARCHIVE)
	gl3_intensity = ri.Cvar_Get("gl3_intensity", "1.5", shared.CVAR_ARCHIVE)
	gl3_intensity_2D = ri.Cvar_Get("gl3_intensity_2D", "1.5", shared.CVAR_ARCHIVE)

	r_lightlevel = ri.Cvar_Get("r_lightlevel", "0", 0)
	gl3_overbrightbits = ri.Cvar_Get("gl3_overbrightbits", "1.3", shared.CVAR_ARCHIVE)

	gl_lightmap = ri.Cvar_Get("r_lightmap", "0", 0)
	gl_shadows = ri.Cvar_Get("r_shadows", "0", shared.CVAR_ARCHIVE)

	r_modulate = ri.Cvar_Get("r_modulate", "1", shared.CVAR_ARCHIVE)
	gl_zfix = ri.Cvar_Get("gl_zfix", "0", 0)
	r_clear = ri.Cvar_Get("r_clear", "0", 0)
	r_cull = ri.Cvar_Get("r_cull", "1", 0)
	r_lockpvs = ri.Cvar_Get("r_lockpvs", "0", 0)
	r_novis = ri.Cvar_Get("r_novis", "0", 0)
	r_speeds = ri.Cvar_Get("r_speeds", "0", 0)
	gl_finish = ri.Cvar_Get("gl_finish", "0", shared.CVAR_ARCHIVE)
	gl_znear = ri.Cvar_Get("gl_znear", "4", shared.CVAR_ARCHIVE)

	gl3_usefbo = ri.Cvar_Get("gl3_usefbo", "1", shared.CVAR_ARCHIVE) # use framebuffer object for postprocess effects (water)

	gl3_show_draw_stats = ri.Cvar_Get("gl3_show_draw_stats", "0", shared.CVAR_ARCHIVE)

	"""
#if 0 // TODO!
	(the gl1 cvars of the C's #if 0 block are not ported, as in the C)
#endif // 0
	"""

	ri.Cmd_AddCommand("imagelist", gl3_image.GL3_ImageList_f)
	ri.Cmd_AddCommand("screenshot", gl3_misc.GL3_ScreenShot)
	ri.Cmd_AddCommand("modellist", gl3_model.GL3_Mod_Modellist_f)
	ri.Cmd_AddCommand("gl_strings", GL3_Strings_f)

"""
 * Changes the video mode
"""

# the following is only used in the next to functions,
# no need to put it in a header
rserr_ok = 0

rserr_invalid_mode = 1

rserr_unknown = 2

def SetMode_impl(pwidth, pheight, mode, fullscreen): #int *, int *, int, int (returns int, *pwidth, *pheight)

	clientserver.Com_Printf("Setting mode {}:".format(int(mode)))

	# mode -1 is not in the vid mode table - so we keep the values in pwidth
	#   and pheight and don't even try to look up the mode info
	if mode >= 0:

		ok, w, h = ri.Vid_GetModeInfo(int(mode))
		if not ok:

			clientserver.Com_Printf(" invalid mode\n")
			return rserr_invalid_mode, pwidth, pheight

		pwidth, pheight = w, h

	# We trying to get resolution from desktop
	if mode == -2:

		ok, w, h = ri.GLimp_GetDesktopMode()
		if not ok:

			clientserver.Com_Printf(" can't detect mode\n" )
			return rserr_invalid_mode, pwidth, pheight

		pwidth, pheight = w, h

	clientserver.Com_Printf(" {}x{} (vid_fullscreen {})\n".format(pwidth, pheight, int(fullscreen)))

	# Q2PORT: the C's GLimp_InitGraphics() can change the size through the
	# pointers; the port's returns only the result
	if not ri.GLimp_InitGraphics(int(fullscreen), pwidth, pheight):

		return rserr_invalid_mode, pwidth, pheight

	if mode == -2 or fullscreen:

		local.GL3_BindVBO(0)

	# This is totally obscure: For some strange reasons the renderer
	#   maintains two(!) representations of the resolution. One comes
	#   from the client and is saved in r_newrefdef. The other one
	#   is determined here and saved in vid. Several calculations take
	#   both representations into account.
	#
	#   The values will always be the same. The GLimp_InitGraphics()
	#   call above communicates the requested resolution to the client
	#   where it ends up in the vid subsystem and the vid system writes
	#   it into r_newrefdef.
	#
	#   We can't avoid the client roundtrip, because we can get the
	#   real size of the drawable (which can differ from the resolution
	#   due to high dpi awareness) only after the render context was
	#   created by GLimp_InitGraphics() and need to communicate it
	#   somehow to the client. So we just overwrite the values saved
	#   in vid with a call to GL3_GetDrawableSize(), just like the
	#   client does. This makes sure that both values are the same
	#   and everything is okay.
	#
	#   We also need to take the special case fullscreen window into
	#   account. With the fullscreen windows we cannot use the
	#   drawable size, it would scale all cases to the size of the
	#   window. Instead use the drawable size when the user wants
	#   native resolution (the fullscreen window fills the screen)
	#   and use the requested resolution in all other cases.
	if gl3_sdl.IsHighDPIaware:

		if vid_fullscreen.value != 2:

			pwidth, pheight = gl3_sdl.GL3_GetDrawableSize()

		else:

			if r_mode.value == -2:

				# User requested native resolution.
				pwidth, pheight = gl3_sdl.GL3_GetDrawableSize()

	return rserr_ok, pwidth, pheight

def GL3_SetMode(): #void (returns qboolean)

	#int err;
	#int fullscreen;

	fullscreen = int(vid_fullscreen.value)

	# a bit hackish approach to enable custom resolutions:
	#   Glimp_SetMode needs these values set for mode -1
	vid.width = int(r_customwidth.value)
	vid.height = int(r_customheight.value)

	err, vid.width, vid.height = SetMode_impl(vid.width, vid.height, r_mode.value, fullscreen)
	if err == rserr_ok:

		if r_mode.value == -1:

			gl3state.prev_mode = 4 # safe default for custom mode

		else:

			gl3state.prev_mode = int(r_mode.value)

	else:

		if err == rserr_invalid_mode:

			clientserver.Com_Printf("ref_gl3::GL3_SetMode() - invalid mode\n")

			if gl_msaa_samples.value != 0.0:

				clientserver.Com_Printf("gl_msaa_samples was {} - will try again with gl_msaa_samples = 0\n".format(int(gl_msaa_samples.value)))
				ri.Cvar_SetValue("r_msaa_samples", 0.0)
				gl_msaa_samples.modified = False

				err, vid.width, vid.height = SetMode_impl(vid.width, vid.height, r_mode.value, 0)
				if err == rserr_ok:

					return True

			if r_mode.value == gl3state.prev_mode:

				# trying again would result in a crash anyway, give up already
				# (this would happen if your initing fails at all and your resolution already was 640x480)
				return False

			ri.Cvar_SetValue("r_mode", gl3state.prev_mode)
			r_mode.modified = False

		# try setting it back to something safe
		err, vid.width, vid.height = SetMode_impl(vid.width, vid.height, gl3state.prev_mode, 0)
		if err != rserr_ok:

			clientserver.Com_Printf("ref_gl3::GL3_SetMode() - could not revert to safe mode\n")
			return False

	return True

def GL3_ResetClearColor(): #void

	# Q2PORT: the C's YQ2_GL3_GLES branch is not the desktop port
	GL.glClearColor(1, 0, 0.5, 0.5)

def GL3_Init(): #void (returns qboolean)

	global transModelMats

	#byte *colormap;

	shared_c.Swap_Init() # FIXME: for fucks sake, this doesn't have to be done at runtime!

	clientserver.Com_Printf("Refresh: " + REF_VERSION + "\n")
	clientserver.Com_Printf("Client: " + common_h.YQ2VERSION + "\n\n")

	# Q2PORT: the C's sizeof(float) != sizeof(GLfloat) check is moot here,
	# the port packs float32 numpy arrays

	files_pcx.GetPCXPalette (None, gl3_draw.d_8to24table)
	#free(colormap);

	transModelMats.clear() # da_clear(transModelMats)
	transModelMats.append(gl3_identityMat4) # element 0 is always the identity matrix

	GL3_Register()

	# set our "safe" mode
	gl3state.prev_mode = 4
	#gl_state.stereo_mode = gl1_stereo->value;

	# create the window and set up the context
	if not GL3_SetMode():

		clientserver.Com_Printf("ref_gl3::R_Init() - could not R_SetMode()\n")
		return False

	ri.Vid_MenuInit()

	# get our various GL strings
	# Q2PORT: PyOpenGL returns bytes
	gl3config.vendor_string = GL.glGetString(GL.GL_VENDOR).decode("ascii", "replace")
	gl3config.renderer_string = GL.glGetString(GL.GL_RENDERER).decode("ascii", "replace")
	gl3config.version_string = GL.glGetString(GL.GL_VERSION).decode("ascii", "replace")
	gl3config.glsl_version_string = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION).decode("ascii", "replace")

	clientserver.Com_Printf("\nOpenGL features:\n")
	GL3_Strings(False)

	"""
	if (gl_config.major_version < 3)
	{
		// if (gl_config.major_version == 3 && gl_config.minor_version < 2)
		{
			QGL_Shutdown();
			Com_Printf("Support for OpenGL 3.2 is not available\n");

			return false;
		}
	}
	"""

	clientserver.Com_Printf("\nProbing for OpenGL extensions:\n")


	# Anisotropic
	clientserver.Com_Printf(" - Anisotropic Filtering: ")

	if gl3config.anisotropic:

		gl3config.max_anisotropy = float(GL.glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT))

		clientserver.Com_Printf("Max level: {}x\n".format(int(gl3config.max_anisotropy)))

	else:

		gl3config.max_anisotropy = 0.0

		clientserver.Com_Printf("Not supported\n")

	if gl3config.debug_output:

		clientserver.Com_Printf(" - OpenGL Debug Output: Supported ")
		if gl3_debugcontext.value == 0.0:

			clientserver.Com_Printf("(but disabled with gl3_debugcontext = 0)\n")

		else:

			clientserver.Com_Printf("and enabled with gl3_debugcontext = {}\n".format(int(gl3_debugcontext.value)))

	else:

		clientserver.Com_Printf(" - OpenGL Debug Output: Not Supported\n")

	# generate texture handles for all possible lightmaps
	ids = GL.glGenTextures(local.MAX_LIGHTMAPS*local.MAX_LIGHTMAPS_PER_SURFACE)
	for i in range(local.MAX_LIGHTMAPS):
		for j in range(local.MAX_LIGHTMAPS_PER_SURFACE):
			gl3state.lightmap_textureIDs[i][j] = int(ids[i*local.MAX_LIGHTMAPS_PER_SURFACE + j])

	GL3_ResetClearColor()
	gl3_misc.GL3_SetDefaultState()

	if gl3_shaders.GL3_InitShaders():

		clientserver.Com_Printf("Loading shaders succeeded.\n")

	else:

		clientserver.Com_Printf("Loading shaders failed.\n")
		return False

	gl3_model.registration_sequence = 1 # from R_InitImages() (everything else from there shouldn't be needed anymore)

	gl3_image.GL3_Scrap_Init()

	gl3_model.GL3_Mod_Init()

	gl3_misc.GL3_InitParticleTexture()

	gl3_draw.GL3_Draw_InitLocal()

	gl3_surf.GL3_SurfInit()

	gl3state.ppFBO = GL.glGenFramebuffers(1)
	# the rest for the FBO is done dynamically in GL3_RenderView() so it can
	# take the viewsize into account (enforce that by setting invalid size)
	gl3state.ppFBtexWidth = gl3state.ppFBtexHeight = -1

	clientserver.Com_Printf("\n")
	return True

def GL3_Shutdown(): #void

	ri.Cmd_RemoveCommand("modellist")
	ri.Cmd_RemoveCommand("screenshot")
	ri.Cmd_RemoveCommand("imagelist")
	ri.Cmd_RemoveCommand("gl_strings")

	# only call all these if we have an OpenGL context and the gl function pointers
	# randomly chose one function that should always be there to test..
	# Q2PORT: if(glDeleteBuffers != NULL): the shaders exist if the context did
	if gl3state.si2D.shaderProgram != 0:

		gl3_model.GL3_Mod_FreeAll()
		gl3_mesh.GL3_ShutdownMeshes()
		gl3_image.GL3_ShutdownImages()
		gl3_surf.GL3_SurfShutdown()
		gl3_draw.GL3_Draw_ShutdownLocal()
		gl3_shaders.GL3_ShutdownShaders()

		# free the postprocessing FBO and its renderbuffer and texture
		if gl3state.ppFBrbo != 0:
			GL.glDeleteRenderbuffers(1, [gl3state.ppFBrbo])
		if gl3state.ppFBtex != 0:
			GL.glDeleteTextures(1, [gl3state.ppFBtex])
		if gl3state.ppFBO != 0:
			GL.glDeleteFramebuffers(1, [gl3state.ppFBO])
		gl3state.ppFBrbo = gl3state.ppFBtex = gl3state.ppFBO = 0
		gl3state.ppFBObound = False
		gl3state.ppFBtexWidth = gl3state.ppFBtexHeight = -1

	vtxBuf.clear() # da_free(vtxBuf)
	idxBuf.clear()
	drawCmds.clear()
	transModelMats.clear()

	# shutdown OS specific OpenGL stuff like contexts, etc.
	gl3_sdl.GL3_ShutdownContext()

	# Q2PORT: the C unloads the renderer library after this, so gl3state is zero
	# again when it's next loaded. The python module stays loaded: reset what
	# gl3state caches about the GL context's bindings, as the new context has
	# nothing bound. Otherwise GL3_BindVBO() etc. skip binding the new context's
	# objects that got the same ids as the old ones (a GLError on vid_restart).
	fresh = local.gl3state_t()
	gl3state.currenttexture = fresh.currenttexture
	gl3state.currentlightmap = fresh.currentlightmap
	gl3state.currenttmu = fresh.currenttmu
	gl3state.currentVAO = fresh.currentVAO
	gl3state.currentVBO = fresh.currentVBO
	gl3state.currentEBO = fresh.currentEBO
	gl3state.currentShaderProgram = fresh.currentShaderProgram
	gl3state.currentUBO = fresh.currentUBO

def colorsEqual(c1, c2): #const byte [3], const byte [3] (returns qboolean)

	return c1[0] == c2[0] and c1[1] == c2[1] and c1[2] == c2[2]

def lmstylesEqual(st1, st2): #const byte [MAXLIGHTMAPS], const byte [MAXLIGHTMAPS] (returns qboolean)

	for i in range(files_h_MAXLIGHTMAPS):

		astyle = st1[i]
		if astyle != st2[i]:
			return False
		# 255 indicates that this and the remaining styles can be ignored
		# (still needed to check first if a and b agree about ignoring it)
		if astyle == 255:
			break

	return True

files_h_MAXLIGHTMAPS = local.MAX_LIGHTMAPS_PER_SURFACE # MAXLIGHTMAPS

def UpdateLMscales(lmScales, si): #const hmm_vec4 [MAX_LIGHTMAPS_PER_SURFACE], gl3ShaderInfo_t*

	hasChanged = False

	for i in range(local.MAX_LIGHTMAPS_PER_SURFACE):

		if hasChanged:

			si.lmScales[i] = lmScales[i]

		elif (si.lmScales[i][0] != lmScales[i][0]
		        or si.lmScales[i][1] != lmScales[i][1]
		        or si.lmScales[i][2] != lmScales[i][2]
		        or si.lmScales[i][3] != lmScales[i][3] ):

			si.lmScales[i] = lmScales[i]
			hasChanged = True

	if hasChanged:

		GL.glUniform4fv(si.uniLmScalesOrTime, local.MAX_LIGHTMAPS_PER_SURFACE, si.lmScales)

def GL3_Draw3DBatchesNow(): #void

	global vtxBufCount

	if len(drawCmds) == 0:
		return

	local.GL3_BindVAO(gl3state.vao3D)
	local.GL3_BindVBO(gl3state.vbo3D)
	local.GL3_BindEBO(gl3state.ebo3D)

	# Q2PORT: vtxBuf is a list of record arrays; join them as bytes, as joining
	# the record arrays makes numpy merge their field types for each one (slow)
	vtx = np.concatenate([b.view(np.uint8) for b in vtxBuf])
	idx = np.array(idxBuf, dtype=np.uint16)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vtx.nbytes, vtx, GL.GL_STREAM_DRAW)
	GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, idx.nbytes, idx, GL.GL_STREAM_DRAW)

	gl3_draw.gl3_numBufferVtxData += 1

	# set curState to something that reflects the actual state, as far as possible,
	# and otherwise makes sure it'll be set in the loop
	curState = local.GL3_CreateDrawCmd()

	curState.texnum = gl3state.currenttexture
	curState.lmtexnum = gl3state.currentlightmap
	curState.alpha = float(gl3state.uni3DData[local.UNI3D_ALPHA])
	curState.scroll = float(gl3state.uni3DData[local.UNI3D_SCROLL])
	curState.lightScaleForTurb = float(gl3state.uni3DData[local.UNI3D_LIGHTSCALEFORTURB])

	# for the next two the approach is setting a value that
	# is different from the one in the first drawCmd, to make sure
	# the corresponding state is set in the first iteration
	curState.flags = ~drawCmds[0].flags & 0xff # just the opposite flags of the first element
	curState.transModelMatIdx = drawCmds[0].transModelMatIdx + 1

	shader = None

	for cmd in drawCmds:

		flags = cmd.flags
		curFlags = curState.flags
		updateUni3D = False

		if cmd.shaderIdx != curState.shaderIdx:

			shader = local.GL3_GetDrawCmdShader(cmd)
			local.GL3_UseProgram( shader.shaderProgram )

		if cmd.texnum != gl3state.currenttexture:
			gl3_image.GL3_Bind(cmd.texnum)
		if cmd.lmtexnum >= 0:
			gl3_image.GL3_BindLightmap(cmd.lmtexnum)

		if (flags & local.DCFlag_DisableDepthMask) != (curFlags & local.DCFlag_DisableDepthMask):
			GL.glDepthMask((flags & local.DCFlag_DisableDepthMask) == 0)

		if (flags & local.DCFlag_Blend) != (curFlags & local.DCFlag_Blend):

			if flags & local.DCFlag_Blend:
				GL.glEnable(GL.GL_BLEND)
			else:
				GL.glDisable(GL.GL_BLEND)

		if (flags & local.DCFlag_PolyOffsetFill) != (curFlags & local.DCFlag_PolyOffsetFill):

			if flags & local.DCFlag_PolyOffsetFill:
				GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
			else:
				GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

		if (flags & local.DCFlag_UseScroll) and cmd.scroll != gl3state.uni3DData[local.UNI3D_SCROLL]:

			gl3state.uni3DData[local.UNI3D_SCROLL] = cmd.scroll
			updateUni3D = True

		if ((flags & local.DCFlag_UseLightScaleForTurb)
		   and cmd.lightScaleForTurb != gl3state.uni3DData[local.UNI3D_LIGHTSCALEFORTURB]):

			gl3state.uni3DData[local.UNI3D_LIGHTSCALEFORTURB] = cmd.lightScaleForTurb
			updateUni3D = True

		if (flags & local.DCFlag_UseLmStyles) and not lmstylesEqual(cmd.styles, curState.styles):

			lmScales = np.zeros((local.MAX_LIGHTMAPS_PER_SURFACE, 4), dtype=np.float32) #hmm_vec4 [MAX_LIGHTMAPS_PER_SURFACE] = {0}
			lmScales[0] = (1.0, 1.0, 1.0, 1.0)
			map_ = 0
			while map_ < local.MAX_LIGHTMAPS_PER_SURFACE and cmd.styles[map_] != 255:

				lmScales[map_][0] = r_newrefdef.lightstyles[cmd.styles[map_]].rgb[0]
				lmScales[map_][1] = r_newrefdef.lightstyles[cmd.styles[map_]].rgb[1]
				lmScales[map_][2] = r_newrefdef.lightstyles[cmd.styles[map_]].rgb[2]
				lmScales[map_][3] = 1.0
				map_ += 1

			UpdateLMscales(lmScales, shader)

		if flags & local.DCFlag_UseColor:

			if cmd.alpha != curState.alpha or not colorsEqual(cmd.color, curState.color):

				gl3state.uniCommonData[local.UNICOMMON_COLOR + 0] = cmd.color[0] * (1.0/255.0)
				gl3state.uniCommonData[local.UNICOMMON_COLOR + 1] = cmd.color[1] * (1.0/255.0)
				gl3state.uniCommonData[local.UNICOMMON_COLOR + 2] = cmd.color[2] * (1.0/255.0)
				gl3state.uniCommonData[local.UNICOMMON_COLOR + 3] = cmd.alpha
				gl3_shaders.GL3_UpdateUBOCommon()

		elif (flags & local.DCFlag_Blend) and cmd.alpha != gl3state.uni3DData[local.UNI3D_ALPHA]:

			gl3state.uni3DData[local.UNI3D_ALPHA] = cmd.alpha
			updateUni3D = True

		if cmd.transModelMatIdx != curState.transModelMatIdx:

			gl3state.uni3DData[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = transModelMats[cmd.transModelMatIdx].flatten()
			updateUni3D = True

		if updateUni3D:
			gl3_shaders.GL3_UpdateUBO3D()

		elemOffset = cmd.idxBufOffset * 2 # sizeof(GLushort)
		GL.glDrawElements(GL.GL_TRIANGLES, cmd.numElements, GL.GL_UNSIGNED_SHORT, ctypes.c_void_p(elemOffset))
		curState = cmd

		gl3_draw.gl3_num3Ddraws += 1

	vtxBuf.clear() # da_clear(vtxBuf)
	vtxBufCount = 0
	idxBuf.clear()
	drawCmds.clear()

	del transModelMats[1:] # da_setcount(transModelMats, 1); keep index 0 (identity matrix)

	# restore sane default for other draw operations (models, particles, 2D)
	if curState.transModelMatIdx != 0:

		gl3state.uni3DData[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = gl3_identityMat4.flatten()
		gl3_shaders.GL3_UpdateUBO3D()

	curFlags = curState.flags
	if curFlags & local.DCFlag_Blend:
		GL.glDisable(GL.GL_BLEND)
	if curFlags & local.DCFlag_DisableDepthMask:
		GL.glDepthMask(GL.GL_TRUE)

	if curFlags & local.DCFlag_PolyOffsetFill:
		GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

def drawStateEqual(a, b): #const gl3drawCmd_t*, const gl3drawCmd_t* (returns qboolean)

	if ( a.flags != b.flags or a.shaderIdx != b.shaderIdx
	   or a.texnum != b.texnum or a.lmtexnum != b.lmtexnum
	   or a.transModelMatIdx != b.transModelMatIdx ):
		return False

	flags = a.flags # at this point we know the flags are identical

	if (flags & local.DCFlag_UseScroll) and a.scroll != b.scroll:
		return False

	if (flags & local.DCFlag_UseLightScaleForTurb) and a.lightScaleForTurb != b.lightScaleForTurb:
		return False

	if (flags & local.DCFlag_UseColor) and not colorsEqual(a.color, b.color):
		return False

	if a.alpha != b.alpha:
		return False

	if (flags & local.DCFlag_UseLmStyles) and not lmstylesEqual(a.styles, b.styles):
		return False

	return True

def GL3_SetDrawCmdTransMatrix(drawCmd, mat): #gl3drawCmd_t*, hmm_mat4

	idx = len(transModelMats)
	transModelMats.append(mat)
	drawCmd.transModelMatIdx = idx

"""
 assumes gl3state.v[ab]o3D are bound
 buffers and draws gl3_3D_vtx_t vertices
 drawMode is something like GL_TRIANGLE_STRIP or GL_TRIANGLE_FAN or whatever
"""
def GL3_Add3DdrawCmdToBatch(verts, numVerts, drawMode, drawCmd): #const gl3_3D_vtx_t*, int, GLenum, gl3drawCmd_t

	global vtxBufCount

	if numVerts > UINT16_MAX:

		clientserver.Com_Printf("WARNING: Discarding a draw command with {} vertices (max {} allowed)!\n".format(numVerts, UINT16_MAX))
		return

	if vtxBufCount+numVerts > UINT16_MAX:

		GL3_Draw3DBatchesNow()

	# Q2PORT: the C gets the drawCmd by value
	byValue = local.gl3drawCmd_t()
	byValue.copy(drawCmd)
	drawCmd = byValue

	nextVtxIdx = vtxBufCount
	drawCmd.idxBufOffset = len(idxBuf)
	assert drawCmd.shaderIdx != -1

	# translate triangle fan/strip to just triangle indices
	if drawMode == GL.GL_TRIANGLE_FAN:

		for i in range(1, numVerts-1):

			idxBuf.extend((nextVtxIdx, nextVtxIdx+i, nextVtxIdx+i+1))

	elif drawMode == GL.GL_TRIANGLE_STRIP:

		i = 1
		while i < numVerts-2:

			# add two triangles at once, because the vertex order is different
			# for odd vs even triangles
			idxBuf.extend((nextVtxIdx + i-1,
			               nextVtxIdx + i,
			               nextVtxIdx + i+1,

			               nextVtxIdx + i,
			               nextVtxIdx + i+2,
			               nextVtxIdx + i+1))
			i += 2

		# add remaining triangle, if any
		if i < numVerts-1:

			idxBuf.extend((nextVtxIdx + i-1,
			               nextVtxIdx + i,
			               nextVtxIdx + i+1))

	elif drawMode == GL.GL_TRIANGLES:

		idxBuf.extend(range(nextVtxIdx, nextVtxIdx + numVerts))

	else:

		clientserver.Com_Printf("GL3_BufferAndDraw3D(): WARNING: Unsupported drawmode 0x{:x}\n".format(drawMode))
		return

	vtxBuf.append(verts[:numVerts]) # da_addn(vtxBuf, verts, numVerts)
	vtxBufCount += numVerts

	numAddedIndices = len(idxBuf) - drawCmd.idxBufOffset

	lastDrawCmd = drawCmds[-1] if drawCmds else None # da_lastptr(drawCmds)
	if lastDrawCmd is not None and drawStateEqual(lastDrawCmd, drawCmd):

		lastDrawCmd.numElements += numAddedIndices

	else:

		drawCmd.numElements = numAddedIndices
		drawCmds.append(drawCmd)

def GL3_DrawBeam(e): #entity_t *

	NUM_BEAM_SEGS = 6

	drawCmd = local.GL3_CreateDrawCmd()

	perpvec = np.zeros(3, dtype=np.float32) #vec3_t
	direction = np.zeros(3, dtype=np.float32)
	normalized_direction = np.zeros(3, dtype=np.float32)
	start_points = np.zeros((NUM_BEAM_SEGS, 3), dtype=np.float32) #vec3_t [NUM_BEAM_SEGS]
	end_points = np.zeros((NUM_BEAM_SEGS, 3), dtype=np.float32)
	oldorigin = np.zeros(3, dtype=np.float32)
	origin = np.zeros(3, dtype=np.float32)

	verts = np.zeros(NUM_BEAM_SEGS*4, dtype=model.gl3_3D_vtx_t) #gl3_3D_vtx_t [NUM_BEAM_SEGS*4]
	#unsigned int pointb;

	oldorigin[0] = e.oldorigin[0]
	oldorigin[1] = e.oldorigin[1]
	oldorigin[2] = e.oldorigin[2]

	origin[0] = e.origin[0]
	origin[1] = e.origin[1]
	origin[2] = e.origin[2]

	normalized_direction[0] = direction[0] = oldorigin[0] - origin[0]
	normalized_direction[1] = direction[1] = oldorigin[1] - origin[1]
	normalized_direction[2] = direction[2] = oldorigin[2] - origin[2]

	if shared_c.VectorNormalize(normalized_direction) == 0:

		return

	shared_c.PerpendicularVector(perpvec, normalized_direction)
	shared_c.VectorScale(perpvec, e.frame / 2, perpvec)

	for i in range(6):

		shared_c.RotatePointAroundVector(start_points[i], normalized_direction, perpvec,
		                        (360.0 / NUM_BEAM_SEGS) * i)
		start_points[i] += origin # VectorAdd(start_points[i], origin, start_points[i])
		end_points[i] = start_points[i] + direction # VectorAdd(start_points[i], direction, end_points[i])

	#glDisable(GL_TEXTURE_2D);
	drawCmd.flags |= (local.DCFlag_Blend | local.DCFlag_DisableDepthMask | local.DCFlag_UseColor)

	local.GL3_SetDrawCmdShader(drawCmd, gl3state.si3DcolorOnly)

	color = gl3_draw.d_8to24table[e.skinnum & 0xFF] # Q2PORT: (r, g, b, a), the C takes the bytes of LittleLong(d_8to24table[..])
	drawCmd.color[0] = color[0] & 0xFF
	drawCmd.color[1] = color[1] & 0xFF
	drawCmd.color[2] = color[2] & 0xFF
	drawCmd.alpha = e.alpha



	for i in range(NUM_BEAM_SEGS):

		verts[4*i+0]["pos"] = start_points[i]
		verts[4*i+1]["pos"] = end_points[i]

		pointb = ( i + 1 ) % NUM_BEAM_SEGS

		verts[4*i+2]["pos"] = start_points[pointb]
		verts[4*i+3]["pos"] = end_points[pointb]


	GL3_Add3DdrawCmdToBatch(verts, NUM_BEAM_SEGS*4, GL.GL_TRIANGLE_STRIP, drawCmd)


def GL3_DrawSpriteModel(e, currentmodel): #entity_t *, gl3model_t *

	alpha = 1.0
	verts = np.zeros(4, dtype=model.gl3_3D_vtx_t) #gl3_3D_vtx_t [4]
	#dsprframe_t *frame;
	#float *up, *right;
	#dsprite_t *psprite;
	#gl3image_t *skin;

	drawCmd = local.GL3_CreateDrawCmd()

	# don't even bother culling, because it's just
	#   a single polygon without a surface cache
	psprite = currentmodel.extradata

	e.frame %= psprite.numframes
	frame = psprite.frames[e.frame]

	# normal sprite
	up = vup
	right = vright

	if e.flags & shared.RF_TRANSLUCENT:

		drawCmd.flags |= local.DCFlag_DisableDepthMask
		alpha = e.alpha

	drawCmd.alpha = alpha

	skin = currentmodel.skins[e.frame]
	if skin is None:

		skin = gl3_misc.gl3_notexture # fallback...

	drawCmd.texnum = skin.texnum

	if alpha == 1.0:

		# use shader with alpha test
		local.GL3_SetDrawCmdShader(drawCmd, gl3state.si3DspriteAlpha)

	else:

		drawCmd.flags |= local.DCFlag_Blend

		local.GL3_SetDrawCmdShader(drawCmd, gl3state.si3Dsprite)

	verts[0]["texCoord"] = (0, 1)
	verts[1]["texCoord"] = (0, 0)
	verts[2]["texCoord"] = (1, 0)
	verts[3]["texCoord"] = (1, 1)

	pos = np.zeros(3, dtype=np.float32)

	shared_c.VectorMA( e.origin, -frame.origin_y, up, pos )
	shared_c.VectorMA( pos, -frame.origin_x, right, pos )
	verts[0]["pos"] = pos

	shared_c.VectorMA( e.origin, frame.height - frame.origin_y, up, pos )
	shared_c.VectorMA( pos, -frame.origin_x, right, pos )
	verts[1]["pos"] = pos

	shared_c.VectorMA( e.origin, frame.height - frame.origin_y, up, pos )
	shared_c.VectorMA( pos, frame.width - frame.origin_x, right, pos )
	verts[2]["pos"] = pos

	shared_c.VectorMA( e.origin, -frame.origin_y, up, pos )
	shared_c.VectorMA( pos, frame.width - frame.origin_x, right, pos )
	verts[3]["pos"] = pos


	GL3_Add3DdrawCmdToBatch(verts, 4, GL.GL_TRIANGLE_FAN, drawCmd)


def GL3_DrawNullModel(currententity): #entity_t *

	shadelight = np.zeros(3, dtype=np.float32) #vec3_t
	drawCmd = local.GL3_CreateDrawCmd()

	if currententity.flags & shared.RF_TRANSLUCENT:
		drawCmd.flags |= local.DCFlag_DisableDepthMask

	if currententity.flags & shared.RF_FULLBRIGHT:

		shadelight[0] = shadelight[1] = shadelight[2] = 1.0

	else:

		gl3_light.GL3_LightPoint(currententity, currententity.origin, shadelight)

	GL3_RotateForEntity(currententity, drawCmd)

	drawCmd.alpha = 1.0
	for i in range(3):

		c = int(shadelight[i] * 255.0)
		drawCmd.color[i] = c & 255

	drawCmd.flags |= local.DCFlag_UseColor

	local.GL3_SetDrawCmdShader(drawCmd, gl3state.si3DcolorOnly)

	vtxA = np.zeros(6, dtype=model.gl3_3D_vtx_t) #gl3_3D_vtx_t [6]
	vtxA["pos"] = [
		(0, 0, -16),
		(16 * math.cos( 0 * math.pi / 2 ), 16 * math.sin( 0 * math.pi / 2 ), 0),
		(16 * math.cos( 1 * math.pi / 2 ), 16 * math.sin( 1 * math.pi / 2 ), 0),
		(16 * math.cos( 2 * math.pi / 2 ), 16 * math.sin( 2 * math.pi / 2 ), 0),
		(16 * math.cos( 3 * math.pi / 2 ), 16 * math.sin( 3 * math.pi / 2 ), 0),
		(16 * math.cos( 4 * math.pi / 2 ), 16 * math.sin( 4 * math.pi / 2 ), 0)
	]

	GL3_Add3DdrawCmdToBatch(vtxA, 6, GL.GL_TRIANGLE_FAN, drawCmd)

	vtxB = np.zeros(6, dtype=model.gl3_3D_vtx_t) #gl3_3D_vtx_t [6]
	vtxB[0]["pos"] = (0, 0, 16)
	vtxB[1:] = vtxA[5:0:-1] # vtxA[5], vtxA[4], vtxA[3], vtxA[2], vtxA[1]

	GL3_Add3DdrawCmdToBatch(vtxB, 6, GL.GL_TRIANGLE_FAN, drawCmd)


# part_vtx: GLfloat pos[3]; GLfloat size; GLfloat dist; GLfloat color[4];
part_vtx = np.dtype([("pos", "<f4", 3), ("size", "<f4"), ("dist", "<f4"), ("color", "<f4", 4)])
assert part_vtx.itemsize == 9*4, "invalid part_vtx size" # remember to update GL3_SurfInit() if this changes!

def GL3_DrawParticles(): #void

	# TODO: stereo
	#qboolean stereo_split_tb = ((gl_state.stereo_mode == STEREO_SPLIT_VERTICAL) && gl_state.camera_separation);
	#qboolean stereo_split_lr = ((gl_state.stereo_mode == STEREO_SPLIT_HORIZONTAL) && gl_state.camera_separation);

	#if (!(stereo_split_tb || stereo_split_lr))
	if True:

		numParticles = r_newrefdef.num_particles
		#YQ2_ALIGNAS_TYPE(unsigned) byte color[4];
		#const particle_t *p;
		# assume the size looks good with window height 480px and scale according to real resolution
		pointSize = gl3_particle_size.value * float(r_newrefdef.height)/480.0

		# Don't try to draw particles if there aren't any.
		if numParticles == 0:

			return

		buf = np.zeros(numParticles, dtype=part_vtx) #YQ2_VLA(part_vtx, buf, numParticles);

		# TODO: viewOrg could be in UBO
		viewOrg = np.array(r_newrefdef.vieworg, dtype=np.float32) #vec3_t

		GL.glDepthMask(GL.GL_FALSE)
		GL.glEnable(GL.GL_BLEND)

		# GLES doesn't have this, maybe it's always enabled? (https://gamedev.stackexchange.com/a/15528 says it works)
		# luckily we don't use glPointSize() but set gl_PointSize in shader anyway
		GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)

		local.GL3_UseProgram(gl3state.siParticle.shaderProgram)

		# Q2PORT: the C's per-particle loop, done with numpy over all particles
		particles = r_newrefdef.particles[:numParticles]
		origins = np.array([p.origin for p in particles], dtype=np.float32)
		colors = np.array([gl3_draw.d_8to24table[p.color & 0xFF] for p in particles], dtype=np.float32)

		buf["pos"] = origins # VectorCopy(p->origin, cur->pos);
		buf["size"] = pointSize
		buf["dist"] = np.linalg.norm(viewOrg - origins, axis=1) # VectorLength(offset), offset between viewOrg and particle position

		buf["color"][:, 0:3] = colors[:, 0:3] * (1.0/255.0)

		buf["color"][:, 3] = [p.alpha for p in particles]

		local.GL3_BindVAO(gl3state.vaoParticle)
		local.GL3_BindVBO(gl3state.vboParticle)
		GL.glBufferData(GL.GL_ARRAY_BUFFER, buf.nbytes, buf.view(np.uint8), GL.GL_STREAM_DRAW)
		GL.glDrawArrays(GL.GL_POINTS, 0, numParticles)
		gl3_draw.gl3_num3Ddraws += 1
		gl3_draw.gl3_numBufferVtxData += 1

		GL.glDisable(GL.GL_BLEND)
		GL.glDepthMask(GL.GL_TRUE)
		GL.glDisable(GL.GL_PROGRAM_POINT_SIZE)

		#YQ2_VLAFREE(buf);

def _drawEntity(currententity): # Q2PORT: the loop body both passes of GL3_DrawEntitiesOnList share

	if currententity.flags & shared.RF_BEAM:

		GL3_DrawBeam(currententity)

	else:

		currentmodel = currententity.model

		if currentmodel is None:

			GL3_DrawNullModel(currententity)
			return

		if currentmodel.type == model.modtype_t.mod_alias:
			gl3_mesh.GL3_DrawAliasModel(currententity)
		elif currentmodel.type == model.modtype_t.mod_brush:
			gl3_surf.GL3_DrawBrushModel(currententity, currentmodel)
		elif currentmodel.type == model.modtype_t.mod_sprite:
			GL3_DrawSpriteModel(currententity, currentmodel)
		else:
			clientserver.Com_Error(shared.ERR_DROP, "Bad modeltype")

def GL3_DrawEntitiesOnList(): #void

	if not r_drawentities.value:

		return

	gl3_mesh.GL3_ResetShadowAliasModels()

	# draw non-transparent first
	for i in range(r_newrefdef.num_entities):

		currententity = r_newrefdef.entities[i]

		if currententity.flags & shared.RF_TRANSLUCENT:

			continue # solid

		_drawEntity(currententity)

	# draw transparent entities
	#   we could sort these if it ever
	#   becomes a problem...

	# make sure that drawing the solid entities is done first
	GL3_Draw3DBatchesNow()

	GL.glDepthMask(GL.GL_FALSE)

	for i in range(r_newrefdef.num_entities):

		currententity = r_newrefdef.entities[i]

		if not (currententity.flags & shared.RF_TRANSLUCENT):

			continue # solid

		_drawEntity(currententity)

	# make sure that drawing the entities is done before drawing the shadows
	GL3_Draw3DBatchesNow()

	GL.glDepthMask(GL.GL_FALSE)

	gl3_mesh.GL3_DrawAliasShadows()

	GL.glDepthMask(GL.GL_TRUE) # back to writing


def SetupFrame(): #void

	global gl3_framecount, gl3_oldviewcluster, gl3_oldviewcluster2, gl3_viewcluster, gl3_viewcluster2, c_brush_polys, c_alias_polys

	#int i;
	#mleaf_t *leaf;

	gl3_framecount += 1

	# build the transformation matrix for the given view angles
	shared.VectorCopy(r_newrefdef.vieworg, gl3_origin)

	shared_c.AngleVectors(r_newrefdef.viewangles, vpn, vright, vup)

	# current viewcluster
	if not (r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL):

		if gl3_worldmodel is None:

			clientserver.Com_Error(shared.ERR_DROP, "{}: bad world model".format("SetupFrame"))
			return

		gl3_oldviewcluster = gl3_viewcluster
		gl3_oldviewcluster2 = gl3_viewcluster2
		leaf = files_models.Mod_PointInLeaf(gl3_origin, gl3_worldmodel.nodes[0]) # Q2PORT: the C's nodes pointer is the first (root) node
		gl3_viewcluster = gl3_viewcluster2 = leaf.cluster

		# check above and below so crossing solid water doesn't draw wrong
		if not leaf.contents:

			# look down a bit
			temp = np.zeros(3, dtype=np.float32) #vec3_t

			shared.VectorCopy(gl3_origin, temp)
			temp[2] -= 16
			leaf = files_models.Mod_PointInLeaf(temp, gl3_worldmodel.nodes[0]) # Q2PORT: the C's nodes pointer is the first (root) node

			if (not (leaf.contents & shared.CONTENTS_SOLID) and
				(leaf.cluster != gl3_viewcluster2)):

				gl3_viewcluster2 = leaf.cluster

		else:

			# look up a bit
			temp = np.zeros(3, dtype=np.float32) #vec3_t

			shared.VectorCopy(gl3_origin, temp)
			temp[2] += 16
			leaf = files_models.Mod_PointInLeaf(temp, gl3_worldmodel.nodes[0]) # Q2PORT: the C's nodes pointer is the first (root) node

			if (not (leaf.contents & shared.CONTENTS_SOLID) and
				(leaf.cluster != gl3_viewcluster2)):

				gl3_viewcluster2 = leaf.cluster

	for i in range(4):

		v_blend[i] = r_newrefdef.blend[i]

	c_brush_polys = 0
	c_alias_polys = 0

	# clear out the portion of the screen that the NOWORLDMODEL defines
	if r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:

		GL.glEnable(GL.GL_SCISSOR_TEST)
		GL.glClearColor(0.3, 0.3, 0.3, 1)
		GL.glScissor(r_newrefdef.x,
				vid.height - r_newrefdef.height - r_newrefdef.y,
				r_newrefdef.width, r_newrefdef.height)
		GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
		GL3_ResetClearColor()
		GL.glDisable(GL.GL_SCISSOR_TEST)

def GL3_SetGL2D(): #void

	x = 0
	w = vid.width
	y = 0
	h = vid.height

	# Q2PORT: the C's #if 0 // TODO: stereo block is not ported

	GL.glViewport(x, y, w, h)

	transMatr = hmm.HMM_Orthographic(0, vid.width, vid.height, 0, -99999, 99999)

	gl3state.uni2DData[local.UNI2D_TRANS:local.UNI2D_TRANS + 16] = transMatr.flatten() # gl3state.uni2DData.transMat4 = transMatr; [col][row], see hmm.py

	gl3_shaders.GL3_UpdateUBO2D()

	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glDisable(GL.GL_CULL_FACE)
	GL.glDisable(GL.GL_BLEND)

"""
 equivalent to R_x * R_y * R_z where R_x is the trans matrix for rotating around X axis for aroundXdeg
"""
def rotAroundAxisXYZ(aroundXdeg, aroundYdeg, aroundZdeg): #float, float, float (returns hmm_mat4)

	alpha = hmm.HMM_ToRadians(aroundXdeg)
	beta = hmm.HMM_ToRadians(aroundYdeg)
	gamma = hmm.HMM_ToRadians(aroundZdeg)

	sinA = hmm.HMM_SinF(alpha)
	cosA = hmm.HMM_CosF(alpha)
	sinB = hmm.HMM_SinF(beta)
	cosB = hmm.HMM_CosF(beta)
	sinG = hmm.HMM_SinF(gamma)
	cosG = hmm.HMM_CosF(gamma)

	ret = np.array([
		[  cosB*cosG,  sinA*sinB*cosG + cosA*sinG, -cosA*sinB*cosG + sinA*sinG, 0 ], # first *column*
		[ -cosB*sinG, -sinA*sinB*sinG + cosA*cosG,  cosA*sinB*sinG + sinA*cosG, 0 ],
		[  sinB,      -sinA*cosB,                   cosA*cosB,                  0 ],
		[  0,          0,                           0,                          1 ]
	], dtype=np.float32)

	return ret

"""
 equivalent to R_SetPerspective() but returning a matrix instead of setting internal OpenGL state
"""
def GL3_SetPerspective(fovy): #GLdouble (returns hmm_mat4)

	# gluPerspective() / R_MYgluPerspective() style parameters
	zNear = max(gl_znear.value, 0.1)
	zFar = 8192.0 if r_farsee.value else 4096.0
	aspect = float(r_newrefdef.width) / r_newrefdef.height

	# calculation of left, right, bottom, top is from R_MYgluPerspective() of old gl backend
	# which seems to be slightly different from the real gluPerspective()
	# and thus also from HMM_Perspective()
	#GLdouble left, right, bottom, top;
	#float A, B, C, D;

	top = zNear * math.tan(fovy * math.pi / 360.0)
	right = top * aspect

	bottom = -top
	left = -right

	# TODO:  stereo stuff
	# left += - gl1_stereo_convergence->value * (2 * gl_state.camera_separation) / zNear;
	# right += - gl1_stereo_convergence->value * (2 * gl_state.camera_separation) / zNear;

	# the following emulates glFrustum(left, right, bottom, top, zNear, zFar)
	# see https://www.khronos.org/registry/OpenGL-Refpages/gl2.1/xhtml/glFrustum.xml
	#  or http://docs.gl/gl2/glFrustum#description (looks better in non-Firefox browsers)
	A = (right+left)/(right-left)
	B = (top+bottom)/(top-bottom)
	C = -(zFar+zNear)/(zFar-zNear)
	D = -(2.0*zFar*zNear)/(zFar-zNear)

	ret = np.array([
		[ (2.0*zNear)/(right-left), 0, 0, 0 ], # first *column*
		[ 0, (2.0*zNear)/(top-bottom), 0, 0 ],
		[ A, B, C, -1.0 ],
		[ 0, 0, D, 0 ]
	], dtype=np.float32)

	return ret

def SetupGL(): #void

	#int x, x2, y2, y, w, h;

	# set up viewport
	x = math.floor(r_newrefdef.x * vid.width / float(vid.width))
	x2 = math.ceil((r_newrefdef.x + r_newrefdef.width) * vid.width / float(vid.width))
	y = math.floor(vid.height - r_newrefdef.y * vid.height / float(vid.height))
	y2 = math.ceil(vid.height - (r_newrefdef.y + r_newrefdef.height) * vid.height / float(vid.height))

	w = x2 - x
	h = y - y2

	# Q2PORT: the C's #if 0 // TODO: stereo stuff block is not ported

	# set up the FBO accordingly, but only if actually rendering the world
	# (=> don't use FBO when rendering the playermodel in the player menu)
	# also, only do this when under water, because this has a noticeable overhead on some systems
	if (gl3_usefbo.value and gl3state.ppFBO != 0
		and (r_newrefdef.rdflags & (shared.RDF_NOWORLDMODEL|shared.RDF_UNDERWATER)) == shared.RDF_UNDERWATER):

		GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, gl3state.ppFBO)
		gl3state.ppFBObound = True
		if gl3state.ppFBtex == 0:

			gl3state.ppFBtexWidth = -1 # make sure we generate the texture storage below
			gl3state.ppFBtex = GL.glGenTextures(1)

		if gl3state.ppFBrbo == 0:

			gl3state.ppFBtexWidth = -1 # make sure we generate the RBO storage below
			gl3state.ppFBrbo = GL.glGenRenderbuffers(1)

		# even if the FBO already has a texture and RBO, the viewport size
		# might have changed so they need to be regenerated with the correct sizes
		if gl3state.ppFBtexWidth != w or gl3state.ppFBtexHeight != h:

			gl3state.ppFBtexWidth = w
			gl3state.ppFBtexHeight = h
			gl3_image.GL3_Bind(gl3state.ppFBtex)
			# create texture for FBO with size of the viewport
			GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, w, h, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, None)
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR )
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
			gl3_image.GL3_Bind(0)
			# attach it to currently bound FBO
			GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, gl3state.ppFBtex, 0)

			# also create a renderbuffer object so the FBO has a stencil- and depth-buffer
			GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, gl3state.ppFBrbo)
			GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH24_STENCIL8, w, h)
			GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, 0)
			# attach it to the FBO
			GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_STENCIL_ATTACHMENT,
			                          GL.GL_RENDERBUFFER, gl3state.ppFBrbo)

			fbState = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)
			if fbState != GL.GL_FRAMEBUFFER_COMPLETE:

				clientserver.Com_Printf("GL3 SetupGL(): WARNING: FBO is not complete, status = 0x{:x}\n".format(fbState))
				gl3state.ppFBtexWidth = -1 # to try again next frame; TODO: maybe give up?
				gl3state.ppFBObound = False
				GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

		GL3_Clear() # clear the FBO that's bound now

		GL.glViewport(0, 0, w, h) # this will be moved to the center later, so no x/y offset

	else: # rendering directly (not to FBO for postprocessing)

		GL.glViewport(x, y2, w, h)

	# set up projection matrix (eye coordinates -> clip coordinates)
	gl3state.projMat3D = GL3_SetPerspective(r_newrefdef.fov_y)

	GL.glCullFace(GL.GL_FRONT)

	# set up view matrix (world coordinates -> eye coordinates)
	if True:

		# first put Z axis going up
		viewMat = np.array([
			[  0, 0, -1, 0 ], # first *column* (the matrix is column-major)
			[ -1, 0,  0, 0 ],
			[  0, 1,  0, 0 ],
			[  0, 0,  0, 1 ]
		], dtype=np.float32)

		# now rotate by view angles
		rotMat = rotAroundAxisXYZ(-r_newrefdef.viewangles[2], -r_newrefdef.viewangles[0], -r_newrefdef.viewangles[1])

		viewMat = hmm.HMM_MultiplyMat4( viewMat, rotMat )

		# .. and apply translation for current position
		trans = hmm.HMM_Vec3(-r_newrefdef.vieworg[0], -r_newrefdef.vieworg[1], -r_newrefdef.vieworg[2])
		viewMat = hmm.HMM_MultiplyMat4( viewMat, hmm.HMM_Translate(trans) )

		gl3state.viewMat3D = viewMat

	# just use one projection-view-matrix (premultiplied here)
	# so we have one less mat4 multiplication in the 3D shaders
	gl3state.uni3DData[local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16] = hmm.HMM_MultiplyMat4(gl3state.projMat3D, gl3state.viewMat3D).flatten()

	gl3state.uni3DData[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = gl3_identityMat4.flatten()

	gl3state.uni3DData[local.UNI3D_TIME] = r_newrefdef.time

	gl3_shaders.GL3_UpdateUBO3D()

	# set drawing parms
	if r_cull.value:

		GL.glEnable(GL.GL_CULL_FACE)

	else:

		GL.glDisable(GL.GL_CULL_FACE)

	GL.glEnable(GL.GL_DEPTH_TEST)

#extern int c_visible_lightmaps, c_visible_textures;

"""
 * r_newrefdef must be set before the first call - FIXME: ?! it is set right here
"""
def GL3_RenderView(fd): #refdef_t *

	global r_newrefdef, c_brush_polys, c_alias_polys

	# Q2PORT: the C's #if 0 // TODO: keep stereo stuff? block is not ported

	if r_norefresh.value:

		return

	r_newrefdef = copy.copy(fd) # r_newrefdef = *fd;

	if gl3_worldmodel is None and not (r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL):

		clientserver.Com_Error(shared.ERR_DROP, "R_RenderView: NULL worldmodel")

	if r_speeds.value:

		c_brush_polys = 0
		c_alias_polys = 0

	gl3_light.GL3_PushDlights()

	if gl_finish.value:

		GL.glFinish()

	SetupFrame()

	files_surf.R_SetFrustum(vup, vpn, vright, gl3_origin,
		r_newrefdef.fov_x, r_newrefdef.fov_y, frustum)

	SetupGL()

	gl3_surf.GL3_MarkLeaves() # done here so we know if we're in water

	gl3_surf.GL3_DrawWorld()

	GL3_DrawEntitiesOnList()

	# kick the silly gl1_flashblend poly lights
	# GL3_RenderDlights();

	GL3_DrawParticles()

	gl3_surf.GL3_DrawAlphaSurfaces()

	# make sure all remaining batched 3D stuff is drawn
	GL3_Draw3DBatchesNow()

	# Note: R_Flash() is now GL3_Draw_Flash() and called from GL3_RenderFrame()

	if r_speeds.value:

		clientserver.Com_Printf("{:4} wpoly {:4} epoly {} tex {} lmaps\n".format(
				c_brush_polys, c_alias_polys, gl3_surf.c_visible_textures,
				gl3_surf.c_visible_lightmaps))

	# Q2PORT: the C's #if 0 // TODO: stereo stuff block is not ported

def GL3_SetLightLevel(currententity): #entity_t *

	shadelight = np.zeros(3, dtype=np.float32) #vec3_t = {0}

	if r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:

		return

	# save off light value for server to look at
	gl3_light.GL3_LightPoint(currententity, r_newrefdef.vieworg, shadelight)

	# pick the greatest component, which should be the
	# same as the mono value returned by software
	if shadelight[0] > shadelight[1]:

		if shadelight[0] > shadelight[2]:

			r_lightlevel.value = 150 * shadelight[0]

		else:

			r_lightlevel.value = 150 * shadelight[2]

	else:

		if shadelight[1] > shadelight[2]:

			r_lightlevel.value = 150 * shadelight[1]

		else:

			r_lightlevel.value = 150 * shadelight[2]

def GL3_RenderFrame(fd): #refdef_t *

	# in case some batched 2D draws are outstanding, draw them now
	# to preserve draw order (I think here this is only relevant
	# for the player model in the multiplayer player setup menu)
	gl3_draw.GL3_DrawCurrent2Dbatch()

	GL3_RenderView(fd)
	GL3_SetLightLevel(None)
	usedFBO = gl3state.ppFBObound # if it was/is used this frame
	if usedFBO:

		GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0) # now render to default framebuffer
		gl3state.ppFBObound = False

	GL3_SetGL2D()

	x = (vid.width - r_newrefdef.width)//2
	y = (vid.height - r_newrefdef.height)//2
	if usedFBO:

		# if we're actually drawing the world and using an FBO, render the FBO's texture
		gl3_draw.GL3_DrawFrameBufferObject(x, y, r_newrefdef.width, r_newrefdef.height, gl3state.ppFBtex, v_blend)

	elif v_blend[3] != 0.0:

		gl3_draw.GL3_Draw_Flash(v_blend, x, y, r_newrefdef.width, r_newrefdef.height)


def GL3_Clear(): #void

	global gl3depthmin, gl3depthmax

	# Define which buffers need clearing
	clearFlags = GL.GL_DEPTH_BUFFER_BIT

	if r_clear.value:

		clearFlags |= GL.GL_COLOR_BUFFER_BIT

	# Stencilbuffer shadows
	if gl_shadows.value and gl3config.stencil:

		GL.glClearStencil(1)
		clearFlags |= GL.GL_STENCIL_BUFFER_BIT

	# Q2PORT: the C's #if 0 // TODO: stereo stuff and YQ2_GL3_GLES blocks are not ported

	GL.glClear(clearFlags)

	gl3depthmin = 0
	gl3depthmax = 1
	GL.glDepthFunc(GL.GL_LEQUAL)
	GL.glDepthRange(gl3depthmin, gl3depthmax)

	if gl_zfix.value:

		if gl3depthmax > gl3depthmin:

			GL.glPolygonOffset(0.05, 1)

		else:

			GL.glPolygonOffset(-0.05, -1)

def GL3_BeginFrame(camera_separation): #float

	# Q2PORT: the C's #if 0 // TODO: stereo stuff block is not ported

	if vid_gamma.modified or gl3_intensity.modified or gl3_intensity_2D.modified:

		vid_gamma.modified = False
		gl3_intensity.modified = False
		gl3_intensity_2D.modified = False

		gl3state.uniCommonData[local.UNICOMMON_GAMMA] = 1.0/vid_gamma.value
		gl3state.uniCommonData[local.UNICOMMON_INTENSITY] = gl3_intensity.value
		gl3state.uniCommonData[local.UNICOMMON_INTENSITY2D] = gl3_intensity_2D.value
		gl3_shaders.GL3_UpdateUBOCommon()

	# in GL3, overbrightbits can have any positive value
	if gl3_overbrightbits.modified:

		gl3_overbrightbits.modified = False

		if gl3_overbrightbits.value < 0.0:

			ri.Cvar_Set("gl3_overbrightbits", "0")

		gl3state.uni3DData[local.UNI3D_OVERBRIGHTBITS] = 1.0 if (gl3_overbrightbits.value <= 0.0) else gl3_overbrightbits.value
		gl3_shaders.GL3_UpdateUBO3D()

	if gl3_particle_fade_factor.modified:

		gl3_particle_fade_factor.modified = False
		gl3state.uni3DData[local.UNI3D_PARTICLEFADEFATOR] = gl3_particle_fade_factor.value
		gl3_shaders.GL3_UpdateUBO3D()

	if gl3_particle_square.modified or gl3_colorlight.modified:

		gl3_particle_square.modified = False
		gl3_colorlight.modified = False
		gl3_shaders.GL3_RecreateShaders()


	# go into 2D mode

	GL3_SetGL2D()

	# draw buffer stuff
	if gl_drawbuffer.modified:

		gl_drawbuffer.modified = False


		# Desktop GL
		# TODO: stereo stuff
		#if ((gl3state.camera_separation == 0) || gl3state.stereo_mode != STEREO_MODE_OPENGL)
		if True:

			drawBuffer = GL.GL_BACK
			if shared_c.Q_stricmp(gl_drawbuffer.string, "GL_FRONT") == 0:

				drawBuffer = GL.GL_FRONT

			GL.glDrawBuffer(drawBuffer)

	# texturemode stuff
	if (gl_texturemode.modified or (gl3config.anisotropic and gl_anisotropic.modified)
	    or gl_nolerp_list.modified or r_lerp_list.modified
		or r_2D_unfiltered.modified or r_videos_unfiltered.modified):

		gl3_image.GL3_TextureMode(gl_texturemode.string)
		gl_texturemode.modified = False
		gl_anisotropic.modified = False
		gl_nolerp_list.modified = False
		r_lerp_list.modified = False
		r_2D_unfiltered.modified = False
		r_videos_unfiltered.modified = False

	if r_vsync.modified:

		r_vsync.modified = False
		gl3_sdl.GL3_SetVsync()

	# clear screen if desired
	GL3_Clear()

def GL3_SetPalette(palette): #const unsigned char *

	#int i;
	rp = gl3_rawpalette.view(np.uint8) # byte *rp = (byte *)gl3_rawpalette;

	if palette is not None:

		for i in range(256):

			rp[i * 4 + 0] = palette[i * 3 + 0]
			rp[i * 4 + 1] = palette[i * 3 + 1]
			rp[i * 4 + 2] = palette[i * 3 + 2]
			rp[i * 4 + 3] = 0xff

	else:

		for i in range(256):

			rp[i * 4 + 0] = gl3_draw.d_8to24table[i][0] # LittleLong(d_8to24table[i]) & 0xff
			rp[i * 4 + 1] = gl3_draw.d_8to24table[i][1]
			rp[i * 4 + 2] = gl3_draw.d_8to24table[i][2]
			rp[i * 4 + 3] = 0xff

	GL.glClearColor(0, 0, 0, 0)
	GL.glClear(GL.GL_COLOR_BUFFER_BIT)
	GL3_ResetClearColor()

"""
=====================
GL3_EndWorldRenderpass
=====================
"""
def GL3_EndWorldRenderpass(): #void (returns qboolean)

	return True

# Q2PORT: shims between the port's refexport_t (id's interface) and the gl3
# functions with Yamagi's signatures

def RI_Init(hinstance, hWnd): #void *, void * (returns int)

	# id's re.Init(hinstance, wndproc), vid.py checks for -1
	if not GL3_Init():
		return -1
	return 0

def GetRefAPI(imp): #refimport_t (returns refexport_t)

	global ri

	re = ref.refexport_t() # = {0}

	ri = imp

	re.api_version = ref.API_VERSION
	#re.framework_version = GL3_GetSDLVersion(); Q2PORT: the port's refexport_t has no framework_version

	re.Init = RI_Init # GL3_Init
	re.Shutdown = GL3_Shutdown
	re.PrepareForWindow = gl3_sdl.GL3_PrepareForWindow
	re.InitContext = gl3_sdl.GL3_InitContext
	re.GetDrawableSize = gl3_sdl.GL3_GetDrawableSize
	re.ShutdownContext = gl3_sdl.GL3_ShutdownContext
	re.IsVSyncActive = gl3_sdl.GL3_IsVsyncActive

	re.BeginRegistration = gl3_model.GL3_BeginRegistration
	re.RegisterModel = gl3_model.GL3_RegisterModel
	re.RegisterSkin = gl3_image.GL3_RegisterSkin
	re.RegisterPic = gl3_draw.GL3_Draw_FindPic # Q2PORT: id's refexport_t

	re.SetSky = gl3_warp.GL3_SetSky
	re.EndRegistration = gl3_model.GL3_EndRegistration

	re.RenderFrame = GL3_RenderFrame

	re.DrawFindPic = gl3_draw.GL3_Draw_FindPic
	re.DrawGetPicSize = gl3_draw.GL3_Draw_GetPicSize

	re.DrawPicScaled = gl3_draw.GL3_Draw_PicScaled
	re.DrawPicScaledCol = gl3_draw.GL3_Draw_PicScaledCol
	re.DrawStretchPic = gl3_draw.GL3_Draw_StretchPic

	re.DrawCharScaled = gl3_draw.GL3_Draw_CharScaled
	re.DrawTileClear = gl3_draw.GL3_Draw_TileClear
	re.DrawFill = gl3_draw.GL3_Draw_Fill
	re.DrawFadeScreen = gl3_draw.GL3_Draw_FadeScreen

	re.DrawStretchRaw = gl3_draw.GL3_Draw_StretchRaw
	re.SetPalette = GL3_SetPalette

	re.BeginFrame = GL3_BeginFrame
	re.EndWorldRenderpass = GL3_EndWorldRenderpass
	re.EndFrame = gl3_draw.GL3_EndFrame

	re.AppActivate = lambda active: None # Q2PORT: id's refexport_t; Yamagi's has no AppActivate

	# Tell the client that we're unsing the
	# new renderer restart API.
	#ri.Vid_RequestRestart(RESTART_NO); Q2PORT: the port's refimport_t has no Vid_RequestRestart

	return re
