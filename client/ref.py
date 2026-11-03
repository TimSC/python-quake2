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
import copy
import numpy as np
"""
#ifndef __REF_H
#define __REF_H

#include "../qcommon/qcommon.h"
"""
MAX_DLIGHTS		= 32
MAX_ENTITIES	= 128
MAX_PARTICLES	= 4096
MAX_LIGHTSTYLES	= 256

POWERSUIT_SCALE		= 4.0
"""
#define POWERSUIT_SCALE		4.0F

#define SHELL_RED_COLOR		0xF2
#define SHELL_GREEN_COLOR	0xD0
#define SHELL_BLUE_COLOR	0xF3

#define SHELL_RG_COLOR		0xDC
//#define SHELL_RB_COLOR		0x86
#define SHELL_RB_COLOR		0x68
#define SHELL_BG_COLOR		0x78

//ROGUE
#define SHELL_DOUBLE_COLOR	0xDF // 223
#define	SHELL_HALF_DAM_COLOR	0x90
#define SHELL_CYAN_COLOR	0x72
//ROGUE

#define SHELL_WHITE_COLOR	0xD7
"""
class entity_t(object):

	def __init__(self):


		self.model = None # struct model_s		*;			// opaque type outside refresh

		self.angles = np.zeros((3,), dtype=np.float32) # float[3];
		"""

		/*
		** most recent data
		*/
		"""
		self.origin = np.zeros((3,), dtype=np.float32) #float [3], also used as RF_BEAM's "from"
		self.frame = 0

		# previous data for lerping
		self.oldorigin = np.zeros((3,), dtype=np.float32) #float [3], also used as RF_BEAM's "to"
		self.oldframe = 0

		# misc
		self.backlerp = 0.0
		self.skinnum = 0
		self.lightstyle = 0
		self.alpha = 1.0
		"""
		int					frame;			// also used as RF_BEAM's diameter

		/*
		** previous data for lerping
		*/
		float				oldorigin[3];	// also used as RF_BEAM's "to"
		int					oldframe;

		/*
		** misc
		*/
		float	backlerp;				// 0.0 = current, 1.0 = old
		int		skinnum;				// also used as RF_BEAM's palette index

		int		lightstyle;				// for flashing entities
		float	alpha;					// ignore if RF_TRANSLUCENT isn't set

		"""
		self.skin = None # struct image_s	*, NULL for inline skin
		self.flags = 0 # int

	def copy(self):
		# struct assignment, arrays are copied but pointers (model, skin) stay shared.
		# copy.deepcopy would also copy the whole model.
		out = copy.copy(self)
		out.angles = self.angles.copy()
		out.origin = self.origin.copy()
		out.oldorigin = self.oldorigin.copy()
		return out


"""
#define ENTITY_FLAGS  68
"""
class dlight_t(object):

	def __init__(self):
		self.origin = np.zeros((3,), dtype=np.float32) # vec3_t
		self.color = np.zeros((3,), dtype=np.float32) # vec3_t
		self.intensity = 0.0 # float

class particle_t(object):

	def __init__(self):
		self.origin = np.zeros((3,), dtype=np.float32) # vec3_t
		self.color = 0 # int
		self.alpha = 0.0 # float

class lightstyle_t(object):

	def __init__(self):
		self.rgb = np.zeros((3,), dtype=np.float32) # float[3], 0.0 - 2.0
		self.white = 0.0 # float, highest of rgb

class refdef_t(object):

	def __init__(self):


		self.x = 0 
		self.y = 0 
		self.width = 0 
		self.height = 0 # int, in virtual screen coordinates
		self.fov_x = 0.0 #float
		self.fov_y = 0.0

		self.vieworg = np.zeros((3,), dtype=np.float32) # float [3]
		self.viewangles = np.zeros((3,), dtype=np.float32) #float [3]

		self.blend = np.zeros((4,), dtype=np.float32) #float[4], rgba 0-1 full screen blend

		self.time = None 				# float, time is uesed to auto animate
		self.rdflags = 0 				# int, RDF_UNDERWATER, etc

		self.areabits = None			# byte *, if not NULL, only areas with set bits will be drawn

		self.lightstyles = None			# lightstyle_t *, [MAX_LIGHTSTYLES]

		self.num_entities = 0			# int
		self.entities = None			# entity_t *

		self.num_dlights = 0			# int
		self.dlights = None				# dlight_t *

		self.num_particles = 0			# int
		self.particles = None			# particle_t *

	def copy(self):
		# struct assignment, arrays are copied but pointers (entities, lightstyles...) stay shared.
		# copy.deepcopy would also copy every entity model and the world.
		out = copy.copy(self)
		out.vieworg = self.vieworg.copy()
		out.viewangles = self.viewangles.copy()
		out.blend = self.blend.copy()
		return out


