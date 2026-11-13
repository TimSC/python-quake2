"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * File formats supported by stb_image, for now only tga, png, jpg
 * See also https://github.com/nothings/stb
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np

from PIL import Image

from q2data import FormatError
from q2data import images as q2images
from common import clientserver, filesystem
from client.refresh import ref_shared
from client.refresh.files import pcx, wal

#
# files/stb.c
#

#
#include <stdlib.h>
#include "../ref_shared.h"

"""
// don't need HDR stuff
#define STBI_NO_LINEAR
#define STBI_NO_HDR
// make sure STB_image uses standard malloc(), as we'll use standard free() to deallocate
#define STBI_MALLOC(sz)    malloc(sz)
#define STBI_REALLOC(p,sz) realloc(p,sz)
#define STBI_FREE(p)       free(p)
// Switch of the thread local stuff. Breaks mingw under Windows.
#define STBI_NO_THREAD_LOCALS
// include implementation part of stb_image into this file
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

// include resize implementation
#define STB_IMAGE_RESIZE_IMPLEMENTATION
#include "stb_image_resize.h"
"""

# Q2PORT: FixFileExt is in pcx.py (pcx.FixFileExt), which was ported first

"""
 * origname: the filename to be opened, might be without extension
 * type: extension of the type we wanna open ("jpg", "png" or "tga")
 * pic: pointer RGBA pixel data will be assigned to
"""
def LoadSTB(origname, type): #const char *, const char*, byte **, int *, int * (returns qboolean, pic, width, height)

	#char filename[256];

	filename = pcx.FixFileExt(origname, type, None)

	pic = None

	rawsize, rawdata = filesystem.FS_LoadFile(filename)
	if rawdata is None:

		return False, None, 0, 0

	# stbi_load_from_memory(..., STBI_rgb_alpha) is q2data.images.load_rgba
	try:
		img = q2images.load_rgba(bytes(rawdata))
		w, h = img.width, img.height
		data = bytearray(img.pixels.tobytes()) # mutable: the renderers change it in place
	except FormatError as e:
		clientserver.Com_Printf("{} couldn't load data from {}: {}!\n".format("LoadSTB", filename, e))
		filesystem.FS_FreeFile(rawdata)
		return False, None, 0, 0

	filesystem.FS_FreeFile(rawdata)

	clientserver.Com_DPrintf("{}() loaded: {}\n".format("LoadSTB", filename))

	pic = data
	return True, pic, w, h

def ResizeSTB(input_pixels, input_width, input_height, output_pixels, output_width, output_height): #const byte *, int, int, byte *, int, int (returns qboolean)

	# Q2PORT: stbir_resize_uint8 (stb_image_resize) is replaced by Pillow's
	# resize, like LoadSTB uses Pillow for stb_image. stbir defaults to a
	# Catmull-Rom/Mitchell cubic filter; BICUBIC is the closest Pillow has.
	# The pixels are RGBA (4 channels); the result is written into output_pixels.
	try:
		img = Image.frombytes("RGBA", (input_width, input_height),
			bytes(input_pixels[:input_width * input_height * 4]))
		img = img.resize((output_width, output_height), Image.BICUBIC)
	except (ValueError, OSError):
		return False

	output_pixels[:output_width * output_height * 4] = img.tobytes()
	return True

# 8 looks good for smoothed textures with whole width as rstep
COLOR_DISTANCE = 8

def SmoothColorImage(dst, size, rstep): #unsigned *, size_t, size_t

	"""
	const unsigned *full_size;
	unsigned last_color;
	unsigned *last_diff;
	"""

	# Q2PORT: dst is the RGBA bytearray; pix is a view of it as the C's unsigned
	# pixels, and the pointers are indices into it
	pix = np.frombuffer(dst, dtype=np.uint32, count=size)
	d = 0 # dst

	# maximum step for apply
	if rstep < 2:
		return

	# step one pixel back as with check one pixel more
	full_size = d + size - rstep - 1
	last_diff = d
	last_color = int(pix[d])

	# skip current point
	d += 1

	while d < full_size:
	
		if last_color != pix[d]:
		
			step = d - last_diff
			if step > 1:
			
				#int a_beg, b_beg, c_beg, d_beg;
				#int a_end, b_end, c_end, d_end;
				#int a_step, b_step, c_step, d_step;
				#int k;

				# minimize effect size to rstep
				if step > rstep:
				
					# change place for start effect
					last_diff += (step - rstep)
					step = rstep

				# compare next pixels
				k = 1
				while k <= step:
				
					if pix[d + k] != pix[d]:
						break
					k += 1

				# step back as pixel different after previous step
				k -= 1

				# mirror steps
				if k < step:
				
					# Com_Printf("%s %d -> %d\n", __func__, k, step);
					# change place for start effect
					last_diff += (step - k)
					step = k

				# update step to correct value
				step += k
				d += k

				# get colors
				a_beg = (last_color >> 0 ) & 0xff
				b_beg = (last_color >> 8 ) & 0xff
				c_beg = (last_color >> 16) & 0xff
				d_beg = (last_color >> 24) & 0xff

				cur = int(pix[d])
				a_end = (cur >> 0 ) & 0xff
				b_end = (cur >> 8 ) & 0xff
				c_end = (cur >> 16) & 0xff
				d_end = (cur >> 24) & 0xff

				a_step = a_end - a_beg
				b_step = b_end - b_beg
				c_step = c_end - c_beg
				d_step = d_end - d_beg

				if (step > 0 and
					(abs(a_step) < COLOR_DISTANCE) and
					(abs(b_step) < COLOR_DISTANCE) and
					(abs(c_step) < COLOR_DISTANCE) and
					(abs(d_step) < COLOR_DISTANCE) and
					(
						abs(a_step) > 1 or
						abs(b_step) > 1 or
						abs(c_step) > 1 or
						abs(d_step) > 1
					)):
				
					# generate color change steps (the C's int division truncates)
					a_step = int((a_step << 16) / step)
					b_step = int((b_step << 16) / step)
					c_step = int((c_step << 16) / step)
					d_step = int((d_step << 16) / step)

					# apply color changes
					for k in range(step):
					
						pix[last_diff] = ((((a_beg + ((a_step * k) >> 16)) << 0) & 0x000000ff) |
									 (((b_beg + ((b_step * k) >> 16)) << 8) & 0x0000ff00) |
									 (((c_beg + ((c_step * k) >> 16)) << 16) & 0x00ff0000) |
									 (((d_beg + ((d_step * k) >> 16)) << 24) & 0xff000000))
						last_diff += 1

			last_color = int(pix[d])
			last_diff = d
		
		d += 1

"""
 https://en.wikipedia.org/wiki/Pixel-art_scaling_algorithms
"""
def scale2x(src, dst, width, height): #const byte *, byte *, int, int

	"""
		EPX/Scale2x/AdvMAME2x

		x A x
		C P B -> 1 2
		x D x    3 4

		1=P; 2=P; 3=P; 4=P;
		IF C==A AND C!=D AND A!=B => 1=A
		IF A==B AND A!=C AND B!=D => 2=B
		IF D==C AND D!=B AND C!=A => 3=C
		IF B==D AND B!=A AND D!=C => 4=D
	"""
	if True:

		in_buff = 0
		out_buff = 0
		out_buff_full = ((width * height) << 2)

		while out_buff < out_buff_full:

			for x in range(width):

				# copy one source byte to two destinatuion bytes
				dst[out_buff] = src[in_buff]
				out_buff += 1
				dst[out_buff] = src[in_buff]
				out_buff += 1

				# next source pixel
				in_buff += 1

			# copy last line one more time
			dst[out_buff:out_buff + (width << 1)] = dst[out_buff - (width << 1):out_buff]
			out_buff += width << 1

	if True:

		h = height - 1
		w = width - 1
		for y in range(height):

			for x in range(width):

				p = src[(width * (y    )) + (x    )]
				a = src[(width * (y - 1)) + (x    )] if (y > 0) else p
				b = src[(width * (y    )) + (x + 1)] if (x < w) else p
				c = src[(width * (y    )) + (x - 1)] if (x > 0) else p
				d = src[(width * (y + 1)) + (x    )] if (y < h) else p

				if (c == a) and (c != d) and (a != b):

					dst[(2 * width * ((y * 2)    )) + ((x * 2)    )] = a

				if (a == b) and (a != c) and (b != d):

					dst[(2 * width * ((y * 2)    )) + ((x * 2) + 1)] = b

				if (d == c) and (d != b) and (c != a):

					dst[(2 * width * ((y * 2) + 1)) + ((x * 2)    )] = c

				if (b == d) and (b != a) and (d != c):

					dst[(2 * width * ((y * 2) + 1)) + ((x * 2) + 1)] = d


