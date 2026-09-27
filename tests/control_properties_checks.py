"""Shared control properties must affect geometry, attachment and events."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
import saturn as st
from page_compatibility_checks import AppStub


def main():
    pygame.init()
    pygame.display.set_mode((360, 200))
    app = AppStub()
    page = st.Page(app)
    try:
        reference = st.Ref[st.Container]()
        events = []
        box = st.Container(key="preview", ref=reference, aspect_ratio=2,
                           on_size_change=events.append, size_change_interval=0)
        page.add(box)
        assert reference.current is box and box.key == "preview"
        assert box._intrinsic(200, 300, 1) == (200, 100)
        box._place(0, 0, 200, 300, 1)
        assert box._rect == (0, 0, 200, 100)
        assert (events[-1].width, events[-1].height, events[-1].page) == (200, 100, page)
        box._place(0, 0, 200, 300, 1)
        assert len(events) == 1
        box.size_change_interval = 20
        box._place(0, 0, 160, 300, 1)
        time.sleep(.03)
        while app.pending:
            app.pending.pop(0)()
        assert (events[-1].width, events[-1].height) == (160, 80)
        child = st.Text("Inherited RTL")
        row = st.Row(controls=[child], rtl=True)
        page.add(row)
        assert child._rtl
        child.rtl = False
        assert not child._rtl
        first, skipped, last = st.TextButton("A"), st.TextButton("Skip", can_request_focus=False), st.TextButton("B")
        page.controls = [first, skipped, last]
        page.update()
        page.focus(first)
        page._focus_next()
        assert page._focused is last
        page._focus_next(reverse=True)
        assert page._focused is first
        skipped.focus()
        assert page._focused is first
        for invalid in (0, -1, float("inf"), float("nan")):
            try:
                st.Container(aspect_ratio=invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid aspect ratio accepted")
        try:
            st.Container(nonexistent_parameter=True)
        except TypeError:
            pass
        else:
            raise AssertionError("Unknown parameter was silently accepted")
        print("CONTROL PROPERTY CHECKS PASS: ref, ratio, RTL, throttled final size, focus traversal, argument validation.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
