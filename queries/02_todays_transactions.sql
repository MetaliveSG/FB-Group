-- Today's transactions (timestamps are naive UTC).
-- For Singapore-local "today", swap CURRENT_DATE for: (now() AT TIME ZONE 'Asia/Singapore')::date
-- and compare created_at AT TIME ZONE 'Asia/Singapore'.

-- 1) Today's sales summary per merchant
SELECT m.name AS merchant,
       count(*)               AS txns,
       sum(t.amount)          AS revenue,
       round(avg(t.amount),2) AS avg_ticket,
       sum(t.points_earned)   AS points_issued
FROM transactions t
JOIN merchants m ON m.id = t.merchant_id
WHERE t.created_at::date = CURRENT_DATE
GROUP BY m.name
ORDER BY revenue DESC;

-- 2) Most recent transactions (any day) with customer + outlet context
SELECT m.name AS merchant, ou.name AS outlet,
       c.full_name AS customer, t.amount, t.points_earned, t.created_at
FROM transactions t
JOIN merchants m  ON m.id = t.merchant_id
LEFT JOIN outlets ou ON ou.id = t.outlet_id
LEFT JOIN customers c ON c.id = t.customer_id
ORDER BY t.created_at DESC
LIMIT 30;

-- 3) Last 7 days revenue trend per merchant
SELECT m.name AS merchant, t.created_at::date AS day,
       count(*) AS txns, sum(t.amount) AS revenue
FROM transactions t
JOIN merchants m ON m.id = t.merchant_id
WHERE t.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY m.name, day
ORDER BY day DESC, revenue DESC;
