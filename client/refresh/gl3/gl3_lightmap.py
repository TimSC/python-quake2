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
 * Lightmap handling
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
import OpenGL.GL as GL

from common import clientserver
from common.header import shared
from client import ref
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model
from client.refresh.gl3 import gl3_main, gl3_image, gl3_light, gl3_surf

#include "header/local.h"


TEXNUM_LIGHTMAPS = 1024

GL_LIGHTMAP_FORMAT = GL.GL_RGBA # local.h

#extern gl3lightmapstate_t gl3_lms;

def GL3_LM_InitBlock(): #void

	gl3_surf.gl3_lms.allocated[:] = [0] * local.BLOCK_WIDTH # memset(gl3_lms.allocated, 0, sizeof(gl3_lms.allocated))

def GL3_LM_UploadBlock(): #void

	#int map;

	# NOTE: we don't use the dynamic lightmap anymore - all lightmaps are loaded at level load
	#       and not changed after that. they're blended dynamically depending on light styles
	#       though, and dynamic lights are (will be) applied in shader, hopefully per fragment.

	gl3_image.GL3_BindLightmap(gl3_surf.gl3_lms.current_lightmap_texture)

	# upload all 4 lightmaps
	for map_ in range(local.MAX_LIGHTMAPS_PER_SURFACE):

		local.GL3_SelectTMU(GL.GL_TEXTURE1+map_) # this relies on GL_TEXTURE2 being GL_TEXTURE1+1 etc
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
		GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

		GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL_LIGHTMAP_FORMAT,
		             local.BLOCK_WIDTH, local.BLOCK_HEIGHT, 0, GL_LIGHTMAP_FORMAT,
		             GL.GL_UNSIGNED_BYTE, gl3_surf.gl3_lms.lightmap_buffers[map_])

	gl3_surf.gl3_lms.current_lightmap_texture += 1
	if gl3_surf.gl3_lms.current_lightmap_texture == local.MAX_LIGHTMAPS:

		clientserver.Com_Error(shared.ERR_DROP, "LM_UploadBlock() - MAX_LIGHTMAPS exceeded\n")

"""
 * returns a texture number and the position inside it
"""
def GL3_LM_AllocBlock(w, h): #int, int, int *, int * (returns qboolean, x, y)

	#int i, j;
	#int best, best2;

	allocated = gl3_surf.gl3_lms.allocated
	x, y = 0, 0

	best = local.BLOCK_HEIGHT

	for i in range(local.BLOCK_WIDTH - w):

		best2 = 0

		j = 0
		while j < w:

			if allocated[i + j] >= best:

				break

			if allocated[i + j] > best2:

				best2 = allocated[i + j]

			j += 1

		if j == w:

			# this is a valid spot
			x = i
			y = best = best2

	if best + h > local.BLOCK_HEIGHT:

		return False, x, y

	for i in range(w):

		allocated[x + i] = best + h

	return True, x, y

