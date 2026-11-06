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

This file implements all static entities at client site.

=======================================================================
"""
from __future__ import annotations

import random
import numpy as np
import math
from client import cl_main, cl_parse, cl_tent, cl_fx, cl_newfx, cl_view, ref
from linux import vid_so
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import filesystem
from client import cl_main
from client import cl_parse
from client import cl_view
from client.header import client as client_h

"""
#include <math.h>
#include "header/client.h"
"""

def CL_AddPacketEntities (frame): #frame_t *

	"""
	entity_t			ent;
	entity_state_t		*s1;
	float				autorotate;
	int					i;
	int					pnum;
	centity_t			*cent;
	int					autoanim;
	clientinfo_t		*ci;
	unsigned int		effects, renderfx;
	"""
	cl = cl_main.cl

	# bonus items rotate at a fixed rate
	autorotate = shared_c.anglemod(cl.time/10)

	# brush models can auto animate their frames
	autoanim = int(2*cl.time/1000)

	ent = ref.entity_t() # memset (&ent, 0, sizeof(ent)); it is reused for every entity, as in the C

	for pnum in range(frame.num_entities):
	
		s1 = cl_main.cl_parse_entities[(frame.parse_entities+pnum)&(client_h.MAX_PARSE_ENTITIES-1)]

		cent = cl_main.cl_entities[s1.number]

		effects = s1.effects
		renderfx = s1.renderfx

			# set frame
		if effects & shared.EF_ANIM01:
			ent.frame = autoanim & 1
		elif effects & shared.EF_ANIM23:
			ent.frame = 2 + (autoanim & 1)
		elif effects & shared.EF_ANIM_ALL:
			ent.frame = autoanim
		elif effects & shared.EF_ANIM_ALLFAST:
			ent.frame = int(cl.time) // 100 # cl.time is int in C
		else:
			ent.frame = s1.frame

		# quad and pent can do different things on client
		if effects & shared.EF_PENT:
		
			effects &= ~shared.EF_PENT
			effects |= shared.EF_COLOR_SHELL
			renderfx |= shared.RF_SHELL_RED
		
		if effects & shared.EF_QUAD:
		
			effects &= ~shared.EF_QUAD
			effects |= shared.EF_COLOR_SHELL
			renderfx |= shared.RF_SHELL_BLUE
		
#======
# PMM
		if effects & shared.EF_DOUBLE:
		
			effects &= ~shared.EF_DOUBLE
			effects |= shared.EF_COLOR_SHELL
			renderfx |= shared.RF_SHELL_DOUBLE
		
		if effects & shared.EF_HALF_DAMAGE:
		
			effects &= ~shared.EF_HALF_DAMAGE
			effects |= shared.EF_COLOR_SHELL
			renderfx |= shared.RF_SHELL_HALF_DAM
		
# pmm
#======
		ent.oldframe = cent.prev.frame
		ent.backlerp = 1.0 - cl.lerpfrac

		if renderfx & (shared.RF_FRAMELERP|shared.RF_BEAM):
			# step origin discretely, because the frames
			# do the animation properly
			shared.VectorCopy (cent.current.origin, ent.origin)
			shared.VectorCopy (cent.current.old_origin, ent.oldorigin)
		
		else:
			# interpolate origin
			for i in range(3):
			
				ent.origin[i] = ent.oldorigin[i] = cent.prev.origin[i] + cl.lerpfrac * \
					(cent.current.origin[i] - cent.prev.origin[i])
			
		# create a new entity
	
		# tweak the color of beams
		if renderfx & shared.RF_BEAM:
			# the four beam colors are encoded in 32 bits of skinnum (hack)
			ent.alpha = 0.30
			ent.skinnum = (s1.skinnum >> ((random.getrandbits(15) % 4)*8)) & 0xff
			ent.model = None
		
		else:
		
			# set skin
			if s1.modelindex == 255:
				# use custom player skin
				ent.skinnum = 0
				ci = cl.clientinfo[s1.skinnum & 0xff]
				ent.skin = ci.skin
				ent.model = ci.model
				if not ent.skin or not ent.model:
				
					ent.skin = cl.baseclientinfo.skin
					ent.model = cl.baseclientinfo.model
				
#============
#PGM
				if renderfx & shared.RF_USE_DISGUISE:
				
					# strncmp((char *)ent.skin, ...) compares the image name, the first field of image_t
					skinname = ent.skin.name if ent.skin is not None else ""
					if skinname[:12] == "players/male":
					
						ent.skin = vid_so.re.RegisterSkin ("players/male/disguise.pcx")
						ent.model = vid_so.re.RegisterModel ("players/male/tris.md2")
					
					elif skinname[:14] == "players/female":
					
						ent.skin = vid_so.re.RegisterSkin ("players/female/disguise.pcx")
						ent.model = vid_so.re.RegisterModel ("players/female/tris.md2")
					
					elif skinname[:14] == "players/cyborg":
					
						ent.skin = vid_so.re.RegisterSkin ("players/cyborg/disguise.pcx")
						ent.model = vid_so.re.RegisterModel ("players/cyborg/tris.md2")
					
#PGM
#============
			
			else:
			
				ent.skinnum = s1.skinnum
				ent.skin = None
				ent.model = cl.model_draw[s1.modelindex]
			
		# only used for black hole model right now, FIXME: do better
		if renderfx == shared.RF_TRANSLUCENT:
			ent.alpha = 0.70

		# render effects (fullbright, translucent, etc)
		if effects & shared.EF_COLOR_SHELL:
			ent.flags = 0	# renderfx go on color shell entity
		else:
			ent.flags = renderfx

		# calculate angles
		if effects & shared.EF_ROTATE:
			# some bonus items auto-rotate
			ent.angles[0] = 0
			ent.angles[1] = autorotate
			ent.angles[2] = 0
		
		# RAFAEL
		elif effects & shared.EF_SPINNINGLIGHTS:
		
			ent.angles[0] = 0
			ent.angles[1] = shared_c.anglemod(cl.time/2) + s1.angles[1]
			ent.angles[2] = 180
			
			#vec3_t forward;
			#vec3_t start;
			forward = np.zeros((3,), dtype=np.float32)
			start = np.zeros((3,), dtype=np.float32)

			shared_c.AngleVectors (ent.angles, forward, None, None)
			shared_c.VectorMA (ent.origin, 64, forward, start)
			cl_view.V_AddLight (start, 100, 1, 0, 0)
			
		else:
			# interpolate angles
			#float	a1, a2;

			for i in range(3):
			
				a1 = cent.current.angles[i]
				a2 = cent.prev.angles[i]
				ent.angles[i] = shared_c.LerpAngle (a2, a1, cl.lerpfrac)
			
		if s1.number == cl.playernum+1:
		
			ent.flags |= shared.RF_VIEWERMODEL	# only draw from mirrors
			# FIXME: still pass to refresh

			if effects & shared.EF_FLAG1:
				cl_view.V_AddLight (ent.origin, 225, 1.0, 0.1, 0.1)
			elif effects & shared.EF_FLAG2:
				cl_view.V_AddLight (ent.origin, 225, 0.1, 0.1, 1.0)
			elif effects & shared.EF_TAGTRAIL:						#PGM
				cl_view.V_AddLight (ent.origin, 225, 1.0, 1.0, 0.0)	#PGM
			elif effects & shared.EF_TRACKERTRAIL:					#PGM
				cl_view.V_AddLight (ent.origin, 225, -1.0, -1.0, -1.0)	#PGM

			continue
		
		# if set to invisible, skip
		if not s1.modelindex:
			continue

		if effects & shared.EF_BFG:
		
			ent.flags |= shared.RF_TRANSLUCENT
			ent.alpha = 0.30
		
		# RAFAEL
		if effects & shared.EF_PLASMA:
		
			ent.flags |= shared.RF_TRANSLUCENT
			ent.alpha = 0.6
		
		if effects & shared.EF_SPHERETRANS:
		
			ent.flags |= shared.RF_TRANSLUCENT
			# PMM - *sigh*  yet more EF overloading
			if effects & shared.EF_TRACKERTRAIL:
				ent.alpha = 0.6
			else:
				ent.alpha = 0.3
		
#pmm

		# add to refresh list
		cl_view.V_AddEntity (ent)


		# color shells generate a seperate entity for the main model
		if effects & shared.EF_COLOR_SHELL:
		
			# PMM - at this point, all of the shells have been handled
			# if we're in the rogue pack, set up the custom mixing, otherwise just
			# keep going
#			if(Developer_searchpath(2) == 2)
#			{
				# all of the solo colors are fine.  we need to catch any of the combinations that look bad
				# (double & half) and turn them into the appropriate color, and make double/quad something special
			if renderfx & shared.RF_SHELL_HALF_DAM:
			
				if filesystem.Developer_searchpath(2) == 2:
				
					# ditch the half damage shell if any of red, blue, or double are on
					if renderfx & (shared.RF_SHELL_RED|shared.RF_SHELL_BLUE|shared.RF_SHELL_DOUBLE):
						renderfx &= ~shared.RF_SHELL_HALF_DAM
				
			if renderfx & shared.RF_SHELL_DOUBLE:
			
				if filesystem.Developer_searchpath(2) == 2:
				
					# lose the yellow shell if we have a red, blue, or green shell
					if renderfx & (shared.RF_SHELL_RED|shared.RF_SHELL_BLUE|shared.RF_SHELL_GREEN):
						renderfx &= ~shared.RF_SHELL_DOUBLE
					# if we have a red shell, turn it to purple by adding blue
					if renderfx & shared.RF_SHELL_RED:
						renderfx |= shared.RF_SHELL_BLUE
					# if we have a blue shell (and not a red shell), turn it to cyan by adding green
					elif renderfx & shared.RF_SHELL_BLUE:
						# go to green if it's on already, otherwise do cyan (flash green)
						if renderfx & shared.RF_SHELL_GREEN:
							renderfx &= ~shared.RF_SHELL_BLUE
						else:
							renderfx |= shared.RF_SHELL_GREEN
				
#			}
			# pmm
			ent.flags = renderfx | shared.RF_TRANSLUCENT
			ent.alpha = 0.30
			cl_view.V_AddEntity (ent)
		
		ent.skin = None		# never use a custom skin on others
		ent.skinnum = 0
		ent.flags = 0
		ent.alpha = 0

		# duplicate for linked models
		if s1.modelindex2:
		
			if s1.modelindex2 == 255:
				# custom weapon
				ci = cl.clientinfo[s1.skinnum & 0xff]
				i = (s1.skinnum >> 8) # 0 is default weapon model
				if not cl_main.cl_vwep.value or i > client_h.MAX_CLIENTWEAPONMODELS - 1:
					i = 0
				ent.model = ci.weaponmodel[i]
				if not ent.model:
					if i != 0:
						ent.model = ci.weaponmodel[0]
					if not ent.model:
						ent.model = cl.baseclientinfo.weaponmodel[0]
				
			else:
				ent.model = cl.model_draw[s1.modelindex2]

			# PMM - check for the defender sphere shell .. make it translucent
			# replaces the previous version which used the high bit on modelindex2 to determine transparency
			if not shared_c.Q_strcasecmp (cl.configstrings[shared.CS_MODELS+(s1.modelindex2)] or "", "models/items/shell/tris.md2"):
			
				ent.alpha = 0.32
				ent.flags = shared.RF_TRANSLUCENT
			
			# pmm

			cl_view.V_AddEntity (ent)

			#PGM - make sure these get reset.
			ent.flags = 0
			ent.alpha = 0
			#PGM
		
		if s1.modelindex3:
		
			ent.model = cl.model_draw[s1.modelindex3]
			cl_view.V_AddEntity (ent)
		
		if s1.modelindex4:
		
			ent.model = cl.model_draw[s1.modelindex4]
			cl_view.V_AddEntity (ent)
		
		if effects & shared.EF_POWERSCREEN:
		
			ent.model = cl_tent.cl_mod_powerscreen
			ent.oldframe = 0
			ent.frame = 0
			ent.flags |= (shared.RF_TRANSLUCENT | shared.RF_SHELL_GREEN)
			ent.alpha = 0.30
			cl_view.V_AddEntity (ent)
		
		# add automatic particle trails
		if effects&~shared.EF_ROTATE:
		
			if effects & shared.EF_ROCKET:
			
				cl_fx.CL_RocketTrail (cent.lerp_origin, ent.origin, cent)
				cl_view.V_AddLight (ent.origin, 200, 1, 1, 0)
			
			# PGM - Do not reorder EF_BLASTER and EF_HYPERBLASTER. 
			# EF_BLASTER | EF_TRACKER is a special case for EF_BLASTER2... Cheese!
			elif effects & shared.EF_BLASTER:
			
#				CL_BlasterTrail (cent->lerp_origin, ent.origin);
#PGM
				if effects & shared.EF_TRACKER:	# lame... problematic?
				
					cl_newfx.CL_BlasterTrail2 (cent.lerp_origin, ent.origin)
					cl_view.V_AddLight (ent.origin, 200, 0, 1, 0)		
				
				else:
				
					cl_fx.CL_BlasterTrail (cent.lerp_origin, ent.origin)
					cl_view.V_AddLight (ent.origin, 200, 1, 1, 0)
				
#PGM
			
			elif effects & shared.EF_HYPERBLASTER:
			
				if effects & shared.EF_TRACKER:						# PGM	overloaded for blaster2.
					cl_view.V_AddLight (ent.origin, 200, 0, 1, 0)		# PGM
				else:											# PGM
					cl_view.V_AddLight (ent.origin, 200, 1, 1, 0)
			
			elif effects & shared.EF_GIB:
			
				cl_fx.CL_DiminishingTrail (cent.lerp_origin, ent.origin, cent, effects)
			
			elif effects & shared.EF_GRENADE:
			
				cl_fx.CL_DiminishingTrail (cent.lerp_origin, ent.origin, cent, effects)
			
			elif effects & shared.EF_FLIES:
			
				cl_fx.CL_FlyEffect (cent, ent.origin)
			
			elif effects & shared.EF_BFG:
			
				#static int bfg_lightramp[6] = {300, 400, 600, 300, 150, 75};

				if effects & shared.EF_ANIM_ALLFAST:
				
					cl_fx.CL_BfgParticles (ent)
					i = 200
				
				else:
				
					i = cl_parse.bfg_lightramp[s1.frame]
				
				cl_view.V_AddLight (ent.origin, i, 0, 1, 0)
			
			# RAFAEL
			elif effects & shared.EF_TRAP:
			
				ent.origin[2] += 32
				cl_fx.CL_TrapParticles (ent)
				i = (random.getrandbits(15)%100) + 100
				cl_view.V_AddLight (ent.origin, i, 1, 0.8, 0.1)
			
			elif effects & shared.EF_FLAG1:
			
				cl_fx.CL_FlagTrail (cent.lerp_origin, ent.origin, 242)
				cl_view.V_AddLight (ent.origin, 225, 1, 0.1, 0.1)
			
			elif effects & shared.EF_FLAG2:
			
				cl_fx.CL_FlagTrail (cent.lerp_origin, ent.origin, 115)
				cl_view.V_AddLight (ent.origin, 225, 0.1, 0.1, 1)
			
#======
#ROGUE
			elif effects & shared.EF_TAGTRAIL:
			
				cl_newfx.CL_TagTrail (cent.lerp_origin, ent.origin, 220)
				cl_view.V_AddLight (ent.origin, 225, 1.0, 1.0, 0.0)
			
			elif effects & shared.EF_TRACKERTRAIL:
			
				if effects & shared.EF_TRACKER:
				
					#float intensity;

					intensity = 50 + (500 * (math.sin(cl.time/500.0) + 1.0))
					# FIXME - check out this effect in rendition
					if cl_parse.vidref_val == shared.VIDREF_GL:
						cl_view.V_AddLight (ent.origin, intensity, -1.0, -1.0, -1.0)
					else:
						cl_view.V_AddLight (ent.origin, -1.0 * intensity, 1.0, 1.0, 1.0)
					
				else:
				
					cl_newfx.CL_Tracker_Shell (cent.lerp_origin)
					cl_view.V_AddLight (ent.origin, 155, -1.0, -1.0, -1.0)
				
			elif effects & shared.EF_TRACKER:
			
				cl_newfx.CL_TrackerTrail (cent.lerp_origin, ent.origin, 0)
				# FIXME - check out this effect in rendition
				if cl_parse.vidref_val == shared.VIDREF_GL:
					cl_view.V_AddLight (ent.origin, 200, -1, -1, -1)
				else:
					cl_view.V_AddLight (ent.origin, -200, 1, 1, 1)
			
#ROGUE
#======
			# RAFAEL
			elif effects & shared.EF_GREENGIB:
			
				cl_fx.CL_DiminishingTrail (cent.lerp_origin, ent.origin, cent, effects)				
			
			# RAFAEL
			elif effects & shared.EF_IONRIPPER:
			
				cl_fx.CL_IonripperTrail (cent.lerp_origin, ent.origin)
				cl_view.V_AddLight (ent.origin, 100, 1, 0.5, 0.5)
			
			# RAFAEL
			elif effects & shared.EF_BLUEHYPERBLASTER:
			
				cl_view.V_AddLight (ent.origin, 200, 0, 0, 1)
			
			# RAFAEL
			elif effects & shared.EF_PLASMA:
			
				if effects & shared.EF_ANIM_ALLFAST:
				
					cl_fx.CL_BlasterTrail (cent.lerp_origin, ent.origin)
				
				cl_view.V_AddLight (ent.origin, 130, 1, 0.5, 0.5)
			
		shared.VectorCopy (ent.origin, cent.lerp_origin)
	


def CL_AddViewWeapon (ps, ops):
	if not cl_main.cl_gun.value:
		return
	if ps.fov > 90:
		return

	if ps.gunindex is None:
		return

	gun_index = ps.gunindex
	if gun_index < 0 or gun_index >= len(cl_main.cl.model_draw):
		return

	gun = ref.entity_t()
	gun.model = cl_main.cl.model_draw[gun_index]
	if gun.model is None:
		return

	for i in range(3):
		gun.origin[i] = cl_main.cl.refdef.vieworg[i] + ops.gunoffset[i] + \
			cl_main.cl.lerpfrac * (ps.gunoffset[i] - ops.gunoffset[i])
		gun.angles[i] = cl_main.cl.refdef.viewangles[i] + shared_c.LerpAngle(
			ops.gunangles[i], ps.gunangles[i], cl_main.cl.lerpfrac
		)

	gun.frame = ps.gunframe
	if gun.frame == 0:
		gun.oldframe = 0
	else:
		gun.oldframe = ops.gunframe

	gun.flags = shared.RF_MINLIGHT | shared.RF_DEPTHHACK | shared.RF_WEAPONMODEL
	gun.backlerp = 1.0 - cl_main.cl.lerpfrac
	shared.VectorCopy(gun.origin, gun.oldorigin)
	cl_view.V_AddEntity(gun)


"""
/*
 * Adapts a 4:3 aspect FOV to the current aspect (Hor+)
 */
