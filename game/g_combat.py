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

Combat code like damage, death and so on.

=======================================================================
"""
from __future__ import annotations

import math
import numpy as np
from game import g_main
from game import g_items
from game import g_ai
from game import g_cmds
from game import g_monster
from game import g_utils
from common.header.shared import CHAN_ITEM, ATTN_NORM
from common.header.shared import multicast_t

"""
#include "header/local.h"
"""

MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
from game.header.local import svc_temp_entity
from common.header.shared import temp_event_t
TE_BLOOD = temp_event_t.TE_BLOOD.value
TE_SPARKS = temp_event_t.TE_SPARKS.value
TE_SCREEN_SPARKS = temp_event_t.TE_SCREEN_SPARKS.value
TE_SHIELD_SPARKS = temp_event_t.TE_SHIELD_SPARKS.value
TE_BULLET_SPARKS = temp_event_t.TE_BULLET_SPARKS.value
from common.header.shared import DF_SKINTEAMS, DF_MODELTEAMS, DF_NO_FRIENDLY_FIRE
from common.header.shared import MASK_SOLID
from common.shared.shared import vec3_origin
from game.header.local import MOD_FRIENDLY_FIRE, POWER_ARMOR_NONE, POWER_ARMOR_SCREEN, FL_FLY, FL_SWIM, FL_NO_KNOCKBACK, FL_GODMODE, MOVETYPE_PUSH, MOVETYPE_STOP, MOVETYPE_NONE, MOVETYPE_BOUNCE, DEAD_DEAD, AI_GOOD_GUY, AI_SOUND_TARGET, AI_DUCKED
from game.header.game import SVF_MONSTER
from game.header.local import DAMAGE_RADIUS, DAMAGE_NO_ARMOR, DAMAGE_ENERGY, DAMAGE_NO_KNOCKBACK, DAMAGE_BULLET, DAMAGE_NO_PROTECTION
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from game import g_items

"""
 * Returns true if the inflictor can
 * directly damage the target.  Used for
 * explosions and melee attacks.
"""
def CanDamage(targ, inflictor)->bool: #edict_t *, edict_t * (returns qboolean)

	"""
	vec3_t dest;
	trace_t trace;
	"""

	if not targ or not inflictor:

		return False


	dest = np.zeros((3,), dtype=np.float32)

	# bmodels need special checking because their origin is 0,0,0
	if targ.movetype == MOVETYPE_PUSH:

		shared.VectorAdd(targ.absmin, targ.absmax, dest)
		shared_c.VectorScale(dest, 0.5, dest)
		trace = g_main.gi.trace(inflictor.s.origin, vec3_origin, vec3_origin,
				dest, inflictor, MASK_SOLID)

		if trace.fraction == 1.0:

			return True


		if trace.ent == targ:

			return True


		return False


	trace = g_main.gi.trace(inflictor.s.origin, vec3_origin, vec3_origin,
			targ.s.origin, inflictor, MASK_SOLID)

	if trace.fraction == 1.0:

		return True


	shared.VectorCopy(targ.s.origin, dest)
	dest[0] += 15.0
	dest[1] += 15.0
	trace = g_main.gi.trace(inflictor.s.origin, vec3_origin, vec3_origin,
			dest, inflictor, MASK_SOLID)

	if trace.fraction == 1.0:

		return True


	shared.VectorCopy(targ.s.origin, dest)
	dest[0] += 15.0
	dest[1] -= 15.0
	trace = g_main.gi.trace(inflictor.s.origin, vec3_origin, vec3_origin,
			dest, inflictor, MASK_SOLID)

	if trace.fraction == 1.0:

		return True


	shared.VectorCopy(targ.s.origin, dest)
	dest[0] -= 15.0
	dest[1] += 15.0
	trace = g_main.gi.trace(inflictor.s.origin, vec3_origin, vec3_origin,
			dest, inflictor, MASK_SOLID)

	if trace.fraction == 1.0:

		return True


	shared.VectorCopy(targ.s.origin, dest)
	dest[0] -= 15.0
	dest[1] -= 15.0
	trace = g_main.gi.trace(inflictor.s.origin, vec3_origin, vec3_origin,
			dest, inflictor, MASK_SOLID)

	if trace.fraction == 1.0:

		return True


	return False

def Killed(targ, inflictor, attacker, damage: int, point): #edict_t *, edict_t *, edict_t *, int, vec3_t (static)

	if not targ or not inflictor or not attacker:

		return


	targ.enemy = attacker

	if (targ.svflags & SVF_MONSTER) and (targ.deadflag != DEAD_DEAD):

		if not (targ.monsterinfo.aiflags & AI_GOOD_GUY):

			g_main.level.killed_monsters += 1

			if g_main.coop.value and attacker.client:

				attacker.client.resp.score += 1


			# medics won't heal monsters that they kill themselves
			if attacker.classname and attacker.classname == "monster_medic":

				targ.owner = attacker




	if (targ.movetype == MOVETYPE_PUSH) or \
		(targ.movetype == MOVETYPE_STOP) or \
		(targ.movetype == MOVETYPE_NONE):

		# doors, triggers, etc
		targ.die(targ, inflictor, attacker, damage, point)
		return


	if (targ.svflags & SVF_MONSTER) and (targ.deadflag != DEAD_DEAD):

		targ.touch = None
		g_monster.monster_death_use(targ)


	targ.die(targ, inflictor, attacker, damage, point)

def SpawnDamage(type: int, origin, normal): #int, const vec3_t, const vec3_t (static)

	g_main.gi.WriteByte(svc_temp_entity)
	g_main.gi.WriteByte(type)
	g_main.gi.WritePosition(origin)
	g_main.gi.WriteDir(normal)
	g_main.gi.multicast(origin, MULTICAST_PVS)

"""
 * targ			entity that is being damaged
 * inflictor	entity that is causing the damage
 * attacker		entity that caused the inflictor to damage targ
 *      example: targ=monster, inflictor=rocket, attacker=player
 *
 * dir			direction of the attack
 * point		point at which the damage is being inflicted
 * normal		normal vector from that point
 * damage		amount of damage being inflicted
 * knockback	force to be applied against targ as a result of the damage
 *
 * dflags -> these flags are used to control how T_Damage works
 *      DAMAGE_RADIUS			damage was indirect (from a nearby explosion)
 *      DAMAGE_NO_ARMOR			armor does not protect from this damage
 *      DAMAGE_ENERGY			damage is from an energy based weapon
 *      DAMAGE_NO_KNOCKBACK		do not affect velocity, just view angles
 *      DAMAGE_BULLET			damage is from a bullet (used for ricochets)
 *      DAMAGE_NO_PROTECTION	kills godmode, armor, everything
