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

The "camera" through which the player looks into the game.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

import math
import numpy as np
from game import g_main, g_utils
from game import g_combat, g_items, g_ai
from game.header.local import DAMAGE_TIME, FALL_TIME, DAMAGE_NO_ARMOR, POWER_ARMOR_SCREEN, POWER_ARMOR_SHIELD, PNOISE_SELF, MOD_WATER, MOD_SLIME, MOD_LAVA, MOD_FALLING, ANIM_BASIC, ANIM_WAVE, ANIM_JUMP, ANIM_PAIN, ANIM_DEATH, ANIM_REVERSE, MOVETYPE_NOCLIP
from common.header.shared import RDF_UNDERWATER, CONTENTS_SOLID, CONTENTS_LAVA, CONTENTS_SLIME, CONTENTS_WATER, CHAN_VOICE, CHAN_BODY, CHAN_ITEM, CHAN_AUTO, ATTN_NORM, ATTN_STATIC, PMF_DUCKED, ROLL, PITCH, YAW, DotProduct, VectorClear, VectorCopy, VectorAdd, VectorSet, EF_COLOR_SHELL, EF_POWERSCREEN, EF_QUAD, EF_PENT, RF_SHELL_RED, RF_SHELL_GREEN, RF_SHELL_BLUE, RF_IR_VISIBLE, DF_NO_FALLING, EV_FOOTSTEP, EV_FALLSHORT, EV_FALL, EV_FALLFAR, STAT_FLASHES
from common.shared.shared import VectorMA, VectorNormalize, AngleVectors, vec3_origin
from game.header import local
from game.monster.misc import player as player_h
from game import g_items
from game.player import hud as p_hud
from game.player import weapon as p_weapon

"""
#include "../header/local.h"
#include "../monster/misc/player.h"
"""

current_player = None #edict_t *
current_client = None #gclient_t *

forward = np.zeros((3,), dtype=np.float32)
right = np.zeros((3,), dtype=np.float32)
up = np.zeros((3,), dtype=np.float32)
xyspeed = 0.0

bobmove = 0.0
bobcycle = 0 #int
bobfracsin = 0.0

_pain_anim_i = 0


"""

#include "g_local.h"
#include "m_player.h"
"""

def SV_CalcRoll (angles, velocity): #vec3_t, vec3_t
	side = DotProduct (velocity, right)
	sign = -1 if side < 0 else 1
	side = abs(side)

	value = float(g_main.sv_rollangle.value)

	if side < float(g_main.sv_rollspeed.value):
		side = side * value / float(g_main.sv_rollspeed.value)
	else:
		side = value

	return side*sign


