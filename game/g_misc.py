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
import random as _r
from game import q_shared
from game import g_local
from game import g_main
from game import g_utils
from game import g_combat
from game import g_monster
from game import g_target
from game.game import SVF_MONSTER, SVF_DEADMONSTER, SVF_NOCLIENT
from game.game import solid_t
SOLID_TRIGGER = solid_t.SOLID_TRIGGER.value
SOLID_BSP = solid_t.SOLID_BSP.value
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value
from game.q_shared import CS_LIGHTS
from game.q_shared import (EF_GIB, EF_FLIES, EF_ROCKET, EF_TELEPORTER,
	EF_ANIM_ALL, EF_ANIM_ALLFAST, EV_OTHER_TELEPORT, EV_PLAYER_TELEPORT,
	PMF_TIME_TELEPORT, RF_FRAMELERP, RF_TRANSLUCENT, MASK_MONSTERSOLID,
	ANGLE2SHORT, ATTN_NORM, CHAN_VOICE, CHAN_BODY, YAW, PITCH, ROLL)
from game.q_shared import temp_event_t
TE_EXPLOSION1 = temp_event_t.TE_EXPLOSION1.value
TE_EXPLOSION2 = temp_event_t.TE_EXPLOSION2.value
from game.g_local import (GIB_ORGANIC, ANIM_DEATH,
	MOVETYPE_NONE, MOVETYPE_PUSH, MOVETYPE_STEP, MOVETYPE_TOSS, MOVETYPE_BOUNCE,
	FL_GODMODE, FL_NO_KNOCKBACK, FL_SWIM, FL_FLY, DEAD_DEAD,
	AI_GOOD_GUY, AI_NOSTEP, AI_STAND_GROUND, AI_COMBAT_POINT,
	MOD_CRUSH, MOD_EXPLOSIVE, MOD_BARREL, MOD_BOMB, svc_temp_entity)
from game.g_local import damage_t
DAMAGE_NO = damage_t.DAMAGE_NO.value
DAMAGE_YES = damage_t.DAMAGE_YES.value
from game.g_local import FRAMETIME

"""
// g_misc.c

#include "g_local.h"
"""

"""QUAKED func_group (0 0 0) ?
Used to group brushes together just for editor convenience.
"""

"""
// func_areaportal: non-visible object that divides the world into areas
// that are separated when this portal is not activated.
"""
def Use_Areaportal (ent, other, activator):
	ent.count ^= 1		# toggle state
	g_main.gi.SetAreaPortalState (ent.style, ent.count)


def SP_func_areaportal (ent):
	ent.use = Use_Areaportal
	ent.count = 0		# always start closed;


"""
=================
Misc functions
=================
"""
def VelocityForDamage (damage, v):
	v[0] = 100.0 * g_local.crandom()
	v[1] = 100.0 * g_local.crandom()
	v[2] = 200.0 + 100.0 * g_local.random()

	if damage < 50:
		q_shared.VectorScale (v, 0.7, v)
	else:
		q_shared.VectorScale (v, 1.2, v)


def ClipGibVelocity (ent):
	if ent.velocity[0] < -300:
		ent.velocity[0] = -300
	elif ent.velocity[0] > 300:
		ent.velocity[0] = 300
	if ent.velocity[1] < -300:
		ent.velocity[1] = -300
	elif ent.velocity[1] > 300:
		ent.velocity[1] = 300
	if ent.velocity[2] < 200:
		ent.velocity[2] = 200	# always some upwards
	elif ent.velocity[2] > 500:
		ent.velocity[2] = 500


"""
=================
gibs
=================
"""
def gib_think (self):
	self.s.frame += 1
	self.nextthink = g_main.level.time + FRAMETIME

	if self.s.frame == 10:
		self.think = g_utils.G_FreeEdict
		self.nextthink = g_main.level.time + 8 + g_local.random()*10


def gib_touch (self, other, plane, surf):
	#vec3_t normal_angles, right
	normal_angles = [0, 0, 0]
	right = [0, 0, 0]

	if not self.groundentity:
		return

	self.touch = None

	if plane:
		g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("misc/fhit3.wav"), 1, ATTN_NORM, 0)

		g_utils.vectoangles (plane.normal, normal_angles)
		q_shared.AngleVectors (normal_angles, None, right, None)
		g_utils.vectoangles (right, self.s.angles)

		if self.s.modelindex == g_main.sm_meat_index:
			self.s.frame += 1
			self.think = gib_think
			self.nextthink = g_main.level.time + FRAMETIME


def gib_die (self, inflictor, attacker, damage, point):
	g_utils.G_FreeEdict (self)


def ThrowGib (self, gibname, damage, type):
	#edict_t *gib
	#vec3_t vd, origin, size
	#float vscale
	vd = [0, 0, 0]
	origin = [0, 0, 0]
	size = [0, 0, 0]

	gib = g_utils.G_Spawn()

	q_shared.VectorScale (self.size, 0.5, size)
	q_shared.VectorAdd (self.absmin, size, origin)
	gib.s.origin[0] = origin[0] + g_local.crandom() * size[0]
	gib.s.origin[1] = origin[1] + g_local.crandom() * size[1]
	gib.s.origin[2] = origin[2] + g_local.crandom() * size[2]

	g_main.gi.setmodel (gib, gibname)
	gib.solid = SOLID_NOT
	gib.s.effects |= EF_GIB
	gib.flags |= FL_NO_KNOCKBACK
	gib.takedamage = DAMAGE_YES
	gib.die = gib_die

	if type == GIB_ORGANIC:
		gib.movetype = MOVETYPE_TOSS
		gib.touch = gib_touch
		vscale = 0.5
	else:
		gib.movetype = MOVETYPE_BOUNCE
		vscale = 1.0

	VelocityForDamage (damage, vd)
	q_shared.VectorMA (self.velocity, vscale, vd, gib.velocity)
	ClipGibVelocity (gib)
	gib.avelocity[0] = g_local.random()*600
	gib.avelocity[1] = g_local.random()*600
	gib.avelocity[2] = g_local.random()*600

	gib.think = g_utils.G_FreeEdict
	gib.nextthink = g_main.level.time + 10 + g_local.random()*10

	g_main.gi.linkentity (gib)


def ThrowHead (self, gibname, damage, type):
	#vec3_t vd
	#float vscale
	vd = [0, 0, 0]

	self.s.skinnum = 0
	self.s.frame = 0
	q_shared.VectorClear (self.mins)
	q_shared.VectorClear (self.maxs)

	self.s.modelindex2 = 0
	g_main.gi.setmodel (self, gibname)
	self.solid = SOLID_NOT
	self.s.effects |= EF_GIB
	self.s.effects &= ~EF_FLIES
	self.s.sound = 0
	self.flags |= FL_NO_KNOCKBACK
	self.svflags &= ~SVF_MONSTER
	self.takedamage = DAMAGE_YES
	self.die = gib_die

	if type == GIB_ORGANIC:
		self.movetype = MOVETYPE_TOSS
		self.touch = gib_touch
		vscale = 0.5
	else:
		self.movetype = MOVETYPE_BOUNCE
		vscale = 1.0

	VelocityForDamage (damage, vd)
	q_shared.VectorMA (self.velocity, vscale, vd, self.velocity)
	ClipGibVelocity (self)

	self.avelocity[YAW] = g_local.crandom()*600

	self.think = g_utils.G_FreeEdict
	self.nextthink = g_main.level.time + 10 + g_local.random()*10

	g_main.gi.linkentity (self)


def ThrowClientHead (self, damage):
	#vec3_t vd
	vd = [0, 0, 0]

	if _r.randint(0, 1) & 1:
		gibname = "models/objects/gibs/head2/tris.md2"
		self.s.skinnum = 1		# second skin is player
	else:
		gibname = "models/objects/gibs/skull/tris.md2"
		self.s.skinnum = 0

	self.s.origin[2] += 32
	self.s.frame = 0
	g_main.gi.setmodel (self, gibname)
	q_shared.VectorSet (self.mins, -16, -16, 0)
	q_shared.VectorSet (self.maxs, 16, 16, 16)

	self.takedamage = DAMAGE_NO
	self.solid = SOLID_NOT
	self.s.effects = EF_GIB
	self.s.sound = 0
	self.flags |= FL_NO_KNOCKBACK

	self.movetype = MOVETYPE_BOUNCE
	VelocityForDamage (damage, vd)
	q_shared.VectorAdd (self.velocity, vd, self.velocity)

	if self.client:	# bodies in the queue don't have a client anymore
		self.client.anim_priority = ANIM_DEATH
		self.client.anim_end = self.s.frame
	else:
		self.think = None
		self.nextthink = 0

	g_main.gi.linkentity (self)


"""
=================
debris
=================
"""
def debris_die (self, inflictor, attacker, damage, point):
	g_utils.G_FreeEdict (self)


def ThrowDebris (self, modelname, speed, origin):
	#edict_t *chunk
	#vec3_t v
	v = [0, 0, 0]

	chunk = g_utils.G_Spawn()
	q_shared.VectorCopy (origin, chunk.s.origin)
	g_main.gi.setmodel (chunk, modelname)
	v[0] = 100 * g_local.crandom()
	v[1] = 100 * g_local.crandom()
	v[2] = 100 + 100 * g_local.crandom()
	q_shared.VectorMA (self.velocity, speed, v, chunk.velocity)
	chunk.movetype = MOVETYPE_BOUNCE
	chunk.solid = SOLID_NOT
	chunk.avelocity[0] = g_local.random()*600
	chunk.avelocity[1] = g_local.random()*600
	chunk.avelocity[2] = g_local.random()*600
	chunk.think = g_utils.G_FreeEdict
	chunk.nextthink = g_main.level.time + 5 + g_local.random()*5
	chunk.s.frame = 0
	chunk.flags = 0
	chunk.classname = "debris"
	chunk.takedamage = DAMAGE_YES
	chunk.die = debris_die
	g_main.gi.linkentity (chunk)


def BecomeExplosion1 (self):
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_EXPLOSION1)
	g_main.gi.WritePosition (self.s.origin)
	g_main.gi.multicast (self.s.origin, q_shared.multicast_t.MULTICAST_PVS.value)

	g_utils.G_FreeEdict (self)


def BecomeExplosion2 (self):
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_EXPLOSION2)
	g_main.gi.WritePosition (self.s.origin)
	g_main.gi.multicast (self.s.origin, q_shared.multicast_t.MULTICAST_PVS.value)

	g_utils.G_FreeEdict (self)


"""QUAKED path_corner (.5 .3 0) (-8 -8 -8) (8 8 8) TELEPORT
Target: next path corner
Pathtarget: gets used when an entity that has
	this path_corner targeted touches it
"""

def path_corner_touch (self, other, plane, surf):
	#vec3_t v
	#edict_t *next
	v = [0, 0, 0]

	if other.movetarget != self:
		return

	if other.enemy:
		return

	if self.pathtarget:
		savetarget = self.target
		self.target = self.pathtarget
		g_utils.G_UseTargets (self, other)
		self.target = savetarget

	if self.target:
		next = g_utils.G_PickTarget(self.target)
	else:
		next = None

	if (next) and (next.spawnflags & 1):
		q_shared.VectorCopy (next.s.origin, v)
		v[2] += next.mins[2]
		v[2] -= other.mins[2]
		q_shared.VectorCopy (v, other.s.origin)
		next = g_utils.G_PickTarget(next.target)
		other.s.event = EV_OTHER_TELEPORT

	other.goalentity = other.movetarget = next

	if self.wait:
		other.monsterinfo.pausetime = g_main.level.time + self.wait
		other.monsterinfo.stand (other)
		return

	if not other.movetarget:
		other.monsterinfo.pausetime = g_main.level.time + 100000000
		other.monsterinfo.stand (other)
	else:
		q_shared.VectorSubtract (other.goalentity.s.origin, other.s.origin, v)
		other.ideal_yaw = g_utils.vectoyaw (v)


def SP_path_corner (self):
	if not self.targetname:
		g_main.gi.dprintf ("path_corner with no targetname at %s\n", g_utils.vtos(self.s.origin))
		g_utils.G_FreeEdict (self)
		return

	self.solid = SOLID_TRIGGER
	self.touch = path_corner_touch
	q_shared.VectorSet (self.mins, -8, -8, -8)
	q_shared.VectorSet (self.maxs, 8, 8, 8)
	self.svflags |= SVF_NOCLIENT
	g_main.gi.linkentity (self)


