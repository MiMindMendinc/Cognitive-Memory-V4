"""Centralised configuration for dream_memory."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path

LANES = ("episodic", "rules", "safety", "preferences")

@dataclass
class Config:
    qdrant_path: str = field(default_factory=lambda: os.getenv("QDRANT_PATH", "./qdrant_data"))
    collection_name: str = "dream_memory"
    embedding_model: str = "all-MiniLM-L6-v2"
    dream_interval_minutes: int = 5
    max_memories: int = 10_000
    decay_rate: float = 0.01          # importance decay per dream cycle
    prune_threshold: float = 0.05     # memories below this are pruned
    top_k_recall: int = 5
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            qdrant_path=os.getenv("QDRANT_PATH", "./qdrant_data"),
            collection_name=os.getenv("COLLECTION_NAME", "dream_memory"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            dream_interval_minutes=int(os.getenv("DREAM_INTERVAL_MINUTES", "5")),
            max_memories=int(os.getenv("MAX_MEMORIES", "10000")),
            decay_rate=float(os.getenv("DECAY_RATE", "0.01")),
            prune_threshold=float(os.getenv("PRUNE_THRESHOLD", "0.05")),
            top_k_recall=int(os.getenv("TOP_K_RECALL", "5")),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
        )
