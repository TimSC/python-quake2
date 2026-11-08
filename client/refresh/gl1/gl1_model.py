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
import struct
import numpy as np
from client.refresh.gl1 import gl1_main, gl1_image, gl1_surf, gl1_warp, gl1_lightmap
from client.refresh.gl1.header import model
from client.refresh.files import models as files_models
from client.refresh.files import pvs as files_pvs
pass
pass
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
"""
// models.c -- model loading and caching

#include "gl_local.h"

"""
loadmodel = None #model_t	*
modfilelen = None #int
"""
model_t *Mod_LoadModel (model_t *mod, qboolean crash);
"""
mod_novis = None# byte[MAX_MAP_LEAFS/8];

MAX_MOD_KNOWN	= 512
mod_known = [] #model_t[MAX_MOD_KNOWN]
for i in range(MAX_MOD_KNOWN):
	mod_known.append(model.model_t())
mod_numknown = 0 #int
"""
// the inline * models from the current map are kept seperate
model_t	mod_inline[MAX_MOD_KNOWN];
"""
mod_inline = [model.model_t() for _ in range(MAX_MOD_KNOWN)]
currentmodel = None
registration_sequence = 0 #int		

# ==================
# Mod_ClusterPVS
# ==================
def Mod_ClusterPVS(cluster, model):

	if cluster is None or cluster == -1 or not model or not model.vis:
		return mod_novis

	cluster = int(cluster)
	offset = int(model.vis.bitofs[cluster, files_h.DVIS_PVS])
	data = model.vis.data
	if offset < 0 or data is None or len(data) == 0:
		return mod_novis

	return files_pvs.Mod_DecompressVis(data[offset:], (model.vis.numclusters + 7) >> 3)



"""
# =================
# Mod_Modellist_f
# =================
"""
def Mod_Modellist_f():

	total = 0
	gl1_main.ri.Con_Printf (shared.PRINT_ALL,"Loaded models:\n")
	for mod in mod_known[:mod_numknown]:
		if not mod.name:
			continue
		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "{:8d} : {}\n".format(mod.extradatasize, mod.name))
		total += mod.extradatasize
	gl1_main.ri.Con_Printf (shared.PRINT_ALL, "Total resident: {}\n".format(total))

