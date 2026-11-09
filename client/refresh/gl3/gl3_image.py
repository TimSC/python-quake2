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
 * gl3_image.c - textures for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

from client.refresh.gl1 import gl1_image, gl1_main
from client.refresh import ref_shared
from client.refresh.gl3 import gl3_main

# Q2PORT: the image_t struct is duck-type compatible with gl3image_t (the only
# extra gl3 field, is_lava, defaults to False via getattr). Only one renderer is
# active at a time, so gl3 reuses gl1_image's loading and GL texture upload.

gl3_scrap_dirty = False #qboolean


def RI_FindPic (name): #char * (returns gl3image_t *)

	return gl1_image.R_FindImage (name, ref_shared.imagetype_t.it_pic)


def RI_FindImage (name, imgType): #char *, imagetype_t (returns gl3image_t *)

	return gl1_image.R_FindImage (name, imgType)


def RI_RegisterSkin (name): #char * (returns gl3image_t *)

	return gl1_image.RI_RegisterSkin (name)


def RI_LoadPic (name, pic, width, height, imgType, bits):

	return gl1_image.R_LoadPic (name, pic, width, height, imgType, bits)


def RI_ShutdownImages (): #void

	gl1_image.R_ShutdownImages ()


def RI_FreeUnusedImages (): #void

	gl1_image.R_FreeUnusedImages ()


def RI_BeginRegistration (registration_sequence): #int

	# Q2PORT: bump the shared registration sequence (gl1_model owns it)
	gl3_main.registration_sequence = registration_sequence


def RI_EndRegistration (): #void

	gl1_image.R_FreeUnusedImages ()


def RI_ImageList_f (): #void

	gl1_image.R_ImageList_f ()


def RI_SetPalette (palette): #byte *

	from client.refresh.gl1 import gl1_main
	# Q2PORT: reuse gl1's palette handling
	gl1_main.RI_SetPalette (palette)


def RI_Bind (texnum): #GLuint (returns qboolean)

	"""
	Q2PORT: bind a texture to GL_TEXTURE0 (gl3_bind helper from the C gl3_image.c).
	"""
	from OpenGL import GL
	if gl3_main.gl3state.currenttexture == texnum:
		return True
	if texnum == 0:
		texnum = gl1_main.r_notexture.texnum
	if gl3_main.gl_nobind.value:
		texnum = 0
	gl3_main.gl3state.currenttexture = texnum
	from client.refresh.gl3.header import local
	local.GL3_SelectTMU (GL.GL_TEXTURE0)
	GL.glBindTexture (GL.GL_TEXTURE_2D, texnum)
	return True


def RI_BindLightmap (lightmapnum): #int

	from OpenGL import GL
	from client.refresh.gl3.header import local
	# bind the lightmap texture to GL_TEXTURE1
	texnum = gl3_main.gl3state.lightmap_textureIDs [lightmapnum][0]
	from client.refresh.gl1 import gl1_image, gl1_main
	if texnum == 0:
		texnum = gl1_main.r_notexture.texnum
	local.GL3_SelectTMU (GL.GL_TEXTURE1)
	GL.glBindTexture (GL.GL_TEXTURE_2D, texnum)
	gl3_main.gl3state.currentlightmap = lightmapnum
