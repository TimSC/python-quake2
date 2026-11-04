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
from game import game as _gamemod
from game import q_shared, g_local, g_main, g_utils, g_misc, g_combat, g_weapon, g_spawn, p_hud
from game.q_shared import (CHAN_VOICE, CHAN_RELIABLE, CHAN_AUTO,
	ATTN_NORM, ATTN_NONE, RF_BEAM, RF_TRANSLUCENT, EF_BLASTER, EF_HYPERBLASTER,
	CS_CDTRACK, CS_LIGHTS, CONTENTS_SOLID, CONTENTS_MONSTER, CONTENTS_DEADMONSTER,
	DF_ALLOW_EXIT, PRINT_HIGH)
from game.q_shared import temp_event_t, multicast_t
TE_EXPLOSION1 = temp_event_t.TE_EXPLOSION1.value
TE_SPLASH = temp_event_t.TE_SPLASH.value
TE_LASER_SPARKS = temp_event_t.TE_LASER_SPARKS.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
MULTICAST_PHS = multicast_t.MULTICAST_PHS.value
from game.g_local import (svc_temp_entity, FRAMETIME, crandom, FL_IMMUNE_LASER, DAMAGE_ENERGY,
	MOD_EXPLOSIVE, MOD_EXIT, MOD_SPLASH, MOD_TARGET_BLASTER, MOD_TARGET_LASER,
	SFL_CROSS_TRIGGER_MASK, MOVETYPE_NONE)
from game.game import SVF_NOCLIENT, solid_t
SOLID_NOT = solid_t.SOLID_NOT.value
"""
#include "g_local.h"
"""


def Use_Target_Tent (ent, other, activator): #edict_t *, edict_t *, edict_t *
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (ent.style)
	g_main.gi.WritePosition (ent.s.origin)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)
	"""
	gi.WriteByte (svc_temp_entity);
	gi.WriteByte (ent->style);
	gi.WritePosition (ent->s.origin);
	gi.multicast (ent->s.origin, MULTICAST_PVS);
	"""


def SP_target_temp_entity (ent): #edict_t *
	ent.use = Use_Target_Tent
	"""
	ent->use = Use_Target_Tent;
	"""


def Use_Target_Speaker (ent, other, activator): #edict_t *, edict_t *, edict_t *
	chan = 0

	if ent.spawnflags & 3:
		#	# looping sound toggles
		if ent.s.sound:
			ent.s.sound = 0	# turn it off
		else:
			ent.s.sound = ent.noise_index	# start it
	else:
		#	# normal sound
		if ent.spawnflags & 4:
			chan = CHAN_VOICE|CHAN_RELIABLE
		else:
			chan = CHAN_VOICE
		# use a positioned_sound, because this entity won't normally be
		# sent to any clients because it is invisible
		g_main.gi.positioned_sound (ent.s.origin, ent, chan, ent.noise_index, ent.volume, ent.attenuation, 0)
	"""
	int		chan;

	if (ent->spawnflags & 3)
	{	// looping sound toggles
		if (ent->s.sound)
			ent->s.sound = 0;	// turn it off
		else
			ent->s.sound = ent->noise_index;	// start it
	}
	else
	{	// normal sound
		if (ent->spawnflags & 4)
			chan = CHAN_VOICE|CHAN_RELIABLE;
		else
			chan = CHAN_VOICE;
		// use a positioned_sound, because this entity won't normally be
		// sent to any clients because it is invisible
		gi.positioned_sound (ent->s.origin, ent, chan, ent->noise_index, ent->volume, ent->attenuation, 0);
	}
	"""


def SP_target_speaker (ent): #edict_t *
	buffer = ""

	if not g_main.st.noise:
		g_main.gi.dprintf("target_speaker with no noise set at %s\n", g_utils.vtos(ent.s.origin))
		return
	if ".wav" not in g_main.st.noise:
		buffer = "%s.wav" % g_main.st.noise
	else:
		buffer = g_main.st.noise
	ent.noise_index = g_main.gi.soundindex (buffer)

	if not ent.volume:
		ent.volume = 1.0

	if not ent.attenuation:
		ent.attenuation = 1.0
	elif ent.attenuation == -1:	# use -1 so 0 defaults to 1
		ent.attenuation = 0

	# check for prestarted looping sound
	if ent.spawnflags & 1:
		ent.s.sound = ent.noise_index

	ent.use = Use_Target_Speaker

	# must link the entity so we get areas and clusters so
	# the server can determine who to send updates to
	g_main.gi.linkentity (ent)
	"""
	char	buffer[MAX_QPATH];

	if(!st.noise)
	{
		gi.dprintf("target_speaker with no noise set at %s\n", vtos(ent->s.origin));
		return;
	}
	if (!strstr (st.noise, ".wav"))
		Com_sprintf (buffer, sizeof(buffer), "%s.wav", st.noise);
	else
		strncpy (buffer, st.noise, sizeof(buffer));
	ent->noise_index = gi.soundindex (buffer);

	if (!ent->volume)
		ent->volume = 1.0;

	if (!ent->attenuation)
		ent->attenuation = 1.0;
	else if (ent->attenuation == -1)	// use -1 so 0 defaults to 1
		ent->attenuation = 0;

	// check for prestarted looping sound
	if (ent->spawnflags & 1)
		ent->s.sound = ent->noise_index;

	ent->use = Use_Target_Speaker;

	// must link the entity so we get areas and clusters so
	// the server can determine who to send updates to
	gi.linkentity (ent);
	"""


