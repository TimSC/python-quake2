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
 * gl3_mesh.c - alias models and particles for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from OpenGL import GL
from client.refresh.gl3 import gl3_main
from client.refresh.gl3.header import local
from client.refresh.gl3 import gl3_shaders


def RI_ShutdownMeshes (): #void

	# Q2PORT: free per-model alias VBOs (none allocated yet)
	pass


def RI_DrawEntities (fd): #refdef_t *

	"""
	Q2PORT: draw the alias entities (weapons, players, monsters). The full
	alias VBO build + drawCmd batching is the remaining deep work.
	"""
	pass


def RI_DrawParticles (fd): #refdef_t *

	"""
	Q2PORT: draw the frame's particles as point sprites via siParticle.
	"""
	n = fd.num_particles
	if n <= 0:
		return

	local.GL3_UseProgram (gl3_main.gl3state.siParticle.shaderProgram)
	gl3_shaders.GL3_UpdateUBO3D ()
	local.GL3_BindVAO (gl3_main.gl3state.vaoParticle)
	local.GL3_BindVBO (gl3_main.gl3state.vboParticle)

	# build the particle vertex array (x,y,z, size, r,g,b,a)
	verts = np.zeros (n * 9, dtype = np.float32)
	i = 0
	while i < n:
		p = fd.particles[i]
		base = i * 9
		verts[base] = p.org[0]
		verts[base + 1] = p.org[1]
		verts[base + 2] = p.org[2]
		verts[base + 3] = 1.0 # size
		verts[base + 4] = p.color[0]
		verts[base + 5] = p.color[1]
		verts[base + 6] = p.color[2]
		verts[base + 7] = 1.0 # alpha
		i += 1

	GL.glBufferData (GL.GL_ARRAY_BUFFER, verts.nbytes, verts, GL.GL_DYNAMIC_DRAW)
	local.gl3_num3Ddraws += 1
	GL.glDrawArrays (GL.GL_POINTS, 0, n)


def RI_DrawAlias (entity, loadmodel): #entity_t *, model_t *

	pass


def RI_LerpModel (oldModel, newModel, currenttime, ent): #model_t *, model_t *, float, entity_t *

	# Q2PORT: model lerping (reuses the shared model frame data)
	pass
