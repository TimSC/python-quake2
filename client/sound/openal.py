"""The OpenAL sound backend (Yamagi's openal.c).

Copyright (C) 1997-2005 Id Software, Inc., (C) 2010 skuller.net,
(C) 2005 Stuart Dalton; GPL version 2 or later (see the other files).

``OpenALBackend`` plays the sound system's channels through AudioEngine
voices, plus one source for streamed raw samples (music and cinematics),
moves the listener, and applies the EFX effects: the underwater low-pass
filter, distance occlusion and the reverb presets. AudioEngine owns static
sounds and voices; the backend owns the stream, effects and playback device.
"""

from collections.abc import Callable, Iterator, Sequence
from typing import Any, Self

import numpy as np
import openal_py as al

from client import cl_entities, cl_main
from client.header import client as client_h
from client.sound import ogg
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
from client.sound.header import qal as qal_h
from common import clientserver, cmdparser, collision, cvar
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


def al_vector(v: Sequence[float] | np.ndarray) -> tuple[float, float, float]:
    """A Quake vector in OpenAL's coordinates."""
    return float(-v[1]), float(v[2]), float(-v[0])


def al_format(width: int, channels: int) -> al.AudioFormat:
    """The OpenAL buffer format for a sample width (bytes) and channel count."""
    return {
        (1, 1): al.AudioFormat.MONO8, (1, 2): al.AudioFormat.STEREO8,
        (2, 1): al.AudioFormat.MONO16, (2, 2): al.AudioFormat.STEREO16,
    }.get((width, channels), al.AudioFormat.MONO8)


def _from_listener(ch: sound_local.channel_t) -> bool:
    """A channel that plays at the listener, at full volume."""
    return ch.entnum == -1 or ch.entnum == cl_main.cl.playernum + 1 or not ch.dist_mult


class ChannelAudioEngine(al.AudioEngine):
    """Configure Quake's attenuation and effect routes before a voice starts."""

    configure_voice: Callable[[al.Voice], None] | None = None

    def _create_voice(self, sound: al.Sound, source: al.Source) -> al.Voice:
        voice = super()._create_voice(sound, source)
        if self.configure_voice is not None:
            self.configure_voice(voice)
        return voice


