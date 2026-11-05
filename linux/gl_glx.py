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
import OpenGL.GL as GL
from ref_gl import gl_rmain
from game import q_shared

screen = None
"""
** GLW_IMP.C
**
** This file contains ALL Linux specific stuff having to do with the
** OpenGL refresh.  When a port is being made the following functions
** must be implemented by the port:
**
** GLimp_EndFrame
** GLimp_Init
** GLimp_Shutdown
** GLimp_SwitchFullscreen
**
*/

#include <termios.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/vt.h>
#include <stdarg.h>
#include <stdio.h>
#include <signal.h>

#include "../ref_gl/gl_local.h"

#include "../client/keys.h"

#include "../linux/rw_linux.h"
#include "../linux/glw_linux.h"

#include <GL/glx.h>

#include <X11/keysym.h>
#include <X11/cursorfont.h>

#include <X11/extensions/xf86dga.h>
#include <X11/extensions/xf86vmode.h>

"""
class glwstate_t(object): # glw_linux.h

	def __init__(self):
		self.OpenGLLib = None # void *, instance of OpenGL library

		self.log_fp = None # FILE *

glw_state = glwstate_t()
"""

static Display *dpy = NULL;
static int scrnum;
static Window win;
static GLXContext ctx = NULL;

#define KEY_MASK (KeyPressMask | KeyReleaseMask)
#define MOUSE_MASK (ButtonPressMask | ButtonReleaseMask | \
		    PointerMotionMask | ButtonMotionMask )
#define X_MASK (KEY_MASK | MOUSE_MASK | VisibilityChangeMask | StructureNotifyMask )

/*****************************************************************************/
/* MOUSE                                                                     */
/*****************************************************************************/
"""
# Q2PORT: X11 is replaced by pygame for the window events. The pointer grab,
# the hidden cursor and the relative motion pygame reports while grabbed take
# the place of XGrabPointer, the null cursor and DGA or XWarpPointer.

# this is inside the renderer shared lib, so these are called from vid_so

mouse_avail = False #static qboolean
mx, my = 0, 0 #static int
old_mouse_x, old_mouse_y = 0, 0 #static int

win_x, win_y = 0, 0 #static int

m_filter = None #static cvar_t *
in_mouse = None #static cvar_t *
in_dgamouse = None #static cvar_t *

"""
static cvar_t	*r_fakeFullscreen;

static XF86VidModeModeInfo **vidmodes;
static int default_dotclock_vidmode;
static int num_vidmodes;
"""
vidmode_active = False #static qboolean

mlooking = False #static qboolean

mouse_active = False #static qboolean
dgamouse = False #static qboolean
vidmode_ext = False #static qboolean

# state struct passed in Init
in_state = None #static in_state_t *

sensitivity = None #static cvar_t *
lookstrafe = None #static cvar_t *
m_side = None #static cvar_t *
m_yaw = None #static cvar_t *
m_pitch = None #static cvar_t *
m_forward = None #static cvar_t *
freelook = None #static cvar_t *

"""
static Cursor CreateNullCursor(Display *display, Window root)
{
	...
}
"""

def install_grabs():

	global dgamouse, mouse_active

	# inviso cursor
	pygame.mouse.set_visible(False) # XDefineCursor(dpy, win, CreateNullCursor(dpy, win));

	pygame.event.set_grab(True) # XGrabPointer(dpy, win, True, 0, GrabModeAsync, GrabModeAsync, win, None, CurrentTime);

	if in_dgamouse.value:
		# a grabbed pointer with a hidden cursor gives relative motion, as XF86DGADirectMouse does
		dgamouse = True
	"""
	else {
		XWarpPointer(dpy, None, win,
					 0, 0, 0, 0,
					 vid.width / 2, vid.height / 2);
	}

	XGrabKeyboard(dpy, win,
				  False,
				  GrabModeAsync, GrabModeAsync,
				  CurrentTime);
	"""
	pygame.mouse.get_rel() # discard the motion from before the grab

	mouse_active = True

#	XSync(dpy, True);


def uninstall_grabs():

	global dgamouse, mouse_active

	if screen is None: # if (!dpy || !win)
		return

	if dgamouse:
		dgamouse = False
		# XF86DGADirectVideo(dpy, DefaultScreen(dpy), 0);
	
	pygame.event.set_grab(False) # XUngrabPointer(dpy, CurrentTime); XUngrabKeyboard(dpy, CurrentTime);

	# inviso cursor
	pygame.mouse.set_visible(True) # XUndefineCursor(dpy, win);

	mouse_active = False


def Force_CenterView_f ():

	in_state.viewangles[q_shared.PITCH] = 0


def RW_IN_MLookDown (): 

	global mlooking

	mlooking = True 


def RW_IN_MLookUp ():

	global mlooking

	mlooking = False
	in_state.IN_CenterView_fp ()


def RW_IN_Init(in_state_p): #in_state_t *

	global in_state, m_filter, in_mouse, in_dgamouse, freelook, lookstrafe, sensitivity
	global m_pitch, m_yaw, m_forward, m_side, mx, my, mouse_avail

	#int mtype;
	#int i;

	in_state = in_state_p

	# mouse variables
	m_filter = gl_rmain.ri.Cvar_Get ("m_filter", "0", 0)
	in_mouse = gl_rmain.ri.Cvar_Get ("in_mouse", "1", q_shared.CVAR_ARCHIVE)
	in_dgamouse = gl_rmain.ri.Cvar_Get ("in_dgamouse", "1", q_shared.CVAR_ARCHIVE)
	freelook = gl_rmain.ri.Cvar_Get( "freelook", "0", 0 )
	lookstrafe = gl_rmain.ri.Cvar_Get ("lookstrafe", "0", 0)
	sensitivity = gl_rmain.ri.Cvar_Get ("sensitivity", "3", 0)
	m_pitch = gl_rmain.ri.Cvar_Get ("m_pitch", "0.022", 0)
	m_yaw = gl_rmain.ri.Cvar_Get ("m_yaw", "0.022", 0)
	m_forward = gl_rmain.ri.Cvar_Get ("m_forward", "1", 0)
	m_side = gl_rmain.ri.Cvar_Get ("m_side", "0.8", 0)

	gl_rmain.ri.Cmd_AddCommand ("+mlook", RW_IN_MLookDown)
	gl_rmain.ri.Cmd_AddCommand ("-mlook", RW_IN_MLookUp)

	gl_rmain.ri.Cmd_AddCommand ("force_centerview", Force_CenterView_f)

	mx = my = 0.0
	mouse_avail = True


def RW_IN_Shutdown():

	global mouse_avail

	mouse_avail = False


"""
===========
IN_Commands
===========
"""
def RW_IN_Commands ():

	pass


"""
===========
IN_Move
===========
"""
def RW_IN_Move (cmd): #usercmd_t *

	global mx, my, old_mouse_x, old_mouse_y

	if not mouse_avail:
		return
   
	if m_filter.value:
	
		mx = (mx + old_mouse_x) * 0.5
		my = (my + old_mouse_y) * 0.5
	
	old_mouse_x = mx
	old_mouse_y = my

	mx *= sensitivity.value
	my *= sensitivity.value

	# add mouse X/Y movement to cmd
	if ( (in_state.in_strafe_state.state & 1) or # *in_state->in_strafe_state & 1
		(lookstrafe.value and mlooking )):
		cmd.sidemove += m_side.value * mx
	else:
		in_state.viewangles[q_shared.YAW] -= m_yaw.value * mx

	if ( (mlooking or freelook.value) and 
		not (in_state.in_strafe_state.state & 1)):
	
		in_state.viewangles[q_shared.PITCH] += m_pitch.value * my
	
	else:
	
		cmd.forwardmove -= m_forward.value * my
	
	mx = my = 0


def IN_DeactivateMouse(): 

	global mouse_active

	if not mouse_avail or screen is None: # || !dpy || !win
		return

	if mouse_active:
		uninstall_grabs()
		mouse_active = False


def IN_ActivateMouse(): 

	global mx, my, mouse_active

	if not mouse_avail or screen is None: # || !dpy || !win
		return

	if not mouse_active:
		mx = my = 0 # don't spazz
		install_grabs()
		mouse_active = True


def RW_IN_Frame ():

	pass


def RW_IN_Activate(active): #qboolean

	if active or vidmode_active:
		IN_ActivateMouse()
	else:
		IN_DeactivateMouse ()


