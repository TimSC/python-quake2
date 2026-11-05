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
import numpy as np
from game import q_shared
from game import g_local
from game import g_main
from game import g_utils
from game import g_items
from game import g_weapon
from game.game import SVF_NOCLIENT

"""
// g_weapon.c

static qboolean	is_quad;
static byte		is_silenced;
"""
is_quad = False
is_silenced = 0

"""
player weapon animation frames (from m_player.h)
#define FRAME_attack1         	46
#define FRAME_attack8         	53
#define FRAME_wave08          	119
#define FRAME_crattak1        	160
#define FRAME_crattak3        	162
#define FRAME_crattak9        	168
"""
FRAME_attack1   = 46
FRAME_attack8   = 53
FRAME_wave08    = 119
FRAME_crattak1  = 160
FRAME_crattak3  = 162
FRAME_crattak9  = 168

"""
shotgun defaults (from g_local.h)
#define DEFAULT_SHOTGUN_HSPREAD		1000
#define DEFAULT_SHOTGUN_VSPREAD		500
#define DEFAULT_DEATHMATCH_SHOTGUN_COUNT	12
#define DEFAULT_SHOTGUN_COUNT		12
#define DEFAULT_SSHOTGUN_COUNT		20
"""
DEFAULT_SHOTGUN_HSPREAD          = 1000
DEFAULT_SHOTGUN_VSPREAD          = 500
DEFAULT_DEATHMATCH_SHOTGUN_COUNT = 12
DEFAULT_SHOTGUN_COUNT            = 12
DEFAULT_SSHOTGUN_COUNT           = 20

MULTICAST_PVS = q_shared.multicast_t.MULTICAST_PVS.value


def P_ProjectSource (client, point, distance, forward, right, result):
	"""
	static void P_ProjectSource (gclient_t *client, vec3_t point, vec3_t distance, vec3_t forward, vec3_t right, vec3_t result)
	{
		vec3_t	_distance;

		VectorCopy (distance, _distance);
		if (client->pers.hand == LEFT_HANDED)
			_distance[1] *= -1;
		else if (client->pers.hand == CENTER_HANDED)
			_distance[1] = 0;
		G_ProjectSource (point, _distance, forward, right, result);
	}
	"""
	_distance = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (distance, _distance)
	if client.pers.hand == g_local.LEFT_HANDED:
		_distance[1] *= -1
	elif client.pers.hand == g_local.CENTER_HANDED:
		_distance[1] = 0
	g_utils.G_ProjectSource (point, _distance, forward, right, result)


def PlayerNoise (who, where, type):
	"""
	void PlayerNoise(edict_t *who, vec3_t where, int type)
	{
		edict_t		*noise;

		if (type == PNOISE_WEAPON)
		{
			if (who->client->silencer_shots)
			{
				who->client->silencer_shots--;
				return;
			}
		}

		if (deathmatch->value)
			return;

		if (who->flags & FL_NOTARGET)
			return;


		if (!who->mynoise)
		{
			noise = G_Spawn();
			noise->classname = "player_noise";
			VectorSet (noise->mins, -8, -8, -8);
			VectorSet (noise->maxs, 8, 8, 8);
			noise->owner = who;
			noise->svflags = SVF_NOCLIENT;
			who->mynoise = noise;

			noise = G_Spawn();
			noise->classname = "player_noise";
			VectorSet (noise->mins, -8, -8, -8);
			VectorSet (noise->maxs, 8, 8, 8);
			noise->owner = who;
			noise->svflags = SVF_NOCLIENT;
			who->mynoise2 = noise;
		}

		if (type == PNOISE_SELF || type == PNOISE_WEAPON)
		{
			noise = who->mynoise;
			level.sound_entity = noise;
			level.sound_entity_framenum = level.framenum;
		}
		else // type == PNOISE_IMPACT
		{
			noise = who->mynoise2;
			level.sound2_entity = noise;
			level.sound2_entity_framenum = level.framenum;
		}

		VectorCopy (where, noise->s.origin);
		VectorSubtract (where, noise->maxs, noise->absmin);
		VectorAdd (where, noise->maxs, noise->absmax);
		noise->teleport_time = level.time;
		gi.linkentity (noise);
	}
	"""
	if type == g_local.PNOISE_WEAPON:
		if who.client.silencer_shots:
			who.client.silencer_shots -= 1
			return

	if g_main.deathmatch.value:
		return

	if who.flags & g_local.FL_NOTARGET:
		return

	if not who.mynoise:
		noise = g_utils.G_Spawn()
		noise.classname = "player_noise"
		q_shared.VectorSet (noise.mins, -8, -8, -8)
		q_shared.VectorSet (noise.maxs, 8, 8, 8)
		noise.owner = who
		noise.svflags = SVF_NOCLIENT
		who.mynoise = noise

		noise = g_utils.G_Spawn()
		noise.classname = "player_noise"
		q_shared.VectorSet (noise.mins, -8, -8, -8)
		q_shared.VectorSet (noise.maxs, 8, 8, 8)
		noise.owner = who
		noise.svflags = SVF_NOCLIENT
		who.mynoise2 = noise

	if type == g_local.PNOISE_SELF or type == g_local.PNOISE_WEAPON:
		noise = who.mynoise
		g_main.level.sound_entity = noise
		g_main.level.sound_entity_framenum = g_main.level.framenum
	else:
		noise = who.mynoise2
		g_main.level.sound2_entity = noise
		g_main.level.sound2_entity_framenum = g_main.level.framenum

	q_shared.VectorCopy (where, noise.s.origin)
	q_shared.VectorSubtract (where, noise.maxs, noise.absmin)
	q_shared.VectorAdd (where, noise.maxs, noise.absmax)
	noise.teleport_time = g_main.level.time
	g_main.gi.linkentity (noise)


