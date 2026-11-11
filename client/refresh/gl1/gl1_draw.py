"""
 * Copyright (C) 1997-2001 Id Software, Inc.
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
 * Drawing of all images that are not textures
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from client.refresh.gl1 import gl1_main, gl1_image, gl1_scrap, gl1_buffer
from client.refresh.files import stb as files_stb
from common import clientserver
from common.header import shared

"""
#include "header/local.h"
"""

draw_chars = None #image_t *

#extern unsigned r_rawpalette[256];

def Draw_InitLocal(): #void

	global draw_chars

	# load console characters
	draw_chars = files_stb.R_FindPic("conchars", gl1_image.R_FindImage)
	if not draw_chars:

		clientserver.Com_Error(shared.ERR_FATAL, "{}: Couldn't load pics/conchars.pcx".format(
			"Draw_InitLocal"))

def Scrap_Update(): #void (static)

	#qboolean default2Dnolerp;
	#int texnum;

	default2Dnolerp = gl1_main.r_2D_unfiltered.value != 0.0

	for texnum in range(gl1_scrap.MAX_SCRAPS):

		#unsigned *scrap_texels;

		scrap_texels = gl1_scrap.Scrap_Upload(texnum)
		if scrap_texels is not None:

			#size_t scrap_size;
			#unsigned *tmp;

			gl1_image.R_Bind(gl1_image.TEXNUM_SCRAPS + texnum)

			scrap_size = gl1_scrap.SCRAP_WIDTH * gl1_scrap.SCRAP_HEIGHT * 4 # sizeof(unsigned)
			tmp = bytearray(scrap_texels[:scrap_size]) # malloc + memcpy(tmp, scrap_texels, scrap_size);

			gl1_image.R_Upload32(tmp, gl1_scrap.SCRAP_WIDTH, gl1_scrap.SCRAP_HEIGHT, False)
			#free(tmp);

			if default2Dnolerp or (texnum < gl1_scrap.MAX_SCRAPS_NOLERP):

				# 2D textures shouldn't be filtered by default (r_2D_unfiltered),
				# so the scrap shouldn't be filtered
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

			else: # 2D textures should be filtered by default => filter the scrap

				# we can't use gl_filter_min which might be GL_*_MIPMAP_*
				# also, there's no anisotropic filtering for textures w/o mipmaps
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl1_image.gl_filter_max)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl1_image.gl_filter_max)

"""
 * Draws one 8*8 graphics character with 0 being transparent.
 * It can be clipped to the top of the screen to allow the console to be
 * smoothly scrolled off.
"""
def RDraw_CharScaled(x, y, num, scale): #int, int, int, float

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

	scaledSize = 8 * scale

	if draw_chars.scrap:

		Scrap_Update()

	gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_2d, draw_chars.texnum, 0, 0, 1)

	gl1_buffer.R_Buffer2DQuad(x, y, x + scaledSize, y + scaledSize,
		draw_chars.sl + fcol * (draw_chars.sh - draw_chars.sl),
		draw_chars.tl + frow * (draw_chars.th - draw_chars.tl),
		draw_chars.sl + (fcol + size) * (draw_chars.sh - draw_chars.sl),
		draw_chars.tl + (frow + size) * (draw_chars.th - draw_chars.tl))

def RDraw_FindPic(name): #const char * (returns image_t *)

	return files_stb.R_FindPic(name, gl1_image.R_FindImage)

def RDraw_GetPicSize(pic): #int *, int *, const char * (Q2PORT: returns w, h)

	#const image_t *gl;

	gl = files_stb.R_FindPic(pic, gl1_image.R_FindImage)

	if not gl:

		return -1, -1 # *w = *h = -1;

	return gl.width, gl.height

def RDraw_StretchPic(x, y, w, h, pic): #int, int, int, int, const char *

	#image_t *gl;

	gl = files_stb.R_FindPic(pic, gl1_image.R_FindImage)

	if not gl:

		clientserver.Com_Printf("{}(): Can't find pic: {}\n".format("RDraw_StretchPic", pic))
		return

	if gl.scrap:

		Scrap_Update()

	gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_2d, gl.texnum, 0, 0, 1)

	gl1_buffer.R_Buffer2DQuad(x, y, x + w, y + h,
		gl.sl, gl.tl, gl.sh, gl.th)

def RDraw_PicScaled(x, y, pic, factor): #int, int, const char *, float

	#image_t *gl;

	gl = files_stb.R_FindPic(pic, gl1_image.R_FindImage)

	if not gl:

		clientserver.Com_Printf("Can't find pic: {}\n".format(pic))
		return

	if gl.scrap:

		Scrap_Update()

	if gl.texnum >= gl1_image.TEXNUM_SCRAPS and gl.texnum < gl1_image.TEXNUM_IMAGES:

		gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_2d, gl.texnum, 0, 0, 1)
		gl1_buffer.R_Buffer2DQuad(x, y, x + gl.width * factor, y + gl.height * factor,
			gl.sl, gl.tl, gl.sh, gl.th)
		return

	if gl.scrap:

		Scrap_Update()

	gl1_buffer.R_ApplyGLBuffer()	# respect drawing order

	gl1_image.R_Bind(gl.texnum)

	vtx = np.array([ #GLfloat[]
		x, y,
		x + gl.width * factor, y,
		x + gl.width * factor, y + gl.height * factor,
		x, y + gl.height * factor
	], dtype=np.float32)

	tex = np.array([ #GLfloat[]
		gl.sl, gl.tl,
		gl.sh, gl.tl,
		gl.sh, gl.th,
		gl.sl, gl.th
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
	GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glVertexPointer( 2, GL.GL_FLOAT, 0, vtx )
	GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
	GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

def RDraw_PicScaledCol(x, y, pic, factor, color): #int, int, const char *, float, const float[3]

	#image_t *gl;

	gl = files_stb.R_FindPic(pic, gl1_image.R_FindImage)

	if not gl:

		clientserver.Com_Printf("Can't find pic: {}\n".format(pic))
		return

	if gl.scrap:

		Scrap_Update()

	gl1_buffer.R_ApplyGLBuffer()

	gl1_image.R_TexEnv(GL.GL_MODULATE)
	GL.glColor4f(color[0], color[1], color[2], 1)

	gl1_image.R_Bind(gl.texnum)

	vtx = np.array([ #GLfloat[]
		x, y,
		x + gl.width * factor, y,
		x + gl.width * factor, y + gl.height * factor,
		x, y + gl.height * factor
	], dtype=np.float32)

	tex = np.array([ #GLfloat[]
		gl.sl, gl.tl,
		gl.sh, gl.tl,
		gl.sh, gl.th,
		gl.sl, gl.th
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
	GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glVertexPointer( 2, GL.GL_FLOAT, 0, vtx )
	GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
	GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glColor4f(1, 1, 1, 1)
	gl1_image.R_TexEnv(GL.GL_REPLACE)

"""
 * This repeats a 64*64 tile graphic to fill
 * the screen around a sized down
 * refresh window.
