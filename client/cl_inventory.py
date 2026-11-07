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

This file implements the inventory screen

=======================================================================
"""
from __future__ import annotations

from client.header import keyboard as keyboard_h

from client.vid import vid

from client import cl_main
from client.vid import vid
from common.header import shared
from common.shared import shared as shared_c
from common import movemsg
from common import netchan
from client import cl_keyboard
from client import cl_main
from client import cl_screen

"""
#include "header/client.h"
"""

def CL_ParseInventory ():

	#int		i;

	for i in range(shared.MAX_ITEMS):
		cl_main.cl.inventory[i] = movemsg.MSG_ReadShort (netchan.net_message)


def Inv_DrawStringScaled(x: int, y: int, string: str, factor: float): #int, int, char *, float (static)

	for ch in string: # while (*string)

		vid.Draw_CharScaled(x, y, ord(ch), factor)
		x += factor*8


def SetStringHighBit (s): #char * (returns the changed string)

	return "".join(chr(ord(ch) | 128) for ch in s) # while (*s) *s++ |= 128;


"""
================
CL_DrawInventory
================
"""
DISPLAY_ITEMS = 17

def CL_DrawInventory(): #

	"""
	int i, j;
	int num, selected_num, item;
	char string[1024];
	int x, y;
	char binding[1024];
	const char *bind;
	int selected;
	int top;
	int index[MAX_ITEMS] = {0};
	float scale = cl_screen.SCR_GetHUDScale();
	"""
	string = [None] * 1024
	binding = [None] * 1024
	index = [0] * shared.MAX_ITEMS
	scale = cl_screen.SCR_GetHUDScale()

	selected = cl_main.cl.frame.playerstate.stats[shared.STAT_SELECTED_ITEM]
	num = 0
	selected_num = 0
	for i in range(shared.MAX_ITEMS):

		if i == selected:

			selected_num = num


		if cl_main.cl.inventory[i]:

			index[num] = i
			num += 1


	# determine scroll point
	top = int(selected_num - DISPLAY_ITEMS / 2) # C int
	if num - top < DISPLAY_ITEMS:

		top = num - DISPLAY_ITEMS


	if top < 0:

		top = 0


	x = int((vid.viddef.width - scale*256) / 2) # C int
	y = int((vid.viddef.height - scale*240) / 2) # C int
	# repaint everything next frame
	cl_screen.SCR_DirtyScreen()
	vid.Draw_PicScaled(x, y + scale*8, "inventory", scale)
	y += scale*24
	x += scale*24
	Inv_DrawStringScaled(x, y, "hotkey ### item", scale)
	Inv_DrawStringScaled(x, y + scale*8, "------ --- ----", scale)
	y += scale*16
	for i in range(top, num and i < top + DISPLAY_ITEMS):

		item = index[i]
		# search for a binding
		binding = "use %s" % (cl_main.cl.configstrings[shared.CS_ITEMS + item],) # Com_sprintf
		bind = ""
		for j in range(keyboard_h.K_LAST):

			if cl_keyboard.keybindings[j] and not shared_c.Q_stricmp(cl_keyboard.keybindings[j], binding):

				bind = cl_keyboard.Key_KeynumToString(j)
				break


		string = "%6.6s %3i %s" % (bind, cl_main.cl.inventory[item], cl_main.cl.configstrings[shared.CS_ITEMS + item],) # Com_sprintf
		if item != selected:

			SetStringHighBit(string)

		else:

			# draw a blinky cursor by the selected item
			if (cl_main.cls.realtime * 10) & 1:

				vid.Draw_CharScaled(x - scale*8, y, 15, scale)


		Inv_DrawStringScaled(x, y, string, scale)
		y += scale*8
