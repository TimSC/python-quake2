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

import struct
import OpenGL.GL as GL
from PIL import Image
from client.refresh.gl1 import gl1_main, gl1_image, gl1_scrap


"""
** Scrap_Update
"""
def Scrap_Update ():

	"""
	qboolean default2Dnolerp;
	int texnum;
	"""

	# r_2D_unfiltered not ported; default 0
	default2Dnolerp = False

	for texnum in range(gl1_scrap.MAX_SCRAPS):
		scrap_texels = gl1_scrap.Scrap_Upload(texnum)
		if scrap_texels is not None:
			gl1_image.R_Bind(gl1_image.TEXNUM_SCRAPS + texnum)
			gl1_image.R_Upload32(scrap_texels, gl1_scrap.SCRAP_WIDTH, gl1_scrap.SCRAP_HEIGHT, False)
			if default2Dnolerp or (texnum < gl1_scrap.MAX_SCRAPS_NOLERP):
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
			else:
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
				GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)


pass
from linux import qgl_linux
from common.header import shared
"""
// draw.c

#include "gl_local.h"
"""
draw_chars = None #image_t *
"""
# scrap code lives in gl1_scrap.py


/*
===============
Draw_InitLocal
===============
"""
def Draw_InitLocal ():
	global draw_chars

	# load console characters (don't bilerp characters)
	draw_chars = gl1_image.R_FindImage ("pics/conchars.pcx", gl1_image.imagetype_t.it_pic)
	gl1_image.R_Bind( draw_chars.texnum )
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

"""
================
Draw_Char

Draws one 8*8 graphics character with 0 being transparent.
It can be clipped to the top of the screen to allow the console to be
smoothly scrolled off.
================
"""
def Draw_Char (x, y, num): #int, int, int

	#int				row, col;
	#float			frow, fcol, size;

	num &= 255
	if (num&127) == 32:
		return		# space

	if y <= -8:
		return			# totally off screen

	row = num>>4
	col = num&15

	frow = row*0.0625
	fcol = col*0.0625
	size = 0.0625

	#Q2PORT: conchars may live in the scrap (a 128x128 block of the scrap
	#texture), so map the char UV through the scrap span like the C does
	#(sl + fcol*(sh-sl)).  For a nonscrap texture sl/sh are 0/1 so this is
	#a no-op.
	fu  = draw_chars.sl  + fcol       * (draw_chars.sh - draw_chars.sl)
	fu2 = draw_chars.sl  + (fcol+size)* (draw_chars.sh - draw_chars.sl)
	fv  = draw_chars.tl  + frow       * (draw_chars.th - draw_chars.tl)
	fv2 = draw_chars.tl  + (frow+size)* (draw_chars.th - draw_chars.tl)

	gl1_image.R_Bind (draw_chars.texnum)

	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (fu, fv)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f (fu2, fv)
	GL.glVertex2f (x+8, y)
	GL.glTexCoord2f (fu2, fv2)
	GL.glVertex2f (x+8, y+8)
	GL.glTexCoord2f (fu, fv2)
	GL.glVertex2f (x, y+8)
	GL.glEnd ()

"""
================
RDraw_CharScaled

Q2PORT: Yamagi's RDraw_CharScaled (gl1_draw.c), in id's immediate mode
until the renderer is ported (group 15).
================
"""
def RDraw_CharScaled (x, y, num, scale): #int, int, int, float

	#int row, col;
	#float frow, fcol, size, scaledSize;

	num &= 255

	if (num & 127) == 32:

		return # space


	if y <= -8:

		return # totally off screen


	row = num >> 4
	col = num & 15

	frow = row * 0.0625
	fcol = col * 0.0625
	size = 0.0625

	scaledSize = 8 * scale

	#Q2PORT: map the char UV through the scrap span (see Draw_Char).
	fu  = draw_chars.sl  + fcol        * (draw_chars.sh - draw_chars.sl)
	fu2 = draw_chars.sl  + (fcol+size) * (draw_chars.sh - draw_chars.sl)
	fv  = draw_chars.tl  + frow        * (draw_chars.th - draw_chars.tl)
	fv2 = draw_chars.tl  + (frow+size) * (draw_chars.th - draw_chars.tl)

	gl1_image.R_Bind (draw_chars.texnum)

	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (fu, fv)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f (fu2, fv)
	GL.glVertex2f (x + scaledSize, y)
	GL.glTexCoord2f (fu2, fv2)
	GL.glVertex2f (x + scaledSize, y + scaledSize)
	GL.glTexCoord2f (fu, fv2)
	GL.glVertex2f (x, y + scaledSize)
	GL.glEnd ()

