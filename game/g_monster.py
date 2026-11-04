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
import random as _r
from game import q_shared
from game import g_local
from game import g_main
from game import g_utils
from game import g_ai
from game import g_items
from game import g_weapon
from game import g_combat
from game.game import SVF_MONSTER, SVF_DEADMONSTER, SVF_NOCLIENT
from game.q_shared import (MASK_MONSTERSOLID, MASK_WATER, EF_FLIES,
	EF_COLOR_SHELL, EF_POWERSCREEN, RF_SHELL_RED, RF_SHELL_GREEN,
	RF_SHELL_BLUE, RF_FRAMELERP, CONTENTS_LAVA, CONTENTS_SLIME,
	CONTENTS_WATER, CHAN_BODY, ATTN_NORM, YAW)
from game.g_local import (MOD_UNKNOWN, MOD_WATER, MOD_LAVA, MOD_SLIME, FRAMETIME,
	DAMAGE_NO_ARMOR, POWER_ARMOR_SCREEN,
	POWER_ARMOR_SHIELD, FL_SWIM, FL_FLY, FL_INWATER, FL_IMMUNE_LAVA,
	FL_IMMUNE_SLIME, FL_NOTARGET, DEAD_NO,
	AI_GOOD_GUY, AI_RESURRECTING, AI_HOLD_FRAME,
	MOVETYPE_NONE, MOVETYPE_STEP)
from game.game import solid_t
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value
from game.g_local import damage_t
DAMAGE_AIM = damage_t.DAMAGE_AIM.value

"""
#include "g_local.h"

//
// monster weapons
//
"""


def monster_fire_bullet (self, start, dir, damage, kick, hspread, vspread, flashtype):
	g_weapon.fire_bullet (self, start, dir, damage, kick, hspread, vspread, MOD_UNKNOWN)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


def monster_fire_shotgun (self, start, aimdir, damage, kick, hspread, vspread, count, flashtype):
	g_weapon.fire_shotgun (self, start, aimdir, damage, kick, hspread, vspread, count, MOD_UNKNOWN)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


def monster_fire_blaster (self, start, dir, damage, speed, flashtype, effect):
	g_weapon.fire_blaster (self, start, dir, damage, speed, effect, False)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


def monster_fire_grenade (self, start, aimdir, damage, speed, flashtype):
	g_weapon.fire_grenade (self, start, aimdir, damage, speed, 2.5, damage+40)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


def monster_fire_rocket (self, start, dir, damage, speed, flashtype):
	g_weapon.fire_rocket (self, start, dir, damage, speed, damage+20, damage)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


def monster_fire_railgun (self, start, aimdir, damage, kick, flashtype):
	g_weapon.fire_rail (self, start, aimdir, damage, kick)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


def monster_fire_bfg (self, start, aimdir, damage, speed, kick, damage_radius, flashtype):
	g_weapon.fire_bfg (self, start, aimdir, damage, speed, damage_radius)

	g_main.gi.WriteByte (g_local.svc_muzzleflash2)
	g_main.gi.WriteShort (g_main.g_edicts.index(self))
	g_main.gi.WriteByte (flashtype)
	g_main.gi.multicast (start, q_shared.multicast_t.MULTICAST_PVS.value)


"""
//
// Monster utility functions
//
"""
def M_FliesOff (self):
	self.s.effects &= ~EF_FLIES
	self.s.sound = 0


def M_FliesOn (self):
	if self.waterlevel:
		return
	self.s.effects |= EF_FLIES
	self.s.sound = g_main.gi.soundindex ("infantry/inflies1.wav")
	self.think = M_FliesOff
	self.nextthink = g_main.level.time + 60


def M_FlyCheck (self):
	if self.waterlevel:
		return

	if g_local.random() > 0.5:
		return

	self.think = M_FliesOn
	self.nextthink = g_main.level.time + 5 + 10 * g_local.random()


def AttackFinished (self, time):
	self.monsterinfo.attack_finished = g_main.level.time + time


