"""
Copyright (C) 2010, 2013 Yamagi Burmeister
Copyright (C) 2005 Ryan C. Gordon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

This file implements an interface to libvorbis for decoding
OGG/Vorbis files. Strongly spoken this file isn't part of the sound
system but part of the main client. It justs converts Vorbis streams
into normal, raw Wave stream which are injected into the backends as
if they were normal "raw" samples. At this moment only background
music playback and in theory .cin movie file playback is supported.

=======================================================================
"""

from client.sound import music

# The music player (client/sound/music.py). A process-wide one until the
# sound system is an object that holds it.
player = music.MusicPlayer()


def OGG_InitTrackList() -> None:  # noqa: N802
    player.init_track_list()


def OGG_Read() -> None:  # noqa: N802
    player.read()


def OGG_Stream() -> None:  # noqa: N802
    player.stream()


def OGG_PlayTrack(track: str, cdtrack: bool, immediate: bool) -> None:  # noqa: N802
    player.play_track(track, cdtrack, immediate)


def OGG_Stop() -> None:  # noqa: N802
    player.stop()


def OGG_TogglePlayback() -> None:  # noqa: N802
    player.toggle_playback()


def OGG_SaveState() -> None:  # noqa: N802
    player.save_state()


def OGG_RecoverState() -> None:  # noqa: N802
    player.recover_state()


def OGG_Status() -> int:  # noqa: N802
    return player.status


def OGG_Init() -> None:  # noqa: N802
    player.init()


def OGG_Shutdown() -> None:  # noqa: N802
    player.shutdown()


def OGG_LoadAsWav(filename: str):  # noqa: N802
    """Returns (wavinfo_t, samples), or (None, None)."""
    return music.load_as_wav(filename)