def GL3_LM_BuildPolygonFromSurface(currentmodel, fa): #gl3model_t *, msurface_t *

	#int i, lindex, lnumverts;
	#medge_t *pedges, *r_pedge;
	#float *vec;
	#float s, t;
	#glpoly_t *poly;
	total = np.zeros(3, dtype=np.float32) #vec3_t
	normal = np.zeros(3, dtype=np.float32) #vec3_t

	# reconstruct the polygon
	pedges = currentmodel.edges
	lnumverts = fa.numedges

	#VectorClear(total);

	# draw texture
	poly = model.glpoly_t(lnumverts) # Hunk_Alloc(sizeof(glpoly_t) + (lnumverts - 4) * sizeof(gl3_3D_vtx_t))
	poly.flags = fa.flags
	fa.polys.insert(0, poly) # poly->next = fa->polys; fa->polys = poly;
	poly.numverts = lnumverts

	shared.VectorCopy(fa.plane.normal, normal)

	if fa.flags & model.SURF_PLANEBACK:

		# if for some reason the normal sticks to the back of the plane, invert it
		# so it's usable for the shader
		for i in range(3):  normal[i] = -normal[i]

	vecs = fa.texinfo.vecs
	for i in range(lnumverts):

		vert = poly.vertices[i]

		lindex = currentmodel.surfedges[fa.firstedge + i]

		if lindex > 0:

			r_pedge = pedges[lindex]
			vec = currentmodel.vertexes[r_pedge.v[0]].position

		else:

			r_pedge = pedges[-lindex]
			vec = currentmodel.vertexes[r_pedge.v[1]].position

		s = shared.DotProduct(vec, vecs[0]) + vecs[0][3]
		s /= fa.texinfo.image.width

		t = shared.DotProduct(vec, vecs[1]) + vecs[1][3]
		t /= fa.texinfo.image.height

		total += vec # VectorAdd(total, vec, total)
		vert["pos"] = vec
		vert["texCoord"] = (s, t)

		# lightmap texture coordinates
		s = shared.DotProduct(vec, vecs[0]) + vecs[0][3]
		s -= fa.texturemins[0]
		s += fa.light_s * 16
		s += 8
		s /= local.BLOCK_WIDTH * 16 # fa->texinfo->texture->width;

		t = shared.DotProduct(vec, vecs[1]) + vecs[1][3]
		t -= fa.texturemins[1]
		t += fa.light_t * 16
		t += 8
		t /= local.BLOCK_HEIGHT * 16 # fa->texinfo->texture->height;

		vert["lmTexCoord"] = (s, t)

		vert["normal"] = normal
		vert["lightFlags"] = 0

def GL3_LM_CreateSurfaceLightmap(surf): #msurface_t *

	#int smax, tmax;

	if surf.flags & (model.SURF_DRAWSKY | model.SURF_DRAWTURB):

		return

	smax = (surf.extents[0] >> 4) + 1
	tmax = (surf.extents[1] >> 4) + 1

	ok, surf.light_s, surf.light_t = GL3_LM_AllocBlock(smax, tmax)
	if not ok:

		GL3_LM_UploadBlock()
		GL3_LM_InitBlock()

		ok, surf.light_s, surf.light_t = GL3_LM_AllocBlock(smax, tmax)
		if not ok:

			clientserver.Com_Error(shared.ERR_FATAL, "Consecutive calls to LM_AllocBlock({},{}) failed\n".format(
					smax, tmax))

	surf.lightmaptexturenum = gl3_surf.gl3_lms.current_lightmap_texture

	gl3_light.GL3_BuildLightMap(surf, (surf.light_t * local.BLOCK_WIDTH + surf.light_s) * local.LIGHTMAP_BYTES, local.BLOCK_WIDTH * local.LIGHTMAP_BYTES)

lightstyles = [] #static lightstyle_t [MAX_LIGHTSTYLES]
for i in range(shared.MAX_LIGHTSTYLES):
	lightstyles.append(ref.lightstyle_t())

def GL3_LM_BeginBuildingLightmaps(m): #gl3model_t *

	gl3_surf.gl3_lms.allocated[:] = [0] * local.BLOCK_WIDTH # memset(gl3_lms.allocated, 0, sizeof(gl3_lms.allocated))

	gl3_main.gl3_framecount = 1 # no dlightcache

	# setup the base lightstyles so the lightmaps
	#   won't have to be regenerated the first time
	#   they're seen
	for i in range(shared.MAX_LIGHTSTYLES):

		lightstyles[i].rgb[0] = 1
		lightstyles[i].rgb[1] = 1
		lightstyles[i].rgb[2] = 1
		lightstyles[i].white = 3

	gl3_main.r_newrefdef.lightstyles = lightstyles

	gl3_surf.gl3_lms.current_lightmap_texture = 0

	# Note: the dynamic lightmap used to be initialized here, we don't use that anymore.

def GL3_LM_EndBuildingLightmaps(): #void

	GL3_LM_UploadBlock()
