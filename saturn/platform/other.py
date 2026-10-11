"""Fallback adapter for platforms without a native Saturn integration."""
from __future__ import annotations

from .base import PlatformAdapter


class OtherPlatform(PlatformAdapter):
    name = "other"


__all__ = ["OtherPlatform"]
