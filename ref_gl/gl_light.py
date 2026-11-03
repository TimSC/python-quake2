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
from game import q_shared
from qcommon import qfiles
from ref_gl import gl_rmain, gl_model_h
"""
// r_light.c

#include "gl_local.h"
"""
r_dlightframecount = None #int

DLIGHT_CUTOFF = 64


def _lightstyle_values(style_idx):
    lightstyles = getattr(gl_rmain.r_newrefdef, "lightstyles", None)
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
	pass
	"""
	int		i, j;
	float	a;
	vec3_t	v;
	float	rad;

	rad = light->intensity * 0.35;

	VectorSubtract (light->origin, r_origin, v);
#if 0
	// FIXME?
	if (VectorLength (v) < rad)
	{	// view is inside the dlight
		V_AddBlend (light->color[0], light->color[1], light->color[2], light->intensity * 0.0003, v_blend);
		return;
	}
#endif

	qglBegin (GL_TRIANGLE_FAN);
	qglColor3f (light->color[0]*0.2, light->color[1]*0.2, light->color[2]*0.2);
	for (i=0 ; i<3 ; i++)
		v[i] = light->origin[i] - vpn[i]*rad;
	qglVertex3fv (v);
	qglColor3f (0,0,0);
	for (i=16 ; i>=0 ; i--)
	{
		a = i/16.0 * M_PI*2;
		for (j=0 ; j<3 ; j++)
			v[j] = light->origin[j] + vright[j]*cos(a)*rad
				+ vup[j]*sin(a)*rad;
		qglVertex3fv (v);
	}
	qglEnd ();
	"""


"""
=============
R_RenderDlights
=============
"""
def R_RenderDlights ():
	pass
	"""
	int		i;
	dlight_t	*l;

	if (!gl_flashblend->value)
		return;

	r_dlightframecount = r_framecount + 1;	// because the count hasn't
											//  advanced yet for this frame
	qglDepthMask (0);
	qglDisable (GL_TEXTURE_2D);
	qglShadeModel (GL_SMOOTH);
	qglEnable (GL_BLEND);
	qglBlendFunc (GL_ONE, GL_ONE);

	l = r_newrefdef.dlights;
	for (i=0 ; i<r_newrefdef.num_dlights ; i++, l++)
		R_RenderDlight (l);

	qglColor3f (1,1,1);
	qglDisable (GL_BLEND);
	qglEnable (GL_TEXTURE_2D);
	qglBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
	qglDepthMask (1);
	"""


"""
=============================================================================

DYNAMIC LIGHTS

=============================================================================
"""

"""
=============
R_MarkLights
=============
"""
def R_MarkLights (light, bit, node): #dlight_t *, int, mnode_t *
	pass
	"""
	cplane_t	*splitplane;
	float		dist;
	msurface_t	*surf;
	int			i;
	
	if (node->contents != -1)
		return;

	splitplane = node->plane;
	dist = DotProduct (light->origin, splitplane->normal) - splitplane->dist;
	
	if (dist > light->intensity-DLIGHT_CUTOFF)
	{
		R_MarkLights (light, bit, node->children[0]);
		return;
	}
	if (dist < -light->intensity+DLIGHT_CUTOFF)
	{
		R_MarkLights (light, bit, node->children[1]);
		return;
	}
		
// mark the polygons
	surf = r_worldmodel->surfaces + node->firstsurface;
	for (i=0 ; i<node->numsurfaces ; i++, surf++)
	{
		if (surf->dlightframe != r_dlightframecount)
		{
			surf->dlightbits = 0;
			surf->dlightframe = r_dlightframecount;
		}
		surf->dlightbits |= bit;
	}

	R_MarkLights (light, bit, node->children[0]);
	R_MarkLights (light, bit, node->children[1]);
	"""


"""
=============
R_PushDlights
=============
"""
def R_PushDlights ():
	pass
	"""
	int		i;
	dlight_t	*l;

	if (gl_flashblend->value)
		return;

	r_dlightframecount = r_framecount + 1;	// because the count hasn't
											//  advanced yet for this frame
	l = r_newrefdef.dlights;
	for (i=0 ; i<r_newrefdef.num_dlights ; i++, l++)
		R_MarkLights ( l, 1<<i, r_worldmodel->nodes );
	"""


"""
=============================================================================

LIGHT SAMPLING

=============================================================================
"""
pointcolor = np.zeros((3,), dtype=np.float32)
lightplane = None #cplane_t *, used as shadow plane
lightspot = np.zeros((3,), dtype=np.float32)


