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

pass
from game import g_local
from game import g_main
from game import g_utils
from game import g_items
from game import g_chase
from game import p_hud
from game import p_client
from common.shared.shared import Q_stricmp, Info_ValueForKey, vec3_origin
from common.header.shared import MAX_ITEMS, STAT_FRAGS, PMF_DUCKED, DF_MODELTEAMS, DF_SKINTEAMS, PRINT_HIGH, PRINT_CHAT
from game.g_local import (IT_WEAPON, IT_AMMO, IT_ARMOR, IT_POWERUP,
	FL_GODMODE, FL_NOTARGET, MOVETYPE_NOCLIP, MOVETYPE_WALK, ANIM_WAVE,
	MOD_SUICIDE, svc_inventory,
	FRAME_flip01, FRAME_flip12, FRAME_salute01, FRAME_salute11,
	FRAME_taunt01, FRAME_taunt17, FRAME_wave01, FRAME_wave11,
	FRAME_point01, FRAME_point12)

"""
#include "g_local.h"
#include "m_player.h"
"""

_client_team_index = [0]


def ClientTeam (ent):
	#char *p
	#static char value[512]
	if not ent.client:
		return ""

	value = Info_ValueForKey (ent.client.pers.userinfo, "skin")
	p = value.find('/')
	if p < 0:
		return value

	if int(g_main.dmflags.value) & DF_MODELTEAMS:
		return value[:p]

	# if ((int)(dmflags->value) & DF_SKINTEAMS)
	return value[p+1:]


def OnSameTeam (ent1, ent2):
	if not (int(g_main.dmflags.value) & (DF_MODELTEAMS | DF_SKINTEAMS)):
		return False

	ent1Team = ClientTeam (ent1)
	ent2Team = ClientTeam (ent2)

	if ent1Team == ent2Team:
		return True
	return False


def SelectNextItem (ent, itflags):
	#gclient_t *cl
	#int i, index
	#gitem_t *it
	cl = ent.client

	if cl.chase_target:
		g_chase.ChaseNext(ent)
		return

	# scan  for the next valid one
	for i in range(1, MAX_ITEMS+1):
		index = (cl.pers.selected_item + i) % MAX_ITEMS
		if not cl.pers.inventory[index]:
			continue
		it = g_items.itemlist[index]
		if not it.use:
			continue
		if not (it.flags & itflags):
			continue

		cl.pers.selected_item = index
		return

	cl.pers.selected_item = -1


def SelectPrevItem (ent, itflags):
	#gclient_t *cl
	#int i, index
	#gitem_t *it
	cl = ent.client

	if cl.chase_target:
		g_chase.ChasePrev(ent)
		return

	# scan  for the next valid one
	for i in range(1, MAX_ITEMS+1):
		index = (cl.pers.selected_item + MAX_ITEMS - i) % MAX_ITEMS
		if not cl.pers.inventory[index]:
			continue
		it = g_items.itemlist[index]
		if not it.use:
			continue
		if not (it.flags & itflags):
			continue

		cl.pers.selected_item = index
		return

	cl.pers.selected_item = -1


def ValidateSelectedItem (ent):
	#gclient_t *cl
	cl = ent.client

	sel = cl.pers.selected_item
	if 0 <= sel < MAX_ITEMS and cl.pers.inventory[sel]:
		return		# valid

	SelectNextItem (ent, -1)


"""
=================================================================================
"""

