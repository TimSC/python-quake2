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

import pygame
pass
pass
from client import console, client, cl_main, cl_scrn, menu
from linux import sys_linux, q_shlinux
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar

#
# these are the key numbers that should be passed to Key_Event
#
K_TAB			= 9
K_ENTER			= 13
K_ESCAPE		= 27
K_SPACE			= 32

# normal keys should be passed as lowercased ascii

K_BACKSPACE		= 127
K_UPARROW		= 128
K_DOWNARROW		= 129
K_LEFTARROW		= 130
K_RIGHTARROW	= 131

K_ALT			= 132
K_CTRL			= 133
K_SHIFT			= 134
K_F1			= 135
K_F2			= 136
K_F3			= 137
K_F4			= 138
K_F5			= 139
K_F6			= 140
K_F7			= 141
K_F8			= 142
K_F9			= 143
K_F10			= 144
K_F11			= 145
K_F12			= 146
K_INS			= 147
K_DEL			= 148
K_PGDN			= 149
K_PGUP			= 150
K_HOME			= 151
K_END			= 152

K_KP_HOME		= 160
K_KP_UPARROW	= 161
K_KP_PGUP		= 162
K_KP_LEFTARROW	= 163
K_KP_5			= 164
K_KP_RIGHTARROW	= 165
K_KP_END		= 166
K_KP_DOWNARROW	= 167
K_KP_PGDN		= 168
K_KP_ENTER		= 169
K_KP_INS   		= 170
K_KP_DEL		= 171
K_KP_SLASH		= 172
K_KP_MINUS		= 173
K_KP_PLUS		= 174

K_PAUSE			= 255

#
# mouse buttons generate virtual keys
#
K_MOUSE1		= 200
K_MOUSE2		= 201
K_MOUSE3		= 202

#
# joystick buttons
#
K_JOY1			= 203
K_JOY2			= 204
K_JOY3			= 205
K_JOY4			= 206

#
# aux keys are for multi-buttoned joysticks to generate so they can use
# the normal binding process
#
K_AUX1			= 207
K_AUX2			= 208
K_AUX3			= 209
K_AUX4			= 210
K_AUX5			= 211
K_AUX6			= 212
K_AUX7			= 213
K_AUX8			= 214
K_AUX9			= 215
K_AUX10			= 216
K_AUX11			= 217
K_AUX12			= 218
K_AUX13			= 219
K_AUX14			= 220
K_AUX15			= 221
K_AUX16			= 222
K_AUX17			= 223
K_AUX18			= 224
K_AUX19			= 225
K_AUX20			= 226
K_AUX21			= 227
K_AUX22			= 228
K_AUX23			= 229
K_AUX24			= 230
K_AUX25			= 231
K_AUX26			= 232
K_AUX27			= 233
K_AUX28			= 234
K_AUX29			= 235
K_AUX30			= 236
K_AUX31			= 237
K_AUX32			= 238

K_MWHEELDOWN	= 239
K_MWHEELUP		= 240

keypadMapping = {
	K_KP_SLASH: ord('/'),
	K_KP_MINUS: ord('-'),
	K_KP_PLUS: ord('+'),
	K_KP_HOME: ord('7'),
	K_KP_UPARROW: ord('8'),
	K_KP_PGUP: ord('9'),
	K_KP_LEFTARROW: ord('4'),
	K_KP_5: ord('5'),
	K_KP_RIGHTARROW: ord('6'),
	K_KP_END: ord('1'),
	K_KP_DOWNARROW: ord('2'),
	K_KP_PGDN: ord('3'),
	K_KP_INS: ord('0'),
	K_KP_DEL: ord('.'),
}


"""
extern char		*keybindings[256];
extern	int		key_repeats[256];

extern	int	anykeydown;
extern char chat_buffer[];
extern	int chat_bufferlen;
extern	qboolean	chat_team;

#include "client.h"
"""


# key up events are sent even if in console mode

MAXCMDLINE = 256
key_lines = [] #char[32][MAXCMDLINE]
for i in range(32):
	key_lines.append(None)
key_linepos = 0 #int

shift_down = 0 #int
anykeydown = 0 #int

