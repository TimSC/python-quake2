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
from game import g_combat
from game import g_cmds
from game import g_weapon
from game import p_weapon
from game.game import solid_t
from game.g_local import (gitem_t, gitem_armor_t, ARMOR_JACKET, ARMOR_COMBAT,
	ARMOR_BODY, ARMOR_SHARD, IT_WEAPON, IT_AMMO, IT_ARMOR, IT_STAY_COOP,
	IT_KEY, IT_POWERUP, DROPPED_ITEM, DROPPED_PLAYER_ITEM, ITEM_TRIGGER_SPAWN,
	ITEM_NO_TOUCH, ITEM_TARGETS_USED, POWER_ARMOR_NONE, POWER_ARMOR_SHIELD,
	POWER_ARMOR_SCREEN)
from game.g_local import ammo_t
AMMO_BULLETS  = ammo_t.AMMO_BULLETS.value
AMMO_SHELLS   = ammo_t.AMMO_SHELLS.value
AMMO_ROCKETS  = ammo_t.AMMO_ROCKETS.value
AMMO_GRENADES = ammo_t.AMMO_GRENADES.value
AMMO_CELLS    = ammo_t.AMMO_CELLS.value
AMMO_SLUGS    = ammo_t.AMMO_SLUGS.value
from game.q_shared import (Q_stricmp, EF_ROTATE, RF_GLOW, CHAN_ITEM, CHAN_AUTO,
	ATTN_NORM, PRINT_HIGH, CS_ITEMS, STAT_PICKUP_ICON, STAT_PICKUP_STRING,
	STAT_SELECTED_ITEM, MASK_SOLID, CONTENTS_SOLID, MAX_QPATH, EV_ITEM_RESPAWN)
from game.g_local import (MOVETYPE_TOSS, FL_RESPAWN, FL_POWER_ARMOR,
	FL_TEAMSLAVE, FRAMETIME)
from game.game import SVF_NOCLIENT

SOLID_TRIGGER = solid_t.SOLID_TRIGGER.value
SOLID_BBOX = solid_t.SOLID_BBOX.value
SOLID_NOT = solid_t.SOLID_NOT.value

"""
// g_items.c

#include "g_local.h"

// health, armor and powerup items
// these are defined in g_cmds.c (for use) and here (for pickup)

#define	HEALTH_IGNORE_MAX	1
#define	HEALTH_TIMED		2
"""
HEALTH_IGNORE_MAX = 1
HEALTH_TIMED = 2

#
# armor info
#
jacketarmor_info = gitem_armor_t()
jacketarmor_info.base_count = 25
jacketarmor_info.max_count = 50
jacketarmor_info.normal_protection = .30
jacketarmor_info.energy_protection = .00
jacketarmor_info.armor = ARMOR_JACKET

combatarmor_info = gitem_armor_t()
combatarmor_info.base_count = 50
combatarmor_info.max_count = 100
combatarmor_info.normal_protection = .60
combatarmor_info.energy_protection = .30
combatarmor_info.armor = ARMOR_COMBAT

bodyarmor_info = gitem_armor_t()
bodyarmor_info.base_count = 100
bodyarmor_info.max_count = 200
bodyarmor_info.normal_protection = .80
bodyarmor_info.energy_protection = .60
bodyarmor_info.armor = ARMOR_BODY

#
# static
#
jacket_armor_index = 0
combat_armor_index = 0
body_armor_index = 0
power_screen_index = 0
power_shield_index = 0
quad_drop_timeout_hack = 0

#
# forward declarations for pickup functions defined below
#
# void Use_Quad (edict_t *ent, gitem_t *item);

"""
===============
GetItemByIndex
===============
"""
def GetItemByIndex (index):
	if index == 0 or index >= g_main.game.num_items:
		return None

	return itemlist[index]


"""
===============
FindItemByClassname
===============
"""
def FindItemByClassname (classname):
	#int i
	#gitem_t *it
	for i in range(g_main.game.num_items):
		it = itemlist[i]
		if not it.classname:
			continue
		if not Q_stricmp(it.classname, classname):
			return it

	return None


"""
===============
FindItem
===============
"""
def FindItem (pickup_name):
	#int i
	#gitem_t *it
	for i in range(g_main.game.num_items):
		it = itemlist[i]
		if not it.pickup_name:
			continue
		if not Q_stricmp(it.pickup_name, pickup_name):
			return it

	return None


def ITEM_INDEX (item):
	# #define ITEM_INDEX(x) ((x)-itemlist)
	return itemlist.index(item)


"""
==========
DoRespawn
==========
"""
def DoRespawn (ent):
	if ent.team:
		#edict_t *master
		#int count, choice
		master = ent.teammaster

		count = 0
		tmp = master
		while tmp:
			count += 1
			tmp = tmp.chain

		choice = _r.randint(0, 2147483647) % count

		count = 0
		tmp = master
		while count < choice:
			tmp = tmp.chain
			count += 1
		ent = tmp

	ent.svflags &= ~SVF_NOCLIENT
	ent.solid = SOLID_TRIGGER
	g_main.gi.linkentity (ent)

	# send an effect
	ent.s.event = EV_ITEM_RESPAWN


def SetRespawn (ent, delay):
	ent.flags |= FL_RESPAWN
	ent.svflags |= SVF_NOCLIENT
	ent.solid = SOLID_NOT
	ent.nextthink = g_main.level.time + delay
	ent.think = DoRespawn
	g_main.gi.linkentity (ent)


"""
================================================================
"""
def Pickup_Powerup (ent, other):
	#int quantity
	quantity = other.client.pers.inventory[ITEM_INDEX(ent.item)]
	if (g_main.skill.value == 1 and quantity >= 2) or (g_main.skill.value >= 2 and quantity >= 1):
		return False

	if g_main.coop.value and (ent.item.flags & IT_STAY_COOP) and (quantity > 0):
		return False

	other.client.pers.inventory[ITEM_INDEX(ent.item)] += 1

	if g_main.deathmatch.value:
		if not (ent.spawnflags & DROPPED_ITEM):
			SetRespawn (ent, ent.item.quantity)
		if (int(g_main.dmflags.value) & q_shared.DF_INSTANT_ITEMS) or ((ent.item.use == Use_Quad) and (ent.spawnflags & DROPPED_PLAYER_ITEM)):
			if (ent.item.use == Use_Quad) and (ent.spawnflags & DROPPED_PLAYER_ITEM):
				global quad_drop_timeout_hack
				quad_drop_timeout_hack = (ent.nextthink - g_main.level.time) / FRAMETIME
			ent.item.use (other, ent.item)

	return True


