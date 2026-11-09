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
import OpenGL.GL as GL
pass
pass
from client.refresh.gl1 import gl1_main
from client.refresh.gl1.header import model
from client.refresh.files import surf as files_surf
from common.header import files as files_h
from common.header import shared
from common.shared import shared as shared_c
"""
// r_light.c

#include "gl_local.h"
"""
r_dlightframecount = None #int

DLIGHT_CUTOFF = 64


def _lightstyle_values(style_idx):
    lightstyles = getattr(gl1_main.r_newrefdef, "lightstyles", None)
    if not lightstyles:
        return (1.0, 1.0, 1.0), 1.0
    if style_idx >= len(lightstyles):
        return (1.0, 1.0, 1.0), 1.0
    style = lightstyles[style_idx]
    if style is None:
        return (1.0, 1.0, 1.0), 1.0
    if isinstance(style, dict):
        rgb = tuple(style.get("rgb", (1.0, 1.0, 1.0)))
        white = style.get("white", max(rgb))
    else:
        rgb = tuple(getattr(style, "rgb", (1.0, 1.0, 1.0)))
        white = getattr(style, "white", max(rgb))
    return rgb, white


"""
=============================================================================

DYNAMIC LIGHTS BLEND RENDERING

=============================================================================
"""
def R_RenderDlight (light): #dlight_t *

	"""
	int		i, j;
	float	a;
	vec3_t	v;
	float	rad;
	"""
	v = np.zeros((3,), dtype=np.float32)

	rad = light.intensity * 0.35

	shared.VectorSubtract (light.origin, gl1_main.r_origin, v)
	"""
#if 0
	// FIXME?
	if (VectorLength (v) < rad)
	{	// view is inside the dlight
		V_AddBlend (light->color[0], light->color[1], light->color[2], light->intensity * 0.0003, v_blend);
		return;
	}
#endif
	"""

	GL.glBegin (GL.GL_TRIANGLE_FAN)
	GL.glColor3f (light.color[0]*0.2, light.color[1]*0.2, light.color[2]*0.2)
	for i in range(3):
		v[i] = light.origin[i] - gl1_main.vpn[i]*rad
	GL.glVertex3fv (v)
	GL.glColor3f (0,0,0)
	for i in range(16, -1, -1):
	
		a = i/16.0 * math.pi*2
		for j in range(3):
			v[j] = light.origin[j] + gl1_main.vright[j]*math.cos(a)*rad \
				+ gl1_main.vup[j]*math.sin(a)*rad
		GL.glVertex3fv (v)
	
	GL.glEnd ()


