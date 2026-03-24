# Zorby – Context-Aware Focus Assistant

Zorby is a smart desktop productivity assistant that adapts to your workflow in real time.
It detects user activity, automatically manages background music, tracks focus sessions, and provides intelligent feedback — all through a minimal floating UI.

---

## 🚀 Features

* 🎯 **Smart Activity Detection**
  Detects whether you're working, idle, or consuming content using window and process tracking.

* 🎧 **Dynamic Music System**
  Automatically plays focus music during work and adapts based on user state.

* 🧠 **Context-Aware Feedback**
  Generates intelligent messages based on session duration and behavior.

* ⏱️ **Focus Tracking & Stats**
  Tracks total focus time, longest session, and session count.

* 🏆 **Achievement System**
  Rewards productivity milestones like long focus streaks.

* 🟣 **Floating Orb UI**
  Minimal, animated interface inspired by modern assistants.

---

## 🧠 How It Works

Zorby continuously monitors the active window and classifies user activity into states:

* Work
* Entertainment
* Idle

Based on this state, it triggers:

* Music playback
* UI updates
* Smart messages
* Break reminders

---

## 🛠️ Tech Stack

* **Python**
* **PyQt5** – UI & animations
* **pygame** – music playback
* **psutil & pygetwindow** – activity detection

---

## ⚙️ Setup

```bash
pip install pyqt5 psutil pygetwindow pygame
python main.py
```


## 💡 Key Idea

Zorby is built around the concept of a **non-intrusive assistant** —
it doesn’t demand attention, but subtly enhances focus and productivity.

---

## 🔮 Future Improvements

* AI-powered personalized suggestions
* Spotify / streaming integration
* Advanced analytics dashboard
* Custom themes & modes

---

## 📌 Author

Built as a productivity-focused system design + UI/UX project.
