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

Game fields to be saved.

=======================================================================
"""
from __future__ import annotations

from game.header import local

entfields = [ #field_t []
	local.field_t("classname", local.FOFS("classname"), local.fieldtype_t.F_LSTRING),
	local.field_t("model", local.FOFS("model"), local.fieldtype_t.F_LSTRING),
	local.field_t("spawnflags", local.FOFS("spawnflags"), local.fieldtype_t.F_INT),
	local.field_t("speed", local.FOFS("speed"), local.fieldtype_t.F_FLOAT),
	local.field_t("accel", local.FOFS("accel"), local.fieldtype_t.F_FLOAT),
	local.field_t("decel", local.FOFS("decel"), local.fieldtype_t.F_FLOAT),
	local.field_t("target", local.FOFS("target"), local.fieldtype_t.F_LSTRING),
	local.field_t("targetname", local.FOFS("targetname"), local.fieldtype_t.F_LSTRING),
	local.field_t("pathtarget", local.FOFS("pathtarget"), local.fieldtype_t.F_LSTRING),
	local.field_t("deathtarget", local.FOFS("deathtarget"), local.fieldtype_t.F_LSTRING),
	local.field_t("killtarget", local.FOFS("killtarget"), local.fieldtype_t.F_LSTRING),
	local.field_t("combattarget", local.FOFS("combattarget"), local.fieldtype_t.F_LSTRING),
	local.field_t("message", local.FOFS("message"), local.fieldtype_t.F_LSTRING),
	local.field_t("team", local.FOFS("team"), local.fieldtype_t.F_LSTRING),
	local.field_t("wait", local.FOFS("wait"), local.fieldtype_t.F_FLOAT),
	local.field_t("delay", local.FOFS("delay"), local.fieldtype_t.F_FLOAT),
	local.field_t("random", local.FOFS("random"), local.fieldtype_t.F_FLOAT),
	local.field_t("move_origin", local.FOFS("move_origin"), local.fieldtype_t.F_VECTOR),
	local.field_t("move_angles", local.FOFS("move_angles"), local.fieldtype_t.F_VECTOR),
	local.field_t("style", local.FOFS("style"), local.fieldtype_t.F_INT),
	local.field_t("count", local.FOFS("count"), local.fieldtype_t.F_INT),
	local.field_t("health", local.FOFS("health"), local.fieldtype_t.F_INT),
	local.field_t("sounds", local.FOFS("sounds"), local.fieldtype_t.F_INT),
	local.field_t("light", 0, local.fieldtype_t.F_IGNORE),
	local.field_t("dmg", local.FOFS("dmg"), local.fieldtype_t.F_INT),
	local.field_t("mass", local.FOFS("mass"), local.fieldtype_t.F_INT),
	local.field_t("volume", local.FOFS("volume"), local.fieldtype_t.F_FLOAT),
	local.field_t("attenuation", local.FOFS("attenuation"), local.fieldtype_t.F_FLOAT),
	local.field_t("map", local.FOFS("map"), local.fieldtype_t.F_LSTRING),
	local.field_t("origin", local.FOFS("s.origin"), local.fieldtype_t.F_VECTOR),
	local.field_t("angles", local.FOFS("s.angles"), local.fieldtype_t.F_VECTOR),
	local.field_t("angle", local.FOFS("s.angles"), local.fieldtype_t.F_ANGLEHACK),
	local.field_t("goalentity", local.FOFS("goalentity"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("movetarget", local.FOFS("movetarget"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("enemy", local.FOFS("enemy"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("oldenemy", local.FOFS("oldenemy"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("activator", local.FOFS("activator"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("groundentity", local.FOFS("groundentity"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("teamchain", local.FOFS("teamchain"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("teammaster", local.FOFS("teammaster"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("owner", local.FOFS("owner"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("mynoise", local.FOFS("mynoise"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("mynoise2", local.FOFS("mynoise2"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("target_ent", local.FOFS("target_ent"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("chain", local.FOFS("chain"), local.fieldtype_t.F_EDICT, local.FFL_NOSPAWN),
	local.field_t("prethink", local.FOFS("prethink"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("think", local.FOFS("think"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("blocked", local.FOFS("blocked"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("touch", local.FOFS("touch"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("use", local.FOFS("use"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("pain", local.FOFS("pain"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("die", local.FOFS("die"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("stand", local.FOFS("monsterinfo.stand"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("idle", local.FOFS("monsterinfo.idle"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("search", local.FOFS("monsterinfo.search"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("walk", local.FOFS("monsterinfo.walk"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("run", local.FOFS("monsterinfo.run"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("dodge", local.FOFS("monsterinfo.dodge"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("attack", local.FOFS("monsterinfo.attack"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("melee", local.FOFS("monsterinfo.melee"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("sight", local.FOFS("monsterinfo.sight"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("checkattack", local.FOFS("monsterinfo.checkattack"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("currentmove", local.FOFS("monsterinfo.currentmove"), local.fieldtype_t.F_MMOVE, local.FFL_NOSPAWN),
	local.field_t("endfunc", local.FOFS("moveinfo.endfunc"), local.fieldtype_t.F_FUNCTION, local.FFL_NOSPAWN),
	local.field_t("item", local.FOFS("item"), local.fieldtype_t.F_ITEM),
]
