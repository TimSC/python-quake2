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
import os
import sys
import socket
import select
from errno import EWOULDBLOCK, ECONNREFUSED
from qcommon import qcommon, common, cvar
from game import q_shared
from linux import sys_linux
"""
// net_wins.c

#include "../qcommon/qcommon.h"

#include <unistd.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/param.h>
#include <sys/ioctl.h>
#include <sys/uio.h>
#include <errno.h>

#ifdef NeXT
#include <libc.h>
#endif
"""
net_local_adr = qcommon.netadr_t()
"""
#define	LOOPBACK	0x7f000001
"""
MAX_LOOPBACK	= 4
"""
typedef struct
{
	byte	data[MAX_MSGLEN];
	int		datalen;
} loopmsg_t;
"""
class loopback_t(object):

	def __init__(self):

		self.msgs = [] # loopmsg_t[MAX_LOOPBACK];
		self.get, self.send = 0, 0 #int

loopbacks = [loopback_t(), loopback_t()]
ip_sockets = [None, None] #int [2], python socket objects, None for no socket
ipx_sockets = [None, None] #int [2]

errno = 0 # the errno of the last failed socket call, read by NET_ErrorString

"""
int NET_Socket (char *net_interface, int port);
char *NET_ErrorString (void);

//=============================================================================
"""
def NetadrToSockadr (a): #netadr_t * (returns struct sockaddr_in, as a (host, sin_port) tuple, sin_port in network byte order)

	s = None # memset (s, 0, sizeof(*s));

	if a.type == qcommon.netadrtype_t.NA_BROADCAST:
	
		# s->sin_family = AF_INET;

		s = ("<broadcast>", a.port) # s->sin_port = a->port; *(int *)&s->sin_addr = -1;
	
	elif a.type == qcommon.netadrtype_t.NA_IP:
	
		# s->sin_family = AF_INET;

		s = (socket.inet_ntoa(a.ip), a.port) # *(int *)&s->sin_addr = *(int *)&a->ip; s->sin_port = a->port;
	
	return s


def SockadrToNetadr (s, a): #struct sockaddr_in * ((host, sin_port) tuple, sin_port in network byte order), netadr_t *

	a.ip = socket.inet_aton(s[0]) # *(int *)&a->ip = *(int *)&s->sin_addr;
	a.port = s[1]
	a.type = qcommon.netadrtype_t.NA_IP

def NET_CompareAdr (a, b): #netadr_t, netadr_t (returns qboolean)

	if a.ip == b.ip and a.port == b.port:
		return True
	return False

"""
===================
NET_CompareBaseAdr

Compares without the port
===================
"""
def NET_CompareBaseAdr (a, b): # netadr_t, netadr_t (returns qboolean)

	if a.type != b.type:
		return False

	if a.type == qcommon.netadrtype_t.NA_LOOPBACK:
		return True

	if a.type == qcommon.netadrtype_t.NA_IP:
	
		if a.ip[0] == b.ip[0] and a.ip[1] == b.ip[1] and a.ip[2] == b.ip[2] and a.ip[3] == b.ip[3]:
			return True
		return False
	
	if a.type == qcommon.netadrtype_t.NA_IPX:
	
		if a.ipx == b.ipx:
			return True
		return False
	

def NET_AdrToString (a): #netadr_t (returns char	*)

	#static	char	s[64];
	
	s = "{:d}.{:d}.{:d}.{:d}:{:d}".format(a.ip[0], a.ip[1], a.ip[2], a.ip[3], socket.ntohs(a.port))

	return s


def NET_BaseAdrToString (a): #netadr_t (returns char	*)

	#static	char	s[64];
	
	s = "{:d}.{:d}.{:d}.{:d}".format(a.ip[0], a.ip[1], a.ip[2], a.ip[3])

	return s

"""

/*
=============
NET_StringToAdr

localhost
idnewt
idnewt:28000
192.246.40.70
192.246.40.70:28000
=============
*/
"""
def NET_StringToSockaddr (s): #char * (returns struct sockaddr, as a (host, sin_port) tuple with sin_port in network byte order, or None)

	#struct hostent	*h;
	#char	*colon;
	#char	copy[128];
	
	# memset (sadr, 0, sizeof(*sadr));
	# ((struct sockaddr_in *)sadr)->sin_family = AF_INET;
	
	sin_port = 0

	copy = s
	# strip off a trailing :port if present
	colon = copy.find(':')
	if colon != -1:
	
		sin_port = socket.htons(q_shared.atoi(copy[colon+1:]) & 0xffff) # htons((short)atoi(colon+1))
		copy = copy[:colon]
	
	if copy and copy[0] >= '0' and copy[0] <= '9':
	
		try:
			sin_addr = socket.inet_ntoa(socket.inet_aton(copy)) # inet_addr(copy);
		except OSError:
			sin_addr = "255.255.255.255" # inet_addr returns INADDR_NONE
	
	else:
	
		try:
			h = socket.gethostbyname(copy)
		except OSError:
			return None
		sin_addr = h # *(int *)h->h_addr_list[0];
	
	return (sin_addr, sin_port)

