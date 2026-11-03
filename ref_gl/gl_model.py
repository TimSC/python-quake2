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
import math
import struct
import numpy as np
from ref_gl import gl_rmain, gl_model_h, gl_image, gl_rsurf, gl_warp
from qcommon import qfiles
from game import q_shared
"""
// models.c -- model loading and caching

#include "gl_local.h"

"""
loadmodel = None #model_t	*
modfilelen = None #int
"""
void Mod_LoadSpriteModel (model_t *mod, void *buffer);
void Mod_LoadBrushModel (model_t *mod, void *buffer);
void Mod_LoadAliasModel (model_t *mod, void *buffer);
model_t *Mod_LoadModel (model_t *mod, qboolean crash);
"""
mod_novis = None# byte[MAX_MAP_LEAFS/8];

MAX_MOD_KNOWN	= 512
mod_known = [] #model_t[MAX_MOD_KNOWN]
for i in range(MAX_MOD_KNOWN):
	mod_known.append(gl_model_h.model_t())
mod_numknown = 0 #int
"""
// the inline * models from the current map are kept seperate
model_t	mod_inline[MAX_MOD_KNOWN];
"""
mod_inline = [gl_model_h.model_t() for _ in range(MAX_MOD_KNOWN)]
currentmodel = None
registration_sequence = 0 #int		

# ===================
# Mod_PointInLeaf
# ===================
def Mod_PointInLeaf(p, model):
	"""Return the leaf containing point `p` inside `model`."""

	if model is None or not model.nodes:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Mod_PointInLeaf: bad model")

	node = model.nodes[0] if model.nodes else None
	while node is not None:
		if node.contents != -1:
			return node
		plane = node.plane
		if plane is None:
			break
		d = q_shared.DotProduct(p, plane.normal) - plane.dist
		node = node.children[0] if d > 0 else node.children[1]

	return None


# ===================
# Mod_DecompressVis
# ===================
def Mod_DecompressVis(data, model):

	if not model or not model.vis:
		return mod_novis

	row = (model.vis.numclusters + 7) >> 3
	if row <= 0:
		return bytearray()

	decompressed = bytearray(row)
	if not data:
		for i in range(row):
			decompressed[i] = 0xff
		return decompressed

	out_pos = 0
	i = 0
	data_view = memoryview(data)
	while out_pos < row and i < len(data_view):
		value = data_view[i]
		if value:
			decompressed[out_pos] = value
			out_pos += 1
			i += 1
			continue

		if i + 1 >= len(data_view):
			break
		count = data_view[i + 1]
		i += 2
		for _ in range(count):
			if out_pos >= row:
				break
			decompressed[out_pos] = 0
			out_pos += 1

	while out_pos < row:
		decompressed[out_pos] = 0
		out_pos += 1

	return decompressed

# ==================
# Mod_ClusterPVS
# ==================
def Mod_ClusterPVS(cluster, model):

	if cluster is None or cluster == -1 or not model or not model.vis:
		return mod_novis

	cluster = int(cluster)
	offset = int(model.vis.bitofs[cluster, qfiles.DVIS_PVS])
	data = model.vis.data
	if offset < 0 or data is None or len(data) == 0:
		return mod_novis

	return Mod_DecompressVis(data[offset:], model)



"""
# =================
# Mod_Modellist_f
# =================
"""
def Mod_Modellist_f():

	total = 0
	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL,"Loaded models:\n")
	for mod in mod_known[:mod_numknown]:
		if not mod.name:
			continue
		gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "%8i : %s\n", mod.extradatasize, mod.name)
		total += mod.extradatasize
	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "Total resident: %i\n", total)

