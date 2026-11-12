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

import math
import struct
import numpy as np
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from client.refresh import ref_shared


"""
=================
Mod_LoadAliasModel/Mod_LoadMD2
=================
"""
def Mod_LoadMD2(mod_name, buff, modfilelen, mins, maxs, skins, find_image, type): #const char *, const void *, int, vec3_t, vec3_t, struct image_s **, findimage_t, modtype_t * (returns void *)

	header = files_h.dmdl_t()
	header.load(buff)

	if header.version != files_h.ALIAS_VERSION:
		clientserver.Com_Printf("{}: {} has wrong version number ({} should be {})\n".format("Mod_LoadMD2", mod_name, header.version, files_h.ALIAS_VERSION))
		return None

	if header.ofs_end < 0 or header.ofs_end > modfilelen:
		clientserver.Com_Printf("{}: model {} file size({}) too small, should be {}\n".format("Mod_LoadMD2", mod_name, modfilelen, header.ofs_end))
		return None

	# Hunk_Begin(modfilelen); the Python objects are the hunk

	if header.skinheight > ref_shared.MAX_LBM_HEIGHT:
		clientserver.Com_Printf("{}: model {} has a skin taller than {}\n".format("Mod_LoadMD2", mod_name, ref_shared.MAX_LBM_HEIGHT))
		return None

	if header.num_xyz <= 0:
		clientserver.Com_Printf("{}: model {} has no vertices\n".format("Mod_LoadMD2", mod_name))
		return None

	if header.num_xyz > files_h.MAX_VERTS:
		clientserver.Com_Printf("{}: model {} has too many vertices\n".format("Mod_LoadMD2", mod_name))
		return None

	if header.num_st <= 0:
		clientserver.Com_Printf("{}: model {} has no st vertices\n".format("Mod_LoadMD2", mod_name))
		return None

	if header.num_tris <= 0:
		clientserver.Com_Printf("{}: model {} has no triangles\n".format("Mod_LoadMD2", mod_name))
		return None

	if header.num_frames <= 0:
		clientserver.Com_Printf("{}: model {} has no frames\n".format("Mod_LoadMD2", mod_name))
		return None

	if header.num_skins > files_h.MAX_MD2SKINS:
		clientserver.Com_Printf("{} has too many skins ({} > {}), extra sprites will be ignored\n".format(mod_name, header.num_skins, files_h.MAX_MD2SKINS))
		header.num_skins = files_h.MAX_MD2SKINS

	#
	# load base s and t vertices (not used in gl version)
	#
	stverts = []
	for i in range(header.num_st):
		entry_offset = header.ofs_st + i * 4
		s, t = struct.unpack_from("<hh", buff, entry_offset)
		stverts.append((s, t))

	#
	# load the frames
	#
	frames = [] # daliasframe_t[num_frames]
	frame_offset = header.ofs_frames
	for i in range(header.num_frames):
		frame_data = buff[frame_offset:frame_offset + header.framesize]
		frame = files_h.daliasframe_t()
		frame.scale = np.array(struct.unpack_from("<3f", frame_data, 0), dtype=np.float32)
		frame.translate = np.array(struct.unpack_from("<3f", frame_data, 12), dtype=np.float32)
		frame.name = frame_data[24:40].split(b'\x00', 1)[0].decode("ascii", "ignore")
		frame.verts = np.frombuffer(frame_data, dtype=np.uint8, count=header.num_xyz * 4, offset=40).reshape((header.num_xyz, 4))
		frames.append(frame)
		frame_offset += header.framesize

	#
	# load the glcmds
	#
	# The C stores these as ints, with the texture coordinates being floats
	# punned into the same array. Decode them here into a plain list of
	# count, then (s float, t float, index_xyz int) per vertex, ending with 0.
	glcmds = []
	glcmds_counts = [] # Q2PORT: see header.glcmds_counts below
	glcmds_st = []
	glcmds_xyz = []
	cmd_offset = header.ofs_glcmds
	cmd_end = header.ofs_glcmds + header.num_glcmds * 4
	while cmd_offset < cmd_end:
		count = struct.unpack_from("<i", buff, cmd_offset)[0]
		cmd_offset += 4
		glcmds.append(count)
		if not count:
			break
		glcmds_counts.append(count)
		for _ in range(abs(count)):
			s, t, index_xyz = struct.unpack_from("<ffi", buff, cmd_offset)
			cmd_offset += 12
			glcmds.extend((s, t, index_xyz))
			glcmds_st.append((s, t))
			glcmds_xyz.append(index_xyz)

	if glcmds and glcmds[-1] != 0:
		clientserver.Com_Printf("{}: Entity {} has possible last element issues with {} verts.\n".format("Mod_LoadMD2", mod_name, glcmds[-1]))

	# register all skins
	skinnames = []
	for i in range(header.num_skins):
		offset = header.ofs_skins + i * files_h.MAX_SKINNAME
		name = buff[offset:offset + files_h.MAX_SKINNAME].split(b'\x00', 1)[0].decode("ascii", "ignore")
		skinnames.append(name)
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
	# Q2PORT: the glcmds again as arrays, so the renderers can draw a whole
	# model with numpy instead of walking the fans and strips vertex by vertex
	# (much faster in python). glcmds_counts is the signed count of each
	# fan (< 0) or strip (> 0), glcmds_st and glcmds_xyz the (s, t) and
	# index_xyz of all their vertices in order. glcmds_tris is the triangle
	# index list the renderer builds from these on the first draw.
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

	sprite = files_h.dsprite_t()
	sprite.load(buff)

	if sprite.version != files_h.SPRITE_VERSION:
		clientserver.Com_Printf("{} has wrong version number ({} should be {})\n".format(mod_name, sprite.version, files_h.SPRITE_VERSION))
		return None

	if sprite.numframes > files_h.MAX_MD2SKINS:
		clientserver.Com_Printf("{} has too many frames ({} > {}), extra frames will be ignored\n".format(mod_name, sprite.numframes, files_h.MAX_MD2SKINS))
		sprite.numframes = files_h.MAX_MD2SKINS

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
	r_leaftovis = [0] * files_h.MAX_MAP_LEAFS
	r_vistoleaf = [0] * files_h.MAX_MAP_LEAFS
	in_obj = files_h.dnode_t()

	if l.filelen % files_h.dnode_t.packed_size():
		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}\n".format("Mod_LoadNodes", name))

	count = l.filelen // files_h.dnode_t.packed_size()
	#out = Hunk_Alloc(count * sizeof(*out));
	nodes[0] = []
	numnodes[0] = count

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dnode_t.packed_size()
		in_offset2 = in_offset + files_h.dnode_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

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
		in_offset = l.fileofs + i * files_h.dnode_t.packed_size()
		in_offset2 = in_offset + files_h.dnode_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])
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

	if not l.filelen:
		vis[0] = None
		return

	in_offset = l.fileofs
	in_offset2 = in_offset + l.filelen
	buffer = mod_base[in_offset:in_offset2]

	vis_obj = files_h.dvis_t()
	vis_obj.load(buffer)
	vis[0] = vis_obj

