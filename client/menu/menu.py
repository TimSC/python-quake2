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

This file implements the non generic part of the menu system, e.g.
the menu shown to the player. Beware! This code is very fragile and
should only be touched with great care and exessive testing.
Otherwise strange things and hard to track down bugs can occure. In a
better world someone would rewrite this file to something more like
Quake III Team Arena.

=======================================================================
"""
from __future__ import annotations

from client.sound import ogg

import copy
import functools
import math
import numpy as np
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common.shared import rand
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import frame
from backends.unix import system
from backends.unix import network
from client.vid import vid
from client import cl_main
from client import cl_console
from client import cl_input
from client import cl_keyboard
from client import cl_network
from client import cl_screen
from client import cl_view
from client.sound import sound as sound_c
from client.header import client as client_h
from client.header import keyboard as keyboard_h
from client.input import sdl2
from client.input.header import gyro as gyro_h
from client.sound.header import vorbis
from server import sv_main
from client import ref
from client.menu.header import qmenu as qmenu_h
from client.menu import qmenu
from client.menu import videomenu
from client.vid import vid

"""
void M_Menu_Main_f(void);
static void M_Menu_Game_f(void);
static void M_Menu_LoadGame_f(void);
static void M_Menu_SaveGame_f(void);
static void M_Menu_PlayerConfig_f(void);
static void M_Menu_DownloadOptions_f(void);
static void M_Menu_Credits_f(void);
static void M_Menu_Mods_f(void);
static void M_Menu_Multiplayer_f(void);
static void M_Menu_Multiplayer_Keys_f(void);
static void M_Menu_JoinServer_f(void);
static void M_Menu_AddressBook_f(void);
static void M_Menu_StartServer_f(void);
static void M_Menu_DMOptions_f(void);
void M_Menu_Video_f(void);
static void M_Menu_Options_f(void);
static void M_Menu_Keys_f(void);
static void M_Menu_Joy_f(void);
static void M_Menu_ControllerButtons_f(void);
static void M_Menu_ControllerAltButtons_f(void);
static void M_Menu_Quit_f(void);
void M_Menu_Credits(void);
"""

NUM_CURSOR_FRAMES	= 15
MAX_MENU_DEPTH	= 8
m_cursor_width = 0 #static int
menu_startdemoloop = False #qboolean
m_entersound = False #qboolean
m_layers = [None] * MAX_MENU_DEPTH #static menuframework_s *[MAX_MENU_DEPTH]
m_menudepth = 0 #static int
m_popup = qmenu_h.menupopup_s() #static menupopup_s

"""
#include <ctype.h>
#include "../header/client.h"
#include "../input/header/gyro.h"
#include "../sound/header/local.h"
#include "header/qmenu.h"
"""


m_gamepadbind_statusbar = 0 #static static char
cached = 0 #static static qboolean

yes_no_names = ["no", "yes", None] #static static const char
teamplay_names = ["disabled", "by skin", "by model", None] #static static const char
gyro_modes = ["always off", "off, button enables", "on, button disables", "always on", None] #static static const char
gyro_space_choices = ["local", "player", "world", None] #static static const char
gyro_local_roll_choices = ["off", "on", "on, invert", None] #static static const char
onoff_names = ["off", "on", None] #static static const char
yesno_names = ["no", "yes", None] #static static const char
custom_names = ["", "custom", "", None] #static static const char
ogg_shuffle_items = ["default", "play once", "sequential", "random", None] #static static const char
able_items = ["disabled", "enabled", None] #static static const char
sound_items = ["openal", None] #static static const char, Q2PORT: no "sdl", the SDL backend (the C software mixer) isn't ported
crosshair_names = ["none", "cross", "dot", "angle", None] #static static const char
crosshair_color_names = ["white", "red", "green", "blue", "yellow", "cyan", "magenta", "orange", None] #static static const char
stick_layouts = ["default", "southpaw", "legacy", "legacy southpaw", None] #static static const char
stick_layouts_fs = ["default", "southpaw", "legacy", "legacy southpaw", "flick stick", "flick stick spaw", None] #static static const char

def M_GetActiveMenu(): # (returns static menuframework_s *)

	return (m_layers[m_menudepth - 1] if ((m_menudepth > 0) and (m_menudepth < MAX_MENU_DEPTH)) else None)

def M_IsGame(gamename): #const char * (returns static qboolean)

	"""
	cvar_t *game = Cvar_Get("game", "", CVAR_LATCH | CVAR_SERVERINFO);
	"""
	game = cvar.Cvar_Get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)

	if (game.string == gamename) or ((gamename == common_h.BASEDIRNAME) and (game.string == "")):

		return True


	return False

def M_Banner(name): #const char * (static)

	"""
	int w, h;
	float scale;
	"""

	if not name:

		return


	scale = cl_screen.SCR_GetMenuScale()
	w, h = vid.Draw_GetPicSize(name)
	vid.Draw_PicScaled(vid.viddef.width / 2 - (w * scale) / 2, vid.viddef.height / 2 - (110 * scale), name, scale)

def M_ForceMenuOff(): #
	global m_menudepth

	"""
	int i;
	"""

	for i in range(m_menudepth - 1, 0 - 1, -1):

		#menuframework_s *menu = m_layers[i];
		menu = m_layers[i]
		if menu and menu.close:

			menu.close(menu)


	if qmenu_h.Menu_PopupActive(m_popup):

		qmenu_h.Menu_ClosePopup(m_popup)


	m_menudepth = 0
	cl_main.cls.key_dest = client_h.keydest_t.key_game
	cl_keyboard.Key_MarkAllUp()
	cvar.Cvar_Set("paused", "0")

def M_PopMenu(silent): #qboolean (static)
	global m_menudepth

	"""
	menuframework_s *menu;
	"""

	if m_menudepth <= 0:

		M_ForceMenuOff()
		return


	menu = M_GetActiveMenu()
	if menu and menu.close:

		menu.close(menu)


	m_menudepth -= 1
	if silent:

		return


	sound_c.S_StartLocalSound(qmenu.menu_out_sound)
	if not m_menudepth:

		M_ForceMenuOff()
		# play music
		if cvar.Cvar_VariableValue("ogg_pausewithgame") == 1 and ogg.OGG_Status() == vorbis.PAUSE and cl_main.cl.attractloop == False:

			cmdparser.Cbuf_AddText("ogg toggle\n")

"""
 * This crappy function maintaines a stack of opened menus.
 * The steps in this horrible mess are:
 *
 * 1. But the game into pause if a menu is opened
 *
 * 2. If the requested menu is already open, close it.
 *
 * 3. If the requested menu is already open but not
 *    on top, close all menus above it and the menu
 *    itself. This is necessary since an instance of
 *    the reqeuested menu is in flight and will be
 *    displayed.
 *
 * 4. Save the previous menu on top (which was in flight)
 *    to the stack and make the requested menu the menu in
 *    flight.

"""
def M_PushMenu(menu): #menuframework_s*
	global m_menudepth, m_entersound

	"""
	int i;
	int alreadyPresent = 0;
	"""
	alreadyPresent = 0

	if menu == None:

		return


	if (cvar.Cvar_VariableValue("maxclients") == 1) and clientserver.Com_ServerState():

		cvar.Cvar_Set("paused", "1")


	# #ifdef USE_OPENAL
	# #endif
	# pause music
	if cvar.Cvar_VariableValue("ogg_pausewithgame") == 1 and ogg.OGG_Status() == vorbis.PLAY and cl_main.cl.attractloop == False:

		cmdparser.Cbuf_AddText("ogg toggle\n")


	# if this menu is already open (and on top),
	# close it => toggling behaviour
	if M_GetActiveMenu() == menu:

		M_PopMenu(False)
		return


	# if this menu is already present, drop back to
	# that level to avoid stacking menus by hotkeys
	for i in range(m_menudepth):

		if m_layers[i] == menu:

			alreadyPresent = 1
			break


	# menu was already opened further down the stack
	while alreadyPresent and i <= m_menudepth:

		M_PopMenu(False)


	if m_menudepth >= MAX_MENU_DEPTH:

		clientserver.Com_Printf("Too many open menus!\n")
		return


	m_layers[m_menudepth] = menu
	m_menudepth += 1
	m_entersound = True
	cl_main.cls.key_dest = client_h.keydest_t.key_menu

"""
extern qboolean japanese_confirm;
"""

def Key_GetMenuKey(key: int)->int: #int (returns int)

	# Q2PORT: the C switch falls through from each keypad case to the arrow key
	# below it unless the numpad is on; here those cases test it in their condition
	K = keyboard_h
	if (key == K.K_KP_UPARROW and not (sdl2.IN_NumpadIsOn() == True)) or key in (K.K_UPARROW, K.K_DPAD_UP):

		return K.K_UPARROW

	if (key == K.K_KP_DOWNARROW and not (sdl2.IN_NumpadIsOn() == True)) or key in (K.K_TAB, K.K_DOWNARROW, K.K_DPAD_DOWN):

		# case K_TAB: case K_KP_DOWNARROW: if (IN_NumpadIsOn() == true) { break; }
		if key == K.K_TAB and sdl2.IN_NumpadIsOn() == True:
			return key
		return K.K_DOWNARROW

	if (key == K.K_KP_LEFTARROW and not (sdl2.IN_NumpadIsOn() == True)) or key in (K.K_LEFTARROW, K.K_DPAD_LEFT, K.K_SHOULDER_LEFT):

		return K.K_LEFTARROW

	if (key == K.K_KP_RIGHTARROW and not (sdl2.IN_NumpadIsOn() == True)) or key in (K.K_RIGHTARROW, K.K_DPAD_RIGHT, K.K_SHOULDER_RIGHT):

		return K.K_RIGHTARROW

	if key in (K.K_MOUSE1, K.K_MOUSE2, K.K_MOUSE3, K.K_MOUSE4, K.K_MOUSE5, K.K_KP_ENTER, K.K_ENTER):

		return K.K_ENTER

	if (key == K.K_KP_DEL and not (sdl2.IN_NumpadIsOn() == True)) or key == K.K_DEL:

		return K.K_DEL

	if key in (K.K_BACKSPACE, K.K_BTN_NORTH):

		return K.K_BACKSPACE

	if (key == K.K_KP_INS and not (sdl2.IN_NumpadIsOn() == True)) or key == K.K_INS:

		return K.K_INS

	if key == K.K_BTN_SOUTH:

		if sdl2.japanese_confirm: return K.K_ESCAPE
		else: return K.K_ENTER

	if key == K.K_BTN_EAST:

		if sdl2.japanese_confirm: return K.K_ENTER
		else: return K.K_ESCAPE


	return key


def Default_MenuKey(m, key): #menuframework_s *, int (returns const char *)

	"""
	const char *sound;
	menucommon_s *item;
	int menu_key;
	"""

	if qmenu_h.Menu_PopupActive(m_popup):

		qmenu_h.Menu_ClosePopup(m_popup)
		return None


	menu_key = Key_GetMenuKey(key)
	item = qmenu.Menu_ItemAtCursor(m)
	if item and item.type == qmenu_h.MTYPE_FIELD:

		if qmenu.Field_Key(item, key):

			return None


	sound = None
	if menu_key == keyboard_h.K_ESCAPE:

		qmenu.Field_ResetCursor(m)
		M_PopMenu(False)

	elif menu_key == keyboard_h.K_UPARROW:

		qmenu.Field_ResetCursor(m)
		m.cursor -= 1
		qmenu.Menu_AdjustCursor(m, -1)
		sound = qmenu.menu_move_sound

	elif menu_key == keyboard_h.K_DOWNARROW:

		qmenu.Field_ResetCursor(m)
		m.cursor += 1
		qmenu.Menu_AdjustCursor(m, 1)
		sound = qmenu.menu_move_sound

	elif menu_key == keyboard_h.K_LEFTARROW:

		if qmenu.Menu_SlideItem(m, -1):

			sound = qmenu.menu_move_sound


	elif menu_key == keyboard_h.K_RIGHTARROW:

		if qmenu.Menu_SlideItem(m, 1):

			sound = qmenu.menu_move_sound


	elif menu_key == keyboard_h.K_ENTER:

		if qmenu.Menu_SelectItem(m):

			sound = qmenu.menu_move_sound


	return sound

def Default_MenuDraw(m): #menuframework_s *

	M_Banner(m.banner)
	qmenu.Menu_Draw(m)
	qmenu.Menu_DrawPopup(320, 240, m_popup)

"""
 Unsused, left for backward compability
"""
def M_DrawPic(x, y, pic): #int, int, char *

	"""
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	vid.Draw_PicScaled((x + ((vid.viddef.width - 320) >> 1)) * scale, (y + ((vid.viddef.height - 240) >> 1)) * scale, pic, scale)

"""
 * Draws an animating cursor with the point at
 * x,y. The pic will extend to the left of x,
 * and both above and below y.

"""
def M_DrawCursor(x, y, f): #int, int, int (static)
	global cached

	"""
	char cursorname[80];
	static qboolean cached;
	float scale = SCR_GetMenuScale();
	"""
	cursorname = [None] * 80
	scale = cl_screen.SCR_GetMenuScale()

	if not cached:

		#int i;
		for i in range(NUM_CURSOR_FRAMES):

			cursorname = "m_cursor%d" % (i,) # Com_sprintf
			vid.Draw_FindPic(cursorname)


		cached = True


	cursorname = "m_cursor%d" % (f,) # Com_sprintf
	vid.Draw_PicScaled(x * scale, y * scale, cursorname, scale)

def M_DrawTextBox(x, y, width, lines): #int, int, int, int (static)

	"""
	int cx, cy;
	int n;
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	# draw left side
	cx = x
	cy = y
	qmenu.Menu_DrawCharacter(cx * scale, cy * scale, 1)
	for n in range(lines):

		cy += 8
		qmenu.Menu_DrawCharacter(cx * scale, cy * scale, 4)


	qmenu.Menu_DrawCharacter(cx * scale, cy * scale + 8 * scale, 7)
	# draw middle
	cx += 8
	while width > 0:

		cy = y
		qmenu.Menu_DrawCharacter(cx * scale, cy * scale, 2)
		for n in range(lines):

			cy += 8
			qmenu.Menu_DrawCharacter(cx * scale, cy * scale, 5)


		qmenu.Menu_DrawCharacter(cx * scale, cy *scale + 8 * scale, 8)
		width -= 1
		cx += 8


	# draw right side
	cy = y
	qmenu.Menu_DrawCharacter(cx * scale, cy * scale, 3)
	for n in range(lines):

		cy += 8
		qmenu.Menu_DrawCharacter(cx * scale, cy * scale, 6)


	qmenu.Menu_DrawCharacter(cx * scale, cy * scale + 8 * scale, 9)

s_main = qmenu_h.menuframework_s() #static menuframework_s
s_plaque = qmenu_h.menubitmap_s() #static menubitmap_s
s_logo = qmenu_h.menubitmap_s() #static menubitmap_s
s_game = qmenu_h.menubitmap_s() #static menubitmap_s
s_multiplayer = qmenu_h.menubitmap_s() #static menubitmap_s
s_options = qmenu_h.menubitmap_s() #static menubitmap_s
s_video = qmenu_h.menubitmap_s() #static menubitmap_s
s_quit = qmenu_h.menubitmap_s() #static menubitmap_s

def GameFunc(unused): #void * (static)

	M_Menu_Game_f()

def MultiplayerFunc(unused): #void * (static)

	M_Menu_Multiplayer_f()

def OptionsFunc(unused): #void * (static)

	M_Menu_Options_f()

def VideoFunc(unused): #void * (static)

	videomenu.M_Menu_Video_f()

def QuitFunc(unused): #void * (static)

	M_Menu_Quit_f()

def InitMainMenu(): # (static)

	"""
	float scale = SCR_GetMenuScale();
	int i = 0;
	int x = 0;
	int y = 0;
	int w = 0;
	int h = 0;
	int widest = -1;
	char * names[] = { "m_main_game", "m_main_multiplayer", "m_main_options", "m_main_video", "m_main_quit", NULL };
	int tmp = s_main.cursor;
	"""
	scale = cl_screen.SCR_GetMenuScale()
	i = 0
	x = 0
	y = 0
	w = 0
	h = 0
	widest = -1
	names = ["m_main_game", "m_main_multiplayer", "m_main_options", "m_main_video", "m_main_quit", None]
	tmp = s_main.cursor

	i = 0
	while names[i]: # names[i] != 0

		w, h = vid.Draw_GetPicSize(names[i])
		if w > widest:

			widest = w


		i += 1


	x = int((vid.viddef.width / scale - widest + 70) / 2) # C int
	y = int((vid.viddef.height / (2 * scale) - 110)) # C int
	s_main.clear() # memset(&s_main, 0, sizeof( menuframework_s ))
	s_main.cursor = tmp
	w, h = vid.Draw_GetPicSize("m_main_plaque")
	s_plaque.generic.type = qmenu_h.MTYPE_BITMAP
	s_plaque.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_INACTIVE
	s_plaque.generic.x = (x - (m_cursor_width + 5) - w)
	s_plaque.generic.y = y
	s_plaque.generic.name = "m_main_plaque"
	s_plaque.generic.callback = None
	s_plaque.focuspic = 0
	s_logo.generic.type = qmenu_h.MTYPE_BITMAP
	s_logo.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_INACTIVE
	s_logo.generic.x = (x - (m_cursor_width + 5) - w)
	s_logo.generic.y = y + h + 5
	s_logo.generic.name = "m_main_logo"
	s_logo.generic.callback = None
	s_logo.focuspic = 0
	y += 10
	s_game.generic.type = qmenu_h.MTYPE_BITMAP
	s_game.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_HIGHLIGHT_IF_FOCUS
	s_game.generic.x = x
	s_game.generic.y = y
	s_game.generic.name = "m_main_game"
	s_game.generic.callback = GameFunc
	s_game.focuspic = "m_main_game_sel"
	w, h = vid.Draw_GetPicSize(s_game.generic.name)
	y += h + 8
	s_multiplayer.generic.type = qmenu_h.MTYPE_BITMAP
	s_multiplayer.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_HIGHLIGHT_IF_FOCUS
	s_multiplayer.generic.x = x
	s_multiplayer.generic.y = y
	s_multiplayer.generic.name = "m_main_multiplayer"
	s_multiplayer.generic.callback = MultiplayerFunc
	s_multiplayer.focuspic = "m_main_multiplayer_sel"
	w, h = vid.Draw_GetPicSize(s_multiplayer.generic.name)
	y += h + 8
	s_options.generic.type = qmenu_h.MTYPE_BITMAP
	s_options.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_HIGHLIGHT_IF_FOCUS
	s_options.generic.x = x
	s_options.generic.y = y
	s_options.generic.name = "m_main_options"
	s_options.generic.callback = OptionsFunc
	s_options.focuspic = "m_main_options_sel"
	w, h = vid.Draw_GetPicSize(s_options.generic.name)
	y += h + 8
	s_video.generic.type = qmenu_h.MTYPE_BITMAP
	s_video.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_HIGHLIGHT_IF_FOCUS
	s_video.generic.x = x
	s_video.generic.y = y
	s_video.generic.name = "m_main_video"
	s_video.generic.callback = VideoFunc
	s_video.focuspic = "m_main_video_sel"
	w, h = vid.Draw_GetPicSize(s_video.generic.name)
	y += h + 8
	s_quit.generic.type = qmenu_h.MTYPE_BITMAP
	s_quit.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY | qmenu_h.QMF_HIGHLIGHT_IF_FOCUS
	s_quit.generic.x = x
	s_quit.generic.y = y
	s_quit.generic.name = "m_main_quit"
	s_quit.generic.callback = QuitFunc
	s_quit.focuspic = "m_main_quit_sel"
	qmenu.Menu_AddItem(s_main, s_plaque)
	qmenu.Menu_AddItem(s_main, s_logo)
	qmenu.Menu_AddItem(s_main, s_game)
	qmenu.Menu_AddItem(s_main, s_multiplayer)
	qmenu.Menu_AddItem(s_main, s_options)
	qmenu.Menu_AddItem(s_main, s_video)
	qmenu.Menu_AddItem(s_main, s_quit)
	qmenu.Menu_Center(s_main)

def M_Main_Draw(m): #menuframework_s * (static)

	"""
	const menucommon_s *item;
	"""

	qmenu.Menu_Draw(m)
	item = qmenu.Menu_ItemAtCursor(m)
	if item:

		M_DrawCursor(item.x - m_cursor_width, item.y, (cl_main.cls.realtime / 100) % NUM_CURSOR_FRAMES)

def M_Menu_Main_f(): #

	InitMainMenu()
	s_main.draw = M_Main_Draw
	s_main.key = Default_MenuKey
	qmenu.Menu_AdjustCursor(s_main, 1)
	M_PushMenu(s_main)

s_multiplayer_menu = qmenu_h.menuframework_s() #static menuframework_s
s_join_network_server_action = qmenu_h.menuaction_s() #static menuaction_s
s_start_network_server_action = qmenu_h.menuaction_s() #static menuaction_s
s_player_setup_action = qmenu_h.menuaction_s() #static menuaction_s
s_customize_options_action = qmenu_h.menuaction_s() #static menuaction_s

def PlayerSetupFunc(unused): #void * (static)

	M_Menu_PlayerConfig_f()

def MultplayerCustomizeControlsFunc(unused): #void * (static)

	M_Menu_Multiplayer_Keys_f()

def JoinNetworkServerFunc(unused): #void * (static)

	M_Menu_JoinServer_f()

def StartNetworkServerFunc(unused): #void * (static)

	M_Menu_StartServer_f()

def Multiplayer_MenuInit(): # (static)

	"""
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	s_multiplayer_menu.x = int(int(vid.viddef.width * 0.50) - 64 * scale) # int x
	s_multiplayer_menu.nitems = 0
	s_multiplayer_menu.banner = "m_banner_multiplayer"
	s_join_network_server_action.generic.type = qmenu_h.MTYPE_ACTION
	s_join_network_server_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_join_network_server_action.generic.x = 0
	s_join_network_server_action.generic.y = 0
	s_join_network_server_action.generic.name = " join network server"
	s_join_network_server_action.generic.callback = JoinNetworkServerFunc
	s_start_network_server_action.generic.type = qmenu_h.MTYPE_ACTION
	s_start_network_server_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_start_network_server_action.generic.x = 0
	s_start_network_server_action.generic.y = 10
	s_start_network_server_action.generic.name = " start network server"
	s_start_network_server_action.generic.callback = StartNetworkServerFunc
	s_player_setup_action.generic.type = qmenu_h.MTYPE_ACTION
	s_player_setup_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_player_setup_action.generic.x = 0
	s_player_setup_action.generic.y = 20
	s_player_setup_action.generic.name = " player setup"
	s_player_setup_action.generic.callback = PlayerSetupFunc
	s_customize_options_action.generic.type = qmenu_h.MTYPE_ACTION
	s_customize_options_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_customize_options_action.generic.x = 0
	s_customize_options_action.generic.y = 30
	s_customize_options_action.generic.name = " customize controls"
	s_customize_options_action.generic.callback = MultplayerCustomizeControlsFunc
	qmenu.Menu_AddItem(s_multiplayer_menu, s_join_network_server_action)
	qmenu.Menu_AddItem(s_multiplayer_menu, s_start_network_server_action)
	qmenu.Menu_AddItem(s_multiplayer_menu, s_player_setup_action)
	qmenu.Menu_AddItem(s_multiplayer_menu, s_customize_options_action)
	qmenu.Menu_SetStatusBar(s_multiplayer_menu, None)
	qmenu.Menu_Center(s_multiplayer_menu)

def M_Menu_Multiplayer_f(): # (static)

	Multiplayer_MenuInit()
	s_multiplayer_menu.draw = Default_MenuDraw
	s_multiplayer_menu.key = Default_MenuKey
	M_PushMenu(s_multiplayer_menu)

bindnames = [["+attack", "attack"], ["weapnext", "next weapon"], ["weapprev", "previous weapon"], ["+forward", "walk forward"], ["+back", "backpedal"], ["+left", "turn left"], ["+right", "turn right"], ["+speed", "run"], ["+moveleft", "step left"], ["+moveright", "step right"], ["+strafe", "sidestep"], ["+lookup", "look up"], ["+lookdown", "look down"], ["centerview", "center view"], ["+mlook", "mouse look"], ["+klook", "keyboard look"], ["+moveup", "up / jump"], ["+movedown", "down / crouch"], ["inven", "inventory"], ["invuse", "use item"], ["invdrop", "drop item"], ["invprev", "prev item"], ["invnext", "next item"], ["cmd help", "help computer"]] #char *[][2]
keys_cursor = 0 #int
menukeyitem_bind = 0 #static int
s_keys_menu = qmenu_h.menuframework_s() #static menuframework_s
s_joy_menu = qmenu_h.menuframework_s() #static menuframework_s
s_keys_actions = [qmenu_h.menuaction_s() for i in range(len(bindnames))] #static menuaction_s[ARRLEN(bindnames)]

def M_UnbindCommand(command, scope): #char *, int (static)

	"""
	int j;
	int begin = 0, end = K_LAST;
	"""
	begin = 0
	end = keyboard_h.K_LAST

	if scope == qmenu_h.KEYS_KEYBOARD_MOUSE:

		end = keyboard_h.K_JOY_FIRST_BTN

	elif scope == qmenu_h.KEYS_CONTROLLER:

		begin = keyboard_h.K_JOY_FIRST_BTN
		end = keyboard_h.K_JOY_FIRST_BTN_ALT

	elif scope == qmenu_h.KEYS_CONTROLLER_ALT:

		begin = keyboard_h.K_JOY_FIRST_BTN_ALT


	for j in range(begin, end):

		#const char *b;
		b = cl_keyboard.keybindings[j]
		if not b:

			continue


		if (b == command):

			cl_keyboard.Key_SetBinding(j, "")

