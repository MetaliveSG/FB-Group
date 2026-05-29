# Deployment

## Local (Docker Compose)
```bash
docker compose -f infra/docker-compose.yml up --build
```
- `db` — Postgres 16 (healthcheck `pg_isready`, named volume `pgdata`)
- `api` — FastAPI; entrypoint runs `alembic upgrade head` then (if `SEED_ON_START=1`) seeds, then `uvicorn`. Container `HEALTHCHECK` hits `/health`.
- `web` — Next.js, `NEXT_PUBLIC_API_BASE=http://localhost:8000`

Config is env-based (12-factor). Copy `apps/api/.env.example` → `.env` and set a real
`JWT_SECRET` (`openssl rand -hex 32`).

## Migrations
```bash
alembic upgrade head            # apply
alembic downgrade -1            # roll back one revision
alembic revision --autogenerate -m "msg"   # new migration after model changes
```
Migration chain: **7 revisions** (initial schema → rewards catalog/wheel/tasks/owner →
redemption voucher_code → opportunities/activities → pipeline_type + merchant settings →
jackpot_prizes → customers.gender), single head, verified to upgrade (40 tables) and downgrade cleanly.
On container start,
`alembic upgrade head` runs, then the seed runs **idempotently** (only if the DB is empty,
so restarts don't wipe data / invalidate tokens).

## AWS-ready blueprint (target production topology)
```
Route53 ─ CloudFront(WAF) ─ ALB ─┬─ ECS Fargate: web (Next.js)
                                 └─ ECS Fargate: api (FastAPI)  ──► RDS PostgreSQL (Multi-AZ)
                                                                ──► ElastiCache Redis (rate limit, OTP, cache)
   Secrets Manager (JWT, DB creds) · ECR (images) · CloudWatch + OpenTelemetry (logs/traces/metrics)
   S3 (assets, db dump archive) · SES/SNS or Twilio/Meta (real OTP + WhatsApp)
```

### Mapping PoC → AWS
| PoC component | AWS production |
|---|---|
| docker-compose api/web | ECS Fargate services behind ALB, autoscaling on CPU/RPS |
| Postgres container | RDS PostgreSQL Multi-AZ, automated backups + PITR |
| in-process rate limiter / OTP store | ElastiCache (Redis) |
| `.env` secrets | Secrets Manager + IAM task roles (no secrets in env files) |
| structured JSON logs to stdout | CloudWatch Logs + OpenTelemetry collector |
| mock WhatsApp/OTP | SNS/SES or Twilio/Meta WhatsApp Business API |
| simulated payments | Stripe / NETS / PayNow PSP integration |
| local image build | ECR + CI/CD (GitHub Actions) blue/green via CodeDeploy |

### Hardening checklist for production
- TLS everywhere (ACM certs on CloudFront + ALB); HSTS already set by API.
- WAF rules (rate-based, common rule set) in front of CloudFront.
- Least-privilege IAM task roles; DB user scoped to app schema.
- Image scanning (ECR) + dependency scanning in CI.
- Per-tenant log/metric dimensions for isolation alerting.
