"""Backend factory. GL/Vulkan renderers land in TODO milestones 11/12."""
from __future__ import annotations

from .base import Renderer

__all__ = ["Renderer", "create_renderer"]


def create_renderer(backend) -> Renderer:
    kind = backend.value if hasattr(backend, "value") else backend
    if kind == "software":
        from .software import SoftwareRenderer
        return SoftwareRenderer()
    if kind == "opengl":
        from .gl import GLRenderer
        return GLRenderer()
    raise NotImplementedError(
        f"{backend!r} backend is a placeholder; use Render.SOFTWARE or Render.OPENGL")
