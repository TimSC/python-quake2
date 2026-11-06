# Plan: moving the port to Yamagi Quake II

This is the plan for the `yquake2` branch. It moves the Python port from id
Software's Quake II 3.21 source to [Yamagi Quake II](https://github.com/yquake2/yquake2),
and tracks the work group by group.

## Decisions

| Topic | Decision |
|---|---|
| Reference | Yamagi's source in `yquake2/` (git `4e2ad5e7`, version 8.71pre). Pin this commit for the whole move, so every group ports the same code. |
| Layout | Mirror Yamagi's `src/` tree exactly. `yquake2/src/<path>.c` becomes `<path>.py`, and `yquake2/src/<path>/header/<name>.h` becomes `<path>/header/<name>.py`. |
| Names and order | Follow Yamagi: function names, function order and globals, as the port did with id's code. |
| Behaviour | Take both Yamagi's bug fixes and its gameplay changes. |
| Network | Follow Yamagi's protocol. Today this is the same Quake II protocol 34 with the same messages, so the port can still play with Yamagi and other C servers and clients. |
| `quake2-original/` | Keep unmodified as a historical reference. |
| `yquake2/` | A separate git checkout, ignored by this repository (`.gitignore`). |

## Scope

**In scope:** everything the port runs today, re-based on Yamagi:

- `src/common/`: shared code, including `common/shared/`.
- `src/server/`.
- `src/game/`: the single player and deathmatch game.
- `src/client/`: the client, menus and sound.
- `src/client/refresh/gl1/` and `src/client/refresh/files/`: the OpenGL 1 renderer and its shared loaders.
- The SDL 2 platform code, with pygame (which is built on SDL 2) standing in for SDL:
  - `src/client/vid/glimp_sdl2.c`, `src/client/input/sdl2.c`;
  - `src/backends/unix/` and `src/backends/generic/`.

**Not ported, at least for now:**

| Yamagi code | Why |
|---|---|
| `client/refresh/soft/`, `client/refresh/gl3/`, Vulkan | Other renderers. GL3 is a candidate for a later "modern OpenGL" step. |
| `glimp_sdl3.c`, `input/sdl3.c` | pygame uses SDL 2. |
| `backends/windows/` | Linux only, as before. |
| `client/sound/openal.c`, `qal.c` | OpenAL back end. pygame does the playback. |
| The `curl` HTTP downloader | Optional; later if needed. |
| Gyro and gamepad extras in `client/input/` | Later. |

Yamagi builds the game as a separate library and loads it with
`GetGameAPI`. The port keeps importing the game module directly, marked
`Q2PORT`.

## How each group is done

Each group in the table below goes through the same steps, and the game must
run and pass the tests at the end of each one.

1. **Move.** Move or split the Python functions into the files Yamagi uses,
   with the same order, and fix all imports. No logic changes in this step.
2. **Diff.** For every function in the group, compare id's version with
   Yamagi's after removing noise: formatting, braces, comments, renamed
   locals, and the `if (!self) { return; }` null guards Yamagi adds to most
   game functions. Use Yamagi's `CHANGELOG` and commit messages to understand
   why each change was made.
3. **Port.** Bring each function to Yamagi's version. Keep the port's own
   changes, marked `Q2PORT`:
   - the pygame and numpy code;
   - the Pillow PCX decoding;
   - the speed-ups;
   - fixes for bugs that only exist in the port.
4. **Test.** Run the group's tests, then the full set, and check the group
   off below.

C that isn't ported yet stays in `"""` blocks, as before. From now on it's
Yamagi's C, not id's.

## Groups

The order follows dependencies: each group only depends on groups above it.

