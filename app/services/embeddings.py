from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings


class EmbeddingProviderUnavailableError(Exception):
    """Raised when embedding provider is not configured."""


class EmbeddingProviderError(Exception):
    """Raised when embedding provider call fails."""


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings aligned with the input order."""


class UnconfiguredEmbeddingProvider(BaseEmbeddingProvider):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        _ = texts
        raise EmbeddingProviderUnavailableError("Embedding provider is not configured.")


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        expected_dimension: int,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.expected_dimension = expected_dimension
        self.timeout_seconds = timeout_seconds

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(f"OpenAI embedding request failed: {exc}") from exc

        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list):
            raise EmbeddingProviderError("OpenAI embedding response format is invalid.")

        ordered = sorted(data, key=lambda row: row.get("index", 0))
        embeddings: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list):
                raise EmbeddingProviderError("OpenAI embedding vector is missing.")
            float_vector = [float(value) for value in vector]
            if self.expected_dimension and len(float_vector) != self.expected_dimension:
                raise EmbeddingProviderError(
                    "Embedding dimension mismatch. "
                    f"expected={self.expected_dimension}, got={len(float_vector)}"
                )
            embeddings.append(float_vector)
        return embeddings


def build_embedding_provider(settings: Settings) -> BaseEmbeddingProvider:
    provider_name = settings.provider_name.lower().strip()
    if provider_name != "openai":
        return UnconfiguredEmbeddingProvider()
    if not settings.openai_api_key:
        return UnconfiguredEmbeddingProvider()
    return OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
        expected_dimension=settings.embedding_dimension,
    )

