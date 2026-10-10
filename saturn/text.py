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
evicted + dirty flags through registered app listeners). Active Pages receive
on_font_optimize notifications when background optimization starts and ends.

Glyph fallback: a line is segmented into runs — each run renders with the
first font in the chain that actually covers its characters — and runs are
baseline-aligned into one surface. Coverage probing uses pygame.freetype
(pygame.font has no per-glyph metrics).
"""
from __future__ import annotations

import io
import hashlib
import os
import re
import tempfile
import threading
import warnings
import weakref
from urllib.parse import urlparse
from urllib.request import urlopen
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import pygame
import pygame.freetype as _freetype
from saturn_fonts_cjk import BOLD_FONT as NOTO_BOLD
from saturn_fonts_cjk import REGULAR_FONT as NOTO_REGULAR
from saturn_fonts_cjk import VARIABLE_FONT as NOTO
from saturn_icons_material import FILLED_FONT as ICON_FONT_PATH
from saturn_icons_material import OUTLINED_FONT as ICON_OUTLINED_PATH

# bundled UI fonts (SIL OFL 1.1; each distribution ships its own license)
# DEFAULT = Inter (variable; real weights via runtime instancing). CJK
# fallback = Noto Sans SC (variable, same mechanism). Italic = real Inter Italic.
INTER = Path(__file__).parent / "assets" / "Inter-VariableFont_opsz,wght.woff2"
INTER_ITALIC = Path(__file__).parent / "assets" / "Inter-Italic-VariableFont_opsz,wght.woff2"
INTER_BOLD = Path(__file__).parent / "assets" / "Inter-Bold.woff2"

# CJK-capable system fonts (extra fallback chain; windows/mac/linux picklist)
CJK_FAMILY = "microsoftyahei,msyh,pingfangsc,hiraginosansgb,notosanscjk,wqymicrohei,simhei"
_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")

# pre-instanced hot-path weights shipped with the framework: zero instancing
# on a cold start for 400/700 text (Inter@400 needs none — its fvar default
# IS 400; Noto's default master is 100/Thin and MUST be instanced or static)
_STATIC_WEIGHTS: dict[object, dict[int, object]] = {
    str(NOTO): {400: str(NOTO_REGULAR), 700: str(NOTO_BOLD)},
    str(NOTO_REGULAR): {400: str(NOTO_REGULAR), 700: str(NOTO_BOLD)},
    str(NOTO_BOLD): {400: str(NOTO_REGULAR), 700: str(NOTO_BOLD)},
}

# instancing a big CJK variable font takes seconds; for fonts above this size
# snap un-shipped weights to the nearest shipped static instead
_SNAP_TO_STATIC_LIMIT = 5 * 1024 * 1024

_fvar_cache: dict[str, float | None] = {}  # path -> default wght (None: static)

# Selected by the active Page theme; None = bundled Inter.
default_family: str | None = None
# Resolved aliases registered through page.fonts.
registered_fonts: dict[str, str] = {}
_font_sources: dict[str, str] = {}
_font_downloads: dict[str, list] = {}
_font_download_lock = threading.RLock()
font_revision = 0

_font_cache: dict = {}
_font_cache_lock = threading.RLock()  # ✅ Added thread safety
_line_surface_cache: OrderedDict = OrderedDict()
_line_surface_lock = threading.RLock()
_icon_cache: dict = {}
_icon_cache_lock = threading.RLock()  # ✅ Added thread safety
_icon_surface_cache: OrderedDict = OrderedDict()
_icon_surface_lock = threading.RLock()  # ✅ Added thread safety
_probe_cache: dict[tuple, _freetype.Font] = {}
_probe_cache_lock = threading.RLock()  # ✅ Added thread safety
_cover_cache: dict[tuple, bool] = {}
_cover_cache_lock = threading.RLock()  # ✅ Added thread safety
# Generated icon values are Material Symbols codepoints. Use the filled
# static font instance for the default Icons family.
# Regular-first async instancing (see module docstring)
on_weight_ready = None                          # optional legacy completion hook
_font_event_apps = weakref.WeakSet()
_pending_inst: set[tuple[str, int]] = set()     # (path, wnum) being instanced
_inst_failed: set[tuple[str, int]] = set()      # instancing impossible
_mem_instances: dict[tuple[str, int], io.BytesIO] = {}  # disk write failed
_optimizing_notice = False                      # the notice prints only once
_woff2_lock = threading.RLock()


def _emit_font_optimize(font, weight=None, *, status, error=None,
                        operation="instance", cached=False):
    for app in tuple(_font_event_apps):
        if not app._closed.is_set():
            app._notify_font_optimize(
                font="memory font" if isinstance(font, io.BytesIO) else str(font),
                weight=weight, status=status, error=error, operation=operation,
                cached=cached, success=None if status == "started" else status == "completed")


def invalidate_fonts():
    """Invalidate measurements, glyph coverage and rendered text together."""
    global font_revision
    font_revision += 1
    _font_cache.clear()
    _probe_cache.clear()
    _cover_cache.clear()
    _compressed_font_source.cache_clear()
    _chain_cached.cache_clear()
    _glyph_links.cache_clear()
    _line_width_cached.cache_clear()
    with _line_surface_lock:
        _line_surface_cache.clear()


def set_default_family(family):
    global default_family
    if family != default_family:
        default_family = family
        invalidate_fonts()


def _font_cache_locations():
    locations = [Path.home() / ".cache" / "saturn" / "font-cache"]
    try:
        locations.append(Path(tempfile.gettempdir()) / "saturn-font-cache")
    except OSError:
        # Some hosts have no writable temp directory. WOFF decoding can
        # still return an in-memory font when neither cache is writable.
        pass
    return locations


def _font_cache_directory():
    return _font_cache_locations()[-1] / "downloads"


def _download_font(source, destination):
    """Resolve HTTP fonts off the UI thread, then notify affected pages."""
    _emit_font_optimize(source, status="started", operation="load")
    failure = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(source, timeout=20) as response:
            data = response.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("font exceeds 32 MiB")
        # Reject a failed download (e.g. an HTML error page) before it can
        # become a persistent cache entry. Collections are valid too.
        from fontTools.ttLib import TTCollection, TTFont
        loaded = (TTCollection(io.BytesIO(data)) if data[:4] == b"ttcf"
                  else TTFont(io.BytesIO(data)))
        try:
            if data[:4] in (b"wOF2", b"wOFF"):
                # HTTP endpoints need not have a filename extension.
                # Normalize compressed fonts before storing the cache.
                loaded.flavor = None
                decoded = io.BytesIO()
                loaded.save(decoded)
                data = decoded.getvalue()
        finally:
            loaded.close()
        with tempfile.NamedTemporaryFile(dir=destination.parent,
                                         delete=False) as temporary:
            temporary.write(data)
            staged = Path(temporary.name)
        try:
            os.replace(staged, destination)
        finally:
            staged.unlink(missing_ok=True)
        with _font_download_lock:
            aliases = [alias for alias, value in _font_sources.items()
                       if value == source]
            for alias in aliases:
                registered_fonts[alias] = str(destination)
            if aliases:
                invalidate_fonts()
    except Exception as error:
        failure = str(error)
        warnings.warn(f"Cannot load font {source}: {error}", RuntimeWarning)
    finally:
        with _font_download_lock:
            callbacks = _font_downloads.pop(source, [])
        for callback in callbacks:
            if callback is not None:
                callback()
        _emit_font_optimize(source, status="failed" if failure else "completed",
                            error=failure, operation="load", cached=failure is None)


def register_fonts(fonts: dict[str, str], on_ready=None):
    """Register local paths/assets or asynchronously cached HTTP(S) fonts."""
    sources = {str(alias): os.fspath(source) for alias, source in fonts.items()}
    with _font_download_lock:
        if sources == _font_sources:
            return
        _font_sources.clear()
        _font_sources.update(sources)
        registered_fonts.clear()
        pending = []
        for alias, source in sources.items():
            parsed = urlparse(source)
            if parsed.scheme.lower() in ("http", "https"):
                cached = _font_cache_directory() / (
                    hashlib.sha256(source.encode()).hexdigest() + ".ttf")
                if cached.is_file():
                    registered_fonts[alias] = str(cached)
                else:
                    registered_fonts[alias] = ""
                    callbacks = _font_downloads.get(source)
                    if callbacks is None:
                        _font_downloads[source] = [on_ready]
                        pending.append((source, cached))
                    elif on_ready not in callbacks:
                        callbacks.append(on_ready)
            else:
                path = Path(source).expanduser()
                if not path.is_absolute() and not path.is_file():
                    asset = Path("assets") / path
                    if asset.is_file():
                        path = asset
                registered_fonts[alias] = str(path)
        invalidate_fonts()
        for source, cached in pending:
            threading.Thread(target=_download_font, args=(source, cached),
                             daemon=True, name="saturn-font-download").start()


@lru_cache(maxsize=64)
def _decode_woff2(path: str, modified_ns: int, size: int):
    """Decode a local web font once; use a stable SFNT file across runs."""
    from fontTools.ttLib import TTFont

    digest = hashlib.sha256(f"{path}:{modified_ns}:{size}".encode()).hexdigest()[:20]
    name = f"{Path(path).stem}.{digest}.ttf"
    locations = _font_cache_locations()
    for directory in locations:
        cached = directory / name
        if cached.is_file():
            return str(cached)

    try:
        font = TTFont(path)
        try:
            font.flavor = None
            data = io.BytesIO()
            font.save(data)
            sfnt = data.getvalue()
        finally:
            font.close()
    except Exception as exc:
        raise ValueError(f"cannot decode WOFF2 font: {path}") from exc

    for directory in locations:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            cached = directory / name
            with tempfile.NamedTemporaryFile(dir=directory, suffix=".ttf",
                                             delete=False) as temporary:
                temporary.write(sfnt)
                staged = Path(temporary.name)
            try:
                os.replace(staged, cached)
            finally:
                staged.unlink(missing_ok=True)
            return str(cached)
        except OSError:
            continue
    return io.BytesIO(sfnt)


@lru_cache(maxsize=3)
def _bundled_font_source(path: str):
    # Bundled files are immutable during a process lifetime. Resolving a
    # WOFF2 path on Windows is surprisingly expensive in text measurement.
    return _resolve_font_source(path)


def _font_source(path: str):
    if path in (str(INTER), str(INTER_ITALIC), str(INTER_BOLD)):
        return _bundled_font_source(path)
    # Ordinary SFNT paths do not require Path/stat work for each run.
    if not path.lower().endswith((".woff2", ".woff")):
        return path
    stat = os.stat(path)
    return _compressed_font_source(path, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=256)
def _compressed_font_source(path: str, modified_ns: int, size: int):
    return _resolve_font_source(path)


def _resolve_font_source(path: str):
    if not path.lower().endswith((".woff2", ".woff")):
        return path
    resolved = Path(path).resolve()
    with resolved.open("rb") as stream:
        if stream.read(4) not in (b"wOF2", b"wOFF"):
            raise ValueError(f"not a web font: {path}")
    stat = resolved.stat()
    with _woff2_lock:
        source = _decode_woff2(str(resolved), stat.st_mtime_ns, stat.st_size)
        if resolved == INTER.resolve() and source not in _STATIC_WEIGHTS:
            _STATIC_WEIGHTS[source] = {700: str(INTER_BOLD)}
        elif resolved == NOTO.resolve() and source not in _STATIC_WEIGHTS:
            _STATIC_WEIGHTS[source] = {
                400: str(NOTO_REGULAR), 700: str(NOTO_BOLD)}
        elif resolved in (NOTO_REGULAR.resolve(), NOTO_BOLD.resolve()) \
                and source not in _STATIC_WEIGHTS:
            _STATIC_WEIGHTS[source] = {
                400: str(NOTO_REGULAR), 700: str(NOTO_BOLD)}
        return source


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

        source = io.BytesIO(path.getvalue()) if isinstance(path, io.BytesIO) else path
        font = TTFont(source, lazy=True)
        if "fvar" not in font:
            return None
        axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
        axes["wght"] = wght
        instancer.instantiateVariableFont(font, axes, inplace=True)
        buf = io.BytesIO()
        font.save(buf)
        font.close()
        return buf.getvalue()
    except Exception:
        return None


def _fvar_default_wght(path: str) -> float | None:
    """Default wght of a variable font; None when static (cached).
    Raw sfnt/fvar binary parse — deliberately avoids importing fontTools on
    the cold start path (fontTools only loads for actual instancing)."""
    memory = isinstance(path, io.BytesIO)
    key = f"memory:{id(path)}" if memory else \
        f"{path}:{int(os.path.getmtime(path)) if os.path.exists(path) else 0}"
    if key in _fvar_cache:
        return _fvar_cache[key]
    value: float | None = None
    try:
        import struct

        with (io.BytesIO(path.getvalue()) if memory else open(path, "rb")) as fh:
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
    if static and (isinstance(static, io.BytesIO) or os.path.exists(static)):
        return _font_source(static) if isinstance(static, str) else static, True
    table = _STATIC_WEIGHTS.get(path, {})
    memory = isinstance(path, io.BytesIO)
    try:
        source_size = len(path.getbuffer()) if memory else os.path.getsize(path)
        big_font = source_size > _SNAP_TO_STATIC_LIMIT
    except OSError:
        return path, False
    if big_font and table:
        # instancing a multi-MB CJK font costs seconds; snap to the nearest
        # shipped static instead (ponytail: exact weights via instancing if
        # someone actually needs them)
        near = min(table, key=lambda w: abs(w - wnum))
        if isinstance(table[near], io.BytesIO) or os.path.exists(table[near]):
            source = table[near]
            return _font_source(source) if isinstance(source, str) else source, True
    default_wght = _fvar_default_wght(path)
    if default_wght is None:
        return path, False                      # static font: synthetic bold
    if int(default_wght) == wnum:
        return path, True                       # var file at its default weight
    mtime = 0 if memory else int(os.path.getmtime(path))
    stem = (hashlib.sha256(path.getbuffer()).hexdigest()[:20]
            if memory else Path(path).stem)
    key = f"{stem}.{wnum}.{mtime}.{source_size}"
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
    _emit_font_optimize(path, wnum, status="started")
    failure = None
    cached = False
    try:
        data = _instance_weight(path, wnum)
    except Exception as error:
        data, failure = None, str(error)
    if data is None:
        failure = failure or "Cannot instance the requested font weight"
        _inst_failed.add((path, wnum))
    else:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            cached = True
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
    global font_revision
    font_revision += 1
    if on_weight_ready is not None:
        on_weight_ready()
    _emit_font_optimize(path, wnum, status="failed" if failure else "completed",
                        error=failure, cached=cached)


# -- chain (per-glyph fallback) --------------------------------------------------
def _primary_link(family: str | None, wnum: int, italic: bool) -> tuple:
    resolved = family_for("", family)
    if resolved:
        reg = registered_fonts.get(resolved)
        if reg is not None:
            if os.path.exists(reg):
                return ("file", _font_source(reg), wnum, italic)
            return _default_link(wnum, italic)
        if os.path.isfile(resolved) and Path(resolved).suffix.lower() in \
                (".ttf", ".otf", ".ttc", ".woff", ".woff2"):
            return ("file", _font_source(resolved), wnum, italic)
        return ("sys", resolved, wnum, italic)
    return _default_link(wnum, italic)


def _default_link(wnum: int, italic: bool) -> tuple:
    if italic:
        return ("file", _font_source(str(INTER_ITALIC)), wnum, True)
    return ("file", _font_source(str(INTER)), wnum, False)


def _chain(family: str | None, wnum: int, italic: bool) -> tuple[tuple, ...]:
    # Measuring many distinct rows used to resolve the same bundled sources
    # once for every word and glyph run. Theme/font revisions invalidate the
    # small shared chain cache without changing callers.
    return _chain_cached(family, wnum, italic, default_family, font_revision)


@lru_cache(maxsize=256)
def _chain_cached(family, wnum, italic, _default, _revision):
    """Primary link first, then fallbacks: the other bundled fonts (Inter /
    Inter-Italic / Noto), then the CJK system chain. Deduped by priority."""
    links = ([_primary_link(item, wnum, italic) for item in family if item is not None]
             if isinstance(family, tuple) else [_primary_link(family, wnum, italic)])
    links.append(_default_link(wnum, False))
    # System CJK fonts first: this is what Flet renders through Flutter's
    # platform fallback (Microsoft YaHei on Windows, PingFang on macOS), so
    # migrated apps keep the same typeface flavor. The bundled Noto is the
    # fallback for systems without a covering system font.
    links += [("sys", n.strip(), wnum, False)
              for n in CJK_FAMILY.split(",") if n.strip()]
    links.append(("file", str(NOTO_REGULAR), wnum, False))
    out, seen = [], set()
    for link in links:
        key = (link[0], link[1], link[3])
        if key not in seen:
            seen.add(key)
            out.append(link)
    return tuple(out)


def _probe(link: tuple) -> _freetype.Font:
    key = (link[0], link[1])
    f = _probe_cache.get(key)
    if f is None:
        if not _freetype.get_init():
            _freetype.init()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            source = (_font_source(link[1]) if link[0] == "file"
                      and isinstance(link[1], str) else link[1])
            if isinstance(source, io.BytesIO):
                source = io.BytesIO(source.getvalue())
            f = _freetype.Font(source, 16) if link[0] == "file" \
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
    if kind == "file" and isinstance(ident, str):
        ident = _font_source(ident)
    key = (kind, ident, wnum, italic, px)
    f = _font_cache.get(key)
    if f is None:
        if kind == "file":
            path, is_var = _weighted_source(ident, wnum)
            if isinstance(path, io.BytesIO):
                path = io.BytesIO(path.getvalue())
            f = pygame.font.Font(path, px)
            # real weight already instanced; synthetic bold only for
            # non-variable files that cannot express the requested weight
            f.set_bold((not is_var) and wnum >= 550)
            f.set_italic(italic and not is_var)
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


def get_icon_font(px_size: int, outlined: bool = False) -> pygame.font.Font:
    """Material Symbols font; the variant font follows the icon name."""
    if not pygame.font.get_init():
        pygame.font.init()
    key = (px_size, outlined)
    with _icon_cache_lock:
        f = _icon_cache.get(key)
        if f is None:
            f = pygame.font.Font(str(ICON_OUTLINED_PATH if outlined else ICON_FONT_PATH), px_size)
            _icon_cache[key] = f
        return f


def render_icon_cached(icon, px_size: int, color) -> pygame.Surface:
    """Render an immutable Material icon once and reuse it across frames.

    Icon names ending in ``_OUTLINED`` render with the outlined font; the
    filled font would draw e.g. crop_square as a solid block. The surface is
    cropped to the visible glyph: symbol fonts carry large ascent margins,
    and only a tight bitmap lets widgets center the glyph optically."""
    name = getattr(icon, "name", "") or ""
    outlined = name.endswith("_OUTLINED")
    rgba = tuple(color)
    key = (int(icon), int(px_size), rgba, outlined)
    with _icon_surface_lock:
        surface = _icon_surface_cache.get(key)
        if surface is None:
            rendered = get_icon_font(px_size, outlined).render(chr(int(icon)), True, rgba)
            bbox = rendered.get_bounding_rect()
            surface = (rendered.subsurface(bbox).copy()
                       if bbox.w > 0 and bbox.h > 0 else rendered)
            _icon_surface_cache[key] = surface
            if len(_icon_surface_cache) > 256:
                _icon_surface_cache.popitem(last=False)
        else:
            _icon_surface_cache.move_to_end(key)
        return surface


# -- segmentation + rendering -----------------------------------------------------
@lru_cache(maxsize=256)
def _glyph_links(family, wnum, italic, _default, _revision):
    """Share exact fallback choices across different strings in one style."""
    return _chain(family, wnum, italic), {}


def _segment(text: str, px: int, wnum: int, italic: bool,
             family: str | None) -> list[tuple[pygame.font.Font, str]]:
    """Split text into (font, substring) runs by glyph coverage."""
    if not text:
        return []
    links, glyphs = _glyph_links(family, wnum, italic,
                                default_family, font_revision)
    fonts = {}
    runs: list[tuple[pygame.font.Font, str]] = []
    cur_font, cur = None, ""
    for ch in text:
        link = glyphs.get(ch)
        if link is None:
            link = next((l for l in links if _covers(l, ch)), links[0])
            if len(glyphs) >= 2048:
                glyphs.clear()
            glyphs[ch] = link
        f = fonts.get(link)
        if f is None:
            f = fonts[link] = _render_font(link, px)
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
                color=(0, 0, 0, 255), letter_spacing: float = 0.0) -> pygame.Surface:
    """Render one line with per-glyph fallback, concatenated into a surface.
    Runs are aligned by BASELINE (ascent difference), not top edge.
    ``letter_spacing`` is logical px added between characters; it disables
    kerning by falling back to per-character rasters."""
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)
    px = max(1, round(size * scale))
    runs = _segment(text, px, wnum, italic, family)
    if not runs:
        return pygame.Surface((0, 0), pygame.SRCALPHA)
    spacing_px = letter_spacing * scale
    if spacing_px:
        chars = [(f, ch) for f, part in runs for ch in part]
        surfs = [f.render(ch, True, color) for f, ch in chars]
        ascents = [f.get_ascent() for f, _ in chars]
        base = max(ascents)
        ys = [base - a for a in ascents]
        # Float advance matches line_width exactly; only blit positions round.
        x = 0.0
        height = 0
        positions = []
        for s, y in zip(surfs, ys):
            positions.append((round(x), y, s))
            x += s.get_width() + spacing_px
            height = max(height, y + s.get_height())
        out = pygame.Surface((max(0, round(x - spacing_px)), height), pygame.SRCALPHA)
        for px_, py_, s in positions:
            out.blit(s, (px_, py_))
        return out
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
                       color=(0, 0, 0, 255), letter_spacing: float = 0.0) -> pygame.Surface:
    """Return an immutable line raster from a bounded animation-safe cache."""
    frozen_color = tuple(color) if isinstance(color, (tuple, list)) else color
    key = (text, float(size), float(scale), weight, bool(bold), bool(italic),
           family, default_family, frozen_color, float(letter_spacing))
    with _line_surface_lock:
        surface = _line_surface_cache.get(key)
        if surface is not None:
            _line_surface_cache.move_to_end(key)
            return surface
    surface = render_line(
        text, size, scale=scale, weight=weight, bold=bold, italic=italic,
        family=family, color=color, letter_spacing=letter_spacing)
    with _line_surface_lock:
        _line_surface_cache[key] = surface
        _line_surface_cache.move_to_end(key)
        while len(_line_surface_cache) > 512:
            _line_surface_cache.popitem(last=False)
    return surface


def line_width(text: str, size: float, *, scale: float = 1.0,
               weight: int | None = None, bold: bool = False,
               italic: bool = False, family: str | None = None,
               letter_spacing: float = 0.0) -> float:
    """Width of a line in logical px under per-glyph fallback."""
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)
    return _line_width_cached(text, float(size), float(scale), wnum,
                              bool(italic), family, default_family,
                              font_revision, float(letter_spacing))


@lru_cache(maxsize=32768)
def _line_width_cached(text, size, scale, wnum, italic, family,
                       _default, _revision, letter_spacing=0.0):
    px = max(1, round(size * scale))
    total = sum(f.size(part)[0] for f, part in _segment(text, px, wnum, italic, family))
    if letter_spacing and len(text) > 1:
        total += letter_spacing * scale * (len(text) - 1)
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
    # The line box is 10/7 of the logical font size, independent of rasterizer
    # metrics: a 30px Text has a 43px box even if its glyph bitmap is shorter.
    return float(max(1, round(size * 10 / 7)))


def wrap(text: str, max_width: float, size: float, *, scale: float = 1.0,
         bold: bool = False, italic: bool = False, family: str | None = None,
         max_lines: int | None = None, weight: int | None = None,
         letter_spacing: float = 0.0) -> list[str]:
    """Word-wrap into lines fitting max_width (logical px). Honors \n breaks;
    char-splits words longer than a line; adds an ellipsis when truncated."""
    if not text:
        return []
    wnum = weight_num(weight) if weight is not None else weight_num(700 if bold else None)

    def width(s: str) -> float:
        return line_width(s, size, scale=scale, weight=wnum, italic=italic,
                          family=family, letter_spacing=letter_spacing)

    if "\n" not in text and (max_lines is None or max_lines >= 1) and \
            width(text) <= max_width:
        return [text]

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
