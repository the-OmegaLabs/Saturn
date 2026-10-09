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
- `Control::attach` is protected; only `Page` (friend) attaches children

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
- `Page::layout` is a vertical column (padding/gap), not flex. Resize via `Window::consume_resized` triggers relayout.
- `clip_push` throws if stack exceeds `kMaxClipDepth` (no silent drop).
- Invalid layout size clears `layout_dirty_` (no per-frame no-op spin).

## Phase 4 status
- `Text` + `FilledButton` with embedded 5x7 bitmap font (ASCII subset)
- Page clips children to bounds (overflow cropped; no scroll yet)
- Pointer down/up routed to buttons
- Pointer: down hit-tests topmost child and captures; up goes only to capture (no broadcast).
- Glyph path: CPU atlas (16x8 cells of 8px, ASCII 0..127) uploaded once; one textured quad per character via `draw_textured_quads` (not per-pixel / not solid `fill_rects`).
- Caps: `kMaxTextLen` (4096) on text draw; `kMaxFillRects` (16384) on `fill_rects` / `draw_textured_quads` (throw, no silent truncate).
- Hello track closed; next knives are elsewhere (e.g. layout widgets) - not more ColorBox/hello churn.
