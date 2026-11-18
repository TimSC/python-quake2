"""The server's save files: the configstrings block and the save comment."""

import time

# imported the way the game imports the server (through the platform layer)
import backends.unix.system  # noqa: F401
from common.header import shared
from server import sv_init, sv_save

Q = shared.MAX_QPATH


def configstrings_with(**at: str) -> list[str]:
    strings = [""] * shared.MAX_CONFIGSTRINGS
    for index, text in at.items():
        strings[int(index[1:])] = text
    return strings


def test_configstrings_round_trip_with_a_long_statusbar():
    statusbar = "yv 0 " * 40  # 200 characters: runs over four slots
    strings = configstrings_with(**{
        f"i{shared.CS_NAME}": "Outer Base",
        f"i{shared.CS_STATUSBAR}": statusbar,
        f"i{shared.CS_MODELS + 1}": "maps/base1.bsp",
    })
    sv_init.sv.configstrings[:] = strings
    blob = sv_save.configstrings_blob()
    assert len(blob) == shared.MAX_CONFIGSTRINGS * Q
    # as the C's array: the statusbar runs on into the following slots
    start = shared.CS_STATUSBAR * Q
    assert blob[start:start + len(statusbar)] == statusbar.encode()
    assert sv_save.parse_configstrings(blob) == strings


def test_parse_ends_every_slot_outside_the_statusbar():
    # a name that fills its slot without a NUL is cut, as the C does
    blob = bytearray(shared.MAX_CONFIGSTRINGS * Q)
    blob[shared.CS_NAME * Q:(shared.CS_NAME + 1) * Q] = b"x" * Q
    strings = sv_save.parse_configstrings(bytes(blob))
    assert strings[shared.CS_NAME] == "x" * (Q - 1)


def test_short_block_is_padded():
    assert sv_save.parse_configstrings(b"abc") == configstrings_with(i0="abc")


def test_save_comment():
    now = time.struct_time((2026, 11, 5, 9, 7, 0, 3, 309, 0))
    assert sv_save.save_comment(False, "Outer Base", now) == " 9:07 11/ 5  Outer Base"
    assert sv_save.save_comment(True, "Outer Base", now) == "ENTERING Outer Base"
    assert len(sv_save.save_comment(False, "x" * 50, now)) == sv_save.COMMENT_SIZE - 1


def test_save_names_that_leave_the_save_directory_are_refused():
    for name in ("../x", "a/b", "a\\b"):
        assert sv_save._bad_save_name(name)
    assert not sv_save._bad_save_name("save1")
