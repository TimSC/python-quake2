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

This file implements the camera, e.g the player's view

=======================================================================
"""
from __future__ import annotations

from client.vid import vid


"""
#include "header/client.h"
#include "input/header/input.h"
"""

import math
import functools
import numpy as np
from client import cl_tent, cl_main, ref
from linux import q_shlinux, vid_so, cd_linux, sys_linux
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import cvar
from common import frame
from common import collision
from client import cl_console
from client import cl_entities
from client import cl_main
from client import cl_parse
from client import cl_prediction
from client import cl_screen
from client.sound import ogg
from client.header import client as client_h

pass
pass
"""
#include "client.h"
"""

#=============
#
# development tools for weapons
#
gun_frame = 0 #int
gun_model = None #struct model_s *

#=============
crosshair = None #cvar_t *
crosshair_3d = None #cvar_t *
crosshair_3d_glow = None #cvar_t *
cl_testparticles = None #cvar_t *
cl_testentities = None #cvar_t *
cl_testlights = None #cvar_t *
cl_testblend = None #cvar_t *

crosshair_3d_glow_r = None #cvar_t *
crosshair_3d_glow_g = None #cvar_t *
crosshair_3d_glow_b = None #cvar_t *

cl_stats = None #cvar_t *

cl_weaponmodels = [""] * client_h.MAX_CLIENTWEAPONMODELS
num_cl_weaponmodels = 0


r_numdlights: int = 0
r_dlights = []
for i in range(ref.MAX_DLIGHTS):
	r_dlights.append(ref.dlight_t())

r_numentities: int = 0
r_entities = []
for i in range(ref.MAX_ENTITIES):
	r_entities.append(ref.entity_t())

r_numparticles: int = 0
r_particles = []
for i in range(ref.MAX_PARTICLES):
	r_particles.append(ref.particle_t())

r_lightstyles = []
for i in range(ref.MAX_LIGHTSTYLES):
	r_lightstyles.append(ref.lightstyle_t())

crosshair_scale = None #cvar_t *
crosshair_color_r = None #cvar_t *
crosshair_color_g = None #cvar_t *
crosshair_color_b = None #cvar_t *

"""
char cl_weaponmodels[MAX_CLIENTWEAPONMODELS][MAX_QPATH];

