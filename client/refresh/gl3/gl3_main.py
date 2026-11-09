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
 * gl3_main.c - main file for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from OpenGL import GL
from enum import Enum
from common import cvar
from common.header import shared
from common.header import files as files_h
from client import ref
from client.vid import glimp_sdl2
from common.header import common as common_h
from client.refresh import ref_shared
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model
from client.refresh.gl3.header import hmm
from client.refresh.gl3 import gl3_shaders
from client.refresh.gl3 import gl3_draw
from client.refresh.gl3 import gl3_surf
from client.refresh.gl3 import gl3_mesh
from client.refresh.gl3 import gl3_model
from client.refresh.gl3 import gl3_image
from client.refresh.gl3 import gl3_light
from client.refresh.gl3 import gl3_lightmap
from client.refresh.gl3 import gl3_warp
from client.refresh import files
from client.refresh.gl1 import gl1_main, gl1_image # Q2PORT: gl3 reuses gl1's image/model/data subsystems

REF_VERSION = "gl3"

class rserr_t(Enum):

	rserr_ok = 0
	rserr_invalid_mode = 1
	rserr_unknown = 2

# cvars (from local.h)
gl_msaa_samples = None #cvar_t *
r_vsync = None #cvar_t *
r_retexturing = None #cvar_t *
r_scale8bittextures = None #cvar_t *
vid_fullscreen = None #cvar_t *
r_mode = None #cvar_t *
r_customwidth = None #cvar_t *
r_customheight = None #cvar_t *

r_2D_unfiltered = None #cvar_t *
r_videos_unfiltered = None #cvar_t *
gl_nolerp_list = None #cvar_t *
r_lerp_list = None #cvar_t *
gl_nobind = None #cvar_t *
gl_showtris = None #cvar_t *
r_lockpvs = None #cvar_t *
r_novis = None #cvar_t *

r_cull = None #cvar_t *
gl_zfix = None #cvar_t *
r_fullbright = None #cvar_t *

r_norefresh = None #cvar_t *
gl_lefthand = None #cvar_t *
r_gunfov = None #cvar_t *
r_farsee = None #cvar_t *
r_drawworld = None #cvar_t *

vid_gamma = None #cvar_t *
gl3_intensity = None #cvar_t *
gl3_intensity_2D = None #cvar_t *
gl_anisotropic = None #cvar_t *
gl_texturemode = None #cvar_t *

r_lightlevel = None #cvar_t *
gl3_overbrightbits = None #cvar_t *
gl3_particle_fade_factor = None #cvar_t *
gl3_particle_square = None #cvar_t *
gl3_colorlight = None #cvar_t *
gl_polyblend = None #cvar_t *

r_modulate = None #cvar_t *
gl_lightmap = None #cvar_t *
gl_shadows = None #cvar_t *
r_clear = None #cvar_t *
gl_drawbuffer = None #cvar_t *
r_fixsurfsky = None #cvar_t *
r_palettedtexture = None #cvar_t *
r_validation = None #cvar_t *
gl3_debugcontext = None #cvar_t *
gl3_show_draw_stats = None #cvar_t *

gl1_stereo = None #cvar_t *
gl1_stereo_separation = None #cvar_t *
gl1_stereo_anaglyph_colors = None #cvar_t *
gl1_stereo_convergence = None #cvar_t *
gl1_particle_min_size = None #cvar_t *
gl1_particle_max_size = None #cvar_t *
gl1_particle_size = None #cvar_t *
gl1_particle_att_a = None #cvar_t *
gl1_particle_att_b = None #cvar_t *
gl1_particle_att_c = None #cvar_t *
r_drawentities = None #cvar_t *
r_lerpmodels = None #cvar_t *
r_speeds = None #cvar_t *


class gl3config_t(object):

	def __init__(self):

		self.stencil = True #qboolean, stencil buffer available
		self.gles = False #qboolean, OpenGL ES (not the desktop port)
		self.anisotropic = False #qboolean
		self.max_anisotropy = 1.0 #float
		self.npottextures = True #qboolean


gl3config = gl3config_t() #gl3config_t

#
gl3state = local.gl3state_t() #gl3state_t
gl3depthmin = 0 #float
gl3depthmax = 1 #float
gl_filter_min = GL.GL_LINEAR #int
gl_filter_max = GL.GL_LINEAR #int

ri = None #refimport_t
registration_sequence = 0 #int, for re-registering images

# GL capability strings (the C stores these on gl_config; the Python platform
# has no single gl_config object, so we keep them here)
gl_vendor_string = None #const char *
gl_renderer_string = None #const char *
gl_version_string = None #const char *
gl_glsl_version_string = None #const char *

# dynamic light model rotation matrices (transModelMats in the C)
transModelMats = [hmm.HMM_Mat4d (1.0)] #hmm_mat4 [dynamic_array]