def M_FindKeysForCommand(command, twokeys, scope): #char *, int *, int (static)

	"""
	int count;
	int j;
	int begin = 0, end = K_LAST;
	"""
	begin = 0
	end = keyboard_h.K_LAST

	if scope == qmenu_h.KEYS_KEYBOARD_MOUSE:

		end = keyboard_h.K_JOY_FIRST_BTN

	elif scope == qmenu_h.KEYS_CONTROLLER:

		begin = keyboard_h.K_JOY_FIRST_BTN
		end = keyboard_h.K_JOY_FIRST_BTN_ALT

	elif scope == qmenu_h.KEYS_CONTROLLER_ALT:

		begin = keyboard_h.K_JOY_FIRST_BTN_ALT


	twokeys[0] = twokeys[1] = -1
	count = 0
	for j in range(begin, end):

		#const char *b;
		b = cl_keyboard.keybindings[j]
		if not b:

			continue


		if (b == command):

			twokeys[count] = j
			count += 1
			if count == 2:

				break

def KeyCursorDrawFunc(menu): #menuframework_s * (static)

	"""
	float scale;
	int c;
	"""

	if not qmenu.Menu_ItemAtCursor(menu):

		return


	if menukeyitem_bind:

		c = ' = '

	else:

		c = int(12 + (int(system.Sys_Milliseconds() / 250) & 1)) # C int


	scale = cl_screen.SCR_GetMenuScale()
	vid.Draw_CharScaled(menu.x, (menu.y + menu.cursor * 9) * scale, c, scale)

def DrawKeyBindingFunc(self): #void * (static)

	"""
	int keys[2];
	menuaction_s *a = (menuaction_s *)self;
	float scale = SCR_GetMenuScale();
	"""
	keys = [0] * 2
	a = self
	scale = cl_screen.SCR_GetMenuScale()

	M_FindKeysForCommand(bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_KEYBOARD_MOUSE)
	if keys[0] == -1:

		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, "???")

	else:

		#int x;
		#const char *name;
		name = cl_keyboard.Key_KeynumToString(keys[0])
		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, name)
		x = len(name) * 8
		if keys[1] != -1:

			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 24 * scale + (x * scale), a.generic.y + a.generic.parent.y, "or")
			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 48 * scale + (x * scale), a.generic.y + a.generic.parent.y, cl_keyboard.Key_KeynumToString(keys[1]))

def KeyBindingFunc(self): #void * (static)
	global menukeyitem_bind

	"""
	menuaction_s *a = (menuaction_s *)self;
	int keys[2];
	"""
	a = self
	keys = [0] * 2

	M_FindKeysForCommand(bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_KEYBOARD_MOUSE)
	if keys[1] != -1:

		M_UnbindCommand(bindnames[a.generic.localdata[0]][0], qmenu_h.KEYS_KEYBOARD_MOUSE)


	menukeyitem_bind = True
	qmenu.Menu_SetStatusBar(s_keys_menu, "press a key or button for this action")

def Keys_MenuInit(): # (static)

	"""
	int i;
	"""

	s_keys_menu.x = int(vid.viddef.width * 0.50)
	s_keys_menu.nitems = 0
	s_keys_menu.cursordraw = KeyCursorDrawFunc
	for i in range(len(bindnames)):

		s_keys_actions[i].generic.type = qmenu_h.MTYPE_ACTION
		s_keys_actions[i].generic.flags = qmenu_h.QMF_GRAYED
		s_keys_actions[i].generic.x = 0
		s_keys_actions[i].generic.y = (i * 9)
		s_keys_actions[i].generic.ownerdraw = DrawKeyBindingFunc
		s_keys_actions[i].generic.localdata[0] = i
		s_keys_actions[i].generic.name = bindnames[s_keys_actions[i].generic.localdata[0]][1]
		qmenu.Menu_AddItem(s_keys_menu, s_keys_actions[i])


	qmenu.Menu_SetStatusBar(s_keys_menu, "ENTER to change, BACKSPACE to clear")
	qmenu.Menu_Center(s_keys_menu)

def Keys_MenuKey(m, key): #menuframework_s *, int (returns static const char *)
	global menukeyitem_bind

	"""
	menuaction_s *item = (menuaction_s *)Menu_ItemAtCursor(m);
	"""
	item = qmenu.Menu_ItemAtCursor(m)

	if menukeyitem_bind:

		# Any key/button except from the game controller and escape keys
		if (key != keyboard_h.K_ESCAPE) and (key != 96) and (key < keyboard_h.K_JOY_FIRST_BTN):

			#char cmd[1024];
			cmd = [None] * 1024
			cmd = "bind \"%s\" \"%s\"\n" % (cl_keyboard.Key_KeynumToString(key), bindnames[item.generic.localdata[0]][0],) # Com_sprintf
			cmdparser.Cbuf_InsertText(cmd)


		qmenu.Menu_SetStatusBar(m, "ENTER to change, BACKSPACE to clear")
		menukeyitem_bind = False
		return qmenu.menu_out_sound


	key = Key_GetMenuKey(key)
	if key == keyboard_h.K_ENTER:

		KeyBindingFunc(item)
		return qmenu.menu_in_sound

	elif key == keyboard_h.K_DEL or key == keyboard_h.K_BACKSPACE:

		# delete bindings
		M_UnbindCommand(bindnames[item.generic.localdata[0]][0], qmenu_h.KEYS_KEYBOARD_MOUSE)
		return qmenu.menu_out_sound

	else:

		return Default_MenuKey(m, key)

def M_Menu_Keys_f(): # (static)

	Keys_MenuInit()
	s_keys_menu.draw = Default_MenuDraw
	s_keys_menu.key = Keys_MenuKey
	M_PushMenu(s_keys_menu)

multiplayer_key_bindnames = [["score", "score"], ["messagemode", "chat"], ["messagemode2", "team chat"], ["wave 1", "wave 1"], ["wave 2", "wave 2"], ["wave 3", "wave 3"], ["wave 4", "wave 4"]] #char *[][2]
s_multiplayer_keys_menu = qmenu_h.menuframework_s() #static menuframework_s
s_multiplayer_keys_actions = [qmenu_h.menuaction_s() for i in range(len(multiplayer_key_bindnames))] #static menuaction_s[ARRLEN(multiplayer_key_bindnames)]

def MultiplayerDrawKeyBindingFunc(self): #void * (static)

	"""
	int keys[2];
	menuaction_s *a = (menuaction_s *)self;
	float scale = SCR_GetMenuScale();
	"""
	keys = [0] * 2
	a = self
	scale = cl_screen.SCR_GetMenuScale()

	M_FindKeysForCommand(multiplayer_key_bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_ALL)
	if keys[0] == -1:

		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, "???")

	else:

		#int x;
		#const char *name;
		name = cl_keyboard.Key_KeynumToString(keys[0])
		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, name)
		x = len(name) * 8
		if keys[1] != -1:

			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 24 * scale + (x * scale), a.generic.y + a.generic.parent.y, "or")
			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 48 * scale + (x * scale), a.generic.y + a.generic.parent.y, cl_keyboard.Key_KeynumToString(keys[1]))

def MultiplayerKeyBindingFunc(self): #void * (static)
	global menukeyitem_bind

	"""
	menuaction_s *a = (menuaction_s *)self;
	int keys[2];
	"""
	a = self
	keys = [0] * 2

	M_FindKeysForCommand(multiplayer_key_bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_ALL)
	if keys[1] != -1:

		M_UnbindCommand(multiplayer_key_bindnames[a.generic.localdata[0]][0], qmenu_h.KEYS_ALL)


	menukeyitem_bind = True
	qmenu.Menu_SetStatusBar(s_multiplayer_keys_menu, "press a key or button for this action")

def MultiplayerKeys_MenuInit(): # (static)

	"""
	int i;
	"""

	s_multiplayer_keys_menu.x = int(vid.viddef.width * 0.50)
	s_multiplayer_keys_menu.nitems = 0
	s_multiplayer_keys_menu.cursordraw = KeyCursorDrawFunc
	for i in range(len(multiplayer_key_bindnames)):

		s_multiplayer_keys_actions[i].generic.type = qmenu_h.MTYPE_ACTION
		s_multiplayer_keys_actions[i].generic.flags = qmenu_h.QMF_GRAYED
		s_multiplayer_keys_actions[i].generic.x = 0
		s_multiplayer_keys_actions[i].generic.y = (i * 9)
		s_multiplayer_keys_actions[i].generic.ownerdraw = MultiplayerDrawKeyBindingFunc
		s_multiplayer_keys_actions[i].generic.localdata[0] = i
		s_multiplayer_keys_actions[i].generic.name = multiplayer_key_bindnames[s_multiplayer_keys_actions[i].generic.localdata[0]][1]
		qmenu.Menu_AddItem(s_multiplayer_keys_menu, s_multiplayer_keys_actions[i])


	qmenu.Menu_SetStatusBar(s_multiplayer_keys_menu, "ENTER to change, BACKSPACE to clear")
	qmenu.Menu_Center(s_multiplayer_keys_menu)

def MultiplayerKeys_MenuKey(m, key): #menuframework_s *, int (returns static const char *)
	global menukeyitem_bind

	"""
	menuaction_s *item = (menuaction_s *)Menu_ItemAtCursor(m);
	"""
	item = qmenu.Menu_ItemAtCursor(m)

	if menukeyitem_bind:

		# Any key/button but the escape ones
		if (key != keyboard_h.K_ESCAPE) and (key != 96):

			#char cmd[1024];
			cmd = [None] * 1024
			cmd = "bind \"%s\" \"%s\"\n" % (cl_keyboard.Key_KeynumToString(key), multiplayer_key_bindnames[item.generic.localdata[0]][0],) # Com_sprintf
			cmdparser.Cbuf_InsertText(cmd)


		qmenu.Menu_SetStatusBar(m, "ENTER to change, BACKSPACE to clear")
		menukeyitem_bind = False
		return qmenu.menu_out_sound


	key = Key_GetMenuKey(key)
	if key == keyboard_h.K_ENTER:

		MultiplayerKeyBindingFunc(item)
		return qmenu.menu_in_sound

	elif key == keyboard_h.K_DEL or key == keyboard_h.K_BACKSPACE:

		# delete bindings
		M_UnbindCommand(multiplayer_key_bindnames[item.generic.localdata[0]][0], qmenu_h.KEYS_ALL)
		return qmenu.menu_out_sound

	else:

		return Default_MenuKey(m, key)

def M_Menu_Multiplayer_Keys_f(): # (static)

	MultiplayerKeys_MenuInit()
	s_multiplayer_keys_menu.draw = Default_MenuDraw
	s_multiplayer_keys_menu.key = MultiplayerKeys_MenuKey
	M_PushMenu(s_multiplayer_keys_menu)

def GamepadMenu_StatusPrompt(m): #menuframework_s * (static)

	global m_gamepadbind_statusbar

	"""
	static char m_gamepadbind_statusbar[64];
	int btn_confirm, btn_cancel;
	"""

	if sdl2.japanese_confirm:

		btn_confirm = keyboard_h.K_BTN_EAST
		btn_cancel = keyboard_h.K_BTN_SOUTH

	else:

		btn_confirm = keyboard_h.K_BTN_SOUTH
		btn_cancel = keyboard_h.K_BTN_EAST


	m_gamepadbind_statusbar = ("%s assigns, %s clears, %s exits" % (cl_keyboard.Key_KeynumToString_Joy(btn_confirm), cl_keyboard.Key_KeynumToString_Joy(keyboard_h.K_BTN_NORTH), cl_keyboard.Key_KeynumToString_Joy(btn_cancel),))[:64 - 1] # snprintf
	qmenu.Menu_SetStatusBar(m, m_gamepadbind_statusbar)

controller_bindnames = [["+attack", "attack"], ["+moveup", "up / jump"], ["+movedown", "down / crouch"], ["weapnext", "next weapon"], ["weapprev", "previous weapon"], ["cycleweap weapon_plasmabeam weapon_boomer weapon_chaingun weapon_etf_rifle weapon_machinegun weapon_blaster", "long range: quickswitch 1"], ["cycleweap weapon_supershotgun weapon_shotgun weapon_chainfist", "close range: quickswitch 2"], ["cycleweap weapon_phalanx weapon_rocketlauncher weapon_proxlauncher weapon_grenadelauncher ammo_grenades", "explosives: quickswitch 3"], ["cycleweap weapon_bfg weapon_disintegrator weapon_railgun weapon_hyperblaster ammo_tesla ammo_trap", "special: quickswitch 4"], ["prefweap weapon_railgun weapon_plasmabeam weapon_boomer weapon_hyperblaster weapon_chaingun weapon_supershotgun weapon_etf_rifle weapon_machinegun weapon_shotgun weapon_blaster", "best safe weapon"], ["prefweap weapon_bfg weapon_disintegrator weapon_phalanx weapon_railgun weapon_rocketlauncher weapon_plasmabeam weapon_boomer weapon_hyperblaster weapon_grenadelauncher weapon_chaingun weapon_proxlauncher ammo_grenades weapon_supershotgun", "best unsafe weapon"], ["centerview", "center view"], ["inven", "inventory"], ["invuse", "use item"], ["invdrop", "drop item"], ["invprev", "prev item"], ["invnext", "next item"], ["cmd help", "help computer"], ["+gyroaction", "gyro off / on"], ["+joyaltselector", "alt buttons modifier"]] #char *[][2]
s_controller_buttons_menu = qmenu_h.menuframework_s() #static menuframework_s
s_controller_buttons_actions = [qmenu_h.menuaction_s() for i in range(len(controller_bindnames))] #static menuaction_s[ARRLEN(controller_bindnames)]

def DrawControllerButtonBindingFunc(self): #void * (static)

	"""
	int keys[2];
	menuaction_s *a = (menuaction_s *)self;
	float scale = SCR_GetMenuScale();
	"""
	keys = [0] * 2
	a = self
	scale = cl_screen.SCR_GetMenuScale()

	M_FindKeysForCommand(controller_bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_CONTROLLER)
	if keys[0] == -1:

		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, "???")

	else:

		#int x;
		#const char *name;
		name = cl_keyboard.Key_KeynumToString_Joy(keys[0])
		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, name)
		x = len(name) * 8
		if keys[1] != -1:

			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 24 * scale + (x * scale), a.generic.y + a.generic.parent.y, "or")
			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 48 * scale + (x * scale), a.generic.y + a.generic.parent.y, cl_keyboard.Key_KeynumToString_Joy(keys[1]))

def ControllerButtonBindingFunc(self): #void * (static)
	global menukeyitem_bind

	"""
	menuaction_s *a = (menuaction_s *)self;
	int keys[2];
	"""
	a = self
	keys = [0] * 2

	M_FindKeysForCommand(controller_bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_CONTROLLER)
	if keys[1] != -1:

		M_UnbindCommand(controller_bindnames[a.generic.localdata[0]][0], qmenu_h.KEYS_CONTROLLER)


	menukeyitem_bind = True
	qmenu.Menu_SetStatusBar(s_controller_buttons_menu, "press a button for this action")

def ControllerButtons_MenuInit(): # (static)

	"""
	int i;
	"""

	s_controller_buttons_menu.x = int(vid.viddef.width * 0.50)
	s_controller_buttons_menu.nitems = 0
	s_controller_buttons_menu.cursordraw = KeyCursorDrawFunc
	for i in range(len(controller_bindnames)):

		s_controller_buttons_actions[i].generic.type = qmenu_h.MTYPE_ACTION
		s_controller_buttons_actions[i].generic.flags = qmenu_h.QMF_GRAYED
		s_controller_buttons_actions[i].generic.x = 0
		s_controller_buttons_actions[i].generic.y = (i * 9)
		s_controller_buttons_actions[i].generic.ownerdraw = DrawControllerButtonBindingFunc
		s_controller_buttons_actions[i].generic.localdata[0] = i
		s_controller_buttons_actions[i].generic.name = controller_bindnames[s_controller_buttons_actions[i].generic.localdata[0]][1]
		qmenu.Menu_AddItem(s_controller_buttons_menu, s_controller_buttons_actions[i])


	GamepadMenu_StatusPrompt(s_controller_buttons_menu)
	qmenu.Menu_Center(s_controller_buttons_menu)

def ControllerButtons_MenuKey(m, key): #menuframework_s *, int (returns static const char *)
	global menukeyitem_bind

	"""
	menuaction_s *item = (menuaction_s *)Menu_ItemAtCursor(m);
	"""
	item = qmenu.Menu_ItemAtCursor(m)

	if menukeyitem_bind:

		# Only controller buttons allowed
		if key >= keyboard_h.K_JOY_FIRST_BTN:

			#char cmd[1024];
			cmd = [None] * 1024
			cmd = "bind \"%s\" \"%s\"\n" % (cl_keyboard.Key_KeynumToString(key), controller_bindnames[item.generic.localdata[0]][0],) # Com_sprintf
			cmdparser.Cbuf_InsertText(cmd)


		GamepadMenu_StatusPrompt(m)
		menukeyitem_bind = False
		return qmenu.menu_out_sound


	key = Key_GetMenuKey(key)
	if key == keyboard_h.K_ENTER:

		ControllerButtonBindingFunc(item)
		return qmenu.menu_in_sound

	elif key == keyboard_h.K_DEL or key == keyboard_h.K_BACKSPACE:

		M_UnbindCommand(controller_bindnames[item.generic.localdata[0]][0], qmenu_h.KEYS_CONTROLLER)
		return qmenu.menu_out_sound

	else:

		return Default_MenuKey(m, key)

def M_Menu_ControllerButtons_f(): # (static)

	ControllerButtons_MenuInit()
	s_controller_buttons_menu.draw = Default_MenuDraw
	s_controller_buttons_menu.key = ControllerButtons_MenuKey
	M_PushMenu(s_controller_buttons_menu)

controller_alt_bindnames = [["weapnext", "next weapon"], ["weapprev", "previous weapon"], ["cycleweap weapon_plasmabeam weapon_boomer weapon_chaingun weapon_etf_rifle weapon_machinegun weapon_blaster", "long range: quickswitch 1"], ["cycleweap weapon_supershotgun weapon_shotgun weapon_chainfist", "close range: quickswitch 2"], ["cycleweap weapon_phalanx weapon_rocketlauncher weapon_proxlauncher weapon_grenadelauncher ammo_grenades", "explosives: quickswitch 3"], ["cycleweap weapon_bfg weapon_disintegrator weapon_railgun weapon_hyperblaster ammo_tesla ammo_trap", "special: quickswitch 4"], ["prefweap weapon_railgun weapon_plasmabeam weapon_boomer weapon_hyperblaster weapon_chaingun weapon_supershotgun weapon_etf_rifle weapon_machinegun weapon_shotgun weapon_blaster", "best safe weapon"], ["prefweap weapon_bfg weapon_disintegrator weapon_phalanx weapon_railgun weapon_rocketlauncher weapon_plasmabeam weapon_boomer weapon_hyperblaster weapon_grenadelauncher weapon_chaingun weapon_proxlauncher ammo_grenades weapon_supershotgun", "best unsafe weapon"], ["centerview", "center view"], ["inven", "inventory"], ["invuse", "use item"], ["invdrop", "drop item"], ["invprev", "prev item"], ["invnext", "next item"], ["use invulnerability", "use invulnerability"], ["use rebreather", "use rebreather"], ["use environment suit", "use environment suit"], ["use power shield", "use power shield"], ["use quad damage", "use quad damage"], ["cmd help", "help computer"]] #char *[][2]
s_controller_alt_buttons_menu = qmenu_h.menuframework_s() #static menuframework_s
s_controller_alt_buttons_actions = [qmenu_h.menuaction_s() for i in range(len(controller_alt_bindnames))] #static menuaction_s[ARRLEN(controller_alt_bindnames)]

def DrawControllerAltButtonBindingFunc(self): #void * (static)

	"""
	int keys[2];
	menuaction_s *a = (menuaction_s *)self;
	float scale = SCR_GetMenuScale();
	"""
	keys = [0] * 2
	a = self
	scale = cl_screen.SCR_GetMenuScale()

	M_FindKeysForCommand(controller_alt_bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_CONTROLLER_ALT)
	if keys[0] == -1:

		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, "???")

	else:

		#size_t x;
		#const char *name;
		name = cl_keyboard.Key_KeynumToString_Joy(keys[0])
		qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + qmenu_h.RCOLUMN_OFFSET * scale, a.generic.y + a.generic.parent.y, name)
		x = len(name) * 8
		if keys[1] != -1:

			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 24 * scale + (x * scale), a.generic.y + a.generic.parent.y, "or")
			qmenu.Menu_DrawString(a.generic.x + a.generic.parent.x + 48 * scale + (x * scale), a.generic.y + a.generic.parent.y, cl_keyboard.Key_KeynumToString_Joy(keys[1]))

def ControllerAltButtonBindingFunc(self): #void * (static)
	global menukeyitem_bind

	"""
	menuaction_s *a = (menuaction_s *)self;
	int keys[2];
	"""
	a = self
	keys = [0] * 2

	M_FindKeysForCommand(controller_alt_bindnames[a.generic.localdata[0]][0], keys, qmenu_h.KEYS_CONTROLLER_ALT)
	if keys[1] != -1:

		M_UnbindCommand(controller_alt_bindnames[a.generic.localdata[0]][0], qmenu_h.KEYS_CONTROLLER_ALT)


	menukeyitem_bind = True
	qmenu.Menu_SetStatusBar(s_controller_alt_buttons_menu, "press a button for this action")

def ControllerAltButtons_MenuInit(): # (static)

	"""
	int i;
	"""

	s_controller_alt_buttons_menu.x = int(vid.viddef.width * 0.50)
	s_controller_alt_buttons_menu.nitems = 0
	s_controller_alt_buttons_menu.cursordraw = KeyCursorDrawFunc
	for i in range(len(controller_alt_bindnames)):

		s_controller_alt_buttons_actions[i].generic.type = qmenu_h.MTYPE_ACTION
		s_controller_alt_buttons_actions[i].generic.flags = qmenu_h.QMF_GRAYED
		s_controller_alt_buttons_actions[i].generic.x = 0
		s_controller_alt_buttons_actions[i].generic.y = (i * 9)
		s_controller_alt_buttons_actions[i].generic.ownerdraw = DrawControllerAltButtonBindingFunc
		s_controller_alt_buttons_actions[i].generic.localdata[0] = i
		s_controller_alt_buttons_actions[i].generic.name = controller_alt_bindnames[s_controller_alt_buttons_actions[i].generic.localdata[0]][1]
		qmenu.Menu_AddItem(s_controller_alt_buttons_menu, s_controller_alt_buttons_actions[i])


	GamepadMenu_StatusPrompt(s_controller_alt_buttons_menu)
	qmenu.Menu_Center(s_controller_alt_buttons_menu)

def ControllerAltButtons_MenuKey(m, key): #menuframework_s *, int (returns static const char *)
	global menukeyitem_bind

	"""
	menuaction_s *item = (menuaction_s *)Menu_ItemAtCursor(m);
	"""
	item = qmenu.Menu_ItemAtCursor(m)

	if menukeyitem_bind:

		# Only controller buttons allowed, different from the alt buttons modifier
		if key >= keyboard_h.K_JOY_FIRST_BTN and (cl_keyboard.keybindings[key] == None or (cl_keyboard.keybindings[key] != "+joyaltselector")):

			#char cmd[1024];
			cmd = [None] * 1024
			key = key + (keyboard_h.K_JOY_FIRST_BTN_ALT - keyboard_h.K_JOY_FIRST_BTN)
			# change input to its ALT mode
			cmd = "bind \"%s\" \"%s\"\n" % (cl_keyboard.Key_KeynumToString(key), controller_alt_bindnames[item.generic.localdata[0]][0],) # Com_sprintf
			cmdparser.Cbuf_InsertText(cmd)


		GamepadMenu_StatusPrompt(m)
		menukeyitem_bind = False
		return qmenu.menu_out_sound


	key = Key_GetMenuKey(key)
	if key == keyboard_h.K_ENTER:

		ControllerAltButtonBindingFunc(item)
		return qmenu.menu_in_sound

	elif key == keyboard_h.K_DEL or key == keyboard_h.K_BACKSPACE:

		M_UnbindCommand(controller_alt_bindnames[item.generic.localdata[0]][0], qmenu_h.KEYS_CONTROLLER_ALT)
		return qmenu.menu_out_sound

	else:

		return Default_MenuKey(m, key)

def M_Menu_ControllerAltButtons_f(): # (static)

	ControllerAltButtons_MenuInit()
	s_controller_alt_buttons_menu.draw = Default_MenuDraw
	s_controller_alt_buttons_menu.key = ControllerAltButtons_MenuKey
	M_PushMenu(s_controller_alt_buttons_menu)

"""
extern qboolean show_gyro;
"""

s_sticks_config_menu = qmenu_h.menuframework_s() #static menuframework_s
s_stk_layout_box = qmenu_h.menulist_s() #static menulist_s
s_stk_title_text = [qmenu_h.menuseparator_s() for i in range(3)] #static menuseparator_s[3]
s_stk_expo_slider = [qmenu_h.menuslider_s() for i in range(2)] #static menuslider_s[2]
s_stk_deadzone_slider = [qmenu_h.menuslider_s() for i in range(4)] #static menuslider_s[4]
s_stk_threshold_slider = qmenu_h.menuslider_s() #static menuslider_s

def StickLayoutFunc(unused): #void * (static)

	cvar.Cvar_SetValue("joy_layout", int(s_stk_layout_box.curvalue))