def Pickup_Weapon (ent, other):
	"""
	qboolean Pickup_Weapon (edict_t *ent, edict_t *other)
	{
		int			index;
		gitem_t		*ammo;

		index = ITEM_INDEX(ent->item);

		if ( ( ((int)(dmflags->value) & DF_WEAPONS_STAY) || coop->value)
			&& other->client->pers.inventory[index])
		{
			if (!(ent->spawnflags & (DROPPED_ITEM | DROPPED_PLAYER_ITEM) ) )
				return false;	// leave the weapon for others to pickup
		}

		other->client->pers.inventory[index]++;

		if (!(ent->spawnflags & DROPPED_ITEM) )
		{
			// give them some ammo with it
			ammo = FindItem (ent->item->ammo);
			if ( (int)dmflags->value & DF_INFINITE_AMMO )
				Add_Ammo (other, ammo, 1000);
			else
				Add_Ammo (other, ammo, ammo->quantity);

			if (! (ent->spawnflags & DROPPED_PLAYER_ITEM) )
			{
				if (deathmatch->value)
				{
					if ((int)(dmflags->value) & DF_WEAPONS_STAY)
						ent->flags |= FL_RESPAWN;
					else
						SetRespawn (ent, 30);
				}
				if (coop->value)
					ent->flags |= FL_RESPAWN;
			}
		}

		if (other->client->pers.weapon != ent->item &&
			(other->client->pers.inventory[index] == 1) &&
			( !deathmatch->value || other->client->pers.weapon == FindItem("blaster") ) )
			other->client->newweapon = ent->item;

		return true;
	}
	"""
	index = g_items.ITEM_INDEX (ent.item)

	if ( ( ((int)(g_main.dmflags.value) & q_shared.DF_WEAPONS_STAY) or g_main.coop.value)
		and other.client.pers.inventory[index]):
		if not (ent.spawnflags & (g_local.DROPPED_ITEM | g_local.DROPPED_PLAYER_ITEM) ):
			return False

	other.client.pers.inventory[index] += 1

	if not (ent.spawnflags & g_local.DROPPED_ITEM) :
		ammo = g_items.FindItem (ent.item.ammo)
		if (int(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO ):
			g_items.Add_Ammo (other, ammo, 1000)
		else:
			g_items.Add_Ammo (other, ammo, ammo.quantity)

		if not (ent.spawnflags & g_local.DROPPED_PLAYER_ITEM) :
			if g_main.deathmatch.value:
				if (int(g_main.dmflags.value) & q_shared.DF_WEAPONS_STAY):
					ent.flags |= g_local.FL_RESPAWN
				else:
					g_items.SetRespawn (ent, 30)
			if g_main.coop.value:
				ent.flags |= g_local.FL_RESPAWN

	if other.client.pers.weapon != ent.item and \
		other.client.pers.inventory[index] == 1 and \
		(not g_main.deathmatch.value or other.client.pers.weapon == g_items.FindItem("blaster")):
		other.client.newweapon = ent.item

	return True


def ChangeWeapon (ent):
	"""
	void ChangeWeapon (edict_t *ent)
	{
		int i;

		if (ent->client->grenade_time)
		{
			ent->client->grenade_time = level.time;
			ent->client->weapon_sound = 0;
			weapon_grenade_fire (ent, false);
			ent->client->grenade_time = 0;
		}

		ent->client->pers.lastweapon = ent->client->pers.weapon;
		ent->client->pers.weapon = ent->client->newweapon;
		ent->client->newweapon = NULL;
		ent->client->machinegun_shots = 0;

		// set visible model
		if (ent->s.modelindex == 255) {
			if (ent->client->pers.weapon)
				i = ((ent->client->pers.weapon->weapmodel & 0xff) << 8);
			else
				i = 0;
			ent->s.skinnum = (ent - g_edicts - 1) | i;
		}

		if (ent->client->pers.weapon && ent->client->pers.weapon->ammo)
			ent->client->ammo_index = ITEM_INDEX(FindItem(ent->client->pers.weapon->ammo));
		else
			ent->client->ammo_index = 0;

		if (!ent->client->pers.weapon)
		{	// dead
			ent->client->ps.gunindex = 0;
			return;
		}

		ent->client->weaponstate = WEAPON_ACTIVATING;
		ent->client->ps.gunframe = 0;
		ent->client->ps.gunindex = gi.modelindex(ent->client->pers.weapon->view_model);

		ent->client->anim_priority = ANIM_PAIN;
		if(ent->client->ps.pmove.pm_flags & PMF_DUCKED)
		{
				ent->s.frame = FRAME_crpain1;
				ent->client->anim_end = FRAME_crpain4;
		}
		else
		{
			ent->s.frame = FRAME_pain301;
			ent->client->anim_end = FRAME_pain304;
		}
	}
	"""
	if ent.client.grenade_time:
		ent.client.grenade_time = g_main.level.time
		ent.client.weapon_sound = 0
		weapon_grenade_fire (ent, False)
		ent.client.grenade_time = 0

	ent.client.pers.lastweapon = ent.client.pers.weapon
	ent.client.pers.weapon = ent.client.newweapon
	ent.client.newweapon = None
	ent.client.machinegun_shots = 0

	# set visible model
	if ent.s.modelindex == 255:
		if ent.client.pers.weapon:
			i = ((ent.client.pers.weapon.weapmodel & 0xff) << 8)
		else:
			i = 0
		ent.s.skinnum = (g_main.g_edicts.index(ent) - 1) | i

	if ent.client.pers.weapon and ent.client.pers.weapon.ammo:
		ent.client.ammo_index = g_items.ITEM_INDEX(g_items.FindItem(ent.client.pers.weapon.ammo))
	else:
		ent.client.ammo_index = 0

	if not ent.client.pers.weapon:
		# dead
		ent.client.ps.gunindex = 0
		return

	ent.client.weaponstate = g_local.weaponstate_t.WEAPON_ACTIVATING
	ent.client.ps.gunframe = 0
	ent.client.ps.gunindex = g_main.gi.modelindex(ent.client.pers.weapon.view_model)

	ent.client.anim_priority = g_local.ANIM_PAIN
	if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
		ent.s.frame = g_local.FRAME_crpain1
		ent.client.anim_end = g_local.FRAME_crpain4
	else:
		ent.s.frame = g_local.FRAME_pain301
		ent.client.anim_end = g_local.FRAME_pain304


def NoAmmoWeaponChange (ent):
	"""
	void NoAmmoWeaponChange (edict_t *ent)
	{
		if ( ent->client->pers.inventory[ITEM_INDEX(FindItem("slugs"))]
			&&  ent->client->pers.inventory[ITEM_INDEX(FindItem("railgun"))] )
		{
			ent->client->newweapon = FindItem ("railgun");
			return;
		}
		if ( ent->client->pers.inventory[ITEM_INDEX(FindItem("cells"))]
			&&  ent->client->pers.inventory[ITEM_INDEX(FindItem("hyperblaster"))] )
		{
			ent->client->newweapon = FindItem ("hyperblaster");
			return;
		}
		if ( ent->client->pers.inventory[ITEM_INDEX(FindItem("bullets"))]
			&&  ent->client->pers.inventory[ITEM_INDEX(FindItem("chaingun"))] )
		{
			ent->client->newweapon = FindItem ("chaingun");
			return;
		}
		if ( ent->client->pers.inventory[ITEM_INDEX(FindItem("bullets"))]
			&&  ent->client->pers.inventory[ITEM_INDEX(FindItem("machinegun"))] )
		{
			ent->client->newweapon = FindItem ("machinegun");
			return;
		}
		if ( ent->client->pers.inventory[ITEM_INDEX(FindItem("shells"))] > 1
			&&  ent->client->pers.inventory[ITEM_INDEX(FindItem("super shotgun"))] )
		{
			ent->client->newweapon = FindItem ("super shotgun");
			return;
		}
		if ( ent->client->pers.inventory[ITEM_INDEX(FindItem("shells"))]
			&&  ent->client->pers.inventory[ITEM_INDEX(FindItem("shotgun"))] )
		{
			ent->client->newweapon = FindItem ("shotgun");
			return;
		}
		ent->client->newweapon = FindItem ("blaster");
	}
	"""
	if ( ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("slugs"))]
		and  ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("railgun"))] ):
		ent.client.newweapon = g_items.FindItem ("railgun")
		return
	if ( ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("cells"))]
		and  ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("hyperblaster"))] ):
		ent.client.newweapon = g_items.FindItem ("hyperblaster")
		return
	if ( ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("bullets"))]
		and  ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("chaingun"))] ):
		ent.client.newweapon = g_items.FindItem ("chaingun")
		return
	if ( ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("bullets"))]
		and  ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("machinegun"))] ):
		ent.client.newweapon = g_items.FindItem ("machinegun")
		return
	if ( ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("shells"))] > 1
		and  ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("super shotgun"))] ):
		ent.client.newweapon = g_items.FindItem ("super shotgun")
		return
	if ( ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("shells"))]
		and  ent.client.pers.inventory[g_items.ITEM_INDEX(g_items.FindItem("shotgun"))] ):
		ent.client.newweapon = g_items.FindItem ("shotgun")
		return
	ent.client.newweapon = g_items.FindItem ("blaster")


def Think_Weapon (ent):
	"""
	void Think_Weapon (edict_t *ent)
	{
		// if just died, put the weapon away
		if (ent->health < 1)
		{
			ent->client->newweapon = NULL;
			ChangeWeapon (ent);
		}

		// call active weapon think routine
		if (ent->client->pers.weapon && ent->client->pers.weapon->weaponthink)
		{
			is_quad = (ent->client->quad_framenum > level.framenum);
			if (ent->client->silencer_shots)
				is_silenced = MZ_SILENCED;
			else
				is_silenced = 0;
			ent->client->pers.weapon->weaponthink (ent);
		}
	}
	"""
	global is_quad, is_silenced
	# if just died, put the weapon away
	if ent.health < 1:
		ent.client.newweapon = None
		ChangeWeapon (ent)

	# call active weapon think routine
	if ent.client.pers.weapon and ent.client.pers.weapon.weaponthink:
		is_quad = (ent.client.quad_framenum > g_main.level.framenum)
		if ent.client.silencer_shots:
			is_silenced = q_shared.MZ_SILENCED
		else:
			is_silenced = 0
		ent.client.pers.weapon.weaponthink (ent)


def Use_Weapon (ent, item):
	"""
	void Use_Weapon (edict_t *ent, gitem_t *item)
	{
		int			ammo_index;
		gitem_t		*ammo_item;

		// see if we're already using it
		if (item == ent->client->pers.weapon)
			return;

		if (item->ammo && !g_select_empty->value && !(item->flags & IT_AMMO))
		{
			ammo_item = FindItem(item->ammo);
			ammo_index = ITEM_INDEX(ammo_item);

			if (!ent->client->pers.inventory[ammo_index])
			{
				gi.cprintf (ent, PRINT_HIGH, "No %s for %s.\n", ammo_item->pickup_name, item->pickup_name);
				return;
			}

			if (ent->client->pers.inventory[ammo_index] < item->quantity)
			{
				gi.cprintf (ent, PRINT_HIGH, "Not enough %s for %s.\n", ammo_item->pickup_name, item->pickup_name);
				return;
			}
		}

		// change to this weapon when down
		ent->client->newweapon = item;
	}
	"""
	# see if we're already using it
	if item == ent.client.pers.weapon:
		return

	if item.ammo and not g_main.g_select_empty.value and not (item.flags & g_local.IT_AMMO):
		ammo_item = g_items.FindItem(item.ammo)
		ammo_index = g_items.ITEM_INDEX(ammo_item)

		if not ent.client.pers.inventory[ammo_index]:
			g_main.gi.cprintf (ent, q_shared.PRINT_HIGH, "No %s for %s.\n" % (ammo_item.pickup_name, item.pickup_name))
			return

		if ent.client.pers.inventory[ammo_index] < item.quantity:
			g_main.gi.cprintf (ent, q_shared.PRINT_HIGH, "Not enough %s for %s.\n" % (ammo_item.pickup_name, item.pickup_name))
			return

	# change to this weapon when down
	ent.client.newweapon = item


