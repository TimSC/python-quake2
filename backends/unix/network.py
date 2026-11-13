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
 * Low level network code, based upon the BSD socket api.
 *
 * =======================================================================
"""
from __future__ import annotations

import os
import sys
import socket
import select
import struct
from errno import EWOULDBLOCK, ECONNREFUSED

from backends.unix import system
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cvar
from common import frame

"""
#include "../../common/header/common.h"

#include <unistd.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/param.h>
#include <sys/ioctl.h>
#include <sys/uio.h>
#include <errno.h>
#include <arpa/inet.h>
#include <net/if.h>
"""

# Q2PORT: a struct sockaddr_storage is a (family, address) tuple, the address
# in the form Python's socket module uses for that family: (host, port) for
# AF_INET, (host, port, flowinfo, scope_id) for AF_INET6, with the port in host
# byte order. A zeroed sockaddr_storage is (0, None). netadr_t.port stays in
# network byte order, as in the C.

net_local_adr = common_h.netadr_t() #netadr_t

LOOPBACK	= 0x7f000001
MAX_LOOPBACK	= 4
QUAKE2MCAST	= "ff12::666"

"""
typedef struct
{
	byte data[MAX_MSGLEN];
	int datalen;
} loopmsg_t;
"""
class loopback_t(object):

	def __init__(self):

		self.msgs = [] #loopmsg_t[MAX_LOOPBACK], Q2PORT: a queue of the messages' bytes
		self.get, self.send = 0, 0 #int

loopbacks = [loopback_t(), loopback_t()] #loopback_t[2]
ip_sockets = [None, None] #int [2], python socket objects, None for no socket
ip6_sockets = [None, None] #int [2]
ipx_sockets = [None, None] #int [2]
multicast_interface = None #char *

errno = 0 # Q2PORT: the errno of the last failed socket call, read by NET_ErrorString

#static int NET_Socket(char *net_interface, int port, netsrc_t type, int family);
#static const char *NET_ErrorString(void);

# Q2PORT: the <netinet/in.h> macros, on the 16 bytes of an in6_addr
def IN6_IS_ADDR_V4MAPPED(a: bytes)->bool:

	return a[:12] == b"\x00" * 10 + b"\xff\xff"

def IN6_IS_ADDR_LINKLOCAL(a: bytes)->bool:

	return a[0] == 0xfe and (a[1] & 0xc0) == 0x80

def IN6_IS_ADDR_MULTICAST(a: bytes)->bool:

	return a[0] == 0xff

def NetadrToSockadr(a): #netadr_t *, struct sockaddr_storage * (returns the sockaddr_storage)

	#struct sockaddr_in6 *s6;

	s = (0, None) # memset(s, 0, sizeof(*s));

	if a.type == common_h.netadrtype_t.NA_BROADCAST:

		# sin_family = AF_INET; sin_port = a->port; sin_addr.s_addr = INADDR_BROADCAST
		s = (socket.AF_INET, ("255.255.255.255", socket.ntohs(a.port)))

	elif a.type == common_h.netadrtype_t.NA_IP:

		# sin_family = AF_INET; sin_addr = *(int *)&a->ip; sin_port = a->port
		s = (socket.AF_INET, (socket.inet_ntoa(a.ip[:4]), socket.ntohs(a.port)))

	elif a.type == common_h.netadrtype_t.NA_MULTICAST6:

		try:
			sin6_addr = socket.inet_pton(socket.AF_INET6, QUAKE2MCAST)
		except OSError as e:
			clientserver.Com_Printf("NET_NetadrToSockadr: inet_pton: {}\n".format(e.strerror))
			return s

		# scope_id is important for
		# link-local destination.
		s = (socket.AF_INET6, (socket.inet_ntop(socket.AF_INET6, sin6_addr), socket.ntohs(a.port), 0, a.scope_id))

	elif a.type == common_h.netadrtype_t.NA_IP6:

		if IN6_IS_ADDR_V4MAPPED(a.ip):

			s = (socket.AF_INET, (socket.inet_ntoa(a.ip[12:16]), socket.ntohs(a.port)))

		else:

			# scope_id is important for
			# link-local destination.
			s = (socket.AF_INET6, (socket.inet_ntop(socket.AF_INET6, a.ip), socket.ntohs(a.port), 0, a.scope_id))

	# NA_LOOPBACK, NA_IPX, NA_BROADCAST_IPX: nothing

	return s

def SockadrToNetadr(s, a): #struct sockaddr_storage *, netadr_t *

	#struct sockaddr_in6 *s6;

	family, addr = s

	if family == socket.AF_INET:

		a.ip = socket.inet_aton(addr[0]) + a.ip[4:] # *(int *) &a->ip = *(int *)&sin_addr;
		a.port = socket.htons(addr[1])
		a.type = common_h.netadrtype_t.NA_IP

	elif family == socket.AF_INET6:

		# Q2PORT: Python gives a link-local host as "addr%interface"
		sin6_addr = socket.inet_pton(socket.AF_INET6, addr[0].split("%")[0])

		if IN6_IS_ADDR_V4MAPPED(sin6_addr):

			a.ip = sin6_addr[12:16] + a.ip[4:]
			a.port = socket.htons(addr[1])
			a.type = common_h.netadrtype_t.NA_IP

		else:

			a.ip = sin6_addr
			a.port = socket.htons(addr[1])
			a.type = common_h.netadrtype_t.NA_IP6
			a.scope_id = addr[3]

def NET_Init(): #void

	pass

def NET_CompareAdr(a, b): #netadr_t, netadr_t (returns qboolean)

	if a.type != b.type:

		return False

	if a.type == common_h.netadrtype_t.NA_LOOPBACK:

		return True

	if a.type == common_h.netadrtype_t.NA_IP:

		if (a.ip[0] == b.ip[0] and a.ip[1] == b.ip[1] and
			a.ip[2] == b.ip[2] and a.ip[3] == b.ip[3] and a.port == b.port):

			return True

	if a.type == common_h.netadrtype_t.NA_IP6:

		if a.ip[:16] == b.ip[:16] and a.port == b.port:

			return True

	return False

"""
 * Compares without the port
"""
def NET_CompareBaseAdr(a, b): #netadr_t, netadr_t (returns qboolean)

	if a.type != b.type:

		return False

	if a.type == common_h.netadrtype_t.NA_LOOPBACK:

		return True

	if a.type == common_h.netadrtype_t.NA_IP:

		if (a.ip[0] == b.ip[0] and a.ip[1] == b.ip[1] and
			a.ip[2] == b.ip[2] and a.ip[3] == b.ip[3]):

			return True

		return False

	if a.type == common_h.netadrtype_t.NA_IP6:

		if a.ip[:16] == b.ip[:16]:

			return True

		return False

	if a.type == common_h.netadrtype_t.NA_IPX:

		if a.ipx[:10] == b.ipx[:10]:

			return True

		return False

	return False

def NET_BaseAdrToString(a): #netadr_t (returns static char *)

	#static char s[64];
	#struct sockaddr_storage ss;
	#struct sockaddr_in6 *s6;

	if a.type in (common_h.netadrtype_t.NA_IP, common_h.netadrtype_t.NA_LOOPBACK):

		s = "{:d}.{:d}.{:d}.{:d}".format(a.ip[0], a.ip[1], a.ip[2], a.ip[3])

	elif a.type == common_h.netadrtype_t.NA_BROADCAST:

		s = "255.255.255.255"

	elif a.type in (common_h.netadrtype_t.NA_IP6, common_h.netadrtype_t.NA_MULTICAST6):

		# memset(&ss, 0, sizeof(ss));
		sin6_scope_id = 0

		if IN6_IS_ADDR_V4MAPPED(a.ip):

			ss = (socket.inet_ntoa(a.ip[12:16]), 0)

		else:

			sin6_scope_id = a.scope_id
			ss = (socket.inet_ntop(socket.AF_INET6, a.ip), 0, 0, sin6_scope_id)

		try:
			s = socket.getnameinfo(ss, socket.NI_NUMERICHOST)[0]
		except OSError:
			s = None

		if s is None:

			s = "<invalid>"

		else:

			if (a.type == common_h.netadrtype_t.NA_MULTICAST6 or
				(len(ss) == 4 and IN6_IS_ADDR_LINKLOCAL(a.ip))):

				# If the address is multicast (link) or a
				# link-local, need to carry the scope. The string
				# format of the IPv6 address is used by the
				# client to extablish the connect to the
				# server.
				tmp = "{}%{:d}".format(s, sin6_scope_id)
				s = tmp[:63]

	else:

		s = "invalid IP address family type"

	return s

def NET_AdrToString(a): #netadr_t (returns char *)

	#static char s[64];
	#const char *base;

	base = NET_BaseAdrToString(a)
	s = "[{}]:{:d}".format(base, socket.ntohs(a.port))

	return s[:63]

def NET_StringToSockaddr(s: str): #const char *, struct sockaddr_storage * (returns qboolean, the sockaddr_storage)

	#char copy[128];
	#char *addrs, *space;
	#char *ports = NULL;
	#int err;
	#struct addrinfo hints;
	#struct addrinfo *resultp;

	# hints.ai_socktype = SOCK_DGRAM; hints.ai_family = PF_UNSPEC;

	copy = s[:127] # Q_strlcpy(copy, s, sizeof(copy));
	addrs = copy
	space = 0
	ports = None

	if copy[:1] == "[":

		space = copy.find("]")

		if space == -1:

			clientserver.Com_Printf("NET_StringToSockaddr: invalid IPv6 address {}\n".format(s))
			return False, (0, None)

		addrs = copy[1:space] # *space++ = '\0';
		space += 1

	# Q2PORT: the C's loop puts a '\0' on every ':' after space, so the
	# address ends at the first one and the port starts after the last one
	rest = copy[space:]

	if ":" in rest:

		if space == 0:

			addrs = rest[:rest.find(":")]

		ports = rest[rest.rfind(":") + 1:]

	try:
		if addrs == "": # Q2PORT: Python takes "" as INADDR_ANY, C's getaddrinfo fails
			raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

		resultp = socket.getaddrinfo(addrs, ports, socket.AF_UNSPEC, socket.SOCK_DGRAM)

	except socket.gaierror as err:
		# Error
		clientserver.Com_Printf("NET_StringToSockaddr: string {}:\n{}\n".format(s, err.strerror))
		return False, (0, None)

	ai_family, _, _, _, ai_addr = resultp[0]

	if ai_family in (socket.AF_INET, socket.AF_INET6):

		# convert to ipv4/ipv6 addr
		sadr = (ai_family, ai_addr)

	else:

		clientserver.Com_Printf("NET_StringToSockaddr: string {}:\nprotocol family {:d} not supported\n".format(
			s, ai_family))
		return False, (0, None)

	return True, sadr

def NET_StringToAdr(s: str): #const char *, netadr_t * (returns netadr_t, or None for false)

	#struct sockaddr_storage sadr;

	a = common_h.netadr_t() # memset(a, 0, sizeof(*a));

	if s == "localhost":

		a.type = common_h.netadrtype_t.NA_LOOPBACK
		return a

	ok, sadr = NET_StringToSockaddr(s)
	if not ok:

		return None

	SockadrToNetadr(sadr, a)

	return a

def NET_IsLocalAddress(adr): #netadr_t (returns qboolean)

	return NET_CompareAdr(adr, net_local_adr)

def NET_GetLoopPacket(sock, net_from, net_message): #netsrc_t, netadr_t *, sizebuf_t * (returns qboolean, netadr_t)

	#int i;
	#loopback_t *loop;

	loop = loopbacks[sock.value]

	# Q2PORT: msgs is a queue that NET_SendLoopPacket keeps at MAX_LOOPBACK
	# messages, which is what the C's get/send ring indices do
	if len(loop.msgs) == 0:

		return False, net_from

	data = loop.msgs.pop(0)
	loop.get += 1

	net_message.data = bytearray(data) # memcpy(net_message->data, loop->msgs[i].data, loop->msgs[i].datalen);
	net_message.cursize = len(data)
	net_from = net_local_adr.copy() # *net_from = net_local_adr;
	return True, net_from

def NET_SendLoopPacket(sock, data: bytes, to): #netsrc_t, int, void *, netadr_t

	#int i;
	#loopback_t *loop;

	assert isinstance(data, bytes) or isinstance(data, bytearray)
	loop = loopbacks[sock.value ^ 1]

	if len(loop.msgs) >= MAX_LOOPBACK:

		loop.msgs.pop(0)

	loop.send += 1
	loop.msgs.append(data)

def NET_GetPacket(sock, net_from, net_message): #netsrc_t, netadr_t *, sizebuf_t * (returns qboolean, netadr_t)
	# net_message is filled in place like the C buffer; net_from is returned as a new
	# netadr_t because python code keeps references where C copies the struct

	#int ret;
	#struct sockaddr_storage from;
	#socklen_t fromlen;
	#int net_socket;
	#int protocol;
	#int err;

	global errno

	rx, net_from = NET_GetLoopPacket(sock, net_from, net_message)
	if rx:

		return True, net_from

	for protocol in range(3):

		if protocol == 0:

			net_socket = ip_sockets[sock.value]

		elif protocol == 1:

			net_socket = ip6_sockets[sock.value]

		else:

			net_socket = ipx_sockets[sock.value]

		if net_socket is None:

			continue

		#fromlen = sizeof(from);
		try:
			data, from_adr = net_socket.recvfrom(net_message.maxsize)
			ret = len(data)
		except OSError as e:
			errno = e.errno
			ret = -1

		if ret == -1:

			err = errno

			if err == EWOULDBLOCK or err == ECONNREFUSED:

				continue

			# Q2PORT: the C converts the address before the error check; there is
			# no address on a Python error, so this prints the last one
			clientserver.Com_Printf("{}: {} from {}\n".format(NET_ErrorString(),
					"NET_GetPacket", NET_AdrToString(net_from)))
			continue

		net_from = common_h.netadr_t()
		SockadrToNetadr((net_socket.family, from_adr), net_from)

		if ret == net_message.maxsize:

			clientserver.Com_Printf("Oversize packet from {}\n".format(NET_AdrToString(net_from)))
			continue

		net_message.data = bytearray(data)
		net_message.cursize = ret
		return True, net_from

	return False, net_from

def NET_SendPacket(sock, data, to): #netsrc_t, int, void *, netadr_t

	#int ret;
	#struct sockaddr_storage addr;
	#int net_socket;
	#int addr_size = sizeof(struct sockaddr_in);

	global errno

	if to.type == common_h.netadrtype_t.NA_LOOPBACK:

		NET_SendLoopPacket(sock, data, to)
		return

	elif to.type in (common_h.netadrtype_t.NA_BROADCAST, common_h.netadrtype_t.NA_IP):

		net_socket = ip_sockets[sock.value]

		if net_socket is None:

			return

	elif to.type in (common_h.netadrtype_t.NA_IP6, common_h.netadrtype_t.NA_MULTICAST6):

		net_socket = ip6_sockets[sock.value]
		#addr_size = sizeof(struct sockaddr_in6);

		if net_socket is None:

			return

	elif to.type in (common_h.netadrtype_t.NA_IPX, common_h.netadrtype_t.NA_BROADCAST_IPX):

		net_socket = ipx_sockets[sock.value]

		if net_socket is None:

			return

	else:

		clientserver.Com_Error(shared.ERR_FATAL, "{}: bad address type".format("NET_SendPacket"))
		return

	addr = NetadrToSockadr(to)

	# Re-check the address family. If to.type is NA_IP6 but
	# contains an IPv4 mapped address, NetadrToSockadr will
	# return an AF_INET struct.  If so, switch back to AF_INET
	# socket.
	if to.type == common_h.netadrtype_t.NA_IP6 and addr[0] == socket.AF_INET:

		net_socket = ip_sockets[sock.value]
		#addr_size = sizeof(struct sockaddr_in);

		if net_socket is None:

			return

	if addr[0] == socket.AF_INET6:

		s6 = addr[1]

		# If multicast socket, must specify scope.
		# So multicast_interface must be specified
		if IN6_IS_ADDR_MULTICAST(socket.inet_pton(socket.AF_INET6, s6[0].split("%")[0])):

			#struct addrinfo hints;
			#struct addrinfo *res;
			#char tmp[128];

			if multicast_interface is not None:

				#int error;
				#char mcast_addr[128], mcast_port[10];

				# Do a getnameinfo/getaddrinfo cycle
				# to calculate the scope_id of the
				# multicast address. getaddrinfo is
				# passed a multicast address of the
				# form ff0x::xxx%multicast_interface
				try:
					tmp = socket.getnameinfo(s6, socket.NI_NUMERICHOST)[0]
				except OSError as error:
					clientserver.Com_Printf("NET_SendPacket: getnameinfo: {}\n".format(error.strerror))
					return

				mcast_addr = "{}%{}".format(tmp, multicast_interface)
				mcast_port = "{:d}".format(s6[1])
				# hints.ai_family = AF_INET6; hints.ai_socktype = SOCK_DGRAM; hints.ai_flags = AI_NUMERICHOST;

				try:
					res = socket.getaddrinfo(mcast_addr, mcast_port, socket.AF_INET6,
						socket.SOCK_DGRAM, 0, socket.AI_NUMERICHOST)
				except socket.gaierror as error:
					clientserver.Com_Printf("NET_SendPacket: getaddrinfo: {}\n".format(error.strerror))
					return

				# sockaddr_in6 should now have a valid scope_id.
				addr = (socket.AF_INET6, res[0][4])

			else:

				clientserver.Com_Printf("NET_SendPacket: IPv6 multicast destination but +set multicast not specified: {}\n".format(
						s6[0]))
				return

	try:
		ret = net_socket.sendto(data, addr[1])
	except OSError as e:
		errno = e.errno
		ret = -1

	if ret == -1:

		clientserver.Com_Printf("{} ERROR: {} to {}\n".format(NET_ErrorString(),
				"NET_SendPacket", NET_AdrToString(to)))

def NET_OpenIP(): #void

	#cvar_t *port, *ip;

	port = cvar.Cvar_Get("port", "{}".format(common_h.PORT_SERVER), shared.CVAR_NOSET)
	ip = cvar.Cvar_Get("ip", "localhost", shared.CVAR_NOSET)

	if ip6_sockets[common_h.netsrc_t.NS_SERVER.value] is None:

		ip6_sockets[common_h.netsrc_t.NS_SERVER.value] = NET_Socket(ip.string, int(port.value),
				common_h.netsrc_t.NS_SERVER, socket.AF_INET6)

	if ip6_sockets[common_h.netsrc_t.NS_CLIENT.value] is None:

		ip6_sockets[common_h.netsrc_t.NS_CLIENT.value] = NET_Socket(ip.string, common_h.PORT_ANY,
				common_h.netsrc_t.NS_CLIENT, socket.AF_INET6)

	if ip_sockets[common_h.netsrc_t.NS_SERVER.value] is None:

		ip_sockets[common_h.netsrc_t.NS_SERVER.value] = NET_Socket(ip.string, int(port.value),
				common_h.netsrc_t.NS_SERVER, socket.AF_INET)

	if ip_sockets[common_h.netsrc_t.NS_CLIENT.value] is None:

		ip_sockets[common_h.netsrc_t.NS_CLIENT.value] = NET_Socket(ip.string, common_h.PORT_ANY,
				common_h.netsrc_t.NS_CLIENT, socket.AF_INET)

"""
 * A single player game will only use the loopback code
