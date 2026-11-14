# Quake II in Python

A port of the id Software Quake II engine (version 3.21) from C to Python. It
follows the original source closely: each `.c` file maps to a `.py` file with
the same path, and functions keep their names, order and global variables, so
the port can be compared with the C line by line. The renderer is the OpenGL
one (`ref_gl`), and the platform layer uses pygame for the window, input and
sound.

This is the Quake2 game engine without the maps, textures and models which are 
proprietary. If you purchase the official game, it includes the
quake2data asset folder and the game can be played normally using that. 
Alternatively, you can try running independently created maps but they mostly 
rely on the base games textures.

About 5% of the code was ported by hand; the rest was ported with the
help of ChatGPT, Claude and qwen.

## This branch: the port of id's original source

The `original` branch is the first stage of the port. It follows id
Software's Quake II 3.21 C source, as released in 2001, with none of the
later fixes made by the source ports:

- **Layout:** id's tree, file for file: `qcommon/cmodel.c` becomes
  `qcommon/cmodel.py`, `ref_gl/gl_rmain.c` becomes `ref_gl/gl_rmain.py`.
  A header whose name would clash with its `.c` file gets an `_h` suffix
  (`gl_model.h` becomes `ref_gl/gl_model_h.py`).
- **Code:** C names, function order and global variables, with the C's
  types in comments, so the Python can be read side by side with the C.
- **Behaviour:** id's, bugs included, except where a `Q2PORT` comment marks
  a change made only in the port.

It is kept to show the port as a direct translation of id's code. For
Yamagi's fixes and features, or for the engine as ordinary Python, see the
branches below.

## Other branches

This ports based on this branch:

| Branch | What it is | Use it to |
|---|---|---|
| [`yquake2`](https://github.com/TimSC/python-quake2/tree/yquake2) | the port moved to [Yamagi Quake II](https://github.com/yquake2/yquake2)'s C source, with its bug fixes and features (the OpenGL 3 renderer, OGG music, HTTP downloads, IPv6), still structured like the C | compare the Python with Yamagi's C: each C file has a Python file at the same path, with the same functions in the same order |
| [`pythonic`](https://github.com/TimSC/python-quake2/tree/pythonic) | a rewrite of the `yquake2` branch into ordinary Python: PEP 8, type hints, objects instead of globals, and `q2data`, a separate library for reading Quake II data | read or build on the engine as Python, without the C structure |

The later branches use pyglet and OpenAL in place of pygame.

## Status

- The single player game runs: maps load, monsters fight, items, doors, lifts
  and triggers work.
- All of the game's monsters are ported, including the bosses.
- The client can connect to a C Quake II server (tested against Yamagi Quake II
  8.30).
- A Python dedicated server runs and takes console commands from the terminal.
- Demos play back, and `timedemo` reports frame rates.
- Expect bugs: the port is still being tested level by level.

Not ported, or out of scope for now:

- the software renderer (`ref_soft`), the Capture the Flag mod (`ctf`), and
  platforms other than Linux (`win32`, `irix`, `solaris`)
- the C sound mixer (pygame does the playback) and CD audio

## Requirements

- Python 3 (developed and tested with 3.12)
- The packages in `requirements.txt`: pygame, PyOpenGL, numpy and Pillow.
- The Quake II game data (`baseq2/pak0.pak` and so on), from a copy of the
  game you own. It is not included.

## Setup

```
pip3 install -r requirements.txt
```

## Running

Point `basedir` at the folder that contains `baseq2`:

```
python3 main.py +set basedir /path/to/quake2data/Data
```

Commands after `+` run at startup, as in the original game. For example, to
start a map at a chosen skill (0 to 3):

```
python3 main.py +set basedir /path/to/quake2data/Data +skill 1 +map base1
```

To measure performance on a demo:

```
python3 main.py +set basedir /path/to/quake2data/Data +demomap demo1.dm2 +timedemo 1
```

PyOpenGL checks for an OpenGL error (`glGetError`) after every OpenGL call by
default. That is useful for catching rendering bugs but costs performance. Set
`PYOPENGL_ERROR_CHECKING=0` to turn it off; it is on by default, and setting it
to `1`/`true` leaves it on.

### Dedicated server

```
python3 main.py +set basedir /path/to/quake2data/Data +set dedicated 1 +map base1
```

Type server commands such as `status`, `serverinfo` or `map base2` into the
terminal.

### Terminal commands in the windowed game

The windowed game ignores the terminal, as the original does. Set
`Q2STDIN=1` to have it read commands from the terminal as well. Commands can
also be piped in, which is useful for scripted tests:

```
Q2STDIN=1 python3 main.py +set basedir /path/to/quake2data/Data +map base1
```

## Source layout

| Folder | Contents |
|---|---|
| `client/` | client: input, prediction, effects, menus, console, sound |
| `server/` | server: game hosting, networking, entity updates |
| `game/` | game logic: monsters, weapons, items, physics, triggers |
| `qcommon/` | shared code: collision, player movement, file system, network channel |
| `ref_gl/` | OpenGL renderer |
| `linux/` | platform layer, using pygame for video, input and sound |

## Porting conventions

- Keep the 1:1 file mapping and the original function names and order.
- Favour closeness to the C over idiomatic Python, so the two can be compared.
- C code that is not yet ported stays in triple-quoted blocks next to the
  Python. Code that is disabled in the C (`#if 0`) stays disabled.
- Changes that only exist in the port are marked with `Q2PORT` comments.

`AGENTS.md` has the full set of conventions.

## License

The code is licensed under the GNU General Public License (see `gnu.txt`).
You should read the whole license, but in short: you can do anything you want
with the code, including sell your own version, but if you distribute
binaries you must make the full source code freely available.

The Quake II data files are still copyrighted and licensed under their
original terms. You cannot redistribute data from the original game, but you
can build a standalone game on this code if you make a true total conversion.
