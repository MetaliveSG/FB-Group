#!/usr/bin/env sh
# Container entrypoint: apply migrations, optionally seed, then serve.
set -e

echo "[start] applying database migrations..."
alembic upgrade head

if [ "${SEED_ON_START:-0}" = "1" ]; then
  echo "[start] seeding demo data (idempotent — only if DB is empty)..."
  python -c "from app.seed import seed_if_empty; print('[start] seeded fresh demo data' if seed_if_empty() else '[start] data already present — preserved (tokens stay valid)')" \
    || echo "[start] seed check failed (continuing)"
fi

echo "[start] launching API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
