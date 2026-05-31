from core import persona


def test_persona_version_is_stable_string():
    assert isinstance(persona.PERSONA_VERSION, str)
    assert persona.PERSONA_VERSION


def test_system_prompt_contains_core_traits():
    prompt = persona.build_system_prompt()
    low = prompt.lower()
    assert "friday" in low
    assert "sir" in low          # butler address
    assert "concise" in low or "brief" in low   # voice brevity
    assert "tool" in low         # tool discipline


def test_system_prompt_includes_mood_bias():
    prompt = persona.build_system_prompt(mood_bias="Highly witty and slightly mocking.")
    assert "Highly witty and slightly mocking." in prompt


def test_system_prompt_includes_lore_when_provided():
    prompt = persona.build_system_prompt(lore_context="You acknowledge the Stark legacy.")
    assert "Stark legacy" in prompt


def test_load_exemplars_returns_list():
    ex = persona.load_exemplars()
    assert isinstance(ex, list)
    assert all("user" in e and "assistant" in e for e in ex)


def test_select_exemplars_is_token_budgeted():
    chosen = persona.select_exemplars("what's my cpu doing", limit=2)
    assert isinstance(chosen, list)
    assert len(chosen) <= 2


from core.personality import FridayPersonality


def test_personality_delegates_to_contract():
    p = FridayPersonality()
    prompt = p.get_system_prompt()
    # The contract's version stamp must appear, proving delegation.
    from core import persona
    assert f"persona_version: {persona.PERSONA_VERSION}" in prompt


def test_personality_mood_bias_flows_through():
    p = FridayPersonality()
    p.set_mood("sarcastic")
    prompt = p.get_system_prompt()
    assert "mocking" in prompt.lower()
