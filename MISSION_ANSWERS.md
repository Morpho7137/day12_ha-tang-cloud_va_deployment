# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. Hardcoded API key.
2. Hardcoded database URL with password.
3. Debug/reload mode enabled.
4. Fixed host set to `localhost`.
5. Fixed port `8000` instead of `PORT` env var.
6. No health check endpoint.
7. Secret value is logged.

### Exercise 1.2: Basic version run

- The basic app runs locally with `python app.py`.
- `POST /ask` returns a mock answer from `utils/mock_llm.py`.
- It works, but it is not production-safe because config and secrets are embedded in code.

### Exercise 1.3: Comparison table

| Feature | Basic | Advanced | Why it matters |
|---|---|---|---|
| Config | Hardcoded | Environment variables | Keeps secrets out of code and supports multiple deploy targets |
| Health check | None | `/health` endpoint | Lets the platform detect and restart unhealthy processes |
| Logging | `print()` | Structured logging | Easier to search and aggregate in cloud logs |
| Shutdown | Immediate | Graceful shutdown | Prevents request loss during deploy/restart |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11-slim`.
2. Working directory: `/app`.
3. Copy `requirements.txt` first so Docker can cache dependency layers.
4. `CMD` is the default command and can be overridden; `ENTRYPOINT` is more fixed.

### Exercise 2.2: Build and run basic container

- The develop Dockerfile builds a single-stage Python image.
- The container exposes the same mock agent endpoint as local Python.

### Exercise 2.3: Multi-stage build benefits

- Builder stage installs dependencies and build tools.
- Runtime stage copies only installed packages and app code.
- This reduces image size and attack surface.

### Exercise 2.4: Architecture diagram

```text
Client -> Nginx -> Agent -> Redis
```

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- Deployment target: Railway.
- Public URL: `https://<your-railway-service>.up.railway.app`
- Health endpoint: `GET /health`
- Agent endpoint: `POST /ask`

### Exercise 3.2: Render deployment

- Render uses `render.yaml` as the blueprint.
- Render creates a web service and a Redis service.
- `REDIS_URL` is injected from the Redis service.

### Exercise 3.3: Cloud Run

- `service.yaml` defines the Cloud Run service.
- `cloudbuild.yaml` defines test, build, push, and deploy steps.

## Part 4: API Security

### Exercise 4.1: API key authentication

- API key is checked in `04-api-gateway/develop/app.py` with `X-API-Key`.
- Missing key returns `401`.
- Invalid key returns `403`.
- Key rotation is done by changing the env var and redeploying.

### Exercise 4.2: JWT authentication

- JWT token is created in `04-api-gateway/production/auth.py`.
- `student / demo123` and `teacher / teach456` issue signed tokens.
- `Authorization: Bearer <token>` is used on protected requests.

### Exercise 4.3: Rate limiting

- The production example uses a sliding-window counter.
- Limit is 10 requests per minute for normal users and 100 for admin.
- The admin bucket is separate from the user bucket.

### Exercise 4.4: Cost guard

- Monthly or daily cost is tracked in Redis or in-memory demo code.
- Requests are rejected once the budget threshold is exceeded.
- In the final app, the limit is `MONTHLY_BUDGET_USD=10.0`.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

- `GET /health` is the liveness probe.
- `GET /ready` is the readiness probe.
- `/ready` checks dependency availability before accepting traffic.

### Exercise 5.2: Graceful shutdown

- SIGTERM is handled through application shutdown lifecycle.
- The app logs shutdown and stops taking new traffic before exit.

### Exercise 5.3: Stateless design

- Session history is stored in Redis, not process memory.
- Any instance can serve the next request.
- This is required for horizontal scaling.

### Exercise 5.4: Load balancing

- Nginx forwards requests to the `agent` service.
- Docker Compose can scale the agent service with multiple replicas.

### Exercise 5.5: Test stateless design

- Create a conversation.
- Restart or replace one instance.
- Continue the conversation from another instance.
- History remains available because Redis stores the state.

## Part 6: Final Project

### Functional requirements

- `POST /ask` accepts `user_id` and `question`.
- Conversation history is persisted in Redis.
- Mock LLM can answer follow-up questions using history.

### Non-functional requirements

- Multi-stage Dockerfile.
- Env-based config.
- API key auth.
- Rate limiting.
- Monthly cost guard.
- Health and readiness checks.
- Graceful shutdown.
- Stateless design.
- Deployment files for Railway and Render.

