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

import ctypes
import _ctypes
import os
import sys
import select
import time
import fnmatch
from backends.generic import misc
from client import cl_main
from game import g_main
from common import cvar
from common import frame, filesystem, clientserver
from common.header import common as common_h
from common.header import shared
"""
#include <unistd.h>
#include <signal.h>
#include <stdlib.h>
#include <limits.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <string.h>
#include <ctype.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <errno.h>

#include "../../common/header/common.h"
"""
nostdout = None # cvar_t *;

stdin_active = True #qboolean

game_library = None #static void *, the game is a python module so nothing is opened with dlopen

cfgdir = common_h.CFGDIRNAME #char [MAX_OSPATH]
user_cfgdir = False #static qboolean

# Q2PORT: the port's own config dir (~/.yq2py), so its configs and save games don't replace
# those of a Yamagi Quake II install in ~/.yq2. -cfgdir still works as in Yamagi.
PORT_CFGDIRNAME_SHORT = "yq2py"

_homedir = "" #static char dir[MAX_OSPATH], in Sys_GetHomeDir

def setCustomCfgDir(dir: str): #const char *

	global cfgdir, user_cfgdir

	cfgdir = dir[:shared.MAX_OSPATH - 1]
	user_cfgdir = True

def Sys_Error (error):

	"""
    va_list     argptr;
    char        string[1024];

// change stdin to non blocking
    fcntl (0, F_SETFL, fcntl (0, F_GETFL, 0) & ~FNDELAY);
"""
	cl_main.CL_Shutdown ()

	frame.Qcommon_Shutdown ()
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
	fprintf(stderr, "Warning: %s", warning);
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

def Sys_Quit ():

	cl_main.CL_Shutdown ()
	frame.Qcommon_Shutdown ()
	#fcntl (0, F_SETFL, fcntl (0, F_GETFL, 0) & ~FNDELAY);
	sys.stdout.flush() # Q2PORT: _exit does not flush python's buffered stdout
	os._exit(0)

def Sys_Init():

	#if id386
	#	Sys_SetFPCW();
	#endif
	pass

def Sys_ConsoleInput(): # (returns char *)

	global stdin_active
	#static char text[256];
	#int     len;
	#fd_set	fdset;
	#struct timeval timeout;

	# Q2PORT: env Q2STDIN=1 also reads terminal commands in the GUI build (default off)
	if (frame.dedicated is None or not frame.dedicated.value) and os.environ.get("Q2STDIN") != "1":
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

def Sys_ConsoleOutput (string): #char *

	if nostdout and nostdout.value:
		return

	print (string, end="")


Sys_Microseconds_first = None #static struct timespec first

def Sys_Microseconds(): #void (returns long long)

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14; the C's
	# monotonic clock_gettime is time.monotonic_ns
	global Sys_Microseconds_first

	now = time.monotonic_ns()

	if Sys_Microseconds_first is None:

		# set back first by 1ms so neither this function nor Sys_Milliseconds()
		# (which calls this) will ever return 0
		Sys_Microseconds_first = now - 1000000


	return (now - Sys_Microseconds_first) // 1000

