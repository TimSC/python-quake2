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
 * The models file format
 *
 * =======================================================================
"""
from __future__ import annotations

import types

import numpy as np

from q2data import FormatError
from q2data import bsp as q2bsp
from q2data import md2 as q2md2
from q2data import sp2 as q2sp2
from common.header import shared
from common import clientserver
from client.refresh import ref_shared


class daliasframe_t(object):
	# one frame of an alias model, as the renderers use it

	def __init__(self):
		self.scale = np.zeros((3,), dtype=np.float32) # multiply byte verts by this
		self.translate = np.zeros((3,), dtype=np.float32) # then add this
		self.name = "" # frame name from grabbing
		self.verts = [] # (num_xyz, 4) bytes: the position, then the normal index

class dmdl_t(object):
	# an alias model: the MD2 header values, and the data the renderers use
	# (Mod_LoadMD2 sets frames, stverts, glcmds and the glcmds_* arrays)

	def __init__(self):
		self.ident = None
		self.version = None
		self.skinwidth = None
		self.skinheight = None
		self.framesize = None # byte size of each frame
		self.num_skins = None
		self.num_xyz = None
		self.num_st = None # greater than num_xyz for seams
		self.num_tris = None
		self.num_glcmds = None # dwords in strip/fan command list
		self.num_frames = None
		self.ofs_skins = None # each skin is a MAX_SKINNAME string
		self.ofs_st = None # byte offset from start for stverts
		self.ofs_tris = None # offset for dtriangles
		self.ofs_frames = None # offset for first frame
		self.ofs_glcmds = None
		self.ofs_end = None # end of file

class dsprframe_t(object):

	def __init__(self):
		self.width = None
		self.height = None
		self.origin_x = None # raster coordinates inside pic
		self.origin_y = None
		self.name = "" # name of pcx file

class dsprite_t(object):

	def __init__(self):
		self.ident = None
		self.version = None
		self.numframes = None
		self.frames = []

"""
=================
lump_records, lump_rows