def Drop_Weapon (ent, item):
	"""
	void Drop_Weapon (edict_t *ent, gitem_t *item)
	{
		int		index;

		if ((int)(dmflags->value) & DF_WEAPONS_STAY)
			return;

		index = ITEM_INDEX(item);
		// see if we're already using it
		if ( ((item == ent->client->pers.weapon) || (item == ent->client->newweapon))&& (ent->client->pers.inventory[index] == 1) )
		{
			gi.cprintf (ent, PRINT_HIGH, "Can't drop current weapon\n");
			return;
		}

		Drop_Item (ent, item);
		ent->client->pers.inventory[index]--;
	}
	"""
	if (int(g_main.dmflags.value) & q_shared.DF_WEAPONS_STAY):
		return

	index = g_items.ITEM_INDEX(item)
	# see if we're already using it
	if ( (item == ent.client.pers.weapon) or (item == ent.client.newweapon)) and (ent.client.pers.inventory[index] == 1):
		g_main.gi.cprintf (ent, q_shared.PRINT_HIGH, "Can't drop current weapon\n")
		return

	g_items.Drop_Item (ent, item)
	ent.client.pers.inventory[index] -= 1


def Weapon_Generic (ent, FRAME_ACTIVATE_LAST, FRAME_FIRE_LAST, FRAME_IDLE_LAST, FRAME_DEACTIVATE_LAST, pause_frames, fire_frames, fire):
	"""
	void Weapon_Generic (edict_t *ent, int FRAME_ACTIVATE_LAST, int FRAME_FIRE_LAST, int FRAME_IDLE_LAST, int FRAME_DEACTIVATE_LAST, int *pause_frames, int *fire_frames, void (*fire)(edict_t *ent))
	{
		int		n;

		if(ent->deadflag || ent->s.modelindex != 255) // VWep animations screw up corpses
		{
			return;
		}

		if (ent->client->weaponstate == WEAPON_DROPPING)
		{
			if (ent->client->ps.gunframe == FRAME_DEACTIVATE_LAST)
			{
				ChangeWeapon (ent);
				return;
			}
			else if ((FRAME_DEACTIVATE_LAST - ent->client->ps.gunframe) == 4)
			{
				ent->client->anim_priority = ANIM_REVERSE;
				if(ent->client->ps.pmove.pm_flags & PMF_DUCKED)
				{
					ent->s.frame = FRAME_crpain4+1;
					ent->client->anim_end = FRAME_crpain1;
				}
				else
				{
					ent->s.frame = FRAME_pain304+1;
					ent->client->anim_end = FRAME_pain301;
				}
			}

			ent->client->ps.gunframe++;
			return;
		}

		if (ent->client->weaponstate == WEAPON_ACTIVATING)
		{
			if (ent->client->ps.gunframe == FRAME_ACTIVATE_LAST)
			{
				ent->client->weaponstate = WEAPON_READY;
				ent->client->ps.gunframe = FRAME_IDLE_FIRST;
				return;
			}

			ent->client->ps.gunframe++;
			return;
		}

		if ((ent->client->newweapon) && (ent->client->weaponstate != WEAPON_FIRING))
		{
			ent->client->weaponstate = WEAPON_DROPPING;
			ent->client->ps.gunframe = FRAME_DEACTIVATE_FIRST;

			if ((FRAME_DEACTIVATE_LAST - FRAME_DEACTIVATE_FIRST) < 4)
			{
				ent->client->anim_priority = ANIM_REVERSE;
				if(ent->client->ps.pmove.pm_flags & PMF_DUCKED)
				{
					ent->s.frame = FRAME_crpain4+1;
					ent->client->anim_end = FRAME_crpain1;
				}
				else
				{
					ent->s.frame = FRAME_pain304+1;
					ent->client->anim_end = FRAME_pain301;
				}
			}
			return;
		}

		if (ent->client->weaponstate == WEAPON_READY)
		{
			if ( ((ent->client->latched_buttons|ent->client->buttons) & BUTTON_ATTACK) )
			{
				ent->client->latched_buttons &= ~BUTTON_ATTACK;
				if ((!ent->client->ammo_index) ||
					( ent->client->pers.inventory[ent->client->ammo_index] >= ent->client->pers.weapon->quantity))
				{
					ent->client->ps.gunframe = FRAME_FIRE_FIRST;
					ent->client->weaponstate = WEAPON_FIRING;

					// start the animation
					ent->client->anim_priority = ANIM_ATTACK;
					if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
					{
						ent->s.frame = FRAME_crattak1-1;
						ent->client->anim_end = FRAME_crattak9;
					}
					else
					{
						ent->s.frame = FRAME_attack1-1;
						ent->client->anim_end = FRAME_attack8;
					}
				}
				else
				{
					if (level.time >= ent->pain_debounce_time)
					{
						gi.sound(ent, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1, ATTN_NORM, 0);
						ent->pain_debounce_time = level.time + 1;
					}
					NoAmmoWeaponChange (ent);
				}
			}
			else
			{
				if (ent->client->ps.gunframe == FRAME_IDLE_LAST)
				{
					ent->client->ps.gunframe = FRAME_IDLE_FIRST;
					return;
				}

				if (pause_frames)
				{
					for (n = 0; pause_frames[n]; n++)
					{
						if (ent->client->ps.gunframe == pause_frames[n])
						{
							if (rand()&15)
								return;
						}
					}
				}

				ent->client->ps.gunframe++;
				return;
			}
		}

		if (ent->client->weaponstate == WEAPON_FIRING)
		{
			for (n = 0; fire_frames[n]; n++)
			{
				if (ent->client->ps.gunframe == fire_frames[n])
				{
					if (ent->client->quad_framenum > level.framenum)
						gi.sound(ent, CHAN_ITEM, gi.soundindex("items/damage3.wav"), 1, ATTN_NORM, 0);

					fire (ent);
					break;
				}
			}

			if (!fire_frames[n])
				ent->client->ps.gunframe++;

			if (ent->client->ps.gunframe == FRAME_IDLE_FIRST+1)
				ent->client->weaponstate = WEAPON_READY;
		}
	}
	"""
	FRAME_FIRE_FIRST     = FRAME_ACTIVATE_LAST + 1
	FRAME_IDLE_FIRST     = FRAME_FIRE_LAST + 1
	FRAME_DEACTIVATE_FIRST = FRAME_IDLE_LAST + 1

	if(ent.deadflag or ent.s.modelindex != 255):
		return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_DROPPING:
		if ent.client.ps.gunframe == FRAME_DEACTIVATE_LAST:
			ChangeWeapon (ent)
			return
		elif (FRAME_DEACTIVATE_LAST - ent.client.ps.gunframe) == 4:
			ent.client.anim_priority = g_local.ANIM_REVERSE
			if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
				ent.s.frame = g_local.FRAME_crpain4+1
				ent.client.anim_end = g_local.FRAME_crpain1
			else:
				ent.s.frame = g_local.FRAME_pain304+1
				ent.client.anim_end = g_local.FRAME_pain301

		ent.client.ps.gunframe += 1
		return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_ACTIVATING:
		if ent.client.ps.gunframe == FRAME_ACTIVATE_LAST:
			ent.client.weaponstate = g_local.weaponstate_t.WEAPON_READY
			ent.client.ps.gunframe = FRAME_IDLE_FIRST
			return

		ent.client.ps.gunframe += 1
		return

	if ent.client.newweapon and ent.client.weaponstate != g_local.weaponstate_t.WEAPON_FIRING:
		ent.client.weaponstate = g_local.weaponstate_t.WEAPON_DROPPING
		ent.client.ps.gunframe = FRAME_DEACTIVATE_FIRST

		if (FRAME_DEACTIVATE_LAST - FRAME_DEACTIVATE_FIRST) < 4:
			ent.client.anim_priority = g_local.ANIM_REVERSE
			if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
				ent.s.frame = g_local.FRAME_crpain4+1
				ent.client.anim_end = g_local.FRAME_crpain1
			else:
				ent.s.frame = g_local.FRAME_pain304+1
				ent.client.anim_end = g_local.FRAME_pain301
		return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_READY:
		if (ent.client.latched_buttons|ent.client.buttons) & q_shared.BUTTON_ATTACK:
			ent.client.latched_buttons &= ~q_shared.BUTTON_ATTACK
			if (not ent.client.ammo_index) or \
				(ent.client.pers.inventory[ent.client.ammo_index] >= ent.client.pers.weapon.quantity):
				ent.client.ps.gunframe = FRAME_FIRE_FIRST
				ent.client.weaponstate = g_local.weaponstate_t.WEAPON_FIRING

				# start the animation
				ent.client.anim_priority = g_local.ANIM_ATTACK
				if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
					ent.s.frame = FRAME_crattak1-1
					ent.client.anim_end = FRAME_crattak9
				else:
					ent.s.frame = FRAME_attack1-1
					ent.client.anim_end = FRAME_attack8
			else:
				if g_main.level.time >= ent.pain_debounce_time:
					g_main.gi.sound(ent, q_shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, q_shared.ATTN_NORM, 0)
					ent.pain_debounce_time = g_main.level.time + 1
				NoAmmoWeaponChange (ent)
		else:
			if ent.client.ps.gunframe == FRAME_IDLE_LAST:
				ent.client.ps.gunframe = FRAME_IDLE_FIRST
				return

			if pause_frames:
				n = 0
				while pause_frames[n]:
					if ent.client.ps.gunframe == pause_frames[n]:
						if _r.randint(0, 0x7fffffff) & 15:
							return
					n += 1

			ent.client.ps.gunframe += 1
			return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_FIRING:
		n = 0
		while fire_frames[n]:
			if ent.client.ps.gunframe == fire_frames[n]:
				if ent.client.quad_framenum > g_main.level.framenum:
					g_main.gi.sound(ent, q_shared.CHAN_ITEM, g_main.gi.soundindex("items/damage3.wav"), 1, q_shared.ATTN_NORM, 0)

				fire (ent)
				break
			n += 1

		if not fire_frames[n]:
			ent.client.ps.gunframe += 1

		if ent.client.ps.gunframe == FRAME_IDLE_FIRST+1:
			ent.client.weaponstate = g_local.weaponstate_t.WEAPON_READY

