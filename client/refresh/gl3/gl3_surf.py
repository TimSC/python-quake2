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
 * Surface generation and drawing
 *
 * =======================================================================
"""

from __future__ import annotations

import ctypes

import numpy as np
import OpenGL.GL as GL

from q2data import bsp as q2bsp
from common.header import shared
from common.shared import shared as shared_c
from client import ref
from client.refresh import ref_shared
from client.refresh.files import surf as files_surf
from client.refresh.gl3.header import local
from client.refresh.gl3.header import model
from client.refresh.gl3 import gl3_main, gl3_image, gl3_light, gl3_model, gl3_shaders, gl3_warp

#include <assert.h>
#include <stddef.h> // ofsetof()

#include "header/local.h"

c_visible_lightmaps = 0 #int
c_visible_textures = 0 #int
modelorg = np.zeros(3, dtype=np.float32) #static vec3_t, relative to viewpoint
# static msurface_t *gl3_alpha_surfaces; Q2PORT: a list; the C prepends to the
# chain, so it is walked reversed()
gl3_alpha_surfaces = []

gl3_lms = local.gl3lightmapstate_t() #gl3lightmapstate_t

BACKFACE_EPSILON = 0.01

#extern gl3image_t gl3textures[MAX_GL3TEXTURES];
#extern int numgl3textures;

def _offsetof(field): # Q2PORT: offsetof(gl3_3D_vtx_t, field), as the pointer PyOpenGL needs
	return ctypes.c_void_p(model.gl3_3D_vtx_t.fields[field][1])

def GL3_SurfInit(): #void

	# init the VAO and VBO for the standard vertexdata: 10 floats and 1 uint
	# (X, Y, Z), (S, T), (LMS, LMT), (normX, normY, normZ) ; lightFlags - last two groups for lightmap/dynlights

	gl3_main.gl3state.vao3D = GL.glGenVertexArrays(1)
	local.GL3_BindVAO(gl3_main.gl3state.vao3D)

	gl3_main.gl3state.vbo3D = GL.glGenBuffers(1)
	local.GL3_BindVBO(gl3_main.gl3state.vbo3D)

	stride = model.gl3_3D_vtx_t.itemsize # sizeof(gl3_3D_vtx_t)

	# Q2PORT: the offsets must be ctypes.c_void_p, PyOpenGL turns a plain int into a pointer to a temporary
	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_POSITION, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, ctypes.c_void_p(0))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_TEXCOORD)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, _offsetof("texCoord"))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_LMTEXCOORD)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_LMTEXCOORD, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, _offsetof("lmTexCoord"))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_NORMAL)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_NORMAL, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, _offsetof("normal"))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_LIGHTFLAGS)
	GL.glVertexAttribIPointer(local.GL3_ATTRIB_LIGHTFLAGS, 1, GL.GL_UNSIGNED_INT, stride, _offsetof("lightFlags"))

	gl3_main.gl3state.ebo3D = GL.glGenBuffers(1)

	# init VAO and VBO for model vertexdata: 9 floats
	# (X,Y,Z), (S,T), (R,G,B,A)

	gl3_main.gl3state.vaoAlias = GL.glGenVertexArrays(1)
	local.GL3_BindVAO(gl3_main.gl3state.vaoAlias)

	gl3_main.gl3state.vboAlias = GL.glGenBuffers(1)
	local.GL3_BindVBO(gl3_main.gl3state.vboAlias)

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_POSITION, 3, GL.GL_FLOAT, GL.GL_FALSE, 9*4, ctypes.c_void_p(0))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_TEXCOORD)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, GL.GL_FALSE, 9*4, ctypes.c_void_p(3*4))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_COLOR)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_COLOR, 4, GL.GL_FLOAT, GL.GL_FALSE, 9*4, ctypes.c_void_p(5*4))

	gl3_main.gl3state.eboAlias = GL.glGenBuffers(1)

	# init VAO and VBO for particle vertexdata: 9 floats
	# (X,Y,Z), (point_size,distace_to_camera), (R,G,B,A)

	gl3_main.gl3state.vaoParticle = GL.glGenVertexArrays(1)
	local.GL3_BindVAO(gl3_main.gl3state.vaoParticle)

	gl3_main.gl3state.vboParticle = GL.glGenBuffers(1)
	local.GL3_BindVBO(gl3_main.gl3state.vboParticle)

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_POSITION)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_POSITION, 3, GL.GL_FLOAT, GL.GL_FALSE, 9*4, ctypes.c_void_p(0))

	# TODO: maybe move point size and camera origin to UBO and calculate distance in vertex shader
	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_TEXCOORD) # it's abused for (point_size, distance) here..
	GL.glVertexAttribPointer(local.GL3_ATTRIB_TEXCOORD, 2, GL.GL_FLOAT, GL.GL_FALSE, 9*4, ctypes.c_void_p(3*4))

	GL.glEnableVertexAttribArray(local.GL3_ATTRIB_COLOR)
	GL.glVertexAttribPointer(local.GL3_ATTRIB_COLOR, 4, GL.GL_FLOAT, GL.GL_FALSE, 9*4, ctypes.c_void_p(5*4))

def GL3_SurfShutdown(): #void

	GL.glDeleteBuffers(1, [gl3_main.gl3state.ebo3D])
	gl3_main.gl3state.ebo3D = 0
	GL.glDeleteBuffers(1, [gl3_main.gl3state.vbo3D])
	gl3_main.gl3state.vbo3D = 0
	GL.glDeleteVertexArrays(1, [gl3_main.gl3state.vao3D])
	gl3_main.gl3state.vao3D = 0

	GL.glDeleteBuffers(1, [gl3_main.gl3state.eboAlias])
	gl3_main.gl3state.eboAlias = 0
	GL.glDeleteBuffers(1, [gl3_main.gl3state.vboAlias])
	gl3_main.gl3state.vboAlias = 0
	GL.glDeleteVertexArrays(1, [gl3_main.gl3state.vaoAlias])
	gl3_main.gl3state.vaoAlias = 0

def SetLightFlags(surf): #msurface_t *

	lightFlags = 0
	if surf.dlightframe == gl3_main.gl3_framecount:

		lightFlags = surf.dlightbits & 0xffffffff

	verts = surf.polys[0].vertices

	numVerts = surf.polys[0].numverts
	verts["lightFlags"][:numVerts] = lightFlags # for each of the numVerts: verts[i].lightFlags = lightFlags

def SetAllLightFlags(surf): #msurface_t *

	lightFlags = 0xffffffff

	verts = surf.polys[0].vertices

	numVerts = surf.polys[0].numverts
	verts["lightFlags"][:numVerts] = lightFlags

def GL3_DrawGLPoly(fa, drawCmd): #msurface_t *, gl3drawCmd_t

	p = fa.polys[0]

	gl3_main.GL3_Add3DdrawCmdToBatch(p.vertices, p.numverts, GL.GL_TRIANGLE_FAN, drawCmd)

def GL3_DrawGLFlowingPoly(fa, drawCmd): #msurface_t *, gl3drawCmd_t

	#glpoly_t *p;
	#float scroll;

	p = fa.polys[0]

	scroll = -64.0 * ((gl3_main.r_newrefdef.time / 40.0) - int(gl3_main.r_newrefdef.time / 40.0))

	if scroll == 0.0:

		scroll = -64.0

	drawCmd.scroll = scroll
	drawCmd.flags |= local.DCFlag_UseScroll

	gl3_main.GL3_Add3DdrawCmdToBatch(p.vertices, p.numverts, GL.GL_TRIANGLE_FAN, drawCmd)

LINE_VTX_COUNT = (256 * 6)

def DrawTriangleOutlines(): #void

	#static gl3_3D_vtx_t vtx[LINE_VTX_COUNT];
	#const msurface_t *surf;
	#size_t i, curr_vtx;

	if not gl3_main.gl_showtris.value:

		return

	gl3_main.GL3_Draw3DBatchesNow()

	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glUseProgram(gl3_main.gl3state.si3DcolorOnly.shaderProgram)

	gl3_main.gl3state.uniCommonData[local.UNICOMMON_COLOR:local.UNICOMMON_COLOR + 4] = (1.0, 1.0, 1.0, 1.0)
	gl3_shaders.GL3_UpdateUBOCommon()
	local.GL3_BindVAO(gl3_main.gl3state.vao3D)
	local.GL3_BindVBO(gl3_main.gl3state.vbo3D)

	curr_vtx = 0

	vtx = np.zeros(LINE_VTX_COUNT, dtype=model.gl3_3D_vtx_t) # memset(vtx, 0, sizeof(vtx))
	for surf in gl3_main.gl3_worldmodel.surfaces:

		if surf.visframe != gl3_main.gl3_framecount:

			continue

		for p in surf.polys: # for (p = surf->polys; p != NULL; p = p->chain)

			for j in range(2, p.numverts):

				if curr_vtx > (LINE_VTX_COUNT - 6):

					GL.glBufferData(GL.GL_ARRAY_BUFFER, vtx.nbytes, vtx.view(np.uint8), GL.GL_STREAM_DRAW)
					GL.glDrawArrays(GL.GL_LINES, 0, curr_vtx)
					curr_vtx = 0
					vtx[:] = 0

				pos = p.vertices["pos"]
				vtx["pos"][curr_vtx + 0] = pos[0]
				vtx["pos"][curr_vtx + 1] = pos[j - 1]

				vtx["pos"][curr_vtx + 2] = pos[j - 1]
				vtx["pos"][curr_vtx + 3] = pos[j]

				vtx["pos"][curr_vtx + 4] = pos[j]
				vtx["pos"][curr_vtx + 5] = pos[0]

				curr_vtx += 6

	if curr_vtx:

		GL.glBufferData(GL.GL_ARRAY_BUFFER, vtx.nbytes, vtx.view(np.uint8), GL.GL_STREAM_DRAW)
		GL.glDrawArrays(GL.GL_LINES, 0, curr_vtx)

	GL.glEnable(GL.GL_DEPTH_TEST)

def RenderBrushPoly(currententity, fa, drawCmd): #entity_t *, msurface_t *, gl3drawCmd_t

	#gl3image_t *image;

	gl3_main.c_brush_polys += 1

	image = files_surf.R_TextureAnimation(currententity, fa.texinfo)
	drawCmd.texnum = image.texnum

	if fa.flags & model.SURF_DRAWTURB:

		gl3_warp.GL3_EmitWaterPolys(fa, drawCmd)
		return


	drawCmd.lmtexnum = fa.lightmaptexturenum

	# Any dynamic lights on this surface?
	# TODO: maybe put lightstyles into a uniform (it's just 256 vec4)
	#       and put fa->styles[] into the 3d draw vertex?
	drawCmd.styles = list(fa.styles) # memcpy(drawCmd.styles, fa->styles, sizeof(fa->styles))
	drawCmd.flags |= local.DCFlag_UseLmStyles

	if fa.texinfo.flags & shared.SURF_FLOWING:

		local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3DlmFlow)
		GL3_DrawGLFlowingPoly(fa, drawCmd)

	else:

		local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3Dlm)
		GL3_DrawGLPoly(fa, drawCmd)

	# Note: lightmap chains are gone, lightmaps are rendered together with normal texture in one pass

"""
 * Draw water surfaces and windows.
 * The BSP tree is walked front to back, so unwinding the chain
 * of alpha_surfaces will draw back to front, giving proper ordering.
