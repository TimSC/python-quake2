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
from __future__ import annotations

import random as _r
from game import q_shared
from game import g_local
from game import g_main
from game import g_utils
from game import g_items
from game import g_misc
from game import g_chase
from game import g_ai
from game import g_weapon
from game import p_trail
from game import p_view
from game import p_hud
from game import p_weapon
from game import game
from qcommon import pmove
from game.q_shared import (Q_stricmp, Info_ValueForKey, Info_SetValueForKey,
	MAX_INFO_STRING, PRINT_HIGH, PRINT_MEDIUM, CS_PLAYERSKINS,
	MASK_PLAYERSOLID, MASK_DEADSOLID, CHAN_VOICE, CHAN_BODY, ATTN_NORM,
	EV_PLAYER_TELEPORT,
	PMF_DUCKED, PMF_TIME_TELEPORT, PMF_NO_PREDICTION, PMF_JUMP_HELD,
	BUTTON_ANY,
	BUTTON_ATTACK, MZ_LOGIN, MZ_LOGOUT, ANGLE2SHORT, SHORT2ANGLE, TO_SHORT,
	DF_FIXED_FOV, DF_FORCE_RESPAWN, DF_SPAWN_FARTHEST, DF_QUAD_DROP,
	DF_MODELTEAMS, YAW, PITCH, ROLL)
from game.q_shared import multicast_t, pmtype_t
MULTICAST_PVS = multicast_t.MULTICAST_PVS.value
PM_FREEZE = pmtype_t.PM_FREEZE.value
PM_SPECTATOR = pmtype_t.PM_SPECTATOR.value
PM_GIB = pmtype_t.PM_GIB.value
PM_DEAD = pmtype_t.PM_DEAD.value
PM_NORMAL = pmtype_t.PM_NORMAL.value
from game.g_local import (FRAMETIME, BODY_QUEUE_SIZE, MOD_FRIENDLY_FIRE,
	MOD_SUICIDE, MOD_FALLING, MOD_CRUSH, MOD_WATER, MOD_SLIME, MOD_LAVA,
	MOD_EXPLOSIVE, MOD_BARREL, MOD_EXIT, MOD_TARGET_LASER, MOD_TARGET_BLASTER,
	MOD_BOMB, MOD_SPLASH, MOD_TRIGGER_HURT, MOD_HELD_GRENADE, MOD_HG_SPLASH,
	MOD_G_SPLASH, MOD_R_SPLASH, MOD_BFG_BLAST, MOD_BLASTER, MOD_SHOTGUN,
	MOD_SSHOTGUN, MOD_MACHINEGUN, MOD_CHAINGUN, MOD_GRENADE, MOD_ROCKET,
	MOD_HYPERBLASTER, MOD_RAILGUN, MOD_BFG_LASER, MOD_BFG_EFFECT,
	MOD_HANDGRENADE, MOD_TELEFRAG, IT_KEY, IT_AMMO,
	DEAD_NO, DEAD_DEAD, MOVETYPE_TOSS, MOVETYPE_WALK,
	MOVETYPE_NOCLIP, FL_NO_KNOCKBACK, FL_POWER_ARMOR, ANIM_DEATH,
	GIB_ORGANIC, PNOISE_SELF, svc_muzzleflash, svc_stufftext,
	FRAME_crdeath1, FRAME_crdeath5, FRAME_death101, FRAME_death106,
	FRAME_death201, FRAME_death206, FRAME_death301, FRAME_death308)
from game.g_local import damage_t
DAMAGE_NO = damage_t.DAMAGE_NO.value
DAMAGE_YES = damage_t.DAMAGE_YES.value
DAMAGE_AIM = damage_t.DAMAGE_AIM.value
from game.game import solid_t
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value
SVF_NOCLIENT = game.SVF_NOCLIENT
SVF_DEADMONSTER = game.SVF_DEADMONSTER

"""
#include "g_local.h"
#include "m_player.h"

void SP_misc_teleporter_dest (edict_t *ent);
"""

pm_passent = None  # edict_t *


def _SV_FilterPacket (value):
	# server-side ban list check; not wired up in the Python port
	return False


def _cvar_string (name):
	# read a cvar's string value directly from the cvar system
	from qcommon import cvar
	v = cvar.Cvar_VariableString (name)
	return v if v is not None else ""


def _cvar_value (name):
	# read a cvar's numeric value directly from the cvar system
	from qcommon import cvar
	return cvar.Cvar_VariableValue (name)


def _info_validate (userinfo):
	# simple stand-in for C Info_Validate
	return isinstance(userinfo, str)


def _copy_pmove_state (src):
	dst = q_shared.pmove_state_t()
	dst.pm_type = src.pm_type
	dst.origin = src.origin.copy()
	dst.velocity = src.velocity.copy()
	dst.pm_flags = src.pm_flags
	dst.pm_time = src.pm_time
	dst.gravity = src.gravity
	dst.delta_angles = src.delta_angles.copy()
	return dst


"""
// this function is an ugly as hell hack to fix some map flaws
"""
def SP_FixCoopSpots (self):
	#edict_t *spot
	#vec3_t d
	spot = None

	while True:
		spot = g_utils.G_Find (spot, g_utils.FOFS("classname"), "info_player_start")
		if not spot:
			return
		if not spot.targetname:
			continue
		d = self.s.origin - spot.s.origin
		if q_shared.VectorLength(d) < 384:
			if (not self.targetname) or Q_stricmp(self.targetname, spot.targetname) != 0:
				self.targetname = spot.targetname
			return


"""
// some maps don't have any coop spots at all, so we need to create them
"""
def SP_CreateCoopSpots (self):
	#edict_t *spot
	if Q_stricmp(g_main.level.mapname, "security") == 0:
		spot = g_utils.G_Spawn()
		spot.classname = "info_player_coop"
		spot.s.origin[0] = 188 - 64
		spot.s.origin[1] = -164
		spot.s.origin[2] = 80
		spot.targetname = "jail3"
		spot.s.angles[1] = 90

		spot = g_utils.G_Spawn()
		spot.classname = "info_player_coop"
		spot.s.origin[0] = 188 + 64
		spot.s.origin[1] = -164
		spot.s.origin[2] = 80
		spot.targetname = "jail3"
		spot.s.angles[1] = 90

		spot = g_utils.G_Spawn()
		spot.classname = "info_player_coop"
		spot.s.origin[0] = 188 + 128
		spot.s.origin[1] = -164
		spot.s.origin[2] = 80
		spot.targetname = "jail3"
		spot.s.angles[1] = 90


