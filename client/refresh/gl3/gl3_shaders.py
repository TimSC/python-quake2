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
 * Shaders for the OpenGL3 refresher.
 *
 * =======================================================================
"""

from __future__ import annotations

import ctypes

from OpenGL import GL
def _ri (): #refimport_t (lazy, avoids circular import at module load)

	from client.refresh.gl3 import gl3_main
	return gl3_main.ri


def _shared ():

	from common.header import shared
	return shared


def _gl3main (): #gl3_main module (lazy, avoids circular import at module load)

	from client.refresh.gl3 import gl3_main
	return gl3_main


def _gl3state (): #gl3state_t (from gl3_main)

	return _gl3main ().gl3state
from client.refresh.gl3.header import local
from client.refresh.gl3.header import hmm
from client.refresh.gl3 import gl3_draw
from common import cvar

# cvars
gl_msaa_samples = None #cvar_t *
gl3_colorlight = None #cvar_t *
gl3_particle_square = None #cvar_t *
gl3_overbrightbits = None #cvar_t *
gl3_particle_fade_factor = None #cvar_t *
gl3_intensity = None #cvar_t *
gl3_intensity_2D = None #cvar_t *
vid_gamma = None #cvar_t *

# UBO binding points (enum)
GL3_BINDINGPOINT_UNICOMMON = 0
GL3_BINDINGPOINT_UNI2D = 1
GL3_BINDINGPOINT_UNI3D = 2
GL3_BINDINGPOINT_UNILIGHTS = 3


# ############## GLSL shader sources (extracted from the C MULTILINE_STRING) #####################

vertexSrc2D = """
		in vec2 position; // GL3_ATTRIB_POSITION
		in vec2 texCoord; // GL3_ATTRIB_TEXCOORD

		// for UBO shared between 2D shaders
		layout (std140) uniform uni2D
		{
			mat4 trans;
		};

		out vec2 passTexCoord;

		void main()
		{
			gl_Position = trans * vec4(position, 0.0, 1.0);
			passTexCoord = texCoord;
		}
"""

fragmentSrc2D = """
		in vec2 passTexCoord;

		// for UBO shared between all shaders (incl. 2D)
		layout (std140) uniform uniCommon
		{
			float gamma;
			float intensity;
			float intensity2D; // for HUD, menu etc

			vec4 color;
		};

		uniform sampler2D tex;

		out vec4 outColor;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);
			// the gl1 renderer used glAlphaFunc(GL_GREATER, 0.666);
			// and glEnable(GL_ALPHA_TEST); for 2D rendering
			// this should do the same
			if(texel.a <= 0.666)
				discard;

			// apply gamma correction and intensity
			texel.rgb *= intensity2D;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc2Dtinted = """
		in vec2 passTexCoord;

		// for UBO shared between all shaders (incl. 2D)
		layout (std140) uniform uniCommon
		{
			float gamma;
			float intensity;
			float intensity2D; // for HUD, menu etc

			vec4 color;
		};

		uniform sampler2D tex;

		out vec4 outColor;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			if(texel.a <= 0.666)
				discard;

			// apply color tint
			texel.rgb *= color.rgb;

			// apply gamma correction and intensity
			texel.rgb *= intensity2D;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a;
		}
"""

fragmentSrc2Dpostprocess = """
		in vec2 passTexCoord;

		uniform sampler2D tex;
		uniform vec4 v_blend;

		out vec4 outColor;

		void main()
		{
			// no gamma or intensity here, it has been applied before
			// (this is just for postprocessing)
			vec4 res = texture(tex, passTexCoord);
			// apply the v_blend, usually blended as a colored quad with:
			// glBlendEquation(GL_FUNC_ADD); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
			res.rgb = v_blend.a * v_blend.rgb + (1.0 - v_blend.a)*res.rgb;
			outColor =  res;
		}
"""

fragmentSrc2DpostprocessWater = """
		in vec2 passTexCoord;

		const float PI = 3.14159265358979323846;

		uniform sampler2D tex;

		uniform float time;
		uniform vec4 v_blend;

		out vec4 outColor;

		void main()
		{
			vec2 uv = passTexCoord;

			// warping based on vkquake2
			// here uv is always between 0 and 1 so ignore all that scrWidth and gl_FragCoord stuff
			//float sx = pc.scale - abs(pc.scrWidth  / 2.0 - gl_FragCoord.x) * 2.0 / pc.scrWidth;
			//float sy = pc.scale - abs(pc.scrHeight / 2.0 - gl_FragCoord.y) * 2.0 / pc.scrHeight;
			float sx = 1.0 - abs(0.5-uv.x)*2.0;
			float sy = 1.0 - abs(0.5-uv.y)*2.0;
			float xShift = 2.0 * time + uv.y * PI * 10.0;
			float yShift = 2.0 * time + uv.x * PI * 10.0;
			vec2 distortion = vec2(sin(xShift) * sx, sin(yShift) * sy) * 0.00666;

			uv += distortion;
			uv = clamp(uv, vec2(0.0, 0.0), vec2(1.0, 1.0));

			// no gamma or intensity here, it has been applied before
			// (this is just for postprocessing)
			vec4 res = texture(tex, uv);
			// apply the v_blend, usually blended as a colored quad with:
			// glBlendEquation(GL_FUNC_ADD); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
			res.rgb = v_blend.a * v_blend.rgb + (1.0 - v_blend.a)*res.rgb;
			outColor =  res;
		}
"""

vertexSrc2Dcolor = """
		in vec2 position; // GL3_ATTRIB_POSITION

		// for UBO shared between 2D shaders
		layout (std140) uniform uni2D
		{
			mat4 trans;
		};

		void main()
		{
			gl_Position = trans * vec4(position, 0.0, 1.0);
		}
"""

fragmentSrc2Dcolor = """
		// for UBO shared between all shaders (incl. 2D)
		layout (std140) uniform uniCommon
		{
			float gamma;
			float intensity;
			float intensity2D; // for HUD, menus etc

			vec4 color;
		};

		out vec4 outColor;

		void main()
		{
			vec3 col = color.rgb * intensity2D;
			outColor.rgb = pow(col, vec3(gamma));
			outColor.a = color.a;
		}
"""

vertexCommon3D = """
		in vec3 position;   // GL3_ATTRIB_POSITION
		in vec2 texCoord;   // GL3_ATTRIB_TEXCOORD
		in vec2 lmTexCoord; // GL3_ATTRIB_LMTEXCOORD
		in vec4 vertColor;  // GL3_ATTRIB_COLOR
		in vec3 normal;     // GL3_ATTRIB_NORMAL
		in uint lightFlags; // GL3_ATTRIB_LIGHTFLAGS

		out vec2 passTexCoord;

		// for UBO shared between all 3D shaders
		layout (std140) uniform uni3D
		{
			mat4 transProjView;
			mat4 transModel;

			float scroll; // for SURF_FLOWING
			float time;
			float alpha;
			float overbrightbits;
			float particleFadeFactor;
			float lightScaleForTurb; // surfaces with SURF_DRAWTURB (water, lava) don't have lightmaps, use this instead
			float _pad_1; // AMDs legacy windows driver needs this, otherwise uni3D has wrong size
			float _pad_2;
		};
"""

fragmentCommon3D = """
		in vec2 passTexCoord;

		out vec4 outColor;

		// for UBO shared between all shaders (incl. 2D)
		layout (std140) uniform uniCommon
		{
			float gamma; // this is 1.0/vid_gamma
			float intensity;
			float intensity2D; // for HUD, menus etc

			vec4 color; // really?
		};
		// for UBO shared between all 3D shaders
		layout (std140) uniform uni3D
		{
			mat4 transProjView;
			mat4 transModel;

			float scroll; // for SURF_FLOWING
			float time;
			float alpha;
			float overbrightbits;
			float particleFadeFactor;
			float lightScaleForTurb; // surfaces with SURF_DRAWTURB (water, lava) don't have lightmaps, use this instead
			float _pad_1; // AMDs legacy windows driver needs this, otherwise uni3D has wrong size
			float _pad_2;
		};
"""

vertexSrc3D = """
		// it gets attributes and uniforms from vertexCommon3D

		void main()
		{
			passTexCoord = texCoord;
			gl_Position = transProjView * transModel * vec4(position, 1.0);
		}
"""

vertexSrc3Dflow = """
		// it gets attributes and uniforms from vertexCommon3D

		void main()
		{
			passTexCoord = texCoord + vec2(scroll, 0.0);
			gl_Position = transProjView * transModel * vec4(position, 1.0);
		}
"""

vertexSrc3Dlm = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec2 passLMcoord;
		out vec3 passWorldCoord;
		out vec3 passNormal;
		flat out uint passLightFlags;

		void main()
		{
			passTexCoord = texCoord;
			passLMcoord = lmTexCoord;
			vec4 worldCoord = transModel * vec4(position, 1.0);
			passWorldCoord = worldCoord.xyz;
			vec4 worldNormal = transModel * vec4(normal, 0.0f);
			passNormal = normalize(worldNormal.xyz);
			passLightFlags = lightFlags;

			gl_Position = transProjView * worldCoord;
		}
"""

vertexSrc3DlmFlow = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec2 passLMcoord;
		out vec3 passWorldCoord;
		out vec3 passNormal;
		flat out uint passLightFlags;

		void main()
		{
			passTexCoord = texCoord + vec2(scroll, 0.0);
			passLMcoord = lmTexCoord;
			vec4 worldCoord = transModel * vec4(position, 1.0);
			passWorldCoord = worldCoord.xyz;
			vec4 worldNormal = transModel * vec4(normal, 0.0f);
			passNormal = normalize(worldNormal.xyz);
			passLightFlags = lightFlags;

			gl_Position = transProjView * worldCoord;
		}
"""

