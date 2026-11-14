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

 The prototypes for most file formats used by Quake II

=======================================================================
"""
from __future__ import annotations

import struct
import numpy as np

pass
from common.header import shared
from common.shared import shared as shared_c
"""

//
// qfiles.h: quake file formats
// This file must be identical in the quake and utils directories
//

/*
========================================================================

The .pak files are just a linear collapse of a directory tree

========================================================================
*/
"""
IDPAKHEADER		= (ord('K')<<24)+(ord('C')<<16)+(ord('A')<<8)+ord('P')


class dpackfile_t(object):

	def __init__(self):
		self.name = None #char [56]
		self.filepos, self.filelen = None, None # int

	def read(self, fi):
		self.name = fi.read(56).decode("latin-1").replace("\x00", "", -1) # Q2PORT: latin-1, the C's names are bytes (ascii failed on others)

		self.filepos, self.filelen = struct.unpack('<ll', fi.read(8))

	def __repr__(self):
		return "dpackfile_t ({} {} {})".format(self.name, self.filepos, self.filelen)

class dpackheader_t(object):
	def __init__(self):

		self.ident = None #int == IDPAKHEADER
		self.dirofs = None #int
		self.dirlen = None #int

	def read(self, fi):

		self.ident, self.dirofs, self.dirlen = struct.unpack('<lll', fi.read(12))


MAX_FILES_IN_PACK = 4096


"""
========================================================================

PCX files are used for as many images as possible

========================================================================
"""

class pcx_t (object):

	def __init__(self):

		self.manufacturer = None #char
		self.version = None #char
		self.encoding = None #char
		self.bits_per_pixel = None #char
		self.xmin,ymin,xmax,ymax = None,None,None,None #unsigned short
		self.hres,vres = None,None #unsigned short
		self.palette=[] #unsigned char[48]
		self.reserved = None #char
		self.color_planes = None #char
		self.bytes_per_line = None #unsigned short
		self.palette_type = None #unsigned short
		self.filler = [] #char[58]
		self.data = None

	def Read(self, buff):

		# Q2PORT: the C casts the file to pcx_t; returns False if it is too
		# short for the header (the callers check the size first)
		if len(buff) < 128:
			return False

		self.manufacturer, self.version, self.encoding, self.bits_per_pixel = struct.unpack("<BBBB", buff[:4])
		self.xmin = struct.unpack("<H", buff[4:6])[0]
		self.ymin = struct.unpack("<H", buff[6:8])[0]
		self.xmax = struct.unpack("<H", buff[8:10])[0]
		self.ymax = struct.unpack("<H", buff[10:12])[0]
		self.hres = struct.unpack("<H", buff[12:14])[0]
		self.vres = struct.unpack("<H", buff[14:16])[0]

		self.palette = buff[16:64]

		self.reserved, self.color_planes = struct.unpack("<BB", buff[64:66])

		self.bytes_per_line = struct.unpack("<H", buff[66:68])[0]
		self.palette_type = struct.unpack("<H", buff[68:70])[0]
		
		self.filler = buff[70:128]
		self.data = buff[128:]

		return True

"""
========================================================================

.MD2 triangle model file format

