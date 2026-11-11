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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * Header for the model stuff (gl3).
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
from enum import Enum
from common.header import files as files_h
from common.header import shared
from client.refresh import ref_shared


# used for vertex array elements when drawing brushes, sprites, sky and more
# (ok, it has the layout used for rendering brushes, but is not used there)
# Q2PORT: the structs are numpy structured dtypes with the C layout, so an
# array of them is the vertex buffer data; dtype.fields gives offsetof()
gl3_3D_vtx_t = np.dtype([
	("pos", "<f4", 3), #vec3_t
	("texCoord", "<f4", 2), #float [2]
	("lmTexCoord", "<f4", 2), #float [2], lightmap texture coordinate (sometimes unused)
	("normal", "<f4", 3), #vec3_t
	("lightFlags", "<u4"), #GLuint, bit i set means: dynlight i affects surface
]) # 44 bytes

# used for vertex array elements when drawing models
gl3_alias_vtx_t = np.dtype([
	("pos", "<f4", 3), #GLfloat [3]
	("texCoord", "<f4", 2), #GLfloat [2]
	("color", "<f4", 4), #GLfloat [4]
]) # 36 bytes

# surface flags
# Q2PORT: these and modtype_t are in ref_shared.h; kept here for the gl3 modules
SURF_PLANEBACK = ref_shared.SURF_PLANEBACK
SURF_DRAWSKY = ref_shared.SURF_DRAWSKY
SURF_DRAWTURB = ref_shared.SURF_DRAWTURB
SURF_DRAWBACKGROUND = ref_shared.SURF_DRAWBACKGROUND
SURF_UNDERWATER = ref_shared.SURF_UNDERWATER

modtype_t = ref_shared.modtype_t

# in memory representation
class glpoly_t(object):

	def __init__(self, numverts=4):

		# struct  glpoly_s *next;  Q2PORT: msurface_t.polys is a list
		# struct  glpoly_s *chain;
		self.numverts = numverts #int
		self.flags = 0 #int, for SURF_UNDERWATER (not needed anymore?)
		self.vertices = np.zeros(numverts, dtype=gl3_3D_vtx_t) #gl3_3D_vtx_t [4], variable sized

class msurface_t(object):

	def __init__(self):
		self.visframe = 0 #int, should be drawn when node is crossed
		self.plane = None #cplane_t *
		self.flags = 0 #int
		self.firstedge = 0 #int, look up in model->surfedges[], negative numbers
		self.numedges = 0 #int, are backwards edges
		self.texturemins = [0, 0] #short [2]
		self.extents = [0, 0] #short [2]
		self.light_s = 0 #int, gl lightmap coordinates
		self.light_t = 0 #int
		self.dlight_s = 0 #int, gl lightmap coordinates for dynamic lightmaps
		self.dlight_t = 0 #int
		self.polys = [] #glpoly_t list, multiple if warped
		# struct msurface_s *texturechain; replaced by a list
		self.texinfo = None #mtexinfo_t *
		self.dlightframe = 0 #int, lighting info
		self.dlightbits = 0 #int
		self.lightmaptexturenum = 0 #int
		self.styles = [0] * files_h.MAXLIGHTMAPS #byte, MAXLIGHTMAPS = MAX_LIGHTMAPS_PER_SURFACE
		self.samples = None #byte *, [numstyles*surfsize]

# this, must be struct model_s, not gl3model_s, because struct model_s* is returned by re.RegisterModel()
class gl3model_t(object):

	def __init__(self):
		self.reset()

	def reset(self):

		self.name = None #char [MAX_QPATH]
		self.registration_sequence = 0 #int
		self.type = modtype_t.mod_bad #modtype_t
		self.numframes = 0 #int
		self.flags = 0 #int
		self.mins = np.zeros((3,), dtype=np.float32) #vec3_t, volume occupied by the model graphics
		self.maxs = np.zeros((3,), dtype=np.float32) #vec3_t
		self.radius = 0.0 #float
		self.clipbox = False #qboolean, solid volume for clipping
		self.clipmins = np.zeros((3,), dtype=np.float32) #vec3_t
		self.clipmaxs = np.zeros((3,), dtype=np.float32) #vec3_t
		self.firstmodelsurface = 0 #int, brush model
		self.nummodelsurfaces = 0 #int
		self.lightmap = 0 #int, only for submodels
		self.numsubmodels = 0 #int
		self.submodels = [] #model_t *
		self.numplanes = 0 #int
		self.planes = [] #cplane_t *
		self.numleafs = 0 #int, number of visible leafs, not counting 0
		self.leafs = [] #mleaf_t *
		self.numvertexes = 0 #int
		self.vertexes = None #mvertex_t *
		self.numedges = 0 #int
		self.edges = None #medge_t *
		self.numnodes = 0 #int
		self.firstnode = 0 #int
		self.nodes = [] #mnode_t *
		self.numtexinfo = 0 #int
		self.texinfo = [] #mtexinfo_t *
		self.numsurfaces = 0 #int
		self.surfaces = [] #msurface_t *
		self.numsurfedges = 0 #int
		self.surfedges = None #int *
		self.nummarksurfaces = 0 #int
		self.marksurfaces = [] #msurface_t **
		self.vis = None #dvis_t *
		self.lightdata = None #byte *
		self.skins = [None] * files_h.MAX_MD2SKINS #gl3image_t *, for alias models and skins
		self.extradatasize = 0 #int
		self.extradata = None #void *
		self.origin = np.zeros((3,), dtype=np.float32) #vec3_t, submodules, for sounds or lights
