"""GPU matching, startup forwarding and real rendering on selectable adapters."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import saturn
from saturn.app import App, Renderer
from saturn.page import _RendererSettings
from saturn.renderer import create_renderer
from saturn.renderer.gpu import GPUSelectionError, select_gpu, validate_gpu


def expect_error(kind, fn):
    try:
        fn()
    except kind as error:
        return error
    raise AssertionError(f"Expected {kind.__name__}")


def check_matching():
    names = ("NVIDIA RTX A", "Intel Graphics", "NVIDIA RTX B")
    assert select_gpu(names, None, default=1) == 1
    assert select_gpu(names, 2) == 2
    assert select_gpu(names, " intel ") == 1
    assert select_gpu(names, "NVIDIA RTX A/PCIe/SSE2") == 0
    assert select_gpu(("RTX", "RTX Pro"), "RTX") == 0
    for gpu in ("NVIDIA", "missing", 3):
        expect_error(GPUSelectionError, lambda: select_gpu(names, gpu))
    expect_error(GPUSelectionError, lambda: select_gpu(("same", "same"), "same"))
    for gpu in (True, 1.5, object()):
        expect_error(TypeError, lambda: validate_gpu(gpu))
    for gpu in (-1, " "):
        expect_error(ValueError, lambda: validate_gpu(gpu))
    expect_error(ValueError, lambda: App(lambda p: None, Renderer.SOFTWARE, gpu=0))


def check_run():
    import importlib
    module = importlib.import_module("saturn.app")
    with patch.object(module, "App") as app:
        saturn.run(lambda page: None, backend=Renderer.VULKAN, gpu="Intel")
        assert app.call_args.kwargs["gpu"] == "Intel"
        app.return_value.start.assert_called_once()
        app.return_value.run_until_closed.assert_called_once()
    with patch.object(module, "App") as app:
        saturn.run(lambda page: None, backend=Renderer.OPENGL)
        assert app.call_args.kwargs["gpu"] is None
        app.return_value.start.side_effect = GPUSelectionError("unavailable")
        expect_error(GPUSelectionError, lambda: saturn.run(lambda p: None, gpu="missing"))
        app.return_value.close.assert_called_once()


def check_backend(backend):
    pygame.init()
    def render(gpu=None, invalid=False):
        window = pygame.Window("GPU selection check", size=(96, 64), hidden=True,
                               resizable=True, opengl=backend is Renderer.OPENGL,
                               vulkan=backend is Renderer.VULKAN)
        renderer = None
        try:
            if invalid:
                error = expect_error(GPUSelectionError, lambda: create_renderer(backend, window, gpu=gpu))
                assert "unavailable" in str(error)
                return
            renderer = create_renderer(backend, window, gpu=gpu, vsync=False)
            settings = _RendererSettings(SimpleNamespace(renderer=renderer))
            assert settings.name == backend.value
            assert settings.gpu_name == renderer.gpu_name and settings.gpu_name
            assert settings.gpus == renderer.gpus and settings.gpus
            assert settings.gpu_index == renderer.gpu_index
            for key in ("gpu_name", "gpu_index", "gpus"):
                expect_error(AttributeError, lambda: setattr(settings, key, None))
            for size in ((96, 64), (128, 80)):
                window.size = size
                pygame.event.pump()
                renderer.activate()
                renderer.on_resize(*size, pixel_size=size, pixel_ratio=1)
                renderer.clear((25, 35, 45, 255))
                renderer.fill_rect(12, 12, 32, 24, (200, 80, 60, 255), radius=4)
                renderer.flip()
                frame = renderer.screenshot()
                assert frame.get_size() == size
                assert all(abs(frame.get_at((24, 24))[i]-(200, 80, 60)[i]) <= 3 for i in range(3))
            print(backend.value, "requested:", gpu, "actual:", settings.gpu_name, "index:", settings.gpu_index)
            return settings.gpus, settings.gpu_name
        finally:
            if renderer is not None:
                renderer.close()
            window.destroy()
    try:
        names, _ = render()
        for index, name in enumerate(names):
            render(index)
            render(name)
        render("Saturn deliberately nonexistent GPU", invalid=True)
        render(len(names), invalid=True)
        # Failed selection must not corrupt subsequent native contexts.
        render()
    finally:
        pygame.quit()


def check_child_selection():
    app = App(lambda page: None, Renderer.VULKAN, gpu=0)
    app.start()
    try:
        names = app.renderer.gpus
        inherited = app.page.open_subpage(title="Inherited GPU")
        other = app.page.open_subpage(title="Explicit GPU", gpu=len(names)-1)
        # Queued child creation and rendering execute on the owner's UI thread.
        app._drain_commands()
        assert inherited.ready and other.ready
        assert inherited.renderer.gpu_name == app.page.renderer.gpu_name
        assert other.renderer.gpu_name == names[-1]
        assert inherited._app._gpu == app._gpu
        for target, rgb in ((app, (25, 35, 45)), (other._app, (100, 50, 30)), (app, (25, 35, 45))):
            target._activate()
            target.renderer.clear((*rgb, 255))
            target.renderer.flip()
            assert target.renderer.screenshot().get_at((2, 2))[:3] == rgb
        print("Vulkan parent and child GPU isolation/inheritance OK")
    finally:
        app.close()
        app.run_until_closed()


if __name__ == "__main__":
    check_matching()
    check_run()
    for backend in (Renderer.OPENGL, Renderer.VULKAN):
        check_backend(backend)
    check_child_selection()
    print("GPU SELECTION CHECKS PASS")
