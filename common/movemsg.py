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

Movement message (forward, backward, left, right, etc) handling.

=======================================================================
"""
from __future__ import annotations

import struct
import json
import numpy as np
from backends.unix import system
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import szone

"""
#include "header/common.h"
#include <limits.h>
"""

def MSG_ConfigString_Size(s: str)->int: #const char * (returns size_t)

	return len(s) + 4 # string length + null char + message type + index

"""
==============================================================================

			MESSAGE IO FUNCTIONS

Handles byte ordering and avoids alignment errors
==============================================================================
*/
"""
bytedirs = np.array(json.load(open("client/anorms.json", "rt")), dtype=np.float32)

"""
#
# writing functions
#
"""
def MSG_WriteChar (sb: common_h.sizebuf_t, c):

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")
	"""
	byte	*buf;
	
#ifdef PARANOID
	if (c < -128 || c > 127)
		Com_Error (q_shared.ERR_FATAL, "MSG_WriteChar: range error");
#endif

	buf = SZ_GetSpace (sb, 1);
	buf[0] = c;
	"""
	if isinstance(c, (bytes, bytearray)):
		assert len(c) == 1
		value = c[0]
	else:
		value = int(c) & 0xFF
	offset = szone.SZ_GetSpace(sb, 1)

	struct.pack_into("B", sb.data, offset, value)

def MSG_WriteByte (sb: common_h.sizebuf_t, c): #sizebuf_t *, int

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")
	"""
	byte	*buf;
	
#ifdef PARANOID
	if (c < 0 || c > 255)
		Com_Error (q_shared.ERR_FATAL, "MSG_WriteByte: range error");
#endif
"""
	if isinstance(c, (bytes, bytearray)):
		assert len(c) == 1
		value = c[0]
	else:
		value = int(c)
	offset = szone.SZ_GetSpace(sb, 1)

	struct.pack_into("B", sb.data, offset, value & 0xFF)


def MSG_WriteShort (sb: common_h.sizebuf_t, c):

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")

	"""
	byte	*buf;
	
#ifdef PARANOID
	if (c < ((short)0x8000) || c > (short)0x7fff)
		Com_Error (q_shared.ERR_FATAL, "MSG_WriteShort: range error");
