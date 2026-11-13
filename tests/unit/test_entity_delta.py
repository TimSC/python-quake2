import random
import struct

import numpy as np
import pytest

from common import entity_delta, movemsg, szone
from common.header import common as common_h
from common.header import shared

U = common_h


def new_buffer() -> common_h.sizebuf_t:
    buf = common_h.sizebuf_t()
    szone.SZ_Init(buf, 4096)
    return buf


def state(**values) -> shared.entity_state_t:
    s = shared.entity_state_t()
    for name, value in values.items():
        if name in ("origin", "angles", "old_origin"):
            getattr(s, name)[:] = value
        else:
            setattr(s, name, value)
    return s


def round_trip(from_, to, force=True, new_entity=False):
    buf = new_buffer()
    entity_delta.write_delta(from_, to, buf, force, new_entity)
    assert buf.cursize == entity_delta.delta_size(from_, to, force, new_entity)
    movemsg.MSG_BeginReading(buf)
    number, bits = entity_delta.read_bits(buf)
    out = shared.entity_state_t()
    entity_delta.read_delta(from_, out, number, bits, buf)
    assert buf.readcount == buf.cursize
    return bytes(buf.data[:buf.cursize]), out


def test_origin_change_bytes():
    data, out = round_trip(state(number=5), state(number=5, origin=(1.0, 0, 0)), force=False)
    # bits: ORIGIN1 only (one byte), number 5, x coordinate 1.0 = 8 eighths
    assert data == bytes([U.U_ORIGIN1, 5]) + struct.pack("<h", 8)
    assert out.origin.tolist() == [1.0, 0.0, 0.0]


def test_unchanged_and_not_forced_writes_nothing():
    s = state(number=3, origin=(1, 2, 3))
    buf = new_buffer()
    entity_delta.write_delta(s, s, buf, False, False)
    assert buf.cursize == 0
    assert entity_delta.delta_size(s, s, False, False) == 0


def test_high_numbers():
    data, out = round_trip(None, state(number=300))
    assert out.number == 300
    buf = new_buffer()
    entity_delta.write_delta(None, state(number=40000), buf, True, False)
    assert buf.cursize == 0  # entity numbers are 16-bit


@pytest.mark.parametrize("field, value, bits", [
    ("frame", 10, U.U_FRAME8), ("frame", 300, U.U_FRAME16),
    ("skinnum", 10, U.U_SKIN8), ("skinnum", 300, U.U_SKIN16),
    ("skinnum", 0x12345678, U.U_SKIN8 | U.U_SKIN16), ("skinnum", -1, U.U_SKIN8 | U.U_SKIN16),
    ("effects", 10, U.U_EFFECTS8), ("effects", 0x7FFF, U.U_EFFECTS16),
    ("effects", 0x8000, U.U_EFFECTS8 | U.U_EFFECTS16),
    ("renderfx", 0x10000, U.U_RENDERFX8 | U.U_RENDERFX16),
])
def test_width_of_variable_fields(field, value, bits):
    to = state(number=1, **{field: value})
    assert entity_delta.delta_bits(entity_delta.NULL_STATE, to, False) & bits == bits
    _, out = round_trip(None, to)
    # long fields come back as unsigned 32 bit values (as the port always read them)
    assert getattr(out, field) == value & 0xFFFFFFFF


def test_old_origin_for_new_entities_and_beams():
    to = state(number=1, origin=(8, 8, 8), old_origin=(4, 4, 4))
    assert entity_delta.delta_bits(entity_delta.NULL_STATE, to, True) & U.U_OLDORIGIN
    assert not entity_delta.delta_bits(entity_delta.NULL_STATE, to, False) & U.U_OLDORIGIN
    beam = state(number=1, renderfx=shared.RF_BEAM)
    assert entity_delta.delta_bits(entity_delta.NULL_STATE, beam, False) & U.U_OLDORIGIN


def test_read_starts_from_the_old_state():
    old = state(number=7, origin=(16, 32, 48), modelindex=3, event=2, sound=5)
    new = state(number=7, origin=(16, 32, 64), modelindex=3, sound=5)
    _, out = round_trip(old, new, force=False)
    assert out.modelindex == 3 and out.sound == 5
    assert out.origin.tolist() == [16.0, 32.0, 64.0]
    assert out.old_origin.tolist() == [16.0, 32.0, 48.0]  # the previous origin
    assert out.event == 0  # events are not carried over


def test_random_round_trips():
    rng = random.Random(4)
    for _ in range(500):
        to = state(number=rng.randrange(1, 2000),
                   origin=[rng.randrange(-32768, 32768) / 8 for _ in range(3)],
                   angles=[rng.randrange(256) * 360 / 256 for _ in range(3)],
                   modelindex=rng.randrange(256), frame=rng.randrange(32768),
                   skinnum=rng.randrange(-2**31, 2**31), effects=rng.randrange(2**31),
                   renderfx=rng.randrange(2**31) & ~shared.RF_BEAM,
                   solid=rng.randrange(32768), sound=rng.randrange(256),
                   event=rng.randrange(256))
        _, out = round_trip(None, to, new_entity=False)
        for name in ("number", "modelindex", "frame", "effects", "renderfx", "solid",
                     "sound", "event"):
            assert getattr(out, name) == getattr(to, name), name
        assert out.skinnum == to.skinnum & 0xFFFFFFFF
        assert np.allclose(out.origin, to.origin)
        assert np.allclose(out.angles % 360, to.angles % 360)


def test_malformed_both_frame_bits_reads_byte_then_short():
    buf = new_buffer()
    bits = U.U_FRAME8 | U.U_MOREBITS1 | U.U_MOREBITS2
    for value in (bits & 255, (bits >> 8) & 255, U.U_FRAME16 >> 16 & 255, 9):
        movemsg.MSG_WriteByte(buf, value)
    movemsg.MSG_WriteByte(buf, 77)        # the byte frame, ignored
    movemsg.MSG_WriteShort(buf, 1234)     # the short frame, kept
    movemsg.MSG_BeginReading(buf)
    number, read = entity_delta.read_bits(buf)
    out = shared.entity_state_t()
    entity_delta.read_delta(None, out, number, read, buf)
    assert (number, out.frame) == (9, 1234)


def test_read_without_a_target():
    buf = new_buffer()
    entity_delta.write_delta(None, state(number=2, modelindex=4), buf, True, False)
    movemsg.MSG_BeginReading(buf)
    number, bits = entity_delta.read_bits(buf)
    entity_delta.read_delta(None, None, number, bits, buf)
    assert buf.readcount == buf.cursize
