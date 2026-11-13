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
 * The PVS Decompress
 *
 * =======================================================================
"""
from __future__ import annotations

import numpy as np
from q2data import bsp as q2bsp
from common.header import shared
from common.shared import shared as shared_c


"""
===================
Mod_DecompressVis
===================
"""
def Mod_DecompressVis(data, row): #const byte *, int (returns byte *)

	# YQ2_ALIGNAS_TYPE(int) static byte decompressed[MAX_MAP_LEAFS / 8];
	decompressed = bytearray(q2bsp.MAX_MAP_LEAFS // 8)

	if not data:
		# no vis info, so make all visible
		for i in range(row):
			decompressed[i] = 0xff
		return bytes(decompressed[:row])

	in_offset = 0
	out_pos = 0
	data_view = memoryview(data)
	while out_pos < row:
		if data_view[in_offset]:
			decompressed[out_pos] = data_view[in_offset]
			in_offset += 1
			out_pos += 1
			continue

		c = data_view[in_offset + 1]
		in_offset += 2
		while c:
			decompressed[out_pos] = 0
			out_pos += 1
			c -= 1

	return bytes(decompressed[:row])

def Mod_RadiusFromBounds(mins, maxs): #const vec3_t, const vec3_t (returns float)

	corner = np.zeros((3,), dtype=np.float32)
	for i in range(3):
		corner[i] = abs(mins[i]) if abs(mins[i]) > abs(maxs[i]) else abs(maxs[i])

	return float(shared_c.VectorLength(corner))