"""
/*QUAKED info_player_start (1 0 0) (-16 -16 -24) (16 16 32)
The normal starting point for a level.
*/
"""
def SP_info_player_start (self):
	if not int(g_main.coop.value):
		return
	if Q_stricmp(g_main.level.mapname, "security") == 0:
		# invoke one of our gross, ugly, disgusting hacks
		self.think = SP_CreateCoopSpots
		self.nextthink = g_main.level.time + FRAMETIME


"""
/*QUAKED info_player_deathmatch (1 0 1) (-16 -16 -24) (16 16 32)
potential spawning position for deathmatch games
*/
"""
def SP_info_player_deathmatch (self):
	if not int(g_main.deathmatch.value):
		g_utils.G_FreeEdict (self)
		return
	g_misc.SP_misc_teleporter_dest (self)


"""
/*QUAKED info_player_coop (1 0 1) (-16 -16 -24) (16 16 32)
potential spawning position for coop games
*/
"""
def SP_info_player_coop (self):
	if not int(g_main.coop.value):
		g_utils.G_FreeEdict (self)
		return

	if (Q_stricmp(g_main.level.mapname, "jail2") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "jail4") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "mine1") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "mine2") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "mine3") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "mine4") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "lab") == 0)     or \
	   (Q_stricmp(g_main.level.mapname, "boss1") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "fact3") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "biggun") == 0)  or \
	   (Q_stricmp(g_main.level.mapname, "space") == 0)   or \
	   (Q_stricmp(g_main.level.mapname, "command") == 0) or \
	   (Q_stricmp(g_main.level.mapname, "power2") == 0)  or \
	   (Q_stricmp(g_main.level.mapname, "strike") == 0):
		# invoke one of our gross, ugly, disgusting hacks
		self.think = SP_FixCoopSpots
		self.nextthink = g_main.level.time + FRAMETIME


"""
/*QUAKED info_player_intermission (1 0 1) (-16 -16 -24) (16 16 32)
The deathmatch intermission point will be at one of these
*/
"""
def SP_info_player_intermission (self):
	pass


def player_pain (self, other, kick, damage):
	# player pain is handled at the end of the frame in P_DamageFeedback
	pass


def IsFemale (ent):
	#char *info
	if not ent.client:
		return False

	info = Info_ValueForKey (ent.client.pers.userinfo, "gender")
	if info[0] == 'f' or info[0] == 'F':
		return True
	return False


def IsNeutral (ent):
	#char *info
	if not ent.client:
		return False

	info = Info_ValueForKey (ent.client.pers.userinfo, "gender")
	if info[0] != 'f' and info[0] != 'F' and info[0] != 'm' and info[0] != 'M':
		return True
	return False


def ClientObituary (self, inflictor, attacker):
	#int mod
	#char *message
	#char *message2
	#qboolean ff
	if int(g_main.coop.value) and attacker.client:
		g_main.meansOfDeath |= MOD_FRIENDLY_FIRE

	if int(g_main.deathmatch.value) or int(g_main.coop.value):
		ff = bool(g_main.meansOfDeath & MOD_FRIENDLY_FIRE)
		mod = g_main.meansOfDeath & ~MOD_FRIENDLY_FIRE
		message = None
		message2 = ""

		if mod == MOD_SUICIDE:
			message = "suicides"
		elif mod == MOD_FALLING:
			message = "cratered"
		elif mod == MOD_CRUSH:
			message = "was squished"
		elif mod == MOD_WATER:
			message = "sank like a rock"
		elif mod == MOD_SLIME:
			message = "melted"
		elif mod == MOD_LAVA:
			message = "does a back flip into the lava"
		elif mod == MOD_EXPLOSIVE or mod == MOD_BARREL:
			message = "blew up"
		elif mod == MOD_EXIT:
			message = "found a way out"
		elif mod == MOD_TARGET_LASER:
			message = "saw the light"
		elif mod == MOD_TARGET_BLASTER:
			message = "got blasted"
		elif mod == MOD_BOMB or mod == MOD_SPLASH or mod == MOD_TRIGGER_HURT:
			message = "was in the wrong place"

		if attacker == self:
			if mod == MOD_HELD_GRENADE:
				message = "tried to put the pin back in"
			elif mod == MOD_HG_SPLASH or mod == MOD_G_SPLASH:
				if IsNeutral(self):
					message = "tripped on its own grenade"
				elif IsFemale(self):
					message = "tripped on her own grenade"
				else:
					message = "tripped on his own grenade"
			elif mod == MOD_R_SPLASH:
				if IsNeutral(self):
					message = "blew itself up"
				elif IsFemale(self):
					message = "blew herself up"
				else:
					message = "blew himself up"
			elif mod == MOD_BFG_BLAST:
				message = "should have used a smaller gun"
			else:
				if IsNeutral(self):
					message = "killed itself"
				elif IsFemale(self):
					message = "killed herself"
				else:
					message = "killed himself"

		if message:
			g_main.gi.bprintf (PRINT_MEDIUM, "%s %s.\n" % (self.client.pers.netname, message))
			if int(g_main.deathmatch.value):
				self.client.resp.score -= 1
			self.enemy = None
			return

		self.enemy = attacker
		if attacker and attacker.client:
			if mod == MOD_BLASTER:
				message = "was blasted by"
			elif mod == MOD_SHOTGUN:
				message = "was gunned down by"
			elif mod == MOD_SSHOTGUN:
				message = "was blown away by"
				message2 = "'s super shotgun"
			elif mod == MOD_MACHINEGUN:
				message = "was machinegunned by"
			elif mod == MOD_CHAINGUN:
				message = "was cut in half by"
				message2 = "'s chaingun"
			elif mod == MOD_GRENADE:
				message = "was popped by"
				message2 = "'s grenade"
			elif mod == MOD_G_SPLASH:
				message = "was shredded by"
				message2 = "'s shrapnel"
			elif mod == MOD_ROCKET:
				message = "ate"
				message2 = "'s rocket"
			elif mod == MOD_R_SPLASH:
				message = "almost dodged"
				message2 = "'s rocket"
			elif mod == MOD_HYPERBLASTER:
				message = "was melted by"
				message2 = "'s hyperblaster"
			elif mod == MOD_RAILGUN:
				message = "was railed by"
			elif mod == MOD_BFG_LASER:
				message = "saw the pretty lights from"
				message2 = "'s BFG"
			elif mod == MOD_BFG_BLAST:
				message = "was disintegrated by"
				message2 = "'s BFG blast"
			elif mod == MOD_BFG_EFFECT:
				message = "couldn't hide from"
				message2 = "'s BFG"
			elif mod == MOD_HANDGRENADE:
				message = "caught"
				message2 = "'s handgrenade"
			elif mod == MOD_HG_SPLASH:
				message = "didn't see"
				message2 = "'s handgrenade"
			elif mod == MOD_HELD_GRENADE:
				message = "feels"
				message2 = "'s pain"
			elif mod == MOD_TELEFRAG:
				message = "tried to invade"
				message2 = "'s personal space"
			else:
				message = None

			if message:
				g_main.gi.bprintf (PRINT_MEDIUM, "%s %s %s%s\n" % (
					self.client.pers.netname, message, attacker.client.pers.netname, message2))
				if int(g_main.deathmatch.value):
					if ff:
						attacker.client.resp.score -= 1
					else:
						attacker.client.resp.score += 1
				return

	g_main.gi.bprintf (PRINT_MEDIUM, "%s died.\n" % self.client.pers.netname)
	if int(g_main.deathmatch.value):
		self.client.resp.score -= 1


