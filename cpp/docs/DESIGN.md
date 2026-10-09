# Design snapshot

Synced with group agreement (Saturn room). Update when constraints change.

## Non-goals (phase 1-4)
- Parallel Software / Vulkan backends
- `saturn.web` port
- Flet-compatible wide kwargs surface
- Shipping Material icon mega-tables

## Security
- Memory/bounds ownership rules in headers (`limits.hpp`)
- Resource validation before GPU/file use (doc now; code when assets land)
- Web (future): auth, origins, max_message_bytes, resume token lifetime first-class

## Quality
- Do not copy Python `**base` / Unpack sticker pattern
- Explicit options + nullable size contracts written once
- Hello before API width
- `Window` uses SDL init refcount (safe for multi-window later)
- `Window` size API: `client_width/height()` (logical, layout/hit) vs `drawable_width/height()` (pixels, GL/shot). No `width()`/`height()` aliases; no `requested_*` — ctor args are intent, `client_*` is live
- `Control::attach` is protected; only `Page` (friend) and `Control::add_child` attach; attach propagates `page_` to subtree

## Phase 1 status
- Real `glClear` + swap (not swap-only)
- `OpenGLRenderer` impl owned by `unique_ptr`
- Docs match tree (no phantom `cmake/` folder)

## Mapping from Python (reference only)
| Python | C++ target |
|--------|------------|
| `saturn.app` / `run` | `saturn::App`, `saturn::run` |
| `saturn.page.Page` | `saturn::Page` |
| `saturn.control.Control` | `saturn::Control` |
| `saturn.Row` / `Column` | `saturn::Row` / `saturn::Column` |
| `saturn.renderer.*` | `saturn::Renderer` + `OpenGLRenderer` |
| SDL via pygame-ce | SDL3 directly |

## Phase 2 status
- `fill_rect` via GL 3.3 core: sharp path = solid batch `fill_rects`; `radius > 0` = SDF rounded fill
- `stroke_rect` real via same SDF shader (annulus); **stroke alignment = inside** (outer edge on given Rect bounds; layout size unchanged)
- Caps: `kMaxCornerRadius` / `kMaxStrokeWidth` (also clamped to half min(w,h)); non-finite throws
- Clip / textured quads as before
- UTF-8 without BOM

## Phase 3 status
- GL entry points cached once; shader compile/link failures roll back GL objects
- `clip_push`/`clip_pop` drive real scissor with `kMaxClipDepth`
- Demo `ColorBox` added via `Page::add` (no hard-coded rect in `App::run`)

## Layout note
- `Page::layout(w,h)` uses `set_padding` / `set_spacing` (defaults 40/16; demo uses 24/16). `set_bgcolor` feeds `App` clear. After `set_rect` it calls `child->layout()` so nested `Row`/`Column` can position kids.
- `Container` width-only / height-only: unset axis still measured from children (+ padding).
- `Text::set_size` / ctor `size` (clamped `kMinFontPx`..`kMaxFontPx`); default 16.
- Screenshot: `SATURN_SHOT=path.png` (+ optional `SATURN_SHOT_FRAMES`, default 3) via `Renderer::read_pixels_rgba` + stb_image_write; capped by `kMaxScreenshotPixels` / `kMaxPathBytes`. Target `saturn_demo` (explicit `demo_contract` / `SATURN_DEMO_CONTRACT`; size constants in `demo_size.hpp`).
- `Row` / `Column`: own children via `unique_ptr` + `add()`; explicit `spacing` / `set_spacing` (no kwargs); `kMaxChildren` cap; intrinsic = sum main-axis + gaps, max cross-axis.
- Cross-axis: `CrossAxisAlignment` {Start, Center, End, Stretch} via `set_cross_axis_alignment`. Row default Center (Python `vertical_alignment`); Column default Start (Python `horizontal_alignment`). Stretch fills cross size unless child has explicit width/height.
- Expand: `Control::set_expand(bool)` / `ControlOptions::expand` — leftover main-axis space shared equally among expand siblings (bool only; no flex weights yet). Intrinsic size still sums natural footprints.
- Pointer: `Control::hit_target` walks children back-to-front then self `hit_test`; `Page::dispatch_pointer` captures the deepest target (nested buttons work).
- `FilledButton::hit_test` uses the same effective corner radius as paint (`kMaxCornerRadius` / half min(w,h)); corner pockets use circle tests so round paint and hit agree.
- `clip_push` throws if stack exceeds `kMaxClipDepth` (no silent drop).
- Invalid layout size clears `layout_dirty_` (no per-frame no-op spin).

## Phase 4 status
- `Text` + `FilledButton` hello (pointer capture, SDF round fill)
- Caps: `kMaxTextLen` / `kMaxFillRects` throw, no silent truncate
- Hello track closed; layout widgets (`Row`/`Column`/`Container`) landed

