# Day 12 - Productionized Group RAG Agent

This is the production deployment of the Vietnamese drug-law RAG chatbot from
`Morpho7137/2A202600677_Nguyen-Anh-Kiet`, adapted for the Day 12 assignment.

## Production Features

- Group-project BM25 retrieval over the checked-in legal/news index
- Optional OpenAI generation with a cited local fallback
- `POST /chat` compatibility with the original group API
- `POST /ask` with Redis-backed server-side conversation history
- API key authentication, rate limiting, and monthly cost guard
- Health/readiness endpoints, structured logs, and graceful shutdown
- Multi-stage non-root Docker image
- Render Blueprint with free web and Redis services

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","question":"Quy dinh ve cai nghien ma tuy la gi?"}'
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## Deployment

The repository-level `render.yaml` deploys `day12-agent` and `day12-redis`.

Public API: `https://day12-agent-pjde.onrender.com`

Free Render instances can take about 50 seconds to wake after inactivity.

## Verification

```bash
python check_production_ready.py
```
