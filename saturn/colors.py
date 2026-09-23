"""Color parsing + Material 3 semantic role resolution.

parse_color is the single ColorValue entry point: hex strings (#RGB, #RRGGBB,
#AARRGGBB — flet puts alpha first), ints (0xAARRGGBB), (r,g,b) tuples,
Colors members, and named values ("red", "red500") or M3 role names
("primary", "onSurface") resolved against the active theme brightness.
"""
from __future__ import annotations

import sys

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

# Flutter 3 / Flet 1.0 ColorScheme.fromSeed for Material indigo (#3F51B5),
# captured from the reference renderer. Keep this exact table for the common
# named seed while a general HCT generator remains outside Saturn's light
# dependency budget.
INDIGO_LIGHT = {
    "primary": "515B92", "onprimary": "FFFFFF",
    "primarycontainer": "DEE0FF", "onprimarycontainer": "394379",
    "secondary": "5B5D72", "onsecondary": "FFFFFF",
    "secondarycontainer": "E0E1F9", "onsecondarycontainer": "434659",
    "tertiary": "77536D", "ontertiary": "FFFFFF",
    "tertiarycontainer": "FFD7F1", "ontertiarycontainer": "5D3C55",
    "error": "BA1A1A", "onerror": "FFFFFF",
    "errorcontainer": "FFDAD6", "onerrorcontainer": "93000A",
    "outline": "767680", "outlinevariant": "C7C5D0",
    "surface": "FBF8FF", "onsurface": "1B1B21", "onsurfacevariant": "46464F",
    "inversesurface": "303036", "oninversesurface": "F2EFF7",
    "inverseprimary": "BAC3FF", "shadow": "000000", "scrim": "000000",
    "surfacecontainerlowest": "FFFFFF", "surfacecontainerlow": "F5F2FA",
    "surfacecontainer": "EFEDF4", "surfacecontainerhigh": "E9E7EF",
    "surfacecontainerhighest": "E4E1E9", "surfacedim": "DBD9E0",
    "surfacebright": "FBF8FF",
}
INDIGO_DARK = {
    "primary": "BAC3FF", "onprimary": "222C61",
    "primarycontainer": "394379", "onprimarycontainer": "DEE0FF",
    "secondary": "C3C5DD", "onsecondary": "2D2F42",
    "secondarycontainer": "434659", "onsecondarycontainer": "E0E1F9",
    "tertiary": "E6BAD7", "ontertiary": "44263D",
    "tertiarycontainer": "5D3C55", "ontertiarycontainer": "FFD7F1",
    "error": "FFB4AB", "onerror": "690005",
    "errorcontainer": "93000A", "onerrorcontainer": "FFDAD6",
    "outline": "90909A", "outlinevariant": "46464F",
    "surface": "121318", "onsurface": "E4E1E9", "onsurfacevariant": "C7C5D0",
    "inversesurface": "E4E1E9", "oninversesurface": "303036",
    "inverseprimary": "515B92", "shadow": "000000", "scrim": "000000",
    "surfacecontainerlowest": "0D0E13", "surfacecontainerlow": "1B1B21",
    "surfacecontainer": "1F1F25", "surfacecontainerhigh": "29292F",
    "surfacecontainerhighest": "34343A", "surfacedim": "121318",
    "surfacebright": "39393F",
}

# Compose Material 3 1.5.0-alpha28 expressiveLightColorScheme(): only these
# four on-container roles differ from lightColorScheme(). Custom seed schemes
# supply their own colors, as in Compose's MaterialExpressiveTheme(colorScheme=).
EXPRESSIVE_LIGHT = {
    "onprimarycontainer": "4F378B",
    "onsecondarycontainer": "4A4458",
    "ontertiarycontainer": "633B48",
    "onerrorcontainer": "8C1D18",
}

# set by the active Page's theme_mode; role names resolve against it
theme_dark: bool = False
role_overrides: dict[str, str] = {}  # Theme(color_scheme=...) lands in M3

_system_dark_cache: bool | None = None


def system_prefers_dark() -> bool:
    """Windows app-mode dark preference (ThemeMode.SYSTEM resolution);
    cached once per run — flipping the OS theme mid-run is not a thing."""
    global _system_dark_cache
    if _system_dark_cache is None:
        v = False
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                    v = winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
            except OSError:
                pass
        _system_dark_cache = v
    return _system_dark_cache


def apply_seed(seed, *, expressive: bool = False) -> None:
    """Apply a known Flet ColorScheme.fromSeed table to semantic roles."""
    role_overrides.clear()
    if seed is None:
        if expressive and not theme_dark:
            role_overrides.update(EXPRESSIVE_LIGHT)
        return
    value = getattr(seed, "value", seed)
    try:
        rgba = parse_color(value)
    except (TypeError, ValueError):
        return
    if rgba[:3] == (0x3F, 0x51, 0xB5):
        role_overrides.update(INDIGO_DARK if theme_dark else INDIGO_LIGHT)


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


def with_opacity(opacity: float, color) -> str:
    """flet Colors.with_opacity: `color` at the given opacity, as #AARRGGBB
    (parse_color reads it back)."""
    r, g, b, _ = parse_color(color)
    a = round(max(0.0, min(1.0, opacity)) * 255)
    return f"#{a:02X}{r:02X}{g:02X}{b:02X}"


# Colors is generated ("do not edit"); flet exposes with_opacity on it, so
# attach here. Enum classes accept new non-member attributes.
Colors.with_opacity = staticmethod(with_opacity)
