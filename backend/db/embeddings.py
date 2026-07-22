"""Text embedding utilities using Sentence Transformers with LRU Caching."""

import functools
import asyncio
from sentence_transformers import SentenceTransformer
from backend.config.settings import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazy-load and cache the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBED_MODEL_NAME)
    return _model


@functools.lru_cache(maxsize=1024)
def _embed_cached(text: str) -> tuple[float, ...]:
    """Internal LRU-cached embedding function (returns tuple for hashability)."""
    model = get_model()
    vec = model.encode(text).tolist()
    return tuple(vec)


def embed_text(text: str) -> list[float]:
    """Embed a single text string and return the vector (uses LRU cache)."""
    return list(_embed_cached(text))


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts at once efficiently using cache where possible."""
    results = []
    uncached_indices = []
    uncached_texts = []

    for i, t in enumerate(texts):
        if t in _embed_cached.cache_info():
            results.append(embed_text(t))
        else:
            uncached_indices.append(i)
            uncached_texts.append(t)
            results.append([])  # placeholder

    if uncached_texts:
        model = get_model()
        vectors = model.encode(uncached_texts).tolist()
        for idx, vec in zip(uncached_indices, vectors):
            results[idx] = vec
            # Populate cache
            _embed_cached.cache_clear()  # keep cache clean if needed or rely on embed_text

    return results


async def embed_text_async(text: str) -> list[float]:
    """Async wrapper to run embedding generation in an executor thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, embed_text, text)
