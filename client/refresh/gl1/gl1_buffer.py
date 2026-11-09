"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 * Copyright (C) 2024-2025 Jaime Moreira
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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * Drawing buffer: sort of a "Q3A shader" handler, allows to join multiple
 * draw calls into one, by grouping/batching those which share the same
 * characteristics (mostly the same texture).
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL

from client.refresh.gl1 import gl1_image, gl1_main
from client.refresh.gl1.header import model
from common.header import shared


MAX_VERTICES	= 16384
MAX_INDICES 	= (MAX_VERTICES * 4)

MAX_TEXTURE_UNITS	= 2

MAX_LIGHTMAPS	= 128


class buffered_draw_t(object):

	def __init__(self):
		pass


buf_2d			= 0
buf_singletex	= 1
buf_mtex		= 2
buf_alpha		= 3
buf_alias		= 4
buf_flash		= 5
buf_shadow		= 6


class glbuffer_t(object):

	def __init__(self):

		self.type = buf_singletex #buffered_draw_t

		self.vtx = np.zeros((MAX_VERTICES * 3,), dtype=np.float32) #GLfloat [MAX_VERTICES*3], vertexes
		self.tex = [np.zeros((MAX_VERTICES * 2,), dtype=np.float32) for _ in range(MAX_TEXTURE_UNITS)] #GLfloat [MAX_TEXTURE_UNITS][MAX_VERTICES*2], texture coords

		self.clr = np.zeros((MAX_VERTICES * 4,), dtype=np.uint8) #GLubyte [MAX_VERTICES*4], color components

		self.idx = np.zeros((MAX_INDICES,), dtype=np.uint16) #GLushort [MAX_INDICES], indices for the draw call

		self.vt, self.tx, self.cl = 0, 0, 0 #GLuint, indices for the first 3 arrays above

		self.texture = [0, 0] #int [MAX_TEXTURE_UNITS]
		self.flags = 0 #int, entity flags
		self.alpha = 0.0 #float


gl_buf = glbuffer_t()	# our drawing buffer, used globally
cur_lm_copy = 0 #int, which lightmap copy to use (when tilerendering=on)

vtx_ptr = 0 #static GLushort, pointers for array positions in gl_buf
idx_ptr = 0 #static GLushort


def GLBUFFER_RESET(): # vtx_ptr = idx_ptr = 0; gl_buf.vt = gl_buf.tx = gl_buf.cl = 0
	global vtx_ptr, idx_ptr

	vtx_ptr = idx_ptr = 0
	gl_buf.vt = gl_buf.tx = gl_buf.cl = 0


def GLBUFFER_VERTEX(X, Y, Z):
	gl_buf.vtx[gl_buf.vt] = X; gl_buf.vtx[gl_buf.vt+1] = Y
	gl_buf.vtx[gl_buf.vt+2] = Z; gl_buf.vt += 3


def GLBUFFER_SINGLETEX(S, T):
	gl_buf.tex[0][gl_buf.tx] = S; gl_buf.tex[0][gl_buf.tx+1] = T; gl_buf.tx += 2


def GLBUFFER_MULTITEX(CS, CT, LS, LT):
	gl_buf.tex[0][gl_buf.tx] = CS; gl_buf.tex[0][gl_buf.tx+1] = CT
	gl_buf.tex[1][gl_buf.tx] = LS; gl_buf.tex[1][gl_buf.tx+1] = LT; gl_buf.tx += 2


def GLBUFFER_COLOR(R, G, B, A):
	gl_buf.clr[gl_buf.cl] = gl1_image.gammatable[R]; gl_buf.clr[gl_buf.cl+1] = gl1_image.gammatable[G]
	gl_buf.clr[gl_buf.cl+2] = gl1_image.gammatable[B]; gl_buf.clr[gl_buf.cl+3] = A; gl_buf.cl += 4


def R_ResetGLBuffer(): #void

	GLBUFFER_RESET()


