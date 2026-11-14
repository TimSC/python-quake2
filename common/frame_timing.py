"""When to run packet frames and render frames (Yamagi's Qcommon_Frame timing).

A packet frame runs the server and the client; a render frame runs the
renderer. With ``cl_async`` they run at their own rates: render frames at
``vid_maxfps`` (or the display's refresh rate with vsync), packet frames at
``cl_maxfps``, never more often than render frames, and only together with
one. Without it, both run together at the render rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SECOND = 1_000_000  # microseconds


def target_rates(vsync_active: bool, refresh_rate: float, vid_maxfps: float, cl_maxfps: float,
                 cl_async: bool) -> tuple[float, float]:
    """The target render and packet frame rates: (rfps, pfps)."""
    if vsync_active and vid_maxfps >= refresh_rate - 2:
        # Target the refresh rate, a bit above it: the reported rate is often
        # rounded down, and vsync throttles to it anyway.
        rfps = refresh_rate * 1.2
        pfps = cl_maxfps if cl_maxfps < refresh_rate - 2 else rfps
    else:
        rfps = vid_maxfps
        pfps = min(cl_maxfps, rfps)  # no more packet frames than render frames

    if cl_maxfps <= 0.0 and cl_async:
        # Choose a packet rate that divides the render rate, as close to 60
        # as possible (45..90 works well; outside it movement gets glitchy).
        if rfps < 90.0:
            pfps = rfps
        else:
            divider = math.floor(rfps / 60 + 0.5)  # rounds halves up, as the C's round()
            pfps = rfps / divider
    return rfps, pfps


@dataclass(slots=True)
class FrameClock:
    """The time since each kind of frame last ran, in microseconds."""

    packet_delta: int = SECOND   # since the last packet frame
    render_delta: int = SECOND   # since the last render frame
    client_delta: int = 0        # since the client last ran
    server_delta: int = 0        # since the server last ran

    def advance(self, usec: int, rfps: float, pfps: float, timedemo: bool,
                cl_async: bool) -> tuple[bool, bool]:
        """Add usec of time and decide this iteration: (packet frame, render frame)."""
        self.packet_delta += usec
        self.render_delta += usec
        self.client_delta += usec
        self.server_delta += usec
        if timedemo:
            return True, True

        render = self.render_delta >= SECOND / rfps
        if not cl_async:
            return render, render
        # Run a packet frame if we're closer to its target time now than we'd
        # probably be after the next render frame, and only with a render frame.
        packet = render and self.packet_delta + int(self.render_delta / 2) >= SECOND / pfps
        return packet, render

    def server_ran(self) -> None:
        self.server_delta = 0

    def client_ran(self) -> None:
        self.client_delta = 0

    def frame_done(self, packet: bool, render: bool) -> None:
        if packet:
            self.packet_delta = 0
        if render:
            self.render_delta = 0
