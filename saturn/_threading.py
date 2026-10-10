"""Threading model and lifecycle documentation for Saturn.

This module documents Saturn's threading model and provides thread-safe primitives.
All threading usage in Saturn should follow these patterns.

## Thread Ownership Model

Saturn uses the following daemon threads:

1. **saturn-async** (app.py)
   - Owner: App instance
   - Lifecycle: Created in App.__init__, dies with process
   - Purpose: asyncio event loop for async event handlers
   - Cleanup: None (daemon thread)

2. **saturn-main** (app.py)
   - Owner: App instance
   - Lifecycle: Created in App.start(), dies with process
   - Purpose: Run main() entry point off UI thread
   - Cleanup: None (daemon thread)

3. **saturn-window** (app.py run_thread)
   - Owner: Caller
   - Lifecycle: Created in run_thread(), dies with process
   - Purpose: Run entire window on background thread
   - Cleanup: None (daemon thread)

4. **saturn-font-download** (text.py)
   - Owner: Font download system
   - Lifecycle: One per font URL download, dies when complete or on process exit
   - Purpose: Download fonts without blocking UI
   - Cleanup: None (daemon thread, in-progress downloads are lost)

5. **saturn-font-{wnum}** (text.py)
   - Owner: Font instancing system
   - Lifecycle: One per font weight instance, dies when complete or on process exit
   - Purpose: Instance variable fonts in background
   - Cleanup: None (daemon thread, in-progress instances are lost)

6. **saturn-modwatch** (_modwatch.py)
   - Owner: App instance
   - Lifecycle: Created if hot reload enabled, dies with process
   - Purpose: Watch for Python module changes
   - Cleanup: Via stop Event

## Design Rationale

All threads are marked daemon=True because:
- Saturn windows are short-lived desktop applications
- Process exit is an acceptable cleanup mechanism
- No critical data is lost if threads are terminated
- Simplifies shutdown logic (no join() needed)

## Known Issues

- Font downloads/instancing interrupted on shutdown are not retried
- No graceful thread shutdown on App.close()
- Background work cannot be awaited before process exit

## Thread-Safe Primitives

Use these for cross-thread communication and state management.
"""
from __future__ import annotations

import threading
from typing import TypeVar, Generic

T = TypeVar('T')


class ThreadSafeDict(Generic[T]):
    """Thread-safe dictionary wrapper with RLock protection.

    Use this instead of plain dict when accessed from multiple threads.
    """

    def __init__(self):
        self._data: dict[str, T] = {}
        self._lock = threading.RLock()

    def get(self, key: str, default: T | None = None) -> T | None:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._data[key] = value

    def pop(self, key: str, default: T | None = None) -> T | None:
        with self._lock:
            return self._data.pop(key, default)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def keys(self):
        with self._lock:
            return list(self._data.keys())

    def values(self):
        with self._lock:
            return list(self._data.values())

    def items(self):
        with self._lock:
            return list(self._data.items())


# Global lock registry for debugging deadlocks
_lock_registry: dict[str, threading.RLock] = {}


def register_lock(name: str, lock: threading.RLock) -> None:
    """Register a named lock for debugging purposes.

    Use this to track lock acquisition order and detect potential deadlocks.
    """
    _lock_registry[name] = lock


def get_locks() -> dict[str, threading.RLock]:
    """Get all registered locks (for debugging)."""
    return dict(_lock_registry)
