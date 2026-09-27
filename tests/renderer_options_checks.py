"""Renderer settings: UI-thread dispatch and real backend resource changes."""
import sys
import threading
from types import SimpleNamespace

sys.path.insert(0, ".")

import pygame
import vulkan as vk
from saturn.app import App, Renderer
from saturn.page import _RendererSettings
from saturn.renderer import create_renderer
from saturn.renderer.vulkan import VulkanRenderer


def check_dispatch():
    app = object.__new__(App)
    app._anti_aliasing = app._vsync = True
    app._renderer_configuration_pending = False
    app._renderer_options_lock = threading.Lock()
    pending, applied = [], []
    app.post = pending.append
    app.mark_dirty = lambda: None
    app.page = SimpleNamespace(_layout_dirty=False)
    app.renderer = SimpleNamespace(configure=lambda **kw: applied.append(kw))
    settings = _RendererSettings(app)
    assert settings.context is app.renderer
    app.renderer = None
    assert settings.name is None
    app.renderer = SimpleNamespace(name='vulkan',configure=lambda **kw:applied.append(kw))
    app._backend = Renderer.OPENGL
    assert settings.name == 'vulkan'  # Inspect the context, not the requested backend.
    try:
        settings.name='opengl'
    except AttributeError:
        pass
    else:
        raise AssertionError('Renderer name must be read-only')
    settings.anti_aliasing = False
    settings.vsync = False
    assert not settings.anti_aliasing and not settings.vsync
    assert len(pending) == 1 and not applied
    pending.pop()()
    assert applied == [dict(anti_aliasing=False, vsync=False)]
    assert app.page._layout_dirty
    for name in ("anti_aliasing", "vsync"):
        try:
            setattr(settings, name, "false")
        except TypeError:
            pass
        else:
            raise AssertionError("Non-boolean setting accepted")


def check_present_fallback():
    renderer = object.__new__(VulkanRenderer)
    renderer._physical_device = renderer._surface = None
    renderer.vsync = False
    renderer._get_present_modes = lambda *args: [vk.VK_PRESENT_MODE_FIFO_KHR]
    assert renderer._choose_present_mode() == vk.VK_PRESENT_MODE_FIFO_KHR
    assert renderer.vsync_active
    renderer._get_present_modes = lambda *args: [
        vk.VK_PRESENT_MODE_FIFO_KHR, vk.VK_PRESENT_MODE_MAILBOX_KHR]
    assert renderer._choose_present_mode() == vk.VK_PRESENT_MODE_MAILBOX_KHR
    renderer._get_present_modes = lambda *args: [
        vk.VK_PRESENT_MODE_FIFO_KHR, vk.VK_PRESENT_MODE_IMMEDIATE_KHR]
    assert renderer._choose_present_mode() == vk.VK_PRESENT_MODE_IMMEDIATE_KHR
    assert not renderer.vsync_active


def check_backend(backend):
    pygame.init()
    window = pygame.Window(
        "Renderer options check", size=(96, 64), hidden=True, resizable=True,
        opengl=backend is Renderer.OPENGL, vulkan=backend is Renderer.VULKAN)
    renderer = None
    try:
        renderer = create_renderer(backend, window, anti_aliasing=False, vsync=False)
        settings = _RendererSettings(SimpleNamespace(renderer=renderer))
        assert settings.name == backend.value
        assert settings.name == settings.context.name
        for enabled in (False, True, False):
            renderer.configure(anti_aliasing=enabled, vsync=enabled)
            renderer.on_resize(96, 64, pixel_size=(96, 64), pixel_ratio=1)
            assert renderer.anti_aliasing is enabled and renderer.vsync is enabled
            if backend is Renderer.VULKAN:
                assert renderer._gpu_samples == vk.VK_SAMPLE_COUNT_1_BIT
                assert renderer._render_extent == ((192, 128) if enabled else (96, 64))
                assert not enabled or renderer.present_mode == "fifo"
            assert renderer.scale == (2 if enabled else 1)
            renderer.clear((25, 35, 45, 255))
            renderer.fill_rect(12, 12, 32, 24, (200, 80, 60, 255), radius=4)
            renderer.flip()
            frame = renderer.screenshot()
            assert frame.get_size() == (96, 64)
            assert all(abs(frame.get_at((24, 24))[i] - (200, 80, 60)[i]) <= 3
                       for i in range(3))
            print(backend.value, "AA:", enabled, "scale:", renderer.scale,
                  "vsync active:", renderer.vsync_active,
                  "samples:", getattr(renderer, "_gpu_samples", None),
                  "present:", getattr(renderer, "present_mode", None))
    finally:
        if renderer is not None:
            renderer.close()
        window.destroy()
        pygame.quit()


if __name__ == "__main__":
    check_dispatch()
    check_present_fallback()
    for backend in Renderer:
        check_backend(backend)
    print("RENDERER OPTIONS CHECKS PASS")
