"""
Q2PORT: the parts of stb_vorbis (header/stb_vorbis.h, a public domain Ogg Vorbis
decoder by Sean Barrett) that client/sound/ogg.c calls, done with pyglet's media
decoders (FFmpeg) instead of a port of the decoder.

	stb_vorbis_open_file, stb_vorbis_open_memory, stb_vorbis_close,
	stb_vorbis_get_samples_short_interleaved, stb_vorbis_get_sample_offset,
	stb_vorbis_seek_frame, stb_vorbis_stream_length_in_samples

As in stb_vorbis, a "sample" is one sample per channel (a frame), and the
samples come out as signed 16 bit, interleaved.
"""
from __future__ import annotations

import io

import numpy as np
import pyglet

# pyglet only decodes here; the game plays through its own OpenAL context.
# pyglet's OpenAL audio driver (created on the first pyglet.media.load) would
# make another OpenAL context current, and the game's sources and buffers
# would no longer exist for its OpenAL calls. The silent driver makes none.
pyglet.options['audio'] = ('silent',)

import pyglet.media  # noqa: E402

#define STB_VORBIS_NO_PUSHDATA_API

VORBIS__no_error = 0
VORBIS_file_open_failure = 6 # fopen() failed
VORBIS_invalid_stream = 34

class stb_vorbis(object):

	def __init__(self, source):

		self.source = source # pyglet.media streaming source
		audio_format = source.audio_format
		self.sample_rate = audio_format.sample_rate #unsigned int
		self.channels = audio_format.channels #int
		self.sample_size = audio_format.sample_size # bits per sample of the decoder's output
		self.pending = np.zeros((0,), dtype=np.int16) # decoded, not yet returned
		self.current_loc = 0 # sample (frame) offset of the next returned sample

	def decode(self, data: bytes)->np.ndarray:

		# the decoder's samples as shorts, clamped as stb_vorbis converts its floats
		if self.sample_size == 32:
			f = np.frombuffer(data, dtype=np.float32)
			return np.clip(np.rint(f * 32768.0), -32768, 32767).astype(np.int16)
		elif self.sample_size == 16:
			return np.frombuffer(data, dtype=np.int16)
		else: # 8 bit unsigned
			return ((np.frombuffer(data, dtype=np.uint8).astype(np.int16) - 128) << 8).astype(np.int16)

def _open(name: str, f, error)->stb_vorbis:

	try:
		source = pyglet.media.load(name, file=f, streaming=True)
	except Exception: # pyglet raises its own decode exceptions for a bad stream
		error[0] = VORBIS_invalid_stream
		return None

	if source.audio_format is None:
		source.delete()
		error[0] = VORBIS_invalid_stream
		return None

	error[0] = VORBIS__no_error
	return stb_vorbis(source)

def stb_vorbis_open_file(f, close_handle_on_close: bool, error: list, alloc_buffer)->stb_vorbis: #FILE *, int, int *, const stb_vorbis_alloc * (returns stb_vorbis *)

	# error is a one element list (int *error)
	v = _open(f.name, f, error)
	if v is None and close_handle_on_close:
		f.close()
	return v

def stb_vorbis_open_memory(data: bytes, len_: int, error: list, alloc_buffer)->stb_vorbis: #const unsigned char *, int, int *, const stb_vorbis_alloc * (returns stb_vorbis *)

	return _open("memory.ogg", io.BytesIO(bytes(data[:len_])), error)

def stb_vorbis_close(f: stb_vorbis): #stb_vorbis *

	if f is None:
		return
	f.source.delete()
	f.source = None

def stb_vorbis_get_samples_short_interleaved(f: stb_vorbis, channels: int, buffer: np.ndarray, num_shorts: int)->int: #stb_vorbis *, int, short *, int (returns int)

	# fills buffer (a numpy int16 array) and returns the number of samples per channel
	want = (num_shorts // channels) * channels
	bytes_per_short = f.sample_size // 8

	empty = 0 # pyglet can hand out empty chunks before the decoder has output; None is the end
	while len(f.pending) < want and empty < 16:

		audio_data = f.source.get_audio_data((want - len(f.pending)) * bytes_per_short)
		if audio_data is None:
			break
		if audio_data.length == 0:
			empty += 1
			continue
		empty = 0
		f.pending = np.concatenate((f.pending, f.decode(audio_data.data[:audio_data.length])))

	n = min(want, len(f.pending))
	n -= n % f.channels
	buffer[:n] = f.pending[:n]
	f.pending = f.pending[n:]

	samples = n // f.channels
	f.current_loc += samples
	return samples

def stb_vorbis_get_sample_offset(f: stb_vorbis)->int: #stb_vorbis * (returns int)

	return f.current_loc

def stb_vorbis_seek_frame(f: stb_vorbis, sample_number: int)->int: #stb_vorbis *, unsigned int (returns int)

	f.source.seek(sample_number / f.sample_rate)
	f.pending = np.zeros((0,), dtype=np.int16)
	f.current_loc = sample_number
	return 1

def stb_vorbis_stream_length_in_samples(f: stb_vorbis)->int: #stb_vorbis * (returns unsigned int)

	if not f.source.duration:
		return 0
	return int(round(f.source.duration * f.sample_rate))