def Stick_MenuInit(): # (static)

	"""
	static const char *stick_layouts[] = { "default", "southpaw", "legacy", "legacy southpaw", NULL };
	static const char *stick_layouts_fs[] = { "default", "southpaw", "legacy", "legacy southpaw", "flick stick", "flick stick spaw", NULL };
	unsigned short int y = 0, i;
	float scale = SCR_GetMenuScale();
	"""
	y = 0
	scale = cl_screen.SCR_GetMenuScale()

	s_sticks_config_menu.x = int(vid.viddef.width * 0.50)
	s_sticks_config_menu.nitems = 0
	s_stk_layout_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_stk_layout_box.generic.x = 0
	s_stk_layout_box.generic.y = y
	s_stk_layout_box.generic.name = "layout"
	s_stk_layout_box.generic.callback = StickLayoutFunc
	if sdl2.show_gyro or sdl2.joy_layout.value > 3:

		s_stk_layout_box.itemnames = stick_layouts_fs
		s_stk_layout_box.curvalue = int(qmenu.ClampCvar(0, 5, sdl2.joy_layout.value)) # int curvalue

	else:

		s_stk_layout_box.itemnames = stick_layouts
		s_stk_layout_box.curvalue = int(qmenu.ClampCvar(0, 3, sdl2.joy_layout.value)) # int curvalue


	s_stk_title_text[0].generic.name = "left stick"
	y += 22; s_stk_title_text[0].generic.y = y
	s_stk_expo_slider[0].generic.name = "expo"
	y += 14; s_stk_expo_slider[0].generic.y = y
	s_stk_expo_slider[0].cvar = "joy_left_expo"
	s_stk_deadzone_slider[0].generic.name = "snap to axis"
	y += 10; s_stk_deadzone_slider[0].generic.y = y
	s_stk_deadzone_slider[0].cvar = "joy_left_snapaxis"
	s_stk_deadzone_slider[1].generic.name = "deadzone"
	y += 10; s_stk_deadzone_slider[1].generic.y = y
	s_stk_deadzone_slider[1].cvar = "joy_left_deadzone"
	s_stk_title_text[1].generic.name = "right stick"
	y += 22; s_stk_title_text[1].generic.y = y
	s_stk_expo_slider[1].generic.name = "expo"
	y += 14; s_stk_expo_slider[1].generic.y = y
	s_stk_expo_slider[1].cvar = "joy_right_expo"
	s_stk_deadzone_slider[2].generic.name = "snap to axis"
	y += 10; s_stk_deadzone_slider[2].generic.y = y
	s_stk_deadzone_slider[2].cvar = "joy_right_snapaxis"
	s_stk_deadzone_slider[3].generic.name = "deadzone"
	y += 10; s_stk_deadzone_slider[3].generic.y = y
	s_stk_deadzone_slider[3].cvar = "joy_right_deadzone"
	for i in range(2):

		s_stk_title_text[i].generic.type = qmenu_h.MTYPE_SEPARATOR
		s_stk_title_text[i].generic.x = int(48 * scale) # int x
		s_stk_expo_slider[i].generic.type = qmenu_h.MTYPE_SLIDER
		s_stk_expo_slider[i].generic.x = 0
		s_stk_expo_slider[i].minvalue = 1
		s_stk_expo_slider[i].maxvalue = 5


	for i in range(4):

		s_stk_deadzone_slider[i].generic.type = qmenu_h.MTYPE_SLIDER
		s_stk_deadzone_slider[i].generic.x = 0
		s_stk_deadzone_slider[i].minvalue = 0.0
		s_stk_deadzone_slider[i].maxvalue = 0.50
		s_stk_deadzone_slider[i].slidestep = 0.01
		s_stk_deadzone_slider[i].printformat = "%.2f"


	s_stk_title_text[2].generic.type = qmenu_h.MTYPE_SEPARATOR
	s_stk_title_text[2].generic.x = int(48 * scale) # int x
	y += 22; s_stk_title_text[2].generic.y = y
	s_stk_title_text[2].generic.name = "both sticks"
	s_stk_threshold_slider.generic.name = "outer thresh"
	s_stk_threshold_slider.generic.x = 0
	y += 14; s_stk_threshold_slider.generic.y = y
	s_stk_threshold_slider.cvar = "joy_outer_threshold"
	s_stk_threshold_slider.minvalue = 0.0
	s_stk_threshold_slider.maxvalue = 0.30
	s_stk_threshold_slider.slidestep = 0.01
	s_stk_threshold_slider.printformat = "%.2f"
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_layout_box)
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_title_text[0])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_expo_slider[0])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_deadzone_slider[0])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_deadzone_slider[1])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_title_text[1])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_expo_slider[1])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_deadzone_slider[2])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_deadzone_slider[3])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_title_text[2])
	qmenu.Menu_AddItem(s_sticks_config_menu, s_stk_threshold_slider)
	qmenu.Menu_Center(s_sticks_config_menu)

def M_Menu_Stick_f(): # (static)

	Stick_MenuInit()
	s_sticks_config_menu.draw = Default_MenuDraw
	s_sticks_config_menu.key = Default_MenuKey
	M_PushMenu(s_sticks_config_menu)

"""
extern void StartCalibration(void);
extern qboolean IsCalibrationZero(void);
static void M_Menu_Joy_f(void);
static void M_Menu_Gyro_f(void);
"""

s_gyro_menu = qmenu_h.menuframework_s() #static menuframework_s
s_gyro_mode_box = qmenu_h.menulist_s() #static menulist_s
s_gyro_space_box = qmenu_h.menulist_s() #static menulist_s
s_gyro_local_roll_box = qmenu_h.menulist_s() #static menulist_s
s_gyro_yawsensitivity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gyro_pitchsensitivity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gyro_tightening_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gyro_smoothing_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gyro_acceleration_box = qmenu_h.menulist_s() #static menulist_s
s_gyro_accel_mult_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gyro_accel_lower_thresh_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gyro_accel_upper_thresh_slider = qmenu_h.menuslider_s() #static menuslider_s
s_calibrating_text = [qmenu_h.menuseparator_s() for i in range(2)] #static menuseparator_s[2]
s_calibrate_gyro = qmenu_h.menuaction_s() #static menuaction_s

def CalibrateGyroFunc(unused): #void * (static)

	if not sdl2.show_gyro:

		return


	qmenu.Menu_StartPopup(m_popup, "Calibrating, please wait...", 4650)
	qmenu.Menu_DrawPopup(320, 240, m_popup)
	vid.R_EndFrame()
	sdl2.StartCalibration()

def CalibrationFinishedCallback(): #

	qmenu.Menu_SetStatusBar(s_gyro_menu, None)
	qmenu.Menu_StartPopup(m_popup, "Calibration complete!", 1900)
	qmenu.Menu_DrawPopup(320, 240, m_popup)
	vid.R_EndFrame()

def GyroModeFunc(unused): #void * (static)

	cvar.Cvar_SetValue("gyro_mode", int(s_gyro_mode_box.curvalue))

def GyroSpaceFunc(unused): #void * (static)

	cvar.Cvar_SetValue("gyro_space", s_gyro_space_box.curvalue)
	# Force the menu to refresh.
	M_PopMenu(True)
	M_Menu_Gyro_f()

def GyroLocalRollFunc(unused): #void * (static)

	cvar.Cvar_SetValue("gyro_local_roll", s_gyro_local_roll_box.curvalue)

def GyroAccelerationFunc(unused): #void * (static)

	cvar.Cvar_SetValue("gyro_acceleration", s_gyro_acceleration_box.curvalue)
	# Force the menu to refresh.
	M_PopMenu(True)
	M_Menu_Gyro_f()

def GyroAcceThreshFunc(unused): #void * (static)

	"""
	const float min_value = Cvar_VariableValue("gyro_accel_lower_thresh");
	float value = Cvar_VariableValue("gyro_accel_upper_thresh");
	"""
	min_value = cvar.Cvar_VariableValue("gyro_accel_lower_thresh")
	value = cvar.Cvar_VariableValue("gyro_accel_upper_thresh")

	# Make sure the accel upper threshold is always greater than or equal to
	# the accel lower threshold.
	value = qmenu.ClampCvar(min_value, gyro_h.GYRO_MAX_ACCEL_THRESH, value)
	cvar.Cvar_SetValue("gyro_accel_upper_thresh", value)

def Gyro_MenuInit(): # (static)

	"""
	static const char *gyro_modes[] = { "always off", "off, button enables", "on, button disables", "always on", NULL };
	static const char *gyro_space_choices[] = { "local", "player", "world", NULL };
	static const char *gyro_local_roll_choices[] = { "off", "on", "on, invert", NULL };
	static const char *onoff_names[] = { "off", "on", NULL };
	unsigned short int y = 0;
	float scale = SCR_GetMenuScale();
	"""
	y = 0
	scale = cl_screen.SCR_GetMenuScale()

	s_gyro_menu.x = int(vid.viddef.width * 0.50)
	s_gyro_menu.nitems = 0
	s_gyro_mode_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_gyro_mode_box.generic.x = 0
	s_gyro_mode_box.generic.y = y
	s_gyro_mode_box.generic.name = "gyro mode"
	s_gyro_mode_box.generic.callback = GyroModeFunc
	s_gyro_mode_box.itemnames = gyro_modes
	s_gyro_mode_box.curvalue = int(qmenu.ClampCvar(0, 3, sdl2.gyro_mode.value)) # int curvalue
	s_gyro_space_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_gyro_space_box.generic.x = 0
	y += 10; s_gyro_space_box.generic.y = y
	s_gyro_space_box.generic.name = "gyro space"
	s_gyro_space_box.generic.callback = GyroSpaceFunc
	s_gyro_space_box.itemnames = gyro_space_choices
	s_gyro_space_box.curvalue = int(qmenu.ClampCvar(gyro_h.GYRO_SPACE_LOCAL, gyro_h.GYRO_SPACE_WORLD, cvar.Cvar_VariableValue("gyro_space"))) # int curvalue
	if s_gyro_space_box.curvalue == gyro_h.GYRO_SPACE_LOCAL:

		s_gyro_local_roll_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_gyro_local_roll_box.generic.x = 0
		y += 10; s_gyro_local_roll_box.generic.y = y
		s_gyro_local_roll_box.generic.name = "local roll"
		s_gyro_local_roll_box.generic.callback = GyroLocalRollFunc
		s_gyro_local_roll_box.itemnames = gyro_local_roll_choices
		s_gyro_local_roll_box.curvalue = int(qmenu.ClampCvar(gyro_h.GYRO_LOCAL_ROLL_OFF, gyro_h.GYRO_LOCAL_ROLL_INVERT, cvar.Cvar_VariableValue("gyro_local_roll"))) # int curvalue


	s_gyro_yawsensitivity_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_gyro_yawsensitivity_slider.generic.x = 0
	y += 20; s_gyro_yawsensitivity_slider.generic.y = y
	s_gyro_yawsensitivity_slider.generic.name = "yaw sensitivity"
	s_gyro_yawsensitivity_slider.cvar = "gyro_yawsensitivity"
	s_gyro_yawsensitivity_slider.minvalue = gyro_h.GYRO_MIN_SENS
	s_gyro_yawsensitivity_slider.maxvalue = gyro_h.GYRO_MAX_SENS
	s_gyro_yawsensitivity_slider.slidestep = gyro_h.GYRO_STEP_SENS
	s_gyro_yawsensitivity_slider.abs = True
	s_gyro_pitchsensitivity_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_gyro_pitchsensitivity_slider.generic.x = 0
	y += 10; s_gyro_pitchsensitivity_slider.generic.y = y
	s_gyro_pitchsensitivity_slider.generic.name = "pitch sensitivity"
	s_gyro_pitchsensitivity_slider.cvar = "gyro_pitchsensitivity"
	s_gyro_pitchsensitivity_slider.minvalue = gyro_h.GYRO_MIN_SENS
	s_gyro_pitchsensitivity_slider.maxvalue = gyro_h.GYRO_MAX_SENS
	s_gyro_pitchsensitivity_slider.slidestep = gyro_h.GYRO_STEP_SENS
	s_gyro_pitchsensitivity_slider.abs = True
	s_gyro_tightening_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_gyro_tightening_slider.generic.x = 0
	y += 20; s_gyro_tightening_slider.generic.y = y
	s_gyro_tightening_slider.generic.name = "tightening"
	s_gyro_tightening_slider.cvar = "gyro_tightening"
	s_gyro_tightening_slider.minvalue = gyro_h.GYRO_MIN_TIGHT_THRESH
	s_gyro_tightening_slider.maxvalue = gyro_h.GYRO_MAX_TIGHT_THRESH
	s_gyro_tightening_slider.slidestep = gyro_h.GYRO_STEP_TIGHT_THRESH
	s_gyro_smoothing_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_gyro_smoothing_slider.generic.x = 0
	y += 10; s_gyro_smoothing_slider.generic.y = y
	s_gyro_smoothing_slider.generic.name = "smoothing"
	s_gyro_smoothing_slider.cvar = "gyro_smoothing"
	s_gyro_smoothing_slider.minvalue = gyro_h.GYRO_MIN_SMOOTH_THRESH
	s_gyro_smoothing_slider.maxvalue = gyro_h.GYRO_MAX_SMOOTH_THRESH
	s_gyro_smoothing_slider.slidestep = gyro_h.GYRO_STEP_SMOOTH_THRESH
	s_gyro_acceleration_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_gyro_acceleration_box.generic.x = 0
	y += 20; s_gyro_acceleration_box.generic.y = y
	s_gyro_acceleration_box.generic.name = "acceleration"
	s_gyro_acceleration_box.generic.callback = GyroAccelerationFunc
	s_gyro_acceleration_box.itemnames = onoff_names
	s_gyro_acceleration_box.curvalue = (cvar.Cvar_VariableValue("gyro_acceleration") > 0)
	if s_gyro_acceleration_box.curvalue:

		s_gyro_accel_mult_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gyro_accel_mult_slider.generic.x = 0
		y += 10; s_gyro_accel_mult_slider.generic.y = y
		s_gyro_accel_mult_slider.generic.name = "multiplier"
		s_gyro_accel_mult_slider.cvar = "gyro_accel_multiplier"
		s_gyro_accel_mult_slider.minvalue = gyro_h.GYRO_MIN_ACCEL_MULT
		s_gyro_accel_mult_slider.maxvalue = gyro_h.GYRO_MAX_ACCEL_MULT
		s_gyro_accel_mult_slider.slidestep = gyro_h.GYRO_STEP_ACCEL_MULT
		s_gyro_accel_lower_thresh_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gyro_accel_lower_thresh_slider.generic.x = 0
		y += 10; s_gyro_accel_lower_thresh_slider.generic.y = y
		s_gyro_accel_lower_thresh_slider.generic.name = "lower thresh"
		s_gyro_accel_lower_thresh_slider.generic.callback = GyroAcceThreshFunc
		s_gyro_accel_lower_thresh_slider.cvar = "gyro_accel_lower_thresh"
		s_gyro_accel_lower_thresh_slider.minvalue = gyro_h.GYRO_MIN_ACCEL_THRESH
		s_gyro_accel_lower_thresh_slider.maxvalue = gyro_h.GYRO_MAX_ACCEL_THRESH
		s_gyro_accel_lower_thresh_slider.slidestep = gyro_h.GYRO_STEP_ACCEL_THRESH
		s_gyro_accel_lower_thresh_slider.printformat = "%.0f"
		s_gyro_accel_upper_thresh_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gyro_accel_upper_thresh_slider.generic.x = 0
		y += 10; s_gyro_accel_upper_thresh_slider.generic.y = y
		s_gyro_accel_upper_thresh_slider.generic.name = "upper thresh"
		s_gyro_accel_upper_thresh_slider.generic.callback = GyroAcceThreshFunc
		s_gyro_accel_upper_thresh_slider.cvar = "gyro_accel_upper_thresh"
		s_gyro_accel_upper_thresh_slider.minvalue = gyro_h.GYRO_MIN_ACCEL_THRESH
		s_gyro_accel_upper_thresh_slider.maxvalue = gyro_h.GYRO_MAX_ACCEL_THRESH
		s_gyro_accel_upper_thresh_slider.slidestep = gyro_h.GYRO_STEP_ACCEL_THRESH
		s_gyro_accel_upper_thresh_slider.printformat = "%.0f"


	s_calibrating_text[0].generic.type = qmenu_h.MTYPE_SEPARATOR
	s_calibrating_text[0].generic.x = int(48 * scale + 32) # int x
	y += 20; s_calibrating_text[0].generic.y = y
	s_calibrating_text[0].generic.name = "place the gamepad on a flat,"
	s_calibrating_text[1].generic.type = qmenu_h.MTYPE_SEPARATOR
	s_calibrating_text[1].generic.x = int(48 * scale + 32) # int x
	y += 10; s_calibrating_text[1].generic.y = y
	s_calibrating_text[1].generic.name = "stable surface to..."
	s_calibrate_gyro.generic.type = qmenu_h.MTYPE_ACTION
	s_calibrate_gyro.generic.x = 0
	y += 15; s_calibrate_gyro.generic.y = y
	s_calibrate_gyro.generic.name = "calibrate"
	s_calibrate_gyro.generic.callback = CalibrateGyroFunc
	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_mode_box)
	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_space_box)
	if s_gyro_space_box.curvalue == gyro_h.GYRO_SPACE_LOCAL:

		qmenu.Menu_AddItem(s_gyro_menu, s_gyro_local_roll_box)


	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_yawsensitivity_slider)
	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_pitchsensitivity_slider)
	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_tightening_slider)
	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_smoothing_slider)
	qmenu.Menu_AddItem(s_gyro_menu, s_gyro_acceleration_box)
	if s_gyro_acceleration_box.curvalue:

		qmenu.Menu_AddItem(s_gyro_menu, s_gyro_accel_mult_slider)
		qmenu.Menu_AddItem(s_gyro_menu, s_gyro_accel_lower_thresh_slider)
		qmenu.Menu_AddItem(s_gyro_menu, s_gyro_accel_upper_thresh_slider)


	qmenu.Menu_AddItem(s_gyro_menu, s_calibrating_text[0])
	qmenu.Menu_AddItem(s_gyro_menu, s_calibrating_text[1])
	qmenu.Menu_AddItem(s_gyro_menu, s_calibrate_gyro)
	if sdl2.IsCalibrationZero():

		qmenu.Menu_SetStatusBar(s_gyro_menu, "Calibration required")


	qmenu.Menu_Center(s_gyro_menu)

def M_Menu_Gyro_f(): # (static)

	Gyro_MenuInit()
	s_gyro_menu.draw = Default_MenuDraw
	s_gyro_menu.key = Default_MenuKey
	M_PushMenu(s_gyro_menu)

"""
extern void IN_ApplyJoyPreset(void);
extern qboolean IN_MatchJoyPreset(void);
"""

s_joy_preset_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_preset_box = qmenu_h.menulist_s() #static menulist_s
s_joy_advanced_box = qmenu_h.menulist_s() #static menulist_s
s_joy_invertpitch_box = qmenu_h.menulist_s() #static menulist_s
s_joy_yawspeed_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_pitchspeed_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_extra_yawspeed_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_extra_pitchspeed_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_ramp_time_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_haptic_slider = qmenu_h.menuslider_s() #static menuslider_s
s_joy_stickcfg_action = qmenu_h.menuaction_s() #static menuaction_s
s_joy_gyro_action = qmenu_h.menuaction_s() #static menuaction_s
s_joy_customize_buttons_action = qmenu_h.menuaction_s() #static menuaction_s
s_joy_customize_alt_buttons_action = qmenu_h.menuaction_s() #static menuaction_s

def RefreshJoyMenuFunc(unused): #void * (static)

	M_PopMenu(True)
	M_Menu_Joy_f()

def JoyPresetFunc(unused): #void * (static)

	sdl2.IN_ApplyJoyPreset()
	RefreshJoyMenuFunc(None)

def JoyAdvancedFunc(unused): #void * (static)

	cvar.Cvar_SetValue("joy_advanced", s_joy_advanced_box.curvalue)
	RefreshJoyMenuFunc(None)

def CustomizeControllerButtonsFunc(unused): #void * (static)

	M_Menu_ControllerButtons_f()

def CustomizeControllerAltButtonsFunc(unused): #void * (static)

	M_Menu_ControllerAltButtons_f()

def ConfigStickFunc(unused): #void * (static)

	M_Menu_Stick_f()

def ConfigGyroFunc(unused): #void * (static)

	M_Menu_Gyro_f()

def InvertJoyPitchFunc(unused): #void * (static)

	"""
	float v = fabsf(Cvar_VariableValue("joy_pitchspeed"));
	"""
	v = abs(cvar.Cvar_VariableValue("joy_pitchspeed"))

	cvar.Cvar_SetValue("joy_pitchspeed",(-v if s_joy_invertpitch_box.curvalue else v))

def Joy_MenuInit(): # (static)

	"""
	static const char *yesno_names[] = { "no", "yes", NULL };
	static const char *custom_names[] = { "", "custom", "", NULL };
	unsigned short int y = 0;
	"""
	y = 0

	#extern qboolean show_haptic;
	s_joy_menu.x = int(vid.viddef.width * 0.50)
	s_joy_menu.nitems = 0
	if sdl2.IN_MatchJoyPreset():

		s_joy_preset_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_preset_slider.generic.x = 0
		s_joy_preset_slider.generic.y = y
		s_joy_preset_slider.generic.name = "look sensitivity"
		s_joy_preset_slider.generic.callback = JoyPresetFunc
		s_joy_preset_slider.cvar = "joy_sensitivity"
		s_joy_preset_slider.minvalue = 0.0
		s_joy_preset_slider.maxvalue = 8.0
		s_joy_preset_slider.slidestep = 1.0
		s_joy_preset_slider.printformat = "%.0f"
		qmenu.Menu_AddItem(s_joy_menu, s_joy_preset_slider)

	else:

		# Display "custom"
		s_joy_preset_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_joy_preset_box.generic.x = 0
		s_joy_preset_box.generic.y = y
		s_joy_preset_box.generic.name = "look sensitivity"
		s_joy_preset_box.generic.callback = JoyPresetFunc
		s_joy_preset_box.itemnames = custom_names
		s_joy_preset_box.curvalue = 1
		qmenu.Menu_AddItem(s_joy_menu, s_joy_preset_box)


	s_joy_advanced_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_joy_advanced_box.generic.x = 0
	y += 10; s_joy_advanced_box.generic.y = y
	s_joy_advanced_box.generic.name = "show advanced"
	s_joy_advanced_box.generic.callback = JoyAdvancedFunc
	s_joy_advanced_box.itemnames = yesno_names
	s_joy_advanced_box.curvalue = (cvar.Cvar_VariableValue("joy_advanced") > 0)
	qmenu.Menu_AddItem(s_joy_menu, s_joy_advanced_box)
	if s_joy_advanced_box.curvalue:

		s_joy_yawspeed_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_yawspeed_slider.generic.x = 0
		y += 10; s_joy_yawspeed_slider.generic.y = y
		s_joy_yawspeed_slider.generic.name = "yaw speed"
		s_joy_yawspeed_slider.generic.callback = RefreshJoyMenuFunc
		s_joy_yawspeed_slider.cvar = "joy_yawspeed"
		s_joy_yawspeed_slider.minvalue = 0.0
		s_joy_yawspeed_slider.maxvalue = 720.0
		s_joy_yawspeed_slider.slidestep = 10.0
		s_joy_yawspeed_slider.printformat = "%.0f"
		qmenu.Menu_AddItem(s_joy_menu, s_joy_yawspeed_slider)
		s_joy_pitchspeed_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_pitchspeed_slider.generic.x = 0
		y += 10; s_joy_pitchspeed_slider.generic.y = y
		s_joy_pitchspeed_slider.generic.name = "pitch speed"
		s_joy_pitchspeed_slider.generic.callback = RefreshJoyMenuFunc
		s_joy_pitchspeed_slider.cvar = "joy_pitchspeed"
		s_joy_pitchspeed_slider.minvalue = 0.0
		s_joy_pitchspeed_slider.maxvalue = 720.0
		s_joy_pitchspeed_slider.slidestep = 10.0
		s_joy_pitchspeed_slider.printformat = "%.0f"
		s_joy_pitchspeed_slider.abs = True
		qmenu.Menu_AddItem(s_joy_menu, s_joy_pitchspeed_slider)
		s_joy_extra_yawspeed_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_extra_yawspeed_slider.generic.x = 0
		y += 10; s_joy_extra_yawspeed_slider.generic.y = y
		s_joy_extra_yawspeed_slider.generic.name = "extra yaw speed"
		s_joy_extra_yawspeed_slider.cvar = "joy_extra_yawspeed"
		s_joy_extra_yawspeed_slider.generic.callback = RefreshJoyMenuFunc
		s_joy_extra_yawspeed_slider.minvalue = 0.0
		s_joy_extra_yawspeed_slider.maxvalue = 720.0
		s_joy_extra_yawspeed_slider.slidestep = 10.0
		s_joy_extra_yawspeed_slider.printformat = "%.0f"
		qmenu.Menu_AddItem(s_joy_menu, s_joy_extra_yawspeed_slider)
		s_joy_extra_pitchspeed_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_extra_pitchspeed_slider.generic.x = 0
		y += 10; s_joy_extra_pitchspeed_slider.generic.y = y
		s_joy_extra_pitchspeed_slider.generic.name = "extra pitch speed"
		s_joy_extra_pitchspeed_slider.cvar = "joy_extra_pitchspeed"
		s_joy_extra_pitchspeed_slider.generic.callback = RefreshJoyMenuFunc
		s_joy_extra_pitchspeed_slider.minvalue = 0.0
		s_joy_extra_pitchspeed_slider.maxvalue = 720.0
		s_joy_extra_pitchspeed_slider.slidestep = 10.0
		s_joy_extra_pitchspeed_slider.printformat = "%.0f"
		qmenu.Menu_AddItem(s_joy_menu, s_joy_extra_pitchspeed_slider)
		s_joy_ramp_time_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_ramp_time_slider.generic.x = 0
		y += 10; s_joy_ramp_time_slider.generic.y = y
		s_joy_ramp_time_slider.generic.name = "ramp time"
		s_joy_ramp_time_slider.cvar = "joy_ramp_time"
		s_joy_ramp_time_slider.generic.callback = RefreshJoyMenuFunc
		s_joy_ramp_time_slider.minvalue = 0.0
		s_joy_ramp_time_slider.maxvalue = 1.0
		s_joy_ramp_time_slider.slidestep = 0.05
		s_joy_ramp_time_slider.printformat = "%.2f"
		qmenu.Menu_AddItem(s_joy_menu, s_joy_ramp_time_slider)


	s_joy_invertpitch_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_joy_invertpitch_box.generic.x = 0
	y += 10; s_joy_invertpitch_box.generic.y = y
	s_joy_invertpitch_box.generic.name = "invert pitch"
	s_joy_invertpitch_box.generic.callback = InvertJoyPitchFunc
	s_joy_invertpitch_box.itemnames = yesno_names
	s_joy_invertpitch_box.curvalue = (cvar.Cvar_VariableValue("joy_pitchspeed") < 0)
	qmenu.Menu_AddItem(s_joy_menu, s_joy_invertpitch_box)
	if sdl2.show_haptic:

		s_joy_haptic_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_joy_haptic_slider.generic.x = 0
		y += 20; s_joy_haptic_slider.generic.y = y
		s_joy_haptic_slider.generic.name = "rumble intensity"
		s_joy_haptic_slider.cvar = "joy_haptic_magnitude"
		s_joy_haptic_slider.minvalue = 0.0
		s_joy_haptic_slider.maxvalue = 2.0
		qmenu.Menu_AddItem(s_joy_menu, s_joy_haptic_slider)


	s_joy_stickcfg_action.generic.type = qmenu_h.MTYPE_ACTION
	s_joy_stickcfg_action.generic.x = 0
	y += 20; s_joy_stickcfg_action.generic.y = y
	s_joy_stickcfg_action.generic.name = "sticks config"
	s_joy_stickcfg_action.generic.callback = ConfigStickFunc
	qmenu.Menu_AddItem(s_joy_menu, s_joy_stickcfg_action)
	if sdl2.show_gyro:

		s_joy_gyro_action.generic.type = qmenu_h.MTYPE_ACTION
		s_joy_gyro_action.generic.x = 0
		y += 10; s_joy_gyro_action.generic.y = y
		s_joy_gyro_action.generic.name = "gyro options"
		s_joy_gyro_action.generic.callback = ConfigGyroFunc
		qmenu.Menu_AddItem(s_joy_menu, s_joy_gyro_action)


	s_joy_customize_buttons_action.generic.type = qmenu_h.MTYPE_ACTION
	s_joy_customize_buttons_action.generic.x = 0
	y += 20; s_joy_customize_buttons_action.generic.y = y
	s_joy_customize_buttons_action.generic.name = "customize buttons"
	s_joy_customize_buttons_action.generic.callback = CustomizeControllerButtonsFunc
	qmenu.Menu_AddItem(s_joy_menu, s_joy_customize_buttons_action)
	s_joy_customize_alt_buttons_action.generic.type = qmenu_h.MTYPE_ACTION
	s_joy_customize_alt_buttons_action.generic.x = 0
	y += 10; s_joy_customize_alt_buttons_action.generic.y = y
	s_joy_customize_alt_buttons_action.generic.name = "custom. alt buttons"
	s_joy_customize_alt_buttons_action.generic.callback = CustomizeControllerAltButtonsFunc
	qmenu.Menu_AddItem(s_joy_menu, s_joy_customize_alt_buttons_action)
	qmenu.Menu_Center(s_joy_menu)

