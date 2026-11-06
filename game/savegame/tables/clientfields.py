"""
Copyright (C) 1997-2001 Id Software, Inc.
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

Fields of the client to be saved.

=======================================================================
"""
from __future__ import annotations

from game.header import local

clientfields = [ #field_t []
	local.field_t("pers.weapon", local.CLOFS("pers.weapon"), local.fieldtype_t.F_ITEM),
	local.field_t("pers.lastweapon", local.CLOFS("pers.lastweapon"), local.fieldtype_t.F_ITEM),
	local.field_t("newweapon", local.CLOFS("newweapon"), local.fieldtype_t.F_ITEM),
	local.field_t("resp.coop_respawn.weapon", local.CLOFS("resp.coop_respawn.weapon"), local.fieldtype_t.F_ITEM, 0, 3),
	local.field_t("resp.coop_respawn.lastweapon", local.CLOFS("resp.coop_respawn.lastweapon"), local.fieldtype_t.F_ITEM, 0, 3),
]
