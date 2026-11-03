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
from qcommon import cvar
from game import q_shared
"""
// in_null.c -- for systems without a mouse

#include "../client/client.h"
"""
in_mouse = None #cvar_t	*
in_joystick = None # cvar_t	*

def IN_Init ():

	global in_mouse, in_joystick

	in_mouse = cvar.Cvar_Get ("in_mouse", "1", q_shared.CVAR_ARCHIVE)
	in_joystick = cvar.Cvar_Get ("in_joystick", "0", q_shared.CVAR_ARCHIVE)

"""
void IN_Shutdown (void)
{
}

void IN_Commands (void)
{
}
"""
def IN_Move (cmd):
	pass

"""
void IN_Activate (qboolean active)
{
}
"""
