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
 * Surface generation and drawing
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from client import ref
from client.refresh.gl1 import gl1_warp, gl1_image, gl1_main, gl1_light, gl1_lightmap, gl1_buffer, gl1_model
from client.refresh import ref_shared
from client.refresh.gl1.header import model
from client.refresh.files import surf as files_surf
from common import clientserver
from q2data import bsp as q2bsp
from common.header import shared
from common.shared import shared as shared_c

"""
#include <assert.h>

#include "header/local.h"
"""

# from header/local.h
BLOCK_WIDTH		= 128
BLOCK_HEIGHT	= 128
LIGHTMAP_BYTES	= 4
MAX_LIGHTMAPS	= 128
MAX_LIGHTMAP_COPIES = 3 # Meant for tile / deferred rendering platforms

GL_LIGHTMAP_FORMAT = GL.GL_RGBA

BACKFACE_EPSILON = 0.01

class gllightmapstate_t(object): # from header/local.h

	def __init__(self):

		self.current_lightmap_texture = 0 #int

		self.lightmap_surfaces = [[] for _ in range(MAX_LIGHTMAPS)] #msurface_t *[MAX_LIGHTMAPS], Q2PORT: each lightmapchain is a list

		self.allocated = [0] * BLOCK_WIDTH #int [BLOCK_WIDTH]

		# the lightmap texture data needs to be kept in
		# main memory so texsubimage can update properly
		self.lightmap_buffer = [None] * MAX_LIGHTMAPS #byte *[MAX_LIGHTMAPS]

class lmrect_t(object):

	def __init__(self):

		self.top, self.bottom, self.left, self.right = 0, 0, 0, 0 #int

	def copy(self): # struct assignment
		r = lmrect_t()
		r.top, r.bottom, r.left, r.right = self.top, self.bottom, self.left, self.right
		return r

c_visible_lightmaps = 0 #int
c_visible_textures = 0 #int
modelorg = np.zeros((3,), dtype=np.float32) #static vec3_t, relative to viewpoint
r_alpha_surfaces = [] #msurface_t *, Q2PORT: the texturechain is a list; the C prepends, so it is walked reversed()

gl_lms = gllightmapstate_t() #gllightmapstate_t
#extern int cur_lm_copy;

#void LM_InitBlock(void);
#void LM_UploadBlock(qboolean dynamic);
#qboolean LM_AllocBlock(int w, int h, int *x, int *y);

def R_DrawGLPoly(fa): #msurface_t * (static)

	#int i, nv;
	#float *v, scroll;

	p = fa.polys[0] # fa->polys
	nv = p.numverts

	if fa.texinfo.flags & shared.SURF_FLOWING:

		scroll = -64 * ((gl1_main.r_newrefdef.time / 40.0) - int(gl1_main.r_newrefdef.time / 40.0))

		if scroll == 0.0:

			scroll = -64.0

	else:

		scroll = 0.0

	gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_FAN, nv)

	for v in p.verts[:nv].tolist():

		gl1_buffer.GLBUFFER_VERTEX( v[0], v[1], v[2] )
		gl1_buffer.GLBUFFER_SINGLETEX( v[3] + scroll, v[4] )

def R_DrawTriangleOutlines(): #void (static)

	#int i, j;
	#glpoly_t *p;

	if not gl1_main.gl_showtris.value:

		return

	GL.glDisable(GL.GL_TEXTURE_2D)
	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glColor4f(1, 1, 1, 1)

	for i in range(MAX_LIGHTMAPS):

		#msurface_t *surf;

		for surf in reversed(gl_lms.lightmap_surfaces[i]):

			for p in surf.polys:

				for j in range(2, p.numverts):

					#GLfloat vtx[12];
					#unsigned int k;
					vtx = np.zeros((12,), dtype=np.float32)

					for k in range(3):

						vtx[0 + k] = p.verts[0][k]
						vtx[3 + k] = p.verts[j - 1][k]
						vtx[6 + k] = p.verts[j][k]
						vtx[9 + k] = p.verts[0][k]

					GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

					GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtx )
					GL.glDrawArrays( GL.GL_LINE_STRIP, 0, 4 )

					GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	GL.glEnable(GL.GL_DEPTH_TEST)
	GL.glEnable(GL.GL_TEXTURE_2D)