"""
/*****************************************************************************/
/* KEYBOARD                                                                  */
/*****************************************************************************/
"""
def XLateKey(ev): #XKeyEvent * (returns int), a pygame KEYDOWN or KEYUP event here

	from client import keys # the K_ values, imported here as the renderer loads before the client modules finish

	#int key;
	#char buf[64];
	#KeySym keysym;

	key = 0

	keysym = ev.key # XLookupString(ev, buf, sizeof buf, &keysym, 0);

	if keysym == pygame.K_KP9:	key = keys.K_KP_PGUP # XK_KP_Page_Up
	elif keysym == pygame.K_PAGEUP:	key = keys.K_PGUP

	elif keysym == pygame.K_KP3: key = keys.K_KP_PGDN # XK_KP_Page_Down
	elif keysym == pygame.K_PAGEDOWN:	key = keys.K_PGDN

	elif keysym == pygame.K_KP7: key = keys.K_KP_HOME # XK_KP_Home
	elif keysym == pygame.K_HOME:	key = keys.K_HOME

	elif keysym == pygame.K_KP1: key = keys.K_KP_END # XK_KP_End
	elif keysym == pygame.K_END:	key = keys.K_END

	elif keysym == pygame.K_KP4: key = keys.K_KP_LEFTARROW # XK_KP_Left
	elif keysym == pygame.K_LEFT:	key = keys.K_LEFTARROW

	elif keysym == pygame.K_KP6: key = keys.K_KP_RIGHTARROW # XK_KP_Right
	elif keysym == pygame.K_RIGHT:	key = keys.K_RIGHTARROW

	elif keysym == pygame.K_KP2: key = keys.K_KP_DOWNARROW # XK_KP_Down
	elif keysym == pygame.K_DOWN:	key = keys.K_DOWNARROW

	elif keysym == pygame.K_KP8: key = keys.K_KP_UPARROW # XK_KP_Up
	elif keysym == pygame.K_UP:		key = keys.K_UPARROW

	elif keysym == pygame.K_ESCAPE: key = keys.K_ESCAPE

	elif keysym == pygame.K_KP_ENTER: key = keys.K_KP_ENTER
	elif keysym == pygame.K_RETURN: key = keys.K_ENTER

	elif keysym == pygame.K_TAB:		key = keys.K_TAB

	elif keysym == pygame.K_F1:		 key = keys.K_F1

	elif keysym == pygame.K_F2:		 key = keys.K_F2

	elif keysym == pygame.K_F3:		 key = keys.K_F3

	elif keysym == pygame.K_F4:		 key = keys.K_F4

	elif keysym == pygame.K_F5:		 key = keys.K_F5

	elif keysym == pygame.K_F6:		 key = keys.K_F6

	elif keysym == pygame.K_F7:		 key = keys.K_F7

	elif keysym == pygame.K_F8:		 key = keys.K_F8

	elif keysym == pygame.K_F9:		 key = keys.K_F9

	elif keysym == pygame.K_F10:		key = keys.K_F10

	elif keysym == pygame.K_F11:		key = keys.K_F11

	elif keysym == pygame.K_F12:		key = keys.K_F12

	elif keysym == pygame.K_BACKSPACE: key = keys.K_BACKSPACE

	elif keysym == pygame.K_KP_PERIOD: key = keys.K_KP_DEL # XK_KP_Delete
	elif keysym == pygame.K_DELETE: key = keys.K_DEL

	elif keysym == pygame.K_PAUSE:	key = keys.K_PAUSE

	elif keysym in (pygame.K_LSHIFT,
		pygame.K_RSHIFT):	key = keys.K_SHIFT

	elif keysym in (pygame.K_LCTRL, # XK_Execute has no pygame key
		pygame.K_RCTRL):	key = keys.K_CTRL

	elif keysym in (pygame.K_LALT,
		pygame.K_LMETA,
		pygame.K_RALT,
		pygame.K_RMETA): key = keys.K_ALT

	elif keysym == pygame.K_KP5: key = keys.K_KP_5 # XK_KP_Begin

	elif keysym == pygame.K_INSERT: key = keys.K_INS
	elif keysym == pygame.K_KP0: key = keys.K_KP_INS # XK_KP_Insert

	elif keysym == pygame.K_KP_MULTIPLY: key = ord('*')
	elif keysym == pygame.K_KP_PLUS:  key = keys.K_KP_PLUS
	elif keysym == pygame.K_KP_MINUS: key = keys.K_KP_MINUS
	elif keysym == pygame.K_KP_DIVIDE: key = keys.K_KP_SLASH

	else:
		# key = *(unsigned char*)buf; pygame's key value is the unshifted
		# character for printable keys, and keys with no character give 0
		key = keysym if keysym < 256 else 0
		if key >= ord('A') and key <= ord('Z'):
			key = key - ord('A') + ord('a')
	
	return key


