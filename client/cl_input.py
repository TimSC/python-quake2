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

from client import cl_main, cl_cin
from linux import vid_so, sys_linux, q_shlinux
from common.header import common as common_h
from common.header import shared
from common import clientserver
from common import cmdparser
from common import crc
from common import cvar
from common import movemsg
from common import szone
from common import netchan
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
"""
extern	unsigned	sys_frame_time;
"""
def KeyDown(b):
	c = cmdparser.Cmd_Argv(1)
	if c:
		k = int(c)
	else:
		k = -1

	if k == b.down[0] or k == b.down[1]:
		return

	if not b.down[0]:
		b.down[0] = k
	elif not b.down[1]:
		b.down[1] = k
	else:
		clientserver.Com_Printf("Three keys down for a button!\n")
		return

	if b.state & 1:
		return

	c = cmdparser.Cmd_Argv(2)
	b.downtime = int(c) if c else 0
	if not b.downtime:
		b.downtime = sys_linux.sys_frame_time - 100

	b.state |= 1 + 2


def KeyUp(b):
	c = cmdparser.Cmd_Argv(1)
	if c:
		k = int(c)
	else:
		b.down[0] = 0
		b.down[1] = 0
		b.state = 4
		return

	if b.down[0] == k:
		b.down[0] = 0
	elif b.down[1] == k:
		b.down[1] = 0
	else:
		return
	if b.down[0] or b.down[1]:
		return

	if not (b.state & 1):
		return

	c = cmdparser.Cmd_Argv(2)
	uptime = int(c) if c else 0
	if uptime:
		b.msec += uptime - b.downtime
	else:
		b.msec += 10

	b.state &= ~1
	b.state |= 4


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


def IN_Impulse():
	global in_impulse
	c = cmdparser.Cmd_Argv(1)
	in_impulse = int(c) if c else 0


"""
===============
CL_KeyState

Returns the fraction of the frame that the key was down
===============
"""
def CL_KeyState(key):
	global frame_msec

	key.state &= 1

	msec = key.msec
	key.msec = 0

	if key.state:
		msec += sys_linux.sys_frame_time - key.downtime
		key.downtime = sys_linux.sys_frame_time

	val = float(msec) / float(frame_msec) if frame_msec else 0.0
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
def CL_AdjustAngles():
	if in_speed.state & 1:
		speed = cl_main.cls.frametime * cl_anglespeedkey.value
	else:
		speed = cl_main.cls.frametime

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
def CL_FinishMove (cmd): #usercmd_t *

	global in_impulse

	if in_attack.state & 3:
		cmd.buttons |= shared.BUTTON_ATTACK
	in_attack.state &= ~2

	if in_use.state & 3:
		cmd.buttons |= shared.BUTTON_USE
	in_use.state &= ~2

	if cl_keyboard.anykeydown and cl_main.cls.key_dest == client_h.keydest_t.key_game:
		cmd.buttons |= shared.BUTTON_ANY

	ms = cl_main.cls.frametime * 1000
	if ms > 250:
		ms = 100
	cmd.msec = int(ms)

	CL_ClampPitch ()
	for i in range(3):
		cmd.angles[i] = ((shared.ANGLE2SHORT(cl_main.cl.viewangles[i]) + 0x8000) & 0xffff) - 0x8000 # short cmd->angles[i]

	cmd.impulse = in_impulse
	in_impulse = 0

	cmd.lightlevel = int(cl_main.cl_lightlevel.value) if cl_main.cl_lightlevel else 0

def CL_CreateCmd ():

	global old_sys_frame_time, frame_msec

	cmd = shared.usercmd_t()

	frame_msec = sys_linux.sys_frame_time - old_sys_frame_time
	if frame_msec < 1:
		frame_msec = 1
	if frame_msec > 200:
		frame_msec = 200
	
	# get basic movement from keyboard
	CL_BaseMove (cmd)

	# allow mice or other external controllers to add to the move
	vid_so.IN_Move (cmd)

	CL_FinishMove (cmd)

	old_sys_frame_time = sys_linux.sys_frame_time

	##cmd.impulse = cl_main.cls.framecount;

	return cmd

def IN_CenterView ():
	cl_main.cl.viewangles[shared.PITCH] = -shared.SHORT2ANGLE(
		cl_main.cl.frame.playerstate.pmove.delta_angles[shared.PITCH]
	)

"""
/*
 * Centers the view
 */
static void
IN_ForceCenterView(void)
{
	cl.viewangles[PITCH] = 0;
}
"""

def CL_InitInput ():

	global cl_nodelta
	global cl_upspeed, cl_forwardspeed, cl_sidespeed
	global cl_yawspeed, cl_pitchspeed, cl_run, cl_anglespeedkey

	cmdparser.Cmd_AddCommand ("centerview", IN_CenterView)

	cmdparser.Cmd_AddCommand ("+moveup", IN_UpDown)
	cmdparser.Cmd_AddCommand ("-moveup", IN_UpUp)
	cmdparser.Cmd_AddCommand ("+movedown", IN_DownDown)
	cmdparser.Cmd_AddCommand ("-movedown", IN_DownUp)
	cmdparser.Cmd_AddCommand ("+left", IN_LeftDown)
	cmdparser.Cmd_AddCommand ("-left", IN_LeftUp)
	cmdparser.Cmd_AddCommand ("+right", IN_RightDown)
	cmdparser.Cmd_AddCommand ("-right", IN_RightUp)
	cmdparser.Cmd_AddCommand ("+forward", IN_ForwardDown)
	cmdparser.Cmd_AddCommand ("-forward", IN_ForwardUp)
	cmdparser.Cmd_AddCommand ("+back", IN_BackDown)
	cmdparser.Cmd_AddCommand ("-back", IN_BackUp)
	cmdparser.Cmd_AddCommand ("+lookup", IN_LookupDown)
	cmdparser.Cmd_AddCommand ("-lookup", IN_LookupUp)
	cmdparser.Cmd_AddCommand ("+lookdown", IN_LookdownDown)
	cmdparser.Cmd_AddCommand ("-lookdown", IN_LookdownUp)
	cmdparser.Cmd_AddCommand ("+strafe", IN_StrafeDown)
	cmdparser.Cmd_AddCommand ("-strafe", IN_StrafeUp)
	cmdparser.Cmd_AddCommand ("+moveleft", IN_MoveleftDown)
	cmdparser.Cmd_AddCommand ("-moveleft", IN_MoveleftUp)
	cmdparser.Cmd_AddCommand ("+moveright", IN_MoverightDown)
	cmdparser.Cmd_AddCommand ("-moveright", IN_MoverightUp)
	cmdparser.Cmd_AddCommand ("+speed", IN_SpeedDown)
	cmdparser.Cmd_AddCommand ("-speed", IN_SpeedUp)
	cmdparser.Cmd_AddCommand ("+attack", IN_AttackDown)
	cmdparser.Cmd_AddCommand ("-attack", IN_AttackUp)
	cmdparser.Cmd_AddCommand ("+use", IN_UseDown)
	cmdparser.Cmd_AddCommand ("-use", IN_UseUp)
	cmdparser.Cmd_AddCommand ("impulse", IN_Impulse)
	cmdparser.Cmd_AddCommand ("+klook", IN_KLookDown)
	cmdparser.Cmd_AddCommand ("-klook", IN_KLookUp)

	cl_nodelta = cvar.Cvar_Get ("cl_nodelta", "0", 0)
	cl_upspeed = cvar.Cvar_Get ("cl_upspeed", "200", 0)
	cl_forwardspeed = cvar.Cvar_Get ("cl_forwardspeed", "200", 0)
	cl_sidespeed = cvar.Cvar_Get ("cl_sidespeed", "200", 0)
	cl_yawspeed = cvar.Cvar_Get ("cl_yawspeed", "140", 0)
	cl_pitchspeed = cvar.Cvar_Get ("cl_pitchspeed", "150", 0)
	cl_run = cvar.Cvar_Get ("cl_run", "0", 0)
	cl_anglespeedkey = cvar.Cvar_Get ("cl_anglespeedkey", "1.5", 0)


"""
void
CL_RefreshCmd(void)
{
	int ms;
	usercmd_t *cmd;

	// CMD to fill
	cmd = &cl.cmds[cls.netchan.outgoing_sequence & (CMD_BACKUP - 1)];

	// Calculate delta
	frame_msec = sys_frame_time - old_sys_frame_time;

	// Check bounds
	if (frame_msec < 1)
	{
		return;
	}
	else if (frame_msec > 200)
	{
		frame_msec = 200;
	}

	// Add movement
	CL_BaseMove(cmd);
	IN_Move(cmd);

	// Clamp angels for prediction
	CL_ClampPitch();

	cmd->angles[0] = ANGLE2SHORT(cl.viewangles[0]);
	cmd->angles[1] = ANGLE2SHORT(cl.viewangles[1]);
	cmd->angles[2] = ANGLE2SHORT(cl.viewangles[2]);

	// Update time for prediction
	ms = (int)(cls.nframetime * 1000.0f);

	if (ms > 250)
	{
		ms = 100;
	}

	cmd->msec = ms;

	// Update frame time for the next call
	old_sys_frame_time = sys_frame_time;

	// Important events are send immediately
	if (((in_attack.state & 2)) || (in_use.state & 2))
	{
		cls.forcePacket = true;
	}
}
"""

"""
void
CL_RefreshMove(void)
{
	usercmd_t *cmd;

	// CMD to fill
	cmd = &cl.cmds[cls.netchan.outgoing_sequence & (CMD_BACKUP - 1)];

	// Calculate delta
	frame_msec = sys_frame_time - old_sys_frame_time;

	// Check bounds
	if (frame_msec < 1)
	{
		return;
	}
	else if (frame_msec > 200)
	{
		frame_msec = 200;
	}

	// Add movement
	CL_BaseMove(cmd);
	IN_Move(cmd);

	old_sys_frame_time = sys_frame_time;
}
"""

