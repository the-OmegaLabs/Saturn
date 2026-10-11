"""Platform capability and native-window adapters.

The UI and renderer layers use this module as the boundary between portable
Saturn behavior and operating-system APIs.  Platform modules are imported
lazily so importing Saturn on Linux, macOS, or a headless test host never
loads Win32 DLLs.
"""
from __future__ import annotations

import sys
from functools import lru_cache

from .base import PlatformAdapter, PlatformCapabilities


@lru_cache(maxsize=1)
def get_platform() -> PlatformAdapter:
    """Return the adapter for the current host platform.

    The cache is process-wide because SDL's video subsystem and native window
    APIs are process-wide for the current Saturn runtime.  Tests can clear the
    cache with ``get_platform.cache_clear()`` before replacing ``sys.platform``
    in an isolated import test.
    """
    if sys.platform == "win32":
        from .windows import WindowsPlatform
        return WindowsPlatform()
    if sys.platform.startswith("linux"):
        from .linux import LinuxPlatform
        return LinuxPlatform()
    from .other import OtherPlatform
    return OtherPlatform()


__all__ = ["PlatformAdapter", "PlatformCapabilities", "get_platform"]
