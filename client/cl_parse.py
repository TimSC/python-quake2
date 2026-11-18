"""Reading the server's messages (Yamagi's cl_parse.c).

``parse_server_message`` reads one message from the server: a list of
commands (``svc_*``), each handled by ``SERVER_COMMANDS``. The frame
command carries the player state and the entities, delta compressed
against an earlier frame (``parse_frame``); configstrings set the level's
resources; and there are prints, sounds, effects, downloads and stuffed
console commands.

Copyright (C) 1997-2001 Id Software, Inc.; GPL version 2 or later.
"""

from __future__ import annotations

import copy
from collections.abc import Callable

import numpy as np

from client import (
    cl_cin,
    cl_console,
    cl_download,
    cl_effects,
    cl_inventory,
    cl_lights,
    cl_main,
    cl_prediction,
    cl_screen,
    cl_tempentities,
    cl_view,
)
from client.header import client as client_h
from client.input import sdl2
from client.sound import ogg
from client.sound import sound as sound_c
from client.vid import vid
from common import (
    clientserver,
    cmdparser,
    collision,
    cvar,
    entity_delta,
    filesystem,
    movemsg,
    netchan,
    player_delta,
)
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c

SVC = common_h.svc_ops_e
CA = client_h.connstate_t
NO_ENTITY = 99999  # past the last entity number
PARSE_MASK = client_h.MAX_PARSE_ENTITIES - 1
LAYOUT_SIZE = 1024

# the command names cl_shownet prints
SVC_NAMES = ["svc_bad", "svc_muzzleflash", "svc_muzzlflash2", "svc_temp_entity", "svc_layout",
             "svc_inventory", "svc_nop", "svc_disconnect", "svc_reconnect", "svc_sound",
             "svc_print", "svc_stufftext", "svc_serverdata", "svc_configstring",
             "svc_spawnbaseline", "svc_centerprint", "svc_download", "svc_playerinfo",
             "svc_packetentities", "svc_deltapacketentities", "svc_frame"]


def _msg() -> common_h.sizebuf_t:
    return netchan.net_message


def _shownet(text: str) -> None:
    if cl_main.cl_shownet.value >= 2:
        clientserver.Com_Printf(f"{_msg().readcount - 1:3d}:{text}\n")


def _show_net_command(cmd: int) -> None:
    if cmd < 0:
        clientserver.Com_Error(shared.ERR_DROP, "%3i: unexpected message end",
                               _msg().readcount - 1)
        return
    if cl_main.cl_shownet.value >= 2:
        if cmd >= len(SVC_NAMES):
            clientserver.Com_Printf("%3i:BAD CMD %i\n", _msg().readcount - 1, cmd)
            return
        _shownet(SVC_NAMES[cmd])


def register_sounds() -> None:
    """Registers the level's sounds (configstrings CS_SOUNDS on)."""
    sound_c.S_BeginRegistration()
    cl_tempentities.CL_RegisterTEntSounds()
    cl = cl_main.cl
    for i in range(1, shared.MAX_SOUNDS):
        name = cl.configstrings[shared.CS_SOUNDS + i]
        if not name:
            break
        cl.sound_precache[i] = sound_c.S_RegisterSound(name)
        sdl2.IN_Update()  # keep the window responsive while loading
    sound_c.S_EndRegistration()


def _no_lerp(state: shared.entity_state_t, current: shared.entity_state_t) -> bool:
    """Changes that mean the entity jumps instead of moving smoothly."""
    if (state.modelindex != current.modelindex or state.modelindex2 != current.modelindex2
            or state.modelindex3 != current.modelindex3
            or state.modelindex4 != current.modelindex4):
        return True
    if state.event in (shared.EV_PLAYER_TELEPORT, shared.EV_OTHER_TELEPORT):
        return True
    return any(abs(int(state.origin[i] - current.origin[i])) > 512 for i in range(3))


