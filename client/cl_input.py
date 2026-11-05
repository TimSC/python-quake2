"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""
from __future__ import annotations

import numpy as np
from qcommon import cvar, net_chan, qcommon, common, cmd
from game import q_shared
from client import cl_main, client, keys, client, cl_cin
from linux import vid_so, sys_linux, q_shlinux
"""
// cl_main.cl.input.c  -- builds an intended movement command to send to the server

#include "client.h"
"""
cl_nodelta = None #cvar_t *
"""
extern	unsigned	sys_frame_time;
"""
old_sys_frame_time = 0
frame_msec = 0
"""
/*
===============================================================================

KEY BUTTONS

Continuous button event tracking is complicated by the fact that two different
input sources (say, mouse button 1 and the control key) can both press the
same button, but the button should only be released when both of the
pressing key have been released.

When a key event issues a button command (+forward, +attack, etc), it appends
its key number as a parameter to the command so it can be matched up with
the release.

state bit 0 is the current state of the key
state bit 1 is edge triggered on the up to down transition
state bit 2 is edge triggered on the down to up transition


Key_Event (int key, qboolean down, unsigned time);

  +mlook src time

===============================================================================
*/
class kbutton_t(object):

	def __init__(self):
		self.down = [0, 0]
		self.state = 0
		self.downtime = 0
		self.msec = 0


in_klook = kbutton_t()
in_left = kbutton_t()
in_right = kbutton_t()
in_forward = kbutton_t()
in_back = kbutton_t()
in_lookup = kbutton_t()
in_lookdown = kbutton_t()
in_moveleft = kbutton_t()
in_moveright = kbutton_t()
in_strafe = kbutton_t()
in_speed = kbutton_t()
in_use = kbutton_t()
in_attack = kbutton_t()
in_up = kbutton_t()
in_down = kbutton_t()

in_impulse = 0

cl_upspeed = None
cl_forwardspeed = None
cl_sidespeed = None
cl_yawspeed = None
cl_pitchspeed = None
cl_run = None
cl_anglespeedkey = None


def KeyDown(b):
	c = cmd.Cmd_Argv(1)
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
		common.Com_Printf("Three keys down for a button!\n")
		return

	if b.state & 1:
		return

	c = cmd.Cmd_Argv(2)
	b.downtime = int(c) if c else 0
	if not b.downtime:
		b.downtime = sys_linux.sys_frame_time - 100

	b.state |= 1 + 2


def KeyUp(b):
	c = cmd.Cmd_Argv(1)
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

	c = cmd.Cmd_Argv(2)
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
	c = cmd.Cmd_Argv(1)
	in_impulse = int(c) if c else 0


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


def CL_AdjustAngles():
	if in_speed.state & 1:
		speed = cl_main.cls.frametime * cl_anglespeedkey.value
	else:
		speed = cl_main.cls.frametime

	if not (in_strafe.state & 1):
		cl_main.cl.viewangles[q_shared.YAW] -= speed * cl_yawspeed.value * CL_KeyState(in_right)
		cl_main.cl.viewangles[q_shared.YAW] += speed * cl_yawspeed.value * CL_KeyState(in_left)
	if in_klook.state & 1:
		cl_main.cl.viewangles[q_shared.PITCH] -= speed * cl_pitchspeed.value * CL_KeyState(in_forward)
		cl_main.cl.viewangles[q_shared.PITCH] += speed * cl_pitchspeed.value * CL_KeyState(in_back)

	up = CL_KeyState(in_lookup)
	down = CL_KeyState(in_lookdown)

	cl_main.cl.viewangles[q_shared.PITCH] -= speed * cl_pitchspeed.value * up
	cl_main.cl.viewangles[q_shared.PITCH] += speed * cl_pitchspeed.value * down



kbutton_t	in_klook;
kbutton_t	in_left, in_right, in_forward, in_back;
kbutton_t	in_lookup, in_lookdown, in_moveleft, in_moveright;
kbutton_t	in_strafe, in_speed, in_use, in_attack;
kbutton_t	in_up, in_down;

int			in_impulse;


void KeyDown (kbutton_t *b)
{
	int		k;
	char	*c;
	
	c = Cmd_Argv(1);
	if (c[0])
		k = atoi(c);
	else
		k = -1;		// typed manually at the console for continuous down

	if (k == b->down[0] || k == b->down[1])
		return;		// repeating key
	
	if (!b->down[0])
		b->down[0] = k;
	else if (!b->down[1])
		b->down[1] = k;
	else
	{
		Com_Printf ("Three keys down for a button!\n");
		return;
	}
	
	if (b->state & 1)
		return;		// still down

	// save timestamp
	c = Cmd_Argv(2);
	b->downtime = atoi(c);
	if (!b->downtime)
		b->downtime = sys_frame_time - 100;

	b->state |= 1 + 2;	// down + impulse down
}

void KeyUp (kbutton_t *b)
{
	int		k;
	char	*c;
	unsigned	uptime;

	c = Cmd_Argv(1);
	if (c[0])
		k = atoi(c);
	else
	{ // typed manually at the console, assume for unsticking, so clear all
		b->down[0] = b->down[1] = 0;
		b->state = 4;	// impulse up
		return;
	}

	if (b->down[0] == k)
		b->down[0] = 0;
	else if (b->down[1] == k)
		b->down[1] = 0;
	else
		return;		// key up without coresponding down (menu pass through)
	if (b->down[0] || b->down[1])
		return;		// some other key is still holding it down

	if (!(b->state & 1))
		return;		// still up (this should not happen)

	// save timestamp
	c = Cmd_Argv(2);
	uptime = atoi(c);
	if (uptime)
		b->msec += uptime - b->downtime;
	else
		b->msec += 10;

	b->state &= ~1;		// now up
	b->state |= 4; 		// impulse up
}

void IN_KLookDown (void) {KeyDown(&in_klook);}
void IN_KLookUp (void) {KeyUp(&in_klook);}
void IN_UpDown(void) {KeyDown(&in_up);}
void IN_UpUp(void) {KeyUp(&in_up);}
void IN_DownDown(void) {KeyDown(&in_down);}
void IN_DownUp(void) {KeyUp(&in_down);}
void IN_LeftDown(void) {KeyDown(&in_left);}
void IN_LeftUp(void) {KeyUp(&in_left);}
void IN_RightDown(void) {KeyDown(&in_right);}
void IN_RightUp(void) {KeyUp(&in_right);}
void IN_ForwardDown(void) {KeyDown(&in_forward);}
void IN_ForwardUp(void) {KeyUp(&in_forward);}
void IN_BackDown(void) {KeyDown(&in_back);}
void IN_BackUp(void) {KeyUp(&in_back);}
void IN_LookupDown(void) {KeyDown(&in_lookup);}
void IN_LookupUp(void) {KeyUp(&in_lookup);}
void IN_LookdownDown(void) {KeyDown(&in_lookdown);}
void IN_LookdownUp(void) {KeyUp(&in_lookdown);}
void IN_MoveleftDown(void) {KeyDown(&in_moveleft);}
void IN_MoveleftUp(void) {KeyUp(&in_moveleft);}
void IN_MoverightDown(void) {KeyDown(&in_moveright);}
void IN_MoverightUp(void) {KeyUp(&in_moveright);}

void IN_SpeedDown(void) {KeyDown(&in_speed);}
void IN_SpeedUp(void) {KeyUp(&in_speed);}
void IN_StrafeDown(void) {KeyDown(&in_strafe);}
void IN_StrafeUp(void) {KeyUp(&in_strafe);}

void IN_AttackDown(void) {KeyDown(&in_attack);}
void IN_AttackUp(void) {KeyUp(&in_attack);}

void IN_UseDown (void) {KeyDown(&in_use);}
void IN_UseUp (void) {KeyUp(&in_use);}

void IN_Impulse (void) {in_impulse=atoi(Cmd_Argv(1));}
"""
"""
/*
===============
CL_KeyState

Returns the fraction of the frame that the key was down
===============
*/
float CL_KeyState (kbutton_t *key)
{
	float		val;
	int			msec;

	key->state &= 1;		// clear impulses

	msec = key->msec;
	key->msec = 0;

	if (key->state)
	{	// still down
		msec += sys_frame_time - key->downtime;
		key->downtime = sys_frame_time;
	}

#if 0
	if (msec)
	{
		Com_Printf ("%i ", msec);
	}
#endif

	val = (float)msec / frame_msec;
	if (val < 0)
		val = 0;
	if (val > 1)
		val = 1;

	return val;
}




//==========================================================================

cvar_t	*cl_upspeed;
cvar_t	*cl_forwardspeed;
cvar_t	*cl_sidespeed;

cvar_t	*cl_yawspeed;
cvar_t	*cl_pitchspeed;

cvar_t	*cl_run;

cvar_t	*cl_anglespeedkey;
"""
"""
/*
================
CL_AdjustAngles

Moves the local angle positions
================
*/
void CL_AdjustAngles (void)
{
	float	speed;
	float	up, down;
	
	if (in_speed.state & 1)
		speed = cl_main.cls.frametime * cl_anglespeedkey->value;
	else
		speed = cl_main.cls.frametime;

	if (!(in_strafe.state & 1))
	{
		cl_main.cl.viewangles[YAW] -= speed*cl_yawspeed->value*CL_KeyState (&in_right);
		cl_main.cl.viewangles[YAW] += speed*cl_yawspeed->value*CL_KeyState (&in_left);
	}
	if (in_klook.state & 1)
	{
		cl_main.cl.viewangles[PITCH] -= speed*cl_pitchspeed->value * CL_KeyState (&in_forward);
		cl_main.cl.viewangles[PITCH] += speed*cl_pitchspeed->value * CL_KeyState (&in_back);
	}
	
	up = CL_KeyState (&in_lookup);
	down = CL_KeyState(&in_lookdown);
	
	cl_main.cl.viewangles[PITCH] -= speed*cl_pitchspeed->value * up;
	cl_main.cl.viewangles[PITCH] += speed*cl_pitchspeed->value * down;
}
"""
"""
/*
================
CL_BaseMove

Send the intended movement message to the server
================
"""
class kbutton_t(object):

	def __init__(self):
		self.down = [0, 0]
		self.state = 0
		self.downtime = 0
		self.msec = 0


