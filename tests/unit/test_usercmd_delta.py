from common import movemsg, szone, usercmd_delta
from common.header import common as common_h
from common.header import shared

C = common_h


def new_buffer() -> common_h.sizebuf_t:
    buf = common_h.sizebuf_t()
    szone.SZ_Init(buf, 256)
    return buf


def command(**values) -> shared.usercmd_t:
    cmd = shared.usercmd_t()
    for name, value in values.items():
        if name == "angles":
            cmd.angles[:] = value
        else:
            setattr(cmd, name, value)
    return cmd


def test_unchanged_command_is_three_bytes():
    cmd = command(msec=16, lightlevel=40)
    buf = new_buffer()
    usercmd_delta.write_delta(buf, cmd, cmd)
    assert bytes(buf.data[:buf.cursize]) == bytes([0, 16, 40])


def test_round_trip():
    old = command(msec=16, angles=(0, 100, 0), forwardmove=400)
    new = command(msec=17, angles=(5, 100, -7), forwardmove=400, sidemove=-200,
                  buttons=1, impulse=8, lightlevel=99)
    buf = new_buffer()
    usercmd_delta.write_delta(buf, old, new)
    movemsg.MSG_BeginReading(buf)
    bits = buf.data[0]
    assert bits == C.CM_ANGLE1 | C.CM_ANGLE3 | C.CM_SIDE | C.CM_BUTTONS | C.CM_IMPULSE
    out = shared.usercmd_t()
    usercmd_delta.read_delta(buf, old, out)
    assert list(out.angles) == [5, 100, -7]
    assert (out.forwardmove, out.sidemove, out.upmove) == (400, -200, 0)
    assert (out.buttons, out.impulse, out.msec, out.lightlevel) == (1, 8, 17, 99)


def test_truncated_message_gives_masked_bytes():
    buf = new_buffer()
    usercmd_delta.write_delta(buf, command(), command(buttons=3, msec=10))
    buf.cursize = 1  # only the bits byte arrived
    movemsg.MSG_BeginReading(buf)
    out = shared.usercmd_t()
    usercmd_delta.read_delta(buf, command(), out)
    # reading past the end gives -1, stored as 255 in the C's byte fields
    assert (out.buttons, out.msec, out.lightlevel) == (255, 255, 255)