GRENADE_TIMER    = 3.0
GRENADE_MINSPEED = 400
GRENADE_MAXSPEED = 800


def weapon_grenade_fire (ent, held):
	"""
	void weapon_grenade_fire (edict_t *ent, qboolean held)
	{
		vec3_t	offset;
		vec3_t	forward, right;
		vec3_t	start;
		int		damage = 125;
		float	timer;
		int		speed;
		float	radius;

		radius = damage+40;
		if (is_quad)
			damage *= 4;

		VectorSet(offset, 8, 8, ent->viewheight-8);
		AngleVectors (ent->client->v_angle, forward, right, NULL);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);

		timer = ent->client->grenade_time - level.time;
		speed = GRENADE_MINSPEED + (GRENADE_TIMER - timer) * ((GRENADE_MAXSPEED - GRENADE_MINSPEED) / GRENADE_TIMER);
		fire_grenade2 (ent, start, forward, damage, speed, timer, radius, held);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index]--;

		ent->client->grenade_time = level.time + 1.0;

		if(ent->deadflag || ent->s.modelindex != 255) // VWep animations screw up corpses
		{
			return;
		}

		if (ent->health <= 0)
			return;

		if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
		{
			ent->client->anim_priority = ANIM_ATTACK;
			ent->s.frame = FRAME_crattak1-1;
			ent->client->anim_end = FRAME_crattak3;
		}
		else
		{
			ent->client->anim_priority = ANIM_REVERSE;
			ent->s.frame = FRAME_wave08;
			ent->client->anim_end = FRAME_wave01;
		}
	}
	"""
	offset = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	damage = 125

	radius = damage+40
	if is_quad:
		damage *= 4

	q_shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)

	timer = ent.client.grenade_time - g_main.level.time
	speed = GRENADE_MINSPEED + (GRENADE_TIMER - timer) * ((GRENADE_MAXSPEED - GRENADE_MINSPEED) / GRENADE_TIMER)
	g_weapon.fire_grenade2 (ent, start, forward, damage, speed, timer, radius, held)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1

	ent.client.grenade_time = g_main.level.time + 1.0

	if(ent.deadflag or ent.s.modelindex != 255):
		return

	if ent.health <= 0:
		return

	if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
		ent.client.anim_priority = g_local.ANIM_ATTACK
		ent.s.frame = FRAME_crattak1-1
		ent.client.anim_end = FRAME_crattak3
	else:
		ent.client.anim_priority = g_local.ANIM_REVERSE
		ent.s.frame = FRAME_wave08
		ent.client.anim_end = g_local.FRAME_wave01


def Weapon_Grenade (ent):
	"""
	void Weapon_Grenade (edict_t *ent)
	{
		if ((ent->client->newweapon) && (ent->client->weaponstate == WEAPON_READY))
		{
			ChangeWeapon (ent);
			return;
		}

		if (ent->client->weaponstate == WEAPON_ACTIVATING)
		{
			ent->client->weaponstate = WEAPON_READY;
			ent->client->ps.gunframe = 16;
			return;
		}

		if (ent->client->weaponstate == WEAPON_READY)
		{
			if ( ((ent->client->latched_buttons|ent->client->buttons) & BUTTON_ATTACK) )
			{
				ent->client->latched_buttons &= ~BUTTON_ATTACK;
				if (ent->client->pers.inventory[ent->client->ammo_index])
				{
					ent->client->ps.gunframe = 1;
					ent->client->weaponstate = WEAPON_FIRING;
					ent->client->grenade_time = 0;
				}
				else
				{
					if (level.time >= ent->pain_debounce_time)
					{
						gi.sound(ent, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1, ATTN_NORM, 0);
						ent->pain_debounce_time = level.time + 1;
					}
					NoAmmoWeaponChange (ent);
				}
				return;
			}

			if ((ent->client->ps.gunframe == 29) || (ent->client->ps.gunframe == 34) || (ent->client->ps.gunframe == 39) || (ent->client->ps.gunframe == 48))
			{
				if (rand()&15)
					return;
			}

			if (++ent->client->ps.gunframe > 48)
				ent->client->ps.gunframe = 16;
			return;
		}

		if (ent->client->weaponstate == WEAPON_FIRING)
		{
			if (ent->client->ps.gunframe == 5)
				gi.sound(ent, CHAN_WEAPON, gi.soundindex("weapons/hgrena1b.wav"), 1, ATTN_NORM, 0);

			if (ent->client->ps.gunframe == 11)
			{
				if (!ent->client->grenade_time)
				{
					ent->client->grenade_time = level.time + GRENADE_TIMER + 0.2;
					ent->client->weapon_sound = gi.soundindex("weapons/hgrenc1b.wav");
				}

				// they waited too long, detonate it in their hand
				if (!ent->client->grenade_blew_up && level.time >= ent->client->grenade_time)
				{
					ent->client->weapon_sound = 0;
					weapon_grenade_fire (ent, true);
					ent->client->grenade_blew_up = true;
				}

				if (ent->client->buttons & BUTTON_ATTACK)
					return;

				if (ent->client->grenade_blew_up)
				{
					if (level.time >= ent->client->grenade_time)
					{
						ent->client->ps.gunframe = 15;
						ent->client->grenade_blew_up = false;
					}
					else
					{
						return;
					}
				}
			}

			if (ent->client->ps.gunframe == 12)
			{
				ent->client->weapon_sound = 0;
				weapon_grenade_fire (ent, false);
			}

			if ((ent->client->ps.gunframe == 15) && (level.time < ent->client->grenade_time))
				return;

			ent->client->ps.gunframe++;

			if (ent->client->ps.gunframe == 16)
			{
				ent->client->grenade_time = 0;
				ent->client->weaponstate = WEAPON_READY;
			}
		}
	}
	"""
	if ent.client.newweapon and ent.client.weaponstate == g_local.weaponstate_t.WEAPON_READY:
		ChangeWeapon (ent)
		return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_ACTIVATING:
		ent.client.weaponstate = g_local.weaponstate_t.WEAPON_READY
		ent.client.ps.gunframe = 16
		return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_READY:
		if (ent.client.latched_buttons|ent.client.buttons) & q_shared.BUTTON_ATTACK:
			ent.client.latched_buttons &= ~q_shared.BUTTON_ATTACK
			if ent.client.pers.inventory[ent.client.ammo_index]:
				ent.client.ps.gunframe = 1
				ent.client.weaponstate = g_local.weaponstate_t.WEAPON_FIRING
				ent.client.grenade_time = 0
			else:
				if g_main.level.time >= ent.pain_debounce_time:
					g_main.gi.sound(ent, q_shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, q_shared.ATTN_NORM, 0)
					ent.pain_debounce_time = g_main.level.time + 1
				NoAmmoWeaponChange (ent)
			return

		if (ent.client.ps.gunframe == 29) or (ent.client.ps.gunframe == 34) or (ent.client.ps.gunframe == 39) or (ent.client.ps.gunframe == 48):
			if _r.randint(0, 0x7fffffff) & 15:
				return

		ent.client.ps.gunframe += 1
		if ent.client.ps.gunframe > 48:
			ent.client.ps.gunframe = 16
		return

	if ent.client.weaponstate == g_local.weaponstate_t.WEAPON_FIRING:
		if ent.client.ps.gunframe == 5:
			g_main.gi.sound(ent, q_shared.CHAN_WEAPON, g_main.gi.soundindex("weapons/hgrena1b.wav"), 1, q_shared.ATTN_NORM, 0)

		if ent.client.ps.gunframe == 11:
			if not ent.client.grenade_time:
				ent.client.grenade_time = g_main.level.time + GRENADE_TIMER + 0.2
				ent.client.weapon_sound = g_main.gi.soundindex("weapons/hgrenc1b.wav")

			# they waited too long, detonate it in their hand
			if not ent.client.grenade_blew_up and g_main.level.time >= ent.client.grenade_time:
				ent.client.weapon_sound = 0
				weapon_grenade_fire (ent, True)
				ent.client.grenade_blew_up = True

			if ent.client.buttons & q_shared.BUTTON_ATTACK:
				return

			if ent.client.grenade_blew_up:
				if g_main.level.time >= ent.client.grenade_time:
					ent.client.ps.gunframe = 15
					ent.client.grenade_blew_up = False
				else:
					return

		if ent.client.ps.gunframe == 12:
			ent.client.weapon_sound = 0
			weapon_grenade_fire (ent, False)

		if (ent.client.ps.gunframe == 15) and (g_main.level.time < ent.client.grenade_time):
			return

		ent.client.ps.gunframe += 1

		if ent.client.ps.gunframe == 16:
			ent.client.grenade_time = 0
			ent.client.weaponstate = g_local.weaponstate_t.WEAPON_READY


