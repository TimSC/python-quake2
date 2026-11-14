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

The Quake II file system, implements generic file system operations
as well as the .pak file format and support for .pk3 files.

=======================================================================
"""
from __future__ import annotations

import io
import os
from enum import Enum

from q2data import FormatError
from q2data import filesystem as q2fs
from q2data import pak as q2pak
from backends.unix import system
from backends.generic import misc
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import argproc, clientserver, cmdparser, cvar, frame, glob, zone

"""
#ifndef _MSC_VER
#include <libgen.h>
#endif

#include "header/common.h"
#include "header/glob.h"

#ifdef USE_SYSTEM_MINIZIP
#include <minizip/unzip.h>
#else
#include "unzip/unzip.h"
#endif

#include "../client/sound/header/vorbis.h"
"""
# .pak and .pk3 files are read with q2data.pak (Python's zipfile in place of minizip)

MAX_HANDLES = 512
MAX_MODS = 32
MAX_PAKS = q2fs.MAX_PAKS

#ifdef SYSTEMWIDE
# #ifndef SYSTEMDIR
#  #define SYSTEMDIR "/usr/share/games/quake2"
# #endif
#endif

class fsMode_t(Enum):	# Q2PORT: fsMode_t is in common.h, used only here
	FS_READ = 0
	FS_WRITE = 1
	FS_APPEND = 2

class fsHandle_t(object):

	def __init__(self):

		self.name = "" #char [MAX_QPATH]
		self.mode = None #fsMode_t
		self.file = None #FILE *, or an io.BytesIO of a pack member

class fsLink_t(object):

	def __init__(self):

		self.from_ = None #char *
		self.to = None #char *
		self.length = 0 #int
		#struct fsLink_s *next;

class fsPackFile_t(object):

	def __init__(self):

		self.name = "" #char [MAX_QPATH]
		self.size = 0 #int
		self.offset = 0 #int, Ignored in PK3 files.

class fsPack_t(object):

	def __init__(self):

		self.name = "" #char [MAX_OSPATH]
		self.numFiles = 0 #int
		self.archive = None # q2data.pak.PakArchive or ZipArchive
		self.isProtectedPak = False #qboolean
		self.files = [] #fsPackFile_t *
		self.lookup = {} # Q2PORT: lower-case name -> index, in place of FS_PackQuickSearch's binary search

class fsSearchPath_t(object):

	def __init__(self):

		self.path = "" #char [MAX_OSPATH], Only one used.
		self.pack = None #fsPack_t *, (path or pack)
		#struct fsSearchPath_s *next;

class fsPackFormat_t(Enum):
	PAK = 0
	PK3 = 1

class fsPackTypes_t(object):

	def __init__(self, suffix, format):

		self.suffix = suffix #char *
		self.format = format #fsPackFormat_t

fs_handles = [] #fsHandle_t [MAX_HANDLES]
for i in range(MAX_HANDLES):
	fs_handles.append(fsHandle_t())
fs_links = [] #fsLink_t *, Q2PORT: the linked list is a Python list, newest first
fs_searchPaths = [] #fsSearchPath_t *, Q2PORT: the linked list is a Python list, head first
fs_baseSearchPaths = 0 #fsSearchPath_t *, Q2PORT: the number of generic search paths at the end of fs_searchPaths

# Pack formats / suffixes.
# the pack types, from q2data.filesystem.PACK_TYPES (pak, pk2, pk3, pkz, zip)
fs_packtypes = [fsPackTypes_t(suffix, fsPackFormat_t.PAK if reader is q2pak.PakArchive else fsPackFormat_t.PK3)
	for suffix, reader in q2fs.PACK_TYPES]

datadir = "" #char [MAX_OSPATH]
fs_gamedir = "" #char [MAX_OSPATH]
file_from_protected_pak = False #qboolean

fs_basedir = None #cvar_t *
fs_cddir = None #cvar_t *
fs_gamedirvar = None #cvar_t *
fs_debug = None #cvar_t *

# --------

# Raw search path, the actual search
# bath is build from this one.
class fsRawPath_t(object):

	def __init__(self):

		self.path = "" #char [MAX_OSPATH]
		self.create = False #qboolean
		#struct fsRawPath_s *next;

fs_rawPath = [] #fsRawPath_t *, Q2PORT: the linked list is a Python list, head first

# --------

#if _WIN32
# ... minizip Unicode trickery, not needed here
#endif

"""
 * All of Quake's data access is through a hierchal file system, but the
 * contents of the file system can be transparently merged from several
 * sources.
 *
 * The "base directory" is the path to the directory holding the quake.exe and
 * all game directories.  The sys_* files pass this to host_init in
 * quakeparms_t->basedir.  This can be overridden with the "-basedir" command
 * line parm to allow code debugging in a different directory.  The base
 * directory is only used during filesystem initialization.
 *
 * The "game directory" is the first tree on the search path and directory that
 * all generated files (savegames, screenshots, demos, config files) will be
 * saved to.  This can be overridden with the "-game" command line parameter.
 * The game directory can never be changed while quake is executing.  This is
 * a precacution against having a malicious server instruct clients to write
 * files over areas they shouldn't.
 *
"""

def FS_FileLength(f)->int: #FILE * (returns static int)

	"""
	int pos; /* Current position. */
	int end; /* End of file. */
	"""

	try:	# Q2PORT: ftell and fseek raise instead of returning -1
		pos = f.tell()
	except OSError:
		clientserver.Com_Printf("%s: refusing to ftell\n", "FS_FileLength")
		return -1

	try:
		f.seek(0, os.SEEK_END)
	except OSError:
		clientserver.Com_Printf("%s: seek failed", "FS_FileLength")
		return -1

	end = f.tell()

	try:
		f.seek(pos, os.SEEK_SET)
	except OSError:
		clientserver.Com_Printf("%s: seek failed", "FS_FileLength")
		return -1


	return end

"""
 * Creates any directories needed to store the given filename.
