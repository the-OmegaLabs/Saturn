"""Paths to Saturn's bundled Material Symbols font assets."""

from pathlib import Path

ASSET_DIR = Path(__file__).parent
FILLED_FONT = ASSET_DIR / "MaterialSymbolsFilled.ttf"
OUTLINED_FONT = ASSET_DIR / "MaterialSymbolsOutlined.ttf"

__all__ = ["ASSET_DIR", "FILLED_FONT", "OUTLINED_FONT"]
__version__ = "0.1.0"