"""
=================
Mod_LoadVertexes

extra for skybox
=================
"""
def Mod_LoadVertexes(name, vertexes, numvertexes, mod_base, l, extra): #const char *, mvertex_t **, int *, const byte *, const lump_t *, int

	in_obj = files_h.dvertex_t()

	if l.filelen % files_h.dvertex_t.packed_size():
		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}\n".format("Mod_LoadVertexes", name))
	count = l.filelen // files_h.dvertex_t.packed_size()
	#out = Hunk_Alloc((count + extra)*sizeof(*out));
	out = []
	for i in range(count):

		in_offset = l.fileofs + i * files_h.dvertex_t.packed_size()
		in_offset2 = in_offset + files_h.dvertex_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

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

	if not l.filelen:
		lightdata[0] = None
		return

	in_offset = l.fileofs
	in_offset2 = in_offset + l.filelen
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

	in_obj = files_h.texinfo_t()

	if l.filelen % files_h.texinfo_t.packed_size():
		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}\n".format("Mod_LoadTexinfo", name))
	count = l.filelen // files_h.texinfo_t.packed_size()
	out = []
	texinfo[0] = out
	numtexinfo[0] = count

	for i in range(count):

		in_offset = l.fileofs + i * files_h.texinfo_t.packed_size()
		in_offset2 = in_offset + files_h.texinfo_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

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

	in_obj = files_h.dedge_t()

	if l.filelen % files_h.dedge_t.packed_size():
		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}\n".format("Mod_LoadEdges", name))
	count = l.filelen // files_h.dedge_t.packed_size()
	out = []
	for i in range(count):

		in_offset = l.fileofs + i * files_h.dedge_t.packed_size()
		in_offset2 = in_offset + files_h.dedge_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

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

	in_obj = files_h.dplane_t()

	if l.filelen % files_h.dplane_t.packed_size():
		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}\n".format("Mod_LoadPlanes", name))
	count = l.filelen // files_h.dplane_t.packed_size()
	out = []
	for i in range(count):

		in_offset = l.fileofs + i * files_h.dplane_t.packed_size()
		in_offset2 = in_offset + files_h.dplane_t.packed_size()
		in_obj.load(mod_base[in_offset:in_offset2])

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

	if l.filelen % 4:
		clientserver.Com_Error(shared.ERR_DROP, "{}: funny lump size in {}\n".format("Mod_LoadSurfedges", name))
	count = l.filelen // 4
	out = []
	for i in range(count):
		in_offset = l.fileofs + i * 4
		out.append(shared_c.LittleSLong(mod_base[in_offset:in_offset + 4]))

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
	if l.filelen % inSize:
		return 0

	count = l.filelen // inSize + extra
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