"""
static void
CL_FinalizeCmd(void)
{
	usercmd_t *cmd;

	// CMD to fill
	cmd = &cl.cmds[cls.netchan.outgoing_sequence & (CMD_BACKUP - 1)];

	// Mouse button events
	if (in_attack.state & 3)
	{
		cmd->buttons |= BUTTON_ATTACK;
	}

	in_attack.state &= ~2;

	if (in_use.state & 3)
	{
		cmd->buttons |= BUTTON_USE;
	}

	in_use.state &= ~2;

	// Keyboard events
	if (anykeydown && cls.key_dest == key_game)
	{
		cmd->buttons |= BUTTON_ANY;
	}

	cmd->impulse = in_impulse;
	in_impulse = 0;

	// Set light level for muzzle flash
	cmd->lightlevel = (byte)cl_lightlevel->value;
}
"""

"""
=================
CL_SendCmd
=================
"""
def CL_SendCmd ():

	buf = common_h.sizebuf_t()
	#byte		data[128];
	#int			i;
	#usercmd_t	*cmd, *oldcmd;
	nullcmd = shared.usercmd_t()
	#int			checksumIndex;

	# build a command even if not connected

	# save this command off for prediction
	i = cl_main.cls.netchan.outgoing_sequence & (client_h.CMD_BACKUP-1)
	#cmd = &cl.cmds[i];
	cl_main.cl.cmd_time[i] = cl_main.cls.realtime	# for netgraph ping calculation

	cmd = CL_CreateCmd () # a new usercmd_t each call, so storing it is the struct copy
	cl_main.cl.cmds[i] = cmd # *cmd = CL_CreateCmd ();

	cl_main.cl.cmd = cmd # cl.cmd = *cmd;, cl.cmds[i] is not changed after this

	if cl_main.cls.state == client_h.connstate_t.ca_disconnected or cl_main.cls.state == client_h.connstate_t.ca_connecting:
		return

	if cl_main.cls.state == client_h.connstate_t.ca_connected:
	
		if cl_main.cls.netchan.message.cursize or q_shlinux.curtime - cl_main.cls.netchan.last_sent > 1000:
			netchan.Netchan_Transmit (cl_main.cls.netchan, b"")
		return
	
	# send a userinfo update if needed
	if cvar.userinfo_modified:
	
		cl_main.CL_FixUpGender()
		cvar.userinfo_modified = False
		movemsg.MSG_WriteByte (cl_main.cls.netchan.message, common_h.clc_ops_e.clc_userinfo.value)
		movemsg.MSG_WriteString (cl_main.cls.netchan.message, cvar.Cvar_Userinfo().encode('ascii') )
	
	szone.SZ_Init (buf, 128)

	if cmd.buttons and cl_main.cl.cinematictime > 0 and not cl_main.cl.attractloop \
		and cl_main.cls.realtime - cl_main.cl.cinematictime > 1000:
		# skip the rest of the cinematic
		cl_cin.SCR_FinishCinematic ()
	
	# begin a client move command
	movemsg.MSG_WriteByte (buf, common_h.clc_ops_e.clc_move.value.to_bytes(1, 'big'))

	# save the position for a checksum byte
	checksumIndex = len(buf.data)
	movemsg.MSG_WriteByte (buf, b'\x00')
	
	# let the server know what the last frame we
	# got was, so the next message can be delta compressed

	if cl_nodelta.value or not cl_main.cl.frame.valid or cl_main.cls.demowaiting:
		movemsg.MSG_WriteSLong (buf, -1)	# no compression
	else:
		movemsg.MSG_WriteLong (buf, cl_main.cl.frame.serverframe)

	# send this and the previous cmds in the message, so
	# if the last packet was dropped, it can be recovered
	
	i = (cl_main.cls.netchan.outgoing_sequence-2) & (client_h.CMD_BACKUP-1)
	cmd = cl_main.cl.cmds[i]
	movemsg.MSG_WriteDeltaUsercmd (buf, nullcmd, cmd)
	oldcmd = cmd

	i = (cl_main.cls.netchan.outgoing_sequence-1) & (client_h.CMD_BACKUP-1)
	cmd = cl_main.cl.cmds[i]
	movemsg.MSG_WriteDeltaUsercmd (buf, oldcmd, cmd)
	oldcmd = cmd

	i = (cl_main.cls.netchan.outgoing_sequence) & (client_h.CMD_BACKUP-1)
	cmd = cl_main.cl.cmds[i]
	movemsg.MSG_WriteDeltaUsercmd (buf, oldcmd, cmd)

	# calculate a checksum over the move commands
	buf.data[checksumIndex] = crc.COM_BlockSequenceCRCByte(
		buf, checksumIndex + 1, len(buf.data) - checksumIndex - 1,
		cl_main.cls.netchan.outgoing_sequence)[0]

	#
	# deliver the message
	#
	netchan.Netchan_Transmit (cl_main.cls.netchan, buf.data)

cl_run, freelook, lookspring, lookstrafe, sensitivity = None, None, None, None, None
