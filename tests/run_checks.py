"""Startup argument validation and callback forwarding against real Flet."""
import inspect
import os
from unittest.mock import patch

import flet
import saturn


def check():
    for entry in (saturn.run, flet.run):
        parameters = inspect.signature(entry).parameters
        assert "width" not in parameters and "height" not in parameters

    class Application:
        def create_window(self, page):
            pass

    main = Application().create_window
    with patch("saturn.app.App") as app_class, patch.dict(os.environ, {}, clear=True):
        app = app_class.return_value
        assert saturn.run(main) is app
        app_class.assert_called_once_with(
            main, saturn.Renderer.OPENGL, title="saturn", gpu=None)
        app.start.assert_called_once_with()
        app.run_until_closed.assert_called_once_with()

    with patch("saturn.app.App") as app_class:
        for option in ("width", "height", "before_main", "host"):
            try:
                saturn.run(main, **{option: 640})
            except TypeError as error:
                assert option in str(error), error
            else:
                raise AssertionError(f"Unsupported startup option accepted: {option}")
        app_class.assert_not_called()


if __name__ == "__main__":
    check()
    print("RUN API CHECKS PASS")
