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


void InitTrigger (edict_t *self)
{
	if (!VectorCompare (self->s.angles, vec3_origin))
		G_SetMovedir (self->s.angles, self->movedir);

	self->solid = SOLID_TRIGGER;
	self->movetype = MOVETYPE_NONE;
	gi.setmodel (self, self->model);
	self->svflags = SVF_NOCLIENT;
}


// the wait time has passed, so set back up for another activation
void multi_wait (edict_t *ent)
{
	ent->nextthink = 0;
}


// the trigger was just activated
// ent->activator should be set to the activator so it can be held through a delay
// so wait for the delay time before firing
void multi_trigger (edict_t *ent)
{
	if (ent->nextthink)
		return;		// already been triggered

	G_UseTargets (ent, ent->activator);

	if (ent->wait > 0)
	{
		ent->think = multi_wait;
		ent->nextthink = level.time + ent->wait;
	}
	else
	{	// we can't just remove (self) here, because this is a touch function
		// called while looping through area links...
		ent->touch = NULL;
		ent->nextthink = level.time + FRAMETIME;
		ent->think = G_FreeEdict;
	}
}

void Use_Multi (edict_t *ent, edict_t *other, edict_t *activator)
{
	ent->activator = activator;
	multi_trigger (ent);
}

void Touch_Multi (edict_t *self, edict_t *other, cplane_t *plane, csurface_t *surf)
{
	if(other->client)
	{
		if (self->spawnflags & 2)
			return;
	}
	else if (other->svflags & SVF_MONSTER)
	{
		if (!(self->spawnflags & 1))
			return;
	}
	else
		return;

	if (!VectorCompare(self->movedir, vec3_origin))
	{
		vec3_t	forward;

		AngleVectors(other->s.angles, forward, NULL, NULL);
		if (_DotProduct(forward, self->movedir) < 0)
			return;
	}

	self->activator = other;
	multi_trigger (self);
}

void trigger_enable (edict_t *self, edict_t *other, edict_t *activator)
{
	self->solid = SOLID_TRIGGER;
	self->use = Use_Multi;
	gi.linkentity (self);
}

void SP_trigger_multiple (edict_t *ent)
{
	if (ent->sounds == 1)
		ent->noise_index = gi.soundindex ("misc/secret.wav");
	else if (ent->sounds == 2)
		ent->noise_index = gi.soundindex ("misc/talk.wav");
	else if (ent->sounds == 3)
		ent->noise_index = gi.soundindex ("misc/trigger1.wav");

	if (!ent->wait)
		ent->wait = 0.2;
	ent->touch = Touch_Multi;
	ent->movetype = MOVETYPE_NONE;
	ent->svflags |= SVF_NOCLIENT;

	if (ent->spawnflags & 4)
	{
		ent->solid = SOLID_NOT;
		ent->use = trigger_enable;
	}
	else
	{
		ent->solid = SOLID_TRIGGER;
		ent->use = Use_Multi;
	}

	if (!VectorCompare(ent->s.angles, vec3_origin))
		G_SetMovedir (ent->s.angles, ent->movedir);

	gi.setmodel (ent, ent->model);
	gi.linkentity (ent);
}

void SP_trigger_once(edict_t *ent)
{
	// make old maps work because I messed up on flag assignments here
	// triggered was on bit 1 when it should have been on bit 4
	if (ent->spawnflags & 1)
	{
		vec3_t	v;

		VectorMA (ent->mins, 0.5, ent->size, v);
		ent->spawnflags &= ~1;
		ent->spawnflags |= 4;
		gi.dprintf("fixed TRIGGERED flag on %s at %s\n", ent->classname, vtos(v));
	}

	ent->wait = -1;
	SP_trigger_multiple (ent);
}

void trigger_relay_use (edict_t *self, edict_t *other, edict_t *activator)
{
	G_UseTargets (self, activator);
}

void SP_trigger_relay (edict_t *self)
{
	self->use = trigger_relay_use;
}