The renderers' BSP lumps, read by q2data.bsp. lump_rows gives each record as
an object with the C field names, which the loaders below still use.
=================
"""
C_FIELDS = {
	q2bsp.Lump.PLANES: ("normal", "dist", "type"),
	q2bsp.Lump.VERTICES: ("point",),
	q2bsp.Lump.NODES: ("planenum", "children", "mins", "maxs", "firstface", "numfaces"),
	q2bsp.Lump.TEXINFO: ("vecs", "flags", "value", "texture", "nexttexinfo"),
	q2bsp.Lump.FACES: ("planenum", "side", "firstedge", "numedges", "texinfo", "styles", "lightofs"),
	q2bsp.Lump.LEAFS: ("contents", "cluster", "area", "mins", "maxs", "firstleafface",
		"numleaffaces", "firstleafbrush", "numleafbrushes"),
	q2bsp.Lump.EDGES: ("v",),
	q2bsp.Lump.MODELS: ("mins", "maxs", "origin", "headnode", "firstface", "numfaces"),
}

def lump_records(error, mod_base, l, lump): #str, bytes, q2bsp.LumpInfo, q2bsp.Lump (returns numpy record array)

	try:
		return q2bsp.lump_records(mod_base, l, lump)
	except FormatError:
		clientserver.Com_Error(shared.ERR_DROP, error)

def lump_rows(error, mod_base, l, lump): #str, bytes, q2bsp.LumpInfo, q2bsp.Lump (returns list of SimpleNamespace)

	fields = C_FIELDS[lump]
	rows = [types.SimpleNamespace(**dict(zip(fields, row)))
		for row in lump_records(error, mod_base, l, lump).tolist()]
	if lump == q2bsp.Lump.TEXINFO:
		for row in rows:
			row.texture = row.texture.split(b"\0", 1)[0].decode("latin-1")
	return rows

"""
=================
Mod_LoadAliasModel/Mod_LoadMD2
=================
"""
def Mod_LoadMD2(mod_name, buff, modfilelen, mins, maxs, skins, find_image, type): #const char *, const void *, int, vec3_t, vec3_t, struct image_s **, findimage_t, modtype_t * (returns void *)

	# The file is parsed by q2data.md2; the engine checks its limits and keeps
	# the model in a dmdl_t, as the renderers expect.
	data = bytes(buff[:modfilelen])

	try:
		q2header = q2md2.read_header(data)
	except FormatError as err:
		reason = str(err)
		if reason.startswith("has wrong version"):
			clientserver.Com_Printf("{}: {} {}\n".format("Mod_LoadMD2", mod_name, reason))
		elif reason.startswith("file size"):
			clientserver.Com_Printf("{}: model {} {}\n".format("Mod_LoadMD2", mod_name, reason))
		else:
			clientserver.Com_Printf("{}: model {} {}\n".format("Mod_LoadMD2", mod_name, reason))
		return None

	if q2header.skin_height > ref_shared.MAX_LBM_HEIGHT:
		clientserver.Com_Printf("{}: model {} has a skin taller than {}\n".format("Mod_LoadMD2", mod_name, ref_shared.MAX_LBM_HEIGHT))
		return None

	if q2header.num_xyz <= 0:
		clientserver.Com_Printf("{}: model {} has no vertices\n".format("Mod_LoadMD2", mod_name))
		return None

	if q2header.num_xyz > q2md2.MAX_VERTS:
		clientserver.Com_Printf("{}: model {} has too many vertices\n".format("Mod_LoadMD2", mod_name))
		return None

	if q2header.num_st <= 0:
		clientserver.Com_Printf("{}: model {} has no st vertices\n".format("Mod_LoadMD2", mod_name))
		return None

	if q2header.num_tris <= 0:
		clientserver.Com_Printf("{}: model {} has no triangles\n".format("Mod_LoadMD2", mod_name))
		return None

	if q2header.num_frames <= 0:
		clientserver.Com_Printf("{}: model {} has no frames\n".format("Mod_LoadMD2", mod_name))
		return None

	try:
		model = q2md2.load_md2(data)
	except FormatError as err:
		clientserver.Com_Printf("{}: model {} {}\n".format("Mod_LoadMD2", mod_name, err))
		return None

	header = dmdl_t()
	header.ident = q2md2.MD2_IDENT
	header.version = q2md2.MD2_VERSION
	header.skinwidth = q2header.skin_width
	header.skinheight = q2header.skin_height
	header.framesize = q2header.frame_size
	header.num_skins = q2header.num_skins
	header.num_xyz = q2header.num_xyz
	header.num_st = q2header.num_st
	header.num_tris = q2header.num_tris
	header.num_glcmds = q2header.num_glcmds
	header.num_frames = q2header.num_frames
	header.ofs_skins = q2header.ofs_skins
	header.ofs_st = q2header.ofs_st
	header.ofs_tris = q2header.ofs_tris
	header.ofs_frames = q2header.ofs_frames
	header.ofs_glcmds = q2header.ofs_glcmds
	header.ofs_end = q2header.ofs_end

	if header.num_skins > q2md2.MAX_SKINS:
		clientserver.Com_Printf("{} has too many skins ({} > {}), extra sprites will be ignored\n".format(mod_name, header.num_skins, q2md2.MAX_SKINS))
		header.num_skins = q2md2.MAX_SKINS

	# base s and t vertices (not used in gl version)
	stverts = list(zip(model.st["s"].tolist(), model.st["t"].tolist()))

	# the frames: verts is (num_xyz, 4) bytes, the position then the normal index
	frames = [] # daliasframe_t[num_frames]
	for q2frame in model.frames:
		frame = daliasframe_t()
		frame.scale = q2frame.scale
		frame.translate = q2frame.translate
		frame.name = q2frame.name
		frame.verts = q2frame.verts.view(np.uint8).reshape((header.num_xyz, 4))
		frames.append(frame)

	# The glcmds are ints with the texture coordinates being floats punned into
	# the same array. Decode them into a plain list of count, then (s float,
	# t float, index_xyz int) per vertex, ending with 0.
	words = model.glcmds
	floats = words.view(np.float32)
	glcmds = []
	glcmds_counts = [] # the signed count of each fan (< 0) or strip (> 0)
	glcmds_st = []
	glcmds_xyz = []
	i = 0
	while i < len(words):
		count = int(words[i])
		i += 1
		glcmds.append(count)
		if not count:
			break
		if i + abs(count) * 3 > len(words):
			break # the list ends in the middle of a fan or strip
		glcmds_counts.append(count)
		for _ in range(abs(count)):
			s_coord, t_coord, index_xyz = float(floats[i]), float(floats[i + 1]), int(words[i + 2])
			i += 3
			glcmds.extend((s_coord, t_coord, index_xyz))
			glcmds_st.append((s_coord, t_coord))
			glcmds_xyz.append(index_xyz)

	if glcmds and glcmds[-1] != 0:
		clientserver.Com_Printf("{}: Entity {} has possible last element issues with {} verts.\n".format("Mod_LoadMD2", mod_name, glcmds[-1]))

	# register all skins
	skinnames = model.skins[:header.num_skins]
	for i, name in enumerate(skinnames):
		skins[i] = find_image(name, ref_shared.imagetype_t.it_skin)

	type[0] = ref_shared.modtype_t.mod_alias.value

	mins[0] = -32
	mins[1] = -32
	mins[2] = -32
	maxs[0] = 32
	maxs[1] = 32
	maxs[2] = 32

	header.stverts = stverts
	header.frames = frames
	header.glcmds = glcmds
	# the glcmds again as arrays, so the renderers can draw a whole model with
	# numpy: glcmds_st and glcmds_xyz are the (s, t) and index_xyz of all the
	# fan and strip vertices in order; glcmds_tris is the triangle index list
	# the renderer builds from these on the first draw.
	header.glcmds_counts = glcmds_counts
	header.glcmds_st = np.array(glcmds_st, dtype=np.float32).reshape((-1, 2))
	header.glcmds_xyz = np.array(glcmds_xyz, dtype=np.intp)
	header.glcmds_tris = None
	header.skinnames = skinnames
	return header # extradata

"""
==============================================================================

