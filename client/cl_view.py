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
from __future__ import annotations

# cl_view.c -- player rendering positioning

import math
import functools
import copy
import numpy as np
from qcommon import cvar, common, cmd, cmodel
from game import q_shared
from client import cl_tent, cl_main, client, console, cl_scrn, cl_ents, ref
from linux import q_shlinux, vid_so, cd_linux, sys_linux
"""
#include "client.h"

//=============
//
// development tools for weapons
//
int			gun_frame;
struct model_s	*gun_model;

//=============
"""
crosshair = None #cvar_t *
cl_testparticles = None #cvar_t *
cl_testentities = None #cvar_t *
cl_testlights = None #cvar_t *
cl_testblend = None #cvar_t *

cl_stats = None #cvar_t *

cl_weaponmodels = [""] * client.MAX_CLIENTWEAPONMODELS
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
	q_shared.VectorCopy(org, p.origin)
	p.color = color
	p.alpha = alpha
	r_numparticles += 1


def V_AddLight (org, intensity, r, g, b):
	global r_numdlights

	if r_numdlights >= ref.MAX_DLIGHTS:
		return
	dl = r_dlights[r_numdlights]
	q_shared.VectorCopy(org, dl.origin)
	dl.intensity = intensity
	dl.color[0] = r
	dl.color[1] = g
	dl.color[2] = b
	r_numdlights += 1