"""
==================
Cmd_Give_f

Give items to a client
==================
"""
def Cmd_Give_f (ent):
	#char *name
	#gitem_t *it
	#int index, i
	#qboolean give_all
	#edict_t *it_ent
	if g_main.deathmatch.value and not g_main.sv_cheats.value:
		g_main.gi.cprintf (ent, PRINT_HIGH, "You must run the server with '+set cheats 1' to enable this command.\n")
		return

	name = g_main.gi.args()

	if Q_stricmp(name, "all") == 0:
		give_all = True
	else:
		give_all = False

	if give_all or Q_stricmp(g_main.gi.argv(1), "health") == 0:
		if g_main.gi.argc() == 3:
			ent.health = int(g_main.gi.argv(2))
		else:
			ent.health = ent.max_health
		if not give_all:
			return

	if give_all or Q_stricmp(name, "weapons") == 0:
		for i in range(g_main.game.num_items):
			it = g_items.itemlist[i]
			if not it.pickup:
				continue
			if not (it.flags & IT_WEAPON):
				continue
			ent.client.pers.inventory[i] += 1
		if not give_all:
			return

	if give_all or Q_stricmp(name, "ammo") == 0:
		for i in range(g_main.game.num_items):
			it = g_items.itemlist[i]
			if not it.pickup:
				continue
			if not (it.flags & IT_AMMO):
				continue
			g_items.Add_Ammo (ent, it, 1000)
		if not give_all:
			return

	if give_all or Q_stricmp(name, "armor") == 0:
		#gitem_armor_t *info
		it = g_items.FindItem("Jacket Armor")
		ent.client.pers.inventory[g_items.ITEM_INDEX(it)] = 0

		it = g_items.FindItem("Combat Armor")
		ent.client.pers.inventory[g_items.ITEM_INDEX(it)] = 0

		it = g_items.FindItem("Body Armor")
		info = it.info
		ent.client.pers.inventory[g_items.ITEM_INDEX(it)] = info.max_count

		if not give_all:
			return

	if give_all or Q_stricmp(name, "Power Shield") == 0:
		it = g_items.FindItem("Power Shield")
		it_ent = g_utils.G_Spawn()
		it_ent.classname = it.classname
		g_items.SpawnItem (it_ent, it)
		g_items.Touch_Item (it_ent, ent, None, None)
		if it_ent.inuse:
			g_utils.G_FreeEdict(it_ent)

		if not give_all:
			return

	if give_all:
		for i in range(g_main.game.num_items):
			it = g_items.itemlist[i]
			if not it.pickup:
				continue
			if it.flags & (IT_ARMOR|IT_WEAPON|IT_AMMO):
				continue
			ent.client.pers.inventory[i] = 1
		return

	it = g_items.FindItem (name)
	if not it:
		name = g_main.gi.argv(1)
		it = g_items.FindItem (name)
		if not it:
			g_main.gi.cprintf (ent, PRINT_HIGH, "unknown item\n")
			return

	if not it.pickup:
		g_main.gi.cprintf (ent, PRINT_HIGH, "non-pickup item\n")
		return

	index = g_items.ITEM_INDEX(it)

	if it.flags & IT_AMMO:
		if g_main.gi.argc() == 3:
			ent.client.pers.inventory[index] = int(g_main.gi.argv(2))
		else:
			ent.client.pers.inventory[index] += it.quantity
	else:
		it_ent = g_utils.G_Spawn()
		it_ent.classname = it.classname
		g_items.SpawnItem (it_ent, it)
		g_items.Touch_Item (it_ent, ent, None, None)
		if it_ent.inuse:
			g_utils.G_FreeEdict(it_ent)


"""
==================
Cmd_God_f

Sets client to godmode

argv(0) god
==================
"""
def Cmd_God_f (ent):
	#char *msg
	if g_main.deathmatch.value and not g_main.sv_cheats.value:
		g_main.gi.cprintf (ent, PRINT_HIGH, "You must run the server with '+set cheats 1' to enable this command.\n")
		return

	ent.flags ^= FL_GODMODE
	if not (ent.flags & FL_GODMODE):
		msg = "godmode OFF\n"
	else:
		msg = "godmode ON\n"

	g_main.gi.cprintf (ent, PRINT_HIGH, msg)


