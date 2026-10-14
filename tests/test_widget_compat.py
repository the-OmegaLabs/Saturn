"""Compatibility behavior used by Flet applications running on Saturn."""
import io
import uuid
import unittest
from unittest.mock import patch

import pygame

from saturn.widgets.basic import Image, Placeholder, _img_cache


class PlaceholderTests(unittest.TestCase):
    def test_expand_uses_both_available_constraints(self):
        placeholder = Placeholder(expand=True)
        self.assertEqual(placeholder._intrinsic(760, 520, 1), (760, 520))

    def test_draws_outline_and_cross_without_a_center_circle(self):
        class Renderer:
            def __init__(self):
                self.rects = []
                self.lines = []
                self.circles = []

            def stroke_rect(self, *args, **kwargs):
                self.rects.append((args, kwargs))

            def line(self, *args, **kwargs):
                self.lines.append((args, kwargs))

            def circle(self, *args, **kwargs):
                self.circles.append((args, kwargs))

        placeholder = Placeholder()
        placeholder._place(0, 0, 600, 400, 1)
        renderer = Renderer()

        placeholder._draw(renderer, 0, 0)

        self.assertEqual(len(renderer.rects), 1)
        self.assertEqual(len(renderer.lines), 2)
        self.assertEqual(renderer.circles, [])


class RemoteImageTests(unittest.TestCase):
    def test_loads_and_caches_http_image_bytes(self):
        surface = pygame.Surface((3, 2), pygame.SRCALPHA)
        surface.fill((80, 120, 160, 255))
        buffer = io.BytesIO()
        pygame.image.save(surface, buffer, "sample.png")
        payload = buffer.getvalue()
        url = f"https://example.invalid/{uuid.uuid4().hex}.png"
        _img_cache.pop(url, None)

        with patch("saturn.widgets.basic.urlopen", return_value=io.BytesIO(payload)) as fetch:
            image = Image(url)
            image._load()
            image._remote_future.result(timeout=1)
            loaded = image._load()
            cached = Image(url)._load()

        self.assertEqual(loaded.get_size(), (3, 2))
        self.assertEqual(cached.get_size(), (3, 2))
        fetch.assert_called_once_with(url, timeout=5)
        _img_cache.pop(url, None)


if __name__ == "__main__":
    unittest.main()
