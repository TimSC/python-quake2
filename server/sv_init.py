"""Starting games and maps (Yamagi's sv_init.c).

``start_map`` handles the ``map`` syntax (``[*]<map>$<spawnpoint>+<next>``,
and cinematics, demos and pictures); ``new_game`` sets the server up for a
new game (the game mode, the client slots, the network and the game);
``spawn_server`` loads a level and spawns its entities. The index
functions give the game the configstring slot of a model, sound or image.

``server`` is the one server (see ``context``); ``sv`` and ``svs`` are its
level and persistent state under the C's names, which the other server
modules use.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import copy

from backends.unix import network
from client import cl_network, cl_screen
from common import (
    clientserver,
    cmdparser,
    collision,
    cvar,
    filesystem,
    frame,
    movemsg,
    pmove,
    szone,
)
from common.header import common as common_h
from common.header import shared
from common.shared import rand
from common.shared import shared as shared_c
from server import context, sv_game, sv_main, sv_save, sv_send, sv_world
from server.header import server as server_h

SS = server_h.server_state_t
CS = server_h.client_state_t

ALLOC_ENTITIES_MIN = 32  # the baselines start with at least this many entities
MAX_SV_ENTNUM = 32767  # SHRT_MAX
SERVERINFO_LATCH = shared.CVAR_SERVERINFO | shared.CVAR_LATCH
ID_MASTER = f"192.246.40.37:{common_h.PORT_MASTER}"  # heartbeats always go here

server = context.server
svs = server.persistent
sv = server.level


def alloc_baseline(entnum: int) -> shared.entity_state_t | None:
    """An entity's baseline, growing the list in powers of two as the C does."""
    if entnum < 0 or entnum > MAX_SV_ENTNUM:
        return None
    if entnum >= sv.numbaselines:
        if sv.numbaselines or entnum >= ALLOC_ENTITIES_MIN:
            size = shared_c.NextPow2gt(entnum)
        else:
            size = ALLOC_ENTITIES_MIN
        while len(sv.baselines) < size:
            sv.baselines.append(shared.entity_state_t())
        sv.numbaselines = size
    return sv.baselines[entnum]


def _overflowed(name: str, message: str, *args) -> None:
    """Notes a resource that didn't fit in the configstrings (printed once, after loading)."""
    if name not in sv.configstrings_overflow:
        if sv.state != SS.ss_loading:
            clientserver.Com_Printf(message, *args)
        sv.configstrings_overflow.append(name)


def find_index(name: str, start: int, count: int, create: bool) -> int:
    """The configstring slot (from 1) of a resource, given one if create is set; 0 for none."""
    if not name:
        return 0

    i = 1
    while i < count and sv.configstrings[start + i]:
        if sv.configstrings[start + i] == name:
            return i
        i += 1

    if not create:
        return 0
    if i == count:
        _overflowed(name, "Failed to load %s: configstrings overflowed\n", name)
        return 0
    if len(name) >= shared.MAX_QPATH:
        sv.configstrings[start + i] = ""
        _overflowed(name, "Failed to load %s: configstring too long: %d > %d\n",
                    name, len(name), shared.MAX_QPATH - 1)
        return 0

    sv.configstrings[start + i] = name
    if sv.state != SS.ss_loading:
        # tell everyone
        movemsg.MSG_WriteChar(sv.multicast, common_h.svc_ops_e.svc_configstring.value)
        movemsg.MSG_WriteConfigString(sv.multicast, start + i, name)
        sv_send.multicast(shared_c.vec3_origin, shared.multicast_t.MULTICAST_ALL_R)
    return i


def model_index(name: str) -> int:
    return find_index(name, shared.CS_MODELS, shared.MAX_MODELS, True)


def sound_index(name: str) -> int:
    return find_index(name, shared.CS_SOUNDS, shared.MAX_SOUNDS, True)


def image_index(name: str) -> int:
    return find_index(name, shared.CS_IMAGES, shared.MAX_IMAGES, True)


def create_baseline() -> None:
    """The entities' states now, as the baselines their updates are compressed against."""
    for entnum in range(1, server.game.num_edicts):
        ent = server_h.EDICT_NUM(entnum)
        if not ent.inuse:
            continue
        if not ent.s.modelindex and not ent.s.sound and not ent.s.effects:
            continue
        ent.s.number = entnum
        shared.VectorCopy(ent.s.origin, ent.s.old_origin)
        if alloc_baseline(entnum) is not None:
            sv.baselines[entnum] = copy.deepcopy(ent.s)


