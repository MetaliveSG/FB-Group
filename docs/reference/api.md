# API Reference

Base URL: `http://localhost:8000` · All app endpoints under `/api/v1`.
Interactive docs: `/docs` (Swagger) · `/redoc` · machine spec: `/openapi.json`
(also saved to `artifacts/openapi.json`).

Auth: `Authorization: Bearer <access_token>`. Errors:
`{ "error": { "code": "...", "message": "..." } }` with the matching HTTP status.

## Health
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | – | liveness probe |

## Auth (Module 2)
| Method | Path | Auth | Body / Notes |
|---|---|---|---|
| POST | `/api/v1/auth/customer/register` | – | `{email,password,full_name?,phone?,birthday?}` → token resp (201) |
| POST | `/api/v1/auth/customer/login` | – | `{email,password}` (rate-limited) |
| POST | `/api/v1/auth/customer/otp/request` | – | `{phone}` → `{message, debug_code}` (dev only) |
| POST | `/api/v1/auth/customer/otp/verify` | – | `{phone,code,full_name?}` (register-or-login) |
| POST | `/api/v1/auth/customer/sso` | – | `{provider:"google"\|"apple", sub, email?, full_name?}` (mock) |
| POST | `/api/v1/auth/staff/login` | – | `{email,password}` → token resp `actor:"user"` (suspend-aware; rejects POS-only accounts) |
| POST | `/api/v1/auth/staff/pin-login` | – | POS PIN login: `{merchant_id, outlet_id, pin}` → token resp. Resolves the `kind="pos"` operator at the bound storefront; suspend-aware |
| POST | `/api/v1/auth/customer/consent` | customer | `{purpose:"terms"\|"marketing", granted, version?}` — PDPA consent capture |
| POST | `/api/v1/auth/refresh` | – | `{refresh_token}` → new access token |

Token response: `{access_token, refresh_token, token_type, actor, customer?, user?}`.

## QR + Menu (Modules 3, 4)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/qr/{token}` | – | dining context + `is_foodcourt`/`stalls[]`; inline `menu` for single-stall, null for foodcourt; module flags `ordering_enabled`/`rewards_enabled` (Phase 2 — rewards-only when ordering off) |
| GET | `/api/v1/qr/{token}/menu/{menu_id}` | – | full menu for one stall, validated to the token's outlet (cross-outlet → 404 `menu_not_found`) |
| GET | `/api/v1/outlets/{outlet_id}/menu` | – | menu only |

## Orders + Checkout (Modules 4, 5)
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/orders` | customer | `{qr_token, items:[…], service_option?}` — `service_option` picks the storefront's enabled fulfilment option (auto if one); derives `order_type` + `hand_off` |
| GET | `/api/v1/orders` | staff `order.view` | merchant-wide orders feed: order+items+breakdown+outlet/customer/table labels; filters `?status=&outlet_id=&limit=`; outlet-scoped users see only their outlets |
| GET | `/api/v1/orders/kitchen` | staff `order.view` | **KDS** queue for `?outlet_id=`: paid (`status=completed`), not-yet-collected orders, oldest-first; items + table/order number (no PII) |
| PATCH | `/api/v1/orders/{id}/fulfilment` | staff `order.manage` | **KDS** advance the kitchen ticket `{status}` (queued→preparing→ready→collected); validated forward-only |
| POST | `/api/v1/orders/manual` | staff `order.manage` | cashier/walk-in order (`{outlet_id, items, customer_phone?}`) |
| GET | `/api/v1/orders/{id}` | customer (own) | order detail |
| PATCH | `/api/v1/orders/{id}/status` | staff `order.manage` | `{status}` — validated lifecycle |
| POST | `/api/v1/orders/{id}/checkout` | customer (own) | `{method, force_outcome?}` → payment + points |
| POST | `/api/v1/orders/{id}/cashier-checkout` | staff `payment.process` | walk-in checkout |
| POST | `/api/v1/orders/{id}/void` | staff `order.void` (Supervisor+) | reverse a COMPLETED sale: drops the transaction, voids the payment, claws back loyalty, restores a redeemed voucher → status `voided`. `{reason?}` |
| GET | `/api/v1/orders/{id}/receipt` | staff `order.view` | printable receipt payload (company header + outlet/stall + lines + payment) |

Payment methods: `cash` `card` `nets` `paywave` `paynow`.
Order lifecycle: `pending → accepted → preparing → ready → completed`; `cancelled` (pre-payment) or `voided` (supervisor reversal of a paid sale) terminal.

## CRM (Module 7) — staff, tenant-isolated
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/crm/customers` | `crm.view` | `?segment=&search=&outlet_id=&merchant_id=` |
| GET | `/api/v1/crm/segments` | `crm.view` | segment counts |
| GET | `/api/v1/crm/customers/{id}` | `crm.view` | profile + visit/txn/reward history + tags/notes |
| POST | `/api/v1/crm/customers/{id}/tags` | `crm.manage` | `{tag}` |
| POST | `/api/v1/crm/customers/{id}/notes` | `crm.manage` | `{body}` |

