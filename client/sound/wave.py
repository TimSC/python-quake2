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
 * This file implements a subset of the WAVE audio file format.
 *
 * =======================================================================
"""
from __future__ import annotations

from common import clientserver
from common.header import shared
from client.sound.header import local as sound_local

#include "../header/client.h"
#include "header/local.h"

# Q2PORT: the pointers are indices into iff_buf, None for NULL
data_p = None #static byte *
iff_end = None #static byte *
last_chunk = None #static byte *
iff_data = None #static byte *
iff_chunk_len = 0 #static int
iff_buf = None # the wav buffer the pointers above index into

class _Truncated(Exception): # Q2PORT: a read past the end of the file, see GetWavinfo()
	pass

def GetLittleShort()->int: #void (returns static short)

	global data_p

	if data_p + 2 > iff_end: # Q2PORT: the C reads past the buffer
		raise _Truncated()

	val = 0 #short

	val = iff_buf[data_p]
	val = val + (iff_buf[data_p + 1] << 8)
	data_p += 2
	if val >= 0x8000: # short
		val -= 0x10000
	return val

def GetLittleLong()->int: #void (returns static int)

	global data_p

	if data_p + 4 > iff_end: # Q2PORT: the C reads past the buffer
		raise _Truncated()

	val = 0 #int

	val = iff_buf[data_p]
	val = val + (iff_buf[data_p + 1] << 8)
	val = val + (iff_buf[data_p + 2] << 16)
	val = val + (iff_buf[data_p + 3] << 24)
	data_p += 4
	if val >= 0x80000000: # int
		val -= 0x100000000
	return val

def FindNextChunk(name: bytes): #char * (static)

	global data_p, iff_chunk_len, last_chunk

	while True:

		data_p = last_chunk
		data_p += 4

		if data_p >= iff_end:

			data_p = None
			return

		iff_chunk_len = GetLittleLong()

		if iff_chunk_len < 0:

			data_p = None
			return

		data_p -= 8
		last_chunk = data_p + 8 + ((iff_chunk_len + 1) & ~1)

		if iff_buf[data_p:data_p + 4] == name: # !strncmp((const char *)data_p, name, 4)

			return

def FindChunk(name: bytes): #char * (static)

	global last_chunk

	last_chunk = iff_data
	FindNextChunk(name)

def GetWavinfo(name: str, wav: bytes, wavlength: int)->sound_local.wavinfo_t: #char *, byte *, int (returns wavinfo_t)

	# Q2PORT: a file that ends inside a header field is damaged (the C reads
	# past the buffer): it gives an empty info, which S_LoadSound() refuses
	try:
		return _GetWavinfo(name, wav, wavlength)
	except _Truncated:
		clientserver.Com_Printf("{}: {} is truncated\n".format("GetWavinfo", name))
		return sound_local.wavinfo_t()

def _GetWavinfo(name: str, wav: bytes, wavlength: int)->sound_local.wavinfo_t: #char *, byte *, int (returns wavinfo_t)

	global data_p, iff_data, iff_end, iff_buf

	#wavinfo_t info;
	#int format;
	#int samples;

	info = sound_local.wavinfo_t() # memset(&info, 0, sizeof(info));

	if wav is None:

		return info

	iff_buf = wav
	iff_data = 0 # wav
	iff_end = wavlength # wav + wavlength

	# find "RIFF" chunk
	FindChunk(b"RIFF")

	if not (data_p is not None and iff_buf[data_p + 8:data_p + 12] == b"WAVE"):

		clientserver.Com_Printf("Missing RIFF/WAVE chunks\n")
		return info

	# get "fmt " chunk
	iff_data = data_p + 12

	FindChunk(b"fmt ")

	if data_p is None:

		clientserver.Com_Printf("Missing fmt chunk\n")
		return info

	data_p += 8
	format = GetLittleShort()

	if format != 1:

		clientserver.Com_Printf("Microsoft PCM format only\n")
		return info

	info.channels = GetLittleShort()
	info.rate = GetLittleLong()
	data_p += 4 + 2
	info.width = int(GetLittleShort() / 8)

	# wBitPerSample assumes it's not an uncommon value such as < 8 bits
	if info.width <= 0:

		clientserver.Com_Printf("Invalid bits per sample")
		return info

	# get cue chunk
	FindChunk(b"cue ")

	if data_p is not None:

		data_p += 32
		info.loopstart = GetLittleLong()

		# if the next chunk is a LIST chunk,
		# look for a cue length marker
		FindNextChunk(b"LIST")

		if data_p is not None:

			if ((data_p + 32 <= wavlength) and # (data_p - wav) + 32 <= wavlength
				iff_buf[data_p + 28:data_p + 32] == b"mark"):

				#int i;

				# this is not a proper parse,
				# but it works with cooledit...
				data_p += 24
				i = GetLittleLong() # samples in loop
				info.samples = info.loopstart + i

	else:

		info.loopstart = -1

	# find data chunk
	FindChunk(b"data")

	if data_p is None:

		clientserver.Com_Printf("Missing data chunk\n")
		return info

	data_p += 4
	samples = int(GetLittleLong() / info.width)

	if info.samples:

		if samples < info.samples:

			clientserver.Com_Error(shared.ERR_DROP, "{}: Sound {} has a bad loop length".format(
				"GetWavinfo", name))

	else:

		info.samples = samples

	info.dataofs = data_p # (int)(data_p - wav)

	return info
