"""Integration layer - bridges new refactored components with existing code.

This module provides backwards-compatible wrappers and migration utilities
to gradually adopt the new thread-safe, optimized architecture without
breaking existing applications.
"""
from __future__ import annotations

import functools
import threading
from typing import Any, Callable, TypeVar

from ._threading import ThreadSafeDict, ThreadSafeValue
from ._theme import ThemeManager, FontManager
from ._errors import handle_error, safe_call, ErrorSeverity, logger
from ._performance import get_render_cache, get_layout_cache, get_performance_monitor

T = TypeVar('T')


class CompatibilityLayer:
    """Provides backwards compatibility during migration.
    
    Allows existing code to continue using global state while
    internally routing through the new thread-safe systems.
    """
    
    def __init__(self):
        self._theme_manager = ThemeManager()
        self._font_manager = FontManager()
        self._lock = threading.RLock()
        self._migration_warnings_shown = set()
    
    def get_theme_manager(self) -> ThemeManager:
        """Get thread-safe theme manager."""
        return self._theme_manager
    
    def get_font_manager(self) -> FontManager:
        """Get thread-safe font manager."""
        return self._font_manager
    
    def warn_once(self, key: str, message: str) -> None:
        """Show migration warning once per key."""
        if key not in self._migration_warnings_shown:
            logger.warning(f"[MIGRATION] {message}")
            self._migration_warnings_shown.add(key)


# Global compatibility layer instance
_compat = CompatibilityLayer()


def get_compat_layer() -> CompatibilityLayer:
    """Get global compatibility layer."""
    return _compat


# Decorator for safe method calls
def safe_method(
    context: str = "",
    fallback: Any = None,
    log_errors: bool = True
):
    """Decorator to wrap methods with error handling.
    
    Example:
        class Widget:
            @safe_method("rendering widget", fallback=None)
            def render(self):
                # If this raises, error is logged and None is returned
                risky_operation()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ctx = context or f"{func.__qualname__}"
            return safe_call(
                func, *args,
                context=ctx,
                fallback=fallback,
                log_errors=log_errors,
                **kwargs
            )
        return wrapper
    return decorator


def thread_safe_property(attr_name: str):
    """Decorator to make a property thread-safe.
    
    Example:
        class Control:
            @thread_safe_property("_opacity")
            def opacity(self):
                pass
    """
    def decorator(func):
        @property
        @functools.wraps(func)
        def wrapper(self):
            if not hasattr(self, '_property_lock'):
                self._property_lock = threading.RLock()
            with self._property_lock:
                return getattr(self, attr_name, func(self))
        
        @wrapper.setter
        def setter(self, value):
            if not hasattr(self, '_property_lock'):
                self._property_lock = threading.RLock()
            with self._property_lock:
                setattr(self, attr_name, value)
        
        return wrapper
    return decorator


class MigrationHelper:
    """Utilities to help migrate existing code to new architecture."""
    
    @staticmethod
    def wrap_control_init(original_init):
        """Wrap Control.__init__ to add new thread-safe fields.
        
        This allows gradual migration without breaking existing controls.
        """
        @functools.wraps(original_init)
        def wrapped_init(self, **kwargs):
            # Add new thread-safe infrastructure
            if not hasattr(self, '_animation_lock'):
                object.__setattr__(self, "_animation_lock", threading.RLock())
            if not hasattr(self, '_animation_overrides'):
                object.__setattr__(self, "_animation_overrides", ThreadSafeDict())
            if not hasattr(self, '_animation_targets'):
                object.__setattr__(self, "_animation_targets", ThreadSafeDict())
            
            # Call original init
            return original_init(self, **kwargs)
        
        return wrapped_init
    
    @staticmethod
    def make_thread_safe(cls):
        """Class decorator to add thread safety to existing classes.
        
        Example:
            @MigrationHelper.make_thread_safe
            class Button(Control):
                pass
        """
        # Wrap __init__
        if hasattr(cls, '__init__'):
            original_init = cls.__init__
            cls.__init__ = MigrationHelper.wrap_control_init(original_init)
        
        return cls
    
    @staticmethod
    def create_cached_property(compute_func: Callable, cache_name: str):
        """Create a property that caches its computed value.
        
        Example:
            class Widget:
                def _compute_size(self):
                    # Expensive calculation
                    return (width, height)
                
                size = MigrationHelper.create_cached_property(
                    _compute_size, "_cached_size"
                )
        """
        @property
        def cached_property(self):
            if not hasattr(self, cache_name):
                value = compute_func(self)
                setattr(self, cache_name, value)
            return getattr(self, cache_name)
        
        return cached_property


class PerformanceIntegration:
    """Integration helpers for performance monitoring."""
    
    @staticmethod
    def timed_method(category: str = "general"):
        """Decorator to measure method execution time.
        
        Example:
            @PerformanceIntegration.timed_method("layout")
            def calculate_layout(self):
                pass
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                import time
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    monitor = get_performance_monitor()
                    
                    # Record to appropriate category
                    if category == "layout":
                        monitor.record_layout(duration)
                    elif category == "render":
                        monitor.record_render(duration)
                    else:
                        monitor.record_frame(duration)
            
            return wrapper
        return decorator
    
    @staticmethod
    def cached_text_render(render_func):
        """Wrap text rendering function with caching.
        
        Example:
            @PerformanceIntegration.cached_text_render
            def render_line(text, size, family, ...):
                # Expensive pygame.font.render()
                pass
        """
        @functools.wraps(render_func)
        def wrapper(text, size, family="Inter", weight="normal", 
                   italic=False, color=(0, 0, 0, 255), scale=1.0, **kwargs):
            cache = get_render_cache()
            
            # Try cache first
            surface = cache.get_text_surface(
                text, size, family, weight, italic, color, scale
            )
            if surface is not None:
                return surface
            
            # Render and cache
            surface = render_func(
                text, size, family=family, weight=weight,
                italic=italic, color=color, scale=scale, **kwargs
            )
            cache.cache_text_surface(
                text, size, family, weight, italic, color, scale, surface
            )
            
            return surface
        
        return wrapper


# Convenience exports
__all__ = [
    "CompatibilityLayer",
    "get_compat_layer",
    "safe_method",
    "thread_safe_property",
    "MigrationHelper",
    "PerformanceIntegration",
]
