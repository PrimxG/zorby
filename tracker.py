"""Window title helpers using win32gui."""

import win32gui

from config import get_entertainment_apps, get_work_apps


def get_active_window() -> str:
    """Return the active window title as a string, or empty string on failure.

    Uses win32gui.GetForegroundWindow() to get the current foreground window
    handle, then win32gui.GetWindowText() to read its title.

    Returns:
        The window title string, or "" if no window is active or an error occurs.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            # No foreground window (e.g. desktop has focus or screen is locked)
            return ""
        title = win32gui.GetWindowText(hwnd)
        if not title:
            # Window exists but has no title (e.g. background system process)
            return ""
        return title
    except Exception:
        return ""


def classify_activity(title: str) -> str:
    """Classify activity from a window title (case-insensitive)."""
    if not title or not title.strip():
        return "idle"

    t = title.lower()

    work_kw = get_work_apps()
    if any(k in t for k in work_kw):
        return "work"

    ent_kw = get_entertainment_apps()
    if any(k in t for k in ent_kw):
        return "entertainment"

    return "other"


if __name__ == "__main__":
    title = get_active_window()
    print("title:", repr(title))
    print("activity:", classify_activity(title))
