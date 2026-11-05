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

from qcommon import cmd, cvar, common, qcommon, files
import os
from linux import vid_so
from client import cl_scrn, cl_main, client, keys, menu
"""
// console.c

#include "client.h"

"""

NUM_CON_TIMES = 4

CON_TEXTSIZE = 32768

class console_t(object):

	def __init__(self):

		self.initialized = False #qboolean

		self.text = [] #char	[CON_TEXTSIZE];
		self.current = None #int, line where next message will be printed
		self.x = 0 #int, offset in current line for next print
		self.display = None #int, bottom of console displays this line

		self.ormask = 0 #int, high bit mask for colored characters

		self.linewidth = None #int, characters across screen
		self.totallines = 0 #int, total lines in console scrollback

		self.cursorspeed = None #float

		self.vislines = None #int		

		self.times = [] #float	[NUM_CON_TIMES], cls.realtime time the line was generated
									# for transparent notify lines
		for i in range(NUM_CON_TIMES):
			self.times.append(None)

con = console_t()

con_notifytime = None #cvar_t		*
"""

#define		MAXCMDLINE	256
extern	char	key_lines[32][MAXCMDLINE];
extern	int		edit_line;
extern	int		key_linepos;
		
"""

def DrawString (x: int, y: int, s: str): #int, int, char *

	i = 0 # index into s
	while i < len(s) and s[i] != '\0': # while (*s)
	
		vid_so.re.DrawChar (x, y, ord(s[i]))
		x+=8
		i+=1 # s++
	

def DrawAltString (x: int, y: int, s: str): #int, int, char *

	i = 0 # index into s
	while i < len(s) and s[i] != '\0': # while (*s)
	
		vid_so.re.DrawChar (x, y, ord(s[i]) ^ 0x80)
		x+=8
		i+=1 # s++
	

def Key_ClearTyping ():

	keys.key_lines[keys.edit_line] = keys.key_lines[keys.edit_line][0]	# clear any typing
	keys.key_linepos = 1


"""
================
Con_ToggleConsole_f
================
"""
def Con_ToggleConsole_f ():

	cl_scrn.SCR_EndLoadingPlaque ()	# get rid of loading plaque
	
	if cl_main.cl.attractloop:
		cmd.Cbuf_AddText ("killserver\n")
		return
	
	if cl_main.cls.state == client.connstate_t.ca_disconnected:
		# start the demo loop again
		cmd.Cbuf_AddText ("d1\n")
		return
	
	Key_ClearTyping ()
	Con_ClearNotify ()

	if cl_main.cls.key_dest == client.keydest_t.key_console:
	
		menu.M_ForceMenuOff ()
		cvar.Cvar_Set ("paused", "0")
	
	else:
	
		menu.M_ForceMenuOff ()
		cl_main.cls.key_dest = client.keydest_t.key_console

		if cvar.Cvar_VariableValue ("maxclients") == 1\
			and common.Com_ServerState ():

			cvar.Cvar_Set ("paused", "1")
	


"""
================
Con_ToggleChat_f
================
"""
def Con_ToggleChat_f ():

	Key_ClearTyping ()

	if cl_main.cls.key_dest == client.keydest_t.key_console:
		if cl_main.cls.state == client.connstate_t.ca_active:
			menu.M_ForceMenuOff ()
			cl_main.cls.key_dest = client.keydest_t.key_game
	else:
		cl_main.cls.key_dest = client.keydest_t.key_console

	Con_ClearNotify ()

def Con_Clear_f ():

	for i, li in enumerate(con.text):
		con.text[i] = ""
def Con_Dump_f ():
	if cmd.Cmd_Argc() != 2:
		common.Com_Printf ("usage: condump <filename>\n")
		return

	name = os.path.join(files.FS_Gamedir(), "{}.txt".format(cmd.Cmd_Argv(1)))

	common.Com_Printf ("Dumped console text to {}.\n".format(name))
	files.FS_CreatePath (name)
	try:
		f = open(name, "w", encoding="ascii", errors="ignore")
	except OSError:
		common.Com_Printf ("ERROR: couldn't open.\n")
		return

	l = con.current - con.totallines + 1
	while l <= con.current:
		line = con.text[l % con.totallines] if con.text else ""
		if any(ch != " " for ch in line[:con.linewidth]):
			break
		l += 1

	while l <= con.current:
		line = con.text[l % con.totallines] if con.text else ""
		buffer = line[:con.linewidth].rstrip(" ")
		buffer = "".join(chr(ord(ch) & 0x7f) for ch in buffer)
		f.write(buffer + "\n")
		l += 1

	f.close()

						
