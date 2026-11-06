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

The savegame system.

=======================================================================
"""
from __future__ import annotations

import struct
import sys
import platform
import numpy as np
from enum import Enum
from common.header import shared
from common.header import common as common_h
from common.shared import shared as shared_c
from game import g_main
from game import g_items
from game import g_cmds
from game.header import local
from game.header import game as game_h
from game.player import client as p_client
from game.savegame import layout
from game.savegame.tables import gamefunc_list
from game.savegame.tables import gamemmove_list
from game.savegame.tables import stfields as stfields_t
from game.savegame.tables import entfields as entfields_t
from game.savegame.tables import levelfields as levelfields_t
from game.savegame.tables import clientfields as clientfields_t

"""
 * This is the Quake 2 savegame system, fixed by Yamagi
 * based on an idea by Knightmare of kmquake2. This major
 * rewrite of the original g_save.c is much more robust
 * and portable since it doesn't use any function pointers.
 *
 * Inner workings:
 * When the game is saved all function pointers are
 * translated into human readable function definition strings.
 * The same way all mmove_t pointers are translated. This
 * human readable strings are then written into the file.
 * At game load the human readable strings are retranslated
 * into the actual function pointers and struct pointers. The
 * pointers are generated at each compilation / start of the
 * client, thus the pointers are always correct.
 *
 * Limitations:
 * While savegames survive recompilations of the game source
 * and bigger changes in the source, there are some limitation
 * which a nearly impossible to fix without a object orientated
 * rewrite of the game.
 *  - If functions or mmove_t structs that a referencenced
 *    inside savegames are added or removed (e.g. the files
 *    in tables/ are altered) the load functions cannot
 *    reconnect all pointers and thus not restore the game.
 *  - If the operating system is changed internal structures
 *    may change in an unrepairable way.
 *  - If the architecture is changed pointer length and
 *    other internal datastructures change in an
 *    incompatible way.
 *  - If the edict_t struct is changed, savegames
 *    will break.
 * This is not so bad as it looks since functions and
 * struct won't be added and edict_t won't be changed
 * if no big, sweeping changes are done. The operating
 * system and architecture are in the hands of the user.

#include "../../common/header/common.h" // YQ2ARCH
#include "../header/local.h"
#include "savegame.h"
"""

"""
 * When ever the savegame version is changed, q2 will refuse to
 * load older savegames. This should be bumped if the files
 * in tables/ are changed, otherwise strange things may happen.
"""
SAVEGAMEVER = "YQ2-5"

"""
 * This macros are used to prohibit loading of savegames
 * created on other systems or architectures. This will
 * crash q2 in spectacular ways
"""

"""
 * Older operating system and architecture detection
 * macros, implemented by savegame version YQ2-1.
"""
# Q2PORT: the C picks these with #if defined(...)
OSTYPE_1 = {"Darwin": "MacOS X", "FreeBSD": "FreeBSD", "OpenBSD": "OpenBSD", "Linux": "Linux", "Windows": "Windows"}.get(platform.system(), "Unknown")
ARCH_1 = {"i386": "i386", "i686": "i386", "x86_64": "amd64", "AMD64": "amd64", "sparc64": "sparc64", "ia64": "ia64"}.get(platform.machine(), "unknown")

# =========================================================

"""
 * Prototypes for forward
 * declaration for all game
 * functions.
#include "tables/gamefunc_decs.h"

 * List with function pointer
 * to each of the functions
 * prototyped above.
#include "tables/gamefunc_list.h"

 * Prototypes for forward
 * declaration for all game
 * mmove_t functions.
#include "tables/gamemmove_decs.h"
"""

"""
 * List with pointers to
 * each of the mmove_t
 * functions prototyped
 * above.
"""
mmoveList = gamemmove_list.mmoveList #static const mmoveList_t []

"""
 * Spawntemp fields for entity spawning
"""
stfields = stfields_t.stfields #static const field_t []

"""
 * Entity fields to be saved
"""
fpentries_ent = [ #static const fplist_entry_t []
	(local.FOFS("die"), gamefunc_list.fnlist_die),
	(local.FOFS("pain"), gamefunc_list.fnlist_pain),
	(local.FOFS("prethink"), gamefunc_list.fnlist_prethink),
	(local.FOFS("think"), gamefunc_list.fnlist_think),
	(local.FOFS("touch"), gamefunc_list.fnlist_touch),
	(local.FOFS("use"), gamefunc_list.fnlist_use),
	(local.FOFS("blocked"), gamefunc_list.fnlist_blocked),
	(local.FOFS("monsterinfo.sight"), gamefunc_list.fnlist_mi_sight),
	(local.FOFS("monsterinfo.search"), gamefunc_list.fnlist_mi_search),
	(local.FOFS("monsterinfo.stand"), gamefunc_list.fnlist_mi_stand),
	(local.FOFS("monsterinfo.idle"), gamefunc_list.fnlist_mi_idle),
	(local.FOFS("monsterinfo.walk"), gamefunc_list.fnlist_mi_walk),
	(local.FOFS("monsterinfo.run"), gamefunc_list.fnlist_mi_run),
	(local.FOFS("monsterinfo.melee"), gamefunc_list.fnlist_mi_melee),
	(local.FOFS("monsterinfo.attack"), gamefunc_list.fnlist_mi_attack),
	(local.FOFS("monsterinfo.checkattack"), gamefunc_list.fnlist_mi_checkattack),
	(local.FOFS("monsterinfo.dodge"), gamefunc_list.fnlist_mi_dodge),
	(local.FOFS("moveinfo.endfunc"), gamefunc_list.fnlist_mv_end)
]
fplist_ent = fpentries_ent #static const fptrList_t

entfields = entfields_t.entfields #static const field_t []
sd_ent = (entfields, fplist_ent, "edict_s") #static const structdef_t: fields, fplist, struct (Q2PORT: its layout instead of sizeof)

"""
 * Level fields to be saved