def M_CheckGround (ent):
	#vec3_t point
	point = [0, 0, 0]

	if ent.flags & (FL_SWIM|FL_FLY):
		return

	if ent.velocity[2] > 100:
		ent.groundentity = None
		return

	# if the hull point one-quarter unit down is solid the entity is on ground
	point[0] = ent.s.origin[0]
	point[1] = ent.s.origin[1]
	point[2] = ent.s.origin[2] - 0.25

	trace = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, point, ent, MASK_MONSTERSOLID)

	# check steepness
	if (trace.plane.normal[2] < 0.7 and not trace.startsolid):
		ent.groundentity = None
		return

	if not trace.startsolid and not trace.allsolid:
		q_shared.VectorCopy (trace.endpos, ent.s.origin)
		ent.groundentity = trace.ent
		ent.groundentity_linkcount = trace.ent.linkcount
		ent.velocity[2] = 0


def M_CatagorizePosition (ent):
	#vec3_t point
	point = [0, 0, 0]

	#
	# get waterlevel
	#
	point[0] = ent.s.origin[0]
	point[1] = ent.s.origin[1]
	point[2] = ent.s.origin[2] + ent.mins[2] + 1
	cont = g_main.gi.pointcontents (point)

	if not (cont & MASK_WATER):
		ent.waterlevel = 0
		ent.watertype = 0
		return

	ent.watertype = cont
	ent.waterlevel = 1
	point[2] += 26
	cont = g_main.gi.pointcontents (point)
	if not (cont & MASK_WATER):
		return

	ent.waterlevel = 2
	point[2] += 22
	cont = g_main.gi.pointcontents (point)
	if cont & MASK_WATER:
		ent.waterlevel = 3


def M_WorldEffects (ent):
	#int dmg

	if ent.health > 0:
		if not (ent.flags & FL_SWIM):
			if ent.waterlevel < 3:
				ent.air_finished = g_main.level.time + 12
			elif ent.air_finished < g_main.level.time:
				# drown!
				if ent.pain_debounce_time < g_main.level.time:
					dmg = 2 + 2 * int(math.floor(g_main.level.time - ent.air_finished))
					if dmg > 15:
						dmg = 15
					g_combat.T_Damage (ent, g_main.world, g_main.world, q_shared.vec3_origin, ent.s.origin, q_shared.vec3_origin, dmg, 0, DAMAGE_NO_ARMOR, MOD_WATER)
					ent.pain_debounce_time = g_main.level.time + 1
		else:
			if ent.waterlevel > 0:
				ent.air_finished = g_main.level.time + 9
			elif ent.air_finished < g_main.level.time:
				# suffocate!
				if ent.pain_debounce_time < g_main.level.time:
					dmg = 2 + 2 * int(math.floor(g_main.level.time - ent.air_finished))
					if dmg > 15:
						dmg = 15
					g_combat.T_Damage (ent, g_main.world, g_main.world, q_shared.vec3_origin, ent.s.origin, q_shared.vec3_origin, dmg, 0, DAMAGE_NO_ARMOR, MOD_WATER)
					ent.pain_debounce_time = g_main.level.time + 1

	if ent.waterlevel == 0:
		if ent.flags & FL_INWATER:
			g_main.gi.sound (ent, CHAN_BODY, g_main.gi.soundindex("player/watr_out.wav"), 1, ATTN_NORM, 0)
			ent.flags &= ~FL_INWATER
		return

	if (ent.watertype & CONTENTS_LAVA) and not (ent.flags & FL_IMMUNE_LAVA):
		if ent.damage_debounce_time < g_main.level.time:
			ent.damage_debounce_time = g_main.level.time + 0.2
			g_combat.T_Damage (ent, g_main.world, g_main.world, q_shared.vec3_origin, ent.s.origin, q_shared.vec3_origin, 10*ent.waterlevel, 0, 0, MOD_LAVA)
	if (ent.watertype & CONTENTS_SLIME) and not (ent.flags & FL_IMMUNE_SLIME):
		if ent.damage_debounce_time < g_main.level.time:
			ent.damage_debounce_time = g_main.level.time + 1
			g_combat.T_Damage (ent, g_main.world, g_main.world, q_shared.vec3_origin, ent.s.origin, q_shared.vec3_origin, 4*ent.waterlevel, 0, 0, MOD_SLIME)

	if not (ent.flags & FL_INWATER) :
		if not (ent.svflags & SVF_DEADMONSTER):
			if ent.watertype & CONTENTS_LAVA:
				if g_local.random() <= 0.5:
					g_main.gi.sound (ent, CHAN_BODY, g_main.gi.soundindex("player/lava1.wav"), 1, ATTN_NORM, 0)
				else:
					g_main.gi.sound (ent, CHAN_BODY, g_main.gi.soundindex("player/lava2.wav"), 1, ATTN_NORM, 0)
			elif ent.watertype & CONTENTS_SLIME:
				g_main.gi.sound (ent, CHAN_BODY, g_main.gi.soundindex("player/watr_in.wav"), 1, ATTN_NORM, 0)
			elif ent.watertype & CONTENTS_WATER:
				g_main.gi.sound (ent, CHAN_BODY, g_main.gi.soundindex("player/watr_in.wav"), 1, ATTN_NORM, 0)

		ent.flags |= FL_INWATER
		ent.damage_debounce_time = 0


