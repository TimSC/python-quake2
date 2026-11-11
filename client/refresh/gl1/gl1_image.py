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
 * Texture handling
 *
 * =======================================================================
"""
from __future__ import annotations

import math
import numpy as np
import OpenGL.GL as GL
from client.refresh import ref_shared
from client.refresh.gl1 import gl1_main, gl1_model, gl1_draw, gl1_scrap, gl1_light, qgl
from client.refresh.gl1.header import qgl as qgl_h
from client.refresh.files import stb as files_stb, pcx as files_pcx
from common import clientserver
from common.header import shared
from common.shared import shared as shared_c

"""
#include "header/local.h"
#include <limits.h>
"""

# Q2PORT: imagetype_t is ref_shared.h's, as in the C (the shared loaders in files/ use it too)
imagetype_t = ref_shared.imagetype_t

# from header/local.h
class image_t(object):

	def __init__(self):

		self.clear()

	def clear(self): # memset (image, 0, sizeof(*image))

		self.name = "" #char	[MAX_QPATH], game path, including extension
		self.type = imagetype_t.it_skin #imagetype_t
		self.width, self.height = 0, 0 #int, source image
		self.upload_width, self.upload_height = 0, 0 #int, after power of two and picmip
		self.registration_sequence = 0 #int, 0 = free
		self.texturechain = [] #msurface_t list, for sort-by-texture world drawing
		self.texnum = 0 #int, gl texture binding
		self.sl, self.tl, self.sh, self.th = 0.0, 0.0, 0.0, 0.0 #float, 0,0 - 1,1 unless part of the scrap
		self.scrap = False #qboolean
		self.has_alpha = False #qboolean

		self.paletted = False #qboolean

	def __repr__(self):
		return "image_t({}, texnum {})".format(self.name, self.texnum)

# from header/local.h
TEXNUM_LIGHTMAPS	= 1024
TEXNUM_SCRAPS		= TEXNUM_LIGHTMAPS + 128 * 3 # MAX_LIGHTMAPS * MAX_LIGHTMAP_COPIES
TEXNUM_IMAGES		= TEXNUM_SCRAPS + 4 # MAX_SCRAPS

MAX_GLTEXTURES	= 1024

gltextures = [] #image_t[MAX_GLTEXTURES];
for i in range(MAX_GLTEXTURES):
	gltextures.append(image_t())

numgltextures = 0 #int
image_max = 0 #static int

intensitytable = bytearray(256) #static byte[256]
gammatable = bytearray(256) #byte[256]

intensity = None #static cvar_t *

d_8to24table = [(0, 0, 0, 0)] * 256 #unsigned [256], Q2PORT: (r, g, b, a) per entry, as pcx.GetPCXPalette fills it

#extern cvar_t *gl1_minlight;

Q2_GL_SOLID_FORMAT = GL.GL_RGB
Q2_GL_ALPHA_FORMAT = GL.GL_RGBA

#ifdef YQ2_GL1_GLES
#define DEFAULT_SOLID_FORMAT GL_RGBA
#else
DEFAULT_SOLID_FORMAT = GL.GL_RGB
#endif

gl_tex_solid_format = DEFAULT_SOLID_FORMAT #int
gl_tex_alpha_format = GL.GL_RGBA #int

#undef DEFAULT_SOLID_FORMAT

gl_filter_min = GL.GL_LINEAR_MIPMAP_NEAREST #int
gl_filter_max = GL.GL_LINEAR #int

class glmode_t(object):

	def __init__(self, name, minimize, maximize):

		self.name = name #char *
		self.minimize, self.maximize = minimize, maximize #int

modes = [ #static const glmode_t[]
	glmode_t("GL_NEAREST", GL.GL_NEAREST, GL.GL_NEAREST),
	glmode_t("GL_LINEAR", GL.GL_LINEAR, GL.GL_LINEAR),
	glmode_t("GL_NEAREST_MIPMAP_NEAREST", GL.GL_NEAREST_MIPMAP_NEAREST, GL.GL_NEAREST),
	glmode_t("GL_LINEAR_MIPMAP_NEAREST", GL.GL_LINEAR_MIPMAP_NEAREST, GL.GL_LINEAR),
	glmode_t("GL_NEAREST_MIPMAP_LINEAR", GL.GL_NEAREST_MIPMAP_LINEAR, GL.GL_NEAREST),
	glmode_t("GL_LINEAR_MIPMAP_LINEAR", GL.GL_LINEAR_MIPMAP_LINEAR, GL.GL_LINEAR)
]

class gltmode_t(object):

	def __init__(self, name, mode):

		self.name = name #char *
		self.mode = mode #int

#ifdef YQ2_GL1_GLES
# (GLES only)
#else

gl_alpha_modes = [ #static const gltmode_t[]
	gltmode_t("default", GL.GL_RGBA),
	gltmode_t("GL_RGBA", GL.GL_RGBA),
	gltmode_t("GL_RGBA8", GL.GL_RGBA8),
	gltmode_t("GL_RGB5_A1", GL.GL_RGB5_A1),
	gltmode_t("GL_RGBA4", GL.GL_RGBA4),
	gltmode_t("GL_RGBA2", GL.GL_RGBA2),
]

gl_solid_modes = [ #static const gltmode_t[]
	gltmode_t("default", GL.GL_RGB),
	gltmode_t("GL_RGB", GL.GL_RGB),
	gltmode_t("GL_RGB8", GL.GL_RGB8),
	gltmode_t("GL_RGB5", GL.GL_RGB5),
	gltmode_t("GL_RGB4", GL.GL_RGB4),
	gltmode_t("GL_R3_G3_B2", GL.GL_R3_G3_B2),
]

#endif

upload_width, upload_height = 0, 0 #static int
uploaded_paletted = False #static qboolean

def R_SetTexturePalette(palette): #const unsigned [256]

	if gl1_main.gl_config.palettedtexture:

		#byte temptable[768];
		#int i;
		temptable = bytearray(768)

		for i in range(256):

			temptable[i * 3 + 0] = (palette[i] >> 0) & 0xff
			temptable[i * 3 + 1] = (palette[i] >> 8) & 0xff
			temptable[i * 3 + 2] = (palette[i] >> 16) & 0xff

		qgl.qglColorTableEXT(qgl_h.GL_SHARED_TEXTURE_PALETTE_EXT, GL.GL_RGB,
				256, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, bytes(temptable))

def R_SelectTexture(texture): #GLenum (static)

	if not gl1_main.gl_config.multitexture or gl1_main.gl_state.currenttarget == texture:
		return

	gl1_main.gl_state.currenttmu = texture - GL.GL_TEXTURE0
	gl1_main.gl_state.currenttarget = texture

	qgl.qglActiveTexture(texture)
	qgl.qglClientActiveTexture(texture)

lastmodes = [-1, -1] #static int [MAX_TEXTURE_UNITS], in R_TexEnv

def R_TexEnv(mode): #GLenum

	if mode != lastmodes[gl1_main.gl_state.currenttmu]:

		GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, mode)
		lastmodes[gl1_main.gl_state.currenttmu] = mode

def R_Bind(texnum): #int (returns qboolean)

	#extern image_t *draw_chars;

	if gl1_main.gl_nobind.value and gl1_draw.draw_chars: # performance evaluation option

		texnum = gl1_draw.draw_chars.texnum

	if gl1_main.gl_state.currenttextures[gl1_main.gl_state.currenttmu] == texnum:

		return False

	gl1_main.gl_state.currenttextures[gl1_main.gl_state.currenttmu] = texnum
	GL.glBindTexture(GL.GL_TEXTURE_2D, texnum)
	return True

def R_MBind(target, texnum): #GLenum, int

	tmu = target - GL.GL_TEXTURE0

	if target != gl1_main.gl_state.currenttarget:

		R_SelectTexture(target)

	if gl1_main.gl_state.currenttextures[tmu] == texnum:

		return

	R_Bind(texnum)

R_EnableMultitexture_active = False #static qboolean active, in R_EnableMultitexture

def R_EnableMultitexture(enable): #qboolean

	global R_EnableMultitexture_active

	if not gl1_main.gl_config.multitexture or enable == R_EnableMultitexture_active:

		return	# current state is the right one

	R_EnableMultitexture_active = enable
	R_SelectTexture(GL.GL_TEXTURE1)

	if R_EnableMultitexture_active and not gl1_main.r_fullbright.value:

		GL.glEnable(GL.GL_TEXTURE_2D)

		if gl1_main.gl_lightmap.value:

			R_TexEnv(GL.GL_REPLACE)

		else:

			R_TexEnv(GL.GL_MODULATE)

	else:	# disable multitexturing

		GL.glDisable(GL.GL_TEXTURE_2D)
		R_TexEnv(GL.GL_REPLACE)

	R_SelectTexture(GL.GL_TEXTURE0)
	R_TexEnv(GL.GL_REPLACE)

def R_TextureMode(string): #const char *

	global gl_filter_min, gl_filter_max

	#static const int num_modes = ARRLEN(modes);
	#int i, texnum;
	#image_t *glt;
	num_modes = len(modes)

	i = 0
	while i < num_modes:

		if not shared_c.Q_stricmp(modes[i].name, string):

			break

		i += 1

	if i == num_modes:

		clientserver.Com_Printf("bad filter name '{}'\n".format(string))
		return

	gl_filter_min = modes[i].minimize
	gl_filter_max = modes[i].maximize

	# clamp selected anisotropy
	if gl1_main.gl_config.anisotropic:

		if gl1_main.gl_anisotropic.value > gl1_main.gl_config.max_anisotropy:

			gl1_main.ri.Cvar_SetValue("r_anisotropic", gl1_main.gl_config.max_anisotropy)

	else:

		gl1_main.ri.Cvar_SetValue("r_anisotropic", 0.0)

	nolerplist = gl1_main.gl_nolerp_list.string #const char*
	lerplist = gl1_main.r_lerp_list.string #const char*
	unfiltered2D = gl1_main.r_2D_unfiltered.value != 0 #qboolean

	# change all the existing mipmap texture objects
	for i in range(numgltextures):

		glt = gltextures[i]

		nolerp = False
		# r_2D_unfiltered and r_nolerp_list allow rendering stuff unfiltered even if gl_filter_* is filtered
		if unfiltered2D and glt.type == imagetype_t.it_pic:

			# exception to that exception: stuff on the r_lerp_list
			nolerp = (lerplist is None) or (glt.name not in lerplist) # strstr(lerplist, glt->name) == NULL

		elif nolerplist is not None and glt.name in nolerplist: # strstr(nolerplist, glt->name) != NULL

			nolerp = True

		if not R_Bind(glt.texnum):

			continue	# don't bother changing anything if texture was already set

		if (glt.type != imagetype_t.it_pic) and (glt.type != imagetype_t.it_sky): # mipmapped texture

			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_min)
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

			# Set anisotropic filter if supported and enabled
			if gl1_main.gl_config.anisotropic and gl1_main.gl_anisotropic.value:

				GL.glTexParameteri(GL.GL_TEXTURE_2D, qgl_h.GL_TEXTURE_MAX_ANISOTROPY_EXT,
						int(shared.Q_max(gl1_main.gl_anisotropic.value, 1.0)))

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

	for texnum in range(gl1_scrap.MAX_SCRAPS_NOLERP, gl1_scrap.MAX_SCRAPS):

		R_Bind(TEXNUM_SCRAPS + texnum)

		if unfiltered2D:

			# 2D textures shouldn't be filtered by default (r_2D_unfiltered),
			# so the scrap shouldn't be filtered
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

		else: # 2D textures should be filtered by default => filter the scrap

			# we can't use gl_filter_min which might be GL_*_MIPMAP_*
			# also, there's no anisotropic filtering for textures w/o mipmaps
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_max)
			GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

def R_TextureAlphaMode(string): #const char *

	global gl_tex_alpha_format

	#static const int num_alpha_modes = ARRLEN(gl_alpha_modes);
	#int i;
	num_alpha_modes = len(gl_alpha_modes)

	i = 0
	while i < num_alpha_modes:

		if not shared_c.Q_stricmp(gl_alpha_modes[i].name, string):

			break

		i += 1

	if i == num_alpha_modes:

		clientserver.Com_Printf("bad alpha texture mode name\n")
		return

	gl_tex_alpha_format = gl_alpha_modes[i].mode

def R_TextureSolidMode(string): #const char *

	global gl_tex_solid_format

	#static const int num_solid_modes = ARRLEN(gl_solid_modes);
	#int i;
	num_solid_modes = len(gl_solid_modes)

	i = 0
	while i < num_solid_modes:

		if not shared_c.Q_stricmp(gl_solid_modes[i].name, string):

			break

		i += 1

	if i == num_solid_modes:

		clientserver.Com_Printf("bad solid texture mode name\n")
		return

	gl_tex_solid_format = gl_solid_modes[i].mode

def R_ImageList_f(): #void

	"""
	int i, used, texels;
	qboolean freeup;
	image_t *image;
	"""
	palstrings = [ #const char *[2]
		"RGB",
		"PAL"
	]

	clientserver.Com_Printf("------------------\n")
	texels = 0
	used = 0

	for i in range(numgltextures):

		image = gltextures[i]

		#int w, h;
		in_use = ""
		isScrap = 'S' if image.scrap else ' '

		if image.texnum <= 0:

			continue

		if image.registration_sequence == gl1_model.registration_sequence:

			in_use = "*"
			used += 1

		w = image.upload_width
		h = image.upload_height

		texels += w * h

		if image.type == imagetype_t.it_skin:
			imageType = 'M'
		elif image.type == imagetype_t.it_sprite:
			imageType = 'S'
		elif image.type == imagetype_t.it_wall:
			imageType = 'W'
		elif image.type == imagetype_t.it_pic:
			imageType = 'P'
		elif image.type == imagetype_t.it_sky:
			imageType = 'Y'
		else:
			imageType = '?'

		clientserver.Com_Printf("{}{} {:3d} {:3d} {}: {} ({}x{}) {}\n".format(
				isScrap, imageType, image.upload_width, image.upload_height,
				palstrings[image.paletted], image.name,
				image.width, image.height, in_use))

	clientserver.Com_Printf("Total texel count (not counting mipmaps): {}\n".format(
			texels))
	freeup = R_ImageHasFreeSpace()
	clientserver.Com_Printf("Used {} of {} / {} images{}.\n".format(
		used, image_max, MAX_GLTEXTURES, ", has free space" if freeup else ""))

"""
 * Scale up the pixel values in a
 * texture to increase the
 * lighting range
