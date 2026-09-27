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
new raster scale. Vulkan may rebuild its swapchain and offscreen frame target.

## Backend behavior

| Backend | `anti_aliasing` | `vsync` |
| --- | --- | --- |
| OpenGL | Enables additional 2× offscreen supersampling at display densities below 1.5; otherwise uses native display density | Requests SDL's GL swap interval; driver overrides are possible |
| Vulkan | Matches OpenGL: additional 2× offscreen supersampling below display density 1.5, otherwise native density; GPU linear reduction includes SVG, text and texture detail | Uses FIFO when enabled; when disabled prefers immediate, then mailbox, then FIFO |
| Software | Enables additional 2× raster supersampling below display density 1.5 | Uses application pacing at the display refresh rate; no native swap synchronization |

Disabling antialiasing removes the additional sampling above. Font smoothing,
SVG rasterization, texture filtering, and analytic shape edge coverage remain
part of their drawing paths. On a Vulkan device without immediate presentation,
disabling `vsync` may still use synchronized mailbox or FIFO presentation.
With `vsync=False`, active updates have no application refresh cap; idle input
polling waits briefly to avoid spinning a CPU core.

## Active renderer

`page.renderer.name` is the read-only name of the current backend:
`"software"`, `"opengl"` or `"vulkan"`. It reads the active context, rather
than the requested startup setting. It is available inside `main(page)` and
event handlers; before a native window starts, it returns `None`. A Subpage
reports its own window's backend.

```python
print(self.page.renderer.name)  # "vulkan", for example
```

## GPU selection

Select the GPU at startup with a device name or a zero-based index:

```python
saturn.run(main, backend=saturn.Renderer.VULKAN, gpu="Intel")
saturn.run(main, backend=saturn.Renderer.VULKAN, gpu=1)
saturn.run(main, backend=saturn.Renderer.OPENGL, gpu="NVIDIA")
```

Omitting `gpu`, or passing `None`, preserves default selection. Vulkan prefers
a compatible discrete GPU, then an integrated GPU; OpenGL uses SDL's driver
default. Names are case-insensitive: an exact match wins, otherwise a unique
substring is accepted. Ambiguous or unavailable choices fail GPU initialization;
the application prints the fallback notice below and starts software rendering.
It never silently substitutes a different GPU. Invalid selector types, empty
names and negative indices raise immediately. Software rejects explicit GPUs.

| Backend | Explicit device selection |
| --- | --- |
| Vulkan | Selects from physical devices that support graphics, presentation and the window's swapchain. |
| Windows OpenGL | Uses `WGL_NV_gpu_affinity` or `WGL_AMD_gpu_association` when the driver exposes it. Offscreen frames are copied/blitted between GPU contexts for window presentation, without CPU readback. |
| OpenGL without these extensions, including other platforms | Can identify and accept the current device; requests for another device trigger software fallback. Configure the OS/driver graphics preference before startup or use Vulkan to choose another adapter. |

The actual device and available choices are read-only:

```python
print(page.renderer.gpu_name)   # Actual renderer device, not the request string
print(page.renderer.gpu_index)  # Index into gpus, if identifiable
print(page.renderer.gpus)       # Tuple of backend-compatible device names
```

Before startup, these return `None`, `None`, and `()` respectively. Software
uses the same empty values. OpenGL drivers without selection extensions expose
only their current device. Indices depend on driver enumeration and can change
after hardware/driver updates; names are preferable for saved configuration.
Device selection is fixed for the lifetime of a window.

On the development laptop, Vulkan selection, screenshots and resize were
verified on both NVIDIA GeForce RTX 5070 Laptop GPU and Intel(R) Graphics.
OpenGL default/name/index selection and multiple native windows were verified
on NVIDIA. Its driver does not expose either selection extension, so the
alternate-device NVIDIA/AMD OpenGL presentation paths remain unverified on
hardware with those extensions.

Try `python examples/gpu_selection.py --backend vulkan --gpu Intel`.
Run `python tests/gpu_selection_checks.py` for matching, startup forwarding,
failure recovery, real rendering on each selectable device and child-window
GPU isolation/inheritance.

## Renderer and font events

If GPU window/context/device initialization fails, Saturn releases that window
and creates a software window with the same title, dimensions and position.
The console prints this exact notice:

```text
Saturn can't use your current GPU, fallback to software renderer.
```

Register handlers inside `main(page)`. Notifications are sent after the entry
function finishes (after awaiting an async entry function), so handlers can be
installed even when the fallback happened before `main` started:

```python
def main(page):
    page.on_render_failed = lambda e: print(e.message, e.backend, e.gpu, e.error)
    page.on_render_ready = lambda e: print(e.backend, e.gpu_name, e.fallback)
    page.on_font_optimize = lambda e: print(e.font, e.weight, e.status, e.error)
```

| Handler / event | When and payload |
| --- | --- |
| `on_render_failed` / `RenderFailedEvent` | Once after failed GPU initialization and successful software recovery. `backend` and `gpu` identify the failed request; `error` contains the reason, `message` is the notice above, `fallback` is `"software"`. |
| `on_render_ready` / `RenderReadyEvent` | Once after initialization, including recovery. `backend`, `gpu_name`, `gpu_index` describe the actual renderer; `fallback` is a boolean. Delivered after the failure handler finishes. |
| `on_font_optimize` / `FontOptimizeEvent` | Background font work starts and ends. `status` is `"started"`, `"completed"` or `"failed"`; `success` is `None`, `True` or `False`; `font`, `weight`, `error`, `cached` describe the work. `operation="instance"` builds a font weight, `operation="load"` downloads/validates/caches an HTTP font (`weight=None`). |

All three support one callback, callback lists, zero arguments, one event
argument, and async callbacks. Sync callbacks run in workers; async callbacks
are awaited on the application loop. Font notifications are serialized so
completion cannot overtake a slow async start handler. Cached/shipped fonts
produce no optimization events because no background work runs. Shared font
cache jobs notify all active Pages in the application; completion also requests
layout and redraw. Closed Pages do not receive these notifications.

Fallback covers initialization, including Subpages. It does not switch renderers
after runtime draw failures, and shader compilation failures keep the existing
`Shader.error` behavior. Software cannot render custom GLSL; use a shader's
`fallback_color` when software fallback needs a visible placeholder.

Run `python tests/renderer_event_checks.py` to check recovery pixels, native
child inheritance, sync/async notification order and font success/failure paths.

## Renderer context

`page.renderer.context` is the active backend renderer object. It is read-only;
the backend itself is selected through `saturn.run(..., backend=...)`.

```python
context = page.renderer.context
name = page.renderer.name
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
creation disabled. Vulkan uses a single-sample offscreen attachment with whole-frame
supersampling rather than MSAA. `python -m tests.vulkan_supersampling_checks`
compares SVG, text, fractional positions and clipping against OpenGL, checks
antialiasing toggles and DPI changes, and checks cached image edges and frame replacement.

After changing the Vulkan fragment source or shared `renderer/wave.glsl`, rebuild
the checked-in shader with a developer-installed Khronos glslang compiler:

```powershell
glslang -V -S frag saturn/renderer/vulkan_frag.glsl -o saturn/renderer/vulkan_frag.spv
```

Applications load the packaged SPIR-V; no shader compiler is needed at runtime.

[Documentation home](./README.md)