def R_DrawGLPolyChain(p, soffset, toffset): #glpoly_t * (Q2PORT: a list), float, float (static)

	# Q2PORT: the C points glVertexPointer and glTexCoordPointer into the
	# interleaved verts with a stride; PyOpenGL would copy a strided numpy view,
	# so the position and lightmap coordinates are passed as contiguous arrays
	if (soffset == 0) and (toffset == 0):

		for poly in p:

			#float *v;

			v = np.ascontiguousarray(poly.verts[:poly.numverts, 0:3])
			tex = np.ascontiguousarray(poly.verts[:poly.numverts, 5:7])

			GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
			GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )

			GL.glVertexPointer( 3, GL.GL_FLOAT, 0, v ) # VERTEXSIZE*sizeof(GLfloat), v
			GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex ) # VERTEXSIZE*sizeof(GLfloat), v+5
			GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, poly.numverts )

			GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
			GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	else:

		# workaround for lack of VLAs (=> our workaround uses alloca() which is bad in loops)

		for poly in p:

			#float *v;
			#int j;

			#YQ2_VLA(GLfloat, tex, 2*p->numverts);
			tex = np.empty((poly.numverts, 2), dtype=np.float32)

			#unsigned int index_tex = 0;

			# tex[index_tex++] = v [ 5 ] - soffset; tex[index_tex++] = v [ 6 ] - toffset;
			tex[:, 0] = poly.verts[:poly.numverts, 5] - soffset
			tex[:, 1] = poly.verts[:poly.numverts, 6] - toffset

			v = np.ascontiguousarray(poly.verts[:poly.numverts, 0:3]) # v = p->verts [ 0 ];

			GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
			GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )

			GL.glVertexPointer( 3, GL.GL_FLOAT, 0, v )
			GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex )
			GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, poly.numverts )

			GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
			GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

		#YQ2_VLAFREE( tex );

"""
 * This routine takes all the given light mapped surfaces
 * in the world and blends them into the framebuffer.
"""
def R_BlendLightmaps(currentmodel): #const model_t * (static)

	global c_visible_lightmaps

	#int i;
	#msurface_t *surf, *newdrawsurf = 0;

	# don't bother if we're set to fullbright or multitexture is enabled
	if gl1_main.gl_config.multitexture or gl1_main.r_fullbright.value or not gl1_main.r_worldmodel.lightdata:

		return

	# don't bother writing Z
	GL.glDepthMask(GL.GL_FALSE)

	# set the appropriate blending mode unless
	# we're only looking at the lightmaps.
	if not gl1_main.gl_lightmap.value:

		GL.glEnable(GL.GL_BLEND)

		if gl1_main.gl1_saturatelighting.value:

			GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE)

		else:

			GL.glBlendFunc(GL.GL_ZERO, GL.GL_SRC_COLOR)

	if currentmodel is gl1_main.r_worldmodel:

		c_visible_lightmaps = 0

	# render static lightmaps first
	for i in range(1, MAX_LIGHTMAPS):

		if gl_lms.lightmap_surfaces[i]:

			if currentmodel is gl1_main.r_worldmodel:

				c_visible_lightmaps += 1

			gl1_image.R_Bind(gl1_main.gl_state.lightmap_textures + i)

			for surf in reversed(gl_lms.lightmap_surfaces[i]):

				if surf.polys:

					# Apply overbright bits to the static lightmaps
					if gl1_main.gl1_overbrightbits.value:

						gl1_image.R_TexEnv(GL.GL_COMBINE)
						GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_RGB_SCALE, int(gl1_main.gl1_overbrightbits.value))

					R_DrawGLPolyChain(surf.polys, 0, 0)

	# render dynamic lightmaps
	if gl1_main.gl1_dynamic.value:

		gl1_lightmap.LM_InitBlock()

		gl1_image.R_Bind(gl1_main.gl_state.lightmap_textures + 0)

		if currentmodel is gl1_main.r_worldmodel:

			c_visible_lightmaps += 1

		# Q2PORT: the chain as a list in the C's order; newdrawsurf is an index into it
		chain = list(reversed(gl_lms.lightmap_surfaces[0]))
		newdrawsurf = 0

		for surf_i, surf in enumerate(chain):

			#int smax, tmax;
			#byte *base;

			smax = (surf.extents[0] >> 4) + 1
			tmax = (surf.extents[1] >> 4) + 1

			ok, surf.dlight_s, surf.dlight_t = gl1_lightmap.LM_AllocBlock(smax, tmax)
			if ok:

				base = (surf.dlight_t * BLOCK_WIDTH +
						surf.dlight_s) * LIGHTMAP_BYTES # base = gl_lms.lightmap_buffer[0] + ...

				gl1_light.R_BuildLightMap(surf, memoryview(gl_lms.lightmap_buffer[0])[base:], BLOCK_WIDTH * LIGHTMAP_BYTES)

			else:

				#msurface_t *drawsurf;

				# upload what we have so far
				gl1_lightmap.LM_UploadBlock(True)

				# draw all surfaces that use this lightmap
				for drawsurf in chain[newdrawsurf:surf_i]:

					if drawsurf.polys:

						# Apply overbright bits to the dynamic lightmaps
						if gl1_main.gl1_overbrightbits.value:

							gl1_image.R_TexEnv(GL.GL_COMBINE)
							GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_RGB_SCALE, int(gl1_main.gl1_overbrightbits.value))

						R_DrawGLPolyChain(drawsurf.polys,
								(drawsurf.light_s - drawsurf.dlight_s) * (1.0 / BLOCK_WIDTH),
								(drawsurf.light_t - drawsurf.dlight_t) * (1.0 / BLOCK_HEIGHT))

				newdrawsurf = surf_i # newdrawsurf = drawsurf;

				# clear the block
				gl1_lightmap.LM_InitBlock()

				# try uploading the block now
				ok, surf.dlight_s, surf.dlight_t = gl1_lightmap.LM_AllocBlock(smax, tmax)
				if not ok:

					clientserver.Com_Error(shared.ERR_FATAL,
							"{}: Consecutive calls to LM_AllocBlock({},{}) failed (dynamic)\n".format(
							"R_BlendLightmaps", smax, tmax))

				base = (surf.dlight_t * BLOCK_WIDTH +
						surf.dlight_s) * LIGHTMAP_BYTES

				gl1_light.R_BuildLightMap(surf, memoryview(gl_lms.lightmap_buffer[0])[base:], BLOCK_WIDTH * LIGHTMAP_BYTES)

		# draw remainder of dynamic lightmaps that haven't been uploaded yet
		if chain[newdrawsurf:]: # if (newdrawsurf)

			gl1_lightmap.LM_UploadBlock(True)

		for surf in chain[newdrawsurf:]:

			if surf.polys:

				# Apply overbright bits to the remainder lightmaps
				if gl1_main.gl1_overbrightbits.value:

					gl1_image.R_TexEnv(GL.GL_COMBINE)
					GL.glTexEnvi(GL.GL_TEXTURE_ENV, GL.GL_RGB_SCALE, int(gl1_main.gl1_overbrightbits.value))

				R_DrawGLPolyChain(surf.polys,
						(surf.light_s - surf.dlight_s) * (1.0 / BLOCK_WIDTH),
						(surf.light_t - surf.dlight_t) * (1.0 / BLOCK_HEIGHT))

	# restore state
	GL.glDisable(GL.GL_BLEND)
	GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
	GL.glDepthMask(GL.GL_TRUE)

def R_RenderBrushPoly(fa): #msurface_t * (static)

	#int maps;
	#qboolean is_dynamic = false;
	is_dynamic = False

	gl1_main.c_brush_polys += 1

	if fa.flags & model.SURF_DRAWTURB:

		gl1_warp.R_EmitWaterPolys(fa)
		return

	R_DrawGLPoly(fa)

	if gl1_main.gl_config.multitexture:

		return	# lighting already done at this point for mtex

	# check for lightmap modification
	dynamic = False # Q2PORT: the C's goto dynamic
	maps = 0
	while maps < q2bsp.MAX_LIGHTMAPS and fa.styles[maps] != 255:

		if (gl1_main.r_newrefdef.lightstyles[fa.styles[maps]].white !=
			fa.cached_light[maps]):

			dynamic = True
			break # goto dynamic;

		maps += 1

	# dynamic this frame or dynamic previously
	if dynamic or fa.dlightframe == gl1_main.r_framecount:

	#dynamic:

		if gl1_main.gl1_dynamic.value:

			if not (fa.texinfo.flags &
				  (shared.SURF_SKY | shared.SURF_TRANS33 |
				   shared.SURF_TRANS66 | shared.SURF_WARP)):

				is_dynamic = True

	if is_dynamic:

		if (maps < q2bsp.MAX_LIGHTMAPS and
			((fa.styles[maps] >= 32) or
			 (fa.styles[maps] == 0)) and
			  (fa.dlightframe != gl1_main.r_framecount)):

			#unsigned temp[34 * 34];
			#int smax, tmax;

			smax = (fa.extents[0] >> 4) + 1
			tmax = (fa.extents[1] >> 4) + 1
			temp = bytearray(34 * 34 * 4)

			gl1_light.R_BuildLightMap(fa, temp, smax * 4)
			gl1_light.R_SetCacheState(fa)

			gl1_image.R_Bind(gl1_main.gl_state.lightmap_textures + fa.lightmaptexturenum)

			GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, fa.light_s, fa.light_t,
					smax, tmax, GL_LIGHTMAP_FORMAT, GL.GL_UNSIGNED_BYTE, bytes(temp[:smax * tmax * 4]))

			gl_lms.lightmap_surfaces[fa.lightmaptexturenum].append(fa) # fa->lightmapchain = ...; ... = fa;

		else:

			gl_lms.lightmap_surfaces[0].append(fa)

	else:

		gl_lms.lightmap_surfaces[fa.lightmaptexturenum].append(fa)

