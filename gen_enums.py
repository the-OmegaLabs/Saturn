"""One-off generator: rebuilds saturn/_gen/colors.py and saturn/_gen/icons.py.

Inputs (both committed):
  - gen/MaterialSymbolsOutlined.codepoints  (icon name -> codepoint, plane-0)
  - the installed flet package (member names are taken from it verbatim)

Palette embedded from Flutter's material colors.dart (2025 snapshot).
Run: .venv/Scripts/python.exe gen_enums.py
"""
from pathlib import Path

import flet as ft

# hue_lower -> (base_hex, {shade: hex}); hex without alpha
PALETTE = {
    "red": ("F44336", {100: "FFCDD2", 200: "EF9A9A", 300: "E57373", 400: "EF5350", 50: "FFEBEE", 500: "F44336", 600: "E53935", 700: "D32F2F", 800: "C62828", 900: "B71C1C"}),
    "redaccent": ("FF5252", {100: "FF8A80", 200: "FF5252", 400: "FF1744", 700: "D50000"}),
    "pink": ("E91E63", {100: "F8BBD0", 200: "F48FB1", 300: "F06292", 400: "EC407A", 50: "FCE4EC", 500: "E91E63", 600: "D81B60", 700: "C2185B", 800: "AD1457", 900: "880E4F"}),
    "pinkaccent": ("FF4081", {100: "FF80AB", 200: "FF4081", 400: "F50057", 700: "C51162"}),
    "purple": ("9C27B0", {100: "E1BEE7", 200: "CE93D8", 300: "BA68C8", 400: "AB47BC", 50: "F3E5F5", 500: "9C27B0", 600: "8E24AA", 700: "7B1FA2", 800: "6A1B9A", 900: "4A148C"}),
    "purpleaccent": ("E040FB", {100: "EA80FC", 200: "E040FB", 400: "D500F9", 700: "AA00FF"}),
    "deeppurple": ("673AB7", {100: "D1C4E9", 200: "B39DDB", 300: "9575CD", 400: "7E57C2", 50: "EDE7F6", 500: "673AB7", 600: "5E35B1", 700: "512DA8", 800: "4527A0", 900: "311B92"}),
    "deeppurpleaccent": ("7C4DFF", {100: "B388FF", 200: "7C4DFF", 400: "651FFF", 700: "6200EA"}),
    "indigo": ("3F51B5", {100: "C5CAE9", 200: "9FA8DA", 300: "7986CB", 400: "5C6BC0", 50: "E8EAF6", 500: "3F51B5", 600: "3949AB", 700: "303F9F", 800: "283593", 900: "1A237E"}),
    "indigoaccent": ("536DFE", {100: "8C9EFF", 200: "536DFE", 400: "3D5AFE", 700: "304FFE"}),
    "blue": ("2196F3", {100: "BBDEFB", 200: "90CAF9", 300: "64B5F6", 400: "42A5F5", 50: "E3F2FD", 500: "2196F3", 600: "1E88E5", 700: "1976D2", 800: "1565C0", 900: "0D47A1"}),
    "blueaccent": ("448AFF", {100: "82B1FF", 200: "448AFF", 400: "2979FF", 700: "2962FF"}),
    "lightblue": ("03A9F4", {100: "B3E5FC", 200: "81D4FA", 300: "4FC3F7", 400: "29B6F6", 50: "E1F5FE", 500: "03A9F4", 600: "039BE5", 700: "0288D1", 800: "0277BD", 900: "01579B"}),
    "lightblueaccent": ("40C4FF", {100: "80D8FF", 200: "40C4FF", 400: "00B0FF", 700: "0091EA"}),
    "cyan": ("00BCD4", {100: "B2EBF2", 200: "80DEEA", 300: "4DD0E1", 400: "26C6DA", 50: "E0F7FA", 500: "00BCD4", 600: "00ACC1", 700: "0097A7", 800: "00838F", 900: "006064"}),
    "cyanaccent": ("18FFFF", {100: "84FFFF", 200: "18FFFF", 400: "00E5FF", 700: "00B8D4"}),
    "teal": ("009688", {100: "B2DFDB", 200: "80CBC4", 300: "4DB6AC", 400: "26A69A", 50: "E0F2F1", 500: "009688", 600: "00897B", 700: "00796B", 800: "00695C", 900: "004D40"}),
    "tealaccent": ("64FFDA", {100: "A7FFEB", 200: "64FFDA", 400: "1DE9B6", 700: "00BFA5"}),
    "green": ("4CAF50", {100: "C8E6C9", 200: "A5D6A7", 300: "81C784", 400: "66BB6A", 50: "E8F5E9", 500: "4CAF50", 600: "43A047", 700: "388E3C", 800: "2E7D32", 900: "1B5E20"}),
    "greenaccent": ("69F0AE", {100: "B9F6CA", 200: "69F0AE", 400: "00E676", 700: "00C853"}),
    "lightgreen": ("8BC34A", {100: "DCEDC8", 200: "C5E1A5", 300: "AED581", 400: "9CCC65", 50: "F1F8E9", 500: "8BC34A", 600: "7CB342", 700: "689F38", 800: "558B2F", 900: "33691E"}),
    "lightgreenaccent": ("B2FF59", {100: "CCFF90", 200: "B2FF59", 400: "76FF03", 700: "64DD17"}),
    "lime": ("CDDC39", {100: "F0F4C3", 200: "E6EE9C", 300: "DCE775", 400: "D4E157", 50: "F9FBE7", 500: "CDDC39", 600: "C0CA33", 700: "AFB42B", 800: "9E9D24", 900: "827717"}),
    "limeaccent": ("EEFF41", {100: "F4FF81", 200: "EEFF41", 400: "C6FF00", 700: "AEEA00"}),
    "yellow": ("FFEB3B", {100: "FFF9C4", 200: "FFF59D", 300: "FFF176", 400: "FFEE58", 50: "FFFDE7", 500: "FFEB3B", 600: "FDD835", 700: "FBC02D", 800: "F9A825", 900: "F57F17"}),
    "yellowaccent": ("FFFF00", {100: "FFFF8D", 200: "FFFF00", 400: "FFEA00", 700: "FFD600"}),
    "amber": ("FFC107", {100: "FFECB3", 200: "FFE082", 300: "FFD54F", 400: "FFCA28", 50: "FFF8E1", 500: "FFC107", 600: "FFB300", 700: "FFA000", 800: "FF8F00", 900: "FF6F00"}),
    "amberaccent": ("FFD740", {100: "FFE57F", 200: "FFD740", 400: "FFC400", 700: "FFAB00"}),
    "orange": ("FF9800", {100: "FFE0B2", 200: "FFCC80", 300: "FFB74D", 400: "FFA726", 50: "FFF3E0", 500: "FF9800", 600: "FB8C00", 700: "F57C00", 800: "EF6C00", 900: "E65100"}),
    "orangeaccent": ("FFAB40", {100: "FFD180", 200: "FFAB40", 400: "FF9100", 700: "FF6D00"}),
    "deeporange": ("FF5722", {100: "FFCCBC", 200: "FFAB91", 300: "FF8A65", 400: "FF7043", 50: "FBE9E7", 500: "FF5722", 600: "F4511E", 700: "E64A19", 800: "D84315", 900: "BF360C"}),
    "deeporangeaccent": ("FF6E40", {100: "FF9E80", 200: "FF6E40", 400: "FF3D00", 700: "DD2C00"}),
    "brown": ("795548", {100: "D7CCC8", 200: "BCAAA4", 300: "A1887F", 400: "8D6E63", 50: "EFEBE9", 500: "795548", 600: "6D4C41", 700: "5D4037", 800: "4E342E", 900: "3E2723"}),
    "grey": ("9E9E9E", {100: "F5F5F5", 200: "EEEEEE", 300: "E0E0E0", 350: "D6D6D6", 400: "BDBDBD", 50: "FAFAFA", 500: "9E9E9E", 600: "757575", 700: "616161", 800: "424242", 850: "303030", 900: "212121"}),
    "bluegrey": ("607D8B", {100: "CFD8DC", 200: "B0BEC5", 300: "90A4AE", 400: "78909C", 50: "ECEFF1", 500: "607D8B", 600: "546E7A", 700: "455A64", 800: "37474F", 900: "263238"}),
    "black": ("000000", {}),
    "white": ("FFFFFF", {}),
    "transparent": ("000000", {}),
}

