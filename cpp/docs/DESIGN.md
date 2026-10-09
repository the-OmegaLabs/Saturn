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
- `Page::layout` remains a top-level vertical column (padding/gap) for hello zero churn; after `set_rect` it calls `child->layout()` so nested `Row`/`Column` can position kids.
- `Row` / `Column`: own children via `unique_ptr` + `add()`; explicit `spacing` / `set_spacing` (no kwargs); `kMaxChildren` cap; intrinsic = sum main-axis + gaps, max cross-axis.
- Cross-axis: `CrossAxisAlignment` {Start, Center, End, Stretch} via `set_cross_axis_alignment`. Row default Center (Python `vertical_alignment`); Column default Start (Python `horizontal_alignment`). Stretch fills cross size unless child has explicit width/height.
- Expand: `Control::set_expand(bool)` / `ControlOptions::expand` — leftover main-axis space shared equally among expand siblings (bool only; no flex weights yet). Intrinsic size still sums natural footprints.
- Pointer: `Control::hit_target` walks children back-to-front then self `hit_test`; `Page::dispatch_pointer` captures the deepest target (nested buttons work).
- `FilledButton::hit_test` uses the same effective corner radius as paint (`kMaxCornerRadius` / half min(w,h)); corner pockets use circle tests so round paint and hit agree.
- `clip_push` throws if stack exceeds `kMaxClipDepth` (no silent drop).
- Invalid layout size clears `layout_dirty_` (no per-frame no-op spin).

## Phase 4 status
- `Text` + `FilledButton` hello (pointer capture, SDF round fill/stroke)
- Caps: `kMaxTextLen` / `kMaxFillRects` throw, no silent truncate
- Hello track closed; layout widgets (`Row`/`Column`/`Container`) landed

## Font (TTF metrics)
- `saturn::Font` via vendored `third_party/stb_truetype.h`; bundled `assets/Inter-Regular.ttf`
  (OFL; instanced from Python `saturn/assets` Inter variable @ wght=400/opsz=14).
- Real advances / ascent / descent; on-demand atlas (ASCII preload) → `create_texture_rgba8` +
  `draw_textured_quads`. Caps: `kMaxFontPx`, `kMaxFontFileBytes`, `kMaxPathBytes`, `kFontAtlasDim`.
- `Text` / `FilledButton` use `default_font()` at 16px. `run()` calls `Font::load_default()` and
  **fails loud** if missing (`SATURN_FONT_PATH` or `assets/Inter-Regular.ttf` next to exe).
- 5x7 `bitmap_font.hpp` is **not** for pixel parity (kept as emergency reference only).

## Next goal (not done)
- First C++ demo should pixel-match Python `examples/demo.py` (screenshot compare against
  Windows true-GL golden `demo-opengl-win-944x761.png`). Full control port / parity pixels are **not** claimed here.
  `expand`/`CrossAxisAlignment` landed on Row/Column; MainAxisAlignment / flex weights still deferred.