def P_DamageFeedback (player): #edict_t *
	global _pain_anim_i

	if not player:

		return


	# death/gib sound is now aggregated and played here
	if player.sounds:

		g_main.gi.sound (player, CHAN_VOICE, player.sounds, 1, ATTN_NORM, 0)
		player.sounds = 0


	client = player.client

	power_color = np.array([0.0, 1.0, 0.0], dtype=np.float32)
	acolor = np.array([1.0, 1.0, 1.0], dtype=np.float32)
	bcolor = np.array([1.0, 0.0, 0.0], dtype=np.float32)
	v = np.zeros((3,), dtype=np.float32)

	# flash the backgrounds behind the status numbers
	client.ps.stats[STAT_FLASHES] = 0
	if client.damage_blood:
		client.ps.stats[STAT_FLASHES] |= 1
	if (client.damage_armor and not (player.flags & local.FL_GODMODE)
		and (client.invincible_framenum <= g_main.level.framenum)):
		client.ps.stats[STAT_FLASHES] |= 2

	# total points of damage shot at the player this frame
	count = client.damage_blood + client.damage_armor + client.damage_parmor
	if count == 0:
		return		# didn't take any damage

	# start a pain animation if still in the player model
	if client.anim_priority < ANIM_PAIN and player.s.modelindex == 255:
		client.anim_priority = ANIM_PAIN
		if client.ps.pmove.pm_flags & PMF_DUCKED:
			player.s.frame = player_h.FRAME_crpain1-1
			client.anim_end = player_h.FRAME_crpain4
		else:
			_pain_anim_i = (_pain_anim_i+1)%3
			if _pain_anim_i == 0:
				player.s.frame = player_h.FRAME_pain101-1
				client.anim_end = player_h.FRAME_pain104
			elif _pain_anim_i == 1:
				player.s.frame = player_h.FRAME_pain201-1
				client.anim_end = player_h.FRAME_pain204
			elif _pain_anim_i == 2:
				player.s.frame = player_h.FRAME_pain301-1
				client.anim_end = player_h.FRAME_pain304

	realcount = count
	if count < 10:
		count = 10		# always make a visible effect

	# play an apropriate pain sound
	if ((g_main.level.time > player.pain_debounce_time)
		and not (player.flags & local.FL_GODMODE)
		and (client.invincible_framenum <= g_main.level.framenum)
		and player.health > 0):
		r = 1 + (rand.randk()&1)
		player.pain_debounce_time = g_main.level.time + 0.7
		if player.health < 25:
			l = 25
		elif player.health < 50:
			l = 50
		elif player.health < 75:
			l = 75
		else:
			l = 100
		g_main.gi.sound (player, CHAN_VOICE, g_main.gi.soundindex("*pain%i_%i.wav" % (l, r)), 1, ATTN_NORM, 0)

	# the total alpha of the blend is always proportional to count
	if client.damage_alpha < 0:
		client.damage_alpha = 0
	client.damage_alpha += count*0.01
	if client.damage_alpha < 0.2:
		client.damage_alpha = 0.2
	if client.damage_alpha > 0.6:
		client.damage_alpha = 0.6		# don't go too saturated

	# the color of the blend will vary based on how much was absorbed
	# by different armors
	VectorClear (v)
	if client.damage_parmor:
		VectorMA (v, client.damage_parmor/realcount, power_color, v)
	if client.damage_armor:
		VectorMA (v, client.damage_armor/realcount, acolor, v)
	if client.damage_blood:
		VectorMA (v, client.damage_blood/realcount, bcolor, v)
	VectorCopy (v, client.damage_blend)

	# calculate view angle kicks
	kick = abs(client.damage_knockback)
	if kick and player.health > 0:		# kick of 0 means no view adjust at all
		kick = kick * 100 / player.health

		if kick < count*0.5:
			kick = count*0.5
		if kick > 50:
			kick = 50

		v = client.damage_from - player.s.origin
		VectorNormalize (v)

		side = DotProduct (v, right)
		client.v_dmg_roll = kick*side*0.3

		side = -DotProduct (v, forward)
		client.v_dmg_pitch = kick*side*0.3

		client.v_dmg_time = g_main.level.time + DAMAGE_TIME

	# clear totals
	client.damage_blood = 0
	client.damage_armor = 0
	client.damage_parmor = 0
	client.damage_knockback = 0


