# Saturn Platform Adapter Layer

This directory is the boundary between Saturn and the operating system's native
APIs. The core UI, public window API, and renderers only call `PlatformAdapter`
and must not import Win32, X11, Wayland, D-Bus, or platform dynamic libraries
directly.

## Layout

| File | Responsibility |
| --- | --- |
| `base.py` | Cross-platform interface, capability table, and no-op default implementations |
| `__init__.py` | Selects the adapter for the running platform and caches the instance |
| `windows.py` | DPI, window rectangles, title bars, modal owners, module monitoring, and the Win32 resize hook |
| `windows_native.py` | Win32 window styles, transparency, taskbar, drag-and-drop, resizing, and subclass callbacks |
| `windows_gl.py` | WGL GPU affinity/association and cross-context presentation |
| `linux.py` | Linux adapter placeholder plus `/proc` module snapshots |
| `other.py` | Safe fallback for macOS, BSD, and headless test environments |

## Usage

```python
from saturn.platform import get_platform

platform = get_platform()
if platform.supports("window_frame_metrics"):
    # use platform-provided native window frame metrics
    ...
```

Features must be queried through the capability table instead of checking
`sys.platform` in public modules. Unsupported features should return an empty
result, fall back to SDL, or raise a `NotImplementedError` with a
platform-specific explanation; never fake a native success.

## Linux Integration Order

The first Linux milestone only needs ordinary top-level windows: an SDL window,
input, Software/OpenGL rendering, and basic DPI/resize handling. After that,
split by display protocol:

```text
saturn/platform/linux.py          generic Linux capabilities
saturn/platform/linux_x11.py      X11/EWMH/ICCCM
saturn/platform/linux_wayland.py  Wayland/XDG
```

Shell capabilities such as panels, desktop backgrounds, and a notification
center must not be crammed into the ordinary window adapter; they belong in a
separate services/shell layer using layer-shell, D-Bus, and
xdg-desktop-portal.

## Rules for Adding Platform Capabilities

1. Add a capability flag to `PlatformCapabilities` and provide default behavior
   in `PlatformAdapter`.
2. Implement the behavior in the corresponding platform file; do not put native
   library imports at the top level of core modules.
3. Call adapter methods only from `Window`, `App`, or the renderers.
4. Keep software/SDL fallbacks and clear errors for platforms that do not
   support a capability.
5. Run at least the Software smoke test, `compileall`, and the target
   platform's window lifecycle tests.
