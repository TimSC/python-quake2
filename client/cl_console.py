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

This file implements the console

=======================================================================
"""
from __future__ import annotations

from client.sound import ogg
from client.sound.header import vorbis

import time

from client.vid import vid

import os
from linux import vid_so
from client import cl_main
from common.header import common as common_h
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from client import cl_keyboard
from client import cl_main
from client import cl_screen
from client.header import client as client_h
from client.header import console as console_h
from client.header import keyboard as keyboard_h
from client.menu import menu

"""
#include "header/client.h"
#include "sound/header/local.h"
#include <time.h>
"""

con = console_h.console_t()

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
	

def DrawStringScaled(x: int, y: int, s: str, factor: float): #int, int, const char *, float

	for ch in s: # while (*s)

		vid.Draw_CharScaled(x, y, ord(ch), factor)
		x += 8*factor

def DrawAltStringScaled(x: int, y: int, s: str, factor: float): #int, int, const char *, float

	for ch in s: # while (*s)

		vid.Draw_CharScaled(x, y, ord(ch) ^ 0x80, factor)
		x += 8*factor

def Key_ClearTyping(): #

	cl_keyboard.key_lines[cl_keyboard.edit_line] = "" # key_lines[edit_line][0] = 0
	cl_keyboard.key_linepos = 0


"""
================
Con_ToggleConsole_f
================
"""
def Con_ToggleConsole_f(): #

	cl_screen.SCR_EndLoadingPlaque()
	# get rid of loading plaque
	if cl_main.cl.attractloop:

		cmdparser.Cbuf_AddText("killserver\n")
		return


	if cl_main.cls.state == client_h.connstate_t.ca_disconnected:

		# start the demo loop again
		cmdparser.Cbuf_AddText("d1\n")
		return


	Key_ClearTyping()
	Con_ClearNotify()
	# #ifdef USE_OPENAL
	# #endif
	if cl_main.cls.key_dest == client_h.keydest_t.key_console:

		menu.M_ForceMenuOff()
		cvar.Cvar_Set("paused", "0")
		# play music
		if cvar.Cvar_VariableValue("ogg_pausewithgame") == 1 and ogg.OGG_Status() == vorbis.PAUSE:

			cmdparser.Cbuf_AddText("ogg toggle\n")


	else:

		menu.M_ForceMenuOff()
		cl_main.cls.key_dest = client_h.keydest_t.key_console
		if (cvar.Cvar_VariableValue("maxclients") == 1) and clientserver.Com_ServerState():

			cvar.Cvar_Set("paused", "1")
			# pause music
			if cvar.Cvar_VariableValue("ogg_pausewithgame") == 1 and ogg.OGG_Status() == vorbis.PLAY:

				cmdparser.Cbuf_AddText("ogg toggle\n")
	


"""
================
Con_ToggleChat_f
================
"""
def Con_ToggleChat_f ():

	Key_ClearTyping ()

	if cl_main.cls.key_dest == client_h.keydest_t.key_console:
		if cl_main.cls.state == client_h.connstate_t.ca_active:
			menu.M_ForceMenuOff ()
			cl_main.cls.key_dest = client_h.keydest_t.key_game
	else:
		cl_main.cls.key_dest = client_h.keydest_t.key_console

	Con_ClearNotify ()

def Con_Clear_f ():

	for i, li in enumerate(con.text):
		con.text[i] = ""
def Con_Dump_f(): #void

	"""
	int l, x;
	char *line;
	FILE *f;
	char buffer[1024];
	char name[MAX_OSPATH];
	"""

	if cmdparser.Cmd_Argc() != 2:

		clientserver.Com_Printf("usage: condump <filename>\n")
		return


	if con.linewidth >= 1024:

		clientserver.Com_Printf("con.linewidth too large!\n")
		return


	name = "%s/%s.txt" % (filesystem.FS_Gamedir(), cmdparser.Cmd_Argv(1))

	clientserver.Com_Printf("Dumped console text to %s.\n", name)
	filesystem.FS_CreatePath(name)
	try:

		f = open(name, "w", encoding="latin-1", errors="replace") # Q_fopen(name, "w")

	except OSError:

		clientserver.Com_Printf("ERROR: couldn't open.\n")
		return


	# Q2PORT: con.text is a list of lines (see console_t)

	# skip empty lines
	l = con.current - con.totallines + 1
	while l <= con.current:

		line = con.text[l % con.totallines].ljust(con.linewidth)[:con.linewidth]

		if line.strip(" "):

			break


		l += 1


	# write the remaining lines
	while l <= con.current:

		buffer = con.text[l % con.totallines].ljust(con.linewidth)[:con.linewidth]
		buffer = buffer.rstrip(" ")
		buffer = "".join(chr(ord(ch) & 0x7f) for ch in buffer)

		f.write("%s\n" % buffer)
		l += 1


	f.close()

						
def Con_ClearNotify ():

	global con
	#int		i;
	
	for i in range(console_h.NUM_CON_TIMES):
		con.times[i] = 0
						
"""
================
Con_MessageMode_f
================
"""
def Con_MessageMode_f ():

	cl_keyboard.chat_team = False
	cl_main.cls.key_dest = client_h.keydest_t.key_message


def Con_MessageMode2_f ():

	cl_keyboard.chat_team = True
	cl_main.cls.key_dest = client_h.keydest_t.key_message


def Con_CheckResize(): #void

	"""
	int i, j, width, oldwidth, oldtotallines, numlines, numchars;
	char tbuf[CON_TEXTSIZE];
	float scale = SCR_GetConsoleScale();
	"""
	scale = cl_screen.SCR_GetConsoleScale()

	# We need to clamp the line width to MAXCMDLINE - 2,
	# otherwise we may overflow the text buffer if the
	# vertical resultion / 8 (one char == 8 pixels) is
	# bigger then MAXCMDLINE.
	# MAXCMDLINE - 2 because 1 for the prompt and 1 for
	# the terminating \0.
	width = (int(vid_so.viddef.width / scale) // 8) - 2
	width = keyboard_h.MAXCMDLINE - 2 if width > keyboard_h.MAXCMDLINE - 2 else width

	if width == con.linewidth:

		return


	# Q2PORT: con.text is a list of lines (see console_t), so the C's
	# character copies become line copies

	# video hasn't been initialized yet
	if width < 1:

		width = 38
		con.linewidth = width
		con.totallines = console_h.CON_TEXTSIZE // con.linewidth
		con.text = ["" for _ in range(con.totallines)] # memset(con.text, ' ', CON_TEXTSIZE);

	else:

		oldwidth = con.linewidth
		con.linewidth = width
		oldtotallines = con.totallines
		con.totallines = console_h.CON_TEXTSIZE // con.linewidth
		numlines = oldtotallines

		if con.totallines < numlines:

			numlines = con.totallines


		numchars = oldwidth

		if con.linewidth < numchars:

			numchars = con.linewidth


		tbuf = con.text # memcpy(tbuf, con.text, CON_TEXTSIZE);
		con.text = ["" for _ in range(con.totallines)] # memset(con.text, ' ', CON_TEXTSIZE);

		for i in range(numlines):

			con.text[con.totallines - 1 - i] = tbuf[(con.current - i + oldtotallines) % oldtotallines][:numchars]


		Con_ClearNotify()


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
	
	clientserver.Com_Printf ("Console initialized.\n")

	#
	# register our commands
	#
	con_notifytime = cvar.Cvar_Get ("con_notifytime", "3", 0);

	cmdparser.Cmd_AddCommand ("toggleconsole", Con_ToggleConsole_f)
	cmdparser.Cmd_AddCommand ("togglechat", Con_ToggleChat_f)
	cmdparser.Cmd_AddCommand ("messagemode", Con_MessageMode_f)
	cmdparser.Cmd_AddCommand ("messagemode2", Con_MessageMode2_f)
	cmdparser.Cmd_AddCommand ("clear", Con_Clear_f)
	cmdparser.Cmd_AddCommand ("condump", Con_Dump_f)
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


Con_Print_cr = 0 #static int, in Con_Print

"""
================
Con_Print

