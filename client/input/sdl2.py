"""
Copyright (C) 2010 Yamagi Burmeister
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

This is the Quake II input system backend, implemented with SDL.

=======================================================================
"""
from __future__ import annotations

import math

import pygame

import os

from backends.unix import system
from common.header import shared
from common import clientserver
from common import cmdparser
from common import cvar
from client.vid import vid

from client.header import client as client_h
from client.header import keyboard as keyboard_h
from client import cl_keyboard
from client import cl_input
from client import cl_main

joy_current_lbls = client_h.gamepad_labels_t.LBL_SDL #gamepad_labels_t

# Using japanese style for confirm & cancel buttons on gamepad
japanese_confirm = False #qboolean

MOUSE_MAX = 3000 #3000
MOUSE_MIN = 40 #40

mouse_x, mouse_y = 0.0, 0.0 #static float, the mouse motion since the last frame, in pixels
old_mouse_x, old_mouse_y = 0.0, 0.0 #static float, for m_filter
mlooking = False #static qboolean

# Q2PORT: id's in_mouse cvar and the Q2PORT_NOMOUSE environment variable (the
# tests set it) leave the mouse alone: no grab, no motion
in_mouse = None #cvar_t *
mouse_avail = False #qboolean

sys_frame_time = 0 #unsigned

# Console Variables
freelook = None #cvar_t *
lookstrafe = None #cvar_t *
m_forward = None #cvar_t *
m_pitch = None #cvar_t *
m_side = None #cvar_t *
m_up = None #cvar_t *
m_yaw = None #cvar_t *
sensitivity = None #static cvar_t *

exponential_speedup = None #static cvar_t *
in_grab = None #static cvar_t *
m_filter = None #static cvar_t *
windowed_pauseonfocuslost = None #static cvar_t *
windowed_mouse = None #static cvar_t *
haptic_feedback_filter = None #static cvar_t *
s_muteonfocusloss = None #static cvar_t *

joy_haptic_magnitude = None #static cvar_t *
joy_haptic_distance = None #static cvar_t *
joy_sensitivity = None #static cvar_t *
joy_advanced = None #static cvar_t *
joy_yawspeed = None #static cvar_t *
joy_pitchspeed = None #static cvar_t *
joy_extra_yawspeed = None #static cvar_t *
joy_extra_pitchspeed = None #static cvar_t *
joy_ramp_time = None #static cvar_t *
joy_outer_threshold = None #static cvar_t *
joy_forwardsensitivity = None #static cvar_t *
joy_sidesensitivity = None #static cvar_t *
joy_labels = None #static cvar_t *
joy_confirm = None #static cvar_t *
joy_layout = None #static cvar_t *
joy_left_expo = None #static cvar_t *
joy_left_snapaxis = None #static cvar_t *
joy_left_deadzone = None #static cvar_t *
joy_right_expo = None #static cvar_t *
joy_right_snapaxis = None #static cvar_t *
joy_right_deadzone = None #static cvar_t *
joy_trigger = None #static cvar_t *
joy_flick_threshold = None #static cvar_t *
joy_flick_smoothed = None #static cvar_t *
gyro_mode = None #static cvar_t *
gyro_space = None #static cvar_t *
gyro_local_roll = None #static cvar_t *
gyro_yawsensitivity = None #static cvar_t *
gyro_pitchsensitivity = None #static cvar_t *
gyro_tightening = None #static cvar_t *
gyro_smoothing = None #static cvar_t *
gyro_smoothing_window = None #static cvar_t *
gyro_acceleration = None #static cvar_t *
gyro_accel_multiplier = None #static cvar_t *
gyro_accel_lower_thresh = None #static cvar_t *
gyro_accel_upper_thresh = None #static cvar_t *
gyro_calibration_a = None #static cvar_t *
gyro_calibration_x = None #static cvar_t *
gyro_calibration_y = None #static cvar_t *
gyro_calibration_z = None #static cvar_t *

default_haptic_filter = ( #static char *
	# skipped files should be before wider rule
	"!weapons/*grenlb " # bouncing grenades don't have feedback
	"!weapons/*hgrenb " # bouncing grenades don't have feedback
	"!weapons/*open " # rogue's items don't have feedback
	"!weapons/*warn " # rogue's items don't have feedback
	# any weapons that are not in previous list
	"weapons/ "
	# player{,s} effects
	"player/*land " # fall without injury
	"player/*burn "
	"player/*pain "
	"player/*fall "
	"player/*death "
	"players/*burn "
	"players/*pain "
	"players/*fall "
	"players/*death "
	# environment effects
	"doors/ "
	"plats/ "
	"world/*dish  "
	"world/*drill2a "
	"world/*dr_ "
	"world/*explod1 "
	"world/*rocks "
	"world/*rumble  "
	"world/*quake  "
	"world/*train2 "
)

