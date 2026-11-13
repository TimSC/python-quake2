"""Entity state deltas (protocol 34), driven by one table.

The server sends each entity as the fields that changed since a previous
state; a bit mask (1 to 4 bytes) says which fields follow, and in some cases
how wide they are. ``FIELDS`` lists the fields in wire order with their
encodings, and ``delta_bits``, ``delta_size``, ``write_delta`` and
``read_delta`` all work from it, so the writer and the reader can't disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from common import movemsg
from common.header import common as common_h
from common.header import shared

U = common_h

# Wire encodings: name -> (size in bytes, write, read).
BYTE, SHORT, LONG, COORD, ANGLE = "byte", "short", "long", "coord", "angle"
# Both frame bits (never written; a reader takes a byte, then the short that wins).
BYTE_SHORT = "byte+short"


def _read_byte_short(msg: common_h.sizebuf_t) -> int:
    movemsg.MSG_ReadByte(msg)
    return movemsg.MSG_ReadShort(msg)


# The movemsg functions are looked up when called: movemsg may still be
# importing when this module is.
ENCODINGS: dict[str, tuple[int, Callable | None, Callable]] = {
    BYTE: (1, lambda msg, v: movemsg.MSG_WriteByte(msg, v),
           lambda msg: movemsg.MSG_ReadByte(msg)),
    SHORT: (2, lambda msg, v: movemsg.MSG_WriteShort(msg, v),
            lambda msg: movemsg.MSG_ReadShort(msg)),
    LONG: (4, lambda msg, v: movemsg.MSG_WriteLong(msg, v),
           lambda msg: movemsg.MSG_ReadLong(msg)),
    COORD: (2, lambda msg, v: movemsg.MSG_WriteCoord(msg, v),
            lambda msg: movemsg.MSG_ReadCoord(msg)),
    ANGLE: (1, lambda msg, v: movemsg.MSG_WriteAngle(msg, v),
            lambda msg: movemsg.MSG_ReadAngle(msg)),
    BYTE_SHORT: (3, None, _read_byte_short),
}


def _always(bits: int) -> Callable[[int], int]:
    return lambda value: bits


def _frame_bits(value: int) -> int:
    return U.U_FRAME8 if value < 256 else U.U_FRAME16


def _skin_bits(value: int) -> int:
    unsigned = value & 0xFFFFFFFF
    if unsigned < 256:
        return U.U_SKIN8
    if unsigned < 0x10000:
        return U.U_SKIN16
    return U.U_SKIN8 | U.U_SKIN16


def _wide_bits(bits8: int, bits16: int) -> Callable[[int], int]:
    """effects and renderfx: a byte, a (signed) short, or a long."""
    def choose(value: int) -> int:
        if value < 256:
            return bits8
        if value < 0x8000:
            return bits16
        return bits8 | bits16
    return choose


@dataclass(frozen=True, slots=True)
class Field:
    """One delta-compressed field of entity_state_t."""

    attr: str
    index: int | None                   # element of a vector attribute
    mask: int                           # the update bits this field uses
    encodings: dict[int, str]           # (bits & mask) -> encoding
    choose_bits: Callable[[int], int]   # the bits to send a new value with


def _variable(attr: str, bits8: int, bits16: int, choose: Callable[[int], int],
              both: str | None) -> Field:
    encodings = {bits8: BYTE, bits16: SHORT}
    if both is not None:
        encodings[bits8 | bits16] = both
    return Field(attr, None, bits8 | bits16, encodings, choose)


def _simple(attr: str, index: int | None, bits: int, encoding: str) -> Field:
    return Field(attr, index, bits, {bits: encoding}, _always(bits))


# The delta-compressed fields, in the order they are written.
FIELDS: tuple[Field, ...] = (
    _simple("modelindex", None, U.U_MODEL, BYTE),
    _simple("modelindex2", None, U.U_MODEL2, BYTE),
    _simple("modelindex3", None, U.U_MODEL3, BYTE),
    _simple("modelindex4", None, U.U_MODEL4, BYTE),
    _variable("frame", U.U_FRAME8, U.U_FRAME16, _frame_bits, BYTE_SHORT),
    _variable("skinnum", U.U_SKIN8, U.U_SKIN16, _skin_bits, LONG),  # long: laser colours
    _variable("effects", U.U_EFFECTS8, U.U_EFFECTS16,
              _wide_bits(U.U_EFFECTS8, U.U_EFFECTS16), LONG),
    _variable("renderfx", U.U_RENDERFX8, U.U_RENDERFX16,
              _wide_bits(U.U_RENDERFX8, U.U_RENDERFX16), LONG),
    _simple("origin", 0, U.U_ORIGIN1, COORD),
    _simple("origin", 1, U.U_ORIGIN2, COORD),
    _simple("origin", 2, U.U_ORIGIN3, COORD),
    _simple("angles", 0, U.U_ANGLE1, ANGLE),
    _simple("angles", 1, U.U_ANGLE2, ANGLE),
    _simple("angles", 2, U.U_ANGLE3, ANGLE),
)

# Written after FIELDS, in this order; old_origin is three coordinates.
TAIL_SIZES = ((U.U_OLDORIGIN, 6), (U.U_SOUND, 1), (U.U_EVENT, 1), (U.U_SOLID, 2))

NULL_STATE = shared.entity_state_t()


def _get(state: shared.entity_state_t, field: Field):
    value = getattr(state, field.attr)
    return value if field.index is None else value[field.index]


def delta_bits(from_: shared.entity_state_t, to: shared.entity_state_t,
               new_entity: bool) -> int:
    """The update bits to send ``to`` as a change from ``from_``."""
    bits = U.U_NUMBER16 if to.number >= 256 else 0  # number8 is implicit otherwise
    for field in FIELDS:
        value = _get(to, field)
        if value != _get(from_, field):
            bits |= field.choose_bits(value)
    if to.solid != from_.solid:
        bits |= U.U_SOLID
    if to.event:  # the event is not delta compressed, just 0 compressed
        bits |= U.U_EVENT
    if to.sound != from_.sound:
        bits |= U.U_SOUND
    if new_entity or (to.renderfx & shared.RF_BEAM):
        bits |= U.U_OLDORIGIN

    if bits & 0xFF000000:
        bits |= U.U_MOREBITS3 | U.U_MOREBITS2 | U.U_MOREBITS1
    elif bits & 0x00FF0000:
        bits |= U.U_MOREBITS2 | U.U_MOREBITS1
    elif bits & 0x0000FF00:
        bits |= U.U_MOREBITS1
    return bits


def _bit_bytes(bits: int) -> int:
    if bits & 0xFF000000:
        return 4
    if bits & 0x00FF0000:
        return 3
    if bits & 0x0000FF00:
        return 2
    return 1


def delta_size(from_: shared.entity_state_t | None, to: shared.entity_state_t | None,
               force: bool, new_entity: bool) -> int:
    """The bytes ``write_delta`` would write (0 when nothing would be sent)."""
    from_ = NULL_STATE if from_ is None else from_
    to = NULL_STATE if to is None else to
    bits = delta_bits(from_, to, new_entity)
    if not bits and not force:
        return 0
    size = _bit_bytes(bits) + (2 if bits & U.U_NUMBER16 else 1)
    for field in FIELDS:
        selected = bits & field.mask
        if selected:
            size += ENCODINGS[field.encodings[selected]][0]
    for bit, field_size in TAIL_SIZES:
        if bits & bit:
            size += field_size
    return size


def write_delta(from_: shared.entity_state_t | None, to: shared.entity_state_t | None,
                msg: common_h.sizebuf_t, force: bool, new_entity: bool) -> None:
    """Write ``to`` as a delta from ``from_`` (nothing if unchanged and not forced)."""
    from_ = NULL_STATE if from_ is None else from_
    to = NULL_STATE if to is None else to
    if to.number > 32767:  # entity numbers are sent in 16-bit form
        return
    bits = delta_bits(from_, to, new_entity)
    if not bits and not force:
        return  # nothing to send

    write_byte = movemsg.MSG_WriteByte
    for i in range(_bit_bytes(bits)):
        write_byte(msg, (bits >> (8 * i)) & 255)
    if bits & U.U_NUMBER16:
        movemsg.MSG_WriteShort(msg, to.number)
    else:
        write_byte(msg, to.number)

    for field in FIELDS:
        selected = bits & field.mask
        if selected:
            ENCODINGS[field.encodings[selected]][1](msg, _get(to, field))

    if bits & U.U_OLDORIGIN:
        for i in range(3):
            movemsg.MSG_WriteCoord(msg, to.old_origin[i])
    if bits & U.U_SOUND:
        write_byte(msg, to.sound)
    if bits & U.U_EVENT:
        write_byte(msg, to.event)
    if bits & U.U_SOLID:
        movemsg.MSG_WriteShort(msg, to.solid)


def read_bits(msg: common_h.sizebuf_t) -> tuple[int, int]:
    """Read the update bits and the entity number: (number, bits)."""
    read_byte = movemsg.MSG_ReadByte
    bits = read_byte(msg)
    if bits & U.U_MOREBITS1:
        bits |= read_byte(msg) << 8
    if bits & U.U_MOREBITS2:
        bits |= read_byte(msg) << 16
    if bits & U.U_MOREBITS3:
        bits |= read_byte(msg) << 24
    number = movemsg.MSG_ReadShort(msg) if bits & U.U_NUMBER16 else read_byte(msg)
    return number, bits


def read_delta(from_: shared.entity_state_t | None, to: shared.entity_state_t | None,
               number: int, bits: int, msg: common_h.sizebuf_t) -> None:
    """Read a delta into ``to``: ``from_`` (or the null state) plus the changes.

    old_origin starts as from_'s origin, and the event is cleared unless sent.
    With no ``to`` the delta is read and dropped.
    """
    from_ = NULL_STATE if from_ is None else from_
    to = shared.entity_state_t() if to is None else to
    to.copy(from_)
    shared.VectorCopy(from_.origin, to.old_origin)
    to.number = number

    for field in FIELDS:
        selected = bits & field.mask
        if selected:
            value = ENCODINGS[field.encodings[selected]][2](msg)
            if field.index is None:
                setattr(to, field.attr, value)
            else:
                getattr(to, field.attr)[field.index] = value

    if bits & U.U_OLDORIGIN:
        movemsg.MSG_ReadPos(msg, to.old_origin)
    if bits & U.U_SOUND:
        to.sound = movemsg.MSG_ReadByte(msg)
    to.event = movemsg.MSG_ReadByte(msg) if bits & U.U_EVENT else 0
    if bits & U.U_SOLID:
        to.solid = movemsg.MSG_ReadShort(msg)