"""QUAKED point_combat (0.5 0.3 0) (-8 -8 -8) (8 8 8) Hold
Makes this the target of a monster and it will head here
when first activated before going after the activator.  If
hold is selected, it will stay here.
"""
def point_combat_touch (self, other, plane, surf):
	#edict_t *activator

	if other.movetarget != self:
		return

	if self.target:
		other.target = self.target
		other.goalentity = other.movetarget = g_utils.G_PickTarget(other.target)
		if not other.goalentity:
			g_main.gi.dprintf("%s at %s target %s does not exist\n", self.classname, g_utils.vtos(self.s.origin), self.target)
			other.movetarget = self
		self.target = None
	elif (self.spawnflags & 1) and not (other.flags & (FL_SWIM|FL_FLY)):
		other.monsterinfo.pausetime = g_main.level.time + 100000000
		other.monsterinfo.aiflags |= AI_STAND_GROUND
		other.monsterinfo.stand (other)

	if other.movetarget == self:
		other.target = None
		other.movetarget = None
		other.goalentity = other.enemy
		other.monsterinfo.aiflags &= ~AI_COMBAT_POINT

	if self.pathtarget:
		savetarget = self.target
		self.target = self.pathtarget
		if other.enemy and other.enemy.client:
			activator = other.enemy
		elif other.oldenemy and other.oldenemy.client:
			activator = other.oldenemy
		elif other.activator and other.activator.client:
			activator = other.activator
		else:
			activator = other
		g_utils.G_UseTargets (self, activator)
		self.target = savetarget


def SP_point_combat (self):
	if g_main.deathmatch.value:
		g_utils.G_FreeEdict (self)
		return
	self.solid = SOLID_TRIGGER
	self.touch = point_combat_touch
	q_shared.VectorSet (self.mins, -8, -8, -16)
	q_shared.VectorSet (self.maxs, 8, 8, 16)
	self.svflags = SVF_NOCLIENT
	g_main.gi.linkentity (self)


"""QUAKED viewthing (0 .5 .8) (-8 -8 -8) (8 8 8)
Just for the debugging level.  Don't use
"""
def TH_viewthing(ent):
	ent.s.frame = (ent.s.frame + 1) % 7
	ent.nextthink = g_main.level.time + FRAMETIME


def SP_viewthing(ent):
	g_main.gi.dprintf ("viewthing spawned\n")

	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	ent.s.renderfx = RF_FRAMELERP
	q_shared.VectorSet (ent.mins, -16, -16, -24)
	q_shared.VectorSet (ent.maxs, 16, 16, 32)
	ent.s.modelindex = g_main.gi.modelindex ("models/objects/banner/tris.md2")
	g_main.gi.linkentity (ent)
	ent.nextthink = g_main.level.time + 0.5
	ent.think = TH_viewthing
	return


"""QUAKED info_null (0 0.5 0) (-4 -4 -4) (4 4 4)
Used as a positional target for spotlights, etc.
"""
def SP_info_null (self):
	g_utils.G_FreeEdict (self)


"""QUAKED info_notnull (0 0.5 0) (-4 -4 -4) (4 4 4)
Used as a positional target for lightning.
"""
def SP_info_notnull (self):
	q_shared.VectorCopy (self.s.origin, self.absmin)
	q_shared.VectorCopy (self.s.origin, self.absmax)


"""QUAKED light (0 1 0) (-8 -8 -8) (8 8 8) START_OFF
Non-displayed light.
"""
START_OFF = 1

def light_use (self, other, activator):
	if self.spawnflags & START_OFF:
		g_main.gi.configstring (CS_LIGHTS+self.style, "m")
		self.spawnflags &= ~START_OFF
	else:
		g_main.gi.configstring (CS_LIGHTS+self.style, "a")
		self.spawnflags |= START_OFF


def SP_light (self):
	# no targeted lights in deathmatch, because they cause global messages
	if not self.targetname or g_main.deathmatch.value:
		g_utils.G_FreeEdict (self)
		return

	if self.style >= 32:
		self.use = light_use
		if self.spawnflags & START_OFF:
			g_main.gi.configstring (CS_LIGHTS+self.style, "a")
		else:
			g_main.gi.configstring (CS_LIGHTS+self.style, "m")


"""QUAKED func_wall (0 .5 .8) ? TRIGGER_SPAWN TOGGLE START_ON ANIMATED ANIMATED_FAST
This is just a solid wall if not inhibited
"""
def func_wall_use (self, other, activator):
	if self.solid == SOLID_NOT:
		self.solid = SOLID_BSP
		self.svflags &= ~SVF_NOCLIENT
		g_utils.KillBox (self)
	else:
		self.solid = SOLID_NOT
		self.svflags |= SVF_NOCLIENT
	g_main.gi.linkentity (self)

	if not (self.spawnflags & 2):
		self.use = None


def SP_func_wall (self):
	self.movetype = MOVETYPE_PUSH
	g_main.gi.setmodel (self, self.model)

	if self.spawnflags & 8:
		self.s.effects |= EF_ANIM_ALL
	if self.spawnflags & 16:
		self.s.effects |= EF_ANIM_ALLFAST

	# just a wall
	if (self.spawnflags & 7) == 0:
		self.solid = SOLID_BSP
		g_main.gi.linkentity (self)
		return

	# it must be TRIGGER_SPAWN
	if not (self.spawnflags & 1):
		self.spawnflags |= 1

	# yell if the spawnflags are odd
	if self.spawnflags & 4:
		if not (self.spawnflags & 2):
			g_main.gi.dprintf("func_wall START_ON without TOGGLE\n")
			self.spawnflags |= 2

	self.use = func_wall_use
	if self.spawnflags & 4:
		self.solid = SOLID_BSP
	else:
		self.solid = SOLID_NOT
		self.svflags |= SVF_NOCLIENT
	g_main.gi.linkentity (self)


"""QUAKED func_object (0 .5 .8) ? TRIGGER_SPAWN ANIMATED ANIMATED_FAST
This is solid bmodel that will fall if it's support it removed.
"""
def func_object_touch (self, other, plane, surf):
	# only squash thing we fall on top of
	if not plane:
		return
	if plane.normal[2] < 1.0:
		return
	if other.takedamage == DAMAGE_NO:
		return
	g_combat.T_Damage (other, self, self, q_shared.vec3_origin, self.s.origin, q_shared.vec3_origin, self.dmg, 1, 0, MOD_CRUSH)


def func_object_release (self):
	self.movetype = MOVETYPE_TOSS
	self.touch = func_object_touch


def func_object_use (self, other, activator):
	self.solid = SOLID_BSP
	self.svflags &= ~SVF_NOCLIENT
	self.use = None
	g_utils.KillBox (self)
	func_object_release (self)


def SP_func_object (self):
	g_main.gi.setmodel (self, self.model)

	self.mins[0] += 1
	self.mins[1] += 1
	self.mins[2] += 1
	self.maxs[0] -= 1
	self.maxs[1] -= 1
	self.maxs[2] -= 1

	if not self.dmg:
		self.dmg = 100

	if self.spawnflags == 0:
		self.solid = SOLID_BSP
		self.movetype = MOVETYPE_PUSH
		self.think = func_object_release
		self.nextthink = g_main.level.time + 2 * FRAMETIME
	else:
		self.solid = SOLID_NOT
		self.movetype = MOVETYPE_PUSH
		self.use = func_object_use
		self.svflags |= SVF_NOCLIENT

	if self.spawnflags & 2:
		self.s.effects |= EF_ANIM_ALL
	if self.spawnflags & 4:
		self.s.effects |= EF_ANIM_ALLFAST

	self.clipmask = MASK_MONSTERSOLID

	g_main.gi.linkentity (self)


