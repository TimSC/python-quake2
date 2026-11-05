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

// cl_newfx.c -- MORE entity effects parsing and management

#include "client.h"

extern cparticle_t	*active_particles, *free_particles;
extern cparticle_t	particles[MAX_PARTICLES];
extern int			cl_numparticles;
extern cvar_t		*vid_ref;

extern void MakeNormalVectors (vec3_t forward, vec3_t right, vec3_t up);
"""
from __future__ import annotations

import math
import random
import numpy as np
from game import q_shared
from qcommon import common
from client import cl_main, cl_fx, cl_ents


"""
======
vectoangles2 - this is duplicated in the game DLL, but I need it here.
======
"""
def vectoangles2 (value1, angles): #vec3_t, vec3_t

	#float	forward;
	#float	yaw, pitch;
	
	if value1[1] == 0 and value1[0] == 0:
	
		yaw = 0
		if value1[2] > 0:
			pitch = 90
		else:
			pitch = 270
	
	else:
	
	# PMM - fixed to correct for pitch of 0
		if value1[0]:
			yaw = (math.atan2(value1[1], value1[0]) * 180 / math.pi)
		elif value1[1] > 0:
			yaw = 90
		else:
			yaw = 270

		if yaw < 0:
			yaw += 360

		forward = math.sqrt (value1[0]*value1[0] + value1[1]*value1[1])
		pitch = (math.atan2(value1[2], forward) * 180 / math.pi)
		if pitch < 0:
			pitch += 360
	
	angles[q_shared.PITCH] = -pitch
	angles[q_shared.YAW] = yaw
	angles[q_shared.ROLL] = 0

#=============
#=============
def CL_Flashlight (ent, pos): #int, vec3_t

	#cdlight_t	*dl;

	dl = cl_fx.CL_AllocDlight (ent)
	q_shared.VectorCopy (pos,  dl.origin)
	dl.radius = 400
	dl.minlight = 250
	dl.die = cl_main.cl.time + 100
	dl.color[0] = 1
	dl.color[1] = 1
	dl.color[2] = 1

"""
======
CL_ColorFlash - flash of light
======
"""
def CL_ColorFlash (pos, ent, intensity, r, g, b): #vec3_t, int, int, float, float, float

	#cdlight_t	*dl;

	if (cl_ents.vidref_val == q_shared.VIDREF_SOFT) and ((r < 0) or (g<0) or (b<0)):
	
		intensity = -intensity
		r = -r
		g = -g
		b = -b
	
	dl = cl_fx.CL_AllocDlight (ent)
	q_shared.VectorCopy (pos,  dl.origin)
	dl.radius = intensity
	dl.minlight = 250
	dl.die = cl_main.cl.time + 100
	dl.color[0] = r
	dl.color[1] = g
	dl.color[2] = b


"""
======
CL_DebugTrail
======
"""
def CL_DebugTrail (start, end): #vec3_t, vec3_t

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
//	int			j;
	cparticle_t	*p;
	float		dec;
	vec3_t		right, up;
//	int			i;
//	float		d, c, s;
//	vec3_t		dir;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	cl_fx.MakeNormalVectors (vec, right, up)

#	VectorScale(vec, RT2_SKIP, vec);

#	dec = 1.0;
#	dec = 0.75;
	dec = 3
	q_shared.VectorScale (vec, dec, vec)
	q_shared.VectorCopy (start, move)

	while length > 0:
	
		length -= dec

		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		q_shared.VectorClear (p.accel)
		q_shared.VectorClear (p.vel)
		p.alpha = 1.0
		p.alphavel = -0.1
#		p->alphavel = 0;
		p.color = 0x74 + (random.getrandbits(15)&7)
		q_shared.VectorCopy (move, p.org)
		"""
		for (j=0 ; j<3 ; j++)
		{
			p->org[j] = move[j] + crand()*2;
			p->vel[j] = crand()*3;
			p->accel[j] = 0;
		}
		"""
		q_shared.VectorAdd (move, vec, move)
	

"""
===============
CL_SmokeTrail
===============
"""
def CL_SmokeTrail (start, end, colorStart, colorRun, spacing): #vec3_t, vec3_t, int, int, int

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	q_shared.VectorScale (vec, spacing, vec)

	# FIXME: this is a really silly way to have a loop
	while length > 0:
	
		length -= spacing

		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (1+common.frand()*0.5)
		p.color = colorStart + (random.getrandbits(15) % colorRun)
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()*3
			p.accel[j] = 0
		
		p.vel[2] = 20 + common.crand()*5

		q_shared.VectorAdd (move, vec, move)
	

def CL_ForceWall (start, end, color): #vec3_t, vec3_t, int

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	q_shared.VectorScale (vec, 4, vec)

	# FIXME: this is a really silly way to have a loop
	while length > 0:
	
		length -= 4

		if not cl_fx.free_particles:
			return
		
		if common.frand() > 0.3:
		
			p = cl_fx._alloc_particle()
			if p is None:
				return
			cl_fx.active_particles.append(p)
			q_shared.VectorClear (p.accel)
			
			p.time = cl_main.cl.time

			p.alpha = 1.0
			p.alphavel =  -1.0 / (3.0+common.frand()*0.5)
			p.color = color
			for j in range(3):
			
				p.org[j] = move[j] + common.crand()*3
				p.accel[j] = 0
			
			p.vel[0] = 0
			p.vel[1] = 0
			p.vel[2] = -40 - (common.crand()*10)
		
		q_shared.VectorAdd (move, vec, move)
	

def CL_FlameEffects (ent, origin): #centity_t *, vec3_t

	#int			n, count;
	#int			j;
	#cparticle_t	*p;

	count = random.getrandbits(15) & 0xF

	for n in range(count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		
		q_shared.VectorClear (p.accel)
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (1+common.frand()*0.2)
		p.color = 226 + (random.getrandbits(15) % 4)
		for j in range(3):
		
			p.org[j] = origin[j] + common.crand()*5
			p.vel[j] = common.crand()*5
		
		p.vel[2] = common.crand() * -10
		p.accel[2] = -cl_fx.PARTICLE_GRAVITY
	
	count = random.getrandbits(15) & 0x7

	for n in range(count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (1+common.frand()*0.5)
		p.color = 0 + (random.getrandbits(15) % 4)
		for j in range(3):
		
			p.org[j] = origin[j] + common.crand()*3
		
		p.vel[2] = 20 + common.crand()*5
	


"""
===============
CL_GenericParticleEffect
===============
"""
def CL_GenericParticleEffect (org, dir, color, count, numcolors, dirspread, alphavel): #vec3_t, vec3_t, int, int, int, int, float

	#int			i, j;
	#cparticle_t	*p;
	#float		d;

	for i in range(count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		if numcolors > 1:
			p.color = color + (random.getrandbits(15) & numcolors)
		else:
			p.color = color

		d = random.getrandbits(15) & dirspread
		for j in range(3):
		
			p.org[j] = org[j] + ((random.getrandbits(15)&7)-4) + d*dir[j]
			p.vel[j] = common.crand()*20
		
		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -cl_fx.PARTICLE_GRAVITY
#		VectorCopy (accel, p->accel);
		p.alpha = 1.0

		p.alphavel = -1.0 / (0.5 + common.frand()*alphavel)
#		p->alphavel = alphavel;
	

"""
===============
CL_BubbleTrail2 (lets you control the # of bubbles by setting the distance between the spawns)

===============
"""
def CL_BubbleTrail2 (start, end, dist): #vec3_t, vec3_t, int

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			i, j;
	cparticle_t	*p;
	float		dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = dist
	q_shared.VectorScale (vec, dec, vec)

	i = 0
	while i < length:
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		q_shared.VectorClear (p.accel)
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (1+common.frand()*0.1)
		p.color = 4 + (random.getrandbits(15)&7)
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()*2
			p.vel[j] = common.crand()*10
		
		p.org[2] -= 4
#		p->vel[2] += 6;
		p.vel[2] += 20

		q_shared.VectorAdd (move, vec, move)
		i += dec
	

#define CORKSCREW		1
#define DOUBLE_SCREW	1
RINGS = 1
#define	SPRAY		1

"""
#ifdef CORKSCREW
void CL_Heatbeam (vec3_t start, vec3_t end)
{
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j,k;
	cparticle_t	*p;
	vec3_t		right, up;
	int			i;
	float		d, c, s;
	vec3_t		dir;
	float		ltime;
	float		step = 5.0;

	VectorCopy (start, move);
	VectorSubtract (end, start, vec);
	len = VectorNormalize (vec);

//	MakeNormalVectors (vec, right, up);
	VectorCopy (cl.v_right, right);
	VectorCopy (cl.v_up, up);
	VectorMA (move, -1, right, move);
	VectorMA (move, -1, up, move);

	VectorScale (vec, step, vec);
	ltime = (float) cl.time/1000.0;

//	for (i=0 ; i<len ; i++)
	for (i=0 ; i<len ; i+=step)
	{
		d = i * 0.1 - fmod(ltime,16.0)*M_PI;
		c = cos(d)/1.75;
		s = sin(d)/1.75;
#ifdef DOUBLE_SCREW		
		for (k=-1; k<2; k+=2)
		{
#else
		k=1;
#endif
			if (!free_particles)
				return;

			p = free_particles;
			free_particles = p->next;
			p->next = active_particles;
			active_particles = p;
			
			p->time = cl.time;
			VectorClear (p->accel);

			p->alpha = 0.5;
	//		p->alphavel = -1.0 / (1+frand()*0.2);
			// only last one frame!
			p->alphavel = INSTANT_PARTICLE;
	//		p->color = 0x74 + (rand()&7);
//			p->color = 223 - (rand()&7);
			p->color = 223;
//			p->color = 240;

			// trim it so it looks like it's starting at the origin
			if (i < 10)
			{
				VectorScale (right, c*(i/10.0)*k, dir);
				VectorMA (dir, s*(i/10.0)*k, up, dir);
			}
			else
			{
				VectorScale (right, c*k, dir);
				VectorMA (dir, s*k, up, dir);
			}
			
			for (j=0 ; j<3 ; j++)
			{
				p->org[j] = move[j] + dir[j]*3;
	//			p->vel[j] = dir[j]*6;
				p->vel[j] = 0;
			}
#ifdef DOUBLE_SCREW
		}
#endif
		VectorAdd (move, vec, move);
	}
}
#endif
"""
#ifdef RINGS
#void CL_Heatbeam (vec3_t start, vec3_t end)
def CL_Heatbeam (start, forward): #vec3_t, vec3_t

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	vec3_t		right, up;
	int			i;
	float		c, s;
	vec3_t		dir;
	float		ltime;
	float		step = 32.0, rstep;
	float		start_pt;
	float		rot;
	float		variance;
	vec3_t		end;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)
	end = np.zeros((3,), dtype=np.float32)
	step = 32.0

	q_shared.VectorMA (start, 4096, forward, end)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	# FIXME - pmm - these might end up using old values?
#	MakeNormalVectors (vec, right, up);
	q_shared.VectorCopy (cl_main.cl.v_right, right)
	q_shared.VectorCopy (cl_main.cl.v_up, up)
	if cl_ents.vidref_val == q_shared.VIDREF_GL:
		# GL mode
		q_shared.VectorMA (move, -0.5, right, move)
		q_shared.VectorMA (move, -0.5, up, move)
	
	# otherwise assume SOFT

	ltime = float(cl_main.cl.time)/1000.0
	start_pt = math.fmod(ltime*96.0,step)
	q_shared.VectorMA (move, start_pt, vec, move)

	q_shared.VectorScale (vec, step, vec)

#	Com_Printf ("%f\n", ltime);
	rstep = math.pi/10.0
	i = int(start_pt) # for (i=start_pt ; i<len ; i+=step), i is an int
	while i < length:
	
		if i>step*5: # don't bother after the 5th ring
			break

		rot = 0
		while rot < math.pi*2:
		
			p = cl_fx._alloc_particle()
			if p is None:
				return
			cl_fx.active_particles.append(p)
			
			p.time = cl_main.cl.time
			q_shared.VectorClear (p.accel)
#			rot+= fmod(ltime, 12.0)*M_PI;
#			c = cos(rot)/2.0;
#			s = sin(rot)/2.0;
#			variance = 0.4 + ((float)rand()/(float)RAND_MAX) *0.2;
			variance = 0.5
			c = math.cos(rot)*variance
			s = math.sin(rot)*variance
			
			# trim it so it looks like it's starting at the origin
			if i < 10:
			
				q_shared.VectorScale (right, c*(i/10.0), dir)
				q_shared.VectorMA (dir, s*(i/10.0), up, dir)
			
			else:
			
				q_shared.VectorScale (right, c, dir)
				q_shared.VectorMA (dir, s, up, dir)
			
			p.alpha = 0.5
	#		p->alphavel = -1.0 / (1+frand()*0.2);
			p.alphavel = -1000.0
	#		p->color = 0x74 + (rand()&7);
			p.color = 223 - (random.getrandbits(15)&7)
			for j in range(3):
			
				p.org[j] = move[j] + dir[j]*3
	#			p->vel[j] = dir[j]*6;
				p.vel[j] = 0
			
			rot += rstep
		
		q_shared.VectorAdd (move, vec, move)
		i = int(i + step)
	
#endif
"""
#ifdef SPRAY
void CL_Heatbeam (vec3_t start, vec3_t end)
{
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	vec3_t		forward, right, up;
	int			i;
	float		d, c, s;
	vec3_t		dir;
	float		ltime;
	float		step = 32.0, rstep;
	float		start_pt;
	float		rot;

	VectorCopy (start, move);
	VectorSubtract (end, start, vec);
	len = VectorNormalize (vec);

//	MakeNormalVectors (vec, right, up);
	VectorCopy (cl.v_forward, forward);
	VectorCopy (cl.v_right, right);
	VectorCopy (cl.v_up, up);
	VectorMA (move, -0.5, right, move);
	VectorMA (move, -0.5, up, move);

	for (i=0; i<8; i++)
	{
		if (!free_particles)
			return;

		p = free_particles;
		free_particles = p->next;
		p->next = active_particles;
		active_particles = p;
		
		p->time = cl.time;
		VectorClear (p->accel);
		
		d = crand()*M_PI;
		c = cos(d)*30;
		s = sin(d)*30;

		p->alpha = 1.0;
		p->alphavel = -5.0 / (1+frand());
		p->color = 223 - (rand()&7);

		for (j=0 ; j<3 ; j++)
		{
			p->org[j] = move[j];
		}
		VectorScale (vec, 450, p->vel);
		VectorMA (p->vel, c, right, p->vel);
		VectorMA (p->vel, s, up, p->vel);
	}
/*

	ltime = (float) cl.time/1000.0;
	start_pt = fmod(ltime*16.0,step);
	VectorMA (move, start_pt, vec, move);

	VectorScale (vec, step, vec);

//	Com_Printf ("%f\n", ltime);
	rstep = M_PI/12.0;
	for (i=start_pt ; i<len ; i+=step)
	{
		if (i>step*5) // don't bother after the 5th ring
			break;

		for (rot = 0; rot < M_PI*2; rot += rstep)
		{
			if (!free_particles)
				return;

			p = free_particles;
			free_particles = p->next;
			p->next = active_particles;
			active_particles = p;
			
			p->time = cl.time;
			VectorClear (p->accel);
//			rot+= fmod(ltime, 12.0)*M_PI;
//			c = cos(rot)/2.0;
//			s = sin(rot)/2.0;
			c = cos(rot)/1.5;
			s = sin(rot)/1.5;
			
			// trim it so it looks like it's starting at the origin
			if (i < 10)
			{
				VectorScale (right, c*(i/10.0), dir);
				VectorMA (dir, s*(i/10.0), up, dir);
			}
			else
			{
				VectorScale (right, c, dir);
				VectorMA (dir, s, up, dir);
			}
		
			p->alpha = 0.5;
	//		p->alphavel = -1.0 / (1+frand()*0.2);
			p->alphavel = -1000.0;
	//		p->color = 0x74 + (rand()&7);
			p->color = 223 - (rand()&7);
			for (j=0 ; j<3 ; j++)
			{
				p->org[j] = move[j] + dir[j]*3;
	//			p->vel[j] = dir[j]*6;
				p->vel[j] = 0;
			}
		}
		VectorAdd (move, vec, move);
	}
*/
}
#endif

/*
===============
CL_ParticleSteamEffect

Puffs with velocity along direction, with some randomness thrown in
===============
*/
"""
def CL_ParticleSteamEffect (org, dir, color, count, magnitude): #vec3_t, vec3_t, int, int, int

	"""
	int			i, j;
	cparticle_t	*p;
	float		d;
	vec3_t		r, u;
	"""
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)

#	vectoangles2 (dir, angle_dir);
#	AngleVectors (angle_dir, f, r, u);

	cl_fx.MakeNormalVectors (dir, r, u)

	for i in range(count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = color + (random.getrandbits(15)&7)

		for j in range(3):
		
			p.org[j] = org[j] + magnitude*0.1*common.crand()
#			p->vel[j] = dir[j]*magnitude;
		
		q_shared.VectorScale (dir, magnitude, p.vel)
		d = common.crand()*magnitude/3
		q_shared.VectorMA (p.vel, d, r, p.vel)
		d = common.crand()*magnitude/3
		q_shared.VectorMA (p.vel, d, u, p.vel)

		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -cl_fx.PARTICLE_GRAVITY/2
		p.alpha = 1.0

		p.alphavel = -1.0 / (0.5 + common.frand()*0.3)
	

def CL_ParticleSteamEffect2 (self): #cl_sustain_t *
#vec3_t org, vec3_t dir, int color, int count, int magnitude)

	"""
	int			i, j;
	cparticle_t	*p;
	float		d;
	vec3_t		r, u;
	vec3_t		dir;
	"""
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)
	dir = np.zeros((3,), dtype=np.float32)

#	vectoangles2 (dir, angle_dir);
#	AngleVectors (angle_dir, f, r, u);

	q_shared.VectorCopy (self.dir, dir)
	cl_fx.MakeNormalVectors (dir, r, u)

	for i in range(self.count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = self.color + (random.getrandbits(15)&7)

		for j in range(3):
		
			p.org[j] = self.org[j] + self.magnitude*0.1*common.crand()
#			p->vel[j] = dir[j]*magnitude;
		
		q_shared.VectorScale (dir, self.magnitude, p.vel)
		d = common.crand()*self.magnitude/3
		q_shared.VectorMA (p.vel, d, r, p.vel)
		d = common.crand()*self.magnitude/3
		q_shared.VectorMA (p.vel, d, u, p.vel)

		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -cl_fx.PARTICLE_GRAVITY/2
		p.alpha = 1.0

		p.alphavel = -1.0 / (0.5 + common.frand()*0.3)
	
	self.nextthink += self.thinkinterval

"""
===============
CL_TrackerTrail
===============
"""
def CL_TrackerTrail (start, end, particleColor): #vec3_t, vec3_t, int

	"""
	vec3_t		move;
	vec3_t		vec;
	vec3_t		forward,right,up,angle_dir;
	float		len;
	int			j;
	cparticle_t	*p;
	int			dec;
	float		dist;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)
	forward = np.zeros((3,), dtype=np.float32)
	right = np.zeros((3,), dtype=np.float32)
	up = np.zeros((3,), dtype=np.float32)
	angle_dir = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	q_shared.VectorCopy(vec, forward)
	vectoangles2 (forward, angle_dir)
	q_shared.AngleVectors (angle_dir, forward, right, up)

	dec = 3
	q_shared.VectorScale (vec, 3, vec)

	# FIXME: this is a really silly way to have a loop
	while length > 0:
	
		length -= dec

		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -2.0
		p.color = particleColor
		dist = q_shared.DotProduct(move, forward)
		q_shared.VectorMA(move, 8 * math.cos(dist), up, p.org)
		for j in range(3):
		
