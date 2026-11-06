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

HUD, deathmatch scoreboard, help computer and intermission stuff.

=======================================================================
"""
from __future__ import annotations
from common.shared import rand

from game import g_main, g_utils, g_items
from game.header.game import solid_t
from common.header.shared import pmtype_t
from game.header.local import FL_POWER_ARMOR, IT_KEY, CENTER_HANDED, svc_layout, svc_inventory
from common.header.shared import RDF_UNDERWATER, MAX_ITEMS, CHAN_ITEM, ATTN_NORM, STAT_HEALTH_ICON, STAT_HEALTH, STAT_AMMO_ICON, STAT_AMMO, STAT_ARMOR_ICON, STAT_ARMOR, STAT_PICKUP_ICON, STAT_PICKUP_STRING, STAT_TIMER_ICON, STAT_TIMER, STAT_SELECTED_ICON, STAT_SELECTED_ITEM, STAT_LAYOUTS, STAT_FRAGS, STAT_HELPICON, STAT_SPECTATOR, STAT_CHASE, CS_PLAYERSKINS
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from game.player import client as p_client

"""
#include "../header/local.h"
"""

def MoveClientToIntermission (ent): #edict_t *
	if not ent:

		return


	if int(g_main.deathmatch.value) or int(g_main.coop.value):
		ent.client.showscores = True
	shared.VectorCopy (g_main.level.intermission_origin, ent.s.origin)
	ent.client.ps.pmove.origin[0] = g_main.level.intermission_origin[0]*8
	ent.client.ps.pmove.origin[1] = g_main.level.intermission_origin[1]*8
	ent.client.ps.pmove.origin[2] = g_main.level.intermission_origin[2]*8
	shared.VectorCopy (g_main.level.intermission_angle, ent.client.ps.viewangles)
	ent.client.ps.pmove.pm_type = pmtype_t.PM_FREEZE.value
	ent.client.ps.gunindex = 0
	ent.client.ps.blend[3] = 0
	ent.client.ps.rdflags &= ~RDF_UNDERWATER

	# clean up powerup info
	ent.client.quad_framenum = 0
	ent.client.invincible_framenum = 0
	ent.client.breather_framenum = 0
	ent.client.enviro_framenum = 0
	ent.client.grenade_blew_up = False
	ent.client.grenade_time = 0

	ent.viewheight = 0
	ent.s.modelindex = 0
	ent.s.modelindex2 = 0
	ent.s.modelindex3 = 0
	ent.s.modelindex = 0
	ent.s.effects = 0
	ent.s.sound = 0
	ent.solid = solid_t.SOLID_NOT.value

	g_main.gi.linkentity(ent)

	# add the layout
	if int(g_main.deathmatch.value) or int(g_main.coop.value):
		DeathmatchScoreboardMessage (ent, None)
		g_main.gi.unicast (ent, True)



def BeginIntermission (targ): #edict_t *
	if not targ:

		return


	if g_main.level.intermissiontime:
		return		# already activated

	g_main.game.autosaved = False

	# respawn any dead clients
	for i in range(int(g_main.maxclients.value)):
		client = g_main.g_edicts[1 + i]
		if not client.inuse:
			continue
		if client.health <= 0:
			p_client.respawn(client)

	g_main.level.intermissiontime = g_main.level.time
	g_main.level.changemap = targ.map

	if targ.map and "*" in targ.map:
		if int(g_main.coop.value):
			for i in range(int(g_main.maxclients.value)):
				client = g_main.g_edicts[1 + i]
				if not client.inuse:
					continue
				# strip players of all keys between units
				for n in range(g_items.itemlist_len):
					if g_items.itemlist[n].flags & IT_KEY:
						client.client.pers.inventory[n] = 0

				client.client.pers.power_cubes = 0
	else:
		if not int(g_main.deathmatch.value):
			g_main.level.exitintermission = 1		# go immediately to the next level
			return

	g_main.level.exitintermission = 0

	# find an intermission spot
	ent = g_utils.G_Find (None, "classname", "info_player_intermission")
	if not ent:
		# the map creator forgot to put in an intermission point...
		ent = g_utils.G_Find (None, "classname", "info_player_start")
		if not ent:
			ent = g_utils.G_Find (None, "classname", "info_player_deathmatch")
	else:
		# chose one of four spots
		i = rand.randk() & 3
		while i:
			ent = g_utils.G_Find (ent, "classname", "info_player_intermission")
			if not ent:		# wrap around the list
				ent = g_utils.G_Find (ent, "classname", "info_player_intermission")
			i -= 1

	shared.VectorCopy (ent.s.origin, g_main.level.intermission_origin)
	shared.VectorCopy (ent.s.angles, g_main.level.intermission_angle)

	# In fact1 the intermission collides
	# with an area portal, resulting in
	# clutterings
	if not shared_c.Q_stricmp(g_main.level.mapname, "fact1"):

		g_main.level.intermission_origin[0] = 1037.0
		g_main.level.intermission_origin[1] = 1100.0
		g_main.level.intermission_origin[2] = 222.0


	# move all clients to the intermission point
	for i in range(int(g_main.maxclients.value)):
		client = g_main.g_edicts[1 + i]
		if not client.inuse:
			continue
		MoveClientToIntermission (client)



def DeathmatchScoreboardMessage (ent, killer): #edict_t *, edict_t *
	# sort the clients by score
	sorted_idx = []
	sortedscores = []
	for i in range(g_main.game.maxclients):
		cl_ent = g_main.g_edicts[1 + i]
		if not cl_ent.inuse or g_main.game.clients[i].resp.spectator:
			continue
		score = g_main.game.clients[i].resp.score
		j = 0
		while j < len(sortedscores):
			if score > sortedscores[j]:
				break
			j += 1
		while len(sorted_idx) > j:
			i2 = len(sorted_idx) - 1
			sorted_idx.insert(j, sorted_idx[i2])
			sortedscores.insert(j, sortedscores[i2])
			sorted_idx.pop(i2+1)
			sortedscores.pop(i2+1)
		sorted_idx.insert(j, i)
		sortedscores.insert(j, score)

	total = len(sorted_idx)

	# print level name and exit rules
	string = ""
	stringlength = 0

	# add the clients in sorted order
	if total > 12:
		total = 12

	for i in range(total):
		cl = g_main.game.clients[sorted_idx[i]]
		cl_ent = g_main.g_edicts[1 + sorted_idx[i]]

		x = 160 if (i>=6) else 0
		y = 32 + 32 * (i%6)

		# add a dogtag
		if cl_ent is ent:
			tag = "tag1"
		elif cl_ent is killer:
			tag = "tag2"
		else:
			tag = None
		if tag:
			entry = "xv %i yv %i picn %s " % (x+32, y, tag)
			j = len(entry)
			if stringlength + j > 1024:
				break
			string += entry
			stringlength += j

		# send the layout
		entry = "client %i %i %i %i %i %i " % (x, y, sorted_idx[i], cl.resp.score, cl.ping,
			(g_main.level.framenum - cl.resp.enterframe)//600)
		j = len(entry)
		if stringlength + j > 1024:
			break
		string += entry
		stringlength += j

	g_main.gi.WriteByte (svc_layout)
	g_main.gi.WriteString (string)



def HelpComputerMessage(ent): #edict_t *

	"""
	char string[1024];
	char *sk;
	"""

	if not ent:

		return


	if g_main.skill.value == local.SKILL_EASY:

		sk = "easy"

	elif g_main.skill.value == local.SKILL_MEDIUM:

		sk = "medium"

	elif g_main.skill.value == local.SKILL_HARD:

		sk = "hard"

	else:

		sk = "hard+"


	# send the layout
	string = ("xv 32 yv 8 picn help " # background
			"xv 202 yv 12 string2 \"%s\" " # skill
			"xv 0 yv 24 cstring2 \"%s\" " # level name
			"xv 0 yv 54 cstring2 \"%s\" " # help 1
			"xv 0 yv 110 cstring2 \"%s\" " # help 2
			"xv 50 yv 164 string2 \" kills     goals    secrets\" "
			"xv 50 yv 172 string2 \"%3i/%3i     %i/%i       %i/%i\" " %
			(sk,
			g_main.level.level_name,
			g_main.game.helpmessage1,
			g_main.game.helpmessage2,
			g_main.level.killed_monsters, g_main.level.total_monsters,
			g_main.level.found_goals, g_main.level.total_goals,
			g_main.level.found_secrets, g_main.level.total_secrets))[:1024 - 1] # Com_sprintf into char string[1024]

	g_main.gi.WriteByte(svc_layout)
	g_main.gi.WriteString(string)

def InventoryMessage(ent): #edict_t *

	"""
	int i;
	"""

	if not ent:

		return


	g_main.gi.WriteByte(svc_inventory)

	for i in range(MAX_ITEMS):

		g_main.gi.WriteShort(ent.client.pers.inventory[i])

def G_SetStats_SelectedItem(cl): #gclient_t * (static)

	"""
	const gitem_t *it;
	int si;
	"""

	si = cl.pers.selected_item
	it = g_items.GetItemByIndex(si)

	if (si <= 0) or (si >= g_items.itemlist_len):

		si = -1


	cl.ps.stats[STAT_SELECTED_ITEM] = si
	cl.ps.stats[STAT_SELECTED_ICON] = g_main.gi.imageindex(it.icon) if (it and it.icon) else 0

"""
=======================================================================

