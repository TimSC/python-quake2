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
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
USA.

=======================================================================

The header file for the upper level key event processing

=======================================================================
"""
from __future__ import annotations

"""
#include "../../common/header/shared.h" /* for qboolean etc */
"""

MAXCMDLINE = 1024
NUM_KEY_LINES = 32

joy_altselector_pressed = False #extern qboolean, Q2PORT: defined in input/sdl2.c (group 14)

"""
 * these are the key numbers that should be passed to Key_Event
 * they must be matched by the low level key event processing!
"""
K_TAB = 9
K_ENTER = 13
K_ESCAPE = 27
# Note: ASCII keys are generally valid but don't get constants here,
# just use 'a' (yes, lowercase) or '2' or whatever, however there are
# some special cases when writing/parsing configs (space or quotes or
# also ; and $ have a special meaning there so we use e.g. "SPACE" instead),
# see keynames[] in cl_keyboard.c
K_SPACE = 32
K_BACKSPACE = 127
K_COMMAND = 128	# "Windows Key"
K_CAPSLOCK = 129
K_POWER = 130
K_PAUSE = 131
K_UPARROW = 132
K_DOWNARROW = 133
K_LEFTARROW = 134
K_RIGHTARROW = 135
K_ALT = 136
K_CTRL = 137
K_SHIFT = 138
K_INS = 139
K_DEL = 140
K_PGDN = 141
K_PGUP = 142
K_HOME = 143
K_END = 144
K_F1 = 145
K_F2 = 146
K_F3 = 147
K_F4 = 148
K_F5 = 149
K_F6 = 150
K_F7 = 151
K_F8 = 152
K_F9 = 153
K_F10 = 154
K_F11 = 155
K_F12 = 156
K_F13 = 157
K_F14 = 158
K_F15 = 159
K_KP_HOME = 160
K_KP_UPARROW = 161
K_KP_PGUP = 162
K_KP_LEFTARROW = 163
K_KP_5 = 164
K_KP_RIGHTARROW = 165
K_KP_END = 166
K_KP_DOWNARROW = 167
K_KP_PGDN = 168
K_KP_ENTER = 169
K_KP_INS = 170
K_KP_DEL = 171
K_KP_SLASH = 172
K_KP_MINUS = 173
K_KP_PLUS = 174
K_KP_NUMLOCK = 175
K_KP_STAR = 176
K_KP_EQUALS = 177
K_MOUSE1 = 178
K_MOUSE2 = 179
K_MOUSE3 = 180
K_MOUSE4 = 181
K_MOUSE5 = 182
K_MWHEELDOWN = 183
K_MWHEELUP = 184
K_SUPER = 185	# TODO: what is this? SDL doesn't seem to know it..
K_COMPOSE = 186
K_MODE = 187
K_HELP = 188
K_PRINT = 189
K_SYSREQ = 190
K_SCROLLOCK = 191
K_MENU = 192
K_UNDO = 193
# The following are mapped from SDL_Scancodes, used as a *fallback* for keys
# whose SDL_KeyCode we don't have a K_ constant for, like German Umlaut keys.
# The scancode name corresponds to the key at that position on US-QWERTY keyboards
# *not* the one in the local layout (e.g. German 'Ö' key is K_SC_SEMICOLON)
# !!! NOTE: if you add a scancode here, make sure to also add it to:
# 1. keynames[] in cl_keyboard.c
# 2. IN_TranslateScancodeToQ2Key() in input/sdl.c
K_SC_A = 194
K_SC_B = 195
K_SC_C = 196
K_SC_D = 197
K_SC_E = 198
K_SC_F = 199
K_SC_G = 200
K_SC_H = 201
K_SC_I = 202
K_SC_J = 203
K_SC_K = 204
K_SC_L = 205
K_SC_M = 206
K_SC_N = 207
K_SC_O = 208
K_SC_P = 209
K_SC_Q = 210
K_SC_R = 211
K_SC_S = 212
K_SC_T = 213
K_SC_U = 214
K_SC_V = 215
K_SC_W = 216
K_SC_X = 217
K_SC_Y = 218
K_SC_Z = 219
# leaving out SDL_SCANCODE_1 ... _0, we handle them separately already
# also return, escape, backspace, tab, space, already handled as keycodes
K_SC_MINUS = 220
K_SC_EQUALS = 221
K_SC_LEFTBRACKET = 222
K_SC_RIGHTBRACKET = 223
K_SC_BACKSLASH = 224
K_SC_NONUSHASH = 225
K_SC_SEMICOLON = 226
K_SC_APOSTROPHE = 227
K_SC_GRAVE = 228
K_SC_COMMA = 229
K_SC_PERIOD = 230
K_SC_SLASH = 231
# leaving out lots of key incl. from keypad, we already handle them as normal keys
K_SC_NONUSBACKSLASH = 232
K_SC_INTERNATIONAL1 = 233	# used on Asian keyboards, see footnotes in USB doc
K_SC_INTERNATIONAL2 = 234
K_SC_INTERNATIONAL3 = 235	# Yen
K_SC_INTERNATIONAL4 = 236
K_SC_INTERNATIONAL5 = 237
K_SC_INTERNATIONAL6 = 238
K_SC_INTERNATIONAL7 = 239
K_SC_INTERNATIONAL8 = 240
K_SC_INTERNATIONAL9 = 241
K_SC_THOUSANDSSEPARATOR = 242
K_SC_DECIMALSEPARATOR = 243
K_SC_CURRENCYUNIT = 244
K_SC_CURRENCYSUBUNIT = 245
# hardcoded pseudo-key to open the console, emitted when pressing the "console key"
# (SDL_SCANCODE_GRAVE, the one between Esc, 1 and Tab) on layouts that don't
# have a relevant char there (unlike Brazilian which has quotes there which you
# want to be able to type in the console) - the user can't bind this key.
K_CONSOLE = 246
# Keyboard keys / codes end here. Any new ones should go before this.
# From here on, only gamepad controls must be allowed.
# Otherwise, separate bindings (keyboard / controller) menu options will not work.
K_BTN_SOUTH = 247
K_JOY_FIRST_BTN = K_BTN_SOUTH
K_BTN_EAST = 248
K_BTN_WEST = 249
K_BTN_NORTH = 250
K_BTN_BACK = 251
K_BTN_GUIDE = 252
K_BTN_START = 253
K_STICK_LEFT = 254
K_STICK_RIGHT = 255
K_SHOULDER_LEFT = 256
K_SHOULDER_RIGHT = 257
K_DPAD_UP = 258
K_DPAD_DOWN = 259
K_DPAD_LEFT = 260
K_DPAD_RIGHT = 261
K_BTN_MISC1 = 262
K_PADDLE_RIGHT_1 = 263
K_PADDLE_LEFT_1 = 264
K_PADDLE_RIGHT_2 = 265
K_PADDLE_LEFT_2 = 266
K_TOUCHPAD = 267	# SDL_CONTROLLER_BUTTON_MAX - 1, SDL2 limit
K_BTN_MISC2 = 268
K_BTN_MISC3 = 269
K_BTN_MISC4 = 270
K_BTN_MISC5 = 271
K_BTN_MISC6 = 272	# SDL_GAMEPAD_BUTTON_COUNT - 1, current SDL3 count
K_TRIG_LEFT = 273	# buttons for triggers (axes)
K_TRIG_RIGHT = 274
# Add other gamepad keys before this one, adjust from SDL 2/3 definitions, and
# add the corresponding _ALT key below! Respect the order, must be the same as above.
# Also, verify if cl_keyboard.c needs a refactor on its arrays.
K_BTN_SOUTH_ALT = 275
K_JOY_FIRST_BTN_ALT = K_BTN_SOUTH_ALT
K_BTN_EAST_ALT = 276
K_BTN_WEST_ALT = 277
K_BTN_NORTH_ALT = 278
K_BTN_BACK_ALT = 279
K_BTN_GUIDE_ALT = 280
K_BTN_START_ALT = 281
K_STICK_LEFT_ALT = 282
K_STICK_RIGHT_ALT = 283
K_SHOULDER_LEFT_ALT = 284
K_SHOULDER_RIGHT_ALT = 285
K_DPAD_UP_ALT = 286
K_DPAD_DOWN_ALT = 287
K_DPAD_LEFT_ALT = 288
K_DPAD_RIGHT_ALT = 289
K_BTN_MISC1_ALT = 290
K_PADDLE_RIGHT_1_ALT = 291
K_PADDLE_LEFT_1_ALT = 292
K_PADDLE_RIGHT_2_ALT = 293
K_PADDLE_LEFT_2_ALT = 294
K_TOUCHPAD_ALT = 295
K_BTN_MISC2_ALT = 296
K_BTN_MISC3_ALT = 297
K_BTN_MISC4_ALT = 298
K_BTN_MISC5_ALT = 299
K_BTN_MISC6_ALT = 300
K_TRIG_LEFT_ALT = 301
K_TRIG_RIGHT_ALT = 302
K_LAST = 303

"""
extern char		*keybindings[K_LAST];
extern int		key_repeats[K_LAST];
extern qboolean	keydown[K_LAST];
extern int		anykeydown;
extern char		chat_buffer[];
extern int		chat_bufferlen;
extern int		chat_cursorpos;
extern qboolean	chat_team;
"""

# Q2PORT: the keypad keys as characters, used by the port's platform layer
keypadMapping = {
	K_KP_SLASH: ord('/'),
	K_KP_MINUS: ord('-'),
	K_KP_PLUS: ord('+'),
	K_KP_HOME: ord('7'),
	K_KP_UPARROW: ord('8'),
	K_KP_PGUP: ord('9'),
	K_KP_LEFTARROW: ord('4'),
	K_KP_5: ord('5'),
	K_KP_RIGHTARROW: ord('6'),
	K_KP_END: ord('1'),
	K_KP_DOWNARROW: ord('2'),
	K_KP_PGDN: ord('3'),
	K_KP_INS: ord('0'),
	K_KP_DEL: ord('.'),
}
