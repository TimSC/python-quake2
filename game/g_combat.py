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
import math
import numpy as np
from game import q_shared
from game import g_local
from game import g_main
from game import g_items
from game import g_ai
from game import g_cmds
from game import g_monster
from game.q_shared import CHAN_ITEM, CHAN_AUTO, ATTN_NORM
from game.q_shared import multicast_t
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
from game.g_local import svc_temp_entity
from game.q_shared import temp_event_t
TE_BLOOD = temp_event_t.TE_BLOOD.value
TE_SPARKS = temp_event_t.TE_SPARKS.value
TE_SCREEN_SPARKS = temp_event_t.TE_SCREEN_SPARKS.value
TE_SHIELD_SPARKS = temp_event_t.TE_SHIELD_SPARKS.value
TE_BULLET_SPARKS = temp_event_t.TE_BULLET_SPARKS.value
from game.q_shared import DF_SKINTEAMS, DF_MODELTEAMS, DF_NO_FRIENDLY_FIRE
from game.q_shared import MASK_SOLID, vec3_origin
from game.g_local import (MOD_FRIENDLY_FIRE, POWER_ARMOR_NONE, POWER_ARMOR_SCREEN,
	FL_FLY, FL_SWIM, FL_NO_KNOCKBACK, FL_GODMODE,
	MOVETYPE_PUSH, MOVETYPE_STOP, MOVETYPE_NONE, MOVETYPE_BOUNCE,
	DEAD_DEAD, AI_GOOD_GUY, AI_SOUND_TARGET, AI_DUCKED)
from game.game import SVF_MONSTER
from game.g_local import (DAMAGE_RADIUS, DAMAGE_NO_ARMOR, DAMAGE_ENERGY,
	DAMAGE_NO_KNOCKBACK, DAMAGE_BULLET, DAMAGE_NO_PROTECTION)

"""
// g_combat.c

#include "g_local.h"
"""


"""
============
CanDamage

Returns true if the inflictor can directly damage the target.  Used for
explosions and melee attacks.
============
"""
def CanDamage (targ, inflictor):
	#vec3_t dest
	#trace_t trace
	dest = np.zeros((3,), dtype=np.float32)

	# bmodels need special checking because their origin is 0,0,0
	if targ.movetype == MOVETYPE_PUSH:
		q_shared.VectorAdd (targ.absmin, targ.absmax, dest)
		q_shared.VectorScale (dest, 0.5, dest)
		trace = g_main.gi.trace (inflictor.s.origin, vec3_origin, vec3_origin, dest, inflictor, MASK_SOLID)
		if trace.fraction == 1.0:
			return True
		if trace.ent == targ:
			return True
		return False

	trace = g_main.gi.trace (inflictor.s.origin, vec3_origin, vec3_origin, targ.s.origin, inflictor, MASK_SOLID)
	if trace.fraction == 1.0:
		return True

	q_shared.VectorCopy (targ.s.origin, dest)
	dest[0] += 15.0
	dest[1] += 15.0
	trace = g_main.gi.trace (inflictor.s.origin, vec3_origin, vec3_origin, dest, inflictor, MASK_SOLID)
	if trace.fraction == 1.0:
		return True

	q_shared.VectorCopy (targ.s.origin, dest)
	dest[0] += 15.0
	dest[1] -= 15.0
	trace = g_main.gi.trace (inflictor.s.origin, vec3_origin, vec3_origin, dest, inflictor, MASK_SOLID)
	if trace.fraction == 1.0:
		return True

	q_shared.VectorCopy (targ.s.origin, dest)
	dest[0] -= 15.0
	dest[1] += 15.0
	trace = g_main.gi.trace (inflictor.s.origin, vec3_origin, vec3_origin, dest, inflictor, MASK_SOLID)
	if trace.fraction == 1.0:
		return True

	q_shared.VectorCopy (targ.s.origin, dest)
	dest[0] -= 15.0
	dest[1] -= 15.0
	trace = g_main.gi.trace (inflictor.s.origin, vec3_origin, vec3_origin, dest, inflictor, MASK_SOLID)
	if trace.fraction == 1.0:
		return True

	return False


