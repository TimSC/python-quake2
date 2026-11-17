"""
Q2PORT: the parts of stb_vorbis (header/stb_vorbis.h, a public domain Ogg Vorbis
decoder by Sean Barrett) that client/sound/ogg.c calls, done with SoundFile
(libsndfile) instead of a port of the decoder.

	stb_vorbis_open_file, stb_vorbis_open_memory, stb_vorbis_close,
	stb_vorbis_get_samples_short_interleaved, stb_vorbis_get_sample_offset,
	stb_vorbis_seek_frame, stb_vorbis_stream_length_in_samples

As in stb_vorbis, a "sample" is one sample per channel (a frame), and the
samples come out as signed 16 bit, interleaved.
"""
from __future__ import annotations

import io

import numpy as np
import soundfile

#define STB_VORBIS_NO_PUSHDATA_API

VORBIS__no_error = 0
VORBIS_file_open_failure = 6 # fopen() failed
VORBIS_invalid_stream = 34

class stb_vorbis(object):

	def __init__(self, source, handle, close_handle_on_close: bool):

		self.source = source # soundfile.SoundFile streaming decoder
		self.handle = handle # underlying file or BytesIO
		self.close_handle_on_close = close_handle_on_close #int
		self.sample_rate = source.samplerate #unsigned int
		self.channels = source.channels #int

def _open(f, close_handle_on_close: bool, error: list)->stb_vorbis:

	try:
		source = soundfile.SoundFile(f, mode='r')
	except (soundfile.SoundFileError, OSError):
		if close_handle_on_close:
			f.close()
		error[0] = VORBIS_invalid_stream
		return None

	if source.format != 'OGG' or source.subtype != 'VORBIS':
		source.close()
		if close_handle_on_close:
			f.close()
		error[0] = VORBIS_invalid_stream
		return None

	error[0] = VORBIS__no_error
	return stb_vorbis(source, f, close_handle_on_close)

def stb_vorbis_open_file(f, close_handle_on_close: bool, error: list, alloc_buffer)->stb_vorbis: #FILE *, int, int *, const stb_vorbis_alloc * (returns stb_vorbis *)

	# error is a one element list (int *error)
	return _open(f, close_handle_on_close, error)

def stb_vorbis_open_memory(data: bytes, len_: int, error: list, alloc_buffer)->stb_vorbis: #const unsigned char *, int, int *, const stb_vorbis_alloc * (returns stb_vorbis *)

	return _open(io.BytesIO(bytes(data[:len_])), True, error)

def stb_vorbis_close(f: stb_vorbis): #stb_vorbis *

	if f is None:
		return
	f.source.close()
	if f.close_handle_on_close:
		f.handle.close()
	f.source = None

def stb_vorbis_get_samples_short_interleaved(f: stb_vorbis, channels: int, buffer: np.ndarray, num_shorts: int)->int: #stb_vorbis *, int, short *, int (returns int)

	# fills buffer (a numpy int16 array) and returns the number of samples per channel
	# All engine callers request the stream's channel count, as in ogg.c.
	assert channels == f.channels
	want = min(num_shorts, len(buffer)) // channels
	data = f.source.read(want, dtype='int16', always_2d=True)
	buffer[:data.size] = data.reshape(-1)
	return len(data)

def stb_vorbis_get_sample_offset(f: stb_vorbis)->int: #stb_vorbis * (returns int)

	return f.source.tell()

def stb_vorbis_seek_frame(f: stb_vorbis, sample_number: int)->int: #stb_vorbis *, unsigned int (returns int)

	if sample_number < 0 or sample_number > len(f.source):
		return 0
	try:
		f.source.seek(sample_number)
	except (soundfile.SoundFileError, OSError):
		return 0
	return 1

def stb_vorbis_stream_length_in_samples(f: stb_vorbis)->int: #stb_vorbis * (returns unsigned int)

	return len(f.source)
