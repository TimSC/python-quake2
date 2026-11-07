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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
USA.

=======================================================================

This file implements the generic part of the menu

=======================================================================
"""
from __future__ import annotations

from backends.unix import system
from client.vid import vid
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cvar
from client import cl_keyboard
from client import cl_main
from client import cl_screen
from client.header import keyboard as keyboard_h
from client.input import sdl2
from client.menu.header import qmenu as qmenu_h
from client.vid import vid

"""
#include <ctype.h>
#include "../header/client.h"
#include "header/qmenu.h"

void IN_GetClipboardText(char *out, size_t n);
int IN_SetClipboardText(const char *s);

static void Action_Draw(menuaction_s *a);
static void Menu_DrawStatusBar(const char *string);
static void MenuList_Draw(menulist_s *l);
static void Separator_Draw(menuseparator_s *s);
static void Slider_Draw(menuslider_s *s);
static void SpinControl_Draw(menulist_s *s);

static qboolean Slider_DoSlide(menuslider_s *s, int dir);
static qboolean SpinControl_DoSlide(menulist_s *s, int dir);

extern viddef_t viddef;
"""

def VID_WIDTH(): return vid.viddef.width #define VID_WIDTH viddef.width
def VID_HEIGHT(): return vid.viddef.height #define VID_HEIGHT viddef.height

menu_in_sound = "misc/menu1.wav" #const char *
menu_move_sound = "misc/menu2.wav" #const char *
menu_out_sound = "misc/menu3.wav" #const char *

# "Wrapper" for Q_clamp to evaluate parameters just once (TODO: delete?)
def ClampCvar(min_: float, max_: float, value: float)->float: #float, float, float (returns float)

	return shared.Q_clamp(value, min_, max_)

"""
=================
Bitmap_Draw
=================
"""
def Bitmap_Draw(item: qmenu_h.menubitmap_s): #menubitmap_s * (static)

	"""
	const char *pic;
	"""

	if ((item.generic.flags & qmenu_h.QMF_HIGHLIGHT_IF_FOCUS) and
		(Menu_ItemAtCursor(item.generic.parent) is item)):

		pic = item.focuspic

	else:

		pic = item.generic.name


	if pic and pic[0] != '\0':

		scale = cl_screen.SCR_GetMenuScale()

		vid.Draw_PicScaled(item.generic.x * scale, item.generic.y * scale,
			pic, scale)

def Action_Draw(a: qmenu_h.menuaction_s): #menuaction_s * (static)

	scale = cl_screen.SCR_GetMenuScale()
	x = 0
	y = 0

	x = a.generic.parent.x + a.generic.x
	y = a.generic.parent.y + a.generic.y

	if a.generic.flags & qmenu_h.QMF_LEFT_JUSTIFY:

		if a.generic.flags & qmenu_h.QMF_GRAYED:

			Menu_DrawStringDark(x + (qmenu_h.LCOLUMN_OFFSET * scale),
				y, a.generic.name)


		else:

			Menu_DrawString(x + (qmenu_h.LCOLUMN_OFFSET * scale),
				y, a.generic.name)


	else:

		if a.generic.flags & qmenu_h.QMF_GRAYED:

			Menu_DrawStringR2LDark(x + (qmenu_h.LCOLUMN_OFFSET * scale),
				y, a.generic.name)


		else:

			Menu_DrawStringR2L(x + (qmenu_h.LCOLUMN_OFFSET * scale),
				y, a.generic.name)



	if a.generic.ownerdraw:

		a.generic.ownerdraw(a)

def Field_InitState(f: qmenu_h.menufield_s, s: str, len_: int, vislen: int): #menufield_s *, const char *, int, int

	if len_ < 1:

		len_ = 1

	elif len_ > 80: # sizeof(f->buffer)

		len_ = 80


	if vislen < 1:

		vislen = 1

	elif vislen > len_:

		vislen = len_


	f.buffer = "" # *f->buffer = '\0';

	if s is not None:

		# Q_strlcpy(f->buffer, s, len) returns strlen(s)
		if (((f.generic.flags & qmenu_h.QMF_NUMBERSONLY) and not shared_c.Q_strisnum(s)) or
			len(s) >= len_):

			f.buffer = "" # *f->buffer = '\0';

		else:

			f.buffer = s


	f.length = len_
	f.visible_length = vislen
	f.cursor = len(f.buffer)

def Field_Draw(f: qmenu_h.menufield_s): #menufield_s * (static)

	"""
	int i, n;
	char tempbuffer[128] = "";
	"""
	scale = cl_screen.SCR_GetMenuScale()
	x = 0
	y = 0

	x = f.generic.parent.x + f.generic.x
	y = f.generic.parent.y + f.generic.y

	if f.generic.name:

		Menu_DrawStringR2LDark(x + qmenu_h.LCOLUMN_OFFSET * scale,
			y, f.generic.name)


	n = f.visible_length + 1

	if n > 128: # sizeof(tempbuffer)

		n = 128


	i = (f.cursor - f.visible_length) if (f.cursor > f.visible_length) else 0
	tempbuffer = f.buffer[i:][:n - 1] # Q_strlcpy(tempbuffer, f->buffer + i, n);

	vid.Draw_CharScaled(x + (16 * scale),
			(y - 4) * scale, 18, scale)
	vid.Draw_CharScaled(x + 16 * scale,
			(y + 4) * scale, 24, scale)

	vid.Draw_CharScaled(x + (24 * scale) + (f.visible_length * (8 * scale)),
			(y - 4) * scale, 20, scale)
	vid.Draw_CharScaled(x + (24 * scale) + (f.visible_length * (8 * scale)),
			(y + 4) * scale, 26, scale)

	for i in range(f.visible_length):

		vid.Draw_CharScaled(x + (24 * scale) + (i * 8 * scale),
				(y - 4) * scale, 19, scale)
		vid.Draw_CharScaled(x + (24 * scale) + (i * 8 * scale),
				(y + 4) * scale, 25, scale)


	Menu_DrawString(x + (24 * scale),
		y, tempbuffer)

	if Menu_ItemAtCursor(f.generic.parent) is f:

		if int(system.Sys_Milliseconds() / 250) & 1:

			"""
			int offset;
			"""

			if f.cursor > f.visible_length:

				offset = f.visible_length

			else:

				offset = f.cursor


			vid.Draw_CharScaled(
				x + (24 * scale) + (offset * (8 * scale)),
				y * scale, 11, scale)

def Field_ResetCursor(m: qmenu_h.menuframework_s): #menuframework_s *

	item = Menu_ItemAtCursor(m) # menucommon_s *

	if item and item.type == qmenu_h.MTYPE_FIELD:

		f = item # (menufield_s *)item

		f.cursor = len(f.buffer)

def Field_Key(f: qmenu_h.menufield_s, key: int)->bool: #menufield_s *, int (returns qboolean)

	"""
	char txt[256];
	"""

	if cl_keyboard.keydown[keyboard_h.K_CTRL]:

		if key == ord('l'):

			f.buffer = "" # *f->buffer = '\0';
			f.cursor = 0

			return True


		if key == ord('c') or key == ord('x'):

			if f.buffer: # *f->buffer != '\0'

				if sdl2.IN_SetClipboardText(f.buffer):

					clientserver.Com_Printf("Copying menu field to clipboard failed.\n")

				elif key == ord('x'):

					f.buffer = "" # *f->buffer = '\0';
					f.cursor = 0



			return True


		if key == ord('v'):

			txt = sdl2.IN_GetClipboardText(256) # IN_GetClipboardText(txt, sizeof(txt));

			if txt: # *txt != '\0'

				if (f.generic.flags & qmenu_h.QMF_NUMBERSONLY) and not shared_c.Q_strisnum(txt):

					return False


				f.buffer, slen = shared_c.Q_strins(f.buffer, txt, f.cursor, f.length)
				f.cursor += slen



		return True


	if key in (keyboard_h.K_KP_LEFTARROW, keyboard_h.K_LEFTARROW):

		if f.cursor > 0:

			f.cursor -= 1


	elif key in (keyboard_h.K_KP_RIGHTARROW, keyboard_h.K_RIGHTARROW):

		if f.cursor < len(f.buffer): # f->buffer[f->cursor] != '\0'

			f.cursor += 1


	elif key == keyboard_h.K_BACKSPACE:

		if f.cursor > 0:

			f.buffer = shared_c.Q_strdel(f.buffer, f.cursor - 1, 1)
			f.cursor -= 1


	elif key == keyboard_h.K_END:

		if f.cursor >= len(f.buffer): # f->buffer[f->cursor] == '\0'

			f.cursor = 0

		else:

			f.cursor = len(f.buffer)


	elif key in (keyboard_h.K_KP_DEL, keyboard_h.K_DEL):

		if f.cursor < len(f.buffer): # f->buffer[f->cursor] != '\0'

			f.buffer = shared_c.Q_strdel(f.buffer, f.cursor, 1)


	elif key in (keyboard_h.K_KP_ENTER, keyboard_h.K_ENTER, keyboard_h.K_ESCAPE, keyboard_h.K_TAB):

		return False

	else:

		if key > 127:

			return False


		if not (ord('0') <= key <= ord('9')) and (f.generic.flags & qmenu_h.QMF_NUMBERSONLY): # !isdigit(key)

			return False


		txt = chr(key) # *txt = key; *(txt + 1) = '\0';

		f.buffer, slen = shared_c.Q_strins(f.buffer, txt, f.cursor, f.length)
		f.cursor += slen


	return True

def Menu_AddItem(menu: qmenu_h.menuframework_s, item): #menuframework_s *, void *

	if (menu.nitems >= 0) and (menu.nitems < qmenu_h.MAXMENUITEMS):

		menu.items[menu.nitems] = item
		item.parent = menu # ((menucommon_s *)item)->parent = menu;
		menu.nitems += 1

"""
 * This function takes the given menu, the direction, and attempts
 * to adjust the menu's cursor so that it's at the next available
 * slot.
