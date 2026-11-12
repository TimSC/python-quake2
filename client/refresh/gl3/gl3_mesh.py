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
 * MD2 file format
 *
 * =======================================================================
"""

from __future__ import annotations

import ctypes
import math
import os
import re

import numpy as np
import OpenGL.GL as GL

from common import clientserver
from common import movemsg
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model as model_h
from client.refresh.gl3.header import hmm
from client.refresh.gl3 import gl3_draw, gl3_image, gl3_light, gl3_main, gl3_misc, gl3_shaders

#include "header/local.h"

#include "header/DG_dynarr.h"

NUMVERTEXNORMALS = 162
SHADEDOT_QUANT = 16

POWERSUIT_SCALE = 4.0 # vid/header/ref.h

# static float r_avertexnormals[NUMVERTEXNORMALS][3] = { #include "../constants/anorms.h" };
# Q2PORT: the same table as common's bytedirs, used directly
r_avertexnormals = movemsg.bytedirs

def _LoadAnormtab(): # Q2PORT: #include "../constants/anormtab.h", from the copy in gl1/

	text = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "gl1", "anormtab.h")).read()
	text = text[text.index("{"):] # skip the licence comment
	values = [float(x) for x in re.findall(r"\d+\.\d+", text)]
	return np.array(values, dtype=np.float32).reshape((SHADEDOT_QUANT, 256))

# precalculated dot products for quantized angles
r_avertexnormal_dots = _LoadAnormtab() #static float [SHADEDOT_QUANT][256]

#typedef float vec4_t[4];
s_lerped = np.zeros((files_h.MAX_VERTS, 4), dtype=np.float32) #static vec4_t [MAX_VERTS]
#extern vec3_t lightspot;

class gl3_shadowinfo_t(object):

	def __init__(self):

		self.lightspot = np.zeros(3, dtype=np.float32) #vec3_t
		self.shadevector = np.zeros(3, dtype=np.float32) #vec3_t
		self.paliashdr = None #dmdl_t*
		self.entity = None #entity_t*

# DA_TYPEDEF(gl3_shadowinfo_t, ShadowInfoArray_t);
# collect all models casting shadows (each frame)
# to draw shadows last
shadowModels = [] #static ShadowInfoArray_t

# DA_TYPEDEF(gl3_alias_vtx_t, AliasVtxArray_t);
# DA_TYPEDEF(GLushort, UShortArray_t);
# dynamic arrays to batch all the data of a model, so we can render a model in one draw call
# Q2PORT: vtxBuf is a list of gl3_alias_vtx_t numpy arrays, idxBuf a list of ints
vtxBuf = [] #static AliasVtxArray_t
idxBuf = [] #static UShortArray_t

def GL3_ShutdownMeshes(): #void

	vtxBuf.clear() # da_free(vtxBuf)
	idxBuf.clear()

	shadowModels.clear()

def LerpVerts(powerUpEffect, nverts, v, ov, verts, lerp, move, frontv, backv): #qboolean, int, dtrivertx_t *, dtrivertx_t *, dtrivertx_t *, float *, float [3], float [3], float [3]

	# Q2PORT: v, ov and verts are (nverts, 4) byte arrays of dtrivertx_t (v[0..2],
	# lightnormalindex); the C's per-vertex loops are numpy over all of them
	if powerUpEffect:

		normal = r_avertexnormals[verts[:nverts, 3]]

		lerp[:nverts, 0:3] = (move + ov[:nverts, 0:3] * backv + v[:nverts, 0:3] * frontv +
				  normal * POWERSUIT_SCALE)

	else:

		lerp[:nverts, 0:3] = move + ov[:nverts, 0:3] * backv + v[:nverts, 0:3] * frontv

def _AddFanOrStripIndices(type_, count, nextVtxIdx): # Q2PORT: the fan/strip to triangles translation both draw functions share

	# translate triangle fan/strip to just triangle indices
	if type_ == GL.GL_TRIANGLE_FAN:

		for i in range(1, count-1):

			idxBuf.extend((nextVtxIdx, nextVtxIdx+i, nextVtxIdx+i+1))

	else: # triangle strip

		i = 1
		while i < count-2:

			# add two triangles at once, because the vertex order is different
			# for odd vs even triangles
			idxBuf.extend((nextVtxIdx + i-1,
			               nextVtxIdx + i,
			               nextVtxIdx + i+1,

			               nextVtxIdx + i,
			               nextVtxIdx + i+2,
			               nextVtxIdx + i+1))
			i += 2

		# add remaining triangle, if any
		if i < count-1:

			idxBuf.extend((nextVtxIdx + i-1,
			               nextVtxIdx + i,
			               nextVtxIdx + i+1))

"""
 * Interpolates between two frames and origins
