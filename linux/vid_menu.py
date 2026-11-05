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

from qcommon import cvar
from client import menu, qmenu, keys, cl_scrn
from linux import vid_so
from game import q_shared
"""
#include "../client/client.h"
#include "../client/qmenu.h"
"""
REF_SOFT	= 0
REF_SOFTX11	= 1
REF_MESA3D  = 2
REF_3DFXGL = 3
REF_OPENGLX	= 4
REF_MESA3DGLX = 5

"""
extern cvar_t *vid_ref;
extern cvar_t *vid_fullscreen;
extern cvar_t *vid_gamma;
extern cvar_t *scr_viewsize;
"""

gl_mode = None #static cvar_t *
gl_driver = None #static cvar_t *
gl_picmip = None #static cvar_t *
gl_ext_palettedtexture = None #static cvar_t *

sw_mode = None #static cvar_t *
sw_stipplealpha = None #static cvar_t *

_windowed_mouse = None #static cvar_t *

#extern void M_ForceMenuOff( void );

"""
====================================================================

MENU INTERACTION

====================================================================
"""
SOFTWARE_MENU = 0
OPENGL_MENU   = 1

s_software_menu = menu.menuframework_s() #static menuframework_s
s_opengl_menu = menu.menuframework_s() #static menuframework_s
s_current_menu = None #static menuframework_s *
s_current_menu_index = 0 #static int

s_mode_list = [menu.menulist_s(), menu.menulist_s()] #static menulist_s [2]
s_ref_list = [menu.menulist_s(), menu.menulist_s()] #static menulist_s [2]
s_tq_slider = menu.menuslider_s() #static menuslider_s
s_screensize_slider = [menu.menuslider_s(), menu.menuslider_s()] #static menuslider_s [2]
s_brightness_slider = [menu.menuslider_s(), menu.menuslider_s()] #static menuslider_s [2]
s_fs_box = [menu.menulist_s(), menu.menulist_s()] #static menulist_s [2]
s_stipple_box = menu.menulist_s() #static menulist_s
s_paletted_texture_box = menu.menulist_s() #static menulist_s
s_windowed_mouse = menu.menulist_s() #static menulist_s
s_apply_action = [menu.menuaction_s(), menu.menuaction_s()] #static menuaction_s [2]
s_defaults_action = [menu.menuaction_s(), menu.menuaction_s()] #static menuaction_s [2]

def DriverCallback( unused ): #void *

	global s_current_menu, s_current_menu_index

	s_ref_list[int(not s_current_menu_index)].curvalue = s_ref_list[s_current_menu_index].curvalue

	# Q2PORT: only the OpenGL driver is implemented
	s_current_menu = s_opengl_menu
	s_current_menu_index = 1


def ScreenSizeCallback( s ): #void *

	slider = s # menuslider_s *

	cvar.Cvar_SetValue( "viewsize", slider.curvalue * 10 )


def BrightnessCallback( s ): #void *

	slider = s # menuslider_s *

	if s_current_menu_index == 0:
		s_brightness_slider[1].curvalue = s_brightness_slider[0].curvalue
	else:
		s_brightness_slider[0].curvalue = s_brightness_slider[1].curvalue

	if ( q_shared.Q_stricmp( vid_so.vid_ref.string, "soft" ) == 0 or
		 q_shared.Q_stricmp( vid_so.vid_ref.string, "softx" ) == 0 ):

		gamma = ( 0.8 - ( slider.curvalue/10.0 - 0.5 ) ) + 0.5

		cvar.Cvar_SetValue( "vid_gamma", gamma )


def ResetDefaults( unused ): #void *

	VID_MenuInit()


