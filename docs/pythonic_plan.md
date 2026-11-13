# Pythonic branch plan

The `pythonic` branch drops the rule that the port mirrors the C code. Its
structure, names and variables become ordinary, idiomatic Python. What the
player and other programs see stays the same. The branch keeps Yamagi's
features (mostly), but not Yamagi's approach.

The work is done step by step: the game stays runnable, and the tests pass,
after every step.

## Fixed: external interfaces

These must not change. Each one needs a test before the code behind it is
reworked.

| Interface | What has to keep working |
|---|---|
| Network | Protocol 34 with Yamagi's messages: play against Yamagi and other C clients and servers. HTTP downloads (`dlserver`, the `.filelist` quirks). |
| Game data | `baseq2` and mod directories, `pak*.pak` and `.pk3` files, every file format the game reads. |
| Map entities | Entity keys (`classname`, `target`, `spawnflags`, ...) and every spawnable class name. |
| Save games | Yamagi's save format. It stores struct layouts and callbacks by their C function names (`savegame/tables/`). These become explicit name tables, so Python names can change without breaking saves. |
| Demos | `.dm2` recording and playback. |
| Console | Cvar names, values and flags, console commands, key binds, `config.cfg`/`autoexec.cfg`, the command line (`+set`, `+map`, ...). |
| Output files | Screenshots (`scrnshot/`), `condump`, save and config paths. |
| User interface | Menus, HUD, console, and what each renderer draws. |

Free to change: module layout, names, data structures, internal APIs, the
renderer and game interfaces between modules, and anything else inside the
process.

## Style

- **PEP 8:** spaces, snake_case functions and variables, CapWords classes,
  `UPPER_CASE` constants. A formatter and linter (ruff) are set up in step 0.
- **Python 3.12 or later:** type hints throughout, checked by pyright or mypy
  on the new code.
- **Data:** `@dataclass(slots=True)` and `Enum`/`IntEnum`/`IntFlag` for data;
  numpy arrays for geometry and pixels; plain classes for objects with
  behaviour.
- **No global state where it can be avoided:** state belongs to objects that
  are passed in or reached through one context object (see Architecture).
  Module-level constants are fine.
- **No C leftovers:** no C type comments, no pasted C, no `Q2PORT` markers in
  reworked code. A comment says why, not which C line this was.
- **Repetitive code:** fold it into tables, helpers or loops. Examples are the
  duplicated gl1/gl3 loaders, the frame tables of the monster files, and the
  hand-written `MSG_Read*`/`MSG_Write*` pairs.
- **Errors:** engine errors stay engine errors (`Com_Error` becomes
  exceptions with clear types, e.g. `DropError` and `FatalError`, caught at the
  frame loop as `abortframe` is today). The loading library raises its own
  exceptions and never prints.

`AGENTS.md` is rewritten for these rules in step 0. The C-port rules move to
a short historical note.

## Architecture

### `q2data`: the loading library (self-contained)

A package at the repository root. It reads Quake II data and returns plain
Python objects, and it can be used outside the engine (tools, notebooks,
viewers, converters).

- **Dependencies:** only numpy and Pillow. No pyglet, OpenGL, engine imports,
  cvars, console output or global state.
- **Input:** bytes, paths, or a `FileSystem` object; never the engine's
  filesystem directly.
- **Contents:**
  - `filesystem`: search paths, `.pak` and `.pk3` archives, and mod
    directories, as a `FileSystem` object with `open`, `read`, `exists` and
    `list`. It replaces the lookup half of `common/filesystem.py`.
  - `bsp`: one BSP loader giving every lump (planes, nodes, leafs, brushes,
    faces, texinfo, visibility, lighting, areas, models, entity string) as
    dataclasses with numpy arrays. It replaces the three loaders today: in
    `common/collision.py`, `gl1_model.py` and `gl3_model.py`.
  - `entities`: parsing the entity string.
  - `md2`, `sp2`: alias and sprite models.
  - `images`: PCX, WAL, TGA, PNG and JPG, palettes (`colormap.pcx`), and the
    quit-screen fix.
  - `sound`: WAV headers and samples, and OGG via the existing decoder.
  - `cinematic`: `.cin` files (the Huffman decoder from `cl_cin.py`).
  - `demo`: reading `.dm2` blocks.
