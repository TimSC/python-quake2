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
import random as _r
from game import q_shared, g_main, g_utils, g_items, p_client
from game.game import solid_t
from game.q_shared import pmtype_t
from game.g_local import FL_POWER_ARMOR, IT_KEY, CENTER_HANDED, svc_layout
from game.q_shared import (RDF_UNDERWATER, MAX_ITEMS, CHAN_ITEM, ATTN_NORM,
	STAT_HEALTH_ICON, STAT_HEALTH, STAT_AMMO_ICON, STAT_AMMO, STAT_ARMOR_ICON,
	STAT_ARMOR, STAT_PICKUP_ICON, STAT_PICKUP_STRING, STAT_TIMER_ICON,
	STAT_TIMER, STAT_SELECTED_ICON, STAT_SELECTED_ITEM, STAT_LAYOUTS,
	STAT_FRAGS, STAT_HELPICON, STAT_SPECTATOR, STAT_CHASE, CS_PLAYERSKINS)
"""
#include "g_local.h"
"""


"""
======================================================================

INTERMISSION

======================================================================
"""

def MoveClientToIntermission (ent): #edict_t *
	if int(g_main.deathmatch.value) or int(g_main.coop.value):
		ent.client.showscores = True
	q_shared.VectorCopy (g_main.level.intermission_origin, ent.s.origin)
	ent.client.ps.pmove.origin[0] = g_main.level.intermission_origin[0]*8
	ent.client.ps.pmove.origin[1] = g_main.level.intermission_origin[1]*8
	ent.client.ps.pmove.origin[2] = g_main.level.intermission_origin[2]*8
	q_shared.VectorCopy (g_main.level.intermission_angle, ent.client.ps.viewangles)
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

	# add the layout
	if int(g_main.deathmatch.value) or int(g_main.coop.value):
		DeathmatchScoreboardMessage (ent, None)
		g_main.gi.unicast (ent, True)

	"""
	if (deathmatch->value || coop->value)
		ent->client->showscores = true;
	VectorCopy (level.intermission_origin, ent->s.origin);
	ent->client->ps.pmove.origin[0] = level.intermission_origin[0]*8;
	ent->client->ps.pmove.origin[1] = level.intermission_origin[1]*8;
	ent->client->ps.pmove.origin[2] = level.intermission_origin[2]*8;
	VectorCopy (level.intermission_angle, ent->client->ps.viewangles);
	ent->client->ps.pmove.pm_type = PM_FREEZE;
	ent->client->ps.gunindex = 0;
	ent->client->ps.blend[3] = 0;
	ent->client->ps.rdflags &= ~RDF_UNDERWATER;

	// clean up powerup info
	ent->client->quad_framenum = 0;
	ent->client->invincible_framenum = 0;
	ent->client->breather_framenum = 0;
	ent->client->enviro_framenum = 0;
	ent->client->grenade_blew_up = false;
	ent->client->grenade_time = 0;

	ent->viewheight = 0;
	ent->s.modelindex = 0;
	ent->s.modelindex2 = 0;
	ent->s.modelindex3 = 0;
	ent->s.modelindex = 0;
	ent->s.effects = 0;
	ent->s.sound = 0;
	ent->solid = SOLID_NOT;

	// add the layout

	if (deathmatch->value || coop->value)
	{
		DeathmatchScoreboardMessage (ent, NULL);
		gi.unicast (ent, true);
	}
	"""


