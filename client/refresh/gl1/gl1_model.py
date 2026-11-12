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
 * Model loading and caching. Includes the .bsp file format
 *
 * =======================================================================
"""
from __future__ import annotations

import copy
import math
from common import clientserver
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from client.refresh import ref_shared
from client.refresh.files import models as files_models
from client.refresh.files import pvs as files_pvs
from client.refresh.gl1.header import model
from client.refresh.gl1 import gl1_main, gl1_image, gl1_warp, gl1_lightmap

#include "header/local.h"

MAX_MOD_KNOWN = 512

modfilelen = 0 #int
mod_novis = bytearray(files_h.MAX_MAP_LEAFS // 8) #YQ2_ALIGNAS_TYPE(int) byte [MAX_MAP_LEAFS / 8]
mod_known = [] #static model_t [MAX_MOD_KNOWN]
for i in range(MAX_MOD_KNOWN):
	mod_known.append(model.model_t())
mod_numknown = 0 #static int
mod_max = 0 #static int
registration_sequence = 0 #int

#static void Mod_LoadBrushModel(model_t *mod, void *buffer, int modfilelen);
#extern void LM_BuildPolygonFromSurface(model_t *currentmodel, msurface_t *fa);
#extern void LM_CreateSurfaceLightmap(msurface_t *surf);
#extern void LM_EndBuildingLightmaps(void);
#extern void LM_BeginBuildingLightmaps(model_t *m);

#===============================================================================

def Mod_HasFreeSpace()->bool: #void (returns qboolean)

	global mod_max

	#int		i, used;
	#model_t	*mod;

	used = 0

	for i in range(mod_numknown):

		mod = mod_known[i]
		if not mod.name:
			continue
		if mod.registration_sequence == registration_sequence:

			used += 1

	if mod_max < used:

		mod_max = used

	# should same size of free slots as currently used
	return (mod_numknown + mod_max) < MAX_MOD_KNOWN

def Mod_ClusterPVS(cluster: int, model_: model.model_t): #int, const model_t * (returns const byte *)

	if (cluster == -1) or model_.vis is None:

		return mod_novis

	# Q2PORT: vis.data is the whole lump, the C's (byte *)model->vis
	return files_pvs.Mod_DecompressVis(model_.vis.data[model_.vis.bitofs[cluster][files_h.DVIS_PVS]:],
			(model_.vis.numclusters + 7) >> 3)

def Mod_Modellist_f(): #void

	#int i, total, used;
	#model_t *mod;
	#qboolean freeup;

	total = 0
	used = 0
	clientserver.Com_Printf("Loaded models:\n")

	for i in range(mod_numknown):

		mod = mod_known[i]
		in_use = ""

		if mod.registration_sequence == registration_sequence:

			in_use = "*"
			used += 1

		if not mod.name:

			continue

		clientserver.Com_Printf("{:8} : {} {}\n".format(
			mod.extradatasize, mod.name, in_use))
		total += mod.extradatasize

	clientserver.Com_Printf("Total resident: {}\n".format(total))
	# update statistics
	freeup = Mod_HasFreeSpace()
	clientserver.Com_Printf("Used {} of {} models{}.\n".format(used, mod_max, ", has free space" if freeup else ""))

def Mod_Init(): #void

	global mod_max

	mod_max = 0
	mod_novis[:] = b"\xff" * len(mod_novis) # memset(mod_novis, 0xff, sizeof(mod_novis))

"""
 * Loads in a model for the given name
