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
import time
import fnmatch
"""
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <dirent.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/time.h>

#include "../linux/glob.h"

#include "../qcommon/qcommon.h"

//===============================================================================

byte *membase;
int maxhunksize;
int curhunksize;

void *Hunk_Begin (int maxsize)
{
	// reserve a huge chunk of memory, but don't commit any yet
	maxhunksize = maxsize + sizeof(int);
	curhunksize = 0;
	membase = mmap(0, maxhunksize, PROT_READ|PROT_WRITE, 
		MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
	if (membase == NULL || membase == (byte *)-1)
		Sys_Error("unable to virtual allocate %d bytes", maxsize);

	*((int *)membase) = curhunksize;

	return membase + sizeof(int);
}

void *Hunk_Alloc (int size)
{
	byte *buf;

	// round to cacheline
	size = (size+31)&~31;
	if (curhunksize + size > maxhunksize)
		Sys_Error("Hunk_Alloc overflow");
	buf = membase + sizeof(int) + curhunksize;
	curhunksize += size;
	return buf;
}

int Hunk_End (void)
{
	byte *n;

	n = mremap(membase, maxhunksize, curhunksize + sizeof(int), 0);
	if (n != membase)
		Sys_Error("Hunk_End:  Could not remap virtual block (%d)", errno);
	*((int *)membase) = curhunksize + sizeof(int);
	
	return curhunksize;
}

void Hunk_Free (void *base)
{
	byte *m;

	if (base) {
		m = ((byte *)base) - sizeof(int);
		if (munmap(m, *((int *)m)))
			Sys_Error("Hunk_Free: munmap failed (%d)", errno);
	}
}

//===============================================================================


/*
================
Sys_Milliseconds
================
"""
curtime = 0 #int

def Sys_Milliseconds (): #(returns int)

	global curtime
	curtime = int(time.time() * 1000.0)

	return curtime
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
def Sys_Mkdir (path): #char *

	try:
		os.mkdir (path, 0o777)
	except OSError:
		pass # C ignores the mkdir return value

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
		from linux import sys_linux
		sys_linux.Sys_Error ("Sys_BeginFind without close")

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
