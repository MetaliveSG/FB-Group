"""AI Insights Advisor.

Turns a merchant's analytics (sales, momentum, forecast, segments, churn, RFM,
pipeline, campaign performance) into a plain-English executive summary plus a
ranked list of next-best actions wired to features the platform already has
(win-back launcher, campaigns, VIP rewards, pipeline follow-up).

Two execution paths behind one stable output shape:

* **Claude** (`AI_ENABLED=1` + `ANTHROPIC_API_KEY`): the gathered context is sent
  to Claude via the Anthropic SDK with a cached system prompt and a structured
  JSON schema, so the advisor reasons over the numbers like a business analyst.
* **Heuristic** (default): a deterministic, rule-based advisor derives the same
  summary/recommendations from the numbers — no key, no network, no cost. This is
  what the PoC demos out of the box and what the tests assert against.

The provider abstraction mirrors the OTP / WhatsApp / payment mocks elsewhere in
the codebase: real integration code, with a deterministic fallback for the PoC.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.analytics import reports as rpt
from app.analytics import rfm as rfm_analytics
from app.auth.access import Scope
from app.core.config import settings
from app.db.base import utcnow
from app.models.tenancy import Merchant
from app.services import campaigns as campaign_service
from app.services import crm as crm_service
from app.services import opportunities as opp_service

logger = logging.getLogger(__name__)

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


# --- 1. Gather a compact, JSON-serialisable analytics context ----------------
def build_context(
    db: Session, *, merchant_id: str, scope: Scope, allowed_outlets: set[str] | None
) -> dict:
    merchant = db.get(Merchant, merchant_id)

    totals = rpt.totals(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets)
    mix = rpt.new_vs_repeat_revenue(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets)

    # 30-day momentum from the daily series (last 30d vs the prior 30d).
    daily = rpt.sales_timeseries(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets,
                                 granularity="day", days=60)
    rev = [d["revenue"] for d in daily]
    last30, prev30 = round(sum(rev[-30:]), 2), round(sum(rev[:-30]), 2)
    change_pct = round((last30 - prev30) / prev30 * 100, 1) if prev30 > 0 else None

    fc = rpt.forecast(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets, horizon_days=7, window=7)
    top = rpt.top_items(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets, limit=5)
    hours = rpt.peak_hours(db, merchant_id=merchant_id, allowed_outlets=allowed_outlets)
    peak = max(hours, key=lambda h: h["orders"]) if any(h["orders"] for h in hours) else None

    # Customer health (one pass over the merchant's CRM book).
    items = crm_service.list_customers(db, merchant_id=merchant_id, scope=scope)
    segments: dict[str, int] = {}
    churn = {"high": 0, "medium": 0, "low": 0}
    lifecycle: dict[str, int] = {}
    for it in items:
        for seg in it.metrics.segments:
            segments[seg] = segments.get(seg, 0) + 1
        churn[it.metrics.churn_label] = churn.get(it.metrics.churn_label, 0) + 1
        lifecycle[it.metrics.lifecycle_stage] = lifecycle.get(it.metrics.lifecycle_stage, 0) + 1

    rfm = rfm_analytics.compute_rfm(db, merchant_id=merchant_id)

    sales_pipe = opp_service.pipeline(db, merchant_id=merchant_id, pipeline_type="sales")
    winback_pipe = opp_service.pipeline(db, merchant_id=merchant_id, pipeline_type="winback")

    # Campaign performance, aggregated across the merchant's campaigns.
    camp_agg = {"count": 0, "delivered": 0, "redeemed": 0, "revenue_generated": 0.0, "cost": 0.0}
    for c in campaign_service.list_campaigns(db, merchant_id=merchant_id):
        m = campaign_service.metrics(db, campaign=c)
        camp_agg["count"] += 1
        camp_agg["delivered"] += m["delivered"]
        camp_agg["redeemed"] += m["redeemed"]
        camp_agg["revenue_generated"] += m["revenue_generated"]
        camp_agg["cost"] += m["cost"]
    camp_agg["revenue_generated"] = round(camp_agg["revenue_generated"], 2)
    camp_agg["cost"] = round(camp_agg["cost"], 2)
    camp_agg["roi"] = round((camp_agg["revenue_generated"] - camp_agg["cost"]) / camp_agg["cost"], 2) \
        if camp_agg["cost"] > 0 else 0.0

    return {
        "merchant": {"id": merchant_id, "name": merchant.name if merchant else merchant_id},
        "as_of": utcnow().isoformat(),
        "currency": "SGD",
        "sales": {
            **totals,
            **mix,
            "revenue_last_30d": last30,
            "revenue_prev_30d": prev30,
            "revenue_change_pct": change_pct,
            "forecast_next_7d_per_day": fc["moving_average"],
            "forecast_method": fc["method"],
        },
        "top_items": top,
        "peak_hour": peak,
        "customers": {
            "total": len(items),
            "segments": segments,
            "churn": churn,
            "lifecycle": lifecycle,
        },
        "rfm": {"distribution": rfm["distribution"], "count": rfm["count"]},
        "pipeline": {
            "sales": {"open_count": sales_pipe["open_count"], "open_value": sales_pipe["open_value"],
                      "won_value": sales_pipe["won_value"]},
            "winback": {"open_count": winback_pipe["open_count"], "open_value": winback_pipe["open_value"]},
        },
        "campaigns": camp_agg,
    }


# --- 2. Deterministic rule-based advisor (default / fallback) ----------------
def heuristic_insights(ctx: dict) -> dict:
    sales = ctx["sales"]
    custs = ctx["customers"]
    recs: list[dict] = []

    def add(title, rationale, action, priority, metric=None):
        recs.append({"title": title, "rationale": rationale, "action": action,
                     "priority": priority, "metric": metric})

    # Churn / lapsing customers -> win-back.
    at_risk = custs["lifecycle"].get("at_risk", 0)
    dormant = custs["lifecycle"].get("dormant", 0)
    high_churn = custs["churn"].get("high", 0)
    lapsing = at_risk + dormant
    if lapsing or high_churn:
        add("Launch a win-back campaign",
            f"{lapsing} customers are at-risk or dormant and {high_churn} carry high churn risk — "
            "they have spent with you before and are slipping away.",
            "Use the win-back launcher (RFM → win-back pipeline → WhatsApp) targeting the "
            "'At Risk' and 'Hibernating' RFM segments.",
            "high" if (lapsing + high_churn) >= 5 else "medium",
            f"{lapsing} lapsing · {high_churn} high churn-risk")

    # Revenue momentum.
    change = sales.get("revenue_change_pct")
    if change is not None and change <= -5:
        add("Reverse the revenue dip",
            f"Revenue is down {abs(change)}% over the last 30 days vs the prior 30.",
            "Run a weekday-boost or limited-time promo to lift order frequency, and review your "
            "slowest hours from the peak-hours report.",
            "high", f"{change}% MoM")
    elif change is not None and change >= 10:
        add("Capitalise on momentum",
            f"Revenue is up {change}% over the last 30 days — demand is rising.",
            "Push a VIP-reward campaign to your best customers to deepen the trend before it cools.",
            "low", f"+{change}% MoM")

    # New-customer conversion.
    new_count = custs["segments"].get("new", 0)
    new_rev = sales.get("new_customer_revenue", 0.0)
    repeat_rev = sales.get("repeat_customer_revenue", 0.0)
    if new_count and repeat_rev <= new_rev:
        add("Convert first-timers into regulars",
            f"{new_count} customers are still on their first visit and repeat revenue "
            f"(${repeat_rev:.0f}) has not yet overtaken new-customer revenue (${new_rev:.0f}).",
            "Run a New-Customer-Return campaign offering bonus points on the 2nd visit.",
            "medium", f"{new_count} new customers")

    # VIPs.
    vip = custs["segments"].get("vip", 0)
    if vip:
        add("Reward your VIPs",
            f"{vip} VIP customers drive an outsized share of revenue and respond well to recognition.",
            "Send a VIP-reward campaign (exclusive perk or bonus multiplier) to protect this segment.",
            "medium" if vip >= 3 else "low", f"{vip} VIPs")

    # Win-back pipeline already in flight.
    wb_open = ctx["pipeline"]["winback"]["open_count"]
    if wb_open:
        add("Advance your win-back pipeline",
            f"{wb_open} win-back opportunities are open and waiting on a next step.",
            "Work the win-back board: move 'contacted' → 'offer_sent', and log the outcomes.",
            "medium", f"{wb_open} open win-backs")

    # Concentration risk in the menu.
    top = ctx["top_items"]
    if top and sales.get("revenue", 0) > 0:
        share = round(top[0]["revenue"] / sales["revenue"] * 100, 1)
        if share >= 40:
            add(f"Bundle around {top[0]['name']}",
                f"{top[0]['name']} alone is {share}% of revenue — a concentration risk and an upsell hook.",
                "Create combos pairing it with lower-velocity items to lift average order value.",
                "low", f"{share}% of revenue")

    if not recs:
        add("Grow repeat visits",
            "Your fundamentals look healthy with no urgent risks flagged.",
            "Keep capturing diners at the QR step and nudge a 2nd visit with a small points bonus.",
            "low", None)

    recs.sort(key=lambda r: PRIORITY_RANK.get(r["priority"], 1))

    # Executive summary.
    rev = sales.get("revenue", 0.0)
    aov = sales.get("avg_order_value", 0.0)
    total = custs["total"]
    bits = [f"{ctx['merchant']['name']} has booked ${rev:,.0f} across {sales.get('orders', 0)} orders "
            f"from {total} captured customers (avg order ${aov:.2f})."]
    if change is not None:
        bits.append(f"30-day revenue is {'up' if change >= 0 else 'down'} {abs(change)}% vs the prior period.")
    if lapsing or high_churn:
        bits.append(f"{lapsing + high_churn} customers need attention before they churn.")
    summary = " ".join(bits)

    highlights = [
        f"Revenue ${rev:,.0f} · {sales.get('orders', 0)} orders · AOV ${aov:.2f}",
        f"Captured customers: {total}" + (f" ({vip} VIP)" if vip else ""),
    ]
    if change is not None:
        highlights.append(f"30-day momentum: {'+' if change >= 0 else ''}{change}%")
    if top:
        highlights.append(f"Top seller: {top[0]['name']} (${top[0]['revenue']:,.0f})")
    if ctx["peak_hour"]:
        highlights.append(f"Busiest hour: {ctx['peak_hour']['hour']:02d}:00")

    return {"summary": summary, "highlights": highlights, "recommendations": recs}


# --- 3. Claude path ----------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are the AI growth advisor for a Singapore F&B CRM platform. You are given a single "
    "merchant's analytics as JSON: sales totals and 30-day momentum, a naive revenue forecast, "
    "top-selling items, the busiest hour, customer counts by CRM segment / churn-risk / lifecycle "
    "stage, an RFM segment distribution, sales and win-back pipeline status, and aggregated "
    "campaign performance.\n\n"
    "Produce a concise executive summary and a ranked list of next-best actions for the merchant "
    "owner. Ground every claim in the numbers provided — cite the specific figure. Recommend only "
    "actions the platform supports: launching a win-back campaign (RFM → win-back pipeline → "
    "WhatsApp), running a segment campaign (birthday / VIP-reward / new-customer-return / "
    "weekday-boost), advancing the sales or win-back pipeline, menu bundling, or owner follow-up. "
    "Order recommendations by impact (highest priority first). Be specific and practical; no fluff. "
    "Amounts are in SGD. Respond ONLY with JSON matching the provided schema."
)

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "highlights": {"type": "array", "items": {"type": "string"}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "rationale": {"type": "string"},
                    "action": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "metric": {"type": "string"},
                },
                "required": ["title", "rationale", "action", "priority"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "highlights", "recommendations"],
    "additionalProperties": False,
}


def _claude_insights(ctx: dict) -> dict:
    """Call Claude for the advisory. Raises on any failure (caller falls back)."""
    import anthropic  # lazy: absent / unconfigured installs never break import

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=settings.AI_TIMEOUT_SECONDS)
    resp = client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=settings.AI_MAX_TOKENS,
        # Stable instructions form the cached prefix; volatile per-merchant data
        # goes in the user turn so it never invalidates the cache.
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user",
                   "content": "Analyse this merchant and advise.\n\n"
                              + json.dumps(ctx, sort_keys=True, default=str)}],
        output_config={"format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


# --- 4. Orchestration --------------------------------------------------------
def generate(
    db: Session, *, merchant_id: str, scope: Scope, allowed_outlets: set[str] | None
) -> dict:
    ctx = build_context(db, merchant_id=merchant_id, scope=scope, allowed_outlets=allowed_outlets)

    generated_by, model, fallback_reason = "heuristic", None, None
    if settings.ai_ready:
        try:
            insights = _claude_insights(ctx)
            generated_by, model = "claude", settings.AI_MODEL
        except Exception as exc:  # network / auth / parse — degrade gracefully
            logger.warning("AI insights: Claude call failed, using heuristic fallback: %s", exc)
            insights = heuristic_insights(ctx)
            fallback_reason = type(exc).__name__
    else:
        insights = heuristic_insights(ctx)

    return {
        "summary": insights["summary"],
        "highlights": insights["highlights"],
        "recommendations": insights["recommendations"],
        "generated_by": generated_by,
        "model": model,
        "fallback_reason": fallback_reason,
        "context": ctx,
        "generated_at": utcnow().isoformat(),
    }
