# Design snapshot

Synced with group agreement (Saturn room). Update this when constraints change.

## Non-goals (phase ①–④)
- Parallel Software / Vulkan backends
- `saturn.web` port
- Flet-compatible wide kwargs surface
- Shipping Material icon mega-tables

## Security (审查者)
- Memory/bounds ownership rules in headers
- Resource validation before GPU/file use
- Web (future): auth, origins, max_message_bytes, resume token lifetime first-class

## Quality (锐评者)
- Do not copy Python `**base` / Unpack sticker pattern
- Explicit options + nullable size contracts written once
- Hello before API width

## Mapping from Python (reference only)
| Python | C++ target |
|--------|------------|
| `saturn.app` / `run` | `saturn::App`, `saturn::run` |
| `saturn.page.Page` | `saturn::Page` |
| `saturn.control.Control` | `saturn::Control` |
| `saturn.renderer.*` | `saturn::Renderer` + `OpenGLRenderer` |
| SDL via pygame-ce | SDL3 directly |
