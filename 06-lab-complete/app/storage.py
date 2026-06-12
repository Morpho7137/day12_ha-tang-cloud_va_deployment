"""Redis-backed storage helpers with a safe local fallback."""

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone

import redis

from app.config import settings


def current_month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def current_minute_window(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    return int(now.timestamp() // 60)


@dataclass(slots=True)
class StorageState:
    redis_client: redis.Redis | None
    in_memory: dict[str, object]
    last_failed_at: float = 0.0


_state = StorageState(redis_client=None, in_memory={})


def get_redis() -> redis.Redis | None:
    if _state.redis_client is not None:
        return _state.redis_client
    if time.monotonic() - _state.last_failed_at < 5:
        return None
    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        )
        client.ping()
        _state.redis_client = client
        return client
    except Exception:
        _state.redis_client = None
        _state.last_failed_at = time.monotonic()
        return None


def redis_ready() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False


def save_history(user_id: str, history: list[dict], ttl_seconds: int | None = None) -> None:
    ttl_seconds = ttl_seconds or settings.history_ttl_seconds
    client = get_redis()
    payload = json.dumps(history, ensure_ascii=True)
    if client is not None:
        client.setex(f"history:{user_id}", ttl_seconds, payload)
        return
    _state.in_memory[f"history:{user_id}"] = history


def load_history(user_id: str) -> list[dict]:
    client = get_redis()
    if client is not None:
        raw = client.get(f"history:{user_id}")
        return json.loads(raw) if raw else []
    return list(_state.in_memory.get(f"history:{user_id}", []))


def append_history(user_id: str, role: str, content: str) -> list[dict]:
    history = load_history(user_id)
    history.append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    if len(history) > settings.max_history_messages:
        history = history[-settings.max_history_messages :]
    save_history(user_id, history)
    return history


def delete_history(user_id: str) -> None:
    client = get_redis()
    if client is not None:
        client.delete(f"history:{user_id}")
        return
    _state.in_memory.pop(f"history:{user_id}", None)


def _fallback_rate_bucket(user_id: str) -> deque[float]:
    key = f"rate:{user_id}"
    bucket = _state.in_memory.get(key)
    if bucket is None:
        bucket = deque()
        _state.in_memory[key] = bucket
    return bucket  # type: ignore[return-value]


def rate_limit_check(user_id: str, limit: int, window_seconds: int = 60) -> None:
    client = get_redis()
    if client is not None:
        key = f"rate:{user_id}"
        now = datetime.now(timezone.utc).timestamp()
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zcard(key)
        _, count = pipe.execute()
        if int(count) >= limit:
            raise ValueError("rate_limited")
        pipe = client.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 5)
        pipe.execute()
        return

    bucket = _fallback_rate_bucket(user_id)
    now = datetime.now(timezone.utc).timestamp()
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise ValueError("rate_limited")
    bucket.append(now)


def budget_check_and_add(user_id: str, amount: float, monthly_budget_usd: float) -> None:
    client = get_redis()
    month = current_month_key()
    key = f"budget:{user_id}:{month}"
    if client is not None:
        current = float(client.get(key) or 0.0)
        if current + amount > monthly_budget_usd:
            raise ValueError("budget_exceeded")
        pipe = client.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, 35 * 24 * 3600)
        pipe.execute()
        return

    current = float(_state.in_memory.get(key, 0.0))
    if current + amount > monthly_budget_usd:
        raise ValueError("budget_exceeded")
    _state.in_memory[key] = current + amount


def get_budget_spend(user_id: str) -> float:
    client = get_redis()
    key = f"budget:{user_id}:{current_month_key()}"
    if client is not None:
        return float(client.get(key) or 0.0)
    return float(_state.in_memory.get(key, 0.0))
