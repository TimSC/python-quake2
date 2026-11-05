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

The Quake II CVAR subsystem. Implements dynamic variable handling.

=======================================================================
"""
from __future__ import annotations

from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import cmdparser
from common import frame

"""
#include "header/common.h"
"""

cvar_vars = [] #cvar_t *, Q2PORT: the linked list is a Python list, sorted by name as in Yamagi
_cvar_index = {} # Q2PORT: name -> cvar_t, so Cvar_FindVar doesn't walk the list

class replacement_t(object):

	def __init__(self, old, new):

		self.old = old #char *
		self.new = new #char *

# An ugly hack to rewrite CVARs loaded from config.cfg
replacements = [ #static const replacement_t []
	replacement_t("cd_shuffle", "ogg_shuffle"),
	replacement_t("cl_anglekicks", "cl_kickangles"),
	replacement_t("cl_drawfps", "cl_showfps"),
	replacement_t("gl_drawentities", "r_drawentities"),
	replacement_t("gl_drawworld", "r_drawworld"),
	replacement_t("gl_fullbright", "r_fullbright"),
	replacement_t("gl_lerpmodels", "r_lerpmodels"),
	replacement_t("gl_lightlevel", "r_lightlevel"),
	replacement_t("gl_norefresh", "r_norefresh"),
	replacement_t("gl_novis", "r_novis"),
	replacement_t("gl_speeds", "r_speeds"),
	replacement_t("gl_clear", "r_clear"),
	replacement_t("gl_consolescale", "r_consolescale"),
	replacement_t("gl_hudscale", "r_hudscale"),
	replacement_t("gl_menuscale", "r_scale"),
	replacement_t("gl_customheight", "r_customheight"),
	replacement_t("gl_customwidth", "r_customheight"),
	replacement_t("gl_dynamic", "gl1_dynamic"),
	replacement_t("gl_farsee", "r_farsee"),
	replacement_t("gl_flashblend", "gl1_flashblend"),
	replacement_t("gl_lockpvs", "r_lockpvs"),
	replacement_t("gl_maxfps", "vid_maxfps"),
	replacement_t("gl_mode", "r_mode"),
	replacement_t("gl_modulate", "r_modulate"),
	replacement_t("gl_overbrightbits", "gl1_overbrightbits"),
	replacement_t("gl_palettedtextures", "r_palettedtextures"),
	replacement_t("gl1_palettedtextures", "r_palettedtextures"),
	replacement_t("gl_particle_min_size", "gl1_particle_min_size"),
	replacement_t("gl_particle_max_size", "gl1_particle_max_size"),
	replacement_t("gl_particle_size", "gl1_particle_size"),
	replacement_t("gl_particle_att_a", "gl1_particle_att_a"),
	replacement_t("gl_particle_att_b", "gl1_particle_att_b"),
	replacement_t("gl_particle_att_c", "gl1_particle_att_c"),
	replacement_t("gl_picmip", "gl1_picmip"),
	replacement_t("gl_pointparameters", "gl1_pointparameters"),
	replacement_t("gl_round_down", "gl1_round_down"),
	replacement_t("gl_saturatelightning", "gl1_saturatelightning"),
	replacement_t("gl_stencilshadows", "gl1_stencilshadows"),
	replacement_t("gl_stereo", "gl1_stereo"),
	replacement_t("gl_stereo_separation", "gl1_stereo_separation"),
	replacement_t("gl_stereo_anaglyph_colors", "gl1_stereo_anaglyph_colors"),
	replacement_t("gl_stereo_convergence", "gl1_stereo_convergence"),
	replacement_t("gl_swapinterval", "r_vsync"),
	replacement_t("gl_texturealphamode", "gl1_texturealphamode"),
	replacement_t("gl_texturesolidmode", "gl1_texturesolidmode"),
	replacement_t("gl_ztrick", "gl1_ztrick"),
	replacement_t("gl_msaa_samples", "r_msaa_samples"),
	replacement_t("gl_nolerp_list", "r_nolerp_list"),
	replacement_t("gl_retexturing", "r_retexturing"),
	replacement_t("gl_shadows", "r_shadows"),
	replacement_t("gl_anisotropic", "r_anisotropic"),
	replacement_t("gl_lightmap", "r_lightmap"),
	replacement_t("gl1_polyblend", "gl_polyblend"),
	replacement_t("gl_cull", "r_cull"),
	replacement_t("intensity", "gl1_intensity")
]
_replacements = {r.old: r for r in replacements} # Q2PORT: lookup table for Cvar_CheckReplacement

"""
An ugly hack to rewrite changed CVARs
"""
def Cvar_CheckReplacement(var_name: str, msg: bool)->str: #const char *, qboolean (returns static const char *)

	"""
	const replacement_t *r;
	"""

	r = _replacements.get(var_name)	# Q2PORT: in place of the loop over replacements
	if r is not None:

		if msg:

			clientserver.Com_Printf("cvar %s is deprecated, use %s instead\n",
				r.old, r.new)


		return r.new


	return var_name

def Cvar_CopyString(old_str: str, new_value: str)->str: #char *, const char * (returns static char *)
	# Q2PORT: Python strings are values, there is no buffer to reuse

	if new_value is None:

		new_value = ""


	return new_value

def Cvar_InfoValidate(s: str)->bool: #const char * (returns static qboolean)

	if "\\" in s:

		return False


	if "\"" in s:

		return False


	if ";" in s:

		return False


	return True

def Cvar_FindVar(var_name: str)->shared.cvar_t: #const char * (returns static cvar_t *)

	"""
	cvar_t *var;
	"""

	return _cvar_index.get(var_name)	# Q2PORT: in place of the walk over cvar_vars

def Cvar_IsFloat(s: str)->bool: #const char * (returns static qboolean)

	"""
	int dot = '.';
	"""
	dot = '.'
	i = 0

	if s[:1] == '-':

		i += 1


	if i >= len(s):

		return False


	while i < len(s):

		c = s[i]
		i += 1

		if c == dot:

			dot = ''

		elif c < '0' or c > '9':

			return False


	return True

def strtod(s: str)->float: #const char *, char ** (returns double)
	# Q2PORT: the C library function, with NULL for the end pointer: the longest number at the start, else 0

	return shared_c.atof(s)

def Cvar_VariableValue(var_name: str)->float: #const char * (returns float)

	"""
	const cvar_t *var;
	"""

	var = Cvar_FindVar(Cvar_CheckReplacement(var_name, True))

	if var is None:

		return 0


	return strtod(var.string)

def Cvar_VariableString(var_name: str)->str: #const char * (returns const char *)

	"""
	const cvar_t *var;
	"""

	var = Cvar_FindVar(Cvar_CheckReplacement(var_name, True))

	return var.string if var is not None else ""

def Cvar_CompleteVariable(partial: str)->str: #char * (returns char *)
	# Q2PORT: id's function, gone in Yamagi (Cmd_CompleteCommand completes cvars);
	# the console uses it until it's ported (group 10)

	length = len(partial)

	if length == 0:
		return None

	# check exact match
	for var in cvar_vars:
		if partial == var.name:
			return var.name

	# check partial match
	for var in cvar_vars:
		if partial == var.name[:length]:
			return var.name

	return None

"""
 * If the variable already exists, the value will not be set
 * The flags will be or'ed in if the variable exists.
