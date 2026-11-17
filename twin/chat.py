import logging
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

from twin.prompt import build_system_prompt
from twin.tools import TOOL_DEFINITIONS, run_tool as default_run_tool

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/v1"
GROQ_URL = "https://api.groq.com/openai/v1"
MAX_TOOL_ROUNDS = 3
BUSY_MESSAGE = "We're experiencing high demand right now, please try again shortly."


@dataclass(frozen=True)
class Provider:
    base_url: str
    api_key: str
    model: str
    fallback_model: str | None = None


def get_provider(name: str) -> Provider:
    if name == "ollama":
        return Provider(OLLAMA_URL, "ollama", "llama3.2")
    if name == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        return Provider(GROQ_URL, api_key, "openai/gpt-oss-120b", "llama-3.3-70b-versatile")
    raise ValueError(f"Unknown provider: {name}")


def _complete(client, models: list[str], **kwargs):
    last_error = None
    for model in models:
        try:
            return client.chat.completions.create(model=model, **kwargs)
        except RateLimitError as exc:
            logger.warning("rate limited on %s", model)
            last_error = exc
    raise last_error


def _assistant_message(message) -> dict:
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ],
    }


def _tool_messages(message, run_tool) -> list[dict]:
    return [
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": run_tool(call.function.name, call.function.arguments),
        }
        for call in message.tool_calls
    ]


def reply(
    client,
    model: str,
    system_prompt: str,
    history: list[dict],
    fallback_model: str | None = None,
    run_tool=default_run_tool,
) -> str:
    models = [m for m in (model, fallback_model) if m]
    messages = [{"role": "system", "content": system_prompt}, *history]
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = _complete(
                client, models, messages=messages, tools=TOOL_DEFINITIONS
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content
            messages = [
                *messages,
                _assistant_message(message),
                *_tool_messages(message, run_tool),
            ]
        final = _complete(client, models, messages=messages)
        return final.choices[0].message.content
    except RateLimitError:
        return BUSY_MESSAGE


def main(provider_name: str = "ollama") -> None:
    load_dotenv()
    provider = get_provider(provider_name)
    client = OpenAI(base_url=provider.base_url, api_key=provider.api_key)
    system_prompt = build_system_prompt()
    history: list[dict] = []
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not question:
            continue
        history = [*history, {"role": "user", "content": question}]
        answer = reply(
            client, provider.model, system_prompt, history, provider.fallback_model
        )
        history = [*history, {"role": "assistant", "content": answer}]
        print(f"twin> {answer}\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ollama")
