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

Misc. utility functions for the game logic.

=======================================================================
"""
from __future__ import annotations

import math
import numpy as np
from game import g_main
from game import g_combat
from game.header.game import edict_t, SOLID_NOT, SVF_MONSTER
from common.header.shared import CHAN_AUTO, ATTN_NORM
from common.header.shared import AREA_TRIGGERS, AREA_SOLID, MASK_PLAYERSOLID
from game.header.local import DAMAGE_NO_PROTECTION, MOD_TELEFRAG
from common.header import shared
from common.shared import shared as shared_c
from game.header import local
from common.shared import rand

"""
#include "header/local.h"
"""

MOVEDIR_UP    = np.array([0, 0, 1], dtype=np.float32)
VEC_DOWN      = np.array([0, -2, 0], dtype=np.float32)
MOVEDIR_DOWN  = np.array([0, 0, -1], dtype=np.float32)

# static temporaries for tv() and vtos()
_tv_index = 0
_tv_vecs  = [np.zeros((3,), dtype=np.float32) for _ in range(8)]
_vtos_index = 0
_vtos_str = [""] * 8


def G_ProjectSource (point, distance, forward, right, result):
	result[0] = point[0] + forward[0] * distance[0] + right[0] * distance[1]
	result[1] = point[1] + forward[1] * distance[0] + right[1] * distance[1]
	result[2] = point[2] + forward[2] * distance[0] + right[2] * distance[1] + distance[2]


"""
=============
G_Find

Searches all active entities for the next one that holds
the matching string at fieldofs (use the FOFS() macro) in the structure.

Searches beginning at the edict after from, or the beginning if NULL
NULL will be returned if the end of the list is reached.

=============
"""
def G_Find (from_, fieldofs, match):
	if match is None:

		return None


	edicts = g_main.g_edicts
	if from_:
		i = edicts.index(from_) + 1
	else:
		i = 0

	for i in range(i, g_main.glob.num_edicts):
		e = edicts[i]
		if not e.inuse:
			continue
		s = getattr(e, fieldofs)
		if not s:
			continue
		if not shared_c.Q_stricmp (s, match):
			return e

	return None


"""
=================
findradius

Returns entities that have origins within a spherical area

findradius (origin, radius)
=================
"""
def findradius (from_, org, rad):
	global g_main
	edicts = g_main.g_edicts
	if from_:
		i = edicts.index(from_) + 1
	else:
		i = 0
	eorg = np.zeros((3,), dtype=np.float32)
	for i in range(i, g_main.glob.num_edicts):
		e = edicts[i]
		if not e.inuse:
			continue
		if e.solid == SOLID_NOT:
			continue
		for j in range(3):
			eorg[j] = org[j] - (e.s.origin[j] + (e.mins[j] + e.maxs[j])*0.5)
		if shared_c.VectorLength(eorg) > rad:
			continue
		return e

	return None


"""
=============
G_PickTarget

Searches all active entities for the next one that holds
the matching string at fieldofs (use the FOFS() macro) in the structure.

Searches beginning at the edict after from, or the beginning if NULL
NULL will be returned if the end of the list is reached.

=============
"""
MAXCHOICES = 8


def G_PickTarget(targetname): #char * (returns edict_t *)

	"""
	edict_t *ent = NULL;
	int num_choices = 0;
	edict_t *choice[MAXCHOICES];
	"""
	ent = None
	num_choices = 0
	choice = [None] * MAXCHOICES

	if targetname is None:

		g_main.gi.dprintf("G_PickTarget called with NULL targetname\n")
		return None


	while 1:

		ent = G_Find(ent, local.FOFS("targetname"), targetname)

		if not ent:

			break


		choice[num_choices] = ent
		num_choices += 1

		if num_choices == MAXCHOICES:

			break



	if not num_choices:

		g_main.gi.dprintf("G_PickTarget: target %s not found\n", targetname)
		return None


	return choice[rand.randk() % num_choices]


def Think_Delay (ent):
	if not ent:

		return


	G_UseTargets (ent, ent.activator)
	G_FreeEdict (ent)


"""
==============================
G_UseTargets

the global "activator" should be set to the entity that initiated the firing.

If self.delay is set, a DelayedUse entity will be created that will actually
do the SUB_UseTargets after that many seconds have passed.

Centerprints any self.message to the activator.

Search for (string)targetname in all entities that
match (string)self.target and call their .use function