def M_droptofloor (ent):
	#vec3_t end
	end = [0, 0, 0]

	ent.s.origin[2] += 1
	q_shared.VectorCopy (ent.s.origin, end)
	end[2] -= 256

	trace = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, end, ent, MASK_MONSTERSOLID)

	if trace.fraction == 1 or trace.allsolid:
		return

	q_shared.VectorCopy (trace.endpos, ent.s.origin)

	g_main.gi.linkentity (ent)
	M_CheckGround (ent)
	M_CatagorizePosition (ent)


def M_SetEffects (ent):
	ent.s.effects &= ~(EF_COLOR_SHELL|EF_POWERSCREEN)
	ent.s.renderfx &= ~(RF_SHELL_RED|RF_SHELL_GREEN|RF_SHELL_BLUE)

	if ent.monsterinfo.aiflags & AI_RESURRECTING:
		ent.s.effects |= EF_COLOR_SHELL
		ent.s.renderfx |= RF_SHELL_RED

	if ent.health <= 0:
		return

	if ent.powerarmor_time > g_main.level.time:
		if ent.monsterinfo.power_armor_type == POWER_ARMOR_SCREEN:
			ent.s.effects |= EF_POWERSCREEN
		elif ent.monsterinfo.power_armor_type == POWER_ARMOR_SHIELD:
			ent.s.effects |= EF_COLOR_SHELL
			ent.s.renderfx |= RF_SHELL_GREEN


def M_MoveFrame (self):
	#mmove_t *move
	#int index

	move = self.monsterinfo.currentmove
	self.nextthink = g_main.level.time + FRAMETIME

	if (self.monsterinfo.nextframe) and (self.monsterinfo.nextframe >= move.firstframe) and (self.monsterinfo.nextframe <= move.lastframe):
		self.s.frame = self.monsterinfo.nextframe
		self.monsterinfo.nextframe = 0
	else:
		if self.s.frame == move.lastframe:
			if move.endfunc:
				move.endfunc (self)

				# regrab move, endfunc is very likely to change it
				move = self.monsterinfo.currentmove

				# check for death
				if self.svflags & SVF_DEADMONSTER:
					return

		if self.s.frame < move.firstframe or self.s.frame > move.lastframe:
			self.monsterinfo.aiflags &= ~AI_HOLD_FRAME
			self.s.frame = move.firstframe
		else:
			if not (self.monsterinfo.aiflags & AI_HOLD_FRAME):
				self.s.frame += 1
				if self.s.frame > move.lastframe:
					self.s.frame = move.firstframe

	index = self.s.frame - move.firstframe
	if move.frame[index].aifunc:
		if not (self.monsterinfo.aiflags & AI_HOLD_FRAME):
			move.frame[index].aifunc (self, move.frame[index].dist * self.monsterinfo.scale)
		else:
			move.frame[index].aifunc (self, 0)

	if move.frame[index].thinkfunc:
		move.frame[index].thinkfunc (self)


