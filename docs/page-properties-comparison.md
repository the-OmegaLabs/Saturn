# Page compatibility and remaining differences

Reviewed on **2026-09-27** against installed **Flet 1.0.1**. The ordinary desktop Page problems from the earlier audit are now repaired. This document describes implemented behavior; it does not claim complete Flet compatibility.

## Completed repairs

| Area | Saturn now supports | Verification |
| --- | --- | --- |
| Keyboard and resize events | One callback or a callback list; typed key/modifier and logical size payloads; sync/async callbacks accepting zero or one argument | Payload fields, callback lists, and actual App worker/async-loop dispatch |
| `controls` and `overlay` | Direct replacement or append followed by `update()` attaches additions. Removal detaches descendants and clears obsolete focus, press, hover, and animation targets | Top-level mutation, retained attachment counts, subtree removal, and focus cleanup |
| `padding` | Numeric, `Padding`, and `None` values; each edge participates independently in root layout | Actual rendered asymmetric and zero-padding layouts |
| `theme`, `dark_theme`, `theme_mode` | Dark mode selects `dark_theme` when available, otherwise `theme`; SYSTEM follows the detected platform preference. Changes refresh font/layout/color state | Light/dark selection, in-place theme mutation, and system-change events |
| `fonts` | Local files/assets and HTTP(S) URLs; assignment or dictionary mutation plus `update()` refreshes aliases and text caches. Download completion requests layout and redraw | Changed font produces different geometry and pixels; real HTTP download, extensionless URL, ready notification, and cache reuse |
| `title` and `window.title` | Both access the same startup/window title | Startup title and updates through both access paths |
| Window state | Native state readback and events synchronize minimized, maximized, fullscreen, focus, and visibility behavior | See [Native windows](./window.md) and native window checks |
| `disabled` | Blocks control and overlay pointer, keyboard, IME, and wheel input; clears existing focus/press/hover | Focused input and overlay hit testing while disabled; input resumes after enabling |
| `services` | Registering through the list and calling `update()` assigns the owning Page; removal clears ownership | FilePicker ownership and removal |
| Platform brightness and density | `platform_brightness`, change events, and measured `media.device_pixel_ratio` | System preference change and logical/device pointer conversion |

Fonts and event behavior were implemented in Saturn after inspecting Flet's installed API and dispatcher. Flet implementation code was not copied into these changes.

## Event migration

Page callbacks now receive an **event**, including callbacks registered with the existing list syntax. Access the owning Page through `event.page`:

```python
def resized(event):
    print(event.width, event.height, event.page.title)

page.on_resize = resized
page.on_keyboard_event = lambda event: print(event.key, event.ctrl)

# Existing registration style remains available.
page.on_resize = [resized]
page.on_resize.append(lambda event: print(event.page.width))
```

Earlier Saturn callbacks received Page directly. Replace `current_page.width` with `event.width` or `event.page.width`. Handlers run off the UI thread through reusable workers or the application async loop. They can update controls and call `page.update()`; direct SDL/GPU operations require the UI thread. Native close interception belongs to `page.window.on_event` and `prevent_close`, described in the [window guide](./window.md).

## Meaningful remaining differences

| Area | Current boundary | Guidance |
| --- | --- | --- |
| Service registration | Saturn uses an explicit `page.services` list. Flet uses a contextual internal registry; matching one service's API does not provide every Flet service | Append an existing Saturn service and call `page.update()` |
| Asset resolution | Relative font paths resolve from the working directory, then `assets/`. Saturn has no Flet `assets_dir` startup option | Use absolute paths when packaging or when the working directory can change |
| Font downloads | HTTP fonts load asynchronously with fallback text while loading; the URL determines a persistent cache key. Downloads have a 20-second timeout and 32 MiB limit | Change the URL to refresh remote font content. A failed download warns and keeps fallback rendering |
| Brightness | Saturn exposes `"light"` / `"dark"` strings. SYSTEM detection currently reads Windows application-theme settings, checked approximately once per second | Compare strings; explicitly choose LIGHT/DARK on other platforms when needed |
| Media metrics | `page.media` currently provides the measured `device_pixel_ratio` only | Do not assume the full Flet MediaData field set is present |
| Root scrolling | Page has no root `scroll` / `auto_scroll` implementation | Put content in the existing `ListView` |
| Root effects | Root positioning, rotation, scale, and `animate_*` are not Page geometry APIs. General rotation/scale raster transforms are also incomplete on child controls. Root `visible` and `opacity` affect the main tree; background clearing and overlays are separate | Use supported child offset, opacity, size, and position animations. Use `page.window.visible` / `.opacity` for native whole-window behavior |
| Navigation and accessibility | Flet views/routes, navigation slots, and accessibility semantics remain separate feature work | Treat these as application-specific additions, rather than implicit Page compatibility |

`page.width` and `page.height` remain read-only **client** dimensions. Set native outer dimensions through `page.window.width` and `.height`. Native constraints, position, stacking, close handling, framing, and `hwnd` are implemented separately; see the [window guide](./window.md) for their platform/backend limits.

Renderer configuration remains a Saturn extension: `page.renderer.anti_aliasing`, `.vsync`, and `.context`. See [Renderer settings](./rendering.md).

## Evidence and acceptance checks

The focused checks pass on the current working implementation:

```powershell
python tests/page_compatibility_checks.py
python tests/flet_api_checks.py
```

The Page suite covers event payloads and dispatch, attachment/removal, services, disabled input, theme selection, actual software-rendered font/padding changes, generated TTC/WOFF fonts, and a real local HTTP font server. The Flet check verifies shared exported classes and common constructor/property behavior; it reports unsupported control parameters and is not a complete frontend equivalence test.

Sources: [Page](../saturn/page.py), [events](../saturn/event.py), [font loading](../saturn/text.py), [services](../saturn/services.py), [native windows](../saturn/window.py), and installed Flet `controls/page.py`, `controls/base_page.py`, `controls/core/window.py`, and `controls/services/service.py`.

[Page guide](./page.md) · [Documentation home](./README.md) · [Startup comparison](./run-comparison.md)
