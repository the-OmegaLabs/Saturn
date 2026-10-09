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
- `Row` / `Column`: own children via `unique_ptr` + `add()`; explicit `spacing` ctor arg (no kwargs); `kMaxChildren` cap; intrinsic = sum main-axis + gaps, max cross-axis; left/top aligned (no flex expand yet).
- Pointer: `Control::hit_target` walks children back-to-front then self `hit_test`; `Page::dispatch_pointer` captures the deepest target (nested buttons work).
- `FilledButton::hit_test` uses the same effective corner radius as paint (`kMaxCornerRadius` / half min(w,h)); corner pockets use circle tests so round paint and hit agree.
- `clip_push` throws if stack exceeds `kMaxClipDepth` (no silent drop).
- Invalid layout size clears `layout_dirty_` (no per-frame no-op spin).

## Phase 4 status
- `Text` + `FilledButton` with embedded 5x7 bitmap font (ASCII subset)
- `FilledButton` paints SDF rounded fill + 1px inside stroke (default radius 8; `set_corner_radius`)
- Page clips children to bounds (overflow cropped; no scroll yet)
- Pointer down/up routed to buttons
- Pointer: down hit-tests topmost child and captures; up goes only to capture (no broadcast).
- Glyph path: CPU atlas (16x8 cells of 8px, ASCII 0..127) uploaded once; one textured quad per character via `draw_textured_quads` (not per-pixel / not solid `fill_rects`).
- Caps: `kMaxTextLen` (4096) on text draw; `kMaxFillRects` (16384) on `fill_rects` / `draw_textured_quads` (throw, no silent truncate).
- Hello track closed; layout widgets (`Row`/`Column`) landed as phase-5 start.

## Next goal (not done)
- First C++ demo should pixel-match Python `examples/demo.py` (screenshot compare). `Row`/`Column` + rounded hit are on that path; full demo port / Container / scroll / parity pixels are **not** claimed here.
