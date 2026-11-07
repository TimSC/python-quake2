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
 * Header shared between different refreshers (but not with client)
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
from enum import Enum
from client.vid.header import ref as ref_h
from common.header import shared


# skins will be outline flood filled and mip mapped
# pics and sprites with alpha will be outline flood filled
# pic won't be mip mapped
#
# model skin
# sprite frame
# wall texture
# pic
class imagetype_t(Enum):
	it_skin = 0
	it_sprite = 1
	it_wall = 2
	it_pic = 3
	it_sky = 4


class modtype_t(Enum):
	mod_bad = 0
	mod_brush = 1
	mod_sprite = 2
	mod_alias = 3


MAX_LBM_HEIGHT = 480

# enum SIDE_FRONT = 0, SIDE_BACK = 1, SIDE_ON = 2
SIDE_FRONT = 0
SIDE_BACK = 1
SIDE_ON = 2

# FIXME: differentiate from texinfo SURF_ flags
SURF_PLANEBACK = 0x02
SURF_DRAWSKY = 0x04 # sky brush face
SURF_DRAWTURB = 0x10
SURF_DRAWBACKGROUND = 0x40
SURF_UNDERWATER = 0x80


# in memory representation
class mvertex_t(object):

	def __init__(self):

		self.position = np.zeros((3,), dtype=np.float32) #vec3_t


class medge_t(object):

	def __init__(self):

		self.v = [0, 0] #unsigned short [2]
		self.cachededgeoffset = 0 #unsigned int


class mtexinfo_t(object):

	def __init__(self):

		self.vecs = np.zeros((2, 4), dtype=np.float32) #float [2][4]
		self.flags = 0 #int
		self.numframes = None # int
		self.next = None #struct mtexinfo_s *, animation chain
		self.image = None #struct image_s *


CONTENTS_NODE = -1

class mnode_t(object):

	def __init__(self):

		self.contents = -1 #int, CONTENTS_NODE, to differentiate from leafs
		self.visframe = 0 #int, node needs to be traversed if current
		self.minmaxs = [0.0] * 6 #float [6], for bounding box culling
		self.parent = None #struct mnode_s *
		self.plane = None #cplane_t *
		self.children = [None, None] #struct mnode_s * [2]
		self.firstsurface = 0 #unsigned short
		self.numsurfaces = 0 #unsigned short


class mleaf_t(object):

	def __init__(self):

		self.contents = 0 #int, CONTENTS_NODE, to differentiate from leafs
		self.visframe = 0 #int, node needs to be traversed if current
		self.minmaxs = [0.0] * 6 #float [6], for bounding box culling
		self.parent = None #struct mnode_s *
		self.cluster = 0 #int
		self.area = 0 #int
		self.firstmarksurface = [] #struct msurface_s **
		self.nummarksurfaces = 0 #unsigned int
		self.key = 0 #int, BSP sequence number for leaf's contents


# screen size info
r_newrefdef = ref_h.refdef_t()
vid = None #viddef_t, set by the platform layer


DLIGHT_CUTOFF = 64
