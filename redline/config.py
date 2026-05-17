"""Central configuration. Loaded once at startup; fail fast on bad config."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The 10 attack categories from the Redline spec.
CATEGORIES: list[str] = [
    "prompt_injection",
    "jailbreak",
    "role_confusion",
    "data_exfiltration",
    "boundary_violation",
    "adversarial_context",
    "chain_manipulation",
    "hallucination_trigger",
    "denial_of_service",
    "social_engineering",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_DIR = REPO_ROOT / "payloads"
CACHE_DIR = Path.home() / ".redline" / "cache"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    redline_request_timeout: float = 10.0
    redline_max_retries: int = 3
    redline_db_path: str = "redline.db"
    redline_demo_mode: bool = False
    redline_max_tests: int | None = None

    @property
    def scorer_backend(self) -> str:
        """Which judge to use. Groq preferred, then Anthropic, else regex."""
        if self.groq_api_key:
            return "groq"
        if self.anthropic_api_key:
            return "anthropic"
        return "regex"


settings = Settings()
CACHE_DIR.mkdir(parents=True, exist_ok=True)
