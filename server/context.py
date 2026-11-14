"""The server's state as one object.

``Server`` holds what the C keeps in its server globals: the level being
played (``level``, the C's ``sv``), the state that lasts across levels
(``persistent``, the C's ``svs``: the client slots, the challenges, the
frame ring, the server demo), and the client whose packet or command is
being handled (``client`` and its edict, ``player``).

``server`` (also ``sv_init.server``) is the process's one server;
``sv_init.sv`` and ``sv_init.svs`` are its ``level`` and ``persistent``,
for the code that still uses the C names.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from common.header import common as common_h
from server.header import server as server_h


@dataclass(slots=True)
class ServerCvars:
    """The server's cvars (made by sv_main.SV_Init)."""

    optimize_sp_loadtime: Any
    optimize_mp_loadtime: Any
    rcon_password: Any  # password for remote server commands
    maxclients: Any
    hostname: Any
    timeout: Any  # seconds without a message before a client is dropped
    zombietime: Any  # seconds to keep sending to a dropped client
    showclamp: Any
    paused: Any
    timedemo: Any
    enforcetime: Any
    allow_download: Any
    allow_download_players: Any
    allow_download_models: Any
    allow_download_sounds: Any
    allow_download_maps: Any
    downloadserver: Any  # the HTTP download server given to clients
    noreload: Any  # don't reload a level's state when entering it again
    airaccelerate: Any
    public: Any  # send heartbeats to the masters
    entfile: Any  # load external entity files


class Server:
    """The level, the persistent server state and the current client."""

    def __init__(self) -> None:
        self.level = server_h.server_t()
        self.persistent = server_h.server_static_t()
        self.client: server_h.client_t | None = None  # whose message is being handled
        self.player = None  # that client's edict
        self.cvars: ServerCvars | None = None  # None until SV_Init
        self.masters = [common_h.netadr_t() for _ in range(server_h.MAX_MASTERS)]  # slot 0: id's

    @property
    def maxclients(self) -> int:
        return int(self.cvars.maxclients.value)

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


server = Server()  # the process's one server
