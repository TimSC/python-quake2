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
from game import q_shared, g_main, g_utils, g_ai

TRAIL_LENGTH = 8

trail = [None] * TRAIL_LENGTH
trail_head = 0
trail_active = False

def _next (n):
	return ((n + 1) & (TRAIL_LENGTH - 1))

def _prev (n):
	return ((n - 1) & (TRAIL_LENGTH - 1))


def PlayerTrail_Init ():
	global trail_head, trail_active

	if int(g_main.deathmatch.value):
		return

	for n in range(TRAIL_LENGTH):
		trail[n] = g_utils.G_Spawn()
		trail[n].classname = "player_trail"

	trail_head = 0
	trail_active = True
	"""
	int		n;

	if (deathmatch->value /* FIXME || coop */)
		return;

	for (n = 0; n < TRAIL_LENGTH; n++)
	{
		trail[n] = G_Spawn();
		trail[n]->classname = "player_trail";
	}

	trail_head = 0;
	trail_active = true;
	"""


def PlayerTrail_Add (spot): #vec3_t
	global trail_head

	if not trail_active:
		return

	q_shared.VectorCopy (spot, trail[trail_head].s.origin)

	trail[trail_head].timestamp = g_main.level.time

	temp = spot - trail[_prev(trail_head)].s.origin
	trail[trail_head].s.angles[1] = g_utils.vectoyaw (temp)

	trail_head = _next(trail_head)
	"""
	vec3_t	temp;

	if (!trail_active)
		return;

	VectorCopy (spot, trail[trail_head]->s.origin);

	trail[trail_head]->timestamp = level.time;

	VectorSubtract (spot, trail[PREV(trail_head)]->s.origin, temp);
	trail[trail_head]->s.angles[1] = vectoyaw (temp);

	trail_head = NEXT(trail_head);
	"""


def PlayerTrail_New (spot): #vec3_t
	if not trail_active:
		return

	PlayerTrail_Init ()
	PlayerTrail_Add (spot)
	"""
	if (!trail_active)
		return;

	PlayerTrail_Init ();
	PlayerTrail_Add (spot);
	"""


def PlayerTrail_PickFirst (self): #edict_t *
	if not trail_active:
		return None

	marker = trail_head
	n = TRAIL_LENGTH
	while n:
		if trail[marker].timestamp <= self.monsterinfo.trail_time:
			marker = _next(marker)
		else:
			break
		n -= 1

	if g_ai.visible(self, trail[marker]):
		return trail[marker]

	if g_ai.visible(self, trail[_prev(marker)]):
		return trail[_prev(marker)]

	return trail[marker]
	"""
	int		marker;
	int		n;

	if (!trail_active)
		return NULL;

	for (marker = trail_head, n = TRAIL_LENGTH; n; n--)
	{
		if(trail[marker]->timestamp <= self->monsterinfo.trail_time)
			marker = NEXT(marker);
		else
			break;
	}

	if (visible(self, trail[marker]))
	{
		return trail[marker];
	}

	if (visible(self, trail[PREV(marker)]))
	{
		return trail[PREV(marker)];
	}

	return trail[marker];
	"""


def PlayerTrail_PickNext (self): #edict_t *
	if not trail_active:
		return None

	marker = trail_head
	n = TRAIL_LENGTH
	while n:
		if trail[marker].timestamp <= self.monsterinfo.trail_time:
			marker = _next(marker)
		else:
			break
		n -= 1

	return trail[marker]
	"""
	int		marker;
	int		n;

	if (!trail_active)
		return NULL;

	for (marker = trail_head, n = TRAIL_LENGTH; n; n--)
	{
		if(trail[marker]->timestamp <= self->monsterinfo.trail_time)
			marker = NEXT(marker);
		else
			break;
	}

	return trail[marker];
	"""


def PlayerTrail_LastSpot ():
	return trail[_prev(trail_head)]
	"""
	return trail[PREV(trail_head)];
	"""
