# Conventions for the `pythonic` branch

This repository is a Quake II engine in Python with the features of Yamagi
Quake II. It started as a line-by-line port of the C. On this branch it is
being reworked into ordinary, idiomatic Python, one step at a time. The plan
and the order of the steps are in `docs/pythonic_plan.md`. Read it before
starting a step.

## The two rules that don't change

1. **External interfaces stay the same.** These are:
   - the network protocol (34, as Yamagi);
   - game data and map formats, and map entity keys and class names;
   - save games;
   - demos;
   - console commands, cvar names and flags, binds and config files;
   - the command line;
   - the files the game writes;
   - what the player sees and hears.

   The full list is in the plan. Before reworking code behind one of
   them, make sure a test covers it.
2. **The game keeps working after every step.** Rework in steps small
   enough that the tests pass at the end of each.

Everything else may change: module layout, names, data structures, internal
APIs and algorithms.

## Workflow

1. Pick the next step from `docs/pythonic_plan.md`.
2. Make sure tests cover the behaviour you are about to change. Add unit
   tests first where they are missing.
3. Rework the code.
   - **Rework whole units:** convert a module or subsystem completely,
     rather than leaving a file half C-style and half PEP 8.
   - **Callers:** update every caller in the same change.
   - **Unconverted code you only touch:** match its existing style; leave
     the reformatting for its own step.
4. **Run the tests:**
   - `env/bin/python -m pytest tests/unit`, always;
   - `tests/run_all.sh` and `tests/harness/run.sh`, when the game data is
     available;
   - `timedemo` (`+demomap demo1.dm2 +timedemo 1`) for anything in a frame
     path. It must not get slower.
5. Update the plan's progress, and these conventions if they change.

To check behaviour, use Yamagi's C in `yquake2/src/` (pinned at
`4e2ad5e7`); id's 3.21 source in `quake2-original/` is history only. Port
Yamagi features and fixes by understanding the C change and writing it the
Python way, not by translating it line by line.

## Style

- **PEP 8:**
  - four spaces;
  - `snake_case` for functions, methods, variables and modules;
  - `CapWords` for classes;
  - `UPPER_CASE` for constants.

  Format and lint with ruff (set up in `pyproject.toml`).
- **Python 3.12:** every file has type hints on its functions and public
  attributes, checked with pyright or mypy. `from __future__ import
  annotations` is not needed.
- **Names:** say what a thing is. Drop C prefixes and abbreviations
  (`CL_`, `SV_`, `GL3_`, `Mod_`, `R_`, `vec3_t`, `_t`) where a module or
  class name already gives the context. Names stay where they are part of an
  external interface: console commands, cvars, entity class names, and the
  names stored in save games.
- **Imports:**
  - absolute imports, grouped as standard library, third party, then
    project;
  - `from package import module`, and `from module import Name` for
    classes and functions, are both fine;
  - no `import *`.
- **Comments and docstrings:**
  - explain why, and the Quake II behaviour being kept (e.g. "Quake II rounds
    toward zero here, demos depend on it");
  - reworked code drops the C type comments, pasted C blocks, `Q2PORT` and
    banner comments.

## Data and state

- **Structs:** `@dataclass(slots=True)` for plain data.
  - Classes with behaviour are ordinary classes.
  - Use properties only where they make an API clearer.
- **Constants:** `Enum`, `IntEnum` and `IntFlag` for named constants and bit
  flags. An `IntEnum` or `IntFlag` is fine where the value goes over the
  network or into a file.
- **numpy:** for geometry, vertices, pixels, lightmaps and other bulk
  numbers. Plain Python for small or irregular data.
- **No global state where it can be avoided.**
  - State belongs to objects (`Engine`, `Server`, `Client`, a renderer, a
    `FileSystem`) and is passed in explicitly.
  - Module-level constants and pure functions are fine.
  - Where a process-wide singleton is truly needed (the window system),
    say so in a comment.
- **Function results:** return values, or small dataclasses, instead of
  output parameters.
- **Repetition:** fold repetitive code into tables, loops or helpers. This
  covers the read/write pairs, per-type loaders, and frame tables.
- **Byte order:** on-disk and network formats use `struct` or numpy dtypes
  with explicit byte order: `<` for files, network order where the protocol
  uses it.

## Errors and output

- **Engine errors:** exceptions, not return codes.
  - The engine's error types (drop to console, fatal) are caught at the
    frame loop.
  - Catch specific exceptions; never use a bare `except`.
- **Console output:** the engine's console printing, so it reaches the
  console, the log and `condump`. No `print` in the engine, except
  temporary tracing that is removed before the change is finished.
- **`q2data`:** never prints. It raises its own exceptions (e.g.
  `q2data.FormatError`) and leaves reporting to the caller.

## The `q2data` package

The self-contained loading library (step 1 of the plan).

- **Dependencies:** only numpy and Pillow. It never imports the engine,
  pyglet or OpenGL, and has no global state.
- **Input:** bytes, paths, or a `q2data` `FileSystem`.
- **Output:** dataclasses with numpy arrays.
- **Writers:** each format has one, where tests need it to build fixtures.
- **Engine-only structures** (collision trees, GPU buffers, texture
  caches) belong in the engine, built from `q2data` objects.

## Tests

- **Unit tests** go in `tests/unit/` and run with `pytest`
  (`env/bin/python -m pytest tests/unit`).
  - They must never read the proprietary game data, nor depend on
    `quake2data` being present.
  - They build their fixtures in code with the `q2data` writers: tiny
    maps, models, images, archives and sounds.
  - No window or OpenGL context is needed. Test renderer logic without GL.
- **Engine tests** (`tests/run_all.sh`) and the C harnesses
  (`tests/harness/`) use the real data. They skip when it is missing.
- **When behaviour changes on purpose**, say so in the plan and update the
  tests in the same change.

## Dependencies

- **Runtime:** in `requirements.txt` (pyglet, PyOpenGL, numpy, Pillow,
  pycurl). Sound needs `libopenal.so.1`, and OGG music needs FFmpeg's
  libraries, which pyglet loads.
- **Development:** in `requirements-dev.txt` (pytest).
- The port stays pure Python, with no compiled extensions or build step.
- **Speed:** try numpy or a better algorithm first. Measure before
  optimising.

## Game data

- The game data in `/home/tim/dev/quake2data/Data` is only for running the
  game and the engine tests: `env/bin/python main.py -datadir
  /home/tim/dev/quake2data/Data`.
- It is proprietary. Never copy it, or anything derived from it, into the
  repository or into test fixtures.
- To drive the game from a script, set `Q2STDIN=1` and pipe console
  commands in on stdin, one per line.

## Commits

- Commit messages are short and plain: "Porting" for routine progress,
  otherwise name what changed (e.g. "q2data BSP loader").

## History: the C-port conventions

Code that hasn't been reworked yet still follows the earlier rules, which
help when reading it:
- one `.py` file per Yamagi `.c` file, at the same path;
- C names, order and globals;
- tabs;
- C types in comments;
- unported C kept in `"""` blocks;
- port-only changes marked `Q2PORT`.

The module import names in that code (`shared`, `shared_c`, `common_h`,
`sound_c`, ...) always mean the same C file. `scripts/yq_*.py` and
`docs/yquake2_plan.md` document that work. Don't add new code in that style.