Segments: `vip`, `inactive`, `new`, `frequent`, `high_spender`, `low_frequency`,
`birthday_month`; `outlet_specific` via `?outlet_id=`.

## CRM activities — Salesforce-style (staff)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/crm/customers/{id}/timeline` | `crm.view` | unified activity feed (orders/payments/points/notes/tasks), newest first |
| GET | `/api/v1/crm/customers/{id}/tasks` | `crm.view` | tasks for a customer |
| POST | `/api/v1/crm/customers/{id}/tasks` | `crm.manage` | `{title, description?, due_date?, priority?, assignee_user_id?}` |
| PATCH | `/api/v1/crm/tasks/{task_id}` | `crm.manage` | `{status:"done"\|"open"}` |
| GET | `/api/v1/crm/tasks` | `crm.view` | the caller's open tasks ("My Tasks") |
| PUT | `/api/v1/crm/customers/{id}/owner` | `crm.manage` | `{owner_user_id}` — assign/clear record owner |

Customer list/profile also return `owner_user_id`, `owner_name`, `open_tasks` (list) / `tasks` (profile).

## Promotions & Retention Campaigns (Module 8) — staff `campaign.manage`
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/campaigns` | list campaigns, each with metrics (sent/delivered/redeemed/revenue/conversion/ROI) |
| POST | `/api/v1/campaigns` | `{name, campaign_type, segment_key?, message_template, reward_points?}` |
| GET | `/api/v1/campaigns/{id}` | campaign + metrics + message log |
| POST | `/api/v1/campaigns/{id}/audience` | resolve audience by segment → `{audience_size}` |
| POST | `/api/v1/campaigns/{id}/send` | mock WhatsApp send (with retry) → `{delivered, failed, audience}` |
| GET | `/api/v1/campaigns/{id}/metrics` | sent, delivered, redeemed, revenue_generated, conversion_rate, cost, ROI |
| POST | `/api/v1/campaigns/{id}/redemptions` | `{customer_id, revenue, order_id?}` — track attribution |

Campaign types: `whatsapp_promo`, `birthday`, `winback`, `weekday_boost`, `new_customer_return`, `vip_reward`.
WhatsApp send goes through a provider abstraction (`app/services/whatsapp.py`); the mock logs structured delivery + retries transient failures.

## Platform Console — platform-tier roles (top of the hierarchy)
Gated by **operator role**, not a single super-admin flag. Roles: **Owner** (`super_admin`, full + manages operators), **Admin** (`platform_admin`, merchants+coalitions+drill-in), **Onboarding** (`platform_onboarder`, onboard/edit only), **Support** (`platform_support`, read-only + read-only drill-in). Each route below lists the permission it requires; a caller lacking it gets 403.
| Method | Path | Perm required | Notes |
|---|---|---|---|
| GET | `/api/v1/platform/permissions` | any operator | `{permissions:[…], is_owner}` — the caller's own platform capabilities (console section gating) |
| GET | `/api/v1/platform/overview` | `platform.overview.view` | ecosystem KPIs |
| GET | `/api/v1/platform/merchants` | `platform.merchants.view` | every merchant + KPIs + owner + status |
| GET | `/api/v1/platform/coalitions` | `platform.merchants.view` | coalitions + members (`members` names + `member_ids`) + points |
| POST | `/api/v1/platform/merchants` | `platform.merchants.onboard` | onboard merchant → merchant+brand+owner (409 if email taken) |
| PUT | `/api/v1/platform/merchants/{id}` | `platform.merchants.onboard` | `{name?, module_flags?}` — rename + flags (unknown flag → 400) |
| PATCH | `/api/v1/platform/merchants/{id}` | `platform.merchants.suspend` | `{is_active}` — suspend/activate |
| GET/POST/DELETE | `/api/v1/platform/operators[/{id}]` | `platform.operators.manage` (**Owner-only**) | list/invite/revoke operators; invite body `{email,password,full_name?,role}`; can't revoke self or the **last Owner**; bad role → 422 |
| POST/PATCH | `/api/v1/platform/coalitions[/{id}]` | `platform.coalitions.manage` | create / rename / activate |
| POST/DELETE | `/api/v1/platform/coalitions/{id}/members[/{merchant_id}]` | `platform.coalitions.manage` | add (409 dup) / remove (404 non-member) member |

**Drill-in:** operators with `platform.merchant.access` reach the CRM/reports endpoints with `?merchant_id=` — **Admin/Owner full**, **Support read-only** (view 200, write 403). Onboarding has no drill-in.

## Customer Rewards & Spin-the-Wheel (customer)
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/me/loyalty?merchant_id=` | balance, lifetime, tier, next_tier, points_to_next_tier, recent ledger |
| GET | `/api/v1/me/orders?merchant_id=` | the customer's order history (status, total, items_count, summary, outlet, created_at) |
| GET | `/api/v1/me/vouchers?merchant_id=` | the customer's reward vouchers (`reward_name`, `voucher_code`, `status`, `created_at`) |
| GET | `/api/v1/me/profile` | customer profile: `full_name`, `phone`, `email`, `birthday`, `gender` |
| PATCH | `/api/v1/me/profile` | update profile — `phone` (compulsory, E.164, unique), `birthday`/`gender`/`full_name` optional |
| GET | `/api/v1/me/rewards/catalog?merchant_id=` | redeemable rewards + `can_afford` |
| POST | `/api/v1/me/rewards/redeem` | `{merchant_id, item_id}` → `{voucher_code, reward_name, points_balance}` |
| GET | `/api/v1/me/wheel?merchant_id=` | `{spin_cost, segments:[{label,color}]}`. `spin_cost` defaults to 10 but is **per-merchant configurable** via `merchants.settings.wheel_spin_cost`. |
| POST | `/api/v1/me/wheel/spin` | `{merchant_id}` → `{winning_index, prize, points_balance}` (insufficient points → 409) |
| GET | `/api/v1/me/jackpot?merchant_id=` | **888 Jackpot** config: `{spin_cost, grid_size, payline:"middle_row", grand_prize, prizes:[…]}`. `spin_cost` defaults to 5 but is **per-merchant configurable** via `merchants.settings.jackpot_spin_cost` (set on `/org/settings`; 0 = free play); `grand_prize` = persistent progressive pot (base 1000, grows ~0.5/s, resets on a win). |
| POST | `/api/v1/me/jackpot/play` | `{merchant_id}` → server-authoritative outcome: `{spin_cost, grid:[[{item_name,emoji,…}]]×3, won, prize?:{item_name,item_price,emoji,voucher_code}, points_balance}`. Middle row is the payline — 3-of-a-kind there = win that item as a `JACKPOT-*` voucher. **Free to play** (no coin cost / balance untouched while `JACKPOT_SPIN_COST=0`). |