static inline float
AdaptFov(float fov, float w, float h)
{
	static const float pi = M_PI; /* float instead of double */

	if (w <= 0 || h <= 0)
		return fov;

	/*
	 * Formula:
	 *
	 * fov = 2.0 * atan(width / height * 3.0 / 4.0 * tan(fov43 / 2.0))
	 *
	 * The code below is equivalent but precalculates a few values and
	 * converts between degrees and radians when needed.
	 */
	return (atanf(tanf(fov / 360.0f * pi) * (w / h * 0.75f)) / pi * 360.0f);
}
"""

"""
===============
CL_CalcViewValues

Sets cl_main.cl.refdef view values
===============
"""
def CL_CalcViewValues ():

	"""
	Interpolate entity states and account for prediction to update the view definition.
	"""

	ps = cl_main.cl.frame.playerstate
	frame_index = (cl_main.cl.frame.serverframe - 1) & common_h.UPDATE_MASK
	oldframe = cl_main.cl.frames[frame_index]
	if oldframe.serverframe != cl_main.cl.frame.serverframe - 1 or not oldframe.valid:
		oldframe = cl_main.cl.frame
	ops = oldframe.playerstate

	if abs(ops.pmove.origin[0] - ps.pmove.origin[0]) > 256 * 8 \
		or abs(ops.pmove.origin[1] - ps.pmove.origin[1]) > 256 * 8 \
		or abs(ops.pmove.origin[2] - ps.pmove.origin[2]) > 256 * 8:
		ops = ps

	ent = cl_main.cl_entities[cl_main.cl.playernum + 1]
	lerp = cl_main.cl.lerpfrac

	prediction_allowed = (
		cl_main.cl_predict
		and cl_main.cl_predict.value
		and not (cl_main.cl.frame.playerstate.pmove.pm_flags & shared.PMF_NO_PREDICTION)
	)

	if prediction_allowed:
		backlerp = 1.0 - lerp
		for i in range(3):
			cl_main.cl.refdef.vieworg[i] = (
				cl_main.cl.predicted_origin[i]
				+ ops.viewoffset[i]
				+ cl_main.cl.lerpfrac * (ps.viewoffset[i] - ops.viewoffset[i])
				- backlerp * cl_main.cl.prediction_error[i]
			)

		step_time = cl_main.cl.predicted_step_time or 0
		delta = cl_main.cls.realtime - step_time
		if delta < 100:
			predicted_step = (
				cl_main.cl.predicted_step
				if cl_main.cl.predicted_step is not None
				else 0.0
			)
			cl_main.cl.refdef.vieworg[2] -= predicted_step * (100 - delta) * 0.01
	else:
		for i in range(3):
			cl_main.cl.refdef.vieworg[i] = (
				ops.pmove.origin[i] * 0.125
				+ ops.viewoffset[i]
				+ lerp
				* (
					ps.pmove.origin[i] * 0.125
					+ ps.viewoffset[i]
					- (ops.pmove.origin[i] * 0.125 + ops.viewoffset[i])
				)
			)

	if cl_main.cl.frame.playerstate.pmove.pm_type < shared.pmtype_t.PM_DEAD.value:
		for i in range(3):
			cl_main.cl.refdef.viewangles[i] = cl_main.cl.predicted_angles[i]
	else:
		for i in range(3):
			cl_main.cl.refdef.viewangles[i] = shared_c.LerpAngle(
				ops.viewangles[i], ps.viewangles[i], lerp
			)

	for i in range(3):
		cl_main.cl.refdef.viewangles[i] += shared_c.LerpAngle(
			ops.kick_angles[i], ps.kick_angles[i], lerp
		)

	shared_c.AngleVectors(
		cl_main.cl.refdef.viewangles,
		cl_main.cl.v_forward,
		cl_main.cl.v_right,
		cl_main.cl.v_up,
	)

	cl_main.cl.refdef.fov_x = ops.fov + lerp * (ps.fov - ops.fov)
	cl_main.cl.refdef.blend[:] = ps.blend

	CL_AddViewWeapon (ps, ops)

"""
===============
CL_AddEntities