def M_Menu_Joy_f(): # (static)

	Joy_MenuInit()
	s_joy_menu.draw = Default_MenuDraw
	s_joy_menu.key = Default_MenuKey
	M_PushMenu(s_joy_menu)

s_options_menu = qmenu_h.menuframework_s() #static menuframework_s
s_options_defaults_action = qmenu_h.menuaction_s() #static menuaction_s
s_options_customize_options_action = qmenu_h.menuaction_s() #static menuaction_s
s_options_customize_joy_action = qmenu_h.menuaction_s() #static menuaction_s
s_options_sensitivity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_options_freelook_box = qmenu_h.menulist_s() #static menulist_s
s_options_alwaysrun_box = qmenu_h.menulist_s() #static menulist_s
s_options_invertmouse_box = qmenu_h.menulist_s() #static menulist_s
s_options_lookstrafe_box = qmenu_h.menulist_s() #static menulist_s
s_options_crosshair_box = qmenu_h.menulist_s() #static menulist_s
s_options_crosshair_color_box = qmenu_h.menulist_s() #static menulist_s
s_options_sfxvolume_slider = qmenu_h.menuslider_s() #static menuslider_s
s_options_oggshuffle_box = qmenu_h.menulist_s() #static menulist_s
s_options_oggvolume_slider = qmenu_h.menuslider_s() #static menuslider_s
s_options_oggenable_box = qmenu_h.menulist_s() #static menulist_s
s_options_quality_list = qmenu_h.menulist_s() #static menulist_s
s_options_console_action = qmenu_h.menulist_s() #static menulist_s

def CrosshairFunc(unused): #void * (static)

	cvar.Cvar_SetValue("crosshair", float(s_options_crosshair_box.curvalue))

crosshair_color_values = [ #static const float [][3], in CrosshairColorFunc and ControlsSetMenuItemValues
	[1.0, 1.0, 1.0],  # white
	[1.0, 0.0, 0.0],  # red
	[0.0, 1.0, 0.0],  # green
	[0.0, 0.0, 1.0],  # blue
	[1.0, 1.0, 0.0],  # yellow
	[0.0, 1.0, 1.0],  # cyan
	[1.0, 0.0, 1.0],  # magenta
	[1.0, 0.5, 0.0],  # orange
]

def CrosshairColorFunc(unused): #void * (static)

	color_values = crosshair_color_values

	idx = s_options_crosshair_color_box.curvalue

	if idx < 0 or idx >= len(color_values): # (int)ARRLEN(color_values)

		idx = 0


	cvar.Cvar_SetValue("crosshair_color_r", color_values[idx][0])
	cvar.Cvar_SetValue("crosshair_color_g", color_values[idx][1])
	cvar.Cvar_SetValue("crosshair_color_b", color_values[idx][2])


def CustomizeControlsFunc(unused): #void * (static)

	M_Menu_Keys_f()

def CustomizeJoyFunc(unused): #void * (static)

	M_Menu_Joy_f()

def AlwaysRunFunc(unused): #void * (static)

	cvar.Cvar_SetValue("cl_run", s_options_alwaysrun_box.curvalue)

def FreeLookFunc(unused): #void * (static)

	cvar.Cvar_SetValue("freelook", s_options_freelook_box.curvalue)

def ControlsSetMenuItemValues(): # (static)

	s_options_oggshuffle_box.curvalue = int(cvar.Cvar_VariableValue("ogg_shuffle"))
	s_options_oggenable_box.curvalue = int(cvar.Cvar_VariableValue("ogg_enable") != 0)
	s_options_quality_list.curvalue = int(cvar.Cvar_VariableValue("s_openal") == 0)
	s_options_alwaysrun_box.curvalue = int(cl_input.cl_run.value != 0)
	s_options_invertmouse_box.curvalue = int(sdl2.m_pitch.value < 0)
	s_options_lookstrafe_box.curvalue = int(sdl2.lookstrafe.value != 0)
	s_options_freelook_box.curvalue = int(sdl2.freelook.value != 0)
	s_options_crosshair_box.curvalue = int(qmenu.ClampCvar(0, 3, cl_view.crosshair.value))

	# Match crosshair color cvars to a preset index
	color_values = crosshair_color_values
	r = cvar.Cvar_VariableValue("crosshair_color_r")
	g = cvar.Cvar_VariableValue("crosshair_color_g")
	b = cvar.Cvar_VariableValue("crosshair_color_b")
	best = 0
	best_dist = 999.0

	for i in range(8):

		dr = r - color_values[i][0]
		dg = g - color_values[i][1]
		db = b - color_values[i][2]
		dist = dr * dr + dg * dg + db * db

		if dist < best_dist:

			best_dist = dist
			best = i



	s_options_crosshair_color_box.curvalue = best


def ControlsResetDefaultsFunc(unused): #void * (static)

	cmdparser.Cbuf_AddText("exec default.cfg\n")
	cmdparser.Cbuf_AddText("exec yq2.cfg\n")
	cmdparser.Cbuf_Execute()
	ControlsSetMenuItemValues()
	s_options_oggshuffle_box.curvalue = 0

def InvertMouseFunc(unused): #void * (static)

	"""
	float v = fabsf(m_pitch->value);
	"""
	v = abs(sdl2.m_pitch.value)

	cvar.Cvar_SetValue("m_pitch",(-v if s_options_invertmouse_box.curvalue else v))

def LookstrafeFunc(unused): #void * (static)

	cvar.Cvar_SetValue("lookstrafe", s_options_lookstrafe_box.curvalue)

def OGGShuffleFunc(unused): #void * (static)

	cvar.Cvar_SetValue("ogg_shuffle", s_options_oggshuffle_box.curvalue)

def EnableOGGMusic(unused): #void * (static)

	cvar.Cvar_SetValue("ogg_enable", s_options_oggenable_box.curvalue)
	if s_options_oggenable_box.curvalue:

		ogg.OGG_Init()
		ogg.OGG_InitTrackList()
		ogg.OGG_Stop()
		if cl_main.cls.state == client_h.connstate_t.ca_active:

			ogg.OGG_PlayTrack(cl_main.cl.configstrings[shared.CS_CDTRACK], True, True)


	else:

		ogg.OGG_Shutdown()

"""
extern void Key_ClearTyping(void);
"""

def ConsoleFunc(unused): #void * (static)

	cl_screen.SCR_EndLoadingPlaque()
	# get rid of loading plaque
	if cl_main.cl.attractloop:

		cmdparser.Cbuf_AddText("killserver\n")
		return


	cl_console.Key_ClearTyping()
	cl_console.Con_ClearNotify()
	M_ForceMenuOff()
	cl_main.cls.key_dest = client_h.keydest_t.key_console
	if (cvar.Cvar_VariableValue("maxclients") == 1) and clientserver.Com_ServerState():

		cvar.Cvar_Set("paused", "1")

def UpdateSoundBackendFunc(unused): #void * (static)

	cvar.Cvar_Set("s_openal",("1" if (s_options_quality_list.curvalue == 0) else "0"))
	qmenu.Menu_StartPopup(m_popup, "Restarting the sound system. This\n" "could take up to a minute, so\n" "please be patient.", 2000)
	qmenu.Menu_DrawPopup(320, 240, m_popup)
	# the text box won't show up unless we do a buffer swap
	vid.R_EndFrame()
	cl_main.CL_Snd_Restart_f()

def Options_MenuInit(): # (static)

	"""
	static const char *ogg_shuffle_items[] = { "default", "play once", "sequential", "random", NULL };
	static const char *able_items[] = { "disabled", "enabled", NULL };
	static const char *sound_items[] = { "openal", "sdl", NULL };
	static const char *yesno_names[] = { "no", "yes", NULL };
	static const char *crosshair_names[] = { "none", "cross", "dot", "angle", NULL };
	static const char *crosshair_color_names[] = { "white", "red", "green", "blue", "yellow", "cyan", "magenta", "orange", NULL };
	float scale = SCR_GetMenuScale();
	unsigned short int y = 0;
	"""
	scale = cl_screen.SCR_GetMenuScale()
	y = 0

	#extern qboolean show_gamepad;
	# configure controls menu and menu items
	s_options_menu.x = int(vid.viddef.width / 2) # int x
	s_options_menu.y = int(vid.viddef.height / (2 * scale) - 58) # int y
	s_options_menu.banner = "m_banner_options"
	s_options_menu.nitems = 0
	s_options_sfxvolume_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_options_sfxvolume_slider.generic.x = 0
	s_options_sfxvolume_slider.generic.y = y
	s_options_sfxvolume_slider.generic.name = "effects volume"
	s_options_sfxvolume_slider.cvar = "s_volume"
	s_options_sfxvolume_slider.minvalue = 0.0
	s_options_sfxvolume_slider.maxvalue = 1.0
	s_options_oggvolume_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_options_oggvolume_slider.generic.x = 0
	y += 10; s_options_oggvolume_slider.generic.y = y
	s_options_oggvolume_slider.generic.name = "OGG volume"
	s_options_oggvolume_slider.cvar = "ogg_volume"
	s_options_oggvolume_slider.minvalue = 0.0
	s_options_oggvolume_slider.maxvalue = 1.0
	s_options_oggenable_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_oggenable_box.generic.x = 0
	y += 10; s_options_oggenable_box.generic.y = y
	s_options_oggenable_box.generic.name = "OGG music"
	s_options_oggenable_box.generic.callback = EnableOGGMusic
	s_options_oggenable_box.itemnames = able_items
	s_options_oggshuffle_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_oggshuffle_box.generic.x = 0
	y += 10; s_options_oggshuffle_box.generic.y = y
	s_options_oggshuffle_box.generic.name = "OGG playback mode"
	s_options_oggshuffle_box.generic.callback = OGGShuffleFunc
	s_options_oggshuffle_box.itemnames = ogg_shuffle_items
	s_options_quality_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_quality_list.generic.x = 0
	y += 10; s_options_quality_list.generic.y = y
	s_options_quality_list.generic.name = "sound backend"
	s_options_quality_list.generic.callback = UpdateSoundBackendFunc
	s_options_quality_list.itemnames = sound_items
	s_options_sensitivity_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_options_sensitivity_slider.generic.x = 0
	y += 20; s_options_sensitivity_slider.generic.y = y
	s_options_sensitivity_slider.generic.name = "mouse speed"
	s_options_sensitivity_slider.cvar = "sensitivity"
	s_options_sensitivity_slider.minvalue = 0
	s_options_sensitivity_slider.maxvalue = 11
	s_options_sensitivity_slider.slidestep = 0.5
	s_options_alwaysrun_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_alwaysrun_box.generic.x = 0
	y += 10; s_options_alwaysrun_box.generic.y = y
	s_options_alwaysrun_box.generic.name = "always run"
	s_options_alwaysrun_box.generic.callback = AlwaysRunFunc
	s_options_alwaysrun_box.itemnames = yesno_names
	s_options_invertmouse_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_invertmouse_box.generic.x = 0
	y += 10; s_options_invertmouse_box.generic.y = y
	s_options_invertmouse_box.generic.name = "invert mouse"
	s_options_invertmouse_box.generic.callback = InvertMouseFunc
	s_options_invertmouse_box.itemnames = yesno_names
	s_options_lookstrafe_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_lookstrafe_box.generic.x = 0
	y += 10; s_options_lookstrafe_box.generic.y = y
	s_options_lookstrafe_box.generic.name = "lookstrafe"
	s_options_lookstrafe_box.generic.callback = LookstrafeFunc
	s_options_lookstrafe_box.itemnames = yesno_names
	s_options_freelook_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_freelook_box.generic.x = 0
	y += 10; s_options_freelook_box.generic.y = y
	s_options_freelook_box.generic.name = "free look"
	s_options_freelook_box.generic.callback = FreeLookFunc
	s_options_freelook_box.itemnames = yesno_names
	s_options_crosshair_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_crosshair_box.generic.x = 0
	y += 10; s_options_crosshair_box.generic.y = y
	s_options_crosshair_box.generic.name = "crosshair"
	s_options_crosshair_box.generic.callback = CrosshairFunc
	s_options_crosshair_box.itemnames = crosshair_names
	s_options_crosshair_color_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_options_crosshair_color_box.generic.x = 0
	y += 10; s_options_crosshair_color_box.generic.y = y
	s_options_crosshair_color_box.generic.name = "crosshair color"
	s_options_crosshair_color_box.generic.callback = CrosshairColorFunc
	s_options_crosshair_color_box.itemnames = crosshair_color_names
	y += 10
	if sdl2.show_gamepad:

		s_options_customize_joy_action.generic.type = qmenu_h.MTYPE_ACTION
		s_options_customize_joy_action.generic.x = 0
		y += 10; s_options_customize_joy_action.generic.y = y
		s_options_customize_joy_action.generic.name = "customize gamepad"
		s_options_customize_joy_action.generic.callback = CustomizeJoyFunc


	s_options_customize_options_action.generic.type = qmenu_h.MTYPE_ACTION
	s_options_customize_options_action.generic.x = 0
	y += 10; s_options_customize_options_action.generic.y = y
	s_options_customize_options_action.generic.name = "customize controls"
	s_options_customize_options_action.generic.callback = CustomizeControlsFunc
	s_options_defaults_action.generic.type = qmenu_h.MTYPE_ACTION
	s_options_defaults_action.generic.x = 0
	y += 10; s_options_defaults_action.generic.y = y
	s_options_defaults_action.generic.name = "reset defaults"
	s_options_defaults_action.generic.callback = ControlsResetDefaultsFunc
	s_options_console_action.generic.type = qmenu_h.MTYPE_ACTION
	s_options_console_action.generic.x = 0
	y += 10; s_options_console_action.generic.y = y
	s_options_console_action.generic.name = "go to console"
	s_options_console_action.generic.callback = ConsoleFunc
	ControlsSetMenuItemValues()
	qmenu.Menu_AddItem(s_options_menu, s_options_sfxvolume_slider)
	qmenu.Menu_AddItem(s_options_menu, s_options_oggvolume_slider)
	qmenu.Menu_AddItem(s_options_menu, s_options_oggenable_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_oggshuffle_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_quality_list)
	qmenu.Menu_AddItem(s_options_menu, s_options_sensitivity_slider)
	qmenu.Menu_AddItem(s_options_menu, s_options_alwaysrun_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_invertmouse_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_lookstrafe_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_freelook_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_crosshair_box)
	qmenu.Menu_AddItem(s_options_menu, s_options_crosshair_color_box)
	if sdl2.show_gamepad:

		qmenu.Menu_AddItem(s_options_menu, s_options_customize_joy_action)


	qmenu.Menu_AddItem(s_options_menu, s_options_customize_options_action)
	qmenu.Menu_AddItem(s_options_menu, s_options_defaults_action)
	qmenu.Menu_AddItem(s_options_menu, s_options_console_action)

def M_Menu_Options_f(): # (static)

	Options_MenuInit()
	s_options_menu.draw = Default_MenuDraw
	s_options_menu.key = Default_MenuKey
	M_PushMenu(s_options_menu)

credits = None #static const char **

CREDITS_SIZE	= 256
s_credits = qmenu_h.menuframework_s() #menuframework_s
credits_start_time = 0 #static int
creditsIndex = [None] * CREDITS_SIZE #static char *[CREDITS_SIZE]
creditsBuffer = None #static char *
idcredits = ["+QUAKE II BY ID SOFTWARE", "", "+PROGRAMMING", "John Carmack", "John Cash", "Brian Hook", "", "+ART", "Adrian Carmack", "Kevin Cloud", "Paul Steed", "", "+LEVEL DESIGN", "Tim Willits", "American McGee", "Christian Antkow", "Jennell Jaquays", "Brandon James", "", "+BIZ", "Todd Hollenshead", "Barrett (Bear) Alexander", "Donna Jackson", "", "", "+SPECIAL THANKS", "Ben Donges for beta testing", "", "", "", "", "", "", "+ADDITIONAL SUPPORT", "", "+LINUX PORT AND CTF", "Zoid Kirsch", "", "+CINEMATIC SEQUENCES", "Ending Cinematic by Blur Studio - ", "Venice, CA", "", "Environment models for Introduction", "Cinematic by Karl Dolgener", "", "Assistance with environment design", "by Cliff Iwai", "", "+SOUND EFFECTS AND MUSIC", "Sound Design by Soundelux Media Labs.", "Music Composed and Produced by", "Soundelux Media Labs. Special thanks", "to Bill Brown, Tom Ozanich, Brian", "Celano, Jeff Eisner, and The Soundelux", "Players.", "", "\"Level Music\" by Sonic Mayhem", "www.sonicmayhem.com", "", "\"Quake II Theme Song\"", "(C) 1997 Rob Zombie. All Rights", "Reserved.", "", "Track 10 (\"Climb\") by Jer Sypult", "", "Voice of computers by", "Carly Staehlin-Taylor", "", "+THANKS TO ACTIVISION", "+IN PARTICULAR:", "", "John Tam", "Steve Rosenthal", "Marty Stratton", "Henk Hartong", "", "+PATCHES AUTHORS", "eliasm", "", "+YAMAGI QUAKE II BY", "Yamagi Burmeister", "Daniel Gibson", "Sander van Dijk", "Denis Pauk", "Bjorn Alfredsson", "Jaime Moreira", "", "Quake II(tm) (C)1997 Id Software, Inc.", "All Rights Reserved. Distributed by", "Activision, Inc. under license.", "Quake II(tm), the Id Software name,", "the \"Q II\"(tm) logo and id(tm)", "logo are trademarks of Id Software,", "Inc. Activision(R) is a registered", "trademark of Activision, Inc. All", "other trademarks and trade names are", "properties of their respective owners.", None] #static const char *[]
xatcredits = ["+QUAKE II MISSION PACK: THE RECKONING", "+BY", "+XATRIX ENTERTAINMENT, INC.", "", "+DESIGN AND DIRECTION", "Drew Markham", "", "+PRODUCED BY", "Greg Goodrich", "", "+PROGRAMMING", "Rafael Paiz", "", "+LEVEL DESIGN / ADDITIONAL GAME DESIGN", "Alex Mayberry", "", "+LEVEL DESIGN", "Mal Blackwell", "Dan Koppel", "", "+ART DIRECTION", "Michael \"Maxx\" Kaufman", "", "+COMPUTER GRAPHICS SUPERVISOR AND", "+CHARACTER ANIMATION DIRECTION", "Barry Dempsey", "", "+SENIOR ANIMATOR AND MODELER", "Jason Hoover", "", "+CHARACTER ANIMATION AND", "+MOTION CAPTURE SPECIALIST", "Amit Doron", "", "+ART", "Claire Praderie-Markham", "Viktor Antonov", "Corky Lehmkuhl", "", "+INTRODUCTION ANIMATION", "Dominique Drozdz", "", "+ADDITIONAL LEVEL DESIGN", "Aaron Barber", "Rhett Baldwin", "", "+3D CHARACTER ANIMATION TOOLS", "Gerry Tyra, SA Technology", "", "+ADDITIONAL EDITOR TOOL PROGRAMMING", "Robert Duffy", "", "+ADDITIONAL PROGRAMMING", "Ryan Feltrin", "", "+PRODUCTION COORDINATOR", "Victoria Sylvester", "", "+SOUND DESIGN", "Gary Bradfield", "", "+MUSIC BY", "Sonic Mayhem", "", "", "", "+SPECIAL THANKS", "+TO", "+OUR FRIENDS AT ID SOFTWARE", "", "John Carmack", "John Cash", "Brian Hook", "Adrian Carmack", "Kevin Cloud", "Paul Steed", "Tim Willits", "Christian Antkow", "Jennell Jaquays", "Brandon James", "Todd Hollenshead", "Barrett (Bear) Alexander", "Zoid Kirsch", "Donna Jackson", "", "", "", "+THANKS TO ACTIVISION", "+IN PARTICULAR:", "", "Marty Stratton", "Henk \"The Original Ripper\" Hartong", "Kevin Kraff", "Jamey Gottlieb", "Chris Hepburn", "", "+AND THE GAME TESTERS", "", "Tim Vanlaw", "Doug Jacobs", "Steven Rosenthal", "David Baker", "Chris Campbell", "Aaron Casillas", "Steve Elwell", "Derek Johnstone", "Igor Krinitskiy", "Samantha Lee", "Michael Spann", "Chris Toft", "Juan Valdes", "", "+THANKS TO INTERGRAPH COMPUTER SYSTEMS", "+IN PARTICULAR:", "", "Michael T. Nicolaou", "", "", "Quake II Mission Pack: The Reckoning", "(tm) (C)1998 Id Software, Inc. All", "Rights Reserved. Developed by Xatrix", "Entertainment, Inc. for Id Software,", "Inc. Distributed by Activision Inc.", "under license. Quake(R) is a", "registered trademark of Id Software,", "Inc. Quake II Mission Pack: The", "Reckoning(tm), Quake II(tm), the Id", "Software name, the \"Q II\"(tm) logo", "and id(tm) logo are trademarks of Id", "Software, Inc. Activision(R) is a", "registered trademark of Activision,", "Inc. Xatrix(R) is a registered", "trademark of Xatrix Entertainment,", "Inc. All other trademarks and trade", "names are properties of their", "respective owners.", None] #static const char *[]
roguecredits = ["+QUAKE II MISSION PACK 2: GROUND ZERO", "+BY", "+ROGUE ENTERTAINMENT, INC.", "", "+PRODUCED BY", "Jim Molinets", "", "+PROGRAMMING", "Peter Mack", "Patrick Magruder", "", "+LEVEL DESIGN", "Jim Molinets", "Cameron Lamprecht", "Berenger Fish", "Robert Selitto", "Steve Tietze", "Steve Thoms", "", "+ART DIRECTION", "Rich Fleider", "", "+ART", "Rich Fleider", "Steve Maines", "Won Choi", "", "+ANIMATION SEQUENCES", "Creat Studios", "Steve Maines", "", "+ADDITIONAL LEVEL DESIGN", "Rich Fleider", "Steve Maines", "Peter Mack", "", "+SOUND", "James Grunke", "", "+GROUND ZERO THEME", "+AND", "+MUSIC BY", "Sonic Mayhem", "", "+VWEP MODELS", "Brent \"Hentai\" Dill", "", "", "", "+SPECIAL THANKS", "+TO", "+OUR FRIENDS AT ID SOFTWARE", "", "John Carmack", "John Cash", "Brian Hook", "Adrian Carmack", "Kevin Cloud", "Paul Steed", "Tim Willits", "Christian Antkow", "Jennell Jaquays", "Brandon James", "Todd Hollenshead", "Barrett (Bear) Alexander", "Katherine Anna Kang", "Donna Jackson", "Zoid Kirsch", "", "", "", "+THANKS TO ACTIVISION", "+IN PARTICULAR:", "", "Marty Stratton", "Henk Hartong", "Mitch Lasky", "Steve Rosenthal", "Steve Elwell", "", "+AND THE GAME TESTERS", "", "The Ranger Clan", "Zoid Kirsch", "Nihilistic Software", "Robert Duffy", "", "And Countless Others", "", "", "", "Quake II Mission Pack 2: Ground Zero", "(tm) (C)1998 Id Software, Inc. All", "Rights Reserved. Developed by Rogue", "Entertainment, Inc. for Id Software,", "Inc. Distributed by Activision Inc.", "under license. Quake(R) is a", "registered trademark of Id Software,", "Inc. Quake II Mission Pack 2: Ground", "Zero(tm), Quake II(tm), the Id", "Software name, the \"Q II\"(tm) logo", "and id(tm) logo are trademarks of Id", "Software, Inc. Activision(R) is a", "registered trademark of Activision,", "Inc. Rogue(R) is a registered", "trademark of Rogue Entertainment,", "Inc. All other trademarks and trade", "names are properties of their", "respective owners.", None] #static const char *[]

