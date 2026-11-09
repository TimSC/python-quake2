"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 * Copyright (C) 2016-2017 Daniel Gibson
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
 * gl3_light.c - dynamic lights for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
from client.refresh.gl1 import gl1_light
from client.refresh.gl3 import gl3_main
from client.refresh.gl3.header import local


def RI_MarkSurfaceLights (light, bit, node, r_dlightframecount): #dlight_t *, int, mnode_t *, int

	gl1_light.R_MarkSurfaceLights (light, bit, node, r_dlightframecount)


def RI_PushDlights (fd): #refdef_t *

	"""
	Q2PORT: copy the frame's dynamic lights into the uniLights UBO.
	"""
	data = gl3_main.gl3state.uniLightsData
	n = fd.num_dlights
	if n > 32:
		n = 32
	i = 0
	while i < n:
		dl = fd.dlights[i]
		base = i * 8
		data[base] = dl.origin[0]
		data[base + 1] = dl.origin[1]
		data[base + 2] = dl.origin[2]
		data[base + 3] = 0.0 # _padding
		data[base + 4] = dl.color[0] * dl.intensity
		data[base + 5] = dl.color[1] * dl.intensity
		data[base + 6] = dl.color[2] * dl.intensity
		data[base + 7] = dl.intensity
		i += 1
	data[local.UNILIGHTS_NUM] = n
	gl3_shaders_UpdateUBOLights ()


def gl3_shaders_UpdateUBOLights (): #void

	from client.refresh.gl3 import gl3_shaders
	gl3_shaders.GL3_UpdateUBOLights ()


def RI_LightPoint (currententity, p, color): #entity_t *, vec3_t, vec3_t

	# Q2PORT: gl1 reads the current entity from its globals
	gl1_light.R_LightPoint (p, color)


def RI_BuildLightMap (surf, dest, stride): #msurface_t *, byte *, int

	gl1_light.R_BuildLightMap (surf, dest, stride)