========================================================================
*/
"""
IDALIASHEADER = ((ord('2')<<24)+(ord('P')<<16)+(ord('D')<<8)+ord('I'))
ALIAS_VERSION = 8
IDSPRITEHEADER = ((ord('2')<<24)+(ord('S')<<16)+(ord('D')<<8)+ord('I'))
SPRITE_VERSION = 2
MAX_SKINNAME = 64
MAX_TRIANGLES = 4096
MAX_VERTS = 2048
MAX_FRAMES = 512

class daliasframe_t(object):

	def __init__(self):
		self.scale = np.zeros((3,), dtype=np.float32)
		self.translate = np.zeros((3,), dtype=np.float32)
		self.name = ""
		self.verts = []


class dmdl_t(object):

	def __init__(self):
		self.ident = None
		self.version = None
		self.skinwidth = None
		self.skinheight = None
		self.framesize = None
		self.num_skins = None
		self.num_xyz = None
		self.num_st = None
		self.num_tris = None
		self.num_glcmds = None
		self.num_frames = None
		self.ofs_skins = None
		self.ofs_st = None
		self.ofs_tris = None
		self.ofs_frames = None
		self.ofs_glcmds = None
		self.ofs_end = None

	@classmethod
	def packed_size(cls):
		return 17 * 4

	def load(self, buff):
		values = struct.unpack("<17i", buff[:self.packed_size()])
		(
			self.ident,
			self.version,
			self.skinwidth,
			self.skinheight,
			self.framesize,
			self.num_skins,
			self.num_xyz,
			self.num_st,
			self.num_tris,
			self.num_glcmds,
			self.num_frames,
			self.ofs_skins,
			self.ofs_st,
			self.ofs_tris,
			self.ofs_frames,
			self.ofs_glcmds,
			self.ofs_end,
		) = values


class dsprframe_t(object):

	def __init__(self):
		self.width = None
		self.height = None
		self.origin_x = None
		self.origin_y = None
		self.name = ""


class dsprite_t(object):

	def __init__(self):
		self.ident = None
		self.version = None
		self.numframes = None
		self.frames = []

	@classmethod
	def packed_size(cls): # Q2PORT: the header, without frames[1]
		return 12

	def load(self, buff):
		# Q2PORT: reads only the frames that are in buff (the C would read
		# past the end); Mod_LoadSP2() checks len(frames)
		self.ident, self.version, self.numframes = struct.unpack("<3i", buff[:12])
		cursor = 12
		for _ in range(self.numframes):
			if cursor + 16 + MAX_SKINNAME > len(buff):
				break
			width, height, origin_x, origin_y = struct.unpack("<4i", buff[cursor:cursor+16])
			cursor += 16
			name_bytes = buff[cursor:cursor+MAX_SKINNAME]
			cursor += MAX_SKINNAME
			frame = dsprframe_t()
			frame.width = width
			frame.height = height
			frame.origin_x = origin_x
			frame.origin_y = origin_y
			frame.name = name_bytes.split(b"\x00", 1)[0].decode("latin-1") # Q2PORT: latin-1, the C's strings are bytes
			self.frames.append(frame)


class dstvert_t(object):

	def __init__(self):
		self.s = 0 # short
		self.t = 0 # short

	@classmethod
	def packed_size(cls):
		return 4

	def load(self, buff):

		self.s = shared_c.LittleShort(buff[:2])
		self.t = shared_c.LittleShort(buff[2:])


class dtriangle_t(object):

	def __init__(self):
		self.index_xyz = np.zeros((3,), dtype=np.int16)
		self.index_st = np.zeros((3,), dtype=np.int16)

	@classmethod
	def packed_size(cls):
		return 12

	def load(self, buff):

		self.index_xyz[:] = struct.unpack("<3h", buff[:6])
		self.index_st[:] = struct.unpack("<3h", buff[6:12])


class dtrivertx_t(object):

	def __init__(self):
		self.v = np.zeros((3,), dtype=np.uint8)
		self.lightnormalindex = 0

	@classmethod
	def packed_size(cls):
		return 4

	def load(self, buff):

		self.v[0] = buff[0]
		self.v[1] = buff[1]
		self.v[2] = buff[2]
		self.lightnormalindex = buff[3]

DTRIVERTX_V0 = 0
DTRIVERTX_V1 = 1
DTRIVERTX_V2 = 2
DTRIVERTX_LNI = 3
DTRIVERTX_SIZE = 4

MIPLEVELS = 4

class miptex_t(object):

	def __init__(self):

		self.name = None # char [32]
		self.width, self.height = None, None # unsigned	
		self.offsets = None # unsigned [MIPLEVELS], four mip maps stored
		self.animname = None # char		[32],  next frame in animation chain
		self.flags = None # int			
		self.contents = None # int			
		self.value = None # int			

	@classmethod
	def packed_size(cls):
		return 100

	def load(self, buff):

		self.name = buff[:32].decode('latin-1').rstrip('\x00') # Q2PORT: latin-1, the C's names are bytes (ascii failed on others)
		self.width = shared_c.LittleLong(buff[32:36])
		self.height = shared_c.LittleLong(buff[36:40])
		self.offsets = []
		c = 40
		for i in range(4):
			self.offsets.append(shared_c.LittleLong(buff[c:c+4]))
			c += 4
		self.animname = buff[56:88].decode('latin-1').rstrip('\x00') # Q2PORT: latin-1, the C's names are bytes (ascii failed on others)
		self.flags = shared_c.LittleSLong(buff[88:92])		
		self.contents = shared_c.LittleSLong(buff[92:96])
		self.value = shared_c.LittleSLong(buff[96:100])

# .M8 texture file format

M8_MIP_LEVELS = 16
M8_VERSION = 0x2

"""
typedef struct {
	unsigned char r;
	unsigned char g;
	unsigned char b;
} rgb_t;

