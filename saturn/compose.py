"""Material 3 Expressive API grouped separately from Flet-style controls.

Most names reuse the existing public classes. Button variants wrap those
classes to opt into Expressive sizing while the Flet-style defaults stay put.
"""

from .types import MaterialExpressiveTheme
from .widgets import (
    ButtonGroup,
    ElevatedButton,
    ExpressiveButton,
    ExpressiveIconButton,
    FilledButton,
    FilledTonalButton,
    ExtendedFloatingActionButton,
    FilledTonalToggleButton,
    FloatingActionButton,
    FloatingActionButtonMenu,
    FloatingActionButtonMenuItem,
    FloatingToolbar,
    HorizontalFloatingToolbar,
    LargeFloatingActionButton,
    LinearWavyProgressIndicator,
    ListItem,
    LoadingIndicator,
    MediumFloatingActionButton,
    OutlinedButton,
    OutlinedToggleButton,
    SmallFloatingActionButton,
    SplitButton,
    ToggleButton,
    TextButton,
    ElevatedToggleButton,
    VerticalFloatingToolbar,
    WavyProgressIndicator,
    CircularWavyProgressIndicator,
)


class _ComposeElevatedButton(ElevatedButton):
    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


class _ComposeFilledButton(FilledButton):
    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


class _ComposeFilledTonalButton(FilledTonalButton):
    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


class _ComposeOutlinedButton(OutlinedButton):
    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


class _ComposeTextButton(TextButton):
    def __init__(self, content=None, *, size="small", shape="round", **kwargs):
        super().__init__(content, size=size, shape=shape, **kwargs)


class Compose:
    """Namespace for Saturn's Material 3 Expressive controls and theme."""

    Theme = MaterialExpressiveTheme
    MaterialExpressiveTheme = MaterialExpressiveTheme
    Button = ExpressiveButton
    IconButton = ExpressiveIconButton
    ExpressiveButton = ExpressiveButton
    ExpressiveIconButton = ExpressiveIconButton
    SplitButton = SplitButton
    ButtonGroup = ButtonGroup
    FilledButton = _ComposeFilledButton
    FilledTonalButton = _ComposeFilledTonalButton
    ElevatedButton = _ComposeElevatedButton
    OutlinedButton = _ComposeOutlinedButton
    TextButton = _ComposeTextButton
    ToggleButton = ToggleButton
    ElevatedToggleButton = ElevatedToggleButton
    FilledTonalToggleButton = FilledTonalToggleButton
    OutlinedToggleButton = OutlinedToggleButton
    FloatingActionButton = FloatingActionButton
    SmallFloatingActionButton = SmallFloatingActionButton
    MediumFloatingActionButton = MediumFloatingActionButton
    LargeFloatingActionButton = LargeFloatingActionButton
    ExtendedFloatingActionButton = ExtendedFloatingActionButton
    ListItem = ListItem
    LoadingIndicator = LoadingIndicator
    WavyProgressIndicator = WavyProgressIndicator
    LinearWavyProgressIndicator = LinearWavyProgressIndicator
    CircularWavyProgressIndicator = CircularWavyProgressIndicator
    FloatingToolbar = FloatingToolbar
    HorizontalFloatingToolbar = HorizontalFloatingToolbar
    VerticalFloatingToolbar = VerticalFloatingToolbar
    FloatingActionButtonMenu = FloatingActionButtonMenu
    FloatingActionButtonMenuItem = FloatingActionButtonMenuItem
