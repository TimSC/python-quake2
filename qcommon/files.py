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
import os
from qcommon import cmd, common, qcommon, cvar, qfiles
from game import q_shared
from linux import q_shlinux, cd_linux
"""
#include "qcommon.h"

// define this to dissalow any data but the demo pak file
//#define	NO_ADDONS

// if a packfile directory differs from this, it is assumed to be hacked
// Full version
#define	PAK0_CHECKSUM	0x40e614e0
// Demo
//#define	PAK0_CHECKSUM	0xb2c6d7ea
// OEM
//#define	PAK0_CHECKSUM	0x78e135c

/*
=============================================================================

QUAKE FILESYSTEM

=============================================================================
*/


//
// in memory
//

typedef struct
{
	char	name[MAX_QPATH];
	int		filepos, filelen;
} packfile_t;

"""
class pack_t(object):
	def __init__(self):
		
		filename = None #char	[MAX_OSPATH]
		handle = None #FILE	*
		numfiles = None #int		
		files = None #packfile_t	*

fs_gamedir = None #char[MAX_OSPATH];
fs_basedir = None #cvar_t	*;
fs_cddir = None #cvar_t	*;
fs_gamedirvar = None # None cvar_t	*;
"""

typedef struct filelink_s
{
	struct filelink_s	*next;
	char	*from;
	int		fromlength;
	char	*to;
} filelink_t;

filelink_t	*fs_links;
"""
class filelink_t(object):

	def __init__(self, from_path, to_path):
		self.from_path = from_path
		self.fromlength = len(from_path)
		self.to_path = to_path

	def __repr__(self):
		return "filelink_t({} -> {})".format(self.from_path, self.to_path)

fs_links = []
class searchpath_t(object):

	def __init__(self):

		self.filename = None #char	[MAX_OSPATH];
		self.pack = None #pack_t	*;		# only one of filename / pack will be used

	def __repr__(self):
		return "searchpath_t ({} {})".format(self.filename, self.pack is not None)

fs_searchpaths = [] #searchpath_t	*;
fs_base_searchpaths = [] #searchpath_t	*x;	# without gamedirs
"""

/*

All of Quake's data access is through a hierchal file system, but the contents of the file system can be transparently merged from several sources.

The "base directory" is the path to the directory holding the quake.exe and all game directories.  The sys_* files pass this to host_init in quakeparms_t->basedir.  This can be overridden with the "-basedir" command line parm to allow code debugging in a different directory.  The base directory is
only used during filesystem initialization.

The "game directory" is the first tree on the search path and directory that all generated files (savegames, screenshots, demos, config files) will be saved to.  This can be overridden with the "-game" command line parameter.  The game directory can never be changed while quake is executing.  This is a precacution against having a malicious server instruct clients to write files over areas they shouldn't.

*/


/*
================
FS_filelength
================
"""
def FS_filelength (f): #FILE * (returns int)

	#int		pos;
	#int		end;

	pos = f.tell ()
	f.seek (0, 2)
	end = f.tell ()
	f.seek (pos, 0)

	return end

"""
============
FS_CreatePath

Creates any directories needed to store the given filename
============
"""
def FS_CreatePath (path): #char *
	if not path:
		return

	directory = os.path.dirname(path)
	if not directory:
		return
	os.makedirs(directory, exist_ok=True)

"""
==============
FS_FCloseFile

For some reason, other dll's can't just cal fclose()
on files returned by FS_FOpenFile...
==============
"""
def FS_FCloseFile (f): #FILE *
	if f is None:
		return
	f.close()


# RAFAEL
def Developer_searchpath (who): #int (returns int)
	for search in fs_searchpaths:
		filename = search.filename or ""
		if "xatrix" in filename:
			return 1
		if "rogue" in filename:
			return 2
	return 0