"""
def Mod_ForName(name: str, parent_model: model.model_t, crash: bool)->model.model_t: #const char *, model_t *, qboolean (returns model_t *)

	global modfilelen, mod_numknown

	#model_t *mod;
	#void *buf;
	#int i;

	if not name:

		clientserver.Com_Error(shared.ERR_DROP, "{}: NULL name".format("Mod_ForName"))

	# inline models are grabbed only from worldmodel
	if name[0] == '*' and parent_model is not None:

		try:
			i = int(name[1:]) # (int)strtol(name + 1, (char **)NULL, 10)
		except ValueError:
			i = 0

		if i < 1 or i >= parent_model.numsubmodels:

			clientserver.Com_Error(shared.ERR_DROP, "{}: bad inline model number".format(
					"Mod_ForName"))

		return parent_model.submodels[i]

	# search the currently loaded models
	for i in range(mod_numknown):

		mod = mod_known[i]
		if not mod.name:

			continue

		if mod.name == name:

			return mod

	# find a free model slot spot
	i = 0
	while i < mod_numknown:

		if not mod_known[i].name:

			break # free spot

		i += 1

	if i == mod_numknown:

		if mod_numknown == MAX_MOD_KNOWN:

			clientserver.Com_Error(shared.ERR_DROP, "{}: mod_numknown == MAX_MOD_KNOWN".format("Mod_ForName"))

		mod_numknown += 1

	mod = mod_known[i]

	mod.name = name

	# load the file
	modfilelen, buf = gl1_main.ri.FS_LoadFile(mod.name)

	if buf is None:

		if crash:

			clientserver.Com_Error(shared.ERR_DROP, "{}: {} not found".format(
					"Mod_ForName", mod.name))

		mod.name = None # memset(mod->name, 0, sizeof(mod->name))
		return None

	# call the apropriate loader
	ident = shared_c.LittleLong(buf[:4])
	if ident == files_h.IDALIASHEADER:

		type_ = [0] # Q2PORT: the files_models loaders set the type's int value
		mod.extradata = files_models.Mod_LoadMD2(mod.name, buf, modfilelen,
			mod.mins, mod.maxs,
			mod.skins, gl1_image.R_FindImage,
			type_)
		mod.type = model.modtype_t(type_[0])
		if mod.extradata is None:

			clientserver.Com_Error(shared.ERR_DROP, "{}: Failed to load {}".format(
				"Mod_ForName", mod.name))

	elif ident == files_h.IDSPRITEHEADER:

		type_ = [0]
		mod.extradata = files_models.Mod_LoadSP2(mod.name, buf, modfilelen,
			mod.skins, gl1_image.R_FindImage,
			type_)
		mod.type = model.modtype_t(type_[0])
		if mod.extradata is None:

			clientserver.Com_Error(shared.ERR_DROP, "{}: Failed to load {}".format(
				"Mod_ForName", mod.name))

	elif ident == files_h.IDBSPHEADER:

		Mod_LoadBrushModel(mod, buf, modfilelen)

	else:

		clientserver.Com_Error(shared.ERR_DROP, "{}: unknown fileid for {}".format(
				"Mod_ForName", mod.name))

	mod.extradatasize = modfilelen # Hunk_End(); Q2PORT: there is no hunk, the file size stands in

	gl1_main.ri.FS_FreeFile(buf)

	return mod

def Mod_LoadSubmodels(loadmodel: model.model_t, mod_base: bytes, l: files_h.lump_t): #model_t *, byte *, lump_t *

	#dmodel_t *in;
	#model_t	*out;
	#int i, j, count;

	if l.filelen % files_h.dmodel_t.packed_size():

		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}".format(
				"Mod_LoadSubmodels", loadmodel.name))

	count = l.filelen // files_h.dmodel_t.packed_size()
	#out = Hunk_Alloc(count * sizeof(*out));

	loadmodel.submodels = []
	loadmodel.numsubmodels = count

	in_ = files_h.dmodel_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dmodel_t.packed_size()
		in_.load(mod_base[in_offset:in_offset + files_h.dmodel_t.packed_size()])

		if i == 0:

			# copy parent as template for first model
			out = copy.copy(loadmodel) # memcpy(out, loadmodel, sizeof(*out))

		else:

			# copy first as template for model
			out = copy.copy(loadmodel.submodels[0]) # memmove(out, loadmodel->submodels, sizeof(*out))

		# Q2PORT: the copy shares the parent's arrays, as the C's does; these
		# three are vec3_t and need their own storage
		out.mins = out.mins.copy()
		out.maxs = out.maxs.copy()
		out.origin = out.origin.copy()

		out.name = "*{}".format(i) # Com_sprintf (out->name, sizeof(out->name), "*%d", i)

		for j in range(3):

			# spread the mins / maxs by a pixel
			out.mins[j] = in_.mins[j] - 1
			out.maxs[j] = in_.maxs[j] + 1
			out.origin[j] = in_.origin[j]

		out.radius = files_pvs.Mod_RadiusFromBounds(out.mins, out.maxs)
		out.firstnode = in_.headnode
		out.firstmodelsurface = in_.firstface
		out.nummodelsurfaces = in_.numfaces
		# visleafs
		out.numleafs = 0
		#  check limits
		if out.firstnode >= loadmodel.numnodes:

			clientserver.Com_Error(shared.ERR_DROP, "{}: Inline model {} has bad firstnode".format(
					"Mod_LoadSubmodels", i))

		loadmodel.submodels.append(out)

"""
 * Fills in s->texturemins[] and s->extents[]