def Use_Target_Help (ent, other, activator): #edict_t *, edict_t *, edict_t *
	if ent.spawnflags & 1:
		g_main.game.helpmessage1 = ent.message
	else:
		g_main.game.helpmessage2 = ent.message

	g_main.game.helpchanged += 1
	"""
	if (ent->spawnflags & 1)
		strncpy (game.helpmessage1, ent->message, sizeof(game.helpmessage2)-1);
	else
		strncpy (game.helpmessage2, ent->message, sizeof(game.helpmessage1)-1);

	game.helpchanged++;
	"""


def SP_target_help (ent): #edict_t *
	if g_main.deathmatch.value:
		#	# auto-remove for deathmatch
		g_utils.G_FreeEdict (ent)
		return

	if not ent.message:
		g_main.gi.dprintf ("%s with no message at %s\n", ent.classname, g_utils.vtos(ent.s.origin))
		g_utils.G_FreeEdict (ent)
		return
	ent.use = Use_Target_Help
	"""
	if (deathmatch->value)
	{	// auto-remove for deathmatch
		G_FreeEdict (ent);
		return;
	}

	if (!ent->message)
	{
		gi.dprintf ("%s with no message at %s\n", ent->classname, vtos(ent->s.origin));
		G_FreeEdict (ent);
		return;
	}
	ent->use = Use_Target_Help;
	"""


def use_target_secret (ent, other, activator): #edict_t *, edict_t *, edict_t *
	g_main.gi.sound (ent, CHAN_VOICE, ent.noise_index, 1, ATTN_NORM, 0)

	g_main.level.found_secrets += 1

	g_utils.G_UseTargets (ent, activator)
	g_utils.G_FreeEdict (ent)
	"""
	gi.sound (ent, CHAN_VOICE, ent->noise_index, 1, ATTN_NORM, 0);

	level.found_secrets++;

	G_UseTargets (ent, activator);
	G_FreeEdict (ent);
	"""


def SP_target_secret (ent): #edict_t *
	if g_main.deathmatch.value:
		#	# auto-remove for deathmatch
		g_utils.G_FreeEdict (ent)
		return

	ent.use = use_target_secret
	if not g_main.st.noise:
		g_main.st.noise = "misc/secret.wav"
	ent.noise_index = g_main.gi.soundindex (g_main.st.noise)
	ent.svflags = SVF_NOCLIENT
	g_main.level.total_secrets += 1
	# map bug hack
	if q_shared.Q_stricmp(g_main.level.mapname, "mine3") == 0 and ent.s.origin[0] == 280 and ent.s.origin[1] == -2048 and ent.s.origin[2] == -624:
		ent.message = "You have found a secret area."
	"""
	if (deathmatch->value)
	{	// auto-remove for deathmatch
		G_FreeEdict (ent);
		return;
	}

	ent->use = use_target_secret;
	if (!st.noise)
		st.noise = "misc/secret.wav";
	ent->noise_index = gi.soundindex (st.noise);
	ent->svflags = SVF_NOCLIENT;
	level.total_secrets++;
	// map bug hack
	if (!Q_stricmp(level.mapname, "mine3") && ent->s.origin[0] == 280 && ent->s.origin[1] == -2048 && ent->s.origin[2] == -624)
		ent->message = "You have found a secret area.";
	"""


def use_target_goal (ent, other, activator): #edict_t *, edict_t *, edict_t *
	g_main.gi.sound (ent, CHAN_VOICE, ent.noise_index, 1, ATTN_NORM, 0)

	g_main.level.found_goals += 1

	if g_main.level.found_goals == g_main.level.total_goals:
		g_main.gi.configstring (CS_CDTRACK, "0")

	g_utils.G_UseTargets (ent, activator)
	g_utils.G_FreeEdict (ent)
	"""
	gi.sound (ent, CHAN_VOICE, ent->noise_index, 1, ATTN_NORM, 0);

	level.found_goals++;

	if (level.found_goals == level.total_goals)
		gi.configstring (CS_CDTRACK, "0");

	G_UseTargets (ent, activator);
	G_FreeEdict (ent);
	"""


