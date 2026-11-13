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
from backends.unix import network, system
from common.header import common as common_h
from common.header import shared
from common import net_channel
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
	network.NET_SendPacket (net_socket, send, adr)


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
Netchan_Setup ... Netchan_Process

The channel itself is common/net_channel.py's NetChannel; these add the
sending, the clock and the showpackets / showdrop output.
==============
"""
def Netchan_Setup (sock: common_h.netsrc_t, chan: net_channel.NetChannel, adr: common_h.netadr_t, qport: int)->None:

	chan.setup(sock, adr, qport, frame.curtime)

def Netchan_CanReliable (chan: net_channel.NetChannel)->bool:

	return chan.can_reliable()

def Netchan_NeedReliable (chan: net_channel.NetChannel)->bool:

	return chan.need_reliable()

def Netchan_Transmit (chan: net_channel.NetChannel, data: bytes | bytearray)->None:

	assert isinstance(data, bytes) or isinstance(data, bytearray)

	packet = chan.build_packet(data, frame.curtime, int(qport.value))

	if packet is None:

		clientserver.Com_Printf ("{}:Outgoing message overflow\n".format(
			network.NET_AdrToString (chan.remote_address)))
		return

	if packet.dumped_unreliable:
		clientserver.Com_Printf ("Netchan_Transmit: dumped unreliable\n")

	network.NET_SendPacket (chan.sock, packet.data, chan.remote_address)

	if showpackets.value != 0:

		if packet.reliable:
			clientserver.Com_Printf ("send {:4d} : s={:d} reliable={:d} ack={:d} rack={:d}\n".format(
				len(packet.data), chan.outgoing_sequence - 1, chan.reliable_sequence,
				chan.incoming_sequence, chan.incoming_reliable_sequence))
		else:
			clientserver.Com_Printf ("send {:4d} : s={:d} ack={:d} rack={:d}\n".format(
				len(packet.data), chan.outgoing_sequence - 1,
				chan.incoming_sequence, chan.incoming_reliable_sequence))

def Netchan_Process (chan: net_channel.NetChannel, msg: common_h.sizebuf_t)->bool:

	# the reliable bit shown is the one this packet will set, as in the C
	reliable_shown = chan.incoming_reliable_sequence ^ 1
	header = chan.accept(msg, frame.curtime)

	if showpackets.value:

		if header.reliable_message:
			clientserver.Com_Printf ("recv {:4d} : s={:d} reliable={:d} ack={:d} rack={:d}\n".format(
				header.size, header.sequence, reliable_shown, header.sequence_ack, header.reliable_ack))
		else:
			clientserver.Com_Printf ("recv {:4d} : s={:d} ack={:d} rack={:d}\n".format(
				header.size, header.sequence, header.sequence_ack, header.reliable_ack))

	if not header.accepted:

		if showdrop.value:
			clientserver.Com_Printf ("{}:Out of order packet {:d} at {:d}\n".format(
				network.NET_AdrToString (chan.remote_address), header.sequence, chan.incoming_sequence))
		return False

	if header.dropped > 0 and showdrop.value:
		clientserver.Com_Printf ("{}:Dropped {:d} packets at {:d}\n".format(
			network.NET_AdrToString (chan.remote_address), header.dropped, header.sequence))

	return True