fragmentSrc3D = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply intensity and gamma
			texel.rgb *= intensity;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dwater = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec2 tc = passTexCoord;
			tc.s += sin( passTexCoord.t*0.125 + time ) * 4.0;
			tc.s += scroll;
			tc.t += sin( passTexCoord.s*0.125 + time ) * 4.0;
			tc *= 1.0/64.0; // do this last

			vec4 texel = texture(tex, tc);

			// apply intensity and gamma
			texel.rgb *= intensity * lightScaleForTurb;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dlm = """
		// it gets attributes and uniforms from fragmentCommon3D

		struct DynLight { // gl3UniDynLight in C
			vec3 lightOrigin;
			float _pad;
			//vec3 lightColor;
			//float lightIntensity;
			vec4 lightColor; // .a is intensity; this way it also works on OSX...
			// (otherwise lightIntensity always contained 1 there)
		};

		layout (std140) uniform uniLights
		{
			DynLight dynLights[32];
			uint numDynLights;
			uint _pad1; uint _pad2; uint _pad3; // FFS, AMD!
		};

		uniform sampler2D tex;

		uniform sampler2D lightmap0;
		uniform sampler2D lightmap1;
		uniform sampler2D lightmap2;
		uniform sampler2D lightmap3;

		uniform vec4 lmScales[4];

		in vec2 passLMcoord;
		in vec3 passWorldCoord;
		in vec3 passNormal;
		flat in uint passLightFlags;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply intensity
			texel.rgb *= intensity;

			// apply lightmap
			vec4 lmTex = texture(lightmap0, passLMcoord) * lmScales[0];
			lmTex     += texture(lightmap1, passLMcoord) * lmScales[1];
			lmTex     += texture(lightmap2, passLMcoord) * lmScales[2];
			lmTex     += texture(lightmap3, passLMcoord) * lmScales[3];

			if(passLightFlags != 0u)
			{
				// TODO: or is hardcoding 32 better?
				for(uint i=0u; i<numDynLights; ++i)
				{
					// I made the following up, it's probably not too cool..
					// it basically checks if the light is on the right side of the surface
					// and, if it is, sets intensity according to distance between light and pixel on surface

					// dyn light number i does not affect this plane, just skip it
					if((passLightFlags & (1u << i)) == 0u)  continue;

					float intens = dynLights[i].lightColor.a;

					vec3 lightToPos = dynLights[i].lightOrigin - passWorldCoord;
					float distLightToPos = length(lightToPos);
					float fact = max(0.0, intens - distLightToPos - 52.0);

					// move the light source a bit further above the surface
					// => helps if the lightsource is so close to the surface (e.g. grenades, rockets)
					//    that the dot product below would return 0
					// (light sources that are below the surface are filtered out by lightFlags)
					lightToPos += passNormal*32.0;

					// also factor in angle between light and point on surface
					fact *= max(0.0, dot(passNormal, normalize(lightToPos)));


					lmTex.rgb += dynLights[i].lightColor.rgb * fact * (1.0/256.0);
				}
			}

			lmTex.rgb *= overbrightbits;
			outColor = lmTex*texel;
			outColor.rgb = pow(outColor.rgb, vec3(gamma)); // apply gamma correction to result

			outColor.a = 1.0; // lightmaps aren't used with translucent surfaces
		}
"""

fragmentSrc3DlmNoColor = """
		// it gets attributes and uniforms from fragmentCommon3D

		struct DynLight { // gl3UniDynLight in C
			vec3 lightOrigin;
			float _pad;
			//vec3 lightColor;
			//float lightIntensity;
			vec4 lightColor; // .a is intensity; this way it also works on OSX...
			// (otherwise lightIntensity always contained 1 there)
		};

		layout (std140) uniform uniLights
		{
			DynLight dynLights[32];
			uint numDynLights;
			uint _pad1; uint _pad2; uint _pad3; // FFS, AMD!
		};

		uniform sampler2D tex;

		uniform sampler2D lightmap0;
		uniform sampler2D lightmap1;
		uniform sampler2D lightmap2;
		uniform sampler2D lightmap3;

		uniform vec4 lmScales[4];

		in vec2 passLMcoord;
		in vec3 passWorldCoord;
		in vec3 passNormal;
		flat in uint passLightFlags;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply intensity
			texel.rgb *= intensity;

			// apply lightmap
			vec4 lmTex = texture(lightmap0, passLMcoord) * lmScales[0];
			lmTex     += texture(lightmap1, passLMcoord) * lmScales[1];
			lmTex     += texture(lightmap2, passLMcoord) * lmScales[2];
			lmTex     += texture(lightmap3, passLMcoord) * lmScales[3];

			if(passLightFlags != 0u)
			{
				// TODO: or is hardcoding 32 better?
				for(uint i=0u; i<numDynLights; ++i)
				{
					// I made the following up, it's probably not too cool..
					// it basically checks if the light is on the right side of the surface
					// and, if it is, sets intensity according to distance between light and pixel on surface

					// dyn light number i does not affect this plane, just skip it
					if((passLightFlags & (1u << i)) == 0u)  continue;

					float intens = dynLights[i].lightColor.a;

					vec3 lightToPos = dynLights[i].lightOrigin - passWorldCoord;
					float distLightToPos = length(lightToPos);
					float fact = max(0.0, intens - distLightToPos - 52.0);

					// move the light source a bit further above the surface
					// => helps if the lightsource is so close to the surface (e.g. grenades, rockets)
					//    that the dot product below would return 0
					// (light sources that are below the surface are filtered out by lightFlags)
					lightToPos += passNormal*32.0;

					// also factor in angle between light and point on surface
					fact *= max(0.0, dot(passNormal, normalize(lightToPos)));


					lmTex.rgb += dynLights[i].lightColor.rgb * fact * (1.0/256.0);
				}
			}

			// turn lightcolor into grey for gl3_colorlight 0
			lmTex.rgb = vec3(0.333 * (lmTex.r+lmTex.g+lmTex.b));

			lmTex.rgb *= overbrightbits;
			outColor = lmTex*texel;
			outColor.rgb = pow(outColor.rgb, vec3(gamma)); // apply gamma correction to result

			outColor.a = 1; // lightmaps aren't used with translucent surfaces
		}
"""

