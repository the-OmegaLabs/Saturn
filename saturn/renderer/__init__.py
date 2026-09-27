"""Renderer backend factory."""
from __future__ import annotations

from .base import Renderer

__all__ = ["Renderer", "create_renderer"]


def create_renderer(backend, window, *, logical_size=None,
                    pixel_ratio: float = 1.0, anti_aliasing: bool = True,
                    vsync: bool = True, gpu=None) -> Renderer:
    from .gpu import validate_gpu
    gpu = validate_gpu(gpu)
    kind = backend.value if hasattr(backend, "value") else backend
    if kind == "software":
        if gpu is not None:
            raise ValueError('The software renderer does not support GPU selection')
        from .software import SoftwareRenderer
        return SoftwareRenderer(
            window, logical_size=logical_size, pixel_ratio=pixel_ratio,
            anti_aliasing=anti_aliasing, vsync=vsync)
    if kind == "opengl":
        from .gl import GLRenderer
        return GLRenderer(
            window, logical_size=logical_size, pixel_ratio=pixel_ratio,
            anti_aliasing=anti_aliasing, vsync=vsync, gpu=gpu)
    if kind == "vulkan":
        from .vulkan import VulkanRenderer
        return VulkanRenderer(
            window, logical_size=logical_size, pixel_ratio=pixel_ratio,
            anti_aliasing=anti_aliasing, vsync=vsync, gpu=gpu)
    raise NotImplementedError(
        f"unknown rendering backend: {backend!r}")