"""
# =================
# Mod_Init
# =================
"""
def Mod_Init ():
	global mod_novis

	mod_novis = bytearray([0xff]*(qfiles.MAX_MAP_LEAFS//8))


"""
==================
Mod_ForName

Loads in a model for the given name
==================
"""
def Mod_ForName (name, crash)->gl_model_h.model_t: #char *, qboolean

	global loadmodel, modfilelen, mod_numknown
	"""
	model_t	*mod;
	unsigned *buf;
	int		i;
	"""
	
	if name is None or len(name) == 0:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Mod_ForName: NULL name");

	#
	# inline models are grabbed only from worldmodel
	#
	if name[0] == '*':

		i = int(name[1:])
		if i < 1 or gl_rmain.r_worldmodel is None or i >= gl_rmain.r_worldmodel.numsubmodels:
			gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "bad inline model number")
		return mod_inline[i]


	#
	# search the currently loaded models
	#
	for i in range(mod_numknown):
		mod = mod_known[i]
	
		if mod.name is None:
			continue
		if mod.name == name:
			return mod
	
	
	#
	# find a free model slot spot
	#
	found = False
	mod = None
	for i in range(mod_numknown):
	
		mod = mod_known[i]

		if mod.name is None:
			found = True
			break	# free spot
	
	if not found:
		# assign next mod
		if mod_numknown == MAX_MOD_KNOWN:
			gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "mod_numknown == MAX_MOD_KNOWN")
		mod = mod_known[mod_numknown]
		mod_numknown+=1
	
	mod.name = name
	
	#
	# load the file
	#
	modfilelen, buf = gl_rmain.ri.FS_LoadFile (mod.name)
	if buf is None:
	
		if crash:
			gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Mod_NumForName: {} not found".format(mod.name))
		mod.name = None
		return None
	
	loadmodel = mod

	#
	# fill it in
	#


	# call the apropriate loader

	val = q_shared.LittleLong(buf[:4])

	if val == qfiles.IDALIASHEADER:
		#loadmodel.extradata = Hunk_Begin (0x200000)
		Mod_LoadAliasModel (mod, buf)
		
	elif val == qfiles.IDSPRITEHEADER:
		#loadmodel.extradata = Hunk_Begin (0x10000)
		Mod_LoadSpriteModel (mod, buf)
	
	elif val == qfiles.IDBSPHEADER:
		#loadmodel.extradata = Hunk_Begin (0x1000000)
		Mod_LoadBrushModel (mod, buf)

	else:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP,"Mod_NumForName: unknown fileid for {}".format(mod.name))

	#loadmodel.extradatasize = Hunk_End ()

	#ri.FS_FreeFile (buf)

	return mod

"""
===============================================================================

						BRUSHMODEL LOADING

===============================================================================
"""
mod_base = None #byte *


"""
=================
Mod_LoadLighting
=================
"""
def Mod_LoadLighting (l: qfiles.lump_t):

	if not l.filelen:
	
		loadmodel.lightdata = None
		return
	
	in_offset = l.fileofs
	in_offset2 = in_offset + l.filelen

	loadmodel.lightdata = mod_base[in_offset:in_offset2]


"""
=================
Mod_LoadVisibility
=================
"""
def Mod_LoadVisibility(l: qfiles.lump_t):

	if not l.filelen:
		loadmodel.vis = None
		return

	in_offset = l.fileofs
	in_offset2 = in_offset + l.filelen
	buffer = mod_base[in_offset:in_offset2]

	vis = qfiles.dvis_t()
	vis.load(buffer)
	loadmodel.vis = vis


"""
=================
Mod_LoadVertexes
=================
"""
def Mod_LoadVertexes (l): #qfiles.lump_t *

	global mod_base, loadmodel
	print ("Mod_LoadVertexes", l)
	"""
	dvertex_t	*in;
	mvertex_t	*out;
	int			i, count;
	"""

	#in = (void *)(mod_base + l->fileofs);
	if l.filelen % qfiles.dvertex_t.packed_size():
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))
	count = l.filelen // qfiles.dvertex_t.packed_size()
	#out = Hunk_Alloc ( count*sizeof(*out))

	loadmodel.vertexes = np.zeros((count, 3), dtype=np.float32)
	loadmodel.numvertexes = count
	in_obj = qfiles.dvertex_t()
	out = loadmodel.vertexes

	for i in range(count):
	
		in_offset = l.fileofs + i * qfiles.dvertex_t.packed_size()
		in_offset2 = in_offset + qfiles.dvertex_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

		out[i, 0] = in_obj.point[0]
		out[i, 1] = in_obj.point[1]
		out[i, 2] = in_obj.point[2]

