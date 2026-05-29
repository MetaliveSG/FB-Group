-- ─────────────────────────────────────────────────────────────────────────
-- FB Group diagnostic SQL. Run against the local Docker Postgres (`fbgroup`).
--   VS Code:  open file → connect "FB Group (Docker Postgres)" in SQLTools → run block
--   Terminal: docker-compose -f infra/docker-compose.yml exec -T db \
--               psql -U fbgroup -d fbgroup -f - < queries/<file>.sql
-- Money cols are numeric; timestamps are naive UTC (SG = UTC+8).
-- ─────────────────────────────────────────────────────────────────────────

-- Customer lookup + loyalty snapshot
-- Edit the search term below (matches phone / email / full name, case-insensitive).
\set q '%'

-- 1) Find matching customers
SELECT id, full_name, phone, email, birthday, marketing_consent, is_active, created_at
FROM customers
WHERE full_name ILIKE :'q' OR phone ILIKE :'q' OR email ILIKE :'q'
ORDER BY created_at DESC
LIMIT 25;

-- 2) Loyalty accounts for matching customers (one account per scope: merchant/coalition)
SELECT c.full_name, c.phone,
       la.scope_type, la.scope_id,
       la.tier, la.points_balance, la.lifetime_points,
       la.visit_count, la.total_spend,
       la.first_visit_at, la.last_visit_at
FROM loyalty_accounts la
JOIN customers c ON c.id = la.customer_id
WHERE c.full_name ILIKE :'q' OR c.phone ILIKE :'q' OR c.email ILIKE :'q'
ORDER BY la.total_spend DESC;

-- 3) Recent orders for matching customers
SELECT c.full_name, m.name AS merchant, o.status, o.total,
       o.placed_at, o.completed_at, o.created_at
FROM orders o
JOIN customers c ON c.id = o.customer_id
JOIN merchants m ON m.id = o.merchant_id
WHERE c.full_name ILIKE :'q' OR c.phone ILIKE :'q' OR c.email ILIKE :'q'
ORDER BY o.created_at DESC
LIMIT 50;
