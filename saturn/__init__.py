"""Saturn is a lightweight, GPU-accelerated UI frameworks.

Usage:
    import saturn as ft

    def main(page: ft.Page):
        page.add(ft.Text("Hello"))

    ft.run(main, backend=ft.Renderer.SOFTWARE)
"""
from types import SimpleNamespace

from .event import (
    ControlEvent, KeyboardEvent, PageResizeEvent, PlatformBrightnessChangeEvent,
    TextSelectionChangeEvent, LayoutSizeChangeEvent, RouteChangeEvent,
    RenderFailedEvent, RenderReadyEvent, FontOptimizeEvent,
)
from .app import App, Renderer, run

Render = Renderer
from ._gen.icons import Icons
from .colors import BASELINE_DARK, BASELINE_LIGHT, Colors, parse_color, theme_dark
from .control import Control
from .page import Page, Window
from .subpage import Subpage
from .widgets.shader import Shader, ShaderEffect, ShaderBuffer
from .window import WindowEvent, WindowEventType, WindowResizeEdge
from .services import (
    Clipboard,
    FilePicker,
    FilePickerFile,
    FilePickerFileType,
    FilePickerResultEvent,
    FilePickerUploadEvent,
    FilePickerUploadFile,
)
from .types import (
    ButtonStyle, ControlState, BoxConstraints, MouseCursor, Ref,
    RoundedRectangleBorder, StadiumBorder, CircleBorder,
    ImageRepeat, FilterQuality, ClipBehavior, BoxShape, StrokeCap, VisualDensity,
    TextSelection, TextAffinity, InputFilter, TextCapitalization,
    SliderInteraction, LinearGradient, RadialGradient,
    NoInputBorder, UnderlineInputBorder,
    Alignment,
    Animation,
    AnimationCurve,
    Border,
    BorderRadius,
    BorderSide,
    BoxShadow,
    BoxFit,
    CrossAxisAlignment,
    Duration,
    FontWeight,
    KeyboardType,
    LabelPosition,
    MainAxisAlignment,
    MaterialExpressiveTheme,
    Margin,
    Offset,
    OutlineInputBorder,
    Padding,
    Rotate,
    Scale,
    ScrollMode,
    TextAlign,
    Theme,
    ThemeMode,
    TextOverflow,
    TextStyle,
    Tooltip,
    TooltipTriggerMode,
)
from .widgets import (
    AlertDialog,
    DialogControl,
    Button,
    Card,
    Checkbox,
    Column,
    Container,
    Divider,
    VerticalDivider,
    WindowDragArea,
    Dropdown,
    DropdownOption,
    ElevatedButton,
    ExpressiveButton,
    ExpressiveIconButton,
    SplitButton,
    ButtonGroup,
    ToggleButton,
    ElevatedToggleButton,
    FilledTonalToggleButton,
    OutlinedToggleButton,
    FilledButton,
    FilledTonalButton,
    FloatingActionButton,
    SmallFloatingActionButton,
    MediumFloatingActionButton,
    LargeFloatingActionButton,
    ExtendedFloatingActionButton,
    GestureDetector,
    Icon,
    IconButton,
    Image,
    ListView,
    ListItem,
    LoadingIndicator,
    WavyProgressIndicator,
    LinearWavyProgressIndicator,
    CircularWavyProgressIndicator,
    FloatingToolbar,
    HorizontalFloatingToolbar,
    VerticalFloatingToolbar,
    FloatingActionButtonMenu,
    FloatingActionButtonMenuItem,
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
from .compose import Compose

__all__ = [
    "NoInputBorder", "UnderlineInputBorder",
    "Subpage", "Shader", "ShaderEffect", "ShaderBuffer", "SliderInteraction", "LinearGradient", "RadialGradient",
    "App", "Renderer", "Render", "run", "ControlEvent", "Compose",
    "KeyboardEvent", "PageResizeEvent", "PlatformBrightnessChangeEvent",
    "WindowEvent", "WindowEventType", "WindowResizeEdge",
    "TextSelectionChangeEvent", "LayoutSizeChangeEvent", "RouteChangeEvent",
    "RenderFailedEvent", "RenderReadyEvent", "FontOptimizeEvent",
    "ButtonStyle", "ControlState", "BoxConstraints", "MouseCursor", "Ref",
    "RoundedRectangleBorder", "StadiumBorder", "CircleBorder",
    "ImageRepeat", "FilterQuality", "ClipBehavior", "BoxShape", "StrokeCap", "VisualDensity",
    "TextSelection", "TextAffinity", "InputFilter", "TextCapitalization",
    "Colors", "Icons", "parse_color",
    "Control", "Page", "Window", "Text", "Row", "Column", "Container",
    "Stack", "Divider", "VerticalDivider", "WindowDragArea", "Icon", "Image", "Card", "ProgressBar", "ProgressRing",
    "Button", "ElevatedButton", "FilledButton", "FilledTonalButton", "OutlinedButton",
    "ExpressiveButton",
    "ExpressiveIconButton",
    "SplitButton", "ButtonGroup",
    "ToggleButton", "ElevatedToggleButton", "FilledTonalToggleButton",
    "OutlinedToggleButton",
    "TextButton", "IconButton",
    "FloatingActionButton", "SmallFloatingActionButton",
    "MediumFloatingActionButton", "LargeFloatingActionButton",
    "ExtendedFloatingActionButton",
    "TextField", "Checkbox", "Switch", "Radio", "RadioGroup", "Dropdown",
    "DropdownOption", "Option", "Slider", "AlertDialog", "SnackBar",
    "ListView", "GestureDetector",
    "ListItem",
    "LoadingIndicator", "WavyProgressIndicator", "LinearWavyProgressIndicator",
    "CircularWavyProgressIndicator",
    "FloatingToolbar", "HorizontalFloatingToolbar", "VerticalFloatingToolbar",
    "FloatingActionButtonMenu", "FloatingActionButtonMenuItem",
    "FilePicker", "FilePickerFile", "FilePickerFileType",
    "FilePickerResultEvent", "FilePickerUploadEvent", "FilePickerUploadFile",
    "Clipboard", "DialogControl",
    "Alignment", "Animation", "AnimationCurve", "Border", "BorderRadius",
    "BorderSide", "BoxFit", "BoxShadow", "CrossAxisAlignment", "Duration",
    "FontWeight", "KeyboardType", "LabelPosition",
    "MainAxisAlignment", "Margin", "Offset", "Padding", "ScrollMode",
    "MaterialExpressiveTheme",
    "OutlineInputBorder",
    "Rotate", "Scale", "TextAlign", "Theme", "ThemeMode", "TextOverflow", "TextStyle",
    "Tooltip", "TooltipTriggerMode",
]
__version__ = "0.1.0"

dropdown = SimpleNamespace(Option=Option, DropdownOption=DropdownOption)
