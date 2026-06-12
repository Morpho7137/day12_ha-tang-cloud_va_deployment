"""Monthly cost guard for the lab app."""

from __future__ import annotations

from app.config import settings
from app.storage import budget_check_and_add, get_budget_spend


def estimate_cost(question: str, answer: str) -> float:
    input_tokens = max(1, len(question.split()) * 2)
    output_tokens = max(1, len(answer.split()) * 2)
    return round((input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006, 6)


def check_budget(user_id: str, estimated_cost: float) -> None:
    budget_check_and_add(user_id, estimated_cost, settings.monthly_budget_usd)


def current_spend(user_id: str) -> float:
    return get_budget_spend(user_id)