"""
============
Killed
============
"""
def Killed (targ, inflictor, attacker, damage, point):
	if targ.health < -999:
		targ.health = -999

	targ.enemy = attacker

	if ((targ.svflags & SVF_MONSTER) and (targ.deadflag != DEAD_DEAD)):
		# targ.svflags |= SVF_DEADMONSTER;	// now treat as a different content type
		if not (targ.monsterinfo.aiflags & AI_GOOD_GUY):
			g_main.level.killed_monsters += 1
			if g_main.coop.value and attacker.client:
				attacker.client.resp.score += 1
			# medics won't heal monsters that they kill themselves
			if attacker.classname == "monster_medic":
				targ.owner = attacker

	if targ.movetype == MOVETYPE_PUSH or targ.movetype == MOVETYPE_STOP or targ.movetype == MOVETYPE_NONE:
		# doors, triggers, etc
		targ.die (targ, inflictor, attacker, damage, point)
		return

	if (targ.svflags & SVF_MONSTER) and (targ.deadflag != DEAD_DEAD):
		targ.touch = None
		g_monster.monster_death_use (targ)

	targ.die (targ, inflictor, attacker, damage, point)


"""
================
SpawnDamage
================
"""
def SpawnDamage (type, origin, normal, damage):
	if damage > 255:
		damage = 255
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (type)
	g_main.gi.WritePosition (origin)
	g_main.gi.WriteDir (normal)
	g_main.gi.multicast (origin, MULTICAST_PVS)


"""
============
T_Damage

targ		entity that is being damaged
inflictor	entity that is causing the damage
attacker	entity that caused the inflictor to damage targ
	example: targ=monster, inflictor=rocket, attacker=player

dir			direction of the attack
point		point at which the damage is being inflicted
normal		normal vector from that point
damage		amount of damage being inflicted
knockback	force to be applied against targ as a result of the damage

dflags		these flags are used to control how T_Damage works
	DAMAGE_RADIUS			damage was indirect (from a nearby explosion)
	DAMAGE_NO_ARMOR			armor does not protect from this damage
	DAMAGE_ENERGY			damage is from an energy based weapon
	DAMAGE_NO_KNOCKBACK		do not affect velocity, just view angles
	DAMAGE_BULLET			damage is from a bullet (used for ricochets)
	DAMAGE_NO_PROTECTION	kills godmode, armor, everything
============
"""
def CheckPowerArmor (ent, point, normal, damage, dflags):
	#gclient_t *client
	#int save, power_armor_type, index, damagePerCell, pa_te_type, power, power_used

	if not damage:
		return 0

	client = ent.client
	power_armor_type = 0
	index = 0
	damagePerCell = 0
	pa_te_type = 0
	power = 0

	if dflags & DAMAGE_NO_ARMOR:
		return 0

	if client:
		power_armor_type = g_items.PowerArmorType (ent)
		if power_armor_type != POWER_ARMOR_NONE:
			index = g_items.ITEM_INDEX(g_items.FindItem("Cells"))
			power = client.pers.inventory[index]
	elif ent.svflags & SVF_MONSTER:
		power_armor_type = ent.monsterinfo.power_armor_type
		power = ent.monsterinfo.power_armor_power
	else:
		return 0

	if power_armor_type == POWER_ARMOR_NONE:
		return 0
	if not power:
		return 0

	if power_armor_type == POWER_ARMOR_SCREEN:
		#vec3_t vec, forward
		#float dot
		vec = np.zeros((3,), dtype=np.float32)
		forward = np.zeros((3,), dtype=np.float32)

		# only works if damage point is in front
		q_shared.AngleVectors (ent.s.angles, forward, None, None)
		q_shared.VectorSubtract (point, ent.s.origin, vec)
		q_shared.VectorNormalize (vec)
		dot = q_shared.DotProduct (vec, forward)
		if dot <= 0.3:
			return 0

		damagePerCell = 1
		pa_te_type = TE_SCREEN_SPARKS
		damage = damage // 3
	else:
		damagePerCell = 2
		pa_te_type = TE_SHIELD_SPARKS
		damage = (2 * damage) // 3

	save = power * damagePerCell
	if not save:
		return 0
	if save > damage:
		save = damage

	SpawnDamage (pa_te_type, point, normal, save)
	ent.powerarmor_time = g_main.level.time + 0.2

	power_used = save // damagePerCell

	if client:
		client.pers.inventory[index] -= power_used
	else:
		ent.monsterinfo.power_armor_power -= power_used
	return save


def CheckArmor (ent, point, normal, damage, te_sparks, dflags):
	#gclient_t *client
	#int save, index
	#gitem_t *armor

	if not damage:
		return 0

	client = ent.client
	save = 0
	index = 0

	if not client:
		return 0

	if dflags & DAMAGE_NO_ARMOR:
		return 0

	index = g_items.ArmorIndex (ent)
	if not index:
		return 0

	armor = g_items.GetItemByIndex (index)

	if dflags & DAMAGE_ENERGY:
		save = int(math.ceil(armor.info.energy_protection * damage))
	else:
		save = int(math.ceil(armor.info.normal_protection * damage))
	if save >= client.pers.inventory[index]:
		save = client.pers.inventory[index]

	if not save:
		return 0

	client.pers.inventory[index] -= save
	SpawnDamage (te_sparks, point, normal, save)

	return save


