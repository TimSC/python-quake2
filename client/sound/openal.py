"""The OpenAL sound backend (Yamagi's openal.c).

Copyright (C) 1997-2005 Id Software, Inc., (C) 2010 skuller.net,
(C) 2005 Stuart Dalton; GPL version 2 or later (see the other files).

``OpenALBackend`` plays the sound system's channels on OpenAL sources (one
per channel, plus one for streamed raw samples: music and cinematics),
moves the listener, and applies the EFX effects: the underwater low-pass
filter, distance occlusion and the reverb presets. ``qal.py`` loads the
OpenAL library and owns the device and context.
"""

from __future__ import annotations

import ctypes

import numpy as np

from client import cl_entities, cl_main
from client.header import client as client_h
from client.sound import ogg, qal
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
from client.sound.header import qal as qal_h
from common import clientserver, collision
from common.header import shared
from common.shared import shared as shared_c

# avg US male height / q2PlayerHeight = 1.764 / 56.0 = 0.0315
# (see PutClientInServer()'s bounding box)
METERS_PER_UNIT = 0.0315

# The OpenAL implementation has to give at least this many sources.
MIN_CHANNELS = 16

# The reverb presets: s_reverb_preset is an index into this list.
REVERB_PRESETS = [
    ("Generic", qal_h.EFX_REVERB_PRESET_GENERIC),
    ("Padded Cell", qal_h.EFX_REVERB_PRESET_PADDEDCELL),
    ("Room", qal_h.EFX_REVERB_PRESET_ROOM),
    ("Bathroom", qal_h.EFX_REVERB_PRESET_BATHROOM),
    ("LivingRoom", qal_h.EFX_REVERB_PRESET_LIVINGROOM),
    ("StoneRoom", qal_h.EFX_REVERB_PRESET_STONEROOM),
    ("Auditorium", qal_h.EFX_REVERB_PRESET_AUDITORIUM),
    ("ConcertHall", qal_h.EFX_REVERB_PRESET_CONCERTHALL),
    ("Cave", qal_h.EFX_REVERB_PRESET_CAVE),
    ("Arena", qal_h.EFX_REVERB_PRESET_ARENA),
    ("Hangar", qal_h.EFX_REVERB_PRESET_HANGAR),
    ("Carpeted Hallway", qal_h.EFX_REVERB_PRESET_CARPETEDHALLWAY),
    ("Hallway", qal_h.EFX_REVERB_PRESET_HALLWAY),
    ("Stone Corridor", qal_h.EFX_REVERB_PRESET_STONECORRIDOR),
    ("Alley", qal_h.EFX_REVERB_PRESET_ALLEY),
    ("Forest", qal_h.EFX_REVERB_PRESET_FOREST),
    ("City", qal_h.EFX_REVERB_PRESET_CITY),
    ("Mountains", qal_h.EFX_REVERB_PRESET_MOUNTAINS),
    ("Quarry", qal_h.EFX_REVERB_PRESET_QUARRY),
    ("Plain", qal_h.EFX_REVERB_PRESET_PLAIN),
    ("Parking Lot", qal_h.EFX_REVERB_PRESET_PARKINGLOT),
    ("Sewer Pipe", qal_h.EFX_REVERB_PRESET_SEWERPIPE),
    ("Underwater", qal_h.EFX_REVERB_PRESET_UNDERWATER),
    ("Drugged", qal_h.EFX_REVERB_PRESET_DRUGGED),
    ("Dizzy", qal_h.EFX_REVERB_PRESET_DIZZY),
    ("Psychotic", qal_h.EFX_REVERB_PRESET_PSYCHOTIC),
    ("Castle Small Room", qal_h.EFX_REVERB_PRESET_CASTLE_SMALLROOM),
    ("Castle Short Passage", qal_h.EFX_REVERB_PRESET_CASTLE_SHORTPASSAGE),
    ("Castle Medium Room", qal_h.EFX_REVERB_PRESET_CASTLE_MEDIUMROOM),
    ("Castle Large Room", qal_h.EFX_REVERB_PRESET_CASTLE_LARGEROOM),
    ("Castle Long Passage", qal_h.EFX_REVERB_PRESET_CASTLE_LONGPASSAGE),
    ("Castle Hall", qal_h.EFX_REVERB_PRESET_CASTLE_HALL),
    ("Castle Cupboard", qal_h.EFX_REVERB_PRESET_CASTLE_CUPBOARD),
    ("Castle Courtyard", qal_h.EFX_REVERB_PRESET_CASTLE_COURTYARD),
    ("Castle Alcove", qal_h.EFX_REVERB_PRESET_CASTLE_ALCOVE),
    ("Factory Small Room", qal_h.EFX_REVERB_PRESET_FACTORY_SMALLROOM),
    ("Factory Short Passage", qal_h.EFX_REVERB_PRESET_FACTORY_SHORTPASSAGE),
    ("Factory Medium Room", qal_h.EFX_REVERB_PRESET_FACTORY_MEDIUMROOM),
    ("Factory Large Room", qal_h.EFX_REVERB_PRESET_FACTORY_LARGEROOM),
    ("Factory Long Passage", qal_h.EFX_REVERB_PRESET_FACTORY_LONGPASSAGE),
    ("Factory Hall", qal_h.EFX_REVERB_PRESET_FACTORY_HALL),
    ("Factory Cupboard", qal_h.EFX_REVERB_PRESET_FACTORY_CUPBOARD),
    ("Factory Courtyard", qal_h.EFX_REVERB_PRESET_FACTORY_COURTYARD),
    ("Factory Alcove", qal_h.EFX_REVERB_PRESET_FACTORY_ALCOVE),
    ("Icepalace Small Room", qal_h.EFX_REVERB_PRESET_ICEPALACE_SMALLROOM),
    ("Icepalace Short Passage", qal_h.EFX_REVERB_PRESET_ICEPALACE_SHORTPASSAGE),
    ("Icepalace Medium Room", qal_h.EFX_REVERB_PRESET_ICEPALACE_MEDIUMROOM),
    ("Icepalace Large Room", qal_h.EFX_REVERB_PRESET_ICEPALACE_LARGEROOM),
    ("Icepalace Long Passage", qal_h.EFX_REVERB_PRESET_ICEPALACE_LONGPASSAGE),
    ("Icepalace Hall", qal_h.EFX_REVERB_PRESET_ICEPALACE_HALL),
    ("Icepalace Cupboard", qal_h.EFX_REVERB_PRESET_ICEPALACE_CUPBOARD),
    ("Icepalace Courtyard", qal_h.EFX_REVERB_PRESET_ICEPALACE_COURTYARD),
    ("Icepalace Alcove", qal_h.EFX_REVERB_PRESET_ICEPALACE_ALCOVE),
    ("Spacestation Small Room", qal_h.EFX_REVERB_PRESET_SPACESTATION_SMALLROOM),
    ("Spacestation Short Passage", qal_h.EFX_REVERB_PRESET_SPACESTATION_SHORTPASSAGE),
    ("Spacestation Medium Room", qal_h.EFX_REVERB_PRESET_SPACESTATION_MEDIUMROOM),
    ("Spacestation Large Room", qal_h.EFX_REVERB_PRESET_SPACESTATION_LARGEROOM),
    ("Spacestation Long Passage", qal_h.EFX_REVERB_PRESET_SPACESTATION_LONGPASSAGE),
    ("Spacestation Hall", qal_h.EFX_REVERB_PRESET_SPACESTATION_HALL),
    ("Spacestation Cupboard", qal_h.EFX_REVERB_PRESET_SPACESTATION_CUPBOARD),
    ("Spacestation Alcove", qal_h.EFX_REVERB_PRESET_SPACESTATION_ALCOVE),
    ("Wooden Small Room", qal_h.EFX_REVERB_PRESET_WOODEN_SMALLROOM),
    ("Wooden Short Passage", qal_h.EFX_REVERB_PRESET_WOODEN_SHORTPASSAGE),
    ("Wooden Medium Room", qal_h.EFX_REVERB_PRESET_WOODEN_MEDIUMROOM),
    ("Wooden Large Room", qal_h.EFX_REVERB_PRESET_WOODEN_LARGEROOM),
    ("Wooden Long Passage", qal_h.EFX_REVERB_PRESET_WOODEN_LONGPASSAGE),
    ("Wooden Hall", qal_h.EFX_REVERB_PRESET_WOODEN_HALL),
    ("Wooden Cupboard", qal_h.EFX_REVERB_PRESET_WOODEN_CUPBOARD),
    ("Wooden CourtYard", qal_h.EFX_REVERB_PRESET_WOODEN_COURTYARD),
    ("Wooden Alcove", qal_h.EFX_REVERB_PRESET_WOODEN_ALCOVE),
    ("Sport Empty Stadium", qal_h.EFX_REVERB_PRESET_SPORT_EMPTYSTADIUM),
    ("Sport Squash Court", qal_h.EFX_REVERB_PRESET_SPORT_SQUASHCOURT),
    ("Sport Small Swimming Pool", qal_h.EFX_REVERB_PRESET_SPORT_SMALLSWIMMINGPOOL),
    ("Sport Large Swimming Pool", qal_h.EFX_REVERB_PRESET_SPORT_LARGESWIMMINGPOOL),
    ("Sport Gymnasium", qal_h.EFX_REVERB_PRESET_SPORT_GYMNASIUM),
    ("Sport Full Stadium", qal_h.EFX_REVERB_PRESET_SPORT_FULLSTADIUM),
    ("Sport Stadium Tannoy", qal_h.EFX_REVERB_PRESET_SPORT_STADIUMTANNOY),
    ("Prefab Workshop", qal_h.EFX_REVERB_PRESET_PREFAB_WORKSHOP),
    ("Prefab School Room", qal_h.EFX_REVERB_PRESET_PREFAB_SCHOOLROOM),
    ("Prefab Practise Room", qal_h.EFX_REVERB_PRESET_PREFAB_PRACTISEROOM),
    ("Prefab Outhouse", qal_h.EFX_REVERB_PRESET_PREFAB_OUTHOUSE),
    ("Prefab Caravan", qal_h.EFX_REVERB_PRESET_PREFAB_CARAVAN),
    ("Dome Tomb", qal_h.EFX_REVERB_PRESET_DOME_TOMB),
    ("Pipe Small", qal_h.EFX_REVERB_PRESET_PIPE_SMALL),
    ("Dome Saintpauls", qal_h.EFX_REVERB_PRESET_DOME_SAINTPAULS),
    ("Pipe Longthin", qal_h.EFX_REVERB_PRESET_PIPE_LONGTHIN),
    ("Pipe Large", qal_h.EFX_REVERB_PRESET_PIPE_LARGE),
    ("Pipe Resonant", qal_h.EFX_REVERB_PRESET_PIPE_RESONANT),
    ("Outdoors Backyard", qal_h.EFX_REVERB_PRESET_OUTDOORS_BACKYARD),
    ("Outdoors Rolling Plains", qal_h.EFX_REVERB_PRESET_OUTDOORS_ROLLINGPLAINS),
    ("Outdoors Deep Canyon", qal_h.EFX_REVERB_PRESET_OUTDOORS_DEEPCANYON),
    ("Outdoors Creek", qal_h.EFX_REVERB_PRESET_OUTDOORS_CREEK),
    ("Outdoors Valley", qal_h.EFX_REVERB_PRESET_OUTDOORS_VALLEY),
    ("Mood Heaven", qal_h.EFX_REVERB_PRESET_MOOD_HEAVEN),
    ("Mood Hell", qal_h.EFX_REVERB_PRESET_MOOD_HELL),
    ("Mood Memory", qal_h.EFX_REVERB_PRESET_MOOD_MEMORY),
    ("Driving Commentator", qal_h.EFX_REVERB_PRESET_DRIVING_COMMENTATOR),
    ("Driving Pit Garage", qal_h.EFX_REVERB_PRESET_DRIVING_PITGARAGE),
    ("Driving Incar Racer", qal_h.EFX_REVERB_PRESET_DRIVING_INCAR_RACER),
    ("Driving Incar Sports", qal_h.EFX_REVERB_PRESET_DRIVING_INCAR_SPORTS),
    ("Driving Incar Luxury", qal_h.EFX_REVERB_PRESET_DRIVING_INCAR_LUXURY),
    ("Driving Full Grandstand", qal_h.EFX_REVERB_PRESET_DRIVING_FULLGRANDSTAND),
    ("Driving Empty Grandstand", qal_h.EFX_REVERB_PRESET_DRIVING_EMPTYGRANDSTAND),
    ("Driving Tunnel", qal_h.EFX_REVERB_PRESET_DRIVING_TUNNEL),
    ("City Streets", qal_h.EFX_REVERB_PRESET_CITY_STREETS),
    ("City Subway", qal_h.EFX_REVERB_PRESET_CITY_SUBWAY),
    ("City Museum", qal_h.EFX_REVERB_PRESET_CITY_MUSEUM),
    ("City Library", qal_h.EFX_REVERB_PRESET_CITY_LIBRARY),
    ("City Underpass", qal_h.EFX_REVERB_PRESET_CITY_UNDERPASS),
    ("City Abandoned", qal_h.EFX_REVERB_PRESET_CITY_ABANDONED),
    ("Dusty Room", qal_h.EFX_REVERB_PRESET_DUSTYROOM),
    ("Chapel", qal_h.EFX_REVERB_PRESET_CHAPEL),
    ("Smallwater Room", qal_h.EFX_REVERB_PRESET_SMALLWATERROOM),
]

