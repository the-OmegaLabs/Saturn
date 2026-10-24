"""Markdown control.

The native Flet Markdown control is backed by Flutter's markdown renderer.
Saturn does not have that renderer, so this implementation translates the
common Markdown blocks into Saturn controls.  Keeping the result as an
ordinary control tree means it participates in the same layout, scrolling,
selection, and event system as the rest of the toolkit.
"""
from __future__ import annotations

from dataclasses import dataclass
import enum
import re
import webbrowser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Unpack

from markdown_it import MarkdownIt

from .. import colors
from ..control import Control, ControlOptions
from ..event import ControlEvent, TextSelectionChangeEvent, dispatch_event
from ..types import (
    Border,
    BorderSide,
    CrossAxisAlignment,
    FontWeight,
    MainAxisAlignment,
    Padding,
    TextStyle,
)
from .containers import Column, Container, Divider, Row
from .basic import Image
from .text import Text


class MarkdownExtensionSet(enum.Enum):
    """Markdown extension presets accepted by :class:`Markdown`."""

    NONE = "none"
    COMMON_MARK = "commonMark"
    GITHUB_WEB = "gitHubWeb"
    GITHUB_FLAVORED = "gitHubFlavored"


class MarkdownCodeTheme(enum.Enum):
    """Names of the Pygments/Highlight.js themes understood by Flet.

    Saturn currently uses a neutral code-block style.  The enum is still
    provided so code written for Flet can pass a theme without failing.
    """

    DEFAULT = "default"
    GITHUB = "github"
    DARK = "dark"
    MONOKAI = "monokai"
    DRACULA = "dracula"
    DRAGULA = "dracula"
    VS = "vs"
    VS2015 = "vs2015"
    XCODE = "xcode"
    NORD = "nord"
    SOLARIZED_DARK = "solarized-dark"
    SOLARIZED_LIGHT = "solarized-light"
    A11Y_DARK = "a11y-dark"
    A11Y_LIGHT = "a11y-light"
    AGATE = "agate"
    ARTA = "arta"
    ATOM_ONE_DARK = "atom-one-dark"
    ATOM_ONE_LIGHT = "atom-one-light"
    ATOM_ONE_DARK_REASONABLE = "atom-one-dark-reasonable"
    AN_OLD_HOPE = "an-old-hope"
    ANDROID_STUDIO = "androidstudio"
    ARDUINO_LIGHT = "arduino-light"
    ASCETIC = "ascetic"
    ATELIER_CAVE_DARK = "atelier-cave-dark"
    ATELIER_CAVE_LIGHT = "atelier-cave-light"
    ATELIER_DUNE_DARK = "atelier-dune-dark"
    ATELIER_DUNE_LIGHT = "atelier-dune-light"
    ATELIER_ESTUARY_DARK = "atelier-estuary-dark"
    ATELIER_ESTUARY_LIGHT = "atelier-estuary-light"
    ATELIER_FOREST_DARK = "atelier-forest-dark"
    ATELIER_FOREST_LIGHT = "atelier-forest-light"
    ATELIER_HEATH_DARK = "atelier-heath-dark"
    ATELIER_HEATH_LIGHT = "atelier-heath-light"
    ATELIER_LAKESIDE_DARK = "atelier-lakeside-dark"
    ATELIER_LAKESIDE_LIGHT = "atelier-lakeside-light"
    ATELIER_PLATEAU_DARK = "atelier-plateau-dark"
    ATELIER_PLATEAU_LIGHT = "atelier-plateau-light"
    ATELIER_SAVANNA_DARK = "atelier-savanna-dark"
    ATELIER_SAVANNA_LIGHT = "atelier-savanna-light"
    ATELIER_SEASIDE_DARK = "atelier-seaside-dark"
    ATELIER_SEASIDE_LIGHT = "atelier-seaside-light"
    ATELIER_SULPHURPOOL_DARK = "atelier-sulphurpool-dark"
    ATELIER_SULPHURPOOL_LIGHT = "atelier-sulphurpool-light"
    BROWN_PAPER = "brown-paper"
    CODEPEN_EMBED = "codepen-embed"
    COLOR_BREWER = "color-brewer"
    DOCCO = "docco"
    FAR = "far"
    FOUNDATION = "foundation"
    GITHUB_GIST = "github-gist"
    GML = "gml"
    GOOGLE_CODE = "googlecode"
    GRADIENT_DARK = "gradient-dark"
    GRAYSCALE = "grayscale"
    GRUVBOX_DARK = "gruvbox-dark"
    GRUVBOX_LIGHT = "gruvbox-light"
    HOPSCOTCH = "hopscotch"
    HYBRID = "hybrid"
    IDEA = "idea"
    IR_BLACK = "ir-black"
    ISBL_EDITOR_DARK = "isbl-editor-dark"
    ISBL_EDITOR_LIGHT = "isbl-editor-light"
    KIMBIE_DARK = "kimbie.dark"
    KIMBIE_LIGHT = "kimbie.light"
    LIGHTFAIR = "lightfair"
    MAGULA = "magula"
    MONO_BLUE = "mono-blue"
    MONOKAI_SUBLIME = "monokai-sublime"
    OBSIDIAN = "obsidian"
    OCEAN = "ocean"
    NIGHT_OWL = "night-owl"
    PARAISEO_DARK = "paraiso-dark"
    PARAISEO_LIGHT = "paraiso-light"
    POJOAQUE = "pojoaque"
    PURE_BASIC = "purebasic"
    QT_CREATOR_DARK = "qtcreator_dark"
    QT_CREATOR_LIGHT = "qtcreator_light"
    RAILSCASTS = "railscasts"
    RAINBOW = "rainbow"
    ROUTERS = "routers"
    SCHOOL_BOOK = "school-book"
    SHADES_OF_PURPLE = "shades-of-purple"
    SUNBURST = "sunburst"
    TOMORROW_NIGHT_BLUE = "tomorrow-night-blue"
    TOMORROW_NIGHT_BRIGHT = "tomorrow-night-bright"
    TOMORROW_NIGHT_EIGHTIES = "tomorrow-night-eighties"
    TOMORROW_NIGHT = "tomorrow-night"
    TOMORROW = "tomorrow"
    XT256 = "xt256"
    ZENBURN = "zenburn"


