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
from game import g_combat
from game import g_cmds
from game import g_misc
from game import p_weapon
from game.game import SVF_MONSTER, SVF_DEADMONSTER
from game.game import solid_t
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value
from game.q_shared import (MASK_SHOT, MASK_WATER, MASK_OPAQUE, CONTENTS_SOLID,
	CONTENTS_MONSTER, CONTENTS_DEADMONSTER, CONTENTS_WATER, CONTENTS_SLIME,
	CONTENTS_LAVA, CONTENTS_WINDOW, SURF_SKY, SURF_WARP, SURF_TRANS33,
	SURF_TRANS66, SURF_FLOWING, SPLASH_BLUE_WATER, SPLASH_BROWN_WATER,
	SPLASH_SLIME, SPLASH_LAVA, SPLASH_UNKNOWN, EF_GRENADE, EF_ROCKET,
	EF_BFG, EF_ANIM_ALLFAST)
from game.g_local import (svc_temp_entity, FRAMETIME, MOVETYPE_FLYMISSILE,
	MOVETYPE_BOUNCE, PNOISE_IMPACT,
	DAMAGE_NO_KNOCKBACK, DAMAGE_BULLET, DAMAGE_ENERGY, DAMAGE_RADIUS,
	MOD_HIT, MOD_HYPERBLASTER, MOD_BLASTER, MOD_HANDGRENADE, MOD_GRENADE,
	MOD_HELD_GRENADE, MOD_HG_SPLASH, MOD_G_SPLASH, MOD_ROCKET, MOD_R_SPLASH,
	MOD_RAILGUN, MOD_BFG_EFFECT, MOD_BFG_BLAST, MOD_BFG_LASER, FL_IMMUNE_LASER)
from game.q_shared import (multicast_t, CHAN_VOICE, CHAN_WEAPON, ATTN_NORM,
	vec3_origin, YAW, PITCH, ROLL)
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
MULTICAST_PHS = multicast_t.MULTICAST_PHS.value

"""
#include "g_local.h"

/*
=================
check_dodge
=================
*/
"""
def check_dodge (self, start, dir, speed):
	#vec3_t end, v
	#float eta
	end = [0, 0, 0]
	v = [0, 0, 0]

	# easy mode only ducks one quarter the time
	if g_main.skill.value == 0:
		if g_local.random() > 0.25:
			return

	q_shared.VectorMA (start, 8192, dir, end)
	tr = g_main.gi.trace (start, None, None, end, self, MASK_SHOT)
	if (tr.ent) and (tr.ent.svflags & SVF_MONSTER) and (tr.ent.health > 0) and (tr.ent.monsterinfo.dodge) and g_ai.infront(tr.ent, self):
		q_shared.VectorSubtract (tr.endpos, start, v)
		eta = (q_shared.VectorLength(v) - tr.ent.maxs[0]) / speed
		tr.ent.monsterinfo.dodge (tr.ent, self, eta)


"""
=================
fire_hit

Used for all impact (hit/punch/slash) attacks
=================
"""
def fire_hit (self, aim, damage, kick):
	#vec3_t forward, right, up, v, point, dir
	#float range
	forward = [0, 0, 0]
	right = [0, 0, 0]
	up = [0, 0, 0]
	v = [0, 0, 0]
	point = [0, 0, 0]
	dir = [0, 0, 0]

	#see if enemy is in range
	q_shared.VectorSubtract (self.enemy.s.origin, self.s.origin, dir)
	range = q_shared.VectorLength(dir)
	if range > aim[0]:
		return False

	if aim[1] > self.mins[0] and aim[1] < self.maxs[0]:
		# the hit is straight on so back the range up to the edge of their bbox
		range -= self.enemy.maxs[0]
	else:
		# this is a side hit so adjust the "right" value out to the edge of their bbox
		if aim[1] < 0:
			aim[1] = self.enemy.mins[0]
		else:
			aim[1] = self.enemy.maxs[0]

	q_shared.VectorMA (self.s.origin, range, dir, point)

	tr = g_main.gi.trace (self.s.origin, None, None, point, self, MASK_SHOT)
	if tr.fraction < 1:
		if not tr.ent.takedamage:
			return False
		# if it will hit any client/monster then hit the one we wanted to hit
		if (tr.ent.svflags & SVF_MONSTER) or (tr.ent.client):
			tr.ent = self.enemy

	q_shared.AngleVectors(self.s.angles, forward, right, up)
	q_shared.VectorMA (self.s.origin, range, forward, point)
	q_shared.VectorMA (point, aim[1], right, point)
	q_shared.VectorMA (point, aim[2], up, point)
	q_shared.VectorSubtract (point, self.enemy.s.origin, dir)

	# do the damage
	g_combat.T_Damage (tr.ent, self, self, dir, point, vec3_origin, damage, kick/2, DAMAGE_NO_KNOCKBACK, MOD_HIT)

	if not (tr.ent.svflags & SVF_MONSTER) and (not tr.ent.client):
		return False

	# do our special form of knockback here
	q_shared.VectorMA (self.enemy.absmin, 0.5, self.enemy.size, v)
	q_shared.VectorSubtract (v, point, v)
	q_shared.VectorNormalize (v)
	q_shared.VectorMA (self.enemy.velocity, kick, v, self.enemy.velocity)
	if self.enemy.velocity[2] > 0:
		self.enemy.groundentity = None
	return True