"""
===========
FS_FOpenFile

Finds the file in the search path.
returns filesize and an open FILE *
Used for streaming data out of either a pak file or
a seperate file.
===========
"""
#int file_from_pak = 0;
#ifndef NO_ADDONS
def FS_FOpenFile (filename): #char *

	"""
	searchpath_t	*search;
	char			netpath[MAX_OSPATH];
	pack_t			*pak;
	int				i;
	filelink_t		*link;
	"""

	file_from_pak = 0
	handle = None

	# check for links first
	for link in fs_links:
		if filename.startswith(link.from_path):
			netpath = "{}{}".format(link.to_path, filename[link.fromlength:])
			try:
				handle = open(netpath, "rb")
			except FileNotFoundError:
				return -1, None
			common.Com_DPrintf ("link file: {}\n".format(netpath))
			return FS_filelength(handle), handle

	#
	# search through the path, one element at a time
	#
	for search in fs_searchpaths:
	
		# is the element a pak file?
		if search.pack is not None:
		
			# look through all the pak file elements
			pak = search.pack
			for i in range (pak.numfiles):

				if not q_shared.Q_strcasecmp (pak.files[i].name, filename):
					# found it!
					file_from_pak = 1;
					common.Com_DPrintf ("PackFile: {} : {}\n".format(pak.filename, filename))
					# open a new file on the pakfile
					try:
						handle = open (pak.filename, "rb")
					except FileNotFoundError:
						common.Com_Error (q_shared.ERR_FATAL, "Couldn't reopen {}".format(pak.filename))
					handle.seek(pak.files[i].filepos)
					return pak.files[i].filelen, handle
					
		else:
			
			# check a file in the directory tree
			netpath = os.path.join(search.filename, filename)
			
			try:
				handle = open (netpath, "rb")
			except FileNotFoundError:
				continue
			
			common.Com_DPrintf ("FindFile: {}\n".format(netpath))

			return FS_filelength (handle), handle
	
	common.Com_DPrintf ("FindFile: can't find {}\n".format(filename))
	
	return -1, None

"""
#else

// this is just for demos to prevent add on hacking

int FS_FOpenFile (char *filename, FILE **file)
{
	searchpath_t	*search;
	char			netpath[MAX_OSPATH];
	pack_t			*pak;
	int				i;

	file_from_pak = 0;

	// get config from directory, everything else from pak
	if (!strcmp(filename, "config.cfg") || !strncmp(filename, "players/", 8))
	{
		Com_sprintf (netpath, sizeof(netpath), "%s/%s",FS_Gamedir(), filename);
		
		*file = fopen (netpath, "rb");
		if (!*file)
			return -1;
		
		Com_DPrintf ("FindFile: %s\n",netpath);

		return FS_filelength (*file);
	}

	for (search = fs_searchpaths ; search ; search = search->next)
		if (search->pack)
			break;
	if (!search)
	{
		*file = NULL;
		return -1;
	}

	pak = search->pack;
	for (i=0 ; i<pak->numfiles ; i++)
		if (!Q_strcasecmp (pak->files[i].name, filename))
		{	// found it!
			file_from_pak = 1;
			Com_DPrintf ("PackFile: %s : %s\n",pak->filename, filename);
		// open a new file on the pakfile
			*file = fopen (pak->filename, "rb");
			if (!*file)
				Com_Error (ERR_FATAL, "Couldn't reopen %s", pak->filename);	
			fseek (*file, pak->files[i].filepos, SEEK_SET);
			return pak->files[i].filelen;
		}
	
	Com_DPrintf ("FindFile: can't find %s\n", filename);
	
	*file = NULL;
	return -1;
}

#endif


/*
=================
FS_ReadFile

Properly handles partial reads
=================
*/
void CDAudio_Stop(void);
"""
MAX_READ = 0x10000		# read in blocks of 64k

def FS_Read (length, f): #int, FILE * (out void *)

	
	"""
	int		block, remaining;
	int		read;
	byte	*buf;
	int		tries;

	buf = (byte *)buffer;
	"""
	buf = bytearray()

	# read in chunks for progress bar
	remaining = length
	tries = 0
	while remaining:
	
		block = remaining
		if block > MAX_READ:
			block = MAX_READ
	
		try:
			read = f.read (block)
			if len(read) == 0:
			
				# we might have been trying to read from a CD
				if tries==0:
				
					tries = 1
					cd_linux.CDAudio_Stop()
				
				else:
					common.Com_Error (q_shared.ERR_FATAL, "FS_Read: 0 bytes read");
		

		except Exception as err:
			print (err)
			common.Com_Error (q_shared.ERR_FATAL, "FS_Read: -1 bytes read");

		# do some progress bar thing here...

		remaining -= len(read)
		buf += read
	
	return buf

