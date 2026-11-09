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
 * gl3_warp.c - water/sky for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

from client.refresh.gl1 import gl1_warp
from client.refresh.gl3 import gl3_main


def RI_SetSky (name, rotate, axis): #char *, float, vec3_t

	gl1_warp.RI_SetSky (name, rotate, axis)


def RI_DrawSkyBox (): #void

	"""
	Q2PORT: the sky box is drawn via the gl3 sky shader (si3Dsky). The sky data
	(skymap, rotation) comes from gl1_warp (shared). For now, reuse gl1's sky
	draw path which operates on the shared skymap textures.
	"""
	gl1_warp.R_DrawSkyBox ()


def RI_ClearSkyBox (): #void

	gl1_warp.R_ClearSkyBox ()


def RI_AddSkySurface (fa): #msurface_t *

	gl1_warp.R_AddSkySurface (fa)


def RI_EmitWaterPolys (fa): #msurface_t *

	gl1_warp.R_EmitWaterPolys (fa)


def RI_SubdivideSurface (fa): #msurface_t *

	gl1_warp.R_SubdivideSurface (fa)