# s_reverb_preset -2 picks one by the size of the space around the listener:
# (average distance to the walls below which it applies, preset)
AUTO_REVERB = [(100, 41), (200, 26), (330, 5), (450, 12), (650, 18), (float("inf"), 17)]
UNDERWATER_REVERB = 22

# Where apply_reverb() traces to from the listener: forward, back, left,
# right, up, down.
_REVERB_DIRECTIONS = np.array([
    [1000000, 0, 0], [-1000000, 0, 0], [0, 1000000, 0],
    [0, -1000000, 0], [0, 0, 1000000], [0, 0, -1000000],
], dtype=np.float32)

_ZERO = np.zeros((3,), dtype=np.float32)


def al_vector(v) -> tuple[float, float, float]:
    """A Quake vector in OpenAL's coordinates."""
    return float(-v[1]), float(v[2]), float(-v[0])


def al_format(width: int, channels: int) -> int:
    """The OpenAL buffer format for a sample width (bytes) and channel count."""
    return {
        (1, 1): qal_h.AL_FORMAT_MONO8, (1, 2): qal_h.AL_FORMAT_STEREO8,
        (2, 1): qal_h.AL_FORMAT_MONO16, (2, 2): qal_h.AL_FORMAT_STEREO16,
    }.get((width, channels), qal_h.AL_FORMAT_MONO8)


