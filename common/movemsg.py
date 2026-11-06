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
from linux import sys_linux
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

es_nullstate = shared.entity_state_t() #static const entity_state_t, {0}

def DeltaEntityBits(from_: shared.entity_state_t, to: shared.entity_state_t, newentity: bool)->int: #const entity_state_t *, const entity_state_t *, qboolean (returns static int)

	bits = 0

	if to.number >= 256:
		bits |= common_h.U_NUMBER16		# number8 is implicit otherwise

	if to.origin[0] != from_.origin[0]:
		bits |= common_h.U_ORIGIN1
	if to.origin[1] != from_.origin[1]:
		bits |= common_h.U_ORIGIN2
	if to.origin[2] != from_.origin[2]:
		bits |= common_h.U_ORIGIN3

	if to.angles[0] != from_.angles[0]:
		bits |= common_h.U_ANGLE1		
	if to.angles[1] != from_.angles[1]:
		bits |= common_h.U_ANGLE2
	if to.angles[2] != from_.angles[2]:
		bits |= common_h.U_ANGLE3
		
	if to.skinnum != from_.skinnum:
	
		if (to.skinnum & 0xffffffff) < 256: # (unsigned)to->skinnum
			bits |= common_h.U_SKIN8
		elif (to.skinnum & 0xffffffff) < 0x10000:
			bits |= common_h.U_SKIN16
		else:
			bits |= (common_h.U_SKIN8|common_h.U_SKIN16)
	
	if to.frame != from_.frame:
	
		if to.frame < 256:
			bits |= common_h.U_FRAME8
		else:
			bits |= common_h.U_FRAME16
	
	if to.effects != from_.effects:
	
		if to.effects < 256:
			bits |= common_h.U_EFFECTS8
		elif to.effects < 0x8000:
			bits |= common_h.U_EFFECTS16
		else:
			bits |= common_h.U_EFFECTS8|common_h.U_EFFECTS16
	
	if to.renderfx != from_.renderfx:
	
		if to.renderfx < 256:
			bits |= common_h.U_RENDERFX8
		elif to.renderfx < 0x8000:
			bits |= common_h.U_RENDERFX16
		else:
			bits |= common_h.U_RENDERFX8|common_h.U_RENDERFX16
	
	if to.solid != from_.solid:
		bits |= common_h.U_SOLID

	# event is not delta compressed, just 0 compressed
	if to.event:
		bits |= common_h.U_EVENT
	
	if to.modelindex != from_.modelindex:
		bits |= common_h.U_MODEL
	if to.modelindex2 != from_.modelindex2:
		bits |= common_h.U_MODEL2
	if to.modelindex3 != from_.modelindex3:
		bits |= common_h.U_MODEL3
	if to.modelindex4 != from_.modelindex4:
		bits |= common_h.U_MODEL4

	if to.sound != from_.sound:
		bits |= common_h.U_SOUND

	if newentity or (to.renderfx & shared.RF_BEAM):
		bits |= common_h.U_OLDORIGIN

	if bits & 0xff000000:
		bits |= common_h.U_MOREBITS3 | common_h.U_MOREBITS2 | common_h.U_MOREBITS1
	elif bits & 0x00ff0000:
		bits |= common_h.U_MOREBITS2 | common_h.U_MOREBITS1
	elif bits & 0x0000ff00:
		bits |= common_h.U_MOREBITS1

	return bits

