"""The sound backend interface, and the one backend there is: OpenAL.

The sound system (``sound.py``) mixes nothing itself; a backend uploads the
sounds, plays the channels, streams raw samples (cinematics, music) and
updates the listener every frame. Yamagi also has an SDL backend with a
software mixer; it isn't ported, so without OpenAL there is no sound.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SoundBackend:
    """A sound backend's entry points."""

    name: str
    # (sfx, wavinfo, samples, volume, begin, end, attack, fade) -> sfxcache_t
    upload_sfx: Callable[..., Any]
    delete_sfx: Callable[[Any], None]
    start_channel: Callable[[Any, float, float], None]  # (channel, volume, master volume)
    stop_channel: Callable[[Any], None]
    stop_all_channels: Callable[[], None]
    # When a playsound starts and at what volume: (timeofs, volume, paintedtime)
    # -> (begin, volume)
    playsound_start: Callable[[float, float, int], tuple[int, float]]
    raw_samples: Callable[[int, int, int, int, Any, float], None]
    unqueue_raw_samples: Callable[[], None]
    update: Callable[[], None]
    sound_info: Callable[[], None]
    shutdown: Callable[[], None]


def openal_backend() -> SoundBackend:
    """The OpenAL backend (client/sound/openal.py)."""
    from client.sound import openal, qal

    def start_channel(channel: Any, volume: float, master: float) -> None:
        channel.oal_vol = volume * master  # clamped to 1.0 in AL_PlayChannel()
        openal.AL_PlayChannel(channel)

    def playsound_start(timeofs: float, volume: float, painted: int) -> tuple[int, float]:
        return int(painted + timeofs * 1000), volume  # OpenAL counts in milliseconds

    return SoundBackend(
        name="openal",
        upload_sfx=openal.AL_UploadSfx,
        delete_sfx=openal.AL_DeleteSfx,
        start_channel=start_channel,
        stop_channel=openal.AL_StopChannel,
        stop_all_channels=openal.AL_StopAllChannels,
        playsound_start=playsound_start,
        raw_samples=openal.AL_RawSamples,
        unqueue_raw_samples=openal.AL_UnqueueRawSamples,
        update=openal.AL_Update,
        sound_info=lambda: qal.QAL_SoundInfo(True),
        shutdown=openal.AL_Shutdown,
    )