"""
def Cvar_AddToList(var_name: str, var_value: str, flags: int)->shared.cvar_t: #const char *, const char *, int (returns static cvar_t *)

	"""
	cvar_t *var;
	cvar_t **pos;
	"""

	var = shared.cvar_t()

	var.name = var_name #CopyString(var_name);
	var.string = var_value #CopyString(var_value);
	var.default_string = var_value #CopyString(var_value);
	var.flags = flags
	var.modified = True
	var.value = strtod(var_value)

	pos = 0

	while pos < len(cvar_vars) and cvar_vars[pos].name < var.name:

		pos += 1


	cvar_vars.insert(pos, var) #var->next = *pos; *pos = var;
	_cvar_index[var.name] = var

	return var

def Cvar_GetNew(var_name: str, var_value: str, flags: int)->shared.cvar_t: #const char *, const char *, int (returns static cvar_t *)

	if var_value is None:

		return None


	if flags & (shared.CVAR_USERINFO | shared.CVAR_SERVERINFO):

		if not Cvar_InfoValidate(var_name):

			clientserver.Com_Printf("invalid info cvar name\n")
			return None


		if not Cvar_InfoValidate(var_value):

			clientserver.Com_Printf("invalid info cvar value\n")
			return None



	# if $game is the default one ("baseq2"), then use "" instead because
	# other code assumes this behavior (e.g. FS_BuildGameSpecificSearchPath())
	if var_name == "game" and var_value == common_h.BASEDIRNAME:

		var_value = ""


	return Cvar_AddToList(var_name, var_value, flags)

def Cvar_Get(var_name: str, var_value: str, flags: int)->shared.cvar_t: #const char *, const char *, int (returns cvar_t *)

	"""
	cvar_t *var;
	"""

	if var_value is None:

		return None


	if flags & (shared.CVAR_USERINFO | shared.CVAR_SERVERINFO):

		if not Cvar_InfoValidate(var_name):

			clientserver.Com_Printf("invalid info cvar name\n")
			return None


		if not Cvar_InfoValidate(var_value):

			clientserver.Com_Printf("invalid info cvar value\n")
			return None



	var_name = Cvar_CheckReplacement(var_name, True)

	# if $game is the default one ("baseq2"), then use "" instead because
	# other code assumes this behavior (e.g. FS_BuildGameSpecificSearchPath())
	if var_name == "game" and var_value == common_h.BASEDIRNAME:

		var_value = ""


	var = Cvar_FindVar(var_name)

	if var is not None:

		var.flags |= flags
		var.default_string = Cvar_CopyString(var.default_string, var_value)

		return var


	return Cvar_AddToList(var_name, var_value, flags)

def Cvar_SetVar(var: shared.cvar_t, value: str, force: bool)->shared.cvar_t: #cvar_t *, const char *, qboolean (returns static cvar_t *)

	global userinfo_modified

	from common import filesystem	# Q2PORT: imported here, the filesystem imports cvar

	if var.flags & (shared.CVAR_USERINFO | shared.CVAR_SERVERINFO):

		if not Cvar_InfoValidate(value):

			clientserver.Com_Printf("invalid info cvar value\n")
			return var



	# if $game is the default one ("baseq2"), then use "" instead because
	# other code assumes this behavior (e.g. FS_BuildGameSpecificSearchPath())
	if var.name == "game" and value == common_h.BASEDIRNAME:

		value = ""


	if not force:

		if var.flags & shared.CVAR_NOSET:

			clientserver.Com_Printf("%s is write protected.\n", var.name)
			return var


		if var.flags & shared.CVAR_LATCH:

			if var.latched_string is not None:

				if value == var.latched_string:

					return var


				var.latched_string = None

			else:

				if value == var.string:

					return var



			if clientserver.Com_ServerState():

				clientserver.Com_Printf("%s will be changed for next game.\n", var.name)
				var.latched_string = value #CopyString(value);

			else:

				var.string = Cvar_CopyString(var.string, value)
				var.value = strtod(var.string)

				if var.name == "game":

					filesystem.FS_BuildGameSpecificSearchPath(var.string)



			return var


	else:

		if var.latched_string is not None:

			var.latched_string = None



	if value == var.string:

		return var


	var.modified = True

	if var.flags & shared.CVAR_USERINFO:

		userinfo_modified = True


	var.string = Cvar_CopyString(var.string, value)
	var.value = strtod(var.string)

	return var

def Cvar_Set2(var_name: str, value: str, force: bool)->shared.cvar_t: #const char *, const char *, qboolean (returns static cvar_t *)

	"""
	cvar_t *var;
	"""

	var_name = Cvar_CheckReplacement(var_name, True)
	var = Cvar_FindVar(var_name)

	return Cvar_GetNew(var_name, value, 0) if (var is None) else \
		Cvar_SetVar(var, value, force)

def Cvar_ForceSet(var_name: str, value: str)->shared.cvar_t: #const char *, const char * (returns cvar_t *)

	return Cvar_Set2(var_name, value, True)

def Cvar_Set(var_name: str, value: str)->shared.cvar_t: #const char *, const char * (returns cvar_t *)

	return Cvar_Set2(var_name, value, False)

def Cvar_FullSet(var_name: str, value: str, flags: int)->shared.cvar_t: #const char *, const char *, int (returns cvar_t *)

	global userinfo_modified

	"""
	cvar_t *var;
	"""

	var_name = Cvar_CheckReplacement(var_name, True)
	var = Cvar_FindVar(var_name)

	if var is None:

		return Cvar_GetNew(var_name, value, flags)


	var.modified = True

	if var.flags & shared.CVAR_USERINFO:

		userinfo_modified = True


	# if $game is the default one ("baseq2"), then use "" instead because
	# other code assumes this behavior (e.g. FS_BuildGameSpecificSearchPath())
	if var_name == "game" and value == common_h.BASEDIRNAME:

		value = ""


	var.string = Cvar_CopyString(var.string, value)
	var.value = strtod(var.string)

	var.flags = flags

	return var

def Cvar_SetValue(var_name: str, value: float): #const char *, float

	#char val[32];

	if value == int(value):

		val = "%i" % int(value) #Com_sprintf(val, sizeof(val), "%i", (int)value);

	else:

		val = "%f" % value #Com_sprintf(val, sizeof(val), "%f", value);


	Cvar_Set(var_name, val)

"""
 * Any variables with latched values will now be updated