"""
levelfields = levelfields_t.levelfields #static const field_t []
sd_level = (levelfields, None, "level_locals_t") #static const structdef_t

"""
 * Client fields to be saved
"""
clientfields = clientfields_t.clientfields #static const field_t []
sd_client = (clientfields, None, "gclient_s") #static const structdef_t

"""
 * Game struct to be saved
"""
sd_game = ([], None, "game_locals_t") #static const structdef_t

# =========================================================

def sg_fread(n: int, f)->bytes: #void *, size_t, FILE * (static)

	# Q2PORT: returns the bytes read instead of filling dest

	data = f.read(n)

	if len(data) != n:

		f.close()
		g_main.gi.error("Error reading %i bytes from save file", n)


	return data

def sg_fwrite(src, n: int, f): #const void *, size_t, FILE * (static)

	try:

		f.write(bytes(src[:n]))

	except OSError:

		f.close()
		g_main.gi.error("Error writing %i bytes to save file", n)

def FindSpawntempField(key: str): #const char * (returns const field_t *)

	"""
	const field_t *f;
	"""

	for f in stfields:

		if not shared_c.Q_strcasecmp(f.name, key):

			return f



	return None

def FindSpawnfield(key: str): #const char * (returns const field_t *)

	"""
	const field_t *f;
	"""

	for f in entfields:

		if not (f.flags & local.FFL_NOSPAWN) and not shared_c.Q_strcasecmp(f.name, key):

			return f



	return None

"""
 * Allocate the edicts and clients arrays.
"""
def InitAllocations(): #void (static)

	#int num_c = maxclients->value;
	#int num_e = maxentities->value;
	num_c = int(g_main.maxclients.value)
	num_e = int(g_main.maxentities.value)

	if num_c < 1:

		num_c = 1
		g_main.gi.cvar_forceset("maxclients", "1")


	if num_e < (num_c + 1):

		num_e = num_c + 1
		g_main.gi.cvar_forceset("maxentities", "%d" % (num_c + 1))


	g_main.g_edicts = [game_h.edict_t() for _ in range(num_e)] # gi.TagMalloc (num_e * sizeof(g_edicts[0]), TAG_GAME)
	g_main.game.maxentities = num_e

	g_main.glob.edicts = g_main.g_edicts
	g_main.glob.num_edicts = num_c + 1
	g_main.glob.max_edicts = num_e

	g_main.game.clients = [game_h.gclient_s() for _ in range(num_c)] # gi.TagMalloc (num_c * sizeof(game.clients[0]), TAG_GAME)
	g_main.game.maxclients = num_c

"""
 * This will be called when the dll is first loaded,
 * which only happens when a new game is started or
 * a save game is loaded.
