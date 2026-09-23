"""Input editing and OpenGL caret rendering regressions."""
import pygame
import saturn as ft
from saturn.renderer.gl import GLRenderer


def check():
    field = ft.TextField('abcdef')
    backspace = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0)
    for _ in range(3):
        field._key(backspace)
    assert field.value == 'abc' and field._caret == 3
    field.read_only = True
    field._key(backspace)
    assert field.value == 'abc'
    field.read_only = False
    field._composition = '\u62fc'  # A CJK IME composition character.
    field._key(backspace)
    assert field.value == 'abc'
    field._composition = ''
    field._select_range(0, 2)
    field._key(backspace)
    assert field.value == 'c' and field._caret == 0
    field._key(backspace)
    assert field.value == 'c'


def check_textfield_vertical_alignment():
    """Value and hint ink stay vertically centered on the caret."""
    pygame.init()
    window = pygame.Window(size=(336, 473), hidden=True, opengl=True)
    renderer = GLRenderer(window, logical_size=(336, 473))
    field = ft.TextField(
        '123123', hint_text='License key', password=True,
        can_reveal_password=True, filled=True,
        bgcolor=ft.Colors.with_opacity(.06, ft.Colors.WHITE),
        text_size=14, text_style=ft.TextStyle(font_family='Consolas', size=14),
        cursor_color=ft.Colors.WHITE, height=50)
    field._password_revealed = True
    field._focused = field._cursor_visible = True
    field._place(46, 275, 250, 50, renderer.scale)

    def capture():
        renderer.clear((31, 31, 31, 255))
        field._draw_all(renderer)
        return renderer.screenshot()

    def changed_bbox(a, b):
        pixels = [(x, y) for x in range(60, 170)
                  for y in range(285, 317)
                  if sum(abs(a.get_at((x, y))[i] - b.get_at((x, y))[i])
                         for i in range(3)) > 12]
        assert pixels
        return min(y for _, y in pixels), max(y for _, y in pixels)

    def aligned(ink, caret):
        return abs(sum(ink) / 2 - sum(caret) / 2) <= 1

    def check_style(family):
        field.text_style = ft.TextStyle(font_family=family, size=14)
        field.value = '123123'
        field.hint_text = 'License key'
        field._password_revealed = True
        field._cursor_visible = True
        with_cursor = capture()
        field._cursor_visible = False
        value_only = capture()
        field.value = ''
        field.hint_text = None
        blank = capture()
        value_bbox = changed_bbox(value_only, blank)
        caret_bbox = changed_bbox(with_cursor, value_only)
        assert aligned(value_bbox, caret_bbox), (
            family, value_bbox, caret_bbox)

        field.hint_text = 'License key'
        field._cursor_visible = True
        with_cursor = capture()
        field._cursor_visible = False
        hint_only = capture()
        field.hint_text = None
        blank = capture()
        hint_bbox = changed_bbox(hint_only, blank)
        caret_bbox = changed_bbox(with_cursor, hint_only)
        assert aligned(hint_bbox, caret_bbox), (
            family, hint_bbox, caret_bbox)

    try:
        for family in ('Consolas', None):
            check_style(family)
    finally:
        renderer.close()
        window.destroy()
        pygame.quit()


def check_gl_redraw_removes_old_caret():
    """A transparent redraw must replace the previous screen pixels."""
    pygame.init()
    window = pygame.Window(size=(100, 80), hidden=True, opengl=True)
    renderer = GLRenderer(window, logical_size=(100, 80))

    def pixel(target, width, height, x, y, components):
        data = target.read(components=components)
        start = ((height - y - 1) * width + x) * components
        return tuple(data[start:start + components])

    try:
        for caret_x in (30, 40, None):
            renderer.clear((39, 39, 39, 0))
            if caret_x is not None:
                renderer.fill_rect(10, 10, 60, 30, (200, 100, 100, 128))
                renderer.fill_rect(caret_x, 16, 4, 15, (255, 255, 255, 255))
            renderer._flush_rects()
            frame = pixel(renderer._frame_target, 200, 160, 62, 40, 4)
            renderer._resolve_to_window()
            screen = pixel(renderer.ctx.screen, 100, 80, 31, 20, 3)
            assert screen == frame[:3], (caret_x, frame, screen)
            renderer._use_frame_target()
    finally:
        renderer.close()
        window.destroy()
        pygame.quit()


if __name__ == '__main__':
    check()
    check_textfield_vertical_alignment()
    check_gl_redraw_removes_old_caret()
    print('INPUT CHECKS PASS')