"""
=============
RDraw_PicScaled

Q2PORT: Yamagi's RDraw_PicScaled and RDraw_PicScaledCol (gl1_draw.c), in
id's immediate mode until the renderer is ported (group 15).
=============
"""
def RDraw_PicScaled (x, y, pic, factor): #int, int, char *, float

	RDraw_PicScaledCol (x, y, pic, factor, None)

def RDraw_PicScaledCol (x, y, pic, factor, color): #int, int, char *, float, const float[3]

	#image_t *gl;

	gl = RDraw_FindPic (pic)
	if gl is None:

		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "Can't find pic: {}\n".format(pic))
		return


	Scrap_Update ()


	if color is not None:

		GL.glTexEnvf (GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_MODULATE)
		GL.glColor4f (color[0], color[1], color[2], 1)


	gl1_image.R_Bind (gl.texnum)
	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (gl.sl, gl.tl)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f (gl.sh, gl.tl)
	GL.glVertex2f (x + gl.width * factor, y)
	GL.glTexCoord2f (gl.sh, gl.th)
	GL.glVertex2f (x + gl.width * factor, y + gl.height * factor)
	GL.glTexCoord2f (gl.sl, gl.th)
	GL.glVertex2f (x, y + gl.height * factor)
	GL.glEnd ()

	if color is not None:

		GL.glColor4f (1, 1, 1, 1)
		GL.glTexEnvf (GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_REPLACE)


"""
=============
RDraw_FindPic
=============
"""
def RDraw_FindPic (name): #char * (returns image_t	*)

	#image_t *gl;
	#char	fullname[MAX_QPATH];

	if name[0] != '/' and name[0] != '\\':
	
		fullname = "pics/{}.pcx".format(name)
		gl = gl1_image.R_FindImage (fullname, gl1_image.imagetype_t.it_pic)
	
	else:
		gl = gl1_image.R_FindImage (name[1:], gl1_image.imagetype_t.it_pic)

	return gl

"""
=============
RDraw_GetPicSize
=============
"""
def RDraw_GetPicSize (pic): #int *, int *, char *

	gl = RDraw_FindPic (pic)
	if gl is None:
	
		return -1, -1
	
	return gl.width, gl.height

"""
=============
RDraw_StretchPic
=============
"""
def RDraw_StretchPic (x, y, w, h, pic): #int, int, int, int, char *

	#image_t *gl;

	gl = RDraw_FindPic (pic)
	if gl is None:
	
		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "Can't find pic: {}\n".format(pic))
		return
	

	Scrap_Update ()
	
	#if ( ( ( gl_config.renderer == GL_RENDERER_MCD ) || ( gl_config.renderer & GL_RENDERER_RENDITION ) ) && !gl->has_alpha)
	#	qglDisable (GL_ALPHA_TEST);

	gl1_image.R_Bind (gl.texnum)
	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (gl.sl, gl.tl)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f (gl.sh, gl.tl)
	GL.glVertex2f (x+w, y)
	GL.glTexCoord2f (gl.sh, gl.th)
	GL.glVertex2f (x+w, y+h)
	GL.glTexCoord2f (gl.sl, gl.th)
	GL.glVertex2f (x, y+h)
	GL.glEnd ()

	#if ( ( ( gl_config.renderer == GL_RENDERER_MCD ) || ( gl_config.renderer & GL_RENDERER_RENDITION ) ) && !gl->has_alpha)
	#	qglEnable (GL_ALPHA_TEST);

