# C++ demo behavior and experience parity

Goal: first shippable C++ demo matches the Python version's **animations,
interaction logic, and user experience**, using `examples/demo.py` and its
control implementations as the reference. Screenshots are a coarse visual
gate for layout, colors, sizing, and missing controls; pixel-perfect rendering,
screenshot equality, and a fixed framebuffer size are not required.

## Acceptance

- Animation: match applicable Python state transitions, durations, easing,
  and interruption/reversal behavior. Cover hover/press feedback, toggles,
  menus, and dialog/SnackBar motion where Python implements them.
- Input: match pointer capture/release/cancellation, drag and scroll behavior,
  focus, keyboard navigation, text editing/submission, and disabled states
  where supported by Python. Verify state changes and callback order/payloads.
- Demo flows: the four buttons share an incrementing click count; Name input
  reports changes and submission; Checkbox, Slider, Switch, and Dropdown
  report their Python-equivalent values. Dialog Cancel/Delete close the
  dialog; SnackBar action/duration/dismissal follow Python behavior.
- Complete controls: TextField editing and the 30-item scrollable ListView
  are required demo experiences, not placeholders that can remain frozen.
- Usability: retain readable text, sensible layout and hit targets, correct
  clipping/overlays, and consistent behavior after resize or DPI changes.
  Platform-specific rasterization or window decoration differences are allowed.
- Verification: replay the same event sequences against Python and C++;
  check state/callback traces and compare animation samples over time. Also
  capture idle screenshots and require broadly comparable layout/control
  regions. A static screenshot alone cannot establish behavioral parity.

Keep the existing bounds, ownership, and untrusted-input constraints.
No Software/Vulkan/web backend is added by this goal change.

## Current Progress (2026-10-10)

- `motion.hpp`: deterministic scalar tweens, the same eight Material/linear
  curves and endpoint clamping as Python; continuous retarget/reversal.
- Button hover/press alpha + clipped moving ripple, elevated hover/press
  shadow, Checkbox value animation, Switch position/color/size + drag, Slider
  handle-width/state-layer motion.
- Dropdown no longer expands layout. Its page-level menu has reveal,
  staggered item alpha, close animation, outside dismissal, keyboard selection,
  and capped scrolling. Dialog/SnackBar now animate in/out before removal.
- Bounded UTF-8 TextField editing/selection/submission, Tab navigation, button
  keyboard activation; 30-row ListView with clipping, wheel, scrollbar dragging
  and Material scrollbar fade. Clipboard, IME preedit/commit, and word navigation
  are implemented; native candidate-window behavior still needs manual testing.
- Font sizes use em pixels and Text uses Python's 10/7 line box. Images default
  to Fill; the brand logo explicitly uses Contain. Renderer layout coordinates
  stay logical under HiDPI; framebuffer readback is no longer fixed to 944x761.
- Verified: Release build, `saturn_behavior` CTest, 64 easing samples plus
  9 Switch / 8 button / 10 Dialog+SnackBar / 58 Checkbox+Slider+field+menu+scrollbar
  / 80 interrupted/reversed samples against actual Python classes.
- Idle screenshots: `cpp/build/Release/demo-python-idle.png` vs
  `demo-aligned.png`, 944x761; mean absolute RGB error 0.9189, fraction above
  channel tolerance 12 = 0.013940. Raster/font-weight differences remain.
- Verified GPU motion: 36 fixed-time OpenGL frames, 112 control-region checks
  and 9 temporal-change checks. Modal close scroll blocking, disabled-ancestor
  cancellation, scrollbar drag and timeout dismissal have behavior regressions.
- AA update: vector `SaturnLogo`, pixel-derivative shape coverage, premultiplied
  image filtering/mipmaps and 2x cached glyphs (see CPP_GUIDE.md). After AA,
  idle mean RGB error = 0.9949, fraction above tolerance 12 = 0.015067.
- Not yet proven: full focus/disabled appearance/cancellation equivalence,
  native IME candidate UI and Unicode word classes, and HiDPI runtime validation.
  The goal remains active; these checks do not establish full completion.

```bash
cmake -S cpp -B cpp/build -DBUILD_TESTING=ON
cmake --build cpp/build --config Release
ctest --test-dir cpp/build -C Release --output-on-failure
python cpp/tools/verify_motion.py cpp/build/Release/saturn_behavior_tests.exe
python cpp/tools/capture_python_demo.py cpp/build/Release/demo-python-idle.png
python cpp/tools/compare_shots.py cpp/build/Release/demo-python-idle.png cpp/build/Release/demo-aligned.png --tol 12 --max-avg 2 --max-diff-frac .03
```

