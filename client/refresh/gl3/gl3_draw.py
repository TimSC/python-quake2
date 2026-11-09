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
 * gl3_draw.c - 2D rendering for the OpenGL3 refresher (HUD, menus, console)
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from OpenGL import GL
from client.refresh.gl1 import gl1_draw, gl1_image
from client.refresh import ref_shared
from common.header import shared
from client.refresh.gl3 import gl3_main
from client.refresh.gl3.header import local
from client.refresh.gl3.header import hmm
from client.refresh.gl3 import gl3_shaders

# the 2D VAO (position + texcoord)
_2d_vao = [0] #GLuint
_2d_vbo = [0] #GLuint
_2d_init = [False]


def RDraw_2DSetup (): #void

	"""
	Q2PORT: set up the 2D VAO once (position[2] + texCoord[2]).
	"""
	if _2d_init[0]:
		return
	_2d_vao[0] = GL.glGenVertexArrays (1)
	GL.glBindVertexArray (_2d_vao[0])
	_2d_vbo[0] = GL.glGenBuffers (1)
	GL.glBindBuffer (GL.GL_ARRAY_BUFFER, _2d_vbo[0])
	stride = 4 * 4
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_POSITION, 2, GL.GL_FLOAT, False, stride, 0)
	GL.glEnableVertexAttribArray (local.GL3_ATTRIB_TEXCOORD)
	GL.glVertexAttribPointer (local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, False, stride, 8)
	GL.glBindVertexArray (0)
	_2d_init[0] = True


