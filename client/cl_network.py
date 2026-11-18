"""The client's connection to a server (Yamagi's cl_network.c).

Connecting (``connect``: getchallenge, then connect, then the server's
client_connect), reconnecting and disconnecting, forwarding commands to the
server, rcon and raw packets, pinging for servers, and reading the packets
that arrive: connectionless ones (``CONNECTIONLESS``) and the server's.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import struct
import traceback
from collections.abc import Callable

from backends.unix import network, system
from client import cl_cin, cl_keyboard, cl_main, cl_parse, cl_screen
from client.curl import download
from client.header import client as client_h
from client.menu import menu
from client.sound import ogg
from client.sound import sound as sound_c
from client.vid import vid
from common import clientserver, cmdparser, cvar, errors, frame, movemsg, netchan, szone
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from server import sv_main

CA = client_h.connstate_t
NS_CLIENT = common_h.netsrc_t.NS_CLIENT
STRINGCMD = common_h.clc_ops_e.clc_stringcmd.value
DEFAULT_PORT = shared_c.BigShort(struct.pack("=H", common_h.PORT_SERVER))  # in network order
RESEND_MS = 3000


def _encode(text: str) -> bytes:
    # the C's strings are bytes; latin-1 keeps each one
    return text.encode("latin-1", "replace")


def _cls():
    return cl_main.cls


def _address(text: str) -> common_h.netadr_t | None:
    """A server address, on Quake II's port unless it names one."""
    adr = network.NET_StringToAdr(text)
    if adr is not None and not adr.port:
        adr.port = DEFAULT_PORT
    return adr


def _write_stringcmd(text: str) -> None:
    msg = _cls().netchan.message
    movemsg.MSG_WriteByte(msg, STRINGCMD)
    movemsg.MSG_WriteString(msg, text)


def forward_to_server() -> None:
    """Sends a command the client doesn't know to the server."""
    cls = _cls()
    name = cmdparser.Cmd_Argv(0)
    if cls.state.value <= CA.ca_connected.value or name[:1] in ("-", "+"):
        clientserver.Com_Printf(f'Unknown command "{name}"\n')
        return

    msg = cls.netchan.message
    movemsg.MSG_WriteByte(msg, STRINGCMD)
    szone.SZ_Print(msg, name)
    if cmdparser.Cmd_Argc() > 1:
        szone.SZ_Print(msg, " ")
        szone.SZ_Print(msg, cmdparser.Cmd_Args())


def _cmd_command() -> None:
    """``cmd ...``: sends the rest of the line to the server."""
    cls = _cls()
    if cls.state not in (CA.ca_connected, CA.ca_active):
        clientserver.Com_Printf(f'Can\'t "{cmdparser.Cmd_Argv(0)}", not connected\n')
        return
    if cmdparser.Cmd_Argc() > 1:  # not the command itself
        movemsg.MSG_WriteByte(cls.netchan.message, STRINGCMD)
        szone.SZ_Print(cls.netchan.message, cmdparser.Cmd_Args())


def drop() -> None:
    """Disconnects after an ERR_DROP."""
    cls = _cls()
    if cls.state in (CA.ca_uninitialized, CA.ca_disconnected):
        return
    disconnect()
    # drop the loading plaque, unless this is the game's first start
    if cls.disable_servercount != -1:
        cl_screen.SCR_EndLoadingPlaque()


def _send_connect_packet() -> None:
    """We have the server's challenge: ask to connect."""
    cls = _cls()
    adr = _address(cls.servername)
    if adr is None:
        clientserver.Com_Printf("Bad server address\n")
        cls.connect_time = 0
        return

    qport = int(cvar.Cvar_VariableValue("qport"))
    cvar.registry.userinfo_modified = False
    request = (f"connect {common_h.PROTOCOL_VERSION:d} {qport:d} {cls.challenge:d} "
               f'"{cvar.Cvar_Userinfo()}"\n')
    netchan.Netchan_OutOfBandPrint(NS_CLIENT, adr, request)


def check_for_resend() -> None:
    """Connects to a local server, or asks the server for a challenge again."""
    cls = _cls()
    if cls.state == CA.ca_disconnected and clientserver.Com_ServerState():
        # a local server is running and we aren't in it; no challenge needed
        cls.state = CA.ca_connecting
        cls.servername = "localhost"
        _send_connect_packet()
        return

    if cls.state != CA.ca_connecting or cls.realtime - cls.connect_time < RESEND_MS:
        return

    adr = _address(cls.servername)
    if adr is None:
        clientserver.Com_Printf("Bad server address\n")
        cls.state = CA.ca_disconnected
        return

    cls.connect_time = cls.realtime
    clientserver.Com_Printf(f"Connecting to {cls.servername}...\n")
    netchan.Netchan_OutOfBandPrint(NS_CLIENT, adr, "getchallenge\n")


