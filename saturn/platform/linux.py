"""Linux platform placeholder.

Linux window and desktop protocols are intentionally not implemented in this
first split.  Keeping a named adapter means X11, Wayland, portal and D-Bus
work can be added here without changing the portable App/Window/Page layers.
"""
from __future__ import annotations

import os

from .base import PlatformAdapter


class LinuxPlatform(PlatformAdapter):
    name = "linux"

    capabilities = PlatformAdapter.capabilities.__class__(module_watch=True)

    def snapshot_modules(self) -> list[str]:
        out = []
        try:
            with open("/proc/self/maps", "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    path = line.rstrip("\n").rpartition(" ")[2]
                    if path.startswith("/") and ".so" in os.path.basename(path):
                        out.append(os.path.realpath(path).lower())
        except OSError:
            return []
        return out


__all__ = ["LinuxPlatform"]