def scale3x(src, dst, width, height): #const byte *, byte *, int, int

	"""
		Scale3x/AdvMAME3x and ScaleFX

		A B C    1 2 3
		D E F -> 4 5 6
		G H I    7 8 9


		1=E; 2=E; 3=E; 4=E; 5=E; 6=E; 7=E; 8=E; 9=E;
		IF D==B AND D!=H AND B!=F => 1=D
		IF (D==B AND D!=H AND B!=F AND E!=C) OR (B==F AND B!=D AND F!=H AND E!=A) => 2=B
		IF B==F AND B!=D AND F!=H => 3=F
		IF (H==D AND H!=F AND D!=B AND E!=A) OR (D==B AND D!=H AND B!=F AND E!=G) => 4=D
		5=E
		IF (B==F AND B!=D AND F!=H AND E!=I) OR (F==H AND F!=B AND H!=D AND E!=C) => 6=F
		IF H==D AND H!=F AND D!=B => 7=D
		IF (F==H AND F!=B AND H!=D AND E!=G) OR (H==D AND H!=F AND D!=B AND E!=I) => 8=H
		IF F==H AND F!=B AND H!=D => 9=F
	"""
	if True:

		in_buff = 0
		out_buff = 0
		out_buff_full = ((width * height) * 9)

		while out_buff < out_buff_full:

			for x in range(width):

				# copy one source byte to two destinatuion bytes
				dst[out_buff] = src[in_buff]
				out_buff += 1
				dst[out_buff] = src[in_buff]
				out_buff += 1
				dst[out_buff] = src[in_buff]
				out_buff += 1

				# next source pixel
				in_buff += 1

			# copy last line one more time
			dst[out_buff:out_buff + width * 3] = dst[out_buff - (width * 3):out_buff]
			out_buff += width * 3
			# copy last line one more time
			dst[out_buff:out_buff + width * 3] = dst[out_buff - (width * 3):out_buff]
			out_buff += width * 3

	if True:

		z = height - 1
		w = width - 1
		for y in range(height):

			for x in range(width):

				e = src[(width * y) + x]

				a = src[(width * (y - 1)) + (x - 1)] if ((y > 0) and (x > 0)) else e
				b = src[(width * (y - 1)) + (x    )] if ((y > 0) and (x    )) else e
				c = src[(width * (y - 1)) + (x + 1)] if ((y > 0) and (x < w)) else e

				d = src[(width * (y    )) + (x - 1)] if (           (x > 0)) else e
				f = src[(width * (y    )) + (x + 1)] if (           (x < w)) else e

				g = src[(width * (y + 1)) + (x - 1)] if ((y < z) and (x > 0)) else e
				h = src[(width * (y + 1)) + (x    )] if ((y < z) and (x    )) else e
				i = src[(width * (y + 1)) + (x + 1)] if ((y < z) and (x < w)) else e

				if (d == b) and (d != h) and (b != f):

					dst[(3 * width * ((y * 3)    )) + ((x * 3)    )] = d

				if (((d == b) and (d != h) and (b != f) and (e != c)) or
					((b == f) and (b != d) and (f != h) and (e != a))):

					dst[(3 * width * ((y * 3)    )) + ((x * 3) + 1)] = b

				if (b == f) and (b != d) and (f != h):

					dst[(3 * width * ((y * 3)    )) + ((x * 3) + 2)] = f

				if (((h == d) and (h != f) and (d != b) and (e != a)) or
					((d == b) and (d != h) and (b != f) and (e != g))):

					dst[(3 * width * ((y * 3) + 1)) + ((x * 3)    )] = d

				if (((b == f) and (b != d) and (f != h) and (e != i)) or
					((f == h) and (f != b) and (h != d) and (e != c))):

					dst[(3 * width * ((y * 3) + 1)) + ((x * 3) + 2)] = f

				if (h == d) and (h != f) and (d != b):

					dst[(3 * width * ((y * 3) + 2)) + ((x * 3)    )] = d

				if (((f == h) and (f != b) and (h != d) and (e != g)) or
					((h == d) and (h != f) and (d != b) and (e != i))):

					dst[(3 * width * ((y * 3) + 2)) + ((x * 3) + 1)] = h

				if (f == h) and (f != b) and (h != d):

					dst[(3 * width * ((y * 3) + 2)) + ((x * 3) + 2)] = f


