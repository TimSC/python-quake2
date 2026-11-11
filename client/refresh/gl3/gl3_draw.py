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
 * Drawing of all images that are not textures
 *
 * =======================================================================
"""

from __future__ import annotations

import ctypes

import numpy as np
import OpenGL.GL as GL

from common import clientserver
from common.header import shared
from client.refresh.files import stb as files_stb
from client.refresh.gl3.header import local
from client.refresh.gl3 import gl3_main, gl3_image, gl3_shaders, gl3_sdl

#include "header/local.h"

#include "header/DG_dynarr.h"

d_8to24table = [(0, 0, 0, 0)] * 256 #unsigned [256], Q2PORT: (r, g, b, a) per entry, as pcx.GetPCXPalette fills it

draw_chars = None #gl3image_t *

vbo2D, ebo2D, vao2D, vao2Dcolor = 0, 0, 0, 0 #static GLuint, vao2D is for textured rendering, vao2Dcolor for color-only

gl3_num3Ddraws, gl3_num2Ddraws, gl3_numBufferVtxData, gl3_numBufferUniforms = 0, 0, 0, 0 #int

"""
typedef struct gl3_drawVert2D_s {
	float x, y, s, t;
} gl3_drawVert2D;
"""

# DA_TYPEDEF(gl3_drawVert2D, Vtx2DArray_t);
# DA_TYPEDEF(GLushort, UShortArray_t);
# dynamic arrays to batch all consecutive 2D draws with same texture to reduce drawcalls
# Q2PORT: python lists, 4 floats per gl3_drawVert2D in vtxBuf
vtxBuf = [] #static Vtx2DArray_t
idxBuf = [] #static UShortArray_t
lastBatchTexture = 0 #static GLuint

UINT16_MAX = 65535

def GL3_Draw_InitLocal(): #void

	global draw_chars, vbo2D, ebo2D, vao2D, vao2Dcolor

	# load console characters
	draw_chars = files_stb.R_FindPic("conchars", gl3_image.GL3_FindImage)
	if draw_chars is None:

		clientserver.Com_Error(shared.ERR_FATAL, "{}: Couldn't load pics/conchars.pcx".format(
			"GL3_Draw_InitLocal"))

	# set up attribute layout for 2D textured rendering
	vao2D = GL.glGenVertexArrays(1)
	GL.glBindVertexArray(vao2D)

	vbo2D = GL.glGenBuffers(1)
	local.GL3_BindVBO(vbo2D)
	ebo2D = GL.glGenBuffers(1)

	local.GL3_UseProgram(gl3_main.gl3state.si2D.shaderProgram)

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_POSITION)
	# Note: the glVertexAttribPointer() configuration is stored in the VAO, not the shader or sth
	#       (that's why I use one VAO per 2D shader)
	# Q2PORT: the offsets must be ctypes.c_void_p, PyOpenGL turns a plain int into a pointer to a temporary
	GL.glVertexAttribPointer(local.GL3_ATTRIB_POSITION, 2, GL.GL_FLOAT, GL.GL_FALSE, 4*4, ctypes.c_void_p(0))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_TEXCOORD)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, GL.GL_FALSE, 4*4, ctypes.c_void_p(2*4))

	# set up attribute layout for 2D flat color rendering

	vao2Dcolor = GL.glGenVertexArrays(1)
	GL.glBindVertexArray(vao2Dcolor)

	local.GL3_BindVBO(vbo2D) # yes, both VAOs share the same VBO

	local.GL3_UseProgram(gl3_main.gl3state.si2Dcolor.shaderProgram)

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_POSITION, 2, GL.GL_FLOAT, GL.GL_FALSE, 2*4, ctypes.c_void_p(0))

	local.GL3_BindVAO(0)

def GL3_Draw_ShutdownLocal(): #void

	global vbo2D, ebo2D, vao2D, vao2Dcolor

	GL.glDeleteBuffers(1, [ebo2D])
	ebo2D = 0
	GL.glDeleteBuffers(1, [vbo2D])
	vbo2D = 0
	GL.glDeleteVertexArrays(1, [vao2D])
	vao2D = 0
	GL.glDeleteVertexArrays(1, [vao2Dcolor])
	vao2Dcolor = 0

	vtxBuf.clear() # da_free(vtxBuf)
	idxBuf.clear() # da_free(idxBuf)

def GL3_DrawCurrent2Dbatch(): #void

	global lastBatchTexture, gl3_numBufferVtxData, gl3_num2Ddraws

	numVtx = len(vtxBuf) // 4 # da_count(vtxBuf)
	if numVtx == 0:
		return

	if gl3_image.gl3_scrap_dirty:
		gl3_image.GL3_Scrap_Upload()

	local.GL3_UseProgram(gl3_main.gl3state.si2D.shaderProgram)
	gl3_image.GL3_Bind(lastBatchTexture)

	local.GL3_BindVAO(vao2D)

	# Note: while vao2D "remembers" its vbo for drawing, binding the vao does *not*
	#       implicitly bind the vbo, so I need to explicitly bind it before glBufferData()
	local.GL3_BindVBO(vbo2D)
	vtx = np.array(vtxBuf, dtype=np.float32)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vtx.nbytes, vtx, GL.GL_STREAM_DRAW)

	local.GL3_BindEBO(ebo2D)
	idx = np.array(idxBuf, dtype=np.uint16)
	GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, idx.nbytes, idx, GL.GL_STREAM_DRAW)
	GL.glDrawElements(GL.GL_TRIANGLES, len(idxBuf), GL.GL_UNSIGNED_SHORT, ctypes.c_void_p(0))

	gl3_numBufferVtxData += 1
	gl3_num2Ddraws += 1

	lastBatchTexture = 0
	vtxBuf.clear() # da_clear(vtxBuf)
	idxBuf.clear() # da_clear(idxBuf)

def drawTexturedRectangle(texNum, x, y, w, h, sl, tl, sh, th): #GLuint, float, float, float, float, float, float, float, float

	global lastBatchTexture

	"""
	 *  x,y+h      x+w,y+h
	 * sl,th--------sh,th
	 *  |             |
	 *  |             |
	 *  |             |
	 * sl,tl--------sh,tl
	 *  x,y        x+w,y
	"""

	if (lastBatchTexture != 0 and texNum != lastBatchTexture) or len(vtxBuf) // 4 + 4 > UINT16_MAX:
		GL3_DrawCurrent2Dbatch()

	lastBatchTexture = texNum

	firstIdx = len(vtxBuf) // 4 # GLushort, da_count(vtxBuf)

	# gl3_drawVert2D* addVtx = da_addn_uninit(vtxBuf, 4);
	#               X,   Y,   S,  T
	vtxBuf.extend((x,   y+h, sl, th,
	               x,   y,   sl, tl,
	               x+w, y+h, sh, th,
	               x+w, y,   sh, tl))

	# GLushort* addIdx = da_addn_uninit(idxBuf, 6);
	idxBuf.extend((firstIdx,   # first triangle of rectangle
	               firstIdx+1,
	               firstIdx+2,
	               firstIdx+1, # second triangle
	               firstIdx+3,
	               firstIdx+2))

"""
 bind the texture before calling this
