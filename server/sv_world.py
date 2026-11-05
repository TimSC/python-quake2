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
import numpy as np
from game import q_shared, game
from server import sv_init, sv_game
from qcommon import cmodel, qcommon, common
"""
// world.c -- world query functions

#include "server.h"

/*
===============================================================================

ENTITY AREA CHECKING

FIXME: this use of "area" is different from the bsp file use
===============================================================================
*/

// (type *)STRUCT_FROM_LINK(link_t *link, type, member)
// ent = STRUCT_FROM_LINK(link,entity_t,order)
// FIXME: remove this mess!
#define	STRUCT_FROM_LINK(l,t,m) ((t *)((byte *)l - (int)&(((t *)0).m)))

#define	EDICT_FROM_AREA(l) STRUCT_FROM_LINK(l,edict_t,area)
"""

#typedef struct
#{
#	int		axis;		// -1 = leaf node
#	float		dist;
#	struct areanode_s	*children[2];
#	link_t	trigger_edicts;
#	link_t	solid_edicts;
#} areanode_t;
class areanode_t(object):

	def __init__(self):
		self.clear()

	def clear(self):
		self.axis = None # int, -1 = leaf node
		self.dist = None #float
		self.children = [None, None] #struct areanode_s	*[2]
		self.trigger_edicts = game.link_t()
		self.solid_edicts = game.link_t()

AREA_DEPTH = 4
AREA_NODES = 32

sv_areanodes = []
for i in range(AREA_NODES):
	sv_areanodes.append(areanode_t())
sv_numareanodes = 0 #int
"""
float	*area_mins, *area_maxs;
edict_t	**area_list;
int		area_count, area_maxcount;

"""
area_mins = None #float *
area_maxs = None #float *
area_list = None #edict_t **
area_count = 0 #int
area_maxcount = 0 #int
area_type = 0 #int


# ClearLink is used for new headnodes
def ClearLink (l): #link_t *
	l.prev = l.next = l


def RemoveLink (l): #link_t *
	l.next.prev = l.prev
	l.prev.next = l.next


def InsertLinkBefore (l, before): #link_t *, link_t *
	l.next = before
	l.prev = before.prev
	l.prev.next = l
	l.next.prev = l


"""
===============
SV_CreateAreaNode

Builds a uniformly subdivided tree for the given world size
===============
"""
def SV_CreateAreaNode (depth, mins, maxs): #int, vec3_t, vec3_t

	global sv_numareanodes

	"""
	areanode_t	*anode;
	vec3_t		size;
	vec3_t		mins1, maxs1, mins2, maxs2;
	"""
	size = np.zeros((3,), dtype=np.float32)
	mins1 = np.zeros((3,), dtype=np.float32)
	maxs1 = np.zeros((3,), dtype=np.float32)
	mins2 = np.zeros((3,), dtype=np.float32)
	maxs2 = np.zeros((3,), dtype=np.float32)

	anode = sv_areanodes[sv_numareanodes]
	sv_numareanodes += 1

	ClearLink (anode.trigger_edicts)
	ClearLink (anode.solid_edicts)

	if depth == AREA_DEPTH:
		anode.axis = -1
		anode.children[0] = anode.children[1] = None
		return anode

	q_shared.VectorSubtract (maxs, mins, size)
	if size[0] > size[1]:
		anode.axis = 0
	else:
		anode.axis = 1

	anode.dist = 0.5 * (maxs[anode.axis] + mins[anode.axis])
	q_shared.VectorCopy (mins, mins1)
	q_shared.VectorCopy (mins, mins2)
	q_shared.VectorCopy (maxs, maxs1)
	q_shared.VectorCopy (maxs, maxs2)

	maxs1[anode.axis] = anode.dist
	mins2[anode.axis] = anode.dist

	anode.children[0] = SV_CreateAreaNode (depth+1, mins2, maxs2)
	anode.children[1] = SV_CreateAreaNode (depth+1, mins1, maxs1)

	return anode


"""
===============
SV_ClearWorld

===============
"""
def SV_ClearWorld ():

	global sv_areanodes, sv_numareanodes

	for n in sv_areanodes:
		n.clear()
	sv_numareanodes = 0
	SV_CreateAreaNode (0, sv_init.sv.models[1].mins, sv_init.sv.models[1].maxs)


"""
===============
SV_UnlinkEdict

===============
"""
def SV_UnlinkEdict (ent): #edict_t *

	if not ent.area.prev:
		return		# not linked in anywhere
	RemoveLink (ent.area)
	ent.area.prev = ent.area.next = None


