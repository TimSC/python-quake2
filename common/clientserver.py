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

Client / Server interactions

=======================================================================
"""
from __future__ import annotations

from linux import sys_linux
pass
from client import cl_main
from common.header import shared
from common import frame, filesystem
from server import sv_main
from client import cl_console
from client import cl_main
from client import cl_network

"""
#include "header/common.h"
#include <stdlib.h>
#include <setjmp.h>
"""

MAXPRINTMSG = 4096

logfile = None #FILE *
logfile_active = None #cvar_t *, 1 = buffer log, 2 = flush after each print
class abortframe(Exception):	# jmp_buf abortframe, an ERR_DROP occured, exit the entire frame
	pass				# YQ2_LONGJMP (abortframe, 1) raises it, the setjmp in Qcommon_Frame catches it
server_state = 0 #int
color_terminal = None #cvar_t *

# Q2PORT: the unprintable characters Com_VPrintf replaces, as a str.translate table
UNPRINTABLE = {c: ' ' for c in range(32) if c < ord('\t') or c > ord('\r')}
UNPRINTABLE[0x10] = '['
UNPRINTABLE[0x11] = ']'
UNPRINTABLE[0x1D] = '-'
UNPRINTABLE[0x1F] = '-'
UNPRINTABLE[0x1E] = '='

"""
============================================================================

CLIENT / SERVER interactions

============================================================================
"""

rd_target = 0 #static int
rd_buffer = None #static char *, python strings are immutable so the text is held here and passed to rd_flush
rd_buffersize = 0 #static int
rd_flush = None #static void	(*rd_flush)(int target, char *buffer);


def Com_BeginRedirect (target, buffer, buffersize, flush): #int, char *, int, void (*flush)

	global rd_target, rd_buffer, rd_buffersize, rd_flush

	if not target or buffer is None or not buffersize or flush is None:
		return
	rd_target = target
	rd_buffer = ""
	rd_buffersize = buffersize
	rd_flush = flush

def Com_EndRedirect ():

	global rd_target, rd_buffer, rd_buffersize, rd_flush

	rd_flush(rd_target, rd_buffer)

	rd_target = 0
	rd_buffer = None
	rd_buffersize = 0
	rd_flush = None

"""
 * Both client and server can use this, and it will output
 * to the apropriate place.
"""
def Com_VPrintf(print_level: int, fmt: str, argptr: tuple): #int, const char *, va_list
	# Q2PORT: the va_list is the tuple of arguments

	global rd_buffer, logfile

	if (print_level == shared.PRINT_DEVELOPER) and (frame.developer is None or not frame.developer.value):

		return # don't confuse non-developers with techie stuff...

	else:

		"""
		int i;
		char msg[MAXPRINTMSG];
		"""

		msg = (fmt % argptr) if argptr else fmt #int msgLen = vsnprintf(msg, MAXPRINTMSG, fmt, argptr);
		msgLen = len(msg)
		if msgLen >= MAXPRINTMSG:
			msgLen = MAXPRINTMSG-1
			msg = msg[:msgLen]


		if rd_target:

			if (msgLen + len(rd_buffer)) > (rd_buffersize - 1):

				rd_flush(rd_target, rd_buffer)
				rd_buffer = ""


			rd_buffer += msg
			return


		#ifndef DEDICATED_ONLY
		cl_console.Con_Print(msg)
		#endif

		if (msg[:1] == '\x01' or msg[:1] == '\x02') and \
			color_terminal is not None and color_terminal.value:

			# skip color marker
			i = 1

		else:

			i = 0


		# remove unprintable characters
		# Q2PORT: the loop and switch over msg[i:] are done with str.translate (UNPRINTABLE)
		msg = msg[:i] + msg[i:msgLen].translate(UNPRINTABLE)

		# also echo to debugging console
		sys_linux.Sys_ConsoleOutput(msg)

		# logfile
		if logfile_active is not None and logfile_active.value:

			#char name[MAX_OSPATH];

			if (msg[:1] == '\x01') or (msg[:1] == '\x02'):

				# remove color marker
				msg = ' ' + msg[1:]


			if logfile is None:

				name = "{}/qconsole.log".format(filesystem.FS_Gamedir())

				try:	# Q2PORT: Q_fopen returns NULL on failure
					if logfile_active.value > 2:

						logfile = open(name, "a")


					else:

						logfile = open(name, "w")

				except OSError:
					logfile = None



			if logfile is not None:

				logfile.write(msg)


			if logfile_active.value > 1 and logfile is not None:

				logfile.flush()  # force it to save every time

"""
 * Both client and server can use this, and it will output
 * to the apropriate place.
"""
def Com_Printf(fmt: str, *args): #const char *, ...

	#va_list argptr;
	#va_start(argptr, fmt);
	Com_VPrintf(shared.PRINT_ALL, fmt, args)

"""
 * A Com_Printf that only shows up if the "developer" cvar is set
