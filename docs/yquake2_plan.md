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
- `src/client/refresh/gl3/`: the modern OpenGL 3 renderer (group 16).
- The SDL 2 platform code. There is no SDL: `backends/sdl.py` provides the
  SDL 2 calls the port uses (windows, GL contexts, events, display modes,
  gamma, clipboard), done with pyglet, so the ports of Yamagi's SDL files call
  `sdl.SDL_...` line by line as the C does (pygame was the back end until the
  switch to pyglet):
  - `src/client/vid/vid.c`, `src/client/vid/glimp_sdl2.c`;
  - `src/client/input/sdl2.c` (mostly done in groups 10 and 12);
  - `src/backends/unix/` and `src/backends/generic/` (mostly `sys_linux` today).

**Not ported, at least for now:**

| Yamagi code | Why |
|---|---|
| `client/refresh/soft/`, Vulkan | Other renderers. |
| `glimp_sdl3.c`, `input/sdl3.c` | `backends/sdl.py` follows SDL 2. |
| `backends/windows/` | Linux only, as before. |
| `client/sound/sdl.c` | SDL audio and the C software mixer; OpenAL (`openal.c`) is the back end. |
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
   - the pyglet and numpy code;
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
| 13 | Sound | `client/sound/sound.c`, `wave.c`, `ogg.c`, `openal.c`, `qal.c` | `client/snd_*.py`, `linux/snd_linux.py` | **Moved** to `client/sound/` (`sound.py`, `openal.py`, `qal.py`, `wave.py`, `ogg.py`, `header/local.py`, `header/qal.py`); OpenAL is the back end (ctypes on `libopenal.so.1`), `sdl.c` is not ported (`SDL_BackendInit` fails). Music is decoded by `header/stb_vorbis.py` (pyglet's FFmpeg decoder in place of stb_vorbis) and queued through `S_RawSamples`, as the C does. Test `tests/ogg_music.py` | Sounds, loops, sexed sounds, cinematic sound, music |
| 14 | Platform layer | `client/vid/vid.c`, `glimp_sdl2.c`, `client/input/sdl2.c`, `backends/unix/*.c`, `backends/generic/misc.c` | `linux/*.py` | Restructure: Yamagi's `vid`/`glimp`/`backends`. The SDL calls go to `backends/sdl.py` (SDL 2 on pyglet; pygame before) | Window, video modes, input, mouse grab, quit |
| 15 | Renderer: gl1 (OpenGL 1) | `client/refresh/gl1/*.c`, `client/refresh/files/*.c`, `client/refresh/ref_shared.h`, `client/vid/header/ref.h` | `ref_gl/*.py` | Faithful re-port of Yamagi's `gl1/`, replacing `ref_gl/`; Yamagi's approach as written, no `Q2PORT` speed-ups carried over (performance is a later pass) | Screenshots match; `timedemo`; extensions off |
| 16 | Renderer: gl3 (modern OpenGL) | `client/refresh/gl3/*.c` | none (new) | New: Yamagi's gl3 renderer with GLSL shaders, selected at start up alongside gl1 | Screenshots look right on base maps; `timedemo`; renderer switch at start up |

The current `ref_gl/` keeps the game running until group 15 replaces it.

## Group 15: the gl1 renderer re-port

`ref_gl/` is replaced, not patched: each of Yamagi's `gl1/gl1_*.c` and
`refresh/files/*.c` files becomes a module under `client/refresh/gl1/` and
`client/refresh/files/` (with `gl1/header/` for `local.h`, `model.h` and
`qgl.h`), ported function by function from Yamagi's C in its order. This
picks up Yamagi's fixes to the OpenGL 1 renderer (e.g. the `gl1_stereo`
fixes, `gl1_overbrightbits` value checks, `gl1_multitexture`,
`gl1_particle_square`) that the old `ref_gl/` doesn't have. The modern
gl3 renderer is a separate step (group 16).

- **Faithful first.** Port Yamagi's structure and logic as written. The
  old `ref_gl/` is the reference for what already works, not the template
  for the new code.
- **No `Q2PORT` speed-ups for now.** Port Yamagi's C as written, including
  its per-pixel loops. Performance (numpy texture passes, unrolled
glcmds, inlined frustum culling, the `Q2DBG` trace) is a separate later
  pass once the faithful port runs.
- **`qgl.c`** is replaced by PyOpenGL, as the old `ref_gl/` already did;
  `gl1_sdl.c` (context, swap, mode changes) calls `backends/sdl.py`
  (pyglet), like `glimp_sdl2.py`. gl1 gets a compatibility context (no
  profile is asked for), gl3 a 3.2 core one.
- **Interface:** the port's client calls the renderer through the
  `refexport`-style `re.` attributes. The current `ref_gl/` already
  exposes the few extra exports the ported client uses (`DrawCharScaled`,
  `RDraw_PicScaled`, ...); the new modules must keep those signatures so
  groups 10–14 keep working across the cutover. `refresh/files/` provides
  the shared model/texture loaders (`models.c`, `pcx.c`, `pvs.c`,
  `surf.c`, `wal.c`); PCX keeps the Pillow decode (`Q2PORT`).
- **Cutover:** the old `ref_gl/` is deleted once the new renderer passes
  the tests: screenshots match the old renderer, `timedemo` runs, and it
  works with the extensions off.

### Status (cutover done, faithful reconciliation in progress)

- **Done:** `client/refresh/files/` (models, pcx, pvs, surf, wal) is a
  faithful port of Yamagi's shared loaders. `client/vid/header/ref.py`
  (new `ref.h`, `API_VERSION` 8), `client/refresh/ref_shared.py`
  (`ref_shared.h`) and `client/refresh/gl1/header/model.py` (`model.h`) are
  in place. The `client/refresh/gl1/` package is live: `client/vid/vid.py`,
  `client/vid/glimp_sdl2.py` and `linux/qgl_linux.py` now import `gl1_main`;
  the old `ref_gl/` is deleted. All deterministic tests and the movement
  harness pass, and the real-time tests pass in isolation (they are
  timing-flaky when the whole suite runs back-to-back, which is pre-existing).