"""
 * Draw water surfaces and windows.
 * The BSP tree is waled front to back, so unwinding the chain
 * of alpha_surfaces will draw back to front, giving proper ordering.
"""
def R_DrawAlphaSurfaces(): #void

	#msurface_t *s;
	#float alpha;

	# go back to the world matrix
	GL.glLoadMatrixf(gl1_main.r_world_matrix)

	GL.glEnable(GL.GL_BLEND)
	gl1_image.R_TexEnv(GL.GL_MODULATE)

	for s in reversed(r_alpha_surfaces):

		gl1_main.c_brush_polys += 1

		if s.texinfo.flags & shared.SURF_TRANS33:

			alpha = 0.33

		elif s.texinfo.flags & shared.SURF_TRANS66:

			alpha = 0.66

		else:

			alpha = 1.0

		gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_alpha, s.texinfo.image.texnum, 0, 0, alpha)

		if s.flags & model.SURF_DRAWTURB:

			gl1_warp.R_EmitWaterPolys(s)

		else:

			R_DrawGLPoly(s)

	gl1_buffer.R_ApplyGLBuffer()	# Flush the last batched array

	gl1_image.R_TexEnv(GL.GL_REPLACE)
	GL.glColor4f(1, 1, 1, 1)
	GL.glDisable(GL.GL_BLEND)

	r_alpha_surfaces.clear() # r_alpha_surfaces = NULL;

def R_RenderLightmappedPoly(surf): #msurface_t * (static)

	#const int nv = surf->polys->numverts;
	#int i;
	#float scroll;
	#float *v;
	p = surf.polys[0]
	nv = p.numverts

	gl1_main.c_brush_polys += 1

	if surf.texinfo.flags & shared.SURF_FLOWING:

		scroll = -64 * ((gl1_main.r_newrefdef.time / 40.0) - int(gl1_main.r_newrefdef.time / 40.0))

		if scroll == 0.0:

			scroll = -64.0

	else:

		scroll = 0.0

	gl1_buffer.R_SetBufferIndices(GL.GL_TRIANGLE_FAN, nv)

	for v in p.verts[:nv].tolist():

		gl1_buffer.GLBUFFER_VERTEX( v[0], v[1], v[2] )
		gl1_buffer.GLBUFFER_MULTITEX( v[3] + scroll, v[4], v[5], v[6] )

# Add "adding" area to "obj"
def R_JoinAreas(adding, obj): #lmrect_t *, lmrect_t * (static)

	if adding.top < obj.top:

		obj.top = adding.top

	if adding.bottom > obj.bottom:

		obj.bottom = adding.bottom

	if adding.left < obj.left:

		obj.left = adding.left

	if adding.right > obj.right:

		obj.right = adding.right

lmchange = [[lmrect_t() for _ in range(MAX_LIGHTMAP_COPIES)] for _ in range(MAX_LIGHTMAPS)] #static lmrect_t [MAX_LIGHTMAPS][MAX_LIGHTMAP_COPIES], in R_RegenAllLightmaps
altered = [[False] * MAX_LIGHTMAP_COPIES for _ in range(MAX_LIGHTMAPS)] #static qboolean [MAX_LIGHTMAPS][MAX_LIGHTMAP_COPIES], in R_RegenAllLightmaps

