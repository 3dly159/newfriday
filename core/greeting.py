"""Pure greeting composition + recognition-mode decision (mirrors recognition.js)."""


def _time_of_day(hour):
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    return "evening"


def build_greeting(bio, hour, minutes_since_seen=0):
    """Compose an in-persona greeting from bio + time + absence length."""
    address = bio.get("title") or bio.get("name") or "Sir"
    tod = _time_of_day(hour)
    if minutes_since_seen >= 240:
        return f"Welcome back, {address}. It's been a while — good {tod}."
    return f"Good {tod}, {address}. Friday is online and at your service."


def pick_greeting_mode(has_camera, enrolled, matched):
    """Return 'face' only when camera + enrollment + match all hold; else 'profile'."""
    if has_camera and enrolled and matched:
        return "face"
    return "profile"


def greeting_prompt(bio, hour, minutes_since_seen=0):
    """Build an LLM instruction to generate ONE short in-persona greeting line."""
    address = bio.get("title") or bio.get("name") or "Sir"
    tod = _time_of_day(hour)
    absence = ""
    if minutes_since_seen >= 240:
        hrs = minutes_since_seen // 60
        absence = f" The user has been away about {hrs} hours, so welcome them back."
    return (
        f"As Friday, greet the user with ONE short, in-character spoken line. "
        f"It is {tod}; address them as {address}.{absence} "
        f"No preamble or quotation marks — just the greeting line."
    )
