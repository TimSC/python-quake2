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

This file implements the input handling like mouse events and
keyboard strokes.

=======================================================================
"""
from __future__ import annotations

import copy

from client.input import sdl2
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common import clientserver
from common import frame
from common import cmdparser
from common import crc
from common import cvar
from common import movemsg
from common import szone
from common import netchan
from client import cl_cin
from client import cl_keyboard
from client import cl_main
from client.header import client as client_h

"""
#include "header/client.h"
#include "input/header/input.h"
"""

cl_nodelta = None #cvar_t *
old_sys_frame_time = 0
frame_msec = 0


in_klook = client_h.kbutton_t()
in_left = client_h.kbutton_t()
in_right = client_h.kbutton_t()
in_forward = client_h.kbutton_t()
in_back = client_h.kbutton_t()
in_lookup = client_h.kbutton_t()
in_lookdown = client_h.kbutton_t()
in_moveleft = client_h.kbutton_t()
in_moveright = client_h.kbutton_t()
in_strafe = client_h.kbutton_t()
in_speed = client_h.kbutton_t()
in_use = client_h.kbutton_t()
in_attack = client_h.kbutton_t()
in_up = client_h.kbutton_t()
in_down = client_h.kbutton_t()

in_impulse = 0

cl_upspeed = None
cl_forwardspeed = None
cl_sidespeed = None
cl_yawspeed = None
cl_pitchspeed = None
cl_run = None
cl_anglespeedkey = None


"""
// cl_main.cl.input.c  -- builds an intended movement command to send to the server

#include "client.h"
"""
center_target = 0 #static float
center_progress = 1.0 #static float, from 0.0 to 1.0
center_start = 0 #static int
cl_centertime = None #cvar_t *

"""
extern	unsigned	sys_frame_time;
"""
def KeyDown(b: client_h.kbutton_t): #kbutton_t * (static)

	"""
	int k;
	char *c;
	"""

	c = cmdparser.Cmd_Argv(1)

	if c: # c[0]

		k = shared_c.atoi(c) # (int)strtol(c, (char **)NULL, 10)

	else:

		k = -1 # typed manually at the console for continuous down


	if (k == b.down[0]) or (k == b.down[1]):

		return # repeating key


	if not b.down[0]:

		b.down[0] = k

	elif not b.down[1]:

		b.down[1] = k

	else:

		clientserver.Com_Printf("Three keys down for a button!\n")
		return


	if b.state & 1:

		return # still down


	# save timestamp
	c = cmdparser.Cmd_Argv(2)
	b.downtime = shared_c.atoi(c) # (int)strtol(c, (char **)NULL, 10)

	if not b.downtime:

		b.downtime = sdl2.sys_frame_time - 100


	b.state |= 1 + 2 # down + impulse down



def KeyUp(b: client_h.kbutton_t): #kbutton_t * (static)

	"""
	int k;
	char *c;
	unsigned uptime;
	"""

	c = cmdparser.Cmd_Argv(1)

	if c: # c[0]

		k = shared_c.atoi(c) # (int)strtol(c, (char **)NULL, 10)

	else:

		# typed manually at the console, assume for unsticking, so clear all
		b.down[0] = b.down[1] = 0
		b.state = 4 # impulse up
		return


	if b.down[0] == k:

		b.down[0] = 0

	elif b.down[1] == k:

		b.down[1] = 0

	else:

		return # key up without coresponding down (menu pass through)


	if b.down[0] or b.down[1]:

		return # some other key is still holding it down


	if not (b.state & 1):

		return # still up (this should not happen)


	# save timestamp
	c = cmdparser.Cmd_Argv(2)
	uptime = shared_c.atoi(c) # (int)strtol(c, (char **)NULL, 10)

	if uptime:

		b.msec += uptime - b.downtime

	else:

		b.msec += 10


	b.state &= ~1 # now up
	b.state |= 4 # impulse up



def IN_KLookDown(): KeyDown(in_klook)
def IN_KLookUp(): KeyUp(in_klook)
def IN_UpDown(): KeyDown(in_up)
def IN_UpUp(): KeyUp(in_up)
def IN_DownDown(): KeyDown(in_down)
def IN_DownUp(): KeyUp(in_down)
def IN_LeftDown(): KeyDown(in_left)
def IN_LeftUp(): KeyUp(in_left)
def IN_RightDown(): KeyDown(in_right)
def IN_RightUp(): KeyUp(in_right)
def IN_ForwardDown(): KeyDown(in_forward)
def IN_ForwardUp(): KeyUp(in_forward)
def IN_BackDown(): KeyDown(in_back)
def IN_BackUp(): KeyUp(in_back)
def IN_LookupDown(): KeyDown(in_lookup)
def IN_LookupUp(): KeyUp(in_lookup)
def IN_LookdownDown(): KeyDown(in_lookdown)
def IN_LookdownUp(): KeyUp(in_lookdown)
def IN_MoveleftDown(): KeyDown(in_moveleft)
def IN_MoveleftUp(): KeyUp(in_moveleft)
def IN_MoverightDown(): KeyDown(in_moveright)
def IN_MoverightUp(): KeyUp(in_moveright)
def IN_SpeedDown(): KeyDown(in_speed)
def IN_SpeedUp(): KeyUp(in_speed)
def IN_StrafeDown(): KeyDown(in_strafe)
def IN_StrafeUp(): KeyUp(in_strafe)
def IN_AttackDown(): KeyDown(in_attack)
def IN_AttackUp(): KeyUp(in_attack)
def IN_UseDown(): KeyDown(in_use)
def IN_UseUp(): KeyUp(in_use)


def IN_Impulse(): # (static)

	global in_impulse

	in_impulse = shared_c.atoi(cmdparser.Cmd_Argv(1)) # (int)strtol(Cmd_Argv(1), (char **)NULL, 10)



"""
===============
CL_KeyState

