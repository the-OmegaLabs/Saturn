"""Window/Page size semantics self-check."""
import sys

sys.path.insert(0, ".")

from saturn.app import App, Render


def check_outer_to_client_conversion():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    app._frame_size = (16, 39)
    assert app.outer_size == (800, 600)
    assert app.client_size_for_outer(350, 480) == (334, 441)


def check_live_resize_frame():
    class Renderer:
        def __init__(self):
            self.resizes = []
            self.flips = 0

        def on_resize(self, width, height):
            self.resizes.append((width, height))

        def flip(self):
            self.flips += 1

    class Page:
        def __init__(self):
            self.draws = 0
            self.on_resize = [object()]
            self.dispatches = 0

        def draw(self):
            self.draws += 1

        def _dispatch(self, handlers):
            assert handlers is self.on_resize
            self.dispatches += 1

    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    app._frame_size = (16, 39)
    app.renderer = Renderer()
    app.page = Page()
    app._resize_frame(500, 320, present=True, dispatch=True)
    assert app.size == (500, 320)
    assert app.outer_size == (516, 359)
    assert app.renderer.resizes == [(500, 320)]
    assert app.page.draws == 1 and app.renderer.flips == 1
    assert app.page.dispatches == 1
    app._resize_frame(500, 320, present=False, dispatch=True)
    assert app.page.dispatches == 1, "same SDL resize must not dispatch twice"


if __name__ == "__main__":
    check_outer_to_client_conversion()
    check_live_resize_frame()
    print("ALL WINDOW TESTS PASS")