"""
def GL3_DrawAlphaSurfaces(): #void

	global gl3_alpha_surfaces

	#msurface_t *s;

	# go back to the world matrix
	drawCmd = local.GL3_CreateDrawCmd()
	drawCmd.flags |= local.DCFlag_Blend

	for s in reversed(gl3_alpha_surfaces): # for (s = gl3_alpha_surfaces; s != NULL; s = s->texturechain)

		drawCmd.texnum = s.texinfo.image.texnum
		gl3_main.c_brush_polys += 1
		if s.texinfo.flags & shared.SURF_TRANS33:

			drawCmd.alpha = 0.333

		elif s.texinfo.flags & shared.SURF_TRANS66:

			drawCmd.alpha = 0.666

		else:

			drawCmd.alpha = 1.0

		if s.flags & model.SURF_DRAWTURB:

			gl3_warp.GL3_EmitWaterPolys(s, drawCmd)

		elif s.texinfo.flags & shared.SURF_FLOWING:

			local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3DtransFlow)
			GL3_DrawGLFlowingPoly(s, drawCmd)

		else:

			local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3Dtrans)
			GL3_DrawGLPoly(s, drawCmd)

	gl3_alpha_surfaces = []

def DrawTextureChains(currententity): #entity_t *

	global c_visible_textures

	#int i;
	#msurface_t *s;
	#gl3image_t *image;

	c_visible_textures = 0

	drawCmd = local.GL3_CreateDrawCmd()

	for i in range(gl3_image.numgl3textures):

		image = gl3_image.gl3textures[i]

		if not image.registration_sequence:

			continue

		# Q2PORT: image->texturechain is a list; the C prepends, so it is walked reversed()
		s = image.texturechain

		if not s:

			continue

		c_visible_textures += 1

		for s in reversed(image.texturechain):

			SetLightFlags(s)
			RenderBrushPoly(currententity, s, drawCmd)

		image.texturechain = None

	# TODO: maybe one loop for normal faces and one for SURF_DRAWTURB ???

def RenderLightmappedPoly(currententity, surf, drawCmd): #entity_t *, msurface_t *, gl3drawCmd_t

	image = files_surf.R_TextureAnimation(currententity, surf.texinfo)


	assert (surf.texinfo.flags & (shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP)) == 0, \
			"RenderLightMappedPoly mustn't be called with transparent, sky or warping surfaces!"

	# Any dynamic lights on this surface?
	drawCmd.styles = list(surf.styles) # memcpy(drawCmd.styles, surf->styles, sizeof(surf->styles))
	drawCmd.flags |= local.DCFlag_UseLmStyles

	gl3_main.c_brush_polys += 1

	drawCmd.texnum = image.texnum
	drawCmd.lmtexnum = surf.lightmaptexturenum

	if surf.texinfo.flags & shared.SURF_FLOWING:

		local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3DlmFlow)
		GL3_DrawGLFlowingPoly(surf, drawCmd)

	else:

		local.GL3_SetDrawCmdShader(drawCmd, gl3_main.gl3state.si3Dlm)
		GL3_DrawGLPoly(surf, drawCmd)

def DrawInlineBModel(currententity, currentmodel, drawCmd): #entity_t *, gl3model_t *, gl3drawCmd_t

	#int i, k;
	#cplane_t *pplane;
	#float dot;
	#msurface_t *psurf;
	#dlight_t *lt;

	# calculate dynamic lighting for bmodel
	for k in range(gl3_main.r_newrefdef.num_dlights):

		lt = gl3_main.r_newrefdef.dlights[k]
		files_surf.R_MarkLights(lt, 1 << k, currentmodel.nodes[currentmodel.firstnode],
			gl3_light.r_dlightframecount, gl3_light.GL3_MarkSurfaceLights)

	if currententity.flags & shared.RF_TRANSLUCENT:

		drawCmd.flags |= local.DCFlag_Blend
		""" TODO: should I care about the 0.25 part? we'll just set alpha to 0.33 or 0.66 depending on surface flag..
		glColor4f(1, 1, 1, 0.25);
		R_TexEnv(GL_MODULATE);
		"""

	# draw texture
	for i in range(currentmodel.nummodelsurfaces):

		psurf = currentmodel.surfaces[currentmodel.firstmodelsurface + i]

		# find which side of the node we are on
		pplane = psurf.plane

		dot = shared.DotProduct(modelorg, pplane.normal) - pplane.dist

		# draw the polygon
		if (((psurf.flags & model.SURF_PLANEBACK) and (dot < -BACKFACE_EPSILON)) or
			(not (psurf.flags & model.SURF_PLANEBACK) and (dot > BACKFACE_EPSILON))):

			if psurf.texinfo.flags & (shared.SURF_TRANS33 | shared.SURF_TRANS66):

				# add to the translucent chain
				gl3_alpha_surfaces.append(psurf)

			elif not (psurf.flags & model.SURF_DRAWTURB):

				SetAllLightFlags(psurf)
				RenderLightmappedPoly(currententity, psurf, drawCmd)

			else:

				RenderBrushPoly(currententity, psurf, drawCmd)


def GL3_DrawBrushModel(e, currentmodel): #entity_t *, gl3model_t *

	mins = np.zeros(3, dtype=np.float32) #vec3_t
	maxs = np.zeros(3, dtype=np.float32) #vec3_t
	#int i;
	#qboolean rotated;

	if currentmodel.nummodelsurfaces == 0:

		return

	drawCmd = local.GL3_CreateDrawCmd()
	if e.flags & shared.RF_TRANSLUCENT:
		drawCmd.flags |= local.DCFlag_DisableDepthMask


	if e.angles[0] or e.angles[1] or e.angles[2]:

		rotated = True

		for i in range(3):

			mins[i] = e.origin[i] - currentmodel.radius
			maxs[i] = e.origin[i] + currentmodel.radius

	else:

		rotated = False
		shared.VectorAdd(e.origin, currentmodel.mins, mins)
		shared.VectorAdd(e.origin, currentmodel.maxs, maxs)

	if gl3_main.r_cull.value and files_surf.R_CullBox(mins, maxs, gl3_main.frustum):

		return

	if gl3_main.gl_zfix.value:

		drawCmd.flags |= local.DCFlag_PolyOffsetFill

	shared.VectorSubtract(gl3_main.r_newrefdef.vieworg, e.origin, modelorg)

	if rotated:

		temp = np.zeros(3, dtype=np.float32) #vec3_t
		forward = np.zeros(3, dtype=np.float32)
		right = np.zeros(3, dtype=np.float32)
		up = np.zeros(3, dtype=np.float32)

		shared.VectorCopy(modelorg, temp)
		shared_c.AngleVectors(e.angles, forward, right, up)
		modelorg[0] = shared.DotProduct(temp, forward)
		modelorg[1] = -shared.DotProduct(temp, right)
		modelorg[2] = shared.DotProduct(temp, up)

	#glPushMatrix();

	e.angles[0] = -e.angles[0]
	e.angles[2] = -e.angles[2]
	gl3_main.GL3_RotateForEntity(e, drawCmd)
	e.angles[0] = -e.angles[0]
	e.angles[2] = -e.angles[2]

	DrawInlineBModel(e, currentmodel, drawCmd)

	# glPopMatrix();


def RecursiveWorldNode(currententity, node): #entity_t *, mnode_t *

	#int c, side, sidebit;
	#cplane_t *plane;
	#msurface_t *surf, **mark;
	#mleaf_t *pleaf;
	#float dot;
	#gl3image_t *image;

	if node.contents == shared.CONTENTS_SOLID:

		return # solid

	if node.visframe != gl3_main.gl3_visframecount:

		return

	if gl3_main.r_cull.value and files_surf.R_CullBox(node.minmaxs[0:3], node.minmaxs[3:6], gl3_main.frustum):

		return

	# if a leaf node, draw stuff
	if node.contents != ref_shared.CONTENTS_NODE:

		pleaf = node # (mleaf_t *)node

		# check for door connected areas
		# check for door connected areas
		if not files_surf.R_AreaVisible(gl3_main.r_newrefdef.areabits, pleaf):
			return # not visible

		for mark in pleaf.firstmarksurface[:pleaf.nummarksurfaces]:

			mark.visframe = gl3_main.gl3_framecount

		return

	# node is just a decision point, so go down the apropriate
	#   sides find which side of the node we are on
	plane = node.plane

	if plane.type == q2bsp.PlaneType.X:
		dot = modelorg[0] - plane.dist
	elif plane.type == q2bsp.PlaneType.Y:
		dot = modelorg[1] - plane.dist
	elif plane.type == q2bsp.PlaneType.Z:
		dot = modelorg[2] - plane.dist
	else:
		dot = shared.DotProduct(modelorg, plane.normal) - plane.dist

	if dot >= 0:

		side = 0
		sidebit = 0

	else:

		side = 1
		sidebit = model.SURF_PLANEBACK

	# recurse down the children, front side first
	RecursiveWorldNode(currententity, node.children[side])

	# draw stuff
	surfaces = gl3_main.gl3_worldmodel.surfaces
	for c in range(node.numsurfaces):

		surf = surfaces[node.firstsurface + c]

		if surf.visframe != gl3_main.gl3_framecount:

			continue

		if (surf.flags & model.SURF_PLANEBACK) != sidebit:

			continue # wrong side

		if surf.texinfo.flags & shared.SURF_SKY:

			# just adds to visible sky bounds
			gl3_warp.GL3_AddSkySurface(surf)

		elif surf.texinfo.flags & (shared.SURF_TRANS33 | shared.SURF_TRANS66):

			# add to the translucent chain
			gl3_alpha_surfaces.append(surf)
			surf.texinfo.image = files_surf.R_TextureAnimation(currententity, surf.texinfo)

		else:

			# calling RenderLightmappedPoly() here probably isn't optimal, rendering everything
			# through texturechains should be faster, because far less glBindTexture() is needed
			# (and it might allow batching the drawcalls of surfaces with the same texture)
			"""