in_klook = kbutton_t()
in_left = kbutton_t()
in_right = kbutton_t()
in_forward = kbutton_t()
in_back = kbutton_t()
in_lookup = kbutton_t()
in_lookdown = kbutton_t()
in_moveleft = kbutton_t()
in_moveright = kbutton_t()
in_strafe = kbutton_t()
in_speed = kbutton_t()
in_use = kbutton_t()
in_attack = kbutton_t()
in_up = kbutton_t()
in_down = kbutton_t()

in_impulse = 0

cl_upspeed = None
cl_forwardspeed = None
cl_sidespeed = None
cl_yawspeed = None
cl_pitchspeed = None
cl_run = None
cl_anglespeedkey = None


def KeyDown(b):
	c = cmd.Cmd_Argv(1)
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
		common.Com_Printf("Three keys down for a button!\n")
		return

	if b.state & 1:
		return

	c = cmd.Cmd_Argv(2)
	b.downtime = int(c) if c else 0
	if not b.downtime:
		b.downtime = sys_linux.sys_frame_time - 100

	b.state |= 1 + 2


def KeyUp(b):
	c = cmd.Cmd_Argv(1)
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

	c = cmd.Cmd_Argv(2)
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
	c = cmd.Cmd_Argv(1)
	in_impulse = int(c) if c else 0


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


