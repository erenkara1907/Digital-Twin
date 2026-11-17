import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator, model_validator

from twin.chat import Provider, get_provider, reply
from twin.prompt import build_system_prompt

# Local development only; on Vercel the variables are injected by the platform.
load_dotenv()

logger = logging.getLogger(__name__)

MAX_MESSAGES = 20
MAX_USER_MESSAGE_CHARS = 500
# The browser echoes the model's earlier replies back in the history; they are
# routinely longer than a visitor message, so they get a separate, larger cap.
MAX_ASSISTANT_MESSAGE_CHARS = 4000
DEFAULT_PROVIDER = "groq"
INVALID_REQUEST_MESSAGE = "Invalid request."
BACKEND_ERROR_MESSAGE = "I can't answer right now, please try again shortly."

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value

    @model_validator(mode="after")
    def content_must_fit_role_limit(self) -> "Message":
        limit = (
            MAX_USER_MESSAGE_CHARS
            if self.role == "user"
            else MAX_ASSISTANT_MESSAGE_CHARS
        )
        if len(self.content) > limit:
            raise ValueError(f"{self.role} message is longer than {limit} characters")
        return self


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=MAX_MESSAGES)

    @model_validator(mode="after")
    def last_message_must_be_from_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("last message must be from the user")
        return self


@dataclass(frozen=True)
class Backend:
    client: OpenAI
    provider: Provider
    system_prompt: str


@lru_cache(maxsize=1)
def get_backend() -> Backend:
    provider = get_provider(os.environ.get("CHAT_PROVIDER", DEFAULT_PROVIDER))
    client = OpenAI(base_url=provider.base_url, api_key=provider.api_key)
    return Backend(client, provider, build_system_prompt())


def answer(history: list[dict]) -> str:
    backend = get_backend()
    return reply(
        backend.client,
        backend.provider.model,
        backend.system_prompt,
        history,
        backend.provider.fallback_model,
    )


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Never echo the rejected input back to the caller.
    return JSONResponse({"error": INVALID_REQUEST_MESSAGE}, status_code=400)


@app.post("/api/chat")
def chat(request: ChatRequest):
    history = [message.model_dump() for message in request.messages]
    try:
        return {"reply": answer(history)}
    except Exception as exc:
        # Type only: exception text from HTTP clients can embed secrets.
        logger.error("chat failed: %s", type(exc).__name__)
        return JSONResponse({"error": BACKEND_ERROR_MESSAGE}, status_code=502)
