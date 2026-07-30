"""
app/services/cache.py

Semantic cache for RAG answers, backed by Redis.

Why semantic, not exact-match:
  Users ask the same thing in different words — "what's the re-delivery
  policy?" vs "how does re-delivery work?" An exact-string cache misses
  those. A semantic cache embeds the question and treats any incoming
  question that is >= a similarity threshold to a cached one as a hit,
  returning the stored answer instantly instead of calling the LLM.

Why it's safe (doesn't serve stale policy):
  The cache stores GENERATED answers (with their citations), not
  hand-written ones — so the single source of truth is still the
  documents. When documents are re-ingested, we bump a "generation"
  counter so every prior cache entry is logically invalidated. Entries
  also carry a TTL so nothing lives forever.

Scope:
  Only the /answer (RAG) path is cached. Investigations are NOT cached —
  they depend on live shipment state (SLA countdowns, status), so a
  cached investigation could be stale and misleading.

Design:
  Each entry is a Redis hash at key `wasl:cache:{gen}:{uuid}` holding
  the question, the serialized answer, and the raw embedding bytes.
  On lookup we embed the incoming question and compare (cosine) against
  the cached embeddings for the current generation. Small N (dozens to
  hundreds of entries) makes an in-Python comparison simple and fast;
  if the cache ever grows large, this is where you'd switch to a
  RediSearch HNSW vector index.

Everything degrades gracefully: if Redis is unreachable, the cache is a
no-op and the app answers normally (just without caching).
"""

from __future__ import annotations

import json
import uuid

import numpy as np

from app.config import settings

_GEN_KEY = "wasl:cache:generation"  # current generation counter
_ENTRY_PREFIX = "wasl:cache:entries"  # per-generation entry index set


class SemanticCache:
    """Redis-backed semantic cache over RAG answers."""

    def __init__(self) -> None:
        self._redis = None
        self._enabled = False
        self._init_redis()

    # ------------------------------------------------------------------
    def _init_redis(self) -> None:
        if not getattr(settings, "cache_enabled", True):
            return
        try:
            import redis

            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=False,  # we store binary embeddings
                socket_connect_timeout=2,
            )
            self._redis.ping()
            self._enabled = True
        except Exception as exc:  # noqa: BLE001
            print(f"[cache] Redis unavailable, semantic cache disabled: {exc}")
            self._redis = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    def _generation(self) -> int:
        """Current cache generation. Re-ingesting documents bumps this."""
        raw = self._redis.get(_GEN_KEY)
        return int(raw) if raw else 0

    def _index_key(self, gen: int) -> str:
        return f"{_ENTRY_PREFIX}:{gen}"

    # ------------------------------------------------------------------
    def lookup(self, question: str, query_embedding: list[float]) -> dict | None:
        """
        Return a cached answer dict for a semantically similar question,
        or None on a miss. `query_embedding` is the already-computed
        embedding of `question` (we reuse the one retrieval computes).
        """
        if not self._enabled:
            return None
        try:
            gen = self._generation()
            index_key = self._index_key(gen)
            entry_ids = self._redis.smembers(index_key)
            if not entry_ids:
                return None

            q_vec = np.asarray(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec) or 1.0

            best_score = -1.0
            best_payload = None

            for entry_id in entry_ids:
                data = self._redis.hgetall(entry_id)
                if not data:
                    continue
                emb = np.frombuffer(data[b"embedding"], dtype=np.float32)
                score = float(q_vec @ emb / (q_norm * (np.linalg.norm(emb) or 1.0)))
                if score > best_score:
                    best_score = score
                    best_payload = data.get(b"answer")

            if (
                best_payload is not None
                and best_score >= settings.cache_similarity_threshold
            ):
                answer = json.loads(best_payload)
                answer["_cache_hit"] = True
                answer["_cache_score"] = round(best_score, 4)
                return answer
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"[cache] lookup failed, ignoring: {exc}")
            return None

    # ------------------------------------------------------------------
    def store(self, question: str, query_embedding: list[float], answer: dict) -> None:
        """Cache a freshly generated answer for future similar questions."""
        if not self._enabled:
            return
        # Don't cache declines — an "I don't know" shouldn't be pinned.
        if not answer.get("answered", False):
            return
        try:
            gen = self._generation()
            index_key = self._index_key(gen)
            entry_id = f"wasl:cache:{gen}:{uuid.uuid4().hex}"

            emb = np.asarray(query_embedding, dtype=np.float32).tobytes()
            # Strip transient cache markers before storing.
            clean = {k: v for k, v in answer.items() if not k.startswith("_cache")}

            self._redis.hset(
                entry_id,
                mapping={
                    "question": question,
                    "answer": json.dumps(clean),
                    "embedding": emb,
                },
            )
            self._redis.expire(entry_id, settings.cache_ttl_seconds)
            self._redis.sadd(index_key, entry_id)
            self._redis.expire(index_key, settings.cache_ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            print(f"[cache] store failed, ignoring: {exc}")

    # ------------------------------------------------------------------
    def invalidate(self) -> None:
        """
        Invalidate the whole cache by bumping the generation counter.
        Call this after re-ingesting documents so no stale answers survive.
        Old entries expire on their own TTL; they're simply never matched.
        """
        if not self._enabled:
            return
        try:
            self._redis.incr(_GEN_KEY)
        except Exception as exc:  # noqa: BLE001
            print(f"[cache] invalidate failed, ignoring: {exc}")

    def stats(self) -> dict:
        """Small stats blob for a debug/health endpoint."""
        if not self._enabled:
            return {"enabled": False}
        try:
            gen = self._generation()
            count = self._redis.scard(self._index_key(gen))
            return {"enabled": True, "generation": gen, "entries": int(count)}
        except Exception:  # noqa: BLE001
            return {"enabled": True, "generation": None, "entries": None}


# ---------------------------------------------------------------------------
_cache: SemanticCache | None = None


def get_cache() -> SemanticCache:
    """Shared SemanticCache instance (lazy singleton)."""
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache
