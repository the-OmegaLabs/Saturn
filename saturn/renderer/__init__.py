"""Backend factory. GL/Vulkan renderers land in TODO milestones 11/12."""
from __future__ import annotations

from .base import Renderer

__all__ = ["Renderer", "create_renderer"]


def create_renderer(backend, window, *, logical_size=None,
                    pixel_ratio: float = 1.0) -> Renderer:
    kind = backend.value if hasattr(backend, "value") else backend
    if kind == "software":
        from .software import SoftwareRenderer
        return SoftwareRenderer(
            window, logical_size=logical_size, pixel_ratio=pixel_ratio)
    if kind == "opengl":
        from .gl import GLRenderer
        return GLRenderer(
            window, logical_size=logical_size, pixel_ratio=pixel_ratio)
    raise NotImplementedError(
        f"{backend!r} backend is a placeholder; use Render.SOFTWARE or Render.OPENGL")