"""
=================
fire_lead

This is an internal support routine used for bullet/pellet based weapons.
=================
"""
def fire_lead (self, start, aimdir, damage, kick, te_impact, hspread, vspread, mod):
	#vec3_t dir, forward, right, up, end, water_start
	#float r, u
	#qboolean water
	#int content_mask
	dir = [0, 0, 0]
	forward = [0, 0, 0]
	right = [0, 0, 0]
	up = [0, 0, 0]
	end = [0, 0, 0]
	water_start = [0, 0, 0]
	water = False
	content_mask = MASK_SHOT | MASK_WATER

	tr = g_main.gi.trace (self.s.origin, None, None, start, self, MASK_SHOT)
	if not (tr.fraction < 1.0):
		g_utils.vectoangles (aimdir, dir)
		q_shared.AngleVectors (dir, forward, right, up)

		r = g_local.crandom()*hspread
		u = g_local.crandom()*vspread
		q_shared.VectorMA (start, 8192, forward, end)
		q_shared.VectorMA (end, r, right, end)
		q_shared.VectorMA (end, u, up, end)

		if g_main.gi.pointcontents (start) & MASK_WATER:
			water = True
			q_shared.VectorCopy (start, water_start)
			content_mask &= ~MASK_WATER

		tr = g_main.gi.trace (start, None, None, end, self, content_mask)

		# see if we hit water
		if tr.contents & MASK_WATER:
			#int color
			water = True
			q_shared.VectorCopy (tr.endpos, water_start)

			if not q_shared.VectorCompare (start, tr.endpos):
				if tr.contents & CONTENTS_WATER:
					if tr.surface.name == "*brwater":
						color = SPLASH_BROWN_WATER
					else:
						color = SPLASH_BLUE_WATER
				elif tr.contents & CONTENTS_SLIME:
					color = SPLASH_SLIME
				elif tr.contents & CONTENTS_LAVA:
					color = SPLASH_LAVA
				else:
					color = SPLASH_UNKNOWN

				if color != SPLASH_UNKNOWN:
					g_main.gi.WriteByte (svc_temp_entity)
					g_main.gi.WriteByte (q_shared.temp_event_t.TE_SPLASH.value)
					g_main.gi.WriteByte (8)
					g_main.gi.WritePosition (tr.endpos)
					g_main.gi.WriteDir (tr.plane.normal)
					g_main.gi.WriteByte (color)
					g_main.gi.multicast (tr.endpos, MULTICAST_PVS)

				# change bullet's course when it enters water
				q_shared.VectorSubtract (end, start, dir)
				g_utils.vectoangles (dir, dir)
				q_shared.AngleVectors (dir, forward, right, up)
				r = g_local.crandom()*hspread*2
				u = g_local.crandom()*vspread*2
				q_shared.VectorMA (water_start, 8192, forward, end)
				q_shared.VectorMA (end, r, right, end)
				q_shared.VectorMA (end, u, up, end)

			# re-trace ignoring water this time
			tr = g_main.gi.trace (water_start, None, None, end, self, MASK_SHOT)

	# send gun puff / flash
	if not ((tr.surface) and (tr.surface.flags & SURF_SKY)):
		if tr.fraction < 1.0:
			if tr.ent.takedamage:
				g_combat.T_Damage (tr.ent, self, self, aimdir, tr.endpos, tr.plane.normal, damage, kick, DAMAGE_BULLET, mod)
			else:
				if tr.surface.name[:3] != "sky":
					g_main.gi.WriteByte (svc_temp_entity)
					g_main.gi.WriteByte (te_impact)
					g_main.gi.WritePosition (tr.endpos)
					g_main.gi.WriteDir (tr.plane.normal)
					g_main.gi.multicast (tr.endpos, MULTICAST_PVS)

					if self.client:
						p_weapon.PlayerNoise(self, tr.endpos, PNOISE_IMPACT)

	# if went through water, determine where the end and make a bubble trail
	if water:
		#vec3_t pos
		pos = [0, 0, 0]

		q_shared.VectorSubtract (tr.endpos, water_start, dir)
		q_shared.VectorNormalize (dir)
		q_shared.VectorMA (tr.endpos, -2, dir, pos)
		if g_main.gi.pointcontents (pos) & MASK_WATER:
			q_shared.VectorCopy (pos, tr.endpos)
		else:
			tr = g_main.gi.trace (pos, None, None, water_start, tr.ent, MASK_WATER)

		q_shared.VectorAdd (water_start, tr.endpos, pos)
		q_shared.VectorScale (pos, 0.5, pos)

		g_main.gi.WriteByte (svc_temp_entity)
		g_main.gi.WriteByte (q_shared.temp_event_t.TE_BUBBLETRAIL.value)
		g_main.gi.WritePosition (water_start)
		g_main.gi.WritePosition (tr.endpos)
		g_main.gi.multicast (pos, MULTICAST_PVS)