def delta_entity(frame, newnum: int, old, bits: int) -> None:
    """Reads an entity's delta from old and adds the result to frame."""
    cl = cl_main.cl
    ent = cl_main.CL_AllocEntity(newnum) or client_h.centity_t()

    state = cl_main.cl_parse_entities[cl.parse_entities & PARSE_MASK]
    cl.parse_entities += 1
    frame.num_entities += 1
    entity_delta.read_delta(old, state, newnum, bits, _msg())

    if _no_lerp(state, ent.current):
        ent.serverframe = -99

    if ent.serverframe != cl.frame.serverframe - 1:
        # not in the last frame: start it fresh
        ent.trailcount = 1024  # for the diminishing rocket and grenade trails
        ent.prev = shared.entity_state_t()
        ent.prev.copy(state)  # so the lerp doesn't hurt anything
        ent.serverframe_created = cl.frame.serverframe
        start = state.origin if state.event == shared.EV_OTHER_TELEPORT else state.old_origin
        shared.VectorCopy(start, ent.prev.origin)
        shared.VectorCopy(start, ent.lerp_origin)
    else:
        ent.prev = ent.current

    ent.serverframe = cl.frame.serverframe
    ent.current = shared.entity_state_t()
    ent.current.copy(state)


class _OldEntities:
    """Walks the entities of the frame a delta is from."""

    def __init__(self, frame) -> None:
        self.frame = frame
        self.index = -1
        self.state = None
        self.number = NO_ENTITY
        if frame is not None:
            self.next()

    def next(self) -> None:
        self.index += 1
        if self.index >= self.frame.num_entities:
            self.number = NO_ENTITY
            return
        self.state = cl_main.cl_parse_entities[(self.frame.parse_entities + self.index)
                                               & PARSE_MASK]
        self.number = self.state.number


def _shownet3(text: str) -> None:
    if cl_main.cl_shownet.value == 3:
        clientserver.Com_Printf(text)


def parse_packet_entities(oldframe, newframe) -> None:
    """Reads the entities of a frame, as changes to the frame it is from.

    Entities of the old frame the message doesn't name stay unchanged; the
    others are removed, changed, or new (from their baselines).
    """
    newframe.parse_entities = cl_main.cl.parse_entities
    newframe.num_entities = 0
    old = _OldEntities(oldframe)

    while True:
        newnum, bits = entity_delta.read_bits(_msg())
        if newnum > client_h.MAX_CL_ENTNUM:
            clientserver.Com_Error(shared.ERR_DROP, "%s: bad entity %d > %d\n",
                                   "CL_ParsePacketEntities", newnum, client_h.MAX_CL_ENTNUM)
            return
        if _msg().readcount > _msg().cursize:
            clientserver.Com_Error(shared.ERR_DROP, "%s: end of message",
                                   "CL_ParsePacketEntities")
            return
        if newnum == 0:
            break

        while old.number < newnum:
            _shownet3(f"   unchanged: {old.number}\n")
            delta_entity(newframe, old.number, old.state, 0)
            old.next()

        if bits & common_h.U_REMOVE:
            # in the old frame, gone from this one
            _shownet3(f"   remove: {newnum}\n")
            if old.number != newnum:
                clientserver.Com_Printf("U_REMOVE: oldnum != newnum: %d %d\n",
                                        old.number, newnum)
            old.next()
            continue

        if old.number == newnum:
            _shownet3(f"   delta: {newnum}\n")
            delta_entity(newframe, newnum, old.state, bits)
            old.next()
            continue

        # old.number > newnum: a new entity, from its baseline
        _shownet3(f"   baseline: {newnum}\n")
        ent = cl_main.CL_AllocEntity(newnum)
        delta_entity(newframe, newnum, ent.baseline if ent else None, bits)

    # the rest of the old frame's entities, unchanged
    while old.number != NO_ENTITY:
        _shownet3(f"   unchanged: {old.number}\n")
        delta_entity(newframe, old.number, old.state, 0)
        old.next()


def parse_playerstate(oldframe, newframe) -> None:
    """Reads the player state, as changes to the old frame's."""
    if oldframe:
        newframe.playerstate = copy.deepcopy(oldframe.playerstate)
    else:
        newframe.playerstate.clear()
    state = newframe.playerstate
    player_delta.read_delta(_msg(), state)
    if cl_main.cl.attractloop:
        state.pmove.pm_type = shared.pmtype_t.PM_FREEZE.value  # a demo plays


def _fire_entity_events(frame) -> None:
    for i in range(frame.num_entities):
        state = cl_main.cl_parse_entities[(frame.parse_entities + i) & PARSE_MASK]
        if state.event:
            cl_effects.CL_EntityEvent(state)
        if state.effects & shared.EF_TELEPORTER:
            cl_effects.CL_TeleporterParticles(state)