#			p->org[j] = move[j] + crand();
			p.vel[j] = 0
			p.accel[j] = 0
		
		p.vel[2] = 5

		q_shared.VectorAdd (move, vec, move)
	

def CL_Tracker_Shell(origin): #vec3_t

	#vec3_t			dir;
	#int				i;
	#cparticle_t		*p;
	dir = np.zeros((3,), dtype=np.float32)

	for i in range(300):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = cl_fx.INSTANT_PARTICLE
		p.color = 0

		dir[0] = common.crand()
		dir[1] = common.crand()
		dir[2] = common.crand()
		q_shared.VectorNormalize(dir)
	
		q_shared.VectorMA(origin, 40, dir, p.org)
	

def CL_MonsterPlasma_Shell(origin): #vec3_t

	#vec3_t			dir;
	#int				i;
	#cparticle_t		*p;
	dir = np.zeros((3,), dtype=np.float32)

	for i in range(40):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = cl_fx.INSTANT_PARTICLE
		p.color = 0xe0

		dir[0] = common.crand()
		dir[1] = common.crand()
		dir[2] = common.crand()
		q_shared.VectorNormalize(dir)
	
		q_shared.VectorMA(origin, 10, dir, p.org)
#		VectorMA(origin, 10*(((rand () & 0x7fff) / ((float)0x7fff))), dir, p->org);
	

