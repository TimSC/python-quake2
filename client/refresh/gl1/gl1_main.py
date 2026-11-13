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
 * Refresher setup and main part of the frame generation
 *
 * =======================================================================
"""
from __future__ import annotations

import math
import struct
import numpy as np
import OpenGL.GL as GL
from OpenGL.GL import glGetString
from client import ref
from client.vid.header import ref as ref_h
from client.refresh.gl1 import gl1_draw, gl1_image, gl1_misc, gl1_model, gl1_warp, gl1_surf, gl1_mesh, gl1_light, \
	gl1_scrap, gl1_buffer, gl1_sdl, gl1_lightmap, qgl
from client.refresh.gl1.header import model, qgl as qgl_h
from client.refresh.files import models as files_models, pcx as files_pcx, surf as files_surf
from common import clientserver
from common.header import common as common_h
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c

"""
#include "header/local.h"
"""

# from header/local.h

REF_VERSION = "Yamagi Quake II OpenGL Refresher"

# up / down
PITCH	= 0

# left / right
YAW		= 1

# fall over
ROLL	= 2

#enum stereo_modes
STEREO_MODE_NONE				= 0
STEREO_MODE_OPENGL				= 1
STEREO_MODE_ANAGLYPH			= 2
STEREO_MODE_ROW_INTERLEAVED		= 3
STEREO_MODE_COLUMN_INTERLEAVED	= 4
STEREO_MODE_PIXEL_INTERLEAVED	= 5
STEREO_SPLIT_HORIZONTAL			= 6
STEREO_SPLIT_VERTICAL			= 7

#enum opengl_special_buffer_modes
OPENGL_SPECIAL_BUFFER_MODE_NONE		= 0
OPENGL_SPECIAL_BUFFER_MODE_STEREO	= 1
OPENGL_SPECIAL_BUFFER_MODE_STENCIL	= 2

class viddef_t(object):
	def __init__(self):
		self.width, self.height = 0, 0 #int, coordinates from main game

vid = viddef_t() #viddef_t

class glconfig_t(object):

	def __init__(self):

		self.renderer_string = None #const char *
		self.vendor_string = None #const char *
		self.version_string = None #const char *
		self.extensions_string = None #const char *

		self.num_extensions = 0 #int
		self.major_version = 0 #int
		self.minor_version = 0 #int

		# ----

		self.anisotropic = False #qboolean
		self.npottextures = False #qboolean
		self.palettedtexture = False #qboolean
		self.pointparameters = False #qboolean
		self.multitexture = False #qboolean
		self.tilerendering = False #qboolean, see "Tile-Based Rendering optimizations" in gl1_main.c

		# ----

		self.max_anisotropy = 0.0 #float

class glstate_t(object):

	def __init__(self):

		self.inverse_intensity = 0.0 #float
		self.sw_gamma = 1.0 #float, always 1 if using SDL2 hw gamma
		self.minlight_set = False #qboolean, is gl1_minlight > 0 ?
		self.fullscreen = False #qboolean

		self.prev_mode = 0 #int

		self.d_16to8table = None #byte *

		self.lightmap_textures = 0 #int

		self.currenttextures = [0, 0] #int [MAX_TEXTURE_UNITS]
		self.currenttmu = 0 #int
		self.currenttarget = 0 #GLenum

		self.camera_separation = 0.0 #float
		self.stereo_mode = STEREO_MODE_NONE #enum stereo_modes

		self.stencil = False #qboolean

# gl1_main.c

NUM_BEAM_SEGS = 6

r_worldmodel = None #model_t *

gldepthmin, gldepthmax = 0.0, 0.0 #float

gl_config = glconfig_t() #glconfig_t
gl_state = glstate_t() #glstate_t

r_notexture = None #image_t *, use for bad textures
r_particletexture = None #image_t *, little dot for particles

frustum = [shared.cplane_t() for _ in range(4)] #cplane_t[4]

r_visframecount = 0 #int, bumped when going to a new PVS
r_framecount = 0 #int, used for dlight push checking

c_brush_polys, c_alias_polys = 0, 0 #int

v_blend = np.zeros((4,), dtype=np.float32) #float[4], final blending color

#extern void R_Strings(qboolean show_ext);

# view origin
vup = np.zeros((3,), dtype=np.float32) #vec3_t
vpn = np.zeros((3,), dtype=np.float32) #vec3_t
vright = np.zeros((3,), dtype=np.float32) #vec3_t
r_origin = np.zeros((3,), dtype=np.float32) #vec3_t

r_world_matrix = np.zeros((16,), dtype=np.float32) #float[16]
r_base_world_matrix = np.zeros((16,), dtype=np.float32) #float[16]

# screen size info
r_newrefdef = ref.refdef_t() #refdef_t

r_viewcluster, r_viewcluster2, r_oldviewcluster, r_oldviewcluster2 = -1, -1, -1, -1 #int
r_rawpalette = [0] * 256 #unsigned [256]

r_norefresh = None #cvar_t *
r_drawentities = None #cvar_t *
r_drawworld = None #cvar_t *
r_speeds = None #cvar_t *
r_fullbright = None #cvar_t *
r_novis = None #cvar_t *
r_lerpmodels = None #cvar_t *
gl_lefthand = None #cvar_t *
r_gunfov = None #cvar_t *
r_farsee = None #cvar_t *
r_validation = None #cvar_t *

r_lightlevel = None #cvar_t *
gl1_overbrightbits = None #cvar_t *

gl1_particle_min_size = None #cvar_t *
gl1_particle_max_size = None #cvar_t *
gl1_particle_size = None #cvar_t *
gl1_particle_att_a = None #cvar_t *
gl1_particle_att_b = None #cvar_t *
gl1_particle_att_c = None #cvar_t *
gl1_particle_square = None #cvar_t *

gl1_palettedtexture = None #cvar_t *
gl1_pointparameters = None #cvar_t *

gl_drawbuffer = None #cvar_t *
gl_lightmap = None #cvar_t *
gl_shadows = None #cvar_t *
gl1_stencilshadow = None #cvar_t *
r_mode = None #cvar_t *
r_fixsurfsky = None #cvar_t *
gl1_minlight = None #cvar_t *

r_customwidth = None #cvar_t *
r_customheight = None #cvar_t *

r_retexturing = None #cvar_t *
r_scale8bittextures = None #cvar_t *

gl_nolerp_list = None #cvar_t *
r_lerp_list = None #cvar_t *
r_2D_unfiltered = None #cvar_t *
r_videos_unfiltered = None #cvar_t *

gl1_dynamic = None #cvar_t *
r_modulate = None #cvar_t *
gl_nobind = None #cvar_t *
gl1_round_down = None #cvar_t *
gl1_picmip = None #cvar_t *
gl_showtris = None #cvar_t *
gl_showbbox = None #cvar_t *
gl1_ztrick = None #cvar_t *
gl_zfix = None #cvar_t *
gl_finish = None #cvar_t *
r_clear = None #cvar_t *
r_cull = None #cvar_t *
gl_polyblend = None #cvar_t *
gl1_flashblend = None #cvar_t *
gl1_saturatelighting = None #cvar_t *
r_vsync = None #cvar_t *
gl_texturemode = None #cvar_t *
gl1_texturealphamode = None #cvar_t *
gl1_texturesolidmode = None #cvar_t *
gl_anisotropic = None #cvar_t *
r_lockpvs = None #cvar_t *
gl_msaa_samples = None #cvar_t *

vid_fullscreen = None #cvar_t *
vid_gamma = None #cvar_t *

gl1_stereo = None #cvar_t *
gl1_stereo_separation = None #cvar_t *
gl1_stereo_anaglyph_colors = None #cvar_t *
gl1_stereo_convergence = None #cvar_t *

gl_znear = None #static cvar_t *
gl1_multitexture = None #static cvar_t *
gl1_waterwarp = None #static cvar_t *

#ifndef YQ2_GL1_GLES
gl1_tilerendering = None #static cvar_t *, this is always "forced on" in GLES1
#endif


ri = ref.refimport_t() #refimport_t

#extern void LM_FreeLightmapBuffers(void);
#extern void R_SetDefaultState(void);
#extern void R_ResetGLBuffer(void);


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
def R_DrawSpriteModel(currententity, currentmodel): #entity_t *, const model_t *

	"""
	float alpha = 1.0F;
	vec3_t point[4];
	dsprframe_t *frame;
	float *up, *right;
	dsprite_t *psprite;
	image_t *skin;
	"""
	alpha = 1.0
	point = np.zeros((4, 3), dtype=np.float32)

	gl1_image.R_EnableMultitexture(False)
	# don't even bother culling, because it's just
	# a single polygon without a surface cache
	psprite = currentmodel.extradata

	currententity.frame %= psprite.numframes
	frame = psprite.frames[currententity.frame]

	# normal sprite
	up = vup
	right = vright

	if currententity.flags & shared.RF_TRANSLUCENT:

		alpha = currententity.alpha

	if alpha != 1.0:

		GL.glEnable(GL.GL_BLEND)

	GL.glColor4f(1, 1, 1, alpha)

	skin = currentmodel.skins[currententity.frame]
	if not skin:

		skin = r_notexture # fallback...

	gl1_image.R_Bind(skin.texnum)

	gl1_image.R_TexEnv(GL.GL_MODULATE)

	if alpha == 1.0:

		GL.glEnable(GL.GL_ALPHA_TEST)

	else:

		GL.glDisable(GL.GL_ALPHA_TEST)

	tex = np.array([ #GLfloat[]
		0, 1,
		0, 0,
		1, 0,
		1, 1
	], dtype=np.float32)

	shared_c.VectorMA( currententity.origin, -frame.origin_y, up, point[0] )
	shared_c.VectorMA( point[0], -frame.origin_x, right, point[0] )

	shared_c.VectorMA( currententity.origin, frame.height - frame.origin_y, up, point[1] )
	shared_c.VectorMA( point[1], -frame.origin_x, right, point[1] )

	shared_c.VectorMA( currententity.origin, frame.height - frame.origin_y, up, point[2] )
	shared_c.VectorMA( point[2], frame.width - frame.origin_x, right, point[2] )

	shared_c.VectorMA( currententity.origin, -frame.origin_y, up, point[3] )
	shared_c.VectorMA( point[3], frame.width - frame.origin_x, right, point[3] )

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
	GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glVertexPointer( 3, GL.GL_FLOAT, 0, point )
	GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
	GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )

	GL.glDisable(GL.GL_ALPHA_TEST)
	gl1_image.R_TexEnv(GL.GL_REPLACE)

	if alpha != 1.0:

		GL.glDisable(GL.GL_BLEND)

	GL.glColor4f(1, 1, 1, 1)

def R_DrawNullModel(currententity): #entity_t *

	#vec3_t shadelight;
	shadelight = np.zeros((3,), dtype=np.float32)

	if currententity.flags & shared.RF_FULLBRIGHT:

		shadelight[0] = shadelight[1] = shadelight[2] = 1.0

	else:

		gl1_light.R_LightPoint(currententity, currententity.origin, shadelight)

	gl1_image.R_EnableMultitexture(False)
	GL.glPushMatrix()
	R_RotateForEntity(currententity)

	GL.glDisable(GL.GL_TEXTURE_2D)
	GL.glColor4f( shadelight[0], shadelight[1], shadelight[2], 1 )

	vtxA = np.array([ #GLfloat[]
		0, 0, -16,
		16 * math.cos( 0 * math.pi / 2 ), 16 * math.sin( 0 * math.pi / 2 ), 0,
		16 * math.cos( 1 * math.pi / 2 ), 16 * math.sin( 1 * math.pi / 2 ), 0,
		16 * math.cos( 2 * math.pi / 2 ), 16 * math.sin( 2 * math.pi / 2 ), 0,
		16 * math.cos( 3 * math.pi / 2 ), 16 * math.sin( 3 * math.pi / 2 ), 0,
		16 * math.cos( 4 * math.pi / 2 ), 16 * math.sin( 4 * math.pi / 2 ), 0
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

	GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtxA )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 6 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	vtxB = np.array([ #GLfloat[]
		0, 0, 16,
		16 * math.cos( 4 * math.pi / 2 ), 16 * math.sin( 4 * math.pi / 2 ), 0,
		16 * math.cos( 3 * math.pi / 2 ), 16 * math.sin( 3 * math.pi / 2 ), 0,
		16 * math.cos( 2 * math.pi / 2 ), 16 * math.sin( 2 * math.pi / 2 ), 0,
		16 * math.cos( 1 * math.pi / 2 ), 16 * math.sin( 1 * math.pi / 2 ), 0,
		16 * math.cos( 0 * math.pi / 2 ), 16 * math.sin( 0 * math.pi / 2 ), 0
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

	GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtxB )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 6 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	GL.glColor4f(1, 1, 1, 1)
	GL.glPopMatrix()
	GL.glEnable(GL.GL_TEXTURE_2D)

def R_DrawEntitiesOnList(): #void

	#int i;

	if not r_drawentities.value:

		return

	# draw non-transparent first
	for i in range(r_newrefdef.num_entities):

		currententity = r_newrefdef.entities[i]

		if currententity.flags & shared.RF_TRANSLUCENT:

			continue # solid

		if currententity.flags & shared.RF_BEAM:

			R_DrawBeam(currententity)

		else:

			currentmodel = currententity.model

			if not currentmodel:

				R_DrawNullModel(currententity)
				continue

			if currentmodel.type == model.modtype_t.mod_alias:
				gl1_mesh.R_DrawAliasModel(currententity, currentmodel)
			elif currentmodel.type == model.modtype_t.mod_brush:
				gl1_surf.R_DrawBrushModel(currententity, currentmodel)
			elif currentmodel.type == model.modtype_t.mod_sprite:
				R_DrawSpriteModel(currententity, currentmodel)
			else:
				clientserver.Com_Error(shared.ERR_DROP, "Bad modeltype")

	# draw transparent entities
	# we could sort these if it ever
	# becomes a problem...
	GL.glDepthMask(GL.GL_FALSE)

	for i in range(r_newrefdef.num_entities):

		currententity = r_newrefdef.entities[i]

		if not (currententity.flags & shared.RF_TRANSLUCENT):

			continue # solid

		if currententity.flags & shared.RF_BEAM:

			R_DrawBeam(currententity)

		else:

			currentmodel = currententity.model

			if not currentmodel:

				R_DrawNullModel(currententity)
				continue

			if currentmodel.type == model.modtype_t.mod_alias:
				gl1_mesh.R_DrawAliasModel(currententity, currentmodel)
			elif currentmodel.type == model.modtype_t.mod_brush:
				gl1_surf.R_DrawBrushModel(currententity, currentmodel)
			elif currentmodel.type == model.modtype_t.mod_sprite:
				R_DrawSpriteModel(currententity, currentmodel)
			else:
				clientserver.Com_Error(shared.ERR_DROP, "Bad modeltype")

	GL.glDepthMask(GL.GL_TRUE) # back to writing
	gl1_image.R_EnableMultitexture(False)

def _ParticleArrays(num_particles, particles, colortable): # Q2PORT: shared by both particle draws
	# The C fills vtx and clr per particle; here numpy arrays of the origins and
	# the colours (gammatable[color[0..2]], p->alpha * 255) of all particles
	origins = np.array([particles[i].origin for i in range(num_particles)], dtype=np.float32).reshape(num_particles, 3)
	table = np.array(colortable, dtype=np.uint8) # (r, g, b, a) per entry
	gt = np.frombuffer(bytes(gl1_image.gammatable), dtype=np.uint8)
	clr = np.empty((num_particles, 4), dtype=np.uint8)
	idx = np.array([particles[i].color & 0xFF for i in range(num_particles)], dtype=np.intp)
	clr[:, :3] = gt[table[idx, :3]]
	clr[:, 3] = np.array([particles[i].alpha * 255 for i in range(num_particles)], dtype=np.float32).astype(np.uint8)
	return origins, clr

def R_DrawParticles2(num_particles, particles, colortable): #int, const particle_t[], const unsigned *

	"""
	const particle_t *p;
	int i;
	vec3_t up, right;
	float scale;
	YQ2_ALIGNAS_TYPE(unsigned) byte color[4];

	YQ2_VLA(GLfloat, vtx, 3 * num_particles * 3);
	YQ2_VLA(GLfloat, tex, 2 * num_particles * 3);
	YQ2_VLA(GLubyte, clr, 4 * num_particles * 3);

	unsigned int index_vtx = 0;
	unsigned int index_tex = 0;
	unsigned int index_clr = 0;
	unsigned int j;
	"""
	up = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)

	gl1_image.R_Bind(r_particletexture.texnum)
	GL.glDepthMask(GL.GL_FALSE) # no z buffering
	GL.glEnable(GL.GL_BLEND)
	gl1_image.R_TexEnv(GL.GL_MODULATE)

	shared_c.VectorScale( vup, 1.5, up )
	shared_c.VectorScale( vright, 1.5, right )

	# Q2PORT: the C's per-particle loop, done with numpy over all particles
	origins, pclr = _ParticleArrays(num_particles, particles, colortable)

	# hack a scale up to keep particles from disapearing
	scale = (origins - r_origin) @ vpn
	scale = np.where(scale < 20, 1.0, 1 + scale * 0.004).astype(np.float32)

	# Copy the color for each point
	clr = np.repeat(pclr, 3, axis=0)

	vtx = np.empty((num_particles, 3, 3), dtype=np.float32)
	# point 0
	vtx[:, 0] = origins
	# point 1
	vtx[:, 1] = origins + up[np.newaxis, :] * scale[:, np.newaxis]
	# point 2
	vtx[:, 2] = origins + right[np.newaxis, :] * scale[:, np.newaxis]

	tex = np.tile(np.array([0.0625, 0.0625, 1.0625, 0.0625, 0.0625, 1.0625], dtype=np.float32), num_particles)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
	GL.glEnableClientState( GL.GL_TEXTURE_COORD_ARRAY )
	GL.glEnableClientState( GL.GL_COLOR_ARRAY )

	GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtx )
	GL.glTexCoordPointer( 2, GL.GL_FLOAT, 0, tex )
	GL.glColorPointer( 4, GL.GL_UNSIGNED_BYTE, 0, clr )
	GL.glDrawArrays( GL.GL_TRIANGLES, 0, num_particles * 3 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
	GL.glDisableClientState( GL.GL_TEXTURE_COORD_ARRAY )
	GL.glDisableClientState( GL.GL_COLOR_ARRAY )

	GL.glDisable(GL.GL_BLEND)
	GL.glColor4f(1, 1, 1, 1)
	GL.glDepthMask(GL.GL_TRUE) # back to normal Z buffering
	gl1_image.R_TexEnv(GL.GL_REPLACE)

	#YQ2_VLAFREE(vtx);
	#YQ2_VLAFREE(tex);
	#YQ2_VLAFREE(clr);

def R_DrawParticles(): #void

	stereo_split_tb = ((gl_state.stereo_mode == STEREO_SPLIT_VERTICAL) and gl_state.camera_separation) #qboolean
	stereo_split_lr = ((gl_state.stereo_mode == STEREO_SPLIT_HORIZONTAL) and gl_state.camera_separation) #qboolean

	if r_newrefdef.num_particles <= 0: # avoiding VLA with no size and vertexes built on it

		return

	if gl_config.pointparameters and not (stereo_split_tb or stereo_split_lr):

		"""
		int i;
		YQ2_ALIGNAS_TYPE(unsigned) byte color[4];
		const particle_t *p;

		YQ2_VLA(GLfloat, vtx, 3 * r_newrefdef.num_particles);
		YQ2_VLA(GLubyte, clr, 4 * r_newrefdef.num_particles);

		unsigned int index_vtx = 0;
		unsigned int index_clr = 0;
		"""

		GL.glDepthMask(GL.GL_FALSE)
		GL.glEnable(GL.GL_BLEND)
		GL.glDisable(GL.GL_TEXTURE_2D)

		# assume the particle size looks good with window height 480px and scale according to real resolution
		GL.glPointSize(gl1_particle_size.value * r_newrefdef.height / 480.0)

		# Q2PORT: the C's per-particle loop, done with numpy over all particles
		vtx, clr = _ParticleArrays(r_newrefdef.num_particles, r_newrefdef.particles, gl1_image.d_8to24table)

		GL.glEnableClientState( GL.GL_VERTEX_ARRAY )
		GL.glEnableClientState( GL.GL_COLOR_ARRAY )

		GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtx )
		GL.glColorPointer( 4, GL.GL_UNSIGNED_BYTE, 0, clr )
		GL.glDrawArrays( GL.GL_POINTS, 0, r_newrefdef.num_particles )

		GL.glDisableClientState( GL.GL_VERTEX_ARRAY )
		GL.glDisableClientState( GL.GL_COLOR_ARRAY )

		GL.glDisable(GL.GL_BLEND)
		GL.glColor4f( 1, 1, 1, 1 )
		GL.glDepthMask(GL.GL_TRUE)
		GL.glEnable(GL.GL_TEXTURE_2D)

		#YQ2_VLAFREE(vtx);
		#YQ2_VLAFREE(clr);

	else:

		R_DrawParticles2(r_newrefdef.num_particles,
				r_newrefdef.particles, gl1_image.d_8to24table)

def R_PolyBlend(): #void

	if not gl_polyblend.value:

		return

	if not v_blend[3]:

		return

	GL.glDisable(GL.GL_ALPHA_TEST)
	GL.glEnable(GL.GL_BLEND)
	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glDisable(GL.GL_TEXTURE_2D)

	GL.glLoadIdentity()

	GL.glRotatef(-90, 1, 0, 0) # put Z going up
	GL.glRotatef(90, 0, 0, 1) # put Z going up

	GL.glColor4f( v_blend[0], v_blend[1], v_blend[2], v_blend[3] )

	vtx = np.array([ #GLfloat[]
		10, 100, 100,
		10, -100, 100,
		10, -100, -100,
		10, 100, -100
	], dtype=np.float32)

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

	GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtx )
	GL.glDrawArrays( GL.GL_TRIANGLE_FAN, 0, 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	GL.glDisable(GL.GL_BLEND)
	GL.glEnable(GL.GL_TEXTURE_2D)
	GL.glEnable(GL.GL_ALPHA_TEST)

	GL.glColor4f(1, 1, 1, 1)

def R_ResetClearColor(): #void (static)

	if gl_config.tilerendering and not r_clear.value:

		GL.glClearColor(0, 0, 0, 0.5)

	else:

		GL.glClearColor(1, 0, 0.5, 0.5)

def R_SetupFrame(): #void

	global r_framecount, r_oldviewcluster, r_oldviewcluster2, r_viewcluster, r_viewcluster2, \
		c_brush_polys, c_alias_polys

	#int i;
	#mleaf_t *leaf;

	r_framecount += 1

	# build the transformation matrix for the given view angles
	shared.VectorCopy(r_newrefdef.vieworg, r_origin)

	shared_c.AngleVectors(r_newrefdef.viewangles, vpn, vright, vup)

	# current viewcluster
	if not (r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL):

		if not r_worldmodel:

			clientserver.Com_Error(shared.ERR_DROP, "{}: bad world model".format("R_SetupFrame"))
			return

		r_oldviewcluster = r_viewcluster
		r_oldviewcluster2 = r_viewcluster2
		leaf = files_models.Mod_PointInLeaf(r_origin, r_worldmodel.nodes[0]) # r_worldmodel->nodes
		r_viewcluster = r_viewcluster2 = leaf.cluster

		# check above and below so crossing solid water doesn't draw wrong
		if not leaf.contents:

			# look down a bit
			temp = np.zeros((3,), dtype=np.float32) #vec3_t

			shared.VectorCopy(r_origin, temp)
			temp[2] -= 16
			leaf = files_models.Mod_PointInLeaf(temp, r_worldmodel.nodes[0])

			if (not (leaf.contents & shared.CONTENTS_SOLID) and
				(leaf.cluster != r_viewcluster2)):

				r_viewcluster2 = leaf.cluster

		else:

			# look up a bit
			temp = np.zeros((3,), dtype=np.float32) #vec3_t

			shared.VectorCopy(r_origin, temp)
			temp[2] += 16
			leaf = files_models.Mod_PointInLeaf(temp, r_worldmodel.nodes[0])

			if (not (leaf.contents & shared.CONTENTS_SOLID) and
				(leaf.cluster != r_viewcluster2)):

				r_viewcluster2 = leaf.cluster

	for i in range(3):

		v_blend[i] = r_newrefdef.blend[i] * gl_state.sw_gamma

	v_blend[3] = r_newrefdef.blend[3]

	c_brush_polys = 0
	c_alias_polys = 0

	# clear out the portion of the screen that the NOWORLDMODEL defines
	if r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:

		GL.glEnable(GL.GL_SCISSOR_TEST)
		GL.glClearColor(0.3, 0.3, 0.3, 1)
		GL.glScissor(r_newrefdef.x,
				vid.height - r_newrefdef.height - r_newrefdef.y,
				r_newrefdef.width, r_newrefdef.height)
		GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
		R_ResetClearColor()
		GL.glDisable(GL.GL_SCISSOR_TEST)

def R_SetPerspective(fovy): #GLdouble

	# gluPerspective style parameters
	zNear = shared.Q_max(gl_znear.value, 0.1) #const GLdouble
	zFar = 8192.0 if r_farsee.value else 4096.0 #const GLdouble
	aspectratio = r_newrefdef.width / r_newrefdef.height #const GLdouble

	#GLdouble xmin, xmax, ymin, ymax;

	# traditional gluPerspective calculations - https://youtu.be/YqSNGcF5nvM?t=644
	ymax = zNear * math.tan(fovy * math.pi / 360.0)
	xmax = ymax * aspectratio

	if (r_newrefdef.rdflags & shared.RDF_UNDERWATER) and gl1_waterwarp.value:

		warp = math.sin(r_newrefdef.time * 1.5) * 0.03 * gl1_waterwarp.value #const GLdouble
		ymax *= 1.0 - warp
		xmax *= 1.0 + warp

	ymin = -ymax
	xmin = -xmax

	if gl_state.camera_separation:

		separation = - gl1_stereo_convergence.value * (2 * gl_state.camera_separation) / zNear #const GLdouble
		xmin += separation
		xmax += separation

	GL.glFrustum(xmin, xmax, ymin, ymax, zNear, zFar)

def R_SetupGL(): #void

	#int x, x2, y2, y, w, h;

	# set up viewport
	x = math.floor(r_newrefdef.x * vid.width / vid.width)
	x2 = math.ceil((r_newrefdef.x + r_newrefdef.width) * vid.width / vid.width)
	y = math.floor(vid.height - r_newrefdef.y * vid.height / vid.height)
	y2 = math.ceil(vid.height -
			  (r_newrefdef.y + r_newrefdef.height) * vid.height / vid.height)

	w = x2 - x
	h = y - y2

	drawing_left_eye = gl_state.camera_separation < 0 #qboolean
	stereo_split_tb = ((gl_state.stereo_mode == STEREO_SPLIT_VERTICAL) and gl_state.camera_separation) #qboolean
	stereo_split_lr = ((gl_state.stereo_mode == STEREO_SPLIT_HORIZONTAL) and gl_state.camera_separation) #qboolean

	if stereo_split_lr:
		w = int(w / 2)
		x = int(x / 2) if drawing_left_eye else int((x + vid.width) / 2)

	if stereo_split_tb:
		h = int(h / 2)
		y2 = int((y2 + vid.height) / 2) if drawing_left_eye else int(y2 / 2)

	GL.glViewport(x, y2, w, h)

	# set up projection matrix
	GL.glMatrixMode(GL.GL_PROJECTION)
	GL.glLoadIdentity()

	R_SetPerspective(r_newrefdef.fov_y)

	GL.glCullFace(GL.GL_FRONT)

	GL.glMatrixMode(GL.GL_MODELVIEW)
	GL.glLoadIdentity()

	GL.glRotatef(-90, 1, 0, 0) # put Z going up
	GL.glRotatef(90, 0, 0, 1) # put Z going up
	GL.glRotatef(-r_newrefdef.viewangles[2], 1, 0, 0)
	GL.glRotatef(-r_newrefdef.viewangles[0], 0, 1, 0)
	GL.glRotatef(-r_newrefdef.viewangles[1], 0, 0, 1)
	GL.glTranslatef(-r_newrefdef.vieworg[0], -r_newrefdef.vieworg[1],
			-r_newrefdef.vieworg[2])

	GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX, r_world_matrix)

	# set drawing parms
	if r_cull.value:

		GL.glEnable(GL.GL_CULL_FACE)

	else:

		GL.glDisable(GL.GL_CULL_FACE)

	GL.glDisable(GL.GL_BLEND)
	GL.glDisable(GL.GL_ALPHA_TEST)
	GL.glEnable(GL.GL_DEPTH_TEST)

trickframe = 0 #static int, in R_Clear

def R_Clear(): #void

	global gldepthmin, gldepthmax, trickframe

	# Define which buffers need clearing
	clearFlags = 0 #GLbitfield
	depthFunc = GL.GL_LEQUAL #GLenum

	# This breaks stereo modes, but we'll leave that responsibility to the user
	if r_clear.value:

		clearFlags |= GL.GL_COLOR_BUFFER_BIT

	# No stencil shadows allowed when using certain stereo modes, otherwise "wallhack" happens
	if gl_state.stereo_mode >= STEREO_MODE_ROW_INTERLEAVED and gl_state.stereo_mode <= STEREO_MODE_PIXEL_INTERLEAVED:

		GL.glClearStencil(0)
		clearFlags |= GL.GL_STENCIL_BUFFER_BIT

	elif gl_shadows.value and gl_state.stencil and gl1_stencilshadow.value:

		GL.glClearStencil(1)
		clearFlags |= GL.GL_STENCIL_BUFFER_BIT

	if gl1_ztrick.value:

		#static int trickframe;

		trickframe += 1

		if trickframe & 1:

			gldepthmin = 0
			gldepthmax = 0.49999

		else:

			gldepthmin = 1
			gldepthmax = 0.5
			depthFunc = GL.GL_GEQUAL

	else:

		clearFlags |= GL.GL_DEPTH_BUFFER_BIT

		gldepthmin = 0
		gldepthmax = 1

	if gl_config.tilerendering:

		clearFlags |= GL.GL_STENCIL_BUFFER_BIT

		if gl_state.stereo_mode == STEREO_MODE_NONE:

			clearFlags |= GL.GL_COLOR_BUFFER_BIT

	if clearFlags:

		GL.glClear(clearFlags)

	GL.glDepthFunc(depthFunc)
	GL.glDepthRange(gldepthmin, gldepthmax)

	if gl_zfix.value:

		if gldepthmax > gldepthmin:

			GL.glPolygonOffset(0.05, 1)

		else:

			GL.glPolygonOffset(-0.05, -1)

def R_Flash(): #void

	R_PolyBlend()

def R_SetGL2D(): #void

	#int x, w, y, h;
	# set 2D virtual screen size
	drawing_left_eye = gl_state.camera_separation < 0 #qboolean
	stereo_split_tb = ((gl_state.stereo_mode == STEREO_SPLIT_VERTICAL) and gl_state.camera_separation) #qboolean
	stereo_split_lr = ((gl_state.stereo_mode == STEREO_SPLIT_HORIZONTAL) and gl_state.camera_separation) #qboolean

	x = 0
	w = vid.width
	y = 0
	h = vid.height

	if stereo_split_lr:
		w = int(w / 2)
		x = 0 if drawing_left_eye else w

	if stereo_split_tb:
		h = int(h / 2)
		y = h if drawing_left_eye else 0

	GL.glViewport(x, y, w, h)
	GL.glMatrixMode(GL.GL_PROJECTION)
	GL.glLoadIdentity()
	GL.glOrtho(0, vid.width, vid.height, 0, -99999, 99999)
	GL.glMatrixMode(GL.GL_MODELVIEW)
	GL.glLoadIdentity()
	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glDisable(GL.GL_CULL_FACE)
	GL.glDisable(GL.GL_BLEND)
	GL.glEnable(GL.GL_ALPHA_TEST)
	GL.glColor4f(1, 1, 1, 1)

"""
 * r_newrefdef must be set before the first call
