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

Zone malloc. It's just a normal malloc with tags.

=======================================================================
"""
from __future__ import annotations

from common.header import shared
from common import clientserver

"""
#include "header/common.h"
#include <limits.h>
#include <stdint.h>
"""

def Z_Init(): #void

	global z_count, z_bytes

	#memset(&z_chain, 0, sizeof(z_chain));

	z_chain.prev = z_chain
	z_chain.next = z_chain

	z_count = 0
	z_bytes = 0

Z_MAGIC = 0x1d1d

z_count, z_bytes = 0, 0 # int


class zhead_t(object):

	def __init__(self):
		self.prev = None
		self.next = None
		self.magic = None # short
		self.tag = 0 # short
		self.size = 0 # int


z_chain = zhead_t()
z_chain.next = z_chain
z_chain.prev = z_chain
"""
/*
========================
Z_Free
========================
*/
"""
def Z_Free (ptr): # void *

	global z_count, z_bytes

	# z = ((zhead_t *)ptr) - 1  ->  ptr IS the zhead

	if ptr.magic != Z_MAGIC:
		clientserver.Com_Error (shared.ERR_FATAL, "%s: not a valid memory block: %s", "Z_Free", ptr)
		return

	ptr.prev.next = ptr.next
	ptr.next.prev = ptr.prev

	z_count -= 1
	z_bytes -= ptr.size
	ptr.magic = 0
	ptr.next = ptr.prev = None
"""
========================
Z_Stats_f
========================
"""
def Z_Stats_f ():

	clientserver.Com_Printf ("%d bytes in %d blocks\n", z_bytes, z_count)

"""
/*
========================
Z_FreeTags
========================
*/
"""
def Z_FreeTags (tag): # int

	z = z_chain.next
	while z is not z_chain:
		nxt = z.next
		if z.tag == tag:
			Z_Free (z)
		z = nxt
"""
/*
========================
Z_TagMalloc
========================
*/
"""
def Z_TagMalloc (size, tag): # int, int

	global z_count, z_bytes

	if not size: # || ((SIZE_MAX - size) < sizeof(zhead_t))

		clientserver.Com_Error(shared.ERR_FATAL, "%s: bad allocation size: %d", "Z_TagMalloc", size)
		return None


	size = size + 8 # size + sizeof(zhead_t)
	z = zhead_t()
	#z = malloc(size)
	#if (!z)
	#	Com_Error (q_shared.ERR_FATAL, "Z_Malloc: failed on allocation of %i bytes",size)
	z_count += 1
	z_bytes += size
	z.magic = Z_MAGIC
	z.tag = tag
	z.size = size

	z.next = z_chain.next
	z.prev = z_chain
	z_chain.next.prev = z
	z_chain.next = z

	return z # (void *)(z+1)

"""
/*
========================
Z_Malloc
========================
*/
"""
def Z_Malloc (size): # int

	return Z_TagMalloc (size, 0)
"""
void *
Z_TagRealloc(void *ptr, size_t size, unsigned short tag)
{
	zhead_t *z, *zr;

	if (!size || ((SIZE_MAX - size) < sizeof(zhead_t)))
	{
		Com_Error(ERR_FATAL, "%s: bad allocation size: " YQ2_COM_PRIdS,
			__func__, size);
		return NULL;
	}

	if (!ptr)
	{
		return Z_TagMalloc(size, tag);
	}

	z = (zhead_t *)ptr - 1;

	if (z->magic != Z_MAGIC)
	{
		Com_Error(ERR_FATAL, "%s: not a valid memory block: %p", __func__, ptr);
		return NULL;
	}

	size = size + sizeof(zhead_t);
	zr = Q_realloc0(z, z->size, size);

	if (!zr)
	{
		Com_Error(ERR_FATAL, "%s: failed to allocate " YQ2_COM_PRIdS " bytes",
			__func__, size);
		return NULL;
	}

	z_bytes -= zr->size;
	z_bytes += size;

	zr->tag = tag;
	zr->size = size;
	zr->prev->next = zr;
	zr->next->prev = zr;

	return zr + 1;
}
"""

"""
void *
Z_Realloc(void *ptr, size_t size)
{
	return Z_TagRealloc(ptr, size, 0);
}
"""

"""
size_t
Z_BlockSize(const void *ptr)
{
	const zhead_t *z;

	if (!ptr)
	{
		return 0;
	}

	z = (const zhead_t *)ptr - 1;

	if (z->magic != Z_MAGIC)
	{
		return 0;
	}

	return z->size - sizeof(*z);
}
"""

