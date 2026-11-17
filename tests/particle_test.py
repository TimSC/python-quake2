"""
Fire the blaster and check that GL3 particles reach the framebuffer.

Usage: python tests/particle_test.py -datadir /path/to/Data -cfgdir /tmp/q2particles
       +set vid_renderer gl3 +set s_initsound 0 +map base1
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("Q2PORT_NOMOUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = ["main.py"] + sys.argv[1:]

from backends.unix import system
import OpenGL.GL as GL
from common.header import shared
from client import cl_main
from client.refresh.gl3 import gl3_main
from game.player import client as p_client

t0 = None
particle_frames = 0
visible_frames = 0
draw_particles = gl3_main.GL3_DrawParticles
client_think = p_client.ClientThink


def DrawParticles():

	global particle_frames, visible_frames

	if not gl3_main.r_newrefdef.num_particles:
		return draw_particles()

	query = int(GL.glGenQueries(1)[0])
	GL.glBeginQuery(GL.GL_SAMPLES_PASSED, query)
	draw_particles()
	GL.glEndQuery(GL.GL_SAMPLES_PASSED)
	samples = int(GL.glGetQueryObjectuiv(query, GL.GL_QUERY_RESULT))
	GL.glDeleteQueries(1, [query])
	particle_frames += 1
	if samples > 0:
		visible_frames += 1


def ClientThink(ent, ucmd):

	global t0

	if cl_main.cls.state.name == "ca_active":

		if t0 is None:
			t0 = time.monotonic()
		elapsed = time.monotonic() - t0
		if 1 < elapsed < 4:
			ucmd.buttons |= shared.BUTTON_ATTACK
		if elapsed > 6:

			passed = particle_frames > 0 and visible_frames > 0
			print("particle: {} ({} submitted frames, {} visible frames)".format(
				"passed" if passed else "FAILED", particle_frames, visible_frames), flush=True)
			os._exit(0 if passed else 1)

	client_think(ent, ucmd)


gl3_main.GL3_DrawParticles = DrawParticles
p_client.ClientThink = ClientThink
system.main()