"""
def CheckPowerArmor(ent, point, normal, damage: int, dflags: int)->int: #edict_t *, const vec3_t, const vec3_t, int, int (returns static int)

	"""
	gclient_t *client;
	int save;
	int power_armor_type;
	int index = 0;
	int damagePerCell;
	int pa_te_type;
	int power = 0;
	int power_used;
	"""
	index = 0
	power = 0

	if not ent:

		return 0


	if not damage:

		return 0


	index = 0

	client = ent.client

	if dflags & DAMAGE_NO_ARMOR:

		return 0


	if client:

		power_armor_type = g_items.PowerArmorType(ent)

		if power_armor_type != POWER_ARMOR_NONE:

			index = local.ITEM_INDEX(g_items.FindItem("Cells"))
			power = client.pers.inventory[index]


	elif ent.svflags & SVF_MONSTER:

		power_armor_type = ent.monsterinfo.power_armor_type
		power = ent.monsterinfo.power_armor_power
		index = 0

	else:

		return 0


	if power_armor_type == POWER_ARMOR_NONE:

		return 0


	if not power:

		return 0


	if power_armor_type == POWER_ARMOR_SCREEN:

		#vec3_t vec;
		#float dot;
		#vec3_t forward;
		vec = np.zeros((3,), dtype=np.float32)
		forward = np.zeros((3,), dtype=np.float32)

		# only works if damage point is in front
		shared_c.AngleVectors(ent.s.angles, forward, None, None)
		shared.VectorSubtract(point, ent.s.origin, vec)
		shared_c.VectorNormalize(vec)
		dot = shared.DotProduct(vec, forward)

		if dot <= 0.3:

			return 0


		damagePerCell = 1
		pa_te_type = TE_SCREEN_SPARKS
		damage = int(damage / 3)

	else:

		damagePerCell = 2
		pa_te_type = TE_SHIELD_SPARKS
		damage = int((2 * damage) / 3)


	save = power * damagePerCell

	if not save:

		return 0


	if save > damage:

		save = damage


	SpawnDamage(pa_te_type, point, normal)
	ent.powerarmor_time = g_main.level.time + 0.2

	power_used = int(save / damagePerCell)

	if client:

		client.pers.inventory[index] -= power_used

	else:

		ent.monsterinfo.power_armor_power -= power_used


	return save

def CheckArmor(ent, point, normal, damage: int, te_sparks: int, dflags: int)->int: #edict_t *, vec3_t, const vec3_t, int, int, int (returns static int)

	"""
	gclient_t *client;
	int save;
	int index;
	const gitem_t *armor;
	"""

	if not ent:

		return 0


	if not damage:

		return 0


	client = ent.client

	if not client:

		return 0


	if dflags & DAMAGE_NO_ARMOR:

		return 0


	index = g_items.ArmorIndex(ent)

	if not index:

		return 0


	armor = g_items.GetItemByIndex(index)

	if dflags & DAMAGE_ENERGY:

		save = int(math.ceil(armor.info.energy_protection * damage))

	else:

		save = int(math.ceil(armor.info.normal_protection * damage))


	if save >= client.pers.inventory[index]:

		save = client.pers.inventory[index]


	if not save:

		return 0


	client.pers.inventory[index] -= save
	SpawnDamage(te_sparks, point, normal)

	return save

def M_ReactToDamage(targ, attacker): #edict_t *, edict_t *

	if not targ or not attacker:

		return


	if targ.health <= 0:

		return


	if not (attacker.client) and not (attacker.svflags & SVF_MONSTER):

		return


	if (attacker == targ) or (attacker == targ.enemy):

		return


	# if we are a good guy monster and our attacker is a player
	# or another good guy, do not get mad at them
	if targ.monsterinfo.aiflags & AI_GOOD_GUY:

		if attacker.client or (attacker.monsterinfo.aiflags & AI_GOOD_GUY):

			return



	# if attacker is a client, get mad at
	# them because he's good and we're not
	if attacker.client:

		targ.monsterinfo.aiflags &= ~AI_SOUND_TARGET

		# this can only happen in coop (both new and old
		# enemies are clients)  only switch if can't see
		# the current enemy
		if targ.enemy and targ.enemy.client:

			if g_ai.visible(targ, targ.enemy):

				targ.oldenemy = attacker
				return


			targ.oldenemy = targ.enemy


		targ.enemy = attacker

		if not (targ.monsterinfo.aiflags & AI_DUCKED):

			g_ai.FoundTarget(targ)


		return


	# it's the same base (walk/swim/fly) type and a
	# different classname and it's not a tank
	# (they spray too much), get mad at them
	if ((targ.flags & (FL_FLY | FL_SWIM)) ==
		 (attacker.flags & (FL_FLY | FL_SWIM))) and \
		(targ.classname != attacker.classname) and \
		(attacker.classname != "monster_tank") and \
		(attacker.classname != "monster_supertank") and \
		(attacker.classname != "monster_makron") and \
		(attacker.classname != "monster_jorg"):

		if targ.enemy and targ.enemy.client:

			targ.oldenemy = targ.enemy


		targ.enemy = attacker

		if not (targ.monsterinfo.aiflags & AI_DUCKED):

			g_ai.FoundTarget(targ)


	# if they *meant* to shoot us, then shoot back
	elif attacker.enemy == targ:

		if targ.enemy and targ.enemy.client:

			targ.oldenemy = targ.enemy


		targ.enemy = attacker

		if not (targ.monsterinfo.aiflags & AI_DUCKED):

			g_ai.FoundTarget(targ)


	# otherwise get mad at whoever they are mad
	# at (help our buddy) unless it is us!
	elif attacker.enemy:

		if targ.enemy and targ.enemy.client:

			targ.oldenemy = targ.enemy


		targ.enemy = attacker.enemy

		if not (targ.monsterinfo.aiflags & AI_DUCKED):

			g_ai.FoundTarget(targ)

def apply_knockback(targ, dir, knockback: float, scale: float): #edict_t *, vec3_t, float, float (static)

	"""
	vec3_t kvel;
	float mass;
	"""

	if not knockback:

		return


	kvel = np.zeros((3,), dtype=np.float32)

	mass = 50.0 if (targ.mass < 50) else float(targ.mass)

	shared_c.VectorNormalize2(dir, kvel)
	shared_c.VectorScale(kvel, scale * (knockback / mass), kvel)
	shared.VectorAdd(targ.velocity, kvel, targ.velocity)

def T_Damage(targ, inflictor, attacker, dir, point, normal, damage: int, knockback: int, dflags: int, mod: int): #edict_t *, edict_t *, edict_t *, vec3_t, vec3_t, const vec3_t, int, int, int, int

	"""
	gclient_t *client;
	int take;
	int save;
	int asave;
	int psave;
	int te_sparks;
	"""

	if not targ or not inflictor or not attacker:

		return


	if not targ.takedamage:

		return


	# friendly fire avoidance if enabled you
	# can't hurt teammates (but you can hurt
	# yourself) knockback still occurs
	if (targ != attacker) and ((g_main.deathmatch.value and
		  (int(g_main.dmflags.value) & (DF_MODELTEAMS | DF_SKINTEAMS))) or
		 g_main.coop.value):

		if g_cmds.OnSameTeam(targ, attacker):

			if int(g_main.dmflags.value) & DF_NO_FRIENDLY_FIRE:

				damage = 0

			else:

				mod |= MOD_FRIENDLY_FIRE




	g_main.meansOfDeath = mod

	# easy mode takes half damage
	if (g_main.skill.value == local.SKILL_EASY) and (g_main.deathmatch.value == 0) and targ.client:

		damage = int(damage * 0.5)

		if not damage:

			damage = 1



	client = targ.client

	if dflags & DAMAGE_BULLET:

		te_sparks = TE_BULLET_SPARKS

	else:

		te_sparks = TE_SPARKS


	# bonus damage for suprising a monster
	if not (dflags & DAMAGE_RADIUS) and (targ.svflags & SVF_MONSTER) and \
		(attacker.client) and (not targ.enemy) and (targ.health > 0):

		damage *= 2


	if targ.flags & FL_NO_KNOCKBACK:

		knockback = 0


	# figure momentum add
	if not (dflags & DAMAGE_NO_KNOCKBACK) and \
		(targ.movetype != MOVETYPE_NONE) and \
		(targ.movetype != MOVETYPE_BOUNCE) and \
		(targ.movetype != MOVETYPE_PUSH) and \
		(targ.movetype != MOVETYPE_STOP):

		apply_knockback(targ, dir, knockback,
			(1600.0 if (client and attacker == targ) else 500.0))


	take = damage
	save = 0

	# check for godmode
	if (targ.flags & FL_GODMODE) and not (dflags & DAMAGE_NO_PROTECTION):

		take = 0
		save = damage
		SpawnDamage(te_sparks, point, normal)


	# check for invincibility
	if (client and (client.invincible_framenum > g_main.level.framenum)) and \
		not (dflags & DAMAGE_NO_PROTECTION):

		if targ.pain_debounce_time < g_main.level.time:

			g_main.gi.sound(targ, CHAN_ITEM, g_main.gi.soundindex(
						"items/protect4.wav"), 1, ATTN_NORM, 0)
			targ.pain_debounce_time = g_main.level.time + 2


		take = 0
		save = damage


	psave = CheckPowerArmor(targ, point, normal, take, dflags)
	take -= psave

	asave = CheckArmor(targ, point, normal, take, te_sparks, dflags)
	take -= asave

	# treat cheat/powerup savings the same as armor
	asave += save

	# do the damage
	if take:

		if (targ.svflags & SVF_MONSTER) or (client):

			SpawnDamage(TE_BLOOD, point, normal)

		else:

			SpawnDamage(te_sparks, point, normal)


		targ.health = targ.health - take

		if targ.health <= 0:

			if (targ.svflags & SVF_MONSTER) or (client):

				targ.flags |= FL_NO_KNOCKBACK


			Killed(targ, inflictor, attacker, take, point)
			return



	if targ.svflags & SVF_MONSTER:

		M_ReactToDamage(targ, attacker)

		if not (targ.monsterinfo.aiflags & AI_DUCKED) and (take):

			targ.pain(targ, attacker, knockback, take)

			# nightmare mode monsters don't go into pain frames often
			if g_main.skill.value == local.SKILL_HARDPLUS:

				targ.pain_debounce_time = g_main.level.time + 5



	elif client:

		if not (targ.flags & FL_GODMODE) and (take):

			targ.pain(targ, attacker, knockback, take)


	elif take:

		if targ.pain:

			targ.pain(targ, attacker, knockback, take)



	# add to the damage inflicted on a player this frame
	# the total will be turned into screen blends and view
	# angle kicks at the end of the frame
	if client:

		client.damage_parmor += psave
		client.damage_armor += asave
		client.damage_blood += take
		client.damage_knockback += knockback
		shared.VectorCopy(point, client.damage_from)

def T_RadiusDamage(inflictor, attacker, damage: float, ignore, radius: float, mod: int): #edict_t *, edict_t *, float, const edict_t *, float, int

	"""
	float points;
	edict_t *ent = NULL;
	vec3_t v;
	vec3_t dir;
	"""
	ent = None

	if not inflictor or not attacker:

		return


	v = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	while True:

		ent = g_utils.findradius(ent, inflictor.s.origin, radius)
		if ent is None:

			break


		if ent == ignore:

			continue


		if not ent.takedamage:

			continue


		shared.VectorAdd(ent.mins, ent.maxs, v)
		shared_c.VectorMA(ent.s.origin, 0.5, v, v)
		shared.VectorSubtract(inflictor.s.origin, v, v)
		points = damage - 0.5 * shared_c.VectorLength(v)

		if ent == attacker:

			points = points * 0.5


		if points > 0:

			if CanDamage(ent, inflictor):

				shared.VectorSubtract(ent.s.origin, inflictor.s.origin, dir)
				T_Damage(ent, inflictor, attacker, dir, inflictor.s.origin,
						vec3_origin, int(points), int(points), DAMAGE_RADIUS,
						mod)