def _efx_available() -> bool:
    return all((
        qal.qalAuxiliaryEffectSloti, qal.qalDeleteAuxiliaryEffectSlots, qal.qalDeleteEffects,
        qal.qalDeleteFilters, qal.qalEffectf, qal.qalEffecti, qal.qalFilterf, qal.qalFilteri,
        qal.qalGenAuxiliaryEffectSlots, qal.qalGenEffects, qal.qalGenFilters,
    ))


def _from_listener(ch: sound_local.channel_t) -> bool:
    """A channel that plays at the listener, at full volume."""
    return ch.entnum == -1 or ch.entnum == cl_main.cl.playernum + 1 or not ch.dist_mult


class OpenALBackend:
    """The sound backend on OpenAL (see client/sound/backend.py)."""

    name = "openal"

    def __init__(self) -> None:
        self.active_buffers = 0  # OpenAL buffers in use: sounds and queued raw samples
        self.sources: list[int] = []  # one per channel
        self.stream_source = qal.ALuint()
        self.stream_playing = False
        # buffers raw_samples() queued since the last stream update
        self.stream_queued = 0
        self.frame_count = 0
        self.underwater_filter = qal.ALuint()
        self.occlusion_filter = qal.ALuint()
        self.reverb_effect = qal.ALuint()
        self.reverb_slot = qal.ALuint()
        self.last_reverb = -1
        self.underwater_enabled = False

    @classmethod
    def start(cls) -> OpenALBackend | None:
        """Opens OpenAL and makes the sources; None (with a message) if it can't."""
        if not qal.QAL_Init():
            clientserver.Com_Printf("ERROR: OpenAL failed to initialize.\n")
            return None

        if not qal.qalIsExtensionPresent(b"AL_EXT_LINEAR_DISTANCE"):
            clientserver.Com_Printf(
                "ERROR: Required AL_EXT_LINEAR_DISTANCE extension is missing.\n")
            qal.QAL_Shutdown()
            return None

        backend = cls()
        qal.qalGetError()
        qal.qalGenSources(1, ctypes.byref(backend.stream_source))
        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            clientserver.Com_Printf("ERROR: Couldn't get a single Source.\n")
            qal.QAL_Shutdown()
            return None

        # one source less than MAX_CHANNELS: the stream has one
        while len(backend.sources) < sound_local.MAX_CHANNELS - 1:
            source = qal.ALuint()
            qal.qalGenSources(1, ctypes.byref(source))
            if qal.qalGetError() != qal_h.AL_NO_ERROR:
                break
            backend.sources.append(source.value)

        if len(backend.sources) < MIN_CHANNELS - 1:
            clientserver.Com_Printf(f"ERROR: Required at least {MIN_CHANNELS} sources, "
                                    f"but got {len(backend.sources) + 1}.\n")
            qal.QAL_Shutdown()
            return None

        backend._init_stream_source()
        backend._init_underwater_filter()
        backend._init_occlusion_filter()
        backend._init_reverb_effect()

        clientserver.Com_Printf(f"Number of OpenAL sources: {len(backend.sources)}\n\n")

        if sound_c.s_doppler.value:
            qal.qalDopplerFactor(2.0)  # exaggerated, realistic is barely noticeable
        qal.qalDistanceModel(qal_h.AL_LINEAR_DISTANCE_CLAMPED)
        return backend

    @property
    def num_channels(self) -> int:
        return len(self.sources)

    # -- setup ------------------------------------------------------------

    def _init_stream_source(self) -> None:
        src = self.stream_source
        qal.qalSource3f(src, qal_h.AL_POSITION, 0.0, 0.0, 0.0)
        qal.qalSource3f(src, qal_h.AL_VELOCITY, 0.0, 0.0, 0.0)
        qal.qalSource3f(src, qal_h.AL_DIRECTION, 0.0, 0.0, 0.0)
        qal.qalSourcef(src, qal_h.AL_ROLLOFF_FACTOR, 0.0)
        qal.qalSourcei(src, qal_h.AL_BUFFER, 0)
        qal.qalSourcei(src, qal_h.AL_LOOPING, qal_h.AL_FALSE)
        qal.qalSourcei(src, qal_h.AL_SOURCE_RELATIVE, qal_h.AL_TRUE)

    def _make_lowpass(self, flt: ctypes.c_uint, what: str) -> bool:
        """Makes a low-pass filter in flt (0 if it can't)."""
        flt.value = 0
        if not _efx_available():
            return False
        qal.qalGenFilters(1, ctypes.byref(flt))
        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            clientserver.Com_Printf(f"Couldn't generate {what}!\n")
            return False
        qal.qalFilteri(flt, qal_h.AL_FILTER_TYPE, qal_h.AL_FILTER_LOWPASS)
        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            clientserver.Com_Printf("Low pass filter is not supported!\n")
            return False
        qal.qalFilterf(flt, qal_h.AL_LOWPASS_GAIN, qal_h.AL_LOWPASS_DEFAULT_GAIN)
        return True

    def _init_underwater_filter(self) -> None:
        # Yamagi keeps the filter name when the low pass type fails
        if self._make_lowpass(self.underwater_filter, "an OpenAL filter"):
            sound_c.s_underwater.modified = True
            sound_c.s_underwater_gain_hf.modified = True

    def _init_occlusion_filter(self) -> None:
        if self._make_lowpass(self.occlusion_filter, "occlusion filter"):
            qal.qalFilterf(self.occlusion_filter, qal_h.AL_LOWPASS_GAINHF,
                           qal_h.AL_LOWPASS_DEFAULT_GAINHF)
        else:
            self.occlusion_filter.value = 0

    def _init_reverb_effect(self) -> None:
        if not _efx_available():
            return
        qal.qalGenEffects(1, ctypes.byref(self.reverb_effect))
        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            clientserver.Com_Printf("Couldn't generate an OpenAL effect!\n")
            return
        qal.qalGenAuxiliaryEffectSlots(1, ctypes.byref(self.reverb_slot))
        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            clientserver.Com_Printf("Couldn't generate an OpenAL auxiliary effect slot!\n")
            return
        qal.qalEffecti(self.reverb_effect.value, qal_h.AL_EFFECT_TYPE, qal_h.AL_EFFECT_REVERB)
        self.set_reverb(int(sound_c.s_reverb_preset.value))

    def shutdown(self) -> None:
        clientserver.Com_Printf("Shutting down OpenAL.\n")
        self.stop_all_channels()

        qal.qalDeleteSources(1, ctypes.byref(self.stream_source))
        if qal.qalDeleteFilters:  # missing without ALC_EXT_EFX
            qal.qalDeleteFilters(1, ctypes.byref(self.underwater_filter))
            qal.qalDeleteFilters(1, ctypes.byref(self.occlusion_filter))
            qal.qalDeleteAuxiliaryEffectSlots(1, ctypes.byref(self.reverb_slot))
            qal.qalDeleteEffects(1, ctypes.byref(self.reverb_effect))

        if self.sources:
            names = (qal.ALuint * len(self.sources))(*self.sources)
            qal.qalDeleteSources(len(self.sources), names)
            self.sources = []

        qal.QAL_Shutdown()

    # -- sounds -----------------------------------------------------------

    def _gen_buffer(self, data: bytes, size: int, fmt: int, rate: int) -> qal.ALuint:
        name = qal.ALuint()
        qal.qalGenBuffers(1, ctypes.byref(name))
        qal.qalBufferData(name, fmt, data, size, rate)
        self.active_buffers += 1
        return name

    def _delete_buffer(self, name: qal.ALuint) -> None:
        qal.qalDeleteBuffers(1, ctypes.byref(name))
        self.active_buffers -= 1

    def upload_sfx(self, s: sound_local.sfx_t, info: sound_local.wavinfo_t, data, volume: int,
                   begin_length: int, end_length: int,
                   attack_length: int, fade_length: int) -> sound_local.sfxcache_t | None:
        """Uploads a sound to an OpenAL buffer and gives it a placeholder cache.

        The cache holds no samples, only the buffer name and the lengths
        (in milliseconds) the sound system needs.
        """
        size = info.samples * info.width
        if not size:
            return None

        qal.qalGetError()
        name = self._gen_buffer(bytes(data[:size]), size, al_format(info.width, info.channels),
                                info.rate)
        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            return None

        sc = s.cache = sound_local.sfxcache_t()
        sc.length = (info.samples * 1000) // info.rate
        sc.loopstart = info.loopstart
        sc.width = info.width
        sc.size = size
        sc.bufnum = name.value
        sc.stereo = info.channels - 1
        sc.volume = int(volume)
        sc.begin = int(begin_length * 1000 / info.rate)
        sc.end = int(end_length * 1000 / info.rate)
        sc.fade = int(fade_length * 1000 / info.rate)
        sc.attack = int(attack_length * 1000 / info.rate)
        return sc

    def delete_sfx(self, s: sound_local.sfx_t) -> None:
        """Deletes a sound's buffer (the sound system frees the cache)."""
        if s.cache:
            self._delete_buffer(qal.ALuint(s.cache.bufnum))

    # -- reverb -----------------------------------------------------------

    def set_reverb(self, preset: int) -> None:
        """Sets the reverb effect to a preset, unless it's set already."""
        if preset == self.last_reverb or not 0 <= preset < len(REVERB_PRESETS):
            return
        if not qal.qalEffectf:
            return  # no EFX
        reverb = REVERB_PRESETS[preset][1]
        self.last_reverb = preset

        effect = self.reverb_effect.value
        for param, value in (
            (qal_h.AL_REVERB_DENSITY, reverb.flDensity),
            (qal_h.AL_REVERB_DIFFUSION, reverb.flDiffusion),
            (qal_h.AL_REVERB_GAIN, reverb.flGain),
            (qal_h.AL_REVERB_GAINHF, reverb.flGainHF),
            (qal_h.AL_REVERB_DECAY_TIME, reverb.flDecayTime),
            (qal_h.AL_REVERB_DECAY_HFRATIO, reverb.flDecayHFRatio),
            (qal_h.AL_REVERB_REFLECTIONS_GAIN, reverb.flReflectionsGain),
            (qal_h.AL_REVERB_REFLECTIONS_DELAY, reverb.flReflectionsDelay),
            (qal_h.AL_REVERB_LATE_REVERB_GAIN, reverb.flLateReverbGain),
            (qal_h.AL_REVERB_LATE_REVERB_DELAY, reverb.flLateReverbDelay),
            (qal_h.AL_REVERB_AIR_ABSORPTION_GAINHF, reverb.flAirAbsorptionGainHF),
            (qal_h.AL_REVERB_ROOM_ROLLOFF_FACTOR, reverb.flRoomRolloffFactor),
        ):
            qal.qalEffectf(effect, param, value)
        qal.qalEffecti(effect, qal_h.AL_REVERB_DECAY_HFLIMIT, reverb.iDecayHFLimit)
        qal.qalAuxiliaryEffectSloti(self.reverb_slot.value, qal_h.AL_EFFECTSLOT_EFFECT, effect)

    def apply_reverb(self) -> None:
        """Picks a reverb preset by the size of the space around the listener."""
        if self.reverb_effect.value == 0:
            return

        average = 0.0
        length = np.zeros((3,), dtype=np.float32)
        for direction in _REVERB_DIRECTIONS:
            trace = collision.CM_BoxTrace(sound_c.listener_origin, direction, _ZERO, _ZERO,
                                          0, shared.MASK_DEADSOLID)
            shared.VectorSubtract(trace.endpos, sound_c.listener_origin, length)
            average += shared_c.VectorLength(length)
        average /= 5  # five, as down is near to us

        for limit, preset in AUTO_REVERB:
            if average < limit:
                self.set_reverb(preset)
                break

    def _update_reverb_cvar(self) -> None:
        cv = sound_c.s_reverb_preset
        if not cv.modified:
            return
        cv.modified = False

        preset = int(cv.value)
        if preset == -2:
            clientserver.Com_Printf("Reverb set to: AUTO\n")
        elif preset == -1:
            clientserver.Com_Printf("Reverb set to: Disabled\n")
        elif 0 <= preset < len(REVERB_PRESETS):
            clientserver.Com_Printf(f"Reverb set to: {REVERB_PRESETS[preset][0]}\n")
            self.set_reverb(preset)
        else:
            clientserver.Com_Printf("Uknown reverb effect, supported:\n-2: Auto\n-1: Disabled\n")
            for i, (name, _) in enumerate(REVERB_PRESETS):
                clientserver.Com_Printf(f"{i}: {name}\n")

    # -- underwater -------------------------------------------------------

    def _set_direct_filter(self, flt: int) -> None:
        for source in self.sources:
            qal.qalSourcei(source, qal_h.AL_DIRECT_FILTER, flt)

    def underwater(self) -> None:
        """The listener went under water: muffle every source."""
        if not self.underwater_enabled or self.underwater_filter.value == 0:
            return
        self._set_direct_filter(self.underwater_filter.value)
        self.set_reverb(UNDERWATER_REVERB)

    def overwater(self) -> None:
        """The listener came out of the water."""
        if not self.underwater_enabled or self.underwater_filter.value == 0:
            return
        self._set_direct_filter(qal_h.AL_FILTER_NULL)
        self.set_reverb(int(sound_c.s_reverb_preset.value))

    def _update_underwater_cvars(self) -> None:
        if self.underwater_filter.value == 0:
            return

        update = False
        if sound_c.s_underwater.modified:
            update = True
            sound_c.s_underwater.modified = False
            self.underwater_enabled = int(sound_c.s_underwater.value) != 0
        if sound_c.s_underwater_gain_hf.modified:
            update = True
            sound_c.s_underwater_gain_hf.modified = False
        if not update:
            return

        gain_hf = min(max(sound_c.s_underwater_gain_hf.value, qal_h.AL_LOWPASS_MIN_GAINHF),
                      qal_h.AL_LOWPASS_MAX_GAINHF)
        qal.qalFilterf(self.underwater_filter, qal_h.AL_LOWPASS_GAINHF, gain_hf)

        under = self.underwater_enabled and sound_c.snd_is_underwater
        self._set_direct_filter(self.underwater_filter.value if under else 0)

    # -- channels ---------------------------------------------------------

    def _spatialize(self, ch: sound_local.channel_t) -> None:
        """Moves a channel's source to where its sound comes from."""
        if _from_listener(ch):
            return  # relative, at the listener (see start_channel())

        origin = np.zeros((3,), dtype=np.float32)
        if ch.fixed_origin:
            shared.VectorCopy(ch.origin, origin)
            qal.qalSource3f(ch.srcnum, qal_h.AL_POSITION, *al_vector(origin))
            return

        sound_c.GetEntitySoundOrigin(ch.entnum, sound_c.listener_origin, origin)
        qal.qalSource3f(ch.srcnum, qal_h.AL_POSITION, *al_vector(origin))

        if sound_c.s_doppler.value:
            velocity = np.zeros((3,), dtype=np.float32)
            cl_entities.CL_GetEntitySoundVelocity(ch.entnum, velocity)
            shared_c.VectorScale(velocity, METERS_PER_UNIT, velocity)
            qal.qalSource3f(ch.srcnum, qal_h.AL_VELOCITY, *al_vector(velocity))

        occluded = False
        strength = sound_c.s_occlusion_strength.value
        if not sound_c.snd_is_underwater and strength and self.occlusion_filter.value != 0:
            trace = collision.CM_BoxTrace(origin, sound_c.listener_origin, _ZERO, _ZERO,
                                          0, shared.MASK_PLAYERSOLID)
            if trace.fraction < 1.0:
                distance = np.zeros((3,), dtype=np.float32)
                shared.VectorSubtract(origin, sound_c.listener_origin, distance)
                dist = shared_c.VectorLength(distance)

                gain = 1.0 - ((dist / 1000) * (1.0 - strength))
                qal.qalSourcef(ch.srcnum, qal_h.AL_GAIN, min(max(gain, 0), 1))

                # high frequencies fade with distance, but keep enough for
                # HRTF's spatial cues
                gain_hf = 1.0 - (0.5 * strength * min(dist / 1000.0, 1.0))
                gain_hf = min(max(gain_hf, qal_h.AL_LOWPASS_MIN_GAINHF),
                              qal_h.AL_LOWPASS_MAX_GAINHF)
                qal.qalFilterf(self.occlusion_filter, qal_h.AL_LOWPASS_GAINHF, gain_hf)
                qal.qalSourcei(ch.srcnum, qal_h.AL_DIRECT_FILTER, self.occlusion_filter.value)
                occluded = True

        reverb = False
        if not occluded:
            if not sound_c.snd_is_underwater:
                qal.qalSourcei(ch.srcnum, qal_h.AL_DIRECT_FILTER, 0)
            if sound_c.s_reverb_preset.value != -1:
                qal.qalSource3i(ch.srcnum, qal_h.AL_AUXILIARY_SEND_FILTER,
                                self.reverb_slot.value, 0, qal_h.AL_FILTER_NULL)
                reverb = True
        if not reverb:
            qal.qalSource3i(ch.srcnum, qal_h.AL_AUXILIARY_SEND_FILTER, 0, 0, qal_h.AL_FILTER_NULL)

    def _play(self, ch: sound_local.channel_t) -> None:
        if sound_c.s_show.value > 1:
            clientserver.Com_Printf("{}: {}\n".format("AL_PlayChannel", ch.sfx.name))

        vol = min(ch.oal_vol, 1.0)
        ch.srcnum = src = self.sources[sound_c.channels.index(ch)]

        qal.qalGetError()
        qal.qalSourcef(src, qal_h.AL_REFERENCE_DISTANCE, sound_local.SOUND_FULLVOLUME)
        qal.qalSourcef(src, qal_h.AL_MAX_DISTANCE, 8192)
        qal.qalSourcef(src, qal_h.AL_ROLLOFF_FACTOR,
                       ch.dist_mult * (8192 - sound_local.SOUND_FULLVOLUME))
        qal.qalSourcef(src, qal_h.AL_GAIN, vol)
        qal.qalSourcei(src, qal_h.AL_BUFFER, ch.sfx.cache.bufnum)
        qal.qalSourcei(src, qal_h.AL_LOOPING, qal_h.AL_TRUE if ch.autosound else qal_h.AL_FALSE)

        if _from_listener(ch):
            # at the listener, at full volume
            qal.qalSource3f(src, qal_h.AL_POSITION, 0.0, 0.0, 0.0)
            qal.qalSourcei(src, qal_h.AL_SOURCE_RELATIVE, qal_h.AL_TRUE)
        else:
            qal.qalSourcei(src, qal_h.AL_SOURCE_RELATIVE, qal_h.AL_FALSE)

        self._spatialize(ch)
        qal.qalSourcePlay(src)

        if qal.qalGetError() != qal_h.AL_NO_ERROR:
            self.stop_channel(ch)  # don't keep a broken channel

    def start_channel(self, ch: sound_local.channel_t, volume: float, master: float) -> None:
        ch.oal_vol = volume * master  # clamped to 1.0 in _play()
        self._play(ch)

    def stop_channel(self, ch: sound_local.channel_t) -> None:
        if sound_c.s_show.value > 1:
            clientserver.Com_Printf("{}: {}\n".format("AL_StopChannel", ch.sfx.name))
        qal.qalSourceStop(ch.srcnum)
        qal.qalSourcei(ch.srcnum, qal_h.AL_BUFFER, qal_h.AL_NONE)
        ch.clear()

    def _active_channels(self):
        return (ch for ch in sound_c.channels[:sound_c.s_numchannels] if ch.sfx)

    def stop_all_channels(self) -> None:
        for ch in list(self._active_channels()):
            self.stop_channel(ch)
        sound_c.s_rawend = 0
        self._stream_die()

    def playsound_start(self, timeofs: float, volume: float, painted: int) -> tuple[int, float]:
        return int(painted + timeofs * 1000), volume  # OpenAL counts in milliseconds

    def _find_looping_sound(self, entnum: int, sfx: sound_local.sfx_t):
        for ch in self._active_channels():
            if ch.autosound and ch.entnum == entnum and ch.sfx is sfx:
                return ch
        return None

    def _add_loop_sounds(self) -> None:
        """Keeps the entities' looping sounds playing, one channel each."""
        cl = cl_main.cl
        if (cl_main.cls.state != client_h.connstate_t.ca_active
                or (cl_main.cl_paused.value and cl_main.cl_audiopaused.value)
                or not sound_c.s_ambient.value):
            return

        sounds = [0] * shared.MAX_EDICTS
        sound_c.S_BuildSoundList(sounds)

        for i in range(cl.frame.num_entities):
            if not sounds[i]:
                continue
            sfx = cl.sound_precache[sounds[i]]
            if not sfx or not sfx.cache:
                continue  # bad sound effect
            sc = sfx.cache

            num = (cl.frame.parse_entities + i) & (client_h.MAX_PARSE_ENTITIES - 1)
            ent = cl_main.cl_parse_entities[num]

            ch = self._find_looping_sound(ent.number, sfx)
            if ch:
                ch.autoframe = self.frame_count
                ch.end = sound_c.paintedtime + sc.length
                continue

            ch = sound_c.S_PickChannel(0, 0)
            if not ch:
                continue

            ch.autosound = True  # removed next frame unless still there
            ch.autoframe = self.frame_count
            ch.sfx = sfx
            ch.entnum = ent.number
            ch.master_vol = 1
            ch.dist_mult = sound_local.SOUND_LOOPATTENUATE
            ch.end = sound_c.paintedtime + sc.length
            # looping sounds play at full volume (SDL_AddLoopSounds() uses 255)
            ch.oal_vol = sound_c.s_volume.value
            self._play(ch)

    # -- raw samples (music, cinematics) ------------------------------------

    def _unqueue(self, count: int) -> None:
        buffer = qal.ALuint()
        for _ in range(count):
            qal.qalSourceUnqueueBuffers(self.stream_source, 1, ctypes.byref(buffer))
            self._delete_buffer(buffer)

    def _source_int(self, source, param: int) -> int:
        value = qal.ALint()
        qal.qalGetSourcei(source, param, ctypes.byref(value))
        return value.value

    def _stream_die(self) -> None:
        """Stops the stream and drops its buffers."""
        if not qal.qalSourceStop:
            return  # OpenAL might not be initialised yet
        self.stream_playing = False
        qal.qalSourceStop(self.stream_source)
        self._unqueue(self._source_int(self.stream_source, qal_h.AL_BUFFERS_QUEUED))
        self.stream_queued = 0

    def _stream_update(self) -> None:
        """Drops played stream buffers and restarts the stream if it stopped."""
        src = self.stream_source
        if self._source_int(src, qal_h.AL_SOURCE_STATE) == qal_h.AL_STOPPED:
            self.stream_playing = False
            # A source that ran dry (a cinematic paused by the menu or
            # console) stops with its played buffers still queued, and
            # playing it again would loop the last chunk. Drop them, but
            # keep the ones queued since the last update: a stopped source
            # counts every buffer as processed.
            self._unqueue(max(self._source_int(src, qal_h.AL_BUFFERS_QUEUED)
                              - self.stream_queued, 0))
        else:
            self._unqueue(self._source_int(src, qal_h.AL_BUFFERS_PROCESSED))

        if not self.stream_playing and self._source_int(src, qal_h.AL_BUFFERS_QUEUED):
            qal.qalSourcePlay(src)
            self.stream_playing = True
        self.stream_queued = 0

    def raw_samples(self, samples: int, rate: int, width: int, channels: int,
                    data, volume: float) -> None:
        """Queues raw samples (music or a cinematic's sound) on the stream."""
        size = samples * width * channels
        buffer = self._gen_buffer(bytes(data), size, al_format(width, channels), rate)
        qal.qalSourcef(self.stream_source, qal_h.AL_GAIN, min(volume, 1.0))
        qal.qalSourceQueueBuffers(self.stream_source, 1, ctypes.byref(buffer))
        self.stream_queued += 1
        sound_c.s_rawend += samples  # as S_RawSamples() keeps it

    def unqueue_raw_samples(self) -> None:
        """Drops the queued raw samples (music stops on silence)."""
        self._stream_die()

    # -- every frame ------------------------------------------------------

    def update(self) -> None:
        sound_c.paintedtime = cl_main.cls.realtime

        # Without an output device skip the frame, after paintedtime moved
        # on: otherwise sound and game drift apart.
        if not qal.QAL_RecoverLostDevice():
            return

        # the listener
        orientation = (qal.ALfloat * 6)(*al_vector(sound_c.listener_forward),
                                        *al_vector(sound_c.listener_up))
        qal.qalListener3f(qal_h.AL_POSITION, *al_vector(sound_c.listener_origin))
        qal.qalListenerfv(qal_h.AL_ORIENTATION, orientation)

        if sound_c.s_reverb_preset.value == -2:
            self.apply_reverb()
        elif sound_c.s_reverb_preset.value >= 0:
            self.set_reverb(int(sound_c.s_reverb_preset.value))

        if sound_c.s_doppler.value:
            velocity = np.zeros((3,), dtype=np.float32)
            cl_entities.CL_GetViewVelocity(velocity)
            shared_c.VectorScale(velocity, METERS_PER_UNIT, velocity)
            qal.qalListener3f(qal_h.AL_VELOCITY, *al_vector(velocity))

        # the channels: drop the finished ones and move the others
        state = qal.ALint()
        for ch in list(self._active_channels()):
            if ch.autosound:
                if ch.autoframe != self.frame_count:
                    self.stop_channel(ch)  # looping sounds are added again each frame
                    continue
            else:
                qal.qalGetError()
                qal.qalGetSourcei(ch.srcnum, qal_h.AL_SOURCE_STATE, ctypes.byref(state))
                if qal.qalGetError() != qal_h.AL_NO_ERROR or state.value == qal_h.AL_STOPPED:
                    self.stop_channel(ch)
                    continue

            if sound_c.s_show.value:
                clientserver.Com_Printf(f"{ch.master_vol:3} {ch.sfx.name}\n")
            self._spatialize(ch)

        self.frame_count += 1

        self._add_loop_sounds()
        ogg.OGG_Stream()  # the music
        self._stream_update()

        # start the playsounds that are due
        while sound_c.s_pendingplays and sound_c.s_pendingplays[0].begin <= sound_c.paintedtime:
            sound_c.S_IssuePlaysound(sound_c.s_pendingplays[0])

        self._update_underwater_cvars()
        self._update_reverb_cvar()

    def sound_info(self) -> None:
        qal.QAL_SoundInfo(True)