| # | Group | Yamagi files | Current Python files | Kind of change | Tests |
|---|---|---|---|---|---|
| 0 | Tooling and conventions | n/a | n/a | New tools; update `AGENTS.md`; move tests into the repo | Tools produce the function map and diffs |
| 1 | Shared code | `common/shared/shared.c`, `flash.c`, `rand.c`, `common/header/*.h` | `game/q_shared.py`, `game/m_flash.py`, `qcommon/qcommon.py`, `qcommon/qfiles.py` | Renames, new `rand.c` | Everything imports and runs |
| 2 | Common engine code | `common/cmdparser.c`, `cvar.c`, `filesystem.c`, `zone.c`, `szone.c`, `movemsg.c`, `argproc.c`, `clientserver.c`, `frame.c`, `crc.c`, `md4.c`, `glob.c` | `qcommon/cmd.py`, `cvar.py`, `files.py`, `common.py`, `crc.py`, `md4.py`, `linux/glob.py` | `common.py` splits into several files | Startup, map load, dedicated server commands |
| 3 | Collision and player movement | `common/collision.c`, `common/pmove.c` | `qcommon/cmodel.py`, `qcommon/pmove.py` | Mostly 1:1 | C harnesses rebuilt against Yamagi's `collision.c` and `pmove.c`; random traces and moves must match exactly |
| 4 | Network channel and server | `common/netchan.c`, `server/*.c` | `qcommon/net_chan.py`, `server/*.py`, `linux/net_udp.py` | `sv_ccmds` → `sv_cmd` + `sv_save`, `sv_main` → `sv_main` + `sv_conless`, `sv_ents` → `sv_entities` | Dedicated server; fake UDP clients; play against a Yamagi client |
| 5 | Game: core and physics | `game/g_main.c`, `g_utils.c`, `g_spawn.c`, `g_phys.c`, `g_combat.c`, `g_svcmds.c`, `g_chase.c`, `game/header/*.h` | `game/g_*.py`, `game/game.py`, `game/g_local.py` | Mostly 1:1 | Maps load and run; walk and fall tests |
| 6 | Game: player, weapons and items | `game/player/*.c`, `g_items.c`, `g_weapon.c`, `g_cmds.c` | `game/p_*.py`, `g_items.py`, `g_weapon.py`, `g_cmds.py` | `p_*` → `player/` | Blaster test, pickups, death and respawn |
| 7 | Game: doors, triggers, targets, misc | `g_func.c`, `g_trigger.c`, `g_target.c`, `g_misc.c`, `g_turret.c` | same names | 1:1 | Doors, lifts, triggers on base1 to base3 |
| 8 | Game: monsters and AI | `g_ai.c`, `g_monster.c`, `game/monster/**` | `g_ai.py`, `g_monster.py`, `m_*.py` | `m_*` → `monster/<name>/<name>`; `m_actor` is gone in Yamagi | All-monster exercise; maps with each monster |
| 9 | Game: save games | `game/savegame/` | `game/g_save.py` | Rewritten in Yamagi | Save and load on several maps |
| 10 | Client core | `client/cl_main.c`, `cl_network.c`, `cl_download.c`, `cl_parse.c`, `cl_entities.c`, `cl_prediction.c`, `cl_input.c`, `cl_keyboard.c`, `cl_console.c`, `cl_screen.c`, `cl_view.c`, `cl_inventory.c`, `cl_cin.c`, `client/header/*.h` | `client/cl_*.py`, `keys.py`, `console.py`, `client.py` | Several splits and renames | Connect, play, demos, cinematics, `timedemo` |
| 11 | Client effects | `cl_effects.c`, `cl_lights.c`, `cl_particles.c`, `cl_tempentities.c` | `cl_fx.py`, `cl_newfx.py`, `cl_tent.py` | Split differently | Screenshots of effects |
| 12 | Menus | `client/menu/menu.c`, `qmenu.c`, `videomenu.c` | `client/menu.py`, `qmenu.py`, `linux/vid_menu.py` | Moves to `client/menu/` | Every menu opens; settings apply |
| 13 | Sound | `client/sound/sound.c`, `wave.c`, `ogg.c`, `sdl.c` (structure only) | `client/snd_*.py`, `linux/snd_linux.py` | pygame stays the back end. OGG music (pygame plays OGG) would replace CD audio | Sounds, loops, sexed sounds, cinematic sound, music |
| 14 | Platform layer | `client/vid/vid.c`, `glimp_sdl2.c`, `client/input/sdl2.c`, `backends/unix/*.c`, `backends/generic/misc.c` | `linux/*.py` | Rewrite: X11/GLX → SDL (pygame) | Window, video modes, input, mouse grab, quit |
| 15 | Renderer | `client/refresh/gl1/*.c`, `client/refresh/files/*.c`, `client/refresh/ref_shared.h`, `client/vid/header/ref.h` | `ref_gl/*.py` | Rewrite: most id function names are gone, and the renderer interface changed | Screenshots match; `timedemo`; extensions off |

The current `ref_gl/` keeps the game running until group 15 replaces it.

## Group 0: tooling and conventions

- **Function map:** for every function in the port, the id file it came from
  and the Yamagi file and position it moves to. This is generated from both C
  trees by function name. Functions that are gone in Yamagi are listed for
  review.
- **Noise-filtered diff:** a script that prints, per function, id's C,
  Yamagi's C and the real difference, so each change can be reviewed and
  ported.
