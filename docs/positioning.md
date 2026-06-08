# CIP — positioning, pitch & growth model

_Strategic narrative for the **Customer Intelligence Platform (CIP)**. Split out of `CLAUDE.md`
(2026-06-08) to keep the per-turn operating-guidance file lean — read this on demand for bizdev /
pitch / go-to-market work (see also `/my-bizdev`)._

The system is the **Customer Intelligence Platform (CIP)** — it helps F&B merchants **grow using
customer intelligence**. Five integrated modules: **CRM · AI · Payment · Ordering · Rewards (loyalty)**.
The positioning is *intelligence-led growth*, not just QR-ordering/loyalty — the data captured across
ordering/payment/rewards feeds the CRM + AI that drive merchant growth. Maps to the 3-module engine
(Table QR · **Intelligence** · POS) on one core — see `docs/architecture-3-modules.md`.

## The pitch (intelligence-led growth)
- **Category line:** *"Most F&B tools RUN your operations. CIP GROWS your business — it turns every order,
  payment and reward into customer intelligence that brings diners back."* Position **against** POS-led tools
  (Toast/Square/StoreHub — run the till, ~2–3% + hardware) and aggregators (rent your customers ~30%). CIP =
  **intelligence-led, own-your-customer, ~0 commission.** "They process transactions; we grow relationships."
- **Land-and-expand ladder (the module toggles ARE the sales model):** start with one module, switch on the
  rest as you grow — one platform, one customer record. Price: **Intelligence = the anchor SKU** (the value);
  Ordering/Payment/Rewards = expansion; **AI = premium add-on**. Low adoption friction → NRR > 110%.
- **Compounding-network moat (M1):** the CRM gets smarter every day, and smarter *on the network* — SG Eats
  Rewards (earn-here-spend-there) + cross-merchant data make the AI better than any single shop could build.
- **Sell the % lift, not features:** 2nd-visit 15%→40%, win-back 15%+, repeat-rate compounding; CAC payback < 1mo.
- **The arc under the logo:** **Capture (Ordering) → Retain (Rewards/CRM) → Grow (Referral)** — referral is the
  top *unbuilt* lever; build it to make "growth" visible.
- **Demo risk:** turn ON real AI (`AI_ENABLED=1` + `ANTHROPIC_API_KEY`) for any pitch — "Intelligence" must
  not be the deterministic-heuristic fallback in the room.

## Growth model — Luckin Coffee (the playbook we copy, + its caution)
Model CIP's growth engine on Luckin's (the engine worked; the 2020 accounting fraud was unrelated):
1. **~100% identity capture** — every order tied to a known customer (Luckin: app-only; CIP: QR-at-table, less friction).
2. **Aggressive RFM-segmented coupons** — a different offer per segment, pushed (WhatsApp here).
3. **Coalition density** — make it easier to stay loyal than to switch (SG Eats Rewards = our version).
4. **Referral loop** — invite-a-friend, both earn → compounding acquisition (the TOP unbuilt lever).
5. **Private community / broadcast** — per-store engagement (WeChat there; WhatsApp/broadcast here, later).

**CFO discipline (the cautionary half):** aggressive discounting burned Luckin's margin for years — so build the
engine first, then **TUNE economics: coupon-budget guardrails, margin-per-redemption caps, RFM-targeted not
blanket sends, and NEVER wire unverified earn to the coalition pool** — before scaling spend. See `/my-bizdev`.
