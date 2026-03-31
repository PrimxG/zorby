"""Configuration loader for app classification keywords."""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_DEFAULT_CONFIG: dict[str, list[str]] = {
    "work_keywords": ["code", "pycharm", "intellij", "vscode", "leetcode", "udemy", "geeksforgeeks"],
    "entertainment_keywords": ["youtube", "netflix", "prime", "spotify", "discord"],
    "games": ["steam", "minecraft", "roblox", "fortnite", "valorant", "csgo", "gta", "chess"],
}

_REQUIRED_KEYS = tuple(_DEFAULT_CONFIG.keys())


def _load_config() -> dict:
    """Load config.json, falling back to defaults if the file is missing or invalid."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Validate all required keys exist and are lists
        for key in _REQUIRED_KEYS:
            if key not in data or not isinstance(data[key], list):
                raise ValueError(f"Missing or invalid key: '{key}'")
        return data
    except FileNotFoundError:
        print(f"[config] config.json not found at {_CONFIG_PATH}. Using defaults.")
        return dict(_DEFAULT_CONFIG)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"[config] config.json is invalid ({exc}). Using defaults.")
        return dict(_DEFAULT_CONFIG)


def _get_keywords(key: str) -> tuple[str, ...]:
    """Re-read config.json on every call so live edits are always picked up."""
    config = _load_config()
    return tuple(str(k).lower() for k in config.get(key, _DEFAULT_CONFIG[key]))


def get_work_keywords() -> tuple[str, ...]:
    """Return work-app keywords."""
    return _get_keywords("work_keywords")


def get_entertainment_keywords() -> tuple[str, ...]:
    """Return entertainment-app keywords."""
    return _get_keywords("entertainment_keywords")


def get_games() -> tuple[str, ...]:
    """Return game keywords."""
    return _get_keywords("games")


# ---------------------------------------------------------------------------
# Back-compat aliases used by tracker.py
# ---------------------------------------------------------------------------
get_work_apps = get_work_keywords
get_entertainment_apps = get_entertainment_keywords