def M_Credits_Draw(m: qmenu_h.menuframework_s): #menuframework_s * (static)

	"""
	int i, y;
	"""
	global credits_start_time

	scale = cl_screen.SCR_GetMenuScale()

	# draw the credits
	i = 0
	y = int(vid.viddef.height / scale - ((cl_main.cls.realtime - credits_start_time) / 40.0))
	while credits[i] is not None and y < vid.viddef.height / scale: # for (i = 0, y = ...; credits[i] && ...; y += 10, i++)

		"""
		int j, stringoffset = 0;
		int bold = false;
		"""
		stringoffset = 0
		bold = False

		if y <= -8:

			y += 10; i += 1
			continue


		if credits[i][:1] == '+':

			bold = True
			stringoffset = 1

		else:

			bold = False
			stringoffset = 0


		for j in range(len(credits[i]) - stringoffset): # for (j = 0; credits[i][j + stringoffset]; j++)

			"""
			int x;
			"""

			x = int((vid.viddef.width / scale- len(credits[i]) * 8 - stringoffset *
				 8) / 2 + (j + stringoffset) * 8) # int x

			if bold:

				vid.Draw_CharScaled(x * scale, y * scale, ord(credits[i][j + stringoffset]) + 128, scale)


			else:

				vid.Draw_CharScaled(x * scale, y * scale, ord(credits[i][j + stringoffset]), scale)



		y += 10; i += 1


	if y < 0:

		credits_start_time = cl_main.cls.realtime


def M_Credits_Close(m): #menuframework_s * (static)

	global creditsBuffer

	if creditsBuffer:

		filesystem.FS_FreeFile(creditsBuffer)
		creditsBuffer = None

def M_Credits_Key(m, key): #menuframework_s *, int (returns static const char *)

	key = Key_GetMenuKey(key)
	if key == keyboard_h.K_ESCAPE:

		M_PopMenu(False)


	return None

def M_Menu_Credits_f(): # (static)

	"""
	int count;
	char *p;
	"""
	global creditsBuffer, credits, credits_start_time

	creditsBuffer = None
	count, creditsBuffer = filesystem.FS_LoadFile("credits")

	if count != -1:

		"""
		int n;
		"""
		# Q2PORT: the C cuts creditsBuffer into lines in place and points
		# creditsIndex at them; here the lines are strings
		text = bytes(creditsBuffer[:count]).decode("latin-1")
		p = 0 # p = creditsBuffer;

		# CREDITS_SIZE - 1 - last pointer should be NULL
		n = 0
		while n < CREDITS_SIZE - 1:

			start = p # creditsIndex[n] = p;
			stop = False

			while p < len(text) and text[p] != '\r' and text[p] != '\n':

				p += 1

				count -= 1
				if count == 0:

					break



			creditsIndex[n] = text[start:p]

			if p < len(text) and text[p] == '\r':

				p += 1 # *p++ = 0;

				count -= 1
				if count == 0:

					stop = True



			if not stop:

				p += 1 # *p++ = 0;

				count -= 1
				if count == 0:

					# no credits any more
					# move one step futher for set NULL
					n += 1
					stop = True


			if stop:

				break

			n += 1


		creditsIndex[n] = None # 0
		credits = creditsIndex # (const char **)

	else:

		if M_IsGame("xatrix"): # Xatrix - The Reckoning

			credits = xatcredits


		elif M_IsGame("rogue"): # Rogue - Ground Zero

			credits = roguecredits


		else:

			credits = idcredits



	credits_start_time = cl_main.cls.realtime

	s_credits.draw  = M_Credits_Draw
	s_credits.key   = M_Credits_Key
	s_credits.close = M_Credits_Close

	M_PushMenu(s_credits)


MODS_MAX_DISPNAMELEN	= 15
s_mods_menu = qmenu_h.menuframework_s() #static menuframework_s
s_mods_list = qmenu_h.menulist_s() #static menulist_s
s_mods_apply_action = qmenu_h.menuaction_s() #static menuaction_s
mods_statusbar = "" #static char[64]
modnames = shared.strlist_t() #static strlist_t
moddispnames = shared.strlist_t() #static strlist_t

def Mods_NamesFinish(): # (static)

	shared_c.StrList_Free(modnames)
	shared_c.StrList_Free(moddispnames)
	s_mods_list.itemnames = None

"""
 create array of bracketed display names from folder names - TG626
"""
def Mods_DisplayNamesInit(mods: shared.strlist_t)->shared.strlist_t: #const strlist_t * (returns static strlist_t)

	"""
	strlist_t list;
	int i;
	"""
	list_ = shared.strlist_t()

	shared_c.StrList_Init(list_, 0)

	for i in range(mods.num):

		"""
		const char *m;
		char dispname[MODS_MAX_DISPNAMELEN + 3];
		int len;
		"""

		dispname = "[" # strcpy

		m = mods.data[i]
		len_ = len(m)

		if len_ <= MODS_MAX_DISPNAMELEN:

			dispname += m # strcat

			for j in range(MODS_MAX_DISPNAMELEN - len_):

				dispname += " " # strcat



		else:

			dispname += m[:MODS_MAX_DISPNAMELEN - 3] # strncat(dispname, m, MODS_MAX_DISPNAMELEN - 3);
			dispname += "..." # strcat


		dispname += "]" # strcat

		shared_c.StrList_Append(list_, dispname)


	return list_


def Mods_NamesInit(): # (static)

	# initialize list of mods once, reuse it afterwards
	global moddispnames, modnames

	if not modnames.num:

		modnames = filesystem.FS_ListMods()
		moddispnames = Mods_DisplayNamesInit(modnames)
		shared_c.StrList_Compress(modnames)
		shared_c.StrList_Compress(moddispnames)

def ModsListFunc(unused): #void * (static)

	global mods_statusbar

	"""
	const char *m, *sb;
	int i;
	"""

	i = s_mods_list.curvalue
	if (i < 0) or (i >= modnames.num):

		mods_statusbar = "(invalid)" # strcpy
		s_mods_menu.statusbar = mods_statusbar # Q2PORT: see below
		return


	m = modnames.data[i]
	if (common_h.BASEDIRNAME == m):

		sb = "Quake II"

	elif ("ctf" == m):

		sb = "Quake II Capture The Flag"

	elif ("rogue" == m):

		sb = "Quake II Mission Pack: Ground Zero"

	elif ("xatrix" == m):

		sb = "Quake II Mission Pack: The Reckoning"

	else:

		sb = ""


	mods_statusbar = sb # strcpy
	s_mods_menu.statusbar = mods_statusbar # Q2PORT: the menu's statusbar points at the mods_statusbar buffer

def ModsApplyActionFunc(unused): #void * (static)

	global menu_startdemoloop

	"""
	int i = s_mods_list.curvalue;
	"""
	i = s_mods_list.curvalue

	if (i < 0) or (i >= modnames.num):

		return


	if M_IsGame(modnames.data[i]):

		return


	if clientserver.Com_ServerState():

		# equivalent to "killserver" cmd, but avoids cvar latching below
		sv_main.SV_Shutdown("Server is changing games.\n", False)
		network.NET_Config(False)


	# called via command buffer so that any running server has time to shutdown
	cmdparser.Cbuf_AddText(("game %s\n" % (modnames.data[i],)))
	# start the demo cycle in the new game directory
	menu_startdemoloop = True
	M_ForceMenuOff()

def Mods_CurrentModIndex(): # (returns static int)

	"""
	int m;
	"""

	for m in range(modnames.num):

		if M_IsGame(modnames.data[m]):

			return m


	return 0

def Mods_MenuInit(): # (static)

	x = 0
	y = 0

	Mods_NamesInit()

	s_mods_menu.x = int(vid.viddef.width * 0.50) # int x
	s_mods_menu.nitems = 0

	s_mods_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_mods_list.generic.name = "mod"
	s_mods_list.generic.x = x
	s_mods_list.generic.y = y
	s_mods_list.generic.callback = ModsListFunc
	s_mods_list.itemnames = moddispnames.data # (const char **)
	s_mods_list.curvalue = Mods_CurrentModIndex()

	y += 20

	s_mods_apply_action.generic.type = qmenu_h.MTYPE_ACTION
	s_mods_apply_action.generic.name = "apply"
	s_mods_apply_action.generic.x = x
	s_mods_apply_action.generic.y = y
	s_mods_apply_action.generic.callback = ModsApplyActionFunc

	qmenu.Menu_AddItem(s_mods_menu, s_mods_list)
	qmenu.Menu_AddItem(s_mods_menu, s_mods_apply_action)

	qmenu.Menu_Center(s_mods_menu)

	# set the original mods statusbar
	ModsListFunc(0)
	qmenu.Menu_SetStatusBar(s_mods_menu, mods_statusbar)


def M_Menu_Mods_f(): # (static)

	Mods_MenuInit()
	s_mods_menu.draw = Default_MenuDraw
	s_mods_menu.key = Default_MenuKey
	M_PushMenu(s_mods_menu)

m_game_cursor = 0 #static int
s_game_menu = qmenu_h.menuframework_s() #static menuframework_s
s_easy_game_action = qmenu_h.menuaction_s() #static menuaction_s
s_medium_game_action = qmenu_h.menuaction_s() #static menuaction_s
s_hard_game_action = qmenu_h.menuaction_s() #static menuaction_s
s_hardp_game_action = qmenu_h.menuaction_s() #static menuaction_s
s_load_game_action = qmenu_h.menuaction_s() #static menuaction_s
s_save_game_action = qmenu_h.menuaction_s() #static menuaction_s
s_credits_action = qmenu_h.menuaction_s() #static menuaction_s
s_mods_action = qmenu_h.menuaction_s() #static menuaction_s
s_blankline = qmenu_h.menuseparator_s() #static menuseparator_s

def StartGame(): # (static)

	if cl_main.cls.state != client_h.connstate_t.ca_disconnected and cl_main.cls.state != client_h.connstate_t.ca_uninitialized:

		cl_network.CL_Disconnect()


	# disable updates and start the cinematic going
	cl_main.cl.servercount = -1
	M_ForceMenuOff()
	cvar.Cvar_SetValue("deathmatch", 0)
	cvar.Cvar_SetValue("coop", 0)
	cmdparser.Cbuf_AddText("loading ; killserver ; wait ; newgame\n")
	cl_main.cls.key_dest = client_h.keydest_t.key_game

def EasyGameFunc(data): #void * (static)

	cvar.Cvar_ForceSet("skill", "0")
	StartGame()

def MediumGameFunc(data): #void * (static)

	cvar.Cvar_ForceSet("skill", "1")
	StartGame()

def HardGameFunc(data): #void * (static)

	cvar.Cvar_ForceSet("skill", "2")
	StartGame()

def HardpGameFunc(data): #void * (static)

	cvar.Cvar_ForceSet("skill", "3")
	StartGame()

def LoadGameFunc(unused): #void * (static)

	M_Menu_LoadGame_f()

def SaveGameFunc(unused): #void * (static)

	M_Menu_SaveGame_f()

def CreditsFunc(unused): #void * (static)

	M_Menu_Credits_f()

def ModsFunc(unused): #void * (static)

	M_Menu_Mods_f()

def Game_MenuInit(): # (static)

	Mods_NamesInit()
	s_game_menu.x = int(vid.viddef.width * 0.50)
	s_game_menu.nitems = 0
	s_game_menu.banner = "m_banner_game"
	s_easy_game_action.generic.type = qmenu_h.MTYPE_ACTION
	s_easy_game_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_easy_game_action.generic.x = 0
	s_easy_game_action.generic.y = 0
	s_easy_game_action.generic.name = "easy"
	s_easy_game_action.generic.callback = EasyGameFunc
	s_medium_game_action.generic.type = qmenu_h.MTYPE_ACTION
	s_medium_game_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_medium_game_action.generic.x = 0
	s_medium_game_action.generic.y = 10
	s_medium_game_action.generic.name = "medium"
	s_medium_game_action.generic.callback = MediumGameFunc
	s_hard_game_action.generic.type = qmenu_h.MTYPE_ACTION
	s_hard_game_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_hard_game_action.generic.x = 0
	s_hard_game_action.generic.y = 20
	s_hard_game_action.generic.name = "hard"
	s_hard_game_action.generic.callback = HardGameFunc
	s_hardp_game_action.generic.type = qmenu_h.MTYPE_ACTION
	s_hardp_game_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_hardp_game_action.generic.x = 0
	s_hardp_game_action.generic.y = 30
	s_hardp_game_action.generic.name = "hard+"
	s_hardp_game_action.generic.callback = HardpGameFunc
	s_blankline.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_load_game_action.generic.type = qmenu_h.MTYPE_ACTION
	s_load_game_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_load_game_action.generic.x = 0
	s_load_game_action.generic.y = 50
	s_load_game_action.generic.name = "load game"
	s_load_game_action.generic.callback = LoadGameFunc
	s_save_game_action.generic.type = qmenu_h.MTYPE_ACTION
	s_save_game_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_save_game_action.generic.x = 0
	s_save_game_action.generic.y = 60
	s_save_game_action.generic.name = "save game"
	s_save_game_action.generic.callback = SaveGameFunc
	s_credits_action.generic.type = qmenu_h.MTYPE_ACTION
	s_credits_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_credits_action.generic.x = 0
	s_credits_action.generic.y = 70
	s_credits_action.generic.name = "credits"
	s_credits_action.generic.callback = CreditsFunc
	qmenu.Menu_AddItem(s_game_menu, s_easy_game_action)
	qmenu.Menu_AddItem(s_game_menu, s_medium_game_action)
	qmenu.Menu_AddItem(s_game_menu, s_hard_game_action)
	qmenu.Menu_AddItem(s_game_menu, s_hardp_game_action)
	qmenu.Menu_AddItem(s_game_menu, s_blankline)
	qmenu.Menu_AddItem(s_game_menu, s_load_game_action)
	qmenu.Menu_AddItem(s_game_menu, s_save_game_action)
	qmenu.Menu_AddItem(s_game_menu, s_credits_action)
	if modnames.num > 1:

		s_mods_action.generic.type = qmenu_h.MTYPE_ACTION
		s_mods_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
		s_mods_action.generic.x = 0
		s_mods_action.generic.y = 90
		s_mods_action.generic.name = "mods"
		s_mods_action.generic.callback = ModsFunc
		qmenu.Menu_AddItem(s_game_menu, s_blankline)
		qmenu.Menu_AddItem(s_game_menu, s_mods_action)


	qmenu.Menu_Center(s_game_menu)

def M_Menu_Game_f(): # (static)
	global m_game_cursor

	Game_MenuInit()
	s_game_menu.draw = Default_MenuDraw
	s_game_menu.key = Default_MenuKey
	M_PushMenu(s_game_menu)
	m_game_cursor = 1

MAX_SAVESLOTS	= 14
MAX_SAVEPAGES	= 4
m_quicksavestring = "" #static char[32]
m_quicksavevalid = False #static qboolean
m_savestrings = ["" for i in range(MAX_SAVESLOTS)] #static char[MAX_SAVESLOTS][32]
m_savevalid = [False] * MAX_SAVESLOTS #static qboolean[MAX_SAVESLOTS]
m_loadsave_page = 0 #static int
m_loadsave_statusbar = "" #static char[32]
s_loadgame_menu = qmenu_h.menuframework_s() #static menuframework_s
s_loadgame_actions = [qmenu_h.menuaction_s() for i in range(MAX_SAVESLOTS + 1)] #static menuaction_s[MAX_SAVESLOTS+1]
s_savegame_menu = qmenu_h.menuframework_s() #static menuframework_s
s_savegame_actions = [qmenu_h.menuaction_s() for i in range(MAX_SAVESLOTS + 1)] #static menuaction_s[MAX_SAVESLOTS+1]
menukeyitem_delete = False #static qboolean

def PromptDeleteSaveFunc(m): #menuframework_s * (static)
	global menukeyitem_delete

	"""
	const menucommon_s *item = Menu_ItemAtCursor(m);
	"""
	item = qmenu.Menu_ItemAtCursor(m)

	if item == None or item.type != qmenu_h.MTYPE_ACTION:

		return


	if item.localdata[0] == -1:

		if m_quicksavevalid:

			menukeyitem_delete = True


	else:

		if m_savevalid[item.localdata[0] - m_loadsave_page * MAX_SAVESLOTS]:

			menukeyitem_delete = True


	if menukeyitem_delete:

		qmenu.Menu_SetStatusBar(m, "are you sure you want to delete? y\\n")

def ExecDeleteSaveFunc(m, menu_key): #menuframework_s *, int (returns static qboolean)
	global menukeyitem_delete

	"""
	menucommon_s *item = Menu_ItemAtCursor(m);
	"""
	item = qmenu.Menu_ItemAtCursor(m)

	menukeyitem_delete = False
	if menu_key == keyboard_h.K_ENTER or menu_key == 121 or menu_key == 89:

		#char name[MAX_OSPATH] = {0};
		name = [None] * shared.MAX_OSPATH
		if item.localdata[0] == -1:

			# quicksave
			name = "%s/save/quick/" % (filesystem.FS_Gamedir(),) # Com_sprintf

		else:

			name = "%s/save/save%d/" % (filesystem.FS_Gamedir(), item.localdata[0],) # Com_sprintf


		system.Sys_RemoveDir(name)
		return True


	qmenu.Menu_SetStatusBar(m, m_loadsave_statusbar)
	return False

def Create_Savestrings(): # (static)

	"""
	int i;
	fileHandle_t f;
	"""
	global m_quicksavestring, m_quicksavevalid

	# The quicksave slot...
	_, f = filesystem.FS_FOpenFile("save/quick/server.ssv", True)

	if not f:

		m_quicksavestring = "QUICKSAVE <empty>" # strcpy
		m_quicksavevalid = False

	else:

		#char tmp[32]; // Same length as m_quicksavestring-

		tmp = filesystem.FS_Read(32, f) # FS_Read(tmp, sizeof(tmp), f);
		filesystem.FS_FCloseFile(f)
		tmp = bytes(tmp[:31]).split(b"\0")[0].decode("latin-1") # tmp[sizeof(tmp) - 1] = 0;

		if len(tmp) > 12:

			# Horrible hack to construct a nice looking 'QUICKSAVE Level Name'
			# comment string matching the 'ENTERING Level Name' comment string
			# of autosaves. The comment field is in format 'HH:MM mm:dd  Level
			# Name'. Remove the date (the first 13) characters and replace it
			# with 'QUICKSAVE'.
			m_quicksavestring = ("QUICKSAVE %s" % (tmp[13:],))[:31] # Com_sprintf

		else:

			m_quicksavestring = tmp[:31] # Q_strlcpy

		m_quicksavevalid = True


	# ... and everything else.
	for i in range(MAX_SAVESLOTS):

		#char name[MAX_OSPATH];

		name = "save/save%i/server.ssv" % (m_loadsave_page * MAX_SAVESLOTS + i,) # Com_sprintf
		_, f = filesystem.FS_FOpenFile(name, True)

		if not f:

			m_savestrings[i] = "<empty>" # strcpy
			m_savevalid[i] = False

		else:

			m_savestrings[i] = bytes(filesystem.FS_Read(32, f)).split(b"\0")[0].decode("latin-1") # FS_Read(m_savestrings[i], sizeof(m_savestrings[i]), f);
			filesystem.FS_FCloseFile(f)
			m_savevalid[i] = True


def LoadSave_AdjustPage(dir_: int): #int (static)

	"""
	int i;
	"""
	global m_loadsave_page, m_loadsave_statusbar

	m_loadsave_page += dir_

	if m_loadsave_page >= MAX_SAVEPAGES:

		m_loadsave_page = 0

	elif m_loadsave_page < 0:

		m_loadsave_page = MAX_SAVEPAGES - 1


	m_loadsave_statusbar = "pages: " # strcpy

	for i in range(MAX_SAVEPAGES):

		"""
		char *str;
		"""
		str_ = "%c%d%c" % (
				'[' if i == m_loadsave_page else ' ',
				i + 1,
				']' if i == m_loadsave_page else ' ') # va

		if (len(m_loadsave_statusbar) + len(str_) >=
			32): # sizeof(m_loadsave_statusbar)

			break


		m_loadsave_statusbar += str_ # Q_strlcat


def LoadGameCallback(self): #void * (static)

	"""
	menuaction_s *a = (menuaction_s *)self;
	"""
	a = self

	if a.generic.localdata[0] == -1:

		cmdparser.Cbuf_AddText("load quick\n")

	else:

		cmdparser.Cbuf_AddText(("load save%i\n" % (a.generic.localdata[0],)))


	M_ForceMenuOff()

