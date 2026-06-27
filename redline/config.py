"""Central configuration. Loaded once at startup; fail fast on bad config."""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMCreds(NamedTuple):
    """Credentials for an OpenAI-compatible /chat/completions endpoint."""

    name: str
    base_url: str
    api_key: str
    model: str

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

    # Primary LLM-judge scorer (Fireworks AI, OpenAI-compatible).
    fireworks_api_key: str = ""
    fireworks_model: str = "accounts/fireworks/models/gpt-oss-120b"
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_base_url: str = "https://api.anthropic.com/v1/messages"

    openai_model: str = "gpt-3.5-turbo"

    redline_request_timeout: float = 10.0
    redline_max_retries: int = 3
    redline_db_path: str = "redline.db"
    redline_demo_mode: bool = False
    redline_max_tests: int | None = None

    # Observability (both optional; absent backend == no-op)
    redline_metrics_enabled: bool = True
    otel_exporter_otlp_endpoint: str = ""

    # GitHub App / Actions integration
    github_token: str = ""
    github_webhook_secret: str = ""

    # GitHub OAuth (user login). Works for both GitHub OAuth Apps and
    # GitHub Apps — both expose /login/oauth/authorize. Leave empty to
    # disable the login feature (the rest of the app still works).
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = (
        "http://localhost:5173/api/auth/github/callback"
    )
    # Where the user lands after a successful login (frontend route).
    auth_post_login_redirect: str = "http://localhost:5173/dashboard"

    @property
    def llm(self) -> LLMCreds | None:
        """Active OpenAI-compatible LLM provider, or None if none is configured.

        Fireworks is preferred, then Groq. Both share the same request shape,
        so the scorer/payload agents can use whichever is returned here.
        """
        if self.fireworks_api_key:
            return LLMCreds("fireworks", self.fireworks_base_url,
                            self.fireworks_api_key, self.fireworks_model)
        if self.groq_api_key:
            return LLMCreds("groq", self.groq_base_url,
                            self.groq_api_key, self.groq_model)
        return None

    @property
    def scorer_backend(self) -> str:
        """Which judge to use. Fireworks/Groq preferred, then Anthropic, else regex."""
        if self.llm:
            return self.llm.name
        if self.anthropic_api_key:
            return "anthropic"
        return "regex"


settings = Settings()
CACHE_DIR.mkdir(parents=True, exist_ok=True)