def IN_Init(): #void

	global exponential_speedup, freelook, in_grab, lookstrafe, m_filter, m_up, m_forward, m_pitch, \
		m_side, m_yaw, sensitivity, joy_haptic_magnitude, joy_haptic_distance, haptic_feedback_filter, joy_sensitivity, joy_advanced, \
		joy_yawspeed, joy_pitchspeed, joy_extra_yawspeed, joy_extra_pitchspeed, joy_ramp_time, joy_outer_threshold, joy_forwardsensitivity, joy_sidesensitivity, \
		joy_labels, joy_confirm, joy_layout, joy_left_expo, joy_left_snapaxis, joy_left_deadzone, joy_right_expo, joy_right_snapaxis, \
		joy_right_deadzone, joy_trigger, joy_flick_threshold, joy_flick_smoothed, gyro_mode, gyro_space, gyro_local_roll, gyro_yawsensitivity, \
		gyro_pitchsensitivity, gyro_tightening, gyro_smoothing, gyro_smoothing_window, gyro_acceleration, gyro_accel_multiplier, gyro_accel_lower_thresh, gyro_accel_upper_thresh, \
		gyro_calibration_a, gyro_calibration_x, gyro_calibration_y, gyro_calibration_z, windowed_pauseonfocuslost, windowed_mouse, s_muteonfocusloss, in_mouse, mouse_avail

	clientserver.Com_Printf("------- input initialization -------\n")

	mouse_x = mouse_y = 0.0
	# Q2PORT: the joystick and gyro state of sdl2.c aren't ported (group 14)
	#joystick_left_x = joystick_left_y = joystick_right_x = joystick_right_y = 0;
	#joy_active_layout = LAYOUT_NONE;
	#gyro_active = gyro_enabled = false;

	in_mouse = cvar.Cvar_Get("in_mouse", "1", shared.CVAR_ARCHIVE) # Q2PORT: id's cvar, it and Q2PORT_NOMOUSE gate the mouse grab
	mouse_avail = bool(in_mouse.value) and not os.environ.get("Q2PORT_NOMOUSE")

	exponential_speedup = cvar.Cvar_Get("exponential_speedup", "0", shared.CVAR_ARCHIVE)
	freelook = cvar.Cvar_Get("freelook", "1", shared.CVAR_ARCHIVE)
	in_grab = cvar.Cvar_Get("in_grab", "2", shared.CVAR_ARCHIVE)
	lookstrafe = cvar.Cvar_Get("lookstrafe", "0", shared.CVAR_ARCHIVE)
	m_filter = cvar.Cvar_Get("m_filter", "0", shared.CVAR_ARCHIVE)
	m_up = cvar.Cvar_Get("m_up", "1", shared.CVAR_ARCHIVE)
	m_forward = cvar.Cvar_Get("m_forward", "1", shared.CVAR_ARCHIVE)
	m_pitch = cvar.Cvar_Get("m_pitch", "0.022", shared.CVAR_ARCHIVE)
	m_side = cvar.Cvar_Get("m_side", "0.8", shared.CVAR_ARCHIVE)
	m_yaw = cvar.Cvar_Get("m_yaw", "0.022", shared.CVAR_ARCHIVE)
	sensitivity = cvar.Cvar_Get("sensitivity", "3", shared.CVAR_ARCHIVE)
	joy_haptic_magnitude = cvar.Cvar_Get("joy_haptic_magnitude", "0.0", shared.CVAR_ARCHIVE)
	joy_haptic_distance = cvar.Cvar_Get("joy_haptic_distance", "100.0", shared.CVAR_ARCHIVE)
	haptic_feedback_filter = cvar.Cvar_Get("joy_haptic_filter", default_haptic_filter, shared.CVAR_ARCHIVE)
	joy_sensitivity = cvar.Cvar_Get("joy_sensitivity", "3", shared.CVAR_ARCHIVE)
	joy_advanced = cvar.Cvar_Get("joy_advanced", "0", shared.CVAR_ARCHIVE)
	joy_yawspeed = cvar.Cvar_Get("joy_yawspeed", "160", shared.CVAR_ARCHIVE)
	joy_pitchspeed = cvar.Cvar_Get("joy_pitchspeed", "120", shared.CVAR_ARCHIVE)
	joy_extra_yawspeed = cvar.Cvar_Get("joy_extra_yawspeed", "220", shared.CVAR_ARCHIVE)
	joy_extra_pitchspeed = cvar.Cvar_Get("joy_extra_pitchspeed", "0", shared.CVAR_ARCHIVE)
	joy_ramp_time = cvar.Cvar_Get("joy_ramp_time", "0.35", shared.CVAR_ARCHIVE)
	joy_outer_threshold = cvar.Cvar_Get("joy_outer_threshold", "0.02", shared.CVAR_ARCHIVE)
	joy_forwardsensitivity = cvar.Cvar_Get("joy_forwardsensitivity", "1.0", shared.CVAR_ARCHIVE)
	joy_sidesensitivity = cvar.Cvar_Get("joy_sidesensitivity", "1.0", shared.CVAR_ARCHIVE)
	joy_labels = cvar.Cvar_Get("joy_labels", "-1", shared.CVAR_ARCHIVE)
	joy_confirm = cvar.Cvar_Get("joy_confirm", "-1", shared.CVAR_ARCHIVE)
	joy_layout = cvar.Cvar_Get("joy_layout", "0", shared.CVAR_ARCHIVE)
	joy_left_expo = cvar.Cvar_Get("joy_left_expo", "2.0", shared.CVAR_ARCHIVE)
	joy_left_snapaxis = cvar.Cvar_Get("joy_left_snapaxis", "0.15", shared.CVAR_ARCHIVE)
	joy_left_deadzone = cvar.Cvar_Get("joy_left_deadzone", "0.16", shared.CVAR_ARCHIVE)
	joy_right_expo = cvar.Cvar_Get("joy_right_expo", "2.0", shared.CVAR_ARCHIVE)
	joy_right_snapaxis = cvar.Cvar_Get("joy_right_snapaxis", "0.15", shared.CVAR_ARCHIVE)
	joy_right_deadzone = cvar.Cvar_Get("joy_right_deadzone", "0.16", shared.CVAR_ARCHIVE)
	joy_trigger = cvar.Cvar_Get("joy_trigger", "0.2", shared.CVAR_ARCHIVE)
	joy_flick_threshold = cvar.Cvar_Get("joy_flick_threshold", "0.65", shared.CVAR_ARCHIVE)
	joy_flick_smoothed = cvar.Cvar_Get("joy_flick_smoothed", "16", shared.CVAR_ARCHIVE)
	gyro_mode = cvar.Cvar_Get("gyro_mode", "2", shared.CVAR_ARCHIVE)
	gyro_space = cvar.Cvar_Get("gyro_space", "1", shared.CVAR_ARCHIVE)
	gyro_local_roll = cvar.Cvar_Get("gyro_local_roll", "1", shared.CVAR_ARCHIVE)
	gyro_yawsensitivity = cvar.Cvar_Get("gyro_yawsensitivity", "2.5", shared.CVAR_ARCHIVE)
	gyro_pitchsensitivity = cvar.Cvar_Get("gyro_pitchsensitivity", "2.5", shared.CVAR_ARCHIVE)
	gyro_tightening = cvar.Cvar_Get("gyro_tightening", "3.5", shared.CVAR_ARCHIVE)
	gyro_smoothing = cvar.Cvar_Get("gyro_smoothing", "2.5", shared.CVAR_ARCHIVE)
	gyro_smoothing_window = cvar.Cvar_Get("gyro_smoothing_window", "0.125", shared.CVAR_ARCHIVE)
	gyro_acceleration = cvar.Cvar_Get("gyro_acceleration", "0", shared.CVAR_ARCHIVE)
	gyro_accel_multiplier = cvar.Cvar_Get("gyro_accel_multiplier", "2.0", shared.CVAR_ARCHIVE)
	gyro_accel_lower_thresh = cvar.Cvar_Get("gyro_accel_lower_thresh", "0.0", shared.CVAR_ARCHIVE)
	gyro_accel_upper_thresh = cvar.Cvar_Get("gyro_accel_upper_thresh", "75.0", shared.CVAR_ARCHIVE)
	gyro_calibration_a = cvar.Cvar_Get("gyro_calibration_a", "0.0", shared.CVAR_ARCHIVE)
	gyro_calibration_x = cvar.Cvar_Get("gyro_calibration_x", "0.0", shared.CVAR_ARCHIVE)
	gyro_calibration_y = cvar.Cvar_Get("gyro_calibration_y", "0.0", shared.CVAR_ARCHIVE)
	gyro_calibration_z = cvar.Cvar_Get("gyro_calibration_z", "0.0", shared.CVAR_ARCHIVE)
	windowed_pauseonfocuslost = cvar.Cvar_Get("vid_pauseonfocuslost", "0", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	windowed_mouse = cvar.Cvar_Get("windowed_mouse", "1", shared.CVAR_USERINFO | shared.CVAR_ARCHIVE)
	s_muteonfocusloss = cvar.Cvar_Get("s_muteonfocusloss", "1", shared.CVAR_ARCHIVE)

	cmdparser.Cmd_AddCommand("+mlook", IN_MLookDown)
	cmdparser.Cmd_AddCommand("-mlook", IN_MLookUp)
	cmdparser.Cmd_AddCommand("+joyaltselector", IN_JoyAltSelectorDown)
	cmdparser.Cmd_AddCommand("-joyaltselector", IN_JoyAltSelectorUp)
	#Cmd_AddCommand("+gyroaction", IN_GyroActionDown);
	#Cmd_AddCommand("-gyroaction", IN_GyroActionUp);

	#SDL_StartTextInput(); Q2PORT: pygame starts text input with the window

	#IN_Controller_Init(false);

	clientserver.Com_Printf("------------------------------------\n\n")


# ------------------------------------------------------------------

"""
 * This creepy function translates SDL keycodes into
 * the id Tech 2 engines interal representation.
"""
def IN_TranslateSDLtoQ2Key(keysym: int)->int: #unsigned int (returns static int)

	key = 0

	# These must be translated
	if keysym == pygame.K_TAB:

		key = keyboard_h.K_TAB

	elif keysym == pygame.K_RETURN:

		key = keyboard_h.K_ENTER

	elif keysym == pygame.K_ESCAPE:

		key = keyboard_h.K_ESCAPE

	elif keysym == pygame.K_BACKSPACE:

		key = keyboard_h.K_BACKSPACE

	elif keysym == pygame.K_RGUI or keysym == pygame.K_LGUI:

		key = keyboard_h.K_SUPER

	elif keysym == pygame.K_CAPSLOCK:

		key = keyboard_h.K_CAPSLOCK

	elif keysym == pygame.K_POWER:

		key = keyboard_h.K_POWER

	elif keysym == pygame.K_PAUSE:

		key = keyboard_h.K_PAUSE

	elif keysym == pygame.K_UP:

		key = keyboard_h.K_UPARROW

	elif keysym == pygame.K_DOWN:

		key = keyboard_h.K_DOWNARROW

	elif keysym == pygame.K_LEFT:

		key = keyboard_h.K_LEFTARROW

	elif keysym == pygame.K_RIGHT:

		key = keyboard_h.K_RIGHTARROW

	elif keysym == pygame.K_RALT or keysym == pygame.K_LALT:

		key = keyboard_h.K_ALT

	elif keysym == pygame.K_LCTRL or keysym == pygame.K_RCTRL:

		key = keyboard_h.K_CTRL

	elif keysym == pygame.K_LSHIFT or keysym == pygame.K_RSHIFT:

		key = keyboard_h.K_SHIFT

	elif keysym == pygame.K_INSERT:

		key = keyboard_h.K_INS

	elif keysym == pygame.K_DELETE:

		key = keyboard_h.K_DEL

	elif keysym == pygame.K_PAGEDOWN:

		key = keyboard_h.K_PGDN

	elif keysym == pygame.K_PAGEUP:

		key = keyboard_h.K_PGUP

	elif keysym == pygame.K_HOME:

		key = keyboard_h.K_HOME

	elif keysym == pygame.K_END:

		key = keyboard_h.K_END

	elif keysym == pygame.K_F1:

		key = keyboard_h.K_F1

	elif keysym == pygame.K_F2:

		key = keyboard_h.K_F2

	elif keysym == pygame.K_F3:

		key = keyboard_h.K_F3

	elif keysym == pygame.K_F4:

		key = keyboard_h.K_F4

	elif keysym == pygame.K_F5:

		key = keyboard_h.K_F5

	elif keysym == pygame.K_F6:

		key = keyboard_h.K_F6

	elif keysym == pygame.K_F7:

		key = keyboard_h.K_F7

	elif keysym == pygame.K_F8:

		key = keyboard_h.K_F8

	elif keysym == pygame.K_F9:

		key = keyboard_h.K_F9

	elif keysym == pygame.K_F10:

		key = keyboard_h.K_F10

	elif keysym == pygame.K_F11:

		key = keyboard_h.K_F11

	elif keysym == pygame.K_F12:

		key = keyboard_h.K_F12

	elif keysym == pygame.K_F13:

		key = keyboard_h.K_F13

	elif keysym == pygame.K_F14:

		key = keyboard_h.K_F14

	elif keysym == pygame.K_F15:

		key = keyboard_h.K_F15

	elif keysym == pygame.K_KP_7:

		key = keyboard_h.K_KP_HOME

	elif keysym == pygame.K_KP_8:

		key = keyboard_h.K_KP_UPARROW

	elif keysym == pygame.K_KP_9:

		key = keyboard_h.K_KP_PGUP

	elif keysym == pygame.K_KP_4:

		key = keyboard_h.K_KP_LEFTARROW

	elif keysym == pygame.K_KP_5:

		key = keyboard_h.K_KP_5

	elif keysym == pygame.K_KP_6:

		key = keyboard_h.K_KP_RIGHTARROW

	elif keysym == pygame.K_KP_1:

		key = keyboard_h.K_KP_END

	elif keysym == pygame.K_KP_2:

		key = keyboard_h.K_KP_DOWNARROW

	elif keysym == pygame.K_KP_3:

		key = keyboard_h.K_KP_PGDN

	elif keysym == pygame.K_KP_ENTER:

		key = keyboard_h.K_KP_ENTER

	elif keysym == pygame.K_KP_0:

		key = keyboard_h.K_KP_INS

	elif keysym == pygame.K_KP_PERIOD:

		key = keyboard_h.K_KP_DEL

	elif keysym == pygame.K_KP_DIVIDE:

		key = keyboard_h.K_KP_SLASH

	elif keysym == pygame.K_KP_MINUS:

		key = keyboard_h.K_KP_MINUS

	elif keysym == pygame.K_KP_PLUS:

		key = keyboard_h.K_KP_PLUS

	elif keysym == pygame.K_NUMLOCKCLEAR:

		key = keyboard_h.K_KP_NUMLOCK

	elif keysym == pygame.K_KP_MULTIPLY:

		key = keyboard_h.K_KP_STAR

	elif keysym == pygame.K_KP_EQUALS:

		key = keyboard_h.K_KP_EQUALS

	elif keysym == 0x40000065: # SDLK_APPLICATION

		key = keyboard_h.K_COMPOSE

	elif keysym == pygame.K_MODE:

		key = keyboard_h.K_MODE

	elif keysym == pygame.K_HELP:

		key = keyboard_h.K_HELP

	elif keysym == pygame.K_PRINTSCREEN:

		key = keyboard_h.K_PRINT

	elif keysym == pygame.K_SYSREQ:

		key = keyboard_h.K_SYSREQ

	elif keysym == pygame.K_SCROLLLOCK:

		key = keyboard_h.K_SCROLLOCK

	elif keysym == pygame.K_MENU:

		key = keyboard_h.K_MENU

	elif keysym == 0x4000007A: # SDLK_UNDO

		key = keyboard_h.K_UNDO

	return key

# #define MY_SC_CASE(X) case SDL_SCANCODE_ ## X : return K_SC_ ## X;
# Q2PORT: the cases MY_SC_CASE makes, as a table from scancode to key
_sc_cases = { #SDL_Scancode -> int
	pygame.KSCAN_X: keyboard_h.K_SC_X,
	pygame.KSCAN_A: keyboard_h.K_SC_A,
	pygame.KSCAN_B: keyboard_h.K_SC_B,
	pygame.KSCAN_C: keyboard_h.K_SC_C,
	pygame.KSCAN_D: keyboard_h.K_SC_D,
	pygame.KSCAN_E: keyboard_h.K_SC_E,
	pygame.KSCAN_F: keyboard_h.K_SC_F,
	pygame.KSCAN_G: keyboard_h.K_SC_G,
	pygame.KSCAN_H: keyboard_h.K_SC_H,
	pygame.KSCAN_I: keyboard_h.K_SC_I,
	pygame.KSCAN_J: keyboard_h.K_SC_J,
	pygame.KSCAN_K: keyboard_h.K_SC_K,
	pygame.KSCAN_L: keyboard_h.K_SC_L,
	pygame.KSCAN_M: keyboard_h.K_SC_M,
	pygame.KSCAN_N: keyboard_h.K_SC_N,
	pygame.KSCAN_O: keyboard_h.K_SC_O,
	pygame.KSCAN_P: keyboard_h.K_SC_P,
	pygame.KSCAN_Q: keyboard_h.K_SC_Q,
	pygame.KSCAN_R: keyboard_h.K_SC_R,
	pygame.KSCAN_S: keyboard_h.K_SC_S,
	pygame.KSCAN_T: keyboard_h.K_SC_T,
	pygame.KSCAN_U: keyboard_h.K_SC_U,
	pygame.KSCAN_V: keyboard_h.K_SC_V,
	pygame.KSCAN_W: keyboard_h.K_SC_W,
	pygame.KSCAN_X: keyboard_h.K_SC_X,
	pygame.KSCAN_Y: keyboard_h.K_SC_Y,
	pygame.KSCAN_Z: keyboard_h.K_SC_Z,
	pygame.KSCAN_MINUS: keyboard_h.K_SC_MINUS,
	pygame.KSCAN_EQUALS: keyboard_h.K_SC_EQUALS,
	pygame.KSCAN_LEFTBRACKET: keyboard_h.K_SC_LEFTBRACKET,
	pygame.KSCAN_RIGHTBRACKET: keyboard_h.K_SC_RIGHTBRACKET,
	pygame.KSCAN_BACKSLASH: keyboard_h.K_SC_BACKSLASH,
	pygame.KSCAN_NONUSHASH: keyboard_h.K_SC_NONUSHASH,
	pygame.KSCAN_SEMICOLON: keyboard_h.K_SC_SEMICOLON,
	pygame.KSCAN_APOSTROPHE: keyboard_h.K_SC_APOSTROPHE,
	pygame.KSCAN_GRAVE: keyboard_h.K_SC_GRAVE,
	pygame.KSCAN_COMMA: keyboard_h.K_SC_COMMA,
	pygame.KSCAN_PERIOD: keyboard_h.K_SC_PERIOD,
	pygame.KSCAN_SLASH: keyboard_h.K_SC_SLASH,
	pygame.KSCAN_NONUSBACKSLASH: keyboard_h.K_SC_NONUSBACKSLASH,
	pygame.KSCAN_INTERNATIONAL1: keyboard_h.K_SC_INTERNATIONAL1,
	pygame.KSCAN_INTERNATIONAL2: keyboard_h.K_SC_INTERNATIONAL2,
	pygame.KSCAN_INTERNATIONAL3: keyboard_h.K_SC_INTERNATIONAL3,
	pygame.KSCAN_INTERNATIONAL4: keyboard_h.K_SC_INTERNATIONAL4,
	pygame.KSCAN_INTERNATIONAL5: keyboard_h.K_SC_INTERNATIONAL5,
	pygame.KSCAN_INTERNATIONAL6: keyboard_h.K_SC_INTERNATIONAL6,
	pygame.KSCAN_INTERNATIONAL7: keyboard_h.K_SC_INTERNATIONAL7,
	pygame.KSCAN_INTERNATIONAL8: keyboard_h.K_SC_INTERNATIONAL8,
	pygame.KSCAN_INTERNATIONAL9: keyboard_h.K_SC_INTERNATIONAL9,
	178: keyboard_h.K_SC_THOUSANDSSEPARATOR, # SDL_SCANCODE_THOUSANDSSEPARATOR
	179: keyboard_h.K_SC_DECIMALSEPARATOR, # SDL_SCANCODE_DECIMALSEPARATOR
	pygame.KSCAN_CURRENCYUNIT: keyboard_h.K_SC_CURRENCYUNIT,
	pygame.KSCAN_CURRENCYSUBUNIT: keyboard_h.K_SC_CURRENCYSUBUNIT,
}

def IN_TranslateScancodeToQ2Key(sc: int)->int: #SDL_Scancode (returns static int)

	if sc in _sc_cases: # switch( (int)sc )

		return _sc_cases[sc]

	# #undef MY_SC_CASE

	return 0

"""
 * Updates the input queue state. Called every
 * frame by the client and does nearly all the
 * input magic.
 */
"""
def IN_Update(): #void

	global sys_frame_time, mouse_x, mouse_y

	# Q2PORT: the C's SDL event pump is the port's pygame event queue (linux/gl_glx.py's
	# HandleEvents did the same); mouse buttons, keys and text go straight to the client

	#qboolean want_grab;
	#SDL_Event event;
	#unsigned int key;

	#static qboolean left_trigger = false;
	#static qboolean right_trigger = false;
	#static qboolean left_stick[4] = {false, false, false, false};   // left, right, up, down virtual keys

	static_consoleKeyCode = 0 #static int consoleKeyCode

	# get and process an event
	for event in pygame.event.get(): # while (SDL_PollEvent(&event))

		if event.type == pygame.MOUSEWHEEL: # SDL_MOUSEWHEEL
			cl_keyboard.Key_Event(keyboard_h.K_MWHEELUP if event.wheel > 0 else keyboard_h.K_MWHEELDOWN, True, True)
			cl_keyboard.Key_Event(keyboard_h.K_MWHEELUP if event.wheel > 0 else keyboard_h.K_MWHEELDOWN, False, True)

		elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
			key = 0
			if event.button == 1: # SDL_BUTTON_LEFT
				key = keyboard_h.K_MOUSE1
			elif event.button == 2: # SDL_BUTTON_MIDDLE
				key = keyboard_h.K_MOUSE3
			elif event.button == 3: # SDL_BUTTON_RIGHT
				key = keyboard_h.K_MOUSE2
			elif event.button == 4: # SDL_BUTTON_X1
				key = keyboard_h.K_MOUSE4
			elif event.button == 5: # SDL_BUTTON_X2
				key = keyboard_h.K_MOUSE5
			else:
				continue # return;

			cl_keyboard.Key_Event(key, event.type == pygame.MOUSEBUTTONDOWN, True)

		elif event.type == pygame.MOUSEMOTION:
			if cl_main.cls.key_dest == client_h.keydest_t.key_game and not cl_main.cl_paused.value:
				mouse_x += event.rel[0]
				mouse_y += event.rel[1]

		elif event.type == pygame.TEXTINPUT: # SDL_TEXTINPUT
			if event.text:
				c = ord(event.text[0])
				# also make sure we don't get the char that corresponds to the
				# "console key" (like "^" or "`") as text input
				if c >= ord(' ') and c <= ord('~') and c != static_consoleKeyCode:
					cl_keyboard.Char_Event(c)

		elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
			down = event.type == pygame.KEYDOWN
			sc = event.scancode # SDL_Scancode sc = event.key.keysym.scancode;
			if sc >= pygame.KSCAN_1 and sc <= pygame.KSCAN_0:
				# workaround for AZERTY-keyboards, which don't have 1, 2, ..., 9, 0 in first row:
				# always map those physical keys (scancodes) to those keycodes anyway
				# see also https://bugzilla.libsdl.org/show_bug.cgi?id=3188
				key = ord('0') # implicitly handles SDL_SCANCODE_0
				if sc <= pygame.KSCAN_9:
					key = ord('1') + (sc - pygame.KSCAN_1)

				cl_keyboard.Key_Event(key, down, False)
			else:
				kc = event.key # SDL_Keycode kc = event.key.keysym.sym;
				if sc == pygame.KSCAN_GRAVE and kc != ord('\'') and kc != ord('"'):
					# special case/hack: open the console with the "console key"
					# (beneath Esc, left of 1, above Tab)
					# but not if the keycode for this is a quote (like on Brazilian
					# keyboards) - otherwise you couldn't type them in the console
					if (event.mod & (pygame.KMOD_CAPS|pygame.KMOD_SHIFT|pygame.KMOD_ALT|pygame.KMOD_CTRL|pygame.KMOD_GUI)) == 0:
						# also, only do this if no modifiers like shift or AltGr or whatever are pressed
						# so kc will most likely be the ascii char generated by this and can be ignored
						# in case SDL_TEXTINPUT above (so we don't get ^ or whatever as text in console)
						# (can't just check for mod == 0 because numlock is a KMOD too)
						cl_keyboard.Key_Event(keyboard_h.K_CONSOLE, down, True)
						static_consoleKeyCode = kc
				elif kc >= pygame.K_SPACE and kc < pygame.K_DELETE:
					cl_keyboard.Key_Event(kc, down, False)
				else:
					key = IN_TranslateSDLtoQ2Key(kc)
					if key == 0:
						# fallback to scancodes if we don't know the keycode
						key = IN_TranslateScancodeToQ2Key(sc)
					if key != 0:
						cl_keyboard.Key_Event(key, down, True)
					else:
						clientserver.Com_DPrintf("Pressed unknown key with SDL_Keycode {}, SDL_Scancode {}.\n".format(kc, sc))

		# Q2PORT: the C's single SDL_WINDOWEVENT (with an event.window_event subcode) is
		# several pygame event types, each carrying the subcode as the type itself
		elif event.type == pygame.WINDOWFOCUSLOST:

			cl_keyboard.Key_MarkAllUp()

			if windowed_pauseonfocuslost.value != 1:
				cvar.Cvar_SetValue("paused", 1)

			# the C toggles the ogg music here (ogg_pausewithgame), Q2PORT: music is group 13

			# S_Activate(false), Q2PORT: the port's sound has no focus activate

		elif event.type == pygame.WINDOWFOCUSGAINED:

			if windowed_pauseonfocuslost.value == 2:
				cvar.Cvar_SetValue("paused", 0)

			# the C toggles the ogg music here (ogg_pausewithgame), Q2PORT: music is group 13

			# S_Activate(true), Q2PORT: the port's sound has no focus activate

		elif event.type == pygame.WINDOWMOVED:
			# make sure GLimp_GetRefreshRate() will query from SDL again - the window might
			# be on another display now!
			vid.glimp_sdl2.glimp_refreshRate = -1.0

		elif event.type == pygame.WINDOWSHOWN:

			if cl_main.cl_unpaused_scvis.value > 0:
				cvar.Cvar_SetValue("paused", 0)

			# the C toggles the ogg music here (ogg_pausewithgame), Q2PORT: music is group 13

		# the C's SDL_CONTROLLERBUTTON/AXIS/SENSOR/DEVICE/JOY events aren't ported (group 14)

		elif event.type == pygame.QUIT: # SDL_QUIT
			clientserver.Com_Quit()

	# grab and ungrab the mouse if the console or the menu is opened
	if in_grab.value == 3:
		want_grab = windowed_mouse.value
	else:
		want_grab = vid.vid_fullscreen.value or in_grab.value == 1 or \
			(in_grab.value == 2 and windowed_mouse.value)

	# calling GLimp_GrabInput() each frame is a bit ugly but simple and should work.
	# The called SDL functions return after a cheap check, if there's nothing to do.
	if mouse_avail: # Q2PORT: id's mouse_avail
		vid.glimp_sdl2.GLimp_GrabInput(want_grab)

	# we need to save the frame time so other subsystems
	# know the exact time of the last input events.
	sys_frame_time = system.Sys_Milliseconds()

	# the C's hot-plug countdown, joystick preset and gyro checks need the
	# unported controller and gyro state (group 14)

"""
 * Move handling
 */
"""
def IN_Move(cmd): #usercmd_t *

	global mouse_x, mouse_y, old_mouse_x, old_mouse_y

	# Q2PORT: the C's IN_GamepadMove and gyro block need the unported controller
	# and gyro state (group 14)
	if not mouse_avail: # Q2PORT: id's mouse_avail
		return

	if m_filter.value:

		if mouse_x > 1 or mouse_x < -1:

			mouse_x = (mouse_x + old_mouse_x) * 0.5

		if mouse_y > 1 or mouse_y < -1:

			mouse_y = (mouse_y + old_mouse_y) * 0.5

		old_mouse_x = mouse_x
		old_mouse_y = mouse_y

	if mouse_x or mouse_y:

		if not exponential_speedup.value:

			mouse_x *= sensitivity.value
			mouse_y *= sensitivity.value
		else:

			if mouse_x > MOUSE_MIN or mouse_y > MOUSE_MIN or \
				mouse_x < -MOUSE_MIN or mouse_y < -MOUSE_MIN:

				mouse_x = (mouse_x * mouse_x * mouse_x) / 4
				mouse_y = (mouse_y * mouse_y * mouse_y) / 4

				if mouse_x > MOUSE_MAX:

					mouse_x = MOUSE_MAX
				elif mouse_x < -MOUSE_MAX:

					mouse_x = -MOUSE_MAX

				if mouse_y > MOUSE_MAX:

					mouse_y = MOUSE_MAX
				elif mouse_y < -MOUSE_MAX:

					mouse_y = -MOUSE_MAX

		# add mouse X/Y movement to cmd
		if (cl_input.in_strafe.state & 1) or (lookstrafe.value and mlooking):

			cmd.sidemove += m_side.value * mouse_x
		else:

			cl_main.cl.viewangles[shared.YAW] -= m_yaw.value * mouse_x

		if (mlooking or freelook.value) and not (cl_input.in_strafe.state & 1):

			cl_main.cl.viewangles[shared.PITCH] += m_pitch.value * mouse_y
		else:

			cmd.forwardmove -= m_forward.value * mouse_y

		mouse_x = mouse_y = 0

"""
 * Look down
 */
"""
def IN_MLookDown(): #void

	global mlooking

	mlooking = True

"""
 * Look up
 */
"""
def IN_MLookUp(): #void

	global mlooking

	mlooking = False
	cl_input.IN_CenterView()

"""
 * Shuts the backend down
 */
"""
def IN_Shutdown(): #void

	cmdparser.Cmd_RemoveCommand("+mlook")
	cmdparser.Cmd_RemoveCommand("-mlook")

	cmdparser.Cmd_RemoveCommand("+joyaltselector")
	cmdparser.Cmd_RemoveCommand("-joyaltselector")
	# the C also removes "+gyroaction" and "-gyroaction", Q2PORT: not registered

	clientserver.Com_Printf("Shutting down input.\n")

	# IN_Controller_Shutdown(false), Q2PORT: no gamepads (group 14)

def IN_GetClipboardText(n: int)->str: #char *, size_t

	# Q2PORT: returns the text; pygame's scrap module in place of SDL_GetClipboardText
	try:

		if not pygame.scrap.get_init():

			pygame.scrap.init()


		data = pygame.scrap.get(pygame.SCRAP_TEXT)

	except (pygame.error, NotImplementedError): # no clipboard support

		data = None


	if not data:

		return ""


	s = data.decode("utf-8", "replace").rstrip("\0")
	return s[:n - 1 - 1] # Q_strlcpy(out, s, n - 1);

def IN_SetClipboardText(s: str)->int: #const char * (returns int)

	# Q2PORT: pygame's scrap module in place of SDL_SetClipboardText
	try:

		if not pygame.scrap.get_init():

			pygame.scrap.init()


		pygame.scrap.put(pygame.SCRAP_TEXT, s.encode("utf-8"))
		return 0

	except (pygame.error, NotImplementedError): # no clipboard support

		return 1

def IN_JoyAltSelectorDown(): # (static)

	keyboard_h.joy_altselector_pressed = True

def IN_JoyAltSelectorUp(): # (static)

	keyboard_h.joy_altselector_pressed = False

"""
 * Removes all pending events from SDLs queue.
"""
def In_FlushQueue(): #void

	pygame.event.clear() # SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT);
	cl_keyboard.Key_MarkAllUp()
	IN_JoyAltSelectorUp()

def IN_NumpadIsOn()->bool: #void (returns qboolean)

	mod = pygame.key.get_mods() # SDL_Keymod mod = SDL_GetModState();

	if (mod & pygame.KMOD_NUM) == pygame.KMOD_NUM:

		return True


	return False

show_gamepad, show_haptic, show_gyro = False, False, False #qboolean

first_init = True #static qboolean

"""
 * Gyro calibration functions, called from menu
"""
def StartCalibration(): #void

	# Q2PORT: no gamepads or gyros until input/sdl2.c is ported (group 14)
	#ifdef NO_SDL_GYRO
	#ImuJoy_ResetSamples();
	#endif
	#IN_GYRO_ResetSamples();
	#updates_countdown = 300;
	#countdown_reason = REASON_GYROCALIBRATION;
	pass

def IsCalibrationZero()->bool: #void (returns qboolean)

	return (not gyro_calibration_x.value and not gyro_calibration_y.value and not gyro_calibration_z.value)

class joy_preset_t(object):

	def __init__(self, yawspeed, pitchspeed, extra_yawspeed, extra_pitchspeed, ramp_time):

		self.yawspeed = yawspeed #float
		self.pitchspeed = pitchspeed #float
		self.extra_yawspeed = extra_yawspeed #float
		self.extra_pitchspeed = extra_pitchspeed #float
		self.ramp_time = ramp_time #float

joy_presets = [ #static const joy_preset_t []
	joy_preset_t(   0.0,   0.0,   0.0,   0.0, 0.00 ),
	joy_preset_t(  50.0,  50.0,  60.0,   0.0, 0.50 ),
	joy_preset_t(  80.0,  50.0, 150.0, 120.0, 0.30 ),
	joy_preset_t( 160.0, 120.0, 220.0,   0.0, 0.35 ), # Default
	joy_preset_t( 240.0, 200.0, 220.0,   0.0, 0.30 ),
	joy_preset_t( 380.0, 240.0,   0.0,   0.0, 0.00 ),
	joy_preset_t( 450.0, 300.0,   0.0,   0.0, 0.00 ),
	joy_preset_t( 500.0, 500.0,   0.0,   0.0, 0.00 ),
	joy_preset_t( 720.0, 720.0,   0.0,   0.0, 0.00 ),
]

def IN_ApplyJoyPreset(): #void

	final_preset = len(joy_presets) - 1 #static const int, ARRLEN(joy_presets) - 1
	i = int(math.floor(shared.Q_clamp(joy_sensitivity.value, 0, final_preset) + 0.5)) # lroundf

	joy_sensitivity.modified = False
	if first_init: return

	cvar.Cvar_SetValue("joy_yawspeed", joy_presets[i].yawspeed)
	cvar.Cvar_SetValue("joy_pitchspeed",
				  joy_presets[i].pitchspeed * shared.Q_signf(joy_pitchspeed.value))
	cvar.Cvar_SetValue("joy_extra_yawspeed", joy_presets[i].extra_yawspeed)
	cvar.Cvar_SetValue("joy_extra_pitchspeed", joy_presets[i].extra_pitchspeed)
	cvar.Cvar_SetValue("joy_ramp_time", joy_presets[i].ramp_time)

def EQF(a, b): return (abs((a) - (b)) < 1.0e-6) #define EQF(a, b)

def IN_MatchJoyPreset()->bool: #void (returns qboolean)

	num_presets = len(joy_presets) #static const int, ARRLEN(joy_presets)

	for i in range(num_presets):

		if (EQF(joy_presets[i].yawspeed, joy_yawspeed.value)
			and EQF(joy_presets[i].pitchspeed, abs(joy_pitchspeed.value))
			and EQF(joy_presets[i].extra_yawspeed, joy_extra_yawspeed.value)
			and EQF(joy_presets[i].extra_pitchspeed, joy_extra_pitchspeed.value)
			and EQF(joy_presets[i].ramp_time, joy_ramp_time.value)):

			cvar.Cvar_SetValue("joy_sensitivity", i)
			joy_sensitivity.modified = False
			return True



	return False
