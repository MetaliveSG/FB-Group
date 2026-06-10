# Deployment

## Local (Docker Compose)
```bash
docker-compose -f infra/docker-compose.yml up --build   # this machine uses docker-compose v1 (hyphenated)
```
- `db` — Postgres 16 (healthcheck `pg_isready`, named volume `pgdata`); host `:5432`
- `api` — FastAPI; entrypoint runs `alembic upgrade head` then (if `SEED_ON_START=1`) seeds, then `uvicorn`. Container `HEALTHCHECK` hits `/health`. Host `:8000`.
- `web` — Next.js, `NEXT_PUBLIC_API_BASE=http://localhost:8000`; mapped to host **`:3001`** (host 3000 was taken)
- **Seeding is OFF by default** (`SEED_ON_START=0`): the DB boots clean; provision demo data with `python -m app.seed_demo_merchants` (Breadtalk/Pepper Lunch) or `python -m app.seed_kampong` (SG-local).

Config is env-based (12-factor). Copy `apps/api/.env.example` → `.env` and set a real
`JWT_SECRET` (`openssl rand -hex 32`).

## Migrations
```bash
alembic upgrade head            # apply
alembic downgrade -1            # roll back one revision
alembic revision --autogenerate -m "msg"   # new migration after model changes
```
Migration chain: **32 revisions**, single head (`h2i3serviceopts`), verified to upgrade from empty (45 tables);
migrations are **roll-forward** (CI checks upgrade-from-empty + model-drift, no downgrade-to-base). The
chain self-documents in `apps/api/alembic/versions/` (`alembic history`) — not hand-listed here (it drifts).
On container start `alembic upgrade head` runs; seeding is **off by default** (`SEED_ON_START=0` → clean DB,
restarts don't wipe data / invalidate tokens; provision via the ensure-scripts).

## AWS-ready blueprint (target production topology — NOT built)
> **Aspirational.** No IaC exists in the repo (no Terraform/CDK/CloudFormation; only
> `infra/docker-compose.yml` + a single `.github/workflows/ci.yml`). Local-first per the roadmap;
> cloud is deferred. This is the *target*, not a deployment guide you can run today. This doc is the
> **single canonical home** for the AWS topology — `bc-dr.md` and `security.md` reference it rather than
> restating it.
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