"""
=================
fire_bullet

Fires a single round.  Used for machinegun and chaingun.
=================
"""
def fire_bullet (self, start, aimdir, damage, kick, hspread, vspread, mod):
	fire_lead (self, start, aimdir, damage, kick, q_shared.temp_event_t.TE_GUNSHOT.value, hspread, vspread, mod)


"""
=================
fire_shotgun

Shoots shotgun pellets.  Used by shotgun and super shotgun.
=================
"""
def fire_shotgun (self, start, aimdir, damage, kick, hspread, vspread, count, mod):
	#int i
	for i in range(count):
		fire_lead (self, start, aimdir, damage, kick, q_shared.temp_event_t.TE_SHOTGUN.value, hspread, vspread, mod)


"""
=================
fire_blaster

Fires a single blaster bolt.  Used by the blaster and hyper blaster.
=================
"""
def blaster_touch (self, other, plane, surf):
	#int mod
	if other == self.owner:
		return

	if surf and (surf.flags & SURF_SKY):
		g_utils.G_FreeEdict (self)
		return

	if self.owner.client:
		p_weapon.PlayerNoise(self.owner, self.s.origin, PNOISE_IMPACT)

	if other.takedamage:
		if self.spawnflags & 1:
			mod = MOD_HYPERBLASTER
		else:
			mod = MOD_BLASTER
		# NOTE: latent C bug - fire_blaster() calls touch() with (NULL, NULL),
		# so plane is NULL here when the initial gi.trace hit a takedamage entity.
		# C does plane->normal (NULL deref, only avoided because that case is rare);
		# we guard with vec3_origin to match the !plane handling in the else branch.
		g_combat.T_Damage (other, self, self.owner, self.velocity, self.s.origin, (plane.normal if plane else vec3_origin), self.dmg, 1, DAMAGE_ENERGY, mod)
	else:
		g_main.gi.WriteByte (svc_temp_entity)
		g_main.gi.WriteByte (q_shared.temp_event_t.TE_BLASTER.value)
		g_main.gi.WritePosition (self.s.origin)
		if not plane:
			g_main.gi.WriteDir (vec3_origin)
		else:
			g_main.gi.WriteDir (plane.normal)
		g_main.gi.multicast (self.s.origin, MULTICAST_PVS)

	g_utils.G_FreeEdict (self)


