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
import sys
import struct
import json
import random
import numpy as np
from qcommon import cvar, cmd, files, qcommon, net_chan, crc
from linux import sys_linux, q_shlinux, net_udp
from game import q_shared
from server import sv_main
from client import cl_main, cl_scrn, keys, console
import pygame

screen = None

"""
# common.c -- misc functions used in client and server
#include "qcommon.h"
#include <setjmp.h>

#define	MAXPRINTMSG	4096
"""
MAX_NUM_ARGVS = 50

com_argc = None #int
com_argv = [] #char	*[MAX_NUM_ARGVS+1];
for i in range(MAX_NUM_ARGVS+1):
	com_argv.append(None)

"""
int		realtime;
"""

class abortframe(Exception):	# jmp_buf abortframe, an ERR_DROP occured, exit the entire frame
	pass				# longjmp (abortframe, -1) raises it, the setjmp in Qcommon_Frame catches it

"""


FILE	*log_stats_file;


"""
host_speeds = None #cvar_t	*
log_stats = None #cvar_t	*
developer = None #cvar_t	*
timescale = None #cvar_t	*
fixedtime = None #cvar_t	*
logfile_active = None #cvar_t	*, 1 = buffer log, 2 = flush after each print
showtrace = None #cvar_t	*
dedicated = None #cvar_t	*
"""
FILE	*logfile;
"""
server_state = 0 #int

# host_speeds times
time_before_game = None #int
time_after_game = None #int
time_before_ref = None #int
time_after_ref = None #int

"""
============================================================================

CLIENT / SERVER interactions

============================================================================
"""

rd_target = 0 #static int
rd_buffer = None #static char *, python strings are immutable so the text is held here and passed to rd_flush
rd_buffersize = 0 #static int
rd_flush = None #static void	(*rd_flush)(int target, char *buffer);

RD_NONE	= 0
RD_CLIENT	= 1
RD_PACKET	= 2

def Com_BeginRedirect (target, buffer, buffersize, flush): #int, char *, int, void (*flush)

	global rd_target, rd_buffer, rd_buffersize, rd_flush

	if not target or buffer is None or not buffersize or flush is None:
		return
	rd_target = target
	rd_buffer = ""
	rd_buffersize = buffersize
	rd_flush = flush

def Com_EndRedirect ():

	global rd_target, rd_buffer, rd_buffersize, rd_flush

	rd_flush(rd_target, rd_buffer)

	rd_target = 0
	rd_buffer = None
	rd_buffersize = 0
	rd_flush = None

"""
=============
Com_Printf

Both client and server can use this, and it will output
to the apropriate place.
=============
"""
def Com_Printf (msg): #char *

	global rd_buffer

	"""
	va_list		argptr;
	char		msg[MAXPRINTMSG];

	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);
	"""

	if rd_target:
	
		if (len (msg) + len(rd_buffer)) > (rd_buffersize - 1):
		
			rd_flush(rd_target, rd_buffer)
			rd_buffer = ""
		
		rd_buffer += msg
		return
	
	console.Con_Print(msg)

	# also echo to debugging console
	sys_linux.Sys_ConsoleOutput (msg)
	"""		
	// logfile
	if (logfile_active && logfile_active->value)
	{
		char	name[MAX_QPATH];
		
		if (!logfile)
		{
			Com_sprintf (name, sizeof(name), "%s/qconsole.log", FS_Gamedir ());
			if (logfile_active->value > 2)
				logfile = fopen (name, "a");
			else
				logfile = fopen (name, "w");
		}
		if (logfile)
			fprintf (logfile, "%s", msg);
		if (logfile_active->value > 1)
			fflush (logfile);		// force it to save every time
	}

/*
================
Com_DPrintf

A Com_Printf that only shows up if the "developer" cvar is set
================
"""
def Com_DPrintf (fmt):

	"""
	va_list		argptr;
	char		msg[MAXPRINTMSG];
	"""

	if developer is None or not developer.value:
		return			# don't confuse non-developers with techie stuff...

	"""
	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);
	"""

	Com_Printf (msg)

"""
=============
Com_Error

Both client and server can use this, and it will
do the apropriate things.
=============
"""
com_error_msg = "" #static char [MAXPRINTMSG], in Com_Error
com_error_recursive = False #static qboolean, in Com_Error

def Com_Error (code, msg): #int, char *

	global com_error_msg, com_error_recursive

	"""
	va_list		argptr;
	static char		msg[MAXPRINTMSG];
	static	qboolean	recursive;
	"""

	if com_error_recursive:
		sys_linux.Sys_Error ("recursive error after: {}".format(com_error_msg))
	com_error_recursive = True

	com_error_msg = msg # va_start (argptr,fmt); vsprintf (msg,fmt,argptr); va_end (argptr);
	
	if code == q_shared.ERR_DISCONNECT:
	
		cl_main.CL_Drop ()
		com_error_recursive = False
		raise abortframe () # longjmp (abortframe, -1);
	
	elif code == q_shared.ERR_DROP:
	
		Com_Printf ("********************\nERROR: {}\n********************\n".format(msg))
		sv_main.SV_Shutdown ("Server crashed: {}\n".format(msg), False)
		cl_main.CL_Drop ()
		com_error_recursive = False
		raise abortframe () # longjmp (abortframe, -1);
	
	else:
	
		sv_main.SV_Shutdown ("Server fatal crashed: {}\n".format(msg), False)
		cl_main.CL_Shutdown ()
	
	"""
	if (logfile)
	{
		fclose (logfile);
		logfile = NULL;
	}
	"""

	sys_linux.Sys_Error ("{}".format(msg))
	

"""

/*
=============
Com_Quit

Both client and server can use this, and it will
do the apropriate things.
=============
"""
def Com_Quit ():

	sv_main.SV_Shutdown ("Server quit\n", False)
	cl_main.CL_Shutdown ()

	"""
	if (logfile)
	{
		fclose (logfile);
		logfile = NULL;
	}
	"""

	sys_linux.Sys_Quit()

"""
==================
Com_ServerState
==================
"""
def Com_ServerState (): #(returns int)

	return server_state


"""
==================
Com_SetServerState
==================
"""
def Com_SetServerState (state):

	global server_state

	server_state = state

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
def MSG_WriteChar (sb: qcommon.sizebuf_t, c: bytes|bytearray):

	assert isinstance(c, bytes) or isinstance(c, bytearray)
	if not isinstance(sb, qcommon.sizebuf_t):
		raise RuntimeError("Wrong input type")
	assert len(c) == 1

	"""
	byte	*buf;
	
#ifdef PARANOID
	if (c < -128 || c > 127)
		Com_Error (q_shared.ERR_FATAL, "MSG_WriteChar: range error");
#endif

	buf = SZ_GetSpace (sb, 1);
	buf[0] = c;
	"""
	offset = SZ_GetSpace(sb, 1)

	struct.pack_into("c", sb.data, offset, c)

def MSG_WriteByte (sb: qcommon.sizebuf_t, c): #sizebuf_t *, int

	if not isinstance(sb, qcommon.sizebuf_t):
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
	offset = SZ_GetSpace(sb, 1)

	struct.pack_into("B", sb.data, offset, value & 0xFF)


def MSG_WriteShort (sb: qcommon.sizebuf_t, c):

	if not isinstance(sb, qcommon.sizebuf_t):
		raise RuntimeError("Wrong input type")

	"""
	byte	*buf;
	
#ifdef PARANOID
	if (c < ((short)0x8000) || c > (short)0x7fff)
		Com_Error (q_shared.ERR_FATAL, "MSG_WriteShort: range error");
#endif
"""
	offset = SZ_GetSpace(sb, 2)

	struct.pack_into("<H", sb.data, offset, int(c) & 0xffff) # C writes the low 16 bits

def MSG_WriteSShort (sb: qcommon.sizebuf_t, c):

	offset = SZ_GetSpace(sb, 2)

	struct.pack_into("<h", sb.data, offset, c)