SPRITE MODELS

==============================================================================
"""
"""
=================
Mod_LoadSP2

support for .sp2 sprites
=================
"""
def Mod_LoadSP2(mod_name, buff, modfilelen, skins, find_image, type): #const char *, const void *, int, struct image_s **, findimage_t, modtype_t * (returns void *)

	try:
		q2sprite = q2sp2.load_sp2(bytes(buff[:modfilelen]))
	except FormatError as err:
		clientserver.Com_Printf("{} {}\n".format(mod_name, err))
		return None

	sprite = dsprite_t()
	sprite.ident = q2sp2.SP2_IDENT
	sprite.version = q2sp2.SP2_VERSION
	sprite.numframes = len(q2sprite.frames)
	for q2frame in q2sprite.frames:
		frame = dsprframe_t()
		frame.width, frame.height = q2frame.width, q2frame.height
		frame.origin_x, frame.origin_y = q2frame.origin_x, q2frame.origin_y
		frame.name = q2frame.name
		sprite.frames.append(frame)

	if sprite.numframes > q2md2.MAX_SKINS:
		clientserver.Com_Printf("{} has too many frames ({} > {}), extra frames will be ignored\n".format(mod_name, sprite.numframes, q2md2.MAX_SKINS))
		sprite.numframes = q2md2.MAX_SKINS

	for i in range(sprite.numframes):
		skins[i] = find_image(sprite.frames[i].name, ref_shared.imagetype_t.it_sprite)

	type[0] = ref_shared.modtype_t.mod_sprite.value

	return sprite # extradata

"""
=================
Mod_ReLoad