Handles cursor positioning, line wrapping, etc
All console printing must go through this in order to be logged to disk
If no console is visible, the text will appear at the top of the game window
================
"""
def Con_Print(txt: str): #char *

	global Con_Print_cr

	"""
	int y;
	int c, l;
	static int cr;
	int mask;
	"""

	if not con.initialized:

		return


	if txt[:1] == "\x01" or txt[:1] == "\x02": # (txt[0] == 1) || (txt[0] == 2)

		mask = 128 # go to colored text
		txt = txt[1:]

	else:

		mask = 0


	i = 0
	while i < len(txt): # while ((c = *txt))

		c = txt[i]

		# count word length
		l = 0
		while l < con.linewidth:

			if i + l >= len(txt) or txt[i + l] <= ' ':

				break


			l += 1


		# word wrap
		if (l != con.linewidth) and (con.x + l > con.linewidth):

			con.x = 0


		i += 1 # txt++

		if Con_Print_cr:

			con.current -= 1
			Con_Print_cr = False


		if not con.x:

			Con_Linefeed()

			# mark time for transparent overlay
			if con.current >= 0:

				con.times[con.current % console_h.NUM_CON_TIMES] = cl_main.cls.realtime



		if c == '\n':

			con.x = 0

		elif c == '\r':

			con.x = 0
			Con_Print_cr = 1

		else: # display character and advance

			y = con.current % con.totallines
			line = con.text[y].ljust(con.x) # Q2PORT: the line as a string
			con.text[y] = line[:con.x] + chr(ord(c) | mask | con.ormask) + line[con.x + 1:]
			con.x += 1

			if con.x >= con.linewidth:

				con.x = 0

def Con_DrawInput(): #void (static)

	"""
	int i;
	float scale;
	char *text;
	char ch;
	size_t txtlen;
	int linepos;
	int draw_icon;
	"""

	if cl_main.cls.key_dest == client_h.keydest_t.key_menu:

		return


	# don't draw anything (always draw if not active)
	if (cl_main.cls.key_dest != client_h.keydest_t.key_console) and (cl_main.cls.state == client_h.connstate_t.ca_active):

		return


	scale = cl_screen.SCR_GetConsoleScale()
	text = cl_keyboard.key_lines[cl_keyboard.edit_line]
	linepos = cl_keyboard.key_linepos

	# prestep if horizontally scrolling
	if linepos >= (con.linewidth - 1):

		#int ofs = 1 + linepos - con.linewidth;
		ofs = 1 + linepos - con.linewidth

		text = text[ofs:] # text += ofs;
		linepos -= ofs

		draw_icon = 0

	else:

		vid.Draw_CharScaled(8 * scale, con.vislines - 22 * scale, console_h.CON_INPUT_INDICATOR, scale)
		draw_icon = 1


	txtlen = len(text)

	for i in range(con.linewidth - draw_icon):

		if i == linepos:

			if (int(cl_main.cls.realtime) >> 8) & 1:

				ch = console_h.CON_INPUT_CURSOR

			else:

				ch = 10 if (i >= txtlen) else ord(text[i]) # (text[i] == '\0') ? 10 : text[i]


		elif i >= txtlen:

			ch = ord(' ')

		else:

			ch = ord(text[i])


		vid.Draw_CharScaled(((i + 1 + draw_icon) << 3) * scale, con.vislines - 22 * scale, ch, scale)


	# remove cursor
	#key_lines[edit_line][keys.key_linepos] = 0;

"""
================
Con_DrawNotify

