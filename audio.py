"""audio.py — Detect whether any audio is currently playing on Windows.

Uses the Windows Core Audio API (WASAPI) via pycaw to inspect all active
audio sessions and read their peak meter values.  A session with a peak
value above a small threshold is considered "playing".

Why peak meters instead of session state?
  Session state (Active / Inactive / Expired) is unreliable — many apps
  (browsers, games, media players) keep a session marked Active even when
  paused.  The IAudioMeterInformation peak is a real-time signal: it is
  non-zero only when samples are actually being pushed to the audio device.

Public API
----------
is_audio_playing(threshold)   → bool
    Returns True if *any* audio session has a peak above `threshold`.
    Safe to call from any thread.  Suitable for polling loops.

get_playing_sessions()        → list[SessionInfo]
    Returns a list of named sessions that are currently producing audio.
    Useful for debugging / logging which app is making sound.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

from pycaw.pycaw import AudioUtilities, IAudioMeterInformation


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Audio is considered "playing" when peak amplitude exceeds this value.
# 0.001 filters out digital silence / driver noise while catching real audio.
DEFAULT_THRESHOLD: float = 0.001


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionInfo:
    """Metadata for a single audio session that has active output."""
    pid:        int
    name:       str     # process name or "(System)"
    peak:       float   # instantaneous peak amplitude [0.0 – 1.0]

    def __str__(self) -> str:
        return f"{self.name} (pid={self.pid}, peak={self.peak:.4f})"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _get_peak(session) -> float:
    """Read the peak meter value for a pycaw AudioSession.

    Queries IAudioMeterInformation via COM QueryInterface.
    Returns 0.0 on any error (COM failures, access denied, etc.).
    """
    try:
        meter = session._ctl.QueryInterface(IAudioMeterInformation)
        return meter.GetPeakValue()
    except Exception:
        return 0.0


def _session_name(session) -> str:
    """Return a human-readable name for the audio session."""
    try:
        proc = session.Process
        if proc:
            return proc.name()
    except Exception:
        pass
    return "(System)"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_audio_playing(threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Return True if any Windows audio session is actively producing sound.

    Enumerates all WASAPI audio sessions and checks their peak meter.
    A peak value above `threshold` means samples are reaching the device.

    Args:
        threshold: Minimum peak value to count as "playing" [0.0 – 1.0].
                   Default 0.001 ignores digital silence / driver noise.

    Returns:
        True  — at least one session is above the threshold.
        False — all sessions are silent, or no sessions exist.
    """
    try:
        sessions = AudioUtilities.GetAllSessions()
        return any(_get_peak(s) > threshold for s in sessions)
    except Exception:
        return False


def get_playing_sessions(threshold: float = DEFAULT_THRESHOLD) -> list[SessionInfo]:
    """Return info for every audio session that is currently producing sound.

    Useful for logging or displaying which apps are playing audio.

    Args:
        threshold: Same meaning as in `is_audio_playing`.

    Returns:
        List of SessionInfo, sorted by peak value descending.
        Empty list if nothing is playing or on error.
    """
    results: list[SessionInfo] = []
    try:
        for session in AudioUtilities.GetAllSessions():
            peak = _get_peak(session)
            if peak > threshold:
                results.append(SessionInfo(
                    pid=session.ProcessId,
                    name=_session_name(session),
                    peak=peak,
                ))
    except Exception:
        pass

    return sorted(results, key=lambda s: s.peak, reverse=True)


# ---------------------------------------------------------------------------
# Quick manual test / standalone run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    print("Audio monitor — press Ctrl+C to quit\n")
    last_state: bool | None = None

    try:
        while True:
            playing  = is_audio_playing()
            sessions = get_playing_sessions() if playing else []

            if playing != last_state:
                if playing:
                    print("▶  Audio IS playing:")
                    for s in sessions:
                        print(f"   • {s}")
                else:
                    print("⏹  No audio playing.")
                last_state = playing

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nStopped.")
