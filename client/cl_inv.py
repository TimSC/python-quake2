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
from __future__ import annotations

pass
pass
from client import cl_main, cl_scrn, keys
from linux import vid_so
from common.header import shared
from common.shared import shared as shared_c
from common import movemsg
from common import netchan
"""
// cl_inv.c -- client inventory screen

#include "client.h"
"""


"""
================
CL_ParseInventory
================
"""
def CL_ParseInventory ():

	#int		i;

	for i in range(shared.MAX_ITEMS):
		cl_main.cl.inventory[i] = movemsg.MSG_ReadShort (netchan.net_message)


"""
================
Inv_DrawString
================
"""
def Inv_DrawString (x, y, string): #int, int, char *

	for ch in string: # while (*string)
	
		vid_so.re.DrawChar (x, y, ord(ch))
		x+=8
	

def SetStringHighBit (s): #char * (returns the changed string)

	return "".join(chr(ord(ch) | 128) for ch in s) # while (*s) *s++ |= 128;


"""
================
CL_DrawInventory
================
"""
DISPLAY_ITEMS = 17

def CL_DrawInventory ():

	"""
	int		i, j;
	int		num, selected_num, item;
	int		index[MAX_ITEMS];
	char	string[1024];
	int		x, y;
	char	binding[1024];
	char	*bind;
	int		selected;
	int		top;
	"""
	index = [0] * shared.MAX_ITEMS

	selected = cl_main.cl.frame.playerstate.stats[shared.STAT_SELECTED_ITEM]

	num = 0
	selected_num = 0
	for i in range(shared.MAX_ITEMS):
	
		if i==selected:
			selected_num = num
		if cl_main.cl.inventory[i]:
		
			index[num] = i
			num += 1
		
	# determine scroll point
	top = selected_num - DISPLAY_ITEMS//2
	if num - top < DISPLAY_ITEMS:
		top = num - DISPLAY_ITEMS
	if top < 0:
		top = 0

	x = (vid_so.viddef.width-256)//2
	y = (vid_so.viddef.height-240)//2

	# repaint everything next frame
	cl_scrn.SCR_DirtyScreen ()

	vid_so.re.DrawPic (x, y+8, "inventory")

	y += 24
	x += 24
	Inv_DrawString (x, y, "hotkey ### item")
	Inv_DrawString (x, y+8, "------ --- ----")
	y += 16
	i = top
	while i<num and i < top+DISPLAY_ITEMS:
	
		item = index[i]
		# search for a binding
		binding = "use {}".format(cl_main.cl.configstrings[shared.CS_ITEMS+item])
		bind = ""
		for j in range(256):
			if keys.keybindings[j] and not shared_c.Q_stricmp (keys.keybindings[j], binding):
			
				bind = keys.Key_KeynumToString(j)
				break
			
		string = "{:>6} {:3d} {}".format(bind, cl_main.cl.inventory[item],
			cl_main.cl.configstrings[shared.CS_ITEMS+item] ) # "%6s %3i %s"
		if item != selected:
			string = SetStringHighBit (string)
		else:	# draw a blinky cursor by the selected item
		
			if int(cl_main.cls.realtime*10) & 1:
				vid_so.re.DrawChar (x-8, y, 15)
		
		Inv_DrawString (x, y, string)
		y += 8
		i += 1

