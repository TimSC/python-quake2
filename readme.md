# Quake II in Python

A Quake II engine written in Python, with the features of
[Yamagi Quake II](https://github.com/yquake2/yquake2). It plays the original
game and talks to C Quake II clients and servers over the network.

This is the engine only. The maps, textures, models and sounds are
proprietary: you need the data from a copy of the game you own
(`baseq2/pak0.pak` and so on). It is not included.

The code started as a line-by-line port of id Software's C source (3.21), then
moved to Yamagi Quake II's source. Most of it was ported with the help of
ChatGPT, Claude and qwen.

## This branch: a Pythonic rewrite

The `pythonic` branch drops the rule that the Python mirrors the C. The code
is reworked, step by step, into ordinary Python:

- **Style:** PEP 8 names and layout, type hints, dataclasses and numpy.
- **State:** objects instead of module-level global state.
- **Repetition:** repetitive code folded into tables and helpers.
- **Loading library:** a self-contained package, `q2data`, for reading
  Quake II data (PAK/PK3, maps, models, images, sounds). It can be used
  without the engine.

What the player sees stays the same:
- the network protocol;
- the game data and map formats;
- save games and demos;
- console commands, cvars and config files.

The game keeps running after every step. The plan and the order of the
steps are in [docs/pythonic_plan.md](docs/pythonic_plan.md). Until a part
has been reworked, it still reads like the C it came from.

## Other branches

The earlier stages of the port live on as their own branches. Both keep the
structure of the C they were ported from, so they can be read side by side
with it.

| Branch | Ported from | Use it to |
|---|---|---|
| [`original`](https://github.com/TimSC/python-quake2/tree/original) | id Software's Quake II 3.21 C source | see the first port, which follows id's C line by line (file names, function names, globals and layout) |
| [`yquake2`](https://github.com/TimSC/python-quake2/tree/yquake2) | Yamagi Quake II's C source | compare the Python with Yamagi's C: each C file has a Python file at the same path, with the same functions in the same order |

On `yquake2`, a change made only in the Python (a fix, or something C does
differently) is marked with a `Q2PORT` comment. Bugs found on this branch
that `yquake2` shares are listed in
[docs/yquake2_fixes.md](docs/yquake2_fixes.md).

## Features

- Single player and deathmatch on the original maps, with all monsters,
  weapons, items and bosses.
- Two OpenGL renderers: OpenGL 1 (`gl1`, the default) and OpenGL 3.2 core
  (`gl3`).
- Sound through OpenAL, with music from OGG files.
- Cinematics, demos and `timedemo`.
- Save games in Yamagi's format.
- Network play against C Quake II servers and clients (protocol 34), over
  IPv4 and IPv6, with LAN server search and HTTP downloads.
- A dedicated server that takes commands from the terminal.
- Screenshots in TGA, BMP, PNG and JPG.

Not included:
- the software and Vulkan renderers;
- gamepad and gyro input;
- the C software sound mixer;
- the mission packs and Capture the Flag;
- platforms other than Linux.

## Requirements

- Python 3.12 or later.
- The packages in `requirements.txt`: pyglet, PyOpenGL, numpy, Pillow and
  pycurl.
- For sound, the system's OpenAL library (`libopenal.so.1`, e.g. the
  `libopenal1` package). The game loads it itself; pip's pyglet doesn't
  include it.
- For OGG music, FFmpeg's libraries, which pyglet loads.
- The Quake II game data.

## Setup

```
python3 -m venv env
env/bin/pip install -r requirements.txt
```

For development (tests), install `requirements-dev.txt` instead.

## Running

Point `-datadir` at the folder that contains `baseq2`:

```
env/bin/python main.py -datadir /path/to/quake2data/Data
```

Commands after `+` run at startup, as in the original game. For example, to
start a map at a chosen skill (0 to 3):

```
env/bin/python main.py -datadir /path/to/quake2data/Data +skill 1 +map base1
```

To measure performance on a demo:

```
env/bin/python main.py -datadir /path/to/quake2data/Data +demomap demo1.dm2 +timedemo 1
```

### Renderer

The `vid_renderer` cvar picks the renderer: `gl1` (the default) or `gl3`.
Change it in the video menu, or on the command line with
`+set vid_renderer gl3`. The `Q2_RENDERER` environment variable overrides
the cvar.

### Dedicated server

```
env/bin/python main.py -datadir /path/to/quake2data/Data +set dedicated 1 +map base1
```

Type server commands such as `status`, `serverinfo` or `map base2` into the
terminal.

### Terminal commands in the windowed game

The windowed game ignores the terminal, as the original does. Set
`Q2STDIN=1` to have it read commands from the terminal as well. Commands can
also be piped in, which is useful for scripted tests:

```
Q2STDIN=1 env/bin/python main.py -datadir /path/to/quake2data/Data +map base1
```

### OpenGL error checking

PyOpenGL checks for an OpenGL error after every call by default. That costs
speed. Set `PYOPENGL_ERROR_CHECKING=0` to turn it off.

## Tests

- **Unit tests:** they don't need the game data. They build their own small
  map, model, image and archive files.

  ```
  env/bin/python -m pytest tests/unit
  ```

- **Engine tests:** these need the game data. They play maps, fight
  monsters, save and load, and run a dedicated server. They also compare
  collision and player movement with Yamagi's C code:

  ```
  tests/run_all.sh
  tests/harness/run.sh
  ```

## Source layout

| Folder | Contents |
|---|---|
| `common/` | engine core: console, cvars, commands, file system, collision, player movement, messages, network channel |
| `server/` | the server: hosting games, entity updates, client connections |
| `game/` | game logic: player, weapons, items, physics, triggers, monsters, save games |
| `client/` | the client: input, prediction, effects, screen, menus, sound, downloads |
| `client/refresh/` | the renderers (`gl1`, `gl3`) and their shared loaders (`files`) |
| `backends/` | the platform layer: the system, networking, and `sdl.py` (SDL 2's calls, done with pyglet) |
| `tests/` | unit tests, engine tests, and the C comparison harnesses |
| `scripts/` | tools used while porting |
| `docs/` | plans and notes |
| `yquake2/` | a checkout of Yamagi Quake II, the reference for behaviour (not tracked) |
| `quake2-original/` | id Software's 3.21 C source (not tracked) |

`AGENTS.md` has the coding conventions.

## License

The code is licensed under the GNU General Public License (see `gnu.txt`).
You should read the whole license, but in short: you can do anything you want
with the code, including sell your own version, but if you distribute
binaries you must make the full source code freely available.

The Quake II data files are still copyrighted and licensed under their
original terms. You cannot redistribute data from the original game, but you
can build a standalone game on this code if you make a true total conversion.