def check_for_savegame(isautosave: bool) -> None:
    """Loads the level's state from the current save, if the level was visited."""
    if server.cvars.noreload.value or cvar.Cvar_VariableValue("deathmatch"):
        return

    name = f"{filesystem.FS_Gamedir()}/save/current/{sv.name}.sav"
    f = filesystem.Q_fopen(name, "rb")
    if f is None:
        return  # no save
    f.close()

    sv_world.clear_world()
    sv_save.read_level_file()  # the configstrings and area portals

    if not sv.loadgame or isautosave:
        # back in a level after being in another: run it for ten seconds
        previous = sv.state
        sv.state = SS.ss_loading
        for _ in range(100):
            server.game.RunFrame()
        sv.state = previous


def _set_state(state: server_h.server_state_t) -> None:
    sv.state = state
    clientserver.Com_SetServerState(state.value)


def spawn_server(name: str, spawnpoint: str, serverstate: server_h.server_state_t,
                 attractloop: bool, loadgame: bool, isautosave: bool) -> None:
    """Changes the server to a new level, taking the connected clients along."""
    if attractloop:
        cvar.Cvar_Set("paused", "0")

    clientserver.Com_Printf("------- server initialization ------\n")
    clientserver.Com_DPrintf("SpawnServer: %s\n", name)

    if sv.demofile:
        filesystem.FS_FCloseFile(sv.demofile)

    svs.spawncount += 1  # any partly connected client restarts
    _set_state(SS.ss_dead)

    # wipe the level
    sv_main.clear_baselines()
    sv.clear()
    svs.realtime = 0
    sv.loadgame = loadgame
    sv.attractloop = attractloop

    sv.configstrings[shared.CS_NAME] = name  # for levels that don't set a message
    if cvar.Cvar_VariableValue("deathmatch"):
        airaccelerate = server.cvars.airaccelerate.value
        sv.configstrings[shared.CS_AIRACCEL] = f"{airaccelerate:g}"
        pmove.pm_airaccelerate = airaccelerate
    else:
        sv.configstrings[shared.CS_AIRACCEL] = "0"
        pmove.pm_airaccelerate = 0

    szone.SZ_Init(sv.multicast, common_h.MAX_MSGLEN)
    sv.name = name

    # the first slots are the clients'; they have to reconnect
    for cl in svs.clients[:server.maxclients]:
        if cl.state.value > CS.cs_connected.value:
            cl.state = CS.cs_connected
        cl.lastframe = -1

    sv.time = 1000

    if serverstate != SS.ss_game:
        sv.models[1], checksum = collision.CM_LoadMap("", False)  # no real map
    else:
        mappath = f"maps/{name}.bsp"[:shared.MAX_QPATH - 1]
        sv.configstrings[shared.CS_MODELS + 1] = mappath
        sv.models[1], checksum = collision.CM_LoadMap(mappath, False)
    sv.configstrings[shared.CS_MAPCHECKSUM] = str(int(checksum))

    sv_world.clear_world()
    for i in range(1, collision.CM_NumInlineModels()):
        sv.configstrings[shared.CS_MODELS + 1 + i] = f"*{i}"
        sv.models[i + 1] = collision.CM_InlineModel(f"*{i}")

    # spawn the entities, and run two frames to let everything settle
    _set_state(SS.ss_loading)
    server.game.SpawnEntities(sv.name, collision.CM_EntityString(), spawnpoint)
    server.game.RunFrame()
    server.game.RunFrame()

    if checksum != shared_c.atoi(sv.configstrings[shared.CS_MAPCHECKSUM]):
        clientserver.Com_Error(shared.ERR_DROP, "Game DLL corrupted server configstrings")

    _set_state(serverstate)  # every precache is done
    create_baseline()
    check_for_savegame(isautosave)

    cvar.Cvar_FullSet("mapname", sv.name, shared.CVAR_SERVERINFO | shared.CVAR_NOSET)
    clientserver.Com_Printf("------------------------------------\n\n")


def choose_gamemode() -> int:
    """The game mode from deathmatch, coop and singleplayer; the others are cleared.

    Deathmatch wins over coop, coop over single player; a dedicated server
    without any is deathmatch.
    """
    ignored = []

    def clear(name: str, flags: int) -> None:
        cvar.Cvar_FullSet(name, "0", flags)
        ignored.append(name)

    if cvar.Cvar_VariableValue("deathmatch"):
        if cvar.Cvar_VariableValue("coop"):
            clear("coop", SERVERINFO_LATCH)
        if cvar.Cvar_VariableValue("singleplayer"):
            clear("singleplayer", 0)
        choice, gamemode = "deathmatch", server_h.GAMEMODE_DM
    elif cvar.Cvar_VariableValue("coop"):
        if cvar.Cvar_VariableValue("singleplayer"):
            clear("singleplayer", 0)
        choice, gamemode = "coop", server_h.GAMEMODE_COOP
    elif frame.dedicated.value and not cvar.Cvar_VariableValue("singleplayer"):
        cvar.Cvar_FullSet("deathmatch", "1", SERVERINFO_LATCH)
        choice, gamemode = "deathmatch", server_h.GAMEMODE_DM
    else:
        cvar.Cvar_FullSet("singleplayer", "1", SERVERINFO_LATCH)
        choice, gamemode = "singleplayer", server_h.GAMEMODE_SP

    if ignored:
        clientserver.Com_Printf("Gamemode ambiguity: Chose: %s, ignored: %s\n",
                                choice, "".join(name + " " for name in ignored))
    return gamemode