"""
def RDraw_TileClear(x, y, w, h, pic): #int, int, int, int, const char *

	#const image_t *image;
	#int x2;

	image = files_stb.R_FindPic(pic, gl1_image.R_FindImage)

	if not image:

		clientserver.Com_Printf("{}(): Can't find pic: {}\n".format("RDraw_TileClear", pic))
		return

	if image.scrap:

		Scrap_Update()

	gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_2d, image.texnum, 0, 0, 1)

	for x2 in range(0, w, image.width):

		#int next_x, y2, tile_w;
		#float tile_sh;

		next_x = x + x2 + image.width
		if next_x > x + w:

			next_x = x + w

		tile_w = next_x - (x + x2)

		tile_sh = image.sl + \
			(image.sh - image.sl) * (tile_w / image.width)

		for y2 in range(0, h, image.height):

			#int next_y, tile_h;
			#float tile_th;

			next_y = y + y2 + image.height
			if next_y > y + h:

				next_y = y + h

			tile_h = next_y - (y + y2)
			tile_th = image.tl + \
				(image.th - image.tl) * (tile_h / image.height)

			gl1_buffer.R_Buffer2DQuad(x + x2, y + y2,
				next_x,
				next_y,
				image.sl, image.tl,
				tile_sh, tile_th
			)

"""
 * Fills a box of pixels with a single color
