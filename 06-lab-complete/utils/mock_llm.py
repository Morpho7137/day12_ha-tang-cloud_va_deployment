"""Local copy of the repo mock LLM for the complete lab project."""

from __future__ import annotations

import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock AI response. In production, this would come from a hosted model.",
        "The agent is running correctly. Ask another question.",
        "Your request was accepted by the demo agent.",
    ],
    "docker": ["Containers package an app so it runs the same everywhere."],
    "deploy": ["Deployment moves code from your machine to a public service."],
    "health": ["The agent is healthy and operational."],
}


def _extract_name(history: list[dict]) -> str | None:
    for item in reversed(history):
        content = str(item.get("content", ""))
        lower = content.lower()
        if "my name is" in lower:
            start = lower.index("my name is") + len("my name is")
            tail = content[start:].strip(" .!?,")
            if tail:
                return tail.split()[0]
    return None


def ask(question: str, delay: float = 0.1, history: list[dict] | None = None) -> str:
    time.sleep(delay + random.uniform(0, 0.05))
    history = history or []
    question_lower = question.lower()

    if "what is my name" in question_lower:
        name = _extract_name(history)
        if name:
            return f"Your name is {name}."

    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)

    return random.choice(MOCK_RESPONSES["default"])


def ask_stream(question: str):
    response = ask(question)
    for word in response.split():
        time.sleep(0.05)
        yield word + " "
