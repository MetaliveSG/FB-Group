# Database Schema

SQLAlchemy 2.0 models (`apps/api/app/models/`), Alembic-managed (**8 migrations**, single
head). **40 application tables** (+ `alembic_version`). String UUID PKs (`uuid4().hex`),
naive-UTC timestamps, money as `Numeric(12,2)`. Full DDL: run `alembic upgrade head` or
see `artifacts/schema_tables.txt`.

## Tables by domain
**Tenancy** — `merchants` (+`settings` JSON feature-toggles), `brands`, `outlets`, `tables`, `qr_codes`
**Identity / RBAC** — `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `customers`, `customer_auth_identities`
**Catalog** — `menus`, `menu_categories`, `menu_items` (incl. `image_url` for real food photos), `menu_modifiers`
**Orders** — `orders`, `order_items`
**Payments** — `payments`, `transactions`
**Loyalty** — `coalitions`, `coalition_members`, `loyalty_accounts` (+`owner_user_id` CRM owner), `reward_rules`, `reward_transactions`, `reward_redemptions` (+`voucher_code`)
**Engagement** — `reward_catalog_items` (redeemable rewards), `wheel_segments` (spin-the-wheel), `jackpot_prizes` (3x3 slot reels, server-authoritative), `crm_tasks` (activities/to-dos), `opportunities` (pipeline; `pipeline_type` sales|winback), `customer_activities` (logged call/email/meeting/whatsapp)
**CRM** — `customer_tags`, `customer_notes`, `customer_segments`
**Campaigns** — `campaigns`, `campaign_audiences`, `campaign_messages`, `campaign_redemptions`
**Audit** — `audit_logs`

## Migrations (chain)
`initial schema` → `rewards catalog/wheel/tasks/owner` → `redemption voucher_code` →
`opportunities/customer_activities` → `pipeline_type + merchant settings`.
(Target Postgres; SQLite dev/test uses `Base.metadata.create_all`.)

## Key relationships
```
Merchant 1─* Brand 1─* Outlet 1─* Table 1─1 QRCode
Outlet 1─* Menu 1─* MenuCategory 1─* MenuItem 1─* MenuModifier
Customer 1─* CustomerAuthIdentity        (password / mobile_otp / google / apple)
Customer 1─* Order *─1 Outlet            Order 1─* OrderItem
Order 1─1 Payment 1─1 Transaction        (transaction = successful-payment ledger row)
Customer 1─* LoyaltyAccount              (scope = one merchant OR one coalition; unique per scope)
LoyaltyAccount 1─* RewardTransaction     (append-only points ledger)
RewardRule (scope merchant|coalition, JSON config — earn/first-visit/birthday/repeat/multiplier)
User *─* Role (via user_roles, scoped) ; Role *─* Permission (role_permissions)
```

## Isolation keys
`merchant_id` is denormalized onto `brands, outlets, tables, qr_codes, orders,
transactions, customer_tags, customer_notes, audit_logs` and is the single predicate
enforcing tenant isolation on reads.