"""
def R_RenderView(fd): #refdef_t * (static)

	global r_newrefdef, c_brush_polys, c_alias_polys

	if (gl_state.stereo_mode != STEREO_MODE_NONE) and gl_state.camera_separation:

		drawing_left_eye = gl_state.camera_separation < 0 #qboolean

		if gl_state.stereo_mode == STEREO_MODE_ANAGLYPH:

			# Work out the colour for each eye.
			anaglyph_colours = [ 0x4, 0x3 ] # Left = red, right = cyan.

			if len(gl1_stereo_anaglyph_colors.string) == 2:

				#int eye, colour, missing_bits;
				# Decode the colour name from its character.
				for eye in range(2):

					colour = 0
					# Q2PORT: the C's switch falls through each case below the
					# one it enters, so the colour is the number of cases run
					letter = gl1_stereo_anaglyph_colors.string[eye].upper()
					if letter in "BGCRMY":

						colour += 6 - "BGCRMY".index(letter)
						anaglyph_colours[eye] = colour

				# Fill in any missing bits.
				missing_bits = ~(anaglyph_colours[0] | anaglyph_colours[1]) & 0x3
				for eye in range(2):

					anaglyph_colours[eye] |= missing_bits

			# Set the current colour.
			GL.glColorMask(
				bool(anaglyph_colours[drawing_left_eye] & 0x4),
				bool(anaglyph_colours[drawing_left_eye] & 0x2),
				bool(anaglyph_colours[drawing_left_eye] & 0x1),
				GL.GL_TRUE
			)

		elif gl_state.stereo_mode in (STEREO_MODE_ROW_INTERLEAVED, STEREO_MODE_COLUMN_INTERLEAVED, STEREO_MODE_PIXEL_INTERLEAVED):

			flip_eyes = True #qboolean
			#int client_x, client_y;

			screen = np.array([ #GLshort[]
				0, 0,
				vid.width, 0,
				vid.width, vid.height,
				0, vid.height
			], dtype=np.int16)

			#GLimp_GetClientAreaOffset(&client_x, &client_y);
			client_x = 0
			client_y = 0

			R_SetGL2D()

			GL.glEnable(GL.GL_STENCIL_TEST)
			GL.glStencilMask(1)
			GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)

			GL.glStencilOp(GL.GL_REPLACE, GL.GL_KEEP, GL.GL_KEEP)
			GL.glStencilFunc(GL.GL_NEVER, 0, 1)

			GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
			GL.glVertexPointer(2, GL.GL_SHORT, 0, screen)
			GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
			GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

			GL.glStencilOp(GL.GL_INVERT, GL.GL_KEEP, GL.GL_KEEP)
			GL.glStencilFunc(GL.GL_NEVER, 1, 1)

			gl_buf = gl1_buffer.gl_buf

			if gl_state.stereo_mode == STEREO_MODE_ROW_INTERLEAVED or gl_state.stereo_mode == STEREO_MODE_PIXEL_INTERLEAVED:

				for y in range(0, vid.height + 1, 2):

					gl_buf.vtx[gl_buf.vt    ] = 0
					gl_buf.vtx[gl_buf.vt + 1] = y - 0.5
					gl_buf.vtx[gl_buf.vt + 2] = vid.width
					gl_buf.vtx[gl_buf.vt + 3] = y - 0.5
					gl_buf.vt += 4

				flip_eyes ^= (client_y & 1)

			if gl_state.stereo_mode == STEREO_MODE_COLUMN_INTERLEAVED or gl_state.stereo_mode == STEREO_MODE_PIXEL_INTERLEAVED:

				for x in range(0, vid.width + 1, 2):

					gl_buf.vtx[gl_buf.vt    ] = x - 0.5
					gl_buf.vtx[gl_buf.vt + 1] = 0
					gl_buf.vtx[gl_buf.vt + 2] = x - 0.5
					gl_buf.vtx[gl_buf.vt + 3] = vid.height
					gl_buf.vt += 4

				flip_eyes ^= (client_x & 1)

			GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
			GL.glVertexPointer(2, GL.GL_FLOAT, 0, gl_buf.vtx)
			GL.glDrawArrays(GL.GL_LINES, 0, gl_buf.vt // 2)
			GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
			gl_buf.vt = 0

			GL.glStencilMask(0)
			GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)

			GL.glStencilFunc(GL.GL_EQUAL, int(drawing_left_eye) ^ int(flip_eyes), 1)
			GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_KEEP)

	if r_norefresh.value:

		return

	r_newrefdef = fd.copy() # r_newrefdef = *fd;

	if not r_worldmodel and not (r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL):

		clientserver.Com_Error(shared.ERR_DROP, "{}: NULL worldmodel".format("R_RenderView"))

	if r_speeds.value:

		c_brush_polys = 0
		c_alias_polys = 0

	gl1_light.R_PushDlights()

	if gl_finish.value:

		GL.glFinish()

	R_SetupFrame()

	files_surf.R_SetFrustum(vup, vpn, vright, r_origin, r_newrefdef.fov_x, r_newrefdef.fov_y,
		frustum)

	R_SetupGL()

	gl1_surf.R_MarkLeaves() # done here so we know if we're in water

	gl1_surf.R_DrawWorld()

	R_DrawEntitiesOnList()

	gl1_light.R_RenderDlights()

	R_DrawParticles()

	gl1_surf.R_DrawAlphaSurfaces()

	R_Flash()

	if r_speeds.value:

		clientserver.Com_Printf("{:4d} wpoly {:4d} epoly {} tex {} lmaps\n".format(
				c_brush_polys, c_alias_polys, gl1_surf.c_visible_textures,
				gl1_surf.c_visible_lightmaps))

	if gl_state.stereo_mode == STEREO_MODE_NONE:

		pass

	elif gl_state.stereo_mode == STEREO_MODE_ANAGLYPH:

		GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)

	elif gl_state.stereo_mode in (STEREO_MODE_ROW_INTERLEAVED, STEREO_MODE_COLUMN_INTERLEAVED, STEREO_MODE_PIXEL_INTERLEAVED):

		GL.glDisable(GL.GL_STENCIL_TEST)

def GL_GetSpecialBufferModeForStereoMode(stereo_mode): #enum stereo_modes (returns enum opengl_special_buffer_modes)

	if stereo_mode in (STEREO_MODE_NONE, STEREO_SPLIT_HORIZONTAL, STEREO_SPLIT_VERTICAL, STEREO_MODE_ANAGLYPH):

		return OPENGL_SPECIAL_BUFFER_MODE_NONE

	elif stereo_mode == STEREO_MODE_OPENGL:

		return OPENGL_SPECIAL_BUFFER_MODE_STEREO

	elif stereo_mode in (STEREO_MODE_ROW_INTERLEAVED, STEREO_MODE_COLUMN_INTERLEAVED, STEREO_MODE_PIXEL_INTERLEAVED):

		return OPENGL_SPECIAL_BUFFER_MODE_STENCIL

	return OPENGL_SPECIAL_BUFFER_MODE_NONE

"""
/*
====================
R_SetLightLevel

====================
"""
def R_SetLightLevel (currententity): #entity_t *

	#vec3_t		shadelight;
	shadelight = np.zeros((3,), dtype=np.float32)

	if r_newrefdef.rdflags & shared.RDF_NOWORLDMODEL:
		return

	# save off light value for server to look at (BIG HACK!)

	gl1_light.R_LightPoint (currententity, r_newrefdef.vieworg, shadelight)

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
RI_RenderFrame

@@@@@@@@@@@@@@@@@@@@@
"""
def RI_RenderFrame(fd): #refdef_t * (static)

	gl1_buffer.R_ApplyGLBuffer()	# menu rendering when needed
	R_RenderView(fd)
	R_SetLightLevel(None)
	R_SetGL2D()

def R_Strings_f(): #void (static)

	gl1_misc.R_Strings(True)

#ifdef YQ2_GL1_GLES
#define ONLY_ENABLED_IN_GL1   "0"
#else
ONLY_ENABLED_IN_GL1 = "1"
#endif

def R_Register(): #void

	global gl_lefthand, r_gunfov, r_farsee, r_norefresh, r_fullbright, r_drawentities, r_drawworld, \
		r_novis, r_lerpmodels, r_speeds, r_lightlevel, gl1_overbrightbits, gl1_particle_min_size, \
		gl1_particle_max_size, gl1_particle_size, gl1_particle_att_a, gl1_particle_att_b, \
		gl1_particle_att_c, gl1_particle_square, r_modulate, r_mode, gl_lightmap, gl_shadows, \
		gl1_stencilshadow, gl1_dynamic, gl_nobind, gl1_round_down, gl1_picmip, gl_showtris, gl_showbbox, \
		gl1_ztrick, gl_zfix, gl_finish, r_clear, r_cull, gl_polyblend, gl1_flashblend, r_fixsurfsky, \
		gl_znear, gl1_minlight, gl_texturemode, gl1_texturealphamode, gl1_texturesolidmode, \
		gl_anisotropic, r_lockpvs, gl1_palettedtexture, gl1_pointparameters, gl1_multitexture, \
		gl1_tilerendering, gl_drawbuffer, r_vsync, gl1_saturatelighting, vid_fullscreen, vid_gamma, \
		r_customwidth, r_customheight, gl_msaa_samples, r_retexturing, r_validation, \
		r_scale8bittextures, gl_nolerp_list, r_lerp_list, r_2D_unfiltered, r_videos_unfiltered, \
		gl1_stereo, gl1_stereo_separation, gl1_stereo_anaglyph_colors, gl1_stereo_convergence, \
		gl1_waterwarp

	gl_lefthand = ri.Cvar_Get("hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	r_gunfov = ri.Cvar_Get("r_gunfov", "80", shared.CVAR_ARCHIVE)
	r_farsee = ri.Cvar_Get("r_farsee", "0", shared.CVAR_LATCH | shared.CVAR_ARCHIVE)
	r_norefresh = ri.Cvar_Get("r_norefresh", "0", 0)
	r_fullbright = ri.Cvar_Get("r_fullbright", "0", 0)
	r_drawentities = ri.Cvar_Get("r_drawentities", "1", 0)
	r_drawworld = ri.Cvar_Get("r_drawworld", "1", 0)
	r_novis = ri.Cvar_Get("r_novis", "0", 0)
	r_lerpmodels = ri.Cvar_Get("r_lerpmodels", "1", 0)
	r_speeds = ri.Cvar_Get("r_speeds", "0", 0)

	r_lightlevel = ri.Cvar_Get("r_lightlevel", "0", 0)
	gl1_overbrightbits = ri.Cvar_Get("gl1_overbrightbits", "0", shared.CVAR_ARCHIVE)

	gl1_particle_min_size = ri.Cvar_Get("gl1_particle_min_size", "2", shared.CVAR_ARCHIVE)
	gl1_particle_max_size = ri.Cvar_Get("gl1_particle_max_size", "40", shared.CVAR_ARCHIVE)
	gl1_particle_size = ri.Cvar_Get("gl1_particle_size", "40", shared.CVAR_ARCHIVE)
	gl1_particle_att_a = ri.Cvar_Get("gl1_particle_att_a", "0.01", shared.CVAR_ARCHIVE)
	gl1_particle_att_b = ri.Cvar_Get("gl1_particle_att_b", "0.0", shared.CVAR_ARCHIVE)
	gl1_particle_att_c = ri.Cvar_Get("gl1_particle_att_c", "0.01", shared.CVAR_ARCHIVE)
	gl1_particle_square = ri.Cvar_Get("gl1_particle_square", "0", shared.CVAR_ARCHIVE)

	r_modulate = ri.Cvar_Get("r_modulate", "1", shared.CVAR_ARCHIVE)
	r_mode = ri.Cvar_Get("r_mode", "4", shared.CVAR_ARCHIVE)
	gl_lightmap = ri.Cvar_Get("r_lightmap", "0", 0)
	gl_shadows = ri.Cvar_Get("r_shadows", "0", shared.CVAR_ARCHIVE)
	gl1_stencilshadow = ri.Cvar_Get("gl1_stencilshadow", "0", shared.CVAR_ARCHIVE)
	gl1_dynamic = ri.Cvar_Get("gl1_dynamic", "1", 0)
	gl_nobind = ri.Cvar_Get("gl_nobind", "0", 0)
	gl1_round_down = ri.Cvar_Get("gl1_round_down", "1", 0)
	gl1_picmip = ri.Cvar_Get("gl1_picmip", "0", 0)
	gl_showtris = ri.Cvar_Get("gl_showtris", "0", 0)
	gl_showbbox = ri.Cvar_Get("gl_showbbox", "0", 0)
	gl1_ztrick = ri.Cvar_Get("gl1_ztrick", "0", 0)
	gl_zfix = ri.Cvar_Get("gl_zfix", "0", 0)
	gl_finish = ri.Cvar_Get("gl_finish", "0", shared.CVAR_ARCHIVE)
	r_clear = ri.Cvar_Get("r_clear", "0", 0)
	r_cull = ri.Cvar_Get("r_cull", "1", 0)
	gl_polyblend = ri.Cvar_Get("gl_polyblend", "1", 0)
	gl1_flashblend = ri.Cvar_Get("gl1_flashblend", "0", 0)
	r_fixsurfsky = ri.Cvar_Get("r_fixsurfsky", "0", shared.CVAR_ARCHIVE)
	gl_znear = ri.Cvar_Get("gl_znear", "4", shared.CVAR_ARCHIVE)
	gl1_minlight = ri.Cvar_Get("gl1_minlight", "0", shared.CVAR_ARCHIVE)

	gl_texturemode = ri.Cvar_Get("gl_texturemode", "GL_LINEAR_MIPMAP_NEAREST", shared.CVAR_ARCHIVE)
	gl1_texturealphamode = ri.Cvar_Get("gl1_texturealphamode", "default", shared.CVAR_ARCHIVE)
	gl1_texturesolidmode = ri.Cvar_Get("gl1_texturesolidmode", "default", shared.CVAR_ARCHIVE)
	gl_anisotropic = ri.Cvar_Get("r_anisotropic", "0", shared.CVAR_ARCHIVE)
	r_lockpvs = ri.Cvar_Get("r_lockpvs", "0", 0)

	gl1_palettedtexture = ri.Cvar_Get("r_palettedtextures", "0", shared.CVAR_ARCHIVE)
	gl1_pointparameters = ri.Cvar_Get("gl1_pointparameters", ONLY_ENABLED_IN_GL1, shared.CVAR_ARCHIVE)
	gl1_multitexture = ri.Cvar_Get("gl1_multitexture", "1", shared.CVAR_ARCHIVE)
	#ifndef YQ2_GL1_GLES
	gl1_tilerendering = ri.Cvar_Get("gl1_tilerendering", "0", shared.CVAR_ARCHIVE)
	#endif

	gl_drawbuffer = ri.Cvar_Get("gl_drawbuffer", "GL_BACK", 0)
	r_vsync = ri.Cvar_Get("r_vsync", "1", shared.CVAR_ARCHIVE)

	gl1_saturatelighting = ri.Cvar_Get("gl1_saturatelighting", "0", 0)

	vid_fullscreen = ri.Cvar_Get("vid_fullscreen", "0", shared.CVAR_ARCHIVE)
	vid_gamma = ri.Cvar_Get("vid_gamma", "1.2", shared.CVAR_ARCHIVE)

	r_customwidth = ri.Cvar_Get("r_customwidth", "1024", shared.CVAR_ARCHIVE)
	r_customheight = ri.Cvar_Get("r_customheight", "768", shared.CVAR_ARCHIVE)
	gl_msaa_samples = ri.Cvar_Get ( "r_msaa_samples", "0", shared.CVAR_ARCHIVE )

	r_retexturing = ri.Cvar_Get("r_retexturing", "1", shared.CVAR_ARCHIVE)
	r_validation = ri.Cvar_Get("r_validation", "0", shared.CVAR_ARCHIVE)
	r_scale8bittextures = ri.Cvar_Get("r_scale8bittextures", "0", shared.CVAR_ARCHIVE)

	# don't bilerp characters and crosshairs
	gl_nolerp_list = ri.Cvar_Get("r_nolerp_list", "pics/conchars.pcx pics/ch1.pcx pics/ch2.pcx pics/ch3.pcx", shared.CVAR_ARCHIVE)
	# textures that should always be filtered, even if r_2D_unfiltered or an unfiltered gl mode is used
	r_lerp_list = ri.Cvar_Get("r_lerp_list", "", shared.CVAR_ARCHIVE)
	# don't bilerp any 2D elements
	r_2D_unfiltered = ri.Cvar_Get("r_2D_unfiltered", "0", shared.CVAR_ARCHIVE)
	# don't bilerp videos
	r_videos_unfiltered = ri.Cvar_Get("r_videos_unfiltered", "0", shared.CVAR_ARCHIVE)

	gl1_stereo = ri.Cvar_Get( "gl1_stereo", "0", shared.CVAR_ARCHIVE )
	gl1_stereo_separation = ri.Cvar_Get( "gl1_stereo_separation", "-0.4", shared.CVAR_ARCHIVE )
	gl1_stereo_anaglyph_colors = ri.Cvar_Get( "gl1_stereo_anaglyph_colors", "rc", shared.CVAR_ARCHIVE )
	gl1_stereo_convergence = ri.Cvar_Get( "gl1_stereo_convergence", "1", shared.CVAR_ARCHIVE )

	gl1_waterwarp = ri.Cvar_Get( "gl1_waterwarp", "1.0", shared.CVAR_ARCHIVE )

	ri.Cmd_AddCommand("imagelist", gl1_image.R_ImageList_f)
	ri.Cmd_AddCommand("screenshot", gl1_misc.R_ScreenShot)
	ri.Cmd_AddCommand("modellist", gl1_model.Mod_Modellist_f)
	ri.Cmd_AddCommand("gl_strings", R_Strings_f)

#undef ONLY_ENABLED_IN_GL1

"""
 * Used in the SetMode functions below, no need to have these in local.h
"""
#typedef enum
rserr_ok = 0

rserr_invalid_mode = 1

rserr_unknown = 2
#} rserr_t;

"""
 * Changes the video mode
"""
def SetMode_impl(pwidth, pheight, mode, fullscreen): #int *, int *, int, int (returns int, *pwidth, *pheight) (static)

	clientserver.Com_Printf("Setting mode {}:".format(int(mode)))

	# mode -1 is not in the vid mode table - so we keep the values in pwidth
	#   and pheight and don't even try to look up the mode info
	if mode >= 0:

		ok, w, h = ri.Vid_GetModeInfo(int(mode))
		if not ok:

			clientserver.Com_Printf(" invalid mode\n")
			return rserr_invalid_mode, pwidth, pheight

		pwidth, pheight = w, h

	# We trying to get resolution from desktop
	if mode == -2:

		ok, w, h = ri.GLimp_GetDesktopMode()
		if not ok:

			clientserver.Com_Printf(" can't detect mode\n" )
			return rserr_invalid_mode, pwidth, pheight

		pwidth, pheight = w, h

	clientserver.Com_Printf(" {}x{} (vid_fullscreen {})\n".format(pwidth, pheight, int(fullscreen)))

	# Q2PORT: the C's GLimp_InitGraphics() can change the size through the
	# pointers; the port's returns only the result
	if not ri.GLimp_InitGraphics(int(fullscreen), pwidth, pheight):

		return rserr_invalid_mode, pwidth, pheight

	# This is totally obscure: For some strange reasons the renderer
	#   maintains two(!) representations of the resolution. One comes
	#   from the client and is saved in r_newrefdef. The other one
	#   is determined here and saved in vid. Several calculations take
	#   both representations into account.
	#
	#   The values will always be the same. The GLimp_InitGraphics()
	#   call above communicates the requested resolution to the client
	#   where it ends up in the vid subsystem and the vid system writes
	#   it into r_newrefdef.
	#
	#   We can't avoid the client roundtrip, because we can get the
	#   real size of the drawable (which can differ from the resolution
	#   due to high dpi awareness) only after the render context was
	#   created by GLimp_InitGraphics() and need to communicate it
	#   somehow to the client. So we just overwrite the values saved
	#   in vid with a call to RI_GetDrawableSize(), just like the
	#   client does. This makes sure that both values are the same
	#   and everything is okay.
	#
	#   We also need to take the special case fullscreen window into
	#   account. With the fullscreen windows we cannot use the
	#   drawable size, it would scale all cases to the size of the
	#   window. Instead use the drawable size when the user wants
	#   native resolution (the fullscreen window fills the screen)
	#   and use the requested resolution in all other cases.
	if gl1_sdl.IsHighDPIaware:

		if vid_fullscreen.value != 2:

			pwidth, pheight = gl1_sdl.RI_GetDrawableSize()

		else:

			if r_mode.value == -2:

				# User requested native resolution.
				pwidth, pheight = gl1_sdl.RI_GetDrawableSize()

	return rserr_ok, pwidth, pheight

def R_SetMode(): #void (returns qboolean)

	#rserr_t err;
	#int fullscreen;

	fullscreen = int(vid_fullscreen.value)

	# a bit hackish approach to enable custom resolutions:
	#   Glimp_SetMode needs these values set for mode -1
	vid.width = int(r_customwidth.value)
	vid.height = int(r_customheight.value)

	err, vid.width, vid.height = SetMode_impl(vid.width, vid.height, r_mode.value, fullscreen)
	if err == rserr_ok:

		if r_mode.value == -1:

			gl_state.prev_mode = 4 # safe default for custom mode

		else:

			gl_state.prev_mode = int(r_mode.value)

	else:

		if err == rserr_invalid_mode:

			clientserver.Com_Printf("ref_gl::R_SetMode() - invalid mode\n")
			if gl_msaa_samples.value != 0.0:

				clientserver.Com_Printf("gl_msaa_samples was {} - will try again with gl_msaa_samples = 0\n".format(int(gl_msaa_samples.value)))
				ri.Cvar_SetValue("r_msaa_samples", 0.0)
				gl_msaa_samples.modified = False

				err, vid.width, vid.height = SetMode_impl(vid.width, vid.height, r_mode.value, 0)
				if err == rserr_ok:

					return True

			if r_mode.value == gl_state.prev_mode:

				# trying again would result in a crash anyway, give up already
				# (this would happen if your initing fails at all and your resolution already was 640x480)
				return False

			ri.Cvar_SetValue("r_mode", gl_state.prev_mode)
			r_mode.modified = False

		# try setting it back to something safe
		err, vid.width, vid.height = SetMode_impl(vid.width, vid.height, gl_state.prev_mode, 0)
		if err != rserr_ok:

			clientserver.Com_Printf("ref_gl::R_SetMode() - could not revert to safe mode\n")
			return False

	return True

# just to avoid too many preprocessor directives in RI_Init()
#typedef enum
rf_opengl14 = 0
rf_opengles10 = 1
#} refresher_t;

def RI_Init(): #void (returns qboolean)

	"""
	int j;
	byte *colormap;
	extern float r_turbsin[256];
	"""

	#ifdef YQ2_GL1_GLES
	#else
	GLEXTENSION_NPOT = "GL_ARB_texture_non_power_of_two"
	refresher = rf_opengl14 #static const refresher_t
	#endif

	shared_c.Swap_Init()

	# Q2PORT: the C module is reloaded on every vid_restart, so its static
	# r_turbsin starts out unscaled; this module stays loaded, so reload the table
	gl1_warp.r_turbsin[:] = gl1_warp._LoadTurbsin()
	for j in range(256):

		gl1_warp.r_turbsin[j] *= 0.5

	# Q2PORT: likewise for R_EnableMultitexture's static state (the new context
	# starts with multitexturing off), R_TexEnv's lastmodes and the zeroed
	# gl_config / gl_state (the bound textures are those of the old context)
	gl1_image.R_EnableMultitexture_active = False
	gl1_image.lastmodes[:] = [-1, -1]
	global gl_config, gl_state
	gl_config = glconfig_t()
	gl_state = glstate_t()

	clientserver.Com_Printf("Refresh: " + REF_VERSION + "\n")
	clientserver.Com_Printf("Client: " + common_h.YQ2VERSION + "\n\n")

	#ifdef DEBUG
	#endif

	files_pcx.GetPCXPalette(None, gl1_image.d_8to24table) # GetPCXPalette (&colormap, d_8to24table);
	#free(colormap);

	R_Register()

	# initialize our QGL dynamic bindings
	qgl.QGL_Init()

	# set our "safe" mode
	gl_state.prev_mode = 4
	gl_state.stereo_mode = int(gl1_stereo.value)

	# create the window and set up the context
	if not R_SetMode():

		qgl.QGL_Shutdown()
		clientserver.Com_Printf("ref_gl1::{} - could not R_SetMode()\n".format("RI_Init"))
		return False

	ri.Vid_MenuInit()

	# --------

	# get our various GL strings
	gl_config.vendor_string     = glGetString(GL.GL_VENDOR).decode("ascii", "ignore")
	gl_config.renderer_string   = glGetString(GL.GL_RENDERER).decode("ascii", "ignore")
	gl_config.version_string    = glGetString(GL.GL_VERSION).decode("ascii", "ignore")
	gl_config.extensions_string = glGetString(GL.GL_EXTENSIONS).decode("ascii", "ignore")
	gl_config.num_extensions    = shared_c.Word_Count(gl_config.extensions_string)

	clientserver.Com_Printf("\nOpenGL features:\n")
	gl1_misc.R_Strings(False)

	# sscanf(gl_config.version_string, "%d.%d", &gl_config.major_version, &gl_config.minor_version);
	try:
		gl_config.major_version, gl_config.minor_version = (int(x) for x in gl_config.version_string.split(" ")[0].split(".")[:2])
	except ValueError:
		gl_config.major_version, gl_config.minor_version = 0, 0

	if ( refresher == rf_opengl14 and
		gl_config.major_version == 1 and gl_config.minor_version < 4 ):

		qgl.QGL_Shutdown()
		clientserver.Com_Printf("Support for OpenGL 1.4 is not available\n")

		return False

	clientserver.Com_Printf("\nProbing for OpenGL extensions:\n")

	# ----

	# Point parameters
	clientserver.Com_Printf(" - Point parameters: ")

	if ( refresher == rf_opengles10 or
		"GL_ARB_point_parameters" in gl_config.extensions_string or
		"GL_EXT_point_parameters" in gl_config.extensions_string ):	# should exist for all OGL 1.4 hw...

		qgl.qglPointParameterf = gl1_sdl.RI_GetProcAddress ( "glPointParameterf" )
		qgl.qglPointParameterfv = gl1_sdl.RI_GetProcAddress ( "glPointParameterfv" )

		if not qgl.qglPointParameterf or not qgl.qglPointParameterfv:

			qgl.qglPointParameterf = gl1_sdl.RI_GetProcAddress ( "glPointParameterfARB" )
			qgl.qglPointParameterfv = gl1_sdl.RI_GetProcAddress ( "glPointParameterfvARB" )

		if not qgl.qglPointParameterf or not qgl.qglPointParameterfv:

			qgl.qglPointParameterf = gl1_sdl.RI_GetProcAddress ( "glPointParameterfEXT" )
			qgl.qglPointParameterfv = gl1_sdl.RI_GetProcAddress ( "glPointParameterfvEXT" )

	gl_config.pointparameters = False

	if gl1_pointparameters.value:

		if qgl.qglPointParameterf and qgl.qglPointParameterfv:

			gl_config.pointparameters = True
			clientserver.Com_Printf("Okay\n")

		else:

			clientserver.Com_Printf("Failed\n")

	else:

		clientserver.Com_Printf("Disabled\n")

	# ----

	# Paletted texture
	clientserver.Com_Printf(" - Paletted texture: ")

	if ("GL_EXT_paletted_texture" in gl_config.extensions_string and
		"GL_EXT_shared_texture_palette" in gl_config.extensions_string):

		qgl.qglColorTableEXT = gl1_sdl.RI_GetProcAddress ("glColorTableEXT")

	gl_config.palettedtexture = False

	if gl1_palettedtexture.value:

		if qgl.qglColorTableEXT:

			gl_config.palettedtexture = True
			clientserver.Com_Printf("Okay\n")

		else:

			clientserver.Com_Printf("Failed\n")

	else:

		clientserver.Com_Printf("Disabled\n")

	# --------

	# Anisotropic
	clientserver.Com_Printf(" - Anisotropic: ")

	if "GL_EXT_texture_filter_anisotropic" in gl_config.extensions_string:

		gl_config.anisotropic = True
		gl_config.max_anisotropy = float(GL.glGetFloatv(qgl_h.GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT))

		clientserver.Com_Printf("{}x\n".format(int(gl_config.max_anisotropy)))

	else:

		gl_config.anisotropic = False
		gl_config.max_anisotropy = 0.0

		clientserver.Com_Printf("Failed\n")

	# ----

	# Non power of two textures
	clientserver.Com_Printf(" - Non power of two textures: ")

	if GLEXTENSION_NPOT in gl_config.extensions_string:

		gl_config.npottextures = True
		clientserver.Com_Printf("Okay\n")

	else:

		gl_config.npottextures = False
		clientserver.Com_Printf("Failed\n")

	#undef GLEXTENSION_NPOT

	# ----

	# Multitexturing
	gl_config.multitexture = False

	clientserver.Com_Printf(" - Multitexturing: ")

	if refresher == rf_opengles10 or "GL_ARB_multitexture" in gl_config.extensions_string:

		qgl.qglActiveTexture = gl1_sdl.RI_GetProcAddress ("glActiveTexture")
		qgl.qglClientActiveTexture = gl1_sdl.RI_GetProcAddress ("glClientActiveTexture")

		if not qgl.qglActiveTexture or not qgl.qglClientActiveTexture:

			qgl.qglActiveTexture = gl1_sdl.RI_GetProcAddress ("glActiveTextureARB")
			qgl.qglClientActiveTexture = gl1_sdl.RI_GetProcAddress ("glClientActiveTextureARB")

	if gl1_multitexture.value:

		if qgl.qglActiveTexture and qgl.qglClientActiveTexture:

			gl_config.multitexture = True
			clientserver.Com_Printf("Okay\n")

		else:

			clientserver.Com_Printf("Failed\n")

	else:

		clientserver.Com_Printf("Disabled\n")

	# ----

	# Discard framebuffer: Enables the use of a "performance hint" to the graphic
	# driver in GLES1, to get rid of the contents of the different framebuffers.
	# Useful for some GPUs that may attempt to keep them and/or write them back to
	# external/uniform memory, actions that are useless for Quake 2 rendering path.
	# https://registry.khronos.org/OpenGL/extensions/EXT/EXT_discard_framebuffer.txt
	# Regardless of the existence of this extension, if gl_config.tilerendering is
	# true, glClear() will run at the start of each frame, helping mobile GPUs.

	#ifdef YQ2_GL1_GLES
	# (GLES only)
	#endif

	# ----

	# Tile-Based Rendering optimizations
	# ----------------------------------
	# Controlled by the `gl1_tilerendering` cvar, this in meant for Tile-Based / Deferred Rendering
	# GPUs (embedded / mobile / SoCs), which differ from Immediate-Mode Rendering ones (desktop).
	# Imply two alterations in rendering:
	#
	# 1.- Lightmap copies: keep multiple copies of "the same" lightmap on video memory. All of
	# them are actually different, because they are affected by different dynamic lighting, in
	# different frames. In TBR, active manipulation of textures already being used in the last
	# few frames can cause slowdown, so we avoid using them after being just changed. Note that
	# this requires mtex support, so may not work on VERY old GL ES 1.0 devices (1.1 is safe).
	# Watch out in low VRAM situations.
	#
	# 2.- Discard framebuffers / glClear before rendering every frame: explained above in
	# "Discard framebuffer".

	clientserver.Com_Printf("Optimizations target: ")
	gl_config.tilerendering = False

	if ( gl_config.multitexture
		#ifndef YQ2_GL1_GLES
		and gl1_tilerendering.value
		#endif
	):

		gl_config.tilerendering = True
		clientserver.Com_Printf("SBC / embedded (TBR)\n")

	else:

		clientserver.Com_Printf("Desktop (IMR)\n")

	# ----

	R_ResetClearColor()
	gl1_misc.R_SetDefaultState()

	gl1_scrap.Scrap_Init()
	gl1_image.R_InitImages()
	gl1_model.Mod_Init()
	gl1_misc.R_InitParticleTexture()
	gl1_draw.Draw_InitLocal()
	gl1_buffer.R_ResetGLBuffer()

	return True

def RI_Shutdown(): #void

	ri.Cmd_RemoveCommand("modellist")
	ri.Cmd_RemoveCommand("screenshot")
	ri.Cmd_RemoveCommand("imagelist")
	ri.Cmd_RemoveCommand("gl_strings")

	gl1_lightmap.LM_FreeLightmapBuffers()
	gl1_model.Mod_FreeAll()

	gl1_image.R_ShutdownImages()

	# shutdown OS specific OpenGL stuff like contexts, etc.
	gl1_sdl.RI_ShutdownContext()

	# shutdown our QGL subsystem
	qgl.QGL_Shutdown()

def RI_BeginFrame(camera_separation): #float

	gl_state.camera_separation = camera_separation

	# force a vid_restart if gl1_stereo has been modified.
	if gl_state.stereo_mode != gl1_stereo.value:

		# If we've gone from one mode to another with the same special buffer requirements there's no need to restart.
		if GL_GetSpecialBufferModeForStereoMode(gl_state.stereo_mode) == GL_GetSpecialBufferModeForStereoMode(gl1_stereo.value):

			gl_state.stereo_mode = int(gl1_stereo.value)

		else:

			clientserver.Com_Printf("stereo supermode changed, restarting video!\n")
			ri.Cmd_ExecuteText(common_h.EXEC_APPEND, "vid_restart\n")

	if vid_gamma.modified:

		vid_gamma.modified = False
		gl1_sdl.RI_UpdateGamma()

	# Clamp overbrightbits
	if gl1_overbrightbits.modified:

		obb_val = int(gl1_overbrightbits.value)

		obb_val = shared.Q_clamp(obb_val, 0, 4)
		if obb_val == 3:	# allowed values: 0,1,2,4

			obb_val = 2

		ri.Cvar_SetValue("gl1_overbrightbits", obb_val)
		gl1_overbrightbits.modified = False

	# go into 2D mode

	# FIXME: just call R_SetGL2D();

	#int x, w, y, h;
	drawing_left_eye = gl_state.camera_separation < 0 #qboolean
	stereo_split_tb = ((gl_state.stereo_mode == STEREO_SPLIT_VERTICAL) and gl_state.camera_separation) #qboolean
	stereo_split_lr = ((gl_state.stereo_mode == STEREO_SPLIT_HORIZONTAL) and gl_state.camera_separation) #qboolean

	x = 0
	w = vid.width
	y = 0
	h = vid.height

	if stereo_split_lr:
		w = int(w / 2)
		x = 0 if drawing_left_eye else w

	if stereo_split_tb:
		h = int(h / 2)
		y = h if drawing_left_eye else 0

	GL.glViewport(x, y, w, h)
	GL.glMatrixMode(GL.GL_PROJECTION)
	GL.glLoadIdentity()
	GL.glOrtho(0, vid.width, vid.height, 0, -99999, 99999)
	GL.glMatrixMode(GL.GL_MODELVIEW)
	GL.glLoadIdentity()
	GL.glDisable(GL.GL_DEPTH_TEST)
	GL.glDisable(GL.GL_CULL_FACE)
	GL.glDisable(GL.GL_BLEND)
	GL.glEnable(GL.GL_ALPHA_TEST)
	GL.glColor4f(1, 1, 1, 1)

	if gl1_particle_square.modified:

		if gl_config.pointparameters:

			# GL_POINT_SMOOTH is not implemented by some OpenGL
			# drivers, especially the crappy Mesa3D backends like
			# i915.so. That the points are squares and not circles
			# is not a problem by Quake II!
			if gl1_particle_square.value:

				GL.glDisable(GL.GL_POINT_SMOOTH)

			else:

				GL.glEnable(GL.GL_POINT_SMOOTH)

		else:

			# particles aren't drawn as GL_POINTS, but as textured triangles
			# => update particle texture to look square - or circle-ish
			gl1_misc.R_InitParticleTexture()

		gl1_particle_square.modified = False

	# draw buffer stuff
	if gl_drawbuffer.modified:

		gl_drawbuffer.modified = False

		#ifndef YQ2_GL1_GLES
		if (gl_state.camera_separation == 0) or gl_state.stereo_mode != STEREO_MODE_OPENGL:

			if shared_c.Q_stricmp(gl_drawbuffer.string, "GL_FRONT") == 0:

				GL.glDrawBuffer(GL.GL_FRONT)

			else:

				GL.glDrawBuffer(GL.GL_BACK)

		#endif

	# texturemode stuff
	if (gl_texturemode.modified or (gl_config.anisotropic and gl_anisotropic.modified)
	    or gl_nolerp_list.modified or r_lerp_list.modified
		or r_2D_unfiltered.modified or r_videos_unfiltered.modified):

		gl1_image.R_TextureMode(gl_texturemode.string)
		gl_texturemode.modified = False
		gl_anisotropic.modified = False
		gl_nolerp_list.modified = False
		r_lerp_list.modified = False
		r_2D_unfiltered.modified = False
		r_videos_unfiltered.modified = False

	if gl1_texturealphamode.modified:

		gl1_image.R_TextureAlphaMode(gl1_texturealphamode.string)
		gl1_texturealphamode.modified = False

	if gl1_texturesolidmode.modified:

		gl1_image.R_TextureSolidMode(gl1_texturesolidmode.string)
		gl1_texturesolidmode.modified = False

	if r_vsync.modified:

		r_vsync.modified = False
		gl1_sdl.RI_SetVsync()

	# clear screen if desired
	R_Clear()

"""
=============
RI_SetPalette
=============
*/
"""
r_rawpalette = [0]*256 #unsigned[256];

def RI_SetPalette (palette): #const unsigned char *
	
	#int		i;
	global r_rawpalette

	#byte *rp = ( byte * ) r_rawpalette;

	if palette is not None:
	
		for i in range(256):
		
			c = [0, 0, 0, 0]
			c[0] = gl1_image.gammatable[palette[i*3+0]]
			c[1] = gl1_image.gammatable[palette[i*3+1]]
			c[2] = gl1_image.gammatable[palette[i*3+2]]
			c[3] = 0xff
			r_rawpalette[i] = struct.unpack("<L", struct.pack("<BBBB", *c))[0]
		
	else:
	
		for i in range(256):
		
			c = gl1_image.d_8to24table[i]
			r_rawpalette[i] = struct.unpack("<L", struct.pack("<BBBB", c[0], c[1], c[2], 0xff))[0]
	
	gl1_image.R_SetTexturePalette( r_rawpalette )

	GL.glClearColor (0,0,0,0)
	GL.glClear (GL.GL_COLOR_BUFFER_BIT)
	R_ResetClearColor ()


"""
 R_DrawBeam
