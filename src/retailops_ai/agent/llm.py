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
- Never invent sales, forecast, model, inventory, purchase-order, lead-time, or policy facts.
- Use forecast for future demand questions about explicit item/store entities.
- Use inventory_decision when the user supplies an explicit inventory scenario and asks about
  stockout risk, safety-stock coverage, reorder review, supplier delay, what-if analysis, or
  what needs to change. Inventory values are scenario inputs, never M5 facts.
- inventory_decision requires an explicit item, store and current stock. If incoming_units are
  positive, use the lead time stated by the user. Never invent a PO or lead time.
- For a pure stockout question with no safety-stock threshold, safety_stock=0 is acceptable.
  Otherwise never invent a safety-stock target.
- Set horizon_days to the horizon explicitly requested by the user; default to 28 only when
  the user asks about the full forecast horizon or gives no shorter horizon.
- Keep include_counterfactuals=true when the user asks "what should change", "how many more",
  "what if", "compare", "avoid the stockout", or similar prescriptive questions.
- Do not also request a separate forecast tool when inventory_decision already covers the same
  item/store/horizon; that tool obtains the live forecast internally.
- Use analytics for historical or aggregate facts. Analytics supports only:
  sales_summary, store_summary, top_products, baseline_metrics.
- Use model info for model/version/metric questions.
- Use knowledge retrieval for project policy, limitations, data semantics, or business rules.
- You may plan another tool round after seeing evidence, but the total budget is {max_steps}.
- If evidence is already sufficient, set status='answer'.
- If required scenario information is missing, do not guess it. Set status='answer' so the
  answer component can ask for the missing information.
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
        evidence_json = json.dumps(evidence, ensure_ascii=False, default=str)[:30000]
        context_json = json.dumps(user_context, ensure_ascii=False, default=str)[:4000]
        prompt = f"""
You are the answer component of RetailOps AI.
Produce a concise decision-support answer grounded ONLY in the tool evidence below.
Never manufacture numbers, dates, model performance, inventory levels, or source claims.
If evidence is insufficient, say exactly what scenario information is missing and lower confidence.

Important domain rules:
- A demand forecast is not automatically an order quantity.
- M5 contains sales, prices, and calendar context, not true inventory positions.
- Inventory, incoming PO, lead time and safety stock from inventory_decision are explicit
  user-provided scenario inputs. Never describe them as observed retailer inventory.
- inventory_decision calculations are deterministic and grounded on the live forecast.
- Counterfactual options answer "what would need to change?" but are not cost-optimal orders.
  They do not account for MOQ, supplier capacity, carrying cost, margin, substitution or
  service-level optimization.
- Clearly distinguish uncovered forecast demand from guaranteed lost sales.
- The project currently reports bottom-level mean RMSSE, not official M5 WRMSSE.
- A proposed reorder, safety-stock change, anomaly investigation, or escalation is advisory
  and must be represented as proposed_action so that a human can approve it.
- For high/medium inventory risk, propose a review_reorder or review_safety_stock action when
  the evidence supports it. Do not propose an action if the inventory scenario is low risk.
- Do not claim that any external system was changed.
- evidence_sources must contain only source names actually present in the evidence.
- When counterfactuals exist, summarize the smallest grounded change that removes the risk and
  mention at least one alternative when useful.

User question: {question}
User context: {context_json}
Tool evidence: {evidence_json}
""".strip()
        return self._generate_structured(prompt, AgentDraft)