- **Faithful reconciliation (in progress):** the `gl1/*.py` bodies are the id
  version moved into the new package; they are being reconciled to Yamagi's C
  file by file. Verification runs against the live X display (RTX 3090, GL 4.6)
  via `glReadPixels` screenshots diffed pixel-for-pixel against a reference frame
  of the current renderer (no Xvfb needed).
  - **Done (each verified pixel-identical to the reference):** cvar renames to
    Yamagi names (`gl_*` -> `gl1_*`/`r_*`, `gl_swapinterval` -> `r_vsync`);
    `gl_cull` -> `r_cull`; dropped `r_nocull` and the duplicate `R_CullBox`
    (now `files/surf.R_CullBox`); image texture functions renamed `GL_*` -> `R_*`
    (`R_Bind`, `R_MBind`, `R_SelectTexture`, `R_TexEnv`, `R_EnableMultitexture`,
    `R_TextureMode`, `R_TextureSolidMode`, `R_LoadPic`, `R_Upload32/8`, ...).
    The old port already carried most of Yamagi's image module (with
    `currenttmu`/`currenttextures` state), so these were pure renames.
  - **Done (verified against the live display):** function renames to Yamagi's
    gl1 names - the warp helpers (`BoundPoly`/`ClipSkyPolygon`/`DrawSkyPolygon`/
    `EmitWaterPolys`/`MakeSkyVec`/`SubdividePolygon`/`GL_SubdivideSurface` -> `R_*`,
    `R_SetSky` -> `RI_SetSky`); the mesh alias draws (`GL_DrawAliasFrameLerp`/
    `GL_DrawAliasShadow`/`GL_LerpVerts` -> `R_*`); the 2d draw (`Draw_*` -> `RDraw_*`; the
    vid-level `vid.py` `Draw_*` already matched the C); the light marker
    (`R_MarkLights` -> `R_MarkSurfaceLights`, now the per-surface front/back marker
    called through `files/surf.R_MarkLights` - a real Yamagi fix); and the renderer
    entry points (`R_Init`/`R_Shutdown`/`R_RenderFrame`/`R_BeginFrame`/`R_SetPalette` ->
    `RI_*`, `R_RegisterSkin`/`R_BeginRegistration`/`R_RegisterModel`/`R_EndRegistration`
    -> `RI_*`), plus a port of `R_ResetClearColor`. `re.DrawPic`/`re.DrawChar` are now
    commented out to match the C (the id-era base `Draw_Pic`/`Draw_Char` remain as
    dead code, since removing them is a cleanup this pass leaves alone).
  - **Brightness bug fixed (verified against the compiled C reference):** the
    base texture rendered ~2x too bright (fullbright ratio 2.01x, normal 1.79x;
    the lightmap path was already correct). The C reference
    (`yquake2/` at `4e2ad5e7`) is the ground truth. Two bugs, both in
    `gl1_image.py` `R_Upload32`:
    1. `gl_solid_format`/`gl_alpha_format`/`gl_tex_solid_format`/`gl_tex_alpha_format`
       were the raw ints `3`/`4` instead of the GL enums `GL_RGB`/`GL_RGBA`; passing
       an invalid internal format to `glTexImage2D` made the driver mis-read the
       bytes (2x brighter). The C uses `Q2_GL_SOLID_FORMAT`/`Q2_GL_ALPHA_FORMAT`
       (`GL_RGB`/`GL_RGBA`).
    2. `R_LightScaleTexture` ran on the raw data **and** again on the resampled
       result, so resampled (mip) textures were intensity-scaled twice. The C's
       `R_Upload32Native` scales `data` once; `R_Upload32Soft` resamples the raw data
       then scales the result once. Now the non-resample path scales `data` once and
       the resample/mip path scales `scaled` once.
    After the fix the rendered frame matches the C: fullbright ratio 1.005, lightmap
    1.009, normal ~0.92 (the small residual is within the lightmap base-offset
    tolerance, not a brightness bug).
  - **Re-ported from Yamagi (function by function):** `gl1_buffer`, `gl1_scrap`,
    `gl1_image` (Native/Soft uploads, nolerp lists, anisotropy, minlight table,
    retexturing through `files/stb.R_LoadImage`), `gl1_draw` (2D through the
    buffer), `gl1_misc` (16x16 dot/square particle texture, `R_Strings`,
    `R_SetDefaultState`; `R_ScreenShot` still writes id's TGA until the client's
    `Vid_WriteScreenshot` is ported), `gl1_sdl` (window/context hooks used by
    `GLimp_InitGraphics`, vsync, hardware gamma), `qgl` (+ `header/qgl.py`), and
    gl1_main's set-up: `R_Register` (Yamagi cvar names), `SetMode_impl`/`R_SetMode`,
    `RI_Init` extension probing, `RI_Shutdown`, `RI_BeginFrame`, the particles,
    `R_SetGL2D`, `R_DrawBeam`, `GetRefAPI`. `files/stb.py` gained `ResizeSTB`
    (Pillow) and `SmoothColorImage`, and `R_Convert8to32` uses numpy (Q2PORT).
    Then `gl1_surf` (all of it: buffered world, `R_RegenAllLightmaps`,
    `R_GetBrushesLighting`, entity arguments), `gl1_mesh` (all of it: buffered
    alias models, stencil shadows, overbright, minlight; the `drawtris` Q2PORT is
    gone), `gl1_lightmap`, gl1_light's `R_BuildLightMap`/`R_SetCacheState`/
    buffered dlights, gl1_warp's `R_EmitWaterPolys`/`RI_SetSky`, and gl1_main's
    `R_DrawSpriteModel`/`R_DrawNullModel`/`R_DrawEntitiesOnList`. Then gl1_main's
    frame code (`R_SetupFrame`, `R_SetupGL` stereo split, `R_Clear`
    stencil/tile/zfix, `R_RenderView` stereo with files/surf `R_SetFrustum`,
    `R_PolyBlend` arrays), `gl1_model` (all of it: files/models `Mod_LoadMD2`/
    `Mod_LoadSP2`/`Mod_ReLoadSkins`, `parent_model` inline models as `model_t`
    submodels, free-space checks, `r_fixsurfsky`), `gl1_warp` (all of it: the sky
    box drawn with vertex arrays, `r_farsee`), `gl1_light` (all of it), and
    `header/model.py` (`modtype_t`/`mleaf_t` from `ref_shared`, no `mmodel_t`).
  - **Remaining:** none of the gl1 modules are id code now. Known Q2PORT
    differences: `R_ScreenShot` (TGA writer), numpy speed-ups (`R_Convert8to32`,
    `R_LightScaleTexture`, `R_MipMap`, particles, `R_LerpVerts`), and `ResizeSTB`
    via Pillow. Adaptive vsync (`r_vsync 2`) falls back to normal vsync, as the
    C does when the driver refuses it (pyglet only switches vsync on or off).

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
- **gl3 (group 16):** a new, additive renderer selected at start up with
  `Q2_RENDERER=gl3` (the port ships gl1 as the default; the C default is
  gl3). All of Yamagi's `gl3/*.c` is now ported function by function (main,
  draw, image, misc, model, lightmap, light, surf, warp, mesh, shaders, sdl),
  self-contained (no gl1 code), with the 2D and 3D batching, in a real
  OpenGL 3.2 core context: the renderer's `PrepareForWindow`/`InitContext`
  are called by `GLimp_InitGraphics`, through new optional fields on the
  port's `refexport_t`. It needed the rest of `files/stb.c` (`R_LoadImage`,
  `R_FindPic`, `GetSkyImage`, scale2x/3x, `R_FloodFillSkin`; tga/png/jpg via
  PIL) and fixes to `files/pcx.c`/`wal.c`, which gl1 doesn't use yet.
  Checked by screenshot against gl1: console, menus, cinematics, base1/base2,
  test entities/particles/dlights, the underwater FBO and a level change.
  Not ported: the stereo code (`#if 0` in the C), `gl3_debugcontext`'s
  callback, and `GL3_ScreenShot`'s file writing (the client's
  `VID_WriteScreenshot` isn't ported).
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