def MSG_WriteLong (sb: qcommon.sizebuf_t, c: int): #sizebuf_t *sb, int c)

	if not isinstance(sb, qcommon.sizebuf_t):
		raise RuntimeError("Wrong input type")


	#byte	*buf;
	
	#buf = SZ_GetSpace (sb, 4);
	#buf[0] = c&0xff;
	#buf[1] = (c>>8)&0xff;
	#buf[2] = (c>>16)&0xff;
	#buf[3] = c>>24;

	offset = SZ_GetSpace(sb, 4)

	struct.pack_into("<L", sb.data, offset, int(c) & 0xffffffff) # C writes the low 32 bits

def MSG_WriteSLong (sb: qcommon.sizebuf_t, c: int): #sizebuf_t *sb, int c)

	offset = SZ_GetSpace(sb, 4)

	struct.pack_into("<l", sb.data, offset, c)

def MSG_WriteFloat (sb, f): #sizebuf_t *, float

	"""
	union
	{
		float	f;
		int	l;
	} dat;
	"""
	
	SZ_Write (sb, struct.pack("<f", f)) # dat.f = f; dat.l = LittleLong (dat.l); SZ_Write (sb, &dat.l, 4);

def MSG_WriteString (sb: qcommon.sizebuf_t, s): #sizebuf_t

	assert isinstance(s, bytes) or isinstance(s, bytearray) or s is None
	if not isinstance(sb, qcommon.sizebuf_t):
		raise RuntimeError("Wrong input type")

	if s is None:
		SZ_Write (sb, b"\0")
	else:
		SZ_Write (sb, s)
		SZ_Write (sb, b"\0")

def MSG_WriteCoord (sb, f): #sizebuf_t *, float

	MSG_WriteShort (sb, int(f*8))

def MSG_WritePos (sb, pos): #sizebuf_t *, vec3_t

	MSG_WriteShort (sb, int(pos[0]*8))
	MSG_WriteShort (sb, int(pos[1]*8))
	MSG_WriteShort (sb, int(pos[2]*8))

def MSG_WriteAngle (sb, f): #sizebuf_t *, float

	MSG_WriteByte (sb, int(f*256/360) & 255)

def MSG_WriteAngle16 (sb, f): #sizebuf_t *, float

	MSG_WriteShort (sb, q_shared.ANGLE2SHORT(f))

def MSG_WriteDeltaUsercmd (buf, from_cmd, cmd): #sizebuf_t *, usercmd_t *, usercmd_t *

	bits = 0
	if cmd.angles[0] != from_cmd.angles[0]:
		bits |= qcommon.CM_ANGLE1
	if cmd.angles[1] != from_cmd.angles[1]:
		bits |= qcommon.CM_ANGLE2
	if cmd.angles[2] != from_cmd.angles[2]:
		bits |= qcommon.CM_ANGLE3
	if cmd.forwardmove != from_cmd.forwardmove:
		bits |= qcommon.CM_FORWARD
	if cmd.sidemove != from_cmd.sidemove:
		bits |= qcommon.CM_SIDE
	if cmd.upmove != from_cmd.upmove:
		bits |= qcommon.CM_UP
	if cmd.buttons != from_cmd.buttons:
		bits |= qcommon.CM_BUTTONS
	if cmd.impulse != from_cmd.impulse:
		bits |= qcommon.CM_IMPULSE

	MSG_WriteByte(buf, bits)
	if bits & qcommon.CM_ANGLE1:
		MSG_WriteShort(buf, cmd.angles[0])
	if bits & qcommon.CM_ANGLE2:
		MSG_WriteShort(buf, cmd.angles[1])
	if bits & qcommon.CM_ANGLE3:
		MSG_WriteShort(buf, cmd.angles[2])

	if bits & qcommon.CM_FORWARD:
		MSG_WriteShort(buf, cmd.forwardmove)
	if bits & qcommon.CM_SIDE:
		MSG_WriteShort(buf, cmd.sidemove)
	if bits & qcommon.CM_UP:
		MSG_WriteShort(buf, cmd.upmove)

	if bits & qcommon.CM_BUTTONS:
		MSG_WriteByte(buf, cmd.buttons)
	if bits & qcommon.CM_IMPULSE:
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
	for i in range(qcommon.NUMVERTEXNORMALS):
	
		d = q_shared.DotProduct (dir, bytedirs[i])
		if d > bestd:
		
			bestd = d
			best = i
		
	MSG_WriteByte (sb, best)

def MSG_ReadDir (sb):

	if not isinstance(sb, qcommon.sizebuf_t):
		raise RuntimeError("Wrong input type")
	#int		b;

	b = MSG_ReadByte (sb)
	if b >= qcommon.NUMVERTEXNORMALS:
		Com_Error (q_shared.ERR_DROP, "MSF_ReadDir: out of range")
	dirOut = np.zeros((3,), dtype=np.float32)
	q_shared.VectorCopy (bytedirs[b], dirOut)
	return dirOut


"""
==================
MSG_WriteDeltaEntity

Writes part of a packetentities message.
Can delta from either a baseline or a previous packet_entity
==================
"""
def MSG_WriteDeltaEntity (from_ent, to, msg, force, newentity): #entity_state_t *, entity_state_t *, sizebuf_t *, qboolean, qboolean

	#int		bits;

	if not to.number:
		Com_Error (q_shared.ERR_FATAL, "Unset entity number")
	if to.number >= q_shared.MAX_EDICTS:
		Com_Error (q_shared.ERR_FATAL, "Entity number >= MAX_EDICTS")

	# send an update
	bits = 0

	if to.number >= 256:
		bits |= qcommon.U_NUMBER16		# number8 is implicit otherwise

	if to.origin[0] != from_ent.origin[0]:
		bits |= qcommon.U_ORIGIN1
	if to.origin[1] != from_ent.origin[1]:
		bits |= qcommon.U_ORIGIN2
	if to.origin[2] != from_ent.origin[2]:
		bits |= qcommon.U_ORIGIN3

	if to.angles[0] != from_ent.angles[0]:
		bits |= qcommon.U_ANGLE1		
	if to.angles[1] != from_ent.angles[1]:
		bits |= qcommon.U_ANGLE2
	if to.angles[2] != from_ent.angles[2]:
		bits |= qcommon.U_ANGLE3
		
	if to.skinnum != from_ent.skinnum:
	
		if (to.skinnum & 0xffffffff) < 256: # (unsigned)to->skinnum
			bits |= qcommon.U_SKIN8
		elif (to.skinnum & 0xffffffff) < 0x10000:
			bits |= qcommon.U_SKIN16
		else:
			bits |= (qcommon.U_SKIN8|qcommon.U_SKIN16)
	
	if to.frame != from_ent.frame:
	
		if to.frame < 256:
			bits |= qcommon.U_FRAME8
		else:
			bits |= qcommon.U_FRAME16
	
	if to.effects != from_ent.effects:
	
		if to.effects < 256:
			bits |= qcommon.U_EFFECTS8
		elif to.effects < 0x8000:
			bits |= qcommon.U_EFFECTS16
		else:
			bits |= qcommon.U_EFFECTS8|qcommon.U_EFFECTS16
	
	if to.renderfx != from_ent.renderfx:
	
		if to.renderfx < 256:
			bits |= qcommon.U_RENDERFX8
		elif to.renderfx < 0x8000:
			bits |= qcommon.U_RENDERFX16
		else:
			bits |= qcommon.U_RENDERFX8|qcommon.U_RENDERFX16
	
	if to.solid != from_ent.solid:
		bits |= qcommon.U_SOLID

	# event is not delta compressed, just 0 compressed
	if to.event:
		bits |= qcommon.U_EVENT
	
	if to.modelindex != from_ent.modelindex:
		bits |= qcommon.U_MODEL
	if to.modelindex2 != from_ent.modelindex2:
		bits |= qcommon.U_MODEL2
	if to.modelindex3 != from_ent.modelindex3:
		bits |= qcommon.U_MODEL3
	if to.modelindex4 != from_ent.modelindex4:
		bits |= qcommon.U_MODEL4

	if to.sound != from_ent.sound:
		bits |= qcommon.U_SOUND

	if newentity or (to.renderfx & q_shared.RF_BEAM):
		bits |= qcommon.U_OLDORIGIN

	#
	# write the message
	#
	if not bits and not force:
		return		# nothing to send!

	#----------

	if bits & 0xff000000:
		bits |= qcommon.U_MOREBITS3 | qcommon.U_MOREBITS2 | qcommon.U_MOREBITS1
	elif bits & 0x00ff0000:
		bits |= qcommon.U_MOREBITS2 | qcommon.U_MOREBITS1
	elif bits & 0x0000ff00:
		bits |= qcommon.U_MOREBITS1

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

	if bits & qcommon.U_NUMBER16:
		MSG_WriteShort (msg, to.number)
	else:
		MSG_WriteByte (msg,	to.number)

	if bits & qcommon.U_MODEL:
		MSG_WriteByte (msg,	to.modelindex)
	if bits & qcommon.U_MODEL2:
		MSG_WriteByte (msg,	to.modelindex2)
	if bits & qcommon.U_MODEL3:
		MSG_WriteByte (msg,	to.modelindex3)
	if bits & qcommon.U_MODEL4:
		MSG_WriteByte (msg,	to.modelindex4)

	if bits & qcommon.U_FRAME8:
		MSG_WriteByte (msg, to.frame)
	if bits & qcommon.U_FRAME16:
		MSG_WriteShort (msg, to.frame)

	if (bits & qcommon.U_SKIN8) and (bits & qcommon.U_SKIN16):		#used for laser colors
		MSG_WriteLong (msg, to.skinnum)
	elif bits & qcommon.U_SKIN8:
		MSG_WriteByte (msg, to.skinnum)
	elif bits & qcommon.U_SKIN16:
		MSG_WriteShort (msg, to.skinnum)


	if (bits & (qcommon.U_EFFECTS8|qcommon.U_EFFECTS16)) == (qcommon.U_EFFECTS8|qcommon.U_EFFECTS16):
		MSG_WriteLong (msg, to.effects)
	elif bits & qcommon.U_EFFECTS8:
		MSG_WriteByte (msg, to.effects)
	elif bits & qcommon.U_EFFECTS16:
		MSG_WriteShort (msg, to.effects)

	if (bits & (qcommon.U_RENDERFX8|qcommon.U_RENDERFX16)) == (qcommon.U_RENDERFX8|qcommon.U_RENDERFX16):
		MSG_WriteLong (msg, to.renderfx)
	elif bits & qcommon.U_RENDERFX8:
		MSG_WriteByte (msg, to.renderfx)
	elif bits & qcommon.U_RENDERFX16:
		MSG_WriteShort (msg, to.renderfx)

	if bits & qcommon.U_ORIGIN1:
		MSG_WriteCoord (msg, to.origin[0])		
	if bits & qcommon.U_ORIGIN2:
		MSG_WriteCoord (msg, to.origin[1])
	if bits & qcommon.U_ORIGIN3:
		MSG_WriteCoord (msg, to.origin[2])

	if bits & qcommon.U_ANGLE1:
		MSG_WriteAngle(msg, to.angles[0])
	if bits & qcommon.U_ANGLE2:
		MSG_WriteAngle(msg, to.angles[1])
	if bits & qcommon.U_ANGLE3:
		MSG_WriteAngle(msg, to.angles[2])

	if bits & qcommon.U_OLDORIGIN:
	
		MSG_WriteCoord (msg, to.old_origin[0])
		MSG_WriteCoord (msg, to.old_origin[1])
		MSG_WriteCoord (msg, to.old_origin[2])
	
	if bits & qcommon.U_SOUND:
		MSG_WriteByte (msg, to.sound)
	if bits & qcommon.U_EVENT:
		MSG_WriteByte (msg, to.event)
	if bits & qcommon.U_SOLID:
		MSG_WriteShort (msg, to.solid)



