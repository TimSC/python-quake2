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

import math

import numpy as np

from client import ref
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common.shared import rand
from common import clientserver
from common import cvar
from common import frame
from client import cl_main
from client import cl_view
from client.header import client as client_h
from client.vid import vid
from client import cl_effects
from client import cl_lights
from client import cl_particles
from client import cl_tempentities

"""
#include <math.h>
#include "header/client.h"
"""

pi = math.pi #static const float

LASERLERP_NSKIPS	= 2
CL_AddPacketEntities_game = None #static const cvar_t *, in CL_AddPacketEntities
bfg_lightramp = [300, 400, 600, 300, 150, 75] #static int [6], in CL_AddPacketEntities

def CL_AddPacketEntities(frame: client_h.frame_t): #frame_t * (static)

	"""
	entity_t ent = {0};
	entity_state_t *s1;
	float autorotate;
	int i;
	int pnum;
	centity_t *cent;
	int autoanim;
	clientinfo_t *ci;
	unsigned int effects, renderfx;
	"""
	global CL_AddPacketEntities_game

	ent = ref.entity_t() # it is reused for every entity, as in the C
	cl = cl_main.cl

	# To distinguish baseq2, xatrix and rogue.
	if CL_AddPacketEntities_game is None:

		CL_AddPacketEntities_game = cvar.Cvar_Get("game",  "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)

	game = CL_AddPacketEntities_game

	# bonus items rotate at a fixed rate
	autorotate = shared_c.anglemod(cl.time * 0.1)

	# brush models can auto animate their frames
	autoanim = int(2 * cl.time / 1000)

	for pnum in range(frame.num_entities):

		s1 = cl_main.cl_parse_entities[(frame.parse_entities +
				pnum) & (client_h.MAX_PARSE_ENTITIES - 1)]

		if (s1.number < 0) or (s1.number >= cl_main.cl_numentities):

			continue


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

			ent.frame = int(cl.time / 100)


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


		if effects & shared.EF_DOUBLE:

			effects &= ~shared.EF_DOUBLE
			effects |= shared.EF_COLOR_SHELL
			renderfx |= shared.RF_SHELL_DOUBLE


		if effects & shared.EF_HALF_DAMAGE:

			effects &= ~shared.EF_HALF_DAMAGE
			effects |= shared.EF_COLOR_SHELL
			renderfx |= shared.RF_SHELL_HALF_DAM


		ent.oldframe = cent.prev.frame
		ent.backlerp = 1.0 - cl.lerpfrac

		if ((renderfx & shared.RF_BEAM) and
			(cl.frame.serverframe - cent.serverframe_created) >= LASERLERP_NSKIPS):

			for i in range(3):

				ent.origin[i] = cent.prev.origin[i] + (cl.lerpfrac *
						(cent.current.origin[i] - cent.prev.origin[i]))
				ent.oldorigin[i] = cent.prev.old_origin[i] + (cl.lerpfrac *
						(cent.current.old_origin[i] - cent.prev.old_origin[i]))


		elif renderfx & (shared.RF_BEAM | shared.RF_FRAMELERP):

			# step origin discretely, because the
			# frames do the animation properly
			shared.VectorCopy(cent.current.origin, ent.origin)
			shared.VectorCopy(cent.current.old_origin, ent.oldorigin)

		else:

			# interpolate origin
			for i in range(3):

				ent.origin[i] = ent.oldorigin[i] = cent.prev.origin[i] + cl.lerpfrac * \
					(cent.current.origin[i] - cent.prev.origin[i])



		# tweak the color of beams
		if renderfx & shared.RF_BEAM:

			ent.alpha = cl_main.cl_laseralpha.value
			if ent.alpha < 0.0:

				ent.alpha = 0.0

			elif ent.alpha > 1.0:

				ent.alpha = 1.0


			# the four beam colors are encoded in 32 bits of skinnum (hack)
			ent.skinnum = (s1.skinnum >> ((rand.randk() % 4) * 8)) & 0xff
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


				if renderfx & shared.RF_USE_DISGUISE:

					if ent.skin is not None:

						# strncmp((char *)ent.skin, ...) compares the image name, the first field of image_t
						if ent.skin.name[:12] == "players/male":

							ent.skin = vid.R_RegisterSkin("players/male/disguise.pcx")
							ent.model = vid.R_RegisterModel("players/male/tris.md2")

						elif ent.skin.name[:14] == "players/female":

							ent.skin = vid.R_RegisterSkin("players/female/disguise.pcx")
							ent.model = vid.R_RegisterModel("players/female/tris.md2")

						elif ent.skin.name[:14] == "players/cyborg":

							ent.skin = vid.R_RegisterSkin("players/cyborg/disguise.pcx")
							ent.model = vid.R_RegisterModel("players/cyborg/tris.md2")




			else:

				ent.skinnum = s1.skinnum
				ent.skin = None
				ent.model = cl.model_draw[s1.modelindex]



		# only used for black hole model right now
		if renderfx & shared.RF_TRANSLUCENT and not (renderfx & shared.RF_BEAM):

			ent.alpha = 0.70


		# render effects (fullbright, translucent, etc)
		if effects & shared.EF_COLOR_SHELL:

			ent.flags = 0 # renderfx go on color shell entity

		else:

			ent.flags = renderfx


		# calculate angles
		if effects & shared.EF_ROTATE:

			# some bonus items auto-rotate
			ent.angles[0] = 0
			ent.angles[1] = autorotate
			ent.angles[2] = 0

		elif effects & shared.EF_SPINNINGLIGHTS:

			ent.angles[0] = 0
			ent.angles[1] = shared_c.anglemod(int(cl.time / 2)) + s1.angles[1]
			ent.angles[2] = 180

			"""
			vec3_t forward;
			vec3_t start;
			"""
			forward = np.zeros((3,), dtype=np.float32)
			start = np.zeros((3,), dtype=np.float32)

			shared_c.AngleVectors(ent.angles, forward, None, None)
			shared_c.VectorMA(ent.origin, 64, forward, start)
			cl_view.V_AddLight(start, 100, 1, 0, 0)


		else:

			# interpolate angles
			"""
			float a1, a2;
			"""

			for i in range(3):

				a1 = cent.current.angles[i]
				a2 = cent.prev.angles[i]
				ent.angles[i] = shared_c.LerpAngle(a2, a1, cl.lerpfrac)



		if s1.number == cl.playernum + 1:

			ent.flags |= shared.RF_VIEWERMODEL

			if effects & shared.EF_FLAG1:

				cl_view.V_AddLight(ent.origin, 225, 1.0, 0.1, 0.1)


			elif effects & shared.EF_FLAG2:

				cl_view.V_AddLight(ent.origin, 225, 0.1, 0.1, 1.0)


			elif effects & shared.EF_TAGTRAIL:

				cl_view.V_AddLight(ent.origin, 225, 1.0, 1.0, 0.0)


			elif effects & shared.EF_TRACKERTRAIL:

				cl_view.V_AddLight(ent.origin, 225, -1.0, -1.0, -1.0)


			continue


		# if set to invisible, skip
		if not s1.modelindex:

			continue


		if effects & shared.EF_BFG:

			ent.flags |= shared.RF_TRANSLUCENT
			ent.alpha = 0.30


		if effects & shared.EF_PLASMA:

			ent.flags |= shared.RF_TRANSLUCENT
			ent.alpha = 0.6


		if effects & shared.EF_SPHERETRANS:

			ent.flags |= shared.RF_TRANSLUCENT

			if effects & shared.EF_TRACKERTRAIL:

				ent.alpha = 0.6


			else:

				ent.alpha = 0.3



		# add to refresh list
		cl_view.V_AddEntity(ent)

		# color shells generate a seperate entity for the main model
		if effects & shared.EF_COLOR_SHELL:

			# all of the solo colors are fine.  we need to catch any of
			# the combinations that look bad (double & half) and turn
			# them into the appropriate color, and make double/quad
			# something special
			if renderfx & shared.RF_SHELL_HALF_DAM:

				if game.string == "rogue":

					# ditch the half damage shell if any of red, blue, or double are on
					if renderfx & (shared.RF_SHELL_RED | shared.RF_SHELL_BLUE | shared.RF_SHELL_DOUBLE):

						renderfx &= ~shared.RF_SHELL_HALF_DAM




			if renderfx & shared.RF_SHELL_DOUBLE:

				if game.string == "rogue":

					# lose the yellow shell if we have a red, blue, or green shell
					if renderfx & (shared.RF_SHELL_RED | shared.RF_SHELL_BLUE | shared.RF_SHELL_GREEN):

						renderfx &= ~shared.RF_SHELL_DOUBLE


					# if we have a red shell, turn it to purple by adding blue
					if renderfx & shared.RF_SHELL_RED:

						renderfx |= shared.RF_SHELL_BLUE


					# if we have a blue shell (and not a red shell),
					# turn it to cyan by adding green
					elif renderfx & shared.RF_SHELL_BLUE:

						# go to green if it's on already,
						# otherwise do cyan (flash green)
						if renderfx & shared.RF_SHELL_GREEN:

							renderfx &= ~shared.RF_SHELL_BLUE


						else:

							renderfx |= shared.RF_SHELL_GREEN





			ent.flags = renderfx | shared.RF_TRANSLUCENT
			ent.alpha = 0.30
			cl_view.V_AddEntity(ent)


		ent.skin = None # never use a custom skin on others
		ent.skinnum = 0
		ent.flags = 0
		ent.alpha = 0

		# duplicate for linked models
		if s1.modelindex2:

			if s1.modelindex2 == 255:

				# custom weapon
				ci = cl.clientinfo[s1.skinnum & 0xff]
				i = (s1.skinnum >> 8) # 0 is default weapon model

				if not cl_main.cl_vwep.value or (i > client_h.MAX_CLIENTWEAPONMODELS - 1):

					i = 0


				ent.model = ci.weaponmodel[i]

				if not ent.model:

					if i != 0:

						ent.model = ci.weaponmodel[0]


					if not ent.model:

						ent.model = cl.baseclientinfo.weaponmodel[0]



			else:

				ent.model = cl.model_draw[s1.modelindex2]


			# check for the defender sphere shell and make it translucent
			if not shared_c.Q_strcasecmp(cl.configstrings[shared.CS_MODELS + (s1.modelindex2)],
						"models/items/shell/tris.md2"):

				ent.alpha = 0.32
				ent.flags = shared.RF_TRANSLUCENT


			cl_view.V_AddEntity(ent)

			ent.flags = 0
			ent.alpha = 0


		if s1.modelindex3:

			ent.model = cl.model_draw[s1.modelindex3]
			cl_view.V_AddEntity(ent)


		if s1.modelindex4:

			ent.model = cl.model_draw[s1.modelindex4]
			cl_view.V_AddEntity(ent)


		if effects & shared.EF_POWERSCREEN:

			ent.model = cl_tempentities.CL_PowerScreenModel()
			ent.oldframe = 0
			ent.frame = 0
			ent.flags |= (shared.RF_TRANSLUCENT | shared.RF_SHELL_GREEN)
			ent.alpha = 0.30
			cl_view.V_AddEntity(ent)


		# add automatic particle trails
		if effects & ~shared.EF_ROTATE:

			if effects & shared.EF_ROCKET:

				cl_effects.CL_RocketTrail(cent.lerp_origin, ent.origin, cent)

				if cl_main.cl_r1q2_lightstyle.value:

					cl_view.V_AddLight(ent.origin, 200, 1, 0.23, 0)

				else:

					cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)



			# Do not reorder EF_BLASTER and EF_HYPERBLASTER.
			# EF_BLASTER | EF_TRACKER is a special case for
			# EF_BLASTER2
			elif effects & shared.EF_BLASTER:

				if effects & shared.EF_TRACKER:

					cl_effects.CL_BlasterTrail2(cent.lerp_origin, ent.origin)
					cl_view.V_AddLight(ent.origin, 200, 0, 1, 0)

				else:

					cl_effects.CL_BlasterTrail(cent.lerp_origin, ent.origin)
					cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)


			elif effects & shared.EF_HYPERBLASTER:

				if effects & shared.EF_TRACKER:

					cl_view.V_AddLight(ent.origin, 200, 0, 1, 0)

				else:

					cl_view.V_AddLight(ent.origin, 200, 1, 1, 0)


			elif effects & shared.EF_GIB:

				cl_effects.CL_DiminishingTrail(cent.lerp_origin, ent.origin,
						cent, effects)

			elif effects & shared.EF_GRENADE:

				cl_effects.CL_DiminishingTrail(cent.lerp_origin, ent.origin,
						cent, effects)

			elif effects & shared.EF_FLIES:

				cl_effects.CL_FlyEffect(cent, ent.origin)

			elif effects & shared.EF_BFG:

				#static int bfg_lightramp[6] = {300, 400, 600, 300, 150, 75};

				if effects & shared.EF_ANIM_ALLFAST:

					cl_effects.CL_BfgParticles(ent)
					i = 200

				else:

					i = bfg_lightramp[s1.frame]


				cl_view.V_AddLight(ent.origin, i, 0, 1, 0)

			elif effects & shared.EF_TRAP:

				ent.origin[2] += 32
				cl_effects.CL_TrapParticles(ent)
				i = (rand.randk() % 100) + 100
				cl_view.V_AddLight(ent.origin, i, 1, 0.8, 0.1)

			elif effects & shared.EF_FLAG1:

				cl_effects.CL_FlagTrail(cent.lerp_origin, ent.origin, 242)
				cl_view.V_AddLight(ent.origin, 225, 1, 0.1, 0.1)

			elif effects & shared.EF_FLAG2:

				cl_effects.CL_FlagTrail(cent.lerp_origin, ent.origin, 115)
				cl_view.V_AddLight(ent.origin, 225, 0.1, 0.1, 1)

			elif effects & shared.EF_TAGTRAIL:

				cl_effects.CL_TagTrail(cent.lerp_origin, ent.origin, 220)
				cl_view.V_AddLight(ent.origin, 225, 1.0, 1.0, 0.0)

			elif effects & shared.EF_TRACKERTRAIL:

				if effects & shared.EF_TRACKER:

					"""
					float intensity;
					"""

					intensity = 50 + (500 * (math.sin(cl.time / 500.0) + 1.0))
					cl_view.V_AddLight(ent.origin, intensity, -1.0, -1.0, -1.0)

				else:

					cl_effects.CL_Tracker_Shell(cent.lerp_origin)
					cl_view.V_AddLight(ent.origin, 155, -1.0, -1.0, -1.0)


			elif effects & shared.EF_TRACKER:

				cl_effects.CL_TrackerTrail(cent.lerp_origin, ent.origin, 0)
				cl_view.V_AddLight(ent.origin, 200, -1, -1, -1)

			elif effects & shared.EF_IONRIPPER:

				cl_effects.CL_IonripperTrail(cent.lerp_origin, ent.origin)
				cl_view.V_AddLight(ent.origin, 100, 1, 0.5, 0.5)

			elif effects & shared.EF_BLUEHYPERBLASTER:

				cl_view.V_AddLight(ent.origin, 200, 0, 0, 1)

			elif effects & shared.EF_PLASMA:

				if effects & shared.EF_ANIM_ALLFAST:

					cl_effects.CL_BlasterTrail(cent.lerp_origin, ent.origin)


				cl_view.V_AddLight(ent.origin, 130, 1, 0.5, 0.5)



		shared.VectorCopy(ent.origin, cent.lerp_origin)

	


