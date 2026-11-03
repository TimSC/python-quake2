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
import numpy as np
from enum import Enum
from qcommon import qfiles
"""

d*_t structures are on-disk representations
m*_t structures are in-memory

*/

/*
==============================================================================

BRUSH MODELS

==============================================================================
*/


//
// in memory representation
//
// !!! if this is changed, it must be changed in asm_draw.h too !!!
typedef struct
{
	vec3_t		position;
} mvertex_t;

typedef struct
{
	vec3_t		mins, maxs;
	vec3_t		origin;		// for sounds or lights
	float		radius;
	int			headnode;
	int			visleafs;		// not including the solid leaf 0
	int			firstface, numfaces;
} mmodel_t;

"""
# SIDE_* constants
SIDE_FRONT = 0
SIDE_BACK = 1
SIDE_ON = 2

# surface flags
SURF_PLANEBACK = 2
SURF_DRAWSKY = 4
SURF_DRAWTURB = 0x10
SURF_DRAWBACKGROUND = 0x40
SURF_UNDERWATER = 0x80

"""
// !!! if this is changed, it must be changed in asm_draw.h too !!!
typedef struct
{
	unsigned short	v[2];
	unsigned int	cachededgeoffset;
} medge_t;
"""
class mtexinfo_t(object):

	def __init__(self):

		self.vecs = np.zeros((2, 4), dtype=np.float32) # float [2][4]
		self.flags = 0 #int
		self.numframes = None # int
		self.next = None # struct mtexinfo_s *, animation chain
		self.image = None # image_t *

"""
#define	VERTEXSIZE	7

typedef struct glpoly_s
{
	struct	glpoly_s	*next;
	struct	glpoly_s	*chain;
	int		numverts;
	int		flags;			// for SURF_UNDERWATER (not needed anymore?)
	float	verts[4][VERTEXSIZE];	// variable sized (xyz s1t1 s2t2)
} glpoly_t;

typedef struct msurface_s
{
	int			visframe;		// should be drawn when node is crossed

	cplane_t	*plane;
	int			flags;

	int			firstedge;	// look up in model->surfedges[], negative numbers
	int			numedges;	// are backwards edges
	
	short		texturemins[2];
	short		extents[2];

	int			light_s, light_t;	// gl lightmap coordinates
	int			dlight_s, dlight_t; // gl lightmap coordinates for dynamic lightmaps

	glpoly_t	*polys;				// multiple if warped
	struct	msurface_s	*texturechain;
	struct  msurface_s	*lightmapchain;

	mtexinfo_t	*texinfo;
	
// lighting info
	int			dlightframe;
	int			dlightbits;

	int			lightmaptexturenum;
	byte		styles[MAXLIGHTMAPS];
	float		cached_light[MAXLIGHTMAPS];	// values currently used in lightmap
	byte		*samples;		// [numstyles*surfsize]
} msurface_t;

typedef struct mnode_s
{
// common with leaf
	int			contents;		// -1, to differentiate from leafs
	int			visframe;		// node needs to be traversed if current
	
	float		minmaxs[6];		// for bounding box culling

	struct mnode_s	*parent;

// node specific
	cplane_t	*plane;
	struct mnode_s	*children[2];	

	unsigned short		firstsurface;
	unsigned short		numsurfaces;
} mnode_t;



typedef struct mleaf_s
{
// common with node
	int			contents;		// wil be a negative contents number
	int			visframe;		// node needs to be traversed if current

	float		minmaxs[6];		// for bounding box culling

	struct mnode_s	*parent;

// leaf specific
	int			cluster;
	int			area;

	msurface_t	**firstmarksurface;
	int			nummarksurfaces;
} mleaf_t;


//===================================================================

//
// Whole model
//
"""

class modtype_t(Enum):
	mod_bad = 0
	mod_brush = 1
	mod_sprite = 2
	mod_alias = 3

