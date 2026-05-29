"""Standalone CLI: add Merchant 4 'Kampong Eats' to the configured DATABASE_URL.

Idempotent — safe to run against the live Postgres without wiping data. Joins
the existing SG Eats coalition if present.

Run:  python -m app.seed_kampong
"""
from __future__ import annotations

from app.db.session import SessionLocal
from app.seed import seed_kampong


def main() -> None:
    with SessionLocal() as db:
        result = seed_kampong(db)
    print("Kampong Eats seed:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
