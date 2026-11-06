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

Targets.

=======================================================================
"""
from __future__ import annotations

import numpy as np

from game import g_main, g_utils, g_misc, g_combat, g_weapon, g_spawn
from common.header.shared import CHAN_VOICE, CHAN_RELIABLE, CHAN_AUTO, ATTN_NORM, ATTN_NONE, RF_BEAM, RF_TRANSLUCENT, EF_BLASTER, EF_HYPERBLASTER, CS_CDTRACK, CS_LIGHTS, CONTENTS_SOLID, CONTENTS_MONSTER, CONTENTS_DEADMONSTER, DF_ALLOW_EXIT, PRINT_HIGH
from common.header.shared import temp_event_t, multicast_t

"""
#include "header/local.h"
"""

TARGET_HELP_PRIMARY = 1
TARGET_HELP_THINK_DELAY = 0.3

TE_EXPLOSION1 = temp_event_t.TE_EXPLOSION1.value
TE_SPLASH = temp_event_t.TE_SPLASH.value
TE_LASER_SPARKS = temp_event_t.TE_LASER_SPARKS.value
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
MULTICAST_PHS = multicast_t.MULTICAST_PHS.value
from game.header.local import svc_temp_entity, FRAMETIME, crandom, FL_IMMUNE_LASER, DAMAGE_ENERGY, MOD_EXPLOSIVE, MOD_EXIT, MOD_SPLASH, MOD_TARGET_BLASTER, MOD_TARGET_LASER, SFL_CROSS_TRIGGER_MASK, MOVETYPE_NONE
from game.header.game import SVF_NOCLIENT, solid_t
from common.header import shared
from common.shared import shared as shared_c
from game.header import game as game_h
from game.player import hud as p_hud
SOLID_NOT = solid_t.SOLID_NOT.value
"""
#include "g_local.h"
"""


def Use_Target_Tent (ent, other, activator): #edict_t *, edict_t *, edict_t *
	if not ent:

		return


	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (ent.style)
	g_main.gi.WritePosition (ent.s.origin)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)


def SP_target_temp_entity (ent): #edict_t *
	if not ent:

		return


	ent.use = Use_Target_Tent


def Use_Target_Speaker (ent, other, activator): #edict_t *, edict_t *, edict_t *
	if not ent:

		return


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


def SP_target_speaker (ent): #edict_t *
	if not ent:

		return


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


def Target_Help_Apply(msg: str, is_primary: int): #const char *, int (static)

	"""
	char *curr;
	size_t sz;
	"""

	if msg is None:

		return


	# Q2PORT: curr is the name of the game field, as Python strings can't be changed in place
	if is_primary:

		curr = "helpmessage1"
		sz = 512 # sizeof (game.helpmessage1)

	else:

		curr = "helpmessage2"
		sz = 512 # sizeof (game.helpmessage2)


	if getattr(g_main.game, curr) == msg:

		return


	setattr(g_main.game, curr, msg[:sz - 1 - 1]) # Q_strlcpy(curr, msg, sz - 1);

	g_main.game.helpchanged += 1

def Target_Help_Think (ent): #edict_t *

	if not ent:

		return


	Target_Help_Apply(ent.message, ent.spawnflags & TARGET_HELP_PRIMARY)
	ent.think = None

def Use_Target_Help (ent, other, activator): #edict_t *, edict_t *, edict_t *
	if not ent:

		return


	if g_main.level.time > TARGET_HELP_THINK_DELAY:

		Target_Help_Apply(ent.message, ent.spawnflags & TARGET_HELP_PRIMARY)

	else:

		# The game is still pre-loading so delay the help message a bit,
		# otherwise its changes to game structure will leak past save loads
		ent.think = Target_Help_Think
		ent.nextthink = TARGET_HELP_THINK_DELAY



def SP_target_help (ent): #edict_t *
	if not ent:

		return


	if g_main.deathmatch.value:
		#	# auto-remove for deathmatch
		g_utils.G_FreeEdict (ent)
		return

	if not ent.message:
		g_main.gi.dprintf ("%s with no message at %s\n", ent.classname, g_utils.vtos(ent.s.origin))
		g_utils.G_FreeEdict (ent)
		return
	ent.use = Use_Target_Help


def use_target_secret (ent, other, activator): #edict_t *, edict_t *, edict_t *
	if not ent:

		return


	g_main.gi.sound (ent, CHAN_VOICE, ent.noise_index, 1, ATTN_NORM, 0)

	g_main.level.found_secrets += 1

	g_utils.G_UseTargets (ent, activator)
	g_utils.G_FreeEdict (ent)


def SP_target_secret (ent): #edict_t *
	if not ent:

		return


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
	if shared_c.Q_stricmp(g_main.level.mapname, "mine3") == 0 and ent.s.origin[0] == 280 and ent.s.origin[1] == -2048 and ent.s.origin[2] == -624:
		ent.message = "You have found a secret area."


def use_target_goal (ent, other, activator): #edict_t *, edict_t *, edict_t *
	if not ent:

		return


	g_main.gi.sound (ent, CHAN_VOICE, ent.noise_index, 1, ATTN_NORM, 0)

	g_main.level.found_goals += 1

	if g_main.level.found_goals == g_main.level.total_goals:
		g_main.gi.configstring (CS_CDTRACK, "0")

	g_utils.G_UseTargets (ent, activator)
	g_utils.G_FreeEdict (ent)


def SP_target_goal (ent): #edict_t *
	if not ent:

		return


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


def target_explosion_explode (self): #edict_t *
	if not self:

		return


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


def use_target_explosion (self, other, activator): #edict_t *, edict_t *, edict_t *
	self.activator = activator

	if not self.delay:
		target_explosion_explode (self)
		return

	self.think = target_explosion_explode
	self.nextthink = g_main.level.time + self.delay


def SP_target_explosion (ent): #edict_t *
	if not ent:

		return


	ent.use = use_target_explosion
	ent.svflags = SVF_NOCLIENT


def use_target_changelevel (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self or not other:

		return


	if g_main.level.intermissiontime:
		return		# already activated

	if not g_main.deathmatch.value and not g_main.coop.value:
		if g_main.g_edicts[1].health <= 0:
			return

	# if noexit, do a ton of damage to other
	if g_main.deathmatch.value and not (int(g_main.dmflags.value) & DF_ALLOW_EXIT) and other != g_main.g_edicts[1]:
		g_combat.T_Damage (other, self, self, shared_c.vec3_origin, other.s.origin, shared_c.vec3_origin, 10 * other.max_health, 1000, 0, MOD_EXIT)
		return

	# if multiplayer, let everyone know who hit the exit
	if g_main.deathmatch.value:
		if activator and activator.client:
			g_main.gi.bprintf (PRINT_HIGH, "%s exited the level.\n", activator.client.pers.netname)

	# if going to a new unit, clear cross triggers
	if "*" in self.map:	
		g_main.game.serverflags &= ~SFL_CROSS_TRIGGER_MASK

	p_hud.BeginIntermission (self)


def SP_target_changelevel (ent): #edict_t *
	if not ent:

		return


	if not ent.map:
		g_main.gi.dprintf("target_changelevel with no map at %s\n", g_utils.vtos(ent.s.origin))
		g_utils.G_FreeEdict (ent)
		return

	# ugly hack because *SOMEBODY* screwed up their map
	if (shared_c.Q_stricmp(g_main.level.mapname, "fact1") == 0) and (shared_c.Q_stricmp(ent.map, "fact3") == 0):
		ent.map = "fact3$secret1"

	ent.use = use_target_changelevel
	ent.svflags = SVF_NOCLIENT


def use_target_splash (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self or not activator:

		return


	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (TE_SPLASH)
	g_main.gi.WriteByte (self.count)
	g_main.gi.WritePosition (self.s.origin)
	g_main.gi.WriteDir (self.movedir)
	g_main.gi.WriteByte (self.sounds)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)

	if self.dmg:
		g_combat.T_RadiusDamage (self, activator, self.dmg, None, self.dmg+40, MOD_SPLASH)


def SP_target_splash (self): #edict_t *
	if not self:

		return


	self.use = use_target_splash
	g_utils.G_SetMovedir (self.s.angles, self.movedir)

	if not self.count:
		self.count = 32

	self.svflags = SVF_NOCLIENT


def use_target_spawner (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self:

		return


	ent = None

	ent = g_utils.G_Spawn()
	ent.classname = self.target
	shared.VectorCopy (self.s.origin, ent.s.origin)
	shared.VectorCopy (self.s.angles, ent.s.angles)
	g_spawn.ED_CallSpawn (ent)
	g_main.gi.unlinkentity (ent)
	g_utils.KillBox (ent)
	g_main.gi.linkentity (ent)
	if self.speed:
		shared.VectorCopy (self.movedir, ent.velocity)


def SP_target_spawner (self): #edict_t *
	if not self:

		return


	#vec3_t	forward;
	#vec3_t	fact2spawnpoint1 = {-1504,512,72};
	forward = np.zeros((3,), dtype=np.float32)
	fact2spawnpoint1 = np.array([-1504, 512, 72], dtype=np.float32)

	self.use = use_target_spawner
	self.svflags = SVF_NOCLIENT

	# Maphack for the insane spawner in Mobs-Egerlings
	# beloved fact2. Found in KMQuake2
	if not shared_c.Q_stricmp(g_main.level.mapname, "fact2") \
		and shared_c.VectorCompare(self.s.origin, fact2spawnpoint1):

		shared.VectorSet (forward, 0, 0, 1)
		shared_c.VectorMA (self.s.origin, -8, forward, self.s.origin)


	if self.speed:
		g_utils.G_SetMovedir (self.s.angles, self.movedir)
		shared_c.VectorScale (self.movedir, self.speed, self.movedir)


def use_target_blaster (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self:

		return


	g_weapon.fire_blaster (self, self.s.origin, self.movedir, self.dmg, self.speed, EF_BLASTER, MOD_TARGET_BLASTER)
	g_main.gi.sound (self, CHAN_VOICE, self.noise_index, 1, ATTN_NORM, 0)


def SP_target_blaster (self): #edict_t *
	if not self:

		return


	self.use = use_target_blaster
	g_utils.G_SetMovedir (self.s.angles, self.movedir)
	self.noise_index = g_main.gi.soundindex ("weapons/laser2.wav")

	if not self.dmg:
		self.dmg = 15
	if not self.speed:
		self.speed = 1000

	self.svflags = SVF_NOCLIENT


def trigger_crosslevel_trigger_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self or not activator:

		return


	g_main.game.serverflags |= self.spawnflags
	g_utils.G_UseTargets (self, activator)
	g_utils.G_FreeEdict (self)


def SP_target_crosslevel_trigger (self): #edict_t *
	if not self:

		return


	self.svflags = SVF_NOCLIENT
	self.use = trigger_crosslevel_trigger_use


def target_crosslevel_target_think (self): #edict_t *
	if not self:

		return


	if self.spawnflags == (g_main.game.serverflags & SFL_CROSS_TRIGGER_MASK & self.spawnflags):
		g_utils.G_UseTargets (self, self)
		g_utils.G_FreeEdict (self)


def SP_target_crosslevel_target (self): #edict_t *
	if not self:

		return


	if not self.delay:
		self.delay = 1
	self.svflags = SVF_NOCLIENT

	self.think = target_crosslevel_target_think
	self.nextthink = g_main.level.time + self.delay


def target_laser_think (self): #edict_t *
	if not self:

		return


	ignore = None
	start = shared_c.vec3_origin.copy()
	end = shared_c.vec3_origin.copy()
	tr = shared.trace_t()
	point = shared_c.vec3_origin.copy()
	last_movedir = shared_c.vec3_origin.copy()
	count = 0

	if self.spawnflags & 0x80000000:
		count = 8
	else:
		count = 4

	if self.enemy:
		shared.VectorCopy (self.movedir, last_movedir)
		shared_c.VectorMA (self.enemy.absmin, 0.5, self.enemy.size, point)
		shared.VectorSubtract (point, self.s.origin, self.movedir)
		shared_c.VectorNormalize (self.movedir)
		if not shared_c.VectorCompare(self.movedir, last_movedir):
			self.spawnflags |= 0x80000000

	ignore = self
	shared.VectorCopy (self.s.origin, start)
	shared_c.VectorMA (start, 2048, self.movedir, end)
	while True:
		tr = g_main.gi.trace (start, None, None, end, ignore, CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_DEADMONSTER)

		if not tr.ent:
			break

		# hurt it if we can
		if (tr.ent.takedamage) and not (tr.ent.flags & FL_IMMUNE_LASER):
			g_combat.T_Damage (tr.ent, self, self.activator, self.movedir, tr.endpos, shared_c.vec3_origin, self.dmg, 1, DAMAGE_ENERGY, MOD_TARGET_LASER)

		# if we hit something that's not a monster or player or is immune to lasers, we're done
		if not (tr.ent.svflags & game_h.SVF_MONSTER) and not tr.ent.client:
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
		shared.VectorCopy (tr.endpos, start)

	shared.VectorCopy (tr.endpos, self.s.old_origin)

	self.nextthink = g_main.level.time + FRAMETIME


def target_laser_on (self): #edict_t *
	if not self:

		return


	if not self.activator:
		self.activator = self
	self.spawnflags |= 0x80000001
	self.svflags &= ~SVF_NOCLIENT
	target_laser_think (self)


def target_laser_off (self): #edict_t *
	if not self:

		return


	self.spawnflags &= ~1
	self.svflags |= SVF_NOCLIENT
	self.nextthink = 0


def target_laser_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self or not activator:

		return


	self.activator = activator
	if self.spawnflags & 1:
		target_laser_off (self)
	else:
		target_laser_on (self)


def target_laser_start (self): #edict_t *
	if not self:

		return


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

	shared.VectorSet (self.mins, -8, -8, -8)
	shared.VectorSet (self.maxs, 8, 8, 8)
	g_main.gi.linkentity (self)

	if self.spawnflags & 1:
		target_laser_on (self)
	else:
		target_laser_off (self)


def SP_target_laser (self): #edict_t *
	# let everything else get spawned before we start firing
	if not self:

		return


	self.think = target_laser_start
	self.nextthink = g_main.level.time + 1


def target_lightramp_think (self): #edict_t *
	if not self:

		return


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


def target_lightramp_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self:

		return


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


def SP_target_lightramp (self): #edict_t *
	if not self:

		return


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


def target_earthquake_think (self): #edict_t *
	if not self:

		return


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


def target_earthquake_use (self, other, activator): #edict_t *, edict_t *, edict_t *
	if not self or not activator:

		return


	self.timestamp = g_main.level.time + self.count
	self.nextthink = g_main.level.time + FRAMETIME
	self.activator = activator
	self.last_move_time = 0


def SP_target_earthquake (self): #edict_t *
	if not self:

		return


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
