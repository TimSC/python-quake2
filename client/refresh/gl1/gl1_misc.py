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
 * Misc refresher functions
 *
 * =======================================================================
"""
from __future__ import annotations

import os
import OpenGL.GL as GL
from client.refresh.gl1 import gl1_image, gl1_main, qgl
from client.refresh.gl1.header import qgl as qgl_h
from backends.unix import system
from common import clientserver

"""
#include "header/local.h"
"""

dottexture = [ #static byte[16][16]
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 1, 2, 3, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 1, 3, 3, 3, 3, 3, 3, 1, 0, 0, 0, 0, 0, 0, 0],
	[0, 2, 3, 3, 3, 3, 3, 3, 2, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 2, 3, 3, 3, 3, 3, 3, 2, 0, 0, 0, 0, 0, 0, 0],
	[0, 1, 3, 3, 3, 3, 3, 3, 1, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 1, 2, 3, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
]

squaretexture = [ #static byte[16][16]
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
	[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
]

notex = [ #static byte[4][4]
	[0, 0, 0, 0],
	[0, 0, 1, 1],
	[0, 1, 1, 1],
	[0, 1, 1, 1]
]

def R_InitParticleTexture(): #void

	#int x, y;
	#byte partData[16][16][4];
	#byte notexData[8][8][4];
	partData = bytearray(16 * 16 * 4)
	notexData = bytearray(8 * 8 * 4)

	# particle texture
	for x in range(16):

		for y in range(16):

			partData[(y * 16 + x) * 4 + 0] = 255
			partData[(y * 16 + x) * 4 + 1] = 255
			partData[(y * 16 + x) * 4 + 2] = 255

			if not gl1_main.gl1_particle_square.value:

				partData[(y * 16 + x) * 4 + 3] = dottexture[x][y] * 85

			else:

				partData[(y * 16 + x) * 4 + 3] = squaretexture[x][y] * 85

	gl1_main.r_particletexture = gl1_image.R_LoadPic("***particle***", partData,
	                              16, 0, 16, 0, 16 * 16, gl1_image.imagetype_t.it_sprite, 32)

	# also use this for bad textures, but without alpha
	for x in range(8):

		for y in range(8):

			notexData[(y * 8 + x) * 4 + 0] = notex[x & 3][y & 3] * 255
			notexData[(y * 8 + x) * 4 + 1] = 0
			notexData[(y * 8 + x) * 4 + 2] = 0
			notexData[(y * 8 + x) * 4 + 3] = 255

	gl1_main.r_notexture = gl1_image.R_LoadPic("***r_notexture***", notexData,
	                        8, 0, 8, 0, 8 * 8, gl1_image.imagetype_t.it_wall, 32)

def R_ScreenShot(): #void

	w = gl1_main.vid.width
	h = gl1_main.vid.height

	GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
	buffer = bytearray(GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE))

	# the pixels are now row-wise left to right, bottom to top,
	# but we need them row-wise left to right, top to bottom.
	# so swap bottom rows with top rows
	"""
	(row swap: not needed for the TGA below, which is stored bottom to top)
	"""

	# ri.Vid_WriteScreenshot(w, h, 3, buffer);
	# Q2PORT: the port's refimport_t has no Vid_WriteScreenshot yet (the
	# client's VID_WriteScreenshot isn't ported), so the screenshot is
	# written as id's quakeNN.tga in scrnshot/ until it is
	checkname = "{}/scrnshot".format(gl1_main.ri.FS_Gamedir())
	system.Sys_Mkdir(checkname)

	for i in range(100):

		picname = "quake{:02d}.tga".format(i)
		checkname = "{}/scrnshot/{}".format(gl1_main.ri.FS_Gamedir(), picname)
		if not os.path.exists(checkname):
			break

	else:

		clientserver.Com_Printf("SCR_ScreenShot_f: Couldn't create a file\n")
		return

	header = bytearray(18)
	header[2] = 2		# uncompressed type
	header[12] = w & 255
	header[13] = w >> 8
	header[14] = h & 255
	header[15] = h >> 8
	header[16] = 24	# pixel size

	# swap rgb to bgr
	buffer[0::3], buffer[2::3] = buffer[2::3], buffer[0::3]

	with open(checkname, "wb") as f:
		f.write(header + buffer)

	clientserver.Com_Printf("Wrote {}\n".format(picname))

def R_Strings(show_ext): #qboolean

	Printf_Ext = clientserver.Com_Printf if show_ext else clientserver.Com_DPrintf

	clientserver.Com_Printf("GL_VENDOR: {}\n".format(gl1_main.gl_config.vendor_string))
	clientserver.Com_Printf("GL_RENDERER: {}\n".format(gl1_main.gl_config.renderer_string))
	clientserver.Com_Printf("GL_VERSION: {}\n".format(gl1_main.gl_config.version_string))
	Printf_Ext("GL_EXTENSIONS: {}".format(gl1_main.gl_config.extensions_string))
	Printf_Ext("\n")	# For some reason this is being ignored in the line above.
	clientserver.Com_Printf("GL_EXTENSIONS number: {}\n".format(gl1_main.gl_config.num_extensions))

def R_SetDefaultState(): #void

	GL.glDisable(qgl_h.GL_MULTISAMPLE)
	GL.glCullFace(GL.GL_FRONT)
	GL.glEnable(GL.GL_TEXTURE_2D)

	GL.glEnable(GL.GL_ALPHA_TEST)
	GL.glAlphaFunc(GL.GL_GREATER, 0.666)

	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glDisable(GL.GL_CULL_FACE)
	GL.glDisable(GL.GL_BLEND)

	GL.glColor4f(1, 1, 1, 1)

	GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
	GL.glShadeModel(GL.GL_FLAT)

	gl1_image.R_TextureMode(gl1_main.gl_texturemode.string)
	gl1_image.R_TextureAlphaMode(gl1_main.gl1_texturealphamode.string)
	gl1_image.R_TextureSolidMode(gl1_main.gl1_texturesolidmode.string)

	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl1_image.gl_filter_min)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl1_image.gl_filter_max)

	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)

	GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

	gl1_image.R_TexEnv(GL.GL_REPLACE)

	if gl1_main.gl_config.pointparameters:

		#float attenuations[3];
		attenuations = [0.0, 0.0, 0.0]

		attenuations[0] = gl1_main.gl1_particle_att_a.value
		attenuations[1] = gl1_main.gl1_particle_att_b.value
		attenuations[2] = gl1_main.gl1_particle_att_c.value

		qgl.qglPointParameterf(qgl_h.GL_POINT_SIZE_MIN, gl1_main.gl1_particle_min_size.value)
		qgl.qglPointParameterf(qgl_h.GL_POINT_SIZE_MAX, gl1_main.gl1_particle_max_size.value)
		qgl.qglPointParameterfv(qgl_h.GL_POINT_DISTANCE_ATTENUATION, attenuations)

		# GL_POINT_SMOOTH is not implemented by some OpenGL
		# drivers, especially the crappy Mesa3D backends like
		# i915.so. That the points are squares and not circles
		# is not a problem by Quake II!
		if gl1_main.gl1_particle_square.value:

			GL.glDisable(GL.GL_POINT_SMOOTH)

		else:

			GL.glEnable(GL.GL_POINT_SMOOTH)

	if gl1_main.gl_config.palettedtexture:

		GL.glEnable(qgl_h.GL_SHARED_TEXTURE_PALETTE_EXT)
		# Q2PORT: d_8to24table holds (r, g, b, a); R_SetTexturePalette takes the C's packed unsigneds
		gl1_image.R_SetTexturePalette([c[0] | (c[1] << 8) | (c[2] << 16) | (c[3] << 24) for c in gl1_image.d_8to24table])

	if gl1_main.gl_msaa_samples.value:

		GL.glEnable(qgl_h.GL_MULTISAMPLE)
		GL.glHint(qgl_h.GL_MULTISAMPLE_FILTER_HINT_NV, GL.GL_NICEST)
