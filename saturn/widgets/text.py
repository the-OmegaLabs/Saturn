"""Text control. Icon/Image/Divider join this module in the widgets milestone."""
from __future__ import annotations

from .. import colors
from ..control import Control
from ..text import family_for, get_font, line_height, measure, wrap
from ..types import TextAlign, font_bold


class Text(Control):
    def __init__(self, value: str = "", *, size: float | None = None,
                 color=None, weight=None, italic: bool = False,
                 text_align=None, max_lines: int | None = None,
                 no_wrap: bool = False, selectable: bool | None = None,
                 font_family: str | None = None, **base):
        super().__init__(**base)
        self.value = value
        self.size = size if size is not None else 14
        self.color = color            # None → theme on_surface
        self.weight = weight
        self.italic = italic
        self.text_align = text_align
        self.max_lines = max_lines
        self.no_wrap = no_wrap
        self.selectable = selectable
        self.font_family = font_family
        self._lines: list[str] = []
        self._line_h = 0.0

    # -- style helpers -----------------------------------------------------
    def _style(self, scale: float):
        return dict(scale=scale, bold=font_bold(self.weight), italic=self.italic,
                    family=family_for(self.value, self.font_family))

    # -- layout hooks (flex engine drives these) ---------------------------
    def _intrinsic(self, max_w, max_h, scale):
        kw = self._style(scale)
        if self.no_wrap:
            w, h = measure(self.value, self.size, **kw)
        else:
            lines = wrap(self.value, max_w if max_w is not None else 10_000,
                         self.size, max_lines=self.max_lines, **kw)
            f = get_font(self.size, **kw)
            w = max((f.size(l)[0] / scale for l in lines), default=0.0)
            h = line_height(self.size, scale=scale,
                            family=family_for(self.value, self.font_family)) * len(lines)
        if self._width is not None:
            w = self._width
        if self._height is not None:
            h = self._height
        return w, h

    def _place(self, x, y, w, h, scale):
        kw = self._style(scale)
        if not self.no_wrap:
            self._lines = wrap(self.value, w, self.size,
                               max_lines=self.max_lines, **kw)
            self._line_h = line_height(self.size, scale=scale,
                                       family=self._style(scale)["family"])
        self._rect = (x, y, w, h)

    def _draw(self, r, x, y):
        color = colors.parse_color(self.color or colors.Colors.ON_SURFACE)
        f = get_font(self.size, **self._style(r.scale))
        align = self.text_align or TextAlign.START
        w = self._rect[2]
        for line in self._lines:
            surf = f.render(line, True, color)
            lw = surf.get_width() / r.scale
            if align in (TextAlign.CENTER, TextAlign.JUSTIFY):
                ox = (w - lw) / 2
            elif align in (TextAlign.RIGHT, TextAlign.END):
                ox = w - lw
            else:
                ox = 0.0
            r.blit(surf, x + ox, y, alpha=self.opacity)
            y += self._line_h
