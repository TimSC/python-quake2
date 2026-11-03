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
import OpenGL.GL as GL
from ref_gl import gl_image, gl_rmain
from linux import qgl_linux, q_shlinux
from game import q_shared
"""
// r_misc.c

#include "gl_local.h"

/*
==================
R_InitParticleTexture
==================
*/
"""
dottexture = [ #byte[8][8]
	[0,0,0,0,0,0,0,0],
	[0,0,1,1,0,0,0,0],
	[0,1,1,1,1,0,0,0],
	[0,1,1,1,1,0,0,0],
	[0,0,1,1,0,0,0,0],
	[0,0,0,0,0,0,0,0],
	[0,0,0,0,0,0,0,0],
	[0,0,0,0,0,0,0,0],
]

def R_InitParticleTexture ():

	#int		x,y;
	#byte	data[8][8][4];
	data = bytearray(8*8*4)

	#
	# particle texture
	#
	for x in range(8):
	
		for y in range(8):
		
			data[(y*8+x)*4+0] = 255
			data[(y*8+x)*4+1] = 255
			data[(y*8+x)*4+2] = 255
			data[(y*8+x)*4+3] = dottexture[x][y]*255
		
	gl_rmain.r_particletexture = gl_image.GL_LoadPic ("***particle***", data, 8, 8, gl_image.imagetype_t.it_sprite, 32)

	#
	# also use this for bad textures, but without alpha
	#
	data = bytearray(8*8*4)
	for x in range(8):
	
		for y in range(8):
		
			data[(y*8+x)*4+0] = dottexture[x&3][y&3]*255
			data[(y*8+x)*4+1] = 0 # dottexture[x&3][y&3]*255;
			data[(y*8+x)*4+2] = 0 #dottexture[x&3][y&3]*255;
			data[(y*8+x)*4+3] = 255
		
	gl_rmain.r_notexture = gl_image.GL_LoadPic ("***r_notexture***", data, 8, 8, gl_image.imagetype_t.it_wall, 32)

"""


/* 
============================================================================== 
 
						SCREEN SHOTS 
 
============================================================================== 
*/ 

typedef struct _TargaHeader {
	unsigned char 	id_length, colormap_type, image_type;
	unsigned short	colormap_index, colormap_length;
	unsigned char	colormap_size;
	unsigned short	x_origin, y_origin, width, height;
	unsigned char	pixel_size, attributes;
} TargaHeader;


"""
""" 
================== 
GL_ScreenShot_f
================== 
"""
def GL_ScreenShot_f ():

	"""
	byte		*buffer;
	char		picname[80]; 
	char		checkname[MAX_OSPATH];
	int			i, c, temp;
	FILE		*f;
	"""
	vid = gl_rmain.vid

	# create the scrnshots directory if it doesn't exist
	checkname = "{}/scrnshot".format(gl_rmain.ri.FS_Gamedir())
	q_shlinux.Sys_Mkdir (checkname)

	# 
	# find a file name to save it to 
	# 
	picname = list("quake00.tga")

	for i in range(101):
	
		if i == 100:
			break
		picname[5] = chr(i//10 + ord('0'))
		picname[6] = chr(i%10 + ord('0'))
		checkname = "{}/scrnshot/{}".format(gl_rmain.ri.FS_Gamedir(), "".join(picname))
		if not os.path.exists(checkname): # f = fopen (checkname, "rb"); if (!f)
			break	# file doesn't exist
	
	if i == 100:
	
		gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "SCR_ScreenShot_f: Couldn't create a file\n")
		return
	
	buffer = bytearray(vid.width*vid.height*3 + 18) # malloc and memset (buffer, 0, 18);
	buffer[2] = 2		# uncompressed type
	buffer[12] = vid.width&255
	buffer[13] = vid.width>>8
	buffer[14] = vid.height&255
	buffer[15] = vid.height>>8
	buffer[16] = 24	# pixel size

	GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1) # rows are not padded in the C buffer
	buffer[18:] = GL.glReadPixels (0, 0, vid.width, vid.height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)

	# swap rgb to bgr
	c = 18+vid.width*vid.height*3
	buffer[18:c:3], buffer[20:c:3] = buffer[20:c:3], buffer[18:c:3]

	with open (checkname, "wb") as f:
		f.write (buffer[:c])

	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "Wrote {}\n".format("".join(picname)))