- **Group 6:** `game/p_*.py` moved to `game/player/` (imported as
  `p_client`, `p_hud`, `p_trail`, `p_view`, `p_weapon`, since a bare
  `client` would clash with the game's many `client` variables). The
  player animation frames are now all in `game/monster/misc/player.py`
  (`player_h`, from Yamagi's `player.h`). `scripts/yq_guards.py` adds
  Yamagi's leading NULL guards; pointer parameters that are vectors or
  strings are tested with `is None`, since `""` and numpy arrays don't
  behave like C pointers. Yamagi's `InitGame` and `InitAllocations`
  (`savegame.c`) are ported early in `g_save.py` for the new cvars
  (`aimfix`, `g_swap_speed`, `g_footsteps`, `coop_pickup_weapons`, ...).
  `itemlist` is now copied from a const `gameitemlist` in `InitItems`, as
  in Yamagi. Fixed: `client.pers` aliased `resp.coop_respawn` (C copies
  the struct), so dying in coop wiped the saved keys. `G_SetClientEffects`
  in the port matched neither C version; rewritten. Yamagi quirks kept on
  purpose: `SelectPrev` ignores its item flags; the coop fallback loop in
  `SelectSpawnPoint` never ends if the first coop spot is far away
  (marked FIXME); `OnSameTeam` with skin teams compares the full
  `model/skin`.

- **Group 7:** done function by function from Yamagi's changes (crush
  handling, `wait_and_change` for coop elevators, `hurt_use` hurting idle
  monsters, help-message delay, gibs now `SOLID_BBOX` and capped per
  frame, `commander_body_die`). The `target_string` and `func_clock` code is
  a full rewrite from Yamagi. The C helpers that write into a `char *`
  buffer return the string instead (`Q2PORT`). `CheckBlock` and
  `PrintPmove` (unused debug helpers that sum raw struct bytes) stay as C.

- **Group 8:** the monsters moved to `game/monster/<name>/<name>.py`
  (imported as `m_<id name>`, e.g. `m_berserk`, `m_soldier`, `m_move`),
  with their frame numbers in `<name>_h.py`, generated from Yamagi's `.h`
  files. The generation found a real bug: the soldier used
  `MODEL_SCALE` 1.0 instead of 1.2. `m_actor` is gone (Yamagi has no
  actor). Yamagi renamed `range` to `ai_range`; the boss modules had
  imported `range` from `g_ai` and so shadowed the builtin. Two new tools:
  `scripts/yq_c2py.py` translates simple Yamagi C functions into the
  port's style and writes them into a module (unresolved names are marked
  `FIXME c2py`). It ported most of the changed AI, monster and move
  functions. `scripts/yq_frames.py` compares and rewrites `mframe_t` and
  `mmove_t` tables, which picked up Yamagi's footstep frames. Footsteps
  play when `g_monsterfootsteps` is set. `tests/monster_all.py` now gives
  the medic a monster to heal rather than the player.

