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

// GL_RSURF.C: surface-related refresh code
#include <assert.h>

#include "gl_local.h"
"""
from __future__ import annotations

import numpy as np
import OpenGL.GL as GL
from client.refresh.gl1 import gl1_warp, gl1_image, gl1_main, gl1_model, gl1_light, gl1_lightmap, gl1_buffer
from client.refresh.gl1.header import model
from linux import qgl_linux
pass
pass
from client import ref
from common.header import files as files_h
from client.refresh.files import surf as files_surf
from common.header import shared
from common.shared import shared as shared_c

modelorg = np.zeros((3,), dtype=np.float32) #static vec3_t, relative to viewpoint

r_alpha_surfaces = [] #msurface_t list, was a chain through msurface_t.texturechain

DYNAMIC_LIGHT_WIDTH = 128
DYNAMIC_LIGHT_HEIGHT = 128

LIGHTMAP_BYTES = 4

BLOCK_WIDTH		= 128
BLOCK_HEIGHT	= 128

MAX_LIGHTMAPS	= 128

c_visible_lightmaps = 0 #int
c_visible_textures = 0 #int

GL_LIGHTMAP_FORMAT = GL.GL_RGBA

BACKFACE_EPSILON = 0.01 # from gl_local.h

class gllightmapstate_t(object):

	def __init__(self):

		self.current_lightmap_texture = 0 #int

		self.lightmap_surfaces = [[] for _ in range(MAX_LIGHTMAPS)] #msurface_t *[MAX_LIGHTMAPS], each chain is a list

		self.allocated = [0] * BLOCK_WIDTH #int [BLOCK_WIDTH]

		# the lightmap texture data needs to be kept in
		# main memory so texsubimage can update properly
		self.lightmap_buffer = [None] * MAX_LIGHTMAPS #byte *[MAX_LIGHTMAPS]

gl_lms = gllightmapstate_t() #static gllightmapstate_t

"""

extern void R_SetCacheState( msurface_t *surf );
extern void R_BuildLightMap (msurface_t *surf, byte *dest, int stride);
"""
"""
=============================================================

	BRUSH MODELS

=============================================================
"""

"""
===============
R_TextureAnimation

