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

Spawntemp fields used for entity spawning.

=======================================================================
"""
from __future__ import annotations

from game.header import local

stfields = [ #field_t []
	local.field_t("lip", local.STOFS("lip"), local.fieldtype_t.F_INT),
	local.field_t("distance", local.STOFS("distance"), local.fieldtype_t.F_INT),
	local.field_t("height", local.STOFS("height"), local.fieldtype_t.F_INT),
	local.field_t("noise", local.STOFS("noise"), local.fieldtype_t.F_LSTRING),
	local.field_t("pausetime", local.STOFS("pausetime"), local.fieldtype_t.F_FLOAT),
	local.field_t("item", local.STOFS("item"), local.fieldtype_t.F_LSTRING),
	local.field_t("gravity", local.STOFS("gravity"), local.fieldtype_t.F_LSTRING),
	local.field_t("sky", local.STOFS("sky"), local.fieldtype_t.F_LSTRING),
	local.field_t("skyrotate", local.STOFS("skyrotate"), local.fieldtype_t.F_FLOAT),
	local.field_t("skyaxis", local.STOFS("skyaxis"), local.fieldtype_t.F_VECTOR),
	local.field_t("minyaw", local.STOFS("minyaw"), local.fieldtype_t.F_FLOAT),
	local.field_t("maxyaw", local.STOFS("maxyaw"), local.fieldtype_t.F_FLOAT),
	local.field_t("minpitch", local.STOFS("minpitch"), local.fieldtype_t.F_FLOAT),
	local.field_t("maxpitch", local.STOFS("maxpitch"), local.fieldtype_t.F_FLOAT),
	local.field_t("music", local.STOFS("music"), local.fieldtype_t.F_LSTRING),
	local.field_t("nextmap", local.STOFS("nextmap"), local.fieldtype_t.F_LSTRING),
]
