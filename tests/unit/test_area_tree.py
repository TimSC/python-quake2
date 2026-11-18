"""The server's area tree: building it, and finding the entities touching a box."""

from dataclasses import dataclass, field

import numpy as np

# imported the way the game imports the server (through the platform layer)
import backends.unix.system  # noqa: F401
from game.header import game as game_h
from server import sv_world


def vec(*v: float) -> np.ndarray:
    return np.array(v, dtype=np.float32)


@dataclass
class Ent:
    name: str
    absmin: np.ndarray
    absmax: np.ndarray
    solid: int = game_h.SOLID_BBOX
    area: game_h.link_t = field(default_factory=game_h.link_t)


def build() -> sv_world.AreaNode:
    """A world 2048 x 1024 x 512, centred on the origin."""
    root = sv_world._create_area_node(0, vec(-1024, -512, -256), vec(1024, 512, 256))
    sv_world._root = root
    return root


def leaves(node: sv_world.AreaNode) -> list[sv_world.AreaNode]:
    if node.axis == -1:
        return [node]
    return leaves(node.children[0]) + leaves(node.children[1])


def place(ent: Ent) -> None:
    """Links ent into the node it fits in, as link_edict does after its box."""
    node = sv_world._root
    while node.axis != -1:
        if ent.absmin[node.axis] > node.dist:
            node = node.children[0]
        elif ent.absmax[node.axis] < node.dist:
            node = node.children[1]
        else:
            break
    linked_in = node.triggers if ent.solid == game_h.SOLID_TRIGGER else node.solids
    linked_in.append(ent)
    ent.area.prev = linked_in


def test_tree_has_16_leaves_split_on_the_longer_side():
    root = build()
    assert root.axis == 0 and root.dist == 0.0  # x is the longer side
    assert len(leaves(root)) == 2 ** sv_world.AREA_DEPTH
    front, back = root.children
    assert front.axis == 1  # each half is 1024 x 1024: y next
    # the front child holds the high side
    assert sv_world._create_area_node(0, vec(0, 0, 0), vec(8, 2, 2)).children[0].dist > 4


def test_find_touching_entities_in_tree_order():
    build()
    crossing = Ent("crossing", vec(-8, -8, 0), vec(8, 8, 8))  # crosses the root split
    east = Ent("east", vec(500, 100, 0), vec(520, 120, 8))
    west = Ent("west", vec(-520, 100, 0), vec(-500, 120, 8))
    for e in (crossing, east, west):
        place(e)

    found = sv_world.find_area_edicts(vec(-600, 0, 0), vec(600, 200, 8), 100, 1)
    # the node's own entities first, then the front (high) side, then the back
    assert [e.name for e in found] == ["crossing", "east", "west"]

    found = sv_world.find_area_edicts(vec(490, 90, 0), vec(530, 130, 8), 100, 1)
    assert [e.name for e in found] == ["east"]


def test_triggers_and_solids_are_separate_and_inactive_ones_skipped():
    build()
    trigger = Ent("trigger", vec(0, 0, 0), vec(8, 8, 8), solid=game_h.SOLID_TRIGGER)
    solid = Ent("solid", vec(0, 0, 0), vec(8, 8, 8))
    place(trigger)
    place(solid)
    box = (vec(-1, -1, -1), vec(9, 9, 9))
    assert [e.name for e in sv_world.find_area_edicts(*box, 100, 1)] == ["solid"]
    assert [e.name for e in sv_world.find_area_edicts(*box, 100, 2)] == ["trigger"]

    solid.solid = game_h.SOLID_NOT  # deactivated, though still linked
    assert sv_world.find_area_edicts(*box, 100, 1) == []


def test_unlink_removes_only_that_entity():
    build()
    a = Ent("a", vec(0, 0, 0), vec(8, 8, 8))
    b = Ent("b", vec(0, 0, 0), vec(8, 8, 8))
    place(a)
    place(b)
    sv_world.unlink_edict(a)
    assert a.area.prev is None
    assert [e.name for e in sv_world.find_area_edicts(vec(0, 0, 0), vec(8, 8, 8), 100, 1)] == ["b"]
    sv_world.unlink_edict(a)  # not linked: nothing happens


def test_area_edicts_fills_the_games_list():
    build()
    place(Ent("a", vec(0, 0, 0), vec(8, 8, 8)))
    out = [None] * 4
    assert sv_world.area_edicts(vec(0, 0, 0), vec(8, 8, 8), out, 4, 1) == 1
    assert out[0].name == "a" and out[1] is None