# Upload dynamic lights to each lightmap texture (multitexture path only)
def R_RegenAllLightmaps(): #void (static)

	#int i, lmtex;
	#ifndef YQ2_GL1_GLES
	pixelstore_set = False #qboolean
	#endif

	if not gl1_main.gl_config.multitexture or gl1_main.r_fullbright.value or not gl1_main.gl1_dynamic.value:

		return

	if gl1_main.gl_config.tilerendering:

		gl1_buffer.cur_lm_copy = (gl1_buffer.cur_lm_copy + 1) % MAX_LIGHTMAP_COPIES	# select the next lightmap copy
		lmtex = MAX_LIGHTMAPS * gl1_buffer.cur_lm_copy	# ...and its corresponding texture

	else:

		lmtex = 0

	for i in range(1, MAX_LIGHTMAPS):

		#lmrect_t current, best;
		#msurface_t *surf;
		#byte *base;
		#qboolean affected_lightmap;
		current = lmrect_t()
		best = lmrect_t()

		if not gl_lms.lightmap_surfaces[i] or not gl_lms.lightmap_buffer[i]:

			continue

		affected_lightmap = False
		best.top = BLOCK_HEIGHT
		best.left = BLOCK_WIDTH
		best.bottom = best.right = 0

		for surf in reversed(gl_lms.lightmap_surfaces[i]):

			#int map;

			if surf.texinfo.flags & (shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP):

				continue

			# Any dynamic lights on this surface?
			dynamic_surf = False # Q2PORT: the C's goto dynamic_surf
			map = 0
			while map < q2bsp.MAX_LIGHTMAPS and surf.styles[map] != 255:

				if gl1_main.r_newrefdef.lightstyles[surf.styles[map]].white != surf.cached_light[map]:

					dynamic_surf = True
					break # goto dynamic_surf;

				map += 1

			# Surface is considered to have dynamic lights if it had them in the previous frame
			if not dynamic_surf and surf.dlightframe != gl1_main.r_framecount and not surf.dirty_lightmap:

				continue	# no dynamic lights affect this surface in this frame

	#dynamic_surf:
			affected_lightmap = True

			current.left = surf.light_s
			current.right = surf.light_s + (surf.extents[0] >> 4) + 1	# + smax
			current.top = surf.light_t
			current.bottom = surf.light_t + (surf.extents[1] >> 4) + 1	# + tmax

			base = (current.top * BLOCK_WIDTH + current.left) * LIGHTMAP_BYTES # base = gl_lms.lightmap_buffer[i] + ...

			gl1_light.R_BuildLightMap(surf, memoryview(gl_lms.lightmap_buffer[i])[base:], BLOCK_WIDTH * LIGHTMAP_BYTES)

			surf.dirty_lightmap = (surf.dlightframe == gl1_main.r_framecount)
			if not surf.dirty_lightmap or gl1_main.gl_config.tilerendering:

				map = 0
				while map < q2bsp.MAX_LIGHTMAPS and surf.styles[map] != 255:

					if (surf.styles[map] >= 32) or (surf.styles[map] == 0):

						gl1_light.R_SetCacheState(surf)
						break

					map += 1

			R_JoinAreas(current, best)

		if not gl1_main.gl_config.tilerendering and not affected_lightmap:

			continue

		if gl1_main.gl_config.tilerendering:

			# Add all the changes that have happened in the last few frames,
			# at least just for consistency between them.
			apply_changes = affected_lightmap #qboolean
			current = best.copy()		# save state for next frames... +

			for k in range(MAX_LIGHTMAP_COPIES):

				if altered[i][k]:

					apply_changes = True
					R_JoinAreas(lmchange[i][k], best)

			altered[i][gl1_buffer.cur_lm_copy] = affected_lightmap
			if affected_lightmap:

				lmchange[i][gl1_buffer.cur_lm_copy] = current	# + ...here

			if not apply_changes:

				continue

		#ifndef YQ2_GL1_GLES
		if not pixelstore_set:

			GL.glPixelStorei(GL.GL_UNPACK_ROW_LENGTH, BLOCK_WIDTH)
			pixelstore_set = True

		#endif

		# upload changes
		#ifdef YQ2_GL1_GLES
		#else
		base = (best.top * BLOCK_WIDTH + best.left) * LIGHTMAP_BYTES # base = gl_lms.lightmap_buffer[i] + ...

		gl1_image.R_Bind(gl1_main.gl_state.lightmap_textures + i + lmtex)

		GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, best.left, best.top,
			best.right - best.left, best.bottom - best.top,
			GL_LIGHTMAP_FORMAT, GL.GL_UNSIGNED_BYTE, bytes(gl_lms.lightmap_buffer[i][base:]))
		#endif

	#ifndef YQ2_GL1_GLES
	if pixelstore_set:

		GL.glPixelStorei(GL.GL_UNPACK_ROW_LENGTH, 0)

	#endif

def R_DrawTextureChains(): #void (static)

	global c_visible_textures

	#int i;
	#msurface_t *s;
	#image_t *image;

	c_visible_textures = 0

	if not gl1_main.gl_config.multitexture:	# classic path

		for i in range(gl1_image.numgltextures):

			image = gl1_image.gltextures[i]

			if not image.registration_sequence:

				continue

			if not image.texturechain:

				continue

			c_visible_textures += 1

			for s in reversed(image.texturechain):

				gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_singletex, image.texnum, 0, s.flags, 1)
				R_RenderBrushPoly(s)

			image.texturechain = []

		gl1_buffer.R_ApplyGLBuffer()	# Flush the last batched array

	else:	# multitexture

		for i in range(gl1_image.numgltextures):

			image = gl1_image.gltextures[i]

			if not image.registration_sequence or not image.texturechain:

				continue

			c_visible_textures += 1

			for s in reversed(image.texturechain):

				if not (s.flags & model.SURF_DRAWTURB):

					gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_mtex, image.texnum, s.lightmaptexturenum, 0, 1)
					R_RenderLightmappedPoly(s)

		gl1_buffer.R_ApplyGLBuffer()

		gl1_image.R_EnableMultitexture(False)	# force disabling, SURF_DRAWTURB surfaces may not exist

		for i in range(gl1_image.numgltextures):

			image = gl1_image.gltextures[i]

			if not image.registration_sequence or not image.texturechain:

				continue

			for s in reversed(image.texturechain):

				if s.flags & model.SURF_DRAWTURB:

					gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_singletex, image.texnum, 0, s.flags, 1)
					R_RenderBrushPoly(s)

			image.texturechain = []

		gl1_buffer.R_ApplyGLBuffer()

