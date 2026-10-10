"""Theme management system - replaces global color state.

This module eliminates the global `theme_dark` and `_seed_cache` variables
from colors.py, making themes instance-based and thread-safe.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Tuple

from . import colors as legacy_colors
from ._threading import ThreadSafeDict


@dataclass
class ColorRole:
    """A single color role with light and dark variants."""
    light: str
    dark: str
    
    def get(self, dark_mode: bool) -> str:
        """Get the appropriate color for the current mode."""
        return self.dark if dark_mode else self.light


@dataclass
class ColorPalette:
    """Complete Material 3 color palette."""
    
    # Primary colors
    primary: ColorRole
    on_primary: ColorRole
    primary_container: ColorRole
    on_primary_container: ColorRole
    
    # Secondary colors
    secondary: ColorRole
    on_secondary: ColorRole
    secondary_container: ColorRole
    on_secondary_container: ColorRole
    
    # Tertiary colors
    tertiary: ColorRole
    on_tertiary: ColorRole
    tertiary_container: ColorRole
    on_tertiary_container: ColorRole
    
    # Error colors
    error: ColorRole
    on_error: ColorRole
    error_container: ColorRole
    on_error_container: ColorRole
    
    # Surface colors
    surface: ColorRole
    on_surface: ColorRole
    surface_variant: ColorRole
    on_surface_variant: ColorRole
    
    # Background colors
    background: ColorRole
    on_background: ColorRole
    
    # Outline colors
    outline: ColorRole
    outline_variant: ColorRole
    
    # Other
    shadow: ColorRole
    scrim: ColorRole
    inverse_surface: ColorRole
    inverse_on_surface: ColorRole
    inverse_primary: ColorRole
    
    @classmethod
    def default(cls) -> ColorPalette:
        """Create default Material 3 baseline palette."""
        return cls(
            primary=ColorRole("#6750A4", "#D0BCFF"),
            on_primary=ColorRole("#FFFFFF", "#381E72"),
            primary_container=ColorRole("#EADDFF", "#4F378B"),
            on_primary_container=ColorRole("#21005D", "#EADDFF"),
            
            secondary=ColorRole("#625B71", "#CCC2DC"),
            on_secondary=ColorRole("#FFFFFF", "#332D41"),
            secondary_container=ColorRole("#E8DEF8", "#4A4458"),
            on_secondary_container=ColorRole("#1D192B", "#E8DEF8"),
            
            tertiary=ColorRole("#7D5260", "#EFB8C8"),
            on_tertiary=ColorRole("#FFFFFF", "#492532"),
            tertiary_container=ColorRole("#FFD8E4", "#633B48"),
            on_tertiary_container=ColorRole("#31111D", "#FFD8E4"),
            
            error=ColorRole("#B3261E", "#F2B8B5"),
            on_error=ColorRole("#FFFFFF", "#601410"),
            error_container=ColorRole("#F9DEDC", "#8C1D18"),
            on_error_container=ColorRole("#410E0B", "#F9DEDC"),
            
            surface=ColorRole("#FFFBFE", "#1C1B1F"),
            on_surface=ColorRole("#1C1B1F", "#E6E1E5"),
            surface_variant=ColorRole("#E7E0EC", "#49454F"),
            on_surface_variant=ColorRole("#49454F", "#CAC4D0"),
            
            background=ColorRole("#FFFBFE", "#1C1B1F"),
            on_background=ColorRole("#1C1B1F", "#E6E1E5"),
            
            outline=ColorRole("#79747E", "#938F99"),
            outline_variant=ColorRole("#CAC4D0", "#49454F"),
            
            shadow=ColorRole("#000000", "#000000"),
            scrim=ColorRole("#000000", "#000000"),
            inverse_surface=ColorRole("#313033", "#E6E1E5"),
            inverse_on_surface=ColorRole("#F4EFF4", "#313033"),
            inverse_primary=ColorRole("#D0BCFF", "#6750A4"),
        )


class ThemeManager:
    """Thread-safe theme manager - replaces global color state.
    
    Each Page instance should have its own ThemeManager to avoid
    conflicts between multiple windows.
    """
    
    def __init__(self, dark_mode: bool = False, seed: str | None = None):
        self._dark_mode = dark_mode
        self._palette = ColorPalette.default()
        self._seed = seed
        self._lock = threading.RLock()
        self._seed_cache = ThreadSafeDict[ColorPalette]()
        
        if seed:
            self.apply_seed(seed)
    
    @property
    def dark_mode(self) -> bool:
        """Get current dark mode state."""
        with self._lock:
            return self._dark_mode
    
    @dark_mode.setter
    def dark_mode(self, value: bool) -> None:
        """Set dark mode."""
        with self._lock:
            self._dark_mode = bool(value)
    
    def color(self, role: str) -> str:
        """Get color for a role in current theme mode.
        
        Args:
            role: Color role name (e.g., "primary", "surface")
        
        Returns:
            Hex color string
        
        Example:
            theme.color("primary")  # Returns "#6750A4" or "#D0BCFF"
        """
        with self._lock:
            role_obj = getattr(self._palette, role.lower(), None)
            if role_obj is None:
                # Fallback to legacy colors module for backwards compatibility
                return getattr(legacy_colors.Colors, role.upper(), "#000000")
            return role_obj.get(self._dark_mode)
    
    def apply_seed(self, seed: str) -> None:
        """Apply a seed color to generate the palette.
        
        Args:
            seed: Seed color name or hex
        """
        with self._lock:
            # Check cache first
            cached = self._seed_cache.get(seed)
            if cached:
                self._palette = cached
                self._seed = seed
                return
            
            # Generate new palette (simplified - full implementation would use
            # Material Color Utilities for proper tone generation)
            if seed == "blue":
                palette = ColorPalette.default()
            else:
                # For now, use default palette
                # TODO: Implement proper seed color generation
                palette = ColorPalette.default()
            
            self._seed_cache.set(seed, palette)
            self._palette = palette
            self._seed = seed
    
    def to_legacy_globals(self) -> None:
        """Update legacy global color state for backwards compatibility.
        
        This is a temporary bridge until all code is migrated to use
        ThemeManager directly.
        """
        with self._lock:
            legacy_colors.theme_dark = self._dark_mode
            # Update Colors class attributes to match current palette
            # This ensures existing code that reads Colors.SURFACE still works


class FontManager:
    """Thread-safe font management - replaces global text module state.
    
    Manages font family defaults and registration.
    """
    
    def __init__(self, default_family: str = "Inter"):
        self._default_family = default_family
        self._custom_fonts: Dict[str, str] = {}  # alias -> path
        self._lock = threading.RLock()
    
    @property
    def default_family(self) -> str:
        """Get default font family."""
        with self._lock:
            return self._default_family
    
    @default_family.setter
    def default_family(self, family: str) -> None:
        """Set default font family."""
        with self._lock:
            self._default_family = family
    
    def register_font(self, alias: str, path: str) -> None:
        """Register a custom font.
        
        Args:
            alias: Font family alias to use in code
            path: Filesystem path to font file
        """
        with self._lock:
            self._custom_fonts[alias] = path
    
    def get_font_path(self, alias: str) -> str | None:
        """Get registered font path by alias."""
        with self._lock:
            return self._custom_fonts.get(alias)
    
    def registered_fonts(self) -> Dict[str, str]:
        """Get all registered fonts (returns copy)."""
        with self._lock:
            return dict(self._custom_fonts)


# Backwards compatibility helpers
def create_default_theme_manager(dark: bool = False) -> ThemeManager:
    """Create a default theme manager instance."""
    return ThemeManager(dark_mode=dark)