typedef struct m8tex_s
{
	unsigned version;
	char name[32];
	unsigned width[M8_MIP_LEVELS];
	unsigned height[M8_MIP_LEVELS];
	unsigned offsets[M8_MIP_LEVELS]; /* 16 mip maps stored */
	char animname[32];           /* next frame in animation chain */
	rgb_t palette[256];
	int flags;
	int contents;
	int value;
} m8tex_t;
"""

# .M32 texture file format

M32_VERSION     = 0x4
M32_MIP_LEVELS  = 16

"""
typedef struct m32tex_s
{
	int version;
	char name[128];
	char altname[128];                   // texture substitution
	char animname[128];                  // next frame in animation chain
	char damagename[128];                // image that should be shown when damaged
	unsigned width[M32_MIP_LEVELS], height[M32_MIP_LEVELS];
	unsigned offsets[M32_MIP_LEVELS];
	int flags;
	int contents;
	int value;
	float scale_x, scale_y;
	int mip_scale;

	// detail texturing info
	char dt_name[128];                  // detailed texture name
	float dt_scale_x, dt_scale_y;
	float dt_u, dt_v;
	float dt_alpha;
	int dt_src_blend_mode, dt_dst_blend_mode;

	int unused[20];                     // future expansion to maintain compatibility with h2
} m32tex_t;
"""

class rgb_t(object):

	def __init__(self):
		self.r = 0 #unsigned char
		self.g = 0 #unsigned char
		self.b = 0 #unsigned char


class m8tex_t(object):

	def __init__(self):
		self.version = 0 #unsigned
		self.name = None #char [32]
		self.width = [0] * M8_MIP_LEVELS #unsigned
		self.height = [0] * M8_MIP_LEVELS #unsigned
		self.offsets = [0] * M8_MIP_LEVELS #unsigned, 16 mip maps stored
		self.animname = None #char [32], next frame in animation chain
		self.palette = [] #rgb_t [256]
		self.flags = 0 #int
		self.contents = 0 #int
		self.value = 0 #int

	def load(self, buff):
		self.version = struct.unpack("<I", buff[0:4])[0]
		self.name = buff[4:36].split(b'\x00', 1)[0].decode("ascii", "ignore")
		self.width = list(struct.unpack("<16I", buff[36:100]))
		self.height = list(struct.unpack("<16I", buff[100:164]))
		self.offsets = list(struct.unpack("<16I", buff[164:228]))
		self.animname = buff[228:260].split(b'\x00', 1)[0].decode("ascii", "ignore")
		self.palette = []
		for i in range(256):
			o = 260 + i * 3
			rgb = rgb_t()
			rgb.r, rgb.g, rgb.b = struct.unpack("<BBB", buff[o:o + 3])
			self.palette.append(rgb)
		o = 260 + 256 * 3
		self.flags, self.contents, self.value = struct.unpack("<3i", buff[o:o + 12])

	@classmethod
	def packed_size(cls):
		return 4 + 32 + 16 * 4 * 3 + 32 + 256 * 3 + 12


class m32tex_t(object):

	def __init__(self):
		self.version = 0 #int
		self.name = None #char [128]
		self.altname = None #char [128], texture substitution
		self.animname = None #char [128], next frame in animation chain
		self.damagename = None #char [128], image that should be shown when damaged
		self.width = [0] * M32_MIP_LEVELS #unsigned
		self.height = [0] * M32_MIP_LEVELS #unsigned
		self.offsets = [0] * M32_MIP_LEVELS #unsigned
		self.flags = 0 #int
		self.contents = 0 #int
		self.value = 0 #int
		self.scale_x = 0.0 #float
		self.scale_y = 0.0 #float
		self.mip_scale = 0 #int
		self.dt_name = None #char [128], detailed texture name
		self.dt_scale_x = 0.0 #float
		self.dt_scale_y = 0.0 #float
		self.dt_u = 0.0 #float
		self.dt_v = 0.0 #float
		self.dt_alpha = 0.0 #float
		self.dt_src_blend_mode = 0 #int
		self.dt_dst_blend_mode = 0 #int

	def load(self, buff):
		self.version = struct.unpack("<i", buff[0:4])[0]
		self.name = buff[4:132].split(b'\x00', 1)[0].decode("ascii", "ignore")
		self.altname = buff[132:260].split(b'\x00', 1)[0].decode("ascii", "ignore")
		self.animname = buff[260:388].split(b'\x00', 1)[0].decode("ascii", "ignore")
		self.damagename = buff[388:516].split(b'\x00', 1)[0].decode("ascii", "ignore")
		o = 516
		self.width = list(struct.unpack("<16I", buff[o:o + 64]))
		self.height = list(struct.unpack("<16I", buff[o + 64:o + 128]))
		self.offsets = list(struct.unpack("<16I", buff[o + 128:o + 192]))
		o = 516 + 192
		self.flags, self.contents, self.value = struct.unpack("<3i", buff[o:o + 12])
		self.scale_x, self.scale_y = struct.unpack("<2f", buff[o + 12:o + 20])
		self.mip_scale = struct.unpack("<i", buff[o + 20:o + 24])[0]
		o = o + 24
		self.dt_name = buff[o:o + 128].split(b'\x00', 1)[0].decode("ascii", "ignore")
		self.dt_scale_x, self.dt_scale_y, self.dt_u, self.dt_v, self.dt_alpha = struct.unpack("<5f", buff[o + 128:o + 148])
		self.dt_src_blend_mode, self.dt_dst_blend_mode = struct.unpack("<2i", buff[o + 148:o + 156])

	@classmethod
	def packed_size(cls):
		return 4 + 128 * 4 + 16 * 4 * 3 + 4 * 12 + 128 + 4 * 7

"""
==============================================================================

  .BSP file format

