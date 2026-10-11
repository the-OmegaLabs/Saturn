"""Portable platform contracts used by Saturn's desktop runtime."""
from __future__ import annotations

from dataclasses import dataclass
import os

import pygame


@dataclass(frozen=True)
class PlatformCapabilities:
    """Capabilities that cannot be inferred reliably from SDL alone."""

    native_window: bool = False
    hwnd: bool = False
    native_window_dragging: bool = False
    native_window_resizing: bool = False
    window_frame_metrics: bool = False
    live_resize_watch: bool = False
    dark_title_bar: bool = False
    modal_owner: bool = False
    module_watch: bool = False


class PlatformAdapter:
    """Portable defaults and the extension point for another OS backend.

    SDL remains responsible for ordinary window creation and input.  This
    adapter owns only operations that need an OS API or a platform-specific
    event hook.  A future Linux adapter can implement the same methods without
    adding Linux branches to ``App`` or ``Window``.
    """

    name = "generic"
    is_windows = False
    capabilities = PlatformCapabilities()

    def supports(self, capability: str) -> bool:
        return bool(getattr(self.capabilities, capability, False))

    def supports_window_feature(self, name: str) -> bool:
        """Return whether a legacy Window property is native on this host.

        The initial split keeps the old Windows-only contract intact.  Linux
        and other adapters can later opt into individual properties without
        changing the public ``Window`` implementation.
        """
        return False

    def prepare_environment(self) -> None:
        """Set portable SDL environment defaults before video initialization."""
        os.environ.setdefault("SDL_IME_SHOW_UI", "1")

    def system_prefers_dark(self) -> bool:
        """Return the host's dark-mode preference when it has one."""
        return False

    def snapshot_modules(self) -> list[str]:
        """Return loaded native module paths for the optional watchdog."""
        return []

    def create_gl_gpu_binding(self, context, gpu):
        """Return the platform's optional explicit OpenGL GPU binding.

        Most platforms use the context selected by SDL/ModernGL directly.
        The small default binding keeps the renderer's lifecycle uniform while
        leaving WGL, GLX and any future native GPU-selection APIs in their
        platform adapters.
        """
        return _DefaultGLBinding(context, gpu)

    # -- window identity and display metrics ----------------------------
    def create_native_window(self, owner):
        """Create an optional native helper for a Saturn ``Window``."""
        return None

    def native_handle(self, window) -> int:
        """Return SDL's native handle where pygame exposes one."""
        try:
            native = getattr(window, "handle", 0)
            return int(native) if native else 0
        except (AttributeError, TypeError, ValueError, pygame.error):
            return 0

    def hwnd(self, window) -> int:
        """Return an HWND-like handle, or zero when the host has no HWND."""
        return self.native_handle(window) if self.supports("hwnd") else 0

    def system_pixel_ratio(self) -> float:
        return 1.0

    def window_pixel_ratio(self, handle: int) -> float:
        return self.system_pixel_ratio()

    def window_rects(self, window):
        """Return ``(outer, client)`` native rectangles, if available."""
        return None

    def work_area(self, window):
        """Return the active work area in physical pixels.

        SDL exposes a conservative primary-display fallback.  Native adapters
        can override this with the monitor containing the current window.
        """
        try:
            sizes = pygame.display.get_desktop_sizes()
        except (AttributeError, pygame.error):
            sizes = ()
        if sizes:
            width, height = sizes[0]
        else:
            try:
                width, height = pygame.display.get_window_size()
            except (AttributeError, pygame.error):
                width, height = (0, 0)
        return (0, 0, width, height)

    # -- optional native behavior ---------------------------------------
    def set_default_window_icon(self, window) -> bool:
        return False

    def set_dark_title_bar(self, hwnd: int, dark: bool) -> bool:
        return False

    def set_window_owner(self, child_hwnd: int, parent_hwnd: int, modal: bool) -> bool:
        """Set native ownership; return False when SDL fallback is needed."""
        return False

    def enable_window(self, hwnd: int, enabled: bool) -> bool:
        return False

    # -- event-loop hooks ------------------------------------------------
    def install_live_resize_watch(self, app) -> None:
        return None

    def remove_live_resize_watch(self, app) -> None:
        return None


class _DefaultGLBinding:
    """No-op OpenGL binding used when SDL owns context selection."""

    def __init__(self, context, gpu):
        from ..renderer.gpu import select_gpu

        self.default_context = context
        self.current_name = context.info.get("GL_RENDERER", "OpenGL")
        self.names = (self.current_name,)
        self.index = select_gpu(self.names, gpu)
        self.render_rc = None

    def activate(self):
        return None

    def activate_default(self):
        return None

    def __enter__(self):
        self.activate()
        return self

    def __exit__(self, *args):
        return None

    def release(self):
        return None

    def close(self):
        return None