widowbeamout_colortable = [2*8,13*8,21*8,18*8] #static int colortable[4]

def CL_Widowbeamout (self): #cl_sustain_t *

	#vec3_t			dir;
	#int				i;
	#cparticle_t		*p;
	#float			ratio;
	dir = np.zeros((3,), dtype=np.float32)

	ratio = 1.0 - ((float(self.endtime) - float(cl_main.cl.time))/2100.0)

	for i in range(300):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = cl_fx.INSTANT_PARTICLE
		p.color = widowbeamout_colortable[random.getrandbits(15)&3]

		dir[0] = common.crand()
		dir[1] = common.crand()
		dir[2] = common.crand()
		q_shared.VectorNormalize(dir)
	
		q_shared.VectorMA(self.org, (45.0 * ratio), dir, p.org)
#		VectorMA(origin, 10*(((rand () & 0x7fff) / ((float)0x7fff))), dir, p->org);
	

nukeblast_colortable = [110, 112, 114, 116] #static int colortable[4]

def CL_Nukeblast (self): #cl_sustain_t *

	#vec3_t			dir;
	#int				i;
	#cparticle_t		*p;
	#float			ratio;
	dir = np.zeros((3,), dtype=np.float32)

	ratio = 1.0 - ((float(self.endtime) - float(cl_main.cl.time))/1000.0)

	for i in range(700):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = cl_fx.INSTANT_PARTICLE
		p.color = nukeblast_colortable[random.getrandbits(15)&3]

		dir[0] = common.crand()
		dir[1] = common.crand()
		dir[2] = common.crand()
		q_shared.VectorNormalize(dir)
	
		q_shared.VectorMA(self.org, (200.0 * ratio), dir, p.org)