Reload images in SP2/MD2 (mark registration_sequence)
=================
"""
def Mod_ReLoadSkins(skins, find_image, extradata, type): #struct image_s **, findimage_t, void *, modtype_t (returns int)

	if type == ref_shared.modtype_t.mod_sprite.value:
		sprout = extradata
		for i in range(sprout.numframes):
			skins[i] = find_image(sprout.frames[i].name, ref_shared.imagetype_t.it_sprite)
		return sprout.numframes
	elif type == ref_shared.modtype_t.mod_alias.value:
		pheader = extradata
		for i in range(pheader.num_skins):
			skins[i] = find_image(pheader.skinnames[i], ref_shared.imagetype_t.it_skin)
		return pheader.num_frames

	# Unknow format, no images associated with it
	return 0

"""
=================
Mod_SetParent
=================
"""
def Mod_SetParent(node, parent): #mnode_t *, mnode_t *

	node.parent = parent
	if node.contents != ref_shared.CONTENTS_NODE:
		return

	Mod_SetParent(node.children[0], node)
	Mod_SetParent(node.children[1], node)

"""
=================
Mod_NumberLeafs
=================
"""
def Mod_NumberLeafs(leafs, node, r_leaftovis, r_vistoleaf, numvisleafs): #mleaf_t *, mnode_t *, int *, int *, int *

	if node.contents != ref_shared.CONTENTS_NODE:
		leaf = node
		leafnum = leafs.index(leaf)
		if leaf.contents & shared.CONTENTS_SOLID:
			return

		r_leaftovis[leafnum] = numvisleafs[0]
		r_vistoleaf[numvisleafs[0]] = leafnum
		numvisleafs[0] += 1
		return

	Mod_NumberLeafs(leafs, node.children[0], r_leaftovis, r_vistoleaf, numvisleafs)
	Mod_NumberLeafs(leafs, node.children[1], r_leaftovis, r_vistoleaf, numvisleafs)

"""
=================
Mod_LoadNodes
=================
"""
def Mod_LoadNodes(name, planes, numplanes, leafs, numleafs, nodes, numnodes, mod_base, l): #const char *, cplane_t *, int, mleaf_t *, int, mnode_t **, int *, const byte *, const lump_t *

	#int	r_leaftovis[MAX_MAP_LEAFS], r_vistoleaf[MAX_MAP_LEAFS];
	r_leaftovis = [0] * q2bsp.MAX_MAP_LEAFS
	r_vistoleaf = [0] * q2bsp.MAX_MAP_LEAFS
	rows = lump_rows("{}: funny lump size in {}\n".format("Mod_LoadNodes", name), mod_base, l, q2bsp.Lump.NODES)
	count = len(rows)
	#out = Hunk_Alloc(count * sizeof(*out));
	nodes[0] = []
	numnodes[0] = count

	for i in range(count):

		in_obj = rows[i]

		node = ref_shared.mnode_t()
		for j in range(3):
			# Q2PORT: float(), the C stores the short into its float minmaxs; a numpy
			# int16 kept here made each BoxOnPlaneSide() in R_CullBox about 8 times slower
			node.minmaxs[j] = float(in_obj.mins[j])
			node.minmaxs[3 + j] = float(in_obj.maxs[j])

		if in_obj.planenum < 0 or in_obj.planenum >= numplanes:
			clientserver.Com_Error(shared.ERR_DROP, "{}: Incorrect {} < {} planenum.\n".format("Mod_LoadNodes", in_obj.planenum, numplanes))
		node.plane = planes[in_obj.planenum]

		node.firstsurface = in_obj.firstface
		node.numsurfaces = in_obj.numfaces
		node.contents = ref_shared.CONTENTS_NODE

		children = [None, None]
		for j in range(2):
			leafnum = in_obj.children[j]
			if leafnum >= 0:
				if leafnum >= numnodes[0]:
					clientserver.Com_Error(shared.ERR_DROP, "{}: Incorrect {} nodenum as leaf.\n".format("Mod_LoadNodes", leafnum))
				children[j] = None # node, fixed up below
			else:
				leafnum = -1 - leafnum
				if leafnum < 0 or leafnum >= numleafs:
					clientserver.Com_Error(shared.ERR_DROP, "{}: Incorrect {} leafnum.\n".format("Mod_LoadNodes", leafnum))
				children[j] = leafs[leafnum]
		node.children = children
		nodes[0].append(node)

	# fix up node children (they reference nodes loaded before they existed)
	for i, (node, (in_off,)) in enumerate(zip(nodes[0], [(None,) for _ in nodes[0]])):
		pass
	# re-walk using the original lump for child indices
	for i in range(count):
		in_obj = rows[i]
		node = nodes[0][i]
		for j in range(2):
			leafnum = in_obj.children[j]
			if leafnum >= 0:
				node.children[j] = nodes[0][leafnum]

	Mod_SetParent(nodes[0][0], None) # sets nodes and leafs

	numvisleafs = [0]
	Mod_NumberLeafs(leafs, nodes[0][0], r_leaftovis, r_vistoleaf, numvisleafs)

"""
=================
Mod_LoadVisibility
=================
"""
def Mod_LoadVisibility(vis, mod_base, l): #dvis_t **, const byte *, const lump_t *

	if not l.length:
		vis[0] = None
		return

	in_offset = l.offset
	in_offset2 = in_offset + l.length
	buffer = mod_base[in_offset:in_offset2]

	vis[0] = q2bsp.Visibility.from_bytes(bytes(buffer))

"""
=================
Mod_LoadVertexes

