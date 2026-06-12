# Lab 12 - Complete Production Agent

This folder contains the final production-ready version of the Day 12 lab.

## What it includes

- Multi-stage Docker image with a non-root runtime user
- Redis-backed conversation history, rate limiting, and monthly cost tracking
- `GET /health` and `GET /ready`
- API key authentication
- Structured JSON logs
- Graceful shutdown handling
- Render and Railway deployment configs

## Local run

```bash
cp .env.example .env
docker compose up --build
```

Health check:

```bash
curl http://localhost/health
```

Agent call:

```bash
curl -X POST http://localhost/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"What is deployment?"}'
```

## Repository layout

```text
06-lab-complete/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── storage.py
│   ├── rate_limiter.py
│   └── cost_guard.py
├── utils/
│   └── mock_llm.py
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── render.yaml
├── .env.example
└── check_production_ready.py
```

## Deployment

- Railway uses the Dockerfile in this folder and `railway.toml`.
- Render uses `render.yaml` with a web service and a Redis service.

## Readiness check

```bash
python check_production_ready.py
```

The checker validates the expected files and the key production behaviors in source.