def Sys_Milliseconds (): #(returns int)

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14. It's on the
	# same clock as Sys_Microseconds, which the main loop's curtime comes from
	return int(Sys_Microseconds() // 1000)
	"""
	struct timeval tp;
	struct timezone tzp;
	static int		secbase;

	gettimeofday(&tp, &tzp);
	
	if (!secbase)
	{
		secbase = tp.tv_sec;
		return tp.tv_usec/1000;
	}

	curtime = (tp.tv_sec - secbase)*1000 + tp.tv_usec/1000;
	
	return curtime;

void Sys_Mkdir (char *path)
{
    mkdir (path, 0777);
}

char *strlwr (char *s)
{
	while (*s) {
		*s = tolower(*s);
		s++;
	}
}

//============================================
"""
def Sys_Nanosleep(nanosec: int): #int

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14
	time.sleep(nanosec / 1000000000.0)

def Sys_CpuPause(): #void

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14; the C runs a
	# PAUSE instruction, which Python has no use for
	pass

findbase = None #static	char[MAX_OSPATH];
findpath = None #static	char	[MAX_OSPATH];
findpattern = None #static	char	[MAX_OSPATH];
fdir = None #static DIR	*
fdirCursor = None

def CompareAttributes(path, name, musthave, canthave ): #char *, char *, unsigned, unsigned (returns static qboolean)

	#struct stat st;
	#char fn[MAX_OSPATH];

	# . and .. never match
	if name == "." or name == "..":
		return False

	return True

	#if (stat(fn, &st) == -1)
	#	return False # shouldn't happen

	#if ( ( st.st_mode & S_IFDIR ) && ( canthave & SFF_SUBDIR ) )
	#	return False

	#if ( ( musthave & SFF_SUBDIR ) && !( st.st_mode & S_IFDIR ) )
	#	return False

	#return True

def Sys_FindFirst (path, musthave, canhave): #char *, unsigned, unsigned (returns char *)

	global fdir, findbase, findpath, findpattern, fdirCursor

	#struct dirent *d;
	#char *p;

	if fdir is not None:
		Sys_Error ("Sys_BeginFind without close")

	## COM_FilePath (path, findbase);
	findbase = path

	p = path.rfind('/')
	if p != -1:
		findpattern = path[p+1:]
		findbase = path[:p]
	else:
		findpattern = "*"

	if findpattern == "*.*":
		findpattern = "*"
	
	try:
		fdir = os.listdir(findbase) # fdir = opendir(findbase), entries are names without the directory
	except OSError:
		fdir = None
		return None

	fdirCursor = 0

	while fdirCursor < len(fdir): # while ((d = readdir(fdir)) != NULL)
		d_name = fdir[fdirCursor]
		fdirCursor += 1

		if not findpattern or fnmatch.fnmatchcase(d_name, findpattern): # glob_match(findpattern, d->d_name)
			if CompareAttributes(findbase, d_name, musthave, canhave):
				findpath = "{}/{}".format(findbase, d_name)
				return findpath

	return None

def Sys_FindNext (musthave, canhave):

	global fdir, findbase, findpath, findpattern, fdirCursor
	#struct dirent *d;

	if fdir is None:
		return None

	while fdirCursor < len(fdir):
		d_name = fdir[fdirCursor]
		fdirCursor += 1

		if not findpattern or fnmatch.fnmatchcase(d_name, findpattern): # glob_match(findpattern, d->d_name)
			if CompareAttributes(findbase, d_name, musthave, canhave):
				findpath = "{}/{}".format(findbase, d_name)
				return findpath
	
	return None

def Sys_FindClose ():

	global fdir

	fdir = None

"""
//============================================
"""

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

def Sys_Mkdir(path: str): #const char *

	if not Sys_IsDir(path):

		try:
			os.mkdir(path, 0o755)
		except OSError:
			clientserver.Com_Error(shared.ERR_FATAL, "Couldn't create dir %s\n", path)

def Sys_IsDir(path: str)->bool: #const char * (returns qboolean)

	return os.path.isdir(path)

def Sys_IsFile(path: str)->bool: #const char * (returns qboolean)

	return os.path.isfile(path)

def Sys_GetHomeDir()->str: #(returns char *)

	global _homedir

	if not _homedir:

		home = os.environ.get("HOME")

		if not home:
			# uh-oh
			return None

		if user_cfgdir:
			# custom cfgdir was set by the user: ~/{cfgdir}
			_homedir = "{}/{}/".format(home, cfgdir)
			Sys_Mkdir(_homedir)
			return _homedir

		# hidden dir: ~/.{CFGDIRNAME_SHORT}
		_homedir = "{}/.{}/".format(home, PORT_CFGDIRNAME_SHORT)	# Q2PORT: CFGDIRNAME_SHORT is "yq2"

	Sys_Mkdir(_homedir)
	return _homedir

def Sys_Rename(from_: str, to: str)->int: #const char *, const char * (returns int)

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14
	try:

		os.rename(from_, to)
		return 0

	except OSError:

		return -1

def Sys_Remove(path: str): #const char *

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14
	try:

		os.remove(path)

	except FileNotFoundError: # errno == ENOENT

		pass

	except OSError as err:

		clientserver.Com_Printf("%s: remove %s: %s\n",
			"Sys_Remove", path, err.strerror)

def Sys_RemoveDir(path: str): #const char *

	# Q2PORT: Yamagi's backends/unix/system.c, until group 14
	"""
	char filepath[MAX_OSPATH];
	struct dirent *file;
	DIR *directory;
	"""

	if os.path.isdir(path): # Sys_IsDir(path)

		try:

			names = os.listdir(path) # directory = opendir(path);

		except OSError:

			return

		for name in names: # while ((file = readdir(directory)) != NULL)

			filepath = "{}/{}".format(path, name) # snprintf(filepath, MAX_OSPATH, "%s/%s", path, file->d_name);
			try:
				os.remove(filepath) # Sys_Remove(filepath);
			except OSError:
				pass

		try:
			os.rmdir(path) # Sys_Remove(path);
		except OSError:
			pass

def Sys_Realpath(inpath: str): #const char *, char *, size_t (returns qboolean)
	# Q2PORT: returns the result and the path: ok, out = Sys_Realpath(inpath)

	if not os.path.exists(inpath):

		clientserver.Com_Printf("Couldn't get realpath for %s\n", inpath)
		return False, ""

	return True, os.path.realpath(inpath)

def Sys_GetProcAddress(handle, sym: str): #void *, const char * (returns void *)

	# Q2PORT: dlsym is an attribute of the ctypes library handle; the result is
	# a ctypes function (the caller sets its prototype), or None for NULL
	if handle is None:

		#ifdef RTLD_DEFAULT
		handle = ctypes.CDLL(None) # dlsym(RTLD_DEFAULT, sym)
		#endif

	try:
		return getattr(handle, sym) # dlsym(handle, sym)
	except AttributeError:
		return None

def Sys_FreeLibrary(handle): #void *

	if handle:

		try:
			_ctypes.dlclose(handle._handle)
		except OSError as err:
			clientserver.Com_Error(shared.ERR_FATAL, "dlclose failed on {}: {}".format(handle, err))

def Sys_LoadLibrary(path: str, sym: str): #const char *, const char *, void ** (returns void *entry, void *handle)

	#void *module, *entry;

	handle = None

	try:
		#ifdef USE_SANITIZER
		#else
		module = ctypes.CDLL(path, mode=os.RTLD_LAZY) # dlopen(path, RTLD_LAZY)
		#endif
	except OSError as err:
		module = None
		dlerror = str(err)

	if not module:

		clientserver.Com_Printf("{} failed: {}\n".format("Sys_LoadLibrary", dlerror))
		return None, None

	if sym:

		entry = Sys_GetProcAddress(module, sym) # dlsym(module, sym)

		if not entry:

			clientserver.Com_Printf("{} failed: {}\n".format("Sys_LoadLibrary", "undefined symbol: {}".format(sym)))
			Sys_FreeLibrary(module)
			return None, None

	else:

		entry = None

	clientserver.Com_DPrintf("{} succeeded: {}\n".format("Sys_LoadLibrary", path))

	handle = module

	return entry, handle

_exeDir = "" #static char exeDir[PATH_MAX], in Sys_GetBinaryDir

def Sys_GetBinaryDir()->str: #(returns const char *)
	# Q2PORT: the "executable" is main.py, so this is the directory it is in

	global _exeDir

	if _exeDir != "":
		return _exeDir

	_exeDir = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else ".")) + "/"
	return _exeDir

