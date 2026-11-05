"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

The collision model. Slaps "boxes" through the world and checks if
they collide with the world model, entities or other boxes.

=======================================================================
"""
from __future__ import annotations

import struct
import numpy as np
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cvar
from common import filesystem
from common import md4
from common import crc as crc_mod

"""
#include <stdint.h>
#include "header/common.h"
"""

class cnode_t(object):

	def __init__(self):
		self.plane = None #cplane_t *
		self.children = [None, None] # int[2], negative numbers are leafs

class cbrushside_t(object):

	def __init__(self):
		self.plane = None #cplane_t *
		self.surface = None #mapsurface_t *


class cleaf_t(object):

	def __init__(self):
		self.contents: int = None
		self.cluster: int = None
		self.area: int = None
		self.firstleafbrush: int = 0 #unsigned short	
		self.numleafbrushes: int = 0 #unsigned short	


class cbrush_t(object):

	def __init__(self):
		self.contents: int = None
		self.numsides: int = None
		self.firstbrushside: int = None
		self.checkcount: int = None		# to avoid repeated testings


class carea_t(object):

	def __init__(self):
		self.numareaportals: int = None
		self.firstareaportal: int = None
		self.floodnum: int = None			# if two areas have equal floodnums, they are connected
		self.floodvalid: int = None


checkcount: int = 0

map_name: str = None # char		[MAX_QPATH];

numbrushsides: int = None
map_brushsides = []
for i in range(files_h.MAX_MAP_BRUSHSIDES):
	map_brushsides.append(cbrushside_t())

numtexinfo: int = None
map_surfaces = []
for i in range(files_h.MAX_MAP_TEXINFO):
	map_surfaces.append(shared.mapsurface_t())

numplanes: int = None
map_planes = []
for i in range(files_h.MAX_MAP_PLANES+6): # extra for box hull
	map_planes.append(shared.cplane_t())

numnodes: int = None
map_nodes = []
for i in range(files_h.MAX_MAP_NODES+6): # extra for box hull
	map_nodes.append(cnode_t())

numleafs: int = 1	# allow leaf funcs to be called without a map
map_leafs = []
for i in range(files_h.MAX_MAP_LEAFS):
	map_leafs.append(cleaf_t())
emptyleaf: int = None
solidleaf: int = None

numleafbrushes: int = None
map_leafbrushes = []
for i in range(files_h.MAX_MAP_LEAFBRUSHES):
	map_leafbrushes.append(None) # unsigned short

numcmodels: int = None
map_cmodels = []
for i in range(files_h.MAX_MAP_MODELS):
	map_cmodels.append(shared.cmodel_t())

numbrushes: int = None
map_brushes = []
for i in range(files_h.MAX_MAP_BRUSHES):
	map_brushes.append(cbrush_t())

numvisibility: int = None
map_visibility = None

map_vis = files_h.dvis_t()

numentitychars: int = None
map_entitystring = None

numareas: int = 1
map_areas = []
for i in range(files_h.MAX_MAP_AREAS):
	map_areas.append(carea_t())

numareaportals: int = None
map_areaportals = []
for i in range(files_h.MAX_MAP_AREAPORTALS):
	map_areaportals.append(files_h.dareaportal_t())

numclusters: int = 1

nullsurface = shared.mapsurface_t()

floodvalid = 0

portalopen = [] #qboolean[MAX_MAP_AREAPORTALS];
for i in range(files_h.MAX_MAP_AREAPORTALS):
	portalopen.append(False)

map_noareas = None # cvar_t	*


c_pointcontents: int = 0
c_traces: int = 0
c_brush_traces: int = 0
last_checksum = None


cmod_base = None # byte*
def FloodArea_r(area: carea_t, floodnum: int):
	if area.floodvalid == floodvalid:
		if area.floodnum == floodnum:
			return
		clientserver.Com_Error(shared.ERR_DROP, "FloodArea_r: reflooded")

	area.floodnum = floodnum
	area.floodvalid = floodvalid

	first_portal = area.firstareaportal if area.firstareaportal is not None else 0
	num_portals = area.numareaportals if area.numareaportals is not None else 0
	for i in range(num_portals):
		portal = map_areaportals[first_portal + i]
		if portalopen[portal.portalnum]:
			FloodArea_r(map_areas[portal.otherarea], floodnum)


def FloodAreaConnections():
	global floodvalid

	floodvalid += 1
	floodnum = 0

	for i in range(1, numareas):
		area = map_areas[i]
		if area.floodvalid == floodvalid:
			continue
		floodnum += 1
		FloodArea_r(area, floodnum)


def CM_SetAreaPortalState(portalnum, open_):
	if portalnum > numareaportals:
		clientserver.Com_Error(shared.ERR_DROP, "areaportal > numareaportals")

	portalopen[portalnum] = bool(open_)
	FloodAreaConnections()


def CM_AreasConnected(area1, area2):
	if map_noareas is not None and map_noareas.value:
		return True

	if area1 > numareas or area2 > numareas:
		clientserver.Com_Error(shared.ERR_DROP, "area > numareas")

	return map_areas[area1].floodnum == map_areas[area2].floodnum


def CM_WriteAreaBits(buffer, area):
	bytes_count = (numareas + 7) >> 3
	if len(buffer) < bytes_count:
		raise ValueError("buffer too small")

	if map_noareas is not None and map_noareas.value:
		for i in range(bytes_count):
			buffer[i] = 0xff
	else:
		for i in range(bytes_count):
			buffer[i] = 0

		floodnum = map_areas[area].floodnum
		for i in range(numareas):
			if map_areas[i].floodnum == floodnum or not area:
				buffer[i >> 3] |= 1 << (i & 7)

	return bytes_count


def CM_WritePortalState(f):
	if f is None:
		return
	f.write(bytes(1 if x else 0 for x in portalopen))


def CM_ReadPortalState(f):
	if f is None:
		return

	data = filesystem.FS_Read(len(portalopen), f)
	if len(data) != len(portalopen):
		clientserver.Com_Error(shared.ERR_DROP, "CM_ReadPortalState: short read")
	for i, value in enumerate(data):
		portalopen[i] = bool(value)
	FloodAreaConnections()


def CM_HeadnodeVisible(nodenum, visbits):
	if nodenum < 0:
		leafnum = -1 - nodenum
		if leafnum >= numleafs:
			return False
		cluster = map_leafs[leafnum].cluster
		if cluster == -1:
			return False
		return bool(visbits[cluster >> 3] & (1 << (cluster & 7)))

	node = map_nodes[nodenum]
	if CM_HeadnodeVisible(node.children[0], visbits):
		return True
	return CM_HeadnodeVisible(node.children[1], visbits)
DIST_EPSILON = 0.03125
trace_start = np.zeros((3,), dtype=np.float32)
trace_end = np.zeros((3,), dtype=np.float32)
trace_mins = np.zeros((3,), dtype=np.float32)
trace_maxs = np.zeros((3,), dtype=np.float32)
trace_extents = np.zeros((3,), dtype=np.float32)

trace_trace = shared.trace_t()
trace_contents = 0
trace_ispoint = False

def _copy_plane(dst, src):
    dst.normal[:] = src.normal
    dst.dist = src.dist
    dst.type = src.type
    dst.signbits = src.signbits
    dst.pad[0] = src.pad[0]
    dst.pad[1] = src.pad[1]

box_planes = None # cplane_t*
box_headnode = None # int			
box_brush = None #cbrush_t *
box_leaf = None # cleaf_t *

"""
===================
CM_InitBoxHull

