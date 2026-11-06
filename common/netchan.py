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

The low level, platform independant network code

=======================================================================
"""
from __future__ import annotations

import struct
import time
from linux import net_udp, q_shlinux
from common.header import common as common_h
from common.header import shared
from common import clientserver
from common import frame
from common import cvar
from common import movemsg
from common import szone

"""
#include <time.h>
#include "header/common.h"
"""

showpackets = None #cvar_t		*
showdrop = None #cvar_t		*
qport = None #cvar_t		*

net_from = common_h.netadr_t() #netadr_t
net_message = common_h.sizebuf_t()
net_message.maxsize = common_h.MAX_MSGLEN
"""
byte		net_message_buffer[qcommon.MAX_MSGLEN];

/*
===============
Netchan_Init

===============
"""
def Netchan_Init ()->None:

	global showpackets, showdrop, qport

	#int		port;

	# pick a port value that should be nice and random
	port = int(time.time()) & 0xffff

	showpackets = cvar.Cvar_Get ("showpackets", "0", 0)
	showdrop = cvar.Cvar_Get ("showdrop", "0", 0)
	qport = cvar.Cvar_Get ("qport", str(port), shared.CVAR_NOSET)


"""
===============
Netchan_OutOfBand

Sends an out-of-band datagram
================
"""
def Netchan_OutOfBand (net_socket: int, adr: common_h.netadr_t, data: bytes)->None: #int, netadr_t, byte *

	assert isinstance(data, bytes)

	#sizebuf_t	send;
	#byte		send_buf[qcommon.MAX_MSGLEN];

	# write the packet header
	send = struct.pack("<l", -1)	# MSG_WriteLong (&send, -1), -1 sequence means out of band
	send += data

	# send the datagram
	net_udp.NET_SendPacket (net_socket, send, adr)


"""
===============
Netchan_OutOfBandPrint

Sends a text message in an out-of-band datagram
================
"""
def Netchan_OutOfBandPrint (net_socket: int, adr: common_h.netadr_t, format: str | bytes, *args)->None: #int, netadr_t, const char *, ...

	#va_list argptr;
	#static char string[MAX_MSGLEN - 4];

	#va_start(argptr, format);
	#vsnprintf(string, MAX_MSGLEN - 4, format, argptr);
	#va_end(argptr);
	# Q2PORT: the format may be str or bytes; the string goes out as latin-1 bytes
	if isinstance(format, (bytes, bytearray)):
		format = format.decode("latin-1")
	string = (format % args) if args else format
	string = string.encode("latin-1")[:common_h.MAX_MSGLEN - 4 - 1]

	Netchan_OutOfBand (net_socket, adr, string)

"""
==============
Netchan_Setup

called to open a channel to a remote system
==============
"""
def Netchan_Setup (sock: common_h.netsrc_t, chan: common_h.netchan_t, adr: common_h.netadr_t, qport: int)->None: #netsrc_t, netchan_t *, netadr_t, int
	
	chan.clear()
	
	chan.sock = sock
	chan.remote_address = adr
	chan.qport = qport
	chan.last_received = frame.curtime
	chan.incoming_sequence = 0
	chan.outgoing_sequence = 1

	szone.SZ_Init (chan.message, common_h.MAX_MSGLEN)
	chan.message.allowoverflow = True


"""
===============
Netchan_CanReliable

Returns true if the last reliable message has acked
================
"""
def Netchan_CanReliable (chan: common_h.netchan_t)->bool: #netchan_t * (returns qboolean)

	if chan.reliable_length:
		return False			# waiting for ack
	return True

def Netchan_NeedReliable (chan: common_h.netchan_t)->bool: #netchan_t *

	# qboolean	send_reliable;

	# if the remote side dropped the last reliable message, resend it
	send_reliable = False

	if chan.incoming_acknowledged > chan.last_reliable_sequence \
		and chan.incoming_reliable_acknowledged != chan.reliable_sequence:

		send_reliable = True

	# if the reliable transmit buffer is empty, copy the current message out
	if not chan.reliable_length and chan.message.cursize:
	
		send_reliable = True
	
	return send_reliable


"""
===============
Netchan_Transmit

tries to send an unreliable message to a connection, and handles the
transmition / retransmition of the reliable messages.

A 0 length will still generate a packet and deal with the reliable messages.
================
"""
def Netchan_Transmit (chan: common_h.netchan_t, data: bytes | bytearray)->None: #netchan_t *

	assert isinstance(data, bytes) or isinstance(data, bytearray)

	send = common_h.sizebuf_t()
	#byte		send_buf[qcommon.MAX_MSGLEN];
	#qboolean	send_reliable;
	#unsigned	w1, w2;


	# check for message overflow
	if chan.message.overflowed:
	
		chan.fatal_error = True
		clientserver.Com_Printf ("{}:Outgoing message overflow\n".format(
			net_udp.NET_AdrToString (chan.remote_address)))
		return
	
	send_reliable = Netchan_NeedReliable (chan)

	if not chan.reliable_length and chan.message.cursize:
		chan.reliable_buf = chan.message.data
		chan.reliable_length = len(chan.message.data)
		chan.message.data = bytearray()
		chan.message.cursize = 0
		chan.reliable_sequence ^= 1
	
	# write the packet header
	szone.SZ_Init (send, common_h.MAX_MSGLEN)

	w1 = ( chan.outgoing_sequence & ~(1<<31) ) | (send_reliable<<31)
	w2 = ( chan.incoming_sequence & ~(1<<31) ) | (chan.incoming_reliable_sequence<<31)

	chan.outgoing_sequence+=1
	chan.last_sent = frame.curtime


	movemsg.MSG_WriteLong(send, w1)
	movemsg.MSG_WriteLong(send, w2)

	# send the qport if we are a client
	if chan.sock == common_h.netsrc_t.NS_CLIENT:
		movemsg.MSG_WriteShort(send, int(qport.value))

	# copy the reliable message to the packet first
	if send_reliable:
	
		szone.SZ_Write(send, chan.reliable_buf)
		chan.last_reliable_sequence = chan.outgoing_sequence
	
	# add the unreliable part if space is available
	if send.maxsize - send.cursize >= len(data):
		szone.SZ_Write(send, data)
	else:
		clientserver.Com_Printf ("Netchan_Transmit: dumped unreliable\n")

	# send the datagram
	net_udp.NET_SendPacket (chan.sock, send.data, chan.remote_address)

	if showpackets.value != 0:
	
		if send_reliable:
			clientserver.Com_Printf ("send {:4d} : s={:d} reliable={:d} ack={:d} rack={:d}\n".format(
				send.cursize
				, chan.outgoing_sequence - 1
				, chan.reliable_sequence
				, chan.incoming_sequence
				, chan.incoming_reliable_sequence))
		else:
			clientserver.Com_Printf ("send {:4d} : s={:d} ack={:d} rack={:d}\n".format(
				send.cursize
				, chan.outgoing_sequence - 1
				, chan.incoming_sequence
				, chan.incoming_reliable_sequence))
	


"""
=================
Netchan_Process

called when the current net_message is from remote_address
modifies net_message so that it points to the packet payload
=================
"""
def Netchan_Process (chan: common_h.netchan_t, msg: common_h.sizebuf_t)->bool: #netchan_t *, sizebuf_t * (returns qboolean)

	#unsigned	sequence, sequence_ack;
	#unsigned	reliable_ack, reliable_message;
	#int			qport;

	# get sequence numbers
	movemsg.MSG_BeginReading (msg)
	sequence = movemsg.MSG_ReadLong (msg)
	sequence_ack = movemsg.MSG_ReadLong (msg)
	
	# read the qport if we are a server
	if chan.sock == common_h.netsrc_t.NS_SERVER:
		qport = movemsg.MSG_ReadShort(msg)

	reliable_message = sequence >> 31
	reliable_ack = sequence_ack >> 31

	sequence &= ~(1<<31)
	sequence_ack &= ~(1<<31)

	if showpackets.value:
	
		if reliable_message:
			clientserver.Com_Printf ("recv {:4d} : s={:d} reliable={:d} ack={:d} rack={:d}\n".format(
				msg.cursize
				, sequence
				, chan.incoming_reliable_sequence ^ 1
				, sequence_ack
				, reliable_ack))
		else:
			clientserver.Com_Printf ("recv {:4d} : s={:d} ack={:d} rack={:d}\n".format(
				msg.cursize
				, sequence
				, sequence_ack
				, reliable_ack))
	

	#
	# discard stale or duplicated packets
	#
	if sequence <= chan.incoming_sequence:
	
		if showdrop.value:
			clientserver.Com_Printf ("{}:Out of order packet {:d} at {:d}\n".format(
				net_udp.NET_AdrToString (chan.remote_address)
				,  sequence
				, chan.incoming_sequence))
		return False
	

	#
	# dropped packets don't keep the message from being used
	#
	chan.dropped = sequence - (chan.incoming_sequence+1)
	if chan.dropped > 0:
	
		if showdrop.value:
			clientserver.Com_Printf ("{}:Dropped {:d} packets at {:d}\n".format(
			net_udp.NET_AdrToString (chan.remote_address)
			, chan.dropped
			, sequence))
	

	#
	# if the current outgoing reliable message has been acknowledged
	# clear the buffer to make way for the next
	#
	if reliable_ack == chan.reliable_sequence:
		chan.reliable_length = 0	# it has been received
	
	#
	# if this message contains a reliable message, bump incoming_reliable_sequence 
	#
	chan.incoming_sequence = sequence
	chan.incoming_acknowledged = sequence_ack
	chan.incoming_reliable_acknowledged = reliable_ack
	if reliable_message:
	
		chan.incoming_reliable_sequence ^= 1
	

	#
	# the message can now be read from the current message pointer
	#
	chan.last_received = frame.curtime

	return True
