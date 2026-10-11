"""Compatibility import for the pre-platform-split Win32 helper.

New code should import :class:`NativeWindow` through
``saturn.platform.windows``. Keeping this module avoids breaking private
imports used by older Saturn examples and downstream experiments.
"""
from .platform.windows_native import NativeWindow

__all__ = ["NativeWindow"]