edit_line=0 #int
history_line=0 #int

key_waiting = None # int

keybindings = [] #char	*[256]
for i in range(256):
	keybindings.append(None)

consolekeys = [] #qboolean[256], if true, can't be rebound while in console
for i in range(256):
	consolekeys.append(False)

menubound = [] #qboolean[256], if true, can't be rebound while in menu
for i in range(256):
	menubound.append(False)

keyshift = [] #int[256], key to map to if shift held down in console
for i in range(256):
	keyshift.append(None)

key_repeats = [] #int[256], if > 1, it is autorepeating
for i in range(256):
	key_repeats.append(0)

keydown = [] #qboolean	[256];
for i in range(256):
	keydown.append(False)

"""
typedef struct
{
	char	*name;
	int		keynum;
} keyname_t;
"""
keynames = [ #keyname_t[]

	["TAB", K_TAB],
	["ENTER", K_ENTER],
	["ESCAPE", K_ESCAPE],
	["SPACE", K_SPACE],
	["BACKSPACE", K_BACKSPACE],
	["UPARROW", K_UPARROW],
	["DOWNARROW", K_DOWNARROW],
	["LEFTARROW", K_LEFTARROW],
	["RIGHTARROW", K_RIGHTARROW],

	["ALT", K_ALT],
	["CTRL", K_CTRL],
	["SHIFT", K_SHIFT],
	
	["F1", K_F1],
	["F2", K_F2],
	["F3", K_F3],
	["F4", K_F4],
	["F5", K_F5],
	["F6", K_F6],
	["F7", K_F7],
	["F8", K_F8],
	["F9", K_F9],
	["F10", K_F10],
	["F11", K_F11],
	["F12", K_F12],

	["INS", K_INS],
	["DEL", K_DEL],
	["PGDN", K_PGDN],
	["PGUP", K_PGUP],
	["HOME", K_HOME],
	["END", K_END],

	["MOUSE1", K_MOUSE1],
	["MOUSE2", K_MOUSE2],
	["MOUSE3", K_MOUSE3],

	["JOY1", K_JOY1],
	["JOY2", K_JOY2],
	["JOY3", K_JOY3],
	["JOY4", K_JOY4],

	["AUX1", K_AUX1],
	["AUX2", K_AUX2],
	["AUX3", K_AUX3],
	["AUX4", K_AUX4],
	["AUX5", K_AUX5],
	["AUX6", K_AUX6],
	["AUX7", K_AUX7],
	["AUX8", K_AUX8],
	["AUX9", K_AUX9],
	["AUX10", K_AUX10],
	["AUX11", K_AUX11],
	["AUX12", K_AUX12],
	["AUX13", K_AUX13],
	["AUX14", K_AUX14],
	["AUX15", K_AUX15],
	["AUX16", K_AUX16],
	["AUX17", K_AUX17],
	["AUX18", K_AUX18],
	["AUX19", K_AUX19],
	["AUX20", K_AUX20],
	["AUX21", K_AUX21],
	["AUX22", K_AUX22],
	["AUX23", K_AUX23],
	["AUX24", K_AUX24],
	["AUX25", K_AUX25],
	["AUX26", K_AUX26],
	["AUX27", K_AUX27],
	["AUX28", K_AUX28],
	["AUX29", K_AUX29],
	["AUX30", K_AUX30],
	["AUX31", K_AUX31],
	["AUX32", K_AUX32],

	["KP_HOME",			K_KP_HOME ],
	["KP_UPARROW",		K_KP_UPARROW ],
	["KP_PGUP",			K_KP_PGUP ],
	["KP_LEFTARROW",	K_KP_LEFTARROW ],
	["KP_5",			K_KP_5 ],
	["KP_RIGHTARROW",	K_KP_RIGHTARROW ],
	["KP_END",			K_KP_END ],
	["KP_DOWNARROW",	K_KP_DOWNARROW ],
	["KP_PGDN",			K_KP_PGDN ],
	["KP_ENTER",		K_KP_ENTER ],
	["KP_INS",			K_KP_INS ],
	["KP_DEL",			K_KP_DEL ],
	["KP_SLASH",		K_KP_SLASH ],
	["KP_MINUS",		K_KP_MINUS ],
	["KP_PLUS",			K_KP_PLUS ],

	["MWHEELUP", K_MWHEELUP ],
	["MWHEELDOWN", K_MWHEELDOWN ],

	["PAUSE", K_PAUSE],

	["SEMICOLON", ord(';')],	# because a raw semicolon seperates commands
]

