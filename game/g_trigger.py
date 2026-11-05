#
# Copyright (C) 1997-2001 Id Software, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
"""
#include "g_local.h"

// the wait time has passed, so set back up for another activation

// the trigger was just activated
// ent->activator should be set to the activator so it can be held through a delay
// so wait for the delay time before firing

#define PUSH_ONCE		1

"""
from __future__ import annotations

import random as _r
pass
from game import g_local
from game import g_main
from game import g_utils
from game import g_combat
from game import g_items
from game.game import SVF_MONSTER, SVF_DEADMONSTER, SVF_NOCLIENT
from game.game import solid_t
SOLID_TRIGGER = solid_t.SOLID_TRIGGER.value
SOLID_BSP = solid_t.SOLID_BSP.value
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value
from common.header.shared import ATTN_NORM, CHAN_AUTO, YAW
from common.header import shared
from common.shared import shared as shared_c

PUSH_ONCE = 1
windsound = None  # int

def InitTrigger (self):
	#edict_t *self
	if not shared_c.VectorCompare(self.s.angles, shared_c.vec3_origin):
		g_utils.G_SetMovedir (self.s.angles, self.movedir)

	self.solid = SOLID_TRIGGER
	self.movetype = g_local.MOVETYPE_NONE
	g_main.gi.setmodel (self, self.model)
	self.svflags = SVF_NOCLIENT


# the wait time has passed, so set back up for another activation
def multi_wait (ent):
	#edict_t *ent
	ent.nextthink = 0


# the trigger was just activated
# ent.activator should be set to the activator so it can be held through a delay
# so wait for the delay time before firing
def multi_trigger (ent):
	#edict_t *ent
	if ent.nextthink:
		return  # already been triggered

	g_utils.G_UseTargets (ent, ent.activator)

	if ent.wait > 0:
		ent.think = multi_wait
		ent.nextthink = g_main.level.time + ent.wait
	else:
		# we can't just remove (self) here, because this is a touch function
		# called while looping through area links...
		ent.touch = None
		ent.nextthink = g_main.level.time + g_local.FRAMETIME
		ent.think = g_utils.G_FreeEdict

def Use_Multi (ent, other, activator):
	#edict_t *ent, *other, *activator
	ent.activator = activator
	multi_trigger (ent)

def Touch_Multi (self, other, plane, surf):
	#edict_t *self, *other; cplane_t *plane; csurface_t *surf
	if other.client:
		if self.spawnflags & 2:
			return
	elif other.svflags & SVF_MONSTER:
		if not (self.spawnflags & 1):
			return
	else:
		return

	if not shared_c.VectorCompare(self.movedir, shared_c.vec3_origin):
		forward = [0.0, 0.0, 0.0]
		shared_c.AngleVectors(other.s.angles, forward, None, None)
		if shared.DotProduct(forward, self.movedir) < 0:
			return

	self.activator = other
	multi_trigger (self)

def trigger_enable (self, other, activator):
	#edict_t *self, *other, *activator
	self.solid = SOLID_TRIGGER
	self.use = Use_Multi
	g_main.gi.linkentity (self)

def SP_trigger_multiple (ent):
	#edict_t *ent
	if ent.sounds == 1:
		ent.noise_index = g_main.gi.soundindex ("misc/secret.wav")
	elif ent.sounds == 2:
		ent.noise_index = g_main.gi.soundindex ("misc/talk.wav")
	elif ent.sounds == 3:
		ent.noise_index = g_main.gi.soundindex ("misc/trigger1.wav")

	if not ent.wait:
		ent.wait = 0.2
	ent.touch = Touch_Multi
	ent.movetype = g_local.MOVETYPE_NONE
	ent.svflags |= SVF_NOCLIENT

	if ent.spawnflags & 4:
		ent.solid = SOLID_NOT
		ent.use = trigger_enable
	else:
		ent.solid = SOLID_TRIGGER
		ent.use = Use_Multi

	if not shared_c.VectorCompare(ent.s.angles, shared_c.vec3_origin):
		g_utils.G_SetMovedir (ent.s.angles, ent.movedir)

	g_main.gi.setmodel (ent, ent.model)
	g_main.gi.linkentity (ent)