def fire_blaster (self, start, dir, damage, speed, effect, hyper):
	#edict_t *bolt
	bolt = g_utils.G_Spawn()
	q_shared.VectorNormalize (dir)

	bolt.svflags = SVF_DEADMONSTER
	q_shared.VectorCopy (start, bolt.s.origin)
	q_shared.VectorCopy (start, bolt.s.old_origin)
	g_utils.vectoangles (dir, bolt.s.angles)
	q_shared.VectorScale (dir, speed, bolt.velocity)
	bolt.movetype = MOVETYPE_FLYMISSILE
	bolt.clipmask = MASK_SHOT
	bolt.solid = SOLID_BBOX
	bolt.s.effects |= effect
	q_shared.VectorClear (bolt.mins)
	q_shared.VectorClear (bolt.maxs)
	bolt.s.modelindex = g_main.gi.modelindex ("models/objects/laser/tris.md2")
	bolt.s.sound = g_main.gi.soundindex ("misc/lasfly.wav")
	bolt.owner = self
	bolt.touch = blaster_touch
	bolt.nextthink = g_main.level.time + 2
	bolt.think = g_utils.G_FreeEdict
	bolt.dmg = damage
	bolt.classname = "bolt"
	if hyper:
		bolt.spawnflags = 1
	g_main.gi.linkentity (bolt)

	if self.client:
		check_dodge (self, bolt.s.origin, dir, speed)

	tr = g_main.gi.trace (self.s.origin, None, None, bolt.s.origin, bolt, MASK_SHOT)
	if tr.fraction < 1.0:
		q_shared.VectorMA (bolt.s.origin, -10, dir, bolt.s.origin)
		bolt.touch (bolt, tr.ent, None, None)


"""
=================
fire_grenade
=================
"""
def Grenade_Explode (ent):
	#vec3_t origin, v, dir
	#int mod
	origin = [0, 0, 0]
	v = [0, 0, 0]
	dir = [0, 0, 0]

	if ent.owner.client:
		p_weapon.PlayerNoise(ent.owner, ent.s.origin, PNOISE_IMPACT)

	if ent.enemy:
		#float points
		q_shared.VectorAdd (ent.enemy.mins, ent.enemy.maxs, v)
		q_shared.VectorMA (ent.enemy.s.origin, 0.5, v, v)
		q_shared.VectorSubtract (ent.s.origin, v, v)
		points = ent.dmg - 0.5 * q_shared.VectorLength (v)
		q_shared.VectorSubtract (ent.enemy.s.origin, ent.s.origin, dir)
		if ent.spawnflags & 1:
			mod = MOD_HANDGRENADE
		else:
			mod = MOD_GRENADE
		g_combat.T_Damage (ent.enemy, ent, ent.owner, dir, ent.s.origin, vec3_origin, int(points), int(points), DAMAGE_RADIUS, mod)

	if ent.spawnflags & 2:
		mod = MOD_HELD_GRENADE
	elif ent.spawnflags & 1:
		mod = MOD_HG_SPLASH
	else:
		mod = MOD_G_SPLASH
	g_combat.T_RadiusDamage(ent, ent.owner, ent.dmg, ent.enemy, ent.dmg_radius, mod)

	q_shared.VectorMA (ent.s.origin, -0.02, ent.velocity, origin)
	g_main.gi.WriteByte (svc_temp_entity)
	if ent.waterlevel:
		if ent.groundentity:
			g_main.gi.WriteByte (q_shared.temp_event_t.TE_GRENADE_EXPLOSION_WATER.value)
		else:
			g_main.gi.WriteByte (q_shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER.value)
	else:
		if ent.groundentity:
			g_main.gi.WriteByte (q_shared.temp_event_t.TE_GRENADE_EXPLOSION.value)
		else:
			g_main.gi.WriteByte (q_shared.temp_event_t.TE_ROCKET_EXPLOSION.value)
	g_main.gi.WritePosition (origin)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PHS)

	g_utils.G_FreeEdict (ent)