"""
=============
NET_StringToAdr

localhost
idnewt
idnewt:28000
192.246.40.70
192.246.40.70:28000
=============
"""
def NET_StringToAdr (s): #char * (returns netadr_t *, or None for false)

	#struct sockaddr_in sadr;
	
	a = qcommon.netadr_t()

	if s == "localhost":
	
		# memset (a, 0, sizeof(*a));
		a.type = qcommon.netadrtype_t.NA_LOOPBACK
		return a
	
	sadr = NET_StringToSockaddr (s)
	if sadr is None:
		return None
	
	SockadrToNetadr (sadr, a)

	return a



def NET_IsLocalAddress (adr): #netadr_t (returns qboolean)

	return NET_CompareAdr (adr, net_local_adr)

"""
/*
=============================================================================

LOOPBACK BUFFERS FOR LOCAL PLAYER

=============================================================================
"""

def NET_GetLoopPacket (sock): #netsrc_t (returns qboolean, netadr_t *, sizebuf_t *)

	loop = loopbacks[sock.value]

	if len(loop.msgs) == 0:
		return False, None, None

	net_message = qcommon.sizebuf_t()
	common.SZ_Init (net_message, qcommon.MAX_MSGLEN)
	net_message.data = loop.msgs.pop(0)
	net_message.cursize = len(net_message.data)

	return True, net_local_adr, net_message


def NET_SendLoopPacket (sock, data: bytes, to): #netsrc_t, void *, netadr_t

	assert isinstance(data, bytes) or isinstance(data, bytearray)
	loop = loopbacks[sock.value^1]

	if len(loop.msgs) >= MAX_LOOPBACK:
		loop.msgs.pop(0)

	loop.msgs.append(data)

"""
//=============================================================================
"""
def NET_GetPacket (sock): #netsrc_t (returns qboolean, netadr_t *, sizebuf_t *)

	#int 	ret;
	#struct sockaddr_in	from;
	#int		fromlen;
	#int		net_socket;
	#int		protocol;
	#int		err;

	global errno

	rx, net_from, net_message = NET_GetLoopPacket (sock)
	assert net_message is None or isinstance(net_message, qcommon.sizebuf_t)
	if rx:
		return True, net_from, net_message
	
	for protocol in range(2):
	
		if protocol == 0:
			net_socket = ip_sockets[sock.value]
		else:
			net_socket = ipx_sockets[sock.value]

		if net_socket is None:
			continue

		net_from = qcommon.netadr_t()
		net_message = qcommon.sizebuf_t()
		common.SZ_Init (net_message, qcommon.MAX_MSGLEN)

		#fromlen = sizeof(from);
		try:
			data, from_adr = net_socket.recvfrom (net_message.maxsize)
			from_adr = (from_adr[0], socket.htons(from_adr[1])) # python returns the port in host byte order, sockaddr_in holds it in network order
			ret = len(data)
		except OSError as e:
			errno = e.errno
			ret = -1

		if ret == -1:
		
			err = errno

			if err == EWOULDBLOCK or err == ECONNREFUSED:
				continue
			common.Com_Printf ("NET_GetPacket: {} from {}\n".format(NET_ErrorString(),
						NET_AdrToString(net_from)))
			continue
		
		SockadrToNetadr (from_adr, net_from) # C converts before the error check, python has no address on error

		if ret == net_message.maxsize:
		
			common.Com_Printf ("Oversize packet from {}\n".format(NET_AdrToString (net_from)))
			continue
		
		net_message.data = data
		net_message.cursize = ret
		return True, net_from, net_message
	
	return False, None, None

"""
//=============================================================================
"""
def NET_SendPacket (sock, data, to): #netsrc_t, void *, netadr_t

	#int		ret;
	#struct sockaddr_in	addr;
	#int		net_socket;

	global errno

	if to.type == qcommon.netadrtype_t.NA_LOOPBACK:
	
		NET_SendLoopPacket (sock, data, to)
		return
	
	if to.type == qcommon.netadrtype_t.NA_BROADCAST:
	
		net_socket = ip_sockets[sock.value]
		if net_socket is None:
			return
	
	elif to.type == qcommon.netadrtype_t.NA_IP:
	
		net_socket = ip_sockets[sock.value]
		if net_socket is None:
			return
	
	elif to.type == qcommon.netadrtype_t.NA_IPX:
	
		net_socket = ipx_sockets[sock.value]
		if net_socket is None:
			return
	
	elif to.type == qcommon.netadrtype_t.NA_BROADCAST_IPX:
	
		net_socket = ipx_sockets[sock.value]
		if net_socket is None:
			return
	
	else:
		common.Com_Error (q_shared.ERR_FATAL, "NET_SendPacket: bad address type")

	addr = NetadrToSockadr (to)

	try:
		ret = net_socket.sendto (data, (addr[0], socket.ntohs(addr[1]))) # python takes the port in host byte order
	except OSError as e:
		errno = e.errno
		ret = -1
	if ret == -1:
	
		common.Com_Printf ("NET_SendPacket ERROR: {} to {}\n".format(NET_ErrorString(),
				NET_AdrToString (to)))
	