def SP_target_goal (ent): #edict_t *
	if g_main.deathmatch.value:
		#	# auto-remove for deathmatch
		g_utils.G_FreeEdict (ent)
		return

	ent.use = use_target_goal
	if not g_main.st.noise:
		g_main.st.noise = "misc/secret.wav"
	ent.noise_index = g_main.gi.soundindex (g_main.st.noise)
	ent.svflags = SVF_NOCLIENT
	g_main.level.total_goals += 1
	"""
	if (deathmatch->value)
	{	// auto-remove for deathmatch
		G_FreeEdict (ent);
		return;
	}

	ent->use = use_target_goal;
	if (!st.noise)
		st.noise = "misc/secret.wav";
	ent->noise_index = gi.soundindex (st.noise);
	ent->svflags = SVF_NOCLIENT;
	level.total_goals++;
	"""


def target_explosion_explode (self): #edict_t *
	save = 0.0

	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_EXPLOSION1)
	g_main.gi.WritePosition (self.s.origin)
	g_main.gi.multicast (self.s.origin, MULTICAST_PHS)

	g_combat.T_RadiusDamage (self, self.activator, self.dmg, None, self.dmg+40, MOD_EXPLOSIVE)

	save = self.delay
	self.delay = 0
	g_utils.G_UseTargets (self, self.activator)
	self.delay = save
	"""
	float		save;

	gi.WriteByte (svc_temp_entity);
	gi.WriteByte (TE_EXPLOSION1);
	gi.WritePosition (self->s.origin);
	gi.multicast (self->s.origin, MULTICAST_PHS);

	T_RadiusDamage (self, self->activator, self->dmg, NULL, self->dmg+40, MOD_EXPLOSIVE);

	save = self->delay;
	self->delay = 0;
	G_UseTargets (self, self->activator);
	self->delay = save;
	"""


def use_target_explosion (self, other, activator): #edict_t *, edict_t *, edict_t *
	self.activator = activator

	if not self.delay:
		target_explosion_explode (self)
		return

	self.think = target_explosion_explode
	self.nextthink = g_main.level.time + self.delay
	"""
	self->activator = activator;

	if (!self->delay)
	{
		target_explosion_explode (self);
		return;
	}

	self->think = target_explosion_explode;
	self->nextthink = level.time + self->delay;
	"""


def SP_target_explosion (ent): #edict_t *
	ent.use = use_target_explosion
	ent.svflags = SVF_NOCLIENT
	"""
	ent->use = use_target_explosion;
	ent->svflags = SVF_NOCLIENT;
	"""


def use_target_changelevel (self, other, activator): #edict_t *, edict_t *, edict_t *
	if g_main.level.intermissiontime:
		return		# already activated

	if not g_main.deathmatch.value and not g_main.coop.value:
		if g_main.g_edicts[1].health <= 0:
			return

	# if noexit, do a ton of damage to other
	if g_main.deathmatch.value and not (int(g_main.dmflags.value) & DF_ALLOW_EXIT) and other != g_main.g_edicts[1]:
		g_combat.T_Damage (other, self, self, q_shared.vec3_origin, other.s.origin, q_shared.vec3_origin, 10 * other.max_health, 1000, 0, MOD_EXIT)
		return

	# if multiplayer, let everyone know who hit the exit
	if g_main.deathmatch.value:
		if activator and activator.client:
			g_main.gi.bprintf (PRINT_HIGH, "%s exited the level.\n", activator.client.pers.netname)

	# if going to a new unit, clear cross triggers
	if "*" in self.map:	
		g_main.game.serverflags &= ~SFL_CROSS_TRIGGER_MASK

	p_hud.BeginIntermission (self)
	"""
	if (level.intermissiontime)
		return;		// already activated

	if (!deathmatch->value && !coop->value)
	{
		if (g_edicts[1].health <= 0)
			return;
	}

	// if noexit, do a ton of damage to other
	if (deathmatch->value && !( (int)dmflags->value & DF_ALLOW_EXIT) && other != world)
	{
		T_Damage (other, self, self, vec3_origin, other->s.origin, vec3_origin, 10 * other->max_health, 1000, 0, MOD_EXIT);
		return;
	}

	// if multiplayer, let everyone know who hit the exit
	if (deathmatch->value)
	{
		if (activator && activator->client)
			gi.bprintf (PRINT_HIGH, "%s exited the level.\n", activator->client->pers.netname);
	}

	// if going to a new unit, clear cross triggers
	if (strstr(self->map, "*"))	
		game.serverflags &= ~(SFL_CROSS_TRIGGER_MASK);

	BeginIntermission (self);
	"""


