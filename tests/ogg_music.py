# Drive the OGG music subsystem (client/sound/ogg.py, pygame.mixer.music backend):
# track listing, play/pause/stop, save/recover state, volume and shutdown.
# Music is copied into $Q2DATA/music/ for the run and removed afterwards.
import os, sys, shutil, time, atexit, subprocess
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

Q2DATA = os.environ.get("Q2DATA", "/home/tim/dev/quake2data/Data")
MUSICDIR = os.path.join(Q2DATA, "music")
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "soundtrack_ogg")

os.makedirs(MUSICDIR, exist_ok=True)

# a 1s mono ogg sample to exercise the S_LoadVorbis (.wav -> .ogg) fallback
SOUNDDIR = os.path.join(Q2DATA, "baseq2", "sound", "misc")
OGGSAMPLE = os.path.join(SOUNDDIR, "oggtest.ogg")
os.makedirs(SOUNDDIR, exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(SRC, "02-Rage.ogg"), "-t", "1", "-ac", "1", "-c:a", "libvorbis", "-q:a", "5", OGGSAMPLE], check=True)

def cleanup():
	shutil.rmtree(MUSICDIR, ignore_errors=True)
	if os.path.exists(OGGSAMPLE):
		os.remove(OGGSAMPLE)

atexit.register(cleanup)
for i, name in [(2, "02-Rage.ogg"), (3, "03-Kill Ratio.ogg")]:
	shutil.copy(os.path.join(SRC, name), os.path.join(MUSICDIR, "{:02d}.ogg".format(i)))
print("ogg: music staged in", MUSICDIR)

import pygame
from backends.unix import system
from client import cl_main
from client.vid import glimp_sdl2
from client import snd_loc, snd_mem
from client.sound import ogg
from client.sound.header import vorbis
from common import cvar

st = {"t0": None, "step": 0}

oe = glimp_sdl2.GLimp_EndFrame
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
			s = snd_loc.sfx_t()
			s.name = "misc/oggtest.wav"
			sc = snd_mem.S_LoadSound(s)
			assert sc is not None and isinstance(sc.data, pygame.mixer.Sound), "ogg sample not loaded"
			print("ogg: sample loaded, length", sc.length)
			ogg.OGG_PlayTrack("2", True, True)
			assert ogg.OGG_Status() == vorbis.PLAY
			st["step"] = 1
			st["t0"] = time.time()
		elif step == 1 and t > 1:
			assert ogg.ogg_numsamples > 0, "no samples read, pos {}".format(ogg.ogg_numsamples)
			print("ogg: playing track 2 at", ogg.ogg_numsamples, "ms")
			ogg.OGG_TogglePlayback()
			assert ogg.OGG_Status() == vorbis.PAUSE
			ogg.OGG_TogglePlayback()
			assert ogg.OGG_Status() == vorbis.PLAY
			cvar.Cvar_SetValue("ogg_volume", 0.5)
			ogg.OGG_Stream()
			assert abs(pygame.mixer.music.get_volume() - 0.5) < 0.01, "volume {}".format(pygame.mixer.music.get_volume())
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
glimp_sdl2.GLimp_EndFrame = EF
system.main()
