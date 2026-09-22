"""One-off: generate the hot-path static weight files bundled with saturn.

pygame's font stack has no variable-font axes; saturn instances variable
fonts at runtime (fonttools + disk cache), but the common 400/700 weights of
the bundled fonts are shipped pre-instanced so a cold start does zero
instancing work. Inter@400 needs none (its fvar default IS 400).

  saturn/assets/Inter-Bold.ttf            (from Inter variable, opsz=14, wght=700)
  saturn/assets/NotoSansSC-Regular.ttf    (wght=400 — the variable file's
      default master is 100/Thin, so it MUST be instanced for normal weight)
  saturn/assets/NotoSansSC-Bold.ttf       (wght=700)

Run: .venv/Scripts/python.exe gen_fonts.py
"""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ASSETS = Path(__file__).parent / "saturn" / "assets"


def instance(var_path: Path, axes: dict, out: Path):
    if out.exists():
        print(f"skip (exists): {out.name}")
        return
    font = TTFont(str(var_path))
    instancer.instantiateVariableFont(font, axes, inplace=True)
    font.save(str(out))
    print(f"wrote {out.name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    instance(ASSETS / "Inter-VariableFont_opsz,wght.ttf",
             {"opsz": 14, "wght": 700}, ASSETS / "Inter-Bold.ttf")
    instance(ASSETS / "NotoSansSC-VariableFont_wght.ttf",
             {"wght": 400}, ASSETS / "NotoSansSC-Regular.ttf")
    instance(ASSETS / "NotoSansSC-VariableFont_wght.ttf",
             {"wght": 700}, ASSETS / "NotoSansSC-Bold.ttf")
