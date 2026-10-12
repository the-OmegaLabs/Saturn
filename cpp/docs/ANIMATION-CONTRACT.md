# Python → C++ Animation Contract (Skeleton)

Goal: replicate behavior, not farm pixels. Fill in this table before cutting code. Sources: `saturn/animation.py`, `saturn/motion.py`, `saturn/types.py` (`Animation` / `Duration` / `AnimationCurve`), and control `_animate_internal`.

## Clock and Entry Points

| Item | Python contract | C++ status | Notes |
|----|-------------|----------|------|
| Frame clock | Driven by Page / app; animations use wall-clock `now` (ms) | TBD | The same clock feeds elevation / ripple / dialog |
| `animation_spec` | `bool` / ms / `Animation` / `None` → `(seconds, curve)` | Not ported | See `animation.animation_spec` |
| `ease(curve, t)` | Includes Material private names (`materialStandard*` etc.) | Not ported | The curve table must match `animation.ease` |
| `interpolate` | Named interpolation for scalars / colors / Offset etc. | Not ported | |

## Material Durations (ms, `motion.py`)

| Token | ms |
|-------|---:|
| SHORT1–4 | 50 / 100 / 150 / 200 |
| MEDIUM1–4 | 250 / 300 / 350 / 400 |
| LONG1–2 | 450 / 500 |

## Demo-Relevant Control Motion (inventory these first)

| Control | Property | Duration | Curve | Trigger |
|------|------|------|------|------|
| ElevatedButton | `_elevation_progress` | SHORT3 (150) | EMPHASIZED | hover / press / release |
| ElevatedButton | `_shape_progress` | SHORT2 (100) | (style) | press / release |
| Button ripple | ink | SHORT4 press / SHORT2 fade | — | press / release |
| Switch / Checkbox / Slider | TBD from source | | | |
| Dialog / SnackBar / Dropdown overlay | TBD | | | |

The idle demo screenshot path uses elevation=1; **interactive live runs** are what need hover→3 / press→1 style transitions.

## Typography (a contract entry point alongside animation)

| Item | Python | C++ |
|----|--------|-----|
| Row/Column expand / cross-axis | Semantics exist | Partially landed |
| Text measurement / wrapping | TBD (needs contracting) | Single-line debt |
| Clip stack | `clip_push/pop` | Has depth cap |

Control sizes follow `cpp/docs/demo-inventory.md`; Spacer-based score farming is forbidden.

## Table-Filling Rules

1. Only record verifiable behavior (trigger → duration → curve → start/end values).
2. Limit overflow goes through `limits.hpp` and throws; never silent.
3. `compare_shots` is regression sniffing only, never a KPI.
