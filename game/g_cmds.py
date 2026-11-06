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

Game command processing.

=======================================================================
"""
from __future__ import annotations

import functools
from game import g_main
from game import g_utils
from game import g_items
from game import g_chase
from game import g_spawn
from common.header import shared
from common.shared import shared as shared_c
from common.shared.shared import Q_stricmp, Info_ValueForKey, vec3_origin
from common.header.shared import MAX_ITEMS, STAT_FRAGS, PMF_DUCKED, DF_MODELTEAMS, DF_SKINTEAMS, PRINT_HIGH, PRINT_CHAT
from game.header.local import IT_WEAPON, IT_AMMO, IT_ARMOR, IT_POWERUP, FL_GODMODE, FL_NOTARGET, MOVETYPE_NOCLIP, MOVETYPE_WALK, ANIM_WAVE, MOD_SUICIDE
from game.monster.misc import player as player_h
from game.header import local
from game.player import client as p_client
from game.player import hud as p_hud

"""
#include "header/local.h"
#include "monster/misc/player.h"
"""

def ClientTeam(ent, val_len: int): #const edict_t *, char *, size_t (returns static char *)

	# Q2PORT: C fills the caller's buffer and returns a pointer into it;
	# this returns (buffer, returned string)

	"""
	char *p;
	"""

	value = ""

	if not ent:

		return value, value


	if not ent.client:

		return value, value


	value = Info_ValueForKey(ent.client.pers.userinfo, "skin")[:val_len - 1] # Q_strlcpy
	p = value.find('/')

	if p < 0:

		return value, value


	if int(g_main.dmflags.value) & DF_MODELTEAMS:

		value = value[:p] # *p = 0
		return value, value


	return value, value[p + 1:]

def OnSameTeam(ent1, ent2)->bool: #const edict_t *, const edict_t * (returns qboolean)

	"""
	char ent1Team[512];
	char ent2Team[512];
	"""

	if not ent1 or not ent2:

		return False


	if not (int(g_main.dmflags.value) & (DF_MODELTEAMS | DF_SKINTEAMS)):

		return False


	ent1Team, _ = ClientTeam(ent1, 512)
	ent2Team, _ = ClientTeam(ent2, 512)

	if ent1Team != "" and ent1Team == ent2Team:

		return True


	return False

def SelectNextItem(cl, itflags: int)->int: #const gclient_t *, int (returns static int)

	"""
	int i, si;
	"""

	si = cl.pers.selected_item

	for i in range(1, g_items.itemlist_len + 1):

		#const gitem_t *it;
		#int index;

		index = (si + i) % g_items.itemlist_len

		if not cl.pers.inventory[index]:

			continue


		it = g_items.itemlist[index]

		if not it.use:

			continue


		if not (it.flags & itflags):

			continue


		return index


	return -1

def SelectNext(ent, itflags: int): #edict_t *, int (static)

	if not ent or not ent.client:

		return


	if ent.client.chase_target:

		g_chase.ChaseNext(ent)
		return


	ent.client.pers.selected_item = SelectNextItem(ent.client, itflags)

def SelectPrevItem(cl, itflags: int)->int: #const gclient_t *, int (returns static int)

	"""
	int i, si;
	"""

	si = cl.pers.selected_item

	for i in range(1, g_items.itemlist_len + 1):

		#const gitem_t *it;
		#int index;

		index = (si + g_items.itemlist_len - i) % g_items.itemlist_len

		if not cl.pers.inventory[index]:

			continue


		it = g_items.itemlist[index]

		if not it.use:

			continue


		if not (it.flags & itflags):

			continue


		return index


	return -1

def SelectPrev(ent, itflags: int): #edict_t *, int (static)

	if not ent or not ent.client:

		return


	if ent.client.chase_target:

		g_chase.ChasePrev(ent)
		return


	ent.client.pers.selected_item = SelectPrevItem(ent.client, -1) # sic, as in the C

def ValidateSelectedItem(cl): #gclient_t *

	"""
	const gitem_t *it;
	int si;
	"""

	if not cl:

		return


	si = cl.pers.selected_item
	it = g_items.GetItemByIndex(si)

	if not it or not it.use or \
		not cl.pers.inventory[si]:

		cl.pers.selected_item = SelectNextItem(cl, -1)

# =================================================================================

"""
 * Give items to a client
