"""Lightweight retrieval and generation for the group-project knowledge base."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


INDEX_PATH = Path(__file__).parent.parent / "data" / "index" / "chunks.json"
_CHUNKS: list[dict] | None = None
_BM25: BM25Okapi | None = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _load_index() -> tuple[list[dict], BM25Okapi]:
    global _CHUNKS, _BM25
    if _CHUNKS is None:
        _CHUNKS = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    if _BM25 is None:
        _BM25 = BM25Okapi([_tokenize(item["content"]) for item in _CHUNKS])
    return _CHUNKS, _BM25


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    chunks, index = _load_index()
    scores = index.get_scores(_tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
    results = []
    for idx in ranked:
        score = float(scores[idx])
        if score <= 0:
            continue
        item = chunks[idx]
        metadata = item.get("metadata", {}) or {}
        results.append(
            {
                "content": item.get("content", ""),
                "score": round(score, 6),
                "source": str(metadata.get("source", "group-project-index")),
                "metadata": metadata,
            }
        )
        if len(results) >= top_k:
            break
    return results


def _source_label(item: dict, position: int) -> str:
    metadata = item.get("metadata", {})
    source = Path(str(metadata.get("source", f"Source {position}"))).stem
    year = metadata.get("published_at") or metadata.get("year")
    match = re.search(r"(19|20)\d{2}", str(year or ""))
    return f"{source}, {match.group(0)}" if match else source


def _fallback_answer(results: list[dict]) -> str:
    if not results:
        return "Toi khong the xac minh thong tin nay tu nguon hien co."
    paragraphs = []
    for position, item in enumerate(results[:3], 1):
        text = re.sub(r"\s+", " ", item["content"]).strip()
        excerpt = text[:500].rsplit(" ", 1)[0] if len(text) > 500 else text
        paragraphs.append(f"{excerpt} [{_source_label(item, position)}]")
    return "\n\n".join(paragraphs)


def _openai_answer(query: str, history: list[dict], results: list[dict]) -> str:
    from openai import OpenAI

    context = "\n\n".join(
        f"[{_source_label(item, position)}]\n{item['content']}"
        for position, item in enumerate(results, 1)
    )
    recent_history = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')}" for item in history[-6:]
    )
    prompt = (
        "Tra loi bang tieng Viet, chi dung thong tin trong context. "
        "Moi khang dinh thuc te phai co trich dan [nguon]. Neu context khong du, noi ro.\n\n"
        f"History:\n{recent_history}\n\nContext:\n{context}\n\nQuestion: {query}"
    )
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content or _fallback_answer(results)


def generate_answer(query: str, history: list[dict] | None = None, top_k: int = 5) -> dict:
    results = retrieve(query, top_k=top_k)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key and "your_" not in api_key.lower() and "xxx" not in api_key.lower():
        try:
            answer = _openai_answer(query, history or [], results)
        except Exception:
            answer = _fallback_answer(results)
    else:
        answer = _fallback_answer(results)
    return {
        "answer": answer,
        "retrieval_source": "bm25-group-project-index" if results else "none",
        "sources": results,
    }
