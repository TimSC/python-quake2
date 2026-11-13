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

This file implements the 2D stuff. For example the HUD and the
networkgraph.

=======================================================================
"""
from __future__ import annotations

import numpy as np
from common import pmove
from common.shared import shared as shared_c
from backends.unix import system

import math

from client.sound import ogg
from client.sound.header import vorbis

import numpy as np
from client.vid import vid

import copy
from client import cl_main, cl_cin, cl_view
from client.sound import sound as sound_c
from backends.unix import system
from client.vid import vid
from common.header import shared
from common import clientserver
from common import cmdparser
from common import cvar
from common import frame as common_frame
from common import movemsg
from client import cl_console
from client import cl_inventory
from client import cl_main
from client import cl_view
from client.header import client as client_h
from client.vid.header import vid as vid_h
from client.menu import menu

"""
#include "header/client.h"
"""

scr_con_current = 0.0 #float, aproaches scr_conlines at scr_conspeed
scr_conlines = 0.0 #float, 0.0 to 1.0 lines of console to display

scr_initialized = False # qboolean, ready to draw
scr_draw_loading = 0 #int

scr_vrect = vid_h.vrect_t() #position of render window on screen

scr_viewsize = None #cvar_t		*
scr_conspeed = None #cvar_t		*
scr_centertime = None #cvar_t		*
scr_showturtle = None #cvar_t		*
scr_showpause = None #cvar_t		*
scr_printspeed = None #cvar_t		*

scr_netgraph = None #cvar_t		*
scr_timegraph = None #cvar_t		*
scr_debuggraph = None #cvar_t		*
scr_graphheight = None #cvar_t		*
scr_graphscale = None #cvar_t		*
scr_graphshift = None #cvar_t		*
scr_drawall = None #cvar_t		*


STAT_MINUS = 10
CHAR_SIZE = 8
CHARACTER_WIDTH = 16
CHAR_WIDTH = 16

sb_nums = [
	["num_0","num_1","num_2","num_3","num_4","num_5","num_6","num_7","num_8","num_9","num_minus"],
	["anum_0","anum_1","anum_2","anum_3","anum_4","anum_5","anum_6","anum_7","anum_8","anum_9","anum_minus"],
]


scr_centerstring = ""
scr_centertime_start = 0.0
scr_centertime_off = 0.0
scr_center_lines = 0
scr_erase_center = 0

crosshair_pic = ""
crosshair_width = 0
crosshair_height = 0


STAT_LAYOUTS = 13
class graphsamp_t(object):

	def __init__(self):

		self.value = 0.0 #float
		self.color = 0 #int

current = 0 #static int
values = [] #static graphsamp_t [2024]
for i in range(2024):
	values.append(graphsamp_t())
r_hudscale = None #cvar_t *
r_consolescale = None #cvar_t *
r_menuscale = None #cvar_t *

class dirty_t(object):

	def __init__(self):
		self.x1 = 0
		self.y1 = 0
		self.x2 = 0
		self.y2 = 0


scr_dirty = dirty_t()
scr_old_dirty = [dirty_t(), dirty_t()]
"""
/*
===============================================================================

BAR GRAPHS

===============================================================================
*/
"""
"""
/*
==============
CL_AddNetgraph

A new packet was just parsed
==============
"""
"""
char		crosshair_pic[MAX_QPATH];
int			crosshair_width, crosshair_height;

"""
def CL_AddNetgraph(): #

	"""
	int i;
	int in;
	int ping;
	"""

	# if using the debuggraph for something
	# else, don't add the net lines
	if scr_debuggraph.value or scr_timegraph.value:

		return


	for i in range(cl_main.cls.netchan.dropped):

		SCR_DebugGraph(30, 0x40)


	for i in range(cl_main.cl.surpressCount):

		SCR_DebugGraph(30, 0xdf)


	# see what the latency was on this packet
	in_ = cl_main.cls.netchan.incoming_acknowledged & (client_h.CMD_BACKUP - 1)
	ping = cl_main.cls.realtime - cl_main.cl.cmd_time[in_]
	ping = int(ping / 30) # C int
	if ping > 30:

		ping = 30


	SCR_DebugGraph(ping, 0xd0)


def SCR_DebugGraph(value, color): #float, int
	global current

	values[current & 2023].value = value
	values[current & 2023].color = color
	current += 1


def SCR_DrawDebugGraph(): # (static)

	"""
	int a, x, y, w, i, h;
	float v;
	int color;
	"""

	# draw the graph
	w = scr_vrect.width
	x = scr_vrect.x
	y = scr_vrect.y + scr_vrect.height
	vid.Draw_Fill(x, y - scr_graphheight.value, w, scr_graphheight.value, 8)
	for a in range(w):

		i = (current - 1 - a + 1024) & 1023
		v = values[i].value
		color = values[i].color
		v = v * scr_graphscale.value + scr_graphshift.value
		if v < 0:

			v += scr_graphheight.value * \
				 (1 + int(-v / scr_graphheight.value))


		h = int(math.fmod(int(v), int(scr_graphheight.value))) # (int)v % (int)scr_graphheight->value
		vid.Draw_Fill(x + w - 1 - a, y - h, 1, h, color)


def SCR_CenterPrint(str_: str): #char *

	global scr_centerstring, scr_centertime_off, scr_centertime_start, scr_center_lines

	"""
	char *s;
	"""

	scr_centerstring = str_[:1024 - 1] # Q_strlcpy(scr_centerstring, str, sizeof(scr_centerstring));
	scr_centertime_off = scr_centertime.value
	scr_centertime_start = cl_main.cl.time

	# count the number of lines for centering
	scr_center_lines = 1 + str_.count("\n")

	# echo it to the console
	clientserver.Com_Printf("\n\n\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n\n")

	s = 0 # Q2PORT: an offset into str

	while True:

		#char line[64];
		#int i, j, l;

		# scan the width of the line
		l = 0
		while l < 40:

			if (s + l >= len(str_)) or (str_[s + l] == '\n'):

				break


			l += 1


		line = " " * ((40 - l) // 2)
		line += str_[s:s + l]
		line += "\n"

		clientserver.Com_Printf("%s", line)

		while s < len(str_) and str_[s] != '\n':

			s += 1


		if s >= len(str_):

			break


		s += 1 # skip the \n


	clientserver.Com_Printf("\n\n\35\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\36\37\n\n")
	cl_console.Con_ClearNotify()



def SCR_DrawCenterString(): #void (static)

	global scr_erase_center

	"""
	char *start;
	int l;
	int j;
	int x, y;
	int remaining;
	float scale;
	const int char_unscaled_width  = 8;
	const int char_unscaled_height = 8;
	"""
	char_unscaled_width = 8
	char_unscaled_height = 8

	# the finale prints the characters one at a time
	remaining = 9999

	scr_erase_center = 0
	start = 0 # Q2PORT: an offset into scr_centerstring
	scale = SCR_GetConsoleScale()

	if scr_center_lines <= 4:

		y = int((vid.viddef.height * 0.35) / scale)

	else:

		y = int(48 / scale)


	while True:

		# scan the width of the line
		l = 0
		while l < 40:

			if (start + l >= len(scr_centerstring)) or (scr_centerstring[start + l] == '\n'):

				break


			l += 1


		x = int(((vid.viddef.width / scale) - (l * char_unscaled_width)) / 2)
		SCR_AddDirtyPoint(x, y)

		for j in range(l):

			vid.Draw_CharScaled(x * scale, y * scale, ord(scr_centerstring[start + j]), scale)

			if not remaining:

				return


			remaining -= 1
			x += char_unscaled_width


		SCR_AddDirtyPoint(x, y + char_unscaled_height)

		y += char_unscaled_height

		while start < len(scr_centerstring) and scr_centerstring[start] != '\n':

			start += 1


		if start >= len(scr_centerstring):

			break


		start += 1 # skip the \n



def SCR_CheckDrawCenterString(): # (static)
	global scr_centertime_off

	scr_centertime_off -= cl_main.cls.rframetime
	if scr_centertime_off <= 0:

		return


	SCR_DrawCenterString()


"""
=================
SCR_CalcVrect

Sets scr_vrect, the coordinates of the rendered window
=================
"""
def SCR_CalcVrect(): # (static)

	"""
	int size;
	"""

	# bound viewsize
	if scr_viewsize.value < 40:

		cvar.Cvar_Set("viewsize", "40")


	if scr_viewsize.value > 100:

		cvar.Cvar_Set("viewsize", "100")


	size = scr_viewsize.value
	scr_vrect.width = vid.viddef.width * size / 100
	scr_vrect.height = vid.viddef.height * size / 100
	scr_vrect.x = (vid.viddef.width - scr_vrect.width) / 2
	scr_vrect.y = (vid.viddef.height - scr_vrect.height) / 2


"""
=================
SCR_SizeUp_f

Keybinding command
=================
"""
def SCR_SizeUp_f(): # (static)

	cvar.Cvar_SetValue("viewsize", scr_viewsize.value + 10)


"""
=================
SCR_SizeDown_f

Keybinding command
=================
"""
def SCR_SizeDown_f(): # (static)

	cvar.Cvar_SetValue("viewsize", scr_viewsize.value - 10)


"""
=================
SCR_Sky_f

Set a specific sky and rotation speed
=================
"""
def SCR_Sky_f(): #void (static)

	"""
	float rotate = 0;
	vec3_t axis;
	"""
	rotate = 0
	axis = np.zeros((3,), dtype=np.float32)

	if cmdparser.Cmd_Argc() < 2:

		clientserver.Com_Printf("Usage: sky <basename> <rotate> <axis x y z>\n")
		return


	if cmdparser.Cmd_Argc() > 2:

		rotate = float(shared_c.atof(cmdparser.Cmd_Argv(2)))

	else:

		rotate = 0


	if cmdparser.Cmd_Argc() == 6:

		axis[0] = float(shared_c.atof(cmdparser.Cmd_Argv(3)))
		axis[1] = float(shared_c.atof(cmdparser.Cmd_Argv(4)))
		axis[2] = float(shared_c.atof(cmdparser.Cmd_Argv(5)))

	else:

		axis[0] = 0
		axis[1] = 0
		axis[2] = 1


	vid.R_SetSky(cmdparser.Cmd_Argv(1), rotate, axis)


# ================================================================================

"""
==================
SCR_Init
==================
"""
def SCR_Init(): #
	global r_consolescale, r_hudscale, r_menuscale, scr_centertime, scr_conspeed, scr_debuggraph, scr_drawall, scr_graphheight, scr_graphscale, scr_graphshift, scr_initialized, scr_netgraph, scr_showpause, scr_showturtle, scr_timegraph, scr_viewsize

	scr_viewsize = cvar.Cvar_Get("viewsize", "100", shared.CVAR_ARCHIVE)
	scr_conspeed = cvar.Cvar_Get("scr_conspeed", "3", 0)
	scr_centertime = cvar.Cvar_Get("scr_centertime", "2.5", 0)
	scr_showturtle = cvar.Cvar_Get("scr_showturtle", "0", 0)
	scr_showpause = cvar.Cvar_Get("scr_showpause", "1", 0)
	scr_netgraph = cvar.Cvar_Get("netgraph", "0", 0)
	scr_timegraph = cvar.Cvar_Get("timegraph", "0", 0)
	scr_debuggraph = cvar.Cvar_Get("debuggraph", "0", 0)
	scr_graphheight = cvar.Cvar_Get("graphheight", "32", 0)
	scr_graphscale = cvar.Cvar_Get("graphscale", "1", 0)
	scr_graphshift = cvar.Cvar_Get("graphshift", "0", 0)
	scr_drawall = cvar.Cvar_Get("scr_drawall", "0", 0)
	r_hudscale = cvar.Cvar_Get("r_hudscale", "-1", shared.CVAR_ARCHIVE)
	r_consolescale = cvar.Cvar_Get("r_consolescale", "-1", shared.CVAR_ARCHIVE)
	r_menuscale = cvar.Cvar_Get("r_menuscale", "-1", shared.CVAR_ARCHIVE)
	# register our commands
	cmdparser.Cmd_AddCommand("timerefresh", SCR_TimeRefresh_f)
	cmdparser.Cmd_AddCommand("loading", SCR_Loading_f)
	cmdparser.Cmd_AddCommand("sizeup", SCR_SizeUp_f)
	cmdparser.Cmd_AddCommand("sizedown", SCR_SizeDown_f)
	cmdparser.Cmd_AddCommand("sky", SCR_Sky_f)
	scr_initialized = True

"""
==============
SCR_DrawNet
==============
"""
def SCR_DrawNet(): # (static)

	"""
	float scale = SCR_GetMenuScale();
	"""
	scale = SCR_GetMenuScale()

	if cl_main.cls.netchan.outgoing_sequence - cl_main.cls.netchan.incoming_acknowledged < client_h.CMD_BACKUP - 1:

		return


	vid.Draw_PicScaled(scr_vrect.x + 64 * scale, scr_vrect.y, "net", scale)

"""
==============
SCR_DrawPause
==============
"""
def SCR_DrawPause(): # (static)

	"""
	int w, h;
	float scale = SCR_GetMenuScale();
	"""
	scale = SCR_GetMenuScale()

	if not scr_showpause.value:

		# turn off for screenshots
		return


	if not cl_main.cl_paused.value:

		return


	w, h = vid.Draw_GetPicSize("pause")
	vid.Draw_PicScaled((vid.viddef.width - w * scale) / 2, vid.viddef.height / 2 + 8 * scale, "pause", scale)

"""
==============
SCR_DrawLoading
==============
"""
def SCR_DrawLoading(): # (static)

	"""
	int w, h;
	float scale = SCR_GetMenuScale();
	"""
	scale = SCR_GetMenuScale()

	if not scr_draw_loading:

		return


	w, h = vid.Draw_GetPicSize("loading")
	vid.Draw_PicScaled((vid.viddef.width - w * scale) / 2, (vid.viddef.height - h * scale) / 2, "loading", scale)


# ================================================================================

"""
==================
SCR_RunConsole

Scroll it up or down
==================
"""
def SCR_RunConsole(): #
	global scr_con_current, scr_conlines

	# src_conspeed must be a positiv integer,
	# otherwise things go wrong. Clamp it.
	if scr_conspeed.value < 0.1:

		cvar.Cvar_Set("scr_conspeed", "0.1")


	# decide on the height of the console
	if cl_main.cls.key_dest == client_h.keydest_t.key_console:

		scr_conlines = 0.5
		# half screen

	else:

		scr_conlines = 0
		# none visible


	if scr_conlines < scr_con_current:

		scr_con_current -= scr_conspeed.value * cl_main.cls.rframetime
		if scr_conlines > scr_con_current:

			scr_con_current = scr_conlines


	elif scr_conlines > scr_con_current:

		scr_con_current += scr_conspeed.value * cl_main.cls.rframetime
		if scr_conlines < scr_con_current:

			scr_con_current = scr_conlines
	

"""
==================
SCR_DrawConsole
==================
"""
def SCR_DrawConsole(): # (static)

	cl_console.Con_CheckResize()
	if (cl_main.cls.state == client_h.connstate_t.ca_disconnected) or (cl_main.cls.state == client_h.connstate_t.ca_connecting):

		# forced full screen console
		cl_console.Con_DrawConsole(1.0)
		return


	if (cl_main.cls.state != client_h.connstate_t.ca_active) or not cl_main.cl.refresh_prepped:

		# connected, but can't render
		cl_console.Con_DrawConsole(0.5)
		vid.Draw_Fill(0, vid.viddef.height / 2, vid.viddef.width, vid.viddef.height / 2, 0)
		return


	if scr_con_current:

		cl_console.Con_DrawConsole(scr_con_current)

	else:

		if (cl_main.cls.key_dest == client_h.keydest_t.key_game) or (cl_main.cls.key_dest == client_h.keydest_t.key_message):

			cl_console.Con_DrawNotify()
			# only draw notify in game
	


"""
# ================================================================================

================
SCR_BeginLoadingPlaque
================
"""
def SCR_BeginLoadingPlaque(): #
	global scr_draw_loading

	sound_c.S_StopAllSounds()
	cl_main.cl.sound_prepped = False
	# don't play ambients
	ogg.OGG_Stop()
	if cl_main.cls.disable_screen:

		return


	if common_frame.developer.value:

		# Hack: When we are returning here (not drawing
		# the loading plaque) we don't reset the palette
		# later on. We might end up with the cinematic
		# palette applied to the world. Enforce the world
		# palette.
		if cl_main.cl.cinematictime > 0:

			vid.R_SetPalette(None)


		return


	if cl_main.cls.state == client_h.connstate_t.ca_disconnected:

		# if at console, don't bring up the plaque
		return


	if cl_main.cls.key_dest == client_h.keydest_t.key_console:

		return


	if cl_main.cl.cinematictime > 0:

		scr_draw_loading = 2
		# clear to balack first

	else:

		scr_draw_loading = 1


	SCR_UpdateScreen()
	scr_draw_loading = False
	cl_cin.SCR_StopCinematic()
	cl_main.cls.disable_screen = system.Sys_Milliseconds()
	cl_main.cls.disable_servercount = cl_main.cl.servercount
	#cl_main.cls.disable_servercount = cl_main.cl.servercount;


"""
================
SCR_EndLoadingPlaque
================
"""
def SCR_EndLoadingPlaque(): #

	cl_main.cls.disable_screen = 0
	cl_console.Con_ClearNotify()

"""
================
SCR_Loading_f
================
"""
def SCR_Loading_f ():

	SCR_BeginLoadingPlaque ()

def SCR_TimeRefresh_f(): # (static)

	"""
	int i;
	int start, stop;
	float time;
	"""

	if cl_main.cls.state != client_h.connstate_t.ca_active:

		return


	start = system.Sys_Milliseconds()
	if cmdparser.Cmd_Argc() == 2:

		# run without page flipping
		#int j;
		for j in range(1000):

			vid.R_BeginFrame(0)
			for i in range(128):

				cl_main.cl.refdef.viewangles[1] = i / 128.0 * 360.0
				vid.R_RenderFrame(cl_main.cl.refdef)


			vid.R_EndFrame()


	else:

		for i in range(128):

			cl_main.cl.refdef.viewangles[1] = i / 128.0 * 360.0
			vid.R_BeginFrame(0)
			vid.R_RenderFrame(cl_main.cl.refdef)
			vid.R_EndFrame()


	stop = system.Sys_Milliseconds()
	time = (stop - start) / 1000.0
	clientserver.Com_Printf("%f seconds (%f fps)\n", time, 128 / time)

"""
=================
SCR_AddDirtyPoint
=================
"""
def SCR_AddDirtyPoint (x, y):

	global scr_dirty
	
	if x < scr_dirty.x1:
		scr_dirty.x1 = x
	if x > scr_dirty.x2:
		scr_dirty.x2 = x
	if y < scr_dirty.y1:
		scr_dirty.y1 = y
	if y > scr_dirty.y2:
		scr_dirty.y2 = y

def SCR_DirtyScreen ():

	SCR_AddDirtyPoint (0, 0)
	SCR_AddDirtyPoint (vid.viddef.width-1, vid.viddef.height-1)


"""
==============
SCR_TileClear

Clear any parts of the tiled background that were drawn on last frame
==============
"""
def SCR_TileClear(): # (static)

	"""
	int i;
	int top, bottom, left, right;
	dirty_t clear;
	"""

	if scr_con_current == 1.0:

		return
		# full screen console


	if scr_viewsize.value == 100:

		return
		# full screen rendering


	if cl_main.cl.cinematictime > 0:

		return
		# full screen cinematic


	# This highly complicated pseudo damage tracking is very effective
	# with the soft render, it gives about 10% speedup. On the GL
	# renderers the speedup is negligible, but in introduce a bug:
	# OpenGL requires to redraw the borders after every glClear(),
	# which the damage tracking doesn't take into account. Fix this
	# by not using the damage tracking when running somethinge else
	# than the soft renderer. Just redraw the borders every frame.
	if (vid.vid_renderer.string != "soft"):

		# Top
		vid.Draw_TileClear(scr_vrect.x, 0, scr_vrect.width, scr_vrect.y, "backtile")
		# Bottom
		vid.Draw_TileClear(scr_vrect.x, scr_vrect.y + scr_vrect.height, scr_vrect.width, vid.viddef.height, "backtile")
		# Left
		vid.Draw_TileClear(0, 0, scr_vrect.x, vid.viddef.height, "backtile")
		# Right
		vid.Draw_TileClear(scr_vrect.x + scr_vrect.width, 0, vid.viddef.width, vid.viddef.height, "backtile")

	else:

		# erase rect will be the union of the past three
		# frames so tripple buffering works properly
		clear = scr_dirty
		for i in range(2):

			if scr_old_dirty[i].x1 < clear.x1:

				clear.x1 = scr_old_dirty[i].x1


			if scr_old_dirty[i].x2 > clear.x2:

				clear.x2 = scr_old_dirty[i].x2


			if scr_old_dirty[i].y1 < clear.y1:

				clear.y1 = scr_old_dirty[i].y1


			if scr_old_dirty[i].y2 > clear.y2:

				clear.y2 = scr_old_dirty[i].y2


		scr_old_dirty[1] = scr_old_dirty[0]
		scr_old_dirty[0] = scr_dirty
		scr_dirty.x1 = 9999
		scr_dirty.x2 = -9999
		scr_dirty.y1 = 9999
		scr_dirty.y2 = -9999
		# don't bother with anything convered by the console
		top = (scr_con_current * vid.viddef.height)
		if top >= clear.y1:

			clear.y1 = top


		if clear.y2 <= clear.y1:

			return
			# nothing disturbed


		top = scr_vrect.y
		bottom = top + scr_vrect.height - 1
		left = scr_vrect.x
		right = left + scr_vrect.width - 1
		if clear.y1 < top:

			# clear above view screen
			i = (clear.y2 if clear.y2 < top - 1 else top - 1)
			vid.Draw_TileClear(clear.x1, clear.y1, clear.x2 - clear.x1 + 1, i - clear.y1 + 1, "backtile")
			clear.y1 = top


		if clear.y2 > bottom:

			# clear below view screen
			i = (clear.y1 if clear.y1 > bottom + 1 else bottom + 1)
			vid.Draw_TileClear(clear.x1, i, clear.x2 - clear.x1 + 1, clear.y2 - i + 1, "backtile")
			clear.y2 = bottom


		if clear.x1 < left:

			# clear left of view screen
			i = (clear.x2 if clear.x2 < left - 1 else left - 1)
			vid.Draw_TileClear(clear.x1, clear.y1, i - clear.x1 + 1, clear.y2 - clear.y1 + 1, "backtile")
			clear.x1 = left


		if clear.x2 > right:

			# clear left of view screen
			i = (clear.x1 if clear.x1 > right + 1 else right + 1)
			vid.Draw_TileClear(i, clear.y1, clear.x2 - i + 1, clear.y2 - clear.y1 + 1, "backtile")
			clear.x2 = right
	


"""
#===============================================================

# C layout constants used by the status bar logic are defined earlier (see STAT_MINUS/CHAR_WIDTH).
"""

"""
================
SizeHUDString

Allow embedded \n in the string
================
"""
def SizeHUDString (string):

	lines = string.split('\n') if string else ['']
	width = 0
	for line in lines:
		if len(line) > width:
			width = len(line)
	return width * 8, len(lines) * 8


def DrawHUDStringScaled(string: str, x: int, y: int, centerwidth: int, xor: int, factor: float): #const char *, int, int, int, int, float

	"""
	int margin;
	int i;
	"""

	margin = x

	p = 0 # Q2PORT: an offset into string
	while p < len(string):

		# scan out one line of text from the string
		#int width;
		#char line[1024];

		width = 0
		line = ""

		while p < len(string) and string[p] != '\n':

			line += string[p]
			p += 1
			width += 1


		if centerwidth:

			x = int(margin + (centerwidth - width * 8)*factor / 2)

		else:

			x = margin


		for i in range(width):

			vid.Draw_CharScaled(x, y, ord(line[i]) ^ xor, factor)
			x += 8*factor


		if p < len(string):

			p += 1 # skip the \n
			y += CHAR_SIZE * factor


def DrawHUDString(string, x, y, centerwidth, xor): #char *, int, int, int, int

	DrawHUDStringScaled(string, x, y, centerwidth, xor, 1.0)


def DrawString (x, y, string):
	DrawHUDString (string, x, y, 0, 0)


def DrawAltString (x, y, string):
	DrawHUDString (string, x, y, 0, 0x80)


def SCR_DrawFieldScaled(x: int, y: int, color: int, width: int, value: int, factor: float): #int, int, int, int, int, float

	"""
	char num[16], *ptr;
	int l;
	int frame;
	"""

	if width < 1:

		return


	# draw number string
	if width > 5:

		width = 5


	SCR_AddDirtyPoint(x, y)
	SCR_AddDirtyPoint(x + (width * CHARACTER_WIDTH + 2) * factor, y + factor * 24)

	num = ("%i" % value)[:16 - 1]
	l = len(num)

	if l > width:

		l = width


	x += (2 + CHARACTER_WIDTH * (width - l)) * factor

	for ch in num: # ptr = num; while (*ptr && l)

		if not l:

			break


		if ch == '-':

			frame = STAT_MINUS

		else:

			frame = ord(ch) - ord('0')


		vid.Draw_PicScaled(x, y, sb_nums[color][frame], factor)
		x += CHARACTER_WIDTH * factor
		l -= 1


"""
==============
SCR_DrawField
==============
"""
def SCR_DrawField(x: int, y: int, color: int, width: int, value: int): #int, int, int, int, int

	SCR_DrawFieldScaled(x, y, color, width, value, 1.0)

	

def SCR_TouchPics(): #

	global crosshair_pic, crosshair_width, crosshair_height

	"""
	int i, j;
	"""

	for i in range(2):

		for j in range(11):

			vid.Draw_FindPic(sb_nums[i][j])


	if cl_view.crosshair.value:

		if (cl_view.crosshair.value > 3) or (cl_view.crosshair.value < 0):

			cl_view.crosshair.value = 3


		crosshair_pic = "ch%i" % (int(cl_view.crosshair.value),) # Com_sprintf
		crosshair_width, crosshair_height = vid.Draw_GetPicSize(crosshair_pic)
		if not crosshair_width:

			crosshair_pic = "" # crosshair_pic[0] = 0
	


"""
================
SCR_ExecuteLayoutString 

================
"""
def SCR_ExecuteLayoutString(s: str): #char * (static)

	"""
	int x, y;
	float scale;
	"""

	cl = cl_main.cl
	viddef = vid.viddef
	atoi = shared_c.atoi # (int)strtol(token, (char **)NULL, 10)

	scale = SCR_GetHUDScale()

	if (cl_main.cls.state != client_h.connstate_t.ca_active) or not cl.refresh_prepped:

		return


	if not s:

		return


	x = 0
	y = 0

	cursor = 0 # Q2PORT: s is the text and an offset into it (None for NULL)
	while cursor is not None:

		#const char *token;

		token, cursor = shared_c.COM_Parse(s, cursor)

		if token == "xl":

			token, cursor = shared_c.COM_Parse(s, cursor)
			x = int(scale * atoi(token))
			continue


		if token == "xr":

			token, cursor = shared_c.COM_Parse(s, cursor)
			x = int(viddef.width + scale * atoi(token))
			continue


		if token == "xv":

			token, cursor = shared_c.COM_Parse(s, cursor)
			x = int(viddef.width / 2 - scale * 160 + scale * atoi(token))
			continue


		if token == "yt":

			token, cursor = shared_c.COM_Parse(s, cursor)
			y = int(scale * atoi(token))
			continue


		if token == "yb":

			token, cursor = shared_c.COM_Parse(s, cursor)
			y = int(viddef.height + scale * atoi(token))
			continue


		if token == "yv":

			token, cursor = shared_c.COM_Parse(s, cursor)
			y = int(viddef.height / 2 - scale * 120 + scale * atoi(token))
			continue


		if token == "pic":

			#int index, value;

			# draw a pic from a stat number
			token, cursor = shared_c.COM_Parse(s, cursor)
			index = atoi(token)

			if (index < 0) or (index >= shared.MAX_STATS):

				clientserver.Com_DPrintf("%s: bad stats index %d (0x%x) in pic\n",
					"SCR_ExecuteLayoutString", index, index)
				continue


			value = cl.frame.playerstate.stats[index]

			if value >= shared.MAX_IMAGES:

				clientserver.Com_DPrintf("%s: Pic %d >= MAX_IMAGES in pic\n",
					"SCR_ExecuteLayoutString", value)
				continue


			if cl.configstrings[shared.CS_IMAGES + value]:

				#const char *text;
				#int w, h;

				text = cl.configstrings[shared.CS_IMAGES + value]
				w, h = vid.Draw_GetPicSize(text)
				SCR_AddDirtyPoint(x, y)
				SCR_AddDirtyPoint(x + (w - 1) * scale, y + (h - 1) * scale)
				vid.Draw_PicScaled(x, y, text, scale)


			continue


		if token == "client":

			# draw a deathmatch client block
			#int score, ping, time, value;
			#clientinfo_t *ci;

			token, cursor = shared_c.COM_Parse(s, cursor)
			x = int(viddef.width / 2 - scale * 160 + scale * atoi(token))
			token, cursor = shared_c.COM_Parse(s, cursor)
			y = int(viddef.height / 2 - scale * 120 + scale * atoi(token))
			SCR_AddDirtyPoint(x, y)
			SCR_AddDirtyPoint(x + scale * 159, y + scale * 31)

			token, cursor = shared_c.COM_Parse(s, cursor)
			value = atoi(token)

			if (value >= shared.MAX_CLIENTS) or (value < 0):

				clientserver.Com_DPrintf("%s: client >= MAX_CLIENTS in client\n", "SCR_ExecuteLayoutString")
				continue


			ci = cl.clientinfo[value]

			token, cursor = shared_c.COM_Parse(s, cursor)
			score = atoi(token)

			token, cursor = shared_c.COM_Parse(s, cursor)
			ping = atoi(token)

			token, cursor = shared_c.COM_Parse(s, cursor)
			time = atoi(token)

			cl_console.DrawAltStringScaled(x + scale * 32, y, ci.name, scale)
			cl_console.DrawAltStringScaled(x + scale * 32, y + scale * CHAR_SIZE, "Score: ", scale)
			cl_console.DrawAltStringScaled(x + scale * (32 + 7 * CHAR_SIZE), y + scale * CHAR_SIZE, "%i" % score, scale)
			cl_console.DrawStringScaled(x + scale * 32, y + scale * 16, "Ping:  %i" % ping, scale)
			cl_console.DrawStringScaled(x + scale * 32, y + scale * 24, "Time:  %i" % time, scale)

			if not ci.icon:

				ci = cl.baseclientinfo


			vid.Draw_PicScaled(x, y, ci.iconname, scale)
			continue


		if token == "ctf":

			# draw a ctf client block
			#int score, ping, value;
			#clientinfo_t *ci;
			#char block[80];

			token, cursor = shared_c.COM_Parse(s, cursor)
			x = int(viddef.width / 2 - scale * 160 + scale*atoi(token))
			token, cursor = shared_c.COM_Parse(s, cursor)
			y = int(viddef.height / 2 - scale * 120 + scale*atoi(token))
			SCR_AddDirtyPoint(x, y)
			SCR_AddDirtyPoint(x + scale * 159, y + scale * 31)

			token, cursor = shared_c.COM_Parse(s, cursor)
			value = atoi(token)

			if (value >= shared.MAX_CLIENTS) or (value < 0):

				clientserver.Com_DPrintf("%s: client >= MAX_CLIENTS in client\n", "SCR_ExecuteLayoutString")
				continue


			ci = cl.clientinfo[value]

			token, cursor = shared_c.COM_Parse(s, cursor)
			score = atoi(token)

			token, cursor = shared_c.COM_Parse(s, cursor)
			ping = atoi(token)

			if ping > 999:

				ping = 999


			block = "%3d %3d %-12.12s" % (score, ping, ci.name)

			if value == cl.playernum:

				cl_console.DrawAltStringScaled(x, y, block, scale)

			else:

				cl_console.DrawStringScaled(x, y, block, scale)


			continue


		if token == "picn":

			#int w, h;

			# draw a pic from a name
			token, cursor = shared_c.COM_Parse(s, cursor)
			w, h = vid.Draw_GetPicSize(token)
			SCR_AddDirtyPoint(x, y)
			SCR_AddDirtyPoint(x + scale * (w - 1), y + scale * (h - 1))
			vid.Draw_PicScaled(x, y, token, scale)
			continue


		if token == "num":

			#int value, width;

			# draw a number
			token, cursor = shared_c.COM_Parse(s, cursor)
			width = atoi(token)
			token, cursor = shared_c.COM_Parse(s, cursor)
			value = cl.frame.playerstate.stats[atoi(token)]
			SCR_DrawFieldScaled(x, y, 0, width, value, scale)
			continue


		if token == "hnum":

			# health number
			#int color, value, width;

			width = 3
			value = cl.frame.playerstate.stats[shared.STAT_HEALTH]

			if value > 25:

				color = 0 # green

			elif value > 0:

				color = (cl.frame.serverframe >> 2) & 1 # flash

			else:

				color = 1


			if cl.frame.playerstate.stats[shared.STAT_FLASHES] & 1:

				vid.Draw_PicScaled(x, y, "field_3", scale)


			SCR_DrawFieldScaled(x, y, color, width, value, scale)
			continue


		if token == "anum":

			# ammo number
			#int color, value, width;

			width = 3
			value = cl.frame.playerstate.stats[shared.STAT_AMMO]

			if value > 5:

				color = 0 # green

			elif value >= 0:

				color = (cl.frame.serverframe >> 2) & 1 # flash

			else:

				continue # negative number = don't show


			if cl.frame.playerstate.stats[shared.STAT_FLASHES] & 4:

				vid.Draw_PicScaled(x, y, "field_3", scale)


			SCR_DrawFieldScaled(x, y, color, width, value, scale)
			continue


		if token == "rnum":

			# armor number
			#int color, value, width;

			width = 3
			value = cl.frame.playerstate.stats[shared.STAT_ARMOR]

			if value < 1:

				continue


			color = 0 # green

			if cl.frame.playerstate.stats[shared.STAT_FLASHES] & 2:

				vid.Draw_PicScaled(x, y, "field_3", scale)


			SCR_DrawFieldScaled(x, y, color, width, value, scale)
			continue


		if token == "stat_string":

			#int index;

			token, cursor = shared_c.COM_Parse(s, cursor)
			index = atoi(token)

			if (index < 0) or (index >= shared.MAX_STATS):

				clientserver.Com_DPrintf("%s: bad stats index %d (0x%x) in stat_string\n",
					"SCR_ExecuteLayoutString", index, index)
				continue


			index = cl.frame.playerstate.stats[index]

			if (index < 0) or (index >= shared.MAX_CONFIGSTRINGS):

				clientserver.Com_DPrintf("%s: bad stats index %d (0x%x) in stat_string\n",
					"SCR_ExecuteLayoutString", index, index)
				continue


			cl_console.DrawStringScaled(x, y, cl.configstrings[index], scale)
			continue


		if token == "cstring":

			token, cursor = shared_c.COM_Parse(s, cursor)
			DrawHUDStringScaled(token, x, y, 320, 0, scale) # FIXME: or scale 320 here?
			continue


		if token == "string":

			token, cursor = shared_c.COM_Parse(s, cursor)
			cl_console.DrawStringScaled(x, y, token, scale)
			continue


		if token == "cstring2":

			token, cursor = shared_c.COM_Parse(s, cursor)
			DrawHUDStringScaled(token, x, y, 320, 0x80, scale) # FIXME: or scale 320 here?
			continue


		if token == "string2":

			token, cursor = shared_c.COM_Parse(s, cursor)
			cl_console.DrawAltStringScaled(x, y, token, scale)
			continue


		if token == "if":

			#int index, value;

			# draw a number
			token, cursor = shared_c.COM_Parse(s, cursor)
			index = atoi(token)

			if (index < 0) or (index >= shared.MAX_STATS):

				clientserver.Com_DPrintf("%s: bad stats index %d (0x%x) in if\n",
					"SCR_ExecuteLayoutString", index, index)
				value = 0

			else:

				value = cl.frame.playerstate.stats[index]


			if not value:

				# skip to endif
				while cursor is not None and token != "endif":

					token, cursor = shared_c.COM_Parse(s, cursor)



			continue


		if token == "endif" or not token:

			# just skip endif and empty line
			continue


		clientserver.Com_DPrintf("%s: Unknown token: %s\n", "SCR_ExecuteLayoutString", token)

		

# =============================================================================== # End layout parsing

def SCR_DrawStats ():

	SCR_ExecuteLayoutString (cl_main.cl.configstrings[shared.CS_STATUSBAR])


def SCR_DrawLayout ():
	if not cl_main.cl.frame.playerstate.stats[shared.STAT_LAYOUTS]:
		return
	SCR_ExecuteLayoutString (cl_main.cl.layout)
# ================================================================================

def SCR_DrawSpeed(): #void (static)

	if cl_main.cl_showspeed.value < 1: # Disabled, do nothing

		return


	#char spd_str[32];
	#float speed, speedxy;
	#float scale = SCR_GetConsoleScale();
	#int str_len, xPos, yPos = 0;
	scale = SCR_GetConsoleScale()
	yPos = 0

	speed, speedxy = pmove.GetPlayerSpeed()
	spd_str = "%6.2f (%6.2f) QU/s" % (speed, speedxy)
	str_len = int(scale * (len(spd_str) * CHAR_SIZE + 2))

	if cl_main.cl_showspeed.value == 1: # Draw speed and xy speed at top right

		xPos = vid.viddef.width - str_len

		if cl_main.cl_showfps.value == 1 or cl_main.cl_showfps.value == 2: # If showfps is enabled, draw it underneath

			yPos = int(scale * 10)

		elif cl_main.cl_showfps.value > 2:

			yPos = int(scale * 20)


		cl_console.DrawStringScaled(xPos, yPos, spd_str, scale)
		SCR_AddDirtyPoint(xPos, yPos)
		SCR_AddDirtyPoint(vid.viddef.width, yPos)

	elif cl_main.cl_showspeed.value > 1: # Draw only xy speed under the crosshair

		if scale != 1: # Check if low resolution

			scale -= 1


		spd_str = "%6.2f" % speedxy
		str_len = int(scale * (len(spd_str) * CHAR_SIZE + 2))
		yPos = int(scr_vrect.y + (scr_vrect.height / 2) + (scale * 10))
		xPos = int(scr_vrect.x + (scr_vrect.width / 2) - (str_len / 2))

		cl_console.DrawStringScaled(xPos, yPos, spd_str, scale)
		SCR_AddDirtyPoint(xPos, yPos)
		SCR_AddDirtyPoint(xPos + str_len, yPos)


SCR_Framecounter_frame = 0 #static int frame
SCR_Framecounter_frametimes = [0] * 60 #static int frametimes[60]
SCR_Framecounter_oldtime = 0 #static long long oldtime

def SCR_Framecounter(): #void (static)

	global SCR_Framecounter_frame, SCR_Framecounter_oldtime

	"""
	long long newtime;
	static int frame;
	static int frametimes[60] = {0};
	static long long oldtime;
	"""
	frametimes = SCR_Framecounter_frametimes

	# skip statistics without show fps
	if cl_main.cl_showfps.value < 1:

		return


	newtime = system.Sys_Microseconds()
	frametimes[SCR_Framecounter_frame] = int(newtime - SCR_Framecounter_oldtime)

	SCR_Framecounter_oldtime = newtime
	SCR_Framecounter_frame += 1
	if SCR_Framecounter_frame > 59:

		SCR_Framecounter_frame = 0


	scale = SCR_GetConsoleScale()

	if cl_main.cl_showfps.value == 1:

		# Calculate average of frames.
		#char str[10];
		avg = 0
		num = 0

		for i in range(60):

			if frametimes[i] != 0:

				avg += frametimes[i]
				num += 1



		str_ = ("%3.2ffps" % ((1000.0 * 1000.0) / (avg // num)))[:10 - 1]
		cl_console.DrawStringScaled(vid.viddef.width - scale * (len(str_) * CHAR_SIZE + 2), 0, str_, scale)
		SCR_AddDirtyPoint(vid.viddef.width - scale * (len(str_) * CHAR_SIZE + 2), 0)
		SCR_AddDirtyPoint(vid.viddef.width, 0)

	elif cl_main.cl_showfps.value >= 2:

		# Calculate average of frames.
		avg = 0
		num = 0
		#char str[64];

		for i in range(60):

			if frametimes[i] != 0:

				avg += frametimes[i]
				num += 1



		# Find lowest and highest
		min_ = frametimes[0]
		max_ = frametimes[1]

		for i in range(1, 60):

			if (frametimes[i] > 0) and (min_ < frametimes[i]):

				min_ = frametimes[i]


			if (frametimes[i] > 0) and (max_ > frametimes[i]):

				max_ = frametimes[i]



		str_ = ("Min: %7.2ffps, Max: %7.2ffps, Avg: %7.2ffps" %
		         ((1000.0 * 1000.0) / min_, (1000.0 * 1000.0) / max_, (1000.0 * 1000.0) / (avg // num)))[:64 - 1]
		cl_console.DrawStringScaled(vid.viddef.width - scale * (len(str_) * CHAR_SIZE + 2), 0, str_, scale)
		SCR_AddDirtyPoint(vid.viddef.width - scale * (len(str_) * CHAR_SIZE + 2), 0)
		SCR_AddDirtyPoint(vid.viddef.width, 0)

		if cl_main.cl_showfps.value > 2:

			str_ = ("Max: %5.2fms, Min: %5.2fms, Avg: %5.2fms" %
			         (0.001 * min_, 0.001 * max_, 0.001 * (avg / num)))[:64 - 1]
			cl_console.DrawStringScaled(vid.viddef.width - scale * (len(str_) * CHAR_SIZE + 2), scale * 10, str_, scale)
			SCR_AddDirtyPoint(vid.viddef.width - scale * (len(str_) * CHAR_SIZE + 2), scale * 10)
			SCR_AddDirtyPoint(vid.viddef.width, scale + 10)


"""
==================
SCR_UpdateScreen

This is called every frame, and can also be called explicitly to flush
text to the screen.
==================
"""
def SCR_UpdateScreen(): #
	global scr_draw_loading

	"""
	int numframes;
	int i;
	float separation[2] = {0, 0};
	float scale = SCR_GetMenuScale();
	"""
	separation = [0.0, 0.0]
	scale = SCR_GetMenuScale()

	# if the screen is disabled (loading plaque is
	# up, or vid mode changing) do nothing at all
	if cl_main.cls.disable_screen:

		if system.Sys_Milliseconds() - cl_main.cls.disable_screen > 120000:

			cl_main.cls.disable_screen = 0
			clientserver.Com_Printf("Loading plaque timed out.\n")


		return


	if not scr_initialized or not cl_console.con.initialized:

		return
		# not initialized yet


	if cl_main.gl1_stereo.value:

		numframes = 2
		separation[0] = -cl_main.gl1_stereo_separation.value / 2
		separation[1] = +cl_main.gl1_stereo_separation.value / 2

	else:

		separation[0] = 0
		separation[1] = 0
		numframes = 1


	for i in range(numframes):

		vid.R_BeginFrame(separation[i])
		if scr_draw_loading == 2:

			# loading plaque over black screen
			#int w, h;
			vid.R_EndWorldRenderpass()
			if i == 0:

				vid.R_SetPalette(None)


			if i == numframes - 1:

				scr_draw_loading = False


			w, h = vid.Draw_GetPicSize("loading")
			vid.Draw_PicScaled((vid.viddef.width - w * scale) / 2, (vid.viddef.height - h * scale) / 2, "loading", scale)

		elif cl_main.cl.cinematictime > 0:

			if cl_main.cls.key_dest == client_h.keydest_t.key_menu:

				if cl_main.cl.cinematicpalette_active:

					vid.R_SetPalette(None)
					cl_main.cl.cinematicpalette_active = False


				vid.R_EndWorldRenderpass()
				menu.M_Draw()

			elif cl_main.cls.key_dest == client_h.keydest_t.key_console:

				if cl_main.cl.cinematicpalette_active:

					vid.R_SetPalette(None)
					cl_main.cl.cinematicpalette_active = False


				vid.R_EndWorldRenderpass()
				SCR_DrawConsole()

			else:

				vid.R_EndWorldRenderpass()
				cl_cin.SCR_DrawCinematic()


		else:

			# make sure the game palette is active
			if cl_main.cl.cinematicpalette_active:

				vid.R_SetPalette(None)
				cl_main.cl.cinematicpalette_active = False


			# do 3D refresh drawing, and then update the screen
			SCR_CalcVrect()
			# clear any dirty part of the background
			SCR_TileClear()
			cl_view.V_RenderView(separation[i])
			SCR_DrawStats()
			SCR_DrawSpeed()
			if cl_main.cl.frame.playerstate.stats[STAT_LAYOUTS] & 1:

				SCR_DrawLayout()


			if cl_main.cl.frame.playerstate.stats[STAT_LAYOUTS] & 2:

				cl_inventory.CL_DrawInventory()


			SCR_DrawNet()
			SCR_CheckDrawCenterString()
			if scr_timegraph.value:

				SCR_DebugGraph(cl_main.cls.rframetime * 300, 0)


			if scr_debuggraph.value or scr_timegraph.value or scr_netgraph.value:

				SCR_DrawDebugGraph()


			SCR_DrawPause()
			SCR_DrawConsole()
			menu.M_Draw()
			SCR_DrawLoading()


	SCR_Framecounter()
	vid.R_EndFrame()

def SCR_ClampScale(scale): #float (returns static float)

	"""
	float f;
	"""

	f = vid.viddef.width / 320.0
	if scale > f:

		scale = f


	f = vid.viddef.height / 240.0
	if scale > f:

		scale = f


	if scale < 1:

		scale = 1


	return scale

def SCR_GetDefaultScale(): # (returns static float)

	"""
	int i = viddef.width / 640;
	int j = viddef.height / 240;
	"""
	i = int(vid.viddef.width / 640) # C int
	j = int(vid.viddef.height / 240) # C int

	if i > j:

		i = j


	if i < 1:

		i = 1


	return i

from client.vid import vid
from client import cl_view

	# C implementation is still unported.

# =============================================================================
# SCR_DrawCrosshair
# =============================================================================
def SCR_DrawCrosshair(): #

	"""
	float scale;
	float color[3];
	"""
	color = np.zeros((3,), dtype=np.float32)

	if not cl_view.crosshair.value:

		return


	if cl_view.crosshair.modified:

		cl_view.crosshair.modified = False
		SCR_TouchPics()


	if not crosshair_pic: # !crosshair_pic[0]

		return


	if cl_view.crosshair_scale.value < 0:

		scale = SCR_GetDefaultScale()

	else:

		scale = SCR_ClampScale(cl_view.crosshair_scale.value)


	color[0] = cl_view.crosshair_color_r.value
	color[1] = cl_view.crosshair_color_g.value
	color[2] = cl_view.crosshair_color_b.value
	vid.Draw_PicScaledCol(scr_vrect.x + (scr_vrect.width - crosshair_width * scale) / 2, scr_vrect.y + (scr_vrect.height - crosshair_height * scale) / 2, crosshair_pic, scale, color)
def SCR_GetHUDScale(): # (returns float)

	"""
	float scale;
	"""

	if not scr_initialized:

		scale = 1

	elif r_hudscale.value < 0:

		scale = SCR_GetDefaultScale()

	elif r_hudscale.value == 0:

		# HACK: allow scale 0 to hide the HUD
		scale = 0

	else:

		scale = SCR_ClampScale(r_hudscale.value)


	return scale

def SCR_GetConsoleScale(): # (returns float)

	"""
	float scale;
	"""

	if not scr_initialized:

		scale = 1

	elif r_consolescale.value < 0:

		scale = SCR_GetDefaultScale()

	else:

		scale = SCR_ClampScale(r_consolescale.value)


	return scale

def SCR_GetMenuScale(): # (returns float)

	"""
	float scale;
	"""

	if not scr_initialized:

		scale = 1

	elif r_menuscale.value < 0:

		scale = SCR_GetDefaultScale()

	else:

		scale = SCR_ClampScale(r_menuscale.value)


	return scale