"""
def Cmd_Give_f(ent): #edict_t * (static)

	"""
	char *name;
	gitem_t *it;
	int index;
	int i;
	qboolean give_all;
	edict_t *it_ent;
	"""

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH,
				"You must run the server with '+set cheats 1' to enable this command.\n")
		return


	name = g_main.gi.args()

	if Q_stricmp(name, "all") == 0:

		give_all = True

	else:

		give_all = False


	if give_all or (Q_stricmp(g_main.gi.argv(1), "health") == 0):

		if g_main.gi.argc() == 3:

			ent.health = shared_c.atoi(g_main.gi.argv(2))
			ent.health = 1 if ent.health < 1 else ent.health

		else:

			ent.health = ent.max_health


		if not give_all:

			return



	if give_all or (Q_stricmp(name, "weapons") == 0):

		for i in range(g_items.itemlist_len):

			it = g_items.itemlist[i]

			if not it.pickup:

				continue


			if not (it.flags & IT_WEAPON):

				continue


			ent.client.pers.inventory[i] += 1


		if not give_all:

			return



	if give_all or (Q_stricmp(name, "ammo") == 0):

		for i in range(g_items.itemlist_len):

			it = g_items.itemlist[i]

			if not it.pickup:

				continue


			if not (it.flags & IT_AMMO):

				continue


			g_items.Add_Ammo(ent, it, 1000)


		if not give_all:

			return



	if give_all or (Q_stricmp(name, "armor") == 0):

		#const gitem_armor_t *info;

		it = g_items.FindItem("Jacket Armor")
		if it:

			ent.client.pers.inventory[local.ITEM_INDEX(it)] = 0


		it = g_items.FindItem("Combat Armor")
		if it:

			ent.client.pers.inventory[local.ITEM_INDEX(it)] = 0


		it = g_items.FindItem("Body Armor")
		if it:

			info = it.info
			ent.client.pers.inventory[local.ITEM_INDEX(it)] = info.max_count


		if not give_all:

			return



	if give_all or (Q_stricmp(name, "Power Shield") == 0):

		it = g_items.FindItem("Power Shield")
		if it:

			it_ent = g_utils.G_Spawn()
			it_ent.classname = it.classname
			g_items.SpawnItem(it_ent, it)
			g_items.Touch_Item(it_ent, ent, None, None)

			if it_ent.inuse:

				g_utils.G_FreeEdict(it_ent)



		if not give_all:

			return



	if give_all:

		for i in range(g_items.itemlist_len):

			it = g_items.itemlist[i]

			if not it.pickup:

				continue


			if it.flags & (IT_ARMOR | IT_WEAPON | IT_AMMO):

				continue


			ent.client.pers.inventory[i] = 1


		return


	it = g_items.FindItem(name)

	if not it:

		name = g_main.gi.argv(1)
		it = g_items.FindItem(name)

		if not it:

			g_main.gi.cprintf(ent, PRINT_HIGH, "unknown item\n")
			return



	if not it.pickup:

		g_main.gi.cprintf(ent, PRINT_HIGH, "non-pickup item\n")
		return


	index = local.ITEM_INDEX(it)

	if it.flags & IT_AMMO:

		if g_main.gi.argc() == 3:

			ent.client.pers.inventory[index] = shared_c.atoi(g_main.gi.argv(2))

		else:

			ent.client.pers.inventory[index] += it.quantity


	else:

		it_ent = g_utils.G_Spawn()
		it_ent.classname = it.classname
		g_items.SpawnItem(it_ent, it)
		g_items.Touch_Item(it_ent, ent, None, None)

		if it_ent.inuse:

			g_utils.G_FreeEdict(it_ent)

"""
 * Sets client to godmode
"""
def Cmd_God_f(ent): #edict_t * (static)

	"""
	char *msg;
	"""

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH,
				"You must run the server with '+set cheats 1' to enable this command.\n")
		return


	ent.flags ^= FL_GODMODE

	if not (ent.flags & FL_GODMODE):

		msg = "godmode OFF\n"

	else:

		msg = "godmode ON\n"


	g_main.gi.cprintf(ent, PRINT_HIGH, msg)

"""
 * Sets client to notarget
"""
def Cmd_Notarget_f(ent): #edict_t * (static)

	"""
	char *msg;
	"""

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH,
				"You must run the server with '+set cheats 1' to enable this command.\n")
		return


	ent.flags ^= FL_NOTARGET

	if not (ent.flags & FL_NOTARGET):

		msg = "notarget OFF\n"

	else:

		msg = "notarget ON\n"


	g_main.gi.cprintf(ent, PRINT_HIGH, msg)

"""
 * argv(0) noclip
"""
def Cmd_Noclip_f(ent): #edict_t * (static)

	"""
	char *msg;
	"""

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH,
				"You must run the server with '+set cheats 1' to enable this command.\n")
		return


	if ent.movetype == MOVETYPE_NOCLIP:

		ent.movetype = MOVETYPE_WALK
		msg = "noclip OFF\n"

	else:

		ent.movetype = MOVETYPE_NOCLIP
		msg = "noclip ON\n"


	g_main.gi.cprintf(ent, PRINT_HIGH, msg)

"""
 * Use an inventory item