gl3_particletexture = None #gl3image_t *
gl3_notexture = None #gl3image_t *

r_dlightframecount = 0 #int
gl3_scrap_dirty = False #qboolean

MAXLIGHTSTYLES = 64 #from the C shared.h
r_lightstyle_value = [1.0] * MAXLIGHTSTYLES #float


class viddef_t(object):

	def __init__(self):

		self.width, self.height = 800, 600 # coordinates from main game


vid = viddef_t() #viddef_t


def R_Register (): #void

	global gl_msaa_samples, r_vsync, r_retexturing, r_scale8bittextures, vid_fullscreen, r_mode, r_customwidth, r_customheight
	global r_2D_unfiltered, r_videos_unfiltered, gl_nolerp_list, r_lerp_list, gl_nobind, gl_showtris, r_lockpvs, r_novis
	global r_cull, gl_zfix, r_fullbright
	global r_norefresh, gl_lefthand, r_gunfov, r_farsee, r_drawworld
	global vid_gamma, gl3_intensity, gl3_intensity_2D, gl_anisotropic, gl_texturemode
	global r_lightlevel, gl3_overbrightbits, gl3_particle_fade_factor, gl3_particle_square, gl3_colorlight, gl_polyblend
	global r_modulate, gl_lightmap, gl_shadows, r_fixsurfsky, r_palettedtexture, r_validation, gl3_debugcontext, gl3_show_draw_stats
	global gl1_stereo, gl1_stereo_separation, gl1_stereo_anaglyph_colors, gl1_stereo_convergence
	global gl1_particle_min_size, gl1_particle_max_size, gl1_particle_size, gl1_particle_att_a, gl1_particle_att_b, gl1_particle_att_c
	global r_drawentities, r_lerpmodels, r_speeds
	global r_clear, gl_drawbuffer

	gl_msaa_samples = ri.Cvar_Get ("r_msaa_samples", "0", shared.CVAR_ARCHIVE)
	r_vsync = ri.Cvar_Get ("r_vsync", "1", shared.CVAR_ARCHIVE)
	r_retexturing = ri.Cvar_Get ("r_retexturing", "1", shared.CVAR_ARCHIVE)
	r_scale8bittextures = ri.Cvar_Get ("r_scale8bittextures", "0", shared.CVAR_ARCHIVE)
	vid_fullscreen = ri.Cvar_Get ("vid_fullscreen", "0", shared.CVAR_ARCHIVE)
	r_mode = ri.Cvar_Get ("r_mode", "4", shared.CVAR_ARCHIVE)
	r_customwidth = ri.Cvar_Get ("r_customwidth", "1024", shared.CVAR_ARCHIVE)
	r_customheight = ri.Cvar_Get ("r_customheight", "768", shared.CVAR_ARCHIVE)

	r_2D_unfiltered = ri.Cvar_Get ("r_2D_unfiltered", "0", shared.CVAR_ARCHIVE)
	r_videos_unfiltered = ri.Cvar_Get ("r_videos_unfiltered", "0", shared.CVAR_ARCHIVE)
	gl_nolerp_list = ri.Cvar_Get ("gl_nolerp_list", "", shared.CVAR_ARCHIVE)
	r_lerp_list = ri.Cvar_Get ("r_lerp_list", "", shared.CVAR_ARCHIVE)
	gl_nobind = ri.Cvar_Get ("gl_nobind", "0", shared.CVAR_ARCHIVE)
	gl_showtris = ri.Cvar_Get ("gl_showtris", "0", 0)
	r_lockpvs = ri.Cvar_Get ("r_lockpvs", "0", 0)
	r_clear = ri.Cvar_Get ("r_clear", "1", 0)
	gl_drawbuffer = ri.Cvar_Get ("gl_drawbuffer", "GL_BACK", 0)
	r_novis = ri.Cvar_Get ("r_novis", "0", 0)

	r_cull = ri.Cvar_Get ("r_cull", "1", 0)
	gl_zfix = ri.Cvar_Get ("gl_zfix", "1", shared.CVAR_ARCHIVE)
	r_fullbright = ri.Cvar_Get ("r_fullbright", "0", 0)

	r_norefresh = ri.Cvar_Get ("r_norefresh", "0", 0)
	gl_lefthand = ri.Cvar_Get ("hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	r_gunfov = ri.Cvar_Get ("r_gunfov", "110", shared.CVAR_ARCHIVE)
	r_farsee = ri.Cvar_Get ("r_farsee", "4096", shared.CVAR_ARCHIVE)
	r_drawworld = ri.Cvar_Get ("r_drawworld", "1", 0)

	vid_gamma = ri.Cvar_Get ("vid_gamma", "1.0", shared.CVAR_ARCHIVE)
	gl3_intensity = ri.Cvar_Get ("gl3_intensity", "2", shared.CVAR_ARCHIVE)
	gl3_intensity_2D = ri.Cvar_Get ("gl3_intensity_2D", "2", shared.CVAR_ARCHIVE)
	gl_anisotropic = ri.Cvar_Get ("gl_anisotropic", "1", shared.CVAR_ARCHIVE)
	gl_texturemode = ri.Cvar_Get ("gl_texturemode", "GL_LINEAR_MIPMAP_NEAREST", shared.CVAR_ARCHIVE)

	r_lightlevel = ri.Cvar_Get ("r_lightlevel", "0", 0)
	gl3_overbrightbits = ri.Cvar_Get ("gl3_overbrightbits", "0", shared.CVAR_ARCHIVE)
	gl3_particle_fade_factor = ri.Cvar_Get ("gl3_particle_fade_factor", "1", shared.CVAR_ARCHIVE)
	gl3_particle_square = ri.Cvar_Get ("gl3_particle_square", "0", shared.CVAR_ARCHIVE)
	gl3_colorlight = ri.Cvar_Get ("gl3_colorlight", "1", shared.CVAR_ARCHIVE)
	gl_polyblend = ri.Cvar_Get ("gl_polyblend", "1", shared.CVAR_ARCHIVE)

	r_modulate = ri.Cvar_Get ("r_modulate", "1", shared.CVAR_ARCHIVE)
	gl_lightmap = ri.Cvar_Get ("r_lightmap", "0", 0)
	gl_shadows = ri.Cvar_Get ("r_shadows", "0", shared.CVAR_ARCHIVE)
	r_fixsurfsky = ri.Cvar_Get ("r_fixsurfsky", "0", 0)
	r_palettedtexture = ri.Cvar_Get ("r_palettedtexture", "0", shared.CVAR_ARCHIVE)
	r_validation = ri.Cvar_Get ("r_validation", "0", 0)
	gl3_debugcontext = ri.Cvar_Get ("gl3_debugcontext", "0", 0)
	gl3_show_draw_stats = ri.Cvar_Get ("gl3_show_draw_stats", "0", 0)

	gl1_stereo = ri.Cvar_Get ("gl1_stereo", "0", shared.CVAR_ARCHIVE)
	gl1_stereo_separation = ri.Cvar_Get ("gl1_stereo_separation", "-0.4", shared.CVAR_ARCHIVE)
	gl1_stereo_anaglyph_colors = ri.Cvar_Get ("gl1_stereo_anaglyph_colors", "rc", shared.CVAR_ARCHIVE)
	gl1_stereo_convergence = ri.Cvar_Get ("gl1_stereo_convergence", "1", shared.CVAR_ARCHIVE)
	gl1_particle_min_size = ri.Cvar_Get ("gl1_particle_min_size", "2", shared.CVAR_ARCHIVE)
	gl1_particle_max_size = ri.Cvar_Get ("gl1_particle_max_size", "40", shared.CVAR_ARCHIVE)
	gl1_particle_size = ri.Cvar_Get ("gl1_particle_size", "40", shared.CVAR_ARCHIVE)
	gl1_particle_att_a = ri.Cvar_Get ("gl1_particle_att_a", "0.01", shared.CVAR_ARCHIVE)
	gl1_particle_att_b = ri.Cvar_Get ("gl1_particle_att_b", "0.0", shared.CVAR_ARCHIVE)
	gl1_particle_att_c = ri.Cvar_Get ("gl1_particle_att_c", "0.01", shared.CVAR_ARCHIVE)
	r_drawentities = ri.Cvar_Get ("r_drawentities", "1", 0)
	r_lerpmodels = ri.Cvar_Get ("r_lerpmodels", "1", 0)
	r_speeds = ri.Cvar_Get ("r_speeds", "0", 0)

	ri.Cmd_AddCommand ("imagelist", gl3_image.RI_ImageList_f)
	ri.Cmd_AddCommand ("screenshot", gl3_misc_ScreenShot)
	ri.Cmd_AddCommand ("modellist", gl3_model.RI_Mod_Modellist_f)
	ri.Cmd_AddCommand ("gl_strings", gl3_strings_f)


def gl3_misc_ScreenShot (): #void

	# Q2PORT: placeholder (gl3_misc.c GL3_ScreenShot)
	pass


def gl3_strings_f (): #void

	# Q2PORT: placeholder (gl3_misc.c GL3_Strings)
	ri.Con_Printf (shared.PRINT_ALL, "gl3 renderer strings (not yet ported)\n")


def GL3_Register (): #void

	"""
	Q2PORT: the C GL3_Register sets up the ri callbacks. In the Python port the
	platform (glimp_sdl2) provides them; nothing to do here yet.
	"""
	pass


def GL3_Init (): #void (returns qboolean)

	global gl3state, gl3_particletexture, gl3_notexture
	global gl_vendor_string, gl_renderer_string, gl_version_string, gl_glsl_version_string

	ri.Con_Printf (shared.PRINT_ALL, "Refresh: {}\n".format (REF_VERSION))
	ri.Con_Printf (shared.PRINT_ALL, "Client: {}\n\n".format (common_h.APPNAME))

	# the model matrix at index 0 is always the identity
	transModelMats [0] = local.gl3_identityMat4

	# register cvars
	R_Register ()

	# Q2PORT: gl3's image/model/data subsystems are thin wrappers over gl1's, so
	# bootstrap gl1's cvars and globals first (the C gl3 is self-contained and has
	# no such dependency).
	gl1_main.ri = ri
	gl1_main.R_Register ()
	gl1_image.Draw_GetPalette () # Q2PORT: set up the shared gl1 palette (pics/colormap.pcx)

	# create the window and set up the context (the Python platform already has one)
	glimp_sdl2.GLimp_Init (None, None)

	if not R_SetMode ():
		ri.Con_Printf (shared.PRINT_ALL, "ref_gl3::GL3_Init() - could not R_SetMode()\n")
		return False

	#
	# get our various GL strings
	#
	gl_vendor_string = GL.glGetString (GL.GL_VENDOR)
	gl_renderer_string = GL.glGetString (GL.GL_RENDERER)
	gl_version_string = GL.glGetString (GL.GL_VERSION)
	gl_glsl_version_string = GL.glGetString (GL.GL_SHADING_LANGUAGE_VERSION)

	ri.Con_Printf (shared.PRINT_ALL, "OpenGL features:\n")
	RI_Strings (False)

	# initialize the shaders (creates the UBOs too)
	if not gl3_shaders.GL3_InitShaders ():
		ri.Sys_Error (shared.ERR_FATAL, "GL3_InitShaders() failed\n")

	# initialize the VAOs / VBOs / EBOs
	GL3_Init3Dstate ()

	# initialize the model subsystem
	gl3_model.RI_Init ()

	# particle texture (see gl3_misc.c: GL3_InitParticleTexture)
	dottexture = (
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 1, 1, 0, 0, 0, 0),
		(0, 1, 1, 1, 1, 0, 0, 0),
		(0, 1, 1, 1, 1, 0, 0, 0),
		(0, 0, 1, 1, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
	)

	data = bytearray (8*8*4)
	for x in range(8):
		for y in range(8):
			data[(y*8+x)*4+0] = 255
			data[(y*8+x)*4+1] = 255
			data[(y*8+x)*4+2] = 255
			data[(y*8+x)*4+3] = dottexture[x][y]*255

	gl3_particletexture = gl3_image.RI_LoadPic ("***particle***", data, 8, 8, ref_shared.imagetype_t.it_sprite, 32)

	data = bytearray (8*8*4)
	for x in range(8):
		for y in range(8):
			data[(y*8+x)*4+0] = dottexture[x&3][y&3]*255
			data[(y*8+x)*4+1] = 0
			data[(y*8+x)*4+2] = 0
			data[(y*8+x)*4+3] = 255

	gl3_notexture = gl3_image.RI_LoadPic ("***r_notexture***", data, 8, 8, ref_shared.imagetype_t.it_wall, 32)

	# lightmap
	gl3_lightmap.RI_InitBlock ()

	# surf
	gl3_surf.RI_SurfInit ()

	ri.Con_Printf (shared.PRINT_ALL, "gl3 renderer initialized.\n")

	return True


def GL3_Init3Dstate (): #void

	"""
	Q2PORT: create the VAOs, VBOs and EBOs used for 3D, alias and particle drawing.
	(Matches the VAO setup in the C gl3_main.c / gl3_surf.c / gl3_mesh.c.)
	"""

	# 3D VAO: 10 floats + 1 uint per vertex (gl3_3D_vtx_t)
	gl3state.vao3D = GL.glGenVertexArrays (1)
	GL.glBindVertexArray (gl3state.vao3D)
	gl3state.vbo3D = GL.glGenBuffers (1)
	gl3state.ebo3D = GL.glGenBuffers (1)
	GL.glBindBuffer (GL.GL_ARRAY_BUFFER, gl3state.vbo3D)
	stride = model.GL3_3D_VTX_SIZE * 4
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_POSITION, 3, GL.GL_FLOAT, False, stride, 0)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_TEXCOORD)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, False, stride, 12)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_LMTEXCOORD)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_LMTEXCOORD, 2, GL.GL_FLOAT, False, stride, 20)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_NORMAL)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_NORMAL, 3, GL.GL_FLOAT, False, stride, 28)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_LIGHTFLAGS)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_LIGHTFLAGS, 1, GL.GL_FLOAT, False, stride, 40)
	GL.glBindBuffer (GL.GL_ELEMENT_ARRAY_BUFFER, gl3state.ebo3D)
	GL.glBindVertexArray (0)

	# alias VAO: 9 floats per vertex (gl3_alias_vtx_t)
	gl3state.vaoAlias = GL.glGenVertexArrays (1)
	GL.glBindVertexArray (gl3state.vaoAlias)
	gl3state.vboAlias = GL.glGenBuffers (1)
	gl3state.eboAlias = GL.glGenBuffers (1)
	GL.glBindBuffer (GL.GL_ARRAY_BUFFER, gl3state.vboAlias)
	stride = model.GL3_ALIAS_VTX_SIZE * 4
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_POSITION, 3, GL.GL_FLOAT, False, stride, 0)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_TEXCOORD)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, False, stride, 12)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_COLOR)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_COLOR, 4, GL.GL_FLOAT, False, stride, 20)
	GL.glBindBuffer (GL.GL_ELEMENT_ARRAY_BUFFER, gl3state.eboAlias)
	GL.glBindVertexArray (0)

	# particle VAO: 9 floats (x,y,z, size,distance, r,g,b,a)
	gl3state.vaoParticle = GL.glGenVertexArrays (1)
	GL.glBindVertexArray (gl3state.vaoParticle)
	gl3state.vboParticle = GL.glGenBuffers (1)
	GL.glBindBuffer (GL.GL_ARRAY_BUFFER, gl3state.vboParticle)
	stride = 9 * 4
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_POSITION, 3, GL.GL_FLOAT, False, stride, 0)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_COLOR)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_COLOR, 4, GL.GL_FLOAT, False, stride, 16)
	GL.glBindVertexArray (0)