def weapon_grenadelauncher_fire (ent):
	"""
	void weapon_grenadelauncher_fire (edict_t *ent)
	{
		vec3_t	offset;
		vec3_t	forward, right;
		vec3_t	start;
		int		damage = 120;
		float	radius;

		radius = damage+40;
		if (is_quad)
			damage *= 4;

		VectorSet(offset, 8, 8, ent->viewheight-8);
		AngleVectors (ent->client->v_angle, forward, right, NULL);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);

		VectorScale (forward, -2, ent->client->kick_origin);
		ent->client->kick_angles[0] = -1;

		fire_grenade (ent, start, forward, damage, 600, 2.5, radius);

		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte (MZ_GRENADE | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		ent->client->ps.gunframe++;

		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index]--;
	}
	"""
	offset = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	damage = 120

	radius = damage+40
	if is_quad:
		damage *= 4

	q_shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)

	q_shared.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -1

	g_weapon.fire_grenade (ent, start, forward, damage, 600, 2.5, radius)

	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (q_shared.MZ_GRENADE | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1

	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_GrenadeLauncher (ent):
	"""
	void Weapon_GrenadeLauncher (edict_t *ent)
	{
		static int	pause_frames[]	= {34, 51, 59, 0};
		static int	fire_frames[]	= {6, 0};

		Weapon_Generic (ent, 5, 16, 59, 64, pause_frames, fire_frames, weapon_grenadelauncher_fire);
	}
	"""
	pause_frames = [34, 51, 59, 0]
	fire_frames = [6, 0]

	Weapon_Generic (ent, 5, 16, 59, 64, pause_frames, fire_frames, weapon_grenadelauncher_fire)


def Weapon_RocketLauncher_Fire (ent):
	"""
	void Weapon_RocketLauncher_Fire (edict_t *ent)
	{
		vec3_t	offset, start;
		vec3_t	forward, right;
		int		damage;
		float	damage_radius;
		int		radius_damage;

		damage = 100 + (int)(random() * 20.0);
		radius_damage = 120;
		damage_radius = 120;
		if (is_quad)
		{
			damage *= 4;
			radius_damage *= 4;
		}

		AngleVectors (ent->client->v_angle, forward, right, NULL);

		VectorScale (forward, -2, ent->client->kick_origin);
		ent->client->kick_angles[0] = -1;

		VectorSet(offset, 8, 8, ent->viewheight-8);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);
		fire_rocket (ent, start, forward, damage, 650, damage_radius, radius_damage);

		// send muzzle flash
		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte (MZ_ROCKET | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		ent->client->ps.gunframe++;

		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index]--;
	}
	"""
	offset = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)

	damage = 100 + int(_r.random() * 20.0)
	radius_damage = 120
	damage_radius = 120
	if is_quad:
		damage *= 4
		radius_damage *= 4

	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)

	q_shared.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -1

	q_shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)
	g_weapon.fire_rocket (ent, start, forward, damage, 650, damage_radius, radius_damage)

	# send muzzle flash
	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (q_shared.MZ_ROCKET | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1

	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_RocketLauncher (ent):
	"""
	void Weapon_RocketLauncher (edict_t *ent)
	{
		static int	pause_frames[]	= {25, 33, 42, 50, 0};
		static int	fire_frames[]	= {5, 0};

		Weapon_Generic (ent, 4, 12, 50, 54, pause_frames, fire_frames, Weapon_RocketLauncher_Fire);
	}
	"""
	pause_frames = [25, 33, 42, 50, 0]
	fire_frames = [5, 0]

	Weapon_Generic (ent, 4, 12, 50, 54, pause_frames, fire_frames, Weapon_RocketLauncher_Fire)


def Blaster_Fire (ent, g_offset, damage, hyper, effect):
	"""
	void Blaster_Fire (edict_t *ent, vec3_t g_offset, int damage, qboolean hyper, int effect)
	{
		vec3_t	forward, right;
		vec3_t	start;
		vec3_t	offset;

		if (is_quad)
			damage *= 4;
		AngleVectors (ent->client->v_angle, forward, right, NULL);
		VectorSet(offset, 24, 8, ent->viewheight-8);
		VectorAdd (offset, g_offset, offset);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);

		VectorScale (forward, -2, ent->client->kick_origin);
		ent->client->kick_angles[0] = -1;

		fire_blaster (ent, start, forward, damage, 1000, effect, hyper);

		// send muzzle flash
		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		if (hyper)
			gi.WriteByte (MZ_HYPERBLASTER | is_silenced);
		else
			gi.WriteByte (MZ_BLASTER | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		PlayerNoise(ent, start, PNOISE_WEAPON);
	}
	"""
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)

	if is_quad:
		damage *= 4
	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)
	q_shared.VectorSet(offset, 24, 8, ent.viewheight-8)
	q_shared.VectorAdd (offset, g_offset, offset)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)

	q_shared.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -1

	g_weapon.fire_blaster (ent, start, forward, damage, 1000, effect, hyper)

	# send muzzle flash
	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	if hyper:
		g_main.gi.WriteByte (q_shared.MZ_HYPERBLASTER | is_silenced)
	else:
		g_main.gi.WriteByte (q_shared.MZ_BLASTER | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)


def Weapon_Blaster_Fire (ent):
	"""
	void Weapon_Blaster_Fire (edict_t *ent)
	{
		int		damage;

		if (deathmatch->value)
			damage = 15;
		else
			damage = 10;
		Blaster_Fire (ent, vec3_origin, damage, false, EF_BLASTER);
		ent->client->ps.gunframe++;
	}
	"""
	if g_main.deathmatch.value:
		damage = 15
	else:
		damage = 10
	Blaster_Fire (ent, q_shared.vec3_origin, damage, False, q_shared.EF_BLASTER)
	ent.client.ps.gunframe += 1


def Weapon_Blaster (ent):
	"""
	void Weapon_Blaster (edict_t *ent)
	{
		static int	pause_frames[]	= {19, 32, 0};
		static int	fire_frames[]	= {5, 0};

		Weapon_Generic (ent, 4, 8, 52, 55, pause_frames, fire_frames, Weapon_Blaster_Fire);
	}
	"""
	pause_frames = [19, 32, 0]
	fire_frames = [5, 0]

	Weapon_Generic (ent, 4, 8, 52, 55, pause_frames, fire_frames, Weapon_Blaster_Fire)


def Weapon_HyperBlaster_Fire (ent):
	"""
	void Weapon_HyperBlaster_Fire (edict_t *ent)
	{
		float	rotation;
		vec3_t	offset;
		int		effect;
		int		damage;

		ent->client->weapon_sound = gi.soundindex("weapons/hyprbl1a.wav");

		if (!(ent->client->buttons & BUTTON_ATTACK))
		{
			ent->client->ps.gunframe++;
		}
		else
		{
			if (! ent->client->pers.inventory[ent->client->ammo_index] )
			{
				if (level.time >= ent->pain_debounce_time)
				{
					gi.sound(ent, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1, ATTN_NORM, 0);
					ent->pain_debounce_time = level.time + 1;
				}
				NoAmmoWeaponChange (ent);
			}
			else
			{
				rotation = (ent->client->ps.gunframe - 5) * 2*M_PI/6;
				offset[0] = -4 * sin(rotation);
				offset[1] = 0;
				offset[2] = 4 * cos(rotation);

				if ((ent->client->ps.gunframe == 6) || (ent->client->ps.gunframe == 9))
					effect = EF_HYPERBLASTER;
				else
					effect = 0;
				if (deathmatch->value)
					damage = 15;
				else
					damage = 20;
				Blaster_Fire (ent, offset, damage, true, effect);
				if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
					ent->client->pers.inventory[ent->client->ammo_index]--;

				ent->client->anim_priority = ANIM_ATTACK;
				if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
				{
					ent->s.frame = FRAME_crattak1 - 1;
					ent->client->anim_end = FRAME_crattak9;
				}
				else
				{
					ent->s.frame = FRAME_attack1 - 1;
					ent->client->anim_end = FRAME_attack8;
				}
			}

			ent->client->ps.gunframe++;
			if (ent->client->ps.gunframe == 12 && ent->client->pers.inventory[ent->client->ammo_index])
				ent->client->ps.gunframe = 6;
		}

		if (ent->client->ps.gunframe == 12)
		{
			gi.sound(ent, CHAN_AUTO, gi.soundindex("weapons/hyprbd1a.wav"), 1, ATTN_NORM, 0);
			ent->client->weapon_sound = 0;
		}

	}
	"""
	offset = np.zeros((3,), dtype=np.float32)

	ent.client.weapon_sound = g_main.gi.soundindex("weapons/hyprbl1a.wav")

	if not (ent.client.buttons & q_shared.BUTTON_ATTACK):
		ent.client.ps.gunframe += 1
	else:
		if not ent.client.pers.inventory[ent.client.ammo_index]:
			if g_main.level.time >= ent.pain_debounce_time:
				g_main.gi.sound(ent, q_shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, q_shared.ATTN_NORM, 0)
				ent.pain_debounce_time = g_main.level.time + 1
			NoAmmoWeaponChange (ent)
		else:
			rotation = (ent.client.ps.gunframe - 5) * 2*math.pi/6
			offset[0] = -4 * math.sin(rotation)
			offset[1] = 0
			offset[2] = 4 * math.cos(rotation)

			if (ent.client.ps.gunframe == 6) or (ent.client.ps.gunframe == 9):
				effect = q_shared.EF_HYPERBLASTER
			else:
				effect = 0
			if g_main.deathmatch.value:
				damage = 15
			else:
				damage = 20
			Blaster_Fire (ent, offset, damage, True, effect)
			if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
				ent.client.pers.inventory[ent.client.ammo_index] -= 1

			ent.client.anim_priority = g_local.ANIM_ATTACK
			if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
				ent.s.frame = FRAME_crattak1 - 1
				ent.client.anim_end = FRAME_crattak9
			else:
				ent.s.frame = FRAME_attack1 - 1
				ent.client.anim_end = FRAME_attack8

		ent.client.ps.gunframe += 1
		if ent.client.ps.gunframe == 12 and ent.client.pers.inventory[ent.client.ammo_index]:
			ent.client.ps.gunframe = 6

	if ent.client.ps.gunframe == 12:
		g_main.gi.sound(ent, q_shared.CHAN_AUTO, g_main.gi.soundindex("weapons/hyprbd1a.wav"), 1, q_shared.ATTN_NORM, 0)
		ent.client.weapon_sound = 0