"""
def InitGame(): #void

	g_main.gi.dprintf("Game is starting up.\n")
	g_main.gi.dprintf("Game is %s built on %s.\n", local.GAMEVERSION, common_h.BUILD_DATE)

	g_main.gun_x = g_main.gi.cvar("gun_x", "0", 0)
	g_main.gun_y = g_main.gi.cvar("gun_y", "0", 0)
	g_main.gun_z = g_main.gi.cvar("gun_z", "0", 0)
	g_main.sv_rollspeed = g_main.gi.cvar("sv_rollspeed", "200", 0)
	g_main.sv_rollangle = g_main.gi.cvar("sv_rollangle", "2", 0)
	g_main.sv_maxvelocity = g_main.gi.cvar("sv_maxvelocity", "2000", 0)
	g_main.sv_gravity = g_main.gi.cvar("sv_gravity", "800", 0)

	# noset vars
	g_main.dedicated = g_main.gi.cvar("dedicated", "0", shared.CVAR_NOSET)

	# latched vars
	g_main.sv_cheats = g_main.gi.cvar("cheats", "0", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.gi.cvar("gamename", local.GAMEVERSION, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.gi.cvar("gamedate", common_h.BUILD_DATE, shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.maxclients = g_main.gi.cvar("maxclients", "4", shared.CVAR_SERVERINFO | shared.CVAR_LATCH)
	g_main.maxspectators = g_main.gi.cvar("maxspectators", "4", shared.CVAR_SERVERINFO)
	g_main.deathmatch = g_main.gi.cvar("deathmatch", "0", shared.CVAR_LATCH)
	g_main.coop = g_main.gi.cvar("coop", "0", shared.CVAR_LATCH)
	g_main.coop_pickup_weapons = g_main.gi.cvar("coop_pickup_weapons", "1", shared.CVAR_ARCHIVE)
	g_main.coop_elevator_delay = g_main.gi.cvar("coop_elevator_delay", "1.0", shared.CVAR_ARCHIVE)
	g_main.skill = g_main.gi.cvar("skill", "1", shared.CVAR_LATCH)
	g_main.maxentities = g_main.gi.cvar("maxentities", "1024", shared.CVAR_LATCH)
	g_main.g_footsteps = g_main.gi.cvar("g_footsteps", "1", shared.CVAR_ARCHIVE)
	g_main.g_monsterfootsteps = g_main.gi.cvar("g_monsterfootsteps", "0", shared.CVAR_ARCHIVE)
	g_main.g_fix_triggered = g_main.gi.cvar ("g_fix_triggered", "0", 0)
	g_main.g_commanderbody_nogod = g_main.gi.cvar("g_commanderbody_nogod", "0", shared.CVAR_ARCHIVE)

	# change anytime vars
	g_main.dmflags = g_main.gi.cvar("dmflags", "0", shared.CVAR_SERVERINFO)
	g_main.fraglimit = g_main.gi.cvar("fraglimit", "0", shared.CVAR_SERVERINFO)
	g_main.timelimit = g_main.gi.cvar("timelimit", "0", shared.CVAR_SERVERINFO)
	g_main.password = g_main.gi.cvar("password", "", shared.CVAR_USERINFO)
	g_main.spectator_password = g_main.gi.cvar("spectator_password", "", shared.CVAR_USERINFO)
	g_main.needpass = g_main.gi.cvar("needpass", "0", shared.CVAR_SERVERINFO)
	g_main.filterban = g_main.gi.cvar("filterban", "1", 0)
	g_main.g_select_empty = g_main.gi.cvar("g_select_empty", "0", shared.CVAR_ARCHIVE)
	g_main.run_pitch = g_main.gi.cvar("run_pitch", "0.002", 0)
	g_main.run_roll = g_main.gi.cvar("run_roll", "0.005", 0)
	g_main.bob_up = g_main.gi.cvar("bob_up", "0.005", 0)
	g_main.bob_pitch = g_main.gi.cvar("bob_pitch", "0.002", 0)
	g_main.bob_roll = g_main.gi.cvar("bob_roll", "0.002", 0)

	# flood control
	g_main.flood_msgs = g_main.gi.cvar("flood_msgs", "4", 0)
	g_main.flood_persecond = g_main.gi.cvar("flood_persecond", "4", 0)
	g_main.flood_waitdelay = g_main.gi.cvar("flood_waitdelay", "10", 0)

	# dm map list
	g_main.sv_maplist = g_main.gi.cvar("sv_maplist", "", 0)

	# others
	g_main.aimfix = g_main.gi.cvar("aimfix", "0", shared.CVAR_ARCHIVE)
	g_main.g_machinegun_norecoil = g_main.gi.cvar("g_machinegun_norecoil", "0", shared.CVAR_ARCHIVE)
	g_main.g_quick_weap = g_main.gi.cvar("g_quick_weap", "1", shared.CVAR_ARCHIVE)
	g_main.g_swap_speed = g_main.gi.cvar("g_swap_speed", "1", shared.CVAR_ARCHIVE)

	g_main.game.__init__() #memset(&game, 0, sizeof(game));

	g_items.InitItems()

	# initialize entities and clients arrays
	InitAllocations()

# =========================================================

# Q2PORT: the C lists hold pointers; the Python lists hold names, so the
# functions and mmove_t structs are found by name in the game's modules.

_by_name = None #name -> function or mmove_t

def _game_objects()->dict:

	global _by_name

	if _by_name is None:

		_by_name = {}
		for modname, mod in sorted(sys.modules.items()):

			if mod is None or not (modname.startswith("game.") or modname == "game"):

				continue


			for k, v in vars(mod).items():

				if (callable(v) and getattr(v, "__module__", None) == modname) or isinstance(v, local.mmove_t):

					_by_name.setdefault(k, v)




	return _by_name

def GetFunctionList(field_ofs, fpl): #int, const fptrList_t * (returns static const functionList_t *)

	"""
	const fplist_entry_t *fpe;
	"""

	if not fpl:

		return None


	for ofs, fnlist in fpl:

		if ofs == field_ofs:

			return fnlist



	return None

"""
 * Helper function to get
 * the human readable function
 * definition by an address.
 * Called by WriteField1 and
 * WriteField2.
"""
def GetFunctionByAddress(adr, fnl): #const byte *, const functionList_t * (returns static const fnlist_entry_t *)

	"""
	const fnlist_entry_t *fne;
	"""

	if not fnl:

		return None


	for fne in fnl[1]:

		if _game_objects().get(fne) is adr:

			return fne



	return None

"""
 * Helper function to get the
 * pointer to a function by
 * its human readable name.
 * Called by WriteField1 and
 * WriteField2.
"""
def FindFunctionByName(name: str, fnl): #const char *, const functionList_t * (returns static byte *)

	"""
	const fnlist_entry_t *fne;
	"""

	if not fnl:

		return None


	for fne in fnl[1]:

		if name == fne:

			return _game_objects().get(fne)



	return None

"""
 * Helper function to get the
 * human readable definition of
 * a mmove_t struct by a pointer.
