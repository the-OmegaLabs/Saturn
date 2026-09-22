"""Font cache + text measurement/wrapping + per-glyph fallback mixing.

All public sizes/widths are logical px; the renderer's scale factor is applied
internally so glyphs stay crisp under the 2x supersampled software backend.

Weights: pygame's font stack exposes no variable-font axes, so any font file
(bundled or user-registered) that carries a `wght` axis is instantiated at
the requested weight ON DEMAND with fonttools and cached on disk — real
W_100..W_900 for every font. Non-variable files fall back to synthetic bold.

First build of a weight runs in a BACKGROUND thread: text shows the Regular
source immediately (the notice prints once per run), and the real weight
swaps in on the next frame after the instance lands (placeholder fonts
evicted + dirty flag via the `on_weight_ready` hook, wired to App.mark_dirty
in App.start).

Glyph fallback: a line is segmented into runs — each run renders with the
first font in the chain that actually covers its characters — and runs are
baseline-aligned into one surface. Coverage probing uses pygame.freetype
(pygame.font has no per-glyph metrics).
"""
from __future__ import annotations

import io
import os
import re
import threading
import warnings
from collections import OrderedDict
from pathlib import Path

import pygame
import pygame.freetype as _freetype

# bundled UI fonts (SIL OFL 1.1 — see saturn/assets/OFL.txt)
# DEFAULT = Inter (variable; real weights via runtime instancing). CJK
# fallback = Noto Sans SC (variable, same mechanism). Italic = real Inter Italic.
INTER = Path(__file__).parent / "assets" / "Inter-VariableFont_opsz,wght.ttf"
INTER_ITALIC = Path(__file__).parent / "assets" / "Inter-Italic-VariableFont_opsz,wght.ttf"
NOTO = Path(__file__).parent / "assets" / "NotoSansSC-VariableFont_wght.ttf"

# CJK-capable system fonts (extra fallback chain; windows/mac/linux picklist)
CJK_FAMILY = "microsoftyahei,msyh,pingfangsc,hiraginosansgb,notosanscjk,wqymicrohei,simhei"
_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")

# pre-instanced hot-path weights shipped with the framework: zero instancing
# on a cold start for 400/700 text (Inter@400 needs none — its fvar default
# IS 400; Noto's default master is 100/Thin and MUST be instanced or static)
_STATIC_WEIGHTS: dict[str, dict[int, str]] = {
    str(INTER): {700: str(INTER.parent / "Inter-Bold.ttf")},
    str(NOTO): {400: str(NOTO.parent / "NotoSansSC-Regular.ttf"),
                700: str(NOTO.parent / "NotoSansSC-Bold.ttf")},
}

# instancing a big CJK variable font takes seconds; for fonts above this size
# snap un-shipped weights to the nearest shipped static instead
_SNAP_TO_STATIC_LIMIT = 5 * 1024 * 1024

_fvar_cache: dict[str, float | None] = {}  # path -> default wght (None: static)

# set by Page.theme (ft.Theme(font_family=...)); None = bundled Inter
default_family: str | None = None
# aliases registered via page.fonts = {"name": path} (flet API)
registered_fonts: dict[str, str] = {}

_font_cache: dict = {}
_line_surface_cache: OrderedDict = OrderedDict()
_line_surface_lock = threading.RLock()
_icon_cache: dict = {}
_probe_cache: dict[tuple, _freetype.Font] = {}
_cover_cache: dict[tuple, bool] = {}
ICON_FONT_PATH = Path(__file__).parent / "assets" / "MaterialSymbolsOutlined.ttf"

# Regular-first async instancing (see module docstring)
on_weight_ready = None                          # set by App.start(): mark_dirty
_pending_inst: set[tuple[str, int]] = set()     # (path, wnum) being instanced
_inst_failed: set[tuple[str, int]] = set()      # instancing impossible
_mem_instances: dict[tuple[str, int], io.BytesIO] = {}  # disk write failed
_optimizing_notice = False                      # the notice prints only once


def register_fonts(fonts: dict[str, str]):
    registered_fonts.update(fonts)
    _cover_cache.clear()
    with _line_surface_lock:
        _line_surface_cache.clear()


def weight_num(weight) -> int:
    """FontWeight enum / 'bold' / int -> numeric weight (100..900)."""
    if weight is None:
        return 400
    if isinstance(weight, int):
        return min(900, max(100, weight))
    v = getattr(weight, "value", weight)
    v = str(v)
    if v.startswith("w") and v[1:].isdigit():
        return min(900, max(100, int(v[1:])))
    return {"normal": 400, "bold": 700}.get(v, 400)