- **Move script:** moves Python functions between files in Yamagi's order and
  rewrites the imports across the tree, so the move step in each group is
  mechanical.
- **Tests in the repo:** move the test scripts used so far into `tests/`.
  They cover map runs, the all-monster exercise, the walking and falling
  test, the blaster test, cinematics, menu settings, the video restart and
  extensions-off runs. Add a runner that runs them all.
- **C harnesses:** keep the collision and movement harnesses (C and Python
  twins) in `tests/`, building against `yquake2/`.
- **`AGENTS.md`:** update the file-mapping rules for Yamagi's layout. Keep
  the id-specific notes as a short historical section.

## Risks and open points

- **Import cycles:** deeper packages such as `game/monster/soldier/` mean
  longer import lines. The port relies on module-level imports resolving at
  call time, and this still has to work.
- **Save games:** Yamagi's save format differs from id's. Python save games
  made before group 9 won't load afterwards.
- **Protocol:** if Yamagi changes the protocol later (for example to raise
  the entity limit), the port follows it, but that would break compatibility
  with id's original clients and servers.
- **Renderer interface:** Yamagi's `refexport_t` differs from id's. Groups 10
  and 14 have to keep working with the old `ref_gl/` until group 15.
- **SDL 2 vs 3:** Yamagi's default is now SDL 3. The port follows the SDL 2
  files, which Yamagi still supports.
- **Tests depend on game data:** the tests need the Quake II data in
  `/home/tim/dev/quake2data/Data`, which isn't in the repository.

## Findings along the way

- **Group 0:** with new seeded random inputs (`tests/harness/run.sh`),
  the Python collision and pmove code differ from id's C in a handful of
  cases, by one unit in the last printed digit (float32 against float64
  rounding). The move didn't cause this: the Python output is the same
  before and after. Group 3 must make the harnesses match exactly. The
  map checksum also differs, because id's `md4.c` uses `unsigned long`
  (8 bytes on 64-bit Linux); Yamagi's `md4.c` is 64-bit clean.

- **Group 1:** the MD4 checksum the Python port computes matches Yamagi's
  `md4.c`; the earlier mismatch was id's 64-bit bug.
- **Group 2:** Yamagi's filesystem writes to a home directory. The port
  uses `~/.yq2py` (not Yamagi's `~/.yq2`, so it doesn't replace a real
  Yamagi install's config and saves); `-cfgdir` works as in Yamagi.
  `Qcommon_Frame` stays id's until the client's `CL_Frame` (group 10) and
  the main loop (group 14) are ported.

- **Group 3:** the harnesses now build against Yamagi's `collision.c`
  and `pmove.c` (`tests/harness/run.sh`) and match exactly on base1,
  base2 and jail1. The differences came from `AngleVectors`,
  `VectorNormalize`, `VectorLength` and `pml.frametime` computing in
  double where the C uses float; they now use `np.float32` arithmetic.

- **Group 4:** `SV_CheckForSavegame` is ported but switched off
  (`SV_CHECKFORSAVEGAME_ENABLED` in `server/sv_init.py`): the game's
  `ReadLevel` (g_save.py) saves and restores only some edict fields, so
  restoring a level would empty it. Group 9 must port the save code and
  turn it on (`tests/save_load.py` should then check the level contents).
  The configstring and latched-cvar save layout now matches Yamagi
  (`MAX_SAVE_TOKEN_CHARS`, `LATCH_CVAR_SAVELENGTH`).

- **Group 5:** `game/game.py` and `game/g_local.py` moved to
  `game/header/game.py` (`game_h`) and `game/header/local.py` (`local`).
  The game now draws its random numbers from `rand.randk()` (seeded in
  `GetGameAPI`). `g_phys` has Yamagi's pushed-entity API, real bounding
  boxes for rotating bmodels, flying-monster friction and the
  stuck-in-world revert in `SV_Physics_Step`. `AI_SetSightClient` looped
  forever once `sight_client` was set (fixed). The move tools had added a
  second `from game import g_utils` to many files; removed.

## Progress

- [x] 0. Tooling and conventions
- [x] 1. Shared code
- [x] 2. Common engine code
- [x] 3. Collision and player movement
- [x] 4. Network channel and server
- [x] 5. Game: core and physics
- [ ] 6. Game: player, weapons and items
- [ ] 7. Game: doors, triggers, targets, misc
- [ ] 8. Game: monsters and AI
- [ ] 9. Game: save games
- [ ] 10. Client core
- [ ] 11. Client effects
- [ ] 12. Menus
- [ ] 13. Sound
- [ ] 14. Platform layer
- [ ] 15. Renderer
