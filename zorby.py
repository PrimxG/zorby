"""zorby.py — CLI entry point for the Zorby monitor.

Thin wrapper around ZorbyEngine. All logic lives in engine.py.

Usage
-----
    python zorby.py                    # default 1-second poll
    python zorby.py --interval 2       # poll every 2 seconds
    python zorby.py --no-pause         # detect only, don't pause media
    python zorby.py --verbose          # print every tick
"""

from __future__ import annotations

import argparse
import signal
import time

from engine import ZorbyEngine, AppStatus, DEFAULT_INTERVAL


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="zorby",
        description="Zorby Monitor — detects games/fullscreen, hides Zorby, pauses media.",
    )
    p.add_argument("--interval",  type=float, default=DEFAULT_INTERVAL,
                   metavar="SEC", help="Poll interval in seconds (default: %(default)s)")
    p.add_argument("--no-pause",  action="store_true",
                   help="Detect games/fullscreen but do NOT auto-pause media")
    p.add_argument("--verbose",   action="store_true",
                   help="Print every tick (not just state changes)")
    return p.parse_args()


def _on_status(s: AppStatus) -> None:
    """Print a compact status line on every meaningful change."""
    flag    = "HIDE" if s.should_hide else "SHOW"
    reason  = ""
    if s.should_hide:
        reason = f"  ({'Game' if s.is_game else 'Fullscreen'})"
    print(f"  [{flag}]{reason}  mode={s.mode:<13}  window={s.title!r}")


def main() -> None:
    args = _parse_args()

    engine = ZorbyEngine(
        interval=args.interval,
        auto_pause_media=not args.no_pause,
        verbose=args.verbose,
    )
    engine.on_status_change(_on_status)

    def _shutdown(sig, _frame):
        print("\n[zorby] Shutting down...")
        engine.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("=" * 52)
    print("        Z O R B Y   M O N I T O R")
    print("=" * 52)

    engine.start()

    try:
        while engine._running:
            time.sleep(0.2)
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
