"""The engine's errors.

``Com_Error`` cleans up (shuts the server down, drops the client) and raises
one of these; the frame loop catches them and goes on with the next frame,
where the C jumps back to its setjmp. Fatal errors end the process instead.
"""


class DropError(Exception):
    """ERR_DROP: the game or connection is dropped back to the console."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class DisconnectError(DropError):
    """ERR_DISCONNECT: the client was disconnected (not an error to report)."""