"""
def NET_Config(multiplayer: bool): #qboolean

	if not multiplayer:

		#int i;

		# shut down any existing sockets
		for i in range(2):

			if ip_sockets[i] is not None:

				ip_sockets[i].close()
				ip_sockets[i] = None

			if ip6_sockets[i] is not None:

				ip6_sockets[i].close()
				ip6_sockets[i] = None

			if ipx_sockets[i] is not None:

				ipx_sockets[i].close()
				ipx_sockets[i] = None

	else:

		# open sockets
		NET_OpenIP()

# ===================================================================

def NET_Socket(net_interface: str, port: int, type_, family: int): #char *, int, netsrc_t, int (returns int, a python socket object or None for 0)

	global errno, multicast_interface

	#char Buf[BUFSIZ], *Host, *Service;
	#int newsocket = -1;
	#int Error = 0;
	#struct sockaddr_storage ss;
	#struct addrinfo hints, *res, *ai;
	#qboolean _true = true;
	#int i = 1;

	#struct ipv6_mreq mreq;
	#cvar_t *mcast;

	# hints.ai_family = family; hints.ai_socktype = SOCK_DGRAM;
	# hints.ai_protocol = IPPROTO_UDP; hints.ai_flags = AI_PASSIVE;

	if (not net_interface or
		shared_c.Q_stricmp(net_interface, "localhost") == 0):

		Host = "::" if family == socket.AF_INET6 else "0.0.0.0"

	else:

		Host = net_interface

	if port == common_h.PORT_ANY:

		Service = None

	else:

		Buf = "{:5d}".format(port)
		Service = Buf

	try:
		res = socket.getaddrinfo(Host, Service, family, socket.SOCK_DGRAM,
			socket.IPPROTO_UDP, socket.AI_PASSIVE)
	except socket.gaierror as Error:
		clientserver.Com_Printf("{} ERROR: getaddrinfo:{}\n".format(
				"NET_Socket", Error.strerror))
		return None

	newsocket = None
	ss = None

	for ai in res:

		ai_family, ai_socktype, ai_protocol, _, ai_addr = ai

		try:
			newsocket = socket.socket(ai_family, ai_socktype, ai_protocol)
		except OSError as e:
			clientserver.Com_Printf("{}: socket: {}\n".format("NET_Socket", e.strerror))
			continue

		# make it non-blocking
		try:
			newsocket.setblocking(False) # ioctl(newsocket, FIONBIO, (char *)&_true)
		except OSError as e:
			clientserver.Com_Printf("{}: ioctl FIONBIO: {}\n".format("NET_Socket", e.strerror))
			newsocket.close()
			continue

		if family == socket.AF_INET:

			# make it broadcast capable
			try:
				newsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			except OSError as e:
				errno = e.errno
				clientserver.Com_Printf("{} ERROR: setsockopt SO_BROADCAST:{}\n".format(
						"NET_Socket", NET_ErrorString()))
				newsocket.close()
				return None

		# make it reusable
		try:
			newsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		except OSError as e:
			errno = e.errno
			clientserver.Com_Printf("{} ERROR: setsockopt SO_REUSEADDR:{}\n".format(
					"NET_Socket", NET_ErrorString()))
			newsocket.close()
			return None

		try:
			newsocket.bind(ai_addr)
		except OSError as e:
			clientserver.Com_Printf("{}: bind: {}\n".format("NET_Socket", e.strerror))
			newsocket.close()
		else:
			ss = (ai_family, ai_addr) # memcpy(&ss, ai->ai_addr, ai->ai_addrlen);
			break

	if ss is None: # ai == NULL

		# socket should be already closed
		return None

	if ss[0] == socket.AF_INET:

		pass

	elif ss[0] == socket.AF_INET6:

		# Multicast outgoing interface is specified for
		# client and server (+set multicast <ifname>)
		mcast = cvar.Cvar_Get("multicast", "NULL", shared.CVAR_NOSET)
		multicast_interface = mcast.string if mcast.string != "NULL" else None

		if multicast_interface is not None:

			# multicast_interface is a global variable.
			# Also used in NET_SendPacket()
			try:
				ipv6mr_interface = socket.if_nametoindex(multicast_interface)
			except OSError:
				ipv6mr_interface = 0

			if ipv6mr_interface == 0:

				clientserver.Com_Printf("{}: invalid interface: {}\n".format(
						"NET_Socket", multicast_interface))

			try:
				newsocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF,
					ipv6mr_interface)
			except OSError as e:
				clientserver.Com_Printf("{}: IPV6_MULTICAST_IF: {}\n".format(
						"NET_Socket", e.strerror))

			# Join multicast group ONLY if server
			if type_ == common_h.netsrc_t.NS_SERVER:

				ipv6mr_multiaddr = bytes(16)
				try:
					ipv6mr_multiaddr = socket.inet_pton(socket.AF_INET6, QUAKE2MCAST)
				except OSError as e:
					clientserver.Com_Printf("{}: inet_pton: {}\n".format(
							"NET_Socket", e.strerror))

				mreq = ipv6mr_multiaddr + struct.pack("=I", ipv6mr_interface) # struct ipv6_mreq

				try:
					newsocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
				except OSError as e:
					clientserver.Com_Printf("{}: IPV6_JOIN_GROUP: {}\n".format(
							"NET_Socket", e.strerror))

	return newsocket

def NET_Shutdown(): #void

	NET_Config(False) # close sockets

def NET_ErrorString()->str: #void (returns static const char *)

	#int code;

	code = errno
	return os.strerror(code)

"""
 * sleeps msec or until net socket is ready
