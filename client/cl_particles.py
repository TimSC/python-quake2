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

This file implements all generic particle stuff

=======================================================================
"""
from __future__ import annotations

from common.shared import rand

import numpy as np

from client import cl_main
from client import cl_view
from client import ref
from client.header import client as client_h

"""
#include "header/client.h"
"""

# Q2PORT: the C's linked lists of particles are Python lists. A new
# particle is appended, where the C puts it at the head of the list, so the
# list runs from the oldest particle to the newest and the C's walks from
# the head go through it reversed(). free_particles is used as a stack.
active_particles, free_particles = [], [] #cparticle_t *
particles = [] #cparticle_t[MAX_PARTICLES]
for i in range(ref.MAX_PARTICLES):
	particles.append(client_h.cparticle_t())
cl_numparticles = ref.MAX_PARTICLES #int

def CL_ClearParticles(): #void

	if cl_numparticles == 0:
		return

	"""
	int i;
	"""

	# free_particles = &particles[0]; ... particles[i].next = &particles[i + 1];
	free_particles[:] = particles[cl_numparticles - 1::-1] # particles[0] is on top
	active_particles.clear() # active_particles = NULL;


"""
===============
CL_ParticleEffect

Wall impact puffs
===============
"""
def CL_ParticleEffect(org, dir, color, count): #vec3_t, vec3_t, int, int

	"""
	int i, j;
	cparticle_t *p;
	float d;
	"""

	for i in range(count):

		if not free_particles:

			return


		p = free_particles.pop() # p = free_particles; free_particles = p->next;
		active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = cl_main.cl.time
		p.color = color + (rand.randk() & 7)
		d = rand.randk() & 31
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() & 7) - 4) + d * dir[j]
			p.vel[j] = rand.crandk() * 20


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY + 0.2
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)

			

def CL_ParticleEffect2(org, dir, color, count): #vec3_t, vec3_t, int, int

	"""
	int i, j;
	cparticle_t *p;
	float d;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(count):

		if not free_particles:

			return


		p = free_particles.pop() # p = free_particles; free_particles = p->next;
		active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = color + (rand.randk() & 7)
		d = rand.randk() & 7
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() & 7) - 4) + d * dir[j]
			p.vel[j] = rand.crandk() * 20


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)


def CL_ParticleEffect3(org, dir, color, count): #vec3_t, vec3_t, int, int

	"""
	int i, j;
	cparticle_t *p;
	float d;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(count):

		if not free_particles:

			return


		p = free_particles.pop() # p = free_particles; free_particles = p->next;
		active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		p.color = color
		d = rand.randk() & 7
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() & 7) - 4) + d * dir[j]
			p.vel[j] = rand.crandk() * 20


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * 0.3)

def CL_AddParticles(): #void

	"""
	cparticle_t *p, *next;
	float alpha;
	float time, time2;
	vec3_t org;
	int color;
	cparticle_t *active, *tail;
	"""
	org = np.zeros((3,), dtype=np.float32)

	active = [] # active = NULL; tail = NULL;

	for p in reversed(active_particles): # for (p = active_particles; p; p = next)

		if p.alphavel != client_h.INSTANT_PARTICLE:

			time = (cl_main.cl.time - p.time) * 0.001
			alpha = p.alpha + time * p.alphavel

			if alpha <= 0:

				# faded out
				free_particles.append(p) # p->next = free_particles; free_particles = p;
				continue


		else:

			time = 0.0
			alpha = p.alpha


		active.append(p) # p->next = NULL; tail->next = p; tail = p;

		if alpha > 1.0:

			alpha = 1


		color = p.color
		time2 = time * time

		org[0] = p.org[0] + p.vel[0] * time + p.accel[0] * time2
		org[1] = p.org[1] + p.vel[1] * time + p.accel[1] * time2
		org[2] = p.org[2] + p.vel[2] * time + p.accel[2] * time2

		cl_view.V_AddParticle(org, color, alpha)

		if p.alphavel == client_h.INSTANT_PARTICLE:

			p.alphavel = 0.0
			p.alpha = 0.0



	active.reverse() # Q2PORT: back to oldest first
	active_particles[:] = active # active_particles = active;

"""
===============
CL_GenericParticleEffect
===============
"""
def CL_GenericParticleEffect(org, dir, color, count, numcolors, dirspread, alphavel): #vec3_t, vec3_t, int, int, int, int, float

	"""
	int i, j;
	cparticle_t *p;
	float d;
	float time;
	"""

	time = cl_main.cl.time
	for i in range(count):

		if not free_particles:

			return


		p = free_particles.pop() # p = free_particles; free_particles = p->next;
		active_particles.append(p) # p->next = active_particles; active_particles = p;
		p.time = time
		if numcolors > 1:

			p.color = color + (rand.randk() & numcolors)

		else:

			p.color = color


		d = (rand.randk() & dirspread)
		for j in range(3):

			p.org[j] = org[j] + ((rand.randk() & 7) - 4) + d * dir[j]
			p.vel[j] = rand.crandk() * 20


		p.accel[0] = p.accel[1] = 0
		p.accel[2] = -client_h.PARTICLE_GRAVITY
		p.alpha = 1.0
		p.alphavel = -1.0 / (0.5 + rand.frandk() * alphavel)