def M_ReactToDamage (targ, attacker):
	if not (attacker.client) and not (attacker.svflags & SVF_MONSTER):
		return

	if attacker == targ or attacker == targ.enemy:
		return

	# if we are a good guy monster and our attacker is a player
	# or another good guy, do not get mad at them
	if targ.monsterinfo.aiflags & AI_GOOD_GUY:
		if attacker.client or (attacker.monsterinfo.aiflags & AI_GOOD_GUY):
			return

	# we now know that we are not both good guys

	# if attacker is a client, get mad at them because he's good and we're not
	if attacker.client:
		targ.monsterinfo.aiflags &= ~AI_SOUND_TARGET

		# this can only happen in coop (both new and old enemies are clients)
		# only switch if can't see the current enemy
		if targ.enemy and targ.enemy.client:
			if g_ai.visible(targ, targ.enemy):
				targ.oldenemy = attacker
				return
			targ.oldenemy = targ.enemy
		targ.enemy = attacker
		if not (targ.monsterinfo.aiflags & AI_DUCKED):
			g_ai.FoundTarget (targ)
		return

	# it's the same base (walk/swim/fly) type and a different classname and it's not a tank
	# (they spray too much), get mad at them
	if (((targ.flags & (FL_FLY|FL_SWIM)) == (attacker.flags & (FL_FLY|FL_SWIM))) and \
		 (targ.classname != attacker.classname) and \
		 (attacker.classname != "monster_tank") and \
		 (attacker.classname != "monster_supertank") and \
		 (attacker.classname != "monster_makron") and \
		 (attacker.classname != "monster_jorg") ):
		if targ.enemy and targ.enemy.client:
			targ.oldenemy = targ.enemy
		targ.enemy = attacker
		if not (targ.monsterinfo.aiflags & AI_DUCKED):
			g_ai.FoundTarget (targ)
	# if they *meant* to shoot us, then shoot back
	elif attacker.enemy == targ:
		if targ.enemy and targ.enemy.client:
			targ.oldenemy = targ.enemy
		targ.enemy = attacker
		if not (targ.monsterinfo.aiflags & AI_DUCKED):
			g_ai.FoundTarget (targ)
	# otherwise get mad at whoever they are mad at (help our buddy) unless it is us!
	elif attacker.enemy and attacker.enemy != targ:
		if targ.enemy and targ.enemy.client:
			targ.oldenemy = targ.enemy
		targ.enemy = attacker.enemy
		if not (targ.monsterinfo.aiflags & AI_DUCKED):
			g_ai.FoundTarget (targ)


def CheckTeamDamage (targ, attacker):
		#FIXME make the next line real and uncomment this block
		# if ((ability to damage a teammate == OFF) and (targ's team == attacker's team))
	return False


