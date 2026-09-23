"""Paths to Saturn's bundled Noto Sans SC font assets."""

from pathlib import Path

ASSET_DIR = Path(__file__).parent
VARIABLE_FONT = ASSET_DIR / "NotoSansSC-VariableFont_wght.ttf"
REGULAR_FONT = ASSET_DIR / "NotoSansSC-Regular.ttf"
BOLD_FONT = ASSET_DIR / "NotoSansSC-Bold.ttf"

__all__ = ["ASSET_DIR", "VARIABLE_FONT", "REGULAR_FONT", "BOLD_FONT"]
__version__ = "0.1.0"
