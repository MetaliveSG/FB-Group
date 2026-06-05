# POS MVP — bug log (found → fixed, with proof)

Format: `[date] AREA — symptom → root cause → fix (commit) → proof`

[2026-06-05] RECEIPT — stall printed twice when stall name == outlet name ("Pepper Lunch @ TPY · Pepper Lunch @ TPY") → root: build_receipt always emitted stall for a single-storefront outlet → fix: suppress stall when it equals outlet.name (services/receipts.py) → proof: screens/02_receipt.png (before), re-verified after.
