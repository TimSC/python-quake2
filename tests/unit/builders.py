"""Synthetic Quake II data for tests: no game data needed.

``box_room`` builds a small but complete map: a closed cube room whose six
walls are solid brushes, with a BSP tree, faces, texinfo, areas and
visibility. It is valid for collision, movement and rendering code.
"""

from __future__ import annotations

import numpy as np

from q2data import bsp, md2
from q2data.binary import encode_name
from q2data.bsp import Bsp, Contents, PlaneType

ROOM_HALF = 128      # the interior is [-128, 128] on every axis
WALL = 16            # wall thickness
TEXTURE = "e1u1/floor1_1"

# The walls, in the order of their leafs: +x, -x, +y, -y, +z, -z.
WALL_DIRECTIONS = [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]


class _Planes:
    """Planes in pairs (plane n and n ^ 1 face opposite ways), as the map
    compiler stores them: the even one of a pair faces a positive axis."""

    def __init__(self) -> None:
        self.rows: list[tuple[tuple[float, float, float], float, int]] = []

    def index(self, axis: int, sign: int, dist: float) -> int:
        normal = [0.0, 0.0, 0.0]
        normal[axis] = 1.0
        positive = (tuple(normal), dist if sign > 0 else -dist)
        for i in range(0, len(self.rows), 2):
            if self.rows[i][:2] == positive:
                return i if sign > 0 else i + 1
        pos_normal, pos_dist = positive
        neg_normal = tuple(-c for c in pos_normal)
        self.rows.append((pos_normal, pos_dist, axis))
        self.rows.append((neg_normal, -pos_dist, axis))
        return len(self.rows) - 2 if sign > 0 else len(self.rows) - 1

    def array(self) -> np.ndarray:
        out = np.zeros(len(self.rows), bsp.PLANE)
        for i, (normal, dist, axis) in enumerate(self.rows):
            out[i] = (normal, dist, PlaneType(axis))
        return out


def box_room(half: int = ROOM_HALF, wall: int = WALL, texture: str = TEXTURE,
             entities: str | None = None) -> Bsp:
    """A closed cube room centred on the origin."""
    planes = _Planes()
    outer = half + wall

    # One solid brush per wall.
    brushes, sides = [], []
    for axis, sign in WALL_DIRECTIONS:
        first_side = len(sides)
        for a in range(3):
            for s in (1, -1):
                if a == axis:
                    dist = outer if s == sign else -half
                else:
                    dist = outer
                sides.append((planes.index(a, s, dist), 0))
        brushes.append((first_side, 6, int(Contents.SOLID)))

    # The tree: a chain of nodes, each splitting off one wall's leaf. A node's
    # plane faces +axis at the inner wall surface.
    interior_leaf = len(WALL_DIRECTIONS)
    nodes = []
    for i, (axis, sign) in enumerate(WALL_DIRECTIONS):
        plane = planes.index(axis, 1, half * sign)
        wall_leaf = -(i + 1)  # leaf i
        next_child = i + 1 if i + 1 < len(WALL_DIRECTIONS) else -(interior_leaf + 1)
        children = (wall_leaf, next_child) if sign > 0 else (next_child, wall_leaf)
        # face i lies on this node's plane
        nodes.append((plane, children, (-outer,) * 3, (outer,) * 3, i, 1))

    leafs = []
    for i in range(len(WALL_DIRECTIONS)):
        leafs.append((int(Contents.SOLID), -1, 0, (-outer,) * 3, (outer,) * 3, 0, 0, i, 1))
    leafs.append((0, 0, 1, (-half,) * 3, (half,) * 3, 0, 6, 0, 0))

    # Six faces lining the inside of the room, facing in.
    corners = np.array([[x, y, z] for x in (-half, half) for y in (-half, half)
                        for z in (-half, half)], np.float32)
    vertices = np.zeros(8, bsp.VERTEX)
    vertices["point"] = corners
    edges_list: list[tuple[int, int]] = [(0, 0)]  # edge 0 is unused, as in real maps
    surf_edges: list[int] = []
    faces = []
    texinfo = np.zeros(6, bsp.TEXINFO)
    for i, (axis, sign) in enumerate(WALL_DIRECTIONS):
        on_face = [v for v in range(8) if corners[v][axis] == half * sign]
        u_axis, v_axis = [a for a in range(3) if a != axis]
        centre = corners[on_face].mean(axis=0)
        angles = [np.arctan2(corners[v][v_axis] - centre[v_axis],
                             corners[v][u_axis] - centre[u_axis]) for v in on_face]
        ring = [on_face[j] for j in np.argsort(angles)]
        if sign > 0:
            ring.reverse()
        first_edge = len(surf_edges)
        for j in range(4):
            edges_list.append((ring[j], ring[(j + 1) % 4]))
            surf_edges.append(len(edges_list) - 1)
        # The face's plane faces into the room: the opposite of the wall direction.
        plane = planes.index(axis, -sign, -half * sign)
        side = plane & 1
        faces.append((plane & ~1, side, first_edge, 4, i, (0, 255, 255, 255), -1))
        vecs = np.zeros((2, 4), np.float32)
        vecs[0, u_axis] = 1.0
        vecs[1, v_axis] = -1.0
        texinfo[i] = (vecs, 0, 0, encode_name(texture, 32), -1)

    world_entities = entities if entities is not None else (
        '{\n"classname" "worldspawn"\n"message" "box room"\n}\n'
        '{\n"classname" "info_player_start"\n"origin" "0 0 -100"\n"angle" "90"\n}\n')

    edges = np.zeros(len(edges_list), bsp.EDGE)
    edges["v"] = edges_list
    model = np.zeros(1, bsp.MODEL)
    model[0] = ((-outer,) * 3, (outer,) * 3, (0, 0, 0), 0, 0, 6)
    areas = np.zeros(2, bsp.AREA)

    return Bsp(
        entities=world_entities,
        planes=planes.array(),
        vertices=vertices,
        visibility=bsp.build_visibility([[0]]),
        nodes=np.array(nodes, bsp.NODE),
        texinfo=texinfo,
        faces=np.array(faces, bsp.FACE),
        lighting=b"",
        leafs=np.array(leafs, bsp.LEAF),
        leaf_faces=np.arange(6, dtype="<u2"),
        leaf_brushes=np.arange(6, dtype="<u2"),
        edges=edges,
        surf_edges=np.array(surf_edges, "<i4"),
        models=model,
        brushes=np.array(brushes, bsp.BRUSH),
        brush_sides=np.array(sides, bsp.BRUSH_SIDE),
        pop=b"\0" * 32,
        areas=areas,
        area_portals=np.zeros(0, bsp.AREA_PORTAL),
    )


