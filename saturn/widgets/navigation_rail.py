"""Material NavigationRail: a vertical strip of navigation destinations."""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Unpack

import enum

from .. import colors
from ..control import Control, ControlOptions
from ..event import fire
from ..types import Alignment, CrossAxisAlignment, as_padding
from ._compat import value
from .basic import Icon
from .containers import Column, Container, Row
from .text import Text


class NavigationRailLabelType(enum.Enum):
    """How destination labels are shown on an unextended rail."""
    NONE = "none"
    ALL = "all"
    SELECTED = "selected"


class NavigationRailDestination(Control):
    """One destination: icon plus optional label (a data holder, not laid out
    directly; the owning rail builds a button for it)."""

    def __init__(self, icon=None, *, selected_icon=None, label=None,
                 padding=None, indicator_color=None, indicator_shape=None, **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.icon = icon
        self.selected_icon = selected_icon
        self.label = label
        self.padding = padding
        self.indicator_color = indicator_color
        self.indicator_shape = indicator_shape


class NavigationRail(Control):
    """Material 3 navigation rail.

    Icons only by default (label_type None); indicator pill behind the
    selected icon unless use_indicator=False. on_change fires with the newly
    selected index in event.data, mirroring flet.
    """

    def __init__(self, destinations=None, *, selected_index=None,
                 extended=False, label_type=None, bgcolor=None,
                 indicator_color=None, leading=None, trailing=None,
                 min_width=None, min_height=None, min_extended_width=None,
                 group_alignment=None, use_indicator=None, on_change=None,
                 **base: Unpack[ControlOptions]):
        super().__init__(**base)
        self.destinations = list(destinations or [])
        self.selected_index = selected_index
        self.extended = bool(extended)
        self.label_type = label_type
        self.bgcolor = bgcolor
        self.indicator_color = indicator_color
        self.leading = leading
        self.trailing = trailing
        self.min_width = min_width
        self.min_height = min_height
        self.min_extended_width = min_extended_width
        self.group_alignment = (group_alignment if group_alignment is not None
                                else -1.0)
        self.use_indicator = True if use_indicator is None else bool(use_indicator)
        self.on_change = on_change
        self._items = []
        self._rebuild_items()

    @property
    def selected(self):
        return self.selected_index

    @selected.setter
    def selected(self, index):
        self._select(index)

    def _children(self):
        return self._items

    def _select(self, index):
        if not 0 <= index < len(self.destinations):
            return
        changed = self.selected_index != index
        self.selected_index = index
        self._rebuild_items()
        self.update()
        if changed:
            fire(self, "change", index)

    def _label_mode(self):
        mode = value(self.label_type)
        return (getattr(mode, "value", mode) if mode is not None else None)

    def _item_height(self, show_label):
        return 80 if self.extended or show_label else 56

    def _rebuild_items(self):
        mode = self._label_mode()
        show_all = mode == "all" or self.extended
        show_selected = mode == "selected"
        width = (self.min_width if self.min_width is not None
                 else 256 if self.extended else 72)
        items = []
        for index, destination in enumerate(self.destinations):
            selected = self.selected_index == index
            show_label = show_all or (show_selected and selected)
            icon_value = (destination.selected_icon if selected and
                          destination.selected_icon is not None else destination.icon)
            if self.use_indicator and selected:
                icon_color = colors.Colors.ON_SECONDARY_CONTAINER
            else:
                icon_color = (colors.Colors.ON_SURFACE if selected
                              else colors.Colors.ON_SURFACE_VARIANT)
            icon = (icon_value if isinstance(icon_value, Control) else
                    Icon(icon_value, size=24, color=icon_color))
            indicator_color = None
            if selected and self.use_indicator:
                indicator_color = (destination.indicator_color or
                                   self.indicator_color or
                                   colors.Colors.SECONDARY_CONTAINER)
            indicator = Container(icon, width=56, height=32, border_radius=16,
                                  alignment=Alignment.CENTER,
                                  bgcolor=indicator_color)
            if self.extended:
                content = Row(indicator, spacing=12)
                if show_label and destination.label is not None:
                    content.controls.append(self._label_control(destination, selected))
            else:
                parts = [indicator]
                if show_label and destination.label is not None:
                    parts.append(self._label_control(destination, selected))
                content = Column(*parts, spacing=6,
                                 horizontal_alignment=CrossAxisAlignment.CENTER)
            item = Container(content, width=width,
                             height=self._item_height(show_label),
                             alignment=Alignment.CENTER, ink=True,
                             margin=destination.padding,
                             on_click=lambda event=None, index=index: self._select(index))
            items.append(item)
        self._items = items

    def _label_control(self, destination, selected):
        if isinstance(destination.label, Control):
            return destination.label
        return Text(destination.label, size=12,
                    color=colors.Colors.ON_SURFACE if selected
                    else colors.Colors.ON_SURFACE_VARIANT)

    def _intrinsic(self, max_w, max_h, scale):
        width = 0.0
        height = 0.0
        extras = [c for c in (self.leading, self.trailing) if c is not None]
        for child in [*extras, *self._items]:
            if not child.visible:
                continue
            w, h = child._intrinsic(max_w, max_h, scale)
            width, height = max(width, w), height + h + 4
        width = max(width, self.min_width or 0, self.min_extended_width or 0)
        height = max(height - 4, self.min_height or 0)
        if max_h is not None:
            height = min(height, max_h)
        if max_w is not None:
            width = min(width, max_w)
        return (self._width if self._width is not None else width,
                self._height if self._height is not None else height)

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        alignment = max(-1.0, min(1.0, float(self.group_alignment)))
        group = [c for c in self._items if c.visible]
        extras_top = self.leading if self.leading is not None and self.leading.visible else None
        cursor = y
        if extras_top is not None:
            lw, lh = extras_top._intrinsic(w, h, scale)
            extras_top._place(x, cursor, w, lh, scale)
            cursor += lh + 4
        total = sum(item._intrinsic(w, h, scale)[1] + 4 for item in group) - 4
        if alignment < 0:
            top = cursor
        elif alignment > 0:
            top = y + h - total
        else:
            top = cursor + max(0.0, (y + h - cursor - total) / 2)
        for item in group:
            _, ih = item._intrinsic(w, h, scale)
            item._place(x, top, w, ih, scale)
            top += ih + 4
        if self.trailing is not None and self.trailing.visible:
            tw, th = self.trailing._intrinsic(w, h, scale)
            self.trailing._place(x, max(cursor + total + 4, y + h - th - 4), w, th, scale)

    def _draw(self, r, x, y):
        bgcolor = value(self.bgcolor)
        if bgcolor is not None:
            r.fill_rect(x, y, self._rect[2], self._rect[3],
                        colors.parse_color(bgcolor))