def SP_target_changelevel (ent): #edict_t *
	if not ent.map:
		g_main.gi.dprintf("target_changelevel with no map at %s\n", g_utils.vtos(ent.s.origin))
		g_utils.G_FreeEdict (ent)
		return

	# ugly hack because *SOMEBODY* screwed up their map
	if (q_shared.Q_stricmp(g_main.level.mapname, "fact1") == 0) and (q_shared.Q_stricmp(ent.map, "fact3") == 0):
		ent.map = "fact3$secret1"

	ent.use = use_target_changelevel
	ent.svflags = SVF_NOCLIENT
	"""
	if (!ent->map)
	{
		gi.dprintf("target_changelevel with no map at %s\n", vtos(ent->s.origin));
		G_FreeEdict (ent);
		return;
	}

	// ugly hack because *SOMEBODY* screwed up their map
   if((Q_stricmp(level.mapname, "fact1") == 0) && (Q_stricmp(ent->map, "fact3") == 0))
	   ent->map = "fact3$secret1";

	ent->use = use_target_changelevel;
	ent->svflags = SVF_NOCLIENT;
	"""


def use_target_splash (self, other, activator): #edict_t *, edict_t *, edict_t *
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_SPLASH)
	g_main.gi.WriteByte (self.count)
	g_main.gi.WritePosition (self.s.origin)
	g_main.gi.WriteDir (self.movedir)
	g_main.gi.WriteByte (self.sounds)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)

	if self.dmg:
		g_combat.T_RadiusDamage (self, activator, self.dmg, None, self.dmg+40, MOD_SPLASH)
	"""
	gi.WriteByte (svc_temp_entity);
	gi.WriteByte (TE_SPLASH);
	gi.WriteByte (self->count);
	gi.WritePosition (self->s.origin);
	gi.WriteDir (self->movedir);
	gi.WriteByte (self->sounds);
	gi.multicast (self->s.origin, MULTICAST_PVS);

	if (self->dmg)
		T_RadiusDamage (self, activator, self->dmg, NULL, self->dmg+40, MOD_SPLASH);
	"""


def SP_target_splash (self): #edict_t *
	self.use = use_target_splash
	g_utils.G_SetMovedir (self.s.angles, self.movedir)

	if not self.count:
		self.count = 32

	self.svflags = SVF_NOCLIENT
	"""
	self->use = use_target_splash;
	G_SetMovedir (self->s.angles, self->movedir);

	if (!self->count)
		self->count = 32;

	self->svflags = SVF_NOCLIENT;
	"""


def use_target_spawner (self, other, activator): #edict_t *, edict_t *, edict_t *
	ent = None

	ent = g_utils.G_Spawn()
	ent.classname = self.target
	q_shared.VectorCopy (self.s.origin, ent.s.origin)
	q_shared.VectorCopy (self.s.angles, ent.s.angles)
	g_spawn.ED_CallSpawn (ent)
	g_main.gi.unlinkentity (ent)
	g_utils.KillBox (ent)
	g_main.gi.linkentity (ent)
	if self.speed:
		q_shared.VectorCopy (self.movedir, ent.velocity)
	"""
	edict_t	*ent;

	ent = G_Spawn();
	ent->classname = self->target;
	VectorCopy (self->s.origin, ent->s.origin);
	VectorCopy (self->s.angles, ent->s.angles);
	ED_CallSpawn (ent);
	gi.unlinkentity (ent);
	KillBox (ent);
	gi.linkentity (ent);
	if (self->speed)
		VectorCopy (self->movedir, ent->velocity);
	"""


def SP_target_spawner (self): #edict_t *
	self.use = use_target_spawner
	self.svflags = SVF_NOCLIENT
	if self.speed:
		g_utils.G_SetMovedir (self.s.angles, self.movedir)
		q_shared.VectorScale (self.movedir, self.speed, self.movedir)
	"""
	self->use = use_target_spawner;
	self->svflags = SVF_NOCLIENT;
	if (self->speed)
	{
		G_SetMovedir (self->s.angles, self->movedir);
		VectorScale (self->movedir, self->speed, self->movedir);
	}
	"""


def use_target_blaster (self, other, activator): #edict_t *, edict_t *, edict_t *
	effect = 0

	if self.spawnflags & 2:
		effect = 0
	elif self.spawnflags & 1:
		effect = EF_HYPERBLASTER
	else:
		effect = EF_BLASTER

	g_weapon.fire_blaster (self, self.s.origin, self.movedir, self.dmg, self.speed, EF_BLASTER, MOD_TARGET_BLASTER)
	g_main.gi.sound (self, CHAN_VOICE, self.noise_index, 1, ATTN_NORM, 0)
	"""
	int effect;

	if (self->spawnflags & 2)
		effect = 0;
	else if (self->spawnflags & 1)
		effect = EF_HYPERBLASTER;
	else
		effect = EF_BLASTER;

	fire_blaster (self, self->s.origin, self->movedir, self->dmg, self->speed, EF_BLASTER, MOD_TARGET_BLASTER);
	gi.sound (self, CHAN_VOICE, self->noise_index, 1, ATTN_NORM, 0);
	"""


def SP_target_blaster (self): #edict_t *
	self.use = use_target_blaster
	g_utils.G_SetMovedir (self.s.angles, self.movedir)
	self.noise_index = g_main.gi.soundindex ("weapons/laser2.wav")

	if not self.dmg:
		self.dmg = 15
	if not self.speed:
		self.speed = 1000

	self.svflags = SVF_NOCLIENT
	"""
	self->use = use_target_blaster;
	G_SetMovedir (self->s.angles, self->movedir);
	self->noise_index = gi.soundindex ("weapons/laser2.wav");

	if (!self->dmg)
		self->dmg = 15;
	if (!self->speed)
		self->speed = 1000;

	self->svflags = SVF_NOCLIENT;
	"""


def trigger_crosslevel_trigger_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	g_main.game.serverflags |= self.spawnflags
	g_utils.G_FreeEdict (self)
	"""
	game.serverflags |= self->spawnflags;
	G_FreeEdict (self);
	"""


def SP_target_crosslevel_trigger (self): #edict_t *
	self.svflags = SVF_NOCLIENT
	self.use = trigger_crosslevel_trigger_use
	"""
	self->svflags = SVF_NOCLIENT;
	self->use = trigger_crosslevel_trigger_use;
	"""


def target_crosslevel_target_think (self): #edict_t *
	if self.spawnflags == (g_main.game.serverflags & SFL_CROSS_TRIGGER_MASK & self.spawnflags):
		g_utils.G_UseTargets (self, self)
		g_utils.G_FreeEdict (self)
	"""
	if (self->spawnflags == (game.serverflags & SFL_CROSS_TRIGGER_MASK & self->spawnflags))
	{
		G_UseTargets (self, self);
		G_FreeEdict (self);
	}
	"""


def SP_target_crosslevel_target (self): #edict_t *
	if not self.delay:
		self.delay = 1
	self.svflags = SVF_NOCLIENT

	self.think = target_crosslevel_target_think
	self.nextthink = g_main.level.time + self.delay
	"""
	if (! self->delay)
		self->delay = 1;
	self->svflags = SVF_NOCLIENT;

	self->think = target_crosslevel_target_think;
	self->nextthink = level.time + self->delay;
	"""


def target_laser_think (self): #edict_t *
	ignore = None
	start = q_shared.vec3_origin.copy()
	end = q_shared.vec3_origin.copy()
	tr = q_shared.trace_t()
	point = q_shared.vec3_origin.copy()
	last_movedir = q_shared.vec3_origin.copy()
	count = 0

	if self.spawnflags & 0x80000000:
		count = 8
	else:
		count = 4

	if self.enemy:
		q_shared.VectorCopy (self.movedir, last_movedir)
		q_shared.VectorMA (self.enemy.absmin, 0.5, self.enemy.size, point)
		q_shared.VectorSubtract (point, self.s.origin, self.movedir)
		q_shared.VectorNormalize (self.movedir)
		if not q_shared.VectorCompare(self.movedir, last_movedir):
			self.spawnflags |= 0x80000000

	ignore = self
	q_shared.VectorCopy (self.s.origin, start)
	q_shared.VectorMA (start, 2048, self.movedir, end)
	while True:
		tr = g_main.gi.trace (start, None, None, end, ignore, CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_DEADMONSTER)

		if not tr.ent:
			break

		# hurt it if we can
		if (tr.ent.takedamage) and not (tr.ent.flags & FL_IMMUNE_LASER):
			g_combat.T_Damage (tr.ent, self, self.activator, self.movedir, tr.endpos, q_shared.vec3_origin, self.dmg, 1, DAMAGE_ENERGY, MOD_TARGET_LASER)

		# if we hit something that's not a monster or player or is immune to lasers, we're done
		if not (tr.ent.svflags & _gamemod.SVF_MONSTER) and not tr.ent.client:
			if self.spawnflags & 0x80000000:
				self.spawnflags &= ~0x80000000
				g_main.gi.WriteByte (svc_temp_entity)
				g_main.gi.WriteByte (TE_LASER_SPARKS)
				g_main.gi.WriteByte (count)
				g_main.gi.WritePosition (tr.endpos)
				g_main.gi.WriteDir (tr.plane.normal)
				g_main.gi.WriteByte (self.s.skinnum)
				g_main.gi.multicast (tr.endpos, MULTICAST_PVS)
			break

		ignore = tr.ent
		q_shared.VectorCopy (tr.endpos, start)

	q_shared.VectorCopy (tr.endpos, self.s.old_origin)

	self.nextthink = g_main.level.time + FRAMETIME
	"""
	edict_t	*ignore;
	vec3_t	start;
	vec3_t	end;
	trace_t	tr;
	vec3_t	point;
	vec3_t	last_movedir;
	int		count;

	if (self->spawnflags & 0x80000000)
		count = 8;
	else
		count = 4;

	if (self->enemy)
	{
		VectorCopy (self->movedir, last_movedir);
		VectorMA (self->enemy->absmin, 0.5, self->enemy->size, point);
		VectorSubtract (point, self->s.origin, self->movedir);
		VectorNormalize (self->movedir);
		if (!VectorCompare(self->movedir, last_movedir))
			self->spawnflags |= 0x80000000;
	}

	ignore = self;
	VectorCopy (self->s.origin, start);
	VectorMA (start, 2048, self->movedir, end);
	while(1)
	{
		tr = gi.trace (start, NULL, NULL, end, ignore, CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_DEADMONSTER);

		if (!tr.ent)
			break;

		// hurt it if we can
		if ((tr.ent->takedamage) && !(tr.ent->flags & FL_IMMUNE_LASER))
			T_Damage (tr.ent, self, self->activator, self->movedir, tr.endpos, vec3_origin, self->dmg, 1, DAMAGE_ENERGY, MOD_TARGET_LASER);

		// if we hit something that's not a monster or player or is immune to lasers, we're done
		if (!(tr.ent->svflags & SVF_MONSTER) && (!tr.ent->client))
		{
			if (self->spawnflags & 0x80000000)
			{
				self->spawnflags &= ~0x80000000;
				gi.WriteByte (svc_temp_entity);
				gi.WriteByte (TE_LASER_SPARKS);
				gi.WriteByte (count);
				gi.WritePosition (tr.endpos);
				gi.WriteDir (tr.plane.normal);
				gi.WriteByte (self->s.skinnum);
				gi.multicast (tr.endpos, MULTICAST_PVS);
			}
			break;
		}

		ignore = tr.ent;
		VectorCopy (tr.endpos, start);
	}

	VectorCopy (tr.endpos, self->s.old_origin);

	self->nextthink = level.time + FRAMETIME;
	"""