def SP_trigger_once (ent):
	#edict_t *ent
	# make old maps work because I messed up on flag assignments here
	# triggered was on bit 1 when it should have been on bit 4
	if ent.spawnflags & 1:
		v = [0.0, 0.0, 0.0]
		shared_c.VectorMA (ent.mins, 0.5, ent.size, v)
		ent.spawnflags &= ~1
		ent.spawnflags |= 4
		g_main.gi.dprintf("fixed TRIGGERED flag on %s at %s\n", ent.classname, g_utils.vtos(v))

	ent.wait = -1
	SP_trigger_multiple (ent)

def trigger_relay_use (self, other, activator):
	#edict_t *self, *other, *activator
	g_utils.G_UseTargets (self, activator)

def SP_trigger_relay (self):
	#edict_t *self
	self.use = trigger_relay_use

def trigger_key_use (self, other, activator):
	#edict_t *self, *other, *activator
	index = None

	if not self.item:
		return
	if not activator.client:
		return

	index = g_items.ITEM_INDEX(self.item)
	if not activator.client.pers.inventory[index]:
		if g_main.level.time < self.touch_debounce_time:
			return
		self.touch_debounce_time = g_main.level.time + 5.0
		g_main.gi.centerprintf (activator, "You need the %s", self.item.pickup_name)
		g_main.gi.sound (activator, CHAN_AUTO, g_main.gi.soundindex ("misc/keytry.wav"), 1, ATTN_NORM, 0)
		return

	g_main.gi.sound (activator, CHAN_AUTO, g_main.gi.soundindex ("misc/keyuse.wav"), 1, ATTN_NORM, 0)
	if g_main.coop.value:
		player = 0
		ent = None

		if shared_c.Q_stricmp(self.item.classname, "key_power_cube") == 0:
			cube = 0
			while cube < 8:
				if activator.client.pers.power_cubes & (1 << cube):
					break
				cube += 1
			for player in range(1, int(g_main.game.maxclients)+1):
				ent = g_main.g_edicts[player]
				if not ent.inuse:
					continue
				if not ent.client:
					continue
				if ent.client.pers.power_cubes & (1 << cube):
					ent.client.pers.inventory[index] -= 1
					ent.client.pers.power_cubes &= ~(1 << cube)
		else:
			for player in range(1, int(g_main.game.maxclients)+1):
				ent = g_main.g_edicts[player]
				if not ent.inuse:
					continue
				if not ent.client:
					continue
				ent.client.pers.inventory[index] = 0
	else:
		activator.client.pers.inventory[index] -= 1

	g_utils.G_UseTargets (self, activator)

	self.use = None

def SP_trigger_key (self):
	#edict_t *self
	if not g_main.st.item:
		g_main.gi.dprintf("no key item for trigger_key at %s\n", g_utils.vtos(self.s.origin))
		return
	self.item = g_items.FindItemByClassname (g_main.st.item)

	if not self.item:
		g_main.gi.dprintf("item %s not found for trigger_key at %s\n", g_main.st.item, g_utils.vtos(self.s.origin))
		return

	if not self.target:
		g_main.gi.dprintf("%s at %s has no target\n", self.classname, g_utils.vtos(self.s.origin))
		return

	g_main.gi.soundindex ("misc/keytry.wav")
	g_main.gi.soundindex ("misc/keyuse.wav")

	self.use = trigger_key_use

def trigger_counter_use (self, other, activator):
	#edict_t *self, *other, *activator
	if self.count == 0:
		return

	self.count -= 1

	if self.count:
		if not (self.spawnflags & 1):
			g_main.gi.centerprintf(activator, "%i more to go...", self.count)
			g_main.gi.sound (activator, CHAN_AUTO, g_main.gi.soundindex ("misc/talk1.wav"), 1, ATTN_NORM, 0)
		return

	if not (self.spawnflags & 1):
		g_main.gi.centerprintf(activator, "Sequence completed!")
		g_main.gi.sound (activator, CHAN_AUTO, g_main.gi.soundindex ("misc/talk1.wav"), 1, ATTN_NORM, 0)
	self.activator = activator
	multi_trigger (self)

def SP_trigger_counter (self):
	#edict_t *self
	self.wait = -1
	if not self.count:
		self.count = 2

	self.use = trigger_counter_use

def SP_trigger_always (ent):
	#edict_t *ent
	# we must have some delay to make sure our use targets are present
	if ent.delay < 0.2:
		ent.delay = 0.2
	g_utils.G_UseTargets(ent, ent)

