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
    if sys.platform == "win32":
        return _snapshot_windows()
    if sys.platform.startswith("linux"):
        return _snapshot_linux()
    return []


def _snapshot_windows() -> list[str]:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    # 64-bit pseudo-handle (-1) truncates without explicit signatures.
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    psapi.GetModuleFileNameExW.argtypes = [
        wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD

    handle = kernel32.GetCurrentProcess()
    LIST_MODULES_ALL = 0x03
    size = 256
    for _ in range(4):
        buf = (wintypes.HMODULE * size)()
        needed = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(handle, buf, ctypes.sizeof(buf),
                                          ctypes.byref(needed), LIST_MODULES_ALL):
            return []
        count = needed.value // ctypes.sizeof(wintypes.HMODULE)
        if count <= size:
            out = []
            for i in range(count):
                name = ctypes.create_unicode_buffer(512)
                length = psapi.GetModuleFileNameExW(handle, buf[i], name, 512)
                if length:
                    out.append(name.value.lower())
            return out
        size = count
    return []


def _snapshot_linux() -> list[str]:
    out = []
    try:
        with open("/proc/self/maps", "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                path = line.rstrip("\n").rpartition(" ")[2]
                if path.startswith("/") and ".so" in os.path.basename(path):
                    out.append(os.path.realpath(path).lower())
    except OSError:
        return []
    return out


def start(page, stop: threading.Event) -> threading.Thread | None:
    """Run the watchdog until `stop` is set; None when scanning is unsupported."""
    if not (sys.platform == "win32" or sys.platform.startswith("linux")):
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