def LoadHiColorImage(name, namewe, ext, type, load_image): #const char *, const char*, const char *, imagetype_t, loadimage_t (returns struct image_s *)

	realwidth, realheight = 0, 0
	width, height = 0, 0
	image = None
	pic = None

	# Get size of the original texture
	# Q2PORT: the Get*Info functions return (width, height), (None, None) if
	# they can't
	if ext == "pcx":

		realwidth, realheight = pcx.GetPCXInfo(name)

	elif ext == "wal":

		realwidth, realheight = wal.GetWalInfo(name)

	elif ext == "m8":

		realwidth, realheight = wal.GetM8Info(name)

	elif ext == "m32":

		realwidth, realheight = wal.GetM32Info(name)

	if realwidth is None or realheight is None:
		realwidth, realheight = 0, 0

	# try to load a tga, png or jpg (in that order/priority)
	for stbtype in ("tga", "png", "jpg"):

		ok, pic, width, height = LoadSTB(namewe, stbtype)
		if ok:
			break

	if ok:

		if width >= realwidth and height >= realheight:

			if realheight == 0 or realwidth == 0:

				realheight = height
				realwidth = width

			image = load_image(name, pic,
				width, realwidth,
				height, realheight,
				width * height,
				type, 32)

	return image


def R_LoadImage(name, namewe, ext, type, r_retexturing, load_image): #const char *, const char*, const char *, imagetype_t, qboolean, loadimage_t (returns struct image_s *)

	image = None

	# with retexturing and not skin
	if r_retexturing:

		image = LoadHiColorImage(name, namewe, ext, type, load_image)

	if image is None:

		if ext == "pcx":

			pic = None
			palette = None
			width, height, bitsPerPixel = 0, 0, 8

			pic, palette, width, height = pcx.LoadPCX (namewe) # Q2PORT: always 8 bits per pixel
			if pic is None:
				return None

			image = load_image(name, pic,
				width, width,
				height, height,
				width * height, type, bitsPerPixel)

		elif ext == "wal":

			image = wal.LoadWal(namewe, type, load_image)

		elif ext == "m8":

			image = wal.LoadM8(namewe, type, load_image)

		elif ext == "m32":

			image = wal.LoadM32(namewe, type, load_image)

		elif (ext == "tga" or
		      ext == "png" or
		      ext == "jpg"):

			ok, pic, width, height = LoadSTB (namewe, ext)
			if ok and pic is not None:

				image = load_image(name, pic,
					width, width,
					height, height,
					width * height,
					type, 32)

	return image


def GetSkyImage(skyname, surfname, palettedtexture, find_image): #const char *, const char*, qboolean, findimage_t (returns struct image_s*)

	image = None
	#char pathname[MAX_QPATH];

	# Quake 2
	if palettedtexture:

		pathname = "env/{}{}.pcx".format(skyname, surfname)
		image = find_image(pathname, ref_shared.imagetype_t.it_sky)

	if image is None:

		pathname = "env/{}{}.tga".format(skyname, surfname)
		image = find_image(pathname, ref_shared.imagetype_t.it_sky)

	# Heretic 2
	if image is None:

		pathname = "pics/Skies/{}{}.m32".format(skyname, surfname)
		image = find_image(pathname, ref_shared.imagetype_t.it_sky)

	if image is None:

		pathname = "pics/Skies/{}{}.m8".format(skyname, surfname)
		image = find_image(pathname, ref_shared.imagetype_t.it_sky)

	return image

# Q2PORT: GetTexImage is in models.py (files_models.GetTexImage)

def R_FindPic(name, find_image): #const char *, findimage_t (returns struct image_s *)

	image = None

	if (name[0] != '/') and (name[0] != '\\'):

		#char	pathname[MAX_QPATH];

		# Quake 2
		pathname = "pics/{}.pcx".format(name)
		image = find_image(pathname, ref_shared.imagetype_t.it_pic)

		# Heretic 2
		if image is None:

			pathname = "pics/misc/{}.m32".format(name)
			image = find_image(pathname, ref_shared.imagetype_t.it_pic)

		if image is None:

			pathname = "pics/misc/{}.m8".format(name)
			image = find_image(pathname, ref_shared.imagetype_t.it_pic)

	else:

		image = find_image(name[1:], ref_shared.imagetype_t.it_pic)

	return image