def SV_CalcViewOffset (ent): #edict_t *
	v = np.zeros((3,), dtype=np.float32)

	# base angles
	angles = ent.client.ps.kick_angles

	# if dead, fix the angle and don't add any kick
	if ent.deadflag:
		VectorClear (angles)

		ent.client.ps.viewangles[ROLL] = 40
		ent.client.ps.viewangles[PITCH] = -15
		ent.client.ps.viewangles[YAW] = ent.client.killer_yaw
	else:
		# add angles based on weapon kick
		VectorCopy (ent.client.kick_angles, angles)

		# add angles based on damage kick
		ratio = (ent.client.v_dmg_time - g_main.level.time) / DAMAGE_TIME
		if ratio < 0:
			ratio = 0
			ent.client.v_dmg_pitch = 0
			ent.client.v_dmg_roll = 0
		angles[PITCH] += ratio * ent.client.v_dmg_pitch
		angles[ROLL] += ratio * ent.client.v_dmg_roll

		# add pitch based on fall kick
		ratio = (ent.client.fall_time - g_main.level.time) / FALL_TIME
		if ratio < 0:
			ratio = 0
		angles[PITCH] += ratio * ent.client.fall_value

		# add angles based on velocity
		delta = DotProduct (ent.velocity, forward)
		angles[PITCH] += delta*float(g_main.run_pitch.value)

		delta = DotProduct (ent.velocity, right)
		angles[ROLL] += delta*float(g_main.run_roll.value)

		# add angles based on bob
		delta = bobfracsin * float(g_main.bob_pitch.value) * xyspeed
		if ent.client.ps.pmove.pm_flags & PMF_DUCKED:
			delta *= 6		# crouching
		angles[PITCH] += delta
		delta = bobfracsin * float(g_main.bob_roll.value) * xyspeed
		if ent.client.ps.pmove.pm_flags & PMF_DUCKED:
			delta *= 6		# crouching
		if bobcycle & 1:
			delta = -delta
		angles[ROLL] += delta

	# base origin
	VectorClear (v)

	# add view height
	v[2] += ent.viewheight

	# add fall height
	ratio = (ent.client.fall_time - g_main.level.time) / FALL_TIME
	if ratio < 0:
		ratio = 0
	v[2] -= ratio * ent.client.fall_value * 0.4

	# add bob height
	bob = bobfracsin * xyspeed * float(g_main.bob_up.value)
	if bob > 6:
		bob = 6
	v[2] += bob

	# add kick offset
	VectorAdd (v, ent.client.kick_origin, v)

	# absolutely bound offsets
	# so the view can never be outside the player box
	if v[0] < -14:
		v[0] = -14
	elif v[0] > 14:
		v[0] = 14
	if v[1] < -14:
		v[1] = -14
	elif v[1] > 14:
		v[1] = 14
	if v[2] < -22:
		v[2] = -22
	elif v[2] > 30:
		v[2] = 30

	VectorCopy (v, ent.client.ps.viewoffset)


def SV_CalcGunOffset (ent): #edict_t *
	# gun angles from bobbing
	if not ent:

		return


	ent.client.ps.gunangles[ROLL] = xyspeed * bobfracsin * 0.005
	ent.client.ps.gunangles[YAW] = xyspeed * bobfracsin * 0.01
	if bobcycle & 1:
		ent.client.ps.gunangles[ROLL] = -ent.client.ps.gunangles[ROLL]
		ent.client.ps.gunangles[YAW] = -ent.client.ps.gunangles[YAW]

	ent.client.ps.gunangles[PITCH] = xyspeed * bobfracsin * 0.005

	# gun angles from delta movement
	for i in range(3):
		delta = ent.client.oldviewangles[i] - ent.client.ps.viewangles[i]
		if delta > 180:
			delta -= 360
		if delta < -180:
			delta += 360
		if delta > 45:
			delta = 45
		if delta < -45:
			delta = -45
		if i == YAW:
			ent.client.ps.gunangles[ROLL] += 0.1*delta
		ent.client.ps.gunangles[i] += 0.2 * delta

	# gun height
	VectorClear (ent.client.ps.gunoffset)

	# gun_x / gun_y / gun_z are development tools
	for i in range(3):
		ent.client.ps.gunoffset[i] += forward[i]*float(g_main.gun_y.value)
		ent.client.ps.gunoffset[i] += right[i]*float(g_main.gun_x.value)
		ent.client.ps.gunoffset[i] += up[i]*(-float(g_main.gun_z.value))


def SV_AddBlend (r, g, b, a, v_blend): #float, float, float, float, float *
	if v_blend is None:

		return


	a2, a3 = 0.0, 0.0

	if a <= 0:
		return
	a2 = v_blend[3] + (1-v_blend[3])*a	# new total alpha
	a3 = v_blend[3]/a2		# fraction of color from old

	v_blend[0] = v_blend[0]*a3 + r*(1-a3)
	v_blend[1] = v_blend[1]*a3 + g*(1-a3)
	v_blend[2] = v_blend[2]*a3 + b*(1-a3)
	v_blend[3] = a2