def BeginIntermission (targ): #edict_t *
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
				for n in range(MAX_ITEMS):
					if g_items.itemlist[n].flags & IT_KEY:
						client.client.pers.inventory[n] = 0
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
		i = _r.randint(0, 2147483647) & 3
		while i:
			ent = g_utils.G_Find (ent, "classname", "info_player_intermission")
			if not ent:		# wrap around the list
				ent = g_utils.G_Find (ent, "classname", "info_player_intermission")
			i -= 1

	q_shared.VectorCopy (ent.s.origin, g_main.level.intermission_origin)
	q_shared.VectorCopy (ent.s.angles, g_main.level.intermission_angle)

	# move all clients to the intermission point
	for i in range(int(g_main.maxclients.value)):
		client = g_main.g_edicts[1 + i]
		if not client.inuse:
			continue
		MoveClientToIntermission (client)

	"""
	int		i, n;
	edict_t	*ent, *client;

	if (level.intermissiontime)
		return;		// already activated

	game.autosaved = false;

	// respawn any dead clients
	for (i=0 ; i<maxclients->value ; i++)
	{
		client = g_edicts + 1 + i;
		if (!client->inuse)
			continue;
		if (client->health <= 0)
			respawn(client);
	}

	level.intermissiontime = level.time;
	level.changemap = targ->map;

	if (strstr(level.changemap, "*"))
	{
		if (coop->value)
		{
			for (i=0 ; i<maxclients->value ; i++)
			{
				client = g_edicts + 1 + i;
				if (!client->inuse)
					continue;
				// strip players of all keys between units
				for (n = 0; n < MAX_ITEMS; n++)
				{
					if (itemlist[n].flags & IT_KEY)
						client->client->pers.inventory[n] = 0;
				}
			}
		}
	}
	else
	{
		if (!deathmatch->value)
		{
			level.exitintermission = 1;		// go immediately to the next level
			return;
		}
	}

	level.exitintermission = 0;

	// find an intermission spot
	ent = G_Find (NULL, FOFS(classname), "info_player_intermission");
	if (!ent)
	{	// the map creator forgot to put in an intermission point...
		ent = G_Find (NULL, FOFS(classname), "info_player_start");
		if (!ent)
			ent = G_Find (NULL, FOFS(classname), "info_player_deathmatch");
	}
	else
	{	// chose one of four spots
		i = rand() & 3;
		while (i--)
		{
			ent = G_Find (ent, FOFS(classname), "info_player_intermission");
			if (!ent)	// wrap around the list
				ent = G_Find (ent, FOFS(classname), "info_player_intermission");
		}
	}

	VectorCopy (ent->s.origin, level.intermission_origin);
	VectorCopy (ent->s.angles, level.intermission_angle);

	// move all clients to the intermission point
	for (i=0 ; i<maxclients->value ; i++)
	{
		client = g_edicts + 1 + i;
		if (!client->inuse)
			continue;
		MoveClientToIntermission (client);
	}
	"""


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

		picnum = g_main.gi.imageindex ("i_fixme")
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

	"""
	char	entry[1024];
	char	string[1400];
	int		stringlength;
	int		i, j, k;
	int		sorted[MAX_CLIENTS];
	int		sortedscores[MAX_CLIENTS];
	int		score, total;
	int		picnum;
	int		x, y;
	gclient_t	*cl;
	edict_t		*cl_ent;
	char	*tag;

	// sort the clients by score
	total = 0;
	for (i=0 ; i<game.maxclients ; i++)
	{
		cl_ent = g_edicts + 1 + i;
		if (!cl_ent->inuse || game.clients[i].resp.spectator)
			continue;
		score = game.clients[i].resp.score;
		for (j=0 ; j<total ; j++)
		{
			if (score > sortedscores[j])
				break;
		}
		for (k=total ; k>j ; k--)
		{
			sorted[k] = sorted[k-1];
			sortedscores[k] = sortedscores[k-1];
		}
		sorted[j] = i;
		sortedscores[j] = score;
		total++;
	}

	// print level name and exit rules
	string[0] = 0;

	stringlength = strlen(string);

	// add the clients in sorted order
	if (total > 12)
		total = 12;

	for (i=0 ; i<total ; i++)
	{
		cl = &game.clients[sorted[i]];
		cl_ent = g_edicts + 1 + sorted[i];

		picnum = gi.imageindex ("i_fixme");
		x = (i>=6) ? 160 : 0;
		y = 32 + 32 * (i%6);

		// add a dogtag
		if (cl_ent == ent)
			tag = "tag1";
		else if (cl_ent == killer)
			tag = "tag2";
		else
			tag = NULL;
		if (tag)
		{
			Com_sprintf (entry, sizeof(entry),
				"xv %i yv %i picn %s ",x+32, y, tag);
			j = strlen(entry);
			if (stringlength + j > 1024)
				break;
			strcpy (string + stringlength, entry);
			stringlength += j;
		}

		// send the layout
		Com_sprintf (entry, sizeof(entry),
			"client %i %i %i %i %i %i ",
			x, y, sorted[i], cl->resp.score, cl->ping, (level.framenum - cl->resp.enterframe)/600);
		j = strlen(entry);
		if (stringlength + j > 1024)
			break;
		strcpy (string + stringlength, entry);
		stringlength += j;
	}

	gi.WriteByte (svc_layout);
	gi.WriteString (string);
	"""