def GL3_Shutdown (): #void

	gl3_lightmap.RI_ShutdownLightmaps ()
	gl3_shaders.GL3_ShutdownShaders ()
	gl3_mesh.RI_ShutdownMeshes ()
	gl3_surf.RI_SurfShutdown ()
	gl3_image.RI_ShutdownImages ()


def R_SetMode (): #void (returns qboolean)

	global vid, r_mode, vid_fullscreen, gl3state

	#rserr_t err;
	#qboolean fullscreen;

	# Q2PORT: the port's CDS always lands in the requested mode (glimp_sdl2), so
	# there is no allow_cds check like the C's.
	fullscreen = vid_fullscreen.value

	vid_fullscreen.modified = False
	r_mode.modified = False

	err, vid.width, vid.height = glimp_sdl2.GLimp_SetMode (vid.width, vid.height, r_mode.value, fullscreen)
	if err == rserr_t.rserr_ok:

		gl3state.prev_mode = r_mode.value

	else:
		if err == rserr_t.rserr_invalid_fullscreen:

			ri.Cvar_SetValue ("vid_fullscreen", 0)
			vid_fullscreen.modified = False
			ri.Con_Printf (shared.PRINT_ALL, "ref_gl3::R_SetMode() - fullscreen unavailable in this mode\n")
			err, vid.width, vid.height = glimp_sdl2.GLimp_SetMode (vid.width, vid.height, r_mode.value, False)
			if err == rserr_t.rserr_ok:
				return True

		elif err == rserr_t.rserr_invalid_mode:

			ri.Cvar_SetValue ("r_mode", gl3state.prev_mode)
			r_mode.modified = False
			ri.Con_Printf (shared.PRINT_ALL, "ref_gl3::R_SetMode() - invalid mode\n")

		# try setting it back to something safe
		err, vid.width, vid.height = glimp_sdl2.GLimp_SetMode (vid.width, vid.height, gl3state.prev_mode, False)
		if err != rserr_t.rserr_ok:

			ri.Con_Printf (shared.PRINT_ALL, "ref_gl3::R_SetMode() - could not revert to safe mode\n")
			return False

	return True


