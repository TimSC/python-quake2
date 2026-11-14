"""Background music from Ogg Vorbis files (Yamagi's ogg.c).

``MusicPlayer`` finds the music tracks (``music/02.ogg``..., or the GOG and
ReRelease names), plays the CD track a map asks for (or a shuffled one), and
streams the decoded samples to the sound backend as raw samples.
"""

from __future__ import annotations

import importlib
from enum import Enum
from types import ModuleType

import numpy as np

from client.sound.header import vorbis

MAX_TRACKS = 128


class GameType(Enum):
    OTHER = 0  # including baseq2
    XATRIX = 1
    ROGUE = 2


# The Reckoning (xatrix) used a mix of baseq2 and rogue tracks: its CD track
# -> the GOG TrackXX.ogg.
XATRIX_TRACKS = {2: 9, 3: 13, 4: 14, 5: 7, 6: 16, 7: 2, 8: 15, 9: 3, 10: 4, 11: 18}


def gog_track(track: int, game: GameType) -> int:
    """The GOG release's TrackXX number for a CD track (0: no track).

    GOG ships music/Track02.ogg to Track21.ogg next to baseq2: 02-11 are the
    baseq2 CD tracks 2-11, 12-21 Ground Zero's (rogue).
    """
    if track <= 1:
        return 0  # 1 is the CD's data track
    if game is GameType.OTHER:
        return track
    if game is GameType.ROGUE:
        return track + 10
    return XATRIX_TRACKS.get(track, track)


class _Engine:
    """The engine modules used, imported when first needed (they import this)."""

    _modules = {
        "cl_main": "client.cl_main", "client_h": "client.header.client",
        "sound_c": "client.sound.sound", "openal": "client.sound.openal",
        "sound_local": "client.sound.header.local", "stb_vorbis": "client.sound.header.stb_vorbis",
        "common_h": "common.header.common",
        "shared": "common.header.shared", "shared_c": "common.shared.shared",
        "rand": "common.shared.rand", "clientserver": "common.clientserver",
        "cmdparser": "common.cmdparser", "cvar": "common.cvar",
        "filesystem": "common.filesystem", "system": "backends.unix.system",
    }

    def __getattr__(self, name: str) -> ModuleType:
        module = importlib.import_module(self._modules[name])
        setattr(self, name, module)
        return module


E = _Engine()


def _print(text: str, *args) -> None:
    E.clientserver.Com_Printf(text, *args)