"""
===============
SV_LinkEdict

===============
"""
MAX_TOTAL_ENT_LEAFS = 128
def SV_LinkEdict (ent): #edict_t *

	"""
	areanode_t	*node;
	int			leafs[MAX_TOTAL_ENT_LEAFS];
	int			clusters[MAX_TOTAL_ENT_LEAFS];
	int			num_leafs;
	int			i, j, k;
	int			area;
	int			topnode;
	"""
	leafs = [0]*MAX_TOTAL_ENT_LEAFS
	clusters = [0]*MAX_TOTAL_ENT_LEAFS
	topnode = [0]

	if ent.area.prev:
		SV_UnlinkEdict (ent)	# unlink from old position

	if ent is sv_game.ge.edicts:
		return		# don't add the world

	if not ent.inuse:
		return

	# set the size
	q_shared.VectorSubtract (ent.maxs, ent.mins, ent.size)

	# encode the size into the entity_state for client prediction
	if ent.solid == game.SOLID_BBOX and not (ent.svflags & game.SVF_DEADMONSTER):
		# assume that x/y are equal and symetric
		i = int(ent.maxs[0]/8)
		if i < 1:
			i = 1
		if i > 31:
			i = 31

		# z is not symetric
		j = int(-ent.mins[2]/8)
		if j < 1:
			j = 1
		if j > 31:
			j = 31

		# and z maxs can be negative...
		k = int((ent.maxs[2]+32)/8)
		if k < 1:
			k = 1
		if k > 63:
			k = 63

		ent.s.solid = (k<<10) | (j<<5) | i

	elif ent.solid == game.SOLID_BSP:
		ent.s.solid = 31		# a solid_bbox will never create this value
	else:
		ent.s.solid = 0

	# set the abs box
	if (ent.solid == game.SOLID_BSP and
		(ent.s.angles[0] or ent.s.angles[1] or ent.s.angles[2])):
		# expand for rotation
		maxv = 0
		for i in range(3):
			v = math.fabs(ent.mins[i])
			if v > maxv:
				maxv = v
			v = math.fabs(ent.maxs[i])
			if v > maxv:
				maxv = v
		for i in range(3):
			ent.absmin[i] = ent.s.origin[i] - maxv
			ent.absmax[i] = ent.s.origin[i] + maxv

	else:
		# normal
		q_shared.VectorAdd (ent.s.origin, ent.mins, ent.absmin)
		q_shared.VectorAdd (ent.s.origin, ent.maxs, ent.absmax)

	# because movement is clipped an epsilon away from an actual edge,
	# we must fully check even when bounding boxes don't quite touch
	ent.absmin[0] -= 1
	ent.absmin[1] -= 1
	ent.absmin[2] -= 1
	ent.absmax[0] += 1
	ent.absmax[1] += 1
	ent.absmax[2] += 1

	# link to PVS leafs
	ent.num_clusters = 0
	ent.areanum = 0
	ent.areanum2 = 0

	# get all leafs, including solids
	num_leafs = cmodel.CM_BoxLeafnums (ent.absmin, ent.absmax,
		leafs, MAX_TOTAL_ENT_LEAFS, topnode)

	# set areas
	for i in range(num_leafs):
		clusters[i] = cmodel.CM_LeafCluster (leafs[i])
		area = cmodel.CM_LeafArea (leafs[i])
		if area:
			# doors may legally straggle two areas,
			# but nothing should evern need more than that
			if ent.areanum and ent.areanum != area:
				if ent.areanum2 and ent.areanum2 != area and sv_init.sv.state == sv_init.server_state_t.ss_loading:
					common.Com_DPrintf ("Object touching 3 areas at %f %f %f\n" % (
						ent.absmin[0], ent.absmin[1], ent.absmin[2]))
				ent.areanum2 = area
			else:
				ent.areanum = area

	if num_leafs >= MAX_TOTAL_ENT_LEAFS:
		# assume we missed some leafs, and mark by headnode
		ent.num_clusters = -1
		ent.headnode = topnode[0]

	else:
		ent.num_clusters = 0
		for i in range(num_leafs):
			if clusters[i] == -1:
				continue		# not a visible leaf
			j = 0
			while j < i and clusters[j] != clusters[i]:
				j += 1
			if j == i:
				if ent.num_clusters == game.MAX_ENT_CLUSTERS:
					# assume we missed some leafs, and mark by headnode
					ent.num_clusters = -1
					ent.headnode = topnode[0]
					break

				ent.clusternums[ent.num_clusters] = clusters[i]
				ent.num_clusters += 1

	# if first time, make sure old_origin is valid
	if not ent.linkcount:
		q_shared.VectorCopy (ent.s.origin, ent.s.old_origin)

	ent.linkcount += 1

	if ent.solid == game.SOLID_NOT:
		return

	# find the first node that the ent's box crosses
	node = sv_areanodes[0]
	while True:
		if node.axis == -1:
			break
		if ent.absmin[node.axis] > node.dist:
			node = node.children[0]
		elif ent.absmax[node.axis] < node.dist:
			node = node.children[1]
		else:
			break		# crosses the node

	# link it in
	ent.area.owner = ent
	if ent.solid == game.SOLID_TRIGGER:
		InsertLinkBefore (ent.area, node.trigger_edicts)
	else:
		InsertLinkBefore (ent.area, node.solid_edicts)