"""
def drawTexturedRectangleNow(x, y, w, h, sl, tl, sh, th): #float, float, float, float, float, float, float, float

	global gl3_numBufferVtxData, gl3_num2Ddraws

	"""
	 *  x,y+h      x+w,y+h
	 * sl,th--------sh,th
	 *  |             |
	 *  |             |
	 *  |             |
	 * sl,tl--------sh,tl
	 *  x,y        x+w,y
	"""

	# in case some batched 2D draws are outstanding, draw them now
	# to preserve draw order
	GL3_DrawCurrent2Dbatch()

	if gl3_image.gl3_scrap_dirty:
		gl3_image.GL3_Scrap_Upload()

	vBuf = np.array([ #gl3_drawVert2D [4]
	#	  X,   Y,   S,  T
		  x,   y+h, sl, th,
		  x,   y,   sl, tl,
		  x+w, y+h, sh, th,
		  x+w, y,   sh, tl
	], dtype=np.float32)

	local.GL3_BindVAO(vao2D)

	# Note: while vao2D "remembers" its vbo for drawing, binding the vao does *not*
	#       implicitly bind the vbo, so I need to explicitly bind it before glBufferData()
	local.GL3_BindVBO(vbo2D)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vBuf.nbytes, vBuf, GL.GL_STREAM_DRAW)
	GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
	gl3_numBufferVtxData += 1
	gl3_num2Ddraws += 1

	#glMultiDrawArrays(mode, first, count, drawcount) ??

"""
 * Draws one 8*8 graphics character with 0 being transparent.
 * It can be clipped to the top of the screen to allow the console to be
 * smoothly scrolled off.