class model_t(object):

	def __init__(self):
		self.reset()

	def reset(self):

		self.name = None
		self.registration_sequence = 0
		self.type = modtype_t.mod_bad
		self.numframes = 0
		self.flags = 0

		self.mins = np.zeros((3,), dtype=np.float32)
		self.maxs = np.zeros((3,), dtype=np.float32)
		self.radius = 0.0

		self.clipbox = False
		self.clipmins = np.zeros((3,), dtype=np.float32)
		self.clipmaxs = np.zeros((3,), dtype=np.float32)

		self.firstmodelsurface = 0
		self.nummodelsurfaces = 0
		self.lightmap = 0

		self.numsubmodels = 0
		self.submodels = []

		self.numplanes = 0
		self.planes = []

		self.numleafs = 0
		self.leafs = []

		self.numvertexes = 0
		self.vertexes = None

		self.numedges = 0
		self.edges = None

		self.numnodes = 0
		self.firstnode = 0
		self.nodes = []

		self.numtexinfo = 0
		self.texinfo = []

		self.numsurfaces = 0
		self.surfaces = []

		self.numsurfedges = 0
		self.surfedges = None

		self.nummarksurfaces = 0
		self.marksurfaces = []

		self.vis = None

		self.lightdata = None

		self.skins = [None] * qfiles.MAX_MD2SKINS

		self.extradatasize = 0
		self.extradata = None

"""
//============================================================================

void	Mod_Init (void);
void	Mod_ClearAll (void);
model_t *Mod_ForName (char *name, qboolean crash);
mleaf_t *Mod_PointInLeaf (float *p, model_t *model);
byte	*Mod_ClusterPVS (int cluster, model_t *model);

void	Mod_Modellist_f (void);

void	*Hunk_Begin (int maxsize);
void	*Hunk_Alloc (int size);
int		Hunk_End (void);
void	Hunk_Free (void *base);

void	Mod_FreeAll (void);
void	Mod_Free (model_t *mod);
"""

VERTEXSIZE = 7


class glpoly_t(object):

	def __init__(self):
		# struct glpoly_s *next, *chain; are replaced by lists of polys
		self.numverts = 0
		self.flags = 0
		self.verts = np.zeros((4, VERTEXSIZE), dtype=np.float32)


class msurface_t(object):

	def __init__(self):
		self.visframe = 0
		self.plane = None
		self.flags = 0
		self.firstedge = 0
		self.numedges = 0
		self.texturemins = [0, 0]
		self.extents = [0, 0]
		self.light_s = 0
		self.light_t = 0
		self.dlight_s = 0
		self.dlight_t = 0
		self.polys = [] # glpoly_t list, multiple if warped
		# struct msurface_s *texturechain, *lightmapchain; are replaced by the
		# image_t.texturechain, gl_lms.lightmap_surfaces and r_alpha_surfaces lists
		self.texinfo = None
		self.dlightframe = 0
		self.dlightbits = 0
		self.lightmaptexturenum = 0
		self.styles = [0] * qfiles.MAXLIGHTMAPS
		self.cached_light = [0.0] * qfiles.MAXLIGHTMAPS
		self.samples = None


class mnode_t(object):

	def __init__(self):
		self.contents = -1
		self.visframe = 0
		self.minmaxs = [0.0] * 6
		self.parent = None
		self.plane = None
		self.children = [None, None]
		self.firstsurface = 0
		self.numsurfaces = 0


class mleaf_t(object):

	def __init__(self):
		self.contents = 0
		self.visframe = 0
		self.minmaxs = [0.0] * 6
		self.parent = None
		self.cluster = -1
		self.area = 0
		self.firstmarksurface = []
		self.nummarksurfaces = 0


class mmodel_t(object):

	def __init__(self):
		self.mins = np.zeros((3,), dtype=np.float32)
		self.maxs = np.zeros((3,), dtype=np.float32)
		self.origin = np.zeros((3,), dtype=np.float32)
		self.radius = 0.0
		self.headnode = 0
		self.visleafs = 0
		self.firstface = 0
		self.numfaces = 0
