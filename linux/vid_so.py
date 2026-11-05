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


// Main windowed and fullscreen graphics interface module. This module
// is used for both the software and OpenGL rendering versions of the
// Quake refresh engine.
"""
from __future__ import annotations

import os
from qcommon import cvar, common, cmd, files
from client import snd_dma, cl_main, ref, cl_input, keys, client
from linux import q_shlinux
from game import q_shared
"""
#include <assert.h>
#include <dlfcn.h> // ELF dl loader
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>

#include "../client/client.h"

#include "../linux/rw_linux.h"
"""
# Structure containing functions exported from refresh DLL
re = ref.refexport_t()

# Console variables that we need to access from this module
vid_gamma = None       #cvar_t		*
vid_ref = None         #cvar_t		*, Name of Refresh DLL loaded
vid_xpos = None        #cvar_t		*, X coordinate of window position
vid_ypos = None        #cvar_t		*, Y coordinate of window position
vid_fullscreen = None  #cvar_t		*

class viddef_t(object):

	def __init__(self):
		self.width, self.height = 800, 600 #unsigned, coordinates from main game

# Global variables used internally by this module
viddef = viddef_t() # global video state; used by other modules
#void		*reflib_library;		// Handle to refresh DLL 

reflib_active = 0 #qboolean
"""
#define VID_NUM_MODES ( sizeof( vid_modes ) / sizeof( vid_modes[0] ) )

const char so_file[] = "/etc/quake2.conf";

"""
#* KEYBOARD **************************************************************

#void Do_Key_Event(int key, qboolean down);

KBD_Update_fp = None #void (*)(void)
KBD_Init_fp = None #void (*)(Key_Event_fp_t fp)
KBD_Close_fp = None #void (*)(void)

#* MOUSE *****************************************************************

class in_state_t(object): # rw_linux.h

	def __init__(self):

		# Pointers to functions back in client, set by vid_so
		self.IN_CenterView_fp = None #void (*)(void)
		self.Key_Event_fp = None #Key_Event_fp_t
		self.viewangles = None #vec_t *
		self.in_strafe_state = None #int *, the in_strafe kbutton_t here, its state is read

in_state = in_state_t() #in_state_t

RW_IN_Init_fp = None #void (*)(in_state_t *in_state_p)
RW_IN_Shutdown_fp = None #void (*)(void)
RW_IN_Activate_fp = None #void (*)(qboolean active)
RW_IN_Commands_fp = None #void (*)(void)
RW_IN_Move_fp = None #void (*)(usercmd_t *cmd)
RW_IN_Frame_fp = None #void (*)(void)

#void Real_IN_Init (void);
"""

/*
==========================================================================

DLL GLUE

==========================================================================
*/

#define	MAXPRINTMSG	4096
"""
def VID_Printf (print_level, msg):

	"""
	va_list		argptr;
	char		msg[MAXPRINTMSG];
	static qboolean	inupdate;
	
	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);
	"""
	if print_level == q_shared.PRINT_ALL:
		common.Com_Printf (str(msg))
	else:
		common.Com_DPrintf (str(msg))


def VID_Error (err_level, msg):

	"""
	va_list		argptr;
	char		msg[MAXPRINTMSG];
	static qboolean	inupdate;
	
	va_start (argptr,fmt);
	vsprintf (msg,fmt,argptr);
	va_end (argptr);
	"""
	common.Com_Error (err_level, str(msg))

"""
//==========================================================================

