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
 * Warps. Used on water surfaces und for skybox rotation.
 *
 * =======================================================================
"""

from __future__ import annotations

import math

import numpy as np
import OpenGL.GL as GL

from common import clientserver
from common.header import shared
from client.refresh import ref_shared
from client.refresh.files import stb as files_stb
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model
from client.refresh.gl3.header import hmm
from client.refresh.gl3 import gl3_main, gl3_image, gl3_misc

#include "header/local.h"

# Q2PORT: the C passes polygons as float arrays (3 floats per vertex) and
# steps a float pointer through them; here a polygon is a (numverts, 3)
# numpy array

def R_BoundPoly(numverts, verts, mins, maxs): #int, float *, vec3_t, vec3_t

	#int i, j;
	#float *v;

	mins[0] = mins[1] = mins[2] = 9999
	maxs[0] = maxs[1] = maxs[2] = -9999

	for i in range(numverts):

		for j in range(3):

			if verts[i][j] < mins[j]:

				mins[j] = verts[i][j]

			if verts[i][j] > maxs[j]:

				maxs[j] = verts[i][j]

SUBDIVIDE_SIZE = 64.0 #static const float

def R_SubdividePolygon(numverts, verts, warpface): #int, float *, msurface_t *

	#int i, j, k;
	mins = np.zeros(3, dtype=np.float32) #vec3_t
	maxs = np.zeros(3, dtype=np.float32) #vec3_t
	#float m;
	#float *v;
	front = np.zeros((64, 3), dtype=np.float32) #vec3_t [64]
	back = np.zeros((64, 3), dtype=np.float32) #vec3_t [64]
	#int f, b;
	dist = [0.0] * 64 #float [64]
	#float frac;
	#glpoly_t *poly;
	#float s, t;
	total = np.zeros(3, dtype=np.float32) #vec3_t
	#float total_s, total_t;
	normal = np.zeros(3, dtype=np.float32) #vec3_t

	shared.VectorCopy(warpface.plane.normal, normal)

	if numverts > 60:

		clientserver.Com_Error(shared.ERR_DROP, "numverts = {}".format(numverts))

	R_BoundPoly(numverts, verts, mins, maxs)

	for i in range(3):

		m = (mins[i] + maxs[i]) * 0.5
		m = SUBDIVIDE_SIZE * math.floor(m / SUBDIVIDE_SIZE + 0.5)

		if maxs[i] - m < 8:

			continue

		if m - mins[i] < 8:

			continue

		# cut it
		for j in range(numverts):

			dist[j] = verts[j][i] - m

		# wrap cases
		dist[numverts] = dist[0]
		# VectorCopy(verts, v): the C copies the first vertex after the last
		verts = np.vstack((verts[:numverts], verts[0:1]))

		f = b = 0

		for j in range(numverts):

			v = verts[j]

			if dist[j] >= 0:

				front[f] = v
				f += 1

			if dist[j] <= 0:

				back[b] = v
				b += 1

			if (dist[j] == 0) or (dist[j + 1] == 0):

				continue

			if (dist[j] > 0) != (dist[j + 1] > 0):

				# clip point
				frac = dist[j] / (dist[j] - dist[j + 1])

				for k in range(3):

					front[f][k] = back[b][k] = v[k] + frac * (verts[j + 1][k] - v[k])

				f += 1
				b += 1

		R_SubdividePolygon(f, front[:f].copy(), warpface)
		R_SubdividePolygon(b, back[:b].copy(), warpface)
		return

	# add a point in the center to help keep warp valid
	poly = model.glpoly_t(numverts + 2) # Hunk_Alloc(sizeof(glpoly_t) + ((numverts - 4) + 2) * sizeof(gl3_3D_vtx_t))
	warpface.polys.insert(0, poly) # poly->next = warpface->polys; warpface->polys = poly;
	poly.numverts = numverts + 2
	total_s = 0
	total_t = 0

	vecs = warpface.texinfo.vecs
	for i in range(numverts):

		vert = poly.vertices[i + 1]
		vert["pos"] = verts[i]
		s = shared.DotProduct(verts[i], vecs[0])
		t = shared.DotProduct(verts[i], vecs[1])

		total_s += s
		total_t += t
		total += verts[i] # VectorAdd(total, verts, total)

		vert["texCoord"] = (s, t)
		vert["normal"] = normal
		vert["lightFlags"] = 0

	poly.vertices[0]["pos"] = total * (1.0 / numverts) # VectorScale(total, (1.0 / numverts), poly->vertices[0].pos)
	poly.vertices[0]["texCoord"] = (total_s / numverts, total_t / numverts)
	poly.vertices[0]["normal"] = normal

	# copy first vertex to last
	#memcpy(poly->vertices[i + 1], poly->vertices[1], sizeof(poly->vertices[0]));
	poly.vertices[numverts + 1] = poly.vertices[1]

"""
 * Breaks a polygon up along axial 64 unit
 * boundaries so that turbulent and sky warps
 * can be done reasonably.
