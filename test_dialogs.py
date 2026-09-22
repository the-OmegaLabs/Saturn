"""Dialogs self-check (milestone 9): AlertDialog barrier/modal/actions,
SnackBar auto-dismiss. Headless + assert-based.
"""
import sys
import threading
import time

sys.path.insert(0, ".")

import saturn as ft
from saturn.widgets.dialogs import AlertDialog, SnackBar
from saturn.widgets.text import Text


class Rec:
    def __init__(self):
        self.items = []
        self.ev = threading.Event()

    def __call__(self, e=None):
        self.items.append(getattr(e, "data", 1))
        self.ev.set()

    def wait(self, timeout=2.0):
        return self.ev.wait(timeout)


def make_page():
    from saturn.app import App
    app = App(lambda p: None, ft.Render.SOFTWARE, 800, 600, "t")
    app.start()
    app.page.add(ft.Text("base"))
    app.page.draw()
    return app, app.page


def check_alert():
    app, page = make_page()
    approved, dismissed = Rec(), Rec()
    dlg = AlertDialog(title="Delete item?",
                      content=Text("This cannot be undone."),
                      actions=[ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                               ft.FilledButton("Delete", on_click=lambda e: (approved(), page.pop_dialog()))],
                      on_dismiss=dismissed)
    page.show_dialog(dlg)
    page.draw()
    assert page.overlay == [dlg] and dlg.open
    # card is centered
    cx, cy, cw, ch = dlg._card_rect
    assert abs(cx + cw / 2 - page.width / 2) < 2, dlg._card_rect
    assert abs(cy + ch / 2 - page.height / 2) < 2, dlg._card_rect
    # click the Delete action button
    btn = dlg.actions[1]
    page.pointer_down(btn._rect[0] + 5, btn._rect[1] + 5)
    page.pointer_up(btn._rect[0] + 5, btn._rect[1] + 5)
    assert approved.wait() and dismissed.wait()
    assert page.overlay == [], page.overlay
    print("alert ok")


def check_barrier_dismiss_and_modal():
    app, page = make_page()
    dlg = AlertDialog(title="t", content=Text("c"), modal=False)
    page.show_dialog(dlg)
    page.draw()
    page.pointer_down(5, 5)   # barrier
    page.pointer_up(5, 5)
    assert page.overlay == [], "non-modal barrier click should dismiss"
    dlg2 = AlertDialog(title="t", content=Text("c"), modal=True)
    page.show_dialog(dlg2)
    page.draw()
    page.pointer_down(5, 5)
    page.pointer_up(5, 5)
    assert page.overlay == [dlg2], "modal barrier click must not dismiss"
    page.pop_dialog()
    assert page.overlay == []
    print("barrier/modal ok")


def check_snackbar():
    app, page = make_page()
    acted, gone = Rec(), Rec()
    snack = SnackBar("Saved!", action="Undo", duration=300,
                     on_action=acted, on_dismiss=gone)
    page.show_dialog(snack)
    assert snack._animations["_reveal"].end_value == 1.0
    now = time.perf_counter()
    snack._animations["_reveal"].started = now - 0.125
    snack._tick_animations(now)
    assert 0 < snack._reveal < 1, snack._reveal
    page.draw()
    assert page.overlay == [snack]
    bx, by, bw, bh = snack._bar_rect
    assert (bx, by, bw, bh) == (0, page.height - 48, page.width, 48), snack._bar_rect
    # click action
    page.pointer_down(bx + bw - 40, by + bh / 2)
    page.pointer_up(bx + bw - 40, by + bh / 2)
    assert acted.wait() and gone.wait()
    assert page.overlay == []
    # auto-dismiss
    snack2 = SnackBar("auto", duration=200)
    page.show_dialog(snack2)
    time.sleep(0.5)
    assert page.overlay == [], "snackbar should auto-dismiss"
    print("snackbar ok")


if __name__ == "__main__":
    check_alert()
    check_barrier_dismiss_and_modal()
    check_snackbar()
    print("ALL DIALOG TESTS PASS")