"""
def Cvar_GetLatchedVars(): #void

	from common import filesystem	# Q2PORT: imported here, the filesystem imports cvar

	"""
	cvar_t *var;
	"""

	for var in cvar_vars:

		if var.latched_string is None:

			continue


		#Z_Free(var->string);
		var.string = var.latched_string
		var.latched_string = None
		var.value = strtod(var.string)

		if var.name == "game":

			filesystem.FS_BuildGameSpecificSearchPath(var.string)

"""
 * Handles variable inspection and changing from the console
"""
def Cvar_Command()->bool: #(returns qboolean)

	"""
	cvar_t *v;
	"""

	# check variables
	v = Cvar_FindVar(Cvar_CheckReplacement(cmdparser.Cmd_Argv(0), True))

	if v is None:

		return False


	# perform a variable print or set
	if cmdparser.Cmd_Argc() == 1:

		clientserver.Com_Printf("\"%s\" is \"%s\"\n", v.name, v.string)
		return True


	# Another evil hack: The user has just changed 'game' trough
	# the console. We reset userGivenGame to that value, otherwise
	# we would revert to the initialy given game at disconnect.
	if v.name == "game":

		frame.userGivenGame = cmdparser.Cmd_Argv(1)[:shared.MAX_QPATH - 1]


	Cvar_SetVar(v, cmdparser.Cmd_Argv(1), False)
	return True

"""
 * Allows setting and defining of arbitrary cvars from console