"""
====================
SV_AreaEdicts_r

====================
"""
def SV_AreaEdicts_r (node): #areanode_t *

	global area_count

	"""
	link_t		*l, *next, *start;
	edict_t		*check;
	int			count;
	"""
	count = 0

	# touch linked edicts
	if area_type == q_shared.AREA_SOLID:
		start = node.solid_edicts
	else:
		start = node.trigger_edicts

	l = start.next
	while l != start:
		next_l = l.next
		check = l.owner

		if check.solid == game.SOLID_NOT:
			l = next_l
			continue		# deactivated
		if (check.absmin[0] > area_maxs[0]
		or check.absmin[1] > area_maxs[1]
		or check.absmin[2] > area_maxs[2]
		or check.absmax[0] < area_mins[0]
		or check.absmax[1] < area_mins[1]
		or check.absmax[2] < area_mins[2]):
			l = next_l
			continue		# not touching

		if area_count == area_maxcount:
			common.Com_Printf ("SV_AreaEdicts: MAXCOUNT\n")
			return

		area_list[area_count] = check
		area_count += 1
		l = next_l

	if node.axis == -1:
		return		# terminal node

	# recurse down both sides
	if area_maxs[node.axis] > node.dist:
		SV_AreaEdicts_r (node.children[0])
	if area_mins[node.axis] < node.dist:
		SV_AreaEdicts_r (node.children[1])


"""
================
SV_AreaEdicts
================
"""
def SV_AreaEdicts (mins, maxs, list_, maxcount, areatype): #vec3_t, vec3_t, edict_t **, int, int

	global area_mins, area_maxs, area_list, area_count, area_maxcount, area_type

	area_mins = mins
	area_maxs = maxs
	area_list = list_
	area_count = 0
	area_maxcount = maxcount
	area_type = areatype

	SV_AreaEdicts_r (sv_areanodes[0])

	return area_count


"""
//===========================================================================
"""
"""
=============
SV_PointContents
=============
"""
def SV_PointContents (p): #vec3_t

	"""
	edict_t		*touch[MAX_EDICTS], *hit;
	int			i, num;
	int			contents, c2;
	int			headnode;
	float		*angles;
	"""
	touch = [None]*q_shared.MAX_EDICTS
	contents = 0
	c2 = 0

	# get base contents from world
	contents = cmodel.CM_PointContents (p, sv_init.sv.models[1].headnode)

	# or in contents from all the other entities
	num = SV_AreaEdicts (p, p, touch, q_shared.MAX_EDICTS, q_shared.AREA_SOLID)

	for i in range(num):
		hit = touch[i]

		# might intersect, so do an exact clip
		headnode = SV_HullForEntity (hit)
		angles = hit.s.angles
		if hit.solid != game.SOLID_BSP:
			angles = q_shared.vec3_origin	# boxes don't rotate

		c2 = cmodel.CM_TransformedPointContents (p, headnode, hit.s.origin, hit.s.angles)

		contents |= c2

	return contents


"""
typedef struct
{
	vec3_t		boxmins, boxmaxs;// enclose the test object along entire move
	float		*mins, *maxs;	// size of the moving object
	vec3_t		mins2, maxs2;	// size when clipping against mosnters
	float		*start, *end;
	trace_t		trace;
	edict_t		*passedict;
	int			contentmask;
} moveclip_t;
"""
class moveclip_t(object):

	def __init__(self):
		self.boxmins = np.zeros((3,), dtype=np.float32)
		self.boxmaxs = np.zeros((3,), dtype=np.float32)
		self.mins = None #float *, size of the moving object
		self.maxs = None #float *
		self.mins2 = np.zeros((3,), dtype=np.float32) # size when clipping against mosnters
		self.maxs2 = np.zeros((3,), dtype=np.float32)
		self.start = None #float *
		self.end = None #float *
		self.trace = q_shared.trace_t()
		self.passedict = None #edict_t *
		self.contentmask = 0 #int