def CL_AddViewWeapon(ps: shared.player_state_t, ops: shared.player_state_t): #player_state_t *, player_state_t * (static)

	"""
	entity_t gun = {0}; /* view model */
	int i;
	"""
	gun = ref.entity_t() # view model

	# allow the gun to be completely removed
	if not cl_main.cl_gun.value:

		return


	# don't draw gun if in wide angle view and drawing not forced
	if ps.fov > 90:

		if cl_main.cl_gun.value < 2:

			return



	if cl_view.gun_model:

		gun.model = cl_view.gun_model


	else:

		gun.model = cl_main.cl.model_draw[ps.gunindex]


	if not gun.model:

		return


	# set up gun position
	for i in range(3):

		gun.origin[i] = cl_main.cl.refdef.vieworg[i] + ops.gunoffset[i] \
			+ cl_main.cl.lerpfrac * (ps.gunoffset[i] - ops.gunoffset[i])
		gun.angles[i] = cl_main.cl.refdef.viewangles[i] + shared_c.LerpAngle(ops.gunangles[i],
			ps.gunangles[i], cl_main.cl.lerpfrac)


	if cl_view.gun_frame:

		gun.frame = cl_view.gun_frame
		gun.oldframe = cl_view.gun_frame

	else:

		gun.frame = ps.gunframe

		if gun.frame == 0:

			gun.oldframe = 0 # just changed weapons, don't lerp from old

		else:

			gun.oldframe = ops.gunframe



	gun.flags = shared.RF_MINLIGHT | shared.RF_DEPTHHACK | shared.RF_WEAPONMODEL
	gun.backlerp = 1.0 - cl_main.cl.lerpfrac
	shared.VectorCopy(gun.origin, gun.oldorigin) # don't lerp at all
	cl_view.V_AddEntity(gun)



