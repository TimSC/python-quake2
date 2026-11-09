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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * File formats supported by stb_image, for now only tga, png, jpg
 * See also https://github.com/nothings/stb
 *
 * =======================================================================
"""

from __future__ import annotations

#
# files/stb.c
#

#
#include <stdlib.h>
#include "../ref_shared.h"


"""
** R_Convert8to32
"""
def R_Convert8to32 (data, width, height, table_8to24): #byte *, size_t, size_t, unsigned [] (returns unsigned *)

	"""
	unsigned *trans;
	size_t i, s;
	"""

	if height == 0:
		return None

	s = width * height

	trans = bytearray(s * 4)

	for i in range(s):
		p = data[i]
		r, g, b, a = table_8to24[p]
		base = i * 4
		trans[base] = r
		trans[base + 1] = g
		trans[base + 2] = b
		trans[base + 3] = a

		# transparent, so scan around for
		# another color to avoid alpha fringes
		if p == 255:
			if i > width and data[i - width] != 255:
				p = data[i - width]
			elif i < s - width and data[i + width] != 255:
				p = data[i + width]
			elif i > 0 and data[i - 1] != 255:
				p = data[i - 1]
			elif i < s - 1 and data[i + 1] != 255:
				p = data[i + 1]
			else:
				p = 0

			# copy rgb components
			r, g, b, a = table_8to24[p]
			trans[base] = r
			trans[base + 1] = g
			trans[base + 2] = b

	return trans


#
# The rest of stb.c (the stb_image loader, scale2x, scale3x) is not
# ported yet; it is only needed for tga/png/jpg texture loading.
#