def Con_ClearNotify ():

	global con
	#int		i;
	
	for i in range(NUM_CON_TIMES):
		con.times[i] = 0
						
"""
================
Con_MessageMode_f
================
"""
def Con_MessageMode_f ():

	keys.chat_team = False
	cl_main.cls.key_dest = client.keydest_t.key_message


def Con_MessageMode2_f ():

	keys.chat_team = True
	cl_main.cls.key_dest = client.keydest_t.key_message


def Con_CheckResize ():
	
	#int		i, j, width, oldwidth, oldtotallines, numlines, numchars;
	#char	tbuf[CON_TEXTSIZE];

	width = (vid_so.viddef.width >> 3) - 2

	if width == con.linewidth:
		return

	if width < 1:			# video hasn't been initialized yet
	
		width = 38
		con.linewidth = width
		con.totallines = CON_TEXTSIZE // con.linewidth
		con.text = []
		for i in range(con.totallines):
			con.text.append("")
	
	else:
	
		oldwidth = con.linewidth
		con.linewidth = width
		oldtotallines = con.totallines
		con.totallines = CON_TEXTSIZE // con.linewidth
		numlines = oldtotallines

		if con.totallines < numlines:
			numlines = con.totallines

		numchars = oldwidth
	
		if con.linewidth < numchars:
			numchars = con.linewidth

		tbuf = con.text
		con.text = []
		for i in range(con.totallines):
			con.text.append("")

		for i in range(numlines):
			con.text[con.totallines - 1 - i] = tbuf[(con.current - i + oldtotallines) % oldtotallines]

		Con_ClearNotify ()
	

	con.current = con.totallines - 1
	con.display = con.current



"""
================
Con_Init
================
"""
def Con_Init ():

	global con_notifytime

	con.linewidth = -1

	Con_CheckResize ()
	
	common.Com_Printf ("Console initialized.\n")

	#
	# register our commands
	#
	con_notifytime = cvar.Cvar_Get ("con_notifytime", "3", 0);

	cmd.Cmd_AddCommand ("toggleconsole", Con_ToggleConsole_f)
	cmd.Cmd_AddCommand ("togglechat", Con_ToggleChat_f)
	cmd.Cmd_AddCommand ("messagemode", Con_MessageMode_f)
	cmd.Cmd_AddCommand ("messagemode2", Con_MessageMode2_f)
	cmd.Cmd_AddCommand ("clear", Con_Clear_f)
	cmd.Cmd_AddCommand ("condump", Con_Dump_f)
	con.initialized = True

"""
===============
Con_Linefeed
===============
"""
def Con_Linefeed ():

	global con

	con.x = 0
	if con.display == con.current:
		con.display+= 1
	con.current+=1
	con.text[con.current%con.totallines] = ""
	#memset (&con.text[(con.current%con.totallines)*con.linewidth]
	#, ' ', con.linewidth);


"""
================
Con_Print

Handles cursor positioning, line wrapping, etc
All console printing must go through this in order to be logged to disk
If no console is visible, the text will appear at the top of the game window
================
"""
def Con_Print (txt): #char *

	global con
	
	#int		y;
	#int		c, l;
	#static int	cr;
	#int		mask;
	cr = 0

	if not con.initialized:
		return

	cursor = 0
	if txt[cursor] == 1 or txt[cursor] == 2:
	
		mask = 128		# go to colored text
		cursor += 1
	
	else:
		mask = 0

	c = txt[cursor]
	while cursor < len(txt):

		# count word length
		l = min(con.linewidth, len(txt) - cursor)

		# word wrap
		if l != con.linewidth and con.x + l > con.linewidth:
			con.x = 0

		cursor+=1

		if cr:
		
			con.current-=1
			cr = False
		
		if con.x == 0:
		
			Con_Linefeed ()
			# mark time for transparent overlay
			if con.current >= 0:
				con.times[con.current % NUM_CON_TIMES] = cl_main.cls.realtime
		
		if c == '\n':
			con.x = 0

		elif c == '\r':
			con.x = 0
			cr = 1

		else:	# display character and advance
			y = con.current % con.totallines
			con.text[y] = con.text[y][:con.x] + str(chr(ord(c) | mask | con.ormask))
			con.x += 1
			if con.x >= con.linewidth:
				con.x = 0

		if cursor < len(txt):
			c = txt[cursor]