Returns the fraction of the frame that the key was down
===============
"""
def CL_KeyState(key): #kbutton_t * (returns static float)

	"""
	float val;
	int msec;
	"""

	key.state &= 1
	# clear impulses
	msec = key.msec
	key.msec = 0
	if key.state:

		# still down
		msec += sdl2.sys_frame_time - key.downtime
		key.downtime = sdl2.sys_frame_time


	val = msec / frame_msec
	if val < 0:

		val = 0


	if val > 1:

		val = 1


	return val


"""
================
CL_AdjustAngles

Moves the local angle positions
================
"""
def CL_AdjustAngles(): # (static)
	global center_progress

	"""
	float speed;
	float up, down;
	"""

	if in_speed.state & 1:

		speed = cl_main.cls.nframetime * cl_anglespeedkey.value

	else:

		speed = cl_main.cls.nframetime


	if not (in_strafe.state & 1):

		cl_main.cl.viewangles[shared.YAW] -= speed * cl_yawspeed.value * CL_KeyState(in_right)
		cl_main.cl.viewangles[shared.YAW] += speed * cl_yawspeed.value * CL_KeyState(in_left)


	if in_klook.state & 1:

		cl_main.cl.viewangles[shared.PITCH] -= speed * cl_pitchspeed.value * CL_KeyState(in_forward)
		cl_main.cl.viewangles[shared.PITCH] += speed * cl_pitchspeed.value * CL_KeyState(in_back)


	up = CL_KeyState(in_lookup)
	down = CL_KeyState(in_lookdown)
	cl_main.cl.viewangles[shared.PITCH] -= speed * cl_pitchspeed.value * up
	cl_main.cl.viewangles[shared.PITCH] += speed * cl_pitchspeed.value * down
	# centerview progression
	if center_progress < 1.0 and cl_centertime.value > 0:

		#float cur_progress = (float)(sys_frame_time - center_start) / cl_centertime->value;
		cur_progress = (sdl2.sys_frame_time - center_start) / cl_centertime.value
		if cur_progress >= 1.0:

			cur_progress = 1.0

		else:

			# "Ease out" processing: f(x) = 1-(1-x)^2 , 0 <= x <= 1
			cur_progress = 1.0 - cur_progress
			cur_progress *= cur_progress
			cur_progress = 1.0 - cur_progress


		cl_main.cl.viewangles[shared.PITCH] -= (cur_progress - center_progress) * center_target
		center_progress = cur_progress

def CL_BaseMove (cmd): #usercmd_t *

	CL_AdjustAngles ()

	cmd.reset()
	cmd.angles = [cl_main.cl.viewangles[0], cl_main.cl.viewangles[1], cl_main.cl.viewangles[2]]

	if in_strafe.state & 1:
		cmd.sidemove += cl_sidespeed.value * CL_KeyState(in_right)
		cmd.sidemove -= cl_sidespeed.value * CL_KeyState(in_left)

	cmd.sidemove += cl_sidespeed.value * CL_KeyState(in_moveright)
	cmd.sidemove -= cl_sidespeed.value * CL_KeyState(in_moveleft)

	cmd.upmove += cl_upspeed.value * CL_KeyState(in_up)
	cmd.upmove -= cl_upspeed.value * CL_KeyState(in_down)

	if not (in_klook.state & 1):
		cmd.forwardmove += cl_forwardspeed.value * CL_KeyState(in_forward)
		cmd.forwardmove -= cl_forwardspeed.value * CL_KeyState(in_back)

	if (in_speed.state & 1) ^ (int(cl_run.value)):
		cmd.forwardmove *= 2
		cmd.sidemove *= 2
		cmd.upmove *= 2

def CL_ClampPitch ():
	pitch = shared.SHORT2ANGLE(cl_main.cl.frame.playerstate.pmove.delta_angles[shared.PITCH])
	if pitch > 180:
		pitch -= 360

	if cl_main.cl.viewangles[shared.PITCH] + pitch < -360:
		cl_main.cl.viewangles[shared.PITCH] += 360
	if cl_main.cl.viewangles[shared.PITCH] + pitch > 360:
		cl_main.cl.viewangles[shared.PITCH] -= 360

	if cl_main.cl.viewangles[shared.PITCH] + pitch > 89:
		cl_main.cl.viewangles[shared.PITCH] = 89 - pitch
	if cl_main.cl.viewangles[shared.PITCH] + pitch < -89:
		cl_main.cl.viewangles[shared.PITCH] = -89 - pitch


def IN_CenterView(): #
	global center_progress, center_start, center_target

	if cl_centertime.value <= 0:

		# vanilla
		cl_main.cl.viewangles[shared.PITCH] = -shared.SHORT2ANGLE(cl_main.cl.frame.playerstate.pmove.delta_angles[shared.PITCH])

	else:

		# start centering the view
		center_target = cl_main.cl.viewangles[shared.PITCH] - shared.SHORT2ANGLE(cl_main.cl.frame.playerstate.pmove.delta_angles[shared.PITCH])
		center_progress = 0.0
		center_start = sdl2.sys_frame_time

"""
 * Centers the view