"""
def FS_CreatePath(path: str): #const char *

	"""
	char *cur; /* Current '/'. */
	char *old; /* Old '/'. */
	char dir_path[MAX_OSPATH];
	"""

	FS_DPrintf("%s(%s)\n", "FS_CreatePath", path)

	if ".." in path:

		clientserver.Com_Printf("WARNING: refusing to create relative path '%s'.\n", path)
		return


	dir_path = path[:shared.MAX_OSPATH - 1]

	# Q2PORT: cur and old are offsets into dir_path; -1 is NULL
	cur = old = 0

	while cur != -1:

		if (cur - old) > 1:

			system.Sys_Mkdir(dir_path[:cur]) #*cur = '\0'; Sys_Mkdir(dir_path); *cur = '/';


		old = cur
		cur = dir_path.find('/', old + 1)

def FS_DPrintf(format: str, *args): #const char *, ...

	"""
	char msg[1024];
	va_list argPtr;
	"""

	if fs_debug.value != 1:

		return


	msg = ((format % args) if args else format)[:1023] #vsnprintf(msg, sizeof(msg), format, argPtr);

	clientserver.Com_Printf("%s", msg)

def FS_Gamedir()->str: #(returns const char *)

	return fs_gamedir

"""
 * Finds a free fileHandle_t.
"""
def FS_HandleForFile(path: str): #const char *, fileHandle_t * (returns static fsHandle_t *)
	# Q2PORT: returns the handle and the fileHandle_t: handle, f = FS_HandleForFile(path)

	"""
	int i;
	fsHandle_t *handle;
	"""

	for i in range(MAX_HANDLES):

		handle = fs_handles[i]
		if handle.file is None:

			handle.name = path[:shared.MAX_QPATH - 1]
			return handle, i + 1



	# Failed.
	clientserver.Com_Error(shared.ERR_DROP, "%s: none free", "FS_HandleForFile")

	return None, 0

"""
 * Returns a fsHandle_t * for the given fileHandle_t.
"""
def FS_GetFileByHandle(f: int)->fsHandle_t: #fileHandle_t (returns fsHandle_t *)

	if (f < 0) or (f > MAX_HANDLES):

		clientserver.Com_Error(shared.ERR_DROP, "%s: out of range", "FS_GetFileByHandle")
		return None


	if f == 0:

		f += 1


	return fs_handles[f - 1]

"""
 * Other dll's can't just call fclose() on files returned by FS_FOpenFile.
"""
def FS_FCloseFile(f: int): #fileHandle_t

	"""
	fsHandle_t *handle;
	"""

	handle = FS_GetFileByHandle(f)

	if handle.file is not None:

		handle.file.close()


	fs_handles[fs_handles.index(handle)] = fsHandle_t() #memset(handle, 0, sizeof(*handle));

def FS_SortPackCompare(file1: fsPackFile_t)->str: #const void *, const void * (returns static int)
	# Q2PORT: a sort key in place of a qsort comparator; Q_stricmp compares case-insensitively

	return file1.name.lower()

def FS_SortPack(pak: fsPack_t): #fsPack_t *

	pak.files.sort(key=FS_SortPackCompare) #qsort(pak->files, pak->numFiles, sizeof(fsPackFile_t), FS_SortPackCompare);
	pak.lookup = {}
	for i in range(len(pak.files)):
		pak.lookup.setdefault(pak.files[i].name.lower(), i)

def FS_PackQuickSearch(pak: fsPack_t, name: str)->int: #const fsPack_t *, const char * (returns static int)
	# Q2PORT: a dictionary lookup in place of the binary search over the sorted names

	return pak.lookup.get(name.lower(), -1)

"""
 * Finds the file in the search path. Returns filesize and an open FILE *. Used
 * for streaming data out of either a pak file or a seperate file.