def Con_DrawInput ():
   
	#int		y;
	#int		i;
	#char	*text;

	if cl_main.cls.key_dest == client.keydest_t.key_menu:
		return
	if cl_main.cls.key_dest != client.keydest_t.key_console and cl_main.cls.state == client.connstate_t.ca_active:
		return		# don't draw anything (always draw if not active)

	text = [keys.key_lines[keys.edit_line]]
	
	# add the cursor frame
	text.append(chr(10+((int(cl_main.cls.realtime)>>8)&1)))
	
	# fill out remainder with spaces
	for i in range(keys.key_linepos+1, con.linewidth):
		text.append(' ')
		
	text = "".join(text)

	# prestep if horizontally scrolling
	if keys.key_linepos >= con.linewidth:
		text = text[1 + keys.key_linepos - con.linewidth:]
		
	# draw it
	y = con.vislines-16

	for i in range(con.linewidth):
		vid_so.re.DrawChar ( (i+1)<<3, con.vislines - 22, ord(text[i]))

	# remove cursor
	#key_lines[edit_line][keys.key_linepos] = 0;

"""
================
Con_DrawNotify

Draws the last few lines of output transparently over the game top
================
"""
def Con_DrawNotify ():

	v = 0
	for i in range(con.current - NUM_CON_TIMES + 1, con.current + 1):
		if i < 0:
			continue
		timestamp = con.times[i % NUM_CON_TIMES]
		if not timestamp:
			continue
		time = cl_main.cls.realtime - timestamp
		if time > con_notifytime.value * 1000:
			continue
		text = con.text[i % con.totallines] if con.text else ""

		for x in range(min(con.linewidth, len(text))):
			vid_so.re.DrawChar((x + 1) << 3, v, ord(text[x]))

		v += 8

	if cl_main.cls.key_dest == client.keydest_t.key_message:
		if keys.chat_team:
			prefix = "say_team:"
		else:
			prefix = "say:"

		skip = len(prefix) + 1
		for idx, ch in enumerate(prefix):
			vid_so.re.DrawChar((idx + 1) << 3, v, ord(ch))

		available = (vid_so.viddef.width >> 3) - (skip + 1)
		text = keys.chat_buffer
		if keys.chat_bufferlen > available:
			text = text[keys.chat_bufferlen - available:]
		for x, ch in enumerate(text):
			vid_so.re.DrawChar((x + skip) << 3, v, ord(ch))
		vid_so.re.DrawChar((len(text) + skip) << 3, v, 10 + ((cl_main.cls.realtime >> 8) & 1))
		v += 8

def Con_DrawConsole (frac): #float

	"""
	int				i, j, x, y, n;
	int				rows;
	char			*text;
	int				row;
	int				lines;
	char			version[64];
	char			dlbar[1024];
	"""

	lines = int(vid_so.viddef.height * frac)
	if lines <= 0:
		return

	if lines > vid_so.viddef.height:
		lines = vid_so.viddef.height

	# draw the background
	vid_so.re.DrawStretchPic (0, -vid_so.viddef.height+lines, vid_so.viddef.width, vid_so.viddef.height, "conback")
	cl_scrn.SCR_AddDirtyPoint (0,0)
	cl_scrn.SCR_AddDirtyPoint (vid_so.viddef.width-1,lines-1)

	
	version = "v{:4.2f}".format(qcommon.VERSION)
	for x in range(5):
		vid_so.re.DrawChar (vid_so.viddef.width-44+x*8, lines-12, 128 + ord(version[x]) )

	# draw the text
	con.vislines = lines

	##rows = (lines-8)>>3;		// rows of text to draw
	##
	##y = lines - 24;

	rows = (lines-22)>>3		# rows of text to draw

	y = lines - 30


	# draw from the bottom up
	if con.display != con.current:
	
		# draw arrows to show the buffer is backscrolled
		for x in range(0, con.linewidth, 4):
			vid_so.re.DrawChar ( (x+1)<<3, y, ord('^'))
	
		y -= 8
		rows-=1
	
	row = con.display
	i = 0
	while i<rows:
	
		if row < 0:
			break
		if con.current - row >= con.totallines:
			break		# past scrollback wrap point
		
		cursor = row % con.totallines
		text = con.text[cursor]

		for x, ch in enumerate(text):
			vid_so.re.DrawChar ( (x+1)<<3, y, ord(text[x]))

		i+=1
		y-=8 
		row-=1
	
	# draw the input prompt, user text, and cursor if desired
	Con_DrawInput ()