def RecursiveLightPoint (node, start, end): #mnode_t *, vec3_t, vec3_t (returns int)

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
	front = q_shared.DotProduct (start, plane.normal) - plane.dist
	back = q_shared.DotProduct (end, plane.normal) - plane.dist
	side = 1 if front < 0 else 0
	
	if (back < 0) == side:
		return RecursiveLightPoint (node.children[side], start, end)
	
	frac = front / (front-back)
	mid = np.zeros((3,), dtype=np.float32)
	mid[0] = start[0] + (end[0] - start[0])*frac
	mid[1] = start[1] + (end[1] - start[1])*frac
	mid[2] = start[2] + (end[2] - start[2])*frac
	
	# go down front side	
	r = RecursiveLightPoint (node.children[side], start, mid)
	if r >= 0:
		return r		# hit something
		
	if (back < 0) == side:
		return -1		# didn't hit anuthing
		
	# check for impact on this node
	q_shared.VectorCopy (mid, lightspot)
	lightplane = plane

	surfaces = gl_rmain.r_worldmodel.surfaces
	for i in range(node.numsurfaces):
	
		surf = surfaces[node.firstsurface + i]
		if surf.flags&(gl_model_h.SURF_DRAWTURB|gl_model_h.SURF_DRAWSKY):
			continue	# no lightmaps

		tex = surf.texinfo
		
		s = int(q_shared.DotProduct (mid, tex.vecs[0]) + tex.vecs[0][3])
		t = int(q_shared.DotProduct (mid, tex.vecs[1]) + tex.vecs[1][3])

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
		q_shared.VectorClear (pointcolor) # VectorCopy (vec3_origin, pointcolor)
		if lightmap is not None:
		
			scale = [0.0, 0.0, 0.0] #vec3_t

			lightmap_p = 3*(dt * ((surf.extents[0]>>4)+1) + ds)

			maps = 0
			while maps < qfiles.MAXLIGHTMAPS and surf.styles[maps] != 255:
			
				for j in range(3):
					scale[j] = gl_rmain.gl_modulate.value*gl_rmain.r_newrefdef.lightstyles[surf.styles[maps]].rgb[j]

				pointcolor[0] += lightmap[lightmap_p+0] * scale[0] * (1.0/255)
				pointcolor[1] += lightmap[lightmap_p+1] * scale[1] * (1.0/255)
				pointcolor[2] += lightmap[lightmap_p+2] * scale[2] * (1.0/255)
				lightmap_p += 3*((surf.extents[0]>>4)+1) * \
						((surf.extents[1]>>4)+1)
				maps += 1
			
		return 1
	
	# go down back side
	return RecursiveLightPoint (node.children[1 - side], mid, end)


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
	
	if gl_rmain.r_worldmodel.lightdata is None:
	
		color[0] = color[1] = color[2] = 1.0
		return
	
	end = np.zeros((3,), dtype=np.float32)
	end[0] = p[0]
	end[1] = p[1]
	end[2] = p[2] - 2048
	
	r = RecursiveLightPoint (gl_rmain.r_worldmodel.nodes[0], p, end)
	
	if r == -1:
		q_shared.VectorClear (color) # VectorCopy (vec3_origin, color)
	else:
		q_shared.VectorCopy (pointcolor, color)

	#
	# add dynamic lights
	#
	dist = np.zeros((3,), dtype=np.float32)
	dlights = gl_rmain.r_newrefdef.dlights
	for lnum in range(gl_rmain.r_newrefdef.num_dlights):
	
		dl = dlights[lnum]
		q_shared.VectorSubtract (gl_rmain.currententity.origin,
						dl.origin,
						dist)
		add = dl.intensity - q_shared.VectorLength(dist)
		add *= (1.0/256)
		if add > 0:
			q_shared.VectorMA (color, add, dl.color, color)
	
	q_shared.VectorScale (color, gl_rmain.gl_modulate.value, color)


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
	if not surf or not surf.texinfo:
		return

	smax = (surf.extents[0] >> 4) + 1
	tmax = (surf.extents[1] >> 4) + 1
	tex = surf.texinfo

	for lnum in range(getattr(gl_rmain.r_newrefdef, "num_dlights", 0)):
		if not (surf.dlightbits & (1 << lnum)):
			continue

		dl = gl_rmain.r_newrefdef.dlights[lnum]
		frad = dl.intensity
		fdist = q_shared.DotProduct(dl.origin, surf.plane.normal) - surf.plane.dist
		frad -= abs(fdist)

		fminlight = DLIGHT_CUTOFF
		if frad < fminlight:
			continue
		fminlight = frad - fminlight

		impact = dl.origin.copy()
		for i in range(3):
			impact[i] -= surf.plane.normal[i] * fdist

		local0 = q_shared.DotProduct(impact, tex.vecs[0]) + tex.vecs[0][3] - surf.texturemins[0]
		local1 = q_shared.DotProduct(impact, tex.vecs[1]) + tex.vecs[1][3] - surf.texturemins[1]

		for t in range(tmax):
			ftacc = t * 16.0
			td = local1 - ftacc
			if td < 0:
				td = -td
			for s in range(smax):
				fsacc = s * 16.0
				sd = q_shared.Q_ftol(local0 - fsacc)
				if sd < 0:
					sd = -sd
				if sd > td:
					fdist2 = sd + (td * 0.5)
				else:
					fdist2 = td + (sd * 0.5)
				if fdist2 < fminlight:
					base = (t * smax + s) * 3
					add = frad - fdist2
					s_blocklights[base + 0] += add * dl.color[0]
					s_blocklights[base + 1] += add * dl.color[1]
					s_blocklights[base + 2] += add * dl.color[2]