def CL_AdjustAngles():
	if in_speed.state & 1:
		speed = cl_main.cls.frametime * cl_anglespeedkey.value
	else:
		speed = cl_main.cls.frametime

	if not (in_strafe.state & 1):
		cl_main.cl.viewangles[q_shared.YAW] -= speed * cl_yawspeed.value * CL_KeyState(in_right)
		cl_main.cl.viewangles[q_shared.YAW] += speed * cl_yawspeed.value * CL_KeyState(in_left)
	if in_klook.state & 1:
		cl_main.cl.viewangles[q_shared.PITCH] -= speed * cl_pitchspeed.value * CL_KeyState(in_forward)
		cl_main.cl.viewangles[q_shared.PITCH] += speed * cl_pitchspeed.value * CL_KeyState(in_back)

	up = CL_KeyState(in_lookup)
	down = CL_KeyState(in_lookdown)

	cl_main.cl.viewangles[q_shared.PITCH] -= speed * cl_pitchspeed.value * up
	cl_main.cl.viewangles[q_shared.PITCH] += speed * cl_pitchspeed.value * down

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
	pitch = q_shared.SHORT2ANGLE(cl_main.cl.frame.playerstate.pmove.delta_angles[q_shared.PITCH])
	if pitch > 180:
		pitch -= 360

	if cl_main.cl.viewangles[q_shared.PITCH] + pitch < -360:
		cl_main.cl.viewangles[q_shared.PITCH] += 360
	if cl_main.cl.viewangles[q_shared.PITCH] + pitch > 360:
		cl_main.cl.viewangles[q_shared.PITCH] -= 360

	if cl_main.cl.viewangles[q_shared.PITCH] + pitch > 89:
		cl_main.cl.viewangles[q_shared.PITCH] = 89 - pitch
	if cl_main.cl.viewangles[q_shared.PITCH] + pitch < -89:
		cl_main.cl.viewangles[q_shared.PITCH] = -89 - pitch
