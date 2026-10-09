# C++ demo pixel parity

Goal: first shippable C++ demo matches Python `examples/demo.py`
against a **Windows true-OpenGL** golden (not Mesa soft GL).

## Contract
- Window intent: 960×800 (`demo_common.DEMO_WIDTH/HEIGHT`).
- **Golden source (pinned):** `.static/shots/demo-opengl-win-960x800.png`
  captured on DESKTOP Windows with `--backend opengl` via `SATURN_SHOT`.
  Measured client pixels today: **944×761** (window chrome / DPI path).
  Do **not** use Mesa soft-GL `demo-opengl-960x800.png` as golden.
- Theme: `ThemeMode.DARK`, `Colors.SURFACE` background, Material baseline dark
  tokens in `include/saturn/colors.hpp`.
- Hard blockers before claiming pixel parity: real font metrics (not 5×7 bitmap),
  same-backend golden, Row/Column expand/align later.

## Compare
```bash
python3 cpp/tools/compare_shots.py .static/shots/demo-opengl-win-960x800.png path/to/cpp_shot.png \
  --diff-out /tmp/demo-diff.png
```

## Caps (security)
See `limits.hpp`: `kMaxChildren`, `kMaxClipDepth`, `kMaxListItems`,
`kMaxScrollBackBytes`, `kMaxScreenshotPixels`. ListView scroll caches must
honor these — no unbounded tile buffers.

## Ownership
Containers / Row / Column own children via `unique_ptr`. Page `pointer_capture_`
is a non-owning raw pointer into that tree; clear it before removing a child.
