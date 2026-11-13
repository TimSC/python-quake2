"""Player state deltas (svc_playerinfo, protocol 34), driven by one table.

A 16-bit flag word says which groups of fields follow; then come the stats
that changed, as a 32-bit mask and a short each. ``GROUPS`` lists the groups
in wire order, so the server's writer and the client's reader share it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from common import movemsg
from common.header import common as common_h
from common.header import shared

C = common_h


@dataclass(frozen=True, slots=True)
class Wire:
    """How a value goes over the wire: write(msg, encode(value)), decode(read(msg))."""

    write: Callable
    read: Callable
    encode: Callable[[float], int | float]
    decode: Callable[[int | float], int | float]


def _identity(value):
    return value


# The movemsg functions are looked up when called: movemsg may still be
# importing when this module is.
def _byte_io() -> tuple[Callable, Callable]:
    return (lambda msg, v: movemsg.MSG_WriteByte(msg, v), lambda msg: movemsg.MSG_ReadByte(msg))


BYTE = Wire(*_byte_io(), int, _identity)
SHORT = Wire(lambda msg, v: movemsg.MSG_WriteShort(msg, v),
             lambda msg: movemsg.MSG_ReadShort(msg), int, _identity)
QUARTER = Wire(lambda msg, v: movemsg.MSG_WriteChar(msg, v),  # a char in quarter units
               lambda msg: movemsg.MSG_ReadChar(msg), lambda v: int(v * 4), lambda v: v * 0.25)
ANGLE16 = Wire(lambda msg, v: movemsg.MSG_WriteAngle16(msg, v),
               lambda msg: movemsg.MSG_ReadAngle16(msg), _identity, _identity)
COLOUR = Wire(*_byte_io(), lambda v: int(v * 255), lambda v: v / 255.0)  # 0..1 as a byte
FOV = Wire(*_byte_io(), int, float)


def _vector(path: tuple[str, ...], wire: Wire, size: int = 3) -> list[tuple]:
    return [(path, i, wire) for i in range(size)]


@dataclass(frozen=True, slots=True)
class Group:
    flag: int
    fields: tuple[tuple[tuple[str, ...], int | None, Wire], ...]  # (attribute path, index, wire)
    always: bool = False  # sent every time (the weapon model)


GROUPS: tuple[Group, ...] = (
    Group(C.PS_M_TYPE, ((("pmove", "pm_type"), None, BYTE),)),
    Group(C.PS_M_ORIGIN, tuple(_vector(("pmove", "origin"), SHORT))),
    Group(C.PS_M_VELOCITY, tuple(_vector(("pmove", "velocity"), SHORT))),
    Group(C.PS_M_TIME, ((("pmove", "pm_time"), None, BYTE),)),
    Group(C.PS_M_FLAGS, ((("pmove", "pm_flags"), None, BYTE),)),
    Group(C.PS_M_GRAVITY, ((("pmove", "gravity"), None, SHORT),)),
    Group(C.PS_M_DELTA_ANGLES, tuple(_vector(("pmove", "delta_angles"), SHORT))),
    Group(C.PS_VIEWOFFSET, tuple(_vector(("viewoffset",), QUARTER))),
    Group(C.PS_VIEWANGLES, tuple(_vector(("viewangles",), ANGLE16))),
    Group(C.PS_KICKANGLES, tuple(_vector(("kick_angles",), QUARTER))),
    Group(C.PS_WEAPONINDEX, ((("gunindex",), None, BYTE),), always=True),
    Group(C.PS_WEAPONFRAME, ((("gunframe",), None, BYTE),
                             *_vector(("gunoffset",), QUARTER),
                             *_vector(("gunangles",), QUARTER))),
    Group(C.PS_BLEND, tuple(_vector(("blend",), COLOUR, 4))),
    Group(C.PS_FOV, ((("fov",), None, FOV),)),
    Group(C.PS_RDFLAGS, ((("rdflags",), None, BYTE),)),
)


def _owner(state: shared.player_state_t, path: tuple[str, ...]):
    """The object holding the last attribute of ``path``."""
    for name in path[:-1]:
        state = getattr(state, name)
    return state


def _get(state: shared.player_state_t, path: tuple[str, ...], index: int | None):
    value = getattr(_owner(state, path), path[-1])
    return value if index is None else value[index]


def _set(state: shared.player_state_t, path: tuple[str, ...], index: int | None,
         value) -> None:
    owner = _owner(state, path)
    if index is None:
        setattr(owner, path[-1], value)
    else:
        getattr(owner, path[-1])[index] = value


def delta_flags(from_: shared.player_state_t, to: shared.player_state_t) -> int:
    """The groups to send ``to`` as a change from ``from_``."""
    flags = 0
    for group in GROUPS:
        if group.always or any(_get(to, path, index) != _get(from_, path, index)
                               for path, index, _ in group.fields):
            flags |= group.flag
    return flags


def write_delta(from_: shared.player_state_t | None, to: shared.player_state_t,
                msg: common_h.sizebuf_t) -> None:
    """Write the flags, the changed groups and the changed stats."""
    from_ = shared.player_state_t() if from_ is None else from_
    flags = delta_flags(from_, to)
    movemsg.MSG_WriteShort(msg, flags)
    for group in GROUPS:
        if flags & group.flag:
            for path, index, wire in group.fields:
                wire.write(msg, wire.encode(_get(to, path, index)))

    statbits = 0
    for i in range(shared.MAX_STATS):
        if to.stats[i] != from_.stats[i]:
            statbits |= 1 << i
    movemsg.MSG_WriteLong(msg, statbits)
    for i in range(shared.MAX_STATS):
        if statbits & (1 << i):
            movemsg.MSG_WriteShort(msg, to.stats[i])


def read_delta(msg: common_h.sizebuf_t, state: shared.player_state_t) -> int:
    """Apply a delta to ``state`` (already holding the old state); returns the flags."""
    flags = movemsg.MSG_ReadShort(msg)
    for group in GROUPS:
        if flags & group.flag:
            for path, index, wire in group.fields:
                _set(state, path, index, wire.decode(wire.read(msg)))

    statbits = movemsg.MSG_ReadLong(msg)
    for i in range(shared.MAX_STATS):
        if statbits & (1 << i):
            state.stats[i] = movemsg.MSG_ReadShort(msg)
    return flags
