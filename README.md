# Zorby – Context-Aware Focus Assistant

Zorby is a smart desktop productivity assistant that adapts to your workflow in real time.
It detects user activity, automatically manages background music, pauses media intelligently, tracks focus sessions, and provides intelligent feedback — all through a minimal floating UI.

---

## 🚀 Features

* 🎯 **Smart Activity Classification**
  Automatically classifies active applications into Work 🧠, Entertainment 🍿, or Game 🎮 using keyword matching.

* 🎮 **Game & Fullscreen Detection**
  Automatically hides Zorby and optionally pauses media when entering games or fullscreen applications.

* 🔊 **Real-Time Audio Detection**
  Detects active audio playback using Windows Core Audio API (WASAPI) peak metering for accurate playback sensing.

* 🎧 **Smart Media Control**
  Auto-pauses media when audio is detected playing, with intelligent cooldown to avoid spam.

* 🎵 **Dynamic Music System**
  Automatically plays focus music during work sessions and adapts based on user state.

* 🧠 **Context-Aware Feedback**
  Generates intelligent messages based on session duration and activity classification.

* ⏱️ **Focus Tracking & Stats**
  Tracks total focus time, longest session, and session count with real-time updates.

* 🏆 **Achievement System**
  Rewards productivity milestones with 30-minute and 1-hour achievement unlocks.

* 🟣 **Floating Orb UI**
  Minimal, non-intrusive animated interface that stays visible during productivity.

---

## 🧠 How It Works

Zorby runs a **centralized engine** (`ZorbyEngine`) that continuously monitors:

### Monitoring Loop
1. **Active Window Tracking** – polls window title and fullscreen state
2. **App Classification** – matches window title against configurable keyword lists to determine category
3. **Audio Detection** – uses WASAPI to measure peak audio amplitude across all system sessions
4. **State Transitions** – triggers callbacks when entering/exiting games or when system state changes

### Activity States

Zorby classifies activities into:
* **Work** 🧠 – IDE, editors, documentation
* **Entertainment** 🍿 – YouTube, social media, streaming
* **Game** 🎮 – detected games and fullscreen apps
* **Idle** – no active window or classified as other
* **Other** – unclassified applications

### Smart Behaviors

Based on detected state, Zorby triggers:
* **Music Control** – plays focus music during work, pauses on game detection
* **Media Auto-Pause** – pauses audio when fullscreen or game detected  
* **UI Updates** – timer, session tracking, and orb animations
* **Smart Messages** – context-aware feedback based on session length
* **Break Reminders** – prompts after extended focus sessions

---

## 🛠️ Architecture

Zorby's core is **ZorbyEngine** — a clean event-driven system that separates concerns:

```
┌─────────────────────────────────────┐
│         ZorbyEngine (core)           │
│  Single source of truth for all      │
│  background monitoring & events      │
└─────────────────────────────────────┘
         ▲           ▲
    ┌────┴───────────┴────┐
    │                     │
    │ Main.py (Qt UI)     │ Zorby.py (CLI)
    │ pygame music ctrl   │ Direct monitoring
    │ Session tracking    │ Event callbacks
```

### Key Modules

| Module | Purpose |
|--------|---------|
| **engine.py** | Central `ZorbyEngine`: monitors window, detects fullscreen/games, triggers callbacks |
| **classifier.py** | Classifies apps by keyword matching (Work/Entertainment/Game) |
| **audio.py** | Real-time audio detection via Windows WASAPI peak metering |
| **media_watcher.py** | Background thread that auto-pauses media on audio detection |
| **media_control.py** | Low-level media pause/play control |
| **hotkey.py** | Global hotkey registration for manual pause toggle |
| **fullscreen.py** | Detects fullscreen windows, screen resolution |
| **tracker.py** | Active window title/handle retrieval (Win32) |
| **config.py** | Keyword lists for app classification |
| **stats.py** | Focus session tracking & statistics |
| **ui.py** | PyQt5 floating orb UI rendering |
| **music.py** | pygame-based music playback |
| **ai_messages.py** | Context-aware message generation |

---

## 🛠️ Tech Stack

* **Python 3.10+**
* **PyQt5** – UI & animations
* **pygame** – music playback
* **psutil & pygetwindow** – process & window tracking
* **pycaw** – Windows Core Audio API (WASAPI) for audio detection
* **pynput** – global hotkey registration

---

## ⚙️ Setup

### Requirements
* Windows 10+ (uses Win32 API and Windows Core Audio)
* Python 3.10+

### Installation

```bash
pip install pyqt5 pygame psutil pygetwindow pycaw pynput
```

### Running Zorby

**Qt UI (Floating Orb)**
```bash
python main.py
```

**CLI Monitor** (detection only, no UI)
```bash
python zorby.py                    # default 1-second poll
python zorby.py --interval 2       # poll every 2 seconds
python zorby.py --no-pause         # detect only, don't auto-pause media
python zorby.py --verbose          # print every state change
```

The CLI is useful for background monitoring, server deployment, or testing the engine independently.

---

## 🎛️ Configuration

Edit `config.json` to customize:

* **Work keywords** – app names to classify as work (VS Code, Jupyter, LeetCode, etc.)
* **Entertainment keywords** – app names for entertainment (YouTube, Netflix, Reddit, etc.)
* **Game keywords** – explicit game titles to detect and hide from
* **Music paths** – directories containing focus music tracks
* **Audio threshold** – sensitivity for audio playback detection (default: 0.001)


## 💡 Design Philosophy

Zorby is built around **non-intrusive assistance**:
* Stays **hidden during games/fullscreen** so it never distracts
* **Auto-pauses media** intelligently without annoying spam
* **Minimal floating UI** that tracks progress without demanding attention
* **Event-driven architecture** that scales cleanly across UI, CLI, and headless deployments

The **ZorbyEngine** abstraction means the core logic is independent of presentation — Qt UI, CLI monitoring, or future integrations (API, notifications, etc.) can all use the same engine.

---

## 🔮 Future Improvements

* **Spotify & Streaming Integration** – control playback across platforms
* **Advanced Analytics Dashboard** – detailed focus statistics and trends
* **Custom Themes & Modes** – user-customizable UI and behavior profiles
* **Adaptive Music Selection** – ML-based music recommendations based on work patterns
* **Web API** – expose engine as HTTP service for mobile control
* **Break Activity Suggestions** – intelligent recommendations during breaks
* **Multi-Monitor Support** – smarter fullscreen detection for ultrawide setups
* **Pomodoro Timer** – structured focus sessions with configurable intervals

---

## 📌 Author

Built as a productivity-focused system design + UI/UX project.