fragmentSrc3Dcolor = """
		// it gets attributes and uniforms from fragmentCommon3D

		void main()
		{
			vec4 texel = color;

			// apply gamma correction and intensity
			// texel.rgb *= intensity; TODO: use intensity here? (this is used for beams)
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dsky = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// TODO: something about GL_BLEND vs GL_ALPHATEST etc

			// apply gamma correction
			// texel.rgb *= intensity; // TODO: really no intensity for sky?
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dsprite = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply gamma correction and intensity
			texel.rgb *= intensity;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3DspriteAlpha = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			if(texel.a <= 0.666)
				discard;

			// apply gamma correction and intensity
			texel.rgb *= intensity;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			//outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
			outColor.a = texel.a; // I think in this case alpha from uni3d shouldn't be used
		}
"""

vertexSrc3Dwater = """
		// it gets attributes and uniforms from vertexCommon3D
		void main()
		{
			passTexCoord = texCoord;

			gl_Position = transProjView * transModel * vec4(position, 1.0);
		}
"""

vertexSrcAlias = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec4 passColor;

		void main()
		{
			passColor = vertColor*overbrightbits;
			passTexCoord = texCoord;
			gl_Position = transProjView* transModel * vec4(position, 1.0);
		}
"""

fragmentSrcAlias = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		in vec4 passColor;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply gamma correction and intensity
			texel.rgb *= intensity;
			texel.a *= alpha; // is alpha even used here?
			texel *= min(vec4(1.5), passColor);

			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrcAliasColor = """
		// it gets attributes and uniforms from fragmentCommon3D

		in vec4 passColor;

		void main()
		{
			vec4 texel = passColor;

			// apply gamma correction and intensity
			// texel.rgb *= intensity; // TODO: color-only rendering probably shouldn't use intensity?
			texel.a *= alpha; // is alpha even used here?
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

vertexSrcParticles = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec4 passColor;

		void main()
		{
			passColor = vertColor;
			gl_Position = transProjView * transModel * vec4(position, 1.0);

			// abusing texCoord for pointSize, pointDist for particles
			float pointDist = texCoord.y*0.1; // with factor 0.1 it looks good.

			gl_PointSize = texCoord.x/pointDist;
		}
"""

fragmentSrcParticles = """
		// it gets attributes and uniforms from fragmentCommon3D

		in vec4 passColor;

		void main()
		{
			vec2 offsetFromCenter = 2.0*(gl_PointCoord - vec2(0.5, 0.5)); // normalize so offset is between 0 and 1 instead 0 and 0.5
			float distSquared = dot(offsetFromCenter, offsetFromCenter);
			if(distSquared > 1.0) // this makes sure the particle is round
				discard;

			vec4 texel = passColor;

			// apply gamma correction and intensity
			//texel.rgb *= intensity; TODO: intensity? Probably not?
			outColor.rgb = pow(texel.rgb, vec3(gamma));

			// I want the particles to fade out towards the edge, the following seems to look nice
			texel.a *= min(1.0, particleFadeFactor*(1.0 - distSquared));

			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrcParticlesSquare = """
		// it gets attributes and uniforms from fragmentCommon3D

		in vec4 passColor;

		void main()
		{
			// outColor = passColor;
			// so far we didn't use gamma correction for square particles, but this way
			// uniCommon is referenced so hopefully Intels Ivy Bridge HD4000 GPU driver
			// for Windows stops shitting itself (see https://github.com/yquake2/yquake2/issues/391)
			outColor.rgb = pow(passColor.rgb, vec3(gamma));
			outColor.a = passColor.a;
		}
"""




# ############## shader compile / link / init #####################


def CompileShader (shaderType, shaderSrc, shaderSrc2): #GLenum, const char *, const char * (returns GLuint)

	shader = GL.glCreateShader (shaderType)

	# desktop GL
	version = "#version 150\n"

	sources = [version, shaderSrc]
	if shaderSrc2 is not None:
		sources.append (shaderSrc2)

	GL.glShaderSource (shader, sources) # Q2PORT: PyOpenGL takes the string list, not a count + array
	GL.glCompileShader (shader)

	_s = GL.glGetShaderiv (shader, GL.GL_COMPILE_STATUS)
	status = _s [0] if isinstance (_s, (list, tuple)) else _s # Q2PORT: PyOpenGL returns a list or a scalar
	if status != GL.GL_TRUE:
		shaderTypeStr = "Vertex" if shaderType == GL.GL_VERTEX_SHADER else "Fragment"
		_ri ().Sys_Error (_shared ().ERR_FATAL, "ERROR: Compiling {} Shader failed: {}\n".format (shaderTypeStr, GL.glGetShaderInfoLog (shader))) # Q2PORT: PyOpenGL returns the log string

	return shader


def CreateShaderProgram (numShaders, shaders): #int, GLuint * (returns GLuint)

	shaderProgram = GL.glCreateProgram ()
	if shaderProgram == 0:
		_ri ().Sys_Error (_shared ().ERR_FATAL, "ERROR: Couldn't create a new Shader Program!\n")

	for i in range(numShaders):
		GL.glAttachShader (shaderProgram, shaders[i])

	# make sure all shaders use the same attribute locations for common attributes
	# (so the same VAO can easily be used with different shaders)
	GL.glBindAttribLocation (shaderProgram, local.GL3_ATTRIB_POSITION, b"position")
	GL.glBindAttribLocation (shaderProgram, local.GL3_ATTRIB_TEXCOORD, b"texCoord")
	GL.glBindAttribLocation (shaderProgram, local.GL3_ATTRIB_LMTEXCOORD, b"lmTexCoord")
	GL.glBindAttribLocation (shaderProgram, local.GL3_ATTRIB_COLOR, b"vertColor")
	GL.glBindAttribLocation (shaderProgram, local.GL3_ATTRIB_NORMAL, b"normal")
	GL.glBindAttribLocation (shaderProgram, local.GL3_ATTRIB_LIGHTFLAGS, b"lightFlags")

	GL.glLinkProgram (shaderProgram)

	_s = GL.glGetProgramiv (shaderProgram, GL.GL_LINK_STATUS)
	status = _s [0] if isinstance (_s, (list, tuple)) else _s # Q2PORT: PyOpenGL returns a list or a scalar
	if status != GL.GL_TRUE:
		_ri ().Sys_Error (_shared ().ERR_FATAL, "ERROR: Linking shader program failed: {}\n".format (GL.glGetProgramInfoLog (shaderProgram))) # Q2PORT: PyOpenGL returns the log string

	for i in range(numShaders):
		# after linking, they don't need to be attached anymore
		GL.glDetachShader (shaderProgram, shaders[i])

	return shaderProgram


def initShader2D (shaderInfo, vertSrc, fragSrc, uniCommonRequired): #gl3ShaderInfo_t *, const char *, const char *, qboolean (returns qboolean)

	shaders2D = [0, 0]
	prog = 0

	if shaderInfo.shaderProgram != 0:
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: calling initShader2D for gl3ShaderInfo_t that already has a shaderProgram!\n")
		GL.glDeleteProgram (shaderInfo.shaderProgram)

	shaderInfo.shaderProgram = 0
	shaderInfo.uniLmScalesOrTime = -1
	shaderInfo.uniVblend = -1

	shaders2D[0] = CompileShader (GL.GL_VERTEX_SHADER, vertSrc, None)
	if shaders2D[0] == 0:
		return False

	shaders2D[1] = CompileShader (GL.GL_FRAGMENT_SHADER, fragSrc, None)
	if shaders2D[1] == 0:
		GL.glDeleteShader (shaders2D[0])
		return False

	prog = CreateShaderProgram (2, shaders2D)

	if prog == 0:
		return False

	shaderInfo.shaderProgram = prog
	local.GL3_UseProgram (prog)

	# bind the buffer objects to the uniform blocks
	blockIndex = GL.GL_INVALID_INDEX
	if uniCommonRequired:
		blockIndex = GL.glGetUniformBlockIndex (prog, b"uniCommon")

	if blockIndex != GL.GL_INVALID_INDEX:
		_ub = (ctypes.c_int * 1) () # Q2PORT: PyOpenGL needs a ctypes buffer, not a list
		GL.glGetActiveUniformBlockiv (prog, blockIndex, GL.GL_UNIFORM_BLOCK_DATA_SIZE, _ub) # Q2PORT: PyOpenGL writes into a buffer list
		blockSize = _ub [0]
		if blockSize != 8 * 4: # sizeof(gl3state.uniCommonData)
			_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: OpenGL driver disagrees with us about UBO size of 'uniCommon'\n")
			return False
		GL.glUniformBlockBinding (prog, blockIndex, GL3_BINDINGPOINT_UNICOMMON)
	elif uniCommonRequired:
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Couldn't find uniform block index 'uniCommon'\n")
		return False

	blockIndex = GL.glGetUniformBlockIndex (prog, b"uni2D")
	if blockIndex != GL.GL_INVALID_INDEX:
		_ub = (ctypes.c_int * 1) () # Q2PORT: PyOpenGL needs a ctypes buffer, not a list
		GL.glGetActiveUniformBlockiv (prog, blockIndex, GL.GL_UNIFORM_BLOCK_DATA_SIZE, _ub) # Q2PORT: PyOpenGL writes into a buffer list
		blockSize = _ub [0]
		if blockSize != 16 * 4: # sizeof(gl3state.uni2DData)
			_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: OpenGL driver disagrees with us about UBO size of 'uni2D'\n")
			return False
		GL.glUniformBlockBinding (prog, blockIndex, GL3_BINDINGPOINT_UNI2D)
	else:
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Couldn't find uniform block index 'uni2D'\n")
		return False

	shaderInfo.uniLmScalesOrTime = GL.glGetUniformLocation (prog, b"time")
	if shaderInfo.uniLmScalesOrTime != -1:
		GL.glUniform1f (shaderInfo.uniLmScalesOrTime, 0.0)

	shaderInfo.uniVblend = GL.glGetUniformLocation (prog, b"v_blend")
	if shaderInfo.uniVblend != -1:
		GL.glUniform4f (shaderInfo.uniVblend, 0, 0, 0, 0)

	return True


def initShader3D (shaderInfo, vertSrc, fragSrc): #gl3ShaderInfo_t *, const char *, const char * (returns qboolean)

	shaders3D = [0, 0]
	prog = 0
	i = 0

	if shaderInfo.shaderProgram != 0:
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: calling initShader3D for gl3ShaderInfo_t that already has a shaderProgram!\n")
		GL.glDeleteProgram (shaderInfo.shaderProgram)

	shaderInfo.shaderProgram = 0
	shaderInfo.uniLmScalesOrTime = -1
	shaderInfo.uniVblend = -1

	shaders3D[0] = CompileShader (GL.GL_VERTEX_SHADER, vertexCommon3D, vertSrc)
	if shaders3D[0] == 0:
		return False

	shaders3D[1] = CompileShader (GL.GL_FRAGMENT_SHADER, fragmentCommon3D, fragSrc)
	if shaders3D[1] == 0:
		GL.glDeleteShader (shaders3D[0])
		return False

	prog = CreateShaderProgram (2, shaders3D)

	if prog == 0:
		return False

	local.GL3_UseProgram (prog)

	blockIndex = GL.glGetUniformBlockIndex (prog, b"uniCommon")
	if blockIndex != GL.GL_INVALID_INDEX:
		_ub = (ctypes.c_int * 1) () # Q2PORT: PyOpenGL needs a ctypes buffer, not a list
		GL.glGetActiveUniformBlockiv (prog, blockIndex, GL.GL_UNIFORM_BLOCK_DATA_SIZE, _ub) # Q2PORT: PyOpenGL writes into a buffer list
		blockSize = _ub [0]
		if blockSize != 8 * 4:
			_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: OpenGL driver disagrees with us about UBO size of 'uniCommon'\n")
			return False
		GL.glUniformBlockBinding (prog, blockIndex, GL3_BINDINGPOINT_UNICOMMON)
	else:
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Couldn't find uniform block index 'uniCommon'\n")
		return False

	blockIndex = GL.glGetUniformBlockIndex (prog, b"uni3D")
	if blockIndex != GL.GL_INVALID_INDEX:
		_ub = (ctypes.c_int * 1) () # Q2PORT: PyOpenGL needs a ctypes buffer, not a list
		GL.glGetActiveUniformBlockiv (prog, blockIndex, GL.GL_UNIFORM_BLOCK_DATA_SIZE, _ub) # Q2PORT: PyOpenGL writes into a buffer list
		blockSize = _ub [0]
		if blockSize != 40 * 4:
			_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: OpenGL driver disagrees with us about UBO size of 'uni3D'\n")
			_ri ().Con_Printf (_shared ().PRINT_ALL, "         driver says {}, we expect {}\n".format (blockSize, 40 * 4))
			return False
		GL.glUniformBlockBinding (prog, blockIndex, GL3_BINDINGPOINT_UNI3D)
	else:
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Couldn't find uniform block index 'uni3D'\n")
		return False

	blockIndex = GL.glGetUniformBlockIndex (prog, b"uniLights")
	if blockIndex != GL.GL_INVALID_INDEX:
		_ub = (ctypes.c_int * 1) () # Q2PORT: PyOpenGL needs a ctypes buffer, not a list
		GL.glGetActiveUniformBlockiv (prog, blockIndex, GL.GL_UNIFORM_BLOCK_DATA_SIZE, _ub) # Q2PORT: PyOpenGL writes into a buffer list
		blockSize = _ub [0]
		if blockSize != 260 * 4:
			_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: OpenGL driver disagrees with us about UBO size of 'uniLights'\n")
			_ri ().Con_Printf (_shared ().PRINT_ALL, "         OpenGL says {}, we say {}\n".format (blockSize, 260 * 4))
			return False
		GL.glUniformBlockBinding (prog, blockIndex, GL3_BINDINGPOINT_UNILIGHTS)
	# else: as uniLights is only used in the LM shaders, it's ok if it's missing

	# make sure texture is GL_TEXTURE0
	texLoc = GL.glGetUniformLocation (prog, b"tex")
	if texLoc != -1:
		GL.glUniform1i (texLoc, 0)

	# ..  and the 4 lightmap textures use GL_TEXTURE1..4
	for i in range(4):
		lmName = "lightmap{}".format (i)
		lmLoc = GL.glGetUniformLocation (prog, lmName.encode ())
		if lmLoc != -1:
			GL.glUniform1i (lmLoc, i + 1) # lightmap0 belongs to GL_TEXTURE1, lightmap1 to GL_TEXTURE2 etc

	lmScalesLoc = GL.glGetUniformLocation (prog, b"lmScales")
	if lmScalesLoc != -1:
		shaderInfo.lmScales[0] = hmm.HMM_Vec4 (1.0, 1.0, 1.0, 1.0)
		for i in range(1, 4):
			shaderInfo.lmScales[i] = hmm.HMM_Vec4 (0.0, 0.0, 0.0, 0.0)
		GL.glUniform4fv (lmScalesLoc, 4, shaderInfo.lmScales.reshape (16))

	shaderInfo.shaderProgram = prog

	# I think the shaders aren't needed anymore once they're linked into the program
	GL.glDeleteShader (shaders3D[0])
	GL.glDeleteShader (shaders3D[1])

	return True


def initUBOs (): #void

	gl3_main = None
	from client.refresh.gl3 import gl3_main as _gl3_main
	gl3state = _gl3_main.gl3state

	gl3state.uniCommonData[local.UNICOMMON_GAMMA] = 1.0 / _gl3main ().vid_gamma.value
	gl3state.uniCommonData[local.UNICOMMON_INTENSITY] = _gl3main ().gl3_intensity.value
	gl3state.uniCommonData[local.UNICOMMON_INTENSITY2D] = _gl3main ().gl3_intensity_2D.value
	gl3state.uniCommonData[4:8] = [1, 1, 1, 1] # color

	# the matrix will be set to something more useful later, before being used
	gl3state.uni2DData[local.UNI2D_TRANS:local.UNI2D_TRANS + 16] = hmm.HMM_Mat4 ().flatten (order="F")

	# the matrices will be set to something more useful later, before being used
	gl3state.uni3DData[local.UNI3D_PROJVIEW:local.UNI3D_PROJVIEW + 16] = hmm.HMM_Mat4 ().flatten (order="F")
	gl3state.uni3DData[local.UNI3D_MODEL:local.UNI3D_MODEL + 16] = local.gl3_identityMat4.flatten (order="F")
	gl3state.uni3DData[local.UNI3D_SCROLL] = 0.0
	gl3state.uni3DData[local.UNI3D_TIME] = 0.0
	gl3state.uni3DData[local.UNI3D_ALPHA] = 1.0
	# gl3_overbrightbits 0 means "no scaling" which is equivalent to multiplying with 1
	gl3state.uni3DData[local.UNI3D_OVERBRIGHTBITS] = 1.0 if _gl3main ().gl3_overbrightbits.value <= 0.0 else _gl3main ().gl3_overbrightbits.value
	gl3state.uni3DData[local.UNI3D_PARTICLEFADEFATOR] = _gl3main ().gl3_particle_fade_factor.value
	gl3state.uni3DData[local.UNI3D_LIGHTSCALEFORTURB] = 1.0

	def _gen_ubo(data):
		buf = GL.glGenBuffers (1)
		GL.glBindBuffer (GL.GL_UNIFORM_BUFFER, buf)
		GL.glBufferData (GL.GL_UNIFORM_BUFFER, len(data), data, GL.GL_DYNAMIC_DRAW)
		return buf

	gl3state.uniCommonUBO = _gen_ubo (gl3state.uniCommonData)
	GL.glBindBufferBase (GL.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNICOMMON, gl3state.uniCommonUBO)
	gl3state.uni2DUBO = _gen_ubo (gl3state.uni2DData)
	GL.glBindBufferBase (GL.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNI2D, gl3state.uni2DUBO)
	gl3state.uni3DUBO = _gen_ubo (gl3state.uni3DData)
	GL.glBindBufferBase (GL.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNI3D, gl3state.uni3DUBO)
	gl3state.uniLightsUBO = _gen_ubo (gl3state.uniLightsData)
	GL.glBindBufferBase (GL.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNILIGHTS, gl3state.uniLightsUBO)

	gl3state.currentUBO = gl3state.uniLightsUBO


def createShaders (): #void (returns qboolean)

	if not initShader2D (_gl3state ().si2D, vertexSrc2D, fragmentSrc2D, True):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for textured 2D rendering!\n")
		return False

	if not initShader2D (_gl3state ().si2Dtinted, vertexSrc2D, fragmentSrc2Dtinted, True):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for tinted 2D rendering!\n")
		return False

	if not initShader2D (_gl3state ().si2Dcolor, vertexSrc2Dcolor, fragmentSrc2Dcolor, True):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for color-only 2D rendering!\n")
		return False

	if not initShader2D (_gl3state ().si2DpostProcess, vertexSrc2D, fragmentSrc2Dpostprocess, False):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program to render framebuffer object!\n")
		return False

	if not initShader2D (_gl3state ().si2DpostProcessWater, vertexSrc2D, fragmentSrc2DpostprocessWater, False):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program to render framebuffer object under water!\n")
		return False

	lightmappedFrag = fragmentSrc3DlmNoColor if _gl3main ().gl3_colorlight.value == 0.0 else fragmentSrc3Dlm # Q2PORT: the cvar lives in gl3_main

	if not initShader3D (_gl3state ().si3Dlm, vertexSrc3Dlm, lightmappedFrag):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for textured 3D rendering with lightmap!\n")
		return False
	if not initShader3D (_gl3state ().si3Dtrans, vertexSrc3D, fragmentSrc3D):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for rendering translucent 3D things!\n")
		return False
	if not initShader3D (_gl3state ().si3DcolorOnly, vertexSrc3D, fragmentSrc3Dcolor):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for flat-colored 3D rendering!\n")
		return False
	if not initShader3D (_gl3state ().si3Dturb, vertexSrc3Dwater, fragmentSrc3Dwater):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for water rendering!\n")
		return False
	if not initShader3D (_gl3state ().si3DlmFlow, vertexSrc3DlmFlow, lightmappedFrag):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for scrolling textured 3D rendering with lightmap!\n")
		return False
	if not initShader3D (_gl3state ().si3DtransFlow, vertexSrc3Dflow, fragmentSrc3D):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for scrolling textured translucent 3D rendering!\n")
		return False
	if not initShader3D (_gl3state ().si3Dsky, vertexSrc3D, fragmentSrc3Dsky):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for sky rendering!\n")
		return False
	if not initShader3D (_gl3state ().si3Dsprite, vertexSrc3D, fragmentSrc3Dsprite):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for sprite rendering!\n")
		return False
	if not initShader3D (_gl3state ().si3DspriteAlpha, vertexSrc3D, fragmentSrc3DspriteAlpha):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for alpha-tested sprite rendering!\n")
		return False
	if not initShader3D (_gl3state ().si3Dalias, vertexSrcAlias, fragmentSrcAlias):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for rendering textured models!\n")
		return False
	if not initShader3D (_gl3state ().si3DaliasColor, vertexSrcAlias, fragmentSrcAliasColor):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for rendering flat-colored models!\n")
		return False

	particleFrag = fragmentSrcParticles
	if _gl3main ().gl3_particle_square.value != 0.0: # Q2PORT: the cvar lives in gl3_main
		particleFrag = fragmentSrcParticlesSquare

	if not initShader3D (_gl3state ().siParticle, vertexSrcParticles, particleFrag):
		_ri ().Con_Printf (_shared ().PRINT_ALL, "WARNING: Failed to create shader program for rendering particles!\n")
		return False

	_gl3state ().currentShaderProgram = 0

	return True


def GL3_InitShaders (): #void (returns qboolean)

	initUBOs ()

	return createShaders ()


def deleteShaders (): #void

	for si in [_gl3state ().si2D, _gl3state ().si2Dtinted, _gl3state ().si2Dcolor,
	            _gl3state ().si2DpostProcess, _gl3state ().si2DpostProcessWater,
	            _gl3state ().si3Dlm, _gl3state ().si3Dtrans, _gl3state ().si3DcolorOnly,
	            _gl3state ().si3Dturb, _gl3state ().si3DlmFlow, _gl3state ().si3DtransFlow,
	            _gl3state ().si3Dsky, _gl3state ().si3Dsprite, _gl3state ().si3DspriteAlpha,
	            _gl3state ().si3Dalias, _gl3state ().si3DaliasColor, _gl3state ().siParticle]:
		if si.shaderProgram != 0:
			GL.glDeleteProgram (si.shaderProgram)
		si.shaderProgram = 0
		si.uniVblend = -1
		si.uniLmScalesOrTime = -1


def GL3_ShutdownShaders (): #void

	deleteShaders ()

	# let's (ab)use the fact that all 4 UBO handles are consecutive fields of the gl3state struct
	GL.glDeleteBuffers (4, [_gl3state ().uniCommonUBO, _gl3state ().uni2DUBO, _gl3state ().uni3DUBO, _gl3state ().uniLightsUBO])
	_gl3state ().uniCommonUBO = _gl3state ().uni2DUBO = _gl3state ().uni3DUBO = _gl3state ().uniLightsUBO = 0


def GL3_RecreateShaders (): #void (returns qboolean)

	# delete and recreate the existing shaders (but not the UBOs)
	deleteShaders ()
	return createShaders ()


def updateUBO (ubo, size, data): #GLuint, int, void *

	if _gl3state ().currentUBO != ubo:
		_gl3state ().currentUBO = ubo
		GL.glBindBuffer (GL.GL_UNIFORM_BUFFER, ubo)

	gl3_draw.gl3_numBufferUniforms += 1

	# this seems to be reasonably fast everywhere
	GL.glBufferData (GL.GL_UNIFORM_BUFFER, size, data, GL.GL_DYNAMIC_DRAW)


def GL3_UpdateUBOCommon (): #void

	updateUBO (_gl3state ().uniCommonUBO, len(_gl3state ().uniCommonData) * 4, _gl3state ().uniCommonData)


def GL3_UpdateUBO2D (): #void

	updateUBO (_gl3state ().uni2DUBO, len(_gl3state ().uni2DData) * 4, _gl3state ().uni2DData)


def GL3_UpdateUBO3D (): #void

	updateUBO (_gl3state ().uni3DUBO, len(_gl3state ().uni3DData) * 4, _gl3state ().uni3DData)


def GL3_UpdateUBOLights (): #void

	updateUBO (_gl3state ().uniLightsUBO, len(_gl3state ().uniLightsData) * 4, _gl3state ().uniLightsData)