- **Writers:** small builders for test fixtures (see Testing). They write
  BSP, MD2, PCX, WAL, PAK and WAV from Python objects.

The engine adds what only the engine needs on top of `q2data`: collision
trees, GPU buffers, texture caches, and sound buffers.

### The engine

The existing packages (`common`, `server`, `client`, `game`, `backends`) stay
where they are while they are reworked, so each step is a small diff. The
final package layout is decided at the end (step 9).

- **Context objects instead of module globals:**
  - an `Engine`, holding the cvars, commands, console, `FileSystem`, timers,
    and the server and client;
  - `Server` and `Client` objects, holding today's `sv`/`svs` and
    `cl`/`cls`;
  - each `Renderer` as an object (see below).

  A few process-wide singletons can stay where they are truly global, such
  as the SDL/pyglet window system. Each such case is named in the code.
- **Renderers:**
  - a `Renderer` protocol replaces the `re`/`ri` function tables;
  - `gl1` and `gl3` are classes implementing it;
  - code both share moves to a common base: model and image management,
    lightmap building, sky, culling, and the 2D draw logic.
- **Game:**
  - The game talks to the server through a `GameImports`/`GameExports`
    pair of objects, not module globals.
  - The monster files become data: frame tables, and moves as dataclasses.
    Behaviour must stay identical; see Testing.
- **Messages:**
  - One table-driven description of entity and player-state deltas, used
    by both reading and writing. It replaces the hand-written pairs.
  - What goes over the wire stays byte for byte the same.

## Testing

There are three tiers. Only the first runs everywhere.

1. **Unit tests (`pytest`, in `tests/unit/`):**
   - **No proprietary data:** they never use `quake2data` or any id file.
     They make their own fixtures in code with the `q2data` writers: a
     tiny two-room BSP, a cube MD2, a 4×4 PCX/WAL, a PAK with a few files,
     and a short WAV.
   - **Round trips:** where a writer exists, test load → save → load.
   - **No window or GL:** renderer tests cover only the logic without GL,
     such as lightmap building and culling.
   - **Engine pieces too:** message reading and writing (encode/decode
     round trips, known byte strings for the protocol), netchan sequencing,
     cvars and commands, `pmove` and collision against the fixture BSP,
     save-game field tables.
   - **Setup:** pytest is a development dependency (`requirements-dev.txt`;
     run with `env/bin/python -m pytest`).
2. **Engine integration tests (`tests/run_all.sh`, existing):**
   - **Data:** they use the real game data, and are skipped when
     `quake2data` is missing.
   - **Coverage:** they check whole-game behaviour (maps, monsters,
     save/load, demos, menus, renderer restart, a dedicated server).
3. **C reference harnesses (`tests/harness/`, existing):**
   - **The oracle:** collision and player movement are compared with
     Yamagi's C, line for line.
   - **When they run:** while collision and `pmove` are reworked. They
     also need the game data.

**Gates for each step:** unit tests pass; the integration tests and
harnesses pass when the data is available; `timedemo` is no slower. Each
interface in the table above gets an integration or unit test before the
code behind it changes, e.g. a protocol capture test, and loading a save
made before the step.

## Steps

Each step ends with the game running and the gates passing.

0. **Groundwork**
   - Rewrite `AGENTS.md` for this branch.
   - Add `pyproject.toml` (pytest and ruff settings) and `tests/unit/`.
   - Remove id leftovers, each file confirmed first: `ref_gl/`,
     `ref_soft/`, `qcommon/`, `linux/`, the DLLs and `quake2.exe`, and
     scratch files in the root.
   - Drop the unused `linux.cd_linux` imports.
