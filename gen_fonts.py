"""One-off: generate the hot-path static weight files bundled with saturn.

pygame's font stack has no variable-font axes; saturn instances variable
fonts at runtime (fonttools + disk cache), but the common 400/700 weights of
the bundled fonts are shipped pre-instanced so a cold start does zero
instancing work. Inter@400 needs none (its fvar default IS 400).

  saturn/assets/Inter-Bold.woff2          (from Inter variable, opsz=14, wght=700)
  saturn/assets/NotoSansSC-Regular.woff2  (wght=400 — the variable file's
      default master is 100/Thin, so it MUST be instanced for normal weight)
  saturn/assets/NotoSansSC-Bold.woff2     (wght=700)

Run: .venv/Scripts/python.exe gen_fonts.py
"""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import WOFF2FlavorData
from fontTools.varLib import instancer

ASSETS = Path(__file__).parent / "saturn" / "assets"


def instance(var_path: Path, axes: dict, out: Path):
    if out.exists():
        print(f"skip (exists): {out.name}")
        return
    font = TTFont(str(var_path))
    instancer.instantiateVariableFont(font, axes, inplace=True)
    font.flavor = "woff2" if out.suffix == ".woff2" else None
    if out.suffix == ".woff2":
        # Large CJK fonts load much faster without the optional glyf transform.
        font.flavorData = WOFF2FlavorData(transformedTables=set())
    font.save(str(out))
    font.close()
    print(f"wrote {out.name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    instance(ASSETS / "Inter-VariableFont_opsz,wght.woff2",
             {"opsz": 14, "wght": 700}, ASSETS / "Inter-Bold.woff2")
    instance(ASSETS / "NotoSansSC-VariableFont_wght.woff2",
             {"wght": 400}, ASSETS / "NotoSansSC-Regular.woff2")
    instance(ASSETS / "NotoSansSC-VariableFont_wght.woff2",
             {"wght": 700}, ASSETS / "NotoSansSC-Bold.woff2")