def R_DrawInlineBModel(currententity, currentmodel): #entity_t *, const model_t * (static)

	#int i, k;
	#cplane_t *pplane;
	#float dot;
	#msurface_t *psurf;
	#dlight_t *lt;
	#image_t *image;

	# calculate dynamic lighting for bmodel
	if not gl1_main.gl_config.multitexture and not gl1_main.gl1_flashblend.value:

		for k in range(gl1_main.r_newrefdef.num_dlights):

			lt = gl1_main.r_newrefdef.dlights[k]
			files_surf.R_MarkLights(lt, 1 << k,
				currentmodel.nodes[currentmodel.firstnode], # currentmodel->nodes + currentmodel->firstnode
				gl1_light.r_dlightframecount, gl1_light.R_MarkSurfaceLights)

	if currententity.flags & shared.RF_TRANSLUCENT:

		GL.glEnable(GL.GL_BLEND)
		GL.glColor4f(1, 1, 1, 0.25)
		gl1_image.R_TexEnv(GL.GL_MODULATE)

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
				r_alpha_surfaces.append(psurf) # psurf->texturechain = r_alpha_surfaces; r_alpha_surfaces = psurf;

			else:

				image = files_surf.R_TextureAnimation(currententity, psurf.texinfo)

				if gl1_main.gl_config.multitexture and not (psurf.flags & model.SURF_DRAWTURB):

					# Dynamic lighting already generated in R_GetBrushesLighting()
					gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_mtex, image.texnum, psurf.lightmaptexturenum, 0, 1)
					R_RenderLightmappedPoly(psurf)

				else:

					gl1_buffer.R_UpdateGLBuffer(gl1_buffer.buf_singletex, image.texnum, 0, psurf.flags, 1)
					R_RenderBrushPoly(psurf)

	gl1_buffer.R_ApplyGLBuffer()

	if not (currententity.flags & shared.RF_TRANSLUCENT):

		R_BlendLightmaps(currentmodel)

	else:

		GL.glDisable(GL.GL_BLEND)
		GL.glColor4f(1, 1, 1, 1)
		gl1_image.R_TexEnv(GL.GL_REPLACE)

def R_DrawBrushModel(currententity, currentmodel): #entity_t *, const model_t *

	#vec3_t mins, maxs;
	#int i;
	#qboolean rotated;
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)

	if currentmodel.nummodelsurfaces == 0:

		return

	gl1_main.gl_state.currenttextures[0] = gl1_main.gl_state.currenttextures[1] = -1

	if currententity.angles[0] or currententity.angles[1] or currententity.angles[2]:

		rotated = True

		for i in range(3):

			mins[i] = currententity.origin[i] - currentmodel.radius
			maxs[i] = currententity.origin[i] + currentmodel.radius

	else:

		rotated = False
		shared.VectorAdd(currententity.origin, currentmodel.mins, mins)
		shared.VectorAdd(currententity.origin, currentmodel.maxs, maxs)

	if gl1_main.r_cull.value and files_surf.R_CullBox(mins, maxs, gl1_main.frustum):

		return

	if gl1_main.gl_zfix.value:

		GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)

	GL.glColor4f(1, 1, 1, 1)
	gl_lms.lightmap_surfaces = [[] for _ in range(MAX_LIGHTMAPS)] # memset(gl_lms.lightmap_surfaces, 0, sizeof(gl_lms.lightmap_surfaces));

	shared.VectorSubtract(gl1_main.r_newrefdef.vieworg, currententity.origin, modelorg)

	if rotated:

		#vec3_t temp;
		#vec3_t forward, right, up;
		forward = np.zeros((3,), dtype=np.float32)
		right = np.zeros((3,), dtype=np.float32)
		up = np.zeros((3,), dtype=np.float32)

		temp = modelorg.copy() # VectorCopy(modelorg, temp);
		shared_c.AngleVectors(currententity.angles, forward, right, up)
		modelorg[0] = shared.DotProduct(temp, forward)
		modelorg[1] = -shared.DotProduct(temp, right)
		modelorg[2] = shared.DotProduct(temp, up)

	GL.glPushMatrix()
	currententity.angles[0] = -currententity.angles[0]
	currententity.angles[2] = -currententity.angles[2]
	gl1_main.R_RotateForEntity(currententity)
	currententity.angles[0] = -currententity.angles[0]
	currententity.angles[2] = -currententity.angles[2]

	if gl1_main.gl_lightmap.value:

		gl1_image.R_TexEnv(GL.GL_REPLACE)

	else:

		gl1_image.R_TexEnv(GL.GL_MODULATE)

	R_DrawInlineBModel(currententity, currentmodel)

	GL.glPopMatrix()

	if gl1_main.gl_zfix.value:

		GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

