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
 * Misc OpenGL3 refresher functions
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL

from common import clientserver
from client.refresh import ref_shared
from client.refresh.gl3 import gl3_main, gl3_image

#include "header/local.h"

gl3_notexture = None #gl3image_t *, use for bad textures
gl3_particletexture = None #gl3image_t *, little dot for particles

def GL3_SetDefaultState(): #void

	# in GLES this is only supported with an extension:
	# https://www.khronos.org/registry/OpenGL/extensions/EXT/EXT_multisample_compatibility.txt
	# but apparently it's just enabled by default if set in the context?
	GL.glDisable(GL.GL_MULTISAMPLE)
	GL.glCullFace(GL.GL_FRONT)

	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glDisable(GL.GL_CULL_FACE)
	GL.glDisable(GL.GL_BLEND)

	# in GLES GL_FILL is the only supported mode
	GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

	# TODO: gl1_texturealphamode?
	gl3_image.GL3_TextureMode(gl3_main.gl_texturemode.string)
	#R_TextureAlphaMode(gl1_texturealphamode->string);
	#R_TextureSolidMode(gl1_texturesolidmode->string);

	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl3_image.gl_filter_min)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl3_image.gl_filter_max)

	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)

	GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

	if gl3_main.gl_msaa_samples.value:

		GL.glEnable(GL.GL_MULTISAMPLE)
		# glHint(GL_MULTISAMPLE_FILTER_HINT_NV, GL_NICEST); TODO what is this for?

dottexture = [ #static byte [8][8]
	[0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 1, 1, 0, 0, 0, 0],
	[0, 1, 1, 1, 1, 0, 0, 0],
	[0, 1, 1, 1, 1, 0, 0, 0],
	[0, 0, 1, 1, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0],
]

def GL3_InitParticleTexture(): #void

	global gl3_particletexture, gl3_notexture

	#int x, y;
	data = np.zeros((8, 8, 4), dtype=np.uint8) #byte [8][8][4]

	# particle texture
	for x in range(8):

		for y in range(8):

			data[y][x][0] = 255
			data[y][x][1] = 255
			data[y][x][2] = 255
			data[y][x][3] = dottexture[x][y] * 255

	gl3_particletexture = gl3_image.GL3_LoadPic("***particle***", data.tobytes(),
	                                  8, 0, 8, 0, 8 * 8, ref_shared.imagetype_t.it_sprite, 32)

	# also use this for bad textures, but without alpha
	for x in range(8):

		for y in range(8):

			data[y][x][0] = dottexture[x & 3][y & 3] * 255
			data[y][x][1] = 0
			data[y][x][2] = 0
			data[y][x][3] = 255

	gl3_notexture = gl3_image.GL3_LoadPic("***r_notexture***", data.tobytes(),
	                            8, 0, 8, 0, 8 * 8, ref_shared.imagetype_t.it_wall, 32)

def GL3_ScreenShot(): #void

	w, h = gl3_main.vid.width, gl3_main.vid.height

	# Desktop GL
	comps = 3

	GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
	buffer = GL.glReadPixels(0, 0, w, h, GL.GL_RGBA if (comps == 4) else GL.GL_RGB, GL.GL_UNSIGNED_BYTE)

	# the pixels are now row-wise left to right, bottom to top,
	# but we need them row-wise left to right, top to bottom.
	# so swap bottom rows with top rows
	# Q2PORT: the C's row swapping loop is a numpy flip
	buffer = np.frombuffer(buffer, dtype=np.uint8).reshape(h, w * comps)[::-1].tobytes()

	# ri.Vid_WriteScreenshot(w, h, comps, buffer);
	# Q2PORT: the port's refimport_t has no Vid_WriteScreenshot yet (the
	# client's VID_WriteScreenshot isn't ported)
	clientserver.Com_Printf("GL3_ScreenShot: Vid_WriteScreenshot is not ported yet, {}x{} screenshot not written\n".format(w, h))
