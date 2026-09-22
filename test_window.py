"""Window/Page size semantics self-check."""
import sys

sys.path.insert(0, ".")

from saturn.app import App, Render


def check_outer_to_client_conversion():
    app = App(lambda page: None, Render.SOFTWARE, 800, 600, "test")
    app._frame_size = (16, 39)
    assert app.outer_size == (800, 600)
    assert app.client_size_for_outer(350, 480) == (334, 441)


if __name__ == "__main__":
    check_outer_to_client_conversion()
    print("ALL WINDOW TESTS PASS")