def RI_Init (hinstance, hWnd): #void *, void * (returns rserr_t)

	# Q2PORT: id-style Init(hinstance, hWnd) entry point (vid.py calls re.Init(0,0))
	if not GL3_Init ():
		return rserr_t.rserr_invalid_mode
	return rserr_t.rserr_ok


def RI_Shutdown (): #void

	global gl3state

	RI_ShutdownLocal ()
	gl3state.currentShaderProgram = 0
	gl3state.currentVAO = 0
	gl3state.currentVBO = 0
	gl3state.currentEBO = 0
	gl3state = local.gl3state_t ()


def RI_ShutdownLocal (): #void

	pass


def RI_SetPalette (palette): #byte *

	gl3_image.RI_SetPalette (palette)


def GL3_SetGL2D (): #void

	x = 0
	w = vid.width
	y = 0
	h = vid.height

	# Q2PORT: the C's stereo block here is #if 0 (TODO: stereo)

	GL.glViewport (x, y, w, h)

	transMatr = hmm.HMM_Orthographic (0, vid.width, vid.height, 0, -99999, 99999)

	gl3state.uni2DData [local.UNI2D_TRANS:local.UNI2D_TRANS + 16] = transMatr.flatten (order="F")

	gl3_shaders.GL3_UpdateUBO2D ()

	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glDisable (GL.GL_CULL_FACE)
	GL.glDisable (GL.GL_BLEND)