@dataclass
class MarkdownStyleSheet:
    """Style overrides for Markdown element groups.

    The fields mirror the public Flet names.  Saturn uses the text styles,
    padding, spacing, and indentation fields directly; decoration fields are
    accepted for source compatibility and are intentionally left to the
    surrounding Saturn controls.
    """

    a_text_style: TextStyle | None = None
    p_text_style: TextStyle | None = None
    p_padding: object = None
    code_text_style: TextStyle | None = None
    h1_text_style: TextStyle | None = None
    h1_padding: object = None
    h2_text_style: TextStyle | None = None
    h2_padding: object = None
    h3_text_style: TextStyle | None = None
    h3_padding: object = None
    h4_text_style: TextStyle | None = None
    h4_padding: object = None
    h5_text_style: TextStyle | None = None
    h5_padding: object = None
    h6_text_style: TextStyle | None = None
    h6_padding: object = None
    em_text_style: TextStyle | None = None
    strong_text_style: TextStyle | None = None
    del_text_style: TextStyle | None = None
    blockquote_text_style: TextStyle | None = None
    img_text_style: TextStyle | None = None
    checkbox_text_style: TextStyle | None = None
    block_spacing: float | None = None
    list_indent: float | None = None
    list_bullet_text_style: TextStyle | None = None
    list_bullet_padding: object = None
    table_head_text_style: TextStyle | None = None
    table_body_text_style: TextStyle | None = None
    table_head_text_align: object = None
    table_padding: object = None
    table_cells_padding: object = None
    table_cells_decoration: object = None
    blockquote_padding: object = None
    blockquote_decoration: object = None
    codeblock_padding: object = None
    codeblock_decoration: object = None
    horizontal_rule_decoration: object = None
    blockquote_alignment: object = None
    codeblock_alignment: object = None
    h1_alignment: object = None
    h2_alignment: object = None
    h3_alignment: object = None
    h4_alignment: object = None
    h5_alignment: object = None
    h6_alignment: object = None
    text_alignment: object = None
    ordered_list_alignment: object = None
    unordered_list_alignment: object = None


