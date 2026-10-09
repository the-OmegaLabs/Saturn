# C++ demo pixel parity

Goal: first shippable C++ demo matches Python `examples/demo.py`
against a **Windows true-OpenGL** golden (not Mesa soft GL).

## Contract
- Window intent: 960x800 (`saturn::kDemoWindowWidth/Height`, Python `DEMO_WIDTH/HEIGHT`).
- **Golden source (pinned):** `.static/shots/demo-opengl-win-944x761.png`
  captured on DESKTOP Windows with `--backend opengl` via `SATURN_SHOT`.
  Measured client pixels today: **944x761** (window chrome / DPI path).
  Do **not** use Mesa soft-GL `demo-opengl-960x800.png` as golden.
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
```

Compare (expect FAIL until widgets catch up; size may also differ from 944x761):

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
