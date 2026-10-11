"""Detect DLLs injected into the process by third-party tools.

Overlay tools (GamePP, RTSS, ...) inject a hook DLL into any process that
shows a GPU-rendered foreground window, and some of them terminate the host
when their own setup fails. The watchdog snapshots the loaded modules of the
running process and fires `page.on_foreign_module` for every new module that
appears outside the interpreter, venv and Windows directories, so a
mysterious flash-exit becomes a diagnosable event.

Detection only — an injected DLL that decides to kill the process cannot be
stopped from user code.
"""
from __future__ import annotations

import os
import sys
import threading

from .platform import get_platform

# Poll interval: overlay injectors usually strike within a second of the
# window taking focus, so one second still fires the event before the host
# dies (GamePP kills ~2-3s after injection).
POLL_SECONDS = 1.0

# Module paths that may legitimately appear at any time: OS components,
# the interpreter and anything installed in the environment. Anything else
# that shows up at runtime is reported.
_KNOWN_OVERLAY = {
    "gpp64.dll": "GamePP (游戏加加)",
    "gpp32.dll": "GamePP (游戏加加)",
    "rtsshooks64.dll": "RTSS / MSI Afterburner",
    "rtsshooks.dll": "RTSS / MSI Afterburner",
    "fraps64.dll": "Fraps",
    "fraps32.dll": "Fraps",
    "nvspcap64.dll": "NVIDIA ShadowPlay",
    "nvspcap.dll": "NVIDIA ShadowPlay",
}


def allow_prefixes() -> tuple[str, ...]:
    """Path prefixes a legitimate late-loaded module can come from."""
    prefixes = [sys.prefix, sys.base_prefix,
                os.path.dirname(sys.executable)]
    windir = os.environ.get("WINDIR")
    if windir:
        prefixes.append(windir)
    out = []
    for prefix in prefixes:
        if prefix:
            out.append(os.path.abspath(prefix).lower().rstrip("\\/") + os.sep)
    return tuple(out)


def _allowed(path: str, prefixes: tuple[str, ...]) -> bool:
    low = path.lower()
    return low.startswith(prefixes)


def classify(path: str, prefixes: tuple[str, ...]) -> tuple[bool, str | None]:
    """Return (is_foreign, overlay_tool_name_or_None) for a module path."""
    if _allowed(path, prefixes):
        return False, None
    tool = _KNOWN_OVERLAY.get(os.path.basename(path).lower())
    return True, tool


def snapshot_modules() -> list[str]:
    """Loaded module paths of the current process ([] if unsupported)."""
    return get_platform().snapshot_modules()


def start(page, stop: threading.Event) -> threading.Thread | None:
    """Run the watchdog until `stop` is set; None when scanning is unsupported."""
    if not get_platform().supports("module_watch"):
        return None
    prefixes = allow_prefixes()
    baseline = snapshot_modules()
    seen_foreign: set[str] = set()

    def watch():
        from .event import ForeignModuleEvent
        current = set(baseline)
        while not stop.wait(POLL_SECONDS):
            new = snapshot_modules()
            if not new:
                continue
            for path in new:
                if path in current:
                    continue
                current.add(path)
                foreign, tool = classify(path, prefixes)
                if not foreign or path in seen_foreign:
                    continue
                seen_foreign.add(path)
                print(f"[saturn] Foreign DLL injected into this process: {path}"
                      + (f" (known overlay injector: {tool})" if tool else "")
                      + "\n[saturn] If the window dies when focused, exclude "
                        "this app from that overlay tool.",
                      file=sys.stderr)
                if page.on_foreign_module:
                    page._dispatch(page.on_foreign_module, ForeignModuleEvent(
                        "foreign_module", page, path=path, tool=tool or ""))

    thread = threading.Thread(target=watch, daemon=True, name="saturn-modwatch")
    thread.start()
    return thread