## Image (PNG via stb_image)
- Path > `kMaxPathBytes` or empty → throw in ctor (no `resize` truncate).
- `ensure_loaded` throws on open/size/decode failure and on dims over
  `kMaxImageDecodeDim` / `kMaxLayoutDim` / `kMaxScreenshotPixels`.
- `STBI_MAX_DIMENSIONS` == `kMaxImageDecodeDim` (4096), set before stb include;
  file bytes capped by `kMaxImageFileBytes`. No silent `catch (...)`.
- `border_radius`: non-finite throws; else `clamp_radius` / `kMaxCornerRadius`.
  Paint uses textured SDF mask (`draw_textured_quads` radius) matching fill_rect
  round AA. Demo inventory Image uses 8.

## Slider
- `divisions` must be in `[0, kMaxSliderDivisions]` (1024); ctor throws otherwise
  (no clamp) — paint ticks loop `divisions-1` times.
- `set_value` / `apply_value`: non-finite → throw (same as min/max).

## TextureImage / icons
- `TextureImage` is the single decode+upload+destroy helper for `Image`,
  `IconButton`, Checkbox `check.png`, Elevated leading (when path set).
- Embedded fallbacks in `icon_assets.hpp` (favorite/check/add); same path/file/dim
  fail-loud caps as Image (`kMaxPathBytes` / `kMaxImageFileBytes` / `kMaxImageDecodeDim`).

## Switch / Checkbox / ProgressRing / Dropdown
- Switch + Checkbox: inherit `Pressable` for press/click (no hand-rolled pointer).
- Switch: track 52×32 in 52×40 hit box; no animation yet.
- ProgressRing: value ∈ [0,1] (non-finite throw); track = SDF annulus; progress =
  segmented discs (pixel debt — no angular SDF yet; segs capped 180). Default
  40×40 / stroke 4 / PRIMARY.
- Elevated leading icon path defaults to **empty**; callers pass PNG explicitly.
- Dropdown: hint + options (≤ `kMaxDropdownOptions`); width default 180; field
  height 56 / text 16; inline popup (no overlay animation). `on_select(key)`.
  Hint / option `key`/`text` > `kMaxTextBytes` → throw (no `resize` truncate).

## Font (TTF metrics)
- `saturn::Font` via vendored `third_party/stb_truetype.h`; bundled `assets/Inter-Regular.ttf`
  (OFL; instanced from Python `saturn/assets` Inter variable @ wght=400/opsz=14).
- Real advances / ascent / descent; on-demand atlas (ASCII preload) → `create_texture_rgba8` +
  `draw_textured_quads`. Caps: `kMaxFontPx`, `kMaxFontFileBytes`, `kMaxPathBytes`, `kFontAtlasDim`.
- `Text` defaults to 16px; `FilledButton` uses M3 label 14px / PRIMARY / ON_PRIMARY. `run()` calls `Font::load_default()` and
  **fails loud** if missing (`SATURN_FONT_PATH` or `assets/Inter-Regular.ttf` next to exe).
- 5x7 `bitmap_font.hpp` is **not** for pixel parity (kept as emergency reference only).

## Dialog / SnackBar
- `DialogControl` overlay base; `Page::show_dialog` / `pop_dialog` / `tick`.
  Barrier dialogs ≤ `kMaxDialogDepth` (8); SnackBars ≤ `kMaxSnackBarQueue`
  (8) — separate counters on the shared overlay vector so Snack cannot starve
  Dialog (and vice versa). Oversize throws (no silent drop). Pops deferred
  until after pointer dispatch (action `on_click` cannot UAF the button).
- `AlertDialog`: barrier scrim (`kScrim`) + card `SURFACE_CONTAINER_HIGH`;
  actions ≤ `kMaxDialogActions`; title/content > `kMaxTextBytes` → throw.
  Title/content single-line paint is pixel debt vs Python wrap (see DEMO.md).
- `TextButton`: no fill / PRIMARY label (dialog Cancel).
- `SnackBar`: non-barrier bottom bar; `INVERSE_SURFACE` / `ON_INVERSE_SURFACE`;
  duration in `(0, kMaxSnackBarDurationMs]`; action present → persist until
  action dismisses. Message/action label > `kMaxTextBytes` → throw.
- TextField / ListView still frozen. No open/close motion yet.

## Next goal (not done)
- First C++ demo should pixel-match Python `examples/demo.py` (screenshot compare against
  Windows true-GL golden `demo-opengl-win-944x761.png`). Size contract: Python outer 960x800
  (`kDemoOuter*`), SDL logical client 944x761 (`kDemoClient*`), shot pixels 944x761 at
  100% DPI (`kDemoGoldenPixel*` — see `demo_size.hpp` / DEMO.md). Logical != pixel under
  HiDPI; do not claim machine alignment. Full control port / parity pixels are **not** claimed.
  `expand`/`CrossAxisAlignment` landed on Row/Column; MainAxisAlignment / flex weights still deferred.