"""
def Cvar_Set_f(): #void

	"""
	const char *firstarg;
	int c;
	"""

	c = cmdparser.Cmd_Argc()

	if (c != 3) and (c != 4):

		clientserver.Com_Printf("usage: set <variable> <value> [u / s]\n")
		return


	firstarg = Cvar_CheckReplacement(cmdparser.Cmd_Argv(1), False)

	if c == 4:

		#int flags;

		if cmdparser.Cmd_Argv(3) == "a":

			flags = shared.CVAR_ARCHIVE

		elif cmdparser.Cmd_Argv(3) == "u":

			flags = shared.CVAR_USERINFO

		elif cmdparser.Cmd_Argv(3) == "s":

			flags = shared.CVAR_SERVERINFO

		else:

			clientserver.Com_Printf("flags can only be 'a', 'u' or 's'\n")
			return


		Cvar_FullSet(firstarg, cmdparser.Cmd_Argv(2), flags)

	else:

		Cvar_Set(firstarg, cmdparser.Cmd_Argv(2))

"""
 * Appends lines containing "set variable value" for all variables
 * with the archive flag set to true.
"""
def Cvar_WriteVariables(path: str): #const char *

	"""
	const cvar_t *var;
	FILE *f;
	"""

	f = open(path, "a") #Q_fopen(path, "a");

	for var in cvar_vars:

		if var.flags & shared.CVAR_ARCHIVE:

			f.write("set {} \"{}\"\n".format(var.name, var.string))



	f.close()

def Cvar_List_f(): #void

	"""
	cvar_t *var;
	int i;
	"""

	i = 0

	for var in cvar_vars:

		if var.flags & shared.CVAR_ARCHIVE:

			clientserver.Com_Printf("*")

		else:

			clientserver.Com_Printf(" ")


		if var.flags & shared.CVAR_USERINFO:

			clientserver.Com_Printf("U")

		else:

			clientserver.Com_Printf(" ")


		if var.flags & shared.CVAR_SERVERINFO:

			clientserver.Com_Printf("S")

		else:

			clientserver.Com_Printf(" ")


		if var.flags & shared.CVAR_NOSET:

			clientserver.Com_Printf("-")

		elif var.flags & shared.CVAR_LATCH:

			clientserver.Com_Printf("L")

		else:

			clientserver.Com_Printf(" ")


		clientserver.Com_Printf(" %s \"%s\"\n", var.name, var.string)
		i += 1


	clientserver.Com_Printf("%i cvars\n", i)

userinfo_modified = False #qboolean

def Cvar_BitInfo(bit: int)->str: #int (returns static char *)

	"""
	static char info[MAX_INFO_STRING];
	cvar_t *var;
	"""

	info = ""

	for var in cvar_vars:

		if var.flags & bit:

			info = shared_c.Info_SetValueForKey(info, var.name, var.string)



	return info

"""
 * returns an info string containing
 * all the CVAR_USERINFO cvars
