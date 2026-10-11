"""Run with: python -m unittest discover -s tests -p test_page_auto_update.py."""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from saturn import Column, Container, Page, Switch, Text, ThemeMode
from saturn.app import App
from saturn.renderer.software import SoftwareRenderer
from saturn.web.session import PageHandle, WebPage


class PageAutoUpdateTests(unittest.TestCase):
    def setUp(self):
        # Exercise the real desktop dirty scheduler and software drawing,
        # without creating an OS window or starting background workers.
        self.app = object.__new__(App)
        self.app.page = None
        self.app._dirty = threading.Event()
        self.app._size = [320, 200]
        self.app._pixel_ratio = 1
        self.app.post = lambda fn: None
        self.app.call = lambda fn, *args: fn(*args)
        with patch.object(Page, "_sync_native_title_bar"):
            self.page = self.app.page = Page(self.app)
        self.page._sync_native_title_bar = lambda: None
        self.page.bgcolor = "#000000"
        window = SimpleNamespace(get_surface=lambda: pygame.Surface((320, 200)))
        self.app.renderer = SoftwareRenderer(window, anti_aliasing=False)

    def draw_requested_frame(self):
        if self.app._dirty.is_set():
            self.app._dirty.clear()
            self.page.draw()
            return True
        return False

    def pause(self):
        self.page.auto_update = False
        self.draw_requested_frame()

    def test_default_and_boolean_validation(self):
        self.assertIs(self.page.auto_update, True)
        for invalid in (0, 1, None, "false"):
            with self.assertRaises(TypeError):
                self.page.auto_update = invalid
        self.assertIs(self.page.auto_update, True)

    def test_paused_changes_wait_for_manual_frame_and_resume(self):
        tile = Container(width=60, height=60, bgcolor="#FF0000")
        self.page.add(tile)
        self.assertTrue(self.draw_requested_frame())
        point = (20, 20)
        self.assertEqual(self.app.renderer._buf.get_at(point)[:3], (255, 0, 0))
        self.pause()
        tile.bgcolor = "#00FF00"
        tile.width = 100
        tile.update()
        tile.repaint()
        self.assertFalse(self.draw_requested_frame())
        self.assertEqual(self.app.renderer._buf.get_at(point)[:3], (255, 0, 0))
        self.page.update()
        self.assertTrue(self.draw_requested_frame())
        self.assertEqual(self.app.renderer._buf.get_at(point)[:3], (0, 255, 0))
        self.assertEqual(tile._rect[2], 100)
        tile.bgcolor = "#0000FF"
        self.page.auto_update = True
        self.assertTrue(self.draw_requested_frame())
        self.assertEqual(self.app.renderer._buf.get_at(point)[:3], (0, 0, 255))

    def test_manual_repaint_still_works(self):
        self.pause()
        self.page.repaint()
        self.assertTrue(self.draw_requested_frame())

    def test_attachment_and_theme_updates_do_not_bypass_pause(self):
        items = Column()
        self.page.add(items)
        self.pause()
        child = Text("Queued")
        items.controls.append(child)
        items.update()
        self.assertIs(child.page, self.page)
        self.page.theme_mode = ThemeMode.DARK
        self.assertFalse(self.app._dirty.is_set())
        extra = Text("Extra")
        self.page.add(extra)
        self.assertIs(extra.page, self.page)
        self.page.remove(extra)
        self.assertIsNone(extra.page)
        self.assertFalse(self.app._dirty.is_set())

    def test_input_state_and_internal_animation_respect_pause(self):
        toggle = Switch("Update", value=True)
        self.page.add(toggle)
        self.pause()
        toggle._set_hover(True)
        toggle._animate_value(False)
        self.assertFalse(self.app._dirty.is_set())
        with patch("pygame.key.stop_text_input"):
            self.page.focus(toggle)
        self.assertFalse(self.app._dirty.is_set())
        self.page._hovered = toggle
        self.page._clear_hover()
        self.assertFalse(self.app._dirty.is_set())
        self.page.update()
        self.assertTrue(self.draw_requested_frame())
        self.assertFalse(self.app._dirty.is_set())

    def test_animation_continues_only_in_auto_mode(self):
        class AnimatedControl(Container):
            def _tick_animations(self, now):
                return True

        self.page.add(AnimatedControl())
        self.assertTrue(self.draw_requested_frame())
        self.assertTrue(self.app._dirty.is_set())
        self.pause()
        self.assertFalse(self.app._dirty.is_set())
        self.page.update()
        self.assertTrue(self.draw_requested_frame())
        self.assertFalse(self.app._dirty.is_set())
        self.page.auto_update = True
        self.assertTrue(self.draw_requested_frame())
        self.assertTrue(self.app._dirty.is_set())

    def test_each_page_controls_its_own_scheduler(self):
        other = object.__new__(App)
        other.page = SimpleNamespace(_auto_update=True)
        other._dirty = threading.Event()
        self.pause()
        self.app.mark_dirty()
        other.mark_dirty()
        self.assertFalse(self.app._dirty.is_set())
        self.assertTrue(other._dirty.is_set())


class WebPageAutoUpdateTests(unittest.TestCase):
    def test_facade_and_manual_updates_use_web_scheduler(self):
        scheduled = []
        session = SimpleNamespace(closed=False, locked=False,
                                  runtime=SimpleNamespace(schedule=scheduled.append),
                                  dirty=lambda: None)
        session.page = WebPage(session)
        page = PageHandle(session, None)
        self.assertIs(page.auto_update, True)
        page.auto_update = False
        self.assertEqual(len(scheduled), 1)
        scheduled.clear()
        label = Text("Queued")
        page.add(label)
        label.width = 120
        label.update()
        self.assertIs(label.page, session.page)
        self.assertEqual(scheduled, [])
        page.update()
        self.assertEqual(len(scheduled), 1)
        scheduled.clear()
        page.repaint()
        self.assertEqual(len(scheduled), 1)
        scheduled.clear()
        page.auto_update = True
        self.assertEqual(len(scheduled), 1)


if __name__ == "__main__":
    unittest.main()
