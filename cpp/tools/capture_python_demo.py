"""Capture an idle Python OpenGL demo once, then close it without manual input."""
from __future__ import annotations
import argparse
import ctypes
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        ctypes.windll.shcore.SetProcessDpiAwareness(0)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "examples"))
    os.environ.pop("SATURN_SHOT", None)
    import pygame
    from saturn.renderer.gl import GLRenderer
    from demo import Application
    import saturn
    original = GLRenderer.flip
    frames = 0
    def flip(renderer):
        nonlocal frames
        original(renderer)
        frames += 1
        if frames == 3:
            pygame.image.save(renderer.screenshot(), str(output))
            pygame.event.post(pygame.event.Event(pygame.QUIT))
    GLRenderer.flip = flip
    saturn.run(main=Application().create_window, backend=saturn.Renderer.OPENGL)
    print(f"captured {output}")

if __name__ == "__main__":
    main()
