"""Turn text into vectors (embeddings) so policy chunks can be searched by meaning.

Two embedders share one interface:
- FastEmbedEmbedder runs a small model on this machine (no API key; the model is
  downloaded once, then it works offline)
- FakeEmbedder makes repeatable fake vectors, so tests run offline and fast
"""

import hashlib
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.models.policy import EMBEDDING_DIM


class EmbeddingError(Exception):
    """The embedding model failed, or returned vectors of the wrong size."""


class Embedder(Protocol):
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _check(vector: list[float]) -> list[float]:
    if len(vector) != EMBEDDING_DIM:
        raise EmbeddingError(
            f"expected {EMBEDDING_DIM} numbers per vector but got {len(vector)}; "
            "the model does not match the database column"
        )
    return vector


class FastEmbedEmbedder:
    def __init__(self, model_name: str, cache_dir: str) -> None:
        from fastembed import TextEmbedding  # imported here because it is slow to load

        self.model_name = model_name
        try:
            self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        except Exception as error:
            raise EmbeddingError(
                f"could not load embedding model {model_name}: {error}"
            ) from error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_check([float(x) for x in vector]) for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self._model.query_embed([text])))
        return _check([float(x) for x in vector])


class FakeEmbedder:
    """Counts words into 384 buckets. Texts that share words get similar vectors."""

    model_name = "fake-embedder"

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            bucket = int(hashlib.sha256(word.encode()).hexdigest(), 16) % EMBEDDING_DIM
            vector[bucket] += 1.0
        length = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / length for x in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    cache_dir = settings.embedding_cache_dir or str(
        Path.home() / ".cache" / "resolviq" / "fastembed"
    )
    return FastEmbedEmbedder(settings.embedding_model, cache_dir)