"""
def GL3_Draw_CharScaled(x, y, num, scale): #int, int, int, float

	#int row, col;
	#float frow, fcol, size, scaledSize;
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

	scaledSize = 8*scale

	drawTexturedRectangle( draw_chars.texnum, x, y, scaledSize, scaledSize,
	                       draw_chars.sl + fcol * (draw_chars.sh - draw_chars.sl),
	                       draw_chars.tl + frow * (draw_chars.th - draw_chars.tl),
	                       draw_chars.sl + (fcol + size) * (draw_chars.sh - draw_chars.sl),
	                       draw_chars.tl + (frow + size) * (draw_chars.th - draw_chars.tl) )

"""
 DG: copy of DrawStringScaled(), so we can draw some stats right here in the render DLL
"""
def GL3_DrawStringScaled(x, y, s, factor): #int, int, const char *, float

	for ch in s:

		GL3_Draw_CharScaled(x, y, ord(ch) ^ 0x80, factor)
		x += 8*factor

def GL3_Draw_FindPic(name): #const char * (returns gl3image_t *)

	return files_stb.R_FindPic(name, gl3_image.GL3_FindImage)

def GL3_Draw_GetPicSize(pic): #int *, int *, const char * (returns w, h)

	#gl3image_t *gl;

	gl = files_stb.R_FindPic(pic, gl3_image.GL3_FindImage)

	if gl is None:

		return -1, -1

	return gl.width, gl.height

def GL3_Draw_StretchPic(x, y, w, h, pic): #int, int, int, int, const char *

	gl = files_stb.R_FindPic(pic, gl3_image.GL3_FindImage)

	if gl is None:

		clientserver.Com_Printf("Can't find pic: {}\n".format(pic))
		return

	drawTexturedRectangle(gl.texnum, x, y, w, h, gl.sl, gl.tl, gl.sh, gl.th)

def GL3_Draw_PicScaled(x, y, pic, factor): #int, int, const char *, float

	gl = files_stb.R_FindPic(pic, gl3_image.GL3_FindImage)
	if gl is None:

		clientserver.Com_Printf("Can't find pic: {}\n".format(pic))
		return

	drawTexturedRectangle(gl.texnum, x, y, gl.width*factor, gl.height*factor, gl.sl, gl.tl, gl.sh, gl.th)

def GL3_Draw_PicScaledCol(x, y, pic, factor, color): #int, int, const char *, float, const float[3]

	gl = files_stb.R_FindPic(pic, gl3_image.GL3_FindImage)
	if gl is None:

		clientserver.Com_Printf("Can't find pic: {}\n".format(pic))
		return

	if gl3_image.gl3_scrap_dirty:
		gl3_image.GL3_Scrap_Upload()

	gl3_main.gl3state.uniCommonData[local.UNICOMMON_COLOR:local.UNICOMMON_COLOR + 4] = (color[0], color[1], color[2], 1.0)
	gl3_shaders.GL3_UpdateUBOCommon()

	local.GL3_UseProgram(gl3_main.gl3state.si2Dtinted.shaderProgram)
	gl3_image.GL3_Bind(gl.texnum)

	# NOTE: this function (and this shader) are only used for the crosshair
	#       so use the simple immediate (unbatched) draw function
	drawTexturedRectangleNow(x, y, gl.width*factor, gl.height*factor, gl.sl, gl.tl, gl.sh, gl.th)

	gl3_main.gl3state.uniCommonData[local.UNICOMMON_COLOR:local.UNICOMMON_COLOR + 4] = (1, 1, 1, 1)
	gl3_shaders.GL3_UpdateUBOCommon()

"""
 * This repeats a 64*64 tile graphic to fill
 * the screen around a sized down
 * refresh window.
