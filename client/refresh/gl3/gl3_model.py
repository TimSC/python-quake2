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
 * Model loading and caching for gl3 (client/refresh/model_cache.py).
 *
 * =======================================================================
"""

from client.refresh import model_cache
from client.refresh.gl3 import gl3_image, gl3_lightmap, gl3_main, gl3_misc, gl3_warp
from client.refresh.gl3.header import model

cache = model_cache.ModelCache(model_cache.ModelHooks(
    header=model,
    new_model=model.gl3model_t,
    find_image=lambda *args: gl3_image.GL3_FindImage(*args),
    notexture=lambda: gl3_misc.gl3_notexture,
    subdivide_surface=lambda mod, surface: gl3_warp.GL3_SubdivideSurface(surface, mod),
    fix_surface_sky=lambda: bool(gl3_main.r_fixsurfsky.value),
    begin_lightmaps=lambda mod: gl3_lightmap.GL3_LM_BeginBuildingLightmaps(mod),
    create_surface_lightmap=lambda surface: gl3_lightmap.GL3_LM_CreateSurfaceLightmap(surface),
    build_polygon=lambda mod, surface: gl3_lightmap.GL3_LM_BuildPolygonFromSurface(mod, surface),
    end_lightmaps=lambda: gl3_lightmap.GL3_LM_EndBuildingLightmaps(),
    load_file=lambda name: gl3_main.ri.FS_LoadFile(name),
    free_file=lambda buf: gl3_main.ri.FS_FreeFile(buf),
    cvar_get=lambda *args: gl3_main.ri.Cvar_Get(*args),
))


def GL3_Mod_Init() -> None:  # noqa: N802
    cache.init()


def GL3_Mod_ClusterPVS(cluster: int, model_: model.gl3model_t):  # noqa: N802
    return cache.cluster_pvs(cluster, model_)


def GL3_Mod_Modellist_f() -> None:  # noqa: N802
    cache.list_command()


def GL3_Mod_FreeAll() -> None:  # noqa: N802
    cache.free_all()


def GL3_BeginRegistration(map_name: str) -> None:  # noqa: N802
    """Specifies the model that will be used as the world."""
    gl3_main.gl3_oldviewcluster = -1  # force markleafs
    gl3_main.gl3state.currentlightmap = -1
    gl3_main.gl3_worldmodel = cache.begin_registration(map_name)
    gl3_main.gl3_viewcluster = -1


def GL3_RegisterModel(name: str) -> model.gl3model_t | None:  # noqa: N802
    return cache.register(name, gl3_main.gl3_worldmodel)


def GL3_EndRegistration() -> None:  # noqa: N802
    cache.end_registration(gl3_image.GL3_ImageHasFreeSpace, gl3_image.GL3_FreeUnusedImages)