"""QUAKED func_explosive (0 .5 .8) ? Trigger_Spawn ANIMATED ANIMATED_FAST
Any brush that you want to explode or break apart.
"""
def func_explosive_explode (self, inflictor, attacker, damage, point):
	#vec3_t origin, chunkorigin, size
	#int count, mass
	origin = [0, 0, 0]
	chunkorigin = [0, 0, 0]
	size = [0, 0, 0]

	# bmodel origins are (0 0 0), we need to adjust that here
	q_shared.VectorScale (self.size, 0.5, size)
	q_shared.VectorAdd (self.absmin, size, origin)
	q_shared.VectorCopy (origin, self.s.origin)

	self.takedamage = DAMAGE_NO

	if self.dmg:
		g_combat.T_RadiusDamage (self, attacker, self.dmg, None, self.dmg+40, MOD_EXPLOSIVE)

	q_shared.VectorSubtract (self.s.origin, inflictor.s.origin, self.velocity)
	q_shared.VectorNormalize (self.velocity)
	q_shared.VectorScale (self.velocity, 150, self.velocity)

	# start chunks towards the center
	q_shared.VectorScale (size, 0.5, size)

	mass = self.mass
	if not mass:
		mass = 75

	# big chunks
	if mass >= 100:
		count = mass // 100
		if count > 8:
			count = 8
		while count > 0:
			chunkorigin[0] = origin[0] + g_local.crandom() * size[0]
			chunkorigin[1] = origin[1] + g_local.crandom() * size[1]
			chunkorigin[2] = origin[2] + g_local.crandom() * size[2]
			ThrowDebris (self, "models/objects/debris1/tris.md2", 1, chunkorigin)
			count -= 1

	# small chunks
	count = mass // 25
	if count > 16:
		count = 16
	while count > 0:
		chunkorigin[0] = origin[0] + g_local.crandom() * size[0]
		chunkorigin[1] = origin[1] + g_local.crandom() * size[1]
		chunkorigin[2] = origin[2] + g_local.crandom() * size[2]
		ThrowDebris (self, "models/objects/debris2/tris.md2", 2, chunkorigin)
		count -= 1

	g_utils.G_UseTargets (self, attacker)

	if self.dmg:
		BecomeExplosion1 (self)
	else:
		g_utils.G_FreeEdict (self)


def func_explosive_use(self, other, activator):
	func_explosive_explode (self, self, other, self.health, q_shared.vec3_origin)


def func_explosive_spawn (self, other, activator):
	self.solid = SOLID_BSP
	self.svflags &= ~SVF_NOCLIENT
	self.use = None
	g_utils.KillBox (self)
	g_main.gi.linkentity (self)


def SP_func_explosive (self):
	if g_main.deathmatch.value:
		# auto-remove for deathmatch
		g_utils.G_FreeEdict (self)
		return

	self.movetype = MOVETYPE_PUSH

	g_main.gi.modelindex ("models/objects/debris1/tris.md2")
	g_main.gi.modelindex ("models/objects/debris2/tris.md2")

	g_main.gi.setmodel (self, self.model)

	if self.spawnflags & 1:
		self.svflags |= SVF_NOCLIENT
		self.solid = SOLID_NOT
		self.use = func_explosive_spawn
	else:
		self.solid = SOLID_BSP
		if self.targetname:
			self.use = func_explosive_use

	if self.spawnflags & 2:
		self.s.effects |= EF_ANIM_ALL
	if self.spawnflags & 4:
		self.s.effects |= EF_ANIM_ALLFAST

	if self.use != func_explosive_use:
		if not self.health:
			self.health = 100
		self.die = func_explosive_explode
		self.takedamage = DAMAGE_YES

	g_main.gi.linkentity (self)


"""QUAKED misc_explobox (0 .5 .8) (-16 -16 0) (16 16 40)
Large exploding box.
"""
def barrel_touch (self, other, plane, surf):
	#float ratio
	#vec3_t v
	v = [0, 0, 0]

	if (not other.groundentity) or (other.groundentity == self):
		return

	ratio = float(other.mass) / float(self.mass)
	q_shared.VectorSubtract (self.s.origin, other.s.origin, v)
	g_monster.M_walkmove (self, g_utils.vectoyaw(v), 20 * ratio * FRAMETIME)


def barrel_explode (self):
	#vec3_t org, save
	#float spd
	org = [0, 0, 0]
	save = [0, 0, 0]

	g_combat.T_RadiusDamage (self, self.activator, self.dmg, None, self.dmg+40, MOD_BARREL)

	q_shared.VectorCopy (self.s.origin, save)
	q_shared.VectorMA (self.absmin, 0.5, self.size, self.s.origin)

	# a few big chunks
	spd = 1.5 * float(self.dmg) / 200.0
	org[0] = self.s.origin[0] + g_local.crandom() * self.size[0]
	org[1] = self.s.origin[1] + g_local.crandom() * self.size[1]
	org[2] = self.s.origin[2] + g_local.crandom() * self.size[2]
	ThrowDebris (self, "models/objects/debris1/tris.md2", spd, org)
	org[0] = self.s.origin[0] + g_local.crandom() * self.size[0]
	org[1] = self.s.origin[1] + g_local.crandom() * self.size[1]
	org[2] = self.s.origin[2] + g_local.crandom() * self.size[2]
	ThrowDebris (self, "models/objects/debris1/tris.md2", spd, org)

	# bottom corners
	spd = 1.75 * float(self.dmg) / 200.0
	q_shared.VectorCopy (self.absmin, org)
	ThrowDebris (self, "models/objects/debris3/tris.md2", spd, org)
	q_shared.VectorCopy (self.absmin, org)
	org[0] += self.size[0]
	ThrowDebris (self, "models/objects/debris3/tris.md2", spd, org)
	q_shared.VectorCopy (self.absmin, org)
	org[1] += self.size[1]
	ThrowDebris (self, "models/objects/debris3/tris.md2", spd, org)
	q_shared.VectorCopy (self.absmin, org)
	org[0] += self.size[0]
	org[1] += self.size[1]
	ThrowDebris (self, "models/objects/debris3/tris.md2", spd, org)

	# a bunch of little chunks
	spd = 2 * self.dmg / 200
	for _ in range(8):
		org[0] = self.s.origin[0] + g_local.crandom() * self.size[0]
		org[1] = self.s.origin[1] + g_local.crandom() * self.size[1]
		org[2] = self.s.origin[2] + g_local.crandom() * self.size[2]
		ThrowDebris (self, "models/objects/debris2/tris.md2", spd, org)

	q_shared.VectorCopy (save, self.s.origin)
	if self.groundentity:
		BecomeExplosion2 (self)
	else:
		BecomeExplosion1 (self)