"""
def R_LightScaleTexture(inPic, inwidth, inheight, only_gamma): #unsigned *, int, int, qboolean (static)

	# Q2PORT: the per-pixel loops are numpy table lookups on a view of inPic, changed in place
	c = inwidth * inheight
	p = np.frombuffer(inPic, dtype=np.uint8, count=c * 4).reshape(c, 4)[:, :3]

	if only_gamma:

		# p[0] = gammatable[p[0]]; ...
		table = np.frombuffer(bytes(gammatable), dtype=np.uint8)

	else:

		# p[0] = gammatable[intensitytable[p[0]]]; ...
		table = np.frombuffer(bytes(gammatable), dtype=np.uint8)[np.frombuffer(bytes(intensitytable), dtype=np.uint8)]

	p[:] = table[p]

"""
 * Operates in place, quartering the size of the texture
"""
def R_MipMap(pic, width, height): #byte *, int, int (static)

	#int i, j;
	#byte *out;

	if width & 1:

		# odd widths (a 1 pixel wide mip level): the C loop reads across row ends, keep it as is
		width <<= 2
		height >>= 1
		c = 0 # in
		out = 0
		for i in range(height):
			for j in range(0, width, 8):
				pic[out + 0] = (pic[c + 0] + pic[c + 4] + pic[c + width + 0] + pic[c + width + 4]) >> 2
				pic[out + 1] = (pic[c + 1] + pic[c + 5] + pic[c + width + 1] + pic[c + width + 5]) >> 2
				pic[out + 2] = (pic[c + 2] + pic[c + 6] + pic[c + width + 2] + pic[c + width + 6]) >> 2
				pic[out + 3] = (pic[c + 3] + pic[c + 7] + pic[c + width + 3] + pic[c + width + 7]) >> 2
				out += 4
				c += 8
			c += width
		return

	# Q2PORT: for even widths the loops are done with numpy. Each output pixel is the >>2
	# average of a 2x2 block, written to the start of pic. The C writes never overtake its
	# reads, so computing from the original values gives the same bytes.
	src = np.frombuffer(pic, dtype=np.uint8, count=width * height * 4).reshape(height, width, 4).astype(np.uint16)
	height >>= 1
	half = (src[0:height * 2:2, 0:width:2] + src[0:height * 2:2, 1:width:2] + src[1:height * 2:2, 0:width:2] + src[1:height * 2:2, 1:width:2]) >> 2
	pic[0:half.size] = half.astype(np.uint8).tobytes()

"""
 * Returns has_alpha
