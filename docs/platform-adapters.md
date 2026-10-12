# Platform Adapters and the Win32 Split

Saturn currently uses Windows as its primary development environment, but the Linux work requires fixing the boundaries first: controls,
layout, theme, events, and rendering interfaces stay platform-independent; the window system, DPI, native dragging, the taskbar,
module monitoring, and GPU binding are implemented by platform adapters.

## The first step, already done

- `saturn/platform/base.py` defines `PlatformAdapter` and
  `PlatformCapabilities`.
- `saturn/platform/windows.py` centralizes Windows DPI, window rectangles, dark title bars,
  modal owner, real-time resize watch, and module enumeration.
- `saturn/platform/windows_native.py` centralizes Win32 window styles, transparency, dragging,
  resize, taskbar progress/badge, and COM resources.
- `saturn/platform/windows_gl.py` centralizes WGL GPU affinity/association.
- `saturn/platform/linux.py` and `saturn/platform/other.py` provide extensible empty adapters;
  Linux already has a `/proc/self/maps` module snapshot.
- `saturn/_native_window.py` is kept as a compatibility forwarder for old private imports and no longer carries implementation.
- `App`, `Window`, `Page`, `Subpage`, `WindowDragArea`, color preferences, and module monitoring
  already access platform capabilities through the adapters.

## Code constraints

Public core code should not directly contain `ctypes.windll`, `ctypes.WinDLL`, `winreg`,
`WGL`, or `sys.platform == "win32"`. Platform detection lives only in
`saturn/platform/__init__.py`; platform-native libraries are lazily loaded only in their corresponding adapters.

The correct way to call a capability is:

```python
platform = app.platform
if platform.supports("native_window_dragging"):
    await page.window.start_dragging()
```

Wayland does not allow simulating window positioning, global input, or layer-shell capabilities. Adapters should return
an explicit unsupported state, or make the public API raise an understandable `NotImplementedError`.

## Next Linux steps

1. First verify that SDL Software/OpenGL can create, resize, take input, render fonts, and handle multi-monitor windows
   on Ubuntu and Fedora, under both X11 and Wayland.
2. Implement common capabilities in `linux.py`, then add `linux_x11.py` and
   `linux_wayland.py` as needed; do not mix the two protocols into the core window classes.
3. Put the clipboard, file selection, notifications, tray, and desktop entries in the services layer, preferring
   xdg-desktop-portal, D-Bus, and standard desktop protocols.
4. Put the panel, launcher, settings center, and notification center in the shell layer; keep a full compositor, lock screen,
   session, and permission boundaries in separate processes.

For the full feasibility assessment, roadmap, test matrix, and desktop environment scope, see the
[Linux desktop roadmap](./linux-desktop-roadmap.md).
