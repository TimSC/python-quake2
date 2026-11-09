"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 * Copyright (C) 2016-2017 Daniel Gibson
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * gl3_model.c - model registration for the OpenGL3 refresher
 *
 * =======================================================================
"""

from __future__ import annotations

from client.refresh.gl1 import gl1_model
from client.refresh.gl3.header import model

# Q2PORT: the model data (model_t) is identical between gl1 and gl3 — only the
# vertex format and the draw path differ. So the model registration reuses
# gl1_model directly; the produced model_t is used as a gl3model_t (duck typing).

registration_sequence = 0 #int


def RI_Init (): #void

	gl1_model.Mod_Init ()


def RI_BeginRegistration (map_): #char *

	gl1_model.RI_BeginRegistration (map_)


def RI_RegisterModel (name): #char * (returns gl3model_t *)

	return gl1_model.RI_RegisterModel (name)


def RI_EndRegistration (): #void

	gl1_model.RI_EndRegistration ()


def RI_Mod_Modellist_f (): #void

	gl1_model.Mod_Modellist_f ()


def RI_Mod_ClusterPVS (cluster, model_): #int, gl3model_t * (returns byte *)

	return gl1_model.Mod_ClusterPVS (cluster, model_)