def HandleEvents():

	global mx, my

	from client import keys # the K_ values, imported here as the renderer loads before the client modules finish

	#XEvent event;
	#int b;
	#qboolean dowarp = false;
	#int mwx = vid.width/2;
	#int mwy = vid.height/2;
   
	if screen is None: # if (!dpy)
		return

	for event in pygame.event.get(): # while (XPending(dpy)) { XNextEvent(dpy, &event);

		if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
			if in_state is not None and in_state.Key_Event_fp is not None:
				in_state.Key_Event_fp (XLateKey(event), event.type == pygame.KEYDOWN)

		elif event.type == pygame.MOUSEMOTION:
			if mouse_active:
				# pygame reports relative motion while the pointer is grabbed, like DGA
				mx += event.rel[0] * 2 # mx += (event.xmotion.x + win_x) * 2;
				my += event.rel[1] * 2 # my += (event.xmotion.y + win_y) * 2;

		elif event.type == pygame.MOUSEBUTTONDOWN:
			b=-1
			if event.button == 1:
				b = 0
			elif event.button == 2:
				b = 2
			elif event.button == 3:
				b = 1
			if b>=0 and in_state is not None and in_state.Key_Event_fp is not None:
				in_state.Key_Event_fp (keys.K_MOUSE1 + b, True)

		elif event.type == pygame.MOUSEBUTTONUP:
			b=-1
			if event.button == 1:
				b = 0
			elif event.button == 2:
				b = 2
			elif event.button == 3:
				b = 1
			if b>=0 and in_state is not None and in_state.Key_Event_fp is not None:
				in_state.Key_Event_fp (keys.K_MOUSE1 + b, False)

		elif event.type == pygame.QUIT: # Q2PORT: the window was closed, quit as the console command does
			gl_rmain.ri.Cmd_ExecuteText (2, "quit\n") # EXEC_APPEND

		# CreateNotify and ConfigureNotify only tracked win_x and win_y for the DGA motion
	
	"""
	if (dowarp) {
		/* move the mouse to the window center again */
		XWarpPointer(dpy,None,win,0,0,0,0, vid.width/2,vid.height/2);
	}
	"""

Key_Event_fp = None #Key_Event_fp_t

def KBD_Init(fp): #Key_Event_fp_t

	global Key_Event_fp

	Key_Event_fp = fp


def KBD_Update():

	# get events from x server
	HandleEvents()


def KBD_Close():

	pass