class MarkdownCustomCodeTheme:
    """Per-token code styles compatible with Flet's custom theme object."""

    def __init__(self, *args, **styles):
        if args:
            if len(args) != 1 or not isinstance(args[0], dict):
                raise TypeError("MarkdownCustomCodeTheme accepts keyword styles")
            styles = {**args[0], **styles}
        for name, style in styles.items():
            setattr(self, name, style)

    def __getattr__(self, name):
        # Flet exposes every Pygments token field and returns ``None`` for a
        # field that was not overridden.  Keep that convenient lookup without
        # silently accepting arbitrary misspelled constructor arguments.
        if name in {
            "addition", "attr", "attribute", "built_in", "builtin_name",
            "bullet", "class_name", "code", "comment", "deletion", "doctag",
            "emphasis", "formula", "function", "keyword", "link", "link_label",
            "literal", "meta", "meta_keyword", "meta_string", "name", "number",
            "operator", "params", "pattern_match", "quote", "regexp", "root",
            "section", "selector_attr", "selector_class", "selector_id",
            "selector_pseudo", "selector_tag", "string", "strong", "stronge",
            "subst", "subtr", "symbol", "tag", "template_tag",
            "template_variable", "title", "type", "variable",
        }:
            return None
        raise AttributeError(name)

    def __repr__(self):  # pragma: no cover - convenience for debugging
        values = self.__dict__
        body = ", ".join(f"{key}={value!r}" for key, value in values.items())
        return f"MarkdownCustomCodeTheme({body})"


@dataclass
class _InlinePart:
    text: str = ""
    strong: bool = False
    emphasis: bool = False
    deleted: bool = False
    code: bool = False
    href: str | None = None
    image_src: str | None = None
    break_kind: str | None = None


class _MarkdownListItem(Control):
    """Lay out a list marker and its content using the actual remaining width."""

    def __init__(self, marker, content, *, gap=4, **base):
        super().__init__(**base)
        self.marker = marker
        self.content = content
        self.gap = float(gap)

    def _children(self):
        return [self.marker, self.content]

    def _intrinsic(self, max_w, max_h, scale):
        marker_w, marker_h = self.marker._intrinsic(max_w, max_h, scale)
        available = None if max_w is None else max(0, max_w - marker_w - self.gap)
        content_w, content_h = self.content._intrinsic(available, max_h, scale)
        width = marker_w + self.gap + content_w
        height = max(marker_h, content_h)
        return (
            self._width if self._width is not None else width,
            self._height if self._height is not None else height,
        )

    def _place(self, x, y, w, h, scale):
        self._rect = (x, y, w, h)
        marker_w, marker_h = self.marker._intrinsic(w, h, scale)
        content_x = x + marker_w + self.gap
        content_w = max(0, w - marker_w - self.gap)
        _, content_h = self.content._intrinsic(content_w, h, scale)
        content_h = min(h, content_h) if h is not None else content_h
        self.marker._place(x, y, marker_w, min(h, marker_h), scale)
        self.content._place(content_x, y, content_w, content_h, scale)

    def _draw(self, r, x, y):
        pass


_HEADING_SIZES = {1: 28, 2: 24, 3: 20, 4: 18, 5: 16, 6: 14}
_CLOSE_TYPES = {
    "paragraph_open": "paragraph_close",
    "heading_open": "heading_close",
    "blockquote_open": "blockquote_close",
    "bullet_list_open": "bullet_list_close",
    "ordered_list_open": "ordered_list_close",
    "list_item_open": "list_item_close",
    "table_open": "table_close",
}


def _token_attr(token, name: str, default=None):
    attrs = getattr(token, "attrs", None) or {}
    if isinstance(attrs, dict):
        return attrs.get(name, default)
    for key, value in attrs:
        if key == name:
            return value
    return default