"""
 * Adapts a 4:3 aspect FOV to the current aspect (Hor+)

"""
def AdaptFov(fov, w, h): #float, float, float (returns static inline float)
	# FIXME c2py: unresolved atanf, tanf

	"""
	static const float pi = M_PI;
	"""

	# float instead of double
	if w <= 0 or h <= 0:

		return fov


	# Formula:
	# fov = 2.0 * atan(width / height * 3.0 / 4.0 * tan(fov43 / 2.0))
	# The code below is equivalent but precalculates a few values and
	# converts between degrees and radians when needed.
	return (math.atan(math.tan(fov / 360.0 * pi) * (w / h * 0.75)) / pi * 360.0)

"""
===============
CL_CalcViewValues

Sets cl_main.cl.refdef view values
===============
"""
def CL_CalcViewValues(): #
	# FIXME c2py: unresolved abs, cl_main.cl_kickangles, cl_main.horplus

	"""
	int i;
	float lerp, backlerp, ifov;
	frame_t *oldframe;
	player_state_t *ps, *ops;
	"""

	# find the previous frame to interpolate from
	ps = cl_main.cl.frame.playerstate
	i = (cl_main.cl.frame.serverframe - 1) & common_h.UPDATE_MASK
	oldframe = cl_main.cl.frames[i]
	if (oldframe.serverframe != cl_main.cl.frame.serverframe - 1) or not oldframe.valid:

		oldframe = cl_main.cl.frame
		# previous frame was dropped or invalid


	ops = oldframe.playerstate
	# see if the player entity was teleported this frame
	if (abs(ops.pmove.origin[0] - ps.pmove.origin[0]) > 256 * 8) or (abs(ops.pmove.origin[1] - ps.pmove.origin[1]) > 256 * 8) or (abs(ops.pmove.origin[2] - ps.pmove.origin[2]) > 256 * 8):

		ops = ps
		# don't interpolate


	if cl_main.cl_paused.value:

		lerp = 1.0

	else:

		lerp = cl_main.cl.lerpfrac


	# calculate the origin
	if (cl_main.cl_predict.value) and not (cl_main.cl.frame.playerstate.pmove.pm_flags & shared.PMF_NO_PREDICTION):

		# use predicted values
		#unsigned delta;
		backlerp = 1.0 - lerp
		for i in range(3):

			cl_main.cl.refdef.vieworg[i] = cl_main.cl.predicted_origin[i] + ops.viewoffset[i] + cl_main.cl.lerpfrac * (ps.viewoffset[i] - ops.viewoffset[i]) - backlerp * cl_main.cl.prediction_error[i]


		# smooth out stair climbing
		delta = cl_main.cls.realtime - cl_main.cl.predicted_step_time
		if delta < 100:

			cl_main.cl.refdef.vieworg[2] -= cl_main.cl.predicted_step * (100 - delta) * 0.01


	else:

		# just use interpolated values
		for i in range(3):

			cl_main.cl.refdef.vieworg[i] = ops.pmove.origin[i] * 0.125 + ops.viewoffset[i] + lerp * (ps.pmove.origin[i] * 0.125 + ps.viewoffset[i] - (ops.pmove.origin[i] * 0.125 + ops.viewoffset[i]))


	# if not running a demo or on a locked frame, add the local angle movement
	if cl_main.cl.frame.playerstate.pmove.pm_type < shared.pmtype_t.PM_DEAD.value: # pm_type is the int read from the message

		# use predicted values
		for i in range(3):

			cl_main.cl.refdef.viewangles[i] = cl_main.cl.predicted_angles[i]


	else:

		# just use interpolated values
		for i in range(3):

			cl_main.cl.refdef.viewangles[i] = shared_c.LerpAngle(ops.viewangles[i], ps.viewangles[i], lerp)


	if cl_main.cl_kickangles.value:

		for i in range(3):

			cl_main.cl.refdef.viewangles[i] += shared_c.LerpAngle(ops.kick_angles[i], ps.kick_angles[i], lerp)


	shared_c.AngleVectors(cl_main.cl.refdef.viewangles, cl_main.cl.v_forward, cl_main.cl.v_right, cl_main.cl.v_up)
	# interpolate field of view
	ifov = ops.fov + lerp * (ps.fov - ops.fov)
	if cl_main.horplus.value:

		cl_main.cl.refdef.fov_x = AdaptFov(ifov, cl_main.cl.refdef.width, cl_main.cl.refdef.height)

	else:

		cl_main.cl.refdef.fov_x = ifov


	# don't interpolate blend color
	for i in range(4):

		cl_main.cl.refdef.blend[i] = ps.blend[i]


	# add the weapon
	CL_AddViewWeapon(ps, ops)