def _delta_source(frame):
    """The frame this one is a delta from, or None; sets frame.valid."""
    cl = cl_main.cl
    if frame.deltaframe <= 0:
        frame.valid = True  # not delta compressed
        cl_main.cls.demowaiting = False  # a demo can start recording now
        return None

    old = cl.frames[frame.deltaframe & common_h.UPDATE_MASK]
    if not old.valid:
        clientserver.Com_Printf("Delta from invalid frame (not supposed to happen!).\n")
    # a delta from a frame we no longer have is read but not used; the
    # client then asks for a full frame
    if old.serverframe != frame.deltaframe:
        clientserver.Com_Printf("Delta frame too old.\n")
    elif cl.parse_entities - old.parse_entities > client_h.MAX_PARSE_ENTITIES - 128:
        clientserver.Com_Printf("Delta parse_entities too old.\n")
    else:
        frame.valid = True
    return old


def _expect(cmd: int, what: int, name: str) -> bool:
    _show_net_command(cmd)
    if cmd != what:
        clientserver.Com_Error(shared.ERR_DROP, "%s: 0x%X not %s", "CL_ParseFrame", cmd, name)
        return False
    return True


def _enter_game() -> None:
    """The first valid frame: the connection is complete."""
    cl = cl_main.cl
    cls = cl_main.cls
    cls.state = CA.ca_active
    cl.force_refdef = True
    for i in range(3):
        cl.predicted_origin[i] = cl.frame.playerstate.pmove.origin[i] * 0.125
    shared.VectorCopy(cl.frame.playerstate.viewangles, cl.predicted_angles)
    if cls.disable_servercount != cl.servercount and cl.refresh_prepped:
        cl_screen.SCR_EndLoadingPlaque()
    cl.sound_prepped = True

    if cl_main.paused_at_load:
        if cl_main.cl_loadpaused.value == 1:
            cvar.Cvar_Set("paused", "0")
        cl_main.paused_at_load = False


def parse_frame() -> None:
    """A server frame: the area bits, the player state and the entities."""
    cl = cl_main.cl
    msg = _msg()
    frame = cl.frame
    frame.clear()
    frame.serverframe = movemsg.MSG_ReadSLong(msg)
    frame.deltaframe = movemsg.MSG_ReadSLong(msg)
    frame.servertime = frame.serverframe * 100

    if cl_main.cls.serverProtocol != 26:  # protocol 26 demos have no count
        cl.surpressCount = movemsg.MSG_ReadByte(msg)
    _shownet3(f"   frame:{frame.serverframe}  delta:{frame.deltaframe}\n")

    old = _delta_source(frame)

    # the client's time stays within the last 100 ms before the frame
    cl.time = min(max(cl.time, frame.servertime - 100), frame.servertime)

    length = movemsg.MSG_ReadByte(msg)
    frame.areabits = movemsg.MSG_ReadData(msg, length)

    if not _expect(movemsg.MSG_ReadByte(msg), SVC.svc_playerinfo.value, "playerinfo"):
        return
    parse_playerstate(old, frame)

    if not _expect(movemsg.MSG_ReadByte(msg), SVC.svc_packetentities.value, "packetentities"):
        return
    parse_packet_entities(old, frame)

    # kept for later deltas
    cl.frames[frame.serverframe & common_h.UPDATE_MASK] = copy.copy(frame)

    if not frame.valid:
        return
    if cl_main.cls.state != CA.ca_active:
        _enter_game()
    _fire_entity_events(frame)
    if cl_main.cl_predict.value and not (frame.playerstate.pmove.pm_flags
                                         & shared.PMF_NO_PREDICTION):
        cl_prediction.CL_CheckPredictionError()