==============================================================================
"""
IDBSPHEADER	= ((ord('P')<<24)+(ord('S')<<16)+(ord('B')<<8)+ord('I'))
		# little-endian "IBSP"
BSPVERSION = 38


# upper design bounds
# leaffaces, leafbrushes, planes, and verts are still bounded by
# 16 bit short limits
MAX_MAP_MODELS		= 1024
MAX_MAP_BRUSHES		= 8192
MAX_MAP_ENTITIES	= 2048
MAX_MAP_ENTSTRING	= 0x40000
MAX_MAP_TEXINFO		= 8192

MAX_MAP_AREAS		= 256
MAX_MAP_AREAPORTALS	= 1024
MAX_MAP_PLANES		= 65536
MAX_MAP_NODES		= 65536
MAX_MAP_BRUSHSIDES	= 65536
MAX_MAP_LEAFS		= 65536
MAX_MAP_VERTS		= 65536
MAX_MAP_FACES		= 65536
MAX_MAP_LEAFFACES	= 65536
MAX_MAP_LEAFBRUSHES = 65536
MAX_MAP_PORTALS		= 65536
MAX_MAP_EDGES		= 128000
MAX_MAP_SURFEDGES	= 256000
MAX_MAP_LIGHTING	= 0x200000
MAX_MAP_VISIBILITY	= 0x100000
MAXLIGHTMAPS		= 4
MAX_MD2SKINS		= 32
MAX_LBM_HEIGHT		= 480
# key / value pair sizes

MAX_KEY = 32
MAX_VALUE = 1024
"""