API_VERSION = 3

#
# these are the functions exported by the refresh module
#
class refexport_t(object):

	def __init__(self):

		# if api_version is different, the dll cannot be used
		self.api_version = None #int

		# called when the library is loaded
		self.Init = None #qboolean (*) ( void *hinstance, void *wndproc )

		# called before the library is unloaded
		self.Shutdown = None #void (*) (void)

		# All data that will be used in a level should be
		# registered before rendering any frames to prevent disk hits,
		# but they can still be registered at a later time
		# if necessary.
		#
		# EndRegistration will free any remaining data that wasn't registered.
		# Any model_s or skin_s pointers from before the BeginRegistration
		# are no longer valid after EndRegistration.
		#
		# Skins and images need to be differentiated, because skins
		# are flood filled to eliminate mip map edge errors, and pics have
		# an implicit "pics/" prepended to the name. (a pic name that starts with a
		# slash will not use the "pics/" prefix or the ".pcx" postfix)
		self.BeginRegistration = None #void (*) (char *map)
		self.RegisterModel = None #struct model_s *(*) (char *name)
		self.RegisterSkin = None #struct image_s *(*) (char *name)
		self.RegisterPic = None #struct image_s *(*) (char *name)
		self.SetSky = None #void	(*) (char *name, float rotate, vec3_t axis)
		self.EndRegistration = None #void (*) (void)

		self.RenderFrame = None #void (*) (refdef_t *fd)

		self.DrawGetPicSize = None #void (*) (int *w, int *h, char *name)	# will return 0 0 if not found
		self.DrawPic = None #void (*) (int x, int y, char *name)
		self.DrawStretchPic = None #void (*) (int x, int y, int w, int h, char *name)
		self.DrawChar = None #void (*) (int x, int y, int c)
		self.DrawTileClear = None #void (*) (int x, int y, int w, int h, char *name)
		self.DrawFill = None #void (*) (int x, int y, int w, int h, int c)
		self.DrawFadeScreen = None #void (*) (void)

		# Draw images for cinematic rendering (which can have a different palette). Note that calls
		self.DrawStretchRaw = None #void (*) (int x, int y, int w, int h, int cols, int rows, byte *data)

		#
		# video mode and refresh state management entry points
		#
		self.CinematicSetPalette = None #void (*)( const unsigned char *palette)	# NULL = game palette
		self.BeginFrame = None #void (*)( float camera_separation )
		self.EndFrame = None #void (*) (void)

		self.AppActivate = None #void (*)( qboolean activate )



#
# these are the functions imported by the refresh module
#
class refimport_t(object):
	
	def __init__(self):

		self.Sys_Error = None #void (*) (int err_level, char *str, ...)

		self.Cmd_AddCommand = None #void (*) (char *name, void(*cmd)(void))
		self.Cmd_RemoveCommand = None #void (*) (char *name)
		self.Cmd_Argc = None #int (*) (void)
		self.Cmd_Argv = None #char *(*) (int i)
		self.Cmd_ExecuteText = None #void (*) (int exec_when, char *text)

		self.Con_Printf = None #void (*) (int print_level, char *str, ...)

		# files will be memory mapped read only
		# the returned buffer may be part of a larger pak file,
		# or a discrete file from anywhere in the quake search path
		# a -1 return means the file does not exist
		# NULL can be passed for buf to just determine existance
		self.FS_LoadFile = None #int (*) (char *name, void **buf)
		self.FS_FreeFile = None #void (*) (void *buf)

		# gamedir will be the current directory that generated
		# files should be stored to, ie: "f:\quake\id1"
		self.FS_Gamedir = None #char *(*) (void)

		self.Cvar_Get = None #cvar_t *(*) (char *name, char *value, int flags)
		self.Cvar_Set = None #cvar_t *(*)( char *name, char *value )
		self.Cvar_SetValue = None #void (*)( char *name, float value )

		self.Vid_GetModeInfo = None #qboolean (*)( int *width, int *height, int mode )
		self.Vid_MenuInit = None #void (*)( void )
		self.Vid_NewWindow = None #void (*)( int width, int height )

"""
// this is the only function actually exported at the linker level
typedef	refexport_t	(*GetRefAPI_t) (refimport_t);

#endif // __REF_H
"""