/*
============
VID_Restart_f

Console command to re-start the video mode and refresh DLL. We do this
simply by setting the modified flag for the vid_ref variable, which will
cause the entire video mode and refresh DLL to be reset on the next frame.
============
"""
def VID_Restart_f ():

	global vid_ref

	vid_ref.modified = True

"""
** VID_GetModeInfo
"""
class vidmode_t(object):

	def __init__(self, description, width, height, mode):

		self.description = description #const char *
		self.width, self.height = width, height #int
		self.mode = mode #int

vid_modes = [ #vidmode_t []
	vidmode_t( "Mode 0: 320x240",   320, 240,   0 ),
	vidmode_t( "Mode 1: 400x300",   400, 300,   1 ),
	vidmode_t( "Mode 2: 512x384",   512, 384,   2 ),
	vidmode_t( "Mode 3: 640x480",   640, 480,   3 ),
	vidmode_t( "Mode 4: 800x600",   800, 600,   4 ),
	vidmode_t( "Mode 5: 960x720",   960, 720,   5 ),
	vidmode_t( "Mode 6: 1024x768",  1024, 768,  6 ),
	vidmode_t( "Mode 7: 1152x864",  1152, 864,  7 ),
	vidmode_t( "Mode 8: 1280x1024",  1280, 1024, 8 ),
	vidmode_t( "Mode 9: 1600x1200", 1600, 1200, 9 ),
	vidmode_t( "Mode 10: 2048x1536", 2048, 1536, 10 ),
]
VID_NUM_MODES = len(vid_modes) # ( sizeof( vid_modes ) / sizeof( vid_modes[0] ) )

def VID_GetModeInfo( mode ): #int *width, int *height, int mode (returns qboolean, width, height)

	if mode < 0 or mode >= VID_NUM_MODES:
		return False, 0, 0

	width  = vid_modes[mode].width
	height = vid_modes[mode].height

	return True, width, height

"""
** VID_NewWindow
"""
def VID_NewWindow ( width, height): #int, int

	viddef.width  = width
	viddef.height = height

def VID_FreeReflib ():

	global KBD_Init_fp, KBD_Update_fp, KBD_Close_fp
	global RW_IN_Init_fp, RW_IN_Shutdown_fp, RW_IN_Activate_fp, RW_IN_Commands_fp, RW_IN_Move_fp, RW_IN_Frame_fp
	global re, reflib_active

	# if (reflib_library), the renderer is a python module that is always loaded
	if KBD_Close_fp is not None:
		KBD_Close_fp()
	if RW_IN_Shutdown_fp is not None:
		RW_IN_Shutdown_fp()
	# dlclose(reflib_library);

	KBD_Init_fp = None
	KBD_Update_fp = None
	KBD_Close_fp = None
	RW_IN_Init_fp = None
	RW_IN_Shutdown_fp = None
	RW_IN_Activate_fp = None
	RW_IN_Commands_fp = None
	RW_IN_Move_fp = None
	RW_IN_Frame_fp = None

	re = ref.refexport_t() # memset (&re, 0, sizeof(re));
	# reflib_library = NULL;
	reflib_active  = False


"""
==============
VID_LoadRefresh
==============
"""
def VID_LoadRefresh(name): #char * (returns qboolean)

	global re, reflib_active
	global RW_IN_Init_fp, RW_IN_Shutdown_fp, RW_IN_Activate_fp, RW_IN_Commands_fp, RW_IN_Move_fp, RW_IN_Frame_fp
	global KBD_Init_fp, KBD_Update_fp, KBD_Close_fp

	ri = ref.refimport_t()
	"""
	GetRefAPI_t	GetRefAPI;
	char	fn[MAX_OSPATH];
	struct stat st;
	extern uid_t saved_euid;
	FILE *fp;
	"""
	
	if reflib_active:
	
		if KBD_Close_fp is not None:
			KBD_Close_fp()
		if RW_IN_Shutdown_fp is not None:
			RW_IN_Shutdown_fp()
		KBD_Close_fp = None
		RW_IN_Shutdown_fp = None
		re.Shutdown()
		VID_FreeReflib ()
	
	common.Com_Printf( "------- Loading {} -------\n".format(name) )
	"""
	//regain root
	seteuid(saved_euid);

	if ((fp = fopen(so_file, "r")) == NULL) {
		Com_Printf( "LoadLibrary(\"%s\") failed: can't open %s (required for location of ref libraries)\n", name, so_file);
		return false;
	}
	fgets(fn, sizeof(fn), fp);
	fclose(fp);
	while (*fn && isspace(fn[strlen(fn) - 1]))
		fn[strlen(fn) - 1] = 0;

	strcat(fn, "/");
	strcat(fn, name);

	// permission checking
	if (strstr(fn, "softx") == NULL) { // softx doesn't require root
		if (stat(fn, &st) == -1) {
			Com_Printf( "LoadLibrary(\"%s\") failed: %s\n", name, strerror(errno));
			return false;
		}
#if 0
		if (st.st_uid != 0) {
			Com_Printf( "LoadLibrary(\"%s\") failed: ref is not owned by root\n", name);
			return false;
		}
		if ((st.st_mode & 0777) & ~0700) {
			Com_Printf( "LoadLibrary(\"%s\") failed: invalid permissions, must be 700 for security considerations\n", name);
			return false;
		}
#endif
	} else {
		// softx requires we give up root now
		setreuid(getuid(), getuid());
		setegid(getgid());
	}

	if ( ( reflib_library = dlopen( fn, RTLD_LAZY | RTLD_GLOBAL ) ) == 0 )
	{
		Com_Printf( "LoadLibrary(\"%s\") failed: %s\n", name , dlerror());
		return false;
	}

  Com_Printf( "LoadLibrary(\"%s\")\n", fn );
	"""
	ri.Cmd_AddCommand = cmd.Cmd_AddCommand
	ri.Cmd_RemoveCommand = cmd.Cmd_RemoveCommand
	ri.Cmd_Argc = cmd.Cmd_Argc
	ri.Cmd_Argv = cmd.Cmd_Argv
	ri.Cmd_ExecuteText = cmd.Cbuf_ExecuteText
	ri.Con_Printf = VID_Printf
	ri.Sys_Error = VID_Error
	ri.FS_LoadFile = files.FS_LoadFile
	ri.FS_FreeFile = files.FS_FreeFile
	ri.FS_Gamedir = files.FS_Gamedir
	ri.Cvar_Get = cvar.Cvar_Get
	ri.Cvar_Set = cvar.Cvar_Set
	ri.Cvar_SetValue = cvar.Cvar_SetValue
	ri.Vid_GetModeInfo = VID_GetModeInfo
	from linux import vid_menu # imported here, vid_menu needs client.menu fully loaded
	ri.Vid_MenuInit = vid_menu.VID_MenuInit
	ri.Vid_NewWindow = VID_NewWindow


	if name == "gl" or True: #Force to gl for python port
		from ref_gl import gl_rmain
		re = gl_rmain.GetRefAPI(ri)

	"""

	if ( ( GetRefAPI = (void *) dlsym( reflib_library, "GetRefAPI" ) ) == 0 )
		Com_Error( ERR_FATAL, "dlsym failed on %s", name );

	re = GetRefAPI( ri );

	if (re.api_version != API_VERSION)
	{
		VID_FreeReflib ();
		Com_Error (ERR_FATAL, "%s has incompatible api_version", name);
	}

	"""
	# Init IN (Mouse)
	in_state.IN_CenterView_fp = cl_input.IN_CenterView
	in_state.Key_Event_fp = Do_Key_Event
	in_state.viewangles = cl_main.cl.viewangles
	in_state.in_strafe_state = cl_input.in_strafe # &in_strafe.state

	# Q2PORT: there is no ref library to dlsym, the RW_IN functions are in gl_glx
	from linux import gl_glx
	RW_IN_Init_fp = gl_glx.RW_IN_Init
	RW_IN_Shutdown_fp = gl_glx.RW_IN_Shutdown
	RW_IN_Activate_fp = gl_glx.RW_IN_Activate
	RW_IN_Commands_fp = gl_glx.RW_IN_Commands
	RW_IN_Move_fp = gl_glx.RW_IN_Move
	RW_IN_Frame_fp = gl_glx.RW_IN_Frame

	Real_IN_Init()

	if re.Init( 0, 0 ) == -1:
	
		re.Shutdown()
		VID_FreeReflib ()
		return False
	
	# Init KBD
	#if 1
	# Q2PORT: the KBD functions are in gl_glx, as dlsym would find them in the ref library
	KBD_Init_fp = gl_glx.KBD_Init
	KBD_Update_fp = gl_glx.KBD_Update
	KBD_Close_fp = gl_glx.KBD_Close
	#endif
	KBD_Init_fp(Do_Key_Event)

	"""

	// give up root now
	setreuid(getuid(), getuid());
	setegid(getgid());

	"""
	common.Com_Printf( "------------------------------------\n")
	reflib_active = True

	return True


"""
============
VID_CheckChanges

This function gets called once just before drawing each frame, and it's sole purpose in life
is to check to see if any of the video mode parameters have changed, and if they have to 
update the rendering DLL and/or video mode to match.
============
"""
def VID_CheckChanges ():

	global vid_ref, vid_fullscreen

	"""
	char name[100];
	cvar_t *sw_mode;
	"""

	if vid_ref.modified:
	
		snd_dma.S_StopAllSounds()
	
	while vid_ref.modified:
	
		#
		# refresh has changed
		#
		vid_ref.modified = False
		vid_fullscreen.modified = True
		cl_main.cl.refresh_prepped = False
		cl_main.cls.disable_screen = True

		name = "ref_{}.so".format(vid_ref.string)

		if not VID_LoadRefresh( name ):
		
			pass
			"""
			if ( strcmp (vid_ref->string, "soft") == 0 ||
				strcmp (vid_ref->string, "softx") == 0 ) {
Com_Printf("Refresh failed\n");
				sw_mode = Cvar_Get( "sw_mode", "0", 0 );
				if (sw_mode->value != 0) {
Com_Printf("Trying mode 0\n");
					Cvar_SetValue("sw_mode", 0);
					if ( !VID_LoadRefresh( name ) )
						Com_Error (ERR_FATAL, "Couldn't fall back to software refresh!");
				} else
					Com_Error (ERR_FATAL, "Couldn't fall back to software refresh!");
			}

			Cvar_Set( "vid_ref", "soft" );

			/*
			** drop the console if we fail to load a refresh
			*/
			if ( cls.key_dest != key_console )
			{
				Con_ToggleConsole_f();
			}
"""
		cl_main.cls.disable_screen = False
	



"""
============
VID_Init
============
"""
def VID_Init ():

	global vid_gamma, vid_ref, vid_xpos, vid_ypos, vid_fullscreen

	# Create the video variables so we know how to start the graphics drivers
	## if DISPLAY is defined, try X
	if os.getenv("DISPLAY") is not None:
		vid_ref = cvar.Cvar_Get ("vid_ref", "softx", q_shared.CVAR_ARCHIVE)
	else:
		vid_ref = cvar.Cvar_Get ("vid_ref", "soft", q_shared.CVAR_ARCHIVE)
	vid_xpos = cvar.Cvar_Get ("vid_xpos", "3", q_shared.CVAR_ARCHIVE)
	vid_ypos = cvar.Cvar_Get ("vid_ypos", "22", q_shared.CVAR_ARCHIVE)
	vid_fullscreen = cvar.Cvar_Get ("vid_fullscreen", "0", q_shared.CVAR_ARCHIVE)
	vid_gamma = cvar.Cvar_Get( "vid_gamma", "1", q_shared.CVAR_ARCHIVE )

	# Add some console commands that we want to handle
	cmd.Cmd_AddCommand ("vid_restart", VID_Restart_f)

	# Disable the 3Dfx splash screen 
	os.environ['FX_GLIDE_NO_SPLASH'] = "0"
	
	# Start the graphics mode and load refresh DLL 
	VID_CheckChanges()


"""
============
VID_Shutdown
============
"""
def VID_Shutdown ():

	global KBD_Close_fp, RW_IN_Shutdown_fp

	if reflib_active:
	
		if KBD_Close_fp is not None:
			KBD_Close_fp()
		if RW_IN_Shutdown_fp is not None:
			RW_IN_Shutdown_fp()
		KBD_Close_fp = None
		RW_IN_Shutdown_fp = None
		re.Shutdown ()
		VID_FreeReflib ()
	

#****************************************************************************
# INPUT
#****************************************************************************

in_joystick = None #cvar_t	*

# This is fake, it's acutally done by the Refresh load
def IN_Init ():

	global in_joystick

	in_joystick	= cvar.Cvar_Get ("in_joystick", "0", q_shared.CVAR_ARCHIVE)


def Real_IN_Init ():

	if RW_IN_Init_fp is not None:
		RW_IN_Init_fp(in_state)


def IN_Shutdown ():

	if RW_IN_Shutdown_fp is not None:
		RW_IN_Shutdown_fp()


def IN_Commands ():

	if RW_IN_Commands_fp is not None:
		RW_IN_Commands_fp()


def IN_Move (cmd): #usercmd_t *

	if RW_IN_Move_fp is not None:
		RW_IN_Move_fp(cmd)


def IN_Frame ():

	if RW_IN_Activate_fp is not None:
	
		if ( not cl_main.cl.refresh_prepped or cl_main.cls.key_dest == client.keydest_t.key_console or cl_main.cls.key_dest == client.keydest_t.key_menu):
			RW_IN_Activate_fp(False)
		else:
			RW_IN_Activate_fp(True)
	
	if RW_IN_Frame_fp is not None:
		RW_IN_Frame_fp()


def IN_Activate (active): #qboolean

	pass


def Do_Key_Event(key, down): #int, qboolean

	keys.Key_Event(key, down, q_shlinux.Sys_Milliseconds())