"""
def Mod_CalcSurfaceExtents(loadmodel: model.model_t, s: model.msurface_t): #model_t *, msurface_t *

	mins = [999999.0, 999999.0] #float [2]
	maxs = [-99999.0, -99999.0] #float [2]
	#float val;
	#int i, j, e;
	#mvertex_t *v;
	#mtexinfo_t *tex;
	bmins = [0, 0] #int [2]
	bmaxs = [0, 0] #int [2]

	tex = s.texinfo

	for i in range(s.numedges):

		e = loadmodel.surfedges[s.firstedge + i]

		if e >= 0:

			v = loadmodel.vertexes[loadmodel.edges[e].v[0]]

		else:

			v = loadmodel.vertexes[loadmodel.edges[-e].v[1]]

		for j in range(2):

			val = (v.position[0] * tex.vecs[j][0] +
				  v.position[1] * tex.vecs[j][1] +
				  v.position[2] * tex.vecs[j][2] +
				  tex.vecs[j][3])

			if val < mins[j]:

				mins[j] = val

			if val > maxs[j]:

				maxs[j] = val

	for i in range(2):

		bmins[i] = math.floor(mins[i] / 16)
		bmaxs[i] = math.ceil(maxs[i] / 16)

		s.texturemins[i] = bmins[i] * 16
		s.extents[i] = (bmaxs[i] - bmins[i]) * 16

"""
static int calcTexinfoAndFacesSize(byte *mod_base, const lump_t *fl, const lump_t *tl)
{
	(not ported: it only sizes the hunk, and the port has no hunk)
}
"""

def Mod_LoadFaces(loadmodel: model.model_t, mod_base: bytes, l: files_h.lump_t): #model_t *, byte *, lump_t *

	#dface_t *in;
	#msurface_t *out;
	#int i, count, surfnum;
	#int planenum, side;
	#int ti;

	if l.filelen % files_h.dface_t.packed_size():

		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}".format(
				"Mod_LoadFaces", loadmodel.name))

	count = l.filelen // files_h.dface_t.packed_size()
	#out = Hunk_Alloc(count * sizeof(*out));

	loadmodel.surfaces = []
	loadmodel.numsurfaces = count

	gl1_lightmap.LM_BeginBuildingLightmaps(loadmodel)

	in_ = files_h.dface_t()

	for surfnum in range(count):

		in_offset = l.fileofs + surfnum * files_h.dface_t.packed_size()
		in_.load(mod_base[in_offset:in_offset + files_h.dface_t.packed_size()])

		out = model.msurface_t()
		loadmodel.surfaces.append(out)

		out.firstedge = in_.firstedge
		out.numedges = in_.numedges
		out.flags = 0
		out.polys = []

		planenum = in_.planenum
		side = in_.side

		if side:

			out.flags |= model.SURF_PLANEBACK

		if planenum < 0 or planenum >= loadmodel.numplanes:

			clientserver.Com_Error(shared.ERR_DROP, "{}: Incorrect {} planenum.".format(
					"Mod_LoadFaces", planenum))

		out.plane = loadmodel.planes[planenum]

		ti = in_.texinfo

		if (ti < 0) or (ti >= loadmodel.numtexinfo):

			clientserver.Com_Error(shared.ERR_DROP, "{}: bad texinfo number".format(
					"Mod_LoadFaces"))

		out.texinfo = loadmodel.texinfo[ti]

		Mod_CalcSurfaceExtents(loadmodel, out)

		# lighting info
		out.styles = [0] * files_h.MAXLIGHTMAPS
		for i in range(files_h.MAXLIGHTMAPS):

			out.styles[i] = in_.styles[i]

		i = in_.lightofs
		if i >= 0x80000000: # Q2PORT: dface_t.load reads it unsigned; the C's int
			i -= 0x100000000

		if i == -1:

			out.samples = None

		else:

			out.samples = memoryview(loadmodel.lightdata)[i:] # loadmodel->lightdata + i, Q2PORT: a view, not a copy

		# set the drawing flags
		if out.texinfo.flags & shared.SURF_WARP:

			out.flags |= model.SURF_DRAWTURB

			for i in range(2):

				out.extents[i] = 16384
				out.texturemins[i] = -8192

			gl1_warp.R_SubdivideSurface(loadmodel, out) # cut up polygon for warps

		if gl1_main.r_fixsurfsky.value:

			if out.texinfo.flags & shared.SURF_SKY:

				out.flags |= model.SURF_DRAWSKY

		# create lightmaps and polygons
		if not (out.texinfo.flags & (shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP)):

			gl1_lightmap.LM_CreateSurfaceLightmap(out)

		if not (out.texinfo.flags & shared.SURF_WARP):

			gl1_lightmap.LM_BuildPolygonFromSurface(loadmodel, out)

	gl1_lightmap.LM_EndBuildingLightmaps()

def Mod_LoadLeafs(loadmodel: model.model_t, mod_base: bytes, l: files_h.lump_t): #model_t *, byte *, lump_t *

	#dleaf_t *in;
	#mleaf_t *out;
	#int i, j, count, p;

	if l.filelen % files_h.dleaf_t.packed_size():

		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}".format(
				"Mod_LoadLeafs", loadmodel.name))

	count = l.filelen // files_h.dleaf_t.packed_size()
	#out = Hunk_Alloc(count * sizeof(*out));

	loadmodel.leafs = []
	loadmodel.numleafs = count

	in_ = files_h.dleaf_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dleaf_t.packed_size()
		in_.load(mod_base[in_offset:in_offset + files_h.dleaf_t.packed_size()])

		out = ref_shared.mleaf_t()
		loadmodel.leafs.append(out)

		#unsigned firstleafface;

		for j in range(3):

			# Q2PORT: float(), the C stores the short into its float minmaxs; a numpy
			# int16 kept here made each BoxOnPlaneSide() in R_CullBox about 8 times slower
			out.minmaxs[j] = float(in_.mins[j])
			out.minmaxs[3 + j] = float(in_.maxs[j])

		p = in_.contents
		out.contents = p

		out.cluster = in_.cluster
		out.area = in_.area

		# make unsigned long from signed short
		firstleafface = in_.firstleafface & 0xFFFF
		out.nummarksurfaces = in_.numleaffaces & 0xFFFF

		# Q2PORT: a slice of loadmodel->marksurfaces in place of the C's pointer into it
		out.firstmarksurface = loadmodel.marksurfaces[firstleafface:firstleafface + out.nummarksurfaces]
		if (firstleafface + out.nummarksurfaces) > loadmodel.nummarksurfaces:

			clientserver.Com_Error(shared.ERR_DROP, "{}: wrong marksurfaces position in {}".format(
				"Mod_LoadLeafs", loadmodel.name))

def Mod_LoadMarksurfaces(loadmodel: model.model_t, mod_base: bytes, l: files_h.lump_t): #model_t *, byte *, lump_t *

	#int i, j, count;
	#short *in;
	#msurface_t **out;

	if l.filelen % 2: # sizeof(*in)

		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}".format(
				"Mod_LoadMarksurfaces", loadmodel.name))

	count = l.filelen // 2
	#out = Hunk_Alloc(count * sizeof(*out));

	loadmodel.marksurfaces = []
	loadmodel.nummarksurfaces = count

	for i in range(count):

		in_offset = l.fileofs + i * 2
		j = shared_c.LittleSShort(mod_base[in_offset:in_offset + 2])

		if (j < 0) or (j >= loadmodel.numsurfaces):

			clientserver.Com_Error(shared.ERR_DROP, "{}: bad surface number".format(
					"Mod_LoadMarksurfaces"))

		loadmodel.marksurfaces.append(loadmodel.surfaces[j])

def Mod_LoadBrushModel(mod: model.model_t, buffer: bytes, modfilelen: int): #model_t *, void *, int

	#int i;
	#dheader_t *header;
	#byte *mod_base;

	if mod is not mod_known[0]:

		clientserver.Com_Error(shared.ERR_DROP, "{}: Loaded a brush model after the world".format("Mod_LoadBrushModel"))

	header = files_h.dheader_t()
	header.parse(buffer)

	i = header.version

	if i != files_h.BSPVERSION:

		clientserver.Com_Error(shared.ERR_DROP, "{}: {} has wrong version number ({} should be {})".format(
				"Mod_LoadBrushModel", mod.name, i, files_h.BSPVERSION))

	# swap all the lumps
	mod_base = buffer

	# Q2PORT: dheader_t.parse swapped the lumps; the C then sizes the hunk
	# (Mod_CalcLumpHunkSize, calcTexinfoAndFacesSize), which the port doesn't need

	#mod->extradata = Hunk_Begin(hunkSize);
	mod.type = model.modtype_t.mod_brush

	# load into heap
	# Q2PORT: the files_models loaders fill one element lists in place of the C's out pointers
	vertexes, numvertexes = [None], [0]
	files_models.Mod_LoadVertexes(mod.name, vertexes, numvertexes, mod_base,
		header.lumps[files_h.LUMP_VERTEXES], 0)
	mod.vertexes, mod.numvertexes = vertexes[0], numvertexes[0]
	edges, numedges = [None], [0]
	files_models.Mod_LoadEdges(mod.name, edges, numedges,
		mod_base, header.lumps[files_h.LUMP_EDGES], 1)
	mod.edges, mod.numedges = edges[0], numedges[0]
	surfedges, numsurfedges = [None], [0]
	files_models.Mod_LoadSurfedges(mod.name, surfedges, numsurfedges,
		mod_base, header.lumps[files_h.LUMP_SURFEDGES], 0)
	mod.surfedges, mod.numsurfedges = surfedges[0], numsurfedges[0]
	lightdata = [None]
	files_models.Mod_LoadLighting(lightdata, mod_base, header.lumps[files_h.LUMP_LIGHTING])
	mod.lightdata = lightdata[0]
	planes, numplanes = [None], [0]
	files_models.Mod_LoadPlanes (mod.name, planes, numplanes,
		mod_base, header.lumps[files_h.LUMP_PLANES], 0)
	mod.planes, mod.numplanes = planes[0], numplanes[0]
	texinfo, numtexinfo = [None], [0]
	files_models.Mod_LoadTexinfo(mod.name, texinfo, numtexinfo,
		mod_base, header.lumps[files_h.LUMP_TEXINFO], gl1_image.R_FindImage,
		gl1_main.r_notexture, 0)
	mod.texinfo, mod.numtexinfo = texinfo[0], numtexinfo[0]
	Mod_LoadFaces(mod, mod_base, header.lumps[files_h.LUMP_FACES])
	Mod_LoadMarksurfaces(mod, mod_base, header.lumps[files_h.LUMP_LEAFFACES])
	vis = [None]
	files_models.Mod_LoadVisibility (vis, mod_base, header.lumps[files_h.LUMP_VISIBILITY])
	mod.vis = vis[0]
	Mod_LoadLeafs(mod, mod_base, header.lumps[files_h.LUMP_LEAFS])
	nodes, numnodes = [None], [0]
	files_models.Mod_LoadNodes(mod.name, mod.planes, mod.numplanes, mod.leafs,
		mod.numleafs, nodes, numnodes, mod_base,
		header.lumps[files_h.LUMP_NODES])
	mod.nodes, mod.numnodes = nodes[0], numnodes[0]
	Mod_LoadSubmodels (mod, mod_base, header.lumps[files_h.LUMP_MODELS])
	mod.numframes = 2 # regular and alternate animation

def Mod_Free(mod: model.model_t): #model_t *

	#Hunk_Free(mod->extradata);
	mod.reset() # memset(mod, 0, sizeof(*mod))

def Mod_FreeAll(): #void

	#int i;

	for i in range(mod_numknown):

		if mod_known[i].extradatasize:

			Mod_Free(mod_known[i])

"""
 * Specifies the model that will be used as the world