"""
==============================================================================

			LINE TYPING INTO THE CONSOLE

==============================================================================
"""

def CompleteCommand ():

	#char	*cmd, *s;
	global key_lines, edit_line

	s = key_lines[edit_line]
	if len(s) > 1:
		cursor = 1
		if s[cursor] == '\\' or s[cursor] == '/':
			cursor+=1
		s = s[cursor:]

	cmdStr = cmdparser.Cmd_CompleteCommand (s)
	if cmdStr is None:
		cmdStr = cvar.Cvar_CompleteVariable (s)
	if cmdStr is not None:
	
		line = ']/' + cmdStr + ' '
		key_lines[edit_line] = line

		return
	
"""
====================
Key_Console

Interactive line editing and console scrollback
====================
"""
def Key_Console (key): #int
	
	global keypadMapping, key_lines, key_linepos, edit_line, history_line

	if key in keypadMapping:
		key = keypadMapping[key]

	"""
	# Clipboard
	if ( ( chr(key).upper() == 'V' and keydown[K_CTRL] ) or
		 ( ( ( key == K_INS ) or ( key == K_KP_INS ) ) and keydown[K_SHIFT] ) )
	{
		#char *cbd;
		
		if ( ( cbd = Sys_GetClipboardData() ) != 0 )
		{
			int i;

			strtok( cbd, "\n\r\b" );

			i = strlen( cbd );
			if ( i + key_linepos >= MAXCMDLINE)
				i= MAXCMDLINE - key_linepos;

			if ( i > 0 )
			{
				cbd[i]=0;
				strcat( key_lines[edit_line], cbd );
				key_linepos += i;
			}
			free( cbd );
		}

		return;
	}
	"""

	if key == ord('l'): 
		if keydown[K_CTRL]:
			cmdparser.Cbuf_AddText ("clear\n")
			return
	
	if key == K_ENTER or key == K_KP_ENTER:
		# backslash text are commands, else chat
		if len(key_lines[edit_line]) >= 2 and (key_lines[edit_line][1] == '\\' or key_lines[edit_line][1] == '/'):
			cmdparser.Cbuf_AddText (key_lines[edit_line][2:])	# skip the >
		else:
			cmdparser.Cbuf_AddText (key_lines[edit_line][1:])	# valid command

		cmdparser.Cbuf_AddText ("\n")
		clientserver.Com_Printf ("{}\n".format(key_lines[edit_line]))
		edit_line = (edit_line + 1) & 31
		history_line = edit_line
		key_lines[edit_line] = ']'
		key_linepos = 1
		if cl_main.cls.state == client.connstate_t.ca_disconnected:
			cl_scrn.SCR_UpdateScreen ()		# force an update, because the command
											# may take some time
		return
	
	if key == K_TAB:
		# command completion
		CompleteCommand ()
		return
	
	if ( key == K_BACKSPACE ) or ( key == K_LEFTARROW ) or ( key == K_KP_LEFTARROW ) or ( ( key == 'h' ) and ( keydown[K_CTRL] ) ):

		if key_linepos > 1:
			key_lines[edit_line] = key_lines[edit_line][:-1]
			key_linepos-=1
		return

	"""
	if ( ( key == K_UPARROW ) || ( key == K_KP_UPARROW ) ||
		 ( ( key == 'p' ) && keydown[K_CTRL] ) )
	{
		do
		{
			history_line = (history_line - 1) & 31;
		} while (history_line != edit_line
				&& !key_lines[history_line][1]);
		if (history_line == edit_line)
			history_line = (edit_line+1)&31;
		strcpy(key_lines[edit_line], key_lines[history_line]);
		key_linepos = strlen(key_lines[edit_line]);
		return;
	}

	if ( ( key == K_DOWNARROW ) || ( key == K_KP_DOWNARROW ) ||
		 ( ( key == 'n' ) && keydown[K_CTRL] ) )
	{
		if (history_line == edit_line) return;
		do
		{
			history_line = (history_line + 1) & 31;
		}
		while (history_line != edit_line
			&& !key_lines[history_line][1]);
		if (history_line == edit_line)
		{
			key_lines[edit_line][0] = ']';
			key_linepos = 1;
		}
		else
		{
			strcpy(key_lines[edit_line], key_lines[history_line]);
			key_linepos = strlen(key_lines[edit_line]);
		}
		return;
	}
	"""
	if key == K_PGUP or key == K_KP_PGUP:
	
		console.con.display -= 2
		return
	
	if key == K_PGDN or key == K_KP_PGDN:
	
		console.con.display += 2
		if console.con.display > console.con.current:
			console.con.display = console.con.current
		return
	
	if key == K_HOME or key == K_KP_HOME:
	
		console.con.display = console.con.current - console.con.totallines + 10
		return

	if key == K_END or key == K_KP_END:
	
		console.con.display = console.con.current
		return
	
	if key < 32 or key > 127:
		return # non printable
	
	# handle normal character
	if key_linepos < MAXCMDLINE-1:
	
		key_lines[edit_line] = key_lines[edit_line][:key_linepos] + chr(key)
		key_linepos+=1