"""
def Cmd_Use_f(ent): #edict_t * (static)

	"""
	int index;
	gitem_t *it;
	char *s;
	"""

	if not ent:

		return


	s = g_main.gi.args()
	it = g_items.FindItem(s)

	if not it:

		g_main.gi.cprintf(ent, PRINT_HIGH, "unknown item: %s\n", s)
		return


	if not it.use:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Item is not usable.\n")
		return


	index = local.ITEM_INDEX(it)

	if not ent.client.pers.inventory[index]:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Out of item: %s\n", s)
		return


	it.use(ent, it)

"""
 * Drop an inventory item
"""
def Cmd_Drop_f(ent): #edict_t * (static)

	"""
	int index;
	const gitem_t *it;
	char *s;
	"""

	if not ent:

		return


	s = g_main.gi.args()
	it = g_items.FindItem(s)

	if not it:

		g_main.gi.cprintf(ent, PRINT_HIGH, "unknown item: %s\n", s)
		return


	if not it.drop:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Item is not dropable.\n")
		return


	index = local.ITEM_INDEX(it)

	if not ent.client.pers.inventory[index]:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Out of item: %s\n", s)
		return


	it.drop(ent, it)

"""
 * Display the scoreboard
"""
def Cmd_Score_f(ent): #edict_t * (static)

	if not ent:

		return


	ent.client.showinventory = False
	ent.client.showhelp = False

	if not g_main.deathmatch.value and not g_main.coop.value:

		return


	if ent.client.showscores:

		ent.client.showscores = False
		return


	ent.client.showscores = True
	p_hud.DeathmatchScoreboardMessage(ent, ent.enemy)
	g_main.gi.unicast(ent, True)

"""
 * Display the current help message