extra for skybox
=================
"""
def Mod_LoadVertexes(name, vertexes, numvertexes, mod_base, l, extra): #const char *, mvertex_t **, int *, const byte *, const lump_t *, int

	rows = lump_rows("{}: funny lump size in {}\n".format("Mod_LoadVertexes", name), mod_base, l, q2bsp.Lump.VERTICES)
	count = len(rows)
	#out = Hunk_Alloc((count + extra)*sizeof(*out));
	out = []
	for i in range(count):

		in_obj = rows[i]

		v = ref_shared.mvertex_t()
		v.position[0] = in_obj.point[0]
		v.position[1] = in_obj.point[1]
		v.position[2] = in_obj.point[2]
		out.append(v)

	for _ in range(extra):
		out.append(ref_shared.mvertex_t())

	vertexes[0] = out
	numvertexes[0] = count

"""
=================
Mod_LoadLighting
=================
"""
def Mod_LoadLighting(lightdata, mod_base, l): #byte **, const byte *, const lump_t *

	if not l.length:
		lightdata[0] = None
		return

	in_offset = l.offset
	in_offset2 = in_offset + l.length
	lightdata[0] = mod_base[in_offset:in_offset2]

"""
=================
Mod_LoadTexinfo

extra for skybox in soft render
=================
"""
def GetTexImage(name, find_image): #const char *, findimage_t (returns struct image_s *)

	image = None
	image = find_image ("textures/{}.wal".format(name), ref_shared.imagetype_t.it_wall)
	if image is None:

		image = find_image ("textures/{}.m32".format(name), ref_shared.imagetype_t.it_wall)

	if image is None:

		image = find_image ("textures/{}.m8".format(name), ref_shared.imagetype_t.it_wall)

	return image

def Mod_LoadTexinfo(name, texinfo, numtexinfo, mod_base, l, find_image, notexture, extra): #const char *, mtexinfo_t **, int *, const byte *, const lump_t *, findimage_t, struct image_s *, int

	rows = lump_rows("{}: funny lump size in {}\n".format("Mod_LoadTexinfo", name), mod_base, l, q2bsp.Lump.TEXINFO)
	count = len(rows)
	out = []
	texinfo[0] = out
	numtexinfo[0] = count

	for i in range(count):

		in_obj = rows[i]

		out_obj = ref_shared.mtexinfo_t()
		for j in range(4):
			out_obj.vecs[0][j] = in_obj.vecs[0][j]
			out_obj.vecs[1][j] = in_obj.vecs[1][j]

		out_obj.flags = in_obj.flags
		next = in_obj.nexttexinfo
		if next > 0:
			out_obj.next = next # index, fixed up below
		else:
			out_obj.next = None

		image = GetTexImage(in_obj.texture, find_image)
		if image is None:
			clientserver.Com_Printf ("{}: Couldn't load {}\n".format("Mod_LoadTexinfo", in_obj.texture))
			image = notexture

		out_obj.image = image

		out.append(out_obj)

	# the index is turned into a reference once all the texinfos exist
	for i in range(count):
		out_obj = out[i]
		if isinstance(out_obj.next, int):
			out_obj.next = out[out_obj.next]

	# count animation frames
	for i in range(count):
		out_obj = out[i]
		out_obj.numframes = 1
		step = out_obj.next
		while step is not None and step is not out_obj:
			out_obj.numframes += 1
			step = step.next

"""
=================
Mod_LoadEdges

