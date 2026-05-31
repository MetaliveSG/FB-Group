# Operator-console role gating — browser proof (2026-06-01)

Live full-page screenshots of `/operator` (Docker, web :3001) logged in as each of the four
operator roles, proving the UI gating matches the server-enforced `platform.*` permissions.
Captured with Playwright + Chromium (`drive.js`), injecting each role's staff token into
`localStorage` and loading the console.

| UI element | Owner | Admin | Onboarding | Support |
|---|:--:|:--:|:--:|:--:|
| + Onboard Merchant | ✅ | ✅ | ✅ | ❌ |
| Edit pencil | ✅ | ✅ | ✅ | ❌ |
| Suspend toggle | ✅ | ✅ | ❌ | ❌ |
| Enter → (drill-in) | ✅ | ✅ | ❌ | ✅ (read-only) |
| **Operators section** (manage operators) | ✅ | ❌ | ❌ | ❌ |
| Coalition management | ✅ | ✅ | ❌ | ❌ |

**Headline control (separation of duties):** only the **Owner** sees the Operators section —
a non-Owner operator cannot manage operators (`platform.operators.manage` is Owner-only).
The UI only prunes controls; the server still enforces every route (`require_platform`).

Files: `operator-Owner.png`, `operator-Admin.png`, `operator-Onboarding.png`, `operator-Support.png`.

## Reproduce
```bash
# stack up (web :3001, api :8000), then:
node drive.js            # needs playwright + chromium; writes operator-<Role>.png
```
Demo logins (all `Password123!`): `superadmin@platform.sg` (Owner), `admin@platform.sg` (Admin),
`onboard@platform.sg` (Onboarding), `support@platform.sg` (Support).