def MSG_DeltaEntity_Size(from_ent, to, force: bool, newentity: bool)->int: #const entity_state_t *, const entity_state_t *, qboolean, qboolean (returns size_t)

	"""
	size_t sz;
	int bits;
	"""
	U = common_h

	if from_ent is None:

		from_ent = es_nullstate


	if to is None:

		to = es_nullstate


	bits = DeltaEntityBits(from_ent, to, newentity)

	if not bits and not force:

		return 0


	sz = 1

	if bits & 0xff000000:

		sz += 3

	elif bits & 0x00ff0000:

		sz += 2

	elif bits & 0x0000ff00:

		sz += 1


	if bits & U.U_NUMBER16:

		sz += 2

	else:

		sz += 1


	if bits & U.U_MODEL:
		sz += 1

	if bits & U.U_MODEL2:
		sz += 1

	if bits & U.U_MODEL3:
		sz += 1

	if bits & U.U_MODEL4:
		sz += 1

	if bits & U.U_FRAME8:
		sz += 1

	if bits & U.U_FRAME16:
		sz += 2

	if (bits & U.U_SKIN8) and (bits & U.U_SKIN16): # used for laser colors
		sz += 4
	elif bits & U.U_SKIN8:
		sz += 1
	elif bits & U.U_SKIN16:
		sz += 2

	if (bits & (U.U_EFFECTS8 | U.U_EFFECTS16)) == (U.U_EFFECTS8 | U.U_EFFECTS16):
		sz += 4
	elif bits & U.U_EFFECTS8:
		sz += 1
	elif bits & U.U_EFFECTS16:
		sz += 2

	if (bits & (U.U_RENDERFX8 | U.U_RENDERFX16)) == (U.U_RENDERFX8 | U.U_RENDERFX16):
		sz += 4
	elif bits & U.U_RENDERFX8:
		sz += 1
	elif bits & U.U_RENDERFX16:
		sz += 2

	if bits & U.U_ORIGIN1:
		sz += 2

	if bits & U.U_ORIGIN2:
		sz += 2

	if bits & U.U_ORIGIN3:
		sz += 2

	if bits & U.U_ANGLE1:
		sz += 1

	if bits & U.U_ANGLE2:
		sz += 1

	if bits & U.U_ANGLE3:
		sz += 1

	if bits & U.U_OLDORIGIN:
		sz += 6

	if bits & U.U_SOUND:
		sz += 1

	if bits & U.U_EVENT:
		sz += 1

	if bits & U.U_SOLID:
		sz += 2

	return sz

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

def MSG_WriteDeltaUsercmd (buf, from_cmd, cmd): #sizebuf_t *, usercmd_t *, usercmd_t *

	bits = 0
	if cmd.angles[0] != from_cmd.angles[0]:
		bits |= common_h.CM_ANGLE1
	if cmd.angles[1] != from_cmd.angles[1]:
		bits |= common_h.CM_ANGLE2
	if cmd.angles[2] != from_cmd.angles[2]:
		bits |= common_h.CM_ANGLE3
	if cmd.forwardmove != from_cmd.forwardmove:
		bits |= common_h.CM_FORWARD
	if cmd.sidemove != from_cmd.sidemove:
		bits |= common_h.CM_SIDE
	if cmd.upmove != from_cmd.upmove:
		bits |= common_h.CM_UP
	if cmd.buttons != from_cmd.buttons:
		bits |= common_h.CM_BUTTONS
	if cmd.impulse != from_cmd.impulse:
		bits |= common_h.CM_IMPULSE

	MSG_WriteByte(buf, bits)
	if bits & common_h.CM_ANGLE1:
		MSG_WriteShort(buf, cmd.angles[0])
	if bits & common_h.CM_ANGLE2:
		MSG_WriteShort(buf, cmd.angles[1])
	if bits & common_h.CM_ANGLE3:
		MSG_WriteShort(buf, cmd.angles[2])

	if bits & common_h.CM_FORWARD:
		MSG_WriteShort(buf, cmd.forwardmove)
	if bits & common_h.CM_SIDE:
		MSG_WriteShort(buf, cmd.sidemove)
	if bits & common_h.CM_UP:
		MSG_WriteShort(buf, cmd.upmove)

	if bits & common_h.CM_BUTTONS:
		MSG_WriteByte(buf, cmd.buttons)
	if bits & common_h.CM_IMPULSE:
		MSG_WriteByte(buf, cmd.impulse)

	MSG_WriteByte(buf, cmd.msec)
	MSG_WriteByte(buf, cmd.lightlevel)


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

