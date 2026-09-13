"""Small-corpus RAG backends for RetailOps business and model documentation."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from google.genai import types

from retailops_ai.agent.vertex_genai import build_vertex_genai_client

_TOKEN_RE = re.compile(r"\b[\w-]{2,}\b", flags=re.UNICODE)


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    section: str
    text: str


@dataclass(frozen=True)
class KnowledgeHit:
    source: str
    section: str
    text: str
    score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "section": self.section,
            "text": self.text,
            "score": round(self.score, 6),
        }


class KnowledgeRetriever(Protocol):
    def search(self, query: str, *, top_k: int) -> list[KnowledgeHit]: ...


def load_markdown_chunks(directory: str | Path) -> list[KnowledgeChunk]:
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"Knowledge directory does not exist: {root}")

    chunks: list[KnowledgeChunk] = []
    for path in sorted(root.glob("*.md")):
        section = path.stem
        buffer: list[str] = []

        def flush() -> None:
            text = "\n".join(buffer).strip()
            if text:
                chunks.append(
                    KnowledgeChunk(source=path.name, section=section, text=text)
                )
            buffer.clear()

        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                flush()
                section = line.lstrip("#").strip() or path.stem
            else:
                buffer.append(line)
        flush()

    if not chunks:
        raise ValueError(f"No Markdown knowledge documents found under {root}")
    return chunks


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class LexicalKnowledgeRetriever:
    """Deterministic no-cloud retriever used by local development and CI."""

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self.chunks = chunks
        self._counters = [Counter(_tokens(chunk.text)) for chunk in chunks]

    def search(self, query: str, *, top_k: int) -> list[KnowledgeHit]:
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return []

        ranked: list[tuple[float, int]] = []
        for index, counter in enumerate(self._counters):
            overlap = sum(1.0 + math.log(counter[token]) for token in query_tokens if token in counter)
            if overlap <= 0:
                continue
            normalization = math.sqrt(max(sum(counter.values()), 1))
            ranked.append((overlap / normalization, index))

        ranked.sort(reverse=True)
        return [
            KnowledgeHit(
                source=self.chunks[index].source,
                section=self.chunks[index].section,
                text=self.chunks[index].text,
                score=score,
            )
            for score, index in ranked[:top_k]
        ]


class VertexEmbeddingKnowledgeRetriever:
    """Embedding retriever for the same small curated corpus using Vertex AI."""

    def __init__(
        self,
        chunks: list[KnowledgeChunk],
        *,
        project: str,
        location: str,
        model: str,
        dimensionality: int = 768,
    ) -> None:
        self.chunks = chunks
        self.model = model
        self.dimensionality = dimensionality
        self.client = build_vertex_genai_client(project, location)
        self._matrix = self._embed_documents(chunks)

    def _embed_documents(self, chunks: list[KnowledgeChunk]) -> np.ndarray:
        response = self.client.models.embed_content(
            model=self.model,
            contents=[chunk.text for chunk in chunks],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self.dimensionality,
            ),
        )
        embeddings = response.embeddings or []
        if len(embeddings) != len(chunks):
            raise RuntimeError("Vertex embedding response did not match corpus size")
        matrix = np.asarray([embedding.values for embedding in embeddings], dtype="float64")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.clip(norms, 1e-12, None)

    def search(self, query: str, *, top_k: int) -> list[KnowledgeHit]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=query,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.dimensionality,
            ),
        )
        embeddings = response.embeddings or []
        if not embeddings:
            return []
        query_vector = np.asarray(embeddings[0].values, dtype="float64")
        query_vector = query_vector / max(float(np.linalg.norm(query_vector)), 1e-12)
        scores = self._matrix @ query_vector
        indices = np.argsort(scores)[::-1][:top_k]
        return [
            KnowledgeHit(
                source=self.chunks[int(index)].source,
                section=self.chunks[int(index)].section,
                text=self.chunks[int(index)].text,
                score=float(scores[int(index)]),
            )
            for index in indices
        ]
