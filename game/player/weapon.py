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

Player weapons.

=======================================================================
"""
from __future__ import annotations

import math
import numpy as np
from game import g_main
from game import g_utils
from game import g_items
from game import g_weapon
from game.header.game import SVF_NOCLIENT
from common.header import shared
from common.shared import shared as shared_c
from common.shared import rand
from game.header import local
from game.monster.misc import player as player_h
from game import g_items

"""
#include "../header/local.h"
#include "../monster/misc/player.h"
#include <limits.h>
"""

PLAYER_NOISE_SELF = 0
PLAYER_NOISE_IMPACT = 1

is_quad = False #static qboolean
is_silenced = 0 #static byte

MULTICAST_PVS = shared.multicast_t.MULTICAST_PVS.value
USHRT_MAX = 0xffff #limits.h


def P_ProjectSource (ent, distance, forward, right, result): #edict_t *, vec3_t, vec3_t, vec3_t, vec3_t

	"""
	gclient_t *client = ent->client;
	float     *point  = ent->s.origin;
	vec3_t     _distance;
	"""
	client = ent.client
	point = ent.s.origin
	_distance = np.zeros((3,), dtype=np.float32)

	if not client:

		return


	shared.VectorCopy (distance, _distance)

	if client.pers.hand == local.LEFT_HANDED:

		_distance[1] *= -1

	elif client.pers.hand == local.CENTER_HANDED:

		_distance[1] = 0


	g_utils.G_ProjectSource (point, _distance, forward, right, result)

	# Berserker: fix - now the projectile hits exactly where the scope is pointing.
	if g_main.aimfix.value:

		#vec3_t start, end;
		start = np.zeros((3,), dtype=np.float32)
		end = np.zeros((3,), dtype=np.float32)
		shared.VectorSet(start, ent.s.origin[0], ent.s.origin[1], ent.s.origin[2] + ent.viewheight)
		shared_c.VectorMA(start, 8192, forward, end)

		tr = g_main.gi.trace(start, None, None, end, ent, shared.MASK_SHOT)
		if tr.fraction < 1:

			shared.VectorSubtract(tr.endpos, result, forward)
			shared_c.VectorNormalize(forward)




"""
/*
 * Each player can have two noise objects associated with it:
 * a personal noise (jumping, pain, weapon firing), and a weapon
 * target noise (bullet wall impacts)
 *
 * Monsters that don't directly see the player can move
 * to a noise in hopes of seeing the player from there.
 */