def SV_CalcBlend (ent): #edict_t *
	if not ent:

		return


	vieworg = np.zeros((3,), dtype=np.float32)

	ent.client.ps.blend[0] = ent.client.ps.blend[1] = \
		ent.client.ps.blend[2] = ent.client.ps.blend[3] = 0

	# add for contents
	VectorAdd (ent.s.origin, ent.client.ps.viewoffset, vieworg)
	contents = g_main.gi.pointcontents (vieworg)
	if contents & (CONTENTS_LAVA|CONTENTS_SLIME|CONTENTS_WATER):
		ent.client.ps.rdflags |= RDF_UNDERWATER
	else:
		ent.client.ps.rdflags &= ~RDF_UNDERWATER

	if contents & (CONTENTS_SOLID|CONTENTS_LAVA):
		SV_AddBlend (1.0, 0.3, 0.0, 0.6, ent.client.ps.blend)
	elif contents & CONTENTS_SLIME:
		SV_AddBlend (0.0, 0.1, 0.05, 0.6, ent.client.ps.blend)
	elif contents & CONTENTS_WATER:
		SV_AddBlend (0.5, 0.3, 0.2, 0.4, ent.client.ps.blend)

	# add for powerups
	if ent.client.quad_framenum > g_main.level.framenum:
		remaining = int(ent.client.quad_framenum - g_main.level.framenum)
		if remaining == 30:		# beginning to fade
			g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("items/damage2.wav"), 1, ATTN_NORM, 0)
		if remaining > 30 or (remaining & 4):
			SV_AddBlend (0, 0, 1, 0.08, ent.client.ps.blend)
	elif ent.client.invincible_framenum > g_main.level.framenum:
		remaining = int(ent.client.invincible_framenum - g_main.level.framenum)
		if remaining == 30:		# beginning to fade
			g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("items/protect2.wav"), 1, ATTN_NORM, 0)
		if remaining > 30 or (remaining & 4):
			SV_AddBlend (1, 1, 0, 0.08, ent.client.ps.blend)
	elif ent.client.enviro_framenum > g_main.level.framenum:
		remaining = int(ent.client.enviro_framenum - g_main.level.framenum)
		if remaining == 30:		# beginning to fade
			g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("items/airout.wav"), 1, ATTN_NORM, 0)
		if remaining > 30 or (remaining & 4):
			SV_AddBlend (0, 1, 0, 0.08, ent.client.ps.blend)
	elif ent.client.breather_framenum > g_main.level.framenum:
		remaining = int(ent.client.breather_framenum - g_main.level.framenum)
		if remaining == 30:		# beginning to fade
			g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("items/airout.wav"), 1, ATTN_NORM, 0)
		if remaining > 30 or (remaining & 4):
			SV_AddBlend (0.4, 1, 0.4, 0.04, ent.client.ps.blend)

	# add for damage
	if ent.client.damage_alpha > 0:
		SV_AddBlend (ent.client.damage_blend[0],ent.client.damage_blend[1],
		ent.client.damage_blend[2], ent.client.damage_alpha, ent.client.ps.blend)

	if ent.client.bonus_alpha > 0:
		SV_AddBlend (0.85, 0.7, 0.3, ent.client.bonus_alpha, ent.client.ps.blend)

	# drop the damage value
	ent.client.damage_alpha -= 0.06
	if ent.client.damage_alpha < 0:
		ent.client.damage_alpha = 0

	# drop the bonus value
	ent.client.bonus_alpha -= 0.1
	if ent.client.bonus_alpha < 0:
		ent.client.bonus_alpha = 0