def Grenade_Touch (ent, other, plane, surf):
	if other == ent.owner:
		return

	if surf and (surf.flags & SURF_SKY):
		g_utils.G_FreeEdict (ent)
		return

	if not other.takedamage:
		if ent.spawnflags & 1:
			if g_local.random() > 0.5:
				g_main.gi.sound (ent, CHAN_VOICE, g_main.gi.soundindex ("weapons/hgrenb1a.wav"), 1, ATTN_NORM, 0)
			else:
				g_main.gi.sound (ent, CHAN_VOICE, g_main.gi.soundindex ("weapons/hgrenb2a.wav"), 1, ATTN_NORM, 0)
		else:
			g_main.gi.sound (ent, CHAN_VOICE, g_main.gi.soundindex ("weapons/grenlb1b.wav"), 1, ATTN_NORM, 0)
		return

	ent.enemy = other
	Grenade_Explode (ent)


def fire_grenade (self, start, aimdir, damage, speed, timer, damage_radius):
	#edict_t *grenade
	#vec3_t dir, forward, right, up
	dir = [0, 0, 0]
	forward = [0, 0, 0]
	right = [0, 0, 0]
	up = [0, 0, 0]

	g_utils.vectoangles (aimdir, dir)
	q_shared.AngleVectors (dir, forward, right, up)

	grenade = g_utils.G_Spawn()
	q_shared.VectorCopy (start, grenade.s.origin)
	q_shared.VectorScale (aimdir, speed, grenade.velocity)
	q_shared.VectorMA (grenade.velocity, 200 + g_local.crandom() * 10.0, up, grenade.velocity)
	q_shared.VectorMA (grenade.velocity, g_local.crandom() * 10.0, right, grenade.velocity)
	q_shared.VectorSet (grenade.avelocity, 300, 300, 300)
	grenade.movetype = MOVETYPE_BOUNCE
	grenade.clipmask = MASK_SHOT
	grenade.solid = SOLID_BBOX
	grenade.s.effects |= q_shared.EF_GRENADE
	q_shared.VectorClear (grenade.mins)
	q_shared.VectorClear (grenade.maxs)
	grenade.s.modelindex = g_main.gi.modelindex ("models/objects/grenade/tris.md2")
	grenade.owner = self
	grenade.touch = Grenade_Touch
	grenade.nextthink = g_main.level.time + timer
	grenade.think = Grenade_Explode
	grenade.dmg = damage
	grenade.dmg_radius = damage_radius
	grenade.classname = "grenade"

	g_main.gi.linkentity (grenade)


def fire_grenade2 (self, start, aimdir, damage, speed, timer, damage_radius, held):
	#edict_t *grenade
	#vec3_t dir, forward, right, up
	dir = [0, 0, 0]
	forward = [0, 0, 0]
	right = [0, 0, 0]
	up = [0, 0, 0]

	g_utils.vectoangles (aimdir, dir)
	q_shared.AngleVectors (dir, forward, right, up)

	grenade = g_utils.G_Spawn()
	q_shared.VectorCopy (start, grenade.s.origin)
	q_shared.VectorScale (aimdir, speed, grenade.velocity)
	q_shared.VectorMA (grenade.velocity, 200 + g_local.crandom() * 10.0, up, grenade.velocity)
	q_shared.VectorMA (grenade.velocity, g_local.crandom() * 10.0, right, grenade.velocity)
	q_shared.VectorSet (grenade.avelocity, 300, 300, 300)
	grenade.movetype = MOVETYPE_BOUNCE
	grenade.clipmask = MASK_SHOT
	grenade.solid = SOLID_BBOX
	grenade.s.effects |= q_shared.EF_GRENADE
	q_shared.VectorClear (grenade.mins)
	q_shared.VectorClear (grenade.maxs)
	grenade.s.modelindex = g_main.gi.modelindex ("models/objects/grenade2/tris.md2")
	grenade.owner = self
	grenade.touch = Grenade_Touch
	grenade.nextthink = g_main.level.time + timer
	grenade.think = Grenade_Explode
	grenade.dmg = damage
	grenade.dmg_radius = damage_radius
	grenade.classname = "hgrenade"
	if held:
		grenade.spawnflags = 3
	else:
		grenade.spawnflags = 1
	grenade.s.sound = g_main.gi.soundindex("weapons/hgrenc1b.wav")

	if timer <= 0.0:
		Grenade_Explode (grenade)
	else:
		g_main.gi.sound (self, CHAN_WEAPON, g_main.gi.soundindex ("weapons/hgrent1a.wav"), 1, ATTN_NORM, 0)
		g_main.gi.linkentity (grenade)