//=============================================================================
"""
class lump_t(object):
	def __init__(self, fileofsIn=None, filelenIn=None):
		self.fileofs = fileofsIn # int
		self.filelen = filelenIn

	@classmethod
	def packed_size(cls):
		return 8

	def __repr__(self):

		return "lumpt({}, {})".format(self.fileofs, self.filelen)


LUMP_ENTITIES		= 0
LUMP_PLANES			= 1
LUMP_VERTEXES		= 2
LUMP_VISIBILITY		= 3
LUMP_NODES			= 4
LUMP_TEXINFO		= 5
LUMP_FACES			= 6
LUMP_LIGHTING		= 7
LUMP_LEAFS			= 8
LUMP_LEAFFACES		= 9
LUMP_LEAFBRUSHES	= 10
LUMP_EDGES			= 11
LUMP_SURFEDGES		= 12
LUMP_MODELS			= 13
LUMP_BRUSHES		= 14
LUMP_BRUSHSIDES		= 15
LUMP_POP			= 16
LUMP_AREAS			= 17
LUMP_AREAPORTALS	= 18
HEADER_LUMPS = 19

class dheader_t(object):

	def __init__(self):

		self.ident = None #int			
		self.version = None #int			
		self.lumps = None # lump_t[HEADER_LUMPS]

	@classmethod
	def packed_size(cls):
		return 8 + lump_t.packed_size() * HEADER_LUMPS

	def parse(self, buf: bytes|bytearray):
		
		self.ident = struct.unpack("<I", buf[:4])[0]
		self.version = struct.unpack("<I", buf[4:8])[0] #int
		self.lumps = [] # lump_t[HEADER_LUMPS]
		cursor = 8
		for i in range(HEADER_LUMPS):
			self.lumps.append(lump_t(*struct.unpack("<II", buf[cursor:cursor+8])))
			cursor += 8

	def BadLump(self, length: int)->int:

		# Q2PORT: the C reads a lump that goes past the end of the file from
		# beyond the buffer; the loaders check this first. Returns the first
		# such lump, or -1.
		for i in range(HEADER_LUMPS):
			if self.lumps[i].fileofs + self.lumps[i].filelen > length:
				return i
		return -1


class dmodel_t(object):

	def __init__(self):

		self.mins = np.zeros((3,), dtype=np.float32) # float[3]
		self.maxs = np.zeros((3,), dtype=np.float32) # float[3]
		self.origin = np.zeros((3,), dtype=np.float32) # float[3], for sounds or lights
		self.headnode = None # int
		self.firstface = None # int, submodels just draw faces
				  # without walking the bsp tree
		self.numfaces = None # int

	@classmethod
	def packed_size(cls):
		return 48

	def load(self, buff):

		c = 0
		for j in range(3):
			self.mins[j] = shared_c.LittleFloat (buff[c:c+4])
			c += 4

		for j in range(3):
			self.maxs[j] = shared_c.LittleFloat (buff[c:c+4])
			c += 4

		for j in range(3):
			self.origin[j] = shared_c.LittleFloat (buff[c:c+4])
			c += 4

		self.headnode = shared_c.LittleSLong (buff[c:c+4])
		c += 4
		self.firstface = shared_c.LittleSLong (buff[c:c+4])
		c += 4
		self.numfaces = shared_c.LittleSLong (buff[c:c+4])
		c += 4


class dvertex_t(object):

	def __init__(self):
		self.point = np.zeros((3,), dtype=np.float32) #float[3]

	@classmethod
	def packed_size(cls):
		return 12

	def load(self, buff):

		self.point[0] = shared_c.LittleFloat(buff[:4])
		self.point[1] = shared_c.LittleFloat(buff[4:8])
		self.point[2] = shared_c.LittleFloat(buff[8:])


# 0-2 are axial planes
PLANE_X = 0
PLANE_Y = 1
PLANE_Z = 2

# 3-5 are non-axial planes snapped to the nearest
PLANE_ANYX = 3
PLANE_ANYY = 4
PLANE_ANYZ = 5

# planes (x&~1) and (x&~1)+1 are always opposites

class dplane_t(object):

	def __init__(self):

		self.normal = np.zeros((3,), dtype=np.float32) # float[3]
		self.dist = None # float
		self.type = None # int, PLANE_X - PLANE_ANYZ ?remove? trivial to regenerate

	@classmethod
	def packed_size(cls):
		return 20

	def load(self, buff):

		self.normal[0] = shared_c.LittleFloat(buff[:4])
		self.normal[1] = shared_c.LittleFloat(buff[4:8])
		self.normal[2] = shared_c.LittleFloat(buff[8:12])
		self.dist = shared_c.LittleFloat(buff[12:16])
		self.type = shared_c.LittleLong(buff[16:])

# contents flags are seperate bits
# a given brush can contribute multiple content bits
# multiple brushes can be in a single leaf

# these definitions also need to be in q_shared.h!

# lower bits are stronger, and will eat weaker brushes completely
CONTENTS_SOLID			= 1		# an eye is never valid in a solid
CONTENTS_WINDOW			= 2		# translucent, but not watery
CONTENTS_AUX			= 4
CONTENTS_LAVA			= 8
CONTENTS_SLIME			= 16
CONTENTS_WATER			= 32
CONTENTS_MIST			= 64
LAST_VISIBLE_CONTENTS	= 64

# remaining contents are non-visible, and don't eat brushes
CONTENTS_AREAPORTAL		= 0x8000

CONTENTS_PLAYERCLIP		= 0x10000
CONTENTS_MONSTERCLIP	= 0x20000

# currents can be added to any other contents, and may be mixed
CONTENTS_CURRENT_0		= 0x40000
CONTENTS_CURRENT_90		= 0x80000
CONTENTS_CURRENT_180	= 0x100000
CONTENTS_CURRENT_270	= 0x200000
CONTENTS_CURRENT_UP		= 0x400000
CONTENTS_CURRENT_DOWN	= 0x800000

CONTENTS_ORIGIN			= 0x1000000	# removed before bsping an entity

CONTENTS_MONSTER		= 0x2000000	# should never be on a brush, only in game
CONTENTS_DEADMONSTER	= 0x4000000
CONTENTS_DETAIL			= 0x8000000	# brushes to be added after vis leafs
CONTENTS_TRANSLUCENT	= 0x10000000	# auto set if any surface has trans
CONTENTS_LADDER			= 0x20000000

SURF_LIGHT		= 0x1		# value will hold the light strength
SURF_SLICK		= 0x2		# effects game physics
SURF_SKY		= 0x4		# don't draw, but add to skybox
SURF_WARP		= 0x8		# turbulent water warp
SURF_TRANS33	= 0x10
SURF_TRANS66	= 0x20
SURF_FLOWING	= 0x40	# scroll towards angle
SURF_NODRAW		= 0x80	# don't bother referencing the texture


class dnode_t(object):

	def __init__(self):

		self.planenum: int = None
		self.children = [None, None] # int[2], negative numbers are -(leafs+1), not nodes
		self.mins = np.zeros((3,), dtype=np.int16) # short[3]		# for frustom culling
		self.maxs = np.zeros((3,), dtype=np.int16) # short[3]
		self.firstface = None # unsigned short
		self.numfaces = None # unsigned short, counting both sides

	@classmethod
	def packed_size(cls):
		return 28

	def load(self, buff):

		self.planenum = shared_c.LittleLong(buff[:4])
		self.children[0] = shared_c.LittleSLong(buff[4:8])
		self.children[1] = shared_c.LittleSLong(buff[8:12])
		c = 12
		for i in range(3):
			self.mins[i] = shared_c.LittleSShort(buff[c:c+2])
			c += 2
		for i in range(3):
			self.maxs[i] = shared_c.LittleSShort(buff[c:c+2])
			c += 2
		self.firstface = shared_c.LittleShort(buff[c:c+2])
		c += 2
		self.numfaces = shared_c.LittleShort(buff[c:c+2])


class texinfo_t(object):

	def __init__(self):

		self.vecs = np.zeros((2,4), dtype=np.float32) # float[2][4], [s/t][xyz offset]
		self.flags = None # int, miptex flags + overrides
		self.value = None # int, light emission, etc
		self.texture = None # char[32],	texture name (textures/*.wal)
		self.nexttexinfo = None # int, for animations, -1 = end of chain
 
	@classmethod
	def packed_size(cls):
		return 76

	def load(self, buff):

		c = 0
		for j in range(8):
			self.vecs[j//4,j%4] = shared_c.LittleFloat (buff[c:c+4]) # float[2][4] is row major
			c+=4

		self.flags = shared_c.LittleSLong(buff[32:36])
		self.value = shared_c.LittleSLong(buff[36:40])
		self.texture = buff[40:72].decode("latin-1").rstrip('\x00') # Q2PORT: latin-1, the C's names are bytes (ascii failed on others)
		self.nexttexinfo = shared_c.LittleSLong(buff[72:])


class dface_t(object):

	def __init__(self):

		self.planenum = None # unsigned short
		self.side = None # short
		self.firstedge = None # int
		self.numedges = None # short
		self.texinfo = None # short
		self.styles = [0]*MAXLIGHTMAPS # byte[MAXLIGHTMAPS]
		self.lightofs = None # int

	@classmethod
	def packed_size(cls):
		return 20

	def load(self, buff):

		self.planenum = shared_c.LittleShort(buff[:2])
		self.side = shared_c.LittleSShort(buff[2:4])
		self.firstedge = shared_c.LittleLong(buff[4:8])
		self.numedges = shared_c.LittleSShort(buff[8:10])
		self.texinfo = shared_c.LittleSShort(buff[10:12])
		self.styles = [buff[12 + i] for i in range(MAXLIGHTMAPS)]
		self.lightofs = shared_c.LittleLong(buff[16:20])


# note that edge 0 is never used, because negative edge nums are used for
# counterclockwise use of the edge in a face
class dedge_t(object):

	def __init__(self):

		self.v = np.zeros((2,), dtype=np.uint16)

	@classmethod
	def packed_size(cls):
		return 4

	def load(self, buff):

		self.v[0] = shared_c.LittleShort(buff[:2])
		self.v[1] = shared_c.LittleShort(buff[2:])

class dleaf_t(object):

	def __init__(self):

		self.contents = None # int, OR of all brushes (not needed?)

		self.cluster = None # short
		self.area = None # short

		self.mins = np.zeros((3,), dtype=np.int16) # short[3]			# for frustum culling
		self.maxs = np.zeros((3,), dtype=np.int16) # short[3]

		self.firstleafface = None # unsigned short
		self.numleaffaces = None # unsigned short

		self.firstleafbrush = None # unsigned short
		self.numleafbrushes = None # unsigned short

	@classmethod
	def packed_size(cls):
		return 28

	def load(self, buff):

		self.contents = shared_c.LittleSLong(buff[:4]) # int
		self.cluster = shared_c.LittleSShort (buff[4:6]) # short, -1 for no cluster
		self.area = shared_c.LittleSShort (buff[6:8]) # short
		c = 8
		for i in range(3):
			self.mins[i] = shared_c.LittleSShort(buff[c:c+2])
			c += 2
		for i in range(3):
			self.maxs[i] = shared_c.LittleSShort(buff[c:c+2])
			c += 2
		self.firstleafface = shared_c.LittleShort(buff[c:c+2]) # unsigned short
		c += 2
		self.numleaffaces = shared_c.LittleShort(buff[c:c+2]) # unsigned short
		c += 2
		self.firstleafbrush = shared_c.LittleShort(buff[c:c+2]) # unsigned short
		c += 2
		self.numleafbrushes = shared_c.LittleShort(buff[c:c+2]) # unsigned short


class dbrushside_t(object):

	def __init__(self):

		self.planenum = None # unsigned short, facing out of the leaf
		self.texinfo = None # short

	@classmethod
	def packed_size(cls):
		return 4

	def load(self, buff):

		self.planenum = shared_c.LittleShort (buff[:2])
		self.texinfo = shared_c.LittleSShort (buff[2:])

class dbrush_t(object):

	def __init__(self):

		self.firstside = None # int
		self.numsides = None # int
		self.contents = None # int

	@classmethod
	def packed_size(cls):
		return 12

	def load(self, buff):

		self.firstside = shared_c.LittleLong (buff[:4])
		self.numsides = shared_c.LittleLong (buff[4:8])
		self.contents = shared_c.LittleLong (buff[8:])

ANGLE_UP   = -1
ANGLE_DOWN = -2


# the visibility lump consists of a header with a count, then
# byte offsets for the PVS and PHS of each cluster, then the raw
# compressed bit vectors
DVIS_PVS	= 0
DVIS_PHS	= 1
class dvis_t(object):

	def __init__(self):

		self.numclusters = None # int
		self.bitofs = np.zeros((8,2), dtype=np.int32) # int[8][2], bitofs[numclusters][2]
		self.data = None # bytes

	@classmethod
	def packed_size(cls):
		return 68

	def load(self, buff):

		self.numclusters = shared_c.LittleSLong (buff[:4])
		self.data = buff
		# int[8] in C is a variable length array trick, the lump really holds numclusters entries
		self.bitofs = np.zeros((self.numclusters, 2), dtype=np.int32)
		c = 4

		for i in range(self.numclusters):
		
			self.bitofs[i][0] = shared_c.LittleLong (buff[c:c+4])
			c += 4
			self.bitofs[i][1] = shared_c.LittleLong (buff[c:c+4])
			c += 4

# each area has a list of portals that lead into other areas
# when portals are closed, other areas may not be visible or
# hearable even if the vis info says that it should be
class dareaportal_t(object):

	def __init__(self):
		self.portalnum = 0 # int		
		self.otherarea = 0 # int

	@classmethod
	def packed_size(cls):
		return 8

	def load(self, buff):

		self.portalnum = shared_c.LittleSLong (buff[:4])
		self.otherarea = shared_c.LittleSLong (buff[4:])

class darea_t(object):

	def __init__(self):

		self.numareaportals = None # int
		self.firstareaportal = None # int

	@classmethod
	def packed_size(cls):
		return 8

	def load(self, buff):

		self.numareaportals = shared_c.LittleSLong (buff[:4])
		self.firstareaportal = shared_c.LittleSLong (buff[4:])