def CL_FinishMove (cmd): #usercmd_t *

	global in_impulse

	if in_attack.state & 3:
		cmd.buttons |= q_shared.BUTTON_ATTACK
	in_attack.state &= ~2

	if in_use.state & 3:
		cmd.buttons |= q_shared.BUTTON_USE
	in_use.state &= ~2

	if keys.anykeydown and cl_main.cls.key_dest == client.keydest_t.key_game:
		cmd.buttons |= q_shared.BUTTON_ANY

	ms = cl_main.cls.frametime * 1000
	if ms > 250:
		ms = 100
	cmd.msec = int(ms)

	CL_ClampPitch ()
	for i in range(3):
		cmd.angles[i] = ((q_shared.ANGLE2SHORT(cl_main.cl.viewangles[i]) + 0x8000) & 0xffff) - 0x8000 # short cmd->angles[i]

	cmd.impulse = in_impulse
	in_impulse = 0

	cmd.lightlevel = int(cl_main.cl_lightlevel.value) if cl_main.cl_lightlevel else 0

def CL_CreateCmd ():

	global old_sys_frame_time, frame_msec

	cmd = q_shared.usercmd_t()

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
	cl_main.cl.viewangles[q_shared.PITCH] = -q_shared.SHORT2ANGLE(
		cl_main.cl.frame.playerstate.pmove.delta_angles[q_shared.PITCH]
	)

def CL_InitInput ():

	global cl_nodelta
	global cl_upspeed, cl_forwardspeed, cl_sidespeed
	global cl_yawspeed, cl_pitchspeed, cl_run, cl_anglespeedkey

	cmd.Cmd_AddCommand ("centerview", IN_CenterView)

	cmd.Cmd_AddCommand ("+moveup", IN_UpDown)
	cmd.Cmd_AddCommand ("-moveup", IN_UpUp)
	cmd.Cmd_AddCommand ("+movedown", IN_DownDown)
	cmd.Cmd_AddCommand ("-movedown", IN_DownUp)
	cmd.Cmd_AddCommand ("+left", IN_LeftDown)
	cmd.Cmd_AddCommand ("-left", IN_LeftUp)
	cmd.Cmd_AddCommand ("+right", IN_RightDown)
	cmd.Cmd_AddCommand ("-right", IN_RightUp)
	cmd.Cmd_AddCommand ("+forward", IN_ForwardDown)
	cmd.Cmd_AddCommand ("-forward", IN_ForwardUp)
	cmd.Cmd_AddCommand ("+back", IN_BackDown)
	cmd.Cmd_AddCommand ("-back", IN_BackUp)
	cmd.Cmd_AddCommand ("+lookup", IN_LookupDown)
	cmd.Cmd_AddCommand ("-lookup", IN_LookupUp)
	cmd.Cmd_AddCommand ("+lookdown", IN_LookdownDown)
	cmd.Cmd_AddCommand ("-lookdown", IN_LookdownUp)
	cmd.Cmd_AddCommand ("+strafe", IN_StrafeDown)
	cmd.Cmd_AddCommand ("-strafe", IN_StrafeUp)
	cmd.Cmd_AddCommand ("+moveleft", IN_MoveleftDown)
	cmd.Cmd_AddCommand ("-moveleft", IN_MoveleftUp)
	cmd.Cmd_AddCommand ("+moveright", IN_MoverightDown)
	cmd.Cmd_AddCommand ("-moveright", IN_MoverightUp)
	cmd.Cmd_AddCommand ("+speed", IN_SpeedDown)
	cmd.Cmd_AddCommand ("-speed", IN_SpeedUp)
	cmd.Cmd_AddCommand ("+attack", IN_AttackDown)
	cmd.Cmd_AddCommand ("-attack", IN_AttackUp)
	cmd.Cmd_AddCommand ("+use", IN_UseDown)
	cmd.Cmd_AddCommand ("-use", IN_UseUp)
	cmd.Cmd_AddCommand ("impulse", IN_Impulse)
	cmd.Cmd_AddCommand ("+klook", IN_KLookDown)
	cmd.Cmd_AddCommand ("-klook", IN_KLookUp)

	cl_nodelta = cvar.Cvar_Get ("cl_nodelta", "0", 0)
	cl_upspeed = cvar.Cvar_Get ("cl_upspeed", "200", 0)
	cl_forwardspeed = cvar.Cvar_Get ("cl_forwardspeed", "200", 0)
	cl_sidespeed = cvar.Cvar_Get ("cl_sidespeed", "200", 0)
	cl_yawspeed = cvar.Cvar_Get ("cl_yawspeed", "140", 0)
	cl_pitchspeed = cvar.Cvar_Get ("cl_pitchspeed", "150", 0)
	cl_run = cvar.Cvar_Get ("cl_run", "0", 0)
	cl_anglespeedkey = cvar.Cvar_Get ("cl_anglespeedkey", "1.5", 0)