"""
 * Draws what's stored in the buffer and clears it up
"""
def R_ApplyGLBuffer(): #void

	# Properties of batched draws here
	# GLint vtx_size;
	# qboolean texture, mtex, alpha, color, alias, texenv_set;

	if vtx_ptr == 0 or idx_ptr == 0:

		return

	# defaults for drawing (mostly buf_singletex features)
	vtx_size = 3
	texture = True
	mtex = alpha = color = alias = texenv_set = False

	# choosing features by type
	if gl_buf.type == buf_2d:
		vtx_size = 2
	elif gl_buf.type == buf_mtex:
		mtex = True
	elif gl_buf.type == buf_alpha:
		alpha = True
	elif gl_buf.type == buf_alias:
		alias = True
		color = True
	elif gl_buf.type == buf_flash:
		color = True
		# fall through
		texture = False
	elif gl_buf.type == buf_shadow:
		texture = False

	gl1_image.R_EnableMultitexture(mtex)

	if alias:

		if gl_buf.flags & shared.RF_DEPTHHACK:
			# hack the depth range to prevent view model from poking into walls
			GL.glDepthRange(gl1_main.gldepthmin, gl1_main.gldepthmin + 0.3 * (gl1_main.gldepthmax - gl1_main.gldepthmin))

		if gl_buf.flags & shared.RF_WEAPONMODEL:
			GL.glMatrixMode(GL.GL_PROJECTION)
			GL.glPushMatrix()
			GL.glLoadIdentity()

			if gl1_main.gl_lefthand.value == 1.0:
				GL.glScalef(-1, 1, 1)

			gl1_main.R_SetPerspective ( (gl1_main.r_gunfov.value < 0) and gl1_main.r_newrefdef.fov_y or gl1_main.r_gunfov.value )

			GL.glMatrixMode(GL.GL_MODELVIEW)

			if gl1_main.gl_lefthand.value == 1.0:
				GL.glCullFace(GL.GL_BACK)

		GL.glShadeModel(GL.GL_SMOOTH)
		gl1_image.R_TexEnv(GL.GL_MODULATE)

		if gl_buf.flags & shared.RF_TRANSLUCENT:
			GL.glEnable(GL.GL_BLEND)

		if gl_buf.flags & (shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE | shared.RF_SHELL_HALF_DAM):
			texture = False
			GL.glDisable(GL.GL_TEXTURE_2D)

	if alpha:
		# the textures are prescaled up for a better
		# lighting range, so scale it back down
		GL.glColor4f(gl1_main.gl_state.inverse_intensity, gl1_main.gl_state.inverse_intensity,
					gl1_main.gl_state.inverse_intensity, gl_buf.alpha)

	elif gl_buf.flags & model.SURF_DRAWTURB:
		texenv_set = True

		# This is a hack ontop of a hack. Warping surfaces like those generated
		# by R_EmitWaterPolys() don't have a lightmap. Original Quake II therefore
		# negated the global intensity on those surfaces, because otherwise they
		# would show up much too bright. When we implemented overbright bits this
		# hack modified the global GL state in an incompatible way. So implement
		# a new hack, based on overbright bits... Depending on the value set to
		# gl1_overbrightbits the result is different:

		#  0: Old behaviour.
		#  1: No overbright bits on the global scene but correct lighting on
		#     warping surfaces.
		#  2,4: Overbright bits on the global scene but not on warping surfaces.
		#       They oversaturate otherwise.

		if gl1_main.gl1_overbrightbits.value:
			gl1_image.R_TexEnv(GL.GL_COMBINE)
			GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_RGB_SCALE, 1)
		else:
			gl1_image.R_TexEnv(GL.GL_MODULATE)
			GL.glColor4f(gl1_main.gl_state.inverse_intensity, gl1_main.gl_state.inverse_intensity,
						gl1_main.gl_state.inverse_intensity, 1.0)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
	GL.glVertexPointer (vtx_size, GL.GL_FLOAT, 0, gl_buf.vtx)

	if texture:
		if mtex:
			# TMU 1: Lightmap texture
			lmtexture = gl1_main.gl_state.lightmap_textures + gl_buf.texture[1]
			if gl1_main.gl_config.tilerendering:
				# Bind appropiate lightmap copy for this frame
				lmtexture += MAX_LIGHTMAPS * cur_lm_copy
			gl1_image.R_MBind(GL.GL_TEXTURE1, lmtexture)

			if gl1_main.gl1_overbrightbits.value:
				gl1_image.R_TexEnv(GL.GL_COMBINE)
				GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_RGB_SCALE, gl1_main.gl1_overbrightbits.value)

			GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
			GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, gl_buf.tex[1])

			# TMU 0: Color texture
			gl1_image.R_MBind(GL.GL_TEXTURE0, gl_buf.texture[0])
		else:
			gl1_image.R_Bind(gl_buf.texture[0])

		GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
		GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, gl_buf.tex[0])

	if color:
		GL.glEnableClientState(GL.GL_COLOR_ARRAY)
		GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, 0, gl_buf.clr)

	# All set, we can finally draw
	GL.glDrawElements(GL.GL_TRIANGLES, idx_ptr, GL.GL_UNSIGNED_SHORT, gl_buf.idx)
	# ... and now, turn back everything as it was

	if color:
		GL.glDisableClientState(GL.GL_COLOR_ARRAY)

	if texture:
		GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	if texenv_set:
		gl1_image.R_TexEnv(GL.GL_REPLACE)

	if alias:
		if gl_buf.flags & (shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE | shared.RF_SHELL_HALF_DAM):
			GL.glEnable(GL.GL_TEXTURE_2D)

		if gl_buf.flags & shared.RF_TRANSLUCENT:
			GL.glDisable(GL.GL_BLEND)

		gl1_image.R_TexEnv(GL.GL_REPLACE)
		GL.glShadeModel(GL.GL_FLAT)

		if gl_buf.flags & shared.RF_WEAPONMODEL:
			GL.glMatrixMode(GL.GL_PROJECTION)
			GL.glPopMatrix()
			GL.glMatrixMode(GL.GL_MODELVIEW)
			if gl1_main.gl_lefthand.value == 1.0:
				GL.glCullFace(GL.GL_FRONT)

		if gl_buf.flags & shared.RF_DEPTHHACK:
			GL.glDepthRange(gl1_main.gldepthmin, gl1_main.gldepthmax)

	GLBUFFER_RESET()