def _connect_command() -> None:
    """``connect <server>``."""
    if cmdparser.Cmd_Argc() != 2:
        clientserver.Com_Printf("usage: connect <server>\n")
        return

    if clientserver.Com_ServerState():
        # a local server stops first (this is how saved games reconnect)
        sv_main.SV_Shutdown("Server quit\n", False)

    network.NET_Config(True)  # allow remote
    disconnect()
    cls = _cls()
    cls.state = CA.ca_connecting
    cls.servername = cmdparser.Cmd_Argv(1)
    cls.connect_time = -99999  # check_for_resend() fires at once


def _rcon_command() -> None:
    """``rcon ...``: sends the rest of the line to a server, with rcon_password."""
    password = cl_main.rcon_client_password.string
    if password is None:
        clientserver.Com_Printf("You must set 'rcon_password' before\n"
                                "issuing an rcon command.\n")
        return

    network.NET_Config(True)  # allow remote

    words = [cmdparser.Cmd_Argv(i) for i in range(1, cmdparser.Cmd_Argc())]
    message = b"\xff\xff\xff\xffrcon " + _encode(password) + b" " + \
        b"".join(_encode(word) + b" " for word in words)

    cls = _cls()
    if cls.state.value >= CA.ca_connected.value:
        to = cls.netchan.remote_address
    else:
        if not cl_main.rcon_address.string:
            clientserver.Com_Printf("You must either be connected,\n"
                                    "or set the 'rcon_address' cvar\n"
                                    "to issue rcon commands\n")
            return
        # the C sends to an empty address when the name doesn't resolve
        to = _address(cl_main.rcon_address.string) or common_h.netadr_t()
        if to.port == 0:
            to.port = DEFAULT_PORT

    network.NET_SendPacket(NS_CLIENT, message + b"\0", to)


def disconnect() -> None:
    """Goes to the full screen console, telling the server we left.

    Also called from Com_Error, so it mustn't raise errors itself.
    """
    cls = _cls()
    cl = cl_main.cl
    if cls.state == CA.ca_disconnected:
        return

    if frame.cl_timedemo and frame.cl_timedemo.value:
        elapsed = system.Sys_Milliseconds() - cl.timedemo_start
        if elapsed > 0:
            clientserver.Com_Printf("%i frames, %3.1f seconds: %3.1f fps\n\n",
                                    cl.timedemo_frames, elapsed / 1000.0,
                                    cl.timedemo_frames * 1000.0 / elapsed)

    shared.VectorClear(cl.refdef.blend)
    vid.R_SetPalette(None)
    menu.M_ForceMenuOff()
    cls.connect_time = 0
    cl_cin.SCR_StopCinematic()
    ogg.OGG_Stop()

    if cls.demorecording:
        cl_main.CL_Stop_f()

    # three times, in case packets are lost
    final = bytes([STRINGCMD]) + b"disconnect"
    for _ in range(3):
        netchan.Netchan_Transmit(cls.netchan, final)

    cl_main.CL_ClearState()

    if cls.download:  # stop a download
        cls.download.close()
        cls.download = None
    download.CL_CancelHTTPDownloads(True)
    cls.downloadReferer = ""
    cls.downloadname = ""
    cls.downloadposition = 0

    cls.state = CA.ca_disconnected
    sound_c.snd_is_underwater = False

    cl_main.CL_WriteConfiguration()  # for the game or mod being left
    # back to the game the player chose (a server may have used another mod)
    cvar.Cvar_Set("game", frame.userGivenGame)


def _disconnect_command() -> None:
    clientserver.Com_Error(shared.ERR_DROP, "Disconnected from server")


def packet_text(text: str) -> bytes:
    r"""A ``packet`` command's contents: connectionless, with \n for a newline."""
    return b"\xff\xff\xff\xff" + _encode(text.replace("\\n", "\n"))


def _packet_command() -> None:
    """``packet <destination> <contents>``."""
    if cmdparser.Cmd_Argc() != 3:
        clientserver.Com_Printf("packet <destination> <contents>\n")
        return

    network.NET_Config(True)  # allow remote
    adr = _address(cmdparser.Cmd_Argv(1))
    if adr is None:
        clientserver.Com_Printf("Bad address\n")
        return
    network.NET_SendPacket(NS_CLIENT, packet_text(cmdparser.Cmd_Argv(2)), adr)