"""
============
FS_LoadFile

Filename are reletive to the quake search path
a null buffer will just return the file length without loading
============
"""
def FS_LoadFile (path): #char * (returns int)

	"""
	FILE	*h;
	byte	*buf;
	int		len;
"""
	# look for it in the filesystem or pack files
	length, handle = FS_FOpenFile (path);
	if handle is None:
		return -1, None

	return length, handle.read(length)

"""
=============
FS_FreeFile
=============
"""
def FS_FreeFile (buff): #void *
	return

"""
=================
FS_LoadPackFile

Takes an explicit (not game tree related) path to a pak file.

Loads the header and directory, adding the files at the beginning
of the list so they override previous pack files.
=================
"""
def FS_LoadPackFile (packfile): # char * (returns pack_t *)

	"""
	dpackheader_t	header;
	int				i;
	packfile_t		*newfiles;
	int				numpackfiles;
	pack_t			*pack;
	FILE			*packhandle;
	dpackfile_t		info[MAX_FILES_IN_PACK];
	unsigned		checksum;
	"""

	try:
		packhandle = open(packfile, "rb")
	except FileNotFoundError:
		return None

	header = qfiles.dpackheader_t()
	header.read(packhandle)

	numpackfiles = header.dirlen // 64;

	if numpackfiles > qfiles.MAX_FILES_IN_PACK:
		common.Com_Error (ERR_FATAL, "{} has {} files".format(packfile, numpackfiles))

	newfiles = []

	packhandle.seek(header.dirofs);

	# crc the directory to check for modifications
	#checksum = Com_BlockChecksum ((void *)info, header.dirlen);

	##ifdef NO_ADDONS
	#if (checksum != PAK0_CHECKSUM)
	#	return NULL;
	##endif

	# parse the directory
	for i in range(numpackfiles):
	
		newfile = qfiles.dpackfile_t()
		newfile.read(packhandle)
		newfiles.append(newfile)

	pack = pack_t()
	pack.filename = packfile
	pack.handle = packhandle
	pack.numfiles = numpackfiles
	pack.files = newfiles
	
	common.Com_Printf ("Added packfile {} ({} files)\n".format(packfile, numpackfiles))
	return pack;

"""
================
FS_AddGameDirectory

Sets fs_gamedir, adds the directory to the head of the path,
then loads and adds pak1.pak pak2.pak ... 
================
"""
def FS_AddGameDirectory (folder): #char *

	global fs_gamedir, fs_searchpaths

	"""
	int				i;
	searchpath_t	*search;
	pack_t			*pak;
	char			pakfile[MAX_OSPATH];
	"""

	fs_gamedir = folder

	#
	# add the directory to the search path
	#
	search = searchpath_t();
	search.filename = folder
	fs_searchpaths.insert(0, search)

	#
	# add any pak files in the format pak0.pak pak1.pak, ...
	#
	for i in range(10):
	
		pakfile = os.path.join(folder, "pak{}.pak".format(i))
		pak = FS_LoadPackFile (pakfile)
		if pak is None:
			continue
		search = searchpath_t()
		search.pack = pak
		fs_searchpaths.insert(0, search)
	
"""

/*
============
FS_Gamedir

Called to find where to write a file (demos, savegames, etc)
============
"""
def FS_Gamedir (): #(returns char *)

	global fs_gamedir

	if fs_gamedir is not None:
		return fs_gamedir
	else:
		return qcommon.BASEDIRNAME


"""
=============
FS_ExecAutoexec
=============
"""
def FS_ExecAutoexec ():

	#char *dir;
	#char name [MAX_QPATH];

	di = cvar.Cvar_VariableString("gamedir")
	if di is not None:
		name = os.path.join(fs_basedir.string, di, "autoexec.cfg")
	else:
		name = os.path.join(fs_basedir.string, qcommon.BASEDIRNAME, "autoexec.cfg")
	canhave = q_shared.SFF_SUBDIR | q_shared.SFF_HIDDEN | q_shared.SFF_SYSTEM
	if q_shlinux.Sys_FindFirst(name, 0, canhave):
		cmd.Cbuf_AddText ("exec autoexec.cfg\n");
	q_shlinux.Sys_FindClose()