def RDraw_2DStart (): #void

	"""
	Q2PORT: begin the 2D pass — set the 2D orthographic projection, viewport, blend.
	The C sets this once in GL3_BeginFrame (GL3_SetGL2D); here the console draw can
	happen before r_refdef is set, so use the window size (vid) like the C does.
	"""
	RDraw_2DSetup ()

	w = float (gl3_main.vid.width)
	h = float (gl3_main.vid.height)
	gl3_main.gl3state.uni2DData [local.UNI2D_TRANS:local.UNI2D_TRANS + 16] = \
		hmm.HMM_Orthographic (0.0, w, -h, 0.0, -1.0, 1.0).flatten (order = "F")
	gl3_shaders.GL3_UpdateUBO2D ()

	GL.glViewport (0, 0, int (w), int (h))
	GL.glEnable (GL.GL_BLEND)
	GL.glBlendFunc (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
	GL.glDepthMask (GL.GL_FALSE)
	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glEnable (GL.GL_SCISSOR_TEST)
	GL.glScissor (0, 0, int (w), int (h))


def RDraw_StretchPic (x, y, w, h, pic): #int, int, int, int, char *

	gl = RDraw_FindPic (pic)
	if gl is None:
		gl3_main.ri.Con_Printf (shared.PRINT_ALL, "Can't find pic: {}\n".format (pic))
		return

	Scrap_Update ()

	gl3_image_RI_Bind (gl.texnum)
	_tex_quad (gl.texnum, x, y, w, h, gl.sl, gl.tl, gl.sh, gl.th, gl3_main.gl3state.si2D)


def RDraw_PicScaled (x, y, pic, factor): #int, int, char *, float

	RDraw_PicScaledCol (x, y, pic, factor, None)


def RDraw_PicScaledCol (x, y, pic, factor, color): #int, int, char *, char *, float, const float[3]

	gl = RDraw_FindPic (pic)
	if gl is None:
		gl3_main.ri.Con_Printf (shared.PRINT_ALL, "Can't find pic: {}\n".format (pic))
		return

	Scrap_Update ()

	w = int (gl.width * factor)
	h = int (gl.height * factor)

	if color is not None:
		# tinted path
		shader = gl3_main.gl3state.si2Dtinted
		gl3_main.gl3state.uniCommonData [4:7] = [color[0], color[1], color[2]]
		gl3_main.gl3state.uniCommonData [7] = 1.0
		gl3_shaders.GL3_UpdateUBOCommon ()
	else:
		shader = gl3_main.gl3state.si2D

	gl3_image_RI_Bind (gl.texnum)
	_tex_quad (gl.texnum, x, y, w, h, gl.sl, gl.tl, gl.sh, gl.th, shader)


def _tex_quad (texnum, x, y, w, h, u0, v0, u1, v1, shader): #GLuint, int, int, int, int, float, float, float, float, gl3ShaderInfo_t

	RDraw_2DStart ()

	local.GL3_UseProgram (shader.shaderProgram)
	local.GL3_BindVAO (_2d_vao[0])
	local.GL3_BindVBO (_2d_vbo[0])

	# 6 verts (two triangles)
	verts = np.array ([
		x, y, u0, v0,
		x + w, y, u1, v0,
		x + w, y + h, u1, v1,
		x, y, u0, v0,
		x + w, y + h, u1, v1,
		x, y + h, u0, v1,
	], dtype = np.float32)
	GL.glBufferData (GL.GL_ARRAY_BUFFER, verts.nbytes, verts, GL.GL_DYNAMIC_DRAW)

	local.GL3_SelectTMU (GL.GL_TEXTURE0)
	GL.glBindTexture (GL.GL_TEXTURE_2D, texnum)
	gl3_main.gl3state.currenttexture = texnum

	local.gl3_num2Ddraws += 1
	GL.glDrawArrays (GL.GL_TRIANGLES, 0, 6)


def RDraw_CharScaled (x, y, num, scale): #int, int, int, float

	"""
	Q2PORT: draw a console char (same glyph UV math as gl1_draw.RDraw_CharScaled,
	drawn through the 2D textured quad).
	"""
	num &= 255

	if (num & 127) == 32:
		return # space

	if y <= -8:
		return # totally off screen

	row = num >> 4
	col = num & 15

	frow = row * 0.0625
	fcol = col * 0.0625
	size = 0.0625

	scaledSize = 8 * scale

	# map the char UV through the scrap span (see gl1_draw Draw_Char)
	draw_chars = gl1_draw.draw_chars
	if draw_chars is None:
		return

	Scrap_Update ()

	fu  = draw_chars.sl  + fcol        * (draw_chars.sh - draw_chars.sl)
	fu2 = draw_chars.sl  + (fcol+size) * (draw_chars.sh - draw_chars.sl)
	fv  = draw_chars.tl  + frow        * (draw_chars.th - draw_chars.tl)
	fv2 = draw_chars.tl  + (frow+size) * (draw_chars.th - draw_chars.tl)

	gl3_image_RI_Bind (draw_chars.texnum)
	_tex_quad (draw_chars.texnum, x, y, scaledSize, scaledSize, fu, fv, fu2, fv2, gl3_main.gl3state.si2D)


def RDraw_Fill (x, y, w, h, c): #int, int, int, int, int

	"""
	Q2PORT: fill a rectangle with a palette color (2D color quad via si2Dcolor).
	"""
	RDraw_2DStart ()

	local.GL3_UseProgram (gl3_main.gl3state.si2Dcolor.shaderProgram)
	local.GL3_BindVAO (_2d_vao[0])
	local.GL3_BindVBO (_2d_vbo[0])

	r, g, b = _palette_rgb (c)
	gl3_main.gl3state.uniCommonData [4:7] = [r, g, b]
	gl3_main.gl3state.uniCommonData [7] = 1.0
	gl3_shaders.GL3_UpdateUBOCommon ()

	verts = np.array ([
		x, y, 0, 0,
		x + w, y, 0, 0,
		x + w, y + h, 0, 0,
		x, y, 0, 0,
		x + w, y + h, 0, 0,
		x, y + h, 0, 0,
	], dtype = np.float32)
	GL.glBufferData (GL.GL_ARRAY_BUFFER, verts.nbytes, verts, GL.GL_DYNAMIC_DRAW)

	local.gl3_num2Ddraws += 1
	GL.glDrawArrays (GL.GL_TRIANGLES, 0, 6)


def _palette_rgb (c): #int (returns float, float, float)

	# Q2PORT: convert a 8-bit palette index to rgb 0..1 (approx)
	pi = c & 255
	return (pi >> 5 & 7) / 7.0, (pi >> 2 & 7) / 7.0, (pi & 3) / 3.0


def RDraw_FadeScreen (): #void

	r, g, b = 0.0, 0.0, 0.0
	w = gl3_main.r_refdef.width
	h = gl3_main.r_refdef.height
	# use the same color-quad path
	RDraw_2DStart ()
	local.GL3_UseProgram (gl3_main.gl3state.si2Dcolor.shaderProgram)
	local.GL3_BindVAO (_2d_vao[0])
	local.GL3_BindVBO (_2d_vbo[0])
	gl3_main.gl3state.uniCommonData [4:7] = [0, 0, 0]
	gl3_main.gl3state.uniCommonData [7] = 0.3
	gl3_shaders.GL3_UpdateUBOCommon ()
	verts = np.array ([
		0, 0, 0, 0, w, 0, 0, 0, w, h, 0, 0,
		0, 0, 0, 0, w, h, 0, 0, 0, h, 0, 0,
	], dtype = np.float32)
	GL.glBufferData (GL.GL_ARRAY_BUFFER, verts.nbytes, verts, GL.GL_DYNAMIC_DRAW)
	GL.glDrawArrays (GL.GL_TRIANGLES, 0, 6)


def RDraw_FindPic (name): #char * (returns gl3image_t *)

	return gl1_draw.RDraw_FindPic (name)


def RDraw_GetPicSize (name): #char * (returns int, int)

	return gl1_draw.RDraw_GetPicSize (name)


def RDraw_TileClear (x, y, w, h, pic): #int, int, int, int, char *

	# Q2PORT: reuse the stretch-pic path for the tile
	RDraw_StretchPic (x, y, w, h, pic)


def RDraw_StretchRaw (x, y, w, h, cols, rows, data): #int, int, int, int, int, int, byte *

	# Q2PORT: placeholder for raw (video) textures
	pass


def gl3_image_RI_Bind (texnum): #GLuint

	from client.refresh.gl3 import gl3_image
	gl3_image.RI_Bind (texnum)


def Scrap_Update (): #void

	gl1_draw.Scrap_Update ()