def P_FallingDamage (ent): #edict_t *
	if not ent:

		return


	dir = np.zeros((3,), dtype=np.float32)
	if ent.s.modelindex != 255:
		return		# not in the player model

	if ent.movetype == MOVETYPE_NOCLIP:
		return

	if ((ent.client.oldvelocity[2] < 0) and (ent.velocity[2] > ent.client.oldvelocity[2]) and (not ent.groundentity)):
		delta = ent.client.oldvelocity[2]
	else:
		if not ent.groundentity:
			return
		delta = ent.velocity[2] - ent.client.oldvelocity[2]
	delta = delta*delta * 0.0001

	# never take falling damage if completely underwater
	if ent.waterlevel == 3:
		return
	if ent.waterlevel == 2:
		delta *= 0.25
	if ent.waterlevel == 1:
		delta *= 0.5

	if delta < 1:
		return

	if delta < 15:
		ent.s.event = EV_FOOTSTEP
		return

	ent.client.fall_value = delta*0.5
	if ent.client.fall_value > 40:
		ent.client.fall_value = 40
	ent.client.fall_time = g_main.level.time + FALL_TIME

	if delta > 30:
		if ent.health > 0:
			if delta >= 55:
				ent.s.event = EV_FALLFAR
			else:
				ent.s.event = EV_FALL
		ent.pain_debounce_time = g_main.level.time		# no normal pain sound
		damage = (delta-30)/2
		if damage < 1:
			damage = 1
		VectorSet (dir, 0, 0, 1)

		if not int(g_main.deathmatch.value) or not (int(g_main.dmflags.value) & DF_NO_FALLING):
			g_combat.T_Damage (ent, g_main.g_edicts[1], g_main.g_edicts[1], dir, ent.s.origin, vec3_origin, damage, 0, 0, MOD_FALLING)
	else:
		ent.s.event = EV_FALLSHORT
		return


def P_WorldEffects ():
	global current_player, current_client
	world = g_main.g_edicts[1]

	if current_player.movetype == MOVETYPE_NOCLIP:
		current_player.air_finished = g_main.level.time + 12		# don't need air
		return

	waterlevel = current_player.waterlevel
	old_waterlevel = current_client.old_waterlevel
	current_client.old_waterlevel = waterlevel

	breather = current_client.breather_framenum > g_main.level.framenum
	envirosuit = current_client.enviro_framenum > g_main.level.framenum

	# if just entered a water volume, play a sound
	if not old_waterlevel and waterlevel:
		p_weapon.PlayerNoise(current_player, current_player.s.origin, PNOISE_SELF)
		if current_player.watertype & CONTENTS_LAVA:
			g_main.gi.sound (current_player, CHAN_BODY, g_main.gi.soundindex("player/lava_in.wav"), 1, ATTN_NORM, 0)
		elif current_player.watertype & CONTENTS_SLIME:
			g_main.gi.sound (current_player, CHAN_BODY, g_main.gi.soundindex("player/watr_in.wav"), 1, ATTN_NORM, 0)
		elif current_player.watertype & CONTENTS_WATER:
			g_main.gi.sound (current_player, CHAN_BODY, g_main.gi.soundindex("player/watr_in.wav"), 1, ATTN_NORM, 0)
		current_player.flags |= local.FL_INWATER

		# clear damage_debounce, so the pain sound will play immediately
		current_player.damage_debounce_time = g_main.level.time - 1

	# if just completely exited a water volume, play a sound
	if old_waterlevel and not waterlevel:
		p_weapon.PlayerNoise(current_player, current_player.s.origin, PNOISE_SELF)
		g_main.gi.sound (current_player, CHAN_BODY, g_main.gi.soundindex("player/watr_out.wav"), 1, ATTN_NORM, 0)
		current_player.flags &= ~local.FL_INWATER

	# check for head just going under water
	if old_waterlevel != 3 and waterlevel == 3:
		g_main.gi.sound (current_player, CHAN_BODY, g_main.gi.soundindex("player/watr_un.wav"), 1, ATTN_NORM, 0)

	# check for head just coming out of water
	if old_waterlevel == 3 and waterlevel != 3:
		if current_player.air_finished < g_main.level.time:
			# gasp for air
			g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("player/gasp1.wav"), 1, ATTN_NORM, 0)
			p_weapon.PlayerNoise(current_player, current_player.s.origin, PNOISE_SELF)
		elif current_player.air_finished < g_main.level.time + 11:
			# just break surface
			g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("player/gasp2.wav"), 1, ATTN_NORM, 0)

	# check for drowning
	if waterlevel == 3:
		# breather or envirosuit give air
		if breather or envirosuit:
			current_player.air_finished = g_main.level.time + 10

			if (int(current_client.breather_framenum - g_main.level.framenum) % 25) == 0:
				if not current_client.breather_sound:
					g_main.gi.sound (current_player, CHAN_AUTO, g_main.gi.soundindex("player/u_breath1.wav"), 1, ATTN_NORM, 0)
				else:
					g_main.gi.sound (current_player, CHAN_AUTO, g_main.gi.soundindex("player/u_breath2.wav"), 1, ATTN_NORM, 0)
				current_client.breather_sound ^= 1
				p_weapon.PlayerNoise(current_player, current_player.s.origin, PNOISE_SELF)

		# if out of air, start drowning
		if current_player.air_finished < g_main.level.time:
			# drown!
			if (current_player.client.next_drown_time < g_main.level.time \
				and current_player.health > 0):
				current_player.client.next_drown_time = g_main.level.time + 1

				# take more damage the longer underwater
				current_player.dmg += 2
				if current_player.dmg > 15:
					current_player.dmg = 15

				# play a gurp sound instead of a normal pain sound
				if current_player.health <= current_player.dmg:
					g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("player/drown1.wav"), 1, ATTN_NORM, 0)
				elif rand.randk()&1:
					g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("*gurp1.wav"), 1, ATTN_NORM, 0)
				else:
					g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("*gurp2.wav"), 1, ATTN_NORM, 0)

				current_player.pain_debounce_time = g_main.level.time

				g_combat.T_Damage (current_player, world, world, vec3_origin, current_player.s.origin, vec3_origin, current_player.dmg, 0, DAMAGE_NO_ARMOR, MOD_WATER)
	else:
		current_player.air_finished = g_main.level.time + 12
		current_player.dmg = 2

	# check for sizzle damage
	if waterlevel and (current_player.watertype&(CONTENTS_LAVA|CONTENTS_SLIME)):
		if current_player.watertype & CONTENTS_LAVA:
			if ((current_player.health > 0)
				and (current_player.pain_debounce_time <= g_main.level.time)
				and (current_client.invincible_framenum < g_main.level.framenum)
				and not (current_player.flags & local.FL_GODMODE)):
				if rand.randk()&1:
					g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("player/burn1.wav"), 1, ATTN_NORM, 0)
				else:
					g_main.gi.sound (current_player, CHAN_VOICE, g_main.gi.soundindex("player/burn2.wav"), 1, ATTN_NORM, 0)
				current_player.pain_debounce_time = g_main.level.time + 1

			if envirosuit:		# take 1/3 damage with envirosuit
				g_combat.T_Damage (current_player, world, world, vec3_origin, current_player.s.origin, vec3_origin, 1*waterlevel, 0, 0, MOD_LAVA)
			else:
				g_combat.T_Damage (current_player, world, world, vec3_origin, current_player.s.origin, vec3_origin, 3*waterlevel, 0, 0, MOD_LAVA)

		if current_player.watertype & CONTENTS_SLIME:
			if not envirosuit:
				# no damage from slime with envirosuit
				g_combat.T_Damage (current_player, world, world, vec3_origin, current_player.s.origin, vec3_origin, 1*waterlevel, 0, 0, MOD_SLIME)