Set up the planes and nodes so that the six floats of a bounding box
can just be stored out and get a proper clipping hull structure.
===================
"""
def CM_InitBoxHull():

	global box_headnode, box_brush, box_leaf, box_planes

	box_headnode = numnodes
	box_planes = map_planes[numplanes:]

	box_brush = map_brushes[numbrushes]
	box_brush.numsides = 6
	box_brush.firstbrushside = numbrushsides
	box_brush.contents = shared.CONTENTS_MONSTER

	box_leaf = map_leafs[numleafs]
	box_leaf.contents = shared.CONTENTS_MONSTER
	box_leaf.firstleafbrush = numleafbrushes
	box_leaf.numleafbrushes = 1

	map_leafbrushes[numleafbrushes] = numbrushes

	for i in range(6):
		side = i & 1

		s = map_brushsides[numbrushsides + i]
		s.plane = map_planes[numplanes + i * 2 + side]
		s.surface = nullsurface

		c = map_nodes[box_headnode + i]
		c.plane = map_planes[numplanes + i * 2]
		c.children[side] = -1 - emptyleaf
		if i != 5:
			c.children[side ^ 1] = box_headnode + i + 1
		else:
			c.children[side ^ 1] = -1 - numleafs

		p = box_planes[i * 2]
		p.type = i >> 1
		p.signbits = 0
		shared.VectorClear(p.normal)
		p.normal[i >> 1] = 1

		p = box_planes[i * 2 + 1]
		p.type = 3 + (i >> 1)
		p.signbits = 0
		shared.VectorClear(p.normal)
		p.normal[i >> 1] = -1
def CM_HeadnodeForBox(mins, maxs):

	box_planes[0].dist = maxs[0]
	box_planes[1].dist = -maxs[0]
	box_planes[2].dist = mins[0]
	box_planes[3].dist = -mins[0]
	box_planes[4].dist = maxs[1]
	box_planes[5].dist = -maxs[1]
	box_planes[6].dist = mins[1]
	box_planes[7].dist = -mins[1]
	box_planes[8].dist = maxs[2]
	box_planes[9].dist = -maxs[2]
	box_planes[10].dist = mins[2]
	box_planes[11].dist = -mins[2]

	return box_headnode
def CM_PointLeafnum_r(p, num):

	global c_pointcontents

	if num is None:
		return 0

	while num >= 0:
		node = map_nodes[num]
		plane = node.plane

		if plane.type < 3:
			d = p[plane.type] - plane.dist
		else:
			d = shared.DotProduct(plane.normal, p) - plane.dist
		if d < 0:
			num = node.children[1]
		else:
			num = node.children[0]

	c_pointcontents += 1

	return -1 - num


def CM_PointLeafnum(p):
	if not numplanes:
		return 0
	return CM_PointLeafnum_r(p, 0)

leaf_count = 0
leaf_maxcount = 0
leaf_list = None
leaf_mins = None
leaf_maxs = None
leaf_topnode = -1

def CM_BoxLeafnums_r(nodenum):
	global leaf_count, leaf_topnode

	while True:
		if nodenum < 0:
			if leaf_count >= leaf_maxcount:
				return
			leaf_list[leaf_count] = -1 - nodenum
			leaf_count += 1
			return

		node = map_nodes[nodenum]
		plane = node.plane
		s = shared_c.BoxOnPlaneSide(leaf_mins, leaf_maxs, plane)
		if s == 1:
			nodenum = node.children[0]
		elif s == 2:
			nodenum = node.children[1]
		else:
			if leaf_topnode == -1:
				leaf_topnode = nodenum
			CM_BoxLeafnums_r(node.children[0])
			nodenum = node.children[1]
			continue

	return


def CM_BoxLeafnums_headnode(mins, maxs, list_, listsize, headnode, topnode):
	global leaf_list, leaf_count, leaf_maxcount, leaf_mins, leaf_maxs, leaf_topnode

	leaf_list = list_
	leaf_count = 0
	leaf_maxcount = listsize
	leaf_mins = mins
	leaf_maxs = maxs
	leaf_topnode = -1

	CM_BoxLeafnums_r(headnode)

	if topnode is not None:
		if isinstance(topnode, list) and topnode:
			topnode[0] = leaf_topnode
		else:
			try:
				topnode[0] = leaf_topnode
			except Exception:
				pass

	return leaf_count


def CM_BoxLeafnums(mins, maxs, list_, listsize, topnode):
	return CM_BoxLeafnums_headnode(mins, maxs, list_, listsize, map_cmodels[0].headnode, topnode)

def CM_PointContents(p, headnode):
	if not numnodes:
		return 0
	l = CM_PointLeafnum_r(p, headnode)
	return map_leafs[l].contents


pvsrow = bytearray((files_h.MAX_MAP_LEAFS + 7) // 8)
phsrow = bytearray((files_h.MAX_MAP_LEAFS + 7) // 8)


def CM_TransformedPointContents(p, headnode, origin, angles):
	pt = np.zeros((3,), dtype=np.float32)
	temp = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)

	shared.VectorSubtract(p, origin, pt)

	if headnode != box_headnode and (angles[0] or angles[1] or angles[2]):
		shared_c.AngleVectors(angles, forward, right, up)
		shared.VectorCopy(pt, temp)
		pt[0] = shared.DotProduct(temp, forward)
		pt[1] = -shared.DotProduct(temp, right)
		pt[2] = shared.DotProduct(temp, up)

	l = CM_PointLeafnum_r(pt, headnode)
	return map_leafs[l].contents


def CM_ClipBoxToBrush(mins, maxs, p1, p2, trace, brush):
    global c_brush_traces

    if not brush.numsides:
        return

    c_brush_traces += 1
    enterfrac = -1.0
    leavefrac = 1.0
    clipplane = None
    getout = False
    startout = False
    leadside = None
    ofs = [0.0, 0.0, 0.0]

    for i in range(brush.numsides):
        side = map_brushsides[brush.firstbrushside + i]
        plane = side.plane

        if not trace_ispoint:
            for j in range(3):
                ofs[j] = maxs[j] if plane.normal[j] < 0 else mins[j]
            dist = shared.DotProduct(ofs, plane.normal)
            dist = plane.dist - dist
        else:
            dist = plane.dist

        d1 = shared.DotProduct(p1, plane.normal) - dist
        d2 = shared.DotProduct(p2, plane.normal) - dist

        if d2 > 0:
            getout = True
        if d1 > 0:
            startout = True

        if d1 > 0 and d2 >= d1:
            return
        if d1 <= 0 and d2 <= 0:
            continue

        if d1 > d2:
            f = (d1 - DIST_EPSILON) / (d1 - d2)
            if f > enterfrac:
                enterfrac = f
                clipplane = plane
                leadside = side
        else:
            f = (d1 + DIST_EPSILON) / (d1 - d2)
            if f < leavefrac:
                leavefrac = f

    if not startout:
        trace.startsolid = True
        if not getout:
            trace.allsolid = True
        return

    if enterfrac < leavefrac and enterfrac > -1 and enterfrac < trace.fraction:
        frac = 0.0 if enterfrac < 0 else enterfrac
        trace.fraction = frac
        if clipplane is not None:
            _copy_plane(trace.plane, clipplane)
        if leadside and leadside.surface:
            trace.surface = leadside.surface.c
        trace.contents = brush.contents

def CM_TestBoxInBrush(mins, maxs, p1, trace, brush):
    if not brush.numsides:
        return

    ofs = [0.0, 0.0, 0.0]
    for i in range(brush.numsides):
        side = map_brushsides[brush.firstbrushside + i]
        plane = side.plane
        for j in range(3):
            ofs[j] = maxs[j] if plane.normal[j] < 0 else mins[j]
        dist = shared.DotProduct(ofs, plane.normal)
        dist = plane.dist - dist

        d1 = shared.DotProduct(p1, plane.normal) - dist
        if d1 > 0:
            return

    trace.startsolid = True
    trace.allsolid = True
    trace.fraction = 0.0
    trace.contents = brush.contents

def CM_TraceToLeaf(leafnum):
    leaf = map_leafs[leafnum]
    if not (leaf.contents & trace_contents):
        return

    for k in range(leaf.numleafbrushes):
        brushnum = map_leafbrushes[leaf.firstleafbrush + k]
        brush = map_brushes[brushnum]
        if brush.checkcount == checkcount:
            continue
        brush.checkcount = checkcount

        if not (brush.contents & trace_contents):
            continue
        CM_ClipBoxToBrush(trace_mins, trace_maxs, trace_start, trace_end, trace_trace, brush)
        if trace_trace.fraction == 0:
            return

def CM_TestInLeaf(leafnum):
    leaf = map_leafs[leafnum]
    if not (leaf.contents & trace_contents):
        return

    for k in range(leaf.numleafbrushes):
        brushnum = map_leafbrushes[leaf.firstleafbrush + k]
        brush = map_brushes[brushnum]
        if brush.checkcount == checkcount:
            continue
        brush.checkcount = checkcount

        if not (brush.contents & trace_contents):
            continue
        CM_TestBoxInBrush(trace_mins, trace_maxs, trace_start, trace_trace, brush)
        if trace_trace.fraction == 0:
            return

def CM_RecursiveHullCheck(num, p1f, p2f, p1, p2):
    if trace_trace.fraction <= p1f:
        return

    if num is None:
        return

    if num < 0:
        CM_TraceToLeaf(-1 - num)
        return

    node = map_nodes[num]
    plane = node.plane

    if plane.type < 3:
        t1 = p1[plane.type] - plane.dist
        t2 = p2[plane.type] - plane.dist
        offset = trace_extents[plane.type]
    else:
        t1 = shared.DotProduct(plane.normal, p1) - plane.dist
        t2 = shared.DotProduct(plane.normal, p2) - plane.dist
        if trace_ispoint:
            offset = 0.0
        else:
            offset = (
                abs(trace_extents[0] * plane.normal[0])
                + abs(trace_extents[1] * plane.normal[1])
                + abs(trace_extents[2] * plane.normal[2])
            )

    if t1 >= offset and t2 >= offset:
        CM_RecursiveHullCheck(node.children[0], p1f, p2f, p1, p2)
        return
    if t1 < -offset and t2 < -offset:
        CM_RecursiveHullCheck(node.children[1], p1f, p2f, p1, p2)
        return

    if t1 < t2:
        idist = 1.0 / (t1 - t2)
        side = 1
        frac2 = (t1 + offset + DIST_EPSILON) * idist
        frac = (t1 - offset + DIST_EPSILON) * idist
    elif t1 > t2:
        idist = 1.0 / (t1 - t2)
        side = 0
        frac2 = (t1 - offset - DIST_EPSILON) * idist
        frac = (t1 + offset + DIST_EPSILON) * idist
    else:
        side = 0
        frac = 1.0
        frac2 = 0.0

    frac = max(0.0, min(1.0, frac))
    midf = p1f + (p2f - p1f) * frac
    mid = np.zeros((3,), dtype=np.float32)
    for i in range(3):
        mid[i] = p1[i] + frac * (p2[i] - p1[i])

    CM_RecursiveHullCheck(node.children[side], p1f, midf, p1, mid)

    frac2 = max(0.0, min(1.0, frac2))
    midf = p1f + (p2f - p1f) * frac2
    for i in range(3):
        mid[i] = p1[i] + frac2 * (p2[i] - p1[i])

    CM_RecursiveHullCheck(node.children[side ^ 1], midf, p2f, mid, p2)

def CM_BoxTrace(start, end, mins, maxs, headnode, brushmask):
    global checkcount, c_traces, trace_contents, trace_ispoint

    checkcount += 1
    c_traces += 1

    trace_trace.allsolid = False
    trace_trace.startsolid = False
    trace_trace.fraction = 1.0
    trace_trace.contents = 0
    trace_trace.surface = nullsurface.c
    shared.VectorClear(trace_trace.plane.normal)
    trace_trace.plane.dist = 0.0
    trace_trace.plane.type = 0
    trace_trace.plane.signbits = 0
    trace_trace.plane.pad[0] = 0
    trace_trace.plane.pad[1] = 0
    trace_trace.endpos[:] = 0.0

    if not numnodes:
        return trace_trace.copy()	# trace_t is returned by value

    trace_contents = brushmask
    shared.VectorCopy(start, trace_start)
    shared.VectorCopy(end, trace_end)
    shared.VectorCopy(mins, trace_mins)
    shared.VectorCopy(maxs, trace_maxs)

    if start[0] == end[0] and start[1] == end[1] and start[2] == end[2]:
        leafs = [0] * 1024
        topnode = [0]
        c1 = np.zeros((3,), dtype=np.float32)
        c2 = np.zeros((3,), dtype=np.float32)
        shared.VectorAdd(start, mins, c1)
        shared.VectorAdd(start, maxs, c2)
        for i in range(3):
            c1[i] -= 1
            c2[i] += 1
        numleafs = CM_BoxLeafnums_headnode(c1, c2, leafs, 1024, headnode, topnode)
        for i in range(numleafs):
            CM_TestInLeaf(leafs[i])
            if trace_trace.allsolid:
                break
        shared.VectorCopy(start, trace_trace.endpos)
        return trace_trace.copy()	# trace_t is returned by value

    if (mins[0] == 0 and mins[1] == 0 and mins[2] == 0
            and maxs[0] == 0 and maxs[1] == 0 and maxs[2] == 0):
        trace_ispoint = True
        shared.VectorClear(trace_extents)
    else:
        trace_ispoint = False
        trace_extents[0] = -mins[0] if -mins[0] > maxs[0] else maxs[0]
        trace_extents[1] = -mins[1] if -mins[1] > maxs[1] else maxs[1]
        trace_extents[2] = -mins[2] if -mins[2] > maxs[2] else maxs[2]

    CM_RecursiveHullCheck(headnode, 0.0, 1.0, start, end)

    if trace_trace.fraction == 1.0:
        shared.VectorCopy(end, trace_trace.endpos)
    else:
        for i in range(3):
            trace_trace.endpos[i] = start[i] + trace_trace.fraction * (end[i] - start[i])

    return trace_trace.copy()	# trace_t is returned by value

def CM_TransformedBoxTrace(start, end, mins, maxs, headnode, brushmask, origin, angles):
    start_l = np.zeros((3,), dtype=np.float32)
    end_l = np.zeros((3,), dtype=np.float32)
    shared.VectorSubtract(start, origin, start_l)
    shared.VectorSubtract(end, origin, end_l)

    rotated = headnode != box_headnode and (angles[0] or angles[1] or angles[2])

    forward = np.zeros((3,), dtype=np.float32)
    right = np.zeros((3,), dtype=np.float32)
    up = np.zeros((3,), dtype=np.float32)
    temp = np.zeros((3,), dtype=np.float32)
    neg_angles = np.zeros((3,), dtype=np.float32)

    if rotated:
        shared_c.AngleVectors(angles, forward, right, up)

        shared.VectorCopy(start_l, temp)
        start_l[0] = shared.DotProduct(temp, forward)
        start_l[1] = -shared.DotProduct(temp, right)
        start_l[2] = shared.DotProduct(temp, up)

        shared.VectorCopy(end_l, temp)
        end_l[0] = shared.DotProduct(temp, forward)
        end_l[1] = -shared.DotProduct(temp, right)
        end_l[2] = shared.DotProduct(temp, up)

    trace = CM_BoxTrace(start_l, end_l, mins, maxs, headnode, brushmask)

    if rotated and trace.fraction != 1.0:
        shared.VectorNegate(angles, neg_angles)
        shared_c.AngleVectors(neg_angles, forward, right, up)

        shared.VectorCopy(trace.plane.normal, temp)
        trace.plane.normal[0] = shared.DotProduct(temp, forward)
        trace.plane.normal[1] = -shared.DotProduct(temp, right)
        trace.plane.normal[2] = shared.DotProduct(temp, up)

    for i in range(3):
        trace.endpos[i] = start[i] + trace.fraction * (end[i] - start[i])

    return trace
"""
// cmodel.c -- model loading