"""
 * Sets current state of the buffer. Any change means "draw its contents now".
"""
def R_UpdateGLBuffer(type, colortex, lighttex, flags, alpha): #buffered_draw_t, int, int, int, float

	if ( gl_buf.type != type or gl_buf.texture[0] != colortex or
		(gl1_main.gl_config.multitexture and type == buf_mtex and gl_buf.texture[1] != lighttex) or
		((type == buf_singletex or type == buf_alias) and gl_buf.flags != flags) or
		(type == buf_alpha and gl_buf.alpha != alpha) ):

		R_ApplyGLBuffer()

		gl_buf.type = type
		gl_buf.texture[0] = colortex
		gl_buf.texture[1] = lighttex
		gl_buf.flags = flags
		gl_buf.alpha = alpha


"""
 * Stores a 2D drawing in the buffer.
 * ul = up-left corner, dr = down-right corner
 * v = vertex, t = texture, x/y = coordinates
"""
def R_Buffer2DQuad(ul_vx, ul_vy, dr_vx, dr_vy, ul_tx, ul_ty, dr_tx, dr_ty): #GLfloat *8

	global vtx_ptr, idx_ptr

	# static const GLushort idx_max = MAX_INDICES - 7;
	# static const GLushort vtx_max = MAX_VERTICES - 5;
	idx_max = MAX_INDICES - 7
	vtx_max = MAX_VERTICES - 5

	if idx_ptr > idx_max or vtx_ptr > vtx_max:
		R_ApplyGLBuffer()

	# "Quad" = 2-triangle GL_TRIANGLE_FAN
	gl_buf.idx[idx_ptr]   = vtx_ptr
	gl_buf.idx[idx_ptr+1] = vtx_ptr+1
	gl_buf.idx[idx_ptr+2] = vtx_ptr+2
	gl_buf.idx[idx_ptr+3] = vtx_ptr
	gl_buf.idx[idx_ptr+4] = vtx_ptr+2
	gl_buf.idx[idx_ptr+5] = vtx_ptr+3
	idx_ptr += 6

	# up left corner coords
	gl_buf.vtx[gl_buf.vt]   = ul_vx
	gl_buf.vtx[gl_buf.vt+1] = ul_vy
	# up right
	gl_buf.vtx[gl_buf.vt+2] = dr_vx
	gl_buf.vtx[gl_buf.vt+3] = ul_vy
	# down right
	gl_buf.vtx[gl_buf.vt+4] = dr_vx
	gl_buf.vtx[gl_buf.vt+5] = dr_vy
	# and finally, down left
	gl_buf.vtx[gl_buf.vt+6] = ul_vx
	gl_buf.vtx[gl_buf.vt+7] = dr_vy

	gl_buf.tex[0][gl_buf.tx]   = ul_tx
	gl_buf.tex[0][gl_buf.tx+1] = ul_ty
	gl_buf.tex[0][gl_buf.tx+2] = dr_tx
	gl_buf.tex[0][gl_buf.tx+3] = ul_ty
	gl_buf.tex[0][gl_buf.tx+4] = dr_tx
	gl_buf.tex[0][gl_buf.tx+5] = dr_ty
	gl_buf.tex[0][gl_buf.tx+6] = ul_tx
	gl_buf.tex[0][gl_buf.tx+7] = dr_ty

	vtx_ptr += 4
	gl_buf.vt += 8
	gl_buf.tx += 8


