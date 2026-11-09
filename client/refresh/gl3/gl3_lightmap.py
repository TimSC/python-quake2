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
 * gl3_lightmap.c - lightmaps for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

from client.refresh.gl1 import gl1_lightmap

# Q2PORT: gl3's lightmap uses a 1024x512 block with 4 sub-lightmaps per surface
# (GL_TEXTURE1..4). For the initial bring-up, reuse gl1's per-surface lightmap
# building and upload; the texture is bound to GL_TEXTURE1 (see gl3_image.RI_BindLightmap).

gl3_lms = None #gl3lightmapstate_t, set by the main module


def RI_InitBlock (): #void

	gl1_lightmap.LM_InitBlock ()


def RI_UploadBlock (dynamic=None): #qboolean

	return gl1_lightmap.LM_UploadBlock (dynamic)


def RI_AllocBlock (w, h): #int, int (returns qboolean, int x, int y)

	return gl1_lightmap.LM_AllocBlock (w, h)


def RI_BuildPolygonFromSurface (currentmodel, fa): #model_t *, msurface_t *

	gl1_lightmap.LM_BuildPolygonFromSurface (currentmodel, fa)


def RI_CreateSurfaceLightmap (surf): #msurface_t *

	gl1_lightmap.LM_CreateSurfaceLightmap (surf)


def RI_BeginBuildingLightmaps (m): #model_t *

	gl1_lightmap.LM_BeginBuildingLightmaps (m)


def RI_EndBuildingLightmaps (): #void

	gl1_lightmap.LM_EndBuildingLightmaps ()


def RI_ShutdownLightmaps (): #void

	gl1_lightmap.LM_FreeLightmapBuffers ()
