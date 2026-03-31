"""engine.py — ZorbyEngine: central orchestration for the Zorby system.

This module is the single source of truth for all background monitoring.
Every other entry point (main.py Qt UI, zorby.py CLI) delegates to this.

Architecture
------------
                    ┌─────────────────────────────────────┐
                    │            ZorbyEngine               │
                    │                                      │
  config.json ──▶  │  ┌──────────┐   ┌────────────────┐  │
                   │  │AppStatus │   │  _MonitorLoop  │  │
  classifier.py ──▶│  │(snapshot)│◀──│  (daemon thd)  │  │
  tracker.py ───▶  │  └──────────┘   └────────────────┘  │
  fullscreen.py ──▶│                                      │
  audio.py ──────▶ │  ┌──────────────────────────────┐    │
  media_control ──▶│  │  Event callbacks (listeners)  │    │
  hotkey.py ─────▶ │  │  on_game_enter / on_game_exit │    │
                    │  │  on_status_change             │    │
                    │  └──────────────────────────────┘    │
                    └─────────────────────────────────────┘

Public API
----------
  ZorbyEngine(interval, auto_pause_media, verbose)
    .start()                 — register hotkeys, begin monitoring thread
    .stop()                  — clean shutdown
    .status                  — latest AppStatus snapshot (read-only)
    .on_game_enter(fn)       — fn() called once when entering game/fullscreen
    .on_game_exit(fn)        — fn() called once when leaving game/fullscreen
    .on_status_change(fn)    — fn(AppStatus) called on every meaningful change
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

# ── leaf-level subsystems (no cross-dependencies) ─────────────────────────
from audio         import is_audio_playing
from classifier    import classify_app, CATEGORY_GAME, CATEGORY_WORK, CATEGORY_ENTERTAINMENT
from config        import get_work_keywords, get_entertainment_keywords, get_games
from fullscreen    import is_fullscreen, _get_screen_resolution
from hotkey        import register_hotkeys, unregister_hotkeys
from media_control import pause_media
from tracker       import get_active_window


# ══════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════

DEFAULT_INTERVAL: float = 1.0       # seconds between polls

# UI-mode strings (used by Qt UI and music selector)
MODE_WORK          = "work"
MODE_ENTERTAINMENT = "entertainment"
MODE_GAME          = "game"
MODE_IDLE          = "idle"
MODE_OTHER         = "other"

# Maps classifier categories → UI modes
_CATEGORY_TO_MODE: dict[str, str] = {
    CATEGORY_GAME:          MODE_GAME,
    CATEGORY_WORK:          MODE_WORK,
    CATEGORY_ENTERTAINMENT: MODE_ENTERTAINMENT,
}


# ══════════════════════════════════════════════════════════════════════════
# AppStatus — immutable per-tick snapshot
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AppStatus:
    """Immutable snapshot of the system state at a single poll tick.

    Passed to all on_status_change listeners so they can react without
    touching mutable engine internals.
    """
    title:         str   # active window title (may be "")
    category:      str   # CATEGORY_* constant from classifier
    mode:          str   # MODE_* constant (work/entertainment/game/idle/other)
    is_game:       bool  # True if classified as game by keyword
    is_fullscreen: bool  # True if window rect == screen resolution
    should_hide:   bool  # is_game or is_fullscreen
    audio_playing: bool  # True if any WASAPI session has peak > threshold


# ══════════════════════════════════════════════════════════════════════════
# Internal mutable state (not exposed publicly)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class _EngineState:
    """Mutable runtime tracking — internal to ZorbyEngine."""
    # Game / fullscreen cycle
    in_game:      bool = False   # True while game/fullscreen is active
    media_paused: bool = False   # True after pause was sent this cycle

    # Session statistics
    tick_count:  int = 0
    hide_count:  int = 0
    show_count:  int = 0
    media_pause_count: int = 0

    # Last known snapshot (for change detection)
    last_status: AppStatus | None = None


# ══════════════════════════════════════════════════════════════════════════
# ZorbyEngine
# ══════════════════════════════════════════════════════════════════════════

class ZorbyEngine:
    """Central orchestration engine for the Zorby system.

    Manages all background monitoring in a single daemon thread.
    Consumers (Qt UI, CLI, tests) hook in via the callback API.

    Args:
        interval:          Seconds between polls (default 1.0).
        auto_pause_media:  Pause system audio when a game/fullscreen starts
                           (default True). Set False to monitor only.
        verbose:           Print every tick to stdout (default False).
    """

    def __init__(
        self,
        interval:         float = DEFAULT_INTERVAL,
        auto_pause_media: bool  = True,
        verbose:          bool  = False,
    ) -> None:
        self.interval         = interval
        self.auto_pause_media = auto_pause_media
        self.verbose          = verbose

        self._state      = _EngineState()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running    = False

        # Callback registries
        self._on_game_enter:    list[Callable[[], None]]          = []
        self._on_game_exit:     list[Callable[[], None]]          = []
        self._on_status_change: list[Callable[[AppStatus], None]] = []

    # ── latest status (read-only property) ────────────────────────────────

    @property
    def status(self) -> AppStatus | None:
        """Most recent AppStatus snapshot, or None before first tick."""
        return self._state.last_status

    # ── lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background monitoring and register global hotkeys.

        Safe to call multiple times — no-op if already running.
        """
        if self._running:
            return

        register_hotkeys()
        self._stop_event.clear()
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop,
            daemon=True,
            name="ZorbyEngine",
        )
        self._thread.start()
        print("[engine] Started.")
        self._log_config()

    def stop(self) -> None:
        """Stop background monitoring and clean up hotkeys.

        Blocks until the monitor thread exits (max: interval + 1 s).
        """
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        unregister_hotkeys()
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
        print("[engine] Stopped.")
        self._log_summary()

    # ── callback registration ──────────────────────────────────────────────

    def on_game_enter(self, fn: Callable[[], None]) -> None:
        """Register *fn* to be called once when a game/fullscreen session starts."""
        self._on_game_enter.append(fn)

    def on_game_exit(self, fn: Callable[[], None]) -> None:
        """Register *fn* to be called once when a game/fullscreen session ends."""
        self._on_game_exit.append(fn)

    def on_status_change(self, fn: Callable[[AppStatus], None]) -> None:
        """Register *fn* to be called whenever the AppStatus changes meaningfully.

        Receives the new AppStatus snapshot as its only argument.
        """
        self._on_status_change.append(fn)

    # ── internal monitoring loop ───────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                print(f"[engine] Tick error: {exc}")
            # Interruptible sleep — wakes immediately when stop() is called
            self._stop_event.wait(self.interval)

    def _tick(self) -> None:
        # ── 1. Gather raw data ─────────────────────────────────────────────
        title      = get_active_window()
        category   = classify_app(title) if title else ""
        is_game    = category == CATEGORY_GAME
        fullscreen = is_fullscreen()
        hide       = is_game or fullscreen
        audio      = is_audio_playing() if hide else False   # skip if not needed
        mode       = _CATEGORY_TO_MODE.get(category, MODE_IDLE if not title else MODE_OTHER)

        status = AppStatus(
            title=title,
            category=category,
            mode=mode,
            is_game=is_game,
            is_fullscreen=fullscreen,
            should_hide=hide,
            audio_playing=audio,
        )

        self._state.tick_count += 1
        if self.verbose:
            self._log_tick(status)

        # ── 2. Detect changes and fire callbacks ───────────────────────────
        prev = self._state.last_status
        self._state.last_status = status

        # Fire on_status_change if anything meaningful changed
        if prev is None or status != prev:
            self._fire(self._on_status_change, status)

        # ── 3. Game / fullscreen state machine ─────────────────────────────
        if hide:
            self._handle_game_active(status)
        else:
            self._handle_game_inactive()

    def _handle_game_active(self, status: AppStatus) -> None:
        """Called every tick while game/fullscreen is active."""
        # ── Visibility: fire on_game_enter on the FIRST tick only ──────────
        if not self._state.in_game:
            self._state.in_game = True
            self._state.hide_count += 1
            reason = "Game 🎮" if status.is_game else "Fullscreen 🖥️"
            print(f"[engine] HIDE Zorby  ← {reason}  ({status.title!r})")
            self._fire(self._on_game_enter)

        # ── Media pause: fire on the FIRST tick only (no spam) ─────────────
        if not self._state.media_paused and self.auto_pause_media:
            if is_audio_playing():
                ok = pause_media()
                if ok:
                    self._state.media_paused    = True
                    self._state.media_pause_count += 1
                    print(f"[engine] Media paused ✅  (total: {self._state.media_pause_count})")
                else:
                    print("[engine] Media pause failed ❌ — will retry next tick")
            else:
                # No audio at game-start; arm the guard so we don't try again
                self._state.media_paused = True
                print("[engine] No audio at game start — skipping pause")

    def _handle_game_inactive(self) -> None:
        """Called every tick while in normal (non-game) state."""
        if self._state.in_game:
            # Transition: game → idle
            self._state.in_game      = False
            self._state.media_paused = False   # re-arm for next session
            self._state.show_count  += 1
            print("[engine] SHOW Zorby  ← returned from game/fullscreen")
            self._fire(self._on_game_exit)

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _fire(listeners: list, *args) -> None:
        """Invoke every listener with *args*, logging but not re-raising errors."""
        for fn in listeners:
            try:
                fn(*args)
            except Exception as exc:
                print(f"[engine] Listener error: {exc}")

    def _log_config(self) -> None:
        w, h = _get_screen_resolution()
        print(f"  Screen        : {w} × {h}")
        print(f"  Poll interval : {self.interval}s")
        print(f"  Auto-pause    : {self.auto_pause_media}")
        print(f"  Work apps     : {', '.join(get_work_keywords())}")
        print(f"  Entertainment : {', '.join(get_entertainment_keywords())}")
        print(f"  Games         : {', '.join(get_games())}")
        print(f"  Hotkey        : Ctrl+Shift+Z\n")

    def _log_tick(self, s: AppStatus) -> None:
        flag = "HIDE" if s.should_hide else "SHOW"
        print(
            f"  [{self._state.tick_count:>5}] {flag:<4}  "
            f"mode={s.mode:<13}  "
            f"fs={s.is_fullscreen!s:<5}  "
            f"audio={s.audio_playing!s:<5}  "
            f"title={s.title!r}"
        )

    def _log_summary(self) -> None:
        st = self._state
        print(f"\n  ── Session summary ───────────────────")
        print(f"  Ticks          : {st.tick_count}")
        print(f"  Times hidden   : {st.hide_count}")
        print(f"  Times shown    : {st.show_count}")
        print(f"  Media pauses   : {st.media_pause_count}")
        print(f"  ──────────────────────────────────────\n")
