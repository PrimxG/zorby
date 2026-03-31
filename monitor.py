"""Zorby visibility monitor.

Continuously polls the active window once per second and decides whether
Zorby should be shown or hidden.

    HIDE ZORBY  — foreground window is fullscreen OR classified as a game.
    SHOW ZORBY  — everything else.

Efficiency notes
----------------
- time.sleep(1) releases the GIL and yields CPU; no busy-wait.
- State is only printed when it *changes*, avoiding console spam.
- win32gui / ctypes calls are lightweight (no COM, no heavy Win32 subsystems).

Usage
-----
    python monitor.py          # run directly
    from monitor import run_monitor, should_hide_zorby   # import API
"""

import time

from classifier import classify_app, CATEGORY_GAME
from fullscreen import is_fullscreen
from tracker import get_active_window

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLL_INTERVAL: float = 1.0      # seconds between each check
MSG_HIDE = "HIDE ZORBY 🙈"
MSG_SHOW = "SHOW ZORBY 🐾"
_SENTINEL = object()             # unique "no previous state" marker


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def should_hide_zorby(title: str) -> bool:
    """Return True if Zorby should be hidden for the given window *title*.

    Hides when:
      - The app is classified as a game  (keyword match via classifier), OR
      - The foreground window is fullscreen (size matches screen resolution).

    Args:
        title: Active window title string (may be empty).

    Returns:
        True  → hide Zorby.
        False → show Zorby.
    """
    if not title:
        return False                       # no active window → keep Zorby visible

    is_game       = classify_app(title) == CATEGORY_GAME
    fullscreen    = is_fullscreen()

    return is_game or fullscreen


# ---------------------------------------------------------------------------
# Main monitoring loop
# ---------------------------------------------------------------------------

def run_monitor(interval: float = POLL_INTERVAL) -> None:
    """Run the Zorby visibility monitor loop indefinitely.

    Polls every *interval* seconds.  Only prints a message when the
    hide/show state changes to avoid log spam.

    Exits cleanly on Ctrl-C.

    Args:
        interval: Seconds between polls (default 1.0).
    """
    print(f"[monitor] Starting Zorby monitor (poll interval: {interval}s) — Ctrl-C to quit\n")

    last_state = _SENTINEL

    try:
        while True:
            title  = get_active_window()
            hide   = should_hide_zorby(title)

            if hide is not last_state:          # state changed → print update
                label = title or "(no active window)"
                if hide:
                    print(f"[monitor] {MSG_HIDE}  ← {label!r}")
                else:
                    print(f"[monitor] {MSG_SHOW}  ← {label!r}")
                last_state = hide

            time.sleep(interval)               # yield CPU; no busy-wait

    except KeyboardInterrupt:
        print("\n[monitor] Stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_monitor()
