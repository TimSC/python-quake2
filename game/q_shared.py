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
import struct
import math
import re
from enum import Enum
import numpy as np
"""
// q_shared.h -- included first by ALL program modules

#ifdef _WIN32
// unknown pragmas are SUPPOSED to be ignored, but....
#pragma warning(disable : 4244)     // MIPS
#pragma warning(disable : 4136)     // X86
#pragma warning(disable : 4051)     // ALPHA

#pragma warning(disable : 4018)     // signed/unsigned mismatch
#pragma warning(disable : 4305)		// truncation from const double to float

#endif

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#if (defined _M_IX86 || defined __i386__) && !defined C_ONLY && !defined __sun__
#define id386	1
#else
#define id386	0
#endif

#if defined _M_ALPHA && !defined C_ONLY
#define idaxp	1
#else
#define idaxp	0
#endif

typedef unsigned char 		byte;
typedef enum {false, true}	qboolean;


#ifndef NULL
#define NULL ((void *)0)
#endif

"""
# angle indexes
PITCH = 0	# up / down
YAW = 1		# left / right
ROLL = 2	# fall over

MAX_STRING_CHARS = 1024	# max length of a string passed to Cmd_TokenizeString

MAX_STRING_TOKENS = 80		# max tokens resulting from Cmd_TokenizeString
MAX_TOKEN_CHARS = 128		# max length of an individual token

MAX_QPATH			= 64		# max length of a quake game pathname
MAX_OSPATH			= 128		# max length of a filesystem pathname

#
# per-level limits
#
MAX_CLIENTS			= 256		# absolute limit
MAX_EDICTS			= 1024	# must change protocol to increase more
MAX_LIGHTSTYLES		= 256
MAX_MODELS			= 256		# these are sent over the net as bytes
MAX_SOUNDS 			= 256		# so they cannot be blindly increased

MAX_IMAGES			= 256
MAX_ITEMS			= 256
MAX_GENERAL			= (MAX_CLIENTS*2)	# general config strings


# game print flags
PRINT_LOW			= 0		# pickup messages
PRINT_MEDIUM		= 1		# death messages
PRINT_HIGH			= 2		# critical messages
PRINT_CHAT			= 3		# chat messages



ERR_FATAL			= 0		# exit the entire game with a popup window
ERR_DROP			= 1		# print to console and disconnect from game
ERR_DISCONNECT		= 2		# don't kill server

PRINT_ALL			= 0
PRINT_DEVELOPER		= 1		# only print when "developer 1"
PRINT_ALERT			= 2		

# destination class for gi.multicast()
class multicast_t(Enum):

	MULTICAST_ALL = 0
	MULTICAST_PHS = 1
	MULTICAST_PVS = 2
	MULTICAST_ALL_R = 3
	MULTICAST_PHS_R = 4
	MULTICAST_PVS_R = 5

"""

/*
==============================================================

MATHLIB

==============================================================
*/
"""
vec_t = np.float32 #typedef float vec_t;
vec3_t = np.ndarray # typedef vec_t vec3_t[3];
vec5_t = np.ndarray # typedef vec_t [5];
"""
typedef	int	fixed4_t;
typedef	int	fixed8_t;
typedef	int	fixed16_t;

#ifndef M_PI
#define M_PI		3.14159265358979323846	// matches value in gcc v2 math.h
#endif

struct cplane_s;

extern vec3_t vec3_origin;

#define	nanmask (255<<23)

#define	IS_NAN(x) (((*(int *)&x)&nanmask)==nanmask)

// microsoft's fabs seems to be ungodly slow...
//float Q_fabs (float f);
//#define	fabs(f) Q_fabs(f)
#if !defined C_ONLY && !defined __linux__ && !defined __sgi
extern long Q_ftol( float f );
#else
#define Q_ftol( f ) ( long ) (f)
#endif

#define DotProduct(x,y)			(x[0]*y[0]+x[1]*y[1]+x[2]*y[2])
#define VectorSubtract(a,b,c)	(c[0]=a[0]-b[0],c[1]=a[1]-b[1],c[2]=a[2]-b[2])
#define VectorAdd(a,b,c)		(c[0]=a[0]+b[0],c[1]=a[1]+b[1],c[2]=a[2]+b[2])
"""
def Q_ftol(f):
	return int(f)

def VectorCopy(a,b): b[:]=a[:]
def VectorAdd(a, b, out): out[:] = [a[i] + b[i] for i in range(3)]
def VectorSubtract(a, b, out): out[:] = [a[i] - b[i] for i in range(3)]
def VectorScale(vec, scale, out): out[:] = [vec[i] * scale for i in range(3)]
def VectorMA(veca, scale, vecb, vecc): vecc[:] = [veca[i] + scale * vecb[i] for i in range(3)]

def DotProduct(v1, v2):
	return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]

def CrossProduct(v1, v2, cross):
	cross[0] = v1[1]*v2[2] - v1[2]*v2[1]
	cross[1] = v1[2]*v2[0] - v1[0]*v2[2]
	cross[2] = v1[0]*v2[1] - v1[1]*v2[0]

def VectorNormalize(v):
	length = v[0]*v[0] + v[1]*v[1] + v[2]*v[2]
	length = math.sqrt(length)
	if length:
		ilength = 1.0 / length
		v[0] *= ilength
		v[1] *= ilength
		v[2] *= ilength
	return length

def VectorNormalize2(v, out):
	length = v[0]*v[0] + v[1]*v[1] + v[2]*v[2]
	length = math.sqrt(length)
	if length:
		ilength = 1.0 / length
		out[0] = v[0]*ilength
		out[1] = v[1]*ilength
		out[2] = v[2]*ilength
	return length

def VectorLength(v):
	return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

def VectorCompare (v1, v2): #vec3_t, vec3_t (returns int)

	if v1[0] != v2[0] or v1[1] != v2[1] or v1[2] != v2[2]:
		return 0

	return 1


def ProjectPointOnPlane(dst, p, normal):
	if dst is None or p is None or normal is None:
		return

	denom = DotProduct(normal, normal)
	if denom == 0.0:
		dst[0] = p[0]
		dst[1] = p[1]
		dst[2] = p[2]
		return

	inv_denom = 1.0 / denom
	d = DotProduct(normal, p) * inv_denom

	dst[0] = p[0] - d * normal[0] * inv_denom
	dst[1] = p[1] - d * normal[1] * inv_denom
	dst[2] = p[2] - d * normal[2] * inv_denom


def PerpendicularVector(dst, src):
	minelem = 1.0
	pos = 0
	for i in range(3):
		val = abs(src[i])
		if val < minelem:
			pos = i
			minelem = val

	tempvec = np.zeros((3,), dtype=np.float32)
	tempvec[pos] = 1.0

	ProjectPointOnPlane(dst, tempvec, src)
	VectorNormalize(dst)


def RotatePointAroundVector(dst, dir, point, degrees):
	axis = np.array(dir, dtype=np.float32)
	length = math.sqrt(axis[0]**2 + axis[1]**2 + axis[2]**2)
	if length == 0.0:
		dst[0] = point[0]
		dst[1] = point[1]
		dst[2] = point[2]
		return

	axis /= length
	radians = math.radians(degrees)
	cos_ang = math.cos(radians)
	sin_ang = math.sin(radians)
	dot = DotProduct(axis, point)
	cross = np.zeros((3,), dtype=np.float32)
	CrossProduct(axis, point, cross)

	dst[0] = point[0] * cos_ang + cross[0] * sin_ang + axis[0] * dot * (1.0 - cos_ang)
	dst[1] = point[1] * cos_ang + cross[1] * sin_ang + axis[1] * dot * (1.0 - cos_ang)
	dst[2] = point[2] * cos_ang + cross[2] * sin_ang + axis[2] * dot * (1.0 - cos_ang)

def VectorInverse(v):
	v[0] = -v[0]
	v[1] = -v[1]
	v[2] = -v[2]

def VectorNegate(a, b):
	b[0] = -a[0]
	b[1] = -a[1]
	b[2] = -a[2]

def VectorSet(v, x, y, z):
	v[0] = x
	v[1] = y
	v[2] = z

def LerpAngle(a2, a1, frac):
	if a1 - a2 > 180:
		a1 -= 360
	if a1 - a2 < -180:
		a1 += 360
	return a2 + frac * (a1 - a2)

def anglemod(a):
	return (360.0 / 65536.0) * (int(a * (65536.0 / 360.0)) & 65535)

def AngleVectors(angles, forward, right, up):
	pitch = math.radians(angles[PITCH])
	yaw = math.radians(angles[YAW])
	roll = math.radians(angles[ROLL])

	sp = math.sin(pitch)
	cp = math.cos(pitch)
	sy = math.sin(yaw)
	cy = math.cos(yaw)
	sr = math.sin(roll)
	cr = math.cos(roll)

	if forward is not None:
		forward[0] = cp * cy
		forward[1] = cp * sy
		forward[2] = -sp
	if right is not None:
		right[0] = (-sr * sp * cy) + (-cr * -sy)
		right[1] = (-sr * sp * sy) + (-cr * cy)
		right[2] = -sr * cp
	if up is not None:
		up[0] = (cr * sp * cy) + (-sr * -sy)
		up[1] = (cr * sp * sy) + (-sr * cy)
		up[2] = cr * cp
def VectorClear(a):	a[0]=0;a[1]=0;a[2]=0
vec3_origin = np.zeros((3,), dtype=np.float32)

def BoxOnPlaneSide2(emins, emaxs, plane):
	corners = np.empty((2, 3), dtype=np.float32)
	for i in range(3):
		if plane.normal[i] < 0:
			corners[0][i] = emins[i]
			corners[1][i] = emaxs[i]
		else:
			corners[0][i] = emaxs[i]
			corners[1][i] = emins[i]

	dist1 = DotProduct(plane.normal, corners[0]) - plane.dist
	dist2 = DotProduct(plane.normal, corners[1]) - plane.dist
	sides = 0
	if dist1 >= 0:
		sides = 1
	if dist2 < 0:
		sides |= 2
	return sides

def BoxOnPlaneSide(emins, emaxs, plane):
	if plane.type < 3:
		if plane.dist <= emins[plane.type]:
			return 1
		if plane.dist >= emaxs[plane.type]:
			return 2
		return 3

	#Q2PORT: the two extreme corners, vectorised
	n = plane.normal
	dist1 = float(n @ np.where(n < 0, emins, emaxs))
	dist2 = float(n @ np.where(n < 0, emaxs, emins))

	sides = 0
	if dist1 >= plane.dist:
		sides = 1
	if dist2 < plane.dist:
		sides |= 2

	if sides == 0:
		raise AssertionError("BoxOnPlaneSide returned no sides")

	return sides

