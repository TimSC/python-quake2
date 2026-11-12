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
 * Lightmaps and dynamic lighting
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np

from common import clientserver
from common.header import shared
from common.shared import shared as shared_c
from client import ref
from client.refresh import ref_shared
from client.refresh.files import surf as files_surf
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model
from client.refresh.gl3 import gl3_main, gl3_shaders, gl3_surf

#include "header/local.h"

#extern gl3lightmapstate_t gl3_lms;

r_dlightframecount = 0 #int
pointcolor = np.zeros(3, dtype=np.float32) #static vec3_t
lightplane = None #static cplane_t *, used as shadow plane
lightspot = np.zeros(3, dtype=np.float32) #vec3_t

vec3_origin = np.zeros(3, dtype=np.float32)

def GL3_MarkSurfaceLights(light, bit, node, r_dlightframecount): #dlight_t *, int, mnode_t *, int

	#msurface_t	*surf;
	#int			i;

	# mark the polygons
	for i in range(node.numsurfaces):

		surf = gl3_main.gl3_worldmodel.surfaces[node.firstsurface + i]

		#int sidebit;
		#float dist;

		if surf.dlightframe != r_dlightframecount:

			surf.dlightbits = 0
			surf.dlightframe = r_dlightframecount

		dist = shared.DotProduct(light.origin, surf.plane.normal) - surf.plane.dist

		if dist >= 0:

			sidebit = 0

		else:

			sidebit = model.SURF_PLANEBACK

		if (surf.flags & model.SURF_PLANEBACK) != sidebit:

			continue

		surf.dlightbits |= bit

def GL3_PushDlights(): #void

	global r_dlightframecount

	#int i;
	#dlight_t *l;

	# because the count hasn't advanced yet for this frame
	r_dlightframecount = gl3_main.gl3_framecount + 1

	lightsData = gl3_main.gl3state.uniLightsData

	# gl3state.uniLightsData.numDynLights = r_newrefdef.num_dlights;
	# Q2PORT: numDynLights is a GLuint among the floats of the UBO data
	lightsData.view(np.uint32)[local.UNILIGHTS_NUM] = gl3_main.r_newrefdef.num_dlights

	i = 0
	while i < gl3_main.r_newrefdef.num_dlights:

		l = gl3_main.r_newrefdef.dlights[i]
		# gl3UniDynLight* udl = &gl3state.uniLightsData.dynLights[i]; origin [0..2], _padding, color [4..6], intensity
		udl = lightsData[i * 8:i * 8 + 8]
		files_surf.R_MarkLights(l, 1 << i, gl3_main.gl3_worldmodel.nodes[0], r_dlightframecount, GL3_MarkSurfaceLights)

		udl[0:3] = l.origin # VectorCopy(l->origin, udl->origin)
		udl[4:7] = l.color # VectorCopy(l->color, udl->color)
		udl[7] = l.intensity

		i += 1

	assert ref.MAX_DLIGHTS == 32, "If MAX_DLIGHTS changes, remember to adjust the uniform buffer definition in the shader!"

	if i < ref.MAX_DLIGHTS:

		lightsData[i * 8:ref.MAX_DLIGHTS * 8] = 0

	gl3_shaders.GL3_UpdateUBOLights()

