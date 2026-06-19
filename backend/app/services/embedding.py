"""Embedding generation with caching and batch processing."""

import hashlib
import json

import redis.asyncio as redis
from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Generate and cache embeddings using OpenAI's API.

    Features:
    - Batch embedding for efficiency (up to 2048 inputs per call)
    - Redis caching to avoid re-computing embeddings for identical text
    - Dimension reduction support (for text-embedding-3-* models)
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self.redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self.redis is None:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self.redis

    def _cache_key(self, text: str) -> str:
        """Generate a stable cache key for text."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"emb:{self.model}:{self.dimensions}:{text_hash}"

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text, using cache if available."""
        cached = await self._get_cached(text)
        if cached is not None:
            return cached

        response = await self.client.embeddings.create(
            input=[text],
            model=self.model,
            dimensions=self.dimensions,
        )
        embedding = response.data[0].embedding

        await self._set_cached(text, embedding)
        return embedding

    async def embed_batch(self, texts: list[str], batch_size: int = 512) -> list[list[float]]:
        """Embed multiple texts in batches with caching.

        The OpenAI API supports up to 2048 inputs per call, but we default
        to 512 to manage latency and memory.
        """
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Batch cache check using MGET (single round-trip instead of N)
        try:
            r = await self._get_redis()
            keys = [self._cache_key(text) for text in texts]
            cached_values = await r.mget(keys)
            for i, cached in enumerate(cached_values):
                if cached:
                    results[i] = json.loads(cached)
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(texts[i])
        except Exception:
            # Redis unavailable — treat all as uncached
            uncached_indices = list(range(len(texts)))
            uncached_texts = list(texts)

        # Batch embed uncached texts
        for batch_start in range(0, len(uncached_texts), batch_size):
            batch = uncached_texts[batch_start : batch_start + batch_size]
            response = await self.client.embeddings.create(
                input=batch,
                model=self.model,
                dimensions=self.dimensions,
            )

            # Batch cache write using pipeline (single round-trip)
            try:
                r = await self._get_redis()
                pipe = r.pipeline()
                for j, data in enumerate(response.data):
                    idx = uncached_indices[batch_start + j]
                    results[idx] = data.embedding
                    key = self._cache_key(uncached_texts[batch_start + j])
                    pipe.set(key, json.dumps(data.embedding), ex=604800)
                await pipe.execute()
            except Exception:
                # Cache write failure — still store results in memory
                for j, data in enumerate(response.data):
                    idx = uncached_indices[batch_start + j]
                    results[idx] = data.embedding

        return results  # type: ignore[return-value]

    async def _get_cached(self, text: str) -> list[float] | None:
        """Retrieve embedding from Redis cache."""
        try:
            r = await self._get_redis()
            key = self._cache_key(text)
            cached = await r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # Cache miss is non-fatal
        return None

    async def _set_cached(self, text: str, embedding: list[float]) -> None:
        """Store embedding in Redis cache (TTL: 7 days)."""
        try:
            r = await self._get_redis()
            key = self._cache_key(text)
            await r.set(key, json.dumps(embedding), ex=604800)
        except Exception:
            pass  # Cache write failure is non-fatal



# Singleton instance
embedding_service = EmbeddingService()
