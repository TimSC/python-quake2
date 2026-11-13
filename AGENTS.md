# Porting style guide

This repo is a work-in-progress port of the original Quake II C code to
Python. The work focuses on the `ref_gl` renderer and a pyglet-based
platform layer for cross-platform use.

This guide describes the style used in the hand-written part of the port
(up to commit 8a7d7c3). New code should follow it so that it reads like
the rest of the port.

The main rule is to **stay as close to the original C as possible**. The
Python should map line by line onto the C reference in
`quake2-original/` (the id Software 3.21 source), so that the two can be
compared side by side. Favour structural fidelity over idiomatic Python,
and make code idiomatic only when a literal translation is impossible or
far too slow. Avoid "cleanup" refactors and renaming.

## Workflow

1. Find the C file in `yquake2/src/` (or, for code not moved yet, in
   `quake2-original/`).
2. Create or open the matching `.py` file at the same relative path.
3. Paste the original C into it in `"""` blocks (or keep the existing
   blocks), as described under "Keeping unported C".
4. Port function by function, keeping names, order and globals.
5. Once a function is ported, delete its C block. Don't keep the
   original C function next to the Python.
6. C that is commented out inside a Python function usually still needs
   porting. Check before leaving it.
7. Don't enable or uncomment code that is disabled or commented out in
   the original C (`#if 0` blocks, `//` lines). Keep it disabled in the
   Python too.

## Files and modules

On the `yquake2` branch the port is moving from id's source to Yamagi
Quake II (`yquake2/src/`, pinned at git `4e2ad5e7`), one group at a time
(see `docs/yquake2_plan.md`). Moved code follows Yamagi's layout:

- Each Yamagi `.c` file becomes a `.py` file at the same path under the
  repo root: `yquake2/src/common/shared/shared.c` becomes
  `common/shared/shared.py`, `src/server/sv_main.c` becomes
  `server/sv_main.py`.
- Each Yamagi header becomes a module at the same path:
  `src/common/header/shared.h` becomes `common/header/shared.py`. If a
  header sits next to a `.c` file with the same stem, add `_h`.
- Each moved module has one local import name, the same in every file,
  so a prefix always means the same C file: `shared` is
  `common/header/shared.py`, `shared_c` is `common/shared/shared.py`,
  `common_h` and `files_h` are `common/header/common.py` and `files.py`
  (while id's `qcommon/common.py` and `files.py` still exist), `flash`
  is `common/shared/flash.py`. The player files are `p_client`, `p_hud`,
  `p_trail`, `p_view` and `p_weapon` (`game/player/*.py`), the monsters
  `m_<id name>` (`game/monster/<name>/<name>.py`, e.g. `m_berserk`,
  `m_soldier`, `m_move`) and their frame headers `<name>_h`.
  The sound files (`client/sound/`) are `sound_c` (`sound.c`),
  `sound_local` (`header/local.h`), `openal`, `qal` and `qal_h`, `wave`,
  `ogg`, `stb_vorbis` and `sound_sdl` (`sdl.c`).
  `scripts/yq_alias.py` renames them.
- SDL is `backends/sdl.py` (imported as `sdl`): the SDL 2 calls the port
  uses, with SDL's names and constants, done with pyglet. Port Yamagi's
  SDL code by calling `sdl.SDL_...` as the C does.
- The port of a Yamagi file follows Yamagi's C (names, order, globals,
  bug fixes and gameplay changes). `quake2-original/` stays as a
  historical reference only.
- `scripts/yq_index.py`, `yq_plan.py` and `yq_move.py` do the mechanical
  moves; `scripts/yq_diff.py <function>` shows what Yamagi changed in a
  function compared with id's code.
- Run `tests/run_all.sh` (and `tests/harness/run.sh` for collision and
  movement) after each group.

Code not yet moved still follows id's layout (historical rules):

- Each `.c` file becomes a `.py` file with the same name in the same
  directory: `client/cl_main.c` becomes `client/cl_main.py`.
- Each header becomes a module too. If its name would clash with the
  `.c` file, add an `_h` suffix (`gl_model.h` becomes `ref_gl/gl_model_h.py`).
  Otherwise use the plain name (`client.h` becomes `client/client.py`,
  `qcommon.h` becomes `qcommon/qcommon.py`).
- Only the Linux platform layer (`linux/`) is ported. `main.py` just
  calls `sys_linux.main()`.