"""
def FS_FOpenFile(rawname: str, gamedir_only: bool = False): #const char *, fileHandle_t *, qboolean (returns int)
	# Q2PORT: returns the size and the fileHandle_t: size, f = FS_FOpenFile(name)

	global file_from_protected_pak

	"""
	char path[MAX_OSPATH], lwrName[MAX_OSPATH];
	fsHandle_t *handle;
	fsPack_t *pack;
	fsSearchPath_t *search;
	int input, output;
	"""

	f = 0

	# Remove self references and empty dirs from the requested path.
	# ZIPs and PAKs don't support them, but they may be hardcoded in
	# some custom maps or models.
	name = [] #char name[MAX_OSPATH] = {0};
	namelen = len(rawname)
	if namelen > shared.MAX_OSPATH - 1:

		clientserver.Com_Printf("%s: used unexpectly long name: %s\n", "FS_FOpenFile", rawname)
		return -1, 0


	rawname_at = lambda k: rawname[k] if k < namelen else '\0'	# Q2PORT: rawname[k] with the terminating NUL
	inp = 0
	while inp < namelen:

		# Remove self reference.
		if rawname[inp] == '.':

			if len(name) > 0:

				# Inside the path.
				if name[-1] == '/' and rawname_at(inp + 1) == '/':

					inp += 2
					continue


			else:

				# At the beginning. Note: This is save because the Quake II
				# VFS doesn't have a current working dir. Paths are always
				# absolute.
				if rawname_at(inp + 1) == '/':

					inp += 1
					continue




		# Empty dir.
		if rawname[inp] == '/':

			if rawname_at(inp + 1) == '/':

				inp += 1
				continue



		# Paths starting with a /. I'm not sure if this is
		# a problem. It shouldn't hurt to remove the leading
		# slash, though.
		if rawname[inp] == '/' and len(name) == 0:

			inp += 1
			continue


		name.append(rawname[inp])
		inp += 1

	name = "".join(name)

	file_from_protected_pak = False
	handle, f = FS_HandleForFile(name)
	handle.name = name[:shared.MAX_QPATH - 1]
	handle.mode = fsMode_t.FS_READ

	# Search through the path, one element at a time.
	for search in fs_searchPaths:

		if gamedir_only:

			if FS_Gamedir() not in search.path:

				continue



		# Evil hack for maps.lst and players/
		# TODO: A flag to ignore paks would be better
		if (fs_gamedirvar.string == "") and search.pack is not None:

			if (name == "maps.lst") or (name[:8] == "players/"):

				if FS_FileInGamedir(name):

					continue




		# Search inside a pack file.
		if search.pack is not None:

			pack = search.pack
			i = FS_PackQuickSearch(pack, handle.name)

			if i >= 0:

				# Found it!
				if fs_debug.value:

					clientserver.Com_Printf("%s: '%s' (found in '%s').\n",
						"FS_FOpenFile", handle.name, pack.name)


				# save the name with *correct case* in the handle
				# (relevant for savegames, when starting map with wrong case but it's still found
				#  because it's from pak, but save/bla/MAPname.sav/sv2 will have wrong case and can't be found then)
				handle.name = pack.files[i].name[:shared.MAX_QPATH - 1]

				if pack.isProtectedPak:

					file_from_protected_pak = True

				# The member is read whole (q2data.pak) and served from memory,
				# so a read can't run past its end into the next file.
				try:
					handle.file = io.BytesIO(pack.archive.read(pack.files[i].name))
					return pack.files[i].size, f
				except (OSError, FormatError):
					handle.file = None

				clientserver.Com_Error(shared.ERR_FATAL, "Couldn't reopen '%s'", pack.name)
				return 0, f


		else:

			# Search in a directory tree.
			path = "{}/{}".format(search.path, handle.name) #Com_sprintf(path, sizeof(path), "%s/%s", search->path, handle->name);

			handle.file = Q_fopen(path, "rb")

			if handle.file is None:

				lwrName = handle.name.lower() #Q_strlwr(lwrName);
				path = "{}/{}".format(search.path, lwrName)
				handle.file = Q_fopen(path, "rb")


			if handle.file is not None:

				if fs_debug.value:

					clientserver.Com_Printf("%s: '%s' (found in '%s').\n",
						"FS_FOpenFile", handle.name, search.path)


				return FS_FileLength(handle.file), f



	if fs_debug.value:

		clientserver.Com_Printf("%s: couldn't find '%s'.\n", "FS_FOpenFile", handle.name)


	# Couldn't open, so free the handle.
	fs_handles[f - 1] = fsHandle_t() #memset(handle, 0, sizeof(*handle));
	f = 0
	return -1, f

def Q_fopen(file: str, mode: str): #const char *, const char * (returns FILE *)
	# Q2PORT: shared.c's Q_fopen: only regular files (or new ones), NULL on failure

	if os.path.exists(file) and not os.path.isfile(file):
		return None
	try:
		return open(file, mode)
	except OSError:
		return None

"""
 * Properly handles partial reads.
"""
def FS_Read(size: int, f): #void *, int, fileHandle_t (returns int)
	# Q2PORT: returns the bytes read (the buffer); f may also still be a Python file object
	# (save games, the menu and the collision code until their groups are ported)

	"""
	qboolean tried = false;    /* Tried to read from a CD. */
	byte *buf;        /* Buffer. */
	int r;         /* Number of bytes read. */
	int remaining;        /* Remaining bytes. */
	fsHandle_t *handle;  /* File handle. */
	"""

	if not isinstance(f, int):	# Q2PORT: a FILE * from id's code
		return f.read(size)

	tried = False
	handle = FS_GetFileByHandle(f)

	# Read.
	remaining = size
	buf = []

	while remaining:

		if handle.file is not None:

			data = handle.file.read(remaining)


		else:

			return b""

		r = len(data)

		if r == 0:

			if not tried:

				# Might tried to read from a CD.
				tried = True

			else:

				# Already tried once.
				clientserver.Com_Error(shared.ERR_FATAL, "%s: 0 bytes read from '%s'",
					"FS_Read", handle.name)
				return b"".join(buf)


		remaining -= r
		buf.append(data)


	return b"".join(buf)

"""
 * Properly handles partial reads of size up to count times. No error if it
 * can't read.
"""
def FS_FRead(size: int, count: int, f): #void *, int, int, fileHandle_t (returns int)
	# Q2PORT: returns the bytes read (the buffer)

	"""
	qboolean tried = false;    /* Tried to read from a CD. */
	byte *buf;        /* Buffer. */
	int loops;         /* Loop indicator. */
	int r;         /* Number of bytes read. */
	int remaining;         /* Remaining bytes. */
	fsHandle_t *handle;  /* File handle. */
	"""

	if not isinstance(f, int):	# Q2PORT: a FILE * from id's code
		return f.read(size * count)

	tried = False
	handle = FS_GetFileByHandle(f)

	# Read.
	loops = count
	buf = []

	while loops:

		# Read in chunks.
		remaining = size

		while remaining:

			if handle.file is not None:

				data = handle.file.read(remaining)


			else:

				return b"".join(buf)

			r = len(data)

			if r == 0:

				if not tried:

					# Might tried to read from a CD.
					tried = True

				else:

					# Already tried once.
					return b"".join(buf)



			remaining -= r
			buf.append(data)


		loops -= 1


	return b"".join(buf)

"""
 * Filename is reletive to the quake search path
 * A null buffer will just return the file length
 * pad adds bytes at the end of the buffer
 * The buffer must be freed by the caller with FS_FreeFile
