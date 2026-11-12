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
 * Warps. Used on water surfaces and for skybox rotation.
 *
 * =======================================================================
"""
from __future__ import annotations

import math
import os
import re
import numpy as np
import OpenGL.GL as GL
from client.refresh.gl1 import gl1_main, gl1_image, gl1_buffer
from client.refresh.gl1.header import model
from client.refresh import ref_shared
from client.refresh.files import stb as files_stb
from common import clientserver
from common.header import shared
from common.shared import shared as shared_c

#include "header/local.h"

TURBSCALE = (256.0 / (2 * math.pi))
SUBDIVIDE_SIZE = 64
ON_EPSILON = 0.1 # point on plane side epsilon
MAX_CLIP_VERTS = 64
MAX_SUBDIVIDE_VERTS = 60

skyrotate = 0.0 #float
skyaxis = np.zeros((3,), dtype=np.float32) #vec3_t
sky_images = [None] * 6 #image_t *[6]
warpface = None #msurface_t *
skytexorder = [0, 2, 1, 3, 4, 5] #int [6]

vtx_sky = np.zeros((12,), dtype=np.float32) #GLfloat [12]
tex_sky = np.zeros((8,), dtype=np.float32) #GLfloat [8]
index_vtx = 0 #unsigned int
index_tex = 0 #unsigned int

# 3dstudio environment map names
suf = ["rt", "bk", "lf", "ft", "up", "dn"] #char *[6]

def _LoadTurbsin ():
	# Q2PORT: float r_turbsin[] = { #include "../constants/warpsin.h" };
	text = open(os.path.join(os.path.dirname(__file__), "warpsin.h")).read()
	text = text[text.index("*/")+2:] # skip the licence comment
	return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", text)]

r_turbsin = _LoadTurbsin() #float[]

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

skymins = np.zeros((2, 6), dtype=np.float32) #float [2][6]
skymaxs = np.zeros((2, 6), dtype=np.float32) #float [2][6]
sky_min, sky_max = 0.0, 0.0 #float

def R_BoundPoly(numverts: int, verts: np.ndarray, mins: np.ndarray, maxs: np.ndarray): #int, float * (array [numverts][3]), vec3_t, vec3_t

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

def R_SubdividePolygon(numverts: int, verts: np.ndarray): #int, float * (array [numverts][3])

	"""
	int i, j, k;
	vec3_t mins, maxs;
	float m;
	float *v;
	vec3_t front[64], back[64];
	int f, b;
	float dist[64];
	float frac;
	glpoly_t *poly;
	float s, t;
	vec3_t total;
	float total_s, total_t;
	"""
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)

	if numverts > MAX_SUBDIVIDE_VERTS:

		clientserver.Com_Error(shared.ERR_DROP, "{}: numverts = {}".format("R_SubdividePolygon", numverts))

	R_BoundPoly(numverts, verts, mins, maxs)

	for i in range(3):

		m = (mins[i] + maxs[i]) * 0.5
		m = SUBDIVIDE_SIZE * math.floor(m / SUBDIVIDE_SIZE + 0.5)

		if maxs[i] - m < 8:

			continue

		if m - mins[i] < 8:

			continue

		# cut it
		dist = [0.0] * 64
		for j in range(numverts):

			dist[j] = verts[j][i] - m

		# wrap cases
		dist[numverts] = dist[0]
		#v -= i; VectorCopy(verts, v); Q2PORT: the wrap around is done with (j + 1) % numverts below

		front = np.zeros((64, 3), dtype=np.float32)
		back = np.zeros((64, 3), dtype=np.float32)
		f = b = 0

		for j in range(numverts):

			v = verts[j]
			vnext = verts[(j + 1) % numverts] # v + 3

			if dist[j] >= 0:

				shared.VectorCopy(v, front[f])
				f += 1

			if dist[j] <= 0:

				shared.VectorCopy(v, back[b])
				b += 1

			if (dist[j] == 0) or (dist[j + 1] == 0):

				continue

			if (dist[j] > 0) != (dist[j + 1] > 0):

				# clip point
				frac = dist[j] / (dist[j] - dist[j + 1])

				for k in range(3):

					front[f][k] = back[b][k] = v[k] + frac * (vnext[k] - v[k])

				f += 1
				b += 1

		R_SubdividePolygon(f, front)
		R_SubdividePolygon(b, back)
		return

	# add a point in the center to help keep warp valid
	poly = model.glpoly_t() # Hunk_Alloc(sizeof(glpoly_t) + ((numverts - 4) + 2) * VERTEXSIZE * sizeof(float));
	poly.verts = np.zeros((numverts + 2, model.VERTEXSIZE), dtype=np.float32)
	warpface.polys.insert(0, poly) # poly->next = warpface->polys; warpface->polys = poly;
	poly.numverts = numverts + 2
	total = np.zeros((3,), dtype=np.float32) # VectorClear(total);
	total_s = 0
	total_t = 0

	for i in range(numverts):

		shared.VectorCopy(verts[i], poly.verts[i + 1][:3])
		s = shared.DotProduct(verts[i], warpface.texinfo.vecs[0])
		t = shared.DotProduct(verts[i], warpface.texinfo.vecs[1])

		total_s += s
		total_t += t
		shared.VectorAdd(total, verts[i], total)

		poly.verts[i + 1][3] = s
		poly.verts[i + 1][4] = t

	shared_c.VectorScale(total, (1.0 / numverts), poly.verts[0][:3])
	poly.verts[0][3] = total_s / numverts
	poly.verts[0][4] = total_t / numverts

	# copy first vertex to last
	poly.verts[numverts + 1] = poly.verts[1] # memcpy(poly->verts[i + 1], poly->verts[1], sizeof(poly->verts[0]));

"""
 * Breaks a polygon up along axial 64 unit
 * boundaries so that turbulent and sky warps
 * can be done reasonably.
