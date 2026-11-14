"""The sound backend interface.

The sound system (``sound.py``) mixes nothing itself; a backend uploads the
sounds, plays the channels, streams raw samples (cinematics, music) and
updates the listener every frame. The one backend is OpenAL
(``openal.OpenALBackend``). Yamagi also has an SDL backend with a software
mixer; it isn't ported, so without OpenAL there is no sound.
"""

from __future__ import annotations

from typing import Any, Protocol


class SoundBackend(Protocol):
    """A sound backend's entry points."""

    name: str
    active_buffers: int  # buffers in use: sounds and queued raw samples

    @property
    def num_channels(self) -> int: ...

    def upload_sfx(self, sfx: Any, info: Any, data: Any, volume: int, begin: int, end: int,
                   attack: int, fade: int) -> Any:
        """Uploads a sound; returns its sfxcache_t, or None."""

    def delete_sfx(self, sfx: Any) -> None: ...

    def start_channel(self, channel: Any, volume: float, master: float) -> None: ...

    def stop_channel(self, channel: Any) -> None: ...

    def stop_all_channels(self) -> None: ...

    def playsound_start(self, timeofs: float, volume: float, painted: int) -> tuple[int, float]:
        """When a playsound starts and at what volume: (begin, volume)."""

    def raw_samples(self, samples: int, rate: int, width: int, channels: int, data: Any,
                    volume: float) -> None: ...

    def unqueue_raw_samples(self) -> None: ...

    def underwater(self) -> None: ...

    def overwater(self) -> None: ...

    def update(self) -> None: ...

    def sound_info(self) -> None: ...

    def shutdown(self) -> None: ...