"""
def R_BuildPalettedTexture(paletted_texture, scaled, scaled_width, scaled_height): #byte *, byte *, int, int (static)

	#int i;
	s = 0 # scaled

	for i in range(scaled_width * scaled_height):

		#unsigned int r, g, b, c;

		r = (scaled[s + 0] >> 3) & 31
		g = (scaled[s + 1] >> 2) & 63
		b = (scaled[s + 2] >> 3) & 31

		c = r | (g << 5) | (b << 11)

		paletted_texture[i] = gl1_main.gl_state.d_16to8table[c]

		s += 4

def R_Upload32Native(data, width, height, mipmap): #unsigned *, size_t, size_t, qboolean (returns qboolean) (static)

	global upload_width, upload_height

	# This is for GL 2.x so no palettes, no scaling, no messing around with the data here. :)
	#int samples;
	#int i, c;
	#byte *scan;
	#int comp;

	c = width * height
	scan = 3 # ((byte *)data) + 3
	samples = Q2_GL_SOLID_FORMAT
	comp = gl_tex_solid_format
	upload_width = width
	upload_height = height

	R_LightScaleTexture(data, upload_width, upload_height, not mipmap)

	# Q2PORT: the C's scan loop for a non-255 alpha, as one numpy test
	if c and np.any(np.frombuffer(data, dtype=np.uint8, count=c * 4)[scan::4] != 255):

		samples = Q2_GL_ALPHA_FORMAT
		comp = gl_tex_alpha_format

	GL.glTexParameteri(GL.GL_TEXTURE_2D, qgl_h.GL_GENERATE_MIPMAP, mipmap)
	GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, comp, width,
			height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
			bytes(data[:c * 4]))
	GL.glTexParameteri(GL.GL_TEXTURE_2D, qgl_h.GL_GENERATE_MIPMAP, False)
	return samples == Q2_GL_ALPHA_FORMAT

def R_Upload32Soft(data, width, height, mipmap): #unsigned *, size_t, size_t, qboolean (returns qboolean) (static)

	global upload_width, upload_height, uploaded_paletted

	"""
	int samples;
	unsigned scaled[256 * 256];
	byte paletted_texture[256 * 256];
	int scaled_width, scaled_height;
	int i, c;
	byte *scan;
	int comp;
	"""
	scaled = bytearray(256 * 256 * 4)
	paletted_texture = bytearray(256 * 256)

	uploaded_paletted = False

	scaled_width = shared_c.NextPow2(width)

	if gl1_main.gl1_round_down.value and (scaled_width > width) and mipmap:

		scaled_width >>= 1

	scaled_height = shared_c.NextPow2(height)

	if gl1_main.gl1_round_down.value and (scaled_height > height) and mipmap:

		scaled_height >>= 1

	# let people sample down the world textures for speed
	if mipmap:

		scaled_width >>= int(gl1_main.gl1_picmip.value)
		scaled_height >>= int(gl1_main.gl1_picmip.value)

	# don't ever bother with >256 textures
	if scaled_width > 256:

		scaled_width = 256

	if scaled_height > 256:

		scaled_height = 256

	if scaled_width < 1:

		scaled_width = 1

	if scaled_height < 1:

		scaled_height = 1

	upload_width = scaled_width
	upload_height = scaled_height

	if scaled_width * scaled_height > len(scaled) // 4:

		# this can't really happen (because they're clamped to 256 above), but whatever
		clientserver.Com_Error(shared.ERR_DROP, "{}: too big".format("R_Upload32Soft"))
		return False

	# scan the texture for any non-255 alpha
	c = width * height
	scan = 3 # ((byte *)data) + 3
	samples = Q2_GL_SOLID_FORMAT
	comp = gl_tex_solid_format

	# Q2PORT: the C's scan loop, as one numpy test
	if c and np.any(np.frombuffer(data, dtype=np.uint8, count=c * 4)[scan::4] != 255):

		samples = Q2_GL_ALPHA_FORMAT
		comp = gl_tex_alpha_format

	if (scaled_width == width) and (scaled_height == height):

		if not mipmap:

			if (qgl.qglColorTableEXT and gl1_main.gl1_palettedtexture.value and
				(samples == Q2_GL_SOLID_FORMAT)):

				uploaded_paletted = True
				R_BuildPalettedTexture(paletted_texture, data,
						scaled_width, scaled_height)
				GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, qgl_h.GL_COLOR_INDEX8_EXT,
						scaled_width, scaled_height, 0, GL.GL_COLOR_INDEX,
						GL.GL_UNSIGNED_BYTE, bytes(paletted_texture[:scaled_width * scaled_height]))

			else:

				GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, comp, scaled_width,
						scaled_height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
						bytes(data[:c * 4]))

			return samples == Q2_GL_ALPHA_FORMAT # goto done;

		scaled[:width * height * 4] = data[:width * height * 4] # memcpy(scaled, data, width * height * 4);

	else:

		files_stb.ResizeSTB(data, width, height,
				  scaled, scaled_width, scaled_height)

	R_LightScaleTexture(scaled, scaled_width, scaled_height, not mipmap)

	if (qgl.qglColorTableEXT and gl1_main.gl1_palettedtexture.value and
		(samples == Q2_GL_SOLID_FORMAT)):

		uploaded_paletted = True
		R_BuildPalettedTexture(paletted_texture, scaled,
				scaled_width, scaled_height)
		GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, qgl_h.GL_COLOR_INDEX8_EXT,
				scaled_width, scaled_height, 0, GL.GL_COLOR_INDEX,
				GL.GL_UNSIGNED_BYTE, bytes(paletted_texture[:scaled_width * scaled_height]))

	else:

		GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, comp, scaled_width,
				scaled_height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
				bytes(scaled[:scaled_width * scaled_height * 4]))

	if mipmap:

		#int miplevel;

		miplevel = 0

		while scaled_width > 1 or scaled_height > 1:

			R_MipMap(scaled, scaled_width, scaled_height)
			scaled_width >>= 1
			scaled_height >>= 1

			if scaled_width < 1:

				scaled_width = 1

			if scaled_height < 1:

				scaled_height = 1

			miplevel += 1

			if (qgl.qglColorTableEXT and gl1_main.gl1_palettedtexture.value and
				(samples == Q2_GL_SOLID_FORMAT)):

				uploaded_paletted = True
				R_BuildPalettedTexture(paletted_texture, scaled,
						scaled_width, scaled_height)
				GL.glTexImage2D(GL.GL_TEXTURE_2D, miplevel, qgl_h.GL_COLOR_INDEX8_EXT,
						scaled_width, scaled_height, 0, GL.GL_COLOR_INDEX,
						GL.GL_UNSIGNED_BYTE, bytes(paletted_texture[:scaled_width * scaled_height]))

			else:

				GL.glTexImage2D(GL.GL_TEXTURE_2D, miplevel, comp, scaled_width,
						scaled_height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(scaled[:scaled_width * scaled_height * 4]))

#done:

	return samples == Q2_GL_ALPHA_FORMAT

def R_Upload32(data, width, height, mipmap): #unsigned *, size_t, size_t, qboolean (returns qboolean)

	#qboolean res;

	# optimize 8bit images only when we forced such logic
	if gl1_main.r_scale8bittextures.value:

		files_stb.SmoothColorImage(data, width * height, width)

	if gl1_main.gl_config.npottextures:

		res = R_Upload32Native(data, width, height, mipmap)

	else:

		res = R_Upload32Soft(data, width, height, mipmap)

	if mipmap:

		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_min)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

	else:

		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_max)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

	if mipmap and gl1_main.gl_config.anisotropic and gl1_main.gl_anisotropic.value:

		GL.glTexParameteri(GL.GL_TEXTURE_2D, qgl_h.GL_TEXTURE_MAX_ANISOTROPY_EXT,
				int(shared.Q_max(gl1_main.gl_anisotropic.value, 1.0)))

	return res

"""
 * Returns has_alpha