"""
=============
Draw_Pic
=============
"""
def Draw_Pic (x, y, pic): #int, int, char *

	#image_t *gl;

	gl = RDraw_FindPic (pic)
	if gl is None:
	
		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "Can't find pic: {}\n".format(pic))
		return
	
	Scrap_Update ()

	#if ( ( ( gl_config.renderer == GL_RENDERER_MCD ) || ( gl_config.renderer & GL_RENDERER_RENDITION ) ) && !gl->has_alpha)
	#	qglDisable (GL_ALPHA_TEST);

	gl1_image.R_Bind (gl.texnum)
	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (gl.sl, gl.tl)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f (gl.sh, gl.tl)
	GL.glVertex2f (x+gl.width, y)
	GL.glTexCoord2f (gl.sh, gl.th)
	GL.glVertex2f (x+gl.width, y+gl.height)
	GL.glTexCoord2f (gl.sl, gl.th)
	GL.glVertex2f (x, y+gl.height)
	GL.glEnd ()

	#if ( ( ( gl_config.renderer == GL_RENDERER_MCD ) || ( gl_config.renderer & GL_RENDERER_RENDITION ) )  && !gl->has_alpha)
	#	qglEnable (GL_ALPHA_TEST);


"""
=============
RDraw_TileClear

This repeats a 64*64 tile graphic to fill the screen around a sized down
refresh window.
=============
"""
def RDraw_TileClear (x, y, w, h, pic): #int, int, int, int, char *
	
	#image_t	*image;

	image = RDraw_FindPic (pic)
	if image is None:
	
		gl1_main.ri.Con_Printf (shared.PRINT_ALL, "Can't find pic: {}\n".format(pic))
		return
	
	if  ( ( gl1_main.gl_config.renderer == gl1_main.GL_RENDERER_MCD ) or ( gl1_main.gl_config.renderer & gl1_main.GL_RENDERER_RENDITION ) )  and not image.has_alpha:
		GL.glDisable (GL.GL_ALPHA_TEST)

	gl1_image.R_Bind (image.texnum)
	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (x/64.0, y/64.0)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f ( (x+w)/64.0, y/64.0)
	GL.glVertex2f (x+w, y)
	GL.glTexCoord2f ( (x+w)/64.0, (y+h)/64.0)
	GL.glVertex2f (x+w, y+h)
	GL.glTexCoord2f ( x/64.0, (y+h)/64.0 )
	GL.glVertex2f (x, y+h)
	GL.glEnd ()

	if ( ( gl1_main.gl_config.renderer == gl1_main.GL_RENDERER_MCD ) or ( gl1_main.gl_config.renderer & gl1_main.GL_RENDERER_RENDITION ) )  and not image.has_alpha:
		GL.glEnable (GL.GL_ALPHA_TEST)



"""
=============
RDraw_Fill

Fills a box of pixels with a single color
=============
"""
def RDraw_Fill (x, y, w, h, c): #int, int, int, int, int

	"""
	union
	{
		unsigned	c;
		byte		v[4];
	} color;
	"""

	if c > 255:
		gl1_main.ri.Sys_Error (shared.ERR_FATAL, "RDraw_Fill: bad color")

	GL.glDisable (GL.GL_TEXTURE_2D)

	color = gl1_image.d_8to24table[c]

	GL.glColor3f (color[0]/255.0,
		color[1]/255.0,
		color[2]/255.0)

	GL.glBegin (GL.GL_QUADS)

	GL.glVertex2f (x,y)
	GL.glVertex2f (x+w, y)
	GL.glVertex2f (x+w, y+h)
	GL.glVertex2f (x, y+h)

	GL.glEnd ()
	GL.glColor3f (1,1,1)
	GL.glEnable (GL.GL_TEXTURE_2D)


