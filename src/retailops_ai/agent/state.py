"""LangGraph state contract for RetailOps AI."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    thread_id: str
    user_context: dict[str, Any]
    step_count: int
    plan: dict[str, Any]
    evidence: list[dict[str, Any]]
    executed_signatures: list[str]
    tool_trace: list[dict[str, Any]]
    draft: dict[str, Any]
    approval_required: bool
    approval: dict[str, Any]
    final_answer: str
    status: str