def MSG_ReadDir (sb, dirOut=None): #sizebuf_t *, vec3_t

	# Q2PORT: fills dirOut as the C does; also returns it, and makes a new one if
	# no vector is given (id's callers in cl_tent.py until group 11)

	if not isinstance(sb, common_h.sizebuf_t):
		raise RuntimeError("Wrong input type")
	#int		b;

	b = MSG_ReadByte (sb)
	if b < 0:
		clientserver.Com_Error (shared.ERR_DROP, "%s: unexpected message end", "MSG_ReadDir")
	if b >= common_h.NUMVERTEXNORMALS:
		clientserver.Com_Error (shared.ERR_DROP, "%s: out of range", "MSG_ReadDir")
	if dirOut is None:
		dirOut = np.zeros((3,), dtype=np.float32)
	shared.VectorCopy (bytedirs[b], dirOut)
	return dirOut


"""
==================
MSG_WriteDeltaEntity

Writes part of a packetentities message.
Can delta from either a baseline or a previous packet_entity
==================
"""
def MSG_WriteDeltaEntity (from_ent, to, msg, force, newentity): #const entity_state_t *, const entity_state_t *, sizebuf_t *, qboolean, qboolean

	#int		bits;

	if from_ent is None:

		from_ent = es_nullstate


	if to is None:

		to = es_nullstate


	# entnums are sent in 16-bit form
	if to.number > 32767: #SHRT_MAX

		return


	# send an update
	bits = DeltaEntityBits(from_ent, to, newentity)

	if not bits and not force:
		return		# nothing to send!

	MSG_WriteByte (msg,	bits&255 )

	if bits & 0xff000000:
	
		MSG_WriteByte (msg,	(bits>>8)&255 )
		MSG_WriteByte (msg,	(bits>>16)&255 )
		MSG_WriteByte (msg,	(bits>>24)&255 )
	
	elif bits & 0x00ff0000:
	
		MSG_WriteByte (msg,	(bits>>8)&255 )
		MSG_WriteByte (msg,	(bits>>16)&255 )
	
	elif bits & 0x0000ff00:
	
		MSG_WriteByte (msg,	(bits>>8)&255 )
	
	#----------

	if bits & common_h.U_NUMBER16:
		MSG_WriteShort (msg, to.number)
	else:
		MSG_WriteByte (msg,	to.number)

	if bits & common_h.U_MODEL:
		MSG_WriteByte (msg,	to.modelindex)
	if bits & common_h.U_MODEL2:
		MSG_WriteByte (msg,	to.modelindex2)
	if bits & common_h.U_MODEL3:
		MSG_WriteByte (msg,	to.modelindex3)
	if bits & common_h.U_MODEL4:
		MSG_WriteByte (msg,	to.modelindex4)

	if bits & common_h.U_FRAME8:
		MSG_WriteByte (msg, to.frame)
	if bits & common_h.U_FRAME16:
		MSG_WriteShort (msg, to.frame)

	if (bits & common_h.U_SKIN8) and (bits & common_h.U_SKIN16):		#used for laser colors
		MSG_WriteLong (msg, to.skinnum)
	elif bits & common_h.U_SKIN8:
		MSG_WriteByte (msg, to.skinnum)
	elif bits & common_h.U_SKIN16:
		MSG_WriteShort (msg, to.skinnum)


	if (bits & (common_h.U_EFFECTS8|common_h.U_EFFECTS16)) == (common_h.U_EFFECTS8|common_h.U_EFFECTS16):
		MSG_WriteLong (msg, to.effects)
	elif bits & common_h.U_EFFECTS8:
		MSG_WriteByte (msg, to.effects)
	elif bits & common_h.U_EFFECTS16:
		MSG_WriteShort (msg, to.effects)

	if (bits & (common_h.U_RENDERFX8|common_h.U_RENDERFX16)) == (common_h.U_RENDERFX8|common_h.U_RENDERFX16):
		MSG_WriteLong (msg, to.renderfx)
	elif bits & common_h.U_RENDERFX8:
		MSG_WriteByte (msg, to.renderfx)
	elif bits & common_h.U_RENDERFX16:
		MSG_WriteShort (msg, to.renderfx)

	if bits & common_h.U_ORIGIN1:
		MSG_WriteCoord (msg, to.origin[0])		
	if bits & common_h.U_ORIGIN2:
		MSG_WriteCoord (msg, to.origin[1])
	if bits & common_h.U_ORIGIN3:
		MSG_WriteCoord (msg, to.origin[2])

	if bits & common_h.U_ANGLE1:
		MSG_WriteAngle(msg, to.angles[0])
	if bits & common_h.U_ANGLE2:
		MSG_WriteAngle(msg, to.angles[1])
	if bits & common_h.U_ANGLE3:
		MSG_WriteAngle(msg, to.angles[2])

	if bits & common_h.U_OLDORIGIN:
	
		MSG_WriteCoord (msg, to.old_origin[0])
		MSG_WriteCoord (msg, to.old_origin[1])
		MSG_WriteCoord (msg, to.old_origin[2])
	
	if bits & common_h.U_SOUND:
		MSG_WriteByte (msg, to.sound)
	if bits & common_h.U_EVENT:
		MSG_WriteByte (msg, to.event)
	if bits & common_h.U_SOLID:
		MSG_WriteShort (msg, to.solid)


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


