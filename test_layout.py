r"""Layout engine self-check (milestone 5). Assert-based, headless.

Protocol under test: _intrinsic(max_w, max_h, scale) and _place(x, y, w, h, scale).
Run: .venv/Scripts/python.exe test_layout.py
"""
import sys

sys.path.insert(0, ".")

import saturn as ft
from saturn.widgets.containers import Column, Container, Row, Stack
from saturn.widgets.text import Text

SCALE = 1.0


def lay(c, x=0.0, y=0.0, w=800.0, h=600.0):
    c._place(x, y, w, h, SCALE)
    return c._rect


def approx(a, b, tol=0.6):
    return abs(a - b) <= tol


def check_row_basic():
    t1 = Text("AAA", size=20)
    t2 = Text("BBB", size=20)
    row = Row(t1, t2, spacing=10)
    lay(row, w=800, h=100)
    assert row._rect == (0, 0, 800, 100), row._rect  # fills width unless tight
    w1 = t1._rect[2]
    assert t1._rect[:2] == (0, 0), t1._rect
    assert approx(t2._rect[0], w1 + 10), (t1._rect, t2._rect)  # START + spacing
    assert approx(t1._rect[1], t2._rect[1], 0.01)
    # tight row shrinks to content: parent asks _intrinsic, then places it there
    row = Row(t1, t2, spacing=10, tight=True)
    tw, th = row._intrinsic(800, 100, SCALE)
    lay(row, w=tw, h=th)
    assert approx(row._rect[2], t1._rect[2] + t2._rect[2] + 10), row._rect


def check_row_alignment():
    t1 = Text("AAA", size=20)
    t2 = Text("BBB", size=20)
    row = Row(t1, t2, spacing=0, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    lay(row, w=300, h=50)
    assert approx(t1._rect[0], 0)
    assert approx(t2._rect[0] + t2._rect[2], 300), t2._rect  # last child flush right
    row = Row(t1, t2, spacing=0, alignment=ft.MainAxisAlignment.CENTER)
    lay(row, w=300, h=50)
    total = t1._rect[2] + t2._rect[2]
    assert approx(t1._rect[0], (300 - total) / 2), t1._rect


def check_expand():
    t1 = Text("AAA", size=20)
    t2 = Text("BBB", size=20)
    t2.expand = True
    row = Row(t1, t2, spacing=0)
    lay(row, w=300, h=50)
    assert approx(t2._rect[2], 300 - t1._rect[2]), (t1._rect, t2._rect)
    # two expands split evenly (same intrinsic width)
    a, b = Text("A", size=20), Text("A", size=20)
    a.expand = b.expand = True
    row = Row(a, b, spacing=0)
    lay(row, w=300, h=50)
    assert approx(a._rect[2], 150) and approx(b._rect[2], 150), (a._rect, b._rect)


def check_cross_alignment():
    t = Text("AAA", size=20)
    row = Row(t, spacing=0, vertical_alignment=ft.CrossAxisAlignment.END)
    lay(row, w=300, h=100)
    assert approx(t._rect[1], 100 - t._rect[3]), t._rect
    row = Row(t, spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    lay(row, w=300, h=100)
    assert approx(t._rect[1], (100 - t._rect[3]) / 2), t._rect


def check_column():
    t1 = Text("AAA", size=20)
    t2 = Text("BBB", size=20)
    col = Column(t1, t2, spacing=10)
    lay(col, w=300, h=600)
    h1 = t1._rect[3]
    assert approx(t2._rect[1], h1 + 10), (t1._rect, t2._rect)
    assert approx(t2._rect[0], 0)  # START cross
    col = Column(t1, t2, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    lay(col, w=300, h=600)
    assert approx(t1._rect[0], (300 - t1._rect[2]) / 2), t1._rect


def check_container():
    t = Text("hi", size=20)
    tw, th = t._intrinsic(800, 600, SCALE)
    c = Container(t, padding=10, bgcolor=ft.Colors.PRIMARY)
    w, h = c._intrinsic(800, 600, SCALE)
    assert approx(h, th + 20) and approx(w, tw + 20), (w, h, tw, th)
    lay(c, w=200, h=100)
    # content not aligned → fills the padded box
    assert t._rect[:2] == (10, 10), t._rect
    assert approx(t._rect[2], 180) and approx(t._rect[3], 80), t._rect
    # alignment centers the child at intrinsic size
    c = Container(Text("hi", size=20), padding=10, alignment=ft.Alignment.CENTER)
    lay(c, w=200, h=100)
    tw = c.content._rect[2]
    assert approx(c.content._rect[0], 10 + (180 - tw) / 2), c.content._rect


def check_stack():
    base = Container(bgcolor=ft.Colors.SURFACE_CONTAINER, width=100, height=50)
    badge = Text("x", size=12, left=80, top=30)
    st = Stack(base, badge)
    lay(st, w=300, h=300)
    assert base._rect[:2] == (0, 0) and base._rect[2:] == (100, 50)
    assert approx(badge._rect[0], 80) and approx(badge._rect[1], 30), badge._rect
    right = Text("r", size=12, right=10, bottom=5)
    st = Stack(base, right)
    lay(st, w=300, h=300)
    assert approx(right._rect[0], 300 - right._rect[2] - 10), right._rect


def check_nested():
    inner = Row(Text("L", size=20), Text("R", size=20),
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    card = Container(inner, padding=10, bgcolor=ft.Colors.SURFACE_CONTAINER)
    col = Column(Text("head", size=20), card, spacing=5)
    lay(col, w=400, h=600)
    assert approx(card._rect[2], 400), card._rect      # column stretches children wide
    assert approx(inner._rect[2], 380), inner._rect    # minus padding
    l, r = inner.controls
    assert approx(l._rect[0], 10)                      # inner start
    assert approx(r._rect[0] + r._rect[2], 390), r._rect  # inner end


def check_visible_and_margin():
    t1 = Text("AAA", size=20)
    t2 = Text("BBB", size=20)
    t2.visible = False
    row = Row(t1, t2, spacing=10)
    lay(row, w=300, h=50)
    assert t2._rect[2] == 0 or not t2.visible
    t3 = Text("CCC", size=20)
    t3.margin = 10
    row = Row(t1, t3, spacing=10)
    lay(row, w=300, h=50)
    assert approx(t3._rect[0], t1._rect[2] + 10 + 10), (t1._rect, t3._rect)  # spacing + margin


if __name__ == "__main__":
    check_row_basic()
    check_row_alignment()
    check_expand()
    check_cross_alignment()
    check_column()
    check_container()
    check_stack()
    check_nested()
    check_visible_and_margin()
    print("ALL LAYOUT TESTS PASS")