class OpenALBackend:
    """The sound backend on OpenAL (see client/sound/backend.py)."""

    name: str = "openal"

    def __init__(self, audio: ChannelAudioEngine) -> None:
        self.audio: ChannelAudioEngine = audio
        self.device: al.Device = audio.device
        self.context: al.Context = audio.context
        self.has_disconnect: bool = self.device.supports("ALC_EXT_disconnect")
        self.channel_count: int = 0
        self.stream_source: al.Source = self.context.create_source(
            relative=True, rolloff_factor=0.0)
        self.stream_playing: bool = False
        self.stream_queued: int = 0
        self.frame_count: int = 0
        self.underwater_filter: al.Filter | None = None
        self.occlusion_filter: al.Filter | None = None
        self.reverb_effect: al.Effect | None = None
        self.reverb_slot: al.AuxiliaryEffectSlot | None = None
        self.last_reverb: int = -1
        self.underwater_enabled: bool = False
        self.disconnect_frames: int = 0
        self.buffers: set[al.Buffer] = set()
        self.sounds: set[al.Sound] = set()

    @classmethod
    def start(cls) -> Self | None:
        """Open the device and sources; report failures through the console."""
        selected = cvar.Cvar_Get("al_device", "", shared.CVAR_ARCHIVE)
        driver = cvar.Cvar_Get("al_driver", "libopenal.so.1", shared.CVAR_ARCHIVE)
        assert selected is not None and driver is not None
        if ".." in driver.string or any(c in driver.string for c in ":/\\"):
            clientserver.Com_Printf(
                "al_driver must not contain '..', ':', '/' or '\\': "
                f"{driver.string}\n")
            return None

        clientserver.Com_Printf(f"OpenAL library: {al.library_path()}\n")
        device = None
        audio = None
        backend = None
        try:
            clientserver.Com_Printf("...opening OpenAL device: ")
            device = al.Device.open(selected.string or None)
            clientserver.Com_Printf("ok\n...creating OpenAL context: ")
            audio = ChannelAudioEngine(device=device, max_voices=sound_local.MAX_CHANNELS - 1)
            context = audio.context
            clientserver.Com_Printf("ok\n...making context current: ")
            # The game owns the process's playback context on the frame thread.
            # Pyglet uses its silent driver and only decodes music.
            context.make_current()
            clientserver.Com_Printf("ok\n\n")
            if not context.supports("AL_EXT_LINEAR_DISTANCE"):
                clientserver.Com_Printf(
                    "ERROR: Required AL_EXT_LINEAR_DISTANCE extension is missing.\n")
                audio.close()
                device.close()
                return None

            backend = cls(audio)
            # Probe the same minimum capacity as Yamagi, then let AudioEngine
            # allocate and reclaim voices as channels start and finish.
            probes: list[al.Source] = []
            try:
                while len(probes) < sound_local.MAX_CHANNELS - 1:
                    try:
                        probes.append(context.create_source())
                    except al.ALLError:
                        break
                backend.channel_count = len(probes)
            finally:
                for source in probes:
                    source.close()
            if backend.channel_count < MIN_CHANNELS - 1:
                clientserver.Com_Printf(f"ERROR: Required at least {MIN_CHANNELS} sources, "
                                        f"but got {backend.channel_count + 1}.\n")
                backend.shutdown()
                return None

            backend._init_underwater_filter()
            backend._init_occlusion_filter()
            backend._init_reverb_effect()
            if sound_c.s_doppler.value:
                context.doppler_factor = 2.0  # exaggerated, realistic is barely noticeable
            context.distance_model = al.DistanceModel.LINEAR_CLAMPED
            backend._sound_info(False)
            clientserver.Com_Printf(f"Number of OpenAL sources: {backend.channel_count}\n\n")
            return backend
        except (al.OpenALError, al.LifecycleError) as error:
            clientserver.Com_DPrintf(f"failed: {error}\n")
            if backend is not None:
                backend.shutdown()
            else:
                if audio is not None:
                    audio.close()
                if device is not None:
                    device.close()
            clientserver.Com_Printf("ERROR: OpenAL failed to initialize.\n")
            return None

    @property
    def active_buffers(self) -> int:
        return len(self.buffers) + len(self.sounds)

    @property
    def num_channels(self) -> int:
        return self.channel_count

    def _make_lowpass(self, what: str) -> al.Filter | None:
        if not self.device.supports("ALC_EXT_EFX"):
            return None
        try:
            return self.context.create_filter(al.FilterType.LOWPASS, gain=1.0, gain_hf=1.0)
        except (al.ALLError, NotImplementedError):
            clientserver.Com_Printf(f"Couldn't generate {what}!\n")
            return None

    def _init_underwater_filter(self) -> None:
        self.underwater_filter = self._make_lowpass("an OpenAL filter")
        if self.underwater_filter is not None:
            sound_c.s_underwater.modified = True
            sound_c.s_underwater_gain_hf.modified = True

    def _init_occlusion_filter(self) -> None:
        self.occlusion_filter = self._make_lowpass("occlusion filter")

    def _init_reverb_effect(self) -> None:
        if not self.device.supports("ALC_EXT_EFX"):
            return
        try:
            self.reverb_effect = self.context.create_effect(al.EffectType.REVERB)
            self.reverb_slot = self.context.create_effect_slot(effect=self.reverb_effect)
            self.set_reverb(int(sound_c.s_reverb_preset.value))
        except (al.ALLError, NotImplementedError):
            clientserver.Com_Printf("Couldn't generate an OpenAL reverb effect!\n")
            if self.reverb_slot is not None:
                self.reverb_slot.close()
                self.reverb_slot = None
            if self.reverb_effect is not None:
                self.reverb_effect.close()
                self.reverb_effect = None

    def shutdown(self) -> None:
        if self.context.closed:
            return
        clientserver.Com_Printf("Shutting down OpenAL.\n")
        self.stop_all_channels()
        # Sources retain their buffers and effect routes. Release them first.
        self.stream_source.close()
        self.audio.stop_all()
        for buffer in list(self.buffers):
            self._delete_buffer(buffer)
        for resource in (self.reverb_slot, self.reverb_effect,
                         self.underwater_filter, self.occlusion_filter):
            if resource is not None:
                resource.close()
        self.audio.close()
        self.sounds.clear()
        self.device.close()

    # -- sounds -----------------------------------------------------------

    def _gen_buffer(self, data: bytes, size: int, fmt: int, rate: int) -> al.Buffer:
        buffer = self.context.buffer_from_pcm(data[:size], format=fmt, sample_rate=rate)
        self.buffers.add(buffer)
        return buffer

    def _delete_buffer(self, buffer: al.Buffer) -> None:
        buffer.close()
        self.buffers.discard(buffer)

    def upload_sfx(self, s: sound_local.sfx_t, info: sound_local.wavinfo_t, data: Any, volume: int,
                   begin_length: int, end_length: int,
                   attack_length: int, fade_length: int) -> sound_local.sfxcache_t | None:
        """Uploads a sound to an OpenAL buffer and gives it a placeholder cache.

        The cache holds no samples, only the Sound object and the lengths
        (in milliseconds) the sound system needs.
        """
        size = info.samples * info.width
        if not size:
            return None

        try:
            sound = self.audio.sound_from_pcm(bytes(data[:size]),
                                              format=al_format(info.width, info.channels),
                                              sample_rate=info.rate)
        except al.ALLError:
            return None

        sc = s.cache = sound_local.sfxcache_t()
        sc.length = (info.samples * 1000) // info.rate
        sc.loopstart = info.loopstart
        sc.width = info.width
        sc.size = size
        sc.sound = sound
        self.sounds.add(sound)
        sc.stereo = info.channels - 1
        sc.volume = int(volume)
        sc.begin = int(begin_length * 1000 / info.rate)
        sc.end = int(end_length * 1000 / info.rate)
        sc.fade = int(fade_length * 1000 / info.rate)
        sc.attack = int(attack_length * 1000 / info.rate)
        return sc

    def delete_sfx(self, s: sound_local.sfx_t) -> None:
        """Deletes a sound's buffer (the sound system frees the cache)."""
        if s.cache and s.cache.sound is not None:
            s.cache.sound.close()
            self.sounds.discard(s.cache.sound)

    # -- reverb -----------------------------------------------------------

    def set_reverb(self, preset: int) -> None:
        """Sets the reverb effect to a preset, unless it's set already."""
        if preset == self.last_reverb or not 0 <= preset < len(REVERB_PRESETS):
            return
        if self.reverb_effect is None or self.reverb_slot is None:
            return  # no EFX
        reverb = REVERB_PRESETS[preset][1]
        self.last_reverb = preset

        effect = self.reverb_effect
        for param, value in (
            ('density', reverb.flDensity),
            ('diffusion', reverb.flDiffusion),
            ('gain', reverb.flGain),
            ('gain_hf', reverb.flGainHF),
            ('decay_time', reverb.flDecayTime),
            ('decay_hf_ratio', reverb.flDecayHFRatio),
            ('reflections_gain', reverb.flReflectionsGain),
            ('reflections_delay', reverb.flReflectionsDelay),
            ('late_reverb_gain', reverb.flLateReverbGain),
            ('late_reverb_delay', reverb.flLateReverbDelay),
            ('air_absorption_gain_hf', reverb.flAirAbsorptionGainHF),
            ('room_rolloff_factor', reverb.flRoomRolloffFactor),
        ):
            effect.parameters[param] = value
        effect.parameters["decay_hf_limit"] = reverb.iDecayHFLimit
        self.reverb_slot.refresh()

    def apply_reverb(self) -> None:
        """Picks a reverb preset by the size of the space around the listener."""
        if self.reverb_effect is None:
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

    def _set_direct_filter(self, flt: al.Filter | None) -> None:
        for voice in self.audio.voices:
            voice.source.direct_filter = flt

    def underwater(self) -> None:
        """The listener went under water: muffle every source."""
        if not self.underwater_enabled or self.underwater_filter is None:
            return
        self._set_direct_filter(self.underwater_filter)
        self.set_reverb(UNDERWATER_REVERB)

    def overwater(self) -> None:
        """The listener came out of the water."""
        if not self.underwater_enabled or self.underwater_filter is None:
            return
        self._set_direct_filter(None)
        self.set_reverb(int(sound_c.s_reverb_preset.value))

    def _update_underwater_cvars(self) -> None:
        if self.underwater_filter is None:
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
        self.underwater_filter.parameters["gain_hf"] = gain_hf

        under = self.underwater_enabled and sound_c.snd_is_underwater
        self._set_direct_filter(self.underwater_filter if under else None)

    # -- channels ---------------------------------------------------------

    def _spatialize(self, ch: sound_local.channel_t) -> None:
        """Moves a channel's source to where its sound comes from."""
        if _from_listener(ch):
            return  # relative, at the listener (see start_channel())
        assert ch.voice is not None
        source = ch.voice.source

        origin = np.zeros((3,), dtype=np.float32)
        if ch.fixed_origin:
            shared.VectorCopy(ch.origin, origin)
            ch.voice.position = al_vector(origin)
            return

        sound_c.GetEntitySoundOrigin(ch.entnum, sound_c.listener_origin, origin)
        ch.voice.position = al_vector(origin)

        if sound_c.s_doppler.value:
            velocity = np.zeros((3,), dtype=np.float32)
            cl_entities.CL_GetEntitySoundVelocity(ch.entnum, velocity)
            shared_c.VectorScale(velocity, METERS_PER_UNIT, velocity)
            source.velocity = al_vector(velocity)

        occluded = False
        strength = sound_c.s_occlusion_strength.value
        if not sound_c.snd_is_underwater and strength and self.occlusion_filter is not None:
            trace = collision.CM_BoxTrace(origin, sound_c.listener_origin, _ZERO, _ZERO,
                                          0, shared.MASK_PLAYERSOLID)
            if trace.fraction < 1.0:
                distance = np.zeros((3,), dtype=np.float32)
                shared.VectorSubtract(origin, sound_c.listener_origin, distance)
                dist = shared_c.VectorLength(distance)

                gain = 1.0 - ((dist / 1000) * (1.0 - strength))
                ch.voice.gain = min(max(gain, 0), 1)

                # high frequencies fade with distance, but keep enough for
                # HRTF's spatial cues
                gain_hf = 1.0 - (0.5 * strength * min(dist / 1000.0, 1.0))
                gain_hf = min(max(gain_hf, qal_h.AL_LOWPASS_MIN_GAINHF),
                              qal_h.AL_LOWPASS_MAX_GAINHF)
                self.occlusion_filter.parameters["gain_hf"] = float(gain_hf)
                source.direct_filter = self.occlusion_filter
                occluded = True

        reverb = False
        if not occluded:
            if not sound_c.snd_is_underwater and self.occlusion_filter is not None:
                source.direct_filter = None
            if sound_c.s_reverb_preset.value != -1 and self.reverb_slot is not None:
                source.set_send(0, self.reverb_slot)
                reverb = True
        if not reverb and self.reverb_slot is not None:
            source.set_send(0, None)

    def _configure_channel(self, ch: sound_local.channel_t, voice: al.Voice) -> None:
        ch.voice = voice
        source = voice.source
        source.reference_distance = sound_local.SOUND_FULLVOLUME
        source.max_distance = 8192
        source.rolloff_factor = ch.dist_mult * (8192 - sound_local.SOUND_FULLVOLUME)
        if (self.underwater_enabled and sound_c.snd_is_underwater
                and self.underwater_filter is not None):
            source.direct_filter = self.underwater_filter
        self._spatialize(ch)

    def _play(self, ch: sound_local.channel_t) -> None:
        if sound_c.s_show.value > 1:
            clientserver.Com_Printf(f"AL_PlayChannel: {ch.sfx.name}\n")
        self.audio.configure_voice = lambda voice: self._configure_channel(ch, voice)
        try:
            ch.voice = self.audio.play(ch.sfx.cache.sound, gain=min(ch.oal_vol, 1.0),
                                       looping=bool(ch.autosound), relative=_from_listener(ch))
        except (al.ALLError, al.ResourceInUseError):
            self.stop_channel(ch)  # don't keep a broken channel
        finally:
            self.audio.configure_voice = None

    def start_channel(self, ch: sound_local.channel_t, volume: float, master: float) -> None:
        ch.oal_vol = volume * master  # clamped to 1.0 in _play()
        self._play(ch)

    def stop_channel(self, ch: sound_local.channel_t) -> None:
        if sound_c.s_show.value > 1:
            clientserver.Com_Printf("{}: {}\n".format("AL_StopChannel", ch.sfx.name))
        if ch.voice is not None:
            ch.voice.stop()
        ch.clear()

    def _active_channels(self) -> Iterator[sound_local.channel_t]:
        return (ch for ch in sound_c.channels[:sound_c.s_numchannels] if ch.sfx)

    def stop_all_channels(self) -> None:
        for ch in list(self._active_channels()):
            self.stop_channel(ch)
        sound_c.s_rawend = 0
        self._stream_die()

    def playsound_start(self, timeofs: float, volume: float, painted: int) -> tuple[int, float]:
        return int(painted + timeofs * 1000), volume  # OpenAL counts in milliseconds

    def _find_looping_sound(
        self, entnum: int, sfx: sound_local.sfx_t,
    ) -> sound_local.channel_t | None:
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
        for buffer in self.stream_source.unqueue_buffers(count):
            self._delete_buffer(buffer)

    def _stream_die(self) -> None:
        """Stops the stream and drops its buffers."""
        if self.context.closed:  # OpenAL might not be initialised yet
            return
        self.stream_playing = False
        self.stream_source.stop()
        self._unqueue(self.stream_source.buffers_queued)
        self.stream_queued = 0

    def _stream_update(self) -> None:
        """Drops played stream buffers and restarts the stream if it stopped."""
        src = self.stream_source
        if src.state == al.SourceState.STOPPED:
            self.stream_playing = False
            # A source that ran dry (a cinematic paused by the menu or
            # console) stops with its played buffers still queued, and
            # playing it again would loop the last chunk. Drop them, but
            # keep the ones queued since the last update: a stopped source
            # counts every buffer as processed.
            self._unqueue(max(src.buffers_queued
                              - self.stream_queued, 0))
        else:
            self._unqueue(src.buffers_processed)

        if not self.stream_playing and src.buffers_queued:
            src.play()
            self.stream_playing = True
        self.stream_queued = 0

    def raw_samples(self, samples: int, rate: int, width: int, channels: int,
                    data: Any, volume: float) -> None:
        """Queues raw samples (music or a cinematic's sound) on the stream."""
        size = samples * width * channels
        buffer = self._gen_buffer(bytes(data), size, al_format(width, channels), rate)
        self.stream_source.gain = min(volume, 1.0)
        self.stream_source.queue_buffers([buffer])
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
        if not self._recover_lost_device():
            return

        # the listener
        listener = self.context.listener
        listener.position = al_vector(sound_c.listener_origin)
        listener.orientation = (al_vector(sound_c.listener_forward),
                                al_vector(sound_c.listener_up))

        if sound_c.s_reverb_preset.value == -2:
            self.apply_reverb()
        elif sound_c.s_reverb_preset.value >= 0:
            self.set_reverb(int(sound_c.s_reverb_preset.value))

        if sound_c.s_doppler.value:
            velocity = np.zeros((3,), dtype=np.float32)
            cl_entities.CL_GetViewVelocity(velocity)
            shared_c.VectorScale(velocity, METERS_PER_UNIT, velocity)
            listener.velocity = al_vector(velocity)

        self.audio.update()
        # the channels: drop the finished ones and move the others
        for ch in list(self._active_channels()):
            if ch.autosound:
                if ch.autoframe != self.frame_count:
                    self.stop_channel(ch)  # looping sounds are added again each frame
                    continue
            else:
                if ch.voice is None or ch.voice.closed:
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
        self._sound_info(True)

    def _sound_info(self, show_extensions: bool) -> None:
        output = clientserver.Com_Printf if show_extensions else clientserver.Com_DPrintf
        extensions = " ".join(sorted(self.context.extensions))
        clientserver.Com_Printf("OpenAL features:\n")
        for name, value in (("AL_VENDOR", self.context.vendor),
                            ("AL_RENDERER", self.context.renderer),
                            ("AL_VERSION", self.context.version)):
            clientserver.Com_Printf(f"{name}: {value}\n")
        output(f"AL_EXTENSIONS: {extensions}\n")
        clientserver.Com_Printf(f"AL_EXTENSIONS number: {len(self.context.extensions)}\n")
        if self.device.supports("ALC_ENUMERATE_ALL_EXT"):
            clientserver.Com_Printf("\nAvailable OpenAL devices:\n")
            for name in al.enumerate_devices():
                clientserver.Com_Printf(f"- {name}\n")
            clientserver.Com_Printf(f"\nCurrent OpenAL device:\n- {self.device.spec}\n")

    def _recover_lost_device(self) -> bool:
        if not self.has_disconnect:
            return True
        if not self.disconnect_frames:
            if self.device.get_parameter("ALC_CONNECTED"):
                return True
            self.disconnect_frames = 1
        elif self.disconnect_frames < int(cvar.Cvar_VariableValue("cl_maxfps") * 2.5):
            self.disconnect_frames += 1
        else:
            cmdparser.Cbuf_AddText("snd_restart\n")
            self.disconnect_frames = 0
        return False
