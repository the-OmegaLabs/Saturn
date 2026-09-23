"""Refresh gallery screenshots that include the Saturn logo.

Usage: python tools/capture_saturn_gallery.py VARIANT
Run each variant in its own process, because each run owns an SDL window.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import saturn
from examples.demo_common import DEMO_HEIGHT, DEMO_WIDTH


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    "hello": ("hello.py", "hello-demo.png", []),
    "demo": ("demo.py", "demo.png", []),
    "buttons": ("buttons_demo.py", "buttons-demo.png", []),
    "inputs": ("inputs_demo.py", "inputs-demo.png", []),
    "layout": ("layout_demo.py", "layout-demo.png", []),
    "text": ("text_demo.py", "text-demo.png", []),
    "widgets": ("widgets_demo.py", "widgets-demo.png", []),
    "dark": ("expressive_demo.py", "expressive-dark.png", []),
    "motion": ("expressive_motion_demo.py", "expressive-motion.png", []),
    "menu": ("expressive_motion_demo.py", "expressive-menu.png", ["--menu"]),
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in VARIANTS:
        raise SystemExit(__doc__)
    variant = sys.argv[1]
    module_name, image_name, flags = VARIANTS[variant]
    path = ROOT / "examples" / module_name
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("saturn_gallery_example", path)
    assert spec and spec.loader
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    sys.argv[:] = [str(path), *flags]
    entry = (example.main if variant in {"dark", "motion", "menu"}
             else example.Application().create_window)

    def capture(page: saturn.Page) -> None:
        page.theme_mode = saturn.ThemeMode.DARK
        entry(page)
        time.sleep(0.8)
        destination = ROOT / ".static" / "shots" / image_name
        page._app.screenshot(str(destination))
        print(destination)
        page.window.destroy()

    saturn.run(capture, backend=saturn.Renderer.SOFTWARE,
               width=DEMO_WIDTH, height=DEMO_HEIGHT)


if __name__ == "__main__":
    main()
