"""Structured Gemini planner and synthesizer for the RetailOps agent."""

from __future__ import annotations

import json
from typing import Any, Protocol, TypeVar

from google.genai import types
from pydantic import BaseModel

from retailops_ai.agent.schemas import AgentDraft, AgentPlan
from retailops_ai.agent.vertex_genai import build_vertex_genai_client

TModel = TypeVar("TModel", bound=BaseModel)


class DecisionLLM(Protocol):
    def plan(
        self,
        *,
        question: str,
        evidence: list[dict[str, Any]],
        user_context: dict[str, Any],
        step_count: int,
        max_steps: int,
    ) -> AgentPlan: ...

    def synthesize(
        self,
        *,
        question: str,
        evidence: list[dict[str, Any]],
        user_context: dict[str, Any],
    ) -> AgentDraft: ...


class GeminiDecisionLLM:
    """Gemini with schema-constrained planning and grounded synthesis."""

    def __init__(self, *, project: str, location: str, model: str) -> None:
        self.model = model
        self.client = build_vertex_genai_client(project, location)

    def _generate_structured(self, prompt: str, schema: type[TModel]) -> TModel:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        if parsed is not None:
            return schema.model_validate(parsed)
        return schema.model_validate_json(response.text or "{}")

    def plan(
        self,
        *,
        question: str,
        evidence: list[dict[str, Any]],
        user_context: dict[str, Any],
        step_count: int,
        max_steps: int,
    ) -> AgentPlan:
        evidence_json = json.dumps(evidence, ensure_ascii=False, default=str)[:18000]
        context_json = json.dumps(user_context, ensure_ascii=False, default=str)[:4000]
        prompt = f"""
You are the planning component of RetailOps AI, a read-only retail decision-support agent.
Return only the structured operational plan required by the schema. Do not provide hidden
reasoning or chain-of-thought.

Trust rules:
- Never invent sales, forecast, model, or policy facts.
- Use forecast for future demand questions about explicit item/store entities.
- Use analytics for historical or aggregate facts. Analytics supports only:
  sales_summary, store_summary, top_products, baseline_metrics.
- Use model info for model/version/metric questions.
- Use knowledge retrieval for project policy, limitations, data semantics, or business rules.
- You may plan another tool round after seeing evidence, but the total budget is {max_steps}.
- If evidence is already sufficient, set status='answer'.
- The note is a short operational justification only, not private reasoning.

Tool round: {step_count}/{max_steps}
User question: {question}
User context: {context_json}
Evidence already collected: {evidence_json}
""".strip()
        return self._generate_structured(prompt, AgentPlan)

    def synthesize(
        self,
        *,
        question: str,
        evidence: list[dict[str, Any]],
        user_context: dict[str, Any],
    ) -> AgentDraft:
        evidence_json = json.dumps(evidence, ensure_ascii=False, default=str)[:24000]
        context_json = json.dumps(user_context, ensure_ascii=False, default=str)[:4000]
        prompt = f"""
You are the answer component of RetailOps AI.
Produce a concise decision-support answer grounded ONLY in the tool evidence below.
Never manufacture numbers, dates, model performance, inventory levels, or source claims.
If evidence is insufficient, say so explicitly and lower confidence.

Important domain rules:
- A demand forecast is not automatically an order quantity.
- M5 contains sales, prices, and calendar context, not true inventory positions.
- Do not describe simulated inventory as real retailer inventory.
- The project currently reports bottom-level mean RMSSE, not official M5 WRMSSE.
- A proposed reorder, safety-stock change, anomaly investigation, or escalation is advisory
  and must be represented as proposed_action so that a human can approve it.
- Do not claim that any external system was changed.
- evidence_sources must contain only source names actually present in the evidence.

User question: {question}
User context: {context_json}
Tool evidence: {evidence_json}
""".strip()
        return self._generate_structured(prompt, AgentDraft)
