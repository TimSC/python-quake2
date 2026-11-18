"""The client's connectionless commands and the packet command's text."""

# imported the way the game imports the client (through the platform layer)
import backends.unix.system  # noqa: F401
from client import cl_network


def test_packet_text_turns_backslash_n_into_newlines():
    assert cl_network.packet_text("status\\nmore") == b"\xff\xff\xff\xffstatus\nmore"
    assert cl_network.packet_text("a\\\\nb") == b"\xff\xff\xff\xffa\\\nb"
    assert cl_network.packet_text("café") == b"\xff\xff\xff\xffcaf\xe9"  # latin-1


def test_every_connectionless_command_has_a_handler():
    assert set(cl_network.CONNECTIONLESS) == {
        "client_connect", "info", "cmd", "print", "ping", "challenge", "echo"}