def Weapon_HyperBlaster (ent):
	"""
	void Weapon_HyperBlaster (edict_t *ent)
	{
		static int	pause_frames[]	= {0};
		static int	fire_frames[]	= {6, 7, 8, 9, 10, 11, 0};

		Weapon_Generic (ent, 5, 20, 49, 53, pause_frames, fire_frames, Weapon_HyperBlaster_Fire);
	}
	"""
	pause_frames = [0]
	fire_frames = [6, 7, 8, 9, 10, 11, 0]

	Weapon_Generic (ent, 5, 20, 49, 53, pause_frames, fire_frames, Weapon_HyperBlaster_Fire)

def Machinegun_Fire (ent):
	"""
	void Machinegun_Fire (edict_t *ent)
	{
		int	i;
		vec3_t		start;
		vec3_t		forward, right;
		vec3_t		angles;
		int			damage = 8;
		int			kick = 2;
		vec3_t		offset;

		if (!(ent->client->buttons & BUTTON_ATTACK))
		{
			ent->client->machinegun_shots = 0;
			ent->client->ps.gunframe++;
			return;
		}

		if (ent->client->ps.gunframe == 5)
			ent->client->ps.gunframe = 4;
		else
			ent->client->ps.gunframe = 5;

		if (ent->client->pers.inventory[ent->client->ammo_index] < 1)
		{
			ent->client->ps.gunframe = 6;
			if (level.time >= ent->pain_debounce_time)
			{
				gi.sound(ent, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1, ATTN_NORM, 0);
				ent->pain_debounce_time = level.time + 1;
			}
			NoAmmoWeaponChange (ent);
			return;
		}

		if (is_quad)
		{
			damage *= 4;
			kick *= 4;
		}

		for (i=1 ; i<3 ; i++)
		{
			ent->client->kick_origin[i] = crandom() * 0.35;
			ent->client->kick_angles[i] = crandom() * 0.7;
		}
		ent->client->kick_origin[0] = crandom() * 0.35;
		ent->client->kick_angles[0] = ent->client->machinegun_shots * -1.5;

		// raise the gun as it is firing
		if (!deathmatch->value)
		{
			ent->client->machinegun_shots++;
			if (ent->client->machinegun_shots > 9)
				ent->client->machinegun_shots = 9;
		}

		// get start / end positions
		VectorAdd (ent->client->v_angle, ent->client->kick_angles, angles);
		AngleVectors (angles, forward, right, NULL);
		VectorSet(offset, 0, 8, ent->viewheight-8);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);
		fire_bullet (ent, start, forward, damage, kick, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MOD_MACHINEGUN);

		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte (MZ_MACHINEGUN | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index]--;

		ent->client->anim_priority = ANIM_ATTACK;
		if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
		{
			ent->s.frame = FRAME_crattak1 - (int) (random()+0.25);
			ent->client->anim_end = FRAME_crattak9;
		}
		else
		{
			ent->s.frame = FRAME_attack1 - (int) (random()+0.25);
			ent->client->anim_end = FRAME_attack8;
		}
	}
	"""
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	angles = np.zeros((3,), dtype=np.float32)
	damage = 8
	kick = 2
	offset = np.zeros((3,), dtype=np.float32)

	if not (ent.client.buttons & q_shared.BUTTON_ATTACK):
		ent.client.machinegun_shots = 0
		ent.client.ps.gunframe += 1
		return

	if ent.client.ps.gunframe == 5:
		ent.client.ps.gunframe = 4
	else:
		ent.client.ps.gunframe = 5

	if ent.client.pers.inventory[ent.client.ammo_index] < 1:
		ent.client.ps.gunframe = 6
		if g_main.level.time >= ent.pain_debounce_time:
			g_main.gi.sound(ent, q_shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, q_shared.ATTN_NORM, 0)
			ent.pain_debounce_time = g_main.level.time + 1
		NoAmmoWeaponChange (ent)
		return

	if is_quad:
		damage *= 4
		kick *= 4

	for i in range(1, 3):
		ent.client.kick_origin[i] = g_local.crandom() * 0.35
		ent.client.kick_angles[i] = g_local.crandom() * 0.7
	ent.client.kick_origin[0] = g_local.crandom() * 0.35
	ent.client.kick_angles[0] = ent.client.machinegun_shots * -1.5

	# raise the gun as it is firing
	if not g_main.deathmatch.value:
		ent.client.machinegun_shots += 1
		if ent.client.machinegun_shots > 9:
			ent.client.machinegun_shots = 9

	# get start / end positions
	q_shared.VectorAdd (ent.client.v_angle, ent.client.kick_angles, angles)
	q_shared.AngleVectors (angles, forward, right, None)
	q_shared.VectorSet(offset, 0, 8, ent.viewheight-8)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)
	g_weapon.fire_bullet (ent, start, forward, damage, kick, g_local.DEFAULT_BULLET_HSPREAD, g_local.DEFAULT_BULLET_VSPREAD, g_local.MOD_MACHINEGUN)

	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (q_shared.MZ_MACHINEGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1

	ent.client.anim_priority = g_local.ANIM_ATTACK
	if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
		ent.s.frame = FRAME_crattak1 - int(_r.random()+0.25)
		ent.client.anim_end = FRAME_crattak9
	else:
		ent.s.frame = FRAME_attack1 - int(_r.random()+0.25)
		ent.client.anim_end = FRAME_attack8


def Weapon_Machinegun (ent):
	"""
	void Weapon_Machinegun (edict_t *ent)
	{
		static int	pause_frames[]	= {23, 45, 0};
		static int	fire_frames[]	= {4, 5, 0};

		Weapon_Generic (ent, 3, 5, 45, 49, pause_frames, fire_frames, Machinegun_Fire);
	}
	"""
	pause_frames = [23, 45, 0]
	fire_frames = [4, 5, 0]

	Weapon_Generic (ent, 3, 5, 45, 49, pause_frames, fire_frames, Machinegun_Fire)


def Chaingun_Fire (ent):
	"""
	void Chaingun_Fire (edict_t *ent)
	{
		int			i;
		int			shots;
		vec3_t		start;
		vec3_t		forward, right, up;
		float		r, u;
		vec3_t		offset;
		int			damage;
		int			kick = 2;

		if (deathmatch->value)
			damage = 6;
		else
			damage = 8;

		if (ent->client->ps.gunframe == 5)
			gi.sound(ent, CHAN_AUTO, gi.soundindex("weapons/chngnu1a.wav"), 1, ATTN_IDLE, 0);

		if ((ent->client->ps.gunframe == 14) && !(ent->client->buttons & BUTTON_ATTACK))
		{
			ent->client->ps.gunframe = 32;
			ent->client->weapon_sound = 0;
			return;
		}
		else if ((ent->client->ps.gunframe == 21) && (ent->client->buttons & BUTTON_ATTACK)
			&& ent->client->pers.inventory[ent->client->ammo_index])
		{
			ent->client->ps.gunframe = 15;
		}
		else
		{
			ent->client->ps.gunframe++;
		}

		if (ent->client->ps.gunframe == 22)
		{
			ent->client->weapon_sound = 0;
			gi.sound(ent, CHAN_AUTO, gi.soundindex("weapons/chngnd1a.wav"), 1, ATTN_IDLE, 0);
		}
		else
		{
			ent->client->weapon_sound = gi.soundindex("weapons/chngnl1a.wav");
		}

		ent->client->anim_priority = ANIM_ATTACK;
		if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
		{
			ent->s.frame = FRAME_crattak1 - (ent->client->ps.gunframe & 1);
			ent->client->anim_end = FRAME_crattak9;
		}
		else
		{
			ent->s.frame = FRAME_attack1 - (ent->client->ps.gunframe & 1);
			ent->client->anim_end = FRAME_attack8;
		}

		if (ent->client->ps.gunframe <= 9)
			shots = 1;
		else if (ent->client->ps.gunframe <= 14)
		{
			if (ent->client->buttons & BUTTON_ATTACK)
				shots = 2;
			else
				shots = 1;
		}
		else
			shots = 3;

		if (ent->client->pers.inventory[ent->client->ammo_index] < shots)
			shots = ent->client->pers.inventory[ent->client->ammo_index];

		if (!shots)
		{
			if (level.time >= ent->pain_debounce_time)
			{
				gi.sound(ent, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1, ATTN_NORM, 0);
				ent->pain_debounce_time = level.time + 1;
			}
			NoAmmoWeaponChange (ent);
			return;
		}

		if (is_quad)
		{
			damage *= 4;
			kick *= 4;
		}

		for (i=0 ; i<3 ; i++)
		{
			ent->client->kick_origin[i] = crandom() * 0.35;
			ent->client->kick_angles[i] = crandom() * 0.7;
		}

		for (i=0 ; i<shots ; i++)
		{
			// get start / end positions
			AngleVectors (ent->client->v_angle, forward, right, up);
			r = 7 + crandom()*4;
			u = crandom()*4;
			VectorSet(offset, 0, r, u + ent->viewheight-8);
			P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);

			fire_bullet (ent, start, forward, damage, kick, DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MOD_CHAINGUN);
		}

		// send muzzle flash
		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte ((MZ_CHAINGUN1 + shots - 1) | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index] -= shots;
	}
	"""
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)
	kick = 2

	if g_main.deathmatch.value:
		damage = 6
	else:
		damage = 8

	if ent.client.ps.gunframe == 5:
		g_main.gi.sound(ent, q_shared.CHAN_AUTO, g_main.gi.soundindex("weapons/chngnu1a.wav"), 1, q_shared.ATTN_IDLE, 0)

	if (ent.client.ps.gunframe == 14) and not (ent.client.buttons & q_shared.BUTTON_ATTACK):
		ent.client.ps.gunframe = 32
		ent.client.weapon_sound = 0
		return
	elif (ent.client.ps.gunframe == 21) and (ent.client.buttons & q_shared.BUTTON_ATTACK) and ent.client.pers.inventory[ent.client.ammo_index]:
		ent.client.ps.gunframe = 15
	else:
		ent.client.ps.gunframe += 1

	if ent.client.ps.gunframe == 22:
		ent.client.weapon_sound = 0
		g_main.gi.sound(ent, q_shared.CHAN_AUTO, g_main.gi.soundindex("weapons/chngnd1a.wav"), 1, q_shared.ATTN_IDLE, 0)
	else:
		ent.client.weapon_sound = g_main.gi.soundindex("weapons/chngnl1a.wav")

	ent.client.anim_priority = g_local.ANIM_ATTACK
	if ent.client.ps.pmove.pm_flags & q_shared.PMF_DUCKED:
		ent.s.frame = FRAME_crattak1 - (ent.client.ps.gunframe & 1)
		ent.client.anim_end = FRAME_crattak9
	else:
		ent.s.frame = FRAME_attack1 - (ent.client.ps.gunframe & 1)
		ent.client.anim_end = FRAME_attack8

	if ent.client.ps.gunframe <= 9:
		shots = 1
	elif ent.client.ps.gunframe <= 14:
		if ent.client.buttons & q_shared.BUTTON_ATTACK:
			shots = 2
		else:
			shots = 1
	else:
		shots = 3

	if ent.client.pers.inventory[ent.client.ammo_index] < shots:
		shots = ent.client.pers.inventory[ent.client.ammo_index]

	if not shots:
		if g_main.level.time >= ent.pain_debounce_time:
			g_main.gi.sound(ent, q_shared.CHAN_VOICE, g_main.gi.soundindex("weapons/noammo.wav"), 1, q_shared.ATTN_NORM, 0)
			ent.pain_debounce_time = g_main.level.time + 1
		NoAmmoWeaponChange (ent)
		return

	if is_quad:
		damage *= 4
		kick *= 4

	for i in range(0, 3):
		ent.client.kick_origin[i] = g_local.crandom() * 0.35
		ent.client.kick_angles[i] = g_local.crandom() * 0.7

	for i in range(0, shots):
		# get start / end positions
		q_shared.AngleVectors (ent.client.v_angle, forward, right, up)
		r = 7 + g_local.crandom()*4
		u = g_local.crandom()*4
		q_shared.VectorSet(offset, 0, r, u + ent.viewheight-8)
		P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)

		g_weapon.fire_bullet (ent, start, forward, damage, kick, g_local.DEFAULT_BULLET_HSPREAD, g_local.DEFAULT_BULLET_VSPREAD, g_local.MOD_CHAINGUN)

	# send muzzle flash
	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte ((q_shared.MZ_CHAINGUN1 + shots - 1) | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= shots


def Weapon_Chaingun (ent):
	"""
	void Weapon_Chaingun (edict_t *ent)
	{
		static int	pause_frames[]	= {38, 43, 51, 61, 0};
		static int	fire_frames[]	= {5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 0};

		Weapon_Generic (ent, 4, 31, 61, 64, pause_frames, fire_frames, Chaingun_Fire);
	}
	"""
	pause_frames = [38, 43, 51, 61, 0]
	fire_frames = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 0]

	Weapon_Generic (ent, 4, 31, 61, 64, pause_frames, fire_frames, Chaingun_Fire)


