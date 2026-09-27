# Native desktop windows

`page.window` configures the existing desktop window. Assignments are queued on
the UI thread, so several size changes before the next frame are combined.
Window width/height include the native frame; `page.width` and `page.height`
are read-only client dimensions. Sizes and positions use logical pixels.

```python
import saturn


def main(page: saturn.Page):
    page.window.width = 960
    page.window.height = 640
    page.window.min_width = 480
    page.window.min_height = 320
    page.window.title = "My application"
    page.window.prevent_close = True

    async def window_event(event: saturn.WindowEvent):
        if event.type == saturn.WindowEventType.CLOSE:
            # Save application state here, then finish closing.
            event.page.window.destroy()

    page.window.on_event = window_event
    page.add(saturn.Text("Hello"))
    print(page.window.hwnd)


saturn.run(main)
```

## Properties

All 39 public Window property names inspected in installed Flet 1.0.1 are
available. Native behavior is implemented and tested on Windows. Saturn also
provides `title`, `hwnd`, and `native_handle`.

| Properties | Behavior |
| --- | --- |
| `width`, `height`, `min_width`, `min_height`, `max_width`, `max_height` | Outer window dimensions and native resize limits; `None` removes a limit |
| `left`, `top`, `alignment` | Position and alignment within the nearest monitor's work area; use `saturn.Alignment.CENTER` for centering |
| `aspect_ratio` | Positive width/height ratio for programmatic and native resize; incompatible bounds raise `ValueError` |
| `maximized`, `minimized`, `full_screen` | Change native state; getters read actual Windows/SDL state |
| `visible`, `focused` | Show/hide or request activation; the OS may restrict foreground activation |
| `resizable`, `minimizable`, `maximizable`, `movable` | Native resize capability, title-bar actions, and native movement |
| `always_on_top`, `always_on_bottom` | Native stacking; enabling both raises `ValueError` |
| `frameless`, `title_bar_hidden`, `title_bar_buttons_hidden` | Native frame, caption, and system buttons |
| `opacity`, `bgcolor`, `shadow`, `brightness` | Whole-window opacity, background/transparency, DWM shadow policy, and title-bar light/dark preference |
| `prevent_close`, `on_event` | Native close interception and typed window callbacks |
| `skip_task_bar`, `progress_bar`, `badge_label` | Native taskbar visibility, progress from 0 to 1, and a small text badge; `None` clears progress/badge |
| `icon`, `ignore_mouse_events` | Window icon path and native mouse pass-through |
| `data`, `key`, `page`, `parent` | Application metadata and Page ownership; `page`/`parent` are read-only |
| `title` | Shares state with `page.title` and the App startup title |
| `hwnd`, `native_handle` | Read-only integer native handles; `hwnd` is zero outside Windows or after destruction |

Unknown Window property assignments raise `AttributeError`, making misspellings
visible. Advanced Win32 properties raise `NotImplementedError` on other systems:
`aspect_ratio`, `minimizable`, `maximizable`, `movable`, `always_on_bottom`,
`skip_task_bar`, `title_bar_hidden`, `title_bar_buttons_hidden`, `shadow`,
`ignore_mouse_events`, `progress_bar`, and `badge_label`. Other native properties
use SDL; non-Windows behavior has not been covered by the Windows checks.

## Handles and transparency

`page.window.hwnd` returns the actual HWND from SDL, suitable for native Windows
integration. Native window operations belong to the UI thread; a handle does
not transfer ownership of the window or rendering resources to an event handler.

`page.bgcolor` overrides `window.bgcolor` for client painting. Otherwise the
window background overrides the theme's surface color.

```python
page.window.frameless = True
page.window.bgcolor = saturn.Colors.TRANSPARENT
page.bgcolor = saturn.Colors.TRANSPARENT
```

Windows transparency uses a color key: pixels matching the transparent
background RGB are removed. Whole-window `opacity` is supported separately.
This does not provide per-pixel desktop alpha composition, and matching opaque
content pixels are also removed by the color key.

## Events and methods

Assign one callback or a list to `window.on_event`. Handlers may be synchronous
or asynchronous. A `WindowEvent` exposes `type`, `name`, `control` (Window), and
`page`. `WindowEventType` includes close, focus/blur, show/hide,
maximize/unmaximize, minimize/restore, resize/resized, move/moved, and enter/leave
full screen. Continuous `RESIZE`/`MOVE` notifications use the Windows sizing loop;
completion and state changes use native SDL events. Duplicate unchanged
`RESIZED` notifications are suppressed.

Set `prevent_close = True` before a close request if an asynchronous handler
needs to decide whether to close. A handler is not awaited inside the native
close operation.

| Method | Use |
| --- | --- |
| `window.close()` | Queue a close request, emit `CLOSE`, and respect `prevent_close` |
| `window.destroy()` | Force application shutdown, including when close is prevented |
| `await window.center()` | Queue centering within the nearest monitor's work area |
| `await window.to_front()` | Queue native activation |
| `await window.wait_until_ready_to_show()` | Wait until earlier UI queue operations have run |
| `await window.start_dragging()` | Begin Windows caption dragging, if movement is enabled |
| `await window.start_resizing(saturn.WindowResizeEdge.BOTTOM_RIGHT)` | Begin Windows native resizing, if resizing is enabled |

Saturn keeps its existing synchronous `close()` and `destroy()` methods; these
two methods differ from Flet's awaitable methods. Other methods above are
awaitable. Dragging/resizing require a pointer interaction and run through the
Windows native loop.

## Verification

`python tests/window_checks.py` creates a real native window and checks handles,
titles, outer/client sizes, limits and their reset, frame styles, opacity and
color-key setup, taskbar progress/badge resources, fullscreen, maximize/minimize,
centering, queue readiness, and close interception. Native drag interactions
require a manual pointer test. Page callback scheduling is covered separately
by `tests/page_compatibility_checks.py`.

[Page compatibility](./page-properties-comparison.md) ·
[Renderer settings](./rendering.md) · [Documentation home](./README.md)
