from types import SimpleNamespace

import pytest

from twin import chat


class FakeClient:
    def __init__(self, content="cevap"):
        self.calls = []
        self._content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self._content, tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_reply_prepends_system_prompt_and_returns_text():
    client = FakeClient("merhaba")
    history = [{"role": "user", "content": "selam"}]

    result = chat.reply(client, "model-x", "SYSTEM", history)

    assert result == "merhaba"
    assert client.calls[0]["model"] == "model-x"
    assert client.calls[0]["messages"] == [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "selam"},
    ]


def test_reply_does_not_mutate_history():
    client = FakeClient()
    history = [{"role": "user", "content": "selam"}]

    chat.reply(client, "m", "S", history)

    assert history == [{"role": "user", "content": "selam"}]


def test_ollama_provider_needs_no_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    provider = chat.get_provider("ollama")

    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model == "llama3.2"


def test_groq_provider_uses_default_model_and_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    provider = chat.get_provider("groq")

    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert provider.model == "openai/gpt-oss-120b"
    assert provider.api_key == "gsk_test"


def test_groq_provider_requires_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        chat.get_provider("groq")


def test_unknown_provider_rejected():
    with pytest.raises(ValueError, match="foo"):
        chat.get_provider("foo")
