"""The shared model cache, with gl1's model classes and stand-in renderer hooks."""

import pytest

from client.refresh import model_cache
from client.refresh.gl1.header import model
from q2data import bsp, md2
from tests.unit.builders import box_room, cube_model


class Image:
    def __init__(self, name: str) -> None:
        self.name = name
        self.registration_sequence = 0


class Renderer:
    """Records what the cache asked the renderer to do."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.events: list[str] = []
        self.cache = model_cache.ModelCache(model_cache.ModelHooks(
            header=model, new_model=model.model_t,
            find_image=lambda name, kind: Image(name),
            notexture=lambda: Image("notexture"),
            subdivide_surface=lambda mod, surface: self.events.append("subdivide"),
            fix_surface_sky=lambda: True,
            begin_lightmaps=lambda mod: self.events.append("begin"),
            create_surface_lightmap=lambda surface: self.events.append("lightmap"),
            build_polygon=lambda mod, surface: self.events.append("polygon"),
            end_lightmaps=lambda: self.events.append("end"),
            load_file=self.load, free_file=lambda buf: None,
            cvar_get=lambda name, value, flags: type("Cvar", (), {"value": 0})()))
        self.cache.init()

    def load(self, name: str):
        data = self.files.get(name)
        return (-1, None) if data is None else (len(data), bytearray(data))


@pytest.fixture
def renderer() -> Renderer:
    return Renderer({"maps/box.bsp": bsp.write_bsp(box_room()),
                     "models/cube/tris.md2": md2.write_md2(cube_model())})


def test_world_loads(renderer):
    world = renderer.cache.begin_registration("box")
    assert world is renderer.cache.known[0]
    assert world.type == model.modtype_t.mod_brush
    assert (world.numsurfaces, world.numleafs, world.numnodes, world.numsubmodels) == (6, 7, 6, 1)
    assert renderer.events == ["begin"] + ["lightmap", "polygon"] * 6 + ["end"]
    surface = world.surfaces[0]
    assert surface.texinfo.image.name == "textures/e1u1/floor1_1.wal"
    assert surface.extents == [256, 256]
    assert world.leafs[6].nummarksurfaces == 6  # the room's empty leaf sees its six walls


def test_world_is_kept_for_the_same_map(renderer):
    first = renderer.cache.begin_registration("box")
    assert renderer.cache.begin_registration("box") is first


def test_models_and_inline_models(renderer):
    world = renderer.cache.begin_registration("box")
    cube = renderer.cache.register("models/cube/tris.md2", world)
    assert cube.type == model.modtype_t.mod_alias
    assert cube.registration_sequence == renderer.cache.registration_sequence
    assert renderer.cache.register("models/cube/tris.md2", world) is cube  # cached
    assert renderer.cache.register("models/missing.md2", world) is None
    with pytest.raises(Exception, match="bad inline model number"):
        renderer.cache.for_name("*5", world, True)


def test_pvs_without_vis_sees_everything(renderer):
    world = renderer.cache.begin_registration("box")
    assert renderer.cache.cluster_pvs(-1, world)[0] == 0xFF
