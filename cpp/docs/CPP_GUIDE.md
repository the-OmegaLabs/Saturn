# Saturn C++ Usage And Rendering

## Current Stack

- C++20, CMake, SDL3 window/events/input and GL context management.
- Native OpenGL 3.3 core, GLSL 330, VAO/VBO, textures, scissor clipping.
- `Renderer` is the abstraction; this phase implements OpenGL only.
- `stb_image` decodes bounded PNGs on CPU; `stb_truetype` rasterizes bounded
  cached glyph atlases on CPU. `stb_image_write` encodes diagnostic screenshots.
- No Python interpreter, Flet, browser, Qt, Skia or SDL software renderer is
  involved in the C++ application.

## Antialiasing

- Rounded shapes, arcs, ripples and the Saturn vector mark use analytic GPU
  coverage based on `fwidth(distance)`. Coverage follows framebuffer pixel
  density rather than a fixed two-logical-pixel blur.
- `SaturnLogo` draws a contained brand shape matching
  `.static/saturn-mark-white.svg` in one quad/draw call. No per-frame bitmap
  generation, image upload or framebuffer-sized intermediate allocation.
- PNG image textures use trilinear mipmaps, generated on the GPU once per
  upload. Texture RGB is premultiplied before filtering to prevent dark
  transparent-edge fringes. Uploaded source bytes remain straight RGBA.
- Font atlases use cached 2x glyph rasterization and bilinear filtering;
  font atlases do not generate mipmaps, which could bleed adjacent glyphs.
- This is not FXAA/TAA, full-frame SSAA or a software render path. It cannot
  reconstruct detail missing from an arbitrary low-resolution photograph.
- Mipmaps add approximately one third of base texture storage. Source dimensions
  and pixel count remain capped; no per-frame mipmap regeneration.

## CPU And GPU Work

CPU:

- Events, callbacks, tree ownership, layout, hit-testing and tween evaluation.
- First-use PNG decoding and glyph rasterization, vertex submission and uploads.
- Screenshot readback/encoding during diagnostics, not normal rendering.

GPU:

- Vertex transformation, rasterization, shape coverage, ripple masks, texture
  filtering, color tint, alpha compositing and final framebuffer writes.

Pixel rendering is performed on the GPU. Which processor limits throughput
depends on the workload: many small draws/layout changes can be CPU/driver
limited; large overdraw or shader-heavy scenes can be GPU limited. No claim
that the complete demo is CPU-bound or GPU-bound is justified by a logo-only
microbenchmark. The current event loop also includes an explicit 16ms delay.

## Recommended Style

Use `saturn::run` to install the default font and run the native event loop.
`Page` owns top-level controls; containers own descendants via `unique_ptr`.
Configure explicit `ControlOptions`, then transfer ownership with `std::move`.
Prefer typed callbacks and setters to generic property dictionaries.

```cpp
#include "saturn/app.hpp"
#include "saturn/control.hpp"
#include "saturn/page.hpp"
#include <memory>

int main() {
  return saturn::run([](saturn::Page& page) {
    page.set_title("My App");
    page.set_padding(24.f);
    auto column = std::make_unique<saturn::Column>(16.f);
    auto text = std::make_unique<saturn::Text>("Ready");
    // Non-owning observer; Column owns Text for the callback lifetime.
    saturn::Text* output = text.get();
    column->add(std::move(text));
    column->add(std::make_unique<saturn::FilledButton>(
        "Run", [output] { output->set_value("Done"); }));
    page.add(std::move(column));
  }, 640, 480);
}
```

The complete built example is `cpp/examples/counter.cpp` (`saturn_counter`).
For a logo:

```cpp
saturn::ControlOptions size;
size.width = 104.f;
size.height = 84.f;
column->add(std::make_unique<saturn::SaturnLogo>(
    saturn::colors::kPrimary, size));
```

Rules:

- Raw control pointers are observers, never owners. Do not retain them after
  removing their owning tree. Prefer `unique_ptr`; use `shared_ptr` only for
  genuinely shared state and document why.
- Callbacks run on the C++ event-loop thread today. Avoid blocking work there;
  do not mutate the UI from worker threads without an explicit dispatch API.
- Window dimensions passed to `run` are logical client dimensions, not outer
  Windows frame dimensions. Layout/hit-testing use logical coordinates;
  readback uses actual framebuffer pixels.
- Bounds and untrusted asset validation remain mandatory. Sources are UTF-8
  without BOM. C++ is a typed API, not a lossless Python kwargs port.
- `Text::set_value`, layout setters and `Page::update` invalidate layout.
  Construct child trees before attaching them when possible.

## Build And Verification

```text
cmake -S cpp -B cpp/build -DCMAKE_PREFIX_PATH=<SDL3-devel-path> -DBUILD_TESTING=ON
cmake --build cpp/build --config Release
ctest --test-dir cpp/build -C Release --output-on-failure
cpp/build/Release/saturn_counter.exe
cpp/build/Release/saturn_antialias_tests.exe cpp/build/Release/antialias-sheet.png
```

`saturn_antialias_tests` checks real OpenGL pixels: transparent filtering,
smooth edges with a solid stroke core, a clean mark interior, and non-finite
input rejection. It prints GL vendor renderer/version and optional elapsed
GPU queries. Timing excludes warmup/texture decoding and is not a complete-app
profile. Use `SATURN_SHOT` for a demo capture; normal rendering does not read
framebuffer pixels back to the CPU.

On October 10, 2026, the local Intel Iris Xe driver reported OpenGL 3.3.0.
A 100-mark test over 30 frames after pipeline warmup measured about
0.116ms CPU submission and 0.336ms elapsed GPU query per frame in the final
run (observed earlier runs varied with system load). GPU elapsed queries may include
submission gaps; these are observed microbenchmark values, not FPS guarantees
or a full-app CPU/GPU utilization measurement.
