# C++ demo pixel parity

Goal: first shippable C++ demo matches Python `examples/demo.py`
against a **Windows true-OpenGL** golden (not Mesa soft GL).

## Contract (drawable / client — not outer chrome)

| Name | Size | Meaning |
|------|------|---------|
| Python `DEMO_WIDTH/HEIGHT` / `page.window.width/height` | **960×800** | **Outer** window intent |
| Windows true-GL drawable (golden) | **944×761** | Client / framebuffer after Win32 frame chrome |
| C++ `saturn_demo` / `SATURN_SHOT` | **944×761** | Must match golden (`kDemoDrawableWidth/Height`) |

**Why the split:** Python `_set_size` treats `page.window.width/height` as
outer, then `client_size_for_outer` subtracts the measured Win32 frame
(~16×39) → client **944×761**. SDL3 `SDL_CreateWindow(w,h)` sizes the
**client** directly — so `CreateWindow(960,800)` shots **960×800** and
mismatches the golden. `saturn_demo` therefore opens at **944×761**
drawable pixels (`kDemoDrawable*`), not the Python outer numbers.

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
Layout-only first cut — **not** pixel parity yet (no ListView / inputs / icons).

```bash
cmake -S cpp -B cpp/build -DCMAKE_PREFIX_PATH=/path/to/SDL3
cmake --build cpp/build --config Release --target saturn_demo
# Windows: run beside copied assets/Inter-Regular.ttf
set SATURN_SHOT=cpp_skeleton.png
saturn_demo.exe
# optional: SATURN_SHOT_FRAMES=5 (default 3)
# optional: SATURN_DEMO_CONTRACT=1 forces drawable-size check even off demo dims
```

`SATURN_SHOT` writes the **actual** framebuffer size. In demo mode (window at
demo drawable/outer dims, or `SATURN_DEMO_CONTRACT`), a size other than
**944×761** fails loud.

Compare (expect FAIL until widgets catch up; size must already be 944×761):

```bash
python3 cpp/tools/compare_shots.py .static/shots/demo-opengl-win-944x761.png cpp_skeleton.png \
  --diff-out /tmp/demo-diff.png
```

`saturn_hello` remains the minimal Text + FilledButton smoke.

## Compare
```bash
python3 cpp/tools/compare_shots.py .static/shots/demo-opengl-win-944x761.png path/to/cpp_shot.png \
  --diff-out /tmp/demo-diff.png
```

## Caps (security)
See `limits.hpp`: `kMaxChildren`, `kMaxClipDepth`, `kMaxListItems`,
`kMaxScrollBackBytes`, `kMaxScreenshotPixels`. Screenshot path length capped by
`kMaxPathBytes`. ListView scroll caches must honor these — no unbounded tile buffers.

## Ownership
Containers / Row / Column own children via `unique_ptr`. Page `pointer_capture_`
is a non-owning raw pointer into that tree; clear it before removing a child.