==============================
"""
def G_UseTargets(ent, activator): #edict_t *, edict_t *

	"""
	edict_t *t;
	"""

	if not ent:

		return


	# check for a delay
	if ent.delay:

		# create a temp object to fire at a later time
		t = G_Spawn()
		t.classname = "DelayedUse"
		t.nextthink = g_main.level.time + ent.delay
		t.think = Think_Delay
		t.activator = activator

		if not activator:

			g_main.gi.dprintf("Think_Delay with no activator\n")


		t.message = ent.message
		t.target = ent.target
		t.killtarget = ent.killtarget
		return


	# print the message
	if activator and (ent.message) and not (activator.svflags & SVF_MONSTER):

		g_main.gi.centerprintf(activator, "%s", ent.message)

		if ent.noise_index:

			g_main.gi.sound(activator, CHAN_AUTO, ent.noise_index, 1, ATTN_NORM, 0)

		else:

			g_main.gi.sound(activator, CHAN_AUTO, g_main.gi.soundindex(
							"misc/talk1.wav"), 1, ATTN_NORM, 0)



	# kill killtargets
	if ent.killtarget:

		t = None

		while True:

			t = G_Find(t, local.FOFS("targetname"), ent.killtarget)
			if not t:
				break

			# decrement secret count if target_secret is removed
			if not shared_c.Q_stricmp(t.classname, "target_secret"):

				g_main.level.total_secrets -= 1


			# same deal with target_goal, but also turn off CD music if applicable
			elif not shared_c.Q_stricmp(t.classname, "target_goal"):

				g_main.level.total_goals -= 1

				if g_main.level.found_goals >= g_main.level.total_goals:

					g_main.gi.configstring(shared.CS_CDTRACK, "0")



			G_FreeEdict(t)

			if not ent.inuse:

				g_main.gi.dprintf("entity was removed while using killtargets\n")
				return




	# fire targets
	if ent.target:

		t = None

		while True:

			t = G_Find(t, local.FOFS("targetname"), ent.target)
			if not t:
				break

			# doors fire area portals in a specific way
			if not shared_c.Q_stricmp(t.classname, "func_areaportal") and \
				(not shared_c.Q_stricmp(ent.classname, "func_door") or
				 not shared_c.Q_stricmp(ent.classname, "func_door_rotating")):

				continue


			if t == ent:

				g_main.gi.dprintf("WARNING: %s used itself.\n", t.classname)

			else:

				if t.use:

					t.use(t, ent, activator)



			if not ent.inuse:

				g_main.gi.dprintf("entity was removed while using targets\n")
				return


"""
=============
TempVector

This is just a convenience function
for making temporary vectors for function calls
=============
"""
def tv (x, y, z):
	global _tv_index

	# use an array so that multiple tempvectors won't collide for a while
	v = _tv_vecs[_tv_index]
	_tv_index = (_tv_index + 1) & 7

	v[0] = x
	v[1] = y
	v[2] = z

	return v


"""
=============
VectorToString

This is just a convenience function
for printing vectors
=============
"""
def vtos (v):
	global _vtos_index

	# use an array so that multiple vtos won't collide
	s = "({} {} {})".format(int(v[0]), int(v[1]), int(v[2]))
	_vtos_str[_vtos_index] = s
	_vtos_index = (_vtos_index + 1) & 7

	return s


def G_SetMovedir (angles, movedir):
	if shared_c.VectorCompare (angles, local.VEC_UP):
		shared.VectorCopy (MOVEDIR_UP, movedir)
	elif shared_c.VectorCompare (angles, VEC_DOWN):
		shared.VectorCopy (MOVEDIR_DOWN, movedir)
	else:
		shared_c.AngleVectors (angles, movedir, None, None)

	shared.VectorClear (angles)


def vectoyaw (vec):
	#float yaw
	yaw = 0

	if vec[shared.PITCH] == 0:
		if vec[shared.YAW] > 0:
			yaw = 90
		elif vec[shared.YAW] < 0:
			yaw = -90
	else:
		yaw = int (math.atan2(vec[shared.YAW], vec[shared.PITCH]) * 180 / math.pi)
		if yaw < 0:
			yaw += 360

	return yaw


def vectoangles (value1, angles):
	#float forward, yaw, pitch
	if value1[1] == 0 and value1[0] == 0:
		yaw = 0
		if value1[2] > 0:
			pitch = 90
		else:
			pitch = 270
	else:
		if value1[0]:
			yaw = int (math.atan2(value1[1], value1[0]) * 180 / math.pi)
		elif value1[1] > 0:
			yaw = 90
		else:
			yaw = -90
		if yaw < 0:
			yaw += 360

		forward = math.sqrt (value1[0]*value1[0] + value1[1]*value1[1])
		pitch = int (math.atan2(value1[2], forward) * 180 / math.pi)
		if pitch < 0:
			pitch += 360

	angles[shared.PITCH] = -pitch
	angles[shared.YAW] = yaw
	angles[shared.ROLL] = 0


def G_CopyString (in_):
	# strings are immutable in Python
	if in_ is None:

		return None


	return in_


def G_InitEdict (e):
	if not e:

		return


	e.inuse = True
	e.classname = "noclass"
	e.gravity = 1.0
	e.s.number = g_main.g_edicts.index(e)


POLICY_DEFAULT = 0
POLICY_DESPERATE = 1

def G_FindFreeEdict(policy: int): #int (returns static edict_t *)

	"""
	edict_t *e;
	"""

	edicts = g_main.g_edicts
	for i in range(g_main.game.maxclients + 1, g_main.glob.num_edicts):

		e = edicts[i]
		# the first couple seconds of server time can involve a lot of
		# freeing and allocating, so relax the replacement policy
		if not e.inuse and (policy == POLICY_DESPERATE or e.freetime < 2.0 or (g_main.level.time - e.freetime) > 0.5):

			G_InitEdict(e)
			return e



	return None

def G_SpawnOptional(): #(returns edict_t *)

	e = G_FindFreeEdict(POLICY_DEFAULT)

	if e:

		return e


	if g_main.glob.num_edicts >= g_main.game.maxentities:

		return G_FindFreeEdict(POLICY_DESPERATE)


	e = g_main.g_edicts[g_main.glob.num_edicts]
	g_main.glob.num_edicts += 1
	G_InitEdict(e)

	return e

"""
=================
G_Spawn