"""
def R_Upload8(data, width, height, mipmap, is_sky): #byte *, int, int, qboolean, qboolean (returns qboolean) (static)

	if gl1_main.gl_config.palettedtexture and is_sky:

		GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, qgl_h.GL_COLOR_INDEX8_EXT,
				width, height, 0, GL.GL_COLOR_INDEX, GL.GL_UNSIGNED_BYTE,
				bytes(data[:width * height]))

		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_filter_max)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_filter_max)

		return False # SBF: FIXME - what is the correct return value?

	else:

		#unsigned *trans = NULL;
		#qboolean ret;

		trans = files_stb.R_Convert8to32(data, width, height, d_8to24table)
		if trans is None:

			return False

		ret = R_Upload32(trans, width, height, mipmap)
		#free(trans);
		return ret

"""
 * This is also used as an entry point for the generated r_notexture
"""
def R_LoadPic(name, pic, width, realwidth, height, realheight, data_size, type, bits): #const char *, byte *, int, int, int, int, size_t, imagetype_t, int (returns image_t *)

	global numgltextures

	#image_t *image;
	#qboolean nolerp = false;
	#int i;
	nolerp = False

	default2Dnolerp = gl1_main.r_2D_unfiltered.value != 0.0 #qboolean
	if default2Dnolerp and type == imagetype_t.it_pic:

		# if r_2D_unfiltered is true(ish), nolerp should usually be true,
		# *unless* the texture is on the r_lerp_list
		nolerp = (gl1_main.r_lerp_list.string is None) or (name not in gl1_main.r_lerp_list.string)

	elif gl1_main.gl_nolerp_list is not None and gl1_main.gl_nolerp_list.string is not None:

		nolerp = name in gl1_main.gl_nolerp_list.string # strstr(gl_nolerp_list->string, name) != NULL

	# find a free image_t
	i = 0
	while i < numgltextures:

		if not gltextures[i].texnum:

			break

		i += 1

	if i == numgltextures:

		if numgltextures == MAX_GLTEXTURES:

			clientserver.Com_Error(shared.ERR_DROP, "{}: MAX_GLTEXTURES".format("R_LoadPic"))

		numgltextures += 1

	image = gltextures[i]

	if len(name) >= shared.MAX_QPATH: # sizeof(image->name)

		clientserver.Com_Error(shared.ERR_DROP, "{}: \"{}\" is too long".format("R_LoadPic", name))
		return None

	image.name = name
	image.registration_sequence = gl1_model.registration_sequence

	image.width = width
	image.height = height
	image.type = type

	if (type == imagetype_t.it_skin) and (bits == 8):

		files_stb.R_FloodFillSkin(pic, width, height, d_8to24table)

	# Normalize crosshair images to white so that color tinting via
	# GL_MODULATE produces the correct hue regardless of the original
	# palette color used in the crosshair PCX.
	if bits == 8 and (name == "pics/ch1.pcx" or
			name == "pics/ch2.pcx" or
			name == "pics/ch3.pcx"):

		#int best = 0, i;
		#float best_lum = 0;
		best = 0
		best_lum = 0.0

		for j in range(255): # Q2PORT: j, the C's inner i shadows the outer one

			r, g, b = d_8to24table[j][0], d_8to24table[j][1], d_8to24table[j][2]
			lum = 0.299 * r + 0.587 * g + 0.114 * b

			if lum > best_lum:

				best_lum = lum
				best = j

		for j in range(width * height):

			if pic[j] != 255:

				pic[j] = best

	# load little pics into the scrap
	nonscrap = True # Q2PORT: the C's goto nonscrap
	if (image.type == imagetype_t.it_pic) and (width <= gl1_scrap.BLOCK_WIDTH) and (height <= gl1_scrap.BLOCK_HEIGHT):

		texnum = -1
		x, y = [0], [0] #int x, y;

		if bits == 32:

			texnum = gl1_scrap.Scrap_AllocBlock(width, height, x, y, pic, 0 if nolerp else gl1_scrap.MAX_SCRAPS_NOLERP)

		elif bits == 8:

			#unsigned *trans;

			trans = files_stb.R_Convert8to32(pic, width, height, d_8to24table)
			if trans is not None:

				texnum = gl1_scrap.Scrap_AllocBlock(width, height, x, y, trans, 0 if nolerp else gl1_scrap.MAX_SCRAPS_NOLERP)
				#free(trans);

		else:

			clientserver.Com_Error(shared.ERR_FATAL, "Error: texture '{}' has {} bits per pixel, only 8 and 32 supported!\n".format(
				name, bits)) # Sys_Error

		if texnum != -1:

			nonscrap = False

			if nolerp and texnum >= gl1_scrap.MAX_SCRAPS_NOLERP:

				clientserver.Com_Printf("{}: Nolerp image stored to lerp\n".format(name))

			image.texnum = TEXNUM_SCRAPS + texnum
			image.scrap = True
			image.has_alpha = True
			image.sl = x[0] / gl1_scrap.SCRAP_WIDTH
			image.sh = (x[0] + width) / gl1_scrap.SCRAP_WIDTH
			image.tl = y[0] / gl1_scrap.SCRAP_HEIGHT
			image.th = (y[0] + height) / gl1_scrap.SCRAP_HEIGHT
			image.upload_width = width
			image.upload_height = height

	if nonscrap:

	#nonscrap:
		image.scrap = False
		image.texnum = TEXNUM_IMAGES + i # (image - gltextures)
		R_Bind(image.texnum)

		if bits == 8:

			# resize 8bit images only when we forced such logic
			if gl1_main.r_scale8bittextures.value:

				#byte *image_converted;
				scale = 2

				# scale 3 times if lerp image
				if not nolerp and (gl1_main.vid.height >= 240 * 3):
					scale = 3

				if height == 0 or scale == 0:

					clientserver.Com_Error(shared.ERR_DROP, "{}: invalid dimensions".format("R_LoadPic"))
					return None

				image_converted = bytearray(width * height * scale * scale)

				if scale == 3:
					files_stb.scale3x(pic, image_converted, width, height)
				else:
					files_stb.scale2x(pic, image_converted, width, height)

				image.has_alpha = R_Upload8(image_converted, width * scale, height * scale,
							(image.type != imagetype_t.it_pic and image.type != imagetype_t.it_sky),
							image.type == imagetype_t.it_sky)
				#free(image_converted);

			else:

				image.has_alpha = R_Upload8(pic, width, height,
							(image.type != imagetype_t.it_pic and image.type != imagetype_t.it_sky),
							image.type == imagetype_t.it_sky)

		else:

			image.has_alpha = R_Upload32(pic, width, height,
						(image.type != imagetype_t.it_pic and image.type != imagetype_t.it_sky))

		image.upload_width = upload_width # after power of 2 and scales
		image.upload_height = upload_height
		image.paletted = uploaded_paletted

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
 * Finds or loads the given image or null
"""
def R_FindImage(originname, type): #const char *, imagetype_t (returns image_t *)

	"""
	char namewe[256], name[256] = {0};
	const char* ext;
	image_t *image;
	size_t len;
	int i;
	"""

	if not originname:

		return None

	name = originname[:255] # Q_strlcpy(name, originname, sizeof(name));

	# fix backslashes
	name = name.replace("\\", "/") # Q_replacebackslash(name);

	ext = shared_c.COM_FileExtension(name)
	if not ext:

		# file has no extension
		return None

	# Remove the extension
	len_ = len(name) - len(ext) - 1 # (ext - name) - 1
	if (len_ < 1) or (len_ > 256 - 1):

		clientserver.Com_DPrintf("{}: Bad filename {}\n".format("R_FindImage", name))
		return None

	namewe = name[:len_]

	# look for it
	for i in range(numgltextures):

		image = gltextures[i]

		if name == image.name:

			image.registration_sequence = gl1_model.registration_sequence
			return image

	#
	# load the pic from disk
	#
	image = files_stb.R_LoadImage(name, namewe, ext, type,
		gl1_main.r_retexturing.value, R_LoadPic)

	if image is None and gl1_main.r_validation.value > 0:

		clientserver.Com_Printf("{}: can't load {}\n".format("R_FindImage", name))

	return image