def R_RecursiveWorldNode(currententity, node): #entity_t *, mnode_t * (static)

	#int c, side, sidebit;
	#cplane_t *plane;
	#msurface_t *surf, **mark;
	#mleaf_t *pleaf;
	#float dot;
	#image_t *image;

	if node.contents == shared.CONTENTS_SOLID:

		return # solid

	if node.visframe != gl1_main.r_visframecount:

		return

	if gl1_main.r_cull.value and files_surf.R_CullBox(node.minmaxs[0:3], node.minmaxs[3:6], gl1_main.frustum):

		return

	# if a leaf node, draw stuff
	if node.contents != ref_shared.CONTENTS_NODE:

		pleaf = node

		# check for door connected areas
		if not files_surf.R_AreaVisible(gl1_main.r_newrefdef.areabits, pleaf):
			return	# not visible

		for mark in pleaf.firstmarksurface[:pleaf.nummarksurfaces]:

			mark.visframe = gl1_main.r_framecount

		return

	# node is just a decision point, so go down the apropriate
	# sides find which side of the node we are on
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
	R_RecursiveWorldNode(currententity, node.children[side])

	# draw stuff
	surfaces = gl1_main.r_worldmodel.surfaces
	for surf in surfaces[node.firstsurface:node.firstsurface + node.numsurfaces]:

		if surf.visframe != gl1_main.r_framecount:

			continue

		if (surf.flags & model.SURF_PLANEBACK) != sidebit:

			continue # wrong side

		if surf.texinfo.flags & shared.SURF_SKY:

			# just adds to visible sky bounds
			gl1_warp.R_AddSkySurface(surf)

		elif surf.texinfo.flags & (shared.SURF_TRANS33 | shared.SURF_TRANS66):

			# add to the translucent chain
			r_alpha_surfaces.append(surf) # surf->texturechain = r_alpha_surfaces; r_alpha_surfaces = surf;
			surf.texinfo.image = files_surf.R_TextureAnimation(currententity, surf.texinfo)

		else:

			# the polygon is visible, so add it to the texture sorted chain
			image = files_surf.R_TextureAnimation(currententity, surf.texinfo)
			image.texturechain.append(surf) # surf->texturechain = image->texturechain; image->texturechain = surf;

			if gl1_main.gl_config.multitexture and not (surf.texinfo.flags & shared.SURF_WARP):	# needed for R_RegenAllLightmaps()

				gl_lms.lightmap_surfaces[surf.lightmaptexturenum].append(surf)

	# recurse down the back side
	R_RecursiveWorldNode(currententity, node.children[1 - side]) # !side

"""
 * This is for the RegenAllLightmaps() function to be able to regenerate
 * lighting not only for the world, but also for the brushes in the entity list.
 * Logic extracted from R_DrawBrushModel() & R_DrawInlineBModel().
"""
def R_GetBrushesLighting(): #void (static)

	#int i, k;
	#vec3_t mins, maxs;
	#msurface_t *surf;
	#cplane_t *pplane;
	#dlight_t *lt;
	#float dot;
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)

	if not gl1_main.gl_config.multitexture or not gl1_main.r_drawentities.value or gl1_main.gl1_flashblend.value:

		return

	for i in range(gl1_main.r_newrefdef.num_entities):

		currententity = gl1_main.r_newrefdef.entities[i]

		if currententity.flags & shared.RF_BEAM:

			continue

		currentmodel = currententity.model

		if not currentmodel or currentmodel.type != model.modtype_t.mod_brush or currentmodel.nummodelsurfaces == 0:

			continue

		# from R_DrawBrushModel()
		if currententity.angles[0] or currententity.angles[1] or currententity.angles[2]:

			for k in range(3):

				mins[k] = currententity.origin[k] - currentmodel.radius
				maxs[k] = currententity.origin[k] + currentmodel.radius

		else:

			shared.VectorAdd(currententity.origin, currentmodel.mins, mins)
			shared.VectorAdd(currententity.origin, currentmodel.maxs, maxs)

		if gl1_main.r_cull.value and files_surf.R_CullBox(mins, maxs, gl1_main.frustum):

			continue

		# from R_DrawInlineBModel()
		for k in range(gl1_main.r_newrefdef.num_dlights):

			lt = gl1_main.r_newrefdef.dlights[k]
			files_surf.R_MarkLights(lt, 1 << k,
				currentmodel.nodes[currentmodel.firstnode], # currentmodel->nodes + currentmodel->firstnode
				gl1_light.r_dlightframecount, gl1_light.R_MarkSurfaceLights)

		for k in range(currentmodel.nummodelsurfaces):

			surf = currentmodel.surfaces[currentmodel.firstmodelsurface + k]

			if (surf.texinfo.flags & (shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP)
				or surf.flags & model.SURF_DRAWTURB or surf.lmchain_frame == gl1_main.r_framecount):

				continue	# either not affected by light, or already in the chain

			# find which side of the node we are on
			pplane = surf.plane
			dot = shared.DotProduct(modelorg, pplane.normal) - pplane.dist

			if (((surf.flags & model.SURF_PLANEBACK) and (dot < -BACKFACE_EPSILON)) or
				(not (surf.flags & model.SURF_PLANEBACK) and (dot > BACKFACE_EPSILON))):

				surf.lmchain_frame = gl1_main.r_framecount	# don't add this twice to the chain
				gl_lms.lightmap_surfaces[surf.lightmaptexturenum].append(surf)