#		VectorMA(origin, 10*(((rand () & 0x7fff) / ((float)0x7fff))), dir, p->org);
	

widowsplash_colortable = [2*8,13*8,21*8,18*8] #static int colortable[4]

def CL_WidowSplash (org): #vec3_t

	#int			i;
	#cparticle_t	*p;
	#vec3_t		dir;
	dir = np.zeros((3,), dtype=np.float32)

	for i in range(256):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = widowsplash_colortable[random.getrandbits(15)&3]

		dir[0] = common.crand()
		dir[1] = common.crand()
		dir[2] = common.crand()
		q_shared.VectorNormalize(dir)
		q_shared.VectorMA(org, 45.0, dir, p.org)
		q_shared.VectorMA(q_shared.vec3_origin, 40.0, dir, p.vel)

		p.accel[0] = p.accel[1] = 0
		p.alpha = 1.0

		p.alphavel = -0.8 / (0.5 + common.frand()*0.3)
	


def CL_Tracker_Explode(origin): #vec3_t

	#vec3_t			dir, backdir;
	#int				i;
	#cparticle_t		*p;
	dir = np.zeros((3,), dtype=np.float32)
	backdir = np.zeros((3,), dtype=np.float32)

	for i in range(300):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0
		p.color = 0

		dir[0] = common.crand()
		dir[1] = common.crand()
		dir[2] = common.crand()
		q_shared.VectorNormalize(dir)
		q_shared.VectorScale(dir, -1, backdir)
	
		q_shared.VectorMA(origin, 64, dir, p.org)
		q_shared.VectorScale(backdir, 64, p.vel)
	

