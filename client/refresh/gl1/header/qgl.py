"""
 * Copyright (C) 2013 Alejandro Ricoveri
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
 * Header for qgl.c (the GL extension pointers are in gl1/qgl.py)
 *
 * =======================================================================
"""
from __future__ import annotations

"""
#ifndef REF_QGL_H
#define REF_QGL_H

#include <GL/gl.h>
"""

# Extracted from <glext.h>
#ifndef GL_VERSION_1_4
GL_POINT_SIZE_MIN					= 0x8126
GL_POINT_SIZE_MAX					= 0x8127
GL_POINT_DISTANCE_ATTENUATION		= 0x8129
GL_GENERATE_MIPMAP					= 0x8191
#endif

#ifndef GL_VERSION_1_3
GL_TEXTURE0							= 0x84C0
GL_TEXTURE1							= 0x84C1
GL_MULTISAMPLE						= 0x809D
GL_COMBINE							= 0x8570
GL_RGB_SCALE						= 0x8573
#endif

#ifndef GL_EXT_shared_texture_palette
GL_SHARED_TEXTURE_PALETTE_EXT		= 0x81FB
#endif

#ifndef GL_EXT_texture_filter_anisotropic
GL_TEXTURE_MAX_ANISOTROPY_EXT		= 0x84FE
GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT	= 0x84FF
#endif

#ifndef GL_NV_multisample_filter_hint
GL_MULTISAMPLE_FILTER_HINT_NV		= 0x8534
#endif

# Q2PORT: from the EXT_paletted_texture header (the C gets it from <GL/gl.h>)
GL_COLOR_INDEX8_EXT					= 0x80E5

#endif