"""
=================
RadiusFromBounds
=================
"""
def RadiusFromBounds(mins, maxs):

	mins_arr = np.abs(np.array(mins))
	maxs_arr = np.abs(np.array(maxs))
	corner = np.maximum(mins_arr, maxs_arr)

	return float(np.linalg.norm(corner))


"""
=================
Mod_LoadSubmodels
=================
"""
def Mod_LoadSubmodels(l: qfiles.lump_t):

	if l.filelen % qfiles.dmodel_t.packed_size():
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // qfiles.dmodel_t.packed_size()
	loadmodel.submodels = []
	loadmodel.numsubmodels = count
	in_obj = qfiles.dmodel_t()

	for i in range(count):

		in_offset = l.fileofs + i * qfiles.dmodel_t.packed_size()
		in_offset2 = in_offset + qfiles.dmodel_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

		out = gl_model_h.mmodel_t()
		out.mins = in_obj.mins - 1.0
		out.maxs = in_obj.maxs + 1.0
		out.origin = in_obj.origin.copy()
		out.radius = RadiusFromBounds(out.mins, out.maxs)
		out.headnode = in_obj.headnode
		out.firstface = in_obj.firstface
		out.numfaces = in_obj.numfaces

		loadmodel.submodels.append(out)

"""
=================
Mod_LoadEdges
=================
"""
def Mod_LoadEdges (l: qfiles.lump_t):

	print ("Mod_LoadEdges", l)
	"""
	dedge_t *in;
	medge_t *out;
	int 	i, count;
	"""

	#in = (void *)(mod_base + l->fileofs);
	if l.filelen % qfiles.dedge_t.packed_size():
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))
	count = l.filelen // qfiles.dedge_t.packed_size()
	out = np.zeros((count, 2), dtype=np.uint16)

	loadmodel.edges = out
	loadmodel.numedges = count
	in_obj = qfiles.dedge_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * qfiles.dedge_t.packed_size()
		in_offset2 = in_offset + qfiles.dedge_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

		out[i, 0] = in_obj.v[0]
		out[i, 1] = in_obj.v[1]
	


"""
=================
Mod_LoadTexinfo
=================
"""
def Mod_LoadTexinfo (l: qfiles.lump_t):

	print ("Mod_LoadTexinfo", l)
	"""
	texinfo_t *in;
	mtexinfo_t *out, *step;
	int 	i, j, count;
	char	name[MAX_QPATH];
	int		next;
	"""

	#in = (void *)(mod_base + l->fileofs);
	if l.filelen % qfiles.texinfo_t.packed_size():
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))
	count = l.filelen // qfiles.texinfo_t.packed_size()
	out = []

	loadmodel.texinfo = out
	loadmodel.numtexinfo = count
	in_obj = qfiles.texinfo_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * qfiles.texinfo_t.packed_size()
		in_offset2 = in_offset + qfiles.texinfo_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

		out_obj = gl_model_h.mtexinfo_t()

		out_obj.vecs = in_obj.vecs.copy()

		out_obj.flags = in_obj.flags
		next = in_obj.nexttexinfo

		if next > 0:
			out_obj.next = next
		else:
		    out_obj.next = None
		name = "textures/{}.wal".format(in_obj.texture)

		out_obj.image = gl_image.GL_FindImage (name, gl_image.imagetype_t.it_wall)
		if out_obj.image is None:
		
			gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "Couldn't load {}\n".format(name))
			out_obj.image = gl_rmain.r_notexture
		
		out.append(out_obj)

	
	# out->next = loadmodel->texinfo + next; the index is turned into a reference
	# once all the texinfos exist
	for i in range(count):
		if loadmodel.texinfo[i].next is not None:
			loadmodel.texinfo[i].next = loadmodel.texinfo[loadmodel.texinfo[i].next]

	# count animation frames
	for i in range(count):

		out = loadmodel.texinfo[i]
		out.numframes = 1
		step = out.next
		while step is not None and step is not out:
			out.numframes+=1
			step = step.next