"""
def GL3_SubdivideSurface(fa, loadmodel): #msurface_t *, gl3model_t*

	verts = np.zeros((64, 3), dtype=np.float32) #vec3_t [64]
	#int numverts;
	#int i;
	#int lindex;
	#float *vec;

	# convert edges back to a normal polygon
	numverts = 0

	for i in range(fa.numedges):

		lindex = loadmodel.surfedges[fa.firstedge + i]

		if lindex > 0:

			vec = loadmodel.vertexes[loadmodel.edges[lindex].v[0]].position

		else:

			vec = loadmodel.vertexes[loadmodel.edges[-lindex].v[1]].position

		verts[numverts] = vec
		numverts += 1

	R_SubdividePolygon(numverts, verts[:numverts].copy(), fa)

"""
 * Does a water warp on the pre-fragmented glpoly_t chain
"""
def GL3_EmitWaterPolys(fa, drawCmd): #msurface_t *, gl3drawCmd_t

	#glpoly_t *bp;
	scroll = 0.0

	if fa.texinfo.flags & shared.SURF_FLOWING:

		scroll = -64.0 * ((gl3_main.r_newrefdef.time * 0.5) - int(gl3_main.r_newrefdef.time * 0.5))
		if scroll == 0.0: # this is done in GL3_DrawGLFlowingPoly() TODO: keep?

			scroll = -64.0

	# set this even if scroll is 0, because the shader uses scroll
	# so the uniform must be set either way
	drawCmd.scroll = scroll
	drawCmd.flags |= local.DCFlag_UseScroll

	# these surfaces (mostly water and lava, I think?) don't have a lightmap.
	# rendering water at full brightness looks bad (esp. for water in dark environments)
	# so default use a factor of 0.5 (ontop of intensity)
	# but lava should be bright and glowing, so use full brightness there
	drawCmd.lightScaleForTurb = 1.0 if fa.texinfo.image.is_lava else 0.5
	drawCmd.flags |= local.DCFlag_UseLightScaleForTurb

	local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3Dturb)

	for bp in fa.polys: # for (bp = fa->polys; bp != NULL; bp = bp->next)

		gl3_main.GL3_Add3DdrawCmdToBatch(bp.vertices, bp.numverts, GL.GL_TRIANGLE_FAN, drawCmd)

# ########### below: Sky-specific stuff ##########

ON_EPSILON = 0.1 # point on plane side epsilon
MAX_CLIP_VERTS = 64


skytexorder = [0, 2, 1, 3, 4, 5] #static const int [6]

skymins = [[0.0] * 6, [0.0] * 6] #static float [2][6]
skymaxs = [[0.0] * 6, [0.0] * 6] #static float [2][6]
sky_min, sky_max = 0.0, 0.0 #static float

skyrotate = 0.0 #static float
skyaxis = np.zeros(3, dtype=np.float32) #static vec3_t
sky_images = [None] * 6 #static gl3image_t* [6]

# 3dstudio environment map names
suf = ["rt", "bk", "lf", "ft", "up", "dn"] #static const char* [6]

skyclip = np.array([ #vec3_t [6]
	[1, 1, 0],
	[1, -1, 0],
	[0, -1, 1],
	[0, 1, 1],
	[1, 0, 1],
	[-1, 0, 1]
], dtype=np.float32)
c_sky = 0 #int

st_to_vec = [ #int [6][3]
	[3, -1, 2],
	[-3, 1, 2],

	[1, 3, 2],
	[-1, -3, 2],

	[-2, -1, 3], # 0 degrees yaw, look straight up
	[2, -1, -3] # look straight down
]

vec_to_st = [ #int [6][3]
	[-2, 3, 1],
	[2, 3, -1],

	[1, 3, 2],
	[-1, 3, -2],

	[-2, -1, 3],
	[-2, 1, -3]
]


def GL3_SetSky(name, rotate, axis): #const char *, float, vec3_t

	global skyrotate, sky_min, sky_max

	#char	skyname[MAX_QPATH];
	#int		i;

	skyname = name[:shared.MAX_QPATH - 1] # Q_strlcpy(skyname, name, sizeof(skyname))
	skyrotate = rotate
	shared.VectorCopy(axis, skyaxis)

	for i in range(6):

		#gl3image_t	*image;

		image = files_stb.GetSkyImage(skyname, suf[i],
			gl3_main.r_palettedtexture.value, gl3_image.GL3_FindImage)

		if image is None:

			clientserver.Com_Printf("{}: can't load {}:{} sky\n".format(
				"GL3_SetSky", skyname, suf[i]))
			image = gl3_misc.gl3_notexture

		sky_images[i] = image

	sky_min = 1.0 / 512
	sky_max = 511.0 / 512

def DrawSkyPolygon(nump, vecs): #int, vec3_t

	global c_sky

	#int i, j;
	#vec3_t v, av;
	#float s, t, dv;
	#int axis;
	#float *vp;

	c_sky += 1

	# decide which face it maps to
	v = vecs[:nump].sum(axis=0) # VectorCopy(vec3_origin, v); then VectorAdd(vp, v, v) for each vertex

	av = np.abs(v)

	if (av[0] > av[1]) and (av[0] > av[2]):

		if v[0] < 0:

			axis = 1

		else:

			axis = 0

	elif (av[1] > av[2]) and (av[1] > av[0]):

		if v[1] < 0:

			axis = 3

		else:

			axis = 2

	else:

		if v[2] < 0:

			axis = 5

		else:

			axis = 4

	# project new texture coords
	for i in range(nump):

		vp = vecs[i]

		j = vec_to_st[axis][2]

		if j > 0:

			dv = vp[j - 1]

		else:

			dv = -vp[-j - 1]

		if dv < 0.001:

			continue # don't divide by zero

		j = vec_to_st[axis][0]

		if j < 0:

			s = -vp[-j - 1] / dv

		else:

			s = vp[j - 1] / dv

		j = vec_to_st[axis][1]

		if j < 0:

			t = -vp[-j - 1] / dv

		else:

			t = vp[j - 1] / dv

		if s < skymins[0][axis]:

			skymins[0][axis] = s

		if t < skymins[1][axis]:

			skymins[1][axis] = t

		if s > skymaxs[0][axis]:

			skymaxs[0][axis] = s

		if t > skymaxs[1][axis]:

			skymaxs[1][axis] = t

def ClipSkyPolygon(nump, vecs, stage): #int, vec3_t, int

	#float *norm;
	#float *v;
	#qboolean front, back;
	#float d, e;
	dists = [0.0] * MAX_CLIP_VERTS #float [MAX_CLIP_VERTS]
	sides = [0] * MAX_CLIP_VERTS #int [MAX_CLIP_VERTS]
	newv = [np.zeros((MAX_CLIP_VERTS, 3), dtype=np.float32), np.zeros((MAX_CLIP_VERTS, 3), dtype=np.float32)] #vec3_t [2][MAX_CLIP_VERTS]
	newc = [0, 0] #int [2]
	#int i, j;

	if nump > MAX_CLIP_VERTS - 2:

		clientserver.Com_Error(shared.ERR_DROP, "R_ClipSkyPolygon: MAX_CLIP_VERTS")

	if stage == 6:

		# fully clipped, so draw it
		DrawSkyPolygon(nump, vecs)
		return

	front = back = False
	norm = skyclip[stage]

	for i in range(nump):

		d = shared.DotProduct(vecs[i], norm)

		if d > ON_EPSILON:

			front = True
			sides[i] = ref_shared.SIDE_FRONT

		elif d < -ON_EPSILON:

			back = True
			sides[i] = ref_shared.SIDE_BACK

		else:

			sides[i] = ref_shared.SIDE_ON

		dists[i] = d

	if not front or not back:

		# not clipped
		ClipSkyPolygon(nump, vecs, stage + 1)
		return

	# clip it
	sides[nump] = sides[0]
	dists[nump] = dists[0]
	vecs = np.vstack((vecs[:nump], vecs[0:1])) # VectorCopy(vecs, (vecs + (i * 3)))
	newc[0] = newc[1] = 0

	for i in range(nump):

		v = vecs[i]

		if sides[i] == ref_shared.SIDE_FRONT:
			newv[0][newc[0]] = v
			newc[0] += 1
		elif sides[i] == ref_shared.SIDE_BACK:
			newv[1][newc[1]] = v
			newc[1] += 1
		elif sides[i] == ref_shared.SIDE_ON:
			newv[0][newc[0]] = v
			newc[0] += 1
			newv[1][newc[1]] = v
			newc[1] += 1

		if ((sides[i] == ref_shared.SIDE_ON) or
			(sides[i + 1] == ref_shared.SIDE_ON) or
			(sides[i + 1] == sides[i])):

			continue

		d = dists[i] / (dists[i] - dists[i + 1])

		for j in range(3):

			e = v[j] + d * (vecs[i + 1][j] - v[j])
			newv[0][newc[0]][j] = e
			newv[1][newc[1]][j] = e

		newc[0] += 1
		newc[1] += 1

	# continue
	ClipSkyPolygon(newc[0], newv[0], stage + 1)
	ClipSkyPolygon(newc[1], newv[1], stage + 1)

def GL3_AddSkySurface(fa): #msurface_t *

	#int i;
	#vec3_t verts[MAX_CLIP_VERTS];
	#glpoly_t *p;

	# calculate vertex values for sky box
	for p in fa.polys:

		verts = (p.vertices["pos"][:p.numverts] - gl3_main.gl3_origin).astype(np.float32) # VectorSubtract(p->vertices[i].pos, gl3_origin, verts[i])

		ClipSkyPolygon(p.numverts, verts, 0)

def GL3_ClearSkyBox(): #void

	for i in range(6):

		skymins[0][i] = skymins[1][i] = 9999
		skymaxs[0][i] = skymaxs[1][i] = -9999

def MakeSkyVec(s, t, axis, vert): #float, float, int, gl3_3D_vtx_t*

	v = np.zeros(3, dtype=np.float32) #vec3_t
	b = np.zeros(3, dtype=np.float32) #vec3_t
	#int j, k;

	dist = 2300.0 if (gl3_main.r_farsee.value == 0) else 4096.0

	b[0] = s * dist
	b[1] = t * dist
	b[2] = dist

	for j in range(3):

		k = st_to_vec[axis][j]

		if k < 0:

			v[j] = -b[-k - 1]

		else:

			v[j] = b[k - 1]

	# avoid bilerp seam
	s = (s + 1) * 0.5
	t = (t + 1) * 0.5

	if s < sky_min:

		s = sky_min

	elif s > sky_max:

		s = sky_max

	if t < sky_min:

		t = sky_min

	elif t > sky_max:

		t = sky_max

	t = 1.0 - t

	vert["pos"] = v

	vert["texCoord"] = (s, t)

	vert["lmTexCoord"] = (0.0, 0.0)

def GL3_DrawSkyBox(): #void

	#int i;

	if skyrotate:

		# check for no sky at all
		i = 0
		while i < 6:

			if ((skymins[0][i] < skymaxs[0][i]) and
			    (skymins[1][i] < skymaxs[1][i])):

				break

			i += 1

		if i == 6:

			return # nothing visible

	drawCmd = local.GL3_CreateDrawCmd()

	# glPushMatrix();

	# glTranslatef(gl3_origin[0], gl3_origin[1], gl3_origin[2]);
	transl = hmm.HMM_Vec3(gl3_main.gl3_origin[0], gl3_main.gl3_origin[1], gl3_main.gl3_origin[2])
	modMVmat = hmm.HMM_Translate(transl)
	if skyrotate != 0.0:

		# glRotatef(r_newrefdef.time * skyrotate, skyaxis[0], skyaxis[1], skyaxis[2]);
		rotAxis = hmm.HMM_Vec3(skyaxis[0], skyaxis[1], skyaxis[2])
		modMVmat = hmm.HMM_MultiplyMat4(modMVmat, hmm.HMM_Rotate(gl3_main.r_newrefdef.time * skyrotate, rotAxis))

	gl3_main.GL3_SetDrawCmdTransMatrix(drawCmd, modMVmat)

	local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3Dsky)

	# TODO: this could all be done in one drawcall.. but.. whatever, it's <= 6 drawcalls/frame
	#       also, they use different textures..

	for i in range(6):

		skyVertices = np.zeros(4, dtype=model.gl3_3D_vtx_t) #gl3_3D_vtx_t [4]

		if skyrotate != 0.0:

			skymins[0][i] = -1
			skymins[1][i] = -1
			skymaxs[0][i] = 1
			skymaxs[1][i] = 1

		if ((skymins[0][i] >= skymaxs[0][i]) or
		    (skymins[1][i] >= skymaxs[1][i])):

			continue

		drawCmd.texnum = sky_images[skytexorder[i]].texnum

		MakeSkyVec( skymins [ 0 ] [ i ], skymins [ 1 ] [ i ], i, skyVertices[0] )
		MakeSkyVec( skymins [ 0 ] [ i ], skymaxs [ 1 ] [ i ], i, skyVertices[1] )
		MakeSkyVec( skymaxs [ 0 ] [ i ], skymaxs [ 1 ] [ i ], i, skyVertices[2] )
		MakeSkyVec( skymaxs [ 0 ] [ i ], skymins [ 1 ] [ i ], i, skyVertices[3] )

		gl3_main.GL3_Add3DdrawCmdToBatch(skyVertices, 4, GL.GL_TRIANGLE_FAN, drawCmd)

	# glPopMatrix();
