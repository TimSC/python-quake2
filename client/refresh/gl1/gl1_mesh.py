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

"""
from __future__ import annotations

import math
import os
import re
import numpy as np
import OpenGL.GL as GL
import OpenGL.GL.EXT.compiled_vertex_array as GLcva
from linux import qgl_linux
pass
pass
from client import ref
from client.refresh.gl1 import gl1_main, gl1_image, gl1_light
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from common import movemsg
"""
// gl1_mesh.c: triangle model functions

#include "gl_local.h"
"""
"""
=============================================================

  ALIAS MODELS

=============================================================
"""

NUMVERTEXNORMALS = 162

# float r_avertexnormals[NUMVERTEXNORMALS][3] = { #include "anorms.h" };
# this is the same table as common.bytedirs, which is used directly. It
# can't be aliased here because qcommon.common is still loading when this
# module is first imported.

s_lerped = np.zeros((files_h.MAX_VERTS, 3), dtype=np.float32) #static vec4_t [MAX_VERTS], 4th value was SIMD padding
# colorArray for the vertex array path. The C one is on the stack, but GL reads it
# during glArrayElement, so it is kept at module level so it outlives the pointer.
s_colorArray = np.zeros((files_h.MAX_VERTS, 3), dtype=np.float32) #float [MAX_VERTS*4]

shadevector = np.zeros((3,), dtype=np.float32) #vec3_t
shadelight = np.zeros((3,), dtype=np.float32) #float[3]

# precalculated dot products for quantized angles
SHADEDOT_QUANT = 16

def _LoadAnormtab ():
	# float r_avertexnormal_dots[SHADEDOT_QUANT][256] = #include "anormtab.h"
	text = open(os.path.join(os.path.dirname(__file__), "anormtab.h")).read()
	text = text[text.index("{"):] # skip the licence comment
	values = [float(x) for x in re.findall(r"\d+\.\d+", text)]
	return np.array(values, dtype=np.float32).reshape((SHADEDOT_QUANT, 256))

r_avertexnormal_dots = _LoadAnormtab()

shadedots = r_avertexnormal_dots[0] #float *

SHELL_FLAGS = shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE | shared.RF_SHELL_HALF_DAM

def R_LerpVerts (nverts, v, ov, verts, lerp, move, frontv, backv): #int, dtrivertx_t *, dtrivertx_t *, dtrivertx_t *, float *, float[3], float[3], float[3]

	#int i;

	# v, ov and verts are numpy arrays of dtrivertx_t rows (v[0], v[1], v[2], lightnormalindex)
	# so the per vertex loop is done as one numpy expression

	#PMM -- added RF_SHELL_DOUBLE, RF_SHELL_HALF_DAM
	if gl1_main.currententity.flags & SHELL_FLAGS:

		normal = movemsg.bytedirs[verts[:nverts, 3]] # r_avertexnormals
		lerp[:nverts] = move + ov[:nverts, :3]*backv + v[:nverts, :3]*frontv + normal * ref.POWERSUIT_SCALE

	else:

		lerp[:nverts] = move + ov[:nverts, :3]*backv + v[:nverts, :3]*frontv


"""
=============
R_DrawAliasFrameLerp

interpolates between two frames and origins
FIXME: batch lerp all vertexes
=============
"""
def R_DrawAliasFrameLerp (paliashdr, backlerp): #dmdl_t *, float

	"""
	float 	l;
	daliasframe_t	*frame, *oldframe;
	dtrivertx_t	*v, *ov, *verts;
	int		*order;
	int		count;
	float	frontlerp;
	float	alpha;
	vec3_t	move, delta, vectors[3];
	vec3_t	frontv, backv;
	int		i;
	int		index_xyz;
	float	*lerp;
	"""
	currententity = gl1_main.currententity

	frame = paliashdr.frames[currententity.frame]
	verts = v = frame.verts

	oldframe = paliashdr.frames[currententity.oldframe]
	ov = oldframe.verts

	order = paliashdr.glcmds

#	glTranslatef (frame->translate[0], frame->translate[1], frame->translate[2]);
#	glScalef (frame->scale[0], frame->scale[1], frame->scale[2]);

	if currententity.flags & shared.RF_TRANSLUCENT:
		alpha = currententity.alpha
	else:
		alpha = 1.0

	# PMM - added double shell
	if currententity.flags & SHELL_FLAGS:
		GL.glDisable( GL.GL_TEXTURE_2D )

	frontlerp = 1.0 - backlerp

	# move should be the delta back to the previous frame * backlerp
	delta = np.zeros((3,), dtype=np.float32)
	vectors = [np.zeros((3,), dtype=np.float32) for _ in range(3)]
	move = np.zeros((3,), dtype=np.float32)
	shared.VectorSubtract (currententity.oldorigin, currententity.origin, delta)
	shared_c.AngleVectors (currententity.angles, vectors[0], vectors[1], vectors[2])

	move[0] = shared.DotProduct (delta, vectors[0])	# forward
	move[1] = -shared.DotProduct (delta, vectors[1])	# left
	move[2] = shared.DotProduct (delta, vectors[2])	# up

	shared.VectorAdd (move, oldframe.translate, move)

	for i in range(3):

		move[i] = backlerp*move[i] + frontlerp*frame.translate[i]

	frontv = frontlerp*frame.scale
	backv = backlerp*oldframe.scale

	lerp = s_lerped

	R_LerpVerts( paliashdr.num_xyz, v, ov, verts, lerp, move, frontv, backv )

	# Q2PORT: the C walks the glcmds and draws each strip and fan with
	# qglBegin, one call per vertex and qglEnd (see the loops quoted below).
	# One python GL call per vertex is too slow, so both paths gather the
	# vertex data into the draw list order of paliashdr.drawtris_xyz (the
	# glcmds unrolled into triangles by Mod_LoadAliasModel) and draw the
	# model with one glDrawArrays. The arrays enabled here are disabled
	# again afterwards, as a later shell model would otherwise draw with a
	# stale color array.
	drawtris_xyz = paliashdr.drawtris_xyz
	lerped = s_lerped[drawtris_xyz]

	if gl1_main.gl_vertex_arrays.value:
	
		#float colorArray[MAX_VERTS*4];
		colorArray = s_colorArray

		GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
		GL.glVertexPointer( 3, GL.GL_FLOAT, 0, lerped )	# C points at s_lerped with a stride of 16, padded for SIMD

#		if ( currententity->flags & ( RF_SHELL_RED | RF_SHELL_GREEN | RF_SHELL_BLUE ) )
		# PMM - added double damage shell
		if currententity.flags & SHELL_FLAGS:
		
			GL.glColor4f( shadelight[0], shadelight[1], shadelight[2], alpha )
		
		else:
		
			GL.glEnableClientState( GL.GL_COLOR_ARRAY )

			#
			# pre light everything
			#
			# for ( i = 0; i < paliashdr->num_xyz; i++ ) colorArray[i*3+n] = shadedots[verts[i].lightnormalindex] * shadelight[n]
			l = shadedots[verts[:paliashdr.num_xyz, 3]]
			colorArray[:paliashdr.num_xyz] = l[:, np.newaxis] * shadelight

			colors = colorArray[drawtris_xyz]
			GL.glColorPointer( 3, GL.GL_FLOAT, 0, colors )	# C points at colorArray

			# texture coordinates come from the draw list
			GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )
			GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, paliashdr.drawtris_st )
		
		if qgl_linux.qglLockArraysEXT:
			GLcva.glLockArraysEXT( 0, len(drawtris_xyz) )	# C locks paliashdr->num_xyz

		"""
		while (1)
		{
			// get the vertex count and primitive type
			count = *order++;
			if (!count)
				break;		// done
			if (count < 0)
			{
				count = -count;
				qglBegin (GL_TRIANGLE_FAN);
			}
			else
			{
				qglBegin (GL_TRIANGLE_STRIP);
			}

			// PMM - added double damage shell
			if ( currententity->flags & ( RF_SHELL_RED | RF_SHELL_GREEN | RF_SHELL_BLUE | RF_SHELL_DOUBLE | RF_SHELL_HALF_DAM) )
			{
				do
				{
					index_xyz = order[2];
					order += 3;

					qglVertex3fv( s_lerped[index_xyz] );

				} while (--count);
			}
			else
			{
				do
				{
					// texture coordinates come from the draw list
					qglTexCoord2f (((float *)order)[0], ((float *)order)[1]);
					index_xyz = order[2];

					order += 3;

					// normals and vertexes come from the frame list
//					l = shadedots[verts[index_xyz].lightnormalindex];
					
//					qglColor4f (l* shadelight[0], l*shadelight[1], l*shadelight[2], alpha);
					qglArrayElement( index_xyz );

				} while (--count);
			}
			qglEnd ();
		}
		"""
		GL.glDrawArrays( GL.GL_TRIANGLES, 0, len(drawtris_xyz) )

		if qgl_linux.qglUnlockArraysEXT:
			GLcva.glUnlockArraysEXT()

		GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )
		GL.glDisableClientState( GL.GL_COLOR_ARRAY )
		GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	else:

		"""
		while (1)
		{
			// get the vertex count and primitive type
			count = *order++;
			if (!count)
				break;		// done
			if (count < 0)
			{
				count = -count;
				qglBegin (GL_TRIANGLE_FAN);
			}
			else
			{
				qglBegin (GL_TRIANGLE_STRIP);
			}

			if ( currententity->flags & ( RF_SHELL_RED | RF_SHELL_GREEN | RF_SHELL_BLUE ) )
			{
				do
				{
					index_xyz = order[2];
					order += 3;

					qglColor4f( shadelight[0], shadelight[1], shadelight[2], alpha);
					qglVertex3fv (s_lerped[index_xyz]);

				} while (--count);
			}
			else
			{
				do
				{
					// texture coordinates come from the draw list
					qglTexCoord2f (((float *)order)[0], ((float *)order)[1]);
					index_xyz = order[2];
					order += 3;

					// normals and vertexes come from the frame list
					l = shadedots[verts[index_xyz].lightnormalindex];
					
					qglColor4f (l* shadelight[0], l*shadelight[1], l*shadelight[2], alpha);
					qglVertex3fv (s_lerped[index_xyz]);
				} while (--count);
			}

			qglEnd ();
		}
		"""
		GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
		GL.glVertexPointer( 3, GL.GL_FLOAT, 0, lerped )	# qglVertex3fv (s_lerped[index_xyz]);

		if currententity.flags & ( shared.RF_SHELL_RED | shared.RF_SHELL_GREEN | shared.RF_SHELL_BLUE ):

			GL.glColor4f( shadelight[0], shadelight[1], shadelight[2], alpha)

		else:

			# texture coordinates come from the draw list
			GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )
			GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, paliashdr.drawtris_st )

			# normals and vertexes come from the frame list
			l = shadedots[verts[drawtris_xyz, 3]]

			colors = np.empty((len(drawtris_xyz), 4), dtype=np.float32) # qglColor4f (l* shadelight[0], l*shadelight[1], l*shadelight[2], alpha);
			colors[:, :3] = l[:, np.newaxis] * shadelight
			colors[:, 3] = alpha
			GL.glEnableClientState( GL.GL_COLOR_ARRAY )
			GL.glColorPointer( 4, GL.GL_FLOAT, 0, colors )

		GL.glDrawArrays( GL.GL_TRIANGLES, 0, len(drawtris_xyz) )

		GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )
		GL.glDisableClientState( GL.GL_COLOR_ARRAY )
		GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

#	if ( currententity->flags & ( RF_SHELL_RED | RF_SHELL_GREEN | RF_SHELL_BLUE ) )
	# PMM - added double damage shell
	if currententity.flags & SHELL_FLAGS:
		GL.glEnable( GL.GL_TEXTURE_2D )


"""
=============
R_DrawAliasShadow
=============
"""
def R_DrawAliasShadow (paliashdr, posenum): #dmdl_t *, int

	"""
	dtrivertx_t	*verts;
	int		*order;
	vec3_t	point;
	float	height, lheight;
	int		count;
	daliasframe_t	*frame;
	"""
	currententity = gl1_main.currententity

	lheight = currententity.origin[2] - gl1_light.lightspot[2]

	frame = paliashdr.frames[currententity.frame]
	verts = frame.verts

	height = 0

	order = paliashdr.glcmds

	height = -lheight + 1.0

	point = np.zeros((3,), dtype=np.float32)
	o = 0 # order offset
	while True:

		# get the vertex count and primitive type
		count = order[o]
		o += 1
		if not count:
			break		# done
		if count < 0:

			count = -count
			GL.glBegin (GL.GL_TRIANGLE_FAN)

		else:
			GL.glBegin (GL.GL_TRIANGLE_STRIP)

		for _ in range(count):

			# normals and vertexes come from the frame list
			"""
			point[0] = verts[order[2]].v[0] * frame->scale[0] + frame->translate[0];
			point[1] = verts[order[2]].v[1] * frame->scale[1] + frame->translate[1];
			point[2] = verts[order[2]].v[2] * frame->scale[2] + frame->translate[2];
			"""

			point[:] = s_lerped[order[o+2]] # memcpy( point, s_lerped[order[2]], sizeof( point )  );

			point[0] -= shadevector[0]*(point[2]+lheight)
			point[1] -= shadevector[1]*(point[2]+lheight)
			point[2] = height
#			height -= 0.001;
			GL.glVertex3fv (point)

			o += 3

#			verts++;

		GL.glEnd ()


"""
** R_CullAliasModel
"""
def R_CullAliasModel (bbox, e): #vec3_t[8], entity_t * (returns qboolean)

	"""
	int i;
	vec3_t		mins, maxs;
	dmdl_t		*paliashdr;
	vec3_t		vectors[3];
	vec3_t		thismins, oldmins, thismaxs, oldmaxs;
	daliasframe_t *pframe, *poldframe;
	vec3_t angles;
	"""
	currentmodel = gl1_main.currentmodel

	paliashdr = currentmodel.extradata

	if ( e.frame >= paliashdr.num_frames ) or ( e.frame < 0 ):

		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "R_CullAliasModel {}: no such frame {}\n".format(
			currentmodel.name, e.frame))
		e.frame = 0

	if ( e.oldframe >= paliashdr.num_frames ) or ( e.oldframe < 0 ):

		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "R_CullAliasModel {}: no such oldframe {}\n".format(
			currentmodel.name, e.oldframe))
		e.oldframe = 0

	pframe = paliashdr.frames[e.frame]

	poldframe = paliashdr.frames[e.oldframe]

	#
	# compute axially aligned mins and maxs
	#
	mins = np.zeros((3,), dtype=np.float32)
	maxs = np.zeros((3,), dtype=np.float32)
	if pframe is poldframe:

		for i in range(3):

			mins[i] = pframe.translate[i]
			maxs[i] = mins[i] + pframe.scale[i]*255

	else:

		for i in range(3):

			thismins = pframe.translate[i]
			thismaxs = thismins + pframe.scale[i]*255

			oldmins  = poldframe.translate[i]
			oldmaxs  = oldmins + poldframe.scale[i]*255

			if thismins < oldmins:
				mins[i] = thismins
			else:
				mins[i] = oldmins

			if thismaxs > oldmaxs:
				maxs[i] = thismaxs
			else:
				maxs[i] = oldmaxs

	#
	# compute a full bounding box
	#
	for i in range(8):

		tmp = np.zeros((3,), dtype=np.float32) #vec3_t

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

		shared.VectorCopy( tmp, bbox[i] )

	#
	# rotate the bounding box
	#
	angles = e.angles.copy() # VectorCopy( e->angles, angles );
	angles[gl1_main.YAW] = -angles[gl1_main.YAW]
	vectors = [np.zeros((3,), dtype=np.float32) for _ in range(3)]
	shared_c.AngleVectors( angles, vectors[0], vectors[1], vectors[2] )

	for i in range(8):

		tmp = bbox[i].copy() # VectorCopy( bbox[i], tmp );

		bbox[i][0] = shared.DotProduct( vectors[0], tmp )
		bbox[i][1] = -shared.DotProduct( vectors[1], tmp )
		bbox[i][2] = shared.DotProduct( vectors[2], tmp )

		shared.VectorAdd( e.origin, bbox[i], bbox[i] )

	#int p, f, aggregatemask = ~0;
	aggregatemask = ~0

	for p in range(8):

		mask = 0

		for f in range(4):

			dp = shared.DotProduct( gl1_main.frustum[f].normal, bbox[p] )

			if ( dp - gl1_main.frustum[f].dist ) < 0:

				mask |= ( 1 << f )

		aggregatemask &= mask

	if aggregatemask:
		return True

	return False


"""
=================
R_DrawAliasModel

=================
"""
def R_DrawAliasModel (e): #entity_t *

	global shadedots

	"""
	int			i;
	dmdl_t		*paliashdr;
	float		an;
	vec3_t		bbox[8];
	image_t		*skin;
	"""
	currententity = gl1_main.currententity
	currentmodel = gl1_main.currentmodel
	bbox = np.zeros((8, 3), dtype=np.float32)

	if not ( e.flags & shared.RF_WEAPONMODEL ):

		if R_CullAliasModel( bbox, e ):
			return

	if e.flags & shared.RF_WEAPONMODEL:

		if gl1_main.gl_lefthand.value == 2:
			return

	paliashdr = currentmodel.extradata

	#
	# get lighting information
	#
	# PMM - rewrote, reordered to handle new shells & mixing
	# PMM - 3.20 code .. replaced with original way of doing it to keep mod authors happy
	#
	if currententity.flags & ( shared.RF_SHELL_HALF_DAM | shared.RF_SHELL_GREEN | shared.RF_SHELL_RED | shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE ):

		shared.VectorClear (shadelight)
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

		gl1_light.R_LightPoint (currententity, currententity.origin, shadelight)

		# player lighting hack for communication back to server
		# big hack!
		if currententity.flags & shared.RF_WEAPONMODEL:

			# pick the greatest component, which should be the same
			# as the mono value returned by software
			if shadelight[0] > shadelight[1]:

				if shadelight[0] > shadelight[2]:
					gl1_main.r_lightlevel.value = 150*shadelight[0]
				else:
					gl1_main.r_lightlevel.value = 150*shadelight[2]

			else:

				if shadelight[1] > shadelight[2]:
					gl1_main.r_lightlevel.value = 150*shadelight[1]
				else:
					gl1_main.r_lightlevel.value = 150*shadelight[2]

	if currententity.flags & shared.RF_MINLIGHT:

		for i in range(3):
			if shadelight[i] > 0.1:
				break
		else: # i == 3 in C

			shadelight[0] = 0.1
			shadelight[1] = 0.1
			shadelight[2] = 0.1

	if currententity.flags & shared.RF_GLOW:
		# bonus items will pulse with time
		#float	scale;
		#float	min;

		scale = 0.1 * math.sin(gl1_main.r_newrefdef.time*7)
		for i in range(3):

			min_light = shadelight[i] * 0.8
			shadelight[i] += scale
			if shadelight[i] < min_light:
				shadelight[i] = min_light

# =================
# PGM	ir goggles color override
	if gl1_main.r_newrefdef.rdflags & shared.RDF_IRGOGGLES and currententity.flags & shared.RF_IR_VISIBLE:

		shadelight[0] = 1.0
		shadelight[1] = 0.0
		shadelight[2] = 0.0

# PGM
# =================

	shadedots = r_avertexnormal_dots[(int(currententity.angles[1] * (SHADEDOT_QUANT / 360.0))) & (SHADEDOT_QUANT - 1)]

	an = currententity.angles[1]/180*math.pi
	shadevector[0] = math.cos(-an)
	shadevector[1] = math.sin(-an)
	shadevector[2] = 1
	shared_c.VectorNormalize (shadevector)

	#
	# locate the proper data
	#

	gl1_main.c_alias_polys += paliashdr.num_tris

	#
	# draw all the triangles
	#
	if currententity.flags & shared.RF_DEPTHHACK: # hack the depth range to prevent view model from poking into walls
		GL.glDepthRange (gl1_main.gldepthmin, gl1_main.gldepthmin + 0.3*(gl1_main.gldepthmax-gl1_main.gldepthmin))

	# Q2PORT: Yamagi sets up the weapon projection (r_gunfov, left hand) in
	# R_ApplyGLBuffer's buf_alias case; this immediate-mode draw does it here
	if currententity.flags & shared.RF_WEAPONMODEL:

		GL.glMatrixMode( GL.GL_PROJECTION )
		GL.glPushMatrix()
		GL.glLoadIdentity()

		if gl1_main.gl_lefthand.value == 1.0:
			GL.glScalef( -1, 1, 1 )

		gl1_main.R_SetPerspective( gl1_main.r_newrefdef.fov_y if (gl1_main.r_gunfov.value < 0) else gl1_main.r_gunfov.value )

		GL.glMatrixMode( GL.GL_MODELVIEW )

		if gl1_main.gl_lefthand.value == 1.0:
			GL.glCullFace( GL.GL_BACK )

	GL.glPushMatrix ()
	e.angles[gl1_main.PITCH] = -e.angles[gl1_main.PITCH]	# sigh.
	gl1_main.R_RotateForEntity (e)
	e.angles[gl1_main.PITCH] = -e.angles[gl1_main.PITCH]	# sigh.

	# select skin
	if currententity.skin is not None:
		skin = currententity.skin	# custom player skin
	else:

		if currententity.skinnum >= files_h.MAX_MD2SKINS:
			skin = currentmodel.skins[0]
		else:

			skin = currentmodel.skins[currententity.skinnum]
			if skin is None:
				skin = currentmodel.skins[0]

	if skin is None:
		skin = gl1_main.r_notexture	# fallback...
	# FIXME r_notexture is None until R_InitParticleTexture is ported, so draw untextured
	gl1_image.R_Bind(skin.texnum if skin is not None else 0)

	# draw it

	GL.glShadeModel (GL.GL_SMOOTH)

	gl1_image.R_TexEnv( GL.GL_MODULATE )
	if currententity.flags & shared.RF_TRANSLUCENT:

		GL.glEnable (GL.GL_BLEND)

	if ( (currententity.frame >= paliashdr.num_frames)
		or (currententity.frame < 0) ):

		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "R_DrawAliasModel {}: no such frame {}\n".format(
			currentmodel.name, currententity.frame))
		currententity.frame = 0
		currententity.oldframe = 0

	if ( (currententity.oldframe >= paliashdr.num_frames)
		or (currententity.oldframe < 0)):

		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "R_DrawAliasModel {}: no such oldframe {}\n".format(
			currentmodel.name, currententity.oldframe))
		currententity.frame = 0
		currententity.oldframe = 0

	if not gl1_main.r_lerpmodels.value:
		currententity.backlerp = 0
	R_DrawAliasFrameLerp (paliashdr, currententity.backlerp)

	gl1_image.R_TexEnv( GL.GL_REPLACE )
	GL.glShadeModel (GL.GL_FLAT)

	GL.glPopMatrix ()

	"""
#if 0
	qglDisable( GL_CULL_FACE );
	qglPolygonMode( GL_FRONT_AND_BACK, GL_LINE );
	qglDisable( GL_TEXTURE_2D );
	qglBegin( GL_TRIANGLE_STRIP );
	for ( i = 0; i < 8; i++ )
	{
		qglVertex3fv( bbox[i] );
	}
	qglEnd();
	qglEnable( GL_TEXTURE_2D );
	qglPolygonMode( GL_FRONT_AND_BACK, GL_FILL );
	qglEnable( GL_CULL_FACE );
#endif
	"""

	if currententity.flags & shared.RF_WEAPONMODEL:

		GL.glMatrixMode( GL.GL_PROJECTION )
		GL.glPopMatrix()
		GL.glMatrixMode( GL.GL_MODELVIEW )
		if gl1_main.gl_lefthand.value == 1.0:
			GL.glCullFace( GL.GL_FRONT )

	if currententity.flags & shared.RF_TRANSLUCENT:

		GL.glDisable (GL.GL_BLEND)

	if currententity.flags & shared.RF_DEPTHHACK:
		GL.glDepthRange (gl1_main.gldepthmin, gl1_main.gldepthmax)

#if 1
	if gl1_main.gl_shadows.value and not (currententity.flags & (shared.RF_TRANSLUCENT | shared.RF_WEAPONMODEL)):

		GL.glPushMatrix ()
		gl1_main.R_RotateForEntity (e)
		GL.glDisable (GL.GL_TEXTURE_2D)
		GL.glEnable (GL.GL_BLEND)
		GL.glColor4f (0,0,0,0.5)
		R_DrawAliasShadow (paliashdr, currententity.frame )
		GL.glEnable (GL.GL_TEXTURE_2D)
		GL.glDisable (GL.GL_BLEND)
		GL.glPopMatrix ()

#endif
	GL.glColor4f (1,1,1,1)
