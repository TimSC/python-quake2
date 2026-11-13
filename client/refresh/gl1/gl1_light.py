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
 * Lightmaps and dynamic lighting
 *
 * =======================================================================
"""
from __future__ import annotations

import math
import numpy as np
import OpenGL.GL as GL
from client.refresh.gl1 import gl1_main, gl1_image, gl1_buffer
from common import clientserver
from client.refresh import ref_shared
from client.refresh.gl1.header import model
from client.refresh.files import surf as files_surf
from q2data import bsp as q2bsp
from common.header import shared
from common.shared import shared as shared_c

#include "header/local.h"

r_dlightframecount = 0 #int
pointcolor = np.zeros((3,), dtype=np.float32) #vec3_t
lightplane = None #cplane_t *, used as shadow plane
lightspot = np.zeros((3,), dtype=np.float32) #vec3_t
s_blocklights = np.zeros((34 * 34 * 3,), dtype=np.float32) #static float [34 * 34 * 3]
TEXEL_ACC = np.arange(34, dtype=np.float32) * 16 # Q2PORT: the ftacc/fsacc of each texel row/column, for R_AddDynamicLights()

minlight = bytearray(256) #byte [256]

def R_RenderDlight(light): #dlight_t * (static)

	rad = light.intensity * 0.35 #const float
	#int i, j, clr[3];
	#float vtx[3], a;
	clr = [0, 0, 0]
	vtx = [0.0, 0.0, 0.0]

	gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_FAN, 18)

	for i in range(3):

		vtx[i] = light.origin[i] - gl1_main.vpn[i] * rad
		clr[i] = int(light.color[i] * 51)	# 255 * 0.2 = 51

	gl1_buffer.GLBUFFER_VERTEX( vtx[0], vtx[1], vtx[2] )
	gl1_buffer.GLBUFFER_COLOR( clr[0], clr[1], clr[2], 255 )

	for i in range(16, -1, -1):

		a = i / 16.0 * math.pi * 2

		for j in range(3):

			vtx[j] = light.origin[j] + gl1_main.vright[j] * math.cos(a) * rad \
				+ gl1_main.vup[j] * math.sin(a) * rad

		gl1_buffer.GLBUFFER_VERTEX( vtx[0], vtx[1], vtx[2] )
		gl1_buffer.GLBUFFER_COLOR( 0, 0, 0, 255 )

def R_RenderDlights(): #void

	global r_dlightframecount

	#int i;
	#dlight_t *l;

	if not gl1_main.gl1_flashblend.value:

		return

	gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_flash, 0, 0, 0, 1)

	# because the count hasn't advanced yet for this frame
	r_dlightframecount = gl1_main.r_framecount + 1

	GL.glDepthMask(GL.GL_FALSE)
	GL.glDisable(GL.GL_TEXTURE_2D)
	GL.glShadeModel(GL.GL_SMOOTH)
	GL.glEnable(GL.GL_BLEND)
	GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE)

	for i in range(gl1_main.r_newrefdef.num_dlights):

		R_RenderDlight(gl1_main.r_newrefdef.dlights[i])

	gl1_buffer.R_ApplyGLBuffer()

	GL.glColor4f(1, 1, 1, 1)
	GL.glDisable(GL.GL_BLEND)
	GL.glEnable(GL.GL_TEXTURE_2D)
	GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
	GL.glDepthMask(GL.GL_TRUE)

def R_MarkSurfaceLights (light, bit, node, lightframecount): #dlight_t *, int, mnode_t *, int

	"""
	msurface_t *surf;
	int i;
	"""

	# mark the polygons
	surfaces = gl1_main.r_worldmodel.surfaces
	for i in range(node.numsurfaces):

		#int sidebit;
		#float dist;
		surf = surfaces[node.firstsurface + i]
		dist = shared.DotProduct (light.origin, surf.plane.normal) - surf.plane.dist
		if dist >= 0:
			sidebit = 0
		else:
			sidebit = model.SURF_PLANEBACK
		if (surf.flags & model.SURF_PLANEBACK) != sidebit:
			continue
		if surf.dlightframe != lightframecount:
			surf.dlightbits = 0
			surf.dlightframe = lightframecount
		surf.dlightbits |= bit


def R_PushDlights ():

	global r_dlightframecount

	#int		i;
	#dlight_t	*l;

	if gl1_main.gl1_flashblend.value:
		return

	r_dlightframecount = gl1_main.r_framecount + 1	# because the count hasn't
											#  advanced yet for this frame
	for i in range(gl1_main.r_newrefdef.num_dlights):
		files_surf.R_MarkLights ( gl1_main.r_newrefdef.dlights[i], 1<<i,
			gl1_main.r_worldmodel.nodes[0], r_dlightframecount, R_MarkSurfaceLights )



def R_RecursiveLightPoint (node, start, end): #mnode_t *, vec3_t, vec3_t (returns int)

	global lightplane

	"""
	float		front, back, frac;
	int			side;
	cplane_t	*plane;
	vec3_t		mid;
	msurface_t	*surf;
	int			s, t, ds, dt;
	int			i;
	mtexinfo_t	*tex;
	byte		*lightmap;
	int			maps;
	int			r;
	"""

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
	side = 1 if front < 0 else 0

	if (back < 0) == side:

		return R_RecursiveLightPoint(node.children[side], start, end)

	frac = front / (front - back)
	mid = [0.0, 0.0, 0.0] # Q2PORT: python floats
	mid[0] = start[0] + (end[0] - start[0]) * frac
	mid[1] = start[1] + (end[1] - start[1]) * frac
	mid[2] = start[2] + (end[2] - start[2]) * frac

	# go down front side
	r = R_RecursiveLightPoint(node.children[side], start, mid)

	if r >= 0:

		return r # hit something

	if (back < 0) == side:

		return -1 # didn't hit anuthing

	# check for impact on this node
	shared.VectorCopy(mid, lightspot)
	lightplane = plane

	surfaces = gl1_main.r_worldmodel.surfaces # r_worldmodel->surfaces + node->firstsurface

	for i in range(node.numsurfaces):

		surf = surfaces[node.firstsurface + i]

		if surf.flags & (model.SURF_DRAWTURB | model.SURF_DRAWSKY):

			continue # no lightmaps

		tex = surf.texinfo

		s = int(shared.DotProduct(mid, tex.vecs[0]) + tex.vecs[0][3])
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
		lightmap_p = 0 # Q2PORT: index into lightmap
		shared.VectorClear(pointcolor) # VectorCopy(vec3_origin, pointcolor);

		lightmap_p += 3 * (dt * ((surf.extents[0] >> 4) + 1) + ds)

		maps = 0
		while maps < q2bsp.MAX_LIGHTMAPS and surf.styles[maps] != 255:

			#const float *rgb;
			#int j;

			rgb = gl1_main.r_newrefdef.lightstyles[surf.styles[maps]].rgb

			# Apply light level to models
			for j in range(3):

				#float	scale;

				scale = rgb[j] * gl1_main.r_modulate.value
				pointcolor[j] += lightmap[lightmap_p + j] * scale * (1.0 / 255)

			lightmap_p += 3 * ((surf.extents[0] >> 4) + 1) * \
						((surf.extents[1] >> 4) + 1)

			maps += 1

		return 1

	# go down back side
	return R_RecursiveLightPoint (node.children[1 - side], mid, end)


def R_LightPoint (currententity, p, color): #entity_t *, vec3_t, vec3_t

	"""
	vec3_t		end;
	float		r;
	int			lnum;
	dlight_t	*dl;
	vec3_t		dist;
	float		add;
	"""
	
	if gl1_main.r_worldmodel.lightdata is None or not currententity:
	
		color[0] = color[1] = color[2] = 1.0
		return
	
	end = np.zeros((3,), dtype=np.float32)
	end[0] = p[0]
	end[1] = p[1]
	end[2] = p[2] - 2048
	
	r = R_RecursiveLightPoint (gl1_main.r_worldmodel.nodes[0], p, end)
	
	if r == -1:
		shared.VectorClear (color) # VectorCopy (vec3_origin, color)
	else:
		shared.VectorCopy (pointcolor, color)

	#
	# add dynamic lights
	#
	dist = np.zeros((3,), dtype=np.float32)
	dlights = gl1_main.r_newrefdef.dlights
	for lnum in range(gl1_main.r_newrefdef.num_dlights):
	
		dl = dlights[lnum]
		shared.VectorSubtract (currententity.origin,
						dl.origin,
						dist)
		add = dl.intensity - shared_c.VectorLength(dist)
		add *= (1.0/256)
		if add > 0:
			shared_c.VectorMA (color, add, dl.color, color)
	
	shared_c.VectorScale (color, gl1_main.r_modulate.value, color)


def R_AddDynamicLights (surf): #msurface_t *

	"""
	int			lnum;
	int			sd, td;
	float		fdist, frad, fminlight;
	vec3_t		impact, local;
	int			s, t;
	int			i;
	int			smax, tmax;
	mtexinfo_t	*tex;
	dlight_t	*dl;
	float		*pfBL;
	float		fsacc, ftacc;
	"""
	impact = np.zeros((3,), dtype=np.float32)
	local = [0.0, 0.0]

	smax = (surf.extents[0]>>4)+1
	tmax = (surf.extents[1]>>4)+1
	tex = surf.texinfo

	for lnum in range(gl1_main.r_newrefdef.num_dlights):
	
		if not (surf.dlightbits & (1<<lnum) ):
			continue		# not lit by this light

		dl = gl1_main.r_newrefdef.dlights[lnum]
		frad = dl.intensity
		fdist = shared.DotProduct (dl.origin, surf.plane.normal) - \
				surf.plane.dist
		frad -= abs(fdist)
		# rad is now the highest intensity on the plane

		fminlight = ref_shared.DLIGHT_CUTOFF
		if frad < fminlight:
			continue
		fminlight = frad - fminlight

		for i in range(3):
		
			impact[i] = dl.origin[i] - \
					surf.plane.normal[i]*fdist
		
		local[0] = shared.DotProduct (impact, tex.vecs[0]) + tex.vecs[0][3] - surf.texturemins[0]
		local[1] = shared.DotProduct (impact, tex.vecs[1]) + tex.vecs[1][3] - surf.texturemins[1]

		# Q2PORT: the C's loops over t and s, done for all the texels at once with
		# numpy (the per texel python loop was slow):
		#	for (t = 0, ftacc = 0; t < tmax; t++, ftacc += 16)
		#		td = abs((int)(local[1] - ftacc));
		#		for (s = 0, fsacc = 0; s < smax; s++, fsacc += 16, pfBL += 3)
		#			sd = abs(Q_ftol(local[0] - fsacc));
		#			fdist = sd > td ? sd + (td >> 1) : td + (sd >> 1);
		#			if (fdist < fminlight)
		#				pfBL[0..2] += (frad - fdist) * dl->color[0..2];
		td = np.abs((np.float32(local[1]) - TEXEL_ACC[:tmax]).astype(np.int32))[:, None]
		sd = np.abs((np.float32(local[0]) - TEXEL_ACC[:smax]).astype(np.int32))

		fdist = np.where(sd > td, sd + (td >> 1), td + (sd >> 1)) # (tmax, smax)
		add = np.float32(frad) - fdist # frad - fdist
		add[fdist >= fminlight] = 0 # only where fdist < fminlight

		pfBL = s_blocklights[:tmax * smax * 3].reshape((tmax, smax, 3))
		pfBL += add[:, :, None] * np.asarray(dl.color, dtype=np.float32)
		

def R_SetCacheState(surf): #msurface_t *

	#int maps;

	maps = 0
	while maps < q2bsp.MAX_LIGHTMAPS and surf.styles[maps] != 255:

		surf.cached_light[maps] = \
			gl1_main.r_newrefdef.lightstyles[surf.styles[maps]].white

		maps += 1

"""
 * Combine and scale multiple lightmaps into the floating format in blocklights
