"""
Copyright (C) 1997-2001 Id Software, Inc.
Copyright (C) 2011 Knightmare
Copyright (C) 2011 Yamagi Burmeister

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

Fields inside a level to be saved.

=======================================================================
"""
from __future__ import annotations

from game.header import local

levelfields = [ #field_t []
	local.field_t("changemap", local.LLOFS("changemap"), local.fieldtype_t.F_LSTRING),
	local.field_t("sight_client", local.LLOFS("sight_client"), local.fieldtype_t.F_EDICT),
	local.field_t("sight_entity", local.LLOFS("sight_entity"), local.fieldtype_t.F_EDICT),
	local.field_t("sound_entity", local.LLOFS("sound_entity"), local.fieldtype_t.F_EDICT),
	local.field_t("sound2_entity", local.LLOFS("sound2_entity"), local.fieldtype_t.F_EDICT),
]
