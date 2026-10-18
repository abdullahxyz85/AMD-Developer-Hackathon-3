"""AMD Token Factory client (OpenAI-compatible chat endpoint).

Standard-library + httpx only; no vendor SDK. The API key is mandatory:
every call raises MissingAPIKeyError with setup instructions when absent.
"""
from __future__ import annotations

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .config import AMD_BASE_URL, AMD_MODEL, MissingAPIKeyError, require_api_key

TIMEOUT = 600


class LLMError(RuntimeError):
    """Raised when the AMD endpoint fails or returns unusable output."""


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer " + require_api_key(), "Content-Type": "application/json"}


def _request(path: str, body: dict | None = None) -> dict:
    # Match tutor.run's proven urllib transport, not just its JSON fields.
    request = Request(AMD_BASE_URL + path,
        data=json.dumps(body, ensure_ascii=True).encode("utf-8") if body is not None else None,
        headers=_auth_headers())
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 429:
            raise LLMError("AMD endpoint rate-limited (HTTP 429); Retry-After="
                           + exc.headers.get("Retry-After", "unknown")) from exc
        detail = exc.read(2048).decode("utf-8", errors="replace")[:300]
        raise LLMError(f"AMD {path} returned HTTP {exc.code}: {detail}") from exc
    except (URLError, OSError) as exc:
        raise LLMError(f"Could not reach AMD endpoint {AMD_BASE_URL}: {exc}") from exc
    except ValueError as exc:
        raise LLMError("AMD endpoint returned invalid JSON") from exc


def list_models() -> list[str]:
    """Return available model IDs from the AMD endpoint."""
    payload = _request("/models")
    models = [m.get("id") for m in payload.get("data", []) if m.get("id")]
    if not models:
        raise LLMError(f"AMD /models returned no models: {str(payload)[:300]}")
    return models


def chat(messages: list[dict], *, model: str | None = None, temperature: float = 0.2,
         max_tokens: int = 4096, json_mode: bool = True) -> str:
    """Send a chat completion and return the assistant message content."""
    body: dict = {
        "model": model or AMD_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_effort": "low",
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    payload = _request("/chat/completions", body)
    try:
        choice = payload["choices"][0]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected AMD response shape: {str(payload)[:300]}") from exc
    if choice.get("finish_reason") == "length":
        raise LLMError("Model token limit reached; retry with a larger max_tokens budget")
    content = choice.get("message", {}).get("content")
    if not content:
        raise LLMError("Model returned empty content")
    return content
