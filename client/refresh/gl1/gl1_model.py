"""
 * Copyright (C) 1997-2001 Id Software, Inc.
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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * Model loading and caching for gl1 (client/refresh/model_cache.py).
 *
 * =======================================================================
"""

from client.refresh import model_cache
from client.refresh.gl1 import gl1_image, gl1_lightmap, gl1_main, gl1_warp
from client.refresh.gl1.header import model

cache = model_cache.ModelCache(model_cache.ModelHooks(
    header=model,
    new_model=model.model_t,
    find_image=lambda *args: gl1_image.R_FindImage(*args),
    notexture=lambda: gl1_main.r_notexture,
    subdivide_surface=lambda mod, surface: gl1_warp.R_SubdivideSurface(mod, surface),
    fix_surface_sky=lambda: bool(gl1_main.r_fixsurfsky.value),
    begin_lightmaps=lambda mod: gl1_lightmap.LM_BeginBuildingLightmaps(mod),
    create_surface_lightmap=lambda surface: gl1_lightmap.LM_CreateSurfaceLightmap(surface),
    build_polygon=lambda mod, surface: gl1_lightmap.LM_BuildPolygonFromSurface(mod, surface),
    end_lightmaps=lambda: gl1_lightmap.LM_EndBuildingLightmaps(),
    load_file=lambda name: gl1_main.ri.FS_LoadFile(name),
    free_file=lambda buf: gl1_main.ri.FS_FreeFile(buf),
    cvar_get=lambda *args: gl1_main.ri.Cvar_Get(*args),
))


def Mod_Init() -> None:  # noqa: N802
    cache.init()


def Mod_ClusterPVS(cluster: int, model_: model.model_t):  # noqa: N802
    return cache.cluster_pvs(cluster, model_)


def Mod_Modellist_f() -> None:  # noqa: N802
    cache.list_command()


def Mod_FreeAll() -> None:  # noqa: N802
    cache.free_all()


def RI_BeginRegistration(map_name: str) -> None:  # noqa: N802
    """Specifies the model that will be used as the world."""
    gl1_main.r_oldviewcluster = -1  # force markleafs
    gl1_main.r_worldmodel = cache.begin_registration(map_name)
    gl1_main.r_viewcluster = -1


def RI_RegisterModel(name: str) -> model.model_t | None:  # noqa: N802
    return cache.register(name, gl1_main.r_worldmodel)


def RI_EndRegistration() -> None:  # noqa: N802
    cache.end_registration(gl1_image.R_ImageHasFreeSpace, gl1_image.R_FreeUnusedImages)