#endif
"""
	offset = szone.SZ_GetSpace(sb, 2)

	struct.pack_into("<H", sb.data, offset, int(c) & 0xffff) # C writes the low 16 bits

def MSG_WriteSShort (sb: common_h.sizebuf_t, c):

	offset = szone.SZ_GetSpace(sb, 2)

	struct.pack_into("<h", sb.data, offset, c)


def MSG_WriteLong (sb: common_h.sizebuf_t, c: int): #sizebuf_t *sb, int c)

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")


	#byte	*buf;
	
	#buf = SZ_GetSpace (sb, 4);
	#buf[0] = c&0xff;
	#buf[1] = (c>>8)&0xff;
	#buf[2] = (c>>16)&0xff;
	#buf[3] = c>>24;

	offset = szone.SZ_GetSpace(sb, 4)

	struct.pack_into("<L", sb.data, offset, int(c) & 0xffffffff) # C writes the low 32 bits

def MSG_WriteSLong (sb: common_h.sizebuf_t, c: int): #sizebuf_t *sb, int c)

	offset = szone.SZ_GetSpace(sb, 4)

	struct.pack_into("<l", sb.data, offset, c)

def MSG_WriteFloat (sb, f): #sizebuf_t *, float

	"""
	union
	{
		float	f;
		int	l;
	} dat;
	"""
	
	szone.SZ_Write (sb, struct.pack("<f", f)) # dat.f = f; dat.l = LittleLong (dat.l); SZ_Write (sb, &dat.l, 4);

def MSG_WriteString (sb: common_h.sizebuf_t, s): #sizebuf_t

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")

	if s is None:
		szone.SZ_Write (sb, b"\0")
	else:
		if isinstance(s, str):
			s = s.encode('latin-1')
		szone.SZ_Write (sb, s)
		szone.SZ_Write (sb, b"\0")

def MSG_WriteCoord (sb, f): #sizebuf_t *, float

	MSG_WriteShort (sb, int(f*8))

def MSG_WritePos (sb, pos): #sizebuf_t *, vec3_t

	MSG_WriteShort (sb, int(pos[0]*8))
	MSG_WriteShort (sb, int(pos[1]*8))
	MSG_WriteShort (sb, int(pos[2]*8))

def MSG_WriteAngle (sb, f): #sizebuf_t *, float

	MSG_WriteByte (sb, int(f*256/360) & 255)

def MSG_WriteAngle16 (sb, f): #sizebuf_t *, float

	MSG_WriteShort (sb, shared.ANGLE2SHORT(f))

def MSG_WriteConfigString(buf: common_h.sizebuf_t, index: int, s: str): #sizebuf_t *, short, const char *

	MSG_WriteShort(buf, index)
	MSG_WriteString(buf, s)

def MSG_WriteDir (sb, dir): #sizebuf_t *, vec3_t

	#int		i, best;
	#float	d, bestd;
	
	if dir is None:
	
		MSG_WriteByte (sb, 0)
		return
	
	bestd = 0
	best = 0
	for i in range(common_h.NUMVERTEXNORMALS):
	
		d = shared.DotProduct (dir, bytedirs[i])
		if d > bestd:
		
			bestd = d
			best = i
		
	MSG_WriteByte (sb, best)

def MSG_ReadDir (sb, dirOut): #sizebuf_t *, vec3_t

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")
	#int		b;

	b = MSG_ReadByte (sb)
	if b < 0:
		clientserver.Com_Error (shared.ERR_DROP, "%s: unexpected message end", "MSG_ReadDir")
	if b >= common_h.NUMVERTEXNORMALS:
		clientserver.Com_Error (shared.ERR_DROP, "%s: out of range", "MSG_ReadDir")
	shared.VectorCopy (bytedirs[b], dirOut)


#============================================================
#
# reading functions
#

def MSG_BeginReading (msg): #sizebuf_t *

	msg.readcount = 0


# returns -1 if no more characters are available
def MSG_ReadChar (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#int	c;

	if msg_read.readcount+1 > msg_read.cursize:
		c = -1
	else:
		c = msg_read.data[msg_read.readcount]
		if c > 127: # (signed char)
			c -= 256
	msg_read.readcount+=1
	
	return c

def MSG_ReadByte (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#int	c;
	if msg_read.readcount+1 > msg_read.cursize:
		c = -1
	else:
		c = msg_read.data[msg_read.readcount]
	msg_read.readcount+=1
	
	return c


def MSG_ReadShort (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)
	#int	c;
	
	if msg_read.readcount+2 > msg_read.cursize:
		c = -1
	else:		
		c = struct.unpack_from("<h", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 2
	
	return c

def MSG_ReadSShort (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#int	c;
	
	if msg_read.readcount+2 > msg_read.cursize:
		c = -1
	else:
		c = struct.unpack_from("<h", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 2
	
	return c


def MSG_ReadLong (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#int	c;
	
	if msg_read.readcount+4 > msg_read.cursize:
		c = -1
	else:
		c = struct.unpack_from("<L", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 4
	
	return c

def MSG_ReadSLong (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#int	c;
	
	if msg_read.readcount+4 > msg_read.cursize:
		c = -1
	else:
		c = struct.unpack_from("<l", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 4
	
	return c

def MSG_ReadFloat (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#union
	#{
	#	byte	b[4];
	#	float	f;
	#	int	l;
	#} dat;
	c = 0
	if msg_read.readcount+4 > msg_read.cursize:
		c = -1
	else:
	
		#dat.b[0] =	msg_read.data[msg_read.readcount]
		#dat.b[1] =	msg_read.data[msg_read.readcount+1]
		#dat.b[2] =	msg_read.data[msg_read.readcount+2]
		#dat.b[3] =	msg_read.data[msg_read.readcount+3]
		c = struct.unpack("<f", msg_read.data[msg_read.readcount:msg_read.readcount+4])
	
	msg_read.readcount += 4
	
	#dat.l = LittleLong (dat.l)

	return c


def MSG_ReadString (msg_read): #sizebuf_t *
	assert isinstance(msg_read, common_h.sizebuf_t)

	#static char	string[2048];
	#int		l,c;
	l = 0
	readStringSize = 2048
	st = bytearray()

	while l < readStringSize-1:
	
		c = MSG_ReadByte (msg_read)
		if c == -1 or c == 0:
			break
		st.append(c & 0xff)
		l+=1
	
	#string[l] = 0;
	return st.decode('latin-1')


def MSG_ReadStringLine (msg_read): # sizebuf_t * (returns char *)
	assert isinstance(msg_read, common_h.sizebuf_t)

	#static char	string[2048];
	#int		l,c;
	
	l = 0
	readStringSize = 2048
	st = bytearray()
	
	while l < readStringSize-1:
	
		c = MSG_ReadByte (msg_read)
		if c == -1 or c == 0 or c == ord('\n'):
			break
		st.append(c & 0xff)
		l+=1
	
	#string[l] = 0
	
	return st.decode('latin-1')


def MSG_ReadCoord (msg_read: common_h.sizebuf_t)->float:

	return MSG_ReadShort(msg_read) * (1.0/8.0)


def MSG_ReadPos (msg_read: common_h.sizebuf_t, pos): #sizebuf_t *, vec3_t

	pos[0] = MSG_ReadShort(msg_read) * (1.0/8.0)
	pos[1] = MSG_ReadShort(msg_read) * (1.0/8.0)
	pos[2] = MSG_ReadShort(msg_read) * (1.0/8.0)


def MSG_ReadAngle (msg_read: common_h.sizebuf_t)->float:

	return MSG_ReadChar(msg_read) * (360.0/256.0)


def MSG_ReadAngle16 (msg_read)->float: #(sizebuf_t *)

	return shared.SHORT2ANGLE(MSG_ReadShort(msg_read))


def MSG_ReadData (msg_read, length: int): #sizebuf_t *, void *, int

	data = bytearray(length)
	for i in range(length):
		data[i] = MSG_ReadByte (msg_read)
	return data


#============================================================================
"""
/*
====================
COM_BlockSequenceCheckByte

For proxy protecting

# THIS IS MASSIVELY BROKEN!  CHALLENGE MAY BE NEGATIVE
# DON'T USE THIS FUNCTION!!!!!

====================
*/
"""
def COM_BlockSequenceCheckByte (base, length, sequence, challenge): #byte *, int, int, int (returns byte)
	system.Sys_Error ("COM_BlockSequenceCheckByte called\n")
	return 0


def COM_Parse(data, cursor):
	"""Expose COM_Parse from q_shared where needed."""
	return shared_c.COM_Parse(data, cursor)