def DeathmatchScoreboard (ent): #edict_t *
	DeathmatchScoreboardMessage (ent, ent.enemy)
	g_main.gi.unicast (ent, True)

	"""
	DeathmatchScoreboardMessage (ent, ent->enemy);
	gi.unicast (ent, true);
	"""


def Cmd_Score_f (ent): #edict_t *
	ent.client.showinventory = False
	ent.client.showhelp = False

	if not int(g_main.deathmatch.value) and not int(g_main.coop.value):
		return

	if ent.client.showscores:
		ent.client.showscores = False
		return

	ent.client.showscores = True
	DeathmatchScoreboard (ent)

	"""
	ent->client->showinventory = false;
	ent->client->showhelp = false;

	if (!deathmatch->value && !coop->value)
		return;

	if (ent->client->showscores)
	{
		ent->client->showscores = false;
		return;
	}

	ent->client->showscores = true;
	DeathmatchScoreboard (ent);
	"""


def HelpComputer (ent): #edict_t *
	if int(g_main.skill.value) == 0:
		sk = "easy"
	elif int(g_main.skill.value) == 1:
		sk = "medium"
	elif int(g_main.skill.value) == 2:
		sk = "hard"
	else:
		sk = "hard+"

	# send the layout
	string = ("xv 32 yv 8 picn help "					# background
		"xv 202 yv 12 string2 \"%s\" "			# skill
		"xv 0 yv 24 cstring2 \"%s\" "			# level name
		"xv 0 yv 54 cstring2 \"%s\" "			# help 1
		"xv 0 yv 110 cstring2 \"%s\" "			# help 2
		"xv 50 yv 164 string2 \" kills     goals    secrets\" "
		"xv 50 yv 172 string2 \"%3i/%3i     %i/%i       %i/%i\" "
		% (sk, g_main.level.level_name,
		   g_main.game.helpmessage1, g_main.game.helpmessage2,
		   g_main.level.killed_monsters, g_main.level.total_monsters,
		   g_main.level.found_goals, g_main.level.total_goals,
		   g_main.level.found_secrets, g_main.level.total_secrets))

	g_main.gi.WriteByte (svc_layout)
	g_main.gi.WriteString (string)
	g_main.gi.unicast (ent, True)

	"""
	char	string[1024];
	char	*sk;

	if (skill->value == 0)
		sk = "easy";
	else if (skill->value == 1)
		sk = "medium";
	else if (skill->value == 2)
		sk = "hard";
	else
		sk = "hard+";

	// send the layout
	Com_sprintf (string, sizeof(string),
		"xv 32 yv 8 picn help "			// background
		"xv 202 yv 12 string2 \"%s\" "		// skill
		"xv 0 yv 24 cstring2 \"%s\" "		// level name
		"xv 0 yv 54 cstring2 \"%s\" "		// help 1
		"xv 0 yv 110 cstring2 \"%s\" "		// help 2
		"xv 50 yv 164 string2 \" kills     goals    secrets\" "
		"xv 50 yv 172 string2 \"%3i/%3i     %i/%i       %i/%i\" ", 
		sk,
		level.level_name,
		game.helpmessage1,
		game.helpmessage2,
		level.killed_monsters, level.total_monsters, 
		level.found_goals, level.total_goals,
		level.found_secrets, level.total_secrets);

	gi.WriteByte (svc_layout);
	gi.WriteString (string);
	gi.unicast (ent, true);
	"""


def Cmd_Help_f (ent): #edict_t *
	# this is for backwards compatability
	if int(g_main.deathmatch.value):
		Cmd_Score_f (ent)
		return

	ent.client.showinventory = False
	ent.client.showscores = False

	if ent.client.showhelp and (ent.client.pers.game_helpchanged == g_main.game.helpchanged):
		ent.client.showhelp = False
		return

	ent.client.showhelp = True
	ent.client.pers.helpchanged = 0
	HelpComputer (ent)

	"""
	// this is for backwards compatability
	if (deathmatch->value)
	{
		Cmd_Score_f (ent);
		return;
	}

	ent->client->showinventory = false;
	ent->client->showscores = false;

	if (ent->client->showhelp && (ent->client->pers.game_helpchanged == game.helpchanged))
	{
		ent->client->showhelp = false;
		return;
	}

	ent->client->showhelp = true;
	ent->client->pers.helpchanged = 0;
	HelpComputer (ent);
	"""


