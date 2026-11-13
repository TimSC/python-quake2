# gl3 (OpenGL 3.2) port — quirks and gotchas

Field notes from bringing up the Yamagi `gl3/` renderer in the Python port.
Everything here was found by reading pixel buffers back and diffing, not by
reading the docs. The C reference is `yquake2/src/client/refresh/gl3/`.

The short version: **PyOpenGL silently drops the C pointer semantics.** Most of
the "why does nothing render" bugs are not GL errors — the calls succeed and
produce a black frame. You only find them by reading the framebuffer back.

---

## 1. PyOpenGL `ctypes` quirks (the silent-failure ones)

PyOpenGL's wrappers for the fixed-function / GL2-era API take Python ints
where the C API takes pointers. When the int is `0` the call happens to work;
when it is non-zero it is interpreted as a *pointer value* and the driver
silently misbehaves. These are the three that bit us:

### 1.1 `glVertexAttribPointer` — the `offset` argument MUST be `ctypes.c_void_p`

This was **the** root cause of the gl3 2D black screen.

```python
# BROKEN (renders nothing, no GL error):
GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, 16, 0)
GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, False, 16, 8)

# WORKS:
import ctypes
GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, False, 16, ctypes.c_void_p(0))
GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, False, 16, ctypes.c_void_p(8))
```

The last argument is a byte offset into the VBO. PyOpenGL expects a
`ctypes.c_void_p` (a pointer), not a Python `int`. A raw `int` (even `0`) is
marshalled wrong and the attribute pointer ends up pointing at garbage, so the
VAO renders nothing. **All 11 `glVertexAttribPointer` calls** in the port use
`ctypes.c_void_p(N)` (2 in `gl3_draw.py`, 10 in `gl3_main.py`).

The **stride** argument (the 5th) is a plain `int` and is fine as-is — only the
offset (6th) needs the pointer wrap.

**Later notes:**

- **What actually happens:** PyOpenGL treats a Python `int` as *data*. It
  converts the int into a temporary one-element array and passes that array's
  address as the "offset". Querying it with `glGetVertexAttribPointerv` shows a
  large address-like value, not 0 or 8. So the attribute reads from far past
  the end of the VBO, and you get no GL error. This applies to `0` too: a plain
  `0` is not NULL here.
- **`None` is fine for offset 0.** It is passed as NULL. `tests/gl3_simple.py`
  and the GLUT example use `None` with one VBO per attribute, and that's why
  they work. With an interleaved VBO every offset after the first is non-zero,
  so use `ctypes.c_void_p(N)` throughout.
- **The fix is not in the working tree at the moment.** After the gl3 changes
  were stashed (`stash@{0}`), the port is back to plain ints. Check
  `RDraw_2DSetup` in `client/refresh/gl3/gl3_draw.py` (lines 60, 62) and
  `GL3_Init3Dstate` in `client/refresh/gl3/gl3_main.py` (about lines 399–436)
  before trusting the "all 11 calls" statement above.
- `tests/gl3_moderate.py --stage 13 --bug offsets` restores plain ints, and
  then almost every readback sample is wrong. That is the regression check for
  this bug.

### 1.2 `glGetActiveUniformBlockiv` (and other `*iv` getters) — use a `ctypes` array

A Python list `[0]` is accepted but **silently returns 0** (no error), so you
think the block index is 0 when it really is -1 (not found).

```python
# BROKEN (silently 0):
GL.glGetActiveUniformBlockindex(prog, name)   # fine (returns int)
GL.glGetActiveUniformBlockiv(prog, i, GL.GL_UNIFORM_BLOCK_BINDING_POINT, [0])  # NO

# WORKS:
buf = (ctypes.c_int * 1)()
GL.glGetActiveUniformBlockiv(prog, i, GL.GL_UNIFORM_BLOCK_BINDING_POINT, buf)
val = buf[0]
```

### 1.3 `glIsEnabledVertexAttribArray` does not exist

PyOpenGL 3.x doesn't bind it. To query an attribute's enabled state:

```python
buf = (ctypes.c_uint * 1)()
GL.glGetVertexAttribiv(idx, GL.GL_VERTEX_ATTRIB_ARRAY_ENABLED, buf)
enabled = bool(buf[0])
```

---

## 2. pygame / SDL buffer & context behaviour