class MusicPlayer:
    """The music: the track list, what plays, and the saved state."""

    def __init__(self) -> None:
        self.pausewithgame = None  # cvars
        self.enabled = None
        self.shuffle = None
        self.ignoretrack0 = None
        self.volume = None
        self.curfile = 0           # the track playing (-1: none yet)
        self.numbufs = 0           # OpenAL buffers to keep queued
        self.numsamples = 0        # samples read from the current file
        self.mapcdtrack = 0        # the map's CD track
        self.status = vorbis.STOP  # or PLAY, PAUSE
        self.file = None           # the stb_vorbis decoder of the current file
        self.started = False
        self.muted = False
        self.tracks: list[str | None] = [None] * MAX_TRACKS
        self.maxfileindex = 0
        self.saved = False         # the state kept over a sound restart
        self.saved_curfile = 0
        self.saved_numsamples = 0

    # ------------------------------------------------------------ the tracks

    def init_track_list(self) -> None:
        """Find the music files: $mod/music/02.ogg..., or GOG's TrackXX.ogg,
        or the ReRelease's trackXX.ogg, in the raw search paths."""
        self.tracks = [None] * MAX_TRACKS
        self.maxfileindex = 0
        game = E.cvar.Cvar_Get("game", "", E.shared.CVAR_LATCH | E.shared.CVAR_SERVERINFO).string
        base = E.common_h.BASEDIRNAME
        if game in ("", base):
            music_dirs = [base + "/music/", "music/"]  # baseq2/music/, the GOG music dir
        else:
            music_dirs = [game + "/music/", "music/", base + "/music/"]
        game_type = {"xatrix": GameType.XATRIX, "rogue": GameType.ROGUE}.get(game,
                                                                              GameType.OTHER)
        system, filesystem = E.system, E.filesystem
        for music_dir in music_dirs:
            raw_path = filesystem.FS_GetNextRawPath(None)
            while raw_path is not None:
                directory = f"{raw_path}/{music_dir}"
                if system.Sys_IsDir(directory):
                    if system.Sys_IsFile(directory + "02.ogg"):  # $mod/music/02.ogg - 11.ogg ...
                        self.tracks[2] = directory + "02.ogg"
                        self._collect(lambda i, d=directory: f"{d}{i:02d}.ogg", 3)
                        return
                    for pattern in ("Track", "track"):  # GOG, ReRelease
                        probe = f"{directory}{pattern}{gog_track(8, game_type):02d}.ogg"
                        if system.Sys_IsFile(probe):
                            self._collect(lambda i, d=directory, p=pattern:
                                          f"{d}{p}{gog_track(i, game_type):02d}.ogg", 2)
                            return
                raw_path = filesystem.FS_GetNextRawPath(raw_path)
        _print("No Ogg Vorbis music tracks have been found, so there will be no music.\n")

    def _collect(self, name_of, first: int) -> None:
        for i in range(first, MAX_TRACKS):
            name = name_of(i)
            if E.system.Sys_IsFile(name):
                self.tracks[i] = name
                self.maxfileindex = i

    # -------------------------------------------------------------- playing

    def read(self) -> None:
        """Decode a block of the current file and queue it."""
        samples = np.zeros(4096, dtype=np.int16)
        volume = 0.0 if self.muted else self.volume.value
        stb = E.stb_vorbis
        count = stb.stb_vorbis_get_samples_short_interleaved(self.file, self.file.channels,
                                                             samples, len(samples))
        if count > 0:
            self.numsamples += count
            E.sound_c.S_RawSamples(count, self.file.sample_rate, 2, self.file.channels,
                                   samples.tobytes(), volume)
        else:
            # Not stop(): that would flush the queued samples (about 12 seconds
            # of music). The next file's samples queue after them instead.
            stb.stb_vorbis_close(self.file)
            self.status = vorbis.STOP
            self.numbufs = 0
            self.numsamples = 0
            self.play_track(f"{self.curfile}", False, False)

    def stream(self) -> None:
        """Keep the music queued (each frame)."""
        if not self.started:
            return
        # Music was disabled: shut down, so nothing plays or starts.
        if self.enabled.value != 1:
            self.shutdown()
            return
        if self.pausewithgame.modified:
            if ((self.pausewithgame.value == 0 and self.status == vorbis.PAUSE)
                    or (self.pausewithgame.value == 1 and self.status == vorbis.PLAY)):
                self.toggle_playback()
            self.pausewithgame.modified = False

        if self.status == vorbis.PLAY and E.sound_c.sound_started == E.sound_local.SS_OAL:
            # Keep 256 OpenAL buffers (about 12 seconds) more than the ones
            # active, against underruns; active_buffers counts sfx and music.
            openal = E.openal
            if self.numbufs == 0 or openal.active_buffers < self.numbufs - 256:
                self.numbufs = openal.active_buffers + 256
            while openal.active_buffers <= self.numbufs:
                self.read()

        if self.status == vorbis.PLAY and self.shuffle.modified:
            self.shuffle.modified = False  # changed before the last track finished
        elif self.status == vorbis.STOP and self.shuffle.modified:
            if E.cl_main.cls.state == E.client_h.connstate_t.ca_disconnected:
                self.mapcdtrack = 0  # the full screen console: track 0, no music
            # playback stopped and shuffle changed: play the map's track
            self.shuffle.modified = False
            self.play_track(f"{self.mapcdtrack}", True, True)

    def play_track(self, track: str, cdtrack: bool, immediate: bool) -> None:
        """Play the file music/<track> if there is one, else CD track number
        <track> (or, with ogg_shuffle, the next or a random one)."""
        sound_c = E.sound_c
        if sound_c.sound_started == E.sound_local.SS_NOT or not self.started:
            return

        path = None
        while (path := E.filesystem.FS_NextPath(path)) is not None:
            name = f"{path}/music/{track}"
            f = E.filesystem.Q_fopen(name, "rb")
            if f is None:
                continue
            if self.status == vorbis.PLAY:
                self.stop()
            result = [0]
            self.file = E.stb_vorbis.stb_vorbis_open_file(f, True, result, None)
            if result[0] != 0:
                _print(f"OGG_PlayTrack: '{name}' is not a valid Ogg Vorbis file "
                       f"(error {result[0]}).\n")
                return
            self.curfile = 0
            self.numsamples = 0
            self.status = vorbis.PLAY
            return

        try:
            number = int(track)  # the C's strtol: 0 on failure
        except ValueError:
            number = 0

        if number == 0:  # track 0 means "stop music"
            if self.ignoretrack0.value == 0:
                self.stop()
                return
            # With ogg_ignoretrack0 the music goes on; but after a restart
            # (curfile not set yet) a random track is shuffled below.
            if self.curfile > 0:
                return

        if cdtrack:
            self.mapcdtrack = number

        playback = self.shuffle.value
        state = E.cl_main.cls.state
        connstate = E.client_h.connstate_t
        # Loading a map, restarting sound or video, the console or nothing
        # played yet: play the asked track, and shuffle from it next time.
        if ((not immediate and state in (connstate.ca_connecting, connstate.ca_connected))
                or immediate or self.curfile == -1):
            current = number
            playback = 0
        else:
            current = self.curfile

        last = self.maxfileindex
        if playback == 0:      # default (these match the options menu)
            new = current
        elif playback == 1:    # play once
            return
        elif playback == 2:    # sequential
            new = current + 1 if (current + 1) % (last + 1) != 0 else 2
        elif playback == 3:    # random
            new = E.rand.randk() % (last - 1) + 2
            new = new + 1 if new == current else new
            new = 2 if new > last else new
        else:
            new = 0
        number = new

        if last == -1:
            return  # no music at all: no warnings every time
        if number < 2 or number > last:
            _print("OGG_PlayTrack: %d out of range.\n", number)
            return
        if self.tracks[number] is None:
            _print("OGG_PlayTrack: Don't have a .ogg file for track %d\n", number)

        if self.status == vorbis.PLAY:
            if self.curfile == number:
                return
            self.stop()

        if self.tracks[number] is None:
            _print("OGG_PlayTrack: I don't have a file for track %d!\n", number)
            return

        f = E.filesystem.Q_fopen(self.tracks[number], "rb")
        if f is None:
            _print("%s: could not open file %s for track %d: %s.\n", "OGG_PlayTrack",
                   self.tracks[number], number, "No such file or directory")
            self.tracks[number] = None
            return
        result = [0]
        self.file = E.stb_vorbis.stb_vorbis_open_file(f, True, result, None)
        if result[0] != 0:
            _print("%s: '%s' is not a valid Ogg Vorbis file (error %i).\n", "OGG_PlayTrack",
                   self.tracks[number], result[0])
            return
        self.curfile = number
        self.numsamples = 0
        self.status = vorbis.PLAY

    def stop(self) -> None:
        if self.status == vorbis.STOP:
            return
        backend = E.sound_c.backend
        if backend is not None:
            backend.unqueue_raw_samples()
        E.stb_vorbis.stb_vorbis_close(self.file)
        self.status = vorbis.STOP
        self.numbufs = 0

    def toggle_playback(self) -> None:
        """Pause or resume."""
        if self.status == vorbis.PLAY:
            self.status = vorbis.PAUSE
            self.numbufs = 0
            backend = E.sound_c.backend
            if backend is not None:
                backend.unqueue_raw_samples()
        elif self.status == vorbis.PAUSE:
            self.status = vorbis.PLAY

    # -------------------------------------------------------- the console

    def info(self) -> None:
        """ogg info: the tracks and the playback state."""
        _print("Tracks:\n")
        for i in range(2, self.maxfileindex + 1):
            _print(" - %02d %s\n", i, self.tracks[i] if self.tracks[i] else "<none>")
        _print("Total: %d Ogg/Vorbis files.\n", self.maxfileindex + 1)
        stb = E.stb_vorbis
        if self.status in (vorbis.PLAY, vorbis.PAUSE):
            state = "Playing" if self.status == vorbis.PLAY else "Paused"
            _print("State: %s file %d (%s) at %i samples.\n", state, self.curfile,
                   self.tracks[self.curfile], stb.stb_vorbis_get_sample_offset(self.file))
        elif self.status == vorbis.STOP:
            if self.curfile == -1:
                _print("State: Stopped.\n")
            else:
                _print("State: Stopped file %d (%s).\n", self.curfile, self.tracks[self.curfile])

    def command(self, args: list[str]) -> None:
        """The 'ogg' console command."""
        sub = args[1].lower() if len(args) > 1 else None
        if sub == "info":
            self.info()
        elif sub == "mute":
            self.muted = not self.muted
        elif sub == "play":
            if len(args) != 3:
                _print("ogg play <track> : Play <track>")
                return
            self.play_track(args[2], False, True)
        elif sub == "skip":
            current = f"{self.curfile}"
            self.stop()
            self.play_track(current, False, False)
        elif sub == "stop":
            self.stop()
        elif sub == "toggle":
            self.toggle_playback()
        else:
            _print("Unknown sub command %s\n\n", args[1] if len(args) > 1 else "")
            _print("Commands:\n")
            _print(" - info: Print information about playback state and tracks\n")
            _print(" - play <track>: Play track number <track>\n")
            _print(" - stop: Stop playback\n")
            _print(" - toggle: Toggle pause\n")
            _print(" - mute: Mute playback\n")

    # ------------------------------------------------------ save / recover

    def save_state(self) -> None:
        """Keep what plays over a sound restart. (enabled is None when init
        never ran, e.g. with sound off: the C dereferences NULL here.)"""
        if self.enabled is None or self.enabled.value != 1 or self.status != vorbis.PLAY:
            self.saved = False
            return
        self.saved = True
        self.saved_curfile = self.curfile
        self.saved_numsamples = self.numsamples

    def recover_state(self) -> None:
        if self.enabled is None or self.enabled.value != 1 or not self.saved:
            return
        # play_track() shuffles; switch shuffle off while recovering
        shuffle = self.shuffle.value
        E.cvar.Cvar_SetValue("ogg_shuffle", 0)
        self.play_track(f"{self.saved_curfile}", False, True)
        E.stb_vorbis.stb_vorbis_seek_frame(self.file, self.saved_numsamples)
        self.numsamples = self.saved_numsamples
        E.cvar.Cvar_SetValue("ogg_shuffle", shuffle)

    # ------------------------------------------------------- start / stop

    def init(self) -> None:
        cvar, shared = E.cvar, E.shared
        self.pausewithgame = cvar.Cvar_Get("ogg_pausewithgame", "0", shared.CVAR_ARCHIVE)
        self.shuffle = cvar.Cvar_Get("ogg_shuffle", "0", shared.CVAR_ARCHIVE)
        self.ignoretrack0 = cvar.Cvar_Get("ogg_ignoretrack0", "0", shared.CVAR_ARCHIVE)
        self.volume = cvar.Cvar_Get("ogg_volume", "0.7", shared.CVAR_ARCHIVE)
        self.enabled = cvar.Cvar_Get("ogg_enable", "1", shared.CVAR_ARCHIVE)
        if self.enabled.value != 1:
            return
        cmdparser = E.cmdparser
        cmdparser.Cmd_AddCommand("ogg", lambda: self.command(
            [cmdparser.Cmd_Argv(i) for i in range(cmdparser.Cmd_Argc())]))
        self.curfile = -1
        self.numsamples = 0
        self.status = vorbis.STOP
        self.mapcdtrack = 0
        self.muted = False
        self.started = True

    def shutdown(self) -> None:
        if not self.started:
            return
        self.stop()
        self.tracks = [None] * MAX_TRACKS
        self.maxfileindex = 0
        E.cmdparser.Cmd_RemoveCommand("ogg")
        self.started = False