"""
=============
R_RenderDlights
=============
"""
def R_RenderDlights ():

	global r_dlightframecount

	#int		i;
	#dlight_t	*l;

	if not gl1_main.gl1_flashblend.value:
		return

	r_dlightframecount = gl1_main.r_framecount + 1	# because the count hasn't
											#  advanced yet for this frame
	GL.glDepthMask (0)
	GL.glDisable (GL.GL_TEXTURE_2D)
	GL.glShadeModel (GL.GL_SMOOTH)
	GL.glEnable (GL.GL_BLEND)
	GL.glBlendFunc (GL.GL_ONE, GL.GL_ONE)

	for i in range(gl1_main.r_newrefdef.num_dlights):
		R_RenderDlight (gl1_main.r_newrefdef.dlights[i])

	GL.glColor3f (1,1,1)
	GL.glDisable (GL.GL_BLEND)
	GL.glEnable (GL.GL_TEXTURE_2D)
	GL.glBlendFunc (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
	GL.glDepthMask (1)


"""
=============================================================================

DYNAMIC LIGHTS

=============================================================================
"""

"""
=============
R_MarkSurfaceLights
=============
"""
def R_MarkSurfaceLights (light, bit, node, lightframecount): #dlight_t *, int, mnode_t *, int

	"""
	msurface_t *surf;
	int i;
	"""

	# mark the polygons
	surfaces = gl1_main.r_worldmodel.surfaces
	for i in range(node.numsurfaces):

		#int sidebit;
		#float dist;
		surf = surfaces[node.firstsurface + i]
		dist = shared.DotProduct (light.origin, surf.plane.normal) - surf.plane.dist
		if dist >= 0:
			sidebit = 0
		else:
			sidebit = model.SURF_PLANEBACK
		if (surf.flags & model.SURF_PLANEBACK) != sidebit:
			continue
		if surf.dlightframe != lightframecount:
			surf.dlightbits = 0
			surf.dlightframe = lightframecount
		surf.dlightbits |= bit


"""
=============
R_PushDlights
=============
"""
def R_PushDlights ():

	global r_dlightframecount

	#int		i;
	#dlight_t	*l;

	if gl1_main.gl1_flashblend.value:
		return

	r_dlightframecount = gl1_main.r_framecount + 1	# because the count hasn't
											#  advanced yet for this frame
	for i in range(gl1_main.r_newrefdef.num_dlights):
		files_surf.R_MarkLights ( gl1_main.r_newrefdef.dlights[i], 1<<i,
			gl1_main.r_worldmodel.nodes[0], r_dlightframecount, R_MarkSurfaceLights )


"""
=============================================================================

LIGHT SAMPLING

=============================================================================
"""
pointcolor = np.zeros((3,), dtype=np.float32)
lightplane = None #cplane_t *, used as shadow plane
lightspot = np.zeros((3,), dtype=np.float32)


def R_RecursiveLightPoint (node, start, end): #mnode_t *, vec3_t, vec3_t (returns int)

	global lightplane

	"""
	float		front, back, frac;
	int			side;
	cplane_t	*plane;
	vec3_t		mid;
	msurface_t	*surf;
	int			s, t, ds, dt;
	int			i;
	mtexinfo_t	*tex;
	byte		*lightmap;
	int			maps;
	int			r;
	"""

	if node.contents != -1:
		return -1		# didn't hit anything
	
	# calculate mid point

	# FIXME: optimize for axial
	plane = node.plane
	front = shared.DotProduct (start, plane.normal) - plane.dist
	back = shared.DotProduct (end, plane.normal) - plane.dist
	side = 1 if front < 0 else 0
	
	if (back < 0) == side:
		return R_RecursiveLightPoint (node.children[side], start, end)
	
	frac = front / (front-back)
	mid = np.zeros((3,), dtype=np.float32)
	mid[0] = start[0] + (end[0] - start[0])*frac
	mid[1] = start[1] + (end[1] - start[1])*frac
	mid[2] = start[2] + (end[2] - start[2])*frac
	
	# go down front side	
	r = R_RecursiveLightPoint (node.children[side], start, mid)
	if r >= 0:
		return r		# hit something
		
	if (back < 0) == side:
		return -1		# didn't hit anuthing
		
	# check for impact on this node
	shared.VectorCopy (mid, lightspot)
	lightplane = plane

	surfaces = gl1_main.r_worldmodel.surfaces
	for i in range(node.numsurfaces):
	
		surf = surfaces[node.firstsurface + i]
		if surf.flags&(model.SURF_DRAWTURB|model.SURF_DRAWSKY):
			continue	# no lightmaps

		tex = surf.texinfo
		
		s = int(shared.DotProduct (mid, tex.vecs[0]) + tex.vecs[0][3])
		t = int(shared.DotProduct (mid, tex.vecs[1]) + tex.vecs[1][3])

		if s < surf.texturemins[0] or t < surf.texturemins[1]:
			continue
		
		ds = s - surf.texturemins[0]
		dt = t - surf.texturemins[1]
		
		if ds > surf.extents[0] or dt > surf.extents[1]:
			continue

		if surf.samples is None:
			return 0

		ds >>= 4
		dt >>= 4

		lightmap = surf.samples
		shared.VectorClear (pointcolor) # VectorCopy (vec3_origin, pointcolor)
		if lightmap is not None:
		
			scale = [0.0, 0.0, 0.0] #vec3_t

			lightmap_p = 3*(dt * ((surf.extents[0]>>4)+1) + ds)

			maps = 0
			while maps < files_h.MAXLIGHTMAPS and surf.styles[maps] != 255:
			
				for j in range(3):
					scale[j] = gl1_main.r_modulate.value*gl1_main.r_newrefdef.lightstyles[surf.styles[maps]].rgb[j]

				pointcolor[0] += lightmap[lightmap_p+0] * scale[0] * (1.0/255)
				pointcolor[1] += lightmap[lightmap_p+1] * scale[1] * (1.0/255)
				pointcolor[2] += lightmap[lightmap_p+2] * scale[2] * (1.0/255)
				lightmap_p += 3*((surf.extents[0]>>4)+1) * \
						((surf.extents[1]>>4)+1)
				maps += 1
			
		return 1
	
	# go down back side
	return R_RecursiveLightPoint (node.children[1 - side], mid, end)


"""
===============
R_LightPoint
===============
"""
def R_LightPoint (p, color): #vec3_t, vec3_t

	"""
	vec3_t		end;
	float		r;
	int			lnum;
	dlight_t	*dl;
	float		light;
	vec3_t		dist;
	float		add;
	"""
	
	if gl1_main.r_worldmodel.lightdata is None:
	
		color[0] = color[1] = color[2] = 1.0
		return
	
	end = np.zeros((3,), dtype=np.float32)
	end[0] = p[0]
	end[1] = p[1]
	end[2] = p[2] - 2048
	
	r = R_RecursiveLightPoint (gl1_main.r_worldmodel.nodes[0], p, end)
	
	if r == -1:
		shared.VectorClear (color) # VectorCopy (vec3_origin, color)
	else:
		shared.VectorCopy (pointcolor, color)

	#
	# add dynamic lights
	#
	dist = np.zeros((3,), dtype=np.float32)
	dlights = gl1_main.r_newrefdef.dlights
	for lnum in range(gl1_main.r_newrefdef.num_dlights):
	
		dl = dlights[lnum]
		shared.VectorSubtract (gl1_main.currententity.origin,
						dl.origin,
						dist)
		add = dl.intensity - shared_c.VectorLength(dist)
		add *= (1.0/256)
		if add > 0:
			shared_c.VectorMA (color, add, dl.color, color)
	
	shared_c.VectorScale (color, gl1_main.r_modulate.value, color)


"""
//===================================================================

static float s_blocklights[34*34*3];
"""
s_blocklights = [0.0] * (34 * 34 * 3)


"""
===============
R_AddDynamicLights
===============
"""
def R_AddDynamicLights (surf): #msurface_t *

	"""
	int			lnum;
	int			sd, td;
	float		fdist, frad, fminlight;
	vec3_t		impact, local;
	int			s, t;
	int			i;
	int			smax, tmax;
	mtexinfo_t	*tex;
	dlight_t	*dl;
	float		*pfBL;
	float		fsacc, ftacc;
	"""
	impact = np.zeros((3,), dtype=np.float32)
	local = [0.0, 0.0]

	smax = (surf.extents[0]>>4)+1
	tmax = (surf.extents[1]>>4)+1
	tex = surf.texinfo

	for lnum in range(gl1_main.r_newrefdef.num_dlights):
	
		if not (surf.dlightbits & (1<<lnum) ):
			continue		# not lit by this light

		dl = gl1_main.r_newrefdef.dlights[lnum]
		frad = dl.intensity
		fdist = shared.DotProduct (dl.origin, surf.plane.normal) - \
				surf.plane.dist
		frad -= abs(fdist)
		# rad is now the highest intensity on the plane

		fminlight = DLIGHT_CUTOFF	# FIXME: make configurable?
		if frad < fminlight:
			continue
		fminlight = frad - fminlight

		for i in range(3):
		
			impact[i] = dl.origin[i] - \
					surf.plane.normal[i]*fdist
		
		local[0] = shared.DotProduct (impact, tex.vecs[0]) + tex.vecs[0][3] - surf.texturemins[0]
		local[1] = shared.DotProduct (impact, tex.vecs[1]) + tex.vecs[1][3] - surf.texturemins[1]

		pfBL = 0 # index into s_blocklights
		ftacc = 0
		for t in range(tmax):
		
			td = int(local[1] - ftacc)
			if td < 0:
				td = -td

			fsacc = 0
			for s in range(smax):
			
				sd = shared.Q_ftol( local[0] - fsacc )

				if sd < 0:
					sd = -sd

				if sd > td:
					fdist = sd + (td>>1)
				else:
					fdist = td + (sd>>1)

				if fdist < fminlight:
				
					s_blocklights[pfBL+0] += ( frad - fdist ) * dl.color[0]
					s_blocklights[pfBL+1] += ( frad - fdist ) * dl.color[1]
					s_blocklights[pfBL+2] += ( frad - fdist ) * dl.color[2]
				
				fsacc += 16
				pfBL += 3
			
			ftacc += 16
		

"""
** R_SetCacheState
"""
def R_SetCacheState (surf): #msurface_t *
	if not surf or not hasattr(surf, "styles"):
		return

	for maps in range(files_h.MAXLIGHTMAPS):
		style_idx = surf.styles[maps] if maps < len(surf.styles) else 255
		if style_idx == 255:
			break
		_, white = _lightstyle_values(style_idx)
		surf.cached_light[maps] = white

def R_BuildLightMap (surf, dest, stride): #msurface_t *, byte *, int
	if not surf or not surf.texinfo:
		return

	flags = surf.texinfo.flags
	forbidden = (shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66 | shared.SURF_WARP)
	if flags & forbidden:
		gl1_main.ri.Sys_Error(shared.ERR_DROP, "R_BuildLightMap called for non-lit surface")

	smax = (surf.extents[0] >> 4) + 1
	tmax = (surf.extents[1] >> 4) + 1
	size = smax * tmax
	max_size = len(s_blocklights) // 3
	if size > max_size:
		gl1_main.ri.Sys_Error(shared.ERR_DROP, "Bad s_blocklights size")

	modulate = gl1_main.r_modulate.value if gl1_main.r_modulate else 1.0
	lightmap_data = surf.samples
	if lightmap_data is None:
		for idx in range(size * 3):
			s_blocklights[idx] = 255.0
	else:
		if isinstance(lightmap_data, (bytes, bytearray)):
			lightmap_data = memoryview(lightmap_data)
		nummaps = 0
		while nummaps < files_h.MAXLIGHTMAPS:
			style_idx = surf.styles[nummaps] if nummaps < len(surf.styles) else 255
			if style_idx == 255:
				break
			nummaps += 1

		lightmap_offset = 0
		if nummaps == 1:
			for maps in range(files_h.MAXLIGHTMAPS):
				style_idx = surf.styles[maps] if maps < len(surf.styles) else 255
				if style_idx == 255:
					break
				scale_rgb, _ = _lightstyle_values(style_idx)
				scale = [modulate * c for c in scale_rgb]
				all_one = all(abs(scale[i] - 1.0) < 1e-6 for i in range(3))
				for i in range(size):
					idx = i * 3
					if all_one:
						s_blocklights[idx + 0] = float(lightmap_data[lightmap_offset + idx + 0])
						s_blocklights[idx + 1] = float(lightmap_data[lightmap_offset + idx + 1])
						s_blocklights[idx + 2] = float(lightmap_data[lightmap_offset + idx + 2])
					else:
						s_blocklights[idx + 0] = lightmap_data[lightmap_offset + idx + 0] * scale[0]
						s_blocklights[idx + 1] = lightmap_data[lightmap_offset + idx + 1] * scale[1]
						s_blocklights[idx + 2] = lightmap_data[lightmap_offset + idx + 2] * scale[2]
				lightmap_offset += size * 3
		else:
			for idx in range(size * 3):
				s_blocklights[idx] = 0.0
			for maps in range(files_h.MAXLIGHTMAPS):
				style_idx = surf.styles[maps] if maps < len(surf.styles) else 255
				if style_idx == 255:
					break
				scale_rgb, _ = _lightstyle_values(style_idx)
				scale = [modulate * c for c in scale_rgb]
				all_one = all(abs(scale[i] - 1.0) < 1e-6 for i in range(3))
				for i in range(size):
					idx = i * 3
					if all_one:
						s_blocklights[idx + 0] += float(lightmap_data[lightmap_offset + idx + 0])
						s_blocklights[idx + 1] += float(lightmap_data[lightmap_offset + idx + 1])
						s_blocklights[idx + 2] += float(lightmap_data[lightmap_offset + idx + 2])
					else:
						s_blocklights[idx + 0] += lightmap_data[lightmap_offset + idx + 0] * scale[0]
						s_blocklights[idx + 1] += lightmap_data[lightmap_offset + idx + 1] * scale[1]
						s_blocklights[idx + 2] += lightmap_data[lightmap_offset + idx + 2] * scale[2]
				lightmap_offset += size * 3

	if surf.dlightframe == gl1_main.r_framecount:
		R_AddDynamicLights(surf)

	stride = int(stride)
	dest_view = memoryview(dest)
	dest_idx = 0	
	bl_idx = 0

	def _clamp(value):
		value = int(value)
		if value < 0:
			return 0
		if value > 255:
			return 255
		return value

	for _ in range(tmax):
		row_base = dest_idx
		for _ in range(smax):
			r = shared.Q_ftol(s_blocklights[bl_idx])
			g = shared.Q_ftol(s_blocklights[bl_idx + 1])
			b = shared.Q_ftol(s_blocklights[bl_idx + 2])
			if r < 0: r = 0
			if g < 0: g = 0
			if b < 0: b = 0
			maxc = r if r > g else g
			if b > maxc:
				maxc = b
			a = maxc
			if maxc > 255:
				t = 255.0 / maxc
				r *= t
				g *= t
				b *= t
				a *= t

			val_r, val_g, val_b, val_a = r, g, b, a
			val_r = _clamp(val_r)
			val_g = _clamp(val_g)
			val_b = _clamp(val_b)
			val_a = _clamp(val_a)
			dest_view[row_base + 0] = val_r
			dest_view[row_base + 1] = val_g
			dest_view[row_base + 2] = val_b
			dest_view[row_base + 3] = val_a
			row_base += 4
			bl_idx += 3
		dest_idx += stride
