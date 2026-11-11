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
 * Texture handling for OpenGL3
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from OpenGL.GL.EXT.texture_filter_anisotropic import GL_TEXTURE_MAX_ANISOTROPY_EXT

from common import clientserver
from common.header import shared
from common.shared import shared as shared_c
from client.refresh import ref_shared
from client.refresh.files import stb as files_stb
from client.refresh.gl3.header import local
from client.refresh.gl3 import gl3_main, gl3_draw, gl3_misc, gl3_model

#include "header/local.h"

class glmode_t(object):

	def __init__(self, name, minimize, maximize):

		self.name = name #char *
		self.minimize, self.maximize = minimize, maximize #int

modes = [ #glmode_t []
	glmode_t("GL_NEAREST", GL.GL_NEAREST, GL.GL_NEAREST),
	glmode_t("GL_LINEAR", GL.GL_LINEAR, GL.GL_LINEAR),
	glmode_t("GL_NEAREST_MIPMAP_NEAREST", GL.GL_NEAREST_MIPMAP_NEAREST, GL.GL_NEAREST),
	glmode_t("GL_LINEAR_MIPMAP_NEAREST", GL.GL_LINEAR_MIPMAP_NEAREST, GL.GL_LINEAR),
	glmode_t("GL_NEAREST_MIPMAP_LINEAR", GL.GL_NEAREST_MIPMAP_LINEAR, GL.GL_NEAREST),
	glmode_t("GL_LINEAR_MIPMAP_LINEAR", GL.GL_LINEAR_MIPMAP_LINEAR, GL.GL_LINEAR)
]

gl_filter_min = GL.GL_LINEAR_MIPMAP_NEAREST #int
gl_filter_max = GL.GL_LINEAR #int

gl3textures = [] #gl3image_t [MAX_GL3TEXTURES]
for i in range(local.MAX_GL3TEXTURES):
	gl3textures.append(local.gl3image_t())
numgl3textures = 0 #int
image_max = 0 #static int

SCRAP_WIDTH = 1024
SCRAP_HEIGHT = 1024

scrap_allocated = [0] * SCRAP_WIDTH #static short [SCRAP_WIDTH]
gl3_scrap_texnum = 0 #static GLuint
# static unsigned scrap_texels[SCRAP_WIDTH * SCRAP_HEIGHT]; as RGBA bytes, a row per scanline
scrap_texels = np.zeros((SCRAP_HEIGHT, SCRAP_WIDTH * 4), dtype=np.uint8)
gl3_scrap_dirty = False #qboolean

def GL3_Scrap_Init(): #void

	global gl3_scrap_texnum

	scrap_allocated[:] = [0] * SCRAP_WIDTH # empty
	scrap_texels[:] = 0 # transparent

	gl3_scrap_texnum = GL.glGenTextures(1)

"""
 returns a texture number (relative to g3_scrap_texnum) and the position inside it
"""
def GL3_Scrap_AllocBlock(w, h, pic): #int, int, int *, int *, const unsigned * (returns int, x, y)

	global gl3_scrap_dirty

	x, y = 0, 0

	w += 2 # add an empty border to all sides
	h += 2

	best = SCRAP_HEIGHT

	for i in range(SCRAP_WIDTH - w):

		best2 = 0

		j = 0
		while j < w:

			if scrap_allocated[i + j] >= best:

				break

			if scrap_allocated[i + j] > best2:

				best2 = scrap_allocated[i + j]

			j += 1

		if j == w:
			# this is a valid spot
			x = i
			y = best = best2

	if best + h > SCRAP_HEIGHT:

		return -1, x, y

	for i in range(w):

		scrap_allocated[x + i] = best + h

	x += 1 # jump the border
	y += 1

	# Q2PORT: the C memcpy's a row of w-2 texels at a time; here the RGBA bytes
	# of the whole block are copied at once
	src = np.frombuffer(bytes(pic[:(w - 2) * (h - 2) * 4]), dtype=np.uint8).reshape(h - 2, (w - 2) * 4)
	scrap_texels[y:y + h - 2, x * 4:(x + w - 2) * 4] = src

	gl3_scrap_dirty = True

	return 0, x, y