def _maxclients_for(gamemode: int) -> str | None:
    """The maxclients a game mode needs, or None to keep it."""
    maxclients = server.cvars.maxclients.value
    if gamemode == server_h.GAMEMODE_DM:
        if maxclients <= 1:
            return "8"
        if maxclients > shared.MAX_CLIENTS:
            return str(shared.MAX_CLIENTS)
        return None
    if gamemode == server_h.GAMEMODE_COOP:
        return "4" if maxclients <= 1 or maxclients > 4 else None
    return "1"  # single player


def new_game() -> None:
    """A brand new game: the game mode, the client slots, the network and the game."""
    if svs.initialized:
        sv_main.SV_Shutdown("Server restarted\n", True)  # the clients reconnect
    else:
        cl_network.drop()  # the local client is down
        cl_screen.SCR_BeginLoadingPlaque()

    cvar.Cvar_GetLatchedVars()  # maxclients and the like
    svs.initialized = True

    gamemode = choose_gamemode()
    maxclients = _maxclients_for(gamemode)
    if maxclients is not None:
        cvar.Cvar_FullSet("maxclients", maxclients, SERVERINFO_LATCH)

    svs.gamemode = gamemode
    svs.spawncount = rand.randk()
    server.make_clients(server.maxclients)
    svs.num_client_entities = int(server.cvars.maxclients.value * common_h.UPDATE_BACKUP * 64)
    svs.client_entities = [shared.entity_state_t() for _ in range(svs.num_client_entities)]

    # a dedicated single player server still listens
    listen = gamemode == server_h.GAMEMODE_SP if frame.dedicated.value else False
    network.NET_Config(listen or server.cvars.maxclients.value > 1)

    svs.last_heartbeat = -99999  # a heartbeat at once
    adr = network.NET_StringToAdr(ID_MASTER)
    if adr is not None:
        server.masters[0] = adr

    sv_game.init_game()

    for i in range(server.maxclients):
        server_h.CLNUM_EDICT(i).s.number = i + 1
        svs.clients[i].lastcmd = shared.usercmd_t()


# the server states of the non-map "levels", by extension
_MEDIA_STATES = {
    ".cin": SS.ss_cinematic,
    ".dm2": SS.ss_demo,
    ".pcx": SS.ss_pic, ".tga": SS.ss_pic, ".jpg": SS.ss_pic, ".png": SS.ss_pic,
}


def start_map(attractloop: bool, levelstring: str, loadgame: bool,
              isautosave: bool = False) -> None:
    """Goes to a map: ``[*]<map>$<spawnpoint>+<next>``.

    The map can also be a cinematic (.cin), a demo (.dm2) or a picture;
    ``+<next>`` is what comes after it (``map tram.cin+jail_e3``), and a
    leading '*' starts a new unit.
    """
    sv.loadgame = loadgame
    sv.attractloop = attractloop

    if sv.state == SS.ss_dead and not sv.loadgame:
        new_game()  # the game is just starting

    level = levelstring
    if "+" in level:
        level, following = level.split("+", 1)
        cvar.Cvar_Set("nextserver", f'gamemap "{following}"')
    else:
        # the next demo, if a list of demos is playing
        cvar.Cvar_Set("nextserver", cvar.Cvar_VariableString("nextdemo"))
        cvar.Cvar_Set("nextdemo", "")

    # the end game screen in coop
    if cvar.Cvar_VariableValue("coop") and not shared_c.Q_stricmp(level, "victory.pcx"):
        cvar.Cvar_Set("nextserver", 'gamemap "*base1"')

    level, _, spawnpoint = level.partition("$")
    if level[:1] == "*":
        level = level[1:]  # the end-of-unit flag

    state = _MEDIA_STATES.get(level[-4:]) if len(level) > 4 else None

    cl_screen.SCR_BeginLoadingPlaque()  # for the local client
    sv_send.broadcast_command("changing\n")
    if state is not None:
        spawn_server(level, spawnpoint, state, attractloop, loadgame, isautosave)
    else:
        # sending here can mean a long reconnect delay
        if not sv_main.optimizations() & server_h.OPTIMIZE_RECONNECT:
            sv_send.send_client_messages()
            sv_send.send_prep_client_messages()
        spawn_server(level, spawnpoint, SS.ss_game, attractloop, loadgame, isautosave)
        cmdparser.Cbuf_CopyToDefer()

    sv_send.broadcast_command("reconnect\n")