#include "qcommon.h"
"""
"""
===============================================================================

					MAP LOADING

===============================================================================
"""
"""
=================
CMod_LoadSubmodels
=================
"""
def CMod_LoadSubmodels (l): #lump_t *

	global numcmodels, map_cmodels, cmod_base
	"""
	dmodel_t	*in;
	cmodel_t	*out;
	int			i, j, count;
	"""

	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.dmodel_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.dmodel_t.packed_size()

	if count < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Map with no models")
	if count > files_h.MAX_MAP_MODELS:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many models")

	numcmodels = count
	in_obj = files_h.dmodel_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * files_h.dmodel_t.packed_size()
		in_offset2 = in_offset + files_h.dmodel_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_cmodels[i]

		for j in range(3):
			# spread the mins / maxs by a pixel
			out.mins[j] = in_obj.mins[j] - 1.0
			out.maxs[j] = in_obj.maxs[j] + 1.0
			out.origin[j] = in_obj.origin[j]
		
		out.headnode = in_obj.headnode

"""
=================
CMod_LoadSurfaces
=================
"""
def CMod_LoadSurfaces (l: files_h.lump_t):

	global numtexinfo, map_surfaces, cmod_base
	"""
	texinfo_t	*in;
	mapsurface_t	*out;
	int			i, count;
	"""

	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.texinfo_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.texinfo_t.packed_size()
	if count < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Map with no surfaces")
	if count > files_h.MAX_MAP_TEXINFO:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many surfaces")

	numtexinfo = count
	in_obj = files_h.texinfo_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * files_h.texinfo_t.packed_size()
		in_offset2 = in_offset + files_h.texinfo_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_surfaces[i]

		out.c.name = in_obj.texture
		out.rname = in_obj.texture
		out.c.flags = in_obj.flags
		out.c.value = in_obj.value

"""
=================
CMod_LoadNodes