def LoadGame_MenuInit(): # (static)

	"""
	int i;
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	s_loadgame_menu.x = int(vid.viddef.width / 2 - (120 * scale)) # int x
	s_loadgame_menu.y = int(vid.viddef.height / (2 * scale) - 58) # int y
	s_loadgame_menu.banner = "m_banner_load_game"
	s_loadgame_menu.nitems = 0
	Create_Savestrings()
	# The quicksave slot...
	s_loadgame_actions[0].generic.type = qmenu_h.MTYPE_ACTION
	s_loadgame_actions[0].generic.name = m_quicksavestring
	s_loadgame_actions[0].generic.x = 0
	s_loadgame_actions[0].generic.y = 0
	s_loadgame_actions[0].generic.localdata[0] = -1
	s_loadgame_actions[0].generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	if not m_quicksavevalid:

		s_loadgame_actions[0].generic.callback = None

	else:

		s_loadgame_actions[0].generic.callback = LoadGameCallback


	qmenu.Menu_AddItem(s_loadgame_menu, s_loadgame_actions[0])
	# ...and everything else.
	for i in range(MAX_SAVESLOTS):

		s_loadgame_actions[i + 1].generic.type = qmenu_h.MTYPE_ACTION
		s_loadgame_actions[i + 1].generic.name = m_savestrings[i]
		s_loadgame_actions[i + 1].generic.x = 0
		s_loadgame_actions[i + 1].generic.y = i * 10 + 20
		s_loadgame_actions[i + 1].generic.localdata[0] = i + m_loadsave_page * MAX_SAVESLOTS
		s_loadgame_actions[i + 1].generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
		if not m_savevalid[i]:

			s_loadgame_actions[i + 1].generic.callback = None

		else:

			s_loadgame_actions[i + 1].generic.callback = LoadGameCallback


		qmenu.Menu_AddItem(s_loadgame_menu, s_loadgame_actions[i + 1])


	qmenu.Menu_SetStatusBar(s_loadgame_menu, m_loadsave_statusbar)

def LoadGame_MenuKey(m, key): #menuframework_s *, int (returns static const char *)

	"""
	int menu_key = Key_GetMenuKey(key);
	"""
	menu_key = Key_GetMenuKey(key)

	if menukeyitem_delete:

		if ExecDeleteSaveFunc(m, menu_key):

			LoadGame_MenuInit()


		return qmenu.menu_move_sound


	if menu_key == keyboard_h.K_UPARROW:

		if m.cursor == 0:

			LoadSave_AdjustPage(-1)
			LoadGame_MenuInit()


	elif menu_key == keyboard_h.K_DOWNARROW:

		if m.cursor == m.nitems - 1:

			LoadSave_AdjustPage(1)
			LoadGame_MenuInit()


	elif menu_key == keyboard_h.K_LEFTARROW:

		LoadSave_AdjustPage(-1)
		LoadGame_MenuInit()
		return qmenu.menu_move_sound

	elif menu_key == keyboard_h.K_RIGHTARROW:

		LoadSave_AdjustPage(1)
		LoadGame_MenuInit()
		return qmenu.menu_move_sound

	elif menu_key == keyboard_h.K_DEL or menu_key == keyboard_h.K_BACKSPACE:

		PromptDeleteSaveFunc(m)
		return qmenu.menu_move_sound

	else:

		s_savegame_menu.cursor = s_loadgame_menu.cursor


	return Default_MenuKey(m, key)

def M_Menu_LoadGame_f(): # (static)

	LoadSave_AdjustPage(0)
	LoadGame_MenuInit()
	s_loadgame_menu.draw = Default_MenuDraw
	s_loadgame_menu.key = LoadGame_MenuKey
	M_PushMenu(s_loadgame_menu)

def SaveGameCallback(self): #void * (static)

	"""
	menuaction_s *a = (menuaction_s *)self;
	"""
	a = self

	if a.generic.localdata[0] == -1:

		qmenu.Menu_StartPopup(m_popup, "This slot is reserved for\n" "quicksaving, so please select\n" "another one.", 2000)
		qmenu.Menu_DrawPopup(320, 240, m_popup)
		return


	if a.generic.localdata[0] == 0:

		qmenu.Menu_StartPopup(m_popup, "This slot is reserved for\n" "autosaving, so please select\n" "another one.", 2000)
		qmenu.Menu_DrawPopup(320, 240, m_popup)
		return


	cmdparser.Cbuf_AddText(("save save%i\n" % (a.generic.localdata[0],)))
	M_ForceMenuOff()

def SaveGame_MenuInit(): # (static)

	"""
	int i;
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	s_savegame_menu.x = int(vid.viddef.width / 2 - (120 * scale)) # int x
	s_savegame_menu.y = int(vid.viddef.height / (2 * scale) - 58) # int y
	s_savegame_menu.banner = "m_banner_save_game"
	s_savegame_menu.nitems = 0
	Create_Savestrings()
	# The quicksave slot...
	s_savegame_actions[0].generic.type = qmenu_h.MTYPE_ACTION
	s_savegame_actions[0].generic.name = m_quicksavestring
	s_savegame_actions[0].generic.x = 0
	s_savegame_actions[0].generic.y = 0
	s_savegame_actions[0].generic.localdata[0] = -1
	s_savegame_actions[0].generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_savegame_actions[0].generic.callback = SaveGameCallback
	qmenu.Menu_AddItem(s_savegame_menu, s_savegame_actions[0])
	# ...and everything else.
	for i in range(MAX_SAVESLOTS):

		s_savegame_actions[i + 1].generic.type = qmenu_h.MTYPE_ACTION
		s_savegame_actions[i + 1].generic.name = m_savestrings[i]
		s_savegame_actions[i + 1].generic.x = 0
		s_savegame_actions[i + 1].generic.y = i * 10 + 20
		s_savegame_actions[i + 1].generic.localdata[0] = i + m_loadsave_page * MAX_SAVESLOTS
		s_savegame_actions[i + 1].generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
		s_savegame_actions[i + 1].generic.callback = SaveGameCallback
		qmenu.Menu_AddItem(s_savegame_menu, s_savegame_actions[i + 1])


	qmenu.Menu_SetStatusBar(s_savegame_menu, m_loadsave_statusbar)

def SaveGame_MenuKey(m, key): #menuframework_s *, int (returns static const char *)

	"""
	int menu_key = Key_GetMenuKey(key);
	"""
	menu_key = Key_GetMenuKey(key)

	if qmenu_h.Menu_PopupActive(m_popup):

		qmenu_h.Menu_ClosePopup(m_popup)
		return None


	if menukeyitem_delete:

		if ExecDeleteSaveFunc(m, menu_key):

			SaveGame_MenuInit()


		return qmenu.menu_move_sound


	if menu_key == keyboard_h.K_UPARROW:

		if m.cursor == 0:

			LoadSave_AdjustPage(-1)
			SaveGame_MenuInit()


	elif menu_key == keyboard_h.K_DOWNARROW:

		if m.cursor == m.nitems - 1:

			LoadSave_AdjustPage(1)
			SaveGame_MenuInit()


	elif menu_key == keyboard_h.K_LEFTARROW:

		LoadSave_AdjustPage(-1)
		SaveGame_MenuInit()
		return qmenu.menu_move_sound

	elif menu_key == keyboard_h.K_RIGHTARROW:

		LoadSave_AdjustPage(1)
		SaveGame_MenuInit()
		return qmenu.menu_move_sound

	elif menu_key == keyboard_h.K_DEL or menu_key == keyboard_h.K_BACKSPACE:

		PromptDeleteSaveFunc(m)
		return qmenu.menu_move_sound

	else:

		s_loadgame_menu.cursor = s_savegame_menu.cursor


	return Default_MenuKey(m, key)

def M_Menu_SaveGame_f(): # (static)

	if not clientserver.Com_ServerState():

		return
		# not playing a game


	LoadSave_AdjustPage(0)
	SaveGame_MenuInit()
	s_savegame_menu.draw = Default_MenuDraw
	s_savegame_menu.key = SaveGame_MenuKey
	M_PushMenu(s_savegame_menu)

MAX_LOCAL_SERVERS	= 8
NO_SERVER_STRING	= "<no server>"
s_joinserver_menu = qmenu_h.menuframework_s() #static menuframework_s
s_joinserver_server_title = qmenu_h.menuseparator_s() #static menuseparator_s
s_joinserver_search_action = qmenu_h.menuaction_s() #static menuaction_s
s_joinserver_address_book_action = qmenu_h.menuaction_s() #static menuaction_s
s_joinserver_server_actions = [qmenu_h.menuaction_s() for i in range(MAX_LOCAL_SERVERS)] #static menuaction_s[MAX_LOCAL_SERVERS]
m_num_servers = 0 #int
local_server_netadr = [common_h.netadr_t() for i in range(MAX_LOCAL_SERVERS)] #static netadr_t[MAX_LOCAL_SERVERS]
local_server_names = ["" for i in range(MAX_LOCAL_SERVERS)] #static char[MAX_LOCAL_SERVERS][80]
local_server_netadr_strings = ["" for i in range(MAX_LOCAL_SERVERS)] #static char[MAX_LOCAL_SERVERS][80]

def M_AddToServerList(adr, info: str): #netadr_t, char *

	"""
	const char *s;
	int i;
	"""
	global m_num_servers

	if m_num_servers == MAX_LOCAL_SERVERS:

		return


	info = info.lstrip(' ') # while (*info == ' ') info++;

	s = network.NET_AdrToString(adr)

	# ignore if duplicated
	for i in range(m_num_servers):

		if (local_server_names[i] == info and
			local_server_netadr_strings[i] == s):

			return



	local_server_netadr[m_num_servers] = copy.copy(adr) # struct copy
	local_server_names[m_num_servers] = info[:79] # Q_strlcpy
	local_server_netadr_strings[m_num_servers] = s[:79] # Q_strlcpy
	s_joinserver_server_actions[m_num_servers].generic.name = local_server_names[m_num_servers] # Q2PORT: the action's name points at the local_server_names buffer
	m_num_servers += 1


def JoinServerFunc(self): #void * (static)

	"""
	char buffer[128];
	int index;
	"""
	buffer = [None] * 128

	index = int(self - s_joinserver_server_actions)
	if shared_c.Q_stricmp(local_server_names[index], NO_SERVER_STRING) == 0:

		return


	if index >= m_num_servers:

		return


	buffer = "connect %s\n" % (network.NET_AdrToString(local_server_netadr[index]),) # Com_sprintf
	cmdparser.Cbuf_AddText(buffer)
	M_ForceMenuOff()

def AddressBookFunc(self): #void * (static)

	M_Menu_AddressBook_f()

def SearchLocalGames(): # (static)

	global m_num_servers

	"""
	int i;
	"""

	m_num_servers = 0
	for i in range(MAX_LOCAL_SERVERS):

		local_server_names[i] = NO_SERVER_STRING # strcpy
		local_server_netadr_strings[i] = "" # local_server_netadr_strings[i][0] = 0;


	qmenu.Menu_StartPopup(m_popup, "Searching for local servers. This\n" "could take up to a minute, so\n" "please be patient.", 2000)
	qmenu.Menu_DrawPopup(320, 240, m_popup)
	# the text box won't show up unless we do a buffer swap
	vid.R_EndFrame()
	# send out info packets
	cl_network.CL_PingServers_f()

def SearchLocalGamesFunc(self): #void * (static)

	SearchLocalGames()

def JoinServer_MenuInit(): # (static)

	"""
	int i;
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	s_joinserver_menu.x = int(int(vid.viddef.width * 0.50) - 120 * scale) # int x
	s_joinserver_menu.nitems = 0
	s_joinserver_menu.banner = "m_banner_join_server"
	s_joinserver_address_book_action.generic.type = qmenu_h.MTYPE_ACTION
	s_joinserver_address_book_action.generic.name = "address book"
	s_joinserver_address_book_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_joinserver_address_book_action.generic.x = 0
	s_joinserver_address_book_action.generic.y = 0
	s_joinserver_address_book_action.generic.callback = AddressBookFunc
	s_joinserver_search_action.generic.type = qmenu_h.MTYPE_ACTION
	s_joinserver_search_action.generic.name = "refresh server list"
	s_joinserver_search_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_joinserver_search_action.generic.x = 0
	s_joinserver_search_action.generic.y = 10
	s_joinserver_search_action.generic.callback = SearchLocalGamesFunc
	s_joinserver_search_action.generic.statusbar = "search for servers"
	s_joinserver_server_title.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_joinserver_server_title.generic.name = "connect to..."
	s_joinserver_server_title.generic.y = 30
	s_joinserver_server_title.generic.x = int(80 * scale) # int x
	for i in range(MAX_LOCAL_SERVERS):

		s_joinserver_server_actions[i].generic.type = qmenu_h.MTYPE_ACTION
		s_joinserver_server_actions[i].generic.name = local_server_names[i]
		s_joinserver_server_actions[i].generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
		s_joinserver_server_actions[i].generic.x = 0
		s_joinserver_server_actions[i].generic.y = 40 + i * 10
		s_joinserver_server_actions[i].generic.callback = JoinServerFunc
		s_joinserver_server_actions[i].generic.statusbar = local_server_netadr_strings[i]


	qmenu.Menu_AddItem(s_joinserver_menu, s_joinserver_address_book_action)
	qmenu.Menu_AddItem(s_joinserver_menu, s_joinserver_server_title)
	qmenu.Menu_AddItem(s_joinserver_menu, s_joinserver_search_action)
	for i in range(8):

		qmenu.Menu_AddItem(s_joinserver_menu, s_joinserver_server_actions[i])


	qmenu.Menu_Center(s_joinserver_menu)
	SearchLocalGames()

def M_Menu_JoinServer_f(): # (static)

	JoinServer_MenuInit()
	s_joinserver_menu.draw = Default_MenuDraw
	s_joinserver_menu.key = Default_MenuKey
	M_PushMenu(s_joinserver_menu)

s_startserver_menu = qmenu_h.menuframework_s() #static menuframework_s
maplist = shared.strlist_t() #static strlist_t
s_startserver_start_action = qmenu_h.menuaction_s() #static menuaction_s
s_startserver_dmoptions_action = qmenu_h.menuaction_s() #static menuaction_s
s_timelimit_field = qmenu_h.menufield_s() #static menufield_s
s_fraglimit_field = qmenu_h.menufield_s() #static menufield_s
s_capturelimit_field = qmenu_h.menufield_s() #static menufield_s
s_maxclients_field = qmenu_h.menufield_s() #static menufield_s
s_hostname_field = qmenu_h.menufield_s() #static menufield_s
s_startmap_list = qmenu_h.menulist_s() #static menulist_s
s_rules_box = qmenu_h.menulist_s() #static menulist_s

def DMOptionsFunc(self): #void * (static)

	M_Menu_DMOptions_f()

def RulesChangeFunc(self): #void * (static)

	# Deathmatch
	if s_rules_box.curvalue == 0:

		s_maxclients_field.generic.statusbar = None
		s_startserver_dmoptions_action.generic.statusbar = None

	elif M_IsGame("rogue"):

		if s_rules_box.curvalue == 2:

			s_maxclients_field.generic.statusbar = None
			s_startserver_dmoptions_action.generic.statusbar = None

GetStartSpot_spots = [ #static const char *[], in GetStartSpot
	"bunk1", "start",
	"mintro", "start",
	"fact1", "start",
	"power1", "pstart",
	"biggun", "bstart",
	"hangar1", "unitstart",
	"city1", "unitstart",
	"boss1", "bosstart"
]

def GetStartSpot(startmap: str): #const char * (returns static const char *)

	"""
	const char **s;
	"""
	spots = GetStartSpot_spots

	for s in range(0, len(spots), 2): # for (s = spots; s < ARREND(spots); s += 2)

		if not shared_c.Q_stricmp(startmap, spots[s]):

			return spots[s + 1]



	return None


def StartServerActionFunc(self): #void * (static)

	"""
	const char *startmap, *spot;
	float timelimit;
	float fraglimit;
	float maxclients;
	"""

	if s_startmap_list.curvalue >= maplist.num:

		return


	startmap = maplist.data[s_startmap_list.curvalue]
	nl = startmap.find('\n') # strchr(..., '\n')

	if nl < 0:

		return


	startmap = startmap[nl + 1:] # startmap++;

	maxclients = shared_c.atof(s_maxclients_field.buffer) # (float)strtod(..., (char **)NULL)
	timelimit = shared_c.atof(s_timelimit_field.buffer)
	fraglimit = shared_c.atof(s_fraglimit_field.buffer)

	if M_IsGame("ctf"):

		"""
		float capturelimit;
		"""

		capturelimit = shared_c.atof(s_capturelimit_field.buffer)
		cvar.Cvar_SetValue("capturelimit", qmenu.ClampCvar(0, capturelimit, capturelimit))


	cvar.Cvar_SetValue("maxclients", qmenu.ClampCvar(0, maxclients, maxclients))
	cvar.Cvar_SetValue("timelimit", qmenu.ClampCvar(0, timelimit, timelimit))
	cvar.Cvar_SetValue("fraglimit", qmenu.ClampCvar(0, fraglimit, fraglimit))
	cvar.Cvar_Set("hostname", s_hostname_field.buffer)

	cvar.Cvar_SetValue("singleplayer", 0)

	if (s_rules_box.curvalue < 2) or M_IsGame("rogue"):

		cvar.Cvar_SetValue("deathmatch", float(not s_rules_box.curvalue))
		cvar.Cvar_SetValue("coop", float(s_rules_box.curvalue))

	else:

		cvar.Cvar_SetValue("deathmatch", 1) # deathmatch is always true for rogue games
		cvar.Cvar_SetValue("coop", 0) # This works for at least the main game and both addons


	spot = None

	if s_rules_box.curvalue == 1:

		spot = GetStartSpot(startmap)


	if spot:

		if clientserver.Com_ServerState():

			cmdparser.Cbuf_AddText("disconnect\n")


		cmdparser.Cbuf_AddText("gamemap \"*%s$%s\"\n" % (startmap, spot))

	else:

		cmdparser.Cbuf_AddText("map %s\n" % (startmap,))


	M_ForceMenuOff()


def CleanCachedMapsList(): #

	shared_c.StrList_Free(maplist)
	s_startmap_list.itemnames = None

def MapsInLst()->shared.strlist_t: # (returns static strlist_t)

	"""
	strlist_t list;
	char *buffer;
	"""
	list_ = shared.strlist_t()

	shared_c.StrList_Init(list_, 0)

	length, buffer = filesystem.FS_LoadFile("maps.lst")
	if length > 0:

		buffer = bytes(buffer[:length]).decode("latin-1")
		bufpos = 0 # bufpos = buffer;

		while bufpos is not None:

			"""
			char shortname[64];
			char scratch[128];
			const char *s;
			"""

			s, bufpos = shared_c.COM_Parse(buffer, bufpos)
			if not s:

				break


			if len(s) >= 64: # Q_strlcpy(shortname, s, sizeof(shortname)) >= sizeof(shortname)

				continue

			shortname = s.upper() # Q_strupr(shortname);

			s, bufpos = shared_c.COM_Parse(buffer, bufpos)
			if not s:

				break


			scratch = "%.*s\n%s" % (63, s, shortname)
			if len(scratch) < 128: # snprintf(scratch, sizeof(scratch), ...) < sizeof(scratch)

				shared_c.StrList_Append(list_, scratch)




	#FS_FreeFile(buffer);

	return list_


def ls_mapeq(list_s: str, targ_s: str)->int: #const char *, const char * (returns static int)

	slash = list_s.find('\n') # strchr(list_s, '\n')

	return 0 if (slash < 0) else shared_c.Q_stricmp(targ_s, list_s[slash + 1:])


"""
 Add bsp files in maps/ dir to list
