"""Central configuration for the tutor backend.

Loads a `.env` file at the repository root (if present) into the environment
without overriding variables that are already set. Every tunable can therefore
be set either in `.env` or in the shell.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = Path(__file__).resolve().parent / "media"


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env()

# ── AMD Token Factory (LLM) ────────────────────────────────────────────────
RADEON_API_KEY = os.environ.get("RADEON_API_KEY", "")
AMD_BASE_URL = os.environ.get("AMD_BASE_URL", "https://developer.amd.com.cn/radeon/api/v1").rstrip("/")
# Exact model ID as listed by GET {AMD_BASE_URL}/models.
AMD_MODEL = os.environ.get("AMD_MODEL", "Gemma-4-31B-IT")

# ── Service URLs ───────────────────────────────────────────────────────────
RECOMMEND_URL = os.environ.get("RECOMMEND_URL", "http://127.0.0.1:8001").rstrip("/")
RAG_URL = os.environ.get("RAG_URL", "http://127.0.0.1:8100").rstrip("/")

# ── Renderer ───────────────────────────────────────────────────────────────
RENDER_TIMEOUT_S = float(os.environ.get("RENDER_TIMEOUT_S", "240"))


class MissingAPIKeyError(RuntimeError):
    """Raised when RADEON_API_KEY is not configured."""


def require_api_key() -> str:
    key = os.environ.get("RADEON_API_KEY") or RADEON_API_KEY
    if not key:
        raise MissingAPIKeyError(
            "RADEON_API_KEY is not set. Add it to the .env file at the "
            "repository root (RADEON_API_KEY=...) or export it in your shell, "
            "then restart the server."
        )
    return key