"""
def FS_LoadFile2(path: str, pad: int): #const char *, void **, int (returns int)
	# Q2PORT: returns the size and the buffer: size, buffer = FS_LoadFile2(path, pad); the pad isn't added

	"""
	fileHandle_t f;
	int size;
	"""

	size, f = FS_FOpenFile(path, False)

	if size <= 0:

		if not size:

			FS_FCloseFile(f)


		return size, None


	buffer = FS_Read(size, f)

	FS_FCloseFile(f)

	return size, buffer

def FS_LoadFile(path: str): #const char *, void ** (returns int)
	# Q2PORT: returns the size and the buffer: size, buffer = FS_LoadFile(path)

	return FS_LoadFile2(path, 1) # safety null byte

def FS_FreeFile(buffer): #void *

	if buffer is None:

		FS_DPrintf("FS_FreeFile: NULL buffer.\n")
		return


	#Z_Free(buffer);

def FS_FreeRawPaths(start: int, end: int): #fsRawPath_t *, fsRawPath_t * (returns static fsRawPath_t *)
	# Q2PORT: start and end are positions in the fs_rawPath list; the entries from start to end are removed

	del fs_rawPath[start:end]

def FS_FreeSearchPaths(start: int, end: int): #fsSearchPath_t *, fsSearchPath_t * (returns static fsSearchPath_t *)
	# Q2PORT: start and end are positions in the fs_searchPaths list; the entries from start to end are removed

	for cur in fs_searchPaths[start:end]:

		if cur.pack is not None:

			if isinstance(cur.pack.archive, q2pak.ZipArchive):

				cur.pack.archive.close()


			#Z_Free(cur->pack->files);
			#Z_Free(cur->pack);


	del fs_searchPaths[start:end]

"""
 * Takes an explicit (not game tree related) path to a pak file.
 *
 * Loads the header and directory, adding the files at the beginning of the
 * list so they override previous pack files.
"""
def FS_LoadPAK(packPath: str)->fsPack_t: #const char * (returns static fsPack_t *)

	if not os.path.isfile(packPath):

		return None

	try:
		archive = q2pak.PakArchive(packPath)
	except OSError:
		return None
	except FormatError as err:
		if str(err) == "not a pack file":
			clientserver.Com_Error(shared.ERR_FATAL, "%s: '%s' is not a pack file", "FS_LoadPAK", packPath)
		else:
			clientserver.Com_Error(shared.ERR_FATAL, "%s: '%s' is too short.", "FS_LoadPAK", packPath)
		return None

	numFiles = len(archive)

	if numFiles > q2pak.MAX_FILES_IN_PACK:

		clientserver.Com_Printf("%s: '%s' has %i > %i files\n",
			"FS_LoadPAK", packPath, numFiles, q2pak.MAX_FILES_IN_PACK)

	files = []

	for entry in archive.entries:

		fi = fsPackFile_t()
		fi.name = entry.name[:shared.MAX_QPATH - 1]
		fi.offset = entry.offset
		fi.size = entry.length
		files.append(fi)

	pack = fsPack_t()
	pack.name = packPath[:shared.MAX_OSPATH - 1]
	pack.archive = archive
	pack.numFiles = numFiles
	pack.files = files

	clientserver.Com_Printf("Added packfile '%s' (%i files).\n", pack.name, numFiles)

	return pack

"""
 * Takes an explicit (not game tree related) path to a pack file.
 *
 * Loads the header and directory, adding the files at the beginning of the list
 * so they override previous pack files.
"""
def FS_LoadPK3(packPath: str)->fsPack_t: #const char * (returns static fsPack_t *)

	if not os.path.isfile(packPath):

		return None

	try:
		archive = q2pak.ZipArchive(packPath)
	except (OSError, FormatError):
		clientserver.Com_Error(shared.ERR_FATAL, "%s: '%s' is not a pack file", "FS_LoadPK3", packPath)
		return None

	numFiles = len(archive)

	if numFiles <= 0:

		archive.close()
		clientserver.Com_Error(shared.ERR_FATAL, "%s: '%s' has %i files",
				"FS_LoadPK3", packPath, numFiles)
		return None

	files = []

	for name in archive.names():

		fi = fsPackFile_t()
		fi.name = name[:shared.MAX_QPATH - 1]
		fi.offset = -1 # Not used in ZIP files
		fi.size = archive.size(name)
		files.append(fi)

	pack = fsPack_t()
	pack.name = packPath[:shared.MAX_OSPATH - 1]
	pack.archive = archive
	pack.numFiles = numFiles
	pack.files = files

	clientserver.Com_Printf("Added packfile '%s' (%i files).\n", pack.name, numFiles)

	return pack

"""
 * Allows enumerating all of the directories in the search path.
"""
_nextpath_index = -1	# Q2PORT: position of the path FS_NextPath returned last, in place of comparing C pointers

def FS_NextPath(prevPath: str)->str: #const char * (returns const char *)
	# Q2PORT: the C compares prevPath with the pointers it returned; equal strings would loop
	# for ever here, so the position of the last returned path is remembered

	global _nextpath_index

	"""
	char *prev;
	fsSearchPath_t *search;
	"""

	paths = [fs_gamedir] + [search.path for search in fs_searchPaths if search.pack is None]

	if prevPath is None:

		_nextpath_index = 0
		return fs_gamedir


	if not (0 <= _nextpath_index < len(paths) and paths[_nextpath_index] == prevPath):

		_nextpath_index = paths.index(prevPath) if prevPath in paths else len(paths)


	_nextpath_index += 1
	if _nextpath_index < len(paths):

		return paths[_nextpath_index]


	return None

def FS_Path_f(): #void

	"""
	int i;
	int totalFiles = 0;
	fsSearchPath_t *search;
	fsHandle_t *handle;
	fsLink_t *link;
	"""

	totalFiles = 0

	clientserver.Com_Printf("Current search path:\n")

	for search in fs_searchPaths:

		if search.pack is not None:

			clientserver.Com_Printf("%s (%i files)\n", search.pack.name,
					search.pack.numFiles)
			totalFiles += search.pack.numFiles

		else:

			clientserver.Com_Printf("%s\n", search.path)



	clientserver.Com_Printf("\n")

	clientserver.Com_Printf("Raw search paths:\n")
	for raw in fs_rawPath:

		clientserver.Com_Printf("%s\n", raw.path)


	clientserver.Com_Printf("\n")

	for i in range(MAX_HANDLES):

		handle = fs_handles[i]
		if handle.file is not None:

			clientserver.Com_Printf("Handle %i: '%s'.\n", i + 1, handle.name)



	for i in range(len(fs_links)):

		link = fs_links[i]
		clientserver.Com_Printf("Link %i: '%s' -> '%s'.\n", i, link.from_, link.to)


	clientserver.Com_Printf("----------------------\n")

	clientserver.Com_Printf("%i files in PAK/PK2/PK3/ZIP files.\n", totalFiles)

"""
 * Creates a filelink_t.