"""
def NET_Sleep(msec: int): #int

	#struct timeval timeout;
	#fd_set fdset;
	#extern cvar_t *dedicated;
	#extern qboolean stdin_active;

	if ((ip_sockets[common_h.netsrc_t.NS_SERVER.value] is None and
		 ip6_sockets[common_h.netsrc_t.NS_SERVER.value] is None) or
		(frame.dedicated is not None and not frame.dedicated.value)):

		return # we're not a server, just run full speed

	fdset = [] # FD_ZERO(&fdset);

	if system.stdin_active:

		fdset.append(sys.stdin) # stdin is processed too

	# Q2PORT: the C's FD_SET of a missing (0) socket is stdin again
	if ip_sockets[common_h.netsrc_t.NS_SERVER.value] is not None:

		fdset.append(ip_sockets[common_h.netsrc_t.NS_SERVER.value]) # IPv4 network socket

	if ip6_sockets[common_h.netsrc_t.NS_SERVER.value] is not None:

		fdset.append(ip6_sockets[common_h.netsrc_t.NS_SERVER.value]) # IPv6 network socket

	timeout = msec / 1000.0 # timeout.tv_sec = msec / 1000; timeout.tv_usec = (msec % 1000) * 1000;
	select.select(fdset, [], [], timeout)
