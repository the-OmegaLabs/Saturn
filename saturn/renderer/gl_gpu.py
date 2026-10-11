"""Compatibility facade for platform-specific OpenGL GPU bindings.

The implementation lives under ``saturn.platform`` so the renderer does not
need to import WGL or other operating-system APIs directly.
"""
from __future__ import annotations

from ..platform import get_platform


class GLGPUBinding:
    """Create the active platform's OpenGL GPU binding.

    This class preserves the old private constructor used by ``GLRenderer``
    while dispatching all platform-specific work to the adapter.
    """

    def __new__(cls, context, gpu):
        return get_platform().create_gl_gpu_binding(context, gpu)


__all__ = ["GLGPUBinding"]
