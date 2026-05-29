-- Per-merchant KPI overview (mirrors the operator console at a glance)

-- 1) Headline KPIs per merchant.
-- Use scalar subqueries (not joins) so multi-row joins can't multiply the sums.
SELECT m.name AS merchant, m.is_active,
       (SELECT count(*) FROM outlets   WHERE merchant_id = m.id) AS outlets,
       (SELECT count(*) FROM orders    WHERE merchant_id = m.id) AS orders,
       (SELECT count(DISTINCT customer_id) FROM orders WHERE merchant_id = m.id) AS customers,
       (SELECT coalesce(sum(amount),0)        FROM transactions WHERE merchant_id = m.id) AS revenue,
       (SELECT coalesce(sum(points_earned),0) FROM transactions WHERE merchant_id = m.id) AS points_issued
FROM merchants m
ORDER BY revenue DESC;

-- 2) Merchant feature toggles (JSONB settings bag)
SELECT name, settings
FROM merchants
ORDER BY name;
