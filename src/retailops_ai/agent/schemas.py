"""Typed contracts for the RetailOps decision-support agent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject undeclared fields in LLM and API structured outputs."""

    model_config = ConfigDict(extra="forbid")


class EntityRef(StrictModel):
    item_id: str = Field(min_length=1, max_length=128)
    store_id: str = Field(min_length=1, max_length=128)


class ForecastToolRequest(StrictModel):
    entities: list[EntityRef] = Field(min_length=1, max_length=10)
    split: Literal["validation", "test"] = "test"


class AnalyticsRequest(StrictModel):
    operation: Literal[
        "sales_summary",
        "store_summary",
        "top_products",
        "baseline_metrics",
    ]
    split: Literal["validation", "test"] = "test"
    item_id: str | None = Field(default=None, max_length=128)
    store_id: str | None = Field(default=None, max_length=128)
    top_n: int = Field(default=5, ge=1, le=20)


class AgentPlan(StrictModel):
    """Bounded operational plan. It is not a chain-of-thought trace."""

    status: Literal["execute", "answer"]
    forecast: ForecastToolRequest | None = None
    analytics: list[AnalyticsRequest] = Field(default_factory=list, max_length=3)
    need_model_info: bool = False
    knowledge_query: str | None = Field(default=None, max_length=500)
    note: str = Field(
        default="",
        max_length=500,
        description="Short operational justification, not hidden reasoning.",
    )


class ActionProposal(StrictModel):
    action_type: Literal[
        "review_reorder",
        "review_safety_stock",
        "investigate_anomaly",
        "escalate_to_planner",
    ]
    description: str = Field(min_length=1, max_length=1200)
    entities: list[EntityRef] = Field(default_factory=list, max_length=10)


class AgentDraft(StrictModel):
    answer: str = Field(min_length=1, max_length=12000)
    confidence: Literal["low", "medium", "high"]
    evidence_sources: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=10)
    proposed_action: ActionProposal | None = None


class ApprovalDecision(StrictModel):
    approved: bool
    reviewer_note: str | None = Field(default=None, max_length=1000)


class AgentRunResult(StrictModel):
    status: Literal["completed", "approval_required"]
    thread_id: str
    answer: str | None = None
    approval_request: dict[str, Any] | None = None
    evidence_sources: list[str] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
