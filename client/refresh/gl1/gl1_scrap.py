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
 * Allocate all the little status bar objects into a single texture
 * to crutch up inefficient hardware / drivers.
 *
 * =======================================================================
"""

from __future__ import annotations

#
# gl1_scrap.c
#

#
#include "gl1_scrap.h"
#include "header/local.h"


MAX_SCRAPS_NOLERP		= 2
MAX_SCRAPS				= 4

BLOCK_WIDTH				= 128
BLOCK_HEIGHT			= 128
SCRAP_WIDTH				= BLOCK_WIDTH * 2
SCRAP_HEIGHT			= BLOCK_HEIGHT * 2

scrap_allocated = [[0] * SCRAP_WIDTH for _ in range(MAX_SCRAPS)] #int [MAX_SCRAPS][SCRAP_WIDTH]
scrap_texels = [bytearray(SCRAP_WIDTH * SCRAP_HEIGHT * 4) for _ in range(MAX_SCRAPS)] #unsigned [MAX_SCRAPS][SCRAP_WIDTH*SCRAP_HEIGHT]
scrap_dirty = [False] * MAX_SCRAPS #qboolean [MAX_SCRAPS]


"""
** CommonAllocBlock
"""
def CommonAllocBlock (allocated, alloc_width, alloc_height, w, h, x, y): #int [], int, int, unsigned, unsigned, int [], int [] (returns qboolean)

	"""
	size_t i, best;
	"""

	best = alloc_height

	for i in range(alloc_width - w):

		best2 = 0
		valid = True

		for j in range(w):
			if allocated[i + j] >= best:

				valid = False
				break

			if allocated[i + j] > best2:
				best2 = allocated[i + j]

		if valid:
		
			# this is a valid spot
			x[0] = i
			y[0] = best = best2

	if best + h > alloc_height:
		return False

	for i in range(w):
		allocated[x[0] + i] = best + h

	return True


"""
** Scrap_AllocBlock

returns a texture number and the position inside it
"""
def Scrap_AllocBlock (w, h, x, y, pic, scrap_offset): #unsigned, unsigned, int [], int [], unsigned [], int (returns int)

	"""
	int texnum;
	"""

	w += 2 # add an empty border to all sides
	h += 2

	for texnum in range(scrap_offset, MAX_SCRAPS):
		if CommonAllocBlock( scrap_allocated[texnum], SCRAP_WIDTH, SCRAP_HEIGHT,
			w, h, x, y ):
		
			#k, i = 0, 0 #size_t, size_t

			x[0] += 1 # jump the border
			y[0] += 1

			scrap_dirty[texnum] = True

			# copy the texels into the scrap block
			k = 0

			row = (w - 2) * 4

			for i in range(h - 2):
				dst = (y[0] + i) * SCRAP_WIDTH * 4 + x[0] * 4
				scrap_texels[texnum][dst:dst + row] = pic[k * 4:k * 4 + row]
				k += w - 2

			return texnum

	return -1


"""
** Scrap_Upload
"""
def Scrap_Upload (texnum): #int (returns unsigned *)

	if texnum < 0 or texnum >= MAX_SCRAPS or not scrap_dirty[texnum]:
		return None

	scrap_dirty[texnum] = False
	return scrap_texels[texnum]


"""
** Scrap_Init
"""
def Scrap_Init ():

	# memset( scrap_allocated, 0, sizeof(scrap_allocated) );
	# memset( scrap_dirty, 0, sizeof(scrap_dirty) );
	for i in range(MAX_SCRAPS):
		for j in range(SCRAP_WIDTH):
			scrap_allocated[i][j] = 0
		scrap_dirty[i] = False

	# transparent
	# memset( scrap_texels, 0, sizeof(scrap_texels) );
	for i in range(MAX_SCRAPS):
		for k in range(SCRAP_WIDTH * SCRAP_HEIGHT * 4):
			scrap_texels[i][k] = 0
