# Business Continuity / Disaster Recovery (Module 12)

> PoC scope: we **implement** the simple, practical pieces and **document** what full
> production BC/DR would require. We deliberately do not over-build enterprise
> infrastructure for a PoC.

## Implemented in the PoC
- **Docker Compose local stack** with Postgres healthcheck + named volume.
- **Health endpoint** `/health` + container `HEALTHCHECK`.
- **Structured JSON logging** (monitoring-ready; ships cleanly to CloudWatch/OTel).
- **Error handling** — domain errors → safe responses; global handler for unexpected errors (no leakage).
- **DB backup script** — `apps/api/scripts/backup_db.sh` (pg_dump custom format, or SQLite copy).
- **Seed script** — `python -m app.seed` for reproducible demo/test data.
- **Migration rollback** — Alembic up/down (verified).
- **Environment-based config** — 12-factor; no hardcoded secrets.
- **Graceful failure + retry hooks** — WhatsApp/OTP behind a provider abstraction with a `attempts` field on `campaign_messages` for retry; simulated payment failure path issues no rewards (no partial state).

## Retry strategy (mock provider → production)
The WhatsApp/OTP senders sit behind a single `_send` interface. Production wraps it
with exponential backoff + jitter (e.g. 3 attempts: 1s, 4s, 16s), a dead-letter queue
for permanent failures, and idempotency keys so retries never double-send or
double-credit. `campaign_messages.status` (`queued→sent→delivered→failed`) +
`attempts` already model this.

## Targets (proposed)
| Tier | RPO | RTO |
|---|---|---|
| PoC (single node) | last manual backup | manual restore (~30–60 min) |
| Production (target) | ≤ 5 min (PITR) | ≤ 30 min (Multi-AZ failover + redeploy) |

## Production BC/DR — what would be needed
- **Multi-AZ RDS** with automatic failover.
- **Automated backups + Point-In-Time Recovery** (35-day retention) + periodic restore drills.
- **Load balancer (ALB)** + **autoscaling** ECS services across AZs.
- **WAF** in front of CloudFront.
- **Secrets Manager** with rotation.
- **CloudWatch / OpenTelemetry** dashboards + alarms (error rate, latency, saturation, per-tenant anomalies).
- **Blue/green deployment** (CodeDeploy) with automatic rollback on alarm.
- **Disaster recovery runbook** (below).

## DR runbook (outline)
1. **Detect** — alarm (health checks failing, error-rate/latency breach) pages on-call.
2. **Triage** — identify scope: app vs DB vs AZ outage.
3. **DB failure** — promote Multi-AZ standby (automatic) or restore PITR snapshot to a new instance; update Secrets Manager DB endpoint.
4. **App failure** — roll back to last green image (blue/green); scale out if capacity-related.
5. **Verify** — `/health`, smoke the golden capture loop, check ledger integrity (no orphan payments/transactions).
6. **Communicate** — status page + stakeholder update.
7. **Post-mortem** — blameless RCA; add a regression test/alarm.
