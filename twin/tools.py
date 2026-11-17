import json
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_TIMEOUT_SECONDS = 10

MAX_QUESTION_CHARS = 1000
MAX_NAME_CHARS = 100
MAX_EMAIL_CHARS = 254
MAX_NOTES_CHARS = 1000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def send_telegram(text: str) -> None:
    token = _require_env("TELEGRAM_BOT_TOKEN")
    chat_id = _require_env("TELEGRAM_CHAT_ID")
    response = httpx.post(
        f"{TELEGRAM_API}/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=TELEGRAM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def _text_arg(args: dict, key: str, max_chars: int, required: bool = True) -> str:
    value = args.get(key, "")
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{key} is required")
    if len(value) > max_chars:
        raise ValueError(f"{key} is too long (max {max_chars} characters)")
    return value


def record_unknown_question(args: dict) -> None:
    question = _text_arg(args, "question", MAX_QUESTION_CHARS)
    send_telegram(f"Unanswered question:\n{question}")


def record_contact(args: dict) -> None:
    name = _text_arg(args, "name", MAX_NAME_CHARS)
    email = _text_arg(args, "email", MAX_EMAIL_CHARS)
    if not EMAIL_PATTERN.match(email):
        raise ValueError("email is invalid")
    notes = _text_arg(args, "notes", MAX_NOTES_CHARS, required=False)
    send_telegram(f"New contact:\nName: {name}\nEmail: {email}\nNotes: {notes or '-'}")


_HANDLERS = {
    "record_unknown_question": record_unknown_question,
    "record_contact": record_contact,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "record_unknown_question",
            "description": (
                "Reports a question to Eren that the texts do not answer. "
                "Call it for every question you cannot answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question the visitor asked",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_contact",
            "description": (
                "Passes on to Eren the details of a visitor who wants to get in touch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The visitor's name"},
                    "email": {"type": "string", "description": "The visitor's email address"},
                    "notes": {
                        "type": "string",
                        "description": "A note the visitor wants to pass on (optional)",
                    },
                },
                "required": ["name", "email"],
            },
        },
    },
]


def _result(status: str, message: str = "") -> str:
    payload = {"status": status}
    if message:
        payload["message"] = message
    return json.dumps(payload)


def run_tool(name: str, arguments: str) -> str:
    handler = _HANDLERS.get(name)
    if handler is None:
        return _result("error", f"unknown tool: {name}")
    try:
        args = json.loads(arguments)
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
        handler(args)
    except ValueError as exc:
        return _result("error", str(exc))
    except (RuntimeError, httpx.HTTPError) as exc:
        # Log only the exception type: httpx messages embed the bot token in the URL.
        logger.error("tool %s failed: %s", name, type(exc).__name__)
        return _result("error", "notification could not be delivered")
    return _result("ok")