void trigger_key_use (edict_t *self, edict_t *other, edict_t *activator)
{
	int			index;

	if (!self->item)
		return;
	if (!activator->client)
		return;

	index = ITEM_INDEX(self->item);
	if (!activator->client->pers.inventory[index])
	{
		if (level.time < self->touch_debounce_time)
			return;
		self->touch_debounce_time = level.time + 5.0;
		gi.centerprintf (activator, "You need the %s", self->item->pickup_name);
		gi.sound (activator, CHAN_AUTO, gi.soundindex ("misc/keytry.wav"), 1, ATTN_NORM, 0);
		return;
	}

	gi.sound (activator, CHAN_AUTO, gi.soundindex ("misc/keyuse.wav"), 1, ATTN_NORM, 0);
	if (coop->value)
	{
		int		player;
		edict_t	*ent;

		if (strcmp(self->item->classname, "key_power_cube") == 0)
		{
			int	cube;

			for (cube = 0; cube < 8; cube++)
				if (activator->client->pers.power_cubes & (1 << cube))
					break;
			for (player = 1; player <= game.maxclients; player++)
			{
				ent = &g_edicts[player];
				if (!ent->inuse)
					continue;
				if (!ent->client)
					continue;
				if (ent->client->pers.power_cubes & (1 << cube))
				{
					ent->client->pers.inventory[index]--;
					ent->client->pers.power_cubes &= ~(1 << cube);
				}
			}
		}
		else
		{
			for (player = 1; player <= game.maxclients; player++)
			{
				ent = &g_edicts[player];
				if (!ent->inuse)
					continue;
				if (!ent->client)
					continue;
				ent->client->pers.inventory[index] = 0;
			}
		}
	}
	else
	{
		activator->client->pers.inventory[index]--;
	}

	G_UseTargets (self, activator);

	self->use = NULL;
}

void SP_trigger_key (edict_t *self)
{
	if (!st.item)
	{
		gi.dprintf("no key item for trigger_key at %s\n", vtos(self->s.origin));
		return;
	}
	self->item = FindItemByClassname (st.item);

	if (!self->item)
	{
		gi.dprintf("item %s not found for trigger_key at %s\n", st.item, vtos(self->s.origin));
		return;
	}

	if (!self->target)
	{
		gi.dprintf("%s at %s has no target\n", self->classname, vtos(self->s.origin));
		return;
	}

	gi.soundindex ("misc/keytry.wav");
	gi.soundindex ("misc/keyuse.wav");

	self->use = trigger_key_use;
}

void trigger_counter_use(edict_t *self, edict_t *other, edict_t *activator)
{
	if (self->count == 0)
		return;

	self->count--;

	if (self->count)
	{
		if (! (self->spawnflags & 1))
		{
			gi.centerprintf(activator, "%i more to go...", self->count);
			gi.sound (activator, CHAN_AUTO, gi.soundindex ("misc/talk1.wav"), 1, ATTN_NORM, 0);
		}
		return;
	}

	if (! (self->spawnflags & 1))
	{
		gi.centerprintf(activator, "Sequence completed!");
		gi.sound (activator, CHAN_AUTO, gi.soundindex ("misc/talk1.wav"), 1, ATTN_NORM, 0);
	}
	self->activator = activator;
	multi_trigger (self);
}

void SP_trigger_counter (edict_t *self)
{
	self->wait = -1;
	if (!self->count)
		self->count = 2;

	self->use = trigger_counter_use;
}

void SP_trigger_always (edict_t *ent)
{
	// we must have some delay to make sure our use targets are present
	if (ent->delay < 0.2)
		ent->delay = 0.2;
	G_UseTargets(ent, ent);
}

#define PUSH_ONCE		1

static int windsound;

void trigger_push_touch (edict_t *self, edict_t *other, cplane_t *plane, csurface_t *surf)
{
	if (strcmp(other->classname, "grenade") == 0)
	{
		VectorScale (self->movedir, self->speed * 10, other->velocity);
	}
	else if (other->health > 0)
	{
		VectorScale (self->movedir, self->speed * 10, other->velocity);

		if (other->client)
		{
			// don't take falling damage immediately from this
			VectorCopy (other->velocity, other->client->oldvelocity);
			if (other->fly_sound_debounce_time < level.time)
			{
				other->fly_sound_debounce_time = level.time + 1.5;
				gi.sound (other, CHAN_AUTO, windsound, 1, ATTN_NORM, 0);
			}
		}
	}
	if (self->spawnflags & PUSH_ONCE)
		G_FreeEdict (self);
}

void SP_trigger_push (edict_t *self)
{
	InitTrigger (self);
	windsound = gi.soundindex ("misc/windfly.wav");
	self->touch = trigger_push_touch;
	if (!self->speed)
		self->speed = 1000;
	gi.linkentity (self);
}

void hurt_use (edict_t *self, edict_t *other, edict_t *activator)
{
	if (self->solid == SOLID_NOT)
		self->solid = SOLID_TRIGGER;
	else
		self->solid = SOLID_NOT;
	gi.linkentity (self);

	if (!(self->spawnflags & 2))
		self->use = NULL;
}

