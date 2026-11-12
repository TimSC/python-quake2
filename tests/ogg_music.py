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

import ctypes
from backends.unix import system
from client import cl_main
from client.vid import glimp_sdl2
from client.refresh.gl1 import gl1_sdl # the gl1 frame swap (Yamagi's RI_EndFrame)
from client.sound import ogg, openal, qal
from client.sound import sound as sound_c
from client.sound.header import local as sound_local
from client.sound.header import qal as qal_h
from client.sound.header import vorbis
from common import cvar

AL_PLAYING = 0x1012 # al.h; Yamagi's code doesn't use it, so header/qal.py hasn't got it

st = {"t0": None, "step": 0}

oe = gl1_sdl.RI_EndFrame
def EF():
	if cl_main.cls.state.name == "ca_active":
		if st["t0"] is None:
			st["t0"] = time.time()
		t = time.time() - st["t0"]
		step = st["step"]
		if step == 0 and t > 2:
			if not ogg.ogg_started:
				ogg.OGG_Init()
				ogg.OGG_InitTrackList()
			assert ogg.ogg_maxfileindex >= 3, "track list empty: {}".format(ogg.ogg_maxfileindex)
			print("ogg: listed tracks up to", ogg.ogg_maxfileindex)
			# S_LoadVorbis: the .wav is missing, the .ogg is picked up
			assert sound_c.sound_started == sound_local.SS_OAL, "OpenAL not started: {}".format(sound_c.sound_started)
			s = sound_local.sfx_t()
			s.name = "misc/oggtest.wav"
			sc = sound_c.S_LoadSound(s)
			assert sc is not None and sc.bufnum and qal.qalIsBuffer(sc.bufnum), "ogg sample not loaded"
			print("ogg: sample loaded into OpenAL buffer", sc.bufnum, "length", sc.length, "ms")
			ogg.OGG_PlayTrack("2", True, True)
			assert ogg.OGG_Status() == vorbis.PLAY
			st["step"] = 1
			st["t0"] = time.time()
		elif step == 1 and t > 1:
			assert ogg.ogg_numsamples > 0, "no samples read, pos {}".format(ogg.ogg_numsamples)
			state = qal.ALint()
			qal.qalGetSourcei(openal.streamSource, qal_h.AL_SOURCE_STATE, ctypes.byref(state))
			assert state.value == AL_PLAYING, "stream source not playing: {:#x}".format(state.value)
			print("ogg: playing track 2 at", ogg.ogg_numsamples, "samples,", openal.active_buffers, "buffers queued")
			ogg.OGG_TogglePlayback()
			assert ogg.OGG_Status() == vorbis.PAUSE
			ogg.OGG_TogglePlayback()
			assert ogg.OGG_Status() == vorbis.PLAY
			cvar.Cvar_SetValue("ogg_volume", 0.5)
			ogg.OGG_Read() # the volume goes with the next samples (S_RawSamples)
			gain = qal.ALfloat()
			qal.qalGetSourcef(openal.streamSource, qal_h.AL_GAIN, ctypes.byref(gain))
			assert abs(gain.value - 0.5) < 0.01, "volume {}".format(gain.value)
			print("ogg: pause/resume ok, volume ok")
			ogg.OGG_SaveState()
			assert ogg.ogg_saved_state.saved
			ogg.OGG_Stop()
			assert ogg.OGG_Status() == vorbis.STOP
			ogg.OGG_RecoverState()
			assert ogg.OGG_Status() == vorbis.PLAY
			print("ogg: save/recover ok")
			st["step"] = 2
			st["t0"] = time.time()
		elif step == 2 and t > 1:
			ogg.OGG_PlayTrack("3", False, True)
			assert ogg.ogg_curfile == 3
			ogg.OGG_Shutdown()
			assert ogg.OGG_Status() == vorbis.STOP and not ogg.ogg_started
			print("ogg: done")
			sys.stdout.flush()
			os._exit(0)
	return oe()
gl1_sdl.RI_EndFrame = EF
system.main()