"""
# =================
# Mod_Init
# =================
"""
def Mod_Init ():
	global mod_novis

	mod_novis = bytearray([0xff]*(files_h.MAX_MAP_LEAFS//8))


"""
==================
Mod_ForName

Loads in a model for the given name
==================
"""
def Mod_ForName (name, crash)->model.model_t: #char *, qboolean

	global loadmodel, modfilelen, mod_numknown
	"""
	model_t	*mod;
	unsigned *buf;
	int		i;
	"""
	
	if name is None or len(name) == 0:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "Mod_ForName: NULL name");

	#
	# inline models are grabbed only from worldmodel
	#
	if name[0] == '*':

		i = int(name[1:])
		if i < 1 or gl1_main.r_worldmodel is None or i >= gl1_main.r_worldmodel.numsubmodels:
			gl1_main.ri.Sys_Error (shared.ERR_DROP, "bad inline model number")
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
			gl1_main.ri.Sys_Error (shared.ERR_DROP, "mod_numknown == MAX_MOD_KNOWN")
		mod = mod_known[mod_numknown]
		mod_numknown+=1
	
	mod.name = name
	
	#
	# load the file
	#
	modfilelen, buf = gl1_main.ri.FS_LoadFile (mod.name)
	if buf is None:
	
		if crash:
			gl1_main.ri.Sys_Error (shared.ERR_DROP, "Mod_NumForName: {} not found".format(mod.name))
		mod.name = None
		return None
	
	loadmodel = mod

	#
	# fill it in
	#


	# call the apropriate loader

	val = shared_c.LittleLong(buf[:4])

	if val == files_h.IDALIASHEADER:
		#loadmodel.extradata = Hunk_Begin (0x200000)
		Mod_LoadAliasModel (mod, buf)
		
	elif val == files_h.IDSPRITEHEADER:
		#loadmodel.extradata = Hunk_Begin (0x10000)
		Mod_LoadSpriteModel (mod, buf)
	
	elif val == files_h.IDBSPHEADER:
		#loadmodel.extradata = Hunk_Begin (0x1000000)
		Mod_LoadBrushModel (mod, buf)

	else:
		gl1_main.ri.Sys_Error (shared.ERR_DROP,"Mod_NumForName: unknown fileid for {}".format(mod.name))

	loadmodel.extradatasize = len(buf) # Q2PORT: Hunk_End returns the hunk size, there is no hunk so the file size stands in

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
Mod_LoadSubmodels
=================
"""
def Mod_LoadSubmodels(l: files_h.lump_t):

	if l.filelen % files_h.dmodel_t.packed_size():
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // files_h.dmodel_t.packed_size()
	loadmodel.submodels = []
	loadmodel.numsubmodels = count
	in_obj = files_h.dmodel_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dmodel_t.packed_size()
		in_offset2 = in_offset + files_h.dmodel_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

		out = model.mmodel_t()
		out.mins = in_obj.mins - 1.0
		out.maxs = in_obj.maxs + 1.0
		out.origin = in_obj.origin.copy()
		out.radius = files_pvs.Mod_RadiusFromBounds(out.mins, out.maxs)
		out.headnode = in_obj.headnode
		out.firstface = in_obj.firstface
		out.numfaces = in_obj.numfaces

		loadmodel.submodels.append(out)

"""
================
CalcSurfaceExtents

Fills in s->texturemins[] and s->extents[]
================
"""
def CalcSurfaceExtents(s: model.msurface_t):

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
			vertex_index = int(loadmodel.edges[e].v[0])
		else:
			vertex_index = int(loadmodel.edges[-e].v[1])

		vertex = loadmodel.vertexes[vertex_index].position
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
def Mod_LoadFaces(l: files_h.lump_t):


	face_size = 20
	if l.filelen % face_size:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // face_size
	loadmodel.surfaces = []
	loadmodel.numsurfaces = count
	global currentmodel
	currentmodel = loadmodel
	gl1_main.currentmodel = loadmodel # GL_BuildPolygonFromSurface reads the renderer global


	gl1_lightmap.LM_BeginBuildingLightmaps (loadmodel)

	for face_num in range(count):

		in_offset = l.fileofs + face_num * face_size
		in_offset2 = in_offset + face_size
		in_data = mod_base[in_offset:in_offset2]

		planenum = shared_c.LittleShort (in_data[0:2])
		side = shared_c.LittleShort (in_data[2:4])
		firstedge = shared_c.LittleLong (in_data[4:8])
		numedges = shared_c.LittleShort (in_data[8:10])
		texinfo_index = shared_c.LittleShort (in_data[10:12])
		styles = [in_data[12], in_data[13], in_data[14], in_data[15]]
		lightofs = shared_c.LittleLong (in_data[16:20])

		surf = model.msurface_t()
		surf.firstedge = firstedge
		surf.numedges = numedges
		surf.flags = 0

		if side:
			surf.flags |= shared.SURF_PLANEBACK

		if 0 <= planenum < loadmodel.numplanes:
			surf.plane = loadmodel.planes[planenum]

		if texinfo_index < 0 or texinfo_index >= loadmodel.numtexinfo:
			gl1_main.ri.Sys_Error (shared.ERR_DROP, "MOD_LoadBmodel: bad texinfo number")
		surf.texinfo = loadmodel.texinfo[texinfo_index]

		CalcSurfaceExtents(surf)

		surf.styles = styles
		if lightofs == -1 or loadmodel.lightdata is None:
			surf.samples = None
		else:
			surf.samples = loadmodel.lightdata[lightofs:]

		# set the drawing flags

		if surf.texinfo.flags & shared.SURF_WARP:

			surf.flags |= model.SURF_DRAWTURB
			for i in range(2):

				surf.extents[i] = 16384
				surf.texturemins[i] = -8192

			gl1_warp.GL_SubdivideSurface (surf)	# cut up polygon for warps

		# create lightmaps and polygons
		if not (surf.texinfo.flags & (shared.SURF_SKY|shared.SURF_TRANS33|shared.SURF_TRANS66|shared.SURF_WARP)):
			gl1_lightmap.LM_CreateSurfaceLightmap (surf)

		if not (surf.texinfo.flags & shared.SURF_WARP):
			gl1_lightmap.LM_BuildPolygonFromSurface (loadmodel, surf)

		loadmodel.surfaces.append(surf)


	gl1_lightmap.LM_EndBuildingLightmaps ()


"""
=================
Mod_LoadLeafs
=================
"""
def Mod_LoadLeafs(l: files_h.lump_t):

	leaf_size = files_h.dleaf_t.packed_size()
	if l.filelen % leaf_size:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // leaf_size
	loadmodel.leafs = []
	loadmodel.numleafs = count
	in_obj = files_h.dleaf_t()

	for i in range(count):

		in_offset = l.fileofs + i * leaf_size
		in_offset2 = in_offset + leaf_size
		in_obj.load(mod_base[in_offset:in_offset2])

		leaf = model.mleaf_t()
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
def Mod_LoadMarksurfaces(l: files_h.lump_t):

	if l.filelen % 2:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size in {}".format(loadmodel.name))

	count = l.filelen // 2
	loadmodel.marksurfaces = []
	loadmodel.nummarksurfaces = count

	for i in range(count):
		in_offset = l.fileofs + i * 2
		index = shared_c.LittleShort(mod_base[in_offset:in_offset+2])
		if index < 0 or index >= loadmodel.numsurfaces:
			gl1_main.ri.Sys_Error (shared.ERR_DROP, "Mod_ParseMarksurfaces: bad surface number")
		loadmodel.marksurfaces.append(loadmodel.surfaces[index])

"""
=================
Mod_LoadBrushModel
=================
"""
def Mod_LoadBrushModel (mod, buff): #model_t *, void *


	global loadmodel, mod_base
	"""
	int			i;
	dheader_t	*header;
	mmodel_t 	*bm;
	"""
	
	loadmodel.type = model.modtype_t.mod_brush
	if id(loadmodel) != id(mod_known[0]):
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "Loaded a brush model after the world")

	header = files_h.dheader_t()
	header.parse(buff)

	if header.version != files_h.BSPVERSION:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "Mod_LoadBrushModel: {} has wrong version number ({} should be {})".format(mod.name, i, files_h.BSPVERSION))

	mod_base = buff

	# load the shared lumps into arrays (files/models.c), then the gl1-specific
	# faces/marksurfaces/leafs/nodes/submodels on top
	vertexes = [None]; numvertexes = [0]
	edges = [None]; numedges = [0]
	surfedges = [None]; numsurfedges = [0]
	lightdata = [None]
	planes = [None]; numplanes = [0]
	texinfo = [None]; numtexinfo = [0]
	vis = [None]
	nodes = [None]; numnodes = [0]

	files_models.Mod_LoadVertexes (loadmodel.name, vertexes, numvertexes, mod_base,
		header.lumps[files_h.LUMP_VERTEXES], 0)
	files_models.Mod_LoadEdges (loadmodel.name, edges, numedges,
		mod_base, header.lumps[files_h.LUMP_EDGES], 1)
	files_models.Mod_LoadSurfedges (loadmodel.name, surfedges, numsurfedges,
		mod_base, header.lumps[files_h.LUMP_SURFEDGES], 0)
	files_models.Mod_LoadLighting (lightdata, mod_base, header.lumps[files_h.LUMP_LIGHTING])
	files_models.Mod_LoadPlanes (loadmodel.name, planes, numplanes,
		mod_base, header.lumps[files_h.LUMP_PLANES], 0)
	files_models.Mod_LoadTexinfo (loadmodel.name, texinfo, numtexinfo,
		mod_base, header.lumps[files_h.LUMP_TEXINFO], gl1_image.R_FindImage,
		gl1_main.r_notexture, 0)

	loadmodel.vertexes = vertexes[0]
	loadmodel.numvertexes = numvertexes[0]
	loadmodel.edges = edges[0]
	loadmodel.numedges = numedges[0]
	loadmodel.surfedges = surfedges[0]
	loadmodel.numsurfedges = numsurfedges[0]
	loadmodel.lightdata = lightdata[0]
	loadmodel.planes = planes[0]
	loadmodel.numplanes = numplanes[0]
	loadmodel.texinfo = texinfo[0]
	loadmodel.numtexinfo = numtexinfo[0]
	loadmodel.vis = vis[0]

	Mod_LoadFaces (header.lumps[files_h.LUMP_FACES])
	Mod_LoadMarksurfaces (header.lumps[files_h.LUMP_LEAFFACES])
	files_models.Mod_LoadVisibility (vis, mod_base, header.lumps[files_h.LUMP_VISIBILITY])
	loadmodel.vis = vis[0]
	Mod_LoadLeafs (header.lumps[files_h.LUMP_LEAFS])
	files_models.Mod_LoadNodes (loadmodel.name, loadmodel.planes, loadmodel.numplanes,
		loadmodel.leafs, loadmodel.numleafs, nodes, numnodes, mod_base,
		header.lumps[files_h.LUMP_NODES])
	loadmodel.nodes = nodes[0]
	loadmodel.numnodes = numnodes[0]
	Mod_LoadSubmodels (header.lumps[files_h.LUMP_MODELS])
	loadmodel.numframes = 2		# regular and alternate animation


	
#
# set up the submodels
#
	for i in range(loadmodel.numsubmodels):

		bm = loadmodel.submodels[i]
		starmod = model.model_t()
		starmod.__dict__.update(loadmodel.__dict__)

		starmod.firstmodelsurface = bm.firstface
		starmod.nummodelsurfaces = bm.numfaces
		starmod.firstnode = bm.headnode
		if starmod.firstnode >= loadmodel.numnodes:
			gl1_main.ri.Sys_Error (shared.ERR_DROP, "Inline model {} has bad firstnode".format(i))

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


	header = files_h.dmdl_t()
	header.load(buff)

	if header.version != files_h.ALIAS_VERSION:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "{} has wrong version number ({} should be {})".format(mod.name, header.version, files_h.ALIAS_VERSION))

	if header.skinheight > files_h.MAX_LBM_HEIGHT:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "model {} has a skin taller than {}".format(mod.name, files_h.MAX_LBM_HEIGHT))

	if header.num_xyz <= 0 or header.num_xyz > files_h.MAX_VERTS:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "model {} has invalid vertex count".format(mod.name))

	if header.num_st <= 0:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "model {} has no st vertices".format(mod.name))

	if header.num_tris <= 0:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "model {} has no triangles".format(mod.name))

	if header.num_frames <= 0:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "model {} has no frames".format(mod.name))

	min_frame_size = 40 + header.num_xyz * 4
	if header.framesize < min_frame_size:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "model {} has invalid frame size".format(mod.name))

	skin_count = min(header.num_skins, files_h.MAX_MD2SKINS)
	for i in range(skin_count):
		offset = header.ofs_skins + i * files_h.MAX_SKINNAME
		name_bytes = buff[offset:offset + files_h.MAX_SKINNAME]
		name = name_bytes.split(b'\x00', 1)[0].decode("ascii", "ignore")
		if not name:
			continue
		mod.skins[i] = gl1_image.R_FindImage (name, gl1_image.imagetype_t.it_skin)

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
		frame = files_h.daliasframe_t()
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

	# Q2PORT: the glcmds are also unrolled into a triangle list, in the same
	# order and winding as the strips and fans GL draws from them, so that
	# GL_DrawAliasFrameLerp can draw a model with one glDrawArrays instead of
	# one GL call per vertex. Texture coordinates belong to the draw list
	# entry, not the model vertex, so the same index_xyz can repeat with a
	# different s and t.
	drawtris_st = []
	drawtris_xyz = []
	o = 0
	while o < len(glcmds):
		count = glcmds[o]
		o += 1
		if not count:
			break
		if count < 0:
			count = -count
			fan = True # GL_TRIANGLE_FAN
		else:
			fan = False # GL_TRIANGLE_STRIP
		drawverts = [glcmds[o+k*3:o+k*3+3] for k in range(count)] # s, t, index_xyz
		o += count*3
		for k in range(count-2):
			if fan:
				tri = (drawverts[0], drawverts[k+1], drawverts[k+2])
			elif k & 1:
				tri = (drawverts[k+1], drawverts[k], drawverts[k+2]) # odd strip triangles keep the strip winding
			else:
				tri = (drawverts[k], drawverts[k+1], drawverts[k+2])
			for s, t, index_xyz in tri:
				drawtris_st.append((s, t))
				drawtris_xyz.append(index_xyz)

	header.stverts = stverts
	header.triangles = triangles
	header.frames = frames
	header.glcmds = glcmds
	header.drawtris_st = np.array(drawtris_st, dtype=np.float32).reshape((-1, 2)) # Q2PORT
	header.drawtris_xyz = np.array(drawtris_xyz, dtype=np.intp) # Q2PORT

	mod.type = model.modtype_t.mod_alias
	mod.numframes = header.num_frames
	mod.extradata = header # paliashdr

	mod.mins[0] = -32
	mod.mins[1] = -32
	mod.mins[2] = -32
	mod.maxs[0] = 32
	mod.maxs[1] = 32
	mod.maxs[2] = 32

def Mod_LoadSpriteModel (mod, buff): # model_t *, void *

	sprite = files_h.dsprite_t()
	sprite.load(buff)

	if sprite.version != files_h.SPRITE_VERSION:
		gl1_main.ri.Sys_Error (shared.ERR_DROP, "{} has wrong sprite version ({})".format(mod.name, sprite.version))

	skin_count = min(sprite.numframes, files_h.MAX_MD2SKINS)
	for i in range(skin_count):
		frame = sprite.frames[i]
		if not frame.name:
			continue
		mod.skins[i] = gl1_image.R_FindImage (frame.name, gl1_image.imagetype_t.it_sprite)

	mod.type = model.modtype_t.mod_sprite
	mod.numframes = sprite.numframes
	mod.extradata = sprite

# @@@@@@@@@@@@@@@@@@@@@
# R_BeginRegistration
#
# Specifies the model that will be used as the world
# @@@@@@@@@@@@@@@@@@@@@
def R_BeginRegistration (model): #char *

	global registration_sequence

	#char	fullname[MAX_QPATH];
	#cvar_t	*flushmap;

	registration_sequence+=1
	gl1_main.r_oldviewcluster = -1		# force markleafs

	fullname = "maps/{}.bsp".format(model)

	# explicitly free the old map if different
	# this guarantees that mod_known[0] is the world map
	flushmap = gl1_main.ri.Cvar_Get ("flushmap", "0", 0)
	if mod_known[0].name != fullname or flushmap.value:
		Mod_Free (mod_known[0])
	gl1_main.r_worldmodel = Mod_ForName(fullname, True)

	gl1_main.r_viewcluster = -1

# @@@@@@@@@@@@@@@@@@@@@
# R_RegisterModel
# 
# @@@@@@@@@@@@@@@@@@@@@
def R_RegisterModel (name): # char * (returns struct model_s *)

	mod = Mod_ForName(name, False)
	if not mod:
		return None

	mod.registration_sequence = registration_sequence
	if mod.type == model.modtype_t.mod_brush:
		for texinfo in mod.texinfo:
			if texinfo.image is not None:
				texinfo.image.registration_sequence = registration_sequence
	elif mod.type in (model.modtype_t.mod_alias, model.modtype_t.mod_sprite):
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
	gl1_image.R_FreeUnusedImages()

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
