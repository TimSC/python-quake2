"""The platform loop releases native resources before Python exits."""

import sys

import pytest

from backends.unix import system


@pytest.mark.parametrize(
    "failure", [None, SystemExit(0), KeyboardInterrupt(), RuntimeError("frame")]
)
def test_main_always_shuts_down_on_frame_thread(monkeypatch, failure) -> None:
    import threading

    thread = threading.get_ident()
    events = []
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setattr(system.frame, "Qcommon_Init", lambda: None)
    monkeypatch.setattr(system.cvar, "Cvar_Get", lambda *args: None)
    monkeypatch.setattr(system, "nostdout", None)

    def frame() -> None:
        events.append(("frame", threading.get_ident()))
        if failure is not None:
            raise failure

    monkeypatch.setattr(system.frame, "Qcommon_Mainloop", frame)
    monkeypatch.setattr(
        system.cl_main, "CL_Shutdown", lambda: events.append(("client", threading.get_ident()))
    )
    monkeypatch.setattr(
        system.frame, "Qcommon_Shutdown", lambda: events.append(("common", threading.get_ident()))
    )
    if failure is None:
        system.main()
    else:
        with pytest.raises(type(failure)) as raised:
            system.main()
        assert raised.value is failure
    assert events == [("frame", thread), ("client", thread), ("common", thread)]
