# Renderer settings

Select a backend when starting the application. Configure its rendering options
through `page.renderer` in the entry function:

```python
import saturn


def main(page: saturn.Page):
    page.window.width = 960
    page.window.height = 800
    page.renderer.anti_aliasing = True
    page.renderer.vsync = True
    page.add(saturn.Text("Hello"))


saturn.run(main, backend=saturn.Renderer.VULKAN)
```

Both options default to `True` and accept boolean values. They can also be
changed after startup. Changes are queued and combined on the UI thread before
the next frame; reading a setting returns the requested value immediately.
Changing antialiasing invalidates layout so text and control textures use the
new raster scale. Vulkan may rebuild its swapchain and sampling attachments.

## Backend behavior

| Backend | `anti_aliasing` | `vsync` |
| --- | --- | --- |
| OpenGL | Enables additional 2× offscreen supersampling at display densities below 1.5; otherwise uses native display density | Requests SDL's GL swap interval; driver overrides are possible |
| Vulkan | Enables supported 4× or 2× MSAA, falling back to 1×, and higher resolution text rasterization; coverage meshes smooth lines/arcs even at 1× | Uses FIFO when enabled; when disabled prefers immediate, then mailbox, then FIFO |
| Software | Enables additional 2× raster supersampling below display density 1.5 | Uses application pacing at the display refresh rate; no native swap synchronization |

Disabling antialiasing removes the additional sampling above. Font smoothing,
SVG rasterization, texture filtering, and analytic shape edge coverage remain
part of their drawing paths. On a Vulkan device without immediate presentation,
disabling `vsync` may still use synchronized mailbox or FIFO presentation.
With `vsync=False`, active updates have no application refresh cap; idle input
polling waits briefly to avoid spinning a CPU core.

## Active renderer

`page.renderer.context` is the active backend renderer object. It is read-only;
the backend itself is selected through `saturn.run(..., backend=...)`.

```python
context = page.renderer.context
requested = page.renderer.vsync
actual_native_sync = context.vsync_active
```

The renderer's `anti_aliasing` and `vsync` fields reflect applied options;
`vsync_active` reports native synchronization, excluding application pacing.
Vulkan also exposes `present_mode` for inspection. These values may lag a newly
requested change until the UI queue is processed. Native synchronization reports
the configured API state; it does not measure the monitor's actual scanout.

Rendering operations and GPU resources belong to the UI thread. Entry functions
and event handlers run on worker threads, so obtaining the object does not make
direct GPU calls from those handlers safe. Ordinary controls should use
`page.update()` to request a redraw.

Run `python tests/renderer_options_checks.py` to verify option dispatch, Vulkan
presentation fallbacks, sampling changes, resize, and pixels on all three backends.

## Dynamic GPU drawing

Both OpenGL and Vulkan rasterize the frame on the GPU. Adjacent compatible
primitives preserve drawing order while sharing vertex batches and textures.
The existing controls now use these GPU paths:

- `LoadingIndicator`: an adaptive polygon mesh with interpolated edge coverage.
- Linear/circular wavy progress: analytic shader strokes without frame bitmaps.
- Material elevation shadows: an analytic Gaussian coverage approximation,
  including corner radii, without new blurred textures during resize.
- Icon and image color changes: reuse source textures and apply tint/opacity
  in the GPU; bitmap enlargement uses native texture sampling.

The CPU still constructs geometry, decodes images, rasterizes fonts and SVGs
when needed, and smoothly reduces large bitmaps. These cached source operations
are separate from full-frame rendering. Software retains bitmap drawing.
Analytic elevation shadows approximate the original blur rather than matching
every pixel exactly; custom `Container.shadow` uses its existing primitive path.

`python -m tests.dynamic_renderer_checks --stress` checks rendered silhouettes,
clipping, opacity, resize, tint texture reuse, and animations with CPU bitmap
creation disabled. It also forces Vulkan to 1× while requesting antialiasing;
the local diagonal/arc checks produce 178/224 blended edge pixels.

After changing the Vulkan fragment source or shared `renderer/wave.glsl`, rebuild
the checked-in shader with a developer-installed Khronos glslang compiler:

```powershell
glslang -V -S frag saturn/renderer/vulkan_frag.glsl -o saturn/renderer/vulkan_frag.spv
```

Applications load the packaged SPIR-V; no shader compiler is needed at runtime.

[Documentation home](./README.md)