extra is used for skybox, which adds 6 surfaces
=================
"""
def Mod_LoadEdges(name, edges, numedges, mod_base, l, extra): #const char *, medge_t **, int *, const byte *, const lump_t *, int

	rows = lump_rows("{}: funny lump size in {}\n".format("Mod_LoadEdges", name), mod_base, l, q2bsp.Lump.EDGES)
	count = len(rows)
	out = []
	for i in range(count):

		in_obj = rows[i]

		e = ref_shared.medge_t()
		e.v[0] = in_obj.v[0]
		e.v[1] = in_obj.v[1]
		out.append(e)

	for _ in range(extra):
		out.append(ref_shared.medge_t())

	edges[0] = out
	numedges[0] = count

"""
=================
Mod_LoadPlanes

extra is used for skybox, which adds 6 surfaces
=================
"""
def Mod_LoadPlanes(name, planes, numplanes, mod_base, l, extra): #const char *, cplane_t **, int *, const byte *, const lump_t *, int

	rows = lump_rows("{}: funny lump size in {}\n".format("Mod_LoadPlanes", name), mod_base, l, q2bsp.Lump.PLANES)
	count = len(rows)
	out = []
	for i in range(count):

		in_obj = rows[i]

		out_obj = shared.cplane_t()
		bits = 0
		for j in range(3):
			out_obj.normal[j] = in_obj.normal[j]
			if out_obj.normal[j] < 0.0:
				bits |= (1 << j)

		out_obj.dist = in_obj.dist
		out_obj.type = in_obj.type
		out_obj.signbits = bits
		out.append(out_obj)

	for _ in range(extra):
		out.append(shared.cplane_t())

	planes[0] = out
	numplanes[0] = count

"""
=================
Mod_LoadSurfedges
=================
"""
def Mod_LoadSurfedges(name, surfedges, numsurfedges, mod_base, l, extra): #const char *, int **, int *, const byte *, const lump_t *, int

	out = lump_records("{}: funny lump size in {}\n".format("Mod_LoadSurfedges", name),
		mod_base, l, q2bsp.Lump.SURF_EDGES).tolist()
	count = len(out)

	for _ in range(extra):
		out.append(0)

	surfedges[0] = out
	numsurfedges[0] = count

"""
=================
Mod_LoadSurfedges

calculate the size that Hunk_Alloc(), called by Mod_Load*() from Mod_LoadBrushModel(),
will use (=> includes its padding), so we'll know how big the hunk needs to be
extra is used for skybox, which adds 6 surfaces
=================
"""
def Mod_CalcLumpHunkSize(l, inSize, outSize, extra): #const lump_t *, int, int, int (returns int)

	# the Python port has no hunk, so this is unused
	if l.length % inSize:
		return 0

	count = l.length // inSize + extra
	size = count * outSize

	size = (size + 31) & ~31
	return size

"""
===============
Mod_PointInLeaf
===============
"""
def Mod_PointInLeaf(p, node): #const vec3_t, mnode_t * (returns mleaf_t *)

	if node is None:
		clientserver.Com_Error(shared.ERR_DROP, "{}: bad node.\n".format("Mod_PointInLeaf"))
		return None

	while True:
		if node.contents != ref_shared.CONTENTS_NODE:
			return node

		plane = node.plane
		d = shared.DotProduct(p, plane.normal) - plane.dist

		if d > 0:
			node = node.children[0]
		else:
			node = node.children[1]

	return None # never reached
