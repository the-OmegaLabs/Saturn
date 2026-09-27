"""Real software fallback, startup ordering and font lifecycle notifications."""
import asyncio
import contextlib
import importlib
import io
import sys
import threading
import time
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saturn as st
from saturn import text
from saturn.app import App


def wait_for(predicate):
    deadline = time.perf_counter()+5
    while not predicate():
        assert time.perf_counter() < deadline, "Event delivery timed out"
        time.sleep(.01)


def check_fallback(backend, *, fail_window=False):
    events, threads = [], []
    def main(page):
        page.bgcolor = "#193047"
        def failed(e):
            assert isinstance(e, st.RenderFailedEvent) and e.page is page
            events.append(e)
            threads.append(threading.get_ident())
        async def ready(e):
            await asyncio.sleep(.01)
            events.append(e)
            threads.append(threading.get_ident())
        page.on_render_failed = failed
        page.on_render_ready = ready
    app = App(main, backend, gpu="Deliberately nonexistent GPU")
    output = io.StringIO()
    module = importlib.import_module("saturn.app")
    native_window = module.pygame.Window
    def window(*args, **kwargs):
        if kwargs.get("opengl") or kwargs.get("vulkan"):
            raise module.pygame.error("Driver cannot create a GPU window")
        return native_window(*args, **kwargs)
    manager = patch.object(module.pygame, "Window", side_effect=window) if fail_window else contextlib.nullcontext()
    try:
        with manager, contextlib.redirect_stdout(output):
            app.start()
        wait_for(lambda: len(events) == 2)
        assert output.getvalue().count("Saturn can't use your current GPU, fallback to software renderer.") == 1
        assert [e.name for e in events] == ["render_failed", "render_ready"]
        failed, ready = events
        assert failed.backend == backend.value and failed.gpu == "Deliberately nonexistent GPU"
        assert failed.error and failed.fallback == "software"
        assert ready.backend == "software" and ready.fallback and ready.gpu_name is None
        assert app.page.renderer.name == "software" and app.page.renderer.gpus == ()
        assert all(t != app._ui_thread for t in threads)
        app._activate()
        app.page.draw()
        assert app.renderer.screenshot().get_at((2, 2))[:3] == (25, 48, 71)
        child = app.page.open_subpage()
        app._drain_commands()
        assert child.ready and child.renderer.name == "software"
        print(backend.value, "window failure" if fail_window else "selection failure", "fallback/events/child OK")
    finally:
        app.close()
        app.run_until_closed()


def check_fonts():
    seen = []
    def main(page):
        async def optimize(e):
            if e.status == "started":
                await asyncio.sleep(.02)
            seen.append(e)
        page.on_font_optimize = optimize
    app = App(main, st.Renderer.SOFTWARE)
    try:
        app.start()
        wait_for(lambda: app.page.on_font_optimize is not None)
        with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/".build-probe") as directory:
            dest = Path(directory)/"weight.ttf"
            with patch.object(text, "_instance_weight", return_value=b"cached font"):
                text._instance_bg("event-font", 555, dest)
            wait_for(lambda: len(seen) == 2)
            assert [e.status for e in seen] == ["started", "completed"]
            statuses = {e.status: e for e in seen}
            assert set(statuses) == {"started", "completed"}
            assert statuses["started"].success is None
            assert statuses["completed"].success and statuses["completed"].cached
            assert dest.read_bytes() == b"cached font"
            assert all(e.font == "event-font" and e.weight == 555 and e.page is app.page for e in seen)
            seen.clear()
            with patch.object(text, "_instance_weight", return_value=None):
                text._instance_bg("bad-event-font", 555, dest)
            wait_for(lambda: len(seen) == 2)
            assert [e.status for e in seen] == ["started", "failed"]
            failed = next(e for e in seen if e.status == "failed")
            assert failed.success is False and failed.error
            seen.clear()
            with patch.object(text, "urlopen", side_effect=OSError("offline")), warnings.catch_warnings():
                warnings.simplefilter("ignore")
                text._download_font("https://invalid.example/font.ttf", Path(directory)/"download.ttf")
            wait_for(lambda: len(seen) == 2)
            assert {e.status for e in seen} == {"started", "failed"}
            assert all(e.operation == "load" and e.weight is None for e in seen)
        print("Font optimize: start/completion/failure, weight cache and download events OK")
    finally:
        app.close()
        app.run_until_closed()
        text._inst_failed.discard(("bad-event-font", 555))


if __name__ == "__main__":
    for backend in (st.Renderer.OPENGL, st.Renderer.VULKAN):
        check_fallback(backend)
        check_fallback(backend, fail_window=True)
    check_fonts()
    print("RENDERER EVENT CHECKS PASS")