"""
def R_DrawBeam(e): #entity_t *

	"""
	int i, clr[4];

	vec3_t perpvec;
	vec3_t direction, normalized_direction;
	vec3_t start_points[NUM_BEAM_SEGS], end_points[NUM_BEAM_SEGS];
	vec3_t oldorigin, origin;

	GLfloat vtx[3*NUM_BEAM_SEGS*4];
	unsigned int index_vtx = 0;
	unsigned int pointb;
	"""
	clr = [0, 0, 0, 0]
	perpvec = np.zeros((3,), dtype=np.float32)
	direction = np.zeros((3,), dtype=np.float32)
	normalized_direction = np.zeros((3,), dtype=np.float32)
	start_points = np.zeros((NUM_BEAM_SEGS, 3), dtype=np.float32)
	end_points = np.zeros((NUM_BEAM_SEGS, 3), dtype=np.float32)
	oldorigin = np.zeros((3,), dtype=np.float32)
	origin = np.zeros((3,), dtype=np.float32)

	vtx = np.zeros((3 * NUM_BEAM_SEGS * 4,), dtype=np.float32)
	index_vtx = 0

	oldorigin[0] = e.oldorigin[0]
	oldorigin[1] = e.oldorigin[1]
	oldorigin[2] = e.oldorigin[2]

	origin[0] = e.origin[0]
	origin[1] = e.origin[1]
	origin[2] = e.origin[2]

	normalized_direction[0] = direction[0] = oldorigin[0] - origin[0]
	normalized_direction[1] = direction[1] = oldorigin[1] - origin[1]
	normalized_direction[2] = direction[2] = oldorigin[2] - origin[2]

	if shared_c.VectorNormalize(normalized_direction) == 0:

		return

	shared_c.PerpendicularVector(perpvec, normalized_direction)
	shared_c.VectorScale(perpvec, e.frame / 2, perpvec)

	for i in range(6):

		shared_c.RotatePointAroundVector(start_points[i], normalized_direction, perpvec,
				(360.0 / NUM_BEAM_SEGS) * i)
		shared.VectorAdd(start_points[i], origin, start_points[i])
		shared.VectorAdd(start_points[i], direction, end_points[i])

	gl1_image.R_EnableMultitexture(False)
	GL.glDisable(GL.GL_TEXTURE_2D)
	GL.glEnable(GL.GL_BLEND)
	GL.glDepthMask(GL.GL_FALSE)

	col = gl1_image.d_8to24table[e.skinnum & 0xFF] # Q2PORT: (r, g, b, a), the C takes the bytes of LittleLong(d_8to24table[...])
	clr[0] = col[0]
	clr[1] = col[1]
	clr[2] = col[2]
	clr[3] = int(e.alpha * 255)

	GL.glColor4ub(gl1_image.gammatable[clr[0]], gl1_image.gammatable[clr[1]],
		gl1_image.gammatable[clr[2]], clr[3])

	for i in range(NUM_BEAM_SEGS):

		vtx[index_vtx:index_vtx + 3] = start_points[i]
		index_vtx += 3

		vtx[index_vtx:index_vtx + 3] = end_points[i]
		index_vtx += 3

		pointb = (i + 1) % NUM_BEAM_SEGS
		vtx[index_vtx:index_vtx + 3] = start_points[pointb]
		index_vtx += 3

		vtx[index_vtx:index_vtx + 3] = end_points[pointb]
		index_vtx += 3

	GL.glEnableClientState( GL.GL_VERTEX_ARRAY )

	GL.glVertexPointer( 3, GL.GL_FLOAT, 0, vtx )
	GL.glDrawArrays( GL.GL_TRIANGLE_STRIP, 0, NUM_BEAM_SEGS * 4 )

	GL.glDisableClientState( GL.GL_VERTEX_ARRAY )

	GL.glEnable(GL.GL_TEXTURE_2D)
	GL.glDisable(GL.GL_BLEND)
	GL.glDepthMask(GL.GL_TRUE)

#extern int RI_PrepareForWindow(void);
#extern int RI_InitContext(void* win);

#extern void RI_BeginRegistration(const char *model);
#extern struct model_s * RI_RegisterModel(const char *name);
#extern struct image_s * RI_RegisterSkin(const char *name);

#extern void RI_SetSky(const char *name, float rotate, vec3_t axis);
#extern void RI_EndRegistration(void);

#extern void RI_RenderFrame(refdef_t *fd);

#extern void RI_SetPalette(const unsigned char *palette);
#extern qboolean RI_IsVSyncActive(void);
#extern void RI_EndFrame(void);

"""
=====================
RI_EndWorldRenderpass
=====================
"""
def RI_EndWorldRenderpass(): #void (returns qboolean) (static)

	return True

def GetRefAPI(imp): #refimport_t (returns refexport_t)

	global ri

	re = ref.refexport_t() # = {0}

	ri = imp

	re.api_version = ref.API_VERSION
	#re.framework_version = RI_GetSDLVersion(); Q2PORT: the port's refexport_t has no framework_version

	# Q2PORT: the port's client still calls id's re.Init(hinstance, wndproc) and
	# checks for -1
	re.Init = lambda hinstance, wndproc: 0 if RI_Init() else -1 # RI_Init
	re.Shutdown = RI_Shutdown
	re.PrepareForWindow = gl1_sdl.RI_PrepareForWindow
	re.InitContext = gl1_sdl.RI_InitContext
	re.GetDrawableSize = gl1_sdl.RI_GetDrawableSize
	re.ShutdownContext = gl1_sdl.RI_ShutdownContext
	re.IsVSyncActive = gl1_sdl.RI_IsVSyncActive
	re.BeginRegistration = gl1_model.RI_BeginRegistration
	re.RegisterModel = gl1_model.RI_RegisterModel
	re.RegisterSkin = gl1_image.RI_RegisterSkin
	re.RegisterPic = gl1_draw.RDraw_FindPic # Q2PORT: id's refexport_t

	re.SetSky = gl1_warp.RI_SetSky
	re.EndRegistration = gl1_model.RI_EndRegistration

	re.RenderFrame = RI_RenderFrame

	re.DrawFindPic = gl1_draw.RDraw_FindPic

	re.DrawGetPicSize = gl1_draw.RDraw_GetPicSize
	#re.DrawPic = Draw_Pic;
	re.DrawPicScaled = gl1_draw.RDraw_PicScaled
	re.DrawPicScaledCol = gl1_draw.RDraw_PicScaledCol
	re.DrawStretchPic = gl1_draw.RDraw_StretchPic
	#re.DrawChar = Draw_Char;
	re.DrawCharScaled = gl1_draw.RDraw_CharScaled
	re.DrawTileClear = gl1_draw.RDraw_TileClear
	re.DrawFill = gl1_draw.RDraw_Fill
	re.DrawFadeScreen = gl1_draw.RDraw_FadeScreen

	re.DrawStretchRaw = gl1_draw.RDraw_StretchRaw

	re.SetPalette = RI_SetPalette
	re.BeginFrame = RI_BeginFrame
	re.EndWorldRenderpass = RI_EndWorldRenderpass
	re.EndFrame = gl1_sdl.RI_EndFrame

	re.AppActivate = lambda active: None # Q2PORT: id's refexport_t; Yamagi's has no AppActivate

	# Tell the client that we're unsing the
	# new renderer restart API.
	ri.Vid_RequestRestart(ref_h.ref_restart_t.RESTART_NO)

	return re

#ifdef DEBUG
#void glCheckError_(const char *file, const char *function, int line)
# (DEBUG builds only)
#endif
