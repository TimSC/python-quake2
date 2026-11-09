"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

Lightmap handling
#include "header/local.h"
"""
from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from client import ref
from client.refresh.gl1 import gl1_image, gl1_light, gl1_main, gl1_surf
from client.refresh.gl1.header import model
from common.header import files as files_h
from common.header import shared

# Meant for tile / deferred rendering platforms
MAX_LIGHTMAP_COPIES = 3

BLOCK_WIDTH	= 128
BLOCK_HEIGHT	= 128
LIGHTMAP_BYTES = 4
MAX_LIGHTMAPS = 128

GL_LIGHTMAP_FORMAT = GL.GL_RGBA


"""
================
LM_FreeLightmapBuffers
================
"""
def LM_FreeLightmapBuffers():

	for i in range(MAX_LIGHTMAPS):

		if gl1_surf.gl_lms.lightmap_buffer[i]:

			# the bytearrays are garbage-collected in Python
			pass

		gl1_surf.gl_lms.lightmap_buffer[i] = None


"""
================
LM_AllocLightmapBuffer
================
"""
def LM_AllocLightmapBuffer(buffer, clean): #int, qboolean

	lightmap_size = BLOCK_WIDTH * BLOCK_HEIGHT * LIGHTMAP_BYTES

	if not gl1_surf.gl_lms.lightmap_buffer[buffer]:

		gl1_surf.gl_lms.lightmap_buffer[buffer] = bytearray(lightmap_size)

	if not gl1_surf.gl_lms.lightmap_buffer[buffer]:

		gl1_main.ri.Sys_Error (shared.ERR_FATAL, "{}: Could not allocate lightmap buffer {}\n".format("LM_AllocLightmapBuffer", buffer) )

	if clean:

		for i in range(lightmap_size):
			gl1_surf.gl_lms.lightmap_buffer[buffer][i] = 0


"""
================
LM_InitBlock
================
"""
def LM_InitBlock():

	gl1_surf.gl_lms.allocated = [0] * BLOCK_WIDTH # memset( gl_lms.allocated, 0, sizeof(gl_lms.allocated) );

	if gl1_main.gl_config.multitexture:

		LM_AllocLightmapBuffer(gl1_surf.gl_lms.current_lightmap_texture, False)


"""
================
LM_UploadBlock
================
"""
def LM_UploadBlock(dynamic): #qboolean


	#int height, i;
	height = 0

	texture = 0 if dynamic else gl1_surf.gl_lms.current_lightmap_texture
	#
	#FIXME Simplified while porting: the classic dynamic lightmap path
	#(R_BlendLightmaps) writes into buffer 0, so the dynamic upload must
	#read buffer 0.  Yamagi's R_RegenAllLightmaps (not ported) writes to
	#buffer[current] and is what the literal C assumes.
	#
	buffer = 0 if dynamic else (gl1_surf.gl_lms.current_lightmap_texture if gl1_main.gl_config.multitexture else 0)

	gl1_image.R_Bind( gl1_main.gl_state.lightmap_textures + texture )
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

	if dynamic:

		for i in range(BLOCK_WIDTH):

			if gl1_surf.gl_lms.allocated[i] > height:

				height = gl1_surf.gl_lms.allocated[i]

		GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, BLOCK_WIDTH,
				height, GL_LIGHTMAP_FORMAT, GL.GL_UNSIGNED_BYTE,
				bytes(gl1_surf.gl_lms.lightmap_buffer[buffer]))

	else:
		GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL_LIGHTMAP_FORMAT,
				BLOCK_WIDTH, BLOCK_HEIGHT,
				0, GL_LIGHTMAP_FORMAT, GL.GL_UNSIGNED_BYTE,
				bytes(gl1_surf.gl_lms.lightmap_buffer[buffer]))

		if gl1_main.gl_config.tilerendering and buffer != 0:

			# Upload to all lightmap copies
			for i in range(1, MAX_LIGHTMAP_COPIES):

				gl1_image.R_Bind(gl1_main.gl_state.lightmap_textures + (MAX_LIGHTMAPS * i) + texture)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
				GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL_LIGHTMAP_FORMAT,
						BLOCK_WIDTH, BLOCK_HEIGHT,
						0, GL_LIGHTMAP_FORMAT, GL.GL_UNSIGNED_BYTE,
						bytes(gl1_surf.gl_lms.lightmap_buffer[buffer]))

		gl1_surf.gl_lms.current_lightmap_texture += 1
		if gl1_surf.gl_lms.current_lightmap_texture == MAX_LIGHTMAPS:

			gl1_main.ri.Sys_Error (shared.ERR_DROP, "{}: MAX_LIGHTMAPS exceeded\n".format("LM_UploadBlock") )


"""
================
LM_AllocBlock

returns a texture number and the position inside it
================
"""
def LM_AllocBlock (w, h): #int, int (returns qboolean, int x, int y)

	#int i, j, best, best2;
	x = y = 0

	best = BLOCK_HEIGHT

	for i in range(BLOCK_WIDTH-w):

		best2 = 0

		for j in range(w):

			if gl1_surf.gl_lms.allocated[i+j] >= best:
				break
			if gl1_surf.gl_lms.allocated[i+j] > best2:
				best2 = gl1_surf.gl_lms.allocated[i+j]

		else: # j == w
			# this is a valid spot
			x = i
			y = best = best2

	if best + h > BLOCK_HEIGHT:
		return False, x, y

	for i in range(w):
		gl1_surf.gl_lms.allocated[x + i] = best + h

	return True, x, y


"""
================
LM_BuildPolygonFromSurface
================
"""
def LM_BuildPolygonFromSurface(currentmodel, fa): #model_t *, msurface_t *

	"""
	int i, lindex, lnumverts;
	medge_t		*pedges, *r_pedge;
	float		*vec;
	float		s, t;
	glpoly_t	*poly;
	vec3_t		total;
	"""
	total = np.zeros((3,), dtype=np.float32)

	# reconstruct the polygon
	pedges = currentmodel.edges
	lnumverts = fa.numedges

	shared.VectorClear (total)
	#
	# draw texture
	#
	poly = model.glpoly_t() # Hunk_Alloc (sizeof(glpoly_t) + (lnumverts-4) * VERTEXSIZE*sizeof(float));
	poly.verts = np.zeros((lnumverts, model.VERTEXSIZE), dtype=np.float32)
	poly.flags = fa.flags
	fa.polys.insert(0, poly) # poly->next = fa->polys; fa->polys = poly;
	poly.numverts = lnumverts

	for i in range(lnumverts):

		lindex = int(currentmodel.surfedges[fa.firstedge + i])

		if lindex > 0:

			r_pedge = pedges[lindex]
			vec = currentmodel.vertexes[r_pedge.v[0]].position

		else:

			r_pedge = pedges[-lindex]
			vec = currentmodel.vertexes[r_pedge.v[1]].position

		s = shared.DotProduct (vec, fa.texinfo.vecs[0]) + fa.texinfo.vecs[0][3]
		s /= fa.texinfo.image.width

		t = shared.DotProduct (vec, fa.texinfo.vecs[1]) + fa.texinfo.vecs[1][3]
		t /= fa.texinfo.image.height

		shared.VectorAdd (total, vec, total)
		poly.verts[i][:3] = vec # VectorCopy (vec, poly->verts[i]);
		poly.verts[i][3] = s
		poly.verts[i][4] = t

		#
		# lightmap texture coordinates
		#
		s = shared.DotProduct (vec, fa.texinfo.vecs[0]) + fa.texinfo.vecs[0][3]
		s -= fa.texturemins[0]
		s += fa.light_s*16
		s += 8
		s /= BLOCK_WIDTH*16 #fa->texinfo->texture->width;

		t = shared.DotProduct (vec, fa.texinfo.vecs[1]) + fa.texinfo.vecs[1][3]
		t -= fa.texturemins[1]
		t += fa.light_t*16
		t += 8
		t /= BLOCK_HEIGHT*16 #fa->texinfo->texture->height;

		poly.verts[i][5] = s
		poly.verts[i][6] = t

	poly.numverts = lnumverts


"""
================
LM_CreateSurfaceLightmap
================
"""
def LM_CreateSurfaceLightmap (surf): #msurface_t *

	#int smax, tmax, buffer;
	#byte	*base;

	if surf.flags & (model.SURF_DRAWSKY|model.SURF_DRAWTURB):
		return

	smax = (surf.extents[0]>>4)+1
	tmax = (surf.extents[1]>>4)+1

	ok, surf.light_s, surf.light_t = LM_AllocBlock( smax, tmax )
	if not ok:

		LM_UploadBlock( False )
		LM_InitBlock()

		ok, surf.light_s, surf.light_t = LM_AllocBlock( smax, tmax )
		if not ok:

			gl1_main.ri.Sys_Error( shared.ERR_FATAL, "{}: Consecutive calls to LM_AllocBlock({},{}) failed\n".format("LM_CreateSurfaceLightmap", smax, tmax) )

	surf.lightmaptexturenum = gl1_surf.gl_lms.current_lightmap_texture
	buffer = surf.lightmaptexturenum if gl1_main.gl_config.multitexture else 0

	base = (surf.light_t * BLOCK_WIDTH + surf.light_s) * LIGHTMAP_BYTES

	gl1_light.R_SetCacheState( surf )
	gl1_light.R_BuildLightMap (surf, memoryview(gl1_surf.gl_lms.lightmap_buffer[buffer])[base:], BLOCK_WIDTH*LIGHTMAP_BYTES)


"""
================
LM_BeginBuildingLightmaps
================
"""
def LM_BeginBuildingLightmaps (m): #model_t *


	"""
	static lightstyle_t	lightstyles[MAX_LIGHTSTYLES];
	int				i;
	"""

	gl1_surf.gl_lms.allocated = [0] * BLOCK_WIDTH # memset( gl_lms.allocated, 0, sizeof(gl_lms.allocated) );
	LM_FreeLightmapBuffers()

	gl1_main.r_framecount = 1		# no dlightcache

	# build the lightmap textures on texture unit 1 (R_Bind is unit-relative)
	gl1_image.R_EnableMultitexture( True )
	gl1_image.R_SelectTexture( GL.GL_TEXTURE1 )

	#
	# setup the base lightstyles so the lightmaps won't have to be regenerated
	# the first time they're seen
	#
	lightstyles = []
	for i in range(shared.MAX_LIGHTSTYLES):

		ls = ref.lightstyle_t()
		ls.rgb[0] = 1
		ls.rgb[1] = 1
		ls.rgb[2] = 1
		ls.white = 3
		lightstyles.append(ls)

	gl1_main.r_newrefdef.lightstyles = lightstyles

	if not gl1_main.gl_state.lightmap_textures:

		gl1_main.gl_state.lightmap_textures = gl1_image.TEXNUM_LIGHTMAPS

	gl1_surf.gl_lms.current_lightmap_texture = 1

	# the dynamic lightmap lives in buffer 0 (classic rendering path)
	LM_AllocLightmapBuffer(0, True)

	# initialize the dynamic lightmap texture
	gl1_image.R_Bind( gl1_main.gl_state.lightmap_textures + 0 )
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
	GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL_LIGHTMAP_FORMAT,
			BLOCK_WIDTH, BLOCK_HEIGHT,
			0, GL_LIGHTMAP_FORMAT, GL.GL_UNSIGNED_BYTE,
			bytes(gl1_surf.gl_lms.lightmap_buffer[0]))

	if gl1_main.gl_config.multitexture:

		LM_AllocLightmapBuffer(gl1_surf.gl_lms.current_lightmap_texture, False)
		return


"""
================
LM_EndBuildingLightmaps
================
"""
def LM_EndBuildingLightmaps ():


	LM_UploadBlock( False )
	gl1_image.R_EnableMultitexture( False )