def RecursiveLightPoint(node, start, end): #mnode_t *, vec3_t, vec3_t (returns int)

	global lightplane

	#float front, back, frac;
	#int side;
	#cplane_t *plane;
	mid = [0.0, 0.0, 0.0] #vec3_t, Q2PORT: python floats
	#msurface_t *surf;
	#int s, t, ds, dt;
	#int i;
	#mtexinfo_t *tex;
	#byte *lightmap;
	#int maps;
	#int r;

	if node.contents != ref_shared.CONTENTS_NODE:

		return -1 # didn't hit anything

	# Q2PORT: start, end, mid and the plane normal as python floats, as numpy
	# scalar arithmetic is slow (this recurses down the BSP for each model's
	# light). The sums are in doubles rather than the C's floats, so now and
	# then (about 1 in 500 in the demos) the lightmap texel picked below is the
	# neighbour of the C's.
	if type(start) is np.ndarray:
		start = start.tolist()
	if type(end) is np.ndarray:
		end = end.tolist()

	# calculate mid point
	plane = node.plane
	normal = plane.normal.tolist() # Q2PORT
	front = shared.DotProduct(start, normal) - plane.dist
	back = shared.DotProduct(end, normal) - plane.dist
	side = int(front < 0)

	if int(back < 0) == side:

		return RecursiveLightPoint(node.children[side], start, end)

	frac = front / (front - back)
	mid[0] = start[0] + (end[0] - start[0]) * frac
	mid[1] = start[1] + (end[1] - start[1]) * frac
	mid[2] = start[2] + (end[2] - start[2]) * frac

	# go down front side
	r = RecursiveLightPoint(node.children[side], start, mid)

	if r >= 0:

		return r # hit something

	if int(back < 0) == side:

		return -1 # didn't hit anuthing

	# check for impact on this node
	shared.VectorCopy(mid, lightspot)
	lightplane = plane

	for i in range(node.numsurfaces):

		surf = gl3_main.gl3_worldmodel.surfaces[node.firstsurface + i]

		if surf.flags & (model.SURF_DRAWTURB | model.SURF_DRAWSKY):

			continue # no lightmaps

		tex = surf.texinfo

		s = int(shared.DotProduct(mid, tex.vecs[0]) + tex.vecs[0][3]) # int, truncated as the C's
		t = int(shared.DotProduct(mid, tex.vecs[1]) + tex.vecs[1][3])

		if ((s < surf.texturemins[0]) or
			(t < surf.texturemins[1])):

			continue

		ds = s - surf.texturemins[0]
		dt = t - surf.texturemins[1]

		if (ds > surf.extents[0]) or (dt > surf.extents[1]):

			continue

		if surf.samples is None:

			return 0

		ds >>= 4
		dt >>= 4

		lightmap = surf.samples
		shared.VectorCopy(vec3_origin, pointcolor)

		lm = 3 * (dt * ((surf.extents[0] >> 4) + 1) + ds) # lightmap += ...; Q2PORT: an index into surf->samples

		maps = 0
		while maps < local.MAX_LIGHTMAPS_PER_SURFACE and surf.styles[maps] != 255:

			#const float *rgb;
			#int j;

			rgb = gl3_main.r_newrefdef.lightstyles[surf.styles[maps]].rgb

			# Apply light level to models
			for j in range(3):

				#float	scale;

				scale = rgb[j] * gl3_main.r_modulate.value
				pointcolor[j] += lightmap[lm + j] * scale * (1.0 / 255)

			lm += (3 * ((surf.extents[0] >> 4) + 1) *
						((surf.extents[1] >> 4) + 1))

			maps += 1

		return 1

	# go down back side
	return RecursiveLightPoint(node.children[1 - side], mid, end) # node->children[!side]

def GL3_LightPoint(currententity, p, color): #entity_t *, vec3_t, vec3_t

	end = np.zeros(3, dtype=np.float32) #vec3_t
	#float r;
	#int lnum;
	#dlight_t *dl;
	dist = np.zeros(3, dtype=np.float32) #vec3_t
	#float add;

	if gl3_main.gl3_worldmodel.lightdata is None or currententity is None:

		color[0] = color[1] = color[2] = 1.0
		return

	end[0] = p[0]
	end[1] = p[1]
	end[2] = p[2] - 2048

	# TODO: don't just aggregate the color, but also save position of brightest+nearest light
	#       for shadow position and maybe lighting on model?

	r = RecursiveLightPoint(gl3_main.gl3_worldmodel.nodes[0], p, end)

	if r == -1:

		shared.VectorCopy(vec3_origin, color)

	else:

		shared.VectorCopy(pointcolor, color)

	# add dynamic lights
	for lnum in range(gl3_main.r_newrefdef.num_dlights):

		dl = gl3_main.r_newrefdef.dlights[lnum]

		shared.VectorSubtract(currententity.origin,
				dl.origin, dist)
		add = dl.intensity - shared_c.VectorLength(dist)
		add *= (1.0 / 256.0)

		if add > 0:

			shared_c.VectorMA(color, add, dl.color, color)

	shared_c.VectorScale(color, gl3_main.r_modulate.value, color)