"""
================
CalcSurfaceExtents

Fills in s->texturemins[] and s->extents[]
================
"""
def CalcSurfaceExtents(s: gl_model_h.msurface_t):

	tex = s.texinfo
	if tex is None or s.numedges <= 0:
		return

	mins = [float("inf"), float("inf")]
	maxs = [float("-inf"), float("-inf")]

	for idx in range(s.numedges):
		surfedge_index = s.firstedge + idx
		if surfedge_index >= len(loadmodel.surfedges):
			continue

		e = int(loadmodel.surfedges[surfedge_index])
		if e >= 0:
			vertex_index = int(loadmodel.edges[e, 0])
		else:
			vertex_index = int(loadmodel.edges[-e, 1])

		vertex = loadmodel.vertexes[vertex_index]
		for j in range(2):
			val = (
				vertex[0] * tex.vecs[j, 0]
				+ vertex[1] * tex.vecs[j, 1]
				+ vertex[2] * tex.vecs[j, 2]
				+ tex.vecs[j, 3]
			)

			if val < mins[j]:
				mins[j] = val
			if val > maxs[j]:
				maxs[j] = val

	for i in range(2):
		bmin = math.floor(mins[i] / 16.0)
		bmax = math.ceil(maxs[i] / 16.0)
		s.texturemins[i] = int(bmin * 16)
		s.extents[i] = int((bmax - bmin) * 16)


"""
=================
Mod_LoadFaces
=================
"""
def Mod_LoadFaces(l: qfiles.lump_t):

	face_size = 20
	if l.filelen % face_size:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // face_size
	loadmodel.surfaces = []
	loadmodel.numsurfaces = count
	global currentmodel
	currentmodel = loadmodel
	gl_rmain.currentmodel = loadmodel # GL_BuildPolygonFromSurface reads the renderer global

	gl_rsurf.GL_BeginBuildingLightmaps (loadmodel)

	for face_num in range(count):

		in_offset = l.fileofs + face_num * face_size
		in_offset2 = in_offset + face_size
		in_data = mod_base[in_offset:in_offset2]

		planenum = q_shared.LittleShort (in_data[0:2])
		side = q_shared.LittleShort (in_data[2:4])
		firstedge = q_shared.LittleLong (in_data[4:8])
		numedges = q_shared.LittleShort (in_data[8:10])
		texinfo_index = q_shared.LittleShort (in_data[10:12])
		styles = [in_data[12], in_data[13], in_data[14], in_data[15]]
		lightofs = q_shared.LittleLong (in_data[16:20])

		surf = gl_model_h.msurface_t()
		surf.firstedge = firstedge
		surf.numedges = numedges
		surf.flags = 0

		if side:
			surf.flags |= q_shared.SURF_PLANEBACK

		if 0 <= planenum < loadmodel.numplanes:
			surf.plane = loadmodel.planes[planenum]

		if texinfo_index < 0 or texinfo_index >= loadmodel.numtexinfo:
			gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: bad texinfo number")
		surf.texinfo = loadmodel.texinfo[texinfo_index]

		CalcSurfaceExtents(surf)

		surf.styles = styles
		if lightofs == -1 or loadmodel.lightdata is None:
			surf.samples = None
		else:
			surf.samples = loadmodel.lightdata[lightofs:]

		# set the drawing flags

		if surf.texinfo.flags & q_shared.SURF_WARP:

			surf.flags |= gl_model_h.SURF_DRAWTURB
			for i in range(2):

				surf.extents[i] = 16384
				surf.texturemins[i] = -8192

			gl_warp.GL_SubdivideSurface (surf)	# cut up polygon for warps

		# create lightmaps and polygons
		if not (surf.texinfo.flags & (q_shared.SURF_SKY|q_shared.SURF_TRANS33|q_shared.SURF_TRANS66|q_shared.SURF_WARP)):
			gl_rsurf.GL_CreateSurfaceLightmap (surf)

		if not (surf.texinfo.flags & q_shared.SURF_WARP):
			gl_rsurf.GL_BuildPolygonFromSurface (surf)

		loadmodel.surfaces.append(surf)

	gl_rsurf.GL_EndBuildingLightmaps ()