## Historical Snapshot

The remaining sections record the earlier skeleton and explain size/cap
contracts. Current progress above supersedes "frozen", "no animation", and
fixed pixel-check statements below; they are not the current acceptance goal.

## Existing size setup (legacy screenshot diagnostic)

The existing demo/screenshot code still has the following size checks.
These describe current implementation, **not** the new milestone's acceptance
criteria; do not extend them into a pixel-matching requirement.

| Name | Size | Meaning |
|------|------|---------|
| Python `DEMO_WIDTH/HEIGHT` / `page.window` | **960×800** | **Outer** window intent (`kDemoOuter*`) |
| C++ `SDL_CreateWindow` / `client_width()` | **944×761** | **Logical client** (`kDemoClient*`) |
| `SATURN_SHOT` / `drawable_width()` / golden PNG | **944×761** | **Pixel** framebuffer (`kDemoGoldenPixel*`) |

**Why the split:** Python `_set_size` treats `page.window.width/height` as
outer, then `client_size_for_outer` subtracts the measured Win32 frame
(~16×39) → client **944×761**. SDL3 `SDL_CreateWindow(w,h)` sizes the
**logical client** directly — so `CreateWindow(960,800)` shots **960×800**
and differs from the historical screenshot. `saturn_demo` currently opens at
`kDemoClientWidth/Height` (**944×761** logical), not the Python outer numbers.

**Logical vs pixel (HiDPI):**
- `Window::client_width/height()` = `SDL_GetWindowSize` (logical). Layout +
  pointer coords use this.
- `Window::drawable_width/height()` = `SDL_GetWindowSizeInPixels` (framebuffer).
  GL viewport + `SATURN_SHOT` use this.
- At **100% DPI**, logical client == pixel drawable (**coincidence**, not
  identity). Under HiDPI, pixels = client × scale: `pin_client` can still
  pass while the legacy shot pixel contract fails loud. This is a diagnostic
  limitation to remove when updating the screenshot path, not intended
  HiDPI behavior or a reason to reject otherwise correct interaction.
- No `Window::width()`/`height()` aliases and no `requested_*` API — call
  `client_*` (layout) or `drawable_*` (GL/shot) explicitly. Ctor `w`,`h` is
  the logical-client intent; after `pin_client`, `client_*` is the live size.

Constants live in `include/saturn/demo_size.hpp` (not `colors.hpp`).

- **Historical screenshot:** `.static/shots/demo-opengl-win-944x761.png`
  (DESKTOP Windows, `--backend opengl`, `SATURN_SHOT`). It may help diagnose
  visual regressions; matching it is not required for completion.
- Theme: `ThemeMode.DARK`, `Colors.SURFACE` background, Material baseline dark
  tokens in `include/saturn/colors.hpp`.
- Text uses `saturn::Font` (not 5x7 bitmap) for readable metrics and layout.
- Font: `cpp/assets/Inter-Regular.ttf` (OFL, instanced from Python's Inter variable
  at wght=400). Override with `SATURN_FONT_PATH`. Hello/demo fail loud if missing.

## Skeleton (`saturn_demo`)
Partial implementation of `examples/demo.py` — **not yet** animation,
interaction, or experience parity.
Has: SURFACE page, brand header (logo `Image` 52×40 CONTAIN + PRIMARY tint +
title 28 + `v0.1.0` 12), status 13, two 440px panels (pad 20 / radius 16),
button row spacing 8: `ElevatedButton` (demo passes **Material ADD**
`icons/add.png`; ctor default icon path is **empty**) /
`FilledButton` / `OutlinedButton` / `IconButton` (**Material FAVORITE PNG**
`icons/favorite.png` / embedded `icon_assets.hpp`). Pressed fills use theme tokens.
Checkbox row spacing 12: `Checkbox("agree")` (18×18 / radius 2 / PRIMARY;
check mark = `icons/check.png`; press via `Pressable`).
Slider row spacing 12: `Slider(0,100,divisions=10)` (~300×48) + `Switch`
(`Pressable`, 52×40, no label) + `ProgressRing(0.6)` (40×40 / stroke 4 /
PRIMARY). Dropdown row spacing 12: `Dropdown` hint `"dropdown..."` options
Alpha/Beta/Gamma width 180 + `Image(test_img.png)` 140×70 `border_radius=8`.
Dialog row spacing 8: `ElevatedButton("Dialog")` → `AlertDialog` (Confirm /
Cancel `TextButton` + Delete `FilledButton`) via `Page::show_dialog`;
`ElevatedButton("SnackBar")` → `SnackBar("Saved!", "Undo", 3000)`.
Right panel: `ListView TBD` until scroll caps land with security review.

