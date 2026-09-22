"""saturn — a Flet-1.0-compatible, self-drawn GUI framework.

Usage:
    import saturn as ft

    def main(page: ft.Page):
        page.add(ft.Text("Hello"))

    ft.run(main, backend=ft.Render.SOFTWARE)
"""
from types import SimpleNamespace

from .event import ControlEvent
from .app import App, Render, run
from ._gen.icons import Icons
from .colors import BASELINE_DARK, BASELINE_LIGHT, Colors, parse_color, theme_dark
from .control import Control
from .page import Page, Window
from .services import (
    FilePicker,
    FilePickerFile,
    FilePickerFileType,
    FilePickerResultEvent,
    FilePickerUploadEvent,
    FilePickerUploadFile,
)
from .types import (
    Alignment,
    Border,
    BorderRadius,
    BorderSide,
    BoxShadow,
    BoxFit,
    CrossAxisAlignment,
    FontWeight,
    KeyboardType,
    LabelPosition,
    MainAxisAlignment,
    Margin,
    Offset,
    Padding,
    ScrollMode,
    TextAlign,
    Theme,
    ThemeMode,
    TextOverflow,
    TextStyle,
)
from .widgets import (
    AlertDialog,
    Button,
    Card,
    Checkbox,
    Column,
    Container,
    Divider,
    Dropdown,
    DropdownOption,
    ElevatedButton,
    FilledButton,
    FilledTonalButton,
    GestureDetector,
    Icon,
    IconButton,
    Image,
    ListView,
    Option,
    OutlinedButton,
    ProgressBar,
    ProgressRing,
    Radio,
    RadioGroup,
    Row,
    Slider,
    SnackBar,
    Stack,
    Switch,
    Text,
    TextField,
    TextButton,
)

__all__ = [
    "App", "Render", "run", "ControlEvent",
    "Colors", "Icons", "parse_color",
    "Control", "Page", "Window", "Text", "Row", "Column", "Container",
    "Stack", "Divider", "Icon", "Image", "Card", "ProgressBar", "ProgressRing",
    "Button", "ElevatedButton", "FilledButton", "FilledTonalButton", "OutlinedButton",
    "TextButton", "IconButton",
    "TextField", "Checkbox", "Switch", "Radio", "RadioGroup", "Dropdown",
    "DropdownOption", "Option", "Slider", "AlertDialog", "SnackBar",
    "ListView", "GestureDetector",
    "FilePicker", "FilePickerFile", "FilePickerFileType",
    "FilePickerResultEvent", "FilePickerUploadEvent", "FilePickerUploadFile",
    "Alignment", "Border", "BorderRadius", "BorderSide", "BoxFit", "BoxShadow",
    "CrossAxisAlignment", "FontWeight", "KeyboardType", "LabelPosition",
    "MainAxisAlignment", "Margin", "Offset", "Padding", "ScrollMode",
    "TextAlign", "Theme", "ThemeMode", "TextOverflow", "TextStyle",
]
__version__ = "0.0.1"

# flet-style module aliases: ft.dropdown.Option(...)
dropdown = SimpleNamespace(Option=Option, DropdownOption=DropdownOption)
