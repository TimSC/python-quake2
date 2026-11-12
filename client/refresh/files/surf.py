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
 * Surface logic
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
from client.refresh import ref_shared


"""
===============
R_TextureAnimation

Returns the proper texture for a given time and base texture
===============
"""
def R_TextureAnimation(currententity, tex): #const entity_t *, const mtexinfo_t * (returns struct image_s *)

	if not tex.next:
		return tex.image

	if not currententity:
		return tex.image

	c = currententity.frame % tex.numframes
	while c and tex:
		tex = tex.next
		c -= 1

	return tex.image


def R_AreaVisible(areabits, pleaf): #const byte *, mleaf_t * (returns qboolean)

	# check for door connected areas
	if not areabits:
		return True

	area = pleaf.area

	if (areabits[area >> 3] & (1 << (area & 7))):
		return True

	return False # not visible

"""
=============
R_MarkLights

bit: 1 << i for light number i, will be or'ed into msurface_t::dlightbits
if surface is affected by this light
=============
"""
def R_MarkLights(light, bit, node, lightframecount, mark_surface_lights): #dlight_t *, int, mnode_t *, int, marksurfacelights_t

	if node.contents != ref_shared.CONTENTS_NODE:
		return

	splitplane = node.plane
	dist = shared.DotProduct(light.origin, splitplane.normal) - splitplane.dist

	intensity = light.intensity

	if dist > intensity - ref_shared.DLIGHT_CUTOFF:	# (dist > light->intensity)
		R_MarkLights(light, bit, node.children[0], lightframecount, mark_surface_lights)
		return

	if dist < -intensity + ref_shared.DLIGHT_CUTOFF:	# (dist < -light->intensity)
		R_MarkLights(light, bit, node.children[1], lightframecount, mark_surface_lights)
		return

	mark_surface_lights(light, bit, node, lightframecount)

	R_MarkLights(light, bit, node.children[0], lightframecount, mark_surface_lights)
	R_MarkLights(light, bit, node.children[1], lightframecount, mark_surface_lights)

def BOX_ON_PLANE_SIDE(emins, emaxs, p): #macro (returns int)
	# the C macro handles axial planes inline and delegates the general
	# case to BoxOnPlaneSide
	if p.type < 3:
		if p.dist <= emins[p.type]:
			return ref_shared.SIDE_FRONT
		if p.dist >= emaxs[p.type]:
			return ref_shared.SIDE_BACK
		return 3
	return shared_c.BoxOnPlaneSide(emins, emaxs, p)


"""
* Returns true if the box is completely outside the frustum
"""
def R_CullBox(mins, maxs, frustum): #vec3_t, vec3_t, cplane_t * (returns qboolean)

	for i in range(4):
		if BOX_ON_PLANE_SIDE(mins, maxs, frustum[i]) == ref_shared.SIDE_ON:
			return True

	return False

def R_SignbitsForPlane(out): #cplane_t * (returns int)

	bits = 0

	# for fast box on planeside test
	for j in range(3):
		if out.normal[j] < 0:
			bits |= 1 << j

	return bits

def R_SetFrustum(vup, vpn, vright, r_origin, fov_x, fov_y, frustum): #vec3_t, vec3_t, vec3_t, vec3_t, float, float, cplane_t *

	# rotate VPN right by FOV_X/2 degrees
	shared_c.RotatePointAroundVector(frustum[0].normal, vup, vpn, -(90 - fov_x / 2))
	# rotate VPN left by FOV_X/2 degrees
	shared_c.RotatePointAroundVector(frustum[1].normal, vup, vpn, 90 - fov_x / 2)
	# rotate VPN up by FOV_X/2 degrees
	shared_c.RotatePointAroundVector(frustum[2].normal, vright, vpn, 90 - fov_y / 2)
	# rotate VPN down by FOV_X/2 degrees
	shared_c.RotatePointAroundVector(frustum[3].normal, vright, vpn, -(90 - fov_y / 2))

	for i in range(4):
		frustum[i].type = files_h.PLANE_ANYZ
		frustum[i].dist = shared.DotProduct(r_origin, frustum[i].normal)
		frustum[i].signbits = R_SignbitsForPlane(frustum[i])
		frustum[i].normal_l = frustum[i].normal.tolist() # Q2PORT: for BoxOnPlaneSide(), once per frame rather than per call