"""
=================
fire_rocket
=================
"""
def rocket_touch (ent, other, plane, surf):
	#vec3_t origin
	#int n
	origin = [0, 0, 0]

	if other == ent.owner:
		return

	if surf and (surf.flags & SURF_SKY):
		g_utils.G_FreeEdict (ent)
		return

	if ent.owner.client:
		p_weapon.PlayerNoise(ent.owner, ent.s.origin, PNOISE_IMPACT)

	# calculate position for the explosion entity
	q_shared.VectorMA (ent.s.origin, -0.02, ent.velocity, origin)

	if other.takedamage:
		g_combat.T_Damage (other, ent, ent.owner, ent.velocity, ent.s.origin, plane.normal, ent.dmg, 0, 0, MOD_ROCKET)
	else:
		# don't throw any debris in net games
		if not g_main.deathmatch.value and not g_main.coop.value:
			if (surf) and not (surf.flags & (SURF_WARP|SURF_TRANS33|SURF_TRANS66|SURF_FLOWING)):
				n = _r.randint(0, 2147483647) % 5
				while n:
					n -= 1
					g_misc.ThrowDebris (ent, "models/objects/debris2/tris.md2", 2, ent.s.origin)

	g_combat.T_RadiusDamage(ent, ent.owner, ent.radius_dmg, other, ent.dmg_radius, MOD_R_SPLASH)

	g_main.gi.WriteByte (svc_temp_entity)
	if ent.waterlevel:
		g_main.gi.WriteByte (q_shared.temp_event_t.TE_ROCKET_EXPLOSION_WATER.value)
	else:
		g_main.gi.WriteByte (q_shared.temp_event_t.TE_ROCKET_EXPLOSION.value)
	g_main.gi.WritePosition (origin)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PHS)

	g_utils.G_FreeEdict (ent)


def fire_rocket (self, start, dir, damage, speed, damage_radius, radius_damage):
	#edict_t *rocket
	rocket = g_utils.G_Spawn()
	q_shared.VectorCopy (start, rocket.s.origin)
	q_shared.VectorCopy (dir, rocket.movedir)
	g_utils.vectoangles (dir, rocket.s.angles)
	q_shared.VectorScale (dir, speed, rocket.velocity)
	rocket.movetype = MOVETYPE_FLYMISSILE
	rocket.clipmask = MASK_SHOT
	rocket.solid = SOLID_BBOX
	rocket.s.effects |= q_shared.EF_ROCKET
	q_shared.VectorClear (rocket.mins)
	q_shared.VectorClear (rocket.maxs)
	rocket.s.modelindex = g_main.gi.modelindex ("models/objects/rocket/tris.md2")
	rocket.owner = self
	rocket.touch = rocket_touch
	rocket.nextthink = g_main.level.time + 8000/speed
	rocket.think = g_utils.G_FreeEdict
	rocket.dmg = damage
	rocket.radius_dmg = radius_damage
	rocket.dmg_radius = damage_radius
	rocket.s.sound = g_main.gi.soundindex ("weapons/rockfly.wav")
	rocket.classname = "rocket"

	if self.client:
		check_dodge (self, rocket.s.origin, dir, speed)

	g_main.gi.linkentity (rocket)


"""
=================
fire_rail
=================
"""
def fire_rail (self, start, aimdir, damage, kick):
	#vec3_t from, end
	#edict_t *ignore
	#int mask
	#qboolean water
	from_ = [0, 0, 0]
	end = [0, 0, 0]
	ignore = self
	water = False
	mask = MASK_SHOT|CONTENTS_SLIME|CONTENTS_LAVA
	q_shared.VectorMA (start, 8192, aimdir, end)
	q_shared.VectorCopy (start, from_)
	while ignore:
		tr = g_main.gi.trace (from_, None, None, end, ignore, mask)

		if tr.contents & (CONTENTS_SLIME|CONTENTS_LAVA):
			mask &= ~(CONTENTS_SLIME|CONTENTS_LAVA)
			water = True
		else:
			#ZOID--added so rail goes through SOLID_BBOX entities (gibs, etc)
			if (tr.ent.svflags & SVF_MONSTER) or (tr.ent.client) or (tr.ent.solid == SOLID_BBOX):
				ignore = tr.ent
			else:
				ignore = None

			if (tr.ent != self) and (tr.ent.takedamage):
				g_combat.T_Damage (tr.ent, self, self, aimdir, tr.endpos, tr.plane.normal, damage, kick, 0, MOD_RAILGUN)

		q_shared.VectorCopy (tr.endpos, from_)

	# send gun puff / flash
	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (q_shared.temp_event_t.TE_RAILTRAIL.value)
	g_main.gi.WritePosition (start)
	g_main.gi.WritePosition (tr.endpos)
	g_main.gi.multicast (self.s.origin, MULTICAST_PHS)
	if water:
		g_main.gi.WriteByte (svc_temp_entity)
		g_main.gi.WriteByte (q_shared.temp_event_t.TE_RAILTRAIL.value)
		g_main.gi.WritePosition (start)
		g_main.gi.WritePosition (tr.endpos)
		g_main.gi.multicast (tr.endpos, MULTICAST_PHS)

	if self.client:
		p_weapon.PlayerNoise(self, tr.endpos, PNOISE_IMPACT)


