"""Regression tests for applying native window size limits."""
import unittest

from saturn.window import Window


class WindowLimitTests(unittest.TestCase):
    def test_native_limit_change_restores_size_before_platform_resize(self):
        class NativeWindow:
            def __init__(self, app):
                self.app = app
                self.saved_minimum = None

            @property
            def minimum_size(self):
                return (1, 1)

            @minimum_size.setter
            def minimum_size(self, size):
                # SDL can synchronously resize the native window when a limit
                # is changed. Model the frame-size overshoot from Windows.
                self.saved_minimum = size
                self.app._outer_size[:] = [281, 739]
                self.app._size[:] = [281, 739]

        class App:
            def __init__(self):
                self._outer_size = [265, 700]
                self._size = [265, 700]
                self._frame_size = (0, 0)
                self._sdl_frame_size = (16, 39)
                self.pixel_ratio = 1
                self._window = NativeWindow(self)
                self.posted = []

            @property
            def outer_size(self):
                return tuple(self._outer_size)

            def client_size_for_outer(self, width, height):
                return width, height

            def post(self, callback):
                self.posted.append(callback)

            def mark_dirty(self):
                pass

        app = App()
        window = object.__new__(Window)
        window._app = app
        window._values = {"min_width": 265, "title_bar_hidden": True}
        window._native = None
        window._size_pending = False
        window._pending_size = None
        window._applied_limits = None
        window._last_resize_event = None
        window.on_event = None
        window.data = None
        window.key = None

        window._apply_limits()

        self.assertEqual(app._window.saved_minimum, (249, 1))
        self.assertEqual(window._pending_size, (265, 700))
        self.assertEqual(app._outer_size, [265, 700])
        self.assertEqual(app._size, [265, 700])


if __name__ == "__main__":
    unittest.main()