"""
==================
Cmd_Notarget_f

Sets client to notarget

argv(0) notarget
==================
"""
def Cmd_Notarget_f (ent):
	#char *msg
	if g_main.deathmatch.value and not g_main.sv_cheats.value:
		g_main.gi.cprintf (ent, PRINT_HIGH, "You must run the server with '+set cheats 1' to enable this command.\n")
		return

	ent.flags ^= FL_NOTARGET
	if not (ent.flags & FL_NOTARGET):
		msg = "notarget OFF\n"
	else:
		msg = "notarget ON\n"

	g_main.gi.cprintf (ent, PRINT_HIGH, msg)


"""
==================
Cmd_Noclip_f

argv(0) noclip
==================
"""
def Cmd_Noclip_f (ent):
	#char *msg
	if g_main.deathmatch.value and not g_main.sv_cheats.value:
		g_main.gi.cprintf (ent, PRINT_HIGH, "You must run the server with '+set cheats 1' to enable this command.\n")
		return

	if ent.movetype == MOVETYPE_NOCLIP:
		ent.movetype = MOVETYPE_WALK
		msg = "noclip OFF\n"
	else:
		ent.movetype = MOVETYPE_NOCLIP
		msg = "noclip ON\n"

	g_main.gi.cprintf (ent, PRINT_HIGH, msg)


"""
==================
Cmd_Use_f

Use an inventory item
==================
"""
def Cmd_Use_f (ent):
	#int index
	#gitem_t *it
	#char *s
	s = g_main.gi.args()
	it = g_items.FindItem (s)
	if not it:
		g_main.gi.cprintf (ent, PRINT_HIGH, "unknown item: %s\n", s)
		return
	if not it.use:
		g_main.gi.cprintf (ent, PRINT_HIGH, "Item is not usable.\n")
		return
	index = g_items.ITEM_INDEX(it)
	if not ent.client.pers.inventory[index]:
		g_main.gi.cprintf (ent, PRINT_HIGH, "Out of item: %s\n", s)
		return

	it.use (ent, it)


"""
==================
Cmd_Drop_f

Drop an inventory item
==================
"""
def Cmd_Drop_f (ent):
	#int index
	#gitem_t *it
	#char *s
	s = g_main.gi.args()
	it = g_items.FindItem (s)
	if not it:
		g_main.gi.cprintf (ent, PRINT_HIGH, "unknown item: %s\n", s)
		return
	if not it.drop:
		g_main.gi.cprintf (ent, PRINT_HIGH, "Item is not dropable.\n")
		return
	index = g_items.ITEM_INDEX(it)
	if not ent.client.pers.inventory[index]:
		g_main.gi.cprintf (ent, PRINT_HIGH, "Out of item: %s\n", s)
		return

	it.drop (ent, it)


"""
=================
Cmd_Inven_f
=================
"""
def Cmd_Inven_f (ent):
	#int i
	#gclient_t *cl
	cl = ent.client

	cl.showscores = False
	cl.showhelp = False

	if cl.showinventory:
		cl.showinventory = False
		return

	cl.showinventory = True

	g_main.gi.WriteByte (svc_inventory)
	for i in range(MAX_ITEMS):
		g_main.gi.WriteShort (cl.pers.inventory[i])
	g_main.gi.unicast (ent, True)


"""
=================
Cmd_InvUse_f
=================
"""
def Cmd_InvUse_f (ent):
	#gitem_t *it
	ValidateSelectedItem (ent)

	if ent.client.pers.selected_item == -1:
		g_main.gi.cprintf (ent, PRINT_HIGH, "No item to use.\n")
		return

	it = g_items.itemlist[ent.client.pers.selected_item]
	if not it.use:
		g_main.gi.cprintf (ent, PRINT_HIGH, "Item is not usable.\n")
		return
	it.use (ent, it)


"""
=================
Cmd_WeapPrev_f
=================
"""
def Cmd_WeapPrev_f (ent):
	#gclient_t *cl
	#int i, index, selected_weapon
	#gitem_t *it
	cl = ent.client

	if not cl.pers.weapon:
		return

	selected_weapon = g_items.ITEM_INDEX(cl.pers.weapon)

	# scan  for the next valid one
	for i in range(1, MAX_ITEMS+1):
		index = (selected_weapon + i) % MAX_ITEMS
		if not cl.pers.inventory[index]:
			continue
		it = g_items.itemlist[index]
		if not it.use:
			continue
		if not (it.flags & IT_WEAPON):
			continue
		it.use (ent, it)
		if cl.pers.weapon == it:
			return	# successful