def GL3_Clear (): #void

	global gl3depthmin, gl3depthmax

	# Define which buffers need clearing
	clearFlags = GL.GL_DEPTH_BUFFER_BIT

	if r_clear.value:

		clearFlags |= GL.GL_COLOR_BUFFER_BIT

	# Stencilbuffer shadows
	if gl_shadows.value and gl3config.stencil:

		GL.glClearStencil (1)
		clearFlags |= GL.GL_STENCIL_BUFFER_BIT

	# Q2PORT: the C's stereo and GLES blocks are #if 0 / not the desktop port

	GL.glClear (clearFlags)

	gl3depthmin = 0
	gl3depthmax = 1
	GL.glDepthFunc (GL.GL_LEQUAL)
	GL.glDepthRange (gl3depthmin, gl3depthmax)

	if gl_zfix.value:

		if gl3depthmax > gl3depthmin:

			GL.glPolygonOffset (0.05, 1)
		elif gl3depthmax < gl3depthmin:

			GL.glPolygonOffset (-0.05, -1)


def GL3_TextureMode (string): #char *

	global gl_filter_min, gl_filter_max

	modes = (
		("GL_NEAREST", GL.GL_NEAREST, GL.GL_NEAREST),
		("GL_LINEAR", GL.GL_LINEAR, GL.GL_LINEAR),
		("GL_LINEAR_MIPMAP_NEAREST", GL.GL_LINEAR, GL.GL_NEAREST_MIPMAP_LINEAR),
		("GL_NEAREST_MIPMAP_LINEAR", GL.GL_NEAREST, GL.GL_LINEAR_MIPMAP_LINEAR),
		("GL_LINEAR_MIPMAP_LINEAR", GL.GL_LINEAR, GL.GL_LINEAR_MIPMAP_LINEAR),
		("GL_NEAREST_MIPMAP_NEAREST", GL.GL_NEAREST, GL.GL_NEAREST_MIPMAP_NEAREST),
	)

	i = 0
	for name, mn, mx in modes:

		if name.lower () == string.lower ():
			break
		i += 1

	if i == len (modes):

		ri.Con_Printf (shared.PRINT_ALL, "bad filter name '{}' (probably from gl_texturemode)\n".format (string))
		return

	gl_filter_min, gl_filter_max = modes[i][1], modes[i][2]

	# Q2PORT: the C now walks every texture object and re-sets their parameters. The
	# port applies them at bind time instead (gl1_image), so there is nothing to do.


