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

This is the refresher dependend video menu. If you add a new
refresher this menu must be altered.

=======================================================================
"""
from __future__ import annotations

import math
from enum import Enum

from client.vid import vid
from common.header import shared
from common.shared import shared as shared_c
from common import cmdparser
from common import cvar
from client import cl_screen
from client.menu.header import qmenu as qmenu_h
from client.menu import menu
from client.menu import qmenu
from client.vid import vid

"""
#include "../../client/header/client.h"
#include "../../client/menu/header/qmenu.h"
#include "header/qmenu.h"

extern void M_ForceMenuOff(void);
extern const char *Default_MenuKey(menuframework_s *m, int key);
extern void Default_MenuDraw(menuframework_s *m);
"""

r_mode = None #static cvar_t *
vid_displayindex = None #static cvar_t *
r_hudscale = None #static cvar_t *
r_consolescale = None #static cvar_t *
r_menuscale = None #static cvar_t *
crosshair_scale = None #static cvar_t *
#extern cvar_t *scr_viewsize;
#extern cvar_t *vid_fullscreen;
#extern cvar_t *vid_renderer;
r_vsync = None #static cvar_t *
gl_anisotropic = None #static cvar_t *
gl_msaa_samples = None #static cvar_t *
gl3_colorlight = None #static cvar_t *
gl4_colorlight = None #static cvar_t *
gl4_bloom = None #static cvar_t *
vk_dynamic = None #static cvar_t *

s_opengl_menu = qmenu_h.menuframework_s() #static menuframework_s

s_renderer_list = qmenu_h.menulist_s() #static menulist_s
s_mode_list = qmenu_h.menulist_s() #static menulist_s
s_uiscale_list = qmenu_h.menulist_s() #static menulist_s
s_brightness_slider = qmenu_h.menuslider_s() #static menuslider_s
s_fov_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl1_intensity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl3_intensity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl4_intensity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_vk_intensity_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl1_overbrightbits_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl3_overbrightbits_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl4_overbrightbits_slider = qmenu_h.menuslider_s() #static menuslider_s
s_vk_overbrightbits_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl1_minlight_slider = qmenu_h.menuslider_s() #static menuslider_s
s_gl3_colorlight_list = qmenu_h.menulist_s() #static menulist_s
s_gl4_colorlight_list = qmenu_h.menulist_s() #static menulist_s
s_gl4_bloom_list = qmenu_h.menulist_s() #static menulist_s
s_vk_dynamic_list = qmenu_h.menulist_s() #static menulist_s
s_fs_box = qmenu_h.menulist_s() #static menulist_s
s_vsync_list = qmenu_h.menulist_s() #static menulist_s
s_af_list = qmenu_h.menulist_s() #static menulist_s
s_msaa_list = qmenu_h.menulist_s() #static menulist_s
s_filter_list = qmenu_h.menulist_s() #static menulist_s
s_defaults_action = qmenu_h.menuaction_s() #static menuaction_s
s_apply_action = qmenu_h.menuaction_s() #static menuaction_s

# --------

# gl1, gl3, gles1, gles3, gl4, vk, soft
MAXRENDERERS	= 7

class renderer_type(Enum):

	ref_custom = 0
	ref_gl1 = 1		# encompasses gl1 and gles1
	ref_gl3 = 2		# encompasses gl3 and gles3
	ref_gl4 = 3
	ref_vk = 4
	ref_soft = 5

class renderer(object):

	def __init__(self, boxstr=None, cvarstr=None):

		self.boxstr = boxstr #const char *
		self.cvarstr = cvarstr #const char *

rendererlist = [renderer() for i in range(MAXRENDERERS)] #static renderer[MAXRENDERERS]
numrenderer = 0 #static int

Renderer_FillRenderdef_fulllist = [ #static const renderer [], in Renderer_FillRenderdef
	renderer("[OpenGL 1.4]", "gl1"),
	renderer("[OpenGL ES1]", "gles1"),
	renderer("[OpenGL 3.2]", "gl3"),
	renderer("[OpenGL ES3]", "gles3"),
	renderer("[OpenGL 4.6]", "gl4"),
	renderer("[Vulkan    ]", "vk"),
	renderer("[Software  ]", "soft"),
	renderer(None, None)
]

def Renderer_FillRenderdef(): # (static)

	global numrenderer

	fulllist = Renderer_FillRenderdef_fulllist
	idx = 0

	numrenderer = -1

	while fulllist[idx].cvarstr:

		if vid.VID_HasRenderer(fulllist[idx].cvarstr):

			numrenderer += 1
			rendererlist[numrenderer].boxstr  = fulllist[idx].boxstr
			rendererlist[numrenderer].cvarstr = fulllist[idx].cvarstr

		idx += 1


	# The custom renderer. Must be known to the menu,
	# but nothing more. The display string is hard
	# coded below, the cvar is unknown.
	numrenderer += 1

def Renderer_GetRenderer()->int: # (returns static int)

	for i in range(numrenderer):

		if vid.vid_renderer.string == rendererlist[i].cvarstr:

			return i



	# Unknown renderer.
	return numrenderer

# --------

NUMMODES	= 33

class mode(object):

	def __init__(self, modenum=0, modestr=None):

		self.modenum = modenum #int
		self.modestr = modestr #char *

# Sorted by string.
modes = [ #static mode []
	mode( 0, "[320 240   ]" ),
	mode( 1, "[400 300   ]" ),
	mode( 2, "[512 384   ]" ),
	mode( 3, "[640 400   ]" ),
	mode( 4, "[640 480   ]" ),
	mode( 5, "[800 500   ]" ),
	mode( 6, "[800 600   ]" ),
	mode( 7, "[960 720   ]" ),
	mode( 8, "[1024 480  ]" ),
	mode( 9, "[1024 640  ]" ),
	mode( 10, "[1024 768  ]" ),
	mode( 11, "[1152 768  ]" ),
	mode( 12, "[1152 864  ]" ),
	mode( 13, "[1280 800  ]" ),
	mode( 14, "[1280 720  ]" ),
	mode( 15, "[1280 960  ]" ),
	mode( 16, "[1280 1024 ]" ),
	mode( 17, "[1366 768  ]" ),
	mode( 18, "[1440 900  ]" ),
	mode( 32, "[1600 900  ]" ),
	mode( 19, "[1600 1200 ]" ),
	mode( 20, "[1680 1050 ]" ),
	mode( 21, "[1920 1080 ]" ),
	mode( 22, "[1920 1200 ]" ),
	mode( 23, "[2048 1536 ]" ),
	mode( 24, "[2560 1080 ]" ),
	mode( 25, "[2560 1440 ]" ),
	mode( 26, "[2560 1600 ]" ),
	mode( 27, "[3440 1440 ]" ),
	mode( 28, "[3840 1600 ]" ),
	mode( 29, "[3840 2160 ]" ),
	mode( 30, "[4096 2160 ]" ),
	mode( 31, "[5120 2880 ]" )
]

def GetModePos(modenum: int)->int: #int (returns static int)

	for i in range(len(modes)): # ARRLEN(modes)

		if modes[i].modenum == modenum:

			return i



	return 3

# --------

GetCustomValue_last = None #static menulist_s *, in GetCustomValue
GetCustomValue_i = 0 #static int, in GetCustomValue

def GetCustomValue(list_: qmenu_h.menulist_s)->int: #menulist_s * (returns static int)

	global GetCustomValue_last, GetCustomValue_i

	if list_ is not GetCustomValue_last:

		GetCustomValue_last = list_
		GetCustomValue_i = list_.curvalue
		while True: # do { i++; } while (list->itemnames[i]);

			GetCustomValue_i += 1
			if not list_.itemnames[GetCustomValue_i]:
				break

		GetCustomValue_i -= 1


	return GetCustomValue_i

def ResetDefaults(unused): #void * (static)

	VID_MenuInit()

CUSTOM_MODE_NAME	= "[Custom    ]"
AUTO_MODE_NAME		= "[Auto      ]"

def CurrentRendererByCvar()->renderer_type: # (returns static renderer_type)

	if shared_c.Q_stricmp(vid.vid_renderer.string, "gl3") == 0 or shared_c.Q_stricmp(vid.vid_renderer.string, "gles3") == 0:

		return renderer_type.ref_gl3

	if shared_c.Q_stricmp(vid.vid_renderer.string, "gl1") == 0 or shared_c.Q_stricmp(vid.vid_renderer.string, "gles1") == 0:

		return renderer_type.ref_gl1

	if shared_c.Q_stricmp(vid.vid_renderer.string, "soft") == 0:

		return renderer_type.ref_soft

	if shared_c.Q_stricmp(vid.vid_renderer.string, "gl4") == 0:

		return renderer_type.ref_gl4

	if shared_c.Q_stricmp(vid.vid_renderer.string, "vk") == 0:

		return renderer_type.ref_vk

	return renderer_type.ref_custom

# See filter_names in VID_MenuInit()
gl_filter_list = [ #static const char *[]
	"GL_NEAREST",	# pixelated
	"GL_LINEAR",	# linear
	"GL_LINEAR_MIPMAP_NEAREST",	# standard
	"GL_LINEAR_MIPMAP_LINEAR"	# trilinear
]

gl_filter_list_len = len(gl_filter_list) #static const int, ARRLEN(gl_filter_list)

def ApplyFilter(unused): #void * (static)

	r = CurrentRendererByCvar()
	if r in (renderer_type.ref_gl3, renderer_type.ref_gl1):

		if s_filter_list.curvalue < gl_filter_list_len:

			cvar.Cvar_Set("gl_texturemode", gl_filter_list[s_filter_list.curvalue])


	elif r == renderer_type.ref_soft:

		if s_filter_list.curvalue == 0:

			cvar.Cvar_Set("sw_texture_filtering", "0")

		elif s_filter_list.curvalue == 1:

			cvar.Cvar_Set("sw_texture_filtering", "1")


	else:

		pass # avoid compiler warning

def ApplyChanges(unused): #void * (static)

	restart = False

	# Renderer
	if s_renderer_list.curvalue != Renderer_GetRenderer():

		# The custom renderer (the last known renderer) cannot be
		# set, because the menu doesn't know it's cvar value. TODO:
		# Hack something that it cannot be selected.
		if s_renderer_list.curvalue != numrenderer:

			cvar.Cvar_Set("vid_renderer", rendererlist[s_renderer_list.curvalue].cvarstr)
			restart = True



	# auto mode

	if s_mode_list.itemnames[s_mode_list.curvalue] == AUTO_MODE_NAME:

		cvar.Cvar_SetValue("r_mode", -2)
		restart = True

	elif s_mode_list.itemnames[s_mode_list.curvalue] == CUSTOM_MODE_NAME:

		cvar.Cvar_SetValue("r_mode", -1)
		restart = True

	else:

		cvar.Cvar_SetValue("r_mode", modes[s_mode_list.curvalue].modenum)
		restart = True


	# UI scaling
	if s_uiscale_list.curvalue == 0:

		cvar.Cvar_SetValue("r_hudscale", -1)

	elif s_uiscale_list.curvalue < GetCustomValue(s_uiscale_list):

		cvar.Cvar_SetValue("r_hudscale", s_uiscale_list.curvalue)


	if s_uiscale_list.curvalue != GetCustomValue(s_uiscale_list):

		cvar.Cvar_SetValue("r_consolescale", r_hudscale.value)
		cvar.Cvar_SetValue("r_menuscale", r_hudscale.value)
		cvar.Cvar_SetValue("crosshair_scale", r_hudscale.value)


	# Restarts automatically
	if vid.vid_fullscreen.value != s_fs_box.curvalue:

		cvar.Cvar_SetValue("vid_fullscreen", s_fs_box.curvalue)
		restart = True


	if s_fs_box.curvalue == 2:

		cvar.Cvar_SetValue("r_mode", -2.0)


	# vertical sync
	if r_vsync.value != s_vsync_list.curvalue:

		cvar.Cvar_SetValue("r_vsync", s_vsync_list.curvalue)
		restart = True


	if gl3_colorlight and gl3_colorlight.value != s_gl3_colorlight_list.curvalue:

		cvar.Cvar_SetValue("gl3_colorlight", s_gl3_colorlight_list.curvalue)


	if gl4_colorlight and gl4_colorlight.value != s_gl4_colorlight_list.curvalue:

		cvar.Cvar_SetValue("gl4_colorlight", s_gl4_colorlight_list.curvalue)


	if gl4_bloom and gl4_bloom.value != s_gl4_bloom_list.curvalue:

		cvar.Cvar_SetValue("r_bloom", s_gl4_bloom_list.curvalue)


	# anisotropic filtering
	if s_af_list.curvalue == 0:

		if gl_anisotropic.value != 0:

			cvar.Cvar_SetValue("r_anisotropic", 0)
			restart = True


	else:

		if gl_anisotropic.value != math.pow(2, s_af_list.curvalue):

			cvar.Cvar_SetValue("r_anisotropic", math.pow(2, s_af_list.curvalue))
			restart = True



	# multisample anti-aliasing
	if s_msaa_list.curvalue == 0:

		if gl_msaa_samples.value != 0:

			cvar.Cvar_SetValue("r_msaa_samples", 0)
			restart = True


	else:

		if gl_msaa_samples.value != math.pow(2, s_msaa_list.curvalue):

			cvar.Cvar_SetValue("r_msaa_samples", math.pow(2, s_msaa_list.curvalue))
			restart = True



	if restart:

		cmdparser.Cbuf_AddText("vid_restart\n")


	menu.M_ForceMenuOff()

def RestartNeededSDL3Msg(unused): #void * (static)

	if (
		# #ifdef USE_SDL3
		# #endif
		shared_c.Q_stricmp(vid.vid_renderer.string, "gles1") == 0 ):

		qmenu.Menu_SetStatusBar(s_opengl_menu, "apply required")

def RestartNeededForAllMsg(unused): #void * (static)

	qmenu.Menu_SetStatusBar(s_opengl_menu, "apply required")

# Renderer selection box.
# MAXRENDERERS + Custom + NULL.
VID_MenuInit_renderers = [None] * (MAXRENDERERS + 2) #static const char *[], in VID_MenuInit
# Generate mode list.
VID_MenuInit_resolutions = [None] * (NUMMODES + 3) #static const char *[], in VID_MenuInit

VID_MenuInit_uiscale_names = [ #static const char *[], in VID_MenuInit
	"auto",
	"1x",
	"2x",
	"3x",
	"4x",
	"5x",
	"6x",
	"custom",
	None
]

VID_MenuInit_onoff_names = [ #static const char *[], in VID_MenuInit
	"off",
	"on",
	None
]

VID_MenuInit_yesno_names = [ #static const char *[], in VID_MenuInit
	"no",
	"yes",
	None
]

VID_MenuInit_fullscreen_names = [ #static const char *[], in VID_MenuInit
	"no",
	"native fullscreen",
	"fullscreen window",
	None
]

VID_MenuInit_pow2_names = [ #static const char *[], in VID_MenuInit
	"off",
	"2x",
	"4x",
	"8x",
	"16x",
	None
]

# This must match 'gl_filter_list' values (except "custom")
VID_MenuInit_filter_names = [ #static const char *[], in VID_MenuInit
	"pixelated",
	"linear",
	"standard",
	"trilinear",
	"custom",
	None
]

def VID_MenuInit(): #void

	global r_mode, vid_displayindex, r_hudscale, r_consolescale, r_menuscale, crosshair_scale, \
		r_vsync, gl_anisotropic, gl_msaa_samples, gl3_colorlight, gl4_colorlight, gl4_bloom, vk_dynamic

	y = 30

	renderers = VID_MenuInit_renderers
	Renderer_FillRenderdef()

	for i in range(numrenderer):

		renderers[i] = rendererlist[i].boxstr


	renderers[numrenderer] = CUSTOM_MODE_NAME

	resolutions = VID_MenuInit_resolutions

	for i in range(NUMMODES):

		resolutions[i] = modes[i].modestr


	resolutions[NUMMODES] = AUTO_MODE_NAME
	resolutions[NUMMODES + 1] = CUSTOM_MODE_NAME
	resolutions[NUMMODES + 2] = None

	current_renderer = CurrentRendererByCvar() #const renderer_type

	uiscale_names = VID_MenuInit_uiscale_names
	onoff_names = VID_MenuInit_onoff_names
	yesno_names = VID_MenuInit_yesno_names
	fullscreen_names = VID_MenuInit_fullscreen_names
	pow2_names = VID_MenuInit_pow2_names
	filter_names = VID_MenuInit_filter_names

	if not r_mode:

		r_mode = cvar.Cvar_Get("r_mode", "4", 0)


	if not vid_displayindex:

		vid_displayindex = cvar.Cvar_Get("vid_displayindex", "0", shared.CVAR_ARCHIVE)


	if not r_hudscale:

		r_hudscale = cvar.Cvar_Get("r_hudscale", "-1", shared.CVAR_ARCHIVE)


	if not r_consolescale:

		r_consolescale = cvar.Cvar_Get("r_consolescale", "-1", shared.CVAR_ARCHIVE)


	if not r_menuscale:

		r_menuscale = cvar.Cvar_Get("r_menuscale", "-1", shared.CVAR_ARCHIVE)


	if not crosshair_scale:

		crosshair_scale = cvar.Cvar_Get("crosshair_scale", "-1", shared.CVAR_ARCHIVE)


	if not vid.vid_renderer:

		vid.vid_renderer = cvar.Cvar_Get("vid_renderer", "gl1", shared.CVAR_ARCHIVE)


	if not r_vsync:

		r_vsync = cvar.Cvar_Get("r_vsync", "1", shared.CVAR_ARCHIVE)


	if not gl_anisotropic:

		gl_anisotropic = cvar.Cvar_Get("r_anisotropic", "0", shared.CVAR_ARCHIVE)


	if not gl_msaa_samples:

		gl_msaa_samples = cvar.Cvar_Get("r_msaa_samples", "0", shared.CVAR_ARCHIVE)


	s_opengl_menu.x = int(vid.viddef.width * 0.50) # int x
	s_opengl_menu.nitems = 0
	s_opengl_menu.banner = "m_banner_video"

	s_renderer_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_renderer_list.generic.name = "renderer"
	s_renderer_list.generic.x = 0
	s_renderer_list.generic.y = y
	s_renderer_list.itemnames = renderers
	s_renderer_list.curvalue = Renderer_GetRenderer()

	s_mode_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_mode_list.generic.name = "video mode"
	s_mode_list.generic.x = 0
	y += 10; s_mode_list.generic.y = y
	s_mode_list.itemnames = resolutions

	if r_mode.value >= 0:

		s_mode_list.curvalue = int(GetModePos(r_mode.value)) # int curvalue

	elif r_mode.value == -2:

		# 'auto' is before 'custom'
		s_mode_list.curvalue = GetCustomValue(s_mode_list) - 1

	else:

		# 'custom'
		s_mode_list.curvalue = GetCustomValue(s_mode_list)


	s_brightness_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_brightness_slider.generic.name = "brightness"
	s_brightness_slider.generic.x = 0
	y += 10; s_brightness_slider.generic.y = y
	s_brightness_slider.generic.callback = RestartNeededSDL3Msg
	s_brightness_slider.cvar = "vid_gamma"
	s_brightness_slider.minvalue = 0.1
	s_brightness_slider.maxvalue = 2.0

	s_fov_slider.generic.type = qmenu_h.MTYPE_SLIDER
	s_fov_slider.generic.name = "field of view"
	s_fov_slider.generic.x = 0
	y += 10; s_fov_slider.generic.y = y
	s_fov_slider.cvar = "fov"
	s_fov_slider.minvalue = 60
	s_fov_slider.maxvalue = 120
	s_fov_slider.slidestep = 1
	s_fov_slider.printformat = "%.0f"

	if current_renderer == renderer_type.ref_gl3:

		s_gl3_intensity_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl3_intensity_slider.generic.name = "color intensity"
		s_gl3_intensity_slider.generic.x = 0
		y += 10; s_gl3_intensity_slider.generic.y = y
		s_gl3_intensity_slider.cvar = "gl3_intensity"
		s_gl3_intensity_slider.minvalue = 0.1
		s_gl3_intensity_slider.maxvalue = 5.0

		s_gl3_overbrightbits_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl3_overbrightbits_slider.generic.name = "overbrights"
		s_gl3_overbrightbits_slider.generic.x = 0
		y += 10; s_gl3_overbrightbits_slider.generic.y = y
		s_gl3_overbrightbits_slider.cvar = "gl3_overbrightbits"
		s_gl3_overbrightbits_slider.minvalue = 0.1
		s_gl3_overbrightbits_slider.maxvalue = 5.0

		gl3_colorlight = cvar.Cvar_Get("gl3_colorlight", "1", shared.CVAR_ARCHIVE)
		s_gl3_colorlight_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_gl3_colorlight_list.generic.name = "color light"
		s_gl3_colorlight_list.generic.x = 0
		y += 10; s_gl3_colorlight_list.generic.y = y
		s_gl3_colorlight_list.itemnames = yesno_names
		s_gl3_colorlight_list.curvalue = int(gl3_colorlight.value != 0)

	elif current_renderer == renderer_type.ref_gl4:

		s_gl4_intensity_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl4_intensity_slider.generic.name = "color intensity"
		s_gl4_intensity_slider.generic.x = 0
		y += 10; s_gl4_intensity_slider.generic.y = y
		s_gl4_intensity_slider.cvar = "gl4_intensity"
		s_gl4_intensity_slider.minvalue = 0.1
		s_gl4_intensity_slider.maxvalue = 5.0

		s_gl4_overbrightbits_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl4_overbrightbits_slider.generic.name = "overbrights"
		s_gl4_overbrightbits_slider.generic.x = 0
		y += 10; s_gl4_overbrightbits_slider.generic.y = y
		s_gl4_overbrightbits_slider.cvar = "gl4_overbrightbits"
		s_gl4_overbrightbits_slider.minvalue = 0.1
		s_gl4_overbrightbits_slider.maxvalue = 5.0

		gl4_colorlight = cvar.Cvar_Get("gl4_colorlight", "1", shared.CVAR_ARCHIVE)
		s_gl4_colorlight_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_gl4_colorlight_list.generic.name = "color light"
		s_gl4_colorlight_list.generic.x = 0
		y += 10; s_gl4_colorlight_list.generic.y = y
		s_gl4_colorlight_list.itemnames = yesno_names
		s_gl4_colorlight_list.curvalue = int(gl4_colorlight.value != 0)

		gl4_bloom = cvar.Cvar_Get("r_bloom", "1", shared.CVAR_ARCHIVE)
		s_gl4_bloom_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_gl4_bloom_list.generic.name = "bloom"
		s_gl4_bloom_list.generic.x = 0
		y += 10; s_gl4_bloom_list.generic.y = y
		s_gl4_bloom_list.itemnames = yesno_names
		s_gl4_bloom_list.curvalue = int(gl4_bloom.value != 0)

	elif current_renderer == renderer_type.ref_vk:

		s_vk_intensity_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_vk_intensity_slider.generic.name = "color intensity"
		s_vk_intensity_slider.generic.x = 0
		y += 10; s_vk_intensity_slider.generic.y = y
		s_vk_intensity_slider.cvar = "vk_intensity"
		s_vk_intensity_slider.minvalue = 0
		s_vk_intensity_slider.maxvalue = 5
		s_vk_intensity_slider.slidestep = 1
		s_vk_intensity_slider.printformat = "%.0f"

		s_vk_overbrightbits_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_vk_overbrightbits_slider.generic.name = "overbrights"
		s_vk_overbrightbits_slider.generic.x = 0
		y += 10; s_vk_overbrightbits_slider.generic.y = y
		s_vk_overbrightbits_slider.cvar = "vk_overbrightbits"
		s_vk_overbrightbits_slider.minvalue = 0.1
		s_vk_overbrightbits_slider.maxvalue = 5.0

		vk_dynamic = cvar.Cvar_Get("vk_dynamic", "1", shared.CVAR_ARCHIVE)
		s_vk_dynamic_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
		s_vk_dynamic_list.generic.name = "dynamic light"
		s_vk_dynamic_list.generic.x = 0
		y += 10; s_vk_dynamic_list.generic.y = y
		s_vk_dynamic_list.itemnames = yesno_names
		s_vk_dynamic_list.curvalue = int(vk_dynamic.value != 0)

	elif current_renderer == renderer_type.ref_gl1:

		gl3_colorlight = None
		s_gl1_intensity_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl1_intensity_slider.generic.name = "color intensity"
		s_gl1_intensity_slider.generic.x = 0
		y += 10; s_gl1_intensity_slider.generic.y = y
		s_gl1_intensity_slider.generic.callback = RestartNeededForAllMsg
		s_gl1_intensity_slider.cvar = "gl1_intensity"
		s_gl1_intensity_slider.minvalue = 1.0
		s_gl1_intensity_slider.maxvalue = 10.0

		s_gl1_overbrightbits_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl1_overbrightbits_slider.generic.name = "overbrights"
		s_gl1_overbrightbits_slider.generic.x = 0
		y += 10; s_gl1_overbrightbits_slider.generic.y = y
		s_gl1_overbrightbits_slider.cvar = "gl1_overbrightbits"
		s_gl1_overbrightbits_slider.minvalue = 0
		s_gl1_overbrightbits_slider.maxvalue = 2
		s_gl1_overbrightbits_slider.slidestep = 1
		s_gl1_overbrightbits_slider.printformat = "%.0f"

		s_gl1_minlight_slider.generic.type = qmenu_h.MTYPE_SLIDER
		s_gl1_minlight_slider.generic.name = "min. light level"
		s_gl1_minlight_slider.generic.x = 0
		y += 10; s_gl1_minlight_slider.generic.y = y
		s_gl1_minlight_slider.generic.callback = RestartNeededForAllMsg
		s_gl1_minlight_slider.cvar = "gl1_minlight"
		s_gl1_minlight_slider.minvalue = 0
		s_gl1_minlight_slider.maxvalue = 32
		s_gl1_minlight_slider.slidestep = 4
		s_gl1_minlight_slider.printformat = "%.0f"

	else:

		pass


	s_uiscale_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_uiscale_list.generic.name = "ui scale"
	s_uiscale_list.generic.x = 0
	y += 10; s_uiscale_list.generic.y = y
	s_uiscale_list.itemnames = uiscale_names
	if (r_hudscale.value != r_consolescale.value or
		r_hudscale.value != r_menuscale.value or
		r_hudscale.value != crosshair_scale.value):

		s_uiscale_list.curvalue = int(GetCustomValue(s_uiscale_list)) # int curvalue

	elif r_hudscale.value < 0:

		s_uiscale_list.curvalue = 0

	elif (r_hudscale.value > 0 and
			r_hudscale.value < GetCustomValue(s_uiscale_list) and
			r_hudscale.value == int(r_hudscale.value)):

		s_uiscale_list.curvalue = int(r_hudscale.value)

	else:

		s_uiscale_list.curvalue = int(GetCustomValue(s_uiscale_list)) # int curvalue


	s_fs_box.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_fs_box.generic.name = "fullscreen"
	s_fs_box.generic.x = 0
	y += 10; s_fs_box.generic.y = y
	s_fs_box.itemnames = fullscreen_names
	s_fs_box.curvalue = int(vid.vid_fullscreen.value)

	s_vsync_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_vsync_list.generic.name = "vertical sync"
	s_vsync_list.generic.x = 0
	y += 10; s_vsync_list.generic.y = y
	s_vsync_list.itemnames = yesno_names
	s_vsync_list.curvalue = int(r_vsync.value != 0)

	s_af_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_af_list.generic.name = "aniso filtering"
	s_af_list.generic.x = 0
	y += 10; s_af_list.generic.y = y
	s_af_list.itemnames = pow2_names
	s_af_list.curvalue = 0
	if gl_anisotropic.value:

		while True: # do { ... } while (...);

			s_af_list.curvalue += 1
			if not (pow2_names[s_af_list.curvalue] and
				math.pow(2, s_af_list.curvalue) <= gl_anisotropic.value):
				break

		s_af_list.curvalue -= 1


	s_msaa_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_msaa_list.generic.name = "multisampling"
	s_msaa_list.generic.x = 0
	y += 10; s_msaa_list.generic.y = y
	s_msaa_list.itemnames = pow2_names
	s_msaa_list.curvalue = 0
	if gl_msaa_samples.value:

		while True: # do { ... } while (...);

			s_msaa_list.curvalue += 1
			if not (pow2_names[s_msaa_list.curvalue] and
				math.pow(2, s_msaa_list.curvalue) <= gl_msaa_samples.value):
				break

		s_msaa_list.curvalue -= 1


	s_filter_list.generic.type = qmenu_h.MTYPE_SPINCONTROL
	s_filter_list.generic.name = "texture filter"
	s_filter_list.curvalue = 0
	s_filter_list.generic.callback = ApplyFilter
	s_filter_list.generic.x = 0

	filter_ = None #const char*
	mode_ = 0

	if current_renderer in (renderer_type.ref_gl3, renderer_type.ref_gl1):

		y += 10; s_filter_list.generic.y = y
		s_filter_list.itemnames = filter_names

		filter_ = cvar.Cvar_VariableString("gl_texturemode")
		mode_ = gl_filter_list_len # "custom" by default

		for i in range(gl_filter_list_len):

			if shared_c.Q_stricmp(filter_, gl_filter_list[i]) == 0:

				mode_ = i
				break



	elif current_renderer == renderer_type.ref_soft:

		y += 10; s_filter_list.generic.y = y
		s_filter_list.itemnames = onoff_names

		filter_ = cvar.Cvar_VariableString("sw_texture_filtering")
		mode_ = 0

		if shared_c.Q_stricmp(filter_, "1") == 0:

			mode_ = 1


	else:

		pass


	s_filter_list.curvalue = mode_

	s_defaults_action.generic.type = qmenu_h.MTYPE_ACTION
	s_defaults_action.generic.name = "reset to default"
	s_defaults_action.generic.x = 0
	y += 20; s_defaults_action.generic.y = y
	s_defaults_action.generic.callback = ResetDefaults

	s_apply_action.generic.type = qmenu_h.MTYPE_ACTION
	s_apply_action.generic.name = "apply"
	s_apply_action.generic.x = 0
	y += 10; s_apply_action.generic.y = y
	s_apply_action.generic.callback = ApplyChanges

	qmenu.Menu_AddItem(s_opengl_menu, s_renderer_list)
	qmenu.Menu_AddItem(s_opengl_menu, s_mode_list)

	qmenu.Menu_AddItem(s_opengl_menu, s_brightness_slider)
	qmenu.Menu_AddItem(s_opengl_menu, s_fov_slider)
	if current_renderer == renderer_type.ref_gl3:

		qmenu.Menu_AddItem(s_opengl_menu, s_gl3_intensity_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl3_overbrightbits_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl3_colorlight_list)

	elif current_renderer == renderer_type.ref_gl4:

		qmenu.Menu_AddItem(s_opengl_menu, s_gl4_intensity_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl4_overbrightbits_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl4_colorlight_list)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl4_bloom_list)

	elif current_renderer == renderer_type.ref_vk:

		qmenu.Menu_AddItem(s_opengl_menu, s_vk_intensity_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_vk_overbrightbits_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_vk_dynamic_list)

	elif current_renderer == renderer_type.ref_gl1:

		qmenu.Menu_AddItem(s_opengl_menu, s_gl1_intensity_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl1_overbrightbits_slider)
		qmenu.Menu_AddItem(s_opengl_menu, s_gl1_minlight_slider)

	else:

		pass

	qmenu.Menu_AddItem(s_opengl_menu, s_uiscale_list)
	qmenu.Menu_AddItem(s_opengl_menu, s_fs_box)
	qmenu.Menu_AddItem(s_opengl_menu, s_vsync_list)
	qmenu.Menu_AddItem(s_opengl_menu, s_af_list)
	qmenu.Menu_AddItem(s_opengl_menu, s_msaa_list)
	if current_renderer == renderer_type.ref_gl3 or current_renderer == renderer_type.ref_gl1 or current_renderer == renderer_type.ref_soft:

		qmenu.Menu_AddItem(s_opengl_menu, s_filter_list)

	qmenu.Menu_AddItem(s_opengl_menu, s_defaults_action)
	qmenu.Menu_AddItem(s_opengl_menu, s_apply_action)

	qmenu.Menu_SetStatusBar(s_opengl_menu, None)
	qmenu.Menu_Center(s_opengl_menu)
	s_opengl_menu.x -= 8

"""
 * VIDEO MENU
"""
def M_Menu_Video_f(): #void

	VID_MenuInit()
	s_opengl_menu.draw = menu.Default_MenuDraw
	s_opengl_menu.key  = menu.Default_MenuKey

	menu.M_PushMenu(s_opengl_menu)
