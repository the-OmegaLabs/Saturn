"""Font cache + text measurement/wrapping + per-glyph fallback mixing.

All public sizes/widths are logical px; the renderer's scale factor is applied
internally so glyphs stay crisp under the 2x supersampled software backend.

Glyph fallback: a line is segmented into runs — each run renders with the
first font in the chain that actually covers its characters (bundled Inter
first, then the CJK system chain), and the runs are concatenated into one
surface. Coverage probing uses pygame.freetype (pygame.font exposes no
per-glyph metrics); `caveat: freetype.SysFont and SysFont may resolve
slightly differently, worst case a glyph stays tofu`.
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

import pygame
import pygame.freetype as _freetype

# bundled default UI font (SIL OFL 1.1 — see saturn/assets/OFL.txt)
INTER = Path(__file__).parent / "assets" / "Inter-VariableFont_opsz,wght.ttf"
INTER_ITALIC = Path(__file__).parent / "assets" / "Inter-Italic-VariableFont_opsz,wght.ttf"

# CJK-capable system fonts (Inter has no CJK glyphs; windows/mac/linux picklist)
CJK_FAMILY = "microsoftyahei,msyh,pingfangsc,hiraginosansgb,notosanscjk,wqymicrohei,simhei"
_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")

_font_cache: dict = {}
_icon_cache: dict = {}
ICON_FONT_PATH = Path(__file__).parent / "assets" / "MaterialSymbolsOutlined.ttf"

# set by Page.theme (ft.Theme(font_family=...)); None = bundled Inter
default_family: str | None = None
# aliases registered via page.fonts = {"name": path} (flet API)
registered_fonts: dict[str, str] = {}

_probe_cache: dict[tuple, _freetype.Font] = {}
_cover_cache: dict[tuple, bool] = {}


def register_fonts(fonts: dict[str, str]):
    registered_fonts.update(fonts)
    _cover_cache.clear()


def family_for(text: str, family: str | None = None) -> str | None:
    """Resolve the PRIMARY family: explicit family wins, then the theme
    default (page.theme); None = bundled Inter. Glyph-level fallback to the
    CJK chain is handled by the segmentation in render_line/line_width."""
    if family:
        return family
    return default_family


def _primary_source(family: str | None, italic: bool) -> tuple:
    """(kind, identifier) for the primary font. kind: 'file' | 'sys'."""
    resolved = family_for("", family)
    if resolved:
        reg = registered_fonts.get(resolved)
        if reg is not None:
            if os.path.exists(reg):
                return ("file", reg)
            # registered but missing -> bundled Inter (italic variant if needed)
            return ("file", str(INTER_ITALIC if italic else INTER))
        return ("sys", resolved)
    return ("file", str(INTER_ITALIC if italic else INTER))


def _chain_sources(family: str | None, italic: bool) -> list[tuple]:
    """Primary font source first, then fallbacks: bundled Inter (if not
    primary), then the CJK system chain. Deduped, order = priority."""
    sources = [_primary_source(family, italic)]
    inter = ("file", str(INTER))
    if sources[0][1] not in (str(INTER), str(INTER_ITALIC)):
        sources.append(inter)
    sources += [("sys", n.strip()) for n in CJK_FAMILY.split(",") if n.strip()]
    out, seen = [], set()
    for s in sources:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _probe(source: tuple) -> _freetype.Font:
    f = _probe_cache.get(source)
    if f is None:
        if not _freetype.get_init():
            _freetype.init()
        f = _freetype.Font(source[1], 16) if source[0] == "file" \
            else _freetype.SysFont(source[1], 16)
        _probe_cache[source] = f
    return f


def _covers(source: tuple, ch: str) -> bool:
    key = (source, ch)
    v = _cover_cache.get(key)
    if v is None:
        try:
            m = _probe(source).get_metrics(ch)
            v = m is not None and m[0] is not None
        except Exception:
            v = False
        _cover_cache[key] = v
    return v


def _render_font(source: tuple, px: int, bold: bool, italic: bool) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    key = (source, px, bold, italic)
    f = _font_cache.get(key)
    if f is None:
        if source[0] == "file":
            f = pygame.font.Font(source[1], px)
            f.set_bold(bold)
            f.set_italic(italic)
        else:
            # the chain intentionally tries platform-specific names that may be
            # absent; pygame warns per miss — silence it, a later link matches
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                f = pygame.font.SysFont(source[1], px, bold=bold, italic=italic)
        _font_cache[key] = f
    return f


def get_font(size: float, scale: float = 1.0, bold: bool = False,
             italic: bool = False, family: str | None = None,
             text: str | None = None) -> pygame.font.Font:
    """The primary font for the given style (chain head)."""
    return _render_font(_primary_source(family, italic),
                        max(1, round(size * scale)), bold, italic)


def _segment(text: str, px: int, bold: bool, italic: bool,
             family: str | None) -> list[tuple[pygame.font.Font, str]]:
    """Split text into (font, substring) runs by glyph coverage."""
    if not text:
        return []
    sources = _chain_sources(family, italic)
    fonts = {s: _render_font(s, px, bold, italic) for s in sources}
    runs: list[tuple[pygame.font.Font, str]] = []
    cur_font, cur = None, ""
    for ch in text:
        src = next((s for s in sources if _covers(s, ch)), sources[0])
        f = fonts[src]
        if cur_font is None or f is cur_font:
            cur_font, cur = f, cur + ch
        else:
            runs.append((cur_font, cur))
            cur_font, cur = f, ch
    if cur:
        runs.append((cur_font, cur))
    return runs


def render_line(text: str, size: float, *, scale: float = 1.0, bold: bool = False,
                italic: bool = False, family: str | None = None,
                color=(0, 0, 0, 255)) -> pygame.Surface:
    """Render one line with per-glyph fallback, concatenated into a surface."""
    px = max(1, round(size * scale))
    runs = _segment(text, px, bold, italic, family)
    if not runs:
        return pygame.Surface((0, 0), pygame.SRCALPHA)
    surfs = [f.render(part, True, color) for f, part in runs]
    if len(surfs) == 1:
        return surfs[0]
    w = sum(s.get_width() for s in surfs)
    h = max(s.get_height() for s in surfs)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    x = 0
    for s in surfs:
        out.blit(s, (x, 0))
        x += s.get_width()
    return out


def line_width(text: str, size: float, *, scale: float = 1.0, bold: bool = False,
               italic: bool = False, family: str | None = None) -> float:
    """Width of a line in logical px under per-glyph fallback."""
    px = max(1, round(size * scale))
    total = sum(f.size(part)[0] for f, part in _segment(text, px, bold, italic, family))
    return total / scale


def get_icon_font(px_size: int) -> pygame.font.Font:
    """Material Symbols font (default instance: outlined, wght 400)."""
    if not pygame.font.get_init():
        pygame.font.init()
    f = _icon_cache.get(px_size)
    if f is None:
        f = pygame.font.Font(str(ICON_FONT_PATH), px_size)
        _icon_cache[px_size] = f
    return f


def measure(text: str, size: float, *, scale: float = 1.0, bold: bool = False,
            italic: bool = False, family: str | None = None) -> tuple[float, float]:
    """Single-font size (kept for exact height metrics); use line_width for
    fallback-aware width."""
    f = get_font(size, scale, bold, italic, family, text=text)
    w, h = f.size(text)
    return w / scale, h / scale


def line_height(size: float, *, scale: float = 1.0, bold: bool = False,
                italic: bool = False, family: str | None = None,
                text: str | None = None) -> float:
    f = get_font(size, scale, bold, italic, family, text=text)
    return f.size("Ag")[1] / scale


def wrap(text: str, max_width: float, size: float, *, scale: float = 1.0,
         bold: bool = False, italic: bool = False, family: str | None = None,
         max_lines: int | None = None) -> list[str]:
    """Word-wrap into lines fitting max_width (logical px). Honors \n breaks;
    char-splits words longer than a line; adds an ellipsis when truncated."""
    if not text:
        return []

    def width(s: str) -> float:
        return line_width(s, size, scale=scale, bold=bold, italic=italic,
                          family=family)

    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            if not cur:
                if width(word) > max_width and len(word) > 1:
                    piece = ""
                    for ch in word:
                        if piece and width(piece + ch) > max_width:
                            lines.append(piece)
                            piece = ch
                        else:
                            piece += ch
                    cur = piece
                else:
                    cur = word
                continue
            trial = cur + " " + word
            if width(trial) <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and width(last + "…") > max_width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines
