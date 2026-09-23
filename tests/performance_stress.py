"""Repeatable Saturn list stress test with real renderer presentation.

Examples:
    python tests/performance_stress.py --backend all --rows 1000 --frames 60
    python tests/performance_stress.py --backend opengl --rows 5000 --frames 120
    python tests/performance_stress.py --backend opengl --full-sweep
    python tests/performance_stress.py --backend opengl --resize-every 5
    python tests/performance_stress.py --backend opengl --resize-sweep --variable-height
    python tests/performance_stress.py --backend all --ripple
    python tests/performance_stress.py --backend opengl --variable-height
    python tests/performance_stress.py --backend opengl --gl-ssaa 1
    python tests/performance_stress.py --backend opengl --relayout-every 10
    python tests/performance_stress.py --backend opengl --max-p95-ms 16.7

The window is hidden by default, but each frame still traverses controls,
renders, and calls flip(). Use --visible for a short real-window replay.
Times include driver/OS scheduling and are not GPU timestamps.
Run each backend with the same rows, window size and frame count for comparison.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import math
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

import saturn as ft
from saturn.renderer import create_renderer
from saturn.widgets.containers import Container
from saturn.widgets._material import draw_state_layer


class BackendUnavailableError(RuntimeError):
    pass


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1_048_576
    except ImportError:
        return None


def _summary(samples):
    ordered = sorted(samples)
    return {
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[math.ceil(len(ordered) * .95) - 1], 3),
        "max_ms": round(ordered[-1], 3),
    }


class StressRow(Container):
    paints = 0

    def _draw(self, renderer, x, y):
        type(self).paints += 1
        super()._draw(renderer, x, y)


class StressListView(ft.ListView):
    layout_ms = 0.0
    layout_calls = 0

    def _place(self, x, y, w, h, scale):
        start = time.perf_counter()
        super()._place(x, y, w, h, scale)
        self.layout_ms += (time.perf_counter() - start) * 1000
        self.layout_calls += 1


def run_backend(backend, rows, frames, warmup, width, height,
                relayout_every=0, scroll_step=40.0, full_sweep=False,
                resize_every=0, resize_sweep=False, ripple=False, variable_height=False,
                gl_ssaa=None, visible=False, gpu_time=False,
                cpu_ripple=False):
    window = renderer = None
    pygame.init()
    try:
        try:
            window = pygame.Window(
                title=f"Saturn stress {backend}", size=(width, height),
                hidden=not visible, opengl=backend == "opengl",
                vulkan=backend == "vulkan")
            renderer = create_renderer(
                backend, window, logical_size=(width, height), pixel_ratio=1.0)
            if backend == "opengl" and gl_ssaa is not None:
                renderer._ssaa = gl_ssaa
                renderer.scale = gl_ssaa * renderer.pixel_ratio
                renderer._create_frame_target()
            if cpu_ripple:
                renderer.native_state_layer = False
        except Exception as error:
            raise BackendUnavailableError(str(error)) from error
        renderer.on_resize(
            width, height, pixel_size=(width, height), pixel_ratio=1.0)
        app = SimpleNamespace(
            size=(width, height), renderer=renderer, _window=window,
            mark_dirty=lambda: None, post=lambda fn: None,
            call=lambda fn, *args: fn(*args))
        page = ft.Page(app)
        page.padding = 0
        StressRow.paints = 0
        build_start = time.perf_counter()
        items = [StressRow(
            content=ft.Row(
                ft.Icon(ft.Icons.PERSON, size=20),
                ft.Text(f"Student {index:05d}  \u5b66\u751f {index}", size=14),
                spacing=8),
            height=None if variable_height else 40, padding=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            on_hover=lambda event: None)
            for index in range(rows)]
        listing = StressListView(
            *items, width=width, height=height, spacing=2)
        page.add(listing)
        ripple_state = SimpleNamespace(
            _state_hover_alpha=.08, _state_press_alpha=.12,
            _state_press_origin=(width / 2, 36),
            _state_ripple_progress=0.0)
        build_ms = (time.perf_counter() - build_start) * 1000

        # First frame includes initial layout, font rasterization and uploads.
        start = time.perf_counter()
        page.draw()
        renderer.flip()
        cold_ms = (time.perf_counter() - start) * 1000
        first_layout_ms = listing.layout_ms
        rss_start = _rss_mb()

        event_samples, hover_samples, frame_samples = [], [], []
        draw_samples, flip_samples = [], []
        gpu_queries = []
        resize_samples = []
        paints, layout_ms, layout_calls = [], [], []
        max_offset = max(0.0, listing._max_offset())
        effective_step = (max(scroll_step, max_offset / max(1, frames))
                          if full_sweep else scroll_step)
        total = warmup + frames
        for index in range(total):
            if resize_sweep or (resize_every and index % resize_every == 0):
                # A sweep approximates a mouse drag: nearly every frame has
                # a new width, so recent-width layout caches cannot hide work.
                size = ((width - 80 + index % 81, height) if resize_sweep else
                        ((width - 40, height - 30) if
                         (index // resize_every) % 2 == 0 else (width, height)))
                start = time.perf_counter()
                window.size = size
                renderer.on_resize(*size, pixel_size=size, pixel_ratio=1.0)
                app.size = size
                listing._width, listing._height = size
                resized_ms = (time.perf_counter() - start) * 1000
                if index >= warmup:
                    resize_samples.append(resized_ms)
            if relayout_every and index % relayout_every == 0:
                page.update()
            offset = (index * effective_step) % (
                max_offset + 1.0) if max_offset else 0.0
            start = time.perf_counter()
            listing.scroll_to(offset)
            scroll_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            page.pointer_move(width / 2, 12 + (index * 17) % max(1, height - 24))
            hover_ms = (time.perf_counter() - start) * 1000

            listing.layout_ms = listing.layout_calls = 0
            before_paints = StressRow.paints
            start = time.perf_counter()
            query = renderer.ctx.query(time=True) if gpu_time else None
            with query if query is not None else nullcontext():
                page.draw()
                if ripple:
                    ripple_state._state_ripple_progress = ((index % 60) + 1) / 60
                    draw_state_layer(ripple_state, renderer,
                                     (width / 2 - 100, 12, 200, 48),
                                     '#FFFFFF', (24, 8, 8, 24))
                drawn = time.perf_counter()
                renderer.flip()
            frame_ms = (time.perf_counter() - start) * 1000
            if index >= warmup:
                if query is not None:
                    gpu_queries.append(query)
                event_samples.append(scroll_ms)
                hover_samples.append(hover_ms)
                frame_samples.append(frame_ms)
                draw_samples.append((drawn - start) * 1000)
                flip_samples.append(frame_ms - draw_samples[-1])
                paints.append(StressRow.paints - before_paints)
                layout_ms.append(listing.layout_ms)
                layout_calls.append(listing.layout_calls)

        assert len(frame_samples) == frames
        assert all(0 < count <= rows for count in paints), paints
        return {
            "backend": backend,
            "rows": rows,
            "frames": frames,
            "window": [width, height],
            "visible": visible,
            "scroll_step": round(effective_step, 2),
            "full_sweep": full_sweep,
            "ripple": ripple,
            "cpu_ripple": cpu_ripple,
            "variable_height": variable_height,
            "resize_sweep": resize_sweep,
            "gl_ssaa": renderer._ssaa if backend == "opengl" else None,
            "build_ms": round(build_ms, 3),
            "cold_frame_ms": round(cold_ms, 3),
            "cold_layout_ms": round(first_layout_ms, 3),
            "scroll_event": _summary(event_samples),
            "hover_event": _summary(hover_samples),
            "draw_and_flip": _summary(frame_samples),
            "draw": _summary(draw_samples),
            "flip": _summary(flip_samples),
            "gpu": (_summary([query.elapsed / 1_000_000
                              for query in gpu_queries]) if gpu_queries
                    else None),
            "resize_setup": _summary(resize_samples) if resize_samples else None,
            "painted_rows_p50": statistics.median(paints),
            "painted_rows_max": max(paints),
            "layout_calls_during_scroll": sum(layout_calls),
            "layout_ms_during_scroll": round(sum(layout_ms), 3),
            "rss_delta_mb": (round(_rss_mb() - rss_start, 2)
                             if rss_start is not None else None),
        }
    finally:
        if renderer is not None:
            renderer.close()
        if window is not None:
            window.destroy()
        # pygame.quit invalidates pygame.font.Font objects. Clear Saturn's
        # process-wide font caches before the next backend in this process.
        from saturn import text as font_cache
        font_cache._font_cache.clear()
        font_cache._icon_cache.clear()
        font_cache._probe_cache.clear()
        font_cache._line_surface_cache.clear()
        font_cache._icon_surface_cache.clear()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("all", "software", "opengl", "vulkan"),
                        default="all")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--scroll-step", type=float, default=40.0,
                        help="Logical pixels scrolled per frame")
    parser.add_argument("--full-sweep", action="store_true",
                        help="Jump far enough to cross the whole list")
    parser.add_argument("--relayout-every", type=int, default=0,
                        help="Force a full layout every N frames; 0 disables it")
    parser.add_argument("--resize-every", type=int, default=0,
                        help="Toggle the real window size every N frames")
    parser.add_argument("--resize-sweep", action="store_true",
                        help="Sweep through 81 widths as during a window drag")
    parser.add_argument("--ripple", action="store_true",
                        help="Animate a rounded interaction ripple each frame")
    parser.add_argument("--cpu-ripple", action="store_true",
                        help="Force the old CPU ripple path for OpenGL comparison")
    parser.add_argument("--variable-height", action="store_true",
                        help="Measure intrinsic row heights instead of fixing them")
    parser.add_argument("--gl-ssaa", type=int, choices=(1, 2), default=None,
                        help="OpenGL supersampling scale for comparison")
    parser.add_argument("--visible", action="store_true",
                        help="Show a short real-window replay")
    parser.add_argument("--gpu-time", action="store_true",
                        help="Collect OpenGL GPU elapsed-time queries")
    parser.add_argument("--max-p95-ms", type=float, default=None,
                        help="Optional CI limit for draw+flip p95")
    args = parser.parse_args()
    if (min(args.rows, args.frames, args.width, args.height) <= 0 or
            min(args.warmup, args.relayout_every, args.resize_every) < 0 or
            args.scroll_step <= 0):
        parser.error("rows, frames, width and height must be positive; "
                     "warmup, relayout-every and resize-every must be >= 0; "
                     "scroll-step > 0")
    if args.gl_ssaa is not None and (args.backend != "opengl" or
                                      args.resize_every or args.resize_sweep):
        parser.error("--gl-ssaa requires --backend opengl without resizing")
    if args.resize_every and args.resize_sweep:
        parser.error("Choose --resize-every or --resize-sweep")
    if args.gpu_time and args.backend != "opengl":
        parser.error("--gpu-time requires --backend opengl")
    if args.cpu_ripple and (args.backend != "opengl" or not args.ripple):
        parser.error("--cpu-ripple requires --backend opengl --ripple")
    backends = (("software", "opengl", "vulkan") if args.backend == "all"
                else (args.backend,))
    failed = False
    for backend in backends:
        try:
            result = run_backend(backend, args.rows, args.frames, args.warmup,
                                 args.width, args.height, args.relayout_every,
                                 args.scroll_step, args.full_sweep,
                                 args.resize_every, args.resize_sweep, args.ripple,
                                 args.variable_height, args.gl_ssaa,
                                 args.visible, args.gpu_time,
                                 args.cpu_ripple)
            print(json.dumps(result, ensure_ascii=False))
            if (args.max_p95_ms is not None and
                    result["draw_and_flip"]["p95_ms"] > args.max_p95_ms):
                failed = True
        except Exception as error:
            status = ("unavailable" if isinstance(error, BackendUnavailableError)
                      else "failed")
            print(json.dumps({"backend": backend, "status": status,
                              "reason": str(error)}, ensure_ascii=False))
            if status == "failed" or args.backend != "all":
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