=================
"""
def CMod_LoadNodes (l): #lump_t *
	
	global cmod_base, map_nodes, numnodes

	"""
	dnode_t		*in;
	int			child;
	cnode_t		*out;
	int			i, j, count;
	"""
	
	#in = (void *)(cmod_base + l->fileofs);
	in_offset = 0
	if l.filelen % files_h.dnode_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.dnode_t.packed_size()

	if count < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Map has no nodes")
	if count > files_h.MAX_MAP_NODES:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many nodes")

	in_obj = files_h.dnode_t()

	#out = map_nodes

	numnodes = count

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dnode_t.packed_size()
		in_offset2 = in_offset + files_h.dnode_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_nodes[i]

		out.plane = map_planes[in_obj.planenum]
		out.children[0] = in_obj.children[0]
		out.children[1] = in_obj.children[1]

"""
=================
CMod_LoadBrushes

=================
"""
def CMod_LoadBrushes (l): #lump_t *

	global map_brushes, numbrushes, cmod_base
	"""
	dbrush_t	*in;
	cbrush_t	*out;
	int			i, count;
	"""
	
	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.dbrush_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.dbrush_t.packed_size()

	if count > files_h.MAX_MAP_BRUSHES:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many brushes")

	out = map_brushes

	numbrushes = count
	in_obj = files_h.dbrush_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * files_h.dbrush_t.packed_size()
		in_offset2 = in_offset + files_h.dbrush_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_brushes[i]

		out.firstbrushside = in_obj.firstside
		out.numsides = in_obj.numsides
		out.contents = in_obj.contents
	


"""
=================
CMod_LoadLeafs
=================
"""
def CMod_LoadLeafs (l): #lump_t *

	global numclusters, map_leafs, cmod_base, numleafs, solidleaf, emptyleaf
	"""
	int			i;
	cleaf_t		*out;
	dleaf_t 	*in;
	int			count;
	"""
	
	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.dleaf_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.dleaf_t.packed_size()

	if count < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Map with no leafs")
	# need to save space for box planes
	if count > files_h.MAX_MAP_PLANES:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many planes")

	out = map_leafs
	numleafs = count
	numclusters = 0
	in_obj = files_h.dleaf_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dleaf_t.packed_size()
		in_offset2 = in_offset + files_h.dleaf_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_leafs[i]
		out.contents = in_obj.contents
		out.cluster = in_obj.cluster
		out.area = in_obj.area
		out.firstleafbrush = in_obj.firstleafbrush
		out.numleafbrushes = in_obj.numleafbrushes

		if out.cluster >= numclusters:
			numclusters = out.cluster + 1

	if map_leafs[0].contents != files_h.CONTENTS_SOLID:
		clientserver.Com_Error (shared.ERR_DROP, "Map leaf 0 is not CONTENTS_SOLID")
	solidleaf = 0
	emptyleaf = -1
	for i in range(1, numleafs):
	
		if not map_leafs[i].contents:
		
			emptyleaf = i
			break
		
	if emptyleaf == -1:
		clientserver.Com_Error (shared.ERR_DROP, "Map does not have an empty leaf")
	
"""
=================
CMod_LoadPlanes
=================
"""
def CMod_LoadPlanes (l): #lump_t *

	global map_planes, numplanes, cmod_base
	"""
	int			i, j;
	cplane_t	*out;
	dplane_t 	*in;
	int			count;
	int			bits;
	"""
	
	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.dplane_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size");
	count = l.filelen // files_h.dplane_t.packed_size()

	
	if count < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Map with no planes")
	# need to save space for box planes
	if count > files_h.MAX_MAP_PLANES:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many planes")

	numplanes = count
	in_obj = files_h.dplane_t()

	for i in range(count):
	
		in_offset = l.fileofs + i * files_h.dplane_t.packed_size()
		in_offset2 = in_offset + files_h.dplane_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_planes[i]
		bits = 0
		for j in range(3):
		
			out.normal[j] = in_obj.normal[j]
			if out.normal[j] < 0:
				bits |= 1<<j
		
		out.dist = in_obj.dist
		out.type = in_obj.type
		out.signbits = bits
	

"""
=================
CMod_LoadLeafBrushes
=================
"""
def CMod_LoadLeafBrushes (l): #lump_t *

	global map_leafbrushes, numleafbrushes, cmod_base
	"""
	int			i;
	unsigned short	*out;
	unsigned short 	*in;
	int			count;
	"""
	
	#in = (void *)(cmod_base + l->fileofs)
	if l.filelen % 2:
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // 2

	if count < 1:
		clientserver.Com_Error (shared.ERR_DROP, "Map with no planes")
	# need to save space for box planes
	if count > files_h.MAX_MAP_LEAFBRUSHES:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many leafbrushes")

	out = map_leafbrushes
	numleafbrushes = count

	for i in range(count):
		in_offset = l.fileofs + i * 2
		in_offset2 = in_offset + 2

		map_leafbrushes[i] = shared_c.LittleShort (cmod_base[in_offset:in_offset2])


"""
=================
CMod_LoadBrushSides
=================
"""
def CMod_LoadBrushSides (l): #lump_t *

	global cmod_base, map_brushsides, numbrushsides, map_planes, map_surfaces, numtexinfo
	"""
	int			i, j;
	cbrushside_t	*out;
	dbrushside_t 	*in;
	int			count;
	int			num;
	"""

	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.dbrushside_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.dbrushside_t.packed_size()

	# need to save space for box planes
	if count > files_h.MAX_MAP_BRUSHSIDES:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many planes")

	#out = map_brushsides
	numbrushsides = count
	in_obj = files_h.dbrushside_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dbrushside_t.packed_size()
		in_offset2 = in_offset + files_h.dbrushside_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])
	
		out = map_brushsides[i]

		num = in_obj.planenum
		out.plane = map_planes[num]
		j = in_obj.texinfo
		if j >= numtexinfo:
			clientserver.Com_Error (shared.ERR_DROP, "Bad brushside texinfo")
		out.surface = map_surfaces[j]
	


"""
=================
CMod_LoadAreas
=================
"""

def CMod_LoadAreas (l): #lump_t *

	global numareas, map_areas, map_areas
	"""
	int			i;
	carea_t		*out;
	darea_t 	*in;
	int			count;
	"""

	#in = (void *)(cmod_base + l->fileofs);
	if l.filelen % files_h.darea_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.darea_t.packed_size()

	if count > files_h.MAX_MAP_AREAS:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many areas")

	numareas = count
	in_obj = files_h.darea_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.darea_t.packed_size()
		in_offset2 = in_offset + files_h.darea_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_areas[i]

		out.numareaportals = in_obj.numareaportals
		out.firstareaportal = in_obj.firstareaportal
		out.floodvalid = 0
		out.floodnum = 0

"""
=================
CMod_LoadAreaPortals
=================
"""
def CMod_LoadAreaPortals (l): #lump_t *

	global numareaportals, map_areaportals, cmod_base
	"""
	int			i;
	dareaportal_t		*out;
	dareaportal_t 	*in;
	int			count;
	"""

	#in = (void *)(cmod_base + l->fileofs)
	if l.filelen % files_h.dareaportal_t.packed_size():
		clientserver.Com_Error (shared.ERR_DROP, "MOD_LoadBmodel: funny lump size")
	count = l.filelen // files_h.dareaportal_t.packed_size()

	if count > files_h.MAX_MAP_AREAS:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too many areas")

	numareaportals = count
	in_obj = files_h.dareaportal_t()

	for i in range(count):

		in_offset = l.fileofs + i * files_h.dareaportal_t.packed_size()
		in_offset2 = in_offset + files_h.dareaportal_t.packed_size()
		in_obj.load(cmod_base[in_offset:in_offset2])

		out = map_areaportals[i]
	
		out.portalnum = in_obj.portalnum
		out.otherarea = in_obj.otherarea
	

"""
=================
CMod_LoadVisibility
=================
"""
def CMod_LoadVisibility (l): #lump_t *

	global map_vis, map_visibility, numvisibility, cmod_base

	numvisibility = l.filelen
	if l.filelen > files_h.MAX_MAP_VISIBILITY:
		clientserver.Com_Error (shared.ERR_DROP, "Map has too large visibility lump")

	map_visibility = cmod_base[l.fileofs:l.fileofs+l.filelen]

	map_vis.load(map_visibility)

"""
=================
CMod_LoadEntityString
=================
"""
def CMod_LoadEntityString(l, name): #const lump_t *, const char *

	global map_entitystring, numentitychars

	from server import sv_main	# Q2PORT: imported here; sv_entfile is the server's cvar

	if sv_main.sv_entfile is not None and sv_main.sv_entfile.value:

		#char *buffer = NULL, entname[256];
		#size_t nameLen;
		buffer = None
		bufLen = -1
		entname = ""

		nameLen = len(name)
		if name[nameLen - 4:] != ".bsp" or nameLen > (shared.MAX_QPATH - 1):

			clientserver.Com_Printf("%s: unsupported map format '%s'\n", "CMod_LoadEntityString", name)

		else:

			#char namewe[MAX_QPATH];

			crc = 0

			if l.filelen > 0:
				crc = crc_mod.CRC_Block(cmod_base[l.fileofs:l.fileofs + l.filelen - 1], l.filelen - 1)


			namewe = name[:nameLen - 4]

			entname = "{}@{:04x}.ent".format(namewe, crc)[:256 - 2]

			bufLen, buffer = filesystem.FS_LoadFile(entname)
			if buffer is None:

				clientserver.Com_Printf("No fixes found as '%s'\n", entname)

				entname = "{}.ent".format(namewe)[:256 - 2]
				bufLen, buffer = filesystem.FS_LoadFile(entname)
				if buffer is not None and bufLen > 1:

					clientserver.Com_Printf("Have used '%s' file without content hash.\n", entname)




		if buffer is not None and bufLen > 1 and bufLen < files_h.MAX_MAP_ENTSTRING - 1:

			numentitychars = bufLen

			map_entitystring = buffer.decode('latin-1')
			# jit entity bug - null terminate the entity string!
			filesystem.FS_FreeFile(buffer)

			clientserver.Com_Printf(".ent file %s loaded.\n", entname)
			return

		elif bufLen != -1:

			# If the .ent file is too small or large, don't load.
			clientserver.Com_Printf("%s: .ent file %s too small.\n", "CMod_LoadEntityString", entname)
			filesystem.FS_FreeFile(buffer)



	numentitychars = l.filelen

	if l.filelen < 0:

		clientserver.Com_Error(shared.ERR_DROP, "%s: Map %s has too small entity lump", "CMod_LoadEntityString", name)


	if l.filelen >= files_h.MAX_MAP_ENTSTRING:

		clientserver.Com_Error(shared.ERR_DROP, "%s: Map %s has too large entity lump", "CMod_LoadEntityString", name)


	map_entitystring = cmod_base[l.fileofs:l.fileofs + numentitychars].decode('latin-1')
	# jit entity bug - null terminate the entity string!

	
"""
==================
CM_LoadMap