"""
def Cvar_Userinfo()->str: #(returns char *)

	return Cvar_BitInfo(shared.CVAR_USERINFO)

"""
 * returns an info string containing
 * all the CVAR_SERVERINFO cvars
"""
def Cvar_Serverinfo()->str: #(returns char *)

	return Cvar_BitInfo(shared.CVAR_SERVERINFO)

"""
 * Increments the given cvar by 1 or adds the
 * optional given float value to it.
"""
def Cvar_Inc_f(): #void

	"""
	const char *var_name;
	char string[MAX_QPATH];
	cvar_t *var;
	float value;
	"""

	if cmdparser.Cmd_Argc() < 2:

		clientserver.Com_Printf("Usage: %s <cvar> [value]\n", cmdparser.Cmd_Argv(0))
		return


	var_name = Cvar_CheckReplacement(cmdparser.Cmd_Argv(1), True)
	var = Cvar_FindVar(var_name)

	if var is None:

		clientserver.Com_Printf("%s is not a cvar\n", var_name)
		return


	if not Cvar_IsFloat(var.string):

		clientserver.Com_Printf("\"%s\" is \"%s\", can't %s\n", var.name, var.string, cmdparser.Cmd_Argv(0))
		return


	value = 1

	if cmdparser.Cmd_Argc() > 2:

		value = shared_c.atof(cmdparser.Cmd_Argv(2))


	if cmdparser.Cmd_Argv(0) == "dec":

		value = -value


	string = "%f" % (var.value + value)
	Cvar_SetVar(var, string, False)

"""
 * Resets a cvar to its default value.