"""

/*
** GL_Strings_f
*/
"""
def GL_Strings_f( ):

	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "GL_VENDOR: {}\n".format(gl_rmain.gl_config.vendor_string) )
	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "GL_RENDERER: {}\n".format(gl_rmain.gl_config.renderer_string) )
	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "GL_VERSION: {}\n".format(gl_rmain.gl_config.version_string) )
	gl_rmain.ri.Con_Printf (q_shared.PRINT_ALL, "GL_EXTENSIONS: {}\n".format(gl_rmain.gl_config.extensions) )


"""
/*
** GL_SetDefaultState
*/
"""
def GL_SetDefaultState( ):
	

	GL.glClearColor (1,0, 0.5 , 0.5)
	GL.glCullFace(GL.GL_FRONT)
	GL.glEnable(GL.GL_TEXTURE_2D)

	GL.glEnable(GL.GL_ALPHA_TEST)
	GL.glAlphaFunc(GL.GL_GREATER, 0.666)

	GL.glDisable (GL.GL_DEPTH_TEST)
	GL.glDisable (GL.GL_CULL_FACE)
	GL.glDisable (GL.GL_BLEND)

	GL.glColor4f (1,1,1,1)

	GL.glPolygonMode (GL.GL_FRONT_AND_BACK, GL.GL_FILL)
	GL.glShadeModel (GL.GL_FLAT)

	gl_image.GL_TextureMode( gl_rmain.gl_texturemode.string )
	gl_image.GL_TextureAlphaMode( gl_rmain.gl_texturealphamode.string )
	gl_image.GL_TextureSolidMode( gl_rmain.gl_texturesolidmode.string )
	
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, gl_image.gl_filter_min)
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, gl_image.gl_filter_max)

	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)

	GL.glBlendFunc (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

	gl_image.GL_TexEnv( GL.GL_REPLACE )

	if qgl_linux.qglPointParameterfEXT:

		#float attenuations[3];
		attenuations = [0.0, 0.0, 0.0]

		attenuations[0] = gl_rmain.gl_particle_att_a.value
		attenuations[1] = gl_rmain.gl_particle_att_b.value
		attenuations[2] = gl_rmain.gl_particle_att_c.value

		GL.glEnable( GL.GL_POINT_SMOOTH )
		GL.glPointParameterf( GL.GL_POINT_SIZE_MIN, gl_rmain.gl_particle_min_size.value ) # GL_POINT_SIZE_MIN_EXT
		GL.glPointParameterf( GL.GL_POINT_SIZE_MAX, gl_rmain.gl_particle_max_size.value ) # GL_POINT_SIZE_MAX_EXT
		GL.glPointParameterfv( GL.GL_POINT_DISTANCE_ATTENUATION, attenuations ) # GL_DISTANCE_ATTENUATION_EXT
	"""
	if ( qglColorTableEXT && gl_ext_palettedtexture->value )
	{
		qglEnable( GL_SHARED_TEXTURE_PALETTE_EXT );

		GL_SetTexturePalette( d_8to24table );
	}

	GL_UpdateSwapInterval();
}
"""
def GL_UpdateSwapInterval():
	gl_swapinterval = getattr(gl_rmain, "gl_swapinterval", None)
	if gl_swapinterval is None:
		return
	if not gl_swapinterval.modified:
		return

	gl_swapinterval.modified = False
	if gl_rmain.gl_state.stereo_enabled:
		return

	# No platform-specific swap interval hooks in this port.
	return