"""
def DrawAliasFrameLerp(paliashdr, entity, shadelight): #dmdl_t *, entity_t*, vec3_t

	#GLenum type;
	#float l;
	#daliasframe_t *frame, *oldframe;
	#dtrivertx_t *v, *ov, *verts;
	#int *order;
	#int count;
	#float alpha;
	move = np.zeros(3, dtype=np.float32) #vec3_t
	delta = np.zeros(3, dtype=np.float32) #vec3_t
	vectors = np.zeros((3, 3), dtype=np.float32) #vec3_t [3]
	frontv = np.zeros(3, dtype=np.float32) #vec3_t
	backv = np.zeros(3, dtype=np.float32) #vec3_t
	#int i;
	#int index_xyz;
	backlerp = entity.backlerp
	frontlerp = 1.0 - backlerp
	#float *lerp;
	# draw without texture? used for quad damage effect etc, I think
	colorOnly = 0 != (entity.flags &
			(shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE |
			 shared.RF_SHELL_HALF_DAM))

	# TODO: maybe we could somehow store the non-rotated normal and do the dot in shader?
	shadedots = r_avertexnormal_dots[(int(entity.angles[1] *
				(SHADEDOT_QUANT / 360.0))) & (SHADEDOT_QUANT - 1)]

	frame = paliashdr.frames[entity.frame]
	verts = v = frame.verts

	oldframe = paliashdr.frames[entity.oldframe]
	ov = oldframe.verts

	order = paliashdr.glcmds # (int *)((byte *)paliashdr + paliashdr->ofs_glcmds)
	o = 0 # Q2PORT: an index into the glcmds list, the C's order pointer

	if entity.flags & shared.RF_TRANSLUCENT:

		alpha = entity.alpha * 0.666

	else:

		alpha = 1.0

	if colorOnly:

		local.GL3_UseProgram(gl3_main.gl3state.si3DaliasColor.shaderProgram)

	else:

		local.GL3_UseProgram(gl3_main.gl3state.si3Dalias.shaderProgram)

	if gl3_main.gl3_colorlight.value == 0.0:

		avg = 0.333333 * (shadelight[0]+shadelight[1]+shadelight[2])
		shadelight[0] = shadelight[1] = shadelight[2] = avg

	# move should be the delta back to the previous frame * backlerp
	shared.VectorSubtract(entity.oldorigin, entity.origin, delta)
	shared_c.AngleVectors(entity.angles, vectors[0], vectors[1], vectors[2])

	move[0] = shared.DotProduct(delta, vectors[0]) # forward
	move[1] = -shared.DotProduct(delta, vectors[1]) # left
	move[2] = shared.DotProduct(delta, vectors[2]) # up

	shared.VectorAdd(move, oldframe.translate, move)

	for i in range(3):

		move[i] = backlerp * move[i] + frontlerp * frame.translate[i]

		frontv[i] = frontlerp * frame.scale[i]
		backv[i] = backlerp * oldframe.scale[i]

	lerp = s_lerped

	LerpVerts(colorOnly, paliashdr.num_xyz, v, ov, verts, lerp, move, frontv, backv)

	assert model_h.gl3_alias_vtx_t.itemsize == 9*4, "invalid gl3_alias_vtx_t size"

	# all the triangle fans and triangle strips of this model will be converted to
	# just triangles: the vertices stay the same and are batched in vtxBuf,
	# but idxBuf will contain indices to draw them all as GL_TRIANGLE
	# this way there's only one draw call (and two glBufferData() calls)
	# instead of (at least) dozens. *greatly* improves performance.

	# so first clear out the data from last call to this function
	# (the buffers are static global so we don't have malloc()/free() for each rendered model)
	vtxBuf.clear() # da_clear(vtxBuf)
	idxBuf.clear() # da_clear(idxBuf)
	numVtx = 0

	while True:

		nextVtxIdx = numVtx # GLushort, da_count(vtxBuf)

		# get the vertex count and primitive type
		count = order[o]
		o += 1

		if not count:

			break # done

		if count < 0:

			count = -count

			type_ = GL.GL_TRIANGLE_FAN

		else:

			type_ = GL.GL_TRIANGLE_STRIP

		buf = np.zeros(count, dtype=model_h.gl3_alias_vtx_t) # da_addn_uninit(vtxBuf, count)

		# Q2PORT: the glcmds of this fan/strip: (s, t, index_xyz) per vertex
		cmds = order[o:o + count * 3]
		o += count * 3
		index_xyz = np.array(cmds[2::3], dtype=np.int32)

		if colorOnly:

			buf["pos"] = s_lerped[index_xyz, 0:3]
			buf["color"][:, 0:3] = shadelight
			buf["color"][:, 3] = alpha

		else:

			# texture coordinates come from the draw list
			buf["texCoord"][:, 0] = cmds[0::3]
			buf["texCoord"][:, 1] = cmds[1::3]

			# normals and vertexes come from the frame list
			# shadedots is set above according to rotation (around Z axis I think)
			# to one of 16 (SHADEDOT_QUANT) presets in r_avertexnormal_dots
			l = shadedots[verts[index_xyz, 3]]

			buf["pos"] = s_lerped[index_xyz, 0:3]
			buf["color"][:, 0:3] = l[:, None] * np.asarray(shadelight, dtype=np.float32)
			buf["color"][:, 3] = alpha

		vtxBuf.append(buf)
		numVtx += count

		_AddFanOrStripIndices(type_, count, nextVtxIdx)

	local.GL3_BindVAO(gl3_main.gl3state.vaoAlias)
	local.GL3_BindVBO(gl3_main.gl3state.vboAlias)

	# Q2PORT: vtxBuf is a list of record arrays; join them as bytes, as joining
	# the record arrays makes numpy merge their field types for each one (slow)
	vtx = np.concatenate([b.view(np.uint8) for b in vtxBuf])
	idx = np.array(idxBuf, dtype=np.uint16)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vtx.nbytes, vtx, GL.GL_STREAM_DRAW)
	local.GL3_BindEBO(gl3_main.gl3state.eboAlias)
	GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, idx.nbytes, idx, GL.GL_STREAM_DRAW)
	GL.glDrawElements(GL.GL_TRIANGLES, len(idxBuf), GL.GL_UNSIGNED_SHORT, ctypes.c_void_p(0))
	gl3_draw.gl3_num3Ddraws += 1
	gl3_draw.gl3_numBufferVtxData += 1
	# TODO ++gl3_numBufferIdxData ?

def DrawAliasShadow(shadowInfo): #gl3_shadowinfo_t*

	#GLenum type;
	#int *order;
	point = np.zeros(3, dtype=np.float32) #vec3_t
	height = 0
	#float lheight;
	#int count;

	paliashdr = shadowInfo.paliashdr
	entity = shadowInfo.entity

	shadevector = np.zeros(3, dtype=np.float32) #vec3_t
	shared.VectorCopy(shadowInfo.shadevector, shadevector)

	# all in this scope is to set s_lerped
	if True:

		#daliasframe_t *frame, *oldframe;
		#dtrivertx_t *v, *ov, *verts;
		backlerp = entity.backlerp
		frontlerp = 1.0 - backlerp
		move = np.zeros(3, dtype=np.float32) #vec3_t
		delta = np.zeros(3, dtype=np.float32)
		vectors = np.zeros((3, 3), dtype=np.float32) #vec3_t [3]
		frontv = np.zeros(3, dtype=np.float32)
		backv = np.zeros(3, dtype=np.float32)
		#int i;

		frame = paliashdr.frames[entity.frame]
		verts = v = frame.verts

		oldframe = paliashdr.frames[entity.oldframe]
		ov = oldframe.verts

		# move should be the delta back to the previous frame * backlerp
		shared.VectorSubtract(entity.oldorigin, entity.origin, delta)
		shared_c.AngleVectors(entity.angles, vectors[0], vectors[1], vectors[2])

		move[0] = shared.DotProduct(delta, vectors[0]) # forward
		move[1] = -shared.DotProduct(delta, vectors[1]) # left
		move[2] = shared.DotProduct(delta, vectors[2]) # up

		shared.VectorAdd(move, oldframe.translate, move)

		for i in range(3):

			move[i] = backlerp * move[i] + frontlerp * frame.translate[i]

			frontv[i] = frontlerp * frame.scale[i]
			backv[i] = backlerp * oldframe.scale[i]

		# false: don't extrude vertices for powerup - this means the powerup shell
		#  is not seen in the shadow, only the underlying model..
		LerpVerts(False, paliashdr.num_xyz, v, ov, verts, s_lerped, move, frontv, backv)

	lheight = entity.origin[2] - shadowInfo.lightspot[2]
	order = paliashdr.glcmds
	o = 0
	height = -lheight + 0.1

	# GL1 uses alpha 0.5, but in GL3 0.3 looks better
	color = (0, 0, 0, 0.3) #GLfloat [4]

	# draw the shadow in a single draw call, just like the model

	vtxBuf.clear()
	idxBuf.clear()
	numVtx = 0

	while True:

		nextVtxIdx = numVtx

		# get the vertex count and primitive type
		count = order[o]
		o += 1

		if not count:

			break # done

		if count < 0:

			count = -count

			type_ = GL.GL_TRIANGLE_FAN

		else:

			type_ = GL.GL_TRIANGLE_STRIP

		buf = np.zeros(count, dtype=model_h.gl3_alias_vtx_t)

		for i in range(count):

			# normals and vertexes come from the frame list
			shared.VectorCopy(s_lerped[order[o + 2]][0:3], point)

			point[0] -= shadevector[0] * (point[2] + lheight)
			point[1] -= shadevector[1] * (point[2] + lheight)
			point[2] = height

			buf[i]["pos"] = point

			buf[i]["color"] = color

			o += 3

		vtxBuf.append(buf)
		numVtx += count

		_AddFanOrStripIndices(type_, count, nextVtxIdx)

	local.GL3_BindVAO(gl3_main.gl3state.vaoAlias)
	local.GL3_BindVBO(gl3_main.gl3state.vboAlias)

	# Q2PORT: vtxBuf is a list of record arrays; join them as bytes, as joining
	# the record arrays makes numpy merge their field types for each one (slow)
	vtx = np.concatenate([b.view(np.uint8) for b in vtxBuf])
	idx = np.array(idxBuf, dtype=np.uint16)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, vtx.nbytes, vtx, GL.GL_STREAM_DRAW)
	local.GL3_BindEBO(gl3_main.gl3state.eboAlias)
	GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, idx.nbytes, idx, GL.GL_STREAM_DRAW)
	GL.glDrawElements(GL.GL_TRIANGLES, len(idxBuf), GL.GL_UNSIGNED_SHORT, ctypes.c_void_p(0))
	gl3_draw.gl3_num3Ddraws += 1
	gl3_draw.gl3_numBufferVtxData += 1
	# TODO ++gl3_numBufferIdxData ?

def CullAliasModel(bbox, e): #vec3_t [8], entity_t * (returns qboolean)

	#int i;
	mins = np.zeros(3, dtype=np.float32) #vec3_t
	maxs = np.zeros(3, dtype=np.float32) #vec3_t
	#dmdl_t *paliashdr;
	vectors = np.zeros((3, 3), dtype=np.float32) #vec3_t [3]
	thismins = np.zeros(3, dtype=np.float32) #vec3_t
	oldmins = np.zeros(3, dtype=np.float32)
	thismaxs = np.zeros(3, dtype=np.float32)
	oldmaxs = np.zeros(3, dtype=np.float32)
	#daliasframe_t *pframe, *poldframe;
	angles = np.zeros(3, dtype=np.float32) #vec3_t

	model = e.model

	paliashdr = model.extradata

	if (e.frame >= paliashdr.num_frames) or (e.frame < 0):

		clientserver.Com_DPrintf("R_CullAliasModel {}: no such frame {}\n".format(
				model.name, e.frame))
		e.frame = 0

	if (e.oldframe >= paliashdr.num_frames) or (e.oldframe < 0):

		clientserver.Com_DPrintf("R_CullAliasModel {}: no such oldframe {}\n".format(
				model.name, e.oldframe))
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

			thismins[i] = pframe.translate[i]
			thismaxs[i] = thismins[i] + pframe.scale[i] * 255

			oldmins[i] = poldframe.translate[i]
			oldmaxs[i] = oldmins[i] + poldframe.scale[i] * 255

			if thismins[i] < oldmins[i]:

				mins[i] = thismins[i]

			else:

				mins[i] = oldmins[i]

			if thismaxs[i] > oldmaxs[i]:

				maxs[i] = thismaxs[i]

			else:

				maxs[i] = oldmaxs[i]

	# compute a full bounding box
	for i in range(8):

		tmp = np.zeros(3, dtype=np.float32) #vec3_t

		if i & 1:

			tmp[0] = mins[0]

		else:

			tmp[0] = maxs[0]

		if i & 2:

			tmp[1] = mins[1]

		else:

			tmp[1] = maxs[1]

		if i & 4:

			tmp[2] = mins[2]

		else:

			tmp[2] = maxs[2]

		shared.VectorCopy(tmp, bbox[i])

	# rotate the bounding box
	shared.VectorCopy(e.angles, angles)
	angles[shared.YAW] = -angles[shared.YAW]
	shared_c.AngleVectors(angles, vectors[0], vectors[1], vectors[2])

	for i in range(8):

		tmp = np.zeros(3, dtype=np.float32) #vec3_t

		shared.VectorCopy(bbox[i], tmp)

		bbox[i][0] = shared.DotProduct(vectors[0], tmp)
		bbox[i][1] = -shared.DotProduct(vectors[1], tmp)
		bbox[i][2] = shared.DotProduct(vectors[2], tmp)

		shared.VectorAdd(e.origin, bbox[i], bbox[i])

	aggregatemask = ~0

	for p in range(8):

		mask = 0

		for f in range(4):

			dp = shared.DotProduct(gl3_main.frustum[f].normal, bbox[p])

			if (dp - gl3_main.frustum[f].dist) < 0:

				mask |= (1 << f)

		aggregatemask &= mask

	if aggregatemask:

		return True

	return False

def GL3_DrawAliasModel(entity): #entity_t *

	#int i;
	#dmdl_t *paliashdr;
	#float an;
	bbox = np.zeros((8, 3), dtype=np.float32) #vec3_t [8]
	shadelight = np.zeros(3, dtype=np.float32) #vec3_t
	shadevector = np.zeros(3, dtype=np.float32) #vec3_t
	#gl3image_t *skin;
	origProjViewMat = None # hmm_mat4 = {0}; use for left-handed rendering
	# used to restore ModelView matrix after changing it for this entities position/rotation
	origModelMat = None # hmm_mat4 = {0}

	if not (entity.flags & shared.RF_WEAPONMODEL):

		if CullAliasModel(bbox, entity):

			return

	if entity.flags & shared.RF_WEAPONMODEL:

		if gl3_main.gl_lefthand.value == 2:

			return

	model = entity.model
	paliashdr = model.extradata

	# get lighting information
	if (entity.flags &
		(shared.RF_SHELL_HALF_DAM | shared.RF_SHELL_GREEN | shared.RF_SHELL_RED |
		 shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE)):

		shadelight[:] = 0 # VectorClear(shadelight)

		if entity.flags & shared.RF_SHELL_HALF_DAM:

			shadelight[0] = 0.56
			shadelight[1] = 0.59
			shadelight[2] = 0.45

		if entity.flags & shared.RF_SHELL_DOUBLE:

			shadelight[0] = 0.9
			shadelight[1] = 0.7

		if entity.flags & shared.RF_SHELL_RED:

			shadelight[0] = 1.0

		if entity.flags & shared.RF_SHELL_GREEN:

			shadelight[1] = 1.0

		if entity.flags & shared.RF_SHELL_BLUE:

			shadelight[2] = 1.0

	elif entity.flags & shared.RF_FULLBRIGHT:

		for i in range(3):

			shadelight[i] = 1.0

	else:

		gl3_light.GL3_LightPoint(entity, entity.origin, shadelight)

		# player lighting hack for communication back to server
		if entity.flags & shared.RF_WEAPONMODEL:

			# pick the greatest component, which should be
			#   the same as the mono value returned by software
			if shadelight[0] > shadelight[1]:

				if shadelight[0] > shadelight[2]:

					gl3_main.r_lightlevel.value = 150 * shadelight[0]

				else:

					gl3_main.r_lightlevel.value = 150 * shadelight[2]

			else:

				if shadelight[1] > shadelight[2]:

					gl3_main.r_lightlevel.value = 150 * shadelight[1]

				else:

					gl3_main.r_lightlevel.value = 150 * shadelight[2]

	if entity.flags & shared.RF_MINLIGHT:

		i = 0
		while i < 3:

			if shadelight[i] > 0.1:

				break

			i += 1

		if i == 3:

			shadelight[0] = 0.1
			shadelight[1] = 0.1
			shadelight[2] = 0.1

	if entity.flags & shared.RF_GLOW:

		# bonus items will pulse with time
		#float scale;
		#float min;

		scale = 0.1 * math.sin(gl3_main.r_newrefdef.time * 7)

		for i in range(3):

			min_ = shadelight[i] * 0.8
			shadelight[i] += scale

			if shadelight[i] < min_:

				shadelight[i] = min_

	# Note: gl_overbrightbits are now applied in shader.

	# ir goggles color override
	if (gl3_main.r_newrefdef.rdflags & shared.RDF_IRGOGGLES) and (entity.flags & shared.RF_IR_VISIBLE):

		shadelight[0] = 1.0
		shadelight[1] = 0.0
		shadelight[2] = 0.0

	an = entity.angles[1] / 180 * math.pi
	shadevector[0] = math.cos(-an)
	shadevector[1] = math.sin(-an)
	shadevector[2] = 1
	shared_c.VectorNormalize(shadevector)

	# locate the proper data
	gl3_main.c_alias_polys += paliashdr.num_tris

	# draw all the triangles
	if entity.flags & shared.RF_DEPTHHACK:

		# hack the depth range to prevent view model from poking into walls
		GL.glDepthRange(gl3_main.gl3depthmin, gl3_main.gl3depthmin + 0.3 * (gl3_main.gl3depthmax - gl3_main.gl3depthmin))

	uni3D = gl3_main.gl3state.uni3DData
	if entity.flags & shared.RF_WEAPONMODEL:

		#extern hmm_mat4 GL3_SetPerspective(GLdouble fovy);

		origProjViewMat = uni3D[local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16].copy()

		# render weapon with a different FOV (r_gunfov) so it's not distorted at high view FOV
		projMat = gl3_main.GL3_SetPerspective( gl3_main.r_newrefdef.fov_y if (gl3_main.r_gunfov.value < 0) else gl3_main.r_gunfov.value )

		if gl3_main.gl_lefthand.value == 1.0:

			# to mirror gun so it's rendered left-handed, just invert X-axis column
			# of projection matrix
			for i in range(4):

				projMat[0][i] = - projMat[0][i]

			#GL3_UpdateUBO3D(); Note: GL3_RotateForEntity() will call this,no need to do it twice before drawing

			GL.glCullFace(GL.GL_BACK)

		uni3D[local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16] = hmm.HMM_MultiplyMat4(projMat, gl3_main.gl3state.viewMat3D).flatten()


	#glPushMatrix();
	origModelMat = uni3D[local.UNI3D_MODEL:local.UNI3D_MODEL + 16].copy()

	entity.angles[shared.PITCH] = -entity.angles[shared.PITCH]
	gl3_main.GL3_RotateUni3DforEntity(entity)
	entity.angles[shared.PITCH] = -entity.angles[shared.PITCH]


	# select skin
	if entity.skin is not None:

		skin = entity.skin # custom player skin

	else:

		if entity.skinnum >= files_h.MAX_MD2SKINS:

			skin = model.skins[0]

		else:

			skin = model.skins[entity.skinnum]

			if skin is None:

				skin = model.skins[0]

	if skin is None:

		skin = gl3_misc.gl3_notexture # fallback...

	gl3_image.GL3_Bind(skin.texnum)

	if entity.flags & shared.RF_TRANSLUCENT:

		GL.glEnable(GL.GL_BLEND)


	if ((entity.frame >= paliashdr.num_frames) or
		(entity.frame < 0)):

		clientserver.Com_DPrintf("R_DrawAliasModel {}: no such frame {}\n".format(
				model.name, entity.frame))
		entity.frame = 0
		entity.oldframe = 0

	if ((entity.oldframe >= paliashdr.num_frames) or
		(entity.oldframe < 0)):

		clientserver.Com_DPrintf("R_DrawAliasModel {}: no such oldframe {}\n".format(
				model.name, entity.oldframe))
		entity.frame = 0
		entity.oldframe = 0

	DrawAliasFrameLerp(paliashdr, entity, shadelight)

	if entity.flags & shared.RF_WEAPONMODEL:

		uni3D[local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16] = origProjViewMat
		if gl3_main.gl_lefthand.value == 1.0:
			GL.glCullFace(GL.GL_FRONT)

	#glPopMatrix();
	uni3D[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = origModelMat
	gl3_shaders.GL3_UpdateUBO3D()

	if entity.flags & shared.RF_TRANSLUCENT:

		GL.glDisable(GL.GL_BLEND)

	if entity.flags & shared.RF_DEPTHHACK:

		GL.glDepthRange(gl3_main.gl3depthmin, gl3_main.gl3depthmax)

	if gl3_main.gl_shadows.value and gl3_main.gl3config.stencil and not (entity.flags & (shared.RF_TRANSLUCENT | shared.RF_WEAPONMODEL | shared.RF_NOSHADOW)):

		si = gl3_shadowinfo_t() # = {0}
		shared.VectorCopy(gl3_light.lightspot, si.lightspot)
		shared.VectorCopy(shadevector, si.shadevector)
		si.paliashdr = paliashdr
		si.entity = entity

		shadowModels.append(si) # da_push(shadowModels, si)

def GL3_ResetShadowAliasModels(): #void

	shadowModels.clear() # da_clear(shadowModels)

def GL3_DrawAliasShadows(): #void

	numShadowModels = len(shadowModels)
	if numShadowModels == 0:

		return

	uni3D = gl3_main.gl3state.uni3DData

	#glPushMatrix();
	oldMat = uni3D[local.UNI3D_MODEL:local.UNI3D_MODEL + 16].reshape(4, 4).copy()

	GL.glEnable(GL.GL_BLEND)
	local.GL3_UseProgram(gl3_main.gl3state.si3DaliasColor.shaderProgram)

	if gl3_main.gl3config.stencil:

		GL.glEnable(GL.GL_STENCIL_TEST)
		GL.glStencilFunc(GL.GL_EQUAL, 1, 2)
		GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_INCR)

	for i in range(numShadowModels):

		si = shadowModels[i] # XXX da_getptr(shadowModels, i);
		e = si.entity

		# don't rotate shadows on ungodly axes
		#glTranslatef(e->origin[0], e->origin[1], e->origin[2]);
		#glRotatef(e->angles[1], 0, 0, 1);
		rotTransMat = hmm.HMM_Rotate(e.angles[1], hmm.HMM_Vec3(0, 0, 1))
		rotTransMat[3][0:3] = e.origin # VectorCopy(e->origin, rotTransMat.Elements[3])
		uni3D[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = hmm.HMM_MultiplyMat4(oldMat, rotTransMat).flatten()
		gl3_shaders.GL3_UpdateUBO3D()

		DrawAliasShadow(si)

	if gl3_main.gl3config.stencil:

		GL.glDisable(GL.GL_STENCIL_TEST)

	GL.glDisable(GL.GL_BLEND)

	#glPopMatrix();
	uni3D[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = oldMat.flatten()
	gl3_shaders.GL3_UpdateUBO3D()
