"""Window title helpers using pygetwindow."""

import pygetwindow as gw


def get_active_window() -> str:
    """Return the active window title in lowercase, or empty string on failure."""
    try:
        win = gw.getActiveWindow()
        if win is None:
            return ""
        title = getattr(win, "title", None)
        if not title or not isinstance(title, str):
            return ""
        return title.lower()
    except Exception:
        return ""


def classify_activity(title: str) -> str:
    """Classify activity from a window title (case-insensitive)."""
    if not title or not title.strip():
        return "idle"

    t = title.lower()

    work_kw = ("code", "pycharm", "intellij", "vscode")
    if any(k in t for k in work_kw):
        return "work"

    ent_kw = ("youtube", "netflix", "prime")
    if any(k in t for k in ent_kw):
        return "entertainment"

    return "other"


if __name__ == "__main__":
    title = get_active_window()
    print("title:", repr(title))
    print("activity:", classify_activity(title))