def parse_server_data() -> None:
    """The first message of a level: protocol, game directory, player number, level name."""
    msg = _msg()
    cl = cl_main.cl
    cls = cl_main.cls

    sdl2.In_FlushQueue()  # clear the key states
    clientserver.Com_DPrintf("Serverdata packet received.\n")

    cl_main.CL_ClearState()
    cls.state = CA.ca_connected

    protocol = movemsg.MSG_ReadLong(msg)
    cls.serverProtocol = protocol
    # a local server (playing a demo) may give an older protocol
    if not clientserver.Com_ServerState() and protocol != common_h.PROTOCOL_VERSION:
        clientserver.Com_Error(shared.ERR_DROP, "Server returned version %i, not %i",
                               protocol, common_h.PROTOCOL_VERSION)
        return

    cl.servercount = movemsg.MSG_ReadLong(msg)
    cl.attractloop = movemsg.MSG_ReadByte(msg)

    gamedir = movemsg.MSG_ReadString(msg)
    cl.gamedir = gamedir[:shared.MAX_QPATH - 1]
    current = filesystem.fs_gamedirvar.string
    if (gamedir and (not current or current != gamedir)) or (not gamedir and current == ""):
        cvar.Cvar_Set("game", gamedir)

    cl.playernum = movemsg.MSG_ReadSShort(msg)
    levelname = movemsg.MSG_ReadString(msg)

    if cl.playernum == -1:
        cl_cin.SCR_PlayCinematic(levelname)  # a cinematic or a picture, not a level
    else:
        # two prints, so the level name can have its colour
        clientserver.Com_Printf("\n\n\35" + "\36" * 35 + "\37\n\n")
        clientserver.Com_Printf("%c%s\n", 2, levelname)
        cl.refresh_prepped = False  # prepare the refresh at the next chance


def parse_baseline() -> None:
    newnum, bits = entity_delta.read_bits(_msg())
    ent = cl_main.CL_AllocEntity(newnum)
    entity_delta.read_delta(None, ent.baseline if ent else None, newnum, bits, _msg())


def _register_default_clientinfo(ci) -> None:
    ci.model = vid.R_RegisterModel("players/male/tris.md2")
    ci.weaponmodel[:] = [None] * client_h.MAX_CLIENTWEAPONMODELS
    ci.weaponmodel[0] = vid.R_RegisterModel("players/male/weapon.md2")
    ci.skin = vid.R_RegisterSkin("players/male/grunt.pcx")
    ci.iconname = "/players/male/grunt_i.pcx"
    ci.icon = vid.Draw_FindPic(ci.iconname)


def load_clientinfo(ci, text: str) -> None:
    """Loads a player's model, skin, weapons and icon from "name\\model/skin"."""
    text = text[:shared.MAX_QPATH - 1]
    ci.cinfo = text

    name, sep, skin_text = text.partition("\\")
    ci.name = name
    if not sep:
        skin_text = text  # no '\': the whole string is both

    if cl_main.cl_noskins.value or not skin_text:
        _register_default_clientinfo(ci)
    else:
        # the model name ends at the first '/' (or '\'); none leaves it empty
        cut = skin_text.find("/")
        if cut == -1:
            cut = skin_text.find("\\")
        if cut == -1:
            cut = 0
        model_name = skin_text[:cut]
        skin_name = skin_text[len(model_name) + 1:][:shared.MAX_QPATH - 1]

        ci.model = vid.R_RegisterModel(f"players/{model_name}/tris.md2")
        if not ci.model:
            model_name = "male"
            ci.model = vid.R_RegisterModel("players/male/tris.md2")

        ci.skin = vid.R_RegisterSkin(f"players/{model_name}/{skin_name}.pcx")
        if not ci.skin and shared_c.Q_stricmp(model_name, "male"):
            # the male model may have the skin (CTF's skins)
            model_name = "male"
            ci.model = vid.R_RegisterModel("players/male/tris.md2")
            ci.skin = vid.R_RegisterSkin(f"players/male/{skin_name}.pcx")
        if not ci.skin:
            ci.skin = vid.R_RegisterSkin(f"players/{model_name}/grunt.pcx")

        for i in range(cl_view.num_cl_weaponmodels):
            weapon = cl_view.cl_weaponmodels[i]
            ci.weaponmodel[i] = vid.R_RegisterModel(f"players/{model_name}/{weapon}")
            if not ci.weaponmodel[i] and model_name == "cyborg":
                ci.weaponmodel[i] = vid.R_RegisterModel(f"players/male/{weapon}")
            if not cl_main.cl_vwep.value:
                break  # only the first without view weapons

        ci.iconname = f"/players/{model_name}/{skin_name}_i.pcx"
        ci.icon = vid.Draw_FindPic(ci.iconname)

    # valid only with every part
    if not ci.skin or not ci.icon or not ci.model or not ci.weaponmodel[0]:
        ci.skin = ci.icon = ci.model = None
        ci.weaponmodel[0] = None


def parse_clientinfo(player: int) -> None:
    """Loads a player's skin, icon and model from their configstring."""
    cl = cl_main.cl
    load_clientinfo(cl.clientinfo[player], cl.configstrings[player + shared.CS_PLAYERSKINS])