"""
 * Combine and scale multiple lightmaps into the floating format in blocklights
"""
def GL3_BuildLightMap(surf, offsetInLMbuf, stride): #msurface_t *, int, int

	#int smax, tmax;
	#int r, g, b, a, max;
	#int i, j, size, map, numMaps;
	#byte *lightmap;

	if (surf.texinfo.flags &
		(shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP)):

		clientserver.Com_Error(shared.ERR_DROP, "GL3_BuildLightMap called for non-lit surface")

	smax = (surf.extents[0] >> 4) + 1
	tmax = (surf.extents[1] >> 4) + 1
	size = smax * tmax

	# Q2PORT: the destination block is a 2D numpy view (tmax rows of smax RGBA
	# texels) of each lightmap buffer, at offsetInLMbuf with stride bytes per
	# row, in place of the C's dest pointer stepping
	rowStride = stride
	row0 = offsetInLMbuf // rowStride
	col0 = offsetInLMbuf % rowStride

	def destBlock(map_):
		buf = np.frombuffer(gl3_surf.gl3_lms.lightmap_buffers[map_], dtype=np.uint8).reshape(-1, rowStride)
		return buf[row0:row0 + tmax, col0:col0 + 4*smax]

	stride -= (smax << 2)

	if size > 34*34*3:

		clientserver.Com_Error(shared.ERR_DROP, "Bad s_blocklights size")

	# count number of lightmaps surf actually has
	numMaps = 0
	while numMaps < local.MAX_LIGHTMAPS_PER_SURFACE and surf.styles[numMaps] != 255:
		numMaps += 1

	if surf.samples is None:

		# no lightmap samples? set at least one lightmap to fullbright, rest to 0 as normal

		if numMaps == 0:  numMaps = 1 # make sure at least one lightmap is set to fullbright

		for map_ in range(local.MAX_LIGHTMAPS_PER_SURFACE):

			# we always create 4 (MAX_LIGHTMAPS_PER_SURFACE) lightmaps.
			# if surf has less (numMaps < 4), the remaining ones are zeroed out.
			# this makes sure that all 4 lightmap textures in gl3state.lightmap_textureIDs[i] have the same layout
			# and the shader can use the same texture coordinates for all of them

			c = 255 if (map_ < numMaps) else 0
			destBlock(map_)[:] = c # memset(dest, c, 4*smax) for each of the tmax rows

		return

	# add all the lightmaps

	# Note: dynamic lights aren't handled here anymore, they're handled in the shader

	# as we don't apply scale here anymore, nor blend the numMaps lightmaps together,
	# the code has gotten a lot easier and we can copy directly from surf->samples to dest
	# without converting to float first etc

	lightmap = 0 # lightmap = surf->samples; Q2PORT: an offset into it

	map_ = 0
	while map_ < numMaps:

		# Q2PORT: the C's per-texel loop over the tmax x smax block, done with numpy
		rgb = np.frombuffer(surf.samples, dtype=np.uint8, count=size * 3, offset=lightmap).reshape(tmax, smax, 3)

		dest = destBlock(map_).reshape(tmax, smax, 4)
		dest[:, :, 0:3] = rgb

		# alpha is ONLY used for the mono lightmap case. For this
		#   reason we set it to the brightest of the color components
		#   so that things don't get too dim.
		dest[:, :, 3] = rgb.max(axis=2) # determine the brightest of the three color components

		lightmap += size * 3 # skip to next lightmap

		map_ += 1

	while map_ < local.MAX_LIGHTMAPS_PER_SURFACE:

		# like above, fill up remaining lightmaps with 0

		destBlock(map_)[:] = 0

		map_ += 1
