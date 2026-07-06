"""main.py — Zorby Qt UI entry point.

Wires ZorbyEngine into the PyQt5 floating orb UI.
All monitoring logic lives in engine.py — main.py only handles:
  - Qt app lifecycle
  - Translating engine events → UI updates and music changes
"""

from dataclasses import dataclass, field

import ai_messages
import music
from engine import ZorbyEngine, AppStatus, MODE_WORK, MODE_ENTERTAINMENT, MODE_GAME
from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication
from stats import FocusStats
from ui import FloatingOrbWindow

# ── tunables ──────────────────────────────────────────────────────────────
POLL_SECONDS       = 3
AWAY_GRACE_SECONDS = 5 * 60


# ══════════════════════════════════════════════════════════════════════════
# Focus session state (UI / work-timer — separate from engine internals)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class SessionState:
    """Tracks work-session progress for the UI timer, music and achievements."""
    # Activity confirmation (requires two consecutive identical ticks)
    previous_mode:   str | None = None
    confirmed_mode:  str | None = None

    # Music
    music_on:   bool      = False
    music_mode: str | None = None

    # Work timer
    session_active: bool = False
    away_seconds:   int  = 0
    work_seconds:   int  = 0

    # Reminders and achievements
    break_reminded:          bool = False
    achievement_30m_unlocked: bool = False
    achievement_1h_unlocked:  bool = False
    work_message_thresholds_triggered: set[int] = field(default_factory=set)

    # Today's cumulative stats
    stats: FocusStats = field(default_factory=FocusStats)


# ══════════════════════════════════════════════════════════════════════════
# Activity confirmation
# ══════════════════════════════════════════════════════════════════════════

def _confirm_mode(session: SessionState, raw_mode: str) -> str | None:
    """Return mode only after two consecutive identical observations."""
    if session.previous_mode == raw_mode:
        session.confirmed_mode = raw_mode
    session.previous_mode = raw_mode
    return session.confirmed_mode


# ══════════════════════════════════════════════════════════════════════════
# Work session processing
# ══════════════════════════════════════════════════════════════════════════

def _process_work_tick(session: SessionState) -> None:
    if not session.session_active:
        session.session_active = True
        session.stats.register_session_start()
        print("Focus mode started")

    session.away_seconds  = 0
    session.work_seconds += POLL_SECONDS
    session.stats.add_focus_seconds(POLL_SECONDS, session.work_seconds)
    print(f"Work session: {session.work_seconds // 60} minutes")

    if session.work_seconds >= 30 * 60 and not session.achievement_30m_unlocked:
        print("Achievement unlocked: 30 Min Focus Streak 🔥")
        session.achievement_30m_unlocked = True
    if session.work_seconds >= 60 * 60 and not session.achievement_1h_unlocked:
        print("Achievement unlocked: 1 Hour Focus Streak 🔥")
        session.achievement_1h_unlocked = True
    if session.work_seconds > 50 * 60 and not session.break_reminded:
        print("You've been working a long time — take a break.")
        session.break_reminded = True


def _process_away_tick(session: SessionState) -> None:
    if not session.session_active:
        return
    session.away_seconds += POLL_SECONDS
    if session.away_seconds < AWAY_GRACE_SECONDS:
        return
    print("Focus session ended")
    session.stats.register_session_end(session.work_seconds)
    session.session_active = False
    session.away_seconds   = 0
    session.work_seconds   = 0
    session.break_reminded = False
    session.work_message_thresholds_triggered.clear()


# ══════════════════════════════════════════════════════════════════════════
# Music
# ══════════════════════════════════════════════════════════════════════════

def _update_music(session: SessionState, confirmed_mode: str | None) -> None:
    if confirmed_mode == MODE_WORK:
        target = "focus"
    elif confirmed_mode in (MODE_ENTERTAINMENT, "idle"):
        target = "calm"
    else:
        target = None

    if target is None:
        if session.music_on:
            music.stop_music()
            session.music_on   = False
            session.music_mode = None
        return

    if session.music_on and session.music_mode == target:
        return

    session.music_on   = music.play_music(target)
    session.music_mode = target if session.music_on else None


# ══════════════════════════════════════════════════════════════════════════
# UI update
# ══════════════════════════════════════════════════════════════════════════

def _resolve_message(session: SessionState, ui_mode: str, focus_minutes: int) -> str:
    if session.confirmed_mode == MODE_WORK:
        msg = ai_messages.get_work_milestone_message(
            focus_minutes, session.work_message_thresholds_triggered
        )
        if msg:
            return msg
    return ai_messages.generate_message(ui_mode, focus_minutes)