SYMBOLS_CP = Path(__file__).parent / "gen" / "MaterialSymbolsOutlined.codepoints"


def _alias_names(name: str):
    n = name.lower()
    base_stripped = [n]
    for suf in ("_outlined", "_rounded", "_sharp", "_filled", "_outline"):
        if n.endswith(suf):
            base_stripped.append(n.removesuffix(suf))
    out = list(base_stripped)
    for c in base_stripped:
        out += [c.removesuffix("_off") + "_inactive", c.removesuffix("_on") + "_active"]
    return out


def gen_colors():
    members = {m.name: m.value for m in ft.Colors}
    material = {}
    for hue, (base, shades) in PALETTE.items():
        material[hue] = base
        for shade, hx in shades.items():
            material[f"{hue}{shade}"] = hx
    out = ["# generated by gen_enums.py — do not edit",
           "import enum", "",
           "# flet value string -> RRGGBB hex (no alpha)",
           "MATERIAL = {"]
    out += [f'    "{k}": "{v}",' for k, v in sorted(material.items())]
    out += ["}", "", "", "class Colors(str, enum.Enum):"]
    out += [f'    {name} = "{val}"' for name, val in sorted(members.items())]
    (Path(__file__).parent / "saturn" / "_gen" / "colors.py").write_text(
        chr(10).join(out) + chr(10), encoding="utf8")
    return len(members), len(material)


def gen_icons():
    flet_names = [m.name for m in ft.Icons]
    master = {}
    for line in SYMBOLS_CP.read_text(encoding="utf8").splitlines():
        name, cp = line.split()
        master[name] = int(cp, 16)
    resolved = {}
    for name in flet_names:
        for cand in _alias_names(name):
            if cand in master:
                resolved[name] = master[cand]
                break
    out = ["# generated by gen_enums.py — do not edit",
           "import enum", "",
           "class Icons(enum.IntEnum):"]
    out += [f"    {name} = {cp}" for name, cp in sorted(resolved.items())]
    (Path(__file__).parent / "saturn" / "_gen" / "icons.py").write_text(
        chr(10).join(out) + chr(10), encoding="utf8")
    return len(resolved), len(flet_names)


if __name__ == "__main__":
    nc, npal = gen_colors()
    ni, nft = gen_icons()
    print(f"colors: {nc} members, {npal} palette entries")
    print(f"icons: {ni} / {nft} resolved")