"""
def FS_Link_f(): #void

	"""
	fsLink_t *l, **prev;
	"""

	if cmdparser.Cmd_Argc() != 3:

		clientserver.Com_Printf("USAGE: link <from> <to>\n")
		return


	# See if the link already exists.
	for l in fs_links:

		if l.from_ == cmdparser.Cmd_Argv(1):

			#Z_Free(l->to);

			if len(cmdparser.Cmd_Argv(2)) == 0:

				# Delete it.
				fs_links.remove(l) #*prev = l->next;
				return


			l.to = cmdparser.Cmd_Argv(2) #CopyString(Cmd_Argv(2));
			return



	# Create a new link.
	l = fsLink_t()
	fs_links.insert(0, l) #l->next = fs_links; fs_links = l;
	l.from_ = cmdparser.Cmd_Argv(1)
	l.length = len(l.from_)
	l.to = cmdparser.Cmd_Argv(2)

"""
 * Create a list of files that match a criteria.
"""
def FS_ListFiles(findname: str, musthave: int, canthave: int)->shared.strlist_t: #const char *, unsigned, unsigned (returns strlist_t)

	"""
	strlist_t list;
	const char *s;
	"""

	lst = shared.strlist_t()
	shared_c.StrList_Init(lst, 0)

	s = system.Sys_FindFirst(findname, musthave, canthave)

	while s is not None:

		if s[-1] != '.':

			shared_c.StrList_Append(lst, s)


		s = system.Sys_FindNext(musthave, canthave)


	system.Sys_FindClose()

	return lst

"""
 * Compare file attributes (musthave and canthave) in packed files. If
 * "output" is not NULL, "size" is greater than zero and the file matches the
 * attributes then a copy of the matching string will be placed there (with
 * SFF_SUBDIR it changes).
"""
def ComparePackFiles(findname: str, name: str, musthave: int, canthave: int): #const char *, const char *, unsigned, unsigned, char *, int (returns static qboolean)
	# Q2PORT: returns the result and the output string: retval, output = ComparePackFiles(...)

	"""
	qboolean retval;
	char *ptr;
	char buffer[MAX_OSPATH];
	"""

	buffer = name[:shared.MAX_OSPATH - 1]

	if (canthave & shared.SFF_SUBDIR) and (name[-1:] == '/'):

		return False, None


	if musthave & shared.SFF_SUBDIR:

		ptr = buffer.rfind('/')
		if ptr != -1:

			buffer = buffer[:ptr]

		else:

			return False, None



	if (musthave & shared.SFF_HIDDEN) or (canthave & shared.SFF_HIDDEN):

		ptr = buffer.rfind('/')
		if ptr == -1:

			ptr = 0


		c = buffer[ptr + 1:ptr + 2] #ptr[1]
		if ((musthave & shared.SFF_HIDDEN) and (c != '.')) or \
			((canthave & shared.SFF_HIDDEN) and (c == '.')):

			return False, None



	if canthave & shared.SFF_RDONLY:

		return False, None


	retval = glob.glob_match(findname, buffer)

	return retval, (buffer if retval else None)

"""
 * Create a list of files that match a criteria.
 * Searchs are relative to the game directory and use all the search paths
 * including .pak and .pk3 files.
"""
def FS_ListFiles2(findname: str, musthave: int, canthave: int)->shared.strlist_t: #const char *, unsigned, unsigned (returns strlist_t)

	"""
	strlist_t list;
	fsSearchPath_t *search;
	"""

	lst = shared.strlist_t()
	shared_c.StrList_Init(lst, 0)

	for search in fs_searchPaths:

		"""
		strlist_t tmplist;
		char path[MAX_OSPATH];
		size_t splen;
		int i;
		"""

		if search.pack is not None:

			if canthave & common_h.SFF_INPACK:

				continue


			for i in range(search.pack.numFiles):

				ok, path = ComparePackFiles(findname, search.pack.files[i].name,
							musthave, canthave)
				if ok:

					if not shared.StrList_Contains(lst, path):

						shared_c.StrList_Append(lst, path)





		if (musthave & common_h.SFF_INPACK) or \
			(search.path == ""):

			continue


		# files from host filesystem
		path = "{}/{}".format(search.path, findname)
		tmplist = FS_ListFiles(path, musthave, canthave)

		splen = len(search.path)

		for i in range(tmplist.num):

			s = tmplist.data[i][splen + 1:]

			if not shared.StrList_Contains(lst, s):

				shared_c.StrList_Append(lst, s)



		shared_c.StrList_Free(tmplist)


	return lst

"""
 * Comparator for mod sorting
"""
def Q_sort_modcmp(s1: str)->tuple: #const void *, const void * (returns static int)
	# Q2PORT: a sort key in place of the qsort comparator

	first_mods = [common_h.BASEDIRNAME, "xatrix", "rogue", "ctf"] #static const char *[]

	for i in range(len(first_mods)):

		if not shared_c.Q_stricmp(first_mods[i], s1):

			return (i, "")


	return (len(first_mods), s1.lower())

"""
 * Combs all Raw search paths to find game dirs containing PAK/PK2/PK3 files.
 * Returns an alphabetized array of unique relative dir names.