def T_Damage (targ, inflictor, attacker, dir, point, normal, damage, knockback, dflags, mod):
	#gclient_t *client
	#int take, save, asave, psave, te_sparks

	if not targ.takedamage:
		return

	# friendly fire avoidance
	# if enabled you can't hurt teammates (but you can hurt yourself)
	# knockback still occurs
	if ((targ != attacker) and ((g_main.deathmatch.value and ((int)(g_main.dmflags.value) & (DF_MODELTEAMS | DF_SKINTEAMS))) or g_main.coop.value)):
		if g_cmds.OnSameTeam (targ, attacker):
			if (int)(g_main.dmflags.value) & DF_NO_FRIENDLY_FIRE:
				damage = 0
			else:
				mod |= MOD_FRIENDLY_FIRE

	g_main.meansOfDeath = mod

	# easy mode takes half damage
	if g_main.skill.value == 0 and g_main.deathmatch.value == 0 and targ.client:
		damage = int(damage * 0.5)
		if not damage:
			damage = 1

	client = targ.client

	if dflags & DAMAGE_BULLET:
		te_sparks = TE_BULLET_SPARKS
	else:
		te_sparks = TE_SPARKS

	q_shared.VectorNormalize(dir)

	# bonus damage for suprising a monster
	if not (dflags & DAMAGE_RADIUS) and (targ.svflags & SVF_MONSTER) and (attacker.client) and (not targ.enemy) and (targ.health > 0):
		damage *= 2

	if targ.flags & FL_NO_KNOCKBACK:
		knockback = 0

	# figure momentum add
	if not (dflags & DAMAGE_NO_KNOCKBACK):
		if (knockback) and (targ.movetype != MOVETYPE_NONE) and (targ.movetype != MOVETYPE_BOUNCE) and (targ.movetype != MOVETYPE_PUSH) and (targ.movetype != MOVETYPE_STOP):
			#vec3_t kvel
			#float mass
			kvel = np.zeros((3,), dtype=np.float32)
			if targ.mass < 50:
				mass = 50.0
			else:
				mass = targ.mass

			if targ.client and attacker == targ:
				q_shared.VectorScale (dir, 1600.0 * float(knockback) / mass, kvel)	# the rocket jump hack...
			else:
				q_shared.VectorScale (dir, 500.0 * float(knockback) / mass, kvel)

			q_shared.VectorAdd (targ.velocity, kvel, targ.velocity)

	take = damage
	save = 0

	# check for godmode
	if ((targ.flags & FL_GODMODE) and not (dflags & DAMAGE_NO_PROTECTION) ):
		take = 0
		save = damage
		SpawnDamage (te_sparks, point, normal, save)

	# check for invincibility
	if ((client and client.invincible_framenum > g_main.level.framenum ) and not (dflags & DAMAGE_NO_PROTECTION)):
		if targ.pain_debounce_time < g_main.level.time:
			g_main.gi.sound(targ, CHAN_ITEM, g_main.gi.soundindex("items/protect4.wav"), 1, ATTN_NORM, 0)
			targ.pain_debounce_time = g_main.level.time + 2
		take = 0
		save = damage

	psave = CheckPowerArmor (targ, point, normal, take, dflags)
	take -= psave

	asave = CheckArmor (targ, point, normal, take, te_sparks, dflags)
	take -= asave

	#treat cheat/powerup savings the same as armor
	asave += save

	# team damage avoidance
	if not (dflags & DAMAGE_NO_PROTECTION) and CheckTeamDamage (targ, attacker):
		return

	# do the damage
	if take:
		if (targ.svflags & SVF_MONSTER) or (client):
			SpawnDamage (TE_BLOOD, point, normal, take)
		else:
			SpawnDamage (te_sparks, point, normal, take)

		targ.health = targ.health - take

		if targ.health <= 0:
			if (targ.svflags & SVF_MONSTER) or (client):
				targ.flags |= FL_NO_KNOCKBACK
			Killed (targ, inflictor, attacker, take, point)
			return

	if targ.svflags & SVF_MONSTER:
		M_ReactToDamage (targ, attacker)
		if not (targ.monsterinfo.aiflags & AI_DUCKED) and (take):
			targ.pain (targ, attacker, knockback, take)
			# nightmare mode monsters don't go into pain frames often
			if g_main.skill.value == 3:
				targ.pain_debounce_time = g_main.level.time + 5
	elif client:
		if not (targ.flags & FL_GODMODE) and (take):
			targ.pain (targ, attacker, knockback, take)
	elif take:
		if targ.pain:
			targ.pain (targ, attacker, knockback, take)

	# add to the damage inflicted on a player this frame
	# the total will be turned into screen blends and view angle kicks
	# at the end of the frame
	if client:
		client.damage_parmor += psave
		client.damage_armor += asave
		client.damage_blood += take
		client.damage_knockback += knockback
		q_shared.VectorCopy (point, client.damage_from)


"""
============
T_RadiusDamage
============
"""
def T_RadiusDamage (inflictor, attacker, damage, ignore, radius, mod):
	#vec3_t v, dir
	v = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

	edicts = g_main.g_edicts
	for i in range(g_main.glob.num_edicts):
		ent = edicts[i]
		if not ent.inuse:
			continue
		if ent.solid == q_shared.solid_t.SOLID_NOT:
			continue
		eorg = np.zeros((3,), dtype=np.float32)
		for j in range(3):
			eorg[j] = inflictor.s.origin[j] - (ent.s.origin[j] + (ent.mins[j] + ent.maxs[j])*0.5)
		if q_shared.VectorLength(eorg) > radius:
			continue

		if ent == ignore:
			continue
		if not ent.takedamage:
			continue

		q_shared.VectorAdd (ent.mins, ent.maxs, v)
		q_shared.VectorMA (ent.s.origin, 0.5, v, v)
		q_shared.VectorSubtract (inflictor.s.origin, v, v)
		points = damage - 0.5 * q_shared.VectorLength (v)
		if ent == attacker:
			points = points * 0.5
		if points > 0:
			if CanDamage (ent, inflictor):
				q_shared.VectorSubtract (ent.s.origin, inflictor.s.origin, dir)
				T_Damage (ent, inflictor, attacker, dir, inflictor.s.origin, vec3_origin, int(points), int(points), DAMAGE_RADIUS, mod)