"""
//=============================================================================

/*
================
RDraw_FadeScreen

================
"""
def RDraw_FadeScreen ():

	GL.glEnable(GL.GL_BLEND)
	GL.glDisable(GL.GL_TEXTURE_2D)
	GL.glColor4f(0, 0, 0, 0.8)
	GL.glBegin(GL.GL_QUADS)

	GL.glVertex2f(0, 0)
	GL.glVertex2f(gl1_main.vid.width, 0)
	GL.glVertex2f(gl1_main.vid.width, gl1_main.vid.height)
	GL.glVertex2f(0, gl1_main.vid.height)

	GL.glEnd()
	GL.glColor4f(1, 1, 1, 1)
	GL.glEnable(GL.GL_TEXTURE_2D)
	GL.glDisable(GL.GL_BLEND)

"""
//====================================================================


/*
=============
RDraw_StretchRaw
=============
*/
extern unsigned	r_rawpalette[256];
"""
def RDraw_StretchRaw (x, y, w, h, cols, rows, data): #int, int, int, int, int, int, byte *

	"""
	unsigned	image32[256*256];
	unsigned char image8[256*256];
	int			i, j, trows;
	byte		*source;
	int			frac, fracstep;
	float		hscale;
	int			row;
	float		t;
	"""
	image32 = bytearray(256*256*4)

	gl1_image.R_Bind (0)

	if rows<=256:
	
		hscale = 1
		trows = rows
	
	else:
	
		hscale = rows/256.0
		trows = 256

	t = rows*hscale / 256
	
	if not qgl_linux.qglColorTableEXT:

		raw_palette_buff = bytearray()
		for col in gl1_main.r_rawpalette:
			raw_palette_buff += struct.pack("<L", col)[:3]	

		img = Image.frombuffer("P", (cols, rows), data, 'raw', 'P', 0, 1)
		img.putpalette(raw_palette_buff)
		img = img.resize((256, 256))
		img = img.convert("RGBA")

		GL.glTexImage2D (GL.GL_TEXTURE_2D, 0, gl1_image.gl_tex_solid_format, 
			256, 256, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img.tobytes())
			
	else:
		raise NotImplemented()
		"""
		unsigned char *dest;

		for (i=0 ; i<trows ; i++)
		{
			row = (int)(i*hscale);
			if (row > rows)
				break;
			source = data + cols*row;
			dest = &image8[i*256];
			fracstep = cols*0x10000/256;
			frac = fracstep >> 1;
			for (j=0 ; j<256 ; j++)
			{
				dest[j] = source[frac>>16];
				frac += fracstep;
			}
		}

		qglTexImage2D( GL_TEXTURE_2D, 
			           0, 
					   GL_COLOR_INDEX8_EXT, 
					   256, 256, 
					   0, 
					   GL_COLOR_INDEX, 
					   GL_UNSIGNED_BYTE, 
					   image8 );
		"""

	
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

	#if ( gl1_main.gl_config.renderer == GL.GL_RENDERER_MCD ) or ( gl1_main.gl_config.renderer & GL.GL_RENDERER_RENDITION ):
	#	GL.glDisable (GL.GL_ALPHA_TEST)

	GL.glBegin (GL.GL_QUADS)
	GL.glTexCoord2f (0, 0)
	GL.glVertex2f (x, y)
	GL.glTexCoord2f (1, 0)
	GL.glVertex2f (x+w, y)
	GL.glTexCoord2f (1, t)
	GL.glVertex2f (x+w, y+h)
	GL.glTexCoord2f (0, t)
	GL.glVertex2f (x, y+h)
	GL.glEnd ()

	#if ( gl1_main.gl_config.renderer == GL.GL_RENDERER_MCD ) or ( gl1_main.gl_config.renderer & GL.GL_RENDERER_RENDITION ):
	#	GL.glEnable (GL.GL_ALPHA_TEST)