def GL3_SetVsync (): #void

	# Q2PORT: the pygame/SDL platform applies vsync through its swap interval; the
	# cvar change is acknowledged by the caller clearing r_vsync.modified.
	pass


def RI_BeginFrame (camera_separation): #float

	# Q2PORT: the C's stereo block (gl_state.camera_separation / gl1_stereo) is #if 0

	if vid_gamma.modified or gl3_intensity.modified or gl3_intensity_2D.modified:

		vid_gamma.modified = False
		gl3_intensity.modified = False
		gl3_intensity_2D.modified = False

		gl3state.uniCommonData [local.UNICOMMON_GAMMA] = 1.0/vid_gamma.value
		gl3state.uniCommonData [local.UNICOMMON_INTENSITY] = gl3_intensity.value
		gl3state.uniCommonData [local.UNICOMMON_INTENSITY2D] = gl3_intensity_2D.value
		gl3_shaders.GL3_UpdateUBOCommon ()

	# in GL3, overbrightbits can have any positive value
	if gl3_overbrightbits.modified:

		gl3_overbrightbits.modified = False

		if gl3_overbrightbits.value < 0.0:

			ri.Cvar_Set ("gl3_overbrightbits", "0")

		gl3state.uni3DData [local.UNI3D_OVERBRIGHTBITS] = 1.0 if gl3_overbrightbits.value <= 0.0 else gl3_overbrightbits.value
		gl3_shaders.GL3_UpdateUBO3D ()

	if gl3_particle_fade_factor.modified:

		gl3_particle_fade_factor.modified = False
		gl3state.uni3DData [local.UNI3D_PARTICLEFADEFATOR] = gl3_particle_fade_factor.value
		gl3_shaders.GL3_UpdateUBO3D ()

	if gl3_particle_square.modified or gl3_colorlight.modified:

		gl3_particle_square.modified = False
		gl3_colorlight.modified = False
		gl3_shaders.GL3_RecreateShaders ()

	# go into 2D mode

	GL3_SetGL2D ()

	# draw buffer stuff
	if gl_drawbuffer.modified:

		gl_drawbuffer.modified = False

		# Q2PORT: the C's GLES check is not the desktop port
		drawBuffer = GL.GL_BACK
		if gl_drawbuffer.string == "GL_FRONT":
			drawBuffer = GL.GL_FRONT
		GL.glDrawBuffer (drawBuffer)

	# texturemode stuff
	if gl_texturemode.modified or gl_anisotropic.modified \
		or gl_nolerp_list.modified or r_lerp_list.modified \
		or r_2D_unfiltered.modified or r_videos_unfiltered.modified:

		GL3_TextureMode (gl_texturemode.string)
		gl_texturemode.modified = False
		gl_anisotropic.modified = False
		gl_nolerp_list.modified = False
		r_lerp_list.modified = False
		r_2D_unfiltered.modified = False
		r_videos_unfiltered.modified = False

	if r_vsync.modified:

		r_vsync.modified = False
		GL3_SetVsync ()

	# clear screen if desired
	GL3_Clear ()


