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
 * Mesh handling
 *
 * =======================================================================
"""
from __future__ import annotations

import math
import os
import re
import numpy as np
import OpenGL.GL as GL
from client import ref
from client.refresh.gl1 import gl1_main, gl1_image, gl1_light, gl1_buffer
from common import clientserver
from common import movemsg
from q2data import md2 as q2md2
from common.header import shared
from common.shared import shared as shared_c

"""
#include "header/local.h"
"""

NUMVERTEXNORMALS = 162
SHADEDOT_QUANT = 16

# float r_avertexnormals[NUMVERTEXNORMALS][3] = { #include "../constants/anorms.h" };
# Q2PORT: the same table as common's bytedirs, which is used directly (it can't
# be aliased here because common is still loading when this module is imported)

# precalculated dot products for quantized angles
def _LoadAnormtab(): # Q2PORT: float r_avertexnormal_dots[SHADEDOT_QUANT][256] = { #include "../constants/anormtab.h" };
	text = open(os.path.join(os.path.dirname(__file__), "anormtab.h")).read()
	text = text[text.index("{"):] # skip the licence comment
	values = [float(x) for x in re.findall(r"\d+\.\d+", text)]
	return np.array(values, dtype=np.float32).reshape((SHADEDOT_QUANT, 256))

r_avertexnormal_dots = _LoadAnormtab() #float [SHADEDOT_QUANT][256]

#typedef float vec4_t[4];
s_lerped = np.zeros((q2md2.MAX_VERTS, 4), dtype=np.float32) #static vec4_t [MAX_VERTS]
shadevector = np.zeros((3,), dtype=np.float32) #vec3_t
shadelight = np.zeros((3,), dtype=np.float32) #float [3]
shadedots = r_avertexnormal_dots[0] #float *
#extern vec3_t lightspot;

def R_LerpVerts(currententity, nverts, v, ov, verts, lerp, move, frontv, backv): #entity_t *, int, dtrivertx_t *, dtrivertx_t *, dtrivertx_t *, float *, float[3], float[3], float[3] (static)

	#int i;

	# Q2PORT: v, ov and verts are (nverts, 4) byte arrays of dtrivertx_t
	# (v[0], v[1], v[2], lightnormalindex); the per vertex loop is one numpy
	# expression with the same arithmetic
	if (currententity.flags &
		(shared.RF_SHELL_RED | shared.RF_SHELL_GREEN |
		 shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE |
		 shared.RF_SHELL_HALF_DAM)):

		normal = movemsg.bytedirs[verts[:nverts, 3]] # r_avertexnormals[verts[i].lightnormalindex]

		lerp[:nverts, :3] = move + ov[:nverts, :3] * backv + v[:nverts, :3] * frontv + \
				  normal * ref.POWERSUIT_SCALE

	else:

		lerp[:nverts, :3] = move + ov[:nverts, :3] * backv + v[:nverts, :3] * frontv

def R_AliasGLCmdsTris(counts): # Q2PORT: list of int (returns numpy array of GLushort)

	# Q2PORT: the triangle index list R_SetBufferIndices() builds for each fan
	# (count < 0) and strip (count > 0) of a model, numbered from the model's
	# first vertex; for R_DrawAliasGLCmds()
	tris = []
	first = 0

	for count in counts:

		if count < 0:

			count = -count

			for i in range(count-2):
				tris.extend((first, first+i+1, first+i+2))

		else:

			for i in range(count-2):
				if i % 2 == 0:
					tris.extend((first+i, first+i+1, first+i+2))
				else:
					# backwards order
					tris.extend((first+i+2, first+i+1, first+i))

		first += count

	return np.array(tris, dtype=np.uint16)

def R_DrawAliasGLCmds(currententity, paliashdr, verts, alpha): # Q2PORT: entity_t *, dmdl_t *, dtrivertx_t *, float (returns qboolean)

	# Q2PORT: the glcmds loop at the end of R_DrawAliasFrameLerp(), for all the
	# fans and strips of the model at once with numpy: the per vertex loop in
	# python was the slowest part of the renderer. The vertices, texture
	# coordinates and colours stored are the same, in the same order (the
	# colour maths is in numpy float32, the C's float). Returns False if the
	# model doesn't fit the buffer, storing nothing; the C loop draws it then.

	if paliashdr.glcmds_tris is None:

		paliashdr.glcmds_tris = R_AliasGLCmdsTris(paliashdr.glcmds_counts)

	xyz = paliashdr.glcmds_xyz # index_xyz of each vertex
	num = len(xyz)

	if not gl1_buffer.R_SetBufferIndicesTris(paliashdr.glcmds_tris, num):

		return False

	gl_buf = gl1_buffer.gl_buf

	# GLBUFFER_VERTEX(lerp[index_xyz][0], lerp[index_xyz][1], lerp[index_xyz][2])
	gl_buf.vtx[gl_buf.vt:gl_buf.vt + num * 3] = s_lerped[xyz, :3].ravel()
	gl_buf.vt += num * 3

	if (currententity.flags &
		(shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE)):

		# the same colour for every vertex
		idx = [0, 0, 0]

		for i in range(3):

			idx[i] = int(shadelight[i] * 255)
			idx[i] = shared.Q_clamp(idx[i], 0, 255)

		rgb = np.array(idx, dtype=np.intp)

	else:

		# GLBUFFER_SINGLETEX(tex[0], tex[1]), texture coordinates come from the draw list
		gl_buf.tex[0][gl_buf.tx:gl_buf.tx + num * 2] = paliashdr.glcmds_st.ravel()
		gl_buf.tx += num * 2

		# normals and vertexes come from the frame list
		l = shadedots[verts[xyz, 3]]

		# idx[i] = (int)(l * shadelight[i] * 255), clamped to 0..255
		rgb = (l[:, None] * shadelight * 255).astype(np.intp)
		np.clip(rgb, 0, 255, out=rgb)

	if gl1_main.gl_state.minlight_set:

		rgb = np.frombuffer(gl1_light.minlight, dtype=np.uint8)[rgb]

	# GLBUFFER_COLOR(idx[0], idx[1], idx[2], alpha * 255)
	clr = gl_buf.clr[gl_buf.cl:gl_buf.cl + num * 4].reshape((num, 4))
	clr[:, :3] = np.frombuffer(gl1_image.gammatable, dtype=np.uint8)[rgb]
	clr[:, 3] = int(alpha * 255) & 0xff
	gl_buf.cl += num * 4

	return True

"""
 * Interpolates between two frames and origins