"""
=======================================================================

G_SetStats

=======================================================================
"""
def G_SetStats (ent): #edict_t *
	item = None
	index = 0
	cells = 0
	power_armor_type = 0

	# health
	ent.client.ps.stats[STAT_HEALTH_ICON] = g_main.level.pic_health
	ent.client.ps.stats[STAT_HEALTH] = ent.health

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
		cells = ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem ("cells"))]
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
	if ent.client.pers.selected_item == -1:
		ent.client.ps.stats[STAT_SELECTED_ICON] = 0
	else:
		ent.client.ps.stats[STAT_SELECTED_ICON] = g_main.gi.imageindex (g_items.itemlist[ent.client.pers.selected_item].icon)

	ent.client.ps.stats[STAT_SELECTED_ITEM] = ent.client.pers.selected_item

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
	elif ((ent.client.pers.hand == CENTER_HANDED or ent.client.ps.fov > 91)
			and ent.client.pers.weapon):
		ent.client.ps.stats[STAT_HELPICON] = g_main.gi.imageindex (ent.client.pers.weapon.icon)
	else:
		ent.client.ps.stats[STAT_HELPICON] = 0

	ent.client.ps.stats[STAT_SPECTATOR] = 0

	"""
	gitem_t		*item;
	int			index, cells;
	int			power_armor_type;

	//
	// health
	//
	ent->client->ps.stats[STAT_HEALTH_ICON] = level.pic_health;
	ent->client->ps.stats[STAT_HEALTH] = ent->health;

	//
	// ammo
	//
	if (!ent->client->ammo_index /* || !ent->client->pers.inventory[ent->client->ammo_index] */)
	{
		ent->client->ps.stats[STAT_AMMO_ICON] = 0;
		ent->client->ps.stats[STAT_AMMO] = 0;
	}
	else
	{
		item = &itemlist[ent->client->ammo_index];
		ent->client->ps.stats[STAT_AMMO_ICON] = gi.imageindex (item->icon);
		ent->client->ps.stats[STAT_AMMO] = ent->client->pers.inventory[ent->client->ammo_index];
	}
	
	//
	// armor
	//
	power_armor_type = PowerArmorType (ent);
	if (power_armor_type)
	{
		cells = ent->client->pers.inventory[ITEM_INDEX(FindItem ("cells"))];
		if (cells == 0)
		{	// ran out of cells for power armor
			ent->flags &= ~FL_POWER_ARMOR;
			gi.sound(ent, CHAN_ITEM, gi.soundindex("misc/power2.wav"), 1, ATTN_NORM, 0);
			power_armor_type = 0;;
		}
	}

	index = ArmorIndex (ent);
	if (power_armor_type && (!index || (level.framenum & 8) ) )
	{	// flash between power armor and other armor icon
		ent->client->ps.stats[STAT_ARMOR_ICON] = gi.imageindex ("i_powershield");
		ent->client->ps.stats[STAT_ARMOR] = cells;
	}
	else if (index)
	{
		item = GetItemByIndex (index);
		ent->client->ps.stats[STAT_ARMOR_ICON] = gi.imageindex (item->icon);
		ent->client->ps.stats[STAT_ARMOR] = ent->client->pers.inventory[index];
	}
	else
	{
		ent->client->ps.stats[STAT_ARMOR_ICON] = 0;
		ent->client->ps.stats[STAT_ARMOR] = 0;
	}

	//
	// pickup message
	//
	if (level.time > ent->client->pickup_msg_time)
	{
		ent->client->ps.stats[STAT_PICKUP_ICON] = 0;
		ent->client->ps.stats[STAT_PICKUP_STRING] = 0;
	}

	//
	// timers
	//
	if (ent->client->quad_framenum > level.framenum)
	{
		ent->client->ps.stats[STAT_TIMER_ICON] = gi.imageindex ("p_quad");
		ent->client->ps.stats[STAT_TIMER] = (ent->client->quad_framenum - level.framenum)/10;
	}
	else if (ent->client->invincible_framenum > level.framenum)
	{
		ent->client->ps.stats[STAT_TIMER_ICON] = gi.imageindex ("p_invulnerability");
		ent->client->ps.stats[STAT_TIMER] = (ent->client->invincible_framenum - level.framenum)/10;
	}
	else if (ent->client->enviro_framenum > level.framenum)
	{
		ent->client->ps.stats[STAT_TIMER_ICON] = gi.imageindex ("p_envirosuit");
		ent->client->ps.stats[STAT_TIMER] = (ent->client->enviro_framenum - level.framenum)/10;
	}
	else if (ent->client->breather_framenum > level.framenum)
	{
		ent->client->ps.stats[STAT_TIMER_ICON] = gi.imageindex ("p_rebreather");
		ent->client->ps.stats[STAT_TIMER] = (ent->client->breather_framenum - level.framenum)/10;
	}
	else
	{
		ent->client->ps.stats[STAT_TIMER_ICON] = 0;
		ent->client->ps.stats[STAT_TIMER] = 0;
	}

	//
	// selected item
	//
	if (ent->client->pers.selected_item == -1)
		ent->client->ps.stats[STAT_SELECTED_ICON] = 0;
	else
		ent->client->ps.stats[STAT_SELECTED_ICON] = gi.imageindex (itemlist[ent->client->pers.selected_item].icon);

	ent->client->ps.stats[STAT_SELECTED_ITEM] = ent->client->pers.selected_item;

	//
	// layouts
	//
	ent->client->ps.stats[STAT_LAYOUTS] = 0;

	if (deathmatch->value)
	{
		if (ent->client->pers.health <= 0 || level.intermissiontime
			|| ent->client->showscores)
			ent->client->ps.stats[STAT_LAYOUTS] |= 1;
		if (ent->client->showinventory && ent->client->pers.health > 0)
			ent->client->ps.stats[STAT_LAYOUTS] |= 2;
	}
	else
	{
		if (ent->client->showscores || ent->client->showhelp)
			ent->client->ps.stats[STAT_LAYOUTS] |= 1;
		if (ent->client->showinventory && ent->client->pers.health > 0)
			ent->client->ps.stats[STAT_LAYOUTS] |= 2;
	}

	//
	// frags
	//
	ent->client->ps.stats[STAT_FRAGS] = ent->client->resp.score;

	//
	// help icon / current weapon if not shown
	//
	if (ent->client->pers.helpchanged && (level.framenum&8) )
		ent->client->ps.stats[STAT_HELPICON] = gi.imageindex ("i_help");
	else if ( (ent->client->pers.hand == CENTER_HANDED || ent->client->ps.fov > 91)
		&& ent->client->pers.weapon)
		ent->client->ps.stats[STAT_HELPICON] = gi.imageindex (ent->client->pers.weapon->icon);
	else
		ent->client->ps.stats[STAT_HELPICON] = 0;

	ent->client->ps.stats[STAT_SPECTATOR] = 0;
	"""