"""

/*****************************************************************************/

static qboolean GLimp_SwitchFullscreen( int width, int height );
qboolean GLimp_InitGL (void);

static void signal_handler(int sig)
{
	printf("Received signal %d, exiting...\n", sig);
	GLimp_Shutdown();
	_exit(0);
}

static void InitSig(void)
{
	signal(SIGHUP, signal_handler);
	signal(SIGQUIT, signal_handler);
	signal(SIGILL, signal_handler);
	signal(SIGTRAP, signal_handler);
	signal(SIGIOT, signal_handler);
	signal(SIGBUS, signal_handler);
	signal(SIGFPE, signal_handler);
	signal(SIGSEGV, signal_handler);
	signal(SIGTERM, signal_handler);
}

/*
** GLimp_SetMode
*/
"""
def GLimp_SetMode( pwidth, pheight, mode, fullscreen ): # int *, int *, int, qboolean (returns rserr_t, *pwidth, *pheight)

	global screen
	"""
	int width, height;
	int attrib[] = {
		GLX_RGBA,
		GLX_RED_SIZE, 1,
		GLX_GREEN_SIZE, 1,
		GLX_BLUE_SIZE, 1,
		GLX_DOUBLEBUFFER,
		GLX_DEPTH_SIZE, 1,
		None
	};
	Window root;
	XVisualInfo *visinfo;
	XSetWindowAttributes attr;
	unsigned long mask;
	int MajorVersion, MinorVersion;
	int actualWidth, actualHeight;
	int i;

	r_fakeFullscreen = gl_rmain.ri.Cvar_Get( "r_fakeFullscreen", "0", CVAR_ARCHIVE);
	"""
	gl_rmain.ri.Con_Printf( q_shared.PRINT_ALL, "Initializing OpenGL display\n")
	
	mode = int(mode)

	if fullscreen:
		gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "...setting fullscreen mode {}:".format(mode) )
	else:
		gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "...setting mode {}:".format(mode) )

	ok, width, height = gl_rmain.ri.Vid_GetModeInfo( mode )
	if not ok:
	
		gl_rmain.ri.Con_Printf( q_shared.PRINT_ALL, " invalid mode\n" )
		return gl_rmain.rserr_t.rserr_invalid_mode, pwidth, pheight
	
	gl_rmain.ri.Con_Printf( q_shared.PRINT_ALL, " {} {}\n".format(width, height) )
	
	# destroy the existing window
	GLimp_Shutdown ()
	"""

	// Mesa VooDoo hacks
	if (fullscreen)
		putenv("MESA_GLX_FX=fullscreen");
	else
		putenv("MESA_GLX_FX=window");

	if (!(dpy = XOpenDisplay(NULL))) {
		fprintf(stderr, "Error couldn't open the X display\n");
		return rserr_invalid_mode;
	}

	scrnum = DefaultScreen(dpy);
	root = RootWindow(dpy, scrnum);

	// Get video mode list
	MajorVersion = MinorVersion = 0;
	if (!XF86VidModeQueryVersion(dpy, &MajorVersion, &MinorVersion)) { 
		vidmode_ext = false;
	} else {
		gl_rmain.ri.Con_Printf(q_shared.PRINT_ALL, "Using XFree86-VidModeExtension Version %d.%d\n",
			MajorVersion, MinorVersion);
		vidmode_ext = true;
	}

	visinfo = qglXChooseVisual(dpy, scrnum, attrib);
	if (!visinfo) {
		fprintf(stderr, "Error couldn't get an RGB, Double-buffered, Depth visual\n");
		return rserr_invalid_mode;
	}

	if (vidmode_ext) {
		int best_fit, best_dist, dist, x, y;
		
		XF86VidModeGetAllModeLines(dpy, scrnum, &num_vidmodes, &vidmodes);

		// Are we going fullscreen?  If so, let's change video mode
		if (fullscreen && !r_fakeFullscreen->value) {
			best_dist = 9999999;
			best_fit = -1;

			for (i = 0; i < num_vidmodes; i++) {
				if (width > vidmodes[i]->hdisplay ||
					height > vidmodes[i]->vdisplay)
					continue;

				x = width - vidmodes[i]->hdisplay;
				y = height - vidmodes[i]->vdisplay;
				dist = (x * x) + (y * y);
				if (dist < best_dist) {
					best_dist = dist;
					best_fit = i;
				}
			}

			if (best_fit != -1) {
				actualWidth = vidmodes[best_fit]->hdisplay;
				actualHeight = vidmodes[best_fit]->vdisplay;

				// change to the mode
				XF86VidModeSwitchToMode(dpy, scrnum, vidmodes[best_fit]);
				vidmode_active = true;

				// Move the viewport to top left
				XF86VidModeSetViewPort(dpy, scrnum, 0, 0);
			} else
				fullscreen = 0;
		}
	}

	/* window attributes */
	attr.background_pixel = 0;
	attr.border_pixel = 0;
	attr.colormap = XCreateColormap(dpy, root, visinfo->visual, AllocNone);
	attr.event_mask = X_MASK;
	if (vidmode_active) {
		mask = CWBackPixel | CWColormap | CWSaveUnder | CWBackingStore | 
			CWEventMask | CWOverrideRedirect;
		attr.override_redirect = True;
		attr.backing_store = NotUseful;
		attr.save_under = False;
	} else
		mask = CWBackPixel | CWBorderPixel | CWColormap | CWEventMask;

	win = XCreateWindow(dpy, root, 0, 0, width, height,
						0, visinfo->depth, InputOutput,
						visinfo->visual, mask, &attr);
	XMapWindow(dpy, win);
	"""
	# Q2PORT: pygame creates the window and GL context in place of XCreateWindow and glXCreateContext,
	# and switches the screen mode for fullscreen in place of XF86VidModeSwitchToMode
	flags = pygame.OPENGL | pygame.DOUBLEBUF
	if fullscreen:
		flags |= pygame.FULLSCREEN
	try:
		screen = pygame.display.set_mode((width, height), flags)
	except pygame.error as err:
		gl_rmain.ri.Con_Printf( q_shared.PRINT_ALL, "Error couldn't set the video mode: {}\n".format(err) )
		screen = None
		if fullscreen:
			return gl_rmain.rserr_t.rserr_invalid_fullscreen, pwidth, pheight
		return gl_rmain.rserr_t.rserr_invalid_mode, pwidth, pheight

	"""
	if (vidmode_active) {
		XMoveWindow(dpy, win, 0, 0);
		XRaiseWindow(dpy, win);
		XWarpPointer(dpy, None, win, 0, 0, 0, 0, 0, 0);
		XFlush(dpy);
		// Move the viewport to top left
		XF86VidModeSetViewPort(dpy, scrnum, 0, 0);
	}

	XFlush(dpy);

	ctx = qglXCreateContext(dpy, visinfo, NULL, True);

	qglXMakeCurrent(dpy, win, ctx);
	"""
	width, height = pygame.display.get_window_size()

	pwidth = width
	pheight = height

	# let the sound and input subsystems know about the new window
	gl_rmain.ri.Vid_NewWindow (width, height)

	#qglXMakeCurrent(dpy, win, ctx);

	return gl_rmain.rserr_t.rserr_ok, pwidth, pheight



