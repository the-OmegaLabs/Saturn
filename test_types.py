"""Self-check for milestone 2 (enums, colors, types, icon font). Assert-based."""
import sys

sys.path.insert(0, ".")

import saturn as ft


def check_colors():
    assert ft.Colors.RED.value == "red"
    assert ft.Colors.RED_500.value == "red500"
    assert ft.parse_color(ft.Colors.RED) == (244, 67, 54, 255)
    assert ft.parse_color("red500") == (244, 67, 54, 255)
    assert ft.parse_color("#FF0000") == (255, 0, 0, 255)
    assert ft.parse_color("#F00") == (255, 0, 0, 255)
    assert ft.parse_color("#80FF0000") == (255, 0, 0, 128)  # flet: #AARRGGBB
    assert ft.parse_color(0x80FF0000) == (255, 0, 0, 128)
    assert ft.parse_color((10, 20, 30)) == (10, 20, 30, 255)
    assert ft.parse_color(ft.Colors.TRANSPARENT) == (0, 0, 0, 0)
    # M3 roles resolve against theme brightness
    p = ft.parse_color(ft.Colors.PRIMARY)
    assert p == (0x67, 0x50, 0xA4, 255), p
    import saturn.colors as C
    C.theme_dark = True
    p = ft.parse_color(ft.Colors.PRIMARY)
    assert p == (0xD0, 0xBC, 0xFF, 255), p
    s = ft.parse_color(ft.Colors.SURFACE)
    assert s == (0x14, 0x12, 0x18, 255), s
    C.theme_dark = False
    print("colors ok")


def check_icons():
    # variant suffixes (_OUTLINED etc.) alias the base glyph — same rendering
    assert len(ft.Icons.__members__) > 8000
    assert ft.Icons.ADD_OUTLINED is ft.Icons.ADD  # variants share the glyph
    # glyph must exist in the bundled font
    import pygame.freetype as FT
    FT.init()
    f = FT.Font("saturn/assets/MaterialSymbolsOutlined.ttf", 24)
    for name in ("HOME", "ADD", "SETTINGS", "SEARCH", "CLOSE", "DELETE"):
        assert f.get_metrics(chr(ft.Icons[name])) is not None, name
    print(f"icons ok ({len(ft.Icons)} members, font glyphs verified)")


def check_types():
    assert [m.value for m in ft.MainAxisAlignment] == [
        "start", "end", "center", "spaceBetween", "spaceAround", "spaceEvenly"]
    assert ft.FontWeight.BOLD.value == "bold"
    p = ft.types.as_padding(10)
    assert (p.left, p.top, p.right, p.bottom) == (10, 10, 10, 10)
    assert ft.types.as_padding(None).left == 0
    r = ft.types.as_border_radius(8)
    assert r.top_left == 8 and r.bottom_right == 8
    b = ft.Border.all(2, ft.Colors.RED)
    assert b.left.width == 2 and b.top.color is ft.Colors.RED
    assert ft.Alignment.CENTER == ft.Alignment(0, 0)
    assert ft.Alignment.BOTTOM_RIGHT.x == 1 and ft.Alignment.BOTTOM_RIGHT.y == 1
    assert ft.text.weight_num(ft.FontWeight.W_600) == 600
    assert ft.text.weight_num(ft.FontWeight.BOLD) == 700
    assert ft.text.weight_num(ft.FontWeight.NORMAL) == 400
    assert ft.text.weight_num('w900') == 900
    print("types ok")


if __name__ == "__main__":
    check_colors()
    check_icons()
    check_types()
    print("ALL PASS")