"""
def R_DrawAliasFrameLerp(currententity, paliashdr, backlerp): #entity_t *, dmdl_t *, float (static)

	"""
	daliasframe_t *frame, *oldframe;
	dtrivertx_t *v, *ov, *verts;
	int *order;
	int count, i, index_xyz;
	float tex[2], frontlerp, l, alpha;
	vec3_t move, delta, vectors[3];
	vec3_t frontv, backv;
	float *lerp;
	"""
	move = np.zeros((3,), dtype=np.float32)
	delta = np.zeros((3,), dtype=np.float32)
	vectors = [np.zeros((3,), dtype=np.float32) for _ in range(3)]
	frontv = np.zeros((3,), dtype=np.float32)
	backv = np.zeros((3,), dtype=np.float32)

	frame = paliashdr.frames[currententity.frame]
	verts = v = frame.verts

	oldframe = paliashdr.frames[currententity.oldframe]
	ov = oldframe.verts

	order = paliashdr.glcmds # (int *)((byte *)paliashdr + paliashdr->ofs_glcmds)
	o = 0 # Q2PORT: an index into order

	if currententity.flags & shared.RF_TRANSLUCENT:

		alpha = currententity.alpha

	else:

		alpha = 1.0

	frontlerp = 1.0 - backlerp

	# move should be the delta back to the previous frame * backlerp
	shared.VectorSubtract(currententity.oldorigin, currententity.origin, delta)
	shared_c.AngleVectors(currententity.angles, vectors[0], vectors[1], vectors[2])

	move[0] = shared.DotProduct(delta, vectors[0]) # forward
	move[1] = -shared.DotProduct(delta, vectors[1]) # left
	move[2] = shared.DotProduct(delta, vectors[2]) # up

	shared.VectorAdd(move, oldframe.translate, move)

	for i in range(3):

		move[i] = backlerp * move[i] + frontlerp * frame.translate[i]

	for i in range(3):

		frontv[i] = frontlerp * frame.scale[i]
		backv[i] = backlerp * oldframe.scale[i]

	lerp = s_lerped # s_lerped[0]

	R_LerpVerts(currententity, paliashdr.num_xyz, v, ov, verts, lerp, move, frontv, backv)

	# Q2PORT: the loop below for the whole model with numpy (much faster)
	if R_DrawAliasGLCmds(currententity, paliashdr, verts, alpha):

		return

	lerped = s_lerped.tolist() # Q2PORT: python floats for the per vertex loops below
	lightnormalindex = verts[:, 3].tolist()
	shadedots_l = shadedots.tolist() # Q2PORT: shadedots and shadelight as python floats too,
	shadelight_l = shadelight.tolist() # numpy scalar arithmetic per vertex is slow

	while True:

		#int idx[3];
		idx = [0, 0, 0]

		# get the vertex count and primitive type
		count = order[o]
		o += 1

		if not count:

			break # done

		if count < 0:

			count = -count
			gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_FAN, count)

		else:

			gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_STRIP, count)

		if (currententity.flags &
			(shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE)):

			while True:

				index_xyz = order[o + 2]
				o += 3

				gl1_buffer.GLBUFFER_VERTEX(lerped[index_xyz][0],
					lerped[index_xyz][1], lerped[index_xyz][2])

				for i in range(3):

					idx[i] = int(shadelight_l[i] * 255)
					idx[i] = shared.Q_clamp(idx[i], 0, 255)

				if gl1_main.gl_state.minlight_set:

					for i in range(3):

						idx[i] = gl1_light.minlight[idx[i]]

				gl1_buffer.GLBUFFER_COLOR(idx[0], idx[1], idx[2], int(alpha * 255))

				count -= 1
				if not count: # while (--count);
					break

		else:

			while True:

				# texture coordinates come from the draw list
				tex0 = order[o + 0] # ((float *)order)[0]
				tex1 = order[o + 1]

				index_xyz = order[o + 2]
				o += 3

				# normals and vertexes come from the frame list
				l = shadedots_l[lightnormalindex[index_xyz]]

				gl1_buffer.GLBUFFER_VERTEX(lerped[index_xyz][0],
					lerped[index_xyz][1], lerped[index_xyz][2])

				gl1_buffer.GLBUFFER_SINGLETEX(tex0, tex1)

				for i in range(3):

					idx[i] = int(l * shadelight_l[i] * 255)
					idx[i] = shared.Q_clamp(idx[i], 0, 255)

				if gl1_main.gl_state.minlight_set:

					for i in range(3):

						idx[i] = gl1_light.minlight[idx[i]]

				gl1_buffer.GLBUFFER_COLOR(idx[0], idx[1], idx[2], int(alpha * 255))

				count -= 1
				if not count: # while (--count);
					break

def R_DrawAliasShadow(currententity, paliashdr, posenum): #entity_t *, dmdl_t *, int (static)

	# Don't do stencil test on unsupported stereo modes
	stencilt = ( gl1_main.gl_state.stencil and gl1_main.gl1_stencilshadow.value and
		( gl1_main.gl_state.stereo_mode < gl1_main.STEREO_MODE_ROW_INTERLEAVED
		or gl1_main.gl_state.stereo_mode > gl1_main.STEREO_MODE_PIXEL_INTERLEAVED ) ) #const qboolean

	#int *order;
	#vec3_t point;
	#float height = 0, lheight;
	#int count;
	point = [0.0, 0.0, 0.0]

	lheight = currententity.origin[2] - gl1_light.lightspot[2]
	order = paliashdr.glcmds # (int *)((byte *)paliashdr + paliashdr->ofs_glcmds)
	o = 0 # Q2PORT: an index into order
	height = -lheight + 0.1

	gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_shadow, 0, 0, 0, 1)

	# stencilbuffer shadows
	if stencilt:

		GL.glEnable(GL.GL_STENCIL_TEST)
		GL.glStencilFunc(GL.GL_EQUAL, 1, 2)
		GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_INCR)

	lerped = s_lerped.tolist() # Q2PORT: python floats for the per vertex loop below

	while True:

		# get the vertex count and primitive type
		count = order[o]
		o += 1

		if not count:

			break # done

		if count < 0:

			count = -count
			gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_FAN, count)

		else:

			gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_STRIP, count)

		while True:

			# normals and vertexes come from the frame list
			point[:] = lerped[order[o + 2]][:3] # memcpy(point, s_lerped[order[2]], sizeof(point));

			point[0] -= shadevector[0] * (point[2] + lheight)
			point[1] -= shadevector[1] * (point[2] + lheight)
			point[2] = height

			gl1_buffer.GLBUFFER_VERTEX( point[0], point[1], point[2] )

			o += 3

			count -= 1
			if not count: # while (--count);
				break

	gl1_buffer.R_ApplyGLBuffer()

	# stencilbuffer shadows
	if stencilt:

		GL.glDisable(GL.GL_STENCIL_TEST)

# Q2PORT: for R_CullAliasModel(), which corners of the box take mins (else
# maxs) on each axis: corner i, axis j is mins when i & (1 << j)
BBOX_CORNER_MINS = ((np.arange(8)[:, None] >> np.arange(3)) & 1).astype(bool)

def R_CullAliasModel(currentmodel, bbox, e): #const model_t *, vec3_t [8], entity_t * (returns qboolean) (static)

	"""
	int i;
	vec3_t mins, maxs;
	dmdl_t *paliashdr;
	vec3_t vectors[3];
	vec3_t thismins, oldmins, thismaxs, oldmaxs;
	daliasframe_t *pframe, *poldframe;
	vec3_t angles;
	"""
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)
	vectors = [np.zeros((3,), dtype=np.float32) for _ in range(3)]

	paliashdr = currentmodel.extradata

	if (e.frame >= paliashdr.num_frames) or (e.frame < 0):

		clientserver.Com_DPrintf("{} {}: no such frame {}\n".format("R_CullAliasModel",
				currentmodel.name, e.frame))
		e.frame = 0

	if (e.oldframe >= paliashdr.num_frames) or (e.oldframe < 0):

		clientserver.Com_DPrintf("{} {}: no such oldframe {}\n".format("R_CullAliasModel",
				currentmodel.name, e.oldframe))
		e.oldframe = 0

	pframe = paliashdr.frames[e.frame]

	poldframe = paliashdr.frames[e.oldframe]

	# compute axially aligned mins and maxs
	if pframe is poldframe:

		for i in range(3):

			mins[i] = pframe.translate[i]
			maxs[i] = mins[i] + pframe.scale[i] * 255

	else:

		for i in range(3):

			thismins = pframe.translate[i]
			thismaxs = thismins + pframe.scale[i] * 255

			oldmins = poldframe.translate[i]
			oldmaxs = oldmins + poldframe.scale[i] * 255

			if thismins < oldmins:

				mins[i] = thismins

			else:

				mins[i] = oldmins

			if thismaxs > oldmaxs:

				maxs[i] = thismaxs

			else:

				maxs[i] = oldmaxs

	# Q2PORT: the three loops over the 8 corners of the box below are done with
	# numpy on the (8, 3) bbox array at once, rather than corner by corner with
	# DotProduct() (slow in python, this runs for every model every frame).

	# compute a full bounding box
	# Q2PORT: for i in range(8): bbox[i][j] = mins[j] if i & (1 << j) else maxs[j]
	bbox[:] = np.where(BBOX_CORNER_MINS, mins, maxs)

	# rotate the bounding box
	angles = e.angles.copy() # VectorCopy(e->angles, angles);
	angles[gl1_main.YAW] = -angles[gl1_main.YAW]
	shared_c.AngleVectors(angles, vectors[0], vectors[1], vectors[2])

	# Q2PORT: for each corner tmp, bbox[i] = (DotProduct(vectors[0], tmp),
	# -DotProduct(vectors[1], tmp), DotProduct(vectors[2], tmp)) + e->origin
	bbox[:] = bbox @ np.array((vectors[0], -vectors[1], vectors[2])).T + e.origin

	#int p, f, aggregatemask = ~0;
	# Q2PORT: corner p is outside plane f when DotProduct(frustum[f].normal,
	# bbox[p]) - frustum[f].dist < 0; the model is culled when all 8 corners
	# are outside the same plane (the C's aggregatemask of the corners' masks)
	frustum = gl1_main.frustum[0:4]
	dp = bbox @ np.array([f.normal for f in frustum]).T # (8, 4)
	mask = (dp - np.array([f.dist for f in frustum], dtype=np.float32)) < 0
	aggregatemask = mask.all(axis=0)

	if aggregatemask.any():

		return True

	return False

def R_DrawAliasModel(currententity, currentmodel): #entity_t *, const model_t *

	global shadedots

	"""
	int i;
	dmdl_t *paliashdr;
	float an;
	vec3_t bbox[8];
	image_t *skin;
	"""
	bbox = np.zeros((8, 3), dtype=np.float32)

	if not (currententity.flags & shared.RF_WEAPONMODEL):

		if R_CullAliasModel(currentmodel, bbox, currententity):

			return

	if currententity.flags & shared.RF_WEAPONMODEL:

		if gl1_main.gl_lefthand.value == 2:

			return

	paliashdr = currentmodel.extradata

	# get lighting information
	if (currententity.flags &
		(shared.RF_SHELL_HALF_DAM | shared.RF_SHELL_GREEN | shared.RF_SHELL_RED |
		 shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE)):

		shared.VectorClear(shadelight)

		if currententity.flags & shared.RF_SHELL_HALF_DAM:

			shadelight[0] = 0.56
			shadelight[1] = 0.59
			shadelight[2] = 0.45

		if currententity.flags & shared.RF_SHELL_DOUBLE:

			shadelight[0] = 0.9
			shadelight[1] = 0.7

		if currententity.flags & shared.RF_SHELL_RED:

			shadelight[0] = 1.0

		if currententity.flags & shared.RF_SHELL_GREEN:

			shadelight[1] = 1.0

		if currententity.flags & shared.RF_SHELL_BLUE:

			shadelight[2] = 1.0

	elif currententity.flags & shared.RF_FULLBRIGHT:

		for i in range(3):

			shadelight[i] = 1.0

	else:

		gl1_light.R_LightPoint(currententity, currententity.origin, shadelight)

		# player lighting hack for communication back to server
		if currententity.flags & shared.RF_WEAPONMODEL:

			# pick the greatest component, which should be
			# the same as the mono value returned by software
			if shadelight[0] > shadelight[1]:

				if shadelight[0] > shadelight[2]:

					gl1_main.r_lightlevel.value = 150 * shadelight[0]

				else:

					gl1_main.r_lightlevel.value = 150 * shadelight[2]

			else:

				if shadelight[1] > shadelight[2]:

					gl1_main.r_lightlevel.value = 150 * shadelight[1]

				else:

					gl1_main.r_lightlevel.value = 150 * shadelight[2]

	if currententity.flags & shared.RF_MINLIGHT:

		for i in range(3):

			if shadelight[i] > 0.1:

				break

		else: # i == 3

			shadelight[0] = 0.1
			shadelight[1] = 0.1
			shadelight[2] = 0.1

	if currententity.flags & shared.RF_GLOW:

		# bonus items will pulse with time
		#float scale;
		#float min;

		scale = 0.1 * math.sin(gl1_main.r_newrefdef.time * 7)

		for i in range(3):

			min_ = shadelight[i] * 0.8
			shadelight[i] += scale

			if shadelight[i] < min_:

				shadelight[i] = min_

	# Apply gl1_overbrightbits to the mesh. If we don't do this they will appear slightly dimmer relative to walls.
	if gl1_main.gl1_overbrightbits.value:

		for i in range(3):

			shadelight[i] *= gl1_main.gl1_overbrightbits.value

	# ir goggles color override
	if (gl1_main.r_newrefdef.rdflags & shared.RDF_IRGOGGLES and currententity.flags &
		shared.RF_IR_VISIBLE):

		shadelight[0] = 1.0
		shadelight[1] = 0.0
		shadelight[2] = 0.0

	shadedots = r_avertexnormal_dots[(int(currententity.angles[1] *
				(SHADEDOT_QUANT / 360.0))) & (SHADEDOT_QUANT - 1)]

	an = currententity.angles[1] / 180 * math.pi
	shadevector[0] = math.cos(-an)
	shadevector[1] = math.sin(-an)
	shadevector[2] = 1
	shared_c.VectorNormalize(shadevector)

	# locate the proper data
	gl1_main.c_alias_polys += paliashdr.num_tris

	GL.glPushMatrix()
	currententity.angles[gl1_main.PITCH] = -currententity.angles[gl1_main.PITCH]
	gl1_main.R_RotateForEntity(currententity)
	currententity.angles[gl1_main.PITCH] = -currententity.angles[gl1_main.PITCH]

	# select skin
	if currententity.skin:

		skin = currententity.skin # custom player skin

	else:

		if currententity.skinnum >= q2md2.MAX_SKINS:

			skin = currentmodel.skins[0]

		else:

			skin = currentmodel.skins[currententity.skinnum]

			if not skin:

				skin = currentmodel.skins[0]

	if not skin:

		skin = gl1_main.r_notexture # fallback...

	if ((currententity.frame >= paliashdr.num_frames) or
		(currententity.frame < 0)):

		clientserver.Com_DPrintf("{} {}: no such frame {}\n".format("R_DrawAliasModel",
				currentmodel.name, currententity.frame))
		currententity.frame = 0
		currententity.oldframe = 0

	if ((currententity.oldframe >= paliashdr.num_frames) or
		(currententity.oldframe < 0)):

		clientserver.Com_DPrintf("{} {}: no such oldframe {}\n".format("R_DrawAliasModel",
				currentmodel.name, currententity.oldframe))
		currententity.frame = 0
		currententity.oldframe = 0

	if not gl1_main.r_lerpmodels.value:

		currententity.backlerp = 0

	gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_alias, skin.texnum, 0, currententity.flags, 1)
	R_DrawAliasFrameLerp(currententity, paliashdr, currententity.backlerp)
	gl1_buffer.R_ApplyGLBuffer()

	gl1_image.R_TexEnv(GL.GL_REPLACE)
	GL.glShadeModel(GL.GL_FLAT)

	GL.glPopMatrix()

	if gl1_main.gl_showbbox.value:

		GL.glDisable(GL.GL_CULL_FACE)
		GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
		GL.glDisable(GL.GL_TEXTURE_2D)

		GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
		GL.glVertexPointer(3, GL.GL_FLOAT, 0, bbox)
		GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 8)
		GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

		GL.glEnable(GL.GL_TEXTURE_2D)
		GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
		GL.glEnable(GL.GL_CULL_FACE)

	if (gl1_main.gl_shadows.value and
		not (currententity.flags & (shared.RF_TRANSLUCENT | shared.RF_WEAPONMODEL | shared.RF_NOSHADOW))):

		GL.glPushMatrix()

		# don't rotate shadows on ungodly axes
		GL.glTranslatef(currententity.origin[0], currententity.origin[1], currententity.origin[2])
		GL.glRotatef(currententity.angles[1], 0, 0, 1)

		GL.glDisable(GL.GL_TEXTURE_2D)
		GL.glEnable(GL.GL_BLEND)
		GL.glColor4f(0, 0, 0, 0.5)
		R_DrawAliasShadow(currententity, paliashdr, currententity.frame)
		GL.glEnable(GL.GL_TEXTURE_2D)
		GL.glDisable(GL.GL_BLEND)
		GL.glPopMatrix()

	GL.glColor4f(1, 1, 1, 1)
