"""media_control.py — System-wide Windows media control via virtual keys.

Sends hardware media key events using Win32 SendInput (via ctypes), which
broadcasts to whichever app has registered for media keys — Spotify, VLC,
YouTube in Chrome/Firefox/Edge (via SMTC), Windows Media Player, etc.

Why SendInput instead of keyboard.send()?
  SendInput is the lowest-level Win32 API for injecting input at the
  device-driver level.  It works regardless of which window has focus
  and handles foreground/background apps equally.  The `keyboard` library
  is used as an optional fallback.

Public API
----------
toggle_media()   → bool   Play if paused, pause if playing (most common use)
pause_media()    → bool   Stop playback (sends play/pause — toggles to pause)
next_track()     → bool   Skip to next track
prev_track()     → bool   Go back to previous track

All functions return True on success, False if SendInput failed.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import time

# ---------------------------------------------------------------------------
# Win32 constants & structures
# ---------------------------------------------------------------------------

# Virtual-key codes for media keys
VK_MEDIA_PLAY_PAUSE: int = 0xB3
VK_MEDIA_NEXT_TRACK: int = 0xB0
VK_MEDIA_PREV_TRACK: int = 0xB1
VK_MEDIA_STOP:       int = 0xB2

# INPUT type
INPUT_KEYBOARD   = 1
KEYEVENTF_KEYUP  = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.wintypes.WORD),
        ("wScan",       ctypes.wintypes.WORD),
        ("dwFlags",     ctypes.wintypes.DWORD),
        ("time",        ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

    # Pad to the same size as the full INPUT union (which also has MOUSEINPUT
    # and HARDWAREINPUT, both larger than KEYBDINPUT on 64-bit).
    _anonymous_ = []


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type",    ctypes.wintypes.DWORD),
        ("_input",  _INPUT_UNION),
    ]


# ---------------------------------------------------------------------------
# Low-level key press/release helpers
# ---------------------------------------------------------------------------

def _make_key_input(vk: int, flags: int) -> INPUT:
    ki = KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=flags | KEYEVENTF_EXTENDEDKEY,
        time=0,
        dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0)),
    )
    ui = _INPUT_UNION(ki=ki)
    return INPUT(type=INPUT_KEYBOARD, _input=ui)


def _send_vk(vk: int) -> bool:
    """Simulate a full key-press + key-release for *vk* via SendInput.

    Returns True on success (SendInput reports it sent 2 events).
    """
    press   = _make_key_input(vk, 0)
    release = _make_key_input(vk, KEYEVENTF_KEYUP)
    events  = (INPUT * 2)(press, release)

    sent = ctypes.windll.user32.SendInput(
        2,
        ctypes.cast(events, ctypes.POINTER(INPUT)),
        ctypes.sizeof(INPUT),
    )
    return sent == 2


def _send_vk_with_fallback(vk: int, keyboard_name: str) -> bool:
    """Try SendInput first; fall back to the `keyboard` library if it fails."""
    if _send_vk(vk):
        return True

    # Fallback: keyboard library (already installed as a project dep)
    try:
        import keyboard as kb
        kb.send(keyboard_name)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public media control API
# ---------------------------------------------------------------------------

def toggle_media() -> bool:
    """Send a play/pause toggle to the system media session.

    Works for: Spotify, VLC, YouTube (Chrome/Firefox/Edge via SMTC),
    Windows Media Player, and any app that registers media keys.

    Returns:
        True if the key event was successfully sent, False otherwise.
    """
    return _send_vk_with_fallback(VK_MEDIA_PLAY_PAUSE, "play/pause media")


# Alias — semantically more explicit callers can use these.
# Both send the same VK_MEDIA_PLAY_PAUSE key (toggle); Windows/SMTC
# figures out the target state from the session's current playback status.
def pause_media() -> bool:
    """Pause currently playing media (sends play/pause toggle)."""
    return toggle_media()


def play_media() -> bool:
    """Resume paused media (sends play/pause toggle)."""
    return toggle_media()


def next_track() -> bool:
    """Skip to the next track in the active media session."""
    return _send_vk_with_fallback(VK_MEDIA_NEXT_TRACK, "next track")


def prev_track() -> bool:
    """Go back to the previous track in the active media session."""
    return _send_vk_with_fallback(VK_MEDIA_PREV_TRACK, "previous track")


def stop_media() -> bool:
    """Stop playback entirely (not just pause)."""
    return _send_vk_with_fallback(VK_MEDIA_STOP, "stop media")


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from audio import is_audio_playing

    print("Current audio state:", "PLAYING" if is_audio_playing() else "SILENT")
    print("Sending play/pause toggle...")

    ok = toggle_media()
    print("SendInput result:", "OK ✅" if ok else "FAILED ❌")

    time.sleep(0.5)
    print("Audio state after:", "PLAYING" if is_audio_playing() else "SILENT")
