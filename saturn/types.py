"""Enums and value types shared by controls (flet 1.0 subset)."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


# -- enums (member values mirror flet exactly) --------------------------------
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
    """Flet/Flutter animation curve names."""
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
    """Flet-compatible duration value."""
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
    """flet Theme subset. font_family overrides the default UI font
    (bundled Inter) for the whole app via page.theme."""
    font_family: str | None = None
    # ponytail: accepted for flet parity, stored only — M3 tone generation
    # from the seed (primary/surface hues) when a port needs it
    color_scheme_seed: str | None = None


@dataclass
class MaterialExpressiveTheme(Theme):
    """Compose MaterialExpressiveTheme's default light color roles."""
    expressive: bool = True


class BoxFit(enum.Enum):
    FILL = "fill"
    CONTAIN = "contain"
    COVER = "cover"
    NONE = "none"
    SCALE_DOWN = "scaleDown"


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
    """Flet 1.0 outline border used by form-field controls."""
    border_radius: object = 4.0
    side: BorderSide = field(default_factory=BorderSide)
    gap_padding: float = 4.0


@dataclass
class Border:
    left: BorderSide = field(default_factory=lambda: BorderSide())
    top: BorderSide = field(default_factory=lambda: BorderSide())
    right: BorderSide = field(default_factory=lambda: BorderSide())
    bottom: BorderSide = field(default_factory=lambda: BorderSide())

    @classmethod
    def all(cls, width: float | None = None, color=None):
        # flet order: Border.all(width, color)
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


@dataclass
class Tooltip:
    """Flet-compatible tooltip value used by every Control.tooltip."""
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


# -- shorthand resolvers (flet *Value unions) ----------------------------------
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
