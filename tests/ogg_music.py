# Drive the OGG music subsystem (client/sound/ogg.py, OpenAL stream source backend):
# track listing, play/pause/stop, save/recover state, volume and shutdown.
# Tracks 02 and 03 come from $Q2DATA/music/. Any that are missing are copied in
# from the repo's music/ (named by CD track, see music/README.md) and removed
# afterwards; music that was already there is left alone.
import os, sys, shutil, time, atexit, subprocess
os.environ.setdefault("Q2PORT_NOMOUSE", "1")  # no mouse capture (tests)
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

Q2DATA = os.environ.get("Q2DATA", "/home/tim/dev/quake2data/Data")
MUSICDIR = os.path.join(Q2DATA, "music")
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music")

created_dir = not os.path.isdir(MUSICDIR)
staged = [] # files this test copied in, the only ones it removes
os.makedirs(MUSICDIR, exist_ok=True)

# a 1s mono ogg sample to exercise the S_LoadVorbis (.wav -> .ogg) fallback
SOUNDDIR = os.path.join(Q2DATA, "baseq2", "sound", "misc")
OGGSAMPLE = os.path.join(SOUNDDIR, "oggtest.ogg")
os.makedirs(SOUNDDIR, exist_ok=True)

def cleanup():
	for f in staged:
		if os.path.exists(f):
			os.remove(f)
	if created_dir and not os.listdir(MUSICDIR):
		os.rmdir(MUSICDIR)
	if os.path.exists(OGGSAMPLE):
		os.remove(OGGSAMPLE)

atexit.register(cleanup)
for name in ["02.ogg", "03.ogg"]:
	dst = os.path.join(MUSICDIR, name)
	if not os.path.exists(dst):
		shutil.copy(os.path.join(SRC, name), dst)
		staged.append(dst)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(MUSICDIR, "02.ogg"), "-t", "1", "-ac", "1", "-c:a", "libvorbis", "-q:a", "5", OGGSAMPLE], check=True)
print("ogg: music staged in", MUSICDIR)

from backends.unix import system
from client import cl_main
from client.vid import glimp_sdl2
from client.refresh.gl1 import gl1_sdl # the gl1 frame swap (Yamagi's RI_EndFrame)
from client.sound import ogg
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
from openal_py import SourceState
from client.sound.header import vorbis
from common import cmdparser, cvar


st = {"t0": None, "step": 0}

oe = gl1_sdl.RI_EndFrame
def EF():
	if cl_main.cls.state.name == "ca_active":
		if st["t0"] is None:
			st["t0"] = time.time()
		t = time.time() - st["t0"]
		step = st["step"]
		if step == 0 and t > 2:
			if not ogg.player.started:
				ogg.OGG_Init()
				ogg.OGG_InitTrackList()
			assert ogg.player.maxfileindex >= 3, "track list empty: {}".format(ogg.player.maxfileindex)
			print("ogg: listed tracks up to", ogg.player.maxfileindex)
			# S_LoadVorbis: the .wav is missing, the .ogg is picked up
			assert sound_c.sound_started == sound_local.SS_OAL, "OpenAL not started: {}".format(sound_c.sound_started)
			s = sound_local.sfx_t()
			s.name = "misc/oggtest.wav"
			sc = sound_c.S_LoadSound(s)
			assert sc is not None and sc.sound and not sc.sound.closed, "ogg sample not loaded"
			print("ogg: sample loaded into OpenAL buffer", sc.sound, "length", sc.length, "ms")
			ogg.OGG_PlayTrack("2", True, True)
			assert ogg.OGG_Status() == vorbis.PLAY
			st["step"] = 1
			st["t0"] = time.time()
		elif step == 1 and t > 1:
			assert ogg.player.numsamples > 0, "no samples read, pos {}".format(ogg.player.numsamples)
			state = sound_c.backend.stream_source.state
			assert state == SourceState.PLAYING, "stream source not playing: {:#x}".format(state)
			print("ogg: playing track 2 at", ogg.player.numsamples, "samples,", sound_c.backend.active_buffers, "buffers queued")
			ogg.OGG_TogglePlayback()
			assert ogg.OGG_Status() == vorbis.PAUSE
			ogg.OGG_TogglePlayback()
			assert ogg.OGG_Status() == vorbis.PLAY
			cvar.Cvar_SetValue("ogg_volume", 0.5)
			ogg.OGG_Read() # the volume goes with the next samples (S_RawSamples)
			gain = sound_c.backend.stream_source.gain
			assert abs(gain - 0.5) < 0.01, "volume {}".format(gain)
			print("ogg: pause/resume ok, volume ok")
			ogg.OGG_SaveState()
			assert ogg.player.saved
			ogg.OGG_Stop()
			assert ogg.OGG_Status() == vorbis.STOP
			ogg.OGG_RecoverState()
			assert ogg.OGG_Status() == vorbis.PLAY
			print("ogg: save/recover ok")
			st["step"] = 2
			st["t0"] = time.time()
		elif step == 2 and t > 1:
			st["old_backend"] = sound_c.backend
			cmdparser.Cbuf_AddText("snd_restart\n")
			st["step"] = 3
			st["t0"] = time.time()
		elif step == 3 and t > 2:
			assert sound_c.backend is not st["old_backend"]
			assert st["old_backend"].context.closed
			assert st["old_backend"].device.closed
			assert sound_c.backend.stream_source.state == SourceState.PLAYING
			assert sound_c.backend.underwater_filter is not None
			print("ogg: snd_restart recovered playback and effects")
			ogg.OGG_PlayTrack("3", False, True)
			assert ogg.player.curfile == 3
			ogg.OGG_Shutdown()
			assert ogg.OGG_Status() == vorbis.STOP and not ogg.player.started
			print("ogg: done")
			sys.stdout.flush()
			os._exit(0)
	return oe()
gl1_sdl.RI_EndFrame = EF
system.main()
