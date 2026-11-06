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

This file implements all client side lighting

=======================================================================
"""
from __future__ import annotations

import numpy as np

from common.header import shared
from client import cl_main
from client import cl_view
from client import ref
from client.header import client as client_h

"""
#include "header/client.h"
"""

class clightstyle_t(object):

	def __init__(self):

		self.clear()

	def clear(self): # Q2PORT: memset(ls, 0, sizeof(*ls))

		self.length = 0 #int
		self.value = np.zeros((3,), dtype=np.float32) #float[3]
		self.map = np.zeros((shared.MAX_QPATH,), dtype=np.float32) #float[MAX_QPATH]

cl_lightstyle = [] #clightstyle_t[MAX_LIGHTSTYLES]
for i in range(ref.MAX_LIGHTSTYLES):
	cl_lightstyle.append(clightstyle_t())
lastofs = 0 #int

def CL_ClearLightStyles(): #void

	global lastofs

	for ls in cl_lightstyle: # memset(cl_lightstyle, 0, sizeof(cl_lightstyle));
		ls.clear()
	lastofs = -1

def CL_RunLightStyles(): #void

	"""
	int ofs;
	int i;
	clightstyle_t *ls;
	"""
	global lastofs

	ofs = int(cl_main.cl.time / 100)

	if ofs == lastofs:

		return


	lastofs = ofs

	for i in range(ref.MAX_LIGHTSTYLES):

		ls = cl_lightstyle[i]
		if not ls.length:

			ls.value[0] = ls.value[1] = ls.value[2] = 1.0
			continue


		if ls.length == 1:

			ls.value[0] = ls.value[1] = ls.value[2] = ls.map[0]


		else:

			ls.value[0] = ls.value[1] = ls.value[2] = ls.map[ofs % ls.length]

def CL_SetLightstyle(i: int): #int

	"""
	char *s;
	int j, k;
	"""

	s = cl_main.cl.configstrings[i + shared.CS_LIGHTS]

	j = len(s) # (int)strlen(s)
	cl_lightstyle[i].length = j

	for k in range(j):

		cl_lightstyle[i].map[k] = float(ord(s[k]) - ord('a')) / float(ord('m') - ord('a'))

def CL_AddLightStyles(): #void

	"""
	int i;
	clightstyle_t *ls;
	"""

	for i in range(ref.MAX_LIGHTSTYLES):

		ls = cl_lightstyle[i]
		cl_view.V_AddLightStyle(i, ls.value[0], ls.value[1], ls.value[2])

cl_dlights = [] #cdlight_t[MAX_DLIGHTS]
for i in range(ref.MAX_DLIGHTS):
	cl_dlights.append(client_h.cdlight_t())

def CL_ClearDlights(): #void

	for dl in cl_dlights: # memset(cl_dlights, 0, sizeof(cl_dlights));
		dl.clear()

def CL_AllocDlight(key: int)->client_h.cdlight_t: #int (returns cdlight_t *)

	"""
	int i;
	cdlight_t *dl;
	"""

	# first look for an exact key match
	if key:

		for i in range(ref.MAX_DLIGHTS):

			dl = cl_dlights[i]
			if dl.key == key:

				return dl




	# then look for anything else
	for i in range(ref.MAX_DLIGHTS):

		dl = cl_dlights[i]
		if dl.die < cl_main.cl.time:

			dl.key = key
			return dl



	dl = cl_dlights[0]
	dl.key = key
	return dl

def CL_NewDlight(key: int, x: float, y: float, z: float, radius: float, time: float): #int, float, float, float, float, float

	"""
	cdlight_t *dl;
	"""

	dl = CL_AllocDlight(key)
	dl.origin[0] = x
	dl.origin[1] = y
	dl.origin[2] = z
	dl.radius = radius
	dl.die = cl_main.cl.time + time

def CL_RunDLights(): #void

	"""
	int i;
	cdlight_t *dl;
	"""

	for i in range(ref.MAX_DLIGHTS):

		dl = cl_dlights[i]
		if not dl.radius:

			continue


		# Vanilla Quake II had just cl.time. This worked in 1997
		# when computers were slow and the game reached ~30 FPS
		# on beefy hardware. Nowadays with 1000 FPS the dlights
		# are often rendered just a fraction of a frame. Work
		# around that by adding 32 ms, e.g. each dlight is shown
		# for at least 32 ms.
		if dl.die < cl_main.cl.time - 32:

			dl.radius = 0
			continue


		dl.radius -= cl_main.cls.rframetime * dl.decay

		if dl.radius < 0:

			dl.radius = 0

def CL_AddDLights(): #void

	"""
	int i;
	cdlight_t *dl;
	"""

	for i in range(ref.MAX_DLIGHTS):

		dl = cl_dlights[i]
		if not dl.radius:

			continue


		cl_view.V_AddLight(dl.origin, dl.radius, dl.color[0], dl.color[1], dl.color[2])