"""
===============
CL_TagTrail

===============
"""
def CL_TagTrail (start, end, color): #vec3_t, vec3_t, float

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	int			dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 5
	q_shared.VectorScale (vec, 5, vec)

	while length >= 0:
	
		length -= dec

		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (0.8+common.frand()*0.2)
		p.color = color
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()*16
			p.vel[j] = common.crand()*5
			p.accel[j] = 0
		
		q_shared.VectorAdd (move, vec, move)
	

"""
===============
CL_ColorExplosionParticles
===============
"""
def CL_ColorExplosionParticles (org, color, run): #vec3_t, int, int

	#int			i, j;
	#cparticle_t	*p;

	for i in range(128):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = color + (random.getrandbits(15) % run)

		for j in range(3):
		
			p.org[j] = org[j] + ((random.getrandbits(15)%32)-16)
			p.vel[j] = (random.getrandbits(15)%256)-128
		
		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -cl_fx.PARTICLE_GRAVITY
		p.alpha = 1.0

		p.alphavel = -0.4 / (0.6 + common.frand()*0.2)
	

"""
===============
CL_ParticleSmokeEffect - like the steam effect, but unaffected by gravity
===============
"""
def CL_ParticleSmokeEffect (org, dir, color, count, magnitude): #vec3_t, vec3_t, int, int, int

	"""
	int			i, j;
	cparticle_t	*p;
	float		d;
	vec3_t		r, u;
	"""
	r = np.zeros((3,), dtype=np.float32)
	u = np.zeros((3,), dtype=np.float32)

	cl_fx.MakeNormalVectors (dir, r, u)

	for i in range(count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = color + (random.getrandbits(15)&7)

		for j in range(3):
		
			p.org[j] = org[j] + magnitude*0.1*common.crand()
#			p->vel[j] = dir[j]*magnitude;
		
		q_shared.VectorScale (dir, magnitude, p.vel)
		d = common.crand()*magnitude/3
		q_shared.VectorMA (p.vel, d, r, p.vel)
		d = common.crand()*magnitude/3
		q_shared.VectorMA (p.vel, d, u, p.vel)

		p.accel[0] = p.accel[1] = p.accel[2] = 0
		p.alpha = 1.0

		p.alphavel = -1.0 / (0.5 + common.frand()*0.3)
	

"""
===============
CL_BlasterParticles2

Wall impact puffs (Green)
===============
"""
def CL_BlasterParticles2 (org, dir, color): #vec3_t, vec3_t, unsigned int

	#int			i, j;
	#cparticle_t	*p;
	#float		d;
	#int			count;

	count = 40
	for i in range(count):
	
		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)

		p.time = cl_main.cl.time
		p.color = color + (random.getrandbits(15)&7)

		d = random.getrandbits(15)&15
		for j in range(3):
		
			p.org[j] = org[j] + ((random.getrandbits(15)&7)-4) + d*dir[j]
			p.vel[j] = dir[j] * 30 + common.crand()*40
		
		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -cl_fx.PARTICLE_GRAVITY
		p.alpha = 1.0

		p.alphavel = -1.0 / (0.5 + common.frand()*0.3)
	

"""
===============
CL_BlasterTrail2

Green!
===============
"""
def CL_BlasterTrail2 (start, end): #vec3_t, vec3_t

	"""
	vec3_t		move;
	vec3_t		vec;
	float		len;
	int			j;
	cparticle_t	*p;
	int			dec;
	"""
	move = np.zeros((3,), dtype=np.float32)
	vec = np.zeros((3,), dtype=np.float32)

	q_shared.VectorCopy (start, move)
	q_shared.VectorSubtract (end, start, vec)
	length = q_shared.VectorNormalize (vec)

	dec = 5
	q_shared.VectorScale (vec, 5, vec)

	# FIXME: this is a really silly way to have a loop
	while length > 0:
	
		length -= dec

		p = cl_fx._alloc_particle()
		if p is None:
			return
		cl_fx.active_particles.append(p)
		q_shared.VectorClear (p.accel)
		
		p.time = cl_main.cl.time

		p.alpha = 1.0
		p.alphavel = -1.0 / (0.3+common.frand()*0.2)
		p.color = 0xd0
		for j in range(3):
		
			p.org[j] = move[j] + common.crand()
			p.vel[j] = common.crand()*5
			p.accel[j] = 0
		
		q_shared.VectorAdd (move, vec, move)
	
