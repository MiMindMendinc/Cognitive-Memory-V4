"""Tests for grok-dream-memory core functionality."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dream_memory.config import Config, LANES


def _make_fake_encoder():
    """Return a mock SentenceTransformer that produces deterministic 384-d vectors."""
    encoder = MagicMock()

    def fake_encode(text, normalize_embeddings=True):
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        v = rng.random(384).astype(np.float32)
        if normalize_embeddings:
            v = v / np.linalg.norm(v)
        return v

    encoder.encode.side_effect = fake_encode
    encoder.get_sentence_embedding_dimension.return_value = 384
    return encoder


@pytest.fixture
def store(tmp_path):
    config = Config(
        qdrant_path=str(tmp_path / "qdrant"),
        collection_name="test_memory",
        prune_threshold=0.0,
        decay_rate=0.01,
    )
    with patch("dream_memory.memory.SentenceTransformer", return_value=_make_fake_encoder()):
        from dream_memory.memory import MemoryStore
        return MemoryStore(config)


# Import after patching is established via fixture; also patch at module level for
# non-fixture tests that just need the class imported.
with patch("dream_memory.memory.SentenceTransformer", return_value=_make_fake_encoder()):
    from dream_memory.memory import MemoryStore
from dream_memory.dreamer import dream_cycle


def test_lanes_constant():
    assert "episodic" in LANES
    assert "rules" in LANES
    assert "safety" in LANES
    assert "preferences" in LANES


def test_store_and_count(store):
    assert store.count() == 0
    store.store("Hello world", lane="episodic")
    assert store.count() == 1


def test_store_returns_id(store):
    mem_id = store.store("Test memory", lane="rules")
    assert isinstance(mem_id, str)
    assert len(mem_id) == 36  # UUID format


def test_invalid_lane_raises(store):
    with pytest.raises(ValueError, match="Unknown lane"):
        store.store("bad lane test", lane="invalid_lane")


def test_recall_returns_results(store):
    store.store("The cat sat on the mat", lane="episodic")
    store.store("Dogs are loyal animals", lane="episodic")
    results = store.recall("cat", top_k=2)
    assert len(results) >= 1
    assert all("text" in r for r in results)
    assert all("score" in r for r in results)


def test_recall_lane_filter(store):
    store.store("Safety rule: do not delete production data", lane="safety")
    store.store("I prefer dark mode", lane="preferences")
    results = store.recall("safety rule", lane="safety", top_k=5)
    assert all(r["lane"] == "safety" for r in results)


def test_all_memories(store):
    store.store("episodic memory 1", lane="episodic")
    store.store("rules memory 1", lane="rules")
    all_mems = store.all_memories()
    assert len(all_mems) == 2


def test_all_memories_lane_filter(store):
    store.store("episodic memory", lane="episodic")
    store.store("rules memory", lane="rules")
    episodic = store.all_memories(lane="episodic")
    assert len(episodic) == 1
    assert episodic[0]["lane"] == "episodic"


def test_decay_reduces_importance(store):
    store.store("some memory to decay", lane="episodic")
    mems_before = store.all_memories()
    imp_before = mems_before[0]["importance"]

    store.decay()

    mems_after = store.all_memories()
    imp_after = mems_after[0]["importance"]
    assert imp_after < imp_before or imp_after == 0.0


def test_prune_removes_low_importance(store):
    # Store with zero importance by using very short text then manually set
    mem_id = store.store("x", lane="episodic")
    # Directly set importance to below threshold
    store._client.set_payload(
        collection_name=store.config.collection_name,
        payload={"importance": 0.001},
        points=[mem_id],
    )
    store.config.prune_threshold = 0.05
    pruned = store.prune()
    assert pruned >= 1
    assert store.count() == 0


def test_dream_cycle(store):
    store.store("I always check types before runtime", lane="episodic")
    store.store("Never expose secrets in logs", lane="safety")
    result = dream_cycle(store=store)
    assert "decayed" in result
    assert "pruned" in result
    assert "consolidated" in result


def test_importance_scoring(store):
    # Safety lane should score higher than preferences for same text
    short = "ok"
    long_text = " ".join(["word"] * 60)
    imp_short = store._importance(short, "safety")
    imp_long = store._importance(long_text, "safety")
    assert imp_long >= imp_short


def test_multiple_lanes(store):
    for lane in LANES:
        store.store(f"Memory in {lane}", lane=lane)
    assert store.count() == len(LANES)
    for lane in LANES:
        mems = store.all_memories(lane=lane)
        assert len(mems) == 1
