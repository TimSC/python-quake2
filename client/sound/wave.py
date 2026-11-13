"""
 * Copyright (C) 1997-2001 Id Software, Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * WAV headers for the sound system, read with q2data.wav.
 *
 * =======================================================================
"""

from client.sound.header import local as sound_local
from common import clientserver
from common.header import shared
from q2data import FormatError
from q2data import wav


def GetWavinfo(name: str, data: bytes, length: int) -> sound_local.wavinfo_t:  # noqa: N802
    """The format and sample range of a WAV file.

    A file that can't be read prints why and gives an empty info (0
    channels), which the sound loader refuses. A loop longer than the sound
    drops to the console, as in Quake II.
    """
    info = sound_local.wavinfo_t()
    if data is None:
        return info
    try:
        parsed = wav.read_wav_info(bytes(data[:length]))
    except FormatError as err:
        message = str(err)
        if message == "has a bad loop length":
            clientserver.Com_Error(shared.ERR_DROP,
                                   f"GetWavinfo: Sound {name} has a bad loop length")
        clientserver.Com_Printf(message if message == "Invalid bits per sample"
                                else message + "\n")
        return info

    info.rate = parsed.rate
    info.width = parsed.width
    info.channels = parsed.channels
    info.loopstart = parsed.loop_start
    info.samples = parsed.samples
    info.dataofs = parsed.data_offset
    return info
