"""App classifier — maps an app name to a category using keyword substring matching."""

from config import get_entertainment_keywords, get_games, get_work_keywords

# ---------------------------------------------------------------------------
# Category labels
# ---------------------------------------------------------------------------
CATEGORY_GAME = "Game 🎮"
CATEGORY_WORK = "Work 🧠"
CATEGORY_ENTERTAINMENT = "Entertainment 🍿"
CATEGORY_UNKNOWN = "Unknown ❓"


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------

def classify_app(app_name: str) -> str:
    """Classify *app_name* into a category using substring matching.

    Priority order: Game → Work → Entertainment → Unknown.

    Args:
        app_name: The window title or application name to classify.

    Returns:
        One of the CATEGORY_* constants defined in this module.
    """
    name = app_name.lower()

    if _matches_any(name, get_games()):
        return CATEGORY_GAME

    if _matches_any(name, get_work_keywords()):
        return CATEGORY_WORK

    if _matches_any(name, get_entertainment_keywords()):
        return CATEGORY_ENTERTAINMENT

    return CATEGORY_UNKNOWN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Return True if *text* contains at least one keyword as a substring."""
    return any(kw in text for kw in keywords)


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        "Visual Studio Code",
        "YouTube - Mozilla Firefox",
        "Minecraft Launcher",
        "Notepad",
        "LeetCode - Chrome",
        "Steam",
        "Netflix",
        "GeeksforGeeks",
    ]
    print(f"{'App':<35} {'Category'}")
    print("-" * 55)
    for app in samples:
        print(f"{app:<35} {classify_app(app)}")
