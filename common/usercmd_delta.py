"""User command deltas (clc_move, protocol 34), driven by one table.

A byte of bits says which fields changed since the previous command; msec and
the light level follow every time.
"""

from __future__ import annotations

from common import movemsg
from common.header import common as common_h
from common.header import shared

C = common_h

# (attribute, index into it, bit, wire size in bytes) in wire order.
FIELDS: tuple[tuple[str, int | None, int, int], ...] = (
    ("angles", 0, C.CM_ANGLE1, 2),
    ("angles", 1, C.CM_ANGLE2, 2),
    ("angles", 2, C.CM_ANGLE3, 2),
    ("forwardmove", None, C.CM_FORWARD, 2),
    ("sidemove", None, C.CM_SIDE, 2),
    ("upmove", None, C.CM_UP, 2),
    ("buttons", None, C.CM_BUTTONS, 1),
    ("impulse", None, C.CM_IMPULSE, 1),
)
ALWAYS = ("msec", "lightlevel")  # bytes, sent every time
COPIED = ("msec", "buttons", "forwardmove", "sidemove", "upmove", "impulse", "lightlevel")


def _get(cmd: shared.usercmd_t, attr: str, index: int | None) -> int:
    value = getattr(cmd, attr)
    return value if index is None else value[index]


def write_delta(msg: common_h.sizebuf_t, from_: shared.usercmd_t,
                cmd: shared.usercmd_t) -> None:
    bits = 0
    for attr, index, bit, _ in FIELDS:
        if _get(cmd, attr, index) != _get(from_, attr, index):
            bits |= bit
    movemsg.MSG_WriteByte(msg, bits)
    for attr, index, bit, size in FIELDS:
        if bits & bit:
            write = movemsg.MSG_WriteShort if size == 2 else movemsg.MSG_WriteByte
            write(msg, _get(cmd, attr, index))
    for attr in ALWAYS:
        movemsg.MSG_WriteByte(msg, getattr(cmd, attr))


def read_delta(msg: common_h.sizebuf_t, from_: shared.usercmd_t,
               move: shared.usercmd_t) -> None:
    """Read a command into ``move``: ``from_`` plus the changes.

    The byte fields are masked to 0..255, as the C's byte fields store them
    (reading past the end of the message gives -1).
    """
    for attr in COPIED:
        setattr(move, attr, getattr(from_, attr))
    move.angles[:] = from_.angles[:]

    bits = movemsg.MSG_ReadByte(msg)
    for attr, index, bit, size in FIELDS:
        if bits & bit:
            value = movemsg.MSG_ReadShort(msg) if size == 2 else movemsg.MSG_ReadByte(msg) & 0xFF
            if index is None:
                setattr(move, attr, value)
            else:
                getattr(move, attr)[index] = value
    for attr in ALWAYS:
        setattr(move, attr, movemsg.MSG_ReadByte(msg) & 0xFF)
