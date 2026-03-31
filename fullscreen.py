"""Fullscreen detection and gaming-session classification.

Public API
----------
is_fullscreen()          -> bool   Detects if the foreground window covers the screen.
is_gaming_session()      -> bool   True when the app is a Game or the window is fullscreen.
get_fullscreen_app_name()-> str    Title of the fullscreen window, or "" if none.
"""

import ctypes
import ctypes.wintypes
import win32gui

from classifier import CATEGORY_GAME, classify_app


# ---------------------------------------------------------------------------
# Internal: screen resolution via ctypes
# ---------------------------------------------------------------------------

def _get_screen_resolution() -> tuple[int, int]:
    """Return the primary monitor's resolution as (width, height).

    Uses SM_CXSCREEN / SM_CYSCREEN system metrics which always reflect the
    physical screen size regardless of DPI scaling mode.
    """
    user32 = ctypes.windll.user32
    width  = user32.GetSystemMetrics(0)   # SM_CXSCREEN
    height = user32.GetSystemMetrics(1)   # SM_CYSCREEN
    return width, height


# ---------------------------------------------------------------------------
# Internal: window rect via win32gui
# ---------------------------------------------------------------------------

def _get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Return (left, top, right, bottom) for *hwnd*, or None on failure."""
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public: fullscreen detection
# ---------------------------------------------------------------------------

def is_fullscreen() -> bool:
    """Detect whether the current foreground window covers the entire screen.

    Strategy: compare the window's bounding rect (via win32gui.GetWindowRect)
    against the primary monitor's resolution (via ctypes system metrics).
    A window is considered fullscreen when its rect exactly matches the screen
    dimensions starting from (0, 0).

    Returns:
        True  — the foreground window spans the full screen.
        False — no foreground window, or the window is smaller than the screen.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False

        rect = _get_window_rect(hwnd)
        if rect is None:
            return False

        left, top, right, bottom = rect
        screen_w, screen_h = _get_screen_resolution()

        win_w = right  - left
        win_h = bottom - top

        return left == 0 and top == 0 and win_w == screen_w and win_h == screen_h

    except Exception:
        return False


def get_fullscreen_app_name() -> str:
    """Return the title of the foreground window if it is fullscreen, else ''.

    Useful for logging which application triggered a fullscreen state.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not is_fullscreen():
            return ""
        return win32gui.GetWindowText(hwnd) or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public: combined gaming-session check
# ---------------------------------------------------------------------------

def is_gaming_session(app_title: str = "") -> bool:
    """Return True if the current session is a gaming or immersive session.

    A session qualifies when:
      1. The classified category is CATEGORY_GAME ("Game 🎮"), OR
      2. The foreground window is running fullscreen.

    Args:
        app_title: The window title to classify. If empty the function still
                   checks the fullscreen flag using the live foreground window.

    Returns:
        True if the session should be treated as a game/immersive session.
    """
    is_game = bool(app_title) and classify_app(app_title) == CATEGORY_GAME
    return is_game or is_fullscreen()


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from tracker import get_active_window

    title      = get_active_window()
    fullscreen = is_fullscreen()
    gaming     = is_gaming_session(title)
    screen_w, screen_h = _get_screen_resolution()

    print(f"Active window  : {title!r}")
    print(f"Screen res     : {screen_w} x {screen_h}")
    print(f"Is fullscreen  : {fullscreen}")
    print(f"Is gaming sess : {gaming}")
    if fullscreen:
        print(f"Fullscreen app : {get_fullscreen_app_name()!r}")
