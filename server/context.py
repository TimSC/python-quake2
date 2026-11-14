"""The server's state as one object.

``Server`` holds what the C keeps in its server globals: the level being
played (``level``, the C's ``sv``), the state that lasts across levels
(``persistent``, the C's ``svs``: the client slots, the challenges, the
frame ring, the server demo), and the client whose packet or command is
being handled (``client`` and its edict, ``player``).

``sv_init.server`` is the process's one server; ``sv_init.sv`` and
``sv_init.svs`` are its ``level`` and ``persistent``, for the code that
still uses the C names.
"""

from __future__ import annotations

from collections.abc import Iterator

from server.header import server as server_h


class Server:
    """The level, the persistent server state and the current client."""

    def __init__(self) -> None:
        self.level = server_h.server_t()
        self.persistent = server_h.server_static_t()
        self.client: server_h.client_t | None = None  # whose message is being handled
        self.player = None  # that client's edict

    @property
    def clients(self) -> list[server_h.client_t]:
        """The client slots (maxclients of them, made by SV_InitGame)."""
        return self.persistent.clients

    def make_clients(self, count: int) -> None:
        self.persistent.clients = [server_h.client_t(slot) for slot in range(count)]

    def clients_from(self, state: server_h.client_state_t) -> Iterator[server_h.client_t]:
        """The clients in this state or later (connected, spawned)."""
        return (cl for cl in self.clients if cl.state.value >= state.value)

    def set_client(self, client: server_h.client_t) -> None:
        """Makes client the one being handled, with its edict as the player."""
        self.client = client
        self.player = server_h.CL_EDICT(client)
