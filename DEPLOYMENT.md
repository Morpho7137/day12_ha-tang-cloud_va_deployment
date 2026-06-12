# Deployment Information

## Public URL

Pending Render deployment.

## Platform

Render

## Service Layout

- Web service: `day12-agent`
- Redis service: `day12-redis`

## Environment Variables

- `ENVIRONMENT=production`
- `APP_VERSION=1.0.0`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10.0`
- `AGENT_API_KEY`
- `JWT_SECRET`
- `REDIS_URL`

## Local Verification

```bash
cd 06-lab-complete
cp .env.example .env
docker compose up --build
curl http://localhost/health
curl -X POST http://localhost/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

## Cloud Verification

```bash
curl https://<your-render-service>.onrender.com/health
curl -X POST https://<your-render-service>.onrender.com/ask \
  -H "X-API-Key: <render-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

## Screenshots

- `screenshots/render-dashboard.png`
- `screenshots/service-running.png`
- `screenshots/health-check.png`
- `screenshots/ask-test.png`

