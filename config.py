"""Configuration loader for app classification keywords.

Caching
-------
_load_config() uses mtime-based caching: it stats config.json on every call
(cheap) and only re-reads/re-parses the file when the mtime has changed since
the last successful load.  Live edits are still detected on the very next call
after the file is saved.

Schema validation
-----------------
Each required key is validated individually:
  - Must be present in the JSON object.
  - Must be a non-empty list.
  - Every element of the list must be a string.
If any condition fails the specific key is logged with a clear warning and
replaced with its built-in default, while all other valid keys are kept as-is.
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_DEFAULT_CONFIG: dict[str, list[str]] = {
    "work_keywords": ["code", "pycharm", "intellij", "vscode", "leetcode", "udemy", "geeksforgeeks"],
    "entertainment_keywords": ["youtube", "netflix", "prime", "spotify", "discord"],
    "games": ["steam", "minecraft", "roblox", "fortnite", "valorant", "csgo", "gta", "chess"],
}

_REQUIRED_KEYS = tuple(_DEFAULT_CONFIG.keys())


# ---------------------------------------------------------------------------
# Per-key schema validation
# ---------------------------------------------------------------------------

def _validate_and_repair(data: dict) -> dict:
    """Validate *data* against the required schema, repairing bad keys in-place.

    Rules checked for each required key
    ------------------------------------
    1. Key must be present in the dict.
    2. Value must be a ``list``.
    3. List must be non-empty.
    4. Every element of the list must be a ``str``.

    For any key that fails one or more rules:
    * A ``[config] WARNING`` line is printed naming the key and the reason.
    * The key is replaced with its built-in default value.

    Valid keys are left untouched.  The repaired dict is returned so the
    caller can cache it normally.
    """
    for key in _REQUIRED_KEYS:
        default = _DEFAULT_CONFIG[key]
        value   = data.get(key)

        if value is None:
            print(f"[config] WARNING: required key '{key}' is missing — "
                  f"using default: {default}")
            data[key] = list(default)
            continue

        if not isinstance(value, list):
            print(f"[config] WARNING: '{key}' must be a list, "
                  f"got {type(value).__name__!r} — using default: {default}")
            data[key] = list(default)
            continue

        if len(value) == 0:
            print(f"[config] WARNING: '{key}' is an empty list — "
                  f"using default: {default}")
            data[key] = list(default)
            continue

        bad_items = [v for v in value if not isinstance(v, str)]
        if bad_items:
            print(f"[config] WARNING: '{key}' contains non-string items "
                  f"{bad_items!r} — using default: {default}")
            data[key] = list(default)
            continue

    return data

# ---------------------------------------------------------------------------
# Module-level mtime cache
# ---------------------------------------------------------------------------

# Last successfully parsed config dict (or None before the first load).
_cached_config: dict | None = None

# os.path.getmtime() value at the time _cached_config was populated.
_cached_mtime: float | None = None


def _load_config() -> dict:
    """Return the parsed config.json, using an mtime cache to avoid redundant I/O.

    Behaviour:
    * On every call, ``os.path.getmtime()`` is checked (a single stat syscall).
    * If the mtime matches the cached value the cached dict is returned immediately
      without opening or parsing the file.
    * If the mtime has changed (or this is the first call) the file is re-read and
      re-parsed, the cache is updated, and the new dict is returned.
    * If the file is missing or malformed the function falls back to the built-in
      defaults and leaves the cache unchanged so the next call tries again.
    """
    global _cached_config, _cached_mtime

    # --- 1. Check mtime (cheap stat) -----------------------------------------
    try:
        current_mtime = os.path.getmtime(_CONFIG_PATH)
    except OSError:
        # File does not exist; fall back to defaults without touching the cache.
        if _cached_config is None:
            print(f"[config] config.json not found at {_CONFIG_PATH}. Using defaults.")
        return _cached_config if _cached_config is not None else dict(_DEFAULT_CONFIG)

    # --- 2. Return cached result if the file has not changed -----------------
    if _cached_config is not None and current_mtime == _cached_mtime:
        return _cached_config

    # --- 3. File is new or modified — re-read and re-parse -------------------
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(
                f"Top-level JSON value must be an object, got {type(data).__name__!r}"
            )
        # Validate and repair per-key; does not raise — bad keys get defaults.
        data = _validate_and_repair(data)
        # Cache the validated (and possibly repaired) result.
        _cached_config = data
        _cached_mtime  = current_mtime
        return _cached_config
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"[config] config.json is invalid ({exc}). Using defaults.")
        # Leave the cache unchanged; return a fresh copy of the defaults.
        return _cached_config if _cached_config is not None else dict(_DEFAULT_CONFIG)


def _get_keywords(key: str) -> tuple[str, ...]:
    """Return keywords for *key*, using the mtime-cached config.

    Live edits to config.json are still picked up on the very next call after
    the file is saved (the mtime check in _load_config() costs one stat syscall).
    """
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
