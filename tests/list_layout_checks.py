"""Exact list geometry and pixels for overflow beyond the preload margin."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame
import saturn as st
from saturn.renderer.software import SoftwareRenderer
from saturn.widgets.scrolling import _OVERSCAN


def render_reference(listing, renderer):
    renderer.clear('#000000')
    x, y, w, h = listing._rect
    renderer.clip_push(x, y, w, h)
    ox = -listing._offset if listing.horizontal else 0
    oy = -listing._offset if not listing.horizontal else 0
    for child in listing._placed_controls:
        child._place(*child._rect, renderer.scale)
        child._draw_all(renderer, ox, oy)
    renderer.clip_pop()
    return pygame.image.tobytes(renderer.screenshot(), 'RGBA')


def compare_pixels(listing, renderer):
    expected = render_reference(listing, renderer)
    renderer.clear('#000000')
    listing._draw_all(renderer)
    actual = pygame.image.tobytes(renderer.screenshot(), 'RGBA')
    assert actual == expected, 'Culled rendering lost visible overflow pixels'
    assert any(value for index, value in enumerate(actual) if index % 4 != 3), 'Empty fixture'


def check_overflow(renderer):
    # The row itself is 200 pixels below the top of a 100-pixel viewport,
    # outside the 96-pixel preload margin. Its large shadow is still visible.
    rows = [st.Container(height=20) for _ in range(60)]
    rows[10].bgcolor = '#FF0000'
    rows[10].shadow = st.BoxShadow(blur_radius=180, color='#FF0000')
    listing = st.ListView(controls=rows)
    listing._place(0, 0, 180, 100, renderer.scale)
    assert listing._paint_guard_before >= 180 > _OVERSCAN
    expected = render_reference(listing, renderer)
    before, after = listing._paint_guard_before, listing._paint_guard_after
    listing._paint_guard_before = listing._paint_guard_after = 0
    renderer.clear('#000000')
    listing._draw_all(renderer)
    assert pygame.image.tobytes(renderer.screenshot(), 'RGBA') != expected
    listing._paint_guard_before, listing._paint_guard_after = before, after
    compare_pixels(listing, renderer)
    listing.page = SimpleNamespace(_layout_dirty=False)
    listing._place(0, 0, 100, 100, renderer.scale)
    compare_pixels(listing, renderer)

    # Offset an offscreen row and a nested descendant back into view.
    rows = [st.Container(height=20) for _ in range(60)]
    rows[18].bgcolor = '#00FF00'
    rows[18].offset = st.Offset(0, -14)
    rows[24].content = st.Container(bgcolor='#0000FF', offset=st.Offset(0, -20))
    listing = st.ListView(controls=rows)
    listing._place(0, 0, 180, 100, renderer.scale)
    compare_pixels(listing, renderer)

    # Both axes use the same overflow-aware candidate bounds.
    rows = [st.Container(width=20) for _ in range(60)]
    rows[18].bgcolor = '#FF0000'
    rows[18].offset = st.Offset(-14, 0)
    listing = st.ListView(controls=rows, horizontal=True)
    listing._place(0, 0, 180, 100, renderer.scale)
    compare_pixels(listing, renderer)

    # Interpolating an offset must cover both its current value and target.
    rows[18]._animation_overrides['offset'] = st.Offset(-13, 0)
    listing._place(0, 0, 180, 100, renderer.scale)
    compare_pixels(listing, renderer)


def check_exact_layout(renderer):
    page = SimpleNamespace(_layout_dirty=True)
    rows = [st.Container(
        content=st.Text('row %d ' % index + 'word ' * (index % 16 + 1)),
        padding=3, margin=st.Margin(top=index % 3, bottom=index % 2),
        visible=index % 11 != 0) for index in range(200)]
    listing = st.ListView(controls=rows, spacing=2)
    listing.page = page
    for width in (180, 100, 200, 180):
        listing._place(0, 0, width, 100, renderer.scale)
        position = 0
        for row in rows:
            if not row.visible:
                continue
            margin = row.margin
            _, height = row._intrinsic(width, None, renderer.scale)
            assert row._rect[1] == position + margin.top
            assert row._rect[3] == height
            position += height + margin.top + margin.bottom + 2
        assert listing._content_size == position - 2
        assert listing._max_offset() == max(0, position - 2 - 100)
        page._layout_dirty = False

    # An unchanged content update, font revision and changed text continue
    # to use exact line counts; there are no estimated row heights.
    rows[1].content.value = 'changed ' * 100
    page._layout_dirty = True
    listing._place(0, 0, 180, 100, renderer.scale)
    assert rows[1]._rect[3] == rows[1]._intrinsic(180, None, renderer.scale)[1]

    ordinary = st.ListView(controls=[st.Container(height=20) for _ in range(1000)])
    ordinary._place(0, 0, 180, 100, renderer.scale)
    assert ordinary._paint_guard_before == ordinary._paint_guard_after == 0
    assert len(ordinary._candidates(-_OVERSCAN, 100 + _OVERSCAN)) <= 15


def check_updates(renderer):
    page = SimpleNamespace(_layout_dirty=True, repaint=lambda: None,
                           _reconcile_branch=lambda control: None)
    rows = [st.Container(height=20) for _ in range(60)]
    rows[0].bgcolor = '#123456'
    listing = st.ListView(controls=rows)
    listing._attach(page)
    listing._place(0, 0, 180, 100, renderer.scale)
    assert not listing._overflow_controls

    page._layout_dirty = False
    rows[18].bgcolor = '#FF0000'
    rows[18].offset = st.Offset(0, -14)
    rows[18].update()
    assert page._layout_dirty
    listing._place(0, 0, 180, 100, renderer.scale)
    assert rows[18] in listing._overflow_controls
    compare_pixels(listing, renderer)

    page._layout_dirty = False
    rows[18].offset = None
    rows[10].shadow = st.BoxShadow(blur_radius=180, color='#FF0000')
    rows[10].update()
    listing._place(0, 0, 180, 100, renderer.scale)
    assert rows[18] not in listing._overflow_controls
    compare_pixels(listing, renderer)

    page._layout_dirty = False
    rows[10].shadow = None
    listing.update()
    listing._place(0, 0, 180, 100, renderer.scale)
    assert not listing._overflow_controls
    assert listing._paint_guard_before == listing._paint_guard_after == 0
    compare_pixels(listing, renderer)

    # GPU elevation shadows use the same culling envelope as the retained
    # software reference, including reduced-resolution blur rounding.
    rows[10] = st.ElevatedButton('shadow', height=20)
    rows[10]._elevation_progress = 80
    listing.controls[10] = rows[10]
    listing.update()
    listing._place(0, 0, 180, 100, renderer.scale)
    assert listing._paint_guard_before > _OVERSCAN
    compare_pixels(listing, renderer)


def main():
    pygame.init()
    pygame.display.set_mode((200, 120), pygame.HIDDEN)
    renderer = SoftwareRenderer()
    try:
        check_overflow(renderer)
        check_exact_layout(renderer)
        check_updates(renderer)
        print('List layout checks passed: exact heights, shadows, offsets, elevation, animation targets, update invalidation.')
    finally:
        renderer.close()
        pygame.quit()


if __name__ == '__main__':
    main()
