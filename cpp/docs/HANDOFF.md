# Saturn C++ Handoff (2026-10-09)

**main tip:** `39cf80c` (after #42 landed)
**Repo:** https://github.com/the-OmegaLabs/Saturn · code lives in `cpp/`
**Golden screenshot:** `.static/shots/demo-opengl-win-944x761.png` (Windows true-GL, drawable **944×761**)

---

## Goal Correction (user decision)

**Do not** treat "fit every pixel / farm `compare_shots` score" as the main goal anymore.

**What to do instead is replicate the Python side:**

1. **Animation** — transitions, elevation motion, press-scaling and other behavior contracts
2. **Logic** — control state machines, events, focus, dialog/menu stacks, scrolling and input
3. **Typography engine** — Row/Column/expand/align, measurement and dirty layout, clip, aligned with Python layout semantics

`compare_shots` is only a regression sniff, **not** a KPI. Adding Spacers or hacking the layout to farm score is forbidden.

---

## Current State in One Sentence

The SDL3 + OpenGL Control tree can already run `saturn_demo`; most inventory controls have static skins; **TextField / ListView are still unimplemented** (the unfreeze work was started but halted by the user). Compared to the golden shot it sits at about **avg_abs 7.63 / 27.6% off at tol=2**; the bulk of that is layout misalignment caused by missing TextField/ListView, not something "polishing a few more rounded corners" can eat away.

---

## Already Landed (C++)

| Area | Content |
|----|------|
| Window/sizing | `demo_size.hpp`: logical client vs pixel drawable; `SATURN_DEMO_CONTRACT` / explicit flags; no `width()`/`height()` alias shims |
| Rendering | Batched `fill_rects`, textured quads, SDF rounded fill/outline, `stroke_arc` (ProgressRing), `TextureImage` |
| Fonts | Bundled Inter + stb_truetype; atlas measurement/drawing |
| Layout | Row/Column, `CrossAxisAlignment`, `set_expand`, Container, rounded hit-testing, clip depth |
| Controls | Text, ColorBox, Elevated/Filled/Outlined/IconButton (Pressable/ButtonBase), Image (`border_radius`), Checkbox, Slider, Switch, ProgressRing, Dropdown (closed state), AlertDialog, SnackBar, TextButton |
| Shadows | Elevated: `painting.draw_shadow` ambient/key approximation (concentric semi-transparent rounded fills); `py_round` banker's rounding; **no** FBO/real Gaussian |
| Safety culture | `limits.hpp` **throws** on limit overflow, never silently truncates; missing GL uniform / pipeline failure throws |

### Key caps (excerpt)

See `cpp/include/saturn/limits.hpp`: `kMaxTextBytes`, `kMaxEventQueue=4096`, `kMaxClipDepth=64`, `kMaxListItems=4096`, `kMaxScrollBackBytes=4MiB`, `kMaxDialogDepth/Actions=8`, `kMaxSnackBarQueue=8`, `kMaxSnackBarDurationMs=60000`, `kMaxDropdownOptions=256`, `kMaxSliderDivisions=1024`, `kMaxImageDecodeDim=4096`, etc.

When unfreezing TextField/ListView, the reviewer already ruled: content goes through `kMaxTextBytes`; queued input goes through `kMaxEventQueue`; ListView must not tile/cache unboundedly; layout sizes follow the inventory, never guesses.

---

## Not Done / Debt

| Item | Notes |
|----|------|
| **TextField / ListView** | Still frozen; TBD in the demo. Inventory: `cpp/docs/demo-inventory.md` (TextField h56/pad16/r4/text16; ListView 400×260, spacing4, 30 items, item pad8/r6) |
| Dropdown **overlay** | The menu popup layer; the closed golden barely moves the headline; build it for **interaction correctness** |
| Elevated shadow fidelity | The contract path is right, but it's still a fill approximation ≠ silhouette Gaussian; don't twist color levels for Δ0.01 |
| Dialog long text | Single-line measure/draw; multi-line is pixel/typography debt |
| Animation system | Mostly not ported; under the new goal, first map the Python animation API before building the C++ equivalent |
| HiDPI / multi-scale | Not seriously done yet |

Recently merged PRs (excerpt): #33 Dialog/SnackBar → #34 queue accounting → #35–36 Image rounded corners → #37–38 ProgressRing real arcs → #39–42 Elevated shadow path correction.

---

## Running the Demo Locally (Windows, verified)

```powershell
cd C:\Users\bzym2\src\Saturn
git fetch origin; git checkout main; git pull origin main
$cmake = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
& $cmake -S cpp -B cpp/build "-DCMAKE_PREFIX_PATH=C:\Users\bzym2\src\SDL3-devel\SDL3-3.4.18"
& $cmake --build cpp/build --config Release --target saturn_demo -- /m
cd cpp\build\Release
.\saturn_demo.exe
```

Screenshot comparison: set `SATURN_SHOT` + `SATURN_SHOT_FRAMES=5`; tool is `cpp/tools/compare_shots.py`. Mesa/Linux screenshots are **not** golden. Desktop pushes used `HTTPS_PROXY=http://127.0.0.1:7897` + `gh`.

Comparison reports: run `cpp/tools/compare_shots.py` locally and use its output; do not depend on agent-machine paths.

---

## Documentation Index

- `cpp/docs/AGENTS.md` — agent constraints
- `cpp/docs/DESIGN.md` — design
- `cpp/docs/DEMO.md` — demo / screenshot contract
- `cpp/docs/demo-inventory.md` — control inventory matching `examples/demo.py`
- `cpp/docs/ANIMATION-CONTRACT.md` — Python animation/clock contract (skeleton)

---

## Suggested Next Steps (ranked by the new goal)

1. **Fill out the animation/clock/implicit contract per `ANIMATION-CONTRACT.md`** (skeleton is in place; fill the gaps before cutting code).
2. **Align typography/measurement semantics** (including Text wrapping), then talk about TextField.
3. **TextField / ListView** — follow the already-agreed caps + inventory, serving logic and layout, not score farming.
4. **Dropdown overlay / focus / dialog stack** — interaction correctness.
5. Hook animation and elevation transitions to the same clock.
6. Demote `compare_shots` to a "big regression didn't blow up" check.

---

## Collaboration Notes

- Group: Saturn (Coding / Coding 2 / Sharp Reviewer / Reviewer)
- Review: pin caps first, throw on overflow; Sharp Review: ruthless nitpicking, score farming forbidden
- Coding preference: plan first, then change (user side); the user explicitly called a **stop** this time, the unfreeze work was cancelled, nothing merged.

*Reason for stopping: the user asked to end the pixel-fitting route and switch to replicating Python animation + logic + the typography engine, leaving this handoff behind.*