def G_SetClientEffects (ent): #edict_t *

	"""
	int pa_type;
	int remaining;
	"""

	if not ent:

		return


	ent.s.effects = 0
	ent.s.renderfx = RF_IR_VISIBLE

	if (ent.health <= 0) or g_main.level.intermissiontime:

		return


	if ent.powerarmor_time > g_main.level.time:

		pa_type = g_items.PowerArmorType(ent)

		if pa_type == POWER_ARMOR_SCREEN:

			ent.s.effects |= EF_POWERSCREEN

		elif pa_type == POWER_ARMOR_SHIELD:

			ent.s.effects |= EF_COLOR_SHELL
			ent.s.renderfx |= RF_SHELL_GREEN



	if ent.client.quad_framenum > g_main.level.framenum:

		remaining = ent.client.quad_framenum - g_main.level.framenum

		if (remaining > 30) or (remaining & 4):

			ent.s.effects |= EF_QUAD



	if ent.client.invincible_framenum > g_main.level.framenum:

		remaining = ent.client.invincible_framenum - g_main.level.framenum

		if (remaining > 30) or (remaining & 4):

			ent.s.effects |= EF_PENT



	# show cheaters
	if ent.flags & local.FL_GODMODE:

		ent.s.effects |= EF_COLOR_SHELL
		ent.s.renderfx |= (RF_SHELL_RED | RF_SHELL_GREEN | RF_SHELL_BLUE)