void hurt_touch (edict_t *self, edict_t *other, cplane_t *plane, csurface_t *surf)
{
	int		dflags;

	if (!other->takedamage)
		return;

	if (self->timestamp > level.time)
		return;

	if (self->spawnflags & 16)
		self->timestamp = level.time + 1;
	else
		self->timestamp = level.time + FRAMETIME;

	if (!(self->spawnflags & 4))
	{
		if ((level.framenum % 10) == 0)
			gi.sound (other, CHAN_AUTO, self->noise_index, 1, ATTN_NORM, 0);
	}

	if (self->spawnflags & 8)
		dflags = DAMAGE_NO_PROTECTION;
	else
		dflags = 0;
	T_Damage (other, self, self, vec3_origin, other->s.origin, vec3_origin, self->dmg, self->dmg, dflags, MOD_TRIGGER_HURT);
}

void SP_trigger_hurt (edict_t *self)
{
	InitTrigger (self);

	self->noise_index = gi.soundindex ("world/electro.wav");
	self->touch = hurt_touch;

	if (!self->dmg)
		self->dmg = 5;

	if (self->spawnflags & 1)
		self->solid = SOLID_NOT;
	else
		self->solid = SOLID_TRIGGER;

	if (self->spawnflags & 2)
		self->use = hurt_use;

	gi.linkentity (self);
}

void trigger_gravity_touch (edict_t *self, edict_t *other, cplane_t *plane, csurface_t *surf)
{
	other->gravity = self->gravity;
}

void SP_trigger_gravity (edict_t *self)
{
	if (st.gravity == 0)
	{
		gi.dprintf("trigger_gravity without gravity set at %s\n", vtos(self->s.origin));
		G_FreeEdict  (self);
		return;
	}

	InitTrigger (self);
	self->gravity = atoi(st.gravity);
	self->touch = trigger_gravity_touch;
}

void trigger_monsterjump_touch (edict_t *self, edict_t *other, cplane_t *plane, csurface_t *surf)
{
	if (other->flags & (FL_FLY | FL_SWIM) )
		return;
	if (other->svflags & SVF_DEADMONSTER)
		return;
	if ( !(other->svflags & SVF_MONSTER))
		return;

// set XY even if not on ground, so the jump will clear lips
	other->velocity[0] = self->movedir[0] * self->speed;
	other->velocity[1] = self->movedir[1] * self->speed;

	if (!other->groundentity)
		return;

	other->groundentity = NULL;
	other->velocity[2] = self->movedir[2];
}

void SP_trigger_monsterjump (edict_t *self)
{
	if (!self->speed)
		self->speed = 200;
	if (!st.height)
		st.height = 200;
	if (self->s.angles[YAW] == 0)
		self->s.angles[YAW] = 360;
	InitTrigger (self);
	self->touch = trigger_monsterjump_touch;
	self->movedir[2] = st.height;
}
"""

import random as _r
from game import q_shared
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
from game.q_shared import ATTN_NORM, CHAN_AUTO, YAW

PUSH_ONCE = 1
windsound = None  # int

def InitTrigger (self):
	#edict_t *self
	if not q_shared.VectorCompare(self.s.angles, q_shared.vec3_origin):
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

	if not q_shared.VectorCompare(self.movedir, q_shared.vec3_origin):
		forward = [0.0, 0.0, 0.0]
		q_shared.AngleVectors(other.s.angles, forward, None, None)
		if q_shared.DotProduct(forward, self.movedir) < 0:
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

	if not q_shared.VectorCompare(ent.s.angles, q_shared.vec3_origin):
		g_utils.G_SetMovedir (ent.s.angles, ent.movedir)

	g_main.gi.setmodel (ent, ent.model)
	g_main.gi.linkentity (ent)

def SP_trigger_once (ent):
	#edict_t *ent
	# make old maps work because I messed up on flag assignments here
	# triggered was on bit 1 when it should have been on bit 4
	if ent.spawnflags & 1:
		v = [0.0, 0.0, 0.0]
		q_shared.VectorMA (ent.mins, 0.5, ent.size, v)
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

		if q_shared.Q_stricmp(self.item.classname, "key_power_cube") == 0:
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
		q_shared.VectorScale (self.movedir, self.speed * 10, other.velocity)
	elif other.health > 0:
		q_shared.VectorScale (self.movedir, self.speed * 10, other.velocity)

		if other.client:
			# don't take falling damage immediately from this
			q_shared.VectorCopy (other.velocity, other.client.oldvelocity)
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
	g_combat.T_Damage (other, self, self, q_shared.vec3_origin, other.s.origin, q_shared.vec3_origin, self.dmg, self.dmg, dflags, g_local.MOD_TRIGGER_HURT)

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
