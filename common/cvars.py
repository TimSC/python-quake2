"""Console variables (cvars): the registry and its console commands.

``CvarRegistry`` holds every cvar, sorted by name as Quake II lists them, and
keeps Yamagi's rules: renamed old names, info string validation, write
protected and latched cvars, and ``game`` as "" for the base game. It reaches
the rest of the engine only through the callbacks it is given, so it can be
used (and tested) on its own.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable

from common.header import shared
from common.shared import shared as shared_c

BASE_GAME = "baseq2"

# Old cvar names (e.g. in config.cfg files) and the names that replace them.
REPLACEMENTS: dict[str, str] = {
    "cd_shuffle": "ogg_shuffle",
    "cl_anglekicks": "cl_kickangles",
    "cl_drawfps": "cl_showfps",
    "gl_drawentities": "r_drawentities",
    "gl_drawworld": "r_drawworld",
    "gl_fullbright": "r_fullbright",
    "gl_lerpmodels": "r_lerpmodels",
    "gl_lightlevel": "r_lightlevel",
    "gl_norefresh": "r_norefresh",
    "gl_novis": "r_novis",
    "gl_speeds": "r_speeds",
    "gl_clear": "r_clear",
    "gl_consolescale": "r_consolescale",
    "gl_hudscale": "r_hudscale",
    "gl_menuscale": "r_scale",
    "gl_customheight": "r_customheight",
    "gl_customwidth": "r_customheight",  # sic, as in Yamagi
    "gl_dynamic": "gl1_dynamic",
    "gl_farsee": "r_farsee",
    "gl_flashblend": "gl1_flashblend",
    "gl_lockpvs": "r_lockpvs",
    "gl_maxfps": "vid_maxfps",
    "gl_mode": "r_mode",
    "gl_modulate": "r_modulate",
    "gl_overbrightbits": "gl1_overbrightbits",
    "gl_palettedtextures": "r_palettedtextures",
    "gl1_palettedtextures": "r_palettedtextures",
    "gl_particle_min_size": "gl1_particle_min_size",
    "gl_particle_max_size": "gl1_particle_max_size",
    "gl_particle_size": "gl1_particle_size",
    "gl_particle_att_a": "gl1_particle_att_a",
    "gl_particle_att_b": "gl1_particle_att_b",
    "gl_particle_att_c": "gl1_particle_att_c",
    "gl_picmip": "gl1_picmip",
    "gl_pointparameters": "gl1_pointparameters",
    "gl_round_down": "gl1_round_down",
    "gl_saturatelightning": "gl1_saturatelightning",
    "gl_stencilshadows": "gl1_stencilshadows",
    "gl_stereo": "gl1_stereo",
    "gl_stereo_separation": "gl1_stereo_separation",
    "gl_stereo_anaglyph_colors": "gl1_stereo_anaglyph_colors",
    "gl_stereo_convergence": "gl1_stereo_convergence",
    "gl_swapinterval": "r_vsync",
    "gl_texturealphamode": "gl1_texturealphamode",
    "gl_texturesolidmode": "gl1_texturesolidmode",
    "gl_ztrick": "gl1_ztrick",
    "gl_msaa_samples": "r_msaa_samples",
    "gl_nolerp_list": "r_nolerp_list",
    "gl_retexturing": "r_retexturing",
    "gl_shadows": "r_shadows",
    "gl_anisotropic": "r_anisotropic",
    "gl_lightmap": "r_lightmap",
    "gl1_polyblend": "gl_polyblend",
    "gl_cull": "r_cull",
    "intensity": "gl1_intensity",
}

INFO_FLAGS = shared.CVAR_USERINFO | shared.CVAR_SERVERINFO


def valid_info(text: str) -> bool:
    """Whether text may go into an info string."""
    return not any(c in text for c in '\\";')


def is_float(text: str) -> bool:
    """A number: an optional minus, digits and at most one dot."""
    body = text[1:] if text.startswith("-") else text
    return bool(body) and body.count(".") <= 1 and all("0" <= c <= "9" or c == "." for c in body)


def to_number(text: str) -> float:
    """C's strtod(text, NULL): the number at the start of text, else 0."""
    return shared_c.atof(text)


def format_value(value: float) -> str:
    """How a number is stored as a cvar's string."""
    return f"{int(value)}" if value == int(value) else f"{value:f}"


def _base_game(name: str, value: str) -> str:
    # "game" is "" for the base game, which other code relies on
    return "" if name == "game" and value == BASE_GAME else value


