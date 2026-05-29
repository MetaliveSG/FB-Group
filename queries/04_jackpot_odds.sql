-- Jackpot win odds per prize.
-- Server logic (app/services/jackpot.py): outcome = weighted random across all prizes
-- PLUS a synthetic "lose" bucket sized total_weight * LOSE_WEIGHT_MULTIPLIER (=3),
-- so grand total = total_weight * 4  ->  overall win rate ~25%.
-- Invariant: cheaper items have higher weight (hit more often); premium items rarer.

WITH per_merchant AS (
  SELECT merchant_id, sum(weight) AS total_weight
  FROM jackpot_prizes
  GROUP BY merchant_id
)
SELECT m.name AS merchant,
       jp.emoji, jp.item_name, jp.item_price, jp.weight, jp.sort_order,
       pm.total_weight,
       -- denominator includes the lose bucket (total_weight * 3)
       round(100.0 * jp.weight / (pm.total_weight * 4), 2) AS win_pct,
       round(100.0 * (pm.total_weight * 3) / (pm.total_weight * 4), 2) AS lose_pct
FROM jackpot_prizes jp
JOIN per_merchant pm ON pm.merchant_id = jp.merchant_id
JOIN merchants m ON m.id = jp.merchant_id
ORDER BY m.name, jp.item_price DESC;  -- premium first; win_pct should ASCEND as price DESCENDS

-- Sanity: total win probability per merchant should be ~25%
SELECT m.name AS merchant,
       round(100.0 * sum(jp.weight) / (sum(jp.weight) * 4), 2) AS overall_win_pct
FROM jackpot_prizes jp
JOIN merchants m ON m.id = jp.merchant_id
GROUP BY m.name;