"""
def R_SubdivideSurface(loadmodel: model.model_t, fa: model.msurface_t): #model_t *, msurface_t *

	global warpface

	"""
	vec3_t verts[64];
	int numverts;
	int i;
	int lindex;
	float *vec;
	"""
	verts = np.zeros((64, 3), dtype=np.float32)

	warpface = fa

	# convert edges back to a normal polygon
	numverts = 0

	for i in range(fa.numedges):

		lindex = int(loadmodel.surfedges[fa.firstedge + i])

		if lindex > 0:

			vec = loadmodel.vertexes[loadmodel.edges[lindex].v[0]].position

		else:

			vec = loadmodel.vertexes[loadmodel.edges[-lindex].v[1]].position

		shared.VectorCopy(vec, verts[numverts])
		numverts += 1

	R_SubdividePolygon(numverts, verts)

"""
 * Does a water warp on the pre-fragmented glpoly_t chain
"""
def R_EmitWaterPolys(fa: model.msurface_t): #msurface_t *

	"""
	glpoly_t *p, *bp;
	float *v;
	int i, nv;
	float s, t, os, ot;
	float scroll;
	float rdt = r_newrefdef.time;
	"""
	rdt = gl1_main.r_newrefdef.time

	if fa.texinfo.flags & shared.SURF_FLOWING:

		scroll = -64 * ((gl1_main.r_newrefdef.time * 0.5) - int(gl1_main.r_newrefdef.time * 0.5))

	else:

		scroll = 0

	for bp in fa.polys:

		p = bp
		nv = p.numverts
		gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_FAN, nv)

		for v in p.verts[:nv].tolist():

			os = v[3]
			ot = v[4]

			s = os + r_turbsin[int((ot * 0.125 + rdt) * TURBSCALE) & 255] + scroll
			t = ot + r_turbsin[int((os * 0.125 + rdt) * TURBSCALE) & 255]

			gl1_buffer.GLBUFFER_VERTEX( v[0], v[1], v[2] )
			gl1_buffer.GLBUFFER_SINGLETEX( s * (1.0 / 64), t * (1.0 / 64) )

def R_DrawSkyPolygon(nump: int, vecs: np.ndarray): #int, vec3_t (array [nump][3])

	global c_sky

	"""
	int i, j;
	vec3_t v, av;
	float s, t, dv;
	int axis;
	float *vp;
	"""

	c_sky += 1

	# decide which face it maps to
	v = np.zeros((3,), dtype=np.float32) # VectorCopy(vec3_origin, v);

	for i in range(nump):

		shared.VectorAdd(vecs[i], v, v)

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

		j = vec_to_st[axis][2]

		if j > 0:

			dv = vecs[i][j - 1]

		else:

			dv = -vecs[i][-j - 1]

		if dv < 0.001:

			continue # don't divide by zero

		j = vec_to_st[axis][0]

		if j < 0:

			s = -vecs[i][-j - 1] / dv

		else:

			s = vecs[i][j - 1] / dv

		j = vec_to_st[axis][1]

		if j < 0:

			t = -vecs[i][-j - 1] / dv

		else:

			t = vecs[i][j - 1] / dv

		if s < skymins[0][axis]:

			skymins[0][axis] = s

		if t < skymins[1][axis]:

			skymins[1][axis] = t

		if s > skymaxs[0][axis]:

			skymaxs[0][axis] = s

		if t > skymaxs[1][axis]:

			skymaxs[1][axis] = t

def R_ClipSkyPolygon(nump: int, vecs: np.ndarray, stage: int): #int, vec3_t (array [nump][3]), int

	"""
	float *norm;
	float *v;
	qboolean front, back;
	float d, e;
	float dists[MAX_CLIP_VERTS];
	int sides[MAX_CLIP_VERTS];
	vec3_t newv[2][MAX_CLIP_VERTS];
	int newc[2];
	int i, j;
	"""

	if nump > MAX_CLIP_VERTS - 2:

		clientserver.Com_Error(shared.ERR_DROP, "{}: MAX_CLIP_VERTS".format("R_ClipSkyPolygon"))

	if stage == 6:

		# fully clipped, so draw it
		R_DrawSkyPolygon(nump, vecs)
		return

	dists = [0.0] * MAX_CLIP_VERTS
	sides = [0] * MAX_CLIP_VERTS

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
		R_ClipSkyPolygon(nump, vecs, stage + 1)
		return

	# clip it
	sides[nump] = sides[0]
	dists[nump] = dists[0]
	#VectorCopy(vecs, (vecs + (i * 3))); Q2PORT: the wrap around is done with (i + 1) % nump below
	newv = np.zeros((2, MAX_CLIP_VERTS, 3), dtype=np.float32) #vec3_t [2][MAX_CLIP_VERTS]
	newc = [0, 0] #int [2]

	for i in range(nump):

		v = vecs[i]
		vnext = vecs[(i + 1) % nump] # v + 3

		if sides[i] == ref_shared.SIDE_FRONT:

			shared.VectorCopy(v, newv[0][newc[0]])
			newc[0] += 1

		elif sides[i] == ref_shared.SIDE_BACK:

			shared.VectorCopy(v, newv[1][newc[1]])
			newc[1] += 1

		elif sides[i] == ref_shared.SIDE_ON:

			shared.VectorCopy(v, newv[0][newc[0]])
			newc[0] += 1
			shared.VectorCopy(v, newv[1][newc[1]])
			newc[1] += 1

		if ((sides[i] == ref_shared.SIDE_ON) or
			(sides[i + 1] == ref_shared.SIDE_ON) or
			(sides[i + 1] == sides[i])):

			continue

		d = dists[i] / (dists[i] - dists[i + 1])

		for j in range(3):

			e = v[j] + d * (vnext[j] - v[j])
			newv[0][newc[0]][j] = e
			newv[1][newc[1]][j] = e

		newc[0] += 1
		newc[1] += 1

	# continue
	R_ClipSkyPolygon(newc[0], newv[0], stage + 1)
	R_ClipSkyPolygon(newc[1], newv[1], stage + 1)

def R_AddSkySurface(fa: model.msurface_t): #msurface_t *

	#int i;
	#vec3_t verts[MAX_CLIP_VERTS];
	#glpoly_t *p;

	# calculate vertex values for sky box
	for p in fa.polys:

		verts = p.verts[:p.numverts, :3] - gl1_main.r_origin # VectorSubtract(p->verts[i], r_origin, verts[i]);

		R_ClipSkyPolygon(p.numverts, verts, 0)

def R_ClearSkyBox(): #void

	#int i;

	for i in range(6):

		skymins[0][i] = skymins[1][i] = 9999
		skymaxs[0][i] = skymaxs[1][i] = -9999

def R_MakeSkyVec(s: float, t: float, axis: int): #float, float, int

	global index_vtx, index_tex

	#vec3_t v, b;
	#int j, k;
	v = [0.0, 0.0, 0.0]
	b = [0.0, 0.0, 0.0]

	if gl1_main.r_farsee.value == 0:

		b[0] = s * 2300
		b[1] = t * 2300
		b[2] = 2300

	else:

		b[0] = s * 4096
		b[1] = t * 4096
		b[2] = 4096

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

	tex_sky[index_tex] = s; index_tex += 1
	tex_sky[index_tex] = t; index_tex += 1

	vtx_sky[index_vtx] = v[ 0 ]; index_vtx += 1
	vtx_sky[index_vtx] = v[ 1 ]; index_vtx += 1
	vtx_sky[index_vtx] = v[ 2 ]; index_vtx += 1

def R_DrawSkyBox(): #void

	global index_vtx, index_tex

	#int i;

	if skyrotate:
		# check for no sky at all
		for i in range(6):

			if ((skymins[0][i] < skymaxs[0][i]) and
				(skymins[1][i] < skymaxs[1][i])):

				break

		else: # i == 6

			return # nothing visible

	GL.glPushMatrix()
	GL.glTranslatef(gl1_main.r_origin[0], gl1_main.r_origin[1], gl1_main.r_origin[2])
	GL.glRotatef(gl1_main.r_newrefdef.time * skyrotate, skyaxis[0], skyaxis[1], skyaxis[2])

	for i in range(6):

		if skyrotate:

			skymins[0][i] = -1
			skymins[1][i] = -1
			skymaxs[0][i] = 1
			skymaxs[1][i] = 1

		if ((skymins[0][i] >= skymaxs[0][i]) or
			(skymins[1][i] >= skymaxs[1][i])):

			continue

		gl1_image.R_Bind(sky_images[skytexorder[i]].texnum)

		GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
		GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )


		index_vtx = 0
		index_tex = 0

		R_MakeSkyVec( float(skymins [ 0 ] [ i ]), float(skymins [ 1 ] [ i ]), i )
		R_MakeSkyVec( float(skymins [ 0 ] [ i ]), float(skymaxs [ 1 ] [ i ]), i )
		R_MakeSkyVec( float(skymaxs [ 0 ] [ i ]), float(skymaxs [ 1 ] [ i ]), i )
		R_MakeSkyVec( float(skymaxs [ 0 ] [ i ]), float(skymins [ 1 ] [ i ]), i )

		GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtx_sky )
		GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex_sky )
		GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

		GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
		GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glPopMatrix()

def RI_SetSky(name: str, rotate: float, axis: np.ndarray): #const char *, float, vec3_t

	global skyrotate, sky_min, sky_max

	#char	skyname[MAX_QPATH];
	#int		i;

	skyname = name[:shared.MAX_QPATH - 1] # Q_strlcpy(skyname, name, sizeof(skyname));
	skyrotate = rotate
	shared.VectorCopy(axis, skyaxis)

	for i in range(6):

		#image_t	*image;

		image = files_stb.GetSkyImage(skyname, suf[i],
			gl1_main.gl_config.palettedtexture, gl1_image.R_FindImage)

		if not image:

			clientserver.Com_Printf("{}: can't load {}:{} sky\n".format(
				"RI_SetSky", skyname, suf[i]))
			image = gl1_main.r_notexture

		sky_images[i] = image

	sky_min = 1.0 / 512
	sky_max = 511.0 / 512