"""
=================
Mod_SetParent
=================
"""
def Mod_SetParent(node: gl_model_h.mnode_t, parent: gl_model_h.mnode_t):

	if node is None:
		return

	node.parent = parent
	if node.contents != -1:
		return

	for child in node.children:
		if child is not None:
			Mod_SetParent(child, node)


"""
=================
Mod_LoadNodes
=================
"""
def Mod_LoadNodes(l: qfiles.lump_t):

	node_size = qfiles.dnode_t.packed_size()
	if l.filelen % node_size:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // node_size
	loadmodel.nodes = []
	loadmodel.numnodes = count
	in_obj = qfiles.dnode_t()
	child_indices = []

	for i in range(count):

		in_offset = l.fileofs + i * node_size
		in_offset2 = in_offset + node_size
		in_obj.load(mod_base[in_offset:in_offset2])

		node = gl_model_h.mnode_t()
		node.minmaxs[:3] = in_obj.mins.tolist()
		node.minmaxs[3:] = in_obj.maxs.tolist()
		node.contents = -1
		node.firstsurface = in_obj.firstface
		node.numsurfaces = in_obj.numfaces
		if 0 <= in_obj.planenum < loadmodel.numplanes:
			node.plane = loadmodel.planes[in_obj.planenum]

		loadmodel.nodes.append(node)
		child_indices.append((int(in_obj.children[0]), int(in_obj.children[1])))

	for node, (child0, child1) in zip(loadmodel.nodes, child_indices):
		for idx, child_value in enumerate((child0, child1)):
			if child_value >= 0:
				node.children[idx] = loadmodel.nodes[child_value]
			else:
				leaf_index = -1 - child_value
				if 0 <= leaf_index < len(loadmodel.leafs):
					node.children[idx] = loadmodel.leafs[leaf_index]

	if loadmodel.nodes:
		Mod_SetParent(loadmodel.nodes[0], None)


"""
=================
Mod_LoadLeafs
=================
"""
def Mod_LoadLeafs(l: qfiles.lump_t):

	leaf_size = qfiles.dleaf_t.packed_size()
	if l.filelen % leaf_size:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // leaf_size
	loadmodel.leafs = []
	loadmodel.numleafs = count
	in_obj = qfiles.dleaf_t()

	for i in range(count):

		in_offset = l.fileofs + i * leaf_size
		in_offset2 = in_offset + leaf_size
		in_obj.load(mod_base[in_offset:in_offset2])

		leaf = gl_model_h.mleaf_t()
		for j in range(3):
			leaf.minmaxs[j] = in_obj.mins[j]
			leaf.minmaxs[3 + j] = in_obj.maxs[j]

		leaf.contents = in_obj.contents
		leaf.cluster = in_obj.cluster
		leaf.area = in_obj.area

		start = in_obj.firstleafface
		end = start + in_obj.numleaffaces
		if loadmodel.marksurfaces:
			leaf.firstmarksurface = loadmodel.marksurfaces[start:end]
		leaf.nummarksurfaces = in_obj.numleaffaces

		loadmodel.leafs.append(leaf)

"""
=================
Mod_LoadMarksurfaces
=================
"""
def Mod_LoadMarksurfaces(l: qfiles.lump_t):

	if l.filelen % 2:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // 2
	loadmodel.marksurfaces = []
	loadmodel.nummarksurfaces = count

	for i in range(count):
		in_offset = l.fileofs + i * 2
		index = q_shared.LittleShort(mod_base[in_offset:in_offset+2])
		if index < 0 or index >= loadmodel.numsurfaces:
			gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Mod_ParseMarksurfaces: bad surface number")
		loadmodel.marksurfaces.append(loadmodel.surfaces[index])