"""
def PlayerNoise_Spawn(who, type: int): #edict_t *, int (returns static edict_t *)

	"""
	edict_t *noise;
	"""

	if not who:

		return None


	noise = g_utils.G_SpawnOptional()
	if not noise:

		return None


	noise.classname = "player_noise"
	noise.spawnflags = type
	shared.VectorSet (noise.mins, -8, -8, -8)
	shared.VectorSet (noise.maxs, 8, 8, 8)
	noise.owner = who
	noise.svflags = SVF_NOCLIENT

	return noise

def PlayerNoise_Verify(who): #edict_t * (static)

	"""
	edict_t *e;
	edict_t *n1;
	edict_t *n2;
	"""

	if not who:

		return


	n1 = who.mynoise
	n2 = who.mynoise2

	if n1 and not n1.inuse:

		n1 = None


	if n2 and not n2.inuse:

		n2 = None


	if n1 and n2:

		return


	for i in range(1 + g_main.game.maxclients, g_main.glob.num_edicts):

		e = g_main.g_edicts[i]

		if not e.inuse or e.classname != "player_noise":

			continue


		if e.owner and e.owner != who:

			continue


		e.owner = who

		if not n2 and (e.spawnflags == PLAYER_NOISE_IMPACT or n1):

			n2 = e

		else:

			n1 = e


		if n1 and n2:

			break



	if not n1:

		n1 = PlayerNoise_Spawn(who, PLAYER_NOISE_SELF)


	if not n2:

		n2 = PlayerNoise_Spawn(who, PLAYER_NOISE_IMPACT)


	who.mynoise = n1
	who.mynoise2 = n2

def PlayerNoise (who, where, type): #edict_t *, vec3_t, int

	"""
	edict_t *noise;
	"""

	if not who or not who.client:

		return


	if type == local.PNOISE_WEAPON:

		if who.client.silencer_shots:

			who.client.silencer_shots -= 1
			return



	if g_main.deathmatch.value:

		return


	if who.flags & local.FL_NOTARGET:

		return


	PlayerNoise_Verify(who)

	if (type == local.PNOISE_SELF) or (type == local.PNOISE_WEAPON):

		if g_main.level.framenum <= (g_main.level.sound_entity_framenum + 3):

			return


		if not who.mynoise:

			return


		noise = who.mynoise
		g_main.level.sound_entity = noise
		g_main.level.sound_entity_framenum = g_main.level.framenum

	else:

		if g_main.level.framenum <= (g_main.level.sound2_entity_framenum + 3):

			return


		if not who.mynoise2:

			return


		noise = who.mynoise2
		g_main.level.sound2_entity = noise
		g_main.level.sound2_entity_framenum = g_main.level.framenum


	shared.VectorCopy (where, noise.s.origin)
	shared.VectorSubtract (where, noise.maxs, noise.absmin)
	shared.VectorAdd (where, noise.maxs, noise.absmax)
	noise.last_sound_time = g_main.level.time
	g_main.gi.linkentity (noise)

def Pickup_Weapon (ent, other):
	if not ent or not other:

		return False


	index = local.ITEM_INDEX (ent.item)

	if ( ( ((int)(g_main.dmflags.value) & shared.DF_WEAPONS_STAY) or g_main.coop.value)
		and other.client.pers.inventory[index]):
		if not (ent.spawnflags & (local.DROPPED_ITEM | local.DROPPED_PLAYER_ITEM)) and \
			(not g_main.coop_pickup_weapons.value or (ent.flags & local.FL_COOP_TAKEN)):
			return False

	other.client.pers.inventory[index] += 1

	if not (ent.spawnflags & local.DROPPED_ITEM) :
		ammo = g_items.FindItem (ent.item.ammo)
		if (int(g_main.dmflags.value) & shared.DF_INFINITE_AMMO ):
			g_items.Add_Ammo (other, ammo, 1000)
		else:
			g_items.Add_Ammo (other, ammo, ammo.quantity)

		if not (ent.spawnflags & local.DROPPED_PLAYER_ITEM) :
			if g_main.deathmatch.value:
				if (int(g_main.dmflags.value) & shared.DF_WEAPONS_STAY):
					ent.flags |= local.FL_RESPAWN
				else:
					g_items.SetRespawn (ent, 30)
			if g_main.coop.value:
				ent.flags |= local.FL_RESPAWN
				ent.flags |= local.FL_COOP_TAKEN

	if other.client.pers.weapon != ent.item and \
		other.client.pers.inventory[index] == 1 and \
		(not g_main.deathmatch.value or other.client.pers.weapon == g_items.FindItem("blaster")):
		other.client.newweapon = ent.item

	return True


def ChangeWeapon (ent):
	if not ent:

		return


	if ent.client.grenade_time:
		ent.client.grenade_time = g_main.level.time
		ent.client.weapon_sound = 0
		weapon_grenade_fire (ent, False)
		ent.client.grenade_time = 0

	ent.client.pers.lastweapon = ent.client.pers.weapon
	ent.client.pers.weapon = ent.client.newweapon
	ent.client.newweapon = None
	ent.client.machinegun_shots = 0

	# set visible model
	if ent.s.modelindex == 255:
		if ent.client.pers.weapon:
			i = ((ent.client.pers.weapon.weapmodel & 0xff) << 8)
		else:
			i = 0
		ent.s.skinnum = (g_main.g_edicts.index(ent) - 1) | i

	ent.client.ammo_index = g_items.GetWeaponAmmoIndex(ent.client.pers.weapon)

	if not ent.client.pers.weapon:
		# dead
		ent.client.ps.gunindex = 0
		return

	ent.client.weaponstate = local.weaponstate_t.WEAPON_ACTIVATING
	ent.client.ps.gunframe = 0
	ent.client.ps.gunindex = g_main.gi.modelindex(ent.client.pers.weapon.view_model)

	ent.client.anim_priority = local.ANIM_PAIN
	if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:
		ent.s.frame = player_h.FRAME_crpain1
		ent.client.anim_end = player_h.FRAME_crpain4
	else:
		ent.s.frame = player_h.FRAME_pain301
		ent.client.anim_end = player_h.FRAME_pain304


def NoAmmoWeaponChange (ent):
	if ( ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("slugs"))]
		and  ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("railgun"))] ):
		ent.client.newweapon = g_items.FindItem ("railgun")
		return
	if ( ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("cells"))]
		and  ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("hyperblaster"))] ):
		ent.client.newweapon = g_items.FindItem ("hyperblaster")
		return
	if ( ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("bullets"))]
		and  ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("chaingun"))] ):
		ent.client.newweapon = g_items.FindItem ("chaingun")
		return
	if ( ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("bullets"))]
		and  ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("machinegun"))] ):
		ent.client.newweapon = g_items.FindItem ("machinegun")
		return
	if ( ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("shells"))] > 1
		and  ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("super shotgun"))] ):
		ent.client.newweapon = g_items.FindItem ("super shotgun")
		return
	if ( ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("shells"))]
		and  ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem("shotgun"))] ):
		ent.client.newweapon = g_items.FindItem ("shotgun")
		return
	ent.client.newweapon = g_items.FindItem ("blaster")


def Think_Weapon (ent):
	global is_quad, is_silenced
	# if just died, put the weapon away
	if not ent:

		return


	if ent.health < 1:
		ent.client.newweapon = None
		ChangeWeapon (ent)

	# call active weapon think routine
	if ent.client.pers.weapon and ent.client.pers.weapon.weaponthink:
		is_quad = (ent.client.quad_framenum > g_main.level.framenum)
		if ent.client.silencer_shots:
			is_silenced = shared.MZ_SILENCED
		else:
			is_silenced = 0
		ent.client.pers.weapon.weaponthink (ent)


def Use_Weapon (ent, item):
	# see if we're already using it
	if not ent or not item:

		return


	if item == ent.client.pers.weapon:
		return

	if item.ammo and not g_main.g_select_empty.value and not (item.flags & local.IT_AMMO):
		ammo_item = g_items.FindItem(item.ammo)
		ammo_index = local.ITEM_INDEX(ammo_item)

		if not ent.client.pers.inventory[ammo_index]:
			g_main.gi.cprintf (ent, shared.PRINT_HIGH, "No %s for %s.\n" % (ammo_item.pickup_name, item.pickup_name))
			return

		if ent.client.pers.inventory[ammo_index] < item.quantity:
			g_main.gi.cprintf (ent, shared.PRINT_HIGH, "Not enough %s for %s.\n" % (ammo_item.pickup_name, item.pickup_name))
			return

	# change to this weapon when down
	ent.client.newweapon = item


def Drop_Weapon (ent, item):
	if not ent or not item:

		return


	if (int(g_main.dmflags.value) & shared.DF_WEAPONS_STAY):
		return

	index = local.ITEM_INDEX(item)
	# see if we're already using it
	if ( (item == ent.client.pers.weapon) or (item == ent.client.newweapon)) and (ent.client.pers.inventory[index] == 1):
		g_main.gi.cprintf (ent, shared.PRINT_HIGH, "Can't drop current weapon\n")
		return

	g_items.Drop_Item (ent, item)
	ent.client.pers.inventory[index] -= 1


"""
/*
 * Client (player) animation for changing weapon
 */