"""
#============================================================================

char		chat_buffer[MAXCMDLINE];
int			chat_bufferlen = 0;
"""
chat_team = False
chat_buffer = ""
chat_bufferlen = 0
def Key_Message (key): #int 

	global chat_buffer, chat_bufferlen, chat_team

	if key == K_ENTER or key == K_KP_ENTER:
		if chat_team:
			cmdparser.Cbuf_AddText("say_team \"")
		else:
			cmdparser.Cbuf_AddText("say \"")
		cmdparser.Cbuf_AddText(chat_buffer)
		cmdparser.Cbuf_AddText("\"\n")

		cl_main.cls.key_dest = client.keydest_t.key_game
		chat_buffer = ""
		chat_bufferlen = 0
		return

	if key == K_ESCAPE:
		cl_main.cls.key_dest = client.keydest_t.key_game
		chat_buffer = ""
		chat_bufferlen = 0
		return

	if key < 32 or key > 127:
		return

	if key == K_BACKSPACE:
		if chat_bufferlen:
			chat_bufferlen -= 1
			chat_buffer = chat_buffer[:chat_bufferlen]
		return

	if chat_bufferlen >= MAXCMDLINE - 1:
		return

	chat_buffer += chr(key)
	chat_bufferlen += 1
	"""
	if ( key == K_ENTER || key == K_KP_ENTER )
	{
		if (chat_team)
			Cbuf_AddText ("say_team \"");
		else
			Cbuf_AddText ("say \"");
		Cbuf_AddText(chat_buffer);
		Cbuf_AddText("\"\n");

		cls.key_dest = key_game;
		chat_bufferlen = 0;
		chat_buffer[0] = 0;
		return;
	}

	if (key == K_ESCAPE)
	{
		cls.key_dest = key_game;
		chat_bufferlen = 0;
		chat_buffer[0] = 0;
		return;
	}

	if (key < 32 || key > 127)
		return;	// non printable

	if (key == K_BACKSPACE)
	{
		if (chat_bufferlen)
		{
			chat_bufferlen--;
			chat_buffer[chat_bufferlen] = 0;
		}
		return;
	}

	if (chat_bufferlen == sizeof(chat_buffer)-1)
		return; // all full

	chat_buffer[chat_bufferlen++] = key;
	chat_buffer[chat_bufferlen] = 0;
}
"""
"""
#============================================================================



===================
Key_StringToKeynum

Returns a key number to be used to index keybindings[] by looking at
the given string.  Single ascii characters return themselves, while
the K_* names are matched up.
===================
"""
def Key_StringToKeynum (strIn): #char * (returns int)

	#keyname_t	*kn;
	
	if strIn is None or len(strIn) == 0:
		return -1
	if len(strIn) == 1:
		return ord(strIn)

	for kn in keynames:
		if not shared_c.Q_strcasecmp(strIn, kn[0]):
			return kn[1]
	
	return -1
	
	
