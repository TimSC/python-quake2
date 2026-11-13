import copy

import pytest

from common import movemsg, player_delta, szone
from common.header import common as common_h
from common.header import shared

C = common_h


def new_buffer() -> common_h.sizebuf_t:
    buf = common_h.sizebuf_t()
    szone.SZ_Init(buf, 4096)
    return buf


def round_trip(old, new):
    buf = new_buffer()
    player_delta.write_delta(old, new, buf)
    movemsg.MSG_BeginReading(buf)
    out = copy.deepcopy(old) if old is not None else shared.player_state_t()
    flags = player_delta.read_delta(buf, out)
    assert buf.readcount == buf.cursize
    return flags, out, buf.cursize


def test_unchanged_state_sends_only_the_weapon_model():
    ps = shared.player_state_t()
    ps.gunindex = 3
    flags, out, size = round_trip(copy.deepcopy(ps), ps)
    assert flags == C.PS_WEAPONINDEX
    assert size == 2 + 1 + 4  # flags, gunindex, empty stats mask
    assert out.gunindex == 3


def test_changed_groups_only():
    old = shared.player_state_t()
    new = copy.deepcopy(old)
    new.pmove.origin[1] = 120
    new.fov = 110.0
    flags, out, _ = round_trip(old, new)
    assert flags == C.PS_M_ORIGIN | C.PS_FOV | C.PS_WEAPONINDEX
    assert list(out.pmove.origin) == [0, 120, 0]
    assert out.fov == 110.0


def test_full_round_trip():
    new = shared.player_state_t()
    pm = new.pmove
    pm.pm_type, pm.pm_time, pm.pm_flags, pm.gravity = 2, 40, 0x18, 800
    pm.origin[:] = (-100, 200, 3000)
    pm.velocity[:] = (5, -6, 7)
    pm.delta_angles[:] = (1000, -2000, 3)
    new.viewoffset[:] = (0.0, 0.0, 22.0)
    new.viewangles[:] = (10.0, 90.0, 0.0)
    new.kick_angles[:] = (-1.25, 0.5, 0.0)
    new.gunindex, new.gunframe = 4, 17
    new.gunoffset[:] = (0.25, -0.5, 1.0)
    new.gunangles[:] = (2.0, 0.0, -3.0)
    new.blend[:] = (1.0, 0.0, 0.0, 0.2)
    new.fov, new.rdflags = 90.0, 2
    new.stats[1], new.stats[5] = 100, -7
    _, out, _ = round_trip(None, new)
    assert (out.pmove.pm_type, out.pmove.pm_time, out.pmove.pm_flags, out.pmove.gravity) == \
        (2, 40, 0x18, 800)
    assert list(out.pmove.origin) == [-100, 200, 3000]
    assert list(out.pmove.delta_angles) == [1000, -2000, 3]
    assert list(out.viewoffset) == [0.0, 0.0, 22.0]
    assert list(out.kick_angles) == [-1.25, 0.5, 0.0]
    assert out.viewangles[1] == pytest.approx(90.0, abs=0.01)
    assert (out.gunindex, out.gunframe) == (4, 17)
    assert list(out.gunoffset) == [0.25, -0.5, 1.0]
    assert out.blend[0] == 1.0 and out.blend[3] == pytest.approx(51 / 255)
    assert (out.fov, out.rdflags) == (90.0, 2)
    assert (out.stats[1], out.stats[5], out.stats[0]) == (100, -7, 0)


def test_quarter_units_truncate():
    new = shared.player_state_t()
    new.viewoffset[2] = 22.3  # 89.2 quarters -> 89 -> 22.25
    _, out, _ = round_trip(None, new)
    assert out.viewoffset[2] == 22.25


def test_stats_mask():
    old = shared.player_state_t()
    new = copy.deepcopy(old)
    new.stats[0], new.stats[31] = 1, 2
    buf = new_buffer()
    player_delta.write_delta(old, new, buf)
    movemsg.MSG_BeginReading(buf)
    flags = movemsg.MSG_ReadShort(buf)
    assert flags == C.PS_WEAPONINDEX
    movemsg.MSG_ReadByte(buf)  # gunindex
    assert movemsg.MSG_ReadLong(buf) == (1 << 0) | (1 << 31)