def trigger_push_touch (self, other, plane, surf):
	#edict_t *self, *other; cplane_t *plane; csurface_t *surf
	global windsound
	if other.classname == "grenade":
		shared_c.VectorScale (self.movedir, self.speed * 10, other.velocity)
	elif other.health > 0:
		shared_c.VectorScale (self.movedir, self.speed * 10, other.velocity)

		if other.client:
			# don't take falling damage immediately from this
			shared.VectorCopy (other.velocity, other.client.oldvelocity)
			if other.fly_sound_debounce_time < g_main.level.time:
				other.fly_sound_debounce_time = g_main.level.time + 1.5
				g_main.gi.sound (other, CHAN_AUTO, windsound, 1, ATTN_NORM, 0)
	if self.spawnflags & PUSH_ONCE:
		g_utils.G_FreeEdict (self)

def SP_trigger_push (self):
	#edict_t *self
	InitTrigger (self)
	global windsound
	windsound = g_main.gi.soundindex ("misc/windfly.wav")
	self.touch = trigger_push_touch
	if not self.speed:
		self.speed = 1000
	g_main.gi.linkentity (self)

def hurt_use (self, other, activator):
	#edict_t *self, *other, *activator
	if self.solid == SOLID_NOT:
		self.solid = SOLID_TRIGGER
	else:
		self.solid = SOLID_NOT
	g_main.gi.linkentity (self)

	if not (self.spawnflags & 2):
		self.use = None

def hurt_touch (self, other, plane, surf):
	#edict_t *self, *other; cplane_t *plane; csurface_t *surf
	dflags = 0

	if not other.takedamage:
		return

	if self.timestamp > g_main.level.time:
		return

	if self.spawnflags & 16:
		self.timestamp = g_main.level.time + 1
	else:
		self.timestamp = g_main.level.time + g_local.FRAMETIME

	if not (self.spawnflags & 4):
		if (g_main.level.framenum % 10) == 0:
			g_main.gi.sound (other, CHAN_AUTO, self.noise_index, 1, ATTN_NORM, 0)

	if self.spawnflags & 8:
		dflags = g_local.DAMAGE_NO_PROTECTION
	else:
		dflags = 0
	g_combat.T_Damage (other, self, self, shared_c.vec3_origin, other.s.origin, shared_c.vec3_origin, self.dmg, self.dmg, dflags, g_local.MOD_TRIGGER_HURT)

def SP_trigger_hurt (self):
	#edict_t *self
	InitTrigger (self)

	self.noise_index = g_main.gi.soundindex ("world/electro.wav")
	self.touch = hurt_touch

	if not self.dmg:
		self.dmg = 5

	if self.spawnflags & 1:
		self.solid = SOLID_NOT
	else:
		self.solid = SOLID_TRIGGER

	if self.spawnflags & 2:
		self.use = hurt_use

	g_main.gi.linkentity (self)

def trigger_gravity_touch (self, other, plane, surf):
	#edict_t *self, *other; cplane_t *plane; csurface_t *surf
	other.gravity = self.gravity

def SP_trigger_gravity (self):
	#edict_t *self
	if g_main.st.gravity == 0:
		g_main.gi.dprintf("trigger_gravity without gravity set at %s\n", g_utils.vtos(self.s.origin))
		g_utils.G_FreeEdict (self)
		return

	InitTrigger (self)
	self.gravity = int(g_main.st.gravity)
	self.touch = trigger_gravity_touch

def trigger_monsterjump_touch (self, other, plane, surf):
	#edict_t *self, *other; cplane_t *plane; csurface_t *surf
	if other.flags & (g_local.FL_FLY | g_local.FL_SWIM):
		return
	if other.svflags & SVF_DEADMONSTER:
		return
	if not (other.svflags & SVF_MONSTER):
		return

	# set XY even if not on ground, so the jump will clear lips
	other.velocity[0] = self.movedir[0] * self.speed
	other.velocity[1] = self.movedir[1] * self.speed

	if not other.groundentity:
		return

	other.groundentity = None
	other.velocity[2] = self.movedir[2]

def SP_trigger_monsterjump (self):
	#edict_t *self
	if not self.speed:
		self.speed = 200
	if not g_main.st.height:
		g_main.st.height = 200
	if self.s.angles[YAW] == 0:
		self.s.angles[YAW] = 360
	InitTrigger (self)
	self.touch = trigger_monsterjump_touch
	self.movedir[2] = g_main.st.height
