"""Clients for calling the V4 forecasting service from the V5 agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token

from retailops_ai.agent.schemas import EntityRef


class ToolExecutionError(RuntimeError):
    """Raised when a deterministic agent tool cannot complete."""


@dataclass
class ForecastServiceClient:
    base_url: str
    timeout_seconds: float = 20.0
    auth_mode: str = "cloud-run"
    audience: str | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url:
            raise ValueError("forecast base_url is required")
        if self.auth_mode not in {"cloud-run", "none"}:
            raise ValueError("auth_mode must be 'cloud-run' or 'none'")

    def _headers(self, request_id: str) -> dict[str, str]:
        headers = {"x-request-id": request_id}
        if self.auth_mode == "cloud-run":
            audience = self.audience or self.base_url
            token = id_token.fetch_id_token(GoogleAuthRequest(), audience)
            headers["authorization"] = f"Bearer {token}"
        return headers

    def _request(self, method: str, path: str, *, request_id: str, json_body: Any = None) -> Any:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._headers(request_id),
                    json=json_body,
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ToolExecutionError(f"Forecast API call failed for {path}: {exc}") from exc

    def forecast(
        self,
        *,
        entities: list[EntityRef],
        split: str,
        request_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/forecast",
            request_id=request_id,
            json_body={
                "entities": [entity.model_dump(mode="json") for entity in entities],
                "split": split,
            },
        )

    def model_info(self, *, request_id: str) -> dict[str, Any]:
        return self._request("GET", "/v1/model", request_id=request_id)