Returns the proper texture for a given time and base texture
===============
"""
def R_TextureAnimation (tex): #mtexinfo_t * (returns image_t *)

	#int		c;

	if not tex.next:
		return tex.image

	c = gl1_main.currententity.frame % tex.numframes
	while c:

		tex = tex.next
		c -= 1

	return tex.image

"""
#if 0
"""
"""
/*
=================
WaterWarpPolyVerts

Mangles the x and y coordinates in a copy of the poly
so that any drawing routine can be water warped
=================
*/
glpoly_t *WaterWarpPolyVerts (glpoly_t *p)
{
	int		i;
	float	*v, *nv;
	static byte	buffer[1024];
	glpoly_t *out;

	out = (glpoly_t *)buffer;

	out->numverts = p->numverts;
	v = p->verts[0];
	nv = out->verts[0];
	for (i=0 ; i<p->numverts ; i++, v+= VERTEXSIZE, nv+=VERTEXSIZE)
	{
		nv[0] = v[0] + 4*sin(v[1]*0.05+r_newrefdef.time)*sin(v[2]*0.05+r_newrefdef.time);
		nv[1] = v[1] + 4*sin(v[0]*0.05+r_newrefdef.time)*sin(v[2]*0.05+r_newrefdef.time);

		nv[2] = v[2];
		nv[3] = v[3];
		nv[4] = v[4];
		nv[5] = v[5];
		nv[6] = v[6];
	}

	return out;
}
"""
"""
/*
================
DrawGLWaterPoly

Warp the vertex coordinates
================
*/
void DrawGLWaterPoly (glpoly_t *p)
{
	int		i;
	float	*v;

	p = WaterWarpPolyVerts (p);
	qglBegin (GL_TRIANGLE_FAN);
	v = p->verts[0];
	for (i=0 ; i<p->numverts ; i++, v+= VERTEXSIZE)
	{
		qglTexCoord2f (v[3], v[4]);
		qglVertex3fv (v);
	}
	qglEnd ();
}
void DrawGLWaterPolyLightmap (glpoly_t *p)
{
	int		i;
	float	*v;

	p = WaterWarpPolyVerts (p);
	qglBegin (GL_TRIANGLE_FAN);
	v = p->verts[0];
	for (i=0 ; i<p->numverts ; i++, v+= VERTEXSIZE)
	{
		qglTexCoord2f (v[5], v[6]);
		qglVertex3fv (v);
	}
	qglEnd ();
}
#endif
"""

"""
================
DrawGLPoly
================
"""
def DrawGLPoly (p): #glpoly_t *

	#int		i;
	#float	*v;

	GL.glBegin (GL.GL_POLYGON)
	for v in p.verts[:p.numverts].tolist():

		GL.glTexCoord2f (v[3], v[4])
		GL.glVertex3f (v[0], v[1], v[2])

	GL.glEnd ()

#============
#PGM
"""
================
DrawGLFlowingPoly -- version of DrawGLPoly that handles scrolling texture
================
"""
def DrawGLFlowingPoly (fa): #msurface_t *

	"""
	int		i;
	float	*v;
	glpoly_t *p;
	float	scroll;
	"""

	p = fa.polys[0]

	scroll = -64 * ( (gl1_main.r_newrefdef.time / 40.0) - int(gl1_main.r_newrefdef.time / 40.0) )
	if scroll == 0.0:
		scroll = -64.0

	GL.glBegin (GL.GL_POLYGON)
	for v in p.verts[:p.numverts].tolist():

		GL.glTexCoord2f ((v[3] + scroll), v[4])
		GL.glVertex3f (v[0], v[1], v[2])

	GL.glEnd ()
#PGM
#============

"""
** R_DrawTriangleOutlines
"""
def R_DrawTriangleOutlines ():

	#int			i, j;
	#glpoly_t	*p;

	if not gl1_main.gl_showtris.value:
		return

	GL.glDisable (GL.GL_TEXTURE_2D)
	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glColor4f (1,1,1,1)

	for i in range(MAX_LIGHTMAPS):

		#msurface_t *surf;

		for surf in gl_lms.lightmap_surfaces[i]:

			for p in surf.polys:

				for j in range(2, p.numverts):

					GL.glBegin (GL.GL_LINE_STRIP)
					GL.glVertex3fv (p.verts[0][:3])
					GL.glVertex3fv (p.verts[j-1][:3])
					GL.glVertex3fv (p.verts[j][:3])
					GL.glVertex3fv (p.verts[0][:3])
					GL.glEnd ()

	GL.glEnable (GL.GL_DEPTH_TEST)
	GL.glEnable (GL.GL_TEXTURE_2D)

"""
** DrawGLPolyChain
"""
def DrawGLPolyChain( polys, soffset, toffset ): #glpoly_t list (was a chain), float, float

	if soffset == 0 and toffset == 0:

		for p in polys:

			#float *v;
			#int j;

			GL.glBegin (GL.GL_POLYGON)
			for v in p.verts[:p.numverts].tolist():

				GL.glTexCoord2f (v[5], v[6] )
				GL.glVertex3f (v[0], v[1], v[2])

			GL.glEnd ()

	else:

		for p in polys:

			#float *v;
			#int j;

			GL.glBegin (GL.GL_POLYGON)
			for v in p.verts[:p.numverts].tolist():

				GL.glTexCoord2f (v[5] - soffset, v[6] - toffset )
				GL.glVertex3f (v[0], v[1], v[2])

			GL.glEnd ()


"""
** R_BlendLightMaps
**
** This routine takes all the given light mapped surfaces in the world and
** blends them into the framebuffer.
"""
def R_BlendLightmaps ():

	global c_visible_lightmaps

	#int			i;
	#msurface_t	*surf, *newdrawsurf = 0;

	# don't bother if we're set to fullbright
	if gl1_main.r_fullbright.value:
		return
	if not gl1_main.r_worldmodel.lightdata:
		return

	# don't bother writing Z
	GL.glDepthMask( 0 )

	#
	# set the appropriate blending mode unless we're only looking at the
	# lightmaps.
	#
	if not gl1_main.r_lightmap.value:

		GL.glEnable (GL.GL_BLEND)

		if gl1_main.gl1_saturatelighting.value:

			GL.glBlendFunc( GL.GL_ONE, GL.GL_ONE )

		else:

			if gl1_main.gl_monolightmap.string[0] != '0':

				mode = gl1_main.gl_monolightmap.string[0].upper()
				if mode == 'I':
					GL.glBlendFunc (GL.GL_ZERO, GL.GL_SRC_COLOR )
				elif mode == 'L':
					GL.glBlendFunc (GL.GL_ZERO, GL.GL_SRC_COLOR )
				else: # case 'A': default:
					GL.glBlendFunc( GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA )

			else:

				GL.glBlendFunc (GL.GL_ZERO, GL.GL_SRC_COLOR )

	if gl1_main.currentmodel is gl1_main.r_worldmodel:
		c_visible_lightmaps = 0

	#
	# render static lightmaps first
	#
	for i in range(1, MAX_LIGHTMAPS):

		if gl_lms.lightmap_surfaces[i]:

			if gl1_main.currentmodel is gl1_main.r_worldmodel:
				c_visible_lightmaps += 1
			gl1_image.R_Bind( gl1_main.gl_state.lightmap_textures + i)

			for surf in gl_lms.lightmap_surfaces[i]:

				if surf.polys:
					DrawGLPolyChain( surf.polys, 0, 0 )

	#
	# render dynamic lightmaps
	#
	if gl1_main.gl1_dynamic.value:

		gl1_lightmap.LM_InitBlock()

		gl1_image.R_Bind( gl1_main.gl_state.lightmap_textures+0 )

		if gl1_main.currentmodel is gl1_main.r_worldmodel:
			c_visible_lightmaps += 1

		dynamic_surfaces = gl_lms.lightmap_surfaces[0]
		newdrawsurf = 0 # index into dynamic_surfaces, was a pointer into the chain

		for surf_i, surf in enumerate(dynamic_surfaces):

			#int		smax, tmax;
			#byte	*base;

			smax = (surf.extents[0]>>4)+1
			tmax = (surf.extents[1]>>4)+1

			ok, surf.dlight_s, surf.dlight_t = gl1_lightmap.LM_AllocBlock( smax, tmax )
			if ok:

				base = ( surf.dlight_t * BLOCK_WIDTH + surf.dlight_s ) * LIGHTMAP_BYTES

				gl1_light.R_BuildLightMap (surf, memoryview(gl_lms.lightmap_buffer[0])[base:], BLOCK_WIDTH*LIGHTMAP_BYTES)

			else:

				#msurface_t *drawsurf;

				# upload what we have so far
				gl1_lightmap.LM_UploadBlock( True )

				# draw all surfaces that use this lightmap
				for drawsurf in dynamic_surfaces[newdrawsurf:surf_i]:

					if drawsurf.polys:
						DrawGLPolyChain( drawsurf.polys,
							              ( drawsurf.light_s - drawsurf.dlight_s ) * ( 1.0 / 128.0 ),
										( drawsurf.light_t - drawsurf.dlight_t ) * ( 1.0 / 128.0 ) )

				newdrawsurf = surf_i

				# clear the block
				gl1_lightmap.LM_InitBlock()

				# try uploading the block now
				ok, surf.dlight_s, surf.dlight_t = gl1_lightmap.LM_AllocBlock( smax, tmax )
				if not ok:

					gl1_main.ri.Sys_Error( shared.ERR_FATAL, "Consecutive calls to LM_AllocBlock({},{}) failed (dynamic)\n".format(smax, tmax) )

				base = ( surf.dlight_t * BLOCK_WIDTH + surf.dlight_s ) * LIGHTMAP_BYTES

				gl1_light.R_BuildLightMap (surf, memoryview(gl_lms.lightmap_buffer[0])[base:], BLOCK_WIDTH*LIGHTMAP_BYTES)

		#
		# draw remainder of dynamic lightmaps that haven't been uploaded yet
		#
		if dynamic_surfaces[newdrawsurf:]:
			gl1_lightmap.LM_UploadBlock( True )

		for surf in dynamic_surfaces[newdrawsurf:]:

			if surf.polys:
				DrawGLPolyChain( surf.polys, ( surf.light_s - surf.dlight_s ) * ( 1.0 / 128.0 ), ( surf.light_t - surf.dlight_t ) * ( 1.0 / 128.0 ) )

	#
	# restore state
	#
	GL.glDisable (GL.GL_BLEND)
	GL.glBlendFunc (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
	GL.glDepthMask( 1 )

"""
================
R_RenderBrushPoly
================
"""
def R_RenderBrushPoly (fa): #msurface_t *

	"""
	int			maps;
	image_t		*image;
	qboolean is_dynamic = false;
	"""
	is_dynamic = False

	gl1_main.c_brush_polys += 1

	image = R_TextureAnimation (fa.texinfo)

	if fa.flags & model.SURF_DRAWTURB:

		gl1_image.R_Bind( image.texnum )

		# warp texture, no lightmaps
		gl1_image.R_TexEnv( GL.GL_MODULATE )
		GL.glColor4f( gl1_main.gl_state.inverse_intensity,
			        gl1_main.gl_state.inverse_intensity,
					gl1_main.gl_state.inverse_intensity,
					1.0 )
		gl1_warp.R_EmitWaterPolys (fa)
		gl1_image.R_TexEnv( GL.GL_REPLACE )

		return

	else:

		gl1_image.R_Bind( image.texnum )

		gl1_image.R_TexEnv( GL.GL_REPLACE )

#======
#PGM
	if fa.texinfo.flags & shared.SURF_FLOWING:
		DrawGLFlowingPoly (fa)
	else:
		DrawGLPoly (fa.polys[0])
#PGM
#======

	#
	# check for lightmap modification
	#
	dynamic = False
	maps = 0
	while maps < files_h.MAXLIGHTMAPS and fa.styles[maps] != 255:

		if gl1_main.r_newrefdef.lightstyles[fa.styles[maps]].white != fa.cached_light[maps]:
			dynamic = True
			break # goto dynamic;
		maps += 1

	# dynamic this frame or dynamic previously
	if dynamic or ( fa.dlightframe == gl1_main.r_framecount ):

	#dynamic:
		if gl1_main.gl1_dynamic.value:

			if not ( fa.texinfo.flags & (shared.SURF_SKY|shared.SURF_TRANS33|shared.SURF_TRANS66|shared.SURF_WARP ) ):

				is_dynamic = True

	if is_dynamic:

		# C reads styles[maps] even when maps == MAXLIGHTMAPS, treat that as no style
		style = fa.styles[maps] if maps < files_h.MAXLIGHTMAPS else 255
		if ( style >= 32 or style == 0 ) and ( fa.dlightframe != gl1_main.r_framecount ):

			#unsigned	temp[34*34];
			#int			smax, tmax;

			smax = (fa.extents[0]>>4)+1
			tmax = (fa.extents[1]>>4)+1
			temp = bytearray(smax*tmax*4)

			gl1_light.R_BuildLightMap( fa, temp, smax*4 )
			gl1_light.R_SetCacheState( fa )

			gl1_image.R_Bind( gl1_main.gl_state.lightmap_textures + fa.lightmaptexturenum )

			GL.glTexSubImage2D( GL.GL_TEXTURE_2D, 0,
							  fa.light_s, fa.light_t,
							  smax, tmax,
							  GL_LIGHTMAP_FORMAT,
							  GL.GL_UNSIGNED_BYTE, bytes(temp) )

			gl_lms.lightmap_surfaces[fa.lightmaptexturenum].append(fa)

		else:

			gl_lms.lightmap_surfaces[0].append(fa)

	else:

		gl_lms.lightmap_surfaces[fa.lightmaptexturenum].append(fa)


"""
================
R_DrawAlphaSurfaces

Draw water surfaces and windows.
The BSP tree is waled front to back, so unwinding the chain
of alpha_surfaces will draw back to front, giving proper ordering.
================
"""
def R_DrawAlphaSurfaces ():

	#msurface_t	*s;
	#float		intens;

	#
	# go back to the world matrix
	#
	GL.glLoadMatrixf (gl1_main.r_world_matrix)

	GL.glEnable (GL.GL_BLEND)
	gl1_image.R_TexEnv( GL.GL_MODULATE )

	# the textures are prescaled up for a better lighting range,
	# so scale it back down
	intens = gl1_main.gl_state.inverse_intensity

	# the C chain is built by prepending, so walk the list backwards to unwind it
	for s in reversed(r_alpha_surfaces):

		gl1_image.R_Bind(s.texinfo.image.texnum)
		gl1_main.c_brush_polys += 1
		if s.texinfo.flags & shared.SURF_TRANS33:
			GL.glColor4f (intens,intens,intens,0.33)
		elif s.texinfo.flags & shared.SURF_TRANS66:
			GL.glColor4f (intens,intens,intens,0.66)
		else:
			GL.glColor4f (intens,intens,intens,1)
		if s.flags & model.SURF_DRAWTURB:
			gl1_warp.R_EmitWaterPolys (s)
		elif s.texinfo.flags & shared.SURF_FLOWING:			# PGM	9/16/98
			DrawGLFlowingPoly (s)							# PGM
		else:
			DrawGLPoly (s.polys[0])

	gl1_image.R_TexEnv( GL.GL_REPLACE )
	GL.glColor4f (1,1,1,1)
	GL.glDisable (GL.GL_BLEND)

	r_alpha_surfaces.clear() # r_alpha_surfaces = NULL;

"""
================
DrawTextureChains
================
"""
def DrawTextureChains ():

	global c_visible_textures

	"""
	int		i;
	msurface_t	*s;
	image_t		*image;
	"""

	c_visible_textures = 0

#	R_TexEnv( GL_REPLACE );

	if not qgl_linux.qglSelectTextureSGIS and not qgl_linux.qglActiveTextureARB:

		for image in gl1_image.gltextures[:gl1_image.numgltextures]:

			if not image.registration_sequence:
				continue
			if not image.texturechain:
				continue
			c_visible_textures += 1

			for s in image.texturechain:
				R_RenderBrushPoly (s)

			image.texturechain = []

	else:

		for image in gl1_image.gltextures[:gl1_image.numgltextures]:

			if not image.registration_sequence:
				continue
			if not image.texturechain:
				continue
			c_visible_textures += 1

			for s in image.texturechain:

				if not ( s.flags & model.SURF_DRAWTURB ):
					R_RenderBrushPoly (s)

		gl1_image.R_EnableMultitexture( False )
		for image in gl1_image.gltextures[:gl1_image.numgltextures]:

			if not image.registration_sequence:
				continue
			if not image.texturechain:
				continue

			for s in image.texturechain:

				if s.flags & model.SURF_DRAWTURB:
					R_RenderBrushPoly (s)

			image.texturechain = []

#		R_EnableMultitexture( true );

	gl1_image.R_TexEnv( GL.GL_REPLACE )


def GL_RenderLightmappedPoly( surf ): #msurface_t *

	"""
	int		i, nv = surf->polys->numverts;
	int		map;
	float	*v;
	image_t *image = R_TextureAnimation( surf->texinfo );
	qboolean is_dynamic = false;
	unsigned lmtex = surf->lightmaptexturenum;
	glpoly_t *p;
	"""
	nv = surf.polys[0].numverts
	image = R_TextureAnimation( surf.texinfo )
	is_dynamic = False
	lmtex = surf.lightmaptexturenum

	dynamic = False
	map = 0
	while map < files_h.MAXLIGHTMAPS and surf.styles[map] != 255:

		if gl1_main.r_newrefdef.lightstyles[surf.styles[map]].white != surf.cached_light[map]:
			dynamic = True
			break # goto dynamic;
		map += 1

	# dynamic this frame or dynamic previously
	if dynamic or ( surf.dlightframe == gl1_main.r_framecount ):

	#dynamic:
		if gl1_main.gl1_dynamic.value:

			if not (surf.texinfo.flags & (shared.SURF_SKY|shared.SURF_TRANS33|shared.SURF_TRANS66|shared.SURF_WARP ) ):

				is_dynamic = True

	if is_dynamic:

		#unsigned	temp[128*128];
		#int			smax, tmax;

		# C reads styles[map] even when map == MAXLIGHTMAPS, treat that as no style
		style = surf.styles[map] if map < files_h.MAXLIGHTMAPS else 255
		if ( style >= 32 or style == 0 ) and ( surf.dlightframe != gl1_main.r_framecount ):

			smax = (surf.extents[0]>>4)+1
			tmax = (surf.extents[1]>>4)+1
			temp = bytearray(smax*tmax*4)

			gl1_light.R_BuildLightMap( surf, temp, smax*4 )
			gl1_light.R_SetCacheState( surf )

			gl1_image.R_MBind( GL.GL_TEXTURE1, gl1_main.gl_state.lightmap_textures + surf.lightmaptexturenum )

			lmtex = surf.lightmaptexturenum

			GL.glTexSubImage2D( GL.GL_TEXTURE_2D, 0,
							  surf.light_s, surf.light_t,
							  smax, tmax,
							  GL_LIGHTMAP_FORMAT,
							  GL.GL_UNSIGNED_BYTE, bytes(temp) )


		else:

			smax = (surf.extents[0]>>4)+1
			tmax = (surf.extents[1]>>4)+1
			temp = bytearray(smax*tmax*4)

			gl1_light.R_BuildLightMap( surf, temp, smax*4 )

			gl1_image.R_MBind( GL.GL_TEXTURE1, gl1_main.gl_state.lightmap_textures + 0 )

			lmtex = 0

			GL.glTexSubImage2D( GL.GL_TEXTURE_2D, 0,
							  surf.light_s, surf.light_t,
							  smax, tmax,
							  GL_LIGHTMAP_FORMAT,
							  GL.GL_UNSIGNED_BYTE, bytes(temp) )

		gl1_main.c_brush_polys += 1

		# Q2PORT: buffer path, Yamagi gl1_buffer
		gl1_buffer.R_UpdateGLBuffer (gl1_buffer.buf_mtex, image.texnum, lmtex, 0, 1.0)

		if surf.texinfo.flags & shared.SURF_FLOWING:

			scroll = -64 * ( (gl1_main.r_newrefdef.time / 40.0) - int(gl1_main.r_newrefdef.time / 40.0) )
			if scroll == 0.0:
				scroll = -64.0

		else:
			scroll = 0.0

		for p in surf.polys:

			gl1_buffer.R_SetBufferIndices (GL.GL_TRIANGLE_FAN, p.numverts)
			for v in p.verts[:p.numverts].tolist():

				gl1_buffer.GLBUFFER_VERTEX (v[0], v[1], v[2])
				gl1_buffer.GLBUFFER_MULTITEX (v[3]+scroll, v[4], v[5], v[6])
#==========

	else:

		gl1_main.c_brush_polys += 1

		gl1_image.R_MBind( GL.GL_TEXTURE0, image.texnum )
		gl1_image.R_MBind( GL.GL_TEXTURE1, gl1_main.gl_state.lightmap_textures + lmtex )

#==========
#PGM
		if surf.texinfo.flags & shared.SURF_FLOWING:

			#float scroll;

			scroll = -64 * ( (gl1_main.r_newrefdef.time / 40.0) - int(gl1_main.r_newrefdef.time / 40.0) )
			if scroll == 0.0:
				scroll = -64.0

			for p in surf.polys:

				GL.glBegin (GL.GL_POLYGON)
				for v in p.verts[:nv].tolist():

					GL.glMultiTexCoord2f( GL.GL_TEXTURE0, (v[3]+scroll), v[4])
					GL.glMultiTexCoord2f( GL.GL_TEXTURE1, v[5], v[6])
					GL.glVertex3f (v[0], v[1], v[2])

				GL.glEnd ()

		else:

#PGM
#==========
			for p in surf.polys:

				GL.glBegin (GL.GL_POLYGON)
				for v in p.verts[:nv].tolist():

					GL.glMultiTexCoord2f( GL.GL_TEXTURE0, v[3], v[4])
					GL.glMultiTexCoord2f( GL.GL_TEXTURE1, v[5], v[6])
					GL.glVertex3f (v[0], v[1], v[2])

				GL.glEnd ()

#==========
#PGM

#PGM
#==========


"""
=================
R_DrawInlineBModel
=================
"""
def R_DrawInlineBModel ():

	"""
	int			i, k;
	cplane_t	*pplane;
	float		dot;
	msurface_t	*psurf;
	dlight_t	*lt;
	"""
	currentmodel = gl1_main.currentmodel
	currententity = gl1_main.currententity

	# calculate dynamic lighting for bmodel
	if not gl1_main.gl1_flashblend.value:

		for k in range(gl1_main.r_newrefdef.num_dlights):

			lt = gl1_main.r_newrefdef.dlights[k]
			files_surf.R_MarkLights (lt, 1<<k,
				currentmodel.nodes[currentmodel.firstnode],
				gl1_light.r_dlightframecount, gl1_light.R_MarkSurfaceLights)

	if currententity.flags & shared.RF_TRANSLUCENT:

		GL.glEnable (GL.GL_BLEND)
		GL.glColor4f (1,1,1,0.25)
		gl1_image.R_TexEnv( GL.GL_MODULATE )

	#
	# draw texture
	#
	for i in range(currentmodel.nummodelsurfaces):

		psurf = currentmodel.surfaces[currentmodel.firstmodelsurface + i]

		# find which side of the node we are on
		pplane = psurf.plane

		dot = shared.DotProduct (modelorg, pplane.normal) - pplane.dist

		# draw the polygon
		if (((psurf.flags & model.SURF_PLANEBACK) and (dot < -BACKFACE_EPSILON)) or
			(not (psurf.flags & model.SURF_PLANEBACK) and (dot > BACKFACE_EPSILON))):

			if psurf.texinfo.flags & (shared.SURF_TRANS33|shared.SURF_TRANS66):
				# add to the translucent chain
				r_alpha_surfaces.append(psurf)

			elif qgl_linux.qglMTexCoord2fSGIS and not ( psurf.flags & model.SURF_DRAWTURB ):

				GL_RenderLightmappedPoly( psurf )

			else:

				gl1_image.R_EnableMultitexture( False )
				R_RenderBrushPoly( psurf )
				gl1_image.R_EnableMultitexture( True )

	if not (currententity.flags & shared.RF_TRANSLUCENT):

		if not qgl_linux.qglMTexCoord2fSGIS:
			R_BlendLightmaps ()

	else:

		GL.glDisable (GL.GL_BLEND)
		GL.glColor4f (1,1,1,1)
		gl1_image.R_TexEnv( GL.GL_REPLACE )


"""
=================
R_DrawBrushModel
=================
"""
def R_DrawBrushModel (e): #entity_t *

	"""
	vec3_t		mins, maxs;
	int			i;
	qboolean	rotated;
	"""
	currentmodel = gl1_main.currentmodel
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)

	if currentmodel.nummodelsurfaces == 0:
		return

	gl1_main.currententity = e
	gl1_main.gl_state.currenttextures[0] = gl1_main.gl_state.currenttextures[1] = -1

	if e.angles[0] or e.angles[1] or e.angles[2]:

		rotated = True
		for i in range(3):

			mins[i] = e.origin[i] - currentmodel.radius
			maxs[i] = e.origin[i] + currentmodel.radius

	else:

		rotated = False
		shared.VectorAdd (e.origin, currentmodel.mins, mins)
		shared.VectorAdd (e.origin, currentmodel.maxs, maxs)

	if files_surf.R_CullBox (mins, maxs, gl1_main.frustum):
		return

	GL.glColor3f (1,1,1)
	gl_lms.lightmap_surfaces = [[] for _ in range(MAX_LIGHTMAPS)] # memset (gl_lms.lightmap_surfaces, 0, sizeof(gl_lms.lightmap_surfaces));

	shared.VectorSubtract (gl1_main.r_newrefdef.vieworg, e.origin, modelorg)
	if rotated:

		#vec3_t	temp;
		#vec3_t	forward, right, up;
		forward = np.zeros((3,), dtype=np.float32)
		right = np.zeros((3,), dtype=np.float32)
		up = np.zeros((3,), dtype=np.float32)

		temp = modelorg.copy() # VectorCopy (modelorg, temp);
		shared_c.AngleVectors (e.angles, forward, right, up)
		modelorg[0] = shared.DotProduct (temp, forward)
		modelorg[1] = -shared.DotProduct (temp, right)
		modelorg[2] = shared.DotProduct (temp, up)

	GL.glPushMatrix ()
	e.angles[0] = -e.angles[0]	# stupid quake bug
	e.angles[2] = -e.angles[2]	# stupid quake bug
	gl1_main.R_RotateForEntity (e)
	e.angles[0] = -e.angles[0]	# stupid quake bug
	e.angles[2] = -e.angles[2]	# stupid quake bug

	gl1_image.R_EnableMultitexture( True )
	gl1_image.R_SelectTexture( GL.GL_TEXTURE0)
	gl1_image.R_TexEnv( GL.GL_REPLACE )
	gl1_image.R_SelectTexture( GL.GL_TEXTURE1)
	gl1_image.R_TexEnv( GL.GL_MODULATE )

	R_DrawInlineBModel ()
	gl1_image.R_EnableMultitexture( False )

	GL.glPopMatrix ()

"""
=============================================================

	WORLD MODEL