"""
def R_BuildLightMap(surf, dest, stride): #msurface_t *, byte *, int

	"""
	int smax, tmax;
	int r, g, b, a, max;
	int i, j, size;
	byte *lightmap;
	float scale[4];
	int nummaps;
	float *bl;
	"""
	scale = [0.0, 0.0, 0.0, 0.0]

	if (surf.texinfo.flags &
		(shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP)):

		clientserver.Com_Error(shared.ERR_DROP, "{} called for non-lit surface".format("R_BuildLightMap"))

	smax = (surf.extents[0] >> 4) + 1
	tmax = (surf.extents[1] >> 4) + 1
	size = smax * tmax

	if size > ((len(s_blocklights) * 4) >> 4): # (sizeof(s_blocklights) >> 4)

		clientserver.Com_Error(shared.ERR_DROP, "{}: Bad s_blocklights size".format("R_BuildLightMap"))

	store = False # Q2PORT: the C's goto store

	# Q2PORT: the loops over the texels below are done with numpy on the
	# (size, 3) part of s_blocklights in use, rather than texel by texel (slow)
	bl = s_blocklights[:size * 3].reshape((size, 3)) # bl = s_blocklights;

	# set to full bright if no light data
	if surf.samples is None:

		bl[:] = 255 # for (i = 0; i < size * 3; i++) s_blocklights[i] = 255;

		store = True # goto store;

	if not store:

		# count the # of maps
		nummaps = 0
		while nummaps < q2bsp.MAX_LIGHTMAPS and surf.styles[nummaps] != 255:

			nummaps += 1

		lightmap = surf.samples
		lm = 0 # Q2PORT: an offset into lightmap

		# add all the lightmaps
		if nummaps == 1:

			#int maps;

			maps = 0
			while maps < q2bsp.MAX_LIGHTMAPS and surf.styles[maps] != 255:

				for i in range(3):

					scale[i] = gl1_main.r_modulate.value * \
							   gl1_main.r_newrefdef.lightstyles[surf.styles[maps]].rgb[i]

				# Q2PORT: the lightmap's size texels, 3 bytes each
				texels = np.frombuffer(lightmap, dtype=np.uint8, count=size * 3, offset=lm).reshape((size, 3))

				if ((scale[0] == 1.0) and
					(scale[1] == 1.0) and
					(scale[2] == 1.0)):

					bl[:] = texels # bl[0..2] = lightmap[i * 3 + 0..2], for each texel i

				else:

					bl[:] = texels * np.array(scale[0:3], dtype=np.float32) # bl[0..2] = lightmap[i * 3 + 0..2] * scale[0..2]

				lm += size * 3 # skip to next lightmap
				maps += 1

		else:

			#int maps;

			bl[:] = 0 # memset(s_blocklights, 0, sizeof(s_blocklights[0]) * size * 3);

			maps = 0
			while maps < q2bsp.MAX_LIGHTMAPS and surf.styles[maps] != 255:

				for i in range(3):

					scale[i] = gl1_main.r_modulate.value * \
							   gl1_main.r_newrefdef.lightstyles[surf.styles[maps]].rgb[i]

				# Q2PORT: the lightmap's size texels, 3 bytes each
				texels = np.frombuffer(lightmap, dtype=np.uint8, count=size * 3, offset=lm).reshape((size, 3))

				if ((scale[0] == 1.0) and
					(scale[1] == 1.0) and
					(scale[2] == 1.0)):

					bl += texels # bl[0..2] += lightmap[i * 3 + 0..2], for each texel i

				else:

					bl += texels * np.array(scale[0:3], dtype=np.float32) # bl[0..2] += lightmap[i * 3 + 0..2] * scale[0..2]

				lm += size * 3 # skip to next lightmap
				maps += 1

		# add all the dynamic lights
		if surf.dlightframe == gl1_main.r_framecount:

			R_AddDynamicLights(surf)

#store:

	# Q2PORT: the C's loop over the rows and columns, for all the texels at once:
	#	r, g, b = Q_ftol(bl[0..2]), each at least 0 (catch negative lights)
	#	a = max = the brightest of r, g and b (alpha is ONLY used for the mono
	#	    lightmap case, so that things don't get too dim)
	#	if (max > 255) { t = 255.0F / max; r, g, b, a = (int)(r, g, b, a * t); }
	#	then minlight[] (if set) and gammatable[] for r, g and b
	#	dest[0..3] = r, g, b, a; dest += 4, and dest += stride after each row
	rgb = bl.astype(np.int32)
	np.maximum(rgb, 0, out=rgb) # catch negative lights

	# determine the brightest of the three color components
	max_ = rgb.max(axis=1)
	a = max_

	# rescale all the color components if the
	# intensity of the greatest channel exceeds
	# 1.0
	over = max_ > 255

	if over.any():

		t = np.float32(255.0) / max_[over].astype(np.float32)

		rgb[over] = (rgb[over].astype(np.float32) * t[:, None]).astype(np.int32)
		a = max_.copy()
		a[over] = (max_[over].astype(np.float32) * t).astype(np.int32)

	if gl1_main.gl_state.minlight_set:

		rgb = np.frombuffer(minlight, dtype=np.uint8)[rgb]

	# Q2PORT: dest as rows of (smax, 4) bytes, stride bytes apart
	out = np.ndarray((tmax, smax, 4), dtype=np.uint8, buffer=dest, strides=(stride, 4, 1))
	out[:, :, 0:3] = np.frombuffer(gl1_image.gammatable, dtype=np.uint8)[rgb].reshape((tmax, smax, 3))
	out[:, :, 3] = a.reshape((tmax, smax))