def target_laser_on (self): #edict_t *
	if not self.activator:
		self.activator = self
	self.spawnflags |= 0x80000001
	self.svflags &= ~SVF_NOCLIENT
	target_laser_think (self)
	"""
	if (!self->activator)
		self->activator = self;
	self->spawnflags |= 0x80000001;
	self->svflags &= ~SVF_NOCLIENT;
	target_laser_think (self);
	"""


def target_laser_off (self): #edict_t *
	self.spawnflags &= ~1
	self.svflags |= SVF_NOCLIENT
	self.nextthink = 0
	"""
	self->spawnflags &= ~1;
	self->svflags |= SVF_NOCLIENT;
	self->nextthink = 0;
	"""


def target_laser_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	self.activator = activator
	if self.spawnflags & 1:
		target_laser_off (self)
	else:
		target_laser_on (self)
	"""
	self->activator = activator;
	if (self->spawnflags & 1)
		target_laser_off (self);
	else
		target_laser_on (self);
	"""


def target_laser_start (self): #edict_t *
	ent = None

	self.movetype = MOVETYPE_NONE
	self.solid = SOLID_NOT
	self.s.renderfx |= RF_BEAM|RF_TRANSLUCENT
	self.s.modelindex = 1			# must be non-zero

	# set the beam diameter
	if self.spawnflags & 64:
		self.s.frame = 16
	else:
		self.s.frame = 4

	# set the color
	if self.spawnflags & 2:
		self.s.skinnum = 0xf2f2f0f0
	elif self.spawnflags & 4:
		self.s.skinnum = 0xd0d1d2d3
	elif self.spawnflags & 8:
		self.s.skinnum = 0xf3f3f1f1
	elif self.spawnflags & 16:
		self.s.skinnum = 0xdcdddedf
	elif self.spawnflags & 32:
		self.s.skinnum = 0xe0e1e2e3

	if not self.enemy:
		if self.target:
			ent = g_utils.G_Find (None, "targetname", self.target)
			if not ent:
				g_main.gi.dprintf ("%s at %s: %s is a bad target\n", self.classname, g_utils.vtos(self.s.origin), self.target)
			self.enemy = ent
		else:
			g_utils.G_SetMovedir (self.s.angles, self.movedir)
	self.use = target_laser_use
	self.think = target_laser_think

	if not self.dmg:
		self.dmg = 1

	q_shared.VectorSet (self.mins, -8, -8, -8)
	q_shared.VectorSet (self.maxs, 8, 8, 8)
	g_main.gi.linkentity (self)

	if self.spawnflags & 1:
		target_laser_on (self)
	else:
		target_laser_off (self)
	"""
	edict_t *ent;

	self->movetype = MOVETYPE_NONE;
	self->solid = SOLID_NOT;
	self->s.renderfx |= RF_BEAM|RF_TRANSLUCENT;
	self->s.modelindex = 1;			// must be non-zero

	// set the beam diameter
	if (self->spawnflags & 64)
		self->s.frame = 16;
	else
		self->s.frame = 4;

	// set the color
	if (self->spawnflags & 2)
		self->s.skinnum = 0xf2f2f0f0;
	else if (self->spawnflags & 4)
		self->s.skinnum = 0xd0d1d2d3;
	else if (self->spawnflags & 8)
		self->s.skinnum = 0xf3f3f1f1;
	else if (self->spawnflags & 16)
		self->s.skinnum = 0xdcdddedf;
	else if (self->spawnflags & 32)
		self->s.skinnum = 0xe0e1e2e3;

	if (!self->enemy)
	{
		if (self->target)
		{
			ent = G_Find (NULL, FOFS(targetname), self->target);
			if (!ent)
				gi.dprintf ("%s at %s: %s is a bad target\n", self->classname, vtos(self->s.origin), self->target);
			self->enemy = ent;
		}
		else
		{
			G_SetMovedir (self->s.angles, self->movedir);
		}
	}
	self->use = target_laser_use;
	self->think = target_laser_think;

	if (!self->dmg)
		self->dmg = 1;

	VectorSet (self->mins, -8, -8, -8);
	VectorSet (self->maxs, 8, 8, 8);
	gi.linkentity (self);

	if (self->spawnflags & 1)
		target_laser_on (self);
	else
		target_laser_off (self);
	"""