"""
=================
Cmd_WeapNext_f
=================
"""
def Cmd_WeapNext_f (ent):
	#gclient_t *cl
	#int i, index, selected_weapon
	#gitem_t *it
	cl = ent.client

	if not cl.pers.weapon:
		return

	selected_weapon = g_items.ITEM_INDEX(cl.pers.weapon)

	# scan  for the next valid one
	for i in range(1, MAX_ITEMS+1):
		index = (selected_weapon + MAX_ITEMS - i) % MAX_ITEMS
		if not cl.pers.inventory[index]:
			continue
		it = g_items.itemlist[index]
		if not it.use:
			continue
		if not (it.flags & IT_WEAPON):
			continue
		it.use (ent, it)
		if cl.pers.weapon == it:
			return	# successful


"""
=================
Cmd_WeapLast_f
=================
"""
def Cmd_WeapLast_f (ent):
	#gclient_t *cl
	#int index
	#gitem_t *it
	cl = ent.client

	if not cl.pers.weapon or not cl.pers.lastweapon:
		return

	index = g_items.ITEM_INDEX(cl.pers.lastweapon)
	if not cl.pers.inventory[index]:
		return
	it = g_items.itemlist[index]
	if not it.use:
		return
	if not (it.flags & IT_WEAPON):
		return
	it.use (ent, it)


"""
=================
Cmd_InvDrop_f
=================
"""
def Cmd_InvDrop_f (ent):
	#gitem_t *it
	ValidateSelectedItem (ent)

	if ent.client.pers.selected_item == -1:
		g_main.gi.cprintf (ent, PRINT_HIGH, "No item to drop.\n")
		return

	it = g_items.itemlist[ent.client.pers.selected_item]
	if not it.drop:
		g_main.gi.cprintf (ent, PRINT_HIGH, "Item is not dropable.\n")
		return
	it.drop (ent, it)


"""
=================
Cmd_Kill_f
=================
"""
def Cmd_Kill_f (ent):
	if (g_main.level.time - ent.client.respawn_time) < 5:
		return
	ent.flags &= ~FL_GODMODE
	ent.health = 0
	g_main.meansOfDeath = MOD_SUICIDE
	p_client.player_die (ent, ent, ent, 100000, vec3_origin)


"""
=================
Cmd_PutAway_f
=================
"""
def Cmd_PutAway_f (ent):
	ent.client.showscores = False
	ent.client.showhelp = False
	ent.client.showinventory = False


"""
==========
PlayerSort
==========
"""
def PlayerSort (a, b):
	#int anum, bnum
	anum = g_main.game.clients[a].ps.stats[STAT_FRAGS]
	bnum = g_main.game.clients[b].ps.stats[STAT_FRAGS]

	if anum < bnum:
		return -1
	if anum > bnum:
		return 1
	return 0


"""
=================
Cmd_Players_f
=================
"""
def Cmd_Players_f (ent):
	#int i, count
	#int index[256]
	#char small[64], large[1280]
	count = 0
	index = []
	for i in range(int(g_main.maxclients.value)):
		if g_main.game.clients[i].pers.connected:
			index.append(i)
			count += 1

	# sort by frags
	index = sorted(index, key=lambda i: g_main.game.clients[i].ps.stats[STAT_FRAGS])

	# print information
	large = ""

	for i in range(count):
		small = "%3i %s\n" % (
			g_main.game.clients[index[i]].ps.stats[STAT_FRAGS],
			g_main.game.clients[index[i]].pers.netname)
		if len(small) + len(large) > 1280 - 100:
			# can't print all of them in one packet
			large += "...\n"
			break
		large += small

	g_main.gi.cprintf (ent, PRINT_HIGH, "%s\n%i players\n" % (large, count))