1. **`q2data` formats**
   - Write the package (filesystem, BSP, entities, MD2, SP2, images,
     sound, cinematic, demo) with writers and unit tests.
   - The engine doesn't use it yet. Test it against the current loaders on
     the real data, where that's available, so both give the same results.
2. **Engine on `q2data`**, one consumer at a time:
   - the filesystem;
   - collision (`CM_LoadMap`);
   - gl3's models;
   - gl1's models;
   - images and skins;
   - sound files;
   - cinematics.

   After this step the three BSP loaders are one, and `common/header/files.py`
   is gone.
3. **Common core**
   - Cvars, commands, the command buffer, the console and the frame loop
     go into the `Engine` object.
   - Errors become exceptions.
   - Table-driven messages; netchan.
4. **Renderers**
   - The `Renderer` protocol, and the gl1 and gl3 classes with a shared
     base.
   - Vid and the window layer.
5. **Sound**
   - OpenAL and OGG as objects. Channels and the playsound lists become
     plain data.
6. **Server**
   - A `Server` object; connectionless commands as a dispatch table;
     entity snapshots.
7. **Client**
   - A `Client` object; parsing, prediction, effects, screen, menus,
     input and downloads.
8. **Game**
   - The `GameImports`/`GameExports` objects.
   - Player and weapons; then items, triggers and targets; then the
     monsters (data-driven); then save games (with the name tables).
9. **Final layout and packaging**
   - Settle the package layout and entry points (`python -m quake2`).
   - Make `q2data` installable on its own.
   - Clean up the docs.

Steps 1–2 come first because they deliver the reusable loading library and
remove the most duplication. Steps 3–8 can overlap, but each step's changes
should land together.

## Progress

- [x] **0. Groundwork:**
    - `AGENTS.md` and `readme.md` are rewritten for this branch.
    - `pyproject.toml` has the pytest and ruff settings; ruff skips code
      not yet reworked.
    - pytest and ruff are in `requirements-dev.txt`, and `tests/unit/`
      exists.
    - `tests/run_all.sh` runs pytest and skips the game tests without the
      game data; `tests/harness/run.sh` skips without it too.
    - The unused `linux.cd_linux` imports are gone.
    - **id leftovers deleted:**
      - tracked: `ref_soft/`, `linux/`, `qcommon/`, `null/`, `ctf/`,
        `test.py`, id's release notes and `joystick.txt`;
      - untracked: id's binaries, build output and scratch files.
    - `gl.md` is now `docs/gl3_notes.md`.
- [x] **1. `q2data` formats:**
  - **Modules:** `q2data/` has `pak` (PAK, and zip-based PK3/PK2/PKZ/ZIP),
    `filesystem` (Yamagi's search order and protected paks), `bsp` (every
    lump as numpy records, `Visibility` decompression, a writer),
    `entities`, `md2`, `sp2`, `images`, `wav`, `cinematic` and `demo`.
    - `images` reads every PCX variant Yamagi reads, plus WAL, M8, M32,
      and TGA/PNG/JPG/BMP through Pillow.
    - `cinematic` has the table-driven Huffman decoder, and an encoder for
      tests.
  - **Unit tests:** 71 tests in `tests/unit/`, run in under 2 seconds. The
    fixtures are built in code: `tests/unit/builders.py` makes a closed
    box-room BSP (tree, brushes, faces, visibility), a cube MD2, patterned
    images and sounds.
  - **Checked against the real data** (not in the repository tests):
    - every one of the 3,285 game files of each type loads;
    - every PCX gives the same pixels and palette as the engine's decoder;
    - every WAV header matches the engine's `GetWavinfo`;
    - every frame of `idlog.cin` and `end.cin` matches the engine's
      Huffman decoder.