"""
def GetMmoveByAddress(adr): #const mmove_t * (returns static const mmoveList_t *)

	"""
	const mmoveList_t *mml;
	"""

	for mml in mmoveList:

		if _game_objects().get(mml) is adr:

			return mml



	return None

"""
 * Helper function to get the
 * pointer to a mmove_t struct
 * by a human readable definition.
"""
def FindMmoveByName(name: str): #const char * (returns static mmove_t *)

	"""
	const mmoveList_t *mml;
	"""

	for mml in mmoveList:

		if name == mml:

			return _game_objects().get(mml)



	return None

# =========================================================

def GetFuncLength(fn, fnl)->int: #const byte *, const functionList_t * (returns static int)

	"""
	const fnlist_entry_t *fne;
	"""

	if not fn:

		return 0


	fne = GetFunctionByAddress(fn, fnl)

	if not fne:

		g_main.gi.dprintf("%s: function at address %s not found in %s\n",
			"GetFuncLength", getattr(fn, "__name__", fn), fnl[0] if fnl else "unknown list")

		return 0


	return len(fne) + 1

def GetMmoveLength(mm)->int: #const mmove_t * (returns static int)

	"""
	const mmoveList_t *mmove;
	"""

	if not mm:

		return 0


	mmove = GetMmoveByAddress(mm)

	if not mmove:

		g_main.gi.dprintf("%s: mmove at address %s not found\n",
			"GetMmoveLength", mm)
		return 0


	return len(mmove) + 1

# Q2PORT: the C copies structs to and from the file with fwrite and fread;
# here each struct is packed into, or unpacked from, the bytes of its x86_64
# layout (game/savegame/layout.py). Pointers are written as 0 except where a
# field table converts them.

_missing = set() #names the port's structs lack, reported once

def _path_get(obj, path: str):

	for p in path.split("."):

		obj = getattr(obj, p)


	return obj

def _path_set(obj, path: str, value):

	parts = path.split(".")
	for p in parts[:-1]:

		obj = getattr(obj, p)


	setattr(obj, parts[-1], value)

def _field_offset(sname: str, path: str)->int:

	off = 0
	for p in path.split("."):

		for name, o, kind, count, sub in layout.LAYOUT[sname]["members"]:

			if name == p:

				off += o
				sname = sub
				break

		else:

			raise KeyError("%s has no member %s" % (sname, p))



	return off

def _scalar(v, kind):

	if isinstance(v, Enum):

		v = v.value


	if kind in "fd":

		return float(v) if v is not None else 0.0


	v = int(v) if v is not None else 0
	# C stores the bits; wrap to the member's width (e.g. FL_RESPAWN in an int)
	bits = {"i": 32, "I": 32, "h": 16, "H": 16, "b": 8, "B": 8, "c": 8}[kind]
	v &= (1 << bits) - 1
	if kind in "ihb" and v >= 1 << (bits - 1):

		v -= 1 << bits


	return v

def _pack(obj, sname: str, buf: bytearray, base: int):

	for name, off, kind, count, sub in layout.LAYOUT[sname]["members"]:

		if kind == "ptr":

			continue	# the buffer is zeroed


		if not hasattr(obj, name):

			if (sname, name) not in _missing:

				_missing.add((sname, name))
				g_main.gi.dprintf("savegame: the port's %s has no %s\n", sname, name)


			continue


		v = getattr(obj, name)
		at = base + off

		if kind == "struct":

			size = layout.LAYOUT[sub]["size"]
			if count == 1:

				_pack(v, sub, buf, at)

			else:

				for i in range(count):

					_pack(v[i], sub, buf, at + i * size)



		elif kind == "c":

			if v is None:

				v = ""


			raw = v.encode("latin-1", "replace") if isinstance(v, str) else bytes(v)
			raw = raw[:count]
			buf[at:at + len(raw)] = raw

		elif count == 1:

			struct.pack_into("<" + kind, buf, at, _scalar(v, kind))

		else:

			vals = [_scalar(x, kind) for x in v][:count]
			vals += [0] * (count - len(vals))
			struct.pack_into("<%d%s" % (count, kind), buf, at, *vals)

def _unpack(data, obj, sname: str, base: int):

	for name, off, kind, count, sub in layout.LAYOUT[sname]["members"]:

		if kind == "ptr":

			continue	# not restored; see the field tables


		at = base + off
		have = getattr(obj, name, None)

		if kind == "struct":

			size = layout.LAYOUT[sub]["size"]
			if have is None:

				continue


			if count == 1:

				_unpack(data, have, sub, at)

			else:

				for i in range(count):

					_unpack(data, have[i], sub, at + i * size)



		elif kind == "c":

			raw = bytes(data[at:at + count])
			setattr(obj, name, raw.split(b"\0", 1)[0].decode("latin-1"))

		elif count == 1:

			v = struct.unpack_from("<" + kind, data, at)[0]
			if isinstance(have, bool):

				v = bool(v)

			elif isinstance(have, Enum):

				v = type(have)(v)


			setattr(obj, name, v)

		else:

			vals = struct.unpack_from("<%d%s" % (count, kind), data, at)
			if isinstance(have, np.ndarray):

				have[:len(vals)] = vals

			elif isinstance(have, list):

				have[:] = list(vals)[:len(have)] + have[len(vals):]

			else:

				setattr(obj, name, np.array(vals, dtype=np.float32) if kind in "fd" else list(vals))

def _copy(obj, sname: str)->bytearray:

	# temp = *obj: the struct's bytes, pointers as 0
	temp = bytearray(layout.LAYOUT[sname]["size"])
	_pack(obj, sname, temp, 0)
	return temp

def _set_int(temp: bytearray, sname: str, path: str, value: int):

	# temp.path = value, for an int member of a copy
	struct.pack_into("<i", temp, _field_offset(sname, path), int(value))

"""
 * The following two functions are
 * doing the dirty work to write the
 * data generated by the functions
 * below this block into files.
