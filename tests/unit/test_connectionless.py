from dataclasses import dataclass, field

import pytest

# imported the way the game imports the server (through the platform layer)
import backends.unix.system  # noqa: F401
from server import sv_conless


@dataclass
class Challenge:
    adr: str = ""
    challenge: int = 0
    time: int = 0


@dataclass
class Numbers:
    """A stand-in for randk(): hands out the numbers given."""

    values: list = field(default_factory=list)

    def __call__(self) -> int:
        return self.values.pop(0)


def same(a, b) -> bool:
    return a == b


def challenges(n: int = 4) -> list:
    return [Challenge() for _ in range(n)]


def test_issue_challenge_reuses_an_address_challenge():
    table = challenges()
    first = sv_conless.issue_challenge(table, "a", 10, same, Numbers([1234]))
    again = sv_conless.issue_challenge(table, "a", 20, same, Numbers([999]))
    assert first == again == 1234
    assert table[0].time == 10  # not renewed


def test_issue_challenge_fills_the_oldest_slot():
    table = challenges(3)
    for i, t in enumerate((30, 10, 20)):
        table[i].adr, table[i].time = f"old{i}", t
    sv_conless.issue_challenge(table, "new", 40, same, Numbers([5]))
    assert [c.adr for c in table] == ["old0", "new", "old2"]
    assert (table[1].challenge, table[1].time) == (5, 40)


def test_issue_challenge_is_15_bits():
    table = challenges()
    assert sv_conless.issue_challenge(table, "a", 0, same, Numbers([0x12345])) == 0x2345


def test_issue_challenge_takes_slot_0_when_none_is_older():
    # the C only takes a slot older than 0x7fffffff, else the first
    table = challenges(2)
    for c in table:
        c.adr, c.time = "x", 0x7fffffff
    sv_conless.issue_challenge(table, "a", 1, same, Numbers([7]))
    assert table[0].adr == "a"


@pytest.mark.parametrize("adr, number, expected", [
    ("a", 77, None),
    ("a", 78, "Bad challenge."),
    ("b", 77, "No challenge for address."),
])
def test_check_challenge(adr, number, expected):
    table = challenges()
    table[2].adr, table[2].challenge = "a", 77
    assert sv_conless.check_challenge(table, adr, number, same) == expected


def test_info_line_right_aligns_as_printf():
    assert sv_conless.info_line("myhost", "base1", 3, 8) == \
        "          myhost    base1  3/ 8\n"


def test_info_line_is_cut_to_the_c_buffer():
    line = sv_conless.info_line("h" * 100, "base1", 1, 16)
    assert len(line) == sv_conless.INFO_REPLY_SIZE - 1


def test_rcon_command_skips_the_password():
    assert sv_conless.rcon_command(["rcon", "secret", "map", "base1"]) == "map base1 "
    assert sv_conless.rcon_command(["rcon", "secret"]) == ""


def test_request_numbers_parse_as_strtol():
    req = sv_conless.Request(None, ["connect", "34", "12abc", "x"], "", "")
    assert (req.int_arg(1), req.int_arg(2), req.int_arg(3), req.int_arg(9)) == (34, 12, 0, 0)


def test_every_connectionless_command_has_a_handler():
    assert set(sv_conless.COMMANDS) == {
        "ping", "ack", "status", "info", "getchallenge", "connect", "rcon"}