def MSG_ReadPos (msg_read: common_h.sizebuf_t, pos=None): #sizebuf_t *, vec3_t

	# Q2PORT: fills pos as the C does; also returns it, and makes a new one if
	# no pos is given (id's callers in cl_tent.py until group 11)
	if pos is None:
		pos = np.empty((3,))
	pos[0] = MSG_ReadShort(msg_read) * (1.0/8.0)
	pos[1] = MSG_ReadShort(msg_read) * (1.0/8.0)
	pos[2] = MSG_ReadShort(msg_read) * (1.0/8.0)
	return pos


def MSG_ReadAngle (msg_read: common_h.sizebuf_t)->float:

	return MSG_ReadChar(msg_read) * (360.0/256.0)


def MSG_ReadAngle16 (msg_read)->float: #(sizebuf_t *)

	return shared.SHORT2ANGLE(MSG_ReadShort(msg_read))


def _copy_usercmd (dst, src):
	dst.msec = src.msec
	dst.buttons = src.buttons
	dst.angles[0] = src.angles[0]
	dst.angles[1] = src.angles[1]
	dst.angles[2] = src.angles[2]
	dst.forwardmove = src.forwardmove
	dst.sidemove = src.sidemove
	dst.upmove = src.upmove
	dst.impulse = src.impulse
	dst.lightlevel = src.lightlevel


def MSG_ReadDeltaUsercmd (msg_read: common_h.sizebuf_t, from_cmd, move):

	_copy_usercmd(move, from_cmd)

	bits = MSG_ReadByte (msg_read)

	if bits & common_h.CM_ANGLE1:
		move.angles[0] = MSG_ReadShort (msg_read)
	if bits & common_h.CM_ANGLE2:
		move.angles[1] = MSG_ReadShort (msg_read)
	if bits & common_h.CM_ANGLE3:
		move.angles[2] = MSG_ReadShort (msg_read)

	if bits & common_h.CM_FORWARD:
		move.forwardmove = MSG_ReadShort (msg_read)
	if bits & common_h.CM_SIDE:
		move.sidemove = MSG_ReadShort (msg_read)
	if bits & common_h.CM_UP:
		move.upmove = MSG_ReadShort (msg_read)

	if bits & common_h.CM_BUTTONS:
		move.buttons = MSG_ReadByte (msg_read)

	if bits & common_h.CM_IMPULSE:
		move.impulse = MSG_ReadByte (msg_read)

	move.msec = MSG_ReadByte (msg_read)
	move.lightlevel = MSG_ReadByte (msg_read)

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
	sys_linux.Sys_Error ("COM_BlockSequenceCheckByte called\n")
	return 0


def COM_Parse(data, cursor):
	"""Expose COM_Parse from q_shared where needed."""
	return shared_c.COM_Parse(data, cursor)
