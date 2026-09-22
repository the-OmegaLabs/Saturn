"""Color parsing + Material 3 semantic role resolution.

parse_color is the single ColorValue entry point: hex strings (#RGB, #RRGGBB,
#AARRGGBB — flet puts alpha first), ints (0xAARRGGBB), (r,g,b) tuples,
Colors members, and named values ("red", "red500") or M3 role names
("primary", "onSurface") resolved against the active theme brightness.
"""
from __future__ import annotations

from ._gen.colors import MATERIAL, Colors  # noqa: F401  (re-exported)

# M3 baseline schemes (the classic 2021 spec defaults; Flutter derives these
# from a seed color now, we ship the baseline tables).
BASELINE_LIGHT = {
    "primary": "6750A4", "onprimary": "FFFFFF",
    "primarycontainer": "EADDFF", "onprimarycontainer": "21005D",
    "secondary": "625B71", "onsecondary": "FFFFFF",
    "secondarycontainer": "E8DEF8", "onsecondarycontainer": "1D192B",
    "tertiary": "7D5260", "ontertiary": "FFFFFF",
    "tertiarycontainer": "FFD8E4", "ontertiarycontainer": "31111D",
    "error": "B3261E", "onerror": "FFFFFF",
    "errorcontainer": "F9DEDC", "onerrorcontainer": "410E0B",
    "outline": "79747E", "outlinevariant": "CAC4D0",
    "surface": "FEF7FF", "onsurface": "1D1B20", "onsurfacevariant": "49454F",
    "inversesurface": "313033", "oninversesurface": "F4EFF4",
    "inverseprimary": "D0BCFF", "shadow": "000000", "scrim": "000000",
    "surfacecontainerlowest": "FFFFFF", "surfacecontainerlow": "F7F2FA",
    "surfacecontainer": "F3EDF7", "surfacecontainerhigh": "ECE6F0",
    "surfacecontainerhighest": "E6E0E9",
    "surfacedim": "DED8E1", "surfacebright": "FEF7FF",
    "primaryfixed": "EADDFF", "primaryfixeddim": "D0BCFF",
    "onprimaryfixed": "21005D", "onprimaryfixedvariant": "4F378B",
    "secondaryfixed": "E8DEF8", "secondaryfixeddim": "CCC2DC",
    "onsecondaryfixed": "1D192B", "onsecondaryfixedvariant": "4A4458",
    "tertiaryfixed": "FFD8E4", "tertiaryfixeddim": "EFB8C8",
    "ontertiaryfixed": "31111D", "ontertiaryfixedvariant": "633B48",
}
BASELINE_DARK = {
    "primary": "D0BCFF", "onprimary": "381E72",
    "primarycontainer": "4F378B", "onprimarycontainer": "EADDFF",
    "secondary": "CCC2DC", "onsecondary": "332D41",
    "secondarycontainer": "4A4458", "onsecondarycontainer": "E8DEF8",
    "tertiary": "EFB8C8", "ontertiary": "492532",
    "tertiarycontainer": "633B48", "ontertiarycontainer": "FFD8E4",
    "error": "F2B8B5", "onerror": "601410",
    "errorcontainer": "8C1D18", "onerrorcontainer": "F9DEDC",
    "outline": "938F99", "outlinevariant": "49454F",
    "surface": "141218", "onsurface": "E6E0E9", "onsurfacevariant": "CAC4D0",
    "inversesurface": "E6E0E9", "oninversesurface": "313033",
    "inverseprimary": "6750A4", "shadow": "000000", "scrim": "000000",
    "surfacecontainerlowest": "0F0D13", "surfacecontainerlow": "1D1B20",
    "surfacecontainer": "211F26", "surfacecontainerhigh": "2B2930",
    "surfacecontainerhighest": "36343B",
    "surfacedim": "141218", "surfacebright": "3B383E",
    "primaryfixed": "4F378B", "primaryfixeddim": "6750A4",
    "onprimaryfixed": "EADDFF", "onprimaryfixedvariant": "D0BCFF",
    "secondaryfixed": "4A4458", "secondaryfixeddim": "625B71",
    "onsecondaryfixed": "E8DEF8", "onsecondaryfixedvariant": "CCC2DC",
    "tertiaryfixed": "633B48", "tertiaryfixeddim": "7D5260",
    "ontertiaryfixed": "FFD8E4", "ontertiaryfixedvariant": "EFB8C8",
}

# set by the active Page's theme_mode; role names resolve against it
theme_dark: bool = False
role_overrides: dict[str, str] = {}  # Theme(color_scheme=...) lands in M3


def _hex_to_rgba(hex6: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex6.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def parse_color(value) -> tuple[int, int, int, int]:
    """Convert any ColorValue to an (r, g, b, a) tuple."""
    if value is None:
        raise ValueError("color is None")
    if isinstance(value, Colors):
        value = value.value
    if isinstance(value, (tuple, list)):
        r, g, b = (int(c) for c in value[:3])
        a = int(value[3]) if len(value) > 3 else 255
        return (r, g, b, a)
    if isinstance(value, int):
        value = f"{value & 0xFFFFFFFF:08X}"
    s = str(value).strip().lstrip("#")
    low = s.lower()
    if low == "transparent":
        return (0, 0, 0, 0)
    if low in MATERIAL:
        return _hex_to_rgba(MATERIAL[low])
    if low in BASELINE_LIGHT or low in role_overrides:
        if low in role_overrides:
            return _hex_to_rgba(role_overrides[low])
        table = BASELINE_DARK if theme_dark else BASELINE_LIGHT
        return _hex_to_rgba(table[low])
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) == 6:
        return _hex_to_rgba(s)
    if len(s) == 8:  # flet/Flutter convention: #AARRGGBB
        a = int(s[0:2], 16)
        return (int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16), a)
    raise ValueError(f"cannot parse color: {value!r}")
