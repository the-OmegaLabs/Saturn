"""Font cache + text measurement/wrapping.

All public sizes/widths are logical px; the renderer's scale factor is applied
internally so glyphs stay crisp under the 2x supersampled software backend.
"""
from __future__ import annotations

import re
from pathlib import Path

import pygame

# flet's default is Roboto; fall through to system fonts when absent
DEFAULT_FAMILY = "roboto,segoeui,arial,helvetica"
# CJK-capable system fonts (windows/mac/linux picklist; first hit wins)
CJK_FAMILY = "microsoftyahei,msyh,pingfangsc,hiraginosansgb,notosanscjk,wqymicrohei,simhei"
_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")

_font_cache: dict = {}
_icon_cache: dict = {}
ICON_FONT_PATH = Path(__file__).parent / "assets" / "MaterialSymbolsOutlined.ttf"


def family_for(text: str, family: str | None = None) -> str:
    """Pick a font family that can actually render `text` (CJK fallback)."""
    if family:
        return family
    if text and _CJK_RE.search(text):
        return CJK_FAMILY
    return DEFAULT_FAMILY


def get_font(size: float, scale: float = 1.0, bold: bool = False,
             italic: bool = False, family: str | None = None,
             text: str | None = None) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    key = (family_for(text, family), max(1, round(size * scale)), bold, italic)
    f = _font_cache.get(key)
    if f is None:
        f = pygame.font.SysFont(key[0], key[1], bold=bold, italic=italic)
        _font_cache[key] = f
    return f


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
    """Single-line size in logical px."""
    f = get_font(size, scale, bold, italic, family, text=text)
    w, h = f.size(text)
    return w / scale, h / scale


def line_height(size: float, *, scale: float = 1.0, family: str | None = None,
                text: str | None = None) -> float:
    f = get_font(size, scale, family=family, text=text)
    return f.size("Ag")[1] / scale


def wrap(text: str, max_width: float, size: float, *, scale: float = 1.0,
         bold: bool = False, italic: bool = False, family: str | None = None,
         max_lines: int | None = None) -> list[str]:
    """Word-wrap into lines fitting max_width (logical px). Honors \n breaks;
    char-splits words longer than a line; adds an ellipsis when truncated."""
    if not text:
        return []
    f = get_font(size, scale, bold, italic, family, text=text)

    def width(s: str) -> float:
        return f.size(s)[0] / scale

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