"""
def WriteField1(f, field, base, temp, sname: str, fpl): #FILE *, const field_t *, void *, const fptrList_t * (static)

	# Q2PORT: base is the struct, temp the bytes being written; the C
	# changes the pointer in its copy of the struct

	"""
	void *p;
	size_t len;
	int index;
	"""

	if field.type in (local.fieldtype_t.F_INT, local.fieldtype_t.F_FLOAT,
		local.fieldtype_t.F_ANGLEHACK, local.fieldtype_t.F_VECTOR, local.fieldtype_t.F_IGNORE):

		return


	p = _path_get(base, field.ofs)
	at = _field_offset(sname, field.ofs)

	if field.type == local.fieldtype_t.F_LSTRING:

		if p:

			len_ = len(p.encode("latin-1", "replace")) + 1

		else:

			len_ = 0


		struct.pack_into("<i", temp, at, len_)

	elif field.type == local.fieldtype_t.F_EDICT:

		if p is None:

			index = -1

		else:

			index = g_main.g_edicts.index(p)


		struct.pack_into("<i", temp, at, index)

	elif field.type == local.fieldtype_t.F_ITEM:

		if p is None:

			index = -1

		else:

			index = local.ITEM_INDEX(p)


		struct.pack_into("<i", temp, at, index)

	elif field.type == local.fieldtype_t.F_FUNCTION:

		struct.pack_into("<i", temp, at, GetFuncLength(p, GetFunctionList(field.ofs, fpl)))

	elif field.type == local.fieldtype_t.F_MMOVE:

		struct.pack_into("<i", temp, at, GetMmoveLength(p))

	else:

		f.close()
		g_main.gi.error("%s: unknown field type", "WriteField1")

def WriteFunction(f, fn, fnl): #FILE *, const byte *, const functionList_t * (static)

	"""
	const fnlist_entry_t *fne;
	"""

	if not fn:

		return


	fne = GetFunctionByAddress(fn, fnl)

	if fne:

		len_ = len(fne) + 1
		sg_fwrite(fne.encode("latin-1") + b"\0", len_, f)

def WriteMmove(f, mm): #FILE *, const mmove_t * (static)

	"""
	const mmoveList_t *mmove;
	"""

	if not mm:

		return


	mmove = GetMmoveByAddress(mm)

	if mmove:

		len_ = len(mmove) + 1
		sg_fwrite(mmove.encode("latin-1") + b"\0", len_, f)

def WriteField2(f, field, base, fpl): #FILE *, const field_t *, const void *, const fptrList_t * (static)

	"""
	const void *p;
	"""

	if field.type == local.fieldtype_t.F_LSTRING:

		p = _path_get(base, field.ofs)
		if p:

			#size_t len;

			raw = p.encode("latin-1", "replace") + b"\0"
			len_ = len(raw)
			sg_fwrite(raw, len_, f)


	elif field.type == local.fieldtype_t.F_FUNCTION:

		WriteFunction(f, _path_get(base, field.ofs), GetFunctionList(field.ofs, fpl))

	elif field.type == local.fieldtype_t.F_MMOVE:

		WriteMmove(f, _path_get(base, field.ofs))

def WriteStruct(f, base, temp, sd): #FILE *, const void *, void *, const structdef_t * (static)

	# Q2PORT: temp is the copy's bytes (see _copy)

	"""
	const field_t *field;
	"""

	fields, fplist, sname = sd

	# change the pointers to lengths or indexes
	for field in fields:

		WriteField1(f, field, base, temp, sname, fplist)


	sg_fwrite(temp, layout.LAYOUT[sname]["size"], f)

	# now write any allocated data following the edict
	for field in fields:

		WriteField2(f, field, base, fplist)

# =========================================================

# int because that is how it's stored in the file
def ReadStringToBuf(f, len_: int, out_sz: int)->str: #FILE *, int, char *, size_t (static)

	# Q2PORT: returns the string instead of filling out

	if not len_:

		return ""


	if len_ < 0:

		f.close()
		g_main.gi.error("%s: string length < 0", "ReadStringToBuf")
		return ""


	if len_ >= out_sz:

		f.close()
		g_main.gi.error("%s: string is too long for buffer: %i > %i ",
				"ReadStringToBuf", len_, out_sz)
		return ""


	return sg_fread(len_, f).split(b"\0", 1)[0].decode("latin-1")

# int because that is how it's stored in the file
def ReadString(f, len_: int, tag: int): #FILE *, int, int (returns static char *)

	"""
	char *s;
	"""

	if not len_:

		return None


	if len_ < 0:

		f.close()
		g_main.gi.error("%s: string length < 0", "ReadString")
		return None


	s = sg_fread(len_, f).split(b"\0", 1)[0].decode("latin-1") # gi.TagMalloc(len + 1, tag)

	return s

def ReadFunction(f, len_: int, fnl): #FILE *, int, const functionList_t * (returns static byte *)

	"""
	char funcStr[128];
	byte *fn;
	"""

	if not len_:

		return None


	funcStr = ReadStringToBuf(f, len_, 128)

	fn = FindFunctionByName(funcStr, fnl)
	if not fn:

		g_main.gi.dprintf("%s: function %s not found in %s\n",
			"ReadFunction", funcStr, fnl[0] if fnl else "unknown list")


	return fn

def ReadMmove(f, len_: int): #FILE *, int (returns static mmove_t *)

	"""
	char mmoveStr[128];
	mmove_t *mm;
	"""

	if not len_:

		return None


	mmoveStr = ReadStringToBuf(f, len_, 128)

	mm = FindMmoveByName(mmoveStr)
	if not mm:

		g_main.gi.dprintf("%s: mmove %s not found\n",
			"ReadMmove", mmoveStr)


	return mm

"""
 * This function does the dirty
 * work to read the data from a
 * file. The processing of the
 * data is done in the functions
 * below
"""
def ReadField(f, field, base, data, sname: str, fpl): #FILE *, const field_t *, void *, const fptrList_t * (static)

	# Q2PORT: data is the struct's bytes as read, sname its layout

	"""
	void *p;
	int len;
	int index;
	"""

	if field.type in (local.fieldtype_t.F_INT, local.fieldtype_t.F_FLOAT,
		local.fieldtype_t.F_ANGLEHACK, local.fieldtype_t.F_VECTOR, local.fieldtype_t.F_IGNORE):

		return


	p = struct.unpack_from("<i", data, _field_offset(sname, field.ofs))[0] # *(int *)p

	if field.type == local.fieldtype_t.F_LSTRING:

		len_ = p
		_path_set(base, field.ofs, ReadString(f, len_, local.TAG_LEVEL))

	elif field.type == local.fieldtype_t.F_EDICT:

		index = p

		if (index < 0) or (index >= g_main.game.maxentities):

			_path_set(base, field.ofs, None)

		else:

			_path_set(base, field.ofs, g_main.g_edicts[index])


	elif field.type == local.fieldtype_t.F_ITEM:

		index = p
		_path_set(base, field.ofs, g_items.GetItemByIndex(index))

	elif field.type == local.fieldtype_t.F_FUNCTION:

		_path_set(base, field.ofs, ReadFunction(f, p, GetFunctionList(field.ofs, fpl)))

	elif field.type == local.fieldtype_t.F_MMOVE:

		_path_set(base, field.ofs, ReadMmove(f, p))

	else:

		f.close()
		g_main.gi.error("%s: unknown field type", "ReadField")

def ReadStruct(f, base, sd, save_ver: int): #FILE *, void *, const structdef_t *, short (static)

	"""
	const field_t *field;
	"""

	fields, fplist, sname = sd
	data = sg_fread(layout.LAYOUT[sname]["size"], f)
	_unpack(data, base, sname, 0)

	for field in fields:

		if field.save_ver <= save_ver:

			ReadField(f, field, base, data, sname, fplist)

# =========================================================

"""
 * Write the client struct into a file.
"""
def WriteClient(f, client): #FILE *, const gclient_t * (static)

	"""
	gclient_t temp;
	"""

	# all of the ints, floats, and vectors stay as they are
	temp = _copy(client, "gclient_s") # temp = *client;

	WriteStruct(f, client, temp, sd_client)

"""
 * Read the client struct from a file
"""
def SanitizeClientStruct(cl): #gclient_t * (static)

	"""
	client_persistant_t *p;
	"""

	p = cl.pers
	p.userinfo = p.userinfo[:shared.MAX_INFO_STRING - 1]
	p.netname = p.netname[:16 - 1]

	p = cl.resp.coop_respawn
	p.userinfo = p.userinfo[:shared.MAX_INFO_STRING - 1]
	p.netname = p.netname[:16 - 1]

	g_cmds.ValidateSelectedItem(cl)
	cl.ammo_index = g_items.GetWeaponAmmoIndex(cl.pers.weapon)
	cl.flood_whenhead = 0

def ReadClient(f, client, save_ver: int): #FILE *, gclient_t *, short (static)

	ReadStruct(f, client, sd_client, save_ver)
	SanitizeClientStruct(client)

	if save_ver < 3:

		p_client.InitClientResp(client)

# =========================================================

"""
 * Writes the game struct into
 * a file. This is called whenever
 * the game goes to a new level or
 * the user saves the game. The saved
 * information consists of:
 * - cross level data
 * - client states
 * - help computer info