"""
def Cvar_Reset_f(): #void

	"""
	const char *var_name;
	cvar_t *var;
	"""

	if cmdparser.Cmd_Argc() < 2:

		clientserver.Com_Printf("Usage: %s <cvar>\n", cmdparser.Cmd_Argv(0))
		return


	var_name = Cvar_CheckReplacement(cmdparser.Cmd_Argv(1), True)
	var = Cvar_FindVar(var_name)

	if var is None:

		clientserver.Com_Printf("%s is not a cvar\n", var_name)
		return


	clientserver.Com_Printf("%s: %s\n", var.name, var.default_string)
	Cvar_SetVar(var, var.default_string, False)

"""
 * Resets all known cvar (with the exception of `game') to
 * their default values.
"""
def Cvar_ResetAll_f(): #void

	"""
	cvar_t *var;
	"""

	for var in cvar_vars:

		if var.flags & shared.CVAR_NOSET:

			continue

		elif var.name == "game":

			continue


		Cvar_SetVar(var, var.default_string, False)

"""
 * Toggles a cvar between 0 and 1 or the given values.
"""
def Cvar_Toggle_f(): #void

	"""
	const char *var_name;
	cvar_t *var;
	int i, argc = Cmd_Argc();
	"""

	argc = cmdparser.Cmd_Argc()

	if argc < 2:

		clientserver.Com_Printf("Usage: %s <cvar> [values]\n", cmdparser.Cmd_Argv(0))
		return


	var_name = Cvar_CheckReplacement(cmdparser.Cmd_Argv(1), True)
	var = Cvar_FindVar(var_name)

	if var is None:

		clientserver.Com_Printf("%s is not a cvar\n", var_name)
		return


	if argc < 3:

		if var.string == "0":

			Cvar_SetVar(var, "1", False)

		elif var.string == "1":

			Cvar_SetVar(var, "0", False)

		else:

			clientserver.Com_Printf("\"%s\" is \"%s\", can't toggle\n", var.name, var.string)


		return


	for i in range(argc - 2):

		if not shared_c.Q_stricmp(var.string, cmdparser.Cmd_Argv(2 + i)):

			i = (i + 1) % (argc - 2)
			Cvar_SetVar(var, cmdparser.Cmd_Argv(2 + i), False)

			return



	clientserver.Com_Printf("\"%s\" is \"%s\", can't cycle\n", var.name, var.string)

"""
 * Reads in all archived cvars
"""
def Cvar_Init(): #void

	del cvar_vars[:] #cvar_vars = NULL;
	_cvar_index.clear()

	cmdparser.Cmd_AddCommand("cvarlist", Cvar_List_f)
	cmdparser.Cmd_AddCommand("dec", Cvar_Inc_f)
	cmdparser.Cmd_AddCommand("inc", Cvar_Inc_f)
	cmdparser.Cmd_AddCommand("reset", Cvar_Reset_f)
	cmdparser.Cmd_AddCommand("resetall", Cvar_ResetAll_f)
	cmdparser.Cmd_AddCommand("set", Cvar_Set_f)
	cmdparser.Cmd_AddCommand("toggle", Cvar_Toggle_f)

"""
 * Free list of cvars
"""
def Cvar_FreeList(): #void

	del cvar_vars[:] #cvar_vars = NULL;
	_cvar_index.clear()

def Cvar_Fini(): #void

	Cvar_FreeList()

	cmdparser.Cmd_RemoveCommand("cvarlist")
	cmdparser.Cmd_RemoveCommand("dec")
	cmdparser.Cmd_RemoveCommand("inc")
	cmdparser.Cmd_RemoveCommand("reset")
	cmdparser.Cmd_RemoveCommand("resetall")
	cmdparser.Cmd_RemoveCommand("set")
	cmdparser.Cmd_RemoveCommand("toggle")