def GL3_TextureMode(string): #char *

	global gl_filter_min, gl_filter_max

	num_modes = len(modes)

	i = 0
	while i < num_modes:

		if modes[i].name.lower() == string.lower(): # !Q_stricmp(modes[i].name, string)

			break

		i += 1

	if i == num_modes:

		clientserver.Com_Printf("bad filter name '{}' (probably from gl_texturemode)\n".format(string))
		return

	gl_filter_min = modes[i].minimize
	gl_filter_max = modes[i].maximize

	# clamp selected anisotropy
	if gl3_main.gl3config.anisotropic:

		if gl3_main.gl_anisotropic.value > gl3_main.gl3config.max_anisotropy:

			gl3_main.ri.Cvar_SetValue("r_anisotropic", gl3_main.gl3config.max_anisotropy)

	else:

		gl3_main.ri.Cvar_SetValue("r_anisotropic", 0.0)

	nolerplist = gl3_main.gl_nolerp_list.string
	lerplist = gl3_main.r_lerp_list.string
	unfiltered2D = gl3_main.r_2D_unfiltered.value != 0
	local.GL3_SelectTMU(GL.GL_TEXTURE0)

	# change all the existing texture objects
	for i in range(numgl3textures):

		glt = gl3textures[i]

		nolerp = False
		# r_2D_unfiltered and gl_nolerp_list allow rendering stuff unfiltered even if gl_filter_* is filtered
		if unfiltered2D and glt.type == ref_shared.imagetype_t.it_pic:

			# exception to that exception: stuff on the r_lerp_list
			nolerp = (lerplist is None) or (glt.name not in lerplist)

		elif nolerplist is not None and glt.name in nolerplist:

			nolerp = True

		if not GL3_Bind(glt.texnum):

			continue # don't bother changing anything if texture was already set

		if (glt.type != ref_shared.imagetype_t.it_pic) and (glt.type != ref_shared.imagetype_t.it_sky): # mipmapped texture

			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_min)
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

			# Set anisotropic filter if supported and enabled
			if gl3_main.gl3config.anisotropic and gl3_main.gl_anisotropic.value:

				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, int(max(gl3_main.gl_anisotropic.value, 1.0)))

		else: # texture has no mipmaps

			if nolerp:

				# this texture shouldn't be filtered at all (no gl_nolerp_list or r_2D_unfiltered case)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

			else:

				# we can't use gl_filter_min which might be GL_*_MIPMAP_*
				# also, there's no anisotropic filtering for textures w/o mipmaps
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_max)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

def GL3_Bind(texnum): #GLuint (returns qboolean)

	#extern gl3image_t *draw_chars;

	if gl3_main.gl_nobind.value and gl3_draw.draw_chars is not None: # performance evaluation option

		texnum = gl3_draw.draw_chars.texnum

	if gl3_main.gl3state.currenttexture == texnum:

		return False

	gl3_main.gl3state.currenttexture = texnum
	local.GL3_SelectTMU(GL.GL_TEXTURE0)
	GL.glBindTexture(GL.GL_TEXTURE_2D, texnum)
	return True

def GL3_BindLightmap(lightmapnum): #int

	if lightmapnum < 0 or lightmapnum >= local.MAX_LIGHTMAPS:

		clientserver.Com_Printf("WARNING: Invalid lightmapnum {} used!\n".format(lightmapnum))
		return

	if gl3_main.gl3state.currentlightmap == lightmapnum:

		return

	gl3_main.gl3state.currentlightmap = lightmapnum
	for i in range(local.MAX_LIGHTMAPS_PER_SURFACE):

		# this assumes that GL_TEXTURE<i+1> = GL_TEXTURE<i> + 1
		# at least for GL_TEXTURE0 .. GL_TEXTURE31 that's true
		local.GL3_SelectTMU(GL.GL_TEXTURE1+i)
		GL.glBindTexture(GL.GL_TEXTURE_2D, gl3_main.gl3state.lightmap_textureIDs[lightmapnum][i])