def TossClientWeapon (self):
	#gitem_t *item
	#edict_t *drop
	#qboolean quad
	#float spread
	if not int(g_main.deathmatch.value):
		return

	item = self.client.pers.weapon
	if not self.client.pers.inventory[self.client.ammo_index]:
		item = None
	if item and item.pickup_name == "Blaster":
		item = None

	if not (int(g_main.dmflags.value) & DF_QUAD_DROP):
		quad = False
	else:
		quad = (self.client.quad_framenum > (g_main.level.framenum + 10))

	if item and quad:
		spread = 22.5
	else:
		spread = 0.0

	if item:
		self.client.v_angle[YAW] -= spread
		drop = g_items.Drop_Item (self, item)
		self.client.v_angle[YAW] += spread
		drop.spawnflags = g_local.DROPPED_PLAYER_ITEM

	if quad:
		self.client.v_angle[YAW] += spread
		drop = g_items.Drop_Item (self, g_items.FindItemByClassname ("item_quad"))
		self.client.v_angle[YAW] -= spread
		drop.spawnflags |= g_local.DROPPED_PLAYER_ITEM

		drop.touch = g_items.Touch_Item
		drop.nextthink = g_main.level.time + (self.client.quad_framenum - g_main.level.framenum) * FRAMETIME
		drop.think = g_utils.G_FreeEdict


def LookAtKiller (self, inflictor, attacker):
	#vec3_t dir
	if attacker and attacker is not g_main.g_edicts[0] and attacker is not self:
		dir_ = attacker.s.origin - self.s.origin
	elif inflictor and inflictor is not g_main.g_edicts[0] and inflictor is not self:
		dir_ = inflictor.s.origin - self.s.origin
	else:
		self.client.killer_yaw = self.s.angles[YAW]
		return

	import math
	if dir_[0]:
		self.client.killer_yaw = 180.0 / math.pi * math.atan2(dir_[1], dir_[0])
	else:
		self.client.killer_yaw = 0
		if dir_[1] > 0:
			self.client.killer_yaw = 90
		elif dir_[1] < 0:
			self.client.killer_yaw = -90
	if self.client.killer_yaw < 0:
		self.client.killer_yaw += 360


