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
    send_telegram(f"Cevaplanamayan soru:\n{question}")


def record_contact(args: dict) -> None:
    name = _text_arg(args, "name", MAX_NAME_CHARS)
    email = _text_arg(args, "email", MAX_EMAIL_CHARS)
    if not EMAIL_PATTERN.match(email):
        raise ValueError("email is invalid")
    notes = _text_arg(args, "notes", MAX_NOTES_CHARS, required=False)
    send_telegram(f"Yeni iletisim:\nAd: {name}\nE-posta: {email}\nNot: {notes or '-'}")


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
                "Metinlerde cevabi olmayan bir soruyu Eren'e bildirir. "
                "Cevabini bilmedigin her soru icin cagir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Ziyaretcinin sordugu soru",
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
                "Eren ile iletisime gecmek isteyen ziyaretcinin bilgisini Eren'e iletir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Ziyaretcinin adi"},
                    "email": {"type": "string", "description": "Ziyaretcinin e-postasi"},
                    "notes": {
                        "type": "string",
                        "description": "Ziyaretcinin iletmek istedigi not (opsiyonel)",
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