"""
#define VectorNegate(a,b)		(b[0]=-a[0],b[1]=-a[1],b[2]=-a[2])
#define VectorSet(v, x, y, z)	(v[0]=(x), v[1]=(y), v[2]=(z))

void VectorMA (vec3_t veca, float scale, vec3_t vecb, vec3_t vecc);

// just in case you do't want to use the macros
vec_t _DotProduct (vec3_t v1, vec3_t v2);
void _VectorSubtract (vec3_t veca, vec3_t vecb, vec3_t out);
void _VectorAdd (vec3_t veca, vec3_t vecb, vec3_t out);
void _VectorCopy (vec3_t in, vec3_t out);

void ClearBounds (vec3_t mins, vec3_t maxs);
void AddPointToBounds (vec3_t v, vec3_t mins, vec3_t maxs);
int VectorCompare (vec3_t v1, vec3_t v2);
vec_t VectorLength (vec3_t v);
void CrossProduct (vec3_t v1, vec3_t v2, vec3_t cross);
vec_t VectorNormalize (vec3_t v);		// returns vector length
vec_t VectorNormalize2 (vec3_t v, vec3_t out);
void VectorInverse (vec3_t v);
void VectorScale (vec3_t in, vec_t scale, vec3_t out);
int Q_log2(int val);

void R_ConcatRotations (float in1[3][3], float in2[3][3], float out[3][3]);
void R_ConcatTransforms (float in1[3][4], float in2[3][4], float out[3][4]);

void AngleVectors (vec3_t angles, vec3_t forward, vec3_t right, vec3_t up);
int BoxOnPlaneSide (vec3_t emins, vec3_t emaxs, struct cplane_s *plane);
float	anglemod(float a);
float LerpAngle (float a1, float a2, float frac);

#define BOX_ON_PLANE_SIDE(emins, emaxs, p)	\
	(((p)->type < 3)?						\
	(										\
		((p)->dist <= (emins)[(p)->type])?	\
			1								\
		:									\
		(									\
			((p)->dist >= (emaxs)[(p)->type])?\
				2							\
			:								\
				3							\
		)									\
	)										\
	:										\
		BoxOnPlaneSide( (emins), (emaxs), (p)))

void ProjectPointOnPlane( vec3_t dst, const vec3_t p, const vec3_t normal );
void PerpendicularVector( vec3_t dst, const vec3_t src );
void RotatePointAroundVector( vec3_t dst, const vec3_t dir, const vec3_t point, float degrees );


//=============================================

char *COM_SkipPath (char *pathname);
void COM_StripExtension (char *in, char *out);
void COM_FileBase (char *in, char *out);
void COM_FilePath (char *in, char *out);
void COM_DefaultExtension (char *path, char *extension);

char *COM_Parse (char **data_p);
// data is an in/out parm, returns a parsed out token

void Com_sprintf (char *dest, int size, char *fmt, ...);

void Com_PageInMemory (byte *buffer, int size);

//=============================================

// portable case insensitive compare
int Q_stricmp (char *s1, char *s2);
int Q_strcasecmp (char *s1, char *s2);
int Q_strncasecmp (char *s1, char *s2, int n);

//=============================================

short	BigShort(short l);
short	LittleShort(short l);
int		BigLong (int l);
int		LittleLong (int l);
float	BigFloat (float l);
float	LittleFloat (float l);

void	Swap_Init (void);
char	*va(char *format, ...);

//=============================================
"""
#
# key / value info strings
#
MAX_INFO_KEY		= 64
MAX_INFO_VALUE		= 64
MAX_INFO_STRING		= 512
"""
char *Info_ValueForKey (char *s, char *key);
void Info_RemoveKey (char *s, char *key);
void Info_SetValueForKey (char *s, char *key, char *value);
qboolean Info_Validate (char *s);

/*
==============================================================

SYSTEM SPECIFIC

==============================================================
*/

extern	int	curtime;		// time returned by last Sys_Milliseconds

int		Sys_Milliseconds (void);
void	Sys_Mkdir (char *path);

// large block stack allocation routines
void	*Hunk_Begin (int maxsize);
void	*Hunk_Alloc (int size);
void	Hunk_Free (void *buf);
int		Hunk_End (void);
"""
# directory searching
SFF_ARCH    = 0x01
SFF_HIDDEN  = 0x02
SFF_RDONLY  = 0x04
SFF_SUBDIR  = 0x08
SFF_SYSTEM  = 0x10
"""
/*
** pass in an attribute mask of things you wish to REJECT
*/
char	*Sys_FindFirst (char *path, unsigned musthave, unsigned canthave );
char	*Sys_FindNext ( unsigned musthave, unsigned canthave );
void	Sys_FindClose (void);


// this is only here so the functions in q_shared.c and q_shwin.c can link
void Sys_Error (char *error, ...);
void Com_Printf (char *msg, ...);


/*
==========================================================

CVARS (console variables)

==========================================================
*/

#ifndef CVAR
#define	CVAR
"""

CVAR_ARCHIVE	= 1	# set to cause it to be saved to vars.rc
CVAR_USERINFO	= 2	# added to userinfo  when changed
CVAR_SERVERINFO	= 4	# added to serverinfo when changed
CVAR_NOSET		= 8	# don't allow change from console at all,
							# but can be set from the command line
CVAR_LATCH		= 16	# save changes until server restart

# nothing outside the Cvar_*() functions should modify these fields!
class cvar_t(object):

	def __init__(self):

		self.name = None #char *
		self.string = None #char	*
		self.latched_string = None #char	*, for CVAR_LATCH vars
		self.flags = None #int
		self.modified = None #qboolean, set each time the cvar is changed
		self.value = None #float

"""

#endif		// CVAR

/*
==============================================================

COLLISION DETECTION

==============================================================
*/

// lower bits are stronger, and will eat weaker brushes completely
#define	CONTENTS_SOLID			1		// an eye is never valid in a solid
#define	CONTENTS_WINDOW			2		// translucent, but not watery
#define	CONTENTS_AUX			4
#define	CONTENTS_LAVA			8
#define	CONTENTS_SLIME			16
#define	CONTENTS_WATER			32
#define	CONTENTS_MIST			64
#define	LAST_VISIBLE_CONTENTS	64

// remaining contents are non-visible, and don't eat brushes

#define	CONTENTS_AREAPORTAL		0x8000

#define	CONTENTS_PLAYERCLIP		0x10000
#define	CONTENTS_MONSTERCLIP	0x20000

// currents can be added to any other contents, and may be mixed
#define	CONTENTS_CURRENT_0		0x40000
#define	CONTENTS_CURRENT_90		0x80000
#define	CONTENTS_CURRENT_180	0x100000
#define	CONTENTS_CURRENT_270	0x200000
#define	CONTENTS_CURRENT_UP		0x400000
#define	CONTENTS_CURRENT_DOWN	0x800000

#define	CONTENTS_ORIGIN			0x1000000	// removed before bsping an entity

#define	CONTENTS_MONSTER		0x2000000	// should never be on a brush, only in game
#define	CONTENTS_DEADMONSTER	0x4000000
#define	CONTENTS_DETAIL			0x8000000	// brushes to be added after vis leafs
#define	CONTENTS_TRANSLUCENT	0x10000000	// auto set if any surface has trans
#define	CONTENTS_LADDER			0x20000000



#define	SURF_LIGHT		0x1		// value will hold the light strength

#define	SURF_PLANEBACK	2
#define	SURF_PLANEBACK		2
#define	SURF_SLICK		0x2		// effects game physics

#define	SURF_SKY		0x4		// don't draw, but add to skybox
#define	SURF_WARP		0x8		// turbulent water warp
#define	SURF_TRANS33	0x10
#define	SURF_TRANS66	0x20
#define	SURF_FLOWING	0x40	// scroll towards angle
#define	SURF_NODRAW		0x80	// don't bother referencing the texture



// content masks
#define	MASK_ALL				(-1)
#define	MASK_SOLID				(CONTENTS_SOLID|CONTENTS_WINDOW)
#define	MASK_PLAYERSOLID		(CONTENTS_SOLID|CONTENTS_PLAYERCLIP|CONTENTS_WINDOW|CONTENTS_MONSTER)
#define	MASK_DEADSOLID			(CONTENTS_SOLID|CONTENTS_PLAYERCLIP|CONTENTS_WINDOW)
#define	MASK_MONSTERSOLID		(CONTENTS_SOLID|CONTENTS_MONSTERCLIP|CONTENTS_WINDOW|CONTENTS_MONSTER)
#define	MASK_WATER				(CONTENTS_WATER|CONTENTS_LAVA|CONTENTS_SLIME)
#define	MASK_OPAQUE				(CONTENTS_SOLID|CONTENTS_SLIME|CONTENTS_LAVA)
#define	MASK_SHOT				(CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_WINDOW|CONTENTS_DEADMONSTER)
#define MASK_CURRENT			(CONTENTS_CURRENT_0|CONTENTS_CURRENT_90|CONTENTS_CURRENT_180|CONTENTS_CURRENT_270|CONTENTS_CURRENT_UP|CONTENTS_CURRENT_DOWN)


// gi.BoxEdicts() can return a list of either solid or trigger entities
// FIXME: eliminate AREA_ distinction?
#define	AREA_SOLID		1
#define	AREA_TRIGGERS	2

"""
CONTENTS_SOLID = 1
CONTENTS_WINDOW = 2
CONTENTS_AUX = 4
CONTENTS_LAVA = 8
CONTENTS_SLIME = 16
CONTENTS_WATER = 32
CONTENTS_MIST = 64
LAST_VISIBLE_CONTENTS = 64
CONTENTS_AREAPORTAL = 0x8000
CONTENTS_PLAYERCLIP = 0x10000
CONTENTS_MONSTERCLIP = 0x20000
CONTENTS_CURRENT_0 = 0x40000
CONTENTS_CURRENT_90 = 0x80000
CONTENTS_CURRENT_180 = 0x100000
CONTENTS_CURRENT_270 = 0x200000
CONTENTS_CURRENT_UP = 0x400000
CONTENTS_CURRENT_DOWN = 0x800000
CONTENTS_ORIGIN = 0x1000000
CONTENTS_MONSTER = 0x2000000
CONTENTS_DEADMONSTER = 0x4000000
CONTENTS_DETAIL = 0x8000000
CONTENTS_TRANSLUCENT = 0x10000000
CONTENTS_LADDER = 0x20000000

SURF_LIGHT = 0x1
SURF_PLANEBACK = 0x2
SURF_SLICK = 0x2
SURF_SKY = 0x4
SURF_WARP = 0x8
SURF_TRANS33 = 0x10
SURF_TRANS66 = 0x20
SURF_FLOWING = 0x40
SURF_NODRAW = 0x80

MASK_ALL = -1
MASK_SOLID = (CONTENTS_SOLID | CONTENTS_WINDOW)
MASK_PLAYERSOLID = (CONTENTS_SOLID | CONTENTS_PLAYERCLIP | CONTENTS_WINDOW | CONTENTS_MONSTER)
MASK_DEADSOLID = (CONTENTS_SOLID | CONTENTS_PLAYERCLIP | CONTENTS_WINDOW)
MASK_MONSTERSOLID = (CONTENTS_SOLID | CONTENTS_MONSTERCLIP | CONTENTS_WINDOW | CONTENTS_MONSTER)
MASK_WATER = (CONTENTS_WATER | CONTENTS_LAVA | CONTENTS_SLIME)
MASK_OPAQUE = (CONTENTS_SOLID | CONTENTS_SLIME | CONTENTS_LAVA)
MASK_SHOT = (CONTENTS_SOLID | CONTENTS_MONSTER | CONTENTS_WINDOW | CONTENTS_DEADMONSTER)
MASK_CURRENT = (
	CONTENTS_CURRENT_0
	| CONTENTS_CURRENT_90
	| CONTENTS_CURRENT_180
	| CONTENTS_CURRENT_270
	| CONTENTS_CURRENT_UP
	| CONTENTS_CURRENT_DOWN
)

AREA_SOLID = 1
AREA_TRIGGERS = 2

# plane_t structure
# !!! if this is changed, it must be changed in asm code too !!!
class cplane_t(object):

	def __init__(self):

		self.normal = np.zeros((3,), dtype=np.float32) # vec3_t
		self.dist = 0.0 # float
		self.type = 0 # byte, for fast side tests
		self.signbits = None # byte, signx + (signy<<1) + (signz<<1)
		self.pad = [None, None] #byte [2]

# structure offset for asm code
CPLANE_NORMAL_X			= 0
CPLANE_NORMAL_Y			= 4
CPLANE_NORMAL_Z			= 8
CPLANE_DIST				= 12
CPLANE_TYPE				= 16
CPLANE_SIGNBITS			= 17
CPLANE_PAD0				= 18
CPLANE_PAD1				= 19

class cmodel_t(object):

	def __init__(self):

		self.mins = np.zeros((3,), dtype=np.float32)
		self.maxs = np.zeros((3,), dtype=np.float32) #vec3_t
		self.origin = np.zeros((3,), dtype=np.float32) #vec3_t, for sounds or lights
		self.headnode = None # int			

class csurface_t(object):

	def __init__(self):

		self.name = "" # char[16], zeroed as C statics are (nullsurface relies on it)
		self.flags = 0 # int
		self.value = 0 # int

class mapsurface_t(object):  # used internally due to name len probs //ZOID

	def __init__(self):

		self.c = csurface_t()
		self.rname = None # char [32]

"""
// a trace is returned when a box is swept through the world
typedef struct
{
	qboolean	allsolid;	// if true, plane is not valid
	qboolean	startsolid;	// if true, the initial point was in a solid area
	float		fraction;	// time completed, 1.0 = didn't hit anything
	vec3_t		endpos;		// final position
	cplane_t	plane;		// surface normal at impact
	csurface_t	*surface;	// surface hit
	int			contents;	// contents on other side of surface hit
	struct edict_s	*ent;		// not set by CM_*() functions
} trace_t;

"""
class trace_t(object):

	def __init__(self):
		self.allsolid = False
		self.startsolid = False
		self.fraction = 1.0
		self.endpos = np.zeros((3,), dtype=np.float32)
		self.plane = cplane_t()
		self.surface = csurface_t()
		self.contents = 0
		self.ent = None

	def copy(self): # Q2PORT: struct assignment; plane is copied by value, surface and ent are pointers
		t = trace_t()
		t.allsolid = self.allsolid
		t.startsolid = self.startsolid
		t.fraction = self.fraction
		t.endpos = np.array(self.endpos, dtype=np.float32)
		t.plane.normal = np.array(self.plane.normal, dtype=np.float32)
		t.plane.dist = self.plane.dist
		t.plane.type = self.plane.type
		t.plane.signbits = self.plane.signbits
		t.plane.pad = list(self.plane.pad)
		t.surface = self.surface
		t.contents = self.contents
		t.ent = self.ent
		return t


# pmove_state_t is the information necessary for client side movement
# prediction
class pmtype_t(Enum):

	# can accelerate and turn
	PM_NORMAL = 0
	PM_SPECTATOR = 1
	# no acceleration or turning
	PM_DEAD = 2
	PM_GIB = 3		# different bounding box
	PM_FREEZE = 4