class CvarRegistry:
    """Every cvar, by name."""

    def __init__(self, *, print_: Callable[[str], None] = lambda text: None,
                 server_running: Callable[[], bool] = lambda: False,
                 game_changed: Callable[[str], None] = lambda game: None,
                 user_game_changed: Callable[[str], None] = lambda game: None) -> None:
        self.print = print_                    # console output
        self.server_running = server_running  # latched cvars wait while it runs
        self.game_changed = game_changed      # the game directory changed
        self.user_game_changed = user_game_changed  # the user set 'game' at the console
        self.vars: list[shared.cvar_t] = []   # sorted by name
        self._names: list[str] = []
        self._by_name: dict[str, shared.cvar_t] = {}
        self.userinfo_modified = False

    # ------------------------------------------------------------ lookup

    def replacement(self, name: str, warn: bool = True) -> str:
        """The current name for an old cvar name."""
        new = REPLACEMENTS.get(name)
        if new is None:
            return name
        if warn:
            self.print(f"cvar {name} is deprecated, use {new} instead\n")
        return new

    def find(self, name: str) -> shared.cvar_t | None:
        return self._by_name.get(name)

    def value(self, name: str) -> float:
        var = self.find(self.replacement(name))
        return 0 if var is None else to_number(var.string)

    def string(self, name: str) -> str:
        var = self.find(self.replacement(name))
        return "" if var is None else var.string

    def complete(self, partial: str) -> str | None:
        """The first cvar name matching partial exactly, else by prefix."""
        if not partial:
            return None
        if partial in self._by_name:
            return partial
        return next((v.name for v in self.vars if v.name.startswith(partial)), None)

    # ---------------------------------------------------------- creation

    def _add(self, name: str, value: str, flags: int) -> shared.cvar_t:
        var = shared.cvar_t()
        var.name = name
        var.string = value
        var.default_string = value
        var.flags = flags
        var.modified = True
        var.value = to_number(value)
        position = bisect.bisect_left(self._names, name)
        self._names.insert(position, name)
        self.vars.insert(position, var)
        self._by_name[name] = var
        return var

    def _info_ok(self, name: str, value: str, flags: int) -> bool:
        if flags & INFO_FLAGS:
            if not valid_info(name):
                self.print("invalid info cvar name\n")
                return False
            if not valid_info(value):
                self.print("invalid info cvar value\n")
                return False
        return True

    def _new(self, name: str, value: str | None, flags: int) -> shared.cvar_t | None:
        if value is None or not self._info_ok(name, value, flags):
            return None
        return self._add(name, _base_game(name, value), flags)

    def get(self, name: str, value: str | None, flags: int) -> shared.cvar_t | None:
        """The cvar, created with value if it doesn't exist. An existing one
        keeps its value, gains the flags and takes value as its default."""
        if value is None or not self._info_ok(name, value, flags):
            return None
        name = self.replacement(name)
        value = _base_game(name, value)
        var = self.find(name)
        if var is not None:
            var.flags |= flags
            var.default_string = value
            return var
        return self._add(name, value, flags)

    # ----------------------------------------------------------- setting

    def set_var(self, var: shared.cvar_t, value: str, force: bool) -> shared.cvar_t:
        """Change a cvar's value, honouring write protection and latching."""
        if var.flags & INFO_FLAGS and not valid_info(value):
            self.print("invalid info cvar value\n")
            return var
        value = _base_game(var.name, value)

        if not force:
            if var.flags & shared.CVAR_NOSET:
                self.print(f"{var.name} is write protected.\n")
                return var
            if var.flags & shared.CVAR_LATCH:
                if var.latched_string is not None:
                    if value == var.latched_string:
                        return var
                    var.latched_string = None
                elif value == var.string:
                    return var
                if self.server_running():
                    self.print(f"{var.name} will be changed for next game.\n")
                    var.latched_string = value
                else:
                    var.string = value
                    var.value = to_number(value)
                    if var.name == "game":
                        self.game_changed(var.string)
                return var
        else:
            var.latched_string = None

        if value == var.string:
            return var
        var.modified = True
        if var.flags & shared.CVAR_USERINFO:
            self.userinfo_modified = True
        var.string = value
        var.value = to_number(value)
        return var

    def set(self, name: str, value: str, force: bool = False) -> shared.cvar_t | None:
        """Set a cvar by name, creating it (with no flags) if needed."""
        name = self.replacement(name)
        var = self.find(name)
        return self._new(name, value, 0) if var is None else self.set_var(var, value, force)

    def full_set(self, name: str, value: str, flags: int) -> shared.cvar_t | None:
        """Set a cvar and replace its flags."""
        name = self.replacement(name)
        var = self.find(name)
        if var is None:
            return self._new(name, value, flags)
        var.modified = True
        if var.flags & shared.CVAR_USERINFO:
            self.userinfo_modified = True
        var.string = _base_game(name, value)
        var.value = to_number(var.string)
        var.flags = flags
        return var

    def set_value(self, name: str, value: float) -> None:
        self.set(name, format_value(value))

    def apply_latched(self) -> None:
        """Give latched cvars their new values (at a new game)."""
        for var in self.vars:
            if var.latched_string is None:
                continue
            var.string = var.latched_string
            var.latched_string = None
            var.value = to_number(var.string)
            if var.name == "game":
                self.game_changed(var.string)

    def clear(self) -> None:
        self.vars.clear()
        self._names.clear()
        self._by_name.clear()

    # ------------------------------------------------------- info strings

    def info_string(self, flag: int) -> str:
        """An info string of the cvars with flag (userinfo or serverinfo)."""
        info = ""
        for var in self.vars:
            if var.flags & flag:
                info = shared_c.Info_SetValueForKey(info, var.name, var.string)
        return info

    def write_archived(self, path: str) -> None:
        """Append "set name value" lines for the archived cvars."""
        with open(path, "a") as f:
            for var in self.vars:
                if var.flags & shared.CVAR_ARCHIVE:
                    f.write(f'set {var.name} "{var.string}"\n')

    # --------------------------------------------------- console commands
    # args is the command line, args[0] being the command's own name.

    def command(self, args: list[str]) -> bool:
        """A cvar name typed at the console: print it, or set it. False if
        args[0] isn't a cvar."""
        var = self.find(self.replacement(args[0]))
        if var is None:
            return False
        if len(args) == 1:
            self.print(f'"{var.name}" is "{var.string}"\n')
            return True
        if var.name == "game":
            # so a disconnect doesn't revert to the game given at startup
            self.user_game_changed(args[1][:shared.MAX_QPATH - 1])
        self.set_var(var, args[1], False)
        return True

    def set_command(self, args: list[str]) -> None:
        """set <variable> <value> [a / u / s]"""
        if len(args) not in (3, 4):
            self.print("usage: set <variable> <value> [u / s]\n")
            return
        name = self.replacement(args[1], warn=False)
        if len(args) == 4:
            flags = {"a": shared.CVAR_ARCHIVE, "u": shared.CVAR_USERINFO,
                     "s": shared.CVAR_SERVERINFO}.get(args[3])
            if flags is None:
                self.print("flags can only be 'a', 'u' or 's'\n")
                return
            self.full_set(name, args[2], flags)
        else:
            self.set(name, args[2])

    def list_command(self, args: list[str]) -> None:
        for var in self.vars:
            flags = var.flags
            self.print("*" if flags & shared.CVAR_ARCHIVE else " ")
            self.print("U" if flags & shared.CVAR_USERINFO else " ")
            self.print("S" if flags & shared.CVAR_SERVERINFO else " ")
            self.print("-" if flags & shared.CVAR_NOSET else
                       "L" if flags & shared.CVAR_LATCH else " ")
            self.print(f' {var.name} "{var.string}"\n')
        self.print(f"{len(self.vars)} cvars\n")

    def _named(self, args: list[str], usage: str) -> shared.cvar_t | None:
        if len(args) < 2:
            self.print(f"Usage: {args[0]} {usage}\n")
            return None
        name = self.replacement(args[1])
        var = self.find(name)
        if var is None:
            self.print(f"{name} is not a cvar\n")
        return var

    def inc_command(self, args: list[str]) -> None:
        """inc / dec <cvar> [value]: add 1, or the value (subtract for dec)."""
        var = self._named(args, "<cvar> [value]")
        if var is None:
            return
        if not is_float(var.string):
            self.print(f'"{var.name}" is "{var.string}", can\'t {args[0]}\n')
            return
        step = shared_c.atof(args[2]) if len(args) > 2 else 1
        if args[0] == "dec":
            step = -step
        self.set_var(var, f"{var.value + step:f}", False)

    def reset_command(self, args: list[str]) -> None:
        var = self._named(args, "<cvar>")
        if var is None:
            return
        self.print(f"{var.name}: {var.default_string}\n")
        self.set_var(var, var.default_string, False)

    def reset_all_command(self, args: list[str]) -> None:
        """Every cvar back to its default, except write protected ones and game."""
        for var in self.vars:
            if not var.flags & shared.CVAR_NOSET and var.name != "game":
                self.set_var(var, var.default_string, False)

    def toggle_command(self, args: list[str]) -> None:
        """toggle <cvar> [values]: between 0 and 1, or cycle through the values."""
        var = self._named(args, "<cvar> [values]")
        if var is None:
            return
        values = args[2:]
        if not values:
            if var.string in ("0", "1"):
                self.set_var(var, "1" if var.string == "0" else "0", False)
            else:
                self.print(f'"{var.name}" is "{var.string}", can\'t toggle\n')
            return
        for i, value in enumerate(values):
            if not shared_c.Q_stricmp(var.string, value):
                self.set_var(var, values[(i + 1) % len(values)], False)
                return
        self.print(f'"{var.name}" is "{var.string}", can\'t cycle\n')

    def commands(self) -> dict[str, Callable[[list[str]], None]]:
        """The console commands, by name."""
        return {
            "cvarlist": self.list_command,
            "dec": self.inc_command,
            "inc": self.inc_command,
            "reset": self.reset_command,
            "resetall": self.reset_all_command,
            "set": self.set_command,
            "toggle": self.toggle_command,
        }