- **Group 9:** `game/g_save.py` is replaced by Yamagi's
  `game/savegame/savegame.py`, with the tables in `game/savegame/tables/`
  (generated by `scripts/yq_savetables.py`). Yamagi writes each struct
  with `fwrite`, so the port packs and unpacks the same bytes using the
  x86_64 layout of Yamagi's structs, `game/savegame/layout.py`. That file
  is generated by `scripts/yq_layout.py` with gcc and pahole, so save
  files should be the same format as Yamagi's (not yet tried against a
  real Yamagi save). `SV_CheckForSavegame` is on again. `ED_ParseField`
  now uses the savegame field tables, as in Yamagi. `tests/save_load.py`
  checks the player's health and position, the monster counts and every
  entity after loading. It passes on base1, base2, jail1 and bunk1; one
  bunk1 run timed out waiting after the load and later runs passed.

- **Group 10:** the client modules follow Yamagi's names and layout
  (`cl_network`, `cl_prediction`, `cl_screen`, `cl_console`, `cl_keyboard`,
  `client/header/*.py`, `client/vid/vid.py` for the renderer wrappers).
  Simple functions came from `yq_c2py.py`; the rest were ported by hand.
  The client runs Yamagi's loop: `Qcommon_Mainloop` and the client
  `Qcommon_Frame(usec)` in `common/frame.py` split packet frames from render
  frames, and `CL_Frame` builds the move command over several frames
  (`CL_RefreshCmd`, sent by `CL_SendCmd`). `curtime` is `frame.curtime`,
  and `Sys_Milliseconds` is Yamagi's monotonic clock; id's wall clock left
  cinematics stuck. `cl_entities` grows with `CL_AllocEntity`. Keys take
  Yamagi's split: `Key_Event(key, down, special)` for keys and
  `Char_Event` for typed text, fed from pygame's `TEXTINPUT` events in
  `linux/gl_glx.py`, which uses Yamagi's `IN_TranslateSDLtoQ2Key`
  (`client/input/sdl2.py`). `In_FlushQueue` and the cvars of `IN_Init` are
  there too; the mouse is still the pygame code in `linux/` (group 14).
  `client/cl_image.py` is Yamagi's PCX decoder for static cinematic pics.
  `CL_ParseConfigString` keeps the whole statusbar string in one
  configstring, where C runs it on into the next slots. The translator
  had made C array initialisers (`{0, 0}`) into Python sets, and `!s[0]`
  into `not s[0]`, which fails on empty strings; both fixed, and
  `cl.configstrings` start as `""`. `in_mouse 0` or the
  `Q2PORT_NOMOUSE` environment variable (set by the test scripts) stops
  the mouse capture. Left for later groups: menu.py still has id's
  options menu (group 12), the effects calls go to `cl_fx`/`cl_tent`
  (group 11), and `S_RawSamples` has no volume argument (group 13).