**ProgressRing:** `stroke_arc` angular SDF (round caps) for track + progress;
track gap matches Python default (4). Finite value clamp stays. AA / HiDPI
raster differences alone do not block the new milestone.

**TextureImage:** shared PNG decode + GPU upload + destroy used by `Image`,
`IconButton`, Checkbox check, Elevated leading — one lifetime, fail-loud caps.

**Button factoring:** `Pressable` → `ButtonBase` (optional leading PNG via
`TextureImage`) → `Elevated` / `Filled` / `Outlined`. `IconButton` /
`Checkbox` / `Switch` are `Pressable` (or `Pressable` + `TextureImage`).

**Dropdown:** simple inline popup (expands intrinsic height when open; no
animation / no page overlay). Options capped by `kMaxDropdownOptions`.

**Dialog / SnackBar:** `Page` overlay stack with **separate** budgets —
barrier `AlertDialog` ≤ `kMaxDialogDepth=8`, non-barrier `SnackBar` ≤
`kMaxSnackBarQueue=8` (neither steals the other's slots; oversize throws).
`AlertDialog` scrim + centered card (pad 24 / inset 40 / radius 28;
`kMaxDialogActions=8`; title/content/action labels > `kMaxTextBytes` throw).
`SnackBar` bottom bar (INVERSE_SURFACE); duration `(0, kMaxSnackBarDurationMs]`;
with action label persists until Undo (Python default). Overlay is simple —
no animation; true menu overlay/clip depth still deferred for Dropdown.
**Usability gap:** title/content/message are single-line `measure`+`draw` (long
text clips; not Python multi-line card wrap). TextField/ListView still frozen.

**Required behavior/experience gaps:** TextField editing/submission, ListView
scroll, Dropdown outside-click dismiss / true overlay+clip, Python-equivalent
focus/keyboard behavior, control state animations, and Dialog open/close motion.
Flex weights / MainAxisAlignment, text wrapping/font coverage, and HiDPI handling
must be addressed where they affect usability. Verify Python behavior before
implementing each transition; do not invent motion to match a still image.

**Elevated shadow:** ambient+key ≈ `painting.draw_shadow` (α=28/40;
blur=`max(1,round(...))`, dy=`round(0.5e)` — Python3 banker’s; e=1 → blur 2/1, dy=0) via
stacked translucent fills; no blur kernel/FBO. Idle elevation=1 only —
hover/press animation deferred.
Not Card `BoxShadow(blur=3*e)`. Prioritize Python-equivalent hover/press
transitions over reducing screenshot-difference percentages.

```bash
cmake -S cpp -B cpp/build -DCMAKE_PREFIX_PATH=/path/to/SDL3
cmake --build cpp/build --config Release --target saturn_demo
# Windows: run beside copied assets/ (Inter + logo + icons/*.png)
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

`saturn_hello` remains the minimal Text + FilledButton smoke (no contract).

## Optional Screenshot Diagnostic
This compares static rendering only. PASS is not behavioral acceptance;
FAIL does not by itself block the milestone. The legacy size check above
still applies when taking demo screenshots.

```bash
python3 cpp/tools/compare_shots.py .static/shots/demo-opengl-win-944x761.png path/to/cpp_shot.png \
  --diff-out /tmp/demo-diff.png
```

## Caps (security)
See `limits.hpp`: `kMaxChildren`, `kMaxClipDepth`, `kMaxListItems`,
`kMaxScrollBackBytes`, `kMaxScreenshotPixels`, `kMaxImageFileBytes`,
`kMaxImageDecodeDim` (STBI_MAX_DIMENSIONS; tighter than `kMaxLayoutDim`),
`kMaxSliderDivisions` (ctor throw if out of range; `set_value` rejects non-finite),
`kMaxDropdownOptions` (ctor throw if options oversize),
`kMaxDialogDepth` / `kMaxDialogActions` / `kMaxSnackBarQueue` /
`kMaxSnackBarDurationMs` (throw, no truncate; Dialog vs SnackBar budgets split).
Screenshot / image / icon path length capped by `kMaxPathBytes` — oversize paths
**throw**, never truncate. `Image` / `IconButton` fail loud on bad/oversize
decode (no silent empty paint). ListView scroll caches must honor these —
no unbounded tile buffers.

## Ownership
Containers / Row / Column own children via `unique_ptr`. Page `pointer_capture_`
is a non-owning raw pointer into that tree; clear it before removing a child.
Pointer **move** events (LMB held) are forwarded to the capture target so
`Slider` can drag.