def SP_target_laser (self): #edict_t *
	# let everything else get spawned before we start firing
	self.think = target_laser_start
	self.nextthink = g_main.level.time + 1
	"""
	// let everything else get spawned before we start firing
	self->think = target_laser_start;
	self->nextthink = level.time + 1;
	"""


def target_lightramp_think (self): #edict_t *
	style = ""

	style = chr(ord('a') + int(self.movedir[0] + (g_main.level.time - self.timestamp) / FRAMETIME * self.movedir[2]))
	g_main.gi.configstring (CS_LIGHTS+self.enemy.style, style)

	if (g_main.level.time - self.timestamp) < self.speed:
		self.nextthink = g_main.level.time + FRAMETIME
	elif self.spawnflags & 1:
		temp = 0.0

		temp = self.movedir[0]
		self.movedir[0] = self.movedir[1]
		self.movedir[1] = temp
		self.movedir[2] *= -1
	"""
	char	style[2];

	style[0] = 'a' + self->movedir[0] + (level.time - self->timestamp) / FRAMETIME * self->movedir[2];
	style[1] = 0;
	gi.configstring (CS_LIGHTS+self->enemy->style, style);

	if ((level.time - self->timestamp) < self->speed)
	{
		self->nextthink = level.time + FRAMETIME;
	}
	else if (self->spawnflags & 1)
	{
		char	temp;

		temp = self->movedir[0];
		self->movedir[0] = self->movedir[1];
		self->movedir[1] = temp;
		self->movedir[2] *= -1;
	}
	"""


def target_lightramp_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self.enemy:
		e = None

		# check all the targets
		e = None
		while True:
			e = g_utils.G_Find (e, "targetname", self.target)
			if not e:
				break
			if e.classname != "light":
				g_main.gi.dprintf("%s at %s ", self.classname, g_utils.vtos(self.s.origin))
				g_main.gi.dprintf("target %s (%s at %s) is not a light\n", self.target, e.classname, g_utils.vtos(e.s.origin))
			else:
				self.enemy = e

		if not self.enemy:
			g_main.gi.dprintf("%s target %s not found at %s\n", self.classname, self.target, g_utils.vtos(self.s.origin))
			g_utils.G_FreeEdict (self)
			return

	self.timestamp = g_main.level.time
	target_lightramp_think (self)
	"""
	if (!self->enemy)
	{
		edict_t		*e;

		// check all the targets
		e = NULL;
		while (1)
		{
			e = G_Find (e, FOFS(targetname), self->target);
			if (!e)
				break;
			if (strcmp(e->classname, "light") != 0)
			{
				gi.dprintf("%s at %s ", self->classname, vtos(self->s.origin));
				gi.dprintf("target %s (%s at %s) is not a light\n", self->target, e->classname, vtos(e->s.origin));
			}
			else
			{
				self->enemy = e;
			}
		}

		if (!self->enemy)
		{
			gi.dprintf("%s target %s not found at %s\n", self->classname, self->target, vtos(self->s.origin));
			G_FreeEdict (self);
			return;
		}
	}

	self->timestamp = level.time;
	target_lightramp_think (self);
	"""


def SP_target_lightramp (self): #edict_t *
	if not self.message or len(self.message) != 2 or ord(self.message[0]) < ord('a') or ord(self.message[0]) > ord('z') or ord(self.message[1]) < ord('a') or ord(self.message[1]) > ord('z') or self.message[0] == self.message[1]:
		g_main.gi.dprintf("target_lightramp has bad ramp (%s) at %s\n", self.message, g_utils.vtos(self.s.origin))
		g_utils.G_FreeEdict (self)
		return

	if g_main.deathmatch.value:
		g_utils.G_FreeEdict (self)
		return

	if not self.target:
		g_main.gi.dprintf("%s with no target at %s\n", self.classname, g_utils.vtos(self.s.origin))
		g_utils.G_FreeEdict (self)
		return

	self.svflags |= SVF_NOCLIENT
	self.use = target_lightramp_use
	self.think = target_lightramp_think

	self.movedir[0] = ord(self.message[0]) - ord('a')
	self.movedir[1] = ord(self.message[1]) - ord('a')
	self.movedir[2] = (self.movedir[1] - self.movedir[0]) / (self.speed / FRAMETIME)
	"""
	if (!self->message || strlen(self->message) != 2 || self->message[0] < 'a' || self->message[0] > 'z' || self->message[1] < 'a' || self->message[1] > 'z' || self->message[0] == self->message[1])
	{
		gi.dprintf("target_lightramp has bad ramp (%s) at %s\n", self->message, vtos(self->s.origin));
		G_FreeEdict (self);
		return;
	}

	if (deathmatch->value)
	{
		G_FreeEdict (self);
		return;
	}

	if (!self->target)
	{
		gi.dprintf("%s with no target at %s\n", self->classname, vtos(self->s.origin));
		G_FreeEdict (self);
		return;
	}

	self->svflags |= SVF_NOCLIENT;
	self->use = target_lightramp_use;
	self->think = target_lightramp_think;

	self->movedir[0] = self->message[0] - 'a';
	self->movedir[1] = self->message[1] - 'a';
	self->movedir[2] = (self->movedir[1] - self->movedir[0]) / (self->speed / FRAMETIME);
	"""


def target_earthquake_think (self): #edict_t *
	i = 0
	e = None

	if self.last_move_time < g_main.level.time:
		g_main.gi.positioned_sound (self.s.origin, self, CHAN_AUTO, self.noise_index, 1.0, ATTN_NONE, 0)
		self.last_move_time = g_main.level.time + 0.5

	for i in range(1, g_main.glob.num_edicts):
		e = g_main.g_edicts[i]
		if not e.inuse:
			continue
		if not e.client:
			continue
		if not e.groundentity:
			continue

		e.groundentity = None
		e.velocity[0] += crandom() * 150
		e.velocity[1] += crandom() * 150
		e.velocity[2] = self.speed * (100.0 / e.mass)

	if g_main.level.time < self.timestamp:
		self.nextthink = g_main.level.time + FRAMETIME
	"""
	int		i;
	edict_t	*e;

	if (self->last_move_time < level.time)
	{
		gi.positioned_sound (self->s.origin, self, CHAN_AUTO, self->noise_index, 1.0, ATTN_NONE, 0);
		self->last_move_time = level.time + 0.5;
	}

	for (i=1, e=g_edicts+i; i < globals.num_edicts; i++,e++)
	{
		if (!e->inuse)
			continue;
		if (!e->client)
			continue;
		if (!e->groundentity)
			continue;

		e->groundentity = NULL;
		e->velocity[0] += crandom()* 150;
		e->velocity[1] += crandom()* 150;
		e->velocity[2] = self->speed * (100.0 / e->mass);
	}

	if (level.time < self->timestamp)
		self->nextthink = level.time + FRAMETIME;
	"""


def target_earthquake_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	self.timestamp = g_main.level.time + self.count
	self.nextthink = g_main.level.time + FRAMETIME
	self.activator = activator
	self.last_move_time = 0
	"""
	self->timestamp = level.time + self->count;
	self->nextthink = level.time + FRAMETIME;
	self->activator = activator;
	self->last_move_time = 0;
	"""


def SP_target_earthquake (self): #edict_t *
	if not self.targetname:
		g_main.gi.dprintf("untargeted %s at %s\n", self.classname, g_utils.vtos(self.s.origin))

	if not self.count:
		self.count = 5

	if not self.speed:
		self.speed = 200

	self.svflags |= SVF_NOCLIENT
	self.think = target_earthquake_think
	self.use = target_earthquake_use

	self.noise_index = g_main.gi.soundindex ("world/quake.wav")
	"""
	if (!self->targetname)
		gi.dprintf("untargeted %s at %s\n", self->classname, vtos(self->s.origin));

	if (!self->count)
		self->count = 5;

	if (!self->speed)
		self->speed = 200;

	self->svflags |= SVF_NOCLIENT;
	self->think = target_earthquake_think;
	self->use = target_earthquake_use;

	self->noise_index = gi.soundindex ("world/quake.wav");
	"""