"""
** R_SetCacheState
"""
def R_SetCacheState (surf): #msurface_t *
	if not surf or not hasattr(surf, "styles"):
		return

	for maps in range(qfiles.MAXLIGHTMAPS):
		style_idx = surf.styles[maps] if maps < len(surf.styles) else 255
		if style_idx == 255:
			break
		_, white = _lightstyle_values(style_idx)
		surf.cached_light[maps] = white

def R_BuildLightMap (surf, dest, stride): #msurface_t *, byte *, int
	if not surf or not surf.texinfo:
		return

	flags = surf.texinfo.flags
	forbidden = (q_shared.SURF_SKY | q_shared.SURF_TRANS33 | q_shared.SURF_TRANS66 | q_shared.SURF_WARP)
	if flags & forbidden:
		gl_rmain.ri.Sys_Error(q_shared.ERR_DROP, "R_BuildLightMap called for non-lit surface")

	smax = (surf.extents[0] >> 4) + 1
	tmax = (surf.extents[1] >> 4) + 1
	size = smax * tmax
	max_size = len(s_blocklights) // 3
	if size > max_size:
		gl_rmain.ri.Sys_Error(q_shared.ERR_DROP, "Bad s_blocklights size")

	modulate = gl_rmain.gl_modulate.value if gl_rmain.gl_modulate else 1.0
	lightmap_data = surf.samples
	if lightmap_data is None:
		for idx in range(size * 3):
			s_blocklights[idx] = 255.0
	else:
		if isinstance(lightmap_data, (bytes, bytearray)):
			lightmap_data = memoryview(lightmap_data)
		nummaps = 0
		while nummaps < qfiles.MAXLIGHTMAPS:
			style_idx = surf.styles[nummaps] if nummaps < len(surf.styles) else 255
			if style_idx == 255:
				break
			nummaps += 1

		lightmap_offset = 0
		if nummaps == 1:
			for maps in range(qfiles.MAXLIGHTMAPS):
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
			for maps in range(qfiles.MAXLIGHTMAPS):
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

	if surf.dlightframe == gl_rmain.r_framecount:
		R_AddDynamicLights(surf)

	stride = int(stride)
	dest_view = memoryview(dest)
	dest_idx = 0	
	bl_idx = 0
	monolightmap = '0'
	if gl_rmain.gl_monolightmap and getattr(gl_rmain.gl_monolightmap, "string", None):
		monolightmap = gl_rmain.gl_monolightmap.string[0]
	monolightmap = monolightmap.upper() if monolightmap else '0'

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
			r = q_shared.Q_ftol(s_blocklights[bl_idx])
			g = q_shared.Q_ftol(s_blocklights[bl_idx + 1])
			b = q_shared.Q_ftol(s_blocklights[bl_idx + 2])
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

			if monolightmap == '0':
				val_r, val_g, val_b, val_a = r, g, b, a
			else:
				if monolightmap in ('L', 'I'):
					val_r, val_g, val_b = a, 0, 0
					val_a = a
				elif monolightmap == 'C':
					val_a = 255 - ((r + g + b) / 3.0)
					if val_a == 0:
						val_r = val_g = val_b = 0
					else:
						val_r = r * (val_a / 255.0)
						val_g = g * (val_a / 255.0)
						val_b = b * (val_a / 255.0)
				else:
					val_r = val_g = val_b = 0
					val_a = 255 - a
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