"""
def MapsInFolder(maps: shared.strlist_t): #strlist_t * (static)

	"""
	strlist_t list;
	int i;
	"""

	list_ = filesystem.FS_ListFiles2("maps/*.bsp", 0, 0)

	for i in range(list_.num):

		"""
		char scratch[128];
		const char *s;
		size_t len;
		"""

		len_ = len(list_.data[i])
		# maps/ + .bsp
		if len_ <= 9 or len_ > (63+9):

			continue


		list_.data[i] = list_.data[i][:len_ - 4] # list.data[i][len - 4]  = '\0';

		s = list_.data[i][5:]

		if shared.StrList_Contains2(maps, ls_mapeq, s):

			continue


		scratch = "%s\n%s" % (s, s)
		if len(scratch) < 128: # snprintf(scratch, sizeof(scratch), ...) < sizeof(scratch)

			shared_c.StrList_Append(maps, scratch)



	shared_c.StrList_Free(list_)


StartServer_MenuInit_dm_coop_names = [ #static const char *[], in StartServer_MenuInit
	"deathmatch",
	"cooperative",
	None
]
StartServer_MenuInit_dm_coop_names_rogue = [ #static const char *[], in StartServer_MenuInit
	"deathmatch",
	"cooperative",
	"tag",
	None
]

def StartServer_MenuInit(): # (static)

	"""
	int y;
	"""
	global maplist

	dm_coop_names = StartServer_MenuInit_dm_coop_names
	dm_coop_names_rogue = StartServer_MenuInit_dm_coop_names_rogue

	scale = cl_screen.SCR_GetMenuScale()

	# initialize list of maps once, reuse it afterwards (=> it isn't freed unless the game dir is changed)
	if not maplist.num:

		s_startmap_list.curvalue = 0

		maplist = MapsInLst()

		MapsInFolder(maplist)

		shared_c.StrList_Compress(maplist)

		if not maplist.num:

			qmenu.Menu_StartPopup(m_popup, "No maps were found\nin maps.lst or folders", 2000)



	# initialize the menu stuff
	s_startserver_menu.x = int(vid.viddef.width * 0.50)
	s_startserver_menu.banner = "m_banner_start_server"
	s_startserver_menu.nitems = 0

	y = 18
	s_startmap_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_startmap_list.generic.x = 0
	s_startmap_list.generic.y = y
	s_startmap_list.generic.name = "initial map"
	s_startmap_list.itemnames = maplist.data # (const char **)

	if M_IsGame("ctf"):

		y += 26
		s_capturelimit_field.generic.type = qmenu_h.MTYPE_FIELD
		s_capturelimit_field.generic.name = "capture limit"
		s_capturelimit_field.generic.flags = qmenu_h.QMF_NUMBERSONLY
		s_capturelimit_field.generic.x = 0
		s_capturelimit_field.generic.y = y
		s_capturelimit_field.generic.statusbar = "0 = no limit"
		qmenu.Field_InitState(s_capturelimit_field,
			cvar.Cvar_VariableString("capturelimit"), 3, 3)

	else:

		y += 20
		s_rules_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_rules_box.generic.x = 0
		s_rules_box.generic.y = y
		s_rules_box.generic.name = "rules"

		# Ground Zero games only available with rogue game
		if M_IsGame("rogue"):

			s_rules_box.itemnames = dm_coop_names_rogue

		else:

			s_rules_box.itemnames = dm_coop_names


		if cvar.Cvar_VariableValue("coop"):

			s_rules_box.curvalue = 1

		else:

			s_rules_box.curvalue = 0


		s_rules_box.generic.callback = RulesChangeFunc


	y += 18
	s_timelimit_field.generic.type = qmenu_h.MTYPE_FIELD
	s_timelimit_field.generic.name = "time limit"
	s_timelimit_field.generic.flags = qmenu_h.QMF_NUMBERSONLY
	s_timelimit_field.generic.x = 0
	s_timelimit_field.generic.y = y
	s_timelimit_field.generic.statusbar = "0 = no limit"
	qmenu.Field_InitState(s_timelimit_field,
		cvar.Cvar_VariableString("timelimit"), 3, 3)

	y += 18
	s_fraglimit_field.generic.type = qmenu_h.MTYPE_FIELD
	s_fraglimit_field.generic.name = "frag limit"
	s_fraglimit_field.generic.flags = qmenu_h.QMF_NUMBERSONLY
	s_fraglimit_field.generic.x = 0
	s_fraglimit_field.generic.y = y
	s_fraglimit_field.generic.statusbar = "0 = no limit"
	qmenu.Field_InitState(s_fraglimit_field,
		cvar.Cvar_VariableString("fraglimit"), 3, 3)

	# maxclients determines the maximum number of players that can join
	# the game. If maxclients is only "1" then we should default the menu
	# option to 8 players, otherwise use whatever its current value is.
	# Clamping will be done when the server is actually started.
	y += 18
	s_maxclients_field.generic.type = qmenu_h.MTYPE_FIELD
	s_maxclients_field.generic.name = "max players"
	s_maxclients_field.generic.flags = qmenu_h.QMF_NUMBERSONLY
	s_maxclients_field.generic.x = 0
	s_maxclients_field.generic.y = y
	s_maxclients_field.generic.statusbar = None
	qmenu.Field_InitState(s_maxclients_field,
		"8" if cvar.Cvar_VariableValue("maxclients") == 1 else cvar.Cvar_VariableString("maxclients"), 3, 3)

	y += 18
	s_hostname_field.generic.type = qmenu_h.MTYPE_FIELD
	s_hostname_field.generic.name = "hostname"
	s_hostname_field.generic.flags = 0
	s_hostname_field.generic.x = 0
	s_hostname_field.generic.y = y
	s_hostname_field.generic.statusbar = None
	qmenu.Field_InitState(s_hostname_field,
		cvar.Cvar_VariableString("hostname"), 12, 12)

	y += 18
	s_startserver_dmoptions_action.generic.type = qmenu_h.MTYPE_ACTION
	s_startserver_dmoptions_action.generic.name = " deathmatch flags"
	s_startserver_dmoptions_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_startserver_dmoptions_action.generic.x = int(24 * scale) # int x
	s_startserver_dmoptions_action.generic.y = y
	s_startserver_dmoptions_action.generic.statusbar = None
	s_startserver_dmoptions_action.generic.callback = DMOptionsFunc

	y += 20
	s_startserver_start_action.generic.type = qmenu_h.MTYPE_ACTION
	s_startserver_start_action.generic.name = " begin"
	s_startserver_start_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_startserver_start_action.generic.x = int(24 * scale) # int x
	s_startserver_start_action.generic.y = y
	s_startserver_start_action.generic.callback = StartServerActionFunc

	qmenu.Menu_AddItem(s_startserver_menu, s_startmap_list)

	if M_IsGame("ctf"):

		qmenu.Menu_AddItem(s_startserver_menu, s_capturelimit_field)

	else:

		qmenu.Menu_AddItem(s_startserver_menu, s_rules_box)


	qmenu.Menu_AddItem(s_startserver_menu, s_timelimit_field)
	qmenu.Menu_AddItem(s_startserver_menu, s_fraglimit_field)
	qmenu.Menu_AddItem(s_startserver_menu, s_maxclients_field)
	qmenu.Menu_AddItem(s_startserver_menu, s_hostname_field)
	qmenu.Menu_AddItem(s_startserver_menu, s_startserver_dmoptions_action)
	qmenu.Menu_AddItem(s_startserver_menu, s_startserver_start_action)

	qmenu.Menu_Center(s_startserver_menu)

	# call this now to set proper inital state
	RulesChangeFunc(None)


def M_Menu_StartServer_f(): # (static)

	StartServer_MenuInit()
	s_startserver_menu.draw = Default_MenuDraw
	s_startserver_menu.key = Default_MenuKey
	M_PushMenu(s_startserver_menu)

dmoptions_statusbar = "" #static char[128]
s_dmoptions_menu = qmenu_h.menuframework_s() #static menuframework_s
s_friendlyfire_box = qmenu_h.menulist_s() #static menulist_s
s_falls_box = qmenu_h.menulist_s() #static menulist_s
s_weapons_stay_box = qmenu_h.menulist_s() #static menulist_s
s_instant_powerups_box = qmenu_h.menulist_s() #static menulist_s
s_powerups_box = qmenu_h.menulist_s() #static menulist_s
s_health_box = qmenu_h.menulist_s() #static menulist_s
s_spawn_farthest_box = qmenu_h.menulist_s() #static menulist_s
s_teamplay_box = qmenu_h.menulist_s() #static menulist_s
s_samelevel_box = qmenu_h.menulist_s() #static menulist_s
s_force_respawn_box = qmenu_h.menulist_s() #static menulist_s
s_armor_box = qmenu_h.menulist_s() #static menulist_s
s_allow_exit_box = qmenu_h.menulist_s() #static menulist_s
s_infinite_ammo_box = qmenu_h.menulist_s() #static menulist_s
s_fixed_fov_box = qmenu_h.menulist_s() #static menulist_s
s_quad_drop_box = qmenu_h.menulist_s() #static menulist_s
s_no_mines_box = qmenu_h.menulist_s() #static menulist_s
s_no_nukes_box = qmenu_h.menulist_s() #static menulist_s
s_stack_double_box = qmenu_h.menulist_s() #static menulist_s
s_no_spheres_box = qmenu_h.menulist_s() #static menulist_s

def DMFlagCallback(self): #void * (static)

	"""
	const menulist_s *f = (menulist_s *)self;
	int flags;
	int bit = 0;
	"""
	global dmoptions_statusbar

	f = self
	bit = 0

	flags = int(cvar.Cvar_VariableValue("dmflags"))

	# Q2PORT: the C jumps to setvalue (goto) from the cases that set flags
	# themselves; here setvalue is True for them and the bit code is skipped
	setvalue = False

	if f is s_friendlyfire_box:

		if f.curvalue:

			flags &= ~shared.DF_NO_FRIENDLY_FIRE


		else:

			flags |= shared.DF_NO_FRIENDLY_FIRE


		setvalue = True # goto setvalue;

	elif f is s_falls_box:

		if f.curvalue:

			flags &= ~shared.DF_NO_FALLING


		else:

			flags |= shared.DF_NO_FALLING


		setvalue = True # goto setvalue;

	elif f is s_weapons_stay_box:

		bit = shared.DF_WEAPONS_STAY

	elif f is s_instant_powerups_box:

		bit = shared.DF_INSTANT_ITEMS

	elif f is s_allow_exit_box:

		bit = shared.DF_ALLOW_EXIT

	elif f is s_powerups_box:

		if f.curvalue:

			flags &= ~shared.DF_NO_ITEMS


		else:

			flags |= shared.DF_NO_ITEMS


		setvalue = True # goto setvalue;

	elif f is s_health_box:

		if f.curvalue:

			flags &= ~shared.DF_NO_HEALTH


		else:

			flags |= shared.DF_NO_HEALTH


		setvalue = True # goto setvalue;

	elif f is s_spawn_farthest_box:

		bit = shared.DF_SPAWN_FARTHEST

	elif f is s_teamplay_box:

		if f.curvalue == 1:

			flags |= shared.DF_SKINTEAMS
			flags &= ~shared.DF_MODELTEAMS

		elif f.curvalue == 2:

			flags |= shared.DF_MODELTEAMS
			flags &= ~shared.DF_SKINTEAMS

		else:

			flags &= ~(shared.DF_MODELTEAMS | shared.DF_SKINTEAMS)


		setvalue = True # goto setvalue;

	elif f is s_samelevel_box:

		bit = shared.DF_SAME_LEVEL

	elif f is s_force_respawn_box:

		bit = shared.DF_FORCE_RESPAWN

	elif f is s_armor_box:

		if f.curvalue:

			flags &= ~shared.DF_NO_ARMOR


		else:

			flags |= shared.DF_NO_ARMOR


		setvalue = True # goto setvalue;

	elif f is s_infinite_ammo_box:

		bit = shared.DF_INFINITE_AMMO

	elif f is s_fixed_fov_box:

		bit = shared.DF_FIXED_FOV

	elif f is s_quad_drop_box:

		bit = shared.DF_QUAD_DROP

	elif M_IsGame("rogue"):

		if f is s_no_mines_box:

			bit = shared.DF_NO_MINES

		elif f is s_no_nukes_box:

			bit = shared.DF_NO_NUKES

		elif f is s_stack_double_box:

			bit = shared.DF_NO_STACK_DOUBLE

		elif f is s_no_spheres_box:

			bit = shared.DF_NO_SPHERES


	elif M_IsGame("ctf"):

		if f is s_no_mines_box:

			bit = shared.DF_NO_MINES # Equivalent to DF_CTF_FORCEJOIN in CTF

		elif f is s_no_nukes_box:

			bit = shared.DF_NO_NUKES # Equivalent to DF_CTF_NO_TECH   in CTF

		elif f is s_stack_double_box:

			bit = shared.DF_NO_STACK_DOUBLE # Equivalent to DF_ARMOR_PROTECT in CTF



	if not setvalue and f:

		if f.curvalue == 0:

			flags &= ~bit


		else:

			flags |= bit



	# setvalue:
	cvar.Cvar_SetValue("dmflags", float(flags))

	dmoptions_statusbar = ("dmflags = %d" % (flags,))[:127] # Com_sprintf
	s_dmoptions_menu.statusbar = dmoptions_statusbar # Q2PORT: the menu's statusbar points at the dmoptions_statusbar buffer


def DMOptions_MenuInit(): # (static)

	"""
	static const char *yes_no_names[] = { "no", "yes", NULL };
	static const char *teamplay_names[] = { "disabled", "by skin", "by model", NULL };
	int dmflags = Cvar_VariableValue("dmflags");
	unsigned short int y = 0;
	"""
	dmflags = int(cvar.Cvar_VariableValue("dmflags")) # int dmflags
	y = 0

	s_dmoptions_menu.x = int(vid.viddef.width * 0.50)
	s_dmoptions_menu.nitems = 0
	s_falls_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_falls_box.generic.x = 0
	s_falls_box.generic.y = y
	s_falls_box.generic.name = "falling damage"
	s_falls_box.generic.callback = DMFlagCallback
	s_falls_box.itemnames = yes_no_names
	s_falls_box.curvalue = (dmflags & shared.DF_NO_FALLING) == 0
	s_weapons_stay_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_weapons_stay_box.generic.x = 0
	y += 10; s_weapons_stay_box.generic.y = y
	s_weapons_stay_box.generic.name = "weapons stay"
	s_weapons_stay_box.generic.callback = DMFlagCallback
	s_weapons_stay_box.itemnames = yes_no_names
	s_weapons_stay_box.curvalue = (dmflags & shared.DF_WEAPONS_STAY) != 0
	s_instant_powerups_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_instant_powerups_box.generic.x = 0
	y += 10; s_instant_powerups_box.generic.y = y
	s_instant_powerups_box.generic.name = "instant powerups"
	s_instant_powerups_box.generic.callback = DMFlagCallback
	s_instant_powerups_box.itemnames = yes_no_names
	s_instant_powerups_box.curvalue = (dmflags & shared.DF_INSTANT_ITEMS) != 0
	s_powerups_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_powerups_box.generic.x = 0
	y += 10; s_powerups_box.generic.y = y
	s_powerups_box.generic.name = "allow powerups"
	s_powerups_box.generic.callback = DMFlagCallback
	s_powerups_box.itemnames = yes_no_names
	s_powerups_box.curvalue = (dmflags & shared.DF_NO_ITEMS) == 0
	s_health_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_health_box.generic.x = 0
	y += 10; s_health_box.generic.y = y
	s_health_box.generic.callback = DMFlagCallback
	s_health_box.generic.name = "allow health"
	s_health_box.itemnames = yes_no_names
	s_health_box.curvalue = (dmflags & shared.DF_NO_HEALTH) == 0
	s_armor_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_armor_box.generic.x = 0
	y += 10; s_armor_box.generic.y = y
	s_armor_box.generic.name = "allow armor"
	s_armor_box.generic.callback = DMFlagCallback
	s_armor_box.itemnames = yes_no_names
	s_armor_box.curvalue = (dmflags & shared.DF_NO_ARMOR) == 0
	s_spawn_farthest_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_spawn_farthest_box.generic.x = 0
	y += 10; s_spawn_farthest_box.generic.y = y
	s_spawn_farthest_box.generic.name = "spawn farthest"
	s_spawn_farthest_box.generic.callback = DMFlagCallback
	s_spawn_farthest_box.itemnames = yes_no_names
	s_spawn_farthest_box.curvalue = (dmflags & shared.DF_SPAWN_FARTHEST) != 0
	s_samelevel_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_samelevel_box.generic.x = 0
	y += 10; s_samelevel_box.generic.y = y
	s_samelevel_box.generic.name = "same map"
	s_samelevel_box.generic.callback = DMFlagCallback
	s_samelevel_box.itemnames = yes_no_names
	s_samelevel_box.curvalue = (dmflags & shared.DF_SAME_LEVEL) != 0
	s_force_respawn_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_force_respawn_box.generic.x = 0
	y += 10; s_force_respawn_box.generic.y = y
	s_force_respawn_box.generic.name = "force respawn"
	s_force_respawn_box.generic.callback = DMFlagCallback
	s_force_respawn_box.itemnames = yes_no_names
	s_force_respawn_box.curvalue = (dmflags & shared.DF_FORCE_RESPAWN) != 0
	if not M_IsGame("ctf"):

		s_teamplay_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_teamplay_box.generic.x = 0
		y += 10; s_teamplay_box.generic.y = y
		s_teamplay_box.generic.name = "teamplay"
		s_teamplay_box.generic.callback = DMFlagCallback
		s_teamplay_box.itemnames = teamplay_names


	s_allow_exit_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_exit_box.generic.x = 0
	y += 10; s_allow_exit_box.generic.y = y
	s_allow_exit_box.generic.name = "allow exit"
	s_allow_exit_box.generic.callback = DMFlagCallback
	s_allow_exit_box.itemnames = yes_no_names
	s_allow_exit_box.curvalue = (dmflags & shared.DF_ALLOW_EXIT) != 0
	s_infinite_ammo_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_infinite_ammo_box.generic.x = 0
	y += 10; s_infinite_ammo_box.generic.y = y
	s_infinite_ammo_box.generic.name = "infinite ammo"
	s_infinite_ammo_box.generic.callback = DMFlagCallback
	s_infinite_ammo_box.itemnames = yes_no_names
	s_infinite_ammo_box.curvalue = (dmflags & shared.DF_INFINITE_AMMO) != 0
	s_fixed_fov_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_fixed_fov_box.generic.x = 0
	y += 10; s_fixed_fov_box.generic.y = y
	s_fixed_fov_box.generic.name = "fixed FOV"
	s_fixed_fov_box.generic.callback = DMFlagCallback
	s_fixed_fov_box.itemnames = yes_no_names
	s_fixed_fov_box.curvalue = (dmflags & shared.DF_FIXED_FOV) != 0
	s_quad_drop_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_quad_drop_box.generic.x = 0
	y += 10; s_quad_drop_box.generic.y = y
	s_quad_drop_box.generic.name = "quad drop"
	s_quad_drop_box.generic.callback = DMFlagCallback
	s_quad_drop_box.itemnames = yes_no_names
	s_quad_drop_box.curvalue = (dmflags & shared.DF_QUAD_DROP) != 0
	if not M_IsGame("ctf"):

		s_friendlyfire_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_friendlyfire_box.generic.x = 0
		y += 10; s_friendlyfire_box.generic.y = y
		s_friendlyfire_box.generic.name = "friendly fire"
		s_friendlyfire_box.generic.callback = DMFlagCallback
		s_friendlyfire_box.itemnames = yes_no_names
		s_friendlyfire_box.curvalue = (dmflags & shared.DF_NO_FRIENDLY_FIRE) == 0


	if M_IsGame("rogue"):

		s_no_mines_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_no_mines_box.generic.x = 0
		y += 10; s_no_mines_box.generic.y = y
		s_no_mines_box.generic.name = "remove mines"
		s_no_mines_box.generic.callback = DMFlagCallback
		s_no_mines_box.itemnames = yes_no_names
		s_no_mines_box.curvalue = (dmflags & shared.DF_NO_MINES) != 0
		s_no_nukes_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_no_nukes_box.generic.x = 0
		y += 10; s_no_nukes_box.generic.y = y
		s_no_nukes_box.generic.name = "remove nukes"
		s_no_nukes_box.generic.callback = DMFlagCallback
		s_no_nukes_box.itemnames = yes_no_names
		s_no_nukes_box.curvalue = (dmflags & shared.DF_NO_NUKES) != 0
		s_stack_double_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_stack_double_box.generic.x = 0
		y += 10; s_stack_double_box.generic.y = y
		s_stack_double_box.generic.name = "2x/4x stacking off"
		s_stack_double_box.generic.callback = DMFlagCallback
		s_stack_double_box.itemnames = yes_no_names
		s_stack_double_box.curvalue = (dmflags & shared.DF_NO_STACK_DOUBLE) != 0
		s_no_spheres_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_no_spheres_box.generic.x = 0
		y += 10; s_no_spheres_box.generic.y = y
		s_no_spheres_box.generic.name = "remove spheres"
		s_no_spheres_box.generic.callback = DMFlagCallback
		s_no_spheres_box.itemnames = yes_no_names
		s_no_spheres_box.curvalue = (dmflags & shared.DF_NO_SPHERES) != 0

	elif M_IsGame("ctf"):

		s_no_mines_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_no_mines_box.generic.x = 0
		y += 10; s_no_mines_box.generic.y = y
		s_no_mines_box.generic.name = "force join"
		s_no_mines_box.generic.callback = DMFlagCallback
		s_no_mines_box.itemnames = yes_no_names
		s_no_mines_box.curvalue = (dmflags & shared.DF_NO_MINES) != 0
		s_stack_double_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_stack_double_box.generic.x = 0
		y += 10; s_stack_double_box.generic.y = y
		s_stack_double_box.generic.name = "armor protect"
		s_stack_double_box.generic.callback = DMFlagCallback
		s_stack_double_box.itemnames = yes_no_names
		s_stack_double_box.curvalue = (dmflags & shared.DF_NO_STACK_DOUBLE) != 0
		s_no_nukes_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_no_nukes_box.generic.x = 0
		y += 10; s_no_nukes_box.generic.y = y
		s_no_nukes_box.generic.name = "techs off"
		s_no_nukes_box.generic.callback = DMFlagCallback
		s_no_nukes_box.itemnames = yes_no_names
		s_no_nukes_box.curvalue = (dmflags & shared.DF_NO_NUKES) != 0


	qmenu.Menu_AddItem(s_dmoptions_menu, s_falls_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_weapons_stay_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_instant_powerups_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_powerups_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_health_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_armor_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_spawn_farthest_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_samelevel_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_force_respawn_box)
	if not M_IsGame("ctf"):

		qmenu.Menu_AddItem(s_dmoptions_menu, s_teamplay_box)


	qmenu.Menu_AddItem(s_dmoptions_menu, s_allow_exit_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_infinite_ammo_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_fixed_fov_box)
	qmenu.Menu_AddItem(s_dmoptions_menu, s_quad_drop_box)
	if not M_IsGame("ctf"):

		qmenu.Menu_AddItem(s_dmoptions_menu, s_friendlyfire_box)


	if M_IsGame("rogue"):

		qmenu.Menu_AddItem(s_dmoptions_menu, s_no_mines_box)
		qmenu.Menu_AddItem(s_dmoptions_menu, s_no_nukes_box)
		qmenu.Menu_AddItem(s_dmoptions_menu, s_stack_double_box)
		qmenu.Menu_AddItem(s_dmoptions_menu, s_no_spheres_box)

	elif M_IsGame("ctf"):

		qmenu.Menu_AddItem(s_dmoptions_menu, s_no_mines_box)
		qmenu.Menu_AddItem(s_dmoptions_menu, s_stack_double_box)
		qmenu.Menu_AddItem(s_dmoptions_menu, s_no_nukes_box)


	qmenu.Menu_Center(s_dmoptions_menu)
	# set the original dmflags statusbar
	DMFlagCallback(0)
	qmenu.Menu_SetStatusBar(s_dmoptions_menu, dmoptions_statusbar)

def M_Menu_DMOptions_f(): # (static)

	DMOptions_MenuInit()
	s_dmoptions_menu.draw = Default_MenuDraw
	s_dmoptions_menu.key = Default_MenuKey
	M_PushMenu(s_dmoptions_menu)

s_downloadoptions_menu = qmenu_h.menuframework_s() #static menuframework_s
s_download_title = qmenu_h.menuseparator_s() #static menuseparator_s
s_allow_download_box = qmenu_h.menulist_s() #static menulist_s
s_allow_download_http_box = qmenu_h.menulist_s() #static menulist_s
s_allow_download_maps_box = qmenu_h.menulist_s() #static menulist_s
s_allow_download_models_box = qmenu_h.menulist_s() #static menulist_s
s_allow_download_players_box = qmenu_h.menulist_s() #static menulist_s
s_allow_download_sounds_box = qmenu_h.menulist_s() #static menulist_s

def DownloadCallback(self): #void * (static)

	"""
	const menulist_s *f = (menulist_s *)self;
	"""
	f = self

	if f == s_allow_download_box:

		cvar.Cvar_SetValue("allow_download", float(f.curvalue))

	# #ifdef USE_CURL
	elif f == s_allow_download_http_box:

		cvar.Cvar_SetValue("cl_http_downloads", f.curvalue)

	# #endif
	elif f == s_allow_download_maps_box:

		cvar.Cvar_SetValue("allow_download_maps", float(f.curvalue))

	elif f == s_allow_download_models_box:

		cvar.Cvar_SetValue("allow_download_models", float(f.curvalue))

	elif f == s_allow_download_players_box:

		cvar.Cvar_SetValue("allow_download_players", float(f.curvalue))

	elif f == s_allow_download_sounds_box:

		cvar.Cvar_SetValue("allow_download_sounds", float(f.curvalue))

def DownloadOptions_MenuInit(): # (static)

	"""
	static const char *yes_no_names[] = { "no", "yes", NULL };
	unsigned short int y = 0;
	float scale = SCR_GetMenuScale();
	"""
	y = 0
	scale = cl_screen.SCR_GetMenuScale()

	s_downloadoptions_menu.x = int(vid.viddef.width * 0.50)
	s_downloadoptions_menu.nitems = 0
	s_download_title.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_download_title.generic.name = "Download Options"
	s_download_title.generic.x = int(48 * scale) # int x
	s_download_title.generic.y = y
	s_allow_download_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_download_box.generic.x = 0
	y += 20; s_allow_download_box.generic.y = y
	s_allow_download_box.generic.name = "allow downloading"
	s_allow_download_box.generic.callback = DownloadCallback
	s_allow_download_box.itemnames = yes_no_names
	s_allow_download_box.curvalue = (cvar.Cvar_VariableValue("allow_download") != 0)
	# #ifdef USE_CURL
	s_allow_download_http_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_download_http_box.generic.x = 0
	y += 20; s_allow_download_http_box.generic.y = y
	s_allow_download_http_box.generic.name = "http downloading"
	s_allow_download_http_box.generic.callback = DownloadCallback
	s_allow_download_http_box.itemnames = yes_no_names
	s_allow_download_http_box.curvalue = (cvar.Cvar_VariableValue("cl_http_downloads") != 0)
	# #else
	#y += 10;
	# #endif
	s_allow_download_maps_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_download_maps_box.generic.x = 0
	y += 10; s_allow_download_maps_box.generic.y = y
	s_allow_download_maps_box.generic.name = "maps"
	s_allow_download_maps_box.generic.callback = DownloadCallback
	s_allow_download_maps_box.itemnames = yes_no_names
	s_allow_download_maps_box.curvalue = (cvar.Cvar_VariableValue("allow_download_maps") != 0)
	s_allow_download_players_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_download_players_box.generic.x = 0
	y += 10; s_allow_download_players_box.generic.y = y
	s_allow_download_players_box.generic.name = "player models/skins"
	s_allow_download_players_box.generic.callback = DownloadCallback
	s_allow_download_players_box.itemnames = yes_no_names
	s_allow_download_players_box.curvalue = (cvar.Cvar_VariableValue("allow_download_players") != 0)
	s_allow_download_models_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_download_models_box.generic.x = 0
	y += 10; s_allow_download_models_box.generic.y = y
	s_allow_download_models_box.generic.name = "models"
	s_allow_download_models_box.generic.callback = DownloadCallback
	s_allow_download_models_box.itemnames = yes_no_names
	s_allow_download_models_box.curvalue = (cvar.Cvar_VariableValue("allow_download_models") != 0)
	s_allow_download_sounds_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_allow_download_sounds_box.generic.x = 0
	y += 10; s_allow_download_sounds_box.generic.y = y
	s_allow_download_sounds_box.generic.name = "sounds"
	s_allow_download_sounds_box.generic.callback = DownloadCallback
	s_allow_download_sounds_box.itemnames = yes_no_names
	s_allow_download_sounds_box.curvalue = (cvar.Cvar_VariableValue("allow_download_sounds") != 0)
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_download_title)
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_allow_download_box)
	# #ifdef USE_CURL
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_allow_download_http_box)
	# #endif
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_allow_download_maps_box)
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_allow_download_players_box)
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_allow_download_models_box)
	qmenu.Menu_AddItem(s_downloadoptions_menu, s_allow_download_sounds_box)
	qmenu.Menu_Center(s_downloadoptions_menu)
	# skip over title
	if s_downloadoptions_menu.cursor == 0:

		s_downloadoptions_menu.cursor = 1

def M_Menu_DownloadOptions_f(): # (static)

	DownloadOptions_MenuInit()
	s_downloadoptions_menu.draw = Default_MenuDraw
	s_downloadoptions_menu.key = Default_MenuKey
	M_PushMenu(s_downloadoptions_menu)

s_addressbook_menu = qmenu_h.menuframework_s() #static menuframework_s
s_addressbook_fields = [qmenu_h.menufield_s() for i in range(client_h.NUM_ADDRESSBOOK_ENTRIES)] #static menufield_s[NUM_ADDRESSBOOK_ENTRIES]

def AddressBook_MenuInit(): # (static)

	"""
	int i;
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	s_addressbook_menu.x = int(vid.viddef.width / 2 - (142 * scale)) # int x
	s_addressbook_menu.y = int(vid.viddef.height / (2 * scale) - 58) # int y
	s_addressbook_menu.banner = "m_banner_addressbook"
	s_addressbook_menu.nitems = 0
	for i in range(client_h.NUM_ADDRESSBOOK_ENTRIES):

		#menufield_s *f;
		#const cvar_t *adr;
		#char buffer[20];
		buffer = [None] * 20
		buffer = "adr%d" % (i,) # Com_sprintf
		adr = cvar.Cvar_Get(buffer, "", shared.CVAR_ARCHIVE)
		f = s_addressbook_fields[i]
		f.generic.type = qmenu_h.MTYPE_FIELD
		f.generic.name = None
		f.generic.callback = None
		f.generic.x = 0
		f.generic.y = i * 18 + 0
		f.generic.localdata[0] = i
		qmenu.Field_InitState(f, adr.string, 60, 30)
		qmenu.Menu_AddItem(s_addressbook_menu, f)

def AddressBook_MenuClose(m): #menuframework_s * (static)

	"""
	int index;
	"""

	for index in range(client_h.NUM_ADDRESSBOOK_ENTRIES):

		#char buffer[20];
		buffer = [None] * 20
		buffer = "adr%d" % (index,) # Com_sprintf
		cvar.Cvar_Set(buffer, s_addressbook_fields[index].buffer)

def M_Menu_AddressBook_f(): # (static)

	AddressBook_MenuInit()
	s_addressbook_menu.draw = Default_MenuDraw
	s_addressbook_menu.key = Default_MenuKey
	s_addressbook_menu.close = AddressBook_MenuClose
	M_PushMenu(s_addressbook_menu)

MAX_PLAYERMODELS	= 1024
s_player_config_menu = qmenu_h.menuframework_s() #static menuframework_s
s_player_name_field = qmenu_h.menufield_s() #static menufield_s
s_player_icon_bitmap = qmenu_h.menubitmap_s() #static menubitmap_s
s_player_model_box = qmenu_h.menulist_s() #static menulist_s
s_player_skin_box = qmenu_h.menulist_s() #static menulist_s
s_player_handedness_box = qmenu_h.menulist_s() #static menulist_s
s_player_rate_box = qmenu_h.menulist_s() #static menulist_s
s_player_skin_title = qmenu_h.menuseparator_s() #static menuseparator_s
s_player_model_title = qmenu_h.menuseparator_s() #static menuseparator_s
s_player_hand_title = qmenu_h.menuseparator_s() #static menuseparator_s
s_player_rate_title = qmenu_h.menuseparator_s() #static menuseparator_s
s_player_download_action = qmenu_h.menuaction_s() #static menuaction_s
s_skinnames = [shared.strlist_t() for i in range(MAX_PLAYERMODELS)] #static strlist_t[MAX_PLAYERMODELS]
s_modelname = shared.strlist_t() #static strlist_t
player_icon_path = "" #static char[MAX_QPATH]
rate_tbl = [2500, 3200, 5000, 10000, 25000] #static int[]
rate_names = ["28.8 Modem", "33.6 Modem", "Single ISDN", "Dual ISDN/Cable", "T1/LAN", "User defined", None] #static const char *[]
model_preview_start = None #static const cvar_t *
model_preview_end = None #static const cvar_t *

def SelectedModelSkin(): #const char **, const char ** (static)

	# Q2PORT: returns (mdl, img) instead of filling *mdl and *img

	mi = s_player_model_box.curvalue
	si = s_player_skin_box.curvalue

	mdl = None # *mdl = NULL;

	img = None # *img = NULL;

	if mi >= 0 and mi < s_modelname.num:

		mdl = s_modelname.data[mi]

		if si >= 0 and si < s_skinnames[mi].num:

			img = s_skinnames[mi].data[si]



	return mdl, img


def DownloadOptionsFunc(self): #void * (static)

	M_Menu_DownloadOptions_f()

def HandednessCallback(unused): #void * (static)

	cvar.Cvar_SetValue("hand", float(s_player_handedness_box.curvalue))

def RateCallback(self): #void * (static)

	"""
	const menulist_s *r = self;
	"""
	r = self

	if r.curvalue >= 0 and r.curvalue != len(rate_tbl):

		cvar.Cvar_SetValue("rate", rate_tbl[r.curvalue])