/*
====================
V_ClearScene

Specifies the model that will be used as the world
====================
"""
def V_ClearScene ():

	global r_numdlights, r_numentities, r_numparticles

	r_numdlights = 0
	r_numentities = 0
	r_numparticles = 0


def V_AddEntity (ent):
	global r_numentities

	if r_numentities >= ref.MAX_ENTITIES:
		return
	r_entities[r_numentities] = ent.copy() # r_entities[r_numentities++] = *ent
	r_numentities += 1


def V_AddParticle (org, color, alpha):
	global r_numparticles

	if r_numparticles >= ref.MAX_PARTICLES:
		return
	p = r_particles[r_numparticles]
	shared.VectorCopy(org, p.origin)
	p.color = color
	p.alpha = alpha
	r_numparticles += 1


def V_AddLight (org, intensity, r, g, b):
	global r_numdlights

	if r_numdlights >= ref.MAX_DLIGHTS:
		return
	dl = r_dlights[r_numdlights]
	shared.VectorCopy(org, dl.origin)
	dl.intensity = intensity
	dl.color[0] = r
	dl.color[1] = g
	dl.color[2] = b
	r_numdlights += 1


def V_AddLightStyle (style, r, g, b):
	if style < 0 or style > ref.MAX_LIGHTSTYLES:
		clientserver.Com_Error(shared.ERR_DROP, "Bad light style %i" % style)
	ls = r_lightstyles[style]
	ls.white = r + g + b
	ls.rgb[0] = r
	ls.rgb[1] = g
	ls.rgb[2] = b
"""
================
V_TestParticles

If cl_testparticles is set, create 4096 particles in the view
================
"""
def V_TestParticles ():

	global r_numparticles
	#particle_t	*p;
	#int			i, j;
	#float		d, r, u;

	r_numparticles = ref.MAX_PARTICLES
	for i in range(r_numparticles):
	
		d = i*0.25
		r = 4*((i&7)-3.5)
		u = 4*(((i>>3)&7)-3.5)
		p = r_particles[i]

		for j in range(3):
			p.origin[j] = cl_main.cl.refdef.vieworg[j] + cl_main.cl.v_forward[j]*d + \
			cl_main.cl.v_right[j]*r + cl_main.cl.v_up[j]*u

		p.color = 8
		p.alpha = cl_testparticles.value
	

"""
================
V_TestEntities

If cl_testentities is set, create 32 player models
================
"""
def V_TestEntities(): # (static)

	"""
	int i, j;
	float f, r;
	entity_t *ent;
	"""
	global r_numentities

	r_numentities = 32
	for i in range(len(r_entities)): # memset(r_entities, 0, sizeof(r_entities));
		r_entities[i] = ref.entity_t()

	for i in range(r_numentities):

		ent = r_entities[i]

		r = 64.0 * (float(i % 4) - 1.5)
		f = float(64 * (i // 4) + 128)

		for j in range(3):

			ent.origin[j] = cl_main.cl.refdef.vieworg[j] + cl_main.cl.v_forward[j] * f + \
							 cl_main.cl.v_right[j] * r


		ent.model = cl_main.cl.baseclientinfo.model
		ent.skin = cl_main.cl.baseclientinfo.skin

	

"""
================
V_TestLights

If cl_testlights is set, create 32 lights models
================
"""
def V_TestLights(): # (static)

	"""
	int i;
	"""
	global r_numdlights

	r_numdlights = 32
	for i in range(len(r_dlights)): # memset(r_dlights, 0, sizeof(r_dlights));
		r_dlights[i] = ref.dlight_t()

	for i in range(r_numdlights):

		"""
		dlight_t *dl;
		float f, r;
		int j;
		"""

		dl = r_dlights[i]

		r = 64 * ((i % 4) - 1.5)
		f = 64 * (i / 4.0) + 128

		for j in range(3):

			dl.origin[j] = cl_main.cl.refdef.vieworg[j] + cl_main.cl.v_forward[j] * f + \
							cl_main.cl.v_right[j] * r


		dl.color[0] = float(((i % 6) + 1) & 1)
		dl.color[1] = float((((i % 6) + 1) & 2) >> 1)
		dl.color[2] = float((((i % 6) + 1) & 4) >> 2)
		dl.intensity = 200

	

# ===================================================================
# CL_PrepRefresh
#
# Call before entering a new level, or after changing dlls
# ===================================================================
def CL_PrepRefresh(): #void

	"""
	char mapname[MAX_QPATH];
	int i;
	char *name;
	float rotate;
	vec3_t axis;
	"""
	global num_cl_weaponmodels

	axis = np.zeros((3,), dtype=np.float32)

	if not cl_main.cl.configstrings[shared.CS_MODELS + 1]: # [0]

		return


	cl_screen.SCR_AddDirtyPoint(0, 0)
	cl_screen.SCR_AddDirtyPoint(vid_so.viddef.width - 1, vid_so.viddef.height - 1)

	# let the refresher load the map
	mapname = cl_main.cl.configstrings[shared.CS_MODELS + 1][5:][:shared.MAX_QPATH - 1] # skip "maps/"
	mapname = mapname[:len(mapname) - 4] # cut off ".bsp"

	# register models, pics, and skins
	clientserver.Com_Printf("Map: %s\r", mapname)
	cl_screen.SCR_UpdateScreen()
	vid.R_BeginRegistration (mapname)

	# precache status bar pics
	clientserver.Com_Printf("pics\r")
	cl_screen.SCR_UpdateScreen()
	cl_screen.SCR_TouchPics()

	cl_tent.CL_RegisterTEntModels()

	num_cl_weaponmodels = 1
	cl_weaponmodels[0] = "weapon.md2" # strcpy

	clientserver.Com_Printf("models\r")
	cl_screen.SCR_UpdateScreen()

	i = 1
	while i < shared.MAX_MODELS and cl_main.cl.configstrings[shared.CS_MODELS + i]:

		name = cl_main.cl.configstrings[shared.CS_MODELS + i]

		if name[0] == '#':

			# special player weapon model
			if num_cl_weaponmodels < client_h.MAX_CLIENTWEAPONMODELS:

				cl_weaponmodels[num_cl_weaponmodels] = cl_main.cl.configstrings[shared.CS_MODELS + i][1:][:shared.MAX_QPATH - 1] # Q_strlcpy

				num_cl_weaponmodels += 1


		else:

			cl_main.cl.model_draw[i] = vid.R_RegisterModel(cl_main.cl.configstrings[shared.CS_MODELS + i])

			cl_main.cl.model_clip[i] = collision.CM_InlineModel(name) if (name[0] == '*') else \
				None

		i += 1


	clientserver.Com_Printf("images\r")
	cl_screen.SCR_UpdateScreen()

	i = 1
	while i < shared.MAX_IMAGES and cl_main.cl.configstrings[shared.CS_IMAGES + i]:

		cl_main.cl.image_precache[i] = vid.Draw_FindPic(cl_main.cl.configstrings[shared.CS_IMAGES + i])
		i += 1


	clientserver.Com_Printf("clients\r")
	cl_screen.SCR_UpdateScreen()

	for i in range(shared.MAX_CLIENTS):

		if cl_main.cl.configstrings[shared.CS_PLAYERSKINS + i]: # [0]

			cl_parse.CL_ParseClientinfo(i)



	cl_parse.CL_LoadClientinfo(cl_main.cl.baseclientinfo, "unnamed\\male/grunt")

	# set sky textures and speed
	clientserver.Com_Printf("sky\r")
	cl_screen.SCR_UpdateScreen()
	rotate = shared_c.atof(cl_main.cl.configstrings[shared.CS_SKYROTATE]) # (float)strtod(..., (char **)NULL)
	# sscanf(cl.configstrings[CS_SKYAXIS], "%f %f %f", &axis[0], &axis[1], &axis[2]); stops at the first value it can't read
	for j, v in enumerate(cl_main.cl.configstrings[shared.CS_SKYAXIS].split()[:3]):
		try:
			axis[j] = float(v)
		except ValueError:
			break
	vid.R_SetSky(cl_main.cl.configstrings[shared.CS_SKY], rotate, axis)

	clientserver.Com_Printf("                                     \r")

	# the renderer can now free unneeded stuff
	vid.R_EndRegistration()

	# clear any lines of console text
	cl_console.Con_ClearNotify()

	cl_screen.SCR_UpdateScreen()
	cl_main.cl.refresh_prepped = True
	cl_main.cl.force_refdef = True # make sure we have a valid refdef

	# start the cd track
	ogg.OGG_PlayTrack(cl_main.cl.configstrings[shared.CS_CDTRACK], True, True)



# ====================
# CalcFov
# ====================
def CalcFov(fov_x, width, height): #float, float, float (returns float)

	"""
	float a;
	float x;
	"""

	if (fov_x < 1) or (fov_x > 179):

		clientserver.Com_Error(shared.ERR_DROP, "Bad fov: %f", fov_x)


	x = width / math.tan(fov_x / 360 * math.pi)
	a = math.atan(height / x)
	a = a * 360 / math.pi
	return a


def V_Gun_Next_f(): # (static)

	global gun_frame

	gun_frame += 1
	clientserver.Com_Printf("frame %i\n", gun_frame)

def V_Gun_Prev_f(): # (static)

	global gun_frame

	gun_frame -= 1

	if gun_frame < 0:

		gun_frame = 0


	clientserver.Com_Printf("frame %i\n", gun_frame)

def V_Gun_Model_f(): # (static)

	global gun_model

	"""
	char name[MAX_QPATH];
	"""
	name = [None] * shared.MAX_QPATH

	if cmdparser.Cmd_Argc() != 2:

		gun_model = None
		return


	name = "models/%s/tris.md2" % (cmdparser.Cmd_Argv(1),) # Com_sprintf
	gun_model = vid.R_RegisterModel(name)

# ==================
# V_RenderView
# ==================
"""
================
SCR_TimeRefresh_f
================
"""
def entitycmpfnc(a, b): #const entity_t *, const entity_t * (returns static int)

	# Q2PORT: the C compares the model and skin pointers; id() is the Python
	# object's address, so entities still group by model then skin

	# all other models are sorted by model then skin
	if a.model is b.model:

		return 0 if (a.skin is b.skin) else \
			(1 if (id(a.skin) > id(b.skin)) else -1)

	else:

		return 1 if (id(a.model) > id(b.model)) else -1


def V_Render3dCrosshair(): # (static)

	"""
	trace_t crosshair_trace;
	vec3_t end;
	"""
	global crosshair_3d, crosshair_3d_glow, crosshair_3d_glow_r, crosshair_3d_glow_g, crosshair_3d_glow_b

	end = np.zeros((3,), dtype=np.float32)

	crosshair_3d = cvar.Cvar_Get("crosshair_3d", "0", shared.CVAR_ARCHIVE)
	crosshair_3d_glow = cvar.Cvar_Get("crosshair_3d_glow", "0", shared.CVAR_ARCHIVE)


	if crosshair_3d.value or crosshair_3d_glow.value:
		shared_c.VectorMA(cl_main.cl.refdef.vieworg, 8192, cl_main.cl.v_forward, end)
		crosshair_trace = cl_prediction.CL_PMTrace(cl_main.cl.refdef.vieworg, shared_c.vec3_origin, shared_c.vec3_origin, end)

		if crosshair_3d_glow.value:
			crosshair_3d_glow_r = cvar.Cvar_Get("crosshair_3d_glow_r", "5", shared.CVAR_ARCHIVE)
			crosshair_3d_glow_g = cvar.Cvar_Get("crosshair_3d_glow_g", "1", shared.CVAR_ARCHIVE)
			crosshair_3d_glow_b = cvar.Cvar_Get("crosshair_3d_glow_b", "4", shared.CVAR_ARCHIVE)

			V_AddLight(
				crosshair_trace.endpos,
				crosshair_3d_glow.value,
				crosshair_3d_glow_r.value,
				crosshair_3d_glow_g.value,
				crosshair_3d_glow_b.value
			)


		if crosshair_3d.value:
			crosshair_ent = ref.entity_t() # entity_t crosshair_ent = {0};

			crosshair_ent.origin[0] = crosshair_trace.endpos[0]
			crosshair_ent.origin[1] = crosshair_trace.endpos[1]
			crosshair_ent.origin[2] = crosshair_trace.endpos[2]

			crosshair_ent.model = vid.R_RegisterModel("models/crosshair/tris.md2")
			#crosshair_ent.skin = R_RegisterSkin("models/crosshair/skin.pcx");

			shared_c.AngleVectors2(crosshair_trace.plane.normal, crosshair_ent.angles)
			crosshair_ent.flags = shared.RF_DEPTHHACK | shared.RF_FULLBRIGHT | shared.RF_NOSHADOW

			V_AddEntity(crosshair_ent)


def V_RenderView(stereo_separation: float): #float

	global r_numdlights, r_numentities, r_numparticles

	if cl_main.cls.state != client_h.connstate_t.ca_active:

		vid.R_EndWorldRenderpass()
		return


	if not cl_main.cl.refresh_prepped:

		vid.R_EndWorldRenderpass()
		return # still loading


	if frame.cl_timedemo.value:

		if not cl_main.cl.timedemo_start:

			cl_main.cl.timedemo_start = q_shlinux.Sys_Milliseconds()


		cl_main.cl.timedemo_frames += 1


	# an invalid frame will just use the exact previous refdef
	# we can't use the old frame if the video mode has changed, though...
	if cl_main.cl.frame.valid and (cl_main.cl.force_refdef or not cl_main.cl_paused.value):

		cl_main.cl.force_refdef = False

		V_ClearScene()

		# build a refresh entity list and calc cl.sim*
		# this also calls CL_CalcViewValues which loads
		# v_forward, etc.
		cl_entities.CL_AddEntities()

		# before changing viewport we should trace the crosshair position
		V_Render3dCrosshair()

		if cl_testparticles.value:

			V_TestParticles()


		if cl_testentities.value:

			V_TestEntities()


		if cl_testlights.value:

			V_TestLights()


		if cl_testblend.value:

			cl_main.cl.refdef.blend[0] = 1
			cl_main.cl.refdef.blend[1] = 0.5
			cl_main.cl.refdef.blend[2] = 0.25
			cl_main.cl.refdef.blend[3] = 0.5


		# offset vieworg appropriately if
		# we're doing stereo separation

		if stereo_separation != 0:

			tmp = np.zeros((3,), dtype=np.float32) #vec3_t

			shared_c.VectorScale(cl_main.cl.v_right, stereo_separation, tmp)
			shared.VectorAdd(cl_main.cl.refdef.vieworg, tmp, cl_main.cl.refdef.vieworg)


		# never let it sit exactly on a node line, because a water plane can
		# dissapear when viewed with the eye exactly on it. the server protocol
		# only specifies to 1/8 pixel, so add 1/16 in each axis
		cl_main.cl.refdef.vieworg[0] += 1.0 / 16
		cl_main.cl.refdef.vieworg[1] += 1.0 / 16
		cl_main.cl.refdef.vieworg[2] += 1.0 / 16

		cl_main.cl.refdef.time = cl_main.cl.time * 0.001

		cl_main.cl.refdef.areabits = cl_main.cl.frame.areabits

		if not cl_main.cl_add_entities.value:

			r_numentities = 0


		if not cl_main.cl_add_particles.value:

			r_numparticles = 0


		if not cl_main.cl_add_lights.value:

			r_numdlights = 0


		if not cl_main.cl_add_blend.value:

			shared.VectorClear(cl_main.cl.refdef.blend)


		cl_main.cl.refdef.num_entities = r_numentities
		cl_main.cl.refdef.entities = r_entities
		cl_main.cl.refdef.num_particles = r_numparticles
		cl_main.cl.refdef.particles = r_particles
		cl_main.cl.refdef.num_dlights = r_numdlights
		cl_main.cl.refdef.dlights = r_dlights
		cl_main.cl.refdef.lightstyles = r_lightstyles

		cl_main.cl.refdef.rdflags = cl_main.cl.frame.playerstate.rdflags

		# sort entities for better cache locality
		# qsort(cl.refdef.entities, cl.refdef.num_entities, ...); only the first num_entities are live
		cl_main.cl.refdef.entities[:cl_main.cl.refdef.num_entities] = sorted(
				cl_main.cl.refdef.entities[:cl_main.cl.refdef.num_entities], key=functools.cmp_to_key(entitycmpfnc))

	elif cl_main.cl.frame.valid and cl_main.cl_paused.value and cl_main.gl1_stereo.value:
		# We need to adjust the refdef in stereo mode when paused.
		tmp = np.zeros((3,), dtype=np.float32) #vec3_t
		cl_entities.CL_CalcViewValues()
		shared_c.VectorScale( cl_main.cl.v_right, stereo_separation, tmp )
		shared.VectorAdd( cl_main.cl.refdef.vieworg, tmp, cl_main.cl.refdef.vieworg )

		cl_main.cl.refdef.vieworg[0] += 1.0/16
		cl_main.cl.refdef.vieworg[1] += 1.0/16
		cl_main.cl.refdef.vieworg[2] += 1.0/16

		cl_main.cl.refdef.time = cl_main.cl.time*0.001


	cl_main.cl.refdef.x = cl_screen.scr_vrect.x
	cl_main.cl.refdef.y = cl_screen.scr_vrect.y
	cl_main.cl.refdef.width = cl_screen.scr_vrect.width
	cl_main.cl.refdef.height = cl_screen.scr_vrect.height
	cl_main.cl.refdef.fov_y = CalcFov(cl_main.cl.refdef.fov_x, float(cl_main.cl.refdef.width),
				float(cl_main.cl.refdef.height))

	vid.R_RenderFrame(cl_main.cl.refdef)

	if cl_stats.value:

		clientserver.Com_Printf("ent:%i  lt:%i  part:%i\n", r_numentities,
				r_numdlights, r_numparticles)


	if frame.log_stats.value and (frame.log_stats_file is not None):

		frame.log_stats_file.write("{},{},{},".format(r_numentities,
				r_numdlights, r_numparticles))


	cl_screen.SCR_AddDirtyPoint(cl_screen.scr_vrect.x, cl_screen.scr_vrect.y)
	cl_screen.SCR_AddDirtyPoint(cl_screen.scr_vrect.x + cl_screen.scr_vrect.width - 1,
			cl_screen.scr_vrect.y + cl_screen.scr_vrect.height - 1)

	cl_screen.SCR_DrawCrosshair()



# =============
# V_Viewpos_f
# =============
def V_Viewpos_f(): # (static)

	clientserver.Com_Printf("position: %i %i %i, angles: %i %i %i\n", cl_main.cl.refdef.vieworg[0], cl_main.cl.refdef.vieworg[1], cl_main.cl.refdef.vieworg[2], cl_main.cl.refdef.viewangles[shared.PITCH], cl_main.cl.refdef.viewangles[shared.YAW], cl_main.cl.refdef.viewangles[shared.ROLL])

# =============
# V_Init
# =============
def V_Init(): #
	global cl_stats, cl_testblend, cl_testentities, cl_testlights, cl_testparticles, crosshair, crosshair_color_b, crosshair_color_g, crosshair_color_r, crosshair_scale

	cmdparser.Cmd_AddCommand("gun_next", V_Gun_Next_f)
	cmdparser.Cmd_AddCommand("gun_prev", V_Gun_Prev_f)
	cmdparser.Cmd_AddCommand("gun_model", V_Gun_Model_f)
	cmdparser.Cmd_AddCommand("viewpos", V_Viewpos_f)
	crosshair = cvar.Cvar_Get("crosshair", "0", shared.CVAR_ARCHIVE)
	crosshair_scale = cvar.Cvar_Get("crosshair_scale", "-1", shared.CVAR_ARCHIVE)
	crosshair_color_r = cvar.Cvar_Get("crosshair_color_r", "1", shared.CVAR_ARCHIVE)
	crosshair_color_g = cvar.Cvar_Get("crosshair_color_g", "1", shared.CVAR_ARCHIVE)
	crosshair_color_b = cvar.Cvar_Get("crosshair_color_b", "1", shared.CVAR_ARCHIVE)
	cl_testblend = cvar.Cvar_Get("cl_testblend", "0", 0)
	cl_testparticles = cvar.Cvar_Get("cl_testparticles", "0", 0)
	cl_testentities = cvar.Cvar_Get("cl_testentities", "0", 0)
	cl_testlights = cvar.Cvar_Get("cl_testlights", "0", 0)
	cl_stats = cvar.Cvar_Get("cl_stats", "0", 0)