def weapon_shotgun_fire (ent):
	"""
	void weapon_shotgun_fire (edict_t *ent)
	{
		vec3_t		start;
		vec3_t		forward, right;
		vec3_t		offset;
		int			damage = 4;
		int			kick = 8;

		if (ent->client->ps.gunframe == 9)
		{
			ent->client->ps.gunframe++;
			return;
		}

		AngleVectors (ent->client->v_angle, forward, right, NULL);

		VectorScale (forward, -2, ent->client->kick_origin);
		ent->client->kick_angles[0] = -2;

		VectorSet(offset, 0, 8,  ent->viewheight-8);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);

		if (is_quad)
		{
			damage *= 4;
			kick *= 4;
		}

		if (deathmatch->value)
			fire_shotgun (ent, start, forward, damage, kick, 500, 500, DEFAULT_DEATHMATCH_SHOTGUN_COUNT, MOD_SHOTGUN);
		else
			fire_shotgun (ent, start, forward, damage, kick, 500, 500, DEFAULT_SHOTGUN_COUNT, MOD_SHOTGUN);

		// send muzzle flash
		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte (MZ_SHOTGUN | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		ent->client->ps.gunframe++;
		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index]--;
	}
	"""
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)
	damage = 4
	kick = 8

	if ent.client.ps.gunframe == 9:
		ent.client.ps.gunframe += 1
		return

	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)

	q_shared.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -2

	q_shared.VectorSet(offset, 0, 8,  ent.viewheight-8)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)

	if is_quad:
		damage *= 4
		kick *= 4

	if g_main.deathmatch.value:
		g_weapon.fire_shotgun (ent, start, forward, damage, kick, 500, 500, DEFAULT_DEATHMATCH_SHOTGUN_COUNT, g_local.MOD_SHOTGUN)
	else:
		g_weapon.fire_shotgun (ent, start, forward, damage, kick, 500, 500, DEFAULT_SHOTGUN_COUNT, g_local.MOD_SHOTGUN)

	# send muzzle flash
	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (q_shared.MZ_SHOTGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1
	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_Shotgun (ent):
	"""
	void Weapon_Shotgun (edict_t *ent)
	{
		static int	pause_frames[]	= {22, 28, 34, 0};
		static int	fire_frames[]	= {8, 9, 0};

		Weapon_Generic (ent, 7, 18, 36, 39, pause_frames, fire_frames, weapon_shotgun_fire);
	}
	"""
	pause_frames = [22, 28, 34, 0]
	fire_frames = [8, 9, 0]

	Weapon_Generic (ent, 7, 18, 36, 39, pause_frames, fire_frames, weapon_shotgun_fire)


def weapon_supershotgun_fire (ent):
	"""
	void weapon_supershotgun_fire (edict_t *ent)
	{
		vec3_t		start;
		vec3_t		forward, right;
		vec3_t		offset;
		vec3_t		v;
		int			damage = 6;
		int			kick = 12;

		AngleVectors (ent->client->v_angle, forward, right, NULL);

		VectorScale (forward, -2, ent->client->kick_origin);
		ent->client->kick_angles[0] = -2;

		VectorSet(offset, 0, 8,  ent->viewheight-8);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);

		if (is_quad)
		{
			damage *= 4;
			kick *= 4;
		}

		v[PITCH] = ent->client->v_angle[PITCH];
		v[YAW]   = ent->client->v_angle[YAW] - 5;
		v[ROLL]  = ent->client->v_angle[ROLL];
		AngleVectors (v, forward, NULL, NULL);
		fire_shotgun (ent, start, forward, damage, kick, DEFAULT_SHOTGUN_HSPREAD, DEFAULT_SHOTGUN_VSPREAD, DEFAULT_SSHOTGUN_COUNT/2, MOD_SSHOTGUN);
		v[YAW]   = ent->client->v_angle[YAW] + 5;
		AngleVectors (v, forward, NULL, NULL);
		fire_shotgun (ent, start, forward, damage, kick, DEFAULT_SHOTGUN_HSPREAD, DEFAULT_SHOTGUN_VSPREAD, DEFAULT_SSHOTGUN_COUNT/2, MOD_SSHOTGUN);

		// send muzzle flash
		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte (MZ_SSHOTGUN | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		ent->client->ps.gunframe++;
		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index] -= 2;
	}
	"""
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)
	v = np.zeros((3,), dtype=np.float32)
	damage = 6
	kick = 12

	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)

	q_shared.VectorScale (forward, -2, ent.client.kick_origin)
	ent.client.kick_angles[0] = -2

	q_shared.VectorSet(offset, 0, 8,  ent.viewheight-8)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)

	if is_quad:
		damage *= 4
		kick *= 4

	v[q_shared.PITCH] = ent.client.v_angle[q_shared.PITCH]
	v[q_shared.YAW]   = ent.client.v_angle[q_shared.YAW] - 5
	v[q_shared.ROLL]  = ent.client.v_angle[q_shared.ROLL]
	q_shared.AngleVectors (v, forward, None, None)
	g_weapon.fire_shotgun (ent, start, forward, damage, kick, DEFAULT_SHOTGUN_HSPREAD, DEFAULT_SHOTGUN_VSPREAD, DEFAULT_SSHOTGUN_COUNT/2, g_local.MOD_SSHOTGUN)
	v[q_shared.YAW]   = ent.client.v_angle[q_shared.YAW] + 5
	q_shared.AngleVectors (v, forward, None, None)
	g_weapon.fire_shotgun (ent, start, forward, damage, kick, DEFAULT_SHOTGUN_HSPREAD, DEFAULT_SHOTGUN_VSPREAD, DEFAULT_SSHOTGUN_COUNT/2, g_local.MOD_SSHOTGUN)

	# send muzzle flash
	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (q_shared.MZ_SSHOTGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1
	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 2


def Weapon_SuperShotgun (ent):
	"""
	void Weapon_SuperShotgun (edict_t *ent)
	{
		static int	pause_frames[]	= {29, 42, 57, 0};
		static int	fire_frames[]	= {7, 0};

		Weapon_Generic (ent, 6, 17, 57, 61, pause_frames, fire_frames, weapon_supershotgun_fire);
	}
	"""
	pause_frames = [29, 42, 57, 0]
	fire_frames = [7, 0]

	Weapon_Generic (ent, 6, 17, 57, 61, pause_frames, fire_frames, weapon_supershotgun_fire)


def weapon_railgun_fire (ent):
	"""
	void weapon_railgun_fire (edict_t *ent)
	{
		vec3_t		start;
		vec3_t		forward, right;
		vec3_t		offset;
		int			damage;
		int			kick;

		if (deathmatch->value)
		{	// normal damage is too extreme in dm
			damage = 100;
			kick = 200;
		}
		else
		{
			damage = 150;
			kick = 250;
		}

		if (is_quad)
		{
			damage *= 4;
			kick *= 4;
		}

		AngleVectors (ent->client->v_angle, forward, right, NULL);

		VectorScale (forward, -3, ent->client->kick_origin);
		ent->client->kick_angles[0] = -3;

		VectorSet(offset, 0, 7,  ent->viewheight-8);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);
		fire_rail (ent, start, forward, damage, kick);

		// send muzzle flash
		gi.WriteByte (svc_muzzleflash);
		gi.WriteShort (ent-g_edicts);
		gi.WriteByte (MZ_RAILGUN | is_silenced);
		gi.multicast (ent->s.origin, MULTICAST_PVS);

		ent->client->ps.gunframe++;
		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index]--;
	}
	"""
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	offset = np.zeros((3,), dtype=np.float32)

	if g_main.deathmatch.value:
		damage = 100
		kick = 200
	else:
		damage = 150
		kick = 250

	if is_quad:
		damage *= 4
		kick *= 4

	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)

	q_shared.VectorScale (forward, -3, ent.client.kick_origin)
	ent.client.kick_angles[0] = -3

	q_shared.VectorSet(offset, 0, 7,  ent.viewheight-8)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)
	g_weapon.fire_rail (ent, start, forward, damage, kick)

	# send muzzle flash
	g_main.gi.WriteByte (g_local.svc_muzzleflash)
	g_main.gi.WriteShort (g_main.g_edicts.index(ent))
	g_main.gi.WriteByte (q_shared.MZ_RAILGUN | is_silenced)
	g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

	ent.client.ps.gunframe += 1
	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 1