- [x] **2. Engine on `q2data`:** every file format is now parsed by
  `q2data`, and id's `common/header/files.py` is deleted.
  - **What switched:**
    - **Cinematics:** `cl_cin.py` uses `HuffmanTables`; the
      hand-written tree code is gone.
    - **Sound:** `wave.py` is a small adapter over `q2data.wav`.
    - **Images:**
      - `files/pcx.py`, `wal.py` and `stb.py` use `q2data.images` (PCX,
        WAL, M8, M32, TGA/PNG/JPG);
      - the client's second PCX decoder (`cl_image.py`) is gone.
    - **Models:** `files/models.py` parses MD2 and SP2 with `q2data`. The
      engine's model containers (`dmdl_t`, `dsprite_t`, ...) now live
      there, without file parsing.
    - **Maps:** collision (`CM_LoadMap`) and both renderers'
      `Mod_LoadBrushModel` read the header and every lump through
      `q2data.bsp`. The renderers' loaders get their records from
      `files/models.lump_rows`, which keeps the C field names until the
      renderer step renames them. Visibility is a `q2data.bsp.Visibility`.
    - **Packs:** `common/filesystem.py` reads PAK and PK3 archives through
      `q2data.pak`. The engine's search path, handles and listings stay
      for step 3.
    - **Downloads:** `cl_download.py` reads MD2 headers with
      `q2data.md2.read_header`.
  - **Checked:**
    - **Screenshots:** gl1 and gl3 frames are pixel-identical to the code
      before step 2, on base1, base2 and bunk1. This used fixed frame
      times (`fixedtime`) and a frozen camera; the gl3 driver is a gl3
      copy of `tests/_refshot.py`.
    - **Collision:** the full collision state of all 39 maps is
      identical.
    - **Models:** every MD2 and SP2 loads to identical engine structures.
    - **Tests:** the harnesses and the test suite pass.
    - **Speed:** `timedemo` is unchanged (about 42 fps on both, under
      load), and loading the collision data for all maps is about 12%
      faster.
  - **Small behaviour changes:**
    - **PCX:** reads follow Yamagi, without id's 640×480 limit.
      True-colour PCX files are still refused where the renderers expect
      8-bit images.
    - **Damaged WAV:** if one can't be read, the sound isn't loaded,
      instead of half its header being used.
    - **Pack members:** opening one reads it whole into memory, so a
      read can't run past its end.
    - **PK3:** directory entries are no longer counted as files.
    - **Downloads:** a truncated MD2 is skipped when checking skins to
      download, instead of having names read from past its end.
    - **Leaf brushes:** collision reads leaf brush numbers unsigned, as
      the C's `unsigned short`.