pygame creates the GL context. Its buffer topology is **not** the simple
single/double-buffer model you get from a raw `XCreateGLContext`.

### 2.1 pygame opens a **stereo** context

`pygame.display.set_mode(..., OPENGL | DOUBLEBUF)` produces a context whose
default draw buffer is **`GL_FRONT_LEFT` (1029)**, not `GL_BACK_LEFT` (1028).
Both `pygame` (2.6.1 / SDL 2.28.4) and `pygame-ce` (2.5.8 / SDL 2.32.10) do
this — it is **not** an obsolete-pygame bug.

Consequence: `glDrawBuffer(GL_BACK)` is a **no-op** here (it stays 1029). You
*can* set it to `GL_FRONT` (1280) and it inverts, but the natural draw target
is `FL`. So "draw to the back buffer" just means "draw to the current draw
buffer (FL)".

### 2.2 Double buffering **is** working

The classic clear→read→flip→read sequence confirms it:

| moment | `GL_BACK` | `GL_FRONT` | `GL_FRONT_LEFT` |
|--------|-----------|------------|-----------------|
| before flip | current frame | previous frame | current frame |
| after flip  | current frame | current frame  | current frame |

So reading the **draw buffer** (`FL`, 1029) before `flip()` gives you the frame
you just drew. That is the correct readback path and it **works**.

### 2.3 What the four buffers contain (stereo, pre-flip)

```
GL_FRONT (1280)   = previous frame
GL_BACK  (2176)   = current frame  (== draw buffer)
FL       (1029)   = current frame  (== draw buffer)  <-- read this
BL       (1028)   = previous frame
```

So a faithful readback is: `glReadBuffer(GL_DRAW_BUFFER)` (== `FL`) then
`glReadPixels`. Reading `GL_FRONT` gives you the *previous* frame — the source
of a lot of "one frame behind" confusion.

### 2.4 The pipeline has **no** FBOs

The gl3 (and gl1) renderer draws straight to the default framebuffer. There is
no off-screen render target. So the only place content can be is the default
framebuffer, and the readback above is the only capture path.

**Correction:** this is true of gl1, but only partly true of gl3. Yamagi's gl3
does have one off-screen target, the post-process FBO. It is used only when
`gl3_usefbo` is 1 (the default) **and** the view needs post-processing, which
in practice means under water (`RDF_UNDERWATER`), or a v_blend while under
water. In the C, `GL3_SetGL3D` creates the FBO on first use:

- `ppFBO`, the framebuffer;
- `ppFBtex`, a `GL_RGB` colour texture with `GL_LINEAR` filtering;
- `ppFBrbo`, a `GL_DEPTH24_STENCIL8` renderbuffer for depth and stencil.

`GL3_RenderFrame` then draws the 3D view into it. Then
`GL3_DrawFrameBufferObject` binds framebuffer 0 and draws `ppFBtex` back as a
2D quad with `si2DpostProcessWater` (or `si2DpostProcess`). So:

- When you are under water, the world is in `ppFBtex`, not in the default
  framebuffer, until that final quad is drawn. A readback taken in between
  sees only the 2D layer.
- To check the FBO itself, bind `ppFBO` and read it back
  (`glReadBuffer(GL_COLOR_ATTACHMENT0)`).
- The FBO is a texture, so rows come back bottom-up, the same as the default
  framebuffer. `GL3_DrawFrameBufferObject` uses t = (1, 0) from top to bottom
  to flip it back the right way up.
- Restore framebuffer 0 before the final readback.

`tests/gl3_moderate.py` stage 13 does all of this and checks both readbacks.

---

## 3. gl3 renderer-specific quirks

### 3.1 `HMM_Orthographic` sign — `bottom = +h, top = 0`

The 2D ortho is `HMM_Orthographic(0, w, h, 0, -1, 1)`. The third param is
`bottom` and the fourth is `top`; to get q2's y-down convention you want
`bottom = +h` and `top = 0` (y=0 at the top). Writing `-h` flips the screen
vertically. The matrix is uploaded column-major: flatten the numpy mat4 with
`order="F"` for `glUniformMatrix4fv`.

### 3.2 mat4 layout

C `HMM_mat4.Elements[col][row]` is column-major. The Python `hmm.py` mat4 is a
numpy `[row][col]` array; the standard `@` operator matches C's `HMM_Multiply`,
and `flatten(order="F")` gives the 16 floats in the order GL wants.

### 3.3 gl3 must bootstrap gl1 state first

The gl3 image/model/warp/lightmap/light submodules are *thin* — they delegate
data-loading and traversal to the gl1 modules (duck-typed structs). So before
any gl3 draw works you must:

1. `gl1_main.ri = ...` and `gl1_main.R_Register()` (registers gl1's cvars).
2. `gl1_image.Draw_GetPalette()` (fills `d_8to24table` from `pics/colormap.pcx`).
3. `gl1_draw.Draw_InitLocal()` (allocates the scrap / console-char state).

Without this the thin modules hit uninitialised gl1 globals.

### 3.4 `RDraw_2DStart` must use `vid.width/height`, not `r_refdef`

The 2D console/menu draws happen **before** the first `RI_RenderFrame`, so
`r_refdef` is still unset. `RDraw_2DStart` sizes the ortho from `vid` (the
actual window), not the refdef.

### 3.5 `RI_RenderFrame` must mirror state into gl1

The gl3 sky reuses `gl1_warp.R_DrawSkyBox` (immediate-mode), which reads
`gl1_main.r_origin`, `gl1_main.r_newrefdef.time`, `skyrotate`, `skyaxis`. So
each frame gl3 copies the refdef/vieworg into gl1's globals before delegating:

```python
gl1_main.r_newrefdef = fd
gl1_main.r_origin[:] = fd.vieworg
```

### 3.6 Window title is renderer-specific

`GLimp_SetWindowTitle(...)` (in `glimp_sdl2.py`) sets the suffix:
gl1 → `"OpenGL 1.4"`, gl3 → `"OpenGL 3.2"`. Full title is
`"{APPNAME} {YQ2VERSION} - {suffix}"`.

### 3.7 GL enum constants must be real GL values

In the gl1 (and gl3) image upload code the internal format must be `GL.GL_RGB`
(6407) / `GL.GL_RGBA` (6408). Raw `3`/`4` are accepted by PyOpenGL (no error)
but produce a broken texture. (This was one half of the earlier brightness bug;
the other half was a double `R_LightScaleTexture` on resampled textures.)

### 3.8 The binding cache must see every bind

gl3 caches GL state in `gl3state` and skips a GL call when the cache says the
state is already set. The cached state and the functions that set it:

- the current program: `GL3_UseProgram`;
- the current VAO: `GL3_BindVAO`;
- the current VBO and EBO: `GL3_BindVBO`, `GL3_BindEBO`;
- the active texture unit: `GL3_SelectTMU`;
- the bound texture: `GL3_Bind`;
- the uniform buffer `updateUBO` last bound: `gl3state.currentUBO`.

So a direct `GL.glBindBuffer`, `glBindVertexArray`, `glUseProgram` or
`glBindTexture` anywhere in the port desyncs the cache. Typical sources are a
debug probe, a helper written straight from a tutorial, or a gl1 code path
that gl3 reuses.

The next cached bind is then skipped. For example, `glBufferData` goes into
whatever buffer *is* bound, and the draw uses the VBO's old vertices. There is
no GL error. In the readback the pic shows where it was drawn on an earlier
frame, or not at all.

- `tests/gl3_moderate.py` (stage 7 on) moves everything 40 px on the first
  frame, so stale vertices show up in the readback.
- `--bug cache` adds one direct `glBindBuffer`, and then almost every sample
  is wrong.
- **Rule:** inside the gl3 renderer, always bind through the `GL3_*` helpers.
  If something has to bind directly, reset the matching cache field to 0 so the
  next helper call binds again.

### 3.9 `_2d_init` survives a renderer restart

The port's `gl3_draw.py` keeps a module-level `_2d_init = [False]` guard. It is
not reset when the renderer is shut down and started again (`vid_restart`, or
"apply" in the video menu). The new GL context then never gets its 2D VAO/VBO
set up, and later binds use names from the old context. In Yamagi's C,
`GL3_Draw_InitLocal` runs on every `GL3_Init`, and `GL3_Draw_ShutdownLocal`
deletes the objects. The port should do the same.

### 3.10 Yamagi bug: `drawTexturedRectangleNow` flushes the pending batch first

At the pinned commit (`4e2ad5e7`), Yamagi batches 2D pics:

- `drawTexturedRectangle` adds 4 vertices and 6 `GLushort` indices to
  `vtxBuf`/`idxBuf`. The vertex order is (x,y+h), (x,y), (x+w,y+h), (x+w,y),
  and the indices are 0,1,2, 1,3,2.
- The batch is drawn with `glDrawElements(GL_UNSIGNED_SHORT)`. That happens
  when the texture changes, in `GL3_Draw_Fill`, `GL3_Draw_Flash`, every
  `*Now` draw and `GL3_RenderFrame`, and in `GL3_EndFrame`.

`drawTexturedRectangleNow` calls `GL3_DrawCurrent2Dbatch()` first. That
function does `GL3_UseProgram(si2D)` and `GL3_Bind(lastBatchTexture)`. Both
callers of `drawTexturedRectangleNow` have already chosen their own shader or
texture by then, so if a batch is pending the flush **undoes their choice**:

- `GL3_Draw_PicScaledCol` (`si2Dtinted`, used by the crosshair) is drawn with
  `si2D` and the batch's texture.
- `GL3_Draw_StretchRaw` (cinematics) is drawn with the batch's texture instead
  of the video frame.

This is Yamagi's code, so the port should keep it (follow the C). In the real
client nothing is pending at those points:

- `V_RenderView` ends with `R_RenderFrame` (which flushes) and then
  `SCR_DrawCrosshair`.
- `SCR_DrawStats` and the other HUD text come after the crosshair.

A test or debug overlay that draws text **before** a tinted pic or a
cinematic will see wrong output, and that output is correct for this C. The
`tint` and `raw` bugs in `gl3_moderate.py` reproduce it.

### 3.11 Default cvars that change what 2D pics look like

These are Yamagi's defaults:

- `vid_gamma` is 1.2. The shader's `gamma` uniform is `1.0 / vid_gamma`.
- `gl3_intensity_2D` is 1.5 and `gl3_intensity` is 1.5, so 2D colours are
  brighter than the raw texture: `pow(texel * 1.5, 1/1.2)`.
- `gl_texturemode` is `GL_LINEAR_MIPMAP_NEAREST`. 2D pics are uploaded without
  mipmaps, so `GL3_TextureMode` gives them a plain `GL_LINEAR` min filter. A
  mipmapped min filter on a texture with no mipmaps samples as black.
- `r_nolerp_list` is
  `"pics/conchars.pcx pics/ch1.pcx pics/ch2.pcx pics/ch3.pcx"`. These pics (the
  font and the crosshairs) get `GL_NEAREST`; every other 2D pic is bilinear.
- `r_2D_unfiltered` 0 and `r_videos_unfiltered` 0, so cinematics are bilinear
  too.
- `r_clear` 0: the screen is not cleared every frame. `GL3_ResetClearColor`
  sets the clear colour to pink, (1, 0, 0.5, 0.5).
- `gl3_usefbo` 1.

### 3.12 Image upload details that show up in readbacks

- **The scrap atlas:**
  - Pics up to 128×128 go into one 1024×1024 atlas, the scrap, with a 1-texel
    border.
  - The scrap is uploaded only when it is dirty, from `GL3_Scrap_Upload`, which
    the batch flush calls.
  - Their texcoords are atlas coordinates, not 0..1, so the scrap is one more
    thing that can make a pic sample the wrong texels.
- **The transparent palette entry:** `d_8to24table[255]` has alpha 0.
- **`R_Convert8to32` fills transparent pixels with a neighbour's colour.** It
  sets the RGB of each transparent pixel from an opaque neighbour, so bilinear
  filtering at a pic's edge doesn't blend in black. A port that leaves them
  black gets dark fringes around the font, the crosshair and HUD pics. These
  fringes are subtle, and only a pixel comparison catches them.
- **The alpha test:** `fragmentSrc2D` discards at `alpha <= 0.666`, which
  replaces gl1's `glAlphaFunc(GL_GREATER, 0.666)`. With bilinear filtering,
  pixels near a transparent edge can fall either side of it.

### 3.13 Shader compile and link conventions

- `CompileShader` puts `"#version 150\n"` in front of every source. The GLSL
  in `gl3_shaders.c` has no `#version` line of its own.
- `CreateShaderProgram` calls `glBindAttribLocation` for all six
  `GL3_ATTRIB_*` names **before** linking. The VAO setup depends on those fixed
  locations (position 0, texCoord 1, lmTexCoord 2, vertColor 3, normal 4,
  lightFlags 5), so don't look locations up with `glGetAttribLocation`.
- **Uniform blocks:** `initShader2D` looks up each block (`uniCommon`, `uni2D`)
  and checks its `GL_UNIFORM_BLOCK_DATA_SIZE` against the C struct size (see
  1.2 for reading that back). Then it binds `uniCommon` to binding point 0 and
  `uni2D` to binding point 1.
- `uniCommon` is std140 and 32 bytes: gamma, intensity, intensity2D, padding,
  then a vec4 color.
- `updateUBO` re-uploads the whole block with `glBufferData(GL_DYNAMIC_DRAW)`.
  It binds the buffer only when `currentUBO` differs (see 3.8).

---

## 4. The si2D texture-sampling bug (open)

The step-by-step harness (`tests/gl3_hello_2d.py`) isolated the 2D pipeline.
Findings, step by step (each verified by reading back the draw buffer `FL`):

| step | what | readback |
|------|------|----------|
| 1 | q2-style context + clear pink | `FL=BACK=pink`, `FRONT=black` — captured |
| 2 | real si2D shader + UBOs + VAO, **no** texture | **black** (unbound tex → `(0,0,0,1)` → `pow` → black; correct) |
| 3 | si2D + solid orange RGBA tex | **orange** (`FF8000`) — shader shades it, captured |
| 4 | si2D + `conchars.pcx`, glyph 'A' quad | orange (background through the black glyph) |
| 5 | si2D + `conchars.pcx` full-screen | **uniform `(19,19,19)`**, not the font sheet |

Step 5 is the bug. The texture is **uploaded correctly** (reading the GPU
texture back gives the conchars mean `[136.6, 104.5, 82.2]`, identical to the
CPU array), yet the si2D fragment shader samples it to a **constant** dark gray
instead of per-pixel. So the glyphs don't show — they render flat. This is the
"black triangle" seen in the real pipeline.

The si2D fragment shader is:

```glsl
vec4 texel = texture(tex, passTexCoord);
if (texel.a <= 0.666) discard;
texel.rgb *= intensity2D;
outColor.rgb = pow(texel.rgb, vec3(gamma));
```

The texcoord-as-color probe (`passTexCoord` output straight to the fragment
color, no texture) confirms it: the texcoord **is constant `(0.5, 0.5)`** —
every fragment samples the same uv, so the sheet renders as one flat color.

### 4.1 It is a **state leak from earlier steps**, not a si2D bug

The decisive test: the *identical* probe (fresh program, `#version 150`,
separate position/uv VBOs, `glVertexAttribPointer` + `glEnableVertexAttribArray`)
**works in a fresh standalone script** (gradient, mean ~`204/204/204`) but is
**flat inside `gl3_hello_2d.py`** even when run *after* a "full" reset:

```python
glBindVertexArray(0)
for i in range(16): glDisableVertexAttribArray(i)
glBindTexture(GL_TEXTURE_2D, 0)
for i in range(4):  glBindBufferBase(GL_UNIFORM_BUFFER, i, 0)
glUseProgram(0)
```

So the leak is **persistent vertex-attrib / VAO state left by the si2D 2D VAO
created in step 2**. Two things that are *not* the cause (each ruled out by an
isolated step): the VAO itself (a separate legacy VAO is flat too), the VBO
(a freshly uploaded full-screen quad is flat too), the matrix (perspective
*and* ortho, *and* a `P·MV` combined matrix are all flat), the shader `#version`
(`150` *and* `330 core` are both flat), the stride (`0` *and* the real stride
both flat), and the UBOs (unbound → still flat). Depth test and `glClear` of the
depth buffer don't help either.

What *does* make it work: **not having run the earlier steps first.** So the
fix path is to isolate the si2D draw in its own context/VAO lifecycle, or to
find the one bit of state the reset above misses (prime candidates: the legacy
global vertex array that a compatibility context keeps around, or the 2D VAO
still implicitly owning attribute 1). The si2D shader and data are fine — this
is purely a per-process GL state problem in the multi-step harness, which means
the *real* gl3 pipeline (one VAO, one consistent lifecycle per frame) is not
necessarily affected; verify against `tests/gl3_real2d.py` and the actual
`RDraw_*` path before assuming the renderer is broken.

### 4.2 Later finding: the likely cause is 1.1, not a hidden state leak

"Every fragment gets the same texcoord" is exactly what the plain-int offset
bug in 1.1 produces. The attribute pointer points at a temporary host array,
not into the VBO, so every vertex gets the same (or undefined) texcoord. That
also explains why a fresh standalone probe worked and the harness didn't:

- the standalone probe passed `None` (NULL), which is correct for offset 0;
- the harness steps passed plain ints, which are wrong whatever their value.

The reset in 4.1 can't fix this, because each new `glVertexAttribPointer`
call makes the same mistake again.

`tests/gl3_moderate.py` goes from the GLUT example to Yamagi's whole 2D path
in one process, one change per stage, with no state leaks. With `c_void_p`
offsets all 14 stages pass, and they fail as soon as the offsets go back to
plain ints. Treat section 4 as **probably resolved by 1.1**. It is only
confirmed for the moderate test, so re-check `gl3_hello_2d.py` step 5 with
`c_void_p` offsets before closing it.

---

## 5. Reproducing / debugging

- Standalone 2D harness (steps 1–5):
  `DISPLAY=:0 env/bin/python tests/gl3_hello_2d.py <step>`
- Real gl3 screenshot:
  `DISPLAY=:0 Q2_RENDERER=gl3 SHOT=/tmp/gl3_base1.png CAPFRAME=30 \
   timeout 15 env/bin/python -u tests/_refshot.py +set r_mode 3 \
   +set s_initsound 0 +set basedir /home/tim/dev/quake2data/Data +map base1`
- Readback pattern (use this in any diagnostic):
  ```python
  GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
  GL.glReadBuffer(GL.GL_DRAW_BUFFER)     # == FL (1029)
  px = GL.glReadPixels(x, y, 1, 1, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
  ```

Reference scripts in `tests/`: `gl3_hello.py` (4-step GL sanity),
`gl3_real2d.py` (real si2Dcolor quad), `gl3_hello_fbo.py` (FBO+blit variant),
`gl3_doublebuf.py` / `gl3_bufs.py` (buffer topology probes).

More scripts:

- `gl3_simple.py`: the GLUT textured-quad example ported to a pygame window,
  as a baseline that "shaders work here at all".
- `gl3_moderate.py`: a standalone step-by-step path from that example to
  Yamagi's gl3 2D renderer, with a pixel check at each stage.
  - Run `env/bin/python tests/gl3_moderate.py --stage N --frames 3` for a
    single stage. Without `--stage` it runs the last stage, 13.
  - `--bug offsets|cache|tint|raw` puts a known bug back.
  - The exit code is 0 when the readback matches.

## 6. Lessons from building a readback checker

These apply to any test that compares a GL readback with a CPU model of the
shaders:

- **Pixel-centre sampling is ambiguous.** With `GL_NEAREST` and minification,
  a sample whose texcoord lands exactly on a texel edge can go to either texel,
  depending on the driver's rounding. Skip those samples instead of accepting
  "either neighbour".
- **Skip the other ambiguous samples too:**
  - texels whose alpha is within rounding of the 0.666 discard threshold;
  - post-process (water warp) samples whose value changes by more than about
    1 byte when the lookup moves 0.02 texel.

  These are where the GPU's float precision decides the answer.
- **Model the uploaded data, not the source image.** Sample the texture as it
  was actually uploaded: scrap placement, `R_Convert8to32` edge fill, wrap mode
  (REPEAT or CLAMP), filter. Then apply, in this order: alpha test, tint,
  intensity, gamma, 8-bit quantisation, blending.
- **Replay the draws in painter's order,** starting from the clear colour. Log
  each draw call (pic, fill, flash, post) with its rectangle, texcoords,
  texture and tint, then replay them on the CPU.
- **Rows come back bottom-up.** Flip the `glReadPixels` result before indexing
  it with q2's y-down coordinates. This applies to the default framebuffer and
  to FBOs.
- **Change the scene between frames.** For example, draw the first frame
  shifted by 40 px, or give a cinematic a different frame each time. Then stale
  VBO contents or a stale texture show up as wrong pixels instead of passing by
  accident.
- **Check a known-bad variant for every bug you fix.** The check is only
  trusted once it **fails** with the bug put back.
