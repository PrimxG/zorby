"""media_control.py — System-wide Windows media control via virtual keys.

Sends hardware media key events using Win32 SendInput (via ctypes), which
broadcasts to whichever app has registered for media keys — Spotify, VLC,
YouTube in Chrome/Firefox/Edge (via SMTC), Windows Media Player, etc.

Why SendInput instead of keyboard.send()?
  SendInput is the lowest-level Win32 API for injecting input at the
  device-driver level.  It works regardless of which window has focus
  and handles foreground/background apps equally.  The `keyboard` library
  is used as an optional fallback.

Why the toggle-key limitation?
  Windows exposes only VK_MEDIA_PLAY_PAUSE (0xB3) — a single toggle virtual
  key.  There is no separate "pause-only" or "play-only" hardware key.
  Callers that want directed pause/play behaviour (not a raw toggle) must
  check the current playback state via is_audio_playing() and skip the key
  press when the system is already in the desired state; otherwise a second
  call would *resume* media instead of keeping it paused.

Public API
----------
toggle_media()   → bool   Unconditional play/pause flip (use when intent is a toggle)
pause_media()    → bool   Stop playback only if audio is currently playing (idempotent)
play_media()     → bool   Start playback only if audio is currently silent  (idempotent)
next_track()     → bool   Skip to next track
prev_track()     → bool   Go back to previous track

All functions return True on success or "already in desired state",
False if SendInput failed.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import time

from audio import is_audio_playing

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
    """Send a play/pause toggle to the system media session unconditionally.

    Use this when the *intent* is to flip state regardless of current
    playback status (e.g. a user-facing hotkey).
    For directed pause or play, prefer pause_media() / play_media() instead.

    Works for: Spotify, VLC, YouTube (Chrome/Firefox/Edge via SMTC),
    Windows Media Player, and any app that registers media keys.

    Returns:
        True if the key event was successfully sent, False otherwise.
    """
    return _send_vk_with_fallback(VK_MEDIA_PLAY_PAUSE, "play/pause media")


def pause_media() -> bool:
    """Pause currently playing media — idempotent, no-op if already silent.

    Why the pre-flight check?
    -------------------------
    Windows exposes only VK_MEDIA_PLAY_PAUSE — a toggle key with no
    dedicated "pause-only" counterpart.  Sending it while media is already
    paused would *resume* playback instead of stopping it.  We therefore
    check the WASAPI peak meter first and skip the key press when audio is
    already silent, ensuring this function is safe to call multiple times
    (e.g. on consecutive ticks, or after the user already paused manually).

    Returns:
        True  — media is now paused (either we sent the key, or it was
                already silent).
        False — SendInput call failed.
    """
    if not is_audio_playing():
        # Already silent / paused — sending the toggle would resume playback.
        return True   # desired state already achieved; report success
    return _send_vk_with_fallback(VK_MEDIA_PLAY_PAUSE, "play/pause media")


def play_media() -> bool:
    """Resume paused media — idempotent, no-op if audio is already playing.

    Why the pre-flight check?
    -------------------------
    Same toggle-key constraint as pause_media(): sending VK_MEDIA_PLAY_PAUSE
    while audio is already playing would pause it.  We therefore only send
    the key when the peak meter confirms audio is currently silent.

    Returns:
        True  — media is now playing (either we sent the key, or it was
                already audible).
        False — SendInput call failed.
    """
    if is_audio_playing():
        # Already playing — sending the toggle would pause it.
        return True   # desired state already achieved; report success
    return _send_vk_with_fallback(VK_MEDIA_PLAY_PAUSE, "play/pause media")


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