"""
def HasValidPack(dir: str)->bool: #const char * (returns static qboolean)

	"""
	const fsPackTypes_t *pkt;
	"""

	# iterate over supported pack types, but ignore ZIP files (they cause false positives)
	for pkt in fs_packtypes:

		"""
		strlist_t packs;
		char findnamepattern[MAX_OSPATH];
		int npacks;
		"""

		if "zip" == pkt.suffix:

			continue


		findnamepattern = "{}/*.{}".format(dir, pkt.suffix)

		packs = FS_ListFiles(findnamepattern, 0, 0)
		npacks = packs.num
		shared_c.StrList_Free(packs)

		if npacks:

			return True



	return False

def FS_ListMods()->shared.strlist_t: #(returns strlist_t)

	"""
	strlist_t list;
	"""

	lst = shared.strlist_t()
	shared_c.StrList_Init(lst, 0)

	for search in fs_rawPath:

		"""
		strlist_t dirchildren;
		const char *path;
		char searchpath[MAX_OSPATH];
		size_t splen;
		int i;
		"""

		splen = len(search.path)
		if not splen:

			continue


		# make sure this Raw path ends with a '/' otherwise FS_ListFiles will open its parent dir
		if search.path[splen - 1] != '/':

			searchpath = "{}/*".format(search.path)
			path = searchpath

		else:

			path = search.path


		dirchildren = FS_ListFiles(path, 0, 0)

		# iterate over the children of this Raw path (unless we've already got enough mods)
		i = 0
		while i < dirchildren.num and lst.num < MAX_MODS:

			if not HasValidPack(dirchildren.data[i]):

				i += 1
				continue


			modname = dirchildren.data[i].rfind('/')
			if modname == -1:

				i += 1
				continue


			modname = dirchildren.data[i][modname + 1:]

			if not shared.StrList_Contains(lst, modname):

				shared_c.StrList_Append(lst, modname)

			i += 1


		shared_c.StrList_Free(dirchildren)


	if lst.num > 1:

		lst.data[:lst.num] = sorted(lst.data[:lst.num], key=Q_sort_modcmp) #qsort(list.data, list.num, sizeof(char *), Q_sort_modcmp);


	return lst

"""
 * Directory listing.
"""
def FS_Dir_f(): #void

	"""
	const char *path, *wildcard;
	"""

	wildcard = cmdparser.Cmd_Argv(1) if (cmdparser.Cmd_Argc() > 1) else "*.*"

	path = FS_NextPath(None)
	while path is not None:

		"""
		strlist_t dirs;
		char findname[MAX_OSPATH];
		int i;
		"""

		findname = "{}/{}".format(path, wildcard)

		clientserver.Com_Printf("Directory of '%s'.\n", findname)
		clientserver.Com_Printf("----\n")

		dirs = FS_ListFiles(findname, 0, 0)

		for i in range(dirs.num):

			lastsep = dirs.data[i].rfind('/')

			clientserver.Com_Printf("%s\n",
				dirs.data[i][lastsep + 1:] if lastsep != -1 else dirs.data[i])


		shared_c.StrList_Free(dirs)

		clientserver.Com_Printf("\n")

		path = FS_NextPath(path)

# --------

"""
 * This function returns true if a real file (e.g. not something
 * in a pak, something in the file system itself) exists in the
 * current gamedir.
"""
def FS_FileInGamedir(file: str)->bool: #const char * (returns qboolean)

	"""
	const char *path;
	"""

	# now run through the search paths
	path = None

	while 1:

		"""
		char name[MAX_OSPATH];
		FILE *fd;
		"""

		path = FS_NextPath(path)

		if path is None:

			return False     # couldn't find one anywhere


		name = "{}/{}".format(path, file)

		fd = Q_fopen(name, "rb")
		if fd is not None:

			fd.close()
			return True



	return False

"""
 * This function loads the given .pak / .pk3 File from the
 * fs_gamedir. There's no need to load from other dirs since
 * fs_gamedir is the only dir written to at runtime.