## Reports & Forecast (Module 9) — staff `report.view`, graph-ready
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/reports/summary` | revenue, orders, unique customers, AOV, new vs repeat |
| GET | `/api/v1/reports/sales` | `?granularity=day\|week\|month&days=` timeseries |
| GET | `/api/v1/reports/top-items` | best sellers by revenue |
| GET | `/api/v1/reports/peak-hours` | 24-hour distribution |
| GET | `/api/v1/reports/outlets` | outlet comparison |
| GET | `/api/v1/reports/forecast` | `?horizon=&window=` moving-average forecast |
| GET | `/api/v1/reports/rfm` | RFM scoring: per-customer R/F/M (1-5) + named segment + distribution |
| GET | `/api/v1/reports/ai-insights` | **AI advisor**: executive summary + ranked next-best actions over sales/segments/churn/RFM/pipeline/campaigns. Uses Claude when `AI_ENABLED=1`+`ANTHROPIC_API_KEY` set, else a deterministic heuristic. Response: `{summary, highlights[], recommendations[{title,rationale,action,priority,metric}], generated_by, model, context}` |

Super admin must pass `?merchant_id=`; merchant-scoped users default to their merchant
and are forbidden from querying others.

## Pipeline / Opportunities (Salesforce-style, staff)
Configurable modes: **sales** (prospecting→qualified→proposal→negotiation→won/lost) or
**winback** (at_risk→contacted→offer_sent→recovered/churned).
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/crm/pipeline` | `?pipeline_type=sales\|winback` → stages (count/value + is_open/is_won/is_lost) + open/won totals |
| GET | `/api/v1/crm/opportunities` | `?pipeline_type=` optional filter |
| GET/POST | `/api/v1/crm/customers/{id}/opportunities` | create `{name, amount, pipeline_type?, stage?, expected_close_date?}` |
| PATCH | `/api/v1/crm/opportunities/{id}` | `{stage?, amount?}` (won/lost stage stamps closed_at) |