"""
=================
fire_bfg
=================
"""
def bfg_explode (self):
	#edict_t *ent
	#float points, dist
	#vec3_t v
	v = [0, 0, 0]

	if self.s.frame == 0:
		# the BFG effect
		ent = None
		while (ent := g_utils.findradius(ent, self.s.origin, self.dmg_radius)) is not None:
			if not ent.takedamage:
				continue
			if ent == self.owner:
				continue
			if not g_combat.CanDamage (ent, self):
				continue
			if not g_combat.CanDamage (ent, self.owner):
				continue

			q_shared.VectorAdd (ent.mins, ent.maxs, v)
			q_shared.VectorMA (ent.s.origin, 0.5, v, v)
			q_shared.VectorSubtract (self.s.origin, v, v)
			dist = q_shared.VectorLength(v)
			points = self.radius_dmg * (1.0 - math.sqrt(dist/self.dmg_radius))
			if ent == self.owner:
				points = points * 0.5

			g_main.gi.WriteByte (svc_temp_entity)
			g_main.gi.WriteByte (q_shared.temp_event_t.TE_BFG_EXPLOSION.value)
			g_main.gi.WritePosition (ent.s.origin)
			g_main.gi.multicast (ent.s.origin, MULTICAST_PHS)
			g_combat.T_Damage (ent, self, self.owner, self.velocity, ent.s.origin, vec3_origin, int(points), 0, DAMAGE_ENERGY, MOD_BFG_EFFECT)

	self.nextthink = g_main.level.time + FRAMETIME
	self.s.frame += 1
	if self.s.frame == 5:
		self.think = g_utils.G_FreeEdict


def bfg_touch (self, other, plane, surf):
	if other == self.owner:
		return

	if surf and (surf.flags & SURF_SKY):
		g_utils.G_FreeEdict (self)
		return

	if self.owner.client:
		p_weapon.PlayerNoise(self.owner, self.s.origin, PNOISE_IMPACT)

	# core explosion - prevents firing it into the wall/floor
	if other.takedamage:
		g_combat.T_Damage (other, self, self.owner, self.velocity, self.s.origin, plane.normal, 200, 0, 0, MOD_BFG_BLAST)
	g_combat.T_RadiusDamage(self, self.owner, 200, other, 100, MOD_BFG_BLAST)

	g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex ("weapons/bfg__x1b.wav"), 1, ATTN_NORM, 0)
	self.solid = SOLID_NOT
	self.touch = None
	q_shared.VectorMA (self.s.origin, -1 * FRAMETIME, self.velocity, self.s.origin)
	q_shared.VectorClear (self.velocity)
	self.s.modelindex = g_main.gi.modelindex ("sprites/s_bfg3.sp2")
	self.s.frame = 0
	self.s.sound = 0
	self.s.effects &= ~q_shared.EF_ANIM_ALLFAST
	self.think = bfg_explode
	self.nextthink = g_main.level.time + FRAMETIME
	self.enemy = other

	g_main.gi.WriteByte (svc_temp_entity)
	g_main.gi.WriteByte (q_shared.temp_event_t.TE_BFG_BIGEXPLOSION.value)
	g_main.gi.WritePosition (self.s.origin)
	g_main.gi.multicast (self.s.origin, MULTICAST_PVS)