#if 0
			if(!(surf->flags & SURF_DRAWTURB))
			{
				RenderLightmappedPoly(surf);
			}
			else
#endif // 0
			"""
			if True:

				# the polygon is visible, so add it to the texture sorted chain
				image = files_surf.R_TextureAnimation(currententity, surf.texinfo)
				if image.texturechain is None:
					image.texturechain = []
				image.texturechain.append(surf) # surf->texturechain = image->texturechain; image->texturechain = surf;

	# recurse down the back side
	RecursiveWorldNode(currententity, node.children[1 - side]) # node->children[!side]

def GL3_DrawWorld(): #void

	#entity_t ent;

	if not gl3_main.r_drawworld.value:

		return

	if gl3_main.r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:

		return

	shared.VectorCopy(gl3_main.r_newrefdef.vieworg, modelorg)

	# auto cycle the world frame for texture animation
	ent = ref.entity_t() # memset(&ent, 0, sizeof(ent));
	ent.frame = int(gl3_main.r_newrefdef.time * 2)

	gl3_main.gl3state.currenttexture = -1

	gl3_warp.GL3_ClearSkyBox()
	RecursiveWorldNode(ent, gl3_main.gl3_worldmodel.nodes[0])
	DrawTextureChains(ent)
	gl3_warp.GL3_DrawSkyBox()
	DrawTriangleOutlines()

	# make sure all this is drawed
	gl3_main.GL3_Draw3DBatchesNow()

"""
 * Mark the leaves and nodes that are
 * in the PVS for the current cluster
