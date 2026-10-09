#!/usr/bin/env python3
"""Pixel-compare two PNGs for Saturn C++ demo parity.

Caps: rejects images larger than kMaxScreenshotPixels (16M). Exit 0 on pass.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image

# Keep in sync with cpp/include/saturn/limits.hpp kMaxScreenshotPixels.
MAX_PIXELS = 1 << 24


def load(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    if w <= 0 or h <= 0:
        raise SystemExit(f"empty image: {path}")
    if w * h > MAX_PIXELS:
        raise SystemExit(f"image too large ({w}x{h}): {path}")
    return im


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("golden", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("--max-avg", type=float, default=2.0,
                   help="max mean absolute RGB error (0-255)")
    p.add_argument("--max-diff-frac", type=float, default=0.002,
                   help="max fraction of pixels with any channel delta > --tol")
    p.add_argument("--tol", type=int, default=2,
                   help="per-channel absolute tolerance before counting a diff")
    p.add_argument("--diff-out", type=Path, default=None,
                   help="optional path to write a red-highlight diff PNG")
    args = p.parse_args()

    a = load(args.golden)
    b = load(args.candidate)
    if a.size != b.size:
        print(f"SIZE_MISMATCH golden={a.size} candidate={b.size}", file=sys.stderr)
        return 2

    pa, pb = a.load(), b.load()
    w, h = a.size
    n = w * h
    abs_sum = 0.0
    bad = 0
    diff = Image.new("RGBA", (w, h), (0, 0, 0, 255)) if args.diff_out else None
    pd = diff.load() if diff else None
    for y in range(h):
        for x in range(w):
            ca, cb = pa[x, y], pb[x, y]
            d = tuple(abs(ca[i] - cb[i]) for i in range(3))
            abs_sum += sum(d) / 3.0
            if max(d) > args.tol:
                bad += 1
                if pd is not None:
                    pd[x, y] = (255, 0, 0, 255)
            elif pd is not None:
                g = ca[0]
                pd[x, y] = (g, g, g, 255)
    avg = abs_sum / n
    frac = bad / n
    print(f"ok_size={w}x{h} avg_abs={avg:.4f} diff_frac={frac:.6f} bad={bad}/{n}")
    if diff is not None and args.diff_out:
        args.diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff.save(args.diff_out)
        print(f"wrote {args.diff_out}")
    if avg > args.max_avg or frac > args.max_diff_frac:
        print("FAIL", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