"""
=================
Mod_LoadSurfedges
=================
"""
def Mod_LoadSurfedges (l: qfiles.lump_t):
	
	print ("Mod_LoadSurfedges", l)	
	#int		i, count;
	#int		*in, *out;
	
	#in = (void *)(mod_base + l->fileofs);
	if l.filelen % 4:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))
	count = l.filelen // 4
	if count < 1 or count >= qfiles.MAX_MAP_SURFEDGES:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: bad surfedges count in {}: {}".format(
		loadmodel.name, count))

	out = np.zeros((count,), dtype=np.int32)

	loadmodel.surfedges = out
	loadmodel.numsurfedges = count

	for i in range(count):
		in_offset = l.fileofs + i * 4
		in_offset2 = in_offset + 4

		out[i] = q_shared.LittleSLong (mod_base[in_offset: in_offset2])



"""
=================
Mod_LoadPlanes
=================
"""
def Mod_LoadPlanes (l: qfiles.lump_t):

	print ("Mod_LoadPlanes", l)
	"""
	int			i, j;
	cplane_t	*out;
	dplane_t 	*in;
	int			count;
	int			bits;
	"""	

	#in = (void *)(mod_base + l->fileofs);
	if l.filelen % qfiles.dplane_t.packed_size():
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))
	count = l.filelen // qfiles.dplane_t.packed_size()
	out = []
	
	loadmodel.planes = out
	loadmodel.numplanes = count
	in_obj = qfiles.dplane_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * qfiles.dplane_t.packed_size()
		in_offset2 = in_offset + qfiles.dplane_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

		out_obj = q_shared.cplane_t()

		bits = 0
		for j in range(3):
		
			out_obj.normal[j] = in_obj.normal[j]
			if out_obj.normal[j] < 0.0:
				bits |= (1<<j)
		
		out_obj.dist = in_obj.dist
		out_obj.type = in_obj.type
		out_obj.signbits = bits
	
		out.append(out_obj)


"""
=================
Mod_LoadBrushModel
=================
"""
def Mod_LoadBrushModel (mod, buff): #model_t *, void *

	global loadmodel, mod_base
	print ("Mod_LoadBrushModel")
	"""
	int			i;
	dheader_t	*header;
	mmodel_t 	*bm;
	"""
	
	loadmodel.type = gl_model_h.modtype_t.mod_brush
	if id(loadmodel) != id(mod_known[0]):
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Loaded a brush model after the world")

	header = qfiles.dheader_t()
	header.parse(buff)

	if header.version != qfiles.BSPVERSION:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Mod_LoadBrushModel: {} has wrong version number ({} should be {})".format(mod.name, i, qfiles.BSPVERSION))

	mod_base = buff

	# load into heap
	
	Mod_LoadVertexes (header.lumps[qfiles.LUMP_VERTEXES])
	Mod_LoadEdges (header.lumps[qfiles.LUMP_EDGES])
	Mod_LoadSurfedges (header.lumps[qfiles.LUMP_SURFEDGES])
	Mod_LoadLighting (header.lumps[qfiles.LUMP_LIGHTING])
	Mod_LoadPlanes (header.lumps[qfiles.LUMP_PLANES])
	Mod_LoadTexinfo (header.lumps[qfiles.LUMP_TEXINFO])
	Mod_LoadFaces (header.lumps[qfiles.LUMP_FACES])
	Mod_LoadMarksurfaces (header.lumps[qfiles.LUMP_LEAFFACES])
	Mod_LoadVisibility (header.lumps[qfiles.LUMP_VISIBILITY])
	Mod_LoadLeafs (header.lumps[qfiles.LUMP_LEAFS])
	Mod_LoadNodes (header.lumps[qfiles.LUMP_NODES])
	Mod_LoadSubmodels (header.lumps[qfiles.LUMP_MODELS])
	loadmodel.numframes = 2		# regular and alternate animation


	
