"""The renderers' model cache and brush model loading, shared by gl1 and gl3.

``ModelCache`` keeps the loaded models (slot 0 is always the world), loads
MD2, SP2 and BSP models into the renderer's model structures, and handles
registration (which models and images a level still uses). What differs
between the renderers (their model and surface classes, images, warp
surfaces and lightmaps) comes in through ``ModelHooks``.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import Any

import numpy as np

from common.header import shared
from q2data import FormatError
from q2data import bsp as q2bsp
from q2data import md2 as q2md2
from q2data import sp2 as q2sp2

MAX_MOD_KNOWN = 512


# The engine modules this uses import the renderers (which import this), so
# they are imported when first needed.
class _Lazy:
    def __getattr__(self, name: str) -> ModuleType:
        import importlib
        module = importlib.import_module({"files_models": "client.refresh.files.models",
                                          "files_pvs": "client.refresh.files.pvs",
                                          "clientserver": "common.clientserver"}[name])
        setattr(self, name, module)
        return module


_lazy = _Lazy()


def _error(message: str) -> None:
    _lazy.clientserver.Com_Error(shared.ERR_DROP, message)


def _print(text: str) -> None:
    _print(text)


@dataclass(slots=True)
class ModelHooks:
    """The renderer-specific parts of model loading."""

    header: ModuleType                       # model_t / msurface_t / modtype_t / SURF_*
    new_model: Callable[[], Any]
    find_image: Callable[..., Any]
    notexture: Callable[[], Any]             # the image for missing textures
    subdivide_surface: Callable[[Any, Any], None]   # (model, surface): cut up warps
    fix_surface_sky: Callable[[], bool]      # r_fixsurfsky
    begin_lightmaps: Callable[[Any], None]
    create_surface_lightmap: Callable[[Any], None]
    build_polygon: Callable[[Any, Any], None]       # (model, surface)
    end_lightmaps: Callable[[], None]
    load_file: Callable[[str], tuple[int, Any]]
    free_file: Callable[[Any], None]
    cvar_get: Callable[[str, str, int], Any]


class ModelCache:
    """Loaded models, by slot (the C's mod_known)."""

    def __init__(self, hooks: ModelHooks) -> None:
        self.hooks = hooks
        self.known = [hooks.new_model() for _ in range(MAX_MOD_KNOWN)]
        self.num_known = 0
        self.max_used = 0
        self.registration_sequence = 0
        self.novis = bytearray(q2bsp.MAX_MAP_LEAFS // 8)

    # ----------------------------------------------------------- bookkeeping

    def init(self) -> None:
        self.max_used = 0
        self.novis[:] = b"\xff" * len(self.novis)

    def has_free_space(self) -> bool:
        """Whether as many free slots remain as the level uses."""
        used = sum(1 for mod in self.known[:self.num_known]
                   if mod.name and mod.registration_sequence == self.registration_sequence)
        self.max_used = max(self.max_used, used)
        return self.num_known + self.max_used < MAX_MOD_KNOWN

    def cluster_pvs(self, cluster: int, model: Any) -> bytes | bytearray:
        """The decompressed PVS row of a cluster (all visible without vis)."""
        if cluster == -1 or model.vis is None:
            return self.novis
        vis = model.vis  # q2data.bsp.Visibility: data is the whole lump
        return _lazy.files_pvs.Mod_DecompressVis(
            vis.data[int(vis.offsets[cluster, q2bsp.VisType.PVS]):], (vis.num_clusters + 7) >> 3)

    def list_command(self) -> None:
        """modellist: the loaded models and their sizes."""
        total = used = 0
        _print("Loaded models:\n")
        for mod in self.known[:self.num_known]:
            in_use = ""
            if mod.registration_sequence == self.registration_sequence:
                in_use = "*"
                used += 1
            if not mod.name:
                continue
            _print(f"{mod.extradatasize:8} : {mod.name} {in_use}\n")
            total += mod.extradatasize
        _print(f"Total resident: {total}\n")
        free = self.has_free_space()
        _print(f"Used {used} of {self.max_used} models"
                                f"{', has free space' if free else ''}.\n")

    def free(self, mod: Any) -> None:
        mod.reset()

    def free_all(self) -> None:
        for mod in self.known[:self.num_known]:
            if mod.extradatasize:
                self.free(mod)

    # ---------------------------------------------------------- registration

    def begin_registration(self, map_name: str) -> Any:
        """Start a level: load (or keep) its world model, returned."""
        self.registration_sequence += 1
        full_name = f"maps/{map_name}.bsp"
        # a different map is freed first, so slot 0 is always the world
        flushmap = self.hooks.cvar_get("flushmap", "0", 0)
        if self.known[0].name != full_name or flushmap.value:
            self.free(self.known[0])
        return self.for_name(full_name, None, True)

    def register(self, name: str, world: Any) -> Any | None:
        """A model the level uses (and its images)."""
        mod = self.for_name(name, world, False)
        if mod is None:
            return None
        mod.registration_sequence = self.registration_sequence
        if mod.type == self.hooks.header.modtype_t.mod_brush:
            for texinfo in mod.texinfo[:mod.numtexinfo]:
                texinfo.image.registration_sequence = self.registration_sequence
        else:
            # numframes is unused for SP2 but set anyway
            mod.numframes = _lazy.files_models.Mod_ReLoadSkins(
                mod.skins, self.hooks.find_image, mod.extradata, mod.type.value)
        return mod

    def end_registration(self, image_has_free_space: Callable[[], bool],
                         free_unused_images: Callable[[], None]) -> None:
        """Free the models (and images) the level doesn't use, if space is short."""
        if self.has_free_space() and image_has_free_space():
            return  # should be enough space to load the next maps
        for mod in self.known[:self.num_known]:
            if mod.name and mod.registration_sequence != self.registration_sequence:
                self.free(mod)
        free_unused_images()

    # -------------------------------------------------------------- loading

    def for_name(self, name: str, parent: Any | None, crash: bool) -> Any | None:
        """The model of a name, loading it if needed; "*n" is an inline model
        of parent (the world)."""
        if not name:
            _error("Mod_ForName: NULL name")
        if name[0] == "*" and parent is not None:
            try:
                i = int(name[1:])
            except ValueError:
                i = 0
            if i < 1 or i >= parent.numsubmodels:
                _error("Mod_ForName: bad inline model number")
            return parent.submodels[i]

        for mod in self.known[:self.num_known]:
            if mod.name and mod.name == name:
                return mod

        slot = next((i for i in range(self.num_known) if not self.known[i].name),
                    self.num_known)
        if slot == self.num_known:
            if self.num_known == MAX_MOD_KNOWN:
                _error("Mod_ForName: mod_numknown == MAX_MOD_KNOWN")
            self.num_known += 1
        mod = self.known[slot]
        mod.name = name

        length, buf = self.hooks.load_file(name)
        if buf is None:
            if crash:
                _error(f"Mod_ForName: {name} not found")
            mod.name = None
            return None

        header = self.hooks.header
        ident = bytes(buf[:4])
        if ident in (q2md2.MD2_IDENT, q2sp2.SP2_IDENT):
            type_ = [0]
            loaders = _lazy.files_models
            if ident == q2md2.MD2_IDENT:
                mod.extradata = loaders.Mod_LoadMD2(name, buf, length, mod.mins, mod.maxs,
                                                    mod.skins, self.hooks.find_image, type_)
            else:
                mod.extradata = loaders.Mod_LoadSP2(name, buf, length, mod.skins,
                                                    self.hooks.find_image, type_)
            mod.type = header.modtype_t(type_[0])
            if mod.extradata is None:
                _error(f"Mod_ForName: Failed to load {name}")
        elif ident == q2bsp.BSP_IDENT:
            self._load_brush_model(mod, buf)
        else:
            _error(f"Mod_ForName: unknown fileid for {name}")

        mod.extradatasize = length  # the file size stands in for the C's hunk size
        self.hooks.free_file(buf)
        return mod

    def _load_brush_model(self, mod: Any, buffer: Any) -> None:
        if mod is not self.known[0]:
            _error("Mod_LoadBrushModel: Loaded a brush model after the world")
        try:
            lumps = q2bsp.read_header(buffer)
        except FormatError as err:
            _error(f"Mod_LoadBrushModel: {mod.name} {err}")
        mod.type = self.hooks.header.modtype_t.mod_brush
        name, base, lump = mod.name, buffer, q2bsp.Lump

        # The shared lump loaders fill one-element lists (the C's out pointers).
        def load(loader: Callable, lump_index: lump, *extra: Any) -> tuple[Any, Any]:
            out, count = [None], [0]
            loader(name, out, count, base, lumps[lump_index], *extra)
            return out[0], count[0]

        loaders = _lazy.files_models
        mod.vertexes, mod.numvertexes = load(loaders.Mod_LoadVertexes, lump.VERTICES, 0)
        mod.edges, mod.numedges = load(loaders.Mod_LoadEdges, lump.EDGES, 1)
        mod.surfedges, mod.numsurfedges = load(loaders.Mod_LoadSurfedges, lump.SURF_EDGES, 0)
        lightdata = [None]
        _lazy.files_models.Mod_LoadLighting(lightdata, base, lumps[lump.LIGHTING])
        mod.lightdata = lightdata[0]
        mod.planes, mod.numplanes = load(_lazy.files_models.Mod_LoadPlanes, lump.PLANES, 0)
        mod.texinfo, mod.numtexinfo = load(_lazy.files_models.Mod_LoadTexinfo, lump.TEXINFO,
                                           self.hooks.find_image, self.hooks.notexture(), 0)
        self._load_faces(mod, base, lumps[lump.FACES])
        self._load_marksurfaces(mod, base, lumps[lump.LEAF_FACES])
        vis = [None]
        _lazy.files_models.Mod_LoadVisibility(vis, base, lumps[lump.VISIBILITY])
        mod.vis = vis[0]
        self._load_leafs(mod, base, lumps[lump.LEAFS])
        nodes, num_nodes = [None], [0]
        _lazy.files_models.Mod_LoadNodes(name, mod.planes, mod.numplanes, mod.leafs, mod.numleafs,
                                   nodes, num_nodes, base, lumps[lump.NODES])
        mod.nodes, mod.numnodes = nodes[0], num_nodes[0]
        self._load_submodels(mod, base, lumps[lump.MODELS])
        mod.numframes = 2  # regular and alternate animation

    def _load_submodels(self, mod: Any, base: Any, lump: q2bsp.LumpInfo) -> None:
        rows = _lazy.files_models.lump_rows(f"Mod_LoadSubmodels: funny lump size in {mod.name}",
                                      base, lump, q2bsp.Lump.MODELS)
        mod.submodels = []
        mod.numsubmodels = len(rows)
        for i, row in enumerate(rows):
            # the first copies the world as its template, the others the first
            out = copy.copy(mod if i == 0 else mod.submodels[0])
            # the copy shares the parent's arrays, as the C's does; these need
            # their own storage
            out.mins = out.mins.copy()
            out.maxs = out.maxs.copy()
            out.origin = out.origin.copy()
            out.name = f"*{i}"
            for j in range(3):
                # spread the mins / maxs by a pixel
                out.mins[j] = row.mins[j] - 1
                out.maxs[j] = row.maxs[j] + 1
                out.origin[j] = row.origin[j]
            out.radius = _lazy.files_pvs.Mod_RadiusFromBounds(out.mins, out.maxs)
            out.firstnode = row.headnode
            out.firstmodelsurface = row.firstface
            out.nummodelsurfaces = row.numfaces
            out.numleafs = 0  # visleafs
            if out.firstnode >= mod.numnodes:
                _error(f"Mod_LoadSubmodels: Inline model {i} has bad firstnode")
            mod.submodels.append(out)

    @staticmethod
    def _surface_extents(mod: Any, surface: Any) -> None:
        """Fill in surface.texturemins and surface.extents."""
        mins = [999999.0, 999999.0]
        maxs = [-99999.0, -99999.0]
        vecs = surface.texinfo.vecs
        for i in range(surface.numedges):
            e = mod.surfedges[surface.firstedge + i]
            v = mod.vertexes[mod.edges[e].v[0] if e >= 0 else mod.edges[-e].v[1]].position
            for j in range(2):
                value = v[0] * vecs[j][0] + v[1] * vecs[j][1] + v[2] * vecs[j][2] + vecs[j][3]
                mins[j] = min(mins[j], value)
                maxs[j] = max(maxs[j], value)
        for i in range(2):
            low, high = math.floor(mins[i] / 16), math.ceil(maxs[i] / 16)
            surface.texturemins[i] = low * 16
            surface.extents[i] = (high - low) * 16

    def _load_faces(self, mod: Any, base: Any, lump: q2bsp.LumpInfo) -> None:
        hooks, header = self.hooks, self.hooks.header
        rows = _lazy.files_models.lump_rows(f"Mod_LoadFaces: funny lump size in {mod.name}",
                                      base, lump, q2bsp.Lump.FACES)
        mod.surfaces = []
        mod.numsurfaces = len(rows)
        hooks.begin_lightmaps(mod)
        for row in rows:
            out = header.msurface_t()
            mod.surfaces.append(out)
            out.firstedge = row.firstedge
            out.numedges = row.numedges
            out.flags = header.SURF_PLANEBACK if row.side else 0
            out.polys = []

            if row.planenum < 0 or row.planenum >= mod.numplanes:
                _error(f"Mod_LoadFaces: Incorrect {row.planenum} planenum.")
            out.plane = mod.planes[row.planenum]
            if row.texinfo < 0 or row.texinfo >= mod.numtexinfo:
                _error("Mod_LoadFaces: bad texinfo number")
            out.texinfo = mod.texinfo[row.texinfo]
            self._surface_extents(mod, out)

            # lighting info
            out.styles = list(row.styles)
            offset = row.lightofs
            out.samples = None if offset == -1 else memoryview(mod.lightdata)[offset:]

            # drawing flags
            flags = out.texinfo.flags
            if flags & shared.SURF_WARP:
                out.flags |= header.SURF_DRAWTURB
                for i in range(2):
                    out.extents[i] = 16384
                    out.texturemins[i] = -8192
                hooks.subdivide_surface(mod, out)  # cut up the polygon for warps
            if hooks.fix_surface_sky() and flags & shared.SURF_SKY:
                out.flags |= header.SURF_DRAWSKY

            # lightmaps and polygons
            if not flags & (shared.SURF_SKY | shared.SURF_TRANS33 | shared.SURF_TRANS66
                            | shared.SURF_WARP):
                hooks.create_surface_lightmap(out)
            if not flags & shared.SURF_WARP:
                hooks.build_polygon(mod, out)
        hooks.end_lightmaps()

    @staticmethod
    def _load_leafs(mod: Any, base: Any, lump: q2bsp.LumpInfo) -> None:
        from client.refresh import ref_shared

        rows = _lazy.files_models.lump_rows(f"Mod_LoadLeafs: funny lump size in {mod.name}",
                                      base, lump, q2bsp.Lump.LEAFS)
        mod.leafs = []
        mod.numleafs = len(rows)
        for row in rows:
            out = ref_shared.mleaf_t()
            mod.leafs.append(out)
            for j in range(3):
                # floats, as the C's float minmaxs (much faster in R_CullBox
                # than numpy int16)
                out.minmaxs[j] = float(row.mins[j])
                out.minmaxs[3 + j] = float(row.maxs[j])
            out.contents = row.contents
            out.cluster = row.cluster
            out.area = row.area
            first = row.firstleafface & 0xFFFF
            out.nummarksurfaces = row.numleaffaces & 0xFFFF
            # a slice of the model's marksurfaces, the C's pointer into them
            out.firstmarksurface = mod.marksurfaces[first:first + out.nummarksurfaces]
            if first + out.nummarksurfaces > mod.nummarksurfaces:
                _error(f"Mod_LoadLeafs: wrong marksurfaces position in {mod.name}")

    @staticmethod
    def _load_marksurfaces(mod: Any, base: Any, lump: q2bsp.LumpInfo) -> None:
        # the C reads them as (signed) shorts
        numbers = _lazy.files_models.lump_records(
            f"Mod_LoadMarksurfaces: funny lump size in {mod.name}", base, lump,
            q2bsp.Lump.LEAF_FACES).astype(np.int16).tolist()
        mod.marksurfaces = []
        mod.nummarksurfaces = len(numbers)
        for j in numbers:
            if j < 0 or j >= mod.numsurfaces:
                _error("Mod_LoadMarksurfaces: bad surface number")
            mod.marksurfaces.append(mod.surfaces[j])
