"""Render each reference example to its own dark Saturn screenshot."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import saturn
import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent))
from control_examples import EXAMPLES  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / ".static" / "controls"
FAILURES = []


def main(page: saturn.Page) -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    page.theme_mode = saturn.ThemeMode.DARK
    page.bgcolor = saturn.Colors.SURFACE
    page.padding = 40
    failures = []

    selected = set(sys.argv[1:]) or set(EXAMPLES)
    unknown = selected - set(EXAMPLES)
    if unknown:
        raise ValueError(f"Unknown controls: {sorted(unknown)}")
    for name, statement in EXAMPLES.items():
        if name not in selected:
            continue
        try:
            page.overlay.clear()
            page.clean()
            page.title = f"Saturn · {name}"
            exec(compile(statement, f"<docs:{name}>", "exec"),
                 {"saturn": saturn, "page": page})
            time.sleep(0.4)
            surface = page._app.screenshot()
            background = surface.get_at((0, 0))
            background_pixels = pygame.mask.from_threshold(
                surface, background, (6, 6, 6, 255))
            background_pixels.invert()
            regions = background_pixels.get_bounding_rects()
            if not regions:
                raise RuntimeError("the control rendered no visible pixels")
            bounds = regions[0].copy()
            for region in regions[1:]:
                bounds.union_ip(region)
            bounds.inflate_ip(48, 48)
            bounds = bounds.clip(surface.get_rect())
            pygame.image.save(surface.subsurface(bounds).copy(),
                              str(DESTINATION / f"{name}.png"))
            print(name, flush=True)
        except Exception as exc:
            failures.append((name, repr(exc)))
            print(f"FAILED {name}: {exc!r}", flush=True)

    page.window.destroy()
    FAILURES.extend(failures)


if __name__ == "__main__":
    saturn.run(main, backend=saturn.Renderer.SOFTWARE, width=720, height=360)
    if FAILURES:
        raise SystemExit(f"Control captures failed: {FAILURES}")
