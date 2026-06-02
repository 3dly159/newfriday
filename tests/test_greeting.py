from core.greeting import build_greeting, pick_greeting_mode


def test_greeting_morning_named():
    g = build_greeting({"name": "Tony", "title": "Sir"}, hour=8, minutes_since_seen=0)
    assert "morning" in g.lower()
    assert "Sir" in g or "Tony" in g


def test_greeting_evening():
    g = build_greeting({"title": "Sir"}, hour=20, minutes_since_seen=0)
    assert "evening" in g.lower()


def test_greeting_welcome_back_after_absence():
    g = build_greeting({"title": "Sir"}, hour=14, minutes_since_seen=600)
    assert "welcome back" in g.lower()


def test_greeting_defaults_when_bio_empty():
    g = build_greeting({}, hour=12, minutes_since_seen=0)
    assert "Sir" in g
    assert len(g) > 0


def test_pick_mode_face_when_matched():
    assert pick_greeting_mode(has_camera=True, enrolled=True, matched=True) == "face"


def test_pick_mode_profile_on_any_failure():
    assert pick_greeting_mode(has_camera=False, enrolled=True, matched=False) == "profile"
    assert pick_greeting_mode(has_camera=True, enrolled=False, matched=False) == "profile"
    assert pick_greeting_mode(has_camera=True, enrolled=True, matched=False) == "profile"


from core.greeting import greeting_prompt


def test_greeting_prompt_includes_time_and_name():
    p = greeting_prompt({"name": "Tony", "title": "Sir"}, hour=8, minutes_since_seen=0)
    assert "morning" in p.lower()
    assert "Tony" in p or "Sir" in p
    assert "one" in p.lower() and "greet" in p.lower()


def test_greeting_prompt_mentions_absence():
    p = greeting_prompt({"title": "Sir"}, hour=14, minutes_since_seen=600)
    assert "while" in p.lower() or "back" in p.lower() or "hours" in p.lower()
