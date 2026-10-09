# C++ demo pixel parity

Goal: first shippable C++ demo matches Python `examples/demo.py`
against a **Windows true-OpenGL** golden (not Mesa soft GL).

## Contract — three sizes, do not collapse

| Name | Size | Meaning |
|------|------|---------|
| Python `DEMO_WIDTH/HEIGHT` / `page.window` | **960×800** | **Outer** window intent (`kDemoOuter*`) |
| C++ `SDL_CreateWindow` / `client_width()` | **944×761** | **Logical client** (`kDemoClient*`) |
| `SATURN_SHOT` / `drawable_width()` / golden PNG | **944×761** | **Pixel** framebuffer (`kDemoGoldenPixel*`) |

**Why the split:** Python `_set_size` treats `page.window.width/height` as
outer, then `client_size_for_outer` subtracts the measured Win32 frame
(~16×39) → client **944×761**. SDL3 `SDL_CreateWindow(w,h)` sizes the
**logical client** directly — so `CreateWindow(960,800)` shots **960×800**
and mismatches the golden. `saturn_demo` therefore opens at
`kDemoClientWidth/Height` (**944×761** logical), not the Python outer numbers.

**Logical vs pixel (HiDPI):**
- `Window::client_width/height()` = `SDL_GetWindowSize` (logical). Layout +
  pointer coords use this.
- `Window::drawable_width/height()` = `SDL_GetWindowSizeInPixels` (framebuffer).
  GL viewport + `SATURN_SHOT` use this.
- At **100% DPI**, logical client == pixel drawable (**coincidence**, not
  identity). Under HiDPI, pixels = client × scale: `pin_client` can still
  pass while the shot pixel contract fails loud. That is intentional until
  scale-aware golden is handled — **do not claim「本机已对齐」**.
- No `Window::width()`/`height()` aliases and no `requested_*` API — call
  `client_*` (layout) or `drawable_*` (GL/shot) explicitly. Ctor `w`,`h` is
  the logical-client intent; after `pin_client`, `client_*` is the live size.

Constants live in `include/saturn/demo_size.hpp` (not `colors.hpp`).

- **Golden (pinned):** `.static/shots/demo-opengl-win-944x761.png`
  (DESKTOP Windows, `--backend opengl`, `SATURN_SHOT`). Do **not** replace
  with Mesa soft-GL `demo-opengl-960x800.png`. Do **not** rename the golden
  to claim 960×800.
- Theme: `ThemeMode.DARK`, `Colors.SURFACE` background, Material baseline dark
  tokens in `include/saturn/colors.hpp`.
- Hard blockers before claiming pixel parity: bundled TTF metrics (Inter; see
  `saturn::Font` — not 5x7 bitmap), same-backend golden, Row/Column expand/align later.
- Font: `cpp/assets/Inter-Regular.ttf` (OFL, instanced from Python's Inter variable
  at wght=400). Override with `SATURN_FONT_PATH`. Hello/demo fail loud if missing.

## Skeleton (`saturn_demo`)
Layout register cut toward `examples/demo.py` — **not** pixel parity.
Has: SURFACE page, brand header (logo `Image` 52×40 CONTAIN + PRIMARY tint +
title 28 + `v0.1.0` 12), status 13, two 440px panels (pad 20 / radius 16),
button row spacing 8: `ElevatedButton` (+ icon) / `FilledButton` / `OutlinedButton`
/ `IconButton` (Inter ♥). Pressed fills use theme tokens (`PRIMARY_CONTAINER` /
surface-container family) — no hand-written RGB. Right panel: `ListView TBD`
until scroll caps land with security review.
**Still deferred** (expect `compare_shots` FAIL): TextField, Checkbox, Slider,
Switch, ProgressRing, Dropdown, Dialog/SnackBar, ListView scroll, variable Inter
weight / Noto SC, flex weights / MainAxisAlignment.

```bash
cmake -S cpp -B cpp/build -DCMAKE_PREFIX_PATH=/path/to/SDL3
cmake --build cpp/build --config Release --target saturn_demo
# Windows: run beside copied assets/Inter-Regular.ttf + saturn-logo-transparent.png
set SATURN_SHOT=cpp_skeleton.png
saturn_demo.exe
# optional: SATURN_SHOT_FRAMES=5 (default 3)
# optional: SATURN_DEMO_CONTRACT=1 forces contract on non-demo binaries
```

`SATURN_SHOT` writes the **actual** framebuffer pixel size.

**Contract arming:** only when `saturn_demo` passes `demo_contract=true`, or
when `SATURN_DEMO_CONTRACT` is set. It does **not** auto-arm just because a
window happens to be 960×800 outer or 944×761. When armed it checks:

1. logical client == `kDemoClient*` (944×761)
2. shot pixels == `kDemoGoldenPixel*` (944×761 at scale=1)

Compare (expect FAIL until widgets catch up; size must already be 944×761
at 100% DPI):

```bash
python3 cpp/tools/compare_shots.py .static/shots/demo-opengl-win-944x761.png cpp_skeleton.png \
  --diff-out /tmp/demo-diff.png
```

`saturn_hello` remains the minimal Text + FilledButton smoke (no contract).

## Compare
```bash
python3 cpp/tools/compare_shots.py .static/shots/demo-opengl-win-944x761.png path/to/cpp_shot.png \
  --diff-out /tmp/demo-diff.png
```

## Caps (security)
See `limits.hpp`: `kMaxChildren`, `kMaxClipDepth`, `kMaxListItems`,
`kMaxScrollBackBytes`, `kMaxScreenshotPixels`, `kMaxImageFileBytes`.
Screenshot / image path length capped by `kMaxPathBytes`. Image decode dims
clamped to `kMaxLayoutDim` / `kMaxScreenshotPixels`. ListView scroll caches
must honor these — no unbounded tile buffers.

## Ownership
Containers / Row / Column own children via `unique_ptr`. Page `pointer_capture_`
is a non-owning raw pointer into that tree; clear it before removing a child.