"""
 * Set up indices with the proper shape for the next buffered vertices.
 * After calling this, GLBUFFER_VERTEX() must be called 'vertices_num' times.
"""
def R_SetBufferIndices(primitive, vertices_num): #GLenum, GLuint

	global vtx_ptr, idx_ptr

	# int i;

	if ( vtx_ptr + vertices_num >= MAX_VERTICES or
		idx_ptr + ( (vertices_num - 2) * 3 ) >= MAX_INDICES ):

		R_ApplyGLBuffer()

	if primitive == GL.GL_TRIANGLE_FAN:
		for i in range(vertices_num-2):
			gl_buf.idx[idx_ptr]   = vtx_ptr
			gl_buf.idx[idx_ptr+1] = vtx_ptr+i+1
			gl_buf.idx[idx_ptr+2] = vtx_ptr+i+2
			idx_ptr += 3
	elif primitive == GL.GL_TRIANGLE_STRIP:
		for i in range(vertices_num-2):
			if i % 2 == 0:
				gl_buf.idx[idx_ptr]   = vtx_ptr+i
				gl_buf.idx[idx_ptr+1] = vtx_ptr+i+1
				gl_buf.idx[idx_ptr+2] = vtx_ptr+i+2
			else:
				# backwards order
				gl_buf.idx[idx_ptr]   = vtx_ptr+i+2
				gl_buf.idx[idx_ptr+1] = vtx_ptr+i+1
				gl_buf.idx[idx_ptr+2] = vtx_ptr+i
			idx_ptr += 3
	else:
		from common import clientserver
		clientserver.Com_DPrintf("{}: no such primitive {}\n".format(__name__, primitive))
		return

	# GLBUFFER_VERTEX() must be called as many times as vertices_num
	vtx_ptr += vertices_num
