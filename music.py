"""Background music via pygame mixer."""

from pathlib import Path
import random

import pygame

BASE_MUSIC_DIR = Path(__file__).resolve().parent / "assets" / "music"
FADE_MS = 1200
MODE_DIRS = {
    "focus": BASE_MUSIC_DIR / "focus",
    "calm": BASE_MUSIC_DIR / "calm",
}

_current_mode: str | None = None
_last_track_by_mode: dict[str, str] = {}


def _ensure_mixer() -> None:
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()


def get_random_track(mode: str) -> str | None:
    """Return random .mp3 path for focus/calm mode."""
    folder = MODE_DIRS.get(mode)
    if folder is None or not folder.is_dir():
        return None

    tracks = [str(p) for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"]
    if not tracks:
        return None

    last_track = _last_track_by_mode.get(mode)
    if len(tracks) > 1 and last_track in tracks:
        tracks = [track for track in tracks if track != last_track]

    return random.choice(tracks)


def _get_track_candidates(mode: str) -> list[str]:
    folder = MODE_DIRS.get(mode)
    if folder is None or not folder.is_dir():
        return []
    tracks = [str(p) for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"]
    if not tracks:
        return []

    random.shuffle(tracks)
    last_track = _last_track_by_mode.get(mode)
    if len(tracks) > 1 and last_track in tracks:
        tracks = [track for track in tracks if track != last_track] + [last_track]
    return tracks


def play_music(mode: str) -> bool:
    """Play random track for mode on loop. Skip if same mode is already playing."""
    global _current_mode
    try:
        _ensure_mixer()
        if pygame.mixer.music.get_busy() and _current_mode == mode:
            return True

        candidates = _get_track_candidates(mode)
        if not candidates:
            print(f"[music] No tracks found for mode: {mode}")
            return False

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(FADE_MS)
            pygame.time.wait(FADE_MS)

        for track in candidates:
            try:
                pygame.mixer.music.load(track)
                pygame.mixer.music.play(loops=-1, fade_ms=FADE_MS)
                _current_mode = mode
                _last_track_by_mode[mode] = track
                print(f"[music] Playing: {Path(track).name} ({mode})")
                return True
            except (OSError, pygame.error):
                print(f"[music] Failed to load track: {Path(track).name}")

        print(f"[music] Could not play any valid track for mode: {mode}")
        return False
    except (OSError, pygame.error):
        print(f"[music] Playback error for mode: {mode}")
        return False


def stop_music() -> None:
    """Stop music if the mixer is initialized."""
    global _current_mode
    try:
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.stop()
        _current_mode = None
    except pygame.error:
        pass