def Sys_GetClipboardData(): #(returns char *)

	return None

"""
int Sys_GetWorkDir(char *path, size_t len)
{
	return snprintf(path, len, "%s/", Sys_GetCwd());
}
int Sys_SetWorkDir(const char *path)
{
	return chdir(path);
}
"""
def main (): #int argc, char **argv

	global nostdout
	#int time, oldtime, newtime

	# go back to real user for config loads
	#saved_euid = geteuid()
	#seteuid(getuid())

	# Q2PORT: from Yamagi's backends/unix/main.c, until the platform layer (group 14)
	# Implement command line options that the rather
	# crappy argument parser can't parse.
	argv = sys.argv
	argc = len(argv)
	for i in range(argc):

		# Are we portable?
		if argv[i] == "-portable":

			frame.is_portable = True


		# Inject a custom data dir.
		if argv[i] == "-datadir":

			# Mkay, did the user give us an argument?
			if i != (argc - 1):

				# Check if it exists.
				if os.path.exists(argv[i + 1]):

					if not os.path.isdir(argv[i + 1]):

						print("-datadir {} is not a directory".format(argv[i + 1]))
						return 1


					filesystem.datadir = os.path.realpath(argv[i + 1])

				else:

					print("-datadir {} could not be found".format(argv[i + 1]))
					return 1


			else:

				print("-datadir needs an argument")
				return 1



		# Inject a custom config dir.
		if argv[i] == "-cfgdir":

			# We need an argument.
			if i != (argc - 1):

				setCustomCfgDir(argv[i + 1])

			else:

				print("-cfgdir needs an argument")
				return 1




	frame.Qcommon_Init() #argc, argv

	#fcntl(0, F_SETFL, fcntl (0, F_GETFL, 0) | FNDELAY)

	nostdout = cvar.Cvar_Get("nostdout", "0", 0)
	#if !nostdout->value:
	#	fcntl(0, F_SETFL, fcntl (0, F_GETFL, 0) | FNDELAY)
	##	printf ("Linux Quake -- Version %0.3f\n", LINUX_VERSION)


	# Q2PORT: Yamagi's Qcommon_Init ends by running Qcommon_Mainloop; here it
	# returns first, so main can set nostdout (until group 14)
	frame.Qcommon_Mainloop()

"""void Sys_CopyProtect(void)
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