def _update_ui(window: FloatingOrbWindow, session: SessionState) -> None:
    focus_minutes = session.work_seconds // 60
    ui_mode       = session.confirmed_mode or "idle"

    window.set_mode(ui_mode)
    window.set_focus_minutes(focus_minutes)
    window.set_message(_resolve_message(session, ui_mode, focus_minutes))
    window.set_break_alert(session.session_active and session.break_reminded)
    window.set_stats(
        session.stats.today_text(),
        session.stats.best_text(),
        session.stats.session_count,
    )


# ══════════════════════════════════════════════════════════════════════════
# Qt tick — driven by QTimer, reads latest engine status
# ══════════════════════════════════════════════════════════════════════════

def _tick(engine: ZorbyEngine, window: FloatingOrbWindow, session: SessionState) -> None:
    status = engine.status
    if status is None:
        return   # engine hasn't produced a tick yet

    print(status.mode)

    # Skip music / UI while gaming — engine already hides the window
    if status.should_hide:
        return

    confirmed = _confirm_mode(session, status.mode)

    if confirmed == MODE_WORK:
        _process_work_tick(session)
    else:
        _process_away_tick(session)

    _update_music(session, confirmed)
    _update_ui(window, session)


# ══════════════════════════════════════════════════════════════════════════
# Engine ↔ Qt bridge
# ══════════════════════════════════════════════════════════════════════════
#
# Problem: engine callbacks are invoked on the engine's background thread.
# Calling Qt widget methods (hide, show, raise_…) directly from that thread
# is undefined behaviour in PyQt5 and a common source of crashes / visual
# corruption.
#
# Solution: _EngineBridge is a QObject that lives on the main thread.
# Its pyqtSignals are emitted from the background thread (safe — Qt queues
# the delivery automatically) and connected to @pyqtSlots that execute on
# the main thread, where widget access is always valid.
# ══════════════════════════════════════════════════════════════════════════

class _EngineBridge(QObject):
    """Thread-safe bridge between ZorbyEngine callbacks and Qt widgets.

    Signals
    -------
    game_entered  emitted (from any thread) when a game/fullscreen session starts.
    game_exited   emitted (from any thread) when a game/fullscreen session ends.
    """

    game_entered = pyqtSignal()   # engine background thread → main thread
    game_exited  = pyqtSignal()   # engine background thread → main thread

    def __init__(self, window: FloatingOrbWindow, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Connect signals to slots once at construction time.
        # Qt will always deliver these on the main thread (queued connection).
        self.game_entered.connect(self._on_game_entered)
        self.game_exited.connect(self._on_game_exited)
        self._window = window

    # ── Callbacks registered with ZorbyEngine (called on engine thread) ─────
    # These only emit a signal — the safest possible operation from a non-Qt
    # thread.  No widget access happens here.

    def emit_game_entered(self) -> None:
        """Engine calls this on its background thread."""
        self.game_entered.emit()

    def emit_game_exited(self) -> None:
        """Engine calls this on its background thread."""
        self.game_exited.emit()

    # ── Slots executed on the main thread ───────────────────────────────────

    @pyqtSlot()
    def _on_game_entered(self) -> None:
        """Hide Zorby while a game / fullscreen app is active."""
        self._window.hide()

    @pyqtSlot()
    def _on_game_exited(self) -> None:
        """Restore Zorby after returning from a game / fullscreen app."""
        self._window.show()
        self._window.raise_()


# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════

def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication([])

    window  = FloatingOrbWindow()
    session = SessionState()

    # Wire engine callbacks → Qt window visibility via a thread-safe bridge.
    # The bridge QObject lives on the main thread; its slots are always
    # invoked on the main thread regardless of which thread emits the signal.
    engine = ZorbyEngine(interval=POLL_SECONDS, auto_pause_media=True)
    bridge = _EngineBridge(window)
    engine.on_game_enter(bridge.emit_game_entered)
    engine.on_game_exit(bridge.emit_game_exited)

    window.show()
    window.raise_()
    engine.start()

    # QTimer drives the UI tick (reads engine.status snapshot)
    timer = QTimer()
    timer.timeout.connect(lambda: _tick(engine, window, session))
    timer.start(POLL_SECONDS * 1000)

    app.aboutToQuit.connect(engine.stop)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
