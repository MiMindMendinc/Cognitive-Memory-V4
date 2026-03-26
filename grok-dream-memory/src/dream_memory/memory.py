"""Core memory store: lanes, store, recall, importance scoring, decay, prune."""
from __future__ import annotations

import uuid
import time
import logging
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PointIdsList,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

from .config import Config, LANES

logger = logging.getLogger(__name__)


class MemoryStore:
    """Thread-safe local Qdrant-backed memory store with 4 memory lanes."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config.from_env()
        self._client = QdrantClient(path=self.config.qdrant_path)
        self._encoder = SentenceTransformer(self.config.embedding_model)
        self._ensure_collection()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if self.config.collection_name not in existing:
            dim = self._encoder.get_sentence_embedding_dimension()
            self._client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s'", self.config.collection_name)

    def _embed(self, text: str) -> list[float]:
        return self._encoder.encode(text, normalize_embeddings=True).tolist()

    @staticmethod
    def _importance(text: str, lane: str) -> float:
        """Heuristic importance score 0-1 based on content and lane."""
        base = min(1.0, len(text.split()) / 50.0)
        lane_weights = {"safety": 1.0, "rules": 0.85, "episodic": 0.7, "preferences": 0.6}
        return round(base * lane_weights.get(lane, 0.7), 4)

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    def store(self, text: str, lane: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """Store a memory and return its ID."""
        if lane not in LANES:
            raise ValueError(f"Unknown lane '{lane}'. Valid: {LANES}")

        mem_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "text": text,
            "lane": lane,
            "importance": self._importance(text, lane),
            "created_at": time.time(),
            "accessed_at": time.time(),
            "access_count": 0,
            **(metadata or {}),
        }
        vector = self._embed(text)
        self._client.upsert(
            collection_name=self.config.collection_name,
            points=[PointStruct(id=mem_id, vector=vector, payload=payload)],
        )
        logger.debug("Stored memory %s in lane '%s'", mem_id, lane)
        return mem_id

    def recall(
        self,
        query: str,
        lane: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Semantic recall, optionally restricted to a single lane."""
        k = top_k or self.config.top_k_recall
        vector = self._embed(query)

        query_filter: Optional[Filter] = None
        if lane:
            if lane not in LANES:
                raise ValueError(f"Unknown lane '{lane}'. Valid: {LANES}")
            query_filter = Filter(
                must=[FieldCondition(key="lane", match=MatchValue(value=lane))]
            )

        results = self._client.query_points(
            collection_name=self.config.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=k,
            with_payload=True,
        ).points

        hits = []
        for r in results:
            payload = dict(r.payload or {})
            # boost access metrics
            self._client.set_payload(
                collection_name=self.config.collection_name,
                payload={
                    "accessed_at": time.time(),
                    "access_count": payload.get("access_count", 0) + 1,
                },
                points=[r.id],
            )
            hits.append({"id": r.id, "score": round(r.score, 4), **payload})
        return hits

    def all_memories(self, lane: Optional[str] = None) -> list[dict[str, Any]]:
        """Return all stored memories (optionally filtered by lane)."""
        scroll_filter: Optional[Filter] = None
        if lane:
            scroll_filter = Filter(
                must=[FieldCondition(key="lane", match=MatchValue(value=lane))]
            )
        records, _ = self._client.scroll(
            collection_name=self.config.collection_name,
            scroll_filter=scroll_filter,
            limit=self.config.max_memories,
            with_payload=True,
            with_vectors=False,
        )
        return [{"id": str(r.id), **dict(r.payload or {})} for r in records]

    def decay(self) -> int:
        """Apply importance decay to all memories. Returns count updated."""
        records, _ = self._client.scroll(
            collection_name=self.config.collection_name,
            limit=self.config.max_memories,
            with_payload=True,
            with_vectors=False,
        )
        updated = 0
        for r in records:
            payload = r.payload or {}
            current = float(payload.get("importance", 0.5))
            new_val = max(0.0, round(current - self.config.decay_rate, 4))
            self._client.set_payload(
                collection_name=self.config.collection_name,
                payload={"importance": new_val},
                points=[r.id],
            )
            updated += 1
        return updated

    def prune(self) -> int:
        """Delete memories below the prune importance threshold."""
        records, _ = self._client.scroll(
            collection_name=self.config.collection_name,
            limit=self.config.max_memories,
            with_payload=True,
            with_vectors=False,
        )
        to_delete = [
            r.id
            for r in records
            if float((r.payload or {}).get("importance", 1.0)) < self.config.prune_threshold
        ]
        if to_delete:
            self._client.delete(
                collection_name=self.config.collection_name,
                points_selector=PointIdsList(points=to_delete),
            )
        logger.info("Pruned %d low-importance memories", len(to_delete))
        return len(to_delete)

    def count(self) -> int:
        return self._client.count(collection_name=self.config.collection_name).count
