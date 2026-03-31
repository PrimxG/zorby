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
from PyQt5.QtCore import QTimer, Qt
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
# Engine ↔ Qt bridge (runs on Qt main thread via Qt callbacks)
# ══════════════════════════════════════════════════════════════════════════

def _make_game_enter_handler(window: FloatingOrbWindow):
    def _on_enter():
        window.hide()
    return _on_enter


def _make_game_exit_handler(window: FloatingOrbWindow):
    def _on_exit():
        window.show()
        window.raise_()
    return _on_exit


# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════

def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication([])

    window  = FloatingOrbWindow()
    session = SessionState()

    # Wire engine callbacks → Qt window visibility
    engine = ZorbyEngine(interval=POLL_SECONDS, auto_pause_media=True)
    engine.on_game_enter(_make_game_enter_handler(window))
    engine.on_game_exit(_make_game_exit_handler(window))

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