def V_AddLightStyle (style, r, g, b):
	if style < 0 or style > ref.MAX_LIGHTSTYLES:
		common.Com_Error(q_shared.ERR_DROP, "Bad light style %i" % style)
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
def V_TestEntities ():

	global r_numentities
	#int			i, j;
	#float		f, r;
	#entity_t	*ent;

	r_numentities = 32
	for i in range(len(r_entities)): # memset (r_entities, 0, sizeof(r_entities));
		r_entities[i] = ref.entity_t()

	for i in range(r_numentities):
	
		ent = r_entities[i]

		r = 64 * ( (i%4) - 1.5 )
		f = 64 * (i//4) + 128

		for j in range(3):
			ent.origin[j] = cl_main.cl.refdef.vieworg[j] + cl_main.cl.v_forward[j]*f + \
			cl_main.cl.v_right[j]*r

		ent.model = cl_main.cl.baseclientinfo.model
		ent.skin = cl_main.cl.baseclientinfo.skin
	

"""
================
V_TestLights

If cl_testlights is set, create 32 lights models
================
"""
def V_TestLights ():

	global r_numdlights
	#int			i, j;
	#float		f, r;
	#dlight_t	*dl;

	r_numdlights = 32
	for i in range(len(r_dlights)): # memset (r_dlights, 0, sizeof(r_dlights));
		r_dlights[i] = ref.dlight_t()

	for i in range(r_numdlights):
	
		dl = r_dlights[i]

		r = 64 * ( (i%4) - 1.5 )
		f = 64 * (i//4) + 128

		for j in range(3):
			dl.origin[j] = cl_main.cl.refdef.vieworg[j] + cl_main.cl.v_forward[j]*f + \
			cl_main.cl.v_right[j]*r
		dl.color[0] = ((i%6)+1) & 1
		dl.color[1] = (((i%6)+1) & 2)>>1
		dl.color[2] = (((i%6)+1) & 4)>>2
		dl.intensity = 200
	

# ===================================================================
# CL_PrepRefresh
#
# Call before entering a new level, or after changing dlls
# ===================================================================
def CL_PrepRefresh ():

	global cl_weaponmodels, num_cl_weaponmodels
	
	axis = np.zeros((3,), dtype=np.float32)

	if not cl_main.cl.configstrings[q_shared.CS_MODELS+1]:
		return		# no map loaded

	cl_scrn.SCR_AddDirtyPoint (0, 0)
	cl_scrn.SCR_AddDirtyPoint (vid_so.viddef.width-1, vid_so.viddef.height-1)

	# let the render dll load the map
	mapname = cl_main.cl.configstrings[q_shared.CS_MODELS+1]
	if mapname and mapname.startswith("maps/"):
		mapname = mapname[5:]
	if mapname and mapname.endswith(".bsp"):
		mapname = mapname[:-4]

	cl_weaponmodels[0] = "weapon.md2"
	num_cl_weaponmodels = 1

	common.Com_Printf ("Map: {}\r".format(mapname))
	cl_scrn.SCR_UpdateScreen ()
	vid_so.re.BeginRegistration (mapname)
	common.Com_Printf ("                                     \r")

	# precache status bar pics
	common.Com_Printf ("pics\r")
	cl_scrn.SCR_UpdateScreen ()
	cl_scrn.SCR_TouchPics ()
	common.Com_Printf ("                                     \r")

	cl_tent.CL_RegisterTEntModels ()

	# register models
	for i in range(1, q_shared.MAX_MODELS):
		model_name = cl_main.cl.configstrings[q_shared.CS_MODELS + i]
		if not model_name:
			break
		name = model_name[:37]
		if not model_name.startswith('*'):
			common.Com_Printf ("{}\r".format(name))
		cl_scrn.SCR_UpdateScreen ()
		sys_linux.Sys_SendKeyEvents ()
		if model_name.startswith('#'):
			if num_cl_weaponmodels < client.MAX_CLIENTWEAPONMODELS:
				cl_weaponmodels[num_cl_weaponmodels] = model_name[1:]
				num_cl_weaponmodels += 1
			if not model_name.startswith('*'):
				common.Com_Printf ("                                     \r")
			continue
		cl_main.cl.model_draw[i] = vid_so.re.RegisterModel (model_name)
		if model_name.startswith('*'):
			cl_main.cl.model_clip[i] = cmodel.CM_InlineModel (model_name)
		else:
			cl_main.cl.model_clip[i] = None
		if not model_name.startswith('*'):
			common.Com_Printf ("                                     \r")

	# precache images
	common.Com_Printf ("images\r")
	cl_scrn.SCR_UpdateScreen ()
	for i in range(1, q_shared.MAX_IMAGES):
		image_name = cl_main.cl.configstrings[q_shared.CS_IMAGES + i]
		if not image_name:
			break
		cl_main.cl.image_precache[i] = vid_so.re.RegisterPic (image_name)
		sys_linux.Sys_SendKeyEvents ()
	common.Com_Printf ("                                     \r")

	# cache player skins
	from client import cl_parse as cl_parse_mod

	for i in range(q_shared.MAX_CLIENTS):
		info = cl_main.cl.configstrings[q_shared.CS_PLAYERSKINS + i]
		if not info:
			continue
		common.Com_Printf ("client {}\r".format(i))
		cl_scrn.SCR_UpdateScreen ()
		sys_linux.Sys_SendKeyEvents ()
		cl_parse_mod.CL_ParseClientinfo (i)
		common.Com_Printf ("                                     \r")

	cl_parse_mod.CL_LoadClientinfo (cl_main.cl.baseclientinfo, "unnamed\\male/grunt")

	# set sky textures and speed
	common.Com_Printf ("sky\r")
	cl_scrn.SCR_UpdateScreen ()
	try:
		rotate = float(cl_main.cl.configstrings[q_shared.CS_SKYROTATE] or 0.0)
	except (TypeError, ValueError):
		rotate = 0.0
	axis_values = (cl_main.cl.configstrings[q_shared.CS_SKYAXIS] or "0 0 1").split()
	for idx in range(min(3, len(axis_values))):
		try:
			axis[idx] = float(axis_values[idx])
		except ValueError:
			axis[idx] = 0.0
	if len(axis_values) < 3:
		for idx in range(len(axis_values), 3):
			axis[idx] = 0.0
	vid_so.re.SetSky (cl_main.cl.configstrings[q_shared.CS_SKY], rotate, axis)
	common.Com_Printf ("                                     \r")

	# the renderer can now free unneeded stuff
	vid_so.re.EndRegistration ()

	# clear any lines of console text
	console.Con_ClearNotify ()

	cl_scrn.SCR_UpdateScreen ()
	cl_main.cl.refresh_prepped = True
	cl_main.cl.force_refdef = True # make sure we have a valid refdef

	# start the cd track
	try:
		cd_track = int(cl_main.cl.configstrings[q_shared.CS_CDTRACK] or 0)
	except (TypeError, ValueError):
		cd_track = 0
	cd_linux.CDAudio_Play (cd_track, True)


# ====================
# CalcFov
# ====================
def CalcFov (fov_x: float, width: float, height: float)->float:

	#float	a;
	#float	x;

	if fov_x < 1 or fov_x > 179:
		common.Com_Error (q_shared.ERR_DROP, "Bad fov: {}".format(fov_x))

	x = width/math.tan(fov_x/360*math.pi)

	a = math.atan (height/x)

	a = a*360.0/math.pi

	return a


# =============================================================================
# gun frame debugging functions
def V_Gun_Next_f ():
	pass
	# C implementation is still unported.

def V_Gun_Prev_f ():
	pass
	# C implementation is still unported.

def V_Gun_Model_f ():

	pass
	# C implementation is still unported.

# =============================================================================
# SCR_DrawCrosshair
# =============================================================================
def SCR_DrawCrosshair ():

	if not crosshair.value:
		return

	if crosshair.modified:
	
		crosshair.modified = False
		cl_scrn.SCR_TouchPics ()
	
	if not cl_scrn.crosshair_pic:
		return

	vid_so.re.DrawPic (cl_scrn.scr_vrect.x + ((cl_scrn.scr_vrect.width - cl_scrn.crosshair_width)>>1)
	, cl_scrn.scr_vrect.y + ((cl_scrn.scr_vrect.height - cl_scrn.crosshair_height)>>1), cl_scrn.crosshair_pic)

# ==================
# V_RenderView
# ==================
def V_RenderView( stereo_separation: float ):

	global r_numdlights, r_numentities, r_numparticles

	#extern int entitycmpfnc( const entity_t *, const entity_t * );

	if cl_main.cls.state != client.connstate_t.ca_active:
		return

	if not cl_main.cl.refresh_prepped:
		return			# still loading

	if int(cl_main.cl_timedemo.value):
	
		if not cl_main.cl.timedemo_start:
			cl_main.cl.timedemo_start = q_shlinux.Sys_Milliseconds ()
		cl_main.cl.timedemo_frames+=1
	
	# an invalid frame will just use the exact previous refdef
	# we can't use the old frame if the video mode has changed, though...
	if cl_main.cl.frame.valid and (cl_main.cl.force_refdef or not int(cl_main.cl_paused.value)):
	
		cl_main.cl.force_refdef = False

		V_ClearScene ()

		# build a refresh entity list and calc cl_main.cl.sim*
		# this also calls CL_CalcViewValues which loads
		# v_forward, etc.
		cl_ents.CL_AddEntities ()

		if int(cl_testparticles.value):
			V_TestParticles ()
		if int(cl_testentities.value):
			V_TestEntities ()
		if int(cl_testlights.value):
			V_TestLights ()
		if int(cl_testblend.value):
		
			cl_main.cl.refdef.blend[0] = 1
			cl_main.cl.refdef.blend[1] = 0.5
			cl_main.cl.refdef.blend[2] = 0.25
			cl_main.cl.refdef.blend[3] = 0.5
		

		# offset vieworg appropriately if we're doing stereo separation
		if stereo_separation != 0:
		
			tmp = np.zeros((3,), dtype=np.float32) #vec3_t

			q_shared.VectorScale( cl_main.cl.v_right, stereo_separation, tmp )
			q_shared.VectorAdd( cl_main.cl.refdef.vieworg, tmp, cl_main.cl.refdef.vieworg )
		

		# never let it sit exactly on a node line, because a water plane can
		# dissapear when viewed with the eye exactly on it.
		# the server protocol only specifies to 1/8 pixel, so add 1/16 in each axis
		cl_main.cl.refdef.vieworg[0] += 1.0/16
		cl_main.cl.refdef.vieworg[1] += 1.0/16
		cl_main.cl.refdef.vieworg[2] += 1.0/16

		cl_main.cl.refdef.x = cl_scrn.scr_vrect.x
		cl_main.cl.refdef.y = cl_scrn.scr_vrect.y
		cl_main.cl.refdef.width = cl_scrn.scr_vrect.width
		cl_main.cl.refdef.height = cl_scrn.scr_vrect.height
		cl_main.cl.refdef.fov_y = CalcFov (cl_main.cl.refdef.fov_x, cl_main.cl.refdef.width, cl_main.cl.refdef.height)
		cl_main.cl.refdef.time = cl_main.cl.time*0.001

		cl_main.cl.refdef.areabits = cl_main.cl.frame.areabits

		if not int(cl_main.cl_add_entities.value):
			r_numentities = 0
		if not int(cl_main.cl_add_particles.value):
			r_numparticles = 0
		if not int(cl_main.cl_add_lights.value):
			r_numdlights = 0
		if not int(cl_main.cl_add_blend.value):
			q_shared.VectorClear (cl_main.cl.refdef.blend)	

		cl_main.cl.refdef.num_entities = r_numentities
		cl_main.cl.refdef.entities = r_entities
		cl_main.cl.refdef.num_particles = r_numparticles
		cl_main.cl.refdef.particles = r_particles
		cl_main.cl.refdef.num_dlights = r_numdlights
		cl_main.cl.refdef.dlights = r_dlights
		cl_main.cl.refdef.lightstyles = r_lightstyles

		cl_main.cl.refdef.rdflags = cl_main.cl.frame.playerstate.rdflags

		# sort entities for better cache locality
		# qsort( cl.refdef.entities, cl.refdef.num_entities, ... ): only the first num_entities are live
		cl_main.cl.refdef.entities[:r_numentities] = sorted(cl_main.cl.refdef.entities[:r_numentities], key=functools.cmp_to_key(cl_scrn.entitycmpfnc))
	
	vid_so.re.RenderFrame (cl_main.cl.refdef)
	if cl_stats.value:
		common.Com_Printf ("ent:{}  lt:{}  part:{}\n".format(r_numentities, r_numdlights, r_numparticles))
	if int(common.log_stats.value) and ( log_stats_file != 0 ):
		log_stats_file = "{},{},{},".format(r_numentities, r_numdlights, r_numparticles)

	cl_scrn.SCR_AddDirtyPoint (cl_scrn.scr_vrect.x, cl_scrn.scr_vrect.y)
	cl_scrn.SCR_AddDirtyPoint (cl_scrn.scr_vrect.x+cl_scrn.scr_vrect.width-1,
		cl_scrn.scr_vrect.y+cl_scrn.scr_vrect.height-1)

	SCR_DrawCrosshair ()



# =============
# V_Viewpos_f
# =============
def V_Viewpos_f ():

	common.Com_Printf ("({} {} {}) : {}\n".format(int(cl_main.cl.refdef.vieworg[0]),
		int(cl_main.cl.refdef.vieworg[1]), int(cl_main.cl.refdef.vieworg[2]), 
		int(cl_main.cl.refdef.viewangles[q_shared.YAW])))

# =============
# V_Init
# =============
def V_Init ():

	global crosshair, cl_testparticles, cl_testentities, cl_testlights, cl_testblend, cl_stats

	cmd.Cmd_AddCommand ("gun_next", V_Gun_Next_f)
	cmd.Cmd_AddCommand ("gun_prev", V_Gun_Prev_f)
	cmd.Cmd_AddCommand ("gun_model", V_Gun_Model_f)

	cmd.Cmd_AddCommand ("viewpos", V_Viewpos_f);
	
	crosshair = cvar.Cvar_Get ("crosshair", "0", q_shared.CVAR_ARCHIVE)

	cl_testblend = cvar.Cvar_Get ("cl_testblend", "0", 0)
	cl_testparticles = cvar.Cvar_Get ("cl_testparticles", "0", 0)
	cl_testentities = cvar.Cvar_Get ("cl_testentities", "0", 0)
	cl_testlights = cvar.Cvar_Get ("cl_testlights", "0", 0)

	cl_stats = cvar.Cvar_Get ("cl_stats", "0", 0)