Loads in the map and all submodels
==================
"""
def CM_LoadMap (name, clientload): #char *, qboolean (returns cmodel_t *, unsigned *)

	global last_checksum
	global numplanes, numnodes, numleafs, numcmodels, numvisibility, numentitychars, map_entitystring, map_name
	global numclusters, numareas
	global map_noareas, cmod_base
	global portalopen


	#return q_shared.cmodel_t(), 0
	"""
	unsigned		*buf;
	int				i;
	dheader_t		header;
	int				length;
	static unsigned	last_checksum;
	"""
	checksum = 0 #unsigned (output)

	map_noareas = cvar.Cvar_Get ("map_noareas", "0", 0)

	if map_name == name and (clientload or int(cvar.Cvar_VariableValue ("flushmap"))):
	
		checksum = last_checksum
		if not clientload:
		
			for i in range(len(portalopen)):
				portalopen[i] = False
			FloodAreaConnections ()
		
		return map_cmodels[0], checksum # still have the right version
	
	# free old stuff
	numplanes = 0
	numnodes = 0
	numleafs = 0
	numcmodels = 0
	numvisibility = 0
	numentitychars = 0
	map_entitystring = None
	map_name = None

	if name is None or len(name) == 0:

		numleafs = 1
		numclusters = 1
		numareas = 1
		checksum = 0

		return map_cmodels[0], checksum # cinematic servers won't have anything at all

	#
	# load the file
	#
	length, buf = filesystem.FS_LoadFile (name)
	if buf is None:
		clientserver.Com_Error (shared.ERR_DROP, "Couldn't load {}".format(name))

	last_checksum = md4.Com_BlockChecksum (buf, length) # LittleLong (Com_BlockChecksum (buf, length)); Q2PORT: already a host int
	checksum = last_checksum

	header = files_h.dheader_t()
	header.parse(buf)

	if header.version != files_h.BSPVERSION:
		clientserver.Com_Error (shared.ERR_DROP, "CMod_LoadBrushModel: {} has wrong version number ({} should be {})".format( \
			name, header.version, files_h.BSPVERSION))

	cmod_base = buf

	# load into heap
	CMod_LoadSurfaces (header.lumps[files_h.LUMP_TEXINFO])
	CMod_LoadLeafs (header.lumps[files_h.LUMP_LEAFS])
	CMod_LoadLeafBrushes (header.lumps[files_h.LUMP_LEAFBRUSHES])
	CMod_LoadPlanes (header.lumps[files_h.LUMP_PLANES])
	CMod_LoadBrushes (header.lumps[files_h.LUMP_BRUSHES])
	CMod_LoadBrushSides (header.lumps[files_h.LUMP_BRUSHSIDES])
	CMod_LoadSubmodels (header.lumps[files_h.LUMP_MODELS])
	CMod_LoadNodes (header.lumps[files_h.LUMP_NODES])
	CMod_LoadAreas (header.lumps[files_h.LUMP_AREAS])
	CMod_LoadAreaPortals (header.lumps[files_h.LUMP_AREAPORTALS])
	CMod_LoadVisibility (header.lumps[files_h.LUMP_VISIBILITY])
	CMod_LoadEntityString (header.lumps[files_h.LUMP_ENTITIES], name)

	del buf, cmod_base

	CM_InitBoxHull ()

	for i in range(len(portalopen)):
		portalopen[i] = False
	FloodAreaConnections ()

	map_name = name

	return map_cmodels[0], checksum


"""
==================
CM_InlineModel
==================
"""
def CM_InlineModel(name):
	"""Return the inline model identified by *<number>."""

	if not name or not name.startswith('*'):
		clientserver.Com_Error(shared.ERR_DROP, "CM_InlineModel: bad name")

	try:
		num = int(name[1:])
	except (ValueError, TypeError):
		clientserver.Com_Error(shared.ERR_DROP, "CM_InlineModel: bad number")

	if num < 1 or num >= numcmodels:
		clientserver.Com_Error(shared.ERR_DROP, "CM_InlineModel: bad number")

	return map_cmodels[num]
def CM_NumClusters ():

	return numclusters


def CM_NumInlineModels ():

	return numcmodels


def CM_EntityString ():

	return map_entitystring

def CM_LeafContents(leafnum: int):
    if leafnum < 0 or leafnum >= numleafs:
        clientserver.Com_Error(shared.ERR_DROP, "CM_LeafContents: bad number")
    return map_leafs[leafnum].contents


def CM_LeafCluster(leafnum: int):
    if leafnum < 0 or leafnum >= numleafs:
        clientserver.Com_Error(shared.ERR_DROP, "CM_LeafCluster: bad number")
    return map_leafs[leafnum].cluster


def CM_LeafArea(leafnum: int):
    if leafnum < 0 or leafnum >= numleafs:
        clientserver.Com_Error(shared.ERR_DROP, "CM_LeafArea: bad number")
    return map_leafs[leafnum].area


#=======================================================================
def CM_DecompressVis(data, out):
	row = (numclusters + 7) >> 3
	if row <= 0:
		return

	if not data or not numvisibility:
		for i in range(row):
			out[i] = 0xff
		return

	in_index = 0
	out_index = 0
	data_len = len(data)

	while out_index < row and in_index < data_len:
		value = data[in_index]
		in_index += 1
		if value:
			out[out_index] = value
			out_index += 1
			continue

		if in_index >= data_len:
			break

		c = data[in_index]
		in_index += 1
		if out_index + c > row:
			c = row - out_index
			clientserver.Com_DPrintf("warning: Vis decompression overrun\n")
		while c and out_index < row:
			out[out_index] = 0
			out_index += 1
			c -= 1


def CM_ClusterPVS(cluster):
	row = (numclusters + 7) >> 3
	if row < 1:
		return pvsrow
	if cluster == -1:
		for i in range(row):
			pvsrow[i] = 0
		return pvsrow

	if map_vis is None or map_visibility is None:
		return pvsrow

	offset = map_vis.bitofs[cluster][files_h.DVIS_PVS]
	CM_DecompressVis(map_visibility[offset:], pvsrow)
	return pvsrow


def CM_ClusterPHS(cluster):
	row = (numclusters + 7) >> 3
	if row < 1:
		return phsrow
	if cluster == -1:
		for i in range(row):
			phsrow[i] = 0
		return phsrow

	if map_vis is None or map_visibility is None:
		return phsrow

	offset = map_vis.bitofs[cluster][files_h.DVIS_PHS]
	CM_DecompressVis(map_visibility[offset:], phsrow)
	return phsrow