def _in_range(i: int, start: int, count: int) -> bool:
    return start <= i < start + count


def parse_configstring() -> None:
    cl = cl_main.cl
    index = movemsg.MSG_ReadShort(_msg())
    text = movemsg.MSG_ReadString(_msg())

    if index < 0 or index >= shared.MAX_CONFIGSTRINGS:
        clientserver.Com_Printf("%s: bad index: %i\n", "CL_ParseConfigString", index)
        return

    changed = text != cl.configstrings[index]

    # the statusbar program runs over several configstrings; here it is
    # all in its first one
    if _in_range(index, shared.CS_STATUSBAR, shared.CS_STATUSBAR_END - shared.CS_STATUSBAR):
        space = shared.CS_STATUSBAR_SPACE(index)
        if len(text) >= space:
            clientserver.Com_Printf("%s: %i: statusbar code too long: %i > %i\n",
                                    "CL_ParseConfigString", index, len(text), space - 1)
            return
    elif len(text) >= shared.MAX_QPATH:
        clientserver.Com_Printf("%s: %i: string too long: %i > %i\n",
                                "CL_ParseConfigString", index, len(text), shared.MAX_QPATH - 1)
        return
    cl.configstrings[index] = text

    if _in_range(index, shared.CS_LIGHTS, shared.MAX_LIGHTSTYLES):
        cl_lights.CL_SetLightstyle(index - shared.CS_LIGHTS)
    elif index == shared.CS_CDTRACK:
        if cl.refresh_prepped:
            ogg.OGG_PlayTrack(text, True, True)
    elif _in_range(index, shared.CS_MODELS, shared.MAX_MODELS):
        if cl.refresh_prepped:
            n = index - shared.CS_MODELS
            cl.model_draw[n] = vid.R_RegisterModel(text)
            cl.model_clip[n] = collision.CM_InlineModel(text) if text[:1] == "*" else None
    # the C uses MAX_MODELS for the sounds' and images' ranges too
    elif _in_range(index, shared.CS_SOUNDS, shared.MAX_MODELS):
        if cl.refresh_prepped:
            cl.sound_precache[index - shared.CS_SOUNDS] = sound_c.S_RegisterSound(text)
    elif _in_range(index, shared.CS_IMAGES, shared.MAX_MODELS):
        if cl.refresh_prepped:
            cl.image_precache[index - shared.CS_IMAGES] = vid.Draw_FindPic(text)
    elif _in_range(index, shared.CS_PLAYERSKINS, shared.MAX_CLIENTS):
        if cl.refresh_prepped and changed:
            parse_clientinfo(index - shared.CS_PLAYERSKINS)


def parse_start_sound() -> None:
    """A sound: its flags, then the optional volume, attenuation, offset, entity and place."""
    msg = _msg()
    flags = movemsg.MSG_ReadByte(msg)
    sound_num = movemsg.MSG_ReadByte(msg)
    if sound_num < 0:
        clientserver.Com_Error(common_h.ERR_DROP, "%s: unexpected message end",
                               "CL_ParseStartSoundPacket")

    volume = (movemsg.MSG_ReadByte(msg) / 255.0 if flags & common_h.SND_VOLUME
              else common_h.DEFAULT_SOUND_PACKET_VOLUME)
    attenuation = (movemsg.MSG_ReadByte(msg) / 64.0 if flags & common_h.SND_ATTENUATION
                   else common_h.DEFAULT_SOUND_PACKET_ATTENUATION)
    offset = movemsg.MSG_ReadByte(msg) / 1000.0 if flags & common_h.SND_OFFSET else 0

    entnum = channel = 0
    if flags & common_h.SND_ENT:
        # the entity and its channel
        channel = movemsg.MSG_ReadShort(msg)
        entnum = channel >> 3
        if entnum < 0:
            clientserver.Com_Printf("%s: incorrect channel %d\n", "CL_ParseStartSoundPacket",
                                    channel)
            return
        channel &= 7

    pos = None  # at the entity
    if flags & common_h.SND_POS:
        pos = np.zeros((3,), dtype=np.float32)
        movemsg.MSG_ReadPos(msg, pos)

    if sound_num >= shared.MAX_SOUNDS:
        clientserver.Com_Printf("%s: incorrect sound id %d > MAX_SOUNDS\n",
                                "CL_ParseStartSoundPacket", sound_num)
        return
    sfx = cl_main.cl.sound_precache[sound_num]
    if sfx:
        sound_c.S_StartSound(pos, entnum, channel, sfx, volume, attenuation, offset)


