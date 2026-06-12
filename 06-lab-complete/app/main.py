"""Production-ready Day 12 agent."""

from __future__ import annotations

import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, current_spend, estimate_cost
from app.rate_limiter import check_rate_limit
from app.storage import append_history, load_history, redis_ready
from utils.mock_llm import ask as llm_ask


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_READY = False


def log_event(event: str, **payload: object) -> None:
    record = {"event": event, "ts": datetime.now(timezone.utc).isoformat(), **payload}
    logger.info(json.dumps(record, ensure_ascii=True))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _READY
    log_event("startup", app=settings.app_name, version=settings.app_version, env=settings.environment)
    _READY = True
    yield
    _READY = False
    log_event("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if settings.allowed_origins != ["*"] else ["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    history_count: int
    monthly_spend_usd: float
    model: str
    timestamp: str


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        log_event("request_error", path=request.url.path, error=str(exc))
        raise
    duration_ms = round((time.time() - start) * 1000, 1)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    log_event(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {"ask": "POST /ask", "health": "GET /health", "ready": "GET /ready"},
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if not _READY:
        raise HTTPException(status_code=503, detail="Not ready")
    if not redis_ready():
        raise HTTPException(status_code=503, detail="Redis not ready")
    return {"ready": True}


@app.post("/ask", response_model=AskResponse)
def ask_agent(
    body: AskRequest,
    _api_key: str = Depends(verify_api_key),
):
    try:
        check_rate_limit(body.user_id)
    except ValueError as exc:
        if str(exc) == "rate_limited":
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        raise

    history = append_history(body.user_id, "user", body.question)
    prior_history = load_history(body.user_id)
    answer = llm_ask(body.question, history=prior_history)
    cost = estimate_cost(body.question, answer)

    try:
        check_budget(body.user_id, cost)
    except ValueError as exc:
        if str(exc) == "budget_exceeded":
            raise HTTPException(status_code=402, detail="Monthly budget exceeded")
        raise

    append_history(body.user_id, "assistant", answer)

    log_event(
        "ask",
        user_id=body.user_id,
        question_len=len(body.question),
        history_count=len(history),
        est_cost=cost,
    )

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        history_count=len(history),
        monthly_spend_usd=round(current_spend(body.user_id), 6),
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/chat/{user_id}/history")
def get_history(user_id: str, _api_key: str = Depends(verify_api_key)):
    history = load_history(user_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"user_id": user_id, "messages": history, "count": len(history)}


@app.delete("/chat/{user_id}")
def delete_history_endpoint(user_id: str, _api_key: str = Depends(verify_api_key)):
    from app.storage import delete_history

    delete_history(user_id)
    return {"deleted": user_id}


def _handle_sigterm(signum, _frame):
    log_event("signal", signum=signum)


signal.signal(signal.SIGTERM, _handle_sigterm)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )

