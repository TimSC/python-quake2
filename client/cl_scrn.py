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

import copy
from qcommon import cvar, cmd, qcommon, common
from client import console, cl_main, client, menu, cl_cin, snd_dma, cl_view, cl_inv
from linux import q_shlinux, vid_so, cd_linux
from game import q_shared
"""
// cl_scrn.c -- master for refresh, status bar, console, chat, notify, etc

/*

  full screen console
  put up loading plaque
  blanked background with loading plaque
  blanked background with menu
  cinematics
  full screen image for quit and victory

  end of unit intermissions

  */

#include "client.h"
"""

class vrect_t(object):

	def __init__(self):
		self.x = 0
		self.y = 0
		self.width = 0
		self.height = 0

scr_con_current = 0.0 #float, aproaches scr_conlines at scr_conspeed
scr_conlines = 0.0 #float, 0.0 to 1.0 lines of console to display

scr_initialized = False # qboolean, ready to draw
scr_draw_loading = 0 #int

scr_vrect = vrect_t() #position of render window on screen

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
CHAR_WIDTH = 16

sb_nums = [
	["num_0","num_1","num_2","num_3","num_4","num_5","num_6","num_7","num_8","num_9","num_minus"],
	["anum_0","anum_1","anum_2","anum_3","anum_4","anum_5","anum_6","anum_7","anum_8","anum_9","anum_minus"],
]

graphs_current = 0
graphs_values = [{"value": 0.0, "color": 0} for _ in range(1024)]

scr_centerstring = ""
scr_centertime_start = 0.0
scr_centertime_off = 0.0
scr_center_lines = 0
scr_erase_center = 0

crosshair_pic = ""
crosshair_width = 0
crosshair_height = 0


class dirty_t(object):

	def __init__(self):
		self.x1 = 0
		self.y1 = 0
		self.x2 = 0
		self.y2 = 0


scr_dirty = dirty_t()
scr_old_dirty = [dirty_t(), dirty_t()]
"""
char		crosshair_pic[MAX_QPATH];
int			crosshair_width, crosshair_height;

void SCR_TimeRefresh_f (void);
void SCR_Loading_f (void);
"""
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
def CL_AddNetgraph ():

	if int(scr_debuggraph.value) or int(scr_timegraph.value):
		return

	for _ in range(cl_main.cls.netchan.dropped):
		SCR_DebugGraph (30, 0x40)

	for _ in range(cl_main.cl.surpressCount):
		SCR_DebugGraph (30, 0xdf)

	in_index = cl_main.cls.netchan.incoming_acknowledged & (client.CMD_BACKUP-1)
	ping = cl_main.cls.realtime - cl_main.cl.cmd_time[in_index]
	ping //= 30
	if ping > 30:
		ping = 30

	SCR_DebugGraph (ping, 0xd0)



def SCR_DebugGraph (value, color):

	global graphs_current
	graphs_values[graphs_current & 1023]["value"] = float(value)
	graphs_values[graphs_current & 1023]["color"] = color
	graphs_current += 1


def SCR_DrawDebugGraph ():

	w = int(scr_vrect.width)
	x = scr_vrect.x
	y = scr_vrect.y + scr_vrect.height
	if w <= 0 or scr_graphheight is None:
		return
	height = int(scr_graphheight.value)
	if height <= 0:
		height = 1
	vid_so.re.DrawFill (x, y-height, w, height, 8)
	for a in range(w):
		i = (graphs_current - 1 - a + 1024) & 1023
		v = graphs_values[i]["value"]
		color = graphs_values[i]["color"]
		v = v * scr_graphscale.value + scr_graphshift.value
		if v < 0:
			v += height * (1 + int(-v // height))
		h = int(v) % height
		vid_so.re.DrawFill (x + w - 1 - a, y - h, 1, h, color)


def SCR_CenterPrint (text):

	global scr_centerstring, scr_centertime_off, scr_centertime_start, scr_center_lines
	scr_centerstring = text
	scr_centertime_off = scr_centertime.value
	scr_centertime_start = cl_main.cl.time
	scr_center_lines = text.count("\n") + 1
	common.Com_Printf("\n\n" + text + "\n\n")
	console.Con_ClearNotify ()


def SCR_DrawCenterString ():

	global scr_erase_center
	if not scr_centerstring:
		return
	scr_erase_center = 0
	start = scr_centerstring
	if scr_center_lines <= 4:
		y = int(vid_so.viddef.height * 0.35)
	else:
		y = 48
	idx = 0
	while idx < len(start):
		line_chars = []
		while idx < len(start) and start[idx] != "\n":
			line_chars.append(start[idx])
			idx += 1
		x = (vid_so.viddef.width - len(line_chars)*8)//2
		for ch in line_chars:
			vid_so.re.DrawChar (x, y, ord(ch))
			x += 8
		y += 8
		if idx < len(start) and start[idx] == "\n":
			idx += 1


def SCR_CheckDrawCenterString ():

	global scr_centertime_off
	scr_centertime_off -= cl_main.cls.frametime
	if scr_centertime_off <= 0:
		return
	SCR_DrawCenterString ()


def SCR_DrawStats ():

	SCR_ExecuteLayoutString (cl_main.cl.configstrings[q_shared.CS_STATUSBAR])


def SCR_DrawLayout ():
	if not cl_main.cl.frame.playerstate.stats[q_shared.STAT_LAYOUTS]:
		return
	SCR_ExecuteLayoutString (cl_main.cl.layout)
# ================================================================================

"""
=================
SCR_CalcVrect

Sets scr_vrect, the coordinates of the rendered window
=================
"""
def SCR_CalcVrect ():
	
	global scr_vrect
	"""
	int		size;
	"""

	# bound viewsize
	if scr_viewsize.value < 40:
		cvar.Cvar_Set ("viewsize","40")
	if scr_viewsize.value > 100:
		cvar.Cvar_Set ("viewsize","100")

	size = int(scr_viewsize.value)

	scr_vrect.width = vid_so.viddef.width*size//100
	scr_vrect.width &= ~7

	scr_vrect.height = vid_so.viddef.height*size//100
	scr_vrect.height &= ~1

	scr_vrect.x = (vid_so.viddef.width - scr_vrect.width)//2
	scr_vrect.y = (vid_so.viddef.height - scr_vrect.height)//2



"""
=================
SCR_SizeUp_f

Keybinding command
=================
"""
def SCR_SizeUp_f ():

	cvar.Cvar_SetValue ("viewsize", scr_viewsize.value+10)


"""
=================
SCR_SizeDown_f

Keybinding command
=================
"""
def SCR_SizeDown_f ():

	cvar.Cvar_SetValue ("viewsize",scr_viewsize.value-10)


"""
=================
SCR_Sky_f

Set a specific sky and rotation speed
=================
"""
def SCR_Sky_f ():

	#float	rotate;
	#vec3_t	axis;

	if cmd.Cmd_Argc() < 2:
		common.Com_Printf ("Usage: sky <basename> <rotate> <axis x y z>\n")
		return

	if cmd.Cmd_Argc() > 2:
		rotate = float(cmd.Cmd_Argv(2))
	else:
		rotate = 0.0

	axis = [0.0, 0.0, 1.0]
	if cmd.Cmd_Argc() == 6:
		axis[0] = float(cmd.Cmd_Argv(3))
		axis[1] = float(cmd.Cmd_Argv(4))
		axis[2] = float(cmd.Cmd_Argv(5))

	vid_so.re.SetSky (cmd.Cmd_Argv(1), rotate, axis)

# ================================================================================

"""
==================
SCR_Init
==================
"""
def SCR_Init ():

	global scr_initialized
	global scr_viewsize, scr_conspeed, scr_centertime, scr_showturtle, scr_showpause, scr_printspeed
	global scr_netgraph, scr_timegraph, scr_debuggraph, scr_graphheight, scr_graphscale, scr_graphshift, scr_drawall

	scr_viewsize = cvar.Cvar_Get ("viewsize", "100", q_shared.CVAR_ARCHIVE)
	scr_conspeed = cvar.Cvar_Get ("scr_conspeed", "3", 0)
	scr_showturtle = cvar.Cvar_Get ("scr_showturtle", "0", 0)
	scr_showpause = cvar.Cvar_Get ("scr_showpause", "1", 0)
	scr_centertime = cvar.Cvar_Get ("scr_centertime", "2.5", 0)
	scr_printspeed = cvar.Cvar_Get ("scr_printspeed", "8", 0)
	scr_netgraph = cvar.Cvar_Get ("netgraph", "0", 0)
	scr_timegraph = cvar.Cvar_Get ("timegraph", "0", 0)
	scr_debuggraph = cvar.Cvar_Get ("debuggraph", "0", 0)
	scr_graphheight = cvar.Cvar_Get ("graphheight", "32", 0)
	scr_graphscale = cvar.Cvar_Get ("graphscale", "1", 0)
	scr_graphshift = cvar.Cvar_Get ("graphshift", "0", 0)
	scr_drawall = cvar.Cvar_Get ("scr_drawall", "0", 0)

	#
	# register our commands
	#
	cmd.Cmd_AddCommand ("timerefresh",SCR_TimeRefresh_f)
	cmd.Cmd_AddCommand ("loading",SCR_Loading_f)
	cmd.Cmd_AddCommand ("sizeup",SCR_SizeUp_f)
	cmd.Cmd_AddCommand ("sizedown",SCR_SizeDown_f)
	cmd.Cmd_AddCommand ("sky",SCR_Sky_f)

	scr_initialized = True

"""
==============
SCR_DrawNet
==============
"""
def SCR_DrawNet ():

	if (cl_main.cls.netchan.outgoing_sequence - cl_main.cls.netchan.incoming_acknowledged) < client.CMD_BACKUP-1:
		return
	vid_so.re.DrawPic (scr_vrect.x+64, scr_vrect.y, "net")

"""
==============
SCR_DrawPause
==============
"""
def SCR_DrawPause ():

	if not scr_showpause.value:
		return
	if not cl_main.cl_paused.value:
		return
	w, h = vid_so.re.DrawGetPicSize ("pause")
	vid_so.re.DrawPic ((vid_so.viddef.width-w)//2, vid_so.viddef.height//2 + 8, "pause")

"""
==============
SCR_DrawLoading
==============
"""
def SCR_DrawLoading ():

	global scr_draw_loading

	#int		w, h;

	if scr_draw_loading == 0:
		return

	scr_draw_loading = 0
	w, h = vid_so.re.DrawGetPicSize ("loading")
	vid_so.re.DrawPic ((vid_so.viddef.width-w)//2, (vid_so.viddef.height-h)//2, "loading")


# ================================================================================

"""
==================
SCR_RunConsole

Scroll it up or down
==================
"""
def SCR_RunConsole ():
	global scr_conlines, scr_con_current

	# decide on the height of the console
	if cl_main.cls.key_dest == client.keydest_t.key_console:
		scr_conlines = 0.5		# half screen
	else:
		scr_conlines = 0				# none visible
	
	if scr_conlines < scr_con_current:
	
		scr_con_current -= scr_conspeed.value*cl_main.cls.frametime
		if scr_conlines > scr_con_current:
			scr_con_current = scr_conlines

	
	elif scr_conlines > scr_con_current:
	
		scr_con_current += scr_conspeed.value*cl_main.cls.frametime
		if scr_conlines < scr_con_current:
			scr_con_current = scr_conlines
	

"""
==================
SCR_DrawConsole
==================
"""
def SCR_DrawConsole ():

	global scr_con_current

	console.Con_CheckResize ()

	if cl_main.cls.state == client.connstate_t.ca_disconnected or cl_main.cls.state == client.connstate_t.ca_connecting:
		# forced full screen console
		console.Con_DrawConsole (1.0)
		return
	

	if cl_main.cls.state != client.connstate_t.ca_active or not cl_main.cl.refresh_prepped:
		# connected, but can't render
		console.Con_DrawConsole (0.5)
		vid_so.re.DrawFill (0, vid_so.viddef.height//2, vid_so.viddef.width, vid_so.viddef.height//2, 0)
		return
	

	if scr_con_current:
	
		console.Con_DrawConsole (scr_con_current)
	
	else:
	
		if cl_main.cls.key_dest == client.keydest_t.key_game or cl_main.cls.key_dest == client.keydest_t.key_message:
			console.Con_DrawNotify ()	# only draw notify in game
	


"""
# ================================================================================

================
SCR_BeginLoadingPlaque
================
"""
def SCR_BeginLoadingPlaque ():

	global scr_draw_loading

	snd_dma.S_StopAllSounds ()
	cl_main.cl.sound_prepped = False		# don't play ambients
	cd_linux.CDAudio_Stop ()
	if cl_main.cls.disable_screen:
		return
	if common.developer.value:
		return
	if cl_main.cls.state == client.connstate_t.ca_disconnected:
		return	# if at console, don't bring up the plaque
	if cl_main.cls.key_dest == client.keydest_t.key_console:
		return

	if cl_main.cl.cinematictime > 0:
		scr_draw_loading = 2	# clear to black first
	else:
		scr_draw_loading = 1

	SCR_UpdateScreen ()
	cl_main.cls.disable_screen = q_shlinux.Sys_Milliseconds ()
	#cl_main.cls.disable_servercount = cl_main.cl.servercount;


"""
================
SCR_EndLoadingPlaque
================
"""
def SCR_EndLoadingPlaque ():

	cl_main.cls.disable_screen = 0
	console.Con_ClearNotify ()

"""
================
SCR_Loading_f
================
"""
def SCR_Loading_f ():

	SCR_BeginLoadingPlaque ()


"""
================
SCR_TimeRefresh_f
================
"""
def entitycmpfnc( a, b )-> int: #(const entity_t *, const entity_t *)

	#
	# all other models are sorted by model then skin
	#

	amid = id(a.model)
	bmid = id(b.model)

	if amid == bmid:
		
		aid = id(a.skin)
		bid = id(b.skin)
		if aid == bid: return 0

		if aid > bid: return 1
		return -1
	
	else:
		if amid > bmid: return 1
		return -1

def SCR_TimeRefresh_f ():

	#int		i;
	#int		start, stop;
	#float	time;

	if cl_main.cls.state != client.connstate_t.ca_active:
		return

	start = q_shlinux.Sys_Milliseconds ()

	if cmd.Cmd_Argc() == 2:
		vid_so.re.BeginFrame(0)
		for i in range(128):
			cl_main.cl.refdef.viewangles[1] = i/128.0*360.0
			vid_so.re.RenderFrame (cl_main.cl.refdef)
		vid_so.re.EndFrame()
	else:
		for i in range(128):
			cl_main.cl.refdef.viewangles[1] = i/128.0*360.0
			vid_so.re.BeginFrame(0)
			vid_so.re.RenderFrame (cl_main.cl.refdef)
			vid_so.re.EndFrame()

	stop = q_shlinux.Sys_Milliseconds ()
	time = (stop-start)/1000.0
	common.Com_Printf ("%f seconds (%f fps)\n", time, 128/time)

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
	SCR_AddDirtyPoint (vid_so.viddef.width-1, vid_so.viddef.height-1)


"""
==============
SCR_TileClear

Clear any parts of the tiled background that were drawn on last frame
==============
"""
def SCR_TileClear ():

	global scr_vrect
	"""
	int		i;
	int		top, bottom, left, right;
	dirty_t	clear;
	"""

	global scr_drawall, scr_con_current

	if int(scr_drawall.value):
		SCR_DirtyScreen ()	# for power vr or broken page flippers...

	if scr_con_current == 1.0:
		return		# full screen console
	if scr_viewsize.value == 100:
		return		# full screen rendering
	if cl_main.cl.cinematictime > 0:
		return		# full screen cinematic

	# erase rect will be the union of the past three frames
	# so triple buffering works properly
	clear = copy.copy(scr_dirty)
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

	# don't bother with anything convered by the console)
	top = scr_con_current*vid_so.viddef.height
	if top >= clear.y1:
		clear.y1 = top;

	if clear.y2 <= clear.y1:
		return		# nothing disturbed

	top = scr_vrect.y
	bottom = top + scr_vrect.height-1
	left = scr_vrect.x
	right = left + scr_vrect.width-1

	if clear.y1 < top:
		# clear above view screen
		i = min(clear.y2, top-1)
		vid_so.re.DrawTileClear (clear.x1 , clear.y1,
			clear.x2 - clear.x1 + 1, i - clear.y1+1, "backtile")
		clear.y1 = top
	
	if clear.y2 > bottom:
		# clear below view screen
		i = max(clear.y1, bottom+1)
		vid_so.re.DrawTileClear (clear.x1, i,
			clear.x2-clear.x1+1, clear.y2-i+1, "backtile")
		clear.y2 = bottom
	
	if clear.x1 < left:
		# clear left of view screen
		i = min(clear.x2, left-1)
		vid_so.re.DrawTileClear (clear.x1, clear.y1,
			i-clear.x1+1, clear.y2 - clear.y1 + 1, "backtile")
		clear.x1 = left
	
	if clear.x2 > right:
		# clear left of view screen
		i = max(clear.x1, right+1)
		vid_so.re.DrawTileClear (i, clear.y1,
			clear.x2-i+1, clear.y2 - clear.y1 + 1, "backtile")
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


def DrawHUDString (string, x, y, centerwidth, xor):
	margin = x
	i = 0
	while i < len(string):
		line = []
		while i < len(string) and string[i] != '\n':
			line.append(string[i])
			i += 1
		width = len(line)
		if centerwidth:
			x = margin + (centerwidth - width*8)//2
		else:
			x = margin
		for ch in line:
			vid_so.re.DrawChar (x, y, ord(ch) ^ xor)
			x += 8
		if i < len(string) and string[i] == '\n':
			i += 1
			y += 8


def DrawString (x, y, string):
	DrawHUDString (string, x, y, 0, 0)


def DrawAltString (x, y, string):
	DrawHUDString (string, x, y, 0, 0x80)


"""
==============
SCR_DrawField
==============
"""
def SCR_DrawField (x, y, color, width, value): #int, int, int, int, int

	"""
	char	num[16], *ptr;
	int		l;
	int		frame;
	"""

	if width < 1:
		return

	# draw number string
	if width > 5:
		width = 5

	SCR_AddDirtyPoint (x, y)
	SCR_AddDirtyPoint (x+width*CHAR_WIDTH+2, y+23)

	num = "{}".format(int(value)) # Com_sprintf (num, sizeof(num), "%i", value);
	l = len(num)
	if l > width:
		l = width
	x += 2 + CHAR_WIDTH*(width - l)

	ptr = 0
	while ptr < len(num) and l:
	
		if num[ptr] == '-':
			frame = STAT_MINUS
		else:
			frame = ord(num[ptr]) - ord('0')

		vid_so.re.DrawPic (x,y,sb_nums[color][frame])
		x += CHAR_WIDTH
		ptr += 1
		l -= 1
	

def SCR_TouchPics ():

	global crosshair_pic, crosshair_width, crosshair_height

	#int		i, j;

	for i in range(2):
		for j in range(11):
			vid_so.re.RegisterPic (sb_nums[i][j])

	if cl_view.crosshair.value:
	
		if cl_view.crosshair.value > 3 or cl_view.crosshair.value < 0:
			cl_view.crosshair.value = 3

		crosshair_pic = "ch{}".format(int(cl_view.crosshair.value))
		crosshair_width, crosshair_height = vid_so.re.DrawGetPicSize (crosshair_pic)
		if not crosshair_width:
			crosshair_pic = "" # crosshair_pic[0] = 0;
	


"""
================
SCR_ExecuteLayoutString 

================
"""
def SCR_ExecuteLayoutString (s): #char *

	"""
	int		x, y;
	int		value;
	char	*token;
	int		width;
	int		index;
	clientinfo_t	*ci;
	"""
	cl = cl_main.cl
	viddef = vid_so.viddef

	if cl_main.cls.state != client.connstate_t.ca_active or not cl.refresh_prepped:
		return

	if not s:
		return

	x = 0
	y = 0
	width = 3

	cursor = 0
	while cursor is not None and cursor < len(s):
	
		token, cursor = common.COM_Parse (s, cursor)

		if token == "xl":
		
			token, cursor = common.COM_Parse (s, cursor)
			x = int(token)
			continue
		
		if token == "xr":
		
			token, cursor = common.COM_Parse (s, cursor)
			x = viddef.width + int(token)
			continue
		
		if token == "xv":
		
			token, cursor = common.COM_Parse (s, cursor)
			x = viddef.width//2 - 160 + int(token)
			continue
		
		if token == "yt":
		
			token, cursor = common.COM_Parse (s, cursor)
			y = int(token)
			continue
		
		if token == "yb":
		
			token, cursor = common.COM_Parse (s, cursor)
			y = viddef.height + int(token)
			continue
		
		if token == "yv":
		
			token, cursor = common.COM_Parse (s, cursor)
			y = viddef.height//2 - 120 + int(token)
			continue
		
		if token == "pic":
			# draw a pic from a stat number
			token, cursor = common.COM_Parse (s, cursor)
			value = cl.frame.playerstate.stats[int(token)]
			if value >= q_shared.MAX_IMAGES:
				common.Com_Error (q_shared.ERR_DROP, "Pic >= MAX_IMAGES")
			if cl.configstrings[q_shared.CS_IMAGES+value]:
			
				SCR_AddDirtyPoint (x, y)
				SCR_AddDirtyPoint (x+23, y+23)
				vid_so.re.DrawPic (x, y, cl.configstrings[q_shared.CS_IMAGES+value])
			
			continue
		
		if token == "client":
			# draw a deathmatch client block
			#int		score, ping, time;

			token, cursor = common.COM_Parse (s, cursor)
			x = viddef.width//2 - 160 + int(token)
			token, cursor = common.COM_Parse (s, cursor)
			y = viddef.height//2 - 120 + int(token)
			SCR_AddDirtyPoint (x, y)
			SCR_AddDirtyPoint (x+159, y+31)

			token, cursor = common.COM_Parse (s, cursor)
			value = int(token)
			if value >= q_shared.MAX_CLIENTS or value < 0:
				common.Com_Error (q_shared.ERR_DROP, "client >= MAX_CLIENTS")
			ci = cl.clientinfo[value]

			token, cursor = common.COM_Parse (s, cursor)
			score = int(token)

			token, cursor = common.COM_Parse (s, cursor)
			ping = int(token)

			token, cursor = common.COM_Parse (s, cursor)
			time = int(token)

			console.DrawAltString (x+32, y, ci.name)
			console.DrawString (x+32, y+8,  "Score: ")
			console.DrawAltString (x+32+7*8, y+8,  "{}".format(score))
			console.DrawString (x+32, y+16, "Ping:  {}".format(ping))
			console.DrawString (x+32, y+24, "Time:  {}".format(time))

			if not ci.icon:
				ci = cl.baseclientinfo
			vid_so.re.DrawPic (x, y, ci.iconname)
			continue
		
		if token == "ctf":
			# draw a ctf client block
			#int		score, ping;
			#char	block[80];

			token, cursor = common.COM_Parse (s, cursor)
			x = viddef.width//2 - 160 + int(token)
			token, cursor = common.COM_Parse (s, cursor)
			y = viddef.height//2 - 120 + int(token)
			SCR_AddDirtyPoint (x, y)
			SCR_AddDirtyPoint (x+159, y+31)

			token, cursor = common.COM_Parse (s, cursor)
			value = int(token)
			if value >= q_shared.MAX_CLIENTS or value < 0:
				common.Com_Error (q_shared.ERR_DROP, "client >= MAX_CLIENTS")
			ci = cl.clientinfo[value]

			token, cursor = common.COM_Parse (s, cursor)
			score = int(token)

			token, cursor = common.COM_Parse (s, cursor)
			ping = int(token)
			if ping > 999:
				ping = 999

			block = "{:3d} {:3d} {:<12.12s}".format(score, ping, ci.name) # sprintf(block, "%3d %3d %-12.12s", score, ping, ci->name);

			if value == cl.playernum:
				console.DrawAltString (x, y, block)
			else:
				console.DrawString (x, y, block)
			continue
		
		if token == "picn":
			# draw a pic from a name
			token, cursor = common.COM_Parse (s, cursor)
			SCR_AddDirtyPoint (x, y)
			SCR_AddDirtyPoint (x+23, y+23)
			vid_so.re.DrawPic (x, y, token)
			continue
		
		if token == "num":
			# draw a number
			token, cursor = common.COM_Parse (s, cursor)
			width = int(token)
			token, cursor = common.COM_Parse (s, cursor)
			value = cl.frame.playerstate.stats[int(token)]
			SCR_DrawField (x, y, 0, width, value)
			continue
		
		if token == "hnum":
			# health number
			#int		color;

			width = 3
			value = cl.frame.playerstate.stats[q_shared.STAT_HEALTH]
			if value > 25:
				color = 0	# green
			elif value > 0:
				color = (cl.frame.serverframe>>2) & 1		# flash
			else:
				color = 1

			if cl.frame.playerstate.stats[q_shared.STAT_FLASHES] & 1:
				vid_so.re.DrawPic (x, y, "field_3")

			SCR_DrawField (x, y, color, width, value)
			continue
		
		if token == "anum":
			# ammo number
			#int		color;

			width = 3
			value = cl.frame.playerstate.stats[q_shared.STAT_AMMO]
			if value > 5:
				color = 0	# green
			elif value >= 0:
				color = (cl.frame.serverframe>>2) & 1		# flash
			else:
				continue	# negative number = don't show

			if cl.frame.playerstate.stats[q_shared.STAT_FLASHES] & 4:
				vid_so.re.DrawPic (x, y, "field_3")

			SCR_DrawField (x, y, color, width, value)
			continue
		
		if token == "rnum":
			# armor number
			#int		color;

			width = 3
			value = cl.frame.playerstate.stats[q_shared.STAT_ARMOR]
			if value < 1:
				continue

			color = 0	# green

			if cl.frame.playerstate.stats[q_shared.STAT_FLASHES] & 2:
				vid_so.re.DrawPic (x, y, "field_3")

			SCR_DrawField (x, y, color, width, value)
			continue
		
		if token == "stat_string":
		
			token, cursor = common.COM_Parse (s, cursor)
			index = int(token)
			if index < 0 or index >= q_shared.MAX_CONFIGSTRINGS:
				common.Com_Error (q_shared.ERR_DROP, "Bad stat_string index")
			index = cl.frame.playerstate.stats[index]
			if index < 0 or index >= q_shared.MAX_CONFIGSTRINGS:
				common.Com_Error (q_shared.ERR_DROP, "Bad stat_string index")
			console.DrawString (x, y, cl.configstrings[index])
			continue
		
		if token == "cstring":
		
			token, cursor = common.COM_Parse (s, cursor)
			DrawHUDString (token, x, y, 320, 0)
			continue
		
		if token == "string":
		
			token, cursor = common.COM_Parse (s, cursor)
			console.DrawString (x, y, token)
			continue
		
		if token == "cstring2":
		
			token, cursor = common.COM_Parse (s, cursor)
			DrawHUDString (token, x, y, 320,0x80)
			continue
		
		if token == "string2":
		
			token, cursor = common.COM_Parse (s, cursor)
			console.DrawAltString (x, y, token)
			continue
		
		if token == "if":
			# draw a number
			token, cursor = common.COM_Parse (s, cursor)
			value = cl.frame.playerstate.stats[int(token)]
			if not value:
				# skip to endif
				while cursor is not None and cursor < len(s) and token != "endif":
				
					token, cursor = common.COM_Parse (s, cursor)
				
			continue
		

# =============================================================================== # End layout parsing

"""
==================
SCR_UpdateScreen

This is called every frame, and can also be called explicitly to flush
text to the screen.
==================
"""
def SCR_UpdateScreen ():

	global scr_initialized, scr_draw_loading

	#int numframes;
	#int i;
	separation = [0.0, 0.0] #float [2]

	# if the screen is disabled (loading plaque is up, or vid mode changing)
	# do nothing at all

	if cl_main.cls.disable_screen != 0:
	
		if q_shlinux.Sys_Milliseconds () - cl_main.cls.disable_screen > 120000:
		
			cl_main.cls.disable_screen = 0
			common.Com_Printf ("Loading plaque timed out.\n")
		
		return

	if not scr_initialized or not console.con.initialized:
		return				# not initialized yet

	
	#
	# range check cl_camera_separation so we don't inadvertently fry someone's
	# brain
	#
	if cl_main.cl_stereo_separation.value > 1.0 :
		cvar.Cvar_SetValue( "cl_stereo_separation", 1.0 )
	elif cl_main.cl_stereo_separation.value < 0 :
		cvar.Cvar_SetValue( "cl_stereo_separation", 0.0 )

	if cl_main.cl_stereo.value:
	
		numframes = 2
		separation[0] = -cl_main.cl_stereo_separation.value / 2
		separation[1] =  cl_main.cl_stereo_separation.value / 2
			
	else:
	
		separation[0] = 0
		separation[1] = 0
		numframes = 1
	
	
	for i in range(numframes):
		
		vid_so.re.BeginFrame( separation[i] )
		
		if scr_draw_loading == 2:
			#  loading plaque over black screen
			#int		w, h;

			vid_so.re.CinematicSetPalette(None)
			scr_draw_loading = 0
			w, h = vid_so.re.DrawGetPicSize ("loading")
			vid_so.re.DrawPic ((vid_so.viddef.width-w)//2, (vid_so.viddef.height-h)//2, "loading")
			##vid_so.re.EndFrame();
			##return;

		# if a cinematic is supposed to be running, handle menus
		# and console specially
		elif cl_main.cl.cinematictime > 0:
		
			
			if cl_main.cls.key_dest == client.keydest_t.key_menu:

				if cl_main.cl.cinematicpalette_active:
				
					vid_so.re.CinematicSetPalette(None)
					cl_main.cl.cinematicpalette_active = False
				
				menu.M_Draw ()
				##vid_so.re.EndFrame()
				##return

			elif cl_main.cls.key_dest == client.keydest_t.key_console:

				if cl_main.cl.cinematicpalette_active:
				
					vid_so.re.CinematicSetPalette(None)
					cl_main.cl.cinematicpalette_active = False
				
				SCR_DrawConsole ()
				##vid_so.re.EndFrame()
				##return

			else:
			
				cl_cin.SCR_DrawCinematic()
				##vid_so.re.EndFrame()
				##return
			

		
		else:

			# make sure the game palette is active
			if cl_main.cl.cinematicpalette_active:
			
				vid_so.re.CinematicSetPalette(None)
				cl_main.cl.cinematicpalette_active = False
			

			# do 3D refresh drawing, and then update the screen
			SCR_CalcVrect ()

			# clear any dirty part of the background
			SCR_TileClear ()

			cl_view.V_RenderView ( separation[i] )
			SCR_DrawStats ()
			if cl_main.cl.frame.playerstate.stats[q_shared.STAT_LAYOUTS] & 1:
				SCR_DrawLayout ()
			if cl_main.cl.frame.playerstate.stats[q_shared.STAT_LAYOUTS] & 2:
				cl_inv.CL_DrawInventory ()

			SCR_DrawNet ()
			SCR_CheckDrawCenterString ()

			if scr_timegraph.value:
				SCR_DebugGraph (cl_main.cls.frametime*300, 0)

			if (int(scr_debuggraph.value) or int(scr_timegraph.value) or int(scr_netgraph.value)):
				SCR_DrawDebugGraph ()

			SCR_DrawPause ()
			SCR_DrawConsole ()

			menu.M_Draw ()

			SCR_DrawLoading ()

		
	
	vid_so.re.EndFrame()
