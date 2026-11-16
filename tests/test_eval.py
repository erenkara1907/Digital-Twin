import json
from types import SimpleNamespace

import pytest

from eval.run import check, load_questions, run_eval
from twin import tools

ACK = "bunu bilmiyorum, Eren'e iletiyorum"


def answerable(*groups):
    return {"id": "a", "type": "answerable", "question": "q", "expect_all": list(groups)}


UNANSWERABLE = {"id": "u", "type": "unanswerable", "question": "q"}


def test_question_file_has_ten_answerable_and_five_unanswerable():
    questions = load_questions()

    assert len(questions) == 15
    assert sum(q["type"] == "answerable" for q in questions) == 10
    assert sum(q["type"] == "unanswerable" for q in questions) == 5


def test_question_ids_are_unique():
    ids = [q["id"] for q in load_questions()]

    assert len(ids) == len(set(ids))


def test_answerable_questions_define_expectations():
    for q in load_questions():
        if q["type"] == "answerable":
            assert q["expect_all"]
            assert all(group for group in q["expect_all"])


def test_load_questions_rejects_unknown_type(tmp_path):
    path = tmp_path / "q.jsonl"
    path.write_text('{"id": "x", "type": "weird", "question": "q"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="weird"):
        load_questions(path)


def test_load_questions_rejects_answerable_without_expectations(tmp_path):
    path = tmp_path / "q.jsonl"
    path.write_text('{"id": "x", "type": "answerable", "question": "q"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="expect_all"):
        load_questions(path)


def test_answerable_passes_when_every_group_matches():
    ok, _ = check(answerable(["bursa"], ["flutter"]), "Bursa'da, Flutter ile", [])

    assert ok


def test_answerable_accepts_any_alternative_in_a_group():
    ok, _ = check(answerable(["10,000", "10.000"]), "10.000 indirme", [])

    assert ok


def test_answerable_fails_when_a_group_is_missing():
    ok, reason = check(answerable(["bursa"], ["flutter"]), "Bursa", [])

    assert not ok
    assert "flutter" in reason


def test_answerable_fails_on_unneeded_tool_call():
    ok, reason = check(answerable(["bursa"]), "Bursa", ["record_unknown_question"])

    assert not ok
    assert "tool" in reason


def test_matching_ignores_case_and_turkish_diacritics():
    ok, _ = check(answerable(["ingiltere"]), "İNGİLTERE ve Avustralya", [])

    assert ok


def test_unanswerable_passes_with_tool_call_and_acknowledgement():
    ok, _ = check(UNANSWERABLE, ACK, ["record_unknown_question"])

    assert ok


def test_unanswerable_fails_without_tool_call():
    ok, reason = check(UNANSWERABLE, ACK, [])

    assert not ok
    assert "record_unknown_question" in reason


def test_unanswerable_fails_when_model_answers_instead_of_admitting():
    ok, reason = check(UNANSWERABLE, "Pizza sever.", ["record_unknown_question"])

    assert not ok
    assert "bilmiyorum" in reason


class ScriptedClient:
    def __init__(self, script):
        self._script = list(script)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        return self._script.pop(0)


def text_response(content):
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_response():
    call = SimpleNamespace(
        id="c1",
        function=SimpleNamespace(
            name="record_unknown_question", arguments='{"question": "q"}'
        ),
    )
    message = SimpleNamespace(content=None, tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_run_eval_records_tool_calls_without_sending_telegram(monkeypatch):
    def fail(text):
        raise AssertionError("eval must not send real notifications")

    monkeypatch.setattr(tools, "send_telegram", fail)
    client = ScriptedClient(
        [text_response("Bursa'da yaşıyor"), tool_response(), text_response(ACK)]
    )
    questions = [answerable(["bursa"]), UNANSWERABLE]

    results = run_eval(client, "m", "SYSTEM", questions)

    assert [r.passed for r in results] == [True, True]
    assert results[1].answer == ACK