def barrel_delay (self, inflictor, attacker, damage, point):
	self.takedamage = DAMAGE_NO
	self.nextthink = g_main.level.time + 2 * FRAMETIME
	self.think = barrel_explode
	self.activator = attacker


def SP_misc_explobox (self):
	if g_main.deathmatch.value:
		# auto-remove for deathmatch
		g_utils.G_FreeEdict (self)
		return

	g_main.gi.modelindex ("models/objects/debris1/tris.md2")
	g_main.gi.modelindex ("models/objects/debris2/tris.md2")
	g_main.gi.modelindex ("models/objects/debris3/tris.md2")

	self.solid = SOLID_BBOX
	self.movetype = MOVETYPE_STEP

	self.model = "models/objects/barrels/tris.md2"
	self.s.modelindex = g_main.gi.modelindex (self.model)
	q_shared.VectorSet (self.mins, -16, -16, 0)
	q_shared.VectorSet (self.maxs, 16, 16, 40)

	if not self.mass:
		self.mass = 400
	if not self.health:
		self.health = 10
	if not self.dmg:
		self.dmg = 150

	self.die = barrel_delay
	self.takedamage = DAMAGE_YES
	self.monsterinfo.aiflags = AI_NOSTEP

	self.touch = barrel_touch

	self.think = g_monster.M_droptofloor
	self.nextthink = g_main.level.time + 2 * FRAMETIME

	g_main.gi.linkentity (self)


"""QUAKED misc_blackhole (1 .5 0) (-8 -8 -8) (8 8 8)
"""
def misc_blackhole_use (ent, other, activator):
	g_utils.G_FreeEdict (ent)


def misc_blackhole_think (self):
	if (self.s.frame + 1) < 19:
		self.s.frame += 1
		self.nextthink = g_main.level.time + FRAMETIME
	else:
		self.s.frame = 0
		self.nextthink = g_main.level.time + FRAMETIME