def ApplyChanges( unused ): #void *

	#float gamma;

	#
	# make values consistent
	#
	s_fs_box[int(not s_current_menu_index)].curvalue = s_fs_box[s_current_menu_index].curvalue
	s_brightness_slider[int(not s_current_menu_index)].curvalue = s_brightness_slider[s_current_menu_index].curvalue
	s_ref_list[int(not s_current_menu_index)].curvalue = s_ref_list[s_current_menu_index].curvalue

	#
	# invert sense so greater = brighter, and scale to a range of 0.5 to 1.3
	#
	gamma = ( 0.8 - ( s_brightness_slider[s_current_menu_index].curvalue/10.0 - 0.5 ) ) + 0.5

	cvar.Cvar_SetValue( "vid_gamma", gamma )
	cvar.Cvar_SetValue( "sw_stipplealpha", s_stipple_box.curvalue )
	cvar.Cvar_SetValue( "gl_picmip", 3 - s_tq_slider.curvalue )
	cvar.Cvar_SetValue( "vid_fullscreen", s_fs_box[s_current_menu_index].curvalue )
	cvar.Cvar_SetValue( "gl_ext_palettedtexture", s_paletted_texture_box.curvalue )
	cvar.Cvar_SetValue( "sw_mode", s_mode_list[SOFTWARE_MENU].curvalue )
	cvar.Cvar_SetValue( "gl_mode", s_mode_list[OPENGL_MENU].curvalue )
	cvar.Cvar_SetValue( "_windowed_mouse", s_windowed_mouse.curvalue)

	# Q2PORT: only the OpenGL driver is implemented
	cvar.Cvar_Set( "vid_ref", "glx" )
	cvar.Cvar_Set( "gl_driver", "libGL.so" )
	if gl_driver.modified:
		vid_so.vid_ref.modified = True

	"""
#if 0
	/*
	** update appropriate stuff if we're running OpenGL and gamma
	** has been modified
	*/
	if ( stricmp( vid_ref->string, "gl" ) == 0 )
	{
		if ( vid_gamma->modified )
		{
			vid_ref->modified = true;
			if ( stricmp( gl_driver->string, "3dfxgl" ) == 0 )
			{
				char envbuffer[1024];
				float g;

				vid_ref->modified = true;

				g = 2.00 * ( 0.8 - ( vid_gamma->value - 0.5 ) ) + 1.0F;
				Com_sprintf( envbuffer, sizeof(envbuffer), "SST_GAMMA=%f", g );
				putenv( envbuffer );

				vid_gamma->modified = false;
			}
		}
	}
#endif
	"""

	menu.M_ForceMenuOff()


