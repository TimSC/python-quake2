import pytest

from common.frame_timing import SECOND, FrameClock, target_rates


@pytest.mark.parametrize("vsync, refresh, vid_maxfps, cl_maxfps, cl_async, expected", [
    (False, 0, 300, 60, True, (300, 60)),
    (False, 0, 30, 60, True, (30, 30)),        # no more packet than render frames
    (True, 60, 300, 60, True, (72.0, 72.0)),   # vsync: target the refresh rate * 1.2
    (True, 144, 300, 60, True, (172.8, 60)),   # packet cap below the refresh rate
    (True, 144, 100, 60, True, (100, 60)),     # vid_maxfps clearly below the refresh rate
    (False, 0, 300, 0, True, (300, 60.0)),     # automatic: 300 / round(300 / 60)
    (False, 0, 150, 0, True, (150, 50.0)),     # 150 / 3: round(2.5) is 3, as in the C
    (False, 0, 149, 0, True, (149, 74.5)),     # 149 / 2
    (False, 0, 80, -1, True, (80, 80)),        # under 90: one packet per render frame
    (False, 0, 300, 0, False, (300, 0)),       # automatic only applies with cl_async
])
def test_target_rates(vsync, refresh, vid_maxfps, cl_maxfps, cl_async, expected):
    assert target_rates(vsync, refresh, vid_maxfps, cl_maxfps, cl_async) == \
        pytest.approx(expected)


def run(clock, steps, usec, rfps, pfps, cl_async=True, timedemo=False):
    frames = []
    for _ in range(steps):
        packet, render = clock.advance(usec, rfps, pfps, timedemo, cl_async)
        frames.append((packet, render))
        if packet:
            clock.server_ran()
        if packet or render:
            clock.client_ran()
        clock.frame_done(packet, render)
    return frames


def test_first_iteration_runs_both():
    assert FrameClock().advance(1000, 300, 60, False, True) == (True, True)


def test_async_rates():
    clock = FrameClock()
    frames = run(clock, 3000, 1000, 200, 50)  # 3 seconds in 1 ms steps
    renders = sum(r for _, r in frames)
    packets = sum(p for p, _ in frames)
    assert renders == pytest.approx(600, abs=3)
    assert packets == pytest.approx(150, abs=3)
    assert all(r for p, r in frames if p)  # packet frames only with render frames


def test_sync_runs_both_together():
    frames = run(FrameClock(), 1000, 1000, 100, 100, cl_async=False)
    assert all(p == r for p, r in frames)
    assert sum(r for _, r in frames) == pytest.approx(100, abs=2)


def test_timedemo_runs_every_iteration():
    frames = run(FrameClock(), 50, 100, 60, 60, timedemo=True)
    assert all(p and r for p, r in frames)


def test_deltas():
    clock = FrameClock(packet_delta=0, render_delta=0)
    clock.advance(SECOND // 1000, 60, 60, False, True)  # too early for either
    assert (clock.packet_delta, clock.render_delta, clock.client_delta, clock.server_delta) == \
        (1000, 1000, 1000, 1000)
