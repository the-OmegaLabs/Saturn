# Saturn C++ - agent notes

Audience: coding agents. Humans: skim constraints only.

## Goal
Rewrite Saturn desktop core in C++. API may resemble Python Saturn/Flet shapes later; **no** lossless port promise. Prefer agent-parseable structure over pretty prose in code.

## Locked constraints (do not reopen without user + review)
1. Stack: SDL3 window/events → `Renderer` abstract → **OpenGL only** this phase. No Software/Vulkan/web in tree yet.
2. Ownership: every owning pointer documents who frees; containers own children; no raw shared ownership without `std::shared_ptr` and a comment why.
3. Bounds: text/input buffers, event queues, layout allocations have explicit caps (see `saturn/limits.hpp`). Unconstrained layout sizes (`nullopt`) must not allocate unbounded memory.
4. Untrusted inputs: fonts, images, FilePicker paths, GLSL - validate format + path escape before pipeline. Custom shaders = untrusted.
5. `ControlOptions`: explicit struct. Open fields (`data`, urls) typed or opaque - never `any`/`void*` dump without tag.
6. Phases 1-4: **hello runs only**. Do not expand Flet-wide widget surface before hello works.
7. Do not vendor giant icon/gen dumps or treat Python Windows-only behavior as truth.

## Phase map
| # | Deliverable |
|---|-------------|
| 1 | SDL3 window + event loop + **real** clear/flip empty frame (GL clear color) |
| 2 | `Renderer` fill/stroke/clip/blit + fuller OpenGL impl |
| 3 | `Control` / `Page` / dirty layout (tighten `attach`) |
| 4 | `Text` + `FilledButton` - hello |
| 5 | `Row` / `Column` / `Container` |
| 6 | more controls as needed |

## Layout
```
cpp/
  CMakeLists.txt
  include/saturn/   public headers
  src/              implementations
  docs/             agent + design notes (this file)
```

## Code style for agents
- Headers declare intent; `.cpp` stay dense OK.
- One concept per file when possible.
- Comments: contracts, ownership, caps - not narration.
- Prefer `std::optional`, `std::span`, `std::string_view`; C++20.
- Prefer `unique_ptr` for owned impls; do not use naked `new`/`delete` for renderer impl.

## Encoding
- Sources are UTF-8 **without BOM**. Do not reintroduce BOM (MSVC CP936 temptation).