- [ ] **3. Common core** (in progress):
  - **Done, table-driven messages:** new PEP 8 modules
    `common/entity_delta.py`, `player_delta.py` and `usercmd_delta.py`.
    - **What they replace:** each has one table of fields (bits, wire
      encodings, scales) that drives the bit computation, sizing, writing
      and reading. They replace the hand-written pairs:
      - `DeltaEntityBits`, `MSG_DeltaEntity_Size`, `MSG_WriteDeltaEntity`
        / `CL_ParseEntityBits`, `CL_ParseDelta`;
      - `SV_WritePlayerstateToClient` / `CL_ParsePlayerstate` (now thin
        callers);
      - `MSG_WriteDeltaUsercmd` / `MSG_ReadDeltaUsercmd`.
    - **Checked against the old code** on random states (20,000 entity,
      5,000 player state and 5,000 user command cases, including
      truncated messages): identical update bits, sizes, bytes, decoded
      states and read positions.
    - **Unit tests:** 26 new ones; the screenshots stay pixel-identical,
      the demo plays, and a client plays on a dedicated server over UDP.
  - **Done, cvars:** `common/cvars.py` has `CvarRegistry`.
    - **Behaviour:** it holds every cvar with Yamagi's rules: renamed old
      names, info validation, write protection, latching, `game` as "" for
      the base game, and the `set`/`cvarlist`/`inc`/`dec`/`reset`/
      `resetall`/`toggle` commands, which take their arguments as a list.
    - **Dependencies:** it reaches the engine only through injected
      callbacks (print, server running, game changed). So 34 unit tests
      cover it without the engine.
    - **Old functions:** `common/cvar.py` is now a thin layer: the old
      `Cvar_*` functions call the engine's one registry
      (`cvar.registry`), until the ~500 call sites move to it.
    - **Checked:**
      - `config.cfg` written after start-up, a `set ... a` and an old
        name (`gl_mode`) is identical to the code before (239 lines);
      - the test suite passes.
    - **When comparing such runs:** the engine adds the directory of
      `main.py` to its search path. Run with the same `main.py`
      location, or the repository's untracked `baseq2/` (with its own
      `config.cfg`) changes the results.
  - **Done, commands:** `common/commands.py` has `CommandSystem`, following
    Yamagi's `cmdparser.c`.
    - **What it covers:** the command buffer, splitting at newlines and
      unquoted semicolons, tokenising with `$cvar` expansion, aliases
      (with the loop guard), dispatch (command, alias, cvar, else the
      server), `wait`, `exec`, `vstr`, `echo`, `cmdlist`, and completion.
    - **The old functions:** `common/cmdparser.py` is a thin layer like
      `cvar.py`. It also keeps the command-line handling (`+set`, `+map`)
      and map name completion.
    - **Taken from Yamagi:**
      - the 32 KB buffer (the port had 8 KB);
      - new aliases listed first;
      - whitespace in tokens is any character up to space.
    - **Fix:** script files are decoded as Latin-1, as the C treats them as
      bytes; the port raised an error on any non-ASCII byte.
    - **Checked:** 21 unit tests; `config.cfg` (with an alias run and a
      bind) is identical to the code before; the test suite passes.
  - **Done, the engine object:** `common/engine.py` has `Engine`.
    - **What it is:** it builds the cvars and the commands and wires them
      to each other, with an `EngineHooks` for the parts not yet reworked.
    - **For now:** `engine.engine` is the process's one engine, which
      `cvar.registry` and `cmdparser.commands` point at.
    - **Unit tests:** they make their own engines.
  - **Left:**
    - the console and the frame loop into the `Engine`;
    - the module globals' callers taking the engine (or its subsystems)
      directly;
    - errors as exceptions;
    - the engine file system on `q2data.filesystem`;
    - netchan.
- [ ] 4. Renderers
- [ ] 5. Sound
- [ ] 6. Server
- [ ] 7. Client
- [ ] 8. Game
- [ ] 9. Final layout and packaging

## Following Yamagi

- **What we take from upstream:** Yamagi's features and bug fixes, by
  hand: read the C change, then write the Python way.
- **What is no longer needed:** the function-level tracking scripts
  (`scripts/yq_*.py`) and `docs/yquake2_plan.md`. They stay as history.
- **Upstream's version:** the `yquake2/` checkout (pinned at `4e2ad5e7`)
  stays as the reference for behaviour.

## Risks

- **Gameplay drift:** reworking the game and monster code can change
  behaviour in small ways. The checks against it are `monster_all`,
  `state_trace`, the harnesses, and comparing traces before and after each
  game step.
- **Save compatibility:** saves store C struct layouts and function names.
  The name tables have to be complete before game names change. Test with
  saves made on the current code.
- **Performance:** objects and attribute access can be slower than module
  globals in hot loops. Measure with `timedemo` and fix the hot spots
  (numpy, local variables) rather than keeping globals.
- **Size:** about 133,000 lines; game 48k, client 59k, common 16k, server
  7k. Steps 7 and 8 are the largest. They may need splitting further when
  reached.
