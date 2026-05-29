-- Loyalty balances & engagement leaderboard

-- 1) Top current point balances
SELECT c.full_name, c.phone,
       la.scope_type, la.tier,
       la.points_balance, la.lifetime_points,
       la.visit_count, la.total_spend, la.last_visit_at
FROM loyalty_accounts la
JOIN customers c ON c.id = la.customer_id
ORDER BY la.points_balance DESC
LIMIT 25;

-- 2) Tier distribution
SELECT scope_type, tier, count(*) AS accounts,
       sum(points_balance) AS total_points,
       round(avg(total_spend),2) AS avg_spend
FROM loyalty_accounts
GROUP BY scope_type, tier
ORDER BY scope_type, accounts DESC;

-- 3) Points liability (outstanding balance the business "owes") per scope
SELECT scope_type, scope_id,
       count(*) AS accounts,
       sum(points_balance) AS outstanding_points,
       sum(lifetime_points) AS lifetime_issued
FROM loyalty_accounts
GROUP BY scope_type, scope_id
ORDER BY outstanding_points DESC;

-- 4) Recent reward redemptions (vouchers minted, incl. JACKPOT-* wins)
SELECT c.full_name, rr.reward_name, rr.points_spent,
       rr.status, rr.voucher_code, rr.created_at
FROM reward_redemptions rr
JOIN loyalty_accounts la ON la.id = rr.account_id
JOIN customers c ON c.id = la.customer_id
ORDER BY rr.created_at DESC
LIMIT 30;