"""
================
SV_HullForEntity

Returns a headnode that can be used for testing or clipping an
object of mins/maxs size.
Offset is filled in to contain the adjustment that must be added to the
testing object's origin to get a point to use with the returned hull.
================
"""
def SV_HullForEntity (ent): #edict_t *

	# decide which clipping hull to use, based on the size
	if ent.solid == game.SOLID_BSP:
		# explicit hulls in the BSP model
		model = sv_init.sv.models[ent.s.modelindex]

		if not model:
			common.Com_Error (qcommon.ERR_FATAL, "MOVETYPE_PUSH with a non bsp model")

		return model.headnode

	# create a temp hull from bounding box sizes

	return cmodel.CM_HeadnodeForBox (ent.mins, ent.maxs)


"""
//===========================================================================
"""
"""
====================
SV_ClipMoveToEntities

====================
"""
def SV_ClipMoveToEntities (clip): #moveclip_t *

	"""
	int			i, num;
	edict_t		*touchlist[MAX_EDICTS], *touch;
	trace_t		trace;
	int			headnode;
	float		*angles;
	"""
	trace = None

	touchlist = [None]*q_shared.MAX_EDICTS
	num = SV_AreaEdicts (clip.boxmins, clip.boxmaxs, touchlist,
		q_shared.MAX_EDICTS, q_shared.AREA_SOLID)

	# be careful, it is possible to have an entity in this
	# list removed before we get to it (killtriggered)
	for i in range(num):
		touch = touchlist[i]
		if touch.solid == game.SOLID_NOT:
			continue
		if touch is clip.passedict:
			continue
		if clip.trace.allsolid:
			return
		if clip.passedict:
			if touch.owner is clip.passedict:
				continue	# don't clip against own missiles
			if clip.passedict.owner is touch:
				continue	# don't clip against owner

		if not (clip.contentmask & q_shared.CONTENTS_DEADMONSTER) \
		and (touch.svflags & game.SVF_DEADMONSTER):
			continue

		# might intersect, so do an exact clip
		headnode = SV_HullForEntity (touch)
		angles = touch.s.angles
		if touch.solid != game.SOLID_BSP:
			angles = q_shared.vec3_origin	# boxes don't rotate

		if touch.svflags & game.SVF_MONSTER:
			trace = cmodel.CM_TransformedBoxTrace (clip.start, clip.end,
				clip.mins2, clip.maxs2, headnode, clip.contentmask,
				touch.s.origin, angles)
		else:
			trace = cmodel.CM_TransformedBoxTrace (clip.start, clip.end,
				clip.mins, clip.maxs, headnode, clip.contentmask,
				touch.s.origin, angles)

		if trace.allsolid or trace.startsolid \
		or trace.fraction < clip.trace.fraction:
			trace.ent = touch
			if clip.trace.startsolid:
				clip.trace = trace
				clip.trace.startsolid = True
			else:
				clip.trace = trace
		elif trace.startsolid:
			clip.trace.startsolid = True


"""
==================
SV_TraceBounds
==================
"""
def SV_TraceBounds (start, mins, maxs, end, boxmins, boxmaxs): #vec3_t, vec3_t, vec3_t, vec3_t, vec3_t, vec3_t

	#int i
	for i in range(3):
		if end[i] > start[i]:
			boxmins[i] = start[i] + mins[i] - 1
			boxmaxs[i] = end[i] + maxs[i] + 1
		else:
			boxmins[i] = end[i] + mins[i] - 1
			boxmaxs[i] = start[i] + maxs[i] + 1


"""
==================
SV_Trace

Moves the given mins/maxs volume through the world from start to end.

Passedict and edicts owned by passedict are explicitly not checked.

==================
"""
def SV_Trace (start, mins, maxs, end, passedict, contentmask): #vec3_t, vec3_t, vec3_t, vec3_t, edict_t *, int

	#moveclip_t clip

	clip = moveclip_t()

	if mins is None:
		mins = q_shared.vec3_origin
	if maxs is None:
		maxs = q_shared.vec3_origin

	# clip to world
	clip.trace = cmodel.CM_BoxTrace (start, end, mins, maxs, 0, contentmask)
	clip.trace.ent = sv_game.ge.edicts[0]
	if clip.trace.fraction == 0:
		return clip.trace		# blocked by the world

	clip.contentmask = contentmask
	clip.start = start
	clip.end = end
	clip.mins = mins
	clip.maxs = maxs
	clip.passedict = passedict

	q_shared.VectorCopy (mins, clip.mins2)
	q_shared.VectorCopy (maxs, clip.maxs2)

	# create the bounding box of the entire move
	SV_TraceBounds (start, clip.mins2, clip.maxs2, end, clip.boxmins, clip.boxmaxs)

	# clip to other solid entities
	SV_ClipMoveToEntities (clip)

	return clip.trace