"""
 * Returns has_alpha
"""
def GL3_Upload32(data, width, height, mipmap): #unsigned *, int, int, qboolean (returns qboolean)

	#qboolean res;

	c = width * height
	comp = local.gl3_tex_solid_format
	samples = local.gl3_solid_format

	# Q2PORT: data is the RGBA bytes (or a uint8 numpy array of them); the C's
	# scan over every 4th byte for an alpha != 255 is a numpy test
	pixels = np.frombuffer(data, dtype=np.uint8, count=c * 4) if not isinstance(data, np.ndarray) else data.reshape(-1)[:c * 4]
	if np.any(pixels[3::4] != 255):

		samples = local.gl3_alpha_format
		comp = local.gl3_tex_alpha_format

	GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, comp, width, height,
	             0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pixels)

	res = (samples == local.gl3_alpha_format)

	if mipmap:

		# TODO: some hardware may require mipmapping disabled for NPOT textures!
		GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_min)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

	else: # if the texture has no mipmaps, we can't use gl_filter_min which might be GL_*_MIPMAP_*

		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_max)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

	if mipmap and gl3_main.gl3config.anisotropic and gl3_main.gl_anisotropic.value:

		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, int(max(gl3_main.gl_anisotropic.value, 1.0)))

	return res

"""
 * Returns has_alpha
"""
def GL3_Upload8(data, width, height, mipmap): #const byte *, size_t, size_t, qboolean (returns qboolean)

	trans = None
	#qboolean ret;

	trans = files_stb.R_Convert8to32(data, width, height, gl3_draw.d_8to24table)
	if trans is None:

		return False

	ret = GL3_Upload32(trans, width, height, mipmap)
	#free(trans);
	return ret

def GL3_Scrap_Upload(): #void

	global gl3_scrap_dirty

	GL3_Bind(gl3_scrap_texnum)

	GL3_Upload32(scrap_texels, SCRAP_WIDTH, SCRAP_HEIGHT, False)

	if gl3_main.r_2D_unfiltered.value != 0:

		# 2D textures shouldn't be filtered by default (r_2D_unfiltered),
		# so the scrap shouldn't be filtered
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

	else: # 2D textures should be filtered by default => filter the scrap

		# we can't use gl_filter_min which might be GL_*_MIPMAP_*
		# also, there's no anisotropic filtering for textures w/o mipmaps
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_max)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

	gl3_scrap_dirty = False

