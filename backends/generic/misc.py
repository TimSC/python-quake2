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

"""
from __future__ import annotations

import os
import sys
"""
#include <stdio.h>
#include <string.h>

#include "../../common/header/shared.h"
"""
"""
static void SetExecutablePath(char* exePath)
{
	// !!! this assumes that exePath can hold PATH_MAX chars !!!
	...
}

static qboolean
Sys_GetCwd(char *buf, size_t size)
{
	if (getcwd(buf, size) == NULL)
	{
		return false;
	}
	return Q_strlcat(buf, "/", size) == 1;
}
"""
_exeDir = "" #static char exeDir[PATH_MAX], in Sys_GetBinaryDir

def Sys_GetBinaryDir()->str: #(returns const char *)
	# Q2PORT: the "executable" is main.py, so this is the directory it is in

	global _exeDir

	if _exeDir != "":
		return _exeDir

	_exeDir = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else ".")) + "/"
	return _exeDir

"""
void Sys_SetupFPU(void)
{
#if defined(__i386__)
	// set to double precision, and enable fast math for fdiv/fsqrt
	...
#endif
}
"""
def Sys_SetupFPU(): #void

	# Q2PORT: Python's floats are always IEEE double, nothing to set up
	pass