def R_DrawWorld(): #void

	#entity_t ent;

	if not gl1_main.r_drawworld.value:

		return

	if gl1_main.r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:

		return

	shared.VectorCopy(gl1_main.r_newrefdef.vieworg, modelorg)

	# auto cycle the world frame for texture animation
	ent = ref.entity_t() # memset(&ent, 0, sizeof(ent));
	ent.frame = int(gl1_main.r_newrefdef.time * 2)

	gl1_main.gl_state.currenttextures[0] = gl1_main.gl_state.currenttextures[1] = -1

	GL.glColor4f(1, 1, 1, 1)
	gl_lms.lightmap_surfaces = [[] for _ in range(MAX_LIGHTMAPS)] # memset(gl_lms.lightmap_surfaces, 0, sizeof(gl_lms.lightmap_surfaces));

	gl1_warp.R_ClearSkyBox()
	R_RecursiveWorldNode(ent, gl1_main.r_worldmodel.nodes[0]) # r_worldmodel->nodes
	R_GetBrushesLighting()
	R_RegenAllLightmaps()
	R_DrawTextureChains()
	R_BlendLightmaps(gl1_main.r_worldmodel)
	gl1_warp.R_DrawSkyBox()
	R_DrawTriangleOutlines()

"""
 * Mark the leaves and nodes that are
 * in the PVS for the current cluster
"""
def R_MarkLeaves(): #void

	#const byte *vis;
	#YQ2_ALIGNAS_TYPE(int) byte fatvis[MAX_MAP_LEAFS / 8];
	#mnode_t *node;
	#int i, c;
	#mleaf_t *leaf;
	#int cluster;
	r_worldmodel = gl1_main.r_worldmodel

	if ((gl1_main.r_oldviewcluster == gl1_main.r_viewcluster) and
		(gl1_main.r_oldviewcluster2 == gl1_main.r_viewcluster2) and
		not gl1_main.r_novis.value and
		(gl1_main.r_viewcluster != -1)):

		return

	# development aid to let you run around
	# and see exactly where the pvs ends
	if gl1_main.r_lockpvs.value:

		return

	gl1_main.r_visframecount += 1
	gl1_main.r_oldviewcluster = gl1_main.r_viewcluster
	gl1_main.r_oldviewcluster2 = gl1_main.r_viewcluster2

	if gl1_main.r_novis.value or (gl1_main.r_viewcluster == -1) or not r_worldmodel.vis:

		# mark everything
		for i in range(r_worldmodel.numleafs):

			r_worldmodel.leafs[i].visframe = gl1_main.r_visframecount

		for i in range(r_worldmodel.numnodes):

			r_worldmodel.nodes[i].visframe = gl1_main.r_visframecount

		return

	vis = gl1_model.Mod_ClusterPVS(gl1_main.r_viewcluster, r_worldmodel)

	# may have to combine two clusters because of solid water boundaries
	if gl1_main.r_viewcluster2 != gl1_main.r_viewcluster:

		fatvis = bytearray(q2bsp.MAX_MAP_LEAFS // 8)
		n = (r_worldmodel.numleafs + 7) // 8
		fatvis[:n] = vis[:n] # memcpy(fatvis, vis, (r_worldmodel->numleafs + 7) / 8);
		vis = gl1_model.Mod_ClusterPVS(gl1_main.r_viewcluster2, r_worldmodel)
		c = (r_worldmodel.numleafs + 31) // 32

		# ((int *)fatvis)[i] |= ((int *)vis)[i]; Q2PORT: OR'ing the bytes gives the same
		for i in range(min(c * 4, len(vis))):

			fatvis[i] |= vis[i]

		vis = fatvis

	for i in range(r_worldmodel.numleafs):

		leaf = r_worldmodel.leafs[i]
		cluster = leaf.cluster

		if cluster == -1:

			continue

		if vis[cluster >> 3] & (1 << (cluster & 7)):

			node = leaf # (mnode_t *)leaf;

			while True:

				if node.visframe == gl1_main.r_visframecount:

					break

				node.visframe = gl1_main.r_visframecount
				node = node.parent

				if not node:

					break

