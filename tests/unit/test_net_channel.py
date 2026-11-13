import struct

from common import movemsg, szone
from common.header import common as common_h
from common.net_channel import NetChannel

CLIENT, SERVER = common_h.netsrc_t.NS_CLIENT, common_h.netsrc_t.NS_SERVER
QPORT = 1234


def pair() -> tuple[NetChannel, NetChannel]:
    client, server = NetChannel(), NetChannel()
    client.setup(CLIENT, common_h.netadr_t(), QPORT, 0)
    server.setup(SERVER, common_h.netadr_t(), QPORT, 0)
    return client, server


def deliver(packet: bytes, to: NetChannel, now: int = 0):
    msg = common_h.sizebuf_t()
    szone.SZ_Init(msg, common_h.MAX_MSGLEN)
    szone.SZ_Write(msg, packet)
    header = to.accept(msg, now)
    return header, bytes(msg.data[msg.readcount:msg.cursize])


def test_header_layout():
    client, _ = pair()
    packet = client.build_packet(b"data", 5, QPORT)
    w1, w2, qport = struct.unpack_from("<IIh", packet.data)
    assert (w1, w2, qport) == (1, 0, QPORT)  # sequence 1, nothing received, no reliable
    assert packet.data[10:] == b"data"
    assert client.outgoing_sequence == 2 and client.last_sent == 5


def test_server_packets_have_no_qport():
    client, server = pair()
    packet = server.build_packet(b"x", 0, QPORT)
    assert len(packet.data) == 8 + 1
    header, payload = deliver(packet.data, client)
    assert header.accepted and payload == b"x"


def test_reliable_message_and_ack():
    client, server = pair()
    szone.SZ_Write(client.message, b"reliable")
    packet = client.build_packet(b"u", 0, QPORT)
    assert packet.reliable and client.reliable_length == 8
    header, payload = deliver(packet.data, server)
    assert header.reliable_message and payload == b"reliableu"
    assert server.incoming_reliable_sequence == 1

    # the server's next packet acknowledges it; the client can send a new one
    deliver(server.build_packet(b"", 0, QPORT).data, client)
    assert client.can_reliable()


def test_lost_reliable_is_resent():
    client, server = pair()
    szone.SZ_Write(client.message, b"important")
    client.build_packet(b"", 0, QPORT)  # lost
    # the server's packets acknowledge sequence 0, so the reliable data is still in flight
    deliver(server.build_packet(b"", 0, QPORT).data, client)
    second = client.build_packet(b"", 0, QPORT)
    assert not second.reliable  # not yet: the server hasn't acked anything newer
    header, _ = deliver(second.data, server)
    assert header.dropped == 1
    # last_reliable_sequence is the sequence after the reliable packet (2), so
    # the resend waits for an ack of a later packet without the reliable bit
    deliver(server.build_packet(b"", 0, QPORT).data, client)  # acks 2
    third = client.build_packet(b"", 0, QPORT)
    assert not third.reliable
    deliver(third.data, server)
    deliver(server.build_packet(b"", 0, QPORT).data, client)  # acks 3
    fourth = client.build_packet(b"", 0, QPORT)
    assert fourth.reliable
    _, payload = deliver(fourth.data, server)
    assert payload == b"important"


def test_stale_and_duplicate_packets_are_rejected():
    client, server = pair()
    first = client.build_packet(b"1", 0, QPORT).data
    second = client.build_packet(b"2", 0, QPORT).data
    assert deliver(second, server)[0].accepted
    assert not deliver(first, server)[0].accepted   # older
    assert not deliver(second, server)[0].accepted  # duplicated


def test_unreliable_data_that_does_not_fit_is_dropped():
    client, _ = pair()
    szone.SZ_Write(client.message, bytes(100))
    packet = client.build_packet(bytes(common_h.MAX_MSGLEN - 50), 0, QPORT)
    assert packet.reliable and packet.dumped_unreliable
    assert len(packet.data) == 10 + 100


def test_reliable_overflow_breaks_the_channel():
    client, _ = pair()
    client.message.overflowed = True
    assert client.build_packet(b"", 0, QPORT) is None
    assert client.fatal_error


def test_sequence_words_are_read_unsigned():
    _, server = pair()
    packet = struct.pack("<IIh", (1 << 31) | 7, (1 << 31) | 3, QPORT) + b"p"
    header, payload = deliver(packet, server)
    assert (header.sequence, header.sequence_ack, header.reliable_message,
            header.reliable_ack) == (7, 3, True, 1)
    assert header.dropped == 6 and payload == b"p"
    assert movemsg.MSG_ReadByte  # the payload is left for the caller to read
