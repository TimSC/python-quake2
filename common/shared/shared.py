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

Support functions, linked into client, server, renderer and game.

=======================================================================
"""
from __future__ import annotations

import struct
import math
import re
from enum import Enum
import numpy as np
from common.header import shared

"""
#include <ctype.h>
#ifndef _MSC_VER
#include <strings.h>
#endif
#include "../header/shared.h"
"""

def DEG2RAD(a): return (a * math.pi) / 180.0 #define DEG2RAD(a) (a * M_PI) / 180.0F

vec3_origin = np.zeros((3,), dtype=np.float32) #vec3_t, {0, 0, 0}

"""
/* ============================================================================ */
"""

def RotatePointAroundVector(dst, dir, point, degrees): #vec3_t, const vec3_t, const vec3_t, float

	"""
	float m[3][3];
	float im[3][3];
	float zrot[3][3];
	float tmpmat[3][3];
	float rot[3][3];
	int i;
	vec3_t vr, vup, vf;
	"""
	m = np.zeros((3, 3), dtype=np.float32)
	zrot = np.zeros((3, 3), dtype=np.float32)
	tmpmat = np.zeros((3, 3), dtype=np.float32)
	rot = np.zeros((3, 3), dtype=np.float32)
	vr = np.zeros((3,), dtype=np.float32)
	vup = np.zeros((3,), dtype=np.float32)
	vf = np.zeros((3,), dtype=np.float32)

	vf[0] = dir[0]
	vf[1] = dir[1]
	vf[2] = dir[2]

	PerpendicularVector(vr, dir)
	CrossProduct(vr, vf, vup)

	m[0][0] = vr[0]
	m[1][0] = vr[1]
	m[2][0] = vr[2]

	m[0][1] = vup[0]
	m[1][1] = vup[1]
	m[2][1] = vup[2]

	m[0][2] = vf[0]
	m[1][2] = vf[1]
	m[2][2] = vf[2]

	im = m.copy() #memcpy(im, m, sizeof(im));

	im[0][1] = m[1][0]
	im[0][2] = m[2][0]
	im[1][0] = m[0][1]
	im[1][2] = m[2][1]
	im[2][0] = m[0][2]
	im[2][1] = m[1][2]

	#memset(zrot, 0, sizeof(zrot));
	zrot[2][2] = 1.0

	zrot[0][0] = math.cos(DEG2RAD(degrees))
	zrot[0][1] = math.sin(DEG2RAD(degrees))
	zrot[1][0] = -math.sin(DEG2RAD(degrees))
	zrot[1][1] = math.cos(DEG2RAD(degrees))

	R_ConcatRotations(m, zrot, tmpmat)
	R_ConcatRotations(tmpmat, im, rot)

	for i in range(3):

		dst[i] = rot[i][0] * point[0] + rot[i][1] * point[1] + rot[i][2] * \
				 point[2]

def AngleVectors(angles, forward, right, up): #const vec3_t, vec3_t, vec3_t, vec3_t
	# Q2PORT: np.float32 scalars do the float arithmetic of the C, so the results match it exactly

	"""
	float angle;
	static float sr, sp, sy, cr, cp, cy;
	"""
	F = np.float32

	angle = F(float(angles[shared.YAW]) * (math.pi * 2 / 360))
	sy = F(math.sin(angle))
	cy = F(math.cos(angle))
	angle = F(float(angles[shared.PITCH]) * (math.pi * 2 / 360))
	sp = F(math.sin(angle))
	cp = F(math.cos(angle))
	angle = F(float(angles[shared.ROLL]) * (math.pi * 2 / 360))
	sr = F(math.sin(angle))
	cr = F(math.cos(angle))

	if forward is not None:

		forward[0] = cp * cy
		forward[1] = cp * sy
		forward[2] = -sp


	if right is not None:

		right[0] = (-1 * sr * sp * cy + - 1 * cr * -sy)
		right[1] = (-1 * sr * sp * sy + - 1 * cr * cy)
		right[2] = -1 * sr * cp


	if up is not None:

		up[0] = (cr * sp * cy + - sr * -sy)
		up[1] = (cr * sp * sy + - sr * cy)
		up[2] = cr * cp

"""
void
AngleVectors2(const vec3_t value1, vec3_t angles)
{
	float yaw, pitch;

	if ((value1[1] == 0) && (value1[0] == 0))
	{
		yaw = 0;

		if (value1[2] > 0)
		{
			pitch = 90;
		}

		else
		{
			pitch = 270;
		}
	}
	else
	{
		float forward;

		if (value1[0])
		{
			yaw = ((float)atan2(value1[1], value1[0]) * 180 / M_PI);
		}

		else if (value1[1] > 0)
		{
			yaw = 90;
		}

		else
		{
			yaw = 270;
		}

		if (yaw < 0)
		{
			yaw += 360;
		}

		forward = (float)sqrt(value1[0] * value1[0] + value1[1] * value1[1]);
		pitch = ((float)atan2(value1[2], forward) * 180 / M_PI);

		if (pitch < 0)
		{
			pitch += 360;
		}
	}

	angles[PITCH] = -pitch;
	angles[YAW] = yaw;
	angles[ROLL] = 0;
}
"""

def ProjectPointOnPlane(dst, p, normal):
	if dst is None or p is None or normal is None:
		return

	denom = shared.DotProduct(normal, normal)
	if denom == 0.0:
		dst[0] = p[0]
		dst[1] = p[1]
		dst[2] = p[2]
		return

	inv_denom = 1.0 / denom
	d = shared.DotProduct(normal, p) * inv_denom

	dst[0] = p[0] - d * normal[0] * inv_denom
	dst[1] = p[1] - d * normal[1] * inv_denom
	dst[2] = p[2] - d * normal[2] * inv_denom


"""
** assumes "src" is normalized
"""
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


def R_ConcatRotations(in1, in2, out): #const float [3][3], const float [3][3], float [3][3]

	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] + \
				in1[0][2] * in2[2][0]
	out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] + \
				in1[0][2] * in2[2][1]
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] + \
				in1[0][2] * in2[2][2]
	out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] + \
				in1[1][2] * in2[2][0]
	out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] + \
				in1[1][2] * in2[2][1]
	out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] + \
				in1[1][2] * in2[2][2]
	out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] + \
				in1[2][2] * in2[2][0]
	out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] + \
				in1[2][2] * in2[2][1]
	out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] + \
				in1[2][2] * in2[2][2]

"""
void
R_ConcatTransforms(const float in1[3][4], const float in2[3][4], float out[3][4])
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
"""

"""
float
Q_fabs(float f)
{
	int tmp = *(int *)&f;

	tmp &= 0x7FFFFFFF;
	return *(float *)&tmp;
}
"""

"""
===============
LerpAngle