"""
===============
CL_AddEntities

Emits all entities, particles, and lights to the refresh
===============
"""
def CL_AddEntities(): #

	if cl_main.cls.state != client_h.connstate_t.ca_active:

		return


	if cl_main.cl.time > cl_main.cl.frame.servertime:

		if cl_main.cl_showclamp.value:

			clientserver.Com_Printf("high clamp %i\n", cl_main.cl.time - cl_main.cl.frame.servertime)


		cl_main.cl.time = cl_main.cl.frame.servertime
		cl_main.cl.lerpfrac = 1.0

	elif cl_main.cl.time < cl_main.cl.frame.servertime - 100:

		if cl_main.cl_showclamp.value:

			clientserver.Com_Printf("low clamp %i\n", cl_main.cl.frame.servertime - 100 - cl_main.cl.time)


		cl_main.cl.time = cl_main.cl.frame.servertime - 100
		cl_main.cl.lerpfrac = 0

	else:

		cl_main.cl.lerpfrac = 1.0 - (cl_main.cl.frame.servertime - cl_main.cl.time) * 0.01


	if frame.cl_timedemo.value:

		cl_main.cl.lerpfrac = 1.0


	CL_CalcViewValues()
	CL_AddPacketEntities(cl_main.cl.frame)
	cl_tempentities.CL_AddTEnts()
	cl_particles.CL_AddParticles()
	cl_lights.CL_AddDLights()
	cl_lights.CL_AddLightStyles()
"""
 * Called to get the sound spatialization

"""
def CL_GetEntitySoundVelocity(ent, vel): #int, vec3_t
	# FIXME c2py: unresolved cl_main.cl_numentities

	"""
	centity_t *old;
	"""

	if (ent < 0) or (ent >= cl_main.cl_numentities):

		shared.VectorClear(vel)
		return


	old = cl_main.cl_entities[ent]
	shared.VectorSubtract(old.current.origin, old.prev.origin, vel)

def CL_GetViewVelocity(vel): #vec3_t

	"""
	const float scale_factor = 1.0f / 8.0f;
	"""
	scale_factor = 1.0 / 8.0

	# restore value from 12.3 fixed point
	vel[0] = cl_main.cl.frame.playerstate.pmove.velocity[0] * scale_factor
	vel[1] = cl_main.cl.frame.playerstate.pmove.velocity[1] * scale_factor
	vel[2] = cl_main.cl.frame.playerstate.pmove.velocity[2] * scale_factor