def G_CheckChaseStats (ent): #edict_t *
	for i in range(1, int(g_main.maxclients.value)+1):
		cl = g_main.g_edicts[i].client
		if not g_main.g_edicts[i].inuse or cl.chase_target is not ent:
			continue
		cl.ps.stats = list(ent.client.ps.stats)
		G_SetSpectatorStats(g_main.g_edicts[i])

	"""
	int i;
	gclient_t *cl;

	for (i = 1; i <= maxclients->value; i++) {
		cl = g_edicts[i].client;
		if (!g_edicts[i].inuse || cl->chase_target != ent)
			continue;
		memcpy(cl->ps.stats, ent->client->ps.stats, sizeof(cl->ps.stats));
		G_SetSpectatorStats(g_edicts + i);
	}
	"""


def G_SetSpectatorStats (ent): #edict_t *
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

	"""
	gclient_t *cl = ent->client;

	if (!cl->chase_target)
		G_SetStats (ent);

	cl->ps.stats[STAT_SPECTATOR] = 1;

	// layouts are independant in spectator
	cl->ps.stats[STAT_LAYOUTS] = 0;
	if (cl->pers.health <= 0 || level.intermissiontime || cl->showscores)
		cl->ps.stats[STAT_LAYOUTS] |= 1;
	if (cl->showinventory && cl->pers.health > 0)
		cl->ps.stats[STAT_LAYOUTS] |= 2;

	if (cl->chase_target && cl->chase_target->inuse)
		cl->ps.stats[STAT_CHASE] = CS_PLAYERSKINS + 
			(cl->chase_target - g_edicts) - 1;
	else
		cl->ps.stats[STAT_CHASE] = 0;
	"""
