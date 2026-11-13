"""The network channel: sequenced packets with one reliable message in flight.

Every packet starts with two 32-bit words: its sequence number and the last
sequence received, each with a flag in the top bit (this packet carries the
reliable message / the reliable bit last received). A client then sends its
qport, so a server can tell clients behind one address apart. A reliable
message is resent in every packet until the other side acknowledges it.

``NetChannel`` is the state and the packet logic; sending, the clock and
debug output belong to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass

from common import movemsg, szone
from common.header import common as common_h

SEQUENCE_MASK = ~(1 << 31)


@dataclass(slots=True)
class Packet:
    """A packet built to send."""

    data: bytes
    reliable: bool            # carries the reliable message
    dumped_unreliable: bool   # the unreliable data didn't fit and was left out


@dataclass(slots=True)
class PacketHeader:
    """What a received packet's header said, for the caller's logging."""

    size: int
    sequence: int
    sequence_ack: int
    reliable_message: bool
    reliable_ack: int
    accepted: bool = False   # False: stale or duplicated
    dropped: int = 0         # packets lost before it


class NetChannel:
    """One end of a connection (the C's netchan_t)."""

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.fatal_error = False
        self.sock = common_h.netsrc_t.NS_CLIENT
        self.dropped = 0              # between the last packet and the one before
        self.last_received = 0        # for timeouts
        self.last_sent = 0            # for retransmits
        self.remote_address = common_h.netadr_t()
        self.qport = 0                # the qport this end writes (as a client)

        # sequencing
        self.incoming_sequence = 0
        self.incoming_acknowledged = 0
        self.incoming_reliable_acknowledged = 0  # single bit
        self.incoming_reliable_sequence = 0      # single bit, maintained here
        self.outgoing_sequence = 0
        self.reliable_sequence = 0               # single bit
        self.last_reliable_sequence = 0          # sequence of the last reliable send

        # reliable staging and holding areas
        self.message = common_h.sizebuf_t()      # the reliable data being written
        self.reliable_length = 0
        self.reliable_buf = bytearray()          # the reliable message awaiting ack

    def setup(self, sock: common_h.netsrc_t, address: common_h.netadr_t, qport: int,
              now: int) -> None:
        """Open the channel to a remote address."""
        self.clear()
        self.sock = sock
        self.remote_address = address
        self.qport = qport
        self.last_received = now
        self.incoming_sequence = 0
        self.outgoing_sequence = 1
        szone.SZ_Init(self.message, common_h.MAX_MSGLEN)
        self.message.allowoverflow = True

    def can_reliable(self) -> bool:
        """Whether the last reliable message has been acknowledged."""
        return not self.reliable_length

    def need_reliable(self) -> bool:
        """Whether the next packet must carry the reliable message."""
        # the other side dropped the last reliable message: resend it
        if (self.incoming_acknowledged > self.last_reliable_sequence
                and self.incoming_reliable_acknowledged != self.reliable_sequence):
            return True
        # or there is new reliable data and nothing in flight
        return not self.reliable_length and bool(self.message.cursize)

    def build_packet(self, data: bytes | bytearray, now: int, qport_value: int) -> Packet | None:
        """The next packet: the header, the reliable message if due, then
        ``data`` if there is room. None when the reliable message overflowed
        (the channel is then broken: fatal_error)."""
        if self.message.overflowed:
            self.fatal_error = True
            return None

        send_reliable = self.need_reliable()
        if not self.reliable_length and self.message.cursize:
            self.reliable_buf = self.message.data
            self.reliable_length = len(self.message.data)
            self.message.data = bytearray()
            self.message.cursize = 0
            self.reliable_sequence ^= 1

        send = common_h.sizebuf_t()
        szone.SZ_Init(send, common_h.MAX_MSGLEN)
        w1 = (self.outgoing_sequence & SEQUENCE_MASK) | (int(send_reliable) << 31)
        w2 = (self.incoming_sequence & SEQUENCE_MASK) | (self.incoming_reliable_sequence << 31)
        self.outgoing_sequence += 1
        self.last_sent = now

        movemsg.MSG_WriteLong(send, w1)
        movemsg.MSG_WriteLong(send, w2)
        if self.sock == common_h.netsrc_t.NS_CLIENT:  # the qport, from a client
            movemsg.MSG_WriteShort(send, qport_value)
        if send_reliable:
            szone.SZ_Write(send, self.reliable_buf)
            self.last_reliable_sequence = self.outgoing_sequence
        fits = send.maxsize - send.cursize >= len(data)
        if fits:
            szone.SZ_Write(send, data)
        return Packet(bytes(send.data), send_reliable, not fits)

    def accept(self, msg: common_h.sizebuf_t, now: int) -> PacketHeader:
        """Read a received packet's header from msg (leaving msg at the
        payload) and update the sequencing. The packet should be used only if
        the result is accepted."""
        movemsg.MSG_BeginReading(msg)
        sequence = movemsg.MSG_ReadLong(msg)
        sequence_ack = movemsg.MSG_ReadLong(msg)
        if self.sock == common_h.netsrc_t.NS_SERVER:  # a server reads the qport
            movemsg.MSG_ReadShort(msg)

        header = PacketHeader(msg.cursize, sequence & SEQUENCE_MASK,
                              sequence_ack & SEQUENCE_MASK, bool(sequence >> 31),
                              sequence_ack >> 31)
        # discard stale or duplicated packets
        if header.sequence <= self.incoming_sequence:
            return header

        # dropped packets don't keep the message from being used
        self.dropped = header.sequence - (self.incoming_sequence + 1)
        header.dropped = self.dropped

        # the reliable message in flight has been received: make way for the next
        if header.reliable_ack == self.reliable_sequence:
            self.reliable_length = 0

        self.incoming_sequence = header.sequence
        self.incoming_acknowledged = header.sequence_ack
        self.incoming_reliable_acknowledged = header.reliable_ack
        if header.reliable_message:
            self.incoming_reliable_sequence ^= 1
        self.last_received = now
        header.accepted = True
        return header