Emits all entities, particles, and lights to the refresh
===============
"""
def CL_AddEntities ():

	cl = cl_main.cl

	if cl_main.cls.state != client_h.connstate_t.ca_active:
		return

	if cl.time > cl.frame.servertime:
	
		if cl_main.cl_showclamp.value:
			clientserver.Com_Printf ("high clamp {}\n".format(cl.time - cl.frame.servertime))
		cl.time = cl.frame.servertime
		cl.lerpfrac = 1.0
	
	elif cl.time < cl.frame.servertime - 100:
	
		if cl_main.cl_showclamp.value:
			clientserver.Com_Printf ("low clamp {}\n".format(cl.frame.servertime-100 - cl.time))
		cl.time = cl.frame.servertime - 100
		cl.lerpfrac = 0
	
	else:
		cl.lerpfrac = 1.0 - (cl.frame.servertime - cl.time) * 0.01

	if cl_main.cl_timedemo.value:
		cl.lerpfrac = 1.0

#	CL_AddPacketEntities (&cl.frame);
#	CL_AddTEnts ();
#	CL_AddParticles ();
#	CL_AddDLights ();
#	CL_AddLightStyles ();

	CL_CalcViewValues ()
	# PMM - moved this here so the heat beam has the right values for the vieworg, and can lock the beam to the gun
	CL_AddPacketEntities (cl.frame)
#if 0
#	CL_AddProjectiles ();
#endif
	cl_tent.CL_AddTEnts ()
	cl_fx.CL_AddParticles ()
	cl_fx.CL_AddDLights ()
	cl_fx.CL_AddLightStyles ()
"""
/*
 * Called to get the sound spatialization
 */
void
CL_GetEntitySoundVelocity(int ent, vec3_t vel)
{
	centity_t *old;

	if ((ent < 0) || (ent >= cl_numentities))
	{
		VectorClear(vel);
		return;
	}

	old = &cl_entities[ent];

	VectorSubtract(old->current.origin, old->prev.origin, vel);
}
"""

"""
void
CL_GetViewVelocity(vec3_t vel)
{
	// restore value from 12.3 fixed point
	const float scale_factor = 1.0f / 8.0f;

	vel[0] = (float)cl.frame.playerstate.pmove.velocity[0] * scale_factor;
	vel[1] = (float)cl.frame.playerstate.pmove.velocity[1] * scale_factor;
	vel[2] = (float)cl.frame.playerstate.pmove.velocity[2] * scale_factor;
}
"""

