"""AMD Token Factory client (OpenAI-compatible chat endpoint).

Standard-library + httpx only; no vendor SDK. The API key is mandatory:
every call raises MissingAPIKeyError with setup instructions when absent.
"""
from __future__ import annotations

import httpx

from .config import AMD_BASE_URL, AMD_MODEL, MissingAPIKeyError, require_api_key

TIMEOUT = httpx.Timeout(600.0, connect=15.0)


class LLMError(RuntimeError):
    """Raised when the AMD endpoint fails or returns unusable output."""


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer " + require_api_key(), "Content-Type": "application/json"}


def list_models() -> list[str]:
    """Return available model IDs from the AMD endpoint."""
    try:
        response = httpx.get(AMD_BASE_URL + "/models", headers=_auth_headers(), timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach AMD endpoint {AMD_BASE_URL}: {exc}") from exc
    if response.status_code != 200:
        raise LLMError(f"AMD /models returned HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
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
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        response = httpx.post(
            AMD_BASE_URL + "/chat/completions", headers=_auth_headers(),
            json=body, timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach AMD endpoint {AMD_BASE_URL}: {exc}") from exc
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "unknown")
        raise LLMError(f"AMD endpoint rate-limited (HTTP 429); Retry-After={retry_after}")
    if response.status_code != 200:
        raise LLMError(f"AMD chat/completions returned HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
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
