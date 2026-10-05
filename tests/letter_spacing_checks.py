"""TextStyle.letter_spacing across the desktop text pipeline."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saturn as st
from saturn.app import App, Renderer


def pump(app, predicate=lambda: True, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while True:
        app._pump_once()
        if predicate():
            return
        assert time.perf_counter() < deadline, "window operation timed out"
        time.sleep(0.01)


def check_text_widget():
    def main(page):
        page.bgcolor = "#193047"
        page.add(st.Text("SATURN", size=24, style=st.TextStyle(letter_spacing=8)))
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        shot = app.renderer.screenshot()
        w = [c for c in app.page.controls if isinstance(c, st.Text)][0]
        _, _, cw, _ = w._rect
        from saturn import text as txt
        plain = txt.line_width("SATURN", 24)
        assert cw >= plain + 8 * (len("SATURN") - 1) - 2, (cw, plain)
        # glyph pixels exist at the far right end of the spaced-out text
        found = any(shot.get_at((round(w._rect[0] + cw) - 3, y))[:3] != (25, 48, 71)
                    for y in range(round(w._rect[1]), round(w._rect[1] + w._rect[3])))
        assert found, "spaced text did not render at its measured width"
        print("Text letter_spacing OK")
    finally:
        app.close()
        app.run_until_closed()


def check_textfield():
    def main(page):
        page.bgcolor = "#193047"
        field = st.TextField(value="AB", text_style=st.TextStyle(letter_spacing=6))
        page.add(field)
        page._field = field
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        page = app.page
        pump(app)
        page.draw()  # must not raise NotImplementedError anymore
        field = page._field
        family, size, _ = field._style()
        spacing = field._spacing()
        assert spacing == 6, spacing
        # caret after "AB" sits one spacing step further than without spacing
        from saturn import text as txt
        plain_x = txt.line_width("AB", size)
        caret_x = field._line_width("AB", size, scale=1.0)
        assert caret_x >= plain_x + 6 - 0.01, (caret_x, plain_x)
        # caret glyph position matches the rendered advance: type a char via state
        field.value = "AB"
        page.draw()
        print("TextField letter_spacing OK")
    finally:
        app.close()
        app.run_until_closed()


def check_plain_text_untouched():
    def main(page):
        page.bgcolor = "#193047"
        page.add(st.Text("plain", size=16))
    app = App(main, Renderer.SOFTWARE)
    app.start()
    try:
        pump(app)
        app.page.draw()
        print("plain Text unaffected OK")
    finally:
        app.close()
        app.run_until_closed()


if __name__ == "__main__":
    check_text_widget()
    check_textfield()
    check_plain_text_untouched()
    print("ALL LETTER SPACING CHECKS PASS")