"""
================
FS_SetGamedir

Sets the gamedir and path to a different directory.
================
"""
def FS_SetGamedir (folder): #char *

	global fs_searchpaths, fs_gamedir

	if folder.find("..") != -1 or folder.find("/") != -1 \
		or folder.find("\\") != -1 or folder.find(":") != -1:
	
		common.Com_Printf ("Gamedir should be a single filename, not a path\n")
		return
	
	#
	# free up any current game dir info
	#
	fs_searchpaths = fs_base_searchpaths[:]
	
	#
	# flush all data, so it will be forced to reload
	#
	if common.dedicated is not None and not common.dedicated.value:
		cmd.Cbuf_AddText ("vid_restart\nsnd_restart\n")

	fs_gamedir = os.path.join(fs_basedir.string, folder)

	if folder == qcommon.BASEDIRNAME or len(folder) == 0:
	
		cvar.Cvar_FullSet ("gamedir", "", q_shared.CVAR_SERVERINFO|q_shared.CVAR_NOSET)
		cvar.Cvar_FullSet ("game", "", q_shared.CVAR_LATCH|q_shared.CVAR_SERVERINFO)
	
	else:	
		cvar.Cvar_FullSet ("gamedir", folder, q_shared.CVAR_SERVERINFO|q_shared.CVAR_NOSET)
		if len(fs_cddir.string) > 0:
			FS_AddGameDirectory (os.path.join(fs_cddir.string, folder) )
		FS_AddGameDirectory (os.path.join(fs_basedir.string, folder) )
	

"""
================
FS_Link_f

Creates a filelink_t
================
"""
def FS_Link_f ():

	global fs_links

	if cmd.Cmd_Argc() != 3:
		common.Com_Printf("USAGE: link <from> <to>\n")
		return

	from_path = cmd.Cmd_Argv(1)
	to_path = cmd.Cmd_Argv(2)

	for link in list(fs_links):
		if link.from_path == from_path:
			if not to_path:
				fs_links.remove(link)
			else:
				link.to_path = to_path
			return

	if to_path:
		fs_links.append(filelink_t(from_path, to_path))
"""
	filelink_t	*l, **prev;

	if (Cmd_Argc() != 3)
	{
		Com_Printf ("USAGE: link <from> <to>\n");
		return;
	}

	// see if the link already exists
	prev = &fs_links;
	for (l=fs_links ; l ; l=l->next)
	{
		if (!strcmp (l->from, Cmd_Argv(1)))
		{
			Z_Free (l->to);
			if (!strlen(Cmd_Argv(2)))
			{	// delete it
				*prev = l->next;
				Z_Free (l->from);
				Z_Free (l);
				return;
			}
			l->to = CopyString (Cmd_Argv(2));
			return;
		}
		prev = &l->next;
	}

	// create a new link
	l = Z_Malloc(sizeof(*l));
	l->next = fs_links;
	fs_links = l;
	l->from = CopyString(Cmd_Argv(1));
	l->fromlength = strlen(l->from);
	l->to = CopyString(Cmd_Argv(2));
}

/*
** FS_ListFiles
*/
"""
def FS_ListFiles( findname, musthave, canthave ): #char *, unsigned, unsigned (returns char **)
	
	
	#char *s;
	#nfiles = 0; #int
	out = [] #char ** = 0;

	"""
	s = Sys_FindFirst( findname, musthave, canthave )
	while s is not None:
	
		if ( s[strlen(s)-1] != '.' )
			nfiles++;
		s = Sys_FindNext( musthave, canthave );
	
	Sys_FindClose ();

	if ( !nfiles )
		return NULL;

	nfiles++; // add space for a guard
	*numfiles = nfiles;

	list = malloc( sizeof( char * ) * nfiles );
	memset( list, 0, sizeof( char * ) * nfiles );
	"""

	s = q_shlinux.Sys_FindFirst( findname, musthave, canthave )
	nfiles = 0
	while s is not None:

		if s[-1] != '.':
		
			out.append(s)
			#ifdef _WIN32
			##strlwr( list[nfiles] );
			#endif
			nfiles+=1
		
		s = q_shlinux.Sys_FindNext( musthave, canthave )
	
	q_shlinux.Sys_FindClose ()

	if not out:
		return None
	return out