"""
def IN_ForceCenterView(): # (static)

	cl_main.cl.viewangles[shared.PITCH] = 0

def CL_InitInput(): #
	global cl_centertime, cl_nodelta

	cmdparser.Cmd_AddCommand("centerview", IN_CenterView)
	cmdparser.Cmd_AddCommand("force_centerview", IN_ForceCenterView)
	cmdparser.Cmd_AddCommand("+moveup", IN_UpDown)
	cmdparser.Cmd_AddCommand("-moveup", IN_UpUp)
	cmdparser.Cmd_AddCommand("+movedown", IN_DownDown)
	cmdparser.Cmd_AddCommand("-movedown", IN_DownUp)
	cmdparser.Cmd_AddCommand("+left", IN_LeftDown)
	cmdparser.Cmd_AddCommand("-left", IN_LeftUp)
	cmdparser.Cmd_AddCommand("+right", IN_RightDown)
	cmdparser.Cmd_AddCommand("-right", IN_RightUp)
	cmdparser.Cmd_AddCommand("+forward", IN_ForwardDown)
	cmdparser.Cmd_AddCommand("-forward", IN_ForwardUp)
	cmdparser.Cmd_AddCommand("+back", IN_BackDown)
	cmdparser.Cmd_AddCommand("-back", IN_BackUp)
	cmdparser.Cmd_AddCommand("+lookup", IN_LookupDown)
	cmdparser.Cmd_AddCommand("-lookup", IN_LookupUp)
	cmdparser.Cmd_AddCommand("+lookdown", IN_LookdownDown)
	cmdparser.Cmd_AddCommand("-lookdown", IN_LookdownUp)
	cmdparser.Cmd_AddCommand("+strafe", IN_StrafeDown)
	cmdparser.Cmd_AddCommand("-strafe", IN_StrafeUp)
	cmdparser.Cmd_AddCommand("+moveleft", IN_MoveleftDown)
	cmdparser.Cmd_AddCommand("-moveleft", IN_MoveleftUp)
	cmdparser.Cmd_AddCommand("+moveright", IN_MoverightDown)
	cmdparser.Cmd_AddCommand("-moveright", IN_MoverightUp)
	cmdparser.Cmd_AddCommand("+speed", IN_SpeedDown)
	cmdparser.Cmd_AddCommand("-speed", IN_SpeedUp)
	cmdparser.Cmd_AddCommand("+attack", IN_AttackDown)
	cmdparser.Cmd_AddCommand("-attack", IN_AttackUp)
	cmdparser.Cmd_AddCommand("+use", IN_UseDown)
	cmdparser.Cmd_AddCommand("-use", IN_UseUp)
	cmdparser.Cmd_AddCommand("impulse", IN_Impulse)
	cmdparser.Cmd_AddCommand("+klook", IN_KLookDown)
	cmdparser.Cmd_AddCommand("-klook", IN_KLookUp)
	cl_nodelta = cvar.Cvar_Get("cl_nodelta", "0", 0)
	cl_centertime = cvar.Cvar_Get("cl_centertime", "180", shared.CVAR_ARCHIVE)


def CL_RefreshCmd(): #

	global frame_msec, old_sys_frame_time

	"""
	int ms;
	usercmd_t *cmd;
	"""

	# CMD to fill
	cmd = cl_main.cl.cmds[cl_main.cls.netchan.outgoing_sequence & (client_h.CMD_BACKUP - 1)]
	# Calculate delta
	frame_msec = sdl2.sys_frame_time - old_sys_frame_time
	# Check bounds
	if frame_msec < 1:

		return

	elif frame_msec > 200:

		frame_msec = 200


	# Add movement
	CL_BaseMove(cmd)
	sdl2.IN_Move(cmd)
	# Clamp angels for prediction
	CL_ClampPitch()
	cmd.angles[0] = ((shared.ANGLE2SHORT(cl_main.cl.viewangles[0]) + 0x8000) & 0xffff) - 0x8000 # short
	cmd.angles[1] = ((shared.ANGLE2SHORT(cl_main.cl.viewangles[1]) + 0x8000) & 0xffff) - 0x8000 # short
	cmd.angles[2] = ((shared.ANGLE2SHORT(cl_main.cl.viewangles[2]) + 0x8000) & 0xffff) - 0x8000 # short
	# Update time for prediction
	ms = int(cl_main.cls.nframetime * 1000.0)
	if ms > 250:

		ms = 100


	cmd.msec = ms
	# Update frame time for the next call
	old_sys_frame_time = sdl2.sys_frame_time
	# Important events are send immediately
	if ((in_attack.state & 2)) or (in_use.state & 2):

		cl_main.cls.forcePacket = True

def CL_RefreshMove(): #

	global frame_msec, old_sys_frame_time

	"""
	usercmd_t *cmd;
	"""

	# CMD to fill
	cmd = cl_main.cl.cmds[cl_main.cls.netchan.outgoing_sequence & (client_h.CMD_BACKUP - 1)]
	# Calculate delta
	frame_msec = sdl2.sys_frame_time - old_sys_frame_time
	# Check bounds
	if frame_msec < 1:

		return

	elif frame_msec > 200:

		frame_msec = 200


	# Add movement
	CL_BaseMove(cmd)
	sdl2.IN_Move(cmd)
	old_sys_frame_time = sdl2.sys_frame_time

def CL_FinalizeCmd(): # (static)
	global in_impulse

	"""
	usercmd_t *cmd;
	"""

	# CMD to fill
	cmd = cl_main.cl.cmds[cl_main.cls.netchan.outgoing_sequence & (client_h.CMD_BACKUP - 1)]
	# Mouse button events
	if in_attack.state & 3:

		cmd.buttons |= shared.BUTTON_ATTACK


	in_attack.state &= ~2
	if in_use.state & 3:

		cmd.buttons |= shared.BUTTON_USE


	in_use.state &= ~2
	# Keyboard events
	if cl_keyboard.anykeydown and cl_main.cls.key_dest == client_h.keydest_t.key_game:

		cmd.buttons |= shared.BUTTON_ANY


	cmd.impulse = in_impulse
	in_impulse = 0
	# Set light level for muzzle flash
	cmd.lightlevel = int(cl_main.cl_lightlevel.value) & 0xff # byte

"""
=================
CL_SendCmd
=================
"""
def CL_SendCmd(): #void

	"""
	sizebuf_t buf;
	byte data[128];
	int i;
	usercmd_t *cmd, *oldcmd;
	usercmd_t nullcmd;
	int checksumIndex;
	"""

	buf = common_h.sizebuf_t() # memset(&buf, 0, sizeof(buf));

	# save this command off for prediction
	i = cl_main.cls.netchan.outgoing_sequence & (client_h.CMD_BACKUP - 1)
	cmd = cl_main.cl.cmds[i]
	cl_main.cl.cmd_time[i] = cl_main.cls.realtime # for netgraph ping calculation

	CL_FinalizeCmd()

	cl_main.cl.cmd = copy.copy(cmd) # cl.cmd = *cmd;
	cl_main.cl.cmd.angles = list(cmd.angles)

	if (cl_main.cls.state == client_h.connstate_t.ca_disconnected) or (cl_main.cls.state == client_h.connstate_t.ca_connecting):

		return


	if cl_main.cls.state == client_h.connstate_t.ca_connected:

		if cl_main.cls.netchan.message.cursize or (frame.curtime - cl_main.cls.netchan.last_sent > 1000):

			netchan.Netchan_Transmit(cl_main.cls.netchan, b"") # Netchan_Transmit(&cls.netchan, 0, buf.data);


		return


	# send a userinfo update if needed
	if cvar.userinfo_modified:

		cl_main.CL_FixUpGender()
		cvar.userinfo_modified = False
		movemsg.MSG_WriteByte(cl_main.cls.netchan.message, common_h.clc_ops_e.clc_userinfo.value)
		movemsg.MSG_WriteString(cl_main.cls.netchan.message, cvar.Cvar_Userinfo().encode('ascii'))


	szone.SZ_Init(buf, 128) # SZ_Init(&buf, data, sizeof(data));

	if ((cl_main.cls.realtime > cl_cin.abort_cinematic) and (cl_main.cl.cinematictime > 0) and
			not cl_main.cl.attractloop and (cl_main.cls.realtime - cl_main.cl.cinematictime > 1000) and
			(cl_main.cls.key_dest == client_h.keydest_t.key_game)):

		# skip the rest of the cinematic
		cl_cin.SCR_FinishCinematic()


	# begin a client move command
	movemsg.MSG_WriteByte(buf, common_h.clc_ops_e.clc_move.value)

	# save the position for a checksum byte
	checksumIndex = buf.cursize
	movemsg.MSG_WriteByte(buf, 0)

	# let the server know what the last frame we
	# got was, so the next message can be delta
	# compressed
	if cl_nodelta.value or not cl_main.cl.frame.valid or cl_main.cls.demowaiting:

		movemsg.MSG_WriteLong(buf, -1) # no compression

	else:

		movemsg.MSG_WriteLong(buf, cl_main.cl.frame.serverframe)


	# send this and the previous cmds in the message, so
	# if the last packet was dropped, it can be recovered
	i = (cl_main.cls.netchan.outgoing_sequence - 2) & (client_h.CMD_BACKUP - 1)
	cmd = cl_main.cl.cmds[i]
	nullcmd = shared.usercmd_t() # memset(&nullcmd, 0, sizeof(nullcmd));
	movemsg.MSG_WriteDeltaUsercmd(buf, nullcmd, cmd)
	oldcmd = cmd

	i = (cl_main.cls.netchan.outgoing_sequence - 1) & (client_h.CMD_BACKUP - 1)
	cmd = cl_main.cl.cmds[i]
	movemsg.MSG_WriteDeltaUsercmd(buf, oldcmd, cmd)
	oldcmd = cmd

	i = (cl_main.cls.netchan.outgoing_sequence) & (client_h.CMD_BACKUP - 1)
	cmd = cl_main.cl.cmds[i]
	movemsg.MSG_WriteDeltaUsercmd(buf, oldcmd, cmd)

	# calculate a checksum over the move commands
	buf.data[checksumIndex] = crc.COM_BlockSequenceCRCByte(
			buf, checksumIndex + 1, buf.cursize - checksumIndex - 1,
			cl_main.cls.netchan.outgoing_sequence)[0]

	# deliver the message
	netchan.Netchan_Transmit(cl_main.cls.netchan, buf.data[:buf.cursize])

	# Reinit the current cmd buffer
	cmd = cl_main.cl.cmds[cl_main.cls.netchan.outgoing_sequence & (client_h.CMD_BACKUP - 1)]
	cmd.reset() # memset(cmd, 0, sizeof(*cmd));


cl_run, freelook, lookspring, lookstrafe, sensitivity = None, None, None, None, None
