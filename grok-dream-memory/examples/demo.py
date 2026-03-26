"""Quick demonstration of grok-dream-memory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dream_memory.config import Config
from dream_memory.memory import MemoryStore
from dream_memory.dreamer import dream_cycle

def main() -> None:
    config = Config(qdrant_path="./demo_qdrant")
    store = MemoryStore(config)

    # Store some memories across lanes
    store.store("I prefer concise, direct answers without extra fluff.", lane="preferences")
    store.store("Always double-check safety constraints before executing.", lane="safety")
    store.store("User asked about Python async patterns on 2026-03-01.", lane="episodic")
    store.store("Use type hints consistently in all Python functions.", lane="rules")
    store.store("Had a great debugging session: discovered the issue was a missing await.", lane="episodic")

    print(f"Total memories stored: {store.count()}")

    # Recall
    results = store.recall("Python best practices", top_k=3)
    print("\nTop recall for 'Python best practices':")
    for r in results:
        print(f"  [{r['lane']}] score={r['score']}  {r['text'][:80]}")

    # Dream
    summary = dream_cycle(store=store, config=config)
    print(f"\nDream cycle summary: {summary}")
    print(f"Memories after dream: {store.count()}")


if __name__ == "__main__":
    main()