"""
=================
Mod_FloodFillSkin

Fill background pixels so mipmapping doesn't have haloes
=================
"""

# must be a power of 2
FLOODFILL_FIFO_SIZE = 0x1000
FLOODFILL_FIFO_MASK = (FLOODFILL_FIFO_SIZE - 1)

"""
 * Fill background pixels so mipmapping doesn't have haloes
"""
def R_FloodFillSkin(skin, skinwidth, skinheight, table_8to24): #byte *, int, int, const unsigned *

	fillcolor = skin[0] # assume this is the pixel to fill
	fifo = [[0, 0] for _ in range(FLOODFILL_FIFO_SIZE)] #static floodfill_t fifo[FLOODFILL_FIFO_SIZE]
	inpt, outpt = 0, 0
	filledcolor = 0

	# NOTE: there was a if (filledcolor == -1) which didn't make sense b/c filledcolor used to be initialized to -1
	# attempt to find opaque black
	for i in range(256):

		if tuple(table_8to24[i]) == (255, 0, 0, 0): # LittleLong(table_8to24[i]) == (255 << 0), alpha 1.0
			# Q2PORT: as the C: the little endian word 255 << 0 is red 255,
			# alpha 0 (not the opaque black the comment says), so with
			# Quake's palette nothing matches and filledcolor stays 0
			filledcolor = i
			break

	# can't fill to filled color or to transparent color (used as visited marker)
	if (fillcolor == filledcolor) or (fillcolor == 255):

		return

	fifo[inpt][0], fifo[inpt][1] = 0, 0
	inpt = (inpt + 1) & FLOODFILL_FIFO_MASK

	while outpt != inpt:

		x, y = fifo[outpt][0], fifo[outpt][1]
		fdc = filledcolor
		pos = x + skinwidth * y

		outpt = (outpt + 1) & FLOODFILL_FIFO_MASK

		# FLOODFILL_STEP(off, dx, dy)
		for cond, off, dx, dy in ((x > 0, -1, -1, 0),
				(x < skinwidth - 1, 1, 1, 0),
				(y > 0, -skinwidth, 0, -1),
				(y < skinheight - 1, skinwidth, 0, 1)):

			if not cond:
				continue

			if skin[pos + off] == fillcolor:

				skin[pos + off] = 255
				fifo[inpt][0], fifo[inpt][1] = x + (dx), y + (dy)
				inpt = (inpt + 1) & FLOODFILL_FIFO_MASK

			elif skin[pos + off] != 255:

				fdc = skin[pos + off]

		skin[x + skinwidth * y] = fdc


"""
** R_Convert8to32
"""
def R_Convert8to32 (data, width, height, table_8to24): #byte *, size_t, size_t, unsigned [] (returns unsigned *)

	"""
	unsigned *trans;
	size_t i, s;
	"""

	if height == 0:
		return None

	s = width * height

	# Q2PORT: the C's per-pixel loop is done with numpy (a palette lookup, then the
	# same neighbour search for the transparent pixels, in the same order)
	pal = np.array(table_8to24, dtype=np.uint8)
	d = np.frombuffer(bytes(data[:s]), dtype=np.uint8).astype(np.intp)
	trans = pal[d] # trans[i] = table_8to24[p];

	i = np.nonzero(d == 255)[0]
	if len(i):

		# transparent, so scan around for
		# another color to avoid alpha fringes
		up = np.where(i > width, d[np.maximum(i - width, 0)], 255)
		down = np.where(i < s - width, d[np.minimum(i + width, s - 1)], 255)
		left = np.where(i > 0, d[np.maximum(i - 1, 0)], 255)
		right = np.where(i < s - 1, d[np.minimum(i + 1, s - 1)], 255)
		p = np.where(up != 255, up, np.where(down != 255, down, np.where(left != 255, left, np.where(right != 255, right, 0))))

		# copy rgb components
		trans[i, 0:3] = pal[p, 0:3]

	trans = bytearray(trans.tobytes())

	return trans

