"""Schemas for the AI Insights advisor."""
from __future__ import annotations

from pydantic import BaseModel


class RecommendationOut(BaseModel):
    title: str
    rationale: str
    action: str
    priority: str  # high | medium | low
    metric: str | None = None


class AIInsightsOut(BaseModel):
    summary: str
    highlights: list[str]
    recommendations: list[RecommendationOut]
    generated_by: str          # "claude" | "heuristic"
    model: str | None = None   # set when generated_by == "claude"
    fallback_reason: str | None = None  # set if a Claude call failed and we degraded
    context: dict              # the analytics the advice was derived from (for transparency)
    generated_at: str
