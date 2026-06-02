import re
import uuid
from datetime import datetime, timedelta

from core.atomicio import atomic_write_json

SCHEDULE_PATH = "config/schedule.json"


def parse_when(s, now=None):
    """Parse a human 'when' into either an ISO datetime (once) or a 'daily@HH:MM'
    recurring spec. Returns the string form stored in an entry's 'when'."""
    now = now or datetime.now()
    s = s.strip().lower()

    m = re.match(r"daily\s+at\s+(\d{1,2}):(\d{2})", s)
    if m:
        return f"daily@{int(m.group(1)):02d}:{m.group(2)}"

    m = re.match(r"in\s+(\d+)\s*m(in)?", s)
    if m:
        return (now + timedelta(minutes=int(m.group(1)))).isoformat()
    m = re.match(r"in\s+(\d+)\s*h(our)?", s)
    if m:
        return (now + timedelta(hours=int(m.group(1)))).isoformat()

    m = re.match(r"at\s+(\d{1,2}):(\d{2})", s)
    if m:
        target = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target.isoformat()

    # Fallback: assume it's already an ISO datetime.
    return s


def kind_for(when):
    return "recurring" if str(when).startswith("daily@") else "once"


def next_run(entry, now=None):
    """Return the next datetime this entry should fire, or None if it's a past one-off."""
    now = now or datetime.now()
    when = entry["when"]
    if str(when).startswith("daily@"):
        hh, mm = when.split("@")[1].split(":")
        target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        return target
    try:
        return datetime.fromisoformat(when)
    except (ValueError, TypeError):
        return None


def due_entries(entries, now=None):
    """Return entries that should fire at `now`."""
    now = now or datetime.now()
    out = []
    for e in entries:
        when = e.get("when")
        if str(when).startswith("daily@"):
            hh, mm = when.split("@")[1].split(":")
            target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if now >= target:
                last = e.get("last_run")
                last_day = last[:10] if last else None
                if last_day != now.date().isoformat():
                    out.append(e)
        else:
            try:
                target = datetime.fromisoformat(when)
            except (ValueError, TypeError):
                continue
            if now >= target and not e.get("last_run"):
                out.append(e)
    return out


def load_schedule(path=SCHEDULE_PATH):
    import json, os
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def save_schedule(entries, path=SCHEDULE_PATH):
    atomic_write_json(path, entries)


def add_entry(text, when_str, path=SCHEDULE_PATH, now=None):
    entries = load_schedule(path)
    when = parse_when(when_str, now)
    entry = {"id": uuid.uuid4().hex[:8], "kind": kind_for(when), "when": when,
             "text": text, "created_at": (now or datetime.now()).isoformat(), "last_run": None}
    entries.append(entry)
    save_schedule(entries, path)
    return entry


def cancel_entry(entry_id, path=SCHEDULE_PATH):
    entries = load_schedule(path)
    kept = [e for e in entries if e.get("id") != entry_id]
    save_schedule(kept, path)
    return len(kept) < len(entries)