"""
** FS_Dir_f
"""
def FS_Dir_f():
	
	"""
	char	findname[1024];
	char	**dirnames;
	int		ndirs;
	"""
	findname = None
	path = None #char	*
	wildcard = "*.*" #char[1024]
 
	if cmd.Cmd_Argc() != 1:
	
		wildcard = cmd.Cmd_Argv( 1 )

	path = FS_NextPath( path )
	while path != None:

		findname = os.path.join(path, wildcard)
		findname = findname.replace("\\", "/")

		common.Com_Printf( "Directory of {}\n".format(findname))
		common.Com_Printf( "----\n" )

		dirnames = FS_ListFiles( findname, 0, 0 )		
		if dirnames is not None:
			
			for name in dirnames:
			
				if name.rfind('/') != -1:
					common.Com_Printf( "{}\n".format(name[name.rfind('/')+1:]))
				else:
					common.Com_Printf( "{}\n".format(name) )

		common.Com_Printf( "\n" );
		
		path = FS_NextPath( path )

"""
============
FS_Path_f

============
"""
def FS_Path_f ():
	common.Com_Printf("Current search path:\n")
	in_base = True
	for search in fs_searchpaths:
		if in_base and search not in fs_base_searchpaths:
			common.Com_Printf("----------\n")
			in_base = False
		if search.pack is not None:
			common.Com_Printf("{} ({} files)\n".format(search.pack.filename, search.pack.numfiles))
		else:
			common.Com_Printf("{}\n".format(search.filename))

	common.Com_Printf("\nLinks:\n")
	for link in fs_links:
		common.Com_Printf("{} : {}\n".format(link.from_path, link.to_path))

"""
	searchpath_t	*s;
	filelink_t		*l;

	Com_Printf ("Current search path:\n");
	for (s=fs_searchpaths ; s ; s=s->next)
	{
		if (s == fs_base_searchpaths)
			Com_Printf ("----------\n");
		if (s->pack)
			Com_Printf ("%s (%i files)\n", s->pack->filename, s->pack->numfiles);
		else
			Com_Printf ("%s\n", s->filename);
	}

	Com_Printf ("\nLinks:\n");
	for (l=fs_links ; l ; l=l->next)
		Com_Printf ("%s : %s\n", l->from, l->to);
"""

"""
/*
================
FS_NextPath

Allows enumerating all of the directories in the search path
================
"""
def FS_NextPath (prevpath): #char * (returns char *)

	global fs_gamedir, fs_searchpaths

	#searchpath_t	*s;
	#char			*prev;

	if prevpath is None:
		return fs_gamedir

	prev = fs_gamedir

	for s in fs_searchpaths:
	
		if s.pack is not None:
			continue;
		if prevpath == prev and s.filename != prevpath: #Why is this fix neccessary in python code?
			return s.filename
		prev = s.filename

	return None



"""
================
FS_InitFilesystem
================
"""
def FS_InitFilesystem ():

	global fs_gamedir, fs_basedir, fs_cddir, fs_gamedirvar, fs_base_searchpaths

	cmd.Cmd_AddCommand ("path", FS_Path_f)
	cmd.Cmd_AddCommand ("link", FS_Link_f)
	cmd.Cmd_AddCommand ("dir", FS_Dir_f )

	#
	# basedir <path>
	# allows the game to run from outside the data tree
	#
	fs_basedir = cvar.Cvar_Get ("basedir", ".", q_shared.CVAR_NOSET)

	#
	# cddir <path>
	# Logically concatenates the cddir after the basedir for 
	# allows the game to run from outside the data tree
	#
	fs_cddir = cvar.Cvar_Get ("cddir", "", q_shared.CVAR_NOSET)
	if len(fs_cddir.string) > 0:
		FS_AddGameDirectory (os.path.join(fs_cddir.string, qcommon.BASEDIRNAME) )

	#
	# start up with baseq2 by default
	#
	FS_AddGameDirectory (os.path.join(fs_basedir.string, qcommon.BASEDIRNAME) )

	# any set gamedirs will be freed up to here
	fs_base_searchpaths = fs_searchpaths[:]

	# check for game override
	fs_gamedirvar = cvar.Cvar_Get ("game", "", q_shared.CVAR_LATCH|q_shared.CVAR_SERVERINFO)
	if len(fs_gamedirvar.string) > 0:
		FS_SetGamedir (fs_gamedirvar.string)