def _changing_command() -> None:
    """The server hints that it changes map: drop to the console."""
    cls = _cls()
    if cls.download:
        return  # not in the middle of downloading a map

    cl_screen.SCR_BeginLoadingPlaque()
    cls.state = CA.ca_connected  # not active, but not disconnected
    # reset in case it didn't settle (a problem with the faster reconnects)
    cl_keyboard.anykeydown = 0
    clientserver.Com_Printf("\nChanging map...\n")
    if cls.downloadServerRetry != "":
        download.CL_SetHTTPServer(cls.downloadServerRetry)


def _reconnect_command() -> None:
    """The server changes level: join it again."""
    cls = _cls()
    if cls.download is not None:
        return  # not in the middle of downloading a map

    sound_c.S_StopAllSounds()
    if cls.state == CA.ca_connected:
        clientserver.Com_Printf("reconnecting...\n")
        _write_stringcmd("new")
        return

    if cls.servername:
        if cls.state.value >= CA.ca_connected.value:
            disconnect()
            cls.connect_time = cls.realtime - 1500
        else:
            cls.connect_time = -99999  # at once
        cls.state = CA.ca_connecting
        clientserver.Com_Printf("reconnecting...\n")


def ping_servers() -> None:
    """``pingservers``: asks for info by broadcast, multicast and the address book."""
    network.NET_Config(True)  # allow remote
    clientserver.Com_Printf("pinging broadcast...\n")
    query = f"info {common_h.PROTOCOL_VERSION}"

    def ping(adrtype: common_h.netadrtype_t) -> None:
        adr = common_h.netadr_t()
        adr.type = adrtype
        adr.port = DEFAULT_PORT
        netchan.Netchan_OutOfBandPrint(NS_CLIENT, adr, query)

    if not cvar.Cvar_Get("noudp", "0", shared.CVAR_NOSET).value:
        ping(common_h.netadrtype_t.NA_BROADCAST)
        clientserver.Com_Printf("pinging multicast...\n")
        ping(common_h.netadrtype_t.NA_MULTICAST6)
    if not cvar.Cvar_Get("noipx", "0", shared.CVAR_NOSET).value:
        ping(common_h.netadrtype_t.NA_BROADCAST_IPX)

    for i in range(client_h.NUM_ADDRESSBOOK_ENTRIES):
        text = cvar.Cvar_VariableString(f"adr{i}")
        if not text:
            continue
        clientserver.Com_Printf(f"pinging {text}...\n")
        adr = _address(text)
        if adr is None:
            clientserver.Com_Printf(f"Bad address: {text}\n")
            continue
        netchan.Netchan_OutOfBandPrint(NS_CLIENT, adr, query)


def _client_connect() -> None:
    """The server accepted us."""
    cls = _cls()
    if cls.state == CA.ca_connected:
        clientserver.Com_Printf("Dup connect received.  Ignored.\n")
        return

    netchan.Netchan_Setup(NS_CLIENT, cls.netchan, netchan.net_from, cls.quakePort)
    server = network.NET_AdrToString(cls.netchan.remote_address)
    for i in range(1, cmdparser.Cmd_Argc()):
        arg = cmdparser.Cmd_Argv(i)
        if arg.startswith("dlserver="):
            cls.downloadReferer = f"quake2://{server}"[:32 - 1]
            download.CL_SetHTTPServer(arg[len("dlserver="):])
            if cls.downloadServer:
                clientserver.Com_Printf("HTTP downloading enabled, URL: %s\n", cls.downloadServer)

    # A local single player game pauses while we connect and load (it lets
    # through a few frames: four of the game's, or a hundred when the level
    # was visited before). Com_ServerState() is 2 (ss_game) for a local
    # game that is not a demo or cinematic. The game is unpaused once we
    # join, unless it was paused already; cl_loadpaused 0 turns this off.
    if clientserver.Com_ServerState() == 2 and cvar.Cvar_VariableValue("maxclients") <= 1:
        if cl_main.cl_loadpaused.value and not cl_main.cl_paused.value:
            cl_main.paused_at_load = True
            cvar.Cvar_Set("paused", "1")

    _write_stringcmd("new")
    cls.state = CA.ca_connected


def _gui_command() -> None:
    """A command from a front end on this machine."""
    if not network.NET_IsLocalAddress(netchan.net_from):
        clientserver.Com_Printf("Command packet from remote host.  Ignored.\n")
        return
    cmdparser.Cbuf_AddText(movemsg.MSG_ReadString(netchan.net_message))
    cmdparser.Cbuf_AddText("\n")