"""
===================
Key_KeynumToString

Returns a string (either a single ascii char, or a K_* name) for the
given keynum.
FIXME: handle quote special (general escape sequence?)
===================
"""
def Key_KeynumToString (keynum): # int (returns char *)

	#keyname_t	*kn;	
	
	if keynum == -1:
		return "<KEY NOT FOUND>"
	if keynum > 32 and keynum < 127:
		# printable ascii
		return chr(keynum)
		
	for kn in keynames:
		if keynum == kn[1]:
			return kn[0]

	return "<UNKNOWN KEYNUM>"

"""
===================
Key_SetBinding
===================
"""
def Key_SetBinding (keynum, binding): #int, char *
		
	if keynum == -1:
		return;
	
	# allocate memory for new binding
	if len(binding) == 0:
		keybindings[keynum] = None
	else:
		keybindings[keynum] = binding

"""
===================
Key_Unbind_f
===================
"""
def Key_Unbind_f ():

	#int		b;

	if cmdparser.Cmd_Argc() != 2:
	
		clientserver.Com_Printf ("unbind <key> : remove commands from a key\n")
		return
	
	
	b = Key_StringToKeynum (cmdparser.Cmd_Argv(1))
	if b==-1:
	
		clientserver.Com_Printf ("\"{}\" isn't a valid key\n".format( cmdparser.Cmd_Argv(1)))
		return;
	

	Key_SetBinding (b, "")

def Key_Unbindall_f ():
	
	for i in range(256):
		if keybindings[i]:
			Key_SetBinding (i, "")



"""
===================
Key_Bind_f
===================
"""
def Key_Bind_f ():
	
	c = cmdparser.Cmd_Argc()

	if c < 2:
	
		clientserver.Com_Printf ("bind <key> [command] : attach a command to a key\n")
		return
	
	b = Key_StringToKeynum (cmdparser.Cmd_Argv(1))

	if b==-1:
	
		clientserver.Com_Printf ("\"{}\" isn't a valid key\n".format(cmdparser.Cmd_Argv(1)))
		return
	
	if c == 2:
	
		if keybindings[b] is not None:
			clientserver.Com_Printf ("\"{}\" = \"{}\"\n".format(cmdparser.Cmd_Argv(1), keybindings[b]))
		else:
			clientserver.Com_Printf ("\"{}\" is not bound\n".format( cmdparser.Cmd_Argv(1)) )
		return
	
	
	# copy the rest of the command line
	cmdArr = []		# start out with a null string
	for i in range(2, c):
	
		cmdArr.append(cmdparser.Cmd_Argv(i))
		if i != (c-1):
			cmdArr.append(" ")
	
	Key_SetBinding (b, "".join(cmdArr))


"""
============
Key_WriteBindings

Writes lines containing "bind key value"
============
"""
def Key_WriteBindings (f): #FILE *

	#int		i;

	for i in range(256):
		if keybindings[i] is not None and len(keybindings[i])>0:
			f.write("bind {} \"{}\"\n".format(Key_KeynumToString(i), keybindings[i]))

"""
============
Key_Bindlist_f

============
"""
def Key_Bindlist_f ():

	for i in range(256):
		if keybindings[i] is not None:
			clientserver.Com_Printf ("{} \"{}\"\n".format(Key_KeynumToString(i), keybindings[i]))

