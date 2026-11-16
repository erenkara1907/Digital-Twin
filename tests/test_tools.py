import json

import httpx
import pytest

from twin import tools


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(tools, "send_telegram", messages.append)
    return messages


def run(tool_name, /, **args):
    return json.loads(tools.run_tool(tool_name, json.dumps(args)))


def test_record_unknown_question_notifies_owner(sent):
    result = run("record_unknown_question", question="En sevdigi yemek ne?")

    assert result["status"] == "ok"
    assert len(sent) == 1
    assert "Cevaplanamayan soru" in sent[0]
    assert "En sevdigi yemek ne?" in sent[0]


def test_record_contact_notifies_owner_with_all_fields(sent):
    result = run(
        "record_contact", name="Ayse", email="ayse@example.com", notes="Flutter rolu"
    )

    assert result["status"] == "ok"
    assert "Ayse" in sent[0]
    assert "ayse@example.com" in sent[0]
    assert "Flutter rolu" in sent[0]


def test_record_contact_notes_are_optional(sent):
    result = run("record_contact", name="Ayse", email="ayse@example.com")

    assert result["status"] == "ok"
    assert len(sent) == 1


def test_record_contact_rejects_invalid_email(sent):
    result = run("record_contact", name="Ayse", email="not-an-email")

    assert result["status"] == "error"
    assert sent == []


def test_missing_required_argument_rejected(sent):
    result = run("record_unknown_question")

    assert result["status"] == "error"
    assert sent == []


def test_overlong_question_rejected(sent):
    result = run("record_unknown_question", question="x" * 1001)

    assert result["status"] == "error"
    assert sent == []


def test_non_string_argument_rejected(sent):
    result = run("record_unknown_question", question=123)

    assert result["status"] == "error"
    assert sent == []


def test_unknown_tool_rejected(sent):
    result = run("delete_everything", question="x")

    assert result["status"] == "error"
    assert sent == []


def test_invalid_json_rejected(sent):
    result = json.loads(tools.run_tool("record_unknown_question", "{not json"))

    assert result["status"] == "error"
    assert sent == []


def test_non_object_arguments_rejected(sent):
    result = json.loads(tools.run_tool("record_unknown_question", '["a"]'))

    assert result["status"] == "error"
    assert sent == []


def test_telegram_failure_is_reported_without_leaking_secrets(monkeypatch):
    def boom(text):
        raise httpx.ConnectError("https://api.telegram.org/botSECRET/sendMessage")

    monkeypatch.setattr(tools, "send_telegram", boom)

    raw = tools.run_tool("record_unknown_question", '{"question": "x"}')

    assert json.loads(raw)["status"] == "error"
    assert "SECRET" not in raw


def test_tool_definitions_expose_both_tools():
    names = {d["function"]["name"] for d in tools.TOOL_DEFINITIONS}

    assert names == {"record_unknown_question", "record_contact"}
    for definition in tools.TOOL_DEFINITIONS:
        assert definition["type"] == "function"
        assert definition["function"]["parameters"]["required"]
