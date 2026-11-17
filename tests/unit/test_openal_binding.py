"""Exercise the installed object API without hardware, a window or game data."""

import os
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize("scenario", [
    """
    # Restart must recreate usable effects as well as playback resources.
    for attempt in range(2):
        backend = OpenALBackend.start()
        assert backend is not None
        context, device = backend.context, backend.device
        assert isinstance(backend.stream_source, al.Source)
        assert context.distance_model == al.DistanceModel.LINEAR_CLAMPED
        assert context.doppler_factor == 2.0
        assert backend.num_channels == 31
        assert isinstance(backend.audio, al.AudioEngine)
        backend.raw_samples(100, 22050, 2, 1, bytes(200), 0.5)
        buffer = next(iter(backend.buffers))
        assert buffer.size == 200
        assert backend.active_buffers == 1
        backend._stream_update()
        assert backend.stream_source.gain == 0.5
        backend.unqueue_raw_samples()
        assert buffer.closed
        assert backend.active_buffers == 0
        asset = backend.audio.sound_from_pcm(bytes(200), format=al.AudioFormat.MONO16,
                                             sample_rate=22050)
        voice = backend.audio.play(asset, looping=True)
        backend._update_underwater_cvars()
        backend.underwater()
        assert voice.source.direct_filter is backend.underwater_filter
        backend.overwater()
        assert voice.source.direct_filter is None
        backend.set_reverb(3)
        assert abs(backend.reverb_effect.parameters['decay_time'] - 1.49) < 0.001
        backend.shutdown()
        backend.shutdown()
        assert device.closed and context.closed
    """,
    """
    backend = OpenALBackend.start()
    try:
        sfx = local.sfx_t()
        sfx.name = 'generated'
        info = local.wavinfo_t()
        info.samples, info.width, info.channels, info.rate = 100, 2, 1, 22050
        info.loopstart = -1
        cache = backend.upload_sfx(sfx, info, bytes(200), 255, 0, 0, 0, 0)
        assert cache.size == 200 and cache.length == 4
        assert isinstance(cache.sound, al.Sound)
        ch = local.channel_t()
        sound.channels = [ch]
        sound.s_numchannels = 1
        ch.sfx, ch.entnum = sfx, -1
        backend.start_channel(ch, 0.5, 0.8)
        voice, source = ch.voice, ch.voice.source
        assert voice.sound is cache.sound
        assert source.relative and source.gain == pytest.approx(0.4)
        assert source.position == (0.0, 0.0, 0.0)
        assert source.max_distance == 8192
        backend.stop_channel(ch)
        assert voice.closed and source.closed and ch.sfx is None
        # New voices must inherit underwater filtering before playback starts.
        sound.snd_is_underwater = True
        backend._update_underwater_cvars()
        ch.sfx, ch.entnum = sfx, -1
        backend.start_channel(ch, 0.5, 0.8)
        assert ch.voice.source.direct_filter is backend.underwater_filter
        backend.stop_channel(ch)
        backend.delete_sfx(sfx)
        assert cache.sound.closed and backend.active_buffers == 0
    finally:
        backend.shutdown()
    """,
    """
    backend = OpenALBackend.start()
    try:
        ch = local.channel_t()
        asset = backend.audio.sound_from_pcm(bytes(200), format=al.AudioFormat.MONO16,
                                             sample_rate=22050)
        ch.voice = backend.audio.play(asset, looping=True)
        ch.entnum, ch.dist_mult = 2, 0.001
        origin, velocity = (100, 200, 300), (1, 2, 3)
        def get_origin(ent, listener, out):
            out[:] = origin
        with patch.object(sound, 'GetEntitySoundOrigin',
                          side_effect=get_origin), \
             patch('client.sound.openal.cl_entities.CL_GetEntitySoundVelocity',
                   side_effect=lambda ent, out: out.__setitem__(slice(None), velocity)):
            backend._spatialize(ch)
            assert ch.voice.source.position == (-200, 300, -100)
            assert ch.voice.source.velocity == pytest.approx((-0.063, 0.0945, -0.0315))
            assert ch.voice.source.get_send(0)[0] is backend.reverb_slot
            sound.s_occlusion_strength.value = 0.5
            with patch('client.sound.openal.collision.CM_BoxTrace',
                       return_value=SimpleNamespace(fraction=0.5)):
                backend._spatialize(ch)
            assert ch.voice.source.direct_filter is backend.occlusion_filter
            assert ch.voice.source.get_send(0) is None
    finally:
        backend.shutdown()
    """,
    """
    # When a stream drains, only the samples queued since the last update survive.
    backend = OpenALBackend.start()
    try:
        backend.raw_samples(100, 22050, 2, 1, bytes(200), 1.0)
        old = next(iter(backend.buffers))
        backend._stream_update()
        backend.stream_source.stop()
        backend.raw_samples(100, 22050, 2, 1, bytes(200), 1.0)
        backend._stream_update()
        assert old.closed
        assert backend.active_buffers == 1
        assert backend.stream_source.buffers_queued == 1
    finally:
        backend.shutdown()
    """,
    """
    with patch.object(al.Device, 'open', side_effect=al.ALCError(0xA005)):
        assert OpenALBackend.start() is None
    """,
    """
    device = al.Device.open()
    with patch.object(al.Device, 'open', return_value=device), \\
         patch.object(al.Device, 'create_context', side_effect=al.ALCError(0xA005)):
        assert OpenALBackend.start() is None
    assert device.closed
    """,
    """
    device = al.Device.open()
    context = device.create_context()
    with patch.object(al.Device, 'open', return_value=device), \\
         patch.object(al.Device, 'create_context', return_value=context), \\
         patch.object(al.Context, 'make_current', side_effect=al.ALCError(0xA005)):
        assert OpenALBackend.start() is None
    assert context.closed and device.closed
    """,
    """
    original = al.Device.supports
    def supports(device, extension):
        return extension != 'ALC_EXT_EFX' and original(device, extension)
    with patch.object(al.Device, 'supports', supports):
        backend = OpenALBackend.start()
        assert backend is not None
        assert backend.reverb_slot is None and backend.underwater_filter is None
        ch = local.channel_t()
        asset = backend.audio.sound_from_pcm(bytes(200), format=al.AudioFormat.MONO16,
                                             sample_rate=22050)
        ch.voice = backend.audio.play(asset, looping=True)
        ch.entnum, ch.dist_mult = 2, 0.001
        sound.s_doppler.value = 0
        with patch.object(sound, 'GetEntitySoundOrigin'):
            backend._spatialize(ch)
        backend.underwater()
        backend.overwater()
        backend.shutdown()
    """,
    """
    # An exhausted source pool must fail cleanly, including its stream source.
    device = al.Device.open()
    with patch.object(al.Device, 'open', return_value=device), \\
         patch.object(al.Context, 'create_source', side_effect=al.ALLError(0xA005)):
        assert OpenALBackend.start() is None
    assert device.closed
    """,
    """
    backend = OpenALBackend.start()
    try:
        with patch.object(al.Device, 'get_parameter', return_value=0), \\
             patch.object(cvar, 'Cvar_VariableValue', return_value=1), \\
             patch.object(cmdparser, 'Cbuf_AddText') as commands:
            assert not backend._recover_lost_device()
            assert not backend._recover_lost_device()
            assert not backend._recover_lost_device()
            commands.assert_called_once_with('snd_restart\\n')
    finally:
        backend.shutdown()
    """,
    """
    backend = OpenALBackend.start()
    try:
        asset = backend.audio.sound_from_pcm(bytes(200), format=al.AudioFormat.MONO16,
                                             sample_rate=22050)
        ch = local.channel_t()
        ch.sfx = SimpleNamespace(name='generated')
        ch.voice = backend.audio.play(asset, looping=True)
        source = ch.voice.source
        source.stop()
        sound.channels, sound.s_numchannels = [ch], 1
        sound.s_pendingplays = []
        sound.s_doppler.value = 0
        with (
            patch.object(backend, '_add_loop_sounds'),
            patch('client.sound.openal.ogg.OGG_Stream'),
        ):
            backend.update()
        assert source.closed and ch.sfx is None
        assert backend.frame_count == 1
    finally:
        backend.shutdown()
    """,
    """
    import io
    import numpy as np
    import soundfile
    from client.sound.header import stb_vorbis as vorbis

    encoded = io.BytesIO()
    samples = np.sin(np.arange(4096) * 0.1).astype(np.float32) * 0.25
    soundfile.write(encoded, samples, 22050, format='OGG', subtype='VORBIS')
    data = encoded.getvalue()
    # Decode while OpenAL owns the current context, then clean up normally.
    for attempt in range(2):
        backend = OpenALBackend.start()
        assert backend is not None
        decoder = None
        try:
            error = [-1]
            decoder = vorbis.stb_vorbis_open_memory(data, len(data), error, None)
            assert decoder is not None and error[0] == 0
            buffer = np.zeros(1024, dtype=np.int16)
            while True:
                count = vorbis.stb_vorbis_get_samples_short_interleaved(
                    decoder, decoder.channels, buffer, len(buffer))
                if not count:
                    break
                backend.raw_samples(count, decoder.sample_rate, 2, decoder.channels,
                                    buffer[:count].tobytes(), 0.5)
            assert backend.active_buffers > 0
            backend._stream_update()
            assert backend.stream_source.state == al.SourceState.PLAYING
            # A test or interrupt must unwind before native resources close.
            raise SystemExit(0)
        except SystemExit as finished:
            assert finished.code == 0
        finally:
            if decoder is not None:
                vorbis.stb_vorbis_close(decoder)
            backend.shutdown()
        assert decoder.handle.closed
        assert backend.context.closed and backend.device.closed
    """,
], ids=[
    "restart-and-effects", "channel-and-buffer", "spatial-audio", "stream-underrun",
    "device-failure", "context-failure", "activation-failure", "without-efx",
    "source-exhaustion", "device-recovery", "finished-voice", "soundfile-stream-cleanup",
])
def test_current_openal_binding(scenario: str) -> None:
    # Library selection stays fixed after import. Isolate it from other tests.
    preamble = """
from types import SimpleNamespace
from unittest.mock import patch
import pytest
import openal_py as al
from client.sound import sound
from client.sound.header import local
from client.sound.openal import OpenALBackend
from common import cvar, cmdparser
for name, value in {
    's_doppler': 1, 's_underwater': 1, 's_underwater_gain_hf': 0.25,
    's_reverb_preset': 0, 's_show': 0, 's_occlusion_strength': 0,
}.items():
    setattr(sound, name, SimpleNamespace(value=value, modified=True))
sound.channels = []
sound.s_numchannels = 0
"""
    result = subprocess.run(
        [sys.executable, "-c", preamble + textwrap.dedent(scenario)],
        env={**os.environ, "ALSOFT_DRIVERS": "null"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