"""
===================
Key_Init
===================
"""
def Key_Init ():

	global key_lines, key_linepos, consolekeys, keyshift, menubound
	
	for i in range(32):
	
		key_lines[i] = ']'
	
	key_linepos = 1
	
	#
	# init ascii characters in console mode
	#
	for i in range(32, 128):
		consolekeys[i] = True
	consolekeys[K_ENTER] = True
	consolekeys[K_KP_ENTER] = True
	consolekeys[K_TAB] = True
	consolekeys[K_LEFTARROW] = True
	consolekeys[K_KP_LEFTARROW] = True
	consolekeys[K_RIGHTARROW] = True
	consolekeys[K_KP_RIGHTARROW] = True
	consolekeys[K_UPARROW] = True
	consolekeys[K_KP_UPARROW] = True
	consolekeys[K_DOWNARROW] = True
	consolekeys[K_KP_DOWNARROW] = True
	consolekeys[K_BACKSPACE] = True
	consolekeys[K_HOME] = True
	consolekeys[K_KP_HOME] = True
	consolekeys[K_END] = True
	consolekeys[K_KP_END] = True
	consolekeys[K_PGUP] = True
	consolekeys[K_KP_PGUP] = True
	consolekeys[K_PGDN] = True
	consolekeys[K_KP_PGDN] = True
	consolekeys[K_SHIFT] = True
	consolekeys[K_INS] = True
	consolekeys[K_KP_INS] = True
	consolekeys[K_KP_DEL] = True
	consolekeys[K_KP_SLASH] = True
	consolekeys[K_KP_PLUS] = True
	consolekeys[K_KP_MINUS] = True
	consolekeys[K_KP_5] = True

	consolekeys[ord('`')] = False
	consolekeys[ord('~')] = False
	
	for i in range(256):
		keyshift[i] = i
	for i in range(ord('a'), ord('z')+1):
		keyshift[i] = i - ord('a') + ord('A')
	keyshift[ord('1')] = ord('!')
	keyshift[ord('2')] = ord('@')
	keyshift[ord('3')] = ord('#')
	keyshift[ord('4')] = ord('$')
	keyshift[ord('5')] = ord('%')
	keyshift[ord('6')] = ord('^')
	keyshift[ord('7')] = ord('&')
	keyshift[ord('8')] = ord('*')
	keyshift[ord('9')] = ord('(')
	keyshift[ord('0')] = ord(')')
	keyshift[ord('-')] = ord('_')
	keyshift[ord('=')] = ord('+')
	keyshift[ord(',')] = ord('<')
	keyshift[ord('.')] = ord('>')
	keyshift[ord('/')] = ord('?')
	keyshift[ord(';')] = ord(':')
	keyshift[ord('\'')] = ord('"')
	keyshift[ord('[')] = ord('{')
	keyshift[ord(']')] = ord('}')
	keyshift[ord('`')] = ord('~')
	keyshift[ord('\\')] = ord('|')

	menubound[K_ESCAPE] = True
	for i in range(12):
		menubound[K_F1+i] = True

	#
	# register our functions
	#

	cmdparser.Cmd_AddCommand ("bind",Key_Bind_f);
	cmdparser.Cmd_AddCommand ("unbind",Key_Unbind_f);
	cmdparser.Cmd_AddCommand ("unbindall",Key_Unbindall_f);
	cmdparser.Cmd_AddCommand ("bindlist",Key_Bindlist_f);

"""
===================
Key_Event

Called by the system between frames for both key up and key down events
Should NOT be called during an interrupt!
===================
"""

