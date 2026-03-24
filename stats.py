"""Simple focus stats tracking and formatting."""

from dataclasses import dataclass


def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    hours = minutes // 60
    rem_minutes = minutes % 60
    if hours > 0:
        return f"{hours}h {rem_minutes}m"
    return f"{minutes}m"


@dataclass
class FocusStats:
    total_focus_seconds_today: int = 0
    longest_session_seconds: int = 0
    session_count: int = 0

    def add_focus_seconds(self, seconds: int, current_session_seconds: int) -> None:
        self.total_focus_seconds_today += seconds
        self.longest_session_seconds = max(
            self.longest_session_seconds, current_session_seconds
        )

    def register_session_start(self) -> None:
        self.session_count += 1

    def register_session_end(self, current_session_seconds: int) -> None:
        self.longest_session_seconds = max(
            self.longest_session_seconds, current_session_seconds
        )

    def today_text(self) -> str:
        return format_duration(self.total_focus_seconds_today)

    def best_text(self) -> str:
        return format_duration(self.longest_session_seconds)