#
# set up the submodels
#
	for i in range(loadmodel.numsubmodels):

		bm = loadmodel.submodels[i]
		starmod = gl_model_h.model_t()
		starmod.__dict__.update(loadmodel.__dict__)

		starmod.firstmodelsurface = bm.firstface
		starmod.nummodelsurfaces = bm.numfaces
		starmod.firstnode = bm.headnode
		if starmod.firstnode >= loadmodel.numnodes:
			gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "Inline model {} has bad firstnode".format(i))

		starmod.maxs = bm.maxs.copy()
		starmod.mins = bm.mins.copy()
		starmod.radius = bm.radius

		if i == 0:
			loadmodel.__dict__.update(starmod.__dict__)

		starmod.numleafs = bm.visleafs
		mod_inline[i] = starmod

# ==============================================================================
# ALIAS MODELS
# ==============================================================================
def Mod_LoadAliasModel (mod, buff): #model_t *, void *

	print ("Mod_LoadAliasModel")

	header = qfiles.dmdl_t()
	header.load(buff)

	if header.version != qfiles.ALIAS_VERSION:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "{} has wrong version number ({} should be {})".format(mod.name, header.version, qfiles.ALIAS_VERSION))

	if header.skinheight > qfiles.MAX_LBM_HEIGHT:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "model {} has a skin taller than {}".format(mod.name, qfiles.MAX_LBM_HEIGHT))

	if header.num_xyz <= 0 or header.num_xyz > qfiles.MAX_VERTS:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "model {} has invalid vertex count".format(mod.name))

	if header.num_st <= 0:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "model {} has no st vertices".format(mod.name))

	if header.num_tris <= 0:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "model {} has no triangles".format(mod.name))

	if header.num_frames <= 0:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "model {} has no frames".format(mod.name))

	min_frame_size = 40 + header.num_xyz * 4
	if header.framesize < min_frame_size:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "model {} has invalid frame size".format(mod.name))

	skin_count = min(header.num_skins, qfiles.MAX_MD2SKINS)
	for i in range(skin_count):
		offset = header.ofs_skins + i * qfiles.MAX_SKINNAME
		name_bytes = buff[offset:offset + qfiles.MAX_SKINNAME]
		name = name_bytes.split(b'\x00', 1)[0].decode("ascii", "ignore")
		if not name:
			continue
		mod.skins[i] = gl_image.GL_FindImage (name, gl_image.imagetype_t.it_skin)

	stverts = []
	st_offset = header.ofs_st
	for i in range(header.num_st):
		entry_offset = st_offset + i * 4
		s, t = struct.unpack_from("<hh", buff, entry_offset)
		stverts.append((s, t))

	triangles = []
	tri_offset = header.ofs_tris
	for i in range(header.num_tris):
		entry_offset = tri_offset + i * 12
		index_xyz = struct.unpack_from("<3h", buff, entry_offset)
		index_st = struct.unpack_from("<3h", buff, entry_offset + 6)
		triangles.append({
			"index_xyz": index_xyz,
			"index_st": index_st,
		})

	#
	# load the frames
	#
	frames = [] # daliasframe_t[num_frames]
	frame_offset = header.ofs_frames
	for _ in range(header.num_frames):
		frame_data = buff[frame_offset:frame_offset + header.framesize]
		frame = qfiles.daliasframe_t()
		frame.scale = np.array(struct.unpack_from("<3f", frame_data, 0), dtype=np.float32)
		frame.translate = np.array(struct.unpack_from("<3f", frame_data, 12), dtype=np.float32)
		frame.name = frame_data[24:40].split(b'\x00', 1)[0].decode("ascii", "ignore")

		# dtrivertx_t[num_xyz] as rows of v[0], v[1], v[2], lightnormalindex
		frame.verts = np.frombuffer(frame_data, dtype=np.uint8, count=header.num_xyz*4, offset=40).reshape((header.num_xyz, 4))

		frames.append(frame)
		frame_offset += header.framesize

	#
	# load the glcmds
	#
	# The C stores these as ints, with the texture coordinates being floats
	# punned into the same array. Decode them here into a plain list of
	# count, then (s float, t float, index_xyz int) per vertex, ending with 0.
	glcmds = []
	cmd_offset = header.ofs_glcmds
	cmd_end = header.ofs_glcmds + header.num_glcmds*4
	while cmd_offset < cmd_end:
		count = struct.unpack_from("<i", buff, cmd_offset)[0]
		cmd_offset += 4
		glcmds.append(count)
		if not count:
			break
		for _ in range(abs(count)):
			s, t, index_xyz = struct.unpack_from("<ffi", buff, cmd_offset)
			cmd_offset += 12
			glcmds.extend((s, t, index_xyz))

	header.stverts = stverts
	header.triangles = triangles
	header.frames = frames
	header.glcmds = glcmds

	mod.type = gl_model_h.modtype_t.mod_alias
	mod.numframes = header.num_frames
	mod.extradata = header # paliashdr

	mod.mins[0] = -32
	mod.mins[1] = -32
	mod.mins[2] = -32
	mod.maxs[0] = 32
	mod.maxs[1] = 32
	mod.maxs[2] = 32

