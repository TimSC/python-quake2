"""Exercise the SoundFile adapter without game data or an audio device."""
from __future__ import annotations

import io
import os
import sys
import unittest

import numpy as np
import soundfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.sound.header import stb_vorbis


class VorbisTests(unittest.TestCase):

	def setUp(self):
		self.rate = 22050
		t = np.arange(4097) / self.rate
		self.data = np.column_stack((0.5 * np.sin(2 * np.pi * 440 * t),
			0.25 * np.sin(2 * np.pi * 880 * t)))
		encoded = io.BytesIO()
		soundfile.write(encoded, self.data, self.rate, format='OGG', subtype='VORBIS')
		self.encoded = encoded.getvalue()
		self.expected, _ = soundfile.read(io.BytesIO(self.encoded), dtype='int16', always_2d=True)

	def test_stream_seek_and_eof(self):
		error = [-1]
		decoder = stb_vorbis.stb_vorbis_open_memory(self.encoded, len(self.encoded), error, None)
		self.assertEqual(error[0], 0)
		self.assertEqual((decoder.sample_rate, decoder.channels), (self.rate, 2))
		self.assertEqual(stb_vorbis.stb_vorbis_stream_length_in_samples(decoder), len(self.data))
		try:
			chunks = []
			buffer = np.full(257, -12345, dtype=np.int16)
			while True:
				frames = stb_vorbis.stb_vorbis_get_samples_short_interleaved(decoder, 2, buffer, len(buffer))
				self.assertEqual(buffer[-1], -12345) # incomplete frames stay untouched
				if frames == 0:
					break
				chunks.append(buffer[:frames * 2].copy())
			np.testing.assert_array_equal(np.concatenate(chunks), self.expected.reshape(-1))
			self.assertEqual(stb_vorbis.stb_vorbis_get_sample_offset(decoder), len(self.data))
			self.assertEqual(stb_vorbis.stb_vorbis_seek_frame(decoder, 123), 1)
			self.assertEqual(stb_vorbis.stb_vorbis_get_sample_offset(decoder), 123)
			frames = stb_vorbis.stb_vorbis_get_samples_short_interleaved(decoder, 2, buffer, 256)
			np.testing.assert_array_equal(buffer[:frames * 2], self.expected[123:123 + frames].reshape(-1))
			self.assertEqual(stb_vorbis.stb_vorbis_seek_frame(decoder, -1), 0)
		finally:
			stb_vorbis.stb_vorbis_close(decoder)
		self.assertTrue(decoder.handle.closed)

	def test_handle_ownership_and_invalid_input(self):
		for owned in (False, True):
			for data in (self.encoded, b'not an ogg file'):
				handle = io.BytesIO(data)
				error = [-1]
				decoder = stb_vorbis.stb_vorbis_open_file(handle, owned, error, None)
				if data == self.encoded:
					self.assertEqual(error[0], 0)
					stb_vorbis.stb_vorbis_close(decoder)
				else:
					self.assertIsNone(decoder)
					self.assertEqual(error[0], stb_vorbis.VORBIS_invalid_stream)
				self.assertEqual(handle.closed, owned)
				handle.close()

	def test_mono_and_non_vorbis(self):
		for format_, subtype in (('OGG', 'VORBIS'), ('WAV', 'PCM_16')):
			handle = io.BytesIO()
			soundfile.write(handle, self.data[:, 0], self.rate, format=format_, subtype=subtype)
			handle.seek(0)
			error = [-1]
			decoder = stb_vorbis.stb_vorbis_open_file(handle, True, error, None)
			if format_ == 'OGG':
				self.assertEqual(decoder.channels, 1)
				buffer = np.zeros(100, dtype=np.int16)
				self.assertEqual(stb_vorbis.stb_vorbis_get_samples_short_interleaved(decoder, 1, buffer, 100), 100)
				stb_vorbis.stb_vorbis_close(decoder)
			else:
				self.assertIsNone(decoder)
				self.assertEqual(error[0], stb_vorbis.VORBIS_invalid_stream)
			self.assertTrue(handle.closed)


if __name__ == '__main__':
	unittest.main()