"""
# pmove->pm_flags
#define	PMF_DUCKED			1
#define	PMF_JUMP_HELD		2
#define	PMF_ON_GROUND		4
#define	PMF_TIME_WATERJUMP	8	// pm_time is waterjump
#define	PMF_TIME_LAND		16	// pm_time is time before rejump
#define	PMF_TIME_TELEPORT	32	// pm_time is non-moving time
#define PMF_NO_PREDICTION	64	// temporarily disables prediction (used for grappling hook)

// this structure needs to be communicated bit-accurate
// from the server to the client to guarantee that
// prediction stays in sync, so no floats are used.
// if any part of the game code modifies this struct, it
// will result in a prediction error of some degree.
"""
PMF_DUCKED = 1
PMF_JUMP_HELD = 2
PMF_ON_GROUND = 4
PMF_TIME_WATERJUMP = 8
PMF_TIME_LAND = 16
PMF_TIME_TELEPORT = 32
PMF_NO_PREDICTION = 64

class pmove_state_t(object):

	def __init__(self):
		self.pm_type = pmtype_t.PM_NORMAL.value

		self.origin = np.zeros((3,), dtype=np.int16) # short		[3];		// 12.3
		self.velocity = np.zeros((3,), dtype=np.int16) #short		[3];	// 12.3
		self.pm_flags = 0 #byte		;		// ducked, jump_held, etc
		self.pm_time = 0 #byte		;		// each unit = 8 ms
		self.gravity = 0 #short		;
		self.delta_angles = np.zeros((3,), dtype=np.int16) #short		[3];	// add to command angles to get view direction
									# changed by spawns, rotating objects, and teleporters



#
# button bits
#
BUTTON_ATTACK		= 1
BUTTON_USE			= 2
BUTTON_ANY			= 128			# any key whatsoever

