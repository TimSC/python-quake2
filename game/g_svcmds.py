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

Game side of server CMDs. At this time only the ipfilter.

=======================================================================
"""
from __future__ import annotations

import struct
from game import g_main
from game.header.local import GAMEVERSION
from common.header.shared import PRINT_HIGH
from common.shared.shared import Q_stricmp

"""
#include "header/local.h"
"""

MAX_IPFILTERS = 1024

class ipfilter_t(object):
	def __init__(self):
		self.mask = 0
		self.compare = 0

ipfilters = [ipfilter_t() for _ in range(MAX_IPFILTERS)]
numipfilters = 0


def Svcmd_Test_f ():
	g_main.gi.cprintf (None, PRINT_HIGH, "Svcmd_Test_f()\n")

def StringToFilter (s, f):
	b = bytearray(4)
	m = bytearray(4)

	i = 0
	idx = 0
	while i < 4:
		if idx >= len(s) or not s[idx].isdigit():
			g_main.gi.cprintf(None, PRINT_HIGH, "Bad filter address: %s\n" % s)
			return False
		val = 0
		while idx < len(s) and s[idx].isdigit():
			val = val*10 + int(s[idx])
			idx += 1
		b[i] = val
		if val != 0:
			m[i] = 255
		if idx >= len(s):
			break
		idx += 1
		i += 1

	f.mask = int.from_bytes(m, 'little')
	f.compare = int.from_bytes(b, 'little')
	return True

def SV_FilterPacket (from_):
	i = 0
	m = bytearray(4)
	idx = 0

	while idx < len(from_) and i < 4:
		m[i] = 0
		while idx < len(from_) and from_[idx].isdigit():
			m[i] = m[i]*10 + int(from_[idx])
			idx += 1
		if idx >= len(from_) or from_[idx] == ':':
			break
		i += 1
		idx += 1

	in_ = int.from_bytes(m, 'little')

	i = 0
	while i < numipfilters:
		if (in_ & ipfilters[i].mask) == ipfilters[i].compare:
			return (g_main.filterban.value != 0)
		i += 1

	return (g_main.filterban.value == 0)

def SVCmd_AddIP_f ():
	global numipfilters
	i = 0

	if g_main.gi.argc() < 3:
		g_main.gi.cprintf(None, PRINT_HIGH, "Usage:  addip <ip-mask>\n")
		return

	while i < numipfilters:
		if ipfilters[i].compare == 0xffffffff:
			break		# free spot
		i += 1
	if i == numipfilters:
		if numipfilters == MAX_IPFILTERS:
			g_main.gi.cprintf (None, PRINT_HIGH, "IP filter list is full\n")
			return
		numipfilters += 1

	if not StringToFilter (g_main.gi.argv(2), ipfilters[i]):
		ipfilters[i].compare = 0xffffffff

def SVCmd_RemoveIP_f ():
	global numipfilters
	f = ipfilter_t()

	if g_main.gi.argc() < 3:
		g_main.gi.cprintf(None, PRINT_HIGH, "Usage:  sv removeip <ip-mask>\n")
		return

	if not StringToFilter (g_main.gi.argv(2), f):
		return

	i = 0
	while i < numipfilters:
		if ipfilters[i].mask == f.mask and ipfilters[i].compare == f.compare:
			j = i + 1
			while j < numipfilters:
				ipfilters[j-1] = ipfilters[j]
				j += 1
			numipfilters -= 1
			g_main.gi.cprintf (None, PRINT_HIGH, "Removed.\n")
			return
		i += 1
	g_main.gi.cprintf (None, PRINT_HIGH, "Didn't find %s.\n" % g_main.gi.argv(2))

def SVCmd_ListIP_f ():
	i = 0

	g_main.gi.cprintf (None, PRINT_HIGH, "Filter list:\n")
	while i < numipfilters:
		b = ipfilters[i].compare.to_bytes(4, 'little')
		g_main.gi.cprintf (None, PRINT_HIGH, "%3i.%3i.%3i.%3i\n" % (b[0], b[1], b[2], b[3]))
		i += 1

def SVCmd_WriteIP_f ():
	game = g_main.gi.cvar("game", "", 0)

	if not game.string:
		name = "%s/listip.cfg" % GAMEVERSION
	else:
		name = "%s/listip.cfg" % game.string

	g_main.gi.cprintf (None, PRINT_HIGH, "Writing %s.\n" % name)

	try:
		f = open(name, "wb")
	except:
		g_main.gi.cprintf (None, PRINT_HIGH, "Couldn't open %s\n" % name)
		return

	f.write(("set filterban %d\n" % int(g_main.filterban.value)).encode())

	i = 0
	while i < numipfilters:
		b = ipfilters[i].compare.to_bytes(4, 'little')
		f.write(("sv addip %i.%i.%i.%i\n" % (b[0], b[1], b[2], b[3])).encode())
		i += 1

	f.close()

def ServerCommand ():
	cmd = g_main.gi.argv(1)
	if Q_stricmp (cmd, "test") == 0:
		Svcmd_Test_f ()
	elif Q_stricmp (cmd, "addip") == 0:
		SVCmd_AddIP_f ()
	elif Q_stricmp (cmd, "removeip") == 0:
		SVCmd_RemoveIP_f ()
	elif Q_stricmp (cmd, "listip") == 0:
		SVCmd_ListIP_f ()
	elif Q_stricmp (cmd, "writeip") == 0:
		SVCmd_WriteIP_f ()
	else:
		g_main.gi.cprintf (None, PRINT_HIGH, "Unknown server command \"%s\"\n" % cmd)