===============
"""
def LerpAngle(a2, a1, frac):
	if a1 - a2 > 180:
		a1 -= 360
	if a1 - a2 < -180:
		a1 += 360
	return a2 + frac * (a1 - a2)

def anglemod(a):
	return (360.0 / 65536.0) * (int(a * (65536.0 / 360.0)) & 65535)


def BoxOnPlaneSide2(emins, emaxs, plane):
	corners = np.empty((2, 3), dtype=np.float32)
	for i in range(3):
		if plane.normal[i] < 0:
			corners[0][i] = emins[i]
			corners[1][i] = emaxs[i]
		else:
			corners[0][i] = emaxs[i]
			corners[1][i] = emins[i]

	dist1 = shared.DotProduct(plane.normal, corners[0]) - plane.dist
	dist2 = shared.DotProduct(plane.normal, corners[1]) - plane.dist
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

	return sides

# Q2PORT: C truncation of an int to a short, as when storing ANGLE2SHORT into a short field
def	TO_SHORT(x):	return ((int(x) + 32768) & 65535) - 32768

"""
void
ClearBounds(vec3_t mins, vec3_t maxs)
{
	mins[0] = mins[1] = mins[2] = 99999;
	maxs[0] = maxs[1] = maxs[2] = -99999;
}
"""

"""
void
AddPointToBounds(const vec3_t v, vec3_t mins, vec3_t maxs)
{
	int i;

	for (i = 0; i < 3; i++)
	{
		vec_t val;

		val = v[i];

		if (val < mins[i])
		{
			mins[i] = val;
		}

		if (val > maxs[i])
		{
			maxs[i] = val;
		}
	}
}
"""

"""
void
ClosestPointOnBounds(const vec3_t p, const vec3_t amin, const vec3_t amax, vec3_t out)
{
	int i;

	for (i = 0; i < 3; i++)
	{
		if (amin[i] > p[i])
		{
			out[i] = amin[i];
		}
		else if (amax[i] < p[i])
		{
			out[i] = amax[i];
		}
		else
		{
			out[i] = p[i];
		}
	}
}
"""

"""
qboolean
IsZeroVector(vec3_t v)
{
	return (v[0] == 0.0f && v[1] == 0.0f && v[2] == 0.0f);
}
"""

def VectorCompare (v1, v2): #vec3_t, vec3_t (returns int)

	if v1[0] != v2[0] or v1[1] != v2[1] or v1[2] != v2[2]:
		return 0

	return 1


def VectorNormalize(v): #vec3_t (returns vec_t)
	# Q2PORT: np.float32 scalars do the float arithmetic of the C, so the results match it exactly

	#float length;

	length = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]
	length = np.float32(math.sqrt(length))

	if length:

		#float ilength;

		ilength = 1 / length
		v[0] *= ilength
		v[1] *= ilength
		v[2] *= ilength


	return length

def VectorNormalize2(v, out): #const vec3_t, vec3_t (returns vec_t)

	shared.VectorCopy(v, out)

	return VectorNormalize(out)

def VectorMA(veca, scale, vecb, vecc): vecc[:] = [veca[i] + scale * vecb[i] for i in range(3)]

"""
vec_t
_DotProduct(const vec3_t v1, const vec3_t v2)
{
	return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2];
}
"""

"""
void
_VectorSubtract(const vec3_t veca, const vec3_t vecb, vec3_t out)
{
	out[0] = veca[0] - vecb[0];
	out[1] = veca[1] - vecb[1];
	out[2] = veca[2] - vecb[2];
}
"""

"""
void
_VectorAdd(const vec3_t veca, const vec3_t vecb, vec3_t out)
{
	out[0] = veca[0] + vecb[0];
	out[1] = veca[1] + vecb[1];
	out[2] = veca[2] + vecb[2];
}
"""

"""
void
_VectorCopy(const vec3_t in, vec3_t out)
{
	out[0] = in[0];
	out[1] = in[1];
	out[2] = in[2];
}
"""

def CrossProduct(v1, v2, cross):
	cross[0] = v1[1]*v2[2] - v1[2]*v2[1]
	cross[1] = v1[2]*v2[0] - v1[0]*v2[2]
	cross[2] = v1[0]*v2[1] - v1[1]*v2[0]

"""
vec_t
VectorLengthSquared(vec3_t v)
{
	return (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}
"""

def VectorLength(v): #const vec3_t (returns vec_t)
	# Q2PORT: float arithmetic as in the C; sqrtf is the double sqrt rounded to float

	return np.float32(math.sqrt((v[0] * v[0]) + (v[1] * v[1]) + (v[2] * v[2])))

def VectorInverse(v):
	v[0] = -v[0]
	v[1] = -v[1]
	v[2] = -v[2]

"""
void
VectorInverse2(const vec3_t v, vec3_t out)
{
	VectorCopy(v, out);
	VectorInverse(out);
}
"""

def VectorScale(vec, scale, out): out[:] = [vec[i] * scale for i in range(3)]
"""
void
VectorLerp(const vec3_t v1, const vec3_t v2, const vec_t factor, vec3_t out)
{
	VectorSubtract(v2, v1, out);
	VectorScale(out, factor, out);
	VectorAdd(out, v1, out);
}
"""

"""
void
VectorToQuat(const vec3_t v, quat_t out)
{
	out[0] = v[0];
	out[1] = v[1];
	out[2] = v[2];
	out[3] = 0.0f;
}
"""

"""
void
QuatInverse(const quat_t q, quat_t out)
{
	out[0] = -q[0];
	out[1] = -q[1];
	out[2] = -q[2];
	out[3] = q[3];
}
"""

"""
void
QuatMultiply(const quat_t q1, const quat_t q2, quat_t out)
{
	out[0] = q1[3] * q2[0] + q1[0] * q2[3] + q1[1] * q2[2] - q1[2] * q2[1];
	out[1] = q1[3] * q2[1] - q1[0] * q2[2] + q1[1] * q2[3] + q1[2] * q2[0];
	out[2] = q1[3] * q2[2] + q1[0] * q2[1] - q1[1] * q2[0] + q1[2] * q2[3];
	out[3] = q1[3] * q2[3] - q1[0] * q2[0] - q1[1] * q2[1] - q1[2] * q2[2];
}
"""

"""
void
QuatAngleAxis(const vec3_t v, float angle, quat_t out)
{
	const vec_t scale = sinf(angle * 0.5f);
	vec3_t v_out;

	VectorNormalize2(v, v_out);
	VectorScale(v_out, scale, v_out);

	out[0] = v_out[0];
	out[1] = v_out[1];
	out[2] = v_out[2];
	out[3] = cosf(angle * 0.5f);
}
"""

"""
void
RotateVectorByUnitQuat(vec3_t v, quat_t q_unit)
{
	quat_t q_vec, q_inv, q_out;

	VectorToQuat(v, q_vec);
	QuatInverse(q_unit, q_inv);
	QuatMultiply(q_unit, q_vec, q_out);
	QuatMultiply(q_out, q_inv, q_out);

	v[0] = q_out[0];
	v[1] = q_out[1];
	v[2] = q_out[2];
}
"""

"""
float
Q_magnitude(float x, float y)
{
	return sqrtf(x * x + y * y);
}
"""

"""
int
Q_log2(int val)
{
	int answer = 0;

	while (val >>= 1)
	{
		answer++;
	}

	return answer;
}
"""

"""
const char *
COM_SkipPath(const char *pathname)
{
	const char *last;

	last = pathname;

	while (*pathname)
	{
		if (*pathname == '/')
		{
			last = pathname + 1;
		}

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

r"""
char *
COM_StripExtension2(char *path)
{
	char *s ;

	if (*path == '\0')
	{
		return NULL;
	}

	s = path + (strlen(path) - 1);

	if (*s != '.')
	{
		for (; s > path && *s != '/' && *s != '\\'; s--)
		{
			if (*s == '.')
			{
				*s = '\0';
				return s + 1;
			}
		}
	}

	return NULL;
}
"""

"""
const char *
COM_FileExtension(const char *in)
{
	const char *ext = strrchr(in, '.');

	if (!ext || ext == in)
	{
		return "";
	}

	return ext + 1;
}
"""

"""
void
COM_FileBase(const char *in, char *out)
{
	const char *s, *s2;

	s = in + strlen(in) - 1;

	while (s != in && *s != '.')
	{
		s--;
	}

	for (s2 = s; s2 != in && *s2 != '/'; s2--)
	{
	}

	if (s - s2 < 2)
	{
		out[0] = 0;
	}
	else
	{
		s--;
		memcpy(out, s2 + 1, s - s2);
		out[s - s2] = 0;
	}
}
"""

"""
/*
 * Returns the path up to, but not including the last /
 */
void
COM_FilePath(const char *in, char *out)
{
	const char *s;

	s = in + strlen(in) - 1;

	while (s != in && *s != '/')
	{
		s--;
	}

	memcpy(out, in, s - in);
	out[s - in] = 0;
}
"""

"""
void
COM_DefaultExtension(char *path, const char *extension)
{
	char *src;

	/* */
	/* if path doesn't have a .EXT, append extension */
	/* (extension should include the .) */
	/* */
	src = path + strlen(path) - 1;

	while (*src != '/' && src != path)
	{
		if (*src == '.')
		{
			return;                 /* it has an extension */
		}

		src--;
	}

	strcat(path, extension);
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
static short
ShortSwap(short l)
{
	byte b1, b2;

	b1 = l & 255;
	b2 = (l >> 8) & 255;

	return (b1 << 8) + b2;
}
"""

"""
static short
ShortNoSwap(short l)
{
	return l;
}
"""

"""
static int
LongSwap(int l)
{
	byte b1, b2, b3, b4;

	b1 = l & 255;
	b2 = (l >> 8) & 255;
	b3 = (l >> 16) & 255;
	b4 = (l >> 24) & 255;

	return ((int)b1 << 24) + ((int)b2 << 16) + ((int)b3 << 8) + b4;
}
"""

"""
static int
LongNoSwap(int l)
{
	return l;
}
"""

"""
static float
FloatSwap(float f)
{
	union
	{
		float f;
		byte b[4];
	} dat1, dat2;

	dat1.f = f;
	dat2.b[0] = dat1.b[3];
	dat2.b[1] = dat1.b[2];
	dat2.b[2] = dat1.b[1];
	dat2.b[3] = dat1.b[0];
	return dat2.f;
}
"""

"""
static float
FloatNoSwap(float f)
{
	return f;
}
"""

def Swap_Init(): #void
	# Q2PORT: Big*/Little* use struct with an explicit byte order, so there are no function pointers to set

	from common import clientserver	# Q2PORT: imported here, shared.c is loaded before the engine

	"""
	byte swaptest[2] = {1, 0};
	short swapTestShort;
	"""
	#YQ2_STATIC_ASSERT(sizeof(short) == 2, "invalid short size");
	swapTestShort = struct.unpack("=h", bytes((1, 0)))[0] #memcpy(&swapTestShort, swaptest, 2);

	# set the byte swapping variables in a portable manner
	if swapTestShort == 1:

		#bigendien = false;
		clientserver.Com_Printf("Byte ordering: little endian\n\n")

	else:

		#bigendien = true;
		clientserver.Com_Printf("Byte ordering: big endian\n\n")


"""
/*
 * does a varargs printf into a temp buffer, so I don't
 * need to have varargs versions of all text functions.
 */
char *
va(const char *format, ...)
{
	va_list argptr;
	static char string[1024];

	va_start(argptr, format);
	vsnprintf(string, 1024, format, argptr);
	va_end(argptr);

	return string;
}
"""

def COM_Parse(data: str, cursor: int): #char ** (returns char *)
	# Q2PORT: *data_p is the text and an offset into it; returns the token and the new offset (None for NULL)

	"""
	int c;
	int len;
	char *data;
	"""

	length = 0
	com_token = [] #char[MAX_TOKEN_CHARS]

	if data is None or cursor is None:

		return "", None #*data_p = NULL;


	while True: #skipwhite:

		c = data[cursor] if cursor < len(data) else '\0'
		while c <= ' ':

			if c == '\0':

				return "", None #*data_p = NULL;


			cursor += 1
			c = data[cursor] if cursor < len(data) else '\0'


		# skip // comments
		if (c == '/') and (data[cursor + 1:cursor + 2] == '/'):

			while cursor < len(data) and data[cursor] != '\n':

				cursor += 1


			continue #goto skipwhite;

		break

	# handle quoted strings specially
	if c == '\"':

		cursor += 1

		while 1:

			c = data[cursor] if cursor < len(data) else '\0'
			cursor += 1

			if (c == '\"') or c == '\0':

				break #goto done;


			if length < shared.MAX_TOKEN_CHARS:

				com_token.append(c)
				length += 1

	else:

		# parse a regular word
		while True:

			if length < shared.MAX_TOKEN_CHARS:

				com_token.append(c)
				length += 1


			cursor += 1
			c = data[cursor] if cursor < len(data) else '\0'

			if not (c > ' '): break


	#done:
	if length == shared.MAX_TOKEN_CHARS:

		length = 0
		com_token = []


	return "".join(com_token), cursor

"""
void
Com_PageInMemory(const byte *buffer, int size)
{
	int i;

	for (i = size - 1; i > 0; i -= 4096)
	{
		paged_total += buffer[i];
	}
}
"""

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
int
Q_strncasecmp(const char *s1, const char *s2, int n)
{
	int c1;

	do
	{
		int c2;

		c1 = *s1++;
		c2 = *s2++;

		if (!n--)
		{
			return 0; /* strings are equal until end point */
		}

		if (c1 != c2)
		{
			if ((c1 >= 'a') && (c1 <= 'z'))
			{
				c1 -= ('a' - 'A');
			}

			if ((c2 >= 'a') && (c2 <= 'z'))
			{
				c2 -= ('a' - 'A');
			}

			if (c1 != c2)
			{
				return -1; /* strings not equal */
			}
		}
	}
	while (c1);

	return 0; /* strings are equal */
}
"""

"""
char *Q_strcasestr(const char *haystack, const char *needle)
{
	size_t len = strlen(needle);

	for (; *haystack; haystack++)
	{
		if (!Q_strncasecmp(haystack, needle, len))
		{
			return (char *)haystack;
		}
	}
	return 0;
}
"""

def Q_strcasecmp (s1, s2): #char *, char *

	if s1 is None or s2 is None:
		return -1
	if s1.lower() == s2.lower():
		return 0
	return -1
	##return Q_strncasecmp (s1, s2, 99999);

r"""
void
Q_replacebackslash(char *curr)
{
	while (*curr)
	{
		if (*curr == '\\')
		{
			*curr = '/';
		}
		curr++;
	}
}
"""

r"""
void
Com_sprintf(char *dest, int size, const char *fmt, ...)
{
	int len;
	va_list argptr;

	va_start(argptr, fmt);
	len = vsnprintf(dest, size, fmt, argptr);
	va_end(argptr);

	if (len >= size)
	{
		Com_Printf("%s: overflow\n", __func__);
	}
}
"""

r"""
void
Q_strlwr(char *s)
{
	for (; *s != '\0'; s++)
	{
		*s = tolower(*s);
	}
}
"""

r"""
void
Q_strupr(char *s)
{
	for (; *s != '\0'; s++)
	{
		*s = toupper(*s);
	}
}
"""

r"""
int
Q_strlcpy(char *dst, const char *src, int size)
{
	const char *s = src;

	while (*s)
	{
		if (size > 1)
		{
			*dst++ = *s;
			size--;
		}
		s++;
	}
	if (size > 0)
	{
		*dst = '\0';
	}

	return s - src;
}
"""

def Q_strlcpy_ascii(s: str, n: int): #char *, const char *, size_t (returns size_t)
	# Q2PORT: the destination is returned with the count: ns, d = Q_strlcpy_ascii(s, n)

	"""
	size_t ns = 0;
	char c;
	int dzero = n == 0;
	"""
	d = []
	ns = 0
	dzero = n == 0

	if not dzero:

		n -= 1


	for c in s:

		c = ord(c)
		c &= 127

		if (c >= 32) and (c < 127):

			if n:

				d.append(chr(c))
				n -= 1


			ns += 1

	#if (!dzero) *d = '\0';

	return ns, "".join(d)

"""
int
Q_strlcat(char *dst, const char *src, int size)
{
	char *d = dst;

	while (size > 0 && *d)
	{
		size--;
		d++;
	}

	return (d - dst) + Q_strlcpy(d, src, size);
}
"""

r"""
void
Q_strdel(char *s, size_t i, size_t n)
{
	size_t len;

	if (!n)
	{
		return;
	}

	len = strlen(s);

	if (i >= len || n > (len - i))
	{
		return;
	}

	memmove(s + i, s + i + n, len - i);
	s[len - n] = '\0';
}
"""

r"""
size_t
Q_strins(char *dest, const char *src, size_t i, size_t n)
{
	size_t dlen;
	size_t slen;

	if (!src || *src == '\0')
	{
		return 0;
	}

	slen = strlen(src);
	dlen = strlen(dest);

	if (i > dlen || (dlen + slen + 1) > n)
	{
		return 0;
	}

	memmove(dest + i + slen, dest + i, dlen - i + 1);
	memcpy(dest + i, src, slen);

	return slen;
}
"""

r"""
qboolean
Q_strisnum(const char *s)
{
	for (; *s != '\0'; s++)
	{
		if (!isdigit(*s))
		{
			return false;
		}
	}

	return true;
}
"""

def Q_strchrs(s: str, chrs: str): #const char *, const char * (returns char *)
	# Q2PORT: returns the offset of the first hit in s, or None

	for s_p in range(len(s)):

		if s[s_p] in chrs:

			return s_p


	return None

"""
char *
Q_strrchrs(const char *s, const char *chrs)
{
	const char *curr;

	for (curr = s + (strlen(s) - 1); curr >= s; curr--)
	{
		if (strchr(chrs, *curr))
		{
			return (char *)curr;
		}
	}

	return NULL;
}
"""

def Q_strchr0(s: str, c: str, s_p: int = 0)->int: #const char *, char (returns char *)
	# Q2PORT: s_p is the pointer as an offset into s; the offset of c, or of the end of s, is returned

	while s_p < len(s) and s[s_p] != c:

		s_p += 1


	return s_p

"""
FILE *Q_fopen(const char *file, const char *mode)
{
	WCHAR wfile[MAX_OSPATH];
	WCHAR wmode[16];

	int len = MultiByteToWideChar(CP_UTF8, 0, file, -1, wfile, MAX_OSPATH);

	if (len > 0)
	{
		if (MultiByteToWideChar(CP_UTF8, 0, mode, -1, wmode, 16) > 0)
		{
			// make sure it's a regular file and not a directory or sth, see #394
			struct _stat buf;
			int statret = _wstat(wfile, &buf);
			if((statret == 0 && (buf.st_mode & _S_IFREG) != 0) || (statret == -1 && errno == ENOENT))
			{
				return _wfopen(wfile, wmode);
			}
		}
	}

	return NULL;
}
"""

"""
FILE *Q_fopen(const char *file, const char *mode)
{
	// make sure it's a regular file and not a directory or sth, see #394
	struct stat statbuf;
	int statret = stat(file, &statbuf);
	// (it's ok if it doesn't exist though, maybe we wanna write/create)
	if((statret == -1 && errno != ENOENT) || (statret == 0 && (statbuf.st_mode & S_IFREG) == 0))
	{
		return NULL;
	}
	return fopen(file, mode);
}
"""

"""
int
Q_sort_stricmp(const void *s1, const void *s2)
{
	return Q_stricmp(*(char**)s1, *(char**)s2);
}
"""

"""
int
Q_sort_strcomp(const void *s1, const void *s2)
{
	return strcmp(*(char **)s1, *(char **)s2);
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
def Info_ValueForKey(s: str, key: str)->str: #const char *, const char * (returns char *)

	# use two buffers so compares
	# work without stomping on each other
	#static char value[2][MAX_INFO_VALUE];
	#static int valueindex = 0;
	# Q2PORT: Python strings are values, so the two static buffers aren't needed

	"""
	const char *kstart, *vstart;
	char *v;
	size_t klen, vlen;
	"""

	#valueindex ^= 1;
	v = ""

	klen = len(key)

	s_p = 0
	while s_p < len(s):

		if s[s_p] == '\\':

			s_p += 1


		kstart = s_p
		s_p = Q_strchr0(s, '\\', s_p)

		if s_p >= len(s):

			break


		vstart = s_p + 1
		s_p = Q_strchr0(s, '\\', vstart)

		if s[kstart:kstart + klen] == key and \
			s[kstart + klen:kstart + klen + 1] == '\\':

			vlen = s_p - vstart

			if vlen > 0:

				vlen += 1 # Q_strlcpy accounts for null char

				#Q_strlcpy(v, vstart, (vlen < MAX_INFO_VALUE) ? vlen : MAX_INFO_VALUE);
				v = s[vstart:vstart + ((vlen if vlen < shared.MAX_INFO_VALUE else shared.MAX_INFO_VALUE) - 1)]


			break



	return v

def Info_RemoveKey(s: str, key: str)->str: #char *, const char *
	# Q2PORT: s is changed in place in C; here the new string is returned

	"""
	size_t klen;
	"""

	if '\\' in key:

		return s


	klen = len(key)

	s_p = 0
	while s_p < len(s):

		"""
		const char *kstart;
		char *start;
		"""

		start = s_p

		if s[s_p] == '\\':

			s_p += 1


		# key segment
		kstart = s_p
		s_p = Q_strchr0(s, '\\', s_p)

		if s_p < len(s):

			# value segment
			s_p = Q_strchr0(s, '\\', s_p + 1)


		if s[kstart:kstart + klen] == key and \
			(s[kstart + klen:kstart + klen + 1] == '\\' or kstart + klen == len(s)):

			#memmove(start, s, strlen(s) + 1);
			return s[:start] + s[s_p:]


	return s

"""
 * Some characters are illegal in info strings
 * because they can mess up the server's parsing
"""
def Info_Validate(s: str)->bool: #const char * (returns qboolean)

	return True if (Q_strchrs(s, "\";") is None) else False

def Info_ValidateKeyValue(key: str, value: str)->bool: #const char *, const char * (returns qboolean)

	from common import clientserver	# Q2PORT: imported here, shared.c is loaded before the engine

	"""
	const char *hit;
	"""

	hit = Q_strchrs(key, "\"\\;")
	if hit is not None:

		clientserver.Com_Printf("Can't use keys with a '%c'\n", key[hit])
		return False


	if value is not None:

		hit = Q_strchrs(value, "\"\\")
		if hit is not None:

			clientserver.Com_Printf("Can't use values with a '%c'\n", value[hit])
			return False



	if (len(key) > shared.MAX_INFO_KEY - 1) or \
		(value is not None and (len(value) > shared.MAX_INFO_VALUE - 1)):

		clientserver.Com_Printf("Keys and values must be < %i characters.\n", shared.MAX_INFO_KEY)
		return False


	return True

def Info_SetValueForKey(s: str, key: str, value: str)->str: #char *, const char *, const char *
	# Q2PORT: s is changed in place in C; here the new string is returned

	from common import clientserver	# Q2PORT: imported here, shared.c is loaded before the engine

	"""
	char newi[MAX_INFO_KEYVAL];
	size_t slen, needed;
	char *dest;
	"""

	if key is None:

		return s


	if not Info_ValidateKeyValue(key, value):

		return s


	s = Info_RemoveKey(s, key)

	if value is None or value == "":

		return s


	newi = "\\{}\\{}".format(key, value)[:shared.MAX_INFO_KEYVAL - 1] #Com_sprintf(newi, sizeof(newi), "\\%s\\%s", key, value);

	slen = len(s)
	#dest = s + slen;

	needed, dest = Q_strlcpy_ascii(newi, shared.MAX_INFO_STRING - slen)
	if needed > (shared.MAX_INFO_STRING - slen - 1):

		clientserver.Com_Printf("Info string length exceeded\n")
		dest = "" #*dest = '\0';


	return s + dest

"""
unsigned int
NextPow2(unsigned int i)
{
	if (!i)
	{
		return 1U;
	}

	i--;

	if (i & (1U << 31U))
	{
		return 0U;
	}

	i |= i >> 1U;
	i |= i >> 2U;
	i |= i >> 4U;
	i |= i >> 8U;
	i |= i >> 16U;

	return i + 1U;
}
"""

"""
unsigned int
NextPow2gt(unsigned int i)
{
	return NextPow2(i + 1U);
}
"""

"""
void *
Q_realloc0(void *ptr, size_t prev_n, size_t new_n)
{
	void *new_ptr = realloc(ptr, new_n);

	if (!new_ptr)
	{
		return NULL;
	}

	if (new_n > prev_n)
	{
		memset((char *)new_ptr + prev_n, 0, new_n - prev_n);
	}

	return new_ptr;
}
"""

"""
void
StrList_Init(strlist_t *sl, int cap)
{
	memset(sl, 0, sizeof(*sl));

	if (cap > 0)
	{
		/* allocating +1 ensures the list is always NULL terminated */
		sl->data = calloc(cap + 1, sizeof(char *));

		if (!sl->data)
		{
			return;
		}

		sl->cap = cap;
	}
}
"""

"""
void
StrList_Free(strlist_t *sl)
{
	if (sl->data)
	{
		int i;

		for (i = 0; i < sl->num; i++)
		{
			if (sl->data[i])
			{
				free(sl->data[i]);
			}
		}

		free(sl->data);
		sl->data = NULL;
	}

	sl->cap = 0;
	sl->num = 0;
}
"""

"""
void
StrList_Compress(strlist_t *sl)
{
	char **new_data;

	if (sl->cap <= sl->num)
	{
		return;
	}

	new_data = realloc(sl->data, (sl->num + 1) * sizeof(char *));
	if (new_data)
	{
		sl->data = new_data;
		sl->cap = sl->num;
	}
}
"""

"""
int
StrList_Find(const strlist_t *sl, sl_eqfunc eq, const char *s)
{
	int i;

	if (!eq)
	{
		eq = strcmp;
	}

	for (i = 0; i < sl->num; i++)
	{
		if (!eq(sl->data[i], s))
		{
			return i;
		}
	}

	return sl->num;
}
"""

"""
void
StrList_Expand(strlist_t *sl, int new_cap)
{
	char **new_data;

	if (new_cap <= sl->cap)
	{
		return;
	}

	new_data = Q_realloc0(sl->data,
		!sl->cap ? 0 : ((sl->cap + 1) * sizeof(char *)),
		(new_cap + 1) * sizeof(char *));

	if (!new_data)
	{
		return;
	}

	sl->data = new_data;
	sl->cap = new_cap;
}
"""

"""
void
StrList_Append(strlist_t *sl, const char *s)
{
	char *new_s;

	if (sl->num >= sl->cap)
	{
		StrList_Expand(sl, NextPow2gt(sl->cap));

		if (sl->num >= sl->cap)
		{
			return;
		}
	}

	new_s = strdup(s);
	if (new_s)
	{
		sl->data[sl->num] = new_s;
		sl->num++;
	}
}
"""

r"""
void
StrList_Print(const strlist_t *sl, void (*printfunc)(const char *fmt, ...))
{
	int i;

	if (!printfunc)
	{
		printfunc = Com_Printf;
	}

	printfunc("%d / %d items\n{\n", sl->num, sl->cap);

	for (i = 0; i < sl->num; i++)
	{
		printfunc("  '%s'\n", sl->data[i]);
	}

	if (sl->num && !sl->data[sl->num])
	{
		printfunc("  NULL\n");
	}

	printfunc("}\n");
}
"""

"""
int
Word_Count(const char *s)
{
	int n = 0;
	qboolean in_word = false;

	if (!s) return 0;

	for (; *s; ++s)
	{
		if ( isspace( (unsigned char)*s ) )
		{
			in_word = false;
		}
		else if (!in_word)
		{
			in_word = true;
			++n;
		}
	}

	return n;
}
"""