Either finds a free edict, or allocates a new one.
Try to avoid reusing an entity that was recently freed, because it
can cause the client to think the entity morphed into something else
instead of being removed and recreated, which can cause interpolated
angles and bad trails.
=================
"""
def G_Spawn(): #(returns edict_t *)

	e = G_SpawnOptional()

	if not e:

		g_main.gi.error("%s: no free edicts", "G_Spawn")


	return e


"""
=================
G_FreeEdict

Marks the edict as free
=================
"""
def G_FreeEdict(ed): #edict_t *

	if not ed:

		return


	g_main.gi.unlinkentity(ed) # unlink from world

	if g_main.deathmatch.value or g_main.coop.value:

		if g_main.g_edicts.index(ed) <= (g_main.maxclients.value + local.BODY_QUEUE_SIZE):

			return


	else:

		if g_main.g_edicts.index(ed) <= g_main.maxclients.value:

			return



	ed.__dict__.update(edict_t().__dict__) #memset(ed, 0, sizeof(*ed));
	ed.classname = "freed"
	ed.freetime = g_main.level.time
	ed.inuse = False


"""
============
G_TouchTriggers

============
"""
def G_TouchTriggers (ent):
	#int i, num

	# dead things don't activate triggers!
	if not ent:

		return


	if ((ent.client or (ent.svflags & SVF_MONSTER)) and (ent.health <= 0)):
		return

	touch = [None] * shared.MAX_EDICTS
	num = g_main.gi.BoxEdicts (ent.absmin, ent.absmax, touch, shared.MAX_EDICTS, AREA_TRIGGERS)

	# be careful, it is possible to have an entity in this
	# list removed before we get to it (killtriggered)
	for i in range(num):
		hit = touch[i]
		if not hit.inuse:
			continue
		if not hit.touch:
			continue
		hit.touch (hit, ent, None, None)


"""
============
G_TouchSolids

Call after linking a new trigger in during gameplay
to force all entities it covers to immediately touch it
============
"""
def G_TouchSolids (ent):
	#int i, num

	if not ent:

		return


	touch = [None] * shared.MAX_EDICTS
	num = g_main.gi.BoxEdicts (ent.absmin, ent.absmax, touch, shared.MAX_EDICTS, AREA_SOLID)

	# be careful, it is possible to have an entity in this
	# list removed before we get to it (killtriggered)
	for i in range(num):
		hit = touch[i]
		if not hit.inuse:
			continue
		if ent.touch:
			ent.touch (hit, ent, None, None)
		if not ent.inuse:
			break


"""
==============================================================================

Kill box

==============================================================================
"""

"""
=================
KillBox

Kills all entities that would touch the proposed new positioning
of ent.  Ent should be unlinked before calling this!
=================
"""
def KillBox (ent):
	if not ent:

		return False


	while True:
		tr = g_main.gi.trace (ent.s.origin, ent.mins, ent.maxs, ent.s.origin, None, MASK_PLAYERSOLID)
		if not tr.ent:
			break

		# nail it
		g_combat.T_Damage (tr.ent, ent, ent, shared_c.vec3_origin, ent.s.origin, shared_c.vec3_origin, 100000, 0, DAMAGE_NO_PROTECTION, MOD_TELEFRAG)

		# if we didn't kill it, fail
		if tr.ent.solid:
			return False

	return True		# all clear
