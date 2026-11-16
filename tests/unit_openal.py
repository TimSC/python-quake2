"""OpenAL binding checks with generated PCM and no window or game data."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREAMBLE = """
import types
from unittest import mock
import openal_py
from client.sound import openal, qal
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
for name, value in {
    's_doppler': 1, 's_underwater': 1, 's_underwater_gain_hf': 0.25,
    's_reverb_preset': 0, 's_show': 0, 's_occlusion_strength': 0,
}.items():
    setattr(sound_c, name, types.SimpleNamespace(value=value, modified=True))
sound_c.s_numchannels = 0
sound_c.channels = [sound_local.channel_t() for _ in range(sound_local.MAX_CHANNELS)]
def sample():
    sfx = sound_local.sfx_t()
    sfx.name = 'generated'
    info = sound_local.wavinfo_t()
    info.samples, info.width, info.channels, info.rate = 100, 2, 1, 22050
    info.loopstart = -1
    assert openal.AL_UploadSfx(sfx, info, bytes(200), 255, 0, 0, 0, 0)
    return sfx
"""


class OpenALTests(unittest.TestCase):

	def run_case(self, code: str) -> None:
		result = subprocess.run(
			[sys.executable, '-c', PREAMBLE + textwrap.dedent(code)],
			cwd=ROOT, env={**os.environ, 'ALSOFT_DRIVERS': 'null'},
			capture_output=True, text=True, timeout=30,
		)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_restart_stream_and_effects(self) -> None:
		self.run_case('''
		for attempt in range(2):
		    assert openal.AL_Init()
		    assert isinstance(qal.audio, openal_py.AudioEngine)
		    device, context = qal.device, qal.context
		    assert sound_c.s_numchannels == 31
		    assert context.distance_model == openal_py.DistanceModel.LINEAR_CLAMPED
		    assert context.doppler_factor == 2.0
		    openal.AL_RawSamples(100, 22050, 2, 1, bytes(200), 0.5)
		    assert openal.active_buffers == 1
		    assert openal.streamSource.buffers_queued == 1
		    assert openal.streamSource.gain == 0.5
		    openal.AL_StreamUpdate()
		    openal.AL_UnqueueRawSamples()
		    assert openal.active_buffers == 0
		    openal.AL_SetReverb(3)
		    effect = openal.ReverbEffect[0]
		    assert abs(effect.parameters['decay_time'] - 1.49) < 0.001
		    openal.AL_Shutdown()
		    assert context.closed and device.closed
		    assert qal.audio is None and qal.device is None
		''')

	def test_channels_and_underwater(self) -> None:
		self.run_case('''
		assert openal.AL_Init()
		sfx = sample()
		assert isinstance(sfx.cache.bufnum, openal_py.Sound)
		assert sfx.cache.size == 200 and sfx.cache.length == 4
		ch = sound_c.channels[0]
		ch.sfx, ch.entnum, ch.oal_vol, ch.autosound = sfx, -1, 0.4, True
		openal.AL_PlayChannel(ch)
		assert isinstance(ch.srcnum, openal_py.Voice)
		voice, source = ch.srcnum, ch.srcnum.source
		assert voice.sound is sfx.cache.bufnum
		assert abs(voice.gain - 0.4) < 0.001
		assert source.relative and source.max_distance == 8192
		sound_c.sound_started = sound_local.SS_OAL
		openal.AL_UpdateUnderwater()
		openal.AL_Underwater()
		assert source.direct_filter is openal.underwaterFilter
		openal.AL_Overwater()
		assert source.direct_filter is None
		openal.AL_StopChannel(ch)
		assert voice.closed and ch.sfx is None
		sound_c.snd_is_underwater = True
		ch.sfx, ch.entnum, ch.oal_vol, ch.autosound = sfx, -1, 0.4, True
		openal.AL_PlayChannel(ch)
		assert ch.srcnum.source.direct_filter is openal.underwaterFilter
		openal.AL_StopChannel(ch)
		openal.AL_DeleteSfx(sfx)
		assert sfx.cache.bufnum.closed and openal.active_buffers == 0
		openal.AL_Shutdown()
		''')

	def test_stream_underrun(self) -> None:
		self.run_case('''
		assert openal.AL_Init()
		openal.AL_RawSamples(100, 22050, 2, 1, bytes(200), 1.0)
		openal.AL_StreamUpdate()
		openal.streamSource.stop()
		openal.AL_RawSamples(100, 22050, 2, 1, bytes(200), 1.0)
		openal.AL_StreamUpdate()
		assert openal.active_buffers == 1
		assert openal.streamSource.buffers_queued == 1
		openal.AL_Shutdown()
		''')

	def test_init_failures(self) -> None:
		self.run_case('''
		with mock.patch.object(openal_py.Device, 'open', side_effect=openal_py.ALCError(0xA005)):
		    assert not openal.AL_Init()
		assert qal.device is None
		device = openal_py.Device.open()
		with (
		    mock.patch.object(openal_py.Device, 'open', return_value=device),
		    mock.patch.object(openal_py.Device, 'create_context',
		                      side_effect=openal_py.ALCError(0xA005)),
		):
		    assert not openal.AL_Init()
		assert device.closed and qal.audio is None
		''')

	def test_without_efx(self) -> None:
		self.run_case('''
		original = openal_py.Device.supports
		def supports(device, extension):
		    return extension != 'ALC_EXT_EFX' and original(device, extension)
		with mock.patch.object(openal_py.Device, 'supports', supports):
		    assert openal.AL_Init()
		    sfx = sample()
		    ch = sound_c.channels[0]
		    ch.sfx, ch.entnum, ch.dist_mult, ch.oal_vol = sfx, 2, 0.001, 0.4
		    sound_c.s_doppler.value = 0
		    with mock.patch.object(sound_c, 'GetEntitySoundOrigin'):
		        openal.AL_PlayChannel(ch)
		    assert not ch.srcnum.closed
		    openal.AL_SetReverb(0)
		    openal.AL_Shutdown()
		''')

	def test_spatialization_and_occlusion(self) -> None:
		self.run_case('''
		assert openal.AL_Init()
		sfx = sample()
		ch = sound_c.channels[0]
		ch.sfx, ch.entnum, ch.dist_mult = sfx, 2, 0.001
		ch.oal_vol, ch.autosound = 1.0, True
		def origin(ent, listener, out):
		    out[:] = (100, 200, 300)
		def velocity(ent, out):
		    out[:] = (1, 2, 3)
		with (
		    mock.patch.object(sound_c, 'GetEntitySoundOrigin', side_effect=origin),
		    mock.patch.object(openal.cl_entities, 'CL_GetEntitySoundVelocity', side_effect=velocity),
		):
		    openal.AL_PlayChannel(ch)
		    source = ch.srcnum.source
		    assert source.position == (-200, 300, -100)
		    assert all(abs(a - b) < 0.0001 for a, b in
		               zip(source.velocity, (-0.063, 0.0945, -0.0315)))
		    assert source.get_send(0)[0] is openal.ReverbEffectSlot[0]
		    sound_c.s_occlusion_strength.value = 0.5
		    with mock.patch.object(openal.collision, 'CM_BoxTrace',
		                           return_value=types.SimpleNamespace(fraction=0.5)):
		        openal.AL_Spatialize(ch)
		    assert source.direct_filter is openal.occlusionFilter
		    assert source.get_send(0) is None
		openal.AL_StopChannel(ch)
		openal.AL_DeleteSfx(sfx)
		openal.AL_Shutdown()
		''')

	def test_activation_and_source_failures(self) -> None:
		self.run_case('''
		device = openal_py.Device.open()
		with (
		    mock.patch.object(openal_py.Device, 'open', return_value=device),
		    mock.patch.object(openal_py.Context, 'make_current',
		                      side_effect=openal_py.ALCError(0xA005)),
		):
		    assert not openal.AL_Init()
		assert device.closed and qal.audio is None
		device = openal_py.Device.open()
		with (
		    mock.patch.object(openal_py.Device, 'open', return_value=device),
		    mock.patch.object(openal_py.Context, 'create_source',
		                      side_effect=openal_py.ALLError(0xA005)),
		):
		    assert not openal.AL_Init()
		assert device.closed and qal.audio is None
		''')

	def test_device_recovery(self) -> None:
		self.run_case('''
		from common import cmdparser
		assert openal.AL_Init()
		with (
		    mock.patch.object(openal_py.Device, 'get_parameter', return_value=0),
		    mock.patch.object(qal.cvar, 'Cvar_VariableValue', return_value=1),
		    mock.patch.object(cmdparser, 'Cbuf_AddText') as commands,
		):
		    assert not qal.QAL_RecoverLostDevice()
		    assert not qal.QAL_RecoverLostDevice()
		    assert not qal.QAL_RecoverLostDevice()
		    commands.assert_called_once_with('snd_restart\\n')
		openal.AL_Shutdown()
		''')

	def test_finished_channel_cleanup(self) -> None:
		self.run_case('''
		assert openal.AL_Init()
		sfx = sample()
		ch = sound_c.channels[0]
		ch.sfx, ch.entnum, ch.oal_vol = sfx, -1, 1.0
		openal.AL_PlayChannel(ch)
		source = ch.srcnum.source
		source.stop()
		sound_c.s_doppler.value = 0
		with (
		    mock.patch.object(openal, 'AL_AddLoopSounds'),
		    mock.patch.object(openal.ogg, 'OGG_Stream'),
		):
		    openal.AL_Update()
		assert ch.sfx is None and source.closed
		openal.AL_Shutdown()
		''')

	def test_rejected_stream_parameters(self) -> None:
		self.run_case('''
		assert openal.AL_Init()
		openal.AL_RawSamples(100, 22050, 2, 1, bytes(200), 0.5)
		# The C ignores a rejected gain and still queues the PCM.
		openal.AL_RawSamples(100, 22050, 2, 1, bytes(200), -1.0)
		assert openal.streamSource.gain == 0.5
		assert openal.active_buffers == 2
		# A rejected buffer must not leak or abort the frame.
		openal.AL_RawSamples(100, 44100, 2, 1, bytes(200), 0.5)
		assert openal.active_buffers == 2
		openal.AL_Shutdown()
		''')


if __name__ == '__main__':
	unittest.main()