"""
def Com_DPrintf(fmt: str, *args): #const char *, ...

	#va_list argptr;
	#va_start(argptr, fmt);
	Com_VPrintf(shared.PRINT_DEVELOPER, fmt, args)

"""
 * A Com_Printf that only shows up when either the "modder" or "developer"
 * cvars is set
"""
def Com_MDPrintf(fmt: str, *args): #const char *, ...

	#va_list argptr;
	#char msg[MAXPRINTMSG];

	if (frame.modder is None or not frame.modder.value) and (frame.developer is None or not frame.developer.value):

		return


	msg = ((fmt % args) if args else fmt)[:MAXPRINTMSG - 1] #vsnprintf(msg, MAXPRINTMSG, fmt, argptr);

	Com_Printf("%s", msg)

com_error_msg = "" #static char [MAXPRINTMSG], in Com_Error
com_error_recursive = False #static qboolean, in Com_Error

"""
 * Both client and server can use this, and it will
 * do the apropriate things.
"""
def Com_Error(code: int, fmt: str, *args): #int, const char *, ...

	global com_error_msg, com_error_recursive, logfile

	"""
	va_list argptr;
	static char msg[MAXPRINTMSG];
	static qboolean recursive;
	"""

	if com_error_recursive:

		sys_linux.Sys_Error("recursive error after: {}".format(com_error_msg)) #Sys_Error("recursive error after: %s", msg); Q2PORT: Sys_Error takes one string until group 14


	com_error_recursive = True

	msg = ((fmt % args) if args else fmt)[:MAXPRINTMSG - 1] #vsnprintf(msg, MAXPRINTMSG, fmt, argptr);
	com_error_msg = msg

	if code == shared.ERR_DISCONNECT:

		#ifndef DEDICATED_ONLY
		cl_network.CL_Drop()
		#endif
		com_error_recursive = False
		raise abortframe() #YQ2_LONGJMP(abortframe, 1);

	elif code == shared.ERR_DROP:

		Com_Printf("********************\nERROR: %s\n********************\n",
				msg)
		sv_main.SV_Shutdown("Server crashed: {}\n".format(msg), False)
		#ifndef DEDICATED_ONLY
		cl_network.CL_Drop()
		#endif
		com_error_recursive = False
		raise abortframe() #YQ2_LONGJMP(abortframe, 1);

	else:

		sv_main.SV_Shutdown("Server fatal crashed: {}\n".format(msg), False)
		#ifndef DEDICATED_ONLY
		cl_main.CL_Shutdown()
		#endif


	if logfile is not None:

		logfile.close()
		logfile = None


	sys_linux.Sys_Error(msg) #Sys_Error("%s", msg);
	com_error_recursive = False

	

"""
 * Both client and server can use this, and it will
 * do the apropriate things.
"""
def Com_Quit(): #void

	Com_Printf("\n----------- shutting down ----------\n")
	sv_main.SV_Shutdown("Server quit\n", False)
	sys_linux.Sys_Quit()

"""
==================
Com_ServerState
==================
"""
def Com_ServerState (): #(returns int)

	return server_state


"""
==================
Com_SetServerState
==================
"""
def Com_SetServerState (state):

	global server_state

	server_state = state
"""
void
StringList_Free(stringlist_t *sl)
{
	char **cs, **end;

	cs = sl->lst;

	if (cs)
	{
		end = &sl->lst[sl->cap];

		for (; cs < end; cs++)
		{
			if (*cs)
			{
				Z_Free(*cs);
			}
		}

		Z_Free(sl->lst);
	}

	sl->lst = NULL;
	sl->n = 0;
	sl->cap = 0;
}
"""

"""
int
StringList_Find(const stringlist_t *sl, const char *s)
{
	char **cs, **end;

	cs = sl->lst;

	if (!cs)
	{
		return sl->cap + 1;
	}

	end = &cs[sl->cap];

	for (; cs < end; cs++)
	{
		if ((!s && !(*cs)) || (s && *cs && !strcmp(*cs, s)))
		{
			return cs - sl->lst;
		}
	}

	return sl->cap + 1;
}
"""

"""
qboolean
StringList_IsInList(const stringlist_t *sl, const char *s)
{
	return (StringList_Find(sl, s) < sl->cap) ? true : false;
}
"""

"""
void
StringList_Add(stringlist_t *sl, const char *s)
{
	char **cs;
	int nf, n;

	nf = StringList_Find(sl, NULL);

	if (nf < sl->cap)
	{
		cs = &sl->lst[nf];
	}
	else
	{
		n = NextPow2gt(sl->cap);
		sl->lst = Z_Realloc(sl->lst, n * sizeof(*sl->lst));

		cs = &sl->lst[sl->cap];

		sl->cap = n;
	}

	sl->n++;

	*cs = Z_Malloc(strlen(s) + 1);
	strcpy(*cs, s);
}
"""

