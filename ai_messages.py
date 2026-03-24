"""Short state-based motivational messages."""


def generate_message(state: str, duration: int) -> str:
    if state == "work":
        if duration < 20:
            return "Getting started, stay consistent 💪"
        if duration <= 50:
            return "Nice focus streak, keep going 🔥"
        return "You're in deep focus, consider a short break ⚡"

    if state == "entertainment":
        return "Taking a break is fine, don’t lose momentum 😉"

    if state == "idle":
        return "Ready to get back into focus?"

    return ""


def get_work_milestone_message(duration: int, triggered: set[int]) -> str:
    """Return one-time milestone message for work duration in minutes."""
    milestones = (
        (90, "Deep work mode achieved 🧠⚡"),
        (60, "You're locked in today 🔥"),
        (30, "Nice focus streak, keep going 🔥"),
    )
    for threshold, message in milestones:
        if duration > threshold and threshold not in triggered:
            triggered.add(threshold)
            return message
    return ""