def monster_think (self):
	M_MoveFrame (self)
	if self.linkcount != self.monsterinfo.linkcount:
		self.monsterinfo.linkcount = self.linkcount
		M_CheckGround (self)
	M_CatagorizePosition (self)
	M_WorldEffects (self)
	M_SetEffects (self)


"""
================
monster_use

Using a monster makes it angry at the current activator
================
"""
def monster_use (self, other, activator):
	if self.enemy:
		return
	if self.health <= 0:
		return
	if activator.flags & FL_NOTARGET:
		return
	if not (activator.client) and not (activator.monsterinfo.aiflags & AI_GOOD_GUY):
		return

	# delay reaction so if the monster is teleported, its sound is still heard
	self.enemy = activator
	g_ai.FoundTarget (self)


def monster_triggered_spawn (self):
	self.s.origin[2] += 1
	g_utils.KillBox (self)

	self.solid = SOLID_BBOX
	self.movetype = MOVETYPE_STEP
	self.svflags &= ~SVF_NOCLIENT
	self.air_finished = g_main.level.time + 12
	g_main.gi.linkentity (self)

	monster_start_go (self)

	if self.enemy and not (self.spawnflags & 1) and not (self.enemy.flags & FL_NOTARGET):
		g_ai.FoundTarget (self)
	else:
		self.enemy = None


def monster_triggered_spawn_use (self, other, activator):
	# we have a one frame delay here so we don't telefrag the guy who activated us
	self.think = monster_triggered_spawn
	self.nextthink = g_main.level.time + FRAMETIME
	if activator.client:
		self.enemy = activator
	self.use = monster_use


def monster_triggered_start (self):
	self.solid = SOLID_NOT
	self.movetype = MOVETYPE_NONE
	self.svflags |= SVF_NOCLIENT
	self.nextthink = 0
	self.use = monster_triggered_spawn_use


"""
================
monster_death_use

When a monster dies, it fires all of its targets with the current
enemy as activator.
================
"""
def monster_death_use (self):
	self.flags &= ~(FL_FLY|FL_SWIM)
	self.monsterinfo.aiflags &= AI_GOOD_GUY

	if self.item:
		g_items.Drop_Item (self, self.item)
		self.item = None

	if self.deathtarget:
		self.target = self.deathtarget

	if not self.target:
		return

	g_utils.G_UseTargets (self, self.enemy)


"""
============================================================================
"""
def monster_start (self):
	if g_main.deathmatch.value:
		g_utils.G_FreeEdict (self)
		return False

	if (self.spawnflags & 4) and not (self.monsterinfo.aiflags & AI_GOOD_GUY):
		self.spawnflags &= ~4
		self.spawnflags |= 1

	if not (self.monsterinfo.aiflags & AI_GOOD_GUY):
		g_main.level.total_monsters += 1

	self.nextthink = g_main.level.time + FRAMETIME
	self.svflags |= SVF_MONSTER
	self.s.renderfx |= RF_FRAMELERP
	self.takedamage = DAMAGE_AIM
	self.air_finished = g_main.level.time + 12
	self.use = monster_use
	self.max_health = self.health
	self.clipmask = MASK_MONSTERSOLID

	self.s.skinnum = 0
	self.deadflag = DEAD_NO
	self.svflags &= ~SVF_DEADMONSTER

	if not self.monsterinfo.checkattack:
		self.monsterinfo.checkattack = g_ai.M_CheckAttack
	q_shared.VectorCopy (self.s.origin, self.s.old_origin)

	if g_main.st.item:
		self.item = g_items.FindItemByClassname (g_main.st.item)
		if not self.item:
			g_main.gi.dprintf("%s at %s has bad item: %s\n", self.classname, g_utils.vtos(self.s.origin), g_main.st.item)

	# randomize what frame they start on
	if self.monsterinfo.currentmove:
		self.s.frame = self.monsterinfo.currentmove.firstframe + (_r.randint(0, 2147483647) % (self.monsterinfo.currentmove.lastframe - self.monsterinfo.currentmove.firstframe + 1))

	return True


