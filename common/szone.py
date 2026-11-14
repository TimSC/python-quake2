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

Server zone, server side of memory management

=======================================================================
"""
from __future__ import annotations

from common.header import common as common_h
from common.header import shared
from common import clientserver

"""
#include "header/common.h"
"""

#===========================================================================

def SZ_Init (buf, length): #sizebuf_t *, byte *, int

	assert isinstance(buf, common_h.sizebuf_t)

	#memset (buf, 0, sizeof(*buf));
	#buf->data = data;
	#buf->maxsize = length;
	#if data is None:
	#	return None
	#return data.serialize()

	buf.data = bytearray()
	buf.maxsize = length


def SZ_Clear (buf: common_h.sizebuf_t):

	buf.cursize = 0
	buf.overflowed = False
	buf.data = bytearray()

def SZ_GetSpace (buf: common_h.sizebuf_t, length): #sizebuf_t *, int (void *)

	#void	*data;
	assert buf.maxsize > 0
	
	if buf.cursize + length > buf.maxsize:
	
		if not buf.allowoverflow:
			clientserver.Com_Error (shared.ERR_FATAL, "SZ_GetSpace: overflow without allowoverflow set")
		
		if length > buf.maxsize:
			clientserver.Com_Error (shared.ERR_FATAL, "SZ_GetSpace: {} is > full buffer size".format(length))
			
		SZ_Clear (buf)
		buf.overflowed = True
		clientserver.Com_DPrintf ("SZ_GetSpace: overflow\n")
	
	offset = buf.cursize
	buf.data += bytearray(length)
	buf.cursize += length
	
	return offset


def SZ_Write (buf: common_h.sizebuf_t, data):

	assert isinstance(data, bytes) or isinstance(data, bytearray)

	if len(data) > 0:

		offset = SZ_GetSpace(buf, len(data))

		buf.data[offset:offset+len(data)] = data


def SZ_Print (buf: common_h.sizebuf_t, data): #char *

	#int		len;
	assert isinstance(data, str)
	
	data = data.encode('latin-1', 'replace') # Q2PORT: latin-1, the C's strings are bytes (ascii failed on others)
	length = len(data)+1

	if buf.cursize > 0:
	
		if buf.data[buf.cursize-1] != 0:

			offset = SZ_GetSpace(buf, length)
			buf.data[offset:offset+len(data)] = data
			buf.data[offset+len(data)] = 0 # string terminator

			#memcpy ((byte *)SZ_GetSpace(buf, len),data,len); # no trailing 0
		else:

			offset = SZ_GetSpace(buf, length-2)
			buf.data[offset-1:offset+len(data)-2] = data
			buf.data[offset+len(data)-1] = 0 # string terminator

			#memcpy ((byte *)SZ_GetSpace(buf, len-1)-1,data,len); # write over trailing 0
	else:
		offset = SZ_GetSpace(buf, length)

		buf.data[offset:offset+len(data)] = data
		buf.data[offset+len(data)] = 0