## Activity logging + Bulk actions + Win-back (staff)
| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/v1/crm/customers/{id}/activities` | log call/email/meeting/whatsapp/note (feeds timeline) |
| POST | `/api/v1/crm/bulk/tag` | `{tag, customer_ids?\|segment?}` → `{affected}` |
| POST | `/api/v1/crm/bulk/owner` | `{owner_user_id?, customer_ids?\|segment?}` |
| POST | `/api/v1/crm/bulk/task` | `{title, priority?, customer_ids?\|segment?}` |
| POST | `/api/v1/crm/winback` | `{customer_ids?\|rfm_segments?, create_campaign?, message_template?}` → win-back opportunities + optional campaign |

## Menu management (Module 4 admin) — staff `menu.manage`
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/menu-admin/outlets` | outlets + their menu_id (pick what to edit) |
| POST/PATCH/DELETE | `/api/v1/menu-admin/categories[/{id}]` | category CRUD |
| POST/PATCH/DELETE | `/api/v1/menu-admin/items[/{id}]` | item CRUD + `is_available` toggle |
| POST/DELETE | `/api/v1/menu-admin/modifiers[/{id}]` | modifier add/remove |

## User management — web logins are node-scoped
The legacy flat `/admin/users` path was **removed** (2026-06-08). Web logins (Manager / Viewer /
Finance) are now created + listed + revoked per member-tree node via
`GET/POST/DELETE /org/nodes/{id}/accounts` (see the Org structure section below). POS operators
(Supervisor / Cashier, PIN-only) live under `/org/nodes/{id}/pos-staff`.

