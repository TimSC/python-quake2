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

The header file for the generic part of the menu system

=======================================================================
"""
from __future__ import annotations

from client import cl_main

"""
#ifndef CL_MENU_QMENU_H
#define CL_MENU_QMENU_H

extern const char *menu_in_sound;
extern const char *menu_move_sound;
extern const char *menu_out_sound;
"""

RCOLUMN_OFFSET	= 16
LCOLUMN_OFFSET	= -16

MAXMENUITEMS	= 64

MTYPE_SLIDER		= 0
MTYPE_LIST			= 1
MTYPE_ACTION		= 2
MTYPE_SPINCONTROL	= 3
MTYPE_SEPARATOR		= 4
MTYPE_FIELD			= 5
MTYPE_BITMAP		= 6

QMF_LEFT_JUSTIFY		= 0x00000001
QMF_GRAYED				= 0x00000002
QMF_NUMBERSONLY			= 0x00000004
QMF_HIGHLIGHT_IF_FOCUS	= 0x00000008
QMF_INACTIVE			= 0x00000010

# enum
KEYS_ALL				= 0
KEYS_KEYBOARD_MOUSE		= 1
KEYS_CONTROLLER			= 2
KEYS_CONTROLLER_ALT		= 3

class menuframework_s(object): # struct _tag_menuframework

	def clear(self): # Q2PORT: memset(x, 0, sizeof(*x))

		self.__init__()

	def __init__(self):

		self.x, self.y = 0, 0 #int
		self.cursor = 0 #int

		self.nitems = 0 #int
		self.items = [None] * 64 #void *[64]

		self.banner = None #const char *
		self.statusbar = None #const char *

		self.draw = None #void (*)(struct _tag_menuframework *m)
		self.key = None #const char *(*)(struct _tag_menuframework *m, int k)
		self.close = None #void (*)(struct _tag_menuframework *m)
		self.cursordraw = None #void (*)(struct _tag_menuframework *m)

# Q2PORT: in C every item struct starts with a menucommon_s generic, and the
# menu code casts item pointers to menucommon_s *. Here the item classes are
# subclasses of menucommon_s and their generic is the item itself, so both
# s.generic.x and ((menucommon_s *)item)->x (item.x) work.
class menucommon_s(object):

	def clear(self): # Q2PORT: memset(x, 0, sizeof(*x))

		self.__init__()

	def __init__(self):

		self.generic = self # Q2PORT: see above

		self.type = 0 #int
		self.name = None #const char *
		self.x, self.y = 0, 0 #int
		self.parent = None #menuframework_s *
		self.cursor_offset = 0 #int
		self.localdata = [0, 0, 0, 0] #int[4]
		self.flags = 0 #unsigned

		self.statusbar = None #const char *

		self.callback = None #void (*)(void *self)
		self.statusbarfunc = None #void (*)(void *self)
		self.ownerdraw = None #void (*)(void *self)
		self.cursordraw = None #void (*)(void *self)

class menubitmap_s(menucommon_s):

	def __init__(self):

		super().__init__() #menucommon_s generic
		self.focuspic = None #char *
		self.width = 0 #int
		self.height = 0 #int

class menufield_s(menucommon_s):

	def __init__(self):

		super().__init__() #menucommon_s generic

		self.buffer = "" #char[80]
		self.cursor = 0 #int
		self.length = 0 #int
		self.visible_length = 0 #int

class menuslider_s(menucommon_s):

	def __init__(self):

		super().__init__() #menucommon_s generic

		self.cvar = None #char *
		self.minvalue = 0.0 #float
		self.maxvalue = 0.0 #float
		self.slidestep = 0.0 #float
		self.printformat = None #char *
		self.abs = False #qboolean

class menulist_s(menucommon_s):

	def __init__(self):

		super().__init__() #menucommon_s generic

		self.curvalue = 0 #int

		self.itemnames = None #const char **

class menuaction_s(menucommon_s):

	def __init__(self):

		super().__init__() #menucommon_s generic

class menuseparator_s(menucommon_s):

	def __init__(self):

		super().__init__() #menucommon_s generic

"""
void M_PushMenu(menuframework_s* menu);

void Field_InitState(menufield_s *f, const char *s, int len, int vislen);
void Field_ResetCursor(menuframework_s *m);
qboolean Field_Key(menufield_s *field, int key);

void Menu_AddItem(menuframework_s *menu, void *item);
void Menu_AdjustCursor(menuframework_s *menu, int dir);
void Menu_Center(menuframework_s *menu);
void Menu_Draw(menuframework_s *menu);
void *Menu_ItemAtCursor(menuframework_s *m);
qboolean Menu_SelectItem(menuframework_s *s);
void Menu_SetStatusBar(menuframework_s *s, const char *string);
qboolean Menu_SlideItem(menuframework_s *s, int dir);

void Menu_DrawCharacter(int cx, int cy, int num);
void Menu_DrawString(int, int, const char *);
void Menu_DrawStringDark(int, int, const char *);
void Menu_DrawStringR2L(int, int, const char *);
void Menu_DrawStringR2LDark(int, int, const char *);
"""

class menupopup_s(object):

	def clear(self): # Q2PORT: memset(x, 0, sizeof(*x))

		self.__init__()

	def __init__(self):

		self.string = None #const char *
		self.endtime = 0 #int

"""
void Menu_DrawTextBox(int x, int y, int width, int lines);
void Menu_DrawText(int x, int y, const char *str);
void Menu_DrawPopup(int x, int y, const menupopup_s *pup);
void Menu_StartPopup(menupopup_s *pup, const char *string, int lifetime);
"""

def Menu_PopupActive(pup): #define Menu_PopupActive(pup)

	return (pup.string and (pup.endtime <= 0 or pup.endtime >= cl_main.cls.realtime))

def Menu_ClosePopup(pup): #define Menu_ClosePopup(pup)

	pup.endtime = cl_main.cls.realtime - 1

"""
float ClampCvar(float min, float max, float value);

#endif
"""
