from core.main import format_error_line


def test_format_error_line_has_context_and_type():
    line = format_error_line("ws_turn", ValueError("boom"))
    assert "ws_turn" in line
    assert "ValueError" in line
    assert "boom" in line
