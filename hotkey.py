"""Global hotkey registration for Zorby.

Registers Ctrl + Shift + Z as a non-blocking global hotkey.
The listener runs on a background thread managed by the `keyboard`
library, so it never blocks the main process or the Qt event loop.

Public API
----------
register_hotkeys(on_activate)  Call once at startup to activate all hotkeys.
unregister_hotkeys()           Call on shutdown to cleanly remove all hotkeys.

Adding new hotkeys
------------------
Drop a new entry into _HOTKEYS below — no other changes needed.
"""

from typing import Callable

import keyboard

# ---------------------------------------------------------------------------
# Hotkey definitions
# ---------------------------------------------------------------------------
# Each entry: (hotkey_string, callback)
# The callback receives no arguments.

def _on_zorby_activate() -> None:
    print("Zorby Activated 🚀")


_HOTKEYS: list[tuple[str, object]] = [
    ("ctrl+shift+z", _on_zorby_activate),
]

# Tracks registered hotkey handles so they can be cleanly removed.
#
# Type note: keyboard.add_hotkey() returns a zero-argument closure (remove_)
# that the library uses internally as a removal token.  The `keyboard` package
# ships no type stubs and does not export a named type for this handle.
# Inspecting the source confirms the return type is always `Callable[[], None]`
# — passed directly to keyboard.remove_hotkey() for cleanup.
_handles: list[Callable[[], None]] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_hotkeys(on_activate=None) -> None:
    """Register all global hotkeys. Safe to call multiple times.

    Args:
        on_activate: Optional zero-argument callable to invoke when
                     Ctrl+Shift+Z is pressed.  If omitted the default
                     action is a console print (useful for standalone
                     testing via ``python hotkey.py``).

                     IMPORTANT: the ``keyboard`` library fires this
                     callback on its own background thread.  If the
                     callback touches Qt widgets it MUST go through a
                     Qt signal/slot (queued connection) rather than
                     calling widget methods directly.
    """
    if _handles:
        return  # already registered

    # Build the hotkey table, substituting the caller-supplied action.
    hotkeys = list(_HOTKEYS)
    if on_activate is not None:
        hotkeys = [
            (combo, on_activate if combo == "ctrl+shift+z" else cb)
            for combo, cb in hotkeys
        ]

    for combo, callback in hotkeys:
        handle = keyboard.add_hotkey(combo, callback, suppress=False)
        _handles.append(handle)
        print(f"[hotkey] Registered: {combo}")


def unregister_hotkeys() -> None:
    """Remove all registered hotkeys (call on app shutdown)."""
    for handle in _handles:
        try:
            keyboard.remove_hotkey(handle)
        except Exception:
            pass
    _handles.clear()
    print("[hotkey] All hotkeys unregistered.")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    register_hotkeys()   # uses default print action
    print("Listening for Ctrl+Shift+Z … (Ctrl+C to quit)")

    try:
        while True:
            time.sleep(0.1)   # yield CPU; keyboard listener runs on its own thread
    except KeyboardInterrupt:
        print("\nExiting.")
        unregister_hotkeys()
