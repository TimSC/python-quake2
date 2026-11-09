"""
ref_dispatch.py

Q2PORT: the C loads the renderer as a DLL (Sys_LoadLibrary of
ref_<name>.<ext>) keyed by the vid_renderer cvar. The port has the
renderers as python modules, so this is the lookup that returns the
active renderer module for the current vid_renderer value. gl1 is the
default (it is the renderer verified against the C reference); gl3 is
the modern-OpenGL renderer, ported alongside it (group 16).
"""

from __future__ import annotations


"""
 * Returns the active renderer module (gl1_main or gl3_main) for the
 * current vid_renderer cvar.
"""
def get_renderer():

	from client.vid import vid

	name = vid.vid_renderer.string
	if name == "gl3":
		from client.refresh.gl3 import gl3_main
		return gl3_main
	else:
		from client.refresh.gl1 import gl1_main
		return gl1_main