"""
 * This is also used as an entry point for the generated r_notexture
"""
def GL3_LoadPic(name, pic, width, realwidth, height, realheight, data_size, type, bits): #char *, byte *, int, int, int, int, size_t, imagetype_t, int (returns gl3image_t *)

	global numgl3textures

	image = None
	texNum = 0

	nolerp = False
	default2Dnolerp = gl3_main.r_2D_unfiltered.value != 0.0
	if default2Dnolerp and type == ref_shared.imagetype_t.it_pic:

		# if r_2D_unfiltered is true(ish), nolerp should usually be true,
		# *unless* the texture is on the r_lerp_list
		nolerp = (gl3_main.r_lerp_list.string is None) or (name not in gl3_main.r_lerp_list.string)

	elif gl3_main.gl_nolerp_list is not None and gl3_main.gl_nolerp_list.string is not None:

		nolerp = name in gl3_main.gl_nolerp_list.string

	# find a free gl3image_t
	i = 0
	while i < numgl3textures:

		if gl3textures[i].texnum == 0:

			break

		i += 1

	if i == numgl3textures:

		if numgl3textures == local.MAX_GL3TEXTURES:

			clientserver.Com_Error(shared.ERR_DROP, "MAX_GLTEXTURES")
			return None

		numgl3textures += 1

	image = gl3textures[i]

	if len(name) >= shared.MAX_QPATH: # sizeof(image->name)

		clientserver.Com_Error(shared.ERR_DROP, "{}: \"{}\" is too long".format("GL3_LoadPic", name))
		return None

	image.name = name
	image.registration_sequence = gl3_model.registration_sequence

	image.width = width
	image.height = height
	image.type = type

	# Q2PORT: R_FloodFillSkin and the crosshair fix below change the pic in place
	if bits == 8:
		pic = bytearray(pic[:width * height])

	if (type == ref_shared.imagetype_t.it_skin) and (bits == 8):

		files_stb.R_FloodFillSkin(pic, width, height, gl3_draw.d_8to24table)

	# Normalize crosshair images to white so that color tinting via
	#   multiplication produces the correct hue regardless of the
	#   original palette color used in the crosshair PCX.
	if bits == 8 and (name == "pics/ch1.pcx" or
			name == "pics/ch2.pcx" or
			name == "pics/ch3.pcx"):

		best = 0
		best_lum = 0

		for i in range(255):

			r = gl3_draw.d_8to24table[i][0]
			g = gl3_draw.d_8to24table[i][1]
			b = gl3_draw.d_8to24table[i][2]
			lum = 0.299 * r + 0.587 * g + 0.114 * b

			if lum > best_lum:

				best_lum = lum
				best = i

		for i in range(width * height):

			if pic[i] != 255:

				pic[i] = best

	nonscrap = True

	# load little pics into the scrap
	if (nolerp == default2Dnolerp and (image.type == ref_shared.imagetype_t.it_pic) and
		(image.width <= 128) and (image.height <= 128)):

		x, y = 0, 0
		nonscrap = False

		# copy the texels into the scrap block
		if bits == 8:

			trans = files_stb.R_Convert8to32(pic, width, height, gl3_draw.d_8to24table)
			if trans is not None:

				scrapnum, x, y = GL3_Scrap_AllocBlock(width, height, trans)
				#free(trans);
				if scrapnum == -1:
					nonscrap = True # goto nonscrap;

			else:

				gl3_main.ri.Sys_Error(shared.ERR_FATAL, "Error: Couldn't convert texture '{}' to 32bit?!\n".format(name))
				return None

		elif bits == 32:

			scrapnum, x, y = GL3_Scrap_AllocBlock(image.width, image.height, pic)
			if scrapnum == -1:

				nonscrap = True # goto nonscrap;

		else:

			gl3_main.ri.Sys_Error(shared.ERR_FATAL, "Error: texture '{}' has {} bits per pixel, only 8 and 32 supported!\n".format(name, bits))
			return None

		if not nonscrap:

			image.texnum = gl3_scrap_texnum
			image.scrap = True
			image.has_alpha = True
			image.sl = float(x) / SCRAP_WIDTH
			image.sh = float(x + image.width) / SCRAP_WIDTH
			image.tl = float(y) / SCRAP_HEIGHT
			image.th = float(y + image.height) / SCRAP_HEIGHT

	if nonscrap:

		#nonscrap:

		image.is_lava = ("lava" in name)
		image.scrap = False

		texNum = GL.glGenTextures(1)

		image.texnum = texNum

		local.GL3_SelectTMU(GL.GL_TEXTURE0)
		GL3_Bind(texNum)

		if bits == 8:

			# resize 8bit images only when we forced such logic
			if gl3_main.r_scale8bittextures.value:

				#byte *image_converted;
				scale = 2

				# scale 3 times if lerp image
				if not nolerp and (gl3_main.vid.height >= 240 * 3):
					scale = 3

				image_converted = bytearray(width * height * scale * scale)

				if scale == 3:
					files_stb.scale3x(pic, image_converted, width, height)
				else:
					files_stb.scale2x(pic, image_converted, width, height)

				image.has_alpha = GL3_Upload8(image_converted, width * scale, height * scale,
							(image.type != ref_shared.imagetype_t.it_pic and image.type != ref_shared.imagetype_t.it_sky))
				#free(image_converted);

			else:

				image.has_alpha = GL3_Upload8(pic, width, height,
							(image.type != ref_shared.imagetype_t.it_pic and image.type != ref_shared.imagetype_t.it_sky))

		else:

			image.has_alpha = GL3_Upload32(pic, width, height,
						(image.type != ref_shared.imagetype_t.it_pic and image.type != ref_shared.imagetype_t.it_sky))

		image.sl = 0
		image.sh = 1
		image.tl = 0
		image.th = 1

		if nolerp:

			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

	if realwidth and realheight:

		if (realwidth <= image.width) and (realheight <= image.height):

			image.width = realwidth
			image.height = realheight

		else:

			clientserver.Com_DPrintf(
					"Warning, image '{}' has hi-res replacement smaller than the original! ({} x {}) < ({} x {})\n".format(
					name, image.width, image.height, realwidth, realheight))

	return image