"""
//=============================================================================
"""



"""
====================
NET_OpenIP
====================
"""
def NET_OpenIP ():

	#cvar_t	*port, *ip;

	port = cvar.Cvar_Get ("port", "{}".format(qcommon.PORT_SERVER), q_shared.CVAR_NOSET)
	ip = cvar.Cvar_Get ("ip", "localhost", q_shared.CVAR_NOSET)

	if ip_sockets[qcommon.netsrc_t.NS_SERVER.value] is None:
		ip_sockets[qcommon.netsrc_t.NS_SERVER.value] = NET_Socket (ip.string, int(port.value))
	if ip_sockets[qcommon.netsrc_t.NS_CLIENT.value] is None:
		ip_sockets[qcommon.netsrc_t.NS_CLIENT.value] = NET_Socket (ip.string, qcommon.PORT_ANY)


"""
====================
NET_OpenIPX
====================
"""
def NET_OpenIPX ():

	pass


"""
====================
NET_Config

A single player game will only use the loopback code
====================
"""
def NET_Config (multiplayer): #qboolean

	#int		i;

	if not multiplayer:
		# shut down any existing sockets
		for i in range(2):
		
			if ip_sockets[i] is not None:
			
				ip_sockets[i].close ()
				ip_sockets[i] = None
			
			if ipx_sockets[i] is not None:
			
				ipx_sockets[i].close ()
				ipx_sockets[i] = None
			
	else:
		# open sockets
		NET_OpenIP ()
		NET_OpenIPX ()
	

"""
//===================================================================


/*
====================
NET_Init
====================
"""
def NET_Init ():

	pass


"""
====================
NET_Socket
====================
"""
def NET_Socket (net_interface, port): #char *, int (returns int, a python socket object or None on failure)

	global errno

	#int newsocket;
	#struct sockaddr_in address;
	#qboolean _true = true;
	#int	i = 1;

	try:
		newsocket = socket.socket (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	except OSError as e:
		errno = e.errno
		common.Com_Printf ("ERROR: UDP_OpenSocket: socket: {}".format(NET_ErrorString()))
		return None
	
	# make it non-blocking
	try:
		newsocket.setblocking (False) # ioctl (newsocket, FIONBIO, &_true)
	except OSError as e:
		errno = e.errno
		common.Com_Printf ("ERROR: UDP_OpenSocket: ioctl FIONBIO:{}\n".format(NET_ErrorString()))
		return None
	
	# make it broadcast capable
	try:
		newsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
	except OSError as e:
		errno = e.errno
		common.Com_Printf ("ERROR: UDP_OpenSocket: setsockopt SO_BROADCAST:{}\n".format(NET_ErrorString()))
		return None
	
	if not net_interface or q_shared.Q_stricmp(net_interface, "localhost") == 0:
		sin_addr = "" # INADDR_ANY
	else:
		sadr = NET_StringToSockaddr (net_interface)
		sin_addr = sadr[0] if sadr is not None else ""

	if port == qcommon.PORT_ANY:
		sin_port = 0
	else:
		sin_port = socket.htons(port & 0xffff) # htons((short)port)

	# address.sin_family = AF_INET;

	try:
		newsocket.bind ((sin_addr, socket.ntohs(sin_port))) # python takes the port in host byte order
	except OSError as e:
		errno = e.errno
		common.Com_Printf ("ERROR: UDP_OpenSocket: bind: {}\n".format(NET_ErrorString()))
		newsocket.close ()
		return None
	
	return newsocket


"""
====================
NET_Shutdown
====================
"""
def NET_Shutdown ():

	NET_Config (False)	# close sockets


"""
====================
NET_ErrorString
====================
"""
def NET_ErrorString (): #(returns char *)

	#int		code;

	code = errno
	return os.strerror (code)

# sleeps msec or until net socket is ready
def NET_Sleep(msec: int):

	#struct timeval timeout;
	#fd_set	fdset;
	#extern cvar_t *dedicated;
	#extern qboolean stdin_active;

	if ip_sockets[qcommon.netsrc_t.NS_SERVER.value] is None or (common.dedicated is not None and not common.dedicated.value):
		return # we're not a server, just run full speed

	fdset = [] # FD_ZERO(&fdset);
	if sys_linux.stdin_active:
		fdset.append(sys.stdin) # stdin is processed too
	fdset.append(ip_sockets[qcommon.netsrc_t.NS_SERVER.value]) # network socket
	timeout = msec / 1000.0 # timeout.tv_sec = msec/1000; timeout.tv_usec = (msec%1000)*1000;
	select.select(fdset, [], [], timeout)