def RI_RegisterSkin(name): #const char * (returns struct image_s *)

	return R_FindImage(name, imagetype_t.it_skin)

"""
 * Any image that was not touched on
 * this registration sequence
 * will be freed.
"""
def R_FreeUnusedImages(): #void

	#image_t *image;
	#size_t i;

	# never free r_notexture or particle texture
	gl1_main.r_notexture.registration_sequence = gl1_model.registration_sequence
	gl1_main.r_particletexture.registration_sequence = gl1_model.registration_sequence

	for i in range(numgltextures):

		image = gltextures[i]

		if image.registration_sequence == gl1_model.registration_sequence:

			continue # used this sequence

		if not image.registration_sequence:

			continue # free image_t slot

		if image.type == imagetype_t.it_pic:

			continue # don't free pics

		# free it
		GL.glDeleteTextures(1, [image.texnum])
		image.clear() # memset(image, 0, sizeof(*image));

def R_ImageHasFreeSpace(): #void (returns qboolean)

	global image_max

	#int		i, used;
	#image_t	*image;

	used = 0

	for i in range(numgltextures):

		image = gltextures[i]

		if not image.name:
			continue
		if image.registration_sequence == gl1_model.registration_sequence:

			used += 1

	if image_max < used:

		image_max = used

	# should same size of free slots as currently used
	return (numgltextures + used) < MAX_GLTEXTURES