def Mod_LoadSpriteModel (mod, buff): # model_t *, void *

	print ("Mod_LoadSpriteModel")
	sprite = qfiles.dsprite_t()
	sprite.load(buff)

	if sprite.version != qfiles.SPRITE_VERSION:
		gl_rmain.ri.Sys_Error (q_shared.ERR_DROP, "{} has wrong sprite version ({})".format(mod.name, sprite.version))

	skin_count = min(sprite.numframes, qfiles.MAX_MD2SKINS)
	for i in range(skin_count):
		frame = sprite.frames[i]
		if not frame.name:
			continue
		mod.skins[i] = gl_image.GL_FindImage (frame.name, gl_image.imagetype_t.it_sprite)

	mod.type = gl_model_h.modtype_t.mod_sprite
	mod.numframes = sprite.numframes
	mod.extradata = sprite

# @@@@@@@@@@@@@@@@@@@@@
# R_BeginRegistration
#
# Specifies the model that will be used as the world
# @@@@@@@@@@@@@@@@@@@@@
def R_BeginRegistration (model): #char *

	global registration_sequence, gl_rmain, r_viewcluster

	#char	fullname[MAX_QPATH];
	#cvar_t	*flushmap;

	registration_sequence+=1
	gl_rmain.r_oldviewcluster = -1		# force markleafs

	fullname = "maps/{}.bsp".format(model)

	# explicitly free the old map if different
	# this guarantees that mod_known[0] is the world map
	flushmap = gl_rmain.ri.Cvar_Get ("flushmap", "0", 0)
	if mod_known[0].name != fullname or flushmap.value:
		Mod_Free (mod_known[0])
	gl_rmain.r_worldmodel = Mod_ForName(fullname, True)

	r_viewcluster = -1

# @@@@@@@@@@@@@@@@@@@@@
# R_RegisterModel
# 
# @@@@@@@@@@@@@@@@@@@@@
def R_RegisterModel (name): # char * (returns struct model_s *)

	mod = Mod_ForName(name, False)
	if not mod:
		return None

	mod.registration_sequence = registration_sequence
	if mod.type == gl_model_h.modtype_t.mod_brush:
		for texinfo in mod.texinfo:
			if texinfo.image is not None:
				texinfo.image.registration_sequence = registration_sequence
	elif mod.type in (gl_model_h.modtype_t.mod_alias, gl_model_h.modtype_t.mod_sprite):
		for skin in mod.skins:
			if skin is not None:
				skin.registration_sequence = registration_sequence
	return mod

# @@@@@@@@@@@@@@@@@@@@@
# R_EndRegistration
# @@@@@@@@@@@@@@@@@@@@@
def R_EndRegistration ():

	for mod in mod_known[:mod_numknown]:
		if not mod or not mod.name:
			continue
		if mod.registration_sequence != registration_sequence:
			Mod_Free(mod)
	gl_image.GL_FreeUnusedImages()

# =============================================================================
#
# =================
# Mod_Free
# =================
def Mod_Free (mod): # model_t *

	mod.extradata = None
	mod.reset()

# =================
# Mod_FreeAll
# =================
def Mod_FreeAll():

	for mod in mod_known[:mod_numknown]:
		if mod.extradatasize:
			Mod_Free(mod)
