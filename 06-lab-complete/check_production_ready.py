"""Production readiness checks for the Day 12 lab."""

from __future__ import annotations

import os
import sys


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "OK" if passed else "FAIL"
    print(f"  {icon} {name}" + (f" - {detail}" if detail else ""))
    return {"name": name, "passed": passed}


def file_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def run_checks() -> bool:
    base = os.path.dirname(__file__)
    results: list[dict] = []

    print("=" * 60)
    print("Production Readiness Check - Day 12 Lab")
    print("=" * 60)

    print("\nRequired files")
    required = [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        ".env.example",
        "requirements.txt",
        "render.yaml",
    ]
    for name in required:
        results.append(check(f"{name} exists", os.path.exists(os.path.join(base, name))))

    print("\nSecurity")
    gitignore_paths = [os.path.join(base, ".gitignore"), os.path.join(base, "..", ".gitignore")]
    env_ignored = False
    for path in gitignore_paths:
        if os.path.exists(path) and ".env" in file_text(path):
            env_ignored = True
            break
    results.append(check(".env ignored", env_ignored))

    main_py = os.path.join(base, "app", "main.py")
    config_py = os.path.join(base, "app", "config.py")
    if os.path.exists(main_py):
        main_text = file_text(main_py)
        results.append(check("/health endpoint", '"/health"' in main_text or "'/health'" in main_text))
        results.append(check("/ready endpoint", '"/ready"' in main_text or "'/ready'" in main_text))
        results.append(check("API key auth", "verify_api_key" in main_text))
        results.append(check("Rate limiting", "check_rate_limit" in main_text))
        results.append(check("Cost guard", "check_budget" in main_text))
        results.append(check("Conversation history", "append_history" in main_text and "load_history" in main_text))
        results.append(check("Group RAG endpoint", '"/chat"' in main_text and "generate_answer" in main_text))
        results.append(check("Graceful shutdown", "SIGTERM" in main_text))
        results.append(check("JSON logging", "json.dumps" in main_text))
    else:
        results.append(check("app/main.py exists", False))

    if os.path.exists(config_py):
        config_text = file_text(config_py)
        results.append(check("Env config", "os.getenv" in config_text))
        results.append(check("Monthly budget default", "MONTHLY_BUDGET_USD" in config_text))
        results.append(check("Rate limit default", "RATE_LIMIT_PER_MINUTE" in config_text))

    rag_py = os.path.join(base, "app", "rag.py")
    if os.path.exists(rag_py):
        rag_text = file_text(rag_py)
        results.append(check("BM25 retrieval", "BM25Okapi" in rag_text))
        results.append(check("Cited fallback", "_fallback_answer" in rag_text))
    results.append(
        check(
            "Group-project index",
            os.path.exists(os.path.join(base, "data", "index", "chunks.json")),
        )
    )

    print("\nDocker")
    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        docker_text = file_text(dockerfile)
        results.append(check("Multi-stage build", "AS builder" in docker_text and "AS runtime" in docker_text))
        results.append(check("Non-root user", "USER agent" in docker_text))
        results.append(check("HEALTHCHECK", "HEALTHCHECK" in docker_text))
        results.append(check("Slim base", "python:3.11-slim" in docker_text))

    dockerignore = os.path.join(base, ".dockerignore")
    if os.path.exists(dockerignore):
        ignore_text = file_text(dockerignore)
        results.append(check(".env ignored in docker", ".env" in ignore_text))
        results.append(check("pycache ignored", "__pycache__" in ignore_text))

    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    pct = round((passed / total) * 100) if total else 0

    print("\n" + "=" * 60)
    print(f"Result: {passed}/{total} checks passed ({pct}%)")
    print("=" * 60)
    return pct == 100


if __name__ == "__main__":
    sys.exit(0 if run_checks() else 1)