"""
def Cmd_Help_f(ent): #edict_t *

	if not ent:

		return


	# this is for backwards compatibility
	if g_main.deathmatch.value:

		Cmd_Score_f(ent)
		return


	ent.client.showinventory = False
	ent.client.showscores = False

	if ent.client.showhelp:

		ent.client.showhelp = False
		return


	ent.client.showhelp = True
	ent.client.pers.helpchanged = 0
	p_hud.HelpComputerMessage(ent)
	g_main.gi.unicast(ent, True)

def Cmd_Inven_f(ent): #edict_t * (static)

	"""
	gclient_t *cl;
	"""

	if not ent:

		return


	cl = ent.client

	cl.showscores = False
	cl.showhelp = False

	if cl.showinventory:

		cl.showinventory = False
		return


	cl.showinventory = True

	p_hud.InventoryMessage(ent)
	g_main.gi.unicast(ent, True)

def Cmd_InvUse_f(ent): #edict_t * (static)

	"""
	gitem_t *it;
	"""

	if not ent:

		return


	ValidateSelectedItem(ent.client)

	if ent.client.pers.selected_item == -1:

		g_main.gi.cprintf(ent, PRINT_HIGH, "No item to use.\n")
		return


	it = g_items.itemlist[ent.client.pers.selected_item]

	if not it.use:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Item is not usable.\n")
		return


	it.use(ent, it)

def Cmd_WeapPrev_f(ent): #edict_t * (static)

	"""
	gclient_t *cl;
	int i;
	const gitem_t *it;
	int selected_weapon;
	"""

	if not ent:

		return


	cl = ent.client

	if g_main.g_quick_weap.value and cl.newweapon:

		it = cl.newweapon

	elif cl.pers.weapon:

		it = cl.pers.weapon

	else:

		return


	selected_weapon = local.ITEM_INDEX(it)

	# scan for the next valid one
	for i in range(1, g_items.itemlist_len + 1):

		#int index;

		index = (selected_weapon + g_items.itemlist_len - i) % g_items.itemlist_len

		if not cl.pers.inventory[index]:

			continue


		it = g_items.itemlist[index]

		if not it.use or not (it.flags & IT_WEAPON):

			continue


		it.use(ent, it)

		if cl.newweapon == it:

			if g_main.g_quick_weap.value:

				cl.ps.stats[shared.STAT_PICKUP_ICON] = g_main.gi.imageindex(cl.newweapon.icon)
				cl.ps.stats[shared.STAT_PICKUP_STRING] = shared.CS_ITEMS + local.ITEM_INDEX(cl.newweapon)
				cl.pickup_msg_time = g_main.level.time + 0.9

			return # successful

def Cmd_WeapNext_f(ent): #edict_t * (static)

	"""
	gclient_t *cl;
	int i;
	const gitem_t *it;
	int selected_weapon;
	"""

	if not ent:

		return


	cl = ent.client

	if g_main.g_quick_weap.value and cl.newweapon:

		it = cl.newweapon

	elif cl.pers.weapon:

		it = cl.pers.weapon

	else:

		return


	selected_weapon = local.ITEM_INDEX(it)

	# scan for the next valid one
	for i in range(1, g_items.itemlist_len + 1):

		#int index;

		index = (selected_weapon + i) % g_items.itemlist_len

		if not cl.pers.inventory[index]:

			continue


		it = g_items.itemlist[index]

		if not it.use or not (it.flags & IT_WEAPON):

			continue


		it.use(ent, it)

		if cl.newweapon == it:

			if g_main.g_quick_weap.value:

				cl.ps.stats[shared.STAT_PICKUP_ICON] = g_main.gi.imageindex(cl.newweapon.icon)
				cl.ps.stats[shared.STAT_PICKUP_STRING] = shared.CS_ITEMS + local.ITEM_INDEX(cl.newweapon)
				cl.pickup_msg_time = g_main.level.time + 0.9

			return # successful

def Cmd_WeapLast_f(ent): #edict_t * (static)

	"""
	gclient_t *cl;
	int index;
	gitem_t *it;
	"""

	if not ent:

		return


	cl = ent.client

	if not cl.pers.weapon or not cl.pers.lastweapon:

		return


	index = local.ITEM_INDEX(cl.pers.lastweapon)

	if not cl.pers.inventory[index]:

		return


	it = g_items.itemlist[index]

	if not it.use:

		return


	if not (it.flags & IT_WEAPON):

		return


	it.use(ent, it)

def Cmd_InvDrop_f(ent): #edict_t * (static)

	"""
	gitem_t *it;
	"""

	if not ent:

		return


	ValidateSelectedItem(ent.client)

	if ent.client.pers.selected_item == -1:

		g_main.gi.cprintf(ent, PRINT_HIGH, "No item to drop.\n")
		return


	it = g_items.itemlist[ent.client.pers.selected_item]

	if not it.drop:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Item is not dropable.\n")
		return


	it.drop(ent, it)

def Cmd_Kill_f(ent): #edict_t * (static)

	if not ent:

		return


	if ((g_main.level.time - ent.client.respawn_time) < 5) or \
		(ent.client.resp.spectator):

		return


	ent.flags &= ~FL_GODMODE
	ent.health = 0
	g_main.meansOfDeath = MOD_SUICIDE
	p_client.player_die(ent, ent, ent, 100000, vec3_origin)

def Cmd_PutAway_f(ent): #edict_t * (static)

	if not ent:

		return


	ent.client.showscores = False
	ent.client.showhelp = False
	ent.client.showinventory = False

def PlayerSort(a, b)->int: #void const *, void const * (returns static int)

	"""
	int anum, bnum;
	"""

	if a is None or b is None:

		return 0


	anum = a
	bnum = b

	anum = g_main.game.clients[anum].ps.stats[STAT_FRAGS]
	bnum = g_main.game.clients[bnum].ps.stats[STAT_FRAGS]

	if anum < bnum:

		return -1


	if anum > bnum:

		return 1


	return 0

def Cmd_Players_f(ent): #edict_t * (static)

	"""
	int i;
	int count;
	char small[64];
	char large[1280];
	int index[256] = {0};
	"""

	if not ent:

		return


	count = 0
	index = []

	for i in range(int(g_main.maxclients.value)):

		if g_main.game.clients[i].pers.connected:

			index.append(i)
			count += 1



	# sort by frags
	index.sort(key=functools.cmp_to_key(PlayerSort)) # qsort(index, count, sizeof(index[0]), PlayerSort);

	# print information
	large = ""

	for i in range(count):

		small = ("%3i %s\n" % (g_main.game.clients[index[i]].ps.stats[STAT_FRAGS],
				g_main.game.clients[index[i]].pers.netname))[:64 - 1]

		if len(small) + len(large) > 1280 - 100:

			# can't print all of them in one packet
			large += "...\n"
			break


		large += small


	g_main.gi.cprintf(ent, PRINT_HIGH, "%s\n%i players\n", large, count)

def Cmd_Wave_f(ent): #edict_t * (static)

	"""
	int i;
	"""

	if not ent:

		return


	i = shared_c.atoi(g_main.gi.argv(1))

	# can't wave when ducked
	if ent.client.ps.pmove.pm_flags & PMF_DUCKED:

		return


	if ent.client.anim_priority > ANIM_WAVE:

		return


	ent.client.anim_priority = ANIM_WAVE

	if i == 0:

		g_main.gi.cprintf(ent, PRINT_HIGH, "flipoff\n")
		ent.s.frame = player_h.FRAME_flip01 - 1
		ent.client.anim_end = player_h.FRAME_flip12

	elif i == 1:

		g_main.gi.cprintf(ent, PRINT_HIGH, "salute\n")
		ent.s.frame = player_h.FRAME_salute01 - 1
		ent.client.anim_end = player_h.FRAME_salute11

	elif i == 2:

		g_main.gi.cprintf(ent, PRINT_HIGH, "taunt\n")
		ent.s.frame = player_h.FRAME_taunt01 - 1
		ent.client.anim_end = player_h.FRAME_taunt17

	elif i == 3:

		g_main.gi.cprintf(ent, PRINT_HIGH, "wave\n")
		ent.s.frame = player_h.FRAME_wave01 - 1
		ent.client.anim_end = player_h.FRAME_wave11

	else: # case 4: default:

		g_main.gi.cprintf(ent, PRINT_HIGH, "point\n")
		ent.s.frame = player_h.FRAME_point01 - 1
		ent.client.anim_end = player_h.FRAME_point12

def flooded(ent)->bool: #edict_t * (returns static qboolean)

	"""
	gclient_t *cl;
	int i;
	int num_msgs;
	int mx;
	"""

	if not ent:

		return False


	if not g_main.deathmatch.value and not g_main.coop.value:

		return False


	num_msgs = int(g_main.flood_msgs.value)
	if num_msgs <= 0:

		return False


	cl = ent.client
	mx = len(cl.flood_when) # ARRLEN(cl->flood_when)

	if num_msgs > mx:

		g_main.gi.dprintf("flood_msgs lowered to max: 10\n")

		num_msgs = mx
		g_main.gi.cvar_forceset("flood_msgs", "10")


	if g_main.level.time < cl.flood_locktill:

		g_main.gi.cprintf(ent, PRINT_HIGH, "You can't talk for %d more seconds\n",
			int(cl.flood_locktill - g_main.level.time))

		return True


	i = (cl.flood_whenhead - num_msgs) + 1

	if i < 0:

		i += mx


	if cl.flood_when[i] and \
		(g_main.level.time - cl.flood_when[i]) < g_main.flood_persecond.value:

		cl.flood_locktill = g_main.level.time + g_main.flood_waitdelay.value

		g_main.gi.cprintf(ent, PRINT_CHAT,
			"Flood protection: You can't talk for %d seconds.\n",
			int(g_main.flood_waitdelay.value))

		return True


	cl.flood_whenhead = (cl.flood_whenhead + 1) % mx
	cl.flood_when[cl.flood_whenhead] = g_main.level.time

	return False

def Cmd_Say_f(ent, team: bool, arg0: bool): #edict_t *, qboolean, qboolean (static)

	"""
	int j;
	char *p;
	char text[2048];
	"""

	if not ent:

		return


	if (g_main.gi.argc() < 2) and not arg0:

		return


	if flooded(ent):

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

		if p[0:1] == '"':

			p = p[1:]
			p = p[:-1] # p[strlen(p) - 1] = 0;


		text += p


	text = text[:2048 - 1] # Q_strlcat into char text[2048]

	# don't let text be too long for malicious reasons
	if len(text) > 150:

		text = text[:150]


	text += "\n"

	if g_main.dedicated.value:

		g_main.gi.cprintf(None, PRINT_CHAT, "%s", text)


	for j in range(1, g_main.game.maxclients + 1):

		#edict_t *other;

		other = g_main.g_edicts[j]

		if not other.inuse:

			continue


		if not other.client:

			continue


		if team:

			if not OnSameTeam(ent, other):

				continue



		g_main.gi.cprintf(other, PRINT_CHAT, "%s", text)

def Cmd_PlayerList_f(ent): #edict_t * (static)

	"""
	int i;
	char text[1400];
	edict_t *e2;
	"""

	if not ent:

		return


	# connect time, ping, score, name
	text = ""

	for i in range(int(g_main.maxclients.value)):

		e2 = g_main.g_edicts[1 + i]

		#size_t text_len;
		#char st_text[80];

		if not e2.inuse:

			continue


		st_text = ("%02d:%02d %4d %3d %s%s\n" % (
				(g_main.level.framenum - e2.client.resp.enterframe) // 600,
				((g_main.level.framenum - e2.client.resp.enterframe) % 600) // 10,
				e2.client.ping,
				e2.client.resp.score,
				e2.client.pers.netname,
				" (spectator)" if e2.client.resp.spectator else ""))[:80 - 1]

		text_len = len(text)

		if (text_len + len(st_text)) > (1400 - 50):

			text += "And more...\n"
			g_main.gi.cprintf(ent, PRINT_HIGH, "%s", text)
			return


		text += st_text


	g_main.gi.cprintf(ent, PRINT_HIGH, "%s", text)

def Cmd_Teleport_f(ent): #edict_t * (static)

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH, "You must run the server with '+set cheats 1' to enable this command.\n")
		return


	if g_main.gi.argc() != 4:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Usage: teleport x y z\n")
		return


	# Unlink it to prevent unwanted interactions with
	# other entities. This works because linkentity()
	# uses the first available slot and the player is
	# always at postion 0.
	g_main.gi.unlinkentity(ent)

	# Set new position
	ent.s.origin[0] = shared_c.atof(g_main.gi.argv(1))
	ent.s.origin[1] = shared_c.atof(g_main.gi.argv(2))
	ent.s.origin[2] = shared_c.atof(g_main.gi.argv(3)) + 10.0

	# Remove velocity and keep the entity briefly in place
	# to give the server and clients time to catch up.
	shared.VectorClear(ent.velocity)
	ent.client.ps.pmove.pm_time = 20
	ent.client.ps.pmove.pm_flags |= shared.PMF_TIME_TELEPORT

	# Remove viewangles. They'll be recalculated
	# by the client at the next frame.
	shared.VectorClear(ent.s.angles)
	shared.VectorClear(ent.client.ps.viewangles)
	shared.VectorClear(ent.client.v_angle)

	# Telefrag everything that's in the target location.
	g_utils.KillBox(ent)

	# And link it back in.
	g_main.gi.linkentity(ent)

def Cmd_SpawnEntity_f(ent): #edict_t * (static)

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH,
			"You must run the server with '+set cheats 1' to enable this command.\n")
		return


	if g_main.gi.argc() < 5 or g_main.gi.argc() > 9:

		g_main.gi.cprintf(ent, PRINT_HIGH,
			"Usage: spawnentity classname x y z <angle_x angle_y angle_z> <flags>\n")
		return


	ent = g_utils.G_Spawn()

	# set position
	ent.s.origin[0] = shared_c.atof(g_main.gi.argv(2))
	ent.s.origin[1] = shared_c.atof(g_main.gi.argv(3))
	ent.s.origin[2] = shared_c.atof(g_main.gi.argv(4))
	# angles
	if g_main.gi.argc() >= 8:

		ent.s.angles[0] = shared_c.atof(g_main.gi.argv(5))
		ent.s.angles[1] = shared_c.atof(g_main.gi.argv(6))
		ent.s.angles[2] = shared_c.atof(g_main.gi.argv(7))

	# flags
	if g_main.gi.argc() >= 9:

		ent.spawnflags = shared_c.atoi(g_main.gi.argv(8))


	ent.classname = g_utils.G_CopyString(g_main.gi.argv(1))

	g_spawn.ED_CallSpawn(ent)

def Cmd_SpawnOnStartByClass(classname: str, origin): #const char *, const vec3_t (static)

	opponent = g_utils.G_Spawn()

	# set position
	opponent.s.origin[0] = origin[0]
	opponent.s.origin[1] = origin[1]
	opponent.s.origin[2] = origin[2]
	# and class
	opponent.classname = g_utils.G_CopyString(classname)

	g_spawn.ED_CallSpawn(opponent)

	g_main.gi.dprintf("Spawned entity at %f %f %f\n",
		origin[0], origin[1], origin[2])

def Cmd_SpawnOnStart_f(ent): #edict_t * (static)

	"""
	edict_t *cur = NULL;
	"""
	cur = None

	if not ent:

		return


	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH,
			"You must run the server with '+set cheats 1' to enable this command.\n")
		return


	if g_main.gi.argc() != 2:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Usage: spawnonstart classname\n")
		return


	while True:

		cur = g_utils.G_Find(cur, local.FOFS("classname"), "info_player_deathmatch")
		if cur is None:

			break


		Cmd_SpawnOnStartByClass(g_main.gi.argv(1), cur.s.origin)


	while True:

		cur = g_utils.G_Find(cur, local.FOFS("classname"), "info_player_coop")
		if cur is None:

			break


		Cmd_SpawnOnStartByClass(g_main.gi.argv(1), cur.s.origin)


	while True:

		cur = g_utils.G_Find(cur, local.FOFS("classname"), "info_player_start")
		if cur is None:

			break


		Cmd_SpawnOnStartByClass(g_main.gi.argv(1), cur.s.origin)

def Cmd_ListEntities_f(ent): #edict_t * (static)

	if (g_main.deathmatch.value or g_main.coop.value) and not g_main.sv_cheats.value:

		g_main.gi.cprintf(ent, PRINT_HIGH, "You must run the server with '+set cheats 1' to enable this command.\n")
		return


	if g_main.gi.argc() < 2:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Usage: listentities <all|ammo|items|keys|monsters|weapons>\n")
		return


	# What to print?
	all_ = False
	ammo = False
	items = False
	keys = False
	monsters = False
	weapons = False

	for i in range(1, g_main.gi.argc()):

		arg = g_main.gi.argv(i)

		if Q_stricmp(arg, "all") == 0:

			all_ = True

		elif Q_stricmp(arg, "ammo") == 0:

			ammo = True

		elif Q_stricmp(arg, "items") == 0:

			items = True

		elif Q_stricmp(arg, "keys") == 0:

			keys = True

		elif Q_stricmp(arg, "monsters") == 0:

			monsters = True

		elif Q_stricmp(arg, "weapons") == 0:

			weapons = True

		else:

			g_main.gi.cprintf(ent, PRINT_HIGH, "Usage: listentities <all|ammo|items|keys|monsters|weapons>\n")



	# Print what's requested.
	for i in range(g_main.glob.num_edicts):

		cur = g_main.g_edicts[i]
		print_ = False

		# Ensure that the entity is valid.
		if not cur.classname:

			continue


		if all_:

			print_ = True

		else:

			if ammo:

				if cur.classname[:5] == "ammo_":

					print_ = True



			if items:

				if cur.classname[:5] == "item_":

					print_ = True



			if keys:

				if cur.classname[:4] == "key_":

					print_ = True



			if monsters:

				if cur.classname[:8] == "monster_":

					print_ = True



			if weapons:

				if cur.classname[:7] == "weapon_":

					print_ = True




		if print_:

			# We use dprintf() because cprintf() may flood the server...
			g_main.gi.dprintf("%s: %f %f %f\n", cur.classname, cur.s.origin[0], cur.s.origin[1], cur.s.origin[2])

def get_ammo_usage(weap)->int: #const gitem_t * (returns static int)

	if not weap:

		return 0


	# handles grenades and tesla which only use 1 ammo per shot
	# have to check this because they don't store their ammo usage in weap->quantity
	if weap.flags & IT_AMMO:

		return 1


	# weapons store their ammo usage in the quantity field
	return weap.quantity

def cycle_weapon(ent): #edict_t * (returns static gitem_t *)

	"""
	gclient_t *cl;
	gitem_t *noammo_fallback;
	gitem_t *noweap_fallback;
	int i;
	int start;
	int num_weaps;
	const char *weapname = NULL;
	"""
	weapname = None

	if not ent:

		return None


	cl = ent.client

	if not cl:

		return None


	num_weaps = g_main.gi.argc()

	# find where we want to start the search for the next eligible weapon
	if cl.newweapon:

		weapname = cl.newweapon.classname

	elif cl.pers.weapon:

		weapname = cl.pers.weapon.classname


	if weapname:

		i = 1
		while i < num_weaps:

			if Q_stricmp(weapname, g_main.gi.argv(i)) == 0:

				break


			i += 1


		i += 1

		if i >= num_weaps:

			i = 1


	else:

		i = 1


	start = i
	noammo_fallback = None
	noweap_fallback = None

	# find the first eligible weapon in the list we can switch to
	while True:

		#gitem_t *weap;

		weap = g_items.FindItemByClassname(g_main.gi.argv(i))

		if weap and weap != cl.pers.weapon and (weap.flags & IT_WEAPON) and weap.use:

			if cl.pers.inventory[local.ITEM_INDEX(weap)] > 0:

				if weap.ammo:

					#const gitem_t *ammo;

					ammo = g_items.FindItem(weap.ammo)
					if ammo:

						if cl.pers.inventory[local.ITEM_INDEX(ammo)] >= get_ammo_usage(weap):

							return weap


						if not noammo_fallback:

							noammo_fallback = weap



				else:

					return weap


			elif not noweap_fallback:

				noweap_fallback = weap



		i += 1

		if i >= num_weaps:

			i = 1


		if i == start: # } while (i != start);

			break



	# if no weapon was found, the fallbacks will be used for
	# printing the appropriate error message to the console

	if noammo_fallback:

		return noammo_fallback


	return noweap_fallback

def Cmd_CycleWeap_f(ent): #edict_t * (static)

	"""
	gitem_t *weap;
	gclient_t *cl;
	int num_weaps;
	"""

	if not ent:

		return


	num_weaps = g_main.gi.argc()
	if num_weaps <= 1:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Usage: cycleweap classname1 classname2 .. classnameN\n")
		return


	weap = cycle_weapon(ent)
	if not weap: return

	cl = ent.client
	if cl.pers.inventory[local.ITEM_INDEX(weap)] <= 0:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Out of item: %s\n", weap.pickup_name)
		return


	weap.use(ent, weap)
	if num_weaps > 3 and cl.newweapon == weap:

		cl.ps.stats[shared.STAT_PICKUP_ICON] = g_main.gi.imageindex(weap.icon)
		cl.ps.stats[shared.STAT_PICKUP_STRING] = shared.CS_ITEMS + local.ITEM_INDEX(weap)
		cl.pickup_msg_time = g_main.level.time + 0.7

def preferred_weapon(ent): #const edict_t * (returns static gitem_t *)

	"""
	const gclient_t *cl;
	gitem_t *noammo_fallback;
	gitem_t *noweap_fallback;
	int i;
	int num_weaps;
	"""

	if not ent:

		return None


	cl = ent.client

	if not cl:

		return None


	num_weaps = g_main.gi.argc()
	noammo_fallback = None
	noweap_fallback = None

	# find the first eligible weapon in the list we can switch to
	for i in range(1, num_weaps):

		#gitem_t *weap;

		weap = g_items.FindItemByClassname(g_main.gi.argv(i))

		if weap and (weap.flags & IT_WEAPON) and weap.use:

			if cl.pers.inventory[local.ITEM_INDEX(weap)] > 0:

				if weap.ammo:

					#const gitem_t *ammo;

					ammo = g_items.FindItem(weap.ammo)
					if ammo:

						if cl.pers.inventory[local.ITEM_INDEX(ammo)] >= get_ammo_usage(weap):

							return weap


						if not noammo_fallback:

							noammo_fallback = weap



				else:

					return weap


			elif not noweap_fallback:

				noweap_fallback = weap




	# if no weapon was found, the fallbacks will be used for
	# printing the appropriate error message to the console

	if noammo_fallback:

		return noammo_fallback


	return noweap_fallback

def Cmd_PrefWeap_f(ent): #edict_t * (static)

	"""
	gitem_t *weap;
	"""

	if not ent:

		return


	if g_main.gi.argc() <= 1:

		g_main.gi.cprintf(ent, PRINT_HIGH, "Usage: prefweap classname1 classname2 .. classnameN\n")
		return


	weap = preferred_weapon(ent)
	if weap:

		if ent.client.pers.inventory[local.ITEM_INDEX(weap)] <= 0:

			g_main.gi.cprintf(ent, PRINT_HIGH, "Out of item: %s\n", weap.pickup_name)

		else:

			weap.use(ent, weap)

def ClientCommand(ent): #edict_t *

	"""
	const char *cmd;
	"""

	if not ent:

		return


	if not ent.client:

		return # not fully in game yet


	cmd = g_main.gi.argv(0)

	if Q_stricmp(cmd, "players") == 0:

		Cmd_Players_f(ent)
		return


	if Q_stricmp(cmd, "say") == 0:

		Cmd_Say_f(ent, False, False)
		return


	if Q_stricmp(cmd, "say_team") == 0:

		Cmd_Say_f(ent, True, False)
		return


	if Q_stricmp(cmd, "score") == 0:

		Cmd_Score_f(ent)
		return


	if Q_stricmp(cmd, "help") == 0:

		Cmd_Help_f(ent)
		return


	if g_main.level.intermissiontime:

		return


	if Q_stricmp(cmd, "use") == 0:

		Cmd_Use_f(ent)

	elif Q_stricmp(cmd, "drop") == 0:

		Cmd_Drop_f(ent)

	elif Q_stricmp(cmd, "give") == 0:

		Cmd_Give_f(ent)

	elif Q_stricmp(cmd, "god") == 0:

		Cmd_God_f(ent)

	elif Q_stricmp(cmd, "notarget") == 0:

		Cmd_Notarget_f(ent)

	elif Q_stricmp(cmd, "noclip") == 0:

		Cmd_Noclip_f(ent)

	elif Q_stricmp(cmd, "inven") == 0:

		Cmd_Inven_f(ent)

	elif Q_stricmp(cmd, "invnext") == 0:

		SelectNext(ent, -1)

	elif Q_stricmp(cmd, "invprev") == 0:

		SelectPrev(ent, -1)

	elif Q_stricmp(cmd, "invnextw") == 0:

		SelectNext(ent, IT_WEAPON)

	elif Q_stricmp(cmd, "invprevw") == 0:

		SelectPrev(ent, IT_WEAPON)

	elif Q_stricmp(cmd, "invnextp") == 0:

		SelectNext(ent, IT_POWERUP)

	elif Q_stricmp(cmd, "invprevp") == 0:

		SelectPrev(ent, IT_POWERUP)

	elif Q_stricmp(cmd, "invuse") == 0:

		Cmd_InvUse_f(ent)

	elif Q_stricmp(cmd, "invdrop") == 0:

		Cmd_InvDrop_f(ent)

	elif Q_stricmp(cmd, "weapprev") == 0:

		Cmd_WeapPrev_f(ent)

	elif Q_stricmp(cmd, "weapnext") == 0:

		Cmd_WeapNext_f(ent)

	elif Q_stricmp(cmd, "weaplast") == 0:

		Cmd_WeapLast_f(ent)

	elif Q_stricmp(cmd, "kill") == 0:

		Cmd_Kill_f(ent)

	elif Q_stricmp(cmd, "putaway") == 0:

		Cmd_PutAway_f(ent)

	elif Q_stricmp(cmd, "wave") == 0:

		Cmd_Wave_f(ent)

	elif Q_stricmp(cmd, "playerlist") == 0:

		Cmd_PlayerList_f(ent)

	elif Q_stricmp(cmd, "teleport") == 0:

		Cmd_Teleport_f(ent)

	elif Q_stricmp(cmd, "spawnentity") == 0:

		Cmd_SpawnEntity_f(ent)

	elif Q_stricmp(cmd, "spawnonstart") == 0:

		Cmd_SpawnOnStart_f(ent)

	elif Q_stricmp(cmd, "listentities") == 0:

		Cmd_ListEntities_f(ent)

	elif Q_stricmp(cmd, "cycleweap") == 0:

		Cmd_CycleWeap_f(ent)

	elif Q_stricmp(cmd, "prefweap") == 0:

		Cmd_PrefWeap_f(ent)

	else: # anything that doesn't match a command will be a chat

		Cmd_Say_f(ent, False, True)