"""
=================
Cmd_Wave_f
=================
"""
def Cmd_Wave_f (ent):
	#int i
	i = int(g_main.gi.argv(1))

	# can't wave when ducked
	if ent.client.ps.pmove.pm_flags & PMF_DUCKED:
		return

	if ent.client.anim_priority > ANIM_WAVE:
		return

	ent.client.anim_priority = ANIM_WAVE

	if i == 0:
		g_main.gi.cprintf (ent, PRINT_HIGH, "flipoff\n")
		ent.s.frame = FRAME_flip01-1
		ent.client.anim_end = FRAME_flip12
	elif i == 1:
		g_main.gi.cprintf (ent, PRINT_HIGH, "salute\n")
		ent.s.frame = FRAME_salute01-1
		ent.client.anim_end = FRAME_salute11
	elif i == 2:
		g_main.gi.cprintf (ent, PRINT_HIGH, "taunt\n")
		ent.s.frame = FRAME_taunt01-1
		ent.client.anim_end = FRAME_taunt17
	elif i == 3:
		g_main.gi.cprintf (ent, PRINT_HIGH, "wave\n")
		ent.s.frame = FRAME_wave01-1
		ent.client.anim_end = FRAME_wave11
	else:
		g_main.gi.cprintf (ent, PRINT_HIGH, "point\n")
		ent.s.frame = FRAME_point01-1
		ent.client.anim_end = FRAME_point12


"""
==================
Cmd_Say_f
==================
"""
def Cmd_Say_f (ent, team, arg0):
	#int i, j
	#edict_t *other
	#char *p
	#char text[2048]
	#gclient_t *cl
	if g_main.gi.argc() < 2 and not arg0:
		return

	if not (int(g_main.dmflags.value) & (DF_MODELTEAMS | DF_SKINTEAMS)):
		team = False

	if team:
		text = "(%s): " % ent.client.pers.netname
	else:
		text = "%s: " % ent.client.pers.netname

	if arg0:
		text += g_main.gi.argv(0)
		text += " "
		text += g_main.gi.args()
	else:
		p = g_main.gi.args()

		if p and p[0] == '"':
			p = p[1:-1] if len(p) >= 2 else ""

		text += p

	# don't let text be too long for malicious reasons
	if len(text) > 150:
		text = text[:150]

	text += "\n"

	if g_main.flood_msgs.value:
		cl = ent.client

		if g_main.level.time < cl.flood_locktill:
			g_main.gi.cprintf(ent, PRINT_HIGH, "You can't talk for %d more seconds\n",
				int(cl.flood_locktill - g_main.level.time))
			return
		i = cl.flood_whenhead - g_main.flood_msgs.value + 1
		if i < 0:
			i = 10 + i
		if cl.flood_when[i] and \
			g_main.level.time - cl.flood_when[i] < g_main.flood_persecond.value:
			cl.flood_locktill = g_main.level.time + g_main.flood_waitdelay.value
			g_main.gi.cprintf(ent, PRINT_CHAT, "Flood protection:  You can't talk for %d seconds.\n",
				int(g_main.flood_waitdelay.value))
			return
		cl.flood_whenhead = (cl.flood_whenhead + 1) % 10
		cl.flood_when[cl.flood_whenhead] = g_main.level.time

	if g_main.dedicated.value:
		g_main.gi.cprintf(None, PRINT_CHAT, "%s" % text)

	for j in range(1, g_main.game.maxclients+1):
		other = g_main.g_edicts[j]
		if not other.inuse:
			continue
		if not other.client:
			continue
		if team:
			if not OnSameTeam(ent, other):
				continue
		g_main.gi.cprintf(other, PRINT_CHAT, "%s" % text)