# usercmd_t is sent to the server each client frame
class usercmd_t(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.msec = 0 #byte	
		self.buttons = 0 #byte	
		self.angles = [0, 0, 0] #short	[3]
		self.forwardmove = 0 #short
		self.sidemove = 0 #short	
		self.upmove = 0 #short	
		self.impulse = 0 #byte, remove?
		self.lightlevel = 0 #byte, light level the player is standing on

"""

#define	MAXTOUCH	32
typedef struct
{
	// state (in / out)
	pmove_state_t	s;

	// command (in)
	usercmd_t		cmd;
	qboolean		snapinitial;	// if s has been changed outside pmove

	// results (out)
	int			numtouch;
	struct edict_s	*touchents[MAXTOUCH];

	vec3_t		viewangles;			// clamped
	float		viewheight;

	vec3_t		mins, maxs;			// bounding box size

	struct edict_s	*groundentity;
	int			watertype;
	int			waterlevel;

	// callbacks to test the world
	trace_t		(*trace) (vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end);
	int			(*pointcontents) (vec3_t point);
} pmove_t;


// entity_state_t->effects
// Effects are things handled on the client side (lights, particles, frame animations)
// that happen constantly on the given entity.
// An entity that has effects will be sent to the client
// even if it has a zero index model.
#define	EF_ROTATE			0x00000001		// rotate (bonus items)
#define	EF_GIB				0x00000002		// leave a trail
#define	EF_BLASTER			0x00000008		// redlight + trail
#define	EF_ROCKET			0x00000010		// redlight + trail
#define	EF_GRENADE			0x00000020
#define	EF_HYPERBLASTER		0x00000040
#define	EF_BFG				0x00000080
#define EF_COLOR_SHELL		0x00000100
#define EF_POWERSCREEN		0x00000200
#define	EF_ANIM01			0x00000400		// automatically cycle between frames 0 and 1 at 2 hz
#define	EF_ANIM23			0x00000800		// automatically cycle between frames 2 and 3 at 2 hz
#define EF_ANIM_ALL			0x00001000		// automatically cycle through all frames at 2hz
#define EF_ANIM_ALLFAST		0x00002000		// automatically cycle through all frames at 10hz
#define	EF_FLIES			0x00004000
#define	EF_QUAD				0x00008000
#define	EF_PENT				0x00010000
#define	EF_TELEPORTER		0x00020000		// particle fountain
#define EF_FLAG1			0x00040000
#define EF_FLAG2			0x00080000
// RAFAEL
#define EF_IONRIPPER		0x00100000
#define EF_GREENGIB			0x00200000
#define	EF_BLUEHYPERBLASTER 0x00400000
#define EF_SPINNINGLIGHTS	0x00800000
#define EF_PLASMA			0x01000000
#define EF_TRAP				0x02000000

//ROGUE
#define EF_TRACKER			0x04000000
#define	EF_DOUBLE			0x08000000
#define	EF_SPHERETRANS		0x10000000
#define EF_TAGTRAIL			0x20000000
#define EF_HALF_DAMAGE		0x40000000
#define EF_TRACKERTRAIL		0x80000000
//ROGUE
"""
# entity_state_t->effects (Python constants)
EF_ROTATE = 0x00000001
EF_GIB = 0x00000002
EF_BLASTER = 0x00000008
EF_ROCKET = 0x00000010
EF_GRENADE = 0x00000020
EF_HYPERBLASTER = 0x00000040
EF_BFG = 0x00000080
EF_COLOR_SHELL = 0x00000100
EF_POWERSCREEN = 0x00000200
EF_ANIM01 = 0x00000400
EF_ANIM23 = 0x00000800
EF_ANIM_ALL = 0x00001000
EF_ANIM_ALLFAST = 0x00002000
EF_FLIES = 0x00004000
EF_QUAD = 0x00008000
EF_PENT = 0x00010000
EF_TELEPORTER = 0x00020000
EF_FLAG1 = 0x00040000
EF_FLAG2 = 0x00080000
EF_IONRIPPER = 0x00100000
EF_GREENGIB = 0x00200000
EF_BLUEHYPERBLASTER = 0x00400000
EF_SPINNINGLIGHTS = 0x00800000
EF_PLASMA = 0x01000000
EF_TRAP = 0x02000000
EF_TRACKER = 0x04000000
EF_DOUBLE = 0x08000000
EF_SPHERETRANS = 0x10000000
EF_TAGTRAIL = 0x20000000
EF_HALF_DAMAGE = 0x40000000
EF_TRACKERTRAIL = 0x80000000
# entity_state_t->renderfx flags
RF_MINLIGHT			= 1		# allways have some light (viewmodel)
RF_VIEWERMODEL		= 2		# don't draw through eyes, only mirrors
RF_WEAPONMODEL		= 4		# only draw through eyes
RF_FULLBRIGHT		= 8		# allways draw full intensity
RF_DEPTHHACK		= 16		# for view weapon Z crunching
RF_TRANSLUCENT		= 32
RF_FRAMELERP		= 64
RF_BEAM				= 128
RF_CUSTOMSKIN		= 256		# skin is an index in image_precache
RF_GLOW				= 512		# pulse lighting for bonus items
RF_SHELL_RED		= 1024
RF_SHELL_GREEN		= 2048
RF_SHELL_BLUE		= 4096
# ROGUE renderfx flags
RF_IR_VISIBLE = 0x00008000
RF_SHELL_DOUBLE = 0x00010000
RF_SHELL_HALF_DAM = 0x00020000
RF_USE_DISGUISE = 0x00040000
"""
//ROGUE
#define RF_IR_VISIBLE		0x00008000		// 32768
#define	RF_SHELL_DOUBLE		0x00010000		// 65536
#define	RF_SHELL_HALF_DAM	0x00020000
#define RF_USE_DISGUISE		0x00040000
//ROGUE
"""
# player_state_t->refdef flags
RDF_UNDERWATER		= 1		# warp the screen as apropriate
RDF_NOWORLDMODEL	= 2		# used for player configuration screen
"""
//ROGUE
#define	RDF_IRGOGGLES		4
#define RDF_UVGOGGLES		8
//ROGUE
"""
RDF_IRGOGGLES		= 4
RDF_UVGOGGLES		= 8
#
# muzzle flashes / player effects
#
MZ_BLASTER			= 0
MZ_MACHINEGUN		= 1
MZ_SHOTGUN			= 2
MZ_CHAINGUN1		= 3
MZ_CHAINGUN2		= 4
MZ_CHAINGUN3		= 5
MZ_RAILGUN			= 6
MZ_ROCKET			= 7
MZ_GRENADE			= 8
MZ_LOGIN			= 9
MZ_LOGOUT			= 10
MZ_RESPAWN			= 11
MZ_BFG				= 12
MZ_SSHOTGUN			= 13
MZ_HYPERBLASTER		= 14
MZ_ITEMRESPAWN		= 15
# RAFAEL
MZ_IONRIPPER		= 16
MZ_BLUEHYPERBLASTER = 17
MZ_PHALANX			= 18
MZ_SILENCED			= 128		# bit flag ORed with one of the above numbers

#ROGUE
MZ_ETF_RIFLE		= 30
MZ_UNUSED			= 31
MZ_SHOTGUN2			= 32
MZ_HEATBEAM			= 33
MZ_BLASTER2			= 34
MZ_TRACKER			= 35
MZ_NUKE1			= 36
MZ_NUKE2			= 37
MZ_NUKE4			= 38
MZ_NUKE8			= 39
#ROGUE
"""
//
// monster muzzle flashes
//
#define MZ2_TANK_BLASTER_1				1
#define MZ2_TANK_BLASTER_2				2
#define MZ2_TANK_BLASTER_3				3
#define MZ2_TANK_MACHINEGUN_1			4
#define MZ2_TANK_MACHINEGUN_2			5
#define MZ2_TANK_MACHINEGUN_3			6
#define MZ2_TANK_MACHINEGUN_4			7
#define MZ2_TANK_MACHINEGUN_5			8
#define MZ2_TANK_MACHINEGUN_6			9
#define MZ2_TANK_MACHINEGUN_7			10
#define MZ2_TANK_MACHINEGUN_8			11
#define MZ2_TANK_MACHINEGUN_9			12
#define MZ2_TANK_MACHINEGUN_10			13
#define MZ2_TANK_MACHINEGUN_11			14
#define MZ2_TANK_MACHINEGUN_12			15
#define MZ2_TANK_MACHINEGUN_13			16
#define MZ2_TANK_MACHINEGUN_14			17
#define MZ2_TANK_MACHINEGUN_15			18
#define MZ2_TANK_MACHINEGUN_16			19
#define MZ2_TANK_MACHINEGUN_17			20
#define MZ2_TANK_MACHINEGUN_18			21
#define MZ2_TANK_MACHINEGUN_19			22
#define MZ2_TANK_ROCKET_1				23
#define MZ2_TANK_ROCKET_2				24
#define MZ2_TANK_ROCKET_3				25

#define MZ2_INFANTRY_MACHINEGUN_1		26
#define MZ2_INFANTRY_MACHINEGUN_2		27
#define MZ2_INFANTRY_MACHINEGUN_3		28
#define MZ2_INFANTRY_MACHINEGUN_4		29
#define MZ2_INFANTRY_MACHINEGUN_5		30
#define MZ2_INFANTRY_MACHINEGUN_6		31
#define MZ2_INFANTRY_MACHINEGUN_7		32
#define MZ2_INFANTRY_MACHINEGUN_8		33
#define MZ2_INFANTRY_MACHINEGUN_9		34
#define MZ2_INFANTRY_MACHINEGUN_10		35
#define MZ2_INFANTRY_MACHINEGUN_11		36
#define MZ2_INFANTRY_MACHINEGUN_12		37
#define MZ2_INFANTRY_MACHINEGUN_13		38

#define MZ2_SOLDIER_BLASTER_1			39
#define MZ2_SOLDIER_BLASTER_2			40
#define MZ2_SOLDIER_SHOTGUN_1			41
#define MZ2_SOLDIER_SHOTGUN_2			42
#define MZ2_SOLDIER_MACHINEGUN_1		43
#define MZ2_SOLDIER_MACHINEGUN_2		44

#define MZ2_GUNNER_MACHINEGUN_1			45
#define MZ2_GUNNER_MACHINEGUN_2			46
#define MZ2_GUNNER_MACHINEGUN_3			47
#define MZ2_GUNNER_MACHINEGUN_4			48
#define MZ2_GUNNER_MACHINEGUN_5			49
#define MZ2_GUNNER_MACHINEGUN_6			50
#define MZ2_GUNNER_MACHINEGUN_7			51
#define MZ2_GUNNER_MACHINEGUN_8			52
#define MZ2_GUNNER_GRENADE_1			53
#define MZ2_GUNNER_GRENADE_2			54
#define MZ2_GUNNER_GRENADE_3			55
#define MZ2_GUNNER_GRENADE_4			56

#define MZ2_CHICK_ROCKET_1				57

#define MZ2_FLYER_BLASTER_1				58
#define MZ2_FLYER_BLASTER_2				59

#define MZ2_MEDIC_BLASTER_1				60

#define MZ2_GLADIATOR_RAILGUN_1			61

#define MZ2_HOVER_BLASTER_1				62

#define MZ2_ACTOR_MACHINEGUN_1			63

#define MZ2_SUPERTANK_MACHINEGUN_1		64
#define MZ2_SUPERTANK_MACHINEGUN_2		65
#define MZ2_SUPERTANK_MACHINEGUN_3		66
#define MZ2_SUPERTANK_MACHINEGUN_4		67
#define MZ2_SUPERTANK_MACHINEGUN_5		68
#define MZ2_SUPERTANK_MACHINEGUN_6		69
#define MZ2_SUPERTANK_ROCKET_1			70
#define MZ2_SUPERTANK_ROCKET_2			71
#define MZ2_SUPERTANK_ROCKET_3			72

#define MZ2_BOSS2_MACHINEGUN_L1			73
#define MZ2_BOSS2_MACHINEGUN_L2			74
#define MZ2_BOSS2_MACHINEGUN_L3			75
#define MZ2_BOSS2_MACHINEGUN_L4			76
#define MZ2_BOSS2_MACHINEGUN_L5			77
#define MZ2_BOSS2_ROCKET_1				78
#define MZ2_BOSS2_ROCKET_2				79
#define MZ2_BOSS2_ROCKET_3				80
#define MZ2_BOSS2_ROCKET_4				81

#define MZ2_FLOAT_BLASTER_1				82

#define MZ2_SOLDIER_BLASTER_3			83
#define MZ2_SOLDIER_SHOTGUN_3			84
#define MZ2_SOLDIER_MACHINEGUN_3		85
#define MZ2_SOLDIER_BLASTER_4			86
#define MZ2_SOLDIER_SHOTGUN_4			87
#define MZ2_SOLDIER_MACHINEGUN_4		88
#define MZ2_SOLDIER_BLASTER_5			89
#define MZ2_SOLDIER_SHOTGUN_5			90
#define MZ2_SOLDIER_MACHINEGUN_5		91
#define MZ2_SOLDIER_BLASTER_6			92
#define MZ2_SOLDIER_SHOTGUN_6			93
#define MZ2_SOLDIER_MACHINEGUN_6		94
#define MZ2_SOLDIER_BLASTER_7			95
#define MZ2_SOLDIER_SHOTGUN_7			96
#define MZ2_SOLDIER_MACHINEGUN_7		97
#define MZ2_SOLDIER_BLASTER_8			98
#define MZ2_SOLDIER_SHOTGUN_8			99
#define MZ2_SOLDIER_MACHINEGUN_8		100

// --- Xian shit below ---
#define	MZ2_MAKRON_BFG					101
#define MZ2_MAKRON_BLASTER_1			102
#define MZ2_MAKRON_BLASTER_2			103
#define MZ2_MAKRON_BLASTER_3			104
#define MZ2_MAKRON_BLASTER_4			105
#define MZ2_MAKRON_BLASTER_5			106
#define MZ2_MAKRON_BLASTER_6			107
#define MZ2_MAKRON_BLASTER_7			108
#define MZ2_MAKRON_BLASTER_8			109
#define MZ2_MAKRON_BLASTER_9			110
#define MZ2_MAKRON_BLASTER_10			111
#define MZ2_MAKRON_BLASTER_11			112
#define MZ2_MAKRON_BLASTER_12			113
#define MZ2_MAKRON_BLASTER_13			114
#define MZ2_MAKRON_BLASTER_14			115
#define MZ2_MAKRON_BLASTER_15			116
#define MZ2_MAKRON_BLASTER_16			117
#define MZ2_MAKRON_BLASTER_17			118
#define MZ2_MAKRON_RAILGUN_1			119
#define	MZ2_JORG_MACHINEGUN_L1			120
#define	MZ2_JORG_MACHINEGUN_L2			121
#define	MZ2_JORG_MACHINEGUN_L3			122
#define	MZ2_JORG_MACHINEGUN_L4			123
#define	MZ2_JORG_MACHINEGUN_L5			124
#define	MZ2_JORG_MACHINEGUN_L6			125
#define	MZ2_JORG_MACHINEGUN_R1			126
#define	MZ2_JORG_MACHINEGUN_R2			127
#define	MZ2_JORG_MACHINEGUN_R3			128
#define	MZ2_JORG_MACHINEGUN_R4			129
#define MZ2_JORG_MACHINEGUN_R5			130
#define	MZ2_JORG_MACHINEGUN_R6			131
#define MZ2_JORG_BFG_1					132
#define MZ2_BOSS2_MACHINEGUN_R1			133
#define MZ2_BOSS2_MACHINEGUN_R2			134
#define MZ2_BOSS2_MACHINEGUN_R3			135
#define MZ2_BOSS2_MACHINEGUN_R4			136
#define MZ2_BOSS2_MACHINEGUN_R5			137

//ROGUE
#define	MZ2_CARRIER_MACHINEGUN_L1		138
#define	MZ2_CARRIER_MACHINEGUN_R1		139
#define	MZ2_CARRIER_GRENADE				140
#define MZ2_TURRET_MACHINEGUN			141
#define MZ2_TURRET_ROCKET				142
#define MZ2_TURRET_BLASTER				143
#define MZ2_STALKER_BLASTER				144
#define MZ2_DAEDALUS_BLASTER			145
#define MZ2_MEDIC_BLASTER_2				146
#define	MZ2_CARRIER_RAILGUN				147
#define	MZ2_WIDOW_DISRUPTOR				148
#define	MZ2_WIDOW_BLASTER				149
#define	MZ2_WIDOW_RAIL					150
#define	MZ2_WIDOW_PLASMABEAM			151		// PMM - not used
#define	MZ2_CARRIER_MACHINEGUN_L2		152
#define	MZ2_CARRIER_MACHINEGUN_R2		153
#define	MZ2_WIDOW_RAIL_LEFT				154
#define	MZ2_WIDOW_RAIL_RIGHT			155
#define	MZ2_WIDOW_BLASTER_SWEEP1		156
#define	MZ2_WIDOW_BLASTER_SWEEP2		157
#define	MZ2_WIDOW_BLASTER_SWEEP3		158
#define	MZ2_WIDOW_BLASTER_SWEEP4		159
#define	MZ2_WIDOW_BLASTER_SWEEP5		160
#define	MZ2_WIDOW_BLASTER_SWEEP6		161
#define	MZ2_WIDOW_BLASTER_SWEEP7		162
#define	MZ2_WIDOW_BLASTER_SWEEP8		163
#define	MZ2_WIDOW_BLASTER_SWEEP9		164
#define	MZ2_WIDOW_BLASTER_100			165
#define	MZ2_WIDOW_BLASTER_90			166
#define	MZ2_WIDOW_BLASTER_80			167
#define	MZ2_WIDOW_BLASTER_70			168
#define	MZ2_WIDOW_BLASTER_60			169
#define	MZ2_WIDOW_BLASTER_50			170
#define	MZ2_WIDOW_BLASTER_40			171
#define	MZ2_WIDOW_BLASTER_30			172
#define	MZ2_WIDOW_BLASTER_20			173
#define	MZ2_WIDOW_BLASTER_10			174
#define	MZ2_WIDOW_BLASTER_0				175
#define	MZ2_WIDOW_BLASTER_10L			176
#define	MZ2_WIDOW_BLASTER_20L			177
#define	MZ2_WIDOW_BLASTER_30L			178
#define	MZ2_WIDOW_BLASTER_40L			179
#define	MZ2_WIDOW_BLASTER_50L			180
#define	MZ2_WIDOW_BLASTER_60L			181
#define	MZ2_WIDOW_BLASTER_70L			182
#define	MZ2_WIDOW_RUN_1					183
#define	MZ2_WIDOW_RUN_2					184
#define	MZ2_WIDOW_RUN_3					185
#define	MZ2_WIDOW_RUN_4					186
#define	MZ2_WIDOW_RUN_5					187
#define	MZ2_WIDOW_RUN_6					188
#define	MZ2_WIDOW_RUN_7					189
#define	MZ2_WIDOW_RUN_8					190
#define	MZ2_CARRIER_ROCKET_1			191
#define	MZ2_CARRIER_ROCKET_2			192
#define	MZ2_CARRIER_ROCKET_3			193
#define	MZ2_CARRIER_ROCKET_4			194
#define	MZ2_WIDOW2_BEAMER_1				195
#define	MZ2_WIDOW2_BEAMER_2				196
#define	MZ2_WIDOW2_BEAMER_3				197
#define	MZ2_WIDOW2_BEAMER_4				198
#define	MZ2_WIDOW2_BEAMER_5				199
#define	MZ2_WIDOW2_BEAM_SWEEP_1			200
#define	MZ2_WIDOW2_BEAM_SWEEP_2			201
#define	MZ2_WIDOW2_BEAM_SWEEP_3			202
#define	MZ2_WIDOW2_BEAM_SWEEP_4			203
#define	MZ2_WIDOW2_BEAM_SWEEP_5			204
#define	MZ2_WIDOW2_BEAM_SWEEP_6			205
#define	MZ2_WIDOW2_BEAM_SWEEP_7			206
#define	MZ2_WIDOW2_BEAM_SWEEP_8			207
#define	MZ2_WIDOW2_BEAM_SWEEP_9			208
#define	MZ2_WIDOW2_BEAM_SWEEP_10		209
#define	MZ2_WIDOW2_BEAM_SWEEP_11		210

// ROGUE

extern	vec3_t monster_flash_offset [];

"""
# monster muzzle flashes, from the #define MZ2_ block above
MZ2_TANK_BLASTER_1 = 1
MZ2_TANK_BLASTER_2 = 2
MZ2_TANK_BLASTER_3 = 3
MZ2_TANK_MACHINEGUN_1 = 4
MZ2_TANK_MACHINEGUN_2 = 5
MZ2_TANK_MACHINEGUN_3 = 6
MZ2_TANK_MACHINEGUN_4 = 7
MZ2_TANK_MACHINEGUN_5 = 8
MZ2_TANK_MACHINEGUN_6 = 9
MZ2_TANK_MACHINEGUN_7 = 10
MZ2_TANK_MACHINEGUN_8 = 11
MZ2_TANK_MACHINEGUN_9 = 12
MZ2_TANK_MACHINEGUN_10 = 13
MZ2_TANK_MACHINEGUN_11 = 14
MZ2_TANK_MACHINEGUN_12 = 15
MZ2_TANK_MACHINEGUN_13 = 16
MZ2_TANK_MACHINEGUN_14 = 17
MZ2_TANK_MACHINEGUN_15 = 18
MZ2_TANK_MACHINEGUN_16 = 19
MZ2_TANK_MACHINEGUN_17 = 20
MZ2_TANK_MACHINEGUN_18 = 21
MZ2_TANK_MACHINEGUN_19 = 22
MZ2_TANK_ROCKET_1 = 23
MZ2_TANK_ROCKET_2 = 24
MZ2_TANK_ROCKET_3 = 25
MZ2_INFANTRY_MACHINEGUN_1 = 26
MZ2_INFANTRY_MACHINEGUN_2 = 27
MZ2_INFANTRY_MACHINEGUN_3 = 28
MZ2_INFANTRY_MACHINEGUN_4 = 29
MZ2_INFANTRY_MACHINEGUN_5 = 30
MZ2_INFANTRY_MACHINEGUN_6 = 31
MZ2_INFANTRY_MACHINEGUN_7 = 32
MZ2_INFANTRY_MACHINEGUN_8 = 33
MZ2_INFANTRY_MACHINEGUN_9 = 34
MZ2_INFANTRY_MACHINEGUN_10 = 35
MZ2_INFANTRY_MACHINEGUN_11 = 36
MZ2_INFANTRY_MACHINEGUN_12 = 37
MZ2_INFANTRY_MACHINEGUN_13 = 38
MZ2_SOLDIER_BLASTER_1 = 39
MZ2_SOLDIER_BLASTER_2 = 40
MZ2_SOLDIER_SHOTGUN_1 = 41
MZ2_SOLDIER_SHOTGUN_2 = 42
MZ2_SOLDIER_MACHINEGUN_1 = 43
MZ2_SOLDIER_MACHINEGUN_2 = 44
MZ2_GUNNER_MACHINEGUN_1 = 45
MZ2_GUNNER_MACHINEGUN_2 = 46
MZ2_GUNNER_MACHINEGUN_3 = 47
MZ2_GUNNER_MACHINEGUN_4 = 48
MZ2_GUNNER_MACHINEGUN_5 = 49
MZ2_GUNNER_MACHINEGUN_6 = 50
MZ2_GUNNER_MACHINEGUN_7 = 51
MZ2_GUNNER_MACHINEGUN_8 = 52
MZ2_GUNNER_GRENADE_1 = 53
MZ2_GUNNER_GRENADE_2 = 54
MZ2_GUNNER_GRENADE_3 = 55
MZ2_GUNNER_GRENADE_4 = 56
MZ2_CHICK_ROCKET_1 = 57
MZ2_FLYER_BLASTER_1 = 58
MZ2_FLYER_BLASTER_2 = 59
MZ2_MEDIC_BLASTER_1 = 60
MZ2_GLADIATOR_RAILGUN_1 = 61
MZ2_HOVER_BLASTER_1 = 62
MZ2_ACTOR_MACHINEGUN_1 = 63
MZ2_SUPERTANK_MACHINEGUN_1 = 64
MZ2_SUPERTANK_MACHINEGUN_2 = 65
MZ2_SUPERTANK_MACHINEGUN_3 = 66
MZ2_SUPERTANK_MACHINEGUN_4 = 67
MZ2_SUPERTANK_MACHINEGUN_5 = 68
MZ2_SUPERTANK_MACHINEGUN_6 = 69
MZ2_SUPERTANK_ROCKET_1 = 70
MZ2_SUPERTANK_ROCKET_2 = 71
MZ2_SUPERTANK_ROCKET_3 = 72
MZ2_BOSS2_MACHINEGUN_L1 = 73
MZ2_BOSS2_MACHINEGUN_L2 = 74
MZ2_BOSS2_MACHINEGUN_L3 = 75
MZ2_BOSS2_MACHINEGUN_L4 = 76
MZ2_BOSS2_MACHINEGUN_L5 = 77
MZ2_BOSS2_ROCKET_1 = 78
MZ2_BOSS2_ROCKET_2 = 79
MZ2_BOSS2_ROCKET_3 = 80
MZ2_BOSS2_ROCKET_4 = 81
MZ2_FLOAT_BLASTER_1 = 82
MZ2_SOLDIER_BLASTER_3 = 83
MZ2_SOLDIER_SHOTGUN_3 = 84
MZ2_SOLDIER_MACHINEGUN_3 = 85
MZ2_SOLDIER_BLASTER_4 = 86
MZ2_SOLDIER_SHOTGUN_4 = 87
MZ2_SOLDIER_MACHINEGUN_4 = 88
MZ2_SOLDIER_BLASTER_5 = 89
MZ2_SOLDIER_SHOTGUN_5 = 90
MZ2_SOLDIER_MACHINEGUN_5 = 91
MZ2_SOLDIER_BLASTER_6 = 92
MZ2_SOLDIER_SHOTGUN_6 = 93
MZ2_SOLDIER_MACHINEGUN_6 = 94
MZ2_SOLDIER_BLASTER_7 = 95
MZ2_SOLDIER_SHOTGUN_7 = 96
MZ2_SOLDIER_MACHINEGUN_7 = 97
MZ2_SOLDIER_BLASTER_8 = 98
MZ2_SOLDIER_SHOTGUN_8 = 99
MZ2_SOLDIER_MACHINEGUN_8 = 100
MZ2_MAKRON_BFG = 101
MZ2_MAKRON_BLASTER_1 = 102
MZ2_MAKRON_BLASTER_2 = 103
MZ2_MAKRON_BLASTER_3 = 104
MZ2_MAKRON_BLASTER_4 = 105
MZ2_MAKRON_BLASTER_5 = 106
MZ2_MAKRON_BLASTER_6 = 107
MZ2_MAKRON_BLASTER_7 = 108
MZ2_MAKRON_BLASTER_8 = 109
MZ2_MAKRON_BLASTER_9 = 110
MZ2_MAKRON_BLASTER_10 = 111
MZ2_MAKRON_BLASTER_11 = 112
MZ2_MAKRON_BLASTER_12 = 113
MZ2_MAKRON_BLASTER_13 = 114
MZ2_MAKRON_BLASTER_14 = 115
MZ2_MAKRON_BLASTER_15 = 116
MZ2_MAKRON_BLASTER_16 = 117
MZ2_MAKRON_BLASTER_17 = 118
MZ2_MAKRON_RAILGUN_1 = 119
MZ2_JORG_MACHINEGUN_L1 = 120
MZ2_JORG_MACHINEGUN_L2 = 121
MZ2_JORG_MACHINEGUN_L3 = 122
MZ2_JORG_MACHINEGUN_L4 = 123
MZ2_JORG_MACHINEGUN_L5 = 124
MZ2_JORG_MACHINEGUN_L6 = 125
MZ2_JORG_MACHINEGUN_R1 = 126
MZ2_JORG_MACHINEGUN_R2 = 127
MZ2_JORG_MACHINEGUN_R3 = 128
MZ2_JORG_MACHINEGUN_R4 = 129
MZ2_JORG_MACHINEGUN_R5 = 130
MZ2_JORG_MACHINEGUN_R6 = 131
MZ2_JORG_BFG_1 = 132
MZ2_BOSS2_MACHINEGUN_R1 = 133
MZ2_BOSS2_MACHINEGUN_R2 = 134
MZ2_BOSS2_MACHINEGUN_R3 = 135
MZ2_BOSS2_MACHINEGUN_R4 = 136
MZ2_BOSS2_MACHINEGUN_R5 = 137
MZ2_CARRIER_MACHINEGUN_L1 = 138
MZ2_CARRIER_MACHINEGUN_R1 = 139
MZ2_CARRIER_GRENADE = 140
MZ2_TURRET_MACHINEGUN = 141
MZ2_TURRET_ROCKET = 142
MZ2_TURRET_BLASTER = 143
MZ2_STALKER_BLASTER = 144
MZ2_DAEDALUS_BLASTER = 145
MZ2_MEDIC_BLASTER_2 = 146
MZ2_CARRIER_RAILGUN = 147
MZ2_WIDOW_DISRUPTOR = 148
MZ2_WIDOW_BLASTER = 149
MZ2_WIDOW_RAIL = 150
MZ2_WIDOW_PLASMABEAM = 151
MZ2_CARRIER_MACHINEGUN_L2 = 152
MZ2_CARRIER_MACHINEGUN_R2 = 153
MZ2_WIDOW_RAIL_LEFT = 154
MZ2_WIDOW_RAIL_RIGHT = 155
MZ2_WIDOW_BLASTER_SWEEP1 = 156
MZ2_WIDOW_BLASTER_SWEEP2 = 157
MZ2_WIDOW_BLASTER_SWEEP3 = 158
MZ2_WIDOW_BLASTER_SWEEP4 = 159
MZ2_WIDOW_BLASTER_SWEEP5 = 160
MZ2_WIDOW_BLASTER_SWEEP6 = 161
MZ2_WIDOW_BLASTER_SWEEP7 = 162
MZ2_WIDOW_BLASTER_SWEEP8 = 163
MZ2_WIDOW_BLASTER_SWEEP9 = 164
MZ2_WIDOW_BLASTER_100 = 165
MZ2_WIDOW_BLASTER_90 = 166
MZ2_WIDOW_BLASTER_80 = 167
MZ2_WIDOW_BLASTER_70 = 168
MZ2_WIDOW_BLASTER_60 = 169
MZ2_WIDOW_BLASTER_50 = 170
MZ2_WIDOW_BLASTER_40 = 171
MZ2_WIDOW_BLASTER_30 = 172
MZ2_WIDOW_BLASTER_20 = 173
MZ2_WIDOW_BLASTER_10 = 174
MZ2_WIDOW_BLASTER_0 = 175
MZ2_WIDOW_BLASTER_10L = 176
MZ2_WIDOW_BLASTER_20L = 177
MZ2_WIDOW_BLASTER_30L = 178
MZ2_WIDOW_BLASTER_40L = 179
MZ2_WIDOW_BLASTER_50L = 180
MZ2_WIDOW_BLASTER_60L = 181
MZ2_WIDOW_BLASTER_70L = 182
MZ2_WIDOW_RUN_1 = 183
MZ2_WIDOW_RUN_2 = 184
MZ2_WIDOW_RUN_3 = 185
MZ2_WIDOW_RUN_4 = 186
MZ2_WIDOW_RUN_5 = 187
MZ2_WIDOW_RUN_6 = 188
MZ2_WIDOW_RUN_7 = 189
MZ2_WIDOW_RUN_8 = 190
MZ2_CARRIER_ROCKET_1 = 191
MZ2_CARRIER_ROCKET_2 = 192
MZ2_CARRIER_ROCKET_3 = 193
MZ2_CARRIER_ROCKET_4 = 194
MZ2_WIDOW2_BEAMER_1 = 195
MZ2_WIDOW2_BEAMER_2 = 196
MZ2_WIDOW2_BEAMER_3 = 197
MZ2_WIDOW2_BEAMER_4 = 198
MZ2_WIDOW2_BEAMER_5 = 199
MZ2_WIDOW2_BEAM_SWEEP_1 = 200
MZ2_WIDOW2_BEAM_SWEEP_2 = 201
MZ2_WIDOW2_BEAM_SWEEP_3 = 202
MZ2_WIDOW2_BEAM_SWEEP_4 = 203
MZ2_WIDOW2_BEAM_SWEEP_5 = 204
MZ2_WIDOW2_BEAM_SWEEP_6 = 205
MZ2_WIDOW2_BEAM_SWEEP_7 = 206
MZ2_WIDOW2_BEAM_SWEEP_8 = 207
MZ2_WIDOW2_BEAM_SWEEP_9 = 208
MZ2_WIDOW2_BEAM_SWEEP_10 = 209
MZ2_WIDOW2_BEAM_SWEEP_11 = 210

# temp entity events
#
# Temp entity events are for things that happen
# at a location seperate from any existing entity.
# Temporary entity messages are explicitly constructed
# and broadcast.
class temp_event_t(Enum):

	TE_GUNSHOT=0
	TE_BLOOD=1
	TE_BLASTER=2
	TE_RAILTRAIL=3
	TE_SHOTGUN=4
	TE_EXPLOSION1=5
	TE_EXPLOSION2=6
	TE_ROCKET_EXPLOSION=7
	TE_GRENADE_EXPLOSION=8
	TE_SPARKS=9
	TE_SPLASH=10
	TE_BUBBLETRAIL=11
	TE_SCREEN_SPARKS=12
	TE_SHIELD_SPARKS=13
	TE_BULLET_SPARKS=14
	TE_LASER_SPARKS=15
	TE_PARASITE_ATTACK=16
	TE_ROCKET_EXPLOSION_WATER=17
	TE_GRENADE_EXPLOSION_WATER=18
	TE_MEDIC_CABLE_ATTACK=19
	TE_BFG_EXPLOSION=20
	TE_BFG_BIGEXPLOSION=21
	TE_BOSSTPORT=22			# used as '22' in a map, so DON'T RENUMBER!!!
	TE_BFG_LASER=23
	TE_GRAPPLE_CABLE=24
	TE_WELDING_SPARKS=25
	TE_GREENBLOOD=26
	TE_BLUEHYPERBLASTER=27
	TE_PLASMA_EXPLOSION=28
	TE_TUNNEL_SPARKS=29
#ROGUE
	TE_BLASTER2=30
	TE_RAILTRAIL2=31
	TE_FLAME=32
	TE_LIGHTNING=33
	TE_DEBUGTRAIL=34
	TE_PLAIN_EXPLOSION=35
	TE_FLASHLIGHT=36
	TE_FORCEWALL=37
	TE_HEATBEAM=38
	TE_MONSTER_HEATBEAM=39
	TE_STEAM=40
	TE_BUBBLETRAIL2=41
	TE_MOREBLOOD=42
	TE_HEATBEAM_SPARKS=43
	TE_HEATBEAM_STEAM=44
	TE_CHAINFIST_SMOKE=45
	TE_ELECTRIC_SPARKS=46
	TE_TRACKER_EXPLOSION=47
	TE_TELEPORT_EFFECT=48
	TE_DBALL_GOAL=49
	TE_WIDOWBEAMOUT=50
	TE_NUKEBLAST=51
	TE_WIDOWSPLASH=52
	TE_EXPLOSION1_BIG=53
	TE_EXPLOSION1_NP=54
	TE_FLECHETTE=55
#ROGUE


SPLASH_UNKNOWN		= 0
SPLASH_SPARKS		= 1
SPLASH_BLUE_WATER	= 2
SPLASH_BROWN_WATER	= 3
SPLASH_SLIME		= 4
SPLASH_LAVA			= 5
SPLASH_BLOOD		= 6


# sound channels
# channel 0 never willingly overrides
# other channels (1-7) allways override a playing sound on that channel

CHAN_AUTO = 0
CHAN_WEAPON = 1
CHAN_VOICE = 2
CHAN_ITEM = 3
CHAN_BODY = 4
# modifier flags
CHAN_NO_PHS_ADD = 8	# send to all clients, not just ones in PHS (ATTN 0 will also do this)
CHAN_RELIABLE = 16	# send by reliable message, not datagram


# sound attenuation values
ATTN_NONE =               0	# full volume the entire level
ATTN_NORM =               1
ATTN_IDLE =               2
ATTN_STATIC =             3	# diminish very rapidly with distance


# player_state->stats[] indexes
STAT_HEALTH_ICON		= 0
STAT_HEALTH				= 1
STAT_AMMO_ICON			= 2
STAT_AMMO				= 3
STAT_ARMOR_ICON			= 4
STAT_ARMOR				= 5
STAT_SELECTED_ICON		= 6
STAT_PICKUP_ICON		= 7
STAT_PICKUP_STRING		= 8
STAT_TIMER_ICON			= 9
STAT_TIMER				= 10
STAT_HELPICON			= 11
STAT_SELECTED_ITEM		= 12
STAT_LAYOUTS			= 13
STAT_FRAGS				= 14
STAT_FLASHES			= 15		# cleared each frame, 1 = health, 2 = armor
STAT_CHASE				= 16
STAT_SPECTATOR			= 17

MAX_STATS =	32


# dmflags->value flags
DF_NO_HEALTH		= 0x00000001	# 1
DF_NO_ITEMS			= 0x00000002	# 2
DF_WEAPONS_STAY		= 0x00000004	# 4
DF_NO_FALLING		= 0x00000008	# 8
DF_INSTANT_ITEMS	= 0x00000010	# 16
DF_SAME_LEVEL		= 0x00000020	# 32
DF_SKINTEAMS		= 0x00000040	# 64
DF_MODELTEAMS		= 0x00000080	# 128
DF_NO_FRIENDLY_FIRE	= 0x00000100	# 256
DF_SPAWN_FARTHEST	= 0x00000200	# 512
DF_FORCE_RESPAWN	= 0x00000400	# 1024
DF_NO_ARMOR			= 0x00000800	# 2048
DF_ALLOW_EXIT		= 0x00001000	# 4096
DF_INFINITE_AMMO	= 0x00002000	# 8192
DF_QUAD_DROP		= 0x00004000	# 16384
DF_FIXED_FOV		= 0x00008000	# 32768

# RAFAEL
DF_QUADFIRE_DROP	= 0x00010000	# 65536

#ROGUE
DF_NO_MINES			= 0x00020000
DF_NO_STACK_DOUBLE	= 0x00040000
DF_NO_NUKES			= 0x00080000
DF_NO_SPHERES		= 0x00100000
#ROGUE
"""
/*
ROGUE - VERSIONS
1234	08/13/1998		Activision
1235	08/14/1998		Id Software
1236	08/15/1998		Steve Tietze
1237	08/15/1998		Phil Dobranski
1238	08/15/1998		John Sheley
1239	08/17/1998		Barrett Alexander
1230	08/17/1998		Brandon Fish
1245	08/17/1998		Don MacAskill
1246	08/17/1998		David "Zoid" Kirsch
1247	08/17/1998		Manu Smith
1248	08/17/1998		Geoff Scully
1249	08/17/1998		Andy Van Fossen
1240	08/20/1998		Activision Build 2
1256	08/20/1998		Ranger Clan
1257	08/20/1998		Ensemble Studios
1258	08/21/1998		Robert Duffy
1259	08/21/1998		Stephen Seachord
1250	08/21/1998		Stephen Heaslip
1267	08/21/1998		Samir Sandesara
1268	08/21/1998		Oliver Wyman
1269	08/21/1998		Steven Marchegiano
1260	08/21/1998		Build #2 for Nihilistic
1278	08/21/1998		Build #2 for Ensemble

9999	08/20/1998		Internal Use
*/
#define ROGUE_VERSION_ID		1278

#define ROGUE_VERSION_STRING	"08/21/1998 Beta 2 for Ensemble"

// ROGUE
/*
==========================================================

  ELEMENTS COMMUNICATED ACROSS THE NET

==========================================================
*/
"""
def	ANGLE2SHORT(x):	return ((int)((x)*65536/360) & 65535)
# Q2PORT: C truncation of an int to a short, as when storing ANGLE2SHORT into a short field
def	TO_SHORT(x):	return ((int(x) + 32768) & 65535) - 32768
def	SHORT2ANGLE(x):	return ((x)*(360.0/65536))


#
# config strings are a general means of communication from
# the server to all connected clients.
# Each config string can be at most MAX_QPATH characters.
#
CS_NAME				= 0
CS_CDTRACK			= 1
CS_SKY				= 2
CS_SKYAXIS			= 3		# %f %f %f format
CS_SKYROTATE		= 4
CS_STATUSBAR		= 5		# display program string

CS_AIRACCEL			= 29		# air acceleration control
CS_MAXCLIENTS		= 30
CS_MAPCHECKSUM		= 31		# for catching cheater maps

CS_MODELS			= 32
CS_SOUNDS			= (CS_MODELS+MAX_MODELS)
CS_IMAGES			= (CS_SOUNDS+MAX_SOUNDS)
CS_LIGHTS			= (CS_IMAGES+MAX_IMAGES)
CS_ITEMS			= (CS_LIGHTS+MAX_LIGHTSTYLES)
CS_PLAYERSKINS		= (CS_ITEMS+MAX_ITEMS)
CS_GENERAL			= (CS_PLAYERSKINS+MAX_CLIENTS)
MAX_CONFIGSTRINGS	= (CS_GENERAL+MAX_GENERAL)
"""

//==============================================


// entity_state_t->event values
// ertity events are for effects that take place reletive
// to an existing entities origin.  Very network efficient.
// All muzzle flashes really should be converted to events...
"""
class entity_event_t(Enum):

	EV_NONE = 0
	EV_ITEM_RESPAWN = 1
	EV_FOOTSTEP = 2
	EV_FALLSHORT = 3
	EV_FALL = 4
	EV_FALLFAR = 5
	EV_PLAYER_TELEPORT = 6
	EV_OTHER_TELEPORT = 7

EV_NONE = entity_event_t.EV_NONE.value
EV_ITEM_RESPAWN = entity_event_t.EV_ITEM_RESPAWN.value
EV_FOOTSTEP = entity_event_t.EV_FOOTSTEP.value
EV_FALLSHORT = entity_event_t.EV_FALLSHORT.value
EV_FALL = entity_event_t.EV_FALL.value
EV_FALLFAR = entity_event_t.EV_FALLFAR.value
EV_PLAYER_TELEPORT = entity_event_t.EV_PLAYER_TELEPORT.value
EV_OTHER_TELEPORT = entity_event_t.EV_OTHER_TELEPORT.value


# entity_state_t is the information conveyed from the server
# in an update message about entities that the client will
# need to render in some way
class entity_state_t(object):

	def __init__(self): 

		self.number = 0 #int, edict index

		self.origin: vec3_t = np.zeros((3,), dtype=np.float32)
		self.angles: vec3_t = np.zeros((3,), dtype=np.float32)
		self.old_origin: vec3_t = np.zeros((3,), dtype=np.float32) # for lerping
		self.modelindex: int = 0
		self.modelindex2, self.modelindex3, self.modelindex4 = 0, 0, 0 # weapons, CTF flags, etc, int
		self.frame: int = 0
		self.skinnum: int = 0
		self.effects: int = 0	# PGM - we're filling it, so it needs to be unsigned, unsigned int
		self.renderfx: int = 0
		self.solid: int = 0  # for client side prediction, 8*(bits 0-4) is x/y radius
								# 8*(bits 5-9) is z down distance, 8(bits10-15) is z up
								# gi.linkentity sets this properly
		self.sound: int	= 0	# for looping sounds, to guarantee shutoff
		self.event: int	= 0	# impulse events -- muzzle flashes, footsteps, etc
								# events only go out for a single frame, they
								# are automatically cleared each frame

	def copy(self, obj):

		# struct assignment, so the vectors are copied by value
		self.number = obj.number
		self.origin: vec3_t = np.array(obj.origin, dtype=np.float32)
		self.angles: vec3_t = np.array(obj.angles, dtype=np.float32)
		self.old_origin: vec3_t = np.array(obj.old_origin, dtype=np.float32)
		self.modelindex: int = obj.modelindex
		self.modelindex2, self.modelindex3, self.modelindex4 = obj.modelindex2, obj.modelindex3, obj.modelindex4
		self.frame: int = obj.frame
		self.skinnum: int = obj.skinnum
		self.effects: int = obj.effects
		self.renderfx: int = obj.renderfx
		self.solid: int = obj.solid					
		self.sound: int	= obj.sound
		self.event: int	= obj.event


"""
//==============================================


// player_state_t is the information needed in addition to pmove_state_t
// to rendered a view.  There will only be 10 player_state_t sent each second,
// but the number of pmove_state_t changes will be reletive to client
// frame rates
"""
class player_state_t(object):

	def __init__(self):
		self.clear()

	def clear(self):

		self.pmove = pmove_state_t() # pmove_state_t, for prediction

		# these fields do not need to be communicated bit-precise

		self.viewangles = np.zeros((3,), dtype=np.float32)		# vec3_t, for fixed views
		self.viewoffset = np.zeros((3,), dtype=np.float32)		# vec3_t, add to pmovestate->origin
		self.kick_angles = np.zeros((3,), dtype=np.float32)		# vec3_t, add to view direction to get render angles
									# set by weapon kicks, pain effects, etc

		self.gunangles = np.zeros((3,), dtype=np.float32) # vec3_t
		self.gunoffset = np.zeros((3,), dtype=np.float32) # vec3_t
		self.gunindex = None # int
		self.gunframe = None # int

		self.blend = np.zeros((4,), dtype=np.float32) # float[4], rgba full screen effect
		
		self.fov = 90.0 #float, horizontal field of view # DEBUG set to 90

		self.rdflags = 0 # int, refdef flags

		self.stats = [] # short[MAX_STATS], fast status bar updates
		for i in range(MAX_STATS):
			self.stats.append(0)

"""
// ==================
// PGM 
#define VIDREF_GL		1
#define VIDREF_SOFT		2
#define VIDREF_OTHER	3

extern int vidref_val;
// PGM
// ==================
"""
VIDREF_GL = 1
VIDREF_SOFT = 2
VIDREF_OTHER = 3
"""

#define DEG2RAD( a ) ( a * M_PI ) / 180.0F

vec3_t vec3_origin = {0,0,0};

//============================================================================

#ifdef _WIN32
#pragma optimize( "", off )
#endif

void RotatePointAroundVector( vec3_t dst, const vec3_t dir, const vec3_t point, float degrees )
{
	float	m[3][3];
	float	im[3][3];
	float	zrot[3][3];
	float	tmpmat[3][3];
	float	rot[3][3];
	int	i;
	vec3_t vr, vup, vf;

	vf[0] = dir[0];
	vf[1] = dir[1];
	vf[2] = dir[2];

	PerpendicularVector( vr, dir );
	CrossProduct( vr, vf, vup );

	m[0][0] = vr[0];
	m[1][0] = vr[1];
	m[2][0] = vr[2];

	m[0][1] = vup[0];
	m[1][1] = vup[1];
	m[2][1] = vup[2];

	m[0][2] = vf[0];
	m[1][2] = vf[1];
	m[2][2] = vf[2];

	memcpy( im, m, sizeof( im ) );

	im[0][1] = m[1][0];
	im[0][2] = m[2][0];
	im[1][0] = m[0][1];
	im[1][2] = m[2][1];
	im[2][0] = m[0][2];
	im[2][1] = m[1][2];

	memset( zrot, 0, sizeof( zrot ) );
	zrot[0][0] = zrot[1][1] = zrot[2][2] = 1.0F;

	zrot[0][0] = cos( DEG2RAD( degrees ) );
	zrot[0][1] = sin( DEG2RAD( degrees ) );
	zrot[1][0] = -sin( DEG2RAD( degrees ) );
	zrot[1][1] = cos( DEG2RAD( degrees ) );

	R_ConcatRotations( m, zrot, tmpmat );
	R_ConcatRotations( tmpmat, im, rot );

	for ( i = 0; i < 3; i++ )
	{
		dst[i] = rot[i][0] * point[0] + rot[i][1] * point[1] + rot[i][2] * point[2];
	}
}

#ifdef _WIN32
#pragma optimize( "", on )
#endif



void AngleVectors (vec3_t angles, vec3_t forward, vec3_t right, vec3_t up)
{
	float		angle;
	static float		sr, sp, sy, cr, cp, cy;
	// static to help MS compiler fp bugs

	angle = angles[YAW] * (M_PI*2 / 360);
	sy = sin(angle);
	cy = cos(angle);
	angle = angles[PITCH] * (M_PI*2 / 360);
	sp = sin(angle);
	cp = cos(angle);
	angle = angles[ROLL] * (M_PI*2 / 360);
	sr = sin(angle);
	cr = cos(angle);

	if (forward)
	{
		forward[0] = cp*cy;
		forward[1] = cp*sy;
		forward[2] = -sp;
	}
	if (right)
	{
		right[0] = (-1*sr*sp*cy+-1*cr*-sy);
		right[1] = (-1*sr*sp*sy+-1*cr*cy);
		right[2] = -1*sr*cp;
	}
	if (up)
	{
		up[0] = (cr*sp*cy+-sr*-sy);
		up[1] = (cr*sp*sy+-sr*cy);
		up[2] = cr*cp;
	}
}


void ProjectPointOnPlane( vec3_t dst, const vec3_t p, const vec3_t normal )
{
	float d;
	vec3_t n;
	float inv_denom;

	inv_denom = 1.0F / DotProduct( normal, normal );

	d = DotProduct( normal, p ) * inv_denom;

	n[0] = normal[0] * inv_denom;
	n[1] = normal[1] * inv_denom;
	n[2] = normal[2] * inv_denom;

	dst[0] = p[0] - d * n[0];
	dst[1] = p[1] - d * n[1];
	dst[2] = p[2] - d * n[2];
}

/*
** assumes "src" is normalized
*/
void PerpendicularVector( vec3_t dst, const vec3_t src )
{
	int	pos;
	int i;
	float minelem = 1.0F;
	vec3_t tempvec;

	/*
	** find the smallest magnitude axially aligned vector
	*/
	for ( pos = 0, i = 0; i < 3; i++ )
	{
		if ( fabs( src[i] ) < minelem )
		{
			pos = i;
			minelem = fabs( src[i] );
		}
	}
	tempvec[0] = tempvec[1] = tempvec[2] = 0.0F;
	tempvec[pos] = 1.0F;

	/*
	** project the point onto the plane defined by src
	*/
	ProjectPointOnPlane( dst, tempvec, src );

	/*
	** normalize the result
	*/
	VectorNormalize( dst );
}
"""
"""
/*
================
R_ConcatRotations
================
*/
void R_ConcatRotations (float in1[3][3], float in2[3][3], float out[3][3])
{
	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] +
				in1[0][2] * in2[2][0];
	out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] +
				in1[0][2] * in2[2][1];
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] +
				in1[0][2] * in2[2][2];
	out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] +
				in1[1][2] * in2[2][0];
	out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] +
				in1[1][2] * in2[2][1];
	out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] +
				in1[1][2] * in2[2][2];
	out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] +
				in1[2][2] * in2[2][0];
	out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] +
				in1[2][2] * in2[2][1];
	out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] +
				in1[2][2] * in2[2][2];
}
"""
"""
/*
================
R_ConcatTransforms
================
*/
void R_ConcatTransforms (float in1[3][4], float in2[3][4], float out[3][4])
{
	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] +
				in1[0][2] * in2[2][0];
	out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] +
				in1[0][2] * in2[2][1];
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] +
				in1[0][2] * in2[2][2];
	out[0][3] = in1[0][0] * in2[0][3] + in1[0][1] * in2[1][3] +
				in1[0][2] * in2[2][3] + in1[0][3];
	out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] +
				in1[1][2] * in2[2][0];
	out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] +
				in1[1][2] * in2[2][1];
	out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] +
				in1[1][2] * in2[2][2];
	out[1][3] = in1[1][0] * in2[0][3] + in1[1][1] * in2[1][3] +
				in1[1][2] * in2[2][3] + in1[1][3];
	out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] +
				in1[2][2] * in2[2][0];
	out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] +
				in1[2][2] * in2[2][1];
	out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] +
				in1[2][2] * in2[2][2];
	out[2][3] = in1[2][0] * in2[0][3] + in1[2][1] * in2[1][3] +
				in1[2][2] * in2[2][3] + in1[2][3];
}


//============================================================================


float Q_fabs (float f)
{
#if 0
	if (f >= 0)
		return f;
	return -f;
#else
	int tmp = * ( int * ) &f;
	tmp &= 0x7FFFFFFF;
	return * ( float * ) &tmp;
#endif
}

#if defined _M_IX86 && !defined C_ONLY
#pragma warning (disable:4035)
__declspec( naked ) long Q_ftol( float f )
{
	static int tmp;
	__asm fld dword ptr [esp+4]
	__asm fistp tmp
	__asm mov eax, tmp
	__asm ret
}
#pragma warning (default:4035)
#endif
"""
"""
/*
===============
LerpAngle

===============
*/
float LerpAngle (float a2, float a1, float frac)
{
	if (a1 - a2 > 180)
		a1 -= 360;
	if (a1 - a2 < -180)
		a1 += 360;
	return a2 + frac * (a1 - a2);
}


float	anglemod(float a)
{
#if 0
	if (a >= 0)
		a -= 360*(int)(a/360);
	else
		a += 360*( 1 + (int)(-a/360) );
#endif
	a = (360.0/65536) * ((int)(a*(65536/360.0)) & 65535);
	return a;
}

	int		i;
	vec3_t	corners[2];


// this is the slow, general version
int BoxOnPlaneSide2 (vec3_t emins, vec3_t emaxs, struct cplane_s *p)
{
	int		i;
	float	dist1, dist2;
	int		sides;
	vec3_t	corners[2];

	for (i=0 ; i<3 ; i++)
	{
		if (p->normal[i] < 0)
		{
			corners[0][i] = emins[i];
			corners[1][i] = emaxs[i];
		}
		else
		{
			corners[1][i] = emins[i];
			corners[0][i] = emaxs[i];
		}
	}
	dist1 = DotProduct (p->normal, corners[0]) - p->dist;
	dist2 = DotProduct (p->normal, corners[1]) - p->dist;
	sides = 0;
	if (dist1 >= 0)
		sides = 1;
	if (dist2 < 0)
		sides |= 2;

	return sides;
}
"""
"""
/*
==================
BoxOnPlaneSide

Returns 1, 2, or 1 + 2
==================
*/
#if !id386 || defined __linux__ 
int BoxOnPlaneSide (vec3_t emins, vec3_t emaxs, struct cplane_s *p)
{
	float	dist1, dist2;
	int		sides;

// fast axial cases
	if (p->type < 3)
	{
		if (p->dist <= emins[p->type])
			return 1;
		if (p->dist >= emaxs[p->type])
			return 2;
		return 3;
	}
	
// general case
	switch (p->signbits)
	{
	case 0:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
		break;
	case 1:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
		break;
	case 2:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
		break;
	case 3:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
		break;
	case 4:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
		break;
	case 5:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
		break;
	case 6:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
		break;
	case 7:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
		break;
	default:
		dist1 = dist2 = 0;		// shut up compiler
		assert( 0 );
		break;
	}

	sides = 0;
	if (dist1 >= p->dist)
		sides = 1;
	if (dist2 < p->dist)
		sides |= 2;

	assert( sides != 0 );

	return sides;
}
#else
#pragma warning( disable: 4035 )

__declspec( naked ) int BoxOnPlaneSide (vec3_t emins, vec3_t emaxs, struct cplane_s *p)
{
	static int bops_initialized;
	static int Ljmptab[8];

	__asm {

		push ebx
			
		cmp bops_initialized, 1
		je  initialized
		mov bops_initialized, 1
		
		mov Ljmptab[0*4], offset Lcase0
		mov Ljmptab[1*4], offset Lcase1
		mov Ljmptab[2*4], offset Lcase2
		mov Ljmptab[3*4], offset Lcase3
		mov Ljmptab[4*4], offset Lcase4
		mov Ljmptab[5*4], offset Lcase5
		mov Ljmptab[6*4], offset Lcase6
		mov Ljmptab[7*4], offset Lcase7
			
initialized:

		mov edx,ds:dword ptr[4+12+esp]
		mov ecx,ds:dword ptr[4+4+esp]
		xor eax,eax
		mov ebx,ds:dword ptr[4+8+esp]
		mov al,ds:byte ptr[17+edx]
		cmp al,8
		jge Lerror
		fld ds:dword ptr[0+edx]
		fld st(0)
		jmp dword ptr[Ljmptab+eax*4]
Lcase0:
		fmul ds:dword ptr[ebx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ebx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase1:
		fmul ds:dword ptr[ecx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ebx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase2:
		fmul ds:dword ptr[ebx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ecx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase3:
		fmul ds:dword ptr[ecx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ecx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase4:
		fmul ds:dword ptr[ebx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ebx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase5:
		fmul ds:dword ptr[ecx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ebx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase6:
		fmul ds:dword ptr[ebx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ecx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ecx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
		jmp LSetSides
Lcase7:
		fmul ds:dword ptr[ecx]
		fld ds:dword ptr[0+4+edx]
		fxch st(2)
		fmul ds:dword ptr[ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[4+ecx]
		fld ds:dword ptr[0+8+edx]
		fxch st(2)
		fmul ds:dword ptr[4+ebx]
		fxch st(2)
		fld st(0)
		fmul ds:dword ptr[8+ecx]
		fxch st(5)
		faddp st(3),st(0)
		fmul ds:dword ptr[8+ebx]
		fxch st(1)
		faddp st(3),st(0)
		fxch st(3)
		faddp st(2),st(0)
LSetSides:
		faddp st(2),st(0)
		fcomp ds:dword ptr[12+edx]
		xor ecx,ecx
		fnstsw ax
		fcomp ds:dword ptr[12+edx]
		and ah,1
		xor ah,1
		add cl,ah
		fnstsw ax
		and ah,1
		add ah,ah
		add cl,ah
		pop ebx
		mov eax,ecx
		ret
Lerror:
		int 3
	}
}
#pragma warning( default: 4035 )
#endif

void ClearBounds (vec3_t mins, vec3_t maxs)
{
	mins[0] = mins[1] = mins[2] = 99999;
	maxs[0] = maxs[1] = maxs[2] = -99999;
}

void AddPointToBounds (vec3_t v, vec3_t mins, vec3_t maxs)
{
	int		i;
	vec_t	val;

	for (i=0 ; i<3 ; i++)
	{
		val = v[i];
		if (val < mins[i])
			mins[i] = val;
		if (val > maxs[i])
			maxs[i] = val;
	}
}


int VectorCompare (vec3_t v1, vec3_t v2)
{
	if (v1[0] != v2[0] || v1[1] != v2[1] || v1[2] != v2[2])
			return 0;
			
	return 1;
}


vec_t VectorNormalize (vec3_t v)
{
	float	length, ilength;

	length = v[0]*v[0] + v[1]*v[1] + v[2]*v[2];
	length = sqrt (length);		// FIXME

	if (length)
	{
		ilength = 1/length;
		v[0] *= ilength;
		v[1] *= ilength;
		v[2] *= ilength;
	}
		
	return length;

}

vec_t VectorNormalize2 (vec3_t v, vec3_t out)
{
	float	length, ilength;

	length = v[0]*v[0] + v[1]*v[1] + v[2]*v[2];
	length = sqrt (length);		// FIXME

	if (length)
	{
		ilength = 1/length;
		out[0] = v[0]*ilength;
		out[1] = v[1]*ilength;
		out[2] = v[2]*ilength;
	}
		
	return length;

}

void VectorMA (vec3_t veca, float scale, vec3_t vecb, vec3_t vecc)
{
	vecc[0] = veca[0] + scale*vecb[0];
	vecc[1] = veca[1] + scale*vecb[1];
	vecc[2] = veca[2] + scale*vecb[2];
}


vec_t _DotProduct (vec3_t v1, vec3_t v2)
{
	return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2];
}

void _VectorSubtract (vec3_t veca, vec3_t vecb, vec3_t out)
{
	out[0] = veca[0]-vecb[0];
	out[1] = veca[1]-vecb[1];
	out[2] = veca[2]-vecb[2];
}

void _VectorAdd (vec3_t veca, vec3_t vecb, vec3_t out)
{
	out[0] = veca[0]+vecb[0];
	out[1] = veca[1]+vecb[1];
	out[2] = veca[2]+vecb[2];
}

void _VectorCopy (vec3_t in, vec3_t out)
{
	out[0] = in[0];
	out[1] = in[1];
	out[2] = in[2];
}

void CrossProduct (vec3_t v1, vec3_t v2, vec3_t cross)
{
	cross[0] = v1[1]*v2[2] - v1[2]*v2[1];
	cross[1] = v1[2]*v2[0] - v1[0]*v2[2];
	cross[2] = v1[0]*v2[1] - v1[1]*v2[0];
}

double sqrt(double x);

vec_t VectorLength(vec3_t v)
{
	int		i;
	float	length;
	
	length = 0;
	for (i=0 ; i< 3 ; i++)
		length += v[i]*v[i];
	length = sqrt (length);		// FIXME

	return length;
}

void VectorInverse (vec3_t v)
{
	v[0] = -v[0];
	v[1] = -v[1];
	v[2] = -v[2];
}

void VectorScale (vec3_t in, vec_t scale, vec3_t out)
{
	out[0] = in[0]*scale;
	out[1] = in[1]*scale;
	out[2] = in[2]*scale;
}


int Q_log2(int val)
{
	int answer=0;
	while (val>>=1)
		answer++;
	return answer;
}



//====================================================================================
"""
"""
/*
============
COM_SkipPath
============
*/
char *COM_SkipPath (char *pathname)
{
	char	*last;
	
	last = pathname;
	while (*pathname)
	{
		if (*pathname=='/')
			last = pathname+1;
		pathname++;
	}
	return last;
}
"""
"""
============
COM_StripExtension
============
"""
def COM_StripExtension (in_str): #char * (returns char *out)

	i = 0
	while i < len(in_str) and in_str[i] != '.':
		i += 1
	out = in_str[:i]
	return out

"""
/*
============
COM_FileExtension
============
*/
char *COM_FileExtension (char *in)
{
	static char exten[8];
	int		i;

	while (*in && *in != '.')
		in++;
	if (!*in)
		return "";
	in++;
	for (i=0 ; i<7 && *in ; i++,in++)
		exten[i] = *in;
	exten[i] = 0;
	return exten;
}
"""
"""
/*
============
COM_FileBase
============
*/
void COM_FileBase (char *in, char *out)
{
	char *s, *s2;
	
	s = in + strlen(in) - 1;
	
	while (s != in && *s != '.')
		s--;
	
	for (s2 = s ; s2 != in && *s2 != '/' ; s2--)
	;
	
	if (s-s2 < 2)
		out[0] = 0;
	else
	{
		s--;
		strncpy (out,s2+1, s-s2);
		out[s-s2] = 0;
	}
}
"""
"""
/*
============
COM_FilePath

Returns the path up to, but not including the last /
============
*/
void COM_FilePath (char *in, char *out)
{
	char *s;
	
	s = in + strlen(in) - 1;
	
	while (s != in && *s != '/')
		s--;

	strncpy (out,in, s-in);
	out[s-in] = 0;
}
"""
"""
/*
==================
COM_DefaultExtension
==================
*/
void COM_DefaultExtension (char *path, char *extension)
{
	char    *src;
//
// if path doesn't have a .EXT, append extension
// (extension should include the .)
//
	src = path + strlen(path) - 1;

	while (*src != '/' && src != path)
	{
		if (*src == '.')
			return;                 // it has an extension
		src--;
	}

	strcat (path, extension);
}
"""
"""
/*
============================================================================

					BYTE ORDER FUNCTIONS

============================================================================
*/

qboolean	bigendien;

// can't just use function pointers, or dll linkage can
// mess up when qcommon is included in multiple places
short	(*_BigShort) (short l);
short	(*_LittleShort) (short l);
int		(*_BigLong) (int l);
int		(*_LittleLong) (int l);
float	(*_BigFloat) (float l);
float	(*_LittleFloat) (float l);
"""
def BigShort(l):
	return struct.unpack(">H", l)[0]
def LittleShort(l):
	return struct.unpack("<H", l)[0]

def BigSShort(l):
	return struct.unpack(">h", l)[0]
def LittleSShort(l):
	return struct.unpack("<h", l)[0]

def BigLong (l): #int, (returns int)
	return struct.unpack(">I", l)[0]
def LittleLong (l): #int, (returns int)
	return struct.unpack("<I", l)[0]

def BigSLong (l): #int, (returns int)
	return struct.unpack(">i", l)[0]
def LittleSLong (l): #int, (returns int)
	return struct.unpack("<i", l)[0]

def BigFloat (l) -> float:
	return struct.unpack(">f", l)[0]
def LittleFloat (l) -> float:
	return struct.unpack("<f", l)[0]

"""

short   ShortSwap (short l)
{
	byte    b1,b2;

	b1 = l&255;
	b2 = (l>>8)&255;

	return (b1<<8) + b2;
}

short	ShortNoSwap (short l)
{
	return l;
}

int    LongSwap (int l)
{
	byte    b1,b2,b3,b4;

	b1 = l&255;
	b2 = (l>>8)&255;
	b3 = (l>>16)&255;
	b4 = (l>>24)&255;

	return ((int)b1<<24) + ((int)b2<<16) + ((int)b3<<8) + b4;
}

int	LongNoSwap (int l)
{
	return l;
}

float FloatSwap (float f)
{
	union
	{
		float	f;
		byte	b[4];
	} dat1, dat2;
	
	
	dat1.f = f;
	dat2.b[0] = dat1.b[3];
	dat2.b[1] = dat1.b[2];
	dat2.b[2] = dat1.b[1];
	dat2.b[3] = dat1.b[0];
	return dat2.f;
}

float FloatNoSwap (float f)
{
	return f;
}

/*
================
Swap_Init
================
"""
def Swap_Init ():

	pass
	"""
	byte	swaptest[2] = {1,0};

// set the byte swapping variables in a portable manner	
	if ( *(short *)swaptest == 1)
	{
		bigendien = false;
		_BigShort = ShortSwap;
		_LittleShort = ShortNoSwap;
		_BigLong = LongSwap;
		_LittleLong = LongNoSwap;
		_BigFloat = FloatSwap;
		_LittleFloat = FloatNoSwap;
	}
	else
	{
		bigendien = true;
		_BigShort = ShortNoSwap;
		_LittleShort = ShortSwap;
		_BigLong = LongNoSwap;
		_LittleLong = LongSwap;
		_BigFloat = FloatNoSwap;
		_LittleFloat = FloatSwap;
	}

"""



"""
============
va

does a varargs printf into a temp buffer, so I don't need to have
varargs versions of all text functions.
FIXME: make this buffer size safe someday
============
*/
char	*va(char *format, ...)
{
	va_list		argptr;
	static char		string[1024];
	
	va_start (argptr, format);
	vsprintf (string, format,argptr);
	va_end (argptr);

	return string;	
}

==============
COM_Parse

Parse a token out of a string
==============
"""
def COM_Parse (data, cursor): #char ** (returns char *)

	length = 0;
	com_token = [] #char[MAX_TOKEN_CHARS]
	
	if data is None or cursor is None: # if (!data)
		return "", None # *data_p = NULL;
	
	# skip whitespace
	possInComment = True
	
	while possInComment:
		while cursor >= len(data) or data[cursor].strip() == '' or data[cursor] == '\0':
			if cursor >= len(data):
				return "", None # *data_p = NULL;
			
			cursor += 1

		# skip // comments
		if data[cursor]=='/' and cursor+1 < len(data) and data[cursor+1] == '/': # data[1] is the terminator at the end
		
			while cursor < len(data) and data[cursor] != '\n':
				cursor+=1
		else:
			possInComment = False

	# handle quoted strings specially
	if data[cursor] == '"':
	
		cursor+=1
		while 1:
		
			c = data[cursor]
			cursor += 1

			if c=='\"' or cursor >= len(data):
				return "".join(com_token), cursor
			
			if length < MAX_TOKEN_CHARS:

				com_token.append(c);
				length+=1
		
	# parse a regular word
	c = data[cursor]
	while c != None and c.strip() != "" and c != '\0' and cursor < len(data):
		
		if length < MAX_TOKEN_CHARS:
		
			com_token.append(c)
			length+=1
		
		cursor += 1
		if cursor < len(data):
			c = data[cursor]
		else:
			c = None
	 
	if length == MAX_TOKEN_CHARS:
	
		##Com_Printf ("Token exceeded %i chars, discarded.\n", MAX_TOKEN_CHARS);
		length = 0;
		com_token = []
	
	return "".join(com_token), cursor


	"""
===============
Com_PageInMemory

===============
*/
int	paged_total;

void Com_PageInMemory (byte *buffer, int size)
{
	int		i;

	for (i=size-1 ; i>0 ; i-=4096)
		paged_total += buffer[i];
}



/*
============================================================================

					LIBRARY REPLACEMENT FUNCTIONS

============================================================================
*/
"""
# FIXME: replace all Q_stricmp with Q_strcasecmp
def Q_stricmp (s1, s2): #char *, char* (return int)

	return Q_strcasecmp(s1, s2)


def atoi (s): #const char * (returns int), C library atoi: leading whitespace, optional sign, digits, else 0

	m = re.match(r"\s*([+-]?\d+)", s)
	if m is None:
		return 0
	return int(m.group(1))

def atof (s): #const char * (returns double), C library atof: leading whitespace, longest valid float prefix, else 0
	# Q2PORT: helper for the C library function

	m = re.match(r"\s*([+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)", s)
	if m is None:
		return 0.0
	return float(m.group(1))

"""

int Q_strncasecmp (char *s1, char *s2, int n)
{
	int		c1, c2;
	
	do
	{
		c1 = *s1++;
		c2 = *s2++;

		if (!n--)
			return 0;		// strings are equal until end point
		
		if (c1 != c2)
		{
			if (c1 >= 'a' && c1 <= 'z')
				c1 -= ('a' - 'A');
			if (c2 >= 'a' && c2 <= 'z')
				c2 -= ('a' - 'A');
			if (c1 != c2)
				return -1;		// strings not equal
		}
	} while (c1);
	
	return 0;		// strings are equal
}
"""
def Q_strcasecmp (s1, s2): #char *, char *

	if s1 is None or s2 is None:
		return -1
	if s1.lower() == s2.lower():
		return 0
	return -1
	##return Q_strncasecmp (s1, s2, 99999);

"""
void Com_sprintf (char *dest, int size, char *fmt, ...)
{
	int		len;
	va_list		argptr;
	char	bigbuffer[0x10000];

	va_start (argptr,fmt);
	len = vsprintf (bigbuffer,fmt,argptr);
	va_end (argptr);
	if (len >= size)
		Com_Printf ("Com_sprintf: overflow of %i in %i\n", len, size);
	strncpy (dest, bigbuffer, size-1);
}
"""
"""
/*
=====================================================================

  INFO STRINGS

=====================================================================
*/
"""
"""
/*
===============
Info_ValueForKey

Searches the string for the given
key and returns the associated value, or an empty string.
===============
"""
def Info_ValueForKey (s, key): #char *, char * (returns char *)

	ssplit = (s.split("\\"))
	data = dict(zip(ssplit[1::2], ssplit[2::2]))
	if key in data:
		return data[key]

	return ""
	"""
	char	pkey[512];
	static	char value[2][512];	// use two buffers so compares
								// work without stomping on each other
	static	int	valueindex;
	char	*o;
	
	valueindex ^= 1;
	if (*s == '\\')
		s++;
	while (1)
	{
		o = pkey;
		while (*s != '\\')
		{
			if (!*s)
				return "";
			*o++ = *s++;
		}
		*o = 0;
		s++;

		o = value[valueindex];

		while (*s != '\\' && *s)
		{
			if (!*s)
				return "";
			*o++ = *s++;
		}
		*o = 0;

		if (!strcmp (key, pkey) )
			return value[valueindex];

		if (!*s)
			return "";
		s++;
	}
}
"""
def Info_RemoveKey (s, key): #char *, char *

	ssplit = (s.split("\\"))
	data = dict(zip(ssplit[1::2], ssplit[2::2]))
	if key not in data:
		return s

	del data[key]

	out = []
	for k, v in data.items():
		out.append("\\{}\\{}".format(k, v))
	return "".join(out)

	"""
	char	*start;
	char	pkey[512];
	char	value[512];
	char	*o;

	if (strstr (key, "\\"))
	{
//		Com_Printf ("Can't use a key with a \\\n");
		return;
	}

	while (1)
	{
		start = s;
		if (*s == '\\')
			s++;
		o = pkey;
		while (*s != '\\')
		{
			if (!*s)
				return;
			*o++ = *s++;
		}
		*o = 0;
		s++;

		o = value;
		while (*s != '\\' && *s)
		{
			if (!*s)
				return;
			*o++ = *s++;
		}
		*o = 0;

		if (!strcmp (key, pkey) )
		{
			strcpy (start, s);	// remove this part
			return;
		}

		if (!*s)
			return;
	}

}


/*
==================
Info_Validate

Some characters are illegal in info strings because they
can mess up the server's parsing
==================
*/
qboolean Info_Validate (char *s)
{
	if (strstr (s, "\""))
		return false;
	if (strstr (s, ";"))
		return false;
	return true;
}
"""
def Info_SetValueForKey (key, value): #char*, char*

	#char	newi[MAX_INFO_STRING], *v;
	#int		c;
	#int		maxsize = MAX_INFO_STRING;

	if key.find("\\") != -1 or value.find("\\") != -1 :
	
		common.Com_Printf ("Can't use keys or values with a \\\n")
		return ""
	
	if key.find(";") != -1:
	
		common.Com_Printf ("Can't use keys or values with a semicolon\n")
		return ""
	 
	if key.find("\"") != -1 or value.find("\"") != -1:
	
		common.Com_Printf ("Can't use keys or values with a \"\n")
		return ""
	
	if len(key) > MAX_INFO_KEY-1 or len(value) > MAX_INFO_KEY-1:
	
		common.Com_Printf ("Keys and values must be < 64 characters.\n")
		return ""
	
	#Info_RemoveKey (s, key)
	if value is None or len(value)==0:
		return ""

	newi = "\\{}\\{}".format(key, value)

	#if len(newi) + len(s) > maxsize:
	#
	#	common.Com_Printf ("Info string length exceeded\n")
	#	return
	
	# only copy ascii values
	#s += strlen(s);
	out = []
	for v in newi:
	
		v = ord(v)
		v &= 127		# strip high bits
		if v >= 32 and v < 127:
			out.append(chr(v))
	
	return "".join(out)

"""
//====================================================================



"""