Draws the last few lines of output transparently over the game top
================
"""
def Con_DrawNotify(): #void

	"""
	int x, v;
	char *text;
	int i;
	int time;
	char *s;
	int skip;
	float scale;
	"""

	v = 0
	scale = cl_screen.SCR_GetConsoleScale()

	for i in range(con.current - console_h.NUM_CON_TIMES + 1, con.current + 1):

		if i < 0:

			continue


		time = con.times[i % console_h.NUM_CON_TIMES]

		if not time: # time == 0

			continue


		time = cl_main.cls.realtime - time

		if time > con_notifytime.value * 1000:

			continue


		text = con.text[i % con.totallines].ljust(con.linewidth) # Q2PORT: the line (see console_t)

		for x in range(con.linewidth):

			vid.Draw_CharScaled(((x + 1) << 3) * scale, v * scale, ord(text[x]), scale)


		v += 8


	if cl_main.cls.key_dest == client_h.keydest_t.key_message:

		if cl_keyboard.chat_team:

			DrawStringScaled(8 * scale, v * scale, "say_team:", scale)
			skip = 11

		else:

			DrawStringScaled(8 * scale, v * scale, "say:", scale)
			skip = 5


		s = cl_keyboard.chat_buffer

		if cl_keyboard.chat_bufferlen > (vid_so.viddef.width >> 3) - (skip + 1):

			s = s[cl_keyboard.chat_bufferlen - ((vid_so.viddef.width >> 3) - (skip + 1)):]


		x = 0

		while x < len(s):

			vid.Draw_CharScaled(((x + skip) << 3) * scale, v * scale, ord(s[x]), scale)
			x += 1


		vid.Draw_CharScaled(((x + skip) << 3) * scale, v * scale, 10 + ((int(cl_main.cls.realtime) >> 8) & 1), scale)
		v += 8


	if v:

		cl_screen.SCR_AddDirtyPoint(0, 0)
		cl_screen.SCR_AddDirtyPoint(vid_so.viddef.width - 1, v)

def Con_DrawConsole(frac: float): #float

	"""
	int i, j, x, y, n;
	int rows;
	size_t verLen;
	char *text;
	int row;
	int lines;
	float scale;
	char version[48];
	char dlbar[1024];
	char timebuf[48];
	char tmpbuf[48];

	time_t t;
	struct tm *today;
	"""

	scale = cl_screen.SCR_GetConsoleScale()
	lines = int(vid_so.viddef.height * frac)

	if lines <= 0:

		return


	if lines > vid_so.viddef.height:

		lines = vid_so.viddef.height


	# draw the background
	vid.Draw_StretchPic(0, -vid_so.viddef.height + lines, vid_so.viddef.width,
			vid_so.viddef.height, "conback")
	cl_screen.SCR_AddDirtyPoint(0, 0)
	cl_screen.SCR_AddDirtyPoint(vid_so.viddef.width - 1, lines - 1)

	version = (f"{common_h.APPNAME} v{common_h.YQ2VERSION}")[:48 - 1]

	verLen = len(version)

	for x in range(verLen):

		vid.Draw_CharScaled(vid_so.viddef.width - ((verLen*8+5) * scale) + x * 8 * scale, lines - 35 * scale, 128 + ord(version[x]), scale)


	today = time.localtime() # t = time(NULL); today = localtime(&t);
	timebuf = time.strftime("%H:%M:%S - %m/%d/%Y", today)

	tmpbuf = timebuf[:48 - 1]

	for x in range(21):

		vid.Draw_CharScaled(vid_so.viddef.width - (173 * scale) + x * 8 * scale, lines - 25 * scale, 128 + (ord(tmpbuf[x]) if x < len(tmpbuf) else 0), scale)


	# draw the text
	con.vislines = lines

	rows = (lines - 22) >> 3 # rows of text to draw
	y = int((lines - 30 * scale) / scale) # C int

	# draw from the bottom up
	if con.display != con.current:

		# draw arrows to show the buffer is backscrolled
		for x in range(0, con.linewidth, 4):

			vid.Draw_CharScaled(((x + 1) << 3) * scale, y * scale, ord('^'), scale)


		y -= 8
		rows -= 1


	row = con.display

	i = 0
	while i < rows:

		if row < 0:

			break


		if con.current - row >= con.totallines:

			break # past scrollback wrap point


		text = con.text[row % con.totallines].ljust(con.linewidth) # Q2PORT: the line (see console_t)

		for x in range(con.linewidth):

			vid.Draw_CharScaled(((x + 1) << 3) * scale, y * scale, ord(text[x]), scale)


		i += 1
		y -= 8
		row -= 1


	# draw the download bar, figure out width
	if cl_main.cls.download: # (no USE_CURL)

		text = cl_main.cls.downloadname
		if "/" in text: # strrchr(cls.downloadname, '/')

			text = text[text.rindex("/") + 1:]


		x = con.linewidth - ((con.linewidth * 7) // 40)
		y = x - len(text) - 8
		i = con.linewidth // 3

		if len(text) > i:

			y = x - i - 11
			dlbar = text[:i]
			dlbar += "..."

		else:

			dlbar = text


		dlbar += ": "
		dlbar += "\x80"

		# where's the dot gone?
		if cl_main.cls.downloadpercent == 0:

			n = 0

		else:

			n = y * cl_main.cls.downloadpercent // 100


		for j in range(y):

			if j == n:

				dlbar += "\x83"

			else:

				dlbar += "\x81"



		dlbar += "\x82"

		dlbar += " %02d%%" % cl_main.cls.downloadpercent

		# draw it
		y = int((lines - 12 * scale) / scale) # C int

		for i in range(len(dlbar)):

			vid.Draw_CharScaled(((i + 1) << 3) * scale, y * scale, ord(dlbar[i]), scale)



	# draw the input prompt, user text, and cursor if desired
	Con_DrawInput()