"""
def Change_Weap_Animation(ent): #edict_t * (static)

	if not ent:

		return


	ent.client.anim_priority = local.ANIM_REVERSE

	if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:

		ent.s.frame = player_h.FRAME_crpain4 + 1
		ent.client.anim_end = player_h.FRAME_crpain1

	else:

		ent.s.frame = player_h.FRAME_pain304 + 1
		ent.client.anim_end = player_h.FRAME_pain301


def Weapon_Generic (ent, FRAME_ACTIVATE_LAST, FRAME_FIRE_LAST, FRAME_IDLE_LAST, FRAME_DEACTIVATE_LAST, pause_frames, fire_frames, fire):
	FRAME_FIRE_FIRST     = FRAME_ACTIVATE_LAST + 1
	FRAME_IDLE_FIRST     = FRAME_FIRE_LAST + 1
	FRAME_DEACTIVATE_FIRST = FRAME_IDLE_LAST + 1

	#int n;
	#const unsigned short int change_speed = ...
	change_speed = (int(g_main.g_swap_speed.value) if (g_main.g_swap_speed.value < USHRT_MAX) else 1) \
		if (g_main.g_swap_speed.value > 1) else 1

	if not ent or not fire_frames or not fire:

		return


	if ent.deadflag or (ent.s.modelindex != 255): # VWep animations screw up corpses

		return


	if ent.client.weaponstate == local.weaponstate_t.WEAPON_DROPPING:

		if ent.client.ps.gunframe >= FRAME_DEACTIVATE_LAST - change_speed + 1:

			ChangeWeapon (ent)
			return

		elif (FRAME_DEACTIVATE_LAST - FRAME_DEACTIVATE_FIRST) >= (4 * change_speed):

			remainder = (FRAME_DEACTIVATE_LAST - ent.client.ps.gunframe) & 0xffff #unsigned short int
			# "if (remainder == 4)" at change_speed == 1
			if (remainder <= (4 * change_speed)) \
				and (remainder > (3 * change_speed)):

				Change_Weap_Animation(ent)



		ent.client.ps.gunframe += change_speed
		return


	if ent.client.weaponstate == local.weaponstate_t.WEAPON_ACTIVATING:

		if ent.client.ps.gunframe >= FRAME_ACTIVATE_LAST - change_speed + 1:

			ent.client.weaponstate = local.weaponstate_t.WEAPON_READY
			ent.client.ps.gunframe = FRAME_IDLE_FIRST
			return


		ent.client.ps.gunframe += change_speed
		return


	if ent.client.newweapon and (ent.client.weaponstate != local.weaponstate_t.WEAPON_FIRING):

		ent.client.weaponstate = local.weaponstate_t.WEAPON_DROPPING
		ent.client.ps.gunframe = FRAME_DEACTIVATE_FIRST

		if (FRAME_DEACTIVATE_LAST - FRAME_DEACTIVATE_FIRST) < (4 * change_speed):

			Change_Weap_Animation(ent)


		return

	if ent.client.weaponstate == local.weaponstate_t.WEAPON_READY:
		if (ent.client.latched_buttons|ent.client.buttons) & shared.BUTTON_ATTACK:
			ent.client.latched_buttons &= ~shared.BUTTON_ATTACK
			if (not ent.client.ammo_index) or \
				(ent.client.pers.inventory[ent.client.ammo_index] >= ent.client.pers.weapon.quantity):
				ent.client.ps.gunframe = FRAME_FIRE_FIRST
				ent.client.weaponstate = local.weaponstate_t.WEAPON_FIRING

				# start the animation
				ent.client.anim_priority = local.ANIM_ATTACK
				if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:
					ent.s.frame = player_h.FRAME_crattak1-1
					ent.client.anim_end = player_h.FRAME_crattak9
				else:
					ent.s.frame = player_h.FRAME_attack1-1
					ent.client.anim_end = player_h.FRAME_attack8
			else:
				if g_main.level.time >= ent.pain_debounce_time:
					g_main.gi.sound(ent, shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, shared.ATTN_NORM, 0)
					ent.pain_debounce_time = g_main.level.time + 1
				NoAmmoWeaponChange (ent)
		else:
			if ent.client.ps.gunframe == FRAME_IDLE_LAST:
				ent.client.ps.gunframe = FRAME_IDLE_FIRST
				return

			if pause_frames:
				n = 0
				while pause_frames[n]:
					if ent.client.ps.gunframe == pause_frames[n]:
						if rand.randk() & 15:
							return
					n += 1

			ent.client.ps.gunframe += 1
			return

	if ent.client.weaponstate == local.weaponstate_t.WEAPON_FIRING:
		n = 0
		while fire_frames[n]:
			if ent.client.ps.gunframe == fire_frames[n]:
				if ent.client.quad_framenum > g_main.level.framenum:
					g_main.gi.sound(ent, shared.CHAN_ITEM, g_main.gi.soundindex("items/damage3.wav"), 1, shared.ATTN_NORM, 0)

				fire (ent)
				break
			n += 1

		if not fire_frames[n]:
			ent.client.ps.gunframe += 1

		if ent.client.ps.gunframe == FRAME_IDLE_FIRST+1:
			ent.client.weaponstate = local.weaponstate_t.WEAPON_READY

GRENADE_TIMER    = 3.0
GRENADE_MINSPEED = 400
GRENADE_MAXSPEED = 800


def weapon_grenade_fire (ent, held):
	if not ent:

		return


	offset = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	damage = 125

	radius = damage+40
	if is_quad:
		damage *= 4

		g_main.gi.sound(ent, shared.CHAN_ITEM, g_main.gi.soundindex(
				"items/damage3.wav"), 1, shared.ATTN_NORM, 0)

	shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)
	P_ProjectSource (ent, offset, forward, right, start)

	timer = ent.client.grenade_time - g_main.level.time
	speed = GRENADE_MINSPEED + (GRENADE_TIMER - timer) * ((GRENADE_MAXSPEED - GRENADE_MINSPEED) / GRENADE_TIMER)
	g_weapon.fire_grenade2 (ent, start, forward, damage, speed, timer, radius, held)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1

	ent.client.grenade_time = g_main.level.time + 1.0

	if(ent.deadflag or ent.s.modelindex != 255):
		return

	if ent.health <= 0:
		return

	if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:
		ent.client.anim_priority = local.ANIM_ATTACK
		ent.s.frame = player_h.FRAME_crattak1-1
		ent.client.anim_end = player_h.FRAME_crattak3
	else:
		ent.client.anim_priority = local.ANIM_REVERSE
		ent.s.frame = player_h.FRAME_wave08
		ent.client.anim_end = player_h.FRAME_wave01


def Weapon_Grenade (ent):
	if not ent:

		return


	if ent.client.newweapon and ent.client.weaponstate == local.weaponstate_t.WEAPON_READY:
		ChangeWeapon (ent)
		return

	if ent.client.weaponstate == local.weaponstate_t.WEAPON_ACTIVATING:
		ent.client.weaponstate = local.weaponstate_t.WEAPON_READY
		ent.client.ps.gunframe = 16
		return

	if ent.client.weaponstate == local.weaponstate_t.WEAPON_READY:
		if (ent.client.latched_buttons|ent.client.buttons) & shared.BUTTON_ATTACK:
			ent.client.latched_buttons &= ~shared.BUTTON_ATTACK
			if ent.client.pers.inventory[ent.client.ammo_index]:
				ent.client.ps.gunframe = 1
				ent.client.weaponstate = local.weaponstate_t.WEAPON_FIRING
				ent.client.grenade_time = 0
			else:
				if g_main.level.time >= ent.pain_debounce_time:
					g_main.gi.sound(ent, shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, shared.ATTN_NORM, 0)
					ent.pain_debounce_time = g_main.level.time + 1
				NoAmmoWeaponChange (ent)
			return

		if (ent.client.ps.gunframe == 29) or (ent.client.ps.gunframe == 34) or (ent.client.ps.gunframe == 39) or (ent.client.ps.gunframe == 48):
			if rand.randk() & 15:
				return

		ent.client.ps.gunframe += 1
		if ent.client.ps.gunframe > 48:
			ent.client.ps.gunframe = 16
		return

	if ent.client.weaponstate == local.weaponstate_t.WEAPON_FIRING:
		if ent.client.ps.gunframe == 5:
			g_main.gi.sound(ent, shared.CHAN_WEAPON, g_main.gi.soundindex("weapons/hgrena1b.wav"), 1, shared.ATTN_NORM, 0)

		if ent.client.ps.gunframe == 11:
			if not ent.client.grenade_time:
				ent.client.grenade_time = g_main.level.time + GRENADE_TIMER + 0.2
				ent.client.weapon_sound = g_main.gi.soundindex("weapons/hgrenc1b.wav")

			# they waited too long, detonate it in their hand
			if not ent.client.grenade_blew_up and g_main.level.time >= ent.client.grenade_time:
				ent.client.weapon_sound = 0
				weapon_grenade_fire (ent, True)
				ent.client.grenade_blew_up = True

			if ent.client.buttons & shared.BUTTON_ATTACK:
				return

			if ent.client.grenade_blew_up:
				if g_main.level.time >= ent.client.grenade_time:
					ent.client.ps.gunframe = 15
					ent.client.grenade_blew_up = False
				else:
					return

		if ent.client.ps.gunframe == 12:
			ent.client.weapon_sound = 0
			weapon_grenade_fire (ent, False)

		if (ent.client.ps.gunframe == 15) and (g_main.level.time < ent.client.grenade_time):
			return

		ent.client.ps.gunframe += 1

		if ent.client.ps.gunframe == 16:
			ent.client.grenade_time = 0
			ent.client.weaponstate = local.weaponstate_t.WEAPON_READY


def weapon_grenadelauncher_fire (ent):
	if not ent:

		return


	offset = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	damage = 120

	radius = damage+40
	if is_quad:
		damage *= 4

	shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)
	P_ProjectSource (ent, offset, forward, right, start)

	shared_c.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -1

	g_weapon.fire_grenade (ent, start, forward, damage, 600, 2.5, radius)

	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (shared.MZ_GRENADE | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1

	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_GrenadeLauncher (ent):
	pause_frames = [34, 51, 59, 0]
	fire_frames = [6, 0]

	Weapon_Generic (ent, 5, 16, 59, 64, pause_frames, fire_frames, weapon_grenadelauncher_fire)


def Weapon_RocketLauncher_Fire (ent):
	if not ent:

		return


	offset = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)

	damage = 100 + int(local.random() * 20.0)
	radius_damage = 120
	damage_radius = 120
	if is_quad:
		damage *= 4
		radius_damage *= 4

	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)

	shared_c.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -1

	shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	P_ProjectSource (ent, offset, forward, right, start)
	g_weapon.fire_rocket (ent, start, forward, damage, 650, damage_radius, radius_damage)

	# send muzzle flash
	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (shared.MZ_ROCKET | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1

	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_RocketLauncher (ent):
	pause_frames = [25, 33, 42, 50, 0]
	fire_frames = [5, 0]

	Weapon_Generic (ent, 4, 12, 50, 54, pause_frames, fire_frames, Weapon_RocketLauncher_Fire)


def Blaster_Fire (ent, g_offset, damage, hyper, effect):
	if not ent:

		return


	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)

	if is_quad:
		damage *= 4
	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)
	shared.VectorSet(offset, 24, 8, ent.viewheight-8)
	shared.VectorAdd (offset, g_offset, offset)
	P_ProjectSource (ent, offset, forward, right, start)

	shared_c.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -1

	g_weapon.fire_blaster (ent, start, forward, damage, 1000, effect, hyper)

	# send muzzle flash
	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	if hyper:
		g_main.gi.WriteByte (shared.MZ_HYPERBLASTER | is_silenced)
	else:
		g_main.gi.WriteByte (shared.MZ_BLASTER | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	PlayerNoise(ent, start, local.PNOISE_WEAPON)


def Weapon_Blaster_Fire (ent):
	if not ent:

		return


	if g_main.deathmatch.value:
		damage = 15
	else:
		damage = 10
	Blaster_Fire (ent, shared_c.vec3_origin, damage, False, shared.EF_BLASTER)
	ent.client.ps.gunframe += 1


def Weapon_Blaster (ent):
	if not ent:

		return


	pause_frames = [19, 32, 0]
	fire_frames = [5, 0]

	Weapon_Generic (ent, 4, 8, 52, 55, pause_frames, fire_frames, Weapon_Blaster_Fire)


def Weapon_HyperBlaster_Fire (ent):
	if not ent:

		return


	offset = np.zeros((3,), dtype=np.float32)

	ent.client.weapon_sound = g_main.gi.soundindex("weapons/hyprbl1a.wav")

	if not (ent.client.buttons & shared.BUTTON_ATTACK):
		ent.client.ps.gunframe += 1
	else:
		if not ent.client.pers.inventory[ent.client.ammo_index]:
			if g_main.level.time >= ent.pain_debounce_time:
				g_main.gi.sound(ent, shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, shared.ATTN_NORM, 0)
				ent.pain_debounce_time = g_main.level.time + 1
			NoAmmoWeaponChange (ent)
		else:
			rotation = (ent.client.ps.gunframe - 5) * 2*math.pi/6
			offset[0] = -4 * math.sin(rotation)
			offset[1] = 0
			offset[2] = 4 * math.cos(rotation)

			if (ent.client.ps.gunframe == 6) or (ent.client.ps.gunframe == 9):
				effect = shared.EF_HYPERBLASTER
			else:
				effect = 0
			if g_main.deathmatch.value:
				damage = 15
			else:
				damage = 20
			Blaster_Fire (ent, offset, damage, True, effect)
			if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
				ent.client.pers.inventory[ent.client.ammo_index] -= 1

			ent.client.anim_priority = local.ANIM_ATTACK
			if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:
				ent.s.frame = player_h.FRAME_crattak1 - 1
				ent.client.anim_end = player_h.FRAME_crattak9
			else:
				ent.s.frame = player_h.FRAME_attack1 - 1
				ent.client.anim_end = player_h.FRAME_attack8

		ent.client.ps.gunframe += 1
		if ent.client.ps.gunframe == 12 and ent.client.pers.inventory[ent.client.ammo_index]:
			ent.client.ps.gunframe = 6

	if ent.client.ps.gunframe == 12:
		g_main.gi.sound(ent, shared.CHAN_AUTO, g_main.gi.soundindex("weapons/hyprbd1a.wav"), 1, shared.ATTN_NORM, 0)
		ent.client.weapon_sound = 0


def Weapon_HyperBlaster (ent):
	if not ent:

		return


	pause_frames = [0]
	fire_frames = [6, 7, 8, 9, 10, 11, 0]

	Weapon_Generic (ent, 5, 20, 49, 53, pause_frames, fire_frames, Weapon_HyperBlaster_Fire)

def Machinegun_Fire (ent):
	if not ent:

		return


	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	angles = np.zeros((3,), dtype=np.float32)
	damage = 8
	kick = 2
	offset = np.zeros((3,), dtype=np.float32)

	if not (ent.client.buttons & shared.BUTTON_ATTACK):
		ent.client.machinegun_shots = 0
		ent.client.ps.gunframe += 1
		return

	if ent.client.ps.gunframe == 5:
		ent.client.ps.gunframe = 4
	else:
		ent.client.ps.gunframe = 5

	if ent.client.pers.inventory[ent.client.ammo_index] < 1:
		ent.client.ps.gunframe = 6
		if g_main.level.time >= ent.pain_debounce_time:
			g_main.gi.sound(ent, shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, shared.ATTN_NORM, 0)
			ent.pain_debounce_time = g_main.level.time + 1
		NoAmmoWeaponChange (ent)
		return

	if is_quad:
		damage *= 4
		kick *= 4

	for i in range(1, 3):
		ent.client.kick_origin[i] = local.crandom() * 0.35
		ent.client.kick_angles[i] = local.crandom() * 0.7
	ent.client.kick_origin[0] = local.crandom() * 0.35
	ent.client.kick_angles[0] = ent.client.machinegun_shots * -1.5

	# raise the gun as it is firing
	if not (g_main.deathmatch.value or g_main.g_machinegun_norecoil.value):
		ent.client.machinegun_shots += 1
		if ent.client.machinegun_shots > 9:
			ent.client.machinegun_shots = 9

	# get start / end positions
	shared.VectorAdd (ent.client.v_angle, ent.client.kick_angles, angles)
	shared_c.AngleVectors (angles, forward, right, None)
	shared.VectorSet(offset, 0, 8, ent.viewheight-8)
	P_ProjectSource (ent, offset, forward, right, start)
	g_weapon.fire_bullet (ent, start, forward, damage, kick, local.DEFAULT_BULLET_HSPREAD, local.DEFAULT_BULLET_VSPREAD, local.MOD_MACHINEGUN)

	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (shared.MZ_MACHINEGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1

	ent.client.anim_priority = local.ANIM_ATTACK
	if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:
		ent.s.frame = player_h.FRAME_crattak1 - int(local.random()+0.25)
		ent.client.anim_end = player_h.FRAME_crattak9
	else:
		ent.s.frame = player_h.FRAME_attack1 - int(local.random()+0.25)
		ent.client.anim_end = player_h.FRAME_attack8


def Weapon_Machinegun (ent):
	if not ent:

		return


	pause_frames = [23, 45, 0]
	fire_frames = [4, 5, 0]

	Weapon_Generic (ent, 3, 5, 45, 49, pause_frames, fire_frames, Machinegun_Fire)


def Chaingun_Fire (ent):
	if not ent:

		return


	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)
	kick = 2

	if g_main.deathmatch.value:
		damage = 6
	else:
		damage = 8

	if ent.client.ps.gunframe == 5:
		g_main.gi.sound(ent, shared.CHAN_AUTO, g_main.gi.soundindex("weapons/chngnu1a.wav"), 1, shared.ATTN_IDLE, 0)

	if (ent.client.ps.gunframe == 14) and not (ent.client.buttons & shared.BUTTON_ATTACK):
		ent.client.ps.gunframe = 32
		ent.client.weapon_sound = 0
		return
	elif (ent.client.ps.gunframe == 21) and (ent.client.buttons & shared.BUTTON_ATTACK) and ent.client.pers.inventory[ent.client.ammo_index]:
		ent.client.ps.gunframe = 15
	else:
		ent.client.ps.gunframe += 1

	if ent.client.ps.gunframe == 22:
		ent.client.weapon_sound = 0
		g_main.gi.sound(ent, shared.CHAN_AUTO, g_main.gi.soundindex("weapons/chngnd1a.wav"), 1, shared.ATTN_IDLE, 0)
	else:
		ent.client.weapon_sound = g_main.gi.soundindex("weapons/chngnl1a.wav")

	ent.client.anim_priority = local.ANIM_ATTACK
	if ent.client.ps.pmove.pm_flags & shared.PMF_DUCKED:
		ent.s.frame = player_h.FRAME_crattak1 - (ent.client.ps.gunframe & 1)
		ent.client.anim_end = player_h.FRAME_crattak9
	else:
		ent.s.frame = player_h.FRAME_attack1 - (ent.client.ps.gunframe & 1)
		ent.client.anim_end = player_h.FRAME_attack8

	if ent.client.ps.gunframe <= 9:
		shots = 1
	elif ent.client.ps.gunframe <= 14:
		if ent.client.buttons & shared.BUTTON_ATTACK:
			shots = 2
		else:
			shots = 1
	else:
		shots = 3

	if ent.client.pers.inventory[ent.client.ammo_index] < shots:
		shots = ent.client.pers.inventory[ent.client.ammo_index]

	if not shots:
		if g_main.level.time >= ent.pain_debounce_time:
			g_main.gi.sound(ent, shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, shared.ATTN_NORM, 0)
			ent.pain_debounce_time = g_main.level.time + 1
		NoAmmoWeaponChange (ent)
		return

	if is_quad:
		damage *= 4
		kick *= 4

	for i in range(0, 3):
		ent.client.kick_origin[i] = local.crandom() * 0.35
		ent.client.kick_angles[i] = local.crandom() * 0.7

	for i in range(0, shots):
		# get start / end positions
		shared_c.AngleVectors (ent.client.v_angle, forward, right, up)
		r = 7 + local.crandom()*4
		u = local.crandom()*4
		shared.VectorSet(offset, 0, r, u + ent.viewheight-8)
		P_ProjectSource (ent, offset, forward, right, start)

		g_weapon.fire_bullet (ent, start, forward, damage, kick, local.DEFAULT_BULLET_HSPREAD, local.DEFAULT_BULLET_VSPREAD, local.MOD_CHAINGUN)

	# send muzzle flash
	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte ((shared.MZ_CHAINGUN1 + shots - 1) | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= shots


def Weapon_Chaingun (ent):
	if not ent:

		return


	pause_frames = [38, 43, 51, 61, 0]
	fire_frames = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 0]

	Weapon_Generic (ent, 4, 31, 61, 64, pause_frames, fire_frames, Chaingun_Fire)


def weapon_shotgun_fire (ent):
	if not ent:

		return


	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)
	damage = 4
	kick = 8

	if ent.client.ps.gunframe == 9:
		ent.client.ps.gunframe += 1
		return

	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)

	shared_c.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -2

	shared.VectorSet(offset, 0, 8,  ent.viewheight-8)
	P_ProjectSource (ent, offset, forward, right, start)

	if is_quad:
		damage *= 4
		kick *= 4

	if g_main.deathmatch.value:
		g_weapon.fire_shotgun (ent, start, forward, damage, kick, 500, 500, local.DEFAULT_DEATHMATCH_SHOTGUN_COUNT, local.MOD_SHOTGUN)
	else:
		g_weapon.fire_shotgun (ent, start, forward, damage, kick, 500, 500, local.DEFAULT_SHOTGUN_COUNT, local.MOD_SHOTGUN)

	# send muzzle flash
	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (shared.MZ_SHOTGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1
	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_Shotgun (ent):
	if not ent:

		return


	pause_frames = [22, 28, 34, 0]
	fire_frames = [8, 9, 0]

	Weapon_Generic (ent, 7, 18, 36, 39, pause_frames, fire_frames, weapon_shotgun_fire)


def weapon_supershotgun_fire (ent):
	if not ent:

		return


	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)
	v = np.zeros((3,), dtype=np.float32)
	damage = 6
	kick = 12

	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)

	shared_c.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -2

	shared.VectorSet(offset, 0, 8,  ent.viewheight-8)
	P_ProjectSource (ent, offset, forward, right, start)

	if is_quad:
		damage *= 4
		kick *= 4

	v[shared.PITCH] = ent.client.v_angle[shared.PITCH]
	v[shared.YAW]   = ent.client.v_angle[shared.YAW] - 5
	v[shared.ROLL]  = ent.client.v_angle[shared.ROLL]
	shared_c.AngleVectors (v, forward, None, None)

	if g_main.aimfix.value:

		shared_c.AngleVectors(v, forward, right, None)

		shared_c.VectorScale(forward, -2, ent.client.kick_origin)
		ent.client.kick_angles[0] = -2

		shared.VectorSet(offset, 0, 8, ent.viewheight - 8)
		P_ProjectSource(ent, offset, forward, right, start)

	g_weapon.fire_shotgun (ent, start, forward, damage, kick, local.DEFAULT_SHOTGUN_HSPREAD, local.DEFAULT_SHOTGUN_VSPREAD, local.DEFAULT_SSHOTGUN_COUNT // 2, local.MOD_SSHOTGUN)

	v[shared.YAW]   = ent.client.v_angle[shared.YAW] + 5
	shared_c.AngleVectors (v, forward, None, None)

	if g_main.aimfix.value:

		shared_c.AngleVectors(v, forward, right, None)

		shared_c.VectorScale(forward, -2, ent.client.kick_origin)
		ent.client.kick_angles[0] = -2

		shared.VectorSet(offset, 0, 8, ent.viewheight - 8)
		P_ProjectSource(ent, offset, forward, right, start)

	g_weapon.fire_shotgun (ent, start, forward, damage, kick, local.DEFAULT_SHOTGUN_HSPREAD, local.DEFAULT_SHOTGUN_VSPREAD, local.DEFAULT_SSHOTGUN_COUNT // 2, local.MOD_SSHOTGUN)

	# send muzzle flash
	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (shared.MZ_SSHOTGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1
	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 2


def Weapon_SuperShotgun (ent):
	if not ent:

		return


	pause_frames = [29, 42, 57, 0]
	fire_frames = [7, 0]

	Weapon_Generic (ent, 6, 17, 57, 61, pause_frames, fire_frames, weapon_supershotgun_fire)


def weapon_railgun_fire (ent):
	if not ent:

		return


	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)

	if g_main.deathmatch.value:
		damage = 100
		kick = 200
	else:
		damage = 150
		kick = 250

	if is_quad:
		damage *= 4
		kick *= 4

	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)

	shared_c.VectorScale (forward, -3, ent.client.kick_origin)
	ent.client.kick_angles[0] = -3

	shared.VectorSet(offset, 0, 7,  ent.viewheight-8)
	P_ProjectSource (ent, offset, forward, right, start)
	g_weapon.fire_rail (ent, start, forward, damage, kick)

	# send muzzle flash
	g_main.gi.WriteByte (local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (shared.MZ_RAILGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1
	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_Railgun (ent):
	if not ent:

		return


	pause_frames = [56, 0]
	fire_frames = [4, 0]

	Weapon_Generic (ent, 3, 18, 56, 61, pause_frames, fire_frames, weapon_railgun_fire)


def weapon_bfg_fire (ent):
	if not ent:

		return


	offset = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	damage_radius = 1000

	if g_main.deathmatch.value:
		damage = 200
	else:
		damage = 500

	if ent.client.ps.gunframe == 9:

		shared_c.AngleVectors(ent.client.v_angle, forward, right, None)

		shared.VectorSet(offset, 8, 8, ent.viewheight - 8)
		P_ProjectSource(ent, offset, forward, right, start)

		# send muzzle flash
		g_main.gi.WriteByte (local.svc_muzzleflash)
		g_main.gi.WriteShort (g_main.g_edicts.index(ent))
		g_main.gi.WriteByte (shared.MZ_BFG | is_silenced)
		g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

		ent.client.ps.gunframe += 1

		PlayerNoise(ent, start, local.PNOISE_WEAPON)
		return

	# cells can go down during windup (from power armor hits), so
	# check again and abort firing if we don't have enough now
	if ent.client.pers.inventory[ent.client.ammo_index] < 50:
		ent.client.ps.gunframe += 1
		return

	if is_quad:
		damage *= 4

	shared_c.AngleVectors (ent.client.v_angle, forward, right, None)

	shared_c.VectorScale (forward, -2, ent.client.kick_origin)

	# make a big pitch kick with an inverse fall
	ent.client.v_dmg_pitch = -40
	ent.client.v_dmg_roll = local.crandom()*8
	ent.client.v_dmg_time = g_main.level.time + local.DAMAGE_TIME

	shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	P_ProjectSource (ent, offset, forward, right, start)
	g_weapon.fire_bfg (ent, start, forward, damage, 400, damage_radius)

	ent.client.ps.gunframe += 1

	PlayerNoise(ent, start, local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 50


def Weapon_BFG (ent):
	if not ent:

		return


	pause_frames = [39, 45, 50, 55, 0]
	fire_frames = [9, 17, 0]

	Weapon_Generic (ent, 8, 32, 55, 58, pause_frames, fire_frames, weapon_bfg_fire)
