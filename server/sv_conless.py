"""Connectionless server packets (Yamagi's sv_conless.c).

A connectionless packet starts with four 0xff bytes instead of a channel
sequence. Its text is one command line: a server browser's ``info`` or
``status``, a client's ``getchallenge`` and ``connect``, ``ping``/``ack``,
or ``rcon``. Clients already in the game can still send them.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backends.unix import network
from common import clientserver, cmdparser, frame, movemsg, netchan
from common.header import common as common_h
from common.header import shared
from common.shared import rand
from common.shared import shared as shared_c
from server import sv_init, sv_main, sv_send
from server.header import server as server_h

PROTOCOL_VERSION = common_h.PROTOCOL_VERSION
INFO_REPLY_SIZE = 64  # the C's char string[64]
RCON_COMMAND_SIZE = 1024  # the C's char remaining[1024]


@dataclass(slots=True)
class Request:
    """One connectionless packet: where it came from and its arguments."""

    adr: common_h.netadr_t
    args: list[str]
    line: str  # the whole command line
    packet_text: str  # the packet after the 0xff marker, up to a NUL

    def arg(self, i: int) -> str:
        return self.args[i] if i < len(self.args) else ""

    def int_arg(self, i: int) -> int:
        """An argument as a number, as the C's strtol(): 0 if it isn't one."""
        return shared_c.atoi(self.arg(i))

    def reply(self, text: str) -> None:
        netchan.Netchan_OutOfBandPrint(common_h.netsrc_t.NS_SERVER, self.adr, text)


def info_line(hostname: str, mapname: str, clients: int, maxclients: int) -> str:
    """The reply to a server browser's ``info``, as the C's 64 byte sprintf."""
    line = f"{hostname:>16} {mapname:>8} {clients:2}/{maxclients:2}\n"
    return line[:INFO_REPLY_SIZE - 1]


def find_challenge(challenges: list, adr, same_address: Callable) -> int | None:
    """The index of the challenge given to adr, if there is one."""
    for i, ch in enumerate(challenges):
        if same_address(adr, ch.adr):
            return i
    return None


def issue_challenge(challenges: list, adr, now: int, same_address: Callable,
                    new_number: Callable[[], int]) -> int:
    """The challenge number for adr: its old one, or a new one in the oldest slot."""
    i = find_challenge(challenges, adr, same_address)
    if i is None:
        i = min(range(len(challenges)), key=lambda k: challenges[k].time)
        if challenges[i].time >= 0x7fffffff:
            i = 0  # the C only takes a slot older than 0x7fffffff
        challenges[i].challenge = new_number() & 0x7fff
        challenges[i].adr = adr
        challenges[i].time = now
    return challenges[i].challenge


def check_challenge(challenges: list, adr, challenge: int, same_address: Callable) -> str | None:
    """Why a connect with this challenge is refused, or None if it is good."""
    i = find_challenge(challenges, adr, same_address)
    if i is None:
        return "No challenge for address."
    if challenges[i].challenge != challenge:
        return "Bad challenge."
    return None


def rcon_command(args: list[str]) -> str:
    """The command an rcon packet runs: its arguments after the password."""
    text = "".join(arg + " " for arg in args[2:])
    return text[:RCON_COMMAND_SIZE - 1]


def _maxclients() -> int:
    return int(sv_main.maxclients.value)


def _status(req: Request) -> None:
    """Everything qplug or qspy can see: the server info and the players."""
    req.reply("print\n" + sv_main.SV_StatusString())


def _ack(req: Request) -> None:
    clientserver.Com_Printf(f"Ping acknowledge from {network.NET_AdrToString(req.adr)}\n")


def _info(req: Request) -> None:
    """Short info for broadcast scans; the argument is the protocol version."""
    if _maxclients() == 1:
        return  # ignore in single player

    if req.int_arg(1) != PROTOCOL_VERSION:
        text = f"{sv_main.hostname.string}: wrong version\n"[:INFO_REPLY_SIZE - 1]
    else:
        clients = sv_init.svs.clients[:_maxclients()]
        count = sum(cl.state.value >= server_h.client_state_t.cs_connected.value for cl in clients)
        text = info_line(sv_main.hostname.string, sv_init.sv.name, count, _maxclients())
    req.reply("info\n" + text)


def _ping(req: Request) -> None:
    req.reply("ack")


def _get_challenge(req: Request) -> None:
    """A challenge number for a later ``connect``.

    It makes a client prove its address, against floods of connects from
    forged ones.
    """
    number = issue_challenge(sv_init.svs.challenges, req.adr, frame.curtime,
                             network.NET_CompareBaseAdr, rand.randk)
    req.reply(f"challenge {number} p=34")


def _direct_connect(req: Request) -> None:
    """A client's connect request (not through a master server)."""
    adr = req.adr
    clientserver.Com_DPrintf("SVC_DirectConnect ()\n")

    version = req.int_arg(1)
    if version != PROTOCOL_VERSION:
        req.reply("print\nServer is protocol version 34.\n")
        clientserver.Com_DPrintf(f"    rejected connect from version {version}\n")
        return

    qport = req.int_arg(2)
    challenge = req.int_arg(3)
    userinfo = req.arg(4)[:shared.MAX_INFO_STRING - 1]

    # the IP, so the game can filter by it
    userinfo = shared_c.Info_SetValueForKey(userinfo, "ip", network.NET_AdrToString(adr))

    local = network.NET_IsLocalAddress(adr)
    if sv_init.sv.attractloop and not local:
        # demo and cinematic servers are only for local clients
        clientserver.Com_Printf("Remote connect in attract loop.  Ignored.\n")
        req.reply("print\nConnection refused.\n")
        return

    if not local:
        refused = check_challenge(sv_init.svs.challenges, adr, challenge,
                                  network.NET_CompareBaseAdr)
        if refused:
            req.reply(f"print\n{refused}\n")
            return

    clients = sv_init.svs.clients[:_maxclients()]

    # a client reconnecting from the same address and port gets its slot back
    for cl in clients:
        if cl.state.value < server_h.client_state_t.cs_connected.value:
            continue
        remote = cl.netchan.remote_address
        if (network.NET_CompareBaseAdr(adr, remote)
                and (cl.netchan.qport == qport or adr.port == remote.port)):
            if not local:
                clientserver.Com_DPrintf(
                    f"{network.NET_AdrToString(adr)}:reconnect rejected : too soon\n")
                return
            clientserver.Com_Printf(f"{network.NET_AdrToString(adr)}:reconnect\n")
            sv_main.SVC_DirectConnect_NewClient(cl, adr, qport, userinfo, challenge)
            return

    newcl = next((cl for cl in clients if cl.state == server_h.client_state_t.cs_free), None)
    if newcl is None:
        req.reply("print\nServer is full.\n")
        clientserver.Com_DPrintf("Rejected a connection.\n")
        return

    sv_main.SVC_DirectConnect_NewClient(newcl, adr, qport, userinfo, challenge)


def _rcon_valid(req: Request) -> bool:
    password = sv_main.rcon_password.string
    return bool(password) and req.arg(1) == password


def _remote_command(req: Request) -> None:
    """An rcon command: run it, and send its console output back."""
    valid = _rcon_valid(req)
    who = network.NET_AdrToString(req.adr)
    clientserver.Com_Printf("{} from {}:\n{}\n".format(
        "Rcon" if valid else "Bad rcon", who, req.packet_text))

    clientserver.Com_BeginRedirect(server_h.redirect_t.RD_PACKET.value, sv_send.output_buffer,
                                   server_h.SV_OUTPUTBUF_LENGTH, sv_send.flush_redirect)
    if not valid:
        clientserver.Com_Printf("Bad rcon_password.\n")
    else:
        cmdparser.Cmd_ExecuteString(rcon_command(req.args))
    clientserver.Com_EndRedirect()


COMMANDS: dict[str, Callable[[Request], None]] = {
    "ping": _ping,
    "ack": _ack,
    "status": _status,
    "info": _info,
    "getchallenge": _get_challenge,
    "connect": _direct_connect,
    "rcon": _remote_command,
}


def SV_ConnectionlessPacket() -> None:  # noqa: N802
    """Handles the connectionless packet in net_message, from net_from."""
    msg = netchan.net_message
    movemsg.MSG_BeginReading(msg)
    movemsg.MSG_ReadLong(msg)  # the -1 marker

    line = movemsg.MSG_ReadStringLine(msg)
    cmdparser.Cmd_TokenizeString(line, False)
    args = [cmdparser.Cmd_Argv(i) for i in range(cmdparser.Cmd_Argc())]

    # the packet as the C string rcon prints; untrusted, so latin-1
    packet_text = bytes(msg.data[4:msg.cursize]).split(b"\0", 1)[0].decode("latin-1")
    req = Request(netchan.net_from, args, line, packet_text)

    name = req.arg(0)
    clientserver.Com_DPrintf(f"Packet {network.NET_AdrToString(req.adr)} : {name}\n")

    handler = COMMANDS.get(name)
    if handler is None:
        who = network.NET_AdrToString(req.adr)
        clientserver.Com_Printf(f"bad connectionless packet from {who}:\n{line}\n")
        return
    handler(req)
