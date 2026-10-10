"""Thread-safe utilities and base classes for Saturn framework.

This module provides thread-safe wrappers and utilities to eliminate
data races in the Control animation system and shared caches.
"""
from __future__ import annotations

import copy
import threading
from typing import Any, Callable, TypeVar, Generic

T = TypeVar('T')


class ThreadSafeDict(Generic[T]):
    """Thread-safe dictionary wrapper with RLock protection.
    
    Used for animation overrides, font caches, and other shared state.
    """
    
    def __init__(self):
        self._dict: dict[Any, T] = {}
        self._lock = threading.RLock()
    
    def get(self, key: Any, default: T | None = None) -> T | None:
        """Thread-safe get with optional deep copy."""
        with self._lock:
            value = self._dict.get(key, default)
            # Deep copy to prevent external modification of cached values
            return copy.deepcopy(value) if value is not None else default
    
    def set(self, key: Any, value: T) -> None:
        """Thread-safe set with deep copy."""
        with self._lock:
            self._dict[key] = copy.deepcopy(value)
    
    def pop(self, key: Any, default: T | None = None) -> T | None:
        """Thread-safe pop."""
        with self._lock:
            return self._dict.pop(key, default)
    
    def clear(self) -> None:
        """Thread-safe clear."""
        with self._lock:
            self._dict.clear()
    
    def __contains__(self, key: Any) -> bool:
        """Thread-safe membership test."""
        with self._lock:
            return key in self._dict
    
    def __len__(self) -> int:
        """Thread-safe length."""
        with self._lock:
            return len(self._dict)
    
    def items(self):
        """Thread-safe iteration over items (returns copy)."""
        with self._lock:
            return list(self._dict.items())
    
    def keys(self):
        """Thread-safe iteration over keys (returns copy)."""
        with self._lock:
            return list(self._dict.keys())
    
    def values(self):
        """Thread-safe iteration over values (returns copy)."""
        with self._lock:
            return list(self._dict.values())


class ThreadSafeValue(Generic[T]):
    """Thread-safe wrapper for a single value.
    
    Used for global configuration like theme_dark, default_font_family.
    """
    
    def __init__(self, initial: T):
        self._value = initial
        self._lock = threading.RLock()
    
    def get(self) -> T:
        """Thread-safe get."""
        with self._lock:
            return copy.deepcopy(self._value)
    
    def set(self, value: T) -> None:
        """Thread-safe set."""
        with self._lock:
            self._value = copy.deepcopy(value)
    
    def update(self, func: Callable[[T], T]) -> T:
        """Thread-safe update with function.
        
        Example:
            value.update(lambda x: x + 1)
        """
        with self._lock:
            self._value = func(self._value)
            return copy.deepcopy(self._value)


class LRUCache(Generic[T]):
    """Thread-safe LRU cache with size limit.
    
    Used for text rendering, texture caching, etc.
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache: dict[Any, T] = {}
        self._access_order: list[Any] = []
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: Any) -> T | None:
        """Get value and update LRU order."""
        with self._lock:
            if key in self._cache:
                self._hits += 1
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            self._misses += 1
            return None
    
    def put(self, key: Any, value: T) -> None:
        """Put value and evict LRU if needed."""
        with self._lock:
            if key in self._cache:
                # Update existing
                self._access_order.remove(key)
            elif len(self._cache) >= self._max_size:
                # Evict least recently used
                evict_key = self._access_order.pop(0)
                del self._cache[evict_key]
            
            self._cache[key] = value
            self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }


class AtomicCounter:
    """Thread-safe counter for IDs, versions, etc."""
    
    def __init__(self, initial: int = 0):
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self) -> int:
        """Increment and return new value."""
        with self._lock:
            self._value += 1
            return self._value
    
    def get(self) -> int:
        """Get current value."""
        with self._lock:
            return self._value
    
    def set(self, value: int) -> None:
        """Set value."""
        with self._lock:
            self._value = value


# Singleton instances for framework-wide use
_layout_version_counter = AtomicCounter()


def next_layout_version() -> int:
    """Get next global layout version for incremental layout."""
    return _layout_version_counter.increment()