"""
 * Finds or loads the given image or NULL
"""
def GL3_FindImage(originname, type): #const char *, imagetype_t (returns gl3image_t *)

	#char namewe[256], name[256] = {0};
	#gl3image_t *image;
	#const char* ext;
	#size_t len;
	#int i;

	if originname is None:

		return None

	name = originname[:255] # Q_strlcpy(name, originname, sizeof(name))

	# fix backslashes
	name = name.replace("\\", "/") # Q_replacebackslash(name)

	ext = shared_c.COM_FileExtension(name)
	if not ext:

		# file has no extension
		return None

	# Remove the extension
	len_ = len(name) - len(ext) - 1 # (ext - name) - 1
	if (len_ < 1) or (len_ > 256 - 1):

		clientserver.Com_DPrintf("{}: Bad filename {}\n".format("GL3_FindImage", name))
		return None

	namewe = name[:len_]

	# look for it
	for i in range(numgl3textures):

		image = gl3textures[i]
		if name == image.name:

			image.registration_sequence = gl3_model.registration_sequence
			return image

	#
	# load the pic from disk
	#
	image = files_stb.R_LoadImage(name, namewe, ext, type,
		gl3_main.r_retexturing.value, GL3_LoadPic)

	if image is None and gl3_main.r_validation.value:

		clientserver.Com_Printf("{}: can't load {}\n".format("GL3_FindImage", name))

	return image

def GL3_RegisterSkin(name): #const char * (returns gl3image_t *)

	return GL3_FindImage(name, ref_shared.imagetype_t.it_skin)

"""
 * Any image that was not touched on
 * this registration sequence
 * will be freed.
"""
def GL3_FreeUnusedImages(): #void

	# never free r_notexture or particle texture
	gl3_misc.gl3_notexture.registration_sequence = gl3_model.registration_sequence
	gl3_misc.gl3_particletexture.registration_sequence = gl3_model.registration_sequence

	for i in range(numgl3textures):

		image = gl3textures[i]

		if image.registration_sequence == gl3_model.registration_sequence:

			continue # used this sequence

		if not image.registration_sequence:

			continue # free image_t slot

		if image.type == ref_shared.imagetype_t.it_pic:

			continue # don't free pics

		# free it
		GL.glDeleteTextures(1, [image.texnum])
		image.__init__() # memset(image, 0, sizeof(*image))

def GL3_ImageHasFreeSpace(): #void (returns qboolean)

	global image_max

	used = 0

	for i in range(numgl3textures):

		image = gl3textures[i]

		if not image.name:
			continue
		if image.registration_sequence == gl3_model.registration_sequence:

			used += 1

	if image_max < used:

		image_max = used

	# should same size of free slots as currently used
	return (numgl3textures + used) < local.MAX_GL3TEXTURES

def GL3_ShutdownImages(): #void

	for i in range(numgl3textures):

		image = gl3textures[i]

		if not image.registration_sequence:

			continue # free image_t slot

		# free it
		GL.glDeleteTextures(1, [image.texnum])
		image.__init__() # memset(image, 0, sizeof(*image))

	GL.glDeleteTextures(1, [gl3_scrap_texnum])

def IsNPOT(v): #int (returns qboolean)

	uv = v & 0xffffffff
	# just try all the power of two values between 1 and 1 << 15 (32k)
	for i in range(16):

		pot = (1 << i)
		if uv & pot:

			return uv != pot

	return True

def GL3_ImageList_f(): #void

	formatstrings = [
		"RGB ",
		"RGBA"
	]

	potstrings = [
		" POT", "NPOT"
	]

	clientserver.Com_Printf("------------------\n")
	texels = 0
	used = 0

	for i in range(numgl3textures):

		image = gl3textures[i]

		in_use = ""
		isNPOT = False
		if image.texnum == 0:

			continue

		if image.registration_sequence == gl3_model.registration_sequence:

			in_use = "*"
			used += 1

		w = image.width
		h = image.height

		isNPOT = IsNPOT(w) or IsNPOT(h)

		texels += w*h

		imageType = {
			ref_shared.imagetype_t.it_skin: 'M',
			ref_shared.imagetype_t.it_sprite: 'S',
			ref_shared.imagetype_t.it_wall: 'W',
			ref_shared.imagetype_t.it_pic: 'P',
			ref_shared.imagetype_t.it_sky: 'Y',
		}.get(image.type, '?')
		isScrap = 'S' if image.scrap else ' '
		isLava = 'L' if image.is_lava else ' '

		clientserver.Com_Printf("{}{}{} {:3} {:3} {} {}: {} {}\n".format(isScrap, imageType, isLava, w, h,
		         formatstrings[int(image.has_alpha)], potstrings[int(isNPOT)], image.name, in_use))

	clientserver.Com_Printf("Total texel count (not counting mipmaps): {}\n".format(texels))
	freeup = GL3_ImageHasFreeSpace()
	clientserver.Com_Printf("Used {} of {} images{}.\n".format(used, image_max, ", has free space" if freeup else ""))
