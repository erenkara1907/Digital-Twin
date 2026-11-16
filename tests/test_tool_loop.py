import httpx
import openai
import pytest
from types import SimpleNamespace

from twin import chat
from twin.tools import TOOL_DEFINITIONS


def text_response(content):
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_response(call_id="call_1", name="record_unknown_question", args='{"question": "q"}'):
    call = SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=args)
    )
    message = SimpleNamespace(content=None, tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def rate_limit_error():
    response = httpx.Response(429, request=httpx.Request("POST", "http://x"))
    return openai.RateLimitError("rate limited", response=response, body=None)


class ScriptedClient:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


HISTORY = [{"role": "user", "content": "soru"}]


def run_reply(client, run_tool=None, fallback="backup-model", history=HISTORY):
    return chat.reply(
        client,
        "primary-model",
        "SYSTEM",
        history,
        fallback_model=fallback,
        run_tool=run_tool or (lambda name, args: '{"status": "ok"}'),
    )


def test_plain_answer_is_returned_and_tools_are_offered():
    client = ScriptedClient([text_response("cevap")])

    assert run_reply(client) == "cevap"
    assert client.calls[0]["tools"] == TOOL_DEFINITIONS


def test_tool_call_is_executed_and_result_fed_back():
    executed = []

    def fake_run_tool(name, args):
        executed.append((name, args))
        return '{"status": "ok"}'

    client = ScriptedClient([tool_response(), text_response("iletildi")])

    assert run_reply(client, fake_run_tool) == "iletildi"
    assert executed == [("record_unknown_question", '{"question": "q"}')]
    second_messages = client.calls[1]["messages"]
    assert second_messages[-2]["role"] == "assistant"
    assert second_messages[-2]["tool_calls"][0]["id"] == "call_1"
    assert second_messages[-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"status": "ok"}',
    }


def test_tool_rounds_are_capped_at_three_then_forced_to_text():
    script = [tool_response(f"c{i}") for i in range(3)] + [text_response("son")]
    client = ScriptedClient(script)

    assert run_reply(client) == "son"
    assert len(client.calls) == 4
    assert "tools" not in client.calls[3]


def test_rate_limit_switches_to_fallback_model_once():
    client = ScriptedClient([rate_limit_error(), text_response("yedek cevap")])

    assert run_reply(client) == "yedek cevap"
    assert [c["model"] for c in client.calls] == ["primary-model", "backup-model"]


def test_both_models_rate_limited_returns_busy_message():
    client = ScriptedClient([rate_limit_error(), rate_limit_error()])

    assert run_reply(client) == chat.BUSY_MESSAGE
    assert len(client.calls) == 2


def test_rate_limit_without_fallback_returns_busy_message():
    client = ScriptedClient([rate_limit_error()])

    assert run_reply(client, fallback=None) == chat.BUSY_MESSAGE


def test_history_is_not_mutated_by_tool_rounds():
    history = [{"role": "user", "content": "soru"}]
    client = ScriptedClient([tool_response(), text_response("ok")])

    run_reply(client, history=history)

    assert history == [{"role": "user", "content": "soru"}]


def test_groq_provider_has_fallback_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    assert chat.get_provider("groq").fallback_model == "llama-3.3-70b-versatile"
    assert chat.get_provider("ollama").fallback_model is None
