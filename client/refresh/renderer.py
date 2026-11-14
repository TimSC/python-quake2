"""The renderer interface: what the client calls in a renderer (the C's refexport_t).

Each renderer (gl1, gl3) gives the client a ``Renderer`` holding its entry
points; the client calls them as methods (``renderer.render_frame(fd)``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

API_VERSION = 8  # Yamagi's API_VERSION; a renderer with another one isn't used


@dataclass(frozen=True, slots=True)
class Renderer:
    """A renderer's entry points."""

    # Started when loaded (False: it failed), stopped before it is unloaded.
    init: Callable[[], bool]
    shutdown: Callable[[], None]

    # The window and GL context (called by GLimp_InitGraphics): the SDL window
    # flags to create the window with (-1 on error), then the context for it,
    # its drawable size (which high-dpi can make differ from the window's),
    # and shutting the context down.
    prepare_for_window: Callable[[], int]
    init_context: Callable[[Any], bool]
    get_drawable_size: Callable[[], tuple[int, int]]
    shutdown_context: Callable[[], None]
    is_vsync_active: Callable[[], bool]

    # Registration: everything a level uses is registered before its first
    # frame; end_registration frees what wasn't. Models and skins from before
    # begin_registration are invalid after end_registration.
    begin_registration: Callable[[str], None]
    register_model: Callable[[str], Any]
    register_skin: Callable[[str], Any]
    set_sky: Callable[[str, float, Any], None]
    end_registration: Callable[[], None]

    render_frame: Callable[[Any], None]   # the 3D view of a refdef_t

    # 2D drawing. Pic names without a slash get "pics/" and ".pcx".
    find_pic: Callable[[str], Any]
    pic_size: Callable[[str], tuple[int, int]]       # (0, 0) if not found
    draw_pic_scaled: Callable[[int, int, str, float], None]
    draw_pic_scaled_col: Callable[[int, int, str, float, Any], None]
    draw_stretch_pic: Callable[[int, int, int, int, str], None]
    draw_char_scaled: Callable[[int, int, int, float], None]
    draw_tile_clear: Callable[[int, int, int, int, str], None]
    draw_fill: Callable[[int, int, int, int, int], None]
    draw_fade_screen: Callable[[], None]
    # a cinematic frame (8-bit, through the cinematic palette)
    draw_stretch_raw: Callable[[int, int, int, int, int, int, Any], None]

    # Frames and the palette (None: the game palette).
    set_palette: Callable[[Any], None]
    begin_frame: Callable[[float], None]
    end_world_renderpass: Callable[[], bool]  # finish the world, switch to the 2D pass
    end_frame: Callable[[], None]

    api_version: int = API_VERSION
