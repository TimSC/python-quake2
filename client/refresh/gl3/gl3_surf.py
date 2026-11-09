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
 * gl3_surf.c - 3D world surfaces for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from OpenGL import GL
from client.refresh.gl1 import gl1_surf
from client.refresh.gl1 import gl1_warp
from client.refresh.gl3 import gl3_main
from client.refresh.gl3.header import local
from client.refresh.gl3 import gl3_shaders


def RI_SurfInit (): #void

	# Q2PORT: no per-surface state to allocate beyond what gl1 sets up
	pass


def RI_SurfShutdown (): #void

	pass


def RI_MarkLeaves (fd): #refdef_t *

	"""
	Q2PORT: leaf/surface marking for the gl3 renderer. The full PVS traversal
	reads gl3_main's state (r_worldmodel, r_viewcluster); this is the remaining
	deep work. For now, mark everything (no-op) so the world draw can proceed.
	"""
	pass


def RI_DrawWorld (fd): #refdef_t *

	"""
	Q2PORT: minimal world draw — clear, then draw the sky. The full per-surface
	gl3_3D_vtx_t drawCmd batching is the remaining deep work.
	"""
	GL.glClearColor (0.0, 0.0, 0.0, 1.0)
	GL.glClear (GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

	# draw the sky
	local.GL3_UseProgram (gl3_main.gl3state.si3Dsky.shaderProgram)
	gl3_shaders.GL3_UpdateUBO3D ()
	gl3_warp_RI_DrawSkyBox ()

	local.gl3_num3Ddraws += 1


def gl3_warp_RI_DrawSkyBox (): #void

	from client.refresh.gl3 import gl3_warp
	gl3_warp.RI_DrawSkyBox ()


def RI_DrawAlphaSurfaces (fd): #refdef_t *

	pass


def RI_DrawGLPoly (fa, drawCmd): #msurface_t *, gl3drawCmd_t

	pass


def RI_DrawGLFlowingPoly (fa, drawCmd): #msurface_t *, gl3drawCmd_t

	pass