"""
def GL3_MarkLeaves(): #void

	#const byte *vis;
	#YQ2_ALIGNAS_TYPE(int) byte fatvis[MAX_MAP_LEAFS / 8];
	#mnode_t *node;
	#int i, c;
	#mleaf_t *leaf;
	#int cluster;

	if ((gl3_main.gl3_oldviewcluster == gl3_main.gl3_viewcluster) and
		(gl3_main.gl3_oldviewcluster2 == gl3_main.gl3_viewcluster2) and
		not gl3_main.r_novis.value and
		(gl3_main.gl3_viewcluster != -1)):

		return

	# development aid to let you run around
	#   and see exactly where the pvs ends
	if gl3_main.r_lockpvs.value:

		return

	gl3_main.gl3_visframecount += 1
	gl3_main.gl3_oldviewcluster = gl3_main.gl3_viewcluster
	gl3_main.gl3_oldviewcluster2 = gl3_main.gl3_viewcluster2

	worldmodel = gl3_main.gl3_worldmodel

	if gl3_main.r_novis.value or (gl3_main.gl3_viewcluster == -1) or worldmodel.vis is None:

		# mark everything
		for i in range(worldmodel.numleafs):

			worldmodel.leafs[i].visframe = gl3_main.gl3_visframecount

		for i in range(worldmodel.numnodes):

			worldmodel.nodes[i].visframe = gl3_main.gl3_visframecount

		return

	vis = gl3_model.GL3_Mod_ClusterPVS(gl3_main.gl3_viewcluster, worldmodel)

	# may have to combine two clusters because of solid water boundaries
	if gl3_main.gl3_viewcluster2 != gl3_main.gl3_viewcluster:

		# Q2PORT: the C ORs whole ints of the two PVS rows; bytes give the same
		# result. The C's rows sit in a static MAX_MAP_LEAFS / 8 byte buffer, so
		# it can read past a row's (numclusters + 7) >> 3 bytes; the port's
		# Mod_DecompressVis returns just the row, so both are padded with zeros
		# (those bits are past the last cluster and never tested)
		c = (worldmodel.numleafs + 31) // 32
		fatvis = bytearray(vis[:(worldmodel.numleafs + 7) // 8]) # memcpy(fatvis, vis, (gl3_worldmodel->numleafs + 7) / 8)
		fatvis.extend(b"\0" * (c * 4 - len(fatvis)))
		vis = gl3_model.GL3_Mod_ClusterPVS(gl3_main.gl3_viewcluster2, worldmodel)
		vis = bytes(vis) + b"\0" * max(0, c * 4 - len(vis))

		for i in range(c * 4):

			fatvis[i] |= vis[i]

		vis = fatvis

	for i in range(worldmodel.numleafs):

		leaf = worldmodel.leafs[i]

		cluster = leaf.cluster

		if cluster == -1:

			continue

		if vis[cluster >> 3] & (1 << (cluster & 7)):

			node = leaf # (mnode_t *)leaf

			while True:

				if node.visframe == gl3_main.gl3_visframecount:

					break

				node.visframe = gl3_main.gl3_visframecount
				node = node.parent

				if node is None:
					break
