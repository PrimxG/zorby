"""Poll active window, control music, and update floating UI."""

from dataclasses import dataclass, field
import ai_messages
import music
import tracker
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication
from stats import FocusStats
from ui import FloatingOrbWindow

POLL_SECONDS = 3
AWAY_GRACE_SECONDS = 5 * 60


@dataclass
class AppState:
    music_on: bool = False
    music_mode: str | None = None
    previous_activity: str | None = None
    confirmed_activity: str | None = None
    session_active: bool = False
    away_seconds: int = 0
    work_seconds: int = 0
    break_reminded: bool = False
    achievement_30m_unlocked: bool = False
    achievement_1h_unlocked: bool = False
    work_message_thresholds_triggered: set[int] = field(default_factory=set)
    stats: FocusStats = field(default_factory=FocusStats)


def get_confirmed_activity(state: AppState, raw_activity: str) -> str | None:
    if state.previous_activity is not None and raw_activity == state.previous_activity:
        state.confirmed_activity = raw_activity
    state.previous_activity = raw_activity
    return state.confirmed_activity


def process_work_tick(state: AppState) -> None:
    if not state.session_active:
        state.session_active = True
        state.stats.register_session_start()
        print("Focus mode started")

    state.away_seconds = 0
    state.work_seconds += POLL_SECONDS
    state.stats.add_focus_seconds(POLL_SECONDS, state.work_seconds)
    print(f"Work session: {state.work_seconds // 60} minutes")

    if state.work_seconds >= 30 * 60 and not state.achievement_30m_unlocked:
        print("Achievement unlocked: 30 Min Focus Streak 🔥")
        state.achievement_30m_unlocked = True
    if state.work_seconds >= 60 * 60 and not state.achievement_1h_unlocked:
        print("Achievement unlocked: 1 Hour Focus Streak 🔥")
        state.achievement_1h_unlocked = True
    if state.work_seconds > 50 * 60 and not state.break_reminded:
        print("You've been working for a long time. Take a short break.")
        state.break_reminded = True


def process_away_tick(state: AppState) -> None:
    if not state.session_active:
        return
    state.away_seconds += POLL_SECONDS
    if state.away_seconds < AWAY_GRACE_SECONDS:
        return

    print("Focus session ended")
    state.stats.register_session_end(state.work_seconds)
    state.session_active = False
    state.away_seconds = 0
    state.work_seconds = 0
    state.break_reminded = False
    state.work_message_thresholds_triggered.clear()


def update_music(state: AppState, confirmed_activity: str | None) -> None:
    if confirmed_activity == "work":
        target_mode = "focus"
    elif confirmed_activity in ("entertainment", "idle"):
        target_mode = "calm"
    else:
        target_mode = None

    if target_mode is None:
        if state.music_on:
            music.stop_music()
            state.music_on = False
            state.music_mode = None
        return

    if state.music_on and state.music_mode == target_mode:
        return

    state.music_on = music.play_music(target_mode)
    state.music_mode = target_mode if state.music_on else None


def resolve_message(state: AppState, ui_state: str, focus_minutes: int) -> str:
    if state.confirmed_activity == "work":
        milestone_message = ai_messages.get_work_milestone_message(
            focus_minutes, state.work_message_thresholds_triggered
        )
        if milestone_message:
            return milestone_message
    return ai_messages.generate_message(ui_state, focus_minutes)


def update_ui(window: FloatingOrbWindow, state: AppState) -> None:
    focus_minutes = state.work_seconds // 60
    ui_state = state.confirmed_activity or "idle"

    window.set_mode(ui_state)
    window.set_focus_minutes(focus_minutes)
    window.set_message(resolve_message(state, ui_state, focus_minutes))
    window.set_break_alert(state.session_active and state.break_reminded)
    window.set_stats(
        state.stats.today_text(),
        state.stats.best_text(),
        state.stats.session_count,
    )


def tick(window: FloatingOrbWindow, state: AppState) -> None:
    title = tracker.get_active_window()
    activity = tracker.classify_activity(title)
    print(activity)
    confirmed_activity = get_confirmed_activity(state, activity)

    if confirmed_activity == "work":
        process_work_tick(state)
    else:
        process_away_tick(state)

    update_music(state, confirmed_activity)
    update_ui(window, state)


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication([])
    window = FloatingOrbWindow()
    state = AppState()
    window.show()
    window.raise_()

    timer = QTimer()
    timer.timeout.connect(lambda: tick(window, state))
    timer.start(POLL_SECONDS * 1000)
    tick(window, state)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
