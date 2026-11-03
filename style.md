# Porting style guide

The style used in the hand-written port of Quake 2 from C to Python
(up to commit 8a7d7c3). New code should follow it so that it reads like
the rest of the port.

The main rule is to **stay as close to the original C as possible**. The
Python should map line by line onto the C in `/home/tim/dev/quake2c`, so
that the two can be compared side by side. Make code idiomatic Python
only when a literal translation is impossible or far too slow.

## Files and modules

- Each `.c` file becomes a `.py` file with the same name in the same
  directory: `client/cl_main.c` becomes `client/cl_main.py`.
- Each header becomes a module too. If its name would clash with the
  `.c` file, add an `_h` suffix (`gl_model.h` becomes `ref_gl/gl_model_h.py`).
  Otherwise use the plain name (`client.h` becomes `client/client.py`,
  `qcommon.h` becomes `qcommon/qcommon.py`).
- Only the Linux platform layer (`linux/`) is ported. `main.py` just
  calls `sys_linux.main()`.
- Keep the id Software GPL header at the top of each file as a `"""`
  docstring. Under it, keep the original file comment and `#include`
  lines as text, for example `cvar.c -- dynamic variable tracking` and
  `#include "qcommon.h"`.

## Imports

- Import whole modules from their packages:
  `from qcommon import cvar, common, cmd`. Then always write the module
  name when using something from it: `common.Com_Printf(...)`,
  `q_shared.CVAR_ARCHIVE`, `cl_main.cls.state`.
- Don't use `from x import *`, and don't import single names. The
  module prefix shows which C file a symbol comes from.
- Put standard library and third-party imports first (`io`, `math`,
  `struct`, `numpy as np`, `pygame`, `OpenGL.GL as GL`), then project
  imports.
- Circular imports between modules are normal (the C globals are
  shared everywhere). They work because names are only looked up at
  call time.

## Keeping unported C

- Paste C that hasn't been ported yet into the `.py` file unchanged,
  inside a `"""` string at the same place it was in the C. Large parts
  of most files are still like this, and that is expected.
- When you port a function, move it out of the string and leave the C
  either side of it as it was.
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
- Type hints are rare. Only use them in small, self-contained helpers,
  e.g. `def CalcFov (fov_x: float, width: float, height: float)->float:`.
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
- `qboolean` is `True`/`False`.
- Add `__repr__` to structs when it helps with debugging.

## Data types

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
  	in_offset = l.fileofs + i * qfiles.dvertex_t.packed_size()
  	in_offset2 = in_offset + qfiles.dvertex_t.packed_size()
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

- On-disk structs (in `qcommon/qfiles.py`) are classes with a `load` or
  `read` method. It unpacks a byte slice or file handle with `struct`
  and explicit little-endian formats (`"<lll"`, `"<H"`). A
  `packed_size()` classmethod returns the size on disk.
- Network byte order uses `">"` formats.

## Errors and debugging

- Report errors through the engine's own functions (`Com_Error`,
  `ri.Sys_Error`, `Com_Printf`), as the C does. Don't raise Python
  exceptions for these.
- Use `try/except` only around Python calls that can fail where C
  wouldn't, such as `float(var.string)`, and catch the specific
  exception.
- `assert` / `isinstance` checks at buffer boundaries (e.g. in
  `MSG_Write*`) are fine for catching `bytes`/`str` mix-ups.
- Temporary `print(...)` tracing during bring-up is tolerated
  (e.g. `print ("Mod_LoadVertexes", l)`). Remove it once the code works.

## Performance

- Only optimise a hotspot after measuring it. Inner loops that are too
  slow in Python, like the cinematic Huffman decoder, go into a Cython
  `.pyx` file (`client/cl_cin_extras.pyx`). It is built with
  `python3 setup.py build_ext --inplace`.
- The `.pyx` keeps the same layout: banner comment, a `"""` block of C
  locals, the C names, and typed locals
  (`count: numpy.uint32_t = ...`). Comment the algorithm where it isn't
  obvious, with a link to its documentation.

## Commits

- Commit messages are short and plain. Use "Porting" for routine
  progress, and name milestones (e.g. "First polygon drawn",
  "Load wal textures").

## Data

- The game data in `/home/tim/dev/quake2data/Data` is only for running
  and testing (`python3 main.py +set basedir /path/to/quake2data/Data`).
  It is proprietary. Never copy it into the repository or port anything
  from it.
