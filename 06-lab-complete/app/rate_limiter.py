"""Sliding-window rate limiting for the lab app."""

from __future__ import annotations

from app.config import settings
from app.storage import rate_limit_check


def check_rate_limit(user_id: str) -> None:
    rate_limit_check(user_id, settings.rate_limit_per_minute, window_seconds=60)