# --- the commands of a server message --------------------------------------

def _disconnect() -> None:
    clientserver.Com_Error(shared.ERR_DISCONNECT, "Server disconnected\n")


def _reconnect() -> None:
    cls = cl_main.cls
    clientserver.Com_Printf("Server disconnected, reconnecting\n")
    if cls.download:
        cls.download.close()
        cls.download = None
    cls.state = CA.ca_connecting
    cls.connect_time = -99999  # check_for_resend() fires at once


def _print() -> None:
    level = movemsg.MSG_ReadByte(_msg())
    if level < 0:
        _shownet("END OF MESSAGE")
        return
    if level == shared.PRINT_CHAT:
        sound_c.S_StartLocalSound("misc/talk.wav")
        cl_console.con.ormask = 128  # chat in the other colour
    clientserver.Com_Printf("%s", movemsg.MSG_ReadString(_msg()))
    cl_console.con.ormask = 0


def _centerprint() -> None:
    cl_screen.SCR_CenterPrint(movemsg.MSG_ReadString(_msg()))


def _stufftext() -> None:
    text = movemsg.MSG_ReadString(_msg())
    clientserver.Com_DPrintf("stufftext: %s\n", text)
    cmdparser.Cbuf_AddText(text)


def _serverdata() -> None:
    cmdparser.Cbuf_Execute()  # the stuffed commands first
    parse_server_data()


def _layout() -> None:
    cl_main.cl.layout = movemsg.MSG_ReadString(_msg())[:LAYOUT_SIZE - 1]


def _out_of_place() -> None:
    clientserver.Com_Error(shared.ERR_DROP, "Out of place frame data")


SERVER_COMMANDS: dict[int, Callable[[], None]] = {
    SVC.svc_nop.value: lambda: None,
    SVC.svc_disconnect.value: _disconnect,
    SVC.svc_reconnect.value: _reconnect,
    SVC.svc_print.value: _print,
    SVC.svc_centerprint.value: _centerprint,
    SVC.svc_stufftext.value: _stufftext,
    SVC.svc_serverdata.value: _serverdata,
    SVC.svc_configstring.value: parse_configstring,
    SVC.svc_sound.value: parse_start_sound,
    SVC.svc_spawnbaseline.value: parse_baseline,
    SVC.svc_temp_entity.value: lambda: cl_tempentities.CL_ParseTEnt(),
    SVC.svc_muzzleflash.value: lambda: cl_effects.CL_AddMuzzleFlash(),
    SVC.svc_muzzleflash2.value: lambda: cl_effects.CL_AddMuzzleFlash2(),
    SVC.svc_download.value: lambda: cl_download.CL_ParseDownload(),
    SVC.svc_frame.value: parse_frame,
    SVC.svc_inventory.value: lambda: cl_inventory.CL_ParseInventory(),
    SVC.svc_layout.value: _layout,
    # the frame command reads these
    SVC.svc_playerinfo.value: _out_of_place,
    SVC.svc_packetentities.value: _out_of_place,
    SVC.svc_deltapacketentities.value: _out_of_place,
}


def parse_server_message() -> None:
    """Reads the message from the server in net_message."""
    msg = _msg()
    if cl_main.cl_shownet.value == 1:
        clientserver.Com_Printf("%i ", msg.cursize)
    elif cl_main.cl_shownet.value >= 2:
        clientserver.Com_Printf("------------------\n")

    while True:
        if msg.readcount > msg.cursize:
            clientserver.Com_Error(shared.ERR_DROP, "%s: Bad server message",
                                   "CL_ParseServerMessage")
            return

        cmd = movemsg.MSG_ReadByte(msg)
        if cmd == -1:
            _shownet("END OF MESSAGE")
            break

        _show_net_command(cmd)
        handler = SERVER_COMMANDS.get(cmd)
        if handler is None:
            clientserver.Com_Error(shared.ERR_DROP, "%s: Illegible server message\n",
                                   "CL_ParseServerMessage")
            return
        handler()

    cl_screen.CL_AddNetgraph()

    # a demo message can be saved only after its frame is parsed
    if cl_main.cls.demorecording and not cl_main.cls.demowaiting:
        cl_main.CL_WriteDemoMessage()