def Key_Event (key, down, timestamp): #int, qboolean, unsigned

	#char	*kb;
	#char	cmd[1024];

	global key_waiting, key_repeats, keydown, menubound, consolekeys, anykeydown, shift_down
	# hack for modal presses
	if key_waiting == -1:
	
		if down:
			key_waiting = key
		return
	
	# update auto-repeat status
	if down:
	
		key_repeats[key] += 1
		if key != K_BACKSPACE \
			and key != K_PAUSE \
			and key != K_PGUP \
			and key != K_KP_PGUP \
			and key != K_PGDN \
			and key != K_KP_PGDN \
			and key_repeats[key] > 1:
			return	# ignore most autorepeats
			
		if key >= 200 and not keybindings[key]:
			clientserver.Com_Printf ("{} is unbound, hit F4 to set.\n".format(Key_KeynumToString (key) ))
	
	else:
	
		key_repeats[key] = 0
	
	
	if key == K_SHIFT:
		shift_down = down

	# console key is hardcoded, so the user can never unbind it
	if key == ord('`') or key == ord('~'):
	
		if not down:
			return
		console.Con_ToggleConsole_f ()
		return
	
	
	# any key during the attract mode will bring up the menu
	if cl_main.cl.attractloop and cl_main.cls.key_dest != client.keydest_t.key_menu and \
		not(key >= K_F1 and key <= K_F12):
		key = K_ESCAPE

	# menu key is hardcoded, so the user can never unbind it
	if key == K_ESCAPE:
	
		if not down:
			return

		if cl_main.cl.frame.playerstate.stats[shared.STAT_LAYOUTS] and cl_main.cls.key_dest == client.keydest_t.key_game:
			# put away help computer / inventory
			cmdparser.Cbuf_AddText ("cmd putaway\n")
			return
		
		if cl_main.cls.key_dest == client.keydest_t.key_message:
			Key_Message (key)
		elif cl_main.cls.key_dest == client.keydest_t.key_menu:
			menu.M_Keydown (key)
		elif cl_main.cls.key_dest in [client.keydest_t.key_game, client.keydest_t.key_console]:
			menu.M_Menu_Main_f ()
		else:
			clientserver.Com_Error (shared.ERR_FATAL, "Bad cls.key_dest")

		return
	
	
	# track if any key is down for BUTTON_ANY
	keydown[key] = down
	if down:
	
		if key_repeats[key] == 1:
			anykeydown+=1
	
	else:
	
		anykeydown-=1
		if anykeydown < 0:
			anykeydown = 0
	

	#
	# key up events only generate commands if the game key binding is
	# a button command (leading + sign).  These will occur even in console mode,
	# to keep the character from continuing an action started before a console
	# switch.  Button commands include the kenum as a parameter, so multiple
	# downs can be matched with ups
	#
	if not down:
	
		kb = keybindings[key]
		if kb and kb[0] == '+':
		
			cmdStr = "-{} {} {}\n".format(kb[1:], key, timestamp)
			cmdparser.Cbuf_AddText (cmdStr)
		
		if keyshift[key] != key:
		
			kb = keybindings[keyshift[key]]
			if kb and kb[0] == '+':
			
				cmdStr = "-{} {} {}\n".format(kb[1:], key, timestamp)
				cmdparser.Cbuf_AddText (cmdStr)
		
		return
	

	#
	# if not a consolekey, send to the interpreter no matter what mode is
	#
	if ( (cl_main.cls.key_dest == client.keydest_t.key_menu and menubound[key])
		or (cl_main.cls.key_dest == client.keydest_t.key_console and not consolekeys[key])
		or (cl_main.cls.key_dest == client.keydest_t.key_game and ( cl_main.cls.state == client.connstate_t.ca_active or not consolekeys[key] ) ) ):
	
		kb = keybindings[key]
		if kb:
		
			if kb[0] == '+':
				# button commands add keynum and timestamp as a parm
				cmdStr = "{} {} {}\n".format(kb, key, timestamp)
				cmdparser.Cbuf_AddText (cmdStr)
			
			else:			
				cmdparser.Cbuf_AddText (kb)
				cmdparser.Cbuf_AddText ("\n")

		return
	
	if not down:
		return		# other systems only care about key down events

	if shift_down:
		key = keyshift[key]

	if cl_main.cls.key_dest == client.keydest_t.key_message:
		Key_Message (key)
	elif cl_main.cls.key_dest == client.keydest_t.key_menu:
		menu.M_Keydown (key)
	elif cl_main.cls.key_dest in [client.keydest_t.key_game, client.keydest_t.key_console]:
		Key_Console (key)
	else:
		clientserver.Com_Error (shared.ERR_FATAL, "Bad cls.key_dest")

"""
===================
Key_ClearStates
===================
"""
def Key_ClearStates ():

	global anykeydown

	#int		i;

	anykeydown = False

	for i in range(256):
	
		if keydown[i] or key_repeats[i]:
			Key_Event( i, False, 0 )
		keydown[i] = 0
		key_repeats[i] = 0
	

"""
===================
Key_GetKey
===================
"""
def Key_GetKey (): #(returns int)

	global key_waiting

	key_waiting = -1

	while key_waiting == -1:
		sys_linux.Sys_SendKeyEvents ()

	return key_waiting