def Weapon_Railgun (ent):
	"""
	void Weapon_Railgun (edict_t *ent)
	{
		static int	pause_frames[]	= {56, 0};
		static int	fire_frames[]	= {4, 0};

		Weapon_Generic (ent, 3, 18, 56, 61, pause_frames, fire_frames, weapon_railgun_fire);
	}
	"""
	pause_frames = [56, 0]
	fire_frames = [4, 0]

	Weapon_Generic (ent, 3, 18, 56, 61, pause_frames, fire_frames, weapon_railgun_fire)


def weapon_bfg_fire (ent):
	"""
	void weapon_bfg_fire (edict_t *ent)
	{
		vec3_t	offset, start;
		vec3_t	forward, right;
		int		damage;
		float	damage_radius = 1000;

		if (deathmatch->value)
			damage = 200;
		else
			damage = 500;

		if (ent->client->ps.gunframe == 9)
		{
			// send muzzle flash
			gi.WriteByte (svc_muzzleflash);
			gi.WriteShort (ent-g_edicts);
			gi.WriteByte (MZ_BFG | is_silenced);
			gi.multicast (ent->s.origin, MULTICAST_PVS);

			ent->client->ps.gunframe++;

			PlayerNoise(ent, start, PNOISE_WEAPON);
			return;
		}

		// cells can go down during windup (from power armor hits), so
		// check again and abort firing if we don't have enough now
		if (ent->client->pers.inventory[ent->client->ammo_index] < 50)
		{
			ent->client->ps.gunframe++;
			return;
		}

		if (is_quad)
			damage *= 4;

		AngleVectors (ent->client->v_angle, forward, right, NULL);

		VectorScale (forward, -2, ent->client->kick_origin);

		// make a big pitch kick with an inverse fall
		ent->client->v_dmg_pitch = -40;
		ent->client->v_dmg_roll = crandom()*8;
		ent->client->v_dmg_time = level.time + DAMAGE_TIME;

		VectorSet(offset, 8, 8, ent->viewheight-8);
		P_ProjectSource (ent->client, ent->s.origin, offset, forward, right, start);
		fire_bfg (ent, start, forward, damage, 400, damage_radius);

		ent->client->ps.gunframe++;

		PlayerNoise(ent, start, PNOISE_WEAPON);

		if (! ( (int)dmflags->value & DF_INFINITE_AMMO ) )
			ent->client->pers.inventory[ent->client->ammo_index] -= 50;
	}
	"""
	offset = np.zeros((3,), dtype=np.float32)
	start = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	damage_radius = 1000

	if g_main.deathmatch.value:
		damage = 200
	else:
		damage = 500

	if ent.client.ps.gunframe == 9:
		# send muzzle flash
		g_main.gi.WriteByte (g_local.svc_muzzleflash)
		g_main.gi.WriteShort (g_main.g_edicts.index(ent))
		g_main.gi.WriteByte (q_shared.MZ_BFG | is_silenced)
		g_main.gi.multicast (ent.s.origin, MULTICAST_PVS)

		ent.client.ps.gunframe += 1

		PlayerNoise(ent, start, g_local.PNOISE_WEAPON)
		return

	# cells can go down during windup (from power armor hits), so
	# check again and abort firing if we don't have enough now
	if ent.client.pers.inventory[ent.client.ammo_index] < 50:
		ent.client.ps.gunframe += 1
		return

	if is_quad:
		damage *= 4

	q_shared.AngleVectors (ent.client.v_angle, forward, right, None)

	q_shared.VectorScale (forward, -2, ent.client.kick_origin)

	# make a big pitch kick with an inverse fall
	ent.client.v_dmg_pitch = -40
	ent.client.v_dmg_roll = g_local.crandom()*8
	ent.client.v_dmg_time = g_main.level.time + g_local.DAMAGE_TIME

	q_shared.VectorSet(offset, 8, 8, ent.viewheight-8)
	P_ProjectSource (ent.client, ent.s.origin, offset, forward, right, start)
	g_weapon.fire_bfg (ent, start, forward, damage, 400, damage_radius)

	ent.client.ps.gunframe += 1

	PlayerNoise(ent, start, g_local.PNOISE_WEAPON)

	if not ((int)(g_main.dmflags.value) & q_shared.DF_INFINITE_AMMO):
		ent.client.pers.inventory[ent.client.ammo_index] -= 50


def Weapon_BFG (ent):
	"""
	void Weapon_BFG (edict_t *ent)
	{
		static int	pause_frames[]	= {39, 45, 50, 55, 0};
		static int	fire_frames[]	= {9, 17, 0};

		Weapon_Generic (ent, 8, 32, 55, 58, pause_frames, fire_frames, weapon_bfg_fire);
	}
	"""
	pause_frames = [39, 45, 50, 55, 0]
	fire_frames = [9, 17, 0]

	Weapon_Generic (ent, 8, 32, 55, 58, pause_frames, fire_frames, weapon_bfg_fire)