def SP_misc_blackhole (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_NOT
	q_shared.VectorSet (ent.mins, -64, -64, 0)
	q_shared.VectorSet (ent.maxs, 64, 64, 8)
	ent.s.modelindex = g_main.gi.modelindex ("models/objects/black/tris.md2")
	ent.s.renderfx = RF_TRANSLUCENT
	ent.use = misc_blackhole_use
	ent.think = misc_blackhole_think
	ent.nextthink = g_main.level.time + 2 * FRAMETIME
	g_main.gi.linkentity (ent)


"""QUAKED misc_eastertank (1 .5 0) (-32 -32 -16) (32 32 32)
"""
def misc_eastertank_think (self):
	if (self.s.frame + 1) < 293:
		self.s.frame += 1
		self.nextthink = g_main.level.time + FRAMETIME
	else:
		self.s.frame = 254
		self.nextthink = g_main.level.time + FRAMETIME


def SP_misc_eastertank (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	q_shared.VectorSet (ent.mins, -32, -32, -16)
	q_shared.VectorSet (ent.maxs, 32, 32, 32)
	ent.s.modelindex = g_main.gi.modelindex ("models/monsters/tank/tris.md2")
	ent.s.frame = 254
	ent.think = misc_eastertank_think
	ent.nextthink = g_main.level.time + 2 * FRAMETIME
	g_main.gi.linkentity (ent)


"""QUAKED misc_easterchick (1 .5 0) (-32 -32 0) (32 32 32)
"""
def misc_easterchick_think (self):
	if (self.s.frame + 1) < 247:
		self.s.frame += 1
		self.nextthink = g_main.level.time + FRAMETIME
	else:
		self.s.frame = 208
		self.nextthink = g_main.level.time + FRAMETIME


def SP_misc_easterchick (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	q_shared.VectorSet (ent.mins, -32, -32, 0)
	q_shared.VectorSet (ent.maxs, 32, 32, 32)
	ent.s.modelindex = g_main.gi.modelindex ("models/monsters/bitch/tris.md2")
	ent.s.frame = 208
	ent.think = misc_easterchick_think
	ent.nextthink = g_main.level.time + 2 * FRAMETIME
	g_main.gi.linkentity (ent)


"""QUAKED misc_easterchick2 (1 .5 0) (-32 -32 0) (32 32 32)
"""
def misc_easterchick2_think (self):
	if (self.s.frame + 1) < 287:
		self.s.frame += 1
		self.nextthink = g_main.level.time + FRAMETIME
	else:
		self.s.frame = 248
		self.nextthink = g_main.level.time + FRAMETIME


def SP_misc_easterchick2 (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	q_shared.VectorSet (ent.mins, -32, -32, 0)
	q_shared.VectorSet (ent.maxs, 32, 32, 32)
	ent.s.modelindex = g_main.gi.modelindex ("models/monsters/bitch/tris.md2")
	ent.s.frame = 248
	ent.think = misc_easterchick2_think
	ent.nextthink = g_main.level.time + 2 * FRAMETIME
	g_main.gi.linkentity (ent)


"""QUAKED monster_commander_body (1 .5 0) (-32 -32 0) (32 32 48)
Not really a monster, this is the Tank Commander's decapitated body.
"""
def commander_body_think (self):
	if (self.s.frame + 1) < 24:
		self.s.frame += 1
		self.nextthink = g_main.level.time + FRAMETIME
	else:
		self.nextthink = 0

	if self.s.frame == 22:
		g_main.gi.sound (self, CHAN_BODY, g_main.gi.soundindex ("tank/thud.wav"), 1, ATTN_NORM, 0)


def commander_body_use (self, other, activator):
	self.think = commander_body_think
	self.nextthink = g_main.level.time + FRAMETIME
	g_main.gi.sound (self, CHAN_BODY, g_main.gi.soundindex ("tank/pain.wav"), 1, ATTN_NORM, 0)


def commander_body_drop (self):
	self.movetype = MOVETYPE_TOSS
	self.s.origin[2] += 2


def SP_monster_commander_body (self):
	self.movetype = MOVETYPE_NONE
	self.solid = SOLID_BBOX
	self.model = "models/monsters/commandr/tris.md2"
	self.s.modelindex = g_main.gi.modelindex (self.model)
	q_shared.VectorSet (self.mins, -32, -32, 0)
	q_shared.VectorSet (self.maxs, 32, 32, 48)
	self.use = commander_body_use
	self.takedamage = DAMAGE_YES
	self.flags = FL_GODMODE
	self.s.renderfx |= RF_FRAMELERP
	g_main.gi.linkentity (self)

	g_main.gi.soundindex ("tank/thud.wav")
	g_main.gi.soundindex ("tank/pain.wav")

	self.think = commander_body_drop
	self.nextthink = g_main.level.time + 5 * FRAMETIME


"""QUAKED misc_banner (1 .5 0) (-4 -4 -4) (4 4 4)
The origin is the bottom of the banner.  The banner is 128 tall.
"""
def misc_banner_think (ent):
	ent.s.frame = (ent.s.frame + 1) % 16
	ent.nextthink = g_main.level.time + FRAMETIME


def SP_misc_banner (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_NOT
	ent.s.modelindex = g_main.gi.modelindex ("models/objects/banner/tris.md2")
	ent.s.frame = _r.randint(0, 2147483647) % 16
	g_main.gi.linkentity (ent)

	ent.think = misc_banner_think
	ent.nextthink = g_main.level.time + FRAMETIME


"""QUAKED misc_deadsoldier (1 .5 0) (-16 -16 0) (16 16 16) ON_BACK ON_STOMACH BACK_DECAP FETAL_POS SIT_DECAP IMPALED
This is the dead player model.
"""
def misc_deadsoldier_die (self, inflictor, attacker, damage, point):
	#int n

	if self.health > -80:
		return

	g_main.gi.sound (self, CHAN_BODY, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
	for n in range(4):
		ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
	ThrowHead (self, "models/objects/gibs/head2/tris.md2", damage, GIB_ORGANIC)


def SP_misc_deadsoldier (ent):
	if g_main.deathmatch.value:
		# auto-remove for deathmatch
		g_utils.G_FreeEdict (ent)
		return

	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	ent.s.modelindex = g_main.gi.modelindex ("models/deadbods/dude/tris.md2")

	# Defaults to frame 0
	if ent.spawnflags & 2:
		ent.s.frame = 1
	elif ent.spawnflags & 4:
		ent.s.frame = 2
	elif ent.spawnflags & 8:
		ent.s.frame = 3
	elif ent.spawnflags & 16:
		ent.s.frame = 4
	elif ent.spawnflags & 32:
		ent.s.frame = 5
	else:
		ent.s.frame = 0

	q_shared.VectorSet (ent.mins, -16, -16, 0)
	q_shared.VectorSet (ent.maxs, 16, 16, 16)
	ent.deadflag = DEAD_DEAD
	ent.takedamage = DAMAGE_YES
	ent.svflags |= SVF_MONSTER|SVF_DEADMONSTER
	ent.die = misc_deadsoldier_die
	ent.monsterinfo.aiflags |= AI_GOOD_GUY

	g_main.gi.linkentity (ent)


"""QUAKED misc_viper (1 .5 0) (-16 -16 0) (16 16 32)
This is the Viper for the flyby bombing.
"""
def misc_viper_use  (self, other, activator):
	self.svflags &= ~SVF_NOCLIENT
	self.use = g_target.train_use
	g_target.train_use (self, other, activator)


def SP_misc_viper (ent):
	if not ent.target:
		g_main.gi.dprintf ("misc_viper without a target at %s\n", g_utils.vtos(ent.absmin))
		g_utils.G_FreeEdict (ent)
		return

	if not ent.speed:
		ent.speed = 300

	ent.movetype = MOVETYPE_PUSH
	ent.solid = SOLID_NOT
	ent.s.modelindex = g_main.gi.modelindex ("models/ships/viper/tris.md2")
	q_shared.VectorSet (ent.mins, -16, -16, 0)
	q_shared.VectorSet (ent.maxs, 16, 16, 32)

	ent.think = g_target.func_train_find
	ent.nextthink = g_main.level.time + FRAMETIME
	ent.use = misc_viper_use
	ent.svflags |= SVF_NOCLIENT
	ent.moveinfo.accel = ent.moveinfo.decel = ent.moveinfo.speed = ent.speed

	g_main.gi.linkentity (ent)


"""QUAKED misc_bigviper (1 .5 0) (-176 -120 -24) (176 120 72)
This is a large stationary viper as seen in Paul's intro
"""
def SP_misc_bigviper (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	q_shared.VectorSet (ent.mins, -176, -120, -24)
	q_shared.VectorSet (ent.maxs, 176, 120, 72)
	ent.s.modelindex = g_main.gi.modelindex ("models/ships/bigviper/tris.md2")
	g_main.gi.linkentity (ent)


"""QUAKED misc_viper_bomb (1 0 0) (-8 -8 -8) (8 8 8)
"dmg" how much boom should the bomb make?
"""
def misc_viper_bomb_touch (self, other, plane, surf):
	g_utils.G_UseTargets (self, self.activator)

	self.s.origin[2] = self.absmin[2] + 1
	g_combat.T_RadiusDamage (self, self, self.dmg, None, self.dmg+40, MOD_BOMB)
	BecomeExplosion2 (self)


def misc_viper_bomb_prethink (self):
	#vec3_t v
	#float diff
	v = [0, 0, 0]

	self.groundentity = None

	diff = self.timestamp - g_main.level.time
	if diff < -1.0:
		diff = -1.0

	q_shared.VectorScale (self.moveinfo.dir, 1.0 + diff, v)
	v[2] = diff

	diff = self.s.angles[2]
	g_utils.vectoangles (v, self.s.angles)
	self.s.angles[2] = diff + 10


def misc_viper_bomb_use (self, other, activator):
	#edict_t *viper

	self.solid = SOLID_BBOX
	self.svflags &= ~SVF_NOCLIENT
	self.s.effects |= EF_ROCKET
	self.use = None
	self.movetype = MOVETYPE_TOSS
	self.prethink = misc_viper_bomb_prethink
	self.touch = misc_viper_bomb_touch
	self.activator = activator

	viper = g_utils.G_Find (None, "classname", "misc_viper")
	q_shared.VectorScale (viper.moveinfo.dir, viper.moveinfo.speed, self.velocity)

	self.timestamp = g_main.level.time
	q_shared.VectorCopy (viper.moveinfo.dir, self.moveinfo.dir)


def SP_misc_viper_bomb (self):
	self.movetype = MOVETYPE_NONE
	self.solid = SOLID_NOT
	q_shared.VectorSet (self.mins, -8, -8, -8)
	q_shared.VectorSet (self.maxs, 8, 8, 8)

	self.s.modelindex = g_main.gi.modelindex ("models/objects/bomb/tris.md2")

	if not self.dmg:
		self.dmg = 1000

	self.use = misc_viper_bomb_use
	self.svflags |= SVF_NOCLIENT

	g_main.gi.linkentity (self)


"""QUAKED misc_strogg_ship (1 .5 0) (-16 -16 0) (16 16 32)
This is a Storgg ship for the flybys.
"""
def misc_strogg_ship_use  (self, other, activator):
	self.svflags &= ~SVF_NOCLIENT
	self.use = g_target.train_use
	g_target.train_use (self, other, activator)


def SP_misc_strogg_ship (ent):
	if not ent.target:
		g_main.gi.dprintf ("%s without a target at %s\n", ent.classname, g_utils.vtos(ent.absmin))
		g_utils.G_FreeEdict (ent)
		return

	if not ent.speed:
		ent.speed = 300

	ent.movetype = MOVETYPE_PUSH
	ent.solid = SOLID_NOT
	ent.s.modelindex = g_main.gi.modelindex ("models/ships/strogg1/tris.md2")
	q_shared.VectorSet (ent.mins, -16, -16, 0)
	q_shared.VectorSet (ent.maxs, 16, 16, 32)

	ent.think = g_target.func_train_find
	ent.nextthink = g_main.level.time + FRAMETIME
	ent.use = misc_strogg_ship_use
	ent.svflags |= SVF_NOCLIENT
	ent.moveinfo.accel = ent.moveinfo.decel = ent.moveinfo.speed = ent.speed

	g_main.gi.linkentity (ent)


"""QUAKED misc_satellite_dish (1 .5 0) (-64 -64 0) (64 64 128)
"""
def misc_satellite_dish_think (self):
	self.s.frame += 1
	if self.s.frame < 38:
		self.nextthink = g_main.level.time + FRAMETIME


def misc_satellite_dish_use (self, other, activator):
	self.s.frame = 0
	self.think = misc_satellite_dish_think
	self.nextthink = g_main.level.time + FRAMETIME


def SP_misc_satellite_dish (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	q_shared.VectorSet (ent.mins, -64, -64, 0)
	q_shared.VectorSet (ent.maxs, 64, 64, 128)
	ent.s.modelindex = g_main.gi.modelindex ("models/objects/satellite/tris.md2")
	ent.use = misc_satellite_dish_use
	g_main.gi.linkentity (ent)


"""QUAKED light_mine1 (0 1 0) (-2 -2 -12) (2 2 12)
"""
def SP_light_mine1 (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	ent.s.modelindex = g_main.gi.modelindex ("models/objects/minelite/light1/tris.md2")
	g_main.gi.linkentity (ent)


"""QUAKED light_mine2 (0 1 0) (-2 -2 -12) (2 2 12)
"""
def SP_light_mine2 (ent):
	ent.movetype = MOVETYPE_NONE
	ent.solid = SOLID_BBOX
	ent.s.modelindex = g_main.gi.modelindex ("models/objects/minelite/light2/tris.md2")
	g_main.gi.linkentity (ent)


"""QUAKED misc_gib_arm (1 0 0) (-8 -8 -8) (8 8 8)
Intended for use with the target_spawner
"""
def SP_misc_gib_arm (ent):
	g_main.gi.setmodel (ent, "models/objects/gibs/arm/tris.md2")
	ent.solid = SOLID_NOT
	ent.s.effects |= EF_GIB
	ent.takedamage = DAMAGE_YES
	ent.die = gib_die
	ent.movetype = MOVETYPE_TOSS
	ent.svflags |= SVF_MONSTER
	ent.deadflag = DEAD_DEAD
	ent.avelocity[0] = g_local.random()*200
	ent.avelocity[1] = g_local.random()*200
	ent.avelocity[2] = g_local.random()*200
	ent.think = g_utils.G_FreeEdict
	ent.nextthink = g_main.level.time + 30
	g_main.gi.linkentity (ent)


"""QUAKED misc_gib_leg (1 0 0) (-8 -8 -8) (8 8 8)
Intended for use with the target_spawner
"""
def SP_misc_gib_leg (ent):
	g_main.gi.setmodel (ent, "models/objects/gibs/leg/tris.md2")
	ent.solid = SOLID_NOT
	ent.s.effects |= EF_GIB
	ent.takedamage = DAMAGE_YES
	ent.die = gib_die
	ent.movetype = MOVETYPE_TOSS
	ent.svflags |= SVF_MONSTER
	ent.deadflag = DEAD_DEAD
	ent.avelocity[0] = g_local.random()*200
	ent.avelocity[1] = g_local.random()*200
	ent.avelocity[2] = g_local.random()*200
	ent.think = g_utils.G_FreeEdict
	ent.nextthink = g_main.level.time + 30
	g_main.gi.linkentity (ent)


"""QUAKED misc_gib_head (1 0 0) (-8 -8 -8) (8 8 8)
Intended for use with the target_spawner
"""
def SP_misc_gib_head (ent):
	g_main.gi.setmodel (ent, "models/objects/gibs/head/tris.md2")
	ent.solid = SOLID_NOT
	ent.s.effects |= EF_GIB
	ent.takedamage = DAMAGE_YES
	ent.die = gib_die
	ent.movetype = MOVETYPE_TOSS
	ent.svflags |= SVF_MONSTER
	ent.deadflag = DEAD_DEAD
	ent.avelocity[0] = g_local.random()*200
	ent.avelocity[1] = g_local.random()*200
	ent.avelocity[2] = g_local.random()*200
	ent.think = g_utils.G_FreeEdict
	ent.nextthink = g_main.level.time + 30
	g_main.gi.linkentity (ent)


"""QUAKED target_character (0 0 1) ?
used with target_string (must be on same "team")
"count" is position in the string (starts at 1)
"""
def SP_target_character (self):
	self.movetype = MOVETYPE_PUSH
	g_main.gi.setmodel (self, self.model)
	self.solid = SOLID_BSP
	self.s.frame = 12
	g_main.gi.linkentity (self)
	return


"""QUAKED target_string (0 0 1) (-8 -8 -8) (8 8 8)
"""
def target_string_use (self, other, activator):
	#edict_t *e
	#int n, l
	#c

	l = len(self.message)
	e = self.teammaster
	while e:
		if not e.count:
			e = e.teamchain
			continue
		n = e.count - 1
		if n > l:
			e.s.frame = 12
			e = e.teamchain
			continue

		c = self.message[n]
		if '0' <= c <= '9':
			e.s.frame = ord(c) - ord('0')
		elif c == '-':
			e.s.frame = 10
		elif c == ':':
			e.s.frame = 11
		else:
			e.s.frame = 12
		e = e.teamchain


def SP_target_string (self):
	if not self.message:
		self.message = ""
	self.use = target_string_use


"""QUAKED func_clock (0 0 1) (-8 -8 -8) (8 8 8) TIMER_UP TIMER_DOWN START_OFF MULTI_USE
target a target_string with this
"""
import time as _time
CLOCK_MESSAGE_SIZE = 16

def func_clock_reset (self):
	self.activator = None
	if self.spawnflags & 1:
		self.health = 0
		self.wait = self.count
	elif self.spawnflags & 2:
		self.health = self.count
		self.wait = 0


def func_clock_format_countdown (self):
	if self.style == 0:
		self.message = "%2i" % self.health
		return

	if self.style == 1:
		self.message = "%2i:%2i" % (self.health // 60, self.health % 60)
		if len(self.message) > 3 and self.message[3] == ' ':
			self.message = self.message[:3] + '0' + self.message[4:]
		return

	if self.style == 2:
		self.message = "%2i:%2i:%2i" % (self.health // 3600, (self.health - (self.health // 3600) * 3600) // 60, self.health % 60)
		if len(self.message) > 3 and self.message[3] == ' ':
			self.message = self.message[:3] + '0' + self.message[4:]
		if len(self.message) > 6 and self.message[6] == ' ':
			self.message = self.message[:6] + '0' + self.message[7:]
		return


def func_clock_think (self):
	if not self.enemy:
		self.enemy = g_utils.G_Find (None, "targetname", self.target)
		if not self.enemy:
			return

	if self.spawnflags & 1:
		func_clock_format_countdown (self)
		self.health += 1
	elif self.spawnflags & 2:
		func_clock_format_countdown (self)
		self.health -= 1
	else:
		ltime = _time.localtime()
		self.message = "%2i:%2i:%2i" % (ltime.tm_hour, ltime.tm_min, ltime.tm_sec)
		if len(self.message) > 3 and self.message[3] == ' ':
			self.message = self.message[:3] + '0' + self.message[4:]
		if len(self.message) > 6 and self.message[6] == ' ':
			self.message = self.message[:6] + '0' + self.message[7:]

	self.enemy.message = self.message
	self.enemy.use (self.enemy, self, self)

	if (((self.spawnflags & 1) and (self.health > self.wait)) or
		((self.spawnflags & 2) and (self.health < self.wait))):
		if self.pathtarget:
			savetarget = self.target
			savemessage = self.message
			self.target = self.pathtarget
			self.message = None
			g_utils.G_UseTargets (self, self.activator)
			self.target = savetarget
			self.message = savemessage

		if not (self.spawnflags & 8):
			return

		func_clock_reset (self)

		if self.spawnflags & 4:
			return

	self.nextthink = g_main.level.time + 1


def func_clock_use (self, other, activator):
	if not (self.spawnflags & 8):
		self.use = None
	if self.activator:
		return
	self.activator = activator
	self.think (self)


def SP_func_clock (self):
	if not self.target:
		g_main.gi.dprintf("%s with no target at %s\n", self.classname, g_utils.vtos(self.s.origin))
		g_utils.G_FreeEdict (self)
		return

	if (self.spawnflags & 2) and (not self.count):
		g_main.gi.dprintf("%s with no count at %s\n", self.classname, g_utils.vtos(self.s.origin))
		g_utils.G_FreeEdict (self)
		return

	if (self.spawnflags & 1) and (not self.count):
		self.count = 60*60

	func_clock_reset (self)

	self.message = ""

	self.think = func_clock_think

	if self.spawnflags & 4:
		self.use = func_clock_use
	else:
		self.nextthink = g_main.level.time + 1


def teleporter_touch (self, other, plane, surf):
	#edict_t *dest
	#int i

	if not other.client:
		return
	dest = g_utils.G_Find (None, "targetname", self.target)
	if not dest:
		g_main.gi.dprintf ("Couldn't find destination\n")
		return

	# unlink to make sure it can't possibly interfere with KillBox
	g_main.gi.unlinkentity (other)

	q_shared.VectorCopy (dest.s.origin, other.s.origin)
	q_shared.VectorCopy (dest.s.origin, other.s.old_origin)
	other.s.origin[2] += 10

	# clear the velocity and hold them in place briefly
	q_shared.VectorClear (other.velocity)
	other.client.ps.pmove.pm_time = 160>>3		# hold time
	other.client.ps.pmove.pm_flags |= PMF_TIME_TELEPORT

	# draw the teleport splash at source and on the player
	self.owner.s.event = EV_PLAYER_TELEPORT
	other.s.event = EV_PLAYER_TELEPORT

	# set angles
	for i in range(3):
		other.client.ps.pmove.delta_angles[i] = ANGLE2SHORT(dest.s.angles[i] - other.client.resp.cmd_angles[i])

	q_shared.VectorClear (other.s.angles)
	q_shared.VectorClear (other.client.ps.viewangles)
	q_shared.VectorClear (other.client.v_angle)

	# kill anything at the destination
	g_utils.KillBox (other)

	g_main.gi.linkentity (other)


"""QUAKED misc_teleporter (1 0 0) (-32 -32 -24) (32 32 -16)
Stepping onto this disc will teleport players to the targeted misc_teleporter_dest object.
"""
def SP_misc_teleporter (ent):
	#edict_t *trig

	if not ent.target:
		g_main.gi.dprintf ("teleporter without a target.\n")
		g_utils.G_FreeEdict (ent)
		return

	g_main.gi.setmodel (ent, "models/objects/dmspot/tris.md2")
	ent.s.skinnum = 1
	ent.s.effects = EF_TELEPORTER
	ent.s.sound = g_main.gi.soundindex ("world/amb10.wav")
	ent.solid = SOLID_BBOX

	q_shared.VectorSet (ent.mins, -32, -32, -24)
	q_shared.VectorSet (ent.maxs, 32, 32, -16)
	g_main.gi.linkentity (ent)

	trig = g_utils.G_Spawn ()
	trig.touch = teleporter_touch
	trig.solid = SOLID_TRIGGER
	trig.target = ent.target
	trig.owner = ent
	q_shared.VectorCopy (ent.s.origin, trig.s.origin)
	q_shared.VectorSet (trig.mins, -8, -8, 8)
	q_shared.VectorSet (trig.maxs, 8, 8, 24)
	g_main.gi.linkentity (trig)


"""QUAKED misc_teleporter_dest (1 0 0) (-32 -32 -24) (32 32 -16)
Point teleporters at these.
"""
def SP_misc_teleporter_dest (ent):
	g_main.gi.setmodel (ent, "models/objects/dmspot/tris.md2")
	ent.s.skinnum = 0
	ent.solid = SOLID_BBOX
	q_shared.VectorSet (ent.mins, -32, -32, -24)
	q_shared.VectorSet (ent.maxs, 32, 32, -16)
	g_main.gi.linkentity (ent)
