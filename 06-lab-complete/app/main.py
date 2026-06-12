"""Production API for the Vietnamese drug-law RAG group project."""

from __future__ import annotations

import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, current_spend, estimate_cost
from app.rag import generate_answer
from app.rate_limiter import check_rate_limit
from app.storage import append_history, load_history, redis_ready


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
async def lifespan(_app: FastAPI):
    global _READY
    log_event("startup", app=settings.app_name, version=settings.app_version)
    _READY = True
    yield
    _READY = False
    log_event("shutdown")


app = FastAPI(
    title=settings.app_name,
    description="Productionized Vietnamese drug-law RAG agent from the group project.",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=10)
    user_id: str = Field(default="anonymous", min_length=1, max_length=128)


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class SourceChunk(BaseModel):
    content: str
    score: float
    source: str
    metadata: dict[str, Any]


class AgentResponse(BaseModel):
    answer: str
    retrieval_source: str
    sources: list[SourceChunk]
    user_id: str
    monthly_spend_usd: float
    timestamp: str


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    started = time.time()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    log_event(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.time() - started) * 1000, 1),
    )
    return response


@app.get("/")
def root() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "agent": "Vietnamese Drug-Law RAG",
        "endpoints": {
            "chat": "POST /chat",
            "ask": "POST /ask",
            "health": "GET /health",
            "ready": "GET /ready",
            "docs": "GET /docs",
        },
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready() -> dict[str, object]:
    if not _READY:
        raise HTTPException(status_code=503, detail="Application not ready")
    return {"ready": True, "redis": redis_ready()}


def _run_agent(user_id: str, question: str, history: list[dict], top_k: int) -> AgentResponse:
    try:
        check_rate_limit(user_id)
    except ValueError as exc:
        if str(exc) == "rate_limited":
            raise HTTPException(status_code=429, detail="Rate limit exceeded") from exc
        raise

    result = generate_answer(question, history=history, top_k=top_k)
    answer = result["answer"]
    cost = estimate_cost(question, answer)
    try:
        check_budget(user_id, cost)
    except ValueError as exc:
        if str(exc) == "budget_exceeded":
            raise HTTPException(status_code=402, detail="Monthly budget exceeded") from exc
        raise

    append_history(user_id, "user", question)
    append_history(user_id, "assistant", answer)
    log_event("agent_call", user_id=user_id, question_len=len(question), source=result["retrieval_source"])

    return AgentResponse(
        answer=answer,
        retrieval_source=result["retrieval_source"],
        sources=result["sources"],
        user_id=user_id,
        monthly_spend_usd=round(current_spend(user_id), 6),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/chat", response_model=AgentResponse)
def chat(body: ChatRequest, _api_key: str = Depends(verify_api_key)) -> AgentResponse:
    history = [{"role": item.role, "content": item.content} for item in body.history]
    return _run_agent(body.user_id, body.message, history, body.top_k)


@app.post("/ask", response_model=AgentResponse)
def ask(body: AskRequest, _api_key: str = Depends(verify_api_key)) -> AgentResponse:
    return _run_agent(body.user_id, body.question, load_history(body.user_id), body.top_k)


@app.get("/chat/{user_id}/history")
def get_history(user_id: str, _api_key: str = Depends(verify_api_key)) -> dict[str, object]:
    history = load_history(user_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"user_id": user_id, "messages": history, "count": len(history)}


@app.delete("/chat/{user_id}")
def delete_history_endpoint(user_id: str, _api_key: str = Depends(verify_api_key)) -> dict[str, str]:
    from app.storage import delete_history

    delete_history(user_id)
    return {"deleted": user_id}


def _handle_sigterm(signum, _frame) -> None:
    log_event("signal", signum=signum)


signal.signal(signal.SIGTERM, _handle_sigterm)