def G_SetClientEvent (ent): #edict_t *

	if not ent:

		return


	if ent.s.event:

		return


	if ent.health <= 0:

		return


	if g_main.g_footsteps.value == 1:

		if ent.groundentity and (xyspeed > 225):

			if int(current_client.bobtime + bobmove) != bobcycle:

				ent.s.event = EV_FOOTSTEP




	elif g_main.g_footsteps.value == 2:

		if ent.groundentity:

			if int(current_client.bobtime + bobmove) != bobcycle:

				ent.s.event = EV_FOOTSTEP




	elif g_main.g_footsteps.value >= 3:

		if int(current_client.bobtime + bobmove) != bobcycle:

			ent.s.event = EV_FOOTSTEP



def G_SetClientSound (ent): #edict_t *
	if not ent:

		return


	if ent.client.pers.game_helpchanged != g_main.game.helpchanged:
		ent.client.pers.game_helpchanged = g_main.game.helpchanged
		ent.client.pers.helpchanged = 1

	# help beep (no more than three times)
	if (ent.client.pers.helpchanged and ent.client.pers.helpchanged <= 3 and not (g_main.level.framenum&63)):
		ent.client.pers.helpchanged += 1
		g_main.gi.sound (ent, CHAN_VOICE, g_main.gi.soundindex ("misc/pc_up.wav"), 1, ATTN_STATIC, 0)

	weap = ent.client.pers.weapon.classname if ent.client.pers.weapon else ""

	if ent.waterlevel and (ent.watertype&(CONTENTS_LAVA|CONTENTS_SLIME)):
		ent.s.sound = g_main.snd_fry
	elif weap == "weapon_railgun":
		ent.s.sound = g_main.gi.soundindex("weapons/rg_hum.wav")
	elif weap == "weapon_bfg":
		ent.s.sound = g_main.gi.soundindex("weapons/bfg_hum.wav")
	elif ent.client.weapon_sound:
		ent.s.sound = ent.client.weapon_sound
	else:
		ent.s.sound = 0


def G_SetClientFrame (ent): #edict_t *
	if not ent:

		return


	client = ent.client

	if ent.s.modelindex != 255:
		return		# not in the player model

	if client.ps.pmove.pm_flags & PMF_DUCKED:
		duck = True
	else:
		duck = False
	if xyspeed:
		run = True
	else:
		run = False

	# check for stand/duck and stop/go transitions
	if (duck != client.anim_duck and client.anim_priority < ANIM_DEATH):
		newanim = True
	elif (run != client.anim_run and client.anim_priority == ANIM_BASIC):
		newanim = True
	elif (not ent.groundentity and client.anim_priority <= ANIM_WAVE):
		newanim = True
	else:
		newanim = False

	if client.anim_priority == ANIM_REVERSE:
		if(ent.s.frame > client.anim_end):
			ent.s.frame -= 1
			return
	elif ent.s.frame < client.anim_end:
		# continue an animation
		ent.s.frame += 1
		return
	else:
		newanim = False

	if newanim:
		# return to either a running or standing frame
		client.anim_priority = ANIM_BASIC
		client.anim_duck = duck
		client.anim_run = run

		if not ent.groundentity:
			client.anim_priority = ANIM_JUMP
			if ent.s.frame != player_h.FRAME_jump2:
				ent.s.frame = player_h.FRAME_jump1
			client.anim_end = player_h.FRAME_jump2
		elif run:
			# running
			if duck:
				ent.s.frame = player_h.FRAME_crwalk1
				client.anim_end = player_h.FRAME_crwalk6
			else:
				ent.s.frame = player_h.FRAME_run1
				client.anim_end = player_h.FRAME_run6
		else:
			# standing
			if duck:
				ent.s.frame = player_h.FRAME_crstnd01
				client.anim_end = player_h.FRAME_crstnd19
			else:
				ent.s.frame = player_h.FRAME_stand01
				client.anim_end = player_h.FRAME_stand40
		return

	if client.anim_priority == ANIM_DEATH:
		return		# stay there
	if client.anim_priority == ANIM_JUMP:
		if not ent.groundentity:
			return		# stay there
		client.anim_priority = ANIM_WAVE
		ent.s.frame = player_h.FRAME_jump3
		client.anim_end = player_h.FRAME_jump6