#
# rendering
#

r_newrefdef = ref.refdef_t () #refdef_t
r_refdef = ref.refdef_t () #refdef_t

lightmaplist = [] #static msurface_t lightmaplist[1024], replaced by a list


def RI_SetupFrame (): #void

	global r_refdef

	# a new frame, clear the lightmap chain
	lightmaplist.clear ()


def RI_RenderFrame (fd): #refdef_t *

	global r_refdef

	# update cvars that can change per frame
	local.gl3_num3Ddraws = 0
	local.gl3_num2Ddraws = 0
	local.gl3_numBufferVtxData = 0
	local.gl3_numBufferUniforms = 0

	r_refdef = fd

	# Q2PORT: gl3 delegates the world/sky/warp draw to gl1, which reads gl1's render
	# state (r_newrefdef, r_origin, ...), so mirror the refdef into gl1 each frame.
	gl1_main.r_newrefdef = fd
	gl1_main.r_origin [:] = fd.vieworg

	# update uniforms
	gl3_shaders.GL3_UpdateUBOCommon ()
	gl3_shaders.GL3_UpdateUBO2D ()

	RI_RenderView (fd)


def RI_PostRender (): #void

	"""
	Q2PORT: draws the frame buffer object (post-processing) if under water.
	"""
	# handled in gl3_draw / gl3_warp
	pass


def RI_RenderView (fd): #refdef_t *

	global r_lightstyle_value

	#
	# update lightstyles
	#
	n = 0
	lightstyles = fd.lightstyles
	while n < len (lightstyles) and n < MAXLIGHTSTYLES:
		ls = lightstyles[n]
		if not (ls.rgb[0] == 0.0 and ls.rgb[1] == 0.0 and ls.rgb[2] == 0.0):
			r_lightstyle_value [n] = ls.rgb[0] + ls.rgb[1] + ls.rgb[2]
		else:
			r_lightstyle_value [n] = 1.0
		n += 1

	# set up the view matrices
	RI_SetupMatrices (fd)

	RI_RenderScene (fd)