"""
def RDraw_Fill(x, y, w, h, c): #int, int, int, int, int

	"""
	union
	{
		unsigned c;
		byte v[4];
	} color;
	"""

	if c < 0 or c > 255: # (unsigned)c > 255

		clientserver.Com_Error(shared.ERR_FATAL, "{}: bad color".format("RDraw_Fill"))
		return

	GL.glDisable(GL.GL_TEXTURE_2D)

	color = gl1_image.d_8to24table[c] # color.c = d_8to24table[c]; Q2PORT: (r, g, b, a)
	GL.glColor4f(color[0] / 255.0, color[1] / 255.0,
			   color[2] / 255.0, 1)

	vtx = np.array([ #GLfloat[]
		x, y,
		x + w, y,
		x + w, y + h,
		x, y + h
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

	GL.glVertexPointer( 2, GL.GL_FLOAT, 0, vtx )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	GL.glColor4f( 1, 1, 1, 1 )
	GL.glEnable(GL.GL_TEXTURE_2D)

def RDraw_FadeScreen(): #void

	gl1_buffer.R_ApplyGLBuffer()	# draw what needs to be hidden
	GL.glEnable(GL.GL_BLEND)
	GL.glDisable(GL.GL_TEXTURE_2D)
	GL.glColor4f(0, 0, 0, 0.8)

	vtx = np.array([ #GLfloat[]
		0, 0,
		gl1_main.vid.width, 0,
		gl1_main.vid.width, gl1_main.vid.height,
		0, gl1_main.vid.height
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

	GL.glVertexPointer( 2, GL.GL_FLOAT, 0, vtx )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	GL.glColor4f(1, 1, 1, 1)
	GL.glEnable(GL.GL_TEXTURE_2D)
	GL.glDisable(GL.GL_BLEND)

"""
=============
RDraw_StretchRaw
=============
"""
def RDraw_StretchRaw (x, y, w, h, cols, rows, data, bits=8): #int, int, int, int, int, int, const byte *, int

	# Q2PORT: vid.Draw_StretchRaw doesn't pass bits yet (8-bit cinematics only), hence the default

	"""
	GLfloat tex[8];
	float hscale = 1.0f;
	int frac, fracstep;
	int row;
	"""
	tex = np.zeros((8,), dtype=np.float32)
	hscale = 1.0

	gl1_image.R_Bind(0)

	if gl1_main.gl_config.npottextures or rows <= 256 or bits == 32:
	
		# X, X
		tex[0] = 0
		tex[1] = 0

		# X, Y
		tex[2] = 1
		tex[3] = 0

		# Y, X
		tex[4] = 1
		tex[5] = 1

		# Y, Y
		tex[6] = 0
		tex[7] = 1
	
	else:
	
		# Scale params
		hscale = rows / 256.0

		# X, X
		tex[0] = 1.0 / 512.0
		tex[1] = 1.0 / 512.0

		# X, Y
		tex[2] = 511.0 / 512.0
		tex[3] = 1.0 / 512.0

		# Y, X
		tex[4] = 511.0 / 512.0
		tex[5] = rows * hscale / 256 - 1.0 / 512.0

		# Y, Y
		tex[6] = 1.0 / 512.0
		tex[7] = rows * hscale / 256 - 1.0 / 512.0

	vtx = np.array([
			x, y,
			x + w, y,
			x + w, y + h,
			x, y + h
	], dtype=np.float32)

	# Q2PORT: r_rawpalette as an array, for the numpy palette lookups below
	rawpalette = np.array(gl1_main.r_rawpalette, dtype=np.uint32)

	if not gl1_main.gl_config.palettedtexture or bits == 32:
	
		# .. because now if non-power-of-2 textures are supported, we just load
		# the data into a texture in the original format, without skipping any
		# pixels to fit into a 256x256 texture.
		# This causes text in videos (which are 320x240) to not look broken anymore.
		if bits == 32:
		
			GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, gl1_image.gl_tex_solid_format,
					cols, rows, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
					bytes(data))
		
		elif gl1_main.gl_config.npottextures or rows <= 256:
		
			# Q2PORT: the per-pixel palette loop is a numpy lookup
			# img[rowOffset+j] = r_rawpalette[data[rowOffset+j]]
			img = rawpalette[np.frombuffer(bytes(data), dtype=np.uint8, count=cols * rows)]

			GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, gl1_image.gl_tex_solid_format,
								cols, rows, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
								img.view(np.uint8))
		
		else:
		
			#static unsigned int image32[320 * 240];
			image32 = np.zeros((320 * 240,), dtype=np.uint32)
			trows = 256
			src = np.frombuffer(bytes(data), dtype=np.uint8)

			for i in range(trows):
			
				row = int(i * hscale)

				if row > rows:
					break

				source = cols * row # data + cols * row
				dest = i * 256 # &image32[i * 256]
				fracstep = cols * 0x10000 // 256
				frac = fracstep >> 1

				for j in range(256):
				
					image32[dest + j] = rawpalette[src[source + (frac >> 16)]]
					frac += fracstep

			GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, gl1_image.gl_tex_solid_format,
					256, 256, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
					image32.view(np.uint8))
	
	else:
	
		# Q2PORT: gl_config.palettedtexture is never set (GL_EXT_paletted_texture
		# isn't offered by current drivers)
		raise NotImplementedError()
		"""
		static byte image8[256 * 256];
		int trows = 256;
		size_t i;

		for (i = 0; i < trows; i++)
		{
			const byte *source;
			byte *dest;
			size_t j;

			row = (int)(i * hscale);

			if (row > rows)
			{
				break;
			}

			source = data + cols * row;
			dest = &image8[i * 256];
			fracstep = cols * 0x10000 / 256;
			frac = fracstep >> 1;

			for (j = 0; j < 256; j++)
			{
				dest[j] = source[frac >> 16];
				frac += fracstep;
			}
		}

		glTexImage2D(GL_TEXTURE_2D, 0, GL_COLOR_INDEX8_EXT, 256, 256,
				0, GL_COLOR_INDEX, GL_UNSIGNED_BYTE, image8);
		"""

	# Note: gl_filter_min could be GL_*_MIPMAP_* so we can't use it for min filter here (=> no mipmaps)
	#       but gl_filter_max (either GL_LINEAR or GL_NEAREST) should do the trick.
	filter = gl1_image.gl_filter_max if (gl1_main.r_videos_unfiltered.value == 0) else GL.GL_NEAREST #GLint
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, filter)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, filter)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
	GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glVertexPointer( 2, GL.GL_FLOAT, 0, vtx )
	GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
	GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )
