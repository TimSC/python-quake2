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

import os
import sys
import math
import struct
import copy
import OpenGL.GL as GL
import OpenGL.GLU as GLU
import numpy as np
from OpenGL.GL import glGetString
from enum import Enum
from client import ref
from linux import qgl_linux
from client.vid import glimp_sdl2
pass
pass
from client.refresh.gl1 import gl1_draw, gl1_image, gl1_misc, gl1_model, gl1_warp, gl1_surf, gl1_mesh, gl1_light
from client.refresh.gl1.header import model
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c

REF_VERSION = "GL 0.01"

# up / down
PITCH	= 0

# left / right
YAW		= 1

# fall over
ROLL	= 2

class rserr_t(Enum):

	rserr_ok = 0

	rserr_invalid_fullscreen = 1
	rserr_invalid_mode = 2

	rserr_unknown = 3

# from gl_local.h
GL_RENDERER_VOODOO = 0x00000001
GL_RENDERER_VOODOO2 = 0x00000002
GL_RENDERER_VOODOO_RUSH = 0x00000004
GL_RENDERER_BANSHEE = 0x00000008
GL_RENDERER_3DFX = 0x0000000F
GL_RENDERER_PCX1 = 0x00000010
GL_RENDERER_PCX2 = 0x00000020
GL_RENDERER_PMX = 0x00000040
GL_RENDERER_POWERVR = 0x00000070
GL_RENDERER_PERMEDIA2 = 0x00000100
GL_RENDERER_GLINT_MX = 0x00000200
GL_RENDERER_GLINT_TX = 0x00000400
GL_RENDERER_3DLABS_MISC = 0x00000800
GL_RENDERER_3DLABS = 0x00000F00
GL_RENDERER_REALIZM = 0x00001000
GL_RENDERER_REALIZM2 = 0x00002000
GL_RENDERER_INTERGRAPH = 0x00003000
GL_RENDERER_3DPRO = 0x00004000
GL_RENDERER_REAL3D = 0x00008000
GL_RENDERER_RIVA128 = 0x00010000
GL_RENDERER_DYPIC = 0x00020000
GL_RENDERER_V1000 = 0x00040000
GL_RENDERER_V2100 = 0x00080000
GL_RENDERER_V2200 = 0x00100000
GL_RENDERER_RENDITION = 0x001C0000
GL_RENDERER_O2 = 0x00100000
GL_RENDERER_IMPACT = 0x00200000
GL_RENDERER_RE = 0x00400000
GL_RENDERER_IR = 0x00800000
GL_RENDERER_SGI = 0x00F00000
GL_RENDERER_MCD = 0x01000000
GL_RENDERER_OTHER = 0x80000000

class glconfig_t(object):

	def __init__(self):

		self.renderer = None #int
		self.renderer_string = None #const char *
		self.vendor_string = None #const char *
		self.version_string = None #const char *
		self.extensions_string = None #const char *

		self.allow_cds = True #qboolean

class glstate_t(object):
	def __init__(self):

		self.inverse_intensity = None #float
		self.fullscreen = None #qboolean

		self.prev_mode = None #int

		self.d_16to8table = None #unsigned char *

		self.lightmap_textures = None #int

		self.currenttextures = [None, None] #int[2]
		self.currenttmu = 0 #int

		self.camera_separation = None #float
		self.stereo_enabled = None #qboolean

		self.originalRedGammaTable = [] #unsigned char [256]
		self.originalGreenGammaTable = [] #unsigned char [256]
		self.originalBlueGammaTable = [] #unsigned char [256]

class viddef_t(object):
	def __init__(self):
		self.width, self.height = 800, 600 # coordinates from main game

vid = viddef_t()

ri = ref.refimport_t()
"""
int GL_TEXTURE0, GL_TEXTURE1;
"""
frustum = [shared.cplane_t() for _ in range(4)]

frustum = [shared.cplane_t() for _ in range(4)]

r_worldmodel = None #model_t *

gldepthmin, gldepthmax = 0.0, 0.0 #float

gl_config = glconfig_t()

gl_state = glstate_t()

r_notexture = None # image_t *, use for bad textures
r_particletexture = None # image_t *, little dot for particles

currententity = None # entity_t *

currentmodel = None # model_t *
 
c_brush_polys = 0 # int
c_alias_polys = 0 # int
"""
cplane_t	frustum[4];

int			c_brush_polys, c_alias_polys;

void GL_Strings_f( void );
"""
v_blend = np.zeros((4,), dtype=np.float32) #float[4], final blending color

#
# view origin
#
vup = np.zeros((3,), dtype=np.float32)
vpn = np.zeros((3,), dtype=np.float32)
vright = np.zeros((3,), dtype=np.float32)
r_origin = np.zeros((3,), dtype=np.float32)

r_world_matrix = np.zeros((16,), dtype=np.float32)
r_base_world_matrix = np.zeros((16,), dtype=np.float32)

#
# screen size info
#
r_newrefdef = ref.refdef_t()

r_viewcluster = -1
r_viewcluster2 = -1
r_oldviewcluster = -1
r_oldviewcluster2 = -1

r_visframecount = 0
r_framecount = 0


def SignbitsForPlane(out):
    bits = 0
    for j in range(3):
        if out.normal[j] < 0:
            bits |= 1 << j
    return bits


def R_SetFrustum():
    shared_c.RotatePointAroundVector(
        frustum[0].normal,
        vup,
        vpn,
        -(90 - r_newrefdef.fov_x / 2.0),
    )
    shared_c.RotatePointAroundVector(
        frustum[1].normal,
        vup,
        vpn,
        90 - r_newrefdef.fov_x / 2.0,
    )
    shared_c.RotatePointAroundVector(
        frustum[2].normal,
        vright,
        vpn,
        90 - r_newrefdef.fov_y / 2.0,
    )
    shared_c.RotatePointAroundVector(
        frustum[3].normal,
        vright,
        vpn,
        -(90 - r_newrefdef.fov_y / 2.0),
    )

    for i in range(4):
        frustum[i].type = files_h.PLANE_ANYZ
        frustum[i].dist = shared.DotProduct(r_origin, frustum[i].normal)
        frustum[i].signbits = SignbitsForPlane(frustum[i])
"""
=================
R_CullBox

Returns true if the box is completely outside the frustom
=================
"""
def R_CullBox (mins, maxs): #vec3_t, vec3_t (returns qboolean)

	#int		i;

	if r_nocull.value:
		return False

	#Q2PORT: BOX_ON_PLANE_SIDE inlined as in the C macro; the frustum
	#planes are always PLANE_ANYZ, so only the most positive corner of
	#the box needs testing against each plane
	for p in frustum:

		n = p.normal
		sb = p.signbits
		if sb & 1:
			dist = n[0]*mins[0]
		else:
			dist = n[0]*maxs[0]
		if sb & 2:
			dist += n[1]*mins[1]
		else:
			dist += n[1]*maxs[1]
		if sb & 4:
			dist += n[2]*mins[2]
		else:
			dist += n[2]*maxs[2]

		if p.dist >= dist: # side == 2, box fully on the negative side
			return True
	return False


def R_RotateForEntity (e): #entity_t *

	GL.glTranslatef (e.origin[0],  e.origin[1],  e.origin[2])

	GL.glRotatef (e.angles[1],  0, 0, 1)
	GL.glRotatef (-e.angles[0],  0, 1, 0)
	GL.glRotatef (-e.angles[2],  1, 0, 0)

"""
=============================================================

  SPRITE MODELS

=============================================================
"""

"""
=================
R_DrawSpriteModel

=================
"""
def R_DrawSpriteModel (e): #entity_t *

	"""
	float alpha = 1.0F;
	vec3_t	point;
	dsprframe_t	*frame;
	float		*up, *right;
	dsprite_t		*psprite;
	"""
	alpha = 1.0
	point = np.zeros((3,), dtype=np.float32)

	# don't even bother culling, because it's just a single
	# polygon without a surface cache

	psprite = currentmodel.extradata

	e.frame %= psprite.numframes

	frame = psprite.frames[e.frame]

	"""
#if 0
	if (psprite->type == SPR_ORIENTED)
	{	// bullet marks on walls
	vec3_t		v_forward, v_right, v_up;

	AngleVectors (currententity->angles, v_forward, v_right, v_up);
		up = v_up;
		right = v_right;
	}
	else
#endif
	"""
	# normal sprite
	up = vup
	right = vright

	if e.flags & shared.RF_TRANSLUCENT:
		alpha = e.alpha

	if alpha != 1.0:
		GL.glEnable( GL.GL_BLEND )

	GL.glColor4f( 1, 1, 1, alpha )

	gl1_image.GL_Bind(currentmodel.skins[e.frame].texnum)

	gl1_image.GL_TexEnv( GL.GL_MODULATE )

	if alpha == 1.0:
		GL.glEnable (GL.GL_ALPHA_TEST)
	else:
		GL.glDisable( GL.GL_ALPHA_TEST )

	GL.glBegin (GL.GL_QUADS)

	GL.glTexCoord2f (0, 1)
	shared_c.VectorMA (e.origin, -frame.origin_y, up, point)
	shared_c.VectorMA (point, -frame.origin_x, right, point)
	GL.glVertex3fv (point)

	GL.glTexCoord2f (0, 0)
	shared_c.VectorMA (e.origin, frame.height - frame.origin_y, up, point)
	shared_c.VectorMA (point, -frame.origin_x, right, point)
	GL.glVertex3fv (point)

	GL.glTexCoord2f (1, 0)
	shared_c.VectorMA (e.origin, frame.height - frame.origin_y, up, point)
	shared_c.VectorMA (point, frame.width - frame.origin_x, right, point)
	GL.glVertex3fv (point)

	GL.glTexCoord2f (1, 1)
	shared_c.VectorMA (e.origin, -frame.origin_y, up, point)
	shared_c.VectorMA (point, frame.width - frame.origin_x, right, point)
	GL.glVertex3fv (point)
	
	GL.glEnd ()

	GL.glDisable (GL.GL_ALPHA_TEST)
	gl1_image.GL_TexEnv( GL.GL_REPLACE )

	if alpha != 1.0:
		GL.glDisable( GL.GL_BLEND )

	GL.glColor4f( 1, 1, 1, 1 )

#==================================================================================

"""
=============
R_DrawNullModel
=============
"""
def R_DrawNullModel ():

	"""
	vec3_t	shadelight;
	int		i;
	"""
	shadelight = np.zeros((3,), dtype=np.float32)

	if currententity.flags & shared.RF_FULLBRIGHT:
		shadelight[0] = shadelight[1] = shadelight[2] = 1.0
	else:
		gl1_light.R_LightPoint (currententity.origin, shadelight)

	GL.glPushMatrix ()
	R_RotateForEntity (currententity)

	GL.glDisable (GL.GL_TEXTURE_2D)
	GL.glColor3fv (shadelight)

	GL.glBegin (GL.GL_TRIANGLE_FAN)
	GL.glVertex3f (0, 0, -16)
	for i in range(5):
		GL.glVertex3f (16*math.cos(i*math.pi/2), 16*math.sin(i*math.pi/2), 0)
	GL.glEnd ()

	GL.glBegin (GL.GL_TRIANGLE_FAN)
	GL.glVertex3f (0, 0, 16)
	for i in range(4, -1, -1):
		GL.glVertex3f (16*math.cos(i*math.pi/2), 16*math.sin(i*math.pi/2), 0)
	GL.glEnd ()

	GL.glColor3f (1,1,1)
	GL.glPopMatrix ()
	GL.glEnable (GL.GL_TEXTURE_2D)


"""
=============
R_DrawEntitiesOnList
=============
"""
def R_DrawEntitiesOnList ():

	global currententity, currentmodel

	#int		i;

	if not r_drawentities.value:
		return

	# draw non-transparent first
	for i in range(r_newrefdef.num_entities):
	
		currententity = r_newrefdef.entities[i]
		if currententity.flags & shared.RF_TRANSLUCENT:
			continue	# solid

		if currententity.flags & shared.RF_BEAM:
		
			R_DrawBeam( currententity )
		
		else:
		
			currentmodel = currententity.model
			if not currentmodel:
			
				R_DrawNullModel ()
				continue
			
			if currentmodel.type == model.modtype_t.mod_alias:
				gl1_mesh.R_DrawAliasModel (currententity)
			elif currentmodel.type == model.modtype_t.mod_brush:
				gl1_surf.R_DrawBrushModel (currententity)
			elif currentmodel.type == model.modtype_t.mod_sprite:
				R_DrawSpriteModel (currententity)
			else:
				ri.Sys_Error (shared.ERR_DROP, "Bad modeltype")
			

	# draw transparent entities
	# we could sort these if it ever becomes a problem...
	GL.glDepthMask (0)		# no z writes
	for i in range(r_newrefdef.num_entities):
	
		currententity = r_newrefdef.entities[i]
		if not (currententity.flags & shared.RF_TRANSLUCENT):
			continue	# solid

		if currententity.flags & shared.RF_BEAM:
		
			R_DrawBeam( currententity )
		
		else:
		
			currentmodel = currententity.model
			if not currentmodel:
			
				R_DrawNullModel ()
				continue
			
			if currentmodel.type == model.modtype_t.mod_alias:
				gl1_mesh.R_DrawAliasModel (currententity)
			elif currentmodel.type == model.modtype_t.mod_brush:
				gl1_surf.R_DrawBrushModel (currententity)
			elif currentmodel.type == model.modtype_t.mod_sprite:
				R_DrawSpriteModel (currententity)
			else:
				ri.Sys_Error (shared.ERR_DROP, "Bad modeltype")
			

	GL.glDepthMask (1)		# back to writing

"""
** GL_DrawParticles
**
"""
def GL_DrawParticles( num_particles, particles, colortable ): #int, const particle_t [], const unsigned [768]

	"""
	const particle_t *p;
	int				i;
	vec3_t			up, right;
	float			scale;
	byte			color[4];
	"""
	up = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)

	gl1_image.GL_Bind(r_particletexture.texnum)
	GL.glDepthMask( GL.GL_FALSE )		# no z buffering
	GL.glEnable( GL.GL_BLEND )
	gl1_image.GL_TexEnv( GL.GL_MODULATE )
	GL.glBegin( GL.GL_TRIANGLES )

	shared_c.VectorScale (vup, 1.5, up)
	shared_c.VectorScale (vright, 1.5, right)

	for i in range(num_particles):
	
		p = particles[i]
		# hack a scale up to keep particles from disapearing
		scale = ( p.origin[0] - r_origin[0] ) * vpn[0] + \
				( p.origin[1] - r_origin[1] ) * vpn[1] + \
				( p.origin[2] - r_origin[2] ) * vpn[2]

		if scale < 20:
			scale = 1
		else:
			scale = 1 + scale * 0.004

		color = colortable[p.color] # *(int *)color = colortable[p->color];

		GL.glColor4ub( color[0], color[1], color[2], int(p.alpha*255) ) # color[3] = p->alpha*255;

		GL.glTexCoord2f( 0.0625, 0.0625 )
		GL.glVertex3fv( p.origin )

		GL.glTexCoord2f( 1.0625, 0.0625 )
		GL.glVertex3f( p.origin[0] + up[0]*scale, 
					 p.origin[1] + up[1]*scale, 
					 p.origin[2] + up[2]*scale)

		GL.glTexCoord2f( 0.0625, 1.0625 )
		GL.glVertex3f( p.origin[0] + right[0]*scale, 
					 p.origin[1] + right[1]*scale, 
					 p.origin[2] + right[2]*scale)
	
	GL.glEnd ()
	GL.glDisable( GL.GL_BLEND )
	GL.glColor4f( 1,1,1,1 )
	GL.glDepthMask( 1 )		# back to normal Z buffering
	gl1_image.GL_TexEnv( GL.GL_REPLACE )

"""
===============
R_DrawParticles
===============
"""
def R_DrawParticles ():

	if gl_ext_pointparameters.value and qgl_linux.qglPointParameterfEXT:
	
		#int i;
		#unsigned char color[4];
		#const particle_t *p;

		GL.glDepthMask( GL.GL_FALSE )
		GL.glEnable( GL.GL_BLEND )
		GL.glDisable( GL.GL_TEXTURE_2D )

		GL.glPointSize( gl_particle_size.value )

		GL.glBegin( GL.GL_POINTS )
		for i in range(r_newrefdef.num_particles):
		
			p = r_newrefdef.particles[i]
			color = gl1_image.d_8to24table[p.color] # *(int *)color = d_8to24table[p->color];

			GL.glColor4ub( color[0], color[1], color[2], int(p.alpha*255) ) # color[3] = p->alpha*255;

			GL.glVertex3fv( p.origin )
		
		GL.glEnd()

		GL.glDisable( GL.GL_BLEND )
		GL.glColor4f( 1.0, 1.0, 1.0, 1.0 )
		GL.glDepthMask( GL.GL_TRUE )
		GL.glEnable( GL.GL_TEXTURE_2D )

	
	else:
	
		GL_DrawParticles( r_newrefdef.num_particles, r_newrefdef.particles, gl1_image.d_8to24table )
	

"""
============
R_PolyBlend
============
"""
def R_PolyBlend ():

	if not gl_polyblend.value:
		return
	if not v_blend[3]:
		return

	GL.glDisable (GL.GL_ALPHA_TEST)
	GL.glEnable (GL.GL_BLEND)
	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glDisable (GL.GL_TEXTURE_2D)

	GL.glLoadIdentity ()

	# FIXME: get rid of these
	GL.glRotatef (-90,  1, 0, 0)		# put Z going up
	GL.glRotatef (90,  0, 0, 1)		# put Z going up

	GL.glColor4fv (v_blend)

	GL.glBegin (GL.GL_QUADS)

	GL.glVertex3f (10, 100, 100)
	GL.glVertex3f (10, -100, 100)
	GL.glVertex3f (10, -100, -100)
	GL.glVertex3f (10, 100, -100)
	GL.glEnd ()

	GL.glDisable (GL.GL_BLEND)
	GL.glEnable (GL.GL_TEXTURE_2D)
	GL.glEnable (GL.GL_ALPHA_TEST)

	GL.glColor4f(1,1,1,1)

"""

//=======================================================================

/*
===============
R_SetupFrame
===============
"""

def R_SetupFrame ():

	global r_framecount, r_oldviewcluster, r_oldviewcluster2, r_viewcluster, r_viewcluster2, \
		c_brush_polys, c_alias_polys

	"""
	int i;
	mleaf_t	*leaf;
	"""

	r_framecount += 1

	# build the transformation matrix for the given view angles
	shared.VectorCopy (r_newrefdef.vieworg, r_origin)

	shared_c.AngleVectors (r_newrefdef.viewangles, vpn, vright, vup)

	# current viewcluster
	if not ( r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL ):
	
		r_oldviewcluster = r_viewcluster
		r_oldviewcluster2 = r_viewcluster2
		leaf = gl1_model.Mod_PointInLeaf (r_origin, r_worldmodel)
		r_viewcluster = r_viewcluster2 = leaf.cluster

		# check above and below so crossing solid water doesn't draw wrong
		if not leaf.contents:
			# look down a bit
			temp = np.zeros((3,), dtype=np.float32) #vec3_t

			shared.VectorCopy (r_origin, temp)
			temp[2] -= 16
			leaf = gl1_model.Mod_PointInLeaf (temp, r_worldmodel)
			if ( not (leaf.contents & shared.CONTENTS_SOLID) and
				(leaf.cluster != r_viewcluster2) ):
				r_viewcluster2 = leaf.cluster
		
		else:
			# look up a bit
			temp = np.zeros((3,), dtype=np.float32) #vec3_t

			shared.VectorCopy (r_origin, temp)
			temp[2] += 16
			leaf = gl1_model.Mod_PointInLeaf (temp, r_worldmodel)
			if ( not (leaf.contents & shared.CONTENTS_SOLID) and
				(leaf.cluster != r_viewcluster2) ):
				r_viewcluster2 = leaf.cluster
		
	for i in range(4):
		v_blend[i] = r_newrefdef.blend[i]

	c_brush_polys = 0
	c_alias_polys = 0

	# clear out the portion of the screen that the NOWORLDMODEL defines
	if r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:
	
		GL.glEnable( GL.GL_SCISSOR_TEST )
		GL.glClearColor( 0.3, 0.3, 0.3, 1 )
		GL.glScissor( r_newrefdef.x, vid.height - r_newrefdef.height - r_newrefdef.y, r_newrefdef.width, r_newrefdef.height )
		GL.glClear( GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT )
		GL.glClearColor( 1, 0, 0.5, 0.5 )
		GL.glDisable( GL.GL_SCISSOR_TEST )
	

def MYgluPerspective( fovy, aspect, zNear, zFar ): # GLdouble, GLdouble, GLdouble, GLdouble

   # GLdouble xmin, xmax, ymin, ymax;

   ymax = zNear * math.tan( fovy * math.pi / 360.0 )
   ymin = -ymax

   xmin = ymin * aspect
   xmax = ymax * aspect

   xmin += -( 2 * gl_state.camera_separation ) / zNear
   xmax += -( 2 * gl_state.camera_separation ) / zNear

   GL.glFrustum( xmin, xmax, ymin, ymax, zNear, zFar )



"""
=============
R_SetupGL
=============
"""
def R_SetupGL ():

	"""
	float	screenaspect;
//	float	yfov;
	int		x, x2, y2, y, w, h;
	"""

	#
	# set up viewport
	#
	x = math.floor(r_newrefdef.x * vid.width // vid.width)
	x2 = math.ceil((r_newrefdef.x + r_newrefdef.width) * vid.width // vid.width)
	y = math.floor(vid.height - r_newrefdef.y * vid.height // vid.height)
	y2 = math.ceil(vid.height - (r_newrefdef.y + r_newrefdef.height) * vid.height // vid.height)

	w = x2 - x
	h = y - y2

	GL.glViewport (x, y2, w, h)

	#
	# set up projection matrix
	#
	screenaspect = float(r_newrefdef.width/r_newrefdef.height)
#	yfov = 2*atan((float)r_newrefdef.height/r_newrefdef.width)*180/M_PI;
	GL.glMatrixMode(GL.GL_PROJECTION)
	GL.glLoadIdentity ()
	MYgluPerspective (r_newrefdef.fov_y, screenaspect,  4,  4096)

	GL.glCullFace(GL.GL_FRONT)

	GL.glMatrixMode(GL.GL_MODELVIEW)
	GL.glLoadIdentity ()

	GL.glRotatef (-90,  1, 0, 0)		# put Z going up
	GL.glRotatef (90,  0, 0, 1)		# put Z going up
	GL.glRotatef (-r_newrefdef.viewangles[2],  1, 0, 0)
	GL.glRotatef (-r_newrefdef.viewangles[0],  0, 1, 0)
	GL.glRotatef (-r_newrefdef.viewangles[1],  0, 0, 1)
	GL.glTranslatef (-r_newrefdef.vieworg[0],  -r_newrefdef.vieworg[1],  -r_newrefdef.vieworg[2]);

#	if ( gl_state.camera_separation != 0 && gl_state.stereo_enabled )
#		qglTranslatef ( gl_state.camera_separation, 0, 0 );

	GL.glGetFloatv (GL.GL_MODELVIEW_MATRIX, r_world_matrix)

	#
	# set drawing parms
	#
	if gl_cull.value:
		GL.glEnable(GL.GL_CULL_FACE)
	else:
		GL.glDisable(GL.GL_CULL_FACE)

	GL.glDisable(GL.GL_BLEND)
	GL.glDisable(GL.GL_ALPHA_TEST)
	GL.glEnable(GL.GL_DEPTH_TEST)


"""
=============
R_Clear
=============
"""
trickframe = 0 #static int, in R_Clear

def R_Clear ():

	global gldepthmin, gldepthmax, trickframe

	if gl_ztrick.value:
	
		#static int trickframe;

		if gl_clear.value:
			GL.glClear (GL.GL_COLOR_BUFFER_BIT)

		trickframe+=1
		if (trickframe & 1):
		
			gldepthmin = 0
			gldepthmax = 0.49999
			GL.glDepthFunc (GL.GL_LEQUAL)
		
		else:
		
			gldepthmin = 1
			gldepthmax = 0.5
			GL.glDepthFunc (GL.GL_GEQUAL)
		
	else:
	
		if gl_clear.value:
			GL.glClear (GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
		else:
			GL.glClear (GL.GL_DEPTH_BUFFER_BIT)
		gldepthmin = 0
		gldepthmax = 1
		GL.glDepthFunc (GL.GL_LEQUAL)
	
	GL.glDepthRange (gldepthmin, gldepthmax)


def R_Flash( ):

	R_PolyBlend ()

"""
================
R_RenderView

r_newrefdef must be set before the first call
================
"""
# Q2PORT DEBUG: frustum and world culling trace, enabled with env Q2DBG=1.
# Output matches R_DebugFrustum added to the C gl1 renderer for diffing.
dbg_frame = 0 #int

def R_DebugFrustum ():

	global dbg_frame

	if not os.environ.get("Q2DBG") or dbg_frame >= 300 \
		or (r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL):
		return

	dbg_frame += 1
	out = sys.stderr
	out.write("DBG frame {} time {:.3f} fov {:.3f} {:.3f} size {} {} cluster {} {}\n".format(
		dbg_frame, r_newrefdef.time, r_newrefdef.fov_x, r_newrefdef.fov_y,
		r_newrefdef.width, r_newrefdef.height, r_viewcluster, r_viewcluster2))
	out.write("DBG org {:.3f} {:.3f} {:.3f} ang {:.3f} {:.3f} {:.3f}\n".format(
		r_origin[0], r_origin[1], r_origin[2], r_newrefdef.viewangles[0],
		r_newrefdef.viewangles[1], r_newrefdef.viewangles[2]))
	out.write("DBG vpn {:.5f} {:.5f} {:.5f} vright {:.5f} {:.5f} {:.5f} vup {:.5f} {:.5f} {:.5f}\n".format(
		vpn[0], vpn[1], vpn[2], vright[0], vright[1], vright[2],
		vup[0], vup[1], vup[2]))

	for i in range(4):
		out.write("DBG frustum {} normal {:.5f} {:.5f} {:.5f} dist {:.3f} type {} signbits {}\n".format(
			i, frustum[i].normal[0], frustum[i].normal[1], frustum[i].normal[2],
			frustum[i].dist, frustum[i].type, frustum[i].signbits))

	out.write("DBG world visited {} culled {} leafs {} wpoly {}\n".format(
		gl1_surf.dbg_nodes_visited, gl1_surf.dbg_nodes_culled, gl1_surf.dbg_leafs_drawn, c_brush_polys))


def R_RenderView (fd): #refdef_t *

	global r_norefresh, r_newrefdef, c_brush_polys, c_alias_polys

	if r_norefresh.value:
		return
	
	r_newrefdef = fd.copy() # r_newrefdef = *fd
	
	if r_worldmodel is None and not ( r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL ):
		ri.Sys_Error (shared.ERR_DROP, "R_RenderView: NULL worldmodel")

	if r_speeds.value:
	
		c_brush_polys = 0
		c_alias_polys = 0
	
	gl1_light.R_PushDlights ()

	if gl_finish.value:
		GL.glFinish ()

	R_SetupFrame ()

	R_SetFrustum ()

	R_SetupGL ()

	gl1_surf.R_MarkLeaves ()	# done here so we know if we're in water

	gl1_surf.dbg_nodes_visited, gl1_surf.dbg_nodes_culled, gl1_surf.dbg_leafs_drawn = 0, 0, 0 # Q2PORT DEBUG
	c_brush_polys = 0 # Q2PORT DEBUG

	gl1_surf.R_DrawWorld ()

	R_DebugFrustum () # Q2PORT DEBUG

	R_DrawEntitiesOnList ()

	gl1_light.R_RenderDlights ()

	R_DrawParticles ()

	gl1_surf.R_DrawAlphaSurfaces ()

	R_Flash()

	if r_speeds.value:
	
		ri.Con_Printf (shared.PRINT_ALL, "{:4d} wpoly {:4d} epoly {} tex {} lmaps\n".format(
			c_brush_polys, 
			c_alias_polys, 
			gl1_surf.c_visible_textures, 
			gl1_surf.c_visible_lightmaps))
	




def	R_SetGL2D ():

	# set 2D virtual screen size
	GL.glViewport (0,0, vid.width, vid.height)
	GL.glMatrixMode(GL.GL_PROJECTION)
	GL.glLoadIdentity ()
	GL.glOrtho  (0, vid.width, vid.height, 0, -99999, 99999)
	GL.glMatrixMode(GL.GL_MODELVIEW)
	GL.glLoadIdentity ()
	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glDisable (GL.GL_CULL_FACE)
	GL.glDisable (GL.GL_BLEND)
	GL.glEnable (GL.GL_ALPHA_TEST)
	GL.glColor4f (1,1,1,1)


def GL_DrawColoredStereoLinePair( r, g, b, y ): #float, float, float, float

	GL.glColor3f( r, g, b )
	GL.glVertex2f( 0, y )
	GL.glVertex2f( vid.width, y )
	GL.glColor3f( 0, 0, 0 )
	GL.glVertex2f( 0, y + 1 )
	GL.glVertex2f( vid.width, y + 1 )


def GL_DrawStereoPattern(): # static void

	#int i;

	if not ( gl_config.renderer & GL_RENDERER_INTERGRAPH ):
		return

	if not gl_state.stereo_enabled:
		return

	R_SetGL2D()

	GL.glDrawBuffer( GL.GL_BACK_LEFT )

	for i in range(20):
	
		GL.glBegin( GL.GL_LINES )
		GL_DrawColoredStereoLinePair( 1, 0, 0, 0 )
		GL_DrawColoredStereoLinePair( 1, 0, 0, 2 )
		GL_DrawColoredStereoLinePair( 1, 0, 0, 4 )
		GL_DrawColoredStereoLinePair( 1, 0, 0, 6 )
		GL_DrawColoredStereoLinePair( 0, 1, 0, 8 )
		GL_DrawColoredStereoLinePair( 1, 1, 0, 10)
		GL_DrawColoredStereoLinePair( 1, 1, 0, 12)
		GL_DrawColoredStereoLinePair( 0, 1, 0, 14)
		GL.glEnd()
		
		glimp_sdl2.GLimp_EndFrame()
	

"""
/*
====================
R_SetLightLevel

====================
"""
def R_SetLightLevel ():

	#vec3_t		shadelight;
	shadelight = np.zeros((3,), dtype=np.float32)

	if r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:
		return

	# save off light value for server to look at (BIG HACK!)

	gl1_light.R_LightPoint (r_newrefdef.vieworg, shadelight)

	# pick the greatest component, which should be the same
	# as the mono value returned by software
	if shadelight[0] > shadelight[1]:

		if shadelight[0] > shadelight[2]:
			r_lightlevel.value = 150*shadelight[0]
		else:
			r_lightlevel.value = 150*shadelight[2]

	else:

		if shadelight[1] > shadelight[2]:
			r_lightlevel.value = 150*shadelight[1]
		else:
			r_lightlevel.value = 150*shadelight[2]



"""
@@@@@@@@@@@@@@@@@@@@@
R_RenderFrame

@@@@@@@@@@@@@@@@@@@@@
"""
def R_RenderFrame (fd): #refdef_t *

	R_RenderView( fd )
	R_SetLightLevel ()
	R_SetGL2D ()




def R_Register():

	global r_norefresh, r_drawentities, r_drawworld, r_speeds, r_fullbright, r_novis, r_nocull, r_lerpmodels, r_lefthand, r_lightlevel, \
	gl_nosubimage, gl_allow_software, gl_vertex_arrays, \
	gl_particle_min_size, gl_particle_max_size, gl_particle_size, gl_particle_att_a, gl_particle_att_b, gl_particle_att_c, \
	gl_ext_swapinterval, gl_ext_palettedtexture, gl_ext_multitexture, gl_ext_pointparameters, gl_ext_compiled_vertex_array, \
	gl_log, gl_bitdepth, gl_drawbuffer, gl_driver, gl_lightmap, gl_shadows, gl_mode, gl_dynamic, gl_monolightmap, gl_modulate, gl_nobind, \
	gl_round_down, gl_picmip, gl_skymip, gl_showtris, gl_ztrick, gl_finish, gl_clear, gl_cull, gl_polyblend, gl_flashblend, gl_playermip, \
	gl_saturatelighting, gl_swapinterval, gl_texturemode, gl_texturealphamode, gl_texturesolidmode, gl_lockpvs, \
	gl_3dlabs_broken, vid_fullscreen, vid_gamma, vid_ref

	r_lefthand = ri.Cvar_Get( "hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE )
	r_norefresh = ri.Cvar_Get ("r_norefresh", "0", 0)
	r_fullbright = ri.Cvar_Get ("r_fullbright", "0", 0)
	r_drawentities = ri.Cvar_Get ("r_drawentities", "1", 0)
	r_drawworld = ri.Cvar_Get ("r_drawworld", "1", 0)
	r_novis = ri.Cvar_Get ("r_novis", "0", 0)
	r_nocull = ri.Cvar_Get ("r_nocull", "0", 0)
	r_lerpmodels = ri.Cvar_Get ("r_lerpmodels", "1", 0)
	r_speeds = ri.Cvar_Get ("r_speeds", "0", 0)

	r_lightlevel = ri.Cvar_Get ("r_lightlevel", "0", 0)

	gl_nosubimage = ri.Cvar_Get( "gl_nosubimage", "0", 0 )
	gl_allow_software = ri.Cvar_Get( "gl_allow_software", "0", 0 )

	gl_particle_min_size = ri.Cvar_Get( "gl_particle_min_size", "2", shared.CVAR_ARCHIVE )
	gl_particle_max_size = ri.Cvar_Get( "gl_particle_max_size", "40", shared.CVAR_ARCHIVE )
	gl_particle_size = ri.Cvar_Get( "gl_particle_size", "40", shared.CVAR_ARCHIVE )
	gl_particle_att_a = ri.Cvar_Get( "gl_particle_att_a", "0.01", shared.CVAR_ARCHIVE )
	gl_particle_att_b = ri.Cvar_Get( "gl_particle_att_b", "0.0", shared.CVAR_ARCHIVE )
	gl_particle_att_c = ri.Cvar_Get( "gl_particle_att_c", "0.01", shared.CVAR_ARCHIVE )

	gl_modulate = ri.Cvar_Get ("gl_modulate", "1", shared.CVAR_ARCHIVE )
	gl_log = ri.Cvar_Get( "gl_log", "0", 0 )
	gl_bitdepth = ri.Cvar_Get( "gl_bitdepth", "0", 0 )
	gl_mode = ri.Cvar_Get( "r_mode", "4", shared.CVAR_ARCHIVE ) # Q2PORT: Yamagi's name (and mode table) for gl_mode, until group 15
	gl_lightmap = ri.Cvar_Get ("gl_lightmap", "0", 0)
	gl_shadows = ri.Cvar_Get ("gl_shadows", "0", shared.CVAR_ARCHIVE )
	gl_dynamic = ri.Cvar_Get ("gl_dynamic", "1", 0)
	gl_nobind = ri.Cvar_Get ("gl_nobind", "0", 0)
	gl_round_down = ri.Cvar_Get ("gl_round_down", "1", 0)
	gl_picmip = ri.Cvar_Get ("gl_picmip", "0", 0)
	gl_skymip = ri.Cvar_Get ("gl_skymip", "0", 0)
	gl_showtris = ri.Cvar_Get ("gl_showtris", "0", 0)
	gl_ztrick = ri.Cvar_Get ("gl_ztrick", "0", 0)
	gl_finish = ri.Cvar_Get ("gl_finish", "0", shared.CVAR_ARCHIVE)
	gl_clear = ri.Cvar_Get ("gl_clear", "0", 0)
	gl_cull = ri.Cvar_Get ("gl_cull", "1", 0)
	gl_polyblend = ri.Cvar_Get ("gl_polyblend", "1", 0)
	gl_flashblend = ri.Cvar_Get ("gl_flashblend", "0", 0)
	gl_playermip = ri.Cvar_Get ("gl_playermip", "0", 0)
	gl_monolightmap = ri.Cvar_Get( "gl_monolightmap", "0", 0 )
	gl_driver = ri.Cvar_Get( "gl_driver", "opengl32", shared.CVAR_ARCHIVE )
	gl_texturemode = ri.Cvar_Get( "gl_texturemode", "GL_LINEAR_MIPMAP_NEAREST", shared.CVAR_ARCHIVE )
	gl_texturealphamode = ri.Cvar_Get( "gl_texturealphamode", "default", shared.CVAR_ARCHIVE )
	gl_texturesolidmode = ri.Cvar_Get( "gl_texturesolidmode", "default", shared.CVAR_ARCHIVE )
	gl_lockpvs = ri.Cvar_Get( "gl_lockpvs", "0", 0 )

	gl_vertex_arrays = ri.Cvar_Get( "gl_vertex_arrays", "0", shared.CVAR_ARCHIVE )

	gl_ext_swapinterval = ri.Cvar_Get( "gl_ext_swapinterval", "1", shared.CVAR_ARCHIVE )
	gl_ext_palettedtexture = ri.Cvar_Get( "gl_ext_palettedtexture", "1", shared.CVAR_ARCHIVE )
	gl_ext_multitexture = ri.Cvar_Get( "gl_ext_multitexture", "1", shared.CVAR_ARCHIVE )
	gl_ext_pointparameters = ri.Cvar_Get( "gl_ext_pointparameters", "1", shared.CVAR_ARCHIVE )
	gl_ext_compiled_vertex_array = ri.Cvar_Get( "gl_ext_compiled_vertex_array", "1", shared.CVAR_ARCHIVE )

	gl_drawbuffer = ri.Cvar_Get( "gl_drawbuffer", "GL_BACK", 0 )
	gl_swapinterval = ri.Cvar_Get( "gl_swapinterval", "1", shared.CVAR_ARCHIVE )

	gl_saturatelighting = ri.Cvar_Get( "gl_saturatelighting", "0", 0 )

	gl_3dlabs_broken = ri.Cvar_Get( "gl_3dlabs_broken", "1", shared.CVAR_ARCHIVE )

	vid_fullscreen = ri.Cvar_Get( "vid_fullscreen", "0", shared.CVAR_ARCHIVE )
	vid_gamma = ri.Cvar_Get( "vid_gamma", "1.0", shared.CVAR_ARCHIVE )
	vid_ref = ri.Cvar_Get( "vid_ref", "soft", shared.CVAR_ARCHIVE )

	ri.Cmd_AddCommand( "imagelist", gl1_image.GL_ImageList_f )
	ri.Cmd_AddCommand( "screenshot", gl1_misc.GL_ScreenShot_f )
	ri.Cmd_AddCommand( "modellist", gl1_model.Mod_Modellist_f )
	ri.Cmd_AddCommand( "gl_strings", gl1_misc.GL_Strings_f )


"""
==================
R_SetMode
==================
"""
def R_SetMode (): # (returns qboolean)

	global vid, gl_mode, vid_fullscreen, gl_config, gl_state

	#rserr_t err;
	#qboolean fullscreen;

	if vid_fullscreen.modified and not gl_config.allow_cds:
	
		ri.Con_Printf( shared.PRINT_ALL, "R_SetMode() - CDS not allowed with this driver\n" )
		ri.Cvar_SetValue( "vid_fullscreen", not vid_fullscreen.value )
		vid_fullscreen.modified = False
	
	fullscreen = vid_fullscreen.value

	vid_fullscreen.modified = False
	gl_mode.modified = False

	err, vid.width, vid.height = glimp_sdl2.GLimp_SetMode( vid.width, vid.height, gl_mode.value, fullscreen )
	if err == rserr_t.rserr_ok:
	
		gl_state.prev_mode = gl_mode.value
	
	else:
		if err == rserr_t.rserr_invalid_fullscreen:
		
			ri.Cvar_SetValue( "vid_fullscreen", 0)
			vid_fullscreen.modified = False
			ri.Con_Printf( shared.PRINT_ALL, "ref_gl::R_SetMode() - fullscreen unavailable in this mode\n" )
			err, vid.width, vid.height = glimp_sdl2.GLimp_SetMode( vid.width, vid.height, gl_mode.value, False )
			if err == rserr_t.rserr_ok:
				return True
		
		elif err == rserr_t.rserr_invalid_mode:
		
			ri.Cvar_SetValue( "r_mode", gl_state.prev_mode ) # Q2PORT: gl_mode is r_mode
			gl_mode.modified = False
			ri.Con_Printf( shared.PRINT_ALL, "ref_gl::R_SetMode() - invalid mode\n" )
		
		# try setting it back to something safe
		err, vid.width, vid.height = glimp_sdl2.GLimp_SetMode( vid.width, vid.height, gl_state.prev_mode, False )
		if err != rserr_t.rserr_ok:
		
			ri.Con_Printf( shared.PRINT_ALL, "ref_gl::R_SetMode() - could not revert to safe mode\n" )
			return False
		

	return True


"""
===============
R_Init
===============
"""
def R_Init( hinstance, hWnd ): #void *, void *

	global gl_state, gl_ext_pointparameters, gl_ext_palettedtexture, gl_ext_multitexture

	"""
	char renderer_buffer[1000];
	char vendor_buffer[1000];
	int		err;
	int		j;
	extern float r_turbsin[256];

	for ( j = 0; j < 256; j++ )
	{
		r_turbsin[j] *= 0.5;
	}
	"""
	ri.Con_Printf (shared.PRINT_ALL, "ref_gl version: {}\n".format(REF_VERSION))
	
	gl1_image.Draw_GetPalette ()
	R_Register()
	"""
	# initialize our QGL dynamic bindings
	if ( !QGL_Init( gl_driver->string ) )
	{
		QGL_Shutdown();
		ri.Con_Printf (q_shared.PRINT_ALL, "ref_gl::R_Init() - could not load \"%s\"\n", gl_driver->string );
		return -1;
	}
	"""
	# initialize OS-specific parts of OpenGL
	if not glimp_sdl2.GLimp_Init( hinstance, hWnd ) :
	
		qgl_linux.QGL_Shutdown()
		return -1
	
	# set our "safe" modes
	gl_state.prev_mode = 3
	
	# create the window and set up the context
	if not R_SetMode ():
	
		qgl_linux.QGL_Shutdown()
		ri.Con_Printf (shared.PRINT_ALL, "ref_gl::R_Init() - could not R_SetMode()\n" )
		return -1
	
	ri.Vid_MenuInit()

	#
	# get our various GL strings
	#
	gl_config.vendor_string = glGetString (GL.GL_VENDOR)
	ri.Con_Printf (shared.PRINT_ALL, "GL_VENDOR: {}\n".format(gl_config.vendor_string) )
	gl_config.renderer_string = glGetString (GL.GL_RENDERER)
	ri.Con_Printf (shared.PRINT_ALL, "GL_RENDERER: {}\n".format(gl_config.renderer_string) )
	gl_config.version_string = glGetString (GL.GL_VERSION)
	ri.Con_Printf (shared.PRINT_ALL, "GL_VERSION: {}\n".format(gl_config.version_string) )
	gl_config.extensions = set(glGetString (GL.GL_EXTENSIONS).decode('utf-8').split(" "))
	ri.Con_Printf (shared.PRINT_ALL, "GL_EXTENSIONS: {}\n".format(gl_config.extensions) )

	renderer_buffer = gl_config.renderer_string.decode("ascii", "ignore").lower() # strcpy and strlwr
	vendor_buffer = gl_config.vendor_string.decode("ascii", "ignore").lower()

	if "voodoo" in renderer_buffer:
	
		if "rush" not in renderer_buffer:
			gl_config.renderer = GL_RENDERER_VOODOO
		else:
			gl_config.renderer = GL_RENDERER_VOODOO_RUSH
	
	elif "sgi" in vendor_buffer:
		gl_config.renderer = GL_RENDERER_SGI
	elif "permedia" in renderer_buffer:
		gl_config.renderer = GL_RENDERER_PERMEDIA2
	elif "glint" in renderer_buffer:
		gl_config.renderer = GL_RENDERER_GLINT_MX
	elif "glzicd" in renderer_buffer:
		gl_config.renderer = GL_RENDERER_REALIZM
	elif "gdi" in renderer_buffer:
		gl_config.renderer = GL_RENDERER_MCD
	elif "pcx2" in renderer_buffer:
		gl_config.renderer = GL_RENDERER_PCX2
	elif "verite" in renderer_buffer:
		gl_config.renderer = GL_RENDERER_RENDITION
	else:
		gl_config.renderer = GL_RENDERER_OTHER

	if gl_monolightmap.string[1:2].upper() != 'F':
	
		if gl_config.renderer == GL_RENDERER_PERMEDIA2:
		
			ri.Cvar_Set( "gl_monolightmap", "A" )
			ri.Con_Printf( shared.PRINT_ALL, "...using gl_monolightmap 'a'\n" )
		
		elif gl_config.renderer & GL_RENDERER_POWERVR:
		
			ri.Cvar_Set( "gl_monolightmap", "0" )
		
		else:
		
			ri.Cvar_Set( "gl_monolightmap", "0" )
		
	# power vr can't have anything stay in the framebuffer, so
	# the screen needs to redraw the tiled background every frame
	if gl_config.renderer & GL_RENDERER_POWERVR:
	
		ri.Cvar_Set( "scr_drawall", "1" )
	
	else:
	
		ri.Cvar_Set( "scr_drawall", "0" )
	
	"""

#ifdef __linux__
	ri.Cvar_SetValue( "gl_finish", 1 );
#endif

	// MCD has buffering issues
	if ( gl_config.renderer == GL_RENDERER_MCD )
	{
		ri.Cvar_SetValue( "gl_finish", 1 );
	}

	if ( gl_config.renderer & GL_RENDERER_3DLABS )
	{
		if ( gl_3dlabs_broken->value )
			gl_config.allow_cds = false;
		else
			gl_config.allow_cds = true;
	}
	else
	{
		gl_config.allow_cds = true;
	}

	"""
	if gl_config.allow_cds:
		ri.Con_Printf( shared.PRINT_ALL, "...allowing CDS\n" )
	else:
		ri.Con_Printf( shared.PRINT_ALL, "...disabling CDS\n" )
	
	#
	# grab extensions
	#
	if "GL_EXT_compiled_vertex_array" in gl_config.extensions or \
		 "GL_SGI_compiled_vertex_array" in gl_config.extensions:
	
		ri.Con_Printf( shared.PRINT_ALL, "...enabling GL_EXT_compiled_vertex_array\n" )
		qgl_linux.qglLockArraysEXT = True #( void * ) qwglGetProcAddress( "glLockArraysEXT" )
		qgl_linux.qglUnlockArraysEXT = True #( void * ) qwglGetProcAddress( "glUnlockArraysEXT" )
	
	else:
	
		ri.Con_Printf( shared.PRINT_ALL, "...GL_EXT_compiled_vertex_array not found\n" )
	
	"""
#ifdef _WIN32
	if ( strstr( gl_config.extensions_string, "WGL_EXT_swap_control" ) )
	{
		qwglSwapIntervalEXT = ( BOOL (WINAPI *)(int)) qwglGetProcAddress( "wglSwapIntervalEXT" );
		ri.Con_Printf( q_shared.PRINT_ALL, "...enabling WGL_EXT_swap_control\n" );
	}
	else
	{
		ri.Con_Printf( q_shared.PRINT_ALL, "...WGL_EXT_swap_control not found\n" );
	}
#endif
	"""
	if "GL_EXT_point_parameters" in gl_config.extensions:
	
		if gl_ext_pointparameters.value:
		
			qgl_linux.qglPointParameterfEXT = True #( void (APIENTRY *)( GLenum, GLfloat ) ) qwglGetProcAddress( "glPointParameterfEXT" )
			qgl_linux.qglPointParameterfvEXT = True #( void (APIENTRY *)( GLenum, const GLfloat * ) ) qwglGetProcAddress( "glPointParameterfvEXT" )
			ri.Con_Printf( shared.PRINT_ALL, "...using GL_EXT_point_parameters\n" )
		
		else:
		
			ri.Con_Printf( shared.PRINT_ALL, "...ignoring GL_EXT_point_parameters\n" )
		
	
	else:
	
		ri.Con_Printf( shared.PRINT_ALL, "...GL_EXT_point_parameters not found\n" );
	
	"""
#ifdef __linux__
	if ( strstr( gl_config.extensions_string, "3DFX_set_global_palette" ))
	{
		if ( gl_ext_palettedtexture->value )
		{
			ri.Con_Printf( q_shared.PRINT_ALL, "...using 3DFX_set_global_palette\n" );
			qgl3DfxSetPaletteEXT = ( void ( APIENTRY * ) (GLuint *) )qwglGetProcAddress( "gl3DfxSetPaletteEXT" );
			qgl_linux.qglColorTableEXT = Fake_glColorTableEXT;
		}
		else
		{
			ri.Con_Printf( q_shared.PRINT_ALL, "...ignoring 3DFX_set_global_palette\n" );
		}
	}
	else
	{
		ri.Con_Printf( q_shared.PRINT_ALL, "...3DFX_set_global_palette not found\n" );
	}
#endif
	"""
	if qgl_linux.qglColorTableEXT is None and \
		"GL_EXT_paletted_texture" in gl_config.extensions and \
		"GL_EXT_shared_texture_palette" in gl_config.extensions:
	
		if gl_ext_palettedtexture.value:
		
			ri.Con_Printf( shared.PRINT_ALL, "...using GL_EXT_shared_texture_palette\n" )
			qgl_linux.qglColorTableEXT = True #( void ( APIENTRY * ) ( int, int, int, int, int, const void * ) ) qwglGetProcAddress( "glColorTableEXT" )
		
		else:
		
			ri.Con_Printf( shared.PRINT_ALL, "...ignoring GL_EXT_shared_texture_palette\n" )
		
	
	else:
	
		ri.Con_Printf( shared.PRINT_ALL, "...GL_EXT_shared_texture_palette not found\n" )
	
	
	if "GL_ARB_multitexture" in gl_config.extensions:
	
		if gl_ext_multitexture.value:
		
			ri.Con_Printf( shared.PRINT_ALL, "...using GL_ARB_multitexture\n" );
			qgl_linux.qglMTexCoord2fSGIS = True #( void * ) qwglGetProcAddress( "glMultiTexCoord2fARB" );
			qgl_linux.qglActiveTextureARB = True #( void * ) qwglGetProcAddress( "glActiveTextureARB" );
			qgl_linux.qglClientActiveTextureARB = True #( void * ) qwglGetProcAddress( "glClientActiveTextureARB" );
			#GL_TEXTURE0 = GL_TEXTURE0_ARB;
			#GL_TEXTURE1 = GL_TEXTURE1_ARB;
		
		else:
		
			ri.Con_Printf( shared.PRINT_ALL, "...ignoring GL_ARB_multitexture\n" );
		
	
	else:
	
		ri.Con_Printf( shared.PRINT_ALL, "...GL_ARB_multitexture not found\n" )
	
	"""
	if ( strstr( gl_config.extensions_string, "GL_SGIS_multitexture" ) )
	{
		if ( qglActiveTextureARB )
		{
			ri.Con_Printf( q_shared.PRINT_ALL, "...GL_SGIS_multitexture deprecated in favor of ARB_multitexture\n" );
		}
		else if ( gl_ext_multitexture->value )
		{
			ri.Con_Printf( q_shared.PRINT_ALL, "...using GL_SGIS_multitexture\n" );
			qglMTexCoord2fSGIS = ( void * ) qwglGetProcAddress( "glMTexCoord2fSGIS" );
			qglSelectTextureSGIS = ( void * ) qwglGetProcAddress( "glSelectTextureSGIS" );
			GL_TEXTURE0 = GL_TEXTURE0_SGIS;
			GL_TEXTURE1 = GL_TEXTURE1_SGIS;
		}
		else
		{
			ri.Con_Printf( q_shared.PRINT_ALL, "...ignoring GL_SGIS_multitexture\n" );
		}
	}
	else
	{
		ri.Con_Printf( q_shared.PRINT_ALL, "...GL_SGIS_multitexture not found\n" );
	}
	"""
	gl1_misc.GL_SetDefaultState()

	#
	# draw our stereo patterns
	#

	# commented out until H3D pays us the money they owe us
	## GL_DrawStereoPattern()

	gl1_image.GL_InitImages ()
	gl1_model.Mod_Init ()
	gl1_misc.R_InitParticleTexture ()
	gl1_draw.Draw_InitLocal ()


	err = GL.glGetError()
	if err != GL.GL_NO_ERROR:
		ri.Con_Printf (shared.PRINT_ALL, "glGetError() = 0x{:x}\n".format(err))

	# q2 extra code to catch opengl errors
	GL.glDebugMessageCallback(GL.GLDEBUGPROC(onGlDebugMessage), None)


def onGlDebugMessage(*args, **kwargs):
    print('glGetError args = {0}, kwargs = {1}'.format(args, kwargs))


"""
===============
R_Shutdown
===============
"""
def R_Shutdown ():

	ri.Cmd_RemoveCommand ("modellist")
	ri.Cmd_RemoveCommand ("screenshot")
	ri.Cmd_RemoveCommand ("imagelist")
	ri.Cmd_RemoveCommand ("gl_strings")

	gl1_model.Mod_FreeAll ()

	gl1_image.GL_ShutdownImages ()
	#
	# shut down OS specific OpenGL stuff like contexts, etc.
	#
	glimp_sdl2.GLimp_Shutdown();
	"""
	/*
	** shutdown our QGL subsystem
	*/
	QGL_Shutdown();
	"""

"""
@@@@@@@@@@@@@@@@@@@@@
R_BeginFrame
@@@@@@@@@@@@@@@@@@@@@
"""
def R_BeginFrame( camera_separation ): #float

	global gl_state, gl_texturemode, gl_texturealphamode, gl_texturesolidmode

	gl_state.camera_separation = camera_separation

	#
	# change modes if necessary
	#
	if gl_mode.modified or vid_fullscreen.modified:
		# FIXME: only restart if CDS is required
		#cvar_t	*ref;

		ref = ri.Cvar_Get ("vid_ref", "gl", 0)
		ref.modified = True
	
	if gl_log.modified:
	
		qgl_linux.GLimp_EnableLogging( gl_log.value )
		gl_log.modified = False
	
	if gl_log.value:
	
		qgl_linux.GLimp_LogNewFrame()
	
	#
	# update 3Dfx gamma -- it is expected that a user will do a vid_restart
	# after tweaking this value
	#
	if vid_gamma.modified:
	
		vid_gamma.modified = False

		if gl_config.renderer & ( GL_RENDERER_VOODOO ):
		
			#char envbuffer[1024];
			#float g;

			g = 2.00 * ( 0.8 - ( vid_gamma.value - 0.5 ) ) + 1.0
			os.environ["SSTV2_GAMMA"] = "{:f}".format(g) # putenv( envbuffer );
			os.environ["SST_GAMMA"] = "{:f}".format(g)
		
	glimp_sdl2.GLimp_BeginFrame( camera_separation )

	#
	# go into 2D mode
	#
	GL.glViewport (0,0, vid.width, vid.height)
	GL.glMatrixMode(GL.GL_PROJECTION)
	GL.glLoadIdentity ()
	GL.glOrtho  (0, vid.width, vid.height, 0, -99999, 99999)
	GL.glMatrixMode(GL.GL_MODELVIEW)
	GL.glLoadIdentity ()
	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glDisable (GL.GL_CULL_FACE)
	GL.glDisable (GL.GL_BLEND)
	GL.glEnable (GL.GL_ALPHA_TEST)
	GL.glColor4f (1,1,1,1)
	#
	# draw buffer stuff
	#
	if gl_drawbuffer.modified:
	
		gl_drawbuffer.modified = False

		if gl_state.camera_separation == 0 or not gl_state.stereo_enabled:
		
			if shared_c.Q_stricmp( gl_drawbuffer.string, "GL_FRONT" ) == 0:
				GL.glDrawBuffer( GL.GL_FRONT )
			else:
				GL.glDrawBuffer( GL.GL_BACK )
		
	#
	# texturemode stuff
	#
	if gl_texturemode.modified:
	
		gl1_image.GL_TextureMode( gl_texturemode.string )
		gl_texturemode.modified = False
	

	if gl_texturealphamode.modified:
	
		gl1_image.GL_TextureAlphaMode( gl_texturealphamode.string )
		gl_texturealphamode.modified = False
	

	if gl_texturesolidmode.modified:
	
		gl1_image.GL_TextureSolidMode( gl_texturesolidmode.string )
		gl_texturesolidmode.modified = False

	
	#
	# swapinterval stuff
	#
	gl1_misc.GL_UpdateSwapInterval()
	
	#
	# clear screen if desired
	#
	R_Clear ()


"""
=============
R_SetPalette
=============
*/
"""
r_rawpalette = [0]*256 #unsigned[256];

def R_SetPalette (palette): #const unsigned char *
	
	#int		i;
	global r_rawpalette

	#byte *rp = ( byte * ) r_rawpalette;

	if palette is not None:
	
		for i in range(256):
		
			c = [0, 0, 0, 0]
			c[0] = palette[i*3+0]
			c[1] = palette[i*3+1]
			c[2] = palette[i*3+2]
			c[3] = 0xff
			r_rawpalette[i] = struct.unpack("<L", struct.pack("<BBBB", *c))[0]
		
	else:
	
		for i in range(256):
		
			c = gl1_image.d_8to24table[i]
			r_rawpalette[i] = struct.unpack("<L", struct.pack("<BBBB", c[0], c[1], c[2], 0xff))[0]
	
	gl1_image.GL_SetTexturePalette( r_rawpalette )

	GL.glClearColor (0,0,0,0)
	GL.glClear (GL.GL_COLOR_BUFFER_BIT)
	GL.glClearColor (1,0, 0.5 , 0.5)


"""
** R_DrawBeam
"""
NUM_BEAM_SEGS = 6

def R_DrawBeam( e ): #entity_t *

	"""
	int	i;
	float r, g, b;

	vec3_t perpvec;
	vec3_t direction, normalized_direction;
	vec3_t	start_points[NUM_BEAM_SEGS], end_points[NUM_BEAM_SEGS];
	vec3_t oldorigin, origin;
	"""
	perpvec = np.zeros((3,), dtype=np.float32)
	start_points = np.zeros((NUM_BEAM_SEGS, 3), dtype=np.float32)
	end_points = np.zeros((NUM_BEAM_SEGS, 3), dtype=np.float32)

	oldorigin = e.oldorigin.copy()
	origin = e.origin.copy()

	direction = oldorigin - origin
	normalized_direction = direction.copy()

	if shared_c.VectorNormalize( normalized_direction ) == 0:
		return

	shared_c.PerpendicularVector( perpvec, normalized_direction )
	shared_c.VectorScale( perpvec, e.frame / 2, perpvec )

	for i in range(6):
	
		shared_c.RotatePointAroundVector( start_points[i], normalized_direction, perpvec, (360.0/NUM_BEAM_SEGS)*i )
		shared.VectorAdd( start_points[i], origin, start_points[i] )
		shared.VectorAdd( start_points[i], direction, end_points[i] )
	
	GL.glDisable( GL.GL_TEXTURE_2D )
	GL.glEnable( GL.GL_BLEND )
	GL.glDepthMask( GL.GL_FALSE )

	col = gl1_image.d_8to24table[e.skinnum & 0xFF] # 4 bytes, r g b a
	r = col[0]
	g = col[1]
	b = col[2]

	r *= 1/255.0
	g *= 1/255.0
	b *= 1/255.0

	GL.glColor4f( r, g, b, e.alpha )

	GL.glBegin( GL.GL_TRIANGLE_STRIP )
	for i in range(NUM_BEAM_SEGS):
	
		GL.glVertex3fv( start_points[i] )
		GL.glVertex3fv( end_points[i] )
		GL.glVertex3fv( start_points[(i+1)%NUM_BEAM_SEGS] )
		GL.glVertex3fv( end_points[(i+1)%NUM_BEAM_SEGS] )
	
	GL.glEnd()

	GL.glEnable( GL.GL_TEXTURE_2D )
	GL.glDisable( GL.GL_BLEND )
	GL.glDepthMask( GL.GL_TRUE )
"""

//===================================================================

void	R_BeginRegistration (char *map);
struct model_s	*R_RegisterModel (char *name);
struct image_s	*R_RegisterSkin (char *name);
void R_SetSky (char *name, float rotate, vec3_t axis);
void	R_EndRegistration (void);

struct image_s	*Draw_FindPic (char *name);

void	Draw_Pic (int x, int y, char *name);
void	Draw_Char (int x, int y, int c);
void	Draw_TileClear (int x, int y, int w, int h, char *name);
void	Draw_Fill (int x, int y, int w, int h, int c);
void	Draw_FadeScreen (void);

/*
@@@@@@@@@@@@@@@@@@@@@
GetRefAPI

@@@@@@@@@@@@@@@@@@@@@
"""
def GetRefAPI ( rimp ): #refimport_t (returns refexport_t)

	global ri

	re = ref.refexport_t()

	ri = rimp

	re.api_version = ref.API_VERSION

	re.BeginRegistration = gl1_model.R_BeginRegistration
	re.RegisterModel = gl1_model.R_RegisterModel
	re.RegisterSkin = gl1_image.R_RegisterSkin
	re.RegisterPic = gl1_draw.Draw_FindPic
	re.SetSky = gl1_warp.R_SetSky
	re.EndRegistration = gl1_model.R_EndRegistration

	re.RenderFrame = R_RenderFrame
	
	re.DrawGetPicSize = gl1_draw.Draw_GetPicSize
	re.DrawPic = gl1_draw.Draw_Pic
	re.DrawStretchPic = gl1_draw.Draw_StretchPic
	re.DrawChar = gl1_draw.Draw_Char
	re.DrawCharScaled = gl1_draw.Draw_CharScaled # Q2PORT: Yamagi's refexport, until group 15
	re.DrawPicScaled = gl1_draw.Draw_PicScaled
	re.DrawPicScaledCol = gl1_draw.Draw_PicScaledCol
	re.DrawFindPic = gl1_draw.Draw_FindPic
	re.DrawTileClear = gl1_draw.Draw_TileClear
	re.DrawFill = gl1_draw.Draw_Fill
	re.DrawFadeScreen= gl1_draw.Draw_FadeScreen

	re.DrawStretchRaw = gl1_draw.Draw_StretchRaw

	re.Init = R_Init
	re.Shutdown = R_Shutdown

	re.CinematicSetPalette = R_SetPalette

	re.BeginFrame = R_BeginFrame
	re.EndFrame = glimp_sdl2.GLimp_EndFrame

	re.AppActivate = glimp_sdl2.GLimp_AppActivate
	
	shared_c.Swap_Init ()

	return re


"""
#ifndef REF_HARD_LINKED
// this is only here so the functions in q_shared.c and q_shwin.c can link
void Sys_Error (char *error, ...)
{
	va_list		argptr;
	char		text[1024];

	va_start (argptr, error);
	vsprintf (text, error, argptr);
	va_end (argptr);

	ri.Sys_Error (ERR_FATAL, "%s", text);
}

void Com_Printf (char *fmt, ...)
{
	va_list		argptr;
	char		text[1024];

	va_start (argptr, fmt);
	vsprintf (text, fmt, argptr);
	va_end (argptr);

	ri.Con_Printf (q_shared.PRINT_ALL, "%s", text);
}

#endif
"""