def Drop_General (ent, item):
	Drop_Item (ent, item)
	ent.client.pers.inventory[ITEM_INDEX(item)] -= 1
	g_cmds.ValidateSelectedItem (ent)


"""
==========
Pickup_Adrenaline
==========
"""
def Pickup_Adrenaline (ent, other):
	if not g_main.deathmatch.value:
		other.max_health += 1

	if other.health < other.max_health:
		other.health = other.max_health

	if not (ent.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
		SetRespawn (ent, ent.item.quantity)

	return True


"""
==========
Pickup_AncientHead
==========
"""
def Pickup_AncientHead (ent, other):
	other.max_health += 2

	if not (ent.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
		SetRespawn (ent, ent.item.quantity)

	return True


"""
==========
Pickup_Bandolier
==========
"""
def Pickup_Bandolier (ent, other):
	#gitem_t *item
	#int index
	if other.client.pers.max_bullets < 250:
		other.client.pers.max_bullets = 250
	if other.client.pers.max_shells < 150:
		other.client.pers.max_shells = 150
	if other.client.pers.max_cells < 250:
		other.client.pers.max_cells = 250
	if other.client.pers.max_slugs < 75:
		other.client.pers.max_slugs = 75

	item = FindItem("Bullets")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_bullets:
			other.client.pers.inventory[index] = other.client.pers.max_bullets

	item = FindItem("Shells")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_shells:
			other.client.pers.inventory[index] = other.client.pers.max_shells

	if not (ent.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
		SetRespawn (ent, ent.item.quantity)

	return True


"""
==========
Pickup_Pack
==========
"""
def Pickup_Pack (ent, other):
	#gitem_t *item
	#int index
	if other.client.pers.max_bullets < 300:
		other.client.pers.max_bullets = 300
	if other.client.pers.max_shells < 200:
		other.client.pers.max_shells = 200
	if other.client.pers.max_rockets < 100:
		other.client.pers.max_rockets = 100
	if other.client.pers.max_grenades < 100:
		other.client.pers.max_grenades = 100
	if other.client.pers.max_cells < 300:
		other.client.pers.max_cells = 300
	if other.client.pers.max_slugs < 100:
		other.client.pers.max_slugs = 100

	item = FindItem("Bullets")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_bullets:
			other.client.pers.inventory[index] = other.client.pers.max_bullets

	item = FindItem("Shells")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_shells:
			other.client.pers.inventory[index] = other.client.pers.max_shells

	item = FindItem("Cells")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_cells:
			other.client.pers.inventory[index] = other.client.pers.max_cells

	item = FindItem("Grenades")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_grenades:
			other.client.pers.inventory[index] = other.client.pers.max_grenades

	item = FindItem("Rockets")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_rockets:
			other.client.pers.inventory[index] = other.client.pers.max_rockets

	item = FindItem("Slugs")
	if item:
		index = ITEM_INDEX(item)
		other.client.pers.inventory[index] += item.quantity
		if other.client.pers.inventory[index] > other.client.pers.max_slugs:
			other.client.pers.inventory[index] = other.client.pers.max_slugs

	if not (ent.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
		SetRespawn (ent, ent.item.quantity)

	return True


"""
==========
Use_Quad
==========
"""
def Use_Quad (ent, item):
	#int timeout
	global quad_drop_timeout_hack
	ent.client.pers.inventory[ITEM_INDEX(item)] -= 1
	g_cmds.ValidateSelectedItem (ent)

	if quad_drop_timeout_hack:
		timeout = quad_drop_timeout_hack
		quad_drop_timeout_hack = 0
	else:
		timeout = 300

	if ent.client.quad_framenum > g_main.level.framenum:
		ent.client.quad_framenum += timeout
	else:
		ent.client.quad_framenum = g_main.level.framenum + timeout

	g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("items/damage.wav"), 1, ATTN_NORM, 0)


"""
==========
Use_Breather
==========
"""
def Use_Breather (ent, item):
	ent.client.pers.inventory[ITEM_INDEX(item)] -= 1
	g_cmds.ValidateSelectedItem (ent)

	if ent.client.breather_framenum > g_main.level.framenum:
		ent.client.breather_framenum += 300
	else:
		ent.client.breather_framenum = g_main.level.framenum + 300


"""
==========
Use_Envirosuit
==========
"""
def Use_Envirosuit (ent, item):
	ent.client.pers.inventory[ITEM_INDEX(item)] -= 1
	g_cmds.ValidateSelectedItem (ent)

	if ent.client.enviro_framenum > g_main.level.framenum:
		ent.client.enviro_framenum += 300
	else:
		ent.client.enviro_framenum = g_main.level.framenum + 300


"""
==========
Use_Invulnerability
==========
"""
def Use_Invulnerability (ent, item):
	ent.client.pers.inventory[ITEM_INDEX(item)] -= 1
	g_cmds.ValidateSelectedItem (ent)

	if ent.client.invincible_framenum > g_main.level.framenum:
		ent.client.invincible_framenum += 300
	else:
		ent.client.invincible_framenum = g_main.level.framenum + 300

	g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("items/protect.wav"), 1, ATTN_NORM, 0)


"""
==========
Use_Silencer
==========
"""
def Use_Silencer (ent, item):
	ent.client.pers.inventory[ITEM_INDEX(item)] -= 1
	g_cmds.ValidateSelectedItem (ent)
	ent.client.silencer_shots += 30


"""
==========
Pickup_Key
==========
"""
def Pickup_Key (ent, other):
	if g_main.coop.value:
		if ent.classname == "key_power_cube":
			if other.client.pers.power_cubes & ((ent.spawnflags & 0x0000ff00) >> 8):
				return False
			other.client.pers.inventory[ITEM_INDEX(ent.item)] += 1
			other.client.pers.power_cubes |= ((ent.spawnflags & 0x0000ff00) >> 8)
		else:
			if other.client.pers.inventory[ITEM_INDEX(ent.item)]:
				return False
			other.client.pers.inventory[ITEM_INDEX(ent.item)] = 1
		return True
	other.client.pers.inventory[ITEM_INDEX(ent.item)] += 1
	return True


"""
==========
Add_Ammo
==========
"""
def Add_Ammo (ent, item, count):
	#int index, max
	if not ent.client:
		return False

	if item.tag == AMMO_BULLETS:
		max = ent.client.pers.max_bullets
	elif item.tag == AMMO_SHELLS:
		max = ent.client.pers.max_shells
	elif item.tag == AMMO_ROCKETS:
		max = ent.client.pers.max_rockets
	elif item.tag == AMMO_GRENADES:
		max = ent.client.pers.max_grenades
	elif item.tag == AMMO_CELLS:
		max = ent.client.pers.max_cells
	elif item.tag == AMMO_SLUGS:
		max = ent.client.pers.max_slugs
	else:
		return False

	index = ITEM_INDEX(item)

	if ent.client.pers.inventory[index] == max:
		return False

	ent.client.pers.inventory[index] += count

	if ent.client.pers.inventory[index] > max:
		ent.client.pers.inventory[index] = max

	return True


def Pickup_Ammo (ent, other):
	#int oldcount, count
	#qboolean weapon
	weapon = (ent.item.flags & IT_WEAPON)
	if weapon and (int(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		count = 1000
	elif ent.count:
		count = ent.count
	else:
		count = ent.item.quantity

	oldcount = other.client.pers.inventory[ITEM_INDEX(ent.item)]

	if not Add_Ammo (other, ent.item, count):
		return False

	if weapon and not oldcount:
		if other.client.pers.weapon != ent.item and (not g_main.deathmatch.value or other.client.pers.weapon == FindItem("blaster")):
			other.client.newweapon = ent.item

	if not (ent.spawnflags & (DROPPED_ITEM | DROPPED_PLAYER_ITEM)) and g_main.deathmatch.value:
		SetRespawn (ent, 30)
	return True


def Drop_Ammo (ent, item):
	#edict_t *dropped
	#int index
	index = ITEM_INDEX(item)
	dropped = Drop_Item (ent, item)
	if ent.client.pers.inventory[index] >= item.quantity:
		dropped.count = item.quantity
	else:
		dropped.count = ent.client.pers.inventory[index]

	if (ent.client.pers.weapon and
		ent.client.pers.weapon.tag == AMMO_GRENADES and
		item.tag == AMMO_GRENADES and
		ent.client.pers.inventory[index] - dropped.count <= 0):
		g_main.gi.cprintf (ent, PRINT_HIGH, "Can't drop current weapon\n")
		g_utils.G_FreeEdict(dropped)
		return

	ent.client.pers.inventory[index] -= dropped.count
	g_cmds.ValidateSelectedItem (ent)


"""
================================================================
"""
def MegaHealth_think (self):
	if self.owner.health > self.owner.max_health:
		self.nextthink = g_main.level.time + 1
		self.owner.health -= 1
		return

	if not (self.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
		SetRespawn (self, 20)
	else:
		g_utils.G_FreeEdict (self)


def Pickup_Health (ent, other):
	if not (ent.style & HEALTH_IGNORE_MAX):
		if other.health >= other.max_health:
			return False

	other.health += ent.count

	if not (ent.style & HEALTH_IGNORE_MAX):
		if other.health > other.max_health:
			other.health = other.max_health

	if ent.style & HEALTH_TIMED:
		ent.think = MegaHealth_think
		ent.nextthink = g_main.level.time + 5
		ent.owner = other
		ent.flags |= FL_RESPAWN
		ent.svflags |= SVF_NOCLIENT
		ent.solid = SOLID_NOT
	else:
		if not (ent.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
			SetRespawn (ent, 30)

	return True


"""
================================================================
"""
def ArmorIndex (ent):
	if not ent.client:
		return 0

	if ent.client.pers.inventory[jacket_armor_index] > 0:
		return jacket_armor_index

	if ent.client.pers.inventory[combat_armor_index] > 0:
		return combat_armor_index

	if ent.client.pers.inventory[body_armor_index] > 0:
		return body_armor_index

	return 0


def Pickup_Armor (ent, other):
	#int old_armor_index, newcount, salvagecount
	#gitem_armor_t *oldinfo, *newinfo
	#float salvage
	# get info on new armor
	newinfo = ent.item.info

	old_armor_index = ArmorIndex (other)

	# handle armor shards specially
	if ent.item.tag == ARMOR_SHARD:
		if not old_armor_index:
			other.client.pers.inventory[jacket_armor_index] = 2
		else:
			other.client.pers.inventory[old_armor_index] += 2

	# if player has no armor, just use it
	elif not old_armor_index:
		other.client.pers.inventory[ITEM_INDEX(ent.item)] = newinfo.base_count

	# use the better armor
	else:
		# get info on old armor
		if old_armor_index == jacket_armor_index:
			oldinfo = jacketarmor_info
		elif old_armor_index == combat_armor_index:
			oldinfo = combatarmor_info
		else:  # (old_armor_index == body_armor_index)
			oldinfo = bodyarmor_info

		if newinfo.normal_protection > oldinfo.normal_protection:
			# calc new armor values
			salvage = oldinfo.normal_protection / newinfo.normal_protection
			salvagecount = salvage * other.client.pers.inventory[old_armor_index]
			newcount = newinfo.base_count + salvagecount
			if newcount > newinfo.max_count:
				newcount = newinfo.max_count

			# zero count of old armor so it goes away
			other.client.pers.inventory[old_armor_index] = 0

			# change armor to new item with computed value
			other.client.pers.inventory[ITEM_INDEX(ent.item)] = newcount
		else:
			# calc new armor values
			salvage = newinfo.normal_protection / oldinfo.normal_protection
			salvagecount = salvage * newinfo.base_count
			newcount = other.client.pers.inventory[old_armor_index] + salvagecount
			if newcount > oldinfo.max_count:
				newcount = oldinfo.max_count

			# if we're already maxed out then we don't need the new armor
			if other.client.pers.inventory[old_armor_index] >= newcount:
				return False

			# update current armor value
			other.client.pers.inventory[old_armor_index] = newcount

	if not (ent.spawnflags & DROPPED_ITEM) and g_main.deathmatch.value:
		SetRespawn (ent, 20)

	return True


"""
================================================================
"""
def PowerArmorType (ent):
	if not ent.client:
		return POWER_ARMOR_NONE

	if not (ent.flags & FL_POWER_ARMOR):
		return POWER_ARMOR_NONE

	if ent.client.pers.inventory[power_shield_index] > 0:
		return POWER_ARMOR_SHIELD

	if ent.client.pers.inventory[power_screen_index] > 0:
		return POWER_ARMOR_SCREEN

	return POWER_ARMOR_NONE


def Use_PowerArmor (ent, item):
	#int index
	if ent.flags & FL_POWER_ARMOR:
		ent.flags &= ~FL_POWER_ARMOR
		g_main.gi.sound(ent, CHAN_AUTO, g_main.gi.soundindex("misc/power2.wav"), 1, ATTN_NORM, 0)
	else:
		index = ITEM_INDEX(FindItem("cells"))
		if not ent.client.pers.inventory[index]:
			g_main.gi.cprintf (ent, PRINT_HIGH, "No cells for power armor.\n")
			return
		ent.flags |= FL_POWER_ARMOR
		g_main.gi.sound(ent, CHAN_AUTO, g_main.gi.soundindex("misc/power1.wav"), 1, ATTN_NORM, 0)


def Pickup_PowerArmor (ent, other):
	#int quantity
	quantity = other.client.pers.inventory[ITEM_INDEX(ent.item)]

	other.client.pers.inventory[ITEM_INDEX(ent.item)] += 1

	if g_main.deathmatch.value:
		if not (ent.spawnflags & DROPPED_ITEM):
			SetRespawn (ent, ent.item.quantity)
		# auto-use for DM only if we didn't already have one
		if not quantity:
			ent.item.use (other, ent.item)

	return True


def Drop_PowerArmor (ent, item):
	if (ent.flags & FL_POWER_ARMOR) and (ent.client.pers.inventory[ITEM_INDEX(item)] == 1):
		Use_PowerArmor (ent, item)
	Drop_General (ent, item)


"""
===============
Touch_Item
===============
"""
def Touch_Item (ent, other, plane, surf):
	#qboolean taken
	if not other.client:
		return
	if other.health < 1:
		return		# dead people can't pickup
	if not ent.item.pickup:
		return		# not a grabbable item?

	taken = ent.item.pickup(ent, other)

	if taken:
		# flash the screen
		other.client.bonus_alpha = 0.25

		# show icon and name on status bar
		other.client.ps.stats[STAT_PICKUP_ICON] = g_main.gi.imageindex(ent.item.icon)
		other.client.ps.stats[STAT_PICKUP_STRING] = CS_ITEMS+ITEM_INDEX(ent.item)
		other.client.pickup_msg_time = g_main.level.time + 3.0

		# change selected item
		if ent.item.use:
			other.client.pers.selected_item = other.client.ps.stats[STAT_SELECTED_ITEM] = ITEM_INDEX(ent.item)

		if ent.item.pickup == Pickup_Health:
			if ent.count == 2:
				g_main.gi.sound(other, CHAN_ITEM, g_main.gi.soundindex("items/s_health.wav"), 1, ATTN_NORM, 0)
			elif ent.count == 10:
				g_main.gi.sound(other, CHAN_ITEM, g_main.gi.soundindex("items/n_health.wav"), 1, ATTN_NORM, 0)
			elif ent.count == 25:
				g_main.gi.sound(other, CHAN_ITEM, g_main.gi.soundindex("items/l_health.wav"), 1, ATTN_NORM, 0)
			else:  # (ent->count == 100)
				g_main.gi.sound(other, CHAN_ITEM, g_main.gi.soundindex("items/m_health.wav"), 1, ATTN_NORM, 0)
		elif ent.item.pickup_sound:
			g_main.gi.sound(other, CHAN_ITEM, g_main.gi.soundindex(ent.item.pickup_sound), 1, ATTN_NORM, 0)

	if not (ent.spawnflags & ITEM_TARGETS_USED):
		g_utils.G_UseTargets (ent, other)
		ent.spawnflags |= ITEM_TARGETS_USED

	if not taken:
		return

	if not (g_main.coop.value and (ent.item.flags & IT_STAY_COOP)) or (ent.spawnflags & (DROPPED_ITEM | DROPPED_PLAYER_ITEM)):
		if ent.flags & FL_RESPAWN:
			ent.flags &= ~FL_RESPAWN
		else:
			g_utils.G_FreeEdict (ent)


"""
================================================================
"""
def drop_temp_touch (ent, other, plane, surf):
	if other == ent.owner:
		return

	Touch_Item (ent, other, plane, surf)


def drop_make_touchable (ent):
	ent.touch = Touch_Item
	if g_main.deathmatch.value:
		ent.nextthink = g_main.level.time + 29
		ent.think = g_utils.G_FreeEdict


def Drop_Item (ent, item):
	#edict_t *dropped
	#vec3_t forward, right, offset
	forward = [0, 0, 0]
	right = [0, 0, 0]
	offset = [0, 0, 0]

	dropped = g_utils.G_Spawn()

	dropped.classname = item.classname
	dropped.item = item
	dropped.spawnflags = DROPPED_ITEM
	dropped.s.effects = item.world_model_flags
	dropped.s.renderfx = RF_GLOW
	q_shared.VectorSet (dropped.mins, -15, -15, -15)
	q_shared.VectorSet (dropped.maxs, 15, 15, 15)
	g_main.gi.setmodel (dropped, dropped.item.world_model)
	dropped.solid = SOLID_TRIGGER
	dropped.movetype = MOVETYPE_TOSS
	dropped.touch = drop_temp_touch
	dropped.owner = ent

	if ent.client:
		#trace_t trace
		q_shared.AngleVectors (ent.client.v_angle, forward, right, None)
		q_shared.VectorSet(offset, 24, 0, -16)
		g_utils.G_ProjectSource (ent.s.origin, offset, forward, right, dropped.s.origin)
		trace = g_main.gi.trace (ent.s.origin, dropped.mins, dropped.maxs,
			dropped.s.origin, ent, CONTENTS_SOLID)
		q_shared.VectorCopy (trace.endpos, dropped.s.origin)
	else:
		q_shared.AngleVectors (ent.s.angles, forward, right, None)
		q_shared.VectorCopy (ent.s.origin, dropped.s.origin)

	q_shared.VectorScale (forward, 100, dropped.velocity)
	dropped.velocity[2] = 300

	dropped.think = drop_make_touchable
	dropped.nextthink = g_main.level.time + 1

	g_main.gi.linkentity (dropped)

	return dropped


def Use_Item (ent, other, activator):
	ent.svflags &= ~SVF_NOCLIENT
	ent.use = None

	if ent.spawnflags & ITEM_NO_TOUCH:
		ent.solid = SOLID_BBOX
		ent.touch = None
	else:
		ent.solid = SOLID_TRIGGER
		ent.touch = Touch_Item

	g_main.gi.linkentity (ent)


"""
================================================================
"""
def droptofloor (ent):
	#trace_t tr
	#vec3_t dest
	#float *v
	v = [0, 0, 0]
	dest = [0, 0, 0]

	v = g_utils.tv(-15, -15, -15)
	q_shared.VectorCopy (v, ent.mins)
	v = g_utils.tv(15, 15, 15)
	q_shared.VectorCopy (v, ent.maxs)

	if ent.model:
		g_main.gi.setmodel (ent, ent.model)
	else:
		g_main.gi.setmodel (ent, ent.item.world_model)
	ent.solid = SOLID_TRIGGER
	ent.movetype = MOVETYPE_TOSS
	ent.touch = Touch_Item

	v = g_utils.tv(0, 0, -128)
	q_shared.VectorAdd (ent.s.origin, v, dest)

	tr = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, dest, ent, MASK_SOLID)
	if tr.startsolid:
		g_main.gi.dprintf ("droptofloor: %s startsolid at %s\n", ent.classname, g_utils.vtos(ent.s.origin))
		g_utils.G_FreeEdict (ent)
		return

	q_shared.VectorCopy (tr.endpos, ent.s.origin)

	if ent.team:
		ent.flags &= ~FL_TEAMSLAVE
		ent.chain = ent.teamchain
		ent.teamchain = None

		ent.svflags |= SVF_NOCLIENT
		ent.solid = SOLID_NOT
		if ent == ent.teammaster:
			ent.nextthink = g_main.level.time + FRAMETIME
			ent.think = DoRespawn

	if ent.spawnflags & ITEM_NO_TOUCH:
		ent.solid = SOLID_BBOX
		ent.touch = None
		ent.s.effects &= ~EF_ROTATE
		ent.s.renderfx &= ~RF_GLOW

	if ent.spawnflags & ITEM_TRIGGER_SPAWN:
		ent.svflags |= SVF_NOCLIENT
		ent.solid = SOLID_NOT
		ent.use = Use_Item

	g_main.gi.linkentity (ent)


"""
===============
PrecacheItem
===============
"""
def PrecacheItem (it):
	#char *s, *start
	#char data[MAX_QPATH]
	#int len
	#gitem_t *ammo
	if not it:
		return

	if it.pickup_sound:
		g_main.gi.soundindex (it.pickup_sound)
	if it.world_model:
		g_main.gi.modelindex (it.world_model)
	if it.view_model:
		g_main.gi.modelindex (it.view_model)
	if it.icon:
		g_main.gi.imageindex (it.icon)

	# parse everything for its ammo
	if it.ammo and it.ammo[0]:
		ammo = FindItem (it.ammo)
		if ammo != it:
			PrecacheItem (ammo)

	# parse the space seperated precache string for other items
	s = it.precaches
	if not s or not s[0]:
		return

	pos = 0
	while pos < len(s):
		start = pos
		while pos < len(s) and s[pos] != ' ':
			pos += 1

		l = pos - start
		if l >= MAX_QPATH or l < 5:
			g_main.gi.error ("PrecacheItem: %s has bad precache string", it.classname)
		data = s[start:pos]
		if pos < len(s):
			pos += 1

		# determine type based on extension
		if data[-3:] == "md2":
			g_main.gi.modelindex (data)
		elif data[-3:] == "sp2":
			g_main.gi.modelindex (data)
		elif data[-3:] == "wav":
			g_main.gi.soundindex (data)
		if data[-3:] == "pcx":
			g_main.gi.imageindex (data)


"""
============
SpawnItem
============
"""
def SpawnItem (ent, item):
	PrecacheItem (item)

	if ent.spawnflags:
		if ent.classname != "key_power_cube":
			ent.spawnflags = 0
			g_main.gi.dprintf("%s at %s has invalid spawnflags set\n", ent.classname, g_utils.vtos(ent.s.origin))

	# some items will be prevented in deathmatch
	if g_main.deathmatch.value:
		if int(g_main.dmflags.value) & q_shared.DF_NO_ARMOR:
			if item.pickup == Pickup_Armor or item.pickup == Pickup_PowerArmor:
				g_utils.G_FreeEdict (ent)
				return
		if int(g_main.dmflags.value) & q_shared.DF_NO_ITEMS:
			if item.pickup == Pickup_Powerup:
				g_utils.G_FreeEdict (ent)
				return
		if int(g_main.dmflags.value) & q_shared.DF_NO_HEALTH:
			if item.pickup == Pickup_Health or item.pickup == Pickup_Adrenaline or item.pickup == Pickup_AncientHead:
				g_utils.G_FreeEdict (ent)
				return
		if int(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO:
			if (item.flags == IT_AMMO) or (ent.classname == "weapon_bfg"):
				g_utils.G_FreeEdict (ent)
				return

	if g_main.coop.value and (ent.classname == "key_power_cube"):
		ent.spawnflags |= (1 << (8 + g_main.level.power_cubes))
		g_main.level.power_cubes += 1

	# don't let them drop items that stay in a coop game
	if g_main.coop.value and (item.flags & IT_STAY_COOP):
		item.drop = None

	ent.item = item
	ent.nextthink = g_main.level.time + 2 * FRAMETIME    # items start after other solids
	ent.think = droptofloor
	ent.s.effects = item.world_model_flags
	ent.s.renderfx = RF_GLOW
	if ent.model:
		g_main.gi.modelindex (ent.model)


"""
================================================================
"""
def _mk (classname, pickup, use, drop, weaponthink, pickup_sound,
		world_model, world_model_flags, view_model, icon, pickup_name,
		count_width, quantity, ammo, flags, weapmodel, info, tag,
		precaches):
	it = gitem_t()
	it.classname = classname
	it.pickup = pickup
	it.use = use
	it.drop = drop
	it.weaponthink = weaponthink
	it.pickup_sound = pickup_sound
	it.world_model = world_model
	it.world_model_flags = world_model_flags
	it.view_model = view_model
	it.icon = icon
	it.pickup_name = pickup_name
	it.count_width = count_width
	it.quantity = quantity
	it.ammo = ammo
	it.flags = flags
	it.weapmodel = weapmodel
	it.info = info
	it.tag = tag
	it.precaches = precaches
	return it


itemlist = [
	# leave index 0 alone
	_mk(None, None, None, None, None, None, None, 0, None, None, None,
		0, 0, None, 0, 0, None, 0, ""),

	#
	# ARMOR
	#
	_mk("item_armor_body", Pickup_Armor, None, None, None,
		"misc/ar1_pkup.wav", "models/items/armor/body/tris.md2", EF_ROTATE,
		None, "i_bodyarmor", "Body Armor", 3, 0, None, IT_ARMOR, 0,
		bodyarmor_info, ARMOR_BODY, ""),

	_mk("item_armor_combat", Pickup_Armor, None, None, None,
		"misc/ar1_pkup.wav", "models/items/armor/combat/tris.md2", EF_ROTATE,
		None, "i_combatarmor", "Combat Armor", 3, 0, None, IT_ARMOR, 0,
		combatarmor_info, ARMOR_COMBAT, ""),

	_mk("item_armor_jacket", Pickup_Armor, None, None, None,
		"misc/ar1_pkup.wav", "models/items/armor/jacket/tris.md2", EF_ROTATE,
		None, "i_jacketarmor", "Jacket Armor", 3, 0, None, IT_ARMOR, 0,
		jacketarmor_info, ARMOR_JACKET, ""),

	_mk("item_armor_shard", Pickup_Armor, None, None, None,
		"misc/ar2_pkup.wav", "models/items/armor/shard/tris.md2", EF_ROTATE,
		None, "i_jacketarmor", "Armor Shard", 3, 0, None, IT_ARMOR, 0,
		None, ARMOR_SHARD, ""),

	_mk("item_power_screen", Pickup_PowerArmor, Use_PowerArmor,
		Drop_PowerArmor, None, "misc/ar3_pkup.wav",
		"models/items/armor/screen/tris.md2", EF_ROTATE, None,
		"i_powerscreen", "Power Screen", 0, 60, None, IT_ARMOR, 0, None, 0,
		""),

	_mk("item_power_shield", Pickup_PowerArmor, Use_PowerArmor,
		Drop_PowerArmor, None, "misc/ar3_pkup.wav",
		"models/items/armor/shield/tris.md2", EF_ROTATE, None,
		"i_powershield", "Power Shield", 0, 60, None, IT_ARMOR, 0, None, 0,
		"misc/power2.wav misc/power1.wav"),

	#
	# WEAPONS
	#
	_mk("weapon_blaster", None, p_weapon.Use_Weapon, None,
		p_weapon.Weapon_Blaster, "misc/w_pkup.wav", None, 0,
		"models/weapons/v_blast/tris.md2", "w_blaster", "Blaster", 0, 0,
		None, IT_WEAPON|IT_STAY_COOP, g_local.WEAP_BLASTER, None, 0,
		"weapons/blastf1a.wav misc/lasfly.wav"),

	_mk("weapon_shotgun", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_Shotgun, "misc/w_pkup.wav",
		"models/weapons/g_shotg/tris.md2", EF_ROTATE,
		"models/weapons/v_shotg/tris.md2", "w_shotgun", "Shotgun", 0, 1,
		"Shells", IT_WEAPON|IT_STAY_COOP, g_local.WEAP_SHOTGUN, None, 0,
		"weapons/shotgf1b.wav weapons/shotgr1b.wav"),

	_mk("weapon_supershotgun", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_SuperShotgun,
		"misc/w_pkup.wav", "models/weapons/g_shotg2/tris.md2", EF_ROTATE,
		"models/weapons/v_shotg2/tris.md2", "w_sshotgun", "Super Shotgun",
		0, 2, "Shells", IT_WEAPON|IT_STAY_COOP,
		g_local.WEAP_SUPERSHOTGUN, None, 0, "weapons/sshotf1b.wav"),

	_mk("weapon_machinegun", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_Machinegun,
		"misc/w_pkup.wav", "models/weapons/g_machn/tris.md2", EF_ROTATE,
		"models/weapons/v_machn/tris.md2", "w_machinegun", "Machinegun", 0,
		1, "Bullets", IT_WEAPON|IT_STAY_COOP, g_local.WEAP_MACHINEGUN, None,
		0, "weapons/machgf1b.wav weapons/machgf2b.wav weapons/machgf3b.wav weapons/machgf4b.wav weapons/machgf5b.wav"),

	_mk("weapon_chaingun", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_Chaingun, "misc/w_pkup.wav",
		"models/weapons/g_chain/tris.md2", EF_ROTATE,
		"models/weapons/v_chain/tris.md2", "w_chaingun", "Chaingun", 0, 1,
		"Bullets", IT_WEAPON|IT_STAY_COOP, g_local.WEAP_CHAINGUN, None, 0,
		"weapons/chngnu1a.wav weapons/chngnl1a.wav weapons/machgf3b.wav` weapons/chngnd1a.wav"),

	_mk("ammo_grenades", Pickup_Ammo, p_weapon.Use_Weapon, Drop_Ammo,
		p_weapon.Weapon_Grenade, "misc/am_pkup.wav",
		"models/items/ammo/grenades/medium/tris.md2", 0,
		"models/weapons/v_handgr/tris.md2", "a_grenades", "Grenades", 3, 5,
		"grenades", IT_AMMO|IT_WEAPON, g_local.WEAP_GRENADES, None,
		AMMO_GRENADES,
		"weapons/hgrent1a.wav weapons/hgrena1b.wav weapons/hgrenc1b.wav weapons/hgrenb1a.wav weapons/hgrenb2a.wav "),

	_mk("weapon_grenadelauncher", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_GrenadeLauncher,
		"misc/w_pkup.wav", "models/weapons/g_launch/tris.md2", EF_ROTATE,
		"models/weapons/v_launch/tris.md2", "w_glauncher",
		"Grenade Launcher", 0, 1, "Grenades", IT_WEAPON|IT_STAY_COOP,
		g_local.WEAP_GRENADELAUNCHER, None, 0,
		"models/objects/grenade/tris.md2 weapons/grenlf1a.wav weapons/grenlr1b.wav weapons/grenlb1b.wav"),

	_mk("weapon_rocketlauncher", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_RocketLauncher,
		"misc/w_pkup.wav", "models/weapons/g_rocket/tris.md2", EF_ROTATE,
		"models/weapons/v_rocket/tris.md2", "w_rlauncher", "Rocket Launcher",
		0, 1, "Rockets", IT_WEAPON|IT_STAY_COOP,
		g_local.WEAP_ROCKETLAUNCHER, None, 0,
		"models/objects/rocket/tris.md2 weapons/rockfly.wav weapons/rocklf1a.wav weapons/rocklr1b.wav models/objects/debris2/tris.md2"),

	_mk("weapon_hyperblaster", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_HyperBlaster,
		"misc/w_pkup.wav", "models/weapons/g_hyperb/tris.md2", EF_ROTATE,
		"models/weapons/v_hyperb/tris.md2", "w_hyperblaster",
		"HyperBlaster", 0, 1, "Cells", IT_WEAPON|IT_STAY_COOP,
		g_local.WEAP_HYPERBLASTER, None, 0,
		"weapons/hyprbu1a.wav weapons/hyprbl1a.wav weapons/hyprbf1a.wav weapons/hyprbd1a.wav misc/lasfly.wav"),

	_mk("weapon_railgun", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_Railgun, "misc/w_pkup.wav",
		"models/weapons/g_rail/tris.md2", EF_ROTATE,
		"models/weapons/v_rail/tris.md2", "w_railgun", "Railgun", 0, 1,
		"Slugs", IT_WEAPON|IT_STAY_COOP, g_local.WEAP_RAILGUN, None, 0,
		"weapons/rg_hum.wav"),

	_mk("weapon_bfg", p_weapon.Pickup_Weapon, p_weapon.Use_Weapon,
		p_weapon.Drop_Weapon, p_weapon.Weapon_BFG, "misc/w_pkup.wav",
		"models/weapons/g_bfg/tris.md2", EF_ROTATE,
		"models/weapons/v_bfg/tris.md2", "w_bfg", "BFG10K", 0, 50, "Cells",
		IT_WEAPON|IT_STAY_COOP, g_local.WEAP_BFG, None, 0,
		"sprites/s_bfg1.sp2 sprites/s_bfg2.sp2 sprites/s_bfg3.sp2 weapons/bfg__f1y.wav weapons/bfg__l1a.wav weapons/bfg__x1b.wav weapons/bfg_hum.wav"),

	#
	# AMMO ITEMS
	#
	_mk("ammo_shells", Pickup_Ammo, None, Drop_Ammo, None, "misc/am_pkup.wav",
		"models/items/ammo/shells/medium/tris.md2", 0, None, "a_shells",
		"Shells", 3, 10, None, IT_AMMO, 0, None, AMMO_SHELLS, ""),

	_mk("ammo_bullets", Pickup_Ammo, None, Drop_Ammo, None,
		"misc/am_pkup.wav", "models/items/ammo/bullets/medium/tris.md2", 0,
		None, "a_bullets", "Bullets", 3, 50, None, IT_AMMO, 0, None,
		AMMO_BULLETS, ""),

	_mk("ammo_cells", Pickup_Ammo, None, Drop_Ammo, None, "misc/am_pkup.wav",
		"models/items/ammo/cells/medium/tris.md2", 0, None, "a_cells",
		"Cells", 3, 50, None, IT_AMMO, 0, None, AMMO_CELLS, ""),

	_mk("ammo_rockets", Pickup_Ammo, None, Drop_Ammo, None,
		"misc/am_pkup.wav", "models/items/ammo/rockets/medium/tris.md2", 0,
		None, "a_rockets", "Rockets", 3, 5, None, IT_AMMO, 0, None,
		AMMO_ROCKETS, ""),

	_mk("ammo_slugs", Pickup_Ammo, None, Drop_Ammo, None, "misc/am_pkup.wav",
		"models/items/ammo/slugs/medium/tris.md2", 0, None, "a_slugs",
		"Slugs", 3, 10, None, IT_AMMO, 0, None, AMMO_SLUGS, ""),

	#
	# POWERUP ITEMS
	#
	_mk("item_quad", Pickup_Powerup, Use_Quad, Drop_General, None,
		"items/pkup.wav", "models/items/quaddama/tris.md2", EF_ROTATE, None,
		"p_quad", "Quad Damage", 2, 60, None, IT_POWERUP, 0, None, 0,
		"items/damage.wav items/damage2.wav items/damage3.wav"),

	_mk("item_invulnerability", Pickup_Powerup, Use_Invulnerability,
		Drop_General, None, "items/pkup.wav",
		"models/items/invulner/tris.md2", EF_ROTATE, None,
		"p_invulnerability", "Invulnerability", 2, 300, None, IT_POWERUP,
		0, None, 0,
		"items/protect.wav items/protect2.wav items/protect4.wav"),

	_mk("item_silencer", Pickup_Powerup, Use_Silencer, Drop_General, None,
		"items/pkup.wav", "models/items/silencer/tris.md2", EF_ROTATE, None,
		"p_silencer", "Silencer", 2, 60, None, IT_POWERUP, 0, None, 0, ""),

	_mk("item_breather", Pickup_Powerup, Use_Breather, Drop_General, None,
		"items/pkup.wav", "models/items/breather/tris.md2", EF_ROTATE, None,
		"p_rebreather", "Rebreather", 2, 60, None, IT_STAY_COOP|IT_POWERUP,
		0, None, 0, "items/airout.wav"),

	_mk("item_enviro", Pickup_Powerup, Use_Envirosuit, Drop_General, None,
		"items/pkup.wav", "models/items/enviro/tris.md2", EF_ROTATE, None,
		"p_envirosuit", "Environment Suit", 2, 60, None,
		IT_STAY_COOP|IT_POWERUP, 0, None, 0, "items/airout.wav"),

	_mk("item_ancient_head", Pickup_AncientHead, None, None, None,
		"items/pkup.wav", "models/items/c_head/tris.md2", EF_ROTATE, None,
		"i_fixme", "Ancient Head", 2, 60, None, 0, 0, None, 0, ""),

	_mk("item_adrenaline", Pickup_Adrenaline, None, None, None,
		"items/pkup.wav", "models/items/adrenal/tris.md2", EF_ROTATE, None,
		"p_adrenaline", "Adrenaline", 2, 60, None, 0, 0, None, 0, ""),

	_mk("item_bandolier", Pickup_Bandolier, None, None, None, "items/pkup.wav",
		"models/items/band/tris.md2", EF_ROTATE, None, "p_bandolier",
		"Bandolier", 2, 60, None, 0, 0, None, 0, ""),

	_mk("item_pack", Pickup_Pack, None, None, None, "items/pkup.wav",
		"models/items/pack/tris.md2", EF_ROTATE, None, "i_pack", "Ammo Pack",
		2, 180, None, 0, 0, None, 0, ""),

	#
	# KEYS
	#
	_mk("key_data_cd", Pickup_Key, None, Drop_General, None, "items/pkup.wav",
		"models/items/keys/data_cd/tris.md2", EF_ROTATE, None, "k_datacd",
		"Data CD", 2, 0, None, IT_STAY_COOP|IT_KEY, 0, None, 0, ""),

	_mk("key_power_cube", Pickup_Key, None, Drop_General, None,
		"items/pkup.wav", "models/items/keys/power/tris.md2", EF_ROTATE, None,
		"k_powercube", "Power Cube", 2, 0, None, IT_STAY_COOP|IT_KEY, 0,
		None, 0, ""),

	_mk("key_pyramid", Pickup_Key, None, Drop_General, None, "items/pkup.wav",
		"models/items/keys/pyramid/tris.md2", EF_ROTATE, None, "k_pyramid",
		"Pyramid Key", 2, 0, None, IT_STAY_COOP|IT_KEY, 0, None, 0, ""),

	_mk("key_data_spinner", Pickup_Key, None, Drop_General, None,
		"items/pkup.wav", "models/items/keys/spinner/tris.md2", EF_ROTATE,
		None, "k_dataspin", "Data Spinner", 2, 0, None, IT_STAY_COOP|IT_KEY,
		0, None, 0, ""),

	_mk("key_pass", Pickup_Key, None, Drop_General, None, "items/pkup.wav",
		"models/items/keys/pass/tris.md2", EF_ROTATE, None, "k_security",
		"Security Pass", 2, 0, None, IT_STAY_COOP|IT_KEY, 0, None, 0, ""),

	_mk("key_blue_key", Pickup_Key, None, Drop_General, None,
		"items/pkup.wav", "models/items/keys/key/tris.md2", EF_ROTATE, None,
		"k_bluekey", "Blue Key", 2, 0, None, IT_STAY_COOP|IT_KEY, 0, None,
		0, ""),

	_mk("key_red_key", Pickup_Key, None, Drop_General, None,
		"items/pkup.wav", "models/items/keys/red_key/tris.md2", EF_ROTATE,
		None, "k_redkey", "Red Key", 2, 0, None, IT_STAY_COOP|IT_KEY, 0,
		None, 0, ""),

	_mk("key_commander_head", Pickup_Key, None, Drop_General, None,
		"items/pkup.wav", "models/monsters/commandr/head/tris.md2",
		q_shared.EF_GIB, None, "k_comhead", "Commander's Head", 2, 0, None,
		IT_STAY_COOP|IT_KEY, 0, None, 0, ""),

	_mk("key_airstrike_target", Pickup_Key, None, Drop_General, None,
		"items/pkup.wav", "models/items/keys/target/tris.md2", EF_ROTATE,
		None, "i_airstrike", "Airstrike Marker", 2, 0, None,
		IT_STAY_COOP|IT_KEY, 0, None, 0, ""),

	_mk(None, Pickup_Health, None, None, None, "items/pkup.wav", None, 0,
		None, "i_health", "Health", 3, 0, None, 0, 0, None, 0,
		"items/s_health.wav items/n_health.wav items/l_health.wav items/m_health.wav"),

	# end of list marker
	_mk(None, None, None, None, None, None, None, 0, None, None, None,
		0, 0, None, 0, 0, None, 0, ""),
]

# the C table ends with a final {NULL} marker; num_items = len - 1


"""
/*QUAKED item_health (.3 .3 1) (-16 -16 -16) (16 16 16)
*/
"""
def SP_item_health (self):
	if g_main.deathmatch.value and (int(g_main.dmflags.value) & q_shared.DF_NO_HEALTH):
		g_utils.G_FreeEdict (self)
		return

	self.model = "models/items/healing/medium/tris.md2"
	self.count = 10
	SpawnItem (self, FindItem ("Health"))
	g_main.gi.soundindex ("items/n_health.wav")


"""
/*QUAKED item_health_small (.3 .3 1) (-16 -16 -16) (16 16 16)
*/
"""
def SP_item_health_small (self):
	if g_main.deathmatch.value and (int(g_main.dmflags.value) & q_shared.DF_NO_HEALTH):
		g_utils.G_FreeEdict (self)
		return

	self.model = "models/items/healing/stimpack/tris.md2"
	self.count = 2
	SpawnItem (self, FindItem ("Health"))
	self.style = HEALTH_IGNORE_MAX
	g_main.gi.soundindex ("items/s_health.wav")


"""
/*QUAKED item_health_large (.3 .3 1) (-16 -16 -16) (16 16 16)
*/
"""
def SP_item_health_large (self):
	if g_main.deathmatch.value and (int(g_main.dmflags.value) & q_shared.DF_NO_HEALTH):
		g_utils.G_FreeEdict (self)
		return

	self.model = "models/items/healing/large/tris.md2"
	self.count = 25
	SpawnItem (self, FindItem ("Health"))
	g_main.gi.soundindex ("items/l_health.wav")


"""
/*QUAKED item_health_mega (.3 .3 1) (-16 -16 -16) (16 16 16)
*/
"""
def SP_item_health_mega (self):
	if g_main.deathmatch.value and (int(g_main.dmflags.value) & q_shared.DF_NO_HEALTH):
		g_utils.G_FreeEdict (self)
		return

	self.model = "models/items/mega_h/tris.md2"
	self.count = 100
	SpawnItem (self, FindItem ("Health"))
	g_main.gi.soundindex ("items/m_health.wav")
	self.style = HEALTH_IGNORE_MAX|HEALTH_TIMED


"""
==========
InitItems
==========
"""
def InitItems ():
	g_main.game.num_items = len(itemlist) - 1


"""
===============
SetItemNames

Called by worldspawn
===============
"""
def SetItemNames ():
	#int i
	#gitem_t *it
	global jacket_armor_index, combat_armor_index, body_armor_index
	global power_screen_index, power_shield_index

	for i in range(g_main.game.num_items):
		it = itemlist[i]
		g_main.gi.configstring (CS_ITEMS+i, it.pickup_name)

	jacket_armor_index = ITEM_INDEX(FindItem("Jacket Armor"))
	combat_armor_index = ITEM_INDEX(FindItem("Combat Armor"))
	body_armor_index   = ITEM_INDEX(FindItem("Body Armor"))
	power_screen_index = ITEM_INDEX(FindItem("Power Screen"))
	power_shield_index = ITEM_INDEX(FindItem("Power Shield"))