class Markdown(Column):
    """Render Markdown using Saturn's regular text and layout controls.

    The constructor follows Flet's public ``Markdown`` signature closely.
    Unsupported presentation options are retained as attributes so existing
    application code can be migrated without special cases.
    """

    def __init__(
        self,
        value: str = "",
        selectable: bool = False,
        extension_set: MarkdownExtensionSet = MarkdownExtensionSet.NONE,
        code_theme: MarkdownCodeTheme | MarkdownCustomCodeTheme | None = None,
        auto_follow_links: bool = False,
        shrink_wrap: bool = True,
        fit_content: bool = True,
        soft_line_break: bool = False,
        auto_follow_links_target=None,
        image_error_content=None,
        code_style_sheet: MarkdownStyleSheet | None = None,
        md_style_sheet: MarkdownStyleSheet | None = None,
        latex_scale_factor: float | None = None,
        latex_style: TextStyle | None = None,
        on_tap_text=None,
        on_selection_change=None,
        on_tap_link=None,
        **base: Unpack[ControlOptions],
    ):
        self.selectable = bool(selectable)
        self.extension_set = extension_set
        self.code_theme = code_theme
        self.auto_follow_links = bool(auto_follow_links)
        self.shrink_wrap = bool(shrink_wrap)
        self.fit_content = bool(fit_content)
        self.soft_line_break = bool(soft_line_break)
        self.auto_follow_links_target = auto_follow_links_target
        self.image_error_content = image_error_content
        self.code_style_sheet = code_style_sheet
        self.md_style_sheet = md_style_sheet or MarkdownStyleSheet()
        self.latex_scale_factor = latex_scale_factor
        self.latex_style = latex_style
        self.on_tap_text = on_tap_text
        self.on_selection_change = on_selection_change
        self.on_tap_link = on_tap_link
        self._value = "" if value is None else str(value)
        self._parser = self._make_parser(extension_set)
        spacing = self._sheet_value("block_spacing", 8.0)
        # A Markdown document should fill the cross axis when it is given a
        # bounded width; otherwise wrapped rows measure against their content.
        super().__init__(
            controls=[],
            alignment=MainAxisAlignment.START,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
            spacing=spacing,
            tight=bool(fit_content),
            **base,
        )
        self._rebuild()

    @staticmethod
    def _make_parser(extension_set):
        raw = getattr(extension_set, "value", extension_set)
        parser = MarkdownIt("commonmark")
        # CommonMark has fenced code blocks.  Saturn also keeps the familiar
        # strikethrough syntax available in the default preset; the GitHub
        # presets add tables on top.
        parser.enable("strikethrough")
        if raw in (MarkdownExtensionSet.GITHUB_WEB.value,
                   MarkdownExtensionSet.GITHUB_FLAVORED.value):
            parser.enable("table")
        return parser

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value):
        new_value = "" if value is None else str(value)
        if new_value == getattr(self, "_value", None):
            return
        self._value = new_value
        if hasattr(self, "controls"):
            self._rebuild()
            self.update()

    def _sheet_value(self, name: str, default):
        if isinstance(self.md_style_sheet, dict):
            value = self.md_style_sheet.get(name)
        else:
            value = getattr(self.md_style_sheet, name, None)
        return default if value is None else value

    def _text_alignment(self, kind: str):
        return (self._sheet_value(f"{kind}_alignment", None)
                or self._sheet_value("text_alignment", None)
                or MainAxisAlignment.START)

    def _rebuild(self):
        tokens = self._parser.parse(self._value)
        self.controls = self._parse_blocks(tokens)

    def _matching(self, tokens, start: int, end: int):
        opening = tokens[start].type
        closing = _CLOSE_TYPES.get(opening)
        if closing is None:
            return end
        depth = 0
        for index in range(start, end):
            token_type = tokens[index].type
            if token_type == opening:
                depth += 1
            elif token_type == closing:
                depth -= 1
                if depth == 0:
                    return index
        return end

    def _parse_blocks(self, tokens, start: int = 0, end: int | None = None,
                      style_context=None):
        end = len(tokens) if end is None else end
        result = []
        index = start
        while index < end:
            token = tokens[index]
            token_type = token.type
            if token_type.endswith("_close"):
                index += 1
                continue
            if token_type in ("paragraph_open", "heading_open"):
                close = self._matching(tokens, index, end)
                inline = tokens[index + 1] if index + 1 < close else None
                level = int(token.tag[1:]) if token_type == "heading_open" else 0
                kind = token.tag if token_type == "heading_open" else "p"
                control = self._inline_block(
                    inline, kind, level,
                    style_override=style_context if kind == "p" else None)
                result.append(self._with_padding(control, kind))
                index = close + 1
                continue
            if token_type in ("bullet_list_open", "ordered_list_open"):
                close = self._matching(tokens, index, end)
                result.append(self._parse_list(
                    tokens, index + 1, close,
                    ordered=token_type == "ordered_list_open",
                    start_value=_token_attr(token, "start", 1),
                ))
                index = close + 1
                continue
            if token_type == "blockquote_open":
                close = self._matching(tokens, index, end)
                children = self._parse_blocks(
                    tokens, index + 1, close,
                    style_context=self._sheet_value("blockquote_text_style", None),
                )
                body = Column(
                    controls=children,
                    spacing=max(0, self._sheet_value("block_spacing", 8.0) / 2),
                    tight=True,
                    horizontal_alignment=CrossAxisAlignment.STRETCH,
                )
                padding = self._sheet_value(
                    "blockquote_padding", Padding.only(left=12, top=2, right=4, bottom=2)
                )
                result.append(Container(
                    body,
                    padding=padding,
                    border=Border.only(left=BorderSide(3, colors.Colors.OUTLINE_VARIANT)),
                ))
                index = close + 1
                continue
            if token_type in ("fence", "code_block"):
                result.append(self._code_block(token.content))
                index += 1
                continue
            if token_type == "hr":
                result.append(Divider(
                    height=12,
                    thickness=1,
                    color=colors.Colors.OUTLINE_VARIANT,
                ))
                index += 1
                continue
            if token_type == "table_open":
                close = self._matching(tokens, index, end)
                table = self._table(tokens, index + 1, close)
                if table is not None:
                    result.append(table)
                index = close + 1
                continue
            if token_type in ("html_block", "inline"):
                # Raw HTML is kept readable instead of being interpreted as
                # executable UI markup.  An inline token outside a paragraph
                # is uncommon but can occur in hand-built token streams.
                result.append(self._inline_block(token, "p", 0))
                index += 1
                continue
            index += 1
        return result

    def _with_padding(self, control, kind: str):
        padding = self._sheet_value(f"{kind}_padding", None)
        return Container(control, padding=padding) if padding is not None else control

    def _parse_list(self, tokens, start, end, *, ordered: bool, start_value=1):
        try:
            number = int(start_value)
        except (TypeError, ValueError):
            number = 1
        rows = []
        index = start
        while index < end:
            if tokens[index].type != "list_item_open":
                index += 1
                continue
            close = self._matching(tokens, index, end)
            children = self._parse_blocks(tokens, index + 1, close)
            body = Column(
                controls=children or [Text("", size=14)],
                spacing=max(0, self._sheet_value("block_spacing", 8.0) / 2),
                tight=True,
                expand=True,
                horizontal_alignment=CrossAxisAlignment.STRETCH,
            )
            marker = f"{number}." if ordered else "•"
            bullet_style = self._sheet_value("list_bullet_text_style", None)
            marker_kwargs = self._style_kwargs(
                bullet_style, default_size=14, strong=False, emphasis=False,
                deleted=False, code=False,
            )
            marker_control = Text(marker, selectable=False, **marker_kwargs)
            rows.append(_MarkdownListItem(marker_control, body, gap=4))
            if ordered:
                number += 1
            index = close + 1
        list_column = Column(
            controls=rows,
            spacing=max(0, self._sheet_value("block_spacing", 8.0) / 2),
            tight=True,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
        )
        indent = self._sheet_value("list_indent", 20.0)
        return Container(list_column, padding=Padding.only(left=indent))

    def _code_block(self, content: str):
        style_sheet = self.code_style_sheet or self.md_style_sheet
        style = getattr(style_sheet, "code_text_style", None)
        kwargs = self._style_kwargs(
            style, default_size=13, strong=False, emphasis=False,
            deleted=False, code=True,
        )
        text = Text(content.rstrip("\n"), selectable=self.selectable,
                    no_wrap=True, **kwargs)
        padding = self._sheet_value("codeblock_padding", Padding.all(8))
        return Container(
            text,
            padding=padding,
            bgcolor=colors.Colors.SURFACE_CONTAINER_LOW,
            border_radius=4,
        )

    def _table(self, tokens, start, end):
        """Render the common table token shape as rows of wrapped cells."""
        rows = []
        row_cells = []
        cell_kind = "body"
        index = start
        while index < end:
            token = tokens[index]
            if token.type in ("thead_open", "tbody_open"):
                cell_kind = "head" if token.type == "thead_open" else "body"
            elif token.type == "tr_close":
                if row_cells:
                    rows.append(Row(
                        *row_cells,
                        spacing=4,
                        vertical_alignment=CrossAxisAlignment.START,
                        horizontal_alignment=CrossAxisAlignment.START,
                    ))
                    row_cells = []
            elif token.type in ("th_open", "td_open"):
                inline = tokens[index + 1] if index + 1 < end else None
                style = self._sheet_value(
                    "table_head_text_style" if cell_kind == "head" else "table_body_text_style",
                    None,
                )
                cell = self._inline_block(inline, "p", 0, style_override=style)
                cell_padding = self._sheet_value("table_cells_padding", Padding.all(4))
                row_cells.append(Container(cell, padding=cell_padding))
                index += 2
            index += 1
        if not rows:
            return None
        return Container(
            Column(controls=rows, spacing=1, tight=True,
                   horizontal_alignment=CrossAxisAlignment.STRETCH),
            padding=self._sheet_value("table_padding", Padding.all(2)),
            border=Border.all(1, colors.Colors.OUTLINE_VARIANT),
        )

    def _inline_parts(self, token):
        if token is None:
            return [_InlinePart("")]
        children = getattr(token, "children", None) or []
        parts = []
        strong = emphasis = deleted = 0
        code = False
        href = None
        for child in children:
            kind = child.type
            if kind == "strong_open":
                strong += 1
            elif kind == "strong_close":
                strong = max(0, strong - 1)
            elif kind in ("em_open", "em_close"):
                emphasis += 1 if kind.endswith("open") else -1
                emphasis = max(0, emphasis)
            elif kind in ("s_open", "del_open"):
                deleted += 1
            elif kind in ("s_close", "del_close"):
                deleted = max(0, deleted - 1)
            elif kind == "link_open":
                href = _token_attr(child, "href")
            elif kind == "link_close":
                href = None
            elif kind == "code_inline":
                parts.append(_InlinePart(
                    child.content, bool(strong), bool(emphasis), bool(deleted),
                    True, href=href,
                ))
            elif kind in ("softbreak", "hardbreak"):
                parts.append(_InlinePart(break_kind="soft" if kind == "softbreak" else "hard"))
            elif kind in ("text", "html_inline"):
                content = child.content
                if content:
                    parts.append(_InlinePart(
                        content, bool(strong), bool(emphasis), bool(deleted),
                        code, href=href,
                    ))
            elif kind == "image":
                parts.append(_InlinePart(
                    child.content or _token_attr(child, "alt", ""),
                    bool(strong), bool(emphasis), bool(deleted), code, href=href,
                    image_src=_token_attr(child, "src"),
                ))
        if not parts:
            content = getattr(token, "content", "")
            return [_InlinePart(content)]
        return parts

    def _style_kwargs(self, style, *, default_size, strong, emphasis,
                      deleted, code):
        if style is None:
            size = default_size
            weight = FontWeight.BOLD if strong else None
            color = colors.Colors.ON_SURFACE_VARIANT if deleted else None
        else:
            size = None if getattr(style, "size", None) is not None else default_size
            weight = None if getattr(style, "weight", None) is not None else (
                FontWeight.BOLD if strong else None)
            color = None if getattr(style, "color", None) is not None else (
                colors.Colors.ON_SURFACE_VARIANT if deleted else None)
        return {
            "size": size,
            "weight": weight,
            "italic": bool(emphasis),
            "color": color,
            "style": style,
            "font_family": "monospace" if code and style is None else None,
        }

    def _inline_block(self, token, kind: str, level: int,
                      style_override=None):
        parts = self._inline_parts(token)
        rows = [[]]
        for part in parts:
            if part.image_src:
                rows[-1].append((part.text, part, style_override))
                continue
            if part.break_kind is not None:
                if part.break_kind == "hard" or self.soft_line_break:
                    rows.append([])
                else:
                    self._append_inline_text(rows[-1], " ", part, kind,
                                              style_override)
                continue
            text = part.text.replace("\r", "")
            # Markdown-it normally emits softbreak tokens, but splitting here
            # also handles inline tokens supplied by extensions.
            for segment in re.split(r"(\n)", text):
                if segment == "\n":
                    if self.soft_line_break:
                        rows.append([])
                    else:
                        self._append_inline_text(rows[-1], " ", part, kind,
                                                  style_override)
                elif segment:
                    self._append_inline_text(rows[-1], segment, part, kind,
                                              style_override)
        if not rows:
            rows = [[]]
        controls = [self._inline_row(row, kind, level, style_override)
                    for row in rows]
        if len(controls) == 1:
            return controls[0]
        return Column(controls=controls, spacing=0, tight=True,
                      horizontal_alignment=CrossAxisAlignment.STRETCH)

    def _append_inline_text(self, row, text, part, kind, style_override):
        # Keep whitespace as a separate item so Row.wrap can break at spaces;
        # discard leading whitespace after an explicit line break.
        chunks = re.split(r"(\s+)", text)
        for chunk in chunks:
            if not chunk:
                continue
            if chunk.isspace():
                chunk = " "
                if not row:
                    continue
                row.append((chunk, part, style_override))
                continue
            # A CJK run has no spaces at which Row.wrap can break.  Split
            # those glyphs into natural break units while leaving Latin and
            # code runs intact for efficient shaping.
            if re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", chunk):
                for glyph in chunk:
                    row.append((glyph, part, style_override))
            else:
                row.append((chunk, part, style_override))

    def _inline_row(self, row, kind, level, style_override):
        controls = []
        for text, part, override in row:
            if part.image_src:
                error_content = self.image_error_content
                if error_content is None:
                    error_content = Text(part.text or "[image]", size=14)
                controls.append(Image(
                    part.image_src,
                    error_content=error_content,
                    semantics_label=part.text or None,
                ))
                continue
            style = override
            if style is None:
                if part.href is not None:
                    style = self._sheet_value("a_text_style", None)
                elif part.code:
                    style = getattr(self.code_style_sheet or self.md_style_sheet,
                                    "code_text_style", None)
                elif part.strong:
                    style = self._sheet_value("strong_text_style", None)
                elif part.emphasis:
                    style = self._sheet_value("em_text_style", None)
                elif part.deleted:
                    style = self._sheet_value("del_text_style", None)
                elif kind == "blockquote":
                    style = self._sheet_value("blockquote_text_style", None)
                elif kind == "p":
                    style = self._sheet_value("p_text_style", None)
                elif kind.startswith("h"):
                    style = self._sheet_value(f"{kind}_text_style", None)
            heading_size = _HEADING_SIZES.get(level, 14)
            kwargs = self._style_kwargs(
                style,
                default_size=heading_size if level else (13 if part.code else 14),
                strong=part.strong or bool(level),
                emphasis=part.emphasis,
                deleted=part.deleted,
                code=part.code,
            )
            if part.href is not None:
                if style is None or getattr(style, "color", None) is None:
                    kwargs["color"] = colors.Colors.PRIMARY
                kwargs["on_tap"] = lambda event=None, url=part.href: self._tap_link(url)
            elif self.on_tap_text is not None:
                kwargs["on_tap"] = lambda event=None: self._tap_text()
            if self.on_selection_change is not None:
                kwargs["on_selection_change"] = self._selection_changed
            controls.append(Text(
                text,
                selectable=self.selectable,
                no_wrap=True,
                **kwargs,
            ))
        if not controls:
            controls = [Text("", size=_HEADING_SIZES.get(level, 14),
                             selectable=self.selectable)]
        return Row(
            *controls,
            wrap=True,
            spacing=0,
            run_spacing=0,
            alignment=self._text_alignment(kind),
            horizontal_alignment=CrossAxisAlignment.START,
            vertical_alignment=CrossAxisAlignment.CENTER,
        )

    def _tap_text(self):
        dispatch_event(self, "tap_text", ControlEvent("tap_text", self))

    def _tap_link(self, url: str):
        if self.auto_follow_links:
            if self.page is not None:
                self.page._app.call(webbrowser.open, str(url))
            else:
                webbrowser.open(str(url))
        dispatch_event(self, "tap_link", ControlEvent("tap_link", self, data=url))

    def _selection_changed(self, event):
        if self.on_selection_change is None:
            return
        dispatch_event(self, "selection_change", TextSelectionChangeEvent(
            "selection_change", self,
            selection=getattr(event, "selection", None),
            text=getattr(event, "text", ""),
        ))


__all__ = [
    "Markdown",
    "MarkdownCodeTheme",
    "MarkdownCustomCodeTheme",
    "MarkdownExtensionSet",
    "MarkdownStyleSheet",
]