def family_for(text: str, family: str | None = None) -> str | None:
    """Resolve the PRIMARY family: explicit family wins, then the theme
    default (page.theme); None = bundled Inter. Glyph-level fallback to Noto
    and the CJK chain is handled by segmentation in render_line/line_width."""
    if family:
        return family
    return default_family


# -- variable-font instancing --------------------------------------------------
def _instance_weight(path: str, wght: int) -> bytes | None:
    """TTF bytes with every axis pinned to its default except wght.
    None when the file is not variable (or instancing fails)."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer

        font = TTFont(path, lazy=True)
        if "fvar" not in font:
            return None
        axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
        axes["wght"] = wght
        instancer.instantiateVariableFont(font, axes, inplace=True)
        buf = io.BytesIO()
        font.save(buf)
        return buf.getvalue()
    except Exception:
        return None


def _fvar_default_wght(path: str) -> float | None:
    """Default wght of a variable font; None when static (cached).
    Raw sfnt/fvar binary parse — deliberately avoids importing fontTools on
    the cold start path (fontTools only loads for actual instancing)."""
    key = f"{path}:{int(os.path.getmtime(path)) if os.path.exists(path) else 0}"
    if key in _fvar_cache:
        return _fvar_cache[key]
    value: float | None = None
    try:
        import struct

        with open(path, "rb") as fh:
            header = fh.read(12)
            if len(header) >= 12 and header[3:4] in (b"\x00", b"O", b"t"):  # sfnt
                num_tables = int.from_bytes(header[4:6], "big")
                for _ in range(num_tables):
                    rec = fh.read(16)
                    if len(rec) < 16:
                        break
                    if rec[:4] == b"fvar":
                        off = int.from_bytes(rec[8:12], "big")
                        fh.seek(off)
                        fvar_hdr = fh.read(16)
                        axes_off = int.from_bytes(fvar_hdr[4:6], "big")
                        axis_count = int.from_bytes(fvar_hdr[12:14], "big")
                        fh.seek(off + axes_off)
                        for _ in range(axis_count):
                            rec = fh.read(20)
                            if len(rec) < 20:
                                break
                            if rec[:4] == b"wght":
                                value = int.from_bytes(rec[8:12], "big") / 65536.0
                                break
                        break
    except Exception:
        value = None
    _fvar_cache[key] = value
    return value


def _weighted_source(path: str, wnum: int) -> tuple[object, bool]:
    """(source-to-load, real-weight-achieved). `source` is a path or a
    BytesIO of instanced TTF bytes.
    Order: shipped static -> variable loaded directly when the requested
    weight equals its fvar default -> runtime instancing (disk-cached under
    ~/.cache/saturn/font-cache, first build in the background while Regular
    shows) -> the original file with synthetic bold."""
    static = _STATIC_WEIGHTS.get(path, {}).get(wnum)
    if static and os.path.exists(static):
        return static, True
    table = _STATIC_WEIGHTS.get(path, {})
    try:
        big_font = os.path.getsize(path) > _SNAP_TO_STATIC_LIMIT
    except OSError:
        return path, False
    if big_font and table:
        # instancing a multi-MB CJK font costs seconds; snap to the nearest
        # shipped static instead (ponytail: exact weights via instancing if
        # someone actually needs them)
        near = min(table, key=lambda w: abs(w - wnum))
        if os.path.exists(table[near]):
            return table[near], True
    default_wght = _fvar_default_wght(path)
    if default_wght is None:
        return path, False                      # static font: synthetic bold
    if int(default_wght) == wnum:
        return path, True                       # var file at its default weight
    try:
        mtime = int(os.path.getmtime(path))
    except OSError:
        return path, False
    key = f"{Path(path).stem}.{wnum}.{mtime}.{os.path.getsize(path)}"
    cache = Path.home() / ".cache" / "saturn" / "font-cache"
    inst = cache / f"{key}.ttf"
    slot = (path, wnum)
    mem = _mem_instances.get(slot)
    if mem is not None:
        return mem, True                        # usable this run, uncached
    if slot in _inst_failed:
        return path, False                      # instancing broke: synthetic bold
    if not inst.exists():
        if slot not in _pending_inst:
            # first miss: show Regular now, build the real weight in the
            # background and swap when it lands
            global _optimizing_notice
            if not _optimizing_notice:
                print("Saturn is optimizing font for better display.")
                _optimizing_notice = True
            _pending_inst.add(slot)
            threading.Thread(target=_instance_bg, args=(path, wnum, inst),
                             daemon=True, name=f"saturn-font-{wnum}").start()
        return _regular_source(path), True      # Regular until ready
    return str(inst), True


def _regular_source(path: str) -> object:
    """Placeholder SOURCE shown while a weight is still instancing: the
    shipped Regular static when bundled, else the file itself (a variable
    file loads at its default instance). Paired with is_var=True so no
    synthetic bold gets layered on top — plain Regular, as requested."""
    static = _STATIC_WEIGHTS.get(path, {}).get(400)
    if static and os.path.exists(static):
        return static
    return path


def _instance_bg(path: str, wnum: int, dest: Path):
    """Background instancing worker: build the weight, persist it, then
    evict every placeholder font built for this (path, weight) and raise
    the dirty flag so the next frame renders with the real weight."""
    data = _instance_weight(path, wnum)
    if data is None:
        _inst_failed.add((path, wnum))
    else:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        except OSError:
            _mem_instances[(path, wnum)] = io.BytesIO(data)
    # all fallback state is final before discard, so a render racing with
    # this thread can never re-spawn the build
    _pending_inst.discard((path, wnum))
    # placeholder fonts are cached under (kind, ident, wnum, italic, px)
    for k in list(_font_cache):
        if k[0] == "file" and k[1] == path and k[2] == wnum:
            _font_cache.pop(k, None)
    with _line_surface_lock:
        _line_surface_cache.clear()
    if on_weight_ready is not None:
        on_weight_ready()


# -- chain (per-glyph fallback) --------------------------------------------------
def _primary_link(family: str | None, wnum: int, italic: bool) -> tuple:
    resolved = family_for(family)
    if resolved:
        reg = registered_fonts.get(resolved)
        if reg is not None:
            if os.path.exists(reg):
                return ("file", reg, wnum, italic)
            return _default_link(wnum, italic)
        return ("sys", resolved, wnum, italic)
    return _default_link(wnum, italic)


def _default_link(wnum: int, italic: bool) -> tuple:
    if italic:
        return ("file", str(INTER_ITALIC), wnum, True)
    return ("file", str(INTER), wnum, False)


def _chain(family: str | None, wnum: int, italic: bool) -> list[tuple]:
    """Primary link first, then fallbacks: the other bundled fonts (Inter /
    Inter-Italic / Noto), then the CJK system chain. Deduped by priority."""
    links = [_primary_link(family, wnum, italic)]
    for path in (str(NOTO), str(INTER)):
        links.append(("file", path, wnum, False))
    links += [("sys", n.strip(), wnum, False)
              for n in CJK_FAMILY.split(",") if n.strip()]
    out, seen = [], set()
    for link in links:
        key = (link[0], link[1], link[3])
        if key not in seen:
            seen.add(key)
            out.append(link)
    return out


def _probe(link: tuple) -> _freetype.Font:
    key = (link[0], link[1])
    f = _probe_cache.get(key)
    if f is None:
        if not _freetype.get_init():
            _freetype.init()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f = _freetype.Font(link[1], 16) if link[0] == "file" \
                else _freetype.SysFont(link[1], 16)
        _probe_cache[key] = f
    return f


def _covers(link: tuple, ch: str) -> bool:
    key = (link[0], link[1], ch)
    v = _cover_cache.get(key)
    if v is None:
        try:
            m = _probe(link).get_metrics(ch)
            v = m is not None and m[0] is not None
        except Exception:
            v = False
        _cover_cache[key] = v
    return v


def _render_font(link: tuple, px: int) -> pygame.font.Font:
    kind, ident, wnum, italic = link
    if not pygame.font.get_init():
        pygame.font.init()
    key = (kind, ident, wnum, italic, px)
    f = _font_cache.get(key)
    if f is None:
        if kind == "file":
            path, is_var = _weighted_source(ident, wnum)
            f = pygame.font.Font(path, px)
            # real weight already instanced; synthetic bold only for
            # non-variable files that cannot express the requested weight
            f.set_bold((not is_var) and wnum >= 550)
            f.set_italic(italic and not is_var or (is_var and italic
                                                   and ident == str(INTER_ITALIC)))
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                f = pygame.font.SysFont(ident, px, bold=wnum >= 550,
                                        italic=italic)
        _font_cache[key] = f
    return f


def get_font(size: float, scale: float = 1.0, bold: bool = False,
             italic: bool = False, family: str | None = None,
             text: str | None = None, weight: int | None = None) -> pygame.font.Font:
    """The primary font for the given style (chain head)."""
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)
    return _render_font(_primary_link(family, wnum, italic),
                        max(1, round(size * scale)))


def get_icon_font(px_size: int) -> pygame.font.Font:
    """Material Symbols font (default instance: outlined, wght 400)."""
    if not pygame.font.get_init():
        pygame.font.init()
    f = _icon_cache.get(px_size)
    if f is None:
        f = pygame.font.Font(str(ICON_FONT_PATH), px_size)
        _icon_cache[px_size] = f
    return f


# -- segmentation + rendering -----------------------------------------------------
def _segment(text: str, px: int, wnum: int, italic: bool,
             family: str | None) -> list[tuple[pygame.font.Font, str]]:
    """Split text into (font, substring) runs by glyph coverage."""
    if not text:
        return []
    links = _chain(family, wnum, italic)
    fonts = {id(l): _render_font(l, px) for l in links}
    runs: list[tuple[pygame.font.Font, str]] = []
    cur_font, cur = None, ""
    for ch in text:
        link = next((l for l in links if _covers(l, ch)), links[0])
        f = fonts[id(link)]
        if cur_font is None or f is cur_font:
            cur_font, cur = f, cur + ch
        else:
            runs.append((cur_font, cur))
            cur_font, cur = f, ch
    if cur:
        runs.append((cur_font, cur))
    return runs


def render_line(text: str, size: float, *, scale: float = 1.0,
                weight: int | None = None, bold: bool = False,
                italic: bool = False, family: str | None = None,
                color=(0, 0, 0, 255)) -> pygame.Surface:
    """Render one line with per-glyph fallback, concatenated into a surface.
    Runs are aligned by BASELINE (ascent difference), not top edge."""
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)
    px = max(1, round(size * scale))
    runs = _segment(text, px, wnum, italic, family)
    if not runs:
        return pygame.Surface((0, 0), pygame.SRCALPHA)
    surfs = [f.render(part, True, color) for f, part in runs]
    if len(surfs) == 1:
        return surfs[0]
    ascents = [f.get_ascent() for f, _ in runs]
    base = max(ascents)
    ys = [base - a for a in ascents]
    w = sum(s.get_width() for s in surfs)
    h = max(y + s.get_height() for y, s in zip(ys, surfs))
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    x = 0
    for s, y in zip(surfs, ys):
        out.blit(s, (x, y))
        x += s.get_width()
    return out


def render_line_cached(text: str, size: float, *, scale: float = 1.0,
                       weight: int | None = None, bold: bool = False,
                       italic: bool = False, family: str | None = None,
                       color=(0, 0, 0, 255)) -> pygame.Surface:
    """Return an immutable line raster from a bounded animation-safe cache."""
    frozen_color = tuple(color) if isinstance(color, (tuple, list)) else color
    key = (text, float(size), float(scale), weight, bool(bold), bool(italic),
           family, default_family, frozen_color)
    with _line_surface_lock:
        surface = _line_surface_cache.get(key)
        if surface is not None:
            _line_surface_cache.move_to_end(key)
            return surface
    surface = render_line(
        text, size, scale=scale, weight=weight, bold=bold, italic=italic,
        family=family, color=color)
    with _line_surface_lock:
        _line_surface_cache[key] = surface
        _line_surface_cache.move_to_end(key)
        while len(_line_surface_cache) > 512:
            _line_surface_cache.popitem(last=False)
    return surface


def line_width(text: str, size: float, *, scale: float = 1.0,
               weight: int | None = None, bold: bool = False,
               italic: bool = False, family: str | None = None) -> float:
    """Width of a line in logical px under per-glyph fallback."""
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)
    px = max(1, round(size * scale))
    total = sum(f.size(part)[0] for f, part in _segment(text, px, wnum, italic, family))
    return total / scale


def measure(text: str, size: float, *, scale: float = 1.0, bold: bool = False,
            italic: bool = False, family: str | None = None,
            weight: int | None = None) -> tuple[float, float]:
    """Single-font size (kept for exact height metrics); use line_width for
    fallback-aware width."""
    f = get_font(size, scale, bold, italic, family, text=text, weight=weight)
    w, h = f.size(text)
    return w / scale, h / scale


def line_height(size: float, *, scale: float = 1.0, bold: bool = False,
                italic: bool = False, family: str | None = None,
                text: str | None = None, weight: int | None = None) -> float:
    # Flutter's default text line box is 10/7 of the logical font size. It
    # is deliberately independent of rasterizer metrics: a 30px Text is a
    # 43px layout box in Flet even when the rendered glyph bitmap is shorter.
    return float(max(1, round(size * 10 / 7)))


def wrap(text: str, max_width: float, size: float, *, scale: float = 1.0,
         bold: bool = False, italic: bool = False, family: str | None = None,
         max_lines: int | None = None, weight: int | None = None) -> list[str]:
    """Word-wrap into lines fitting max_width (logical px). Honors \n breaks;
    char-splits words longer than a line; adds an ellipsis when truncated."""
    if not text:
        return []
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)

    def width(s: str) -> float:
        return line_width(s, size, scale=scale, weight=wnum, italic=italic,
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