def player_die (self, inflictor, attacker, damage, point):
	#int n
	q_shared.VectorClear (self.avelocity)

	self.takedamage = DAMAGE_YES
	self.movetype = MOVETYPE_TOSS

	self.s.modelindex2 = 0	# remove linked weapon model

	self.s.angles[0] = 0
	self.s.angles[2] = 0

	self.s.sound = 0
	self.client.weapon_sound = 0

	self.maxs[2] = -8

	self.svflags |= SVF_DEADMONSTER

	if not self.deadflag:
		self.client.respawn_time = g_main.level.time + 1.0
		LookAtKiller (self, inflictor, attacker)
		self.client.ps.pmove.pm_type = PM_DEAD
		ClientObituary (self, inflictor, attacker)
		TossClientWeapon (self)
		if int(g_main.deathmatch.value):
			p_hud.Cmd_Help_f (self)	# show scores

		# clear inventory
		# this is kind of ugly, but it's how we want to handle keys in coop
		for n in range(g_main.game.num_items):
			if int(g_main.coop.value) and g_items.itemlist[n].flags & IT_KEY:
				self.client.resp.coop_respawn.inventory[n] = self.client.pers.inventory[n]
			self.client.pers.inventory[n] = 0

	# remove powerups
	self.client.quad_framenum = 0
	self.client.invincible_framenum = 0
	self.client.breather_framenum = 0
	self.client.enviro_framenum = 0
	self.flags &= ~FL_POWER_ARMOR

	if self.health < -40:
		# gib
		g_main.gi.sound (self, CHAN_BODY, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(4):
			g_misc.ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		g_misc.ThrowClientHead (self, damage)

		self.takedamage = DAMAGE_NO
	else:
		# normal death
		if not self.deadflag:
			global _death_anim_i
			_death_anim_i = (_death_anim_i + 1) % 3
			# start a death animation
			self.client.anim_priority = ANIM_DEATH
			if self.client.ps.pmove.pm_flags & PMF_DUCKED:
				self.s.frame = FRAME_crdeath1-1
				self.client.anim_end = FRAME_crdeath5
			elif _death_anim_i == 0:
				self.s.frame = FRAME_death101-1
				self.client.anim_end = FRAME_death106
			elif _death_anim_i == 1:
				self.s.frame = FRAME_death201-1
				self.client.anim_end = FRAME_death206
			else:
				self.s.frame = FRAME_death301-1
				self.client.anim_end = FRAME_death308
			g_main.gi.sound (self, CHAN_VOICE, g_main.gi.soundindex("*death%d.wav" % (_r.randint(0, 3)+1)), 1, ATTN_NORM, 0)

	self.deadflag = DEAD_DEAD

	g_main.gi.linkentity (self)


_death_anim_i = 0


def InitClientPersistant (client):
	#gitem_t *item
	client.pers = g_local.client_persistant_t()

	item = g_items.FindItem("Blaster")
	client.pers.selected_item = g_items.ITEM_INDEX(item)
	client.pers.inventory[client.pers.selected_item] = 1

	client.pers.weapon = item

	client.pers.health = 100
	client.pers.max_health = 100

	client.pers.max_bullets = 200
	client.pers.max_shells = 100
	client.pers.max_rockets = 50
	client.pers.max_grenades = 50
	client.pers.max_cells = 200
	client.pers.max_slugs = 50

	client.pers.connected = True


def InitClientResp (client):
	client.resp = g_local.client_respawn_t()
	client.resp.enterframe = g_main.level.framenum
	client.resp.coop_respawn = g_local.client_persistant_t()
	q_shared.VectorCopy(client.pers.cmd_angles, client.resp.cmd_angles) if False else None
	client.resp.coop_respawn = client.pers


def SaveClientData ():
	#int i
	#edict_t *ent
	for i in range(int(g_main.game.maxclients)):
		ent = g_main.g_edicts[1+i]
		if not ent.inuse:
			continue
		g_main.game.clients[i].pers.health = ent.health
		g_main.game.clients[i].pers.max_health = ent.max_health
		g_main.game.clients[i].pers.savedFlags = (ent.flags & (g_local.FL_GODMODE | g_local.FL_NOTARGET | FL_POWER_ARMOR))
		if int(g_main.coop.value):
			g_main.game.clients[i].pers.score = ent.client.resp.score


def FetchClientEntData (ent):
	ent.health = ent.client.pers.health
	ent.max_health = ent.client.pers.max_health
	ent.flags |= ent.client.pers.savedFlags
	if int(g_main.coop.value):
		ent.client.resp.score = ent.client.pers.score


def PlayersRangeFromSpot (spot):
	#edict_t *player
	#float bestplayerdistance
	#vec3_t v
	#int n
	#float playerdistance
	bestplayerdistance = 9999999

	for n in range(1, int(g_main.maxclients.value)+1):
		player = g_main.g_edicts[n]

		if not player.inuse:
			continue

		if player.health <= 0:
			continue

		v = spot.s.origin - player.s.origin
		playerdistance = q_shared.VectorLength (v)

		if playerdistance < bestplayerdistance:
			bestplayerdistance = playerdistance

	return bestplayerdistance


def SelectRandomDeathmatchSpawnPoint ():
	#edict_t *spot, *spot1, *spot2
	#int count
	#int selection
	#float range, range1, range2
	spot = None
	range1 = range2 = 99999
	spot1 = spot2 = None
	count = 0

	while True:
		spot = g_utils.G_Find (spot, g_utils.FOFS("classname"), "info_player_deathmatch")
		if not spot:
			break
		count += 1
		range_ = PlayersRangeFromSpot(spot)
		if range_ < range1:
			range1 = range_
			spot1 = spot
		elif range_ < range2:
			range2 = range_
			spot2 = spot

	if not count:
		return None

	if count <= 2:
		spot1 = spot2 = None
	else:
		count -= 2

	selection = _r.randint(0, 2147483647) % count

	spot = None
	while True:
		spot = g_utils.G_Find (spot, g_utils.FOFS("classname"), "info_player_deathmatch")
		if spot is spot1 or spot is spot2:
			selection += 1
		selection -= 1
		if selection <= 0:
			break

	return spot


def SelectFarthestDeathmatchSpawnPoint ():
	#edict_t *bestspot
	#float bestdistance, bestplayerdistance
	#edict_t *spot
	spot = None
	bestspot = None
	bestdistance = 0
	while True:
		spot = g_utils.G_Find (spot, g_utils.FOFS("classname"), "info_player_deathmatch")
		if not spot:
			break
		bestplayerdistance = PlayersRangeFromSpot (spot)

		if bestplayerdistance > bestdistance:
			bestspot = spot
			bestdistance = bestplayerdistance

	if bestspot:
		return bestspot

	# if there is a player just spawned on each and every start spot
	# we have no choice to turn one into a telefrag meltdown
	spot = g_utils.G_Find (None, g_utils.FOFS("classname"), "info_player_deathmatch")

	return spot


def SelectDeathmatchSpawnPoint ():
	if (int(g_main.dmflags.value) & DF_SPAWN_FARTHEST):
		return SelectFarthestDeathmatchSpawnPoint ()
	else:
		return SelectRandomDeathmatchSpawnPoint ()


def SelectCoopSpawnPoint (ent):
	#int index
	#edict_t *spot
	#char *target
	index = g_main.g_edicts.index(ent) - 1

	# player 0 starts in normal player spawn point
	if not index:
		return None

	spot = None

	# assume there are four coop spots at each spawnpoint
	while True:
		spot = g_utils.G_Find (spot, g_utils.FOFS("classname"), "info_player_coop")
		if not spot:
			return None	# we didn't have enough...

		target = spot.targetname
		if not target:
			target = ""
		if Q_stricmp(g_main.game.spawnpoint, target) == 0:
			# this is a coop spawn point for one of the clients here
			index -= 1
			if not index:
				return spot		# this is it


def SelectSpawnPoint (ent, origin, angles):
	#edict_t *spot
	spot = None

	if int(g_main.deathmatch.value):
		spot = SelectDeathmatchSpawnPoint ()
	elif int(g_main.coop.value):
		spot = SelectCoopSpawnPoint (ent)

	# find a single player start spot
	if not spot:
		while True:
			spot = g_utils.G_Find (spot, g_utils.FOFS("classname"), "info_player_start")
			if not spot:
				break
			if not g_main.game.spawnpoint and not spot.targetname:
				break

			if not g_main.game.spawnpoint or not spot.targetname:
				continue

			if Q_stricmp(g_main.game.spawnpoint, spot.targetname) == 0:
				break

		if not spot:
			if not g_main.game.spawnpoint:
				# there wasn't a spawnpoint without a target, so use any
				spot = g_utils.G_Find (None, g_utils.FOFS("classname"), "info_player_start")
			if not spot:
				g_main.gi.error ("Couldn't find spawn point %s\n" % g_main.game.spawnpoint)

	q_shared.VectorCopy (spot.s.origin, origin)
	origin[2] += 9
	q_shared.VectorCopy (spot.s.angles, angles)


def InitBodyQue ():
	#int i
	#edict_t *ent
	g_main.level.body_que = 0
	for i in range(BODY_QUEUE_SIZE):
		ent = g_utils.G_Spawn()
		ent.classname = "bodyque"


def body_die (self, inflictor, attacker, damage, point):
	#int n
	if self.health < -40:
		g_main.gi.sound (self, CHAN_BODY, g_main.gi.soundindex ("misc/udeath.wav"), 1, ATTN_NORM, 0)
		for n in range(4):
			g_misc.ThrowGib (self, "models/objects/gibs/sm_meat/tris.md2", damage, GIB_ORGANIC)
		self.s.origin[2] -= 48
		g_misc.ThrowClientHead (self, damage)
		self.takedamage = DAMAGE_NO


def CopyToBodyQue (ent):
	#edict_t *body
	# grab a body que and cycle to the next one
	body = g_main.g_edicts[int(g_main.maxclients.value) + g_main.level.body_que + 1]
	g_main.level.body_que = (g_main.level.body_que + 1) % BODY_QUEUE_SIZE

	g_main.gi.unlinkentity (ent)

	g_main.gi.unlinkentity (body)
	body.s = ent.s
	body.s.number = g_main.g_edicts.index(body)

	body.svflags = ent.svflags
	q_shared.VectorCopy (ent.mins, body.mins)
	q_shared.VectorCopy (ent.maxs, body.maxs)
	q_shared.VectorCopy (ent.absmin, body.absmin)
	q_shared.VectorCopy (ent.absmax, body.absmax)
	q_shared.VectorCopy (ent.size, body.size)
	body.solid = ent.solid
	body.clipmask = ent.clipmask
	body.owner = ent.owner
	body.movetype = ent.movetype

	body.die = body_die
	body.takedamage = DAMAGE_YES

	g_main.gi.linkentity (body)


def respawn (self):
	if int(g_main.deathmatch.value) or int(g_main.coop.value):
		# spectator's don't leave bodies
		if self.movetype != MOVETYPE_NOCLIP:
			CopyToBodyQue (self)
		self.svflags &= ~SVF_NOCLIENT
		PutClientInServer (self)

		# add a teleportation effect
		self.s.event = EV_PLAYER_TELEPORT

		# hold in place briefly
		self.client.ps.pmove.pm_flags = PMF_TIME_TELEPORT
		self.client.ps.pmove.pm_time = 14

		self.client.respawn_time = g_main.level.time

		return

	# restart the entire server
	g_main.gi.AddCommandString ("menu_loadgame\n")


def spectator_respawn (ent):
	#int i, numspec
	# if the user wants to become a spectator, make sure he doesn't
	# exceed max_spectators
	if ent.client.pers.spectator:
		value = Info_ValueForKey (ent.client.pers.userinfo, "spectator")
		_spec_pw = _cvar_string ("spectator_password")
		if _spec_pw and _spec_pw != "none" and _spec_pw != value:
			g_main.gi.cprintf(ent, PRINT_HIGH, "Spectator password incorrect.\n")
			ent.client.pers.spectator = False
			g_main.gi.WriteByte (svc_stufftext)
			g_main.gi.WriteString ("spectator 0\n")
			g_main.gi.unicast(ent, True)
			return

		# count spectators
		numspec = 0
		for i in range(1, int(g_main.maxclients.value)+1):
			if g_main.g_edicts[i].inuse and g_main.g_edicts[i].client.pers.spectator:
				numspec += 1

		if numspec >= int(_cvar_value ("maxspectators")):
			g_main.gi.cprintf(ent, PRINT_HIGH, "Server spectator limit is full.")
			ent.client.pers.spectator = False
			# reset his spectator var
			g_main.gi.WriteByte (svc_stufftext)
			g_main.gi.WriteString ("spectator 0\n")
			g_main.gi.unicast(ent, True)
			return
	else:
		# he was a spectator and wants to join the game
		# he must have the right password
		value = Info_ValueForKey (ent.client.pers.userinfo, "password")
		_pw = _cvar_string ("password")
		if _pw and _pw != "none" and _pw != value:
			g_main.gi.cprintf(ent, PRINT_HIGH, "Password incorrect.\n")
			ent.client.pers.spectator = True
			g_main.gi.WriteByte (svc_stufftext)
			g_main.gi.WriteString ("spectator 1\n")
			g_main.gi.unicast(ent, True)
			return

	# clear client on respawn
	ent.client.resp.score = ent.client.pers.score = 0

	ent.svflags &= ~SVF_NOCLIENT
	PutClientInServer (ent)

	# add a teleportation effect
	if not ent.client.pers.spectator:
		# send effect
		g_main.gi.WriteByte (svc_muzzleflash)
		g_main.gi.WriteShort (g_main.g_edicts.index(ent))
		g_main.gi.WriteByte (MZ_LOGIN)
		g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

		# hold in place briefly
		ent.client.ps.pmove.pm_flags = PMF_TIME_TELEPORT
		ent.client.ps.pmove.pm_time = 14

	ent.client.respawn_time = g_main.level.time

	if ent.client.pers.spectator:
		g_main.gi.bprintf (PRINT_HIGH, "%s has moved to the sidelines\n" % ent.client.pers.netname)
	else:
		g_main.gi.bprintf (PRINT_HIGH, "%s joined the game\n" % ent.client.pers.netname)


def PutClientInServer (ent):
	#vec3_t spawn_origin, spawn_angles
	#client_persistant_t saved
	#client_respawn_t resp
	mins = np.zeros((3,), dtype=np.float32)
	mins[:] = [-16, -16, -24]
	maxs = np.zeros((3,), dtype=np.float32)
	maxs[:] = [16, 16, 32]
	spawn_origin = np.zeros((3,), dtype=np.float32)
	spawn_angles = np.zeros((3,), dtype=np.float32)

	# find a spawn point
	# do it before setting health back up, so farthest
	# ranging doesn't count this client
	SelectSpawnPoint (ent, spawn_origin, spawn_angles)

	index = g_main.g_edicts.index(ent) - 1
	client = ent.client

	# deathmatch wipes most client data every spawn
	if int(g_main.deathmatch.value):
		userinfo = client.pers.userinfo
		resp = client.resp
		InitClientPersistant (client)
		ClientUserinfoChanged (ent, userinfo)
	elif int(g_main.coop.value):
		userinfo = client.pers.userinfo
		resp = client.resp
		resp.coop_respawn.game_helpchanged = client.pers.game_helpchanged
		resp.coop_respawn.helpchanged = client.pers.helpchanged
		client.pers = resp.coop_respawn
		ClientUserinfoChanged (ent, userinfo)
		if resp.score > client.pers.score:
			client.pers.score = resp.score
	else:
		resp = g_local.client_respawn_t()

	# clear everything but the persistant data
	saved = client.pers
	client.clear() # memset (client, 0, sizeof(*client));
	client.pers = saved
	if client.pers.health <= 0:
		InitClientPersistant(client)
	client.resp = resp

	# copy some data from the client to the entity
	FetchClientEntData (ent)

	# clear entity values
	ent.groundentity = None
	ent.client = g_main.game.clients[index]
	ent.takedamage = DAMAGE_AIM
	ent.movetype = MOVETYPE_WALK
	ent.viewheight = 22
	ent.inuse = True
	ent.classname = "player"
	ent.mass = 200
	ent.solid = SOLID_BBOX
	ent.deadflag = DEAD_NO
	ent.air_finished = g_main.level.time + 12
	ent.clipmask = MASK_PLAYERSOLID
	ent.model = "players/male/tris.md2"
	ent.pain = player_pain
	ent.die = player_die
	ent.waterlevel = 0
	ent.watertype = 0
	ent.flags &= ~FL_NO_KNOCKBACK
	ent.svflags &= ~SVF_DEADMONSTER

	q_shared.VectorCopy (mins, ent.mins)
	q_shared.VectorCopy (maxs, ent.maxs)
	q_shared.VectorClear (ent.velocity)

	# clear playerstate values
	client.ps = q_shared.player_state_t()
	client = ent.client

	client.ps.pmove.origin[0] = int(spawn_origin[0]*8)
	client.ps.pmove.origin[1] = int(spawn_origin[1]*8)
	client.ps.pmove.origin[2] = int(spawn_origin[2]*8)

	if int(g_main.deathmatch.value) and (int(g_main.dmflags.value) & DF_FIXED_FOV):
		client.ps.fov = 90
	else:
		client.ps.fov = q_shared.atoi(Info_ValueForKey(client.pers.userinfo, "fov"))
		if client.ps.fov < 1:
			client.ps.fov = 90
		elif client.ps.fov > 160:
			client.ps.fov = 160

	client.ps.gunindex = g_main.gi.modelindex(client.pers.weapon.view_model)

	# clear entity state values
	ent.s.effects = 0
	ent.s.modelindex = 255		# will use the skin specified model
	ent.s.modelindex2 = 255		# custom gun model
	# sknum is player num and weapon number
	# weapon number will be added in changeweapon
	ent.s.skinnum = g_main.g_edicts.index(ent) - 1

	ent.s.frame = 0
	q_shared.VectorCopy (spawn_origin, ent.s.origin)
	ent.s.origin[2] += 1	# make sure off ground
	q_shared.VectorCopy (ent.s.origin, ent.s.old_origin)

	# set the delta angle
	for i in range(3):
		client.ps.pmove.delta_angles[i] = TO_SHORT(ANGLE2SHORT(spawn_angles[i] - client.resp.cmd_angles[i]))

	ent.s.angles[PITCH] = 0
	ent.s.angles[YAW] = spawn_angles[YAW]
	ent.s.angles[ROLL] = 0
	q_shared.VectorCopy (ent.s.angles, client.ps.viewangles)
	q_shared.VectorCopy (ent.s.angles, client.v_angle)

	# spawn a spectator
	if client.pers.spectator:
		client.chase_target = None

		client.resp.spectator = True

		ent.movetype = MOVETYPE_NOCLIP
		ent.solid = SOLID_NOT
		ent.svflags |= SVF_NOCLIENT
		ent.client.ps.gunindex = 0
		g_main.gi.linkentity (ent)
		return
	else:
		client.resp.spectator = False

	if not g_utils.KillBox (ent):
		pass	# couldn't spawn in?

	g_main.gi.linkentity (ent)

	# force the current weapon up
	client.newweapon = client.pers.weapon
	p_weapon.ChangeWeapon (ent)


def ClientBeginDeathmatch (ent):
	g_utils.G_InitEdict (ent)

	InitClientResp (ent.client)

	# locate ent at a spawn point
	PutClientInServer (ent)

	if g_main.level.intermissiontime:
		p_hud.MoveClientToIntermission (ent)
	else:
		# send effect
		g_main.gi.WriteByte (svc_muzzleflash)
		g_main.gi.WriteShort (g_main.g_edicts.index(ent))
		g_main.gi.WriteByte (MZ_LOGIN)
		g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	g_main.gi.bprintf (PRINT_HIGH, "%s entered the game\n" % ent.client.pers.netname)

	# make sure all view stuff is valid
	p_view.ClientEndServerFrame (ent)


def ClientBegin (ent):
	#int i
	ent.client = g_main.game.clients[g_main.g_edicts.index(ent) - 1]

	if int(g_main.deathmatch.value):
		ClientBeginDeathmatch (ent)
		return

	# if there is already a body waiting for us (a loadgame), just
	# take it, otherwise spawn one from scratch
	if ent.inuse == True:
		# the client has cleared the client side viewangles upon
		# connecting to the server, which is different than the
		# state when the game is saved, so we need to compensate
		# with deltaangles
		for i in range(3):
			ent.client.ps.pmove.delta_angles[i] = TO_SHORT(ANGLE2SHORT(ent.client.ps.viewangles[i]))
	else:
		# a spawn point will completely reinitialize the entity
		# except for the persistant data that was initialized at
		# ClientConnect() time
		g_utils.G_InitEdict (ent)
		ent.classname = "player"
		InitClientResp (ent.client)
		PutClientInServer (ent)

	if g_main.level.intermissiontime:
		p_hud.MoveClientToIntermission (ent)
	else:
		# send effect if in a multiplayer game
		if g_main.game.maxclients > 1:
			g_main.gi.WriteByte (svc_muzzleflash)
			g_main.gi.WriteShort (g_main.g_edicts.index(ent))
			g_main.gi.WriteByte (MZ_LOGIN)
			g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

			g_main.gi.bprintf (PRINT_HIGH, "%s entered the game\n" % ent.client.pers.netname)

	# make sure all view stuff is valid
	p_view.ClientEndServerFrame (ent)


def ClientUserinfoChanged (ent, userinfo):
	#int playernum
	# check for malformed or illegal info strings
	if not _info_validate(userinfo):
		userinfo = "\\name\\badinfo\\skin\\male/grunt"

	# set name
	s = Info_ValueForKey (userinfo, "name")
	ent.client.pers.netname = s

	# set spectator
	s = Info_ValueForKey (userinfo, "spectator")
	# spectators are only supported in deathmatch
	if int(g_main.deathmatch.value) and s and s != "0":
		ent.client.pers.spectator = True
	else:
		ent.client.pers.spectator = False

	# set skin
	s = Info_ValueForKey (userinfo, "skin")

	playernum = g_main.g_edicts.index(ent) - 1

	# combine name and skin into a configstring
	g_main.gi.configstring (CS_PLAYERSKINS+playernum, "%s\\%s" % (ent.client.pers.netname, s))

	# fov
	if int(g_main.deathmatch.value) and (int(g_main.dmflags.value) & DF_FIXED_FOV):
		ent.client.ps.fov = 90
	else:
		ent.client.ps.fov = q_shared.atoi(Info_ValueForKey(userinfo, "fov"))
		if ent.client.ps.fov < 1:
			ent.client.ps.fov = 90
		elif ent.client.ps.fov > 160:
			ent.client.ps.fov = 160

	# handedness
	s = Info_ValueForKey (userinfo, "hand")
	if len(s):
		ent.client.pers.hand = int(s)

	# save off the userinfo in case we want to check something later
	ent.client.pers.userinfo = userinfo


def ClientConnect (ent, userinfo):
	#char *value
	# check to see if they are on the banned IP list
	value = Info_ValueForKey (userinfo, "ip")
	if _SV_FilterPacket(value):
		userinfo += r"\rejmsg\Banned."
		return False

	# check for a spectator
	value = Info_ValueForKey (userinfo, "spectator")
	if int(g_main.deathmatch.value) and value and value != "0":
		numspec = 0
		_spec_pw = _cvar_string ("spectator_password")
		if _spec_pw and _spec_pw != "none" and _spec_pw != value:
			userinfo += r"\rejmsg\Spectator password required or incorrect."
			return False

		# count spectators
		for i in range(int(g_main.maxclients.value)):
			if g_main.g_edicts[i+1].inuse and g_main.g_edicts[i+1].client.pers.spectator:
				numspec += 1

		if numspec >= int(_cvar_value ("maxspectators")):
			userinfo += r"\rejmsg\Server spectator limit is full."
			return False
	else:
		# check for a password
		value = Info_ValueForKey (userinfo, "password")
		_pw = _cvar_string ("password")
		if _pw and _pw != "none" and _pw != value:
			userinfo += r"\rejmsg\Password required or incorrect."
			return False

	# they can connect
	ent.client = g_main.game.clients[g_main.g_edicts.index(ent) - 1]

	# if there is already a body waiting for us (a loadgame), just
	# take it, otherwise spawn one from scratch
	if ent.inuse == False:
		# clear the respawning variables
		InitClientResp (ent.client)
		if not g_main.game.autosaved or not ent.client.pers.weapon:
			InitClientPersistant (ent.client)

	ClientUserinfoChanged (ent, userinfo)

	if g_main.game.maxclients > 1:
		g_main.gi.dprintf ("%s connected\n" % ent.client.pers.netname)

	ent.svflags = 0 # make sure we start with known default
	ent.client.pers.connected = True
	return True


def ClientDisconnect (ent):
	#int playernum
	if not ent.client:
		return

	g_main.gi.bprintf (PRINT_HIGH, "%s disconnected\n" % ent.client.pers.netname)

	# send effect
	g_main.gi.WriteByte (svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (MZ_LOGOUT)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	g_main.gi.unlinkentity (ent)
	ent.s.modelindex = 0
	ent.solid = SOLID_NOT
	ent.inuse = False
	ent.classname = "disconnected"
	ent.client.pers.connected = False

	playernum = g_main.g_edicts.index(ent) - 1
	g_main.gi.configstring (CS_PLAYERSKINS+playernum, "")


def PM_trace (start, mins, maxs, end):
	if pm_passent.health > 0:
		return g_main.gi.trace (start, mins, maxs, end, pm_passent, MASK_PLAYERSOLID)
	else:
		return g_main.gi.trace (start, mins, maxs, end, pm_passent, MASK_DEADSOLID)


def ClientThink (ent, ucmd):
	global pm_passent
	#edict_t *other
	#int i, j
	client = ent.client

	g_main.level.current_entity = ent
	client = ent.client

	if g_main.level.intermissiontime:
		client.ps.pmove.pm_type = PM_FREEZE
		# can exit intermission after five seconds
		if g_main.level.time > g_main.level.intermissiontime + 5.0 \
			and (ucmd.buttons & BUTTON_ANY):
			g_main.level.exitintermission = True
		return

	pm_passent = ent

	if ent.client.chase_target:
		client.resp.cmd_angles[0] = SHORT2ANGLE(ucmd.angles[0])
		client.resp.cmd_angles[1] = SHORT2ANGLE(ucmd.angles[1])
		client.resp.cmd_angles[2] = SHORT2ANGLE(ucmd.angles[2])
	else:
		# set up for pmove
		pm = pmove.pmove_t()

		if ent.movetype == MOVETYPE_NOCLIP:
			client.ps.pmove.pm_type = PM_SPECTATOR
		elif ent.s.modelindex != 255:
			client.ps.pmove.pm_type = PM_GIB
		elif ent.deadflag:
			client.ps.pmove.pm_type = PM_DEAD
		else:
			client.ps.pmove.pm_type = PM_NORMAL

		client.ps.pmove.gravity = g_main.sv_gravity.value
		pm.s = client.ps.pmove

		for i in range(3):
			pm.s.origin[i] = int(ent.s.origin[i]*8)
			pm.s.velocity[i] = int(ent.velocity[i]*8)

		# memcmp(&client->old_pmove, &pm.s, sizeof(pm.s))
		if (list(pm.s.origin) != list(client.old_pmove.origin)) or \
		   (list(pm.s.velocity) != list(client.old_pmove.velocity)) or \
		   (pm.s.pm_flags != client.old_pmove.pm_flags) or \
		   (pm.s.pm_time != client.old_pmove.pm_time) or \
		   (pm.s.pm_type != client.old_pmove.pm_type) or \
		   (pm.s.gravity != client.old_pmove.gravity):
			pm.snapinitial = True

		pm.cmd = ucmd

		pm.trace = PM_trace	# adds default parms
		pm.pointcontents = g_main.gi.pointcontents

		# perform a pmove
		pmove.Pmove(pm)

		# save results of pmove
		client.ps.pmove = pm.s
		client.old_pmove = _copy_pmove_state(pm.s)

		for i in range(3):
			ent.s.origin[i] = pm.s.origin[i]*0.125
			ent.velocity[i] = pm.s.velocity[i]*0.125

		q_shared.VectorCopy (pm.mins, ent.mins)
		q_shared.VectorCopy (pm.maxs, ent.maxs)

		client.resp.cmd_angles[0] = SHORT2ANGLE(ucmd.angles[0])
		client.resp.cmd_angles[1] = SHORT2ANGLE(ucmd.angles[1])
		client.resp.cmd_angles[2] = SHORT2ANGLE(ucmd.angles[2])

		if ent.groundentity and not pm.groundentity and (pm.cmd.upmove >= 10) and (pm.waterlevel == 0):
			g_main.gi.sound(ent, CHAN_VOICE, g_main.gi.soundindex("*jump1.wav"), 1, ATTN_NORM, 0)
			p_weapon.PlayerNoise(ent, ent.s.origin, PNOISE_SELF)

		ent.viewheight = pm.viewheight
		ent.waterlevel = pm.waterlevel
		ent.watertype = pm.watertype
		ent.groundentity = pm.groundentity
		if pm.groundentity:
			ent.groundentity_linkcount = pm.groundentity.linkcount

		if ent.deadflag:
			client.ps.viewangles[ROLL] = 40
			client.ps.viewangles[PITCH] = -15
			client.ps.viewangles[YAW] = client.killer_yaw
		else:
			q_shared.VectorCopy (pm.viewangles, client.v_angle)
			q_shared.VectorCopy (pm.viewangles, client.ps.viewangles)

		g_main.gi.linkentity (ent)

		if ent.movetype != MOVETYPE_NOCLIP:
			g_utils.G_TouchTriggers (ent)

		# touch other objects
		for i in range(pm.numtouch):
			other = pm.touchents[i]
			j = 0
			while j < i:
				if pm.touchents[j] == other:
					break
				j += 1
			if j != i:
				continue	# duplicated
			if not other.touch:
				continue
			other.touch (other, ent, None, None)

	client.oldbuttons = client.buttons
	client.buttons = ucmd.buttons
	client.latched_buttons |= client.buttons & ~client.oldbuttons

	# save light level the player is standing on for
	# monster sighting AI
	ent.light_level = ucmd.lightlevel

	# fire weapon from final position if needed
	if client.latched_buttons & BUTTON_ATTACK:
		if client.resp.spectator:
			client.latched_buttons = 0

			if client.chase_target:
				client.chase_target = None
				client.ps.pmove.pm_flags &= ~PMF_NO_PREDICTION
			else:
				g_chase.GetChaseTarget(ent)
		elif not client.weapon_thunk:
			client.weapon_thunk = True
			p_weapon.Think_Weapon (ent)

	if client.resp.spectator:
		if ucmd.upmove >= 10:
			if not (client.ps.pmove.pm_flags & PMF_JUMP_HELD):
				client.ps.pmove.pm_flags |= PMF_JUMP_HELD
				if client.chase_target:
					g_chase.ChaseNext(ent)
				else:
					g_chase.GetChaseTarget(ent)
		else:
			client.ps.pmove.pm_flags &= ~PMF_JUMP_HELD

	# update chase cam if being followed
	for i in range(1, int(g_main.maxclients.value)+1):
		other = g_main.g_edicts[i]
		if other.inuse and other.client.chase_target == ent:
			g_chase.UpdateChaseCam(other)


def ClientBeginServerFrame (ent):
	#int buttonMask
	client = ent.client

	if g_main.level.intermissiontime:
		return

	client = ent.client

	if int(g_main.deathmatch.value) and \
		client.pers.spectator != client.resp.spectator and \
		(g_main.level.time - client.respawn_time) >= 5:
		spectator_respawn(ent)
		return

	# run weapon animations if it hasn't been done by a ucmd_t
	if not client.weapon_thunk and not client.resp.spectator:
		p_weapon.Think_Weapon (ent)
	else:
		client.weapon_thunk = False

	if ent.deadflag:
		# wait for any button just going down
		if g_main.level.time > client.respawn_time:
			# in deathmatch, only wait for attack button
			if int(g_main.deathmatch.value):
				buttonMask = BUTTON_ATTACK
			else:
				buttonMask = -1

			if (client.latched_buttons & buttonMask) or \
				(int(g_main.deathmatch.value) and (int(g_main.dmflags.value) & DF_FORCE_RESPAWN)):
				respawn(ent)
				client.latched_buttons = 0
		return

	# add player trail so monsters can follow
	if not int(g_main.deathmatch.value):
		if not g_ai.visible (ent, p_trail.PlayerTrail_LastSpot()):
			p_trail.PlayerTrail_Add (ent.s.old_origin)

	client.latched_buttons = 0


# numpy import used above
import numpy as np
