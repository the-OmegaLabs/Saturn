r"""Fonts self-check: Regular-first async instancing + weight swap.

Headless, assert-based; exercises saturn.text directly (no window).
Run: .venv/Scripts/python.exe test_fonts.py
"""
import contextlib
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

import saturn as ft
from saturn import text as txt


def _cache_inst(wnum):
    inter = str(txt.INTER)
    key = (f"{Path(inter).stem}.{wnum}.{int(Path(inter).stat().st_mtime)}."
           f"{Path(inter).stat().st_size}")
    return Path.home() / ".cache" / "saturn" / "font-cache" / f"{key}.ttf"


def check_placeholder_then_swap():
    inter = str(txt.INTER)
    wnum = 500  # not a shipped static; Inter's fvar default is 400
    # every weight this check first-misses must start uncached, or earlier
    # app runs (which built 300/600 into the shared cache) break the run
    for w in (wnum, 300):
        p = _cache_inst(w)
        if p.exists():
            p.unlink()
    inst = _cache_inst(wnum)
    txt._font_cache.clear()
    txt._pending_inst.clear()
    txt._inst_failed.clear()
    txt._mem_instances.clear()
    txt._optimizing_notice = False
    swaps = []
    txt.on_weight_ready = lambda: swaps.append(1)

    # first miss: prints, starts the background build, shows Regular now
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        src, real = txt._weighted_source(inter, wnum)
    assert real and src == inter, (src, real)   # Regular = default instance
    assert (inter, wnum) in txt._pending_inst

    # while pending: same placeholder, no duplicate print/thread
    out2 = io.StringIO()
    with contextlib.redirect_stdout(out2):
        src2, real2 = txt._weighted_source(inter, wnum)
    assert (src2, real2) == (inter, True)
    assert out2.getvalue() == ""

    # a second weight's first miss starts its own build but stays silent —
    # the notice prints only once per run
    out3 = io.StringIO()
    with contextlib.redirect_stdout(out3):
        src3, real3 = txt._weighted_source(inter, 300)
    assert (src3, real3) == (inter, True)
    assert (inter, 300) in txt._pending_inst
    assert out3.getvalue() == ""

    # a placeholder font gets cached under the requested weight ...
    link = ("file", inter, wnum, False)
    ph = txt._render_font(link, 16)

    deadline = time.time() + 30
    while time.time() < deadline and (inter, wnum) in txt._pending_inst:
        time.sleep(0.05)
    assert (inter, wnum) not in txt._pending_inst, "instancing did not finish"
    assert swaps, "on_weight_ready hook did not fire"
    assert inst.exists(), "instance not written to the disk cache"

    # ... and was evicted: the link now builds from the real instance
    after = txt._render_font(link, 16)
    assert after is not ph, "placeholder font was not evicted after swap"
    src4, real4 = txt._weighted_source(inter, wnum)
    assert real4 and src4 == str(inst), (src4, real4)

    txt.on_weight_ready = None
    print("fonts ok (regular-first async instancing + swap)")


def check_cached_weight_is_sync():
    # once cached, no print and the instance path comes back immediately
    inter = str(txt.INTER)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        src, real = txt._weighted_source(inter, 500)
    assert real and src.endswith(".ttf") and src != inter
    assert out.getvalue() == ""
    print("fonts ok (cached weight loads sync, silent)")


if __name__ == "__main__":
    check_placeholder_then_swap()
    check_cached_weight_is_sync()
    print("ALL PASS")
