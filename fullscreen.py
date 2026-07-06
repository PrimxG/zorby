"""Fullscreen detection and gaming-session classification.

Public API
----------
is_fullscreen()          -> bool   Detects if the foreground window covers the screen.
is_gaming_session()      -> bool   True when the app is a Game or the window is fullscreen.
get_fullscreen_app_name()-> str    Title of the fullscreen window, or "" if none.

Detection strategy (is_fullscreen)
-----------------------------------
A window is classified as *true* fullscreen only when **both** conditions hold:

  1. Style flags: the window must NOT carry WS_CAPTION or WS_THICKFRAME.
     Ordinary maximized windows (VS Code, Chrome, File Explorer …) keep those
     flags; borderless fullscreen apps drop them entirely.

  2. Geometry: the window's bounding rect must exactly match the *monitor it
     lives on* (via MonitorFromWindow + GetMonitorInfo), not just the primary
     screen, so fullscreen apps on secondary monitors are detected correctly.
"""

import ctypes
import ctypes.wintypes
import win32gui
import win32con
import win32api

from classifier import CATEGORY_GAME, classify_app


# ---------------------------------------------------------------------------
# Win32 constants used for style-flag inspection
# ---------------------------------------------------------------------------

# Window styles that are present on ordinary maximized windows but absent on
# true borderless-fullscreen windows.
_WS_CAPTION    = win32con.WS_CAPTION      # title bar (includes WS_BORDER)
_WS_THICKFRAME = win32con.WS_THICKFRAME   # resizable border
_GWL_STYLE     = win32con.GWL_STYLE

# MonitorFromWindow flags
_MONITOR_DEFAULTTONEAREST = 0x00000002


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
# Internal: per-monitor rect via MonitorFromWindow + GetMonitorInfo
# ---------------------------------------------------------------------------

def _get_monitor_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Return the bounding rect of the monitor that contains *hwnd*.

    Uses MonitorFromWindow so the result is correct for any monitor in a
    multi-monitor setup, not just the primary screen.

    Returns (left, top, right, bottom) in virtual-desktop coordinates, or
    None on failure.
    """
    try:
        hmonitor = win32api.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
        if not hmonitor:
            return None
        info = win32api.GetMonitorInfo(hmonitor)
        # 'Monitor' is the full monitor rect; 'Work' excludes the taskbar.
        # For fullscreen detection we want the *full* monitor rect.
        mon_rect = info["Monitor"]  # (left, top, right, bottom)
        return tuple(mon_rect)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Internal: window-style inspection
# ---------------------------------------------------------------------------

def _has_window_chrome(hwnd: int) -> bool:
    """Return True if *hwnd* still has a title-bar or resizable border.

    Maximized windows (VS Code, Chrome, File Explorer …) always keep
    WS_CAPTION and WS_THICKFRAME; true borderless fullscreen apps drop them.
    """
    try:
        style = win32gui.GetWindowLong(hwnd, _GWL_STYLE)
        return bool(style & (_WS_CAPTION | _WS_THICKFRAME))
    except Exception:
        # If we can't read the style, assume it has chrome (safe default).
        return True


# ---------------------------------------------------------------------------
# Public: fullscreen detection
# ---------------------------------------------------------------------------

def is_fullscreen() -> bool:
    """Detect whether the current foreground window is true borderless fullscreen.

    Strategy (both conditions must hold):

      1. **Style flags** — the window must NOT carry WS_CAPTION or WS_THICKFRAME.
         Ordinary maximized windows keep these flags; borderless fullscreen apps
         (games, video players, slide-show renderers …) drop them entirely.

      2. **Geometry** — the window's bounding rect must exactly match the rect of
         the monitor it lives on (via MonitorFromWindow + GetMonitorInfo).  This
         works correctly on every monitor in a multi-monitor setup, not just the
         primary screen.

    Returns:
        True  — foreground window is true borderless fullscreen.
        False — no foreground window, window has title-bar/border chrome, or the
                window does not cover its monitor completely.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False

        # --- 1. Style check: bail out if the window still has normal chrome ---
        if _has_window_chrome(hwnd):
            return False

        # --- 2. Geometry check against the window's actual monitor -----------
        win_rect = _get_window_rect(hwnd)
        if win_rect is None:
            return False

        mon_rect = _get_monitor_rect(hwnd)
        if mon_rect is None:
            return False

        return win_rect == mon_rect

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
