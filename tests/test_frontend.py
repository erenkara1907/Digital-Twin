import re
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "public" / "index.html").read_text(
    encoding="utf-8"
)


def test_page_is_mobile_friendly():
    assert re.search(r'<meta[^>]+name="viewport"[^>]+width=device-width', HTML)


def test_input_is_limited_to_500_characters():
    assert 'maxlength="500"' in HTML


def test_model_output_is_never_injected_as_html():
    assert "innerHTML" not in HTML
    assert "insertAdjacentHTML" not in HTML
    assert "document.write" not in HTML


def test_page_posts_history_to_chat_endpoint():
    assert "/api/chat" in HTML
    assert "messages" in HTML


def test_page_states_contact_details_are_not_stored():
    assert "never stored" in HTML
    assert 'lang="en"' in HTML


def test_page_enforces_twenty_message_limit():
    assert "MAX_MESSAGES = 20" in HTML
