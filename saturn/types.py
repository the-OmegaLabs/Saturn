"""Enums and value types shared by Saturn controls."""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field


# -- enums --------------------------------
class MainAxisAlignment(enum.Enum):
    START = "start"
    END = "end"
    CENTER = "center"
    SPACE_BETWEEN = "spaceBetween"
    SPACE_AROUND = "spaceAround"
    SPACE_EVENLY = "spaceEvenly"


class CrossAxisAlignment(enum.Enum):
    START = "start"
    END = "end"
    CENTER = "center"
    STRETCH = "stretch"
    BASELINE = "baseline"


class TextAlign(enum.Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"
    START = "start"
    END = "end"


class FontWeight(enum.Enum):
    W_100 = "w100"
    W_200 = "w200"
    W_300 = "w300"
    W_400 = "w400"
    NORMAL = "normal"
    W_500 = "w500"
    W_600 = "w600"
    W_700 = "w700"
    BOLD = "bold"
    W_800 = "w800"
    W_900 = "w900"


class ThemeMode(enum.Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class TextOverflow(enum.Enum):
    CLIP = "clip"
    ELLIPSIS = "ellipsis"
    FADE = "fade"
    VISIBLE = "visible"


class LabelPosition(enum.Enum):
    RIGHT = "right"
    LEFT = "left"


class ScrollMode(enum.Enum):
    NONE = "none"
    AUTO = "auto"
    HIDDEN = "hidden"
    ALWAYS = "always"


class KeyboardType(enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    MULTILINE = "multiline"
    PASSWORD = "visiblePassword"
    NONE = "none"


class TooltipTriggerMode(enum.Enum):
    MANUAL = "manual"
    TAP = "tap"
    LONG_PRESS = "long_press"


class AnimationCurve(enum.Enum):
    """Available animation easing curves."""
    BOUNCE_IN = "bounceIn"
    BOUNCE_IN_OUT = "bounceInOut"
    BOUNCE_OUT = "bounceOut"
    DECELERATE = "decelerate"
    EASE = "ease"
    EASE_IN = "easeIn"
    EASE_IN_BACK = "easeInBack"
    EASE_IN_CIRC = "easeInCirc"
    EASE_IN_CUBIC = "easeInCubic"
    EASE_IN_EXPO = "easeInExpo"
    EASE_IN_OUT = "easeInOut"
    EASE_IN_OUT_BACK = "easeInOutBack"
    EASE_IN_OUT_CIRC = "easeInOutCirc"
    EASE_IN_OUT_CUBIC = "easeInOutCubic"
    EASE_IN_OUT_CUBIC_EMPHASIZED = "easeInOutCubicEmphasized"
    EASE_IN_OUT_EXPO = "easeInOutExpo"
    EASE_IN_OUT_QUAD = "easeInOutQuad"
    EASE_IN_OUT_QUART = "easeInOutQuart"
    EASE_IN_OUT_QUINT = "easeInOutQuint"
    EASE_IN_OUT_SINE = "easeInOutSine"
    EASE_IN_QUAD = "easeInQuad"
    EASE_IN_QUART = "easeInQuart"
    EASE_IN_QUINT = "easeInQuint"
    EASE_IN_SINE = "easeInSine"
    EASE_IN_TO_LINEAR = "easeInToLinear"
    EASE_OUT = "easeOut"
    EASE_OUT_BACK = "easeOutBack"
    EASE_OUT_CIRC = "easeOutCirc"
    EASE_OUT_CUBIC = "easeOutCubic"
    EASE_OUT_EXPO = "easeOutExpo"
    EASE_OUT_QUAD = "easeOutQuad"
    EASE_OUT_QUART = "easeOutQuart"
    EASE_OUT_QUINT = "easeOutQuint"
    EASE_OUT_SINE = "easeOutSine"
    ELASTIC_IN = "elasticIn"
    ELASTIC_IN_OUT = "elasticInOut"
    ELASTIC_OUT = "elasticOut"
    FAST_LINEAR_TO_SLOW_EASE_IN = "fastLinearToSlowEaseIn"
    FAST_OUT_SLOWIN = "fastOutSlowIn"
    LINEAR = "linear"
    LINEAR_TO_EASE_OUT = "linearToEaseOut"
    SLOW_MIDDLE = "slowMiddle"


@dataclass
class Duration:
    """Duration value with time-unit conversion helpers."""
    microseconds: int = 0
    milliseconds: int = 0
    seconds: int = 0
    minutes: int = 0
    hours: int = 0
    days: int = 0

    @property
    def in_microseconds(self) -> int:
        return (self.microseconds + self.milliseconds * 1_000
                + self.seconds * 1_000_000 + self.minutes * 60_000_000
                + self.hours * 3_600_000_000 + self.days * 86_400_000_000)

    @property
    def in_milliseconds(self) -> int:
        return self.in_microseconds // 1_000


@dataclass
class Animation:
    duration: object = field(default_factory=Duration)
    curve: AnimationCurve = AnimationCurve.LINEAR


@dataclass
class Theme:
    """Application theme. font_family overrides the default UI font
    (bundled Inter) for the whole app via page.theme."""
    font_family: str | None = None
    # Supported seed colors select a predefined Material 3 role palette.
    color_scheme_seed: str | None = None


@dataclass
class MaterialExpressiveTheme(Theme):
    """Expressive default light color roles."""
    expressive: bool = True


class BoxFit(enum.Enum):
    FILL = "fill"
    CONTAIN = "contain"
    COVER = "cover"
    NONE = "none"
    SCALE_DOWN = "scaleDown"
    FIT_WIDTH = "fitWidth"
    FIT_HEIGHT = "fitHeight"


class ControlState(enum.Enum):
    HOVERED = "hovered"
    FOCUSED = "focused"
    PRESSED = "pressed"
    DRAGGED = "dragged"
    SELECTED = "selected"
    SCROLLED_UNDER = "scrolledUnder"
    DISABLED = "disabled"
    ERROR = "error"
    DEFAULT = "default"


class TextCapitalization(enum.Enum):
    NONE = "none"
    CHARACTERS = "characters"
    WORDS = "words"
    SENTENCES = "sentences"


class TextAffinity(enum.Enum):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"


class MouseCursor(enum.Enum):
    BASIC = "basic"
    CLICK = "click"
    TEXT = "text"
    VERTICAL_TEXT = "verticalText"
    FORBIDDEN = "forbidden"
    NONE = "none"
    MOVE = "move"
    GRAB = "grab"
    GRABBING = "grabbing"
    PRECISE = "precise"
    WAIT = "wait"
    PROGRESS = "progress"
    RESIZE_LEFT_RIGHT = "resizeLeftRight"
    RESIZE_UP_DOWN = "resizeUpDown"
    RESIZE_UP_LEFT_DOWN_RIGHT = "resizeUpLeftDownRight"
    RESIZE_UP_RIGHT_DOWN_LEFT = "resizeUpRightDownLeft"
    RESIZE_COLUMN = "resizeColumn"
    RESIZE_ROW = "resizeRow"
    RESIZE_LEFT = "resizeLeft"
    RESIZE_RIGHT = "resizeRight"
    RESIZE_UP = "resizeUp"
    RESIZE_DOWN = "resizeDown"
    RESIZE_UP_LEFT = "resizeUpLeft"
    RESIZE_UP_RIGHT = "resizeUpRight"
    RESIZE_DOWN_LEFT = "resizeDownLeft"
    RESIZE_DOWN_RIGHT = "resizeDownRight"
    ALIAS = "alias"
    ALL_SCROLL = "allScroll"
    CELL = "cell"
    CONTEXT_MENU = "contextMenu"
    COPY = "copy"
    DISAPPEARING = "disappearing"
    HELP = "help"
    NO_DROP = "noDrop"
    ZOOM_IN = "zoomIn"
    ZOOM_OUT = "zoomOut"


class ImageRepeat(enum.Enum):
    NO_REPEAT = "noRepeat"
    REPEAT = "repeat"
    REPEAT_X = "repeatX"
    REPEAT_Y = "repeatY"


class FilterQuality(enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClipBehavior(enum.Enum):
    NONE = "none"
    HARD_EDGE = "hardEdge"
    ANTI_ALIAS = "antiAlias"
    ANTI_ALIAS_WITH_SAVE_LAYER = "antiAliasWithSaveLayer"


class BoxShape(enum.Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"


class StrokeCap(enum.Enum):
    ROUND = "round"
    SQUARE = "square"
    BUTT = "butt"


class VisualDensity(enum.Enum):
    STANDARD = "standard"
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    ADAPTIVE_PLATFORM_DENSITY = "adaptivePlatformDensity"


@dataclass
class Alignment:
    """Child alignment inside a container; -1..1 on both axes."""
    x: float = 0.0
    y: float = 0.0

    CENTER = None  # class constants wired below the dataclass body
    TOP_LEFT = None
    TOP_CENTER = None
    TOP_RIGHT = None
    CENTER_LEFT = None
    CENTER_RIGHT = None
    BOTTOM_LEFT = None
    BOTTOM_CENTER = None
    BOTTOM_RIGHT = None


Alignment.CENTER = Alignment(0, 0)
Alignment.TOP_LEFT = Alignment(-1, -1)
Alignment.TOP_CENTER = Alignment(0, -1)
Alignment.TOP_RIGHT = Alignment(1, -1)
Alignment.CENTER_LEFT = Alignment(-1, 0)
Alignment.CENTER_RIGHT = Alignment(1, 0)
Alignment.BOTTOM_LEFT = Alignment(-1, 1)
Alignment.BOTTOM_CENTER = Alignment(0, 1)
Alignment.BOTTOM_RIGHT = Alignment(1, 1)


# -- box decoration value types -----------------------------------------------
@dataclass
class Padding:
    left: float = 0.0
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0

    @classmethod
    def all(cls, value: float):
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, vertical: float = 0.0, horizontal: float = 0.0):
        return cls(horizontal, vertical, horizontal, vertical)

    @classmethod
    def only(cls, left: float = 0.0, top: float = 0.0, right: float = 0.0,
             bottom: float = 0.0):
        return cls(left, top, right, bottom)

    @classmethod
    def zero(cls):
        return cls()


class Margin(Padding):
    pass


@dataclass
class BorderRadius:
    top_left: float = 0.0
    top_right: float = 0.0
    bottom_right: float = 0.0
    bottom_left: float = 0.0

    @classmethod
    def all(cls, radius: float):
        return cls(radius, radius, radius, radius)

    @classmethod
    def horizontal(cls, left: float = 0.0, right: float = 0.0):
        return cls(left, right, right, left)

    @classmethod
    def vertical(cls, top: float = 0.0, bottom: float = 0.0):
        return cls(top, top, bottom, bottom)

    @classmethod
    def only(cls, top_left: float = 0.0, top_right: float = 0.0,
             bottom_right: float = 0.0, bottom_left: float = 0.0):
        return cls(top_left, top_right, bottom_right, bottom_left)


@dataclass
class BorderSide:
    width: float = 1.0
    color: object = None

    @classmethod
    def none(cls):
        return cls(0, None)


@dataclass
class OutlineInputBorder:
    """Outline border configuration for form fields."""
    border_radius: object = 4.0
    side: BorderSide = field(default_factory=BorderSide)
    gap_padding: float = 4.0


@dataclass
class NoInputBorder:
    """Remove the input outline and underline."""


@dataclass
class UnderlineInputBorder:
    """Input underline configuration."""
    border_radius: object = 4.0
    side: BorderSide = field(default_factory=BorderSide)


@dataclass
class Border:
    left: BorderSide = field(default_factory=lambda: BorderSide())
    top: BorderSide = field(default_factory=lambda: BorderSide())
    right: BorderSide = field(default_factory=lambda: BorderSide())
    bottom: BorderSide = field(default_factory=lambda: BorderSide())

    @classmethod
    def all(cls, width: float | None = None, color=None):
        # Argument order: Border.all(width, color)
        side = BorderSide(width if width is not None else 1.0, color)
        return cls(side, side, side, side)

    @classmethod
    def symmetric(cls, vertical: BorderSide | None = None,
                  horizontal: BorderSide | None = None):
        v = vertical or BorderSide.none()
        h = horizontal or BorderSide.none()
        return cls(h, v, h, v)

    @classmethod
    def only(cls, left: BorderSide | None = None, top: BorderSide | None = None,
             right: BorderSide | None = None, bottom: BorderSide | None = None):
        return cls(left or BorderSide.none(), top or BorderSide.none(),
                   right or BorderSide.none(), bottom or BorderSide.none())


@dataclass
class Offset:
    x: float = 0.0
    y: float = 0.0
    transform_hit_tests: bool = True
    filter_quality: object = None


@dataclass
class Scale:
    scale: float | None = None
    scale_x: float | None = None
    scale_y: float | None = None
    alignment: Alignment | None = None
    origin: Offset | None = None
    transform_hit_tests: bool = True
    filter_quality: object = None


@dataclass
class Rotate:
    angle: float = 0.0
    alignment: Alignment | None = None
    origin: Offset | None = None
    transform_hit_tests: bool = True
    filter_quality: object = None


@dataclass
class BoxShadow:
    spread_radius: float = 0.0
    blur_radius: float = 0.0
    color: object = "#000000"
    offset: Offset = field(default_factory=Offset)


class BlurTileMode(enum.Enum):
    """Edge sampling mode for ``Blur``.

    Only ``CLAMP`` is implemented (edge samples clamp) for software and
    OpenGL. Unimplemented Flet names (``mirror`` / ``repeated`` / ``decal``)
    are intentionally absent — no sticker graveyard on the enum.
    """
    CLAMP = "clamp"


@dataclass
class Blur:
    """Gaussian blur sigmas for Container.blur (Flet-compatible)."""
    sigma_x: float = 0.0
    sigma_y: float = 0.0
    tile_mode: BlurTileMode = BlurTileMode.CLAMP


def _finite_blur_sigma(value) -> float:
    """Coerce a blur sigma; reject NaN/Inf so they never reach GL uniforms."""
    sigma = float(value)
    if not math.isfinite(sigma):
        raise ValueError("blur sigma must be a finite number")
    return sigma


def _clamp_only_tile_mode(mode) -> BlurTileMode:
    """Only CLAMP exists / is accepted; reject unknown tile_mode values."""
    if mode is None or mode is BlurTileMode.CLAMP:
        return BlurTileMode.CLAMP
    raw = getattr(mode, "value", mode)
    if isinstance(mode, BlurTileMode):
        # Future-proof if more members are added later.
        if mode is not BlurTileMode.CLAMP:
            raise ValueError(
                f"BlurTileMode.{mode.name} is not supported; only "
                f"BlurTileMode.CLAMP is implemented (edge samples clamp)"
            )
        return mode
    try:
        mode = BlurTileMode(raw)
    except ValueError as exc:
        raise ValueError(
            f"unsupported blur tile_mode {raw!r}; only "
            f"BlurTileMode.CLAMP is implemented (edge samples clamp)"
        ) from exc
    return mode


def as_blur(value) -> Blur | None:
    """Normalize Container.blur: None, number, (sx, sy), or Blur.

    ``tile_mode`` must be ``BlurTileMode.CLAMP`` (the only implemented mode).
    """
    if value is None:
        return None
    if isinstance(value, Blur):
        mode = _clamp_only_tile_mode(value.tile_mode)
        return Blur(_finite_blur_sigma(value.sigma_x), _finite_blur_sigma(value.sigma_y), mode)
    if isinstance(value, (int, float)):
        sigma = _finite_blur_sigma(value)
        return Blur(sigma, sigma)
    if isinstance(value, (tuple, list)):
        if not value:
            return Blur()
        sx = _finite_blur_sigma(value[0])
        sy = _finite_blur_sigma(value[1]) if len(value) > 1 else sx
        return Blur(sx, sy)
    raise TypeError(f"blur must be a number, pair, or Blur, got {type(value)!r}")


class SliderInteraction(enum.Enum):
    TAP_AND_SLIDE = "tapAndSlide"
    TAP_ONLY = "tapOnly"
    SLIDE_ONLY = "slideOnly"
    SLIDE_THUMB = "slideThumb"


@dataclass
class LinearGradient:
    colors: list
    begin: Alignment = field(default_factory=lambda: Alignment.CENTER_LEFT)
    end: Alignment = field(default_factory=lambda: Alignment.CENTER_RIGHT)
    stops: list | None = None


@dataclass
class RadialGradient:
    """Flet-compatible radial sweep: ``radius`` spans half the box diagonal,
    so 1.0 reaches the corners from ``center``. ``focal`` currently only
    supports the shared-center two-point form via ``focal_radius``."""
    colors: list
    center: Alignment = field(default_factory=lambda: Alignment(0, 0))
    radius: float = 0.5
    focal: Alignment | None = None
    focal_radius: float = 0.0
    stops: list | None = None


@dataclass
class TextStyle:
    size: float | None = None
    weight: FontWeight | None = None
    italic: bool = False
    color: object = None
    bgcolor: object = None
    font_family: str | None = None
    letter_spacing: float | None = None
    overflow: TextOverflow | None = None
    height: float | None = None
    word_spacing: float | None = None
    decoration: object = None
    decoration_color: object = None
    decoration_thickness: float | None = None


@dataclass
class TextSelection:
    base_offset: int = 0
    extent_offset: int = 0
    affinity: TextAffinity = TextAffinity.DOWNSTREAM
    directional: bool = False

    @property
    def start(self):
        return min(self.base_offset, self.extent_offset)

    @property
    def end(self):
        return max(self.base_offset, self.extent_offset)

    @property
    def is_collapsed(self):
        return self.base_offset == self.extent_offset


@dataclass
class InputFilter:
    allow: bool = True
    regex_string: str = ""
    replacement_string: str = ""


class NumbersOnlyInputFilter(InputFilter):
    """Allows only digits; every other character is stripped from the value."""

    def __init__(self):
        super().__init__(allow=True, regex_string=r"[0-9]*", replacement_string="")


class InputBorder(enum.Enum):
    """TextField border shape, mirroring flet's InputBorder."""
    NONE = "none"
    OUTLINE = "outline"
    UNDERLINE = "underline"
    FILLED = "filled"


@dataclass
class BoxConstraints:
    min_width: float = 0
    max_width: float = float("inf")
    min_height: float = 0
    max_height: float = float("inf")

    def __post_init__(self):
        if (self.min_width < 0 or self.min_height < 0 or
                self.max_width < self.min_width or self.max_height < self.min_height):
            raise ValueError("invalid box constraints")


@dataclass
class RoundedRectangleBorder:
    radius: object = 0
    side: BorderSide | None = None


@dataclass
class StadiumBorder:
    side: BorderSide | None = None


@dataclass
class CircleBorder:
    side: BorderSide | None = None


@dataclass
class ButtonStyle:
    color: object = None
    bgcolor: object = None
    overlay_color: object = None
    shadow_color: object = None
    elevation: object = None
    animation_duration: object = None
    padding: object = None
    side: object = None
    shape: object = None
    alignment: Alignment | None = None
    enable_feedback: bool | None = None
    text_style: object = None
    icon_size: object = None
    icon_color: object = None
    visual_density: VisualDensity | None = None
    mouse_cursor: object = None


class Ref:
    """Reference assigned when a control receives ``ref=``."""
    def __init__(self):
        self.current = None

    def __class_getitem__(cls, _control_type):
        return cls


@dataclass
class Tooltip:
    """Tooltip configuration used by Control.tooltip."""
    message: str
    decoration: object = None
    enable_feedback: bool | None = None
    vertical_offset: float | None = None
    margin: object = None
    padding: object = None
    bgcolor: object = None
    text_style: TextStyle | None = None
    text_align: TextAlign | None = None
    prefer_below: bool | None = None
    show_duration: object = None
    wait_duration: object = None
    exit_duration: object = None
    tap_to_dismiss: bool = True
    exclude_from_semantics: bool | None = False
    trigger_mode: TooltipTriggerMode | None = None
    mouse_cursor: object = None
    size_constraints: object = None


# -- shorthand value resolvers ----------------------------------
def as_padding(v) -> Padding:
    """PaddingValue: number | Padding | Margin | None."""
    if v is None:
        return Padding.zero()
    if isinstance(v, (int, float)):
        return Padding.all(v)
    return v  # Padding or Margin


def as_border_radius(v) -> BorderRadius:
    """BorderRadiusValue: number | BorderRadius."""
    if v is None:
        return BorderRadius()
    if isinstance(v, (int, float)):
        return BorderRadius.all(v)
    return v


def font_bold(weight) -> bool:
    """pygame.font only does bold on/off; treat w600+ as bold."""
    if weight is None:
        return False
    w = weight.value if isinstance(weight, FontWeight) else str(weight)
    return w in ("bold", "w600", "w700", "w800", "w900")