def cube_model(frames: int = 2, skins: tuple[str, ...] = ("models/test/skin.pcx",)) -> md2.Md2:
    """A cube MD2 with a few frames (each frame grows the cube a little)."""
    corners = np.array([[x, y, z] for x in (0, 255) for y in (0, 255) for z in (0, 255)],
                       np.uint8)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    triangles = []
    for a, b, c, d in faces:
        triangles.append(((a, b, c), (a, b, c)))
        triangles.append(((a, c, d), (a, c, d)))
    st = np.zeros(8, md2.ST_VERT)
    st["s"] = [0, 0, 0, 0, 63, 63, 63, 63]
    st["t"] = [0, 0, 63, 63, 0, 0, 63, 63]

    frame_list = []
    for f in range(frames):
        verts = np.zeros(8, md2.TRI_VERTEX)
        verts["v"] = corners
        verts["normal"] = np.arange(8)
        scale = np.full(3, (16 + f) / 255.0, np.float32)
        frame_list.append(md2.Md2Frame(f"frame{f}", scale, np.full(3, -8.0, np.float32), verts))

    glcmds: list[int] = []
    for (xyz, _st) in triangles:
        glcmds.append(3)  # a strip of one triangle
        for index in xyz:
            s = np.float32(st["s"][index] / 64.0).view(np.int32)
            t = np.float32(st["t"][index] / 64.0).view(np.int32)
            glcmds += [int(s), int(t), index]
    glcmds.append(0)
    return md2.Md2(64, 64, list(skins), st, np.array(triangles, md2.TRIANGLE), frame_list,
                   np.array(glcmds, np.int32))


def gradient_palette() -> np.ndarray:
    """A 256-colour palette: index i is (i, 255 - i, i // 2)."""
    i = np.arange(256)
    return np.stack([i, 255 - i, i // 2], axis=1).astype(np.uint8)


def pattern(width: int, height: int, seed: int = 0) -> np.ndarray:
    """Palette indices with runs and single pixels, for testing RLE."""
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, (height, width), dtype=np.uint8)
    pixels[:, : width // 2] = pixels[:, :1]  # long runs on the left half
    return pixels