def load_as_wav(filename: str):
    """A whole .ogg file decoded into a wavinfo_t and 16-bit samples (for
    sounds given as .ogg); (None, None) if it can't be."""
    size, data = E.filesystem.FS_LoadFile(filename)
    if data is None:
        return None, None
    info = buffer = None
    stb = E.stb_vorbis
    result = [0]
    decoder = stb.stb_vorbis_open_memory(data, size, result, None)
    if not result[0] and decoder.channels > 0:
        info = E.sound_local.wavinfo_t()
        info.rate = decoder.sample_rate
        info.width = 2
        info.channels = decoder.channels
        info.loopstart = -1
        info.samples = stb.stb_vorbis_stream_length_in_samples(decoder) * info.channels
        info.dataofs = 0
        samples = np.zeros(info.samples, dtype=np.int16)
        count = stb.stb_vorbis_get_samples_short_interleaved(decoder, info.channels, samples,
                                                             info.samples)
        if count > 0:
            if count * info.channels != info.samples:
                E.clientserver.Com_DPrintf("%s: incorrect size: %d != %d\n", filename,
                                           info.samples, count * info.channels)
                info.samples = count * info.channels
            buffer = samples[:info.samples].tobytes()
    if decoder:
        stb.stb_vorbis_close(decoder)
    E.filesystem.FS_FreeFile(data)
    return info, buffer
