"""Global hotkey registration for Zorby.

Registers Ctrl + Shift + Z as a non-blocking global hotkey.
The listener runs on a background thread managed by the `keyboard`
library, so it never blocks the main process or the Qt event loop.

Public API
----------
register_hotkeys()   Call once at startup to activate all hotkeys.
unregister_hotkeys() Call on shutdown to cleanly remove all hotkeys.

Adding new hotkeys
------------------
Drop a new entry into _HOTKEYS below — no other changes needed.
"""

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
_handles: list[keyboard.KeyboardEvent] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_hotkeys() -> None:
    """Register all global hotkeys. Safe to call multiple times."""
    if _handles:
        return  # already registered

    for combo, callback in _HOTKEYS:
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

    register_hotkeys()
    print("Listening for Ctrl+Shift+Z … (Ctrl+C to quit)")

    try:
        while True:
            time.sleep(0.1)   # yield CPU; keyboard listener runs on its own thread
    except KeyboardInterrupt:
        print("\nExiting.")
        unregister_hotkeys()