- Sound plays through OpenAL (`client/sound/openal.py` and `qal.py`, with
  ctypes). The C software mixer (Yamagi's `sdl.c` backend) is deliberately
  left unported.
- Keep the id Software GPL header at the top of each file as a `"""`
  docstring. Under it, keep the original file comment and `#include`
  lines as text, for example `cvar.c -- dynamic variable tracking` and
  `#include "qcommon.h"`.

## Imports

- Import whole modules from their packages:
  `from qcommon import cvar, common, cmd`. Then always write the module
  name when using something from it: `common.Com_Printf(...)`,
  `shared.CVAR_ARCHIVE`, `cl_main.cls.state`.
- Don't use `from x import *`, and don't import single names. The
  module prefix shows which C file a symbol comes from.
- Every Python file starts with `from __future__ import annotations`
  (right after the module docstring), so type annotations can reference
  types without being evaluated at import time.
- Put standard library and third-party imports first (`io`, `math`,
  `struct`, `numpy as np`, `pyglet`, `OpenGL.GL as GL`), then project
  imports, kept close to the C `#include` order.
- Shared constants and structs come from `common/header/shared.py`
  (Yamagi's `shared.h`, formerly `game/q_shared.py`; the functions of
  `q_shared.c` are in `common/shared/shared.py`) and
  `common/header/files.py` (formerly `qcommon/qfiles.py`).
- Circular imports between modules are normal (the C globals are
  shared everywhere). They work because names are only looked up at
  call time.

## Keeping unported C

- Paste C that hasn't been ported yet into the `.py` file unchanged,
  inside a `"""` string at the same place it was in the C. Large parts
  of most files are still like this, and that is expected.
- Keep each `"""` block to a single C function (banner comment through
  the closing `}`). Don't bundle several pending functions into one big
  block: split at each `/*` / `==================` banner so blocks stay
  small and side-by-side diffs stay aligned. Non-function units (a struct
  typedef, the `#include`/define preamble, a frame table, the GL function-
  pointer list) may share a block, since they aren't functions.
- C local variable declarations become a `"""` block at the top of the
  function body. This records the C types:

  ```python
  def FS_LoadPackFile (packfile): # char * (returns pack_t *)

  	"""
  	dpackheader_t	header;
  	int				i;
  	...
  	"""
  ```

- Comment out single C lines that have no Python equivalent:
  `#out = Hunk_Alloc ( count*sizeof(*out))`, `#cvar_t		*cvar;`.
- If a branch hasn't been ported but the code around it has, use
  `raise NotImplementedError()` and keep the C under it in a `"""` block.
- Use `pass` for functions that do nothing in Python, such as
  `FS_FreeFile`.

## Functions

- Keep the original C names and capitalisation: `Cvar_Get`,
  `Mod_LoadVertexes`, `CL_Stop_f`, `R_RenderView`. Don't convert them
  to snake_case.
- Keep the C banner comment above each function, written as a `"""`
  string before the `def`:

  ```python
  """
  ============
  Cvar_FindVar
  ============
  """
  def Cvar_FindVar (var_name): #char *
  ```

- Write the C types of the parameters in a comment after the colon,
  in order. Add the return type in brackets when it isn't void:
  `#char *, char *, int (returns cvar_t *)`.
- Use type annotations on function parameters and return values, e.g.
  `def CalcFov (fov_x: float, width: float, height: float)->float:`.
  Annotate with the Python type that represents the C type (see Data
  types), so `#char *` is `str` and `#cvar_t *` is `cvar_t`.
- Often there is a space before the parameter list, as in the C:
  `def Cvar_Get (var_name, ...)`. This isn't always the case. Follow
  the spacing of the C you are copying.

## Layout

- **Indent with tabs**, like the C. (`qcommon/md4.py` uses spaces
  because it is a third-party MD4 implementation that was dropped in
  as is. Vendored code like that keeps its own style.)
- Keep the C's blank lines. Where C had an opening `{` on its own line,
  there is often an empty or whitespace-only line after the `if`, `for`
  or `else`:

  ```python
  	if var is not None:
  	
  		var.flags |= flags
  		return var
  ```

- Some C trailing semicolons and brackets around conditions are still
  there (`return False;`, `if (x):`). They're allowed but not needed.
  Don't go back and remove them.
- Keep the C comments, using `#` instead of `//`. Keep `FIXME` notes
  from the original. Mark changes you made while porting, e.g.
  `#FIXME Simplified while porting`.

## Globals

- C file-scope globals are module-level variables with the C type in a
  comment: `cl_stereo = None #cvar_t *`, `numgltextures = 0 #int`.
- Declare many related cvars on one line with tuple assignment set to
  `None`. They get their values later in the module's init/register
  function.
- A function that assigns to a module global must declare it with
  `global`, the same as the C code. Long `global` lines use `\` to
  continue.
- Fixed-size global arrays are filled in at import time with a loop:

  ```python
  gltextures = [] #image_t[MAX_GLTEXTURES];
  for i in range(MAX_GLTEXTURES):
  	gltextures.append(image_t())
  ```

## Structs, enums and constants

- A C `typedef struct` becomes a plain class with the same name
  (`image_t`, `cvar_t`, `client_state_t`) that subclasses `object`.
  Every field is set in `__init__`, with the C type and original
  comment after it:

  ```python
  class image_t(object):

  	def __init__(self):

  		self.name = None #char	[MAX_QPATH], game path, including extension
  		self.width, self.height = None, None #int, source image
  ```

- Don't use dataclasses, `__slots__` or properties.
- Use `None` for unset pointers and ints that have no value yet. Use
  `0`, `0.0` or `False` when the C relies on the value being zeroed.
- An `enum` typedef becomes a subclass of `Enum`, with the same name
  and member names (`imagetype_t.it_skin`). Use `.value` when you need
  the integer, e.g. `clc_ops_e.clc_stringcmd.value`.
- `#define` constants are module-level names in capitals, lined up
  with tabs as in the C: `TEXNUM_LIGHTMAPS	= 1024`.
- Pointers become object references, or `None` for NULL. Keep the C
  type comments.
- `qboolean` is `True`/`False`.
- Add `__repr__` to structs when it helps with debugging.

## Data types

- Use plain Python objects (classes, lists, ints, floats, `str`) for most
  data. Use numpy only for geometry: vectors, vertices, model frames and
  similar numeric arrays. For example, an alias model's frame vertices
  are a numpy array, but its GL command list is a plain list of ints and
  floats.
- C linked lists made of `next`/`chain` pointers become Python lists. For
  example, `surf.polys` is a list of `glpoly_t`, and `r_alpha_surfaces` is a
  list of surfaces. Where C prepends to a chain and the order matters,
  `append` and then iterate `reversed()`; prepend with `insert(0, ...)` when
  the list is only built once.
- `vec3_t` and other fixed-size float arrays are
  `np.zeros((3,), dtype=np.float32)`. Vector "macros" change the array
  in place so that C output parameters still work:
  `def VectorCopy(a,b): b[:]=a[:]`.
- Use `bytearray(n)` for byte buffers such as `byte[256]`. Large tables
  and image data use numpy arrays with matching dtypes.
- C strings are Python `str`. Data read from files and the network is
  `bytes`. Decode it with `.decode("ascii")` and strip the NUL padding.
- Format strings with `"...{}...".format(...)` (most common) or
  f-strings, and keep the `\n` from the C `Com_Printf` calls. Don't use
  `%` formatting.

## Pointers and output parameters

- Pointer arithmetic into a buffer becomes an integer offset plus
  slicing. Use names like `in_offset`, `in_offset2` and `out_p`:

  ```python
  	in_offset = l.fileofs + i * files_h.dvertex_t.packed_size()
  	in_offset2 = in_offset + files_h.dvertex_t.packed_size()
  	in_obj.load(mod_base[in_offset:in_offset2])
  ```

- Out-parameters that are scalars or new objects are returned as a
  tuple instead: `length, handle = FS_FOpenFile (path)`, and
  `return -1, None` on failure.
- Out-parameters that are arrays the caller already has are changed in
  place.
- Use `copy.deepcopy` where the C copies a whole struct by value
  (`r_newrefdef = copy.deepcopy(fd)`).

## Binary file formats

- On-disk structs (in `common/header/files.py`) are classes with a `load` or
  `read` method. It unpacks a byte slice or file handle with `struct`
  and explicit little-endian formats (`"<lll"`, `"<H"`). A
  `packed_size()` classmethod returns the size on disk.
- Network byte order uses `">"` formats.

## Errors and debugging

- Report errors and log output through the engine's own functions
  (`Com_Error`, `ri.Sys_Error`, `Com_Printf` in `qcommon/common.py`), as
  the C does. Don't raise Python exceptions or use `print` for these.
- Don't use `getattr` with a `None` default just to avoid attribute
  errors. Refer to the attribute directly, so a missing name fails
  straight away.
- Use `try/except` only around Python calls that can fail where C
  wouldn't, such as `float(var.string)`, and catch the specific
  exception.
- `assert` / `isinstance` checks at buffer boundaries (e.g. in
  `MSG_Write*`) are fine for catching `bytes`/`str` mix-ups.
- Temporary `print(...)` tracing during bring-up is tolerated
  (e.g. `print ("Mod_LoadVertexes", l)`). Remove it once the code works.

## Performance

- Only optimise a hotspot after measuring it.
- The port is pure Python, with no compiled extensions or build step.
  Try a faster pure-Python approach (numpy, a lookup table) before
  anything else, and keep the C structure where you can. For example,
  the cinematic Huffman decoder (`Huff1Decompress` in `client/cl_cin.py`)
  is a direct port of the C bit loop, and fast enough for playback.

## Dependencies

- Runtime dependencies are listed in `requirements.txt` (notably
  `pyglet`, `numpy` and `PyOpenGL`). Sound needs the OpenAL library
  (`libopenal.so.1`) and Ogg Vorbis decoding needs FFmpeg's libraries,
  which pyglet loads. HTTP downloads (`client/curl/`) use `pycurl`, whose
  wheels include libcurl.

## Commits

- Commit messages are short and plain. Use "Porting" for routine
  progress, and name milestones (e.g. "First polygon drawn",
  "Load wal textures").

## Data

- The game data in `/home/tim/dev/quake2data/Data` is only for running
  and testing (`python3 main.py +set basedir /path/to/quake2data/Data`).
  It is proprietary. Never copy it into the repository or port anything
  from it.
- To drive a test program from the command line, set `Q2STDIN=1` so console
  commands can be passed in via stdin (one command per line), e.g.
  `Q2STDIN=1 python3 main.py +set basedir /… < commands.txt`.