"""
def RI_BeginRegistration(model_: str): #const char *

	global registration_sequence

	#char fullname[MAX_QPATH];
	#cvar_t *flushmap;

	registration_sequence += 1
	gl1_main.r_oldviewcluster = -1 # force markleafs

	fullname = "maps/{}.bsp".format(model_)

	# explicitly free the old map if different
	#   this guarantees that mod_known[0] is the
	#   world map
	flushmap = gl1_main.ri.Cvar_Get("flushmap", "0", 0)

	if mod_known[0].name != fullname or flushmap.value:

		Mod_Free(mod_known[0])

	gl1_main.r_worldmodel = Mod_ForName(fullname, None, True)

	gl1_main.r_viewcluster = -1

def RI_RegisterModel(name: str)->model.model_t: #const char * (returns struct model_s *)

	#model_t *mod;

	mod = Mod_ForName(name, gl1_main.r_worldmodel, False)

	if mod is not None:

		mod.registration_sequence = registration_sequence

		# register any images used by the models
		if mod.type == model.modtype_t.mod_brush:

			#int i;

			for i in range(mod.numtexinfo):

				mod.texinfo[i].image.registration_sequence = registration_sequence

		else:

			# numframes is unused for SP2 but lets set it also
			mod.numframes = files_models.Mod_ReLoadSkins(mod.skins,
				gl1_image.R_FindImage, mod.extradata, mod.type.value)

	return mod

def RI_EndRegistration(): #void

	#int i;
	#model_t *mod;

	if Mod_HasFreeSpace() and gl1_image.R_ImageHasFreeSpace():

		# should be enough space for load next maps
		return

	for i in range(mod_numknown):

		mod = mod_known[i]
		if not mod.name:

			continue

		if mod.registration_sequence != registration_sequence:

			# don't need this model
			Mod_Free(mod)

	gl1_image.R_FreeUnusedImages()
