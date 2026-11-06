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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
USA.
"""
from __future__ import annotations

"""
#ifndef __GYRO_H__
#define __GYRO_H__

#include "../../../common/header/shared.h"
"""

# Default accelerometer magnitude (1 g).
GYRO_DEFAULT_ACCEL	= 1.0

# Sensitivity
GYRO_MIN_SENS	= 0.0			# RWS
GYRO_MAX_SENS	= 20.0			# RWS
GYRO_STEP_SENS	= 0.1			# RWS

# Tightening
GYRO_MIN_TIGHT_THRESH	= 0.0	# deg/s
GYRO_MAX_TIGHT_THRESH	= 50.0	# deg/s
GYRO_STEP_TIGHT_THRESH	= 0.5	# deg/s

# Smoothing
GYRO_MIN_SMOOTH_THRESH	= 0.0	# deg/s
GYRO_MAX_SMOOTH_THRESH	= 50.0	# deg/s
GYRO_STEP_SMOOTH_THRESH	= 0.5	# deg/s
GYRO_MIN_SMOOTH_WINDOW	= 0.0	# seconds
GYRO_MAX_SMOOTH_WINDOW	= 0.5	# seconds

# Acceleration
GYRO_MIN_ACCEL_MULT	= 1.0		# RWS multiplier
GYRO_MAX_ACCEL_MULT	= 20.0		# RWS multiplier
GYRO_STEP_ACCEL_MULT	= 0.1		# RWS multiplier
GYRO_MIN_ACCEL_THRESH	= 0.0	# deg/s
GYRO_MAX_ACCEL_THRESH	= 300.0	# deg/s
GYRO_STEP_ACCEL_THRESH	= 5.0	# deg/s

# typedef enum gyro_space_t
GYRO_SPACE_LOCAL	= 0
GYRO_SPACE_PLAYER	= 1
GYRO_SPACE_WORLD	= 2

# typedef enum gyro_local_roll_t
GYRO_LOCAL_ROLL_OFF		= 0
GYRO_LOCAL_ROLL_ON		= 1
GYRO_LOCAL_ROLL_INVERT	= 2

"""
// Processes accumulated samples and returns pitch rate and yaw rate in
// radians/second. If no new samples were accumulated since the last call to
// this function, then the previous samples are used.
void IN_GYRO_Process(float delta_time, float *out_pitch_rate,
					 float *out_yaw_rate);

// Accumulates accelerometer samples (x, y, z in units of gravity, g).
void IN_GYRO_AccumulateAccelSamples(vec3_t accelerometer_data);

// Accumulates gyro samples (pitch, yaw, roll in radians/second).
void IN_GYRO_AccumulateGyroSamples(vec3_t gyro_data);
"""
