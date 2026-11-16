import httpx
import pytest

from twin import tools


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=httpx.Request("POST", "http://x"), response=self
            )


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOKEN123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")


def test_send_telegram_posts_to_bot_api(env, monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json))
        return FakeResponse()

    monkeypatch.setattr(tools.httpx, "post", fake_post)

    tools.send_telegram("merhaba")

    assert calls == [
        (
            "https://api.telegram.org/botTOKEN123/sendMessage",
            {"chat_id": "42", "text": "merhaba"},
        )
    ]


def test_send_telegram_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        tools.send_telegram("x")


def test_send_telegram_raises_when_chat_id_missing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(RuntimeError, match="TELEGRAM_CHAT_ID"):
        tools.send_telegram("x")


def test_send_telegram_raises_on_http_error(env, monkeypatch):
    monkeypatch.setattr(
        tools.httpx, "post", lambda url, json, timeout: FakeResponse(401)
    )

    with pytest.raises(httpx.HTTPStatusError):
        tools.send_telegram("x")