def Cmd_PlayerList_f(ent):
	#int i
	#char st[80]
	#char text[1400]
	#edict_t *e2
	text = ""
	for i in range(int(g_main.maxclients.value)):
		e2 = g_main.g_edicts[i+1]
		if not e2.inuse:
			continue

		enterframe = e2.client.resp.enterframe
		st = "%02d:%02d %4d %3d %s%s\n" % (
			(g_main.level.framenum - enterframe) / 600,
			((g_main.level.framenum - enterframe) % 600)/10,
			e2.client.ping,
			e2.client.resp.score,
			e2.client.pers.netname,
			" (spectator)" if e2.client.resp.spectator else "")
		if len(text) + len(st) > 1400 - 50:
			text += "And more...\n"
			g_main.gi.cprintf(ent, PRINT_HIGH, "%s" % text)
			return
		text += st
	g_main.gi.cprintf(ent, PRINT_HIGH, "%s" % text)


"""
=================
ClientCommand
=================
"""
def ClientCommand (ent):
	#char *cmd
	if not ent.client:
		return		# not fully in game yet

	cmd = g_main.gi.argv(0)

	if Q_stricmp (cmd, "players") == 0:
		Cmd_Players_f (ent)
		return
	if Q_stricmp (cmd, "say") == 0:
		Cmd_Say_f (ent, False, False)
		return
	if Q_stricmp (cmd, "say_team") == 0:
		Cmd_Say_f (ent, True, False)
		return
	if Q_stricmp (cmd, "score") == 0:
		p_hud.Cmd_Score_f (ent)
		return
	if Q_stricmp (cmd, "help") == 0:
		p_hud.Cmd_Help_f (ent)
		return

	if g_main.level.intermissiontime:
		return

	if Q_stricmp (cmd, "use") == 0:
		Cmd_Use_f (ent)
	elif Q_stricmp (cmd, "drop") == 0:
		Cmd_Drop_f (ent)
	elif Q_stricmp (cmd, "give") == 0:
		Cmd_Give_f (ent)
	elif Q_stricmp (cmd, "god") == 0:
		Cmd_God_f (ent)
	elif Q_stricmp (cmd, "notarget") == 0:
		Cmd_Notarget_f (ent)
	elif Q_stricmp (cmd, "noclip") == 0:
		Cmd_Noclip_f (ent)
	elif Q_stricmp (cmd, "inven") == 0:
		Cmd_Inven_f (ent)
	elif Q_stricmp (cmd, "invnext") == 0:
		SelectNextItem (ent, -1)
	elif Q_stricmp (cmd, "invprev") == 0:
		SelectPrevItem (ent, -1)
	elif Q_stricmp (cmd, "invnextw") == 0:
		SelectNextItem (ent, IT_WEAPON)
	elif Q_stricmp (cmd, "invprevw") == 0:
		SelectPrevItem (ent, IT_WEAPON)
	elif Q_stricmp (cmd, "invnextp") == 0:
		SelectNextItem (ent, IT_POWERUP)
	elif Q_stricmp (cmd, "invprevp") == 0:
		SelectPrevItem (ent, IT_POWERUP)
	elif Q_stricmp (cmd, "invuse") == 0:
		Cmd_InvUse_f (ent)
	elif Q_stricmp (cmd, "invdrop") == 0:
		Cmd_InvDrop_f (ent)
	elif Q_stricmp (cmd, "weapprev") == 0:
		Cmd_WeapPrev_f (ent)
	elif Q_stricmp (cmd, "weapnext") == 0:
		Cmd_WeapNext_f (ent)
	elif Q_stricmp (cmd, "weaplast") == 0:
		Cmd_WeapLast_f (ent)
	elif Q_stricmp (cmd, "kill") == 0:
		Cmd_Kill_f (ent)
	elif Q_stricmp (cmd, "putaway") == 0:
		Cmd_PutAway_f (ent)
	elif Q_stricmp (cmd, "wave") == 0:
		Cmd_Wave_f (ent)
	elif Q_stricmp(cmd, "playerlist") == 0:
		Cmd_PlayerList_f(ent)
	else:		# anything that doesn't match a command will be a chat
		Cmd_Say_f (ent, False, True)