"""
def WriteSaveHeader(f): #FILE * (static)

	"""
	savegameHeader_t sv;
	"""

	sv = bytearray(layout.LAYOUT["savegameHeader_t"]["size"]) # memset(&sv, 0, sizeof(sv));

	for name, value in (("ver", SAVEGAMEVER), ("game", local.GAMEVERSION), ("os", common_h.YQ2OSTYPE), ("arch", common_h.YQ2ARCH)):

		off = _field_offset("savegameHeader_t", name)
		raw = value.encode("latin-1")[:32 - 1 - 1] # Q_strlcpy(sv.ver, SAVEGAMEVER, sizeof(sv.ver) - 1);
		sv[off:off + len(raw)] = raw


	sg_fwrite(sv, len(sv), f)

def WriteGameLocals(f, autosave: bool): #FILE *, qboolean (static)

	"""
	game_locals_t temp;
	"""

	temp = _copy(g_main.game, "game_locals_t") # temp = game;

	_set_int(temp, "game_locals_t", "autosaved", autosave) # temp.autosaved = autosave;
	# temp.clients = NULL; (pointers are written as 0)
	_set_int(temp, "game_locals_t", "maxclients", 0) # temp.maxclients = 0;
	_set_int(temp, "game_locals_t", "maxentities", 0) # temp.maxentities = 0;
	_set_int(temp, "game_locals_t", "num_items", 0) # temp.num_items = 0;

	WriteStruct(f, g_main.game, temp, sd_game)

def WriteGame(filename: str, autosave: bool): #const char *, qboolean

	"""
	FILE *f;
	int i;
	"""

	if not autosave:

		p_client.SaveClientData()


	try:

		f = open(filename, "wb")

	except OSError:

		g_main.gi.error("%s: Couldn't open %s", "WriteGame", filename)
		return


	WriteSaveHeader(f)

	WriteGameLocals(f, autosave)

	for i in range(g_main.game.maxclients):

		WriteClient(f, g_main.game.clients[i])


	f.close()

"""
 * Read the game structs from
 * a file. Called when ever a
 * savegames is loaded.
"""
def GetSaveVersion(ver: str)->int: #const char * (returns static short)

	"""
	int i;
	"""

	version_mappings = [
		("YQ2-1", 1),
		("YQ2-2", 2),
		("YQ2-3", 3),
		("YQ2-4", 4),
		("YQ2-5", 5),
	]

	for verstr, vernum in version_mappings:

		if verstr == ver:

			return vernum



	return 0

def CheckSaveCompatibility(sv: dict, save_ver: int): #const savegameHeader_t *, short (returns static const char *)

	if save_ver == 0: # not found in mappings table

		return "Savegame from an incompatible version."


	if save_ver == 1:

		if sv["game"] != local.GAMEVERSION:

			return "Savegame from another game.so."


		if sv["os"] != OSTYPE_1:

			return "Savegame from another os."


		# Q2PORT: the _WIN32 case of the C isn't ported
		if sv["arch"] != ARCH_1:

			return "Savegame from another architecture."


	else: # all newer savegame versions

		if sv["game"] != local.GAMEVERSION:

			return "Savegame from another game.so."


		if sv["os"] != common_h.YQ2OSTYPE:

			return "Savegame from another os."


		if sv["arch"] != common_h.YQ2ARCH:

			return "Savegame from another architecture."



	return None

def SanitizeGameStruct(): #void (static)

	# these values are set by InitAllocations later
	g_main.game.clients = None
	g_main.game.maxclients = 0
	g_main.game.maxentities = 0

	# ensure inline strings are null terminated
	g_main.game.helpmessage1 = g_main.game.helpmessage1[:512 - 1]
	g_main.game.helpmessage2 = g_main.game.helpmessage2[:512 - 1]
	g_main.game.spawnpoint = g_main.game.spawnpoint[:512 - 1]

	# no longer using this field for security and stability reasons
	g_main.game.num_items = 0

def ReadGame(filename: str): #const char *

	"""
	savegameHeader_t sv;
	FILE *f;
	int i;
	const char *errmsg;
	short save_ver;
	"""

	g_main.gi.FreeTags(local.TAG_GAME)

	try:

		f = open(filename, "rb")

	except OSError:

		g_main.gi.error("%s: Couldn't open %s", "ReadGame", filename)
		return


	# Sanity checks
	data = sg_fread(layout.LAYOUT["savegameHeader_t"]["size"], f)
	sv = {}
	for name in ("ver", "game", "os", "arch"):

		off = _field_offset("savegameHeader_t", name)
		sv[name] = data[off:off + 32 - 1].split(b"\0", 1)[0].decode("latin-1")


	save_ver = GetSaveVersion(sv["ver"])
	errmsg = CheckSaveCompatibility(sv, save_ver)
	if errmsg:

		f.close()
		g_main.gi.error("%s", errmsg)
		return


	ReadStruct(f, g_main.game, sd_game, save_ver)
	SanitizeGameStruct()

	# initialize entities and clients arrays
	InitAllocations()

	for i in range(g_main.game.maxclients):

		ReadClient(f, g_main.game.clients[i], save_ver)


	f.close()

# ==========================================================

"""
 * Helper function to write the
 * edict into a file. Called by
 * WriteLevel.
