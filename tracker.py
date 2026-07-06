"""Window title helpers using win32gui."""

import win32gui


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


if __name__ == "__main__":
    from classifier import classify_app

    title = get_active_window()
    print("title   :", repr(title))
    print("category:", classify_app(title))