#============================================================
#
# reading functions
#

def MSG_BeginReading (msg): #sizebuf_t *

	msg.readcount = 0


# returns -1 if no more characters are available
def MSG_ReadChar (msg_read): #sizebuf_t *
	assert isinstance(msg_read, qcommon.sizebuf_t)

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
	assert isinstance(msg_read, qcommon.sizebuf_t)

	#int	c;
	if msg_read.readcount+1 > msg_read.cursize:
		c = -1
	else:
		c = msg_read.data[msg_read.readcount]
	msg_read.readcount+=1
	
	return c


def MSG_ReadShort (msg_read): #sizebuf_t *
	assert isinstance(msg_read, qcommon.sizebuf_t)
	#int	c;
	
	if msg_read.readcount+2 > msg_read.cursize:
		c = -1
	else:		
		c = struct.unpack_from("<h", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 2
	
	return c

def MSG_ReadSShort (msg_read): #sizebuf_t *
	assert isinstance(msg_read, qcommon.sizebuf_t)

	#int	c;
	
	if msg_read.readcount+2 > msg_read.cursize:
		c = -1
	else:
		c = struct.unpack_from("<h", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 2
	
	return c


def MSG_ReadLong (msg_read): #sizebuf_t *
	assert isinstance(msg_read, qcommon.sizebuf_t)

	#int	c;
	
	if msg_read.readcount+4 > msg_read.cursize:
		c = -1
	else:
		c = struct.unpack_from("<L", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 4
	
	return c

def MSG_ReadSLong (msg_read): #sizebuf_t *
	assert isinstance(msg_read, qcommon.sizebuf_t)

	#int	c;
	
	if msg_read.readcount+4 > msg_read.cursize:
		c = -1
	else:
		c = struct.unpack_from("<l", msg_read.data, msg_read.readcount)[0]
	
	msg_read.readcount += 4
	
	return c

def MSG_ReadFloat (msg_read): #sizebuf_t *
	assert isinstance(msg_read, qcommon.sizebuf_t)

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
	assert isinstance(msg_read, qcommon.sizebuf_t)

	#static char	string[2048];
	#int		l,c;
	l = 0
	readStringSize = 2048
	st = bytearray()

	while l < readStringSize-1:
	
		c = MSG_ReadChar (msg_read)
		if c == -1 or c == 0:
			break
		st.append(c & 0xff)
		l+=1
	
	#string[l] = 0;
	return st.decode('ascii')


def MSG_ReadStringLine (msg_read): # sizebuf_t * (returns char *)
	assert isinstance(msg_read, qcommon.sizebuf_t)

	#static char	string[2048];
	#int		l,c;
	
	l = 0
	readStringSize = 2048
	st = bytearray()
	
	while l < readStringSize-1:
	
		c = MSG_ReadChar (msg_read)
		if c == -1 or c == 0 or c == ord('\n'):
			break
		st.append(c & 0xff)
		l+=1
	
	#string[l] = 0
	
	return st.decode('ascii')


def MSG_ReadCoord (msg_read: qcommon.sizebuf_t)->float:

	return MSG_ReadShort(msg_read) * (1.0/8.0)


def MSG_ReadPos (msg_read: qcommon.sizebuf_t):

	pos = np.empty((3,))
	pos[0] = MSG_ReadShort(msg_read) * (1.0/8.0)
	pos[1] = MSG_ReadShort(msg_read) * (1.0/8.0)
	pos[2] = MSG_ReadShort(msg_read) * (1.0/8.0)
	return pos


def MSG_ReadAngle (msg_read: qcommon.sizebuf_t)->float:

	return MSG_ReadChar(msg_read) * (360.0/256.0)


def MSG_ReadAngle16 (msg_read)->float: #(sizebuf_t *)

	return q_shared.SHORT2ANGLE(MSG_ReadShort(msg_read))


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


def MSG_ReadDeltaUsercmd (msg_read: qcommon.sizebuf_t, from_cmd, move):

	_copy_usercmd(move, from_cmd)

	bits = MSG_ReadByte (msg_read)

	if bits & qcommon.CM_ANGLE1:
		move.angles[0] = MSG_ReadShort (msg_read)
	if bits & qcommon.CM_ANGLE2:
		move.angles[1] = MSG_ReadShort (msg_read)
	if bits & qcommon.CM_ANGLE3:
		move.angles[2] = MSG_ReadShort (msg_read)

	if bits & qcommon.CM_FORWARD:
		move.forwardmove = MSG_ReadShort (msg_read)
	if bits & qcommon.CM_SIDE:
		move.sidemove = MSG_ReadShort (msg_read)
	if bits & qcommon.CM_UP:
		move.upmove = MSG_ReadShort (msg_read)

	if bits & qcommon.CM_BUTTONS:
		move.buttons = MSG_ReadByte (msg_read)

	if bits & qcommon.CM_IMPULSE:
		move.impulse = MSG_ReadByte (msg_read)

	move.msec = MSG_ReadByte (msg_read)
	move.lightlevel = MSG_ReadByte (msg_read)

def MSG_ReadData (msg_read, length: int): #sizebuf_t *, void *, int

	data = bytearray(length)
	for i in range(length):
		data[i] = MSG_ReadByte (msg_read)
	return data


#===========================================================================

def SZ_Init (buf, length): #sizebuf_t *, byte *, int

	assert isinstance(buf, qcommon.sizebuf_t)

	#memset (buf, 0, sizeof(*buf));
	#buf->data = data;
	#buf->maxsize = length;
	#if data is None:
	#	return None
	#return data.serialize()

	buf.data = bytearray()
	buf.maxsize = length


def SZ_Clear (buf: qcommon.sizebuf_t):

	buf.cursize = 0
	buf.overflowed = False
	buf.data = bytearray()

def SZ_GetSpace (buf: qcommon.sizebuf_t, length): #sizebuf_t *, int (void *)

	#void	*data;
	assert buf.maxsize > 0
	
	if buf.cursize + length > buf.maxsize:
	
		if not buf.allowoverflow:
			Com_Error (q_shared.ERR_FATAL, "SZ_GetSpace: overflow without allowoverflow set")
		
		if length > buf.maxsize:
			Com_Error (q_shared.ERR_FATAL, "SZ_GetSpace: {} is > full buffer size".format(length))
			
		Com_Printf ("SZ_GetSpace: overflow\n")
		SZ_Clear (buf)
		buf.overflowed = True
	
	offset = buf.cursize
	buf.data += bytearray(length)
	buf.cursize += length
	
	return offset



def SZ_Write (buf: qcommon.sizebuf_t, data):

	assert isinstance(data, bytes) or isinstance(data, bytearray)

	offset = SZ_GetSpace(buf, len(data))

	buf.data[offset:offset+len(data)] = data


def SZ_Print (buf: qcommon.sizebuf_t, data): #char *

	#int		len;
	assert isinstance(data, str)
	
	data = data.encode('ascii')
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
		#memcpy ((byte *)SZ_GetSpace(buf, len),data,len);



#============================================================================


"""
================
COM_CheckParm

Returns the position (1 to argc-1) in the program's argument list
where the given parameter apears, or 0 if not present
================
*/
"""
def COM_CheckParm (parm): #char *

	for i in range(1, com_argc):
		if com_argv[i] == parm:
			return i

	return 0


def COM_Argc ():

	return com_argc


def COM_Argv (arg):

	if arg < 0 or arg >= com_argc or com_argv[arg] is None:
		return ""
	return com_argv[arg]


def COM_ClearArgv (arg):

	if arg < 0 or arg >= com_argc or com_argv[arg] is None:
		return
	com_argv[arg] = ""

"""
================
COM_InitArgv
================
"""
def COM_InitArgv ():

	global com_argc, com_argv

	argc = len(sys.argv)
	if argc > MAX_NUM_ARGVS:
		Com_Error (q_shared.ERR_FATAL, "argc > MAX_NUM_ARGVS");
	com_argc = argc;
	for i in range (argc):
	
		if sys.argv[i] is None or len(sys.argv[i]) >= q_shared.MAX_TOKEN_CHARS:
			com_argv[i] = ""
		else:
			com_argv[i] = sys.argv[i]

"""
================
COM_AddParm

Adds the given string at the end of the current argument list
================
"""
def COM_AddParm (parm): #char *

	global com_argc

	if com_argc == MAX_NUM_ARGVS:
		Com_Error (q_shared.ERR_FATAL, "COM_AddParm: MAX_NUM)ARGS")
	com_argv[com_argc] = parm
	com_argc += 1

# just for debugging
def memsearch (start, count, search): #byte *, int, int (returns int)
	for i in range(count):
		if start[i] == search:
			return i
	return -1


def CopyString (s): #char *
	# strings are immutable, so no copy is needed in Python
	return s


"""


"""

"""
def Info_Print (s): #char *

	#char	key[512];
	#char	value[512];
	#char	*o;
	#int		l;

	i = 0 # index into s
	if i < len(s) and s[i] == '\\':
		i += 1
	while i < len(s):
	
		o = i
		while i < len(s) and s[i] != '\\':
			i += 1
		key = s[o:i]

		l = len(key)
		if l < 20:
			key = key + ' ' * (20-l)
		Com_Printf ("{}".format(key))

		if i >= len(s):
		
			Com_Printf ("MISSING VALUE\n")
			return
		
		i += 1
		o = i
		while i < len(s) and s[i] != '\\':
			i += 1
		value = s[o:i]

		if i < len(s):
			i += 1
		Com_Printf ("{}\n".format(value))
	
"""

"""
/*
==============================================================================

						ZONE MEMORY ALLOCATION

just cleared malloc with counters now...

==============================================================================
*/

#define	Z_MAGIC		0x1d1d


typedef struct zhead_s
{
	struct zhead_s	*prev, *next;
	short	magic;
	short	tag;			// for group free
	int		size;
} zhead_t;

zhead_t		z_chain;
"""
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
		Com_Error (q_shared.ERR_FATAL, "Z_Free: bad magic")

	ptr.prev.next = ptr.next
	ptr.next.prev = ptr.prev

	z_count -= 1
	z_bytes -= ptr.size
	ptr.next = ptr.prev = None
"""
========================
Z_Stats_f
========================
"""
def Z_Stats_f ():

	Com_Printf ("{} bytes in {} blocks\n", z_bytes, z_count)

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
	Sys_Error ("COM_BlockSequenceCheckByte called\n")
	return 0
"""
#if 0
	int		checksum;
	byte	buf[68];
	byte	*p;
	float temp;
	byte c;

	temp = bytedirs[(sequence/3) % qcommon.NUMVERTEXNORMALS][sequence % 3];
	temp = LittleFloat(temp);
	p = ((byte *)&temp);

	if (length > 60)
		length = 60;
	memcpy (buf, base, length);

	buf[length] = (sequence & 0xff) ^ p[0];
	buf[length+1] = p[1];
	buf[length+2] = ((sequence>>8) & 0xff) ^ p[2];
	buf[length+3] = p[3];

	temp = bytedirs[((sequence+challenge)/3) % qcommon.NUMVERTEXNORMALS][(sequence+challenge) % 3];
	temp = LittleFloat(temp);
	p = ((byte *)&temp);

	buf[length+4] = (sequence & 0xff) ^ p[3];
	buf[length+5] = (challenge & 0xff) ^ p[2];
	buf[length+6] = ((sequence>>8) & 0xff) ^ p[1];
	buf[length+7] = ((challenge >> 7) & 0xff) ^ p[0];

	length += 8;

	checksum = LittleLong(Com_BlockChecksum (buf, length));

	checksum &= 0xff;

	return checksum;
#endif
	return 0;
}

static byte chktbl[1024] = {
0x84, 0x47, 0x51, 0xc1, 0x93, 0x22, 0x21, 0x24, 0x2f, 0x66, 0x60, 0x4d, 0xb0, 0x7c, 0xda,
0x88, 0x54, 0x15, 0x2b, 0xc6, 0x6c, 0x89, 0xc5, 0x9d, 0x48, 0xee, 0xe6, 0x8a, 0xb5, 0xf4,
0xcb, 0xfb, 0xf1, 0x0c, 0x2e, 0xa0, 0xd7, 0xc9, 0x1f, 0xd6, 0x06, 0x9a, 0x09, 0x41, 0x54,
0x67, 0x46, 0xc7, 0x74, 0xe3, 0xc8, 0xb6, 0x5d, 0xa6, 0x36, 0xc4, 0xab, 0x2c, 0x7e, 0x85,
0xa8, 0xa4, 0xa6, 0x4d, 0x96, 0x19, 0x19, 0x9a, 0xcc, 0xd8, 0xac, 0x39, 0x5e, 0x3c, 0xf2,
0xf5, 0x5a, 0x72, 0xe5, 0xa9, 0xd1, 0xb3, 0x23, 0x82, 0x6f, 0x29, 0xcb, 0xd1, 0xcc, 0x71,
0xfb, 0xea, 0x92, 0xeb, 0x1c, 0xca, 0x4c, 0x70, 0xfe, 0x4d, 0xc9, 0x67, 0x43, 0x47, 0x94,
0xb9, 0x47, 0xbc, 0x3f, 0x01, 0xab, 0x7b, 0xa6, 0xe2, 0x76, 0xef, 0x5a, 0x7a, 0x29, 0x0b,
0x51, 0x54, 0x67, 0xd8, 0x1c, 0x14, 0x3e, 0x29, 0xec, 0xe9, 0x2d, 0x48, 0x67, 0xff, 0xed,
0x54, 0x4f, 0x48, 0xc0, 0xaa, 0x61, 0xf7, 0x78, 0x12, 0x03, 0x7a, 0x9e, 0x8b, 0xcf, 0x83,
0x7b, 0xae, 0xca, 0x7b, 0xd9, 0xe9, 0x53, 0x2a, 0xeb, 0xd2, 0xd8, 0xcd, 0xa3, 0x10, 0x25,
0x78, 0x5a, 0xb5, 0x23, 0x06, 0x93, 0xb7, 0x84, 0xd2, 0xbd, 0x96, 0x75, 0xa5, 0x5e, 0xcf,
0x4e, 0xe9, 0x50, 0xa1, 0xe6, 0x9d, 0xb1, 0xe3, 0x85, 0x66, 0x28, 0x4e, 0x43, 0xdc, 0x6e,
0xbb, 0x33, 0x9e, 0xf3, 0x0d, 0x00, 0xc1, 0xcf, 0x67, 0x34, 0x06, 0x7c, 0x71, 0xe3, 0x63,
0xb7, 0xb7, 0xdf, 0x92, 0xc4, 0xc2, 0x25, 0x5c, 0xff, 0xc3, 0x6e, 0xfc, 0xaa, 0x1e, 0x2a,
0x48, 0x11, 0x1c, 0x36, 0x68, 0x78, 0x86, 0x79, 0x30, 0xc3, 0xd6, 0xde, 0xbc, 0x3a, 0x2a,
0x6d, 0x1e, 0x46, 0xdd, 0xe0, 0x80, 0x1e, 0x44, 0x3b, 0x6f, 0xaf, 0x31, 0xda, 0xa2, 0xbd,
0x77, 0x06, 0x56, 0xc0, 0xb7, 0x92, 0x4b, 0x37, 0xc0, 0xfc, 0xc2, 0xd5, 0xfb, 0xa8, 0xda,
0xf5, 0x57, 0xa8, 0x18, 0xc0, 0xdf, 0xe7, 0xaa, 0x2a, 0xe0, 0x7c, 0x6f, 0x77, 0xb1, 0x26,
0xba, 0xf9, 0x2e, 0x1d, 0x16, 0xcb, 0xb8, 0xa2, 0x44, 0xd5, 0x2f, 0x1a, 0x79, 0x74, 0x87,
0x4b, 0x00, 0xc9, 0x4a, 0x3a, 0x65, 0x8f, 0xe6, 0x5d, 0xe5, 0x0a, 0x77, 0xd8, 0x1a, 0x14,
0x41, 0x75, 0xb1, 0xe2, 0x50, 0x2c, 0x93, 0x38, 0x2b, 0x6d, 0xf3, 0xf6, 0xdb, 0x1f, 0xcd,
0xff, 0x14, 0x70, 0xe7, 0x16, 0xe8, 0x3d, 0xf0, 0xe3, 0xbc, 0x5e, 0xb6, 0x3f, 0xcc, 0x81,
0x24, 0x67, 0xf3, 0x97, 0x3b, 0xfe, 0x3a, 0x96, 0x85, 0xdf, 0xe4, 0x6e, 0x3c, 0x85, 0x05,
0x0e, 0xa3, 0x2b, 0x07, 0xc8, 0xbf, 0xe5, 0x13, 0x82, 0x62, 0x08, 0x61, 0x69, 0x4b, 0x47,
0x62, 0x73, 0x44, 0x64, 0x8e, 0xe2, 0x91, 0xa6, 0x9a, 0xb7, 0xe9, 0x04, 0xb6, 0x54, 0x0c,
0xc5, 0xa9, 0x47, 0xa6, 0xc9, 0x08, 0xfe, 0x4e, 0xa6, 0xcc, 0x8a, 0x5b, 0x90, 0x6f, 0x2b,
0x3f, 0xb6, 0x0a, 0x96, 0xc0, 0x78, 0x58, 0x3c, 0x76, 0x6d, 0x94, 0x1a, 0xe4, 0x4e, 0xb8,
0x38, 0xbb, 0xf5, 0xeb, 0x29, 0xd8, 0xb0, 0xf3, 0x15, 0x1e, 0x99, 0x96, 0x3c, 0x5d, 0x63,
0xd5, 0xb1, 0xad, 0x52, 0xb8, 0x55, 0x70, 0x75, 0x3e, 0x1a, 0xd5, 0xda, 0xf6, 0x7a, 0x48,
0x7d, 0x44, 0x41, 0xf9, 0x11, 0xce, 0xd7, 0xca, 0xa5, 0x3d, 0x7a, 0x79, 0x7e, 0x7d, 0x25,
0x1b, 0x77, 0xbc, 0xf7, 0xc7, 0x0f, 0x84, 0x95, 0x10, 0x92, 0x67, 0x15, 0x11, 0x5a, 0x5e,
0x41, 0x66, 0x0f, 0x38, 0x03, 0xb2, 0xf1, 0x5d, 0xf8, 0xab, 0xc0, 0x02, 0x76, 0x84, 0x28,
0xf4, 0x9d, 0x56, 0x46, 0x60, 0x20, 0xdb, 0x68, 0xa7, 0xbb, 0xee, 0xac, 0x15, 0x01, 0x2f,
0x20, 0x09, 0xdb, 0xc0, 0x16, 0xa1, 0x89, 0xf9, 0x94, 0x59, 0x00, 0xc1, 0x76, 0xbf, 0xc1,
0x4d, 0x5d, 0x2d, 0xa9, 0x85, 0x2c, 0xd6, 0xd3, 0x14, 0xcc, 0x02, 0xc3, 0xc2, 0xfa, 0x6b,
0xb7, 0xa6, 0xef, 0xdd, 0x12, 0x26, 0xa4, 0x63, 0xe3, 0x62, 0xbd, 0x56, 0x8a, 0x52, 0x2b,
0xb9, 0xdf, 0x09, 0xbc, 0x0e, 0x97, 0xa9, 0xb0, 0x82, 0x46, 0x08, 0xd5, 0x1a, 0x8e, 0x1b,
0xa7, 0x90, 0x98, 0xb9, 0xbb, 0x3c, 0x17, 0x9a, 0xf2, 0x82, 0xba, 0x64, 0x0a, 0x7f, 0xca,
0x5a, 0x8c, 0x7c, 0xd3, 0x79, 0x09, 0x5b, 0x26, 0xbb, 0xbd, 0x25, 0xdf, 0x3d, 0x6f, 0x9a,
0x8f, 0xee, 0x21, 0x66, 0xb0, 0x8d, 0x84, 0x4c, 0x91, 0x45, 0xd4, 0x77, 0x4f, 0xb3, 0x8c,
0xbc, 0xa8, 0x99, 0xaa, 0x19, 0x53, 0x7c, 0x02, 0x87, 0xbb, 0x0b, 0x7c, 0x1a, 0x2d, 0xdf,
0x48, 0x44, 0x06, 0xd6, 0x7d, 0x0c, 0x2d, 0x35, 0x76, 0xae, 0xc4, 0x5f, 0x71, 0x85, 0x97,
0xc4, 0x3d, 0xef, 0x52, 0xbe, 0x00, 0xe4, 0xcd, 0x49, 0xd1, 0xd1, 0x1c, 0x3c, 0xd0, 0x1c,
0x42, 0xaf, 0xd4, 0xbd, 0x58, 0x34, 0x07, 0x32, 0xee, 0xb9, 0xb5, 0xea, 0xff, 0xd7, 0x8c,
0x0d, 0x2e, 0x2f, 0xaf, 0x87, 0xbb, 0xe6, 0x52, 0x71, 0x22, 0xf5, 0x25, 0x17, 0xa1, 0x82,
0x04, 0xc2, 0x4a, 0xbd, 0x57, 0xc6, 0xab, 0xc8, 0x35, 0x0c, 0x3c, 0xd9, 0xc2, 0x43, 0xdb,
0x27, 0x92, 0xcf, 0xb8, 0x25, 0x60, 0xfa, 0x21, 0x3b, 0x04, 0x52, 0xc8, 0x96, 0xba, 0x74,
0xe3, 0x67, 0x3e, 0x8e, 0x8d, 0x61, 0x90, 0x92, 0x59, 0xb6, 0x1a, 0x1c, 0x5e, 0x21, 0xc1,
0x65, 0xe5, 0xa6, 0x34, 0x05, 0x6f, 0xc5, 0x60, 0xb1, 0x83, 0xc1, 0xd5, 0xd5, 0xed, 0xd9,
0xc7, 0x11, 0x7b, 0x49, 0x7a, 0xf9, 0xf9, 0x84, 0x47, 0x9b, 0xe2, 0xa5, 0x82, 0xe0, 0xc2,
0x88, 0xd0, 0xb2, 0x58, 0x88, 0x7f, 0x45, 0x09, 0x67, 0x74, 0x61, 0xbf, 0xe6, 0x40, 0xe2,
0x9d, 0xc2, 0x47, 0x05, 0x89, 0xed, 0xcb, 0xbb, 0xb7, 0x27, 0xe7, 0xdc, 0x7a, 0xfd, 0xbf,
0xa8, 0xd0, 0xaa, 0x10, 0x39, 0x3c, 0x20, 0xf0, 0xd3, 0x6e, 0xb1, 0x72, 0xf8, 0xe6, 0x0f,
0xef, 0x37, 0xe5, 0x09, 0x33, 0x5a, 0x83, 0x43, 0x80, 0x4f, 0x65, 0x2f, 0x7c, 0x8c, 0x6a,
0xa0, 0x82, 0x0c, 0xd4, 0xd4, 0xfa, 0x81, 0x60, 0x3d, 0xdf, 0x06, 0xf1, 0x5f, 0x08, 0x0d,
0x6d, 0x43, 0xf2, 0xe3, 0x11, 0x7d, 0x80, 0x32, 0xc5, 0xfb, 0xc5, 0xd9, 0x27, 0xec, 0xc6,
0x4e, 0x65, 0x27, 0x76, 0x87, 0xa6, 0xee, 0xee, 0xd7, 0x8b, 0xd1, 0xa0, 0x5c, 0xb0, 0x42,
0x13, 0x0e, 0x95, 0x4a, 0xf2, 0x06, 0xc6, 0x43, 0x33, 0xf4, 0xc7, 0xf8, 0xe7, 0x1f, 0xdd,
0xe4, 0x46, 0x4a, 0x70, 0x39, 0x6c, 0xd0, 0xed, 0xca, 0xbe, 0x60, 0x3b, 0xd1, 0x7b, 0x57,
0x48, 0xe5, 0x3a, 0x79, 0xc1, 0x69, 0x33, 0x53, 0x1b, 0x80, 0xb8, 0x91, 0x7d, 0xb4, 0xf6,
0x17, 0x1a, 0x1d, 0x5a, 0x32, 0xd6, 0xcc, 0x71, 0x29, 0x3f, 0x28, 0xbb, 0xf3, 0x5e, 0x71,
0xb8, 0x43, 0xaf, 0xf8, 0xb9, 0x64, 0xef, 0xc4, 0xa5, 0x6c, 0x08, 0x53, 0xc7, 0x00, 0x10,
0x39, 0x4f, 0xdd, 0xe4, 0xb6, 0x19, 0x27, 0xfb, 0xb8, 0xf5, 0x32, 0x73, 0xe5, 0xcb, 0x32
};


====================
COM_BlockSequenceCRCByte

For proxy protecting
====================
"""
# chktbl table from the original C source.
chktbl = bytes([
    0x84, 0x47, 0x51, 0xc1, 0x93, 0x22, 0x21, 0x24, 0x2f, 0x66, 0x60, 0x4d, 0xb0, 0x7c, 0xda, 0x88,
    0x54, 0x15, 0x2b, 0xc6, 0x6c, 0x89, 0xc5, 0x9d, 0x48, 0xee, 0xe6, 0x8a, 0xb5, 0xf4, 0xcb, 0xfb,
    0xf1, 0x0c, 0x2e, 0xa0, 0xd7, 0xc9, 0x1f, 0xd6, 0x06, 0x9a, 0x09, 0x41, 0x54, 0x67, 0x46, 0xc7,
    0x74, 0xe3, 0xc8, 0xb6, 0x5d, 0xa6, 0x36, 0xc4, 0xab, 0x2c, 0x7e, 0x85, 0xa8, 0xa4, 0xa6, 0x4d,
    0x96, 0x19, 0x19, 0x9a, 0xcc, 0xd8, 0xac, 0x39, 0x5e, 0x3c, 0xf2, 0xf5, 0x5a, 0x72, 0xe5, 0xa9,
    0xd1, 0xb3, 0x23, 0x82, 0x6f, 0x29, 0xcb, 0xd1, 0xcc, 0x71, 0xfb, 0xea, 0x92, 0xeb, 0x1c, 0xca,
    0x4c, 0x70, 0xfe, 0x4d, 0xc9, 0x67, 0x43, 0x47, 0x94, 0xb9, 0x47, 0xbc, 0x3f, 0x01, 0xab, 0x7b,
    0xa6, 0xe2, 0x76, 0xef, 0x5a, 0x7a, 0x29, 0x0b, 0x51, 0x54, 0x67, 0xd8, 0x1c, 0x14, 0x3e, 0x29,
    0xec, 0xe9, 0x2d, 0x48, 0x67, 0xff, 0xed, 0x54, 0x4f, 0x48, 0xc0, 0xaa, 0x61, 0xf7, 0x78, 0x12,
    0x03, 0x7a, 0x9e, 0x8b, 0xcf, 0x83, 0x7b, 0xae, 0xca, 0x7b, 0xd9, 0xe9, 0x53, 0x2a, 0xeb, 0xd2,
    0xd8, 0xcd, 0xa3, 0x10, 0x25, 0x78, 0x5a, 0xb5, 0x23, 0x06, 0x93, 0xb7, 0x84, 0xd2, 0xbd, 0x96,
    0x75, 0xa5, 0x5e, 0xcf, 0x4e, 0xe9, 0x50, 0xa1, 0xe6, 0x9d, 0xb1, 0xe3, 0x85, 0x66, 0x28, 0x4e,
    0x43, 0xdc, 0x6e, 0xbb, 0x33, 0x9e, 0xf3, 0x0d, 0x00, 0xc1, 0xcf, 0x67, 0x34, 0x06, 0x7c, 0x71,
    0xe3, 0x63, 0xb7, 0xb7, 0xdf, 0x92, 0xc4, 0xc2, 0x25, 0x5c, 0xff, 0xc3, 0x6e, 0xfc, 0xaa, 0x1e,
    0x2a, 0x48, 0x11, 0x1c, 0x36, 0x68, 0x78, 0x86, 0x79, 0x30, 0xc3, 0xd6, 0xde, 0xbc, 0x3a, 0x2a,
    0x6d, 0x1e, 0x46, 0xdd, 0xe0, 0x80, 0x1e, 0x44, 0x3b, 0x6f, 0xaf, 0x31, 0xda, 0xa2, 0xbd, 0x77,
    0x06, 0x56, 0xc0, 0xb7, 0x92, 0x4b, 0x37, 0xc0, 0xfc, 0xc2, 0xd5, 0xfb, 0xa8, 0xda, 0xf5, 0x57,
    0xa8, 0x18, 0xc0, 0xdf, 0xe7, 0xaa, 0x2a, 0xe0, 0x7c, 0x6f, 0x77, 0xb1, 0x26, 0xba, 0xf9, 0x2e,
    0x1d, 0x16, 0xcb, 0xb8, 0xa2, 0x44, 0xd5, 0x2f, 0x1a, 0x79, 0x74, 0x87, 0x4b, 0x00, 0xc9, 0x4a,
    0x3a, 0x65, 0x8f, 0xe6, 0x5d, 0xe5, 0x0a, 0x77, 0xd8, 0x1a, 0x14, 0x41, 0x75, 0xb1, 0xe2, 0x50,
    0x2c, 0x93, 0x38, 0x2b, 0x6d, 0xf3, 0xf6, 0xdb, 0x1f, 0xcd, 0xff, 0x14, 0x70, 0xe7, 0x16, 0xe8,
    0x3d, 0xf0, 0xe3, 0xbc, 0x5e, 0xb6, 0x3f, 0xcc, 0x81, 0x24, 0x67, 0xf3, 0x97, 0x3b, 0xfe, 0x3a,
    0x96, 0x85, 0xdf, 0xe4, 0x6e, 0x3c, 0x85, 0x05, 0x0e, 0xa3, 0x2b, 0x07, 0xc8, 0xbf, 0xe5, 0x13,
    0x82, 0x62, 0x08, 0x61, 0x69, 0x4b, 0x47, 0x62, 0x73, 0x44, 0x64, 0x8e, 0xe2, 0x91, 0xa6, 0x9a,
    0xb7, 0xe9, 0x04, 0xb6, 0x54, 0x0c, 0xc5, 0xa9, 0x47, 0xa6, 0xc9, 0x08, 0xfe, 0x4e, 0xa6, 0xcc,
    0x8a, 0x5b, 0x90, 0x6f, 0x2b, 0x3f, 0xb6, 0x0a, 0x96, 0xc0, 0x78, 0x58, 0x3c, 0x76, 0x6d, 0x94,
    0x1a, 0xe4, 0x4e, 0xb8, 0x38, 0xbb, 0xf5, 0xeb, 0x29, 0xd8, 0xb0, 0xf3, 0x15, 0x1e, 0x99, 0x96,
    0x3c, 0x5d, 0x63, 0xd5, 0xb1, 0xad, 0x52, 0xb8, 0x55, 0x70, 0x75, 0x3e, 0x1a, 0xd5, 0xda, 0xf6,
    0x7a, 0x48, 0x7d, 0x44, 0x41, 0xf9, 0x11, 0xce, 0xd7, 0xca, 0xa5, 0x3d, 0x7a, 0x79, 0x7e, 0x7d,
    0x25, 0x1b, 0x77, 0xbc, 0xf7, 0xc7, 0x0f, 0x84, 0x95, 0x10, 0x92, 0x67, 0x15, 0x11, 0x5a, 0x5e,
    0x41, 0x66, 0x0f, 0x38, 0x03, 0xb2, 0xf1, 0x5d, 0xf8, 0xab, 0xc0, 0x02, 0x76, 0x84, 0x28, 0xf4,
    0x9d, 0x56, 0x46, 0x60, 0x20, 0xdb, 0x68, 0xa7, 0xbb, 0xee, 0xac, 0x15, 0x01, 0x2f, 0x20, 0x09,
    0xdb, 0xc0, 0x16, 0xa1, 0x89, 0xf9, 0x94, 0x59, 0x00, 0xc1, 0x76, 0xbf, 0xc1, 0x4d, 0x5d, 0x2d,
    0xa9, 0x85, 0x2c, 0xd6, 0xd3, 0x14, 0xcc, 0x02, 0xc3, 0xc2, 0xfa, 0x6b, 0xb7, 0xa6, 0xef, 0xdd,
    0x12, 0x26, 0xa4, 0x63, 0xe3, 0x62, 0xbd, 0x56, 0x8a, 0x52, 0x2b, 0xb9, 0xdf, 0x09, 0xbc, 0x0e,
    0x97, 0xa9, 0xb0, 0x82, 0x46, 0x08, 0xd5, 0x1a, 0x8e, 0x1b, 0xa7, 0x90, 0x98, 0xb9, 0xbb, 0x3c,
    0x17, 0x9a, 0xf2, 0x82, 0xba, 0x64, 0x0a, 0x7f, 0xca, 0x5a, 0x8c, 0x7c, 0xd3, 0x79, 0x09, 0x5b,
    0x26, 0xbb, 0xbd, 0x25, 0xdf, 0x3d, 0x6f, 0x9a, 0x8f, 0xee, 0x21, 0x66, 0xb0, 0x8d, 0x84, 0x4c,
    0x91, 0x45, 0xd4, 0x77, 0x4f, 0xb3, 0x8c, 0xbc, 0xa8, 0x99, 0xaa, 0x19, 0x53, 0x7c, 0x02, 0x87,
    0xbb, 0x0b, 0x7c, 0x1a, 0x2d, 0xdf, 0x48, 0x44, 0x06, 0xd6, 0x7d, 0x0c, 0x2d, 0x35, 0x76, 0xae,
    0xc4, 0x5f, 0x71, 0x85, 0x97, 0xc4, 0x3d, 0xef, 0x52, 0xbe, 0x00, 0xe4, 0xcd, 0x49, 0xd1, 0xd1,
    0x1c, 0x3c, 0xd0, 0x1c, 0x42, 0xaf, 0xd4, 0xbd, 0x58, 0x34, 0x07, 0x32, 0xee, 0xb9, 0xb5, 0xea,
    0xff, 0xd7, 0x8c, 0x0d, 0x2e, 0x2f, 0xaf, 0x87, 0xbb, 0xe6, 0x52, 0x71, 0x22, 0xf5, 0x25, 0x17,
    0xa1, 0x82, 0x04, 0xc2, 0x4a, 0xbd, 0x57, 0xc6, 0xab, 0xc8, 0x35, 0x0c, 0x3c, 0xd9, 0xc2, 0x43,
    0xdb, 0x27, 0x92, 0xcf, 0xb8, 0x25, 0x60, 0xfa, 0x21, 0x3b, 0x04, 0x52, 0xc8, 0x96, 0xba, 0x74,
    0xe3, 0x67, 0x3e, 0x8e, 0x8d, 0x61, 0x90, 0x92, 0x59, 0xb6, 0x1a, 0x1c, 0x5e, 0x21, 0xc1, 0x65,
    0xe5, 0xa6, 0x34, 0x05, 0x6f, 0xc5, 0x60, 0xb1, 0x83, 0xc1, 0xd5, 0xd5, 0xed, 0xd9, 0xc7, 0x11,
    0x7b, 0x49, 0x7a, 0xf9, 0xf9, 0x84, 0x47, 0x9b, 0xe2, 0xa5, 0x82, 0xe0, 0xc2, 0x88, 0xd0, 0xb2,
    0x58, 0x88, 0x7f, 0x45, 0x09, 0x67, 0x74, 0x61, 0xbf, 0xe6, 0x40, 0xe2, 0x9d, 0xc2, 0x47, 0x05,
    0x89, 0xed, 0xcb, 0xbb, 0xb7, 0x27, 0xe7, 0xdc, 0x7a, 0xfd, 0xbf, 0xa8, 0xd0, 0xaa, 0x10, 0x39,
    0x3c, 0x20, 0xf0, 0xd3, 0x6e, 0xb1, 0x72, 0xf8, 0xe6, 0x0f, 0xef, 0x37, 0xe5, 0x09, 0x33, 0x5a,
    0x83, 0x43, 0x80, 0x4f, 0x65, 0x2f, 0x7c, 0x8c, 0x6a, 0xa0, 0x82, 0x0c, 0xd4, 0xd4, 0xfa, 0x81,
    0x60, 0x3d, 0xdf, 0x06, 0xf1, 0x5f, 0x08, 0x0d, 0x6d, 0x43, 0xf2, 0xe3, 0x11, 0x7d, 0x80, 0x32,
    0xc5, 0xfb, 0xc5, 0xd9, 0x27, 0xec, 0xc6, 0x4e, 0x65, 0x27, 0x76, 0x87, 0xa6, 0xee, 0xee, 0xd7,
    0x8b, 0xd1, 0xa0, 0x5c, 0xb0, 0x42, 0x13, 0x0e, 0x95, 0x4a, 0xf2, 0x06, 0xc6, 0x43, 0x33, 0xf4,
    0xc7, 0xf8, 0xe7, 0x1f, 0xdd, 0xe4, 0x46, 0x4a, 0x70, 0x39, 0x6c, 0xd0, 0xed, 0xca, 0xbe, 0x60,
    0x3b, 0xd1, 0x7b, 0x57, 0x48, 0xe5, 0x3a, 0x79, 0xc1, 0x69, 0x33, 0x53, 0x1b, 0x80, 0xb8, 0x91,
    0x7d, 0xb4, 0xf6, 0x17, 0x1a, 0x1d, 0x5a, 0x32, 0xd6, 0xcc, 0x71, 0x29, 0x3f, 0x28, 0xbb, 0xf3,
    0x5e, 0x71, 0xb8, 0x43, 0xaf, 0xf8, 0xb9, 0x64, 0xef, 0xc4, 0xa5, 0x6c, 0x08, 0x53, 0xc7, 0x00,
    0x10, 0x39, 0x4f, 0xdd, 0xe4, 0xb6, 0x19, 0x27, 0xfb, 0xb8, 0xf5, 0x32, 0x73, 0xe5, 0xcb, 0x32,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])


def COM_BlockSequenceCRCByte (buff, baseOffset, length, sequence): #byte *, int , int

	if sequence < 0:
		raise RuntimeError("sequence < 0, this shouldn't happen")

	if length > 60:
		length = 60

	base = buff.data if hasattr(buff, "data") else buff
	chkb = bytearray(base[baseOffset:baseOffset + length])

	offset = sequence % (len(chktbl) - 4)
	chkb.extend(chktbl[offset:offset + 4])
	length += 4

	crc_value = crc.CRC_Block(chkb, length)
	xsum = 0
	for n in range(length):
		xsum += chkb[n]

	crc_value = (crc_value ^ xsum) & 0xFF
	return bytes([crc_value])

"""
#========================================================

float	frand(void)
{
	return (rand()&32767)* (1.0/32767);
}

float	crand(void)
{
	return (rand()&32767)* (2.0/32767) - 1;
}

void Key_Init (void);
void SCR_EndLoadingPlaque (void);

"""

def frand(): # 0 to 1
	return random.random()

def crand(): # -1 to 1
	return random.random() * 2.0 - 1.0

"""
=============
Com_Error_f

Just throw a fatal error to
test error shutdown procedures
=============
"""
def Com_Error_f ():

	Com_Error (q_shared.ERR_FATAL, cmd.Cmd_Argv(1))

"""
=================
Qcommon_Init
=================
"""

def Qcommon_Init (): #int argc, char **argv

	pygame.mixer.pre_init(44100//2)
	pygame.init()
	global host_speeds, log_stats, developer, timescale, fixedtime, logfile_active, showtrace, dedicated

	#screen = pygame.display.set_mode((1000,600), 0, 32)

	#char	*s;

	#if (setjmp (abortframe) )
	#	Sys_Error ("Error during initialization");

	#z_chain.next = z_chain.prev = &z_chain

	# prepare enough of the subsystems to handle
	# cvar and command buffer management
	COM_InitArgv () #argc, argv

	q_shared.Swap_Init ()
	cmd.Cbuf_Init ()

	cmd.Cmd_Init ()
	cvar.Cvar_Init()

	keys.Key_Init ()
	
	# we need to add the early commands twice, because
	# a basedir or cddir needs to be set before execing
	# config files, but we want other parms to override
	# the settings of the config files
	cmd.Cbuf_AddEarlyCommands (False)
	cmd.Cbuf_Execute ()

	files.FS_InitFilesystem ();

	cmd.Cbuf_AddText ("exec default.cfg\n");
	cmd.Cbuf_AddText ("exec config.cfg\n");

	cmd.Cbuf_AddEarlyCommands (True);
	cmd.Cbuf_Execute ();

	#
	# init commands and vars
	#
	cmd.Cmd_AddCommand ("z_stats", Z_Stats_f);
	cmd.Cmd_AddCommand ("error", Com_Error_f);

	host_speeds = cvar.Cvar_Get ("host_speeds", "0", 0);
	log_stats = cvar.Cvar_Get ("log_stats", "0", 0);
	developer = cvar.Cvar_Get ("developer", "0", 0);
	timescale = cvar.Cvar_Get ("timescale", "1", 0);
	fixedtime = cvar.Cvar_Get ("fixedtime", "0", 0);
	logfile_active = cvar.Cvar_Get ("logfile", "0", 0);
	showtrace = cvar.Cvar_Get ("showtrace", "0", 0);
	##ifdef DEDICATED_ONLY
	#dedicated = Cvar_Get ("dedicated", "1", q_shared.CVAR_NOSET);
	##else
	dedicated = cvar.Cvar_Get ("dedicated", "0", q_shared.CVAR_NOSET);
	##endif
	
	s = "{:4.2f}".format(qcommon.VERSION)
	cvar.Cvar_Get ("version", s, q_shared.CVAR_SERVERINFO|q_shared.CVAR_NOSET)
	
	if dedicated.value:
		cmd.Cmd_AddCommand ("quit", Com_Quit)

	sys_linux.Sys_Init ()

	net_udp.NET_Init ()
	net_chan.Netchan_Init ()

	sv_main.SV_Init ()
	cl_main.CL_Init ()

	# add + commands from command line
	if not cmd.Cbuf_AddLateCommands ():
		# if the user didn't give any commands, run default action
		if not dedicated.value:
			cmd.Cbuf_AddText ("d1\n")
		else:
			cmd.Cbuf_AddText ("dedicated_start\n")
		cmd.Cbuf_Execute ()
	
	else:
		# the user asked for something explicit
		# so drop the loading plaque
		cl_scrn.SCR_EndLoadingPlaque ()

	Com_Printf ("====== Quake2 Initialized ======\n\n")


"""
=================
Qcommon_Frame
=================
"""
def Qcommon_Frame (msec): #int
	
	global host_speeds
	global time_before_game, time_after_game, time_before_ref, time_after_ref

	"""
	char	*s;
	int		time_before, time_between, time_after;

	if (setjmp (abortframe) )
		return;			// an ERR_DROP was thrown

	if ( log_stats->modified )
	{
		log_stats->modified = false;
		if ( log_stats->value )
		{
			if ( log_stats_file )
			{
				fclose( log_stats_file );
				log_stats_file = 0;
			}
			log_stats_file = fopen( "stats.log", "w" );
			if ( log_stats_file )
				fprintf( log_stats_file, "entities,dlights,parts,frame time\n" );
		}
		else
		{
			if ( log_stats_file )
			{
				fclose( log_stats_file );
				log_stats_file = 0;
			}
		}
	}

	if (fixedtime->value)
		msec = fixedtime->value;
	else if (timescale->value)
	{
		msec *= timescale->value;
		if (msec < 1)
			msec = 1;
	}

	if (showtrace->value)
	{
		extern	int c_traces, c_brush_traces;
		extern	int	c_pointcontents;

		Com_Printf ("%4i traces  %4i points\n", c_traces, c_pointcontents);
		c_traces = 0;
		c_brush_traces = 0;
		c_pointcontents = 0;
	}
"""
	try: # if (setjmp (abortframe) ) return;, an ERR_DROP was thrown
		firstLoop = True
		s = None
		while firstLoop or s is not None:
			firstLoop = False
			s = sys_linux.Sys_ConsoleInput ()
			if s is not None:
				cmd.Cbuf_AddText ("{}\n".format(s))
	
		cmd.Cbuf_Execute ()
	


		if host_speeds.value:
			time_before = q_shlinux.Sys_Milliseconds ()
	
		sv_main.SV_Frame (msec)
	
		if host_speeds.value:
			time_between = q_shlinux.Sys_Milliseconds ()
	
		cl_main.CL_Frame (msec)
	
		if host_speeds.value:
			time_after = q_shlinux.Sys_Milliseconds ()

		if host_speeds.value:
	
			#int			all, sv, gm, cl, rf;

			allt = time_after - time_before
			sv = time_between - time_before
			cl = time_after - time_between
			gm = time_after_game - time_before_game
			rf = time_after_ref - time_before_ref
			sv -= gm
			cl -= rf
			Com_Printf ("all:{: 3d} sv:{: 3d} gm:{: 3d} cl:{: 3d} rf:{: 3d}\n".format(
				allt, sv, gm, cl, rf))
	except abortframe:
		return

"""
=================
Qcommon_Shutdown
=================
"""
def Qcommon_Shutdown ():

	pass


def COM_Parse(data, cursor):
	"""Expose COM_Parse from q_shared where needed."""
	return q_shared.COM_Parse(data, cursor)