def ClientEndServerFrame (ent): #edict_t *
	global current_player, current_client, xyspeed, bobmove, bobcycle, bobfracsin

	if not ent:

		return


	current_player = ent
	current_client = ent.client

	# If the origin or velocity have changed since ClientThink(),
	# update the pmove values.
	for i in range(3):
		current_client.ps.pmove.origin[i] = ent.s.origin[i]*8.0
		current_client.ps.pmove.velocity[i] = ent.velocity[i]*8.0

	# If the end of unit layout is displayed, don't give the player
	# any normal movement attributes
	if g_main.level.intermissiontime:
		current_client.ps.blend[3] = 0
		current_client.ps.fov = 90
		p_hud.G_SetStats (ent)
		return

	AngleVectors (ent.client.v_angle, forward, right, up)

	# burn from lava, etc
	P_WorldEffects ()

	# set model angles from view angles
	if ent.client.v_angle[PITCH] > 180:
		ent.s.angles[PITCH] = (-360 + ent.client.v_angle[PITCH])/3
	else:
		ent.s.angles[PITCH] = ent.client.v_angle[PITCH]/3
	ent.s.angles[YAW] = ent.client.v_angle[YAW]
	ent.s.angles[ROLL] = 0
	ent.s.angles[ROLL] = SV_CalcRoll (ent.s.angles, ent.velocity)*4

	# calculate speed and cycle to be used for all cyclic walking effects
	xyspeed = math.sqrt(ent.velocity[0]*ent.velocity[0] + ent.velocity[1]*ent.velocity[1])

	if xyspeed < 5:
		bobmove = 0
		current_client.bobtime = 0	# start at beginning of cycle again
	elif ent.groundentity:
		# so bobbing only cycles when on ground
		if xyspeed > 210:
			bobmove = 0.25
		elif xyspeed > 100:
			bobmove = 0.125
		else:
			bobmove = 0.0625

	current_client.bobtime += bobmove
	bobtime = current_client.bobtime

	if current_client.ps.pmove.pm_flags & PMF_DUCKED:
		bobtime *= 4

	bobcycle = int(bobtime)
	bobfracsin = abs(math.sin(bobtime*math.pi))

	# detect hitting the floor
	P_FallingDamage (ent)

	# apply all the damage taken this frame
	P_DamageFeedback (ent)

	# determine the view offsets
	SV_CalcViewOffset (ent)

	# determine the gun offsets
	SV_CalcGunOffset (ent)

	# determine the full screen color blend
	SV_CalcBlend (ent)

	# chase cam stuff
	if ent.client.resp.spectator:
		p_hud.G_SetSpectatorStats(ent)
	else:
		p_hud.G_SetStats (ent)
	p_hud.G_CheckChaseStats(ent)

	G_SetClientEvent (ent)

	G_SetClientEffects (ent)

	G_SetClientSound (ent)

	G_SetClientFrame (ent)

	VectorCopy (ent.velocity, ent.client.oldvelocity)
	VectorCopy (ent.client.ps.viewangles, ent.client.oldviewangles)

	# clear weapon kicks
	VectorClear (ent.client.kick_origin)
	VectorClear (ent.client.kick_angles)

	if not (g_main.level.framenum & 31):

		# if the scoreboard is up, update it
		if ent.client.showscores:

			p_hud.DeathmatchScoreboardMessage (ent, ent.enemy)
			g_main.gi.unicast (ent, False)


		# if the help computer is up, update it
		if ent.client.showhelp:

			ent.client.pers.helpchanged = 0
			p_hud.HelpComputerMessage(ent)
			g_main.gi.unicast(ent, False)



	# if the inventory is up, update it
	if ent.client.showinventory:

		p_hud.InventoryMessage(ent)
		g_main.gi.unicast(ent, False)
