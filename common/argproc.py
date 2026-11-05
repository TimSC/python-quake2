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

Common argument processing

=======================================================================
"""
from __future__ import annotations

import sys
from common.header import shared
from common import clientserver

"""
#include "header/common.h"
"""

MAX_NUM_ARGVS = 50

com_argc = None #int
com_argv = [] #char	*[MAX_NUM_ARGVS+1];
for i in range(MAX_NUM_ARGVS+1):
	com_argv.append(None)

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
		clientserver.Com_Error (shared.ERR_FATAL, "argc > MAX_NUM_ARGVS");
	com_argc = argc;
	for i in range (argc):
	
		if sys.argv[i] is None or len(sys.argv[i]) >= shared.MAX_TOKEN_CHARS:
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
		clientserver.Com_Error (shared.ERR_FATAL, "COM_AddParm: MAX_NUM)ARGS")
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
		clientserver.Com_Printf ("{}".format(key))

		if i >= len(s):
		
			clientserver.Com_Printf ("MISSING VALUE\n")
			return
		
		i += 1
		o = i
		while i < len(s) and s[i] != '\\':
			i += 1
		value = s[o:i]

		if i < len(s):
			i += 1
		clientserver.Com_Printf ("{}\n".format(value))
