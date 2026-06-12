"""12-factor settings for the production lab app."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _split_csv(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


@dataclass(slots=True)
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Vietnamese Drug-Law RAG Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-jwt-secret"))

    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    allowed_origins: list[str] = field(default_factory=lambda: _split_csv(os.getenv("ALLOWED_ORIGINS", "*")))

    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
    monthly_budget_usd: float = field(default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0")))
    history_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("HISTORY_TTL_SECONDS", "2592000")))
    max_history_messages: int = field(default_factory=lambda: int(os.getenv("MAX_HISTORY_MESSAGES", "20")))

    def validate(self) -> "Settings":
        if self.environment == "production":
            if self.agent_api_key == "dev-key-change-me":
                raise ValueError("AGENT_API_KEY must be set in production")
            if self.jwt_secret == "dev-jwt-secret":
                raise ValueError("JWT_SECRET must be set in production")
        return self


settings = Settings().validate()
