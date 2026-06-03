#!/usr/bin/env sh
# Container entrypoint: apply migrations, optionally seed, then serve.
set -e

echo "[start] applying database migrations..."
alembic upgrade head

# Always sync RBAC (idempotent) so new roles/permissions reach an already-seeded DB that
# seed_if_empty would skip — independent of SEED_ON_START / whether demo data exists.
echo "[start] syncing roles + permissions (idempotent)..."
python -c "from app.seed import ensure_rbac; print('[start] RBAC synced:', ensure_rbac(), 'roles')" \
  || echo "[start] RBAC sync failed (continuing)"

if [ "${SEED_ON_START:-0}" = "1" ]; then
  echo "[start] seeding demo data (idempotent — only if DB is empty)..."
  python -c "from app.seed import seed_if_empty; print('[start] seeded fresh demo data' if seed_if_empty() else '[start] data already present — preserved (tokens stay valid)')" \
    || echo "[start] seed check failed (continuing)"
fi

if [ "${SEED_BREADTALK:-0}" = "1" ]; then
  # Enterprise org-tree demo (depth 0→4, two merchants under one Enterprise). Idempotent
  # upsert-by-id, independent of SEED_ON_START, so it reaches an already-seeded DB too.
  echo "[start] seeding BreadTalk enterprise org tree (idempotent)..."
  python -m app.seed_breadtalk || echo "[start] breadtalk seed failed (continuing)"
fi

echo "[start] launching API on :8000"
# --no-access-log: our RequestLoggingMiddleware emits the (JSON, redacted) access
# log to file + console, so uvicorn's plain-text one would just duplicate it.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
