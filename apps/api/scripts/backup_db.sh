#!/usr/bin/env bash
# Database backup helper.
#   Postgres : pg_dump (custom format, compressed) -> ./backups/
#   SQLite   : file copy
# Usage: DATABASE_URL=... ./scripts/backup_db.sh
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$OUT_DIR"
URL="${DATABASE_URL:-sqlite:///./fbgroup.db}"

if echo "$URL" | grep -q '^sqlite'; then
  FILE="${URL#sqlite:///}"
  cp "$FILE" "$OUT_DIR/fbgroup_${TS}.db"
  echo "SQLite backup -> $OUT_DIR/fbgroup_${TS}.db"
else
  # Strip SQLAlchemy driver suffix (+psycopg) for pg_dump.
  PG_URL="$(echo "$URL" | sed 's/+psycopg//')"
  pg_dump -Fc -d "$PG_URL" -f "$OUT_DIR/fbgroup_${TS}.dump"
  echo "Postgres backup -> $OUT_DIR/fbgroup_${TS}.dump"
  echo "Restore with: pg_restore -d <url> --clean $OUT_DIR/fbgroup_${TS}.dump"
fi