"""
** VID_MenuInit
"""
def VID_MenuInit():

	global gl_driver, gl_picmip, gl_mode, sw_mode, gl_ext_palettedtexture, sw_stipplealpha, _windowed_mouse
	global s_current_menu_index

	resolutions = [ #static const char *[]
		"[320 240  ]",
		"[400 300  ]",
		"[512 384  ]",
		"[640 480  ]",
		"[800 600  ]",
		"[960 720  ]",
		"[1024 768 ]",
		"[1152 864 ]",
		"[1280 1024]",
		"[1600 1200]",
		"[2048 1536]",
	]
	refs = [ #static const char *[]
		"[OpenGL glX     ]",
	]
	yesno_names = [ #static const char *[]
		"no",
		"yes",
	]
	#int i;

	if gl_driver is None:
		gl_driver = cvar.Cvar_Get( "gl_driver", "libMesaGL.so.2", 0 )
	if gl_picmip is None:
		gl_picmip = cvar.Cvar_Get( "gl_picmip", "0", 0 )
	if gl_mode is None:
		gl_mode = cvar.Cvar_Get( "gl_mode", "3", 0 )
	if sw_mode is None:
		sw_mode = cvar.Cvar_Get( "sw_mode", "0", 0 )
	if gl_ext_palettedtexture is None:
		gl_ext_palettedtexture = cvar.Cvar_Get( "gl_ext_palettedtexture", "1", q_shared.CVAR_ARCHIVE )

	if sw_stipplealpha is None:
		sw_stipplealpha = cvar.Cvar_Get( "sw_stipplealpha", "0", q_shared.CVAR_ARCHIVE )

	if _windowed_mouse is None:
		_windowed_mouse = cvar.Cvar_Get( "_windowed_mouse", "0", q_shared.CVAR_ARCHIVE )

	s_mode_list[SOFTWARE_MENU].curvalue = int(sw_mode.value)
	s_mode_list[OPENGL_MENU].curvalue = int(gl_mode.value)

	if cl_scrn.scr_viewsize is None:
		cl_scrn.scr_viewsize = cvar.Cvar_Get ("viewsize", "100", q_shared.CVAR_ARCHIVE)

	s_screensize_slider[SOFTWARE_MENU].curvalue = cl_scrn.scr_viewsize.value/10
	s_screensize_slider[OPENGL_MENU].curvalue = cl_scrn.scr_viewsize.value/10

	# Q2PORT: only the OpenGL driver is implemented, force the OpenGL menu
	s_current_menu_index = OPENGL_MENU
	s_ref_list[0].curvalue = s_ref_list[1].curvalue = 0

	s_software_menu.x = int(vid_so.viddef.width * 0.50)
	s_software_menu.nitems = 0
	s_opengl_menu.x = int(vid_so.viddef.width * 0.50)
	s_opengl_menu.nitems = 0

	for i in range(2):

		s_ref_list[i].type = menu.MTYPE_SPINCONTROL
		s_ref_list[i].name = "driver"
		s_ref_list[i].x = 0
		s_ref_list[i].y = 0
		s_ref_list[i].callback = DriverCallback
		s_ref_list[i].itemnames = refs

		s_mode_list[i].type = menu.MTYPE_SPINCONTROL
		s_mode_list[i].name = "video mode"
		s_mode_list[i].x = 0
		s_mode_list[i].y = 10
		s_mode_list[i].itemnames = resolutions

		s_screensize_slider[i].type	= menu.MTYPE_SLIDER
		s_screensize_slider[i].x		= 0
		s_screensize_slider[i].y		= 20
		s_screensize_slider[i].name	= "screen size"
		s_screensize_slider[i].minvalue = 3
		s_screensize_slider[i].maxvalue = 12
		s_screensize_slider[i].callback = ScreenSizeCallback

		s_brightness_slider[i].type	= menu.MTYPE_SLIDER
		s_brightness_slider[i].x	= 0
		s_brightness_slider[i].y	= 30
		s_brightness_slider[i].name	= "brightness"
		s_brightness_slider[i].callback = BrightnessCallback
		s_brightness_slider[i].minvalue = 5
		s_brightness_slider[i].maxvalue = 13
		s_brightness_slider[i].curvalue = ( 1.3 - vid_so.vid_gamma.value + 0.5 ) * 10

		s_fs_box[i].type = menu.MTYPE_SPINCONTROL
		s_fs_box[i].x	= 0
		s_fs_box[i].y	= 40
		s_fs_box[i].name	= "fullscreen"
		s_fs_box[i].itemnames = yesno_names
		s_fs_box[i].curvalue = int(vid_so.vid_fullscreen.value)

		s_defaults_action[i].type = menu.MTYPE_ACTION
		s_defaults_action[i].name = "reset to default"
		s_defaults_action[i].x    = 0
		s_defaults_action[i].y    = 90
		s_defaults_action[i].callback = ResetDefaults

		s_apply_action[i].type = menu.MTYPE_ACTION
		s_apply_action[i].name = "apply"
		s_apply_action[i].x    = 0
		s_apply_action[i].y    = 100
		s_apply_action[i].callback = ApplyChanges

	s_stipple_box.type = menu.MTYPE_SPINCONTROL
	s_stipple_box.x	= 0
	s_stipple_box.y	= 60
	s_stipple_box.name	= "stipple alpha"
	s_stipple_box.curvalue = int(sw_stipplealpha.value)
	s_stipple_box.itemnames = yesno_names

	s_windowed_mouse.type = menu.MTYPE_SPINCONTROL
	s_windowed_mouse.x  = 0
	s_windowed_mouse.y  = 72
	s_windowed_mouse.name   = "windowed mouse"
	s_windowed_mouse.curvalue = int(_windowed_mouse.value)
	s_windowed_mouse.itemnames = yesno_names

	s_tq_slider.type	= menu.MTYPE_SLIDER
	s_tq_slider.x		= 0
	s_tq_slider.y		= 60
	s_tq_slider.name	= "texture quality"
	s_tq_slider.minvalue = 0
	s_tq_slider.maxvalue = 3
	s_tq_slider.curvalue = 3-gl_picmip.value

	s_paletted_texture_box.type = menu.MTYPE_SPINCONTROL
	s_paletted_texture_box.x	= 0
	s_paletted_texture_box.y	= 70
	s_paletted_texture_box.name	= "8-bit textures"
	s_paletted_texture_box.itemnames = yesno_names
	s_paletted_texture_box.curvalue = int(gl_ext_palettedtexture.value)

	qmenu.Menu_AddItem( s_software_menu, s_ref_list[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_software_menu, s_mode_list[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_software_menu, s_screensize_slider[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_software_menu, s_brightness_slider[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_software_menu, s_fs_box[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_software_menu, s_stipple_box )
	qmenu.Menu_AddItem( s_software_menu, s_windowed_mouse )

	qmenu.Menu_AddItem( s_opengl_menu, s_ref_list[OPENGL_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_mode_list[OPENGL_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_screensize_slider[OPENGL_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_brightness_slider[OPENGL_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_fs_box[OPENGL_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_tq_slider )
	qmenu.Menu_AddItem( s_opengl_menu, s_paletted_texture_box )

	qmenu.Menu_AddItem( s_software_menu, s_defaults_action[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_software_menu, s_apply_action[SOFTWARE_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_defaults_action[OPENGL_MENU] )
	qmenu.Menu_AddItem( s_opengl_menu, s_apply_action[OPENGL_MENU] )

	qmenu.Menu_Center( s_software_menu )
	qmenu.Menu_Center( s_opengl_menu )
	s_opengl_menu.x -= 8
	s_software_menu.x -= 8


"""
================
VID_MenuDraw
================
"""
def VID_MenuDraw ():

	global s_current_menu

	#int w, h;

	if s_current_menu_index == 0:
		s_current_menu = s_software_menu
	else:
		s_current_menu = s_opengl_menu

	#
	# draw the banner
	#
	w, h = vid_so.re.DrawGetPicSize( "m_banner_video" )
	vid_so.re.DrawPic( vid_so.viddef.width // 2 - w // 2, vid_so.viddef.height //2 - 110, "m_banner_video" )

	#
	# move cursor to a reasonable starting position
	#
	qmenu.Menu_AdjustCursor( s_current_menu, 1 )

	#
	# draw the menu
	#
	qmenu.Menu_Draw( s_current_menu )


"""
================
VID_MenuKey
================
"""
def VID_MenuKey( key ): #int (returns const char *)

	#extern void M_PopMenu( void );

	m = s_current_menu # menuframework_s *
	sound = "misc/menu1.wav" #static const char *

	if key == keys.K_ESCAPE:
		menu.M_PopMenu()
		return None
	elif key == keys.K_UPARROW:
		m.cursor -= 1
		qmenu.Menu_AdjustCursor( m, -1 )
	elif key == keys.K_DOWNARROW:
		m.cursor += 1
		qmenu.Menu_AdjustCursor( m, 1 )
	elif key == keys.K_LEFTARROW:
		qmenu.Menu_SlideItem( m, -1 )
	elif key == keys.K_RIGHTARROW:
		qmenu.Menu_SlideItem( m, 1 )
	elif key == keys.K_ENTER:
		qmenu.Menu_SelectItem( m )

	return sound