"""
/*
** GLimp_Shutdown
**
** This routine does all OS specific shutdown procedures for the OpenGL
** subsystem.  Under OpenGL this means NULLing out the current DC and
** HGLRC, deleting the rendering context, and releasing the DC acquired
** for the window.  The state structure is also nulled out.
**
*/
"""
def GLimp_Shutdown():

	global mouse_active, dgamouse, screen

	uninstall_grabs()
	mouse_active = False
	dgamouse = False

	if screen is not None: # if (dpy)
		# qglXDestroyContext, XDestroyWindow, the vidmode restore and XCloseDisplay
		pygame.display.quit()
	
	screen = None # ctx = NULL; dpy = NULL; win = 0;

"""
/*
** GLimp_Init
**
** This routine is responsible for initializing the OS specific portions
** of OpenGL.  
*/
"""
def GLimp_Init( hinstance, wndproc ): #void *, void * (returns int)

	#InitSig();

	return True


#
# GLimp_BeginFrame
#
def GLimp_BeginFrame( camera_seperation ): #float
	pass

"""
/*
** GLimp_EndFrame
** 
** Responsible for doing a swapbuffers and possibly for other stuff
** as yet to be determined.  Probably better not to make this a GLimp
** function and instead do a call to GLimp_SwapBuffers.
*/
"""
def GLimp_EndFrame ():

	#qglFlush();
	#qglXSwapBuffers(dpy, win);
	pygame.display.flip()

"""
/*
** GLimp_AppActivate
*/
"""
def GLimp_AppActivate( active ): #qboolean
	pass

"""

void Fake_glColorTableEXT( GLenum target, GLenum internalformat,
                             GLsizei width, GLenum format, GLenum type,
                             const GLvoid *table )
{
	byte temptable[256][4];
	byte *intbl;
	int i;

	for (intbl = (byte *)table, i = 0; i < 256; i++) {
		temptable[i][2] = *intbl++;
		temptable[i][1] = *intbl++;
		temptable[i][0] = *intbl++;
		temptable[i][3] = 255;
	}
	qgl3DfxSetPaletteEXT((GLuint *)temptable);
}


/*------------------------------------------------*/
/* X11 Input Stuff
/*------------------------------------------------*/
"""
