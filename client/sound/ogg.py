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
from __future__ import annotations

from client.sound.header import vorbis

# Q2PORT: ogg.c is ported in group 13. Until then the client's calls into it
# do nothing and the music is stopped.

def OGG_Status()->int: #void (returns int)

	return vorbis.STOP

def OGG_InitTrackList(): #void

	pass

def OGG_Init(): #void

	pass

def OGG_PlayTrack(track: str, cdtrack: bool, immediate: bool): #const char *, qboolean, qboolean

	pass

def OGG_RecoverState(): #void

	pass

def OGG_SaveState(): #void

	pass

def OGG_Shutdown(): #void

	pass

def OGG_Stop(): #void

	pass

def OGG_Stream(): #void

	pass
