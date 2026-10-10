"""Performance optimization layer - caching and lazy evaluation.

Implements:
- Text rendering cache with LRU eviction
- Layout result caching
- Texture/surface caching
- Incremental layout system
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, TypeVar, Generic

from ._threading import LRUCache, AtomicCounter
from ._errors import logger

T = TypeVar('T')


class RenderCache:
    """Cache for expensive rendering operations.
    
    Tracks:
    - Text surfaces
    - Icon surfaces  
    - Gradient surfaces
    - Filter results
    """
    
    def __init__(self, max_text_surfaces: int = 1000, max_textures: int = 500):
        self._text_cache = LRUCache[Any](max_text_surfaces)
        self._texture_cache = LRUCache[Any](max_textures)
        self._gradient_cache = LRUCache[Any](100)
        
        # Statistics
        self._start_time = time.time()
    
    def get_text_surface(
        self,
        text: str,
        size: float,
        family: str,
        weight: str,
        italic: bool,
        color: tuple,
        scale: float,
    ) -> Any | None:
        """Get cached text surface or None."""
        key = (text, size, family, weight, italic, color, scale)
        return self._text_cache.get(key)
    
    def cache_text_surface(
        self,
        text: str,
        size: float,
        family: str,
        weight: str,
        italic: bool,
        color: tuple,
        scale: float,
        surface: Any,
    ) -> None:
        """Store text surface in cache."""
        key = (text, size, family, weight, italic, color, scale)
        self._text_cache.put(key, surface)
    
    def get_texture(self, path: str, scale: float) -> Any | None:
        """Get cached texture or None."""
        key = (path, scale)
        return self._texture_cache.get(key)
    
    def cache_texture(self, path: str, scale: float, texture: Any) -> None:
        """Store texture in cache."""
        key = (path, scale)
        self._texture_cache.put(key, texture)
    
    def clear(self) -> None:
        """Clear all caches."""
        self._text_cache.clear()
        self._texture_cache.clear()
        self._gradient_cache.clear()
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "text_cache": self._text_cache.stats(),
            "texture_cache": self._texture_cache.stats(),
            "gradient_cache": self._gradient_cache.stats(),
            "uptime_seconds": time.time() - self._start_time,
        }
    
    def log_stats(self) -> None:
        """Log cache statistics."""
        stats = self.stats()
        logger.info(f"=== RenderCache Statistics ===")
        logger.info(f"Text cache: {stats['text_cache']['size']}/{stats['text_cache']['max_size']} "
                   f"(hit rate: {stats['text_cache']['hit_rate']:.2%})")
        logger.info(f"Texture cache: {stats['texture_cache']['size']}/{stats['texture_cache']['max_size']} "
                   f"(hit rate: {stats['texture_cache']['hit_rate']:.2%})")
        logger.info(f"Uptime: {stats['uptime_seconds']:.1f}s")


class LayoutCache:
    """Cache layout calculation results.
    
    Uses content-based hashing to detect when recalculation is needed.
    """
    
    def __init__(self):
        self._cache: dict[int, tuple[Any, str]] = {}  # control_id -> (layout, content_hash)
        self._version_counter = AtomicCounter()
    
    def get_layout(self, control_id: int, content: Any) -> Any | None:
        """Get cached layout if content unchanged.
        
        Args:
            control_id: Unique control ID
            content: Content to hash (geometry, children, etc)
        
        Returns:
            Cached layout or None if invalid
        """
        if control_id not in self._cache:
            return None
        
        cached_layout, cached_hash = self._cache[control_id]
        current_hash = self._hash_content(content)
        
        if current_hash == cached_hash:
            return cached_layout
        
        return None
    
    def store_layout(self, control_id: int, content: Any, layout: Any) -> None:
        """Store layout result.
        
        Args:
            control_id: Unique control ID
            content: Content that was laid out
            layout: Layout result to cache
        """
        content_hash = self._hash_content(content)
        self._cache[control_id] = (layout, content_hash)
    
    def invalidate(self, control_id: int) -> None:
        """Invalidate cached layout for a control."""
        self._cache.pop(control_id, None)
    
    def clear(self) -> None:
        """Clear entire layout cache."""
        self._cache.clear()
    
    @staticmethod
    def _hash_content(content: Any) -> str:
        """Hash content for change detection."""
        # Simple string-based hash for now
        # TODO: More sophisticated hashing for complex objects
        content_str = str(content)
        return hashlib.md5(content_str.encode()).hexdigest()


class LazyValue(Generic[T]):
    """Lazy-evaluated value with caching.
    
    Computes value only when accessed and caches result until invalidated.
    """
    
    def __init__(self, compute_func: Callable[[], T]):
        self._compute = compute_func
        self._value: T | None = None
        self._computed = False
    
    def get(self) -> T:
        """Get value, computing if needed."""
        if not self._computed:
            self._value = self._compute()
            self._computed = True
        return self._value
    
    def invalidate(self) -> None:
        """Mark value as stale (needs recomputation)."""
        self._computed = False
        self._value = None
    
    @property
    def is_valid(self) -> bool:
        """Check if cached value is valid."""
        return self._computed


class IncrementalLayoutTracker:
    """Track which controls need layout recalculation.
    
    Implements incremental layout:
    - Only recalculate controls that changed
    - Skip unchanged subtrees
    - Propagate layout changes up the tree
    """
    
    def __init__(self):
        self._dirty_controls: set[int] = set()  # IDs of controls needing layout
        self._layout_versions: dict[int, int] = {}  # control_id -> version
        self._global_version = AtomicCounter()
    
    def mark_dirty(self, control_id: int) -> None:
        """Mark control and ancestors as needing layout."""
        self._dirty_controls.add(control_id)
        self._layout_versions[control_id] = self._global_version.increment()
    
    def mark_clean(self, control_id: int) -> None:
        """Mark control as having valid layout."""
        self._dirty_controls.discard(control_id)
    
    def is_dirty(self, control_id: int) -> bool:
        """Check if control needs layout."""
        return control_id in self._dirty_controls
    
    def get_version(self, control_id: int) -> int:
        """Get layout version for control."""
        return self._layout_versions.get(control_id, 0)
    
    def clear(self) -> None:
        """Clear all dirty flags."""
        self._dirty_controls.clear()
    
    def dirty_count(self) -> int:
        """Count of controls needing layout."""
        return len(self._dirty_controls)


class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    def __init__(self):
        self._frame_times: list[float] = []
        self._layout_times: list[float] = []
        self._render_times: list[float] = []
        self._max_samples = 60  # Keep last 60 frames
    
    def record_frame(self, duration: float) -> None:
        """Record frame time."""
        self._frame_times.append(duration)
        if len(self._frame_times) > self._max_samples:
            self._frame_times.pop(0)
    
    def record_layout(self, duration: float) -> None:
        """Record layout time."""
        self._layout_times.append(duration)
        if len(self._layout_times) > self._max_samples:
            self._layout_times.pop(0)
    
    def record_render(self, duration: float) -> None:
        """Record render time."""
        self._render_times.append(duration)
        if len(self._render_times) > self._max_samples:
            self._render_times.pop(0)
    
    def get_stats(self) -> dict:
        """Get performance statistics."""
        def avg(times: list[float]) -> float:
            return sum(times) / len(times) if times else 0
        
        def max_time(times: list[float]) -> float:
            return max(times) if times else 0
        
        avg_frame = avg(self._frame_times)
        fps = 1.0 / avg_frame if avg_frame > 0 else 0
        
        return {
            "fps": fps,
            "frame_time_ms": avg_frame * 1000,
            "frame_time_max_ms": max_time(self._frame_times) * 1000,
            "layout_time_ms": avg(self._layout_times) * 1000,
            "layout_time_max_ms": max_time(self._layout_times) * 1000,
            "render_time_ms": avg(self._render_times) * 1000,
            "render_time_max_ms": max_time(self._render_times) * 1000,
        }
    
    def log_stats(self) -> None:
        """Log performance statistics."""
        stats = self.get_stats()
        logger.info(f"=== Performance Statistics ===")
        logger.info(f"FPS: {stats['fps']:.1f}")
        logger.info(f"Frame time: {stats['frame_time_ms']:.2f}ms "
                   f"(max: {stats['frame_time_max_ms']:.2f}ms)")
        logger.info(f"Layout time: {stats['layout_time_ms']:.2f}ms "
                   f"(max: {stats['layout_time_max_ms']:.2f}ms)")
        logger.info(f"Render time: {stats['render_time_ms']:.2f}ms "
                   f"(max: {stats['render_time_max_ms']:.2f}ms)")


# Global instances (created per-page in actual use)
_global_render_cache = RenderCache()
_global_layout_cache = LayoutCache()
_global_perf_monitor = PerformanceMonitor()


def get_render_cache() -> RenderCache:
    """Get global render cache instance."""
    return _global_render_cache


def get_layout_cache() -> LayoutCache:
    """Get global layout cache instance."""
    return _global_layout_cache


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    return _global_perf_monitor
