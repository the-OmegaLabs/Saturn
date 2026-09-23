"""Compose M3 Expressive toggle buttons (AndroidX 1.5.0-alpha28)."""
from .. import colors, motion
from ..event import fire
from .buttons import ExpressiveButton


_COLORS = {
    "filled": ("surfacecontainer", "onsurfacevariant", "primary", "onprimary"),
    "elevated": ("surfacecontainerlow", "primary", "primary", "onprimary"),
    "tonal": ("secondarycontainer", "onsecondarycontainer", "secondary", "onsecondary"),
    "outlined": (None, "onsurfacevariant", "inversesurface", "oninversesurface"),
}


class ToggleButton(ExpressiveButton):
    """A toggle with unchecked, checked and pressed shapes.

    ``on_change`` receives an event whose data is ``"true"`` or ``"false"``.
    The checked value can also be changed directly followed by ``update()``.
    """

    def __init__(self, content=None, *, checked=False, on_change=None,
                 variant="filled", size="small", **kwargs):
        if variant not in _COLORS:
            raise ValueError(f"invalid toggle button variant: {variant!r}")
        self.checked = bool(checked)
        self.variant = variant
        self.on_change = on_change
        self._last_checked = self.checked
        self._checked_progress = float(self.checked)
        self.variant_elevation = 1.0 if variant == "elevated" else 0.0
        super().__init__(content, size=size, on_click=self._toggle, **kwargs)

    @property
    def variant_bg(self):
        return _COLORS[self.variant][2 if self.checked else 0]

    @property
    def variant_fg(self):
        return _COLORS[self.variant][3 if self.checked else 1]

    @property
    def variant_border(self):
        return colors.Colors.OUTLINE_VARIANT if self.variant == "outlined" and not self.checked else None

    def _radius(self, height):
        square, pressed = self._metrics()[-2:]
        normal = height / 2 + (square - height / 2) * self._checked_progress
        return normal + (pressed - normal) * self._shape_progress

    def _toggle(self, _event=None):
        if self.disabled:
            return
        self.checked = not self.checked
        self.update()
        fire(self, "change", "true" if self.checked else "false")

    def _prepare_animations(self, now):
        super()._prepare_animations(now)
        if self.checked != self._last_checked:
            self._last_checked = self.checked
            self._animate_internal("_checked_progress", float(self.checked),
                                   motion.SHORT3, motion.EMPHASIZED, now=now)


class ElevatedToggleButton(ToggleButton):
    def __init__(self, content=None, **kwargs):
        super().__init__(content, variant="elevated", **kwargs)


class FilledTonalToggleButton(ToggleButton):
    def __init__(self, content=None, **kwargs):
        super().__init__(content, variant="tonal", **kwargs)


class OutlinedToggleButton(ToggleButton):
    def __init__(self, content=None, **kwargs):
        super().__init__(content, variant="outlined", **kwargs)