def RI_SetupMatrices (fd): #refdef_t *

	global gl3state

	# projection matrix
	gl3state.uni3DData [local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16] = _projection_mat (fd).flatten (order = "F")

	# view matrix (lookat)
	viewmat = _lookat_mat (fd)
	gl3state.uni3DData [local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16] = hmm.HMM_MultiplyMat4 (gl3state.uni3DData [local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16].reshape (4, 4), viewmat).flatten (order = "F")

	gl3state.uni3DData [local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = local.gl3_identityMat4.flatten (order = "F")
	gl3state.uni3DData [local.UNI3D_TIME] = fd.time
	gl3state.uni3DData [local.UNI3D_ALPHA] = 1.0


def _projection_mat (fd): #refdef_t * (returns hmm_mat4)

	# Q2PORT: frustum projection (matches gl1's R_SetupProjectionMatrix)
	fov = fd.fov_x
	aspect = fd.width / fd.height
	neart = 4.0
	fart = float (r_farsee.value)

	a = 1.0 / np.tan (np.radians (fov / 2.0))
	b = 1.0 / np.tan (np.radians (90.0 - fov) / 2.0)

	# build the frustum projection matrix (column-major)
	proj = np.zeros ((4, 4), dtype = np.float32)
	proj[0][0] = a / aspect
	proj[1][1] = a
	proj[2][2] = (fart + neart) / (neart - fart)
	proj[3][2] = (2 * fart * neart) / (neart - fart)
	proj[2][3] = -1.0
	return proj


def _lookat_mat (fd): #refdef_t * (returns hmm_mat4)

	# Q2PORT: view matrix (eye at vieworg looking along the view angles)
	eye = fd.vieworg
	fwd = np.array ([np.cos (np.radians (-fd.viewangles[1])) * np.cos (np.radians (fd.viewangles[0])),
	                 np.sin (np.radians (-fd.viewangles[1])) * np.cos (np.radians (fd.viewangles[0])),
	                 np.sin (np.radians (fd.viewangles[0]))], dtype = np.float32)
	# NOTE: proper Quake II view matrix (pitch/yaw/roll) built from the baseangles
	# Q2PORT: simplified for the initial bring-up
	f = fwd
	f = f / np.linalg.norm (f)
	up = np.array ([0, 0, 1], dtype = np.float32)
	s = np.cross (f, up); s = s / np.linalg.norm (s)
	u = np.cross (s, f)

	view = np.zeros ((4, 4), dtype = np.float32)
	view[0][0] = s[0]; view[0][1] = s[1]; view[0][2] = s[2]
	view[1][0] = u[0]; view[1][1] = u[1]; view[1][2] = u[2]
	view[2][0] = -f[0]; view[2][1] = -f[1]; view[2][2] = -f[2]
	view[0][3] = -float (np.dot (s, eye))
	view[1][3] = -float (np.dot (u, eye))
	view[2][3] = float (np.dot (f, eye))
	view[3][3] = 1.0
	return view


def RI_RenderScene (fd): #refdef_t *

	# mark leaves and surfaces
	gl3_surf.RI_MarkLeaves (fd)

	# build the lightmap chain (lightmapped surfaces)
	RI_BeginBuildingLightmaps ()

	# draw the world (brush models)
	if r_drawworld.value != 0:
		gl3_surf.RI_DrawWorld (fd)

	# draw entities
	if r_drawentities.value != 0:
		gl3_mesh.RI_DrawEntities (fd)

	# draw particles
	gl3_mesh.RI_DrawParticles (fd)

	# upload the lightmap
	gl3_lightmap.RI_UploadBlock ()

	# draw the 2D overlay
	RI_PostRender ()


def RI_BeginBuildingLightmaps (): #void

	pass


def RI_Strings (full): #qboolean

	ri.Con_Printf (shared.PRINT_ALL, "GL_RENDERER: {}\n".format (gl_renderer_string))
	ri.Con_Printf (shared.PRINT_ALL, "GL_VENDOR: {}\n".format (gl_vendor_string))
	ri.Con_Printf (shared.PRINT_ALL, "GL_VERSION: {}\n".format (gl_version_string))
	ri.Con_Printf (shared.PRINT_ALL, "GL_SHADING_LANGUAGE_VERSION: {}\n".format (gl_glsl_version_string))


#
# registration
#

def RI_BeginRegistration (map_): #char *

	global registration_sequence

	registration_sequence += 1
	gl3_image.RI_BeginRegistration (registration_sequence)
	gl3_model.RI_BeginRegistration (map_)


def RI_RegisterModel (name): #char * (returns model_t *)

	return gl3_model.RI_RegisterModel (name)


def RI_RegisterSkin (name): #char * (returns gl3image_t *)

	return gl3_image.RI_RegisterSkin (name)


def RI_SetSky (name, rotate, axis): #char *, float, vec3_t

	gl3_warp.RI_SetSky (name, rotate, axis)


def RI_EndRegistration (): #void

	gl3_image.RI_EndRegistration ()
	gl3_model.RI_EndRegistration ()


#
# GetRefAPI
#

def GetRefAPI (rimp): #refimport_t (returns refexport_t)

	global ri

	re = ref.refexport_t ()

	ri = rimp

	re.api_version = ref.API_VERSION

	re.BeginRegistration = RI_BeginRegistration
	re.RegisterModel = RI_RegisterModel
	re.RegisterSkin = RI_RegisterSkin
	re.SetSky = RI_SetSky
	re.EndRegistration = RI_EndRegistration

	re.RenderFrame = RI_RenderFrame

	re.DrawGetPicSize = gl3_draw.RDraw_GetPicSize
	re.DrawStretchPic = gl3_draw.RDraw_StretchPic
	re.DrawCharScaled = gl3_draw.RDraw_CharScaled
	re.DrawPicScaled = gl3_draw.RDraw_PicScaled
	re.DrawPicScaledCol = gl3_draw.RDraw_PicScaledCol
	re.DrawFindPic = gl3_draw.RDraw_FindPic
	re.DrawTileClear = gl3_draw.RDraw_TileClear
	re.DrawFill = gl3_draw.RDraw_Fill
	re.DrawFadeScreen = gl3_draw.RDraw_FadeScreen
	re.DrawStretchRaw = gl3_draw.RDraw_StretchRaw

	re.Init = RI_Init
	re.Shutdown = RI_Shutdown

	re.SetPalette = RI_SetPalette

	re.BeginFrame = RI_BeginFrame
	re.EndFrame = glimp_sdl2.GLimp_EndFrame

	re.AppActivate = glimp_sdl2.GLimp_AppActivate

	shared_swap_init ()

	return re


def shared_swap_init (): #void

	from common.shared import shared as shared_c
	shared_c.Swap_Init ()