"""
def Menu_AdjustCursor(m: qmenu_h.menuframework_s, dir_: int): #menuframework_s *, int

	citem = None # menucommon_s *

	# see if it's in a valid spot
	if (m.cursor >= 0) and (m.cursor < m.nitems):

		citem = Menu_ItemAtCursor(m)
		if citem is not None:

			if (citem.type != qmenu_h.MTYPE_SEPARATOR and
				(citem.flags & qmenu_h.QMF_INACTIVE) != qmenu_h.QMF_INACTIVE):

				return




	# it's not in a valid spot, so crawl in the direction
	# indicated until we find a valid spot
	cursor = m.nitems

	while cursor > 0: # while (cursor-- > 0)

		cursor -= 1
		citem = Menu_ItemAtCursor(m)

		if citem:

			if (citem.type != qmenu_h.MTYPE_SEPARATOR and
			(citem.flags & qmenu_h.QMF_INACTIVE) != qmenu_h.QMF_INACTIVE):

				break



		m.cursor += dir_

		if m.cursor >= m.nitems:

			m.cursor = 0


		if m.cursor < 0:

			m.cursor = m.nitems - 1

def Menu_Center(menu: qmenu_h.menuframework_s): #menuframework_s *

	"""
	int height;
	"""
	scale = cl_screen.SCR_GetMenuScale()

	height = menu.items[menu.nitems - 1].y # ((menucommon_s *)menu->items[menu->nitems - 1])->y
	height += 10

	menu.y = int((VID_HEIGHT() / scale - height) / 2) # int y

def Menu_Draw(menu: qmenu_h.menuframework_s): #menuframework_s *

	"""
	int i;
	menucommon_s *item;
	"""
	scale = cl_screen.SCR_GetMenuScale()

	# draw contents
	for i in range(menu.nitems):

		t = menu.items[i].type # ((menucommon_s *)menu->items[i])->type
		if t == qmenu_h.MTYPE_FIELD:

			Field_Draw(menu.items[i])

		elif t == qmenu_h.MTYPE_SLIDER:

			Slider_Draw(menu.items[i])

		elif t == qmenu_h.MTYPE_LIST:

			MenuList_Draw(menu.items[i])

		elif t == qmenu_h.MTYPE_SPINCONTROL:

			SpinControl_Draw(menu.items[i])

		elif t == qmenu_h.MTYPE_BITMAP:

			Bitmap_Draw(menu.items[i])

		elif t == qmenu_h.MTYPE_ACTION:

			Action_Draw(menu.items[i])

		elif t == qmenu_h.MTYPE_SEPARATOR:

			Separator_Draw(menu.items[i])



	item = Menu_ItemAtCursor(menu)

	if item and item.cursordraw:

		item.cursordraw(item)

	elif menu.cursordraw:

		menu.cursordraw(menu)

	elif item and (item.type != qmenu_h.MTYPE_FIELD) and item.type != qmenu_h.MTYPE_BITMAP:

		if item.flags & qmenu_h.QMF_LEFT_JUSTIFY:

			vid.Draw_CharScaled(menu.x + (item.x / scale - 24 + item.cursor_offset) * scale,
					(menu.y + item.y) * scale,
					12 + (int(system.Sys_Milliseconds() / 250) & 1), scale)

		else:

			# FIXME:: menu->x + (item->x / scale + 24 + item->cursor_offset) * scale
			vid.Draw_CharScaled(menu.x + (item.cursor_offset) * scale,
					(menu.y + item.y) * scale,
					12 + (int(system.Sys_Milliseconds() / 250) & 1), scale)



	if item:

		if item.statusbarfunc:

			item.statusbarfunc(item) # (void *)item


		elif item.statusbar:

			Menu_DrawStatusBar(item.statusbar)


		else:

			Menu_DrawStatusBar(menu.statusbar)


	else:

		Menu_DrawStatusBar(menu.statusbar)

def Menu_DrawStatusBar(string: str): #const char * (static)

	scale = cl_screen.SCR_GetMenuScale()

	if string:

		l = len(string) # (int)strlen(string)
		col = int((VID_WIDTH() / 2) - int(l*8 / 2) * scale) # int col

		vid.Draw_Fill(0, VID_HEIGHT() - 8 * scale, VID_WIDTH(), 8 * scale, 4)
		Menu_DrawString(col, VID_HEIGHT() / scale - 8, string)

	else:

		vid.Draw_Fill(0, VID_HEIGHT() - 8 * scale, VID_WIDTH(), 8 * scale, 0)

"""
 * Draws one solid graphics character cx and cy are in 320*240
 * coordinates, and will be centered on higher res screens.