"""
=================
CL_SendCmd
=================
"""
def CL_SendCmd ():

	buf = qcommon.sizebuf_t()
	#byte		data[128];
	#int			i;
	#usercmd_t	*cmd, *oldcmd;
	nullcmd = q_shared.usercmd_t()
	#int			checksumIndex;

	# build a command even if not connected

	# save this command off for prediction
	i = cl_main.cls.netchan.outgoing_sequence & (client.CMD_BACKUP-1)
	#cmd = &cl.cmds[i];
	cl_main.cl.cmd_time[i] = cl_main.cls.realtime	# for netgraph ping calculation

	cmd = CL_CreateCmd () # a new usercmd_t each call, so storing it is the struct copy
	cl_main.cl.cmds[i] = cmd # *cmd = CL_CreateCmd ();

	cl_main.cl.cmd = cmd # cl.cmd = *cmd;, cl.cmds[i] is not changed after this

	if cl_main.cls.state == client.connstate_t.ca_disconnected or cl_main.cls.state == client.connstate_t.ca_connecting:
		return

	if cl_main.cls.state == client.connstate_t.ca_connected:
	
		if cl_main.cls.netchan.message.cursize or q_shlinux.curtime - cl_main.cls.netchan.last_sent > 1000:
			net_chan.Netchan_Transmit (cl_main.cls.netchan, b"")
		return
	
	# send a userinfo update if needed
	if cvar.userinfo_modified:
	
		cl_main.CL_FixUpGender()
		cvar.userinfo_modified = False
		common.MSG_WriteByte (cl_main.cls.netchan.message, qcommon.clc_ops_e.clc_userinfo.value)
		common.MSG_WriteString (cl_main.cls.netchan.message, cvar.Cvar_Userinfo().encode('ascii') )
	
	common.SZ_Init (buf, 128)

	if cmd.buttons and cl_main.cl.cinematictime > 0 and not cl_main.cl.attractloop \
		and cl_main.cls.realtime - cl_main.cl.cinematictime > 1000:
		# skip the rest of the cinematic
		cl_cin.SCR_FinishCinematic ()
	
	# begin a client move command
	common.MSG_WriteByte (buf, qcommon.clc_ops_e.clc_move.value.to_bytes(1, 'big'))

	# save the position for a checksum byte
	checksumIndex = len(buf.data)
	common.MSG_WriteByte (buf, b'\x00')
	
	# let the server know what the last frame we
	# got was, so the next message can be delta compressed

	if cl_nodelta.value or not cl_main.cl.frame.valid or cl_main.cls.demowaiting:
		common.MSG_WriteSLong (buf, -1)	# no compression
	else:
		common.MSG_WriteLong (buf, cl_main.cl.frame.serverframe)

	# send this and the previous cmds in the message, so
	# if the last packet was dropped, it can be recovered
	
	i = (cl_main.cls.netchan.outgoing_sequence-2) & (client.CMD_BACKUP-1)
	cmd = cl_main.cl.cmds[i]
	common.MSG_WriteDeltaUsercmd (buf, nullcmd, cmd)
	oldcmd = cmd

	i = (cl_main.cls.netchan.outgoing_sequence-1) & (client.CMD_BACKUP-1)
	cmd = cl_main.cl.cmds[i]
	common.MSG_WriteDeltaUsercmd (buf, oldcmd, cmd)
	oldcmd = cmd

	i = (cl_main.cls.netchan.outgoing_sequence) & (client.CMD_BACKUP-1)
	cmd = cl_main.cl.cmds[i]
	common.MSG_WriteDeltaUsercmd (buf, oldcmd, cmd)

	# calculate a checksum over the move commands
	buf.data[checksumIndex] = common.COM_BlockSequenceCRCByte(
		buf, checksumIndex + 1, len(buf.data) - checksumIndex - 1,
		cl_main.cls.netchan.outgoing_sequence)[0]

	#
	# deliver the message
	#
	net_chan.Netchan_Transmit (cl_main.cls.netchan, buf.data)