"""
def GL3_Draw_TileClear(x, y, w, h, pic): #int, int, int, int, const char *

	#const gl3image_t *image;
	#int x2;

	if w <= 0 or h <= 0:

		return

	image = files_stb.R_FindPic(pic, gl3_image.GL3_FindImage)
	if image is None:

		clientserver.Com_Printf("{}(): Can't find pic: {}\n".format("GL3_Draw_TileClear", pic))
		return

	if gl3_image.gl3_scrap_dirty:

		# Upload any pending scrap textures before rendering 2D elements
		gl3_image.GL3_Scrap_Upload()

	for x2 in range(0, w, image.width):

		#int tile_w, y2;
		#float tile_sh;

		tile_w = (w - x2) if (x2 + image.width > w) else image.width
		tile_sh = (image.sl +
			(image.sh - image.sl) * (float(tile_w) / image.width))

		for y2 in range(0, h, image.height):

			#float tile_th;
			#int tile_h;

			tile_h = (h - y2) if (y2 + image.height > h) else image.height
			tile_th = (image.tl +
				(image.th - image.tl) * (float(tile_h) / image.height))

			drawTexturedRectangle(image.texnum, x + x2, y + y2,
				tile_w,
				tile_h,
				image.sl, image.tl,
				tile_sh, tile_th
			)

def GL3_DrawFrameBufferObject(x, y, w, h, fboTexture, v_blend): #int, int, int, int, GLuint, const float[4]

	underwater = (gl3_main.r_newrefdef.rdflags & shared.RDF_UNDERWATER) != 0
	shader = gl3_main.gl3state.si2DpostProcessWater if underwater \
	                                     else gl3_main.gl3state.si2DpostProcess
	local.GL3_UseProgram(shader.shaderProgram)
	gl3_image.GL3_Bind(fboTexture)

	if underwater and shader.uniLmScalesOrTime != -1:

		GL.glUniform1f(shader.uniLmScalesOrTime, gl3_main.r_newrefdef.time)

	if shader.uniVblend != -1:

		GL.glUniform4fv(shader.uniVblend, 1, np.array(v_blend, dtype=np.float32))

	drawTexturedRectangleNow(x, y, w, h, 0, 1, 1, 0)

"""
 * Fills a box of pixels with a single color
"""
def GL3_Draw_Fill(x, y, w, h, c): #int, int, int, int, int

	global gl3_numBufferVtxData, gl3_num2Ddraws

	"""
	union
	{
		unsigned c;
		byte v[4];
	} color;
	"""

	if c < 0 or c > 255: # (unsigned)c > 255

		clientserver.Com_Error(shared.ERR_FATAL, "Draw_Fill: bad color")

	color = d_8to24table[c]

	# in case some batched 2D draws are outstanding, draw them now
	# to preserve draw order
	GL3_DrawCurrent2Dbatch()

	vBuf = np.array([ #GLfloat [8]
	#	X,   Y
		x,   y+h,
		x,   y,
		x+w, y+h,
		x+w, y
	], dtype=np.float32)

	for i in range(3):

		gl3_main.gl3state.uniCommonData[local.UNICOMMON_COLOR + i] = color[i] * (1.0/255.0)

	gl3_main.gl3state.uniCommonData[local.UNICOMMON_COLOR + 3] = 1.0

	gl3_shaders.GL3_UpdateUBOCommon()

	local.GL3_UseProgram(gl3_main.gl3state.si2Dcolor.shaderProgram)
	local.GL3_BindVAO(vao2Dcolor)

	local.GL3_BindVBO(vbo2D)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vBuf.nbytes, vBuf, GL.GL_STREAM_DRAW)

	GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

	gl3_numBufferVtxData += 1
	gl3_num2Ddraws += 1

"""
 in GL1 this is called R_Flash() (which just calls R_PolyBlend())
 now implemented in 2D mode and called after SetGL2D() because
 it's pretty similar to GL3_Draw_FadeScreen()
