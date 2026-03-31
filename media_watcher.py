"""media_watcher.py — Auto-pause media when playback is detected.

Runs a lightweight background loop that:
  1. Polls the system audio peak meter every `interval` seconds.
  2. On the first tick where audio is detected → sends a play/pause key once.
  3. Waits for audio to stop before arming the trigger again.
     This prevents repeated pause spam during the cooldown.

State machine
-------------
  IDLE  ──(audio detected)──▶  PAUSING  ──(pause sent)──▶  COOLDOWN
  ▲                                                              │
  └──────────────────(audio silent again)───────────────────────┘

Public API
----------
  MediaWatcher(interval, threshold)  — create watcher
  watcher.start()                    — begin background thread
  watcher.stop()                     — stop cleanly
  watcher.pause_count                — total times pause was triggered
"""

from __future__ import annotations

import threading
import time
from enum import Enum, auto

from audio import is_audio_playing
from media_control import pause_media


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class _State(Enum):
    IDLE     = auto()   # no audio: ready to arm
    PAUSING  = auto()   # audio found: sending pause
    COOLDOWN = auto()   # pause sent: waiting for audio to stop


# ---------------------------------------------------------------------------
# MediaWatcher
# ---------------------------------------------------------------------------

class MediaWatcher:
    """Continuously polls for audio and auto-pauses once per playback event.

    Args:
        interval:  Seconds between each poll (default 2.0).
        threshold: Peak amplitude to count as "playing" (default 0.001).
        on_pause:  Optional callback(paused: bool) fired after each action.
    """

    def __init__(
        self,
        interval:  float = 2.0,
        threshold: float = 0.001,
        on_pause=None,
    ) -> None:
        self.interval  = interval
        self.threshold = threshold
        self.on_pause  = on_pause          # callable(paused: bool) | None

        self.pause_count: int = 0          # total successful pauses this session
        self._state = _State.IDLE
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the watcher on a daemon background thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="MediaWatcher",
        )
        self._thread.start()
        print(f"[media_watcher] Started (interval={self.interval}s, threshold={self.threshold})")

    def stop(self) -> None:
        """Stop the watcher and wait for the background thread to exit."""
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
        print(f"[media_watcher] Stopped. Total pauses triggered: {self.pause_count}")

    # ── internal loop ──────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                print(f"[media_watcher] Tick error: {exc}")

            # Interruptible sleep — wakes immediately on stop()
            self._stop_event.wait(self.interval)

    def _tick(self) -> None:
        playing = is_audio_playing(self.threshold)

        if self._state == _State.IDLE:
            if playing:
                # Audio just started — send pause once and enter cooldown
                print("[media_watcher] Audio detected → pausing...")
                ok = pause_media()
                if ok:
                    self.pause_count += 1
                    self._state = _State.COOLDOWN
                    print(f"[media_watcher] Paused ✅  (total: {self.pause_count})")
                    if self.on_pause:
                        self.on_pause(True)
                else:
                    print("[media_watcher] Pause failed ❌ — will retry next tick")
                    # Stay in IDLE so we retry next poll

        elif self._state == _State.COOLDOWN:
            if not playing:
                # Audio has stopped — re-arm for the next playback event
                self._state = _State.IDLE
                print("[media_watcher] Audio stopped — armed and ready.")
                if self.on_pause:
                    self.on_pause(False)


# ---------------------------------------------------------------------------
# Convenience: run standalone
# ---------------------------------------------------------------------------

def run_watcher(
    interval:  float = 2.0,
    threshold: float = 0.001,
) -> None:
    """Block and run the media watcher until Ctrl-C."""
    watcher = MediaWatcher(interval=interval, threshold=threshold)
    watcher.start()

    print("[media_watcher] Running — press Ctrl-C to quit\n")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        watcher.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-pause media watcher")
    parser.add_argument("--interval",  type=float, default=2.0,   help="Poll interval in seconds")
    parser.add_argument("--threshold", type=float, default=0.001, help="Peak threshold (0.0–1.0)")
    args = parser.parse_args()

    run_watcher(interval=args.interval, threshold=args.threshold)