- **Group 11:** `cl_fx.py`, `cl_newfx.py` and `cl_tent.py` are now
  `cl_effects.py`, `cl_lights.py`, `cl_particles.py` and
  `cl_tempentities.py`, as in Yamagi, with Yamagi's `randk`/`frandk`/`crandk`
  in place of `random` and id's `frand`/`crand` (gone from `frame.py`). The
  particle linked lists are Python lists, newest last, walked `reversed()`
  where the C walks from the head (`cl_particles.py`). Heat beams, the beam
  helpers and `CL_AddMuzzleFlash` come from Yamagi; id's player beams,
  `CL_FlameEffects` and the unused projectile code in `cl_parse.py` are gone.
  `MSG_ReadPos` and `MSG_ReadDir` fill their vector as in C. Values read from
  the network are ints, so `CL_ParseTEnt` and `CL_EntityEvent` compare with
  `temp_event_t.X.value`; translated code needs this wherever a switch is on
  a network byte. Translator fixes: string literals are left alone (it had
  turned `!` into `not` in messages), C pointer walks become loops over the
  list, float loop variables become while loops, and pointer casts go.
  `INSTANT_PARTICLE` was +10000 in the port; it is -10000 as in C.

- **Group 12:** the menus are Yamagi's: `client/menu/menu.py`,
  `qmenu.py`, `videomenu.py` and `client/menu/header/qmenu.py`, ported
  from scratch, with id's versions gone. Every menu Yamagi has opens,
  including the gamepad, stick and gyro menus, though there is no gamepad
  input until group 14. In C every item struct starts with a `menucommon_s
  generic` and the code casts item pointers to `menucommon_s *`; here the
  item classes subclass `menucommon_s` and set `generic` to themselves, so
  both spellings work. Where the C points a menu's status bar or an item's
  name at a char buffer and rewrites the buffer later (the mods and DM
  options status bars, the player icon, the server list), the port also
  updates the alias (`Q2PORT`). `strlist_t` and the `StrList_*` API are
  ported (`shared.py`); `FS_ListFiles`, `FS_ListFiles2` and `FS_ListMods`
  return a `strlist_t` again, and their callers changed to match. The video
  menu writes Yamagi's cvars (`r_mode`, `r_vsync`, `r_anisotropic`, ...);
  id's renderer only reads `r_mode` (in place of `gl_mode`) and the mode
  table in `vid_so` is now Yamagi's, until groups 14 and 15. Yamagi's cvar
  rename turns an old `gl_mode 3` (640x480 in id's table) into `r_mode 3`,
  which is 640x400 in Yamagi's table, the same as in Yamagi. The renderer
  menu offers only gl1 (`VID_HasRenderer`); gl3 is added in group 16. New helpers: `IN_Init`'s cvars,
  `IN_NumpadIsOn`, the joystick presets and `In_FlushQueue` (`sdl2.py`),
  `gyro.h`, `Sys_RemoveDir`, `Q_strisnum`, `Q_strrchrs`, `Q_clamp`,
  `COM_StripExtension2`. More translator fixes: `(int)` and `(float)`
  casts become `int()` and `float()`, `x = (y += n)`, C99 `for (int i = ...)`,
  `extern` locals, struct locals become new objects, declarations with
  calls in the initialiser, and the data section of a C file is generated
  by `scripts/yq_cdata.py`.
  `tests/menu_settings_test.py` now opens every menu, changes sliders and
  spin controls, walks a menu with the keys and applies the video menu.

## Progress

- [x] 0. Tooling and conventions
- [x] 1. Shared code
- [x] 2. Common engine code
- [x] 3. Collision and player movement
- [x] 4. Network channel and server
- [x] 5. Game: core and physics
- [x] 6. Game: player, weapons and items
- [x] 7. Game: doors, triggers, targets, misc
- [x] 8. Game: monsters and AI
- [x] 9. Game: save games
- [x] 10. Client core
- [x] 11. Client effects
- [x] 12. Menus
- [ ] 13. Sound
- [x] 14. Platform layer
- [ ] 15. Renderer: gl1 (OpenGL 1)
- [ ] 16. Renderer: gl3 (modern OpenGL)
