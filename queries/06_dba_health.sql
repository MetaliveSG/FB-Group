-- DBA health snapshot (companion to the my-dba skill).
-- Run against the Docker Postgres; safe read-only diagnostics.

-- 1) Table sizes + dead-tuple bloat
SELECT relname AS table,
       pg_size_pretty(pg_relation_size(relid))        AS heap,
       pg_size_pretty(pg_total_relation_size(relid))  AS total_with_indexes,
       n_live_tup, n_dead_tup,
       CASE WHEN n_live_tup > 0
            THEN round(100.0 * n_dead_tup / n_live_tup, 1) ELSE 0 END AS dead_pct,
       last_autovacuum
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- 2) Seq-scan dominance (heuristic for a missing index on a non-trivial table)
SELECT relname AS table, seq_scan, idx_scan, n_live_tup,
       CASE WHEN seq_scan > 0
            THEN seq_tup_read / seq_scan ELSE 0 END AS avg_rows_per_seq_scan
FROM pg_stat_user_tables
WHERE seq_scan > coalesce(idx_scan, 0) AND n_live_tup > 100
ORDER BY seq_scan DESC;

-- 3) Index usage (spot unused indexes after warm-up)
SELECT relname AS table, indexrelname AS index, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC, relname
LIMIT 40;

-- 4) Any currently-blocked locks (should be empty in a healthy idle PoC)
SELECT pid, relation::regclass AS rel, mode, granted, query
FROM pg_locks l LEFT JOIN pg_stat_activity a USING (pid)
WHERE NOT granted;

-- 5) Long-running / idle-in-transaction sessions (>30s)
SELECT pid, state, age(clock_timestamp(), query_start) AS running_for, query
FROM pg_stat_activity
WHERE state <> 'idle' AND query_start < now() - INTERVAL '30 seconds'
ORDER BY query_start;