G_SetStats

=======================================================================
"""
def G_SetStats (ent): #edict_t *
	if not ent:

		return


	item = None
	index = 0
	cells = 0
	power_armor_type = 0

	# health
	ent.client.ps.stats[STAT_HEALTH_ICON] = g_main.level.pic_health
	ent.client.ps.stats[STAT_HEALTH] = -99 if (ent.health < -99) else ent.health

	# ammo
	if not ent.client.ammo_index:
		ent.client.ps.stats[STAT_AMMO_ICON] = 0
		ent.client.ps.stats[STAT_AMMO] = 0
	else:
		item = g_items.itemlist[ent.client.ammo_index]
		ent.client.ps.stats[STAT_AMMO_ICON] = g_main.gi.imageindex (item.icon)
		ent.client.ps.stats[STAT_AMMO] = ent.client.pers.inventory[ent.client.ammo_index]

	# armor
	power_armor_type = g_items.PowerArmorType (ent)
	if power_armor_type:
		cells = ent.client.pers.inventory[local.ITEM_INDEX(g_items.FindItem ("cells"))]
		if cells == 0:
			# ran out of cells for power armor
			ent.flags &= ~FL_POWER_ARMOR
			g_main.gi.sound(ent, CHAN_ITEM, g_main.gi.soundindex("misc/power2.wav"), 1, ATTN_NORM, 0)
			power_armor_type = 0

	index = g_items.ArmorIndex (ent)
	if power_armor_type and (not index or (g_main.level.framenum & 8)):
		# flash between power armor and other armor icon
		ent.client.ps.stats[STAT_ARMOR_ICON] = g_main.gi.imageindex ("i_powershield")
		ent.client.ps.stats[STAT_ARMOR] = cells
	elif index:
		item = g_items.GetItemByIndex (index)
		ent.client.ps.stats[STAT_ARMOR_ICON] = g_main.gi.imageindex (item.icon)
		ent.client.ps.stats[STAT_ARMOR] = ent.client.pers.inventory[index]
	else:
		ent.client.ps.stats[STAT_ARMOR_ICON] = 0
		ent.client.ps.stats[STAT_ARMOR] = 0

	# pickup message
	if g_main.level.time > ent.client.pickup_msg_time:
		ent.client.ps.stats[STAT_PICKUP_ICON] = 0
		ent.client.ps.stats[STAT_PICKUP_STRING] = 0

	# timers
	if ent.client.quad_framenum > g_main.level.framenum:
		ent.client.ps.stats[STAT_TIMER_ICON] = g_main.gi.imageindex ("p_quad")
		ent.client.ps.stats[STAT_TIMER] = (ent.client.quad_framenum - g_main.level.framenum)//10
	elif ent.client.invincible_framenum > g_main.level.framenum:
		ent.client.ps.stats[STAT_TIMER_ICON] = g_main.gi.imageindex ("p_invulnerability")
		ent.client.ps.stats[STAT_TIMER] = (ent.client.invincible_framenum - g_main.level.framenum)//10
	elif ent.client.enviro_framenum > g_main.level.framenum:
		ent.client.ps.stats[STAT_TIMER_ICON] = g_main.gi.imageindex ("p_envirosuit")
		ent.client.ps.stats[STAT_TIMER] = (ent.client.enviro_framenum - g_main.level.framenum)//10
	elif ent.client.breather_framenum > g_main.level.framenum:
		ent.client.ps.stats[STAT_TIMER_ICON] = g_main.gi.imageindex ("p_rebreather")
		ent.client.ps.stats[STAT_TIMER] = (ent.client.breather_framenum - g_main.level.framenum)//10
	else:
		ent.client.ps.stats[STAT_TIMER_ICON] = 0
		ent.client.ps.stats[STAT_TIMER] = 0

	# selected item
	G_SetStats_SelectedItem(ent.client)

	# layouts
	ent.client.ps.stats[STAT_LAYOUTS] = 0

	if int(g_main.deathmatch.value):
		if ent.client.pers.health <= 0 or g_main.level.intermissiontime \
			or ent.client.showscores:
			ent.client.ps.stats[STAT_LAYOUTS] |= 1
		if ent.client.showinventory and ent.client.pers.health > 0:
			ent.client.ps.stats[STAT_LAYOUTS] |= 2
	else:
		if ent.client.showscores or ent.client.showhelp:
			ent.client.ps.stats[STAT_LAYOUTS] |= 1
		if ent.client.showinventory and ent.client.pers.health > 0:
			ent.client.ps.stats[STAT_LAYOUTS] |= 2

	# frags
	ent.client.ps.stats[STAT_FRAGS] = ent.client.resp.score

	# help icon / current weapon if not shown
	if ent.client.pers.helpchanged and (g_main.level.framenum & 8):
		ent.client.ps.stats[STAT_HELPICON] = g_main.gi.imageindex ("i_help")
	elif (((ent.client.pers.hand == CENTER_HANDED) or (ent.client.ps.fov > 91))
			and ent.client.pers.weapon):

		#cvar_t *gun;
		gun = g_main.gi.cvar("cl_gun", "2", 0)

		if gun.value != 2:

			ent.client.ps.stats[STAT_HELPICON] = g_main.gi.imageindex (ent.client.pers.weapon.icon)

		else:

			ent.client.ps.stats[STAT_HELPICON] = 0


	else:
		ent.client.ps.stats[STAT_HELPICON] = 0

	ent.client.ps.stats[STAT_SPECTATOR] = 0



def G_CheckChaseStats (ent): #edict_t *
	if not ent:

		return


	for i in range(1, int(g_main.maxclients.value)+1):
		cl = g_main.g_edicts[i].client
		if not g_main.g_edicts[i].inuse or cl.chase_target is not ent:
			continue
		cl.ps.stats = list(ent.client.ps.stats)
		G_SetSpectatorStats(g_main.g_edicts[i])



def G_SetSpectatorStats (ent): #edict_t *
	if not ent:

		return


	cl = ent.client

	if not cl.chase_target:
		G_SetStats (ent)

	cl.ps.stats[STAT_SPECTATOR] = 1

	# layouts are independant in spectator
	cl.ps.stats[STAT_LAYOUTS] = 0
	if cl.pers.health <= 0 or g_main.level.intermissiontime or cl.showscores:
		cl.ps.stats[STAT_LAYOUTS] |= 1
	if cl.showinventory and cl.pers.health > 0:
		cl.ps.stats[STAT_LAYOUTS] |= 2

	if cl.chase_target and cl.chase_target.inuse:
		cl.ps.stats[STAT_CHASE] = CS_PLAYERSKINS + \
			g_main.g_edicts.index(cl.chase_target) - 1
	else:
		cl.ps.stats[STAT_CHASE] = 0