def bfg_think (self):
	#edict_t *ent, *ignore
	#vec3_t point, dir, start, end
	#int dmg
	dmg = 5 if g_main.deathmatch.value else 10
	point = [0, 0, 0]
	dir = [0, 0, 0]
	start = [0, 0, 0]
	end = [0, 0, 0]

	ent = None
	while (ent := g_utils.findradius(ent, self.s.origin, 256)) is not None:
		if ent == self:
			continue

		if ent == self.owner:
			continue

		if not ent.takedamage:
			continue

		if not (ent.svflags & SVF_MONSTER) and (not ent.client) and (ent.classname != "misc_explobox"):
			continue

		q_shared.VectorMA (ent.absmin, 0.5, ent.size, point)

		q_shared.VectorSubtract (point, self.s.origin, dir)
		q_shared.VectorNormalize (dir)

		ignore = self
		q_shared.VectorCopy (self.s.origin, start)
		q_shared.VectorMA (start, 2048, dir, end)
		while True:
			tr = g_main.gi.trace (start, None, None, end, ignore, CONTENTS_SOLID|CONTENTS_MONSTER|CONTENTS_DEADMONSTER)

			if not tr.ent:
				break

			# hurt it if we can
			if (tr.ent.takedamage) and not (tr.ent.flags & FL_IMMUNE_LASER) and (tr.ent != self.owner):
				g_combat.T_Damage (tr.ent, self, self.owner, dir, tr.endpos, vec3_origin, dmg, 1, DAMAGE_ENERGY, MOD_BFG_LASER)

			# if we hit something that's not a monster or player we're done
			if not (tr.ent.svflags & SVF_MONSTER) and (not tr.ent.client):
				g_main.gi.WriteByte (svc_temp_entity)
				g_main.gi.WriteByte (q_shared.temp_event_t.TE_LASER_SPARKS.value)
				g_main.gi.WriteByte (4)
				g_main.gi.WritePosition (tr.endpos)
				g_main.gi.WriteDir (tr.plane.normal)
				g_main.gi.WriteByte (self.s.skinnum)
				g_main.gi.multicast (tr.endpos, MULTICAST_PVS)
				break

			ignore = tr.ent
			q_shared.VectorCopy (tr.endpos, start)

		g_main.gi.WriteByte (svc_temp_entity)
		g_main.gi.WriteByte (q_shared.temp_event_t.TE_BFG_LASER.value)
		g_main.gi.WritePosition (self.s.origin)
		g_main.gi.WritePosition (tr.endpos)
		g_main.gi.multicast (self.s.origin, MULTICAST_PHS)

	self.nextthink = g_main.level.time + FRAMETIME


def fire_bfg (self, start, dir, damage, speed, damage_radius):
	#edict_t *bfg
	bfg = g_utils.G_Spawn()
	q_shared.VectorCopy (start, bfg.s.origin)
	q_shared.VectorCopy (dir, bfg.movedir)
	g_utils.vectoangles (dir, bfg.s.angles)
	q_shared.VectorScale (dir, speed, bfg.velocity)
	bfg.movetype = MOVETYPE_FLYMISSILE
	bfg.clipmask = MASK_SHOT
	bfg.solid = SOLID_BBOX
	bfg.s.effects |= q_shared.EF_BFG | q_shared.EF_ANIM_ALLFAST
	q_shared.VectorClear (bfg.mins)
	q_shared.VectorClear (bfg.maxs)
	bfg.s.modelindex = g_main.gi.modelindex ("sprites/s_bfg1.sp2")
	bfg.owner = self
	bfg.touch = bfg_touch
	bfg.nextthink = g_main.level.time + 8000/speed
	bfg.think = g_utils.G_FreeEdict
	bfg.radius_dmg = damage
	bfg.dmg_radius = damage_radius
	bfg.classname = "bfg blast"
	bfg.s.sound = g_main.gi.soundindex ("weapons/bfg__l1a.wav")

	bfg.think = bfg_think
	bfg.nextthink = g_main.level.time + FRAMETIME
	bfg.teammaster = bfg
	bfg.teamchain = None

	if self.client:
		check_dodge (self, bfg.s.origin, dir, speed)

	g_main.gi.linkentity (bfg)
