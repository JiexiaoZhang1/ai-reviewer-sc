"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal


DEFAULT_OPENAI_MODEL = "gpt-5"
PLACEHOLDER_SENTINEL = "REPLACE_WITH_OPENAI_API_KEY"
OPENAI_API_KEY_PLACEHOLDER = "REPLACE_WITH_OPENAI_API_KEY"


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    openai_api_key: str
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_base_url: str | None = None
    max_candidate_files: int = 200
    max_file_bytes: int = 200_000
    max_tokens_per_chunk: int = 1800
    max_prompt_tokens: int = 10_000
    summarize_temperature: float = 0.1
    report_temperature: float = 0.0
    environment: Literal["development", "production"] = "development"


def _get_required_env(name: str, *, default: str | None = None) -> str:
    env_value = os.getenv(name)
    if env_value:
        return env_value
    if default:
        if default == PLACEHOLDER_SENTINEL:
            raise RuntimeError(
                f"Missing required environment variable '{name}'. "
                "Set it before starting the service, or update "
                "`OPENAI_API_KEY_PLACEHOLDER` in app/config.py with your key."
            )
        return default

    raise RuntimeError(
        f"Missing required environment variable '{name}'. "
        "Set it before starting the service."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return memoized application settings."""

    return Settings(
        openai_api_key=_get_required_env(
            "OPENAI_API_KEY",
            default=OPENAI_API_KEY_PLACEHOLDER,
        ),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        max_candidate_files=int(os.getenv("MAX_CANDIDATE_FILES", "200")),
        max_file_bytes=int(os.getenv("MAX_FILE_BYTES", "200000")),
        max_tokens_per_chunk=int(os.getenv("MAX_TOKENS_PER_CHUNK", "1800")),
        max_prompt_tokens=int(os.getenv("MAX_PROMPT_TOKENS", "10000")),
        summarize_temperature=float(os.getenv("SUMMARIZE_TEMPERATURE", "0.1")),
        report_temperature=float(os.getenv("REPORT_TEMPERATURE", "0.0")),
        environment=os.getenv("ENVIRONMENT", "development"),  # type: ignore[arg-type]
    )
