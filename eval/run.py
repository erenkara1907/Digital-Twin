import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from twin.chat import get_provider, reply
from twin.prompt import build_system_prompt

QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.jsonl"
UNKNOWN_TOOL = "record_unknown_question"
ACK_PHRASES = ("bilmiyorum", "iletiyorum", "bilgim yok")
VALID_TYPES = ("answerable", "unanswerable")
ANSWER_PREVIEW_CHARS = 300


@dataclass(frozen=True)
class Result:
    id: str
    passed: bool
    reason: str
    answer: str


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict]:
    questions = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        question = json.loads(line)
        if question.get("type") not in VALID_TYPES:
            raise ValueError(f"{question.get('id')}: unknown type {question.get('type')}")
        if question["type"] == "answerable" and not question.get("expect_all"):
            raise ValueError(f"{question['id']}: answerable question needs expect_all")
        questions.append(question)
    return questions


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    return stripped.replace("ı", "i")


def check(question: dict, answer: str, tool_calls: list[str]) -> tuple[bool, str]:
    normalized = _normalize(answer)
    if question["type"] == "answerable":
        return _check_answerable(question, normalized, tool_calls)
    return _check_unanswerable(normalized, tool_calls)


def _check_answerable(question: dict, normalized: str, tool_calls: list[str]):
    if tool_calls:
        return False, f"unneeded tool call: {', '.join(tool_calls)}"
    for group in question["expect_all"]:
        if not any(_normalize(alt) in normalized for alt in group):
            return False, f"missing any of: {group}"
    return True, "ok"


def _check_unanswerable(normalized: str, tool_calls: list[str]):
    if UNKNOWN_TOOL not in tool_calls:
        return False, f"{UNKNOWN_TOOL} was not called"
    if not any(phrase in normalized for phrase in ACK_PHRASES):
        return False, "answer does not admit it does not know (bilmiyorum)"
    return True, "ok"


def _recording_runner(calls: list[str]):
    def run_tool(name: str, arguments: str) -> str:
        calls.append(name)
        return json.dumps({"status": "ok"})

    return run_tool


def run_eval(client, model, system_prompt, questions, fallback_model=None):
    results = []
    for question in questions:
        calls: list[str] = []
        answer = reply(
            client,
            model,
            system_prompt,
            [{"role": "user", "content": question["question"]}],
            fallback_model,
            run_tool=_recording_runner(calls),
        )
        passed, reason = check(question, answer, calls)
        results.append(Result(question["id"], passed, reason, answer))
    return results


def main(provider_name: str = "groq") -> int:
    load_dotenv()
    provider = get_provider(provider_name)
    client = OpenAI(base_url=provider.base_url, api_key=provider.api_key)
    questions = load_questions()
    results = run_eval(
        client,
        provider.model,
        build_system_prompt(),
        questions,
        provider.fallback_model,
    )
    for question, result in zip(questions, results):
        status = "PASS" if result.passed else "FAIL"
        preview = result.answer.replace("\n", " ")[:ANSWER_PREVIEW_CHARS]
        print(f"[{status}] {result.id} {question['question']}")
        print(f"       {result.reason}\n       -> {preview}")
    answerable = [r for q, r in zip(questions, results) if q["type"] == "answerable"]
    unanswerable = [r for q, r in zip(questions, results) if q["type"] == "unanswerable"]
    print(
        f"\nanswerable: {sum(r.passed for r in answerable)}/{len(answerable)}  "
        f"unanswerable: {sum(r.passed for r in unanswerable)}/{len(unanswerable)}"
    )
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "groq"))