def SkinCallback(unused): #void * (static)

	"""
	const char *mdl, *img;
	"""
	global player_icon_path

	mdl, img = SelectedModelSkin()

	if (not mdl or not img or
		len("/players/%s/%s_i.pcx" % (mdl, img)) >= shared.MAX_QPATH): # snprintf(...) >= sizeof(player_icon_path)

		player_icon_path = "" # *player_icon_path = '\0';

	else:

		player_icon_path = "/players/%s/%s_i.pcx" % (mdl, img)

	s_player_icon_bitmap.generic.name = player_icon_path # Q2PORT: the bitmap's name points at the player_icon_path buffer


def ModelCallback(self): #void * (static)

	"""
	const menulist_s *m = self;
	menulist_s *s = &s_player_skin_box;
	const char **skinnames;
	"""
	m = self
	s = s_player_skin_box

	skinnames = s_skinnames[m.curvalue].data # (const char **)

	if s.itemnames is not skinnames:

		s.itemnames = skinnames
		s.curvalue = 0

		SkinCallback(s)


def IconOfSkinExists(skin: str, files: shared.strlist_t, ext: str)->bool: #const char *, const strlist_t *, const char * (returns static qboolean)

	"""
	char scratch[MAX_QPATH];
	int i;
	"""

	if len(skin) >= shared.MAX_QPATH: # Q_strlcpy(scratch, skin, sizeof(scratch)) >= sizeof(scratch)

		return False

	scratch = skin

	scratch, _ = shared_c.COM_StripExtension2(scratch)

	if (len(scratch + "_i.") >= shared.MAX_QPATH or # Q_strlcat(scratch, "_i.", sizeof(scratch)) >= sizeof(scratch)
		len(scratch + "_i." + ext) >= shared.MAX_QPATH): # Q_strlcat(scratch, ext, sizeof(scratch)) >= sizeof(scratch)

		return False

	scratch = scratch + "_i." + ext

	for i in range(files.num):

		if files.data[i] == scratch:

			return True



	return False


def dircmp_func(_a: str, _b: str)->int: #const void*, const void* (returns static int)

	# Q2PORT: the qsort comparator takes the strings; use it with functools.cmp_to_key
	a = _a[_a.rfind('/') + 1:] # strrchr(*(const char**)_a, '/') + 1
	b = _b[_b.rfind('/') + 1:] # strrchr(*(const char**)_b, '/') + 1

	# sort by male, female, then alphabetical
	if a == "male":

		return -1

	elif b == "male":

		return 1


	if a == "female":

		return -1

	elif b == "female":

		return 1


	return (a > b) - (a < b) # strcmp(a, b)


def PlayerModelFree(): # (static)

	global model_preview_end, model_preview_start

	"""
	int i;
	"""

	for i in range(MAX_PLAYERMODELS):

		shared_c.StrList_Free(s_skinnames[i])


	shared_c.StrList_Free(s_modelname)
	s_player_model_box.itemnames = None
	s_player_skin_box.itemnames = None
	model_preview_start = None
	model_preview_end = None

def PlayerDirectoryList()->shared.strlist_t: # (returns static strlist_t)

	"""
	strlist_t dirs, list;
	const char *findname = "players/*";
	int i;
	size_t listoff = strlen(findname);
	"""
	list_ = shared.strlist_t()
	findname = "players/*"
	listoff = len(findname)

	shared_c.StrList_Init(list_, 0)

	dirs = filesystem.FS_ListFiles2(findname, 0, 0)

	for i in range(dirs.num):

		"""
		char *slash;
		"""

		#
		# search slash after "players/" and use only directory name
		# pak search does not return directory names, only files in
		# directories
		#
		slash = shared_c.Q_strchrs(dirs.data[i][listoff:], "/\\")
		if slash is not None:

			dirs.data[i] = dirs.data[i][:listoff + slash] # *slash = '\0';


		if not shared.StrList_Contains(list_, dirs.data[i]):

			if list_.num >= MAX_PLAYERMODELS:

				clientserver.Com_Printf("Too many player models\n")
				break


			shared_c.StrList_Append(list_, dirs.data[i])



	shared_c.StrList_Free(dirs)

	# sort them male, female, alphabetical
	if list_.num > 2:

		list_.data[:list_.num - 1] = sorted(list_.data[:list_.num - 1], key=functools.cmp_to_key(dircmp_func)) # qsort(list.data, list.num - 1, ...)


	return list_


def SkinsInDir(sl: shared.strlist_t, dirname: str, ext: str): #strlist_t *, const char *, const char * (static)

	"""
	strlist_t list;
	char findname[MAX_QPATH];
	size_t dirname_size;
	int i;
	"""

	findname = "%s/*.%s" % (dirname, ext)
	if len(findname) >= shared.MAX_QPATH: # snprintf(findname, sizeof(findname), ...) >= sizeof(findname)

		return


	list_ = filesystem.FS_ListFiles2(findname, 0, 0)
	dirname_size = len(dirname) + 1

	shared_c.StrList_Expand(sl, sl.num + list_.num)

	i = 0
	while i < list_.num and sl.num < sl.cap: # for (i = 0; i < list.num && sl->num < sl->cap; i++)

		if '/' not in list_.data[i][dirname_size:]: # !strchr(list.data[i] + dirname_size, '/')

			sl.data[sl.num] = list_.data[i]
			sl.num += 1

			list_.data[i] = None

		i += 1


	shared_c.StrList_Free(list_)


def PlayerModelList(dirs: shared.strlist_t)->bool: #const strlist_t * (returns static qboolean)

	"""
	int i;
	"""

	shared_c.StrList_Init(s_modelname, 3)

	# verify the existence of at least one pcx skin
	for i in range(dirs.num):

		"""
		strlist_t list, *sl;
		const char *s, *mdl;
		int k;
		"""
		list_ = shared.strlist_t()

		s = dirs.data[i]

		if not s or not common_h.FS_FileExists("%s/tris.md2" % (s,)):

			continue


		shared_c.StrList_Init(list_, 0)

		SkinsInDir(list_, s, "pcx")
		SkinsInDir(list_, s, "png")

		if not list_.num:

			shared_c.StrList_Free(list_)
			continue


		sl = s_skinnames[s_modelname.num]
		shared_c.StrList_Init(sl, 0)

		for k in range(list_.num):

			"""
			char *t;
			"""

			if ("_i.png" in list_.data[k] or
				"_i.pcx" in list_.data[k]):

				continue


			if (not IconOfSkinExists(list_.data[k], list_, "png") and
				not IconOfSkinExists(list_.data[k], list_, "pcx")):

				continue


			t = shared_c.Q_strrchrs(list_.data[k], "/\\")
			if t is None:

				t = list_.data[k]

			else:

				t = list_.data[k][t + 1:] # t++


			t, _ = shared_c.COM_StripExtension2(t)

			shared_c.StrList_Append(sl, t)


		# no matching icon
		if not sl.num:

			shared_c.StrList_Free(sl)
			shared_c.StrList_Free(list_)
			continue


		if sl.num > 1:

			sl.data[:sl.num] = sorted(sl.data[:sl.num], key=functools.cmp_to_key(shared_c.Q_sort_stricmp)) # qsort


		shared_c.StrList_Compress(sl)

		mdl = s.rfind('/') # strrchr(s, '/')
		if mdl < 0:

			mdl = s

		else:

			mdl = s[mdl + 1:] # mdl++


		shared_c.StrList_Append(s_modelname, mdl)

		shared_c.StrList_Free(list_)


	if not s_modelname.num:

		PlayerModelFree()
		return False


	shared_c.StrList_Compress(s_modelname)

	return True


def PlayerConfig_ScanDirectories()->bool: # (returns static qboolean)

	"""
	strlist_t dirs;
	qboolean result;
	"""

	# directory names
	dirs = PlayerDirectoryList()
	if not dirs.num:

		clientserver.Com_Printf("No valid player directories found.\n")
		return False


	# valid models
	result = PlayerModelList(dirs)

	if not result:

		clientserver.Com_Printf("No valid player models found.\n")


	shared_c.StrList_Free(dirs)

	return result


def ListModels_f(): # (static)

	PlayerConfig_ScanDirectories()
	for i in range(s_modelname.num):

		for j in range(s_skinnames[i].num):

			clientserver.Com_Printf("%s/%s\n", s_modelname.data[i], s_skinnames[i].data[j])


	PlayerModelFree()

def CurrentRateIndex(): # (returns static int)

	"""
	int i, curr_rate;
	"""

	curr_rate = int(cvar.Cvar_VariableValue("rate")) # int curr_rate
	for i in range(len(rate_tbl)):

		if rate_tbl[i] == curr_rate:

			break


	return i

PlayerConfig_MenuInit_handedness = ["right", "left", "center", None] #static const char *[], in PlayerConfig_MenuInit

def PlayerConfig_MenuInit()->bool: # (returns static qboolean)

	#extern cvar_t *name;
	#const extern cvar_t *skin;
	"""
	cvar_t *hand = Cvar_Get( "hand", "0", CVAR_USERINFO | CVAR_ARCHIVE );
	char mdlname[MAX_QPATH];
	const char *imgname;
	char *slash;
	int mdlindex, imgindex;
	"""
	hand = cvar.Cvar_Get( "hand", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE )
	handedness = PlayerConfig_MenuInit_handedness
	scale = cl_screen.SCR_GetMenuScale()

	if not PlayerConfig_ScanDirectories():

		qmenu.Menu_StartPopup(m_popup,
			"No player models\nwere found", 3000)


	mdlname = cl_main.skin.string[:shared.MAX_QPATH - 1] # Q_strlcpy

	slash = shared_c.Q_strchrs(mdlname, "/\\")
	if slash is not None:

		imgname = mdlname[slash + 1:] # imgname = slash + 1;
		mdlname = mdlname[:slash] # *slash = '\0';

	else:

		mdlname = "male" # strcpy
		imgname = "grunt"


	mdlindex = shared_c.StrList_Find(s_modelname, shared_c.Q_stricmp, mdlname)
	if mdlindex >= s_modelname.num:

		mdlindex = 0


	imgindex = shared_c.StrList_Find(s_skinnames[mdlindex], shared_c.Q_stricmp, imgname)
	if imgindex >= s_skinnames[mdlindex].num:

		imgindex = 0


	if hand.value < 0 or hand.value > 2:

		cvar.Cvar_SetValue("hand", 0)


	s_player_config_menu.x = int(vid.viddef.width / 2 - 95 * scale) # int x
	s_player_config_menu.y = int(vid.viddef.height / (2 * scale) - 97) # int y
	s_player_config_menu.nitems = 0

	s_player_name_field.generic.type = qmenu_h.MTYPE_FIELD
	s_player_name_field.generic.name = "name"
	s_player_name_field.generic.callback = None
	s_player_name_field.generic.x = 0
	s_player_name_field.generic.y = 0
	qmenu.Field_InitState(s_player_name_field, cl_main.name.string, 20, 20)

	s_player_icon_bitmap.generic.type = qmenu_h.MTYPE_BITMAP
	s_player_icon_bitmap.generic.flags = qmenu_h.QMF_INACTIVE
	s_player_icon_bitmap.generic.x = int(((vid.viddef.width / scale - 95) / 2) - 87) # int x
	s_player_icon_bitmap.generic.y = int(((vid.viddef.height / (2 * scale))) - 72) # int y
	s_player_icon_bitmap.generic.name = player_icon_path
	s_player_icon_bitmap.generic.callback = None
	s_player_icon_bitmap.focuspic = None # 0

	s_player_model_title.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_player_model_title.generic.name = "model"
	s_player_model_title.generic.x = int(-8 * scale)
	s_player_model_title.generic.y = 60

	s_player_model_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_player_model_box.generic.x = int(-56 * scale)
	s_player_model_box.generic.y = 70
	s_player_model_box.generic.callback = ModelCallback
	s_player_model_box.generic.cursor_offset = -48
	s_player_model_box.curvalue = mdlindex
	s_player_model_box.itemnames = s_modelname.data # (const char**)

	s_player_skin_title.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_player_skin_title.generic.name = "skin"
	s_player_skin_title.generic.x = int(-16 * scale)
	s_player_skin_title.generic.y = 84

	s_player_skin_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_player_skin_box.generic.x = int(-56 * scale)
	s_player_skin_box.generic.y = 94
	s_player_skin_box.generic.name = None
	s_player_skin_box.generic.callback = SkinCallback
	s_player_skin_box.generic.cursor_offset = -48
	s_player_skin_box.curvalue = imgindex
	s_player_skin_box.itemnames = s_skinnames[mdlindex].data # (const char **)

	# initialize player icon
	SkinCallback(s_player_skin_box)

	s_player_hand_title.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_player_hand_title.generic.name = "handedness"
	s_player_hand_title.generic.x = int(32 * scale)
	s_player_hand_title.generic.y = 108

	s_player_handedness_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_player_handedness_box.generic.x = int(-56 * scale)
	s_player_handedness_box.generic.y = 118
	s_player_handedness_box.generic.name = None
	s_player_handedness_box.generic.cursor_offset = -48
	s_player_handedness_box.generic.callback = HandednessCallback
	s_player_handedness_box.curvalue = int(qmenu.ClampCvar(0, 2, hand.value))
	s_player_handedness_box.itemnames = handedness

	s_player_rate_title.generic.type = qmenu_h.MTYPE_SEPARATOR
	s_player_rate_title.generic.name = "connect speed"
	s_player_rate_title.generic.x = int(56 * scale)
	s_player_rate_title.generic.y = 156

	s_player_rate_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_player_rate_box.generic.x = int(-56 * scale)
	s_player_rate_box.generic.y = 166
	s_player_rate_box.generic.name = None
	s_player_rate_box.generic.cursor_offset = -48
	s_player_rate_box.generic.callback = RateCallback
	s_player_rate_box.curvalue = CurrentRateIndex()
	s_player_rate_box.itemnames = rate_names

	s_player_download_action.generic.type = qmenu_h.MTYPE_ACTION
	s_player_download_action.generic.name = "download options"
	s_player_download_action.generic.flags = qmenu_h.QMF_LEFT_JUSTIFY
	s_player_download_action.generic.x = int(-24 * scale)
	s_player_download_action.generic.y = 186
	s_player_download_action.generic.statusbar = None
	s_player_download_action.generic.callback = DownloadOptionsFunc

	qmenu.Menu_AddItem(s_player_config_menu, s_player_name_field)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_icon_bitmap)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_model_title)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_model_box)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_skin_title)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_skin_box)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_hand_title)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_handedness_box)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_rate_title)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_rate_box)
	qmenu.Menu_AddItem(s_player_config_menu, s_player_download_action)

	return True


"""
extern float CalcFov(float fov_x, float w, float h);
"""

"""
 * Model animation

"""
def PlayerConfig_AnimateModel(entity, count, curTime): #entity_t *, int, int (static)

	global model_preview_end, model_preview_start

	"""
	int startFrame, endFrame;
	"""

	if not model_preview_start:

		model_preview_start = cvar.Cvar_Get("cl_model_preview_start", "84", shared.CVAR_ARCHIVE)


	if not model_preview_end:

		model_preview_end = cvar.Cvar_Get("cl_model_preview_end", "94", shared.CVAR_ARCHIVE)


	startFrame = int(model_preview_start.value) # int startFrame
	endFrame = int(model_preview_end.value) # int endFrame
	if startFrame >= 0 and endFrame > startFrame:

		#int i;
		for i in range(count):

			# salute male 84..94 frame
			entity[i].frame = int(int(curTime / 100) % (endFrame - startFrame) + startFrame) # int division

def PlayerConfig_ModelDraw(): # (static)

	"""
	refdef_t refdef;
	float scale = SCR_GetMenuScale();
	entity_t entities[2];
	char scratch[MAX_QPATH];
	int i, curTime;
	const char *mdlname, *imgname;
	"""
	scale = cl_screen.SCR_GetMenuScale()

	mdlname, imgname = SelectedModelSkin()
	if not mdlname or not imgname:

		return


	refdef = ref.refdef_t() # memset(&refdef, 0, sizeof(refdef));

	refdef.x = int(vid.viddef.width / 2)
	refdef.y = int(vid.viddef.height / 2 - 72 * scale)
	refdef.width = int(144 * scale)
	refdef.height = int(168 * scale)
	refdef.fov_x = 40
	refdef.fov_y = cl_view.CalcFov(refdef.fov_x, float(refdef.width), float(refdef.height))
	refdef.time = cl_main.cls.realtime * 0.001

	entities = [ref.entity_t(), ref.entity_t()] # memset(&entities, 0, sizeof(entities));

	scratch = "players/%s/tris.md2" % (mdlname,) # Com_sprintf
	entities[0].model = vid.R_RegisterModel(scratch)

	scratch = "players/%s/%s.pcx" % (mdlname,
		imgname) # Com_sprintf
	entities[0].skin = vid.R_RegisterSkin(scratch)

	curTime = system.Sys_Milliseconds()

	# multiplayer weapons loaded
	if cl_view.num_cl_weaponmodels:

		"""
		int weapon_id;
		"""

		# change weapon every 3 rounds
		weapon_id = int(curTime / 9000)

		weapon_id = weapon_id % cl_view.num_cl_weaponmodels
		# show weapon also
		scratch = "players/%s/%s" % (mdlname, cl_view.cl_weaponmodels[weapon_id]) # Com_sprintf
		entities[1].model = vid.R_RegisterModel(scratch)


	# no such weapon model
	if not entities[1].model:

		# show weapon also
		scratch = "players/%s/weapon.md2" % (mdlname,) # Com_sprintf
		entities[1].model = vid.R_RegisterModel(scratch)


	curTime = curTime % 3000
	for i in range(2):

		entities[i].flags = shared.RF_FULLBRIGHT
		entities[i].origin[0] = 80
		entities[i].origin[1] = 0
		entities[i].origin[2] = 0
		shared.VectorCopy(entities[i].origin, entities[i].oldorigin)
		entities[i].frame = 0
		entities[i].oldframe = 0
		entities[i].backlerp = 0.0
		# one full turn is 3s = 3000ms => 3000/360 deg per millisecond
		entities[i].angles[1] = float(curTime)/(3000.0/360.0)


	PlayerConfig_AnimateModel(entities, 2, curTime)

	refdef.areabits = None # 0
	refdef.num_entities = 2 if (entities[1].model) else 1
	refdef.entities = entities
	refdef.lightstyles = None
	refdef.rdflags = shared.RDF_NOWORLDMODEL

	M_DrawTextBox(int(int(refdef.x) * (320.0 / vid.viddef.width) - 8),
	  int((vid.viddef.height / 2) * (240.0 / vid.viddef.height) - 77),
	  int(refdef.width / (8 * scale)), int(refdef.height / (8 * scale)))
	refdef.height += int(4 * scale)

	vid.R_RenderFrame(refdef)


def PlayerConfig_MenuDraw(m): #menuframework_s * (static)

	PlayerConfig_ModelDraw()
	Default_MenuDraw(m)

def PlayerConfig_MenuClose(m: qmenu_h.menuframework_s): #menuframework_s * (static)

	"""
	const char* name;
	const char *mdl, *img;
	"""

	name = s_player_name_field.buffer
	cvar.Cvar_Set("name", name)

	mdl, img = SelectedModelSkin()
	if mdl and img:

		"""
		char skin[MAX_QPATH];
		"""

		skin = ("%s/%s" % (mdl, img))[:shared.MAX_QPATH - 1] # Com_sprintf

		cvar.Cvar_Set("skin", skin)


	PlayerModelFree() # free player skins, models and directories

	# free player skins, models and directories
	# free player skins, models and directories
	# free player skins, models and directories
	# free player skins, models and directories
	# free player skins, models and directories
	# free player skins, models and directories

def M_Menu_PlayerConfig_f(): # (static)

	if not PlayerConfig_MenuInit():

		qmenu.Menu_SetStatusBar(s_multiplayer_menu, "no valid player models found")
		return


	qmenu.Menu_SetStatusBar(s_multiplayer_menu, None)
	s_player_config_menu.draw = PlayerConfig_MenuDraw
	s_player_config_menu.key = Default_MenuKey
	s_player_config_menu.close = PlayerConfig_MenuClose
	M_PushMenu(s_player_config_menu)

s_quit_menu = qmenu_h.menuframework_s() #menuframework_s

def M_Quit_Key(m, key): #menuframework_s *, int (returns static const char *)

	"""
	int menu_key = Key_GetMenuKey(key);
	"""
	menu_key = Key_GetMenuKey(key)

	if menu_key == keyboard_h.K_ESCAPE or menu_key == 110 or menu_key == 78:

		M_PopMenu(False)

	elif menu_key == keyboard_h.K_ENTER or menu_key == 89 or menu_key == 121:

		cl_main.cls.key_dest = client_h.keydest_t.key_console
		cl_main.CL_Quit_f()

	else:

		pass


	return None

def M_Quit_Draw(m): #menuframework_s * (static)

	"""
	int w, h;
	float scale = SCR_GetMenuScale();
	"""
	scale = cl_screen.SCR_GetMenuScale()

	w, h = vid.Draw_GetPicSize("quit")
	vid.Draw_PicScaled((vid.viddef.width - w * scale) / 2, (vid.viddef.height - h * scale) / 2, "quit", scale)

def M_Menu_Quit_f(): # (static)

	s_quit_menu.draw = M_Quit_Draw
	s_quit_menu.key = M_Quit_Key
	M_PushMenu(s_quit_menu)

def M_Init(): #
	global m_cursor_width

	"""
	char cursorname[MAX_QPATH];
	int w = 0;
	int h = 0;
	"""
	cursorname = [None] * shared.MAX_QPATH
	w = 0
	h = 0

	cmdparser.Cmd_AddCommand("playermodels", ListModels_f)
	cmdparser.Cmd_AddCommand("menu_main", M_Menu_Main_f)
	cmdparser.Cmd_AddCommand("menu_game", M_Menu_Game_f)
	cmdparser.Cmd_AddCommand("menu_loadgame", M_Menu_LoadGame_f)
	cmdparser.Cmd_AddCommand("menu_savegame", M_Menu_SaveGame_f)
	cmdparser.Cmd_AddCommand("menu_joinserver", M_Menu_JoinServer_f)
	cmdparser.Cmd_AddCommand("menu_addressbook", M_Menu_AddressBook_f)
	cmdparser.Cmd_AddCommand("menu_startserver", M_Menu_StartServer_f)
	cmdparser.Cmd_AddCommand("menu_dmoptions", M_Menu_DMOptions_f)
	cmdparser.Cmd_AddCommand("menu_playerconfig", M_Menu_PlayerConfig_f)
	cmdparser.Cmd_AddCommand("menu_downloadoptions", M_Menu_DownloadOptions_f)
	cmdparser.Cmd_AddCommand("menu_credits", M_Menu_Credits_f)
	cmdparser.Cmd_AddCommand("menu_mods", M_Menu_Mods_f)
	cmdparser.Cmd_AddCommand("menu_multiplayer", M_Menu_Multiplayer_f)
	cmdparser.Cmd_AddCommand("menu_multiplayer_keys", M_Menu_Multiplayer_Keys_f)
	cmdparser.Cmd_AddCommand("menu_video", videomenu.M_Menu_Video_f)
	cmdparser.Cmd_AddCommand("menu_options", M_Menu_Options_f)
	cmdparser.Cmd_AddCommand("menu_keys", M_Menu_Keys_f)
	cmdparser.Cmd_AddCommand("menu_joy", M_Menu_Joy_f)
	cmdparser.Cmd_AddCommand("menu_gyro", M_Menu_Gyro_f)
	cmdparser.Cmd_AddCommand("menu_buttons", M_Menu_ControllerButtons_f)
	cmdparser.Cmd_AddCommand("menu_altbuttons", M_Menu_ControllerAltButtons_f)
	cmdparser.Cmd_AddCommand("menu_sticks", M_Menu_Stick_f)
	cmdparser.Cmd_AddCommand("menu_quit", M_Menu_Quit_f)
	# initialize the server address book cvars (adr0, adr1, ...)
	# so the entries are not lost if you don't open the address book
	for index in range(client_h.NUM_ADDRESSBOOK_ENTRIES):

		#char buffer[20];
		buffer = [None] * 20
		buffer = "adr%d" % (index,) # Com_sprintf
		cvar.Cvar_Get(buffer, "", shared.CVAR_ARCHIVE)


	# cache the cursor frames
	for i in range(NUM_CURSOR_FRAMES):

		cursorname = "m_cursor%d" % (i,) # Com_sprintf
		vid.Draw_FindPic(cursorname)
		w, h = vid.Draw_GetPicSize(cursorname)
		if w > m_cursor_width:

			m_cursor_width = w

def M_Draw(): #

	global m_entersound

	"""
	menuframework_s *menu;
	"""

	if cl_main.cls.key_dest != client_h.keydest_t.key_menu:

		return


	# repaint everything next frame
	cl_screen.SCR_DirtyScreen()
	# dim everything behind it down
	if cl_main.cl.cinematictime > 0:

		vid.Draw_Fill(0, 0, vid.viddef.width, vid.viddef.height, 0)

	else:

		vid.Draw_FadeScreen()


	menu = M_GetActiveMenu()
	if menu and menu.draw:

		menu.draw(menu)


	# delay playing the enter sound until after the
	# menu has been drawn, to avoid delay while
	# caching images
	if m_entersound:

		sound_c.S_StartLocalSound(qmenu.menu_in_sound)
		m_entersound = False

def M_Keydown(key): #int

	"""
	menuframework_s *menu;
	"""

	menu = M_GetActiveMenu()
	if menu and menu.key:

		#const char *s;
		s = menu.key(menu, key)
		if s:

			sound_c.S_StartLocalSound(s)

def M_Free(): #

	Mods_NamesFinish()
	CleanCachedMapsList()
	PlayerModelFree()