## Org structure (Module 1 admin) — brands / outlets / tables+QR
| Method | Path | Notes |
|---|---|---|
| GET/POST/PATCH | `/api/v1/org/brands[/{id}]` | brand CRUD (`brand.manage`) |
| GET/POST/PATCH | `/api/v1/org/outlets[/{id}]` | outlet CRUD (`outlet.manage`); create auto-provisions an empty menu |
| GET/POST | `/api/v1/org/outlets/{id}/tables` | list/add tables (auto-generates a stable QR token) |
| DELETE | `/api/v1/org/tables/{id}` | remove a table + its QR |
| GET | `/api/v1/org/nav-flags` | nav-only booleans `{pipeline_enabled, rewards_enabled, qr_ordering_enabled, pos_enabled, can_manage_merchant}` for sidebar/nav gating — readable by **any staff member** (`order.view` floor); carries **no** spin costs / earn rates. Optional `?node_id=` resolves the module flags via the node cascade (so the sidebar reacts to per-node toggles); omitted → tenant `Merchant.settings`. `can_manage_merchant` = caller holds `merchant.manage` (owner/operator) → client hides owner-only nav (Settings/Team) when false |
| GET | `/api/v1/org/permissions` | **capabilities** `{permissions:[…], is_super_admin}` — the caller's effective permission codes in a merchant context; drives the declarative client nav manifest. Wildcard expands to all codes; super-admin short-circuits. Server still enforces per-route (this only prunes the menu) |
| GET/PATCH | `/api/v1/org/settings` | full merchant settings: `{pipeline_enabled, wheel_spin_cost, jackpot_spin_cost, rewards_enabled, qr_ordering_enabled, pos_enabled}` — **owner-only** (GET **and** PATCH need `merchant.manage`; downline managers 403 — hard upline isolation, use `/org/nav-flags` for nav) |
| GET/PUT | `/api/v1/org/loyalty` | loyalty program (standing earn rules): `{points_per_dollar, welcome_bonus, birthday_bonus}` — 0 disables a rule; **owner-only** (GET **and** PUT need `merchant.manage`, audited) |
| GET | `/api/v1/org/tree` | the caller's visible slice of the **member tree** (Chain/Storefront nodes, flat — client assembles via `parent_id`); each node has `can_manage`. Scope-aware (no `merchant_id`): a node-assigned user sees its subtree, a platform operator sees the whole forest. Drives the **Platform Console** directory drill-down |
| POST/PATCH | `/api/v1/org/nodes[/{id}]` | create a child node (`{parent_id, role:CHAIN\|STOREFRONT, name, chain_stopped?, subscription_fee?}`) / rename·(de)activate·set fee·stop-chain. Downline-gated (`org.manage`); a child only attaches under a Chain; a chain-stopped node takes Storefronts only; suspending a tenant mirrors `Merchant.is_active` |
| GET/PUT | `/api/v1/org/nodes/{id}/modules` | per-node **module toggles** — **binary** `{rewards, qr_ordering, pos, wallet}` each `on\|off`, **parent-gated** (a node is ON only if it AND every ancestor are ON; wallet additionally needs Table-QR). GET returns own + resolved effective + `parent_enabled` (drives grey/lock). Downline-gated |
| GET/PUT | `/api/v1/org/nodes/{id}/service-options` | per-storefront **fulfilment** options — GET own (`null`=inherit) + resolved (cascade) + catalog; PUT `{options:[dine_in_served\|dine_in_pickup\|takeaway]}` (empty/null=inherit). Cascades to the subtree. Downline-gated |
| GET/POST/DELETE | `/api/v1/org/nodes/{id}/accounts[/{assignment_id}]` | **web logins** (dashboard, email+password) — list (web-palette roles only) / create (`{email, password, full_name?, role:manager\|viewer\|finance}`) / revoke staff at the node; cascade-gated. POS operators (cashier/supervisor) excluded from the listing |
| GET/POST/DELETE | `/api/v1/org/nodes/{id}/pos-staff[/{user_id}]` | **POS operators** (PIN-only, `kind="pos"`) — list (incl. the readable `pin`) / create (`{full_name, role:supervisor\|cashier, pin?}` → returns the PIN) / remove. PINs encrypted at rest, unique per storefront |
| POST | `/api/v1/org/nodes/{id}/pos-staff/{user_id}/reset-pin` | set a chosen PIN (`{pin}`) or auto-generate; returns it. Cascade-gated |
| GET/POST/DELETE | `/api/v1/promotions[/{id}]` | point-multiplier promos (time-bound `CAMPAIGN_MULTIPLIER`): `{label, multiplier, starts_on, ends_on, is_active}` — engine applies an active in-window multiplier to every earn (`campaign.manage`, audited) |

## Vouchers (shared core — loyalty-earned or campaign-granted; one cashier redeem flow)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/vouchers/{code}` | staff `order.view` | preview a voucher (value, validity, min-spend, status) |
| POST | `/api/v1/vouchers/{code}/redeem` | staff `payment.process` | redeem at the counter: validate (active, window, per-period cap, min-spend, redeeming storefront ∈ scope subtree) → apply `value` to `{order_id}` |
| GET | `/api/v1/vouchers/diner/{customer_id}` | staff | the attached diner's unused vouchers at this merchant |
| POST | `/api/v1/campaigns/{id}/issue-vouchers` | `campaign.manage` | grant vouchers from a campaign to its audience |