=============================================================
"""

# Q2PORT DEBUG: per frame world node counters, printed by gl1_main.R_DebugFrustum
dbg_nodes_visited, dbg_nodes_culled, dbg_leafs_drawn = 0, 0, 0

"""
================
R_RecursiveWorldNode
================
"""
def R_RecursiveWorldNode (node): #mnode_t *

	global dbg_nodes_visited, dbg_nodes_culled, dbg_leafs_drawn

	"""
	int			c, side, sidebit;
	cplane_t	*plane;
	msurface_t	*surf, **mark;
	mleaf_t		*pleaf;
	float		dot;
	image_t		*image;
	"""

	if node.contents == shared.CONTENTS_SOLID:
		return		# solid

	if node.visframe != gl1_main.r_visframecount:
		return

	dbg_nodes_visited += 1 # Q2PORT DEBUG

	if files_surf.R_CullBox (node.minmaxs[0:3], node.minmaxs[3:6], gl1_main.frustum):
		dbg_nodes_culled += 1 # Q2PORT DEBUG
		return

	# if a leaf node, draw stuff
	if node.contents != -1:

		dbg_leafs_drawn += 1 # Q2PORT DEBUG
		pleaf = node

		# check for door connected areas
		if gl1_main.r_newrefdef.areabits:

			if not (gl1_main.r_newrefdef.areabits[pleaf.area>>3] & (1<<(pleaf.area&7)) ):
				return		# not visible

		for mark in pleaf.firstmarksurface[:pleaf.nummarksurfaces]:
			mark.visframe = gl1_main.r_framecount

		return

	# node is just a decision point, so go down the apropriate sides

	# find which side of the node we are on
	plane = node.plane

	if plane.type == files_h.PLANE_X:
		dot = modelorg[0] - plane.dist
	elif plane.type == files_h.PLANE_Y:
		dot = modelorg[1] - plane.dist
	elif plane.type == files_h.PLANE_Z:
		dot = modelorg[2] - plane.dist
	else:
		dot = shared.DotProduct (modelorg, plane.normal) - plane.dist

	if dot >= 0:

		side = 0
		sidebit = 0

	else:

		side = 1
		sidebit = model.SURF_PLANEBACK

	# recurse down the children, front side first
	R_RecursiveWorldNode (node.children[side])

	# draw stuff
	surfaces = gl1_main.r_worldmodel.surfaces
	for surf in surfaces[node.firstsurface:node.firstsurface + node.numsurfaces]:

		if surf.visframe != gl1_main.r_framecount:
			continue

		if (surf.flags & model.SURF_PLANEBACK) != sidebit:
			continue		# wrong side

		if surf.texinfo.flags & shared.SURF_SKY:
			# just adds to visible sky bounds
			gl1_warp.R_AddSkySurface (surf)

		elif surf.texinfo.flags & (shared.SURF_TRANS33|shared.SURF_TRANS66):
			# add to the translucent chain
			r_alpha_surfaces.append(surf)

		else:

			if qgl_linux.qglMTexCoord2fSGIS and not ( surf.flags & model.SURF_DRAWTURB ):

				GL_RenderLightmappedPoly( surf )

			else:

				# the polygon is visible, so add it to the texture
				# sorted chain
				# FIXME: this is a hack for animation
				image = R_TextureAnimation (surf.texinfo)
				image.texturechain.append(surf)

	# recurse down the back side
	R_RecursiveWorldNode (node.children[1 - side]) # !side
	"""
	for ( ; c ; c--, surf++)
	{
		if (surf->visframe != r_framecount)
			continue;

		if ( (surf->flags & SURF_PLANEBACK) != sidebit )
			continue;		// wrong side

		if (surf->texinfo->flags & SURF_SKY)
		{	// just adds to visible sky bounds
			R_AddSkySurface (surf);
		}
		else if (surf->texinfo->flags & (SURF_TRANS33|SURF_TRANS66))
		{	// add to the translucent chain
//			surf->texturechain = alpha_surfaces;
//			alpha_surfaces = surf;
		}
		else
		{
			if ( qglMTexCoord2fSGIS && !( surf->flags & SURF_DRAWTURB ) )
			{
				GL_RenderLightmappedPoly( surf );
			}
			else
			{
				// the polygon is visible, so add it to the texture
				// sorted chain
				// FIXME: this is a hack for animation
				image = R_TextureAnimation (surf->texinfo);
				surf->texturechain = image->texturechain;
				image->texturechain = surf;
			}
		}
	}
	"""


"""
=============
R_DrawWorld
=============
"""
def R_DrawWorld ():

	#entity_t	ent;

	if not gl1_main.r_drawworld.value:
		return

	if gl1_main.r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:
		return

	gl1_main.currentmodel = gl1_main.r_worldmodel

	shared.VectorCopy (gl1_main.r_newrefdef.vieworg, modelorg)

	# auto cycle the world frame for texture animation
	ent = ref.entity_t() # memset (&ent, 0, sizeof(ent));
	ent.frame = int(gl1_main.r_newrefdef.time*2)
	gl1_main.currententity = ent

	gl1_main.gl_state.currenttextures[0] = gl1_main.gl_state.currenttextures[1] = -1

	GL.glColor3f (1,1,1)
	gl_lms.lightmap_surfaces = [[] for _ in range(MAX_LIGHTMAPS)] # memset (gl_lms.lightmap_surfaces, 0, sizeof(gl_lms.lightmap_surfaces));
	gl1_warp.R_ClearSkyBox ()

	if qgl_linux.qglMTexCoord2fSGIS:

		gl1_image.R_EnableMultitexture( True )

		gl1_image.R_SelectTexture( GL.GL_TEXTURE0)
		gl1_image.R_TexEnv( GL.GL_REPLACE )
		gl1_image.R_SelectTexture( GL.GL_TEXTURE1)

		if gl1_main.r_lightmap.value:
			gl1_image.R_TexEnv( GL.GL_REPLACE )
		else:
			gl1_image.R_TexEnv( GL.GL_MODULATE )

		R_RecursiveWorldNode (gl1_main.r_worldmodel.nodes[0])

		gl1_buffer.R_ApplyGLBuffer()

		gl1_image.R_EnableMultitexture( False )

	else:

		R_RecursiveWorldNode (gl1_main.r_worldmodel.nodes[0])

	#
	# theoretically nothing should happen in the next two functions
	# if multitexture is enabled
	#
	DrawTextureChains ()
	R_BlendLightmaps ()

	gl1_warp.R_DrawSkyBox ()

	R_DrawTriangleOutlines ()


"""
===============
R_MarkLeaves

Mark the leaves and nodes that are in the PVS for the current
cluster
===============
"""
def R_MarkLeaves ():

	"""
	byte	*vis;
	byte	fatvis[MAX_MAP_LEAFS/8];
	mnode_t	*node;
	int		i, c;
	mleaf_t	*leaf;
	int		cluster;
	"""
	r_worldmodel = gl1_main.r_worldmodel

	if gl1_main.r_oldviewcluster == gl1_main.r_viewcluster and gl1_main.r_oldviewcluster2 == gl1_main.r_viewcluster2 and not gl1_main.r_novis.value and gl1_main.r_viewcluster != -1:
		return

	# development aid to let you run around and see exactly where
	# the pvs ends
	if gl1_main.r_lockpvs.value:
		return

	gl1_main.r_visframecount += 1
	gl1_main.r_oldviewcluster = gl1_main.r_viewcluster
	gl1_main.r_oldviewcluster2 = gl1_main.r_viewcluster2

	if gl1_main.r_novis.value or gl1_main.r_viewcluster == -1 or not r_worldmodel.vis:

		# mark everything
		for i in range(r_worldmodel.numleafs):
			r_worldmodel.leafs[i].visframe = gl1_main.r_visframecount
		for i in range(r_worldmodel.numnodes):
			r_worldmodel.nodes[i].visframe = gl1_main.r_visframecount
		return

	vis = gl1_model.Mod_ClusterPVS (gl1_main.r_viewcluster, r_worldmodel)
	# may have to combine two clusters because of solid water boundaries
	if gl1_main.r_viewcluster2 != gl1_main.r_viewcluster:

		fatvis = bytearray(files_h.MAX_MAP_LEAFS//8)
		n = min((r_worldmodel.numleafs+7)//8, len(vis))
		fatvis[:n] = vis[:n] # memcpy (fatvis, vis, (r_worldmodel->numleafs+7)/8);
		vis = gl1_model.Mod_ClusterPVS (gl1_main.r_viewcluster2, r_worldmodel)
		c = (r_worldmodel.numleafs+31)//32
		for i in range(min(c*4, len(vis))): # ((int *)fatvis)[i] |= ((int *)vis)[i];
			fatvis[i] |= vis[i]
		vis = fatvis

	for i in range(r_worldmodel.numleafs):

		leaf = r_worldmodel.leafs[i]
		cluster = leaf.cluster
		if cluster == -1:
			continue
		if vis[cluster>>3] & (1<<(cluster&7)):

			node = leaf
			while True:

				if node.visframe == gl1_main.r_visframecount:
					break
				node.visframe = gl1_main.r_visframecount
				node = node.parent
				if not node:
					break

	"""
#if 0
	for (i=0 ; i<r_worldmodel->vis->numclusters ; i++)
	{
		if (vis[i>>3] & (1<<(i&7)))
		{
			node = (mnode_t *)&r_worldmodel->leafs[i];	// FIXME: cluster
			do
			{
				if (node->visframe == r_visframecount)
					break;
				node->visframe = r_visframecount;
				node = node->parent;
			} while (node);
		}
	}
#endif
	"""


