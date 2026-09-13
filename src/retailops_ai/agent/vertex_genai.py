"""Google Gen AI client construction for Vertex AI-backed agent capabilities."""

from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types


def build_vertex_genai_client(project: str, location: str) -> Any:
    """Build a stable-v1 Gen AI client using Vertex AI and ADC."""
    if not project:
        raise ValueError("project is required")
    if not location:
        raise ValueError("location is required")

    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ["GOOGLE_CLOUD_LOCATION"] = location
    return genai.Client(http_options=types.HttpOptions(api_version="v1"))