"""
def Menu_DrawCharacter(cx: int, cy: int, num: int): #int, int, int

	scale = cl_screen.SCR_GetMenuScale()

	vid.Draw_CharScaled(cx + (int(vid.viddef.width - 320 * scale) >> 1), cy + (int(vid.viddef.height - 240 * scale) >> 1), num, scale)

def Menu_DrawString(x: int, y: int, string: str): #int, int, const char *

	"""
	unsigned i;
	"""
	scale = cl_screen.SCR_GetMenuScale()

	for i in range(len(string)): # for (i = 0; string[i] != '\0'; i++)

		vid.Draw_CharScaled(x + i * 8 * scale, y * scale, ord(string[i]), scale)

def Menu_DrawStringDark(x: int, y: int, string: str): #int, int, const char *

	"""
	unsigned i;
	"""
	scale = cl_screen.SCR_GetMenuScale()

	for i in range(len(string)): # for (i = 0; string[i] != '\0'; i++)

		vid.Draw_CharScaled(x + i * 8 * scale, y * scale, ord(string[i]) + 128, scale)

def Menu_DrawStringR2L(x: int, y: int, string: str): #int, int, const char *

	"""
	unsigned i, slen;
	float scale;
	"""

	slen = len(string)
	scale = cl_screen.SCR_GetMenuScale()

	for i in range(slen):

		vid.Draw_CharScaled(x - i * 8 * scale, y * scale, ord(string[slen - i - 1]), scale)

def Menu_DrawStringR2LDark(x: int, y: int, string: str): #int, int, const char *

	"""
	unsigned i, slen;
	float scale;
	"""

	slen = len(string)
	scale = cl_screen.SCR_GetMenuScale()

	for i in range(slen):

		vid.Draw_CharScaled(x - i * 8 * scale, y * scale, ord(string[slen - i - 1]) + 128, scale)

def Menu_DrawTextBox(x: int, y: int, width: int, lines: int): #int, int, int, int

	"""
	int cx, cy;
	int n;
	"""
	scale = cl_screen.SCR_GetMenuScale()

	# draw left side
	cx = x
	cy = y
	Menu_DrawCharacter(cx * scale, cy * scale, 1)

	for n in range(lines):

		cy += 8
		Menu_DrawCharacter(cx * scale, cy * scale, 4)


	Menu_DrawCharacter(cx * scale, cy * scale + 8 * scale, 7)

	# draw middle
	cx += 8

	while width > 0:

		cy = y
		Menu_DrawCharacter(cx * scale, cy * scale, 2)

		for n in range(lines):

			cy += 8
			Menu_DrawCharacter(cx * scale, cy * scale, 5)


		Menu_DrawCharacter(cx * scale, cy *scale + 8 * scale, 8)
		width -= 1
		cx += 8


	# draw right side
	cy = y
	Menu_DrawCharacter(cx * scale, cy * scale, 3)

	for n in range(lines):

		cy += 8
		Menu_DrawCharacter(cx * scale, cy * scale, 6)


	Menu_DrawCharacter(cx * scale, cy * scale + 8 * scale, 9)

def Menu_DrawText(x: int, y: int, str_: str): #int, int, const char *

	"""
	int cx, cy;
	float scale;
	"""

	scale = cl_screen.SCR_GetMenuScale()
	cx = x
	cy = y

	for c in str_: # for (; *str != '\0'; str++)

		if c == '\n':

			cx = x
			cy += 8

		else:

			Menu_DrawCharacter(cx * scale, cy * scale, ord(c) + 128)
			cx += 8

def GetString2DSize(s: str): #const char *, int *, int * (static)

	# Q2PORT: returns (w, h) instead of filling *w_out and *h_out

	"""
	int n, w, h;
	"""

	n = 0
	w = 0
	h = 0

	for c in s: # for (; *s != '\0'; s++)

		if c == '\n':

			h += 1
			n = 0

		else:

			n += 1

			if n > w:

				w = n




	if n:

		h += 1


	return w, h # *w_out = w; *h_out = h;

def Menu_DrawPopup(x: int, y: int, pup: qmenu_h.menupopup_s): #int, int, const menupopup_s *

	"""
	int w, h;
	"""

	if not pup.string:

		return


	if pup.endtime > 0 and pup.endtime < cl_main.cls.realtime:

		return


	if not vid.R_EndWorldRenderpass():

		return


	w, h = GetString2DSize(pup.string)

	if w:

		"""
		int cx, cy;
		"""

		w += 2

		cx = int((x - (w + 2) * 8) / 2) # int cx
		cy = int((y - (h + 2) * 8) / 3) # int cy

		Menu_DrawTextBox(cx, cy, w, h)
		Menu_DrawText(cx + 16, cy + 8, pup.string)

def Menu_StartPopup(pup: qmenu_h.menupopup_s, string: str, lifetime: int): #menupopup_s *, const char *, int

	pup.string = string
	pup.endtime = 0 if (lifetime <= 0) else (cl_main.cls.realtime + lifetime)

def Menu_ItemAtCursor(m: qmenu_h.menuframework_s): #menuframework_s * (returns void *)

	if (m.cursor < 0) or (m.cursor >= m.nitems):

		return None


	return m.items[m.cursor]

def Menu_SelectItem(s: qmenu_h.menuframework_s)->bool: #menuframework_s * (returns qboolean)

	item = Menu_ItemAtCursor(s) # (menucommon_s *)

	if item.callback:

		item.callback(item)

		return True


	return False

def Menu_SetStatusBar(m: qmenu_h.menuframework_s, string: str): #menuframework_s *, const char *

	m.statusbar = string

def Menu_SlideItem(s: qmenu_h.menuframework_s, dir_: int)->bool: #menuframework_s *, int (returns qboolean)

	item = Menu_ItemAtCursor(s) # (menucommon_s *)

	if not item:

		return False


	if item.type == qmenu_h.MTYPE_SLIDER:

		return Slider_DoSlide(item, dir_) # (menuslider_s *)item

	elif item.type == qmenu_h.MTYPE_SPINCONTROL:

		return SpinControl_DoSlide(item, dir_) # (menulist_s *)item


	return False

def MenuList_Draw(l: qmenu_h.menulist_s): #menulist_s * (static)

	"""
	const char **n;
	"""
	scale = cl_screen.SCR_GetMenuScale()
	x = 0
	y = 0

	x = l.generic.parent.x + l.generic.x
	y = l.generic.parent.y + l.generic.y

	Menu_DrawStringR2LDark(x + (qmenu_h.LCOLUMN_OFFSET * scale),
		y, l.generic.name)

	n = 0 # n = l->itemnames;

	vid.Draw_Fill(x - 112,
		y + l.curvalue * 10 * scale + 10 * scale, 128, 10, 16)

	while l.itemnames[n]: # while (*n)

		Menu_DrawStringR2LDark(x + (qmenu_h.LCOLUMN_OFFSET * scale),
			y, l.itemnames[n])

		n += 1
		y += 10 * scale

def Separator_Draw(s: qmenu_h.menuseparator_s): #menuseparator_s * (static)

	x = 0
	y = 0

	x = s.generic.parent.x + s.generic.x
	y = s.generic.parent.y + s.generic.y

	if s.generic.name:

		Menu_DrawStringR2LDark(x,
			y, s.generic.name)

def Slider_DoSlide(s: qmenu_h.menuslider_s, dir_: int)->bool: #menuslider_s *, int (returns static qboolean)

	step = s.slidestep if (s.slidestep) else 0.1 #const float
	sign = 1.0

	if not s.cvar:

		return False


	value = cvar.Cvar_VariableValue(s.cvar)

	if s.abs and value < 0: # absolute value treatment

		value = -value
		sign = -1.0


	dir_ = -1 if (dir_ <= 0) else 1

	if ((value == s.minvalue and dir_ == -1) or
		(value == s.maxvalue and dir_ == 1)):

		return False


	value += dir_ * step
	cvar.Cvar_SetValue(s.cvar, ClampCvar(s.minvalue, s.maxvalue, value) * sign)

	if s.generic.callback:

		s.generic.callback(s)


	return True

SLIDER_RANGE	= 10

def Slider_Draw(s: qmenu_h.menuslider_s): #menuslider_s * (static)

	"""
	float scale;
	int x, x_rcol, y;
	int i;
	"""

	scale = cl_screen.SCR_GetMenuScale()
	x = s.generic.parent.x + s.generic.x
	x_rcol = int(x + (qmenu_h.RCOLUMN_OFFSET * scale)) # int x_rcol
	y = s.generic.parent.y + s.generic.y

	if s.generic.name:

		Menu_DrawStringR2LDark(x + (qmenu_h.LCOLUMN_OFFSET * scale),
			y, s.generic.name)


	vid.Draw_CharScaled(x_rcol,
		y * scale, 128, scale)

	i = 0
	while i < SLIDER_RANGE * scale: # for (i = 0; i < SLIDER_RANGE * scale; i++)

		vid.Draw_CharScaled(x_rcol + (i * 8) + 8,
			y * scale, 129, scale)
		i += 1


	vid.Draw_CharScaled(x_rcol + (i * 8) + 8,
		y * scale, 130, scale)

	if s.cvar:

		"""
		float value, range;
		char buffer[5];
		"""

		value = cvar.Cvar_VariableValue(s.cvar)
		if s.abs and value < 0:

			value = -value


		range_ = (ClampCvar(s.minvalue, s.maxvalue, value) - s.minvalue) / \
			(s.maxvalue - s.minvalue)

		vid.Draw_CharScaled(x_rcol + int((SLIDER_RANGE * scale - 1) * 8 * range_) + 8,
			y * scale, 131, scale)

		buffer = (s.printformat if (s.printformat) else "%.1f") % (value,) # Com_sprintf
		buffer = buffer[:4] # sizeof(buffer)
		Menu_DrawString(x_rcol + ((SLIDER_RANGE + 2) * scale * 8),
			y, buffer)

def NumItemNames(items: list)->int: #const char ** (returns static int)

	"""
	const char **i;
	"""

	i = 0
	while items[i]: # for (i = items; *i; i++)
		i += 1


	return i # i - items

def SpinControl_DoSlide(s: qmenu_h.menulist_s, dir_: int)->bool: #menulist_s *, int (returns static qboolean)

	if not s.itemnames or not s.itemnames[0]:

		return False


	if ((s.curvalue < 0) or
		(s.curvalue >= NumItemNames(s.itemnames))):

		s.curvalue = 0

	else:

		dir_ = -1 if (dir_ <= 0) else 1

		if ((s.curvalue == 0 and dir_ == -1) or
			(not s.itemnames[s.curvalue + 1] and dir_ == 1)):

			return False


		s.curvalue += dir_


	if s.generic.callback:

		s.generic.callback(s)


	return True

def GetSelectedItem(s: qmenu_h.menulist_s)->str: #const menulist_s * (returns static const char *)

	if not s.itemnames or not s.itemnames[0]:

		return "(empty)"


	if ((s.curvalue < 0) or
		(s.curvalue >= NumItemNames(s.itemnames))):

		return "(invalid)"


	return s.itemnames[s.curvalue]

def SpinControl_Draw(s: qmenu_h.menulist_s): #menulist_s * (static)

	"""
	const char *item, *nl;
	float scale;
	int x, y;
	"""

	scale = cl_screen.SCR_GetMenuScale()
	x = s.generic.parent.x + s.generic.x
	y = s.generic.parent.y + s.generic.y

	if s.generic.name:

		Menu_DrawStringR2LDark(x + (qmenu_h.LCOLUMN_OFFSET * scale),
			y, s.generic.name)


	item = GetSelectedItem(s)
	nl = item.find('\n') # strchr(item, '\n')

	if nl < 0:

		Menu_DrawString(x + (qmenu_h.RCOLUMN_OFFSET * scale),
			y, item)

	else:

		"""
		char buffer[100];
		"""
		buffer = item[:99]

		if len(item) < 100: # Q_strlcpy(buffer, item, sizeof(buffer)) < sizeof(buffer)

			"""
			char *nlb;
			"""

			# nlb = buffer + (nl - item); *nlb = '\0';
			Menu_DrawString(x + (qmenu_h.RCOLUMN_OFFSET * scale),
				y + 10, buffer[nl + 1:])
			buffer = buffer[:nl]


		Menu_DrawString(x + (qmenu_h.RCOLUMN_OFFSET * scale),
			y, buffer)
