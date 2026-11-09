"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 * Copyright (C) 2016-2017 Daniel Gibson
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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * Local header for the OpenGL3 refresher.
 *
 * =======================================================================
"""

from __future__ import annotations

import numpy as np
from enum import Enum
from OpenGL import GL
from common.header import files as files_h
from common.header import shared
from client.refresh.gl3.header import hmm

# always using RGBA now, GLES3 on RPi4 doesn't work otherwise
# and I think all modern GPUs prefer 4byte pixels over 3bytes
gl3_solid_format = GL.GL_RGBA
gl3_alpha_format = GL.GL_RGBA
gl3_tex_solid_format = GL.GL_RGBA
gl3_tex_alpha_format = GL.GL_RGBA

# attribute locations for vertex shaders
class _attr(Enum):
	GL3_ATTRIB_POSITION = 0
	GL3_ATTRIB_TEXCOORD = 1 # for normal texture
	GL3_ATTRIB_LMTEXCOORD = 2 # for lightmap
	GL3_ATTRIB_COLOR = 3 # per-vertex color
	GL3_ATTRIB_NORMAL = 4 # vertex normal
	GL3_ATTRIB_LIGHTFLAGS = 5 # uint, each set bit means "dyn light i affects this surface"

GL3_ATTRIB_POSITION = _attr.GL3_ATTRIB_POSITION.value
GL3_ATTRIB_TEXCOORD = _attr.GL3_ATTRIB_TEXCOORD.value
GL3_ATTRIB_LMTEXCOORD = _attr.GL3_ATTRIB_LMTEXCOORD.value
GL3_ATTRIB_COLOR = _attr.GL3_ATTRIB_COLOR.value
GL3_ATTRIB_NORMAL = _attr.GL3_ATTRIB_NORMAL.value
GL3_ATTRIB_LIGHTFLAGS = _attr.GL3_ATTRIB_LIGHTFLAGS.value

# for stats
gl3_num3Ddraws, gl3_num2Ddraws, gl3_numBufferVtxData, gl3_numBufferUniforms = 0, 0, 0, 0

class gl3config_t(object):

	def __init__(self):
		self.renderer_string = None #const char *
		self.vendor_string = None #const char *
		self.version_string = None #const char *
		self.glsl_version_string = None #const char *
		self.major_version = 0 #int
		self.minor_version = 0 #int
		self.anisotropic = False #qboolean, is GL_EXT_texture_filter_anisotropic supported?
		self.debug_output = False #qboolean, is GL_ARB_debug_output supported?
		self.stencil = False #qboolean, do we have a stencil buffer?
		self.max_anisotropy = 0.0 #float

class gl3ShaderInfo_t(object):

	def __init__(self):
		self.shaderProgram = 0 #GLuint
		self.uniVblend = -1 #GLint
		self.uniLmScalesOrTime = -1 #GLint, for 3D it's lmScales, for 2D underwater PP it's time
		self.lmScales = np.zeros((4, 4), dtype=np.float32) #hmm_vec4 [4]

# ---- UBO data: std140 layouts as flat float32 numpy arrays ----

# gl3UniCommon_t: gamma intensity intensity2D _padding color(4) = 8 floats
UNICOMMON_GAMMA = 0
UNICOMMON_INTENSITY = 1
UNICOMMON_INTENSITY2D = 2
UNICOMMON_COLOR = 4 # vec4 at [4..7]

# gl3Uni2D_t: transMat4 = 16 floats
UNI2D_TRANS = 0

# gl3Uni3D_t: transProjViewMat4 transModelMat4 scroll time alpha overbrightbits
#            particleFadeFactor lightScaleForTurb _padding[2] = 40 floats
UNI3D_PROJVIEW = 0 # mat4 at [0..15]
UNI3D_MODEL = 16 # mat4 at [16..31]
UNI3D_SCROLL = 32
UNI3D_TIME = 33
UNI3D_ALPHA = 34
UNI3D_OVERBRIGHTBITS = 35
UNI3D_PARTICLEFADEFATOR = 36
UNI3D_LIGHTSCALEFORTURB = 37

# gl3UniLights_t: dynLights[32]{origin(3) _pad color(4)} numDynLights _padding[3] = 260 floats
UNILIGHTS_NUM = 256 # dynLights[i] at [i*8 .. i*8+7]; origin [0..2], color [4..7]

# ---- lightmap block layout ----
BLOCK_WIDTH = 1024
BLOCK_HEIGHT = 512
LIGHTMAP_BYTES = 4
MAX_LIGHTMAPS = 4
MAX_LIGHTMAPS_PER_SURFACE = files_h.MAXLIGHTMAPS # 4

class gl3state_t(object):

	def __init__(self):
		self.prev_mode = 0 #int
		self.fullscreen = False #qboolean
		# each lightmap consists of 4 sub-lightmaps allowing changing shadows on the same surface
		# most surfaces only have one really and the remaining are filled with dummy data
		# GLuint lightmap_textureIDs[MAX_LIGHTMAPS][MAX_LIGHTMAPS_PER_SURFACE]
		self.lightmap_textureIDs = [[0] * MAX_LIGHTMAPS_PER_SURFACE for _ in range(MAX_LIGHTMAPS)]
		self.currenttexture = 0 #GLuint, bound to GL_TEXTURE0
		self.currentlightmap = 0 #int, lightmap_textureIDs[currentlightmap] bound to GL_TEXTURE1
		self.currenttmu = 0 #GLuint, GL_TEXTURE0 or GL_TEXTURE1

		# FBO for postprocess effects (like under-water-warping)
		self.ppFBO = 0 #GLuint
		self.ppFBtex = 0 #GLuint, ppFBO's texture for color buffer
		self.ppFBtexWidth = 0 #int
		self.ppFBtexHeight = 0 #int
		self.ppFBrbo = 0 #GLuint, ppFBO's renderbuffer object for depth and stencil buffer
		self.ppFBObound = False #qboolean, is it currently bound (rendered to)?

		self.currentVAO = 0 #GLuint
		self.currentVBO = 0 #GLuint
		self.currentEBO = 0 #GLuint
		self.currentShaderProgram = 0 #GLuint
		self.currentUBO = 0 #GLuint

		# NOTE: make sure si2D is always the first shaderInfo
		self.si2D = gl3ShaderInfo_t() # shader for rendering 2D with textures
		self.si2Dtinted = gl3ShaderInfo_t() # shader for rendering 2D with textures and color tinting
		self.si2Dcolor = gl3ShaderInfo_t() # shader for rendering 2D with flat colors
		self.si2DpostProcess = gl3ShaderInfo_t() # shader to render postprocess FBO, when *not* underwater
		self.si2DpostProcessWater = gl3ShaderInfo_t() # shader to apply water-warp postprocess effect

		self.si3Dlm = gl3ShaderInfo_t() # a regular opaque face (e.g. from brush) with lightmap
		self.si3Dtrans = gl3ShaderInfo_t() # transparent is always w/o lightmap
		self.si3DcolorOnly = gl3ShaderInfo_t() # used for beams - no lightmaps
		self.si3Dturb = gl3ShaderInfo_t() # for water etc - always without lightmap
		self.si3DlmFlow = gl3ShaderInfo_t() # for flowing/scrolling things with lightmap (conveyor, ..?)
		self.si3DtransFlow = gl3ShaderInfo_t() # for transparent flowing/scrolling things (=> no lightmap)
		self.si3Dsky = gl3ShaderInfo_t() # guess what..
		self.si3Dsprite = gl3ShaderInfo_t() # for sprites
		self.si3DspriteAlpha = gl3ShaderInfo_t() # for sprites with alpha-testing

		self.si3Dalias = gl3ShaderInfo_t() # for models
		self.si3DaliasColor = gl3ShaderInfo_t() # for models w/ flat colors

		# NOTE: make sure siParticle is always the last shaderInfo
		self.siParticle = gl3ShaderInfo_t() # for particles. surprising, right?

		self.vao3D = 0 #GLuint, for brushes etc, using 10 floats and one uint as vertex input
		self.vbo3D = 0 #GLuint
		self.ebo3D = 0 #GLuint
		self.vaoAlias = 0 #GLuint, for models, using 9 floats as (x,y,z, s,t, r,g,b,a)
		self.vboAlias = 0 #GLuint
		self.eboAlias = 0 #GLuint
		self.vaoParticle = 0 #GLuint, for particles, using 9 floats (x,y,z, size,distance, r,g,b,a)
		self.vboParticle = 0 #GLuint

		# UBOs and their data
		self.uniCommonData = np.zeros(8, dtype=np.float32) #gl3UniCommon_t
		self.uni2DData = np.zeros(16, dtype=np.float32) #gl3Uni2D_t
		self.uni3DData = np.zeros(40, dtype=np.float32) #gl3Uni3D_t
		self.uniLightsData = np.zeros(260, dtype=np.float32) #gl3UniLights_t
		self.uniCommonUBO = 0 #GLuint
		self.uni2DUBO = 0 #GLuint
		self.uni3DUBO = 0 #GLuint
		self.uniLightsUBO = 0 #GLuint

		self.projMat3D = hmm.HMM_Mat4d (1.0) #hmm_mat4
		self.viewMat3D = hmm.HMM_Mat4d (1.0) #hmm_mat4

# _gl3_numShaders: siParticle .. si2D inclusive (si2D must be first, siParticle last)
_gl3_numShaders = 15

# drawcommands using gl3_3D_vtx_t, for batching
class gl3drawCmd_t(object):

	def __init__(self):
		# create an "empty" gl3drawCmd_t with sane defaults (GL3_CreateDrawCmd)
		self.texnum = 0 #GLuint
		self.lmtexnum = -1 #signed char
		self.shaderIdx = -1 #signed char
		self.transModelMatIdx = 0 #unsigned short, index into gl3_main.c transModelMats; 0 always is identity
		self.scroll = 0.0 #float, for gl3state.uni3DData.scroll
		self.lightScaleForTurb = 0.0 #float
		self.alpha = 1.0 #float, either part of color or for gl3state.uni3DData.alpha
		self.color = [0, 0, 0] #byte [3], for uniCommonData.color; its alpha chan is in .alpha
		self.flags = 0 #byte, gl3drawCmd_Flags
		self.styles = [255] * files_h.MAXLIGHTMAPS #byte, indexes into r_newrefdef.lightstyles[]; 255 means "ignore"
		# the following are set in GL3_BufferAndDraw3D()
		self.idxBufOffset = 0 #int
		self.numElements = 0 #int, in index buffer

# for gl3drawCmd_t::flags
DCFlag_DisableDepthMask = 1 # glDepthMask() - GL_FALSE if bit is set
DCFlag_Blend = 2 # GL_BLEND (glEnable/glDisable)
DCFlag_PolyOffsetFill = 4 # GL_POLYGON_OFFSET_FILL (glEnable/glDisable) - for gl_zfix
DCFlag_UseColor = 8
DCFlag_UseScroll = 16
DCFlag_UseLmStyles = 32
DCFlag_UseLightScaleForTurb = 64

gl3_identityMat4 = hmm.HMM_Mat4d (1.0) #const hmm_mat4

MAX_GL3TEXTURES = 1024

# NOTE: struct image_s* is what re.RegisterSkin() etc return so no gl3image_s!
class gl3image_t(object):

	def __init__(self):
		self.name = "" #char [MAX_QPATH], game path, including extension
		self.type = 0 #imagetype_t
		self.width = 0 #int, source image
		self.height = 0 #int
		self.registration_sequence = 0 #int, 0 = free
		self.texturechain = None #msurface_t, for sort-by-texture world drawing
		self.texnum = 0 #GLuint, gl texture binding
		self.sl = 0.0 #float, 0,0 - 1,1 unless part of the scrap
		self.tl = 0.0
		self.sh = 0.0
		self.th = 0.0
		self.scrap = False #qboolean
		self.has_alpha = False #qboolean
		self.is_lava = False #qboolean, DG: added for lava brightness hack

class gl3lightmapstate_t(object):

	def __init__(self):
		self.current_lightmap_texture = 0 #int, index into gl3state.lightmap_textureIDs[]
		self.allocated = [0] * BLOCK_WIDTH #int
		# byte lightmap_buffers[MAX_LIGHTMAPS_PER_SURFACE][4 * BLOCK_WIDTH * BLOCK_HEIGHT]
		# the lightmap texture data needs to be kept in main memory so texsubimage can update properly
		self.lightmap_buffers = [bytearray(4 * BLOCK_WIDTH * BLOCK_HEIGHT) for _ in range(MAX_LIGHTMAPS_PER_SURFACE)]

# ---- inline helpers (from local.h) ----
# Q2PORT: these reference gl3state, which is defined by the gl3_main module.
# To avoid a circular import at module load, look it up at call time.

def GL3_UseProgram (shaderProgram): #GLuint

	from client.refresh.gl3 import gl3_main
	if shaderProgram != gl3_main.gl3state.currentShaderProgram:
		gl3_main.gl3state.currentShaderProgram = shaderProgram
		GL.glUseProgram (shaderProgram)

def GL3_BindVAO (vao): #GLuint

	from client.refresh.gl3 import gl3_main
	if vao != gl3_main.gl3state.currentVAO:
		gl3_main.gl3state.currentVAO = vao
		GL.glBindVertexArray (vao)

def GL3_BindVBO (vbo): #GLuint

	from client.refresh.gl3 import gl3_main
	if vbo != gl3_main.gl3state.currentVBO:
		gl3_main.gl3state.currentVBO = vbo
		GL.glBindBuffer (GL.GL_ARRAY_BUFFER, vbo)

def GL3_BindEBO (ebo): #GLuint

	from client.refresh.gl3 import gl3_main
	if ebo != gl3_main.gl3state.currentEBO:
		gl3_main.gl3state.currentEBO = ebo
		GL.glBindBuffer (GL.GL_ELEMENT_ARRAY_BUFFER, ebo)

def GL3_SelectTMU (tmu): #GLenum

	from client.refresh.gl3 import gl3_main
	if gl3_main.gl3state.currenttmu != tmu:
		GL.glActiveTexture (tmu)
		gl3_main.gl3state.currenttmu = tmu
