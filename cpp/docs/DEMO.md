# C++ demo pixel parity

Goal: first shippable C++ demo matches Python [`examples/demo.py`](../../examples/demo.py)
against [`.static/shots/demo.png`](../../.static/shots/demo.png) (pixel compare).

## Contract
- Window intent: 960×800 (`demo_common.DEMO_WIDTH/HEIGHT`).
- Golden PNG on main is currently **944×761** — compare that file, or regenerate
  OpenGL golden at the same size before claiming parity.
- Theme: `ThemeMode.DARK`, `Colors.SURFACE` background, Material baseline dark
  tokens in `include/saturn/colors.hpp`.

## Compare
```bash
python3 cpp/tools/compare_shots.py .static/shots/demo.png path/to/cpp_shot.png \
  --diff-out /tmp/demo-diff.png
```

## Caps (security)
See `limits.hpp`: `kMaxChildren`, `kMaxClipDepth`, `kMaxListItems`,
`kMaxScrollBackBytes`, `kMaxScreenshotPixels`. ListView scroll caches must
honor these — no unbounded tile buffers.

## Ownership
Containers / Row / Column own children via `unique_ptr`. Page `pointer_capture_`
is a non-owning raw pointer into that tree; clear it before removing a child.