"""
def FS_AddPAKFromGamedir(pak: str)->bool: #const char * (returns qboolean)

	"""
	char path[MAX_OSPATH];
	"""

	path = "{}/{}".format(fs_gamedir, pak)

	# Check of the file really exists.
	fd = Q_fopen(path, "rb")
	if fd is None:

		assert fd is not None, "FS_AddPAKfromGamedir() called with nonexisting file"

	else:

		fd.close()


	# Depending on filetype we must load it as .pak or .pk3.
	for i in range(len(fs_packtypes)):

		# Not the current filetype, next one please.
		if not pak.endswith(fs_packtypes[i].suffix):

			continue


		pakfile = None

		if fs_packtypes[i].format == fsPackFormat_t.PAK:
			pakfile = FS_LoadPAK(path)
		elif fs_packtypes[i].format == fsPackFormat_t.PK3:
			pakfile = FS_LoadPK3(path)

		if pakfile is None:

			# Couldn't load it.
			return False

		else:

			FS_SortPack(pakfile)

			# Add it.
			search = fsSearchPath_t()
			search.pack = pakfile
			fs_searchPaths.insert(0, search) #search->next = fs_searchPaths; fs_searchPaths = search;

			return True



	# Apparently we didn't load anything.
	return False

def FS_GetNextRawPath(lastRawPath: str)->str: #const char * (returns const char *)

	assert len(fs_rawPath) > 0, "Don't call this if before FS_InitFilesystem()"

	if lastRawPath is None:

		return fs_rawPath[0].path


	for k in range(len(fs_rawPath)):

		if fs_rawPath[k].path == lastRawPath:

			return fs_rawPath[k + 1].path if (k + 1 < len(fs_rawPath)) else None



	return None

def FS_AddDirToSearchPath(dir: str, create: bool): #char *, qboolean

	global fs_gamedir

	"""
	char *file;
	char path[MAX_OSPATH];
	char *tmp;
	int i, j, k;
	fsPack_t *pack = NULL;
	fsSearchPath_t *search;
	qboolean nextpak;
	size_t len = strlen(dir);
	"""

	# The directory must not end with an /. It would
	# f*ck up the logic in other parts of the game...
	if dir[-1:] == '/' or dir[-1:] == '\\':

		dir = dir[:-1]


	# Set the current directory as game directory. This
	# is somewhat fragile since the game directory MUST
	# be the last directory added to the search path.
	fs_gamedir = dir[:shared.MAX_OSPATH - 1]

	if create:

		FS_CreatePath(fs_gamedir)


	# Add the directory itself.
	search = fsSearchPath_t()
	search.path = dir[:shared.MAX_OSPATH - 1]
	fs_searchPaths.insert(0, search)

	# The archives, in the order Quake II adds them (q2data.filesystem): the
	# numbered paks first (official data, marked protected: never offered for
	# download), then every other archive in the order the directory lists them.
	for spec in q2fs.game_directory_archives(dir):

		if spec.reader is q2pak.PakArchive:
			pack = FS_LoadPAK(spec.path)
		else:
			pack = FS_LoadPK3(spec.path)

		if pack is None:

			continue

		pack.isProtectedPak = spec.protected
		FS_SortPack(pack)

		search = fsSearchPath_t()
		search.pack = pack
		fs_searchPaths.insert(0, search)

def FS_BuildGenericSearchPath(): #void

	global fs_baseSearchPaths

	# We may not use the va() function from shared.c
	# since its buffersize is 1024 while most OS have
	# a maximum path size of 4096...
	#char path[MAX_OSPATH];

	for search in fs_rawPath:

		path = "{}/{}".format(search.path, common_h.BASEDIRNAME)
		FS_AddDirToSearchPath(path, search.create)


	# Until here we've added the generic directories to the
	# search path. Save the current head node so we can
	# distinguish generic and specialized directories.
	fs_baseSearchPaths = len(fs_searchPaths)

	# We need to create the game directory.
	system.Sys_Mkdir(fs_gamedir)

	# We need to create the screenshot directory since the
	# render dll doesn't link the filesystem stuff.
	path = "{}/scrnshot".format(fs_gamedir)
	system.Sys_Mkdir(path)

# filesystem.c is used by the client and the server,
# it includes common.h only. Not the client not the
# server header. The game reset logic messes with
# client state, so we need some forwar declarations
# here.
#ifndef DEDICATED_ONLY
# Variables
#extern qboolean menu_startdemoloop;

# Functions
#void CL_WriteConfiguration(void);
#endif

def FS_BuildGameSpecificSearchPath(dir: str): #const char *

	global fs_gamedir

	from client import cl_main
	from client.menu import menu	# Q2PORT: imported here, the client imports the filesystem

	# We may not use the va() function from shared.c
	# since its buffersize is 1024 while most OS have
	# a maximum path size of 4096...
	"""
	char path[MAX_OSPATH] = {0};
	int i;
	fsRawPath_t *search;
	"""

	#ifndef DEDICATED_ONLY
	# Write the config. Otherwise changes made by the
	# current mod are lost.
	cl_main.CL_WriteConfiguration()
	#endif

	# empty string means baseq2
	if dir == "":

		dir = common_h.BASEDIRNAME


	# This is against PEBCAK. The user may give us paths like
	# xatrix/ or even /home/stupid/quake2/xatrix.
	if dir == "." or ".." in dir or "/" in dir or "\\" in dir:

		clientserver.Com_Printf("Gamedir should be a single filename, not a path.\n")
		return


	# We may already have specialised directories in our search
	# path. This can happen if the server changes the mod. Let's
	# remove them.
	FS_FreeSearchPaths(0, len(fs_searchPaths) - fs_baseSearchPaths)

	# Close open files for game dir.
	for i in range(MAX_HANDLES):

		if dir in fs_handles[i].name and fs_handles[i].file is not None:

			FS_FCloseFile(i)	# (fileHandle_t is i + 1; i closes the handle before, as in Yamagi)



	# Enforce a renderer and sound backend restart to
	# purge all internal caches. This is rather hacky
	# but Quake II doesn't have a better mechanism...
	if (frame.dedicated is not None) and (frame.dedicated.value != 1):

		cmdparser.Cbuf_AddText("vid_restart\nsnd_restart\n")


	# The game was reset to baseq2. Nothing to do here.
	if shared_c.Q_stricmp(dir, common_h.BASEDIRNAME) == 0:
		cvar.Cvar_FullSet("gamedir", "", shared.CVAR_SERVERINFO | shared.CVAR_NOSET)
		cvar.Cvar_FullSet("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)

		# fs_gamedir must be reset to the last
		# dir of the generic search path.
		path = "{}/{}".format(fs_rawPath[0].path, common_h.BASEDIRNAME)
		fs_gamedir = path[:shared.MAX_OSPATH - 1]
	else:
		cvar.Cvar_FullSet("gamedir", dir, shared.CVAR_SERVERINFO | shared.CVAR_NOSET)

		for search in fs_rawPath:
			path = "{}/{}".format(search.path, dir)
			FS_AddDirToSearchPath(path, search.create)



	# Create the game directory.
	system.Sys_Mkdir(fs_gamedir)

	# We need to create the screenshot directory since the
	# render dll doesn't link the filesystem stuff.
	path = "{}/scrnshot".format(fs_gamedir)
	system.Sys_Mkdir(path)

	# the gamedir has changed, so read in the corresponding configs
	frame.Qcommon_ExecConfigs(False)

	#ifndef DEDICATED_ONLY
	# This function is called whenever the game cvar changes =>
	# the player wants to switch to another mod. In that case the
	# list of music tracks needs to be loaded again (=> tracks
	# are possibly from the new mod dir)
	from client.sound import ogg # Q2PORT: lazy import, common/ and client/ would cycle at import time
	ogg.OGG_InitTrackList()

	# ...and the current list of maps in the "start network server" menu is
	# cleared so that it will be re-initialized when the menu is accessed
	menu.CleanCachedMapsList()

	# Start the demoloop, if requested. This is kind of hacky: Normaly the
	# demo loop would be started by the menu, after changeing the 'game'
	# cvar. However, the demo loop is implemented by aliases. Since the
	# game isn't changed right after the cvar is set (but when the control
	# flow enters this function) the aliases evaulate to the wrong game.
	# Work around that by injection the demo loop into the command buffer
	# here, right after the game was changed. Do it only when the game was
	# changed though the menu, otherwise we might break into the demo loop
	# after we've received a latched cvar from the server.
	if menu.menu_startdemoloop:

		cmdparser.Cbuf_AddText("d1\n")
		menu.menu_startdemoloop = False

	#endif

# returns the filename used to open f, but (if opened from pack) in correct case
# returns NULL if f is no valid handle
def FS_GetFilenameForHandle(f: int)->str: #fileHandle_t (returns const char *)

	fsh = FS_GetFileByHandle(f)
	if fsh is not None:

		return fsh.name

	return None

# --------

def FS_AddDirToRawPath(rawdir: str, create: bool, required: bool): #const char *, qboolean, qboolean

	"""
	char dir[MAX_OSPATH] = {0};
	"""

	# Get the realpath.
	ok, dir = system.Sys_Realpath(rawdir)
	if not ok:

		if required:

			clientserver.Com_Error(shared.ERR_FATAL, "Couldn't add required directory %s to search path\n", rawdir)


		return


	# Convert backslashes to forward slashes.
	dir = dir.replace('\\', '/') #Q_replacebackslash(dir);

	# Make sure that the dir doesn't end with a slash.
	while len(dir) > 1 and dir[-1] == '/':

		dir = dir[:-1]


	# Bail out if the dir was already added.
	for search in fs_rawPath:

		if search.path == dir:

			return



	# Add the directory.
	search = fsRawPath_t()
	search.path = dir[:shared.MAX_OSPATH - 1]
	search.create = create
	fs_rawPath.insert(0, search) #search->next = fs_rawPath; fs_rawPath = search;

def FS_BuildRawPath(): #void

	# Add homedir, MUST be the last dir! Required,
	# otherwise the config cannot be written.
	if not frame.is_portable:
		homedir = system.Sys_GetHomeDir()

		if homedir is not None:
			FS_AddDirToRawPath(homedir, True, True)



	# Add binary dir. Required, because the renderer
	# libraries are loaded from it.
	binarydir = misc.Sys_GetBinaryDir()

	if binarydir != "":

		FS_AddDirToRawPath(binarydir, False, True)


	# Add data dir. Required, when the user gives us
	# a data dir he expects it in a working state.
	FS_AddDirToRawPath(datadir, False, True)

	# Add SYSTEMDIR. Optional, the user may have a
	# binary compiled with SYSTEMWIDE (installed from
	# packages), but no systemwide game data.
	#ifdef SYSTEMWIDE
	#FS_AddDirToRawPath(SYSTEMDIR, false, false);
	#endif

	# The CD must be the last directory of the path,
	# otherwise we cannot be sure that the game won't
	# stream the videos from the CD. Required, if the
	# user sets a CD path, he expects data getting
	# read from the CD.
	if fs_cddir.string != "":
		FS_AddDirToRawPath(fs_cddir.string, False, True)

# --------

def FS_InitFilesystem(): #void

	global fs_basedir, fs_cddir, fs_gamedirvar, fs_debug, datadir

	# Register FS commands.
	cmdparser.Cmd_AddCommand("path", FS_Path_f)
	cmdparser.Cmd_AddCommand("link", FS_Link_f)
	cmdparser.Cmd_AddCommand("dir", FS_Dir_f)

	# Register cvars
	fs_basedir = cvar.Cvar_Get("basedir", ".", shared.CVAR_NOSET)
	fs_cddir = cvar.Cvar_Get("cddir", "", shared.CVAR_NOSET)
	fs_gamedirvar = cvar.Cvar_Get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)
	fs_debug = cvar.Cvar_Get("fs_debug", "0", 0)

	# Deprecation warning, can be removed at a later time.
	if fs_basedir.string != ".":

		clientserver.Com_Printf("+set basedir is deprecated, use -datadir instead\n")
		datadir = fs_basedir.string[:shared.MAX_OSPATH - 1]

	elif len(datadir) == 0:

		datadir = "."


	#ifdef _WIN32
	# setup minizip for Unicode compatibility
	#endif

	# Build search path
	FS_BuildRawPath()
	FS_BuildGenericSearchPath()

	if fs_gamedirvar.string != "":

		FS_BuildGameSpecificSearchPath(fs_gamedirvar.string)

	#ifndef DEDICATED_ONLY
	else:

		# no mod, but we still need to get the list of OGG tracks for background music
		from client.sound import ogg # Q2PORT: lazy import, common/ and client/ would cycle at import time
		ogg.OGG_InitTrackList()

	#endif

	# Debug output
	clientserver.Com_Printf("Using '%s' for writing.\n", fs_gamedir)

def FS_ShutdownFilesystem(): #void

	global fs_baseSearchPaths

	FS_FreeSearchPaths(0, len(fs_searchPaths))
	FS_FreeRawPaths(0, len(fs_rawPath))

	fs_baseSearchPaths = 0