def monster_start_go (self):
	#vec3_t v
	v = [0, 0, 0]

	if self.health <= 0:
		return

	# check for target to combat_point and change to combattarget
	if self.target:
		#qboolean notcombat, fixup
		#edict_t *target
		notcombat = False
		fixup = False
		target = None
		while True:
			target = g_utils.G_Find (target, "targetname", self.target)
			if target is None:
				break
			if target.classname == "point_combat":
				self.combattarget = self.target
				fixup = True
			else:
				notcombat = True
		if notcombat and self.combattarget:
			g_main.gi.dprintf("%s at %s has target with mixed types\n", self.classname, g_utils.vtos(self.s.origin))
		if fixup:
			self.target = None

	# validate combattarget
	if self.combattarget:
		target = None
		while True:
			target = g_utils.G_Find (target, "targetname", self.combattarget)
			if target is None:
				break
			if target.classname != "point_combat":
				g_main.gi.dprintf("%s at (%i %i %i) has a bad combattarget %s : %s at (%i %i %i)\n",
					self.classname, int(self.s.origin[0]), int(self.s.origin[1]), int(self.s.origin[2]),
					self.combattarget, target.classname, int(target.s.origin[0]), int(target.s.origin[1]),
					int(target.s.origin[2]))

	if self.target:
		self.goalentity = self.movetarget = g_utils.G_PickTarget(self.target)
		if not self.movetarget:
			g_main.gi.dprintf ("%s can't find target %s at %s\n", self.classname, self.target, g_utils.vtos(self.s.origin))
			self.target = None
			self.monsterinfo.pausetime = 100000000
			self.monsterinfo.stand (self)
		elif self.movetarget.classname == "path_corner":
			q_shared.VectorSubtract (self.goalentity.s.origin, self.s.origin, v)
			self.ideal_yaw = self.s.angles[YAW] = g_utils.vectoyaw(v)
			self.monsterinfo.walk (self)
			self.target = None
		else:
			self.goalentity = self.movetarget = None
			self.monsterinfo.pausetime = 100000000
			self.monsterinfo.stand (self)
	else:
		self.monsterinfo.pausetime = 100000000
		self.monsterinfo.stand (self)

	self.think = monster_think
	self.nextthink = g_main.level.time + FRAMETIME


def walkmonster_start_go (self):
	if not (self.spawnflags & 2) and g_main.level.time < 1:
		M_droptofloor (self)

		if self.groundentity:
			if not g_ai.M_walkmove (self, 0, 0):
				g_main.gi.dprintf ("%s in solid at %s\n", self.classname, g_utils.vtos(self.s.origin))

	if not self.yaw_speed:
		self.yaw_speed = 20
	self.viewheight = 25

	monster_start_go (self)

	if self.spawnflags & 2:
		monster_triggered_start (self)


def walkmonster_start (self):
	self.think = walkmonster_start_go
	monster_start (self)


def flymonster_start_go (self):
	if not g_ai.M_walkmove (self, 0, 0):
		g_main.gi.dprintf ("%s in solid at %s\n", self.classname, g_utils.vtos(self.s.origin))

	if not self.yaw_speed:
		self.yaw_speed = 10
	self.viewheight = 25

	monster_start_go (self)

	if self.spawnflags & 2:
		monster_triggered_start (self)


def flymonster_start (self):
	self.flags |= FL_FLY
	self.think = flymonster_start_go
	monster_start (self)


def swimmonster_start_go (self):
	if not self.yaw_speed:
		self.yaw_speed = 10
	self.viewheight = 10

	monster_start_go (self)

	if self.spawnflags & 2:
		monster_triggered_start (self)


def swimmonster_start (self):
	self.flags |= FL_SWIM
	self.think = swimmonster_start_go
	monster_start (self)
