"""
hmm.py - HandmadeMath.h

Q2PORT of the HandmadeMath subset used by the gl3 renderer (header/HandmadeMath.h).
The C uses a fixed 4x4 matrix (Elements[col][row], column-major) and vec3/vec4.
The port uses numpy: an hmm_mat4 is a 4x4 float32 array indexed [row][col], so
HMM_MultiplyMat4(Left, Right) is a standard numpy @ and a column-major flatten is
M.flatten(order="F") (for glUniformMatrix4fv). Only the functions gl3 calls are
ported.
"""

from __future__ import annotations

import math

import numpy as np


HMM_PI32 = 3.14159265359

# An hmm_mat4 is a 4x4 float32 numpy array [row][col].
# An hmm_vec3 / hmm_vec4 is a 3/4 element float32 numpy array.


def HMM_SinF (radians): #float (returns float)

	return math.sin (radians)


def HMM_CosF (radians): #float (returns float)

	return math.cos (radians)


def HMM_TanF (radians): #float (returns float)

	return math.tan (radians)


def HMM_ToRadians (degrees): #float (returns float)

	return degrees * (HMM_PI32 / 180.0)


def HMM_Vec3 (x, y, z): #float, float, float (returns hmm_vec3)

	return np.array ([x, y, z], dtype=np.float32)


def HMM_Vec4 (x, y, z, w): #float, float, float, float (returns hmm_vec4)

	return np.array ([x, y, z, w], dtype=np.float32)


def HMM_Mat4 (): #void (returns hmm_mat4)

	return np.zeros ((4, 4), dtype=np.float32)


def HMM_Mat4d (diagonal): #float (returns hmm_mat4)

	result = np.zeros ((4, 4), dtype=np.float32)

	for i in range (4):
		result[i][i] = diagonal

	return result


def HMM_NormalizeVec3 (a): #hmm_vec3 (returns hmm_vec3)

	a = np.asarray (a, dtype=np.float32)
	length = math.sqrt (a[0]*a[0] + a[1]*a[1] + a[2]*a[2])
	if length > 0:
		a = a / length
	return a


def HMM_MultiplyMat4 (left, right): #hmm_mat4, hmm_mat4 (returns hmm_mat4)

	return np.matmul (left, right).astype (np.float32)


def HMM_Orthographic (lft, right, bottom, top, near, far): #float *6 (returns hmm_mat4)

	result = HMM_Mat4d (1.0)

	result[0][0] = 2.0 / (right - lft)
	result[1][1] = 2.0 / (top - bottom)
	result[2][2] = -2.0 / (far - near)
	result[3][0] = - (right + lft) / (right - lft)
	result[3][1] = - (top + bottom) / (top - bottom)
	result[3][2] = - (far + near) / (far - near)

	return result


def HMM_Perspective (fov, aspect_ratio, near, far): #float, float, float, float (returns hmm_mat4)

	result = HMM_Mat4 ()

	tan_theta_over2 = HMM_TanF (fov * (HMM_PI32 / 360.0))

	result[0][0] = 1.0 / tan_theta_over2
	result[1][1] = aspect_ratio / tan_theta_over2
	result[2][3] = -1.0
	result[2][2] = (near + far) / (near - far)
	result[3][2] = (2.0 * near * far) / (near - far)
	result[3][3] = 0.0

	return result


def HMM_Translate (translation): #hmm_vec3 (returns hmm_mat4)

	result = HMM_Mat4d (1.0)

	result[3][0] = translation[0]
	result[3][1] = translation[1]
	result[3][2] = translation[2]

	return result


def HMM_Rotate (angle, axis): #float, hmm_vec3 (returns hmm_mat4)

	result = HMM_Mat4d (1.0)

	axis = np.asarray (axis, dtype=np.float32)
	axis = HMM_NormalizeVec3 (axis)

	sin_theta = HMM_SinF (HMM_ToRadians (angle))
	cos_theta = HMM_CosF (HMM_ToRadians (angle))
	cos_value = 1.0 - cos_theta

	ax, ay, az = axis[0], axis[1], axis[2]

	result[0][0] = (ax*ax*cos_value) + cos_theta
	result[0][1] = (ax*ay*cos_value) + (az*sin_theta)
	result[0][2] = (ax*az*cos_value) - (ay*sin_theta)

	result[1][0] = (ay*ax*cos_value) - (az*sin_theta)
	result[1][1] = (ay*ay*cos_value) + cos_theta
	result[1][2] = (ay*az*cos_value) + (ax*sin_theta)

	result[2][0] = (az*ax*cos_value) + (ay*sin_theta)
	result[2][1] = (az*ay*cos_value) - (ax*sin_theta)
	result[2][2] = (az*az*cos_value) + cos_theta

	return result
