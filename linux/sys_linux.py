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

import os
import sys
import select
import time
import pygame
from qcommon import common, cvar
from client import cl_main
from linux import q_shlinux, vid_so
from game import g_main
"""
#include <unistd.h>
#include <signal.h>
#include <stdlib.h>
#include <limits.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/stat.h>
#include <string.h>
#include <ctype.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <errno.h>
#include <mntent.h>

#include <dlfcn.h>

#include "../qcommon/qcommon.h"

#include "../linux/rw_linux.h"
"""
nostdout = None # cvar_t *;

sys_frame_time = 0 #unsigned
"""
uid_t saved_euid;
"""
stdin_active = True #qboolean
"""

// =======================================================================
// General routines
// =======================================================================
"""
def Sys_ConsoleOutput (string): #char *

	if nostdout and nostdout.value:
		return

	print (string, end="")

"""
void Sys_Printf (char *fmt, ...)
{
	va_list		argptr;
	char		text[1024];
	unsigned char		*p;

	va_start (argptr,fmt);
	vsprintf (text,fmt,argptr);
	va_end (argptr);

	if (strlen(text) > sizeof(text))
		Sys_Error("memory overwrite in Sys_Printf");

    if (nostdout && nostdout->value)
        return;

	for (p = (unsigned char *)text; *p; p++) {
		*p &= 0x7f;
		if ((*p > 128 || *p < 32) && *p != 10 && *p != 13 && *p != 9)
			printf("[%02x]", *p);
		else
			putc(*p, stdout);
	}
}
"""
def Sys_Quit ():

	cl_main.CL_Shutdown ()
	common.Qcommon_Shutdown ()
	#fcntl (0, F_SETFL, fcntl (0, F_GETFL, 0) & ~FNDELAY);
	sys.stdout.flush() # Q2PORT: _exit does not flush python's buffered stdout
	os._exit(0)


def Sys_Init():

	#if id386
	#	Sys_SetFPCW();
	#endif
	pass


def Sys_Error (error):

	"""
    va_list     argptr;
    char        string[1024];

// change stdin to non blocking
    fcntl (0, F_SETFL, fcntl (0, F_GETFL, 0) & ~FNDELAY);
"""
	cl_main.CL_Shutdown ()

	common.Qcommon_Shutdown ()
	""" 
    va_start (argptr,error);
    vsprintf (string,error,argptr);
    va_end (argptr);
"""
	sys.stderr.write("Error: {}\n".format(error))

	exit (1)

"""
void Sys_Warn (char *warning, ...)
{ 
    va_list     argptr;
    char        string[1024];
    
    va_start (argptr,warning);
    vsprintf (string,warning,argptr);
    va_end (argptr);
	fprintf(stderr, "Warning: %s", string);
} 

/*
============
Sys_FileTime

returns -1 if not present
============
*/
int	Sys_FileTime (char *path)
{
	struct	stat	buf;
	
	if (stat (path,&buf) == -1)
		return -1;
	
	return buf.st_mtime;
}

void floating_point_exception_handler(int whatever)
{
//	Sys_Warn("floating point exception\n");
	signal(SIGFPE, floating_point_exception_handler);
}
"""

def Sys_ConsoleInput(): # (returns char *)

	global stdin_active
	#static char text[256];
	#int     len;
	#fd_set	fdset;
	#struct timeval timeout;

	# Q2PORT: env Q2STDIN=1 also reads terminal commands in the GUI build (default off)
	if (common.dedicated is None or not common.dedicated.value) and os.environ.get("Q2STDIN") != "1":
		return None

	if not stdin_active:
		return None

	# FD_ZERO / FD_SET(0) / zero timeout select on stdin
	try:
		readable, _, _ = select.select ([0], [], [], 0)
	except (OSError, ValueError):
		return None
	if 0 not in readable:
		return None

	text = os.read (0, 256)
	if len(text) == 0: # eof!
		stdin_active = False
		return None

	if len(text) < 1:
		return None
	text = text[:-1].decode("latin-1")    # rip off the /n and terminate

	return text

"""

/*****************************************************************************/
"""
game_library = None #static void *, the game is a python module so nothing is opened with dlopen

"""
=================
Sys_UnloadGame
=================
"""
def Sys_UnloadGame ():

	global game_library

	if game_library is not None:
		pass # dlclose (game_library);
	game_library = None

"""
/*
=================
Sys_GetGameAPI

Loads the game dll
=================
"""
def Sys_GetGameAPI (parms): # void * (returns void *)

	"""
	void	*(*GetGameAPI) (void *);

	char	name[MAX_OSPATH];
	char	curpath[MAX_OSPATH];
	char	*path;
#ifdef __i386__
	const char *gamename = "gamei386.so";
#elif defined __alpha__
	const char *gamename = "gameaxp.so";
#else
#error "Unknown arch"
#endif

	setreuid(getuid(), getuid());
	setegid(getgid());

	if (game_library)
		Com_Error (ERR_FATAL, "Sys_GetGameAPI without Sys_UnloadingGame");

	getcwd(curpath, sizeof(curpath));

	Com_Printf("------- Loading %s -------\n", gamename);

	// now run through the search paths
	path = NULL;
	while (1)
	{
		path = FS_NextPath (path);
		if (!path)
			return NULL;		// couldn't find one anywhere
		sprintf (name, "%s/%s/%s", curpath, path, gamename);
		game_library = dlopen (name, RTLD_LAZY );
		if (game_library)
		{
			Com_Printf ("LoadLibrary (%s)\n",name);
			break;
		}
	}

	GetGameAPI = (void *)dlsym (game_library, "GetGameAPI");
	if (!GetGameAPI)
	{
		Sys_UnloadGame ();		
		return NULL;
	}
	"""
	return g_main.GetGameAPI (parms)

"""
/*****************************************************************************/
"""
def Sys_AppActivate ():

	pass

def Sys_SendKeyEvents ():

	global sys_frame_time

	#ifndef DEDICATED_ONLY
	if vid_so.KBD_Update_fp is not None:
		vid_so.KBD_Update_fp()
	#endif

	# grab frame time 
	sys_frame_time = q_shlinux.Sys_Milliseconds()

"""
/*****************************************************************************/
"""

def Sys_GetClipboardData(): #(returns char *)

	return None


def main (): #int argc, char **argv

	global nostdout
	#int time, oldtime, newtime

	# go back to real user for config loads
	#saved_euid = geteuid()
	#seteuid(getuid())

	common.Qcommon_Init() #argc, argv

	#fcntl(0, F_SETFL, fcntl (0, F_GETFL, 0) | FNDELAY)

	nostdout = cvar.Cvar_Get("nostdout", "0", 0)
	#if !nostdout->value:
	#	fcntl(0, F_SETFL, fcntl (0, F_GETFL, 0) | FNDELAY)
	##	printf ("Linux Quake -- Version %0.3f\n", LINUX_VERSION)


	oldtime = time.time() * 1000.0
	while 1:

		# find time spent rendering last frame
		firstLoop = True
		while firstLoop or elapse_time < 1.0:
			newtime = time.time() * 1000.0
			elapse_time = newtime - oldtime
			firstLoop = False
			if elapse_time < 1.0:
				time.sleep((1.0 - elapse_time) / 1000.0)

		common.Qcommon_Frame (elapse_time)
		oldtime = newtime

"""

void Sys_CopyProtect(void)
{
	FILE *mnt;
	struct mntent *ent;
	char path[MAX_OSPATH];
	struct stat st;
	qboolean found_cd = false;

	static qboolean checked = false;

	if (checked)
		return;

	if ((mnt = setmntent("/etc/mtab", "r")) == NULL)
		Com_Error(ERR_FATAL, "Can't read mount table to determine mounted cd location.");

	while ((ent = getmntent(mnt)) != NULL) {
		if (strcmp(ent->mnt_type, "iso9660") == 0) {
			// found a cd file system
			found_cd = true;
			sprintf(path, "%s/%s", ent->mnt_dir, "install/data/quake2.exe");
			if (stat(path, &st) == 0) {
				// found it
				checked = true;
				endmntent(mnt);
				return;
			}
			sprintf(path, "%s/%s", ent->mnt_dir, "Install/Data/quake2.exe");
			if (stat(path, &st) == 0) {
				// found it
				checked = true;
				endmntent(mnt);
				return;
			}
			sprintf(path, "%s/%s", ent->mnt_dir, "quake2.exe");
			if (stat(path, &st) == 0) {
				// found it
				checked = true;
				endmntent(mnt);
				return;
			}
		}
	}
	endmntent(mnt);

	if (found_cd)
		Com_Error (ERR_FATAL, "Could not find a Quake2 CD in your CD drive.");
	Com_Error (ERR_FATAL, "Unable to find a mounted iso9660 file system.\n"
		"You must mount the Quake2 CD in a cdrom drive in order to play.");
}

#if 0
/*
================
Sys_MakeCodeWriteable
================
*/
void Sys_MakeCodeWriteable (unsigned long startaddr, unsigned long length)
{

	int r;
	unsigned long addr;
	int psize = getpagesize();

	addr = (startaddr & ~(psize-1)) - psize;

//	fprintf(stderr, "writable code %lx(%lx)-%lx, length=%lx\n", startaddr,
//			addr, startaddr+length, length);

	r = mprotect((char*)addr, length + startaddr - addr + psize, 7);

	if (r < 0)
    		Sys_Error("Protection change failed\n");

}

#endif

"""