def _print() -> None:
    clientserver.Com_Printf("%s", movemsg.MSG_ReadString(netchan.net_message))


def _ping() -> None:
    netchan.Netchan_OutOfBandPrint(NS_CLIENT, netchan.net_from, "ack")


def _challenge() -> None:
    _cls().challenge = shared_c.atoi(cmdparser.Cmd_Argv(1))
    _send_connect_packet()


def _echo() -> None:
    netchan.Netchan_OutOfBandPrint(NS_CLIENT, netchan.net_from, cmdparser.Cmd_Argv(1))


CONNECTIONLESS: dict[str, Callable[[], None]] = {
    "client_connect": _client_connect,  # the server accepted us
    "info": lambda: cl_main.CL_ParseStatusMessage(),  # a server answered pingservers
    "cmd": _gui_command,
    "print": _print,
    "ping": _ping,
    "challenge": _challenge,  # from the server we connect to
    "echo": _echo,  # a server's echo request
}


def _connectionless_packet() -> None:
    msg = netchan.net_message
    movemsg.MSG_BeginReading(msg)
    movemsg.MSG_ReadLong(msg)  # the -1
    cmdparser.Cmd_TokenizeString(movemsg.MSG_ReadStringLine(msg), False)

    name = cmdparser.Cmd_Argv(0)
    clientserver.Com_Printf(f"{network.NET_AdrToString(netchan.net_from)}: {name}\n")

    handler = CONNECTIONLESS.get(name)
    if handler is None:
        clientserver.Com_Printf("Unknown command.\n")
        return
    handler()


def _untrusted_data_error(err: Exception, what: str, drop_connection: bool) -> None:
    """Reports an exception while reading a packet (not in the C).

    Packets are untrusted data; an exception a bad one causes (where the C
    would read garbage) would otherwise end the program. A message from
    the server drops the connection, as the C's ERR_DROP for an illegible
    message; a connectionless packet, which anyone can send, is ignored.
    The traceback shows with developer 1.
    """
    clientserver.Com_DPrintf("{}".format("".join(traceback.format_exception(err))))
    sender = network.NET_AdrToString(netchan.net_from)
    if drop_connection:
        clientserver.Com_Error(shared.ERR_DROP, "CL_ParseServerMessage: %s in %s from %s",
                               type(err).__name__, what, sender)
    clientserver.Com_Printf(f"CL_ReadPackets: {type(err).__name__} in {what} from {sender}, "
                            "ignored\n")


def _read_packet() -> None:
    cls = _cls()
    msg = netchan.net_message

    if msg.cursize >= 4 and struct.unpack("<l", msg.data[:4])[0] == -1:
        try:
            _connectionless_packet()
        except errors.DropError:
            raise
        except Exception as err:
            _untrusted_data_error(err, "connectionless packet", False)
        return

    if cls.state in (CA.ca_disconnected, CA.ca_connecting):
        return  # not connected: dropped
    if msg.cursize < 8:
        clientserver.Com_Printf(f"{network.NET_AdrToString(netchan.net_from)}: Runt packet\n")
        return
    if not network.NET_CompareAdr(netchan.net_from, cls.netchan.remote_address):
        clientserver.Com_DPrintf(
            f"{network.NET_AdrToString(netchan.net_from)}:sequenced packet without connection\n")
        return
    if not netchan.Netchan_Process(cls.netchan, msg):
        return  # not accepted

    try:
        cl_parse.parse_server_message()
    except errors.DropError:
        raise
    except Exception as err:
        _untrusted_data_error(err, "server message", True)


def read_packets() -> None:
    """Reads every packet that arrived, then checks for a timed out server."""
    while True:
        rx, netchan.net_from = network.NET_GetPacket(NS_CLIENT, netchan.net_from,
                                                     netchan.net_message)
        if not rx:
            break
        _read_packet()

    cls = _cls()
    cl = cl_main.cl
    if (cls.state.value >= CA.ca_connected.value
            and cls.realtime - cls.netchan.last_received > cl_main.cl_timeout.value * 1000):
        cl.timeoutcount += 1
        if cl.timeoutcount > 5:  # five frames' grace, for debuggers
            clientserver.Com_Printf("\nServer connection timed out.\n")
            disconnect()
    else:
        cl.timeoutcount = 0


# the console commands (added by cl_main)
COMMANDS: dict[str, Callable[[], None]] = {
    "cmd": _cmd_command,
    "pingservers": ping_servers,
    "changing": _changing_command,
    "disconnect": _disconnect_command,
    "connect": _connect_command,
    "reconnect": _reconnect_command,
    "rcon": _rcon_command,
    "packet": _packet_command,
}