"""
def GL3_Draw_Flash(color, x, y, w, h): #const float[4], float, float, float, float

	global gl3_numBufferVtxData, gl3_num2Ddraws

	if gl3_main.gl_polyblend.value == 0:

		return

	# in case some batched 2D draws are outstanding, draw them now
	# to preserve draw order
	GL3_DrawCurrent2Dbatch()

	vBuf = np.array([ #GLfloat [8]
	#	X,   Y
		x,   y+h,
		x,   y,
		x+w, y+h,
		x+w, y
	], dtype=np.float32)

	GL.glEnable(GL.GL_BLEND)

	for i in range(4):
		gl3_main.gl3state.uniCommonData[local.UNICOMMON_COLOR + i] = color[i]

	gl3_shaders.GL3_UpdateUBOCommon()

	local.GL3_UseProgram(gl3_main.gl3state.si2Dcolor.shaderProgram)

	local.GL3_BindVAO(vao2Dcolor)

	local.GL3_BindVBO(vbo2D)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vBuf.nbytes, vBuf, GL.GL_STREAM_DRAW)

	GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

	gl3_numBufferVtxData += 1
	gl3_num2Ddraws += 1

	GL.glDisable(GL.GL_BLEND)

def GL3_Draw_FadeScreen(): #void

	color = (0, 0, 0, 0.6)
	GL3_Draw_Flash(color, 0, 0, gl3_main.vid.width, gl3_main.vid.height)

def GL3_Draw_StretchRaw(x, y, w, h, cols, rows, data, bits=8): #int, int, int, int, int, int, const byte *, int

	# Q2PORT: the port's refexport_t has no bits argument (the client only
	# sends 8 bit frames), hence the default

	#int i, j;

	gl3_image.GL3_Bind(0)

	#unsigned image32[320*240]; /* was 256 * 256, but we want a bit more space */

	if bits == 32:

		img = np.frombuffer(bytes(data[:cols * rows * 4]), dtype=np.uint8)

	else:

		# Q2PORT: the C's loop img[i] = gl3_rawpalette[data[i]] is a numpy
		# table lookup; the result is passed as bytes (given the uint32 array,
		# PyOpenGL would convert each value to one byte)
		img = gl3_main.gl3_rawpalette[np.frombuffer(bytes(data[:cols * rows]), dtype=np.uint8)].view(np.uint8)

	local.GL3_UseProgram(gl3_main.gl3state.si2D.shaderProgram)

	#GLuint glTex;
	glTex = GL.glGenTextures(1)
	local.GL3_SelectTMU(GL.GL_TEXTURE0)
	GL.glBindTexture(GL.GL_TEXTURE_2D, glTex)

	GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, local.gl3_tex_solid_format,
	             cols, rows, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img)

	# Note: gl_filter_min could be GL_*_MIPMAP_* so we can't use it for min filter here (=> no mipmaps)
	#       but gl_filter_max (either GL_LINEAR or GL_NEAREST) should do the trick.
	filter = gl3_image.gl_filter_max if (gl3_main.r_videos_unfiltered.value == 0) else GL.GL_NEAREST
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, filter)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, filter)

	# NOTE: this is only used for videos and only called once per frame (or not at all)
	drawTexturedRectangleNow(x, y, w, h, 0.0, 0.0, 1.0, 1.0)

	GL.glDeleteTextures(1, [glTex])

	gl3_image.GL3_Bind(0)

"""
 * Called at the end of the frame, after 2D (UI) rendering is done.
 * Does some internal housekeeping, then swaps the buffers
 * and shows the next frame.
"""
def GL3_EndFrame(): #void

	global gl3_num3Ddraws, gl3_num2Ddraws, gl3_numBufferVtxData, gl3_numBufferUniforms

	GL3_DrawCurrent2Dbatch()

	# by saving those values into a variable and setting them to 0 afterwards,
	# gl3_show_draw_stats can include its own drawcalls (from previous frame)
	num3D = gl3_num3Ddraws
	num2D = gl3_num2Ddraws
	numBufVtx = gl3_numBufferVtxData
	numBufUni = gl3_numBufferUniforms
	gl3_num3Ddraws = 0
	gl3_num2Ddraws = 0
	gl3_numBufferVtxData = 0
	gl3_numBufferUniforms = 0

	if gl3_main.gl3_show_draw_stats.value:

		factor = 2.0 # TODO: like SCR_GetConsoleScale()
		stbuf = "3D drawcalls: {} - 2D drawcalls: {} - buffer vtx data: {} - buffer uniforms: {}".format(
		         num3D, num2D, numBufVtx, numBufUni)[:127]

		GL3_DrawStringScaled(10, 5, stbuf, factor)
		GL3_DrawCurrent2Dbatch()

	# Q2PORT: the C's YQ2_GL3_GLES glInvalidateFramebuffer block is not the desktop port

	gl3_sdl.GL3_SwapWindow()
