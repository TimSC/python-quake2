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
"""
// console.c

#include "client.h"

"""

CON_INPUT_INDICATOR = ord(']')
CON_INPUT_CURSOR = 11

NUM_CON_TIMES = 4

CON_TEXTSIZE = 32768

class console_t(object):

	def __init__(self):

		self.initialized = False #qboolean

		self.text = [] #char	[CON_TEXTSIZE]; Q2PORT: a list of totallines strings, one per line
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