"""
def WriteEdict(f, ent): #FILE *, const edict_t * (static)

	"""
	edict_t temp;
	"""

	# all of the ints, floats, and vectors stay as they are
	temp = _copy(ent, "edict_s") # temp = *ent;
	# temp.client = NULL; (pointers are written as 0)

	WriteStruct(f, ent, temp, sd_ent)

"""
 * Helper function to write the
 * level local data into a file.
 * Called by WriteLevel.
"""
def WriteLevelLocals(f): #FILE * (static)

	"""
	level_locals_t temp;
	"""

	# all of the ints, floats, and vectors stay as they are
	temp = _copy(g_main.level, "level_locals_t") # temp = level;

	WriteStruct(f, g_main.level, temp, sd_level)

"""
 * Writes the current level
 * into a file.
"""
def WriteLevel(filename: str): #const char *

	"""
	int i;
	FILE *f;
	"""

	try:

		f = open(filename, "wb")

	except OSError:

		g_main.gi.error("%s: Couldn't open %s", "WriteLevel", filename)
		return


	# write out edict size for checking
	i = layout.LAYOUT["edict_s"]["size"]
	sg_fwrite(struct.pack("<i", i), 4, f)

	# write out level_locals_t
	WriteLevelLocals(f)

	# write out all the entities
	for i in range(g_main.glob.num_edicts):

		#edict_t *ent;

		ent = g_main.g_edicts[i]

		if not ent.inuse:

			continue


		sg_fwrite(struct.pack("<i", i), 4, f)
		WriteEdict(f, ent)


	i = -1
	sg_fwrite(struct.pack("<i", i), 4, f)

	f.close()

# ==========================================================

"""
 * A helper function to
 * read the level local
 * data from a file.
 * Called by ReadLevel.
"""
def SanitizeLevelStruct(): #void (static)

	# ensure inline strings are null terminated
	g_main.level.level_name = g_main.level.level_name[:shared.MAX_QPATH - 1]
	g_main.level.mapname = g_main.level.mapname[:shared.MAX_QPATH - 1]
	g_main.level.nextmap = g_main.level.nextmap[:shared.MAX_QPATH - 1]

	g_main.level.pic_health = g_main.gi.imageindex("i_health")

	g_main.level.body_que %= local.BODY_QUEUE_SIZE

def ReadLevelLocals(f): #FILE * (static)

	ReadStruct(f, g_main.level, sd_level, 0)
	SanitizeLevelStruct()

"""
 * Reads a level back into the memory.
 * SpawnEntities were already called
 * in the same way when the level was
 * saved. All world links were cleared
 * before this function was called. When
 * this function is called, no clients
 * are connected to the server.
"""
def ReadLevel(filename: str): #const char *

	"""
	int entnum;
	FILE *f;
	int i;
	edict_t *ent;
	"""

	try:

		f = open(filename, "rb")

	except OSError:

		g_main.gi.error("%s: Couldn't open %s", "ReadLevel", filename)
		return


	# free any dynamic memory allocated by
	# loading the level  base state
	g_main.gi.FreeTags(local.TAG_LEVEL)

	# wipe all the entities
	for ent in g_main.g_edicts: # memset(g_edicts, 0, game.maxentities * sizeof(g_edicts[0]));

		ent.__init__()


	g_main.glob.num_edicts = int(g_main.maxclients.value) + 1

	# check edict size
	i = struct.unpack("<i", sg_fread(4, f))[0]

	if i != layout.LAYOUT["edict_s"]["size"]:

		f.close()
		g_main.gi.error("%s: mismatched edict size", "ReadLevel")
		return


	# load the level locals
	ReadLevelLocals(f)

	# load all the entities
	while True:

		entnum = struct.unpack("<i", sg_fread(4, f))[0]

		if (entnum < -1) or (entnum >= g_main.game.maxentities):

			f.close()
			g_main.gi.error("%s: entnum out of bounds: %d", "ReadLevel", entnum)


		if entnum == -1:

			break


		if entnum >= g_main.glob.num_edicts:

			g_main.glob.num_edicts = entnum + 1


		ent = g_main.g_edicts[entnum]
		ReadStruct(f, ent, sd_ent, 0)

		# sanitize certain field values
		ent.client = None
		ent.inuse = True
		ent.s.number = entnum

		if not ent.classname:

			ent.classname = "noclass"


		# let the server rebuild world links for this ent
		ent.area.__init__() # memset(&ent->area, 0, sizeof(ent->area));
		g_main.gi.linkentity(ent)


	f.close()

	# mark all clients as unconnected
	for i in range(int(g_main.maxclients.value)):

		ent = g_main.g_edicts[i + 1]
		ent.client = g_main.game.clients[i]
		ent.client.pers.connected = False


	# do any load time things at this point
	for i in range(g_main.glob.num_edicts):

		ent = g_main.g_edicts[i]

		if not ent.inuse:

			continue


		# fire any cross-level triggers
		if ent.classname:

			if ent.classname == "target_crosslevel_target":

				ent.nextthink = g_main.level.time + ent.delay