def R_InitImages(): #void

	global image_max, intensity

	"""
	byte *colormap;
	int i;
	float m;
	"""

	# Q2PORT: Yamagi's SDL2 build doesn't define GL1_GAMMATABLE; vid_gamma is
	# applied as a hardware gamma ramp by RI_UpdateGamma instead
	#ifdef GL1_GAMMATABLE
	#float	g = vid_gamma->value;
	#else
	g = 1.0 #float
	#endif
	g = shared.Q_max(g, 0.1)

	gl1_scrap.Scrap_Init()

	gl1_model.registration_sequence = 1
	image_max = 0

	# init intensity conversions
	intensity = gl1_main.ri.Cvar_Get("gl1_intensity", "2", shared.CVAR_ARCHIVE)

	if intensity.value <= 1:

		gl1_main.ri.Cvar_Set("gl1_intensity", "1")

	gl1_main.gl_state.sw_gamma = g
	gl1_main.gl_state.inverse_intensity = g / intensity.value

	# FIXME: I think this is redundant - RI_Init() already calls that!
	files_pcx.GetPCXPalette(None, d_8to24table) # GetPCXPalette (&colormap, d_8to24table);
	#free(colormap);

	if gl1_main.gl_config.palettedtexture:

		size, gl1_main.gl_state.d_16to8table = gl1_main.ri.FS_LoadFile("pics/16to8.dat")

		if not gl1_main.gl_state.d_16to8table:

			clientserver.Com_Error(shared.ERR_FATAL, "{}: Couldn't load pics/16to8.pcx".format(
				"R_InitImages"))

	if g == 1:

		for i in range(256):

			gammatable[i] = i

	else:

		g = 1.0 / g

		for i in range(256):

			#float inf;

			inf = math.pow((i + 0.5) / 255.5, g) * 255.0 + 0.5
			inf = shared.Q_clamp(inf, 0, 255)

			gammatable[i] = int(inf)

	for i in range(256):

		#int j;

		j = int(i * intensity.value)
		j = min(j, 255) # Q_min

		intensitytable[i] = j

	# I know, minimum light level's calculation is much simpler than gamma.
	# But will still need a vid_restart to apply its values to currently loaded
	# lightmaps. Also, memory is cheaper than CPU.
	m = shared.Q_clamp(gl1_main.gl1_minlight.value, 0, 255)
	gl1_main.gl_state.minlight_set = (m != 0)

	if not gl1_main.gl_state.minlight_set:	# minlight == 0

		for i in range(256):

			gl1_light.minlight[i] = i

	else:

		for i in range(256):

			inf = (255.0 - m) * i / 255.0 + m
			inf = shared.Q_clamp(inf, 0, 255)
			gl1_light.minlight[i] = int(inf)

def R_ShutdownImages(): #void

	#int i;
	#image_t *image;

	for i in range(numgltextures):

		image = gltextures[i]

		if not image.registration_sequence:

			continue # free image_t slot

		# free it
		GL.glDeleteTextures(1, [image.texnum])
		image.clear() # memset(image, 0, sizeof(*image));
