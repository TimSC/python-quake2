"""The server's packet entities: a frame's entities as a delta from an older one."""

import numpy as np

# imported the way the game imports the server (through the platform layer)
import backends.unix.system  # noqa: F401
from common import entity_delta, movemsg, szone
from common.header import common as common_h
from common.header import shared
from server import sv_entities

U = common_h


def new_buffer(size: int = 4096) -> common_h.sizebuf_t:
    buf = common_h.sizebuf_t()
    szone.SZ_Init(buf, size)
    return buf


def ent(number: int, x: float = 0.0, model: int = 1) -> shared.entity_state_t:
    s = shared.entity_state_t()
    s.number = number
    s.modelindex = model
    s.origin[:] = (x, 0, 0)
    return s


def write(old, new, baselines=(), maxclients=1, size=4096):
    buf = new_buffer(size)
    sv_entities.write_packet_entities(old, new, buf, list(baselines), maxclients)
    return buf


def read(buf, old):
    """Reads the packet entities as the client does: {number: state}, and the removes."""
    movemsg.MSG_BeginReading(buf)
    assert movemsg.MSG_ReadByte(buf) == U.svc_ops_e.svc_packetentities.value
    states = {s.number: s for s in old}
    removed = []
    while True:
        number, bits = entity_delta.read_bits(buf)
        if not number:
            break
        if bits & U.U_REMOVE:
            removed.append(number)
            del states[number]
            continue
        out = shared.entity_state_t()
        entity_delta.read_delta(states.get(number), out, number, bits, buf)
        states[number] = out
    assert buf.readcount == buf.cursize
    return states, removed


def test_unchanged_frame_is_just_the_end_marker():
    frame = [ent(5), ent(9)]
    buf = write(frame, frame)
    assert bytes(buf.data[:buf.cursize]) == bytes([U.svc_ops_e.svc_packetentities.value, 0, 0])


def test_merge_of_changed_new_and_removed_entities():
    old = [ent(3), ent(5), ent(7, x=1.0)]
    new = [ent(4, x=2.0), ent(5), ent(7, x=8.0), ent(300)]
    states, removed = read(write(old, new), old)
    assert removed == [3]
    assert sorted(states) == [4, 5, 7, 300]
    assert states[7].origin[0] == 8.0
    assert states[4].origin[0] == 2.0


def test_new_entities_start_from_their_baseline():
    baselines = [shared.entity_state_t() for _ in range(10)]
    baselines[6] = ent(6, x=16.0)
    buf_from_baseline = write([], [ent(6, x=16.0)], baselines)
    buf_from_nothing = write([], [ent(6, x=16.0)])
    # the same entity costs less from a baseline that has its origin
    assert buf_from_baseline.cursize < buf_from_nothing.cursize


def test_remove_of_a_high_entity_number():
    buf = new_buffer()
    sv_entities.write_remove(buf, 300)
    assert bytes(buf.data[:buf.cursize]) == bytes(
        [U.U_REMOVE | U.U_MOREBITS1, U.U_NUMBER16 >> 8]) + (300).to_bytes(2, "little")


def test_players_always_get_their_old_origin():
    # an unchanged player still gets an update (the new entity flag), the
    # others none
    frame = [ent(1), ent(2)]
    with_player = write(frame, frame, maxclients=1)
    movemsg.MSG_BeginReading(with_player)
    movemsg.MSG_ReadByte(with_player)
    assert entity_delta.read_bits(with_player)[0] == 1
    assert entity_delta.read_bits(with_player)[0] == 0  # the end: nothing for entity 2


def test_the_list_stops_when_the_message_is_near_full():
    new = [ent(n, x=float(n)) for n in range(1, 400)]
    buf = write([], new, size=common_h.MAX_MSGLEN)
    assert buf.cursize <= common_h.MAX_MSGLEN
    states, _ = read(buf, [])
    assert 0 < len(states) < len(new)
    assert all(np.isclose(s.origin[0], n) for n, s in states.items())
