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
 * Header for the model stuff.
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
from enum import Enum
from common.header import files as files_h
from common.header import shared


VERTEXSIZE = 7

# surface flags
SURF_PLANEBACK = 2
SURF_DRAWSKY = 4
SURF_DRAWTURB = 0x10
SURF_DRAWBACKGROUND = 0x40
SURF_UNDERWATER = 0x80

class mtexinfo_t(object):

	def __init__(self):
		self.vecs = np.zeros((2, 4), dtype=np.float32) # float [2][4]
		self.flags = 0 #int
		self.numframes = None # int
		self.next = None # struct mtexinfo_s *, animation chain
		self.image = None # image_t *

class modtype_t(Enum):

	mod_bad = 0
	mod_brush = 1
	mod_sprite = 2
	mod_alias = 3

class glpoly_t(object):

	def __init__(self):
		# struct glpoly_s *next, *chain; are replaced by lists of polys
		self.numverts = 0 #int
		self.flags = 0 #int, for SURF_UNDERWATER (not needed anymore?)
		self.verts = np.zeros((4, VERTEXSIZE), dtype=np.float32) # float [4][VERTEXSIZE], variable sized (xyz s1t1 s2t2)

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
		# struct msurface_s *texturechain, *lightmapchain; replaced by lists
		self.lmchain_frame = 0 #int, avoids adding this surface twice to the lightmap chain
		self.texinfo = None #mtexinfo_t *
		self.dlightframe = 0 #int, lighting info
		self.dlightbits = 0 #int
		self.dirty_lightmap = False #qboolean, lightmap has dynamic lights from previous frame (mtex only)
		self.lightmaptexturenum = 0 #int
		self.styles = [0] * files_h.MAXLIGHTMAPS #byte
		self.cached_light = [0.0] * files_h.MAXLIGHTMAPS #float, values currently used in lightmap
		self.samples = None #byte *, [numstyles*surfsize]

class mvertex_t(object):

	def __init__(self):
		self.position = np.zeros((3,), dtype=np.float32) # vec3_t

class medge_t(object):

	def __init__(self):
		self.v = [0, 0] # unsigned short [2]
		self.cachededgeoffset = 0 # unsigned int

class mmodel_t(object):

	def __init__(self):
		self.mins = np.zeros((3,), dtype=np.float32) # vec3_t
		self.maxs = np.zeros((3,), dtype=np.float32) # vec3_t
		self.origin = np.zeros((3,), dtype=np.float32) # vec3_t, for sounds or lights
		self.radius = 0.0 # float
		self.headnode = 0 # int
		self.visleafs = 0 # int, not including the solid leaf 0
		self.firstface = 0 # int
		self.numfaces = 0 # int

class mnode_t(object):

	def __init__(self):
		self.contents = -1 #int, -1, to differentiate from leafs
		self.visframe = 0 #int, node needs to be traversed if current
		self.minmaxs = [0.0] * 6 #float, for bounding box culling
		self.parent = None #struct mnode_s *
		self.plane = None #cplane_t *
		self.children = [None, None] #struct mnode_s [2]
		self.firstsurface = 0 #unsigned short
		self.numsurfaces = 0 #unsigned short

class mleaf_t(object):

	def __init__(self):
		self.contents = 0 #int, wil be a negative contents number
		self.visframe = 0 #int, node needs to be traversed if current
		self.minmaxs = [0.0] * 6 #float, for bounding box culling
		self.parent = None #struct mnode_s *
		self.cluster = -1 #int
		self.area = 0 #int
		self.firstmarksurface = [] #msurface_t list
		self.nummarksurfaces = 0 #int

class model_t(object):

	def __init__(self):
		self.reset()

	def reset(self):

		self.name = None #char [MAX_QPATH]
		self.registration_sequence = 0 #int
		self.type = modtype_t.mod_bad #modtype_t
		self.numframes = 0 #int
		self.flags = 0 #int
		self.mins = np.zeros((3,), dtype=np.float32) #vec3_t
		self.maxs = np.zeros((3,), dtype=np.float32) #vec3_t
		self.radius = 0.0 #float
		self.clipbox = False #qboolean
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
		self.skins = [None] * files_h.MAX_MD2SKINS #image_t *, for alias models and skins
		self.extradatasize = 0 #int
		self.extradata = None #void *
		self.origin = np.zeros((3,), dtype=np.float32) #vec3_t, submodules, for sounds or lights

"""
void	Mod_Init (void);
void	Mod_ClearAll (void);
const byte	*Mod_ClusterPVS (int cluster, const model_t *model);

void	Mod_Modellist_f (void);

void	*Hunk_Begin (int maxsize);
void	*Hunk_Alloc (int size);
int		Hunk_End (void);
void	Hunk_Free (void *base);

void	Mod_FreeAll (void);
void	Mod_Free (model_t *mod);
"""
